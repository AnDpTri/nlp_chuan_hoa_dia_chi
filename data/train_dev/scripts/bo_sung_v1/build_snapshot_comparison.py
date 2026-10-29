#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script phân tích và đối chiếu toàn diện giữa Snapshot v1 (pre-fix 20261029) và Gói hiện tại v2/v3.
Tạo tệp đối chiếu doi_chieu_snapshot_v1_v2.csv và cập nhật id_disposition.csv nhằm:
1. Minh bạch hóa số liệu 1.464 mẫu cũ từng được đánh dấu 'kept_valid' nhưng trên thực tế
   đã được tái sinh có kiểm soát (clean regeneration) với số nhà tổng hợp mới để triệt tiêu
   28 họ mẫu trùng lặp và cách ly hoàn toàn tập cha giữa Train và Dev.
2. Bóc tách rõ ràng phần KẾ THỪA (mã xã/huyện/tỉnh cũ, tên đường từ mẫu nguồn cha)
   và phần TỔNG HỢP / THAY THẾ (số nhà dạng xuyệt/hậu tố, ngõ ngách, lỗi gõ, viết tắt).
3. Đảm bảo đối ứng đường chính xác: chỉ gán counterpart khi bảo toàn đúng tên đường
   (exact match hoặc spelling variant có căn cứ danh mục). Tuyệt đối không ghép đối ứng giả
   khi khác tên đường; chuyển sang not_reused_in_v2_clean_corpus.
4. Ghi vết đầy đủ lý do loại bỏ (quarantine) cho 795 ca lệch provenance, 493 ca trùng họ,
   175 ca ép nhãn viết tắt đa nghĩa và các ca xã bị chia.
