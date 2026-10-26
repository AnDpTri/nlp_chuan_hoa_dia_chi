"""Tách từ điển tên đường OSM từ phần ngoài hold-out; không dùng nhãn test."""

from pathlib import Path
import argparse
from collections import defaultdict, Counter
import csv
import hashlib
import json
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.tien_xu_ly import bo_dau, chuan_hoa_chuoi

ROOT = Path(__file__).resolve().parents[1]


def key(text):
    return bo_dau(chuan_hoa_chuoi(text))


def build(candidates):
    heldout = ROOT / "data/test/goc/selected_sources.jsonl"
    reserved = [
        json.loads(line)
        for line in heldout.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    urls = {r.get("source_url", r.get("nguon", "")) for r in reserved}
    inputs = {key(r.get("dau_vao", "")) for r in reserved}
    names = defaultdict(Counter)
    used = 0
    excluded = 0
    with candidates.open(encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            if r.get("source_url") in urls or key(r.get("dau_vao", "")) in inputs:
                excluded += 1
                continue
            street = r.get("tags", {}).get("addr:street", "").strip()
            if not street or len(street) > 120:
                continue
            street = re.sub(r"^(?:đường|phố|duong|pho)\s+", "", street, flags=re.I)
            normalized = key(street)
            if not normalized or len(normalized) < 3:
                continue
            names[normalized][
                " ".join(w[:1].upper() + w[1:] for w in street.split())
            ] += 1
            used += 1
    out = ROOT / "data/runtime"
    out.mkdir(exist_ok=True)
    rows = []
    for k, variants in sorted(names.items()):
        accented = [name for name in variants if bo_dau(name) != name.lower()]
        choices = accented or list(variants)
        # Không dùng tần suất để tự chốt giữa hai tên có dấu khác nhau.
        if len(choices) == 1:
            rows.append(
                {
                    "khong_dau": k,
                    "ten_duong": choices[0],
                    "so_nguon": sum(variants.values()),
                }
            )
    with (out / "streets.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f, fieldnames=["khong_dau", "ten_duong", "so_nguon"], lineterminator="\n"
        )
        w.writeheader()
        w.writerows(rows)
    manifest = {
        "source": "Geofabrik Vietnam OSM snapshot 2026-10-24",
        "license": "ODbL-1.0",
        "candidates_sha256": hashlib.sha256(candidates.read_bytes()).hexdigest(),
        "reserved_sources": len(urls),
        "excluded_rows": excluded,
        "used_public_rows": used,
        "unambiguous_street_names": len(rows),
        "policy": "Chỉ tên đường từ tags addr:street ngoài URL/đầu vào hold-out. Không đọc nhãn đáp án.",
    }
    (out / "streets_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(manifest, ensure_ascii=True))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--candidates", type=Path, required=True)
    build(p.parse_args().candidates)
