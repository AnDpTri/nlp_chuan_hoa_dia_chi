"""Chuẩn bị dữ liệu và sinh Hard Negatives cho bài toán liên kết thực thể (Entity Linking).
Phân chia Train/Validation theo họ nguồn độc lập (zero leakage).
Phân biệt mốc nguồn/đích và giữ các ca mơ hồ đúng chuẩn.
"""

import json
import random
import unicodedata
from collections import defaultdict
from pathlib import Path


def plain_text(s):
    if not s:
        return ""
    text = unicodedata.normalize("NFD", str(s).casefold().replace("đ", "d"))
    return "".join(c for c in text if not unicodedata.combining(c)).strip()


def compute_string_similarity(str1, str2):
    """Tính độ tương đồng chuỗi từ vựng (Jaccard ký tự 2-gram)."""
    p1 = plain_text(str1)
    p2 = plain_text(str2)
    if not p1 or not p2:
        return 0.0
    if p1 == p2:
        return 1.0
    # 2-grams
    ng1 = {p1[i:i+2] for i in range(len(p1)-1)} or {p1}
    ng2 = {p2[i:i+2] for i in range(len(p2)-1)} or {p2}
    intersection = len(ng1 & ng2)
    union = len(ng1 | ng2)
    return intersection / max(1, union)


def extract_geo_features(span_text, cand_dv, kieu_khop="chinh_xac", co_tien_to=False,
                         parent_support=False):
    """Trích xuất vector 12 đặc trưng địa bàn & từ vựng."""
    # 0, 1, 2: Cấp
    cap_xa = 1.0 if cand_dv.cap == "xa" else 0.0
    cap_huyen = 1.0 if cand_dv.cap == "huyen" else 0.0
    cap_tinh = 1.0 if cand_dv.cap == "tinh" else 0.0

    # 3, 4: Mốc thời gian
    cay_moi = 1.0 if cand_dv.cay == "moi" else 0.0
    cay_cu = 1.0 if cand_dv.cay == "cu" else 0.0

    # 5, 6, 7, 8: Kiểu khớp
    kk_chinh_xac = 1.0 if kieu_khop == "chinh_xac" else 0.0
    kk_khong_dau = 1.0 if kieu_khop == "khong_dau" else 0.0
    kk_viet_tat = 1.0 if kieu_khop == "viet_tat" else 0.0
    kk_sai_chinh_ta = 1.0 if kieu_khop == "sai_chinh_ta" else 0.0

    # 9: Tiền tố
    tt = 1.0 if co_tien_to else 0.0

    # 10: Tương đồng chuỗi
    sim = compute_string_similarity(span_text, cand_dv.ten)

    # 11: Có cha hỗ trợ
    ps = 1.0 if parent_support else 0.0

    return [
        cap_xa, cap_huyen, cap_tinh, cay_moi, cay_cu,
        kk_chinh_xac, kk_khong_dau, kk_viet_tat, kk_sai_chinh_ta,
        tt, sim, ps
    ]


