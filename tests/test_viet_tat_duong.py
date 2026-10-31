"""Chữ viết tắt tên đường viết hoa không giải được thì để trống, không viết thường hóa thành tên giả."""

import unittest

from src.tien_xu_ly.phuc_hoi_duong import bo_duong_viet_tat_chua_giai


def span(tokens, a, b):
    return {'truong': 'duong', 'bat_dau': a, 'ket_thuc': b, 'gia_tri': 'x'}


class VietTatDuongTests(unittest.TestCase):
    def chay(self, chuoi, tokens, a, b, duong='Đường Ntt'):
        detail = {'duong': duong}
        sp = [span(tokens, a, b)]
        return bo_duong_viet_tat_chua_giai(detail, sp, tokens, chuoi)

    def test_viet_tat_viet_hoa_bi_bo(self):
        tokens = ['Số', '428', 'Đ', '.', 'NTT', ',', 'Thành', 'phố']
        detail, spans, da_bo = self.chay('Số 428 Đ. NTT, Thành phố', tokens, 2, 5)
        self.assertTrue(da_bo)
        self.assertEqual(detail['duong'], '')
        self.assertEqual(spans, [])

    def test_ten_thuong_khong_bi_bo(self):
        tokens = ['12', 'Đường', 'Lê', 'Lợi']
        detail, spans, da_bo = self.chay('12 Đường Lê Lợi', tokens, 1, 4, 'Đường Lê Lợi')
        self.assertFalse(da_bo)
        self.assertEqual(detail['duong'], 'Đường Lê Lợi')

    def test_ca_chuoi_viet_hoa_khong_la_dau_hieu_viet_tat(self):
        tokens = ['SỐ', '5', 'ĐƯỜNG', 'AN']
        detail, _, da_bo = self.chay('SỐ 5 ĐƯỜNG AN', tokens, 2, 4, 'Đường An')
        self.assertFalse(da_bo)
        self.assertEqual(detail['duong'], 'Đường An')

    def test_chu_viet_tat_co_so_khong_bi_bo(self):
        tokens = ['87', 'CMT8', ',', 'An', 'Hòa']
        detail, _, da_bo = self.chay('87 CMT8, An Hòa', tokens, 1, 2, 'Đường CMT8')
        self.assertFalse(da_bo)

    def test_nhieu_tu_khong_bi_bo(self):
        tokens = ['9', 'Đ', '.', 'NTT', 'Khai']
        _, _, da_bo = self.chay('9 Đ. NTT Khai', tokens, 1, 5, 'Đường Ntt Khai')
        self.assertFalse(da_bo)


if __name__ == '__main__':
    unittest.main()
