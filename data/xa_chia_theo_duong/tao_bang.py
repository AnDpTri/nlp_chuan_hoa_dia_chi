"""Dựng bảng phân giải XÃ CŨ BỊ CHIA theo TÊN ĐƯỜNG từ dữ liệu tham chiếu số nhà OSM + ranh giới GIS xã mới.

Một dòng (ma_xa_cu, khoa_duong) -> ma_xa_moi được nhận khi:
- điểm OSM có tọa độ gốc nằm gọn trong một xã mới (GIS_1_xa_diem_OSM);
- thẻ xã/huyện/tỉnh OSM xác định đúng MỘT xã cũ, và xã cũ đó bị chia (nhiều xã mới đích);
- xã mới theo GIS nằm trong danh sách đích chính thức của xã cũ (loại thẻ ghi lẫn tên mới / tọa độ lệch);
- cặp (xã cũ, đường) có ít nhất NGUONG_DIEM điểm và tất cả cùng một xã mới.
Loại mọi điểm trùng nguồn với test cũ, test mới niêm phong, dev, train.
Chạy lại khi dữ liệu tham chiếu được bổ sung.

Dùng: tao_bang.py <so_nha_gan_xa_moi_GIS.csv> [--giu-lai-danh-gia 20]
  -> bang_xa_chia_theo_duong.csv (dùng chạy thật)
  -> nếu có --giu-lai-danh-gia P: bang_xa_chia_theo_duong_danh_gia.csv (dựng từ phần còn lại)
     và diem_giu_lai_danh_gia.csv (P% điểm theo mã băm osm_id, KHÔNG nằm trong bảng đánh giá)"""
import collections, csv, hashlib, json, sys, unicodedata
from pathlib import Path

D = Path(__file__).resolve().parent
C = D.parent / 'clean'
NGUONG_DIEM = 2


def fold(s):
    s = unicodedata.normalize('NFD', (s or '').replace('đ', 'd').replace('Đ', 'D'))
    return ''.join(c for c in s if unicodedata.category(c) != 'Mn').casefold()


def khoa_ten(s, tien_to=('thanh pho ', 'tinh ', 'quan ', 'huyen ', 'thi xa ', 'phuong ', 'xa ', 'thi tran ')):
    s = fold(s).strip()
    for p in tien_to:
        if s.startswith(p):
            s = s[len(p):]
    return ''.join(c for c in s if c.isalnum())


def khoa_duong(s):
    """Phải giống hệt DanhMuc.khoa_duong (src/danh_muc.py)."""
    s = fold(s).strip()
    for p in ('duong ', 'pho ', 'd. ', 'd.'):
        if s.startswith(p):
            s = s[len(p):]
            break
    return ''.join(c for c in s if c.isalnum())


def nguon_loai():
    urls = set()
    for p in (r'D:\nlp_chuan_hoa_dia_chi\data\test\goc\selected_sources.jsonl', r'D:\nlp_rf_gate\tm\test_moi\goc\selected_sources.jsonl'):
        if Path(p).exists():
            urls |= {json.loads(l)['source_url'] for l in open(p, encoding='utf-8')}
    for p in (r'D:\nlp_rf_gate\inputs\dev_goc.csv', r'D:\nlp_rf_gate\inputs\dev_kho.csv', r'D:\nlp_rf_gate\inputs\train.csv',
              r'D:\nlp_chuan_hoa_dia_chi\data\test\dia_chi_test.csv'):
        if Path(p).exists():
            urls |= {r['nguon'] for r in csv.DictReader(open(p, encoding='utf-8-sig')) if r.get('nguon')}
    return urls


def giu_lai(osm_id, pct):
    return int(hashlib.sha256(osm_id.encode()).hexdigest()[:8], 16) % 100 < pct


