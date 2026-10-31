import unittest
import unicodedata
from src.tien_xu_ly.crf_chi_tiet import dinh_dang_span
from src.tien_xu_ly import token_co_vi_tri


class FormatTests(unittest.TestCase):
    def format(self, text, field='duong'):
        return dinh_dang_span([t.chu for t in token_co_vi_tri(text)], field)[0]

    def test_telex_chi_o_tien_to(self):
        for prefix in ('dduowngf', 'duowngf', 'dduwowngf', 'duwowngf', 'dduongf', 'duongf'):
            self.assertEqual(self.format(prefix + ' Hoa Binh'), 'Đường Hoa Binh')
        self.assertEqual(self.format('phoos Hòa Bình'), 'Phố Hòa Bình')
        self.assertEqual(self.format('Đường Tên Phoos'), 'Đường Tên Phoos')

    def test_duong_long_loai_tuyen_so(self):
        for raw in ('d. ql 8a', 'Đường quốc lộ 8a', 'đ. QL 8a'):
            self.assertEqual(self.format(raw), 'Quốc lộ 8A')
        self.assertEqual(self.format('Đường TL 10b'), 'Tỉnh lộ 10B')

    def test_khong_xoa_tu_loai_trong_ten_rieng(self):
        self.assertEqual(self.format('Đường Phố Mới'), 'Đường Phố Mới')
        self.assertEqual(self.format('Đường Quốc Lộ Xưa'), 'Đường Quốc Lộ Xưa')
        self.assertEqual(self.format('Đường Dương Quảng Hàm'), 'Đường Dương Quảng Hàm')

    def test_giu_dau_va_khong_fuzzy_bua(self):
        self.assertEqual(self.format('Duòng Hòa Bình'), 'Đường Duòng Hòa Bình')
        self.assertEqual(self.format('dduowngs Hòa Bình'), 'Đường Dduowngs Hòa Bình')
        self.assertEqual(self.format(unicodedata.normalize('NFD', 'Đường Hòa Bình')), 'Đường Hòa Bình')

    def test_khong_doi_so_nha(self):
        self.assertEqual(self.format('252Bis', 'so_nha'), 'Số 252Bis')


if __name__ == '__main__':
    unittest.main()
