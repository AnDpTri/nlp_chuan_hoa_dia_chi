"""Bước 4: tách các token không thuộc tên hành chính thành
số nhà, ngõ/ngách/hẻm, thôn/xóm, đường.

Các phần này không đổi khi sáp nhập, chỉ chuẩn hóa cách viết.
Bản đầu dùng luật, sau có thể thay bằng CRF.
"""

import re
from .tien_xu_ly import bo_dau


def tach(tokens: list[str], da_dung: set[int]) -> dict[str, str]:
    """da_dung: vị trí token đã thuộc về đơn vị hành chính."""
    result = {"so_nha": "", "ngo_ngach_hem": "", "thon_xom": "", "duong": ""}
    segments = []
    current = []
    for i, t in enumerate(tokens):
        if i in da_dung or t == ",":
            if current:
                segments.append(current)
                current = []
        else:
            current.append(t)
    if current:
        segments.append(current)
    markers = {
        "ngo": ("ngo_ngach_hem", "Ngõ"),
        "ng": ("ngo_ngach_hem", "Ngõ"),
        "ngach": ("ngo_ngach_hem", "Ngách"),
        "hem": ("ngo_ngach_hem", "Hẻm"),
        "kiet": ("ngo_ngach_hem", "Kiệt"),
        "thon": ("thon_xom", "Thôn"),
        "xom": ("thon_xom", "Xóm"),
        "ap": ("thon_xom", "Ấp"),
        "ban": ("thon_xom", "Bản"),
        "kp": ("thon_xom", "Khu phố"),
        "duong": ("duong", "Đường"),
        "d": ("duong", "Đường"),
        "pho": ("duong", "Phố"),
    }
    for segment in segments:
        position = 0
        mode = "duong"
        prefix = ""
        if segment and bo_dau(segment[0]) in {"so", "sn"}:
            position += 1
        if position < len(segment) and re.fullmatch(
            r"\d+[a-z]?(?:/\d+[a-z]?)*", segment[position]
        ):
            number = segment[position]
            position += 1
            if "/" in number:
                first, rest = number.split("/", 1)
                result["so_nha"] = first
                result["ngo_ngach_hem"] = "Ngõ " + rest
            elif not result["so_nha"]:
                result["so_nha"] = number
        chunks = []
        words = []

        def flush():
            if words:
                chunks.append((mode, prefix, " ".join(words)))

        while position < len(segment):
            word = segment[position]
            folded = bo_dau(word)
            if folded in markers:
                flush()
                words = []
                mode, prefix = markers[folded]
            else:
                words.append(word)
            position += 1
        flush()
        for field, label, value in chunks:
            # Không tự khôi phục dấu cho tên đường/thôn không có từ điển.
            name = " ".join(w[:1].upper() + w[1:] for w in value.split())
            # Ngõ 5 [tên đường không có tiền tố]: số ngõ kết thúc trước tên đường.
            if field == "ngo_ngach_hem":
                match = re.fullmatch(r"(\d+[a-z]?(?:/\d+[a-z]?)*)(?:\s+)(.+)", name)
                if match:
                    result[field] = ", ".join(
                        v for v in [result[field], label + " " + match[1]] if v
                    )
                    result["duong"] = ", ".join(
                        v for v in [result["duong"], "Đường " + match[2]] if v
                    )
                    continue
            text = (label + " " + name).strip()
            if not label and field == "duong":
                text = "Đường " + name
            result[field] = ", ".join(v for v in [result[field], text] if v)
    return result
