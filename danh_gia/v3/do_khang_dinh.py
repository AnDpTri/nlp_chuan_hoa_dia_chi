"""Chính xác khi khẳng định và độ phủ của mã xã (và mã tỉnh) trên tập có nhãn.
- Khẳng định: hệ thống đưa ra mã (khác rỗng). Chính xác khi khẳng định = số khẳng định đúng nhãn / số khẳng định.
  (Nhãn rỗng mà hệ thống khẳng định một mã = khẳng định sai.)
- Độ phủ: số câu hệ thống khẳng định / tổng số câu; độ phủ đúng = khẳng định đúng / số câu nhãn có mã.
Dùng: do_khang_dinh.py <ket_qua.jsonl> <nhan.csv>[,<nhan2.csv>] [--cot-loai-tru bo_qua]"""
import csv, json, sys


def doc_nhan(paths):
    g = {}
    for p in paths.split(','):
        for r in csv.DictReader(open(p, encoding='utf-8-sig')):
            g[r['id']] = r
    return g


def do(ket_qua, nhan):
    gold = doc_nhan(nhan)
    out = {}
    for l in open(ket_qua, encoding='utf-8'):
        r = json.loads(l)
        if r['id'] in gold:
            out[r['id']] = r['out']
    kq = {}
    for f in ('ma_xa', 'ma_tinh'):
        rows = [(out[k].get(f, ''), g[f]) for k, g in gold.items() if k in out and f not in (g.get('bo_qua') or '').split()]
        kd = [(o, n) for o, n in rows if o]
        dung = sum(o == n for o, n in kd)
        co_nhan = sum(bool(n) for _, n in rows)
        kq[f] = {'so_cau': len(rows), 'khang_dinh': len(kd), 'khang_dinh_dung': dung,
                 'chinh_xac_khi_khang_dinh_pct': round(100 * dung / max(1, len(kd)), 2),
                 'do_phu_pct': round(100 * len(kd) / max(1, len(rows)), 2),
                 'do_phu_dung_pct': round(100 * dung / max(1, co_nhan), 2),
                 'khang_dinh_sai': len(kd) - dung,
                 'de_trong_dung': sum(not o and not n for o, n in rows)}
    return kq


if __name__ == '__main__':
    kq = do(sys.argv[1], sys.argv[2])
    for f, v in kq.items():
        print(f"  {f}: khẳng định {v['khang_dinh']}/{v['so_cau']} (phủ {v['do_phu_pct']}%) | chính xác khi khẳng định {v['chinh_xac_khi_khang_dinh_pct']}% "
              f"| khẳng định SAI {v['khang_dinh_sai']} | để trống đúng {v['de_trong_dung']} | phủ đúng {v['do_phu_dung_pct']}%")
