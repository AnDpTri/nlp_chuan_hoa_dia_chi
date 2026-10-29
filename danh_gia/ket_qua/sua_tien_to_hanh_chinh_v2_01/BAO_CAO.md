# Sửa tiền tố hành chính và giữ lưới token gốc

Khớp nhãn máy/tổng hợp trên dev phát triển, chưa phải gold độc lập. Giữ nguyên model, ranker, từ điển và nhãn.

| Tập | Model | Đúng sau / tổng | % sau | Được / mất | Mean/P95 ms |
|---|---|---:|---:|---:|---:|
| dev_goc | cnn_ranker | 941/1136 | 82.835 | 0/0 | 27.52/46.75 |
| dev_goc | videberta_tay | 926/1136 | 81.514 | 0/0 | 118.58/163.34 |
| dev_kho | cnn_ranker | 337/464 | 72.629 | 4/0 | 28.00/55.67 |
| dev_kho | videberta_tay | 340/464 | 73.276 | 4/0 | 116.67/151.65 |

Baseline: bản sua_dinh_dang_v1_01 (CNN333/464, ViDeBERTa336/464 trên dev khó).
Giai đoạn chỉ thêm Telex tiền tố đã tăng CNN4 câu nhưng ViDeBERTa0; sau bổ sung lưới token gốc, cả hai tăng4 câu.
87 unit tests PASS, gồm tiền tố không phụ thuộc địa danh, ca không được sửa, số đứng một mình, chiếu offset NFD và không nhân đôi ứng viên.
Không đọc test cuối, không train/tune thêm. Đo hai cấu hình, không tự suy kết quả luật/CRF hoặc các biến thể ranker chưa chạy lại.
Output từng câu, latency, hash model/input và mọi thay đổi được lưu ở JSONL/thong_ke.json. Snapshot source và code_sha256.json khớp code lúc hoàn tất.
