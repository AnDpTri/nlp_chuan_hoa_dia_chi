"""Fail closed on corpus/provenance/schema/coverage errors; this is not a model evaluation."""
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
from admin_lookup import Catalogues, norm
from build_labels import FIELDS, full
from pin_catalogues import verify

ROOT = Path(__file__).resolve().parents[1]

def main():
    verify()
    errors, limitations = [], []
    def check(condition, message):
        if not condition: errors.append(message)
    cat = Catalogues()
    check(sum(r['loai_tinh']=='Thành phố' for r in cat.new_pi.values()) == 6, 'Target must use the six city types at 2025-07-01')
    with (ROOT / 'dia_chi_test.csv').open(encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f)
        check(reader.fieldnames == FIELDS, 'Incorrect final CSV schema/order')
        rows = list(reader)
    sources = [json.loads(s) for s in (ROOT / 'goc/selected_sources.jsonl').read_text(encoding='utf-8').splitlines()]
    by_id = {r['id']:r for r in sources}
    check(300 <= len(rows) <= 500, 'Corpus must contain 300–500 rows')
    check(len({r['id'] for r in rows}) == len(rows), 'Duplicate IDs')
    check(len({norm(r['dau_vao']) for r in rows}) == len(rows), 'Duplicate normalized input strings')
    check({r['id'] for r in rows} == set(by_id), 'Source/label ID mismatch')
    old_ds = {r['ma_huyen']:r for r in cat.old_d}
    for r in rows:
        identifier = r['id']; src = by_id[identifier]
        check(r['dau_vao'] == src['dau_vao'], identifier + ': input altered')
        check(r['nguon'] == src['source_url'], identifier + ': URL altered')
        check(src['name'] and any(src['tags'].get(k) for k in ('amenity','shop','office','tourism','craft','healthcare','leisure')), identifier + ': missing public POI evidence')
        if src['input_mode'] == 'addr:full':
            check(r['dau_vao'] == src['tags']['addr:full'], identifier + ': addr:full not verbatim')
        check(r['trang_thai_nhan'] in ('can_duyet','tu_dong_khop'), identifier + ': invalid review status')
        check(isinstance(json.loads(r['canh_bao']),list), identifier + ': warning JSON invalid')
        if r['ma_xa']:
            check(r['ma_xa'] in cat.new_wi, identifier + ': unknown new ward')
            check(cat.new_wi[r['ma_xa']]['ma_tinh'] == r['ma_tinh'], identifier + ': new hierarchy mismatch')
            check(r['xa_phuong'] == full(cat.new_wi[r['ma_xa']],'xa'), identifier + ': target ward name/type differs from dated snapshot')
        if r['ma_tinh']:
            check(r['tinh'] == full(cat.new_pi[r['ma_tinh']],'tinh'), identifier + ': target province name/type differs from dated snapshot')
        if r['ma_xa_cu']:
            ward = cat.old_wi.get(r['ma_xa_cu'])
            check(bool(ward), identifier + ': unknown old ward')
            if ward:
                check((ward['ma_huyen'],ward['ma_tinh']) == (r['ma_huyen_cu'],r['ma_tinh_cu']), identifier + ': old hierarchy mismatch')
            targets = {m['ma_xa_moi'] for m in cat.to_new[r['ma_xa_cu']]}
            if r['ma_xa']: check(r['ma_xa'] in targets, identifier + ': fabricated mapping')
            if len(targets) > 1:
                check(not r['ma_xa'] and not r['xa_phuong'], identifier + ': split ward silently resolved')
                check('xa_bi_chia' in json.loads(r['canh_bao']), identifier + ': missing split flag')
                check('xa_moi_ung_vien=' in r['ghi_chu'], identifier + ': missing split candidates')
        if r['ma_huyen_cu']:
            check(r['ma_huyen_cu'] in old_ds and old_ds[r['ma_huyen_cu']]['ma_tinh'] == r['ma_tinh_cu'], identifier + ': district/province mismatch')
    stats = json.loads((ROOT / 'statistics.json').read_text(encoding='utf-8'))
    check(stats['confirmed_old_split_rows'] >= 20, 'Fewer than 20 code-confirmed old split-ward addresses')
    province_count = len({r['ma_tinh'] for r in rows if r['ma_tinh']})
    check(province_count >= 20, 'Insufficient geographic spread')
    check(stats['eras'].get('cu',0) > 0 and stats['eras'].get('moi',0) > 0, 'Need both old and new era examples')
    check(stats['no_diacritics'] > 0, 'No naturally unaccented inputs')
    check(stats['abbreviations'] > 0, 'No naturally abbreviated inputs')
    limitations += ['Nhãn sơ bộ do máy, chưa có dòng nào được người duyệt; chưa được dùng làm gold test.',
                    'OSM là dữ liệu cộng đồng: nguồn thật không đồng nghĩa địa chỉ luôn đúng hoặc còn hiện hành.',
                    'Xem statistics.json để phân biệt chuỗi addr:full nguyên văn và chuỗi ghép từ thẻ cấu trúc.',
                    'Không cố tình tạo lỗi gõ hay bỏ dấu; độ khó và tỷ lệ lỗi bị giới hạn bởi nguồn tự nhiên.',
                    'Không sử dụng tọa độ hay tên tổ chức để điền đơn vị hành chính thiếu trong đầu vào.',
                    'Các xã bị chia giữ nhiều ứng viên; cần đối chiếu chi tiết địa phương nếu muốn chốt đáp án.']
    report = {'status':'PASS' if not errors else 'FAIL', 'errors':errors, 'rows':len(rows),
              'new_provinces_represented':province_count, 'confirmed_old_split_rows':stats['confirmed_old_split_rows'],
              'provisional_only':True, 'human_reviewed_rows':0, 'limitations':limitations,
              'csv_sha256':hashlib.sha256((ROOT / 'dia_chi_test.csv').read_bytes()).hexdigest()}
    (ROOT / 'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8',newline='\n')
    print(json.dumps(report,ensure_ascii=True,indent=2))
    if errors: raise SystemExit(1)

if __name__ == '__main__': main()
