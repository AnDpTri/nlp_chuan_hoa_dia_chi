#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script chuẩn bị dữ liệu train/dev cho bài toán chuẩn hóa địa chỉ:
- Mốc mục tiêu: 01/07/2025 (Nghị quyết của UBTVQH và Quyết định 19/2025/QĐ-TTg).
- Tách hoàn toàn khỏi tập test (loại trùng theo source_url, OSM ID, chuỗi nguyên văn và chuỗi chuẩn hóa).
- Đối chiếu span trong chuỗi dau_vao: Không bao giờ dùng thẻ OSM để ghi đè hoặc điền thông tin không có trong dau_vao.
- Nhập nhằng mốc cũ/mới: loại bỏ khỏi tập nhãn tin cậy, không tự động mặc định cũ trước là đúng.
- Bổ sung trường ngo_ngach_hem phong phú cho cả dữ liệu OSM và dữ liệu tổng hợp.
- Bổ sung các ca trộn mốc hành chính cũ-mới hợp lệ (topologically verified qua bảng đối chiếu).
- Bổ sung các lỗi gõ có chủ đích (telex keystrokes, dính chữ, thiếu dấu thành phần).
- Chia Train/Dev theo nhóm (group-based split) với seed cố định (seed=42):
  * Mọi biến thể của cùng mẫu gốc tổng hợp nằm trong cùng một tập.
  * Mọi bản ghi của cùng đối tượng OSM nằm trong cùng một tập.
