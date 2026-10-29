"""Tách chi tiết bằng luật có ngữ cảnh, không nối các khoảng token rời nhau."""

import re
from .quy_tac import cac_tien_to, khop_chu_tien_to
from .tien_xu_ly import bo_dau

FIELDS = ("so_nha", "ngo_ngach_hem", "thon_xom", "duong")


def viet_ten(tokens):
    return " ".join(t if any(c.isdigit() for c in t) else t.capitalize() for t in tokens)


def tach_co_dau_vet(tokens: list[str], da_dung: set[int], tien_to=None):
    values = {f: [] for f in FIELDS}
    spans = []
    used = set(da_dung)
    prefixes = cac_tien_to(tokens) if tien_to is None else tien_to
    n = len(tokens)
    inferred = False

    def luu(f, a, b, value):
        if value:
            values[f].append(value)
            spans.append({"truong": f, "bat_dau": a, "ket_thuc": b, "gia_tri": value})
            used.update(range(a, b))

    def number(j):
        return j < n and j not in used and re.fullmatch(r"\d+[A-Za-z]?(?:/\d+[A-Za-z]?)*", tokens[j]) and not (j+1 < n and tokens[j+1] == "+")

    def house_number(j):
        """Bảo toàn cụm số, không diễn giải '-' thành dãy nhà hay tách '/'."""
        end, value = j+1, tokens[j]
        while end+1 < n and end not in used and tokens[end] in {"-", "–", "—", ";"} and number(end+1):
            separator = ";" if tokens[end] == ";" else "-"
            value += separator+tokens[end+1]
            end += 2
        return end, value

    def boundary(j, start, field):
        if j in used or tokens[j] in {",", ";"}:
            return True
        marker = prefixes.get(j)
        if not marker or j == start:
            return False
        end, kind, attrs = marker
        if end >= n or not tokens[end][0].isalnum():
            return False
        if kind == "hanh_chinh":
            return end not in prefixes
        return not (field == "duong" and attrs[0] in {"so_nha", "duong"})

    def end_detail(start, field):
        end = start
        while end < n and not boundary(end, start, field):
            end += 1
        while end > start and tokens[end-1] in {".", "-", "–"}:
            end -= 1
        return end

    def implicit_road():
        if values["duong"] or not (values["so_nha"] or values["ngo_ngach_hem"]):
            return False
        start = max(s["ket_thuc"] for s in spans if s["truong"] in {"so_nha", "ngo_ngach_hem"})
        while start < n and tokens[start] in {",", "."}:
            start += 1
        if start >= n or start in used or start in prefixes:
            return False
        end = end_detail(start, "duong")
        rest = tokens[start:end]
        blocked = ["chung cư", "tòa nhà", "tầng", "phòng", "gần", "đối diện", "district", "block",
                   "lô", "tập thể", "khu đô thị", "khu dân cư", "căn hộ", "dãy nhà"]
        def starts_with(phrase):
            words = phrase.split()
            return len(rest) >= len(words) and all(khop_chu_tien_to(t, bo_dau(w), w) for t, w in zip(rest, words))
        if rest and rest[0][0].isalnum() and sum(t.isalpha() for t in rest) >= 2 and not any(starts_with(p) for p in blocked):
            luu("duong", start, end, "Đường " + viet_ten(rest))
            return True
        return False

    i = 0
    while i < n:
        if i in used or not tokens[i][0].isalnum():
            i += 1
            continue
        entry = prefixes.get(i)
        if entry and entry[1] == "hanh_chinh":
            # Không biến số phường/huyện chưa giải được thành số nhà.
            i = entry[0]
            while i < n and i not in used and tokens[i] not in {",", ";"} and i not in prefixes:
                i += 1
            continue
        if entry and entry[1] == "chi_tiet":
            j, _, (f, label) = entry
            if any(k in used for k in range(i, j)):
                i += 1
                continue
            if f == "so_nha":
                if number(j):
                    end, value = house_number(j)
                    luu(f, i, end, f"Số {value}")
                    inferred = implicit_road() or inferred
                    i = end
                    continue
            elif f == "ngo_ngach_hem" and number(j):
                luu(f, i, j+1, f"{label} {tokens[j]}")
                inferred = implicit_road() or inferred
                i = j+1
                continue
            else:
                end = end_detail(j, f)
                if end > j:
                    luu(f, i, end, f"{label} {viet_ten(tokens[j:end])}")
                    i = end
                    continue
        segment_start = i == 0 or tokens[i-1] in {",", ";"}
        if segment_start and not values["so_nha"] and number(i):
            end, value = house_number(i)
            luu("so_nha", i, end, f"Số {value}")
            # Tách ngay trước khi tên riêng bị nhận thành một tiền tố riêng lẻ.
            inferred = implicit_road() or inferred
        i += 1

    unknown = [i for i, t in enumerate(tokens) if i not in used and any(c.isalnum() for c in t)]
    result = {f: ", ".join(dict.fromkeys(values[f])) for f in FIELDS}
    result["phan_chua_phan_loai"] = " ".join(tokens[i] for i in unknown)
    return result, spans, unknown, inferred


def tach(tokens: list[str], da_dung: set[int]) -> dict[str, str]:
    return tach_co_dau_vet(tokens, da_dung)[0]
