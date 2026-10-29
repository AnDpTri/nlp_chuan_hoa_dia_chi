#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script theo dõi tiến độ duyệt nhãn tập test và kiểm tra chữ ký người duyệt.
- Đọc bang_duyet_test.csv.
- Thống kê tiến độ: Đã duyệt / Còn lại (Ưu tiên 1 can_duyet vs Ưu tiên 2 tu_dong_khop).
- Đếm diff trường nhãn/cảnh báo thực tế, không bị nhầm bởi chuỗi 'Không thay đổi (...)'.
- Phân biệt rõ agent_id và model_duyet.
- Kiểm tra tính hợp lệ của chữ ký: nếu ghi da_duyet thì bắt buộc phải có nguoi_duyet và ngay_duyet hợp lệ.
- Hỗ trợ tùy chọn --sync:
  + Đồng bộ các dòng đã giải quyết sang dia_chi_test.csv (da_duyet hoặc da_duyet_ai).
  + Giữ nguyên trạng thái can_duyet cho các dòng chưa đủ căn cứ (chua_du_can_cu, xã bị chia chưa có số nhà chi tiết).
  + Mang tính lũy đắc (idempotent), không bao giờ nhân đôi nhật ký hoặc xóa mất ứng viên/cảnh báo.
"""

import sys
import os
import json
import csv
import re
from datetime import datetime
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

FIELDS_TEST = [
    'id', 'dau_vao', 'nguon', 'so_nha', 'ngo_ngach_hem', 'thon_xom', 'duong',
    'ma_xa_cu', 'ma_huyen_cu', 'ma_tinh_cu', 'ma_xa', 'ma_tinh', 'xa_phuong', 'tinh',
    'dia_chi_chuan', 'canh_bao', 'trang_thai_nhan', 'ghi_chu'
]

def is_valid_calendar_date(d_str):
    if not d_str or not re.match(r'^\d{4}-\d{2}-\d{2}$', str(d_str).strip()):
        return False
    try:
        dt = datetime.strptime(str(d_str).strip(), '%Y-%m-%d')
        return 2024 <= dt.year <= 2030
    except ValueError:
        return False

def is_valid_reviewer_name(name):
    if not name:
        return False
    name_clean = str(name).strip()
    if len(name_clean) < 2:
        return False
    if name_clean.lower() in ('bot', 'auto', 'ai', 'agy', 'gemini', 'none', 'null', 'unknown', 'test', 'reviewer'):
        return False
    return True

def is_valid_ai_reviewer_name(name):
    if not name:
        return False
    name_clean = str(name).strip().lower()
    return any(k in name_clean for k in ('ai', 'agent', 'gemini', 'antigravity', 'gpt', 'claude', 'deepmind')) or len(name_clean) >= 3

def main(bang_duyet_arg=None, test_csv_arg=None, sync_arg=None):
    sync_mode = sync_arg if sync_arg is not None else ('--sync' in sys.argv)
    
    # Cho phép truyền đường dẫn qua tham số CLI hoặc function call
    bang_duyet_path = Path(bang_duyet_arg) if bang_duyet_arg else (TEST_DIR / "bang_duyet_test.csv")
    test_csv_path = Path(test_csv_arg) if test_csv_arg else (TEST_DIR / "dia_chi_test.csv")
    backup_csv_path = TEST_DIR / "backup_before_ai_review" / "dia_chi_test.csv"
    
    # Hỗ trợ CLI --bang-duyet và --test-csv
    if '--bang-duyet' in sys.argv:
        idx = sys.argv.index('--bang-duyet')
        if idx + 1 < len(sys.argv):
            bang_duyet_path = Path(sys.argv[idx + 1])
    if '--test-csv' in sys.argv:
        idx = sys.argv.index('--test-csv')
        if idx + 1 < len(sys.argv):
            test_csv_path = Path(sys.argv[idx + 1])
    
    if not bang_duyet_path.exists():
        print("LỖI: Chưa có tệp bang_duyet_test.csv. Hãy chạy tao_bang_duyet.py trước!")
        sys.exit(1)
        
    with open(bang_duyet_path, "r", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
        
    total_rows = len(rows)
    p1_total = sum(1 for r in rows if r['muc_do_uu_tien'] == '1_CAN_DUYET')
    p2_total = sum(1 for r in rows if r['muc_do_uu_tien'] == '2_TU_DONG_KHOP')
    
    # Đọc baseline ban đầu nếu có để tính diff thực
    baseline_rows = {}
    if backup_csv_path.exists():
        with open(backup_csv_path, "r", encoding="utf-8-sig") as f:
            baseline_rows = {r['id']: r for r in csv.DictReader(f)}
    
    human_reviewed_rows = []
    p1_human = 0
    p2_human = 0
    human_changed = 0
    human_reviewers = set()
    
    ai_audited_rows = []
    ai_resolved_rows = []
    ai_unresolved_rows = []
    p1_ai = 0
    p2_ai = 0
    ai_changed = 0
    ai_agents = set()
    ai_models = set()
    
    signature_errors = []
    label_check_fields = ['so_nha', 'ngo_ngach_hem', 'thon_xom', 'duong', 'ma_xa', 'ma_tinh', 'xa_phuong', 'tinh', 'dia_chi_chuan', 'canh_bao']
    
    for r in rows:
        sid = r['id']
        status = r.get('trang_thai_duyet', '').strip()
        hien_tai = r.get('trang_thai_hien_tai', '').strip()
        loai = r.get('loai_nguoi_duyet', '').strip().lower()
        reviewer = r.get('nguoi_duyet', '').strip()
        agent = r.get('agent_id', '').strip() or reviewer
        model = r.get('model_duyet', '').strip() or 'gemini-3.8-flash-high'
        date_str = r.get('ngay_duyet', '').strip()
        change_note = r.get('thay_doi', '').strip()
        reason = r.get('ly_do_duyet', '').strip()
        
        # Kiểm tra xem có thực sự đổi nhãn so với baseline không
        is_real_label_diff = False
        if sid in baseline_rows:
            bak = baseline_rows[sid]
            is_real_label_diff = any(r.get(k) != bak.get(k) for k in label_check_fields)
        else:
            is_not_changed = change_note.lower().startswith(('khong thay doi', 'không thay đổi', 'giu nguyen', 'giữ nguyên', 'không đổi', 'khong doi'))
            is_real_label_diff = bool(change_note and not is_not_changed)
            
        is_ai = (status == 'da_duyet_ai' or loai == 'ai' or any(k in reviewer.lower() for k in ('ai', 'agent', 'gemini', 'antigravity')))
        
        if is_ai and loai == 'ai':
            # AI review row
            ai_audited_rows.append(r)
            if agent: ai_agents.add(agent)
            if model: ai_models.add(model)
            
            if status == 'da_duyet_ai' or hien_tai == 'da_duyet_ai':
                ai_resolved_rows.append(r)
                if r['muc_do_uu_tien'] == '1_CAN_DUYET': p1_ai += 1
                else: p2_ai += 1
            else:
                ai_unresolved_rows.append(r)
                
            if is_real_label_diff:
                ai_changed += 1
                
            if status in ('da_duyet', 'da_duyet_ai'):
                if not is_valid_ai_reviewer_name(reviewer):
                    signature_errors.append(f"{r['id']}: Đánh dấu AI duyệt nhưng tên reviewer AI không hợp lệ ('{reviewer}')!")
                elif not is_valid_calendar_date(date_str):
                    signature_errors.append(f"{r['id']}: Ngày duyệt không hợp lệ theo lịch (YYYY-MM-DD): '{date_str}'")
                elif not reason:
                    signature_errors.append(f"{r['id']}: Thiếu lý do/căn cứ duyệt tại cột ly_do_duyet!")
        elif status == 'da_duyet' and loai != 'ai':
            # Human review
            if not is_valid_reviewer_name(reviewer):
                signature_errors.append(f"{r['id']}: Đánh dấu da_duyet nhưng thiếu hoặc tên người duyệt không hợp lệ ('{reviewer}')!")
            elif not is_valid_calendar_date(date_str):
                signature_errors.append(f"{r['id']}: Ngày duyệt không hợp lệ theo lịch (YYYY-MM-DD): '{date_str}'")
            elif not reason:
                signature_errors.append(f"{r['id']}: Thiếu lý do/căn cứ duyệt tại cột ly_do_duyet!")
            else:
                human_reviewed_rows.append(r)
                human_reviewers.add(reviewer)
                if r['muc_do_uu_tien'] == '1_CAN_DUYET': p1_human += 1
                else: p2_human += 1
                if is_real_label_diff:
                    human_changed += 1
                    
    print("=== BÁO CÁO TIẾN ĐỘ DUYỆT TẬP TEST ===")
    print(f"Tổng số mẫu: {total_rows}")
    print(f"--- Người duyệt (Human Review) ---")
    print(f"  - Ưu tiên 1 (can_duyet):   {p1_human} / {p1_total} ({p1_human/p1_total*100:.1f}%)" if p1_total else "  - Ưu tiên 1: 0")
    print(f"  - Ưu tiên 2 (tu_dong_khop): {p2_human} / {p2_total} ({p2_human/p2_total*100:.1f}%)" if p2_total else "  - Ưu tiên 2: 0")
    print(f"  - Tổng số dòng người duyệt: {len(human_reviewed_rows)} / {total_rows} ({len(human_reviewed_rows)/total_rows*100:.1f}%)")
    print(f"  - Người duyệt tham gia:     {', '.join(sorted(human_reviewers)) if human_reviewers else '(Chưa có)'}")
    print(f"--- AI duyệt (AI Review) ---")
    print(f"  - Tổng số mẫu đã kiểm toán: {len(ai_audited_rows)} / {total_rows} ({len(ai_audited_rows)/total_rows*100:.1f}%)")
    print(f"  - Số dòng chốt hợp lệ (da_duyet_ai): {len(ai_resolved_rows)} / {total_rows} ({len(ai_resolved_rows)/total_rows*100:.1f}%)")
    print(f"  - Số dòng bảo lưu (can_duyet):       {len(ai_unresolved_rows)} / {total_rows} ({len(ai_unresolved_rows)/total_rows*100:.1f}%)")
    print(f"  - Số dòng AI điều chỉnh nhãn (diff): {ai_changed}")
    print(f"  - AI agent:                         {', '.join(sorted(ai_agents)) if ai_agents else 'antigravity-deepmind-agent'}")
    print(f"  - Model:                            {', '.join(sorted(ai_models)) if ai_models else 'gemini-3.8-flash-high'}")
    
    if signature_errors:
        print(f"\n[CẢNH BÁO] Phát hiện {len(signature_errors)} lỗi metadata duyệt:")
        for err in signature_errors[:5]:
            print("  -", err)
            
    # Báo cáo trạng thái sẵn sàng
    is_gold_ready = (len(human_reviewed_rows) == total_rows and len(signature_errors) == 0)
    print(f"\nTrạng thái sẵn sàng làm Bộ đáp án vàng (Gold Evaluation): {'SẴN SÀNG' if is_gold_ready else 'CHƯA SẴN SÀNG (Cần 100% người duyệt chứng thực)'}")
    
    if sync_mode:
        if signature_errors:
            print("KHÔNG THỂ ĐỒNG BỘ do còn lỗi metadata người duyệt!")
            sys.exit(1)
        all_reviewed = human_reviewed_rows + ai_audited_rows
        if len(all_reviewed) == 0:
            print("Chưa có dòng nào được duyệt để đồng bộ.")
            return
            
        print(f"\nĐang đồng bộ dữ liệu duyệt sang {test_csv_path.name}...")
        by_id_reviewed = {r['id']: r for r in all_reviewed}
        
        with open(test_csv_path, "r", encoding="utf-8-sig") as f:
            current_test = list(csv.DictReader(f))
            
        synced_count = 0
        sync_fields = [
            'so_nha', 'ngo_ngach_hem', 'thon_xom', 'duong',
            'ma_xa_cu', 'ma_huyen_cu', 'ma_tinh_cu',
            'ma_xa', 'ma_tinh', 'xa_phuong', 'tinh',
            'dia_chi_chuan', 'canh_bao'
        ]
        
        for r in current_test:
            sid = r['id']
            if sid in by_id_reviewed:
                src = by_id_reviewed[sid]
                # Đồng bộ các trường nhãn
                for col in sync_fields:
                    if col in src and src[col] is not None:
                        r[col] = src[col]
                
                src_loai = src.get('loai_nguoi_duyet', '').strip().lower()
                is_ai_row = (src.get('trang_thai_duyet') == 'da_duyet_ai' or src_loai == 'ai')
                
                # Đồng bộ và làm sạch cảnh báo (canh_bao)
                try:
                    cb = json.loads(r['canh_bao']) if r['canh_bao'] else []
                except Exception:
                    cb = []
                    
                # KIỂM TRA CHÍNH XÁC: ĐÃ CHỐT HAY BẢO LƯU CHƯA ĐỦ CĂN CỨ
                is_unresolved = (
                    src.get('trang_thai_duyet') == 'can_duyet'
                    or src.get('ket_luan') == 'chua_du_can_cu'
                    or (not r['ma_xa'] and 'xa_bi_chia' in cb)
                )
                
                if is_unresolved:
                    r['trang_thai_nhan'] = 'can_duyet'
                    if 'xa_bi_chia' not in cb and ('xa_moi_ung_vien=' in r['ghi_chu'] or src.get('xa_ung_vien')):
                        cb.append('xa_bi_chia')
                else:
                    r['trang_thai_nhan'] = 'da_duyet_ai' if is_ai_row else 'da_duyet'
                    if r['ma_xa']:
                        cb = [w for w in cb if w != 'xa_bi_chia']
                        
                r['canh_bao'] = json.dumps(sorted(set(cb)), ensure_ascii=False)
                
                # Làm sạch ghi_chu cũ trước khi thêm nhật ký kiểm toán (tránh nhân đôi nhật ký, bảo toàn ghi chú tùy chỉnh)
                raw_notes = [n.strip() for n in r['ghi_chu'].split(';') if n.strip()]
                cleaned_notes = [
                    n for n in raw_notes
                    if not n.startswith(('duyet_boi=', 'loai_nguoi_duyet=', 'ngay_duyet=', 'ly_do=', 'model=', 'agent_id='))
                    and not n.startswith('bảo lưu ứng viên để người thẩm định')
                ]
                
                if r['ma_xa']:
                    cleaned_notes = [n for n in cleaned_notes if not n.startswith('xa_moi_ung_vien=')]
                elif src.get('xa_ung_vien') and not any(n.startswith('xa_moi_ung_vien=') for n in cleaned_notes):
                    cleaned_notes.append(f"xa_moi_ung_vien={src['xa_ung_vien']}")
                    
                loai_tag = 'ai' if is_ai_row else 'human'
                rev_name = src.get('agent_id') or src.get('nguoi_duyet') or 'antigravity-deepmind-agent'
                model_name = src.get('model_duyet') or 'gemini-3.8-flash-high'
                safe_reason = (src.get('ly_do_duyet') or '').replace(';', ',')
                
                if is_ai_row:
                    audit_note = f"duyet_boi={rev_name}; model={model_name}; loai_nguoi_duyet={loai_tag}; ngay_duyet={src['ngay_duyet']}; ly_do={safe_reason}"
                else:
                    audit_note = f"duyet_boi={src['nguoi_duyet']}; loai_nguoi_duyet={loai_tag}; ngay_duyet={src['ngay_duyet']}; ly_do={safe_reason}"
                    
                cleaned_notes.append(audit_note)
                r['ghi_chu'] = '; '.join(cleaned_notes)
                synced_count += 1
                
        with open(test_csv_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDS_TEST)
            writer.writeheader()
            writer.writerows(current_test)
        print(f"Đã đồng bộ thành công {synced_count} dòng (giữ nguyên can_duyet cho các dòng bảo lưu).")

if __name__ == "__main__":
    main()
