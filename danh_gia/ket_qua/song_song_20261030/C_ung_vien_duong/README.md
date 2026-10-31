# Gói Thử Nghiệm Sinh Đa Ứng Viên Tên Đường (Candidate Generation Prototype)

**Phân vùng:** `danh_gia/ket_qua/song_song_20261030/C_ung_vien_duong/`  
**Ngày thực hiện:** 30/10/2026  
**Mục tiêu:** Bản thử nghiệm sinh đa phương án tên đường ($\le 8$ ứng viên) thuần quy tắc và lexicon lookup, không dùng/huấn luyện Transformer hay mô hình ngoài, chạy độc lập trên CPU 1 thread.

---

## 1. Thành Phần Mã Nguồn & Dữ Liệu

| Tệp tin | Vai trò |
|---|---|
| `prototype_sinh_ung_vien.py` | Module lõi sinh ứng viên tên đường (`BoSinhUngVienDuong`). Nhận `raw_text`, `tokens`, `spans`, `unknown`, `context_admin` và `TuDienDuong`. Hoàn toàn không nhận `ref`. |
| `test_fixtures_ung_vien.py` | Bộ kiểm thử fixtures độc lập kiểm chứng 6 nhóm trường hợp: dính từ, mở rộng unknown kế cận, NFD/NFC, viết tắt không dấu, bảo toàn mơ hồ, va chạm số nhà/đường. |
| `danh_gia_ung_vien.py` | Script đo lường đối chứng tự động trên Dev gốc (1.136 mẫu) và Dev khó frozen (464 mẫu) trên CPU 1 thread (`torch.set_num_threads(1)`). |
| `ket_qua_danh_gia.json` | Kết quả định lượng đầy đủ: Coverage@1..8, thời gian trễ CPU, phân tách theo độ phủ từ điển v5, delta hai chiều. |
| `thong_ke_ung_vien.json` | Danh sách chi tiết các ca Gained (+), Lost (-), Ambiguous (>1 ứng viên), và phân bố provenance. |
| `BAO_CAO.md` | Báo cáo nghiệm thu khoa học chi tiết theo chuẩn mực thực nghiệm. |

---

## 2. Kiến Trúc & Chiến Lược Sinh Ứng Viên

Module `BoSinhUngVienDuong` áp dụng 7 chiến lược độc lập:

1. **Surface Exact (`surface_exact`):** Trích xuất span đường từ mô hình trích xuất hiện hành, chuẩn hóa hiển thị qua `dinh_dang_span`. Luôn được bảo toàn để đảm bảo không bị hồi quy khi từ điển thiếu từ.
2. **Tách Marker Dính Chữ / Dính Số Nhà (`split_marker_canonical`, `split_marker_raw`):** Bóc tách các marker dính liền như `ĐườngPhạmVănThuận` -> `Phạm Văn Thuận`, `47/9ĐườngTrầnHưngĐạo` -> `Đường Trần Hưng Đạo`. Cứu 4 ca train đã biết mà không cần gọi mô hình phụ.
3. **Mở Rộng Unknown Kế Cận An Toàn (`boundary_expansion_canonical`):** Quét token unknown kế cận trước và sau span đường (không vượt qua dấu phân cách `, ; . -`), tra từ điển theo mã tỉnh để phục hồi span bị cắt cụt.
4. **Ghép Ranh Giới Số Nhà / Số Đường (`house_number_boundary_canonical`):** Xử lý ranh giới khi số nhà và đường chạm nhau ở các dạng ngày lễ/số hiệu (`30/4`, `1/5`).
5. **Canonical Names từ Từ Điển theo Context Admin (`admin_context_canonical`):** Tra cứu từ điển đường v5 theo mã tỉnh. Nếu có nhiều hơn 1 đường khớp khóa (ví dụ viết tắt hoặc không dấu mơ hồ), bảo toàn toàn bộ danh sách ứng viên, không đoán mò.
6. **Quét Cụm Unknown khi Span Đường Rỗng (`unknown_cluster_canonical`):** Khi mô hình không phát hiện được span đường nào, quét các n-gram unknown liên tiếp (độ dài 1..6) đối chiếu từ điển theo tỉnh.
7. **Empty Fallback (`empty_fallback`):** Trả về chuỗi rỗng `""` khi span đường trống hoặc nghi ngờ nhiễu, cho phép ranker có phương án bỏ chọn đường khi địa chỉ thực tế không có tên đường.

---

## 3. Hướng Dẫn Tái Hiện Kết Quả

Chạy trong môi trường ảo của dự án:

```powershell
# Chạy bộ kiểm thử fixtures
& "D:\nlp_chuan_hoa_dia_chi\.venv-neural\Scripts\python.exe" D:/nlp_chuan_hoa_dia_chi/danh_gia/ket_qua/song_song_20261030/C_ung_vien_duong/test_fixtures_ung_vien.py

# Chạy đo lường đối chứng trên Dev gốc (1.136) và Dev khó (464)
& "D:\nlp_chuan_hoa_dia_chi\.venv-neural\Scripts\python.exe" D:/nlp_chuan_hoa_dia_chi/danh_gia/ket_qua/song_song_20261030/C_ung_vien_duong/danh_gia_ung_vien.py
```
