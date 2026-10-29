# Thử nghiệm CRF CPU: từ token đến end-to-end

**Đây là phép thử trên nhãn máy/tổng hợp đã đóng băng, không phải điểm test vàng.** Mặc định sản phẩm giữ luật v3. Không dùng GPU, không đọc test cuối.

## Dữ liệu và chất lượng nhãn

| Tập | Input | Qua lọc cơ học | Dùng | Token |
|---|---:|---:|---:|---:|
| train_goc | 4564 | 4199 | 3973 | 67866 |
| dev_goc | 1136 | 1026 | 1026 | 17395 |
| train_bo_sung | 2037 | 1993 | — | — |
| dev_kho | 464 | 452 | 452 | 7715 |
| train_ket_hop | — | — | 5966 | 102019 |

Nhãn máy/tổng hợp; các phép lọc cơ học không xác nhận ngữ nghĩa vàng.

Số họ input train/dev trùng sau lọc: 0. Phép kiểm này che span số nhà và chuẩn hóa chữ/dấu câu; không chứng minh độc lập về mọi nguồn/template.

## Huấn luyện CPU

| Mô hình | Mẫu | Token | Chuẩn bị feature (s) | Train (s) | Model (KiB) |
|---|---:|---:|---:|---:|---:|
| train_goc | 3973 | 67866 | 8.83 | 9.77 | 248.6 |
| train_ket_hop | 5966 | 102019 | 16.11 | 13.91 | 281.9 |

Cấu hình cố định: L-BFGS, c1=0.1, c2=0.1, tối đa 100 vòng, xét mọi chuyển nhãn. Không lấy dev làm dữ liệu fit/chọn siêu tham số.

## CRF đơn lẻ: token và span

| Mô hình | Tập | Mẫu | Token accuracy (%) | Non-O token F1 (%) | Span F1 (%) | Cả chuỗi BIO (%) |
|---|---|---:|---:|---:|---:|---:|
| train_goc | train_goc | 3973 | 100.0 | 100.0 | 100.0 | 100.0 |
| train_goc | dev_goc | 1026 | 99.442 | 98.868 | 98.78 | 97.173 |
| train_goc | dev_kho | 452 | 98.354 | 97.147 | 96.605 | 92.699 |
| train_ket_hop | train_ket_hop | 5966 | 99.999 | 99.998 | 99.991 | 99.983 |
| train_ket_hop | dev_goc | 1026 | 99.368 | 98.691 | 98.547 | 96.686 |
| train_ket_hop | dev_kho | 452 | 99.572 | 99.284 | 99.282 | 98.894 |

Span F1 yêu cầu đúng vai trò và cả hai ranh giới. Không biến nhiều token O thành bằng chứng hiệu quả; xem thêm non-O và từng trường. I mồ côi được đếm trước khi sửa để tạo span.

### Span theo trường trên dev khó

| Model | Trường | Nhãn hỗ trợ | Precision (%) | Recall (%) | F1 (%) |
|---|---|---:|---:|---:|---:|
| train_goc | so_nha | 452 | 98.681 | 99.336 | 99.008 |
| train_goc | ngo_ngach_hem | 0 | 0.0 | 0.0 | 0.0 |
| train_goc | thon_xom | 12 | 100.0 | 91.667 | 95.652 |
| train_goc | duong | 440 | 95.55 | 92.727 | 94.118 |
| train_ket_hop | so_nha | 452 | 100.0 | 100.0 | 100.0 |
| train_ket_hop | ngo_ngach_hem | 0 | 0.0 | 0.0 | 0.0 |
| train_ket_hop | thon_xom | 12 | 100.0 | 100.0 | 100.0 |
| train_ket_hop | duong | 440 | 98.194 | 98.864 | 98.528 |

Trường không có nhãn hỗ trợ không được coi F1=0 là bằng chứng model kém hoặc mọi trường trống là chính xác cao.

## Tích hợp pipeline: span, field, hành chính, địa chỉ

| Cấu hình | Tập | Span F1 (%) | Khớp 4 chi tiết (%) | 4 chi tiết bỏ khác dấu (%) | Mã xã (%) | Mã tỉnh (%) | Khớp 6 (%) |
|---|---|---:|---:|---:|---:|---:|---:|
| luat_v3 | dev_goc | 98.058 | 80.37 | 88.908 | 95.423 | 99.12 | 76.585 |
| luat_v3 | dev_kho | 93.995 | 51.293 | 65.948 | 92.672 | 100.0 | 49.138 |
| crf_train_goc_mo | dev_goc | 98.778 | 82.658 | 91.197 | 95.335 | 99.296 | 79.049 |
| crf_train_goc_mo | dev_kho | 96.605 | 58.836 | 74.138 | 92.672 | 100.0 | 56.466 |
| crf_ket_hop_mo | dev_goc | 98.674 | 82.306 | 90.845 | 95.423 | 99.296 | 78.785 |
| crf_ket_hop_mo | dev_kho | 99.282 | 61.638 | 77.371 | 92.672 | 100.0 | 59.052 |
| crf_ket_hop_bao_ve | dev_goc | 98.674 | 82.306 | 90.845 | 95.511 | 99.208 | 78.785 |
| crf_ket_hop_bao_ve | dev_kho | 99.282 | 61.638 | 77.371 | 92.672 | 100.0 | 59.052 |

