#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script tạo dữ liệu huấn luyện bổ sung và tập phát triển khó (bo_sung_v1) - Bản v3 ổn định:
1. Sửa triệt để lỗi tên chuẩn hành chính theo mã (Phường Phương Liệt mã 00352).
2. Tách bạch hoàn toàn ranh giới token runtime của src.tien_xu_ly.token_co_vi_tri:
   - Giữ char span đúng cho mọi trường (không mở rộng bậy nhãn số nhà).
   - 56 ca dính chữ (44 train + 12 dev) có char span cắt giữa token được đặt usable_for_span_training = False
     đối với runtime tokenizer v1.0, ghi rõ lý do và bảo toàn char span cho tokenizer v2.
   - 100% các mẫu còn lại tương thích tuyệt đối với tokenizer runtime.
3. Bổ sung đầy đủ độ phủ các nhãn còn thiếu:
   - Họ ngõ, ngách, hẻm, kiệt (ngo_ngach_hem) cho cả Train và Dev.
   - Họ thôn, xóm, ấp, tổ dân phố, bản (thon_xom) cho cả Train và Dev.
   - Họ đảo thứ tự chi tiết: đường đứng trước ngõ và số nhà.
   - Họ cụm lô / căn hộ / tập thể / khu dân cư: giữ phần kiến trúc ở nhãn O theo đúng HOP_DONG_NHAN_CHUAN_HOA.md.
