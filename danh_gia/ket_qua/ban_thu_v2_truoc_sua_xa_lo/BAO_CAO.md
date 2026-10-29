# Thống kê bản thử pipeline dùng luật

Đo trên **1136 mẫu dev**, beam=40. Không dùng tập test cuối.

Đây là mức khớp với nhãn tham chiếu máy/tổng hợp, chưa phải độ chính xác thực tế đã được xác minh. So khớp bỏ khác biệt chữ hoa và khoảng trắng, vẫn giữ dấu.

## Kết quả từng trường

| Trường | Đúng / tổng | Khớp (%) | Nhãn khác rỗng | Đúng trong nhãn khác rỗng (%) |
|---|---:|---:|---:|---:|
| so_nha | 1084 / 1136 | 95.423 | 970 | 95.052 |
| ngo_ngach_hem | 1129 / 1136 | 99.384 | 129 | 100.0 |
| thon_xom | 1130 / 1136 | 99.472 | 23 | 91.304 |
| duong | 927 / 1136 | 81.602 | 1031 | 80.892 |
| ma_xa | 1059 / 1136 | 93.222 | 916 | 93.996 |
| ma_tinh | 1124 / 1136 | 98.944 | 1136 | 98.944 |
| xa_phuong | 1053 / 1136 | 92.694 | 916 | 93.341 |
| tinh | 1124 / 1136 | 98.944 | 1136 | 98.944 |
| dia_chi_chuan | 834 / 1136 | 73.415 | 1136 | 73.415 |

Khớp đồng thời 4 trường chi tiết và 2 mã hành chính: **839/1136 (73.856%)**. Chỉ số này bao gồm trường trống.

## Theo nguồn và loại biến thể

| Nhóm | Số mẫu | Khớp 6 trường (%) | Mã xã (%) | Mã tỉnh (%) | Đường (%) |
|---|---:|---:|---:|---:|---:|
| bien_the:chuan_day_du | 73 | 97.26 | 97.26 | 100.0 | 100.0 |
| bien_the:chuan_moc_moi | 17 | 82.353 | 82.353 | 100.0 | 100.0 |
| bien_the:doi_thu_tu | 73 | 97.26 | 97.26 | 100.0 | 100.0 |
| bien_the:doi_thu_tu_moc_moi | 17 | 82.353 | 82.353 | 100.0 | 100.0 |
| bien_the:khong_dau | 73 | 4.11 | 97.26 | 100.0 | 4.11 |
| bien_the:khong_dau_moc_moi | 17 | 0.0 | 82.353 | 100.0 | 0.0 |
| bien_the:loi_chinh_ta | 73 | 97.26 | 97.26 | 100.0 | 100.0 |
| bien_the:loi_chinh_ta_moc_moi | 17 | 82.353 | 82.353 | 100.0 | 100.0 |
| bien_the:ngo_ngach_hem | 73 | 97.26 | 97.26 | 100.0 | 100.0 |
| bien_the:ngo_ngach_moc_moi | 17 | 82.353 | 82.353 | 100.0 | 100.0 |
| bien_the:thieu_thanh_phan | 73 | 97.26 | 97.26 | 100.0 | 100.0 |
| bien_the:tron_moc_cu_moi | 73 | 98.63 | 98.63 | 100.0 | 100.0 |
| bien_the:viet_tat | 73 | 97.26 | 97.26 | 100.0 | 100.0 |
| bien_the:viet_tat_moc_moi | 17 | 82.353 | 82.353 | 100.0 | 100.0 |
| bien_the:xa_bi_chia_doi_thu_tu | 10 | 100.0 | 100.0 | 100.0 | 100.0 |
| bien_the:xa_bi_chia_khong_dau | 10 | 0.0 | 100.0 | 100.0 | 0.0 |
| bien_the:xa_bi_chia_loi_chinh_ta | 10 | 100.0 | 100.0 | 100.0 | 100.0 |
| bien_the:xa_bi_chia_ngo_ngach | 10 | 100.0 | 100.0 | 100.0 | 100.0 |
| bien_the:xa_bi_chia_thon_xom | 10 | 100.0 | 100.0 | 100.0 | 100.0 |
| loai_nhan:nhan_may | 400 | 57.0 | 89.0 | 97.0 | 72.0 |
| loai_nhan:tong_hop | 736 | 83.016 | 95.516 | 100.0 | 86.821 |
| nguon:danh_muc_hanh_chinh | 736 | 83.016 | 95.516 | 100.0 | 86.821 |
| nguon:osm_public | 400 | 57.0 | 89.0 | 97.0 | 72.0 |
| xa_bi_chia | 137 | 67.883 | 100.0 | 99.27 | 72.993 |

