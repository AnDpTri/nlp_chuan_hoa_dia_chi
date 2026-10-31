"""Tạo danh sách xã cũ bị chia (một xã cũ về nhiều xã mới) và chia cho các luồng thu thập.

Dùng (từ gốc repo): py -3.12 data/duoi_xa/tao_danh_sach.py
Ghi rieng/du_lieu_duoi_xa/luong_<n>/danh_sach_xa.csv và rieng/du_lieu_duoi_xa/danh_sach_xa_bi_chia.csv.
"""
import csv
from collections import defaultdict
from pathlib import Path

GOC = Path(__file__).resolve().parents[2]
CLEAN = GOC / 'data' / 'clean'
RA = GOC / 'rieng' / 'du_lieu_duoi_xa'

# Luồng theo tỉnh cũ. Hà Nội riêng một luồng (199/440 xã).
LUONG = {
    1: {'Hà Nội'},
    2: {'Hải Phòng', 'Hải Dương', 'Quảng Ninh', 'Thái Bình', 'Hưng Yên', 'Nam Định', 'Hà Nam', 'Ninh Bình',
        'Bắc Ninh', 'Bắc Giang', 'Vĩnh Phúc', 'Phú Thọ', 'Thái Nguyên', 'Tuyên Quang', 'Hà Giang', 'Lào Cai',
        'Yên Bái', 'Lạng Sơn', 'Cao Bằng', 'Bắc Kạn', 'Điện Biên', 'Lai Châu', 'Sơn La', 'Hoà Bình', 'Hòa Bình',
        'Thanh Hóa', 'Nghệ An', 'Hà Tĩnh'},
}


def doc(ten):
    return list(csv.DictReader(open(CLEAN / ten, encoding='utf-8-sig')))


def main():
    cu = {r['ma_xa']: r for r in doc('cu_tinh_huyen_xa.csv')}
    moi = {r['ma_xa']: r for r in doc('moi_tinh_xa.csv')}
    dich = defaultdict(set)
    for r in doc('doi_chieu_xa_cu_moi.csv'):
        if r['ma_xa_cu']:
            dich[r['ma_xa_cu']].add(r['ma_xa_moi'])
    rows = []
    for ma, ds in sorted(dich.items()):
        if len(ds) < 2 or ma not in cu:
            continue
        c = cu[ma]
        tinh = c['ten_tinh']
        luong = next((n for n, s in LUONG.items() if tinh in s), 3)
        rows.append({
            'luong': luong, 'ma_xa_cu': ma, 'xa_cu': f"{c['loai_xa']} {c['ten_xa']}",
            'huyen_cu': c['ten_huyen'], 'tinh_cu': tinh,
            'xa_moi_ung_vien': '; '.join(f"{m} {moi[m]['loai_xa']} {moi[m]['ten_xa']} ({moi[m]['ten_tinh']})"
                                         for m in sorted(ds)),
        })
    RA.mkdir(parents=True, exist_ok=True)
    cot = list(rows[0])
    with open(RA / 'danh_sach_xa_bi_chia.csv', 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, cot); w.writeheader(); w.writerows(rows)
    for n in sorted({r['luong'] for r in rows}):
        d = RA / f'luong_{n}'
        (d / 'nguon').mkdir(parents=True, exist_ok=True)
        part = [r for r in rows if r['luong'] == n]
        with open(d / 'danh_sach_xa.csv', 'w', encoding='utf-8-sig', newline='') as f:
            w = csv.DictWriter(f, cot); w.writeheader(); w.writerows(part)
        print(f'luong_{n}: {len(part)} xã, {len({r["tinh_cu"] for r in part})} tỉnh cũ')
    print(f'tổng {len(rows)} xã bị chia')


if __name__ == '__main__':
    main()
