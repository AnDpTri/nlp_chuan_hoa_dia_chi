"""Kiểm đếm độc lập train/dev bổ sung, không dùng output mô hình làm nhãn."""
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
import re
import sys
import unicodedata

OUT = Path(__file__).resolve().parent
ROOT = OUT / 'repo_snapshot'
sys.path.insert(0, str(ROOT))
from src.tien_xu_ly import token_co_vi_tri
from src.danh_muc import DanhMuc
from src.crf_chi_tiet import tao_nhan

FIELDS = ('so_nha', 'ngo_ngach_hem', 'thon_xom', 'duong')
def csv_rows(p):
    with p.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))
def jsonl(p):
    return [json.loads(s) for s in p.read_text(encoding='utf-8-sig').splitlines() if s.strip()]
def plain(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s.casefold().replace('đ', 'd')) if not unicodedata.combining(c))
def key(s):
    return ''.join(c for c in plain(s) if c.isalnum())
def family(row, annotation=None):
    text = row['dau_vao']
    if annotation:
        s = annotation.get('spans', {}).get('so_nha')
        if s:
            return key(text[:s['start']] + text[s['end']:])
    target = key(re.sub(r'^(?:số nhà|số|so nha|so)\s+', '', row.get('so_nha', ''), flags=re.I))
    value = key(text)
    if target and target in value:
        value = value.replace(target, '', 1)
    return value
