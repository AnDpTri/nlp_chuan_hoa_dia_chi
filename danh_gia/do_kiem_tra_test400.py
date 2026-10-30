"""Đo lường kiểm chứng độc lập trên tập test 400 địa chỉ thật (data/test/dia_chi_test.csv).

TUYỆT ĐỐI TUÂN THỦ NGUYÊN TẮC:
- Tập test CHỈ ĐƯỢC ĐỌC ĐỂ ĐÁNH GIÁ CUỐI CÙNG (Read-only held-out evaluation).
- KHÔNG dùng dữ liệu, nhãn, từ vựng hay thuộc tính tập test để train, tinh chỉnh tham số, hay bổ sung từ điển.
"""

import argparse
import csv
import json
import time
import unicodedata
from collections import Counter
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DETAIL = ("so_nha", "ngo_ngach_hem", "thon_xom", "duong")
CORE = (*DETAIL, "ma_xa", "ma_tinh")
FIELDS = (*DETAIL, "ma_xa", "ma_tinh", "xa_phuong", "tinh", "dia_chi_chuan")


def norm(s):
    if s is None:
        return ""
    return " ".join(unicodedata.normalize("NFC", str(s)).casefold().split())


def pct(a, b):
    return round(100.0 * a / b, 3) if b else 0.0


def field_metrics(pairs, field):
    correct = sum(norm(r[field]) == norm(p[field]) for r, p in pairs)
    ref_n = sum(bool(r[field]) for r, _ in pairs)
    pred_n = sum(bool(p[field]) for _, p in pairs)
    true_n = sum(bool(r[field]) and norm(r[field]) == norm(p[field]) for r, p in pairs)
    return {
        "dung": correct,
        "tong": len(pairs),
        "ty_le_khop_pct": pct(correct, len(pairs)),
        "nhan_khong_rong": ref_n,
        "du_doan_khong_rong": pred_n,
        "dung_khong_rong": true_n,
        "recall_pct": pct(true_n, ref_n),
        "precision_pct": pct(true_n, pred_n)
    }


def aggregate_metrics(pairs):
    all_ok = sum(all(norm(r[f]) == norm(p[f]) for f in CORE) for r, p in pairs)
    return {
        "so_mau": len(pairs),
        "dung_toan_bo_6_truong": all_ok,
        "khop_toan_bo_6_truong_pct": pct(all_ok, len(pairs)),
        "tung_truong": {f: field_metrics(pairs, f) for f in FIELDS}
    }


