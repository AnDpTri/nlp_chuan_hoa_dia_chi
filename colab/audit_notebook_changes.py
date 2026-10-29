"""Audit notebook hiện hành và tái hiện phép sửa chuỗi trong bộ nhớ, không chạy mã ô."""

import argparse
import ast
import difflib
import hashlib
import json
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def constants(source):
    out = {}
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    out[target.id] = ast.literal_eval(node.value)
    return out


def compile_result(source, name):
    try:
        compile(source, name, 'exec')
        return {'syntax_valid': True}
    except SyntaxError as e:
        return {'syntax_valid': False, 'line': e.lineno, 'message': e.msg, 'source_line': e.text.strip() if e.text else ''}


def audit(current, output):
    output.mkdir(parents=True, exist_ok=False)
    raw = current.read_bytes()
    live = json.loads(raw)
    baseline_path = ROOT / 'colab/ViDeBERTa_Drive.ipynb'
    baseline_raw = baseline_path.read_bytes()
    baseline = json.loads(baseline_raw)
    (output / 'NOTEBOOK_HIEN_TAI.ipynb').write_bytes(raw)
    (output / 'NOTEBOOK_TRUOC_SUA.ipynb').write_bytes(baseline_raw)
    cell_id = lambda c: c.get('id', c.get('metadata', {}).get('id'))
    old = {cell_id(c): c for c in baseline['cells']}
    new = {cell_id(c): c for c in live['cells']}
    changed, added, diff, evidence = [], [], [], []
    for index, cell in enumerate(live['cells']):
        cid = cell_id(cell)
        source = ''.join(cell.get('source', []))
        if cid not in old:
            added.append({'id': cid, 'index': index, 'execution_count': cell.get('execution_count'), 'type': cell['cell_type']})
        elif source != ''.join(old[cid].get('source', [])):
            changed.append({'id': cid, 'index': index, 'execution_count': cell.get('execution_count')})
            diff.extend(difflib.unified_diff(old[cid]['source'], cell['source'], fromfile='before:' + cid, tofile='current:' + cid))
        if cid not in old or any(x['id'] == cid for x in changed) or cid == 'cell-12':
            evidence.append({'cell_id': cid, 'index': index, 'execution_count': cell.get('execution_count'),
                             'source': source, 'outputs': cell.get('outputs', [])})
    archive = ROOT / 'colab/dist/nlp_dia_chi_colab_v1.zip'
    simulated, file_checks = {}, []
    with zipfile.ZipFile(archive) as z:
        prefix = 'nlp_dia_chi_colab/'
        manifest = json.loads(z.read(prefix + 'BUNDLE_MANIFEST.json'))
        for name, entry in manifest['files'].items():
            if name.startswith(('src/', 'danh_gia/', 'colab/')) and name.endswith('.py'):
                local = ROOT / name
                h = hashlib.sha256(local.read_bytes()).hexdigest() if local.exists() else None
                file_checks.append({'file': name, 'matches_delivered_bundle': h == entry['sha256']})
        digest_cell = next((c for c in live['cells'] if 'new_digest_func' in ''.join(c.get('source', []))), None)
        if digest_cell:
            values = constants(''.join(digest_cell['source']))
            original = z.read(prefix + 'danh_gia/chay_ban_thu.py').decode('utf-8')
            pattern = r'def digest\(path\):\s+return hashlib\.sha256\(path\.read_bytes\(\)\)\.hexdigest\(\)'
            try:
                altered = re.sub(pattern, values['new_digest_func'], original)
                simulated['digest_patch'] = {**compile_result(altered, 'gemini_digest.py'),
                                             'matched': altered != original,
                                             'bundle_checksum_would_change': altered != original}
                (output / 'TAI_HIEN_chay_ban_thu.py.txt').write_text(altered, encoding='utf-8', newline='\n')
            except re.error as error:
                simulated['digest_patch'] = {'regex_error': str(error)}
        trainer_cell = next((c for c in live['cells'] if 'old_block =' in ''.join(c.get('source', []))), None)
        if trainer_cell:
            values = constants(''.join(trainer_cell['source']))
            original = z.read(prefix + 'colab/train_videberta.py').decode('utf-8')
            altered = original.replace(values['old_block'], values['new_block'])
            simulated['trainer_patch'] = {**compile_result(altered, 'gemini_train.py'), 'matched': altered != original,
                                         'bundle_checksum_would_change': altered != original}
            (output / 'TAI_HIEN_train_videberta.py.txt').write_text(altered, encoding='utf-8', newline='\n')
        source_manifest = json.loads(z.read(prefix + 'bundle_data/snapshot/sha256.json'))
        posix_missing = [n for n in source_manifest if prefix + 'bundle_data/snapshot/' + n not in z.namelist()]
        normalized_missing = [n for n in source_manifest if prefix + 'bundle_data/snapshot/' + n.replace('\\', '/') not in z.namelist()]
    assert hashlib.sha256(current.read_bytes()).hexdigest() == hashlib.sha256(raw).hexdigest(), 'Notebook đổi trong lúc audit'
    result = {'baseline_cells': len(baseline['cells']), 'current_cells': len(live['cells']),
              'current_sha256': hashlib.sha256(raw).hexdigest(), 'changed_cells': changed, 'added_cells': added,
              'string_patch_reproduction_not_execution': simulated,
              'windows_manifest_paths_not_portable': posix_missing, 'missing_after_normalizing_separators': normalized_missing,
              'local_code_vs_delivered_bundle': file_checks,
              'drive_training_run_dir_exists': (current.parents[1] / 'nlp_chuan_hoa_dia_chi/videberta_v1_01').exists(),
              'source_notebook_unchanged_by_audit': True,
              'limits': 'Mã runtime /content không được đọc trực tiếp; lỗi cú pháp được tái hiện từ literal và phép sửa đã lưu trong notebook. Không gán mọi thay đổi trên ổ D cho Gemini.'}
    (output / 'KIEM_TRA.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8', newline='\n')
    (output / 'O_MA_VA_DAU_RA.json').write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding='utf-8', newline='\n')
    (output / 'THAY_DOI.diff').write_text(''.join(diff), encoding='utf-8', newline='\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'local_code_vs_delivered_bundle'}, ensure_ascii=False, indent=2))


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--notebook', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    audit(args.notebook, args.output)


if __name__ == '__main__':
    main()
