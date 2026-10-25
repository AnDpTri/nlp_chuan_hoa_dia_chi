"""Attach administrative codes independently of src/; generate auditable provisional test data."""
import csv
import json
import re
from collections import Counter
from pathlib import Path
from admin_lookup import Catalogues, norm, bare, stated_type
from pin_catalogues import verify

ROOT = Path(__file__).resolve().parents[1]
FIELDS = ['id','dau_vao','nguon','so_nha','ngo_ngach_hem','thon_xom','duong',
          'ma_xa_cu','ma_huyen_cu','ma_tinh_cu','ma_xa','ma_tinh','xa_phuong','tinh',
          'dia_chi_chuan','canh_bao','trang_thai_nhan','ghi_chu']

def unique(rows, code):
    return list({r[code]: r for r in rows}.values())

def full(row, level):
    name, kind = row['ten_' + level], row['loai_' + level]
    if norm(name).startswith(norm(kind) + ' '): return name
    return kind + ' ' + name

def evidence(value, source):
    return not value or (' ' + norm(value) + ' ') in (' ' + norm(source) + ' ')

def format_component(value, category):
    """Normalize only explicit type words and case, never invent missing place-name accents."""
    prefixes = {'street': {'duong':'Đường', 'pho':'Phố', 'dai lo':'Đại lộ', 'quoc lo':'Quốc lộ', 'tinh lo':'Tỉnh lộ'},
                'alley': {'ngo':'Ngõ', 'ngach':'Ngách', 'hem':'Hẻm', 'kiet':'Kiệt', 'ng':'Ngõ'},
                'hamlet': {'thon':'Thôn', 'xom':'Xóm', 'ap':'Ấp', 'ban':'Bản', 'to dan pho':'Tổ dân phố', 'khu pho':'Khu phố', 'kp':'Khu phố'}}
    words = value.split()
    acronyms = {'QL','ĐT','DT','TL','HL','KP','KCN','KCX','CC','TT','TP','HCM','VN','II','III','IV','VI','VII','VIII','IX'}
    def case_name(text):
        return re.sub(r'[^\W\d_]+', lambda m:m.group(0).upper() if m.group(0).upper() in acronyms else m.group(0).capitalize(), text)
    for prefix, expanded in sorted(prefixes[category].items(), key=lambda x:-len(x[0])):
        length = len(prefix.split())
        if norm(' '.join(words[:length])) == prefix:
            return expanded + (' ' + case_name(' '.join(words[length:])) if len(words) > length else '')
    return case_name(value)

