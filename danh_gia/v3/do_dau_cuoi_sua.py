"""Như do_dau_cuoi.py nhưng chấm theo bộ nhãn chọn được (gốc hoặc đã sửa sau dò nhãn).
Trường ghi trong cột bo_qua (agy phán 'khong_ro') không tính vào phép chấm của câu đó.
Dùng: do_dau_cuoi_sua.py <thu_muc_nhan> <ket_qua.jsonl> [...]"""
import csv, json, sys, unicodedata, collections
from pathlib import Path

F = ('so_nha', 'ngo_ngach_hem', 'thon_xom', 'duong', 'ma_xa', 'ma_tinh')


def fold(s):
    s = unicodedata.normalize('NFD', (s or '').replace('đ', 'd').replace('Đ', 'D'))
    return ''.join(c for c in s if unicodedata.category(c) != 'Mn').casefold().replace(' ', '')


def fold_duong(s):
    """'Phố X' và 'Đường X' là cùng một tên (quy ước 2 của dò nhãn); áp như nhau cho mọi mô hình."""
    s = fold(s)
    return 'duong' + s[3:] if s.startswith('pho') else s


def main(gdir, paths):
    gold = {}
    for sp in ('dev_goc', 'dev_kho'):
        for r in csv.DictReader(open(Path(gdir) / f'{sp}.csv', encoding='utf-8-sig')):
            gold[(sp, r['id'])] = r
    for path in paths:
        c = collections.defaultdict(collections.Counter)
        for r in map(json.loads, open(path, encoding='utf-8')):
            k = (r['split'], r['id'])
            if k not in gold:
                continue
            g, o = gold[k], r['out']
            bo = set((g.get('bo_qua') or '').split())
            ok = {}
            for f in F:
                if f in bo:
                    continue
                if f.startswith('ma_'):
                    ok[f] = o.get(f, '') == g[f]
                else:
                    chuan = fold_duong if f == 'duong' else fold
                    ok[f] = chuan(o.get(f)) == chuan(g[f])
            x = c[k[0]]
            x['n'] += 1; x['du_6'] += all(ok.values())
            for f in F:
                x[f + '_n'] += f in ok; x[f] += ok.get(f, False)
        print(path)
        for sp, x in c.items():
            print(f"  {sp}: du 6 truong {x['du_6']}/{x['n']} ({100 * x['du_6'] / x['n']:.1f}%) | " +
                  ' '.join(f"{f} {100 * x[f] / max(1, x[f + '_n']):.1f}" for f in F))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2:])
