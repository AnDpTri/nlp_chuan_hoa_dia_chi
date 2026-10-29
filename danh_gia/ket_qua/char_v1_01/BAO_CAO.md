# Thử nghiệm Char-CNN + CRF và LambdaRank

Độ khớp nhãn máy/tổng hợp trên dev, không phải độ chính xác gold.

| Tập | Chế độ | Khớp 6 trường | Mean ms | P95 ms |
|---|---|---:|---:|---:|
| dev_goc (1136) | luat_v3 | 76.585% | 5.24 | 8.31 |
| dev_goc (1136) | crf_cu | 78.785% | 10.16 | 15.89 |
| dev_goc (1136) | char_diem_tay | 77.993% | 14.04 | 20.34 |
| dev_goc (1136) | char_ranker | 78.433% | 14.84 | 21.61 |
| dev_kho (464) | luat_v3 | 49.138% | 7.28 | 28.80 |
| dev_kho (464) | crf_cu | 59.052% | 12.14 | 34.57 |
| dev_kho (464) | char_diem_tay | 60.560% | 16.46 | 39.54 |
| dev_kho (464) | char_ranker | 59.914% | 17.52 | 38.87 |

## Phạm vi

Core end-to-end đã nạp mô hình, gồm neural/lookup/beam/ranker/trace; không gồm JSON, I/O, khởi tạo. Một lượt tuần tự, 10 câu train warm-up.

- CNN và ranker dùng các họ train riêng; không fit hoặc chọn checkpoint bằng dev.
- Nhãn hành chính nhận diện là căn chỉnh yếu, chưa phải BIO được kiểm chứng ngữ nghĩa.
- Chưa có danh mục đường chứng thực; không tự phục hồi dấu hay mở rộng viết tắt tên đường.
- Điểm ranker và emission không phải xác suất; ngưỡng gần nhau 0.05 chưa hiệu chỉnh.
- Chi tiết từng tầng ở thong_ke.json; mọi input, nhãn, output ở JSONL; lỗi ở so_sanh_loi.csv.
- P95 đo cục bộ một lượt, không phải SLA web hoặc benchmark máy chủ chuyên dụng.