def resolve(cat, src, label):
    result = {k:'' for k in FIELDS}
    result.update(id=src['id'], dau_vao=src['dau_vao'], nguon=src['source_url'])
    warnings, notes = [], []
    if label.get('ghi_chu'): notes.append(label['ghi_chu'])
    names = {}
    for key in ('so_nha','ngo_ngach_hem','thon_xom','duong','ten_xa','ten_huyen','ten_tinh'):
        value = label[key].strip()
        if not evidence(value, src['dau_vao']):
            warnings.append('nhan_khong_co_trong_dau_vao')
            notes.append(f'{key}={value!r}: không khớp đoạn nguồn, bỏ nhãn tự sinh')
            value = ''
        names[key] = value
        if key in result: result[key] = value
    remaining = ' ' + norm(src['dau_vao']) + ' '
    for value in sorted((v for v in names.values() if v), key=lambda v:-len(norm(v))):
        remaining = remaining.replace(' ' + norm(value) + ' ', ' ')
    remaining = re.sub(r'\b(viet nam|vietnam|vn|so|district|province|city|commune|ward|hamlet)\b', ' ', remaining)
    remaining = ' '.join(remaining.split())
    if remaining:
        warnings.append('phan_chua_phan_loai')
        notes.append('phan_chua_phan_loai=' + remaining)
    if '/' in result['so_nha']:
        warnings.append('so_nha_can_duyet')
    if src['input_mode'] == 'addr:full':
        for field, tag in [('so_nha','addr:housenumber'),('duong','addr:street')]:
            source_value = src['tags'].get(tag, '')
            canonical = lambda x: re.sub(r'^(so|duong|pho)\s+', '', norm(x))
            if result[field] and source_value and canonical(result[field]) != canonical(source_value):
                warnings.append('mau_thuan_the_osm')
                notes.append(f'{tag}={source_value!r} khác addr:full; giữ addr:full, cần so nguồn')
    for field, category in [('duong','street'),('ngo_ngach_hem','alley'),('thon_xom','hamlet')]:
        value = result[field]
        if value and re.search('[A-Za-z]',value) and not re.search('[à-ỹÀ-ỸđĐ]',value):
            warnings.append('phan_du_khong_dau_can_duyet')
        result[field] = format_component(value,category) if value else ''
    old_ps = cat.matches(cat.old_p, 'ten_tinh', names['ten_tinh'])
    new_ps = cat.matches(cat.new_p, 'ten_tinh', names['ten_tinh'])
    ds = cat.matches(cat.old_d, 'ten_huyen', names['ten_huyen'])
    if old_ps: ds = [r for r in ds if r['ma_tinh'] in {p['ma_tinh'] for p in old_ps}]
    old_ws = cat.matches(cat.old_w, 'ten_xa', names['ten_xa'])
    if old_ps: old_ws = [r for r in old_ws if r['ma_tinh'] in {p['ma_tinh'] for p in old_ps}]
    if names['ten_huyen']:
        old_ws = [r for r in old_ws if r['ma_huyen'] in {d['ma_huyen'] for d in ds}]
    new_ws = cat.matches(cat.new_w, 'ten_xa', names['ten_xa'])
    if new_ps: new_ws = [r for r in new_ws if r['ma_tinh'] in {p['ma_tinh'] for p in new_ps}]
    elif names['ten_tinh'] and old_ps:
        scope = set().union(*(cat.province_map[p['ma_tinh']] for p in old_ps))
        new_ws = [r for r in new_ws if r['ma_tinh'] in scope]
    if names['ten_tinh'] and not old_ps and not new_ps:
        warnings.append('khong_khop_tinh'); old_ws = []; new_ws = []; ds = []
    # Do not silently ignore an explicit district which cannot be identified.
    if names['ten_huyen'] and not ds:
        warnings.append('khong_khop_huyen'); old_ws = []; new_ws = []
    old_ws, new_ws, ds = unique(old_ws, 'ma_xa'), unique(new_ws, 'ma_xa'), unique(ds, 'ma_huyen')
    new_code = ''
    old_ward = None
    era = 'thieu_thong_tin'
    if names['ten_huyen']:
        era = 'cu'
        if len(old_ws) == 1: old_ward = old_ws[0]
        elif len(old_ws) > 1: warnings.append('trung_ten_xa')
    elif len(old_ws) == 1:
        targets = {r['ma_xa_moi'] for r in cat.to_new[old_ws[0]['ma_xa']]}
        if len(new_ws) == 1 and targets != {new_ws[0]['ma_xa']}:
            warnings.append('mo_ho_moc_cu_moi')
            notes.append('Tên xã dùng được ở cả mốc cũ và mới với kết quả khác nhau; chưa chọn mốc.')
            era = 'mo_ho'
        elif len(new_ws) == 1 and targets == {new_ws[0]['ma_xa']}:
            # Output is invariant to era; old code is not asserted without old-era evidence.
            new_code = new_ws[0]['ma_xa']; era = 'cu_moi_cung_ket_qua'
        else:
            old_ward = old_ws[0]; era = 'cu'
    elif len(new_ws) == 1 and not old_ws:
        new_code = new_ws[0]['ma_xa']; era = 'moi'
    elif names['ten_xa']:
        warnings.append('trung_ten_xa' if old_ws or new_ws else 'khong_khop_xa')
    if old_ward:
        result.update(ma_xa_cu=old_ward['ma_xa'], ma_huyen_cu=old_ward['ma_huyen'], ma_tinh_cu=old_ward['ma_tinh'])
        targets = sorted({r['ma_xa_moi'] for r in cat.to_new[old_ward['ma_xa']]})
        if len(targets) == 1: new_code = targets[0]
        elif len(targets) > 1:
            warnings.append('xa_bi_chia')
            notes.append('xa_moi_ung_vien=' + json.dumps([{'ma_xa':k, 'ten':full(cat.new_wi[k], 'xa')} for k in targets], ensure_ascii=False))
        else: warnings.append('thieu_doi_chieu')
    elif len(ds) == 1:
        result.update(ma_huyen_cu=ds[0]['ma_huyen'], ma_tinh_cu=ds[0]['ma_tinh'])
        # Five old island districts have no commune children and map directly.
        direct = [r for r in cat.maps if not r['ma_xa_cu'] and not r['ten_xa_cu'] and r['ma_huyen_cu'] == ds[0]['ma_huyen']]
        direct_targets = {r['ma_xa_moi'] for r in direct}
        if not names['ten_xa'] and len(direct_targets) == 1: new_code = next(iter(direct_targets))
    elif len(old_ps) == 1 and era not in ('moi','cu_moi_cung_ket_qua','mo_ho'):
        # Province identity old/new may be invariant. Store old only for clearly old province or district.
        if not new_ps or names['ten_huyen']: result['ma_tinh_cu'] = old_ps[0]['ma_tinh']
    if new_code:
        ward = cat.new_wi[new_code]
        result.update(ma_xa=new_code, ma_tinh=ward['ma_tinh'], xa_phuong=full(ward, 'xa'))
    elif result['ma_tinh_cu']:
        targets = cat.province_map[result['ma_tinh_cu']]
        if len(targets) == 1: result['ma_tinh'] = next(iter(targets))
    elif len(new_ps) == 1:
        result['ma_tinh'] = new_ps[0]['ma_tinh']
    elif len(old_ps) == 1:
        targets = cat.province_map[old_ps[0]['ma_tinh']]
        if len(targets) == 1: result['ma_tinh'] = next(iter(targets))
    if result['ma_tinh']:
        result['tinh'] = full(cat.new_pi[result['ma_tinh']], 'tinh')
        named_type = stated_type(names['ten_tinh'])
        valid_types = {norm(cat.new_pi[result['ma_tinh']]['loai_tinh'])}
        if result['ma_tinh_cu']: valid_types.add(norm(cat.old_pi[result['ma_tinh_cu']]['loai_tinh']))
        if named_type and named_type not in valid_types:
            warnings.append('loai_nguon_khac_moc_2025')
    if result['ma_xa'] and not result['ma_xa_cu']:
        named_type = stated_type(names['ten_xa'])
        if named_type and named_type != norm(cat.new_wi[result['ma_xa']]['loai_xa']):
            warnings.append('loai_nguon_khac_moc_2025')
    if not names['ten_tinh']: warnings.append('thieu_tinh_dau_vao')
    if not result['ma_tinh']: warnings.append('thieu_tinh')
    if not names['ten_xa'] and not new_code: warnings.append('thieu_xa')
    elif not result['ma_xa'] and 'xa_bi_chia' not in warnings: warnings.append('chua_xac_dinh_xa')
    # A fixed administrative outcome does not imply machine interpretation has been human reviewed.
    review = bool(warnings or notes)
    result['trang_thai_nhan'] = 'can_duyet' if review else 'tu_dong_khop'
    result['canh_bao'] = json.dumps(sorted(set(warnings)), ensure_ascii=False)
    street = result['duong']
    if street and not re.match(r'^(duong|pho|quoc lo|tinh lo|dai lo|dt|ql)\b', norm(street)):
        street = 'Đường ' + street
    number = result['so_nha']
    if number and not norm(number).startswith('so '): number = 'Số ' + number
    result['dia_chi_chuan'] = ', '.join(x for x in (number, result['ngo_ngach_hem'], result['thon_xom'], street, result['xa_phuong'], result['tinh']) if x)
    notes.append('moc_nhan=' + era)
    notes.append('nguon_dau_vao=' + src['input_mode'])
    result['ghi_chu'] = '; '.join(notes)
    return result, era

