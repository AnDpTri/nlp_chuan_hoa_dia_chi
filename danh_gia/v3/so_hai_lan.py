"""So hai lượt chạy trên nhãn đã sửa: liệt kê câu đổi đúng/sai và các trường khác nhau.
Dùng: so_hai_lan.py <ket_qua_truoc.jsonl> <ket_qua_sau.jsonl> [thu_muc_nhan]"""
import duong_dan as dd  # gốc repo, CODE_ROOT vào sys.path
import csv, json, sys, unicodedata
from pathlib import Path

F = ('so_nha', 'ngo_ngach_hem', 'thon_xom', 'duong', 'ma_xa', 'ma_tinh')


def fold(s):
    s = unicodedata.normalize('NFD', (s or '').replace('đ', 'd').replace('Đ', 'D'))
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn').casefold().replace(' ', '')
    return 'duong' + s[3:] if s.startswith('pho') else s


def doc(p):
    return {(r['split'], r['id']): r['out'] for r in map(json.loads, open(p, encoding='utf-8'))}


def dung(o, g):
    bo = set((g.get('bo_qua') or '').split())
    return all(f in bo or (o.get(f, '') == g[f] if f.startswith('ma_') else fold(o.get(f)) == fold(g[f])) for f in F)


gdir = Path(sys.argv[3] if len(sys.argv) > 3 else dd.NHAN_SUA)
gold = {(sp, r['id']): r for sp in ('dev_goc', 'dev_kho') for r in csv.DictReader(open(gdir / f'{sp}.csv', encoding='utf-8-sig'))}
a, b = doc(sys.argv[1]), doc(sys.argv[2])
for k in sorted(gold):
    if k not in a or k not in b:
        continue
    da, db = dung(a[k], gold[k]), dung(b[k], gold[k])
    if da != db:
        print(('TỐT HƠN' if db else 'TỆ HƠN'), k, gold[k]['dau_vao'])
        for f in F:
            if a[k].get(f, '') != b[k].get(f, ''):
                print(f'    {f}: nhãn={gold[k][f]!r} | trước={a[k].get(f, "")!r} | sau={b[k].get(f, "")!r}')
n = sum(1 for k in a if k in b and k[0] == 'kho' and {f: a[k].get(f) for f in F} != {f: b[k].get(f) for f in F})
print('bộ khó: số câu đổi đầu ra =', n)
