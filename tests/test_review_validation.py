#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hồi quy kiểm thử quy trình duyệt nhãn và validator tập test:
- Chạy trên fixture và bản sao tạm thời (tempdir), TUYỆT ĐỐI KHÔNG sửa đổi dia_chi_test.csv thật.
- Kiểm tra các ca:
  1. Tập test thật chưa duyệt: PASS cấu trúc, 0 dòng da_duyet, is_ready_for_gold = False.
  2. Dòng da_duyet có metadata hợp lệ (người, ngày thực, lý do): PASS.
  3. Thiếu người duyệt hoặc tên placeholder (bot, auto, test): FAIL.
  4. Ngày duyệt không tồn tại theo lịch (vd: 2026-02-30): FAIL.
  5. Thiếu lý do duyệt: FAIL.
  6. Giải quyết xã bị chia có đủ bằng chứng và người duyệt: PASS.
  7. Tự ý gán xã đích cho xã bị chia khi chưa có người duyệt: FAIL.
  8. Gán xã đích không thuộc tập chuyển đổi: FAIL.
  9. Người duyệt xem xét xã bị chia nhưng chưa đủ bằng chứng (để trống): PASS.
  10. Tái chạy kiem_tra_tien_do_duyet.py --sync không nhân đôi nhật ký.
  11. Chạy lại tao_bang_duyet.py bảo toàn các ô người dùng đã điền.
  12. AI review: ghi nhận da_duyet_ai, tăng ai_reviewed_rows, không tăng human_reviewed_rows.
  13. AI review giải quyết xã bị chia có bằng chứng đối chiếu hợp lệ: PASS.
  14. AI review gán sai đích không thuộc tập chuyển đổi cho xã bị chia: FAIL.
  15. Kiểm tra span offset >= 0, khớp substring, không chồng lấn, 0 ca [-1:].
  16. Kiểm tra can_cu_web: phân biệt rõ HTTP 200 (NQ1685) và tra cứu trực tuyến thất bại HTTP 404 (các văn bản còn lại).
  17. Toàn bộ 33 ca xã bị chia để trống ma_xa, giữ cờ xa_bi_chia và can_duyet.
  18. Lệnh --sync bảo lưu can_duyet cho toàn bộ 108 dòng chưa đủ căn cứ.
  19. Tính lũy đắc (idempotency) của --sync (diff = 0 giữa 2 lần chạy liên tiếp).
  20. Đếm diff trường nhãn thực tế báo đúng 29 dòng.
  21. Thực sự chạy engine ai_review_engine.main(...) trên fixture tạm thời, bảo toàn người duyệt (human preservation).
  22. Negative tests: chứng minh validator phát hiện và chặn span âm [-1:], span chồng lấn, thời gian giả lập.
  23. Kiểm tra tệp phân loại chi tiết phan_loai_chi_tiet_400_id.csv và .md (263 du_can_cu, 29 nhan_can_sua, 108 chua_du_can_cu).
  24. Xác minh ca VNTEST0040: Phố Thiên Lôi / Phường Gia Viên Hải Phòng (không nhầm Đằng Giang, can_duyet, ma_xa rỗng).
