"""Đo bản thử trên dev, không đọc tập test cuối và không huấn luyện mô hình.

py -3.12 -X utf8 -B -m danh_gia.chay_ban_thu --output-dir danh_gia/ket_qua/ban_thu_v1
"""

import argparse
import csv
import hashlib
import io
import json
import math
import platform
import re
import sys
import time
import unicodedata
from collections import Counter, defaultdict
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from src.chuan_hoa import BoChuanHoa
from src.tien_xu_ly import bo_dau, tach_token
from src.tien_xu_ly.tim_kiem import sinh_ung_vien
from src.tien_xu_ly.quy_tac import CHI_TIET, khop_tien_to

ROOT = Path(__file__).resolve().parents[1]
DETAIL = ("so_nha", "ngo_ngach_hem", "thon_xom", "duong")
FIELDS = (*DETAIL, "ma_xa", "ma_tinh", "xa_phuong", "tinh", "dia_chi_chuan")
CORE = (*DETAIL, "ma_xa", "ma_tinh")


def norm(s):
    return " ".join(unicodedata.normalize("NFC", s).casefold().split())


def pct(a, b):
    return round(100*a/b, 3) if b else None


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def memory():
    """Working set của cả tiến trình, không phải phép đo riêng kích thước trie."""
    if sys.platform != "win32":
        return {"phuong_phap": "khong_ho_tro", "working_set_mib": None, "peak_working_set_mib": None}
    import ctypes
    from ctypes import wintypes
    class PMC(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD)] + [(x, ctypes.c_size_t) for x in (
            "PeakWorkingSetSize", "WorkingSetSize", "QuotaPeakPagedPoolUsage", "QuotaPagedPoolUsage",
            "QuotaPeakNonPagedPoolUsage", "QuotaNonPagedPoolUsage", "PagefileUsage", "PeakPagefileUsage", "PrivateUsage")]
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(PMC), wintypes.DWORD]
    psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
    p = PMC()
    p.cb = ctypes.sizeof(p)
    if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(p), p.cb):
        raise ctypes.WinError(ctypes.get_last_error())
    return {"phuong_phap": "Windows GetProcessMemoryInfo", "working_set_mib": round(p.WorkingSetSize/2**20, 3),
            "peak_working_set_mib": round(p.PeakWorkingSetSize/2**20, 3), "private_mib": round(p.PrivateUsage/2**20, 3)}


def field_metrics(pairs, field):
    correct = sum(norm(r[field]) == norm(p[field]) for r, p in pairs)
    ref_n = sum(bool(r[field]) for r, _ in pairs)
    pred_n = sum(bool(p[field]) for _, p in pairs)
    true_n = sum(bool(r[field]) and norm(r[field]) == norm(p[field]) for r, p in pairs)
    return {"dung": correct, "tong": len(pairs), "ty_le_khop_pct": pct(correct, len(pairs)),
            "nhan_khong_rong": ref_n, "du_doan_khong_rong": pred_n, "dung_khong_rong": true_n,
            "recall_nhan_khong_rong_pct": pct(true_n, ref_n), "precision_du_doan_khong_rong_pct": pct(true_n, pred_n)}


def aggregate(pairs):
    all_ok = sum(all(norm(r[f]) == norm(p[f]) for f in CORE) for r, p in pairs)
    return {"so_mau": len(pairs), "dung_toan_bo_6_truong": all_ok,
            "khop_toan_bo_6_truong_pct": pct(all_ok, len(pairs)), "tung_truong": {f: field_metrics(pairs, f) for f in FIELDS}}


def align_detail(text, field, value):
    """Chỉ kiểm tra căn chỉnh nội dung, chưa tạo BIO hay xác nhận nhãn đúng."""
    if not value:
        return []
    src = tach_token(text)
    target = tach_token(value)
    marker = khop_tien_to(target, 0, CHI_TIET)
    if marker and marker[1][0] == field:
        target = target[marker[0]:]
    # Cho phép khác dấu/chữ hoa, tiền tố chuẩn hóa, nhưng không ghép qua dấu câu.
    wanted = [bo_dau(t) for t in target if t not in {".", ","}]
    if not wanted:
        return []
    out = []
    for i in range(len(src)):
        if [bo_dau(t) for t in src[i:i+len(wanted)]] == wanted:
            out.append([i, i+len(wanted)])
    return out


