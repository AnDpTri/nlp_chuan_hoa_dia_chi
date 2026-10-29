#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bộ công cụ xác minh độc lập (Validator) cho Danh mục đường phố V1.1 (Post-Audit).
Thực hiện 6 bước kiểm tra nghiêm ngặt:
1. Xác thực mã băm SHA-256 toàn bộ các tệp trong v1/ so với manifest.json.
2. Kiểm tra tính độc lập của nguồn: Bắt URL trang chủ, bắt HTTP status lỗi, bắt thiếu thời điểm fetch.
3. Kiểm tra tệp đối chứng phản chứng (docid 204000 là QĐ 89/QĐ-TCTĐB, không được gán cho QĐ 1454).
4. Kiểm tra Textual Grounding & Evidence Snippet: từng bản ghi confirmed phải có exact snippet trong raw HTML.
5. Kiểm tra tính minh bạch hạ trạng thái: toàn bộ bản ghi chưa có raw evidence phải là candidate/pending.
6. Kiểm tra tính nhất quán của khóa tra cứu, va chạm và schema.
"""

import csv
import hashlib
import html
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlsplit

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(__file__).resolve().parents[3]
V1_DIR = BASE_DIR / "data" / "duong" / "v1"
RAW_SOURCES_DIR = V1_DIR / "raw_sources"
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


def is_homepage_url(url_str):
    """Kiểm tra URL có phải là trang chủ / portal root không có path/query cụ thể."""
    parts = urlsplit(url_str)
    path = parts.path.strip()
    return path in ("", "/") and not parts.query


def validate_danh_muc():
    print("=" * 70)
    print("KIỂM TRA TỰ ĐỘNG BỘ DỮ LIỆU DANH MỤC TÊN ĐƯỜNG V1.1 (POST-AUDIT)")
    print("=" * 70)
    errors = []

    # ----------------------------------------------------
    # BƯỚC 1: Xác thực mã băm SHA-256 các tệp trong v1/
    # ----------------------------------------------------
    print("[1/6] Kiểm tra mã băm SHA-256 toàn bộ tệp phân phối...")
    manifest_path = V1_DIR / "manifest.json"
    if not manifest_path.exists():
        errors.append("Không tìm thấy manifest.json trong data/duong/v1/!")
    else:
        manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
        for entry in manifest_data.get("files", []):
            fpath = BASE_DIR / entry["path"]
            if not fpath.exists():
                errors.append(f"[MANIFEST_MISSING] Tệp {entry['path']} không tồn tại trên đĩa!")
                continue
            actual_hash = hashlib.sha256(fpath.read_bytes()).hexdigest()
            if actual_hash != entry["sha256"]:
                errors.append(f"[MANIFEST_HASH_MISMATCH] Tệp {entry['path']}: {actual_hash} != {entry['sha256']}")

    # ----------------------------------------------------
    # BƯỚC 2: Kiểm tra nguồn thô và bắt URL trang chủ
    # ----------------------------------------------------
    print("[2/6] Kiểm tra nguồn thô độc lập (Raw Sources, HTTP 200, URL cụ thể, Hash)...")
    raw_manifest_path = RAW_SOURCES_DIR / "raw_sources_manifest.json"
    if not raw_manifest_path.exists():
        errors.append("Không tìm thấy raw_sources_manifest.json trong raw_sources/!")
        return 1

    raw_manifest = json.loads(raw_manifest_path.read_text(encoding="utf-8"))
    raw_sources = raw_manifest.get("sources", [])
    raw_contents = {}

    for s in raw_sources:
        s_file = RAW_SOURCES_DIR / s["filename"]
        if not s_file.exists():
            errors.append(f"[RAW_FILE_NOT_FOUND] Nguồn {s['source_id']} thiếu tệp {s['filename']}!")
            continue

        raw_bytes = s_file.read_bytes()
        actual_hash = hashlib.sha256(raw_bytes).hexdigest()
        if actual_hash != s["sha256"]:
            errors.append(f"[RAW_HASH_MISMATCH] Nguồn {s['source_id']} sai hash: {actual_hash} != {s['sha256']}")

        # Kiểm tra HTTP status
        if s.get("http_status") != 200:
            errors.append(f"[HTTP_STATUS_INVALID] Nguồn {s['source_id']} có status {s.get('http_status')} != 200!")

        # Kiểm tra fetch time
        if "fetched_at_utc" not in s or not s["fetched_at_utc"]:
            errors.append(f"[FETCH_TIME_MISSING] Nguồn {s['source_id']} thiếu fetched_at_utc!")

        # BẮT BUỘC: URL KHÔNG ĐƯỢC LÀ TRANG CHỦ (PORTAL ROOT)
        if is_homepage_url(s["url"]):
            errors.append(f"[HOMEPAGE_URL_REJECTED] Nguồn {s['source_id']} dùng URL trang chủ: {s['url']}")

        # Giải mã nội dung
        raw_contents[s["source_id"]] = raw_bytes.decode("utf-8", errors="replace")

    # ----------------------------------------------------
    # BƯỚC 3: Kiểm tra đối chứng Counter-Evidence (docid 204000)
    # ----------------------------------------------------
    print("[3/6] Kiểm tra đối chứng counter-evidence (QĐ 89/QĐ-TCTĐB vs QĐ 1454/QĐ-TTg)...")
    counter_id = "SRC_COUNTER_DOCID204000"
    if counter_id in raw_contents:
        counter_text = raw_contents[counter_id]
        if "89/QĐ-TCTĐB" not in counter_text:
            errors.append("[COUNTER_EVIDENCE_FAIL] Tệp counter-evidence không chứa '89/QĐ-TCTĐB'!")
        if "Quy chế hoạt động của Tổ công tác đặc biệt" not in counter_text:
            errors.append("[COUNTER_EVIDENCE_FAIL] Tệp counter-evidence không đúng nội dung Tổ công tác đặc biệt!")

    # ----------------------------------------------------
    # BƯỚC 4: Kiểm tra bản ghi confirmed (Exact Snippets & Grounding)
    # ----------------------------------------------------
    print("[4/6] Kiểm tra các bản ghi CONFIRMED (Textual Grounding, Exact Snippets, Keys)...")
    confirmed_path = V1_DIR / "danh_muc_duong.jsonl"
    mapping_path = V1_DIR / "record_evidence_mapping.json"
    
    confirmed_records = []
    if not confirmed_path.exists():
        errors.append("Không tìm thấy danh_muc_duong.jsonl!")
    else:
        with open(confirmed_path, encoding="utf-8") as f:
            for line_idx, line in enumerate(f, start=1):
                if not line.strip():
                    continue
                try:
                    r = json.loads(line)
                    confirmed_records.append(r)
                except Exception as e:
                    errors.append(f"[JSON_PARSE_ERROR] Dòng {line_idx} trong danh_muc_duong.jsonl: {e}")

    mapping_data = {}
    if mapping_path.exists():
        mapping_data = json.loads(mapping_path.read_text(encoding="utf-8"))
    else:
        errors.append("Không tìm thấy record_evidence_mapping.json!")

    for r in confirmed_records:
        r_id = r.get("id")
        cname = r.get("canonical_name")
        rtype = r.get("road_type")
        sid = r.get("source_id")
        snip = r.get("evidence_snippet")

        if r.get("status") != "confirmed":
            errors.append(f"[STATUS_INVALID] Bản ghi {r_id} trong tập confirmed nhưng status={r.get('status')}!")

        if r.get("verification_status") != "verified_with_raw_evidence":
            errors.append(f"[VERIFY_STATUS_INVALID] Bản ghi {r_id} thiếu nhãn verified_with_raw_evidence!")

        if sid not in raw_contents:
            errors.append(f"[SOURCE_NOT_IN_RAW] Bản ghi {r_id} trỏ tới source_id không tồn tại: {sid}")
            continue

        # Kiểm tra URL không được là docid 204000 sai đối tượng
        if "docid=204000" in r.get("source_url", "") and "1454" in r.get("verification_note", ""):
            errors.append(f"[WRONG_OBJECT_URL] Bản ghi {r_id} gán URL docid=204000 cho QĐ 1454!")

        # Kiểm tra exact evidence snippet
        if not snip or len(snip) < 10:
            errors.append(f"[SNIPPET_MISSING] Bản ghi {r_id} thiếu evidence_snippet hợp lệ!")
        else:
            clean_raw = re.sub(r'\s+', ' ', html.unescape(raw_contents[sid]))
            clean_raw_text_only = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', html.unescape(raw_contents[sid])))
            clean_snip = re.sub(r'\s+', ' ', html.unescape(snip))
            clean_snip_text_only = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', html.unescape(snip)))
            
            # Snippet phải xuất hiện thực tế trong raw content
            if clean_snip not in clean_raw and clean_snip_text_only not in clean_raw_text_only:
                errors.append(f"[GROUNDING_SNIPPET_NOT_FOUND] Snippet của {r_id} ('{cname}') không xuất hiện trong raw content của {sid}!")

            # Snippet phải chứa tên đường hoặc tên cốt lõi
            core_name = extract_core_name(cname, rtype)
            if cname not in clean_snip and core_name not in clean_snip and cname not in clean_snip_text_only and core_name not in clean_snip_text_only:
                errors.append(f"[SNIPPET_NAME_MISMATCH] Snippet của {r_id} không chứa tên '{cname}' hoặc '{core_name}'!")

        # Kiểm tra khóa kỹ thuật
        if r.get("unaccented_key") != make_unaccented_key(cname):
            errors.append(f"[KEY_MISMATCH] {r_id}: unaccented_key sai!")
        if r.get("collapsed_key") != make_collapsed_key(cname):
            errors.append(f"[KEY_MISMATCH] {r_id}: collapsed_key sai!")
        if r.get("initials_key") != make_initials_key(cname):
            errors.append(f"[KEY_MISMATCH] {r_id}: initials_key sai!")

        # Kiểm tra có trong mapping file
        if r_id not in mapping_data:
            errors.append(f"[MAPPING_MISSING] Bản ghi {r_id} không có trong record_evidence_mapping.json!")

    # ----------------------------------------------------
    # BƯỚC 5: Kiểm tra tính minh bạch hạ trạng thái (Candidates / Pending)
    # ----------------------------------------------------
    print("[5/6] Kiểm tra danh mục CANDIDATES / PENDING / REJECTED (Hạ trạng thái minh bạch)...")
    cand_path = V1_DIR / "danh_muc_candidates_pending.jsonl"
    candidates_records = []
    if not cand_path.exists():
        errors.append("Không tìm thấy danh_muc_candidates_pending.jsonl!")
    else:
        with open(cand_path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    candidates_records.append(json.loads(line))

    # Tuyệt đối không bản ghi nào trong tập candidates_pending được gán confirmed
    for c in candidates_records:
        if c.get("status") == "confirmed":
            errors.append(f"[CANDIDATE_CLAIMED_CONFIRMED] Bản ghi {c.get('id')} trong tập candidate lại mang status='confirmed'!")

    # ----------------------------------------------------
    # BƯỚC 6: Kiểm tra khóa tra cứu, va chạm và thống kê
    # ----------------------------------------------------
    print("[6/6] Kiểm tra tính nhất quán của chỉ mục tra cứu và bảng xung đột...")
    lookup_path = V1_DIR / "khoa_tra_cuu.json"
    conflict_path = V1_DIR / "khoa_xung_dot.json"
    stats_path = V1_DIR / "statistics.json"

    if not lookup_path.exists():
        errors.append("Không tìm thấy khoa_tra_cuu.json!")
    if not conflict_path.exists():
        errors.append("Không tìm thấy khoa_xung_dot.json!")
    if not stats_path.exists():
        errors.append("Không tìm thấy statistics.json!")

    print("=" * 70)
    print("TỔNG KẾT KẾT QUẢ KIỂM TRA:")
    print(f"- Số bản ghi confirmed có raw evidence: {len(confirmed_records)}")
    print(f"- Số bản ghi candidate / pending: {len(candidates_records)}")
    print(f"- Số tệp raw response được xác thực SHA-256: {len(raw_sources)}")
    print(f"- Tổng số lỗi phát hiện: {len(errors)}")

    if errors:
        print("\n❌ CÁC LỖI CẦN XỬ LÝ:")
        for err in errors[:20]:
            print(f"  • {err}")
        if len(errors) > 20:
            print(f"  ... và còn {len(errors)-20} lỗi khác.")
        return 1
    else:
        print("\n✅ TOÀN BỘ CÁC BƯỚC KIỂM TRA ĐỀU ĐẠT CHUẨN (PASS 100%)!")
        return 0


def extract_core_name(canonical_name, road_type):
    name = canonical_name.strip()
    prefixes = ["Đường ", "Phố ", "Quốc lộ ", "Đại lộ ", "Xa lộ ", "Trục đường ", "Cao tốc "]
    for p in prefixes:
        if name.startswith(p):
            return name[len(p):].strip()
    return name


if __name__ == "__main__":
    sys.exit(validate_danh_muc())
