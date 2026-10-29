"""Kiểm tra các kết luận chẩn đoán dễ bị nhầm giữa có đích và chốt đích."""

import unittest
from pathlib import Path

from danh_gia.chan_doan_pipeline import admin_match, field_decision_counts, find_unique_witness, run
from danh_gia.chay_ban_thu import ROOT
from src.danh_muc import DanhMuc
from src.kieu_du_lieu import UngVien


class DiagnosticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dm = DanhMuc()
        cls.old = next(dv for dv in cls.dm.don_vi.values()
                       if dv.cay == 'cu' and dv.cap == 'xa'
                       and len(cls.dm.dich_xa('cu', dv.ma)) > 1
                       and len(cls.dm.dich_tinh('cu', dv.ma)) == 1)
        cls.ward = sorted(cls.dm.dich_xa('cu', cls.old.ma))[0]
        cls.province = cls.dm.lay('moi', cls.ward).ma_cha

    def candidate(self, a, b, ma, era):
        return UngVien(a, b, ma, era, 'chinh_xac', 9, 'xa', True)

    def test_co_dich_trong_xa_chia_khong_phai_chot_duy_nhat(self):
        u = self.candidate(0, 2, self.old.ma, 'cu')
        result = find_unique_witness([u], self.dm, self.ward, self.province)
        self.assertEqual(result['status'], 'absent')

    def test_them_bang_chung_moi_co_the_chot_dich(self):
        old = self.candidate(0, 2, self.old.ma, 'cu')
        new = self.candidate(3, 5, self.ward, 'moi')
        result = find_unique_witness([old, new], self.dm, self.ward, self.province)
        self.assertEqual(result['status'], 'found')
        self.assertIn(new, result['witness'])

    def test_gioi_han_duyet_khong_duoc_bao_la_khong_co(self):
        new = self.candidate(0, 2, self.ward, 'moi')
        result = find_unique_witness([new], self.dm, self.ward, self.province, max_nodes=0)
        self.assertEqual(result['status'], 'limit')

    def test_nhan_xa_co_gia_tri_khong_khop_tap_dich_nhieu_phan_tu(self):
        row = {'ma_xa': self.ward, 'ma_tinh': self.province}
        wards = set(self.dm.dich_xa('cu', self.old.ma))
        self.assertFalse(admin_match(wards, {self.province}, row))
        self.assertTrue(admin_match({self.ward}, {self.province}, row))
        self.assertTrue(admin_match(wards, {self.province}, {**row, 'ma_xa': ''}))

    def test_mau_trong_khong_lam_giam_ty_le_lech_trong_so_dien(self):
        pairs = [({'ma_xa': ''}, {'ma_xa': ''}) for _ in range(10)]
        pairs += [({'ma_xa': 'a'}, {'ma_xa': 'a'}), ({'ma_xa': 'b'}, {'ma_xa': 'a'}),
                  ({'ma_xa': 'b'}, {'ma_xa': ''})]
        result = field_decision_counts(pairs, 'ma_xa')
        self.assertEqual(result['ty_le_lech_trong_so_dien_pct'], 50)
        self.assertEqual(result['de_trong_khi_nhan_co'], 1)
        self.assertEqual(result['cung_trong'], 10)

    def test_chan_test_truoc_khi_doc(self):
        with self.assertRaisesRegex(ValueError, 'Không đọc tập test cuối'):
            run(ROOT / 'data/test/khong_ton_tai.csv', Path('khong_duoc_tao'), Path('khong_doc'))


if __name__ == '__main__':
    unittest.main()
