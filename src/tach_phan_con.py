"""Bước 4: tách các token không thuộc tên hành chính thành
số nhà, ngõ/ngách/hẻm, thôn/xóm, đường.

Các phần này không đổi khi sáp nhập, chỉ chuẩn hóa cách viết.
Bản đầu dùng luật, sau có thể thay bằng CRF.
"""


def tach(tokens: list[str], da_dung: set[int]) -> dict[str, str]:
    """da_dung: vị trí token đã thuộc về đơn vị hành chính."""
    raise NotImplementedError
