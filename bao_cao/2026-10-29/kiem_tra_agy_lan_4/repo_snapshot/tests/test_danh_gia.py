"""Kiểm tra cách chấm và rào chắn tập test, không sửa dữ liệu."""

import unittest
from danh_gia.chay_ban_thu import ROOT, field_metrics, align_detail, run


class EvaluationTests(unittest.TestCase):
    def test_truong_trong_khong_tang_recall_nhan(self):
        pairs = [({"duong": ""}, {"duong": ""}),
                 ({"duong": "Đường Lê Lợi"}, {"duong": ""}),
                 ({"duong": "Đường Lê Lợi"}, {"duong": "đường  lê lợi"})]
        m = field_metrics(pairs, "duong")
        self.assertEqual(m["dung"], 2)
        self.assertEqual(m["recall_nhan_khong_rong_pct"], 50)
        self.assertEqual(m["precision_du_doan_khong_rong_pct"], 100)

    def test_can_chinh_khong_noi_qua_dau_phay(self):
        self.assertEqual(align_detail("Le, Loi", "duong", "Đường Lê Lợi"), [])
        self.assertEqual(align_detail("12 Đ.LêLợi", "duong", "Đường Lê Lợi"), [[3, 5]])

    def test_can_chinh_nhieu_vi_tri(self):
        self.assertEqual(align_detail("12, ngõ 12", "so_nha", "Số 12"), [[0, 1], [3, 4]])

    def test_chan_tap_test_truoc_khi_doc_ghi(self):
        with self.assertRaisesRegex(ValueError, "không dùng tập test cuối"):
            run(ROOT / "data" / "test" / "khong_can_ton_tai.csv", ROOT / "khong_duoc_tao")


if __name__ == "__main__":
    unittest.main()
