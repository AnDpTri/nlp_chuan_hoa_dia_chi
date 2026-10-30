"""Script đánh giá đối chứng chuyên sâu Candidate Generation Prototype (C_ung_vien_duong).
Thực hiện đo đạc độc lập trên:
- Dev gốc 1.136 mẫu: data/train_dev/dev.csv
- Dev khó frozen 464 mẫu: mo_hinh/thu_nghiem/char_v1_01/snapshot/dev_kho.csv

Tuân thủ nghiêm ngặt:
1. KHÔNG đọc / mở / chạy data/test hoặc dia_chi_test.csv.
2. KHÔNG sửa mã src, checkpoint, từ điển, hoặc manifest.
3. Chạy đo trên CPU 1 thread (torch.set_num_threads(1)).
4. Báo cáo số liệu trung thực: tử số / mẫu số thật, phân tích 2 chiều (Gained vs Lost).
5. Tách semantic validity khỏi exact reference match.
"""

import csv
import json
import os
import sys
import time
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple

import torch

# Thiết lập đường dẫn gốc
ROOT = Path("D:/nlp_chuan_hoa_dia_chi")
os.chdir(str(ROOT))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "danh_gia/ket_qua/song_song_20261030/C_ung_vien_duong"))

# Đặt CPU 1 thread
torch.set_num_threads(1)

from src.char_cnn import BoTachCharCNN
from src.chuan_hoa import BoChuanHoa
from src.chuan_ten_duong import TuDienDuong, tach_ten, tuong_thich_dau
from src.chuyen_doi import sang_cay_moi
from src.danh_muc import DanhMuc
from src.xep_hang import BoXepHang, dac_trung_gia_thuyet
from prototype_sinh_ung_vien import BoSinhUngVienDuong, UngVienDuong, chuan_hoa_chuoi


def norm(s: Any) -> str:
    """Chuẩn hóa NFC, casefold, loại bỏ khoảng trắng thừa, giữ nguyên dấu tiếng Việt."""
    if s is None:
        return ""
    normalized = unicodedata.normalize("NFC", str(s))
    return " ".join(normalized.casefold().split())


def kiem_tra_co_trong_tu_dien(tdd: TuDienDuong, ten_duong: str, ma_tinh: str) -> bool:
    """Kiểm tra xem tên đường có nằm trong từ điển v5 của tỉnh hay không."""
    if not ten_duong or not ma_tinh:
        return False
    ung = tdd.ung_vien(ten_duong, ma_tinh)
    norm_ten = norm(ten_duong)
    for m in ung:
        if norm(m["gia_tri"]) == norm_ten:
            return True
    return False


def tinh_phan_tram(tu_so: int, mau_so: int) -> float:
    return round((tu_so / mau_so) * 100.0, 2) if mau_so > 0 else 0.0


