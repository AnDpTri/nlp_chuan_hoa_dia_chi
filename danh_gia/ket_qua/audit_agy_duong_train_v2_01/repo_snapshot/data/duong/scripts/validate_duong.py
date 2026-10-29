#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Công cụ kiểm tra tự động và độc lập (Validator) cho bộ dữ liệu data/duong/v1/.
Kiểm tra:
1. Tính toàn vẹn băm SHA-256 theo manifest.json và sources_manifest.json.
2. Kiểm chứng chứng thực văn bản (Textual Grounding): Tên đường PHẢI xuất hiện thực tế trong tệp nguồn.
3. Tính chuẩn tắc của mã tỉnh, tên tỉnh và mốc thời kỳ hành chính (hien_hanh, moi_2025, cu_2024).
4. Tính toàn vẹn của các khóa kỹ thuật (unaccented_key, collapsed_key, initials_key).
5. Tính nhất quán giữa tệp JSONL và CSV.
6. Tính chính xác của bảng tra cứu xung đột (khoa_xung_dot.json).
Trả về mã thoát 0 khi PASS toàn bộ; mã thoát 1 khi có lỗi.
"""

import csv
import hashlib
import json
import re
import sys
from collections import defaultdict
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


def validate_danh_muc():
    print("=" * 70)
    print("KIỂM TRA TỰ ĐỘNG BỘ DỮ LIỆU DANH MỤC TÊN ĐƯỜNG V1")
    print("=" * 70)

    errors = []
    warnings = []

    # 1. Kiểm tra cấu trúc tệp bắt buộc
    required_files = [
        "danh_muc_duong.jsonl",
        "danh_muc_duong.csv",
        "danh_muc_pending_rejected.jsonl",
        "danh_muc_pending_rejected.csv",
        "khoa_tra_cuu.json",
        "khoa_xung_dot.json",
        "schema.json",
        "statistics.json",
        "manifest.json",
        "sources/sources_manifest.json"
    ]
    for rf in required_files:
        p = V1_DIR / rf
        if not p.exists():
            errors.append(f"[THIEU_TEP] Tệp bắt buộc không tồn tại: {rf}")

    if errors:
        for e in errors:
            print(f"LỖI: {e}")
        return 1

    # 2. Kiểm tra mã băm SHA-256 từ manifest.json
    print("[1/6] Kiểm tra mã băm SHA-256 toàn bộ tệp...")
    manifest_data = json.loads((V1_DIR / "manifest.json").read_text(encoding="utf-8"))
    for fentry in manifest_data["files"]:
        fpath = V1_DIR / fentry["path"]
        if not fpath.exists():
            errors.append(f"[MANIFEST_NOT_FOUND] Tệp ghi trong manifest không tồn tại: {fentry['path']}")
            continue
        calc_sha = hashlib.sha256(fpath.read_bytes()).hexdigest()
        if calc_sha != fentry["sha256"]:
            errors.append(f"[MANIFEST_HASH_MISMATCH] Tệp {fentry['path']} có mã băm sai lệch! (calc={calc_sha} vs exp={fentry['sha256']})")

    # 3. Kiểm tra sources_manifest.json
    print("[2/6] Kiểm tra nguồn và mã băm chứng thực...")
    src_manifest = json.loads((SOURCES_DIR / "sources_manifest.json").read_text(encoding="utf-8"))
    source_contents = {}
    source_hashes = {}
    for s in src_manifest["sources"]:
        sfpath = SOURCES_DIR / s["filename"]
        if not sfpath.exists():
            errors.append(f"[SOURCE_NOT_FOUND] Tệp nguồn không tồn tại: {s['filename']}")
            continue
        content = sfpath.read_text(encoding="utf-8")
        calc_sha = hashlib.sha256(sfpath.read_bytes()).hexdigest()
        if calc_sha != s["sha256"]:
            errors.append(f"[SOURCE_HASH_MISMATCH] Nguồn {s['filename']} có hash sai lệch!")
        source_contents[s["filename"]] = content
        source_hashes[s["filename"]] = s["sha256"]

    # 4. Nạp danh mục hành chính sạch
    print("[3/6] Nạp danh mục hành chính đối soát...")
    with open(CLEAN_DIR / "moi_tinh.csv", encoding="utf-8") as f:
        moi_tinh = {r["ma_tinh"]: r["ten_tinh"] for r in csv.DictReader(f)}
    with open(CLEAN_DIR / "cu_tinh.csv", encoding="utf-8") as f:
        cu_tinh = {r["ma_tinh"]: r["ten_tinh"] for r in csv.DictReader(f)}

    # 5. Kiểm tra từng bản ghi confirmed
    print("[4/6] Kiểm tra bản ghi confirmed (schema, grounding, keys, admin era)...")
    confirmed_records = []
    with open(V1_DIR / "danh_muc_duong.jsonl", encoding="utf-8") as f:
        for line_num, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception as ex:
                errors.append(f"[JSON_PARSE_ERROR] Dòng {line_num} trong danh_muc_duong.jsonl lỗi cú pháp: {ex}")
                continue
            confirmed_records.append(rec)

    # Đọc CSV confirmed để kiểm tra độ khớp
    with open(V1_DIR / "danh_muc_duong.csv", encoding="utf-8") as f:
        confirmed_csv = list(csv.DictReader(f))

    if len(confirmed_records) != len(confirmed_csv):
        errors.append(f"[CSV_COUNT_MISMATCH] Số dòng JSONL ({len(confirmed_records)}) không khớp CSV ({len(confirmed_csv)})!")

    seen_ids = set()
    canonical_names = set()
    provinces = set()

    for idx, r in enumerate(confirmed_records, start=1):
        rid = r.get("id")
        cname = r.get("canonical_name")
        rtype = r.get("road_type")
        mt = r.get("ma_tinh")
        tt = r.get("ten_tinh")
        era = r.get("administrative_era")
        sid = r.get("source_id")
        ssha = r.get("source_sha256")
        surl = r.get("source_url")
        status = r.get("status")
        unacc = r.get("unaccented_key")
        colla = r.get("collapsed_key")
        init = r.get("initials_key")

        # Check ID
        if not rid or not re.match(r"^STR_\d{5}$", rid):
            errors.append(f"[INVALID_ID] Bản ghi dòng {idx} có id không hợp lệ: {rid}")
        if rid in seen_ids:
            errors.append(f"[DUPLICATE_ID] Bản ghi trùng ID: {rid}")
        seen_ids.add(rid)

        # Check status
        if status != "confirmed":
            errors.append(f"[INVALID_STATUS] Bản ghi {rid} có status khác confirmed: {status}")

        # Check canonical_name & road_type
        if not cname:
            errors.append(f"[MISSING_NAME] Bản ghi {rid} thiếu canonical_name")
        canonical_names.add(cname)

        if rtype not in ["Đường", "Phố", "Quốc lộ", "Đại lộ", "Xa lộ", "Trục đường", "Tỉnh lộ"]:
            errors.append(f"[INVALID_ROAD_TYPE] Bản ghi {rid} có loại đường lạ: {rtype}")

        # Check source grounding
        if sid not in source_contents:
            errors.append(f"[SOURCE_NOT_FOUND] Bản ghi {rid} trỏ đến nguồn không tồn tại: {sid}")
        else:
            # Hash matching
            if ssha != source_hashes[sid]:
                errors.append(f"[SOURCE_HASH_MISMATCH] Bản ghi {rid} ghi sai SHA-256 của {sid}")
            # Literal string grounding
            if cname and cname not in source_contents[sid]:
                errors.append(f"[UNSUPPORTED_NAME] Tên đường '{cname}' (id={rid}) KHÔNG xuất hiện trong nội dung {sid}!")

        # Check source url
        if not surl or not surl.startswith("http"):
            errors.append(f"[INVALID_URL] Bản ghi {rid} thiếu hoặc sai source_url: {surl}")

        # Check administrative era & province
        if not mt or not re.match(r"^\d{2}$", mt):
            errors.append(f"[INVALID_MA_TINH] Bản ghi {rid} có mã tỉnh không chuẩn: {mt}")
        provinces.add(mt)

        if era == "hien_hanh":
            if mt not in moi_tinh or mt not in cu_tinh or moi_tinh[mt] != cu_tinh[mt]:
                errors.append(f"[ERA_MISMATCH] Bản ghi {rid} ghi era 'hien_hanh' nhưng mã {mt} bị lệch tên giữa 2 kỳ!")
            elif tt != moi_tinh[mt]:
                errors.append(f"[TEN_TINH_MISMATCH] Bản ghi {rid} có ten_tinh '{tt}' khác danh mục '{moi_tinh[mt]}'")
        elif era == "moi_2025":
            if mt not in moi_tinh:
                errors.append(f"[ERA_MISMATCH] Bản ghi {rid} ghi era 'moi_2025' nhưng mã {mt} không có trong moi_tinh.csv")
            elif tt != moi_tinh[mt]:
                errors.append(f"[TEN_TINH_MISMATCH] Bản ghi {rid} có ten_tinh '{tt}' khác moi_tinh '{moi_tinh.get(mt)}'")
        elif era == "cu_2024":
            if mt not in cu_tinh:
                errors.append(f"[ERA_MISMATCH] Bản ghi {rid} ghi era 'cu_2024' nhưng mã {mt} không có trong cu_tinh.csv")
            elif tt != cu_tinh[mt]:
                errors.append(f"[TEN_TINH_MISMATCH] Bản ghi {rid} có ten_tinh '{tt}' khác cu_tinh '{cu_tinh.get(mt)}'")
        else:
            errors.append(f"[INVALID_ERA] Bản ghi {rid} có era không hợp lệ: {era}")

        # Check technical lookup keys
        exp_unacc = make_unaccented_key(cname)
        exp_colla = make_collapsed_key(cname)
        exp_init = make_initials_key(cname)

        if unacc != exp_unacc:
            errors.append(f"[KEY_MISMATCH] Bản ghi {rid} unaccented_key sai ({unacc} vs {exp_unacc})")
        if colla != exp_colla:
            errors.append(f"[KEY_MISMATCH] Bản ghi {rid} collapsed_key sai ({colla} vs {exp_colla})")
        if init != exp_init:
            errors.append(f"[KEY_MISMATCH] Bản ghi {rid} initials_key sai ({init} vs {exp_init})")

    # 6. Kiểm tra pending & rejected
    print("[5/6] Kiểm tra danh mục pending / rejected...")
    pr_records = []
    with open(V1_DIR / "danh_muc_pending_rejected.jsonl", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                pr_records.append(json.loads(line))

    with open(V1_DIR / "danh_muc_pending_rejected.csv", encoding="utf-8") as f:
        pr_csv = list(csv.DictReader(f))

    if len(pr_records) != len(pr_csv):
        errors.append(f"[PR_COUNT_MISMATCH] Số dòng PR JSONL ({len(pr_records)}) không khớp CSV ({len(pr_csv)})!")

    for r in pr_records:
        if r.get("status") not in ["pending", "rejected"]:
            errors.append(f"[INVALID_PR_STATUS] Bản ghi PR {r.get('id')} có status không hợp lệ: {r.get('status')}")
        if not r.get("rejection_reason"):
            errors.append(f"[MISSING_REJECTION_REASON] Bản ghi PR {r.get('id')} thiếu lý do thẩm định!")

    # 7. Kiểm tra khóa tra cứu và bảng xung đột
    print("[6/6] Kiểm tra tính nhất quán của khóa tra cứu và bảng xung đột...")
    lookup_data = json.loads((V1_DIR / "khoa_tra_cuu.json").read_text(encoding="utf-8"))
    for rec in confirmed_records[:100]:
        rid = rec["id"]
        unacc = rec["unaccented_key"]
        colla = rec["collapsed_key"]
        init = rec["initials_key"]
        if rid not in lookup_data["by_unaccented_key"].get(unacc, []):
            errors.append(f"[LOOKUP_MISSING] ID {rid} không có trong by_unaccented_key['{unacc}']")
        if rid not in lookup_data["by_collapsed_key"].get(colla, []):
            errors.append(f"[LOOKUP_MISSING] ID {rid} không có trong by_collapsed_key['{colla}']")
        if rid not in lookup_data["by_initials_key"].get(init, []):
            errors.append(f"[LOOKUP_MISSING] ID {rid} không có trong by_initials_key['{init}']")

    conflict_data = json.loads((V1_DIR / "khoa_xung_dot.json").read_text(encoding="utf-8"))
    cross_collisions = conflict_data.get("cross_province_collisions", {})
    for name, occurrences in list(cross_collisions.items())[:30]:
        provs = {x["ma_tinh"] for x in occurrences}
        if len(provs) < 2:
            errors.append(f"[INVALID_CONFLICT] Tên '{name}' ghi trong cross_province_collisions nhưng chỉ có 1 tỉnh ({provs})!")

    print("=" * 70)
    print("TỔNG KẾT KẾT QUẢ KIỂM TRA:")
    print(f"- Số bản ghi confirmed: {len(confirmed_records)}")
    print(f"- Số tên đường phân biệt (canonical_name): {len(canonical_names)}")
    print(f"- Số tỉnh/thành được phủ: {len(provinces)}")
    print(f"- Số bản ghi pending/rejected: {len(pr_records)}")
    print(f"- Tổng số lỗi phát hiện: {len(errors)}")

    if len(canonical_names) < 1000:
        errors.append(f"[TARGET_NOT_MET] Số tên đường phân biệt ({len(canonical_names)}) chưa đạt mốc 1.000!")

    if errors:
        print("\nCÁC LỖI CẦN XỬ LÝ:")
        for e in errors[:20]:
            print(f"  ❌ {e}")
        if len(errors) > 20:
            print(f"  ... và còn {len(errors) - 20} lỗi khác.")
        return 1
    else:
        print("\n✅ TOÀN BỘ CÁC BƯỚC KIỂM TRA ĐỀU ĐẠT CHUẨN (PASS 100%)!")
        return 0


if __name__ == "__main__":
    sys.exit(validate_danh_muc())