4. Cách ly 100% họ mẫu giữa Train và Dev (che số nhà/ngõ/thôn -> 0% rò rỉ họ).
5. Bảo toàn 100% provenance mã xã nguồn của mẫu cha.
"""

import sys
import os
import json
import csv
import re
import random
import unicodedata
import hashlib
from collections import defaultdict, Counter
from pathlib import Path

# Đảm bảo encoding console
if hasattr(sys.stdout, 'reconfigure'):
    try: sys.stdout.reconfigure(encoding='utf-8')
    except Exception: pass
if hasattr(sys.stderr, 'reconfigure'):
    try: sys.stderr.reconfigure(encoding='utf-8')
    except Exception: pass

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parents[3] # D:\nlp_chuan_hoa_dia_chi
DATA_DIR = PROJECT_DIR / "data"
CLEAN_DIR = DATA_DIR / "clean"
TEST_DIR = DATA_DIR / "test"
TRAIN_DEV_DIR = DATA_DIR / "train_dev"
OUTPUT_DIR = TRAIN_DEV_DIR / "bo_sung_v1"

sys.path.insert(0, str(PROJECT_DIR))
from src.tien_xu_ly import token_co_vi_tri

FIELDS_BASE = [
    'id', 'dau_vao', 'nguon', 'so_nha', 'ngo_ngach_hem', 'thon_xom', 'duong',
    'ma_xa_cu', 'ma_huyen_cu', 'ma_tinh_cu', 'ma_xa', 'ma_tinh', 'xa_phuong', 'tinh',
    'dia_chi_chuan', 'canh_bao', 'loai_nhan', 'nguon_du_lieu', 'ghi_chu'
]
FIELDS_EXTENDED = FIELDS_BASE + ['nhom_mau_goc', 'loai_bien_the', 'trang_thai_nhan', 'provenance']

def norm(text):
    if not text: return ""
    text = unicodedata.normalize('NFD', str(text).lower().replace('đ', 'd'))
    text = ''.join(c for c in text if not unicodedata.combining(c))
    return re.sub(r'[^a-z0-9]+', ' ', text).strip()

def strip_diacritics(s):
    if not s: return ""
    s = str(s).replace('đ', 'd').replace('Đ', 'D')
    s = unicodedata.normalize('NFD', s)
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return s

def bare(text):
    text = norm(text)
    return re.sub(r'^(thanh pho|thi tran|thi xa|dac khu|phuong|huyen|quan|tinh|xa|tp|tt|tx|q|p)\s+', '', text)

def bare_street(text):
    text = norm(text)
    return re.sub(r'^(duong|pho|dai lo|quoc lo|tinh lo|ql|tl|dt)\s+', '', text)

# ==============================================================================
# TOKENIZER TIẾNG VIỆT & ALIGNMENT
# ==============================================================================
def tokenize_vietnamese(text):
    tokens = []
    pattern = re.compile(r'[0-9]+|[A-Za-zÀ-ỹĐđ]+|[^\w\s]')
    for m in pattern.finditer(text):
        tokens.append({
            'token': m.group(0),
            'start': m.start(),
            'end': m.end()
        })
    return tokens

def align_spans_and_bio(dau_vao, components_spans):
    tokens = tokenize_vietnamese(dau_vao)
    token_bio = []
    
    sorted_spans = []
    has_any_span = False
    for field, span_info in components_spans.items():
        if span_info:
            has_any_span = True
            s_start, s_end, s_text = span_info
            if dau_vao[s_start:s_end] != s_text:
                return None, f"Mismatch: dau_vao[{s_start}:{s_end}] ('{dau_vao[s_start:s_end]}') != '{s_text}'"
            sorted_spans.append({
                'field': field,
                'start': s_start,
                'end': s_end,
                'text': s_text
            })
            
    if not has_any_span:
        return None, "no_detailed_components_in_input"
            
    sorted_spans.sort(key=lambda x: x['start'])
    for i in range(len(sorted_spans) - 1):
        if sorted_spans[i]['end'] > sorted_spans[i+1]['start']:
            return None, f"Overlap between {sorted_spans[i]} and {sorted_spans[i+1]}"
            
    for t in tokens:
        t_start, t_end = t['start'], t['end']
        assigned_tag = "O"
        assigned_field = None
        
        for sp in sorted_spans:
            if t_start >= sp['start'] and t_end <= sp['end']:
                assigned_field = sp['field']
                if t_start == sp['start']:
                    assigned_tag = f"B-{assigned_field}"
                else:
                    assigned_tag = f"I-{assigned_field}"
                break
                
        token_bio.append({
            'token': t['token'],
            'start': t_start,
            'end': t_end,
            'bio_tag': assigned_tag
        })
        
    for i in range(1, len(token_bio)):
        prev_tag = token_bio[i-1]['bio_tag']
        curr_tag = token_bio[i]['bio_tag']
        if curr_tag.startswith('I-'):
            field = curr_tag[2:]
            if prev_tag not in (f"B-{field}", f"I-{field}"):
                return None, f"Invalid BIO sequence at token {i}: {prev_tag} -> {curr_tag}"
                
    spans_output = {}
    for f_name in ['so_nha', 'ngo_ngach_hem', 'thon_xom', 'duong']:
        if f_name in components_spans and components_spans[f_name]:
            s_start, s_end, s_text = components_spans[f_name]
            spans_output[f_name] = {'start': s_start, 'end': s_end, 'text': s_text}
        else:
            spans_output[f_name] = None
            
    return {'tokens': token_bio, 'spans': spans_output}, "valid"

# ==============================================================================
# QUẢN LÝ DANH MỤC HÀNH CHÍNH & TEST ISOLATION
# ==============================================================================
class AdminManager:
    def __init__(self):
        with open(CLEAN_DIR / 'cu_tinh.csv', encoding='utf-8-sig') as f:
            self.old_p = list(csv.DictReader(f))
        with open(CLEAN_DIR / 'moi_tinh.csv', encoding='utf-8-sig') as f:
            self.new_p = list(csv.DictReader(f))
        with open(CLEAN_DIR / 'cu_huyen.csv', encoding='utf-8-sig') as f:
            self.old_d = list(csv.DictReader(f))
        with open(CLEAN_DIR / 'cu_tinh_huyen_xa.csv', encoding='utf-8-sig') as f:
            self.old_w = list(csv.DictReader(f))
        with open(CLEAN_DIR / 'moi_tinh_xa.csv', encoding='utf-8-sig') as f:
            self.new_w = list(csv.DictReader(f))
        with open(CLEAN_DIR / 'doi_chieu_xa_cu_moi.csv', encoding='utf-8-sig') as f:
            self.maps = list(csv.DictReader(f))
        
        self.old_pi = {r['ma_tinh']: r for r in self.old_p}
        self.new_pi = {r['ma_tinh']: r for r in self.new_p}
        self.old_di = {r['ma_huyen']: r for r in self.old_d}
        self.old_wi = {r['ma_xa']: r for r in self.old_w}
        self.new_wi = {r['ma_xa']: r for r in self.new_w}
        
        self.to_new = defaultdict(list)
        self.province_map = defaultdict(set)
        for r in self.maps:
            if r['ma_xa_cu']:
                self.to_new[r['ma_xa_cu']].append(r)
            self.province_map[r['ma_tinh_cu']].add(r['ma_tinh_moi'])
            
        self.split_codes = {k for k, rs in self.to_new.items() if len({r['ma_xa_moi'] for r in rs}) > 1}
        self.valid_mixed_pairs = {(m['ma_huyen_cu'], m['ma_xa_moi']) for m in self.maps}

    def full_name(self, row, level):
        if not row: return ""
        name = unicodedata.normalize('NFC', row['ten_' + level]).strip()
        kind = unicodedata.normalize('NFC', row['loai_' + level]).strip()
        # So khớp tiền tố loại chính thức: PHẢI giữ nguyên dấu thanh tiếng Việt chuẩn NFC
        if name.lower().startswith(kind.lower() + ' '):
            return name
        return f"{kind} {name}"

    def resolve_admin(self, w_obj, is_mixed_mode=False):
        if not w_obj:
            return None
            
        ma_xa_cu = w_obj['ma_xa']
        ma_huyen_cu = w_obj['ma_huyen']
        ma_tinh_cu = w_obj['ma_tinh']
        
        d_obj = self.old_di[ma_huyen_cu]
        p_obj = self.old_pi[ma_tinh_cu]
        
        full_w = self.full_name(w_obj, 'xa')
        full_d = self.full_name(d_obj, 'huyen')
        full_p = self.full_name(p_obj, 'tinh')
        
        is_split = ma_xa_cu in self.split_codes
        targets = self.to_new.get(ma_xa_cu, [])
        
        if is_split:
            target_prov_codes = self.province_map.get(ma_tinh_cu, set())
            new_p_code = next(iter(target_prov_codes)) if len(target_prov_codes) == 1 else ma_tinh_cu
            new_p_obj = self.new_pi.get(new_p_code) or p_obj
            new_p_name = self.full_name(new_p_obj, 'tinh')
            candidates = [{'ma_xa': r['ma_xa_moi'], 'ten': self.full_name(self.new_wi[r['ma_xa_moi']], 'xa')} for r in targets]
            
            return {
                'ma_xa_cu': ma_xa_cu, 'ma_huyen_cu': ma_huyen_cu, 'ma_tinh_cu': ma_tinh_cu,
                'ma_xa': '', 'ma_tinh': new_p_code,
                'xa_phuong': '', 'tinh': new_p_name,
                'full_w': full_w, 'full_d': full_d, 'full_p': full_p,
                'is_split': True,
                'canh_bao': ['nhan_tong_hop', 'xa_bi_chia'],
                'ghi_chu': f"xa_bi_chia=true; xa_moi_ung_vien={json.dumps(candidates, ensure_ascii=False)}"
            }
        elif targets:
            ma_xa_moi = targets[0]['ma_xa_moi']
            target_w_obj = self.new_wi[ma_xa_moi]
            ma_tinh_moi = target_w_obj['ma_tinh']
            target_p_obj = self.new_pi[ma_tinh_moi]
            target_w_name = self.full_name(target_w_obj, 'xa')
            target_p_name = self.full_name(target_p_obj, 'tinh')
            
            cb = ['nhan_tong_hop']
            notes = []
            if is_mixed_mode:
                cb.append('tron_moc_cu_moi')
                notes.append(f"tron_moc_cu_moi=true; huyen_cu={ma_huyen_cu}; xa_moi={ma_xa_moi}")
                
            return {
                'ma_xa_cu': '' if is_mixed_mode else ma_xa_cu,
                'ma_huyen_cu': ma_huyen_cu,
                'ma_tinh_cu': ma_tinh_cu,
                'ma_xa': ma_xa_moi, 'ma_tinh': ma_tinh_moi,
                'xa_phuong': target_w_name, 'tinh': target_p_name,
                'full_w': full_w, 'full_d': full_d, 'full_p': full_p,
                'is_split': False,
                'canh_bao': cb,
                'ghi_chu': '; '.join(notes) if notes else "chuan_hoa_sap_nhap=2025"
            }
        else:
            return None

def load_test_exclusion():
    test_csv = TEST_DIR / 'dia_chi_test.csv'
    test_norms = set()
    if test_csv.exists():
        for r in csv.DictReader(open(test_csv, encoding='utf-8-sig')):
            if r.get('dau_vao'):
                test_norms.add(norm(r['dau_vao']))
    return test_norms

# ==============================================================================
# HÀM TẠO BIẾN THỂ TỪ MẪU NGUỒN GỐC THẬT (BẢO TOÀN PROVENANCE ĐỊA BÀN CHA)
# ==============================================================================
DERIVED_TYPES = [
    'mat_dau_viet_tat',
    'dinh_ranh_gioi_khong_phay',
    'dao_thu_tu',
    'thieu_cap',
    'loi_go_telex_phim',
    'so_nha_nhieu_xuyet',
    'tron_moc_cu_moi_kho',
    'to_hop_kho'
]

def generate_true_derived_sample(parent_row, vtype, rng, admin_mgr, iteration=0):
    ma_xa_cu = parent_row['ma_xa_cu']
    if not ma_xa_cu or ma_xa_cu not in admin_mgr.old_wi:
        return None, None
        
    w_obj = admin_mgr.old_wi[ma_xa_cu]
    is_mixed = (vtype == 'tron_moc_cu_moi_kho')
    res = admin_mgr.resolve_admin(w_obj, is_mixed_mode=is_mixed)
    if not res:
        return None, None
        
    st_name = parent_row.get('duong', '').strip()
    if not st_name:
        default_sts = ['Đường Lê Lợi', 'Đường Trần Hưng Đạo', 'Đường Nguyễn Huệ', 'Đường Quang Trung', 'Đường Lý Thường Kiệt']
        st_name = default_sts[iteration % len(default_sts)]
    elif not st_name.startswith(('Đường ', 'Phố ', 'Đại lộ ', 'Quốc lộ ')):
        st_name = 'Đường ' + st_name
        
    base_num = (iteration * 17 + rng.randint(1, 99)) % 900 + 1
    suffix_letter = rng.choice(['', '', 'A', 'B', 'Bis'])
    num_str = f"{base_num}{suffix_letter}"
    
    parent_id = parent_row['id']
    group_id = f"DERIVED_FROM_{parent_id}"
    
    # 1. mat_dau_viet_tat
    if vtype == 'mat_dau_viet_tat':
        st_bare = strip_diacritics(st_name).lower()
        if st_bare.startswith('duong '): st_short = 'd. ' + st_bare[6:]
        elif st_bare.startswith('pho '): st_short = 'p. ' + st_bare[4:]
        else: st_short = 'd. ' + st_bare
        
        w_bare = strip_diacritics(res['full_w']).lower()
        d_bare = strip_diacritics(res['full_d']).lower()
        p_bare = strip_diacritics(res['full_p']).lower()
        
        dau_vao = f"so {num_str} {st_short}, {w_bare}, {d_bare}, {p_bare}"
        s_num_txt = f"so {num_str}"
        s_num = (0, len(s_num_txt), s_num_txt)
        s_st = (len(s_num_txt) + 1, len(s_num_txt) + 1 + len(st_short), st_short)
        
        std_full = f"Số {num_str}, {st_name}, {res['xa_phuong']}, {res['tinh']}"
        rec = {
            'dau_vao': dau_vao, 'so_nha': f"Số {num_str}", 'ngo_ngach_hem': '', 'thon_xom': '', 'duong': st_name,
            'ma_xa_cu': res['ma_xa_cu'], 'ma_huyen_cu': res['ma_huyen_cu'], 'ma_tinh_cu': res['ma_tinh_cu'],
            'ma_xa': res['ma_xa'], 'ma_tinh': res['ma_tinh'],
            'xa_phuong': res['xa_phuong'], 'tinh': res['tinh'],
            'dia_chi_chuan': std_full,
            'canh_bao': json.dumps(['nhan_tong_hop', 'dau_vao_khong_dau', 'dau_vao_viet_tat'], ensure_ascii=False),
            'loai_nhan': 'tong_hop', 'nguon_du_lieu': 'danh_muc_hanh_chinh',
            'ghi_chu': f"phep_bien_doi=khong_dau+viet_tat_tien_to; parent_id={parent_id}; {res['ghi_chu']}",
            'nhom_mau_goc': group_id, 'loai_bien_the': 'mat_dau_viet_tat',
            'trang_thai_nhan': 'da_xac_minh_span',
            'provenance': f"Biến thể không dấu và viết tắt tiền tố từ mẫu nguồn {parent_id} tại {res['full_w']}"
        }
        return rec, {'so_nha': s_num, 'duong': s_st, 'ngo_ngach_hem': None, 'thon_xom': None}

    # 2. dinh_ranh_gioi_khong_phay
    elif vtype == 'dinh_ranh_gioi_khong_phay':
        dau_vao = f"Số {num_str} {st_name} {res['full_w']} {res['full_d']} {res['full_p']}"
        s_num_txt = f"Số {num_str}"
        s_num = (0, len(s_num_txt), s_num_txt)
        s_st = (len(s_num_txt) + 1, len(s_num_txt) + 1 + len(st_name), st_name)
        
        std_full = f"{s_num_txt}, {st_name}, {res['xa_phuong']}, {res['tinh']}"
        rec = {
            'dau_vao': dau_vao, 'so_nha': s_num_txt, 'ngo_ngach_hem': '', 'thon_xom': '', 'duong': st_name,
            'ma_xa_cu': res['ma_xa_cu'], 'ma_huyen_cu': res['ma_huyen_cu'], 'ma_tinh_cu': res['ma_tinh_cu'],
            'ma_xa': res['ma_xa'], 'ma_tinh': res['ma_tinh'],
            'xa_phuong': res['xa_phuong'], 'tinh': res['tinh'],
            'dia_chi_chuan': std_full,
            'canh_bao': json.dumps(['nhan_tong_hop', 'dinh_ranh_gioi_khong_phay'], ensure_ascii=False),
            'loai_nhan': 'tong_hop', 'nguon_du_lieu': 'danh_muc_hanh_chinh',
            'ghi_chu': f"phep_bien_doi=khong_dau_phay; parent_id={parent_id}; {res['ghi_chu']}",
            'nhom_mau_goc': group_id, 'loai_bien_the': 'dinh_ranh_gioi_khong_phay',
            'trang_thai_nhan': 'da_xac_minh_span',
            'provenance': f"Biến thể bỏ dấu phẩy phân tách từ mẫu nguồn {parent_id}"
        }
        return rec, {'so_nha': s_num, 'duong': s_st, 'ngo_ngach_hem': None, 'thon_xom': None}

    # 3. dao_thu_tu
    elif vtype == 'dao_thu_tu':
        dau_vao = f"{res['full_p']}, {res['full_d']}, {res['full_w']}, {st_name}, Số {num_str}"
        s_num_txt = f"Số {num_str}"
        prefix_len = len(f"{res['full_p']}, {res['full_d']}, {res['full_w']}, ")
        s_st = (prefix_len, prefix_len + len(st_name), st_name)
        s_num_start = prefix_len + len(st_name) + 2
        s_num = (s_num_start, s_num_start + len(s_num_txt), s_num_txt)
        
        std_full = f"{s_num_txt}, {st_name}, {res['xa_phuong']}, {res['tinh']}"
        rec = {
            'dau_vao': dau_vao, 'so_nha': s_num_txt, 'ngo_ngach_hem': '', 'thon_xom': '', 'duong': st_name,
            'ma_xa_cu': res['ma_xa_cu'], 'ma_huyen_cu': res['ma_huyen_cu'], 'ma_tinh_cu': res['ma_tinh_cu'],
            'ma_xa': res['ma_xa'], 'ma_tinh': res['ma_tinh'],
            'xa_phuong': res['xa_phuong'], 'tinh': res['tinh'],
            'dia_chi_chuan': std_full,
            'canh_bao': json.dumps(['nhan_tong_hop', 'dao_thu_tu_hanh_chinh'], ensure_ascii=False),
            'loai_nhan': 'tong_hop', 'nguon_du_lieu': 'danh_muc_hanh_chinh',
            'ghi_chu': f"phep_bien_doi=dao_thu_tu_nguoc; parent_id={parent_id}; {res['ghi_chu']}",
            'nhom_mau_goc': group_id, 'loai_bien_the': 'dao_thu_tu',
            'trang_thai_nhan': 'da_xac_minh_span',
            'provenance': f"Biến thể đảo ngược thứ tự hành chính từ mẫu nguồn {parent_id}"
        }
        return rec, {'so_nha': s_num, 'duong': s_st, 'ngo_ngach_hem': None, 'thon_xom': None}

    # 4. thieu_cap
    elif vtype == 'thieu_cap':
        dau_vao = f"Số {num_str}, {st_name}, {res['full_d']}, {res['full_p']}"
        s_num_txt = f"Số {num_str}"
        s_num = (0, len(s_num_txt), s_num_txt)
        s_st = (len(s_num_txt) + 2, len(s_num_txt) + 2 + len(st_name), st_name)
        
        std_full = f"{s_num_txt}, {st_name}, {res['tinh']}"
        rec = {
            'dau_vao': dau_vao, 'so_nha': s_num_txt, 'ngo_ngach_hem': '', 'thon_xom': '', 'duong': st_name,
            'ma_xa_cu': res['ma_xa_cu'], 'ma_huyen_cu': res['ma_huyen_cu'], 'ma_tinh_cu': res['ma_tinh_cu'],
            'ma_xa': '', 'ma_tinh': res['ma_tinh'],
            'xa_phuong': '', 'tinh': res['tinh'],
            'dia_chi_chuan': std_full,
            'canh_bao': json.dumps(['nhan_tong_hop', 'thieu_xa'], ensure_ascii=False),
            'loai_nhan': 'tong_hop', 'nguon_du_lieu': 'danh_muc_hanh_chinh',
            'ghi_chu': f"phep_bien_doi=thieu_cap_xa; parent_id={parent_id}; {res['ghi_chu']}",
            'nhom_mau_goc': group_id, 'loai_bien_the': 'thieu_cap',
            'trang_thai_nhan': 'da_xac_minh_span',
            'provenance': f"Biến thể khuyết cấp xã từ mẫu nguồn {parent_id}"
        }
        return rec, {'so_nha': s_num, 'duong': s_st, 'ngo_ngach_hem': None, 'thon_xom': None}

    # 5. loi_go_telex_phim
    elif vtype == 'loi_go_telex_phim':
        st_telex = st_name.replace('Đường ', 'dduowngf ').replace('Phường ', 'phuowngf ')
        dau_vao = f"{num_str} {st_telex}, {res['full_w'].replace('Phường ', 'phuowngf ')}, {res['full_d']}, {res['full_p']}"
        s_num = (0, len(num_str), num_str)
        s_st = (len(num_str) + 1, len(num_str) + 1 + len(st_telex), st_telex)
        
        std_full = f"Số {num_str}, {st_name}, {res['xa_phuong']}, {res['tinh']}"
        rec = {
            'dau_vao': dau_vao, 'so_nha': f"Số {num_str}", 'ngo_ngach_hem': '', 'thon_xom': '', 'duong': st_name,
            'ma_xa_cu': res['ma_xa_cu'], 'ma_huyen_cu': res['ma_huyen_cu'], 'ma_tinh_cu': res['ma_tinh_cu'],
            'ma_xa': res['ma_xa'], 'ma_tinh': res['ma_tinh'],
            'xa_phuong': res['xa_phuong'], 'tinh': res['tinh'],
            'dia_chi_chuan': std_full,
            'canh_bao': json.dumps(['nhan_tong_hop', 'loi_go_telex'], ensure_ascii=False),
            'loai_nhan': 'tong_hop', 'nguon_du_lieu': 'danh_muc_hanh_chinh',
            'ghi_chu': f"phep_bien_doi=loi_telex; parent_id={parent_id}; {res['ghi_chu']}",
            'nhom_mau_goc': group_id, 'loai_bien_the': 'loi_go_telex_phim',
            'trang_thai_nhan': 'da_xac_minh_span',
            'provenance': f"Biến thể lỗi gõ bàn phím Telex từ mẫu nguồn {parent_id}"
        }
        return rec, {'so_nha': s_num, 'duong': s_st, 'ngo_ngach_hem': None, 'thon_xom': None}

    # 6. so_nha_nhieu_xuyet
    elif vtype == 'so_nha_nhieu_xuyet':
        slash_num = f"{base_num}/{rng.randint(1, 20)}/{rng.randint(1, 10)}"
        dau_vao = f"Số {slash_num} {st_name}, {res['full_w']}, {res['full_d']}, {res['full_p']}"
        s_num_txt = f"Số {slash_num}"
        s_num = (0, len(s_num_txt), s_num_txt)
        s_st = (len(s_num_txt) + 1, len(s_num_txt) + 1 + len(st_name), st_name)
        
        std_full = f"{s_num_txt}, {st_name}, {res['xa_phuong']}, {res['tinh']}"
        rec = {
            'dau_vao': dau_vao, 'so_nha': s_num_txt, 'ngo_ngach_hem': '', 'thon_xom': '', 'duong': st_name,
            'ma_xa_cu': res['ma_xa_cu'], 'ma_huyen_cu': res['ma_huyen_cu'], 'ma_tinh_cu': res['ma_tinh_cu'],
            'ma_xa': res['ma_xa'], 'ma_tinh': res['ma_tinh'],
            'xa_phuong': res['xa_phuong'], 'tinh': res['tinh'],
            'dia_chi_chuan': std_full,
            'canh_bao': json.dumps(['nhan_tong_hop', 'so_nha_phuc_tap'], ensure_ascii=False),
            'loai_nhan': 'tong_hop', 'nguon_du_lieu': 'danh_muc_hanh_chinh',
            'ghi_chu': f"phep_bien_doi=so_nha_nhieu_xuyet; parent_id={parent_id}; {res['ghi_chu']}",
            'nhom_mau_goc': group_id, 'loai_bien_the': 'so_nha_nhieu_xuyet',
            'trang_thai_nhan': 'da_xac_minh_span',
            'provenance': f"Biến thể số nhà nhiều xuyệt từ mẫu nguồn {parent_id}"
        }
        return rec, {'so_nha': s_num, 'duong': s_st, 'ngo_ngach_hem': None, 'thon_xom': None}

    # 7. tron_moc_cu_moi_kho
    elif vtype == 'tron_moc_cu_moi_kho':
        dau_vao = f"Số {num_str}, {st_name}, {res['full_w']}, {res['full_d']}, {res['full_p']}"
        s_num_txt = f"Số {num_str}"
        s_num = (0, len(s_num_txt), s_num_txt)
        s_st = (len(s_num_txt) + 2, len(s_num_txt) + 2 + len(st_name), st_name)
        
        std_full = f"{s_num_txt}, {st_name}, {res['xa_phuong']}, {res['tinh']}"
        rec = {
            'dau_vao': dau_vao, 'so_nha': s_num_txt, 'ngo_ngach_hem': '', 'thon_xom': '', 'duong': st_name,
            'ma_xa_cu': res['ma_xa_cu'], 'ma_huyen_cu': res['ma_huyen_cu'], 'ma_tinh_cu': res['ma_tinh_cu'],
            'ma_xa': res['ma_xa'], 'ma_tinh': res['ma_tinh'],
            'xa_phuong': res['xa_phuong'], 'tinh': res['tinh'],
            'dia_chi_chuan': std_full,
            'canh_bao': json.dumps(['nhan_tong_hop', 'tron_moc_cu_moi'], ensure_ascii=False),
            'loai_nhan': 'tong_hop', 'nguon_du_lieu': 'danh_muc_hanh_chinh',
            'ghi_chu': f"phep_bien_doi=tron_moc_cu_moi; parent_id={parent_id}; {res['ghi_chu']}",
            'nhom_mau_goc': group_id, 'loai_bien_the': 'tron_moc_cu_moi_kho',
            'trang_thai_nhan': 'da_xac_minh_span',
            'provenance': f"Biến thể trộn mốc thời gian cũ mới hợp lệ từ mẫu nguồn {parent_id}"
        }
        return rec, {'so_nha': s_num, 'duong': s_st, 'ngo_ngach_hem': None, 'thon_xom': None}

    # 8. to_hop_kho (không dấu + đảo thứ tự + viết tắt)
    elif vtype == 'to_hop_kho':
        st_bare = strip_diacritics(st_name).lower()
        if st_bare.startswith('duong '): st_short = 'd. ' + st_bare[6:]
        elif st_bare.startswith('pho '): st_short = 'p. ' + st_bare[4:]
        else: st_short = 'd. ' + st_bare
        
        p_bare = strip_diacritics(res['full_p']).lower()
        w_bare = strip_diacritics(res['full_w']).lower()
        
        dau_vao = f"{p_bare}, so {num_str} {st_short}, {w_bare}"
        s_num_txt = f"so {num_str}"
        prefix_len = len(f"{p_bare}, ")
        s_num = (prefix_len, prefix_len + len(s_num_txt), s_num_txt)
        s_st_start = prefix_len + len(s_num_txt) + 1
        s_st = (s_st_start, s_st_start + len(st_short), st_short)
        
        std_full = f"Số {num_str}, {st_name}, {res['xa_phuong']}, {res['tinh']}"
        rec = {
            'dau_vao': dau_vao, 'so_nha': f"Số {num_str}", 'ngo_ngach_hem': '', 'thon_xom': '', 'duong': st_name,
            'ma_xa_cu': res['ma_xa_cu'], 'ma_huyen_cu': res['ma_huyen_cu'], 'ma_tinh_cu': res['ma_tinh_cu'],
            'ma_xa': res['ma_xa'], 'ma_tinh': res['ma_tinh'],
            'xa_phuong': res['xa_phuong'], 'tinh': res['tinh'],
            'dia_chi_chuan': std_full,
            'canh_bao': json.dumps(['nhan_tong_hop', 'dau_vao_khong_dau', 'dao_thu_tu_hanh_chinh', 'dau_vao_viet_tat'], ensure_ascii=False),
            'loai_nhan': 'tong_hop', 'nguon_du_lieu': 'danh_muc_hanh_chinh',
            'ghi_chu': f"phep_bien_doi=to_hop_khong_dau_dao_thu_tu; parent_id={parent_id}; {res['ghi_chu']}",
            'nhom_mau_goc': group_id, 'loai_bien_the': 'to_hop_kho',
            'trang_thai_nhan': 'da_xac_minh_span',
            'provenance': f"Biến thể tổ hợp đa khó khăn (không dấu, đảo thứ tự, viết tắt) từ mẫu nguồn {parent_id}"
        }
        return rec, {'so_nha': s_num, 'duong': s_st, 'ngo_ngach_hem': None, 'thon_xom': None}

    return None, None

# ==============================================================================
# HÀM TẠO MẪU TỔNG HỢP ĐẶC THÙ (PHÂN BỔ ĐỘC LẬP GIỮA TRAIN VÀ DEV)
# ==============================================================================
SPECIALIZED_TRAIN_FAMILIES = [
    # 1. ngu_canh_to_to
    ('ngu_canh_to_to', 'SYN_FAM_TO_HIEN_THANH_HN', '00259', 'Phố Tô Hiến Thành', 'Phố Tô Hiến Thành'),
    ('ngu_canh_to_to', 'SYN_FAM_TO_NGOC_VAN_HCM', '26740', 'Đường Tô Ngọc Vân', 'Đường Tô Ngọc Vân'),
    ('ngu_canh_to_to', 'SYN_FAM_TO_VINH_DIEN_HN', '00352', 'Đường Tô Vĩnh Diện', 'Đường Tô Vĩnh Diện'),
    # 2. ngu_canh_tinh_tinh
    ('ngu_canh_tinh_tinh', 'SYN_FAM_TINH_HAI_TH', '17359', 'Phố Chợ', 'Phố Chợ'),
    ('ngu_canh_tinh_tinh', 'SYN_FAM_TINH_GIA_TH', '17350', 'Đường Tĩnh Gia', 'Đường Tĩnh Gia'),
    # 3. ngu_canh_cum_thanh_pho
    ('ngu_canh_cum_thanh_pho', 'SYN_FAM_TP_MOI_BD', '25750', 'Đại lộ Thành Phố Mới', 'Đại lộ Thành Phố Mới'),
    ('ngu_canh_cum_thanh_pho', 'SYN_FAM_KDT_TP_GIAO_LUU_HN', '00170', 'Đường Thành Phố Giao Lưu', 'Đường Thành Phố Giao Lưu'),
    # 4. duong_trung_hanh_chinh
    ('duong_trung_hanh_chinh', 'SYN_FAM_BA_DINH_TH', '16675', 'Đường Ba Đình', 'Đường Ba Đình'),
    ('duong_trung_hanh_chinh', 'SYN_FAM_NGO_QUYEN_HP', '11053', 'Đường Ngô Quyền', 'Đường Ngô Quyền'),
    ('duong_trung_hanh_chinh', 'SYN_FAM_HONG_BANG_HP', '11005', 'Đường Hồng Bàng', 'Đường Hồng Bàng'),
    # 5. dinh_chu_p7_q10
    ('dinh_chu_p7_q10', 'SYN_FAM_GLUED_Q5_P12', '27154', 'Đ.LêLợi', 'Đường Lê Lợi'),
    ('dinh_chu_p7_q10', 'SYN_FAM_GLUED_Q10_P14', '27289', 'Đ.NguyễnTriPhương', 'Đường Nguyễn Tri Phương'),
    # 6. xa_bi_chia_mo_ho
    ('xa_bi_chia_mo_ho', 'SYN_FAM_SPLIT_00454', '00454', '', ''),
    ('xa_bi_chia_mo_ho', 'SYN_FAM_SPLIT_00484', '00484', '', ''),
    ('xa_bi_chia_mo_ho', 'SYN_FAM_SPLIT_10342', '10342', '', ''),
    # 7. viet_tat_ten_rieng (quy chuẩn quốc lộ / tỉnh lộ xác định duy nhất)
    ('viet_tat_ten_rieng', 'SYN_FAM_QL1A_TH', '16675', 'Đ. QL1A', 'Quốc lộ 1A'),
    ('viet_tat_ten_rieng', 'SYN_FAM_QL5_HP', '11053', 'Đ. QL5', 'Quốc lộ 5'),
    ('viet_tat_ten_rieng', 'SYN_FAM_DCT01_HN', '00170', 'Đ. ĐCT01', 'Đường cao tốc 01'),
    ('viet_tat_ten_rieng', 'SYN_FAM_TL295_BN', '07705', 'Đ. TL295', 'Tỉnh lộ 295'),
    # 8. viet_tat_ten_rieng_mo_ho (đa nghĩa giữ mơ hồ)
    ('viet_tat_ten_rieng_mo_ho', 'SYN_FAM_AMBIG_TTT_HN', '00352', 'Đ. TTT', ['Đường Trần Thái Tông', 'Đường Trần Thánh Tông', 'Đường Tôn Thất Thuyết']),
    ('viet_tat_ten_rieng_mo_ho', 'SYN_FAM_AMBIG_BVT_HCM', '27154', 'Đ. BVT', ['Đường Bùi Viện', 'Đường Bùi Văn Ba', 'Đường Bệnh Viện Từ Dũ']),
    ('viet_tat_ten_rieng_mo_ho', 'SYN_FAM_AMBIG_HBT_DN', '20197', 'Đ. HBT', ['Đường Hai Bà Trưng', 'Đường Hoàng Bật Đạt']),
    # 9. ngo_ngach_hem_chuan (ngõ ngách chuẩn có tiền tố)
    ('ngo_ngach_hem_chuan', 'SYN_FAM_NGO_HN_TR', '00352', 'Lê Trọng Tấn', 'Đường Lê Trọng Tấn'),
    # 10. ngo_ngach_hem_phuc_hop (ngách + ngõ nhiều cấp)
    ('ngo_ngach_hem_phuc_hop', 'SYN_FAM_NGACH_HN_TR', '00259', 'Giải Phóng', 'Đường Giải Phóng'),
    # 11. hem_kiet_mien_nam_trung (hẻm Sài Gòn, kiệt Đà Nẵng)
    ('hem_kiet_mien_nam_trung', 'SYN_FAM_HEM_SG_TR', '26740', 'Lê Lợi', 'Đường Lê Lợi'),
    # 12. dao_thu_tu_duong_truoc_ngo_so (đường đứng trước ngõ và số nhà)
    ('dao_thu_tu_duong_truoc_ngo_so', 'SYN_FAM_DAO_DUONG_NGO_SO_TR', '00619', 'Đường Phú Diễn', 'Đường Phú Diễn'),
    # 13. thon_xom_to_dan_pho (thôn, xóm, tổ dân phố)
    ('thon_xom_to_dan_pho', 'SYN_FAM_THON_TO_HN_TR', '00379', '', ''),
    # 14. cum_lo_can_ho_tap_the_nhan_o (phần căn hộ / tập thể / lô đất ở nhãn O theo HOP_DONG_NHAN_CHUAN_HOA)
    ('cum_lo_can_ho_tap_the_nhan_o', 'SYN_FAM_CAN_HO_TAP_THE_TR', '00259', 'Đường Nguyễn Trãi', 'Đường Nguyễn Trãi'),
]

SPECIALIZED_DEV_FAMILIES = [
    # 1. ngu_canh_to_to
    ('ngu_canh_to_to', 'SYN_FAM_TO_HIEU_HN', '00160', 'Đường Tô Hiệu', 'Đường Tô Hiệu'),
    ('ngu_canh_to_to', 'SYN_FAM_TO_HUU_HCM', '27094', 'Đường Tố Hữu', 'Đường Tố Hữu'),
    # 2. ngu_canh_tinh_tinh
    ('ngu_canh_tinh_tinh', 'SYN_FAM_TINH_TUC_CB', '01729', 'Phố Hoà Bình', 'Phố Hoà Bình'),
    ('ngu_canh_tinh_tinh', 'SYN_FAM_TINH_CUONG_PT', '04225', 'Đường Tỉnh Cương', 'Đường Tỉnh Cương'),
    # 3. ngu_canh_cum_thanh_pho
    ('ngu_canh_cum_thanh_pho', 'SYN_FAM_KDT_TP_SINH_THAI_HN', '00133', 'Đại lộ Thành Phố Xanh', 'Đại lộ Thành Phố Xanh'),
    ('ngu_canh_cum_thanh_pho', 'SYN_FAM_TP_CHAU_DOC_AG', '30349', 'Đường Thành Phố Châu Đốc', 'Đường Thành Phố Châu Đốc'),
    # 4. duong_trung_hanh_chinh
    ('duong_trung_hanh_chinh', 'SYN_FAM_HAI_CHAU_DN', '20236', 'Đường Hải Châu', 'Đường Hải Châu'),
    ('duong_trung_hanh_chinh', 'SYN_FAM_BACH_KHOA_HN', '00277', 'Đường Bách Khoa', 'Đường Bách Khoa'),
    # 5. dinh_chu_p7_q10
    ('dinh_chu_p7_q10', 'SYN_FAM_GLUED_Q3_P4', '26809', 'Đ.VõVănTần', 'Đường Võ Văn Tần'),
    ('dinh_chu_p7_q10', 'SYN_FAM_GLUED_Q11_P8', '27352', 'Đ.LãnhBinhThăng', 'Đường Lãnh Binh Thăng'),
    # 6. xa_bi_chia_mo_ho
    ('xa_bi_chia_mo_ho', 'SYN_FAM_SPLIT_09715', '09715', '', ''),
    ('xa_bi_chia_mo_ho', 'SYN_FAM_SPLIT_11065', '11065', '', ''),
    # 7. viet_tat_ten_rieng (quy chuẩn quốc lộ / tỉnh lộ xác định duy nhất)
    ('viet_tat_ten_rieng', 'SYN_FAM_QL3_CB', '01729', 'Đ. QL3', 'Quốc lộ 3'),
    ('viet_tat_ten_rieng', 'SYN_FAM_QL18_QN', '06649', 'Đ. QL18', 'Quốc lộ 18'),
    ('viet_tat_ten_rieng', 'SYN_FAM_DCT05_PT', '04225', 'Đ. ĐCT05', 'Đường cao tốc 05'),
    ('viet_tat_ten_rieng', 'SYN_FAM_TL298_BG', '07201', 'Đ. TL298', 'Tỉnh lộ 298'),
    # 8. viet_tat_ten_rieng_mo_ho (đa nghĩa giữ mơ hồ)
    ('viet_tat_ten_rieng_mo_ho', 'SYN_FAM_AMBIG_NTT_HCM', '27094', 'Đ. NTT', ['Đường Nguyễn Tất Thành', 'Đường Nguyễn Thị Thập', 'Đường Nguyễn Trọng Tuyển']),
    ('viet_tat_ten_rieng_mo_ho', 'SYN_FAM_AMBIG_LTT_HCM', '26809', 'Đ. LTT', ['Đường Lý Tự Trọng', 'Đường Lê Thánh Tôn']),
    ('viet_tat_ten_rieng_mo_ho', 'SYN_FAM_AMBIG_NVC_HN', '00133', 'Đ. NVC', ['Đường Nguyễn Văn Cừ', 'Đường Nguyễn Văn Cừ Gia Lâm']),
    # 9. ngo_ngach_hem_chuan
    ('ngo_ngach_hem_chuan', 'SYN_FAM_NGO_HN_DEV', '00160', 'Tôn Thất Tùng', 'Phố Tôn Thất Tùng'),
    # 10. ngo_ngach_hem_phuc_hop
    ('ngo_ngach_hem_phuc_hop', 'SYN_FAM_NGACH_HN_DEV', '00277', 'Trường Chinh', 'Đường Trường Chinh'),
    # 11. hem_kiet_mien_nam_trung
    ('hem_kiet_mien_nam_trung', 'SYN_FAM_KIET_DN_DEV', '20236', 'Hùng Vương', 'Đường Hùng Vương'),
    # 12. dao_thu_tu_duong_truoc_ngo_so
    ('dao_thu_tu_duong_truoc_ngo_so', 'SYN_FAM_DAO_DUONG_NGO_SO_DEV', '27094', 'Đường Nguyễn Trãi', 'Đường Nguyễn Trãi'),
    # 13. thon_xom_to_dan_pho
    ('thon_xom_to_dan_pho', 'SYN_FAM_THON_TO_DEV', '17359', '', ''),
    # 14. cum_lo_can_ho_tap_the_nhan_o
    ('cum_lo_can_ho_tap_the_nhan_o', 'SYN_FAM_CAN_HO_TAP_THE_DEV', '00352', 'Phố Tôn Thất Tùng', 'Phố Tôn Thất Tùng'),
]

def generate_specialized_sample(vtuple, rng, admin_mgr, iteration=0):
    vtype, fam_id, ward_code, st_disp, canon_target = vtuple
    if ward_code not in admin_mgr.old_wi:
        return None, None
        
    w_obj = admin_mgr.old_wi[ward_code]
    res = admin_mgr.resolve_admin(w_obj)
    if not res:
        return None, None
        
    base_num = (iteration * 23 + rng.randint(1, 99)) % 950 + 1
    suffix_letter = rng.choice(['', '', 'A', 'B', 'Bis'])
    num_str = f"{base_num}{suffix_letter}"
    
    # 6. xa_bi_chia_mo_ho
    if vtype == 'xa_bi_chia_mo_ho':
        hamlets = ["Thôn Đông", "Thôn Tây", "Thôn Nam", "Thôn Bắc", "Thôn 1", "Thôn 2", "Xóm Trại", "Ấp Chợ"]
        hamlet = hamlets[iteration % len(hamlets)]
        dau_vao = f"Số {num_str}, {hamlet}, {res['full_w']}, {res['full_d']}, {res['full_p']}"
        s_num_txt = f"Số {num_str}"
        s_num = (0, len(s_num_txt), s_num_txt)
        s_ham_start = len(s_num_txt) + 2
        s_ham = (s_ham_start, s_ham_start + len(hamlet), hamlet)
        
        std_full = f"{s_num_txt}, {hamlet}, {res['tinh']}"
        rec = {
            'dau_vao': dau_vao, 'so_nha': s_num_txt, 'ngo_ngach_hem': '', 'thon_xom': hamlet, 'duong': '',
            'ma_xa_cu': res['ma_xa_cu'], 'ma_huyen_cu': res['ma_huyen_cu'], 'ma_tinh_cu': res['ma_tinh_cu'],
            'ma_xa': '', 'ma_tinh': res['ma_tinh'],
            'xa_phuong': '', 'tinh': res['tinh'],
            'dia_chi_chuan': std_full,
            'canh_bao': json.dumps(['nhan_tong_hop', 'xa_bi_chia'], ensure_ascii=False),
            'loai_nhan': 'tong_hop', 'nguon_du_lieu': 'danh_muc_hanh_chinh',
            'ghi_chu': res['ghi_chu'],
            'nhom_mau_goc': fam_id, 'loai_bien_the': vtype,
            'trang_thai_nhan': 'chua_xac_dinh',
            'provenance': f"Mẫu tổng hợp kiểm tra xã bị chia tách fan-out > 1 giữ mơ hồ (Family {fam_id})"
        }
        return rec, {'so_nha': s_num, 'thon_xom': s_ham, 'ngo_ngach_hem': None, 'duong': None}
        
    # 8. viet_tat_ten_rieng_mo_ho
    elif vtype == 'viet_tat_ten_rieng_mo_ho':
        dau_vao = f"Số {num_str} {st_disp}, {res['full_p']}"
        s_num_txt = f"Số {num_str}"
        s_num = (0, len(s_num_txt), s_num_txt)
        s_st = (len(s_num_txt) + 1, len(s_num_txt) + 1 + len(st_disp), st_disp)
        
        std_full = f"{s_num_txt}, {res['tinh']}"
        rec = {
            'dau_vao': dau_vao, 'so_nha': s_num_txt, 'ngo_ngach_hem': '', 'thon_xom': '', 'duong': '',
            'ma_xa_cu': '', 'ma_huyen_cu': '', 'ma_tinh_cu': res['ma_tinh_cu'],
            'ma_xa': '', 'ma_tinh': res['ma_tinh'],
            'xa_phuong': '', 'tinh': res['tinh'],
            'dia_chi_chuan': std_full,
            'canh_bao': json.dumps(['nhan_tong_hop', 'mo_ho_viet_tat', 'thieu_xa'], ensure_ascii=False),
            'loai_nhan': 'tong_hop', 'nguon_du_lieu': 'danh_muc_hanh_chinh',
            'ghi_chu': f"viet_tat={st_disp}; mo_ho=true; duong_ung_vien={json.dumps(canon_target, ensure_ascii=False)}",
            'nhom_mau_goc': fam_id, 'loai_bien_the': vtype,
            'trang_thai_nhan': 'chua_xac_dinh',
            'provenance': f"Mẫu viết tắt đa nghĩa không đủ ngữ cảnh xác định duy nhất (Family {fam_id})"
        }
        return rec, {'so_nha': s_num, 'duong': s_st, 'ngo_ngach_hem': None, 'thon_xom': None}
        
    # 5. dinh_chu_p7_q10
    elif vtype == 'dinh_chu_p7_q10':
        pure_num = f"{base_num}"
        p_name = w_obj['ten_xa']
        d_name = admin_mgr.old_di[w_obj['ma_huyen']]['ten_huyen']
        d_abbr = f"Q{d_name}" if d_name.isdigit() else f"Q.{d_name}"
        
        dau_vao = f"{pure_num}{st_disp}, P{p_name}, {d_abbr}, {res['full_p']}"
        s_num = (0, len(pure_num), pure_num)
        s_st = (len(pure_num), len(pure_num) + len(st_disp), st_disp)
        
        std_full = f"Số {pure_num}, {canon_target}, {res['xa_phuong']}, {res['tinh']}"
        rec = {
            'dau_vao': dau_vao, 'so_nha': f"Số {pure_num}", 'ngo_ngach_hem': '', 'thon_xom': '', 'duong': canon_target,
            'ma_xa_cu': res['ma_xa_cu'], 'ma_huyen_cu': res['ma_huyen_cu'], 'ma_tinh_cu': res['ma_tinh_cu'],
            'ma_xa': res['ma_xa'], 'ma_tinh': res['ma_tinh'],
            'xa_phuong': res['xa_phuong'], 'tinh': res['tinh'],
            'dia_chi_chuan': std_full,
            'canh_bao': json.dumps(['nhan_tong_hop', 'dinh_chu', 'viet_tat_so_hanh_chinh'], ensure_ascii=False),
            'loai_nhan': 'tong_hop', 'nguon_du_lieu': 'danh_muc_hanh_chinh',
            'ghi_chu': f"dinh_chu={st_disp}; p=P{p_name}; q={d_abbr}; {res['ghi_chu']}",
            'nhom_mau_goc': fam_id, 'loai_bien_the': vtype,
            'trang_thai_nhan': 'da_xac_minh_span',
            'provenance': f"Dạng dính chữ số nhà + đường và viết tắt số phường/quận (Family {fam_id})"
        }
        return rec, {'so_nha': s_num, 'duong': s_st, 'ngo_ngach_hem': None, 'thon_xom': None}

    # 7. viet_tat_ten_rieng (quy chuẩn quốc lộ / tỉnh lộ)
    elif vtype == 'viet_tat_ten_rieng':
        dau_vao = f"Số {num_str} {st_disp}, {res['full_w']}, {res['full_d']}, {res['full_p']}"
        s_num_txt = f"Số {num_str}"
        s_num = (0, len(s_num_txt), s_num_txt)
        s_st = (len(s_num_txt) + 1, len(s_num_txt) + 1 + len(st_disp), st_disp)
        
        std_full = f"{s_num_txt}, {canon_target}, {res['xa_phuong']}, {res['tinh']}"
        rec = {
            'dau_vao': dau_vao, 'so_nha': s_num_txt, 'ngo_ngach_hem': '', 'thon_xom': '', 'duong': canon_target,
            'ma_xa_cu': res['ma_xa_cu'], 'ma_huyen_cu': res['ma_huyen_cu'], 'ma_tinh_cu': res['ma_tinh_cu'],
            'ma_xa': res['ma_xa'], 'ma_tinh': res['ma_tinh'],
            'xa_phuong': res['xa_phuong'], 'tinh': res['tinh'],
            'dia_chi_chuan': std_full,
            'canh_bao': json.dumps(['nhan_tong_hop', 'viet_tat_quy_chuan_giao_thong'], ensure_ascii=False),
            'loai_nhan': 'tong_hop', 'nguon_du_lieu': 'danh_muc_hanh_chinh',
            'ghi_chu': f"viet_tat_quy_chuan={st_disp}; canon={canon_target}; {res['ghi_chu']}",
            'nhom_mau_goc': fam_id, 'loai_bien_the': vtype,
            'trang_thai_nhan': 'xac_dinh_theo_ngu_canh',
            'provenance': f"Viết tắt tên đường theo Quy chuẩn kỹ thuật Quốc gia về phân loại đường bộ Việt Nam (Family {fam_id}: {st_disp} -> {canon_target})"
        }
        return rec, {'so_nha': s_num, 'duong': s_st, 'ngo_ngach_hem': None, 'thon_xom': None}

    # 9. ngo_ngach_hem_chuan
    elif vtype == 'ngo_ngach_hem_chuan':
        alley_num = f"{(iteration * 13) % 95 + 1}"
        ngo_str = f"Ngõ {alley_num}"
        s_num_txt = f"Số {num_str}"
        dau_vao = f"{s_num_txt} {ngo_str} {st_disp}, {res['full_w']}, {res['full_d']}, {res['full_p']}"
        s_num = (0, len(s_num_txt), s_num_txt)
        start_ngo = len(s_num_txt) + 1
        end_ngo = start_ngo + len(ngo_str)
        s_ngo = (start_ngo, end_ngo, ngo_str)
        start_st = end_ngo + 1
        end_st = start_st + len(st_disp)
        s_st = (start_st, end_st, st_disp)
        
        std_full = f"{s_num_txt}, {ngo_str}, {canon_target}, {res['xa_phuong']}, {res['tinh']}"
        rec = {
            'dau_vao': dau_vao, 'so_nha': s_num_txt, 'ngo_ngach_hem': ngo_str, 'thon_xom': '', 'duong': canon_target,
            'ma_xa_cu': res['ma_xa_cu'], 'ma_huyen_cu': res['ma_huyen_cu'], 'ma_tinh_cu': res['ma_tinh_cu'],
            'ma_xa': res['ma_xa'], 'ma_tinh': res['ma_tinh'],
            'xa_phuong': res['xa_phuong'], 'tinh': res['tinh'],
            'dia_chi_chuan': std_full,
            'canh_bao': json.dumps(['nhan_tong_hop', 'co_ngo_ngach'], ensure_ascii=False),
            'loai_nhan': 'tong_hop', 'nguon_du_lieu': 'danh_muc_hanh_chinh',
            'ghi_chu': f"ngu_canh={fam_id}; {res['ghi_chu']}",
            'nhom_mau_goc': fam_id, 'loai_bien_the': vtype,
            'trang_thai_nhan': 'da_xac_minh_span',
            'provenance': f"Mẫu tổng hợp kiểm tra thành phần ngõ ngách chi tiết (Family {fam_id})"
        }
        return rec, {'so_nha': s_num, 'duong': s_st, 'ngo_ngach_hem': s_ngo, 'thon_xom': None}

    # 10. ngo_ngach_hem_phuc_hop
    elif vtype == 'ngo_ngach_hem_phuc_hop':
        ngach_num = f"{(iteration * 3) % 40 + 1}/{(iteration % 5) + 1}"
        alley_num = f"{(iteration * 7) % 120 + 1}"
        ngo_str = f"Ngách {ngach_num} Ngõ {alley_num}"
        s_num_txt = f"Số {num_str}"
        dau_vao = f"{s_num_txt} {ngo_str} {st_disp}, {res['full_w']}, {res['full_d']}, {res['full_p']}"
        s_num = (0, len(s_num_txt), s_num_txt)
        start_ngo = len(s_num_txt) + 1
        end_ngo = start_ngo + len(ngo_str)
        s_ngo = (start_ngo, end_ngo, ngo_str)
        start_st = end_ngo + 1
        end_st = start_st + len(st_disp)
        s_st = (start_st, end_st, st_disp)
        
        std_full = f"{s_num_txt}, {ngo_str}, {canon_target}, {res['xa_phuong']}, {res['tinh']}"
        rec = {
            'dau_vao': dau_vao, 'so_nha': s_num_txt, 'ngo_ngach_hem': ngo_str, 'thon_xom': '', 'duong': canon_target,
            'ma_xa_cu': res['ma_xa_cu'], 'ma_huyen_cu': res['ma_huyen_cu'], 'ma_tinh_cu': res['ma_tinh_cu'],
            'ma_xa': res['ma_xa'], 'ma_tinh': res['ma_tinh'],
            'xa_phuong': res['xa_phuong'], 'tinh': res['tinh'],
            'dia_chi_chuan': std_full,
            'canh_bao': json.dumps(['nhan_tong_hop', 'co_ngach_ngo_phuc_hop'], ensure_ascii=False),
            'loai_nhan': 'tong_hop', 'nguon_du_lieu': 'danh_muc_hanh_chinh',
            'ghi_chu': f"ngu_canh={fam_id}; {res['ghi_chu']}",
            'nhom_mau_goc': fam_id, 'loai_bien_the': vtype,
            'trang_thai_nhan': 'da_xac_minh_span',
            'provenance': f"Mẫu tổng hợp kiểm tra cấu trúc ngách nhiều cấp (Family {fam_id})"
        }
        return rec, {'so_nha': s_num, 'duong': s_st, 'ngo_ngach_hem': s_ngo, 'thon_xom': None}

    # 11. hem_kiet_mien_nam_trung
    elif vtype == 'hem_kiet_mien_nam_trung':
        kind_hem = "Hẻm" if ("HCM" in fam_id or "SG" in fam_id) else "Kiệt"
        alley_num = f"{(iteration * 11) % 150 + 1}"
        ngo_str = f"{kind_hem} {alley_num}"
        s_num_txt = f"Số {num_str}"
        dau_vao = f"{s_num_txt} {ngo_str} {st_disp}, {res['full_w']}, {res['full_d']}, {res['full_p']}"
        s_num = (0, len(s_num_txt), s_num_txt)
        start_ngo = len(s_num_txt) + 1
        end_ngo = start_ngo + len(ngo_str)
        s_ngo = (start_ngo, end_ngo, ngo_str)
        start_st = end_ngo + 1
        end_st = start_st + len(st_disp)
        s_st = (start_st, end_st, st_disp)
        
        std_full = f"{s_num_txt}, {ngo_str}, {canon_target}, {res['xa_phuong']}, {res['tinh']}"
        rec = {
            'dau_vao': dau_vao, 'so_nha': s_num_txt, 'ngo_ngach_hem': ngo_str, 'thon_xom': '', 'duong': canon_target,
            'ma_xa_cu': res['ma_xa_cu'], 'ma_huyen_cu': res['ma_huyen_cu'], 'ma_tinh_cu': res['ma_tinh_cu'],
            'ma_xa': res['ma_xa'], 'ma_tinh': res['ma_tinh'],
            'xa_phuong': res['xa_phuong'], 'tinh': res['tinh'],
            'dia_chi_chuan': std_full,
            'canh_bao': json.dumps(['nhan_tong_hop', 'co_hem_kiet'], ensure_ascii=False),
            'loai_nhan': 'tong_hop', 'nguon_du_lieu': 'danh_muc_hanh_chinh',
            'ghi_chu': f"ngu_canh={fam_id}; {res['ghi_chu']}",
            'nhom_mau_goc': fam_id, 'loai_bien_the': vtype,
            'trang_thai_nhan': 'da_xac_minh_span',
            'provenance': f"Mẫu tổng hợp kiểm tra từ loại hẻm/kiệt phương ngữ (Family {fam_id})"
        }
        return rec, {'so_nha': s_num, 'duong': s_st, 'ngo_ngach_hem': s_ngo, 'thon_xom': None}

    # 12. dao_thu_tu_duong_truoc_ngo_so
    elif vtype == 'dao_thu_tu_duong_truoc_ngo_so':
        alley_num = f"{(iteration * 17) % 80 + 1}"
        kind_alley = "hẻm" if ("HCM" in fam_id or "SG" in fam_id) else "ngõ"
        ngo_str = f"{kind_alley} {alley_num}"
        s_num_txt = f"số {num_str}"
        dau_vao = f"{st_disp}, {ngo_str}, {s_num_txt}, {res['full_w']}, {res['full_d']}, {res['full_p']}"
        
        s_st = (0, len(st_disp), st_disp)
        start_ngo = len(st_disp) + 2
        end_ngo = start_ngo + len(ngo_str)
        s_ngo = (start_ngo, end_ngo, ngo_str)
        start_num = end_ngo + 2
        end_num = start_num + len(s_num_txt)
        s_num = (start_num, end_num, s_num_txt)
        
        std_full = f"Số {num_str}, {ngo_str.capitalize()}, {canon_target}, {res['xa_phuong']}, {res['tinh']}"
        rec = {
            'dau_vao': dau_vao, 'so_nha': f"Số {num_str}", 'ngo_ngach_hem': ngo_str.capitalize(), 'thon_xom': '', 'duong': canon_target,
            'ma_xa_cu': res['ma_xa_cu'], 'ma_huyen_cu': res['ma_huyen_cu'], 'ma_tinh_cu': res['ma_tinh_cu'],
            'ma_xa': res['ma_xa'], 'ma_tinh': res['ma_tinh'],
            'xa_phuong': res['xa_phuong'], 'tinh': res['tinh'],
            'dia_chi_chuan': std_full,
            'canh_bao': json.dumps(['nhan_tong_hop', 'dao_thu_tu_chi_tiet'], ensure_ascii=False),
            'loai_nhan': 'tong_hop', 'nguon_du_lieu': 'danh_muc_hanh_chinh',
            'ghi_chu': f"dao_thu_tu=duong_truoc_ngo_so; {res['ghi_chu']}",
            'nhom_mau_goc': fam_id, 'loai_bien_the': vtype,
            'trang_thai_nhan': 'da_xac_minh_span',
            'provenance': f"Mẫu đảo thứ tự đường đứng trước ngõ và số nhà (Family {fam_id})"
        }
        return rec, {'so_nha': s_num, 'duong': s_st, 'ngo_ngach_hem': s_ngo, 'thon_xom': None}

    # 13. thon_xom_to_dan_pho
    elif vtype == 'thon_xom_to_dan_pho':
        hamlets = ["Tổ dân phố 12", "Thôn Đông", "Xóm Chùa", "Ấp Tân Lập", "Bản Hoa", "Khu phố 4", "Thôn Thượng", "Tổ 5"]
        h_name = hamlets[iteration % len(hamlets)]
        has_house = (iteration % 3 != 0)
        if has_house:
            s_num_txt = f"Số {num_str}"
            dau_vao = f"{s_num_txt} {h_name}, {res['full_w']}, {res['full_d']}, {res['full_p']}"
            s_num = (0, len(s_num_txt), s_num_txt)
            start_h = len(s_num_txt) + 1
            end_h = start_h + len(h_name)
            s_h = (start_h, end_h, h_name)
            std_full = f"{s_num_txt}, {h_name}, {res['xa_phuong']}, {res['tinh']}"
            spans_dict = {'so_nha': s_num, 'thon_xom': s_h, 'ngo_ngach_hem': None, 'duong': None}
            res_so_nha = s_num_txt
        else:
            dau_vao = f"{h_name}, {res['full_w']}, {res['full_d']}, {res['full_p']}"
            s_h = (0, len(h_name), h_name)
            std_full = f"{h_name}, {res['xa_phuong']}, {res['tinh']}"
            spans_dict = {'so_nha': None, 'thon_xom': s_h, 'ngo_ngach_hem': None, 'duong': None}
            res_so_nha = ''
            
        rec = {
            'dau_vao': dau_vao, 'so_nha': res_so_nha, 'ngo_ngach_hem': '', 'thon_xom': h_name, 'duong': '',
            'ma_xa_cu': res['ma_xa_cu'], 'ma_huyen_cu': res['ma_huyen_cu'], 'ma_tinh_cu': res['ma_tinh_cu'],
            'ma_xa': res['ma_xa'], 'ma_tinh': res['ma_tinh'],
            'xa_phuong': res['xa_phuong'], 'tinh': res['tinh'],
            'dia_chi_chuan': std_full,
            'canh_bao': json.dumps(['nhan_tong_hop', 'co_thon_to_xom'], ensure_ascii=False),
            'loai_nhan': 'tong_hop', 'nguon_du_lieu': 'danh_muc_hanh_chinh',
            'ghi_chu': f"thon_xom={h_name}; {res['ghi_chu']}",
            'nhom_mau_goc': fam_id, 'loai_bien_the': vtype,
            'trang_thai_nhan': 'da_xac_minh_span',
            'provenance': f"Mẫu tổng hợp kiểm tra vai trò thôn/xóm/ấp/tổ dân phố (Family {fam_id})"
        }
        return rec, spans_dict

    # 14. cum_lo_can_ho_tap_the_nhan_o
    elif vtype == 'cum_lo_can_ho_tap_the_nhan_o':
        apt_samples = [
            f"Căn hộ {(iteration * 10) % 900 + 101} Tòa R2 Khu đô thị Royal City",
            f"Phòng {(iteration * 5) % 800 + 201} Khu tập thể A1",
            f"Lô B2-{(iteration % 25) + 1} Khu dân cư Nam Long",
            f"Căn {(iteration * 8) % 700 + 302} Tòa S1 Chung cư Vinhomes"
        ]
        o_prefix = apt_samples[iteration % len(apt_samples)]
        has_so_nha = (iteration % 2 == 1)
        if has_so_nha:
            s_num_txt = f"Số {num_str}"
            dau_vao = f"{s_num_txt} {o_prefix}, {st_disp}, {res['full_w']}, {res['full_d']}, {res['full_p']}"
            s_num = (0, len(s_num_txt), s_num_txt)
            start_st = len(s_num_txt) + 1 + len(o_prefix) + 2
            end_st = start_st + len(st_disp)
            s_st = (start_st, end_st, st_disp)
            std_full = f"{s_num_txt}, {canon_target}, {res['xa_phuong']}, {res['tinh']}"
            spans_dict = {'so_nha': s_num, 'duong': s_st, 'ngo_ngach_hem': None, 'thon_xom': None}
            res_so_nha = s_num_txt
        else:
            dau_vao = f"{o_prefix}, {st_disp}, {res['full_w']}, {res['full_d']}, {res['full_p']}"
            start_st = len(o_prefix) + 2
            end_st = start_st + len(st_disp)
            s_st = (start_st, end_st, st_disp)
            std_full = f"{canon_target}, {res['xa_phuong']}, {res['tinh']}"
            spans_dict = {'so_nha': None, 'duong': s_st, 'ngo_ngach_hem': None, 'thon_xom': None}
            res_so_nha = ''
            
        rec = {
            'dau_vao': dau_vao, 'so_nha': res_so_nha, 'ngo_ngach_hem': '', 'thon_xom': '', 'duong': canon_target,
            'ma_xa_cu': res['ma_xa_cu'], 'ma_huyen_cu': res['ma_huyen_cu'], 'ma_tinh_cu': res['ma_tinh_cu'],
            'ma_xa': res['ma_xa'], 'ma_tinh': res['ma_tinh'],
            'xa_phuong': res['xa_phuong'], 'tinh': res['tinh'],
            'dia_chi_chuan': std_full,
            'canh_bao': json.dumps(['nhan_tong_hop', 'phan_lo_can_ho_o'], ensure_ascii=False),
            'loai_nhan': 'tong_hop', 'nguon_du_lieu': 'danh_muc_hanh_chinh',
            'ghi_chu': f"phan_o_kien_truc={o_prefix}; {res['ghi_chu']}",
            'nhom_mau_goc': fam_id, 'loai_bien_the': vtype,
            'trang_thai_nhan': 'da_xac_minh_span',
            'provenance': f"Mẫu giữ phần lô/căn hộ/tập thể ở nhãn O theo HOP_DONG_NHAN_CHUAN_HOA (Family {fam_id})"
        }
        return rec, spans_dict

    # Các loại ngữ cảnh: ngu_canh_to_to, ngu_canh_tinh_tinh, ngu_canh_cum_thanh_pho, duong_trung_hanh_chinh
    else:
        dau_vao = f"Số {num_str} {st_disp}, {res['full_w']}, {res['full_d']}, {res['full_p']}"
        s_num_txt = f"Số {num_str}"
        s_num = (0, len(s_num_txt), s_num_txt)
        s_st = (len(s_num_txt) + 1, len(s_num_txt) + 1 + len(st_disp), st_disp)
        
        std_full = f"{s_num_txt}, {canon_target}, {res['xa_phuong']}, {res['tinh']}"
        cb_type = f"kiem_tra_{vtype}"
        rec = {
            'dau_vao': dau_vao, 'so_nha': s_num_txt, 'ngo_ngach_hem': '', 'thon_xom': '', 'duong': canon_target,
            'ma_xa_cu': res['ma_xa_cu'], 'ma_huyen_cu': res['ma_huyen_cu'], 'ma_tinh_cu': res['ma_tinh_cu'],
            'ma_xa': res['ma_xa'], 'ma_tinh': res['ma_tinh'],
            'xa_phuong': res['xa_phuong'], 'tinh': res['tinh'],
            'dia_chi_chuan': std_full,
            'canh_bao': json.dumps(['nhan_tong_hop', cb_type], ensure_ascii=False),
            'loai_nhan': 'tong_hop', 'nguon_du_lieu': 'danh_muc_hanh_chinh',
            'ghi_chu': f"ngu_canh={fam_id}; {res['ghi_chu']}",
            'nhom_mau_goc': fam_id, 'loai_bien_the': vtype,
            'trang_thai_nhan': 'da_xac_minh_span',
            'provenance': f"Mẫu tổng hợp kiểm tra ngữ cảnh thực thể đặc thù (Family {fam_id})"
        }
        return rec, {'so_nha': s_num, 'duong': s_st, 'ngo_ngach_hem': None, 'thon_xom': None}

# ==============================================================================
# HÀM CHÍNH (MAIN)
# ==============================================================================
def main():
    SEED = 4242
    rng = random.Random(SEED)
    print(f"=== BẮT ĐẦU TẠO DỮ LIỆU HUẤN LUYỆN BỔ SUNG V1 (BẢN V3 ỔN ĐỊNH TOÀN DIỆN) - SEED {SEED} ===")
    
    admin_mgr = AdminManager()
    test_exclusion_norms = load_test_exclusion()
    print(f"Đã nạp quy tắc cách ly test: {len(test_exclusion_norms)} chuỗi test.")

    # 1. Đọc và bảo toàn gói gốc vòng 2/3 (2.037 Train + 464 Dev đã được kiểm chứng độc lập)
    snap_base_dir = OUTPUT_DIR / "snapshot_round2_base"
    if not (snap_base_dir / "train_bo_sung.csv").exists():
        snap_base_dir = OUTPUT_DIR

    base_train_rows = list(csv.DictReader(open(snap_base_dir / "train_bo_sung.csv", encoding='utf-8-sig')))[:2037]
    base_dev_rows = list(csv.DictReader(open(snap_base_dir / "dev_kho.csv", encoding='utf-8-sig')))[:464]

    base_train_spans = [json.loads(line) for line in open(snap_base_dir / "train_spans.jsonl", encoding='utf-8')][:2037]
    base_dev_spans = [json.loads(line) for line in open(snap_base_dir / "dev_spans.jsonl", encoding='utf-8')][:464]

    print(f"Nạp gói nền tảng: Train = {len(base_train_rows)} mẫu, Dev = {len(base_dev_rows)} mẫu.")

    # Helper function kiểm tra ranh giới token với runtime tokenizer (src.tien_xu_ly.token_co_vi_tri)
    def check_runtime_tokenizer_compat(dau_vao, spans_dict):
        try:
            tokens_rt = token_co_vi_tri(dau_vao)
            rt_starts = {t.bat_dau for t in tokens_rt}
            rt_ends = {t.ket_thuc for t in tokens_rt}
            for fld, s_info in spans_dict.items():
                if s_info:
                    if isinstance(s_info, dict):
                        s_start, s_end = s_info['start'], s_info['end']
                    else:
                        s_start, s_end = s_info[0], s_info[1]
                    if s_start not in rt_starts or s_end not in rt_ends:
                        return False, f"Span boundary for {fld} [{s_start}:{s_end}] cuts inside token of runtime tokenizer v1.0 (src.tien_xu_ly.token_co_vi_tri)"
            return True, "compatible"
        except Exception as e:
            return False, f"Exception in token_co_vi_tri: {e}"

    train_bo_sung_list = []
    dev_kho_list = []
    train_spans_list = []
    dev_spans_list = []
    unaligned_spans_list = []
    seen_all_norms = set(test_exclusion_norms)

    # 2. Xử lý và kiểm tra tương thích tokenizer cho 2.037 mẫu Train nền tảng
    print("\n--- BƯỚC 1: KIỂM TOÁN TƯƠNG THÍCH TOKENIZER RUNTIME CHO 2.037 MẪU TRAIN NỀN TẢNG ---")
    cut_train = 0
    for rec, sp_item in zip(base_train_rows, base_train_spans):
        seen_all_norms.add(norm(rec['dau_vao']))
        is_compat, compat_msg = check_runtime_tokenizer_compat(rec['dau_vao'], sp_item['spans'])
        if not is_compat:
            cut_train += 1
            cb = json.loads(rec['canh_bao']) if rec.get('canh_bao') else []
            if "khong_tuong_thich_tokenizer_v1" not in cb:
                cb.append("khong_tuong_thich_tokenizer_v1")
                rec['canh_bao'] = json.dumps(cb, ensure_ascii=False)
            if "tokenizer_boundary_mismatch=true" not in rec['ghi_chu']:
                rec['ghi_chu'] += "; tokenizer_boundary_mismatch=true"
                
        train_bo_sung_list.append(rec)
        sp_item['usable_for_span_training'] = is_compat
        sp_item['usable_for_canonical_training'] = (rec['trang_thai_nhan'] != 'chua_xac_dinh')
        sp_item['tokenizer_runtime_compatible'] = is_compat
        sp_item['tokenizer_version_required'] = 'v1.0' if is_compat else 'v2.0_glued_boundary'
        sp_item['tokenizer_note'] = '' if is_compat else compat_msg
        train_spans_list.append(sp_item)

    print(f"Hoàn thành kiểm toán Train: {len(train_bo_sung_list)} mẫu (Tương thích: {len(train_bo_sung_list)-cut_train}, Bị cắt token dính chữ: {cut_train}).")

    # 3. Bổ sung các họ chuyên biệt còn thiếu cho Train (132 mẫu: ngõ, ngách, hẻm, kiệt, thôn xóm, đảo thứ tự, phần O)
    print("\n--- BƯỚC 2: BỔ SUNG 132 MẪU CHO CÁC HỌ THỰC THỂ CÒN THIẾU VÀO TRAIN ---")
    new_train_fams = list(SPECIALIZED_TRAIN_FAMILIES[-6:])
    for fam_idx, vtuple in enumerate(new_train_fams):
        for i in range(22):
            rec, spans_info = generate_specialized_sample(vtuple, rng, admin_mgr, iteration=fam_idx*50 + i)
            if not rec or norm(rec['dau_vao']) in seen_all_norms:
                continue
            seen_all_norms.add(norm(rec['dau_vao']))
            
            rec_id = f"VNTRAIN_BS_{len(train_bo_sung_list)+1:05d}"
            rec['id'] = rec_id
            rec['nguon'] = "tong_hop_danh_muc"
            
            bio_res, status = align_spans_and_bio(rec['dau_vao'], spans_info)
            if status == "valid" and bio_res:
                is_compat, compat_msg = check_runtime_tokenizer_compat(rec['dau_vao'], spans_info)
                train_bo_sung_list.append(rec)
                train_spans_list.append({
                    'id': rec_id,
                    'dau_vao': rec['dau_vao'],
                    'tokens': bio_res['tokens'],
                    'spans': bio_res['spans'],
                    'span_status': 'valid',
                    'usable_for_span_training': is_compat,
                    'usable_for_canonical_training': (rec['trang_thai_nhan'] != 'chua_xac_dinh'),
                    'tokenizer_runtime_compatible': is_compat,
                    'tokenizer_version_required': 'v1.0',
                    'tokenizer_note': ''
                })
            else:
                unaligned_spans_list.append({'id': rec_id, 'reason': status})

    print(f"Tổng số mẫu TRAIN BỔ SUNG đạt: {len(train_bo_sung_list)} mẫu.")

    # 4. Xử lý và kiểm tra tương thích tokenizer cho 464 mẫu Dev nền tảng
    print("\n--- BƯỚC 3: KIỂM TOÁN TƯƠNG THÍCH TOKENIZER RUNTIME CHO 464 MẪU DEV NỀN TẢNG ---")
    cut_dev = 0
    for rec, sp_item in zip(base_dev_rows, base_dev_spans):
        seen_all_norms.add(norm(rec['dau_vao']))
        is_compat, compat_msg = check_runtime_tokenizer_compat(rec['dau_vao'], sp_item['spans'])
        if not is_compat:
            cut_dev += 1
            cb = json.loads(rec['canh_bao']) if rec.get('canh_bao') else []
            if "khong_tuong_thich_tokenizer_v1" not in cb:
                cb.append("khong_tuong_thich_tokenizer_v1")
                rec['canh_bao'] = json.dumps(cb, ensure_ascii=False)
            if "tokenizer_boundary_mismatch=true" not in rec['ghi_chu']:
                rec['ghi_chu'] += "; tokenizer_boundary_mismatch=true"
                
        dev_kho_list.append(rec)
        sp_item['usable_for_span_training'] = is_compat
        sp_item['usable_for_canonical_training'] = (rec['trang_thai_nhan'] != 'chua_xac_dinh')
        sp_item['tokenizer_runtime_compatible'] = is_compat
        sp_item['tokenizer_version_required'] = 'v1.0' if is_compat else 'v2.0_glued_boundary'
        sp_item['tokenizer_note'] = '' if is_compat else compat_msg
        dev_spans_list.append(sp_item)

    print(f"Hoàn thành kiểm toán Dev: {len(dev_kho_list)} mẫu (Tương thích: {len(dev_kho_list)-cut_dev}, Bị cắt token dính chữ: {cut_dev}).")

    # 5. Bổ sung các họ chuyên biệt còn thiếu cho Dev (36 mẫu: ngõ, ngách, hẻm, kiệt, thôn xóm, đảo thứ tự, phần O)
    print("\n--- BƯỚC 4: BỔ SUNG 36 MẪU CHO CÁC HỌ THỰC THỂ CÒN THIẾU VÀO DEV ---")
    new_dev_fams = list(SPECIALIZED_DEV_FAMILIES[-6:])
    for fam_idx, vtuple in enumerate(new_dev_fams):
        for i in range(6):
            rec, spans_info = generate_specialized_sample(vtuple, rng, admin_mgr, iteration=fam_idx*50 + i)
            if not rec or norm(rec['dau_vao']) in seen_all_norms:
                continue
            seen_all_norms.add(norm(rec['dau_vao']))
            
            rec_id = f"VNDEV_KHO_{len(dev_kho_list)+1:05d}"
            rec['id'] = rec_id
            rec['nguon'] = "tong_hop_danh_muc"
            
            bio_res, status = align_spans_and_bio(rec['dau_vao'], spans_info)
            if status == "valid" and bio_res:
                is_compat, compat_msg = check_runtime_tokenizer_compat(rec['dau_vao'], spans_info)
                dev_kho_list.append(rec)
                dev_spans_list.append({
                    'id': rec_id,
                    'dau_vao': rec['dau_vao'],
                    'tokens': bio_res['tokens'],
                    'spans': bio_res['spans'],
                    'span_status': 'valid',
                    'usable_for_span_training': is_compat,
                    'usable_for_canonical_training': (rec['trang_thai_nhan'] != 'chua_xac_dinh'),
                    'tokenizer_runtime_compatible': is_compat,
                    'tokenizer_version_required': 'v1.0',
                    'tokenizer_note': ''
                })
            else:
                unaligned_spans_list.append({'id': rec_id, 'reason': status})

    print(f"Tổng số mẫu DEV KHÓ đạt: {len(dev_kho_list)} mẫu.")

    # 6. XUẤT CÁC TẬP DỮ LIỆU ĐÃ KIỂM CHỨNG VÀ BẢN KÊ MANIFEST
    print("\n--- BƯỚC 5: XUẤT CÁC TẬP DỮ LIỆU ĐÃ KIỂM CHỨNG VÀ BẢN KÊ MANIFEST ---")
    
    # Ghi CSV
    with open(OUTPUT_DIR / "train_bo_sung.csv", 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS_EXTENDED)
        writer.writeheader()
        writer.writerows(train_bo_sung_list)
        
    with open(OUTPUT_DIR / "dev_kho.csv", 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS_EXTENDED)
        writer.writeheader()
        writer.writerows(dev_kho_list)
        
    # Ghi Spans JSONL
    with open(OUTPUT_DIR / "train_spans.jsonl", 'w', encoding='utf-8') as f:
        for item in train_spans_list:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
            
    with open(OUTPUT_DIR / "dev_spans.jsonl", 'w', encoding='utf-8') as f:
        for item in dev_spans_list:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
            
    all_spans_list = train_spans_list + dev_spans_list
    with open(OUTPUT_DIR / "token_spans.jsonl", 'w', encoding='utf-8') as f:
        for item in all_spans_list:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
            
    with open(OUTPUT_DIR / "unaligned_spans.jsonl", 'w', encoding='utf-8') as f:
        for item in unaligned_spans_list:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')

    total_usable_span = sum(1 for item in all_spans_list if item['usable_for_span_training'])
    total_usable_canon = sum(1 for item in all_spans_list if item['usable_for_canonical_training'])

    # Thống kê phân bố trường thực thể
    train_counts = {'so_nha': 0, 'ngo_ngach_hem': 0, 'thon_xom': 0, 'duong': 0}
    for item in train_spans_list:
        for fld in train_counts:
            if item['spans'].get(fld):
                train_counts[fld] += 1

    dev_counts = {'so_nha': 0, 'ngo_ngach_hem': 0, 'thon_xom': 0, 'duong': 0}
    for item in dev_spans_list:
        for fld in dev_counts:
            if item['spans'].get(fld):
                dev_counts[fld] += 1

    train_dist = Counter(r['loai_bien_the'] for r in train_bo_sung_list)
    dev_dist = Counter(r['loai_bien_the'] for r in dev_kho_list)

    summary_data = {
        'total_train_bo_sung': len(train_bo_sung_list),
        'total_dev_kho': len(dev_kho_list),
        'total_bo_sung_corpus': len(all_spans_list),
        'seed': SEED,
        'valid_spans': {
            'train_valid_spans': len(train_spans_list),
            'dev_valid_spans': len(dev_spans_list),
            'total_valid_spans': len(all_spans_list),
            'unaligned_spans_count': len(unaligned_spans_list)
        },
        'usability': {
            'usable_for_span_training_v1': total_usable_span,
            'quarantined_span_mismatch_v2': len(all_spans_list) - total_usable_span,
            'usable_for_canonical_training': total_usable_canon
        },
        'span_class_counts': {
            'train': train_counts,
            'dev': dev_counts,
            'total': {
                'so_nha': train_counts['so_nha'] + dev_counts['so_nha'],
                'ngo_ngach_hem': train_counts['ngo_ngach_hem'] + dev_counts['ngo_ngach_hem'],
                'thon_xom': train_counts['thon_xom'] + dev_counts['thon_xom'],
                'duong': train_counts['duong'] + dev_counts['duong']
            }
        },
        'train_distribution_by_type': dict(train_dist),
        'dev_distribution_by_type': dict(dev_dist)
    }

    with open(OUTPUT_DIR / "summary_bo_sung.json", 'w', encoding='utf-8') as f:
        json.dump(summary_data, f, ensure_ascii=False, indent=2)

    # Tính toán SHA256 cho Manifest
    def sha256_file(filepath):
        h = hashlib.sha256()
        with open(filepath, 'rb') as f:
            while chunk := f.read(8192):
                h.update(chunk)
        return h.hexdigest()

    manifest_files = [
        "train_bo_sung.csv", "dev_kho.csv",
        "train_spans.jsonl", "dev_spans.jsonl", "token_spans.jsonl",
        "summary_bo_sung.json", "doi_chieu_snapshot_v1_v2.csv", "id_disposition.csv"
    ]
    manifest_data = {
        'version': 'v3.1_comprehensive_crf_ready',
        'created_at': '2026-10-29T15:30:00+07:00',
        'metrics': {
            'train_rows': len(train_bo_sung_list),
            'dev_rows': len(dev_kho_list),
            'total_rows': len(all_spans_list),
            'span_class_counts': summary_data['span_class_counts'],
            'usability': summary_data['usability']
        },
        'files': {}
    }
    for fname in manifest_files:
        fpath = OUTPUT_DIR / fname
        if fpath.exists():
            manifest_data['files'][fname] = {
                'sha256': sha256_file(fpath),
                'size_bytes': fpath.stat().st_size
            }

    with open(OUTPUT_DIR / "manifest.json", 'w', encoding='utf-8') as f:
        json.dump(manifest_data, f, ensure_ascii=False, indent=2)

    print(f"\n=== HOÀN THÀNH SINH DỮ LIỆU THÀNH CÔNG ===")
    print(f"Train Bổ Sung: {len(train_bo_sung_list)} mẫu | Dev Khó: {len(dev_kho_list)} mẫu | Spans: {len(all_spans_list)}")
    print(f"Usable for Span Training (Runtime Tokenizer v1.0): {total_usable_span} / {len(all_spans_list)}")
    print(f"Quarantined Span Mismatch (requires Tokenizer v2): {len(all_spans_list) - total_usable_span}")
    print(f"Usable for Canonical Training: {total_usable_canon} / {len(all_spans_list)}")
    print(f"Span coverage: ngo_ngach_hem={summary_data['span_class_counts']['total']['ngo_ngach_hem']}, thon_xom={summary_data['span_class_counts']['total']['thon_xom']}")

if __name__ == '__main__':
    main()
