"""Chẩn đoán lỗi trên 2 dev cố định; tuyệt đối không đọc tập test.
Số đo exact 6 trường theo hợp đồng dev có tiền tố. Đánh dấu nghi vấn, không sửa nhãn.
"""
import argparse
import csv
import json
import unicodedata
from collections import Counter, defaultdict
from dataclasses import asdict
from pathlib import Path

from danh_gia.chay_ban_thu import CORE, aggregate, norm
from danh_gia.so_sanh_hop_dong_dev import SPLITS, MODEL, RANKER, NAMES, ROOT, digest
from src.tien_xu_ly.char_cnn import BoTachCharCNN
from src.chuan_hoa import BoChuanHoa
from src.tien_xu_ly.chuan_ten_duong import TuDienDuong
from src.danh_muc import DanhMuc
from src.tien_xu_ly.xep_hang import BoXepHang
from src.tien_xu_ly import bo_dau

DETAIL = ("so_nha", "ngo_ngach_hem", "thon_xom", "duong")


def stripped(s):
    return "".join(bo_dau(w) for w in str(s).split())


def problem(ref, pred, field):
    expected, got = norm(ref[field]), norm(pred[field])
    if expected == got:
        return None
    if not expected:
        return "nhan_rong_du_doan_co"
    if not got:
        return "bo_sot_truong"
    if stripped(expected) == stripped(got):
        return "chi_khac_dau_khoang_trang"
    for prefix in ("số ", "đường ", "phố ", "ngõ ", "hẻm ", "thôn ", "xóm ", "ấp ", "khu phố "):
        if expected.removeprefix(prefix) == got.removeprefix(prefix) and expected != got:
            return "chi_khac_tien_to"
    for other in DETAIL:
        if other != field and norm(pred.get(other, "")) == expected:
            return "nham_vai_tro"
    if stripped(expected) in stripped(got) or stripped(got) in stripped(expected):
        return "thua_thieu_mot_phan"
    return "khac_noi_dung"


def primary(errors):
    for field in ("so_nha", "duong", "thon_xom", "ngo_ngach_hem", "ma_xa", "ma_tinh"):
        if field in errors:
            return field
    return "khong_ro"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--split", choices=["dev_goc", "dev_kho", "all"], default="all")
    args = parser.parse_args()
    if args.limit < 0:
        parser.error("--limit phải >= 0")
    out = args.output_dir.resolve()
    if out.exists():
        parser.error("Không ghi đè báo cáo đã có")
    if out.is_relative_to(ROOT / "data" / "test"):
        parser.error("Cấm ghi vào tập test")
    dm = DanhMuc()
    model = BoTachCharCNN(MODEL, threads=1)
    ranker = BoXepHang(RANKER, model.ma_bam, dm.ma_bam)
    names = TuDienDuong(NAMES)
    pipeline = BoChuanHoa(danh_muc=dm, bo_tach=model, bo_xep_hang=ranker,
                          tu_dien_duong=names, bao_ve_duong=True, tien_to_mac_dinh=True)
    selected = SPLITS.items() if args.split == "all" else [(args.split, SPLITS[args.split])]
    report = {
        "scope": "dev-only, nhan may/tong hop, khong doc test, khong sua nhan",
        "sha256": {str(p.relative_to(ROOT)): digest(p) for p in (*SPLITS.values(), MODEL, RANKER, NAMES)},
        "metrics": {}, "limit": args.limit
    }
    errors_jsonl = []
    for split, path in selected:
        with path.open(encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
        if args.limit:
            rows = rows[:args.limit]
        preds = []
        category_counts = Counter()
        fields_wrong = Counter()
        primary_counts = Counter()
        suspicious = Counter()
        cooccurrences = Counter()
        for i, row in enumerate(rows, 1):
            pred = asdict(pipeline.chuan_hoa(row["dau_vao"]))
            preds.append(pred)
            errors = {f: problem(row, pred, f) for f in CORE}
            errors = {f: category for f, category in errors.items() if category}
            if errors:
                primary_counts[primary(errors)] += 1
                for f, reason in errors.items():
                    fields_wrong[f] += 1
                    category_counts[f + "/" + reason] += 1
                cooccurrences["+".join(sorted(errors))] += 1
                # Heuristic chỉ đánh dấu nhãn đáng rà, không dùng để sửa dữ liệu.
                if row.get("duong") and len(stripped(row["duong"])) >= 5 and stripped(row["duong"]).removeprefix("duong").removeprefix("pho") not in stripped(row["dau_vao"]):
                    suspicious["duong_khong_can_chinh_nguyen_van"] += 1
                errors_jsonl.append({
                    "split": split, "id": row["id"], "input": row["dau_vao"],
                    "reference": {f: row[f] for f in CORE},
                    "prediction": {f: pred[f] for f in CORE},
                    "errors": errors, "primary": primary(errors),
                    "warnings": pred["canh_bao"]
                })
            if i % 250 == 0:
                print(f"{split}: {i}/{len(rows)}", flush=True)
        metr = aggregate(list(zip(rows, preds)))
        report["metrics"][split] = {
            "so_mau": len(rows), "exact_6": metr["dung_toan_bo_6_truong"],
            "exact_pct": metr["khop_toan_bo_6_truong_pct"],
            "field": {f: metr["tung_truong"][f] for f in CORE},
            "errors_by_field_nonexclusive": dict(fields_wrong),
            "errors_by_reason_nonexclusive": dict(category_counts.most_common()),
            "primary_wrong_field_exclusive": dict(primary_counts),
            "field_combinations": dict(cooccurrences.most_common(25)),
            "label_suspicions_not_proof": dict(suspicious)
        }
        print(f"{split}: {metr['dung_toan_bo_6_truong']}/{len(rows)}; errors_by_field={dict(fields_wrong)}", flush=True)
    out.mkdir(parents=True, exist_ok=False)
    (out / "TONG_HOP.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    with (out / "LOI_TUNG_CA.jsonl").open("w", encoding="utf-8", newline="\n") as f:
        for item in errors_jsonl:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    print(f"Saved {len(errors_jsonl)} incorrect dev predictions to {out}", flush=True)


if __name__ == "__main__":
    main()
