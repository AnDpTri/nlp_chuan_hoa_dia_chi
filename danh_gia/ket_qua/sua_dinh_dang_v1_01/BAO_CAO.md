# Sửa định dạng tiền tố, giữ nguyên model

Khớp nhãn máy/tổng hợp trên dev đã dùng phát triển, không phải gold độc lập.

| Tập | Model | Đúng / tổng | % | Được / mất | Mean/P95 ms |
|---|---|---:|---:|---:|---:|
| dev_goc | cnn_ranker | 941/1136 | 82.835 | 0/0 | 16.13/25.97 |
| dev_goc | videberta_tay | 926/1136 | 81.514 | 0/0 | 102.83/129.92 |
| dev_kho | cnn_ranker | 333/464 | 71.767 | 37/0 | 22.51/47.41 |
| dev_kho | videberta_tay | 336/464 | 72.414 | 37/0 | 105.99/137.27 |

Không train/tune thêm, không đổi nhãn/dev/test/từ điển. Hash checkpoint và các file được ghim khớp trước/sau.
Thời gian là một lượt end-to-end cục bộ đã nạp model, không gồm I/O/JSON; tải nền có thể ảnh hưởng.
Mọi input/reference/output và latency ở bốn JSONL; mọi thay đổi sáu trường ở thay_doi_tung_cau.jsonl.
73 unit test liên quan đã PASS trước phép đo; kiểm tra thêm offset và span không chồng trong lúc đo.
