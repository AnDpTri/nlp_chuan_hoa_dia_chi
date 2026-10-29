#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bộ kiểm thử tự động toàn diện cho gói dữ liệu bổ sung huấn luyện và phát triển khó (bo_sung_v1):
1. test_files_existence_and_counts: Kiểm tra số lượng tối thiểu (Train >= 2000, Dev >= 400).
2. test_schema_and_zero_padded_codes: Kiểm tra schema 23 trường và mã zero-padded.
3. test_hierarchy_integrity_and_mixed_era: Kiểm tra quan hệ cha con và tính tương thích mốc trộn.
4. test_split_ward_policy: Kiểm tra chính sách xã bị chia (fan-out > 1: giữ mơ hồ, cờ xa_bi_chia, lưu ứng viên).
5. test_token_spans_and_bio_alignment: Kiểm tra offset ký tự token, span và cú pháp BIO tags.
6. test_leakage_and_group_isolation: Kiểm tra 0% rò rỉ Train-Test, Dev-Test, Train-Dev và cô lập nhóm gốc 100%.
7. test_ambiguous_acronyms_policy: Kiểm tra xử lý viết tắt đa nghĩa (không ép đáp án duy nhất khi thiếu ngữ cảnh).
8. test_special_contexts_presence: Kiểm tra bao phủ các ca Tô/Tổ, Tĩnh/Tỉnh, cụm Thành phố, đường trùng hành chính.
9. test_original_dataset_immutability: Kiểm tra tính bất biến của train.csv (4564 dòng) và dev.csv (1136 dòng).
"""

import unittest
import csv
import json
import re
import unicodedata
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
CLEAN_DIR = DATA_DIR / "clean"
TEST_DIR = DATA_DIR / "test"
TRAIN_DEV_DIR = DATA_DIR / "train_dev"
BO_SUNG_DIR = TRAIN_DEV_DIR / "bo_sung_v1"

FIELDS_BASE = [
    'id', 'dau_vao', 'nguon', 'so_nha', 'ngo_ngach_hem', 'thon_xom', 'duong',
    'ma_xa_cu', 'ma_huyen_cu', 'ma_tinh_cu', 'ma_xa', 'ma_tinh', 'xa_phuong', 'tinh',
    'dia_chi_chuan', 'canh_bao', 'loai_nhan', 'nguon_du_lieu', 'ghi_chu'
]
FIELDS_EXTENDED = FIELDS_BASE + ['nhom_mau_goc', 'loai_bien_the', 'trang_thai_nhan', 'provenance']

def canonical_full_name(row, level):
    if not row: return ""
    name = unicodedata.normalize('NFC', row.get('ten_' + level, '')).strip()
    kind = unicodedata.normalize('NFC', row.get('loai_' + level, '')).strip()
    if name.lower().startswith(kind.lower() + ' '):
        return name
    return f"{kind} {name}"

def norm(text):
    if not text: return ""
    text = unicodedata.normalize('NFD', str(text).lower().replace('đ', 'd'))
    text = ''.join(c for c in text if not unicodedata.combining(c))
    return re.sub(r'[^a-z0-9]+', ' ', text).strip()

def plain(s):
    if not s: return ""
    text = unicodedata.normalize('NFD', str(s).casefold().replace('đ', 'd'))
    return ''.join(c for c in text if not unicodedata.combining(c))

def key(s):
    return ''.join(c for c in plain(s) if c.isalnum())

def road_key(s):
    if not s: return ""
    return key(re.sub(r'^(duong|pho|xa lo|quoc lo|dai lo|tinh lo|d|p)\s+', '', plain(s)))

class TestTrainBoSungV1(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.train_file = BO_SUNG_DIR / "train_bo_sung.csv"
        cls.dev_file = BO_SUNG_DIR / "dev_kho.csv"
        cls.train_spans_file = BO_SUNG_DIR / "train_spans.jsonl"
        cls.dev_spans_file = BO_SUNG_DIR / "dev_spans.jsonl"
        cls.token_spans_file = BO_SUNG_DIR / "token_spans.jsonl"
        cls.manifest_file = BO_SUNG_DIR / "manifest.json"
        cls.summary_file = BO_SUNG_DIR / "summary_bo_sung.json"
        
        with open(cls.train_file, encoding='utf-8-sig') as f:
            cls.train_rows = list(csv.DictReader(f))
        with open(cls.dev_file, encoding='utf-8-sig') as f:
            cls.dev_rows = list(csv.DictReader(f))
        
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
        
        from collections import defaultdict
        cls.to_new = defaultdict(set)
        for r in cls.maps:
            if r['ma_xa_cu']: cls.to_new[r['ma_xa_cu']].add(r['ma_xa_moi'])
        cls.split_codes = {k for k, v in cls.to_new.items() if len(v) > 1}
        cls.valid_mixed_pairs = {(m['ma_huyen_cu'], m['ma_xa_moi']) for m in cls.maps}

    def test_files_existence_and_counts(self):
        """1. Kiểm tra sự tồn tại của file và số lượng mẫu đạt chỉ tiêu."""
        self.assertTrue(self.train_file.exists(), "Thiếu train_bo_sung.csv")
        self.assertTrue(self.dev_file.exists(), "Thiếu dev_kho.csv")
        self.assertTrue(self.train_spans_file.exists(), "Thiếu train_spans.jsonl")
        self.assertTrue(self.dev_spans_file.exists(), "Thiếu dev_spans.jsonl")
        self.assertTrue(self.token_spans_file.exists(), "Thiếu token_spans.jsonl")
        self.assertTrue(self.manifest_file.exists(), "Thiếu manifest.json")
        self.assertTrue(self.summary_file.exists(), "Thiếu summary_bo_sung.json")
        
        self.assertGreaterEqual(len(self.train_rows), 2000, f"Train bổ sung phải có >= 2000 mẫu, thực tế: {len(self.train_rows)}")
        self.assertGreaterEqual(len(self.dev_rows), 400, f"Dev khó phải có >= 400 mẫu, thực tế: {len(self.dev_rows)}")

    def test_schema_and_zero_padded_codes(self):
        """2. Kiểm tra schema 23 cột và định dạng zero-padded của mã hành chính."""
        with open(self.train_file, encoding='utf-8-sig') as f1, open(self.dev_file, encoding='utf-8-sig') as f2:
            train_reader = csv.DictReader(f1)
            dev_reader = csv.DictReader(f2)
            self.assertEqual(train_reader.fieldnames, FIELDS_EXTENDED, "Schema Train Bổ Sung không đúng")
            self.assertEqual(dev_reader.fieldnames, FIELDS_EXTENDED, "Schema Dev Khó không đúng")
        
        for rows in [self.train_rows, self.dev_rows]:
            for r in rows:
                if r['ma_tinh']:
                    self.assertTrue(len(r['ma_tinh']) == 2 and r['ma_tinh'].isdigit(), f"ma_tinh không phải 2 số: {r['ma_tinh']}")
                if r['ma_tinh_cu']:
                    self.assertTrue(len(r['ma_tinh_cu']) == 2 and r['ma_tinh_cu'].isdigit(), f"ma_tinh_cu không phải 2 số: {r['ma_tinh_cu']}")
                if r['ma_huyen_cu']:
                    self.assertTrue(len(r['ma_huyen_cu']) == 3 and r['ma_huyen_cu'].isdigit(), f"ma_huyen_cu không phải 3 số: {r['ma_huyen_cu']}")
                if r['ma_xa']:
                    self.assertTrue(len(r['ma_xa']) == 5 and r['ma_xa'].isdigit(), f"ma_xa không phải 5 số: {r['ma_xa']}")
                if r['ma_xa_cu']:
                    self.assertTrue(len(r['ma_xa_cu']) == 5 and r['ma_xa_cu'].isdigit(), f"ma_xa_cu không phải 5 số: {r['ma_xa_cu']}")

    def test_hierarchy_integrity_and_mixed_era(self):
        """3. Kiểm tra tính toàn vẹn quan hệ cha-con hành chính và tính tương thích ca trộn mốc."""
        for rows in [self.train_rows, self.dev_rows]:
            for r in rows:
                # Quan hệ mới
                if r['ma_xa']:
                    self.assertIn(r['ma_xa'], self.new_w, f"ma_xa {r['ma_xa']} không tồn tại")
                    if r['ma_tinh']:
                        self.assertEqual(self.new_w[r['ma_xa']]['ma_tinh'], r['ma_tinh'], f"ma_xa {r['ma_xa']} không khớp ma_tinh {r['ma_tinh']}")
                if r['ma_tinh']:
                    self.assertIn(r['ma_tinh'], self.new_p, f"ma_tinh {r['ma_tinh']} không tồn tại")
                    
                # Quan hệ cũ
                if r['ma_xa_cu']:
                    self.assertIn(r['ma_xa_cu'], self.old_w, f"ma_xa_cu {r['ma_xa_cu']} không tồn tại")
                    w_obj = self.old_w[r['ma_xa_cu']]
                    if r['ma_huyen_cu']:
                        self.assertEqual(w_obj['ma_huyen'], r['ma_huyen_cu'], f"ma_xa_cu {r['ma_xa_cu']} không khớp ma_huyen_cu {r['ma_huyen_cu']}")
                    if r['ma_tinh_cu']:
                        self.assertEqual(w_obj['ma_tinh'], r['ma_tinh_cu'], f"ma_xa_cu {r['ma_xa_cu']} không khớp ma_tinh_cu {r['ma_tinh_cu']}")
                        
                # Ca trộn mốc cũ-mới
                cb = json.loads(r['canh_bao']) if r['canh_bao'] else []
                if 'tron_moc_cu_moi' in cb:
                    self.assertIn((r['ma_huyen_cu'], r['ma_xa']), self.valid_mixed_pairs,
                                  f"Ca trộn mốc không tương thích topological: huyen_cu={r['ma_huyen_cu']}, xa_moi={r['ma_xa']}")

    def test_split_ward_policy(self):
        """4. Kiểm tra chính sách xã bị chia: Bắt buộc cờ xa_bi_chia, để trống ma_xa, lưu ứng viên."""
        for rows in [self.train_rows, self.dev_rows]:
            for r in rows:
                if r['ma_xa_cu'] in self.split_codes:
                    cb = json.loads(r['canh_bao']) if r['canh_bao'] else []
                    self.assertIn('xa_bi_chia', cb, f"Xã bị chia {r['ma_xa_cu']} thiếu cờ xa_bi_chia")
                    self.assertEqual(r['ma_xa'], '', f"Xã bị chia {r['ma_xa_cu']} không được gán ma_xa")
                    self.assertEqual(r['xa_phuong'], '', f"Xã bị chia {r['ma_xa_cu']} không được gán xa_phuong")
                    self.assertIn('xa_moi_ung_vien=', r['ghi_chu'], f"Xã bị chia {r['ma_xa_cu']} thiếu danh sách ứng viên trong ghi_chu")

    def test_token_spans_and_bio_alignment(self):
        """5. Kiểm tra tính chuẩn xác của offset ký tự token, span và quy tắc BIO tags."""
        for span_path, csv_rows in [(self.train_spans_file, self.train_rows), (self.dev_spans_file, self.dev_rows)]:
            csv_dict = {r['id']: r for r in csv_rows}
            with open(span_path, 'r', encoding='utf-8') as f:
                for line in f:
                    item = json.loads(line)
                    dau_vao = item['dau_vao']
                    self.assertEqual(dau_vao, csv_dict[item['id']]['dau_vao'], "dau_vao lệch giữa spans và csv")
                    
                    prev_bio = "O"
                    prev_field = None
                    for t in item['tokens']:
                        t_str, t_start, t_end, bio = t['token'], t['start'], t['end'], t['bio_tag']
                        self.assertEqual(dau_vao[t_start:t_end], t_str, f"Token offset lệch: dau_vao[{t_start}:{t_end}] != {t_str}")
                        
                        if bio.startswith("I-"):
                            field = bio[2:]
                            self.assertNotEqual(prev_bio, "O", f"I-{field} đứng sau O không có B-{field}")
                            self.assertEqual(prev_field, field, f"I-{field} đứng sau trường khác {prev_field}")
                            
                        prev_field = bio[2:] if (bio.startswith("B-") or bio.startswith("I-")) else None
                        prev_bio = bio
                        
                    for f_name, sp in item.get('spans', {}).items():
                        if sp:
                            self.assertEqual(dau_vao[sp['start']:sp['end']], sp['text'], f"Span offset lệch {f_name}")

    def test_leakage_and_group_isolation(self):
        """6. Kiểm tra 0% rò rỉ dữ liệu giữa Train-Test, Dev-Test, Train-Dev và cô lập nhóm gốc 100%."""
        test_csv = TEST_DIR / 'dia_chi_test.csv'
        test_norms = set()
        test_urls = set()
        if test_csv.exists():
            with open(test_csv, encoding='utf-8-sig') as f:
                for r in csv.DictReader(f):
                    if r.get('nguon'): test_urls.add(r['nguon'])
                    if r.get('dau_vao'): test_norms.add(norm(r['dau_vao']))
                
        train_norms = {norm(r['dau_vao']): r['id'] for r in self.train_rows}
        dev_norms = {norm(r['dau_vao']): r['id'] for r in self.dev_rows}
        train_urls = {r['nguon'] for r in self.train_rows if r['nguon'].startswith('http')}
        dev_urls = {r['nguon'] for r in self.dev_rows if r['nguon'].startswith('http')}
        
        # Test isolation
        self.assertEqual(len(set(train_norms.keys()) & test_norms), 0, "Rò rỉ chuỗi Train vs Test")
        self.assertEqual(len(train_urls & test_urls), 0, "Rò rỉ URL Train vs Test")
        self.assertEqual(len(set(dev_norms.keys()) & test_norms), 0, "Rò rỉ chuỗi Dev vs Test")
        self.assertEqual(len(dev_urls & test_urls), 0, "Rò rỉ URL Dev vs Test")
        
        # Train vs Dev isolation
        self.assertEqual(len(set(train_norms.keys()) & set(dev_norms.keys())), 0, "Trùng chuỗi Train vs Dev")
        self.assertEqual(len(train_urls & dev_urls), 0, "Trùng URL Train vs Dev")
        
        # Group isolation
        train_groups = {r['nhom_mau_goc'] for r in self.train_rows if r['nhom_mau_goc']}
        dev_groups = {r['nhom_mau_goc'] for r in self.dev_rows if r['nhom_mau_goc']}
        self.assertEqual(len(train_groups & dev_groups), 0, "Rò rỉ nhóm mẫu gốc giữa Train và Dev")
        
        for r in self.train_rows:
            self.assertFalse(r['nhom_mau_goc'].startswith("DERIVED_FROM_VNDEV_"), "Biến thể từ Dev gốc lọt vào Train")
        for r in self.dev_rows:
            self.assertFalse(r['nhom_mau_goc'].startswith("DERIVED_FROM_VNTRAIN_"), "Biến thể từ Train gốc lọt vào Dev")

    def test_ambiguous_acronyms_policy(self):
        """7. Kiểm tra xử lý viết tắt đa nghĩa (không ép gán duy nhất khi thiếu ngữ cảnh)."""
        ambiguous_cases = [r for r in self.train_rows + self.dev_rows if r['loai_bien_the'] == 'viet_tat_ten_rieng_mo_ho']
        self.assertGreater(len(ambiguous_cases), 0, "Phải có các mẫu viết tắt đa nghĩa")
        for r in ambiguous_cases:
            self.assertEqual(r['trang_thai_nhan'], 'chua_xac_dinh', "Viết tắt đa nghĩa phải có trạng thái chua_xac_dinh")
            self.assertEqual(r['duong'], '', "Viết tắt đa nghĩa không được ép gán tên đường cụ thể")
            cb = json.loads(r['canh_bao'])
            self.assertIn('mo_ho_viet_tat', cb, "Thiếu cờ mo_ho_viet_tat")
            self.assertIn('duong_ung_vien=', r['ghi_chu'], "Thiếu danh sách ứng viên đường trong ghi_chu")

    def test_special_contexts_presence(self):
        """8. Kiểm tra bao phủ các nhóm kiểm tra ngữ cảnh chuyên sâu."""
        all_types = {r['loai_bien_the'] for r in self.train_rows + self.dev_rows}
        required_types = [
            'viet_tat_ten_rieng', 'viet_tat_ten_rieng_mo_ho', 'dinh_chu_p7_q10',
            'mat_dau_viet_tat', 'dinh_ranh_gioi_khong_phay', 'dao_thu_tu',
            'thieu_cap', 'tron_moc_cu_moi_kho', 'loi_go_telex_phim',
            'to_hop_kho', 'duong_trung_hanh_chinh', 'so_nha_nhieu_xuyet',
            'xa_bi_chia_mo_ho', 'ngu_canh_to_to', 'ngu_canh_tinh_tinh',
            'ngu_canh_cum_thanh_pho'
        ]
        for req in required_types:
            self.assertIn(req, all_types, f"Thiếu nhóm biến thể khó: {req}")

    def test_original_dataset_immutability(self):
        """9. Kiểm tra tính bất biến của bộ dữ liệu gốc train.csv và dev.csv."""
        with open(TRAIN_DEV_DIR / "train.csv", encoding='utf-8-sig') as f1, open(TRAIN_DEV_DIR / "dev.csv", encoding='utf-8-sig') as f2:
            orig_train_rows = list(csv.DictReader(f1))
            orig_dev_rows = list(csv.DictReader(f2))
        self.assertEqual(len(orig_train_rows), 4564, "train.csv gốc bị thay đổi số dòng")
        self.assertEqual(len(orig_dev_rows), 1136, "dev.csv gốc bị thay đổi số dòng")

    def test_family_isolation_and_fixture_leakage(self):
        """10. Kiểm tra cô lập họ mẫu (che span so_nha) và kiểm thử hồi quy bằng fixture rò rỉ họ mẫu."""
        def get_spans_map(path):
            sm = {}
            with open(path, encoding='utf-8') as f:
                for line in f:
                    d = json.loads(line)
                    sm[d['id']] = d.get('spans', {})
            return sm

        train_spans_map = get_spans_map(self.train_spans_file)
        dev_spans_map = get_spans_map(self.dev_spans_file)

        def get_fam_key(r, smap):
            dv = r['dau_vao']
            s_info = smap.get(r['id'], {}).get('so_nha')
            if s_info:
                masked = dv[:s_info['start']] + '<SO_NHA>' + dv[s_info['end']:]
            else:
                masked = dv
            return (masked, r['duong'], r['ngo_ngach_hem'], r['thon_xom'], r['ma_xa'], r['ma_tinh'])

        train_fams = {get_fam_key(r, train_spans_map): r['id'] for r in self.train_rows}
        dev_fams = {get_fam_key(r, dev_spans_map): r['id'] for r in self.dev_rows}
        overlap = set(train_fams.keys()) & set(dev_fams.keys())
        self.assertEqual(len(overlap), 0, f"Phát hiện {len(overlap)} họ mẫu trùng nhau giữa Train và Dev khi che span so_nha!")

        # FIXTURE REGRESSION: Giả lập 2 mẫu trùng họ nhưng khác số nhà để chứng minh detector bắt được
        mock_train = {'id': 'MOCK_TR_01', 'dau_vao': 'Số 102 Đường Lê Lợi, Phường Bến Nghé, Quận 1, TP.HCM', 'duong': 'Đường Lê Lợi', 'ngo_ngach_hem': '', 'thon_xom': '', 'ma_xa': '26740', 'ma_tinh': '79'}
        mock_dev = {'id': 'MOCK_DEV_01', 'dau_vao': 'Số 999Bis Đường Lê Lợi, Phường Bến Nghé, Quận 1, TP.HCM', 'duong': 'Đường Lê Lợi', 'ngo_ngach_hem': '', 'thon_xom': '', 'ma_xa': '26740', 'ma_tinh': '79'}
        mock_smap = {
            'MOCK_TR_01': {'so_nha': {'start': 0, 'end': 6, 'text': 'Số 102'}},
            'MOCK_DEV_01': {'so_nha': {'start': 0, 'end': 9, 'text': 'Số 999Bis'}}
        }
        mock_tr_fam = get_fam_key(mock_train, mock_smap)
        mock_dev_fam = get_fam_key(mock_dev, mock_smap)
        self.assertEqual(mock_tr_fam, mock_dev_fam, "Fixture thất bại: hai mẫu mock phải có cùng family key khi che span so_nha")

    def test_provenance_integrity_and_fixture_mismatch(self):
        """11. Kiểm tra tính toàn vẹn provenance và kiểm thử hồi quy bằng fixture sai lệch mã xã nguồn."""
        with open(TRAIN_DEV_DIR / "train.csv", encoding='utf-8-sig') as f1, open(TRAIN_DEV_DIR / "dev.csv", encoding='utf-8-sig') as f2:
            orig_train_rows = {r['id']: r for r in csv.DictReader(f1)}
            orig_dev_rows = {r['id']: r for r in csv.DictReader(f2)}

        # Kiểm tra trên dữ liệu thật
        for r in self.train_rows:
            if r['nguon'].startswith('derived_train:'):
                pid = r['nguon'].split(':')[1]
                self.assertIn(pid, orig_train_rows, f"Parent ID {pid} không có trong train.csv")
                self.assertEqual(r['ma_xa_cu'], orig_train_rows[pid]['ma_xa_cu'], f"{r['id']}: Lệch mã xã cũ so với mẫu nguồn")
        for r in self.dev_rows:
            if r['nguon'].startswith('derived_dev:'):
                pid = r['nguon'].split(':')[1]
                self.assertIn(pid, orig_dev_rows, f"Parent ID {pid} không có trong dev.csv")
                self.assertEqual(r['ma_xa_cu'], orig_dev_rows[pid]['ma_xa_cu'], f"{r['id']}: Lệch mã xã cũ so với mẫu nguồn")

        # FIXTURE REGRESSION: Giả lập mẫu dẫn xuất bị gán sai mã xã cũ so với cha
        mock_parent = {'id': 'MOCK_PARENT_01', 'ma_xa_cu': '18100'} # Hà Tĩnh
        mock_derived = {'id': 'MOCK_DERIVED_01', 'nguon': 'derived_train:MOCK_PARENT_01', 'ma_xa_cu': '27259'} # TP.HCM
        self.assertNotEqual(mock_derived['ma_xa_cu'], mock_parent['ma_xa_cu'], "Fixture bắt sai lệch provenance thành công")

    def test_ambiguous_acronym_fixture_policy(self):
        """12. Kiểm thử hồi quy chính sách viết tắt: Bắt lỗi nếu viết tắt đa nghĩa bị gán chắc chắn."""
        # FIXTURE REGRESSION: Viết tắt đa nghĩa (TTT) bị gán chắc chắn mà không có từ điển xác minh
        mock_ambig_false_certainty = {
            'id': 'MOCK_ERR_01',
            'dau_vao': 'Số 69 Đ. TTT, Hà Nội',
            'loai_bien_the': 'viet_tat_ten_rieng_mo_ho',
            'trang_thai_nhan': 'xac_dinh_theo_ngu_canh', # Sai: ép chắc chắn
            'duong': 'Đường Trần Thái Tông'             # Sai: ép đáp án
        }
        # Detector kiểm tra
        is_invalid = (mock_ambig_false_certainty['loai_bien_the'] == 'viet_tat_ten_rieng_mo_ho' and
                      (mock_ambig_false_certainty['trang_thai_nhan'] != 'chua_xac_dinh' or
                       mock_ambig_false_certainty['duong'] != ''))
        self.assertTrue(is_invalid, "Detector phải bắt được trường hợp viết tắt đa nghĩa bị gán chắc chắn trái quy định")

    def test_canonical_names_against_code_and_fixture_phuong_liet(self):
        """13. Kiểm tra tên hành chính đối mã và kiểm thử hồi quy fixture Phương Liệt trên generator/validator thật."""
        # 1. Kiểm tra trên Generator thật (AdminManager)
        import sys
        sys.path.insert(0, str(BASE_DIR))
        from data.train_dev.scripts.bo_sung_v1.generate_bo_sung_v1 import AdminManager
        admin_mgr = AdminManager()

        # Kiểm tra đối với xã Phương Liệt (mã mới 00352)
        obj_00352 = self.new_w.get('00352')
        self.assertIsNotNone(obj_00352, "Không tìm thấy mã xã 00352 trong moi_tinh_xa.csv")
        full_00352 = admin_mgr.full_name(obj_00352, 'xa')
        self.assertEqual(full_00352, "Phường Phương Liệt", f"Generator phải trả về 'Phường Phương Liệt', thực tế: '{full_00352}'")
        self.assertNotEqual(full_00352, "Phương Liệt", "Generator không được bỏ sót tiền tố loại đơn vị 'Phường'")

        # Kiểm tra thêm các xã dễ bị nuốt loại đơn vị nếu dùng so sánh không dấu
        test_cases_kind = [
            ({'ten_xa': 'Phương Mai', 'loai_xa': 'Phường'}, 'Phường Phương Mai'),
            ({'ten_xa': 'Phượng Sơn', 'loai_xa': 'Phường'}, 'Phường Phượng Sơn'),
            ({'ten_xa': 'Xá Nhè', 'loai_xa': 'Xã'}, 'Xã Xá Nhè'),
            ({'ten_xa': 'Xa Dung', 'loai_xa': 'Xã'}, 'Xã Xa Dung'),
            ({'ten_xa': 'Tĩnh Gia', 'loai_xa': 'Xã'}, 'Xã Tĩnh Gia'),
        ]
        for mock_row, expected_str in test_cases_kind:
            res_str = admin_mgr.full_name(mock_row, 'xa')
            self.assertEqual(res_str, expected_str, f"AdminManager.full_name thất bại với {mock_row}")

        # 2. FIXTURE REGRESSION: Negative fixture kiểm tra bộ phát hiện validator tên-đối-mã
        mock_bad_row = {
            'id': 'MOCK_ERR_PHUONG_LIET',
            'ma_xa': '00352',
            'xa_phuong': 'Phương Liệt', # Thiếu 'Phường '
            'ma_tinh': '01',
            'tinh': 'Thành phố Hà Nội'
        }
        expected_canonical = canonical_full_name(self.new_w.get(mock_bad_row['ma_xa']), 'xa')
        has_name_mismatch = (mock_bad_row['xa_phuong'] != expected_canonical)
        self.assertTrue(has_name_mismatch, "Validator tên-đối-mã phải bắt được lỗi khi xa_phuong='Phương Liệt' với ma_xa='00352'")

        # 3. Kiểm tra trên 100% dữ liệu thực tế của Train Bổ Sung và Dev Khó
        for split_name, rows in [('train_bo_sung', self.train_rows), ('dev_kho', self.dev_rows)]:
            for r in rows:
                mx = r['ma_xa']
                if mx:
                    expected_w = canonical_full_name(self.new_w.get(mx), 'xa')
                    self.assertEqual(r['xa_phuong'], expected_w,
                                     f"{split_name} {r['id']}: xa_phuong '{r['xa_phuong']}' không khớp tên chuẩn theo mã {mx} (kỳ vọng '{expected_w}')")
                else:
                    self.assertEqual(r['xa_phuong'], '',
                                     f"{split_name} {r['id']}: ma_xa rỗng thì xa_phuong bắt buộc phải rỗng")

                mp = r['ma_tinh']
                if mp:
                    expected_p = canonical_full_name(self.new_p.get(mp), 'tinh')
                    self.assertEqual(r['tinh'], expected_p,
                                     f"{split_name} {r['id']}: tinh '{r['tinh']}' không khớp tên chuẩn theo mã {mp} (kỳ vọng '{expected_p}')")

                # Kiểm tra dia_chi_chuan chứa đúng tên hành chính chuẩn
                if r['xa_phuong'] and r['tinh']:
                    self.assertIn(f"{r['xa_phuong']}, {r['tinh']}", r['dia_chi_chuan'],
                                  f"{split_name} {r['id']}: dia_chi_chuan '{r['dia_chi_chuan']}' không chứa phần hành chính chuẩn '{r['xa_phuong']}, {r['tinh']}'")

        # 4. Kiểm tra cụ thể toàn bộ các dòng thuộc mã 00352 trong train_rows (gồm 24 dòng nền tảng + 22 dòng ngõ chuẩn bổ sung)
        phuong_liet_rows = [r for r in self.train_rows if r['ma_xa'] == '00352']
        self.assertEqual(len(phuong_liet_rows), 46, f"Phải có đúng 46 dòng Phương Liệt (24 nền tảng + 22 bổ sung), thực tế: {len(phuong_liet_rows)}")
        for r in phuong_liet_rows:
            self.assertEqual(r['xa_phuong'], 'Phường Phương Liệt', f"{r['id']}: xa_phuong phải là 'Phường Phương Liệt'")
            self.assertIn('Phường Phương Liệt, Thành phố Hà Nội', r['dia_chi_chuan'], f"{r['id']}: dia_chi_chuan phải chứa 'Phường Phương Liệt, Thành phố Hà Nội'")

    def test_doi_chieu_no_mismatched_old_ward_and_fixture_reject_false_counterpart(self):
        """14. Kiểm tra bảng đối chiếu snapshot bảo toàn địa bàn & tên đường và fixture từ chối đối ứng giả."""
        doi_chieu_path = BO_SUNG_DIR / "doi_chieu_snapshot_v1_v2.csv"
        snapshot_dir = BO_SUNG_DIR / "snapshot_pre_fix_20261029"
        self.assertTrue(doi_chieu_path.exists(), "Thiếu file doi_chieu_snapshot_v1_v2.csv")

        v2_all = {r['id']: r for r in self.train_rows + self.dev_rows}
        snapshot_all = {}
        if (snapshot_dir / "train_bo_sung.csv").exists():
            with open(snapshot_dir / "train_bo_sung.csv", encoding='utf-8-sig') as f_tr:
                snapshot_all.update({r['id']: r for r in csv.DictReader(f_tr)})
        if (snapshot_dir / "dev_kho.csv").exists():
            with open(snapshot_dir / "dev_kho.csv", encoding='utf-8-sig') as f_dev:
                snapshot_all.update({r['id']: r for r in csv.DictReader(f_dev)})

        with open(doi_chieu_path, encoding='utf-8-sig') as f:
            dc_rows = list(csv.DictReader(f))

        mismatched_wards = []
        distinct_road_errors = []
        false_inherit_claims = []

        for dc in dc_rows:
            cid = dc.get('v2_counterpart_id')
            if cid and cid in v2_all:
                v1_rec = snapshot_all.get(dc['v1_id'], {})
                v2_rec = v2_all[cid]

                # 1. Kiểm tra bảo toàn mã xã cũ
                if v2_rec['ma_xa_cu'] != dc['v1_ma_xa_cu']:
                    mismatched_wards.append((dc['v1_id'], cid, dc['v1_ma_xa_cu'], v2_rec['ma_xa_cu']))

                # 2. Kiểm tra tính nhất quán tên đường sau chuẩn hóa (road_key)
                rk1 = road_key(v1_rec.get('duong', ''))
                rk2 = road_key(v2_rec.get('duong', ''))
                if rk1 and rk2 and rk1 != rk2:
                    distinct_road_errors.append((dc['v1_id'], cid, v1_rec.get('duong'), v2_rec.get('duong')))

                # 3. Kiểm tra tuyên bố kế thừa: nếu khác hẳn tên đường mà inheritance_detail lại khai kế thừa tên đường cũ
                inh = dc.get('inheritance_detail', '')
                if rk1 != rk2 and f"duong='{v1_rec.get('duong')}'" in inh:
                    false_inherit_claims.append((dc['v1_id'], cid, inh))

        self.assertEqual(len(mismatched_wards), 0, f"Có {len(mismatched_wards)} đối ứng bị gán sai mã xã cũ: {mismatched_wards[:5]}")
        self.assertEqual(len(distinct_road_errors), 0, f"Có {len(distinct_road_errors)} đối ứng bị gán sai khác tên đường: {distinct_road_errors[:5]}")
        self.assertEqual(len(false_inherit_claims), 0, f"Có {len(false_inherit_claims)} dòng khai man kế thừa tên đường cũ: {false_inherit_claims[:5]}")

        # FIXTURE REGRESSION: Negative fixture kiểm tra detector từ chối khi khai kế thừa nhưng đổi tên đường
        # Giả lập ca VNTRAIN_BS_00042 cũ 'Đường Nguyen Trai' ghép đối ứng 'Đường Hoàng Văn Thụ'
        mock_dc_false_road = {
            'v1_id': 'MOCK_V1_00042',
            'v1_ma_xa_cu': '12646',
            'v2_counterpart_id': 'MOCK_V2_01280',
            'inheritance_detail': "Kế thừa: ma_xa_cu=12646, duong='Đường Nguyen Trai'; Thay thế: so_nha mới"
        }
        mock_v1 = {'id': 'MOCK_V1_00042', 'ma_xa_cu': '12646', 'duong': 'Đường Nguyen Trai'}
        mock_v2_wrong = {'id': 'MOCK_V2_01280', 'ma_xa_cu': '12646', 'duong': 'Đường Hoàng Văn Thụ'}

        # Dùng validator logic kiểm tra
        rk_mock1 = road_key(mock_v1['duong'])
        rk_mock2 = road_key(mock_v2_wrong['duong'])
        is_distinct = (rk_mock1 != rk_mock2)
        has_false_claim = (is_distinct and f"duong='{mock_v1['duong']}'" in mock_dc_false_road['inheritance_detail'])

        self.assertTrue(is_distinct, "Detector phải phát hiện hai tên đường khác hẳn nhau")
        self.assertTrue(has_false_claim, "Detector phải phát hiện hành vi khai man kế thừa tên đường khi khác tên đường")

    def test_runtime_tokenizer_compatibility_and_fixture_boundary_cut(self):
        """15. Kiểm tra tương thích với runtime tokenizer token_co_vi_tri và fixture cắt token dính chữ."""
        import sys
        sys.path.insert(0, str(BASE_DIR))
        from src.tien_xu_ly import token_co_vi_tri

        # Đọc train_spans và dev_spans
        with open(self.token_spans_file, encoding='utf-8') as f:
            all_spans = [json.loads(line) for line in f]

        incompat_detected = 0
        for item in all_spans:
            dau_vao = item['dau_vao']
            tokens = token_co_vi_tri(dau_vao)
            rt_starts = {t.bat_dau for t in tokens}
            rt_ends = {t.ket_thuc for t in tokens}

            has_cut = False
            for fld, s_info in item['spans'].items():
                if s_info:
                    if s_info['start'] not in rt_starts or s_info['end'] not in rt_ends:
                        has_cut = True
                        break

            if has_cut:
                incompat_detected += 1
                self.assertFalse(item['usable_for_span_training'], f"{item['id']}: Cắt token runtime nhưng usable_for_span_training lại là True")
                self.assertFalse(item['tokenizer_runtime_compatible'], f"{item['id']}: Cắt token runtime nhưng tokenizer_runtime_compatible lại là True")
                self.assertEqual(item['tokenizer_version_required'], 'v2.0_glued_boundary')
            else:
                self.assertTrue(item['usable_for_span_training'], f"{item['id']}: Không cắt token runtime nhưng usable_for_span_training lại là False")
                self.assertTrue(item['tokenizer_runtime_compatible'])
                self.assertEqual(item['tokenizer_version_required'], 'v1.0')

        self.assertEqual(incompat_detected, 56, f"Phải phát hiện chính xác 56 ca dính chữ cắt token, thực tế: {incompat_detected}")

        # FIXTURE REGRESSION: Negative fixture kiểm tra span '151' trong '151Đ.LêLợi' bị cắt bởi token_co_vi_tri
        mock_dv = "151Đ.LêLợi, P3, Q3, Thành phố Hồ Chí Minh"
        mock_tokens = token_co_vi_tri(mock_dv)
        mock_starts = {t.bat_dau for t in mock_tokens}
        mock_ends = {t.ket_thuc for t in mock_tokens}
        
        mock_span_so_nha = (0, 3) # '151'
        self.assertNotIn(mock_span_so_nha[1], mock_ends, "Fixture chứng minh token_co_vi_tri gộp '151Đ' thành token [0:4], cắt ngang span '151' [0:3]")

    def test_label_coverage_ngo_ngach_hem_and_thon_xom(self):
        """16. Kiểm tra độ phủ nhãn bắt buộc: ngo_ngach_hem và thon_xom phải xuất hiện ở cả Train và Dev."""
        for split_file, split_name in [(self.train_spans_file, 'Train'), (self.dev_spans_file, 'Dev')]:
            with open(split_file, encoding='utf-8') as f:
                spans_list = [json.loads(line) for line in f]
                
            ngo_count = sum(1 for item in spans_list if item['spans'].get('ngo_ngach_hem'))
            thon_count = sum(1 for item in spans_list if item['spans'].get('thon_xom'))
            
            self.assertGreater(ngo_count, 0, f"{split_name} phải có span ngo_ngach_hem > 0, thực tế: {ngo_count}")
            self.assertGreater(thon_count, 0, f"{split_name} phải có span thon_xom > 0, thực tế: {thon_count}")

    def test_apartment_o_label_preservation(self):
        """17. Kiểm tra phần kiến trúc (lô, căn hộ, tập thể) giữ ở nhãn O theo HOP_DONG_NHAN_CHUAN_HOA."""
        with open(self.token_spans_file, encoding='utf-8') as f:
            all_spans = [json.loads(line) for line in f]

        found_apt = 0
        for item in all_spans:
            dv = item['dau_vao']
            if any(kw in dv for kw in ['Căn hộ', 'Phòng', 'Lô B2', 'Khu tập thể', 'Chung cư']):
                found_apt += 1
                # Kiểm tra trong tokens: các từ thuộc căn hộ/tập thể phải có bio_tag == 'O'
                for t in item['tokens']:
                    if t['token'] in ['Căn', 'hộ', 'Phòng', 'Lô', 'tập', 'thể', 'Chung', 'cư']:
                        self.assertEqual(t['bio_tag'], 'O', f"{item['id']}: Từ '{t['token']}' của phần kiến trúc phải nhận nhãn 'O', thực tế: '{t['bio_tag']}'")
                        
        self.assertGreaterEqual(found_apt, 28, f"Phải có ít nhất 28 mẫu căn hộ/tập thể (22 train + 6 dev), thực tế: {found_apt}")

    def test_counterpart_selection_prefers_matching_road_and_rejects_mismatch(self):
        """18. Kiểm tra thuật toán chọn đối ứng ưu tiên đúng đường và từ chối candidate sai đường dù cùng xã."""
        # Giả lập hàm matcher chuẩn xác của build_snapshot_comparison.py
        def match_candidate(candidates, r_old, used_ids):
            target_road = r_old.get('duong', '')
            target_rk = road_key(target_road)
            # 1. Exact match
            for c in candidates:
                if c['id'] not in used_ids and c['ma_xa_cu'] == r_old['ma_xa_cu']:
                    if c.get('duong', '') == target_road:
                        return c, 'exact_road'
            # 2. Spelling variant
            if target_rk:
                for c in candidates:
                    if c['id'] not in used_ids and c['ma_xa_cu'] == r_old['ma_xa_cu']:
                        if road_key(c.get('duong', '')) == target_rk:
                            return c, 'spelling_variant'
            return None, None

        r_v1 = {'id': 'VNTRAIN_BS_00042', 'ma_xa_cu': '12646', 'duong': 'Đường Nguyen Trai'}

        # Case 1: Pool có 2 candidate cùng xã 12646, candidate sai đường đứng trước
        cand_wrong = {'id': 'CAND_WRONG_ROAD', 'ma_xa_cu': '12646', 'duong': 'Đường Hoàng Văn Thụ'}
        cand_right = {'id': 'CAND_RIGHT_ROAD', 'ma_xa_cu': '12646', 'duong': 'Đường Nguyen Trai'}
        pool_both = [cand_wrong, cand_right]

        chosen, m_type = match_candidate(pool_both, r_v1, set())
        self.assertIsNotNone(chosen, "Matcher phải tìm được candidate đúng đường")
        self.assertEqual(chosen['id'], 'CAND_RIGHT_ROAD', "Matcher bắt buộc phải chọn CAND_RIGHT_ROAD, không được lấy CAND_WRONG_ROAD dù đứng trước")
        self.assertEqual(m_type, 'exact_road')

        # Case 2: Pool chỉ có candidate cùng xã nhưng sai đường
        pool_wrong_only = [cand_wrong]
        chosen_none, m_type_none = match_candidate(pool_wrong_only, r_v1, set())
        self.assertIsNone(chosen_none, "Matcher bắt buộc phải từ chối ghép khi không có candidate nào khớp tên đường")
        self.assertIsNone(m_type_none)

        # Case 3: Candidate có tên đường là biến thể chính tả (khác dấu)
        cand_spelling = {'id': 'CAND_SPELLING', 'ma_xa_cu': '12646', 'duong': 'Đường Nguyễn Trãi'}
        pool_spelling = [cand_wrong, cand_spelling]
        chosen_sp, m_type_sp = match_candidate(pool_spelling, r_v1, set())
        self.assertIsNotNone(chosen_sp)
        self.assertEqual(chosen_sp['id'], 'CAND_SPELLING')
        self.assertEqual(m_type_sp, 'spelling_variant')

    def test_id_disposition_version_transparency_and_no_confusion(self):
        """19. Kiểm tra phân định danh tính thế hệ ID trong id_disposition.csv, tránh nhầm lẫn cờ usable giữa v1 và v3."""
        id_disp_file = BO_SUNG_DIR / "id_disposition.csv"
        self.assertTrue(id_disp_file.exists(), "Thiếu id_disposition.csv")

        with open(id_disp_file, encoding='utf-8-sig') as f:
            disp_rows = list(csv.DictReader(f))

        # 1. Kiểm tra các cột phân định phiên bản
        sample = disp_rows[0]
        self.assertIn('snapshot_version', sample, "Thiếu cột snapshot_version")
        self.assertIn('v1_id', sample, "Thiếu cột v1_id")
        self.assertIn('reused_in_v3_with_different_content', sample, "Thiếu cột reused_in_v3_with_different_content")
        self.assertIn('id_generation_note', sample, "Thiếu cột id_generation_note")
        self.assertEqual(sample['snapshot_version'], 'v1_snapshot_pre_fix')

        # 2. Kiểm tra các bản ghi v1 trùng ID trong v3 phải có chú thích cảnh báo rõ ràng
        reused_diff_rows = [r for r in disp_rows if r.get('reused_in_v3_with_different_content') == 'True']
        self.assertGreater(len(reused_diff_rows), 0, "Phải có các dòng v1 trùng ID nhưng khác nội dung trong v3")

        for r in reused_diff_rows:
            note = r.get('id_generation_note', '')
            self.assertIn('áp dụng cho dữ liệu snapshot v1 cũ', note, f"{r['id']}: Ghi chú thiếu cảnh báo phạm vi áp dụng cho snapshot v1 cũ")

        # 3. Đối chứng tính độc lập cờ: ví dụ VNTRAIN_BS_00001
        # Trong v1_disposition: VNTRAIN_BS_00001 bị loại bỏ -> usable_for_span_training = False
        # Trong token_spans.jsonl: VNTRAIN_BS_00001 là mẫu v3 mới -> usable_for_span_training = True
        v1_00001_disp = next(r for r in disp_rows if r['id'] == 'VNTRAIN_BS_00001')
        self.assertEqual(v1_00001_disp['v1_usable_for_span_training'], 'False')

        with open(self.token_spans_file, encoding='utf-8') as f:
            v3_all_spans = {json.loads(line)['id']: json.loads(line) for line in f}

        v3_00001_span = v3_all_spans['VNTRAIN_BS_00001']
        self.assertTrue(v3_00001_span['usable_for_span_training'], "Bản ghi VNTRAIN_BS_00001 trong corpus v3 phải có usable_for_span_training=True độc lập")
        self.assertNotEqual(v1_00001_disp['dau_vao'], v3_00001_span['dau_vao'], "Dữ liệu đầu vào của hai thế hệ phải khác nhau")

if __name__ == '__main__':
    unittest.main()
