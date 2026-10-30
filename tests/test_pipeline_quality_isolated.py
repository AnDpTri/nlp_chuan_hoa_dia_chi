"""Hồi quy cho nhánh pipeline-quality; chỉ dùng fixture độc lập, không đọc test cuối."""
import unittest
from types import SimpleNamespace

from src.chuan_hoa import _token_trong_span_ky_tu
from src.dinh_dang import dinh_dang_span
from src.tien_xu_ly import token_co_vi_tri


def fmt(text, field, default):
    tokens = [t.chu for t in token_co_vi_tri(text)]
    return dinh_dang_span(tokens, field, tien_to_mac_dinh=default)[0]


class TestHopDongDinhDang(unittest.TestCase):
    def test_so_nha_co_tien_to_ro_rang_khong_bi_xoa(self):
        self.assertEqual(fmt("Số 12B", "so_nha", False), "Số 12B")
        self.assertEqual(fmt("số 12", "so_nha", False), "Số 12")

    def test_khong_tu_them_tien_to_khi_da_tat(self):
        self.assertEqual(fmt("12B", "so_nha", False), "12B")
        self.assertEqual(fmt("12B", "so_nha", True), "Số 12B")

    def test_giu_tien_to_duong_khi_tat_tu_dong(self):
        self.assertEqual(fmt("Đường Lê Lợi", "duong", False), "Đường Lê Lợi")
        self.assertEqual(fmt("Lê Lợi", "duong", False), "Lê Lợi")


class TestCanChinhNeural(unittest.TestCase):
    def test_span_char_offset_khong_phu_thuoc_chi_so_token(self):
        # CNN tách 3 token, ViDeBERTa có thể tách 5 token.
        context = SimpleNamespace(labels=["O"] * 5, char_spans=[("duong", 6, 18)])
        tokens = [SimpleNamespace(bat_dau=0, ket_thuc=5),
                  SimpleNamespace(bat_dau=6, ket_thuc=10),
                  SimpleNamespace(bat_dau=11, ket_thuc=18)]
        self.assertFalse(_token_trong_span_ky_tu(context, tokens[0], "duong"))
        self.assertTrue(_token_trong_span_ky_tu(context, tokens[1], "duong"))
        self.assertTrue(_token_trong_span_ky_tu(context, tokens[2], "duong"))
        self.assertFalse(_token_trong_span_ky_tu(context, tokens[2], "xa"))

    def test_khong_lay_span_chi_phu_mot_phan_token(self):
        context = SimpleNamespace(char_spans=[("duong", 7, 12)])
        token = SimpleNamespace(bat_dau=6, ket_thuc=12)
        self.assertFalse(_token_trong_span_ky_tu(context, token, "duong"))


if __name__ == "__main__":
    unittest.main()
