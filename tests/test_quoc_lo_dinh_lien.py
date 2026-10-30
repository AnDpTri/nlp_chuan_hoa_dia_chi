"""QL3, TL298 viết dính được hiểu giống 'QL 3', 'TL 298'."""

import unittest

from src.dinh_dang import dinh_dang_span


def duong(tokens):
    return dinh_dang_span(tokens, 'duong')[0]


class QuocLoDinhLienTests(unittest.TestCase):
    def test_dinh_lien_giong_co_cach(self):
        self.assertEqual(duong(['Đ', '.', 'QL3']), 'Quốc lộ 3')
        self.assertEqual(duong(['QL18']), 'Quốc lộ 18')
        self.assertEqual(duong(['Đ', '.', 'TL298']), 'Tỉnh lộ 298')
        self.assertEqual(duong(['Đ', '.', 'QL', '5a']), duong(['Đ', '.', 'QL5a']))

    def test_suffix_chu_viet_hoa(self):
        self.assertEqual(duong(['QL14b']), 'Quốc lộ 14B')

    def test_ten_khac_khong_bi_doi(self):
        self.assertEqual(duong(['Đường', 'Lê', 'Lợi']), 'Đường Lê Lợi')
        self.assertEqual(duong(['Đ', '.', 'ĐCT05']), 'Đường ĐCT05')
        self.assertEqual(duong(['Đ', '.', 'QLX']), 'Đường Qlx')


if __name__ == '__main__':
    unittest.main()
