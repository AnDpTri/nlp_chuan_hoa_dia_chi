"""Đối chứng hợp đồng tiền tố trên DEV, không đọc test cuối.

Chỉ dùng hai dev được ghim trong repo. Không sửa nhãn, model, từ điển.
Output phải là thư mục mới; không ghi đè số đo trước.
"""
import argparse
import csv
import hashlib
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from src.char_cnn import BoTachCharCNN
from src.chuan_hoa import BoChuanHoa
from src.chuan_ten_duong import TuDienDuong
from src.danh_muc import DanhMuc
from src.xep_hang import BoXepHang
from danh_gia.chay_ban_thu import CORE, aggregate, norm

ROOT = Path(__file__).resolve().parents[1]
SPLITS = {
    "dev_goc": ROOT / "data/train_dev/dev.csv",
    "dev_kho": ROOT / "mo_hinh/thu_nghiem/char_v1_01/snapshot/dev_kho.csv",
}
MODEL = ROOT / "mo_hinh/thu_nghiem/char_v2_01/char_cnn.pt"
RANKER = ROOT / "mo_hinh/thu_nghiem/char_v2_01/ranker.txt"
NAMES = ROOT / "danh_gia/ket_qua/tu_dien_duong_v5.json"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description="Ablation tiền tố chỉ trên DEV")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=0, help="0 = toàn bộ dev, >0 = smoke test")
    args = parser.parse_args()
    if args.limit < 0:
        parser.error("--limit phải >= 0")
    output = args.output_dir.resolve()
    if output.exists():
        parser.error("Thư mục output đã tồn tại; không được ghi đè kết quả cũ")

    dm = DanhMuc()
    extractor = BoTachCharCNN(MODEL, threads=1)
    ranker = BoXepHang(RANKER, extractor.ma_bam, dm.ma_bam)
    names = TuDienDuong(NAMES)
    configs = {
        "tien_to_tat": BoChuanHoa(danh_muc=dm, bo_tach=extractor,
                                bo_xep_hang=ranker, tu_dien_duong=names,
                                bao_ve_duong=True, tien_to_mac_dinh=False),
        "tien_to_bat": BoChuanHoa(danh_muc=dm, bo_tach=extractor,
                                bo_xep_hang=ranker, tu_dien_duong=names,
                                bao_ve_duong=True, tien_to_mac_dinh=True),
    }
    report = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "DEV only; không đọc data/test; không thay nhãn hoặc mô hình",
        "limited": args.limit > 0,
        "limit_per_split": args.limit,
        "sha256": {str(p.relative_to(ROOT)): digest(p) for p in (*SPLITS.values(), MODEL, RANKER, NAMES)},
        "datasets": {}
    }
    cases = []
    for split, csv_path in SPLITS.items():
        with csv_path.open(encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
        if args.limit:
            rows = rows[:args.limit]
        preds = {}
        for mode, pipeline in configs.items():
            predictions = [asdict(pipeline.chuan_hoa(row["dau_vao"])) for row in rows]
            preds[mode] = predictions
        reports = {}
        for mode in configs:
            reports[mode] = aggregate(list(zip(rows, preds[mode])))
        gain = loss = changed = 0
        by_field = {f: 0 for f in CORE}
        for row, baseline, candidate in zip(rows, preds["tien_to_tat"], preds["tien_to_bat"]):
            base_ok = all(norm(row[f]) == norm(baseline[f]) for f in CORE)
            cand_ok = all(norm(row[f]) == norm(candidate[f]) for f in CORE)
            gain += int(not base_ok and cand_ok)
            loss += int(base_ok and not cand_ok)
            diffs = {f: {"tat": baseline[f], "bat": candidate[f]}
                     for f in CORE if norm(baseline[f]) != norm(candidate[f])}
            if diffs:
                changed += 1
                for f in diffs:
                    by_field[f] += 1
                cases.append({"split": split, "id": row["id"], "input": row["dau_vao"],
                              "fields_changed": diffs, "was_correct": base_ok,
                              "is_correct": cand_ok})
        report["datasets"][split] = {"rows": len(rows), "modes": reports,
                                      "changed": changed, "gained": gain, "lost": loss,
                                      "fields_changed_count": by_field}
        print(f"{split}: prefix_off={reports['tien_to_tat']['dung_toan_bo_6_truong']}/{len(rows)}; "
              f"prefix_on={reports['tien_to_bat']['dung_toan_bo_6_truong']}/{len(rows)}; "
              f"gained={gain}, lost={loss}", flush=True)
    output.mkdir(parents=True, exist_ok=False)
    (output / "BAO_CAO.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n"
    )
    with (output / "THAY_DOI_DEV.jsonl").open("w", encoding="utf-8", newline="\n") as f:
        for item in cases:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    print(f"Results: {output}", flush=True)


if __name__ == "__main__":
    main()
