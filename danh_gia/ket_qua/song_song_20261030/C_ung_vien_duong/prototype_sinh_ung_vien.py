"""Prototype sinh đa ứng viên tên đường (Candidate Generation Prototype).
Không dùng / thêm / huấn luyện Transformer hay mô hình ngoài.
Phạm vi: C_ung_vien_duong (phiên làm việc song song C - 30/10/2026).

Nguyên tắc bắt buộc:
1. KHÔNG nhận hay sử dụng ref/nhãn tham chiếu trong logic sinh ứng viên.
2. Tối đa <= 8 ứng viên duy nhất cho mỗi mẫu.
3. Giữ nguyên nguồn gốc sinh (provenance) và độ tin cậy sơ bộ.
4. Bảo toàn độ mơ hồ khi có nhiều ứng viên hợp lệ từ từ điển.
"""

import re
import sys
import unicodedata
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Set, Tuple

from src.tien_xu_ly import token_co_vi_tri, bo_dau
from src.crf_chi_tiet import dinh_dang_span
from src.chuan_ten_duong import TuDienDuong, tach_ten, tuong_thich_dau, khoa


def chuan_hoa_chuoi(s: Optional[str]) -> str:
    """Chuẩn hóa NFC, loại bỏ khoảng trắng thừa, giữ nguyên dấu tiếng Việt."""
    if not s:
        return ""
    normalized = unicodedata.normalize("NFC", str(s))
    return " ".join(normalized.strip().split())


@dataclass
class UngVienDuong:
    text: str
    provenance: str
    is_canonical: bool = False
    tuong_thich_dau: bool = False
    confidence_tier: int = 3
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "provenance": self.provenance,
            "is_canonical": self.is_canonical,
            "tuong_thich_dau": self.tuong_thich_dau,
            "confidence_tier": self.confidence_tier,
            "metadata": self.metadata,
        }


# Regex nhận diện tiền tố đường/phố/tuyến bị dính chữ liền kề
RE_GLUED_PREFIX = re.compile(
    r"^(Đường|đường|Phố|phố|Đ\.|P\.|QL|ql|Quốc\s*lộ|Quoc\s*lo|Tỉnh\s*lộ|Tinh\s*lo|TL|tl|"
    r"Đại\s*lộ|Dai\s*lo|ĐL|dl|Hương\s*lộ|Huong\s*lo|HL|hl|Ngõ|ngõ|Ngách|ngách|Hẻm|hẻm)"
    r"([A-ZÀ-Ỹ0-9].*)$"
)

# Regex nhận diện số nhà dính tiền tố đường (ví dụ: 47/9ĐườngTrầnHưngĐạo)
RE_GLUED_HOUSE_STREET = re.compile(
    r"^(\d+[\d/A-Za-z-]*?)(Đường|đường|Phố|phố|Đ\.|P\.|QL|ql|TL|tl|HL|hl|ĐL|dl)([A-ZÀ-Ỹ0-9].*)$"
)

# Ký tự phân cách an toàn không vượt qua khi mở rộng unknown
PUNCT_STOPS = {",", ";", ".", "-", "/", ":"}


def tach_camel_case_viet(token: str) -> List[str]:
    """Tách CamelCase cho tiếng Việt dính chữ (ví dụ ĐườngPhạmVănThuận -> ['Đường', 'Phạm', 'Văn', 'Thuận'])."""
    parts = [t.chu for t in token_co_vi_tri(token)]
    if len(parts) > 1:
        return parts
    # Fallback dùng regex nếu token_co_vi_tri không tách được
    m = RE_GLUED_PREFIX.match(token)
    if m:
        prefix, rest = m.group(1), m.group(2)
        rest_parts = [t.chu for t in token_co_vi_tri(rest)]
        return [prefix] + rest_parts
    return [token]


