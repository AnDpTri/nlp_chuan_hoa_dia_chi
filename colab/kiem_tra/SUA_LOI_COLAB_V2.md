# Khôi phục notebook và sửa gói Colab v2

Ngày 29/10/2026. Gói mới: `colab/dist/nlp_dia_chi_colab_v2.zip`.

## Đã sửa

- Lỗi gốc: manifest snapshot cũ lưu `clean\cu_huyen.csv` theo Windows.
  Hàm đọc manifest mới chuyển separator theo từng thành phần đường dẫn,
  dùng chung cho verify, train và đánh giá. Không sửa toàn cục hàm `digest`.
- Giữ nguyên 18 file snapshot và checksum dữ liệu; không bỏ bước kiểm tra.
  Manifest tạo mới từ nay lưu tên bằng `as_posix()`.
- Notebook dùng `run_visible`: stream stdout và stderr vào ô, đồng thời
  lưu log dưới `My Drive/nlp_chuan_hoa_dia_chi/logs/`. Lỗi vẫn ném ra để
  chặn bước tiếp; không còn trường hợp bắt lỗi rồi kết thúc ô bình thường.
- Gói v1 giữ nguyên. Gói v2 có manifest/checksum riêng, không vá trực tiếp
  file trong runtime rồi tự nhận là còn khớp gói cũ.
- Notebook trên Drive đã backup và được khôi phục từ mẫu sạch 19 ô, bỏ
  bốn ô vá/chẩn đoán thêm. Giữ ô cấu hình run đang có (5 epoch, batch 8,
  tích lũy gradient 2) và metadata của notebook để tiếp tục dùng link cũ.
- ZIP v2 đã được chép vào ổ Google Drive for desktop, kiểm SHA-256 trùng
  bản trong dự án. Không thao tác trình duyệt hoặc chạy train thay người dùng.

## Kiểm chứng

- 75 test cục bộ đạt, gồm hồi quy đường dẫn Windows/POSIX, từ chối path
  vượt root, stdout/stderr có trong notebook/log, exit code lỗi vẫn chặn,
  restore notebook có backup, và các test pipeline/neural trước đó.
- Giải nén chính ZIP v2 vào thư mục mới; verify gói và 75 test đều đạt.
- Kiểm tra 18 file snapshot ngay trong ZIP bằng tên POSIX và SHA-256:
  dữ liệu không thay đổi. Tập test cuối không có trong gói.
- Các ô mã notebook compile được; notebook trên Drive trỏ đúng ZIP v2.
- Đây là kiểm tra cục bộ CPU và cấu trúc tên file POSIX; chưa xác nhận
  lần chạy toàn bộ v2 trên runtime Colab/GPU và chưa có mô hình train xong.

Chi tiết: `BUNDLE_V2_KIEM_TRA.json`, `BUNDLE_V2_VERIFY.txt`,
`BUNDLE_V2_TESTS_75.txt`, `DRIVE_TRANSFER.json`.

## Tiếp tục trên Colab

1. Tải lại tab notebook để nhận bản mới từ Drive.
2. Kiểm tra mục 2 có tên `nlp_dia_chi_colab_v2.zip`, rồi chạy lại mục 2.
   Bước này giải nén mã sạch, thay các file runtime đã bị vá sai.
3. Chạy mục 3 rồi mục 4; chỉ tiếp tục khi verify và test hiện OK.
4. Sau đó chạy mục 5 và mục 6 để train. Nếu lỗi, log gốc đã hiện trong ô
   và được lưu trên Drive để đọc trực tiếp, không cần Gemini vá thêm.
