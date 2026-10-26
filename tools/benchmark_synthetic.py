"""Kiểm tra phát triển sinh từ danh mục; không đọc data/test hay nhãn held-out."""

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import importlib.metadata
import json
from pathlib import Path
import random
import statistics
import time
from unittest.mock import patch

from src.danh_muc import DanhMuc
from src.tien_xu_ly import bo_dau
from danh_gia.chay_moc import adapters


def cases(d, n=80):
    rng = random.Random(42)
    new = sorted(
        [u for u in d.don_vi.values() if u.cay == "moi" and u.cap == "xa"],
        key=lambda u: u.ma,
    )
    old = sorted(
        [
            u
            for u in d.don_vi.values()
            if u.cay == "cu" and u.cap == "xa" and d.doi_chieu.get(u.ma)
        ],
        key=lambda u: u.ma,
    )
    rows = []
    for u in rng.sample(new, n) + rng.sample(old, n // 2):
        chain = d.to_tien(u)
        names = [d.ten_day_du(v.cay, v.ma) for v in chain]
        if u.cay == "moi":
            ward, province, split = u.ma, u.ma_cha, False
        else:
            targets = sorted({m for m, _ in d.doi_chieu[u.ma]})
            split = len(targets) > 1
            ward = "" if split else targets[0]
            province = d.tinh_cu_moi[chain[-1].ma]
        canonical = ", ".join(names)
        # Sai một ký tự ở token tên dài nhất của xã; giữ nguyên tiền tố loại đơn vị.
        words = names[0].split()
        ix = max(range(1, len(words)), key=lambda i: len(words[i]))
        changed = words.copy()
        changed[ix] = changed[ix][:-1] if len(changed[ix]) > 3 else changed[ix] + "x"
        typo = ", ".join([" ".join(changed)] + names[1:])
        variants = {
            "canonical": canonical,
            "accentless": bo_dau(canonical),
            "reordered": ", ".join(reversed(names)),
            "one_typo": typo,
        }
        for kind, text in variants.items():
            rows.append(
                dict(
                    id=f"{u.cay}-{u.ma}-{kind}",
                    dau_vao=text,
                    ma_xa=ward,
                    ma_tinh=province,
                    source_tree=u.cay,
                    variant=kind,
                    split=split,
                )
            )
    return rows


def run(rows, methods):
    summaries = {}
    predictions = {}
    for name, predict in methods.items():
        predict("Phường Cầu Giấy, Hà Nội")  # warmup, không tính vào latency
        latencies = []
        groups = defaultdict(Counter)
        out = []
        for row in rows:
            start = time.perf_counter()
            try:
                result = predict(row["dau_vao"])
                error = None
            except Exception as e:
                result = {}
                error = type(e).__name__
            latencies.append((time.perf_counter() - start) * 1000)
            match = all(result.get(k, "") == row[k] for k in ["ma_xa", "ma_tinh"])
            key = row["source_tree"] + "/" + row["variant"]
            groups[key]["n"] += 1
            groups[key]["correct"] += match
            out.append(dict(id=row["id"], **result, execution_error=error))
        summaries[name] = {
            "n": len(rows),
            "admin_pair_accuracy_synthetic": sum(g["correct"] for g in groups.values())
            / len(rows),
            "p50_ms": statistics.median(latencies),
            "p95_ms": sorted(latencies)[int(0.95 * (len(latencies) - 1))],
            "execution_errors": sum(r["execution_error"] is not None for r in out),
            "groups": {
                k: dict(v, accuracy=v["correct"] / v["n"]) for k, v in groups.items()
            },
        }
        predictions[name] = out
        print(
            name,
            json.dumps({k: v for k, v in summaries[name].items() if k != "groups"}),
            flush=True,
        )
    return summaries, predictions


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, default=Path("results/development"))
    p.add_argument("--sample", type=int, default=80)
    a = p.parse_args()
    d = a.output.resolve()
    if Path("data").resolve() in [d, *d.parents]:
        p.error("Lưu kết quả bên ngoài dữ liệu gốc.")
    d.mkdir(parents=True, exist_ok=True)
    rows = cases(DanhMuc(), a.sample)
    (d / "synthetic_cases.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    start = time.perf_counter()
    methods = adapters()
    startup = time.perf_counter() - start
    with patch(
        "socket.socket.connect", side_effect=RuntimeError("Benchmark chạy offline")
    ):
        summaries, predictions = run(rows, methods)
    report = {
        "dataset": "synthetic_from_catalogue_only",
        "seed": 42,
        "rows": len(rows),
        "claim_limit": "Không phải độ chính xác trên 400 địa chỉ thực; không thay thế duyệt nhãn thủ công.",
        "network_blocked": True,
        "startup_seconds_all_adapters": startup,
        "versions": {
            v: importlib.metadata.version(v)
            for v in ["vietnamadminunits", "vietnam-address-converter"]
        },
        "clean_sha256": {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in Path("data/clean").glob("*.csv")
        },
        "methods": summaries,
    }
    (d / "metrics.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    pred = Path("results/predictions")
    pred.mkdir(parents=True, exist_ok=True)
    for name, output in predictions.items():
        (pred / (name + ".json")).write_text(
            json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8"
        )


if __name__ == "__main__":
    main()
