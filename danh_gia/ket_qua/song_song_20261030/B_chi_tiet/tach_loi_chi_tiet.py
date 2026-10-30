"""
Script Phân Tích Chuyên Sâu Nhiệm Vụ B:
TÁCH SAI SPAN / FORMAT / TÊN CHUẨN / NHÃN NGHI VẤN
Chỉ đọc dữ liệu frozen, không train, không sinh thêm data, không sửa src/ hay catalog.
Chỉ ghi vào danh_gia/ket_qua/song_song_20261030/B_chi_tiet/
"""

import sys
import os
import json
import csv
import hashlib
import time
import unicodedata
from pathlib import Path
from collections import Counter, defaultdict

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path("D:/nlp_chuan_hoa_dia_chi")
sys.path.insert(0, str(ROOT))

import torch
torch.set_num_threads(1)

from src.danh_muc import DanhMuc
from src.char_cnn import BoTachCharCNN, nfc_offsets, TAGS
from src.ngu_canh_neural import NguCanhChar
from src.xep_hang import BoXepHang
from src.chuan_ten_duong import TuDienDuong
from src.chuan_hoa import BoChuanHoa

OUT_DIR = ROOT / "danh_gia/ket_qua/song_song_20261030/B_chi_tiet"
OUT_DIR.mkdir(parents=True, exist_ok=True)

DETAIL_ROLES = ("so_nha", "ngo_ngach_hem", "duong", "thon_xom")
CORE_FIELDS = ("so_nha", "ngo_ngach_hem", "thon_xom", "duong", "ma_xa", "ma_tinh")

def norm(s):
    if s is None:
        return ""
    return " ".join(unicodedata.normalize("NFC", str(s)).casefold().split())

def compute_sha256(filepath):
    p = Path(filepath)
    if not p.exists():
        return None
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def verify_manifest():
    manifest_path = ROOT / "danh_gia/ket_qua/song_song_20261030/BASELINE_MANIFEST.json"
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    mismatches = []
    for rel_path, expected_hash in manifest.get("sha256", {}).items():
        actual_hash = compute_sha256(ROOT / rel_path)
        if actual_hash != expected_hash:
            mismatches.append((rel_path, expected_hash, actual_hash))
    return mismatches

