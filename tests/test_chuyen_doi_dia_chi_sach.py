"""Chuyển đổi nhận địa chỉ sạch dựng tay, không cần chạy tiền xử lý hay mô hình."""

import unittest

from src.danh_muc import DanhMuc
from src.kieu_du_lieu import DiaChiSach, DonViNhan
from src.chuyen_doi import chuyen_doi

HN_CU = DonViNhan(cap="tinh", ma="01", cay="cu")


class ChuyenDoiDiaChiSachTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dm = DanhMuc()

    def doi(self, don_vi, cach_hieu_gan=None, **chi_tiet):
        sach = DiaChiSach(don_vi=don_vi, cach_hieu_gan=cach_hieu_gan or [don_vi], **chi_tiet)
        return chuyen_doi(sach, self.dm)

    def test_xa_cu_nhap_tron(self):
        kq = self.doi([DonViNhan("xa", "00004", "cu"), HN_CU], so_nha="Số 12", duong="Đường Lê Lợi")
        self.assertEqual((kq.ma_xa, kq.ma_tinh), ("00004", "01"))
        self.assertEqual(kq.xa_phuong, "Phường Ba Đình")
        self.assertEqual(kq.dia_chi_chuan, "Số 12, Đường Lê Lợi, Phường Ba Đình, Thành phố Hà Nội")

    def test_xa_cu_bi_chia_de_trong(self):
        kq = self.doi([DonViNhan("xa", "00016", "cu"), HN_CU])
        self.assertEqual(kq.ma_xa, "")
        self.assertIn("xa_bi_chia", kq.canh_bao)
        self.assertEqual({x["ma_xa"] for x in kq.xa_moi_ung_vien}, {"00004", "00008"})

    def test_xa_cu_bi_chia_phan_giai_theo_duong(self):
        # Bảng xã chia theo đường (dữ liệu tham chiếu OSM + GIS): chỉ dùng khi đường có trong bảng của đúng xã cũ đó.
        dm = DanhMuc()
        dm.xa_chia_theo_duong = {("00007", "daotan"): "00025"}
        bang = chuyen_doi(DiaChiSach(don_vi=[DonViNhan("xa", "00007", "cu"), HN_CU],
                                     cach_hieu_gan=[[DonViNhan("xa", "00007", "cu"), HN_CU]], duong="Phố Đào Tấn"), dm)
        self.assertEqual(bang.ma_xa, "00025")
        self.assertIn("xa_chia_suy_tu_duong", bang.canh_bao)
        self.assertNotIn("xa_bi_chia", bang.canh_bao)
        khac = chuyen_doi(DiaChiSach(don_vi=[DonViNhan("xa", "00007", "cu"), HN_CU],
                                     cach_hieu_gan=[[DonViNhan("xa", "00007", "cu"), HN_CU]], duong="Đường Lê Lợi"), dm)
        self.assertEqual(khac.ma_xa, "")
        self.assertIn("xa_bi_chia", khac.canh_bao)

    def test_don_vi_moc_moi(self):
        kq = self.doi([DonViNhan("xa", "00004", "moi"), DonViNhan("tinh", "01", "moi")])
        self.assertEqual((kq.ma_xa, kq.ma_tinh), ("00004", "01"))

    def test_hai_cach_hieu_khac_xa(self):
        a = [DonViNhan("xa", "00004", "cu"), HN_CU]
        b = [DonViNhan("xa", "00007", "cu"), HN_CU]
        kq = self.doi(a, cach_hieu_gan=[a, b])
        self.assertEqual(kq.ma_xa, "")
        self.assertEqual(kq.ma_tinh, "01")
        self.assertIn("nhieu_cach_hieu", kq.canh_bao)

    def test_thieu_tinh_dau_vao(self):
        kq = self.doi([DonViNhan("xa", "00004", "cu")])
        self.assertEqual(kq.ma_tinh, "01")
        self.assertIn("thieu_tinh_dau_vao", kq.canh_bao)


if __name__ == "__main__":
    unittest.main()
