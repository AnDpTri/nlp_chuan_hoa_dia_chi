# Tích Hợp Mô Hình PhoBERT-base-v2 Vào Pipeline Chuẩn Hóa Địa Chỉ (2026-10-30)

## 1. Tổng Quan Kiến Trúc
Mô hình PhoBERT-base-v2 đã fine-tune từ Colab được tích hợp vào pipeline chuẩn hóa địa chỉ như một bộ nhận diện thành phần (`bo_tach` của `BoChuanHoa`), kế thừa đầy đủ hợp đồng giao tiếp chuẩn với pipeline:
- Nhận diện token/từ tố và xuất ngữ cảnh `NguCanhChar` (`src/ngu_canh_neural.py`).
- 15 nhãn BIO tương thích hoàn toàn với `src/nhan.py::TAGS`.
- Sử dụng suy luận trên CPU offline (`torch.inference_mode()`, hỗ trợ đa luồng qua tham số `threads`).

## 2. Chi Tiết Kỹ Thuật

### a. Tách Từ & Phân Giải Mapping (`segment_with_map`)
- Dùng `pyvi.ViTokenizer` với quy tắc ánh xạ chỉ số tương thích hoàn toàn với quá trình huấn luyện tại `colab/phobert_v1/train.py`.
- Khi PyVi thay đổi cấu trúc hoặc chèn gạch dưới không khớp khoảng trắng (`ValueError`), tự động kích hoạt cơ chế fallback bảo toàn ký tự gốc (`raw, [(i, i+1) for i in range(len(raw))], True`).

### b. Chính Sách ID Đầu Vào & Xử Lý OOV (`encode_ids`)
- PhoBERT tokenizer fast có tập từ vựng rộng (66.119 ID) trong khi embedding matrix của mô hình là 64.001 token.
- Mọi ID $\ge 64001$ (`vocab_size` lấy từ `config.json`) được thay thế bằng `unk_token_id` (= 3) theo đúng `token_id_policy.json`.

### c. Chiếu Xác Suất Từ Subword Xuống Ký Tự
- Mỗi ký tự trong chuỗi nhận phân phối xác suất `log_softmax` từ subword bao hàm nó. Các ký tự khoảng trắng hoặc dấu ngăn cách chưa được phủ sẽ nhận phân phối của subword liền trước.
- **Bảo toàn tính liên tục của thực thể (Anti-fragmentation)**:
  - Chỉ ký tự đầu tiên của mỗi subword giữ xác suất `B-<vai_tro>`.
  - Các ký tự tiếp theo trong cùng subword dồn toàn bộ xác suất từ `B-<vai_tro>` sang `I-<vai_tro>` thông qua toán tử `torch.logaddexp(I, B)`.
  - Giá trị xác suất `B-` của các ký tự tiếp theo được gán sàn hữu hạn (`-30.0`).
  - Toàn bộ ma trận log-probabilities được giới hạn chặt chẽ trong khoảng `[-30.0, 0.0]`, đảm bảo tính hữu hạn và không chứa NaN/Inf.

### d. Giải Mã Ràng Buộc BIO
- Sử dụng `LinearCRF` từ `src/char_cnn.py` khởi tạo mặc định (chuyển trạng thái 0, ma trận legal mask dựng sẵn) để chạy thuật toán Viterbi giải mã nhãn BIO hợp lệ cho từng chuỗi ký tự.

### e. Huấn Luyện Ranker Cho PhoBERT
- Triển khai kịch bản `danh_gia/huan_luyen_xep_hang_phobert.py` trích xuất đặc trưng giả thuyết trên tập `mo_hinh/thu_nghiem/char_v2_01/data/train_ranker.jsonl`.
- Đào tạo mô hình LightGBM LambdaRank (`ranker.txt`) cùng metadata (`ranker.json`, `training.json`) với `extractor_sha256` trùng khớp mã băm SHA-256 của các tệp trọng số/cấu hình PhoBERT (`BoTachPhoBERT.ma_bam`) và `catalogue_sha256` của `DanhMuc`.

## 3. Nghiệm Thu & Đánh Giá
- Kiểm thử đơn vị: 5 bài test trong `tests/test_phobert.py` bao phủ toàn diện:
  1. Tính tương thích của `segment_with_map` (kể cả trường hợp fallback).
  2. Chính sách remap ID ngoài phạm vi embedding matrix.
  3. Xử lý các chuỗi biên (chuỗi rỗng, khoảng trắng, chuỗi 300 ký tự, ký tự Unicode phân rã NFD).
  4. Tính tiền định (deterministic).
  5. Tính liên tục của span ký tự.
- Hợp đồng kiểm định độc lập qua `phobert_contract.py` đạt chuẩn `PASS` 100% các tiêu chí.
