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
Python 3.12. Không cần sinh lại dữ liệu sạch để dùng pipeline:

```
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m src.cli --text "12 ngo 5 tran thai tong cau giay hn"
.\.venv\Scripts\python.exe -m src.cli --input INPUT.csv --column dau_vao --output OUTPUT.xlsx
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Linux/macOS dùng `.venv/bin/python`. Đầu vào CSV/Excel có cột `dau_vao` (hoặc đổi bằng `--column`); đầu ra hỗ trợ CSV, JSON, XLSX. Không cho đầu vào và đầu ra trùng tệp. Mã giữ dạng chuỗi, Excel giữ văn bản nhập vào dạng Text. Truy vết trong JSON ghi token, kiểu khớp và điểm. Pipeline không cần mạng khi chạy.

## Trạng thái triển khai và số đo

- Đã cài pipeline trie + Levenshtein một lỗi + ghép cây hành chính + đổi cũ/mới; tách số nhà/ngõ/đường bằng luật. Chưa huấn luyện Logistic Regression/CRF hay mô hình học trọng số.
- 34 tỉnh/thành, 3.321 xã/phường. Lớp `data/runtime/loai_moc_2025.csv` giữ loại đúng mốc; không sửa sáu bảng clean đã ghim. `.gitattributes` giữ CRLF của sáu tệp để hash byte khớp manifest trên mọi OS.
- 6.066 tên đường từ OSM ngoài URL/chuỗi đầu vào giữ lại cho đánh giá. Xem [nguồn, ODbL và giới hạn thời gian](data/runtime/NOTICE.md).
- 11 kiểm thử đạt. Trên 480 ca **tổng hợp từ danh mục**, pipeline đúng đồng thời mã xã/tỉnh 94,79%; đây không phải accuracy trên địa chỉ thực. Cấu hình và từng nhóm ở [metrics.json](results/development/metrics.json).
- Đã chạy 400 địa chỉ thực nhưng **0/400 nhãn được duyệt thủ công**. [Bộ chấm](danh_gia/README.md) trả `awaiting_manual_review`, các metric là `null`; không công bố accuracy cuối hoặc đổi nhãn máy thành nhãn đã duyệt.
- Báo cáo tuần 3 giữ nguyên như bản tiến độ lịch sử. Bản triển khai mới: [LaTeX](bao_cao/main.tex), [PDF](bao_cao/main.pdf).

Để tái lập so sánh: cài `requirements-baselines.txt`, chạy `python -m tools.benchmark_synthetic`. Có pipeline, ablation tắt fuzzy và hai thư viện mốc được ghim phiên bản. Tệp ca tổng hợp chỉ lấy danh mục, không đọc gold held-out. Không dùng nhãn 400 dòng để sửa luật. Thời gian đo local có tác vụ đồng thời, không thay thế benchmark trên môi trường riêng.

## Cảnh báo phải đọc

`xa_bi_chia`: để trống xã và trả các ứng viên; `mo_ho_hanh_chinh`: nhiều cách hiểu gần ngang nhau; `mau_thuan_hanh_chinh`: các đơn vị trong đầu vào không cùng tuyến cha con; `thieu_xa`/`thieu_tinh`: thiếu cấp; `phan_con_chua_khoi_phuc_dau`: chưa có từ điển tên riêng duy nhất. Điểm khớp là điểm xếp hạng, không phải xác suất. Chưa đủ dữ liệu thôn/đường để tự giải quyết mọi xã bị chia.

Lệnh tạo lại lớp runtime: `python -m tools.build_catalogue`. Từ điển đường đã kèm repo; muốn tạo lại cần bản OSM candidates đã mô tả trong [NOTICE](data/runtime/NOTICE.md), rồi chạy `python -m tools.build_street_lexicon --candidates PATH`. Không chạy lại script tạo nhãn test trong quy trình huấn luyện hoặc chuẩn hóa.
