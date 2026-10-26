"""Bước 2: sinh ứng viên bằng trie trên tên đơn vị hành chính.

Trie lưu tên đã bỏ dấu và các dạng viết tắt; tìm được khớp chính xác,
khớp không dấu, viết tắt và sai chính tả (tìm gần đúng trên trie).
"""

from .danh_muc import DanhMuc
from .kieu_du_lieu import UngVien
from .tien_xu_ly import bo_dau
from functools import lru_cache

PREFIXES = {
    "tinh": ["tinh", "tp", "thanh pho"],
    "huyen": ["quan", "q", "huyen", "h", "thi xa", "tx", "thanh pho", "tp"],
    "xa": ["xa", "x", "phuong", "p", "thi tran", "tt", "dac khu"],
}


class Trie:
    def __init__(self):
        self.root = {}
        self.units = {}
        self.aliases = set()

    def them(self, khoa: str, ma: str, cay: str) -> None:
        node = self.root
        for ch in khoa:
            node = node.setdefault(ch, {})
        values = node.setdefault("_values", [])
        if (ma, cay) not in values:
            values.append((ma, cay))
        self.tim.cache_clear()

    @lru_cache(maxsize=30000)
    def tim(self, khoa: str, so_loi_toi_da: int = 0) -> list[tuple[str, str, int]]:
        """Trả về [(ma, cay, so_loi)] cho các tên khớp với khoa."""
        if so_loi_toi_da == 0:
            node = self.root
            for ch in khoa:
                if ch not in node:
                    return []
                node = node[ch]
            return [(ma, cay, 0) for ma, cay in node.get("_values", [])]
        result = []

        def visit(node, ch, previous):
            current = [previous[0] + 1]
            for j, target in enumerate(khoa, 1):
                current.append(
                    min(
                        current[j - 1] + 1,
                        previous[j] + 1,
                        previous[j - 1] + (ch != target),
                    )
                )
            if current[-1] <= so_loi_toi_da:
                result.extend(
                    (ma, cay, current[-1]) for ma, cay in node.get("_values", [])
                )
            if min(current) <= so_loi_toi_da:
                for child, subtree in node.items():
                    if child != "_values":
                        visit(subtree, child, current)

        previous = list(range(len(khoa) + 1))
        for ch, node in self.root.items():
            if ch != "_values":
                visit(node, ch, previous)
        return sorted(result, key=lambda r: (r[2], r[1], r[0]))


def dung_trie(danh_muc: DanhMuc) -> Trie:
    trie = Trie()
    trie.units = danh_muc.don_vi
    for (cay, ma), u in danh_muc.don_vi.items():
        name = bo_dau(u.ten)
        # Tên chỉ là số phải có tiền tố, tránh lấy số nhà thành phường.
        if not name.isdigit() and len(name) > 2:
            trie.them(name, ma, cay)
        for prefix in set(PREFIXES[u.cap] + [bo_dau(u.loai)]):
            trie.them(prefix + " " + name, ma, cay)
        if u.cap == "tinh":
            aliases = {
                "ha noi": ["hn"],
                "ho chi minh": ["hcm", "tphcm", "tp hcm", "sai gon", "sg"],
                "hai phong": ["hp"],
                "da nang": ["dn"],
                "dong nai": ["dn"],
            }.get(name, [])
            for alias in aliases:
                trie.them(alias, ma, cay)
                trie.aliases.add((alias, ma, cay))
        if name == "cau giay":
            trie.them("cg", ma, cay)
            trie.aliases.add(("cg", ma, cay))
    return trie


def sinh_ung_vien(tokens: list[str], trie: Trie, fuzzy: bool = True) -> list[UngVien]:
    """Quét mọi đoạn token liên tiếp, trả về các ứng viên kèm điểm khớp."""
    result = {}
    folded = [bo_dau(t) for t in tokens]
    markers = {
        "tinh",
        "tp",
        "thanh",
        "quan",
        "q",
        "huyen",
        "h",
        "xa",
        "x",
        "phuong",
        "p",
        "thi",
        "tt",
        "dac",
    }
    for start in range(len(tokens)):
        if tokens[start] == ",":
            continue
        for end in range(start + 1, min(start + 7, len(tokens)) + 1):
            if "," in tokens[start:end]:
                break
            key = " ".join(folded[start:end])
            matches = trie.tim(key)
            # Chỉ sửa gần đúng đoạn có dấu hiệu cấp hành chính; không sửa mọi tên đường thành xã.
            if (
                not matches
                and fuzzy
                and folded[start] in markers
                and end - start >= 2
                and len(key) >= 6
            ):
                matches = trie.tim(key, 1)
            for ma, cay, errors in matches:
                u = trie.units[(cay, ma)]
                if (
                    start
                    and folded[start - 1]
                    in {"duong", "pho", "ngo", "hem", "thon", "xom", "ap"}
                    and folded[start] not in markers
                ):
                    continue
                raw = " ".join(tokens[start:end])
                full = bo_dau(u.loai) + " " + bo_dau(u.ten)
                explicit = key == full or any(
                    key.startswith(p + " ") for p in PREFIXES[u.cap]
                )
                if (key, ma, cay) in trie.aliases:
                    kind = "viet_tat"
                elif errors:
                    kind = "sai_chinh_ta"
                elif raw in [u.ten.lower(), (u.loai + " " + u.ten).lower()]:
                    kind = "chinh_xac"
                else:
                    kind = "khong_dau"
                score = (
                    2 * (end - start)
                    + 3
                    + 2 * explicit
                    - 2.5 * errors
                    - (0.4 if kind == "viet_tat" else 0)
                )
                uv = UngVien(start, end, ma, cay, kind, score)
                identity = (start, end, ma, cay)
                if identity not in result or uv.diem > result[identity].diem:
                    result[identity] = uv
    return list(result.values())
