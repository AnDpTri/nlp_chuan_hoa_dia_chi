"""Bước 2: sinh ứng viên bằng trie trên tên đơn vị hành chính.

Trie lưu tên đã bỏ dấu và các dạng viết tắt; tìm được khớp chính xác,
khớp không dấu, viết tắt và sai chính tả (tìm gần đúng trên trie).
"""

import unicodedata
from dataclasses import replace

from .danh_muc import DanhMuc
from .kieu_du_lieu import UngVien
from .tien_xu_ly import bo_dau
from .quy_tac import cac_tien_to


def khoa_ten(s):
    # U+02BC là chữ (Lm) theo Unicode dù dùng làm dấu nháy trong tên.
    return "".join(c for c in bo_dau(s) if c.isalnum() and c != "ʼ")


def chu_ten(s):
    """Bỏ cách viết dấu câu/khoảng trắng nhưng giữ dấu tiếng Việt đã nhập."""
    return "".join(c for c in unicodedata.normalize("NFC", s).casefold() if c.isalnum() and c != "ʼ")


def so_dau_mau_thuan(actual, canonical):
    """Thiếu dấu không bị phạt; dấu đã gõ khác danh mục là bằng chứng yếu hơn.

    Chỉ so các tên cùng khóa để không phạt bí danh khác chữ như Sài Gòn.
    Vẫn giữ ứng viên khác dấu cho trường hợp input gõ sai, không loại cứng.
    """
    a, b = chu_ten(actual), chu_ten(canonical)
    if khoa_ten(a) != khoa_ten(b) or len(a) != len(b):
        return 0
    return sum(x != y and x != bo_dau(x) for x, y in zip(a, b))


class Trie:
    def __init__(self):
        self.goc = {}
        self.cache = {}
        self.danh_muc = None
        self.max_tokens = 8

    def them(self, khoa: str, ma: str, cay: str) -> None:
        node = self.goc
        for c in khoa_ten(khoa):
            node = node.setdefault(c, {})
        value = (ma, cay)
        if value not in node.setdefault("$", []):
            node["$"].append(value)
        self.cache.clear()

    def tim(self, khoa: str, so_loi_toi_da: int = 0) -> list[tuple[str, str, int]]:
        """Trả về [(ma, cay, so_loi)] cho các tên khớp với khoa."""
        key = khoa_ten(khoa)
        cache_key = (key, so_loi_toi_da)
        if cache_key in self.cache:
            return self.cache[cache_key]
        out = []
        if so_loi_toi_da == 0:
            node = self.goc
            for c in key:
                node = node.get(c)
                if node is None:
                    break
            if node is not None:
                out = [(ma, cay, 0) for ma, cay in node.get("$", [])]
        else:
            # Levenshtein trên trie, chỉ mở nhánh có hàng DP còn đạt ngưỡng.
            def visit(node, char, prev):
                cur = [prev[0] + 1]
                for j, q in enumerate(key, 1):
                    cur.append(min(cur[-1]+1, prev[j]+1, prev[j-1]+(char != q)))
                if cur[-1] <= so_loi_toi_da:
                    out.extend((ma, cay, cur[-1]) for ma, cay in node.get("$", []))
                if min(cur) <= so_loi_toi_da:
                    for c, child in node.items():
                        if c != "$":
                            visit(child, c, cur)
            for c, child in self.goc.items():
                visit(child, c, list(range(len(key)+1)))
        # Cache có giới hạn để bộ nhớ không tăng theo mọi input khi chạy lâu.
        if len(self.cache) >= 16000:
            self.cache.clear()
        self.cache[cache_key] = out
        return out


def dung_trie(danh_muc: DanhMuc) -> Trie:
    trie = Trie()
    trie.danh_muc = danh_muc
    for dv in danh_muc.don_vi.values():
        trie.them(dv.ten, dv.ma, dv.cay)
        if dv.cap == "tinh":
            aliases = {"Hà Nội": ["HN"], "Hồ Chí Minh": ["HCM", "TPHCM", "Sài Gòn", "SG"]}
            for alias in aliases.get(dv.ten, []):
                trie.them(alias, dv.ma, dv.cay)
    return trie


