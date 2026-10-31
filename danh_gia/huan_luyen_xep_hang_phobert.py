"""Huấn luyện ranker LightGBM cho pipeline chuẩn hóa với bộ tách PhoBERT.

Chỉ dùng dữ liệu train_ranker.jsonl, không đọc dev_goc hay dev_kho.
"""

import argparse
import json
import os
import sys
import time
import unicodedata
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import lightgbm as lgb
import numpy as np

from src.chuan_hoa import BoChuanHoa
from src.chuyen_doi import sang_cay_moi
from src.danh_muc import DanhMuc
from src.phobert import BoTachPhoBERT
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


def train_ranker_phobert(data_file: Path, model_dir: Path, out_dir: Path, threads: int = 2):
    start = time.perf_counter()
    out_dir.mkdir(parents=True, exist_ok=True)
    dm = DanhMuc()
    extractor = BoTachPhoBERT(str(model_dir), threads=threads)
    normalizer = BoChuanHoa(danh_muc=dm, bo_tach=extractor)

    records = doc_jsonl(data_file)
    features, labels, groups, audit = [], [], [], []
    excluded = Counter()

    for idx, rec in enumerate(records):
        if not rec.get("canonical_usable"):
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

        if (idx + 1) % 200 == 0 or (idx + 1) == len(records):
            print(f"Processed {idx + 1}/{len(records)} records, accumulated {len(groups)} valid groups", flush=True)

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

    dataset = lgb.Dataset(np.asarray(features, dtype=np.float64), label=labels, group=groups, feature_name=FEATURES)
    model = lgb.train(params, dataset, num_boost_round=100)

    ranker_txt_path = out_dir / "ranker.txt"
    model.save_model(str(ranker_txt_path))

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
    save_json(out_dir / "ranker.json", ranker_meta)

    training_meta = {
        "device": "cpu",
        "extractor": "BoTachPhoBERT",
        "extractor_sha256": extractor.ma_bam,
        "catalogue_sha256": dm.ma_bam,
        "samples": len(records),
        "groups": len(groups),
        "hypotheses": len(labels),
        "params": params,
        "boost_rounds": 100,
        "fit_seconds": time.perf_counter() - start,
        "heldout_dev_used_for_fit": False,
    }
    save_json(out_dir / "training.json", training_meta)

    # Kiểm tra nạp ranker
    loaded = BoXepHang(str(ranker_txt_path), extractor.ma_bam, dm.ma_bam)
    print(f"Ranker verified successfully loaded! Model sha256: {loaded.ma_bam}")


def main():
    parser = argparse.ArgumentParser(description="Train ranker cho PhoBERT")
    parser.add_argument("--data-file", type=Path,
                        default=Path("mo_hinh/thu_nghiem/char_v2_01/data/train_ranker.jsonl"))
    parser.add_argument("--model-dir", type=Path,
                        default=Path(os.environ.get("PHOBERT_MODEL_DIR") or r"G:\My Drive\PhoBERT_Address_Colab_20261030_v2\runs\phobert_base_v2_20261030T060548404237Z\best_model"))
    parser.add_argument("--out-dir", type=Path,
                        default=Path("mo_hinh/thu_nghiem/phobert_v2_01"))
    parser.add_argument("--threads", type=int, default=2)
    args = parser.parse_args()

    train_ranker_phobert(args.data_file, args.model_dir, args.out_dir, args.threads)


if __name__ == "__main__":
    main()
