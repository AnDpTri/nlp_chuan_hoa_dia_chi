# Sửa pipeline, giữ nguyên CNN/ranker

Khớp nhãn máy/tổng hợp trên dev đã dùng để phát triển, chưa phải gold độc lập.

| Tập | Cấu hình | Đúng / tổng | Khớp 6 trường | Được / mất so mốc | Mean / P95 ms |
|---|---|---:|---:|---:|---:|
| dev_goc | baseline | 893/1136 | 78.609% | 0/0 | 13.97/20.10 |
| dev_goc | ten_train | 941/1136 | 82.835% | 48/0 | 14.54/20.92 |
| dev_goc | bao_ve_duong | 893/1136 | 78.609% | 0/0 | 13.86/20.82 |
| dev_goc | ket_hop | 941/1136 | 82.835% | 48/0 | 14.08/21.29 |
| dev_kho | baseline | 280/464 | 60.345% | 0/0 | 17.01/38.16 |
| dev_kho | ten_train | 295/464 | 63.578% | 15/0 | 15.96/36.37 |
| dev_kho | bao_ve_duong | 281/464 | 60.560% | 1/0 | 15.33/35.63 |
| dev_kho | ket_hop | 296/464 | 63.793% | 16/0 | 15.67/35.50 |

## Kiểm soát phép thử

- Không train lại CNN/ranker, không đổi nhãn, snapshot hoặc train/dev. Baseline tái hiện nguyên output cũ.
- Từ điển có 1018 tên/tỉnh, chỉ từ 4841 mẫu train_cnn. Không đọc train_ranker để lập từ điển, không đọc test cuối.
- Tên từ nhãn train chưa phải danh mục chứng thực; thêm cảnh báo và provenance khi đổi. Tra theo tỉnh dự đoán, không lấy tỉnh từ reference.
- Giữ loại đường, không sửa dấu đã nhập, không đoán typo, không chọn khi trùng khóa khác tên. Dạng đầy đủ/viết tắt được đối chiếu riêng.
- bao_ve_duong là thí nghiệm loại ứng viên admin không tiền tố nằm hoàn toàn trong span đường có tiền tố; không mặc định bật.
- Mỗi sửa là tùy chọn; mặc định và model cũ được giữ để tái hiện. Dev đã dùng để phát triển nên điểm tăng chưa phải bằng chứng tổng quát hóa trên gold.
- Tốc độ cùng lượt chạy trên laptop, không so trực tiếp với CPU Colab. Không gồm nạp model và I/O.
- Output đầy đủ mỗi cấu hình nằm trong JSONL; thay_doi_tung_cau.csv/jsonl giữ mọi câu đổi, kể cả hồi quy. Code đo có snapshot và SHA-256.
