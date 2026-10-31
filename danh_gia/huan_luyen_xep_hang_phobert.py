"""Huấn luyện lại LightGBM LambdaRank cho PhoBERT trên dữ liệu train_ranker tách biệt.

python -m danh_gia.huan_luyen_xep_hang_phobert
"""

import argparse
from collections import Counter
import json
import os
from pathlib import Path
import time
import unicodedata

import lightgbm as lgb
import numpy as np

from src.chuan_hoa import BoChuanHoa
from src.chuyen_doi import sang_cay_moi
from src.danh_muc import DanhMuc
from src.phobert import BoTachPhoBERT, DEFAULT_MODEL_DIR, MODEL_DIR_ENV
from src.xep_hang import FEATURES, BoXepHang, dac_trung_gia_thuyet

DETAIL = ("so_nha", "ngo_ngach_hem", "thon_xom", "duong")
CORE = (*DETAIL, "ma_xa", "ma_tinh")


def norm(s):
    return " ".join(unicodedata.normalize("NFC", s).casefold().split())


def doc_jsonl(path):
    with Path(path).open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def save_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")


def train_ranker_phobert(model_dir, data_path, out_dir, threads=4):
    start = time.perf_counter()
    dm = DanhMuc()
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    extractor = BoTachPhoBERT(model_dir, threads=threads)
    normalizer = BoChuanHoa(danh_muc=dm, bo_tach=extractor)
    records = doc_jsonl(data_path)

    features, labels, groups, audit = [], [], [], []
    excluded = Counter()

    print(f"Bắt đầu trích xuất đặc trưng cho {len(records)} bản ghi...", flush=True)
    t_feat0 = time.perf_counter()

    for idx, rec in enumerate(records, 1):
        if not rec.get("canonical_usable", True):
            excluded["canonical_usable_false"] += 1
            continue
        ref = rec["ref"]
        tokens, candidates, context, items = normalizer.tao_gia_thuyet(rec["text"])
        words = [t.chu for t in tokens]
        relevance, vectors = [], []
        for item in items:
            _, path, detail, *_ = item
            ward, prov, _ = sang_cay_moi(path, detail, dm)
            same_admin = ward == ref["ma_xa"] and prov == ref["ma_tinh"]
            same_detail = all(norm(detail[f]) == norm(ref[f]) for f in CORE[:4])
            relevance.append(3 if same_admin and same_detail else 2 if same_admin else 0)
            vectors.append(dac_trung_gia_thuyet(item, words, candidates, dm, context))

        if not relevance or max(relevance) == 0 or len(set(relevance)) == 1:
            excluded["khong_co_cap_duong_am"] += 1
            continue

        features.extend(vectors)
        labels.extend(relevance)
        groups.append(len(vectors))
        audit.append({"id": rec["id"], "group": rec.get("training_group"), "relevance": relevance})

        if idx % 200 == 0 or idx == len(records):
            elapsed = time.perf_counter() - t_feat0
            print(f"Tiến độ: {idx}/{len(records)} ({elapsed:.1f}s, groups={len(groups)}, items={len(labels)})", flush=True)

    if not groups:
        raise ValueError("Không có nhóm đủ điều kiện train ranker")

    params = {
        "objective": "lambdarank",
        "metric": "ndcg",
        "num_leaves": 15,
        "max_depth": 4,
        "learning_rate": 0.05,
        "min_data_in_leaf": 20,
        "lambda_l2": 1.0,
        "num_threads": threads,
        "seed": 20261029,
        "deterministic": True,
        "force_col_wise": True,
        "verbosity": -1,
        "label_gain": [0, 1, 3, 7],
    }

    print("Huấn luyện mô hình LightGBM LambdaRank...", flush=True)
    dataset = lgb.Dataset(np.asarray(features, dtype=np.float64), label=labels, group=groups, feature_name=FEATURES)
    model = lgb.train(params, dataset, num_boost_round=100)

    ranker_txt = out_dir / "ranker.txt"
    ranker_json = out_dir / "ranker.json"
    training_json = out_dir / "training.json"

    model.save_model(str(ranker_txt))

    ranker_meta = {
        "features": FEATURES,
        "extractor_sha256": extractor.ma_bam,
        "catalogue_sha256": dm.ma_bam,
        "close_margin": 0.05,
        "margin_calibrated": False,
        "group_count": len(groups),
        "hypotheses": len(labels),
        "excluded": dict(excluded),
        "fit_seconds_including_features": time.perf_counter() - start,
        "params": params,
        "boost_rounds": 100,
        "lightgbm_version": lgb.__version__,
        "heldout_dev_used_for_fit": False,
        "phobert_ranker_training_groups_disjoint": True,
        "feature_gain": dict(zip(FEATURES, model.feature_importance("gain").tolist())),
    }
    save_json(ranker_json, ranker_meta)

    save_json(training_json, {
        "model": "PhoBERT-base-v2 LightGBM LambdaRank",
        "extractor_sha256": extractor.ma_bam,
        "catalogue_sha256": dm.ma_bam,
        "records_total": len(records),
        "group_count": len(groups),
        "hypotheses_count": len(labels),
        "excluded": dict(excluded),
        "params": params,
        "boost_rounds": 100,
        "training_seconds": time.perf_counter() - start,
    })

    print(f"Đã lưu ranker tại {ranker_txt} và {ranker_json}", flush=True)

    # Kiểm tra nạp lại
    verifier = BoXepHang(ranker_txt, extractor.ma_bam, dm.ma_bam)
    print(f"Xác nhận nạp ranker thành công! Hash: {verifier.ma_bam}", flush=True)
    return ranker_meta


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model-dir", default=os.environ.get(MODEL_DIR_ENV, DEFAULT_MODEL_DIR))
    p.add_argument("--data", default="mo_hinh/thu_nghiem/char_v2_01/data/train_ranker.jsonl")
    p.add_argument("--out-dir", default="mo_hinh/thu_nghiem/phobert_v2_01")
    p.add_argument("--threads", type=int, default=4)
    args = p.parse_args()

    train_ranker_phobert(args.model_dir, args.data, args.out_dir, threads=args.threads)


if __name__ == "__main__":
    main()
