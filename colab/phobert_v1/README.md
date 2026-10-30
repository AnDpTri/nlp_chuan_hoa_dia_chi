# Colab PhoBERT-base-v2 — gói training có cổng kiểm tra

**Mục tiêu:** huấn luyện bộ gán nhãn BIO *partial-supervision* từ dữ liệu Char-CNN v2, không dùng tập test cuối. Đây là **PhoBERT + token-classification head**; CHƯA phải CRF hoặc accuracy chuẩn hóa sáu trường. Việc tách bài toán thành 2 giai đoạn giúp ngăn CRF học nhầm nhãn hành chính yếu. Nếu tốt trên dev, huấn luyện ranker mới riêng sau.

**Tập nguồn:** `mo_hinh/thu_nghiem/char_v2_01/data/{train_cnn,dev_goc,dev_kho}.jsonl`; train/dev giữ nguyên các mặt nạ `allowed` theo từng ký tự. Bản tạo gói không đọc `data/test` hoặc các JSON báo cáo test. Không huấn luyện ranker trên dev.

**Chặn training nếu sai:**
1. SHA-256 của cả ba tập dữ liệu không đúng manifest; ID, văn bản, nhãn, offset, BIO schema sai hoặc train trùng dev theo ID, text, group.
2. Colab không có CUDA GPU.
3. Fast tokenizer và tokenizer PhoBERT chính thức mã hóa khác nhau.
4. PyVi không thể căn chỉnh chính xác hơn 1% số hàng (trường hợp hiếm được bảo toàn văn bản thô và ghi rõ số hàng fallback).
5. PhoBERT tokenizer subword gộp các thực thể với nhãn xung đột quá 1% tổng số subword; trên các subword xung đột, không bịa nhãn.
6. Địa chỉ vượt giới hạn 256 subword của PhoBERT; phải xử lý dữ liệu thay vì cắt âm thầm.

**Thuật toán nhãn:** ký tự có thể mang nhiều nhãn (`allowed`). Khi chuyển sang subword, quy đổi B/I sang vai trò để đối chiếu toàn bộ ký tự phủ bởi subword; B/I đầu subword được quyết định từ nhãn tại ký tự đầu. Lấy giao vai trò; không ép các vùng hành chính mơ hồ thành O hay tên xã cụ thể. Loss là `-log(sum P(tag thuộc tập được phép))`. Chỉ tính accuracy trên token có duy nhất một nhãn được phép; `dev_kho` đo **một lần sau** lựa chọn best checkpoint bằng `dev_goc`.

**Cách chạy:** mở `TRAIN_PhoBERT_Colab.ipynb` từ Drive bằng Google Colab, chọn GPU T4 (hoặc tốt hơn), chạy tuần tự. Bước smoke một epoch kiểm tra toàn đường dữ liệu trước khi chạy đầy đủ. Sau mỗi epoch, `runs/<run-id>/status.json` và `history.json` được cập nhật ngay trong Drive. Sau khi hoàn tất, thư mục `best_model/` chứa model và tokenizer; `summary.json` chứa dev metrics, `preflight.json` và `package_manifest.json` chứng minh nguồn dữ liệu.

**Không nên coi đây là thành công end-to-end** chỉ dựa vào token accuracy; sau Colab phải tích hợp decoder + danh mục + ranker cho PhoBERT, đối chứng exact sáu trường trên dev rồi mới chấm test 400.

**Bản quyền:** `vinai/phobert-base-v2` có giấy phép AGPL-3.0. Cần xem xét trước khi triển khai sản phẩm.

**Đề xuất Colab:** batch 8, accumulation 2, tối đa 6 epoch, early-stopping patience 2, LR 2e-5, seed 20261030. Có thể giảm batch xuống 4 nếu GPU thiếu VRAM. Mỗi lần chạy dùng thư mục mới; tuyệt đối không ghi đè kết quả cũ.