def write_csv(path, fields, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def run(input_path, output_dir, beam=40):
    input_path = Path(input_path).resolve()
    output_dir = Path(output_dir).resolve()
    if input_path.is_relative_to(ROOT / "data" / "test"):
        raise ValueError("Bản thử này chỉ dùng train/dev hoặc dữ liệu độc lập, không dùng tập test cuối")
    raw = input_path.read_bytes()
    rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))
    if not rows:
        raise ValueError("Không có mẫu để đo")
    if any(f not in rows[0] for f in (*FIELDS, "id", "dau_vao", "loai_nhan")):
        raise ValueError("CSV thiếu trường của schema train/dev")
    output_dir.mkdir(parents=True, exist_ok=False)
    before = memory()
    start = time.perf_counter()
    model = BoChuanHoa(beam=beam)
    init_s = time.perf_counter()-start
    after_init = memory()
    pairs, times = [], []
    with (output_dir / "du_doan.jsonl").open("w", encoding="utf-8") as f:
        for idx, row in enumerate(rows, 1):
            start = time.perf_counter()
            result = model.chuan_hoa(row["dau_vao"])
            ms = (time.perf_counter()-start)*1000
            prediction = asdict(result)
            times.append(ms)
            pairs.append((row, prediction))
            f.write(json.dumps({"id": row["id"], "dau_vao": row["dau_vao"], "thoi_gian_ms": ms, **prediction}, ensure_ascii=False)+"\n")
            if idx % 200 == 0:
                print(f"Đã đo {idx}/{len(rows)}", flush=True)
    after_run = memory()

    groups = defaultdict(list)
    errors = []
    warning_counts = Counter()
    split = Counter()
    diagnostic = Counter()
    alignment = []
    alignment_summary = {f: Counter() for f in DETAIL}
    overlaps = 0
    candidate_reference = 0
    candidate_hits = 0
    for row, pred in pairs:
        for key in ["loai_nhan:"+row["loai_nhan"], "nguon:"+row.get("nguon_du_lieu", "")]:
            groups[key].append((row, pred))
        variant = re.search(r"(?:^|;)\s*bien_the=([^;]+)", row.get("ghi_chu", ""))
        if variant:
            groups["bien_the:"+variant[1]].append((row, pred))
        flags = json.loads(row["canh_bao"])
        if "xa_bi_chia" in flags:
            groups["xa_bi_chia"].append((row, pred))
        warning_counts.update(pred["canh_bao"])
        expected_split = "xa_bi_chia" in flags
        predicted_split = "xa_bi_chia" in pred["canh_bao"]
        split["tp" if expected_split and predicted_split else "fn" if expected_split else "fp" if predicted_split else "tn"] += 1
        for field in FIELDS:
            if norm(row[field]) != norm(pred[field]):
                errors.append({"id": row["id"], "loai_nhan": row["loai_nhan"], "truong": field, "dau_vao": row["dau_vao"],
                               "nhan_tham_chieu": row[field], "du_doan": pred[field], "canh_bao": json.dumps(pred["canh_bao"], ensure_ascii=False)})
        if row["ma_xa"]:
            candidate_reference += 1
            candidates = sinh_ung_vien(tach_token(row["dau_vao"]), model.trie)
            possible = set().union(*(model.danh_muc.dich_xa(u.cay, u.ma) for u in candidates))
            hit = row["ma_xa"] in possible
            candidate_hits += int(hit)
            if row["ma_xa"] != pred["ma_xa"]:
                diagnostic["co_ung_vien_nhung_khong_chot_dung" if hit else "khong_sinh_duoc_dich_xa_tham_chieu"] += 1
        elif pred["ma_xa"]:
            diagnostic["tham_chieu_trong_nhung_du_doan_co_xa"] += 1
        occupied = set()
        row_overlap = False
        for field in DETAIL:
            if not row[field]:
                continue
            spans = align_detail(row["dau_vao"], field, row[field])
            state = "mot_vi_tri" if len(spans) == 1 else "nhieu_vi_tri" if spans else "khong_tim_thay"
            alignment_summary[field][state] += 1
            if len(spans) == 1:
                inds = set(range(*spans[0]))
                if occupied & inds:
                    row_overlap = True
                occupied.update(inds)
            alignment.append({"id": row["id"], "truong": field, "nhan": row[field], "trang_thai": state,
                              "khoang_token_noi_dung": json.dumps(spans), "dau_vao": row["dau_vao"]})
        overlaps += int(row_overlap)
    sorted_times = sorted(times)
    quantile = lambda q: sorted_times[max(0, math.ceil(q*len(times))-1)]
    data_unchanged = hashlib.sha256(raw).hexdigest() == digest(input_path)
    catalogue_unchanged = all(digest(ROOT / "data" / "clean" / name) == value for name, value in model.danh_muc.ma_bam.items())
    if not (data_unchanged and catalogue_unchanged):
        raise RuntimeError("Dữ liệu thay đổi trong lúc đo; không công bố báo cáo từ nhiều phiên bản trộn nhau")
    report = {"phien_ban": model.PHIEN_BAN, "thoi_diem_utc": datetime.now(timezone.utc).isoformat(),
              "python": platform.python_version(), "he_dieu_hanh": platform.platform(), "beam": beam,
              "input": str(input_path), "input_sha256": hashlib.sha256(raw).hexdigest(),
              "catalogue_sha256": model.danh_muc.ma_bam, "du_lieu_bao_toan_trong_luc_do": True,
              "phuong_phap": "So khớp NFC, casefold, gom khoảng trắng; giữ dấu. Không huấn luyện, không đọc test cuối.",
              "gioi_han": ["Dev gồm nhãn máy và nhãn tổng hợp, chưa được xác minh độc lập.",
                            "Đúng toàn bộ là 4 trường chi tiết và 2 mã hành chính; có tính trường trống.",
                            "Căn chỉnh nhãn chỉ xét nội dung token bỏ dấu, chưa xác nhận ngữ nghĩa hay tạo BIO.",
                            "RAM là của toàn tiến trình đánh giá, bao gồm dữ liệu và kết quả trong bộ nhớ.",
                            "Độ trễ chỉ gồm pipeline, không gồm asdict, I/O hoặc chẩn đoán; một lượt, một tiến trình, không warm-up riêng."],
              **aggregate(pairs), "theo_nhom": {k: aggregate(v) for k, v in sorted(groups.items())},
              "toc_do": {"khoi_tao_s": init_s, "tong_pipeline_s": sum(times)/1000, "dia_chi_moi_giay": 1000*len(times)/sum(times),
                         "trung_binh_ms": sum(times)/len(times), "p50_ms": quantile(.5), "p95_ms": quantile(.95), "max_ms": max(times)},
              "bo_nho": {"truoc_khoi_tao": before, "sau_khoi_tao": after_init, "sau_chay": after_run},
              "canh_bao": dict(warning_counts),
              "xa_bi_chia": {**{k: split[k] for k in ("tp", "fp", "fn", "tn")},
                             "precision_pct": pct(split["tp"], split["tp"]+split["fp"]), "recall_pct": pct(split["tp"], split["tp"]+split["fn"])},
              "sinh_ung_vien": {"nhan_ma_xa_khong_rong": candidate_reference, "co_dich_xa_trong_ung_vien": candidate_hits,
                                "ty_le_pct": pct(candidate_hits, candidate_reference), "chan_doan_loi_xa": dict(diagnostic)},
              "can_chinh_chi_tiet": {f: dict(alignment_summary[f]) for f in DETAIL}, "so_mau_chong_lan_noi_dung_nhan": overlaps}
    (output_dir / "thong_ke.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    write_csv(output_dir / "loi_tung_truong.csv", ("id", "loai_nhan", "truong", "dau_vao", "nhan_tham_chieu", "du_doan", "canh_bao"), errors)
    write_csv(output_dir / "can_chinh_nhan.csv", ("id", "truong", "nhan", "trang_thai", "khoang_token_noi_dung", "dau_vao"), alignment)
    # Hash code để các lần đo khác nhau có thể truy vết ngay cả khi chưa commit.
    code_files = list((ROOT / "src").glob("*.py")) + [Path(__file__)]
    (output_dir / "code_sha256.json").write_text(json.dumps({str(p.relative_to(ROOT)): digest(p) for p in code_files}, indent=2), encoding="utf-8")
    write_markdown(output_dir / "BAO_CAO.md", report)
    print(json.dumps({"so_mau": report["so_mau"], "khop_6_truong_pct": report["khop_toan_bo_6_truong_pct"], "toc_do": report["toc_do"], "output": str(output_dir)}, ensure_ascii=False, indent=2))
    return report


def write_markdown(path, r):
    t = r["toc_do"]
    lines = ["# Thống kê bản thử pipeline dùng luật", "", f"Đo trên **{r['so_mau']} mẫu dev**, beam={r['beam']}. Không dùng tập test cuối.", "",
             "Đây là mức khớp với nhãn tham chiếu máy/tổng hợp, chưa phải độ chính xác thực tế đã được xác minh. So khớp bỏ khác biệt chữ hoa và khoảng trắng, vẫn giữ dấu.", "",
             "## Kết quả từng trường", "", "| Trường | Đúng / tổng | Khớp (%) | Nhãn khác rỗng | Đúng trong nhãn khác rỗng (%) |", "|---|---:|---:|---:|---:|"]
    for f, m in r["tung_truong"].items():
        lines.append(f"| {f} | {m['dung']} / {m['tong']} | {m['ty_le_khop_pct']} | {m['nhan_khong_rong']} | {m['recall_nhan_khong_rong_pct']} |")
    lines += ["", f"Khớp đồng thời 4 trường chi tiết và 2 mã hành chính: **{r['dung_toan_bo_6_truong']}/{r['so_mau']} ({r['khop_toan_bo_6_truong_pct']}%)**. Chỉ số này bao gồm trường trống.", "",
              "## Theo nguồn và loại biến thể", "", "| Nhóm | Số mẫu | Khớp 6 trường (%) | Mã xã (%) | Mã tỉnh (%) | Đường (%) |", "|---|---:|---:|---:|---:|---:|"]
    for key, m in r["theo_nhom"].items():
        lines.append(f"| {key} | {m['so_mau']} | {m['khop_toan_bo_6_truong_pct']} | {m['tung_truong']['ma_xa']['ty_le_khop_pct']} | {m['tung_truong']['ma_tinh']['ty_le_khop_pct']} | {m['tung_truong']['duong']['ty_le_khop_pct']} |")
    s = r["xa_bi_chia"]
    lines += ["", "## Tốc độ và bộ nhớ", "", f"- Khởi tạo danh mục và trie: {t['khoi_tao_s']:.3f} giây.",
              f"- Một lượt pipeline tuần tự: {t['dia_chi_moi_giay']:.1f} địa chỉ/giây; trung bình {t['trung_binh_ms']:.3f} ms; p50 {t['p50_ms']:.3f} ms; p95 {t['p95_ms']:.3f} ms; lớn nhất {t['max_ms']:.3f} ms.",
              f"- Working set sau khởi tạo: {r['bo_nho']['sau_khoi_tao']['working_set_mib']} MiB; sau chạy: {r['bo_nho']['sau_chay']['working_set_mib']} MiB; đỉnh tiến trình tính đến cuối lượt pipeline: {r['bo_nho']['sau_chay']['peak_working_set_mib']} MiB.",
              "- Thời gian pipeline không gồm ghi file, chuyển dataclass sang dict và phần chẩn đoán. RAM gồm cả trình đánh giá và dữ liệu/kết quả đang giữ; không phải dự toán máy chủ.", "",
              "## Chẩn đoán", "", f"- Đích mã xã tham chiếu xuất hiện trong ứng viên: {r['sinh_ung_vien']['co_dich_xa_trong_ung_vien']}/{r['sinh_ung_vien']['nhan_ma_xa_khong_rong']} ({r['sinh_ung_vien']['ty_le_pct']}%). Chưa phản ánh việc chọn đúng tổ hợp.",
              f"- Cảnh báo xã bị chia: TP={s['tp']}, FP={s['fp']}, FN={s['fn']}; precision={s['precision_pct']}%, recall={s['recall_pct']}% so với nhãn tham chiếu.", ""]
    for key, value in r["sinh_ung_vien"]["chan_doan_loi_xa"].items():
        lines.append(f"- {key}: {value}.")
    lines += ["", "## Khả năng căn chỉnh dữ liệu cho CRF", "", "Kiểm tra vị trí nội dung của nhãn chi tiết trong token đầu vào, cho phép khác dấu và tiền tố chuẩn hóa. Chưa tạo nhãn BIO, chưa xác nhận ý nghĩa của nhãn. Một vị trí khớp không bảo đảm nhãn đúng.", "",
              "| Trường | Một vị trí | Nhiều vị trí | Không tìm thấy |", "|---|---:|---:|---:|"]
    for f, m in r["can_chinh_chi_tiet"].items():
        lines.append(f"| {f} | {m.get('mot_vi_tri', 0)} | {m.get('nhieu_vi_tri', 0)} | {m.get('khong_tim_thay', 0)} |")
    lines += ["", f"Có {r['so_mau_chong_lan_noi_dung_nhan']} mẫu có nội dung nhãn ở các trường khác nhau chồng token khi căn chỉnh duy nhất; cần xử lý trước khi tạo BIO.", "",
              "## Giới hạn bản thử", "", "- Luật tách chi tiết và trọng số xếp hạng đặt tay; chưa có CRF hoặc logistic regression đã huấn luyện.",
              "- Chỉ tìm gần đúng một ký tự với tên hành chính có tiền tố; tên không tiền tố chưa có fuzzy đầy đủ.",
              "- Không có từ điển đường/thôn để phục hồi dấu; tên không dấu được giữ và cảnh báo, nên có thể lệch nhãn tham chiếu có dấu.",
              "- Đoạn có tiền tố đường/thôn được bảo vệ khỏi nhận nhầm là hành chính; địa chỉ thiếu dấu phân cách có thể làm bỏ sót tên hành chính ở cuối đoạn đó.",
              "- Số nhà có '/' được giữ nguyên và cảnh báo, chưa tách thành nhà/ngõ khi thiếu căn cứ.",
              "- Tỷ lệ theo trường có thể cao do nhiều nhãn trống; xem thêm tỷ lệ trên nhãn khác rỗng và kết quả theo nguồn.", "",
              "## Tái lập và tệp đi kèm", "", f"- Input: `{r['input']}`; SHA-256: `{r['input_sha256']}`.",
              "- `thong_ke.json`: đầy đủ chỉ số, môi trường, mã băm danh mục và cảnh báo.",
              "- `du_doan.jsonl`: kết quả từng mẫu với dấu vết token/ký tự và thời gian.",
              "- `loi_tung_truong.csv`: từng chênh lệch giữa dự đoán và nhãn tham chiếu, không tự kết luận bên nào sai.",
              "- `can_chinh_nhan.csv`: kiểm tra khả năng căn chỉnh từng nhãn chi tiết.",
              "- `code_sha256.json`: mã băm source của lần đo chưa commit.",
              "- Mã băm input và sáu danh mục được kiểm tra lại sau lần đo; dữ liệu được bảo toàn trong suốt phép đo.", ""]
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", type=Path, default=ROOT / "data" / "train_dev" / "dev.csv")
    p.add_argument("--output-dir", type=Path, required=True, help="Thư mục mới; không ghi đè một lần đo cũ")
    p.add_argument("--beam", type=int, default=40)
    a = p.parse_args()
    run(a.input, a.output_dir, a.beam)


if __name__ == "__main__":
    main()
