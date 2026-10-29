"""Phân loại phần chưa khớp bằng output đã đo; không chạy lại hoặc sửa nhãn."""

import argparse
from collections import Counter
import json
from pathlib import Path

from src.tien_xu_ly import bo_dau
from .chay_ban_thu import CORE, norm
from .du_lieu_crf import doc_jsonl
from .huan_luyen_char import save_json


def analyze(folder):
    stats = json.loads((folder / 'thong_ke.json').read_text(encoding='utf-8'))
    dictionary = json.loads((folder / 'tu_dien_duong_train.json').read_text(encoding='utf-8'))
    available = {(r['province'], norm(r['canonical'])) for r in dictionary['entries']}
    summary = {'scope': 'Phân tích hậu kiểm bằng nhãn dev, không dùng reference để chọn output.', 'splits': {}}
    for split in ('dev_goc', 'dev_kho'):
        rows = doc_jsonl(folder / f'ket_hop_{split}.jsonl')
        counts, fields = Counter(), Counter()
        examples = {}
        for row in rows:
            p, r = row['prediction'], row['reference']
            bad = {f for f in CORE if norm(p[f]) != norm(r[f])}
            if not bad:
                continue
            counts['remaining'] += 1
            fields.update(bad)
            detail_bad, admin_bad = bool(bad.intersection(CORE[:4])), bool(bad.intersection(CORE[4:]))
            counts['both' if detail_bad and admin_bad else 'detail_only' if detail_bad else 'admin_only'] += 1
            if all(bo_dau(norm(p[f])) == bo_dau(norm(r[f])) for f in CORE):
                counts['six_fields_only_accents'] += 1
                if norm(p['duong']) != norm(r['duong']):
                    key = 'accent_only_with_reference_road_in_dictionary' if (r['ma_tinh'], norm(r['duong'])) in available else 'accent_only_reference_road_absent_dictionary'
                    counts[key] += 1
                    examples.setdefault(key, []).append(row)
            if 'duong' in bad:
                key = 'reference_road_empty' if not r['duong'] else 'predicted_road_empty' if not p['duong'] else 'both_roads_nonempty_different'
                counts[key] += 1
                examples.setdefault(key, []).append(row)
        summary['splits'][split] = {'counts': dict(counts), 'fields_mismatch_overlapping': dict(fields),
                                     'examples': {k: v[:3] for k, v in examples.items()}}
        assert counts['remaining'] == len(rows) - stats['datasets'][split]['modes']['ket_hop']['dung_toan_bo_6_truong']
    changes = doc_jsonl(folder / 'thay_doi_tung_cau.jsonl')
    summary['boundary_changes_all'] = [r for r in changes if r['mode'] == 'bao_ve_duong']
    summary['normalization_gains_examples'] = [r for r in changes if r['mode'] == 'ten_train' and r['after_correct']][:5]
    save_json(folder / 'CHAN_DOAN_SAU_SUA.json', summary)
    print(json.dumps({s: v['counts'] for s, v in summary['splits'].items()}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--folder', type=Path, required=True)
    analyze(parser.parse_args().folder)