## Tốc độ và bộ nhớ

- Khởi tạo danh mục và trie: 0.162 giây.
- Một lượt pipeline tuần tự: 333.7 địa chỉ/giây; trung bình 2.997 ms; p50 2.843 ms; p95 4.670 ms; lớn nhất 20.352 ms.
- Working set sau khởi tạo: 55.406 MiB; sau chạy: 60.137 MiB; đỉnh tiến trình tính đến cuối lượt pipeline: 60.137 MiB.
- Thời gian pipeline không gồm ghi file, chuyển dataclass sang dict và phần chẩn đoán. RAM gồm cả trình đánh giá và dữ liệu/kết quả đang giữ; không phải dự toán máy chủ.

## Chẩn đoán

- Đích mã xã tham chiếu xuất hiện trong ứng viên: 903/916 (98.581%). Chưa phản ánh việc chọn đúng tổ hợp.
- Cảnh báo xã bị chia: TP=136, FP=2, FN=1; precision=98.551%, recall=99.27% so với nhãn tham chiếu.

- tham_chieu_trong_nhung_du_doan_co_xa: 22.
- co_ung_vien_nhung_khong_chot_dung: 42.
- khong_sinh_duoc_dich_xa_tham_chieu: 13.

## Khả năng căn chỉnh dữ liệu cho CRF

Kiểm tra vị trí nội dung của nhãn chi tiết trong token đầu vào, cho phép khác dấu và tiền tố chuẩn hóa. Chưa tạo nhãn BIO, chưa xác nhận ý nghĩa của nhãn. Một vị trí khớp không bảo đảm nhãn đúng.

| Trường | Một vị trí | Nhiều vị trí | Không tìm thấy |
|---|---:|---:|---:|
| so_nha | 962 | 6 | 2 |
| ngo_ngach_hem | 125 | 4 | 0 |
| thon_xom | 22 | 1 | 0 |
| duong | 1005 | 13 | 13 |

Có 41 mẫu có nội dung nhãn ở các trường khác nhau chồng token khi căn chỉnh duy nhất; cần xử lý trước khi tạo BIO.

## Giới hạn bản thử

- Luật tách chi tiết và trọng số xếp hạng đặt tay; chưa có CRF hoặc logistic regression đã huấn luyện.
- Chỉ tìm gần đúng một ký tự với tên hành chính có tiền tố; tên không tiền tố chưa có fuzzy đầy đủ.
- Không có từ điển đường/thôn để phục hồi dấu; tên không dấu được giữ và cảnh báo, nên có thể lệch nhãn tham chiếu có dấu.
- Đoạn có tiền tố đường/thôn được bảo vệ khỏi nhận nhầm là hành chính; địa chỉ thiếu dấu phân cách có thể làm bỏ sót tên hành chính ở cuối đoạn đó.
- Số nhà có '/' được giữ nguyên và cảnh báo, chưa tách thành nhà/ngõ khi thiếu căn cứ.
- Tỷ lệ theo trường có thể cao do nhiều nhãn trống; xem thêm tỷ lệ trên nhãn khác rỗng và kết quả theo nguồn.

## Tái lập và tệp đi kèm

- Input: `D:\nlp_chuan_hoa_dia_chi\data\train_dev\dev.csv`; SHA-256: `dbf4fd536accd05f7fbd716e2c1e7d83e7db20854b60cf0c78c2fc36d2087cfe`.
- `thong_ke.json`: đầy đủ chỉ số, môi trường, mã băm danh mục và cảnh báo.
- `du_doan.jsonl`: kết quả từng mẫu với dấu vết token/ký tự và thời gian.
- `loi_tung_truong.csv`: từng chênh lệch giữa dự đoán và nhãn tham chiếu, không tự kết luận bên nào sai.
- `can_chinh_nhan.csv`: kiểm tra khả năng căn chỉnh từng nhãn chi tiết.
- `code_sha256.json`: mã băm source của lần đo chưa commit.
- Mã băm input và sáu danh mục được kiểm tra lại sau lần đo; dữ liệu được bảo toàn trong suốt phép đo.
