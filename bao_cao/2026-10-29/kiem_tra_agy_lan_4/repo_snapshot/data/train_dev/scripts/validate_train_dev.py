#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script kiểm tra toàn vẹn và chống rò rỉ (leakage check) cho tập dữ liệu Train/Dev:
- Kiểm tra cấu trúc schema, định dạng mã zero-padded (2 số tỉnh, 3 số huyện, 5 số xã).
- Kiểm tra tính toàn vẹn quan hệ cha-con hành chính.
- Kiểm tra xã bị chia (bắt buộc gắn cờ xa_bi_chia và danh sách ứng viên, không chọn bừa).
- Kiểm tra chống rò rỉ dữ liệu (0% trùng lặp giữa Train-Test, Dev-Test, Train-Dev).
- Kiểm tra cô lập nhóm: mọi biến thể của cùng mẫu gốc chỉ nằm ở một tập.
"""

import sys
import json
import csv
import re
import unicodedata
from collections import Counter
from pathlib import Path

# Đảm bảo encoding console
if hasattr(sys.stdout, 'reconfigure'):
    try: sys.stdout.reconfigure(encoding='utf-8')
    except Exception: pass
if hasattr(sys.stderr, 'reconfigure'):
    try: sys.stderr.reconfigure(encoding='utf-8')
    except Exception: pass

BASE_DIR = Path(__file__).resolve().parents[2] # D:\nlp_chuan_hoa_dia_chi\data
CLEAN_DIR = BASE_DIR / "clean"
TEST_DIR = BASE_DIR / "test"
TRAIN_DEV_DIR = BASE_DIR / "train_dev"

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

def main():
    print("=== BẮT ĐẦU KIỂM TRA CHẤT LƯỢNG VÀ CHỐNG RÒ RỈ DỮ LIỆU TRAIN/DEV ===")
    errors = []
    
    # 1. Đọc danh mục sạch
    new_p = {r['ma_tinh']: r for r in csv.DictReader(open(CLEAN_DIR / 'moi_tinh.csv', encoding='utf-8-sig'))}
    new_w = {r['ma_xa']: r for r in csv.DictReader(open(CLEAN_DIR / 'moi_tinh_xa.csv', encoding='utf-8-sig'))}
    old_p = {r['ma_tinh']: r for r in csv.DictReader(open(CLEAN_DIR / 'cu_tinh.csv', encoding='utf-8-sig'))}
    old_d = {r['ma_huyen']: r for r in csv.DictReader(open(CLEAN_DIR / 'cu_huyen.csv', encoding='utf-8-sig'))}
    old_w = {r['ma_xa']: r for r in csv.DictReader(open(CLEAN_DIR / 'cu_tinh_huyen_xa.csv', encoding='utf-8-sig'))}
    maps = list(csv.DictReader(open(CLEAN_DIR / 'doi_chieu_xa_cu_moi.csv', encoding='utf-8-sig')))
    
    to_new = {}
    for r in maps:
        if r['ma_xa_cu']:
            to_new.setdefault(r['ma_xa_cu'], set()).add(r['ma_xa_moi'])
    split_codes = {k for k, v in to_new.items() if len(v) > 1}
    
    # 2. Đọc tập Test để kiểm tra rò rỉ
    test_csv = TEST_DIR / 'dia_chi_test.csv'
    test_sources_file = TEST_DIR / 'goc' / 'selected_sources.jsonl'
    
    test_urls = set()
    test_norms = set()
    test_raws = set()
    
    if test_csv.exists():
        for r in csv.DictReader(open(test_csv, encoding='utf-8-sig')):
            if r['nguon']: test_urls.add(r['nguon'])
            if r['dau_vao']:
                test_raws.add(r['dau_vao'])
                test_norms.add(norm(r['dau_vao']))
                
    if test_sources_file.exists():
        for line in open(test_sources_file, encoding='utf-8'):
            d = json.loads(line)
            if d.get('source_url'): test_urls.add(d['source_url'])
            if d.get('dau_vao'):
                test_raws.add(d['dau_vao'])
                test_norms.add(norm(d['dau_vao']))
                
    print(f"Đối chứng với tập Test: {len(test_urls)} URL, {len(test_norms)} chuỗi chuẩn hóa.")
    
    # 3. Đọc Train và Dev
    train_file = TRAIN_DEV_DIR / 'train.csv'
    dev_file = TRAIN_DEV_DIR / 'dev.csv'
    
    if not train_file.exists() or not dev_file.exists():
        print("LỖI: Chưa có tệp train.csv hoặc dev.csv!")
        sys.exit(1)
        
    train_reader = csv.DictReader(open(train_file, encoding='utf-8-sig'))
    dev_reader = csv.DictReader(open(dev_file, encoding='utf-8-sig'))
    
    if train_reader.fieldnames != FIELDS:
        errors.append(f"Train schema mismatch: {train_reader.fieldnames}")
    if dev_reader.fieldnames != FIELDS:
        errors.append(f"Dev schema mismatch: {dev_reader.fieldnames}")
        
    train_rows = list(train_reader)
    dev_rows = list(dev_reader)
    
    print(f"Số lượng mẫu kiểm tra: Train = {len(train_rows)}, Dev = {len(dev_rows)}")
    
    # 4. Kiểm tra mã, cấu trúc và quan hệ cha-con
    for split_name, rows in [('train', train_rows), ('dev', dev_rows)]:
        seen_ids = set()
        for idx, r in enumerate(rows):
            identifier = r['id']
            if identifier in seen_ids:
                errors.append(f"{split_name} dòng {idx+2}: Trùng ID {identifier}")
            seen_ids.add(identifier)
            
            # Kiểm tra định dạng mã zero-padded
            if r['ma_tinh'] and (len(r['ma_tinh']) != 2 or not r['ma_tinh'].isdigit()):
                errors.append(f"{identifier}: ma_tinh không đúng định dạng 2 chữ số: {r['ma_tinh']}")
            if r['ma_tinh_cu'] and (len(r['ma_tinh_cu']) != 2 or not r['ma_tinh_cu'].isdigit()):
                errors.append(f"{identifier}: ma_tinh_cu không đúng định dạng 2 chữ số: {r['ma_tinh_cu']}")
            if r['ma_huyen_cu'] and (len(r['ma_huyen_cu']) != 3 or not r['ma_huyen_cu'].isdigit()):
                errors.append(f"{identifier}: ma_huyen_cu không đúng định dạng 3 chữ số: {r['ma_huyen_cu']}")
            if r['ma_xa'] and (len(r['ma_xa']) != 5 or not r['ma_xa'].isdigit()):
                errors.append(f"{identifier}: ma_xa không đúng định dạng 5 chữ số: {r['ma_xa']}")
            if r['ma_xa_cu'] and (len(r['ma_xa_cu']) != 5 or not r['ma_xa_cu'].isdigit()):
                errors.append(f"{identifier}: ma_xa_cu không đúng định dạng 5 chữ số: {r['ma_xa_cu']}")
                
            # Kiểm tra quan hệ mới
            if r['ma_xa']:
                if r['ma_xa'] not in new_w:
                    errors.append(f"{identifier}: ma_xa không tồn tại trong danh mục mới: {r['ma_xa']}")
                elif r['ma_tinh'] and new_w[r['ma_xa']]['ma_tinh'] != r['ma_tinh']:
                    errors.append(f"{identifier}: ma_xa {r['ma_xa']} không thuộc ma_tinh {r['ma_tinh']}")
                    
            if r['ma_tinh'] and r['ma_tinh'] not in new_p:
                errors.append(f"{identifier}: ma_tinh không tồn tại trong danh mục mới: {r['ma_tinh']}")
                
            # Kiểm tra quan hệ cũ
            if r['ma_xa_cu']:
                if r['ma_xa_cu'] not in old_w:
                    errors.append(f"{identifier}: ma_xa_cu không tồn tại trong danh mục cũ: {r['ma_xa_cu']}")
                else:
                    w_obj = old_w[r['ma_xa_cu']]
                    if r['ma_huyen_cu'] and w_obj['ma_huyen'] != r['ma_huyen_cu']:
                        errors.append(f"{identifier}: ma_xa_cu {r['ma_xa_cu']} không thuộc ma_huyen_cu {r['ma_huyen_cu']}")
                    if r['ma_tinh_cu'] and w_obj['ma_tinh'] != r['ma_tinh_cu']:
                        errors.append(f"{identifier}: ma_xa_cu {r['ma_xa_cu']} không thuộc ma_tinh_cu {r['ma_tinh_cu']}")
                        
            # Kiểm tra tính tương thích của ca trộn mốc hành chính cũ-mới (topological check)
            cb = json.loads(r['canh_bao']) if r['canh_bao'] else []
            if 'tron_moc_cu_moi' in cb:
                valid_pairs = {(m['ma_huyen_cu'], m['ma_xa_moi']) for m in maps}
                if (r['ma_huyen_cu'], r['ma_xa']) not in valid_pairs:
                    errors.append(f"{identifier}: Ca trộn mốc có ma_huyen_cu {r['ma_huyen_cu']} không tương thích với ma_xa {r['ma_xa']} trong bảng đối chiếu")
                    
            # Kiểm tra span containment: Mọi thành phần chi tiết đều phải có bằng chứng chuỗi trong dau_vao
            is_typo = 'loi_chinh_ta' in cb
            raw_compact = re.sub(r'\s+', '', norm(r['dau_vao']))
            if is_typo:
                # Với mẫu cố tình tạo lỗi gõ (telex, dính chữ), chuẩn hóa ký tự lặp để đối chiếu
                raw_compact = re.sub(r'([a-z])\1+', r'\1', raw_compact)
                
            if r['so_nha']:
                num_token = re.sub(r'^(số|so)\s+', '', norm(r['so_nha'])).strip()
                num_compact = re.sub(r'\s+', '', num_token)
                if num_compact and (num_compact not in raw_compact and num_token not in norm(r['dau_vao'])):
                    errors.append(f"{identifier}: so_nha '{r['so_nha']}' không có bằng chứng span trong dau_vao: '{r['dau_vao']}'")
            if r['duong']:
                bs = bare_street(r['duong'])
                bs_compact = re.sub(r'\s+', '', bs)
                if is_typo:
                    bs_compact = re.sub(r'([a-z])\1+', r'\1', bs_compact)
                if bs_compact and (bs in norm(r['dau_vao']) or bs_compact in raw_compact):
                    pass
                else:
                    errors.append(f"{identifier}: duong '{r['duong']}' không có bằng chứng span trong dau_vao: '{r['dau_vao']}'")
            if r['ngo_ngach_hem']:
                b_ng = re.sub(r'^(ngõ|ngách|hẻm|kiệt|ngo|ngach|hem|kiet)\s+', '', norm(r['ngo_ngach_hem'])).strip()
                b_ng_compact = re.sub(r'\s+', '', b_ng)
                if b_ng_compact and (b_ng in norm(r['dau_vao']) or b_ng_compact in raw_compact):
                    pass
                else:
                    errors.append(f"{identifier}: ngo_ngach_hem '{r['ngo_ngach_hem']}' không có bằng chứng span trong dau_vao: '{r['dau_vao']}'")
                    
            # Kiểm tra nguồn gốc và nhãn minh bạch
            if r['loai_nhan'] not in ('nhan_may', 'tong_hop'):
                errors.append(f"{identifier}: loai_nhan không hợp lệ: {r['loai_nhan']}")
            if r.get('trang_thai_nhan') == 'da_duyet':
                errors.append(f"{identifier}: Dữ liệu train/dev không được tự động đánh dấu da_duyet")
            if r['loai_nhan'] == 'tong_hop' and r['nguon_du_lieu'] != 'danh_muc_hanh_chinh':
                errors.append(f"{identifier}: Nguồn dữ liệu tổng hợp phải là danh_muc_hanh_chinh")
            if r['loai_nhan'] == 'nhan_may' and r['nguon_du_lieu'] != 'osm_public':
                errors.append(f"{identifier}: Nguồn dữ liệu máy phải là osm_public")

            # Kiểm tra xã bị chia: Bắt buộc gắn cờ xa_bi_chia và KHÔNG tự ý chốt xã
            if r['ma_xa_cu'] in split_codes:
                if 'xa_bi_chia' not in cb:
                    errors.append(f"{identifier}: Thuộc xã cũ bị chia {r['ma_xa_cu']} nhưng thiếu cờ xa_bi_chia")
                if r['ma_xa'] or r['xa_phuong']:
                    errors.append(f"{identifier}: Thuộc xã cũ bị chia {r['ma_xa_cu']} nhưng tự ý gán ma_xa/xa_phuong")
                if 'xa_moi_ung_vien=' not in r['ghi_chu']:
                    errors.append(f"{identifier}: Thuộc xã cũ bị chia {r['ma_xa_cu']} nhưng thiếu danh sách xa_moi_ung_vien trong ghi_chu")

        # Kiểm tra sự hiện diện của các thuộc tính mới trong tập
        n_ngo = sum(bool(r['ngo_ngach_hem']) for r in rows)
        n_tron = sum('tron_moc_cu_moi' in r['canh_bao'] for r in rows)
        n_loi = sum('loi_chinh_ta' in r['canh_bao'] for r in rows)
        if n_ngo == 0:
            errors.append(f"{split_name}: Số lượng mẫu có ngo_ngach_hem phải > 0 (hiện tại = 0)!")
        if n_tron == 0:
            errors.append(f"{split_name}: Số lượng mẫu trộn mốc cũ-mới phải > 0 (hiện tại = 0)!")
        if n_loi == 0:
            errors.append(f"{split_name}: Số lượng mẫu có lỗi gõ chính tả phải > 0 (hiện tại = 0)!")

    # 5. Kiểm tra rò rỉ giữa các tập (Leakage Check)
    train_norms = {norm(r['dau_vao']): r['id'] for r in train_rows}
    dev_norms = {norm(r['dau_vao']): r['id'] for r in dev_rows}
    train_urls = {r['nguon']: r['id'] for r in train_rows if r['nguon'].startswith('http')}
    dev_urls = {r['nguon']: r['id'] for r in dev_rows if r['nguon'].startswith('http')}
    
    # 5.1 Rò rỉ Train vs Test
    train_test_norm_leak = set(train_norms.keys()) & test_norms
    train_test_url_leak = set(train_urls.keys()) & test_urls
    if train_test_norm_leak:
        errors.append(f"RÒ RỈ DỮ LIỆU: Có {len(train_test_norm_leak)} chuỗi Train trùng với Test!")
    if train_test_url_leak:
        errors.append(f"RÒ RỈ DỮ LIỆU: Có {len(train_test_url_leak)} URL OSM Train trùng với Test!")
        
    # 5.2 Rò rỉ Dev vs Test
    dev_test_norm_leak = set(dev_norms.keys()) & test_norms
    dev_test_url_leak = set(dev_urls.keys()) & test_urls
    if dev_test_norm_leak:
        errors.append(f"RÒ RỈ DỮ LIỆU: Có {len(dev_test_norm_leak)} chuỗi Dev trùng với Test!")
    if dev_test_url_leak:
        errors.append(f"RÒ RỈ DỮ LIỆU: Có {len(dev_test_url_leak)} URL OSM Dev trùng với Test!")
        
    # 5.3 Rò rỉ Train vs Dev
    train_dev_norm_leak = set(train_norms.keys()) & set(dev_norms.keys())
    train_dev_url_leak = set(train_urls.keys()) & set(dev_urls.keys())
    if train_dev_norm_leak:
        errors.append(f"RÒ RỈ DỮ LIỆU: Có {len(train_dev_norm_leak)} chuỗi trùng giữa Train và Dev!")
    if train_dev_url_leak:
        errors.append(f"RÒ RỈ DỮ LIỆU: Có {len(train_dev_url_leak)} URL OSM trùng giữa Train và Dev!")
        
    # 5.4 Cô lập nhóm mẫu gốc Synthetic (Group Isolation Check)
    def extract_base_id(ghi_chu):
        m = re.search(r'mau_goc_id=(SYN_BASE_\d+)', ghi_chu)
        return m.group(1) if m else None
        
    train_bases = {extract_base_id(r['ghi_chu']) for r in train_rows if extract_base_id(r['ghi_chu'])}
    dev_bases = {extract_base_id(r['ghi_chu']) for r in dev_rows if extract_base_id(r['ghi_chu'])}
    
    base_leak = train_bases & dev_bases
    if base_leak:
        errors.append(f"RÒ RỈ NHÓM TỔNG HỢP: Có {len(base_leak)} mẫu gốc xuất hiện ở cả Train và Dev: {list(base_leak)[:5]}")
        
    # 6. Đánh giá và lưu báo cáo
    status = "PASS" if not errors else "FAIL"
    
    leakage_report = {
        'status': status,
        'errors': errors,
        'statistics': {
            'train_rows': len(train_rows),
            'dev_rows': len(dev_rows),
            'test_rows_checked': len(test_raws),
            'train_test_overlap_norm': len(train_test_norm_leak),
            'train_test_overlap_url': len(train_test_url_leak),
            'dev_test_overlap_norm': len(dev_test_norm_leak),
            'dev_test_overlap_url': len(dev_test_url_leak),
            'train_dev_overlap_norm': len(train_dev_norm_leak),
            'train_dev_overlap_url': len(train_dev_url_leak),
            'synthetic_base_overlap': len(base_leak)
        },
        'verification_summary': {
            'schema_valid': train_reader.fieldnames == FIELDS and dev_reader.fieldnames == FIELDS,
            'zero_padded_codes_valid': all(len(e) == 0 for e in errors if 'định dạng' in e),
            'hierarchy_integrity_valid': all(len(e) == 0 for e in errors if 'không thuộc' in e or 'không tồn tại' in e),
            'split_ward_rules_enforced': all(len(e) == 0 for e in errors if 'xa_bi_chia' in e),
            'span_grounding_verified': all(len(e) == 0 for e in errors if 'bằng chứng span' in e),
            'mixed_era_compatibility_verified': all(len(e) == 0 for e in errors if 'trộn mốc' in e and 'không tương thích' in e),
            'ngo_ngach_hem_represented': sum(bool(r['ngo_ngach_hem']) for r in train_rows) > 0 and sum(bool(r['ngo_ngach_hem']) for r in dev_rows) > 0,
            'complete_test_isolation': len(train_test_norm_leak) == 0 and len(train_test_url_leak) == 0 and len(dev_test_norm_leak) == 0 and len(dev_test_url_leak) == 0,
            'group_split_isolation': len(base_leak) == 0
        }
    }
    
    report_file = TRAIN_DEV_DIR / "leakage_report.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(leakage_report, f, ensure_ascii=False, indent=2)
        
    print(f"\nKết quả kiểm tra: {status}")
    print(f"Báo cáo chi tiết: {report_file}")
    if errors:
        print(f"Tổng số lỗi phát hiện: {len(errors)}")
        for e in errors[:10]:
            print("  -", e)
        sys.exit(1)
    else:
        print("TẤT CẢ CÁC PHÉP KIỂM TRA ĐẠT YÊU CẦU 100% (0% RÒ RỈ DỮ LIỆU).")

if __name__ == "__main__":
    main()
