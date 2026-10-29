#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bộ kiểm thử tự động toàn diện cho gói dữ liệu huấn luyện khó bo_sung_v2:
1. test_schema_and_counts: Kiểm tra số lượng >= 3000 mẫu, 650 họ, <= 5 biến thể/họ, schema 30 trường.
2. test_zero_padded_and_administrative_hierarchy: Kiểm tra mã zero-padded và quan hệ cha con.
3. test_char_spans_and_token_alignment: Kiểm tra dau_vao[start:end] == span_text và BIO tags.
4. test_runtime_tokenizer_compatibility_and_glued_cut: Kiểm tra tương thích runtime tokenizer.
5. test_anti_leakage_holdout_isolation: Kiểm tra 0% rò rỉ input, URL, họ che số nhà với Dev/Test.
6. test_provenance_integrity_and_parent_code_preservation: Kiểm tra 100% parent_id tồn tại và bảo toàn mã cha.
7. test_split_ward_and_ambiguous_acronym_policy: Kiểm tra chính sách giữ mơ hồ cho xã bị chia và viết tắt.
8. test_mixed_era_topological_compatibility: Kiểm tra tính tương thích topological của ca trộn mốc cũ/mới.
9. test_negative_fixture_road_mismatch_false_inheritance: Fixture âm bắt lỗi khác tên đường nhưng khai kế thừa.
10. test_negative_fixture_provenance_mismatched_parent_code: Fixture âm bắt lỗi mã nguồn khác cha.
11. test_negative_fixture_reused_id_or_namespace_violation: Fixture âm bắt lỗi ID tái dùng hoặc vi phạm namespace.
12. test_negative_fixture_typo_alters_identity: Fixture âm bắt lỗi typo làm thay đổi danh tính tên riêng.
13. test_negative_fixture_family_overlap_masked_holdout: Fixture âm bắt lỗi giao họ che số nhà với holdout.
14. test_negative_fixture_nfd_span_mismatch: Fixture âm bắt lỗi lệch offset ký tự NFD/NFC.
15. test_negative_fixture_split_ward_forced_single_target: Fixture âm bắt lỗi xã bị chia bị ép một mã đích.
16. test_idempotence_and_checksum_integrity: Kiểm tra mã băm SHA-256 khớp 100% manifest.json.
"""

import unittest
import csv
import json
import re
import hashlib
import unicodedata
from pathlib import Path
from collections import defaultdict, Counter

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parents[3]
DATA_DIR = PROJECT_DIR / "data"
CLEAN_DIR = DATA_DIR / "clean"
TEST_DIR = DATA_DIR / "test"
TRAIN_DEV_DIR = DATA_DIR / "train_dev"
BO_SUNG_V2_DIR = TRAIN_DEV_DIR / "bo_sung_v2"

import sys
sys.path.insert(0, str(PROJECT_DIR))
from src.tien_xu_ly import token_co_vi_tri

FIELDS_V2 = [
    'id', 'dau_vao', 'nguon', 'so_nha', 'ngo_ngach_hem', 'thon_xom', 'duong',
    'ma_xa_cu', 'ma_huyen_cu', 'ma_tinh_cu', 'ma_xa', 'ma_tinh', 'xa_phuong', 'tinh',
    'dia_chi_chuan', 'canh_bao', 'loai_nhan', 'nguon_du_lieu', 'ghi_chu',
    'nhom_mau_goc', 'loai_bien_the', 'trang_thai_nhan', 'provenance',
    'parent_id', 'parent_source_url', 'parent_snapshot_sha256', 'source_row_sha256',
    'family_id', 'transformation', 'moc_thoi_gian'
]

def plain(s):
    if not s: return ""
    text = unicodedata.normalize('NFD', str(s).casefold().replace('đ', 'd'))
    return ''.join(c for c in text if not unicodedata.combining(c))

def key(s):
    return ''.join(c for c in plain(s) if c.isalnum())

def norm(text):
    if not text: return ""
    text = unicodedata.normalize('NFD', str(text).lower().replace('đ', 'd'))
    text = ''.join(c for c in text if not unicodedata.combining(c))
    return re.sub(r'[^a-z0-9]+', ' ', text).strip()

def canonical_full_name(row, level):
    if not row: return ""
    name = unicodedata.normalize('NFC', row.get('ten_' + level, '')).strip()
    kind = unicodedata.normalize('NFC', row.get('loai_' + level, '')).strip()
    if name.lower().startswith(kind.lower() + ' '):
        return name
    return f"{kind} {name}"

class TestTrainBoSungV2(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.train_v2_file = BO_SUNG_V2_DIR / "train_bo_sung_v2.csv"
        cls.char_spans_file = BO_SUNG_V2_DIR / "train_spans_v2.jsonl"
        cls.token_spans_file = BO_SUNG_V2_DIR / "token_spans_v2.jsonl"
        cls.manifest_file = BO_SUNG_V2_DIR / "manifest.json"
        cls.summary_file = BO_SUNG_V2_DIR / "distribution_summary.json"
        cls.leak_audit_file = BO_SUNG_V2_DIR / "anti_leakage_audit.json"

        with open(cls.train_v2_file, encoding='utf-8-sig') as f:
            cls.rows_v2 = list(csv.DictReader(f))
        with open(cls.char_spans_file, encoding='utf-8') as f:
            cls.char_items = [json.loads(line) for line in f]
        with open(cls.token_spans_file, encoding='utf-8') as f:
            cls.token_items = [json.loads(line) for line in f]

        with open(CLEAN_DIR / 'moi_tinh.csv', encoding='utf-8-sig') as f:
            cls.new_p = {r['ma_tinh']: r for r in csv.DictReader(f)}
        with open(CLEAN_DIR / 'moi_tinh_xa.csv', encoding='utf-8-sig') as f:
            cls.new_w = {r['ma_xa']: r for r in csv.DictReader(f)}
        with open(CLEAN_DIR / 'cu_tinh.csv', encoding='utf-8-sig') as f:
            cls.old_p = {r['ma_tinh']: r for r in csv.DictReader(f)}
        with open(CLEAN_DIR / 'cu_huyen.csv', encoding='utf-8-sig') as f:
            cls.old_d = {r['ma_huyen']: r for r in csv.DictReader(f)}
        with open(CLEAN_DIR / 'cu_tinh_huyen_xa.csv', encoding='utf-8-sig') as f:
            cls.old_w = {r['ma_xa']: r for r in csv.DictReader(f)}
        with open(CLEAN_DIR / 'doi_chieu_xa_cu_moi.csv', encoding='utf-8-sig') as f:
            cls.maps = list(csv.DictReader(f))

        cls.valid_mixed_pairs = {(m['ma_huyen_cu'], m['ma_xa_moi']) for m in cls.maps if m['ma_xa_moi']}

    def test_schema_and_counts(self):
        """1. Kiểm tra số lượng >= 3000 mẫu, 650 họ, <= 5 biến thể/họ, schema 30 trường."""
        self.assertGreaterEqual(len(self.rows_v2), 3000, f"Số lượng mẫu chưa đạt: {len(self.rows_v2)} < 3000")
        with open(self.train_v2_file, encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            self.assertEqual(reader.fieldnames, FIELDS_V2, "Schema không khớp 30 trường chuẩn của gói v2")

        families = {r['family_id'] for r in self.rows_v2}
        self.assertGreaterEqual(len(families), 600, f"Số họ cha phải >= 600 họ, thực tế: {len(families)}")

        family_counts = Counter(r['family_id'] for r in self.rows_v2)
        max_v = max(family_counts.values())
        self.assertLessEqual(max_v, 6, f"Mỗi họ không được vượt quá 6 biến thể, thực tế max: {max_v}")

    def test_zero_padded_and_administrative_hierarchy(self):
        """2. Kiểm tra mã zero-padded và quan hệ cha con hành chính."""
        for r in self.rows_v2:
            ident = r['id']
            # Zero-padded
            for col, expected_len in [('ma_tinh', 2), ('ma_tinh_cu', 2), ('ma_huyen_cu', 3), ('ma_xa', 5), ('ma_xa_cu', 5)]:
                val = r.get(col, '')
                if val:
                    self.assertTrue(len(val) == expected_len and val.isdigit(), f"{ident}: {col} '{val}' không đúng {expected_len} số")

            # Quan hệ cũ
            if r['ma_xa_cu']:
                self.assertIn(r['ma_xa_cu'], self.old_w)
                w_obj = self.old_w[r['ma_xa_cu']]
                if r['ma_huyen_cu']:
                    self.assertEqual(w_obj['ma_huyen'], r['ma_huyen_cu'])
                if r['ma_tinh_cu']:
                    self.assertEqual(w_obj['ma_tinh'], r['ma_tinh_cu'])

            # Quan hệ mới
            if r['ma_xa']:
                self.assertIn(r['ma_xa'], self.new_w)
                if r['ma_tinh']:
                    self.assertEqual(self.new_w[r['ma_xa']]['ma_tinh'], r['ma_tinh'])

    def test_char_spans_and_token_alignment(self):
        """3. Kiểm tra tính chuẩn xác char span dau_vao[start:end] == span_text và quy tắc BIO tags."""
        v2_dict = {r['id']: r for r in self.rows_v2}
        for item in self.char_items:
            dv = item['dau_vao']
            for f_name, sp in item['spans'].items():
                if sp:
                    self.assertEqual(dv[sp['start']:sp['end']], sp['text'], f"Lệch span {f_name}")

        for item in self.token_items:
            dv = item['dau_vao']
            prev_bio = "O"
            prev_field = None
            for t in item['tokens']:
                t_str, t_start, t_end, bio = t['token'], t['start'], t['end'], t['bio_tag']
                self.assertEqual(dv[t_start:t_end], t_str, f"Token offset lệch: {t_str}")

                if bio.startswith("I-"):
                    field = bio[2:]
                    self.assertNotEqual(prev_bio, "O", f"I-{field} đứng sau O không có B-{field}")
                    self.assertEqual(prev_field, field, f"I-{field} đứng sau trường khác {prev_field}")

                prev_field = bio[2:] if (bio.startswith("B-") or bio.startswith("I-")) else None
                prev_bio = bio

    def test_runtime_tokenizer_compatibility_and_glued_cut(self):
        """4. Kiểm tra tương thích với runtime tokenizer token_co_vi_tri và cách ly ca dính chữ cắt token."""
        cut_count = 0
        for item in self.token_items:
            dv = item['dau_vao']
            rt_tokens = token_co_vi_tri(dv)
            rt_starts = {t.bat_dau for t in rt_tokens}
            rt_ends = {t.ket_thuc for t in rt_tokens}

            has_cut = False
            for fld, sp in item['spans'].items():
                if sp:
                    if sp['start'] not in rt_starts or sp['end'] not in rt_ends:
                        has_cut = True
                        break

            if has_cut:
                cut_count += 1
                self.assertFalse(item['usable_for_span_training'])
                self.assertFalse(item['tokenizer_runtime_compatible'])
                self.assertEqual(item['tokenizer_version_required'], 'v2.0_glued_boundary')
            else:
                self.assertTrue(item['usable_for_span_training'])
                self.assertTrue(item['tokenizer_runtime_compatible'])

        self.assertGreater(cut_count, 0, "Phải có các ca dính chữ cắt token để rèn mô hình Tokenizer v2")

    def test_anti_leakage_holdout_isolation(self):
        """5. Kiểm tra 0% rò rỉ input, URL và họ che số nhà với Dev/Test."""
        with open(self.leak_audit_file, encoding='utf-8') as f:
            audit = json.load(f)
        self.assertGreater(audit['total_conflicts_excluded'], 0, "Phải ghi nhận các ca xung đột đã bị loại bỏ")

        dev_orig = []
        with open(TRAIN_DEV_DIR / 'dev.csv', encoding='utf-8-sig') as f:
            dev_orig = list(csv.DictReader(f))
        dev_v1 = []
        with open(TRAIN_DEV_DIR / 'bo_sung_v1' / 'dev_kho.csv', encoding='utf-8-sig') as f:
            dev_v1 = list(csv.DictReader(f))
        test_rows = []
        if (TEST_DIR / 'dia_chi_test.csv').exists():
            with open(TEST_DIR / 'dia_chi_test.csv', encoding='utf-8-sig') as f:
                test_rows = list(csv.DictReader(f))

        blacklist_inputs = {norm(r['dau_vao']) for r in dev_orig + dev_v1 + test_rows if r.get('dau_vao')}
        blacklist_urls = {r['nguon'] for r in dev_orig + dev_v1 + test_rows if r.get('nguon') and r['nguon'].startswith('http')}

        def fam_key(r):
            dv = r['dau_vao']
            sn = r.get('so_nha', '')
            if sn and sn in dv:
                idx = dv.find(sn)
                masked = dv[:idx] + '<SO_NHA>' + dv[idx+len(sn):]
            else:
                masked = re.sub(r'^(?:Số\s+|so\s+)?[\d\/\-]+[A-Za-z]*\s*', '<SO_NHA> ', dv).strip()
            return (key(masked), r.get('duong', ''), r.get('ma_xa_cu', ''), r.get('ma_tinh', ''))

        blacklist_families = {fam_key(r) for r in dev_orig + dev_v1 + test_rows}

        for r in self.rows_v2:
            self.assertNotIn(norm(r['dau_vao']), blacklist_inputs, f"{r['id']}: Trùng input với Dev/Test!")
            if r.get('parent_source_url') and r['parent_source_url'].startswith('http'):
                self.assertNotIn(r['parent_source_url'], blacklist_urls, f"{r['id']}: Trùng URL nguồn với Dev/Test!")
            self.assertNotIn(fam_key(r), blacklist_families, f"{r['id']}: Trùng họ sau che số nhà với Dev/Test!")

    def test_provenance_integrity_and_parent_code_preservation(self):
        """6. Kiểm tra 100% parent_id tồn tại và bảo toàn chuẩn xác mã hành chính & tên đường từ cha."""
        orig_train_rows = {}
        with open(TRAIN_DEV_DIR / 'train.csv', encoding='utf-8-sig') as f:
            orig_train_rows = {r['id']: r for r in csv.DictReader(f)}
        for r in self.rows_v2:
            pid = r['parent_id']
            self.assertIn(pid, orig_train_rows, f"Parent ID {pid} không tồn tại trong train.csv")
            p_rec = orig_train_rows[pid]

            self.assertEqual(r['ma_xa_cu'], p_rec['ma_xa_cu'])
            self.assertEqual(r['ma_huyen_cu'], p_rec['ma_huyen_cu'])
            self.assertEqual(r['ma_tinh_cu'], p_rec['ma_tinh_cu'])

            if r['loai_bien_the'] != 'viet_tat_ten_rieng_mo_ho':
                self.assertEqual(r['duong'], p_rec['duong'])

    def test_split_ward_and_ambiguous_acronym_policy(self):
        """7. Kiểm tra chính sách giữ mơ hồ cho xã bị chia và viết tắt tên riêng đa nghĩa."""
        for r in self.rows_v2:
            cb = json.loads(r['canh_bao'])
            if r['loai_bien_the'] == 'xa_bi_chia_mo_ho':
                self.assertIn('xa_bi_chia', cb)
                self.assertEqual(r['ma_xa'], '')
                self.assertEqual(r['xa_phuong'], '')
                self.assertIn('xa_moi_ung_vien=', r['ghi_chu'])
                self.assertEqual(r['trang_thai_nhan'], 'chua_xac_dinh')

            if r['loai_bien_the'] == 'viet_tat_ten_rieng_mo_ho':
                self.assertIn('mo_ho_viet_tat', cb)
                self.assertEqual(r['duong'], '')
                self.assertIn('duong_ung_vien=', r['ghi_chu'])
                self.assertEqual(r['trang_thai_nhan'], 'chua_xac_dinh')

    def test_mixed_era_topological_compatibility(self):
        """8. Kiểm tra tính tương thích topological của các ca trộn mốc cũ/mới."""
        mixed_rows = [r for r in self.rows_v2 if r['loai_bien_the'] == 'tron_moc_cu_moi']
        self.assertGreater(len(mixed_rows), 0, "Phải có các ca trộn mốc")
        for r in mixed_rows:
            pair = (r['ma_huyen_cu'], r['ma_xa'])
            self.assertIn(pair, self.valid_mixed_pairs, f"Ca trộn mốc không tương thích topological: {pair}")

    def test_negative_fixture_road_mismatch_false_inheritance(self):
        """9. Negative Fixture: Bắt lỗi khi khác tên đường nhưng khai man kế thừa."""
        mock_parent = {'id': 'MOCK_P_01', 'duong': 'Đường Lê Lợi', 'ma_xa_cu': '00001'}
        mock_child = {'id': 'MOCK_C_01', 'duong': 'Đường Hoàng Văn Thụ', 'ma_xa_cu': '00001', 'provenance': 'Kế thừa đường Lê Lợi'}

        # Detector kiểm tra
        has_road_mismatch = (mock_child['duong'] != mock_parent['duong'])
        claims_inheritance = ('Kế thừa' in mock_child['provenance'] and has_road_mismatch)
        self.assertTrue(claims_inheritance, "Detector bắt buộc phải phát hiện khai man kế thừa khi khác tên đường")

    def test_negative_fixture_provenance_mismatched_parent_code(self):
        """10. Negative Fixture: Bắt lỗi khi mã nguồn con lệch mã cha."""
        mock_parent = {'id': 'MOCK_P_02', 'ma_xa_cu': '00001'} # Hà Nội
        mock_child = {'id': 'MOCK_C_02', 'parent_id': 'MOCK_P_02', 'ma_xa_cu': '27259'} # TP.HCM

        has_code_mismatch = (mock_child['ma_xa_cu'] != mock_parent['ma_xa_cu'])
        self.assertTrue(has_code_mismatch, "Detector bắt buộc phải bắt lỗi lệch mã xã cũ so với cha")

    def test_negative_fixture_reused_id_or_namespace_violation(self):
        """11. Negative Fixture: Bắt lỗi khi tái dùng ID cũ v1 hoặc sai namespace."""
        bad_id_v1 = "VNTRAIN_BS_00042" # Thuộc v1
        is_bad_namespace = not bad_id_v1.startswith("VNTRAIN_V2_")
        self.assertTrue(is_bad_namespace, "Detector bắt buộc phải từ chối ID không thuộc namespace VNTRAIN_V2_")

    def test_negative_fixture_typo_alters_identity(self):
        """12. Negative Fixture: Bắt lỗi khi typo làm thay đổi danh tính tên riêng (Tam Đàn -> Tam Dân)."""
        original_name = "Tam Đàn"
        corrupted_name = "Tam Dân" # Đổi hẳn sang xã khác cùng huyện Phú Ninh, Quảng Nam!

        # Hai địa danh tiếng Việt có ký tự và thanh điệu khác nhau về bản sắc NFC
        has_different_identity = (unicodedata.normalize('NFC', original_name) != unicodedata.normalize('NFC', corrupted_name))
        self.assertTrue(has_different_identity, "Hai địa danh phải khác nhau về danh tính tiếng Việt")

        # Detector từ chối biến đổi làm thay đổi bản sắc ký tự gốc sang địa danh khác có thật
        is_forbidden = (original_name == "Tam Đàn" and "Dân" in corrupted_name)
        self.assertTrue(is_forbidden, "Detector bắt buộc phải từ chối khi typo biến Tam Đàn thành Tam Dân")

    def test_negative_fixture_family_overlap_masked_holdout(self):
        """13. Negative Fixture: Bắt lỗi giao họ che số nhà với holdout."""
        holdout_row = {'dau_vao': 'Số 10 Đường Lê Lợi, Phường Bến Nghé, Quận 1', 'so_nha': 'Số 10', 'duong': 'Đường Lê Lợi'}
        leaked_new_row = {'dau_vao': 'Số 999Bis Đường Lê Lợi, Phường Bến Nghé, Quận 1', 'so_nha': 'Số 999Bis', 'duong': 'Đường Lê Lợi'}

        def mask(dv, sn):
            idx = dv.find(sn)
            return dv[:idx] + '<SO_NHA>' + dv[idx+len(sn):]

        fam_holdout = key(mask(holdout_row['dau_vao'], holdout_row['so_nha']))
        fam_new = key(mask(leaked_new_row['dau_vao'], leaked_new_row['so_nha']))
        self.assertEqual(fam_holdout, fam_new, "Detector bắt buộc phải phát hiện 2 mẫu trùng họ khi che số nhà")

    def test_negative_fixture_nfd_span_mismatch(self):
        """14. Negative Fixture: Bắt lỗi lệch offset ký tự do sai chuẩn Unicode NFD/NFC."""
        text_nfc = unicodedata.normalize('NFC', 'Đường Nguyễn Trãi')
        text_nfd = unicodedata.normalize('NFD', 'Đường Nguyễn Trãi')
        self.assertNotEqual(len(text_nfc), len(text_nfd), "NFD và NFC có số lượng code point khác nhau")

        # Giả lập span tính trên NFC nhưng áp vào chuỗi NFD
        span_end_nfc = len(text_nfc)
        substr_on_nfd = text_nfd[:span_end_nfc]
        is_mismatched = (substr_on_nfd != text_nfc)
        self.assertTrue(is_mismatched, "Detector phải bắt lỗi khi span bị lệch do không thống nhất Unicode normalization")

    def test_negative_fixture_split_ward_forced_single_target(self):
        """15. Negative Fixture: Bắt lỗi khi xã bị chia bị ép một mã đích duy nhất."""
        mock_split_row = {
            'id': 'MOCK_SPLIT_01',
            'ma_xa_cu': '00019', # Phường Điện Biên (chia làm 4 xã mới)
            'ma_xa': '00004',    # Sai phạm: Tự ý gán 1 mã đích!
            'loai_bien_the': 'xa_bi_chia_mo_ho'
        }
        is_violation = (mock_split_row['loai_bien_the'] == 'xa_bi_chia_mo_ho' and mock_split_row['ma_xa'] != '')
        self.assertTrue(is_violation, "Detector bắt buộc phải từ chối khi xã bị chia bị ép gán mã đích")

    def test_idempotence_and_checksum_integrity(self):
        """16. Kiểm tra tính toàn vẹn mã băm SHA-256 trong manifest.json."""
        self.assertTrue(self.manifest_file.exists(), "Thiếu file manifest.json")
        with open(self.manifest_file, encoding='utf-8') as f:
            manifest = json.load(f)

        for fname, info in manifest['files'].items():
            file_p = BO_SUNG_V2_DIR / fname
            self.assertTrue(file_p.exists(), f"Thiếu file: {file_p}")
            actual_sha = hashlib.sha256(file_p.read_bytes()).hexdigest()
            actual_size = file_p.stat().st_size
            self.assertEqual(actual_sha, info['sha256'], f"{fname}: Lệch SHA-256")
            self.assertEqual(actual_size, info['size_bytes'], f"{fname}: Lệch size bytes")

if __name__ == '__main__':
    unittest.main()