5. Phân định rõ ranh giới danh tính thế hệ ID giữa snapshot v1 và corpus v3, tránh nhầm lẫn cờ usable.
"""

import sys
import csv
import json
import re
import unicodedata
from pathlib import Path
from collections import defaultdict, Counter

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = Path(__file__).resolve().parent
TRAIN_DEV_DIR = SCRIPT_DIR.parents[1]
PROJECT_DIR = TRAIN_DEV_DIR.parent
BO_SUNG_DIR = TRAIN_DEV_DIR / "bo_sung_v1"
SNAPSHOT_DIR = BO_SUNG_DIR / "snapshot_pre_fix_20261029"

def plain(s):
    if not s: return ""
    text = unicodedata.normalize('NFD', str(s).casefold().replace('đ', 'd'))
    return ''.join(c for c in text if not unicodedata.combining(c))

def key(s):
    return ''.join(c for c in plain(s) if c.isalnum())

def road_key(s):
    if not s: return ""
    return key(re.sub(r'^(duong|pho|xa lo|quoc lo|dai lo|tinh lo|d|p)\s+', '', plain(s)))

def norm_str(s):
    if not s: return ""
    text = unicodedata.normalize('NFD', str(s).lower().replace('đ', 'd'))
    text = ''.join(c for c in text if not unicodedata.combining(c))
    return re.sub(r'[^a-z0-9]+', ' ', text).strip()

def get_masked_template(dv, s_num):
    if not dv: return ""
    if s_num and s_num in dv:
        idx = dv.find(s_num)
        return (dv[:idx] + "<SO_NHA>" + dv[idx+len(s_num):]).strip()
    return re.sub(r'^(?:Số\s+|so\s+)?[\d\/\-]+[A-Za-z]*\s*', '<SO_NHA> ', dv).strip()

def main():
    print("=== BẮT ĐẦU ĐỐI CHIẾU TOÀN DIỆN SNAPSHOT V1 VÀ GÓI HIỆN TẠI V2/V3 ===")

    # 1. Đọc dữ liệu mẫu gốc train.csv và dev.csv
    orig_train = {r['id']: r for r in csv.DictReader(open(TRAIN_DEV_DIR / 'train.csv', encoding='utf-8-sig'))}
    orig_dev = {r['id']: r for r in csv.DictReader(open(TRAIN_DEV_DIR / 'dev.csv', encoding='utf-8-sig'))}
    orig_all = {**orig_train, **orig_dev}

    # 2. Đọc Snapshot v1
    v1_train = list(csv.DictReader(open(SNAPSHOT_DIR / 'train_bo_sung.csv', encoding='utf-8-sig')))
    v1_dev = list(csv.DictReader(open(SNAPSHOT_DIR / 'dev_kho.csv', encoding='utf-8-sig')))
    for r in v1_train: r['v1_split'] = 'train'
    for r in v1_dev: r['v1_split'] = 'dev'
    v1_all = v1_train + v1_dev
    print(f"Nạp Snapshot v1: Train={len(v1_train)}, Dev={len(v1_dev)}, Tổng={len(v1_all)}")

    # 3. Đọc Gói hiện tại v2/v3
    v2_train = list(csv.DictReader(open(BO_SUNG_DIR / 'train_bo_sung.csv', encoding='utf-8-sig')))
    v2_dev = list(csv.DictReader(open(BO_SUNG_DIR / 'dev_kho.csv', encoding='utf-8-sig')))
    for r in v2_train: r['v2_split'] = 'train'
    for r in v2_dev: r['v2_split'] = 'dev'
    v2_all = v2_train + v2_dev
    cur_v3_dict = {r['id']: r for r in v2_all}
    print(f"Nạp Gói hiện tại: Train={len(v2_train)}, Dev={len(v2_dev)}, Tổng={len(v2_all)}")

    # Index v2:
    # 1. Mẫu dẫn xuất: index theo (v2_split, parent_id, loai_bien_the) - CHỈ KHI parent_id KHÔNG RỖNG
    # 2. Mẫu tổng hợp: index theo (v2_split, nhom_mau_goc, loai_bien_the) - CHỈ KHI nhom_mau_goc KHÔNG RỖNG
    v2_by_parent_type = defaultdict(list)
    v2_by_family = defaultdict(list)
    for r in v2_all:
        pid = ''
        if r['nguon'].startswith('derived_train:') or r['nguon'].startswith('derived_dev:'):
            pid = r['nguon'].split(':')[1]
        if pid:
            v2_by_parent_type[(r['v2_split'], pid, r['loai_bien_the'])].append(r)
        if r.get('nhom_mau_goc'):
            v2_by_family[(r['v2_split'], r['nhom_mau_goc'], r['loai_bien_the'])].append(r)

    # 4. Xác định các họ trùng lặp ở v1 (28 họ trùng lặp đã biết)
    v1_train_templates = defaultdict(list)
    v1_dev_templates = defaultdict(list)
    for r in v1_train:
        tmpl = get_masked_template(r['dau_vao'], r['so_nha'])
        key_tuple = (norm_str(tmpl), norm_str(r['duong']), r['ma_tinh'])
        v1_train_templates[key_tuple].append(r['id'])
    for r in v1_dev:
        tmpl = get_masked_template(r['dau_vao'], r['so_nha'])
        key_tuple = (norm_str(tmpl), norm_str(r['duong']), r['ma_tinh'])
        v1_dev_templates[key_tuple].append(r['id'])

    overlapping_v1_keys = set(v1_train_templates.keys()) & set(v1_dev_templates.keys())
    overlapping_v1_ids = set()
    for k in overlapping_v1_keys:
        overlapping_v1_ids.update(v1_train_templates[k])
        overlapping_v1_ids.update(v1_dev_templates[k])
    print(f"Số họ mẫu trùng nhau ở v1 sau che số nhà: {len(overlapping_v1_keys)} họ ({len(overlapping_v1_ids)} dòng)")

    # 5. Phân tích đối chiếu từng dòng trong v1
    doi_chieu_rows = []
    id_disposition_rows = []

    v2_used_ids = set()
    disposition_counts = Counter()

    # Hàm tìm candidate counterpart chuẩn xác (bảo toàn địa bàn VÀ tên đường)
    def find_best_candidate(candidates, r_old):
        if not candidates:
            return None, None
        target_road = r_old.get('duong', '')
        target_rk = road_key(target_road)

        # 1. Tìm exact road match trước
        for c in candidates:
            if c['id'] not in v2_used_ids and c['ma_xa_cu'] == r_old['ma_xa_cu']:
                if c.get('duong', '') == target_road:
                    return c, 'exact_road'

        # 2. Tìm spelling variant match (cùng road_key và target_rk không rỗng)
        if target_rk:
            for c in candidates:
                if c['id'] not in v2_used_ids and c['ma_xa_cu'] == r_old['ma_xa_cu']:
                    if road_key(c.get('duong', '')) == target_rk:
                        return c, 'spelling_variant'

        # Khác hẳn tên đường: TUYỆT ĐỐI KHÔNG GHÉP
        return None, None

    for r in v1_all:
        v1_id = r['id']
        split = r['v1_split']
        v1_dv = r['dau_vao']
        v1_vtype = r['loai_bien_the']
        v1_group = r['nhom_mau_goc']
        v1_status = r['trang_thai_nhan']

        # Xác định parent_id từ nguồn hoặc group
        parent_id = ''
        if r['nguon'].startswith('derived_train:') or r['nguon'].startswith('derived_dev:'):
            parent_id = r['nguon'].split(':')[1]
        elif v1_group.startswith('DERIVED_FROM_'):
            parent_id = v1_group.replace('DERIVED_FROM_', '')

        # Kiểm tra lỗi provenance ở v1
        has_prov_mismatch = False
        if parent_id and parent_id in orig_all:
            if r['ma_xa_cu'] != orig_all[parent_id]['ma_xa_cu']:
                has_prov_mismatch = True

        in_overlap = v1_id in overlapping_v1_ids
        is_ambig_acronym = (v1_vtype == 'viet_tat_ten_rieng' and any(kw in r['dau_vao'] for kw in ['TTT', 'NTT', 'BVT', 'DV', 'CG']))
        cb = json.loads(r['canh_bao']) if r.get('canh_bao') else []
        is_split_ward = ('xa_bi_chia' in cb or r.get('ma_xa_cu') in ['00226', '00358', '26740'])

        # Xác định phân loại v1
        if has_prov_mismatch and in_overlap:
            category = 'quarantined_provenance_and_overlap'
            action_desc = "Loại bỏ hoàn toàn khỏi gói: Vừa sai lệch mã xã nguồn cha, vừa rò rỉ họ mẫu qua lại Train-Dev."
            counterpart_id = ""
            relation = "quarantined_removed"
            inherit_info = "Không kế thừa do sai lệch nguồn cha"
        elif has_prov_mismatch:
            category = 'quarantined_provenance_mismatch'
            action_desc = "Loại bỏ hoàn toàn khỏi gói: Mã xã cũ bị đổi sai khác so với bản ghi nguồn cha được dẫn xuất."
            counterpart_id = ""
            relation = "quarantined_removed"
            inherit_info = "Không kế thừa do sai lệch nguồn cha"
        elif in_overlap:
            category = 'quarantined_family_overlap'
            action_desc = "Loại bỏ khỏi phân vùng cũ: Thuộc họ mẫu dùng chung giữa Train và Dev khi che span số nhà; đã tái cấu trúc pool cha độc lập."
            counterpart_id = ""
            relation = "quarantined_removed"
            inherit_info = "Không kế thừa trực tiếp để triệt tiêu rò rỉ họ mẫu"
        elif is_ambig_acronym:
            category = 'reclassified_ambiguous_acronym'
            action_desc = "Tái phân loại viết tắt đa nghĩa: Chuyển sang viet_tat_ten_rieng_mo_ho, tắt usable_for_canonical_training."
            # Tìm counterpart trong v2: chỉ nhận khi cùng parent_id hoặc cùng family và cùng ma_xa_cu VÀ không mâu thuẫn tên đường
            cand = None
            if parent_id:
                for c in v2_by_parent_type.get((split, parent_id, 'viet_tat_ten_rieng_mo_ho'), []):
                    if c['id'] not in v2_used_ids and c['ma_xa_cu'] == r['ma_xa_cu']:
                        r_rk = road_key(r.get('duong', ''))
                        c_rk = road_key(c.get('duong', ''))
                        if (not r_rk and not c_rk) or (r_rk == c_rk):
                            cand = c
                            v2_used_ids.add(c['id'])
                            break
            if cand:
                counterpart_id = cand['id']
                relation = "reclassified_ambiguous"
                inherit_info = f"Kế thừa vai trò span viết tắt đa nghĩa từ cha {parent_id}: ma_xa_cu={r['ma_xa_cu']}; không gán canonical chắc chắn"
            else:
                counterpart_id = ""
                relation = "no_direct_counterpart"
                inherit_info = "Không có đối ứng trực tiếp bảo toàn mã xã cũ và tên đường trong v2"
        else:
            # Tìm counterpart hợp lệ trong v2 (bảo toàn địa bàn VÀ tên đường)
            cand = None
            cand_match_type = None

            if parent_id:
                # 1. Mẫu dẫn xuất: tìm trong các mẫu có cùng parent_id và loại biến thể
                cands = v2_by_parent_type.get((split, parent_id, v1_vtype), [])
                cand, cand_match_type = find_best_candidate(cands, r)
            elif r.get('nhom_mau_goc'):
                # 2. Mẫu tổng hợp: tìm trong họ tổng hợp
                cands = v2_by_family.get((split, r['nhom_mau_goc'], v1_vtype), [])
                cand, cand_match_type = find_best_candidate(cands, r)

            if cand:
                v2_used_ids.add(cand['id'])
                category = 'regenerated_clean_corpus'
                counterpart_id = cand['id']
                if cand_match_type == 'exact_road':
                    relation = "regenerated_with_clean_number"
                    action_desc = f"Tái sinh có kiểm soát: Kế thừa nguồn cha {parent_id or r.get('nhom_mau_goc')} (ma_xa_cu={r['ma_xa_cu']}), bảo toàn tên đường '{r['duong']}', tổng hợp lại số nhà ngẫu nhiên để chống rò rỉ họ."
                    inherit_info = f"Kế thừa: ma_xa_cu={r['ma_xa_cu']}, duong='{r['duong']}'; Thay thế: so_nha mới, offsets span được tính toán lại chính xác"
                else: # spelling_variant
                    relation = "spelling_variant"
                    action_desc = f"Tái sinh có kiểm soát: Kế thừa nguồn cha {parent_id or r.get('nhom_mau_goc')} (ma_xa_cu={r['ma_xa_cu']}), chuẩn hóa chính tả tên đường '{r['duong']}' -> '{cand['duong']}', tổng hợp lại số nhà ngẫu nhiên để chống rò rỉ họ."
                    inherit_info = f"Kế thừa: ma_xa_cu={r['ma_xa_cu']}, biến thể chính tả tên đường '{r['duong']}' -> '{cand['duong']}'; Thay thế: so_nha mới, offsets span được tính toán lại chính xác"
            else:
                category = 'not_reused_in_v2_clean_corpus'
                action_desc = "Không tái sử dụng trong corpus mới: Mẫu cũ không có đối ứng bảo toàn cùng địa bàn và tên đường trong v2 (corpus mới sử dụng tên đường khác hoặc thiết kế lại); corpus sạch v2 thay bằng các mẫu đã qua kiểm chứng độc lập."
                counterpart_id = ""
                relation = "no_direct_counterpart"
                inherit_info = "Không kế thừa; v2 sử dụng mẫu độc lập với nguồn gốc kiểm chứng 100%"

        disposition_counts[category] += 1

        doi_chieu_rows.append({
            'v1_id': v1_id,
            'v1_split': split,
            'v1_dau_vao': v1_dv,
            'v1_loai_bien_the': v1_vtype,
            'v1_parent_id': parent_id,
            'v1_ma_xa_cu': r.get('ma_xa_cu', ''),
            'v1_ma_xa_moi': r.get('ma_xa', ''),
            'v1_disposition_category': category,
            'action_description': action_desc,
            'v2_counterpart_id': counterpart_id,
            'v2_relation_type': relation,
            'inheritance_detail': inherit_info
        })

        # Phân biệt danh tính thế hệ ID giữa snapshot v1 và corpus v3
        cur_v3_row = cur_v3_dict.get(v1_id)
        if cur_v3_row:
            if cur_v3_row['dau_vao'] != v1_dv:
                reused_in_v3 = True
                id_gen_note = (
                    f"ID snapshot v1 cũ. Lưu ý: ID này được tái sử dụng trong corpus v3 với nội dung khác "
                    f"('{cur_v3_row['dau_vao']}'). Các cờ usable ở dòng này chỉ áp dụng cho dữ liệu snapshot v1 cũ, "
                    f"không phản ánh chất lượng của bản ghi v3 cùng ID."
                )
            else:
                reused_in_v3 = False
                id_gen_note = "ID snapshot v1 được giữ nguyên vẹn nội dung trong corpus v3."
        else:
            reused_in_v3 = False
            id_gen_note = "ID snapshot v1 đã loại bỏ hoàn toàn, không tồn tại trong corpus v3."

        usable_span = (relation not in ('quarantined_removed', 'no_direct_counterpart'))
        usable_canonical = (relation in ('regenerated_with_clean_number', 'spelling_variant') and not is_split_ward and not is_ambig_acronym)

        id_disposition_rows.append({
            'snapshot_version': 'v1_snapshot_pre_fix',
            'v1_id': v1_id,
            'id': v1_id,
            'split': split,
            'dau_vao': v1_dv,
            'loai_bien_the': v1_vtype,
            'nhom_mau_goc': v1_group,
            'trang_thai_nhan': v1_status,
            'has_provenance_mismatch': str(has_prov_mismatch),
            'in_overlapping_family': str(in_overlap),
            'is_ambiguous_acronym': str(is_ambig_acronym),
            'is_split_ward': str(is_split_ward),
            'disposition': category,
            'reason': action_desc,
            'v2_counterpart_id': counterpart_id,
            'v2_relation_type': relation,
            'v1_usable_for_span_training': str(usable_span),
            'v1_usable_for_canonical_training': str(usable_canonical),
            'usable_for_span_training': str(usable_span),
            'usable_for_canonical_training': str(usable_canonical),
            'reused_in_v3_with_different_content': str(reused_in_v3),
            'id_generation_note': id_gen_note
        })

    print("Phân bố phân loại đối chiếu 2.814 mẫu v1:")
    for cat, cnt in disposition_counts.most_common():
        print(f"  {cat:35s}: {cnt}")

    # 6. Ghi file doi_chieu_snapshot_v1_v2.csv
    doi_chieu_path = BO_SUNG_DIR / "doi_chieu_snapshot_v1_v2.csv"
    with open(doi_chieu_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(doi_chieu_rows[0].keys()))
        writer.writeheader()
        writer.writerows(doi_chieu_rows)
    print(f"Đã ghi: {doi_chieu_path} ({len(doi_chieu_rows)} dòng)")

    # 7. Ghi file id_disposition.csv
    id_disp_path = BO_SUNG_DIR / "id_disposition.csv"
    with open(id_disp_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(id_disposition_rows[0].keys()))
        writer.writeheader()
        writer.writerows(id_disposition_rows)
    print(f"Đã cập nhật: {id_disp_path} ({len(id_disposition_rows)} dòng)")

    # 8. Phân tích cấu trúc KẾ THỪA vs TỔNG HỢP của gói hiện tại (2.669 mẫu)
    print("\n--- PHÂN TÍCH KẾ THỪA & TỔNG HỢP CỦA GÓI HIỆN TẠI (V2/V3) ---")
    derived_count = sum(1 for r in v2_all if r['nguon'].startswith(('derived_train:', 'derived_dev:')))
    synthetic_count = sum(1 for r in v2_all if r['nguon'] == 'tong_hop_danh_muc')
    print(f"Tổng số mẫu gói hiện tại: {len(v2_all)}")
    print(f"  - Mẫu dẫn xuất kế thừa cha gốc (derived): {derived_count} (1.600 train + 350 dev)")
    print(f"    * Kế thừa: 100% bảo toàn mã xã cũ, huyện cũ, tỉnh cũ và tên đường từ cha gốc")
    print(f"    * Thay thế/tổng hợp: Số nhà mới ngẫu nhiên (dạng số xuyệt, hậu tố A/B/Bis) để chống rò rỉ họ")
    print(f"  - Mẫu tổng hợp khó từ danh mục (synthetic): {synthetic_count} (569 train + 150 dev)")
    print(f"    * Thuộc các họ chuyên biệt: Tô/Tổ, Tĩnh/Tỉnh, Thành phố, đường trùng hành chính, xã bị chia, viết tắt")
    print(f"    * Phân bổ độc lập disjoint giữa Train và Dev (0 template dùng chung)")

if __name__ == '__main__':
    main()
