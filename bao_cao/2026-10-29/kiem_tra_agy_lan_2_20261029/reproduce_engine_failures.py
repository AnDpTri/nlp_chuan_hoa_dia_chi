"""Tái hiện trên repo_snapshot cạnh script, chỉ ghi fixture mới trong work.

Không chạy trên dự án thật. Mỗi lượt tạo thư mục mới, không xóa fixture.
"""

import contextlib
import csv
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile


def read(path):
    with path.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def save(path, rows):
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def main():
    work = Path(__file__).resolve().parent
    root = work / 'repo_snapshot'
    if not (root / 'tests/test_review_validation.py').is_file():
        raise RuntimeError('Cần bản sao audit_agy_round2/repo_snapshot đã chụp; không chạy ở repo thật')
    sys.path.insert(0, str(root / 'data/test/scripts'))
    import ai_review_engine as engine
    import validate_dataset
    out = Path(tempfile.mkdtemp(prefix='reproduced_', dir=work))
    results = []
    for mode in ('current_edit', 'missing_span', 'unobserved_output'):
        d = out / mode
        d.mkdir()
        for name in ('dia_chi_test.csv', 'bang_duyet_test.csv'):
            shutil.copyfile(root / 'data/test' / name, d / name)
        labels = root / 'data/test/agy'
        baseline = root / 'data/test/backup_before_ai_review/dia_chi_test.csv'
        if mode == 'current_edit':
            for name in ('dia_chi_test.csv', 'bang_duyet_test.csv'):
                rows = read(d / name)
                row = next(r for r in rows if r['id'] == 'VNTEST0001')
                row['duong'] = 'Đường Tây Thạnh'
                row['ghi_chu' if name == 'dia_chi_test.csv' else 'ly_do_duyet'] = 'CURRENT_EDIT_SENTINEL_KEEP_ME'
                save(d / name, rows)
        if mode == 'missing_span':
            labels = d / 'labels'
            labels.mkdir()
            for p in (root / 'data/test/agy').glob('labels_*.json'):
                rows = json.loads(p.read_text(encoding='utf-8'))
                for row in rows:
                    if row['id'] == 'VNTEST0001':
                        row['duong'] = 'ABSENT_FROM_INPUT_SENTINEL'
                (labels / p.name).write_text(json.dumps(rows, ensure_ascii=False), encoding='utf-8')
        if mode == 'unobserved_output':
            rows = read(baseline)
            next(r for r in rows if r['id'] == 'VNTEST0001')['duong'] = 'ABSENT FROM INPUT SENTINEL'
            baseline = d / 'baseline.csv'
            save(baseline, rows)
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            engine.main(test_csv_arg=d / 'dia_chi_test.csv', bang_duyet_arg=d / 'bang_duyet_test.csv',
                        jsonl_arg=d / 'audit.jsonl', csv_arg=d / 'audit.csv', checkpoint_dir_arg=d / 'checkpoints',
                        phan_loai_csv_arg=d / 'classification.csv', phan_loai_md_arg=d / 'classification.md',
                        backup_csv_arg=baseline, sources_arg=root / 'data/test/goc/selected_sources.jsonl',
                        labels_dir_arg=labels)
            validation = validate_dataset.main(csv_file=str(d / 'dia_chi_test.csv')) if mode == 'unobserved_output' else None
        (d / 'execution.log').write_text(stdout.getvalue(), encoding='utf-8')
        row = next(r for r in read(d / 'dia_chi_test.csv') if r['id'] == 'VNTEST0001')
        log = next(r for r in (json.loads(s) for s in (d / 'audit.jsonl').read_text(encoding='utf-8').splitlines())
                   if r['id'] == 'VNTEST0001')
        results.append({'mode': mode, 'input': row['dau_vao'], 'final_road': row['duong'],
                        'final_notes': row['ghi_chu'], 'status': row['trang_thai_nhan'],
                        'conclusion': log['ket_luan'], 'evidence': log['can_cu_input'],
                        'validator_status': validation.get('status') if validation else None})
    (out / 'results.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'output': str(out), 'results': results}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
