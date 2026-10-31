"""Kiểm thử cấu trúc thành phần nhận diện (thanh_phan) và kết quả hai dòng (ket_qua_hai_dong).
Tuân thủ đầy đủ mục D trong yêu cầu:
1. "313, NGUYỄN VĂN LINH, PHƯỜNG AN KHÁNH, QUẬN NINH KIỀU, THÀNH PHỐ CẦN THƠ":
   - Có so_nha ("Số 313")
   - Có duong ("Đường Nguyễn Văn Linh")
   - Có xa (đối chiếu có, ket_qua_moi là đơn vị mới: "Phường Tân An" / "Phường Ninh Kiều")
   - Có huyen ("Không còn cấp huyện")
   - Có tinh ("Thành phố Cần Thơ")
2. Câu có số điện thoại => phần số điện thoại là bo_qua.
3. Nối các doan_goc theo bat_dau/ket_thuc phải nằm đúng trong input và không chồng lấn.
4. Câu có xã bị chia tách => ket_qua_moi của xã trống (""), ly_do nêu rõ xã bị chia.
"""

import sys
import os
import json
import unittest
from pathlib import Path

# Thiết lập đường dẫn
TESTS_DIR = Path(__file__).resolve().parent
API_DIR = TESTS_DIR.parent
PROJECT_ROOT = API_DIR.parent.parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from engine import NlpEngineAdapter