class LinkingSampleBuilder:
    """Xây dựng tập dữ liệu huấn luyện đầu liên kết với Hard Negatives."""

    def __init__(self, danh_muc, doi_chieu_rows=None):
        self.dm = danh_muc
        self.old_to_new_targets = defaultdict(set)
        if doi_chieu_rows:
            for r in doi_chieu_rows:
                if r.get("ma_xa_cu") and r.get("ma_xa_moi"):
                    self.old_to_new_targets[r["ma_xa_cu"]].add(r["ma_xa_moi"])

        # Chỉ mục danh mục theo tên chuẩn hóa để khai thác Hard Negatives cùng tên khác địa bàn
        self.name_to_candidates = defaultdict(list)
        for dv in danh_muc.don_vi.values():
            p_name = plain_text(dv.ten)
            self.name_to_candidates[dv.cap, p_name].append(dv)

    def is_equivalent_target(self, cand1, cand2):
        """Kiểm tra hai ứng viên có cùng trỏ về một đích hợp lệ không."""
        if cand1.cay == cand2.cay and cand1.ma == cand2.ma:
            return True
        # Nếu 1 cũ 1 mới, kiểm tra đồ thị chuyển đổi mốc 2025
        if cand1.cay == "cu" and cand2.cay == "moi":
            return cand2.ma in self.old_to_new_targets.get(cand1.ma, set())
        if cand1.cay == "moi" and cand2.cay == "cu":
            return cand1.ma in self.old_to_new_targets.get(cand2.ma, set())
        return False

    def mine_negatives(self, pos_cand, span_text, num_hard=3, num_random=2):
        """Khai thác các hard negatives theo địa bàn và tên gần giống."""
        cap = pos_cand.cap
        pos_pname = plain_text(pos_cand.ten)

        negatives = []

        # 1. Hard negative cùng tên khác huyện / tỉnh
        same_name_diff_loc = [
            dv for dv in self.name_to_candidates.get((cap, pos_pname), [])
            if not self.is_equivalent_target(pos_cand, dv)
        ]
        if same_name_diff_loc:
            negatives.extend(random.sample(same_name_diff_loc, min(num_hard, len(same_name_diff_loc))))

        # 2. Hard negative cùng cấp nhưng khác mốc / sáp nhập
        all_same_cap = [dv for dv in self.dm.don_vi.values() if dv.cap == cap and not self.is_equivalent_target(pos_cand, dv)]
        if len(negatives) < num_hard + num_random and all_same_cap:
            needed = (num_hard + num_random) - len(negatives)
            # Ưu tiên các đơn vị có tương đồng chuỗi từ vựng cao
            scored = [(compute_string_similarity(span_text, dv.ten), dv) for dv in all_same_cap]
            scored.sort(key=lambda x: x[0], reverse=True)
            top_similar = [dv for _, dv in scored[:needed * 3]]
            negatives.extend(random.sample(top_similar, min(needed, len(top_similar))))

        return negatives

    def create_linking_instance(self, input_text, span_info, pos_cand, all_retrieved_cands=None):
        """Tạo một instance huấn luyện hoàn chỉnh gồm 1 positive và K negatives."""
        span_text, span_start, span_end = span_info

        neg_dvs = self.mine_negatives(pos_cand, span_text, num_hard=3, num_random=2)

        # Vector đặc trưng cho positive
        pos_geo = extract_geo_features(span_text, pos_cand, kieu_khop="chinh_xac", co_tien_to=True, parent_support=True)

        candidates_data = [{
            "cay": pos_cand.cay,
            "ma": pos_cand.ma,
            "cap": pos_cand.cap,
            "ten": pos_cand.ten,
            "is_positive": True,
            "geo_features": pos_geo
        }]

        for neg in neg_dvs:
            neg_geo = extract_geo_features(span_text, neg, kieu_khop="khac_dia_ban", co_tien_to=False, parent_support=False)
            candidates_data.append({
                "cay": neg.cay,
                "ma": neg.ma,
                "cap": neg.cap,
                "ten": neg.ten,
                "is_positive": False,
                "geo_features": neg_geo
            })

        return {
            "input_text": input_text,
            "span_start": span_start,
            "span_end": span_end,
            "span_text": span_text,
            "candidates": candidates_data
        }


def split_dataset_by_family(rows, val_ratio=0.15, seed=42):
    """Phân chia tập train và validation theo họ nguồn cha (Zero Family Leakage)."""
    rng = random.Random(seed)
    families = defaultdict(list)
    for r in rows:
        fid = r.get("training_group") or r.get("family_id") or r.get("id")
        families[fid].append(r)

    family_keys = sorted(list(families.keys()))
    rng.shuffle(family_keys)

    num_val = max(1, int(len(family_keys) * val_ratio))
    val_fams = set(family_keys[:num_val])
    train_fams = set(family_keys[num_val:])

    train_rows = [r for fid in train_fams for r in families[fid]]
    val_rows = [r for fid in val_fams for r in families[fid]]

    assert not (train_fams & val_fams), "Rò rỉ họ nguồn cha giữa Train và Validation!"

    return {
        "train_rows": train_rows,
        "val_rows": val_rows,
        "train_families": sorted(list(train_fams)),
        "val_families": sorted(list(val_fams))
    }
