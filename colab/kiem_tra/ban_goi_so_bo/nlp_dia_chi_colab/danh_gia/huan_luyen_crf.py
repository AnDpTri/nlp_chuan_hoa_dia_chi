"""Huấn luyện hai đối chứng CRF CPU, cấu hình cố định không chọn theo dev."""

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import time
from collections import Counter
from pathlib import Path

from .du_lieu_crf import prepare, doc_jsonl
from .chay_ban_thu import memory
from src.crf_chi_tiet import dac_trung

PARAMS = {'c1': 0.1, 'c2': 0.1, 'max_iterations': 100, 'feature.possible_transitions': True}


def train(data_path, model_path):
    import pycrfsuite
    if model_path.exists():
        raise ValueError('Không ghi đè mô hình đã train; tạo thí nghiệm mới')
    start = time.perf_counter()
    rows = doc_jsonl(data_path)
    trainer = pycrfsuite.Trainer(algorithm='lbfgs', verbose=False)
    trainer.set_params(PARAMS)
    for row in rows:
        trainer.append(dac_trung(row['tokens']), row['tags'])
    prepare_s = time.perf_counter()-start
    print(f'Train {model_path.name}: {len(rows)} mẫu, {sum(len(r["tokens"]) for r in rows)} token; feature={prepare_s:.2f}s', flush=True)
    before = time.perf_counter()
    trainer.train(str(model_path))
    training_s = time.perf_counter()-before
    tagger = pycrfsuite.Tagger()
    tagger.open(str(model_path))
    info = tagger.info()
    report = {'rows': len(rows), 'tokens': sum(len(r['tokens']) for r in rows),
              'labels': dict(Counter(t for r in rows for t in r['tags'])),
              'feature_preparation_s': prepare_s, 'fit_s': training_s,
              'total_s': time.perf_counter()-start, 'params': PARAMS,
              'model_bytes': model_path.stat().st_size,
              'model_sha256': hashlib.sha256(model_path.read_bytes()).hexdigest(),
              'dataset_sha256': hashlib.sha256(data_path.read_bytes()).hexdigest(),
              'attributes': len(info.attributes), 'state_features': len(info.state_features),
              'transitions': len(info.transitions), 'memory_after_training': memory(),
              'library': 'python-crfsuite '+importlib.metadata.version('python-crfsuite'),
              'python': platform.python_version(), 'cpu_logical_count': os.cpu_count(),
              'device': 'CPU', 'dev_used_for_fitting_or_model_selection': False}
    model_path.with_suffix('.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8', newline='\n')
    print(json.dumps({'model': str(model_path), 'fit_s': training_s, 'size_bytes': report['model_bytes']}, ensure_ascii=False), flush=True)
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--experiment', type=Path, required=True)
    p.add_argument('--reuse-prepared', action='store_true', help='Tiếp tục từ dữ liệu đã chuẩn bị, không tái sinh hoặc ghi đè')
    a = p.parse_args()
    if a.reuse_prepared:
        manifest = json.loads((a.experiment/'snapshot_manifest.json').read_text(encoding='utf-8'))
        for name, item in manifest.items():
            if hashlib.sha256((a.experiment/'du_lieu_dong_bang'/name).read_bytes()).hexdigest() != item['sha256']:
                raise ValueError('Snapshot đã đổi: '+name)
        summary = json.loads((a.experiment/'du_lieu_crf/summary.json').read_text(encoding='utf-8'))
    else:
        summary = prepare(a.experiment/'du_lieu_dong_bang', a.experiment/'du_lieu_crf')
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
    result = {}
    for name in ('train_goc', 'train_ket_hop'):
        result[name] = train(a.experiment/'du_lieu_crf'/(name+'.jsonl'), a.experiment/(name+'.crfsuite'))
    (a.experiment/'training_summary.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8', newline='\n')


if __name__ == '__main__':
    main()
