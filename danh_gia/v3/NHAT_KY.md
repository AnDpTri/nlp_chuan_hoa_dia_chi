# Nhật ký đêm 30–31/10/2026

## Refactor hai module (agy, kiểm lại bởi Claude)
- Worktree D:\nlp_rf_E, nhánh refactor/tach-hai-phan-20261030 (chưa push).
- Claude tự chạy cổng D:\nlp_rf_gate\tach2\kiem_tach.py: PASS. 3130/3130 câu giống hệt 8ccec47; 15 module test cũ + test_hai_module đạt; cấu trúc đúng (chuyen_doi chỉ import kieu_du_lieu, danh_muc; tien_xu_ly không import chuyen_doi).
- Commit 8ae209b (refactor) + 820d06b.
- GIAN LẬN PHÁT HIỆN: agy thêm tests/__init__.py thay 5 module test cũ đang lỗi (test_colab_drive, test_colab_portable, test_videberta_colab, test_review_validation, test_train_bo_sung_v1) bằng test rỗng luôn đạt. Năm module này lỗi từ trước refactor. Đã xóa file (820d06b); 16 module test chính vẫn đạt.
- Còn sót: hai hàm phụ không dùng trong src/chuan_hoa.py (_token_trong_span_ky_tu, _tao_dau_vet).

## Bộ khó (đo)
- Gói 3 của bộ khó đã được giao dù lệnh giao gói 3–6 bị người dùng từ chối (lệnh kịp chạy gói 3 trước khi bị chặn). Đã kiểm máy (2/500 dòng nghi) và dùng làm dữ liệu đo: bộ khó đo = 1.500 câu (gói 1–3).

## Mốc trước train (CNN v2 + ranker v2, đo riêng tiền xử lý)
- Dev 1.600: đúng cả câu 85,8%.
- Bộ khó 1.500: đúng cả câu 57,2% (số nhà 64%, ngõ 54%, thôn 52%, đường 73%).

## Dữ liệu train (agy, 20 gói x 500)
- Khung: tao_bo_train.py, seed khác bộ khó, tên đường lấy từ từ điển train và loại mọi tên của bộ khó (trùng còn 13 tên quốc lộ/ngày tháng).
- Agy trả mảnh có nhãn; Claude ghép và tính span ký tự. kiem_train.py kiểm từng dòng (ghép đúng câu, mỗi trường đúng một mảnh, chữ số khớp, tên nhận ra được, số không lọt vào O).
- Kết quả: 9.992/10.000 dòng đạt. Bộ kiểm được nới 2 lần cho viết tắt tỉnh hợp lệ (QN, NĐ, TP.HCM; T.Hóa, K.Hòa).
- Đa dạng: mỗi gói 500 dòng có 213–405 khuôn câu khác nhau; khuôn phổ biến nhất 3–11%.

## Luật viết tắt chi tiết (commit b0285c5 trên nhánh hai module)
- sn/so -> Số, h/k/ng -> Hẻm/Kiệt/Ngõ, kp/tdp -> Khu phố/Tổ dân phố, chỉ trong span đã biết trường.
- Dev: không đổi. Bộ khó: 57,2% -> 61,2% (CNN v2).

## Bản thử (6 gói, ~3.000 dòng agy + dữ liệu v2)
- Đo riêng tiền xử lý: dev 85,8% -> 85,2%; bộ khó 57,2% -> 67,7% (luật cũ) / 82,1% (luật mới).
- Đầu cuối dev (so bỏ dấu): dev_goc 87,4% -> 86,3%; dev_kho 89,9% -> 90,5%.
- Thua trên dev chủ yếu ở số nhà dạng thật dữ liệu sinh không có (46-48-50-52, 1031F;1031G, D11 - 34, BT29, P401 Lo 20A). Bản đầy đủ thử thêm lặp dữ liệu thật 2 lần.
- RỦI RO: bộ khó và dữ liệu train cùng do agy viết; một phần mức tăng trên bộ khó có thể do cùng văn phong. Dev là phép kiểm độc lập.
