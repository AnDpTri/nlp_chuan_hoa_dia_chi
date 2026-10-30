# Gói huấn luyện PhoBERT-base-v2 trên Colab (30/10/2026)

## Kết quả bàn giao
- **Drive mount trên MSI:** `G:\My Drive\PhoBERT_Address_Colab_20261030`
- **Notebook:** `TRAIN_PhoBERT_Colab.ipynb`
- **Zip đóng băng:** `PhoBERT_Colab_v1_20261030.zip`
- **SHA-256 ZIP:** `aa7bdb65d38735cc582bd5899868c52e043dc9a81fb13a3091303f61fe262387`
- **Dung lượng ZIP:** 848.468 bytes.
- Đã kiểm tra hash **trên G: bằng cách đọc lại file sau khi sao chép**. Việc đồng bộ từ Google Drive Desktop lên cloud cần kiểm tra thêm qua giao diện Drive; chưa khẳng định file đã hiện trên cloud.
- **Nhánh cô lập:** `feature/pipeline-quality-isolated-20261030`, nguồn dữ liệu tại commit `ffe908b`. Không sửa nhánh gốc, test, model CNN hoặc ranker.

## Nguồn dữ liệu trong ZIP
- `train_cnn.jsonl`: **5.768** bản ghi, 0 chuỗi trùng bên trong split.
- `dev_goc.jsonl`: **1.026** bản ghi, 8 chuỗi trùng bên trong split được ghi nhận (không tự loại bỏ).
- `dev_kho.jsonl`: **464** bản ghi.
- Có SHA-256 riêng cho ba tập, đã qua kiểm tra NFC, length, offset span, nhãn cho phép, rò rỉ train/dev theo ID / nội dung / nhóm; không bao gồm test 400.
- Dữ liệu đến từ `mo_hinh/thu_nghiem/char_v2_01/data/` và không phải bộ `data/train_dev/train.csv` 4.564 hàng.

## Huấn luyện và các cửa chặn
1. Notebook mount Drive, unzip nguồn cố định, cài các phiên bản thư viện ghi trong `requirements.txt`.
2. Chạy `check_data.py`; bất kỳ hash mismatch hay train/dev leakage đều **dừng**.
3. Bắt buộc GPU CUDA, không âm thầm chuyển sang train CPU.
4. Nạp `vinai/phobert-base-v2` tại revision ghim `86cd7fd`. Đọc tokenizer.json bằng tokenizer fast để lấy offset; **đối chiếu ID với PhoBERT tokenizer chậm chính thức** trên các ví dụ. Nếu khác, dừng.
5. `pyvi` tách từ, căn chỉnh về ký tự gốc. Giữ nguyên text nếu PyVi không thể căn chỉnh; nếu tỉ lệ fallback vượt 1%, dừng. Nếu subword phủ nhiều vai trò mâu thuẫn vượt 1%, dừng. Không cắt input dài vượt 256 subwords.
6. Loss **partial BIO log-marginal**: không coi nhãn hành chính yếu là O và không ép thành một nhãn đơn lẻ. Đây là **PhoBERT + token-classification head**, chưa phải CRF. Bản đầu tiên phục vụ đo NER ổn định trước khi nối lại decoder/ranker.
7. Smoke: 8 train, 4 dev; 1 epoch. Chỉ sau khi smoke hoàn thành mới chạy tối đa 6 epochs, early stopping chọn trên `dev_goc`; `dev_kho` đánh giá đúng một lần cuối.
8. Sau mỗi epoch ghi `runs/<run-id>/history.json` và `status.json` trực tiếp vào Drive; xuất `best_model/`, `summary.json`, `preflight.json`.

## Những gì đã kiểm chứng
- Toàn bộ kiểm tra offline của `check_data.py` PASS.
- 3/3 unit tests căn chỉnh từ ký tự sang token (kể cả nhãn yếu và xung đột thực thể) PASS.
- ZIP CRC và SHA-256 sau sao chép sang ổ G: PASS.
- **Chưa chạy smoke hoặc full training trên Colab GPU**: việc đó cần người dùng mở notebook và quan sát. Không có tuyên bố accuracy PhoBERT hay chất lượng checkpoint nào khi chưa train.
- Điểm cuối cùng cần đo là exact sáu trường và chuẩn hóa chuỗi sau khi tích hợp PhoBERT vào cùng decoder, danh mục và ranker được train lại; NER token accuracy không phải endpoint.

## Cách bắt đầu
Mở Google Drive / My Drive / PhoBERT_Address_Colab_20261030 / TRAIN_PhoBERT_Colab.ipynb bằng Google Colab, chọn T4 GPU, chạy lần lượt từng ô. Nếu thiếu gói ZIP trên cloud thì kiểm tra trạng thái đồng bộ Drive Desktop của máy MSI trước khi mở notebook.

## Lưu ý pháp lý
PhoBERT-base-v2 dùng AGPL-3.0; xem xét nghĩa vụ giấy phép trước khi đưa vào sản phẩm đóng mã nguồn.
