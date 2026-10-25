"""Independent catalogue lookup for provisional labels. Does not import the system under test."""
import csv
import re
import unicodedata
from collections import defaultdict
from pathlib import Path
from asof_2025 import target_view

CLEAN = Path(__file__).resolve().parents[2] / 'clean'

def norm(text):
    text = unicodedata.normalize('NFD', text.lower().replace('đ', 'd'))
    text = ''.join(c for c in text if not unicodedata.combining(c))
    return re.sub(r'[^a-z0-9]+', ' ', text).strip()

def bare(text):
    text = norm(text)
    text = re.sub(r'^(thanh pho|thi tran|thi xa|dac khu|phuong|huyen|quan|tinh|xa|tp|tt|tx|q|p)\s+', '', text)
    return text

def stated_type(text):
    value = norm(text)
    aliases = {'tp':'thanh pho','tt':'thi tran','tx':'thi xa','p':'phuong','q':'quan'}
    for prefix in ('thanh pho','thi tran','thi xa','dac khu','phuong','huyen','quan','tinh','xa','tp','tt','tx','q','p'):
        if value.startswith(prefix + ' '): return aliases.get(prefix,prefix)
    return ''

def read(name):
    with (CLEAN / name).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))

class Catalogues:
    def __init__(self):
        self.old_p = read('cu_tinh.csv')
        self.new_p = read('moi_tinh.csv')
        self.old_d = read('cu_huyen.csv')
        self.old_w = read('cu_tinh_huyen_xa.csv')
        self.new_w = read('moi_tinh_xa.csv')
        self.maps = read('doi_chieu_xa_cu_moi.csv')
        raw_p, raw_w = self.new_p, self.new_w
        target_p, target_w, self.asof_changes, _ = target_view(raw_p,raw_w)
        self.old_pi = {r['ma_tinh']: r for r in self.old_p}
        self.new_pi = {r['ma_tinh']: r for r in target_p}
        self.new_wi = {r['ma_xa']: r for r in target_w}
        # Recognize both source type variants while emitting only the dated 2025 target type.
        self.new_p = target_p + [r for r in raw_p if r['loai_tinh'] != self.new_pi[r['ma_tinh']]['loai_tinh']]
        self.new_w = target_w + [r for r in raw_w if r['loai_xa'] != self.new_wi[r['ma_xa']]['loai_xa']]
        self.old_wi = {r['ma_xa']: r for r in self.old_w}
        self.to_new = defaultdict(list)
        self.province_map = defaultdict(set)
        for r in self.maps:
            if r['ma_xa_cu']:
                self.to_new[r['ma_xa_cu']].append(r)
            self.province_map[r['ma_tinh_cu']].add(r['ma_tinh_moi'])
        self.split_codes = {k for k, rs in self.to_new.items() if len({r['ma_xa_moi'] for r in rs}) > 1}
        self.ward_names = defaultdict(list)
        for r in self.old_w:
            self.ward_names[bare(r['ten_xa'])].append(r)
        self.province_alias = {'hn': 'ha noi', 'hcm': 'ho chi minh', 'tphcm': 'ho chi minh',
                               'tp hcm': 'ho chi minh', 'sai gon': 'ho chi minh', 'hue': 'hue'}

    def matches(self, rows, field, value):
        if not value: return []
        key = bare(value)
        key = self.province_alias.get(key, key) if field == 'ten_tinh' else key
        kind = stated_type(value)
        type_field = field.replace('ten_', 'loai_')
        matched = [r for r in rows if bare(r[field]) == key
                   and (not kind or type_field not in r or norm(r[type_field]) == kind)]
        code = field.replace('ten_','ma_')
        return list({r[code]:r for r in matched}.values())

    def hints(self, record):
        """Only source text/tags for selecting strata; never supplies target labels to the model."""
        text = record['dau_vao']
        n = ' ' + norm(text) + ' '
        tags = record['tags']
        province_texts = [tags.get(k, '') for k in ('addr:province', 'addr:state', 'addr:city')]
        ps = set()
        for r in self.old_p:
            key = bare(r['ten_tinh'])
            if (' ' + key + ' ') in n or any(bare(p) == key for p in province_texts if p):
                ps.add(r['ma_tinh'])
        ds = []
        for r in self.old_d:
            if ps and r['ma_tinh'] not in ps: continue
            key = bare(r['ten_huyen'])
            typed = norm(r['loai_huyen']) + ' ' + key
            if (' ' + typed + ' ') in n or any(bare(tags.get(k,'')) == key for k in ('addr:district', 'addr:city') if tags.get(k)):
                ds.append(r)
        ward_keys = set()
        for key in ('addr:ward', 'addr:suburb', 'addr:quarter'):
            if tags.get(key): ward_keys.add(bare(tags[key]))
        segments = [bare(x) for x in re.split('[,;]', text)]
        if len(segments) > 2:
            ward_keys.update(segments[1:])
        tokens = norm(text).split()
        for i, token in enumerate(tokens):
            offset = 2 if tokens[i:i+2] == ['thi', 'tran'] else 1
            if token in ('phuong', 'xa', 'p') or offset == 2:
                for length in range(1, 6):
                    ward_keys.add(' '.join(tokens[i+offset:i+offset+length]))
        found = []
        possibilities = [r for key in ward_keys for r in self.ward_names.get(key, [])]
        for r in possibilities:
            if ps and r['ma_tinh'] not in ps: continue
            if ds and r['ma_huyen'] not in {d['ma_huyen'] for d in ds}: continue
            found.append(r)
        split = [r for r in found if r['ma_xa'] in self.split_codes]
        return {'old_provinces': sorted(ps), 'districts': sorted({r['ma_huyen'] for r in ds}),
                'ward_candidates': sorted({r['ma_xa'] for r in found}),
                'split_candidates': sorted({r['ma_xa'] for r in split})}