def save(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8', newline='\n')

def main():
    folder = ROOT / 'data/train_dev/bo_sung_v1'
    dm = DanhMuc(ROOT / 'data/clean')
    refs = {s: csv_rows(folder / f) for s, f in [('train', 'train_bo_sung.csv'), ('dev', 'dev_kho.csv')]}
    annotations = {s: {r['id']: r for r in jsonl(folder / (s + '_spans.jsonl'))} for s in refs}
    originals = {s: {r['id']: r for r in csv_rows(ROOT / 'data/train_dev' / (s + '.csv'))} for s in refs}
    counts, errors, incompatible, parent_errors, name_errors = {}, [], [], [], []
    new_examples = []
    for split, rows in refs.items():
        ids = [r['id'] for r in rows]
        assert len(ids) == len(set(ids)) and set(ids) == set(annotations[split])
        span_count = Counter()
        flags = Counter()
        for row in rows:
            sid, text = row['id'], row['dau_vao']
            ann = annotations[split][sid]
            if ann['dau_vao'] != text:
                errors.append({'id': sid, 'error': 'input_csv_jsonl_mismatch'})
            for token in ann['tokens']:
                if not 0 <= token['start'] < token['end'] <= len(text) or text[token['start']:token['end']] != token['token']:
                    errors.append({'id': sid, 'error': 'token_offset'})
            spans_for_bio = []
            runtime = token_co_vi_tri(text)
            mismatch = []
            occupied = set()
            for field, span in ann['spans'].items():
                if not span:
                    continue
                span_count[field] += 1
                a, b = span['start'], span['end']
                if field not in FIELDS or not 0 <= a < b <= len(text) or text[a:b] != span['text']:
                    errors.append({'id': sid, 'error': 'char_span', 'field': field})
                chars = set(range(a, b))
                if occupied & chars:
                    errors.append({'id': sid, 'error': 'span_overlap'})
                occupied |= chars
                inds = [i for i, t in enumerate(ann['tokens']) if a <= t['start'] < t['end'] <= b]
                if not inds or ann['tokens'][inds[0]]['start'] != a or ann['tokens'][inds[-1]]['end'] != b:
                    errors.append({'id': sid, 'error': 'span_token_source_mismatch'})
                else:
                    spans_for_bio.append((field, inds[0], inds[-1] + 1))
                rt = [t for t in runtime if max(a, t.bat_dau) < min(b, t.ket_thuc)]
                if not rt or rt[0].bat_dau != a or rt[-1].ket_thuc != b:
                    mismatch.append(field)
            if tao_nhan(len(ann['tokens']), spans_for_bio) != [t['bio_tag'] for t in ann['tokens']]:
                errors.append({'id': sid, 'error': 'BIO_vs_span'})
            if bool(ann.get('tokenizer_runtime_compatible')) != (not mismatch):
                errors.append({'id': sid, 'error': 'runtime_flag_false_claim'})
            if mismatch and ann['usable_for_span_training']:
                errors.append({'id': sid, 'error': 'mismatch_marked_usable'})
            if mismatch:
                incompatible.append({'id': sid, 'split': split, 'fields': mismatch, 'usable': ann['usable_for_span_training'], 'input': text})
            flags.update({'usable_span': int(ann['usable_for_span_training']), 'usable_canonical': int(ann['usable_for_canonical_training'])})
            for col, codecol, role in [('xa_phuong', 'ma_xa', 'xa'), ('tinh', 'ma_tinh', 'tinh')]:
                if row.get(codecol) and row[col] != dm.ten_day_du('moi', row[codecol]):
                    name_errors.append({'id': sid, 'field': col, 'value': row[col], 'expected': dm.ten_day_du('moi', row[codecol])})
            old = dm.don_vi.get(('cu', row['ma_xa_cu']))
            if old and (old.ma_cha != row['ma_huyen_cu'] or dm.lay('cu', old.ma_cha).ma_cha != row['ma_tinh_cu']):
                errors.append({'id': sid, 'error': 'old_hierarchy'})
            if row['ma_xa'] and row['ma_tinh'] not in dm.dich_tinh('moi', row['ma_xa']):
                errors.append({'id': sid, 'error': 'new_hierarchy'})
            parent = re.search(r'derived_(?:train|dev):(\w+)', row['nguon'])
            if parent:
                parent_id = parent[1]
                source = originals[split].get(parent_id)
                if not source or any(row[f] != source[f] for f in ('ma_xa_cu', 'ma_huyen_cu', 'ma_tinh_cu')):
                    parent_errors.append({'id': sid, 'parent': parent_id, 'split': split})
            is_new = sid.startswith('VNTRAIN_BS_') and int(sid.rsplit('_', 1)[1]) > 2037 or sid.startswith('VNDEV_KHO_') and int(sid.rsplit('_', 1)[1]) > 464
            if is_new:
                new_examples.append({'split': split, 'row': row, 'spans': ann['spans'], 'flags': {k: ann[k] for k in ('usable_for_span_training', 'usable_for_canonical_training')}})
        counts[split] = {'rows': len(rows), 'span_counts': dict(span_count), **dict(flags),
                         'declared_groups': len({r['nhom_mau_goc'] for r in rows}),
                         'new_rows': sum(x['split'] == split for x in new_examples)}
    masked = {s: {family(r, annotations[s][r['id']]) for r in rs} for s, rs in refs.items()}
    original_masked = {s: {family(r) for r in rs.values()} for s, rs in originals.items()}
    overlap = {'new_train_new_dev_masked': len(masked['train'] & masked['dev']),
               'new_train_original_dev_masked': len(masked['train'] & original_masked['dev']),
               'new_dev_original_train_masked': len(masked['dev'] & original_masked['train']),
               'declared_groups_train_dev': len({r['nhom_mau_goc'] for r in refs['train']} & {r['nhom_mau_goc'] for r in refs['dev']})}
    manifest = json.loads((folder / 'manifest.json').read_text(encoding='utf-8'))
    manifest_errors = [n for n, v in manifest['files'].items() if hashlib.sha256((folder / n).read_bytes()).hexdigest() != v['sha256'] or (folder / n).stat().st_size != v['size_bytes']]
    old_rows = {('train', r['id']): r for r in csv_rows(folder / 'snapshot_pre_fix_20261029/train_bo_sung.csv')}
    old_rows.update({('dev', r['id']): r for r in csv_rows(folder / 'snapshot_pre_fix_20261029/dev_kho.csv')})
    current = {(s, r['id']): r for s, rs in refs.items() for r in rs}
    links = csv_rows(folder / 'doi_chieu_snapshot_v1_v2.csv')
    link_errors, categories = [], Counter()
    for link in links:
        categories[link['v1_disposition_category']] += 1
        if link['v2_counterpart_id']:
            old = old_rows[link['v1_split'], link['v1_id']]
            new = current.get((link['v1_split'], link['v2_counterpart_id']))
            if not new or old['ma_xa_cu'] != new['ma_xa_cu'] or old['duong'] != new['duong']:
                link_errors.append({'link': link, 'old': old, 'new': new})
    token_file = jsonl(folder / 'token_spans.jsonl')
    by_id = {r['id']: r for rows in annotations.values() for r in rows.values()}
    token_jsonl_mismatches = [r['id'] for r in token_file if r != by_id.get(r['id'])]
    road_key = lambda s: key(re.sub(r'^(duong|pho|xa lo|quoc lo|dai lo|tinh lo)\s+', '', plain(s)))
    road_name_errors = [r for r in link_errors if r['new'] and road_key(r['old']['duong']) != road_key(r['new']['duong'])]
    result = {'counts': counts, 'mechanical_errors': errors, 'name_errors': name_errors,
              'parent_code_errors': parent_errors, 'runtime_incompatible_count': len(incompatible),
              'runtime_incompatible_by_split': dict(Counter(r['split'] for r in incompatible)),
              'overlap_checks': overlap, 'manifest_errors': manifest_errors,
              'snapshot_counterpart_categories': dict(categories), 'counterpart_errors': len(link_errors),
              'counterpart_distinct_road_name_errors': len(road_name_errors),
              'counterpart_road_spelling_only_differences': len(link_errors) - len(road_name_errors),
              'token_spans_rows': len(token_file), 'token_spans_mismatches': token_jsonl_mismatches,
              'new_declared_groups': {s: len({x['row']['nhom_mau_goc'] for x in new_examples if x['split'] == s}) for s in refs}}
    save('train_independent_audit.json', result)
    save('train_runtime_incompatible.json', incompatible)
    save('snapshot_counterpart_errors.json', link_errors)
    save('new_training_examples.json', new_examples)
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