- Độc lập với mô hình, tuân thủ đặc tả bai_toan.md, mã số dạng chuỗi zero-padded.
"""

import os
import sys
import json
import csv
import re
import random
import unicodedata
from collections import defaultdict, Counter
from pathlib import Path

# Đảm bảo encoding console
if hasattr(sys.stdout, 'reconfigure'):
    try: sys.stdout.reconfigure(encoding='utf-8')
    except Exception: pass
if hasattr(sys.stderr, 'reconfigure'):
    try: sys.stderr.reconfigure(encoding='utf-8')
    except Exception: pass

BASE_DIR = Path(__file__).resolve().parents[2] # D:\nlp_chuan_hoa_dia_chi\data
PROJECT_DIR = BASE_DIR.parent
CLEAN_DIR = BASE_DIR / "clean"
TEST_DIR = BASE_DIR / "test"
TRAIN_DEV_DIR = BASE_DIR / "train_dev"

# Các trường theo đúng đặc tả bai_toan.md
FIELDS = [
    'id', 'dau_vao', 'nguon', 'so_nha', 'ngo_ngach_hem', 'thon_xom', 'duong',
    'ma_xa_cu', 'ma_huyen_cu', 'ma_tinh_cu', 'ma_xa', 'ma_tinh', 'xa_phuong', 'tinh',
    'dia_chi_chuan', 'canh_bao', 'loai_nhan', 'nguon_du_lieu', 'ghi_chu'
]

def norm(text):
    if not text: return ""
    text = unicodedata.normalize('NFD', str(text).lower().replace('đ', 'd'))
    text = ''.join(c for c in text if not unicodedata.combining(c))
    return re.sub(r'[^a-z0-9]+', ' ', text).strip()

def bare(text):
    text = norm(text)
    text = re.sub(r'^(thanh pho|thi tran|thi xa|dac khu|phuong|huyen|quan|tinh|xa|tp|tt|tx|q|p)\s+', '', text)
    return text

def bare_street(text):
    text = norm(text)
    return re.sub(r'^(duong|pho|dai lo|quoc lo|tinh lo|ql|tl|dt)\s+', '', text)

def strip_diacritics(s):
    if not s: return ""
    s = str(s).replace('đ', 'd').replace('Đ', 'D')
    s = unicodedata.normalize('NFD', s)
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return s

def evidence(value, source):
    """Kiểm tra giá trị có xuất hiện dưới dạng chuỗi/từ ngữ trong nguồn hay không."""
    if not value or not source: return False
    n_val = norm(value)
    n_src = norm(source)
    return (' ' + n_val + ' ') in (' ' + n_src + ' ')

def format_component(value, category):
    if not value: return ""
    value = str(value).strip()
    prefixes = {
        'street': {'duong': 'Đường', 'pho': 'Phố', 'dai lo': 'Đại lộ', 'quoc lo': 'Quốc lộ', 'tinh lo': 'Tỉnh lộ', 'ql': 'Quốc lộ', 'tl': 'Tỉnh lộ', 'dt': 'ĐT'},
        'alley': {'ngo': 'Ngõ', 'ngach': 'Ngách', 'hem': 'Hẻm', 'kiet': 'Kiệt', 'ng': 'Ngõ'},
        'hamlet': {'thon': 'Thôn', 'xom': 'Xóm', 'ap': 'Ấp', 'ban': 'Bản', 'to dan pho': 'Tổ dân phố', 'khu pho': 'Khu phố', 'kp': 'Khu phố'}
    }
    words = value.split()
    if not words: return ""
    acronyms = {'QL','ĐT','DT','TL','HL','KP','KCN','KCX','CC','TT','TP','HCM','VN','II','III','IV','VI','VII','VIII','IX'}
    def case_name(text):
        return re.sub(r'[^\W\d_]+', lambda m: m.group(0).upper() if m.group(0).upper() in acronyms else m.group(0).capitalize(), text)
    
    if category in prefixes:
        for p, exp in sorted(prefixes[category].items(), key=lambda x: -len(x[0])):
            plen = len(p.split())
            if norm(' '.join(words[:plen])) == p:
                return exp + (' ' + case_name(' '.join(words[plen:])) if len(words) > plen else '')
        if category == 'street' and not re.match(r'^(duong|pho|quoc lo|tinh lo|dai lo|dt|ql)\b', norm(value)):
            return 'Đường ' + case_name(value)
        return case_name(value)
    elif category == 'number':
        if not norm(value).startswith('so ') and not value.startswith('Số '):
            return 'Số ' + value
        return value
    return value

class AdminCatalogues:
    def __init__(self):
        self.old_p = list(csv.DictReader(open(CLEAN_DIR / 'cu_tinh.csv', encoding='utf-8-sig')))
        self.new_p = list(csv.DictReader(open(CLEAN_DIR / 'moi_tinh.csv', encoding='utf-8-sig')))
        self.old_d = list(csv.DictReader(open(CLEAN_DIR / 'cu_huyen.csv', encoding='utf-8-sig')))
        self.old_w = list(csv.DictReader(open(CLEAN_DIR / 'cu_tinh_huyen_xa.csv', encoding='utf-8-sig')))
        self.new_w = list(csv.DictReader(open(CLEAN_DIR / 'moi_tinh_xa.csv', encoding='utf-8-sig')))
        self.maps = list(csv.DictReader(open(CLEAN_DIR / 'doi_chieu_xa_cu_moi.csv', encoding='utf-8-sig')))
        
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
        
        # O(1) Lookup tables
        self.old_w_by_bare = defaultdict(list)
        for r in self.old_w:
            self.old_w_by_bare[bare(r['ten_xa'])].append(r)
        self.new_w_by_bare = defaultdict(list)
        for r in self.new_w:
            self.new_w_by_bare[bare(r['ten_xa'])].append(r)
        self.old_d_by_bare = defaultdict(list)
        for r in self.old_d:
            self.old_d_by_bare[bare(r['ten_huyen'])].append(r)
        self.old_p_by_bare = defaultdict(list)
        for r in self.old_p:
            self.old_p_by_bare[bare(r['ten_tinh'])].append(r)
        self.new_p_by_bare = defaultdict(list)
        for r in self.new_p:
            self.new_p_by_bare[bare(r['ten_tinh'])].append(r)
            
        self.p_alias = {
            'hn': '01', 'ha noi': '01', 'hanoi': '01',
            'hcm': '79', 'tp hcm': '79', 'tphcm': '79', 'ho chi minh': '79', 'sai gon': '79',
            'dn': '48', 'da nang': '48',
            'hp': '31', 'hai phong': '31',
            'ct': '92', 'can tho': '92',
            'hue': '46'
        }

    def full_name(self, row, level):
        name, kind = row['ten_' + level], row['loai_' + level]
        if norm(name).startswith(norm(kind) + ' '): return name
        return kind + ' ' + name

def load_test_exclusion():
    test_sources_file = TEST_DIR / 'goc' / 'selected_sources.jsonl'
    test_csv_file = TEST_DIR / 'dia_chi_test.csv'
    
    test_urls = set()
    test_osm_ids = set()
    test_raws = set()
    test_norms = set()
    
    if test_sources_file.exists():
        with open(test_sources_file, 'r', encoding='utf-8') as f:
            for line in f:
                d = json.loads(line)
                if d.get('source_url'): test_urls.add(d['source_url'])
                if 'osm_type' in d and 'osm_id' in d: test_osm_ids.add((d['osm_type'], d['osm_id']))
                if d.get('dau_vao'):
                    test_raws.add(d['dau_vao'])
                    test_norms.add(norm(d['dau_vao']))
                    
    if test_csv_file.exists():
        with open(test_csv_file, 'r', encoding='utf-8') as f:
            for r in csv.DictReader(f):
                if r.get('nguon'): test_urls.add(r['nguon'])
                if r.get('dau_vao'):
                    test_raws.add(r['dau_vao'])
                    test_norms.add(norm(r['dau_vao']))
                    
    return test_urls, test_osm_ids, test_raws, test_norms

def extract_detailed_components(dau_vao, tags):
    """
    Trích xuất so_nha, ngo_ngach_hem, thon_xom, duong dựa trên span trong dau_vao.
    Tuyệt đối không dùng thẻ ghi đè hoặc phát sinh thành phần không có trong chuỗi đầu vào.
    """
    raw = dau_vao.strip()
    norm_in = ' ' + norm(raw) + ' '
    so_nha = ''
    ngo_ngach_hem = ''
    thon_xom = ''
    duong = ''
    
    # 1. Tìm ngõ / ngách / hẻm / kiệt trong dau_vao
    m_alley = re.search(r'\b((?:ngõ|ngách|hẻm|kiệt|ngo|ngach|hem|kiet)\s+\d+[a-zA-Z]?(?:[/-]\d+[a-zA-Z]?)*)\b', raw, re.IGNORECASE)
    if m_alley:
        ngo_ngach_hem = format_component(m_alley.group(1), 'alley')
        
    # 2. Tìm thôn / xóm / ấp / bản / tổ dân phố / khu phố trong dau_vao
    m_hamlet = re.search(r'\b((?:thôn|xóm|ấp|bản|tổ dân phố|khu phố|kp|thon|xom|ap|ban)\s+[A-Za-zÀ-ỹĐđ0-9\s]+?)(?=,|\bphường|\bxã|\bquận|\bhuyện|\btp|\bthị trấn|$)', raw, re.IGNORECASE)
    if m_hamlet:
        thon_xom = format_component(m_hamlet.group(1).strip(), 'hamlet')
        
    # 3. Tìm số nhà dựa trên dau_vao
    m_so = re.search(r'\b(?:số|so|nhà số|nha so)\s*([0-9]+[A-Za-z]?(?:[/-][0-9]+[A-Za-z]?)*)\b', raw, re.IGNORECASE)
    if m_so:
        so_nha = 'Số ' + m_so.group(1).upper()
    else:
        # Nếu thẻ addr:housenumber có mặt, kiểm tra xem nó xuất hiện trong dau_vao như thế nào
        tag_num = tags.get('addr:housenumber', '').strip()
        if tag_num:
            # Tìm xem có kèm hậu tố chữ cái trong dau_vao không (vd tag=18 nhưng dau_vao là 18B)
            m_tag = re.search(rf'\b({re.escape(tag_num)}[A-Za-z]?)\b', raw, re.IGNORECASE)
            if m_tag:
                so_nha = 'Số ' + m_tag.group(1).upper()
            elif (' ' + norm(tag_num) + ' ') in norm_in:
                so_nha = format_component(tag_num, 'number')
        if not so_nha:
            # Tìm số ở đầu chuỗi (vd '34, Hàng Giấy' hoặc '18B Nguyễn Biểu')
            m_start = re.match(r'^\s*([0-9]+[A-Za-z]?(?:[/-][0-9]+[A-Za-z]?)*)\b', raw)
            if m_start:
                cand_num = m_start.group(1).upper()
                # Tránh nhầm với quốc lộ, ví dụ '91B' trong 'QL 91B'
                if not re.search(rf'\b(?:ql|quoc lo|tl|dt)\s+{re.escape(cand_num)}\b', raw, re.IGNORECASE):
                    so_nha = 'Số ' + cand_num
                    
    # 4. Tìm đường dựa trên dau_vao
    tag_street = tags.get('addr:street', '').strip()
    if tag_street:
        bs = bare_street(tag_street)
        # Bắt buộc tag_street hoặc phần cốt lõi của tên đường phải xuất hiện trong dau_vao
        if bs and (' ' + bs + ' ') in norm_in:
            duong = format_component(tag_street, 'street')
            
    if not duong:
        # Nếu không có thẻ hoặc thẻ không khớp span trong dau_vao, trích xuất từ khóa đường/phố trong dau_vao
        m_str = re.search(r'\b((?:đường|phố|đại lộ|quốc lộ|tỉnh lộ|ql|tl|đt)\s+[A-Za-zÀ-ỹĐđ0-9\s]+?)(?=,|\bphường|\bxã|\bquận|\bhuyện|\btp|\bthị trấn|$)', raw, re.IGNORECASE)
        if m_str:
            duong = format_component(m_str.group(1).strip(), 'street')
            
    return so_nha, ngo_ngach_hem, thon_xom, duong

def process_osm_candidate(d, cat):
    """
    Gán nhãn máy sơ bộ cho một ứng viên OSM dựa trên đối chiếu span dau_vao.
    - Loại bỏ nếu nhập nhằng mốc cũ/mới (mo_ho_moc_cu_moi).
    - Giữ cảnh báo và danh sách ứng viên cho xã bị chia, không chọn bừa.
    - Đảm bảo mọi thành phần nhãn đều có căn cứ trong chuỗi đầu vào.
    """
    tags = d.get('tags', {})
    raw_input = d['dau_vao']
    source_url = d['source_url']
    osm_id = d.get('osm_id', '')
    osm_type = d.get('osm_type', 'node')
    input_mode = d.get('input_mode', 'unknown')
    norm_input = ' ' + norm(raw_input) + ' '
    
    # Trích xuất số nhà, ngõ/hẻm, thôn/xóm, đường trực tiếp từ chuỗi đầu vào
    so_nha, ngo_ngach_hem, thon_xom, duong = extract_detailed_components(raw_input, tags)
    
    warnings = ['nhan_may']
    notes = [f"osm_id={osm_id}", f"osm_type={osm_type}", f"input_mode={input_mode}", "nguon_goc=osm_candidates"]
    
    if '/' in so_nha:
        warnings.append('so_nha_can_duyet')
    if duong and re.search(r'[A-Za-z]', duong) and not re.search(r'[à-ỹÀ-ỸđĐ]', duong):
        warnings.append('phan_du_khong_dau_can_duyet')
        
    # 1. Nhận diện tỉnh
    p_tag = tags.get('addr:province') or tags.get('addr:city') or ''
    p_bare = bare(p_tag)
    matched_p_code = None
    
    if p_bare in cat.p_alias and (' ' + p_bare + ' ') in norm_input:
        matched_p_code = cat.p_alias[p_bare]
    elif p_bare in cat.old_p_by_bare and (' ' + p_bare + ' ') in norm_input:
        matched_p_code = cat.old_p_by_bare[p_bare][0]['ma_tinh']
    elif p_bare in cat.new_p_by_bare and (' ' + p_bare + ' ') in norm_input:
        matched_p_code = cat.new_p_by_bare[p_bare][0]['ma_tinh']
    else:
        # Tìm kiếm trực tiếp tên tỉnh/thành phố trong chuỗi dau_vao
        for alias, code in cat.p_alias.items():
            if (' ' + alias + ' ') in norm_input:
                matched_p_code = code
                break
        if not matched_p_code:
            for b_name, rows in cat.new_p_by_bare.items():
                if (' ' + b_name + ' ') in norm_input:
                    matched_p_code = rows[0]['ma_tinh']
                    break
        if not matched_p_code:
            for b_name, rows in cat.old_p_by_bare.items():
                if (' ' + b_name + ' ') in norm_input:
                    matched_p_code = rows[0]['ma_tinh']
                    break
                    
    if not matched_p_code:
        return None, "thieu_tinh_hoac_khong_xac_dinh_duoc_tinh"
        
    # 2. Nhận diện huyện (mốc cũ)
    d_tag = tags.get('addr:district') or ''
    d_bare = bare(d_tag)
    matched_d = None
    if d_bare and (' ' + d_bare + ' ') in norm_input and d_bare in cat.old_d_by_bare:
        candidates = cat.old_d_by_bare[d_bare]
        filtered = [c for c in candidates if c['ma_tinh'] == matched_p_code or matched_p_code in cat.province_map.get(c['ma_tinh'], set())]
        if len(filtered) == 1:
            matched_d = filtered[0]
    if not matched_d:
        # Tìm huyện từ dau_vao
        for b_name, d_rows in cat.old_d_by_bare.items():
            if (' ' + b_name + ' ') in norm_input:
                filtered = [c for c in d_rows if c['ma_tinh'] == matched_p_code or matched_p_code in cat.province_map.get(c['ma_tinh'], set())]
                if len(filtered) == 1:
                    matched_d = filtered[0]
                    break
                    
    # 3. Nhận diện xã (đối chiếu cả mốc cũ và mốc mới)
    w_tag = tags.get('addr:ward') or tags.get('addr:subdistrict') or ''
    w_bare = bare(w_tag)
    
    # Nếu w_tag không xuất hiện trong dau_vao thì không dùng w_tag
    if w_bare and (' ' + w_bare + ' ') not in norm_input:
        w_bare = ""
        
    if not w_bare:
        # Thử trích xuất tên xã từ dau_vao
        m_w = re.search(r'\b(?:phường|xã|thị trấn|p\.|x\.|tt\.)\s+([A-Za-zÀ-ỹĐđ0-9\s]+?)(?=,|\bquận|\bhuyện|\btp|\bthị trấn|$)', raw_input, re.IGNORECASE)
        if m_w:
            w_bare = bare(m_w.group(1).strip())
            
    old_w_cands = []
    new_w_cands = []
    
    if w_bare:
        if w_bare in cat.old_w_by_bare:
            cands = cat.old_w_by_bare[w_bare]
            if matched_d:
                old_w_cands = [c for c in cands if c['ma_huyen'] == matched_d['ma_huyen']]
            else:
                old_w_cands = [c for c in cands if c['ma_tinh'] == matched_p_code or matched_p_code in cat.province_map.get(c['ma_tinh'], set())]
                
        if w_bare in cat.new_w_by_bare:
            cands = cat.new_w_by_bare[w_bare]
            new_w_cands = [c for c in cands if c['ma_tinh'] == matched_p_code or c['ma_tinh'] in cat.province_map.get(matched_p_code, set())]
            
    matched_w = None
    era = 'unknown'
    
    if len(old_w_cands) == 1 and len(new_w_cands) == 1:
        targets = {r['ma_xa_moi'] for r in cat.to_new[old_w_cands[0]['ma_xa']]}
        if targets == {new_w_cands[0]['ma_xa']}:
            # Cả hai mốc đều dẫn đến cùng một xã đích 2025 -> Bất biến
            matched_w = old_w_cands[0]
            era = 'cu_moi_cung_ket_qua'
        elif matched_d:
            # Có huyện cũ chứng thực -> Xác định mốc cũ
            matched_w = old_w_cands[0]
            era = 'cu'
        else:
            # Nhập nhằng mốc cũ/mới nhưng không có huyện chứng thực:
            # "Nhập nhằng mốc phải giữ ứng viên/cảnh báo hoặc loại khỏi tập nhãn đáng tin, không mặc định cũ trước là đúng."
            # Loại khỏi tập nhãn đáng tin cậy huấn luyện để đảm bảo chất lượng!
            return None, "loai_khoi_tap_tin_cay_do_nhap_nhang_moc"
    elif len(old_w_cands) == 1:
        matched_w = old_w_cands[0]
        era = 'cu'
    elif len(new_w_cands) == 1:
        matched_w = new_w_cands[0]
        era = 'moi'
    elif w_bare:
        # Có tên xã nhưng không khớp duy nhất hoặc trùng tên nhiều nơi
        return None, "xa_trung_hoac_khong_xac_dinh_duoc"
        
    # Điền kết quả
    ma_xa_cu = ""
    ma_huyen_cu = ""
    ma_tinh_cu = ""
    ma_xa = ""
    ma_tinh = ""
    xa_phuong = ""
    tinh = ""
    
    if era in ('cu', 'cu_moi_cung_ket_qua') and matched_w:
        ma_xa_cu = matched_w['ma_xa']
        ma_huyen_cu = matched_w['ma_huyen']
        ma_tinh_cu = matched_w['ma_tinh']
        
        targets = sorted({r['ma_xa_moi'] for r in cat.to_new[ma_xa_cu]})
        if len(targets) == 1:
            ma_xa = targets[0]
            target_obj = cat.new_wi[ma_xa]
            ma_tinh = target_obj['ma_tinh']
            xa_phuong = cat.full_name(target_obj, 'xa')
            tinh = cat.full_name(cat.new_pi[ma_tinh], 'tinh')
        elif len(targets) > 1:
            # Xã bị chia (fan-out > 1): Bắt buộc để trống xã đích, gắn cờ xa_bi_chia và lưu ứng viên
            warnings.append('xa_bi_chia')
            target_provs = cat.province_map.get(ma_tinh_cu, set())
            if len(target_provs) == 1:
                ma_tinh = next(iter(target_provs))
                tinh = cat.full_name(cat.new_pi[ma_tinh], 'tinh')
            candidates_info = [{'ma_xa': k, 'ten': cat.full_name(cat.new_wi[k], 'xa')} for k in targets]
            notes.append(f"xa_moi_ung_vien={json.dumps(candidates_info, ensure_ascii=False)}")
    elif era == 'moi' and matched_w:
        ma_xa = matched_w['ma_xa']
        ma_tinh = matched_w['ma_tinh']
        xa_phuong = cat.full_name(matched_w, 'xa')
        tinh = cat.full_name(cat.new_pi[ma_tinh], 'tinh')
    elif matched_d:
        ma_huyen_cu = matched_d['ma_huyen']
        ma_tinh_cu = matched_d['ma_tinh']
        target_provs = cat.province_map.get(ma_tinh_cu, set())
        if len(target_provs) == 1:
            ma_tinh = next(iter(target_provs))
            tinh = cat.full_name(cat.new_pi[ma_tinh], 'tinh')
        warnings.append('thieu_xa')
    else:
        # Không có xã và không có huyện -> Chỉ có tỉnh
        if matched_p_code in cat.new_pi:
            ma_tinh = matched_p_code
            tinh = cat.full_name(cat.new_pi[ma_tinh], 'tinh')
        elif matched_p_code in cat.old_pi:
            ma_tinh_cu = matched_p_code
            target_provs = cat.province_map.get(ma_tinh_cu, set())
            if len(target_provs) == 1:
                ma_tinh = next(iter(target_provs))
                tinh = cat.full_name(cat.new_pi[ma_tinh], 'tinh')
        warnings.append('thieu_xa')
        
    if not tinh:
        warnings.append('thieu_tinh')
        
    dia_chi_chuan = ', '.join(x for x in (so_nha, ngo_ngach_hem, thon_xom, duong, xa_phuong, tinh) if x)
    
    record = {
        'dau_vao': raw_input,
        'nguon': source_url,
        'so_nha': so_nha,
        'ngo_ngach_hem': ngo_ngach_hem,
        'thon_xom': thon_xom,
        'duong': duong,
        'ma_xa_cu': ma_xa_cu,
        'ma_huyen_cu': ma_huyen_cu,
        'ma_tinh_cu': ma_tinh_cu,
        'ma_xa': ma_xa,
        'ma_tinh': ma_tinh,
        'xa_phuong': xa_phuong,
        'tinh': tinh,
        'dia_chi_chuan': dia_chi_chuan,
        'canh_bao': json.dumps(sorted(set(warnings)), ensure_ascii=False),
        'loai_nhan': 'nhan_may',
        'nguon_du_lieu': 'osm_public',
        'ghi_chu': '; '.join(notes),
        'group_key': f"OSM_{osm_type}_{osm_id}"
    }
    return record, "thanh_cong"

def generate_synthetic_samples(cat, seed=42):
    """
    Sinh các mẫu tổng hợp từ danh mục hành chính:
    - ~500 ĐVHC cơ sở (xã cũ sáp nhập 1-1, xã cũ bị chia, xã mới 2025).
    - Biến thể:
      1. Chuẩn đầy đủ (canonical)
      2. Có Ngõ/Ngách/Hẻm/Kiệt (ngo_ngach_hem)
      3. Trộn mốc cũ-mới hợp lệ (tron_moc_cu_moi: Xã mới + Huyện cũ tương thích theo bảng đối chiếu)
      4. Lỗi gõ có chủ đích (loi_chinh_ta: telex keystrokes, dính chữ P.DịchVọng, thiếu dấu 1 từ)
      5. Không dấu (khong_dau)
      6. Viết tắt (viet_tat)
      7. Thiếu thành phần (thieu_thanh_phan)
      8. Đổi thứ tự (doi_thu_tu)
    - Xã bị chia: Luôn để trống ma_xa, xa_phuong, giữ cờ xa_bi_chia và danh sách ứng viên.
    """
    rng = random.Random(seed)
    
    # 1. Chọn danh mục cơ sở
    split_wards = [w for w in cat.old_w if w['ma_xa'] in cat.split_codes]
    normal_old_wards = [w for w in cat.old_w if w['ma_xa'] not in cat.split_codes]
    new_wards = list(cat.new_w)
    
    rng.shuffle(split_wards)
    rng.shuffle(normal_old_wards)
    rng.shuffle(new_wards)
    
    selected_normal_old = normal_old_wards[:380]
    selected_split = split_wards[:60]
    selected_new = new_wards[:60]
    
    SAMPLE_STREETS = [
        "Lê Lợi", "Trần Hưng Đạo", "Nguyễn Huệ", "Quang Trung", "Hai Bà Trưng",
        "Phan Bội Châu", "Nguyễn Trãi", "Lý Thường Kiệt", "Hoàng Hoa Thám", "Trần Phú",
        "Bà Triệu", "Điện Biên Phủ", "Cách Mạng Tháng Tám", "Võ Văn Kiệt", "Hùng Vương",
        "Nguyễn Thị Minh Khai", "Ngô Quyền", "Lê Duẩn", "Phạm Văn Đồng", "Nguyễn Văn Cừ",
        "Hoàng Văn Thụ", "Đinh Tiên Hoàng", "Trường Chinh", "Giải Phóng", "Cầu Giấy",
        "Kim Mã", "Đội Cấn", "Tây Sơn", "Xã Đàn", "Hoàng Cầu", "Nguyễn Chí Thanh"
    ]
    SAMPLE_NUMBERS = ["12", "45", "108", "25B", "15", "88", "120", "5", "68", "72", "99", "10", "204", "168", "35", "4A", "18B", "402"]
    SAMPLE_ALLEYS = ["Ngõ 12", "Ngõ 45", "Ngách 8/2", "Hẻm 108", "Hẻm 25", "Kiệt 35", "Ngõ 168", "Hẻm 68", "Kiệt 12", "Ngách 15/4"]
    SAMPLE_HAMLETS = ["Thôn 1", "Thôn 2", "Thôn Đông", "Xóm Chùa", "Ấp 3", "Bản Mới", "Khu phố 4", "Tổ dân phố 6", "Ấp Bắc"]

    def abbreviate_kind(kind):
        mapping = {
            'Thành phố': 'TP.', 'Tỉnh': 'T.', 'Quận': 'Q.', 'Huyện': 'H.',
            'Thị xã': 'TX.', 'Thị trấn': 'TT.', 'Phường': 'P.', 'Xã': 'X.',
            'Đường': 'Đ.', 'Khu phố': 'KP.'
        }
        return mapping.get(kind, kind)

    synthetic_records = []
    base_counter = 0

    # ========================================================
    # A) Xã cũ bình thường (380 cơ sở * 8 biến thể = 3.040 mẫu)
    # ========================================================
    for w in selected_normal_old:
        base_counter += 1
        base_id = f"SYN_BASE_{base_counter:04d}"
        d = cat.old_di[w['ma_huyen']]
        p = cat.old_pi[w['ma_tinh']]
        targets = cat.to_new[w['ma_xa']]
        new_w = cat.new_wi[targets[0]['ma_xa_moi']]
        new_p = cat.new_pi[new_w['ma_tinh']]
        
        street_raw = rng.choice(SAMPLE_STREETS)
        num_raw = rng.choice(SAMPLE_NUMBERS)
        alley_raw = rng.choice(SAMPLE_ALLEYS)
        
        full_street = f"Đường {street_raw}"
        full_num = f"Số {num_raw}"
        full_ward = cat.full_name(w, 'xa')
        full_dist = cat.full_name(d, 'huyen')
        full_prov = cat.full_name(p, 'tinh')
        
        target_ward_full = cat.full_name(new_w, 'xa')
        target_prov_full = cat.full_name(new_p, 'tinh')
        
        v1_std = f"{full_num}, {full_street}, {target_ward_full}, {target_prov_full}"
        v_alley_std = f"{full_num}, {alley_raw}, {full_street}, {target_ward_full}, {target_prov_full}"
        
        # 1. Biến thể chuẩn đầy đủ (Canonical)
        v1_in = f"{full_num}, {full_street}, {full_ward}, {full_dist}, {full_prov}"
        synthetic_records.append({
            'mau_goc_id': base_id, 'dau_vao': v1_in, 'nguon': f"danh_muc:{base_id}_v1",
            'so_nha': full_num, 'ngo_ngach_hem': '', 'thon_xom': '', 'duong': full_street,
            'ma_xa_cu': w['ma_xa'], 'ma_huyen_cu': d['ma_huyen'], 'ma_tinh_cu': p['ma_tinh'],
            'ma_xa': new_w['ma_xa'], 'ma_tinh': new_p['ma_tinh'],
            'xa_phuong': target_ward_full, 'tinh': target_prov_full, 'dia_chi_chuan': v1_std,
            'canh_bao': json.dumps(['nhan_tong_hop'], ensure_ascii=False),
            'loai_nhan': 'tong_hop', 'nguon_du_lieu': 'danh_muc_hanh_chinh',
            'ghi_chu': f"mau_goc_id={base_id}; bien_the=chuan_day_du; so_nha va duong la gia dinh khong phai dia chi that xac minh"
        })
        
        # 2. Biến thể có ngõ/ngách/hẻm (ngo_ngach_hem khác rỗng)
        v2_in = f"{full_num}, {alley_raw}, {full_street}, {full_ward}, {full_dist}, {full_prov}"
        synthetic_records.append({
            'mau_goc_id': base_id, 'dau_vao': v2_in, 'nguon': f"danh_muc:{base_id}_v2",
            'so_nha': full_num, 'ngo_ngach_hem': alley_raw, 'thon_xom': '', 'duong': full_street,
            'ma_xa_cu': w['ma_xa'], 'ma_huyen_cu': d['ma_huyen'], 'ma_tinh_cu': p['ma_tinh'],
            'ma_xa': new_w['ma_xa'], 'ma_tinh': new_p['ma_tinh'],
            'xa_phuong': target_ward_full, 'tinh': target_prov_full, 'dia_chi_chuan': v_alley_std,
            'canh_bao': json.dumps(['nhan_tong_hop', 'co_ngo_ngach_hem'], ensure_ascii=False),
            'loai_nhan': 'tong_hop', 'nguon_du_lieu': 'danh_muc_hanh_chinh',
            'ghi_chu': f"mau_goc_id={base_id}; bien_the=ngo_ngach_hem; mau tong hop co ngo ngach hem"
        })
        
        # 3. Biến thể trộn mốc cũ-mới hợp lệ (tron_moc_cu_moi: Xã mới + Huyện cũ tương thích + Tỉnh)
        v3_in = f"{full_num}, {full_street}, {target_ward_full}, {full_dist}, {target_prov_full}"
        synthetic_records.append({
            'mau_goc_id': base_id, 'dau_vao': v3_in, 'nguon': f"danh_muc:{base_id}_v3",
            'so_nha': full_num, 'ngo_ngach_hem': '', 'thon_xom': '', 'duong': full_street,
            'ma_xa_cu': '', 'ma_huyen_cu': d['ma_huyen'], 'ma_tinh_cu': p['ma_tinh'],
            'ma_xa': new_w['ma_xa'], 'ma_tinh': new_p['ma_tinh'],
            'xa_phuong': target_ward_full, 'tinh': target_prov_full, 'dia_chi_chuan': v1_std,
            'canh_bao': json.dumps(['nhan_tong_hop', 'tron_moc_cu_moi'], ensure_ascii=False),
            'loai_nhan': 'tong_hop', 'nguon_du_lieu': 'danh_muc_hanh_chinh',
            'ghi_chu': f"mau_goc_id={base_id}; bien_the=tron_moc_cu_moi; xa moi ket hop huyen cu tuong thich theo ban do sap nhap"
        })
        
        # 4. Biến thể lỗi gõ có chủ đích (loi_chinh_ta: telex double keystrokes hoặc dính chữ)
        typo_type = rng.choice(['telex', 'glued', 'partial_unaccented'])
        if typo_type == 'telex':
            # Gõ lỗi telex: dduong, phuowng, thoon
            v4_in = f"{num_raw} dduowng {street_raw}, {w['loai_xa']} {w['ten_xa']}, {full_dist}, {full_prov}"
        elif typo_type == 'glued':
            # Dính chữ không cách: P.DịchVọng, Q.CầuGiấy
            v4_in = f"{num_raw} Đ.{street_raw.replace(' ', '')}, {abbreviate_kind(w['loai_xa'])}{w['ten_xa']}, {abbreviate_kind(d['loai_huyen'])}{d['ten_huyen']}, {full_prov}"
        else:
            # Rớt dấu 1 từ đơn lẻ: Đuong hoặc Phuong
            v4_in = f"{full_num}, Đuong {street_raw}, {w['loai_xa']} {w['ten_xa']}, {full_dist}, {full_prov}"
            
        synthetic_records.append({
            'mau_goc_id': base_id, 'dau_vao': v4_in, 'nguon': f"danh_muc:{base_id}_v4",
            'so_nha': full_num, 'ngo_ngach_hem': '', 'thon_xom': '', 'duong': full_street,
            'ma_xa_cu': w['ma_xa'], 'ma_huyen_cu': d['ma_huyen'], 'ma_tinh_cu': p['ma_tinh'],
            'ma_xa': new_w['ma_xa'], 'ma_tinh': new_p['ma_tinh'],
            'xa_phuong': target_ward_full, 'tinh': target_prov_full, 'dia_chi_chuan': v1_std,
            'canh_bao': json.dumps(['nhan_tong_hop', 'loi_chinh_ta'], ensure_ascii=False),
            'loai_nhan': 'tong_hop', 'nguon_du_lieu': 'danh_muc_hanh_chinh',
            'ghi_chu': f"mau_goc_id={base_id}; bien_the=loi_chinh_ta; kieu_loi={typo_type}"
        })
        
        # 5. Biến thể không dấu (Unaccented)
        v5_in = strip_diacritics(f"{num_raw} duong {street_raw}, {w['loai_xa']} {w['ten_xa']}, {d['loai_huyen']} {d['ten_huyen']}, {p['ten_tinh']}")
        synthetic_records.append({
            'mau_goc_id': base_id, 'dau_vao': v5_in, 'nguon': f"danh_muc:{base_id}_v5",
            'so_nha': full_num, 'ngo_ngach_hem': '', 'thon_xom': '', 'duong': full_street,
            'ma_xa_cu': w['ma_xa'], 'ma_huyen_cu': d['ma_huyen'], 'ma_tinh_cu': p['ma_tinh'],
            'ma_xa': new_w['ma_xa'], 'ma_tinh': new_p['ma_tinh'],
            'xa_phuong': target_ward_full, 'tinh': target_prov_full, 'dia_chi_chuan': v1_std,
            'canh_bao': json.dumps(['nhan_tong_hop', 'dau_vao_khong_dau'], ensure_ascii=False),
            'loai_nhan': 'tong_hop', 'nguon_du_lieu': 'danh_muc_hanh_chinh',
            'ghi_chu': f"mau_goc_id={base_id}; bien_the=khong_dau; so_nha va duong la gia dinh khong phai dia chi that xac minh"
        })
        
        # 6. Biến thể viết tắt (Abbreviated)
        p_abbr = 'HN' if p['ma_tinh'] == '01' else ('TP.HCM' if p['ma_tinh'] == '79' else f"{abbreviate_kind(p['loai_tinh'])} {p['ten_tinh']}")
        v6_in = f"{num_raw} Đ. {street_raw}, {abbreviate_kind(w['loai_xa'])} {w['ten_xa']}, {abbreviate_kind(d['loai_huyen'])} {d['ten_huyen']}, {p_abbr}"
        synthetic_records.append({
            'mau_goc_id': base_id, 'dau_vao': v6_in, 'nguon': f"danh_muc:{base_id}_v6",
            'so_nha': full_num, 'ngo_ngach_hem': '', 'thon_xom': '', 'duong': full_street,
            'ma_xa_cu': w['ma_xa'], 'ma_huyen_cu': d['ma_huyen'], 'ma_tinh_cu': p['ma_tinh'],
            'ma_xa': new_w['ma_xa'], 'ma_tinh': new_p['ma_tinh'],
            'xa_phuong': target_ward_full, 'tinh': target_prov_full, 'dia_chi_chuan': v1_std,
            'canh_bao': json.dumps(['nhan_tong_hop', 'dau_vao_viet_tat'], ensure_ascii=False),
            'loai_nhan': 'tong_hop', 'nguon_du_lieu': 'danh_muc_hanh_chinh',
            'ghi_chu': f"mau_goc_id={base_id}; bien_the=viet_tat; so_nha va duong la gia dinh khong phai dia chi that xac minh"
        })
        
        # 7. Biến thể thiếu thành phần (chỉ có xã, huyện, tỉnh)
        v7_in = f"{full_ward}, {full_dist}, {full_prov}"
        v7_std = f"{target_ward_full}, {target_prov_full}"
        synthetic_records.append({
            'mau_goc_id': base_id, 'dau_vao': v7_in, 'nguon': f"danh_muc:{base_id}_v7",
            'so_nha': '', 'ngo_ngach_hem': '', 'thon_xom': '', 'duong': '',
            'ma_xa_cu': w['ma_xa'], 'ma_huyen_cu': d['ma_huyen'], 'ma_tinh_cu': p['ma_tinh'],
            'ma_xa': new_w['ma_xa'], 'ma_tinh': new_p['ma_tinh'],
            'xa_phuong': target_ward_full, 'tinh': target_prov_full, 'dia_chi_chuan': v7_std,
            'canh_bao': json.dumps(['nhan_tong_hop', 'thieu_so_nha_duong'], ensure_ascii=False),
            'loai_nhan': 'tong_hop', 'nguon_du_lieu': 'danh_muc_hanh_chinh',
            'ghi_chu': f"mau_goc_id={base_id}; bien_the=thieu_thanh_phan; chi co cap hanh chinh"
        })
        
        # 8. Biến thể đổi thứ tự (Tỉnh -> Huyện -> Xã -> Số nhà Đường)
        v8_in = f"{full_prov}, {full_dist}, {full_ward}, {full_num} {full_street}"
        synthetic_records.append({
            'mau_goc_id': base_id, 'dau_vao': v8_in, 'nguon': f"danh_muc:{base_id}_v8",
            'so_nha': full_num, 'ngo_ngach_hem': '', 'thon_xom': '', 'duong': full_street,
            'ma_xa_cu': w['ma_xa'], 'ma_huyen_cu': d['ma_huyen'], 'ma_tinh_cu': p['ma_tinh'],
            'ma_xa': new_w['ma_xa'], 'ma_tinh': new_p['ma_tinh'],
            'xa_phuong': target_ward_full, 'tinh': target_prov_full, 'dia_chi_chuan': v1_std,
            'canh_bao': json.dumps(['nhan_tong_hop', 'doi_thu_tu'], ensure_ascii=False),
            'loai_nhan': 'tong_hop', 'nguon_du_lieu': 'danh_muc_hanh_chinh',
            'ghi_chu': f"mau_goc_id={base_id}; bien_the=doi_thu_tu; tinh truoc xa sau"
        })

    # ========================================================
    # B) Xã cũ bị chia (60 cơ sở * 5 biến thể = 300 mẫu)
    # ========================================================
    for w in selected_split:
        base_counter += 1
        base_id = f"SYN_BASE_{base_counter:04d}"
        d = cat.old_di[w['ma_huyen']]
        p = cat.old_pi[w['ma_tinh']]
        targets = cat.to_new[w['ma_xa']]
        target_p_codes = cat.province_map.get(p['ma_tinh'], set())
        new_p_code = next(iter(target_p_codes)) if len(target_p_codes) == 1 else ""
        new_p_name = cat.full_name(cat.new_pi[new_p_code], 'tinh') if new_p_code else ""
        
        candidates_info = [{'ma_xa': r['ma_xa_moi'], 'ten': cat.full_name(cat.new_wi[r['ma_xa_moi']], 'xa')} for r in targets]
        
        full_ward = cat.full_name(w, 'xa')
        full_dist = cat.full_name(d, 'huyen')
        full_prov = cat.full_name(p, 'tinh')
        
        hamlet_raw = rng.choice(SAMPLE_HAMLETS)
        street_raw = rng.choice(SAMPLE_STREETS)
        num_raw = rng.choice(SAMPLE_NUMBERS)
        alley_raw = rng.choice(SAMPLE_ALLEYS)
        
        # 1. Thôn/Xóm + Xã bị chia
        v1_in = f"{hamlet_raw}, {full_ward}, {full_dist}, {full_prov}"
        v1_std = f"{hamlet_raw}, {new_p_name}" if new_p_name else hamlet_raw
        synthetic_records.append({
            'mau_goc_id': base_id, 'dau_vao': v1_in, 'nguon': f"danh_muc:{base_id}_v1",
            'so_nha': '', 'ngo_ngach_hem': '', 'thon_xom': hamlet_raw, 'duong': '',
            'ma_xa_cu': w['ma_xa'], 'ma_huyen_cu': d['ma_huyen'], 'ma_tinh_cu': p['ma_tinh'],
            'ma_xa': '', 'ma_tinh': new_p_code, 'xa_phuong': '', 'tinh': new_p_name,
            'dia_chi_chuan': v1_std,
            'canh_bao': json.dumps(['nhan_tong_hop', 'xa_bi_chia'], ensure_ascii=False),
            'loai_nhan': 'tong_hop', 'nguon_du_lieu': 'danh_muc_hanh_chinh',
            'ghi_chu': f"mau_goc_id={base_id}; bien_the=xa_bi_chia_thon_xom; xa_moi_ung_vien={json.dumps(candidates_info, ensure_ascii=False)}"
        })
        
        # 2. Ngõ/Ngách + Số nhà + Đường + Xã bị chia
        full_num = f"Số {num_raw}"
        full_street = f"Đường {street_raw}"
        v2_in = f"{full_num}, {alley_raw}, {full_street}, {full_ward}, {full_dist}, {full_prov}"
        v2_std = f"{full_num}, {alley_raw}, {full_street}, {new_p_name}" if new_p_name else f"{full_num}, {alley_raw}, {full_street}"
        synthetic_records.append({
            'mau_goc_id': base_id, 'dau_vao': v2_in, 'nguon': f"danh_muc:{base_id}_v2",
            'so_nha': full_num, 'ngo_ngach_hem': alley_raw, 'thon_xom': '', 'duong': full_street,
            'ma_xa_cu': w['ma_xa'], 'ma_huyen_cu': d['ma_huyen'], 'ma_tinh_cu': p['ma_tinh'],
            'ma_xa': '', 'ma_tinh': new_p_code, 'xa_phuong': '', 'tinh': new_p_name,
            'dia_chi_chuan': v2_std,
            'canh_bao': json.dumps(['nhan_tong_hop', 'co_ngo_ngach_hem', 'xa_bi_chia'], ensure_ascii=False),
            'loai_nhan': 'tong_hop', 'nguon_du_lieu': 'danh_muc_hanh_chinh',
            'ghi_chu': f"mau_goc_id={base_id}; bien_the=xa_bi_chia_ngo_ngach; xa_moi_ung_vien={json.dumps(candidates_info, ensure_ascii=False)}"
        })
        
        # 3. Lỗi gõ / Viết tắt + Xã bị chia
        v3_in = f"{num_raw} Đ.{street_raw.replace(' ', '')}, {abbreviate_kind(w['loai_xa'])}{w['ten_xa']}, {abbreviate_kind(d['loai_huyen'])}{d['ten_huyen']}, {full_prov}"
        v3_std = f"{full_num}, {full_street}, {new_p_name}" if new_p_name else f"{full_num}, {full_street}"
        synthetic_records.append({
            'mau_goc_id': base_id, 'dau_vao': v3_in, 'nguon': f"danh_muc:{base_id}_v3",
            'so_nha': full_num, 'ngo_ngach_hem': '', 'thon_xom': '', 'duong': full_street,
            'ma_xa_cu': w['ma_xa'], 'ma_huyen_cu': d['ma_huyen'], 'ma_tinh_cu': p['ma_tinh'],
            'ma_xa': '', 'ma_tinh': new_p_code, 'xa_phuong': '', 'tinh': new_p_name,
            'dia_chi_chuan': v3_std,
            'canh_bao': json.dumps(['nhan_tong_hop', 'loi_chinh_ta', 'xa_bi_chia'], ensure_ascii=False),
            'loai_nhan': 'tong_hop', 'nguon_du_lieu': 'danh_muc_hanh_chinh',
            'ghi_chu': f"mau_goc_id={base_id}; bien_the=xa_bi_chia_loi_chinh_ta; xa_moi_ung_vien={json.dumps(candidates_info, ensure_ascii=False)}"
        })
        
        # 4. Không dấu + Xã bị chia
        v4_in = strip_diacritics(f"{num_raw} duong {street_raw}, {w['loai_xa']} {w['ten_xa']}, {d['loai_huyen']} {d['ten_huyen']}, {p['ten_tinh']}")
        synthetic_records.append({
            'mau_goc_id': base_id, 'dau_vao': v4_in, 'nguon': f"danh_muc:{base_id}_v4",
            'so_nha': full_num, 'ngo_ngach_hem': '', 'thon_xom': '', 'duong': full_street,
            'ma_xa_cu': w['ma_xa'], 'ma_huyen_cu': d['ma_huyen'], 'ma_tinh_cu': p['ma_tinh'],
            'ma_xa': '', 'ma_tinh': new_p_code, 'xa_phuong': '', 'tinh': new_p_name,
            'dia_chi_chuan': v3_std,
            'canh_bao': json.dumps(['nhan_tong_hop', 'dau_vao_khong_dau', 'xa_bi_chia'], ensure_ascii=False),
            'loai_nhan': 'tong_hop', 'nguon_du_lieu': 'danh_muc_hanh_chinh',
            'ghi_chu': f"mau_goc_id={base_id}; bien_the=xa_bi_chia_khong_dau; xa_moi_ung_vien={json.dumps(candidates_info, ensure_ascii=False)}"
        })
        
        # 5. Đổi thứ tự + Xã bị chia
        v5_in = f"{full_prov}, {full_dist}, {full_ward}, {full_num} {full_street}"
        synthetic_records.append({
            'mau_goc_id': base_id, 'dau_vao': v5_in, 'nguon': f"danh_muc:{base_id}_v5",
            'so_nha': full_num, 'ngo_ngach_hem': '', 'thon_xom': '', 'duong': full_street,
            'ma_xa_cu': w['ma_xa'], 'ma_huyen_cu': d['ma_huyen'], 'ma_tinh_cu': p['ma_tinh'],
            'ma_xa': '', 'ma_tinh': new_p_code, 'xa_phuong': '', 'tinh': new_p_name,
            'dia_chi_chuan': v3_std,
            'canh_bao': json.dumps(['nhan_tong_hop', 'doi_thu_tu', 'xa_bi_chia'], ensure_ascii=False),
            'loai_nhan': 'tong_hop', 'nguon_du_lieu': 'danh_muc_hanh_chinh',
            'ghi_chu': f"mau_goc_id={base_id}; bien_the=xa_bi_chia_doi_thu_tu; xa_moi_ung_vien={json.dumps(candidates_info, ensure_ascii=False)}"
        })

    # ========================================================
    # C) Xã mới (mốc 2025: 60 cơ sở * 6 biến thể = 360 mẫu)
    # ========================================================
    for nw in selected_new:
        base_counter += 1
        base_id = f"SYN_BASE_{base_counter:04d}"
        np = cat.new_pi[nw['ma_tinh']]
        
        street_raw = rng.choice(SAMPLE_STREETS)
        num_raw = rng.choice(SAMPLE_NUMBERS)
        alley_raw = rng.choice(SAMPLE_ALLEYS)
        
        full_num = f"Số {num_raw}"
        full_street = f"Đường {street_raw}"
        target_ward_full = cat.full_name(nw, 'xa')
        target_prov_full = cat.full_name(np, 'tinh')
        
        v1_std = f"{full_num}, {full_street}, {target_ward_full}, {target_prov_full}"
        v_alley_std = f"{full_num}, {alley_raw}, {full_street}, {target_ward_full}, {target_prov_full}"
        
        # 1. Chuẩn mốc mới
        v1_in = f"{full_num}, {full_street}, {target_ward_full}, {target_prov_full}"
        synthetic_records.append({
            'mau_goc_id': base_id, 'dau_vao': v1_in, 'nguon': f"danh_muc:{base_id}_v1",
            'so_nha': full_num, 'ngo_ngach_hem': '', 'thon_xom': '', 'duong': full_street,
            'ma_xa_cu': '', 'ma_huyen_cu': '', 'ma_tinh_cu': '',
            'ma_xa': nw['ma_xa'], 'ma_tinh': np['ma_tinh'],
            'xa_phuong': target_ward_full, 'tinh': target_prov_full, 'dia_chi_chuan': v1_std,
            'canh_bao': json.dumps(['nhan_tong_hop', 'moc_moi'], ensure_ascii=False),
            'loai_nhan': 'tong_hop', 'nguon_du_lieu': 'danh_muc_hanh_chinh',
            'ghi_chu': f"mau_goc_id={base_id}; bien_the=chuan_moc_moi; so_nha va duong la gia dinh khong phai dia chi that xac minh"
        })
        
        # 2. Có ngõ ngách mốc mới
        v2_in = f"{full_num}, {alley_raw}, {full_street}, {target_ward_full}, {target_prov_full}"
        synthetic_records.append({
            'mau_goc_id': base_id, 'dau_vao': v2_in, 'nguon': f"danh_muc:{base_id}_v2",
            'so_nha': full_num, 'ngo_ngach_hem': alley_raw, 'thon_xom': '', 'duong': full_street,
            'ma_xa_cu': '', 'ma_huyen_cu': '', 'ma_tinh_cu': '',
            'ma_xa': nw['ma_xa'], 'ma_tinh': np['ma_tinh'],
            'xa_phuong': target_ward_full, 'tinh': target_prov_full, 'dia_chi_chuan': v_alley_std,
            'canh_bao': json.dumps(['nhan_tong_hop', 'co_ngo_ngach_hem', 'moc_moi'], ensure_ascii=False),
            'loai_nhan': 'tong_hop', 'nguon_du_lieu': 'danh_muc_hanh_chinh',
            'ghi_chu': f"mau_goc_id={base_id}; bien_the=ngo_ngach_moc_moi"
        })
        
        # 3. Lỗi gõ mốc mới
        v3_in = f"{num_raw} dduowng {street_raw}, {nw['loai_xa']} {nw['ten_xa']}, {target_prov_full}"
        synthetic_records.append({
            'mau_goc_id': base_id, 'dau_vao': v3_in, 'nguon': f"danh_muc:{base_id}_v3",
            'so_nha': full_num, 'ngo_ngach_hem': '', 'thon_xom': '', 'duong': full_street,
            'ma_xa_cu': '', 'ma_huyen_cu': '', 'ma_tinh_cu': '',
            'ma_xa': nw['ma_xa'], 'ma_tinh': np['ma_tinh'],
            'xa_phuong': target_ward_full, 'tinh': target_prov_full, 'dia_chi_chuan': v1_std,
            'canh_bao': json.dumps(['nhan_tong_hop', 'loi_chinh_ta', 'moc_moi'], ensure_ascii=False),
            'loai_nhan': 'tong_hop', 'nguon_du_lieu': 'danh_muc_hanh_chinh',
            'ghi_chu': f"mau_goc_id={base_id}; bien_the=loi_chinh_ta_moc_moi"
        })
        
        # 4. Không dấu mốc mới
        v4_in = strip_diacritics(f"{num_raw} duong {street_raw}, {nw['loai_xa']} {nw['ten_xa']}, {np['ten_tinh']}")
        synthetic_records.append({
            'mau_goc_id': base_id, 'dau_vao': v4_in, 'nguon': f"danh_muc:{base_id}_v4",
            'so_nha': full_num, 'ngo_ngach_hem': '', 'thon_xom': '', 'duong': full_street,
            'ma_xa_cu': '', 'ma_huyen_cu': '', 'ma_tinh_cu': '',
            'ma_xa': nw['ma_xa'], 'ma_tinh': np['ma_tinh'],
            'xa_phuong': target_ward_full, 'tinh': target_prov_full, 'dia_chi_chuan': v1_std,
            'canh_bao': json.dumps(['nhan_tong_hop', 'dau_vao_khong_dau', 'moc_moi'], ensure_ascii=False),
            'loai_nhan': 'tong_hop', 'nguon_du_lieu': 'danh_muc_hanh_chinh',
            'ghi_chu': f"mau_goc_id={base_id}; bien_the=khong_dau_moc_moi"
        })
        
        # 5. Viết tắt mốc mới
        v5_in = f"{num_raw} Đ. {street_raw}, {abbreviate_kind(nw['loai_xa'])} {nw['ten_xa']}, {abbreviate_kind(np['loai_tinh'])} {np['ten_tinh']}"
        synthetic_records.append({
            'mau_goc_id': base_id, 'dau_vao': v5_in, 'nguon': f"danh_muc:{base_id}_v5",
            'so_nha': full_num, 'ngo_ngach_hem': '', 'thon_xom': '', 'duong': full_street,
            'ma_xa_cu': '', 'ma_huyen_cu': '', 'ma_tinh_cu': '',
            'ma_xa': nw['ma_xa'], 'ma_tinh': np['ma_tinh'],
            'xa_phuong': target_ward_full, 'tinh': target_prov_full, 'dia_chi_chuan': v1_std,
            'canh_bao': json.dumps(['nhan_tong_hop', 'dau_vao_viet_tat', 'moc_moi'], ensure_ascii=False),
            'loai_nhan': 'tong_hop', 'nguon_du_lieu': 'danh_muc_hanh_chinh',
            'ghi_chu': f"mau_goc_id={base_id}; bien_the=viet_tat_moc_moi"
        })
        
        # 6. Đổi thứ tự mốc mới
        v6_in = f"{target_prov_full}, {target_ward_full}, {full_num} {full_street}"
        synthetic_records.append({
            'mau_goc_id': base_id, 'dau_vao': v6_in, 'nguon': f"danh_muc:{base_id}_v6",
            'so_nha': full_num, 'ngo_ngach_hem': '', 'thon_xom': '', 'duong': full_street,
            'ma_xa_cu': '', 'ma_huyen_cu': '', 'ma_tinh_cu': '',
            'ma_xa': nw['ma_xa'], 'ma_tinh': np['ma_tinh'],
            'xa_phuong': target_ward_full, 'tinh': target_prov_full, 'dia_chi_chuan': v1_std,
            'canh_bao': json.dumps(['nhan_tong_hop', 'doi_thu_tu', 'moc_moi'], ensure_ascii=False),
            'loai_nhan': 'tong_hop', 'nguon_du_lieu': 'danh_muc_hanh_chinh',
            'ghi_chu': f"mau_goc_id={base_id}; bien_the=doi_thu_tu_moc_moi"
        })

    return synthetic_records

def main():
    print("=== BẮT ĐẦU CHUẨN BỊ DỮ LIỆU TRAIN/DEV (MỐC 01/07/2025) ===")
    TRAIN_DEV_DIR.mkdir(parents=True, exist_ok=True)
    
    # 1. Tải danh mục và loại trừ 100% tập test
    cat = AdminCatalogues()
    test_urls, test_osm_ids, test_raws, test_norms = load_test_exclusion()
    print(f"Đã nạp {len(test_urls)} URL, {len(test_norms)} chuỗi test cần cô lập 100%.")
    
    # 2. Xử lý kho ứng viên OSM với kiểm tra span và nhập nhằng mốc nghiêm ngặt
    candidates_file = TEST_DIR / 'goc' / 'osm_public_candidates.jsonl'
    osm_raw_total = 0
    osm_excluded_test = 0
    osm_unqualified = 0
    osm_qualified_records = []
    seen_osm_norms = set()
    
    with open(candidates_file, 'r', encoding='utf-8') as f:
        for line in f:
            osm_raw_total += 1
            d = json.loads(line)
            
            # Kiểm tra loại trừ test
            if (d['source_url'] in test_urls or
                (d.get('osm_type'), d.get('osm_id')) in test_osm_ids or
                d['dau_vao'] in test_raws or
                norm(d['dau_vao']) in test_norms):
                osm_excluded_test += 1
                continue
                
            n_in = norm(d['dau_vao'])
            if n_in in seen_osm_norms:
                continue
            seen_osm_norms.add(n_in)
            
            rec, status = process_osm_candidate(d, cat)
            if status == "thanh_cong" and rec:
                osm_qualified_records.append(rec)
            else:
                osm_unqualified += 1
                
    print(f"Tổng số dòng kho OSM ứng viên: {osm_raw_total}")
    print(f"  Loại do rò rỉ/trùng tập test: {osm_excluded_test}")
    print(f"  Loại do thiếu thông tin hành chính / nhập nhằng mốc: {osm_unqualified}")
    print(f"  Số mẫu OSM sạch đủ điều kiện chất lượng: {len(osm_qualified_records)}")
    
    # Chọn 2.000 mẫu OSM sạch đa dạng: ưu tiên toàn bộ addr:full (địa chỉ tự nhiên do con người viết) và bù bằng structured
    addr_full_records = [r for r in osm_qualified_records if 'input_mode=addr:full' in r['ghi_chu']]
    structured_records = [r for r in osm_qualified_records if 'input_mode=addr:full' not in r['ghi_chu']]
    
    rng = random.Random(42)
    rng.shuffle(structured_records)
    n_structured_needed = max(0, 2000 - len(addr_full_records))
    selected_osm = addr_full_records + structured_records[:n_structured_needed]
    print(f"  Chọn sử dụng tập hạt nhân OSM: {len(selected_osm)} mẫu (addr:full: {len(addr_full_records)}, structured: {len(selected_osm) - len(addr_full_records)}).")
    
    # 3. Sinh dữ liệu tổng hợp
    synthetic_records = generate_synthetic_samples(cat, seed=42)
    # Lọc bỏ nếu có bất kỳ chuỗi tổng hợp nào trùng test (bảo đảm an toàn tuyệt đối)
    synthetic_clean = []
    synthetic_excluded_test = 0
    for r in synthetic_records:
        if norm(r['dau_vao']) in test_norms:
            synthetic_excluded_test += 1
            continue
        synthetic_clean.append(r)
        
    print(f"Tổng số mẫu tổng hợp sinh từ 500 ĐVHC cơ sở: {len(synthetic_records)}")
    if synthetic_excluded_test > 0:
        print(f"  Loại do trùng chuỗi test: {synthetic_excluded_test}")
    print(f"  Số mẫu tổng hợp sạch: {len(synthetic_clean)}")
    
    # 4. Phân chia Train/Dev theo nhóm (Group-based split)
    # Gom nhóm theo group_key
    # - Synthetic: mau_goc_id
    # - OSM: group_key (đối tượng OSM)
    
    # Chia Synthetic theo mau_goc_id
    syn_groups = defaultdict(list)
    for r in synthetic_clean:
        syn_groups[r['mau_goc_id']].append(r)
    unique_syn_bases = sorted(syn_groups.keys())
    rng.shuffle(unique_syn_bases)
    n_train_syn = int(len(unique_syn_bases) * 0.8)
    train_syn_bases = set(unique_syn_bases[:n_train_syn])
    dev_syn_bases = set(unique_syn_bases[n_train_syn:])
    
    train_syn = [r for r in synthetic_clean if r['mau_goc_id'] in train_syn_bases]
    dev_syn = [r for r in synthetic_clean if r['mau_goc_id'] in dev_syn_bases]
    
    # Chia OSM theo group_key
    osm_groups = defaultdict(list)
    for r in selected_osm:
        osm_groups[r['group_key']].append(r)
    unique_osm_groups = sorted(osm_groups.keys())
    rng.shuffle(unique_osm_groups)
    n_train_osm = int(len(unique_osm_groups) * 0.8)
    train_osm_keys = set(unique_osm_groups[:n_train_osm])
    dev_osm_keys = set(unique_osm_groups[n_train_osm:])
    
    train_osm = [r for r in selected_osm if r['group_key'] in train_osm_keys]
    dev_osm = [r for r in selected_osm if r['group_key'] in dev_osm_keys]
    
    # 5. Gán ID duy nhất và ghép tập Train, Dev
    train_records = []
    dev_records = []
    
    train_counter = 0
    for r in train_osm + train_syn:
        train_counter += 1
        rec = {k: r.get(k, '') for k in FIELDS}
        rec['id'] = f"VNTRAIN_{train_counter:05d}"
        train_records.append(rec)
        
    dev_counter = 0
    for r in dev_osm + dev_syn:
        dev_counter += 1
        rec = {k: r.get(k, '') for k in FIELDS}
        rec['id'] = f"VNDEV_{dev_counter:05d}"
        dev_records.append(rec)
        
    print(f"\n--- KẾT QUẢ PHÂN CHIA (TỶ LỆ ~80/20) ---")
    print(f"Tập TRAIN: {len(train_records)} mẫu (OSM: {len(train_osm)}, Tổng hợp: {len(train_syn)})")
    print(f"Tập DEV:   {len(dev_records)} mẫu (OSM: {len(dev_osm)}, Tổng hợp: {len(dev_syn)})")
    print(f"Tổng cộng: {len(train_records) + len(dev_records)} mẫu.")
    
    # 6. Ghi ra tệp CSV (utf-8 chuẩn)
    train_file = TRAIN_DEV_DIR / "train.csv"
    with open(train_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(train_records)
        
    dev_file = TRAIN_DEV_DIR / "dev.csv"
    with open(dev_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(dev_records)
        
    # 7. Thống kê và lưu summary.json
    all_records = train_records + dev_records
    summary = {
        'total_candidates_raw': osm_raw_total,
        'excluded_test_leakage': osm_excluded_test,
        'unqualified_osm_discarded': osm_unqualified,
        'qualified_osm_available': len(osm_qualified_records),
        'osm_selected': len(selected_osm),
        'synthetic_generated': len(synthetic_clean),
        'total_corpus': len(all_records),
        'train_count': len(train_records),
        'dev_count': len(dev_records),
        'split_ratio': f"{len(train_records)/len(all_records)*100:.1f}% / {len(dev_records)/len(all_records)*100:.1f}%",
        'random_seed': 42,
        'feature_counts': {
            'with_ngo_ngach_hem': sum(bool(r['ngo_ngach_hem']) for r in all_records),
            'mixed_era_admin': sum('tron_moc_cu_moi' in r['canh_bao'] for r in all_records),
            'intentional_typos': sum('loi_chinh_ta' in r['canh_bao'] for r in all_records),
            'split_ward_count': sum('xa_bi_chia' in r['canh_bao'] for r in all_records),
            'unaccented_count': sum(r['dau_vao'] == strip_diacritics(r['dau_vao']) for r in all_records),
            'abbreviated_count': sum('dau_vao_viet_tat' in r['canh_bao'] for r in all_records)
        },
        'train_breakdown': {
            'total': len(train_records),
            'osm_public_count': len(train_osm),
            'synthetic_count': len(train_syn),
            'with_ngo_ngach_hem': sum(bool(r['ngo_ngach_hem']) for r in train_records),
            'mixed_era_admin': sum('tron_moc_cu_moi' in r['canh_bao'] for r in train_records),
            'intentional_typos': sum('loi_chinh_ta' in r['canh_bao'] for r in train_records),
            'split_ward_count': sum('xa_bi_chia' in r['canh_bao'] for r in train_records),
            'unaccented_count': sum(r['dau_vao'] == strip_diacritics(r['dau_vao']) for r in train_records)
        },
        'dev_breakdown': {
            'total': len(dev_records),
            'osm_public_count': len(dev_osm),
            'synthetic_count': len(dev_syn),
            'with_ngo_ngach_hem': sum(bool(r['ngo_ngach_hem']) for r in dev_records),
            'mixed_era_admin': sum('tron_moc_cu_moi' in r['canh_bao'] for r in dev_records),
            'intentional_typos': sum('loi_chinh_ta' in r['canh_bao'] for r in dev_records),
            'split_ward_count': sum('xa_bi_chia' in r['canh_bao'] for r in dev_records),
            'unaccented_count': sum(r['dau_vao'] == strip_diacritics(r['dau_vao']) for r in dev_records)
        }
    }
    
    summary_file = TRAIN_DEV_DIR / "summary.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
        
    print(f"Đã lưu tệp huấn luyện: {train_file}")
    print(f"Đã lưu tệp phát triển: {dev_file}")
    print(f"Đã lưu tệp tóm tắt thống kê: {summary_file}")

if __name__ == "__main__":
    main()
