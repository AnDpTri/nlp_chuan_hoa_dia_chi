# Tài liệu Tích hợp PhoBERT-base-v2 vào Pipeline Chuẩn hóa Địa chỉ (30/10/2026)

## 1. Mục tiêu và Bối cảnh
- **Mục tiêu**: Tích hợp mô hình `vinai/phobert-base-v2` đã fine-tune vào pipeline chuẩn hóa địa chỉ như một bộ nhận diện thành phần (`bo_tach` của `BoChuanHoa`), thay thế hoặc bổ sung cho Char-CNN và ViDeBERTa.
- **Thư mục mô hình**: `G:\My Drive\PhoBERT_Address_Colab_20261030_v2\runs\phobert_base_v2_20261030T060548404237Z\best_model`.
- **Hợp đồng bộ nhận diện**: Có hàm `chuan_bi_chuoi(raw) -> NguCanhChar` trả về ngữ cảnh chứa token lưới, nhãn BIO hợp lệ và ma trận `log_probs` [ký tự, 15] hữu hạn.

## 2. Các thành phần đã triển khai

### a. `src/phobert.py`
1. **`segment_with_map(raw)`**:
   - Sử dụng `pyvi.ViTokenizer` với quy tắc căn chỉnh offset khớp hoàn toàn với `colab/phobert_v1/train.py::segment_with_map`.
   - Khi PyVi phát sinh lỗi lệch ký tự hoặc chèn underscore không khớp (raise `ValueError`), hàm tự động fallback an toàn về `(raw, [(i, i+1) for i in range(len(raw))], True)` đúng như `encode_one` lúc train.
2. **`encode_ids(text)`**:
   - Tokenize chuỗi NFC với PhoBERT tokenizer fast.
   - Áp dụng chính sách `token_id_policy.json`: Mọi token ID >= `vocab_size` (64.001) được thay bằng `tokenizer.unk_token_id` (= 3).
   - Kiểm soát độ dài đầu vào không vượt quá 256 subword.
3. **`BoTachPhoBERT(model_dir, threads=1, device='cpu')`**:
   - Thuộc tính định danh: `phien_ban = 'phobert_base_v2_v1'`, `ten_mo_hinh = 'phobert_base_v2'`, `bao_ve_chi_tiet = False`.
   - Tính mã băm `ma_bam`: SHA-256 tuần tự trên các file `model.safetensors`, `config.json`, `tokenizer.json`, `token_id_policy.json`.
   - Khởi tạo `LinearCRF` mặc định (ma trận chuyển trạng thái bằng 0, mặt nạ ràng buộc BIO hợp lệ).
   - Chạy suy luận hoàn toàn trên CPU dưới `torch.inference_mode()`.
4. **Chiếu subword xuống ký tự & Giải mã BIO**:
   - Chiếu log-softmax của từng subword xuống các ký tự trực tiếp hoặc ký tự phân cách/dấu câu thuộc về subword đó.
   - **Bảo toàn ranh giới thực thể**: Chỉ ký tự đầu tiên của subword giữ phân phối nhãn `B-<vai_tro>`; các ký tự tiếp theo trong cùng một subword dồn toàn bộ khối lượng xác suất từ `B-<vai_tro>` sang `I-<vai_tro>` thông qua phép `logaddexp`, sau đó sàn xác suất `B-` tại `-30.0`.
   - Dùng `LinearCRF.decode(char_log_probs)` để giải mã Viterbi mức ký tự, loại bỏ hoàn toàn các lỗi nhãn `I-` mồ côi.

### b. `src/__main__.py`
- Thêm cờ `--phobert-model` vào nhóm loại trừ nhau cùng `--char-model`, `--crf-model`, `--videberta-model`.
- Hỗ trợ cờ `--ranker` kết hợp với `--phobert-model`.
- Giữ nguyên toàn bộ hành vi và cấu hình của các cờ hiện có.

### c. `danh_gia/huan_luyen_xep_hang_phobert.py`
- Huấn luyện lại mô hình LightGBM LambdaRank trên tập `mo_hinh/thu_nghiem/char_v2_01/data/train_ranker.jsonl` (1.169 bản ghi độc lập, không trùng lặp với `train_cnn.jsonl`).
- Tuyệt đối không sử dụng `dev_goc` hay `dev_kho` để huấn luyện hoặc chọn tham số.
- Xuất kết quả tại:
  - `mo_hinh/thu_nghiem/phobert_v2_01/ranker.txt`
  - `mo_hinh/thu_nghiem/phobert_v2_01/ranker.json` (ghi nhận đúng `extractor_sha256 = BoTachPhoBERT.ma_bam` và `catalogue_sha256 = DanhMuc.ma_bam`, `close_margin = 0.05`)
  - `mo_hinh/thu_nghiem/phobert_v2_01/training.json`
- Đã xác thực khả năng nạp lại thành công bằng `BoXepHang(ranker_path, extractor_sha256, catalogue_sha256)`.

### d. `tests/test_phobert.py`
Bao gồm 5 bài kiểm thử đơn vị độc lập:
1. `test_segment_with_map_khop_train_py`: Đối chiếu khớp `segment_with_map` của `train.py` trên tập mẫu câu bình thường và ca gây `ValueError` (`108 Đ.TâySơn...`).
2. `test_encode_ids_oov_va_khong_vuot_vocab_size`: Kiểm tra xử lý token OOV từ câu thực tế trong `dev.csv` (`36B, Phố Mai Hắc Đế...`).
3. `test_chuan_bi_chuoi_bien_va_unicode_phan_ra`: Kiểm thử chuỗi rỗng `""`, chuỗi toàn dấu cách `"   "`, chuỗi 300 ký tự và chuỗi Unicode dạng phân rã NFD.
4. `test_hai_lan_goi_cung_ket_qua`: Kiểm tra tính tất định của bộ nhận diện qua 2 lần gọi độc lập.
5. `test_chieu_ky_tu_khong_vo_span`: Kiểm tra câu `"Số 12, Phố Hàng Bài, Hà Nội"` cho span đường là 1 span duy nhất không bị đứt đoạn theo ký tự.

## 3. Kiểm định & Nghiệm thu
- Toàn bộ các kiểm tra trong `phobert_contract.py` đạt `PASS` (`ok: true, failed: []`).
- 5/5 unit test trong `tests/test_phobert.py` đạt `OK`.
- 115/115 unit test nền của pipeline đạt `OK`.
