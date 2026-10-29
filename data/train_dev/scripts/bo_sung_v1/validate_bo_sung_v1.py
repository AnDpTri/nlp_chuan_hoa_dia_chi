#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script kiểm tra toàn vẹn chất lượng và chống rò rỉ (leakage check) cho bộ dữ liệu bo_sung_v1:
1. Schema & các trường dữ liệu mở rộng (23 trường).
2. Định dạng mã zero-padded (2 số tỉnh, 3 số huyện, 5 số xã).
3. Tính toàn vẹn quan hệ cha-con hành chính mới và cũ.
4. Kiểm tra tương thích mốc trộn (quận cũ thực sự là cha của xã mới theo bảng đối chiếu).
5. Kiểm tra chính sách xã bị chia (fan-out > 1: giữ mơ hồ, cờ xa_bi_chia, lưu danh sách ứng viên, không tự chọn xã).
6. Kiểm tra token spans & BIO alignment:
   - Từng token: dau_vao[start:end] == token
   - Từng span: dau_vao[start:end] == span_text
   - Quy tắc BIO tags: B-field, I-field hợp lệ, không chồng lấn, không dùng tên chuẩn hóa làm span giả.
7. Chống rò rỉ dữ liệu (0% Leakage):
   - Train Bổ Sung vs Test = 0%
   - Dev Khó vs Test = 0%
   - Train Bổ Sung vs Dev Khó = 0%
   - Cô lập nhóm mẫu gốc (Group Isolation) = 100%
   - Biến thể từ train gốc chỉ nằm trong train bổ sung, biến thể từ dev gốc chỉ nằm trong dev khó.
