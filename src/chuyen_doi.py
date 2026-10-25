"""Bước 5: chuyển đường đi trên cây cũ sang đơn vị hành chính mới.

Xã cũ nhập nguyên vào một xã mới thì đổi thẳng. Xã cũ bị chia thì dùng
thôn/xóm, đường nếu dữ liệu cho phép, không thì gắn cờ xa_bi_chia.
"""

from .danh_muc import DanhMuc
from .kieu_du_lieu import DuongDi


def sang_cay_moi(duong_di: DuongDi, phan_con: dict[str, str], danh_muc: DanhMuc) -> tuple[str, str, list[str]]:
    """Trả về (ma_xa_moi, ma_tinh_moi, canh_bao)."""
    raise NotImplementedError