def main():
    verify()
    sources = [json.loads(line) for line in (ROOT / 'goc/selected_sources.jsonl').read_text(encoding='utf-8').splitlines()]
    labels = {}
    for path in sorted((ROOT / 'agy').glob('labels_*.json')):
        for row in json.loads(path.read_text(encoding='utf-8')):
            if row['id'] in labels: raise ValueError('Duplicate model label ID')
            labels[row['id']] = row
    if set(labels) != {r['id'] for r in sources}: raise ValueError('Missing/extra model IDs')
    cat = Catalogues()
    rows, eras = [], Counter()
    for src in sources:
        row, era = resolve(cat, src, labels[src['id']]); rows.append(row); eras[era] += 1
    with (ROOT / 'dia_chi_test.csv').open('w', encoding='utf-8', newline='') as out:
        writer = csv.DictWriter(out, fieldnames=FIELDS, lineterminator='\n'); writer.writeheader(); writer.writerows(rows)
    stats = {'rows':len(rows), 'status':dict(Counter(r['trang_thai_nhan'] for r in rows)),
             'eras':dict(eras), 'new_provinces':dict(sorted(Counter(r['tinh'] or '(chưa xác định)' for r in rows).items())),
             'no_diacritics':sum(r['dau_vao'] == norm(r['dau_vao']) or not re.search('[à-ỹÀ-ỸđĐ]', r['dau_vao']) for r in rows),
             'has_diacritics':sum(bool(re.search('[à-ỹÀ-ỸđĐ]',r['dau_vao'])) for r in rows),
             'abbreviations':sum(bool(re.search(r'\b(?:TPHCM|TP|Q|P|TT|TX|HCM|HN|KP|QL|ĐT|NG)\.?(?=\d|\s|[.,;]|$)',r['dau_vao'],re.IGNORECASE)) for r in rows),
             'with_hamlet_component':sum(bool(r['thon_xom']) for r in rows),
             'warnings':dict(sorted(Counter(w for r in rows for w in json.loads(r['canh_bao'])).items())),
             'old_ward_types':dict(Counter(cat.old_wi[r['ma_xa_cu']]['loai_xa'] for r in rows if r['ma_xa_cu'])),
             'new_ward_types':dict(Counter(cat.new_wi[r['ma_xa']]['loai_xa'] for r in rows if r['ma_xa'])),
             'confirmed_old_split_rows':sum(r['ma_xa_cu'] in cat.split_codes for r in rows),
             'unique_old_split_codes':len({r['ma_xa_cu'] for r in rows if r['ma_xa_cu'] in cat.split_codes}),
             'input_modes':dict(Counter(r['input_mode'] for r in sources))}
    (ROOT / 'statistics.json').write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding='utf-8', newline='\n')
    print(json.dumps(stats, ensure_ascii=True, indent=2))

if __name__ == '__main__': main()