Các mẫu span và mẫu end-to-end có thể khác số lượng. End-to-end dùng toàn bộ CSV tương ứng, có cả nhãn nghi vấn. Bốn trường chi tiết và sáu trường đều tính cả nhãn trống.

### Canonical được phép dùng trong dev khó

| Cấu hình | Mẫu | Khớp 6 (%) |
|---|---:|---:|
| luat_v3 | 434 | 52.535 |
| crf_train_goc_mo | 434 | 60.369 |
| crf_ket_hop_mo | 434 | 63.134 |
| crf_ket_hop_bao_ve | 434 | 63.134 |

Tập được gắn usable canonical vẫn chưa phải gold. Các mẫu ngoài tập này có viết tắt/mơ hồ chủ ý; không ép mô hình mở tên riêng theo nhãn ẩn.

## Thay đổi so với v3

| Cấu hình | Tập | Mới khớp | Mất khớp | Giữ khớp | Vẫn lệch |
|---|---|---:|---:|---:|---:|
| crf_train_goc_mo | dev_goc | 33 | 5 | 865 | 233 |
| crf_train_goc_mo | dev_kho | 43 | 9 | 219 | 193 |
| crf_ket_hop_mo | dev_goc | 33 | 8 | 862 | 233 |
| crf_ket_hop_mo | dev_kho | 46 | 0 | 228 | 190 |
| crf_ket_hop_bao_ve | dev_goc | 33 | 8 | 862 | 233 |
| crf_ket_hop_bao_ve | dev_kho | 46 | 0 | 228 | 190 |

## Hiệu năng

| Cấu hình | Tập | Mean (ms) | p95 (ms) | Địa chỉ/s | Mean ứng viên | Mean nhánh |
|---|---|---:|---:|---:|---:|---:|
| luat_v3 | dev_goc | 6.390 | 13.579 | 156.5 | 10.2 | 19.5 |
| luat_v3 | dev_kho | 8.271 | 34.594 | 120.9 | 8.6 | 17.0 |
| crf_train_goc_mo | dev_goc | 12.856 | 23.848 | 77.8 | 15.1 | 24.2 |
| crf_train_goc_mo | dev_kho | 15.724 | 41.234 | 63.6 | 16.3 | 23.9 |
| crf_ket_hop_mo | dev_goc | 13.997 | 27.096 | 71.4 | 15.1 | 24.2 |
| crf_ket_hop_mo | dev_kho | 15.883 | 45.829 | 63.0 | 16.3 | 23.9 |
| crf_ket_hop_bao_ve | dev_goc | 11.954 | 23.199 | 83.7 | 10.2 | 19.5 |
| crf_ket_hop_bao_ve | dev_kho | 13.650 | 37.604 | 73.3 | 8.6 | 17.0 |

Một lượt trên máy hiện tại, các cấu hình chạy tuần tự; latency chỉ gồm pipeline, không gồm chẩn đoán/ghi file. RAM trong JSON là toàn tiến trình đánh giá, không phải riêng model hoặc dự toán cloud.

## Đọc các mức đo

- Bộ sinh: candidate_target_recall trong JSON đo đích có mặt trong hợp các ứng viên, không bảo đảm có nhánh hợp lệ/chọn đúng.
- CRF đơn lẻ: đo nhãn vai trò trước khi gắn hành chính.
- Span pipeline: đo nhãn sau lựa chọn hành chính và formatter, có thể khác CRF đơn lẻ.
- Field: đo chuỗi chuẩn hóa, có thể lệch vì dấu, tiền tố hoặc loại dù span đúng.
- Mã và sáu trường: đo toàn tuyến; model tách tốt không bảo đảm xếp hạng/chuyển đổi đúng.

## Tệp kiểm chứng

- thong_ke.json: toàn bộ chỉ số theo lớp/nguồn/biến thể, cảnh báo, train time, RAM và hash.
- *_dev_*.jsonl: input/output và dấu vết đầy đủ cho từng cấu hình.
- so_sanh_*.csv: toàn input/output trước/sau/tham chiếu và từng trường lệch; xem cả ca tăng và giảm.
- Snapshot và *.crfsuite/*.json nằm trong thư mục thí nghiệm nêu trong JSON.

## Giới hạn

- Nhãn máy/tổng hợp, chưa phải gold ngữ nghĩa.
- Dev gốc và dev khó có liên quan nguồn; không cộng thành test độc lập.
- Span chỉ đo trên phần căn chỉnh được: báo riêng số mẫu và nhãn hỗ trợ.
- Chuẩn hóa đo cả dấu và loại; CRF không phục hồi tên riêng không có nguồn tra.
- Điểm ghép dùng marginal O và trọng số tay, chưa có mô hình xếp hạng học.
- CRF dự đoán độc lập một lần; từng nhánh hành chính ép token đã chọn về O, không phải giải mã CRF có ràng buộc tối ưu.
- Không chọn siêu tham số theo dev; bốn cấu hình được báo đầy đủ, không tự thay mặc định v3.
- Tập test cuối không được đọc hoặc dùng trong thí nghiệm.
