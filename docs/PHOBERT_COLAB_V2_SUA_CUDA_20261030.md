# Colab PhoBERT v2: phân tích CUDA assert và bàn giao (30-10-2026)

## Kết quả rà soát log Google Drive

- `G:\My Drive\PhoBERT_Address_Colab_20261030\runs\smoke_20261030T035130445957Z/status.json`: COMPLETE.
- `G:\My Drive\PhoBERT_Address_Colab_20261030\runs\phobert_base_v2_20261030T035505828734Z/status.json`: FAILED, `CUDA error: device-side assert triggered`.
- Smoke v1 chỉ dùng tám mẫu đầu và **không kiểm tra đầy đủ token ID**, nên không phát hiện tình huống hiếm.
- `vinai/phobert-base-v2` revision `86cd7fd`: tokenizer fast có 66.119 ID, embedding backbone cấu hình 64.001 ID. ID 65.364 trong train vượt giới hạn embedding.
- Với mẫu `VNTRAIN_00108`, fast ID 65.364 cho token tương ứng; tokenizer chậm chính thức cho ID 3 (`<unk>`). Nguyên nhân xác thực là **tokenizer fast và slow không nhất quán tại token hiếm**, dẫn đến chỉ số bất hợp lệ cho embedding GPU.

## Sửa bản v2

1. `train.py`: remap các ID ngoài `[0, vocab_size)` về `tokenizer.unk_token_id` (giá trị 3), kiểm tra số liệu và giới hạn OOV.
2. Sau remap, **đối chiếu toàn bộ dãy ID mỗi mẫu với tokenizer chậm chính thức**, sai bất kỳ dòng nào thì fail trước GPU.
3. Kiểm tra toàn bộ ba tập ngay cả khi chạy `--smoke`; chọn bảy mẫu đầu cùng một mẫu train từng có OOV để đảm bảo smoke kích hoạt chính nhánh lỗi.
4. Kiểm tra max/min IDs ngay trên CPU trong `collate`, trước chuyển GPU.
5. Ghi `best_model/token_id_policy.json` để pipeline suy luận CPU áp dụng **đúng cùng chính sách token ID**, không lặp lỗi embedding.
6. Dữ liệu train/dev, nhãn và checkpoint CNN cũ không bị thay đổi; không dùng test 400 để sửa mô hình.
7. Đã thêm unit tests cho remap token OOV, không hợp lệ `unk`, và BIO alignment.

## Kiểm tra trước bàn giao

- **6/6 bài test unit PASS**.
- **Toàn bộ train 5.768 mẫu**: 23 token OOV thuộc 22 dòng; sau remap có **5.768/5.768** mẫu khớp tokenizer chậm; 0 ID ngoài embedding.
- **Toàn bộ dev gốc 1.026 mẫu**: 1 token OOV, 1 dòng; khớp **1.026/1.026** tokenizer chậm.
- **Toàn bộ dev khó 464 mẫu**: 0 token OOV; khớp **464/464** tokenizer chậm.
- Xung đột subword train 9/100.967, dev 0; PyVi fallback train 47/5.768, dev gốc 5/1.026; dưới các ngưỡng đã thiết kế.
- **ZIP v2 CRC và SHA-256 sao chép trên ổ Drive PASS**, notebook và script cú pháp hợp lệ.
- **Chưa chạy GPU Colab với v2**: không có bảo đảm không còn lỗi phát sinh ở môi trường người dùng. Chỉ sau smoke v2 PASS mới chạy full training.

## Thư mục bàn giao

- Google Drive mount: `G:\My Drive\PhoBERT_Address_Colab_20261030_v2`
- Notebook mở trong Colab: `TRAIN_PhoBERT_Colab.ipynb`
- Dữ liệu và code: `PhoBERT_Colab_v2_20261030.zip`
- Chẩn đoán CPU: `PREFLIGHT_TOKEN_IDS_V2.json`
- Kết quả huấn luyện mới sẽ nằm trong `runs/` **bên trong folder v2**, tách khỏi log v1.
- Trước khi chạy v2 cần **Runtime → Restart session** để xóa trạng thái CUDA assert đã làm hỏng context GPU ở phiên v1; sau đó chọn T4 GPU và mở notebook v2.
- Không mở lại notebook v1, không ghi đè gói v1 hoặc thư mục `runs` cũ.

**Quan trọng:** Gói này huấn luyện PhoBERT token-classification với partial BIO loss, không phải CRF. Token accuracy ở dev không phải exact match địa chỉ chuẩn hóa; vẫn cần kiểm tra end-to-end sau khi tích hợp model.
