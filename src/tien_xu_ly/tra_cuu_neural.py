"""Mở rộng ứng viên trên span hành chính neural, có giới hạn và dấu vết.

Viết tắt chữ đầu lấy từ danh mục, không học từ dev/test. Tên đường chưa có
danh mục chứng thực nên vẫn giữ nguyên tên đọc được từ input.
"""

from collections import defaultdict

from ..kieu_du_lieu import UngVien
from .quy_tac import HANH_CHINH, khop_tien_to
from .tim_kiem import khoa_ten, chu_ten, so_dau_mau_thuan, gan_mot_ky_tu
from .tien_xu_ly import bo_dau


class TraCuuNeural:
    def __init__(self, dm):
        self.dm = dm
        self.initials = defaultdict(list)
        for dv in dm.don_vi.values():
            name = dv.ten
            if name.casefold().startswith(dv.loai.casefold() + ' '):
                name = name[len(dv.loai):].strip()
            words = bo_dau(name).replace('-', ' ').split()
            if len(words) > 1:
                key = ''.join(w if w.isdigit() else w[0] for w in words)
                self.initials[dv.cap, key].append((dv.ma, dv.cay, 0))

    def mo_rong(self, context, tokens, trie, candidates):
        existing = {(u.bat_dau, u.ket_thuc, u.cay, u.ma): u for u in candidates}
        stats = {'lookups': 0, 'added': 0, 'truncated_spans': 0, 'truncated_lookups': 0}
        parents = [u for u in candidates if u.cap == 'tinh' and u.co_tien_to and u.kieu_khop != 'sai_chinh_ta']
        for role, raw_a, raw_b in context.char_spans:
            if role not in ('xa', 'huyen', 'tinh'):
                continue
            if stats['lookups'] >= 12:
                stats['truncated_lookups'] += 1
                continue
            inds = [i for i, t in enumerate(context.records) if raw_a <= t.bat_dau and t.ket_thuc <= raw_b]
            if not inds:
                continue
            a, b = inds[0], inds[-1] + 1
            prefix = khop_tien_to(tokens, a, HANH_CHINH)
            typed = bool(prefix and role in prefix[1][0] and prefix[0] < b)
            start = prefix[0] if typed else a
            text = ' '.join(tokens[start:b])
            key = khoa_ten(text)
            if not key or (len(key) < 2 and not typed):
                continue
            stats['lookups'] += 1
            exact = trie.tim(text)
            alias = self.initials.get((role, key), []) if 2 <= len(key) <= 8 else []
            # Chỉ tìm gần đúng toàn span đã nhận diện; không quét fuzzy mọi đoạn.
            plausible = [self.dm.lay(era, code) for code, era, _ in exact
                         if self.dm.lay(era, code).cap == role and
                         (not parents or any(self.dm.tuong_thich(self.dm.lay(era, code), self.dm.lay(p.cay, p.ma)) for p in parents))]
            need_fuzzy = not plausible or all(so_dau_mau_thuan(text, dv.ten) for dv in plausible)
            fuzzy = trie.tim(text, 1) if need_fuzzy and len(key) >= 4 else []
            hits = []
            for kind, values in [('khong_dau', exact), ('viet_tat', alias), ('sai_chinh_ta', fuzzy)]:
                for code, era, errors in values:
                    dv = self.dm.lay(era, code)
                    if dv.cap != role:
                        continue
                    if kind != 'khong_dau' and parents and not any(self.dm.tuong_thich(dv, self.dm.lay(p.cay, p.ma)) for p in parents):
                        continue
                    actual_kind = kind
                    conflicts = so_dau_mau_thuan(text, dv.ten)
                    if kind == 'khong_dau':
                        actual_kind = 'chinh_xac' if chu_ten(text) == chu_ten(dv.ten) else 'khac_dau' if conflicts else 'viet_tat' if key != khoa_ten(dv.ten) else 'khong_dau'
                    elif kind == 'sai_chinh_ta' and errors == 0:
                        actual_kind = 'khac_dau' if conflicts else 'khong_dau'
                    # Tên cũ chỉ khớp đúng chữ; khớp sai chính tả phải gần chính tên hiện hành.
                    if errors and not gan_mot_ky_tu(key, khoa_ten(dv.ten)):
                        continue
                    la_ten_cu = (key, code) in trie.ten_cu and era == 'cu' and errors == 0
                    if la_ten_cu:
                        actual_kind, conflicts = 'viet_tat', 0
                    changed_kind = typed and prefix[1][1] and prefix[1][1] != bo_dau(dv.loai) and not la_ten_cu
                    if changed_kind and errors == 0:
                        actual_kind = 'khac_loai'
                    score = 5. + .35 * min(b - start, 5) + (4. if typed else 0.) - (2.5 if kind == 'sai_chinh_ta' else 1. if kind == 'viet_tat' else 0.)
                    score -= conflicts + ((2.5 if role == 'xa' else .75) if changed_kind else 0.)
                    hits.append(UngVien(a, b, code, era, actual_kind, score, role, typed, la_ten_cu))
            unique_hits = {}
            for u in hits:
                k = (u.cay, u.ma)
                if k not in unique_hits or u.diem > unique_hits[k].diem:
                    unique_hits[k] = u
            hits = list(unique_hits.values())
            hits.sort(key=lambda u: (-u.diem, u.cay, u.ma))
            if len(hits) > 64:
                stats['truncated_spans'] += 1
            for u in hits[:64]:
                k = (a, b, u.cay, u.ma)
                if k not in existing:
                    existing[k] = u
                    stats['added'] += 1
        context.lookup_stats = stats
        return sorted(existing.values(), key=lambda u: (u.bat_dau, u.ket_thuc, u.cay, u.ma))