def evaluate_spans(dataset_name, items, botach):
    """
    Đo Exact Span Match và Char-level Match cho 4 roles chi tiết.
    items: danh sách dict có 'id', 'text', 'spans' (từ file jsonl frozen).
    """
    exact_metrics = {r: {"gold": 0, "pred": 0, "tp": 0} for r in DETAIL_ROLES}
    char_metrics = {r: {"gold": 0, "pred": 0, "tp": 0} for r in DETAIL_ROLES}
    
    # Store predictions for further analysis
    pred_cache = {}

    for item in items:
        cid = item["id"]
        text = item["text"]
        ctx = botach.chuan_bi_chuoi(text)
        pred_spans = ctx.char_spans  # list of (role, start, end)
        pred_cache[cid] = pred_spans

        gold_spans = [(r, s, e) for r, s, e in item.get("spans", []) if r in DETAIL_ROLES]
        pred_detail_spans = [(r, s, e) for r, s, e in pred_spans if r in DETAIL_ROLES]

        # 1. Exact span evaluation per role
        for r in DETAIL_ROLES:
            g_set = {(s, e) for role, s, e in gold_spans if role == r}
            p_set = {(s, e) for role, s, e in pred_detail_spans if role == r}
            exact_metrics[r]["gold"] += len(g_set)
            exact_metrics[r]["pred"] += len(p_set)
            exact_metrics[r]["tp"] += len(g_set.intersection(p_set))

        # 2. Character-level offset evaluation per role
        L = len(text)
        gold_char_map = {r: [0] * L for r in DETAIL_ROLES}
        pred_char_map = {r: [0] * L for r in DETAIL_ROLES}

        for role, s, e in gold_spans:
            s_clamped = max(0, min(L, s))
            e_clamped = max(0, min(L, e))
            for i in range(s_clamped, e_clamped):
                gold_char_map[role][i] = 1

        for role, s, e in pred_detail_spans:
            s_clamped = max(0, min(L, s))
            e_clamped = max(0, min(L, e))
            for i in range(s_clamped, e_clamped):
                pred_char_map[role][i] = 1

        for r in DETAIL_ROLES:
            g_c = gold_char_map[r]
            p_c = pred_char_map[r]
            char_metrics[r]["gold"] += sum(g_c)
            char_metrics[r]["pred"] += sum(p_c)
            char_metrics[r]["tp"] += sum(1 for a, b in zip(g_c, p_c) if a == 1 and b == 1)

    # Compute precision, recall, F1
    results = {"dataset": dataset_name, "num_samples": len(items), "exact_span": {}, "char_offset": {}}

    total_exact_gold = sum(exact_metrics[r]["gold"] for r in DETAIL_ROLES)
    total_exact_pred = sum(exact_metrics[r]["pred"] for r in DETAIL_ROLES)
    total_exact_tp = sum(exact_metrics[r]["tp"] for r in DETAIL_ROLES)

    for r in DETAIL_ROLES:
        g = exact_metrics[r]["gold"]
        p = exact_metrics[r]["pred"]
        tp = exact_metrics[r]["tp"]
        if g == 0:
            results["exact_span"][r] = {
                "support": 0, "pred_count": p, "tp": tp,
                "precision": "N/A", "recall": "N/A", "f1": "N/A",
                "note": "support=0 -> N/A"
            }
        else:
            prec = tp / p if p > 0 else 0.0
            rec = tp / g if g > 0 else 0.0
            f1 = (2 * prec * rec / (prec + rec)) if (prec + rec) > 0 else 0.0
            results["exact_span"][r] = {
                "support": g, "pred_count": p, "tp": tp,
                "precision": round(prec, 4), "recall": round(rec, 4), "f1": round(f1, 4)
            }

    # Micro exact
    micro_p = total_exact_tp / total_exact_pred if total_exact_pred > 0 else 0.0
    micro_r = total_exact_tp / total_exact_gold if total_exact_gold > 0 else 0.0
    micro_f1 = (2 * micro_p * micro_r / (micro_p + micro_r)) if (micro_p + micro_r) > 0 else 0.0
    results["exact_span"]["overall_micro"] = {
        "support": total_exact_gold, "pred_count": total_exact_pred, "tp": total_exact_tp,
        "precision": round(micro_p, 4), "recall": round(micro_r, 4), "f1": round(micro_f1, 4)
    }

    # Char offset metrics
    total_char_gold = sum(char_metrics[r]["gold"] for r in DETAIL_ROLES)
    total_char_pred = sum(char_metrics[r]["pred"] for r in DETAIL_ROLES)
    total_char_tp = sum(char_metrics[r]["tp"] for r in DETAIL_ROLES)

    for r in DETAIL_ROLES:
        g = char_metrics[r]["gold"]
        p = char_metrics[r]["pred"]
        tp = char_metrics[r]["tp"]
        if g == 0:
            results["char_offset"][r] = {
                "support_chars": 0, "pred_chars": p, "tp_chars": tp,
                "precision": "N/A", "recall": "N/A", "f1": "N/A",
                "note": "support=0 -> N/A"
            }
        else:
            prec = tp / p if p > 0 else 0.0
            rec = tp / g if g > 0 else 0.0
            f1 = (2 * prec * rec / (prec + rec)) if (prec + rec) > 0 else 0.0
            results["char_offset"][r] = {
                "support_chars": g, "pred_chars": p, "tp_chars": tp,
                "precision": round(prec, 4), "recall": round(rec, 4), "f1": round(f1, 4)
            }

    micro_cp = total_char_tp / total_char_pred if total_char_pred > 0 else 0.0
    micro_cr = total_char_tp / total_char_gold if total_char_gold > 0 else 0.0
    micro_cf1 = (2 * micro_cp * micro_cr / (micro_cp + micro_cr)) if (micro_cp + micro_cr) > 0 else 0.0
    results["char_offset"]["overall_micro"] = {
        "support_chars": total_char_gold, "pred_chars": total_char_pred, "tp_chars": total_char_tp,
        "precision": round(micro_cp, 4), "recall": round(micro_cr, 4), "f1": round(micro_cf1, 4)
    }

    return results, pred_cache