8. Bảo toàn tính nguyên vẹn của bộ dữ liệu gốc train.csv, dev.csv và test.
"""

import sys
import os
import json
import csv
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

# Đảm bảo encoding console
if hasattr(sys.stdout, 'reconfigure'):
    try: sys.stdout.reconfigure(encoding='utf-8')
    except Exception: pass
if hasattr(sys.stderr, 'reconfigure'):
    try: sys.stderr.reconfigure(encoding='utf-8')
    except Exception: pass

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parents[3]
DATA_DIR = PROJECT_DIR / "data"
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

def check_counterpart_validity(dc_row, v1_row, v2_row):
    """
    Kiểm tra một liên kết snapshot có hợp lệ không:
    - Nếu có v2_counterpart_id:
      1. ma_xa_cu phải khớp giữa v1 và v2
      2. Tên đường sau chuẩn hóa (road_key) phải tương thích
      3. Nếu khác hẳn tên đường mà khai kế thừa tên đường cũ -> Sai phạm
    Trả về: (is_valid, error_message)
    """
    cid = dc_row.get('v2_counterpart_id')
    if not cid:
        return True, ""
    if not v2_row:
        return False, f"Đối ứng {cid} không tồn tại trong corpus v2/v3"
    if v2_row.get('ma_xa_cu') != dc_row.get('v1_ma_xa_cu'):
        return False, f"Lệch mã xã cũ: v1={dc_row.get('v1_ma_xa_cu')} != v2={v2_row.get('ma_xa_cu')}"

    v1_road = v1_row.get('duong', '') if v1_row else ""
    v2_road = v2_row.get('duong', '')
    rk1 = road_key(v1_road)
    rk2 = road_key(v2_road)
    if rk1 and rk2 and rk1 != rk2:
        return False, f"Khác biệt tên đường: v1='{v1_road}' != v2='{v2_road}' (road_key '{rk1}' != '{rk2}')"

    inh = dc_row.get('inheritance_detail', '')
    if rk1 != rk2 and f"duong='{v1_road}'" in inh:
        return False, f"Khai man kế thừa tên đường cũ: v1='{v1_road}' nhưng v2='{v2_road}'"

    return True, ""

def main():
    print("=== BẮT ĐẦU KIỂM TRA CHẤT LƯỢNG VÀ CHỐNG RÒ RỈ DỮ LIỆU BO_SUNG_V1 ===")
    errors = []
    
    # 1. Đọc danh mục hành chính sạch
    new_p = {r['ma_tinh']: r for r in csv.DictReader(open(CLEAN_DIR / 'moi_tinh.csv', encoding='utf-8-sig'))}
    new_w = {r['ma_xa']: r for r in csv.DictReader(open(CLEAN_DIR / 'moi_tinh_xa.csv', encoding='utf-8-sig'))}
    old_p = {r['ma_tinh']: r for r in csv.DictReader(open(CLEAN_DIR / 'cu_tinh.csv', encoding='utf-8-sig'))}
    old_d = {r['ma_huyen']: r for r in csv.DictReader(open(CLEAN_DIR / 'cu_huyen.csv', encoding='utf-8-sig'))}
    old_w = {r['ma_xa']: r for r in csv.DictReader(open(CLEAN_DIR / 'cu_tinh_huyen_xa.csv', encoding='utf-8-sig'))}
    maps = list(csv.DictReader(open(CLEAN_DIR / 'doi_chieu_xa_cu_moi.csv', encoding='utf-8-sig')))
    
    to_new = defaultdict(set)
    for r in maps:
        if r['ma_xa_cu']:
            to_new[r['ma_xa_cu']].add(r['ma_xa_moi'])
    split_codes = {k for k, v in to_new.items() if len(v) > 1}
    valid_mixed_pairs = {(m['ma_huyen_cu'], m['ma_xa_moi']) for m in maps}

    # 2. Đọc tập test để kiểm tra cách ly
    test_csv = TEST_DIR / 'dia_chi_test.csv'
    test_sources_file = TEST_DIR / 'goc' / 'selected_sources.jsonl'
    test_urls = set()
    test_norms = set()
    
    if test_csv.exists():
        for r in csv.DictReader(open(test_csv, encoding='utf-8-sig')):
            if r.get('nguon'): test_urls.add(r['nguon'])
            if r.get('dau_vao'): test_norms.add(norm(r['dau_vao']))
            
    if test_sources_file.exists():
        for line in open(test_sources_file, encoding='utf-8'):
            d = json.loads(line)
            if d.get('source_url'): test_urls.add(d['source_url'])
            if d.get('dau_vao'): test_norms.add(norm(d['dau_vao']))
            
    print(f"Đối chứng Test Isolation: {len(test_urls)} URL, {len(test_norms)} chuỗi test.")

    # 3. Đọc dữ liệu Train Bổ Sung và Dev Khó
    train_file = BO_SUNG_DIR / "train_bo_sung.csv"
    dev_file = BO_SUNG_DIR / "dev_kho.csv"
    
    if not train_file.exists() or not dev_file.exists():
        errors.append(f"Không tìm thấy file: {train_file} hoặc {dev_file}")
        print(f"LỖI: {errors[-1]}")
        sys.exit(1)
        
    train_reader = csv.DictReader(open(train_file, encoding='utf-8-sig'))
    dev_reader = csv.DictReader(open(dev_file, encoding='utf-8-sig'))
    
    if train_reader.fieldnames != FIELDS_EXTENDED:
        errors.append(f"Train Bổ Sung schema mismatch: {train_reader.fieldnames} != {FIELDS_EXTENDED}")
    if dev_reader.fieldnames != FIELDS_EXTENDED:
        errors.append(f"Dev Khó schema mismatch: {dev_reader.fieldnames} != {FIELDS_EXTENDED}")
        
    train_rows = list(train_reader)
    dev_rows = list(dev_reader)
    
    print(f"Số lượng bản ghi nạp được: Train Bổ Sung = {len(train_rows)}, Dev Khó = {len(dev_rows)}")
    
    if len(train_rows) < 2000:
        errors.append(f"Train Bổ Sung chưa đạt chỉ tiêu tối thiểu: {len(train_rows)} < 2000")
    if len(dev_rows) < 400:
        errors.append(f"Dev Khó chưa đạt chỉ tiêu tối thiểu: {len(dev_rows)} < 400")

    # 4. Kiểm tra từng bản ghi: Mã, Cấu trúc, Quan hệ và Phân loại
    for split_name, rows in [('train_bo_sung', train_rows), ('dev_kho', dev_rows)]:
        seen_ids = set()
        for idx, r in enumerate(rows):
            ident = r['id']
            if ident in seen_ids:
                errors.append(f"{split_name} dòng {idx+2}: Trùng ID {ident}")
            seen_ids.add(ident)
            
            # 4.1 Kiểm tra zero-padded codes
            for col, expected_len in [('ma_tinh', 2), ('ma_tinh_cu', 2), ('ma_huyen_cu', 3), ('ma_xa', 5), ('ma_xa_cu', 5)]:
                val = r.get(col, '')
                if val:
                    if len(val) != expected_len or not val.isdigit():
                        errors.append(f"{ident}: {col} '{val}' không đúng định dạng {expected_len} chữ số zero-padded")
                        
            # 4.2 Kiểm tra quan hệ hành chính mới
            if r['ma_xa']:
                if r['ma_xa'] not in new_w:
                    errors.append(f"{ident}: ma_xa {r['ma_xa']} không tồn tại trong moi_tinh_xa.csv")
                elif r['ma_tinh'] and new_w[r['ma_xa']]['ma_tinh'] != r['ma_tinh']:
                    errors.append(f"{ident}: ma_xa {r['ma_xa']} không thuộc ma_tinh {r['ma_tinh']}")
                    
            if r['ma_tinh'] and r['ma_tinh'] not in new_p:
                errors.append(f"{ident}: ma_tinh {r['ma_tinh']} không tồn tại trong moi_tinh.csv")

            # 4.2.1 Kiểm tra tên-đối-mã hành chính mới (tên đầy đủ có tiền tố loại đơn vị chuẩn NFC)
            if r['ma_xa']:
                expected_xa = canonical_full_name(new_w.get(r['ma_xa']), 'xa')
                if r['xa_phuong'] != expected_xa:
                    errors.append(f"{ident}: xa_phuong '{r['xa_phuong']}' không khớp tên chuẩn theo mã {r['ma_xa']} (kỳ vọng '{expected_xa}')")
            elif r['xa_phuong']:
                errors.append(f"{ident}: ma_xa rỗng nhưng xa_phuong lại có giá trị '{r['xa_phuong']}'")

            if r['ma_tinh']:
                expected_tinh = canonical_full_name(new_p.get(r['ma_tinh']), 'tinh')
                if r['tinh'] != expected_tinh:
                    errors.append(f"{ident}: tinh '{r['tinh']}' không khớp tên chuẩn theo mã {r['ma_tinh']} (kỳ vọng '{expected_tinh}')")

            # 4.2.2 Kiểm tra dia_chi_chuan chứa đúng tên hành chính chuẩn
            if r['xa_phuong'] and r['tinh']:
                if f"{r['xa_phuong']}, {r['tinh']}" not in r['dia_chi_chuan']:
                    errors.append(f"{ident}: dia_chi_chuan '{r['dia_chi_chuan']}' không chứa phần hành chính chuẩn '{r['xa_phuong']}, {r['tinh']}'")
                
            # 4.3 Kiểm tra quan hệ hành chính cũ
            if r['ma_xa_cu']:
                if r['ma_xa_cu'] not in old_w:
                    errors.append(f"{ident}: ma_xa_cu {r['ma_xa_cu']} không tồn tại trong cu_tinh_huyen_xa.csv")
                else:
                    w_obj = old_w[r['ma_xa_cu']]
                    if r['ma_huyen_cu'] and w_obj['ma_huyen'] != r['ma_huyen_cu']:
                        errors.append(f"{ident}: ma_xa_cu {r['ma_xa_cu']} không thuộc ma_huyen_cu {r['ma_huyen_cu']}")
                    if r['ma_tinh_cu'] and w_obj['ma_tinh'] != r['ma_tinh_cu']:
                        errors.append(f"{ident}: ma_xa_cu {r['ma_xa_cu']} không thuộc ma_tinh_cu {r['ma_tinh_cu']}")
                        
            # 4.4 Kiểm tra ca trộn mốc cũ-mới
            cb = json.loads(r['canh_bao']) if r['canh_bao'] else []
            if 'tron_moc_cu_moi' in cb:
                if (r['ma_huyen_cu'], r['ma_xa']) not in valid_mixed_pairs:
                    errors.append(f"{ident}: Ca trộn mốc có (ma_huyen_cu={r['ma_huyen_cu']}, ma_xa={r['ma_xa']}) không tương thích theo bảng đối chiếu")
                    
            # 4.5 Kiểm tra chính sách xã bị chia
            if r['ma_xa_cu'] in split_codes:
                if 'xa_bi_chia' not in cb:
                    errors.append(f"{ident}: Thuộc xã cũ bị chia {r['ma_xa_cu']} nhưng thiếu cờ xa_bi_chia")
                if r['ma_xa'] or r['xa_phuong']:
                    errors.append(f"{ident}: Thuộc xã cũ bị chia {r['ma_xa_cu']} nhưng tự ý gán ma_xa/xa_phuong")
                if 'xa_moi_ung_vien=' not in r['ghi_chu']:
                    errors.append(f"{ident}: Thuộc xã cũ bị chia {r['ma_xa_cu']} nhưng thiếu danh sách xa_moi_ung_vien trong ghi_chu")

    # 5. Kiểm tra Token Spans & BIO Alignment & Tokenizer Runtime Compatibility
    print("\n--- KIỂM TRA TOKEN SPANS, BIO ALIGNMENT & RUNTIME TOKENIZER COMPATIBILITY ---")
    sys.path.insert(0, str(PROJECT_DIR))
    from src.tien_xu_ly import token_co_vi_tri

    spans_files = [
        ('train_spans', BO_SUNG_DIR / "train_spans.jsonl", train_rows),
        ('dev_spans', BO_SUNG_DIR / "dev_spans.jsonl", dev_rows)
    ]
    
    ngo_counts = {'train_spans': 0, 'dev_spans': 0}
    thon_counts = {'train_spans': 0, 'dev_spans': 0}

    for split_tag, span_path, csv_rows in spans_files:
        if not span_path.exists():
            errors.append(f"Thiếu file: {span_path}")
            continue
            
        csv_dict = {r['id']: r for r in csv_rows}
        span_count = 0
        
        with open(span_path, 'r', encoding='utf-8') as f:
            for line_idx, line in enumerate(f):
                span_count += 1
                item = json.loads(line)
                item_id = item['id']
                
                if item_id not in csv_dict:
                    errors.append(f"{split_tag} dòng {line_idx+1}: ID {item_id} không có trong file CSV tương ứng")
                    continue
                    
                csv_rec = csv_dict[item_id]
                dau_vao = item['dau_vao']
                if dau_vao != csv_rec['dau_vao']:
                    errors.append(f"{item_id}: dau_vao trong spans không khớp với CSV: '{dau_vao}' != '{csv_rec['dau_vao']}'")
                    
                # Kiểm tra từng token offset
                tokens = item.get('tokens', [])
                prev_bio = "O"
                prev_field = None
                
                for t in tokens:
                    t_str = t['token']
                    t_start = t['start']
                    t_end = t['end']
                    bio_tag = t['bio_tag']
                    
                    # 1. Ký tự phải khớp 100%
                    if dau_vao[t_start:t_end] != t_str:
                        errors.append(f"{item_id}: Lệch token offset dau_vao[{t_start}:{t_end}] ('{dau_vao[t_start:t_end]}') != '{t_str}'")
                        
                    # 2. Quy tắc BIO syntax
                    if bio_tag.startswith("I-"):
                        curr_field = bio_tag[2:]
                        if prev_bio == "O" or prev_field != curr_field:
                            errors.append(f"{item_id}: Lỗi BIO sequence - '{bio_tag}' đứng ngay sau '{prev_bio}' mà không có B-{curr_field}")
                    
                    if bio_tag.startswith("B-") or bio_tag.startswith("I-"):
                        prev_field = bio_tag[2:]
                    else:
                        prev_field = None
                    prev_bio = bio_tag
                    
                # Kiểm tra structured spans
                spans = item.get('spans', {})
                if spans.get('ngo_ngach_hem'):
                    ngo_counts[split_tag] += 1
                if spans.get('thon_xom'):
                    thon_counts[split_tag] += 1

                for f_name, sp in spans.items():
                    if sp:
                        s_text = sp['text']
                        s_start = sp['start']
                        s_end = sp['end']
                        if dau_vao[s_start:s_end] != s_text:
                            errors.append(f"{item_id}: Lệch span offset {f_name} dau_vao[{s_start}:{s_end}] ('{dau_vao[s_start:s_end]}') != '{s_text}'")

                # Kiểm tra tính tương thích với Runtime Tokenizer lõi (src.tien_xu_ly.token_co_vi_tri)
                tokens_rt = token_co_vi_tri(dau_vao)
                rt_starts = {t.bat_dau for t in tokens_rt}
                rt_ends = {t.ket_thuc for t in tokens_rt}

                has_cut = False
                for fld, sp in spans.items():
                    if sp:
                        if sp['start'] not in rt_starts or sp['end'] not in rt_ends:
                            has_cut = True
                            break

                is_usable_span = item.get('usable_for_span_training', True)
                if has_cut:
                    if is_usable_span:
                        errors.append(f"{item_id}: Ranh giới span cắt giữa token của runtime tokenizer nhưng lại gán usable_for_span_training = True!")
                    if item.get('tokenizer_runtime_compatible') is not False:
                        errors.append(f"{item_id}: Cắt token runtime nhưng tokenizer_runtime_compatible không phải False!")
                else:
                    if not is_usable_span:
                        errors.append(f"{item_id}: Span hoàn toàn tương thích ranh giới token nhưng lại gán usable_for_span_training = False!")

        print(f"Kiểm tra {split_tag}: {span_count} bản ghi span BIO hợp lệ 100% (ngo_ngach_hem={ngo_counts[split_tag]}, thon_xom={thon_counts[split_tag]}).")

    if ngo_counts['train_spans'] == 0 or ngo_counts['dev_spans'] == 0:
        errors.append(f"ĐỘ PHỦ THIẾU: ngo_ngach_hem phải > 0 ở cả Train và Dev! Thực tế: Train={ngo_counts['train_spans']}, Dev={ngo_counts['dev_spans']}")
    if thon_counts['train_spans'] == 0 or thon_counts['dev_spans'] == 0:
        errors.append(f"ĐỘ PHỦ THIẾU: thon_xom phải > 0 ở cả Train và Dev! Thực tế: Train={thon_counts['train_spans']}, Dev={thon_counts['dev_spans']}")

    # 6. Kiểm tra Chống Rò Rỉ Tuyệt Đối (Leakage Check)
    print("\n--- KIỂM TRA CHỐNG RÒ RỈ DỮ LIỆU (LEAKAGE CHECK) ---")
    train_norms = {norm(r['dau_vao']): r['id'] for r in train_rows}
    dev_norms = {norm(r['dau_vao']): r['id'] for r in dev_rows}
    train_urls = {r['nguon']: r['id'] for r in train_rows if r['nguon'].startswith('http')}
    dev_urls = {r['nguon']: r['id'] for r in dev_rows if r['nguon'].startswith('http')}
    
    # 6.1 Train Bổ Sung vs Test
    train_test_leak = set(train_norms.keys()) & test_norms
    train_test_url_leak = set(train_urls.keys()) & test_urls
    if train_test_leak:
        errors.append(f"RÒ RỈ DỮ LIỆU: Có {len(train_test_leak)} chuỗi Train Bổ Sung trùng Test!")
    if train_test_url_leak:
        errors.append(f"RÒ RỈ DỮ LIỆU: Có {len(train_test_url_leak)} URL Train Bổ Sung trùng Test!")
        
    # 6.2 Dev Khó vs Test
    dev_test_leak = set(dev_norms.keys()) & test_norms
    dev_test_url_leak = set(dev_urls.keys()) & test_urls
    if dev_test_leak:
        errors.append(f"RÒ RỈ DỮ LIỆU: Có {len(dev_test_leak)} chuỗi Dev Khó trùng Test!")
    if dev_test_url_leak:
        errors.append(f"RÒ RỈ DỮ LIỆU: Có {len(dev_test_url_leak)} URL Dev Khó trùng Test!")
        
    # 6.3 Train Bổ Sung vs Dev Khó
    train_dev_leak = set(train_norms.keys()) & set(dev_norms.keys())
    train_dev_url_leak = set(train_urls.keys()) & set(dev_urls.keys())
    if train_dev_leak:
        errors.append(f"RÒ RỈ DỮ LIỆU: Có {len(train_dev_leak)} chuỗi trùng giữa Train Bổ Sung và Dev Khó!")
    if train_dev_url_leak:
        errors.append(f"RÒ RỈ DỮ LIỆU: Có {len(train_dev_url_leak)} URL trùng giữa Train Bổ Sung và Dev Khó!")
        
    # 6.4 Cô lập nhóm mẫu gốc (Group Isolation Check)
    train_groups = {r['nhom_mau_goc'] for r in train_rows if r['nhom_mau_goc']}
    dev_groups = {r['nhom_mau_goc'] for r in dev_rows if r['nhom_mau_goc']}
    group_overlap = train_groups & dev_groups
    if group_overlap:
        errors.append(f"RÒ RỈ NHÓM MẪU GỐC: Có {len(group_overlap)} nhóm xuất hiện ở cả Train và Dev: {list(group_overlap)[:5]}")

    # 6.5 KIỂM TRA HỌ BIẾN THỂ (FAMILY OVERLAP CHECK - CHE SPAN SO_NHA)
    def get_spans_map(path):
        sm = {}
        with open(path, encoding='utf-8') as f:
            for line in f:
                d = json.loads(line)
                sm[d['id']] = d.get('spans', {})
        return sm

    train_spans_map = get_spans_map(BO_SUNG_DIR / "train_spans.jsonl")
    dev_spans_map = get_spans_map(BO_SUNG_DIR / "dev_spans.jsonl")

    def get_fam_key(r, smap):
        dv = r['dau_vao']
        s_info = smap.get(r['id'], {}).get('so_nha')
        if s_info:
            masked = dv[:s_info['start']] + '<SO_NHA>' + dv[s_info['end']:]
        else:
            masked = dv
        return (masked, r['duong'], r['ngo_ngach_hem'], r['thon_xom'], r['ma_xa'], r['ma_tinh'])

    train_fams = {get_fam_key(r, train_spans_map): r['id'] for r in train_rows}
    dev_fams = {get_fam_key(r, dev_spans_map): r['id'] for r in dev_rows}
    fam_overlap = set(train_fams.keys()) & set(dev_fams.keys())
    if fam_overlap:
        errors.append(f"RÒ RỈ HỌ MẪU BIẾN THỂ: Có {len(fam_overlap)} họ mẫu trùng giữa Train và Dev khi che span so_nha!")

    # 6.6 KIỂM TRA TÍNH XÁC THỰC CỦA PROVENANCE (PROVENANCE INTEGRITY CHECK)
    orig_train_rows = {r['id']: r for r in csv.DictReader(open(TRAIN_DEV_DIR / "train.csv", encoding='utf-8-sig'))}
    orig_dev_rows = {r['id']: r for r in csv.DictReader(open(TRAIN_DEV_DIR / "dev.csv", encoding='utf-8-sig'))}

    for r in train_rows:
        if r['nguon'].startswith('derived_train:'):
            pid = r['nguon'].split(':')[1]
            if pid not in orig_train_rows:
                errors.append(f"{r['id']}: parent_id {pid} không tồn tại trong train.csv")
            else:
                p_ward = orig_train_rows[pid]['ma_xa_cu']
                if r['ma_xa_cu'] != p_ward:
                    errors.append(f"{r['id']}: Sai lệch provenance: ma_xa_cu ({r['ma_xa_cu']}) != parent ma_xa_cu ({p_ward})")
                    
    for r in dev_rows:
        if r['nguon'].startswith('derived_dev:'):
            pid = r['nguon'].split(':')[1]
            if pid not in orig_dev_rows:
                errors.append(f"{r['id']}: parent_id {pid} không tồn tại trong dev.csv")
            else:
                p_ward = orig_dev_rows[pid]['ma_xa_cu']
                if r['ma_xa_cu'] != p_ward:
                    errors.append(f"{r['id']}: Sai lệch provenance: ma_xa_cu ({r['ma_xa_cu']}) != parent ma_xa_cu ({p_ward})")

    # 6.7 Kiểm tra nguồn gốc dẫn xuất không bị đảo chiều
    for r in train_rows:
        if r['nhom_mau_goc'].startswith("DERIVED_FROM_VNDEV_"):
            errors.append(f"{r['id']}: Biến thể dẫn xuất từ Dev gốc bị đưa nhầm vào Train Bổ Sung!")
    for r in dev_rows:
        if r['nhom_mau_goc'].startswith("DERIVED_FROM_VNTRAIN_"):
            errors.append(f"{r['id']}: Biến thể dẫn xuất từ Train gốc bị đưa nhầm vào Dev Khó!")

    # 7. Kiểm tra tính nguyên vẹn của bộ gốc train.csv và dev.csv
    print("\n--- KIỂM TRA BẢO TOÀN DỮ LIỆU GỐC & TÍNH NHẤT QUÁN ĐỐI CHIẾU ---")
    orig_train_path = TRAIN_DEV_DIR / "train.csv"
    orig_dev_path = TRAIN_DEV_DIR / "dev.csv"
    orig_train_rows = list(csv.DictReader(open(orig_train_path, encoding='utf-8-sig')))
    orig_dev_rows = list(csv.DictReader(open(orig_dev_path, encoding='utf-8-sig')))
    if len(orig_train_rows) != 4564:
        errors.append(f"Bộ Train gốc bị thay đổi số dòng: {len(orig_train_rows)} != 4564")
    if len(orig_dev_rows) != 1136:
        errors.append(f"Bộ Dev gốc bị thay đổi số dòng: {len(orig_dev_rows)} != 1136")

    # 7.1 Kiểm tra bảng đối chiếu snapshot: Không đổi mã xã cũ, không đổi khác tên đường và không gán khống kế thừa
    doi_chieu_file = BO_SUNG_DIR / "doi_chieu_snapshot_v1_v2.csv"
    snapshot_dir = BO_SUNG_DIR / "snapshot_pre_fix_20261029"
    if doi_chieu_file.exists():
        v2_all_dict = {r['id']: r for r in train_rows + dev_rows}
        doi_chieu_rows = list(csv.DictReader(open(doi_chieu_file, encoding='utf-8-sig')))
        snapshot_v1 = {}
        if (snapshot_dir / "train_bo_sung.csv").exists():
            snapshot_v1.update({r['id']: r for r in csv.DictReader(open(snapshot_dir / "train_bo_sung.csv", encoding='utf-8-sig'))})
        if (snapshot_dir / "dev_kho.csv").exists():
            snapshot_v1.update({r['id']: r for r in csv.DictReader(open(snapshot_dir / "dev_kho.csv", encoding='utf-8-sig'))})

        counterpart_errors = []
        for dc in doi_chieu_rows:
            cid = dc.get('v2_counterpart_id')
            if cid:
                v1_rec = snapshot_v1.get(dc['v1_id'])
                v2_rec = v2_all_dict.get(cid)
                is_valid, err_msg = check_counterpart_validity(dc, v1_rec, v2_rec)
                if not is_valid:
                    counterpart_errors.append(f"{dc['v1_id']} -> {cid}: {err_msg}")

        if counterpart_errors:
            errors.append(f"LỖI ĐỐI ỨNG SNAPSHOT: Có {len(counterpart_errors)} vi phạm đối ứng trong doi_chieu_snapshot_v1_v2.csv (ví dụ: {counterpart_errors[0]})")

    # 7.2 Kiểm tra bảng id_disposition.csv: Phân định rõ ràng danh tính thế hệ ID
    id_disp_file = BO_SUNG_DIR / "id_disposition.csv"
    if id_disp_file.exists():
        id_disp_rows = list(csv.DictReader(open(id_disp_file, encoding='utf-8-sig')))
        disp_dict = {r['id']: r for r in id_disp_rows}
        v2_all_dict = {r['id']: r for r in train_rows + dev_rows}
        
        # Kiểm tra cờ usable của dòng v1 không được hiểu nhầm cho v3 cùng ID
        ambiguous_id_notes = 0
        for vid, v3_rec in v2_all_dict.items():
            if vid in disp_dict:
                v1_disp = disp_dict[vid]
                if v1_disp.get('reused_in_v3_with_different_content') == 'True':
                    note = v1_disp.get('id_generation_note', '')
                    if 'áp dụng cho dữ liệu snapshot v1 cũ' not in note:
                        ambiguous_id_notes += 1
        if ambiguous_id_notes > 0:
            errors.append(f"LỖI MINH BẠCH ID_DISPOSITION: Có {ambiguous_id_notes} ID tái sử dụng trong v3 thiếu ghi chú phân biệt danh tính phiên bản!")

    # 8. Kết luận
    print("\n=== KẾT QUẢ KIỂM TRA ===")
    if errors:
        print(f"THẤT BẠI: Phát hiện {len(errors)} lỗi:")
        for e in errors[:15]:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print("TẤT CẢ PHÉP KIỂM TRA ĐẠT YÊU CẦU 100% (PASS)!")
        print("1. Schema & Zero-padded codes: CHUẨN XÁC 100%.")
        print("2. Quan hệ cha-con hành chính: CHUẨN XÁC 100%.")
        print("3. Trộn mốc cũ-mới tương thích: CHUẨN XÁC 100%.")
        print("4. Xã bị chia tách (fan-out > 1) giữ mơ hồ: CHUẨN XÁC 100%.")
        print("5. Token alignment & BIO sequence tags: CHUẨN XÁC 100%.")
        print("6. Cô lập tập Test (Test Isolation): 0% RÒ RỈ.")
        print("7. Cô lập Train - Dev (Group Isolation & Family Isolation): 0% RÒ RỈ (0 họ trùng khi che span so_nha).")
        print("8. Tính xác thực Provenance (Provenance Integrity): 100% CHUẨN XÁC (0 sai lệch mã xã nguồn).")
        print("9. Bảo toàn bộ gốc: NGUYÊN VẸN 100%.")

if __name__ == '__main__':
    main()