def bo_sung_tu_luoi_goc(goc, refined, trie, candidates, bao_ve_chi_tiet=False):
    """Tra thêm lưới lexical rồi chiếu offset sang lưới model đã chia nhỏ.

    Không cộng điểm hai lần, không ghép token theo nội dung/địa danh cụ thể.
    Ranh giới model chỉ bổ sung một cách chia, không phủ quyết cách chia gốc.
    """
    if [(t.bat_dau,t.ket_thuc) for t in goc]==[(t.bat_dau,t.ket_thuc) for t in refined]:
        return candidates, 0
    starts={t.bat_dau:i for i,t in enumerate(refined)}
    ends={t.ket_thuc:i+1 for i,t in enumerate(refined)}
    merged={(u.bat_dau,u.ket_thuc,u.cay,u.ma):u for u in candidates}
    added=0
    for u in sinh_ung_vien([t.chu for t in goc],trie,bao_ve_chi_tiet):
        a,b=goc[u.bat_dau].bat_dau,goc[u.ket_thuc-1].ket_thuc
        if a not in starts or b not in ends:
            continue
        projected=replace(u,bat_dau=starts[a],ket_thuc=ends[b])
        key=(projected.bat_dau,projected.ket_thuc,projected.cay,projected.ma)
        if key not in merged:
            merged[key]=projected;added+=1
        elif projected.diem>merged[key].diem:
            merged[key]=projected
    return sorted(merged.values(),key=lambda u:(u.bat_dau,u.ket_thuc,u.cay,u.ma)),added


