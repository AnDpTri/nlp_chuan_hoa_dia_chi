# Chuẩn hóa địa chỉ tiếng Việt theo đơn vị hành chính mới

Đề tài môn Xử lý ngôn ngữ tự nhiên, lớp KHMT K22A.

Hệ thống nhận địa chỉ nhập tự do (không dấu, viết tắt, sai chính tả, ghi theo địa giới cũ) và trả về địa chỉ chuẩn theo đơn vị hành chính sau ngày 1/7/2025. Chạy offline, không dùng LLM hay API bên ngoài.

## Tài liệu

- [Sửa lõi với CNN giữ nguyên](docs/SUA_PIPELINE_CNN_V1.md): tra tên từ train và bảo vệ ranh giới đường; dev gốc 82,835%, dev khó 63,793%, có output đối chứng từng câu.
- [Kết quả ViDeBERTa trên Colab](danh_gia/ket_qua/videberta_v1_01_colab/TONG_KET.md): đã train 5 epoch trên T4, kiểm checksum và đối chiếu output; chưa vượt CRF/CNN đồng đều. [Hướng dẫn chạy lại](colab/README.md).
- [Mục lục toàn bộ báo cáo và kết quả kiểm chứng](docs/MUC_LUC_BAO_CAO.md): báo cáo thuật toán, train, số đo, output và audit dữ liệu; toàn bộ gói bàn giao đã lưu trong dự án.
- [docs/THU_NGHIEM_CHAR_CNN_V1.md](docs/THU_NGHIEM_CHAR_CNN_V1.md): Char-CNN + CRF bảy vai trò và LightGBM Ranker chạy CPU, checkpoint, cách train/chạy/đo và giới hạn.
- [docs/THU_NGHIEM_CRF_V1.md](docs/THU_NGHIEM_CRF_V1.md): đã train hai CRF CPU, thống kê từ token/span đến end-to-end, ca thoái lui và giới hạn nhãn. Mặc định vẫn giữ luật v3.
- [docs/SUA_LOI_PIPELINE_V3.md](docs/SUA_LOI_PIPELINE_V3.md): sửa lỗi theo chẩn đoán, kết quả v2 → v3 và ca mất khớp cần lưu ý.
- [docs/HOP_DONG_NHAN_CHUAN_HOA.md](docs/HOP_DONG_NHAN_CHUAN_HOA.md): phân biệt span quan sát, tên chuẩn và các kết quả chưa đủ căn cứ.
- [docs/HUONG_DAN_BAN_THU.md](docs/HUONG_DAN_BAN_THU.md): chạy pipeline dùng luật, đo trên dev và đọc thống kê trước khi huấn luyện mô hình.
- [docs/THIET_KE_LOI.md](docs/THIET_KE_LOI.md): pipeline lõi, mô hình dự kiến và thứ tự triển khai.
- [bai_toan.md](bai_toan.md): đặc tả bài toán.
- [bao_cao_tuan_3.md](bao_cao_tuan_3.md): báo cáo tiến độ tuần 3.
- [Hướng dẫn gửi yêu cầu vào Antigravity và kiểm chứng](docs/antigravity_rpc/HUONG_DAN_AGY_APP_RPC.md): lệnh dùng lại, script và biên nhận đối chiếu.
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
Python 3.12. Bản thử dùng thư viện chuẩn, chạy từ thư mục gốc dự án:

```powershell
py -3.12 -X utf8 -B -m src 'Số 12, Phường Trúc Bạch, Quận Ba Đình, Hà Nội'
py -3.12 -X utf8 -B -m danh_gia.chay_ban_thu --output-dir danh_gia/ket_qua/lan_do_moi
```

Thư mục kết quả phải chưa tồn tại. Bản mặc định: [báo cáo v3](danh_gia/ket_qua/ban_thu_v3_cuoi/BAO_CAO.md), [so sánh v2 → v3](danh_gia/ket_qua/ban_thu_v3_cuoi/SO_SANH.md). Đã có [thử nghiệm CRF CPU](danh_gia/ket_qua/crf_v1_01/BAO_CAO.md) qua `--crf-model` và [Char-CNN + CRF cùng LightGBM Ranker](docs/THU_NGHIEM_CHAR_CNN_V1.md) qua `--char-model`/`--ranker`. Chỉ đo dev, không dùng tập test cuối đang được rà soát.

Chạy mô hình CRF đã train (thư viện tùy chọn, cài trong môi trường riêng):

```powershell
.\.venv-crf\Scripts\python.exe -X utf8 -B -m src 'Số 12, Đường Lê Lợi, Phường Trúc Bạch, Quận Ba Đình, Hà Nội' --crf-model mo_hinh/thu_nghiem/crf_v1_01/train_goc.crfsuite
```

Xem hướng dẫn tạo môi trường và giới hạn ở tài liệu thử nghiệm CRF; không tự thay v3 chỉ theo mức khớp nhãn máy.

Sinh lại dữ liệu sạch khi cần trong quy trình dữ liệu:

```
py -3.12 data/clean/scripts/clean_and_validate.py
```


## Dữ liệu đối chiếu địa chỉ cũ → mới

Bộ cặp địa chỉ chi tiết có bằng chứng nguồn được lưu riêng tại data/doi_chieu_dia_chi_cu_moi/README.md. Tệp chính là cap_nha_duong_dia_chi_cu_moi.csv, hiện có 20 cặp, trong đó 19 cặp có số nhà/chi tiết đường. Đây là dữ liệu tham chiếu được trích từ các văn bản công khai; chưa phải Gold và không được trộn với bộ 4.398 địa chỉ độc lập ở data/tham_chieu_so_nha_toan_quoc.
