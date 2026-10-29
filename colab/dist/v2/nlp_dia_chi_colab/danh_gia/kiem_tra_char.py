"""Kiểm tra độc lập các artifact và sự giữ nguyên baseline sau tích hợp neural."""

import argparse
import json
from collections import Counter
from dataclasses import fields
from pathlib import Path

from src.kieu_du_lieu import KetQua
from src.duong_dan import tu_manifest
from .chay_ban_thu import ROOT, CORE, digest, norm
from .du_lieu_char import family_char
from .du_lieu_crf import doc_jsonl
from .huan_luyen_char import save_json


def audit(run_dir, output):
    sets = {s: doc_jsonl(run_dir / 'data' / (s + '.jsonl')) for s in ('train_cnn', 'train_ranker', 'dev_goc', 'dev_kho')}
    groups = {s: {r['training_group'] for r in sets[s]} for s in ('train_cnn', 'train_ranker')}
    group_overlap = groups['train_cnn'] & groups['train_ranker']
    families = {s: {family_char(r) for r in rs} for s, rs in sets.items()}
    train_families = families['train_cnn'] | families['train_ranker']
    dev_families = families['dev_goc'] | families['dev_kho']
    assert not group_overlap
    assert not (train_families & dev_families)
    manifest = json.loads((run_dir / 'snapshot/sha256.json').read_text(encoding='utf-8'))
    assert all(digest(tu_manifest(run_dir / 'snapshot', p)) == h for p, h in manifest.items())
    original_files = {'data/train_dev/train.csv': 'train.csv', 'data/train_dev/dev.csv': 'dev.csv'}
    original_files.update({'data/clean/' + p.name: 'clean/' + p.name for p in (run_dir / 'snapshot/clean').glob('*.csv')})
    assert all(digest(ROOT / src) == digest(run_dir / 'snapshot' / copy) for src, copy in original_files.items())
    rank_groups = doc_jsonl(run_dir / 'ranker_training_groups.jsonl')
    rank_ids = {r['id'] for r in sets['train_ranker']}
    assert all(r['id'] in rank_ids and r['group'] not in groups['train_cnn'] for r in rank_groups)
    baseline_checks, comparison, examples = {}, {}, []
    contract = [f.name for f in fields(KetQua)]
    for split in ('dev_goc', 'dev_kho'):
        for mode, old_file in [('luat_v3', 'luat_v3'), ('crf_cu', 'crf_ket_hop_mo')]:
            old = doc_jsonl(ROOT / 'danh_gia/ket_qua/crf_v1_01' / (old_file + '_' + split + '.jsonl'))
            new = doc_jsonl(output / (mode + '_' + split + '.jsonl'))
            assert len(old) == len(new)
            differences = [r['id'] for r, p in zip(old, new) if r['id'] != p['id'] or any(r[f] != p['prediction'][f] for f in contract)]
            assert not differences, (split, mode, differences[:3])
            baseline_checks[split + ':' + mode] = {'rows': len(new), 'all_result_fields_unchanged': True}
        old = doc_jsonl(output / ('crf_cu_' + split + '.jsonl'))
        new = doc_jsonl(output / ('char_ranker_' + split + '.jsonl'))
        c = Counter()
        picked = Counter()
        for r, p in zip(old, new):
            ref = p['reference']
            correct = lambda result: all(norm(result[f]) == norm(ref[f]) for f in CORE)
            old_ok, new_ok = correct(r['prediction']), correct(p['prediction'])
            category = 'both_match' if old_ok and new_ok else 'new_match' if new_ok else 'lost_match' if old_ok else 'both_mismatch'
            c[category] += 1
            if picked[category] < 2 and category in ('new_match', 'lost_match', 'both_mismatch'):
                examples.append({'split': split, 'category': category, 'id': p['id'], 'input': p['input'],
                                 'reference': ref, 'old_crf': {f: r['prediction'][f] for f in CORE},
                                 'char_ranker': {f: p['prediction'][f] for f in CORE}})
                picked[category] += 1
        comparison[split] = dict(c)
    results = {'cnn_ranker_group_overlap': len(group_overlap), 'train_dev_masked_house_family_overlap': len(train_families & dev_families),
               'snapshot_hashes_unchanged': True, 'original_train_dev_and_six_catalogues_unchanged': True,
               'ranker_training_groups': len(rank_groups), 'baseline_regression': baseline_checks,
               'comparison_to_combined_crf': comparison,
               'limits': 'Họ che số nhà và khai báo mẫu cha không chứng minh loại hết mọi tương đồng địa lý/ngữ nghĩa. Không dùng nhãn test để fit hoặc đo.'}
    save_json(output / 'KIEM_TRA.json', results)
    save_json(output / 'VI_DU_DUNG_SAI.json', examples)
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return results


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--run-dir', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    args = p.parse_args()
    audit(args.run_dir.resolve(), args.output.resolve())


if __name__ == '__main__':
    main()
