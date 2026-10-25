"""Bước 1: chuẩn hóa chuỗi đầu vào và tách token.

Giữ lại vị trí của từng token trong chuỗi gốc để truy vết.
"""


def chuan_hoa_chuoi(chuoi: str) -> str:
    """Unicode NFC, viết thường, gom khoảng trắng, tách dấu câu."""
    raise NotImplementedError


def bo_dau(chuoi: str) -> str:
    """Bỏ dấu tiếng Việt, đổi đ thành d."""
    raise NotImplementedError


def tach_token(chuoi: str) -> list[str]:
    raise NotImplementedError
