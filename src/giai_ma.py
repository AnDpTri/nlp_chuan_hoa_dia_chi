"""Bước 3: ghép ứng viên thành đường đi hợp lệ trên cây hành chính.

Đọc từ phải sang trái (tỉnh trước), chỉ xét con của nút đã chọn,
giữ k nhánh tốt nhất (beam search). Chạy trên cả cây cũ và cây mới.
"""

from .danh_muc import DanhMuc
from .kieu_du_lieu import DuongDi, UngVien


def cham_diem(duong_di: DuongDi, so_token: int) -> float:
    """Hàm chấm điểm. Bản đầu đặt trọng số bằng tay, sau thay bằng mô hình."""
    raise NotImplementedError


def tim_duong_di(ung_vien: list[UngVien], so_token: int, danh_muc: DanhMuc, beam: int = 5) -> list[DuongDi]:
    """Trả về các đường đi hợp lệ, sắp xếp theo điểm giảm dần."""
    raise NotImplementedError
