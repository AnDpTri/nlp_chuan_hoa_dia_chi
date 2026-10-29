"""Ca âm tính độc lập, chạy engine/validator thật chỉ trong repo_snapshot."""
import contextlib
import csv
import io
import json
from pathlib import Path
import shutil
import sys
import unicodedata

OUT = Path(__file__).resolve().parent
ROOT = OUT / 'repo_snapshot'
sys.path.insert(0, str(ROOT / 'data/test/scripts'))
import ai_review_engine as engine
import validate_dataset as validator
from build_labels import full

def read(p):
    with p.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))

def save(p, rows):
    with p.open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

def validate(p):
    stream = io.StringIO()
    result = None
    with contextlib.redirect_stdout(stream):
        try:
            result = validator.main(csv_file=str(p))
        except SystemExit as exc:
            status = 'FAIL' if exc.code else 'PASS'
        else:
            status = result.get('status', 'UNKNOWN') if isinstance(result, dict) else 'PASS'
    text = stream.getvalue()
    if result is None:
        try:
            result = json.JSONDecoder().raw_decode(text[text.find('{'):])[0]
        except (ValueError, json.JSONDecodeError):
            result = {'status': status, 'output_tail': text[-3000:]}
    return result, text

def set_admin(row, old, cat):
    target = cat.new_wi[cat.to_new[old['ma_xa']][0]['ma_xa_moi']]
    row.update(ma_xa_cu=old['ma_xa'], ma_huyen_cu=old['ma_huyen'], ma_tinh_cu=old['ma_tinh'],
               ma_xa=target['ma_xa'], ma_tinh=target['ma_tinh'], xa_phuong=full(target, 'xa'),
               tinh=full(cat.new_pi[target['ma_tinh']], 'tinh'))

def run_one(mode, cat, original):
    dest = OUT / ('fixture_v2_' + mode)
    dest.mkdir(exist_ok=False)
    for name in ('dia_chi_test.csv', 'bang_duyet_test.csv'):
        shutil.copy2(ROOT / 'data/test' / name, dest / name)
    rows = read(dest / 'dia_chi_test.csv')
    row = next(r for r in rows if r['id'] == 'VNTEST0001')
    if mode == 'absent_output':
        row['duong'] = 'ABSENT FROM INPUT SENTINEL'
    elif mode == 'house_substring':
        row['so_nha'] = 'Số 81'
    elif mode == 'house_admin_name':
        row['so_nha'] = 'Số Tân Phú'
    elif mode == 'absent_valid_admin_chain':
        old = next(w for w in cat.old_w if w['ten_xa'] == 'Bến Nghé' and len(cat.to_new[w['ma_xa']]) == 1)
        set_admin(row, old, cat)
    elif mode == 'ward_name_only_in_district':
        old = next(w for w in cat.old_w if w['ten_xa'] == 'Tân Phú' and w['ma_tinh'] == '79'
                   and w['ma_huyen'] != row['ma_huyen_cu'] and len(cat.to_new[w['ma_xa']]) == 1)
        set_admin(row, old, cat)
    elif mode == 'hamlet_number_mismatch_kp1':
        matches = [r for r in rows if 'kp 1' in engine.remove_diacritics(r['dau_vao'])
                   and r['trang_thai_nhan'] == 'da_duyet_ai']
        if not matches:
            return {'fixture': mode, 'skipped': 'Không có dòng thật KP 1 đã duyệt AI'}
        row = matches[0]
        row['thon_xom'] = 'Thôn 199999'
    elif mode == 'preserve_current_edit':
        row['duong'] = 'Đường Tây Thạnh'
        row['ghi_chu'] += ';CURRENT_EDIT_SENTINEL_KEEP_ME'
    else:
        raise ValueError(mode)
    sid = row['id']
    row['dia_chi_chuan'] = engine.build_dia_chi_chuan(row)
    fields = ['so_nha', 'duong', 'thon_xom', 'ma_xa_cu', 'ma_huyen_cu', 'ma_tinh_cu', 'ma_xa', 'ma_tinh', 'xa_phuong']
    inserted = {k: row[k] for k in fields}
    save(dest / 'dia_chi_test.csv', rows)
    before_validation, before_log = validate(dest / 'dia_chi_test.csv')
    (dest / 'validator_before.log').write_text(before_log, encoding='utf-8', newline='\n')
    run_log = io.StringIO()
    with contextlib.redirect_stdout(run_log):
        engine.main(test_csv_arg=dest / 'dia_chi_test.csv', bang_duyet_arg=dest / 'bang_duyet_test.csv',
                    jsonl_arg=dest / 'audit.jsonl', csv_arg=dest / 'audit.csv', checkpoint_dir_arg=dest / 'checkpoints',
                    phan_loai_csv_arg=dest / 'classification.csv', phan_loai_md_arg=dest / 'classification.md',
                    backup_csv_arg=ROOT / 'data/test/backup_before_ai_review/dia_chi_test.csv',
                    sources_arg=ROOT / 'data/test/goc/selected_sources.jsonl', labels_dir_arg=ROOT / 'data/test/agy')
    (dest / 'engine.log').write_text(run_log.getvalue(), encoding='utf-8', newline='\n')
    final = next(r for r in read(dest / 'dia_chi_test.csv') if r['id'] == sid)
    audit = next(r for r in map(json.loads, (dest / 'audit.jsonl').read_text(encoding='utf-8').splitlines()) if r['id'] == sid)
    after_validation, after_log = validate(dest / 'dia_chi_test.csv')
    (dest / 'validator_after.log').write_text(after_log, encoding='utf-8', newline='\n')
    return {'fixture': mode, 'id': sid, 'input': final['dau_vao'], 'inserted': inserted,
            'output': {k: final[k] for k in fields}, 'status': final['trang_thai_nhan'],
            'conclusion': audit['ket_luan'], 'reason': audit['ly_do_duyet'],
            'validator_before_engine': before_validation, 'validator_after_engine': after_validation,
            'preserves_sentinel': 'CURRENT_EDIT_SENTINEL_KEEP_ME' in final['ghi_chu']}

def main():
    cat = engine.Catalogues()
    original = read(ROOT / 'data/test/dia_chi_test.csv')
    results = [run_one(mode, cat, original) for mode in
               ('absent_output', 'house_substring', 'house_admin_name', 'absent_valid_admin_chain',
                'ward_name_only_in_district', 'hamlet_number_mismatch_kp1', 'preserve_current_edit')]
    raw = unicodedata.normalize('NFD', '12 Tây Thạnh')
    aligned = engine.align_output_components(raw, {'duong': 'Tay Thanh'})
    results.append({'fixture': 'nfd_offset', 'input': raw, 'alignment': aligned,
                    'normalized_match': engine.remove_diacritics(aligned['duong']['matched']),
                    'expected': 'tay thanh', 'passed': engine.remove_diacritics(aligned['duong']['matched']) == 'tay thanh'})
    (OUT / 'independent_negative_fixtures.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8', newline='\n')
    print(json.dumps([{'fixture': r['fixture'], 'status': r.get('status'), 'conclusion': r.get('conclusion'),
                       'validator_before_engine': r.get('validator_before_engine', {}).get('status'),
                       'validator_after_engine': r.get('validator_after_engine', {}).get('status'),
                       'passed': r.get('passed'), 'skipped': r.get('skipped')} for r in results], ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
