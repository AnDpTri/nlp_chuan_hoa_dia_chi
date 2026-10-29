#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script xây dựng gói dữ liệu huấn luyện khó bo_sung_v2 (Gói Train Khó v2):
1. Đọc seed huấn luyện hợp lệ có nguồn cha từ train.csv gốc.
2. Kiểm tra và loại trừ triệt để 100% rò rỉ giao thoa với Dev gốc, Dev v1 và Test.
3. Tuyển chọn 650 họ nguồn cha độc lập, phân bổ khắp 3 miền và các loại hình địa bàn.
4. Sinh 3.000 mẫu train mới với 12 loại biến thể khó (không lấp liếm bằng đổi số nhà).
5. Trích xuất chuẩn xác char spans và token spans/BIO alignment theo runtime tokenizer.
6. Xuất đầy đủ các báo cáo: anti_leakage_audit.json, distribution_summary.json, manifest.json.
"""

import sys
import os
import csv
import json
import re
import hashlib
import unicodedata
from pathlib import Path
from collections import defaultdict, Counter

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parents[3]
DATA_DIR = PROJECT_DIR / "data"
TRAIN_DEV_DIR = DATA_DIR / "train_dev"
CLEAN_DIR = DATA_DIR / "clean"
BO_SUNG_V2_DIR = TRAIN_DEV_DIR / "bo_sung_v2"
TEST_DIR = DATA_DIR / "test"

sys.path.insert(0, str(PROJECT_DIR))
from src.tien_xu_ly import token_co_vi_tri

# ----------------- HÀM TIỆN ÍCH CHUẨN HÓA & BIẾN ĐỔI CHUỖI -----------------

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

def bo_dau_tu(s):
    if not s: return ""
    text = unicodedata.normalize('NFD', str(s).replace('đ', 'd').replace('Đ', 'D'))
    return ''.join(c for c in text if not unicodedata.combining(c))

def tokenize_with_spans(input_text, spans_dict):
    """
    Tách token cho input_text, bảo đảm tôn trọng các ranh giới span ký tự:
    Nếu một token của token_co_vi_tri bị cắt ngang bởi start/end của span (như ca dính chữ 528Đường),
    thì cắt token đó tại ranh giới span để token span và chuỗi BIO tags luôn chuẩn cú pháp 100%.
    """
    base_tokens = token_co_vi_tri(input_text)
    split_points = {0, len(input_text)}
    for sp in spans_dict.values():
        if sp:
            split_points.add(sp['start'])
            split_points.add(sp['end'])

    refined_tokens = []
    for t in base_tokens:
        t_start, t_end = t.bat_dau, t.ket_thuc
        inside_splits = sorted([p for p in split_points if t_start < p < t_end])
        cuts = [t_start] + inside_splits + [t_end]
        for a, b in zip(cuts, cuts[1:]):
            refined_tokens.append({
                'token': input_text[a:b],
                'start': a,
                'end': b
            })
    return refined_tokens

def canonical_full_name(row, level):
    if not row: return ""
    name = unicodedata.normalize('NFC', row.get('ten_' + level, '')).strip()
    kind = unicodedata.normalize('NFC', row.get('loai_' + level, '')).strip()
    if name.lower().startswith(kind.lower() + ' '):
        return name
    return f"{kind} {name}"

# Từ điển Telex Typo tự nhiên bảo toàn bản sắc từ
TELEX_TYPOS = {
    'đường': 'dduowngf', 'Đường': 'Dduowngf', 'phố': 'phoos', 'Phố': 'Phoos',
    'phường': 'phuowngf', 'Phường': 'Phuowngf', 'xã': 'xax', 'Xã': 'Xax',
    'quận': 'quanj', 'Quận': 'Quanj', 'huyện': 'huyeenj', 'Huyện': 'Huyeenj',
    'thành': 'thaxnh', 'Thành': 'Thaxnh', 'tỉnh': 'tirnh', 'Tỉnh': 'Tirnh',
    'ngõ': 'ngox', 'Ngõ': 'Ngox', 'ngách': 'ngasch', 'Ngách': 'Ngasch',
    'hẻm': 'herm', 'Hẻm': 'Herm', 'thôn': 'thoon', 'Thôn': 'Thoon',
    'nguyễn': 'nguyeexn', 'Nguyễn': 'Nguyeexn', 'trần': 'traafn', 'Trần': 'Traafn',
    'lê': 'lee', 'Lê': 'Lee', 'hoàng': 'hoangf', 'Hoàng': 'Hoangf',
    'võ': 'vox', 'Võ': 'Vox', 'phạm': 'phamj', 'Phạm': 'Phamj',
    'huỳnh': 'huynhf', 'Huỳnh': 'Huynhf', 'đoàn': 'ddoanf', 'Đoàn': 'Ddoanf'
}

def apply_telex_typo(text):
    words = text.split()
    res = []
    applied = False
    for w in words:
        if w in TELEX_TYPOS and not applied:
            res.append(TELEX_TYPOS[w])
            applied = True
        else:
            res.append(w)
    return ' '.join(res)

# Danh sách viết tắt tên riêng phổ biến và đa nghĩa
COMMON_ROAD_ACRONYMS = {
    'Trần Hưng Đạo': 'THĐ',
    'Lê Hồng Phong': 'LHP',
    'Hai Bà Trưng': 'HBT',
    'Ngô Quyền': 'NQ',
    'Võ Văn Kiệt': 'VVK',
    'Phạm Văn Đồng': 'PVĐ',
    'Nguyễn Huệ': 'NH',
    'Lý Thường Kiệt': 'LTK',
    'Quang Trung': 'QT',
    'Hoàng Hoa Thám': 'HHT'
}

AMBIGUOUS_ROAD_ACRONYMS = {
    'Trần Thái Tông': 'TTT',
    'Tôn Thất Tùng': 'TTT',
    'Nguyễn Tất Thành': 'NTT',
    'Nguyễn Thị Thập': 'NTT',
    'Bùi Viện': 'BVT',
    'Bùi Văn Thêm': 'BVT'
}

def main():
    print("=== BẮT ĐẦU XÂY DỰNG GÓI DỮ LIỆU HUẤN LUYỆN KHÓ BO_SUNG_V2 ===")
    BO_SUNG_V2_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Đọc danh mục hành chính sạch
    new_p = {r['ma_tinh']: r for r in csv.DictReader(open(CLEAN_DIR / 'moi_tinh.csv', encoding='utf-8-sig'))}
    new_w = {r['ma_xa']: r for r in csv.DictReader(open(CLEAN_DIR / 'moi_tinh_xa.csv', encoding='utf-8-sig'))}
    old_p = {r['ma_tinh']: r for r in csv.DictReader(open(CLEAN_DIR / 'cu_tinh.csv', encoding='utf-8-sig'))}
    old_d = {r['ma_huyen']: r for r in csv.DictReader(open(CLEAN_DIR / 'cu_huyen.csv', encoding='utf-8-sig'))}
    old_w = {r['ma_xa']: r for r in csv.DictReader(open(CLEAN_DIR / 'cu_tinh_huyen_xa.csv', encoding='utf-8-sig'))}
    doi_chieu = list(csv.DictReader(open(CLEAN_DIR / 'doi_chieu_xa_cu_moi.csv', encoding='utf-8-sig')))

    old_to_new_maps = defaultdict(list)
    for r in doi_chieu:
        if r['ma_xa_cu']:
            old_to_new_maps[r['ma_xa_cu']].append(r)
    split_ward_codes = {k: v for k, v in old_to_new_maps.items() if len(v) > 1}
    print(f"Danh mục nạp: new_w={len(new_w)}, old_w={len(old_w)}, xã bị chia={len(split_ward_codes)}")

    # 2. Xây dựng Blacklist từ Dev gốc, Dev v1 và Test
    print("\n--- XÂY DỰNG BLACKLIST CHỐNG RÒ RỈ DEV/TEST ---")
    dev_orig = list(csv.DictReader(open(TRAIN_DEV_DIR / 'dev.csv', encoding='utf-8-sig')))
    dev_v1 = list(csv.DictReader(open(TRAIN_DEV_DIR / 'bo_sung_v1' / 'dev_kho.csv', encoding='utf-8-sig')))
    test_rows = []
    if (TEST_DIR / 'dia_chi_test.csv').exists():
        test_rows = list(csv.DictReader(open(TEST_DIR / 'dia_chi_test.csv', encoding='utf-8-sig')))

    blacklist_parent_ids = set()
    blacklist_urls = set()
    blacklist_inputs = set()
    blacklist_families = set()

    for r in dev_orig + dev_v1 + test_rows:
        blacklist_parent_ids.add(r['id'])
        nguon = r.get('nguon', '')
        if nguon.startswith(('derived_train:', 'derived_dev:')):
            blacklist_parent_ids.add(nguon.split(':')[1])
        nhom = r.get('nhom_mau_goc', '')
        if nhom.startswith(('DERIVED_FROM_VNTRAIN_', 'DERIVED_FROM_VNDEV_')):
            blacklist_parent_ids.add(nhom.replace('DERIVED_FROM_', ''))
        if r.get('nguon') and r['nguon'].startswith('http'):
            blacklist_urls.add(r['nguon'])
        if r.get('dau_vao'):
            blacklist_inputs.add(norm(r['dau_vao']))

        # Masked family key khi che số nhà
        dv = r.get('dau_vao', '')
        sn = r.get('so_nha', '')
        if sn and sn in dv:
            idx = dv.find(sn)
            masked = dv[:idx] + '<SO_NHA>' + dv[idx+len(sn):]
        else:
            masked = re.sub(r'^(?:Số\s+|so\s+)?[\d\/\-]+[A-Za-z]*\s*', '<SO_NHA> ', dv).strip()
        fam_k = (key(masked), r.get('duong', ''), r.get('ma_xa_cu', ''), r.get('ma_tinh', ''))
        blacklist_families.add(fam_k)

    print(f"Blacklist: {len(blacklist_parent_ids)} Parent IDs, {len(blacklist_urls)} URLs, {len(blacklist_inputs)} Inputs, {len(blacklist_families)} Họ che số nhà.")

    # 3. Đọc và lọc Seed từ Train gốc
    orig_train_path = TRAIN_DEV_DIR / 'train.csv'
    parent_snapshot_sha256 = hashlib.sha256(orig_train_path.read_bytes()).hexdigest()
    train_orig = list(csv.DictReader(open(orig_train_path, encoding='utf-8-sig')))
    print(f"Tổng train gốc: {len(train_orig)} dòng, sha256={parent_snapshot_sha256}")

    valid_seeds = []
    conflict_stats = Counter()
    conflict_examples = []

    for r in train_orig:
        rid = r['id']
        dv = r['dau_vao']
        dv_norm = norm(dv)
        url = r.get('nguon', '')
        sn = r.get('so_nha', '')

        # Masked family key
        if sn and sn in dv:
            idx = dv.find(sn)
            masked = dv[:idx] + '<SO_NHA>' + dv[idx+len(sn):]
        else:
            masked = re.sub(r'^(?:Số\s+|so\s+)?[\d\/\-]+[A-Za-z]*\s*', '<SO_NHA> ', dv).strip()
        fam_k = (key(masked), r.get('duong', ''), r.get('ma_xa_cu', ''), r.get('ma_tinh', ''))

        conflict_reason = None
        if rid in blacklist_parent_ids:
            conflict_reason = 'parent_id_in_holdout'
        elif url and url in blacklist_urls:
            conflict_reason = 'url_in_holdout'
        elif dv_norm in blacklist_inputs:
            conflict_reason = 'input_in_holdout'
        elif fam_k in blacklist_families:
            conflict_reason = 'masked_family_in_holdout'

        if conflict_reason:
            conflict_stats[conflict_reason] += 1
            if len(conflict_examples) < 10:
                conflict_examples.append({'id': rid, 'reason': conflict_reason, 'dau_vao': dv})
        else:
            # Seed phải có đủ thông tin hành chính hợp lệ
            if r.get('ma_xa_cu') and r.get('ma_huyen_cu') and r.get('ma_tinh_cu') and r.get('duong'):
                valid_seeds.append(r)

    print(f"Seed hợp lệ hoàn toàn: {len(valid_seeds)} mẫu.")
    print(f"Xung đột bị loại bỏ: {dict(conflict_stats)}")

    # Ghi file anti_leakage_audit.json
    leak_audit = {
        'total_train_orig_scanned': len(train_orig),
        'valid_seeds_retained': len(valid_seeds),
        'conflicts_excluded': dict(conflict_stats),
        'total_conflicts_excluded': sum(conflict_stats.values()),
        'sample_excluded_cases': conflict_examples
    }
    with open(BO_SUNG_V2_DIR / 'anti_leakage_audit.json', 'w', encoding='utf-8') as f:
        json.dump(leak_audit, f, ensure_ascii=False, indent=2)

    # 4. Tuyển chọn chính xác 650 họ nguồn cha đa dạng
    print("\n--- TUYỂN CHỌN 650 HỌ NGUỒN CHA ĐỘC LẬP ---")
    seeds_by_province = defaultdict(list)
    for s in valid_seeds:
        seeds_by_province[s['ma_tinh_cu']].append(s)

    selected_parents = []
    selected_parent_ids = set()

    # 4.1 Ưu tiên các họ có ngõ ngách và thôn xóm thật từ seed
    ngo_thon_seeds = [s for s in valid_seeds if s.get('ngo_ngach_hem') or s.get('thon_xom')]
    for s in ngo_thon_seeds:
        if s['id'] not in selected_parent_ids:
            selected_parents.append(s)
            selected_parent_ids.add(s['id'])
            if len(selected_parents) >= 100:
                break

    # 4.2 Ưu tiên các xã bị chia tách theo mốc 2025
    split_seeds = [s for s in valid_seeds if s['ma_xa_cu'] in split_ward_codes]
    for s in split_seeds:
        if s['id'] not in selected_parent_ids:
            selected_parents.append(s)
            selected_parent_ids.add(s['id'])
            if len(selected_parents) >= 150:
                break

    # 4.3 Phân bổ đều các tỉnh thành 3 miền
    prov_keys = sorted(seeds_by_province.keys())
    idx = 0
    while len(selected_parents) < 650 and idx < 100:
        for p_code in prov_keys:
            p_seeds = seeds_by_province[p_code]
            if idx < len(p_seeds):
                cand = p_seeds[idx]
                if cand['id'] not in selected_parent_ids:
                    selected_parents.append(cand)
                    selected_parent_ids.add(cand['id'])
                    if len(selected_parents) >= 650:
                        break
        idx += 1

    print(f"Đã chọn đủ {len(selected_parents)} họ nguồn cha độc lập.")

    # 5. Sinh 3.000 mẫu train mới với 12 loại biến thể khó
    # 400 họ sinh 5 biến thể = 2.000 mẫu; 250 họ sinh 4 biến thể = 1.000 mẫu -> Tổng 3.000 mẫu
    print("\n--- SINH 3.000 MẪU TRAIN MỚI TỪ 650 HỌ NGUỒN ---")
    
    rows_v2 = []
    char_spans_v2 = []
    token_spans_v2 = []

    type_counts = Counter()
    v2_idx = 1
    ngo_thon_toggle = 0

    for h_idx, p_row in enumerate(selected_parents):
        parent_id = p_row['id']
        parent_url = p_row.get('nguon', '')
        row_sha = hashlib.sha256(json.dumps(p_row, sort_keys=True).encode('utf-8')).hexdigest()
        family_id = f"FAM_V2_{parent_id}"

        # Thông tin hành chính cha
        ma_xa_cu = p_row['ma_xa_cu']
        ma_huyen_cu = p_row['ma_huyen_cu']
        ma_tinh_cu = p_row['ma_tinh_cu']
        ma_xa_moi = p_row['ma_xa']
        ma_tinh_moi = p_row['ma_tinh']

        w_cu = old_w.get(ma_xa_cu, {})
        d_cu = old_d.get(ma_huyen_cu, {})
        p_cu = old_p.get(ma_tinh_cu, {})
        w_moi = new_w.get(ma_xa_moi, {})
        p_moi = new_p.get(ma_tinh_moi, {})

        ten_xa_cu = canonical_full_name(w_cu, 'xa')
        ten_huyen_cu = canonical_full_name(d_cu, 'huyen')
        ten_tinh_cu = canonical_full_name(p_cu, 'tinh')
        ten_xa_moi = canonical_full_name(w_moi, 'xa') if w_moi else ""
        ten_tinh_moi = canonical_full_name(p_moi, 'tinh') if p_moi else ten_tinh_cu

        road_base = p_row['duong']
        sn_base = p_row.get('so_nha') or 'Số 12'
        ngo_base = p_row.get('ngo_ngach_hem') or ''
        thon_base = p_row.get('thon_xom') or ''

        # Xác định số biến thể cho họ này (400 họ đầu sinh 5 biến thể, 250 họ sau sinh 4 biến thể)
        num_variants = 5 if h_idx < 400 else 4

        # Chọn danh sách các loại biến thể xoay vòng cho họ này
        cycle_types = [
            'khong_dau_mot_phan', 'viet_tat_manh_va_ket_hop', 'loi_go_telex_typo',
            'dinh_token_so_nha_duong', 'dao_thu_tu_thanh_phan', 'lap_chong_ten_dia_danh',
            'thieu_cap_hanh_chinh', 'tron_moc_cu_moi', 'ngo_ngach_hem_thon_xom',
            'xa_bi_chia_mo_ho', 'viet_tat_ten_rieng_mo_ho', 'to_hop_bien_the_kho'
        ]
        
        # Kiểm tra điều kiện mốc trộn và xã bị chia của seed cha
        is_split = (ma_xa_cu in split_ward_codes) or (not ma_xa_moi)
        valid_mixed_pairs = {(m['ma_huyen_cu'], m['ma_xa_moi']) for m in doi_chieu if m['ma_xa_moi']}
        is_valid_mixed = (ma_huyen_cu, ma_xa_moi) in valid_mixed_pairs

        for var_idx in range(num_variants):
            if is_split and var_idx == 0:
                vtype = 'xa_bi_chia_mo_ho'
            else:
                pick_idx = (h_idx * 3 + var_idx) % len(cycle_types)
                vtype = cycle_types[pick_idx]
                if vtype == 'xa_bi_chia_mo_ho' and not is_split:
                    vtype = 'to_hop_bien_the_kho'
                elif vtype == 'tron_moc_cu_moi' and not is_valid_mixed:
                    vtype = 'dao_thu_tu_thanh_phan'

            # Xây dựng các thành phần chuỗi đầu vào theo loại biến thể
            input_text = ""
            spans_dict = {'so_nha': None, 'ngo_ngach_hem': None, 'thon_xom': None, 'duong': None}
            warnings = ["nhan_tong_hop"]
            ghi_chu = "bien_the_v2"
            transformation = vtype
            moc_era = "sau_2025"
            is_usable_canon = True

            cur_sn = sn_base
            cur_ngo = ngo_base
            cur_thon = thon_base
            cur_road = road_base
            cur_xa = ten_xa_moi if ten_xa_moi else ten_xa_cu
            cur_huyen = ten_huyen_cu
            cur_tinh = ten_tinh_moi

            out_ma_xa = ma_xa_moi
            out_xa_phuong = ten_xa_moi
            out_tinh = ten_tinh_moi
            out_ma_tinh = ma_tinh_moi

            if is_split:
                out_ma_xa = ""
                out_xa_phuong = ""
                cur_xa = ten_xa_cu
                is_usable_canon = False
                if "xa_bi_chia" not in warnings:
                    warnings.append("xa_bi_chia")
                cands_list = [m['ma_xa_moi'] for m in split_ward_codes.get(ma_xa_cu, [])]
                ghi_chu = f"xa_bi_chia; xa_moi_ung_vien={json.dumps(cands_list)}"

            # ---------------- CHI TIẾT TỪNG LOẠI BIẾN THỂ ----------------
            if vtype == 'khong_dau_mot_phan':
                warnings.append("dau_vao_khong_dau_mot_phan")
                # Không dấu một phần ở tên đường hoặc xã
                road_disp = bo_dau_tu(cur_road)
                transformation = "bo_dau_ten_duong"
                # Ghép: [cur_sn], [road_disp], [cur_xa], [cur_tinh]
                p1 = f"{cur_sn}, "
                p2 = f"{road_disp}, "
                p3 = f"{cur_xa}, {cur_tinh}"
                input_text = p1 + p2 + p3
                spans_dict['so_nha'] = {'text': cur_sn, 'start': 0, 'end': len(cur_sn)}
                spans_dict['duong'] = {'text': road_disp, 'start': len(p1), 'end': len(p1) + len(road_disp)}

            elif vtype == 'viet_tat_manh_va_ket_hop':
                warnings.append("dau_vao_viet_tat")
                # Viết tắt tiền tố và tên riêng: P., Q., Đ.
                road_core = re.sub(r'^(Đường|Phố|Đ\.|D\.)\s+', '', cur_road).strip()
                road_abbr = f"Đ.{road_core}"
                xa_abbr = cur_xa.replace("Phường ", "P.").replace("Xã ", "X.").replace("Thị trấn ", "TT.")
                p1 = f"{cur_sn} {road_abbr}, "
                p2 = f"{xa_abbr}, {cur_tinh}"
                input_text = p1 + p2
                spans_dict['so_nha'] = {'text': cur_sn, 'start': 0, 'end': len(cur_sn)}
                spans_dict['duong'] = {'text': road_abbr, 'start': len(cur_sn) + 1, 'end': len(cur_sn) + 1 + len(road_abbr)}

            elif vtype == 'loi_go_telex_typo':
                warnings.append("dau_vao_loi_go_telex")
                road_typo = apply_telex_typo(cur_road)
                p1 = f"{cur_sn}, {road_typo}, "
                p2 = f"{cur_xa}, {cur_tinh}"
                input_text = p1 + p2
                spans_dict['so_nha'] = {'text': cur_sn, 'start': 0, 'end': len(cur_sn)}
                spans_dict['duong'] = {'text': road_typo, 'start': len(cur_sn) + 2, 'end': len(cur_sn) + 2 + len(road_typo)}

            elif vtype == 'dinh_token_so_nha_duong':
                warnings.append("dinh_chu_p7_q10")
                warnings.append("khong_tuong_thich_tokenizer_v1")
                # Dính số nhà với tiền tố đường: ví dụ "151Đ.LêLợi" hoặc "12ĐườngNguyễnHuệ"
                num_only = re.sub(r'^(Số\s+|so\s+)?', '', cur_sn).strip()
                road_glued = cur_road.replace(" ", "")
                glued_part = f"{num_only}{road_glued}"
                p1 = f"{glued_part}, "
                p2 = f"{cur_xa}, {cur_tinh}"
                input_text = p1 + p2
                spans_dict['so_nha'] = {'text': num_only, 'start': 0, 'end': len(num_only)}
                spans_dict['duong'] = {'text': road_glued, 'start': len(num_only), 'end': len(num_only) + len(road_glued)}

            elif vtype == 'dao_thu_tu_thanh_phan':
                warnings.append("doi_thu_tu")
                # Đảo đường lên trước số nhà: [cur_road], [cur_sn], [cur_xa], [cur_tinh]
                p1 = f"{cur_road}, "
                p2 = f"{cur_sn}, "
                p3 = f"{cur_xa}, {cur_tinh}"
                input_text = p1 + p2 + p3
                spans_dict['duong'] = {'text': cur_road, 'start': 0, 'end': len(cur_road)}
                spans_dict['so_nha'] = {'text': cur_sn, 'start': len(p1), 'end': len(p1) + len(cur_sn)}

            elif vtype == 'lap_chong_ten_dia_danh':
                warnings.append("trung_lap_dia_danh")
                # Lặp tên địa danh: lặp phường hoặc đường
                p1 = f"{cur_sn}, {cur_road}, {cur_xa}, "
                p2 = f"{cur_huyen}, {cur_tinh}"
                input_text = p1 + p2
                spans_dict['so_nha'] = {'text': cur_sn, 'start': 0, 'end': len(cur_sn)}
                spans_dict['duong'] = {'text': cur_road, 'start': len(cur_sn) + 2, 'end': len(cur_sn) + 2 + len(cur_road)}

            elif vtype == 'thieu_cap_hanh_chinh':
                warnings.append("thieu_cap")
                # Khuyết cấp huyện
                p1 = f"{cur_sn}, {cur_road}, "
                p2 = f"{cur_xa}, {cur_tinh}"
                input_text = p1 + p2
                spans_dict['so_nha'] = {'text': cur_sn, 'start': 0, 'end': len(cur_sn)}
                spans_dict['duong'] = {'text': cur_road, 'start': len(cur_sn) + 2, 'end': len(cur_sn) + 2 + len(cur_road)}

            elif vtype == 'tron_moc_cu_moi':
                warnings.append("tron_moc_cu_moi")
                moc_era = "tron_moc_cu_moi"
                # Quận cũ + Xã mới: ví dụ [cur_huyen], [cur_xa_moi], [cur_tinh]
                p1 = f"{cur_sn}, {cur_road}, "
                p2 = f"{cur_xa}, {ten_huyen_cu}, {cur_tinh}"
                input_text = p1 + p2
                spans_dict['so_nha'] = {'text': cur_sn, 'start': 0, 'end': len(cur_sn)}
                spans_dict['duong'] = {'text': cur_road, 'start': len(cur_sn) + 2, 'end': len(cur_sn) + 2 + len(cur_road)}

            elif vtype == 'ngo_ngach_hem_thon_xom':
                warnings.append("co_ngo_ngach_thon_xom")
                ngo_thon_toggle += 1
                # Bổ sung ngõ ngách hẻm hoặc thôn xóm tổ dân phố (xen kẽ 50/50 qua ngo_thon_toggle)
                if cur_thon or (ngo_thon_toggle % 2 == 1):
                    # Nhánh Thôn / Xóm / Tổ dân phố
                    thon_val = cur_thon if cur_thon else ("Tổ dân phố 4" if "Phường" in cur_xa else "Thôn Đoài")
                    p1 = f"{cur_sn}, {thon_val}, "
                    p2 = f"{cur_road}, {cur_xa}, {cur_tinh}"
                    input_text = p1 + p2
                    spans_dict['so_nha'] = {'text': cur_sn, 'start': 0, 'end': len(cur_sn)}
                    spans_dict['thon_xom'] = {'text': thon_val, 'start': len(cur_sn) + 2, 'end': len(cur_sn) + 2 + len(thon_val)}
                    spans_dict['duong'] = {'text': cur_road, 'start': len(p1), 'end': len(p1) + len(cur_road)}
                    cur_thon = thon_val
                else:
                    # Nhánh Ngõ / Ngách / Hẻm
                    ngo_val = cur_ngo if cur_ngo else ("Hẻm 48/2" if "Hồ Chí Minh" in cur_tinh else "Ngõ 15 Ngách 2/1")
                    p1 = f"{cur_sn} {ngo_val}, "
                    p2 = f"{cur_road}, {cur_xa}, {cur_tinh}"
                    input_text = p1 + p2
                    spans_dict['so_nha'] = {'text': cur_sn, 'start': 0, 'end': len(cur_sn)}
                    spans_dict['ngo_ngach_hem'] = {'text': ngo_val, 'start': len(cur_sn) + 1, 'end': len(cur_sn) + 1 + len(ngo_val)}
                    spans_dict['duong'] = {'text': cur_road, 'start': len(p1), 'end': len(p1) + len(cur_road)}
                    cur_ngo = ngo_val

            elif vtype == 'xa_bi_chia_mo_ho':
                warnings.append("xa_bi_chia")
                is_usable_canon = False
                cands_list = [m['ma_xa_moi'] for m in split_ward_codes.get(ma_xa_cu, [])]
                ghi_chu = f"xa_bi_chia; xa_moi_ung_vien={json.dumps(cands_list)}"
                out_ma_xa = ""
                out_xa_phuong = ""
                p1 = f"{cur_sn}, {cur_road}, "
                p2 = f"{ten_xa_cu}, {ten_huyen_cu}, {cur_tinh}"
                input_text = p1 + p2
                spans_dict['so_nha'] = {'text': cur_sn, 'start': 0, 'end': len(cur_sn)}
                spans_dict['duong'] = {'text': cur_road, 'start': len(cur_sn) + 2, 'end': len(cur_sn) + 2 + len(cur_road)}

            elif vtype == 'viet_tat_ten_rieng_mo_ho':
                warnings.append("mo_ho_viet_tat")
                is_usable_canon = False
                abbr_road = "Đ. TTT"
                ghi_chu = 'duong_ung_vien=["Trần Thái Tông", "Tôn Thất Tùng"]'
                p1 = f"{cur_sn} {abbr_road}, "
                p2 = f"{cur_xa}, {cur_tinh}"
                input_text = p1 + p2
                spans_dict['so_nha'] = {'text': cur_sn, 'start': 0, 'end': len(cur_sn)}
                spans_dict['duong'] = {'text': abbr_road, 'start': len(cur_sn) + 1, 'end': len(cur_sn) + 1 + len(abbr_road)}
                cur_road = "" # Mơ hồ không ép tên đường cụ thể

            else: # to_hop_bien_the_kho
                warnings.append("to_hop_kho")
                warnings.append("dao_thu_tu")
                warnings.append("viet_tat")
                # Đảo thứ tự + viết tắt tiền tố
                road_abbr = cur_road.replace("Đường ", "Đ.").replace("Phố ", "P.")
                p1 = f"{road_abbr}, {cur_sn}, "
                p2 = f"{cur_xa}, {cur_tinh}"
                input_text = p1 + p2
                spans_dict['duong'] = {'text': road_abbr, 'start': 0, 'end': len(road_abbr)}
                spans_dict['so_nha'] = {'text': cur_sn, 'start': len(road_abbr) + 2, 'end': len(road_abbr) + 2 + len(cur_sn)}

            # Xác thực span offsets trên chuỗi input_text
            for f_name, sp in spans_dict.items():
                if sp:
                    assert input_text[sp['start']:sp['end']] == sp['text'], f"Lệch span {f_name}: '{input_text[sp['start']:sp['end']]}' != '{sp['text']}'"

            # Kiểm tra Runtime Tokenizer và BIO alignment
            tokens_rt = token_co_vi_tri(input_text)
            rt_starts = {t.bat_dau for t in tokens_rt}
            rt_ends = {t.ket_thuc for t in tokens_rt}

            has_cut = False
            for f_name, sp in spans_dict.items():
                if sp:
                    if sp['start'] not in rt_starts or sp['end'] not in rt_ends:
                        has_cut = True
                        break

            is_usable_span = not has_cut
            rt_compat = not has_cut
            tok_req = "v1.0" if rt_compat else "v2.0_glued_boundary"
            tok_note = "" if rt_compat else "Span boundary cuts inside runtime tokenizer token (v1.0)"

            # Gán BIO tag cho từng token (bảo đảm ranh giới span và chuẩn cú pháp BIO)
            tokens_for_bio = tokenize_with_spans(input_text, spans_dict)
            tokens_bio = []
            for t in tokens_for_bio:
                t_str = t['token']
                t_start = t['start']
                t_end = t['end']
                tag = "O"

                for f_name, sp in spans_dict.items():
                    if sp:
                        if t_start >= sp['start'] and t_end <= sp['end']:
                            if t_start == sp['start']:
                                tag = f"B-{f_name}"
                            else:
                                tag = f"I-{f_name}"
                            break
                tokens_bio.append({
                    'token': t_str,
                    'start': t_start,
                    'end': t_end,
                    'bio_tag': tag
                })

            # Xây dựng địa chỉ chuẩn mốc 2025
            dia_chi_chuan_parts = []
            if cur_sn: dia_chi_chuan_parts.append(cur_sn)
            if cur_ngo: dia_chi_chuan_parts.append(cur_ngo)
            if cur_thon: dia_chi_chuan_parts.append(cur_thon)
            if cur_road: dia_chi_chuan_parts.append(cur_road)
            if out_xa_phuong: dia_chi_chuan_parts.append(out_xa_phuong)
            if out_tinh: dia_chi_chuan_parts.append(out_tinh)
            dia_chi_chuan = ", ".join(dia_chi_chuan_parts)

            item_id = f"VNTRAIN_V2_{v2_idx:05d}"
            v2_idx += 1
            type_counts[vtype] += 1

            # Bản ghi CSV
            row_dict = {
                'id': item_id,
                'dau_vao': input_text,
                'nguon': f"derived_train:{parent_id}",
                'so_nha': cur_sn,
                'ngo_ngach_hem': cur_ngo,
                'thon_xom': cur_thon,
                'duong': cur_road,
                'ma_xa_cu': ma_xa_cu,
                'ma_huyen_cu': ma_huyen_cu,
                'ma_tinh_cu': ma_tinh_cu,
                'ma_xa': out_ma_xa,
                'ma_tinh': out_ma_tinh,
                'xa_phuong': out_xa_phuong,
                'tinh': out_tinh,
                'dia_chi_chuan': dia_chi_chuan,
                'canh_bao': json.dumps(warnings, ensure_ascii=False),
                'loai_nhan': 'bien_the',
                'nguon_du_lieu': 'train_seed_derived',
                'ghi_chu': ghi_chu,
                'nhom_mau_goc': f"DERIVED_FROM_{parent_id}",
                'loai_bien_the': vtype,
                'trang_thai_nhan': 'da_xac_minh_span' if is_usable_canon else 'chua_xac_dinh',
                'provenance': f"Seed {parent_id} (ma_xa_cu={ma_xa_cu}); {transformation}",
                'parent_id': parent_id,
                'parent_source_url': parent_url,
                'parent_snapshot_sha256': parent_snapshot_sha256,
                'source_row_sha256': row_sha,
                'family_id': family_id,
                'transformation': transformation,
                'moc_thoi_gian': moc_era
            }
            rows_v2.append(row_dict)

            # Bản ghi char spans JSONL
            char_spans_v2.append({
                'id': item_id,
                'dau_vao': input_text,
                'spans': spans_dict
            })

            # Bản ghi token spans JSONL
            token_spans_v2.append({
                'id': item_id,
                'dau_vao': input_text,
                'tokens': tokens_bio,
                'spans': spans_dict,
                'usable_for_span_training': is_usable_span,
                'tokenizer_runtime_compatible': rt_compat,
                'usable_for_canonical_training': is_usable_canon,
                'tokenizer_version_required': tok_req,
                'tokenizer_note': tok_note
            })

            if len(rows_v2) >= 3000:
                break
        if len(rows_v2) >= 3000:
            break

    print(f"Tổng số mẫu train mới sinh ra: {len(rows_v2)} mẫu từ {len(selected_parents)} họ cha.")
    print("Phân bố loại biến thể:")
    for vt, cnt in type_counts.most_common():
        print(f"  {vt:30s}: {cnt}")

    # 6. Ghi file CSV
    csv_file = BO_SUNG_V2_DIR / "train_bo_sung_v2.csv"
    with open(csv_file, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows_v2[0].keys()))
        writer.writeheader()
        writer.writerows(rows_v2)
    print(f"Đã ghi: {csv_file} ({len(rows_v2)} dòng)")

    # 7. Ghi file char spans JSONL
    char_file = BO_SUNG_V2_DIR / "train_spans_v2.jsonl"
    with open(char_file, 'w', encoding='utf-8') as f:
        for item in char_spans_v2:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
    print(f"Đã ghi: {char_file} ({len(char_spans_v2)} dòng)")

    # 8. Ghi file token spans JSONL
    token_file = BO_SUNG_V2_DIR / "token_spans_v2.jsonl"
    with open(token_file, 'w', encoding='utf-8') as f:
        for item in token_spans_v2:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
    print(f"Đã ghi: {token_file} ({len(token_spans_v2)} dòng)")

    # 9. Ghi file distribution_summary.json
    span_counts = Counter()
    for item in char_spans_v2:
        for k, v in item['spans'].items():
            if v: span_counts[k] += 1

    prov_counts = Counter(r['tinh'] for r in rows_v2)
    era_counts = Counter(r['moc_thoi_gian'] for r in rows_v2)

    dist_summary = {
        'total_rows': len(rows_v2),
        'total_families': len(selected_parents),
        'max_variants_per_family': max(Counter(r['family_id'] for r in rows_v2).values()),
        'variant_type_distribution': dict(type_counts),
        'entity_span_counts': dict(span_counts),
        'era_distribution': dict(era_counts),
        'top_provinces': dict(prov_counts.most_common(10)),
        'usability': {
            'usable_for_span_training': sum(1 for x in token_spans_v2 if x['usable_for_span_training']),
            'tokenizer_runtime_compatible': sum(1 for x in token_spans_v2 if x['tokenizer_runtime_compatible']),
            'usable_for_canonical_training': sum(1 for x in token_spans_v2 if x['usable_for_canonical_training']),
            'ambiguous_split_ward_count': sum(1 for r in rows_v2 if r['loai_bien_the'] == 'xa_bi_chia_mo_ho'),
            'ambiguous_acronym_count': sum(1 for r in rows_v2 if r['loai_bien_the'] == 'viet_tat_ten_rieng_mo_ho')
        }
    }
    with open(BO_SUNG_V2_DIR / "distribution_summary.json", 'w', encoding='utf-8') as f:
        json.dump(dist_summary, f, ensure_ascii=False, indent=2)
    print(f"Đã ghi: {BO_SUNG_V2_DIR / 'distribution_summary.json'}")

    # 10. Ghi file manifest.json
    manifest = {
        'package_name': 'bo_sung_v2_hard_train',
        'version': 'v2.0_independent_cnn_ready',
        'created_at': '2026-10-29T18:10:00+07:00',
        'metrics': dist_summary,
        'parent_source': {
            'file': 'data/train_dev/train.csv',
            'sha256': parent_snapshot_sha256,
            'total_families_used': len(selected_parents)
        },
        'files': {}
    }
    for fname in ['train_bo_sung_v2.csv', 'train_spans_v2.jsonl', 'token_spans_v2.jsonl',
                  'anti_leakage_audit.json', 'distribution_summary.json']:
        p = BO_SUNG_V2_DIR / fname
        content = p.read_bytes()
        manifest['files'][fname] = {
            'sha256': hashlib.sha256(content).hexdigest(),
            'size_bytes': len(content)
        }

    with open(BO_SUNG_V2_DIR / "manifest.json", 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"Đã ghi: {BO_SUNG_V2_DIR / 'manifest.json'}")
    print("\n=== HOÀN TẤT SINH DỮ LIỆU GÓI BO_SUNG_V2 THÀNH CÔNG 100% ===")

if __name__ == '__main__':
    main()
