"""Huấn luyện ranker LightGBM LambdaRank cho BoTachPhoBERT; không đọc dev/test.

Dữ liệu: mo_hinh/thu_nghiem/char_v2_01/data/train_ranker.jsonl.
Ghi ra: mo_hinh/thu_nghiem/phobert_v2_01/ranker.txt, ranker.json, training.json.
"""

import argparse
from collections import Counter
import json
import os
from pathlib import Path
import time

from src.chuan_hoa import BoChuanHoa
from src.chuyen_doi import sang_cay_moi
from src.danh_muc import DanhMuc
from src.phobert import BoTachPhoBERT
from src.xep_hang import FEATURES, BoXepHang, dac_trung_gia_thuyet
from .chay_ban_thu import CORE, ROOT, norm
from .du_lieu_crf import doc_jsonl, ghi_jsonl

DEFAULT_DATA = ROOT / 'mo_hinh/thu_nghiem/char_v2_01/data/train_ranker.jsonl'
DEFAULT_OUT = ROOT / 'mo_hinh/thu_nghiem/phobert_v2_01'
DEFAULT_MODEL = os.environ.get(
    'PHOBERT_MODEL_DIR',
    r'G:\My Drive\PhoBERT_Address_Colab_20261030_v2\runs\phobert_base_v2_20261030T060548404237Z\best_model'
)


def save_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8', newline='\n')


def huan_luyen(data_path=DEFAULT_DATA, out_dir=DEFAULT_OUT, model_dir=DEFAULT_MODEL, threads=2):
    import lightgbm as lgb
    import numpy as np

    data_path = Path(data_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    start = time.perf_counter()
    dm = DanhMuc()
    extractor = BoTachPhoBERT(model_dir, threads=threads)
    normalizer = BoChuanHoa(danh_muc=dm, bo_tach=extractor)

    records = doc_jsonl(data_path)
    if not records:
        raise ValueError(f"Không có dữ liệu tại {data_path}")

    features, labels, groups, audit = [], [], [], []
    excluded = Counter()

    for idx, rec in enumerate(records):
        if not rec.get('canonical_usable', False):
            excluded['canonical_usable_false'] += 1
            continue
        ref = rec['ref']
        tokens, candidates, context, items = normalizer.tao_gia_thuyet(rec['text'])
        words = [t.chu for t in tokens]
        relevance, vectors = [], []
        for item in items:
            _, path, detail, *_ = item
            ward, prov, _ = sang_cay_moi(path, detail, dm)
            same_admin = ward == ref['ma_xa'] and prov == ref['ma_tinh']
            same_detail = all(norm(detail[f]) == norm(ref[f]) for f in CORE[:4])
            relevance.append(3 if same_admin and same_detail else 2 if same_admin else 0)
            vectors.append(dac_trung_gia_thuyet(item, words, candidates, dm, context))

        if not relevance or max(relevance) == 0 or len(set(relevance)) == 1:
            excluded['khong_co_cap_duong_am'] += 1
            continue

        features.extend(vectors)
        labels.extend(relevance)
        groups.append(len(vectors))
        audit.append({'id': rec['id'], 'group': rec.get('training_group', ''), 'relevance': relevance})

        if (idx + 1) % 200 == 0 or (idx + 1) == len(records):
            elapsed = time.perf_counter() - start
            print(f"Xử lý {idx + 1}/{len(records)} mẫu, nhóm: {len(groups)}, số giả thuyết: {len(labels)} ({elapsed:.1f}s)", flush=True)

    if not groups:
        raise ValueError("Không có nhóm đủ điều kiện train ranker")

    params = {
        'objective': 'lambdarank',
        'metric': 'ndcg',
        'num_leaves': 15,
        'max_depth': 4,
        'learning_rate': .05,
        'min_data_in_leaf': 20,
        'lambda_l2': 1.,
        'num_threads': threads,
        'seed': 20261029,
        'deterministic': True,
        'force_col_wise': True,
        'verbosity': -1,
        'label_gain': [0, 1, 3, 7]
    }

    dataset = lgb.Dataset(np.asarray(features), label=labels, group=groups, feature_name=FEATURES)
    model = lgb.train(params, dataset, num_boost_round=100)

    model_file = out_dir / 'ranker.txt'
    json_file = out_dir / 'ranker.json'
    training_file = out_dir / 'training.json'

    model.save_model(str(model_file))
    total_time = time.perf_counter() - start

    ranker_meta = {
        'features': FEATURES,
        'extractor_sha256': extractor.ma_bam,
        'catalogue_sha256': dm.ma_bam,
        'close_margin': .05,
        'margin_calibrated': False,
        'group_count': len(groups),
        'hypotheses': len(labels),
        'excluded': dict(excluded),
        'fit_seconds_including_features': total_time,
        'params': params,
        'boost_rounds': 100,
        'lightgbm_version': str(lgb.__version__),
        'heldout_dev_used_for_fit': False,
        'phobert_ranker_training_groups_disjoint': True,
        'feature_gain': dict(zip(FEATURES, model.feature_importance('gain').tolist()))
    }
    save_json(json_file, ranker_meta)

    training_meta = {
        'model_backend': 'BoTachPhoBERT',
        'extractor_sha256': extractor.ma_bam,
        'catalogue_sha256': dm.ma_bam,
        'features': FEATURES,
        'group_count': len(groups),
        'total_hypotheses': len(labels),
        'excluded': dict(excluded),
        'fit_seconds': total_time,
        'params': params,
        'boost_rounds': 100,
        'lightgbm_version': str(lgb.__version__),
        'heldout_dev_used_for_fit': False
    }
    save_json(training_file, training_meta)

    ghi_jsonl(out_dir / 'ranker_training_groups.jsonl', audit)

    # Kiểm tra nạp lại
    verifier = BoXepHang(model_file, extractor.ma_bam, dm.ma_bam)
    print(f"Hoàn thành ranker! SHA256 model: {verifier.ma_bam[:16]}... Ngưỡng gần: {verifier.nguong_gan}")
    return ranker_meta


def main():
    p = argparse.ArgumentParser(description="Huấn luyện ranker cho PhoBERT")
    p.add_argument('--data', type=Path, default=DEFAULT_DATA, help="Đường dẫn train_ranker.jsonl")
    p.add_argument('--out-dir', type=Path, default=DEFAULT_OUT, help="Thư mục xuất ranker")
    p.add_argument('--model-dir', type=Path, default=DEFAULT_MODEL, help="Thư mục PhoBERT")
    p.add_argument('--threads', type=int, default=2, help="Số luồng CPU")
    args = p.parse_args()
    huan_luyen(args.data, args.out_dir, args.model_dir, threads=args.threads)


if __name__ == '__main__':
    main()
