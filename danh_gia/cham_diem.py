"""Chấm bằng nhãn da_duyet; không coi nhãn máy là đáp án được xác nhận."""

import argparse
import csv
import json
from pathlib import Path
import unicodedata

FIELDS = [
    "so_nha",
    "ngo_ngach_hem",
    "thon_xom",
    "duong",
    "ma_xa",
    "ma_tinh",
    "xa_phuong",
    "tinh",
]


def normalized(value):
    return " ".join(unicodedata.normalize("NFC", str(value or "")).casefold().split())


def indexed(rows):
    result = {}
    for row in rows:
        key = str(row.get("id", ""))
        if not key or key in result:
            raise ValueError("Mỗi dòng cần id riêng, không rỗng và không trùng.")
        result[key] = row
    return result


def score(gold, predictions):
    all_gold = indexed(gold)
    pred = indexed(predictions)
    reviewed = {
        k: r for k, r in all_gold.items() if r.get("trang_thai_nhan") == "da_duyet"
    }
    n = len(reviewed)
    result = {
        "status": "scored_reviewed_only" if n else "awaiting_manual_review",
        "gold_rows": len(all_gold),
        "reviewed_rows": n,
        "excluded_unreviewed_rows": len(all_gold) - n,
        "prediction_rows": len(pred),
        "extra_prediction_ids": len(pred.keys() - all_gold.keys()),
        "missing_reviewed_predictions": len(reviewed.keys() - pred.keys()),
        "field_accuracy": None,
        "nonempty_field_accuracy": None,
        "exact_match": None,
        "canonical_string_accuracy": None,
        "flag_rate": None,
        "old_address_conversion": None,
        "split_ward_handling": None,
    }
    if not n:
        return result

    def equal(k, field):
        return k in pred and normalized(pred[k].get(field)) == normalized(
            reviewed[k].get(field)
        )

    result["field_accuracy"] = {
        f: sum(equal(k, f) for k in reviewed) / n for f in FIELDS
    }
    result["nonempty_field_accuracy"] = {}
    for f in FIELDS:
        ids = [k for k, r in reviewed.items() if normalized(r.get(f))]
        result["nonempty_field_accuracy"][f] = {
            "count": len(ids),
            "accuracy": sum(equal(k, f) for k in ids) / len(ids) if ids else None,
        }
    result["exact_match"] = sum(all(equal(k, f) for f in FIELDS) for k in reviewed) / n
    result["canonical_string_accuracy"] = (
        sum(equal(k, "dia_chi_chuan") for k in reviewed) / n
    )

    def flags(value):
        if isinstance(value, list):
            return value
        try:
            return json.loads(value or "[]")
        except (ValueError, TypeError):
            return [value] if value else []

    result["flag_rate"] = (
        sum(bool(flags(pred.get(k, {}).get("canh_bao"))) for k in reviewed) / n
    )
    old = [k for k, r in reviewed.items() if r.get("ma_xa_cu")]
    split = [k for k, r in reviewed.items() if "xa_bi_chia" in flags(r.get("canh_bao"))]
    result["old_address_conversion"] = {
        "count": len(old),
        "accuracy": (
            sum(equal(k, "ma_xa") and equal(k, "ma_tinh") for k in old) / len(old)
            if old
            else None
        ),
    }
    result["split_ward_handling"] = {
        "count": len(split),
        "accuracy": (
            sum(
                k in pred
                and not pred[k].get("ma_xa")
                and "xa_bi_chia" in flags(pred[k].get("canh_bao"))
                for k in split
            )
            / len(split)
            if split
            else None
        ),
    }
    return result


def read(path):
    if path.suffix == ".json":
        return json.loads(path.read_text(encoding="utf-8-sig"))
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--gold", type=Path, default=Path("data/test/dia_chi_test.csv"))
    p.add_argument("--predictions", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    if a.output.resolve() in {a.gold.resolve(), a.predictions.resolve()}:
        p.error("Không ghi đè đáp án hoặc dự đoán.")
    result = score(read(a.gold), read(a.predictions))
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
