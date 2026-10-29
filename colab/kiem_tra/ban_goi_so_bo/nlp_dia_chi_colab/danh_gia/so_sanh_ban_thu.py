"""So input/output của hai lần đo trên cùng dữ liệu và danh mục."""

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
from .chay_ban_thu import CORE, FIELDS, norm, write_csv


def compare(before, after):
    reports = [json.loads((p / "thong_ke.json").read_text(encoding="utf-8")) for p in (before, after)]
    old, new = reports
    old_version, new_version = old['phien_ban'], new['phien_ban']
    if old["input_sha256"] != new["input_sha256"] or old["catalogue_sha256"] != new["catalogue_sha256"]:
        raise ValueError("Hai lần đo không cùng dữ liệu/danh mục")
    input_path = Path(new["input"])
    if hashlib.sha256(input_path.read_bytes()).hexdigest() != new["input_sha256"]:
        raise ValueError("Dữ liệu tham chiếu đã đổi từ lúc đo")
    with input_path.open(encoding="utf-8-sig", newline="") as f:
        refs = {r["id"]: r for r in csv.DictReader(f)}
    preds = [{r["id"]: r for r in map(json.loads, (p / "du_doan.jsonl").read_text(encoding="utf-8").splitlines())} for p in (before, after)]
    a, b = preds
    if set(a) != set(b) or set(b) != set(refs):
        raise ValueError("Khác tập ID trong kết quả và tham chiếu")
    counts = Counter({k: 0 for k in ("giu_khop", "moi_khop", "mat_khop", "van_lech")})
    perfield = {f: Counter(moi_khop=0, mat_khop=0) for f in FIELDS}
    rows = []
    for key, r in refs.items():
        before_ok, after_ok = [all(norm(r[f]) == norm(p[key][f]) for f in CORE) for p in preds]
        state = "moi_khop" if after_ok and not before_ok else "mat_khop" if before_ok and not after_ok else "giu_khop" if after_ok else "van_lech"
        counts[state] += 1
        for f in FIELDS:
            x, y = norm(a[key][f]) == norm(r[f]), norm(b[key][f]) == norm(r[f])
            if x != y:
                perfield[f]["moi_khop" if y else "mat_khop"] += 1
        rows.append({"id": key, "trang_thai": state, "dau_vao": r["dau_vao"],
                     "output_truoc": a[key]["dia_chi_chuan"], "output_sau": b[key]["dia_chi_chuan"],
                     "nhan_tham_chieu": r["dia_chi_chuan"],
                     "truong_lech_truoc": ",".join(f for f in FIELDS if norm(a[key][f]) != norm(r[f])),
                     "truong_lech_sau": ",".join(f for f in FIELDS if norm(b[key][f]) != norm(r[f])),
                     "canh_bao_sau": json.dumps(b[key]["canh_bao"], ensure_ascii=False)})
    summary = {"phien_ban_truoc": old_version, "phien_ban_sau": new_version,
               "truoc": old["khop_toan_bo_6_truong_pct"], "sau": new["khop_toan_bo_6_truong_pct"],
               "so_mau": len(rows), "chuyen_trang_thai": dict(counts),
               "tung_truong": {f: {"truoc_pct": old["tung_truong"][f]["ty_le_khop_pct"],
                                  "sau_pct": new["tung_truong"][f]["ty_le_khop_pct"], **dict(perfield[f])} for f in FIELDS}}
    write_csv(after / "so_sanh_tung_mau.csv", list(rows[0]), rows)
    (after / "so_sanh.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [f"# So sánh {old_version} và {new_version}", "", f"Cùng {len(rows)} mẫu dev và sáu bảng danh mục, đã đối chiếu mã băm.", "",
             f"Khớp đồng thời sáu trường: **{old['dung_toan_bo_6_truong']}/{len(rows)} ({summary['truoc']}%) → {new['dung_toan_bo_6_truong']}/{len(rows)} ({summary['sau']}%)**.", "",
             f"Có **{counts['moi_khop']} mẫu mới khớp đủ sáu trường**, **{counts['mat_khop']} mẫu từ khớp đủ sáu trường thành không khớp**. Các số này so với nhãn dev máy/tổng hợp, không phải đánh giá độc lập về độ chính xác thực tế.", "",
             "| Trường | Trước (%) | Sau (%) | Mới khớp | Mất khớp |", "|---|---:|---:|---:|---:|"]
    for f, m in summary["tung_truong"].items():
        lines.append(f"| {f} | {m['truoc_pct']} | {m['sau_pct']} | {m['moi_khop']} | {m['mat_khop']} |")
    lines += ["", "Một số trường riêng vẫn có thể mất khớp ở mẫu vốn chưa khớp toàn bộ; xem bảng và CSV đầy đủ. Không sửa nhãn tham chiếu để tăng điểm.", "",
              f"- OSM: {old['theo_nhom']['nguon:osm_public']['khop_toan_bo_6_truong_pct']}% → {new['theo_nhom']['nguon:osm_public']['khop_toan_bo_6_truong_pct']}%.",
              f"- Tổng hợp: {old['theo_nhom']['loai_nhan:tong_hop']['khop_toan_bo_6_truong_pct']}% → {new['theo_nhom']['loai_nhan:tong_hop']['khop_toan_bo_6_truong_pct']}%.", "", "## Input và output thực tế", ""]
    for key in ("VNDEV_00024", "VNDEV_00031", "VNDEV_00036", "VNDEV_00342", "VNDEV_00505", "VNDEV_00553", "VNDEV_01041", "VNDEV_01095", "VNDEV_00044", "VNDEV_00201"):
        if key not in refs:
            continue
        r = refs[key]
        lines += [f"**{key}**", "", f"Input: `{r['dau_vao']}`", "", f"Trước ({old_version}): `{a[key]['dia_chi_chuan']}`", "",
                  f"Sau ({new_version}): `{b[key]['dia_chi_chuan']}`", "", f"Nhãn tham chiếu: `{r['dia_chi_chuan']}`", "",
                  f"Cảnh báo sau: `{json.dumps(b[key]['canh_bao'], ensure_ascii=False)}`", ""]
    lines += ["## Giới hạn và tệp đi kèm", "", "- Chưa giải mọi tên riêng viết tắt hoặc phục hồi dấu mọi tên đường/thôn; nhãn dev vẫn có lỗi và nhiều mẫu chưa xác định được.",
              "- Thiếu căn cứ về xã bị chia hay mốc cũ/mới thì giữ cảnh báo/ứng viên; không ép một đích để khớp nhãn.",
              "- Tốc độ/RAM trong BAO_CAO.md là một lượt trên máy hiện tại, không phải phép so sánh hiệu năng có kiểm soát hay phép đo tải máy chủ.",
              "- du_doan.jsonl: output đầy đủ và dấu vết từng mẫu.", "- so_sanh_tung_mau.csv: input/output trước–sau và nhãn nguồn cho đủ 1.136 mẫu.",
              "- loi_tung_truong.csv: chênh lệch còn lại.", "- code_sha256.json và thong_ke.json: phiên bản source, dữ liệu và phép đo.", ""]
    (after / "SO_SANH.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--before", type=Path, required=True)
    p.add_argument("--after", type=Path, required=True)
    args = p.parse_args()
    compare(args.before, args.after)
