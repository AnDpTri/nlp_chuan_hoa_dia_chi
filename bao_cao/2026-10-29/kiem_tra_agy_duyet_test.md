# Kiểm tra kết quả agy tự duyệt tập test

Ngày kiểm tra: 29/10/2026. Hội thoại `Chuẩn Hóa Dữ Liệu Địa Chỉ`, ID `feca2faf-c8c5-4c07-8293-c9f0c9e553e4`, trạng thái IDLE, 986 bước. Đã đọc trả lời cuối ở bước 985, đối chiếu file, chạy validator và thử đồng bộ trên bản sao.

**Kết luận: lượt chạy đã kết thúc, nhưng chưa đạt yêu cầu duyệt và truy vết đầy đủ. Chưa dùng kết quả này như bộ nhãn đã được kiểm chứng hoàn chỉnh.**

## Những phần đã xác nhận

- Có 400 dòng nhật ký với 400 ID khác nhau: 337 `giu_nguyen`, 38 `sua_nhan`, 25 `chua_du_can_cu`.
- CSV test có 369 dòng `da_duyet_ai`, 31 dòng `can_duyet`; không có người duyệt bị giả mạo.
- So bản sao trước duyệt: giữ nguyên toàn bộ 400 ID, chuỗi đầu vào và URL nguồn. Mã băm bản gốc là `11c79938a041c22351cd88338d216d7cd094d313b6a1c045c48262a13c178c3a`.
- Có 38 dòng thực sự đổi trường nhãn/cảnh báo, trong đó 37 dòng thay mã xã, một dòng thay số nhà; chưa đánh giá rằng mọi sửa đổi đều đúng.
- Kiểm tra cấu trúc test, ghim danh mục và 14 bài hồi quy đều PASS. Chạy validator trên tập thật sau các fixture để báo cáo cuối không bị fixture ghi đè.
- Lịch sử lượt xử lý có 33 bước SEARCH_WEB; nhật ký đánh dấu có căn cứ web ở 36 mẫu. Một lượt tìm kiếm có thể liên quan nhiều mẫu, nên hai số này không tự mâu thuẫn.

## Các lỗi cần sửa

### 1. Nhật ký chưa có bằng chứng web đủ truy vết

Cả 36 ô `can_cu_web` có nội dung đều không có URL. Các ô chỉ ghi tên nghị quyết/ngày tra cứu, thiếu vị trí điều khoản hoặc bằng chứng cụ thể chứng minh địa chỉ thuộc phần địa giới đã chốt. Không thể suy từ đã có search sang toàn bộ kết luận đều đã được kiểm chứng.

Ví dụ `VNTEST0023`: input thật là `F26-F27, tầng 1, 30 Bờ Bao Tân Thắng, P. Sơn Kỳ, Q. Tân Phú`. Nhật ký khẳng định toàn tuyến Bờ Bao Tân Thắng và Celadon City về Tân Sơn Nhì. [Toàn văn Nghị quyết 1685](https://xaydungchinhsach.chinhphu.vn/toan-van-nghi-quyet-so-1685-nq-ubtvqh15-sap-xep-cac-dvhc-cap-xa-cua-thanh-pho-ho-chi-minh-nam-2025-119250616211341304.htm), Điều 1 khoản 41, 62, 63, phân chia Sơn Kỳ giữa Bình Hưng Hòa, Tây Thạnh và Tân Sơn Nhì; trang này không có đoạn nêu tên Bờ Bao. Từ nguồn đó chưa đủ xác định số 30 thuộc phần nào. Đây là kết luận thiếu chứng cứ được lưu, không phải khẳng định địa chỉ đích chắc chắn sai.

### 2. Nhánh 168 mẫu tự động khớp chưa có phép đối chiếu mới

Trong `data/test/scripts/ai_review_engine.py:110`, nhánh `prior_status == 'tu_dong_khop'` chuyển thẳng thành `da_duyet_ai` và ghi nhãn chính xác. Nhánh này không thực hiện phép kiểm tra span hoặc tra quan hệ mới trước khi khẳng định như vậy. Việc tạo bản ghi nhật ký không tự chứng minh từng mẫu đã được rà soát ngữ nghĩa độc lập.

### 3. Đồng bộ đổi trạng thái chưa giải quyết

`bang_duyet_test.csv` gắn `trang_thai_duyet=da_duyet_ai` cho cả 400 dòng, trong khi CSV test giữ 31 dòng `can_duyet`. Đã thử chạy `kiem_tra_tien_do_duyet.py --sync` với hai file sao chép trong thư mục work: lệnh trả thành công và đổi cả 31 dòng đó sang `da_duyet_ai`, không có bằng chứng mới. Test thật không bị thay đổi trong phép thử này. Cần tách trạng thái đã xem xét với kết luận đã xác định được nhãn, đồng bộ không được âm thầm làm mất sự phân biệt ấy.

### 4. Báo cáo mô tả nhầm input theo ID

| ID | Input được mô tả ở trả lời cuối | Input thật trong CSV |
|---|---|---|
| VNTEST0008 | 27 Lê Lai, Hà Cầu | Số 108 Trần Phú, phường Mộ Lao, quận Hà Đông, Hà Nội |
| VNTEST0023 | 13/8 Thoại Ngọc Hầu, Hòa Thạnh | F26-F27, tầng 1, 30 Bờ Bao Tân Thắng, P. Sơn Kỳ, Q. Tân Phú |
| VNTEST0038 | Số 52 Bạch Đằng, Phường 2 | 8 Cộng Hòa, Phường 4, Hồ Chí Minh, Việt Nam |

Nhật ký của các ID này có input thật; lỗi ở báo cáo cuối khiến phần mô tả sửa nhãn không đáng tin nếu chỉ đọc báo cáo.

### 5. Metadata và thống kê chưa đúng

- `model_duyet` của cả 400 dòng là `antigravity-deepmind-agent`, trong khi cấu hình model của lượt app là `gemini-3.8-flash-high`. Cần ghi riêng tên agent và model thực tế.
- Cả 400 mốc thời gian được ghi bằng một hằng số, chưa phân biệt thời điểm xem xét và thời điểm xuất nhật ký.
- Công cụ tiến độ báo 308 dòng AI điều chỉnh, trong khi diff trường nhãn/cảnh báo thực tế là 38. Code đếm chuỗi `Không thay đổi (...)` thành có thay đổi vì chỉ loại đúng chuỗi `Không thay đổi`.
- Engine đọc lại bản sao trước duyệt và ghi đè toàn bộ CSV test/bảng duyệt khi chạy lại; chưa có cơ chế hợp nhất bảo toàn chỉnh sửa mới trong hai file hiện tại.

## Phạm vi kiểm tra

Chưa xác minh độc lập toàn bộ 38 nhãn sửa, đặc biệt chín ca chốt xã bị chia. Không chạy lại engine, không đồng bộ lên tập thật, không huấn luyện hay điều chỉnh lõi theo nhãn test. Các kiểm tra vừa chạy chỉ chứng minh cấu trúc và hành vi cụ thể đã nêu, không chứng minh toàn bộ nhãn đúng.