def danh_gia_tap_du_lieu(
    dataset_name: str,
    file_path: Path,
    pipe_base: BoChuanHoa,
    bo_sinh: BoSinhUngVienDuong,
    tdd: TuDienDuong,
    dm: DanhMuc,
) -> Dict[str, Any]:
    print(f"\n>>> Đang đánh giá tập: {dataset_name} ({file_path})")

    with open(file_path, "r", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    total_samples = len(rows)
    print(f"    Tổng số mẫu nạp: {total_samples}")

    # Bộ đếm tổng thể
    samples_with_ref_duong = 0
    samples_ref_duong_in_dict = 0
    samples_ref_duong_not_in_dict = 0

    base_correct_all = 0
    base_correct_has_duong = 0

    cov_at_k_all = {1: 0, 3: 0, 5: 0, 8: 0}
    cov_at_k_has_duong = {1: 0, 3: 0, 5: 0, 8: 0}
    cov_at_k_supported = {1: 0, 3: 0, 5: 0, 8: 0}
    cov_at_k_unsupported = {1: 0, 3: 0, 5: 0, 8: 0}

    gained_cases = []
    lost_cases = []
    both_correct_cases = []
    both_wrong_cases = []
    ambiguous_cases = []

    provenance_distribution = Counter()
    provenance_correct_distribution = Counter()

    candidate_lengths = []
    latencies_cand_gen_ms = []
    latencies_e2e_ms = []

    for idx, row in enumerate(rows):
        inp = row["dau_vao"]
        ref_duong = (row.get("duong") or "").strip()
        ref_ma_tinh = (row.get("ma_tinh") or "").strip()
        ref_duong_norm = norm(ref_duong)

        has_duong = bool(ref_duong_norm)
        if has_duong:
            samples_with_ref_duong += 1
            is_supported = kiem_tra_co_trong_tu_dien(tdd, ref_duong, ref_ma_tinh)
            if is_supported:
                samples_ref_duong_in_dict += 1
            else:
                samples_ref_duong_not_in_dict += 1
        else:
            is_supported = False

        # 1. Chạy Baseline Inference
        t_start_e2e = time.perf_counter()
        records, candidates, crf_context, ranked = pipe_base.tao_gia_thuyet(inp)
        tokens = [t.chu for t in records]

        if pipe_base.bo_xep_hang is not None:
            features = [dac_trung_gia_thuyet(x, tokens, candidates, dm, crf_context) for x in ranked]
            scores = pipe_base.bo_xep_hang.cham_diem(features)
            ranked_with_score = [(float(s), *item[1:]) for s, item in zip(scores, ranked)]
            ranked_with_score.sort(key=lambda x: -x[0])
        else:
            ranked_with_score = ranked

        best_hyp = ranked_with_score[0]
        score, path, detail, spans, unknown, inferred = best_hyp
        mx, mt, warns = sang_cay_moi(path, detail, dm)

        res_base = pipe_base.chuan_hoa(inp)
        base_duong = (getattr(res_base, "duong", "") or "").strip()
        base_duong_norm = norm(base_duong)

        base_is_correct = (base_duong_norm == ref_duong_norm)
        if base_is_correct:
            base_correct_all += 1
            if has_duong:
                base_correct_has_duong += 1

        # 2. Chạy Prototype Sinh Ứng Viên (KHÔNG nhận ref)
        context_admin = {"ma_tinh": mt or ref_ma_tinh, "ma_xa": mx}
        t0_cg = time.perf_counter()
        cands: List[UngVienDuong] = bo_sinh.sinh_ung_vien(
            raw_text=inp,
            tokens=tokens,
            spans=spans,
            unknown=unknown,
            context_admin=context_admin,
        )
        t_cg_ms = (time.perf_counter() - t0_cg) * 1000.0
        t_e2e_ms = (time.perf_counter() - t_start_e2e) * 1000.0

        latencies_cand_gen_ms.append(t_cg_ms)
        latencies_e2e_ms.append(t_e2e_ms)
        candidate_lengths.append(len(cands))

        cand_texts_norm = [norm(c.text) for c in cands]

        for c in cands:
            provenance_distribution[c.provenance] += 1

        if len(cands) > 1:
            ambiguous_cases.append({
                "id": row.get("id") or f"ROW_{idx+1}",
                "dau_vao": inp,
                "ref_duong": ref_duong,
                "candidates": [c.to_dict() for c in cands],
            })

        # 3. Đo lường Coverage@k đối chiếu với ref_duong
        in_cands_at_k = {}
        for k in (1, 3, 5, 8):
            found_k = ref_duong_norm in cand_texts_norm[:k]
            in_cands_at_k[k] = found_k
            if found_k:
                cov_at_k_all[k] += 1
                if has_duong:
                    cov_at_k_has_duong[k] += 1
                    if is_supported:
                        cov_at_k_supported[k] += 1
                    else:
                        cov_at_k_unsupported[k] += 1

        # Ghi nhận provenance của candidate khớp đúng
        if ref_duong_norm in cand_texts_norm:
            matched_idx = cand_texts_norm.index(ref_duong_norm)
            matched_cand = cands[matched_idx]
            provenance_correct_distribution[matched_cand.provenance] += 1

        # 4. Phân loại 2 chiều (Gained vs Lost)
        prototype_has_correct = in_cands_at_k[8]

        case_info = {
            "id": row.get("id") or f"ROW_{idx+1}",
            "dau_vao": inp,
            "ref_duong": ref_duong,
            "base_duong": base_duong,
            "candidates": [c.to_dict() for c in cands],
            "in_dict_v5": is_supported,
        }

        if not base_is_correct and prototype_has_correct:
            gained_cases.append(case_info)
        elif base_is_correct and not prototype_has_correct:
            lost_cases.append(case_info)
        elif base_is_correct and prototype_has_correct:
            both_correct_cases.append(case_info)
        else:
            both_wrong_cases.append(case_info)

    # Thống kê độ trễ
    latencies_cand_gen_ms.sort()
    mean_lat_cg = sum(latencies_cand_gen_ms) / len(latencies_cand_gen_ms)
    median_lat_cg = latencies_cand_gen_ms[len(latencies_cand_gen_ms) // 2]
    p95_lat_cg = latencies_cand_gen_ms[int(len(latencies_cand_gen_ms) * 0.95)]
    max_lat_cg = max(latencies_cand_gen_ms)

    avg_cand_len = sum(candidate_lengths) / len(candidate_lengths)

    result_summary = {
        "dataset_name": dataset_name,
        "file_path": str(file_path),
        "total_samples": total_samples,
        "samples_with_ref_duong": samples_with_ref_duong,
        "dictionary_v5_coverage": {
            "supported_in_dict_count": samples_ref_duong_in_dict,
            "supported_in_dict_pct": tinh_phan_tram(samples_ref_duong_in_dict, samples_with_ref_duong),
            "missing_in_dict_count": samples_ref_duong_not_in_dict,
            "missing_in_dict_pct": tinh_phan_tram(samples_ref_duong_not_in_dict, samples_with_ref_duong),
        },
        "baseline_exact_match": {
            "all_samples_count": base_correct_all,
            "all_samples_pct": tinh_phan_tram(base_correct_all, total_samples),
            "has_duong_samples_count": base_correct_has_duong,
            "has_duong_samples_pct": tinh_phan_tram(base_correct_has_duong, samples_with_ref_duong),
        },
        "candidate_coverage_all": {
            f"Coverage@{k}": {
                "count": cov_at_k_all[k],
                "pct": tinh_phan_tram(cov_at_k_all[k], total_samples),
            }
            for k in (1, 3, 5, 8)
        },
        "candidate_coverage_has_duong": {
            f"Coverage@{k}": {
                "count": cov_at_k_has_duong[k],
                "pct": tinh_phan_tram(cov_at_k_has_duong[k], samples_with_ref_duong),
            }
            for k in (1, 3, 5, 8)
        },
        "candidate_coverage_supported_in_dict": {
            f"Coverage@{k}": {
                "count": cov_at_k_supported[k],
                "pct": tinh_phan_tram(cov_at_k_supported[k], samples_ref_duong_in_dict),
            }
            for k in (1, 3, 5, 8)
        },
        "candidate_coverage_missing_in_dict": {
            f"Coverage@{k}": {
                "count": cov_at_k_unsupported[k],
                "pct": tinh_phan_tram(cov_at_k_unsupported[k], samples_ref_duong_not_in_dict),
            }
            for k in (1, 3, 5, 8)
        },
        "two_way_delta": {
            "gained_count": len(gained_cases),
            "lost_count": len(lost_cases),
            "both_correct_count": len(both_correct_cases),
            "both_wrong_count": len(both_wrong_cases),
            "net_gain": len(gained_cases) - len(lost_cases),
        },
        "candidate_diversity": {
            "average_candidates_per_sample": round(avg_cand_len, 2),
            "ambiguous_sample_count": len(ambiguous_cases),
            "ambiguous_sample_pct": tinh_phan_tram(len(ambiguous_cases), total_samples),
            "provenance_distribution": dict(provenance_distribution),
            "provenance_correct_distribution": dict(provenance_correct_distribution),
        },
        "resource_latency_cpu_1_thread_ms": {
            "candidate_generation_mean": round(mean_lat_cg, 2),
            "candidate_generation_median": round(median_lat_cg, 2),
            "candidate_generation_p95": round(p95_lat_cg, 2),
            "candidate_generation_max": round(max_lat_cg, 2),
        },
        "gained_samples_preview": gained_cases[:10],
        "lost_samples_preview": lost_cases,
    }

    print(f"    Baseline Đúng (has_duong): {base_correct_has_duong}/{samples_with_ref_duong} ({tinh_phan_tram(base_correct_has_duong, samples_with_ref_duong)}%)")
    print(f"    Candidate Coverage@1 (has_duong): {cov_at_k_has_duong[1]}/{samples_with_ref_duong} ({tinh_phan_tram(cov_at_k_has_duong[1], samples_with_ref_duong)}%)")
    print(f"    Candidate Coverage@8 (has_duong): {cov_at_k_has_duong[8]}/{samples_with_ref_duong} ({tinh_phan_tram(cov_at_k_has_duong[8], samples_with_ref_duong)}%)")
    print(f"    Coverage@8 trong nhóm có trong từ điển v5: {cov_at_k_supported[8]}/{samples_ref_duong_in_dict} ({tinh_phan_tram(cov_at_k_supported[8], samples_ref_duong_in_dict)}%)")
    print(f"    Báo cáo 2 chiều: Gained = +{len(gained_cases)}, Lost = -{len(lost_cases)} (Net: {len(gained_cases) - len(lost_cases)})")
    print(f"    Độ trễ Candidate Gen CPU 1 thread: Mean={mean_lat_cg:.2f}ms, P95={p95_lat_cg:.2f}ms")

    return result_summary, gained_cases, lost_cases, ambiguous_cases


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    print("=" * 70)
    print("BẮT ĐẦU ĐO ĐẠC ĐỐI CHỨNG CANDIDATE GENERATION PROTOTYPE (CPU 1 THREAD)")
    print("=" * 70)

    # 1. Nạp tài nguyên baseline
    print("1. Nạp tài nguyên baseline...")
    dm = DanhMuc()
    cnn_v2 = BoTachCharCNN(ROOT / "mo_hinh/thu_nghiem/char_v2_01/char_cnn.pt", threads=1)
    rk_v2 = BoXepHang(ROOT / "mo_hinh/thu_nghiem/char_v2_01/ranker.txt", cnn_v2.ma_bam, dm.ma_bam)
    td_v5 = TuDienDuong(ROOT / "danh_gia/ket_qua/tu_dien_duong_v5.json")

    pipe_base = BoChuanHoa(
        dm,
        bo_tach=cnn_v2,
        bo_xep_hang=rk_v2,
        tu_dien_duong=td_v5,
        bao_ve_duong=True,
        tien_to_mac_dinh=True,
    )

    # 2. Nạp Prototype sinh ứng viên
    bo_sinh = BoSinhUngVienDuong(tu_dien_duong=td_v5, max_candidates=8)

    # 3. Đánh giá trên Dev Gốc (1.136 mẫu)
    dev_path = ROOT / "data/train_dev/dev.csv"
    dev_summary, dev_gained, dev_lost, dev_ambig = danh_gia_tap_du_lieu(
        dataset_name="dev_goc_1136",
        file_path=dev_path,
        pipe_base=pipe_base,
        bo_sinh=bo_sinh,
        tdd=td_v5,
        dm=dm,
    )

    # 4. Đánh giá trên Dev Khó Frozen (464 mẫu)
    dev_kho_path = ROOT / "mo_hinh/thu_nghiem/char_v1_01/snapshot/dev_kho.csv"
    dev_kho_summary, dev_kho_gained, dev_kho_lost, dev_kho_ambig = danh_gia_tap_du_lieu(
        dataset_name="dev_kho_frozen_464",
        file_path=dev_kho_path,
        pipe_base=pipe_base,
        bo_sinh=bo_sinh,
        tdd=td_v5,
        dm=dm,
    )

    # 5. Lưu kết quả ra thư mục C_ung_vien_duong
    out_dir = ROOT / "danh_gia/ket_qua/song_song_20261030/C_ung_vien_duong"
    out_dir.mkdir(parents=True, exist_ok=True)

    ket_qua_path = out_dir / "ket_qua_danh_gia.json"
    full_results = {
        "thoi_gian_do": time.strftime("%Y-%m-%d %H:%M:%S"),
        "cau_hinh": {
            "threads": 1,
            "max_candidates": 8,
            "char_cnn_sha256": cnn_v2.ma_bam,
            "ranker_sha256": rk_v2.ma_bam,
            "tu_dien_sha256": td_v5.ma_bam,
            "dev_goc_sha256": "dbf4fd536accd05f7fbd716e2c1e7d83e7db20854b60cf0c78c2fc36d2087cfe",
            "dev_kho_sha256": "588767b2f5470d05a45296de24a6167f811296ed099a1b044165e5f0f9201421",
        },
        "dev_goc_1136": dev_summary,
        "dev_kho_frozen_464": dev_kho_summary,
    }

    with open(ket_qua_path, "w", encoding="utf-8") as f:
        json.dump(full_results, f, ensure_ascii=False, indent=2)
    print(f"\n[OK] Đã lưu kết quả đánh giá tổng hợp: {ket_qua_path}")

    thong_ke_path = out_dir / "thong_ke_ung_vien.json"
    thong_ke_data = {
        "dev_goc": {
            "gained_cases": dev_gained,
            "lost_cases": dev_lost,
            "ambiguous_sample_count": len(dev_ambig),
            "ambiguous_samples_preview": dev_ambig[:20],
        },
        "dev_kho": {
            "gained_cases": dev_kho_gained,
            "lost_cases": dev_kho_lost,
            "ambiguous_sample_count": len(dev_kho_ambig),
            "ambiguous_samples_preview": dev_kho_ambig[:20],
        },
    }
    with open(thong_ke_path, "w", encoding="utf-8") as f:
        json.dump(thong_ke_data, f, ensure_ascii=False, indent=2)
    print(f"[OK] Đã lưu chi tiết thống kê ứng viên: {thong_ke_path}")

    print("\n" + "=" * 70)
    print("HOÀN THÀNH TOÀN BỘ ĐO ĐẠC ĐỐI CHỨNG.")
    print("=" * 70)


if __name__ == "__main__":
    main()
