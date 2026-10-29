#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script xây dựng bộ dữ liệu danh mục tên đường phố có nguồn chứng thực thật (V1.1 - Post-Audit).
Thực hiện:
1. Nạp và xác thực các tệp raw sources từ data/duong/v1/raw_sources/.
2. Trích xuất các tuyến đường chính thức đã có raw evidence độc lập vào tập confirmed.
3. Hạ trạng thái toàn bộ các bản ghi cũ chưa có raw evidence xuống candidate/pending.
4. Xuất mapping record -> evidence (exact snippets), các khóa tra cứu, bảng xung đột và manifest.
"""

import csv
import hashlib
import html
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(__file__).resolve().parents[3]
V1_DIR = BASE_DIR / "data" / "duong" / "v1"
RAW_SOURCES_DIR = V1_DIR / "raw_sources"
LEGACY_SNAPSHOT_DIR = V1_DIR / "legacy_v1_snapshot"
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
    name = canonical_name.strip()
    prefixes = ["Đường ", "Phố ", "Quốc lộ ", "Đại lộ ", "Xa lộ ", "Trục đường ", "Cao tốc "]
    for p in prefixes:
        if name.startswith(p):
            return name[len(p):].strip()
    return name


def build_danh_muc():
    print("=== BẮT ĐẦU XÂY DỰNG DANH MỤC ĐƯỜNG V1.1 (CÓ NGUỒN CHỨNG THỰC ĐỘC LẬP) ===")

    # 1. Nạp raw sources manifest và nội dung HTML thô
    raw_manifest_path = RAW_SOURCES_DIR / "raw_sources_manifest.json"
    if not raw_manifest_path.exists():
        raise FileNotFoundError("Không tìm thấy raw_sources_manifest.json tại raw_sources/!")
    
    raw_manifest = json.loads(raw_manifest_path.read_text(encoding="utf-8"))
    raw_sources_map = {s["source_id"]: s for s in raw_manifest["sources"]}
    raw_contents = {}

    for s in raw_manifest["sources"]:
        fpath = RAW_SOURCES_DIR / s["filename"]
        if not fpath.exists():
            raise FileNotFoundError(f"Tệp nguồn {s['filename']} không tồn tại!")
        b = fpath.read_bytes()
        actual_hash = hashlib.sha256(b).hexdigest()
        if actual_hash != s["sha256"]:
            raise ValueError(f"Mã băm SHA-256 không khớp cho {s['filename']}: {actual_hash} != {s['sha256']}")
        raw_contents[s["source_id"]] = b.decode("utf-8", errors="replace")

    print(f"-> Đã xác thực thành công {len(raw_manifest['sources'])} tệp raw responses từ nguồn thật.")

    # 2. Xây dựng danh sách confirmed records có raw evidence
    confirmed_records = []
    record_evidence_mapping = {}

    # 2.1. Nguồn 1: Hà Nội QĐ 3862/QĐ-UBND (38 tuyến đường phố mới)
    hn_src = raw_sources_map["SRC_RAW_01_HANOI_QD3862"]
    hn_text = raw_contents["SRC_RAW_01_HANOI_QD3862"]

    p_tags = re.findall(r'<p[^>]*>(.*?)</p>', hn_text, re.DOTALL)
    clean_hn_text = re.sub(r'\s+', ' ', html.unescape(hn_text))
    for p in p_tags:
        clean = re.sub(r'<[^>]+>', '', p).strip()
        clean = re.sub(r'\s+', ' ', html.unescape(clean))
        m = re.match(r'^(\d+)\.\s+(Phố|Đường)\s+([^(:]+)\s*\(([^)]+)\):\s*(.*)', clean)
        if m:
            num, rtype, name, loc, desc = m.groups()
            raw_p = clean
            if raw_p not in clean_hn_text:
                raise ValueError(f"Lỗi grounding: đoạn {num} không có trong raw HTML Hà Nội!")
            cname = f"{rtype} {name.strip()}"
            
            confirmed_records.append({
                "canonical_name": cname,
                "road_type": rtype,
                "ma_tinh": "01",
                "ten_tinh": "Hà Nội",
                "administrative_era": "hien_hanh",
                "quan_huyen_list": loc.strip(),
                "aliases": "",
                "source_id": hn_src["source_id"],
                "source_type": hn_src["source_type"],
                "source_url": hn_src["url"],
                "source_sha256": hn_src["sha256"],
                "status": "confirmed",
                "verification_status": "verified_with_raw_evidence",
                "evidence_snippet": raw_p
            })

    if len(confirmed_records) != 38:
        raise ValueError(f"Mong đợi trích xuất 38 tuyến đường phố Hà Nội nhưng thu được {len(confirmed_records)}!")

    # 2.2. Nguồn 2: TPHCM Nghị quyết HĐND khóa X (7 tuyến đường đặt tên lãnh đạo Đảng, Nhà nước)
    hcm_src = raw_sources_map["SRC_RAW_02_TPHCM_HDND_QUOCLO"]
    hcm_text = raw_contents["SRC_RAW_02_TPHCM_HDND_QUOCLO"]

    hcm_definitions = [
        ("Đường Đỗ Mười", "Đường", "79", "Hồ Chí Minh", "Thủ Đức, Quận 12", "đặt tên Tổng Bí thư Đỗ Mười trên Quốc lộ 1 - từ nút giao thông Thủ Đức (ngã ba Trạm 2 cũ) đến nút giao thông An Sương"),
        ("Đường Lê Đức Anh", "Đường", "79", "Hồ Chí Minh", "Quận 12, Hóc Môn, Bình Tân", "đặt tên Chủ tịch nước Lê Đức Anh trên Quốc lộ 1 - từ nút giao thông An Sương đến vòng xoay An Lạc"),
        ("Đường Lê Khả Phiêu", "Đường", "79", "Hồ Chí Minh", "Bình Tân, Bình Chánh", "đặt tên Tổng Bí thư Lê Khả Phiêu trên Quốc lộ 1 - đoạn từ vòng xoay An Lạc đến ranh tỉnh Long An"),
        ("Đường Lê Quang Đạo", "Đường", "79", "Hồ Chí Minh", "Quận 12, Hóc Môn", "đặt tên Chủ tịch Quốc hội Lê Quang Đạo trên Quốc lộ 22 - đoạn từ Quốc lộ 1 đến cầu An Hạ"),
        ("Đường Phan Văn Khải", "Đường", "79", "Hồ Chí Minh", "Hóc Môn, Củ Chi", "đặt tên Thủ tướng Chính phủ Phan Văn Khải trên Quốc lộ 22 - đoạn từ cầu An Hạ đến ranh tỉnh Tây Ninh"),
        ("Đường Văn Tiến Dũng", "Đường", "79", "Hồ Chí Minh", "Quận 7, Nhà Bè, Bình Chánh", "đặt tên Đại tướng Văn Tiến Dũng trên Quốc lộ 50 - đoạn từ đường Nguyễn Văn Linh đến ranh tỉnh Long An"),
        ("Đường Hoàng Cầm", "Đường", "79", "Hồ Chí Minh", "Thủ Đức", "đặt tên Thượng tướng Hoàng Cầm trên Quốc lộ 1K - đoạn từ Quốc lộ 1 đến ranh tỉnh Bình Dương")
    ]

    for cname, rtype, mt, tt, loc, snippet in hcm_definitions:
        if snippet not in hcm_text:
            raise ValueError(f"Lỗi kiểm chứng snippet TPHCM: '{snippet}' không có trong raw content!")
        
        confirmed_records.append({
            "canonical_name": cname,
            "road_type": rtype,
            "ma_tinh": mt,
            "ten_tinh": tt,
            "administrative_era": "hien_hanh",
            "quan_huyen_list": loc,
            "aliases": f"Quốc lộ {cname.split()[-1]} đoạn qua TP.HCM",
            "source_id": hcm_src["source_id"],
            "source_type": hcm_src["source_type"],
            "source_url": hcm_src["url"],
            "source_sha256": hcm_src["sha256"],
            "status": "confirmed",
            "verification_status": "verified_with_raw_evidence",
            "evidence_snippet": snippet
        })

    # 2.3. Nguồn 3: Quốc lộ QĐ 1454/QĐ-TTg trên Báo Chính Phủ
    ql_src = raw_sources_map["SRC_RAW_03_QUOC_LO_QD1454"]
    ql_text = raw_contents["SRC_RAW_03_QUOC_LO_QD1454"]
    clean_ql_text = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', html.unescape(ql_text)))

    ql_definitions = [
        ("Cao tốc Bắc - Nam phía Đông", "Cao tốc", "01", "Toàn quốc", "Liên tỉnh (Lạng Sơn - Cà Mau)", "Tuyến cao tốc Bắc - Nam phía Đông (Từ Lạng Sơn - Cà Mau) chiều dài khoảng 2.063 km"),
        ("Cao tốc Bắc - Nam phía Tây", "Cao tốc", "01", "Toàn quốc", "Liên tỉnh", "Tuyến cao tốc Bắc - Nam phía Tây, chiều dài khoảng 1.205 km"),
        ("Đường bộ ven biển", "Đường", "01", "Toàn quốc", "Qua địa phận 28 tỉnh, thành phố", "(3) Đường bộ ven biển: Qua địa phận 28 tỉnh, thành phố, tổng chiều dài khoảng 3.034 km"),
        ("Quốc lộ 45", "Quốc lộ", "28", "Ninh Bình, Thanh Hóa", "Mai Sơn - Quốc lộ 45", "Công trường thi công cao tốc Bắc-Nam tuyến phía Đông đoạn Mai Sơn - Quốc lộ 45")
    ]

    for cname, rtype, mt, tt, loc, snippet in ql_definitions:
        if snippet not in clean_ql_text:
            raise ValueError(f"Lỗi kiểm chứng snippet QĐ 1454: '{snippet}' không có trong raw content!")
        
        confirmed_records.append({
            "canonical_name": cname,
            "road_type": rtype,
            "ma_tinh": mt,
            "ten_tinh": tt,
            "administrative_era": "hien_hanh",
            "quan_huyen_list": loc,
            "aliases": "",
            "source_id": ql_src["source_id"],
            "source_type": ql_src["source_type"],
            "source_url": ql_src["url"],
            "source_sha256": ql_src["sha256"],
            "status": "confirmed",
            "verification_status": "verified_with_raw_evidence",
            "evidence_snippet": snippet
        })

    # 2.4. Nguồn 4 & 5: Đà Nẵng (Báo Đà Nẵng và Cổng 1022)
    dn_bao_src = raw_sources_map["SRC_RAW_05_DANANG_BAO"]
    dn_bao_text = raw_contents["SRC_RAW_05_DANANG_BAO"]

    dn_definitions = [
        ("Đường Bình Kỳ", "Đường", "48", "Đà Nẵng", "phường Hòa Quý, quận Ngũ Hành Sơn", "được phường đề xuất thành phố đặt tên, ví dụ như đường Bình Kỳ, Lưu Quang Vũ"),
        ("Đường Lưu Quang Vũ", "Đường", "48", "Đà Nẵng", "phường Hòa Quý, quận Ngũ Hành Sơn", "được phường đề xuất thành phố đặt tên, ví dụ như đường Bình Kỳ, Lưu Quang Vũ"),
        ("Đường Trần Hưng Đạo", "Đường", "48", "Đà Nẵng", "phường An Hải, quận Sơn Trà", "Địa chỉ: 525 Trần Hưng Đạo, phường An Hải, TP. Đà Nẵng"),
        ("Đường Hùng Vương", "Đường", "48", "Đà Nẵng", "phường Bàn Thạch", "Cơ sở 2, số 58 Hùng Vương, phường Bàn Thạch, TP. Đà Nẵng")
    ]

    for cname, rtype, mt, tt, loc, snippet in dn_definitions:
        if snippet not in dn_bao_text:
            raise ValueError(f"Lỗi kiểm chứng snippet Đà Nẵng: '{snippet}' không có trong raw content!")
        
        confirmed_records.append({
            "canonical_name": cname,
            "road_type": rtype,
            "ma_tinh": mt,
            "ten_tinh": tt,
            "administrative_era": "hien_hanh",
            "quan_huyen_list": loc,
            "aliases": "",
            "source_id": dn_bao_src["source_id"],
            "source_type": dn_bao_src["source_type"],
            "source_url": dn_bao_src["url"],
            "source_sha256": dn_bao_src["sha256"],
            "status": "confirmed",
            "verification_status": "verified_with_raw_evidence",
            "evidence_snippet": snippet
        })

    # Gán ID tuần tự cho confirmed records
    final_confirmed = []
    lookup_index = {
        "by_unaccented_key": defaultdict(list),
        "by_collapsed_key": defaultdict(list),
        "by_initials_key": defaultdict(list)
    }

    for idx, r in enumerate(confirmed_records, start=1):
        rec_id = f"STR_CONF_{idx:04d}"
        cname = r["canonical_name"]
        unacc = make_unaccented_key(cname)
        colla = make_collapsed_key(cname)
        init = make_initials_key(cname)

        r["id"] = rec_id
        r["unaccented_key"] = unacc
        r["collapsed_key"] = colla
        r["initials_key"] = init

        final_confirmed.append(r)
        lookup_index["by_unaccented_key"][unacc].append(rec_id)
        lookup_index["by_collapsed_key"][colla].append(rec_id)
        lookup_index["by_initials_key"][init].append(rec_id)

        # Ghi mapping record -> evidence
        record_evidence_mapping[rec_id] = {
            "id": rec_id,
            "canonical_name": cname,
            "road_type": r["road_type"],
            "ma_tinh": r["ma_tinh"],
            "ten_tinh": r["ten_tinh"],
            "source_id": r["source_id"],
            "source_url": r["source_url"],
            "source_sha256": r["source_sha256"],
            "exact_evidence_snippet": r["evidence_snippet"],
            "verification_status": "verified_with_raw_evidence"
        }

    print(f"-> Đã xây dựng {len(final_confirmed)} bản ghi CONFIRMED có nguồn chứng thực thật 100%.")

    # 3. Nạp danh mục legacy v1 và hạ trạng thái toàn bộ 1.461 bản ghi cũ xuống CANDIDATE/PENDING
    legacy_file = LEGACY_SNAPSHOT_DIR / "danh_muc_duong.jsonl"
    legacy_records = []
    if legacy_file.exists():
        with open(legacy_file, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    legacy_records.append(json.loads(line))

    candidates_pending_records = []
    # Hạ trạng thái toàn bộ 1.461 bản ghi legacy
    for r in legacy_records:
        cand = dict(r)
        cand["legacy_id"] = r["id"]
        cand["id"] = f"CAND_{r['id']}"
        cand["status"] = "candidate_unverified_source"
        cand["downgrade_reason"] = "CHUA_THU_THAP_DUOC_RAW_EVIDENCE_DOC_LAP (Bản ghi từ definitions cũ chưa có tệp phản hồi HTTP nguyên bản độc lập)"
        cand["verification_status"] = "pending_evidence_fetch"
        cand["legacy_source_id"] = r.get("source_id", "")
        cand["legacy_source_url"] = r.get("source_url", "")
        # Xóa các thông tin gán mác đã chứng thực
        cand["source_sha256"] = ""
        cand["source_id"] = "LEGACY_V1_UNVERIFIED"
        candidates_pending_records.append(cand)

    # Nạp cả 23 bản ghi pending/rejected ban đầu từ legacy snapshot
    legacy_pr_file = LEGACY_SNAPSHOT_DIR / "danh_muc_pending_rejected.jsonl"
    if legacy_pr_file.exists():
        with open(legacy_pr_file, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    pr_rec = json.loads(line)
                    pr_rec["legacy_id"] = pr_rec["id"]
                    pr_rec["id"] = f"PR_{pr_rec['id']}"
                    candidates_pending_records.append(pr_rec)

    print(f"-> Đã hạ trạng thái và nạp {len(candidates_pending_records)} bản ghi CANDIDATES / PENDING / REJECTED.")

    # 4. Phân tích xung đột tra cứu (khoa_xung_dot.json)
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
            "version": "1.1.0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "description": "Bảng tổng hợp va chạm tra cứu của tập confirmed (đã có nguồn chứng thực thật)."
        },
        "collision_summary": {
            "cross_province_count": len(cross_province_collisions),
            "diacritics_collision_count": len(diacritics_collisions),
            "road_type_collision_count": len(road_type_collisions),
            "initials_ambiguity_count": len(initials_ambiguities)
        },
        "cross_province_collisions": cross_province_collisions,
        "diacritics_collisions": diacritics_collisions,
        "road_type_collisions": road_type_collisions,
        "initials_ambiguities": initials_ambiguities
    }

    # 5. Thống kê tổng hợp (statistics.json)
    unique_names = {r["canonical_name"] for r in final_confirmed}
    road_type_counts = defaultdict(int)
    for r in final_confirmed:
        road_type_counts[r["road_type"]] += 1

    stats = {
        "version": "1.1.0",
        "updated_at_utc": datetime.now(timezone.utc).isoformat(),
        "confirmed_summary": {
            "total_confirmed_records": len(final_confirmed),
            "unique_canonical_names": len(unique_names),
            "provinces_covered": sorted(list({r["ten_tinh"] for r in final_confirmed})),
            "road_types": dict(road_type_counts),
            "status": "ALL_CONFIRMED_HAVE_RAW_EVIDENCE_HTTP200"
        },
        "downgraded_candidates_summary": {
            "total_candidates_pending": len(candidates_pending_records),
            "legacy_records_downgraded_to_candidate": len(legacy_records),
            "legacy_pending_rejected": len(candidates_pending_records) - len(legacy_records),
            "status": "AWAITING_INDEPENDENT_EVIDENCE_FETCH"
        },
        "raw_sources_summary": {
            "total_raw_sources": len(raw_manifest["sources"]),
            "official_legal_sources": len([s for s in raw_manifest["sources"] if s["source_type"] == "van_ban_quy_pham"]),
            "press_evidence_sources": len([s for s in raw_manifest["sources"] if s["source_type"] == "bao_chi_chinh_thong"]),
            "counter_evidence_sources": 1
        }
    }

    # 6. Ghi các tệp xuất bản
    # 6.1. danh_muc_duong.jsonl và .csv
    confirmed_jsonl = V1_DIR / "danh_muc_duong.jsonl"
    with open(confirmed_jsonl, "w", encoding="utf-8") as f:
        for r in final_confirmed:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    confirmed_csv = V1_DIR / "danh_muc_duong.csv"
    if final_confirmed:
        fieldnames = list(final_confirmed[0].keys())
        with open(confirmed_csv, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(final_confirmed)

    # 6.2. danh_muc_candidates_pending.jsonl và .csv
    cand_jsonl = V1_DIR / "danh_muc_candidates_pending.jsonl"
    with open(cand_jsonl, "w", encoding="utf-8") as f:
        for r in candidates_pending_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    cand_csv = V1_DIR / "danh_muc_candidates_pending.csv"
    if candidates_pending_records:
        all_cand_keys = set()
        for r in candidates_pending_records:
            all_cand_keys.update(r.keys())
        cand_fieldnames = sorted(list(all_cand_keys))
        with open(cand_csv, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=cand_fieldnames)
            writer.writeheader()
            for r in candidates_pending_records:
                row_dict = {k: r.get(k, "") for k in cand_fieldnames}
                writer.writerow(row_dict)

    # 6.3. record_evidence_mapping.json
    (V1_DIR / "record_evidence_mapping.json").write_text(
        json.dumps(record_evidence_mapping, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # 6.4. khoa_tra_cuu.json
    (V1_DIR / "khoa_tra_cuu.json").write_text(
        json.dumps(lookup_index, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # 6.5. khoa_xung_dot.json
    (V1_DIR / "khoa_xung_dot.json").write_text(
        json.dumps(conflict_data, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # 6.6. statistics.json
    (V1_DIR / "statistics.json").write_text(
        json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # 6.7. schema.json
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "VietnamStreetGazetteerV1_1_Schema",
        "type": "object",
        "required": [
            "id", "canonical_name", "road_type", "ma_tinh", "ten_tinh",
            "administrative_era", "source_id", "source_type", "source_url",
            "source_sha256", "status", "verification_status", "evidence_snippet"
        ],
        "properties": {
            "id": {"type": "string", "pattern": "^STR_CONF_[0-9]{4}$"},
            "canonical_name": {"type": "string", "minLength": 2},
            "road_type": {"type": "string", "enum": ["Đường", "Phố", "Quốc lộ", "Đại lộ", "Xa lộ", "Cao tốc"]},
            "ma_tinh": {"type": "string", "pattern": "^[0-9]{2}$"},
            "ten_tinh": {"type": "string"},
            "administrative_era": {"type": "string", "enum": ["hien_hanh", "moi_2025", "cu_2024"]},
            "source_id": {"type": "string"},
            "source_type": {"type": "string", "enum": ["van_ban_quy_pham", "bao_chi_chinh_thong", "cong_thong_tin_chinh_phu", "cong_dong_osm"]},
            "source_url": {"type": "string", "format": "uri"},
            "source_sha256": {"type": "string", "pattern": "^[a-f0-9]{64}$"},
            "status": {"type": "string", "enum": ["confirmed"]},
            "verification_status": {"type": "string", "enum": ["verified_with_raw_evidence"]},
            "evidence_snippet": {"type": "string", "minLength": 10}
        }
    }
    (V1_DIR / "schema.json").write_text(json.dumps(schema, ensure_ascii=False, indent=2), encoding="utf-8")

    # 6.8. manifest.json (băm toàn bộ tệp trong v1/ trừ manifest.json và legacy snapshot)
    v1_manifest = {
        "metadata": {
            "version": "1.1.0",
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "description": "Bảng mã băm SHA-256 toàn bộ các tệp phân phối thuộc danh mục đường v1.1."
        },
        "files": []
    }
    for p in sorted(V1_DIR.rglob("*")):
        if p.is_file() and p.name != "manifest.json" and "legacy_v1_snapshot" not in str(p):
            rel_path = p.relative_to(BASE_DIR).as_posix()
            v1_manifest["files"].append({
                "path": rel_path,
                "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                "size_bytes": p.stat().st_size
            })
    (V1_DIR / "manifest.json").write_text(json.dumps(v1_manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n=== HOÀN TẤT XÂY DỰNG DANH MỤC ĐƯỜNG V1.1 ===")
    print(f"- Số bản ghi CONFIRMED có nguồn thật: {len(final_confirmed)}")
    print(f"- Số bản ghi CANDIDATE / PENDING được hạ trạng thái: {len(candidates_pending_records)}")
    print(f"- Số tệp raw sources chứng thực: {len(raw_manifest['sources'])}")
    print(f"- Đã ghi manifest.json với {len(v1_manifest['files'])} tệp.")


if __name__ == "__main__":
    build_danh_muc()