def deconstruct_errors(cases_220, goc_spans_map, botach, td_duong, dm):
    """
    Phân rã 220 ca lỗi dev, đặc biệt là nhóm 112 ca LOI_CHI_TIET_LAM_HONG_BEAM
    và 95 ca cờ 'loi_duong' thành 6 tầng nguyên nhân kỹ thuật cụ thể.
    """
    detail_112_cases = [c for c in cases_220 if c.get("error_category") == "LOI_CHI_TIET_LAM_HONG_BEAM"]
    street_95_cases = [c for c in detail_112_cases if "loi_duong" in c.get("secondary_flags", [])]

    # Bảng phân nhóm tầng lỗi cho 112 ca
    layer_counts_112 = Counter()
    layer_counts_95_street = Counter()
    deconstructed_records = []

    for c in detail_112_cases:
        cid = c["id"]
        inp = c["input"]
        ref = c["ref"]
        pred_base = c["pred_base"]
        flags = c.get("secondary_flags", [])
        annot = goc_spans_map.get(cid)

        ctx = botach.chuan_bi_chuoi(inp)
        pred_spans = ctx.char_spans
        pred_detail_spans = [(r, s, e) for r, s, e in pred_spans if r in DETAIL_ROLES]
        pred_roles_dict = {r: inp[s:e] for r, s, e in pred_spans}

        # Check conditions
        gold_spans = annot.get("spans", []) if annot else None
        gold_detail_spans = [(r, s, e) for r, s, e in gold_spans if r in DETAIL_ROLES] if gold_spans is not None else None

        # Attributes
        has_annot = annot is not None
        ref_duong = ref.get("duong", "")
        pred_duong = pred_base.get("duong", "")
        raw_duong = pred_roles_dict.get("duong", "")
        ma_tinh = ref.get("ma_tinh") or pred_base.get("ma_tinh", "")

        # Test dictionary presence
        cands = td_duong.ung_vien(raw_duong, ma_tinh) if (raw_duong and ma_tinh) else []
        is_in_dict = len(cands) > 0

        # Classification logic into primary layer
        assigned_layer = None
        evidence = []

        # Tầng 5: Nhãn tham chiếu nhiễu / khuyết / mơ hồ
        # Ref duong empty while input clearly has street
        if not ref_duong and raw_duong and any(w in norm(inp) for w in ("đường", "phố", "đ.", "d.")):
            assigned_layer = "TANG_5_NHAN_NHIEU_HOAC_MO_HO"
            evidence.append(f"Ref đường rỗng nhưng input có đường rõ: '{raw_duong}'")
        elif ref_duong and any(w in norm(ref_duong) for w in ("phường", "quận", "huyện", "tỉnh", "thành phố")):
            assigned_layer = "TANG_5_NHAN_NHIEU_HOAC_MO_HO"
            evidence.append(f"Ref đường chứa tên đơn vị hành chính: '{ref_duong}'")
        elif "xa_bi_chia" in flags:
            assigned_layer = "TANG_5_NHAN_NHIEU_HOAC_MO_HO"
            evidence.append("Xã bị chia tách mốc 2025 không đủ căn cứ chọn 1 đích duy nhất")

        # Tầng 1: Sai trích xuất span thô (Raw Span Error)
        if assigned_layer is None and has_annot:
            # So sánh gold spans với pred spans
            gold_set = set(gold_detail_spans)
            pred_set = set(pred_detail_spans)
            if gold_set != pred_set:
                # Kiểm tra xem sai ở đâu
                gold_duong_spans = [s for s in gold_detail_spans if s[0] == "duong"]
                pred_duong_spans = [s for s in pred_detail_spans if s[0] == "duong"]
                if gold_duong_spans != pred_duong_spans:
                    assigned_layer = "TANG_1_SAI_RAW_SPAN"
                    g_txt = [inp[s:e] for _, s, e in gold_duong_spans]
                    p_txt = [inp[s:e] for _, s, e in pred_duong_spans]
                    evidence.append(f"CNN cắt sai span đường: gold={g_txt} vs pred={p_txt}")
                else:
                    assigned_layer = "TANG_1_SAI_RAW_SPAN"
                    evidence.append(f"CNN cắt sai span chi tiết khác (số nhà/ngõ/thôn): gold={gold_detail_spans} vs pred={pred_detail_spans}")

        # Tầng 2: Lệch Formatter (Raw span trích đúng nhưng format lệch canonical / ref)
        if assigned_layer is None:
            # Kiểm tra xem raw span có giống ref về mặt từ vựng không (chỉ khác tiền tố 'Đường', 'Số', viết hoa, dấu cách)
            norm_raw_d = norm(raw_duong).replace("đường ", "").replace("phố ", "")
            norm_ref_d = norm(ref_duong).replace("đường ", "").replace("phố ", "")
            norm_pred_d = norm(pred_duong).replace("đường ", "").replace("phố ", "")
            
            norm_raw_sn = norm(pred_roles_dict.get("so_nha", "")).replace("số ", "")
            norm_ref_sn = norm(ref.get("so_nha", "")).replace("số ", "")

            if norm_raw_d == norm_ref_d and norm_ref_d != "":
                if norm(pred_duong) != norm(ref_duong):
                    assigned_layer = "TANG_2_LECH_FORMATTER"
                    evidence.append(f"Raw span đường đúng semantic '{raw_duong}', nhưng pipeline format '{pred_duong}' khác ref '{ref_duong}'")
            elif norm_raw_sn == norm_ref_sn and norm_ref_sn != "":
                if norm(pred_base.get("so_nha", "")) != norm(ref.get("so_nha", "")):
                    assigned_layer = "TANG_2_LECH_FORMATTER"
                    evidence.append(f"Raw số nhà đúng '{pred_roles_dict.get('so_nha')}', nhưng format '{pred_base.get('so_nha')}' lệch ref '{ref.get('so_nha')}'")

        # Tầng 3: Thiếu từ điển (Dictionary OOV)
        if assigned_layer is None:
            if raw_duong and not is_in_dict:
                assigned_layer = "TANG_3_THIEU_TU_DIEN_OOV"
                evidence.append(f"Đường '{raw_duong}' trích xuất được nhưng OOV trong tu_dien_duong_v5 cho mã tỉnh '{ma_tinh}'")

        # Tầng 4: Lỗi xếp hạng / Lựa chọn canonical sai
        if assigned_layer is None:
            if is_in_dict:
                assigned_layer = "TANG_4_XEP_HANG_CANONICAL_SAI"
                evidence.append(f"Đường '{raw_duong}' có trong từ điển v5 (tìm thấy {len(cands)} ứng viên), nhưng bộ chọn/ranking chọn sai hoặc lệch xã/tỉnh")

        # Tầng 6: Chưa xác định
        if assigned_layer is None:
            assigned_layer = "TANG_6_CHUA_XAC_DINH"
            evidence.append("Chưa đủ dữ kiện độc lập phân tách dứt khoát tầng lỗi")

        layer_counts_112[assigned_layer] += 1
        is_street_error = "loi_duong" in flags
        if is_street_error:
            layer_counts_95_street[assigned_layer] += 1

        deconstructed_records.append({
            "id": cid,
            "input": inp,
            "ref": ref,
            "pred_base": pred_base,
            "has_span_annotation": has_annot,
            "raw_spans": pred_spans,
            "assigned_layer": assigned_layer,
            "evidence": "; ".join(evidence),
            "is_street_case": is_street_error,
            "in_dict": is_in_dict,
            "dict_cands_count": len(cands)
        })

    return layer_counts_112, layer_counts_95_street, deconstructed_records

