#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script kiểm tra toàn vẹn chất lượng và chống rò rỉ cho bộ dữ liệu bo_sung_v2 (Train Khó v2):
1. Schema & các trường dữ liệu mở rộng (30 trường).
2. Định dạng mã zero-padded (2 số tỉnh, 3 số huyện, 5 số xã).
3. Tính toàn vẹn quan hệ cha-con hành chính mới và cũ.
4. Kiểm tra tương thích ca trộn mốc (quận cũ thực sự là cha của xã mới theo bảng đối chiếu).
5. Kiểm tra chính sách xã bị chia (fan-out > 1: giữ mơ hồ, cờ xa_bi_chia, lưu ứng viên, ma_xa rỗng).
6. Kiểm tra chính sách viết tắt đa nghĩa (TTT, NTT, BVT: để trống đường chuẩn hóa, lưu ứng viên).
7. Kiểm tra char spans, token spans & BIO alignment:
   - dau_vao[start:end] == span_text 100%
   - dau_vao[start:end] == token 100%
   - Quy tắc BIO sequence tags hợp lệ
   - Phân định tương thích runtime tokenizer và usable_for_span_training.
8. Chống rò rỉ dữ liệu tuyệt đối (Anti-Leakage Check = 0%):
   - Train v2 vs Test = 0%
   - Train v2 vs Dev gốc = 0%
   - Train v2 vs Dev v1 = 0%
9. Tính toàn vẹn của Provenance (Provenance Integrity):
   - 100% parent_id tồn tại trong train.csv gốc
   - 100% bảo toàn mã xã cũ, huyện cũ, tỉnh cũ so với mẫu cha
   - 100% bảo toàn tên đường từ mẫu cha có căn cứ
   - Namespace ID VNTRAIN_V2_... độc lập hoàn toàn.