def sinh_ung_vien(tokens: list[str], trie: Trie, bao_ve_chi_tiet: bool = True) -> list[UngVien]:
    """Quét mọi đoạn token liên tiếp, trả về các ứng viên kèm điểm khớp."""
    dm = trie.danh_muc
    if dm is None:
        raise ValueError("Dùng dung_trie(danh_muc) trước khi sinh ứng viên")
    found = {}
    prefixes = cac_tien_to(tokens)
    inside_prefix = {j for i, (end, _, _) in prefixes.items() for j in range(i+1, end)}
    after_admin_prefix = {end for end, kind, _ in prefixes.values() if kind == "hanh_chinh"}

    for i in range(len(tokens)):
        if not tokens[i][0].isalnum() or i in inside_prefix:
            continue
        entry = prefixes.get(i)
        prefix = (entry[0], entry[2]) if entry and entry[1] == "hanh_chinh" else None
        # Không bỏ tiền tố đã ghi rõ rồi tra riêng phần tên ở một cấp khác.
        modes = [] if i in after_admin_prefix else [(i, None)]
        if prefix:
            modes.insert(0, prefix)
        for start, spec in modes:
            # Tiền tố phải có tên phía sau, không nhận chính chữ "phường" là tên.
            for end in range(start+1, min(len(tokens), start+trie.max_tokens)+1):
                span = tokens[start:end]
                if not all(t[0].isalnum() or t in {"-", "–"} for t in span):
                    break
                if span[-1] in {"-", "–"}:
                    continue
                text = " ".join(span)
                if not spec and (text.isdigit() or (len(span) == 1 and len(khoa_ten(text)) < 3 and bo_dau(text) not in {"hn", "sg"})):
                    continue
                hits = trie.tim(text)
                # Bản đầu chỉ sửa một ký tự khi có tiền tố hành chính rõ ràng.
                if not hits and spec and len(khoa_ten(text)) >= 5:
                    hits = trie.tim(text, 1)
                for ma, cay, errors in hits:
                    dv = dm.lay(cay, ma)
                    changed_kind = bool(spec and spec[1] and bo_dau(dv.loai) != spec[1])
                    if spec and dv.cap not in spec[0]:
                        continue
                    if not spec and dv.ten.isdigit():
                        continue
                    exact = chu_ten(text) == chu_ten(dv.ten)
                    accent_conflicts = so_dau_mau_thuan(text, dv.ten) if not errors else 0
                    kind = "sai_chinh_ta" if errors else "chinh_xac" if exact else "khong_dau"
                    if not errors and (khoa_ten(text) != khoa_ten(dv.ten) or (spec and start-i < len(bo_dau(dv.loai).split()))):
                        kind = "viet_tat"
                    if accent_conflicts:
                        kind = "khac_dau"
                    if changed_kind and not errors:
                        kind = "khac_loai"
                    kind_penalty = (2.5 if dv.cap == "xa" else .75) if changed_kind else 0.0
                    score = 5.0 + .35*min(len(span), 5) + (4.0 if spec else 0.0) - 2.5*errors - kind_penalty - accent_conflicts
                    uv = UngVien(i if spec else start, end, ma, cay, kind, score, dv.cap, bool(spec))
                    key = (uv.bat_dau, end, ma, cay)
                    if key not in found or score > found[key].diem:
                        found[key] = uv
    # Giữ nhánh ngắn để có thể xét ngữ cảnh cha-con, nhưng giảm điểm khi
    # còn một tên đầy đủ cùng cấp/cùng vị trí khớp trực tiếp. Không thưởng
    # hay phạt lặp vì cùng tên có ứng viên ở cả hai mốc.
    groups = {}
    direct = {"chinh_xac", "khong_dau", "viet_tat"}
    for u in found.values():
        if u.kieu_khop in direct:
            key = (u.bat_dau, u.cap, u.co_tien_to)
            groups[key] = max(groups.get(key, 0), u.ket_thuc)
    for key, u in list(found.items()):
        longest = groups.get((u.bat_dau, u.cap, u.co_tien_to), u.ket_thuc)
        if longest > u.ket_thuc:
            found[key] = replace(u, diem=u.diem-(longest-u.ket_thuc))
    if not bao_ve_chi_tiet:
        # CRF được xét vai trò toàn chuỗi trước khi loại cách hiểu đường/hành chính.
        return sorted(found.values(), key=lambda u: (u.bat_dau, u.ket_thuc, u.cay, u.ma))
    # Ranh giới hành chính sau đường/thôn phải có ứng viên đã tra được.
    # Tiền tố ngay đầu tên (Đường Xã Đàn) vẫn thuộc phần tên chi tiết.
    typed_starts = {u.bat_dau for u in found.values() if u.co_tien_to}
    admin_spans = {(u.bat_dau, u.ket_thuc) for u in found.values() if u.co_tien_to and u.kieu_khop != "sai_chinh_ta"}
    detail_zone = set()
    for i, (start, kind, attrs) in prefixes.items():
        if kind != "chi_tiet" or attrs[0] not in {"duong", "thon_xom"} or i in detail_zone:
            continue
        if any(a < i < b for a, b in admin_spans):
            # Phường Phố Mới, Xã Bản Xèo, Xã Đường Lâm là tên hành chính.
            continue
        end = start
        while end < len(tokens) and tokens[end] not in {",", ";"}:
            if end > start and end in typed_starts:
                break
            if end > start and end in prefixes and prefixes[end][1] == "chi_tiet" and prefixes[end][2][0] not in {"so_nha", attrs[0]}:
                break
            detail_zone.add(end)
            end += 1
    filtered = [u for u in found.values() if not any(j in detail_zone for j in range(u.bat_dau, u.ket_thuc))]
    typed_spans = {(u.bat_dau, u.ket_thuc) for u in filtered if u.co_tien_to and u.kieu_khop != "sai_chinh_ta"}
    return sorted((u for u in filtered if u.co_tien_to or not any(a <= u.bat_dau and u.ket_thuc <= b for a, b in typed_spans)), key=lambda u: (u.bat_dau, u.ket_thuc, u.cay, u.ma))
