"""Deterministic stratified selection; inputs are never augmented or typo-generated."""
import hashlib
import json
from collections import Counter
from pathlib import Path
from admin_lookup import Catalogues, norm

ROOT = Path(__file__).resolve().parents[1]

def main():
    cat = Catalogues()
    pool = []
    seen = set()
    for line in (ROOT / 'goc/osm_public_candidates.jsonl').read_text(encoding='utf-8').splitlines():
        r = json.loads(line)
        key = norm(r['dau_vao'])
        if key in seen: continue
        seen.add(key)
        r['hints'] = cat.hints(r)
        r['sort_key'] = hashlib.sha256(r['source_url'].encode()).hexdigest()
        r['province_stratum'] = (r['hints']['old_provinces'] or ['unknown'])[0]
        pool.append(r)
    pool.sort(key=lambda r: r['sort_key'])
    selected = []
    used = set()
    counts = Counter()
    def add(r):
        if r['source_url'] in used: return
        selected.append(r); used.add(r['source_url']); counts[r['province_stratum']] += 1
    # Oversample evidence for split wards so at least 20 survive model/name verification.
    splits = [r for r in pool if r['hints']['split_candidates']]
    split_counts = Counter()
    for r in sorted(splits, key=lambda r: (r['input_mode'] != 'addr:full', r['sort_key'])):
        code = r['hints']['split_candidates'][0]
        if split_counts[code] >= 3 or counts[r['province_stratum']] >= 12: continue
        add(r); split_counts[code] += 1
        if len(selected) >= 55: break
    # Broad geographic coverage first; raw full-address tags take preference.
    groups = {}
    for r in pool:
        groups.setdefault(r['province_stratum'], []).append(r)
    for group in groups.values(): group.sort(key=lambda r: (r['input_mode'] != 'addr:full', not r['hints']['ward_candidates'], r['sort_key']))
    while len(selected) < 400:
        changed = False
        for province in sorted(groups, key=lambda p: (counts[p], p == 'unknown', p)):
            if counts[province] >= (15 if province != 'unknown' else 18): continue
            group = groups[province]
            while group and group[0]['source_url'] in used: group.pop(0)
            if group:
                add(group.pop(0)); changed = True
                if len(selected) == 400: break
        if not changed: break
    if len(selected) < 300: raise RuntimeError(f'Insufficient diversity-qualified candidates: {len(selected)}')
    for i, r in enumerate(selected, 1): r['id'] = f'VNTEST{i:04d}'
    (ROOT / 'goc/selected_sources.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in selected), encoding='utf-8', newline='\n')
    report = {'eligible_unique_pool': len(pool), 'split_evidence_pool': len(splits), 'selected': len(selected),
              'selected_split_evidence': sum(bool(r['hints']['split_candidates']) for r in selected),
              'source_modes': dict(Counter(r['input_mode'] for r in selected)), 'province_strata': dict(sorted(counts.items()))}
    (ROOT / 'selection.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8', newline='\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))

if __name__ == '__main__': main()
