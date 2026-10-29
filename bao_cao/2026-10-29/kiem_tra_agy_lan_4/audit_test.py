"""Đối chiếu bàn giao test hiện hành với snapshot lần 3; không sửa nhãn."""
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
import re
import unicodedata

OUT = Path(__file__).resolve().parent
ROOT = OUT / 'repo_snapshot'
PREVIOUS = Path('C:/Users/andan/Documents/Codex/2026-10-29/d-nlp-chuan-hoa-dia-chi/work/audit_agy_round3/repo_snapshot')
def read(p):
    with p.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))
def jsonl(p):
    return [json.loads(s) for s in p.read_text(encoding='utf-8').splitlines() if s.strip()]
def save(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8', newline='\n')

def main():
    rows = read(ROOT / 'data/test/dia_chi_test.csv')
    before = {r['id']: r for r in read(PREVIOUS / 'data/test/dia_chi_test.csv')}
    assert len(rows) == len(before) == 400 and {r['id'] for r in rows} == set(before)
    source_changes = [r['id'] for r in rows if any(r[f] != before[r['id']][f] for f in ('dau_vao', 'nguon'))]
    assert not source_changes
    old_wards = {r['ma_xa']: r for r in read(ROOT / 'data/clean/cu_tinh_huyen_xa.csv')}
    new_wards = {r['ma_xa']: r for r in read(ROOT / 'data/clean/moi_tinh_xa.csv')}
    mappings = {}
    for r in read(ROOT / 'data/clean/doi_chieu_xa_cu_moi.csv'):
        if r['ma_xa_cu']:
            mappings.setdefault(r['ma_xa_cu'], set()).add(r['ma_xa_moi'])
    split = [r for r in rows if len(mappings.get(r['ma_xa_cu'], set())) > 1]
    split_errors = [r['id'] for r in split if r['ma_xa'] or r['xa_phuong'] or 'xa_bi_chia' not in json.loads(r['canh_bao'])]
    audit = jsonl(ROOT / 'data/test/nhat_ky_ai_duyet.jsonl')
    audit_map = {r['id']: r for r in audit}
    assert len(audit_map) == len(audit) == 400
    mismatch = []
    audited_fields = ('dau_vao', 'nguon', 'so_nha', 'ngo_ngach_hem', 'thon_xom', 'duong',
                      'ma_xa_cu', 'ma_huyen_cu', 'ma_tinh_cu', 'ma_xa', 'ma_tinh', 'xa_phuong', 'tinh', 'dia_chi_chuan')
    for row in rows:
        for field in audited_fields:
            if row[field] != audit_map[row['id']].get(field):
                mismatch.append({'id': row['id'], 'field': field, 'row': row[field], 'audit': audit_map[row['id']].get(field)})
    changes = []
    for row in rows:
        prior = before[row['id']]
        different = {f: {'before': prior[f], 'after': row[f]} for f in row if f != 'ghi_chu' and prior.get(f) != row[f]}
        if different:
            changes.append({'id': row['id'], 'input': row['dau_vao'], 'changes': different})
    web_1286 = [r['id'] for r in audit if '1286' in r.get('can_cu_web', '')]
    web_wrong_split_1232 = [r['id'] for r in audit if re.search(r'chia thành 3.*1232', r.get('can_cu_web', '') + ' ' + r.get('can_cu_danh_muc', ''))]
    summary = {'rows': len(rows), 'id_input_url_unchanged': True,
               'statuses': dict(Counter(r['trang_thai_nhan'] for r in rows)),
               'conclusions': dict(Counter(r['ket_luan'] for r in audit)),
               'split_rows_current_mapping': len(split), 'split_errors': split_errors,
               'additional_split_ids_vs_round3': sorted(r['id'] for r in split if 'xa_bi_chia' not in json.loads(before[r['id']]['canh_bao'])),
               'audit_output_field_mismatches': mismatch,
               'non_note_changed_rows_vs_round3': len(changes),
               'lookup_timestamps_nonempty': sum(bool(r.get('thoi_diem_tra_cuu')) for r in audit),
               'audit_ids_citing_1286': web_1286, 'audit_ids_still_claiming_split_1232': web_wrong_split_1232}
    save('test_independent_audit.json', summary)
    save('test_changes_vs_round3.json', changes)
    print(json.dumps(summary, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
