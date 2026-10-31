"""Cổng kiểm dữ liệu dưới xã (thôn, xóm, tổ dân phố, đường, dải số nhà) do các luồng thu thập.

Mỗi luồng ghi rieng/du_lieu_duoi_xa/luong_<n>/du_lieu.csv và lưu nguồn trong luong_<n>/nguon/.
Cổng này KHÔNG tin luồng tự báo cáo: mọi dòng phải qua đủ các phép kiểm dưới đây mới được nhận.

Dùng (từ gốc repo): py -3.12 data/duoi_xa/kiem_tra.py [luong_1 luong_2 ...]
Ghi rieng/du_lieu_duoi_xa/ket_qua/{hop_le.csv, bi_loai.csv, bao_cao.json}.
"""
import csv
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

GOC = Path(__file__).resolve().parents[2]
CLEAN = GOC / 'data' / 'clean'
THU_MUC = GOC / 'rieng' / 'du_lieu_duoi_xa'

COT = ['ma_xa_cu', 'loai', 'ten', 'so_nha_tu', 'so_nha_den', 'ma_xa_moi',
       'nguon_url', 'file_goc', 'file_van_ban', 'trich_dan_nguyen_van', 'ngay_van_ban']
LOAI = {'thon', 'xom', 'to_dan_pho', 'ap', 'ban', 'khu_pho', 'khom', 'duong', 'pho', 'ngo'}


def gon(s):
    """Chuẩn hóa để so trích dẫn: NFC, thường, gộp khoảng trắng."""
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFC', s or '')).strip().casefold()


def bo_dau(s):
    s = unicodedata.normalize('NFD', (s or '').replace('đ', 'd').replace('Đ', 'D'))
    return ''.join(c for c in s if unicodedata.category(c) != 'Mn').casefold()


def la_so(s):
    return bool(re.fullmatch(r'\d+[A-Za-z]?', s.strip())) if s else True


def doc(p):
    return list(csv.DictReader(open(p, encoding='utf-8-sig')))


def main(luong):
    dich = defaultdict(set)
    for r in doc(CLEAN / 'doi_chieu_xa_cu_moi.csv'):
        if r['ma_xa_cu']:
            dich[r['ma_xa_cu']].add(r['ma_xa_moi'])
    bi_chia = {k for k, v in dich.items() if len(v) > 1}
    van_ban = {}

    nhan, loai_bo = [], []
    for ten_luong in luong:
        d = THU_MUC / ten_luong
        p = d / 'du_lieu.csv'
        if not p.exists():
            loai_bo.append({'luong': ten_luong, 'dong': 0, 'ly_do': 'khong_co_du_lieu_csv'})
            continue
        rows = doc(p)
        thieu = [c for c in COT if rows and c not in rows[0]]
        if thieu:
            loai_bo.append({'luong': ten_luong, 'dong': 0, 'ly_do': 'thieu_cot:' + ','.join(thieu)})
            continue
        for i, r in enumerate(rows, start=2):
            r = {k: (v or '').strip() for k, v in r.items()}
            ly_do = []
            if r['ma_xa_cu'] not in bi_chia:
                ly_do.append('xa_cu_khong_thuoc_danh_sach_bi_chia')
            elif r['ma_xa_moi'] not in dich[r['ma_xa_cu']]:
                ly_do.append('xa_moi_khong_phai_dich_cua_xa_cu')
            if r['loai'] not in LOAI:
                ly_do.append('loai_khong_hop_le')
            if not r['ten']:
                ly_do.append('thieu_ten')
            if not (la_so(r['so_nha_tu']) and la_so(r['so_nha_den'])):
                ly_do.append('so_nha_khong_hop_le')
            if not r['nguon_url'].startswith(('http://', 'https://')):
                ly_do.append('thieu_nguon_url')
            fg = d / 'nguon' / r['file_goc'] if r['file_goc'] else None
            if not fg or not fg.is_file():
                ly_do.append('khong_co_file_goc')
            fv = d / 'nguon' / r['file_van_ban'] if r['file_van_ban'] else None
            if not fv or not fv.is_file():
                ly_do.append('khong_co_file_van_ban')
            else:
                if fv not in van_ban:
                    van_ban[fv] = gon(fv.read_text(encoding='utf-8', errors='replace'))
                td = gon(r['trich_dan_nguyen_van'])
                if len(td) < 15:
                    ly_do.append('trich_dan_qua_ngan')
                elif td not in van_ban[fv]:
                    ly_do.append('trich_dan_khong_co_trong_van_ban')
                elif bo_dau(r['ten']) not in bo_dau(r['trich_dan_nguyen_van']):
                    ly_do.append('trich_dan_khong_nhac_ten')
            r['luong'] = ten_luong
            r['dong'] = i
            (loai_bo if ly_do else nhan).append({**r, 'ly_do': ';'.join(ly_do)} if ly_do else r)

    # Trùng và mâu thuẫn: cùng xã cũ + loại + tên (+ dải số nhà) mà khác xã mới thì loại tất cả.
    nhom = defaultdict(list)
    for r in nhan:
        nhom[(r['ma_xa_cu'], r['loai'], bo_dau(r['ten']), r['so_nha_tu'], r['so_nha_den'])].append(r)
    hop_le = []
    for k, ds in nhom.items():
        if len({r['ma_xa_moi'] for r in ds}) > 1:
            loai_bo += [{**r, 'ly_do': 'mau_thuan_xa_moi'} for r in ds]
        else:
            hop_le.append(ds[0])

    ra = THU_MUC / 'ket_qua'
    ra.mkdir(parents=True, exist_ok=True)
    cot_ra = ['luong', 'dong'] + COT
    with open(ra / 'hop_le.csv', 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, cot_ra, extrasaction='ignore'); w.writeheader(); w.writerows(hop_le)
    with open(ra / 'bi_loai.csv', 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, cot_ra + ['ly_do'], extrasaction='ignore'); w.writeheader(); w.writerows(loai_bo)
    bao_cao = {
        'hop_le': len(hop_le), 'bi_loai': len(loai_bo),
        'xa_cu_co_du_lieu': len({r['ma_xa_cu'] for r in hop_le}), 'xa_cu_bi_chia': len(bi_chia),
        'theo_luong': dict(Counter(r['luong'] for r in hop_le)),
        'theo_loai': dict(Counter(r['loai'] for r in hop_le)),
        'ly_do_loai': dict(Counter(x for r in loai_bo for x in r['ly_do'].split(';'))),
    }
    (ra / 'bao_cao.json').write_text(json.dumps(bao_cao, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(bao_cao, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    luong = sys.argv[1:] or sorted(p.name for p in THU_MUC.glob('luong_*') if p.is_dir())
    main(luong)
