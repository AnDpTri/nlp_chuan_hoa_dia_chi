"""Bước 1: chuẩn hóa chuỗi đầu vào và tách token.

Giữ thứ tự token chuẩn hóa để truy vết theo chỉ số token, không phải offset ký tự gốc.
"""

import re
import unicodedata


def chuan_hoa_chuoi(chuoi: str) -> str:
    """Unicode NFC, viết thường, gom khoảng trắng, tách dấu câu."""
    if not isinstance(chuoi, str):
        raise TypeError("Địa chỉ phải là chuỗi.")
    text = unicodedata.normalize("NFC", chuoi).lower().strip()
    text = re.sub(r"\b(tp|q|p|h|x)\s*\.\s*", r"\1 ", text)
    text = re.sub(r"\b(p|q)(\d+)\b", r"\1 \2", text)
    text = re.sub(r"[;|]", ",", text)
    text = re.sub(r"[^\w\s,/-]", " ", text, flags=re.UNICODE)
    return re.sub(r"\s+", " ", text).strip()


def bo_dau(chuoi: str) -> str:
    """Bỏ dấu tiếng Việt, đổi đ thành d."""
    return "".join(
        c
        for c in unicodedata.normalize("NFD", chuoi.lower().replace("đ", "d"))
        if unicodedata.category(c) != "Mn"
    )


def tach_token(chuoi: str) -> list[str]:
    return re.findall(
        r"\d+[a-z]?(?:/\d+[a-z]?)*|[^\W\d_]+|,",
        chuan_hoa_chuoi(chuoi),
        flags=re.UNICODE,
    )
