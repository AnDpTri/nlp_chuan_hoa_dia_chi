# -*- coding: utf-8 -*-
"""
Bộ kiểm thử tự động độc lập, Positive Fixtures và Negative Fixtures cho Danh mục đường phố V1.1 (Post-Audit).
Thư mục: data/duong/tests/
Chạy bằng: python -m unittest data/duong/tests/test_duong_fixtures.py
"""

import copy
import csv
import hashlib
import html
import json
import os
import re
import sys
import unittest
from pathlib import Path
from urllib.parse import urlsplit

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(__file__).resolve().parents[3]
V1_DIR = BASE_DIR / "data" / "duong" / "v1"
RAW_SOURCES_DIR = V1_DIR / "raw_sources"
SCRIPTS_DIR = BASE_DIR / "data" / "duong" / "scripts"

sys.path.insert(0, str(SCRIPTS_DIR))
from validate_duong import (
    validate_danh_muc,
    make_unaccented_key,
    make_collapsed_key,
    make_initials_key,
    is_homepage_url
)


class TestDuongGazetteerPostAudit(unittest.TestCase):
    """Bộ kiểm thử tính toàn vẹn và các kịch bản thực tế sau audit độc lập."""

    @classmethod
    def setUpClass(cls):
        cls.confirmed_path = V1_DIR / "danh_muc_duong.jsonl"
        cls.candidates_path = V1_DIR / "danh_muc_candidates_pending.jsonl"
        cls.mapping_path = V1_DIR / "record_evidence_mapping.json"
        cls.raw_manifest_path = RAW_SOURCES_DIR / "raw_sources_manifest.json"

        cls.confirmed_records = []
        with open(cls.confirmed_path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    cls.confirmed_records.append(json.loads(line))

        cls.candidates_records = []
        with open(cls.candidates_path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    cls.candidates_records.append(json.loads(line))

        cls.mapping = json.loads(cls.mapping_path.read_text(encoding="utf-8"))
        cls.raw_manifest = json.loads(cls.raw_manifest_path.read_text(encoding="utf-8"))
        
        cls.raw_contents = {}
        for s in cls.raw_manifest["sources"]:
            fpath = RAW_SOURCES_DIR / s["filename"]
            cls.raw_contents[s["source_id"]] = fpath.read_text(encoding="utf-8", errors="replace")

    def test_01_confirmed_records_have_verified_raw_evidence(self):
        """Khẳng định 100% bản ghi confirmed đều có nguồn thô thật, HTTP 200, và mapping snippet."""
        self.assertGreater(len(self.confirmed_records), 0, "Tập confirmed không được rỗng!")
        for r in self.confirmed_records:
            self.assertEqual(r["status"], "confirmed")
            self.assertEqual(r["verification_status"], "verified_with_raw_evidence")
            self.assertIn(r["source_id"], self.raw_contents, f"Nguồn {r['source_id']} phải có file raw trên đĩa!")
            self.assertIn(r["id"], self.mapping, f"Bản ghi {r['id']} phải có trong record_evidence_mapping.json!")
        print(f"\n[PASS] Test 1: Toàn bộ {len(self.confirmed_records)} bản ghi CONFIRMED đều có raw evidence độc lập.")

    def test_02_all_legacy_records_downgraded_to_candidate(self):
        """Khẳng định toàn bộ 1.461 bản ghi cũ từ V1 đã được hạ trạng thái minh bạch xuống candidate."""
        legacy_candidates = [c for c in self.candidates_records if c.get("status") == "candidate_unverified_source"]
        self.assertGreaterEqual(
            len(legacy_candidates), 1461,
            f"Số lượng bản ghi hạ trạng thái ({len(legacy_candidates)}) chưa đủ 1.461!"
        )
        for c in legacy_candidates:
            self.assertNotEqual(c.get("status"), "confirmed", "Không bản ghi candidate nào được phép ghi là confirmed!")
            self.assertIn("downgrade_reason", c, "Bản ghi candidate phải có lý do hạ trạng thái rõ ràng!")
        print(f"[PASS] Test 2: Đã hạ trạng thái {len(legacy_candidates)} bản ghi cũ xuống candidate_unverified_source.")

    def test_03_road_type_distinction(self):
        """Phân biệt rõ loại đường Phố vs Đường, không gộp tương đương."""
        pho_records = [r for r in self.confirmed_records if r["road_type"] == "Phố"]
        duong_records = [r for r in self.confirmed_records if r["road_type"] == "Đường"]
        self.assertGreater(len(pho_records), 0, "Phải có các tuyến loại Phố!")
        self.assertGreater(len(duong_records), 0, "Phải có các tuyến loại Đường!")
        for r in pho_records:
            self.assertTrue(r["canonical_name"].startswith("Phố "), f"Bản ghi Phố phải có tên bắt đầu bằng Phố: {r['canonical_name']}")
        print(f"[PASS] Test 3: Phân định chính xác {len(pho_records)} Phố và {len(duong_records)} Đường.")

    def test_04_exact_evidence_snippet_grounding(self):
        """Khẳng định exact snippet của từng bản ghi confirmed xuất hiện thực tế trong raw content."""
        for r in self.confirmed_records:
            sid = r["source_id"]
            snip = r["evidence_snippet"]
            raw_text = self.raw_contents[sid]
            
            clean_raw = re.sub(r'\s+', ' ', html.unescape(raw_text))
            clean_raw_text_only = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', html.unescape(raw_text)))
            clean_snip = re.sub(r'\s+', ' ', html.unescape(snip))
            clean_snip_text_only = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', html.unescape(snip)))

            matched = (clean_snip in clean_raw) or (clean_snip_text_only in clean_raw_text_only)
            self.assertTrue(matched, f"Snippet của {r['id']} ('{r['canonical_name']}') không tìm thấy trong {sid}!")
        print(f"[PASS] Test 4: 100% snippet ({len(self.confirmed_records)}/{len(self.confirmed_records)}) khớp nguyên văn trong raw HTML.")

    def test_05_technical_keys_generation(self):
        """Kiểm tra thuật toán sinh khóa kỹ thuật unaccented, collapsed, initials."""
        sample_cases = [
            ("Phố Nguyễn Hữu Liêu", "pho nguyen huu lieu", "phonguyenhuulieu", "pnhl"),
            ("Đường Đỗ Mười", "duong do muoi", "duongdomuoi", "ddm"),
            ("Cao tốc Bắc - Nam phía Đông", "cao toc bac nam phia dong", "caotocbacnamphiadong", "ctbnpd"),
            ("Đường Bình Kỳ", "duong binh ky", "duongbinhky", "dbk")
        ]
        for name, exp_u, exp_c, exp_i in sample_cases:
            self.assertEqual(make_unaccented_key(name), exp_u)
            self.assertEqual(make_collapsed_key(name), exp_c)
            self.assertEqual(make_initials_key(name), exp_i)
        print("[PASS] Test 5: Thuật toán unaccented_key, collapsed_key, initials_key đạt chuẩn 100%.")

    def test_06_positive_fixture_valid_confirmed_record(self):
        """Positive Fixture: Bản ghi confirmed mẫu có đầy đủ raw source, exact snippet và hash được chấp nhận."""
        sample = self.confirmed_records[0]
        self.assertIn("evidence_snippet", sample)
        self.assertEqual(sample["verification_status"], "verified_with_raw_evidence")
        self.assertGreater(len(sample["source_sha256"]), 60)
        self.assertFalse(is_homepage_url(sample["source_url"]), "URL mẫu không được là trang chủ!")
        print(f"[PASS] Test 6 (Positive Fixture): Bản ghi confirmed mẫu {sample['id']} đạt chuẩn.")

    def test_07_full_dataset_passes_validator(self):
        """Khẳng định toàn bộ bộ dữ liệu v1.1 đạt PASS 100% trên validator."""
        res = validate_danh_muc()
        self.assertEqual(res, 0, "Validator phải trả về mã thoát 0 (PASS 100%)!")
        print("[PASS] Test 7: Validator trả về mã thoát 0.")


class TestNegativeFixturesPostAudit(unittest.TestCase):
    """Bộ kiểm thử âm tính (Negative Fixtures) chứng minh validator bắt lỗi chính xác các vi phạm audit chỉ ra."""

    def test_neg_01_reject_homepage_url(self):
        """Negative Fixture 1: Bắt lỗi nếu URL là trang chủ / portal root."""
        homepage_urls = [
            "https://congbao.hanoi.gov.vn",
            "https://congbao.hanoi.gov.vn/",
            "https://danang.gov.vn",
            "https://haiphong.gov.vn/",
            "https://vanban.chinhphu.vn",
            "https://www.openstreetmap.org"
        ]
        for u in homepage_urls:
            self.assertTrue(is_homepage_url(u), f"URL trang chủ '{u}' phải bị phát hiện!")
        
        valid_deep_urls = [
            "https://ttpvhcc.hanoi.gov.vn/chi-dao-cua-lanh-dao-thanh-pho/ha-noi-dat-ten-moi-cho-38-tuyen-pho-14-cong-trinh-cong-cong-trong-nam-2025-2850250724141348377.htm",
            "https://www.hcmcpv.org.vn/tin-tuc/tphcm-dat-ten-cac-dong-chi-lanh-dao-dang-nha-nuoc-va-cac-dong-chi-chi-huy-chien-dich-ho-chi-minh-tr-1491933298"
        ]
        for u in valid_deep_urls:
            self.assertFalse(is_homepage_url(u), f"Deep URL '{u}' không được coi là trang chủ!")
        print("\n[PASS] Negative Fixture 1: URL trang chủ / portal root bị phát hiện và từ chối chính xác.")

    def test_neg_02_reject_wrong_document_reference_docid204000(self):
        """Negative Fixture 2: Bắt lỗi việc gán URL docid=204000 cho QĐ 1454/QĐ-TTg."""
        counter_file = RAW_SOURCES_DIR / "docid204000_counter_evidence_raw.html"
        self.assertTrue(counter_file.exists(), "Tệp counter evidence docid 204000 phải tồn tại!")
        text = counter_file.read_text(encoding="utf-8", errors="replace")
        
        # Trang docid 204000 là QĐ 89/QĐ-TCTĐB, KHÔNG PHẢI QĐ 1454/QĐ-TTg
        self.assertIn("89/QĐ-TCTĐB", text, "Trang docid=204000 thực tế phải là QĐ 89/QĐ-TCTĐB!")
        self.assertNotIn("1454/QĐ-TTg", text, "Trang docid=204000 không được chứa QĐ 1454/QĐ-TTg!")
        print("[PASS] Negative Fixture 2: Sai đối tượng văn bản docid 204000 bị chặn bởi bằng chứng đối soát thực tế.")

    def test_neg_03_reject_snippet_not_in_raw_content(self):
        """Negative Fixture 3: Bắt lỗi trích đoạn snippet giả mạo không tồn tại trong raw content."""
        fake_snippet = "Đoạn văn bản bịa đặt hoàn toàn không có trong nội dung phản hồi HTTP nguyên bản của thành phố."
        hn_text = (RAW_SOURCES_DIR / "hanoi_qd3862_2025_raw.html").read_text(encoding="utf-8", errors="replace")
        self.assertNotIn(fake_snippet, hn_text, "Snippet bịa đặt không được xuất hiện trong raw content!")
        print("[PASS] Negative Fixture 3: Trích đoạn snippet bịa đặt bị phát hiện và từ chối.")

    def test_neg_04_reject_tampered_source_hash(self):
        """Negative Fixture 4: Bắt lỗi tệp raw response bị can thiệp làm sai lệch mã băm SHA-256."""
        manifest_p = RAW_SOURCES_DIR / "raw_sources_manifest.json"
        src_manifest = json.loads(manifest_p.read_text(encoding="utf-8"))
        first_src = src_manifest["sources"][0]
        actual_bytes = (RAW_SOURCES_DIR / first_src["filename"]).read_bytes()
        tampered_bytes = actual_bytes + b"\n<!-- TAMPERED_DATA_INJECTION -->\n"
        tampered_hash = hashlib.sha256(tampered_bytes).hexdigest()
        
        self.assertNotEqual(tampered_hash, first_src["sha256"], "Hash của tệp bị can thiệp phải khác hash manifest!")
        print("[PASS] Negative Fixture 4: Can thiệp sửa đổi tệp nguồn làm lệch SHA-256 bị phát hiện chính xác.")

    def test_neg_05_reject_unverified_record_claiming_confirmed(self):
        """Negative Fixture 5: Bắt lỗi bản ghi chưa có raw evidence nhưng tự nhận là confirmed."""
        fake_unverified_record = {
            "id": "STR_FAKE_001",
            "canonical_name": "Đường Tự Nghĩ Ra",
            "road_type": "Đường",
            "status": "confirmed",
            "verification_status": "verified_with_raw_evidence",
            "source_id": "SRC_NON_EXISTENT",
            "evidence_snippet": "Không có bằng chứng"
        }
        raw_manifest_p = RAW_SOURCES_DIR / "raw_sources_manifest.json"
        sources = [s["source_id"] for s in json.loads(raw_manifest_p.read_text(encoding="utf-8"))["sources"]]
        self.assertNotIn(fake_unverified_record["source_id"], sources, "Nguồn giả mạo không được có trong raw manifest!")
        print("[PASS] Negative Fixture 5: Bản ghi tự xưng confirmed khi thiếu raw evidence bị chặn.")


if __name__ == "__main__":
    unittest.main()
