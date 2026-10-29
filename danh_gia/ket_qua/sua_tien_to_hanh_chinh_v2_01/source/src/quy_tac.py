"""Tiền tố dùng chung cho tìm hành chính và tách chi tiết; không học từ test."""

import unicodedata
from functools import lru_cache
from .tien_xu_ly import bo_dau

# (dạng viết, các cấp có thể có, loại chính thức). None nghĩa là không khóa loại.
HANH_CHINH = [
    ("thanh pho", {"tinh", "huyen"}, "thanh pho"),
    ("thi xa", {"huyen"}, "thi xa"),
    ("thi tran", {"xa"}, "thi tran"),
    ("dac khu", {"xa"}, "dac khu"),
    ("tinh", {"tinh"}, "tinh"), ("t", {"tinh"}, None),
    ("tp", {"tinh", "huyen"}, "thanh pho"),
    ("huyen", {"huyen"}, "huyen"), ("h", {"huyen"}, "huyen"),
    ("quan", {"huyen"}, "quan"), ("q", {"huyen"}, "quan"),
    ("tx", {"huyen"}, "thi xa"), ("tt", {"xa"}, "thi tran"),
    ("phuong", {"xa"}, "phuong"), ("phuowng", {"xa"}, "phuong"),
    ("p", {"xa"}, "phuong"), ("xa", {"xa"}, "xa"), ("x", {"xa"}, "xa"),
]
CHI_TIET = [
    ("so nha", "so_nha", "Số"), ("so", "so_nha", "Số"),
    ("ngo", "ngo_ngach_hem", "Ngõ"), ("ng", "ngo_ngach_hem", "Ngõ"),
    ("ngach", "ngo_ngach_hem", "Ngách"), ("hem", "ngo_ngach_hem", "Hẻm"),
    ("kiet", "ngo_ngach_hem", "Kiệt"),
    ("thon", "thon_xom", "Thôn"), ("thoon", "thon_xom", "Thôn"),
    ("xom", "thon_xom", "Xóm"), ("ap", "thon_xom", "Ấp"),
    ("ban", "thon_xom", "Bản"), ("khu pho", "thon_xom", "Khu phố"),
    ("kp", "thon_xom", "Khu phố"), ("to dan pho", "thon_xom", "Tổ dân phố"),
    ("tdp", "thon_xom", "Tổ dân phố"), ("to", "thon_xom", "Tổ"),
    ("duong", "duong", "Đường"), ("dduong", "duong", "Đường"),
    ("dduowng", "duong", "Đường"),
    ("d", "duong", "Đường"), ("pho", "duong", "Phố"),
    ("quoc lo", "duong", "Quốc lộ"), ("ql", "duong", "Quốc lộ"),
    ("tinh lo", "duong", "Tỉnh lộ"), ("tl", "duong", "Tỉnh lộ"),
    ("xa lo", "duong", "Xa lộ"), ("dai lo", "duong", "Đại lộ"),
]

# So khớp không dấu chỉ dùng làm dạng tra cứu; dấu đã có là bằng chứng.
# Tô không phải Tổ, Tĩnh không phải Tỉnh, dù khóa bỏ dấu giống nhau.
_CHU_CHUAN = "Thành phố Thị xã trấn Đặc khu Tỉnh Huyện Quận Phường Số nhà Ngõ Ngách Hẻm Kiệt Thôn Xóm Ấp Bản Khu Tổ dân Đường Quốc lộ"
_DANG_CO_DAU = {}
for _word in _CHU_CHUAN.split():
    _DANG_CO_DAU.setdefault(bo_dau(_word), set()).add(_word.casefold())
_DANG_CO_DAU["d"] = {"đ"}


@lru_cache(maxsize=256)
def dang_go_telex(chu_chuan):
    """Mã hóa từ tiền tố chuẩn; không đoán/sửa tên riêng theo khoảng cách."""
    tone_codes = {'\u0300': 'f', '\u0301': 's', '\u0309': 'r', '\u0303': 'x', '\u0323': 'j'}
    text = unicodedata.normalize('NFD', chu_chuan.casefold())
    letters, tone = [], ''
    for c in text:
        if c in tone_codes:
            tone = tone_codes[c]
        elif c == '\u0302' and letters and letters[-1] in ('a', 'e', 'o'):
            letters[-1] *= 2
        elif c in ('\u0306', '\u031b') and letters:
            letters[-1] += 'w'
        elif c == 'đ':
            letters.append('dd')
        else:
            letters.append(c)
    full = ''.join(letters) + tone
    # Hai cách gõ tổ hợp ươ: uwow và uow.
    return frozenset((full, full.replace('uwow', 'uow')))


def la_tien_to_telex(chu):
    actual = chu.casefold()
    return any(actual != bo_dau(c) and actual in dang_go_telex(c)
               for choices in _DANG_CO_DAU.values() for c in choices)


def khop_chu_tien_to(chu, khoa, chu_chuan=None):
    actual = unicodedata.normalize("NFC", chu).casefold()
    if actual == khoa:
        return True
    choices = {chu_chuan.casefold()} if chu_chuan else _DANG_CO_DAU.get(khoa, ())
    if actual == bo_dau(actual) and any(actual in dang_go_telex(c) for c in choices):
        return True
    if bo_dau(actual) != khoa:
        return False
    # Chấp nhận mất dấu một phần (Đuong), không đổi dấu đã gõ sang dấu khác.
    return any(len(actual) == len(canonical) and
               all(a in {b, c} for a, b, c in zip(actual, canonical, khoa))
               for canonical in choices)


def khop_tien_to(tokens, i, bang):
    """Trả (vị trí sau tiền tố và dấu chấm, các thuộc tính của tiền tố)."""
    for row in bang:
        words = row[0].split()
        canonical = row[2].split() if bang is CHI_TIET and bo_dau(row[2]) == row[0] else []
        j = i
        for index, w in enumerate(words):
            if j >= len(tokens) or not khop_chu_tien_to(tokens[j], w, canonical[index] if canonical else None):
                break
            j += 1
            if j < len(tokens) and tokens[j] == ".":
                j += 1
        else:
            # "to" không dấu đứng trước tên riêng chưa đủ để gọi là tổ.
            if row[0] == "to" and tokens[i].casefold() == "to" and (j >= len(tokens) or not tokens[j][0].isdigit()):
                continue
            return j, row[1:]
    return None


def cac_tien_to(tokens):
    """Nhận cụm dài trước, không nhận 'phố' bên trong 'thành phố'."""
    result = {}
    i = 0
    while i < len(tokens):
        options = []
        for kind, table in (("hanh_chinh", HANH_CHINH), ("chi_tiet", CHI_TIET)):
            m = khop_tien_to(tokens, i, table)
            if m:
                options.append((m[0], kind, m[1]))
        if not options:
            i += 1
            continue
        end, kind, attrs = max(options, key=lambda x: x[0])
        result[i] = (end, kind, attrs)
        i = end
    return result