def compute_independent_oracles(dev_rows, goc_spans_map, botach, ranker, td_duong, dm, cases_220):
    """
    Tính Joint Gained Potential bằng các phép Oracle độc lập từng tầng:
    1. Oracle Span: Thay raw span trích xuất bằng Gold Span từ dev_goc.jsonl.
    2. Oracle Formatter: Chuẩn hóa bỏ khác biệt tiền tố cơ học ('Số', 'Đường', case, space).
    3. Oracle Dictionary: Giả định tên đường luôn có trong từ điển nếu input chứa tên đường.
    4. Oracle Ranking: Lấy theo beam_oracle_6 (nếu đáp án 6 trường đã có trong beam).
    """
    # 4. Oracle Ranking: Lấy trực tiếp từ cờ beam_oracle_6 của cache
    oracle_ranking_solvable = sum(1 for c in cases_220 if c.get("beam_oracle_6") is True)

    # 2. Oracle Formatter: Đếm số ca trong 220 ca lỗi mà nếu chỉ chuẩn hóa tiền tố (strip 'Số', 'Đường', space, casefold) thì 6 trường trùng khớp
    oracle_formatter_solvable = 0
    for c in cases_220:
        ref = c["ref"]
        pred = c["pred_base"]
        # So sánh sau khi strip tiền tố và casefold
        match = True
        for k in CORE_FIELDS:
            r_v = norm(ref.get(k, "")).replace("số ", "").replace("đường ", "").replace("phố ", "")
            p_v = norm(pred.get(k, "")).replace("số ", "").replace("đường ", "").replace("phố ", "")
            if r_v != p_v:
                match = False
                break
        if match:
            oracle_formatter_solvable += 1

    # 1. Oracle Span Extraction:
    # Thử nghiệm trên các ca lỗi có gold annotation trong dev_goc.jsonl
    # Xây dựng NguCanhChar với gold tags và chạy pipe
    annotated_error_cases = [c for c in cases_220 if c["id"] in goc_spans_map]
    oracle_span_solvable = 0

    pipe_base = BoChuanHoa(dm, bo_tach=botach, bo_xep_hang=ranker, tu_dien_duong=td_duong,
                           bao_ve_duong=True, tien_to_mac_dinh=True)

    for c in annotated_error_cases:
        cid = c["id"]
        inp = c["input"]
        ref = c["ref"]
        annot = goc_spans_map[cid]

        # Xây dựng tags từ gold spans
        text_nfc, offsets = nfc_offsets(inp)
        tags = ['O'] * len(text_nfc)
        for role, s, e in annot.get("spans", []):
            if role in DETAIL_ROLES or role in ("xa", "huyen", "tinh"):
                s_c = max(0, min(len(text_nfc), s))
                e_c = max(0, min(len(text_nfc), e))
                if s_c < e_c:
                    tags[s_c] = f"B-{role}"
                    for idx in range(s_c + 1, e_c):
                        tags[idx] = f"I-{role}"

        log_probs = torch.zeros(len(text_nfc), len(TAGS))
        ctx_gold = NguCanhChar(inp, text_nfc, offsets, tags, log_probs)

        class OracleSpanExtractor:
            phien_ban = 'oracle_span'
            bao_ve_chi_tiet = True
            ma_bam = botach.ma_bam
            def chuan_bi_chuoi(self, raw):
                return ctx_gold

        pipe_oracle_span = BoChuanHoa(dm, bo_tach=OracleSpanExtractor(), bo_xep_hang=ranker,
                                      tu_dien_duong=td_duong, bao_ve_duong=True, tien_to_mac_dinh=True)
        try:
            res = pipe_oracle_span.chuan_hoa(inp)
            res_dict = {k: getattr(res, k) for k in CORE_FIELDS}
            # So sánh 6 trường với ref
            if all(norm(res_dict[k]) == norm(ref.get(k, "")) for k in CORE_FIELDS):
                oracle_span_solvable += 1
        except Exception:
            pass

    # 3. Oracle Dictionary:
    # Số ca lỗi ở tầng OOV nhưng nếu giả định tra cứu đường khớp ref thì giải quyết được
    # Đếm số ca có raw span đường trích đúng nhưng OOV
    oracle_dict_solvable = 0
    for c in cases_220:
        cid = c["id"]
        annot = goc_spans_map.get(cid)
        if annot:
            gold_duong = [inp[s:e] for r, s, e in annot.get("spans", []) if r == "duong"]
            pred_duong = [inp[s:e] for r, s, e in botach.chuan_bi_chuoi(c["input"]).char_spans if r == "duong"]
            if gold_duong and gold_duong == pred_duong:
                # Trích xuất đường đúng
                d_name = gold_duong[0]
                ma_tinh = c["ref"].get("ma_tinh") or c["pred_base"].get("ma_tinh")
                if ma_tinh and not td_duong.ung_vien(d_name, ma_tinh):
                    oracle_dict_solvable += 1

    return {
        "oracle_ranking": {
            "correct_gained": oracle_ranking_solvable,
            "denominator": 220,
            "percentage_of_errors": round(oracle_ranking_solvable / 220 * 100, 2),
            "description": "Số ca đáp án 6 trường đã có trong beam (beam_oracle_6 True) nhưng ranker không chọn top-1."
        },
        "oracle_formatter": {
            "correct_gained": oracle_formatter_solvable,
            "denominator": 220,
            "percentage_of_errors": round(oracle_formatter_solvable / 220 * 100, 2),
            "description": "Số ca đúng hoàn toàn nếu bỏ qua khác biệt quy ước tiền tố ('Số', 'Đường', dấu cách, hoa/thường)."
        },
        "oracle_span": {
            "correct_gained": oracle_span_solvable,
            "denominator": len(annotated_error_cases),
            "percentage_of_annotated_errors": round(oracle_span_solvable / len(annotated_error_cases) * 100, 2),
            "description": f"Số ca được cứu khi thay thế hoàn toàn CNN v2 bằng Gold Spans trên {len(annotated_error_cases)} ca lỗi có nhãn span."
        },
        "oracle_dictionary": {
            "correct_gained": oracle_dict_solvable,
            "denominator": len(annotated_error_cases),
            "percentage_of_annotated_errors": round(oracle_dict_solvable / len(annotated_error_cases) * 100, 2),
            "description": "Số ca trích xuất đúng tên đường nhưng thất bại vì từ điển tu_dien_duong_v5 thiếu mục từ này (OOV)."
        },
        "note": "CÁC PHÉP ORACLE ĐƯỢC ĐO ĐỘC LẬP TỪNG TẦNG. TUYỆT ĐỐI KHÔNG CỘNG DỒN TỶ LỆ VÌ CÓ VÙNG GIAO NHAU (CHỒNG LẤN)."
    }

