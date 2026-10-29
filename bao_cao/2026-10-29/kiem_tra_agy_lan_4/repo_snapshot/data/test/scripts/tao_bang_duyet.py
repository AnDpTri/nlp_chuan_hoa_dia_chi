#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script tạo bảng đối chiếu duyệt tập test (bang_duyet_test.csv).
- Gom đầy đủ 400 dòng từ dia_chi_test.csv và selected_sources.jsonl.
- Đặt thứ tự ưu tiên: 232 dòng can_duyet lên đầu (1_CAN_DUYET), 168 dòng tu_dong_khop (2_TU_DONG_KHOP).
- Cung cấp sẵn bằng chứng nguồn: POI name, thẻ địa chỉ OSM, xã ứng viên nếu bị chia.
- Các cột kiểm toán duyệt để trống hoặc giữ nguyên giá trị đã có.
- Bảo toàn tuyệt đối dữ liệu người dùng đã nhập nếu bảng duyệt cũ đã tồn tại.
"""

import sys
import json
import csv
import re
from pathlib import Path

# Đảm bảo encoding console
if hasattr(sys.stdout, 'reconfigure'):
    try: sys.stdout.reconfigure(encoding='utf-8')
    except Exception: pass
if hasattr(sys.stderr, 'reconfigure'):
    try: sys.stderr.reconfigure(encoding='utf-8')
    except Exception: pass

BASE_DIR = Path(__file__).resolve().parents[2] # D:\nlp_chuan_hoa_dia_chi\data
TEST_DIR = BASE_DIR / "test"

DUYET_FIELDS = [
    'id', 'muc_do_uu_tien', 'trang_thai_hien_tai', 'dau_vao', 'nguon', 'input_mode', 'poi_name',
    'so_nha', 'ngo_ngach_hem', 'thon_xom', 'duong', 'ma_xa_cu', 'ma_huyen_cu', 'ma_tinh_cu',
    'ma_xa', 'ma_tinh', 'xa_phuong', 'tinh', 'dia_chi_chuan', 'canh_bao', 'xa_ung_vien',
    'ghi_chu_nguon', 'trang_thai_duyet', 'loai_nguoi_duyet', 'agent_id', 'nguoi_duyet', 'model_duyet', 'ngay_duyet', 'thay_doi', 'ly_do_duyet'
]

def main(test_csv_arg=None, sources_arg=None, out_csv_arg=None):
    print("=== TẠO BẢNG ĐỐI CHIẾU DUYỆT TẬP TEST ===")
    test_csv_path = Path(test_csv_arg) if test_csv_arg else (TEST_DIR / "dia_chi_test.csv")
    sources_path = Path(sources_arg) if sources_arg else (TEST_DIR / "goc" / "selected_sources.jsonl")
    out_csv_path = Path(out_csv_arg) if out_csv_arg else (TEST_DIR / "bang_duyet_test.csv")
    
    if '--test-csv' in sys.argv:
        idx = sys.argv.index('--test-csv')
        if idx + 1 < len(sys.argv): test_csv_path = Path(sys.argv[idx + 1])
    if '--sources' in sys.argv:
        idx = sys.argv.index('--sources')
        if idx + 1 < len(sys.argv): sources_path = Path(sys.argv[idx + 1])
    if '--out-csv' in sys.argv:
        idx = sys.argv.index('--out-csv')
        if idx + 1 < len(sys.argv): out_csv_path = Path(sys.argv[idx + 1])
    
    # 1. Đọc sources
    sources = {}
    with open(sources_path, "r", encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            sources[d['id']] = d
            
    # 2. Đọc bảng duyệt cũ nếu đã có (để bảo toàn các ô người dùng đã điền)
    existing_rows = {}
    if out_csv_path.exists():
        with open(out_csv_path, "r", encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                existing_rows[r['id']] = r

    # 3. Đọc nhãn sơ bộ hiện tại
    with open(test_csv_path, "r", encoding="utf-8-sig") as f:
        test_rows = list(csv.DictReader(f))
        
    duyet_rows = []
    for r in test_rows:
        sid = r['id']
        src = sources.get(sid, {})
        prev = existing_rows.get(sid, {})
        
        # Trích xuất ứng viên xã nếu bị chia
        xa_ung_vien = ""
        m = re.search(r'xa_moi_ung_vien=(\[.*?\])', r['ghi_chu'])
        if m:
            xa_ung_vien = m.group(1)
            
        uu_tien = "1_CAN_DUYET" if r['trang_thai_nhan'] == 'can_duyet' else "2_TU_DONG_KHOP"
        
        # Bảo toàn thông tin nếu người dùng đã duyệt hoặc chỉnh sửa
        has_user_entry = bool(prev.get('trang_thai_duyet') or prev.get('nguoi_duyet') or prev.get('ly_do_duyet'))
        
        duyet_row = {
            'id': sid,
            'muc_do_uu_tien': uu_tien,
            'trang_thai_hien_tai': r['trang_thai_nhan'],
            'dau_vao': r['dau_vao'],
            'nguon': r['nguon'],
            'input_mode': src.get('input_mode', ''),
            'poi_name': src.get('name', ''),
            'so_nha': prev.get('so_nha', r['so_nha']) if has_user_entry else r['so_nha'],
            'ngo_ngach_hem': prev.get('ngo_ngach_hem', r['ngo_ngach_hem']) if has_user_entry else r['ngo_ngach_hem'],
            'thon_xom': prev.get('thon_xom', r['thon_xom']) if has_user_entry else r['thon_xom'],
            'duong': prev.get('duong', r['duong']) if has_user_entry else r['duong'],
            'ma_xa_cu': prev.get('ma_xa_cu', r['ma_xa_cu']) if has_user_entry else r['ma_xa_cu'],
            'ma_huyen_cu': prev.get('ma_huyen_cu', r['ma_huyen_cu']) if has_user_entry else r['ma_huyen_cu'],
            'ma_tinh_cu': prev.get('ma_tinh_cu', r['ma_tinh_cu']) if has_user_entry else r['ma_tinh_cu'],
            'ma_xa': prev.get('ma_xa', r['ma_xa']) if has_user_entry else r['ma_xa'],
            'ma_tinh': prev.get('ma_tinh', r['ma_tinh']) if has_user_entry else r['ma_tinh'],
            'xa_phuong': prev.get('xa_phuong', r['xa_phuong']) if has_user_entry else r['xa_phuong'],
            'tinh': prev.get('tinh', r['tinh']) if has_user_entry else r['tinh'],
            'dia_chi_chuan': prev.get('dia_chi_chuan', r['dia_chi_chuan']) if has_user_entry else r['dia_chi_chuan'],
            'canh_bao': prev.get('canh_bao', r['canh_bao']) if has_user_entry else r['canh_bao'],
            'xa_ung_vien': prev.get('xa_ung_vien', xa_ung_vien) if has_user_entry else xa_ung_vien,
            'ghi_chu_nguon': r['ghi_chu'],
            # Các cột kiểm toán người duyệt bảo toàn nếu đã điền
            'trang_thai_duyet': prev.get('trang_thai_duyet', r['trang_thai_nhan']),
            'loai_nguoi_duyet': prev.get('loai_nguoi_duyet', ''),
            'agent_id': prev.get('agent_id', ''),
            'nguoi_duyet': prev.get('nguoi_duyet', ''),
            'model_duyet': prev.get('model_duyet', ''),
            'ngay_duyet': prev.get('ngay_duyet', ''),
            'thay_doi': prev.get('thay_doi', ''),
            'ly_do_duyet': prev.get('ly_do_duyet', '')
        }
        duyet_rows.append(duyet_row)
        
    # Sắp xếp ưu tiên: 1_CAN_DUYET lên đầu, sau đó theo ID
    duyet_rows.sort(key=lambda x: (x['muc_do_uu_tien'], x['id']))
    
    with open(out_csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=DUYET_FIELDS)
        writer.writeheader()
        writer.writerows(duyet_rows)
        
    n_can_duyet = sum(1 for r in duyet_rows if r['muc_do_uu_tien'] == '1_CAN_DUYET')
    n_tu_dong = sum(1 for r in duyet_rows if r['muc_do_uu_tien'] == '2_TU_DONG_KHOP')
    print(f"Đã tạo bảng đối chiếu duyệt: {out_csv_path}")
    print(f"Tổng số mẫu: {len(duyet_rows)}")
    print(f"  Ưu tiên 1 (can_duyet): {n_can_duyet} dòng")
    print(f"  Ưu tiên 2 (tu_dong_khop): {n_tu_dong} dòng")

if __name__ == "__main__":
    main()
