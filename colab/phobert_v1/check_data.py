"""Fail-closed train/dev integrity gate. NEVER reads the test split."""
import argparse
import hashlib
import json
import unicodedata
from collections import Counter
from pathlib import Path

TAGS = ["O"] + [p + r for r in ("so_nha", "ngo_ngach_hem", "thon_xom", "duong", "xa", "huyen", "tinh")
                for p in ("B-", "I-")]
DATA_FILES = ("train_cnn.jsonl", "dev_goc.jsonl", "dev_kho.jsonl")


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for part in iter(lambda: f.read(1024 * 1024), b""):
            h.update(part)
    return h.hexdigest()


def inspect(root, manifest):
    root = Path(root)
    meta = json.loads(Path(manifest).read_text(encoding="utf-8"))
    assert meta["tag_schema"] == TAGS, "BIO schema mismatch"
    assert set(meta["sha256"]) == set(DATA_FILES), "Exactly three train/dev files required"
    report, seen = {}, {}
    for filename in DATA_FILES:
        p = root / filename
        assert sha256(p) == meta["sha256"][filename], "HASH MISMATCH: " + filename
        count, labels, allowed_sizes = 0, Counter(), Counter()
        id_set, text_set, duplicate_texts = set(), set(), 0
        groups = set()
        with p.open(encoding="utf-8") as f:
            for line_no, line in enumerate(f, 1):
                row = json.loads(line)
                text = row["nfc"]
                assert unicodedata.normalize("NFC", row["text"]) == text == unicodedata.normalize("NFC", text), (filename, line_no, "NFC")
                assert text and len(text) <= 2048, (filename, line_no, "length")
                assert len(row["allowed"]) == len(text), (filename, line_no, "allowed_length")
                assert row["id"] not in id_set, (filename, line_no, "duplicate_id")
                id_set.add(row["id"])
                for allowed in row["allowed"]:
                    assert isinstance(allowed, list) and allowed, (filename, line_no, "empty_mask")
                    assert len(set(allowed)) == len(allowed), (filename, line_no, "duplicate_mask")
                    assert all(isinstance(tag, int) and 0 <= tag < len(TAGS) for tag in allowed), (filename, line_no, "invalid_tag")
                    allowed_sizes[len(allowed)] += 1
                    if len(allowed) == 1:
                        labels[TAGS[allowed[0]]] += 1
                ordered = sorted((a, b, role) for role, a, b in row["spans"])
                prev = 0
                for a, b, role in ordered:
                    assert role in ("so_nha", "ngo_ngach_hem", "thon_xom", "duong", "xa", "huyen", "tinh")
                    assert 0 <= prev <= a < b <= len(text), (filename, line_no, "overlapping_or_invalid_span")
                    prev = b
                canonical = unicodedata.normalize("NFC", " ".join(text.casefold().split()))
                # Duplicate text within a split is reported; we do not silently delete labels.
                duplicate_texts += int(canonical in text_set)
                text_set.add(canonical)
                group = row.get("training_group", row.get("ref", {}).get("nhom_mau_goc", row["id"]))
                groups.add(str(group))
                count += 1
        assert count > 0, "Empty split " + filename
        seen[filename] = (id_set, text_set, groups)
        report[filename] = {"rows": count, "duplicate_texts_within_split": duplicate_texts,
                            "strong_chars": sum(labels.values()),
                            "ambiguous_chars": sum(n * k for n, k in allowed_sizes.items() if n > 1),
                            "strong_tags": dict(labels)}
    for a, b in (("train_cnn.jsonl", "dev_goc.jsonl"), ("train_cnn.jsonl", "dev_kho.jsonl")):
        assert not seen[a][0] & seen[b][0], "TRAIN/DEV ID LEAKAGE"
        assert not seen[a][1] & seen[b][1], "TRAIN/DEV TEXT LEAKAGE"
        assert not seen[a][2] & seen[b][2], "TRAIN/DEV GROUP LEAKAGE"
    assert report["train_cnn.jsonl"]["rows"] > 1000, "Unexpectedly small training corpus"
    return report


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", type=Path, required=True)
    ap.add_argument("--manifest", type=Path, required=True)
    a = ap.parse_args()
    print(json.dumps(inspect(a.data_dir, a.manifest), ensure_ascii=False, indent=2))
    print("PREFLIGHT_DATA_PASS")
