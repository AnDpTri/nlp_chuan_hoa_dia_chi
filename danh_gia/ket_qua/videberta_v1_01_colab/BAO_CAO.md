# Thử nghiệm videberta và LambdaRank

Độ khớp nhãn máy/tổng hợp trên dev, không phải độ chính xác gold.

| Tập | Chế độ | Khớp 6 trường | Mean ms | P95 ms |
|---|---|---:|---:|---:|
| dev_goc (1136) | luat_v3 | 76.585% | 6.14 | 9.25 |
| dev_goc (1136) | crf_cu | 78.785% | 12.64 | 19.61 |
| dev_goc (1136) | videberta_diem_tay | 77.289% | 90.65 | 106.59 |
| dev_goc (1136) | videberta_ranker | 77.377% | 92.19 | 108.35 |
| dev_kho (464) | luat_v3 | 49.138% | 7.75 | 25.81 |
| dev_kho (464) | crf_cu | 59.052% | 13.87 | 33.96 |
| dev_kho (464) | videberta_diem_tay | 61.207% | 93.25 | 113.63 |
| dev_kho (464) | videberta_ranker | 60.776% | 94.86 | 117.18 |

## Phạm vi

Core end-to-end đã nạp mô hình, gồm neural/lookup/beam/ranker/trace; không gồm JSON, I/O, khởi tạo. Một lượt tuần tự, 10 câu train warm-up.

- Bộ nhận diện và ranker dùng các họ train riêng; không fit hoặc chọn checkpoint bằng dev.
- Nhãn hành chính nhận diện là căn chỉnh yếu, chưa phải BIO được kiểm chứng ngữ nghĩa.
- Chưa có danh mục đường chứng thực; không tự phục hồi dấu hay mở rộng viết tắt tên đường.
- Điểm ranker và emission không phải xác suất; ngưỡng gần nhau 0.05 chưa hiệu chỉnh.
- Chi tiết từng tầng ở thong_ke.json; mọi input, nhãn, output ở JSONL; lỗi ở so_sanh_loi.csv.
- P95 đo cục bộ một lượt, không phải SLA web hoặc benchmark máy chủ chuyên dụng.
