"""Ghép cả pipeline: chuan_hoa(chuoi) -> KetQua."""

from .danh_muc import DanhMuc
from .kieu_du_lieu import KetQua


class BoChuanHoa:
    def __init__(self, danh_muc: DanhMuc | None = None):
        self.danh_muc = danh_muc or DanhMuc()
        # dựng trie một lần ở đây

    def chuan_hoa(self, chuoi: str) -> KetQua:
        raise NotImplementedError
