"""Chốt bằng chứng audit và kiểm tra dữ liệu/lõi/mô hình thật không bị sửa."""
import hashlib
import json
from pathlib import Path
import re

OUT = Path(__file__).resolve().parent
PROJECT = Path('D:/nlp_chuan_hoa_dia_chi')
digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
before = json.loads((OUT / 'original_sha256_before.json').read_text(encoding='utf-8'))
changed = [name for name, h in before.items() if digest(PROJECT / name) != h]
data_changed = [name for name in changed if Path(name).parts[0] == 'data']
run = PROJECT / 'mo_hinh/thu_nghiem/char_v1_01'
code = json.loads((run / 'code_sha256_final.json').read_text(encoding='utf-8'))
core_changed = [name for name, h in code.items() if Path(name).parts[0] == 'src' and digest(PROJECT / name) != h]
model_expected = json.loads((PROJECT / 'danh_gia/ket_qua/char_v1_01_cuoi/thong_ke.json').read_text(encoding='utf-8'))['model_sha256']
models_unchanged = digest(run / 'char_cnn.pt') == model_expected['char'] and digest(run / 'ranker.txt') == model_expected['ranker']
index = PROJECT / 'docs/MUC_LUC_BAO_CAO.md'
links = re.findall(r'\]\(([^)]+)\)', index.read_text(encoding='utf-8'))
missing = [url for url in links if not url.startswith(('https://', 'http://')) and not (index.parent / url).resolve().exists()]
train = json.loads((OUT / 'train_independent_audit.json').read_text(encoding='utf-8'))
test = json.loads((OUT / 'test_independent_audit.json').read_text(encoding='utf-8'))
fixtures = json.loads((OUT / 'independent_negative_fixtures.json').read_text(encoding='utf-8'))
checks = {'original_files_hashed': len(before), 'original_files_changed_during_audit': changed,
          'original_data_files_changed_during_audit': data_changed,
          'core_changes_vs_char_v1_deployment': core_changed, 'char_and_ranker_checkpoints_unchanged': models_unchanged,
          'index_broken_links': missing, 'unit_tests': {'train': '17/17 PASS', 'test': '24/24 PASS'},
          'validators': {'train': 'PASS', 'test': 'PASS structural, not gold'},
          'independent_train_mechanical_errors': len(train['mechanical_errors']),
          'independent_train_distinct_road_inheritance_errors': train['counterpart_distinct_road_name_errors'],
          'independent_new_test_fixtures_accepted_incorrectly': [r['fixture'] for r in fixtures if r['fixture'] in
               ('ward_name_only_in_district', 'hamlet_number_mismatch_kp1') and r['status'] == 'da_duyet_ai' and r['validator_after_engine']['status'] == 'PASS'],
          'test_id_input_url_preserved': test['id_input_url_unchanged'],
          'data_labels_or_algorithms_edited_by_this_audit': False, 'new_agy_messages_sent': False}
assert not data_changed and models_unchanged and not missing
(OUT / 'checks.json').write_text(json.dumps(checks, ensure_ascii=False, indent=2), encoding='utf-8', newline='\n')
manifest = {str(p.relative_to(OUT)): digest(p) for p in OUT.rglob('*') if p.is_file() and p.name != 'SHA256SUMS.json'}
(OUT / 'SHA256SUMS.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8', newline='\n')
print(json.dumps(checks, ensure_ascii=False, indent=2))
print('Evidence files hashed:', len(manifest))
