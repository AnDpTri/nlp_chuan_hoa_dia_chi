"""Tên cũ đã bị nhập/đổi trước khi danh mục cũ được chụp vẫn phải tra ra đơn vị hiện thân."""

import unittest

from src.chuan_hoa import BoChuanHoa


class TenCuTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bo = BoChuanHoa()

    def kiem(self, chuoi):
        r = self.bo.chuan_hoa(chuoi)
        self.assertEqual((r.xa_phuong, r.tinh), ('Phường Mỹ Lộc', 'Tỉnh Ninh Bình'), chuoi)
        self.assertEqual(r.canh_bao, [], chuoi)

    def test_xa_my_hung_nam_dinh(self):
        self.kiem('Xã Mỹ Hưng, Huyện Mỹ Lộc, Tỉnh Nam Định')

    def test_co_thon_xom(self):
        self.kiem('Xóm 5, Xã Mỹ Hưng, Huyện Mỹ Lộc, Tỉnh Nam Định')

    def test_thi_tran_my_loc(self):
        self.kiem('Thị trấn Mỹ Lộc, Huyện Mỹ Lộc, Tỉnh Nam Định')

    def test_ten_hien_tai_van_dung(self):
        self.kiem('Phường Hưng Lộc, Thành phố Nam Định, Tỉnh Nam Định')


if __name__ == '__main__':
    unittest.main()
