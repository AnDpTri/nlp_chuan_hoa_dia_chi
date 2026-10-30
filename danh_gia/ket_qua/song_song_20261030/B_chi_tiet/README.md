# NHIỆM VỤ B: TÁCH SAI SPAN / FORMAT / TÊN CHUẨN / NHÃN NGHI VẤN

Thư mục bàn giao độc quyền của Phiên B trong đợt đánh giá song song ngày 30/10/2026.

## 1. Cấu Trúc Thư Mục
- `tach_loi_chi_tiet.py`: Mã nguồn thực thi toàn bộ quy trình đo đạc 4 vai trò span chi tiết, phân rã 112 ca lỗi chi tiết, đo các phép thử Oracle độc lập và trích xuất mẫu kiểm chứng.
- `so_lieu_chi_tiet.json`: Số liệu định lượng chi tiết dạng JSON (F1, Precision, Recall, Support, phân bố tầng lỗi, kết quả độc lập các phép oracle).
- `mau_kiem_chung_12_ca.json`: 17 ca kiểm chứng thực tế có đầy đủ input thô, ref 6 trường, span trích xuất, kết quả pipeline và phân tích nguyên nhân tầng lỗi kỹ thuật.
- `config.json`: Cấu hình tham số, hash model, danh mục và siêu dữ liệu môi trường (CPU 1 thread).
- `BAO_CAO.md`: Báo cáo kỹ thuật phân tích chuyên sâu chi tiết.

## 2. Cách Tái Lập Kết Quả
Chạy lệnh sau từ thư mục gốc dự án:
```powershell
.venv-neural\Scripts\python.exe danh_gia/ket_qua/song_song_20261030/B_chi_tiet/tach_loi_chi_tiet.py
```

Toàn bộ quá trình chạy mất khoảng 37–40 giây trên CPU 1 thread, kiểm tra toàn vẹn hash baseline manifest cả trước và sau khi thực hiện.
