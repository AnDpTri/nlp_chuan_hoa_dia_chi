"""Bản sao cô lập cho audit agy lần 4; không chạy engine trên dữ liệu thật."""
import hashlib
import json
import shutil
import sys
from pathlib import Path

PROJECT = Path('D:/nlp_chuan_hoa_dia_chi')
OUT = Path(__file__).resolve().parent
SNAP = OUT / 'repo_snapshot'
SNAP.mkdir(exist_ok=False)
digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
files = []
for folder in ('src', 'tests', 'data/clean', 'data/train_dev', 'data/test'):
    for p in (PROJECT / folder).rglob('*'):
        relative = p.relative_to(PROJECT)
        if not p.is_file() or '__pycache__' in relative.parts or 'logs' in relative.parts:
            continue
        if p.suffix in ('.pbf', '.part', '.pyc') or p.name == 'osm_public_candidates.jsonl':
            continue
        files.append(p)
files += [PROJECT / 'data/raw/goc/conversion-table.xlsx']
before = {str(p.relative_to(PROJECT)): digest(p) for p in files}
for p in files:
    target = SNAP / p.relative_to(PROJECT)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(p, target)
assert all(digest(p) == before[str(p.relative_to(PROJECT))] == digest(SNAP / p.relative_to(PROJECT)) for p in files)
(OUT / 'original_sha256_before.json').write_text(json.dumps(before, indent=2), encoding='utf-8', newline='\n')

sys.path.insert(0, str(PROJECT / 'docs/antigravity_rpc'))
from agy_app_rpc import AppClient, find_base_url, summarize
client = AppClient(find_base_url())
finals = {}
for name, cid in [('test', 'feca2faf-c8c5-4c07-8293-c9f0c9e553e4'), ('train', '388e264d-6447-42fb-b64f-559ba8e2e86d')]:
    data = client.trajectory(cid)
    visible = [{'step': i, 'response': s.get('plannerResponse', {}).get('response', '')}
               for i, s in enumerate(data['trajectory'].get('steps', []))
               if s.get('plannerResponse', {}).get('response')]
    finals[name] = {'status': summarize(data, cid), 'last_visible_responses': visible[-4:]}
(OUT / 'conversation_finals.json').write_text(json.dumps(finals, ensure_ascii=False, indent=2), encoding='utf-8', newline='\n')
print(json.dumps({'snapshot_files': len(files), 'snapshot_bytes': sum(p.stat().st_size for p in files),
                  'final_responses': {n: v['last_visible_responses'][-1] for n, v in finals.items()}}, ensure_ascii=False, indent=2))
