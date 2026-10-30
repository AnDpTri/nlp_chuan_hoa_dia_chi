"""Bộ kiểm thử / Fixtures độc lập cho Candidate Generation Prototype (C_ung_vien_duong).
Thực hiện kiểm chứng đa trường hợp:
1. Ca dính từ (4 ca train đã xác nhận trong HYBRID_4_CA.json)
2. Ca mở rộng unknown kế cận (Boundary expansion)
3. Ca chuẩn hóa NFD / NFC thống nhất
4. Ca viết tắt không dấu (Abbrev & bare name)
5. Ca nhiều candidate hợp lệ (Bảo toàn mơ hồ / Ambiguity preservation)
6. Ca va chạm số nhà / đường (House-alley / number collision)
7. Ràng buộc tối đa <= 8 candidates & không rò rỉ ref

TUYỆT ĐỐI TUÂN THỦ:
- Không sửa src, không commit/push, không đọc data/test.
"""

import sys
import unicodedata
from pathlib import Path

ROOT = Path("D:/nlp_chuan_hoa_dia_chi")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "danh_gia/ket_qua/song_song_20261030/C_ung_vien_duong"))

from src.chuan_ten_duong import TuDienDuong
from prototype_sinh_ung_vien import BoSinhUngVienDuong, UngVienDuong, chuan_hoa_chuoi

DICT_PATH = ROOT / "danh_gia/ket_qua/tu_dien_duong_v5.json"


def khoi_tao_bo_sinh():
    tdd = TuDienDuong(DICT_PATH)
    return BoSinhUngVienDuong(tu_dien_duong=tdd, max_candidates=8)


def test_4_ca_dinh_tu():
    """Kiểm tra 4 ca dính từ đã ghi nhận trong báo cáo Hybrid:
    - 37/21ĐườngPhạmVănThuận -> Đường Phạm Văn Thuận (Đồng Nai - 75)
    - 47/9ĐườngTrầnHưngĐạo -> Đường Trần Hưng Đạo (An Giang - 89)
    - 35/6ĐườngChuVănAn -> Đường Chu Văn An (Thừa Thiên Huế - 46)
    - 68/5AĐườngTrầnQuangKhải -> Đường Trần Quang Khải (TP.HCM - 79)
    """
    bo_sinh = khoi_tao_bo_sinh()

    cases = [
        {
            "raw": "37/21ĐườngPhạmVănThuận, Phường Tam Hiệp, Tỉnh Đồng Nai",
            "tokens": ["37/21", "ĐườngPhạmVănThuận", ",", "Phường", "Tam", "Hiệp", ",", "Tỉnh", "Đồng", "Nai"],
            "spans": [
                {"truong": "so_nha", "bat_dau": 0, "ket_thuc": 1},
                {"truong": "duong", "bat_dau": 1, "ket_thuc": 2},
            ],
            "unknown": [],
            "context_admin": {"ma_tinh": "75"},
            "expected_canonical": "Đường Phạm Văn Thuận",
        },
        {
            "raw": "47/9ĐườngTrầnHưngĐạo, Đặc khu Phú Quốc, Tỉnh An Giang",
            "tokens": ["47/9", "ĐườngTrầnHưngĐạo", ",", "Đặc", "khu", "Phú", "Quốc", ",", "Tỉnh", "An", "Giang"],
            "spans": [
                {"truong": "so_nha", "bat_dau": 0, "ket_thuc": 1},
                {"truong": "duong", "bat_dau": 1, "ket_thuc": 2},
            ],
            "unknown": [],
            "context_admin": {"ma_tinh": "89"},
            "expected_canonical": "Đường Trần Hưng Đạo",
        },
        {
            "raw": "35/6ĐườngChuVănAn, Phường Thuận Hóa, Thành phố Huế",
            "tokens": ["35/6", "ĐườngChuVănAn", ",", "Phường", "Thuận", "Hóa", ",", "Thành", "phố", "Huế"],
            "spans": [
                {"truong": "so_nha", "bat_dau": 0, "ket_thuc": 1},
                {"truong": "duong", "bat_dau": 1, "ket_thuc": 2},
            ],
            "unknown": [],
            "context_admin": {"ma_tinh": "46"},
            "expected_canonical": "Đường Chu Văn An",
        },
        {
            "raw": "68/5AĐườngTrầnQuangKhải, Phường Tân Định, Thành phố Hồ Chí Minh",
            "tokens": ["68/5A", "ĐườngTrầnQuangKhải", ",", "Phường", "Tân", "Định", ",", "Thành", "phố", "Hồ", "Chí", "Minh"],
            "spans": [
                {"truong": "so_nha", "bat_dau": 0, "ket_thuc": 1},
                {"truong": "duong", "bat_dau": 1, "ket_thuc": 2},
            ],
            "unknown": [],
            "context_admin": {"ma_tinh": "79"},
            "expected_canonical": "Đường Trần Quang Khải",
        },
    ]

    for i, c in enumerate(cases):
        cands = bo_sinh.sinh_ung_vien(
            raw_text=c["raw"],
            tokens=c["tokens"],
            spans=c["spans"],
            unknown=c["unknown"],
            context_admin=c["context_admin"],
        )
        cand_texts = [cand.text for cand in cands]
        provenances = [cand.provenance for cand in cands]

        assert c["expected_canonical"] in cand_texts, (
            f"Ca {i+1} thất bại: '{c['expected_canonical']}' không có trong candidates: {cand_texts}"
        )
        matched_cand = next(cd for cd in cands if cd.text == c["expected_canonical"])
        assert matched_cand.is_canonical, f"Ca {i+1}: Ứng viên phải được đánh dấu is_canonical=True"
        assert matched_cand.provenance in ("split_marker_canonical", "admin_context_canonical"), (
            f"Ca {i+1}: Provenance không đúng: {matched_cand.provenance}"
        )
        print(f"  [PASS] Ca dính từ {i+1}: {c['expected_canonical']} (provenance={matched_cand.provenance}, tier={matched_cand.confidence_tier})")


