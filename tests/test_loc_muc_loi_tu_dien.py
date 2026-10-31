"""Mục từ điển hỏng (chữ bị chẻ, tên không dấu cạnh dạng có dấu) bị loại khi nạp."""

import json
import tempfile
import unittest
from pathlib import Path

from src.tien_xu_ly.chuan_ten_duong import TuDienDuong


def nap(entries):
    tmp = tempfile.TemporaryDirectory()
    path = Path(tmp.name) / 'd.json'
    path.write_text(json.dumps({'format': 1, 'source_scope': 'train_only', 'entries': [
        {'province': p, 'canonical': c, 'train_ids': ['fixture']} for p, c in entries
    ]}, ensure_ascii=False), encoding='utf-8')
    d = TuDienDuong(path)
    return d, tmp


class LocMucLoiTests(unittest.TestCase):
    def test_ten_khong_dau_canh_dang_co_dau_khong_chan_tinh_khac(self):
        d, tmp = nap([('01', 'Đường Trần Hưng Đạo'), ('02', 'Đường Tran Hung Dao'), ('03', 'Đường Trần Hưng Đạo')])
        self.addCleanup(tmp.cleanup)
        self.assertEqual(d.so_muc_bi_loi, 1)
        self.assertEqual(d.chuan_hoa('Đường Tran Hung Dao', '04')[0], 'Đường Trần Hưng Đạo')

    def test_chu_bi_che_bi_loai(self):
        d, tmp = nap([('01', 'Đường Nguyễn Khuyến'), ('02', 'Đường Nguyễ N Khuyế N'), ('03', 'Đường NguyễN KhuyếN')])
        self.addCleanup(tmp.cleanup)
        self.assertEqual(d.so_muc_bi_loi, 2)
        self.assertEqual(d.chuan_hoa('Đường Nguyen Khuyen', '04')[0], 'Đường Nguyễn Khuyến')

    def test_ten_khong_dau_duy_nhat_van_giu(self):
        d, tmp = nap([('01', 'Đường Hang Quat')])
        self.addCleanup(tmp.cleanup)
        self.assertEqual(d.so_muc_bi_loi, 0)

    def test_hai_dang_co_dau_that_van_tu_choi(self):
        d, tmp = nap([('01', 'Đường Hòa Bình'), ('02', 'Đường Hóa Bình')])
        self.addCleanup(tmp.cleanup)
        self.assertEqual(d.chuan_hoa('Đường Hoa Binh', '03'), ('Đường Hoa Binh', None))


if __name__ == '__main__':
    unittest.main()
