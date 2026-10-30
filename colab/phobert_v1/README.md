# Colab PhoBERT-base-v2 — gói V2 (sửa CUDA embedding index)

**Mục tiêu:** huấn luyện bộ gán nhãn BIO *partial-supervision* từ dữ liệu Char-CNN v2, không dùng tập test cuối. Đây là **PhoBERT + token-classification head**; CHƯA phải CRF hoặc accuracy chuẩn hóa sáu trường. Việc tách bài toán thành 2 giai đoạn giúp ngăn CRF học nhầm nhãn hành chính yếu. Nếu tốt trên dev, huấn luyện ranker mới riêng sau.

**Tập nguồn:** `mo_hinh/thu_nghiem/char_v2_01/data/{train_cnn,dev_goc,dev_kho}.jsonl`; train/dev giữ nguyên các mặt nạ `allowed` theo từng ký tự. Bản tạo gói không đọc `data/test` hoặc các JSON báo cáo test. Không huấn luyện ranker trên dev.

**Chặn training nếu sai:**
1. SHA-256 của cả ba tập dữ liệu không đúng manifest; ID, văn bản, nhãn, offset, BIO schema sai hoặc train trùng dev theo ID, text, group.
2. Colab không có CUDA GPU.
3. **V2:** kiểm tra ID trên **toàn bộ train/dev trước cả smoke**. Tokenizer fast có 66.119 ID nhưng backbone chỉ có 64.001 embedding; các ID ngoài khoảng được thay bằng `<unk>` (=3), tương tự tokenizer chậm chính thức, và báo thống kê. Bắt buộc dãy ID cuối cùng khớp PhoBERT tokenizer chậm **trên từng dòng train/dev**, và không có ID ngoài vùng embedding; sai thì dừng.
4. PyVi không thể căn chỉnh chính xác hơn 1% số hàng (trường hợp hiếm được bảo toàn văn bản thô và ghi rõ số hàng fallback).
5. PhoBERT tokenizer subword gộp các thực thể với nhãn xung đột quá 1% tổng số subword; trên các subword xung đột, không bịa nhãn.
6. Địa chỉ vượt giới hạn 256 subword của PhoBERT; phải xử lý dữ liệu thay vì cắt âm thầm.

**Thuật toán nhãn:** ký tự có thể mang nhiều nhãn (`allowed`). Khi chuyển sang subword, quy đổi B/I sang vai trò để đối chiếu toàn bộ ký tự phủ bởi subword; B/I đầu subword được quyết định từ nhãn tại ký tự đầu. Lấy giao vai trò; không ép các vùng hành chính mơ hồ thành O hay tên xã cụ thể. Loss là `-log(sum P(tag thuộc tập được phép))`. Chỉ tính accuracy trên token có duy nhất một nhãn được phép; `dev_kho` đo **một lần sau** lựa chọn best checkpoint bằng `dev_goc`.

**Cách chạy:** chỉ mở `TRAIN_PhoBERT_Colab.ipynb` trong thư mục Drive **`PhoBERT_Address_Colab_20261030_v2`**. Không chạy lại gói v1 (đã phát hiện CUDA device-side assert). Chọn GPU T4 (hoặc tốt hơn), chạy tuần tự. Bước smoke một epoch quét toàn bộ dữ liệu rồi cố ý đưa một ví dụ có ID trước đây ngoài miền embedding qua GPU. Sau mỗi epoch, `runs/<run-id>/status.json` và `history.json` được cập nhật ngay trong Drive. Sau khi hoàn tất, thư mục `best_model/` chứa model và tokenizer; `summary.json` chứa dev metrics, `preflight.json` và `package_manifest.json` chứng minh nguồn dữ liệu.

**Chẩn đoán lỗi v1:** bản v1 có lỗi CUDA khi gặp ID `65364` trong khi embedding tối đa `64000`. Sau thay bằng `<unk>`, đối chiếu tokenizer chậm đúng 5.768/5.768 train, 1.026/1.026 dev gốc và 464/464 dev khó; số token thay lần lượt 23, 1, 0. `best_model/token_id_policy.json` phải được thực hiện giống hệt trong suy luận CPU sau này. Đây là kiểm tra CPU, chưa chứng minh training GPU v2 chạy thành công.

**Không nên coi đây là thành công end-to-end** chỉ dựa vào token accuracy; sau Colab phải tích hợp decoder + danh mục + ranker cho PhoBERT, đối chứng exact sáu trường trên dev rồi mới chấm test 400.

**Bản quyền:** `vinai/phobert-base-v2` có giấy phép AGPL-3.0. Cần xem xét trước khi triển khai sản phẩm.

**Đề xuất Colab:** batch 8, accumulation 2, tối đa 6 epoch, early-stopping patience 2, LR 2e-5, seed 20261030. Có thể giảm batch xuống 4 nếu GPU thiếu VRAM. Mỗi lần chạy dùng thư mục mới; tuyệt đối không ghi đè kết quả cũ.
