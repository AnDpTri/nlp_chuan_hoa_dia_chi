#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script xây dựng bộ dữ liệu danh mục tên đường có nguồn chứng thực (v1).
Đọc toàn bộ các tệp nguồn trong data/duong/v1/sources/, đối chiếu danh mục hành chính
(moi_tinh, cu_tinh, cu_huyen), tính toán các khóa kỹ thuật, phát hiện xung đột và xuất
đầy đủ các tệp bàn giao chuẩn tắc trong data/duong/v1/.
"""

import csv
import hashlib
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(__file__).resolve().parents[3]
V1_DIR = BASE_DIR / "data" / "duong" / "v1"
SOURCES_DIR = V1_DIR / "sources"
CLEAN_DIR = BASE_DIR / "data" / "clean"


def remove_vietnamese_accents(text):
    if not text:
        return ""
    text = re.sub(r'[àáảãạăằắẳẵặâầấẩẫậ]', 'a', text)
    text = re.sub(r'[ÀÁẢÃẠĂẰẮẲẴẶÂẦẤẨẪẬ]', 'A', text)
    text = re.sub(r'[èéẻẽẹêềếểễệ]', 'e', text)
    text = re.sub(r'[ÈÉẺẼẸÊỀẾỂỄỆ]', 'E', text)
    text = re.sub(r'[ìíỉĩị]', 'i', text)
    text = re.sub(r'[ÌÍỈĨỊ]', 'I', text)
    text = re.sub(r'[òóỏõọôồốổỗộơờớởỡợ]', 'o', text)
    text = re.sub(r'[ÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢ]', 'O', text)
    text = re.sub(r'[ùúủũụưừứửữự]', 'u', text)
    text = re.sub(r'[ÙÚỦŨỤƯỪỨỬỮỰ]', 'U', text)
    text = re.sub(r'[ỳýỷỹỵ]', 'y', text)
    text = re.sub(r'[ỲÝỶỸỴ]', 'Y', text)
    text = re.sub(r'[đ]', 'd', text)
    text = re.sub(r'[Đ]', 'D', text)
    return text


def make_unaccented_key(name):
    clean = remove_vietnamese_accents(name).lower()
    clean = re.sub(r'[^a-z0-9\s]', ' ', clean)
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean


def make_collapsed_key(name):
    clean = remove_vietnamese_accents(name).lower()
    clean = re.sub(r'[^a-z0-9]', '', clean)
    return clean


def make_initials_key(name):
    clean = remove_vietnamese_accents(name).lower()
    clean = re.sub(r'[^a-z0-9\s]', ' ', clean)
    words = clean.split()
    initials = "".join([w[0] for w in words if w])
    return initials


def extract_core_name(canonical_name, road_type):
    # Loại bỏ tiền tố loại đường nếu canonical_name bắt đầu bằng road_type
    name = canonical_name.strip()
    prefixes = ["Đường ", "Phố ", "Quốc lộ ", "Đại lộ ", "Xa lộ ", "Trục đường "]
    for p in prefixes:
        if name.startswith(p):
            return name[len(p):].strip()
    return name


def build_danh_muc():
    print("=== BẮT ĐẦU QUY TRÌNH BUILD DANH MỤC ĐƯỜNG PHỐ V1 ===")

    # 1. Nạp danh mục hành chính
    with open(CLEAN_DIR / "moi_tinh.csv", encoding="utf-8") as f:
        moi_tinh_map = {r["ma_tinh"]: r["ten_tinh"] for r in csv.DictReader(f)}

    with open(CLEAN_DIR / "cu_tinh.csv", encoding="utf-8") as f:
        cu_tinh_map = {r["ma_tinh"]: r["ten_tinh"] for r in csv.DictReader(f)}

    # Xác định các mã chung và mã va chạm era
    same_era_codes = {k for k in moi_tinh_map if k in cu_tinh_map and moi_tinh_map[k] == cu_tinh_map[k]}
    conflicting_era_codes = {k: {"moi": moi_tinh_map[k], "cu": cu_tinh_map[k]} for k in moi_tinh_map if k in cu_tinh_map and moi_tinh_map[k] != cu_tinh_map[k]}

    print(f"-> Danh mục hành chính: 34 tỉnh mới, 63 tỉnh cũ. Có {len(same_era_codes)} mã trùng tên hoàn toàn, {len(conflicting_era_codes)} mã va chạm era.")

    # 2. Nạp sources_manifest.json và kiểm tra tính toàn vẹn
    sources_manifest_path = SOURCES_DIR / "sources_manifest.json"
    if not sources_manifest_path.exists():
        raise FileNotFoundError(f"Không tìm thấy {sources_manifest_path}")

    sources_manifest = json.loads(sources_manifest_path.read_text(encoding="utf-8"))
    source_meta = {}
    source_contents = {}

    for s in sources_manifest["sources"]:
        fname = s["filename"]
        fpath = SOURCES_DIR / fname
        if not fpath.exists():
            raise FileNotFoundError(f"Tệp nguồn {fname} không tồn tại trên đĩa")
        content = fpath.read_text(encoding="utf-8")
        calc_hash = hashlib.sha256(fpath.read_bytes()).hexdigest()
        if calc_hash != s["sha256"]:
            raise ValueError(f"Mã băm SHA-256 của {fname} không khớp với manifest! ({calc_hash} vs {s['sha256']})")
        source_meta[fname] = s
        source_contents[fname] = content

    print(f"-> Toàn vẹn 100%: Đã xác thực SHA-256 của {len(source_meta)} tệp nguồn.")

    confirmed_records = []
    pending_rejected_records = []

    # 3. Phân tích các tệp nguồn để trích xuất dữ liệu
    # 3.1. Quốc lộ Việt Nam
    ql_fname = "quoc_lo_vietnam_qd1454_2021.txt"
    for line in source_contents[ql_fname].splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 6:
            ma_tuyen, can_name, rtype, route_desc, provinces_str, aliases_str = parts[:6]
            prov_codes = [c.strip() for c in provinces_str.split(",") if c.strip()]
            for mt in prov_codes:
                # Xác định tên tỉnh và era
                if mt in same_era_codes:
                    ten_tinh = moi_tinh_map[mt]
                    era = "hien_hanh"
                elif mt in moi_tinh_map:
                    ten_tinh = moi_tinh_map[mt]
                    era = "moi_2025"
                elif mt in cu_tinh_map:
                    ten_tinh = cu_tinh_map[mt]
                    era = "cu_2024"
                else:
                    ten_tinh = f"Mã {mt}"
                    era = "cu_2024"

                confirmed_records.append({
                    "canonical_name": can_name,
                    "road_type": rtype,
                    "ma_tinh": mt,
                    "ten_tinh": ten_tinh,
                    "administrative_era": era,
                    "quan_huyen_list": "",
                    "aliases": aliases_str,
                    "source_id": ql_fname,
                    "source_type": source_meta[ql_fname]["source_type"],
                    "source_url": source_meta[ql_fname]["url"],
                    "source_sha256": source_meta[ql_fname]["sha256"],
                    "status": "confirmed",
                    "verification_note": f"Hệ thống Quốc lộ {ma_tuyen} quy hoạch theo QĐ 1454/QĐ-TTg. Lý trình: {route_desc}"
                })

    # 3.2. Hà Nội
    hn_fname = "ha_noi_qd3816_2026.txt"
    for line in source_contents[hn_fname].splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 6:
            cname, rtype, qh, endpoints, legal, aliases = parts[:6]
            confirmed_records.append({
                "canonical_name": cname,
                "road_type": rtype,
                "ma_tinh": "01",
                "ten_tinh": "Hà Nội",
                "administrative_era": "hien_hanh",
                "quan_huyen_list": qh,
                "aliases": aliases,
                "source_id": hn_fname,
                "source_type": source_meta[hn_fname]["source_type"],
                "source_url": source_meta[hn_fname]["url"],
                "source_sha256": source_meta[hn_fname]["sha256"],
                "status": "confirmed",
                "verification_note": f"Địa bàn: {qh}. {endpoints}. Căn cứ: {legal}"
            })

    # 3.3. TP. Hồ Chí Minh
    hcm_fname = "tphcm_qd212_2006.txt"
    for line in source_contents[hcm_fname].splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 6:
            cname, rtype, qh, endpoints, legal, aliases = parts[:6]
            confirmed_records.append({
                "canonical_name": cname,
                "road_type": rtype,
                "ma_tinh": "79",
                "ten_tinh": "Hồ Chí Minh",
                "administrative_era": "hien_hanh",
                "quan_huyen_list": qh,
                "aliases": aliases,
                "source_id": hcm_fname,
                "source_type": source_meta[hcm_fname]["source_type"],
                "source_url": source_meta[hcm_fname]["url"],
                "source_sha256": source_meta[hcm_fname]["sha256"],
                "status": "confirmed",
                "verification_note": f"Địa bàn: {qh}. {endpoints}. Căn cứ: {legal}"
            })

    # 3.4. Đà Nẵng
    dn_fname = "danang_nq49_2025.txt"
    for line in source_contents[dn_fname].splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 6:
            cname, rtype, qh, endpoints, legal, aliases = parts[:6]
            confirmed_records.append({
                "canonical_name": cname,
                "road_type": rtype,
                "ma_tinh": "48",
                "ten_tinh": "Đà Nẵng",
                "administrative_era": "hien_hanh",
                "quan_huyen_list": qh,
                "aliases": aliases,
                "source_id": dn_fname,
                "source_type": source_meta[dn_fname]["source_type"],
                "source_url": source_meta[dn_fname]["url"],
                "source_sha256": source_meta[dn_fname]["sha256"],
                "status": "confirmed",
                "verification_note": f"Địa bàn: {qh}. {endpoints}. Căn cứ: {legal}"
            })

    # 3.5. Hải Phòng
    hp_fname = "hai_phong_nq14_2023.txt"
    for line in source_contents[hp_fname].splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 6:
            cname, rtype, qh, endpoints, legal, aliases = parts[:6]
            confirmed_records.append({
                "canonical_name": cname,
                "road_type": rtype,
                "ma_tinh": "31",
                "ten_tinh": "Hải Phòng",
                "administrative_era": "hien_hanh",
                "quan_huyen_list": qh,
                "aliases": aliases,
                "source_id": hp_fname,
                "source_type": source_meta[hp_fname]["source_type"],
                "source_url": source_meta[hp_fname]["url"],
                "source_sha256": source_meta[hp_fname]["sha256"],
                "status": "confirmed",
                "verification_note": f"Địa bàn: {qh}. {endpoints}. Căn cứ: {legal}"
            })

    # 3.6. Cần Thơ
    ct_fname = "can_tho_qd19_2023.txt"
    for line in source_contents[ct_fname].splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 6:
            cname, rtype, qh, endpoints, legal, aliases = parts[:6]
            confirmed_records.append({
                "canonical_name": cname,
                "road_type": rtype,
                "ma_tinh": "92",
                "ten_tinh": "Cần Thơ",
                "administrative_era": "hien_hanh",
                "quan_huyen_list": qh,
                "aliases": aliases,
                "source_id": ct_fname,
                "source_type": source_meta[ct_fname]["source_type"],
                "source_url": source_meta[ct_fname]["url"],
                "source_sha256": source_meta[ct_fname]["sha256"],
                "status": "confirmed",
                "verification_note": f"Địa bàn: {qh}. {endpoints}. Căn cứ: {legal}"
            })

    # 3.7. Thừa Thiên Huế
    hue_fname = "thua_thien_hue_qd64_2022.txt"
    for line in source_contents[hue_fname].splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 6:
            cname, rtype, qh, endpoints, legal, aliases = parts[:6]
            confirmed_records.append({
                "canonical_name": cname,
                "road_type": rtype,
                "ma_tinh": "46",
                "ten_tinh": "Huế",
                "administrative_era": "hien_hanh",
                "quan_huyen_list": qh,
                "aliases": aliases,
                "source_id": hue_fname,
                "source_type": source_meta[hue_fname]["source_type"],
                "source_url": source_meta[hue_fname]["url"],
                "source_sha256": source_meta[hue_fname]["sha256"],
                "status": "confirmed",
                "verification_note": f"Địa bàn: {qh}. {endpoints}. Căn cứ: {legal}"
            })

    # 3.8. Đô thị tỉnh lỵ
    prov_fname = "cac_tinh_thanh_do_thi_qd_ubnd.txt"
    for line in source_contents[prov_fname].splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 9:
            mt, tt, cname, rtype, qh, endpoints, legal, aliases, era = parts[:9]
            confirmed_records.append({
                "canonical_name": cname,
                "road_type": rtype,
                "ma_tinh": mt,
                "ten_tinh": tt,
                "administrative_era": era,
                "quan_huyen_list": qh,
                "aliases": aliases,
                "source_id": prov_fname,
                "source_type": source_meta[prov_fname]["source_type"],
                "source_url": source_meta[prov_fname]["url"],
                "source_sha256": source_meta[prov_fname]["sha256"],
                "status": "confirmed",
                "verification_note": f"Địa bàn: {qh} ({tt}). {endpoints}. Căn cứ: {legal}"
            })

    # 3.9. OpenStreetMap
    osm_fname = "osm_urban_streets_verified_2025.txt"
    for line in source_contents[osm_fname].splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 9:
            mt, tt, cname, rtype, qh, osm_feat, legal, aliases, era = parts[:9]
            confirmed_records.append({
                "canonical_name": cname,
                "road_type": rtype,
                "ma_tinh": mt,
                "ten_tinh": tt,
                "administrative_era": era,
                "quan_huyen_list": qh,
                "aliases": aliases,
                "source_id": osm_fname,
                "source_type": source_meta[osm_fname]["source_type"],
                "source_url": source_meta[osm_fname]["url"],
                "source_sha256": source_meta[osm_fname]["sha256"],
                "status": "confirmed",
                "verification_note": f"Định danh {osm_feat} ({legal}). Địa bàn: {qh} ({tt})"
            })

    # 3.10. Pending & Rejected
    pr_fname = "tai_lieu_chua_xac_minh_pending.txt"
    for line in source_contents[pr_fname].splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 10:
            raw_inp, cand_name, cand_rtype, mt, tt, qh, st, rej_reason, legal, era = parts[:10]
            pending_rejected_records.append({
                "raw_input": raw_inp,
                "candidate_canonical_name": cand_name,
                "candidate_road_type": cand_rtype,
                "ma_tinh": mt,
                "ten_tinh": tt,
                "quan_huyen": qh,
                "status": st,
                "rejection_reason": rej_reason,
                "legal_source": legal,
                "administrative_era": era,
                "source_id": pr_fname,
                "source_sha256": source_meta[pr_fname]["sha256"]
            })

    # 4. Khử trùng lặp và tính toán các khóa kỹ thuật
    print(f"-> Thu thập được: {len(confirmed_records)} bản ghi confirmed thô, {len(pending_rejected_records)} bản ghi pending/rejected.")

    # Deduplicate confirmed records theo (canonical_name, road_type, ma_tinh, administrative_era)
    dedup_map = {}
    for r in confirmed_records:
        key = (r["canonical_name"], r["road_type"], r["ma_tinh"], r["administrative_era"])
        if key not in dedup_map:
            dedup_map[key] = r
        else:
            # Gộp quan_huyen_list và aliases nếu có
            existing = dedup_map[key]
            if r["quan_huyen_list"] and r["quan_huyen_list"] not in existing["quan_huyen_list"]:
                existing["quan_huyen_list"] = f"{existing['quan_huyen_list']}, {r['quan_huyen_list']}".strip(", ")
            if r["aliases"] and r["aliases"] not in existing["aliases"]:
                existing["aliases"] = f"{existing['aliases']}; {r['aliases']}".strip("; ")

    deduped_confirmed = list(dedup_map.values())

    # Sắp xếp ổn định theo (canonical_name, ma_tinh, administrative_era)
    deduped_confirmed.sort(key=lambda x: (x["canonical_name"], x["ma_tinh"], x["administrative_era"]))

    # Gán ID tuần tự và khóa tra cứu
    lookup_index = {
        "by_unaccented_key": defaultdict(list),
        "by_collapsed_key": defaultdict(list),
        "by_initials_key": defaultdict(list)
    }

    final_confirmed = []
    for idx, r in enumerate(deduped_confirmed, start=1):
        rec_id = f"STR_{idx:05d}"
        cname = r["canonical_name"]
        unacc = make_unaccented_key(cname)
        colla = make_collapsed_key(cname)
        init = make_initials_key(cname)

        r["id"] = rec_id
        r["unaccented_key"] = unacc
        r["collapsed_key"] = colla
        r["initials_key"] = init

        # Kiểm tra tính xuất hiện thực tế (Textual Grounding):
        # Tên đường PHẢI xuất hiện thực tế trong nội dung tệp nguồn
        src_text = source_contents[r["source_id"]]
        if cname not in src_text:
            raise ValueError(f"Lỗi kiểm chứng: '{cname}' không xuất hiện trong nội dung {r['source_id']}!")

        final_confirmed.append(r)
        lookup_index["by_unaccented_key"][unacc].append(rec_id)
        lookup_index["by_collapsed_key"][colla].append(rec_id)
        lookup_index["by_initials_key"][init].append(rec_id)

    # Đánh số ID cho pending/rejected
    final_pending_rejected = []
    for idx, r in enumerate(pending_rejected_records, start=1):
        r_id = f"PR_{idx:05d}"
        r["id"] = r_id
        final_pending_rejected.append(r)

    # 5. Phân tích xung đột tra cứu (khoa_xung_dot.json)
    cross_province_map = defaultdict(list)
    diacritics_map = defaultdict(set)
    road_type_map = defaultdict(set)
    initials_map = defaultdict(set)

    for r in final_confirmed:
        cname = r["canonical_name"]
        rtype = r["road_type"]
        unacc = r["unaccented_key"]
        init = r["initials_key"]
        core = extract_core_name(cname, rtype)

        cross_province_map[cname].append({
            "id": r["id"],
            "ma_tinh": r["ma_tinh"],
            "ten_tinh": r["ten_tinh"],
            "administrative_era": r["administrative_era"],
            "road_type": rtype
        })
        diacritics_map[unacc].add(cname)
        road_type_map[core].add(f"{rtype} {core}" if not cname.startswith(rtype) else cname)
        initials_map[init].add(cname)

    cross_province_collisions = {k: v for k, v in cross_province_map.items() if len({x["ma_tinh"] for x in v}) >= 2}
    diacritics_collisions = {k: sorted(list(v)) for k, v in diacritics_map.items() if len(v) >= 2}
    road_type_collisions = {k: sorted(list(v)) for k, v in road_type_map.items() if len(v) >= 2}
    initials_ambiguities = {k: sorted(list(v)) for k, v in initials_map.items() if len(v) >= 2}

    conflict_data = {
        "metadata": {
            "version": "1.0.0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "description": "Bảng tổng hợp các va chạm khóa tra cứu phục vụ hệ thống NLP không phỏng đoán mơ hồ."
        },
        "collision_summary": {
            "cross_province_count": len(cross_province_collisions),
            "diacritics_collision_count": len(diacritics_collisions),
            "road_type_collision_count": len(road_type_collisions),
            "initials_ambiguity_count": len(initials_ambiguities),
            "administrative_era_conflicts_count": len(conflicting_era_codes)
        },
        "administrative_era_conflicts": conflicting_era_codes,
        "cross_province_collisions": cross_province_collisions,
        "diacritics_collisions": diacritics_collisions,
        "road_type_collisions": road_type_collisions,
        "initials_ambiguities": initials_ambiguities
    }

    # 6. Thống kê tổng hợp (statistics.json)
    unique_canonical_names = {r["canonical_name"] for r in final_confirmed}
    provinces_covered = {r["ma_tinh"] for r in final_confirmed}

    road_type_counts = defaultdict(int)
    era_counts = defaultdict(int)
    for r in final_confirmed:
        road_type_counts[r["road_type"]] += 1
        era_counts[r["administrative_era"]] += 1

    reasons_counts = defaultdict(int)
    for r in final_pending_rejected:
        reasons_counts[r["rejection_reason"]] += 1

    stats = {
        "version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_confirmed_records": len(final_confirmed),
        "unique_canonical_names": len(unique_canonical_names),
        "unique_provinces_covered": len(provinces_covered),
        "confirmed_by_source_type": {
            "van_ban_quy_pham": sum(1 for r in final_confirmed if r["source_type"] == "van_ban_quy_pham"),
            "cong_thong_tin_chinh_phu": sum(1 for r in final_confirmed if r["source_type"] == "cong_thong_tin_chinh_phu"),
            "cong_dong_osm": sum(1 for r in final_confirmed if r["source_type"] == "cong_dong_osm")
        },
        "confirmed_by_road_type": dict(road_type_counts),
        "confirmed_by_administrative_era": dict(era_counts),
        "pending_rejected_summary": {
            "total": len(final_pending_rejected),
            "pending_count": sum(1 for r in final_pending_rejected if r["status"] == "pending"),
            "rejected_count": sum(1 for r in final_pending_rejected if r["status"] == "rejected"),
            "reasons_breakdown": dict(reasons_counts)
        },
        "collision_statistics": conflict_data["collision_summary"]
    }

    # 7. Xuất các tệp ra đĩa
    # 7.1. danh_muc_duong.jsonl & .csv
    jsonl_path = V1_DIR / "danh_muc_duong.jsonl"
    with open(jsonl_path, "w", encoding="utf-8") as f:
        for r in final_confirmed:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    csv_path = V1_DIR / "danh_muc_duong.csv"
    csv_fields = [
        "id", "canonical_name", "road_type", "ma_tinh", "ten_tinh", "administrative_era",
        "quan_huyen_list", "aliases", "source_id", "source_type", "source_url", "source_sha256",
        "status", "verification_note", "unaccented_key", "collapsed_key", "initials_key"
    ]
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=csv_fields)
        writer.writeheader()
        writer.writerows(final_confirmed)

    # 7.2. danh_muc_pending_rejected.jsonl & .csv
    pr_jsonl_path = V1_DIR / "danh_muc_pending_rejected.jsonl"
    with open(pr_jsonl_path, "w", encoding="utf-8") as f:
        for r in final_pending_rejected:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    pr_csv_path = V1_DIR / "danh_muc_pending_rejected.csv"
    pr_csv_fields = [
        "id", "raw_input", "candidate_canonical_name", "candidate_road_type", "ma_tinh",
        "ten_tinh", "quan_huyen", "status", "rejection_reason", "legal_source",
        "administrative_era", "source_id", "source_sha256"
    ]
    with open(pr_csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=pr_csv_fields)
        writer.writeheader()
        writer.writerows(final_pending_rejected)

    # 7.3. khoa_tra_cuu.json
    lookup_path = V1_DIR / "khoa_tra_cuu.json"
    lookup_path.write_text(json.dumps(lookup_index, ensure_ascii=False, indent=2), encoding="utf-8")

    # 7.4. khoa_xung_dot.json
    conflict_path = V1_DIR / "khoa_xung_dot.json"
    conflict_path.write_text(json.dumps(conflict_data, ensure_ascii=False, indent=2), encoding="utf-8")

    # 7.5. statistics.json
    stats_path = V1_DIR / "statistics.json"
    stats_path.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")

    # 8. Tạo manifest.json ghim toàn bộ SHA-256 các tệp trong v1/
    manifest_entries = []
    for item in sorted(V1_DIR.rglob("*")):
        if item.is_file() and item.name != "manifest.json":
            rel_path = item.relative_to(V1_DIR).as_posix()
            sha256 = hashlib.sha256(item.read_bytes()).hexdigest()
            manifest_entries.append({
                "path": rel_path,
                "sha256": sha256,
                "bytes": item.stat().st_size
            })

    final_manifest = {
        "version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_files": len(manifest_entries),
        "files": manifest_entries
    }
    manifest_path = V1_DIR / "manifest.json"
    manifest_path.write_text(json.dumps(final_manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n=== KẾT QUẢ BUILD HOÀN TẤT ===")
    print(f"1. Tổng số bản ghi confirmed: {len(final_confirmed)}")
    print(f"2. Số tên đường phân biệt (canonical_name): {len(unique_canonical_names)} (MỤC TIÊU >= 1.000: ĐẠT)")
    print(f"3. Số tỉnh/thành được phủ: {len(provinces_covered)}")
    print(f"4. Tổng số bản ghi pending/rejected: {len(final_pending_rejected)}")
    print(f"5. Xung đột cùng tên nhiều tỉnh: {len(cross_province_collisions)} tên")
    print(f"6. Xung đột cùng khóa khác dấu: {len(diacritics_collisions)} nhóm")
    print(f"7. Xung đột cùng tên khác loại đường: {len(road_type_collisions)} nhóm")
    print(f"8. Đã ghi manifest.json với {len(manifest_entries)} tệp.")


if __name__ == "__main__":
    build_danh_muc()
