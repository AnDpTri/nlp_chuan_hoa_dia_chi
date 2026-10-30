"""Viết tắt tiền tố chi tiết (sn, h., k, kp...) được mở rộng khi span đã biết là trường nào."""

import unittest

from src.tien_xu_ly.dinh_dang import dinh_dang_span
from src.tien_xu_ly.tien_xu_ly import tach_token


def dd(text, field):
    return dinh_dang_span(tach_token(text), field)[0]


class VietTatChiTietTests(unittest.TestCase):
    def test_so_nha(self):
        self.assertEqual(dd('sn384', 'so_nha'), 'Số 384')
        self.assertEqual(dd('SN 58/51', 'so_nha'), 'Số 58/51')
        self.assertEqual(dd('so315/36', 'so_nha'), 'Số 315/36')

    def test_ngo_hem_kiet(self):
        self.assertEqual(dd('h.184', 'ngo_ngach_hem'), 'Hẻm 184')
        self.assertEqual(dd('h18', 'ngo_ngach_hem'), 'Hẻm 18')
        self.assertEqual(dd('k98', 'ngo_ngach_hem'), 'Kiệt 98')

    def test_thon_xom(self):
        self.assertEqual(dd('kp14', 'thon_xom'), 'Khu phố 14')

    def test_khong_doi_khi_khong_phai_viet_tat(self):
        self.assertEqual(dd('Số 12', 'so_nha'), 'Số 12')
        self.assertEqual(dd('Hồng 5', 'thon_xom'), 'Hồng 5')
        self.assertEqual(dd('h', 'ngo_ngach_hem'), 'H')


if __name__ == '__main__':
    unittest.main()