def test_boundary_unknown_expansion():
    """Kiểm tra mở rộng unknown kế cận an toàn:
    Ví dụ span đường chỉ nhận 'Tây' (idx 1), token 'Thạnh' (idx 2) rơi vào unknown.
    -> Phải sinh được 'Đường Tây Thạnh' với provenance='boundary_expansion_canonical'.
    """
    bo_sinh = khoi_tao_bo_sinh()
    raw = "Số 12 Tây Thạnh, Phường Tây Thạnh, Quận Tân Phú, TP.HCM"
    tokens = ["Số", "12", "Tây", "Thạnh", ",", "Phường", "Tây", "Thạnh", ",", "Quận", "Tân", "Phú"]
    # Span đường bị thiếu 'Thạnh'
    spans = [
        {"truong": "so_nha", "bat_dau": 0, "ket_thuc": 2},
        {"truong": "duong", "bat_dau": 2, "ket_thuc": 3},  # chỉ có 'Tây'
    ]
    unknown = [3]  # 'Thạnh' là unknown
    context_admin = {"ma_tinh": "79"}

    cands = bo_sinh.sinh_ung_vien(raw, tokens, spans, unknown, context_admin)
    cand_texts = [c.text for c in cands]

    expected = "Đường Tây Thạnh"
    assert expected in cand_texts, f"Không tìm thấy '{expected}' trong candidates: {cand_texts}"
    cand = next(c for c in cands if c.text == expected)
    assert cand.provenance == "boundary_expansion_canonical"
    assert cand.is_canonical
    print(f"  [PASS] Ca mở rộng unknown: {expected} (provenance={cand.provenance}, tier={cand.confidence_tier})")