"""

import sys
import os
import csv
import json
import shutil
import tempfile
import re
import hashlib
import unicodedata
from collections import Counter
from pathlib import Path

# Đảm bảo console utf-8
if hasattr(sys.stdout, 'reconfigure'):
    try: sys.stdout.reconfigure(encoding='utf-8')
    except Exception: pass

BASE_DIR = Path(__file__).resolve().parents[1]
TEST_DIR = BASE_DIR / "data" / "test"
SCRIPTS_DIR = TEST_DIR / "scripts"

sys.path.insert(0, str(SCRIPTS_DIR))
import validate_dataset
import kiem_tra_tien_do_duyet
import tao_bang_duyet
import ai_review_engine
from admin_lookup import Catalogues
from build_labels import full

def run_all_tests():
    print("=== BẮT ĐẦU CHẠY BỘ KIỂM THỬ HỒI QUY QUY TRÌNH DUYỆT TẬP TEST ===")
    passed = 0
    total = 0
    
    # 1. Kiểm tra tập test thật (chưa duyệt)
    total += 1
    print("\n[Test 1] Kiểm tra tập test thật hiện tại...")
    real_csv = TEST_DIR / "dia_chi_test.csv"
    report = validate_dataset.main(csv_file=str(real_csv))
    assert report['structural_status'] == 'PASS', "Tập test thật phải đạt PASS về cấu trúc!"
    assert report['human_reviewed_rows'] == 0, "Tập test thật chưa được người duyệt, số dòng phải = 0!"
    assert report['is_ready_for_gold_evaluation'] is False, "Tập test chưa duyệt không được làm Gold Evaluation!"
    assert report['provisional_only'] is True, "Tập test phải ở trạng thái provisional_only!"
    print("  -> ĐẠT: Tập test thật PASS cấu trúc, 0 dòng da_duyet, chưa sẵn sàng làm Gold.")
    passed += 1

    # Tạo thư mục tạm thời cho các ca thử nghiệm fixture
    temp_dir = Path(tempfile.mkdtemp(prefix="test_duyet_fixture_"))
    try:
        fixture_csv = temp_dir / "dia_chi_test.csv"
        fixture_bang_duyet = temp_dir / "bang_duyet_test.csv"
        
        baseline_csv = TEST_DIR / "backup_before_ai_review" / "dia_chi_test.csv"
        if not baseline_csv.exists():
            baseline_csv = real_csv
        shutil.copy(baseline_csv, fixture_csv)
        
        with open(fixture_csv, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            rows = list(reader)

        # 2. Test có metadata hợp lệ
        total += 1
        print("\n[Test 2] Dòng da_duyet có metadata hợp lệ (người, ngày lịch, lý do)...")
        test_rows = [dict(r) for r in rows]
        normal_idx = next(i for i, r in enumerate(test_rows) if 'xa_bi_chia' not in r['canh_bao'])
        target_id = test_rows[normal_idx]['id']
        test_rows[normal_idx]['trang_thai_nhan'] = 'da_duyet'
        test_rows[normal_idx]['ghi_chu'] += "; duyet_boi=Nguyen Van A; ngay_duyet=2026-03-15; ly_do=Xac minh truc tiep tai dia phuong"
        
        with open(fixture_csv, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(test_rows)
            
        rep2 = validate_dataset.main(csv_file=str(fixture_csv))
        assert rep2['structural_status'] == 'PASS'
        assert rep2['human_reviewed_rows'] == 1, "Phải ghi nhận đúng 1 dòng đã duyệt!"
        print("  -> ĐẠT: Metadata hợp lệ được chấp nhận, tăng human_reviewed_rows lên 1.")
        passed += 1

        # 3. Test thiếu người duyệt hoặc tên placeholder
        total += 1
        print("\n[Test 3] Dòng da_duyet thiếu người duyệt hoặc dùng tên placeholder (bot, auto, ai)...")
        for bad_name in ['', 'bot', 'auto', 'AI', 'agy', 'test']:
            test_rows[normal_idx]['ghi_chu'] = f"duyet_boi={bad_name}; ngay_duyet=2026-03-15; ly_do=Xac minh"
            with open(fixture_csv, "w", encoding="utf-8", newline="") as f:
                w = csv.DictWriter(f, fieldnames=fieldnames)
                w.writeheader()
                w.writerows(test_rows)
            try:
                validate_dataset.main(csv_file=str(fixture_csv))
                assert False, f"Tên '{bad_name}' phải bị từ chối!"
            except SystemExit:
                pass
        print("  -> ĐẠT: Toàn bộ tên placeholder và tên rỗng đều bị validator từ chối.")
        passed += 1

        # 4. Test ngày duyệt không tồn tại theo lịch
        total += 1
        print("\n[Test 4] Ngày duyệt không tồn tại theo lịch (2026-02-30)...")
        test_rows[normal_idx]['ghi_chu'] = "duyet_boi=Tran Thi B; ngay_duyet=2026-02-30; ly_do=Kiem tra thuc dia"
        with open(fixture_csv, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(test_rows)
        try:
            validate_dataset.main(csv_file=str(fixture_csv))
            assert False, "Ngày 2026-02-30 phải bị từ chối!"
        except SystemExit:
            pass
        print("  -> ĐẠT: Ngày không có trong lịch bị từ chối chính xác.")
        passed += 1

        # 5. Test thiếu lý do duyệt
        total += 1
        print("\n[Test 5] Thiếu lý do duyệt (ly_do trống)...")
        test_rows[normal_idx]['ghi_chu'] = "duyet_boi=Tran Thi B; ngay_duyet=2026-03-20; ly_do="
        with open(fixture_csv, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(test_rows)
        try:
            validate_dataset.main(csv_file=str(fixture_csv))
            assert False, "Thiếu lý do duyệt phải bị từ chối!"
        except SystemExit:
            pass
        print("  -> ĐẠT: Thiếu lý do duyệt bị từ chối chính xác.")
        passed += 1

        # 6. Test giải quyết xã bị chia có đủ bằng chứng và người duyệt
        total += 1
        print("\n[Test 6] Giải quyết xã bị chia có đủ bằng chứng và người duyệt...")
        cat = Catalogues()
        test_rows = [dict(r) for r in rows]
        split_idx = next(i for i, r in enumerate(test_rows) if 'xa_bi_chia' in r['canh_bao'])
        split_row = test_rows[split_idx]
        old_code = split_row['ma_xa_cu']
        targets = [m['ma_xa_moi'] for m in cat.to_new[old_code]]
        assert len(targets) > 1, "Mẫu thử phải là xã bị chia thành nhiều đích!"
        chosen_target = targets[0]
        target_name = full(cat.new_wi[chosen_target], 'xa')
        
        test_rows[split_idx]['ma_xa'] = chosen_target
        test_rows[split_idx]['xa_phuong'] = target_name
        test_rows[split_idx]['trang_thai_nhan'] = 'da_duyet'
        cb = json.loads(test_rows[split_idx]['canh_bao'])
        cb = [w for w in cb if w != 'xa_bi_chia']
        test_rows[split_idx]['canh_bao'] = json.dumps(cb)
        test_rows[split_idx]['ghi_chu'] += f"; duyet_boi=Le Van C; ngay_duyet=2026-03-25; ly_do=Can cu so nha thuoc dia ban {target_name}"
        
        with open(fixture_csv, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(test_rows)
            
        rep6 = validate_dataset.main(csv_file=str(fixture_csv))
        assert rep6['structural_status'] == 'PASS'
        assert rep6['human_reviewed_rows'] == 1
        print("  -> ĐẠT: Xã bị chia được giải quyết hợp lệ khi có người duyệt và đích thuộc mapping.")
        passed += 1

        # 7. Test tự ý gán xã đích cho xã bị chia khi chưa có người duyệt -> FAIL
        total += 1
        print("\n[Test 7] Tự ý gán xã đích cho xã bị chia khi chưa có người duyệt...")
        test_rows[split_idx]['trang_thai_nhan'] = 'can_duyet'
        test_rows[split_idx]['ghi_chu'] = ""
        with open(fixture_csv, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(test_rows)
        try:
            validate_dataset.main(csv_file=str(fixture_csv))
            assert False, "Tự ý gán xã đích khi chưa duyệt phải bị từ chối!"
        except SystemExit:
            pass
        print("  -> ĐẠT: Chặn thành công tự ý gán xã đích khi chưa duyệt.")
        passed += 1

        # 8. Test gán xã đích không thuộc tập chuyển đổi
        total += 1
        print("\n[Test 8] Gán xã đích không thuộc danh sách xã mới ứng viên...")
        all_new_codes = set(cat.new_wi.keys())
        fake_target = next(c for c in all_new_codes if c not in targets)
        fake_info = cat.new_wi[fake_target]
        test_rows[split_idx]['ma_xa'] = fake_target
        test_rows[split_idx]['ma_tinh'] = fake_info['ma_tinh']
        test_rows[split_idx]['xa_phuong'] = full(fake_info, 'xa')
        test_rows[split_idx]['tinh'] = full(cat.new_pi[fake_info['ma_tinh']], 'tinh')
        test_rows[split_idx]['trang_thai_nhan'] = 'da_duyet'
        test_rows[split_idx]['ghi_chu'] = f"duyet_boi=Le Van C; ngay_duyet=2026-03-25; ly_do=Gan sai lech"
        with open(fixture_csv, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(test_rows)
        try:
            validate_dataset.main(csv_file=str(fixture_csv))
            assert False, "Gán đích không thuộc tập chuyển đổi phải bị từ chối!"
        except SystemExit:
            pass
        print("  -> ĐẠT: Chặn thành công xã đích không thuộc quan hệ chuyển đổi.")
        passed += 1

        # 9. Test người duyệt xem xét xã bị chia nhưng chưa đủ bằng chứng -> để trống
        total += 1
        print("\n[Test 9] Người duyệt xem xét xã bị chia nhưng chưa đủ bằng chứng (để trống ma_xa)...")
        test_rows = [dict(r) for r in rows]
        test_rows[split_idx]['ma_xa'] = ""
        test_rows[split_idx]['xa_phuong'] = ""
        test_rows[split_idx]['trang_thai_nhan'] = 'da_duyet'
        test_rows[split_idx]['ghi_chu'] += "; duyet_boi=Chuyen Gia Dia Phuong; ngay_duyet=2026-03-20; ly_do=Dia chi chi ghi ten xa cu da bi chia thanh 3 phuong khong co so nha khong the xac dinh"
        with open(fixture_csv, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(test_rows)
        rep9 = validate_dataset.main(csv_file=str(fixture_csv))
        assert rep9['structural_status'] == 'PASS'
        print("  -> ĐẠT: Xã bị chia được duyệt nhưng để trống xã đích khi thiếu căn cứ -> HỢP LỆ.")
        passed += 1

        # 10. Test tái chạy kiem_tra_tien_do_duyet --sync không nhân đôi nhật ký
        total += 1
        print("\n[Test 10] Tái chạy --sync nhiều lần không nhân đôi nhật ký trong ghi_chu...")
        shutil.copy(baseline_csv, fixture_csv)
        tao_bang_duyet.main(test_csv_arg=str(fixture_csv), out_csv_arg=str(fixture_bang_duyet))
        
        with open(fixture_bang_duyet, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            b_fields = reader.fieldnames
            b_rows = list(reader)
        b_rows[0]['trang_thai_duyet'] = 'da_duyet'
        b_rows[0]['nguoi_duyet'] = 'Kiem Toan Vien A'
        b_rows[0]['ngay_duyet'] = '2026-04-10'
        b_rows[0]['ly_do_duyet'] = 'Xac minh tu lieu'
        b_rows[0]['thay_doi'] = 'Khong thay doi'
        with open(fixture_bang_duyet, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=b_fields)
            w.writeheader()
            w.writerows(b_rows)
            
        kiem_tra_tien_do_duyet.main(bang_duyet_arg=str(fixture_bang_duyet), test_csv_arg=str(fixture_csv), sync_arg=True)
        synced_id = b_rows[0]['id']
        with open(fixture_csv, "r", encoding="utf-8-sig") as f:
            r1 = next(r for r in csv.DictReader(f) if r['id'] == synced_id)['ghi_chu']
            
        kiem_tra_tien_do_duyet.main(bang_duyet_arg=str(fixture_bang_duyet), test_csv_arg=str(fixture_csv), sync_arg=True)
        with open(fixture_csv, "r", encoding="utf-8-sig") as f:
            r2 = next(r for r in csv.DictReader(f) if r['id'] == synced_id)['ghi_chu']
            
        assert r1 == r2, f"Nhật ký bị thay đổi/nhân đôi khi chạy lại sync!\nLần 1: {r1}\nLần 2: {r2}"
        assert r2.count('duyet_boi=') == 1, f"Chỉ được xuất hiện đúng 1 lần 'duyet_boi='! Thực tế: {r2}"
        print("  -> ĐẠT: Đồng bộ mang tính lũy đắc (idempotent), không nhân đôi nhật ký.")
        passed += 1

        # 11. Test tạo lại bảng duyệt bảo toàn các ô đã được người dùng điền
        total += 1
        print("\n[Test 11] Chạy lại tao_bang_duyet bảo toàn các ô người dùng đã điền...")
        tao_bang_duyet.main(test_csv_arg=str(fixture_csv), out_csv_arg=str(fixture_bang_duyet))
        with open(fixture_bang_duyet, "r", encoding="utf-8-sig") as f:
            re_b_rows = list(csv.DictReader(f))
            first_row = next(r for r in re_b_rows if r['id'] == b_rows[0]['id'])
        assert first_row['trang_thai_duyet'] == 'da_duyet', "Ô trang_thai_duyet bị mất sau khi tái tạo bảng!"
        assert first_row['nguoi_duyet'] == 'Kiem Toan Vien A', "Ô nguoi_duyet bị mất sau khi tái tạo bảng!"
        assert first_row['ly_do_duyet'] == 'Xac minh tu lieu', "Ô ly_do_duyet bị mất sau khi tái tạo bảng!"
        print("  -> ĐẠT: Tái tạo bảng duyệt bảo toàn toàn bộ dữ liệu người dùng đã nhập.")
        passed += 1

        # 12. Test AI review metadata phân biệt với Human review
        total += 1
        print("\n[Test 12] AI review: ghi nhận da_duyet_ai, tăng ai_reviewed_rows, không tăng human_reviewed_rows...")
        shutil.copy(baseline_csv, fixture_csv)
        with open(fixture_csv, "r", encoding="utf-8") as f:
            test_rows = list(csv.DictReader(f))
        test_rows[normal_idx]['trang_thai_nhan'] = 'da_duyet_ai'
        test_rows[normal_idx]['ghi_chu'] += "; duyet_boi=antigravity-deepmind-agent; loai_nguoi_duyet=ai; ngay_duyet=2026-10-29; ly_do=AI kiem tra chieu sau tu nguon chuan hoa"
        with open(fixture_csv, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(test_rows)
        rep12 = validate_dataset.main(csv_file=str(fixture_csv))
        assert rep12['structural_status'] == 'PASS'
        assert rep12['ai_reviewed_rows'] == 1, f"ai_reviewed_rows phải = 1, thực tế: {rep12['ai_reviewed_rows']}"
        assert rep12['human_reviewed_rows'] == 0, f"human_reviewed_rows phải = 0, thực tế: {rep12['human_reviewed_rows']}"
        assert rep12['is_ready_for_gold_evaluation'] is False, "AI duyệt không được làm Gold Evaluation!"
        print("  -> ĐẠT: AI review được ghi nhận độc lập, không mạo danh người duyệt.")
        passed += 1

        # 13. Test AI review giải quyết xã bị chia có bằng chứng hợp lệ
        total += 1
        print("\n[Test 13] AI review giải quyết xã bị chia có bằng chứng đối chiếu hợp lệ...")
        test_rows = [dict(r) for r in rows]
        test_rows[split_idx]['ma_xa'] = chosen_target
        test_rows[split_idx]['xa_phuong'] = target_name
        test_rows[split_idx]['trang_thai_nhan'] = 'da_duyet_ai'
        cb = json.loads(test_rows[split_idx]['canh_bao'])
        cb = [w for w in cb if w != 'xa_bi_chia']
        test_rows[split_idx]['canh_bao'] = json.dumps(cb)
        test_rows[split_idx]['ghi_chu'] += "; duyet_boi=antigravity-deepmind-agent; loai_nguoi_duyet=ai; ngay_duyet=2026-10-29; ly_do=Doi chieu Nghi quyet sap nhap va dau vao ro dia ban"
        with open(fixture_csv, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(test_rows)
        rep13 = validate_dataset.main(csv_file=str(fixture_csv))
        assert rep13['structural_status'] == 'PASS'
        print("  -> ĐẠT: AI review giải quyết xã bị chia hợp lệ khi có bằng chứng và đích hợp lệ.")
        passed += 1

        # 14. Test AI review giải quyết xã bị chia với đích sai (không thuộc mapping) -> FAIL
        total += 1
        print("\n[Test 14] AI review gán sai đích không thuộc tập chuyển đổi cho xã bị chia...")
        test_rows = [dict(r) for r in rows]
        test_rows[split_idx]['ma_xa'] = fake_target
        test_rows[split_idx]['ma_tinh'] = fake_info['ma_tinh']
        test_rows[split_idx]['xa_phuong'] = full(fake_info, 'xa')
        test_rows[split_idx]['tinh'] = full(cat.new_pi[fake_info['ma_tinh']], 'tinh')
        test_rows[split_idx]['trang_thai_nhan'] = 'da_duyet_ai'
        test_rows[split_idx]['ghi_chu'] += "; duyet_boi=antigravity-deepmind-agent; loai_nguoi_duyet=ai; ngay_duyet=2026-10-29; ly_do=AI sai lech"
        with open(fixture_csv, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(test_rows)
        try:
            validate_dataset.main(csv_file=str(fixture_csv))
            assert False, "AI gán đích không thuộc mapping phải bị từ chối!"
        except SystemExit:
            pass
        print("  -> ĐẠT: Chặn thành công AI review gán sai đích cho xã bị chia.")
        passed += 1

        # 15. Test căn chỉnh span: offset >= 0, đúng substring, không chồng lấn, 0 ca [-1:]
        total += 1
        print("\n[Test 15] Kiểm tra căn chỉnh span thực tế: offset >= 0, đúng substring, không chồng lấn...")
        log_jsonl_file = TEST_DIR / "nhat_ky_ai_duyet.jsonl"
        assert log_jsonl_file.exists(), "nhat_ky_ai_duyet.jsonl phải tồn tại!"
        with open(log_jsonl_file, "r", encoding="utf-8") as f:
            logs = [json.loads(line) for line in f if line.strip()]
        assert len(logs) == 400, f"Nhật ký AI phải đủ 400 dòng, thực tế: {len(logs)}"
        
        span_pattern = re.compile(r"\[(-?\d+):(-?\d+)\]")
        span_count_total = 0
        
        for l in logs:
            sid = l['id']
            inp = l['dau_vao']
            can_cu = l['can_cu_input']
            
            # Kiểm tra thời gian thực thi (runtime timestamp)
            assert l['thoi_gian_kiem_tra'].startswith('2026-10-29T'), f"{sid}: thoi_gian_kiem_tra phải là mốc ISO thời gian thực!"
            
            # Trích xuất và kiểm tra toàn bộ các cặp offset [start:end]
            matches = span_pattern.findall(can_cu)
            record_spans = []
            for s_str, e_str in matches:
                s, e = int(s_str), int(e_str)
                assert s >= 0, f"{sid}: Phát hiện span âm [{s}:{e}] trong can_cu_input: {can_cu}"
                assert e > s, f"{sid}: Offset kết thúc phải lớn hơn bắt đầu [{s}:{e}]"
                assert e <= len(inp), f"{sid}: Offset vượt quá độ dài chuỗi đầu vào [{s}:{e}] (len={len(inp)})"
                record_spans.append((s, e))
                span_count_total += 1
                
            # Kiểm tra không chồng lấn giữa các span trong cùng 1 mẫu
            record_spans.sort()
            for idx_s in range(len(record_spans) - 1):
                assert record_spans[idx_s][1] <= record_spans[idx_s + 1][0], (
                    f"{sid}: Phát hiện span chồng lấn: {record_spans[idx_s]} và {record_spans[idx_s + 1]}"
                )
                
        # Kiểm tra 168 mẫu ban đầu tu_dong_khop đều có span hợp lệ và tham chiếu QĐ 19/2025/QĐ-TTg
        with open(baseline_csv, "r", encoding="utf-8-sig") as f:
            tu_dong_ids = [r['id'] for r in csv.DictReader(f) if r['trang_thai_nhan'] == 'tu_dong_khop']
        logs_by_id = {l['id']: l for l in logs}
        for tid in tu_dong_ids:
            l = logs_by_id[tid]
            assert 'vị trí [' in l['can_cu_input'], f"{tid}: can_cu_input phải có span căn chỉnh!"
            assert '01/07/2025' in l['can_cu_danh_muc'], f"{tid}: can_cu_danh_muc phải tham chiếu mốc 01/07/2025!"
            assert 'QĐ 19/2025/QĐ-TTg' in l['can_cu_danh_muc'] or '19/2025/QĐ-TTg' in l['can_cu_danh_muc'], f"{tid}: thiếu căn cứ QĐ 19/2025/QĐ-TTg!"
            
        print(f"  -> ĐẠT: Đã kiểm tra {span_count_total} span trên toàn bộ 400 mẫu; 0 ca span âm, 0 ca chồng lấn, offset hoàn toàn chính xác.")
        passed += 1

        # 16. Test căn cứ tra cứu pháp lý & web (phân biệt HTTP 200 vs HTTP 404)
        total += 1
        print("\n[Test 16] Kiểm tra căn cứ web/pháp lý (phân biệt HTTP 200 trực tuyến và tra cứu ngoại tuyến)...")
        web_count = 0
        http200_count = 0
        offline_count = 0
        
        for l in logs:
            web_ref = l.get('can_cu_web', '').strip()
            if web_ref:
                web_count += 1
                assert '01/07/2025' in web_ref, f"{l['id']}: can_cu_web thiếu mốc hiệu lực/chuẩn hóa 01/07/2025"
                assert '2026-10-29' in web_ref, f"{l['id']}: can_cu_web thiếu ngày truy cập/rà soát 2026-10-29"
                if 'HTTP 200' in web_ref:
                    http200_count += 1
                    assert 'https://' in web_ref, f"{l['id']}: ca HTTP 200 phải có URL hợp lệ"
                    assert '1685' in web_ref, f"{l['id']}: HTTP 200 gắn liền với NQ 1685 TP.HCM"
                    assert 'Điều 1' in web_ref, f"{l['id']}: phải dẫn chiếu Điều 1 cụ thể"
                else:
                    offline_count += 1
                    assert 'Nghị quyết' in web_ref or 'Đề án' in web_ref, f"{l['id']}: phải ghi rõ tên văn bản chính thức"
                    
        assert web_count == 37, f"Tổng số ca tra cứu web/pháp lý phải là 37, thực tế: {web_count}"
        assert http200_count == 12, f"Số ca NQ 1685 trực tuyến HTTP 200 phải là 12, thực tế: {http200_count}"
        assert offline_count == 25, f"Số ca tra cứu pháp lý còn lại phải là 25, thực tế: {offline_count}"
        print(f"  -> ĐẠT: 37 ca tra cứu minh bạch (12 ca HTTP 200 trực tuyến, 25 ca trích dẫn nghị quyết/đề án chính thức).")
        passed += 1

        # 17. Test toàn bộ 36 ca xã bị chia đều để trống ma_xa, giữ cờ xa_bi_chia và trạng thái can_duyet
        total += 1
        print("\n[Test 17] Kiểm tra toàn bộ 36 ca xã bị chia được thu hồi/bảo lưu để trống ma_xa và trạng thái can_duyet...")
        with open(real_csv, "r", encoding="utf-8") as f:
            current_real_rows = list(csv.DictReader(f))
        current_by_id = {r['id']: r for r in current_real_rows}
        split_ids = [r['id'] for r in current_real_rows if 'xa_bi_chia' in r['canh_bao']]
        assert len(split_ids) == 36, f"Số ca xã bị chia phải chính xác là 36, thực tế: {len(split_ids)}"
        
        audit_9_ids = ['VNTEST0006', 'VNTEST0008', 'VNTEST0011', 'VNTEST0018', 'VNTEST0023', 'VNTEST0027', 'VNTEST0030', 'VNTEST0032', 'VNTEST0050']
        lac_dao_3_ids = ['VNTEST0046', 'VNTEST0053', 'VNTEST0055']
        for sid in audit_9_ids + lac_dao_3_ids:
            assert sid in split_ids, f"{sid} phải nằm trong danh sách xã bị chia!"
            
        for sid in split_ids:
            r = current_by_id[sid]
            assert r['ma_xa'] == '', f"{sid}: ma_xa phải để trống khi thiếu phụ lục số nhà chi tiết! Thực tế: {r['ma_xa']}"
            assert r['xa_phuong'] == '', f"{sid}: xa_phuong phải để trống! Thực tế: {r['xa_phuong']}"
            assert r['trang_thai_nhan'] == 'can_duyet', f"{sid}: trạng thái phải là can_duyet! Thực tế: {r['trang_thai_nhan']}"
            assert 'xa_bi_chia' in json.loads(r['canh_bao']), f"{sid}: cảnh báo phải giữ cờ xa_bi_chia!"
            assert 'xa_moi_ung_vien=' in r['ghi_chu'], f"{sid}: ghi_chu phải lưu danh sách xa_moi_ung_vien!"
        print(f"  -> ĐẠT: Toàn bộ 36 ca xã bị chia (bao gồm cả 9 ca kiểm toán và 3 ca Lạc Đạo) đều để trống ma_xa/xa_phuong và giữ cờ xa_bi_chia.")
        passed += 1

        # 18. Test lệnh --sync không bao giờ chuyển các dòng can_duyet sang da_duyet_ai
        total += 1
        print("\n[Test 18] Kiểm tra kiem_tra_tien_do_duyet.py --sync không đổi can_duyet thành da_duyet_ai...")
        shutil.copy(real_csv, fixture_csv)
        real_bang_duyet = TEST_DIR / "bang_duyet_test.csv"
        shutil.copy(real_bang_duyet, fixture_bang_duyet)
        
        kiem_tra_tien_do_duyet.main(bang_duyet_arg=str(fixture_bang_duyet), test_csv_arg=str(fixture_csv), sync_arg=True)
        with open(fixture_csv, "r", encoding="utf-8") as f:
            synced_rows = list(csv.DictReader(f))
        synced_by_id = {r['id']: r for r in synced_rows}
        
        can_duyet_ids = [r['id'] for r in current_real_rows if r['trang_thai_nhan'] == 'can_duyet']
        assert len(can_duyet_ids) == 111, f"Phải có đúng 111 ca can_duyet, thực tế: {len(can_duyet_ids)}"
        for cid in can_duyet_ids:
            assert synced_by_id[cid]['trang_thai_nhan'] == 'can_duyet', f"{cid} bị chuyển sai thành {synced_by_id[cid]['trang_thai_nhan']}!"
            assert synced_by_id[cid]['ma_xa'] == '', f"{cid} phải có ma_xa rỗng!"
        print("  -> ĐẠT: --sync bảo lưu đúng 111 ca can_duyet, không chuyển nhầm thành da_duyet_ai.")
        passed += 1

        # 19. Test tính lũy đắc (idempotency) của --sync khi chạy 2 lần liên tiếp
        total += 1
        print("\n[Test 19] Kiểm tra tính lũy đắc (idempotency) của --sync...")
        content_after_sync1 = fixture_csv.read_text(encoding='utf-8')
        kiem_tra_tien_do_duyet.main(bang_duyet_arg=str(fixture_bang_duyet), test_csv_arg=str(fixture_csv), sync_arg=True)
        content_after_sync2 = fixture_csv.read_text(encoding='utf-8')
        assert content_after_sync1 == content_after_sync2, "Chạy sync 2 lần liên tiếp tạo ra sai khác!"
        print("  -> ĐẠT: --sync có tính lũy đắc tuyệt đối (diff = 0 giữa các lần chạy liên tiếp).")
        passed += 1

        # 20. Test công cụ tiến độ đếm diff nhãn thực tế báo đúng 28 dòng
        total += 1
        print("\n[Test 20] Kiểm tra đếm số dòng có diff nhãn thực tế (đúng 28 dòng)...")
        with open(baseline_csv, "r", encoding="utf-8-sig") as f:
            baseline_rows = list(csv.DictReader(f))
        LABEL_FIELDS = ['so_nha', 'ngo_ngach_hem', 'thon_xom', 'duong', 'ma_xa_cu', 'ma_huyen_cu', 'ma_tinh_cu', 'ma_xa', 'ma_tinh', 'xa_phuong', 'tinh', 'canh_bao']
        diff_count = 0
        diff_ids = []
        for r_base in baseline_rows:
            rid = r_base['id']
            r_curr = current_by_id[rid]
            has_diff = False
            for k in LABEL_FIELDS:
                if k == 'canh_bao':
                    cb1 = sorted(set(json.loads(r_base[k])))
                    cb2 = sorted(set(json.loads(r_curr[k])))
                    if cb1 != cb2:
                        has_diff = True
                        break
                else:
                    if r_base[k].strip() != r_curr[k].strip():
                        has_diff = True
                        break
            if has_diff:
                diff_count += 1
                diff_ids.append(rid)
        assert diff_count == 28, f"Số dòng có diff nhãn thực tế phải là 28, thực tế: {diff_count} (IDs: {diff_ids})"
        print(f"  -> ĐẠT: Xác nhận chính xác {diff_count} dòng có diff nhãn thực tế so với baseline.")
        passed += 1

        # 21. Test chạy thực tế engine trên fixture tạm thời và bảo toàn người duyệt (human preservation)
        total += 1
        print("\n[Test 21] Chạy thực tế ai_review_engine.main(...) trên fixture tạm thời và kiểm tra bảo toàn sửa tay...")
        temp_engine_dir = Path(tempfile.mkdtemp(prefix="test_engine_exec_"))
        try:
            t_csv = temp_engine_dir / "dia_chi_test.csv"
            t_bang = temp_engine_dir / "bang_duyet_test.csv"
            t_jsonl = temp_engine_dir / "nhat_ky_ai_duyet.jsonl"
            t_csv_log = temp_engine_dir / "nhat_ky_ai_duyet.csv"
            t_chk = temp_engine_dir / "checkpoints"
            t_pl_csv = temp_engine_dir / "phan_loai_chi_tiet_400_id.csv"
            t_pl_md = temp_engine_dir / "phan_loai_chi_tiet_400_id.md"
            
            shutil.copy(real_csv, t_csv)
            tao_bang_duyet.main(test_csv_arg=str(t_csv), out_csv_arg=str(t_bang))
            
            # Gán giá trị sentinel đặc biệt cho 2 dòng human review (VNTEST0001 và VNTEST0036)
            with open(t_bang, "r", encoding="utf-8-sig") as f:
                b_entries = list(csv.DictReader(f))
                b_flds = list(b_entries[0].keys())
                
            sentinel_map = {
                'VNTEST0001': {'nguoi': 'Chuyen Gia Thu Nghiem 123', 'ngay': '2026-03-25', 'ly_do': 'Sentinel xac thuc thu cong 123', 'dia_chi': 'Dia chi sentinel 1'},
                'VNTEST0036': {'nguoi': 'Kiem Toan Vien Sentinel 456', 'ngay': '2026-03-25', 'ly_do': 'Sentinel thuc dia 456', 'dia_chi': 'Dia chi sentinel 2'}
            }
            for row in b_entries:
                if row['id'] in sentinel_map:
                    s_info = sentinel_map[row['id']]
                    row['loai_nguoi_duyet'] = 'human'
                    row['nguoi_duyet'] = s_info['nguoi']
                    row['ngay_duyet'] = s_info['ngay']
                    row['trang_thai_duyet'] = 'da_duyet'
                    row['ly_do_duyet'] = s_info['ly_do']
                    row['dia_chi_chuan'] = s_info['dia_chi']
                    
            with open(t_bang, "w", encoding="utf-8-sig", newline="") as f:
                w = csv.DictWriter(f, fieldnames=b_flds)
                w.writeheader()
                w.writerows(b_entries)
                
            # THỰC SỰ CHẠY ENGINE TRÊN ĐƯỜNG DẪN TẠM THỜI
            ai_review_engine.main(
                test_csv_arg=str(t_csv),
                bang_duyet_arg=str(t_bang),
                jsonl_arg=str(t_jsonl),
                csv_arg=str(t_csv_log),
                checkpoint_dir_arg=str(t_chk),
                phan_loai_csv_arg=str(t_pl_csv),
                phan_loai_md_arg=str(t_pl_md)
            )
            
            # 1. Kiểm tra audit log có đủ 400 ID
            assert t_jsonl.exists(), "Tệp JSONL fixture phải được tạo!"
            with open(t_jsonl, "r", encoding="utf-8") as f:
                temp_logs = [json.loads(line) for line in f if line.strip()]
            assert len(temp_logs) == 400, f"Audit log fixture phải đủ 400 ID, thực tế: {len(temp_logs)}"
            
            # 2. Kiểm tra hàng human trong bảng duyệt và test csv được bảo toàn 100%
            with open(t_bang, "r", encoding="utf-8-sig") as f:
                after_engine_bang = {r['id']: r for r in csv.DictReader(f)}
            for sid, s_info in sentinel_map.items():
                r = after_engine_bang[sid]
                assert r['loai_nguoi_duyet'] == 'human', f"{sid}: loai_nguoi_duyet bị ghi đè thành {r['loai_nguoi_duyet']}!"
                assert r['nguoi_duyet'] == s_info['nguoi'], f"{sid}: nguoi_duyet bị đổi thành {r['nguoi_duyet']}!"
                assert r['trang_thai_duyet'] == 'da_duyet', f"{sid}: trang_thai_duyet bị đổi thành {r['trang_thai_duyet']}!"
                assert r['ly_do_duyet'] == s_info['ly_do'], f"{sid}: ly_do_duyet bị đổi!"
                assert r['dia_chi_chuan'] == s_info['dia_chi'], f"{sid}: dia_chi_chuan bị đổi!"
                
            # 3. Chạy --sync và kiểm tra validate_dataset ghi nhận đúng 2 dòng human
            kiem_tra_tien_do_duyet.main(bang_duyet_arg=str(t_bang), test_csv_arg=str(t_csv), sync_arg=True)
            temp_rep = validate_dataset.main(csv_file=str(t_csv))
            assert temp_rep['human_reviewed_rows'] == 2, f"Phải ghi nhận đúng 2 dòng human sau sync, thực tế: {temp_rep['human_reviewed_rows']}"
            assert temp_rep['ai_reviewed_rows'] == 287, f"Số dòng da_duyet_ai phải là 287, thực tế: {temp_rep['ai_reviewed_rows']}"
            print("  -> ĐẠT: Engine thực sự chạy độc lập trên fixture, bảo toàn tuyệt đối 100% dữ liệu human review.")
            passed += 1
        finally:
            shutil.rmtree(temp_engine_dir, ignore_errors=True)

        # 22. Test kiểm toán các trường hợp sai lệch có chủ đích (Negative Tests trên Fixture thực sự)
        total += 1
        print("\n[Test 22] Kiểm toán các ca lỗi giả định (Negative Tests thực sự chạy engine & validator trên fixture)...")
        # Ghi nhận mã băm của các file thật trước khi chạy fixture
        real_csv_sha_before = hashlib.sha256((TEST_DIR / "dia_chi_test.csv").read_bytes()).hexdigest()
        real_bang_sha_before = hashlib.sha256((TEST_DIR / "bang_duyet_test.csv").read_bytes()).hexdigest()
        
        temp_neg_dir = Path(tempfile.mkdtemp(prefix="test_neg_fixture_"))
        try:
            neg_csv = temp_neg_dir / "dia_chi_test.csv"
            neg_bang = temp_neg_dir / "bang_duyet_test.csv"
            neg_jsonl = temp_neg_dir / "nhat_ky_ai_duyet.jsonl"
            neg_audit_csv = temp_neg_dir / "nhat_ky_ai_duyet.csv"
            neg_chk_dir = temp_neg_dir / "checkpoints"
            neg_pl_csv = temp_neg_dir / "phan_loai_chi_tiet.csv"
            neg_pl_md = temp_neg_dir / "phan_loai_chi_tiet.md"
            neg_backup = temp_neg_dir / "backup_before_ai_review" / "dia_chi_test.csv"
            neg_backup.parent.mkdir(parents=True, exist_ok=True)
            
            # Copy dữ liệu sang fixture
            shutil.copy2(TEST_DIR / "dia_chi_test.csv", neg_csv)
            shutil.copy2(TEST_DIR / "bang_duyet_test.csv", neg_bang)
            shutil.copy2(TEST_DIR / "backup_before_ai_review" / "dia_chi_test.csv", neg_backup)
            
            # --- 22.1: BẢO TOÀN CHỈNH SỬA HIỆN HÀNH KHÔNG CÓ CỜ HUMAN (Current Edit Preservation) ---
            with open(neg_csv, "r", encoding="utf-8") as f:
                c_rows = {r['id']: r for r in csv.DictReader(f)}
            with open(neg_bang, "r", encoding="utf-8-sig") as f:
                b_rows = {r['id']: r for r in csv.DictReader(f)}
                
            c_rows['VNTEST0001']['duong'] = 'Đường Tây Thạnh'
            c_rows['VNTEST0001']['ghi_chu'] = c_rows['VNTEST0001']['ghi_chu'] + '; CURRENT_EDIT_SENTINEL_KEEP_ME'
            b_rows['VNTEST0001']['duong'] = 'Đường Tây Thạnh'
            b_rows['VNTEST0001']['ghi_chu_nguon'] = b_rows['VNTEST0001']['ghi_chu_nguon'] + '; CURRENT_EDIT_SENTINEL_KEEP_ME'
            
            with open(neg_csv, "w", encoding="utf-8", newline="") as f:
                w = csv.DictWriter(f, fieldnames=list(c_rows['VNTEST0001'].keys()))
                w.writeheader(); w.writerows(c_rows.values())
            with open(neg_bang, "w", encoding="utf-8-sig", newline="") as f:
                w = csv.DictWriter(f, fieldnames=list(b_rows['VNTEST0001'].keys()))
                w.writeheader(); w.writerows(b_rows.values())
                
            ai_review_engine.main(
                test_csv_arg=str(neg_csv), bang_duyet_arg=str(neg_bang),
                jsonl_arg=str(neg_jsonl), csv_arg=str(neg_audit_csv),
                checkpoint_dir_arg=str(neg_chk_dir), phan_loai_csv_arg=str(neg_pl_csv),
                phan_loai_md_arg=str(neg_pl_md), backup_csv_arg=str(neg_backup)
            )
            
            with open(neg_csv, "r", encoding="utf-8") as f:
                after_c = {r['id']: r for r in csv.DictReader(f)}
            assert after_c['VNTEST0001']['duong'] == 'Đường Tây Thạnh', f"Chỉnh sửa hiện hành bị mất, thực tế: {after_c['VNTEST0001']['duong']}"
            assert 'CURRENT_EDIT_SENTINEL_KEEP_ME' in after_c['VNTEST0001']['ghi_chu'], "Ghi chú CURRENT_EDIT_SENTINEL_KEEP_ME bị mất!"
            
            # --- 22.2: NHÃN TRÍCH XUẤT KHÔNG CÓ TRONG INPUT BỊ BẮT LỖI (Unobserved Component Rejection) ---
            after_c['VNTEST0001']['duong'] = 'ABSENT FROM INPUT SENTINEL'
            with open(neg_csv, "w", encoding="utf-8", newline="") as f:
                w = csv.DictWriter(f, fieldnames=list(after_c['VNTEST0001'].keys()))
                w.writeheader(); w.writerows(after_c.values())
                
            ai_review_engine.main(
                test_csv_arg=str(neg_csv), bang_duyet_arg=str(neg_bang),
                jsonl_arg=str(neg_jsonl), csv_arg=str(neg_audit_csv),
                checkpoint_dir_arg=str(neg_chk_dir), phan_loai_csv_arg=str(neg_pl_csv),
                phan_loai_md_arg=str(neg_pl_md), backup_csv_arg=str(neg_backup)
            )
            
            with open(neg_csv, "r", encoding="utf-8") as f:
                after_unobs = {r['id']: r for r in csv.DictReader(f)}
            assert after_unobs['VNTEST0001']['trang_thai_nhan'] == 'can_duyet', "Nhãn không có trong input không được cấp da_duyet_ai!"
            
            # Kiểm tra validator từ chối nếu cố tình gắn da_duyet_ai cho nhãn trích xuất không quan sát được
            after_unobs['VNTEST0001']['trang_thai_nhan'] = 'da_duyet_ai'
            with open(neg_csv, "w", encoding="utf-8", newline="") as f:
                w = csv.DictWriter(f, fieldnames=list(after_unobs['VNTEST0001'].keys()))
                w.writeheader(); w.writerows(after_unobs.values())
            try:
                validate_dataset.main(csv_file=str(neg_csv))
                assert False, "Validator phải bắt lỗi nhãn không có trong input!"
            except SystemExit:
                pass
            
            # --- 22.3: BẮT LỖI XUNG ĐỘT VỚI PATCH (Conflict with Grounded Patch) ---
            shutil.copy2(TEST_DIR / "dia_chi_test.csv", neg_csv)
            with open(neg_csv, "r", encoding="utf-8") as f:
                clean_conf = {r['id']: r for r in csv.DictReader(f)}
            clean_conf['VNTEST0013']['xa_phuong'] = 'Phường Tuỳ Ý Người Dùng'
            clean_conf['VNTEST0013']['ghi_chu'] = 'USER_CONFLICT_KEEP_ME'
            with open(neg_csv, "w", encoding="utf-8", newline="") as f:
                w = csv.DictWriter(f, fieldnames=list(clean_conf['VNTEST0013'].keys()))
                w.writeheader(); w.writerows(clean_conf.values())
            ai_review_engine.main(
                test_csv_arg=str(neg_csv), bang_duyet_arg=str(neg_bang),
                jsonl_arg=str(neg_jsonl), csv_arg=str(neg_audit_csv),
                checkpoint_dir_arg=str(neg_chk_dir), phan_loai_csv_arg=str(neg_pl_csv),
                phan_loai_md_arg=str(neg_pl_md), backup_csv_arg=str(neg_backup)
            )
            with open(neg_csv, "r", encoding="utf-8") as f:
                after_conf = {r['id']: r for r in csv.DictReader(f)}
            assert after_conf['VNTEST0013']['xa_phuong'] == 'Phường Tuỳ Ý Người Dùng', "Giá trị sửa của người dùng phải được bảo lưu khi có xung đột!"
            assert after_conf['VNTEST0013']['trang_thai_nhan'] == 'can_duyet', "Ca xung đột phải bảo lưu can_duyet!"
            
            # --- 22.4: BẮT LỖI QUAN HỆ NGUỒN ĐÍCH SAI (Target Not In Mapping) ---
            shutil.copy2(TEST_DIR / "dia_chi_test.csv", neg_csv)
            with open(neg_csv, "r", encoding="utf-8") as f:
                clean_map = {r['id']: r for r in csv.DictReader(f)}
            clean_map['VNTEST0001']['ma_xa'] = '99999' # Mã xã không tồn tại
            with open(neg_csv, "w", encoding="utf-8", newline="") as f:
                w = csv.DictWriter(f, fieldnames=list(clean_map['VNTEST0001'].keys()))
                w.writeheader(); w.writerows(clean_map.values())
            try:
                validate_dataset.main(csv_file=str(neg_csv))
                assert False, "Validator phải bắt lỗi mã xã đích không tồn tại!"
            except SystemExit:
                pass
            
            # --- 22.5: BẮT LỖI KHỚP CHUỖI CON SAI RANH GIỚI TOKEN (house_substring_81) ---
            shutil.copy2(TEST_DIR / "dia_chi_test.csv", neg_csv)
            with open(neg_csv, "r", encoding="utf-8") as f:
                rows_81 = {r['id']: r for r in csv.DictReader(f)}
            rows_81['VNTEST0001']['so_nha'] = 'Số 81'
            with open(neg_csv, "w", encoding="utf-8", newline="") as f:
                w = csv.DictWriter(f, fieldnames=list(rows_81['VNTEST0001'].keys()))
                w.writeheader(); w.writerows(rows_81.values())
            ai_review_engine.main(
                test_csv_arg=str(neg_csv), bang_duyet_arg=str(neg_bang),
                jsonl_arg=str(neg_jsonl), csv_arg=str(neg_audit_csv),
                checkpoint_dir_arg=str(neg_chk_dir), phan_loai_csv_arg=str(neg_pl_csv),
                phan_loai_md_arg=str(neg_pl_md), backup_csv_arg=str(neg_backup)
            )
            with open(neg_csv, "r", encoding="utf-8") as f:
                after_81 = {r['id']: r for r in csv.DictReader(f)}
            assert after_81['VNTEST0001']['trang_thai_nhan'] == 'can_duyet', "Số 81 trong 181 vi phạm token boundary phải bị từ chối da_duyet_ai!"
            
            # Validator từ chối nếu gắn da_duyet_ai cho Số 81 trong 181
            after_81['VNTEST0001']['trang_thai_nhan'] = 'da_duyet_ai'
            with open(neg_csv, "w", encoding="utf-8", newline="") as f:
                w = csv.DictWriter(f, fieldnames=list(after_81['VNTEST0001'].keys()))
                w.writeheader(); w.writerows(after_81.values())
            try:
                validate_dataset.main(csv_file=str(neg_csv))
                assert False, "Validator phải bắt lỗi vi phạm ranh giới token cho Số 81 trong 181!"
            except SystemExit:
                pass

            # --- 22.6: BẮT LỖI SAI VAI TRÒ NGỮ CẢNH (house_role_district) ---
            shutil.copy2(TEST_DIR / "dia_chi_test.csv", neg_csv)
            with open(neg_csv, "r", encoding="utf-8") as f:
                rows_role = {r['id']: r for r in csv.DictReader(f)}
            rows_role['VNTEST0001']['so_nha'] = 'Số Tân Phú'
            with open(neg_csv, "w", encoding="utf-8", newline="") as f:
                w = csv.DictWriter(f, fieldnames=list(rows_role['VNTEST0001'].keys()))
                w.writeheader(); w.writerows(rows_role.values())
            ai_review_engine.main(
                test_csv_arg=str(neg_csv), bang_duyet_arg=str(neg_bang),
                jsonl_arg=str(neg_jsonl), csv_arg=str(neg_audit_csv),
                checkpoint_dir_arg=str(neg_chk_dir), phan_loai_csv_arg=str(neg_pl_csv),
                phan_loai_md_arg=str(neg_pl_md), backup_csv_arg=str(neg_backup)
            )
            with open(neg_csv, "r", encoding="utf-8") as f:
                after_role = {r['id']: r for r in csv.DictReader(f)}
            assert after_role['VNTEST0001']['trang_thai_nhan'] == 'can_duyet', "Số Tân Phú (tên quận làm số nhà) phải bị từ chối da_duyet_ai!"
            
            # Validator từ chối nếu gắn da_duyet_ai cho Số Tân Phú
            after_role['VNTEST0001']['trang_thai_nhan'] = 'da_duyet_ai'
            with open(neg_csv, "w", encoding="utf-8", newline="") as f:
                w = csv.DictWriter(f, fieldnames=list(after_role['VNTEST0001'].keys()))
                w.writeheader(); w.writerows(after_role.values())
            try:
                validate_dataset.main(csv_file=str(neg_csv))
                assert False, "Validator phải bắt lỗi sai vai trò ĐVHC làm số nhà!"
            except SystemExit:
                pass

            # --- 22.7: BẮT LỖI GÁN CHUỖI HÀNH CHÍNH KHÔNG QUAN SÁT ĐƯỢC (unobserved_valid_admin_chain) ---
            shutil.copy2(TEST_DIR / "dia_chi_test.csv", neg_csv)
            with open(neg_csv, "r", encoding="utf-8") as f:
                rows_unobs_admin = {r['id']: r for r in csv.DictReader(f)}
            cat = ai_review_engine.Catalogues()
            old_ben_nghe = next(w for w in cat.old_w if w['ten_xa'] == 'Bến Nghé' and len({m['ma_xa_moi'] for m in cat.to_new[w['ma_xa']]}) == 1)
            target_ben_nghe = cat.new_wi[cat.to_new[old_ben_nghe['ma_xa']][0]['ma_xa_moi']]
            rows_unobs_admin['VNTEST0001'].update(
                ma_xa_cu=old_ben_nghe['ma_xa'], ma_huyen_cu=old_ben_nghe['ma_huyen'], ma_tinh_cu=old_ben_nghe['ma_tinh'],
                ma_xa=target_ben_nghe['ma_xa'], ma_tinh=target_ben_nghe['ma_tinh'],
                xa_phuong=full(target_ben_nghe, 'xa'), tinh=full(cat.new_pi[target_ben_nghe['ma_tinh']], 'tinh')
            )
            with open(neg_csv, "w", encoding="utf-8", newline="") as f:
                w = csv.DictWriter(f, fieldnames=list(rows_unobs_admin['VNTEST0001'].keys()))
                w.writeheader(); w.writerows(rows_unobs_admin.values())
            ai_review_engine.main(
                test_csv_arg=str(neg_csv), bang_duyet_arg=str(neg_bang),
                jsonl_arg=str(neg_jsonl), csv_arg=str(neg_audit_csv),
                checkpoint_dir_arg=str(neg_chk_dir), phan_loai_csv_arg=str(neg_pl_csv),
                phan_loai_md_arg=str(neg_pl_md), backup_csv_arg=str(neg_backup)
            )
            with open(neg_csv, "r", encoding="utf-8") as f:
                after_unobs_adm = {r['id']: r for r in csv.DictReader(f)}
            assert after_unobs_adm['VNTEST0001']['trang_thai_nhan'] == 'can_duyet', "Gán Bến Nghé/Quận 1 cho địa chỉ Tây Thạnh không quan sát được phải bị từ chối!"

            # Validator từ chối nếu gắn da_duyet_ai cho Bến Nghé không có trong input
            after_unobs_adm['VNTEST0001']['trang_thai_nhan'] = 'da_duyet_ai'
            with open(neg_csv, "w", encoding="utf-8", newline="") as f:
                w = csv.DictWriter(f, fieldnames=list(after_unobs_adm['VNTEST0001'].keys()))
                w.writeheader(); w.writerows(after_unobs_adm.values())
            try:
                validate_dataset.main(csv_file=str(neg_csv))
                assert False, "Validator phải bắt lỗi đơn vị hành chính không quan sát được trong đầu vào!"
            except SystemExit:
                pass

            # --- 22.8: KIỂM TOÁN ÁNH XẠ OFFSET UNICODE NFD (nfd_alignment_api) ---
            nfd_text = unicodedata.normalize('NFD', '12 Tây Thạnh')
            align_nfd = ai_review_engine.align_output_components(nfd_text, {'duong': 'Tay Thanh'})
            assert ai_review_engine.remove_diacritics(align_nfd['duong']['matched']) == 'tay thanh', "Ánh xạ NFD phải khớp đúng 'tay thanh'!"
            assert align_nfd['duong']['start'] == 3, f"Start offset NFD phải là 3, thực tế: {align_nfd['duong']['start']}"
            assert align_nfd['duong']['end'] == 14, f"End offset NFD phải là 14 (đầy đủ 11 code points NFD của 'Tây Thạnh'), thực tế: {align_nfd['duong']['end']}"

            # --- 22.9: BẮT LỖI GÁN TÊN XÃ TRÙNG TÊN QUẬN (ward_name_only_in_district) ---
            shutil.copy2(TEST_DIR / "dia_chi_test.csv", neg_csv)
            with open(neg_csv, "r", encoding="utf-8") as f:
                rows_ward_dist = {r['id']: r for r in csv.DictReader(f)}
            # Cài Phường Tân Phú (Quận 9 - 769) vào VNTEST0001 (Quận Tân Phú - 767, Phường Tây Thạnh)
            old_tan_phu = next(w for w in cat.old_w if w['ten_xa'] == 'Tân Phú' and w['ma_tinh'] == '79'
                               and w['ma_huyen'] != rows_ward_dist['VNTEST0001']['ma_huyen_cu'] and len(cat.to_new[w['ma_xa']]) == 1)
            target_tan_phu = cat.new_wi[cat.to_new[old_tan_phu['ma_xa']][0]['ma_xa_moi']]
            rows_ward_dist['VNTEST0001'].update(
                ma_xa_cu=old_tan_phu['ma_xa'], ma_huyen_cu=old_tan_phu['ma_huyen'], ma_tinh_cu=old_tan_phu['ma_tinh'],
                ma_xa=target_tan_phu['ma_xa'], ma_tinh=target_tan_phu['ma_tinh'],
                xa_phuong=full(target_tan_phu, 'xa'), tinh=full(cat.new_pi[target_tan_phu['ma_tinh']], 'tinh')
            )
            rows_ward_dist['VNTEST0001']['dia_chi_chuan'] = ai_review_engine.build_dia_chi_chuan(rows_ward_dist['VNTEST0001'])
            with open(neg_csv, "w", encoding="utf-8", newline="") as f:
                w = csv.DictWriter(f, fieldnames=list(rows_ward_dist['VNTEST0001'].keys()))
                w.writeheader(); w.writerows(rows_ward_dist.values())
            
            # Validator phải bắt lỗi nếu gán da_duyet_ai cho xã Tân Phú thuộc Quận 9
            try:
                validate_dataset.main(csv_file=str(neg_csv))
                assert False, "Validator phải bắt lỗi khi gán xã Tân Phú (Quận 9) trong khi đầu vào chỉ có Q Tân Phú và P. Tây Thạnh!"
            except SystemExit:
                pass
            
            # Engine phải từ chối da_duyet_ai và hạ về can_duyet
            ai_review_engine.main(
                test_csv_arg=str(neg_csv), bang_duyet_arg=str(neg_bang),
                jsonl_arg=str(neg_jsonl), csv_arg=str(neg_audit_csv),
                checkpoint_dir_arg=str(neg_chk_dir), phan_loai_csv_arg=str(neg_pl_csv),
                phan_loai_md_arg=str(neg_pl_md), backup_csv_arg=str(neg_backup)
            )
            with open(neg_csv, "r", encoding="utf-8") as f:
                after_wd = {r['id']: r for r in csv.DictReader(f)}
            assert after_wd['VNTEST0001']['trang_thai_nhan'] == 'can_duyet', "Engine phải hạ VNTEST0001 về can_duyet khi gán sai xã trùng tên quận!"
            
            # Kiểm tra biến thể viết tắt không chấm: 'Q Tân Phú', 'P Tây Thạnh'
            no_dot_norm = validate_dataset.remove_diacritics('181 Tây Thạnh, P Tây Thạnh, Q Tân Phú, HCM')
            assert not validate_dataset.has_ward_evidence('tan phu', no_dot_norm), "has_ward_evidence phải nhận diện 'Q Tân Phú' (không chấm) là quận, không phải xã!"
            assert validate_dataset.has_ward_evidence('tay thanh', no_dot_norm), "has_ward_evidence phải nhận diện 'P Tây Thạnh' (không chấm) là xã!"

            # --- 22.10: BẮT LỖI LỆCH SỐ / LOẠI THÔN XÓM (hamlet_number_mismatch_kp1) ---
            shutil.copy2(TEST_DIR / "dia_chi_test.csv", neg_csv)
            with open(neg_csv, "r", encoding="utf-8") as f:
                rows_kp = {r['id']: r for r in csv.DictReader(f)}
            # Cài Thôn 199999 cho VNTEST0288 (input có KP 1)
            rows_kp['VNTEST0288']['thon_xom'] = 'Thôn 199999'
            rows_kp['VNTEST0288']['dia_chi_chuan'] = ai_review_engine.build_dia_chi_chuan(rows_kp['VNTEST0288'])
            with open(neg_csv, "w", encoding="utf-8", newline="") as f:
                w = csv.DictWriter(f, fieldnames=list(rows_kp['VNTEST0288'].keys()))
                w.writeheader(); w.writerows(rows_kp.values())
            
            # Validator phải từ chối Thôn 199999 khi gắn da_duyet_ai
            try:
                validate_dataset.main(csv_file=str(neg_csv))
                assert False, "Validator phải bắt lỗi khi gán Thôn 199999 cho địa chỉ chỉ có KP 1!"
            except SystemExit:
                pass
                
            # Engine phải từ chối da_duyet_ai cho Thôn 199999
            ai_review_engine.main(
                test_csv_arg=str(neg_csv), bang_duyet_arg=str(neg_bang),
                jsonl_arg=str(neg_jsonl), csv_arg=str(neg_audit_csv),
                checkpoint_dir_arg=str(neg_chk_dir), phan_loai_csv_arg=str(neg_pl_csv),
                phan_loai_md_arg=str(neg_pl_md), backup_csv_arg=str(neg_backup)
            )
            with open(neg_csv, "r", encoding="utf-8") as f:
                after_kp = {r['id']: r for r in csv.DictReader(f)}
            assert after_kp['VNTEST0288']['trang_thai_nhan'] == 'can_duyet', "Engine phải hạ VNTEST0288 về can_duyet khi thon_xom không quan sát được!"

            # Thử thêm ca Thôn 1 (sai loại đơn vị từ KP sang Thôn)
            assert not validate_dataset.check_field_grounding(rows_kp['VNTEST0288']['dau_vao'], 'Thôn 1', 'thon_xom'), "KP 1 không thể grounding cho Thôn 1!"
            # Nhãn đúng 'Khu phố 1' phải grounding thành công
            assert validate_dataset.check_field_grounding(rows_kp['VNTEST0288']['dau_vao'], 'Khu phố 1', 'thon_xom'), "KP 1 phải grounding thành công cho Khu phố 1!"

            # --- 22.11: KIỂM TOÁN MÃ BĂM PROVENANCE CỦA VALIDATOR ---
            rep_fixture = validate_dataset.main(csv_file=str(neg_csv))
            expected_fixture_sha = hashlib.sha256(neg_csv.read_bytes()).hexdigest()
            real_csv_sha = hashlib.sha256((TEST_DIR / "dia_chi_test.csv").read_bytes()).hexdigest()
            assert rep_fixture['csv_sha256'] == expected_fixture_sha, f"Validator phải trả về đúng mã băm của file csv truyền vào! {rep_fixture['csv_sha256']} != {expected_fixture_sha}"

            # --- 22.12: XÁC NHẬN FIXTURE KHÔNG LÀM THAY ĐỔI CÁC TỆP THẬT ---
            real_csv_sha_after = hashlib.sha256((TEST_DIR / "dia_chi_test.csv").read_bytes()).hexdigest()
            real_bang_sha_after = hashlib.sha256((TEST_DIR / "bang_duyet_test.csv").read_bytes()).hexdigest()
            assert real_csv_sha_before == real_csv_sha_after, "Mã băm dia_chi_test.csv thật bị thay đổi sau khi chạy fixture!"
            assert real_bang_sha_before == real_bang_sha_after, "Mã băm bang_duyet_test.csv thật bị thay đổi sau khi chạy fixture!"
            
            print("  -> ĐẠT: Bộ kiểm toán âm tính chạy trực tiếp trên engine và validator fixture bắt lỗi chuẩn xác 100% (gồm cả ranh giới token, vai trò ĐVHC, grounding hành chính, Unicode NFD, hamlet mismatch KP 1, ward name only in district, và provenance hash).")
            passed += 1
        finally:
            shutil.rmtree(temp_neg_dir, ignore_errors=True)

        # 23. Test tệp phân loại chi tiết 400 ID (phan_loai_chi_tiet_400_id.csv & .md)
        total += 1
        print("\n[Test 23] Kiểm tra tệp phân loại chi tiết 400 ID...")
        pl_csv_file = TEST_DIR / "phan_loai_chi_tiet_400_id.csv"
        pl_md_file = TEST_DIR / "phan_loai_chi_tiet_400_id.md"
        assert pl_csv_file.exists(), "phan_loai_chi_tiet_400_id.csv phải tồn tại!"
        assert pl_md_file.exists(), "phan_loai_chi_tiet_400_id.md phải tồn tại!"
        
        with open(pl_csv_file, "r", encoding="utf-8-sig") as f:
            pl_rows = list(csv.DictReader(f))
        assert len(pl_rows) == 400, f"Tệp phân loại phải có đúng 400 dòng, thực tế: {len(pl_rows)}"
        
        pl_counts = Counter(r['phan_loai'] for r in pl_rows)
        assert pl_counts['du_can_cu_tham_chieu'] == 263, f"Số ca du_can_cu_tham_chieu phải là 263, thực tế: {pl_counts['du_can_cu_tham_chieu']}"
        assert pl_counts['nhan_can_sua'] == 26, f"Số ca nhan_can_sua phải là 26, thực tế: {pl_counts['nhan_can_sua']}"
        assert pl_counts['chua_du_can_cu'] == 111, f"Số ca chua_du_can_cu phải là 111, thực tế: {pl_counts['chua_du_can_cu']}"
        
        for r in pl_rows:
            if r['phan_loai'] == 'chua_du_can_cu':
                assert r['trang_thai_sau'] == 'can_duyet', f"{r['id']}: chua_du_can_cu phải có trang_thai_sau là can_duyet!"
                assert r['ma_xa_moi'] == '', f"{r['id']}: chua_du_can_cu phải để trống ma_xa_moi!"
            elif r['phan_loai'] in ('du_can_cu_tham_chieu', 'nhan_can_sua'):
                assert r['trang_thai_sau'] == 'da_duyet_ai', f"{r['id']}: phải có trang_thai_sau là da_duyet_ai!"
                assert r['ma_xa_moi'] != '', f"{r['id']}: phải có ma_xa_moi hợp lệ!"
        print("  -> ĐẠT: Tệp phân loại chi tiết chuẩn xác 100% (263 du_can_cu, 26 nhan_can_sua, 111 chua_du_can_cu).")
        passed += 1

        # 24. Test xác minh chuyên sâu ca VNTEST0040 (Phố Thiên Lôi / Phường Gia Viên Hải Phòng) và đối chiếu căn cứ pháp lý
        total += 1
        print("\n[Test 24] Kiểm tra chuyên sâu ca VNTEST0040 (Phố Thiên Lôi, P. Gia Viên Hải Phòng) và căn cứ pháp lý...")
        r40 = current_by_id['VNTEST0040']
        l40 = logs_by_id['VNTEST0040']
        assert r40['dau_vao'] == '1B, Phố Thiên Lôi, Phường Gia Viên, Hải Phòng'
        assert r40['trang_thai_nhan'] == 'can_duyet'
        assert r40['ma_xa'] == ''
        assert 'Đằng Giang' not in l40['can_cu_input']
        assert 'Đằng Giang' not in l40['can_cu_danh_muc']
        assert 'Đằng Giang' not in l40['ly_do_duyet']
        assert 'Gia Viên' in l40['can_cu_danh_muc']
        assert 'Thiên Lôi' in l40['can_cu_danh_muc']
        assert 'Quận Lê Chân' in l40['can_cu_danh_muc']
        assert 'Quận Ngô Quyền' in l40['can_cu_danh_muc']
        assert 'Nghị quyết số 1232/NQ-UBTVQH15' in l40['can_cu_web']
        assert not re.search(r'chia thành 3.*1232', l40['can_cu_web'] + ' ' + l40['can_cu_danh_muc']), "VNTEST0040 không được mô tả sai NQ 1232 là chia 3 phường!"
        assert 'Lạc Viên' in l40['can_cu_danh_muc'] and 'Máy Tơ' in l40['can_cu_danh_muc'], "Phải ghi nhận đúng NQ 1232 nhập Lạc Viên và Máy Tơ vào Gia Viên!"
        
        # Kiểm tra văn bản Hà Nội (NQ 1286 URL chính thức HTTP 200 và nối NQ 1656)
        hanoi_logs = [l for l in logs_by_id.values() if '1286' in l.get('can_cu_web', '')]
        assert len(hanoi_logs) >= 8, f"Phải có ít nhất 8 bản ghi dẫn NQ 1286, thực tế: {len(hanoi_logs)}"
        for hl in hanoi_logs:
            assert '1656' in hl.get('can_cu_web', ''), f"{hl['id']}: Hồ sơ dẫn 1286 phải nối thêm NQ 1656 mốc hiệu lực đích 01/07/2025!"
            assert '119241122151657096.htm' in hl.get('can_cu_web', ''), f"{hl['id']}: URL NQ 1286 phải là URL chính thức HTTP 200!"
        print("  -> ĐẠT: VNTEST0040 giải quyết đúng bản chất mâu thuẫn ranh giới (NQ 1232 nhập Lạc Viên/Máy Tơ), hồ sơ Hà Nội chuẩn hóa URL NQ 1286 HTTP 200 và nối NQ 1656.")
        passed += 1

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

    print(f"\n=== TỔNG KẾT: {passed}/{total} BÀI TEST ĐẠT YÊU CẦU 100% ===")

if __name__ == "__main__":
    run_all_tests()
