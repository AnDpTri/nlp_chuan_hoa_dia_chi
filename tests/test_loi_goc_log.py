"""Hồi quy cho các lỗi gốc tìm được từ nhật ký web (31/10/2026), chạy với mô hình đang dùng char_v3_tc."""

import unittest
from pathlib import Path

from src.danh_muc import DanhMuc
from src.chuan_hoa import BoChuanHoa

GOC = Path(__file__).resolve().parent.parent
MO_HINH = GOC / 'mo_hinh' / 'thu_nghiem' / 'char_v3_tc'
TU_DIEN = GOC / 'danh_gia' / 'ket_qua' / 'tu_dien_duong_v5.json'


@unittest.skipUnless((MO_HINH / 'char_cnn.pt').exists() and TU_DIEN.exists(), 'thiếu mô hình char_v3_tc')
class LoiGocLogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from src.tien_xu_ly.char_cnn import BoTachCharCNN
        from src.tien_xu_ly.xep_hang import BoXepHang
        from src.tien_xu_ly.chuan_ten_duong import TuDienDuong
        dm = DanhMuc()
        cnn = BoTachCharCNN(MO_HINH / 'char_cnn.pt', threads=1)
        cls.bo = BoChuanHoa(danh_muc=dm, bo_tach=cnn, bo_xep_hang=BoXepHang(MO_HINH / 'ranker.txt', cnn.ma_bam, dm.ma_bam),
                            tu_dien_duong=TuDienDuong(TU_DIEN), bao_ve_duong=True, tien_to_mac_dinh=True)

    def test_tinh_khop_dung_khong_thanh_ten_duong(self):
        # 'Hà Nội' được CRF gán tỉnh và khớp đúng tỉnh: không được khôi phục thành 'Đường Hà Nội'.
        r = self.bo.chuan_hoa('Số 5 ngõ 12, Phường Ngọc Hà, Quận Ba Đình, Hà Nội - 0912345678')
        self.assertEqual(r.duong, '')
        self.assertEqual(r.ma_tinh, '01')

    def test_so_dien_thoai_cuoi_cau_khong_lam_mat_tinh(self):
        # Ranker bỏ 'Hà Nội'/'THÀNH PHỐ CẦN THƠ' vì bỏ hay giữ đều ra cùng mã; giả thuyết mở rộng nhất quán giữ lại.
        for cau, ma_tinh in [('Số 5 ngõ 12, Phường Ngọc Hà, Quận Ba Đình, Hà Nội - 0912345678', '01'),
                             ('313, NGUYỄN VĂN LINH, PHƯỜNG AN KHÁNH, QUẬN NINH KIỀU, THÀNH PHỐ CẦN THƠ - 0909123456', '92')]:
            r = self.bo.chuan_hoa(cau)
            self.assertEqual(r.ma_tinh, ma_tinh, cau)
            self.assertNotIn('thieu_tinh_dau_vao', r.canh_bao, cau)
            self.assertNotIn('mau_thuan_hanh_chinh', r.canh_bao, cau)
            self.assertTrue(r.phan_chua_phan_loai.isdigit(), (cau, r.phan_chua_phan_loai))

    def test_duong_khoi_phuc_co_dau_vet_va_khong_con_chua_phan_loai(self):
        # 'Hoàng Văn Thụ' gán nhầm là xã (không có xã đó ở Cần Thơ) -> được khôi phục thành tên đường,
        # và phải có dấu vết + không còn nằm trong phần chưa phân loại.
        r = self.bo.chuan_hoa('45B Hoàng Văn Thụ Ninh Kiều Cần Thơ')
        self.assertEqual(r.duong, 'Đường Hoàng Văn Thụ')
        self.assertEqual(r.phan_chua_phan_loai, '')
        self.assertNotIn('phan_chua_phan_loai', r.canh_bao)
        self.assertIn(('duong', 'Hoàng Văn Thụ'), [(d['truong'], d['doan_goc']) for d in r.dau_vet])

    def test_khop_gan_dung_khong_cam_ten_duong(self):
        # 'Trần' ~ 'Trà An' (sai chính tả) không phải bằng chứng đủ để cấm 'Trần Hưng Đạo' làm tên đường.
        r = self.bo.chuan_hoa('Phòng 801 , tầng 8, PVC MeKong, 131, Trần Hưng Đạo, Q. Ninh Kiều, Tp. Cần Thơ')
        self.assertEqual(r.duong, 'Đường Trần Hưng Đạo')

    def test_don_vi_nhan_ra_nhung_khong_tra_duoc_co_dau_vet(self):
        r = self.bo.chuan_hoa('Phòng 801 , tầng 8, PVC MeKong, 131, Trần Hưng Đạo, Q. Ninh Kiều, Tp. Cần Thơ')
        kieu = {d.get('kieu_khop') for d in r.dau_vet if d['truong'] in ('xa', 'huyen', 'tinh') and not d.get('ma')}
        self.assertTrue(kieu <= {'khong_khop_dia_ban', 'khong_co_trong_danh_muc'})

    def test_bang_chung_ngang_nhau_thi_khong_chon_bua(self):
        # 21 'Phường 5' trùng tên: không có căn cứ chọn một -> không khẳng định tỉnh/xã.
        r = self.bo.chuan_hoa('x5,mh,ml,nd')
        self.assertEqual((r.ma_xa, r.ma_tinh), ('', ''))
        # An Bình (Kiến Xương) mâu thuẫn Vũ Thư: mọi cách viết đều để trống xã, giữ tỉnh nhất quán.
        for cau in ('20A, An Bình, Vũ Thư, Thái Bình', 'So nhà 20A, An Bình, Vu Thư, Thai Bình',
                    'So nhà 20A, An Bình, Vũ Thư, Thai Bình', '20A, ngõ 1, An Bình, Vũ Thư, Thai Bình'):
            r = self.bo.chuan_hoa(cau)
            self.assertEqual((r.ma_xa, r.ma_tinh), ('', '33'), cau)
            self.assertIn('nhieu_cach_hieu', r.canh_bao, cau)

    def test_bang_chung_khac_nhau_van_chon(self):
        # Mốc, độ dài đoạn và vị trí là bằng chứng thật: không được coi là ngang nhau.
        for cau, ma_xa, ma_tinh in [('Phường 5, Quận 3, TP HCM', '27154', '79'),
                                    ('Phố Hàng Đậu, Phường Ba Đình, Hà Nội, Thành phố Hà Nội', '00004', '01'),
                                    ('Xã Cát Tiên 2, Tỉnh Lâm Đồng', '25180', '68'),
                                    ('tinh long an, so 481/7B d. ba trieu, xa dong thanh', '28207', '80')]:
            r = self.bo.chuan_hoa(cau)
            self.assertEqual((r.ma_xa, r.ma_tinh), (ma_xa, ma_tinh), cau)
        self.assertEqual(self.bo.chuan_hoa('20, Yên Bái, Đà Nẵng').ma_tinh, '48')

    def test_thon_xom_khong_nuot_hanh_chinh_khi_khong_dau_phay(self):
        # Luật nới tên thôn nhiều chữ phải dừng ở đơn vị hành chính / tiền tố hành chính.
        for cau, thon in [('xóm 5 xã mỹ hưng huyện mỹ lộc tỉnh nam định', 'Xóm 5'),
                          ('thôn 3 xã hoằng lộc huyện hoằng hóa tỉnh thanh hóa', 'Thôn 3'),
                          ('thôn đông xã nam hồng huyện tiền hải thái bình', 'Thôn Đông'),
                          ('Xóm Khe Cát, Xã Lam Điền, Chương Mỹ, Hà Nội', 'Xóm Khe Cát')]:
            self.assertEqual(self.bo.chuan_hoa(cau).thon_xom, thon, cau)

    def test_viet_tat_xom_trong_span(self):
        r = self.bo.chuan_hoa('x5, Mỹ Hưng, Mỹ Lộc, Nam Định')
        self.assertEqual(r.thon_xom, 'Xóm 5')


if __name__ == '__main__':
    unittest.main()
