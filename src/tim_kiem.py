"""Bước 2: sinh ứng viên bằng trie trên tên đơn vị hành chính.

Trie lưu tên đã bỏ dấu và các dạng viết tắt; tìm được khớp chính xác,
khớp không dấu, viết tắt và sai chính tả (tìm gần đúng trên trie).
"""

from .danh_muc import DanhMuc
from .kieu_du_lieu import UngVien


class Trie:
    def them(self, khoa: str, ma: str, cay: str) -> None:
        raise NotImplementedError

    def tim(self, khoa: str, so_loi_toi_da: int = 0) -> list[tuple[str, str, int]]:
        """Trả về [(ma, cay, so_loi)] cho các tên khớp với khoa."""
        raise NotImplementedError


def dung_trie(danh_muc: DanhMuc) -> Trie:
    raise NotImplementedError


def sinh_ung_vien(tokens: list[str], trie: Trie) -> list[UngVien]:
    """Quét mọi đoạn token liên tiếp, trả về các ứng viên kèm điểm khớp."""
    raise NotImplementedError
