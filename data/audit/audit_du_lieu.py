"""Read-only dataset integrity audit. Aggregates only: never output addresses or OSM URLs."""
import argparse
import csv
import hashlib
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]


def normalize(value):
    s = unicodedata.normalize("NFD", (value or "").casefold().replace("đ", "d"))
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def masked_family(value):
    s = normalize(value)
    s = re.sub(r"^(?:so nha|nha so|so)\s+", "", s)
    s = re.sub(r"^\d+[a-z]?(?:\s+\d+[a-z]?){0,2}\s+", "", s)
    return s if len(s.split()) >= 3 else ""


def osm_identity(value):
    u = urlsplit(value or "")
    if u.hostname not in ("openstreetmap.org", "www.openstreetmap.org"):
        return ""
    m = re.search(r"/(node|way|relation)/(\d+)(?:/|$)", u.path)
    return f"{m.group(1)}:{m.group(2)}" if m else ""


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as src:
        for block in iter(lambda: src.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as src:
        return list(csv.DictReader(src))


def fingerprints(items):
    return {
        "text": {v for r in items if (v := normalize(r.get("dau_vao", "")))},
        "osm": {v for r in items if (v := osm_identity(r.get("nguon", "")))},
        "masked": {v for r in items if (v := masked_family(r.get("dau_vao", "")))},
    }


def compare(a, b):
    return {key: len(a[key] & b[key]) for key in ("text", "osm", "masked")}


def audit(root=ROOT):
    files = {
        "train": root / "data/train_dev/train.csv",
        "dev": root / "data/train_dev/dev.csv",
        "v2": root / "data/train_dev/bo_sung_v2/train_bo_sung_v2.csv",
        "test": root / "data/test/dia_chi_test.csv",
    }
    samples = {k: read_csv(path) for k, path in files.items()}
    fp = {k: fingerprints(v) for k, v in samples.items()}
    pairs = {
        a + "_" + b: compare(fp[a], fp[b])
        for a, b in (("train", "dev"), ("train", "test"), ("dev", "test"),
                     ("v2", "dev"), ("v2", "test"), ("v2", "train"))
    }
    errors, warnings = [], []
    for name, counts in pairs.items():
        if name != "v2_train" and (counts["text"] or counts["osm"]):
            errors.append(f"{name}: direct overlap across evaluation boundary")
        if counts["masked"]:
            warnings.append(f"{name}: possible shared family (heuristic only)")
    if pairs["v2_train"]["text"]:
        warnings.append("v2_train: repeated inputs; deduplicate before combining")
    for name, group in samples.items():
        ids = [row.get("id", "") for row in group]
        if len(ids) != len(set(ids)) or not all(ids):
            errors.append(f"{name}: duplicate or missing ID")

    test_validation = json.loads((root / "data/test/validation.json").read_text(encoding="utf-8"))
    test_stats = json.loads((root / "data/test/statistics.json").read_text(encoding="utf-8"))
    statuses = dict(Counter(r.get("trang_thai_nhan", "") for r in samples["test"]))
    test_hash_ok = sha256(files["test"]) == test_validation.get("csv_sha256")
    if not test_hash_ok:
        errors.append("test: checksum does not match validation.json")
    if statuses.get("da_duyet_ai", 0) != test_validation.get("ai_reviewed_rows"):
        warnings.append("test: validation.json AI count differs from CSV")
    if statuses.get("da_duyet_ai", 0) != test_stats.get("status_ai_review", {}).get("da_duyet_ai"):
        warnings.append("test: statistics.json AI count is stale")
    if statuses.get("can_duyet", 0) != test_stats.get("status_ai_review", {}).get("can_duyet"):
        warnings.append("test: statistics.json pending count is stale")
    gold_ready = bool(test_validation.get("is_ready_for_gold_evaluation", False))
    if not gold_ready:
        warnings.append("test: provisional only, not gold")

    manifest_path = root / "data/train_dev/bo_sung_v2/manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    hash_ok = {}
    for name, entry in manifest.get("files", {}).items():
        path = manifest_path.parent / name
        hash_ok[name] = path.is_file() and sha256(path) == entry.get("sha256")
        if not hash_ok[name]:
            errors.append("v2: hash mismatch: " + name)
    clean_validation = json.loads((root / "data/clean/validation.json").read_text(encoding="utf-8"))
    if clean_validation.get("status") != "PASS":
        errors.append("clean: structural validation not PASS")
    return {
        "version": "1.0",
        "source_rows": {k: len(v) for k, v in samples.items()},
        "overlaps": pairs,
        "v2_manifest_hash_ok": hash_ok,
        "test_status_from_csv": statuses,
        "test_human_reviewed": test_validation.get("human_reviewed_rows"),
        "test_gold_ready": gold_ready,
        "test_sha256_valid": test_hash_ok,
        "clean_structural_pass": clean_validation.get("status") == "PASS",
        "errors": errors,
        "warnings": warnings,
        "status": "FAIL" if errors else ("WARN" if warnings else "PASS"),
        "limitations": [
            "Masked-family overlap is a warning, not proof of leakage.",
            "Exact overlap checks cannot rule out semantic duplicates or test exposure.",
            "Structural validation cannot certify annotation correctness.",
            "Held-out test must not be used to tune models, rules or dictionaries.",
            "Audit output excludes raw addresses, OSM links and labels."
        ],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, help="Optional aggregate-only report path")
    args = parser.parse_args()
    result = json.dumps(audit(), ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(result + "\n", encoding="utf-8")
    print(result)


if __name__ == "__main__":
    main()
