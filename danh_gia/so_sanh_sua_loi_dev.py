"""So sánh hai snapshot chẩn đoán dev đã có, không chạm test và không chạy model."""
import argparse
import json
from pathlib import Path

from danh_gia.chay_ban_thu import CORE, norm


def load(directory):
    p = Path(directory)
    summary = json.loads((p / "TONG_HOP.json").read_text(encoding="utf-8"))
    rows = {}
    with (p / "LOI_TUNG_CA.jsonl").open(encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            key = (r["split"], r["id"])
            if key in rows:
                raise ValueError("Mã dev trùng")
            rows[key] = r
    return summary, rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--before", type=Path, required=True)
    parser.add_argument("--after", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Không được ghi đè kết quả cũ")
    base_stats, base = load(args.before)
    next_stats, new = load(args.after)
    if base_stats["sha256"] != next_stats["sha256"]:
        raise ValueError("Dev/model/ranker/từ điển khác hash, không được đối chứng")
    if base_stats["limit"] != next_stats["limit"]:
        raise ValueError("Hai lượt có limit khác nhau")
    report = {"scope": "DEV only; cùng dữ liệu/model/ranker/từ điển",
              "snapshots": {"before": str(args.before), "after": str(args.after)},
              "sha256": base_stats["sha256"], "splits": {}}
    all_changes = []
    for split in base_stats["metrics"]:
        b = base_stats["metrics"][split]
        a = next_stats["metrics"][split]
        if b["so_mau"] != a["so_mau"]:
            raise ValueError("Hai tập khác số dòng")
        wrong_before = {key for key in base if key[0] == split}
        wrong_after = {key for key in new if key[0] == split}
        gained = sorted(wrong_before - wrong_after)
        lost = sorted(wrong_after - wrong_before)
        changed_wrong = []
        for key in sorted(wrong_before & wrong_after):
            before, after = base[key], new[key]
            if any(norm(before["prediction"][f]) != norm(after["prediction"][f]) for f in CORE):
                changed_wrong.append(key)
        result = {
            "rows": b["so_mau"], "before_exact_6": b["exact_6"],
            "after_exact_6": a["exact_6"], "net_change": a["exact_6"] - b["exact_6"],
            "gained": len(gained), "lost": len(lost),
            "changed_but_still_wrong": len(changed_wrong),
            "before_fields_wrong": b["errors_by_field_nonexclusive"],
            "after_fields_wrong": a["errors_by_field_nonexclusive"]
        }
        if result["net_change"] != result["gained"] - result["lost"]:
            raise ValueError("Net score không khớp gained/lost")
        report["splits"][split] = result
        for key in gained + lost + changed_wrong:
            before, after = base.get(key), new.get(key)
            all_changes.append({
                "split": split, "id": key[1],
                "status": "gained" if key in gained else "lost" if key in lost else "still_wrong_changed",
                "before": before["prediction"] if before else None,
                "after": after["prediction"] if after else None,
                "reference": (before or after)["reference"]
            })
        print(f"{split}: {b['exact_6']} -> {a['exact_6']}; "
              f"gained={len(gained)}, lost={len(lost)}; changed_wrong={len(changed_wrong)}", flush=True)
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "THONG_KE.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    with (args.output / "THAY_DOI.jsonl").open("w", encoding="utf-8", newline="\n") as f:
        for row in all_changes:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