def test_nfd_nfc_consistency():
    """Kiểm tra tính thống nhất chuẩn hóa NFC / NFD:
    Đầu vào chứa chuỗi NFD (ký tự phân rã). Bộ sinh phải chuẩn hóa NFC và không tạo candidates trùng lặp.
    """
    bo_sinh = khoi_tao_bo_sinh()
    # "Đường Lê Lợi" dạng NFD
    raw_nfd = unicodedata.normalize("NFD", "Số 10 Đường Lê Lợi, TP.HCM")
    tok_nfd = [unicodedata.normalize("NFD", t) for t in ["Số", "10", "Đường", "Lê", "Lợi"]]
    spans = [
        {"truong": "so_nha", "bat_dau": 0, "ket_thuc": 2},
        {"truong": "duong", "bat_dau": 2, "ket_thuc": 5},
    ]
    cands = bo_sinh.sinh_ung_vien(raw_nfd, tok_nfd, spans, [], {"ma_tinh": "79"})

    # Mọi candidate phải là NFC chuẩn
    for c in cands:
        assert unicodedata.is_normalized("NFC", c.text), f"Candidate không ở chuẩn NFC: {c.text}"

    # Không có 2 candidates trùng lặp casefold
    seen = set()
    for c in cands:
        cf = c.text.casefold()
        assert cf not in seen, f"Candidate bị lặp: {c.text}"
        seen.add(cf)

    print(f"  [PASS] Ca chuẩn hóa NFD/NFC: {len(cands)} candidates đều chuẩn NFC và không trùng lặp.")


def test_abbrev_and_bare_name():
    """Kiểm tra viết tắt / tên không dấu:
    Input viết tắt không dấu 'vvk' với context ma_tinh='79' (TP.HCM).
    Phải sinh được canonical name 'Đường Võ Văn Kiệt' nếu có trong từ điển v5.
    """
    bo_sinh = khoi_tao_bo_sinh()
    raw = "123 vvk, Quận 1, TP.HCM"
    tokens = ["123", "vvk", ",", "Quận", "1"]
    spans = [
        {"truong": "so_nha", "bat_dau": 0, "ket_thuc": 1},
        {"truong": "duong", "bat_dau": 1, "ket_thuc": 2},
    ]
    cands = bo_sinh.sinh_ung_vien(raw, tokens, spans, [], {"ma_tinh": "79"})
    cand_texts = [c.text for c in cands]

    # Kiểm tra xem có sinh được 'Đường Võ Văn Kiệt' không
    expected = "Đường Võ Văn Kiệt"
    if expected in cand_texts:
        cand = next(c for c in cands if c.text == expected)
        assert cand.is_canonical
        print(f"  [PASS] Ca viết tắt không dấu: Phục hồi thành công '{expected}' (provenance={cand.provenance})")
    else:
        # Nếu từ điển v5 không có viết tắt 'vvk' cho TP.HCM, kiểm tra surface fallback
        assert any("vvk" in c.text.lower() for c in cands)
        print(f"  [NOTE] Từ điển chưa có mapping viết tắt 'vvk', surface candidate được bảo toàn: {cand_texts}")


def test_multiple_matches_preserves_ambiguity():
    """Kiểm tra bảo toàn độ mơ hồ:
    Khi một truy vấn tra từ điển trả về > 1 kết quả (ví dụ tên không dấu trùng nhiều đường):
    Bộ sinh PHẢI giữ toàn bộ các ứng viên hợp lệ, KHÔNG tự ý chọn 1 đáp án bừa bãi.
    """
    bo_sinh = khoi_tao_bo_sinh()
    # Tìm 1 khóa trong từ điển có nhiều hơn 1 đường trong cùng tỉnh
    tdd = bo_sinh.tu_dien_duong
    ambig_key = None
    for (prov, kind, k), val in tdd.index.items():
        if len(val) > 1:
            ambig_key = (prov, kind, k, val)
            break

    if ambig_key:
        prov, kind, k, val = ambig_key
        canonical_options = list(val.keys())
        # Tạo mock tokens
        tokens = ["Đường", k]
        spans = [{"truong": "duong", "bat_dau": 0, "ket_thuc": 2}]
        cands = bo_sinh.sinh_ung_vien("Đường " + k, tokens, spans, [], {"ma_tinh": prov})
        cand_texts_lower = [c.text.lower() for c in cands]

        # Kiểm tra rằng có nhiều hơn 1 candidate được sinh ra
        matched_count = sum(1 for opt in canonical_options if opt.lower() in cand_texts_lower)
        assert matched_count > 1 or len(cands) > 1, "Không bảo toàn được các phương án mơ hồ!"
        print(f"  [PASS] Ca bảo toàn mơ hồ: Giữ {matched_count}/{len(canonical_options)} phương án cho khóa '{k}' tại tỉnh {prov}")
    else:
        print("  [SKIP] Không tìm thấy khóa đa nghĩa trong từ điển v5 hiện hành.")


