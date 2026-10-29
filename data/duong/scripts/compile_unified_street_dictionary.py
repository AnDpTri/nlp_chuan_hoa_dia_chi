#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Biên soạn từ điển đường thống nhất (tu_dien_duong_v2.json).

Tích hợp:
1. Từ điển đường train gốc (danh_gia/ket_qua/sua_pipeline_cnn_v1_01/tu_dien_duong_train.json).
2. Danh mục đường Thủ đô Hà Nội (data/duong/scripts/definitions/hanoi.py).
3. Danh mục đường TP. Hồ Chí Minh (data/duong/scripts/definitions/tphcm.py).
4. Danh mục đường Đà Nẵng, Hải Phòng, Cần Thơ, Huế (data/duong/scripts/definitions/mientrung.py).
5. Danh mục đường các đô thị tỉnh lỵ (data/duong/scripts/definitions/tinh_thanh.py).
6. Danh mục đường OSM đã xác thực (data/duong/scripts/definitions/osm_streets.py).
7. Hệ thống Quốc lộ Việt Nam (data/duong/scripts/definitions/quoc_lo.py).
8. Danh mục candidate hợp lệ từ văn bản pháp quy (data/duong/v1/danh_muc_candidates_pending.jsonl).

TUYỆT ĐỐI KHÔNG DÙNG DỮ LIỆU TẬP TEST.
"""

import json
import re
from pathlib import Path
import sys

# Ensure root directory is in path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.chuan_ten_duong import tach_ten, TuDienDuong
from src.danh_muc import DanhMuc
from data.duong.scripts.definitions.hanoi import HANOI_STREETS
from data.duong.scripts.definitions.tphcm import TPHCM_STREETS
from data.duong.scripts.definitions.mientrung import (
    DANANG_STREETS,
    HAIPHONG_STREETS,
    CANTHO_STREETS,
    HUE_STREETS,
)
from data.duong.scripts.definitions.tinh_thanh import PROVINCIAL_CITIES_STREETS
from data.duong.scripts.definitions.osm_streets import OSM_VERIFIED_STREETS
from data.duong.scripts.definitions.quoc_lo import NATIONAL_HIGHWAYS


def clean_name(name: str) -> str:
    name = re.sub(r"\s+", " ", name).strip()
    return name


def make_canon(prefix: str, name: str) -> str:
    prefix = clean_name(prefix)
    name = clean_name(name)
    if name.casefold().startswith(prefix.casefold() + " "):
        return name
    return f"{prefix} {name}"


def compile_dictionary(out_file: str = "tu_dien_duong_v4.json"):
    dm = DanhMuc()
    tinh_names_map = {}
    for (cay, ma), dv in dm.don_vi.items():
        if dv.cap == "tinh":
            tinh_names_map.setdefault(ma, set()).add(dv.ten.casefold())
            tinh_names_map.setdefault(ma, set()).add(dv.ten.casefold().replace("tỉnh ", "").replace("thành phố ", ""))

    entries_map = {}

    def add_entry(prov: str, canonical: str, source_id: str, observed: list[str] = None):
        prov = str(prov).strip().zfill(2)
        canonical = clean_name(canonical)
        parsed = tach_ten(canonical)
        if not parsed:
            return
        kind, words, co_tien_to = parsed
        k_len = len(kind.split())
        while words and " ".join(words[:k_len]).casefold() == kind.casefold():
            words = words[k_len:]
        while words and words[0].casefold() in ("đường", "phố"):
            words = words[1:]
        while words and len(words) >= 2 and " ".join(words[:2]).casefold() in ("xa lộ", "đại lộ", "quốc lộ", "vành đai"):
            words = words[2:]
        if not words:
            return
        full_canonical = kind + " " + " ".join(words)
        core_name = " ".join(words).casefold()

        # Không lấy tên đường trùng với tên của chính tỉnh đó (lỗi nhãn train)
        prov_tinh_names = tinh_names_map.get(prov, set())
        if core_name in prov_tinh_names:
            return

        key = (prov, full_canonical.casefold())
        if key not in entries_map:
            entries_map[key] = {
                "province": prov,
                "canonical": full_canonical,
                "train_ids": [],
                "observed_forms": [],
            }
        item = entries_map[key]
        if source_id and source_id not in item["train_ids"]:
            item["train_ids"].append(source_id)
        forms = observed or [full_canonical, " ".join(words)]
        for f in forms:
            f_clean = clean_name(f)
            f_parsed = tach_ten(f_clean)
            if f_parsed:
                f_kind, f_words, _ = f_parsed
                fk_len = len(f_kind.split())
                while f_words and " ".join(f_words[:fk_len]).casefold() == f_kind.casefold():
                    f_words = f_words[fk_len:]
                while f_words and f_words[0].casefold() in ("đường", "phố"):
                    f_words = f_words[1:]
                while f_words and len(f_words) >= 2 and " ".join(f_words[:2]).casefold() in ("xa lộ", "đại lộ", "quốc lộ", "vành đai"):
                    f_words = f_words[2:]
                if f_words:
                    f_clean = f_kind + " " + " ".join(f_words)
            if not f_clean:
                continue
            if f_clean.casefold() in prov_tinh_names or f_clean.casefold().replace("đường ", "").replace("phố ", "").replace("xa lộ ", "") in prov_tinh_names:
                continue
            if f_clean and f_clean not in item["observed_forms"]:
                item["observed_forms"].append(f_clean)
        bare = " ".join(words)
        if bare.casefold() not in prov_tinh_names and bare not in item["observed_forms"]:
            item["observed_forms"].append(bare)
        if full_canonical not in item["observed_forms"]:
            item["observed_forms"].insert(0, full_canonical)

    # 1. Base train dictionary
    train_dict_p = ROOT / "danh_gia/ket_qua/sua_pipeline_cnn_v1_01/tu_dien_duong_train.json"
    if train_dict_p.exists():
        train_data = json.loads(train_dict_p.read_text(encoding="utf-8"))
        for entry in train_data.get("entries", []):
            prov = entry["province"]
            canon = entry["canonical"]
            t_ids = entry.get("train_ids", ["train_base"])
            obs = entry.get("observed_forms", [])
            for t_id in t_ids:
                add_entry(prov, canon, t_id, obs)
        print(f"Loaded {len(train_data.get('entries', []))} entries from train dictionary.")

    # 2. Hanoi (prov 01)
    for item in HANOI_STREETS:
        name, prefix, district, desc, src, alias = item
        canon = make_canon(prefix, name)
        obs = [canon, name]
        if alias:
            for al in alias.split(";"):
                if al.strip():
                    obs.append(al.strip())
        add_entry("01", canon, "def_hanoi", obs)

    # 3. TPHCM (prov 79)
    for item in TPHCM_STREETS:
        name, prefix, district, desc, src, alias = item
        canon = make_canon(prefix, name)
        obs = [canon, name]
        if alias:
            for al in alias.split(";"):
                if al.strip():
                    obs.append(al.strip())
        add_entry("79", canon, "def_tphcm", obs)

    # 4. Danang (prov 48)
    for item in DANANG_STREETS:
        name, prefix, district, desc, src, alias = item
        canon = make_canon(prefix, name)
        obs = [canon, name]
        if alias:
            for al in alias.split(";"):
                if al.strip():
                    obs.append(al.strip())
        add_entry("48", canon, "def_danang", obs)

    # 5. Hai Phong (prov 31)
    for item in HAIPHONG_STREETS:
        name, prefix, district, desc, src, alias = item
        canon = make_canon(prefix, name)
        obs = [canon, name]
        if alias:
            for al in alias.split(";"):
                if al.strip():
                    obs.append(al.strip())
        add_entry("31", canon, "def_haiphong", obs)

    # 6. Can Tho (prov 92)
    for item in CANTHO_STREETS:
        name, prefix, district, desc, src, alias = item
        canon = make_canon(prefix, name)
        obs = [canon, name]
        if alias:
            for al in alias.split(";"):
                if al.strip():
                    obs.append(al.strip())
        add_entry("92", canon, "def_cantho", obs)

    # 7. Hue (prov 46)
    for item in HUE_STREETS:
        name, prefix, district, desc, src, alias = item
        canon = make_canon(prefix, name)
        obs = [canon, name]
        if alias:
            for al in alias.split(";"):
                if al.strip():
                    obs.append(al.strip())
        add_entry("46", canon, "def_hue", obs)

    # 8. Provincial cities
    for item in PROVINCIAL_CITIES_STREETS:
        prov_code, prov_name, st_name, prefix, district, desc, src, alias, status = item
        canon = make_canon(prefix, st_name)
        obs = [canon, st_name]
        if alias:
            for al in alias.split(";"):
                if al.strip():
                    obs.append(al.strip())
        add_entry(prov_code, canon, "def_tinh_thanh", obs)

    # 9. OSM verified
    for item in OSM_VERIFIED_STREETS:
        prov_code, prov_name, st_name, prefix, district, osm_id, src, alias, status = item
        canon = make_canon(prefix, st_name)
        obs = [canon, st_name]
        if alias:
            for al in alias.split(";"):
                if al.strip():
                    obs.append(al.strip())
        add_entry(prov_code, canon, "def_osm_streets", obs)

    # 10. National highways
    for item in NATIONAL_HIGHWAYS:
        ma_tuyen, canon_name, r_type, desc, provs, aliases = item
        canon = canon_name
        obs = [canon]
        if aliases:
            for al in aliases.split(";"):
                if al.strip():
                    obs.append(al.strip())
        for p in provs.split(","):
            p = p.strip()
            if p:
                add_entry(p, canon, "def_quoc_lo", obs)

    # 11. Valid candidates from candidates_pending.jsonl
    cand_p = ROOT / "data/duong/v1/danh_muc_candidates_pending.jsonl"
    if cand_p.exists():
        for line in cand_p.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            prov = row.get("ma_tinh")
            c_name = row.get("canonical_name")
            r_type = row.get("road_type") or "Đường"
            if not prov or not c_name:
                continue
            canon = f"{r_type} {c_name}"
            obs = [canon, c_name]
            al = row.get("aliases", "")
            if al:
                for a in al.split(";"):
                    if a.strip():
                        obs.append(a.strip())
            add_entry(prov, canon, row.get("id", "cand_v1"), obs)

    # 12. Verified streets from train.csv (labeled training set, 20,000 samples)
    train_csv_p = ROOT / "data/train_dev/train.csv"
    if train_csv_p.exists():
        import csv
        with train_csv_p.open(encoding="utf-8") as f:
            for row in csv.DictReader(f):
                duong = (row.get("duong") or "").strip()
                ma_tinh = (row.get("ma_tinh") or "").strip()
                t_id = row.get("id", "train_csv")
                if duong and ma_tinh:
                    duong_clean = clean_name(duong)
                    parsed = tach_ten(duong_clean)
                    if parsed:
                        kind, words, co_tien_to = parsed
                        full_canon = kind + " " + " ".join(words)
                        obs = [full_canon, " ".join(words)]
                        add_entry(ma_tinh, full_canon, t_id, obs)

    sorted_entries = sorted(entries_map.values(), key=lambda r: (r["province"], r["canonical"]))
    payload = {
        "format": 1,
        "source_scope": "train_only",
        "description": "Unified verified street gazetteer compiled from official urban decisions, verified definitions, and clean train dataset. Strictly 0% test data.",
        "entries": sorted_entries,
    }

    out_p = ROOT / "danh_gia/ket_qua/tu_dien_duong_v4.json"
    out_p.parent.mkdir(parents=True, exist_ok=True)
    out_p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved {len(sorted_entries)} unique verified street entries to {out_p}.")

    # Validate TuDienDuong loads it properly
    td = TuDienDuong(out_p)
    print(f"Validation successful! TuDienDuong SHA256: {td.ma_bam[:16]}... Index buckets: {len(td.index)}")


if __name__ == "__main__":
    compile_dictionary()