def dung(diem):
    nhom = collections.defaultdict(collections.Counter)
    for d in diem:
        nhom[(d['ma_xa_cu'], d['khoa_duong'])][d['ma_xa_moi']] += 1
    bang = []
    for (mx, kd), c in sorted(nhom.items()):
        if len(c) == 1 and sum(c.values()) >= NGUONG_DIEM:
            bang.append({'ma_xa_cu': mx, 'khoa_duong': kd, 'ma_xa_moi': next(iter(c)), 'so_diem': sum(c.values())})
    return bang, nhom


def ghi(p, rows, cols):
    with open(p, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=cols, lineterminator='\n'); w.writeheader(); w.writerows(rows)


def main(nguon, pct=0):
    cu = list(csv.DictReader(open(C / 'cu_tinh_huyen_xa.csv', encoding='utf-8-sig')))
    idx = collections.defaultdict(list)
    for r in cu:
        idx[khoa_ten(r['ten_xa'])].append(r)
    dc = collections.defaultdict(set)
    for r in csv.DictReader(open(C / 'doi_chieu_xa_cu_moi.csv', encoding='utf-8-sig')):
        dc[r['ma_xa_cu']].add(r['ma_xa_moi'])
    loai_nguon = nguon_loai()
    dem = collections.Counter(); diem = []
    for r in csv.DictReader(open(nguon, encoding='utf-8-sig')):
        if r['source_url'] in loai_nguon:
            dem['trung_test_dev_train'] += 1; continue
        if r['trang_thai_GIS'] != 'GIS_1_xa_diem_OSM' or not (r['xa_the_osm'] and r['duong'] and r['ma_xa_moi_GIS']):
            continue
        cand = [x for x in idx[khoa_ten(r['xa_the_osm'])]
                if (not r['huyen_the_osm'] or khoa_ten(x['ten_huyen']) == khoa_ten(r['huyen_the_osm']))
                and (not r['tinh_the_osm'] or khoa_ten(x['ten_tinh']) == khoa_ten(r['tinh_the_osm']))]
        if len(cand) != 1 or len(dc[cand[0]['ma_xa']]) < 2:
            continue
        if r['ma_xa_moi_GIS'] not in dc[cand[0]['ma_xa']]:
            dem['gis_ngoai_ung_vien'] += 1; continue
        diem.append({'osm_id': r['osm_type'] + '/' + r['osm_id'], 'ma_xa_cu': cand[0]['ma_xa'], 'khoa_duong': khoa_duong(r['duong']),
                     'ma_xa_moi': r['ma_xa_moi_GIS'], 'so_nha': r['so_nha'], 'duong': r['duong'], 'xa_cu': cand[0]['ten_xa'],
                     'huyen_cu': cand[0]['ten_huyen'], 'tinh_cu': cand[0]['ten_tinh']})
    cols = ['ma_xa_cu', 'khoa_duong', 'ma_xa_moi', 'so_diem']
    bang, nhom = dung(diem)
    ghi(D / 'bang_xa_chia_theo_duong.csv', bang, cols)
    tk = {'diem_xa_chia_hop_le': len(diem), 'bo': dict(dem), 'cap_xa_duong': len(nhom), 'dong_bang': len(bang),
          'xa_cu_bi_chia_co_bang': len({b['ma_xa_cu'] for b in bang}), 'nguong_diem': NGUONG_DIEM}
    if pct:
        hoc = [d for d in diem if not giu_lai(d['osm_id'], pct)]
        thu = [d for d in diem if giu_lai(d['osm_id'], pct)]
        bang_dg, _ = dung(hoc)
        ghi(D / 'bang_xa_chia_theo_duong_danh_gia.csv', bang_dg, cols)
        ghi(D / 'diem_giu_lai_danh_gia.csv', thu, list(thu[0]))
        tk.update(diem_hoc=len(hoc), diem_giu_lai=len(thu), dong_bang_danh_gia=len(bang_dg))
    (D / 'thong_ke.json').write_text(json.dumps(tk, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(tk, ensure_ascii=False))


if __name__ == '__main__':
    pct = int(sys.argv[sys.argv.index('--giu-lai-danh-gia') + 1]) if '--giu-lai-danh-gia' in sys.argv else 0
    main(sys.argv[1], pct)
