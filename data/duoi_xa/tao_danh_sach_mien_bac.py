"""Tạo danh sách mọi xã cũ ở miền Bắc (kể cả Bắc Trung Bộ) và chia theo vùng cho các luồng thu thập
thôn, tổ dân phố, đường. Khác tao_danh_sach.py: không chỉ xã bị chia.

Dùng (từ gốc repo): py -3.12 data/duoi_xa/tao_danh_sach_mien_bac.py
Ghi rieng/du_lieu_duoi_xa/mb_<n>/{danh_sach_xa.csv, prompt.txt}.
"""
import csv
from collections import defaultdict
from pathlib import Path

GOC = Path(__file__).resolve().parents[2]
CLEAN = GOC / 'data' / 'clean'
RA = GOC / 'rieng' / 'du_lieu_duoi_xa'

# Chia theo vùng để mỗi luồng tìm văn bản của một nhóm tỉnh liền nhau.
VUNG = {
    1: ('Hà Nội', {'Hà Nội'}),
    2: ('Đồng bằng sông Hồng và Quảng Ninh', {'Hải Phòng', 'Hải Dương', 'Hưng Yên', 'Thái Bình', 'Nam Định',
                                               'Hà Nam', 'Ninh Bình', 'Bắc Ninh', 'Vĩnh Phúc', 'Quảng Ninh'}),
    3: ('Đông Bắc', {'Bắc Giang', 'Phú Thọ', 'Thái Nguyên', 'Tuyên Quang', 'Hà Giang', 'Lạng Sơn', 'Cao Bằng',
                     'Bắc Kạn'}),
    4: ('Tây Bắc', {'Lào Cai', 'Yên Bái', 'Điện Biên', 'Lai Châu', 'Sơn La', 'Hòa Bình', 'Hoà Bình'}),
    5: ('Thanh Hóa', {'Thanh Hóa'}),
    6: ('Nghệ An và Hà Tĩnh', {'Nghệ An', 'Hà Tĩnh'}),
}


def doc(ten):
    return list(csv.DictReader(open(CLEAN / ten, encoding='utf-8-sig')))


def main():
    moi = {r['ma_xa']: r for r in doc('moi_tinh_xa.csv')}
    dich = defaultdict(set)
    for r in doc('doi_chieu_xa_cu_moi.csv'):
        if r['ma_xa_cu']:
            dich[r['ma_xa_cu']].add(r['ma_xa_moi'])
    mau = (Path(__file__).parent / 'prompt_mien_bac.txt').read_text(encoding='utf-8')
    tong = 0
    for n, (ten_vung, tinh) in VUNG.items():
        rows = []
        for c in doc('cu_tinh_huyen_xa.csv'):
            if c['ten_tinh'] not in tinh:
                continue
            ds = sorted(dich.get(c['ma_xa'], ()))
            rows.append({
                'ma_xa_cu': c['ma_xa'], 'xa_cu': f"{c['loai_xa']} {c['ten_xa']}",
                'huyen_cu': c['ten_huyen'], 'tinh_cu': c['ten_tinh'],
                'bi_chia': 'co' if len(ds) > 1 else 'khong',
                'xa_moi_ung_vien': '; '.join(f"{m} {moi[m]['loai_xa']} {moi[m]['ten_xa']} ({moi[m]['ten_tinh']})"
                                             for m in ds if m in moi),
            })
        d = RA / f'mb_{n}'
        (d / 'nguon').mkdir(parents=True, exist_ok=True)
        with open(d / 'danh_sach_xa.csv', 'w', encoding='utf-8-sig', newline='') as f:
            w = csv.DictWriter(f, list(rows[0])); w.writeheader(); w.writerows(rows)
        ds_tinh = sorted({r['tinh_cu'] for r in rows})
        (d / 'prompt.txt').write_text(
            mau.replace('{LUONG}', f'mb_{n}').replace('{VUNG}', ten_vung).replace('{SO_XA}', str(len(rows)))
               .replace('{TINH}', ', '.join(ds_tinh)), encoding='utf-8')
        tong += len(rows)
        print(f'mb_{n} {ten_vung}: {len(rows)} xã, {len(ds_tinh)} tỉnh, '
              f'{sum(r["bi_chia"] == "co" for r in rows)} xã bị chia')
    print(f'tổng {tong} xã')


if __name__ == '__main__':
    main()
