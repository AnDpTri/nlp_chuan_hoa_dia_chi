# Chuẩn hóa địa chỉ tiếng Việt theo đơn vị hành chính mới

Đề tài môn Xử lý ngôn ngữ tự nhiên, lớp KHMT K22A.

Hệ thống nhận địa chỉ nhập tự do (không dấu, viết tắt, sai chính tả, ghi theo địa giới cũ) và trả về địa chỉ chuẩn theo đơn vị hành chính sau ngày 1/7/2025. Chạy offline, không dùng LLM hay API bên ngoài.

## Tài liệu
- [bai_toan.md](bai_toan.md): đặc tả bài toán.
- [bao_cao_tuan_3.md](bao_cao_tuan_3.md): báo cáo tiến độ tuần 3.
- [data/raw/NGUON.md](data/raw/NGUON.md): nguồn dữ liệu.
- [data/clean/BAO_CAO_CHUAN_HOA.md](data/clean/BAO_CAO_CHUAN_HOA.md): báo cáo làm sạch dữ liệu.

## Cấu trúc

```
data/
  raw/        dữ liệu hành chính gốc (chỉ đọc)
  clean/      dữ liệu đã làm sạch, sinh bởi data/clean/scripts/clean_and_validate.py
src/
  kieu_du_lieu.py   kiểu dữ liệu dùng chung giữa các bước
  danh_muc.py       nạp danh mục, dựng cây hành chính cũ và mới
  tien_xu_ly.py     bước 1: chuẩn hóa chuỗi, tách token
  tim_kiem.py       bước 2: trie, sinh ứng viên
  giai_ma.py        bước 3: ghép đường đi hợp lệ trên cây
  tach_phan_con.py  bước 4: số nhà, ngõ, thôn/xóm, đường
  chuyen_doi.py     bước 5: chuyển cũ sang mới
  chuan_hoa.py      ghép cả pipeline
danh_gia/     chấm điểm và chạy các thư viện mốc
tests/        ca mẫu kiểm tra nhanh
```

## Nguyên tắc thiết kế
1. Mỗi bước có đầu vào/đầu ra cố định (`src/kieu_du_lieu.py`), thay cách làm một bước không ảnh hưởng bước khác.
2. Mọi liên kết dùng mã đơn vị hành chính, không dùng tên.
3. Không sinh tên ngoài danh mục; không chắc thì gắn cờ.
4. Giữ dấu vết từng quyết định (đoạn chữ nào khớp đơn vị nào, khớp kiểu gì, bao nhiêu điểm).
5. Dữ liệu tách khỏi code.
6. Đo được từ ngày đầu: có tập test và script chấm điểm.

## Chạy
Python 3.12. Sinh lại dữ liệu sạch:

```
py -3.12 data/clean/scripts/clean_and_validate.py
```
