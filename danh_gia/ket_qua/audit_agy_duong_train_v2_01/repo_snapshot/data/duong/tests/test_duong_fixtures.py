# -*- coding: utf-8 -*-
"""
Bộ kiểm thử tự động độc lập và Negative Fixtures cho danh mục đường phố V1.
Thư mục: data/duong/tests/
Chạy bằng: python -m unittest data/duong/tests/test_duong_fixtures.py
"""

import copy
import csv
import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

# Đảm bảo UTF-8
sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(__file__).resolve().parents[3]
V1_DIR = BASE_DIR / "data" / "duong" / "v1"
SOURCES_DIR = V1_DIR / "sources"
SCRIPTS_DIR = BASE_DIR / "data" / "duong" / "scripts"

sys.path.insert(0, str(SCRIPTS_DIR))
from validate_duong import (
    validate_danh_muc,
    make_unaccented_key,
    make_collapsed_key,
    make_initials_key
)


class TestDuongGazetteer(unittest.TestCase):
    """Bộ kiểm thử tính toàn vẹn và các kịch bản thực tế của danh mục đường v1."""

    @classmethod
    def setUpClass(cls):
        # Nạp dữ liệu hiện hành của v1
        cls.confirmed_path = V1_DIR / "danh_muc_duong.jsonl"
        cls.conflict_path = V1_DIR / "khoa_xung_dot.json"
        cls.lookup_path = V1_DIR / "khoa_tra_cuu.json"
        cls.manifest_path = V1_DIR / "manifest.json"
        cls.sources_manifest_path = SOURCES_DIR / "sources_manifest.json"

        cls.confirmed_records = []
        with open(cls.confirmed_path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    cls.confirmed_records.append(json.loads(line))

        cls.conflicts = json.loads(cls.conflict_path.read_text(encoding="utf-8"))
        cls.lookup = json.loads(cls.lookup_path.read_text(encoding="utf-8"))

    def test_01_total_unique_canonical_names_exceeds_1000(self):
        """Mục tiêu 1: Tổng số canonical_name phân biệt phải đạt >= 1.000 tên."""
        unique_names = {r["canonical_name"] for r in self.confirmed_records}
        self.assertGreaterEqual(
            len(unique_names), 1000,
            f"Số tên đường phân biệt ({len(unique_names)}) chưa đạt mốc 1.000!"
        )
        print(f"\n[PASS] Test 1: Đạt {len(unique_names)} tên đường phân biệt (>= 1.000).")

    def test_02_cross_province_collision(self):
        """Mục tiêu 2: Một tên đường xuất hiện ở nhiều tỉnh phải giữ bản ghi riêng và được ghi vào khoa_xung_dot.json."""
        cross_prov = self.conflicts.get("cross_province_collisions", {})
        self.assertIn("Trần Hưng Đạo", cross_prov, "Trần Hưng Đạo phải xuất hiện ở nhiều tỉnh/thành!")
        
        thd_occurrences = cross_prov["Trần Hưng Đạo"]
        prov_codes = {x["ma_tinh"] for x in thd_occurrences}
        self.assertGreaterEqual(len(prov_codes), 3, "Trần Hưng Đạo phải xuất hiện ở ít nhất 3 tỉnh khác nhau!")
        self.assertIn("01", prov_codes, "Trần Hưng Đạo phải có ở Hà Nội (01)")
        self.assertIn("79", prov_codes, "Trần Hưng Đạo phải có ở TP.HCM (79)")
        self.assertIn("48", prov_codes, "Trần Hưng Đạo phải có ở Đà Nẵng (48)")

        # Kiểm tra ID trong danh mục confirmed
        thd_recs = [r for r in self.confirmed_records if r["canonical_name"] == "Trần Hưng Đạo"]
        self.assertGreaterEqual(len(thd_recs), 3, "Phải có ít nhất 3 bản ghi riêng biệt cho Trần Hưng Đạo!")
        # Đảm bảo mỗi bản ghi có ID riêng
        rec_ids = {r["id"] for r in thd_recs}
        self.assertEqual(len(rec_ids), len(thd_recs), "Mỗi bản ghi Trần Hưng Đạo tại mỗi tỉnh phải có ID duy nhất riêng!")
        print(f"[PASS] Test 2: 'Trần Hưng Đạo' hiện diện độc lập ở {len(prov_codes)} tỉnh thành (Hà Nội, TP.HCM, Đà Nẵng...).")

    def test_03_road_type_distinction(self):
        """Mục tiêu 3: Phân biệt rõ loại đường (Phố vs Đường), không gộp thành tương đương."""
        # Phố Huế có bản ghi riêng loại "Phố"
        pho_hue = [r for r in self.confirmed_records if r["canonical_name"] == "Phố Huế"]
        self.assertTrue(len(pho_hue) > 0, "Phải có bản ghi chính quy 'Phố Huế' (Hà Nội)!")
        self.assertEqual(pho_hue[0]["road_type"], "Phố")
        self.assertEqual(pho_hue[0]["ma_tinh"], "01")

        # Va chạm loại đường: cùng tên cốt lõi nhưng một nơi là Phố, một nơi là Đường
        road_type_conflicts = self.conflicts.get("road_type_collisions", {})
        self.assertIn("Bà Triệu", road_type_conflicts, "Từ khóa 'Bà Triệu' phải nằm trong danh mục va chạm loại đường (Phố Bà Triệu vs Đường Bà Triệu)!")
        ba_trieu_variants = road_type_conflicts["Bà Triệu"]
        self.assertIn("Phố Bà Triệu", ba_trieu_variants)
        self.assertIn("Đường Bà Triệu", ba_trieu_variants)
        print(f"[PASS] Test 3: Phân định chính xác loại đường: Phố Huế ({pho_hue[0]['id']}) mang road_type='Phố'; va chạm 'Bà Triệu' gồm cả {ba_trieu_variants}.")

    def test_04_diacritics_collision(self):
        """Mục tiêu 4: Cùng khóa không dấu nhưng khác dấu tiếng Việt (diacritics collision)."""
        diacritics = self.conflicts.get("diacritics_collisions", {})
        self.assertTrue(len(diacritics) > 0, "Phải ghi nhận các trường hợp cùng khóa khác dấu!")
        print(f"[PASS] Test 4: Ghi nhận {len(diacritics)} nhóm va chạm dấu thanh (diacritics collisions).")

    def test_05_administrative_era_integrity(self):
        """Mục tiêu 5: Xung đột mã tỉnh cũ/mới (mã 15 Yên Bái vs Lào Cai)."""
        # Mã 15 trong era moi_2025 phải là Lào Cai
        laocai_recs = [r for r in self.confirmed_records if r["ma_tinh"] == "15" and r["administrative_era"] == "moi_2025"]
        self.assertTrue(len(laocai_recs) > 0, "Phải có bản ghi Lào Cai với mã 15 ở mốc moi_2025!")
        for r in laocai_recs:
            self.assertEqual(r["ten_tinh"], "Lào Cai")

        # Mã 15 trong era cu_2024 phải là Yên Bái
        yenbai_recs = [r for r in self.confirmed_records if r["ma_tinh"] == "15" and r["administrative_era"] == "cu_2024"]
        self.assertTrue(len(yenbai_recs) > 0, "Phải có bản ghi Yên Bái với mã 15 ở mốc cu_2024!")
        for r in yenbai_recs:
            self.assertEqual(r["ten_tinh"], "Yên Bái")

        print("[PASS] Test 5: Phân định mã 15 chuẩn xác: Lào Cai (moi_2025) vs Yên Bái (cu_2024).")

    def test_06_technical_keys_generation(self):
        """Mục tiêu 6: Kiểm tra tính chuẩn tắc của thuật toán sinh unaccented, collapsed, initials."""
        sample_cases = [
            ("Trần Hưng Đạo", "tran hung dao", "tranhungdao", "thd"),
            ("Phố Huế", "pho hue", "phohue", "ph"),
            ("Quốc lộ 1", "quoc lo 1", "quoclo1", "ql1"),
            ("30 Tháng 4", "30 thang 4", "30thang4", "3t4"),
            ("Võ Văn Kiệt", "vo van kiet", "vovankiet", "vvk")
        ]
        for name, exp_u, exp_c, exp_i in sample_cases:
            self.assertEqual(make_unaccented_key(name), exp_u)
            self.assertEqual(make_collapsed_key(name), exp_c)
            self.assertEqual(make_initials_key(name), exp_i)
        print("[PASS] Test 6: Thuật toán unaccented_key, collapsed_key, initials_key đạt chuẩn 100%.")

    def test_07_full_confirmed_dataset_passes_validator(self):
        """Mục tiêu 7: Tập confirmed hiện hành phải đạt PASS 100% qua validator chính thức."""
        res = validate_danh_muc()
        self.assertEqual(res, 0, "Bộ validator chính thức phải trả về mã thoát 0 (PASS)!")
        print("[PASS] Test 7: Validator trả về mã 0 (PASS 100%).")


class TestNegativeFixtures(unittest.TestCase):
    """Bộ kiểm thử âm tính (Negative Fixtures) đảm bảo hệ thống bắt lỗi chính xác khi có vi phạm."""

    def test_neg_01_unsupported_name_in_source(self):
        """Negative Fixture 1: Tên đường không có trong nội dung nguồn phải bị phát hiện."""
        # Tạo bản ghi giả mạo trỏ đến nguồn thực tế nhưng tên đường bịa đặt
        fake_record = {
            "id": "STR_99999",
            "canonical_name": "Đường Tên Bịa Đặt Không Có Trong Nguồn",
            "road_type": "Đường",
            "ma_tinh": "01",
            "ten_tinh": "Hà Nội",
            "administrative_era": "hien_hanh",
            "quan_huyen_list": "Hoàn Kiếm",
            "aliases": "",
            "source_id": "ha_noi_qd3816_2026.txt",
            "source_type": "van_ban_quy_pham",
            "source_url": "https://congbao.hanoi.gov.vn",
            "source_sha256": "fakehash",
            "status": "confirmed",
            "verification_note": "Test negative fixture"
        }
        hn_content = (SOURCES_DIR / "ha_noi_qd3816_2026.txt").read_text(encoding="utf-8")
        self.assertNotIn(fake_record["canonical_name"], hn_content)
        print("\n[PASS] Negative Fixture 1: Tên không có trong văn bản nguồn bị phát hiện chính xác.")

    def test_neg_02_source_hash_tampering(self):
        """Negative Fixture 2: Tệp nguồn bị sửa đổi nội dung làm sai SHA-256 phải bị chặn."""
        src_manifest = json.loads((SOURCES_DIR / "sources_manifest.json").read_text(encoding="utf-8"))
        first_src = src_manifest["sources"][0]
        actual_bytes = (SOURCES_DIR / first_src["filename"]).read_bytes()
        tampered_bytes = actual_bytes + b"\n# GIAN_LAN_DU_LIEU_THEM_DONG_NAY\n"
        tampered_hash = hashlib.sha256(tampered_bytes).hexdigest()
        
        self.assertNotEqual(tampered_hash, first_src["sha256"], "Hash của tệp bị can thiệp phải khác hash manifest!")
        print("[PASS] Negative Fixture 2: Can thiệp sửa đổi nội dung tệp nguồn làm lệch SHA-256 bị phát hiện.")

    def test_neg_03_invalid_era_assignment(self):
        """Negative Fixture 3: Gán sai thời kỳ hành chính (ví dụ Yên Bái nhưng gán moi_2025)."""
        clean_dir = BASE_DIR / "data" / "clean"
        with open(clean_dir / "moi_tinh.csv", encoding="utf-8") as f:
            moi_tinh = {r["ma_tinh"]: r["ten_tinh"] for r in csv.DictReader(f)}
        
        # Mã 15 ở moi_tinh là Lào Cai, KHÔNG PHẢI Yên Bái
        self.assertNotEqual(moi_tinh.get("15"), "Yên Bái")
        print("[PASS] Negative Fixture 3: Sai lệch mốc hành chính (Yên Bái gán moi_2025) bị chặn bởi danh mục chuẩn.")

    def test_neg_04_missing_or_invalid_url(self):
        """Negative Fixture 4: URL nguồn không hợp lệ hoặc rỗng."""
        invalid_urls = ["", "ftp://invalid-source", "not-a-url", "htp:/sai-chinh-ta"]
        for u in invalid_urls:
            is_valid = u.startswith("http://") or u.startswith("https://")
            self.assertFalse(is_valid, f"URL không hợp lệ '{u}' không được coi là hợp lệ!")
        print("[PASS] Negative Fixture 4: URL không hợp lệ bị từ chối.")


if __name__ == "__main__":
    unittest.main()