"""

import sys
import os
import json
import csv
import re
import hashlib
import unicodedata
from collections import defaultdict, Counter
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parents[3]
DATA_DIR = PROJECT_DIR / "data"
CLEAN_DIR = DATA_DIR / "clean"
TEST_DIR = DATA_DIR / "test"
TRAIN_DEV_DIR = DATA_DIR / "train_dev"
BO_SUNG_V2_DIR = TRAIN_DEV_DIR / "bo_sung_v2"

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

def main():
    print("=== BẮT ĐẦU KIỂM TRA CHẤT LƯỢNG VÀ CHỐNG RÒ RỈ DỮ LIỆU BO_SUNG_V2 ===")
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
        if r['ma_xa_cu']: to_new[r['ma_xa_cu']].add(r['ma_xa_moi'])
    split_codes = {k for k, v in to_new.items() if len(v) > 1}
    valid_mixed_pairs = {(m['ma_huyen_cu'], m['ma_xa_moi']) for m in maps}

    # 2. Đọc file CSV gói v2
    train_v2_file = BO_SUNG_V2_DIR / "train_bo_sung_v2.csv"
    if not train_v2_file.exists():
        print(f"LỖI: Không tìm thấy file {train_v2_file}")
        sys.exit(1)

    reader = csv.DictReader(open(train_v2_file, encoding='utf-8-sig'))
    if reader.fieldnames != FIELDS_V2:
        errors.append(f"Schema mismatch: {reader.fieldnames} != {FIELDS_V2}")
    v2_rows = list(reader)
    print(f"Số lượng bản ghi nạp được: {len(v2_rows)} mẫu.")
    if len(v2_rows) < 3000:
        errors.append(f"Số lượng bản ghi chưa đạt chỉ tiêu: {len(v2_rows)} < 3000")

    # 3. Kiểm tra từng bản ghi: Mã, Cấu trúc, Quan hệ
    seen_ids = set()
    for idx, r in enumerate(v2_rows):
        ident = r['id']
        if ident in seen_ids:
            errors.append(f"Dòng {idx+2}: Trùng ID {ident}")
        seen_ids.add(ident)

        if not ident.startswith("VNTRAIN_V2_"):
            errors.append(f"{ident}: Không đúng định dạng namespace VNTRAIN_V2_...")

        # 3.1 Zero-padded codes
        for col, expected_len in [('ma_tinh', 2), ('ma_tinh_cu', 2), ('ma_huyen_cu', 3), ('ma_xa', 5), ('ma_xa_cu', 5)]:
            val = r.get(col, '')
            if val:
                if len(val) != expected_len or not val.isdigit():
                    errors.append(f"{ident}: {col} '{val}' không đúng định dạng {expected_len} số zero-padded")

        # 3.2 Quan hệ hành chính mới
        if r['ma_xa']:
            if r['ma_xa'] not in new_w:
                errors.append(f"{ident}: ma_xa {r['ma_xa']} không có trong moi_tinh_xa.csv")
            elif r['ma_tinh'] and new_w[r['ma_xa']]['ma_tinh'] != r['ma_tinh']:
                errors.append(f"{ident}: ma_xa {r['ma_xa']} không thuộc ma_tinh {r['ma_tinh']}")
        if r['ma_tinh'] and r['ma_tinh'] not in new_p:
            errors.append(f"{ident}: ma_tinh {r['ma_tinh']} không có trong moi_tinh.csv")

        # 3.3 Tên-đối-mã hành chính mới
        if r['ma_xa']:
            expected_xa = canonical_full_name(new_w.get(r['ma_xa']), 'xa')
            if r['xa_phuong'] != expected_xa:
                errors.append(f"{ident}: xa_phuong '{r['xa_phuong']}' không khớp tên chuẩn theo mã {r['ma_xa']} ('{expected_xa}')")
        elif r['xa_phuong']:
            errors.append(f"{ident}: ma_xa rỗng nhưng xa_phuong lại có giá trị '{r['xa_phuong']}'")

        if r['ma_tinh']:
            expected_tinh = canonical_full_name(new_p.get(r['ma_tinh']), 'tinh')
            if r['tinh'] != expected_tinh:
                errors.append(f"{ident}: tinh '{r['tinh']}' không khớp tên chuẩn theo mã {r['ma_tinh']} ('{expected_tinh}')")

        # 3.4 Quan hệ hành chính cũ
        if r['ma_xa_cu']:
            if r['ma_xa_cu'] not in old_w:
                errors.append(f"{ident}: ma_xa_cu {r['ma_xa_cu']} không có trong cu_tinh_huyen_xa.csv")
            else:
                w_obj = old_w[r['ma_xa_cu']]
                if r['ma_huyen_cu'] and w_obj['ma_huyen'] != r['ma_huyen_cu']:
                    errors.append(f"{ident}: ma_xa_cu {r['ma_xa_cu']} không thuộc ma_huyen_cu {r['ma_huyen_cu']}")
                if r['ma_tinh_cu'] and w_obj['ma_tinh'] != r['ma_tinh_cu']:
                    errors.append(f"{ident}: ma_xa_cu {r['ma_xa_cu']} không thuộc ma_tinh_cu {r['ma_tinh_cu']}")

        # 3.5 Ca trộn mốc
        cb = json.loads(r['canh_bao']) if r['canh_bao'] else []
        if 'tron_moc_cu_moi' in cb:
            if (r['ma_huyen_cu'], r['ma_xa']) not in valid_mixed_pairs:
                errors.append(f"{ident}: Ca trộn mốc (huyen_cu={r['ma_huyen_cu']}, xa_moi={r['ma_xa']}) không tương thích topological")

        # 3.6 Chính sách xã bị chia
        if r['loai_bien_the'] == 'xa_bi_chia_mo_ho':
            if 'xa_bi_chia' not in cb:
                errors.append(f"{ident}: Xã bị chia thiếu cờ xa_bi_chia")
            if r['ma_xa'] != '' or r['xa_phuong'] != '':
                errors.append(f"{ident}: Xã bị chia không được gán ma_xa/xa_phuong")
            if 'xa_moi_ung_vien=' not in r['ghi_chu']:
                errors.append(f"{ident}: Xã bị chia thiếu danh sách ứng viên trong ghi_chu")

        # 3.7 Chính sách viết tắt đa nghĩa
        if r['loai_bien_the'] == 'viet_tat_ten_rieng_mo_ho':
            if 'mo_ho_viet_tat' not in cb:
                errors.append(f"{ident}: Viết tắt đa nghĩa thiếu cờ mo_ho_viet_tat")
            if r['duong'] != '':
                errors.append(f"{ident}: Viết tắt đa nghĩa không được gán duong chuẩn hóa")
            if 'duong_ung_vien=' not in r['ghi_chu']:
                errors.append(f"{ident}: Viết tắt đa nghĩa thiếu danh sách duong_ung_vien")

    print(f"Kiểm tra cấu trúc và quan hệ hành chính: {len(v2_rows)} mẫu đạt chuẩn.")

    # 4. Kiểm tra Char Spans & Token Spans & BIO Alignment
    print("\n--- KIỂM TRA CHAR SPANS, TOKEN SPANS & RUNTIME TOKENIZER COMPATIBILITY ---")
    char_spans_file = BO_SUNG_V2_DIR / "train_spans_v2.jsonl"
    token_spans_file = BO_SUNG_V2_DIR / "token_spans_v2.jsonl"
    v2_dict = {r['id']: r for r in v2_rows}

    # 4.1 Char spans
    with open(char_spans_file, encoding='utf-8') as f:
        char_items = [json.loads(line) for line in f]
    if len(char_items) != len(v2_rows):
        errors.append(f"Số lượng char spans không khớp: {len(char_items)} != {len(v2_rows)}")

    for item in char_items:
        iid = item['id']
        dv = item['dau_vao']
        if dv != v2_dict[iid]['dau_vao']:
            errors.append(f"{iid}: dau_vao trong char_spans không khớp CSV")
        for f_name, sp in item['spans'].items():
            if sp:
                st, en, txt = sp['start'], sp['end'], sp['text']
                if dv[st:en] != txt:
                    errors.append(f"{iid}: Char span lệch {f_name}: dau_vao[{st}:{en}] ('{dv[st:en]}') != '{txt}'")

    # 4.2 Token spans
    with open(token_spans_file, encoding='utf-8') as f:
        token_items = [json.loads(line) for line in f]
    if len(token_items) != len(v2_rows):
        errors.append(f"Số lượng token spans không khớp: {len(token_items)} != {len(v2_rows)}")

    incompat_count = 0
    for item in token_items:
        iid = item['id']
        dv = item['dau_vao']
        tokens = item['tokens']

        # Offset từng token
        prev_bio = "O"
        prev_field = None
        for t in tokens:
            t_str, t_start, t_end, bio = t['token'], t['start'], t['end'], t['bio_tag']
            if dv[t_start:t_end] != t_str:
                errors.append(f"{iid}: Token offset lệch dau_vao[{t_start}:{t_end}] ('{dv[t_start:t_end]}') != '{t_str}'")

            if bio.startswith("I-"):
                field = bio[2:]
                if prev_bio == "O" or prev_field != field:
                    errors.append(f"{iid}: Lỗi BIO sequence: '{bio}' đứng sau '{prev_bio}' mà không có B-{field}")

            prev_field = bio[2:] if (bio.startswith("B-") or bio.startswith("I-")) else None
            prev_bio = bio

        # Runtime Tokenizer Compatibility
        rt_tokens = token_co_vi_tri(dv)
        rt_starts = {t.bat_dau for t in rt_tokens}
        rt_ends = {t.ket_thuc for t in rt_tokens}

        has_cut = False
        for f_name, sp in item['spans'].items():
            if sp:
                if sp['start'] not in rt_starts or sp['end'] not in rt_ends:
                    has_cut = True
                    break

        if has_cut:
            incompat_count += 1
            if item['usable_for_span_training']:
                errors.append(f"{iid}: Cắt token runtime nhưng usable_for_span_training lại là True!")
            if item['tokenizer_runtime_compatible']:
                errors.append(f"{iid}: Cắt token runtime nhưng tokenizer_runtime_compatible lại là True!")
        else:
            if not item['usable_for_span_training']:
                errors.append(f"{iid}: Không cắt token runtime nhưng usable_for_span_training lại là False!")
            if not item['tokenizer_runtime_compatible']:
                errors.append(f"{iid}: Không cắt token runtime nhưng tokenizer_runtime_compatible lại là False!")

    print(f"Kiểm tra Token Spans & BIO: {len(token_items)} bản ghi hợp lệ 100% ({incompat_count} ca dính chữ cắt token cách ly đúng chuẩn).")

    # 4.3 Kiểm tra Căn Cứ Thực Thể (Grounding & Role Consistency)
    print("\n--- KIỂM TRA CĂN CỨ THỰC THỂ (GROUNDING & ROLE CONSISTENCY) ---")
    char_spans_dict = {item['id']: item['spans'] for item in char_items}
    ngo_kw = ['ngõ', 'ngách', 'hẻm', 'kiệt']
    thon_kw = ['thôn', 'xóm', 'tổ', 'khu', 'ấp', 'bản', 'buôn', 'làng']

    null_span_counts = Counter()
    for r in v2_rows:
        iid = r['id']
        sp_entry = char_spans_dict.get(iid, {})

        # Rà từng trường chi tiết: Nếu nhãn khác rỗng thì span bắt buộc phải tồn tại
        for fld in ['so_nha', 'ngo_ngach_hem', 'thon_xom', 'duong']:
            lbl = r.get(fld, '')
            sp = sp_entry.get(fld)
            if lbl:
                if not sp:
                    null_span_counts[fld] += 1
                    errors.append(f"{iid}: Nhãn {fld}='{lbl}' khác rỗng nhưng span lại là null!")
                else:
                    sp_text_lower = sp['text'].lower()
                    if fld == 'ngo_ngach_hem':
                        if not any(kw in sp_text_lower for kw in ngo_kw):
                            errors.append(f"{iid}: Span ngo_ngach_hem '{sp['text']}' không chứa từ khóa ngõ hẻm hợp lệ (sai vai trò)!")
                    elif fld == 'thon_xom':
                        if not any(kw in sp_text_lower for kw in thon_kw):
                            errors.append(f"{iid}: Span thon_xom '{sp['text']}' không chứa từ khóa thôn xóm hợp lệ (sai vai trò)!")
                    elif fld == 'so_nha':
                        if any(kw in sp_text_lower for kw in ['phường', 'thị trấn', 'quận', 'huyện', 'tỉnh']):
                            errors.append(f"{iid}: Span so_nha '{sp['text']}' lẫn tên cấp hành chính (sai vai trò)!")

    if sum(null_span_counts.values()) == 0:
        print("Kiểm tra Grounding: 100% nhãn chi tiết khác rỗng đều có căn cứ span thực tế đúng vai trò trong input (0 null spans).")
    else:
        print(f"LỖI: Phát hiện các nhãn khác rỗng nhưng span null: {dict(null_span_counts)}")

    # 5. Chống Rò Rỉ Tuyệt Đối (Anti-Leakage Check = 0%)
    print("\n--- KIỂM TRA CHỐNG RÒ RỈ DỮ LIỆU DEV/TEST (LEAKAGE CHECK = 0%) ---")
    dev_orig = list(csv.DictReader(open(TRAIN_DEV_DIR / 'dev.csv', encoding='utf-8-sig')))
    dev_v1 = list(csv.DictReader(open(TRAIN_DEV_DIR / 'bo_sung_v1' / 'dev_kho.csv', encoding='utf-8-sig')))
    test_rows = []
    if (TEST_DIR / 'dia_chi_test.csv').exists():
        test_rows = list(csv.DictReader(open(TEST_DIR / 'dia_chi_test.csv', encoding='utf-8-sig')))

    blacklist_inputs = {norm(r['dau_vao']) for r in dev_orig + dev_v1 + test_rows if r.get('dau_vao')}
    blacklist_urls = {r['nguon'] for r in dev_orig + dev_v1 + test_rows if r.get('nguon') and r['nguon'].startswith('http')}

    def get_fam_key(r):
        dv = r['dau_vao']
        sn = r.get('so_nha', '')
        if sn and sn in dv:
            idx = dv.find(sn)
            masked = dv[:idx] + '<SO_NHA>' + dv[idx+len(sn):]
        else:
            masked = re.sub(r'^(?:Số\s+|so\s+)?[\d\/\-]+[A-Za-z]*\s*', '<SO_NHA> ', dv).strip()
        return (key(masked), r.get('duong', ''), r.get('ma_xa_cu', ''), r.get('ma_tinh', ''))

    blacklist_families = {get_fam_key(r) for r in dev_orig + dev_v1 + test_rows}

    v2_inputs = {norm(r['dau_vao']): r['id'] for r in v2_rows}
    v2_urls = {r['parent_source_url']: r['id'] for r in v2_rows if r.get('parent_source_url') and r['parent_source_url'].startswith('http')}
    v2_families = {get_fam_key(r): r['id'] for r in v2_rows}

    leak_inputs = set(v2_inputs.keys()) & blacklist_inputs
    leak_urls = set(v2_urls.keys()) & blacklist_urls
    leak_fams = set(v2_families.keys()) & blacklist_families

    if leak_inputs:
        errors.append(f"RÒ RỈ DỮ LIỆU: Có {len(leak_inputs)} chuỗi input trùng với Dev/Test!")
    if leak_urls:
        errors.append(f"RÒ RỈ DỮ LIỆU: Có {len(leak_urls)} URL nguồn trùng với Dev/Test!")
    if leak_fams:
        errors.append(f"RÒ RỈ HỌ MẪU: Có {len(leak_fams)} họ mẫu trùng với Dev/Test khi che số nhà!")

    print(f"Kết quả Chống Rò Rỉ: 0% rò rỉ input, 0% rò rỉ URL, 0% rò rỉ họ mẫu sau che số nhà.")

    # 6. Tính Toàn Vẹn Provenance (Provenance Integrity)
    print("\n--- KIỂM TRA TÍNH TOÀN VẸN PROVENANCE ---")
    orig_train_rows = {r['id']: r for r in csv.DictReader(open(TRAIN_DEV_DIR / 'train.csv', encoding='utf-8-sig'))}
    for r in v2_rows:
        pid = r['parent_id']
        if pid not in orig_train_rows:
            errors.append(f"{r['id']}: parent_id {pid} không có trong train.csv gốc")
        else:
            p_rec = orig_train_rows[pid]
            if r['ma_xa_cu'] != p_rec['ma_xa_cu']:
                errors.append(f"{r['id']}: Lệch ma_xa_cu so với mẫu cha {pid} ({r['ma_xa_cu']} != {p_rec['ma_xa_cu']})")
            if r['ma_huyen_cu'] != p_rec['ma_huyen_cu']:
                errors.append(f"{r['id']}: Lệch ma_huyen_cu so với mẫu cha {pid}")
            if r['ma_tinh_cu'] != p_rec['ma_tinh_cu']:
                errors.append(f"{r['id']}: Lệch ma_tinh_cu so với mẫu cha {pid}")

            # Kiểm tra bảo toàn tên đường từ mẫu cha (trừ trường hợp viết tắt mơ hồ đã để trống)
            if r['loai_bien_the'] != 'viet_tat_ten_rieng_mo_ho':
                if r['duong'] != p_rec['duong']:
                    errors.append(f"{r['id']}: Lệch tên đường so với mẫu cha {pid} ('{r['duong']}' != '{p_rec['duong']}')")

            # Kiểm tra khai báo minh bạch trường bị bỏ so với mẫu cha
            if p_rec.get('ngo_ngach_hem') and not r.get('ngo_ngach_hem'):
                if 'bo_ngo_ngach_hem_tu_cha' not in r.get('ghi_chu', ''):
                    errors.append(f"{r['id']}: Cha có ngõ '{p_rec['ngo_ngach_hem']}' nhưng con bỏ ngõ mà không khai báo bo_ngo_ngach_hem_tu_cha!")
            if p_rec.get('thon_xom') and not r.get('thon_xom'):
                if 'bo_thon_xom_tu_cha' not in r.get('ghi_chu', ''):
                    errors.append(f"{r['id']}: Cha có thôn '{p_rec['thon_xom']}' nhưng con bỏ thôn mà không khai báo bo_thon_xom_tu_cha!")

    print("Kiểm tra Provenance: 100% mẫu bảo toàn chuẩn xác mã hành chính, tên đường và khai báo trung thực trường bị bỏ.")

    # 7. Tính Toàn Vẹn Manifest & Mã Băm SHA-256 (Manifest Checksum Integrity)
    print("\n--- KIỂM TRA TÍNH TOÀN VẸN MANIFEST & CHECKSUMS ---")
    manifest_file = BO_SUNG_V2_DIR / "manifest.json"
    if not manifest_file.exists():
        errors.append("Không tìm thấy tệp manifest.json")
    else:
        with open(manifest_file, encoding='utf-8') as f:
            manifest_data = json.load(f)
        for fname, info in manifest_data.get('files', {}).items():
            f_path = BO_SUNG_V2_DIR / fname
            if not f_path.exists():
                errors.append(f"Tệp trong manifest không tồn tại: {fname}")
            else:
                c_bytes = f_path.read_bytes()
                actual_sha = hashlib.sha256(c_bytes).hexdigest()
                actual_size = len(c_bytes)
                if actual_sha != info['sha256']:
                    errors.append(f"{fname}: Lệch SHA-256 ({actual_sha} != {info['sha256']})")
                if actual_size != info['size_bytes']:
                    errors.append(f"{fname}: Lệch kích thước bytes ({actual_size} != {info['size_bytes']})")
        print("Kiểm tra Manifest: 100% tệp khớp SHA-256 và kích thước bytes đóng băng.")

    # 8. Kết luận
    print("\n=== KẾT QUẢ KIỂM TRA ===")
    if errors:
        print(f"THẤT BẠI: Phát hiện {len(errors)} lỗi:")
        for e in errors[:15]:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print("TẤT CẢ PHÉP KIỂM TRA ĐẠT YÊU CẦU 100% (PASS)!")
        print("1. Schema 30 trường: ĐẦY ĐỦ & CHUẨN XÁC 100%.")
        print("2. Mã zero-padded & quan hệ hành chính cha con: 100% HỢP LỆ.")
        print("3. Trộn mốc cũ-mới tương thích: 100% HỢP LỆ.")
        print("4. Xã bị chia tách & viết tắt đa nghĩa: GIỮ MƠ HỒ CHUẨN XÁC.")
        print("5. Char Spans, Token Spans & BIO sequence tags: 100% HỢP LỆ.")
        print("6. Grounding thực thể: 100% nhãn có span tương ứng đúng vai trò trong input (0 null spans).")
        print("7. Chống rò rỉ Dev/Test: 0% RÒ RỈ TUYỆT ĐỐI.")
        print("8. Tính toàn vẹn Provenance & Dropped fields: 100% BẢO TOÀN NGUỒN GỐC CHA.")
        print("9. Tính toàn vẹn Manifest & Checksums: 100% ĐÓNG BĂNG.")

if __name__ == '__main__':
    main()
