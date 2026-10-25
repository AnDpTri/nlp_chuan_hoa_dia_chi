"""Kiểu dữ liệu dùng chung giữa các bước của pipeline.

Mọi bước giao tiếp với nhau qua các kiểu ở đây, để có thể thay cách làm
của một bước mà không phải sửa các bước khác.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class DonVi:
    """Một nút trong cây hành chính (cũ hoặc mới)."""

    ma: str
    cap: str  # "tinh" | "huyen" | "xa"
    loai: str  # "Tỉnh", "Thành phố", "Quận", "Phường", "Xã", ...
    ten: str
    ma_cha: str | None
    cay: str  # "cu" | "moi"


@dataclass(frozen=True)
class UngVien:
    """Một đoạn trong chuỗi đầu vào có thể là một đơn vị hành chính."""

    bat_dau: int  # vị trí token bắt đầu (tính cả)
    ket_thuc: int  # vị trí token kết thúc (không tính)
    ma: str
    cay: str
    kieu_khop: str  # "chinh_xac" | "khong_dau" | "viet_tat" | "sai_chinh_ta"
    diem: float


@dataclass
class DuongDi:
    """Một tổ hợp ứng viên tạo thành đường đi hợp lệ trong cây hành chính."""

    cay: str
    ung_vien: list[UngVien]
    diem: float


@dataclass
class KetQua:
    """Đầu ra cho một địa chỉ, đúng các trường trong bai_toan.md mục 3."""

    so_nha: str = ""
    ngo_ngach_hem: str = ""
    thon_xom: str = ""
    duong: str = ""
    xa_phuong: str = ""  # tên chính thức sau sáp nhập
    ma_xa: str = ""
    tinh: str = ""
    ma_tinh: str = ""
    dia_chi_chuan: str = ""
    canh_bao: list[str] = field(default_factory=list)
