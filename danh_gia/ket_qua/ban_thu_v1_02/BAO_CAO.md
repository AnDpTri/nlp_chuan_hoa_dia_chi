# Thống kê bản thử pipeline dùng luật

Đo trên **1136 mẫu dev**, beam=40. Không dùng tập test cuối.

Đây là mức khớp với nhãn tham chiếu máy/tổng hợp, chưa phải độ chính xác thực tế đã được xác minh. So khớp bỏ khác biệt chữ hoa và khoảng trắng, vẫn giữ dấu.

## Kết quả từng trường

| Trường | Đúng / tổng | Khớp (%) | Nhãn khác rỗng | Đúng trong nhãn khác rỗng (%) |
|---|---:|---:|---:|---:|
| so_nha | 1084 / 1136 | 95.423 | 970 | 95.052 |
| ngo_ngach_hem | 1096 / 1136 | 96.479 | 129 | 97.674 |
| thon_xom | 1124 / 1136 | 98.944 | 23 | 82.609 |
| duong | 777 / 1136 | 68.398 | 1031 | 66.537 |
| ma_xa | 1032 / 1136 | 90.845 | 916 | 91.048 |
| ma_tinh | 1099 / 1136 | 96.743 | 1136 | 96.743 |
| xa_phuong | 1029 / 1136 | 90.581 | 916 | 90.721 |
| tinh | 1099 / 1136 | 96.743 | 1136 | 96.743 |
| dia_chi_chuan | 684 / 1136 | 60.211 | 1136 | 60.211 |

Khớp đồng thời 4 trường chi tiết và 2 mã hành chính: **685/1136 (60.299%)**. Chỉ số này bao gồm trường trống.

## Theo nguồn và loại biến thể

| Nhóm | Số mẫu | Khớp 6 trường (%) | Mã xã (%) | Mã tỉnh (%) | Đường (%) |
|---|---:|---:|---:|---:|---:|
| bien_the:chuan_day_du | 73 | 86.301 | 95.89 | 100.0 | 90.411 |
| bien_the:chuan_moc_moi | 17 | 58.824 | 70.588 | 88.235 | 82.353 |
| bien_the:doi_thu_tu | 73 | 86.301 | 95.89 | 100.0 | 90.411 |
| bien_the:doi_thu_tu_moc_moi | 17 | 58.824 | 70.588 | 88.235 | 82.353 |
| bien_the:khong_dau | 73 | 4.11 | 95.89 | 100.0 | 4.11 |
| bien_the:khong_dau_moc_moi | 17 | 0.0 | 82.353 | 100.0 | 0.0 |
| bien_the:loi_chinh_ta | 73 | 56.164 | 97.26 | 100.0 | 58.904 |
| bien_the:loi_chinh_ta_moc_moi | 17 | 0.0 | 76.471 | 94.118 | 0.0 |
| bien_the:ngo_ngach_hem | 73 | 86.301 | 95.89 | 100.0 | 90.411 |
| bien_the:ngo_ngach_moc_moi | 17 | 58.824 | 70.588 | 88.235 | 82.353 |
| bien_the:thieu_thanh_phan | 73 | 94.521 | 95.89 | 100.0 | 98.63 |
| bien_the:tron_moc_cu_moi | 73 | 86.301 | 95.89 | 97.26 | 90.411 |
| bien_the:viet_tat | 73 | 89.041 | 97.26 | 100.0 | 91.781 |
| bien_the:viet_tat_moc_moi | 17 | 70.588 | 82.353 | 100.0 | 82.353 |
| bien_the:xa_bi_chia_doi_thu_tu | 10 | 70.0 | 100.0 | 100.0 | 70.0 |
| bien_the:xa_bi_chia_khong_dau | 10 | 0.0 | 100.0 | 100.0 | 0.0 |
| bien_the:xa_bi_chia_loi_chinh_ta | 10 | 70.0 | 100.0 | 100.0 | 70.0 |
| bien_the:xa_bi_chia_ngo_ngach | 10 | 70.0 | 100.0 | 100.0 | 70.0 |
| bien_the:xa_bi_chia_thon_xom | 10 | 100.0 | 100.0 | 100.0 | 100.0 |
| loai_nhan:nhan_may | 400 | 45.5 | 85.75 | 93.0 | 60.25 |
| loai_nhan:tong_hop | 736 | 68.342 | 93.614 | 98.777 | 72.826 |
| nguon:danh_muc_hanh_chinh | 736 | 68.342 | 93.614 | 98.777 | 72.826 |
| nguon:osm_public | 400 | 45.5 | 85.75 | 93.0 | 60.25 |
| xa_bi_chia | 137 | 56.204 | 100.0 | 98.54 | 61.314 |

## Tốc độ và bộ nhớ

- Khởi tạo danh mục và trie: 0.163 giây.
- Một lượt pipeline tuần tự: 116.6 địa chỉ/giây; trung bình 8.575 ms; p50 6.709 ms; p95 21.207 ms; lớn nhất 70.906 ms.
- Working set sau khởi tạo: 55.316 MiB; sau chạy: 59.641 MiB; đỉnh tiến trình tính đến cuối lượt pipeline: 59.641 MiB.
- Thời gian pipeline không gồm ghi file, chuyển dataclass sang dict và phần chẩn đoán. RAM gồm cả trình đánh giá và dữ liệu/kết quả đang giữ; không phải dự toán máy chủ.

## Chẩn đoán

- Đích mã xã tham chiếu xuất hiện trong ứng viên: 902/916 (98.472%). Chưa phản ánh việc chọn đúng tổ hợp.
- Cảnh báo xã bị chia: TP=135, FP=2, FN=2; precision=98.54%, recall=98.54% so với nhãn tham chiếu.

- tham_chieu_trong_nhung_du_doan_co_xa: 22.
- co_ung_vien_nhung_khong_chot_dung: 68.
- khong_sinh_duoc_dich_xa_tham_chieu: 14.

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