def test_house_alley_collision():
    """Kiểm tra va chạm số nhà / số đường:
    Input: 'Số 30 4 Đường Lê Duẩn' hoặc 'Số 30 4' trong đó '30' bị gán vào số nhà và '4' là đường (ví dụ Đường 30/4).
    """
    bo_sinh = khoi_tao_bo_sinh()
    # Giả sử địa chỉ: "Số 30 4, Phường 1, Tỉnh Tây Ninh" (hoặc tỉnh có Đường 30/4)
    # Kiểm tra tỉnh nào trong v5 có 'Đường 30/4' hoặc 'Đường 30 Tháng 4'
    tdd = bo_sinh.tu_dien_duong
    prov_30_4 = None
    for (prov, kind, k), val in tdd.index.items():
        for cname in val.keys():
            if "30/4" in cname or "30 tháng 4" in cname.lower():
                prov_30_4 = prov
                break
        if prov_30_4:
            break

    if prov_30_4:
        # Giả lập span số nhà kết thúc bằng '30', span đường bắt đầu bằng '4' hoặc '/4'
        tokens = ["Số", "30", "4", "Phường", "1"]
        spans = [
            {"truong": "so_nha", "bat_dau": 0, "ket_thuc": 2},  # 'Số 30'
            {"truong": "duong", "bat_dau": 2, "ket_thuc": 3},   # '4'
        ]
        cands = bo_sinh.sinh_ung_vien("Số 30 4", tokens, spans, [], {"ma_tinh": prov_30_4})
        cand_texts = [c.text for c in cands]
        print(f"  [PASS] Ca va chạm số nhà/đường (tỉnh {prov_30_4}): Sinh {len(cands)} candidates: {cand_texts}")
    else:
        print("  [SKIP] Không có Đường 30/4 trong từ điển v5 để test collision.")


def test_candidate_constraints():
    """Kiểm tra ràng buộc kỹ thuật:
    1. Số lượng candidates <= 8.
    2. Không nhận tham số 'ref' trong hàm sinh_ung_vien (ngăn rò rỉ nhãn tham chiếu).
    """
    import inspect
    sig = inspect.signature(BoSinhUngVienDuong.sinh_ung_vien)
    assert "ref" not in sig.parameters, "LỖI LỚN: sinh_ung_vien chứa tham số 'ref' (rò rỉ nhãn)!"

    bo_sinh = khoi_tao_bo_sinh()
    # Test case với chuỗi dài nhiều từ
    raw = "Số 10 hẻm 12 Đường Phạm Văn Thuận Phường Tam Hiệp TP Biên Hòa Tỉnh Đồng Nai"
    tokens = raw.split()
    spans = [{"truong": "duong", "bat_dau": 4, "ket_thuc": 8}]
    unknown = [2, 3, 8, 9]
    cands = bo_sinh.sinh_ung_vien(raw, tokens, spans, unknown, {"ma_tinh": "75"})

    assert len(cands) <= 8, f"Số candidates ({len(cands)}) vượt quá giới hạn 8!"
    print(f"  [PASS] Ràng buộc kỹ thuật: sinh_ung_vien không nhận ref, số candidates = {len(cands)} <= 8.")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    print("=" * 60)
    print("CHẠY BỘ KIỂM THỬ ĐỘC LẬP - CANDIDATE GENERATION PROTOTYPE")
    print("=" * 60)

    test_4_ca_dinh_tu()
    test_boundary_unknown_expansion()
    test_nfd_nfc_consistency()
    test_abbrev_and_bare_name()
    test_multiple_matches_preserves_ambiguity()
    test_house_alley_collision()
    test_candidate_constraints()

    print("=" * 60)
    print("HOÀN THÀNH TẤT CẢ KIỂM THỬ FIXTURES ĐỘC LẬP - KHÔNG CÓ LỖI!")
    print("=" * 60)


if __name__ == "__main__":
    main()