def danh_gia_test_set(bo_chuan_hoa, test_csv_path=None):
    csv_p = Path(test_csv_path or (ROOT / "data/test/dia_chi_test.csv"))
    if not csv_p.exists():
        raise FileNotFoundError(f"Không tìm thấy file test tại {csv_p}")

    with open(csv_p, "r", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    total = len(rows)
    print(f"Bắt đầu đánh giá trên {total} mẫu của tập test: {csv_p.name}...", flush=True)

    times = []
    pairs_all = []
    pairs_da_duyet = []
    pairs_can_duyet = []

    for i, row in enumerate(rows):
        inp = row.get("dau_vao", "").strip()
        t0 = time.perf_counter()
        res = bo_chuan_hoa.chuan_hoa(inp)
        latency_ms = (time.perf_counter() - t0) * 1000.0
        times.append(latency_ms)

        pred = asdict(res)
        pair = (row, pred)
        pairs_all.append(pair)

        trang_thai = row.get("trang_thai_nhan", "").strip()
        if trang_thai == "da_duyet_ai":
            pairs_da_duyet.append(pair)
        else:
            pairs_can_duyet.append(pair)

        is_correct = all(norm(row[f]) == norm(pred[f]) for f in CORE)

        if (i + 1) % 100 == 0 or (i + 1) == total:
            print(f"Đã xử lý {i + 1}/{total} mẫu ({pct(i + 1, total)}%)...", flush=True)

    times_sorted = sorted(times)
    mean_lat = sum(times) / len(times) if times else 0.0
    p50_lat = times_sorted[int(len(times) * 0.50)] if times else 0.0
    p95_lat = times_sorted[int(len(times) * 0.95)] if times else 0.0
    p99_lat = times_sorted[int(len(times) * 0.99)] if times else 0.0

    stats_all = aggregate_metrics(pairs_all)
    stats_da_duyet = aggregate_metrics(pairs_da_duyet) if pairs_da_duyet else None
    stats_can_duyet = aggregate_metrics(pairs_can_duyet) if pairs_can_duyet else None

    latency_info = {
        "mean_ms": round(mean_lat, 2),
        "p50_ms": round(p50_lat, 2),
        "p95_ms": round(p95_lat, 2),
        "p99_ms": round(p99_lat, 2),
        "throughput_qps": round(1000.0 / mean_lat, 1) if mean_lat > 0 else 0.0
    }

    return {
        "tong_so_mau": total,
        "latency": latency_info,
        "toan_bo_400_mau": stats_all,
        "tap_da_duyet_ai_292_mau": stats_da_duyet,
        "tap_can_duyet_108_mau": stats_can_duyet,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Đánh giá pipeline trên tập test 400 mẫu")
    parser.add_argument("--char-model", type=Path, default=ROOT / "mo_hinh/thu_nghiem/char_v1_01/char_cnn.pt")
    parser.add_argument("--videberta-model", type=Path, default=None)
    parser.add_argument("--ranker", type=Path, default=ROOT / "mo_hinh/thu_nghiem/char_v1_01/ranker.txt")
    parser.add_argument("--tu-dien-duong", type=Path, default=ROOT / "danh_gia/ket_qua/sua_pipeline_cnn_v1_01/tu_dien_duong_train.json")
    # Hợp đồng nhãn chuẩn yêu cầu Số/Đường; có --no-tien-to-mac-dinh để tái hiện cấu hình cũ.
    parser.add_argument("--tien-to-mac-dinh", action=argparse.BooleanOptionalAction, default=True,
                        help="Tự thêm tiền tố Số/Đường khi chưa xuất hiện (mặc định bật)")
    parser.add_argument("--tien-to-so-nha", type=str, default=None, help="Bật/tắt tiền tố Số: true hoặc false")
    parser.add_argument("--tien-to-duong", type=str, default=None, help="Bật/tắt tiền tố Đường: true hoặc false")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    def parse_opt_bool(val):
        if val is None:
            return None
        return val.lower() in ("1", "true", "yes", "t")

    opt_so_nha = parse_opt_bool(args.tien_to_so_nha)
    opt_duong = parse_opt_bool(args.tien_to_duong)

    from src.danh_muc import DanhMuc
    from src.char_cnn import BoTachCharCNN
    from src.xep_hang import BoXepHang
    from src.chuan_ten_duong import TuDienDuong
    from src.chuan_hoa import BoChuanHoa

    dm = DanhMuc()
    if args.videberta_model and args.videberta_model.exists():
        from src.videberta import BoTachViDeberta
        bo_tach = BoTachViDeberta(args.videberta_model, threads=4)
    elif args.char_model and args.char_model.exists():
        bo_tach = BoTachCharCNN(args.char_model)
    else:
        bo_tach = None
    bo_xep_hang = BoXepHang(args.ranker, bo_tach.ma_bam, dm.ma_bam) if args.ranker and args.ranker.exists() and bo_tach else None
    tu_dien_duong = TuDienDuong(args.tu_dien_duong) if args.tu_dien_duong and args.tu_dien_duong.exists() else None

    pipeline = BoChuanHoa(
        danh_muc=dm,
        bo_tach=bo_tach,
        bo_xep_hang=bo_xep_hang,
        tu_dien_duong=tu_dien_duong,
        bao_ve_duong=True,
        tien_to_mac_dinh=args.tien_to_mac_dinh,
        tien_to_so_nha=opt_so_nha,
        tien_to_duong=opt_duong
    )

    ket_qua = danh_gia_test_set(pipeline)
    print("\n" + "=" * 60)
    print("KẾT QUẢ ĐÁNH GIÁ TẬP TEST (dia_chi_test.csv):")
    print(f"1. Toàn bộ {ket_qua['tong_so_mau']} mẫu:")
    print(f"   - Đúng toàn bộ 6 trường: {ket_qua['toan_bo_400_mau']['dung_toan_bo_6_truong']}/{ket_qua['tong_so_mau']} ({ket_qua['toan_bo_400_mau']['khop_toan_bo_6_truong_pct']}%)")
    if ket_qua["tap_da_duyet_ai_292_mau"]:
        nhom = ket_qua["tap_da_duyet_ai_292_mau"]
        print(f"2. Tập đã duyệt AI ({nhom['so_mau']} mẫu):")
        print(f"   - Đúng toàn bộ 6 trường: {nhom['dung_toan_bo_6_truong']}/{nhom['so_mau']} ({nhom['khop_toan_bo_6_truong_pct']}%)")
    print(f"3. Độ trễ CPU:")
    print(f"   - Mean latency: {ket_qua['latency']['mean_ms']} ms | P95: {ket_qua['latency']['p95_ms']} ms | QPS: {ket_qua['latency']['throughput_qps']}")
    print("=" * 60)

    if args.output:
        out_p = Path(args.output)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        # 'x' từ chối ghi đè báo cáo của lần đo trước.
        with out_p.open("x", encoding="utf-8", newline="\n") as f:
            json.dump(ket_qua, f, ensure_ascii=False, indent=2)
        print(f"Đã lưu kết quả chi tiết vào: {out_p}")
