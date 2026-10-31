"""Chấm file đầu ra từng câu trên tập test cũ (đã mở) theo cùng quy ước bộ chấm test: so chuỗi chuẩn hóa NFC/casefold.
Dùng: cham_tung_cau.py <a.jsonl> [b.jsonl ...]"""
import duong_dan as dd  # gốc repo, CODE_ROOT vào sys.path
import csv, json, sys, unicodedata

F = ('so_nha', 'ngo_ngach_hem', 'thon_xom', 'duong', 'ma_xa', 'ma_tinh')


def n(s):
    return ' '.join(unicodedata.normalize('NFC', s or '').casefold().split())


gold = {r['id']: r for r in csv.DictReader(open(dd.TEST, encoding='utf-8-sig'))}
for p in sys.argv[1:]:
    out = {json.loads(l)['id']: json.loads(l)['out'] for l in open(p, encoding='utf-8')}
    du = sum(all(n(out[k][f]) == n(g[f]) for f in F) for k, g in gold.items())
    tung = {f: round(100 * sum(n(out[k][f]) == n(g[f]) for k, g in gold.items()) / len(gold), 2) for f in F}
    print(f'{p:28} đủ 6 trường {du}/{len(gold)} ({100 * du / len(gold):.2f}%) |', tung)
