# Kết quả triển khai Char-CNN + CRF và LightGBM Ranker

Đã triển khai, huấn luyện và chạy toàn pipeline trên CPU. Tốc độ đủ nhẹ cho bản thử; chất lượng chưa vượt CRF cũ đồng đều. Mặc định vẫn giữ luật v3.

**Các tỷ lệ dưới đây là độ khớp nhãn máy/tổng hợp trên dev, chưa phải độ chính xác trên gold độc lập.**

## Huấn luyện

- CNN: 4,841 mẫu, 351,246 tham số, 12 vòng, **263.27 giây** trên 2 luồng CPU.
- Ranker: 1,129 nhóm từ phần train riêng, 27,730 giả thuyết; **19.18 giây** kể cả sinh đặc trưng.
- Chia theo họ che số nhà và ID mẫu cha; 0 nhóm giao giữa CNN và ranker, 0 họ che số nhà giao với dev đã kiểm tra.
- Không sinh thêm câu train, không dùng nhãn test cuối để train/tune/đo.
- Dữ liệu CNN và ranker không trùng nhóm nên CNN chỉ được học 4.841 mẫu, ít hơn CRF kết hợp 5.966 mẫu. Đây là đối chứng cả hệ thống, không phải so sánh encoder trên cùng số mẫu train.

## End-to-end sáu trường

| Tập | Luật v3 | CRF cũ kết hợp | CNN + điểm tay | CNN + ranker |
|---|---:|---:|---:|---:|
| dev_goc | 870/1136 (76.58%) | 895/1136 (78.78%) | 886/1136 (77.99%) | 893/1136 (78.61%) |
| dev_kho | 228/464 (49.14%) | 274/464 (59.05%) | 281/464 (60.56%) | 280/464 (60.34%) |

Ranker giúp dev gốc so với CNN dùng điểm tay, nhưng giảm nhẹ dev khó. So với CRF cũ, bản đầy đủ được thêm 20 ca/mất 22 ca ở dev gốc, thêm 10 ca/mất 4 ca ở dev khó. Chưa chọn nó làm bản mặc định.

## Từ nhận diện đến chọn kết quả

| Phép đo CNN + ranker | Dev gốc | Dev khó |
|---|---:|---:|
| F1 span chi tiết độc lập | 98.13% (1026 câu) | 98.76% (464 câu) |
| Mean riêng bộ nhận diện | 5.28 ms | 5.35 ms |
| Ứng viên chứa xã tham chiếu, khi nhãn xã có giá trị | 916/916 | 386/390 |
| Beam còn phương án đúng mã xã/tỉnh tham chiếu | 1135/1136 | 460/464 |
| Beam còn phương án khớp cả sáu trường | 928/1136 | 293/464 |
| Cuối cùng khớp cả sáu trường | 893/1136 | 280/464 |

F1 đo đúng ranh giới ký tự và loại thành phần, gồm tiền tố trong span. Dev khó không có nhãn ngõ/hẻm, nên không dùng tỷ lệ trường trống để kết luận nhận diện ngõ tốt. Hành chính chỉ có nhãn căn chỉnh yếu một phần; recall từng cấp ở thong_ke.json, không báo precision giả.

Trong tập phương án hiện có, ranker không thể vượt số ca mà beam còn giữ được đầy đủ sáu trường. Thiếu tên đường chuẩn, sai ranh giới và lỗi nhãn đều có thể làm mất phương án khớp; con số oracle này không xác định riêng từng nguyên nhân.

## Tốc độ CPU

| Chế độ | Dev gốc mean / P95 | Dev khó mean / P95 |
|---|---:|---:|
| luat_v3 | 4.86 / 7.20 ms | 7.43 / 29.07 ms |
| crf_cu | 10.63 / 16.76 ms | 12.36 / 34.18 ms |
| char_diem_tay | 14.89 / 22.11 ms | 16.62 / 37.78 ms |
| char_ranker | 15.70 / 23.46 ms | 17.38 / 39.34 ms |

Core end-to-end đã nạp mô hình, gồm neural/lookup/beam/ranker/trace; không gồm JSON, I/O, khởi tạo. Một lượt tuần tự, 10 câu train warm-up.

RAM suy luận tiến trình riêng sau nạp và 21 lần gọi: **249.9 MiB working set**, private committed 606.9 MiB. Khởi tạo kể cả import thư viện: 3.14 giây. Đây là Python + PyTorch + LightGBM + danh mục/trie/model, không phải chỉ file trọng số. Chưa đo cache sau chạy dài.

## Kiểm chứng và cách dùng

- 61 bài test đạt: CRF so với vét cạn, gradient nhãn một phần, padding, Unicode NFD/offset, cắt giữa token, train/load ranker, checksum và các hồi quy pipeline trước đó.
- Toàn bộ kết quả luật v3 và CRF cũ giữ nguyên trên 1.136 + 464 câu; so sánh tất cả trường kết quả, cảnh báo và dấu vết.
- Snapshot, train/dev gốc và sáu CSV danh mục giữ nguyên checksum.
- Chưa có danh mục đường chứng thực; chưa tự phục hồi dấu hoặc mở rộng viết tắt tên đường.
- Điểm neural/ranker chưa hiệu chỉnh thành xác suất; ngưỡng nhập nhằng cố định. Beam vẫn dùng điểm tay trước ranker.

Hướng dẫn chạy/train/API: docs/THU_NGHIEM_CHAR_CNN_V1.md. Checkpoint: mo_hinh/thu_nghiem/char_v1_01/char_cnn.pt và ranker.txt.

Dữ liệu kiểm chứng: thong_ke.json, KIEM_TRA.json, RAM_SUY_LUAN.json, kiem_thu.txt; JSONL chứa đầy đủ input/nhãn/output; so_sanh_loi.csv chứa các lỗi và thay đổi so với CRF; VI_DU_DUNG_SAI.json có ví dụ được thêm/mất khớp.
