"""Hồi quy theo cấu trúc lỗi: dấu, ranh giới tên, dấu nháy và cụm số.

Các chuỗi kiểm tra được viết tay, không bổ sung vào train/dev hoặc test cuối.
"""

import unittest
import unicodedata

from src.chuan_hoa import BoChuanHoa
from src.tien_xu_ly import token_co_vi_tri, tach_token
from src.tien_xu_ly.tim_kiem import sinh_ung_vien, so_dau_mau_thuan


class PipelineV3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bo = BoChuanHoa()

    def test_dau_da_nhap_phan_biet_hai_ten_cung_khoa(self):
        for name, expected in [('Tam Đàn', '20364'), ('Tam Dân', '20392')]:
            for nfd in (False, True):
                text = f'Xã {name}, Huyện Phú Ninh, Tỉnh Quảng Nam'
                if nfd:
                    text = unicodedata.normalize('NFD', text)
                with self.subTest(name=name, nfd=nfd):
                    r = self.bo.chuan_hoa(text)
                    self.assertEqual(r.ma_xa, expected)
                    self.assertNotIn('nhieu_cach_hieu', r.canh_bao)

    def test_thieu_dau_van_giu_cac_kha_nang(self):
        r = self.bo.chuan_hoa('Xa Tam Dan, Huyen Phu Ninh, Tinh Quang Nam')
        self.assertEqual(r.ma_xa, '')
        self.assertTrue({'20364', '20392'} <= {x['ma_xa'] for x in r.xa_moi_ung_vien})
        self.assertEqual(so_dau_mau_thuan('Tam Dan', 'Tam Đàn'), 0)
        self.assertEqual(so_dau_mau_thuan('Tam Đàn', 'Tam Dân'), 2)
        self.assertEqual(so_dau_mau_thuan('Sài Gòn', 'Hồ Chí Minh'), 0)

    def test_khong_ep_moc_moi_khi_ten_cu_moi_deu_hop_le(self):
        r = self.bo.chuan_hoa('Xã Lam Sơn, Tỉnh Thanh Hóa')
        self.assertEqual(r.ma_xa, '')
        self.assertTrue({'15124', '15544'} <= {x['ma_xa'] for x in r.xa_moi_ung_vien})

    def test_ten_day_du_co_so_khong_bi_cat_mat_duoi(self):
        for text in ('Xã Cát Tiên 2, Tỉnh Lâm Đồng', 'Tỉnh Lâm Đồng, Xã Cát Tiên 2',
                     'X. Cat Tien 2, T. Lam Dong'):
            with self.subTest(text=text):
                r = self.bo.chuan_hoa(text)
                self.assertEqual(r.ma_xa, '25180')
                self.assertEqual(r.so_nha, '')
        self.assertEqual(self.bo.chuan_hoa('Xã Cát Tiên, Tỉnh Lâm Đồng').ma_xa, '25159')
        # Nhánh ngắn còn được giữ để decoder có thể xét ngữ cảnh khác.
        us = sinh_ung_vien(tach_token('Xã Cát Tiên 2'), self.bo.trie)
        self.assertTrue(any(u.cay == 'moi' and u.ma == '25159' for u in us))
        self.assertTrue(any(u.cay == 'moi' and u.ma == '25180' for u in us))

    def test_dau_nhay_noi_ten_va_giu_offset_unicode(self):
        for quote in ("'", '’', 'ʼ'):
            text = unicodedata.normalize('NFD', f'Thị trấn M{quote}Drắk, Huyện M{quote}Đrắk, Tỉnh Đắk Lắk')
            with self.subTest(quote=quote):
                r = self.bo.chuan_hoa(text)
                self.assertEqual(r.ma_xa, '24412')
                for span in r.dau_vet:
                    self.assertEqual(span['doan_goc'], text[span['ky_tu_bat_dau']:span['ky_tu_ket_thuc']])
        self.assertEqual(tach_token("'D’Ran'"), ["'", 'D’Ran', "'"])

    def test_dau_nhay_khong_thanh_tien_to_duong(self):
        for quote in ("'", '’', 'ʼ'):
            r = self.bo.chuan_hoa(f'129, Quốc lộ 27, D{quote}Ran, Đơn Dương, Lâm Đồng')
            with self.subTest(quote=quote):
                self.assertEqual(r.ma_xa, '24934')
                self.assertEqual(r.duong, 'Quốc lộ 27')

    def test_bao_toan_cum_so_nha_va_canh_bao(self):
        for raw, expected in [('154-156', '154-156'), ('24B - 24', '24B-24'),
                              ('46–48–50–52', '46-48-50-52'), ('12/5—12/7', '12/5-12/7'),
                              ('1031F;1031G', '1031F;1031G')]:
            for prefix in ('', 'Số '):
                text = f'{prefix}{raw}, Đường Lê Lợi'
                with self.subTest(text=text):
                    r = self.bo.chuan_hoa(text)
                    self.assertEqual(r.so_nha, 'Số '+expected)
                    self.assertEqual(r.duong, 'Đường Lê Lợi')
                    self.assertIn('so_nha_can_duyet', r.canh_bao)
                    span = next(s for s in r.dau_vet if s['truong'] == 'so_nha')
                    self.assertEqual(span['doan_goc'], prefix+raw)

    def test_khong_lay_so_trong_ten_duong_lam_so_nha(self):
        r = self.bo.chuan_hoa('73, Đường số 27, Phường An Lạc, Thành phố Hồ Chí Minh')
        self.assertEqual(r.so_nha, 'Số 73')
        self.assertEqual(r.duong, 'Đường Số 27')
        self.assertEqual(self.bo.chuan_hoa('Đường số 27').so_nha, '')
        self.assertEqual(self.bo.chuan_hoa('843M+RH3, Tây Ninh').so_nha, '')

    def test_lo_tap_the_khu_dan_cu_khong_tu_thanh_duong(self):
        for rest in ('Lô 2 tập thể Viện Kỹ thuật quân sự', 'Lo 2 tap the Vien Ky thuat',
                     'Khu đô thị Hòa Bình', 'Khu dân cư Hòa Bình', 'Căn hộ Hoa Mai'):
            with self.subTest(rest=rest):
                r = self.bo.chuan_hoa('Số 1, '+rest)
                self.assertEqual(r.duong, '')
                self.assertNotEqual(r.phan_chua_phan_loai, '')
        r = self.bo.chuan_hoa('Số 1, Lô 2 tập thể, Đường Lê Lợi')
        self.assertEqual(r.duong, 'Đường Lê Lợi')

    def test_chan_suy_duong_khong_chan_ten_khac_dau(self):
        for name in ('Lò Đúc', 'Tăng Bạt Hổ', 'Đội Cấn', 'Điện Biên Phủ'):
            with self.subTest(name=name):
                # Có ngữ cảnh để loại cách hiểu tên xã/phường trùng tên đường.
                text = '12 '+name+', Phường Trúc Bạch, Quận Ba Đình, Hà Nội'
                self.assertEqual(self.bo.chuan_hoa(text).duong, 'Đường '+name)

    def test_ma_dau_cum_ten_khong_bi_chan_chi_vi_co_so(self):
        r = self.bo.chuan_hoa('23B, K18 Nguyen Van Thoai, Đà Nẵng')
        self.assertEqual(r.duong, 'Đường K18 Nguyen Van Thoai')
        # Giữ cách hiểu tạm và cảnh báo; không tự mở K18 thành tên chính thức.
        self.assertIn('duong_suy_tu_vi_tri', r.canh_bao)
        r = self.bo.chuan_hoa('9, Khu dân cư số 9, Xuân Khánh, Ninh Kiều, Cần Thơ')
        self.assertEqual(r.duong, '')
        self.assertIn('Khu dân cư', r.phan_chua_phan_loai)


if __name__ == '__main__':
    unittest.main()