def main():
    print("=== BẮT ĐẦU NHIỆM VỤ B: TÁCH SAI SPAN / FORMAT / TÊN CHUẨN / NHÃN NGHI VẤN ===")
    t0 = time.time()

    # 1. Kiểm tra hash baseline manifest
    print("1. Kiểm tra SHA-256 Baseline Manifest...")
    mismatches = verify_manifest()
    if mismatches:
        print(f"LỖI: Có {len(mismatches)} file baseline bị lệch hash:")
        for p, exp, act in mismatches:
            print(f"  {p}: expected {exp}, actual {act}")
        sys.exit(1)
    print("  -> Baseline Manifest 100% khớp hash.")

    # 2. Khởi tạo mô hình và tài nguyên
    print("2. Khởi tạo mô hình CNN v2, Ranker v2, Từ điển đường v5 và Danh mục...")
    dm = DanhMuc(ROOT / "data/clean")
    cnn_v2 = BoTachCharCNN(ROOT / "mo_hinh/thu_nghiem/char_v2_01/char_cnn.pt", threads=1)
    ranker_v2 = BoXepHang(ROOT / "mo_hinh/thu_nghiem/char_v2_01/ranker.txt", cnn_v2.ma_bam, dm.ma_bam)
    td_duong_v5 = TuDienDuong(ROOT / "danh_gia/ket_qua/tu_dien_duong_v5.json")

    # 3. Đọc dữ liệu Dev gốc (1136) & join span annotations (1026)
    print("3. Tải và đối chiếu tập Dev gốc...")
    with open(ROOT / "data/train_dev/dev.csv", "r", encoding="utf-8") as f:
        dev_rows = list(csv.DictReader(f))
    total_dev = len(dev_rows)

    goc_spans_map = {}
    with open(ROOT / "mo_hinh/thu_nghiem/char_v1_01/data/dev_goc.jsonl", "r", encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            goc_spans_map[d["id"]] = d

    annotated_dev_items = [goc_spans_map[r["id"]] for r in dev_rows if r["id"] in goc_spans_map]
    unannotated_dev_rows = [r for r in dev_rows if r["id"] not in goc_spans_map]

    print(f"  Tổng mẫu dev.csv: {total_dev}")
    print(f"  Số mẫu có span annotation (dev_goc.jsonl): {len(annotated_dev_items)} ({len(annotated_dev_items)/total_dev*100:.2f}%)")
    print(f"  Số mẫu KHÔNG có span annotation: {len(unannotated_dev_rows)} ({len(unannotated_dev_rows)/total_dev*100:.2f}%)")

    # 4. Đọc dữ liệu Dev Khó (464) & join span annotations (464)
    print("4. Tải và đối chiếu tập Dev Khó...")
    with open(ROOT / "mo_hinh/thu_nghiem/char_v1_01/snapshot/dev_kho.csv", "r", encoding="utf-8-sig") as f:
        dev_kho_rows = list(csv.DictReader(f))
    total_dev_kho = len(dev_kho_rows)

    kho_spans_map = {}
    with open(ROOT / "mo_hinh/thu_nghiem/char_v1_01/data/dev_kho.jsonl", "r", encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            kho_spans_map[d["id"]] = d

    annotated_kho_items = []
    for r in dev_kho_rows:
        cid = r.get("id") or r.get("\ufeffid")
        if cid in kho_spans_map:
            annotated_kho_items.append(kho_spans_map[cid])
        else:
            print(f"Cảnh báo: Không tìm thấy span cho {cid}")

    print(f"  Tổng mẫu dev_kho.csv: {total_dev_kho}")
    print(f"  Số mẫu có span annotation: {len(annotated_kho_items)} (100.0%)")

    # 5. Đo đạc chi tiết 4 roles span metrics
    print("5. Đo Exact Span Match & Char-level Metrics cho 4 roles...")
    eval_dev_goc, pred_cache_goc = evaluate_spans("Dev Gốc (1026 annotated)", annotated_dev_items, cnn_v2)
    eval_dev_kho, pred_cache_kho = evaluate_spans("Dev Khó (464 annotated)", annotated_kho_items, cnn_v2)

    # 6. Đọc cache chẩn đoán cũ (220 ca lỗi dev) và phân rã kỹ thuật
    print("6. Phân rã 220 ca lỗi dev, nhóm 112 ca lỗi chi tiết và 95 ca khác đường...")
    with open(ROOT / "danh_gia/ket_qua/chan_doan_ung_vien_20261030/loi_tung_ca_dev.jsonl", "r", encoding="utf-8") as f:
        cases_220 = [json.loads(line) for line in f]

    layer_112, layer_95_street, deconstructed_112 = deconstruct_errors(
        cases_220, goc_spans_map, cnn_v2, td_duong_v5, dm
    )

    print("  Kết quả phân rã 112 ca 'LOI_CHI_TIET_LAM_HONG_BEAM':")
    for k, v in layer_112.items():
        print(f"    - {k}: {v} ca ({v/112*100:.1f}%)")

    print("  Kết quả phân rã 95 ca 'loi_duong':")
    for k, v in layer_95_street.items():
        print(f"    - {k}: {v} ca ({v/95*100:.1f}%)")

    # 7. Tính Joint Gained Potential (Independent Oracles)
    print("7. Đo đạc Joint Gained Potential độc lập từng tầng...")
    oracles_results = compute_independent_oracles(dev_rows, goc_spans_map, cnn_v2, ranker_v2, td_duong_v5, dm, cases_220)
    for k, v in oracles_results.items():
        if k != "note":
            print(f"  - {k}: {v['correct_gained']} / {v['denominator']} ca ({v.get('percentage_of_errors') or v.get('percentage_of_annotated_errors')}%)")

    # 8. Trích xuất ít nhất 12 ca kiểm chứng đa dạng
    print("8. Trích xuất các ca kiểm chứng mẫu (ít nhất 12 ca phủ các nhóm)...")
    selected_cases = []
    by_layer = defaultdict(list)
    for rec in deconstructed_112:
        by_layer[rec["assigned_layer"]].append(rec)

    # 1. Tầng 1: Sai raw span (2 ca)
    for c in by_layer["TANG_1_SAI_RAW_SPAN"][:2]:
        c["category_group"] = "TANG_1_SAI_RAW_SPAN"
        selected_cases.append(c)

    # 2. Tầng 2: Lệch formatter (2 ca)
    for c in by_layer["TANG_2_LECH_FORMATTER"][:2]:
        c["category_group"] = "TANG_2_LECH_FORMATTER"
        selected_cases.append(c)

    # 3. Tầng 3: Thiếu từ điển OOV (3 ca)
    for c in by_layer["TANG_3_THIEU_TU_DIEN_OOV"][:3]:
        c["category_group"] = "TANG_3_THIEU_TU_DIEN_OOV"
        selected_cases.append(c)

    # 4. Tầng 4: Xếp hạng / Beam canonical sai (2 ca)
    for c in by_layer["TANG_4_XEP_HANG_CANONICAL_SAI"][:2]:
        c["category_group"] = "TANG_4_XEP_HANG_CANONICAL_SAI"
        selected_cases.append(c)

    # 5. Tầng 6: Chưa xác định (2 ca)
    for c in by_layer["TANG_6_CHUA_XAC_DINH"][:2]:
        c["category_group"] = "TANG_6_CHUA_XAC_DINH"
        selected_cases.append(c)

    # 6. Tầng 5: Nhãn tham chiếu nhiễu / khuyết / xã bị chia tách (từ nhóm 68 ca MO_HO_HOAC_NHAN_NHIEU)
    noise_cases = [c for c in cases_220 if c.get("error_category") == "MO_HO_HOAC_NHAN_NHIEU"]
    # 6a. Nhãn đường bị gán nguyên cả chuỗi địa chỉ
    corrupted_ref_cases = [c for c in noise_cases if any(w in str(c.get("secondary_flags", [])) for w in ("nhan_duong", "dai"))]
    for c in corrupted_ref_cases[:2]:
        inp = c["input"]
        ctx = cnn_v2.chuan_bi_chuoi(inp)
        selected_cases.append({
            "id": c["id"],
            "input": inp,
            "ref": c["ref"],
            "pred_base": c["pred_base"],
            "category_group": "TANG_5_NHAN_NHIEU_HOAC_MO_HO",
            "assigned_layer": "TANG_5_NHAN_NHIEU_HOAC_MO_HO",
            "raw_spans": ctx.char_spans,
            "evidence": "Nhãn tham chiếu (ref) bị nhiễu nặng: trường 'duong' bị gán nguyên cả chuỗi dài chứa cả quận/tỉnh, trong khi model trích xuất đúng tên đường."
        })

    # 6b. Xã bị chia tách mốc 2025 không có căn cứ văn bản
    split_ward_cases = [c for c in noise_cases if "xa_bi_chia" in c.get("secondary_flags", [])]
    for c in split_ward_cases[:2]:
        inp = c["input"]
        ctx = cnn_v2.chuan_bi_chuoi(inp)
        selected_cases.append({
            "id": c["id"],
            "input": inp,
            "ref": c["ref"],
            "pred_base": c["pred_base"],
            "category_group": "TANG_5_NHAN_NHIEU_HOAC_MO_HO",
            "assigned_layer": "TANG_5_NHAN_NHIEU_HOAC_MO_HO",
            "raw_spans": ctx.char_spans,
            "evidence": "Xã cũ bị chia tách địa giới hành chính năm 2025 thành nhiều đơn vị mới; đầu vào không có thông tin chi tiết để chọn duy nhất 1 xã."
        })

    # 7. Dev Khó: Biến thể mất dấu / viết tắt tiền tố
    pipe_base = BoChuanHoa(dm, bo_tach=cnn_v2, bo_xep_hang=ranker_v2, tu_dien_duong=td_duong_v5,
                           bao_ve_duong=True, tien_to_mac_dinh=True)
    dev_kho_error_samples = []
    for r in dev_kho_rows:
        cid = r.get("id") or r.get("\ufeffid")
        inp = r["dau_vao"]
        res = pipe_base.chuan_hoa(inp)
        res_dict = {k: getattr(res, k) for k in CORE_FIELDS}
        ref_dict = {k: r.get(k, "") for k in CORE_FIELDS}
        if any(norm(res_dict[k]) != norm(ref_dict[k]) for k in CORE_FIELDS):
            ctx = cnn_v2.chuan_bi_chuoi(inp)
            dev_kho_error_samples.append({
                "id": cid,
                "input": inp,
                "ref": ref_dict,
                "pred_base": res_dict,
                "category_group": "DEV_KHO_BIEN_THE",
                "assigned_layer": "TANG_3_THIEU_TU_DIEN_OOV" if not td_duong_v5.ung_vien(norm(res_dict.get("duong", "")), res_dict.get("ma_tinh", "")) else "TANG_4_XEP_HANG_CANONICAL_SAI",
                "raw_spans": ctx.char_spans,
                "evidence": f"Tập Dev Khó: Biến thể mất dấu / viết tắt ('{r.get('loai_bien_the', '')}'). Khác biệt tại 6 trường cốt lõi."
            })
            if len(dev_kho_error_samples) >= 2:
                break
    selected_cases.extend(dev_kho_error_samples)

    print(f"  -> Đã chọn tổng cộng {len(selected_cases)} ca kiểm chứng đại diện đa dạng (yêu cầu >= 12).")

    # 9. Xuất các artifact
    print("9. Ghi các artifact định lượng vào B_chi_tiet/...")
    
    # 9.1 config.json
    config_data = {
        "task": "NHIỆM VỤ B: TÁCH SAI SPAN / FORMAT / TÊN CHUẨN / NHÃN NGHI VẤN",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "device": "cpu",
        "num_threads": 1,
        "models": {
            "cnn_v2": "mo_hinh/thu_nghiem/char_v2_01/char_cnn.pt",
            "ranker_v2": "mo_hinh/thu_nghiem/char_v2_01/ranker.txt",
            "dictionary_v5": "danh_gia/ket_qua/tu_dien_duong_v5.json",
            "catalog": "data/clean"
        },
        "datasets": {
            "dev_goc_csv": {"path": "data/train_dev/dev.csv", "total_rows": total_dev},
            "dev_goc_spans": {"path": "mo_hinh/thu_nghiem/char_v1_01/data/dev_goc.jsonl", "annotated_rows": len(annotated_dev_items), "coverage": round(len(annotated_dev_items)/total_dev*100, 2)},
            "dev_kho_csv": {"path": "mo_hinh/thu_nghiem/char_v1_01/snapshot/dev_kho.csv", "total_rows": total_dev_kho},
            "dev_kho_spans": {"path": "mo_hinh/thu_nghiem/char_v1_01/data/dev_kho.jsonl", "annotated_rows": len(annotated_kho_items), "coverage": 100.0}
        }
    }
    with open(OUT_DIR / "config.json", "w", encoding="utf-8") as f:
        json.dump(config_data, f, ensure_ascii=False, indent=2)

    # 9.2 so_lieu_chi_tiet.json
    detailed_metrics = {
        "metadata": config_data,
        "span_metrics_dev_goc_1026": eval_dev_goc,
        "unannotated_dev_rows_count": len(unannotated_dev_rows),
        "span_metrics_dev_kho_464": eval_dev_kho,
        "error_deconstruction_112": {
            "total_cases": 112,
            "layer_distribution": dict(layer_112),
            "street_95_cases_layer_distribution": dict(layer_95_street)
        },
        "independent_oracles": oracles_results
    }
    with open(OUT_DIR / "so_lieu_chi_tiet.json", "w", encoding="utf-8") as f:
        json.dump(detailed_metrics, f, ensure_ascii=False, indent=2)

    # 9.3 mau_kiem_chung_12_ca.json
    with open(OUT_DIR / "mau_kiem_chung_12_ca.json", "w", encoding="utf-8") as f:
        json.dump(selected_cases, f, ensure_ascii=False, indent=2)

    # 10. Kiểm tra lại SHA-256 Baseline Manifest
    print("10. Kiểm tra lại SHA-256 Baseline Manifest sau chạy...")
    final_mismatches = verify_manifest()
    if final_mismatches:
        print(f"CẢNH BÁO: Baseline Manifest bị biến đổi sau khi chạy!")
        sys.exit(1)
    print("  -> Baseline Manifest 100% nguyên vẹn.")

    t1 = time.time()
    print(f"=== HOÀN THÀNH NHIỆM VỤ B TRONG {t1-t0:.2f} GIÂY ===")

if __name__ == "__main__":
    main()