class TestThanhPhanVaHaiDong(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = NlpEngineAdapter.get_instance()
        assert cls.engine.is_ready(), "NLP Engine chưa sẵn sàng!"

    def test_01_can_tho_full_breakdown(self):
        """(1) Địa chỉ Cần Thơ đầy đủ 5 cấp nhận diện."""
        addr = "313, NGUYỄN VĂN LINH, PHƯỜNG AN KHÁNH, QUẬN NINH KIỀU, THÀNH PHỐ CẦN THƠ"
        res_dict, elapsed_ms, status = self.engine.normalize(addr)

        thanh_phan = res_dict.get("thanh_phan", [])
        hai_dong = res_dict.get("ket_qua_hai_dong", {})

        self.assertGreater(len(thanh_phan), 0, "thanh_phan không được rỗng")

        nhan_map = {item["nhan_la"]: item for item in thanh_phan}

        # 1. Có so_nha
        self.assertIn("so_nha", nhan_map, "Thiếu thành phần so_nha")
        self.assertEqual(nhan_map["so_nha"]["doan_goc"], "313")
        self.assertEqual(nhan_map["so_nha"]["chuan_hoa"], "Số 313")
        self.assertEqual(nhan_map["so_nha"]["doi_chieu"], "khong")

        # 2. Có duong
        self.assertIn("duong", nhan_map, "Thiếu thành phần duong")
        self.assertEqual(nhan_map["duong"]["doan_goc"], "NGUYỄN VĂN LINH")
        self.assertEqual(nhan_map["duong"]["chuan_hoa"], "Đường Nguyễn Văn Linh")
        self.assertEqual(nhan_map["duong"]["doi_chieu"], "khong")

        # 3. Có xa (đối chiếu có, ket_qua_moi là đơn vị mới)
        self.assertIn("xa", nhan_map, "Thiếu thành phần xa")
        xa_item = nhan_map["xa"]
        self.assertEqual(xa_item["doi_chieu"], "co")
        # Phường An Khánh cũ tại Cần Thơ theo dữ liệu sáp nhập vào Phường Tân An
        self.assertIn(xa_item["ket_qua_moi"], ("Phường Tân An", "Phường Ninh Kiều"))
        self.assertTrue(len(xa_item["ly_do"]) > 0, "Cần có câu tiếng Việt giải thích lý do")

        # 4. Có huyen ("Không còn cấp huyện")
        self.assertIn("huyen", nhan_map, "Thiếu thành phần huyen")
        huyen_item = nhan_map["huyen"]
        self.assertEqual(huyen_item["doi_chieu"], "co")
        self.assertEqual(huyen_item["ket_qua_moi"], "Không còn cấp huyện")

        # 5. Có tinh
        self.assertIn("tinh", nhan_map, "Thiếu thành phần tinh")
        tinh_item = nhan_map["tinh"]
        self.assertEqual(tinh_item["doi_chieu"], "co")
        self.assertEqual(tinh_item["ket_qua_moi"], "Thành phố Cần Thơ")

        # Kiểm tra hai dòng kết quả
        self.assertIn("co_doi_chieu", hai_dong)
        self.assertIn("thieu_du_lieu_doi_chieu", hai_dong)
        self.assertIn("Thành phố Cần Thơ", hai_dong["co_doi_chieu"]["chuoi"])
        self.assertIn("Số 313", hai_dong["thieu_du_lieu_doi_chieu"]["chuoi"])
        self.assertIn("Đường Nguyễn Văn Linh", hai_dong["thieu_du_lieu_doi_chieu"]["chuoi"])

    def test_02_phone_number_labeled_bo_qua(self):
        """(2) Câu chứa số điện thoại => phần số điện thoại được gắn nhãn bo_qua."""
        addr = "Số 10 Lê Lợi, Phường Bến Nghé, Quận 1, TP Hồ Chí Minh, ĐT: 0901234567"
        res_dict, elapsed_ms, status = self.engine.normalize(addr)

        thanh_phan = res_dict.get("thanh_phan", [])
        bo_qua_items = [item for item in thanh_phan if item["nhan_la"] == "bo_qua"]

        self.assertGreater(len(bo_qua_items), 0, "Cần có ít nhất một phần tử nhãn bo_qua")
        # Kiểm tra đoạn chữ chứa số điện thoại
        phone_found = any("0901234567" in item["doan_goc"] for item in bo_qua_items)
        self.assertTrue(phone_found, "Số điện thoại '0901234567' phải nằm trong phần tử nhãn bo_qua")

        for item in bo_qua_items:
            self.assertEqual(item["doi_chieu"], "bo_qua")
            self.assertEqual(item["chuan_hoa"], "")
            self.assertEqual(item["ket_qua_moi"], "")
            self.assertIn("Không thuộc địa chỉ", item["ly_do"])

    def test_03_span_offsets_and_no_overlaps(self):
        """(3) Nối các doan_goc theo bat_dau/ket_thuc phải nằm đúng trong input và không chồng lấn."""
        test_sentences = [
            "313, NGUYỄN VĂN LINH, PHƯỜNG AN KHÁNH, QUẬN NINH KIỀU, THÀNH PHỐ CẦN THƠ",
            "Số 10 Lê Lợi, Phường Bến Nghé, Quận 1, TP Hồ Chí Minh, ĐT: 0901234567",
            "45 XÔ VIẾT NGHỆ TĨNH P.AN CƯ- NINH KIỀU- CẦN THƠ",
            "Thôn 4, Xã Hoằng Lộc, Huyện Hoằng Hóa, Tỉnh Thanh Hóa",
            "110A CMT8, Phường An Thới, Quận Bình Thủy, TP Cần Thơ",
        ]

        for s in test_sentences:
            res_dict, _, _ = self.engine.normalize(s)
            thanh_phan = res_dict.get("thanh_phan", [])
            self.assertGreater(len(thanh_phan), 0, f"thanh_phan của '{s}' rỗng")

            # 1. Kiểm tra vị trí cắt chuỗi nguyên văn
            for item in thanh_phan:
                start = item["bat_dau"]
                end = item["ket_thuc"]
                extracted = s[start:end]
                self.assertEqual(
                    extracted,
                    item["doan_goc"],
                    f"Sai lệch vị trí cắt trong câu '{s}': '{extracted}' != '{item['doan_goc']}' tại [{start}:{end}]",
                )

            # 2. Kiểm tra tính thứ tự và không chồng lấn
            for i in range(len(thanh_phan) - 1):
                prev_item = thanh_phan[i]
                next_item = thanh_phan[i + 1]
                self.assertLessEqual(
                    prev_item["ket_thuc"],
                    next_item["bat_dau"],
                    f"Chồng lấn span trong câu '{s}': [{prev_item['bat_dau']}:{prev_item['ket_thuc']}] vs [{next_item['bat_dau']}:{next_item['ket_thuc']}]",
                )

    def test_04_split_ward_ambiguity(self):
        """(4) Câu có xã bị chia tách => ket_qua_moi của xã trống (""), ly_do nêu rõ chia."""
        # Xã An Khánh, Hoài Đức, Hà Nội bị chia thành nhiều xã/phường mới
        addr = "Xã An Khánh, Huyện Hoài Đức, Hà Nội"
        res_dict, elapsed_ms, status = self.engine.normalize(addr)

        thanh_phan = res_dict.get("thanh_phan", [])
        xa_items = [item for item in thanh_phan if item["nhan_la"] == "xa"]

        self.assertGreater(len(xa_items), 0, "Cần nhận diện được đơn vị cấp xã")
        xa_item = xa_items[0]

        # Xã bị chia tách: ket_qua_moi phải để trống theo hợp đồng chống hallucination
        self.assertEqual(xa_item["ket_qua_moi"], "", "Xã bị chia tách không được đoán mò ket_qua_moi")
        self.assertIn("chia", xa_item["ly_do"].lower(), f"Lý do phải nêu rõ việc bị chia tách: '{xa_item['ly_do']}'")
        self.assertEqual(xa_item["doi_chieu"], "co")


if __name__ == "__main__":
    print("=" * 65)
    print("CHẠY BỘ KIỂM THỬ THANH_PHAN & KET_QUA_HAI_DONG (Address May Cry)")
    print("=" * 65)
    unittest.main(verbosity=2)