class BoSinhUngVienDuong:
    """Bộ sinh đa ứng viên tên đường thuần quy tắc và lexicon tra cứu.
    Không dùng Transformer, chạy trực tiếp trên CPU cực nhẹ.
    """

    def __init__(self, tu_dien_duong: Optional[TuDienDuong] = None, max_candidates: int = 8):
        self.tu_dien_duong = tu_dien_duong
        self.max_candidates = max_candidates

    def sinh_ung_vien(
        self,
        raw_text: str,
        tokens: List[str],
        spans: List[Dict[str, Any]],
        unknown: List[int],
        context_admin: Optional[Dict[str, Any]] = None,
    ) -> List[UngVienDuong]:
        """Sinh danh sách ứng viên (tối đa <= 8) không dùng ref.

        Args:
            raw_text: Chuỗi địa chỉ đầu vào.
            tokens: Danh sách token phân tích.
            spans: Danh sách các span chi tiết từ model/pipeline.
            unknown: Danh sách index token chưa được gán nhãn.
            context_admin: Dict thông tin hành chính (cần nhất ma_tinh).

        Returns:
            List[UngVienDuong]: Tối đa <= max_candidates ứng viên đã deduplicate và xếp hạng sơ bộ.
        """
        ma_tinh = (context_admin.get("ma_tinh") or "").strip() if context_admin else ""
        unknown_set = set(unknown) if unknown else set()

        raw_candidates: List[UngVienDuong] = []

        duong_spans = [s for s in spans if s.get("truong") == "duong"]
        so_nha_spans = [s for s in spans if s.get("truong") == "so_nha"]

        # -------------------------------------------------------------
        # CHIẾN LƯỢC 1: SURFACE GỐC TỪ SPAN ĐƯỜNG HIỆN HÀNH
        # -------------------------------------------------------------
        surface_raw_str = ""
        surface_formatted_str = ""
        if duong_spans:
            d_start = duong_spans[0]["bat_dau"]
            d_end = duong_spans[-1]["ket_thuc"]
            span_toks = tokens[d_start:d_end]
            surface_raw_str = " ".join(span_toks)

            # Format surface gốc qua dinh_dang_span
            fmt_surface, _ = dinh_dang_span(span_toks, "duong", tien_to_mac_dinh=True)
            surface_formatted_str = chuan_hoa_chuoi(fmt_surface)

            if surface_formatted_str:
                raw_candidates.append(
                    UngVienDuong(
                        text=surface_formatted_str,
                        provenance="surface_exact",
                        is_canonical=False,
                        tuong_thich_dau=True,
                        confidence_tier=4,
                        metadata={"raw_span": surface_raw_str, "span_range": (d_start, d_end)},
                    )
                )

        # -------------------------------------------------------------
        # CHIẾN LƯỢC 2: TÁCH MARKER DÍNH CHỮ / DÍNH SỐ NHÀ
        # -------------------------------------------------------------
        glued_tokens_to_check = []
        if duong_spans:
            d_start = duong_spans[0]["bat_dau"]
            d_end = duong_spans[-1]["ket_thuc"]
            span_toks = tokens[d_start:d_end]
            if span_toks:
                glued_tokens_to_check.append((span_toks[0], d_start))

        # Kiểm tra thêm số nhà nếu số nhà dính marker đường (ví dụ: 47/9ĐườngTrầnHưngĐạo)
        if so_nha_spans:
            sn_end = so_nha_spans[-1]["ket_thuc"]
            sn_toks = tokens[so_nha_spans[0]["bat_dau"]:sn_end]
            if sn_toks:
                glued_tokens_to_check.append((sn_toks[-1], sn_end - 1))

        for tok, t_idx in glued_tokens_to_check:
            # 2a: Dính số nhà và đường: 47/9ĐườngTrầnHưngĐạo
            m_hs = RE_GLUED_HOUSE_STREET.match(tok)
            if m_hs:
                sn_part, marker_part, name_part = m_hs.groups()
                body_parts = tach_camel_case_viet(name_part)
                clean_street_cand = marker_part.capitalize() + " " + " ".join(body_parts)
                clean_street_cand = chuan_hoa_chuoi(clean_street_cand)

                # Tra từ điển với ma_tinh
                if self.tu_dien_duong and ma_tinh:
                    matches = self.tu_dien_duong.ung_vien(clean_street_cand, ma_tinh)
                    if not matches:
                        # Thử tra chỉ với phần tên
                        matches = self.tu_dien_duong.ung_vien(" ".join(body_parts), ma_tinh)

                    for m in matches:
                        raw_candidates.append(
                            UngVienDuong(
                                text=chuan_hoa_chuoi(m["gia_tri"]),
                                provenance="split_marker_canonical",
                                is_canonical=True,
                                tuong_thich_dau=m["tuong_thich_dau"],
                                confidence_tier=1 if m["tuong_thich_dau"] else 2,
                                metadata={"original_token": tok, "split_source": "house_street_glued"},
                            )
                        )

                # Sinh phương án raw đã bóc tách
                raw_candidates.append(
                    UngVienDuong(
                        text=clean_street_cand,
                        provenance="split_marker_raw",
                        is_canonical=False,
                        tuong_thich_dau=True,
                        confidence_tier=3,
                        metadata={"original_token": tok, "split_source": "house_street_glued"},
                    )
                )

            # 2b: Dính tiền tố đường: ĐườngPhạmVănThuận / PhốCầnThơ / QL1A
            split_parts = tach_camel_case_viet(tok)
            if len(split_parts) > 1:
                # Token bị dính liền và đã được tách thành nhiều từ
                reconstructed_street = " ".join(split_parts)
                # Đảm bảo có tiền tố hợp lý
                fmt_split, _ = dinh_dang_span(split_parts, "duong", tien_to_mac_dinh=True)
                fmt_split = chuan_hoa_chuoi(fmt_split)

                # Tra từ điển
                if self.tu_dien_duong and ma_tinh:
                    # Tra cả cụm đã format và cụm body
                    matches = self.tu_dien_duong.ung_vien(fmt_split, ma_tinh)
                    if not matches and len(split_parts) >= 2:
                        matches = self.tu_dien_duong.ung_vien(" ".join(split_parts[1:]), ma_tinh)

                    for m in matches:
                        raw_candidates.append(
                            UngVienDuong(
                                text=chuan_hoa_chuoi(m["gia_tri"]),
                                provenance="split_marker_canonical",
                                is_canonical=True,
                                tuong_thich_dau=m["tuong_thich_dau"],
                                confidence_tier=1 if m["tuong_thich_dau"] else 2,
                                metadata={"original_token": tok, "split_parts": split_parts},
                            )
                        )

                # Thêm phương án raw đã tách marker
                raw_candidates.append(
                    UngVienDuong(
                        text=fmt_split,
                        provenance="split_marker_raw",
                        is_canonical=False,
                        tuong_thich_dau=True,
                        confidence_tier=3,
                        metadata={"original_token": tok, "split_parts": split_parts},
                    )
                )

        # -------------------------------------------------------------
        # CHIẾN LƯỢC 3: MỞ RỘNG UNKNOWN KẾ CẬN AN TOÀN (BOUNDARY EXPANSION)
        # -------------------------------------------------------------
        if duong_spans and self.tu_dien_duong and ma_tinh:
            d_start = duong_spans[0]["bat_dau"]
            d_end = duong_spans[-1]["ket_thuc"]

            # 3a. Mở rộng sang phải (forward expansion)
            curr_cand_right = " ".join(tokens[d_start:d_end])
            idx_r = d_end
            step_r = 0
            while idx_r < len(tokens) and idx_r in unknown_set and tokens[idx_r] not in PUNCT_STOPS and step_r < 4:
                curr_cand_right = curr_cand_right + " " + tokens[idx_r]
                matches_r = self.tu_dien_duong.ung_vien(curr_cand_right, ma_tinh)
                for m in matches_r:
                    raw_candidates.append(
                        UngVienDuong(
                            text=chuan_hoa_chuoi(m["gia_tri"]),
                            provenance="boundary_expansion_canonical",
                            is_canonical=True,
                            tuong_thich_dau=m["tuong_thich_dau"],
                            confidence_tier=1 if m["tuong_thich_dau"] else 2,
                            metadata={"direction": "right", "expanded_tokens": tokens[d_end:idx_r + 1]},
                        )
                    )
                idx_r += 1
                step_r += 1

            # 3b. Mở rộng sang trái (backward expansion)
            curr_cand_left = " ".join(tokens[d_start:d_end])
            idx_l = d_start - 1
            step_l = 0
            while idx_l >= 0 and idx_l in unknown_set and tokens[idx_l] not in PUNCT_STOPS and step_l < 4:
                curr_cand_left = tokens[idx_l] + " " + curr_cand_left
                matches_l = self.tu_dien_duong.ung_vien(curr_cand_left, ma_tinh)
                for m in matches_l:
                    raw_candidates.append(
                        UngVienDuong(
                            text=chuan_hoa_chuoi(m["gia_tri"]),
                            provenance="boundary_expansion_canonical",
                            is_canonical=True,
                            tuong_thich_dau=m["tuong_thich_dau"],
                            confidence_tier=1 if m["tuong_thich_dau"] else 2,
                            metadata={"direction": "left", "expanded_tokens": tokens[idx_l:d_start]},
                        )
                    )
                idx_l -= 1
                step_l += 1

        # -------------------------------------------------------------
        # CHIẾN LƯỢC 4: GHÉP BOUNDARY SỐ NHÀ / SỐ ĐƯỜNG (HOUSE-STREET COLLISION)
        # -------------------------------------------------------------
        if duong_spans and so_nha_spans and self.tu_dien_duong and ma_tinh:
            d_start = duong_spans[0]["bat_dau"]
            d_end = duong_spans[-1]["ket_thuc"]
            sn_end = so_nha_spans[-1]["ket_thuc"]

            # Trường hợp số nhà liền kề đường và token cuối số nhà là số (ví dụ: 30 / 4)
            if sn_end == d_start and d_start - 1 >= 0:
                prev_tok = tokens[d_start - 1]
                if prev_tok.isdigit() or (len(prev_tok) <= 4 and any(c.isdigit() for c in prev_tok)):
                    combined_cand = " ".join(tokens[d_start - 1 : d_end])
                    matches = self.tu_dien_duong.ung_vien(combined_cand, ma_tinh)
                    for m in matches:
                        raw_candidates.append(
                            UngVienDuong(
                                text=chuan_hoa_chuoi(m["gia_tri"]),
                                provenance="house_number_boundary_canonical",
                                is_canonical=True,
                                tuong_thich_dau=m["tuong_thich_dau"],
                                confidence_tier=1 if m["tuong_thich_dau"] else 2,
                                metadata={"absorbed_token": prev_tok},
                            )
                        )

        # -------------------------------------------------------------
        # CHIẾN LƯỢC 5: CANONICAL NAMES TỪ TỪ ĐIỂN VỚI CONTEXT ADMIN
        # -------------------------------------------------------------
        if self.tu_dien_duong and ma_tinh:
            # Tra với surface_formatted_str và surface_raw_str
            queries = [q for q in [surface_formatted_str, surface_raw_str] if q]
            for q in queries:
                matches = self.tu_dien_duong.ung_vien(q, ma_tinh)
                for m in matches:
                    raw_candidates.append(
                        UngVienDuong(
                            text=chuan_hoa_chuoi(m["gia_tri"]),
                            provenance="admin_context_canonical",
                            is_canonical=True,
                            tuong_thich_dau=m["tuong_thich_dau"],
                            confidence_tier=1 if m["tuong_thich_dau"] else 2,
                            metadata={"query": q, "train_ids": m.get("train_ids", [])},
                        )
                    )

        # -------------------------------------------------------------
        # CHIẾN LƯỢC 6: UNKNOWN CLUSTER SCAN (KHI SPAN ĐƯỜNG RỖNG)
        # -------------------------------------------------------------
        if not duong_spans and unknown_set and self.tu_dien_duong and ma_tinh:
            u_sorted = sorted(unknown_set)
            # Gom các token unknown liên tiếp
            groups: List[List[int]] = []
            curr_g = [u_sorted[0]]
            for idx in u_sorted[1:]:
                if idx == curr_g[-1] + 1 and tokens[idx] not in PUNCT_STOPS:
                    curr_g.append(idx)
                else:
                    groups.append(curr_g)
                    curr_g = [idx]
            groups.append(curr_g)

            for g in groups:
                for start in range(len(g)):
                    for end in range(start + 1, min(start + 7, len(g) + 1)):
                        phrase = " ".join(tokens[g[k]] for k in range(start, end))
                        matches = self.tu_dien_duong.ung_vien(phrase, ma_tinh)
                        for m in matches:
                            raw_candidates.append(
                                UngVienDuong(
                                    text=chuan_hoa_chuoi(m["gia_tri"]),
                                    provenance="unknown_cluster_canonical",
                                    is_canonical=True,
                                    tuong_thich_dau=m["tuong_thich_dau"],
                                    confidence_tier=2 if m["tuong_thich_dau"] else 3,
                                    metadata={"unknown_phrase": phrase},
                                )
                            )

        # -------------------------------------------------------------
        # CHIẾN LƯỢC 7: EMPTY FALLBACK
        # -------------------------------------------------------------
        # Thêm ứng viên rỗng nếu chưa có gì hoặc span đường trống
        if not duong_spans or not raw_candidates:
            raw_candidates.append(
                UngVienDuong(
                    text="",
                    provenance="empty_fallback",
                    is_canonical=False,
                    tuong_thich_dau=True,
                    confidence_tier=5,
                    metadata={"reason": "no_duong_span_or_candidates"},
                )
            )

        # -------------------------------------------------------------
        # DEDUPLICATION & RANKING & PRUNING (<= max_candidates)
        # -------------------------------------------------------------
        dedup_dict: Dict[str, UngVienDuong] = {}

        # Sắp xếp raw_candidates để ưu tiên giữ bản ghi có confidence_tier thấp hơn (tốt hơn)
        # và tuong_thich_dau = True, is_canonical = True
        def sort_priority(c: UngVienDuong):
            return (
                c.confidence_tier,
                0 if c.tuong_thich_dau else 1,
                0 if c.is_canonical else 1,
            )

        sorted_raw = sorted(raw_candidates, key=sort_priority)

        for c in sorted_raw:
            norm_key = chuan_hoa_chuoi(c.text).casefold()
            if norm_key not in dedup_dict:
                dedup_dict[norm_key] = c
            else:
                # Nếu đã có, giữ lại bản ghi có confidence_tier tốt hơn
                existing = dedup_dict[norm_key]
                if sort_priority(c) < sort_priority(existing):
                    dedup_dict[norm_key] = c

        final_candidates = list(dedup_dict.values())
        final_candidates.sort(key=sort_priority)

        return final_candidates[: self.max_candidates]
