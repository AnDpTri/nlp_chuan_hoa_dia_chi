# Kiểm tra kết quả agy

Ngày 29/10/2026. Đã đọc báo cáo agy người dùng gửi và kiểm tra độc lập các file trong `D:\nlp_chuan_hoa_dia_chi`. Không sửa mã nguồn, nhãn hoặc dữ liệu dự án trong lần kiểm tra này.

## Kết quả xác nhận được

- Danh mục mới hiện có **6 Thành phố, 28 Tỉnh**. Ba loại tỉnh 22, 24, 75 đã được sửa.
- Sáu bảng danh mục khớp manifest hiện tại. So với hash được ghim tại HEAD, chỉ `moi_tinh.csv` thay đổi byte.
- `dia_chi_test.csv` vẫn giữ SHA-256 `11c79938a041c22351cd88338d216d7cd094d313b6a1c045c48262a13c178c3a`, giống trước khi agy làm.
- Có **4.000 mẫu train, 1.000 mẫu dev**, gồm tổng cộng 2.500 dòng `nhan_may` và 2.500 dòng `tong_hop`.
- Kiểm tra độc lập tập chuỗi chuẩn hóa không phát hiện giao giữa train–dev, train–test hoặc dev–test. Đây là kết quả theo phép chuẩn hóa đã dùng, chưa phải chứng minh mọi dạng rò rỉ ngữ nghĩa đều đã bị loại.
- Báo cáo tập test hiện ghi **0/400 dòng được người duyệt**, chưa sẵn sàng đánh giá cuối.

## 1. Nhãn OSM có trường không khớp đầu vào — cần sửa trước huấn luyện

`data/train_dev/scripts/prepare_train_dev.py:193–194` lấy số nhà và đường trực tiếp từ thẻ OSM, không kiểm tra chúng có phù hợp chuỗi `dau_vao` đang dùng hay không. Nếu `addr:full` khác các thẻ cấu trúc, nhãn có thể sai hoặc thêm thông tin ngoài chuỗi.

Các ví dụ đọc trực tiếp từ CSV:

| ID | Đầu vào | Nhãn đang có |
|---|---|---|
| `VNTRAIN_00087` | Số **18B** Nguyễn Biểu, phường Quán Thánh, quận Ba Đình, Hà Nội | `so_nha = Số 18` |
| `VNTRAIN_00398` | Số **402** Kim Giang, phường Đại Kim, quận Hoàng Mai, Hà Nội | `so_nha = Số 404` |
| `VNDEV_00489` | Số **4A** Hàng Chiếu, Phường Đồng Xuân, Quận Hoàn Kiếm Hà Nội | `so_nha = Số 4` |
| `VNTRAIN_01042` | Chung cư cao tầng C2 Xuân Đỉnh, Lô C2, phường Xuân Đỉnh, quận Bắc Từ Liêm. Hà Nội | `duong = Đường Ngách 1/2 Đỗ Nhuận`, không xuất hiện trong đầu vào |

Phép quét chữ chuẩn hóa tìm được ba số nhà và một trường đường không hiện diện nguyên vẹn trong đầu vào. Bảng trên là ví dụ xác nhận bằng đọc trực tiếp; chưa phải toàn bộ lỗi ngữ nghĩa trong dữ liệu.

Cần ưu tiên chuỗi đầu vào, đối chiếu span nguồn trước khi dùng thẻ bổ trợ. Khi thẻ mâu thuẫn hoặc không có bằng chứng trong chuỗi, chuyển dòng sang diện cần kiểm tra hoặc loại khỏi phần nhãn huấn luyện đáng tin. Rà tương tự với các thành phần hành chính vì script cũng dùng các thẻ hành chính làm căn cứ.

## 2. Validator sẽ lỗi khi gặp nhãn đã duyệt

`data/test/scripts/validate_dataset.py:37–53` dùng `re.match` và `re.search`, nhưng module không import `re`.

Hiện mọi dòng đều chưa duyệt nên nhánh này chưa được chạy. Khi có dòng `da_duyet` với thông tin reviewer/ngày, kiểm tra bị dừng bằng:

```text
NameError: name 're' is not defined
```

Đã tái hiện bằng chính hàm được trích từ AST của script và một bản ghi giả lập chỉ nằm trong bộ nhớ; không đổi trạng thái duyệt của bất kỳ dòng thật nào.

Cần thêm import và kiểm tra cả trường hợp chưa duyệt, đã duyệt hợp lệ, thiếu bằng chứng duyệt. Thông tin tên/ngày là metadata kiểm toán, không phải chữ ký số hoặc bằng chứng xác thực danh tính người duyệt.

## 3. Đồng bộ nhãn duyệt chưa đồng bộ cảnh báo

Trong `data/test/scripts/kiem_tra_tien_do_duyet.py:124`, danh sách cột được đồng bộ không có `canh_bao`. Người duyệt có thể sửa nhãn và cảnh báo trong bảng duyệt nhưng lệnh `--sync` chỉ đưa nhãn mới sang tập test, để lại cảnh báo cũ.

Ví dụ người duyệt giải quyết xã bị chia có bằng chứng, điền xã đích và bỏ cờ `xa_bi_chia`; sau sync, cờ cũ vẫn còn. Validator hiện cũng bắt buộc mọi xã nguồn nhiều đích phải để trống xã mới, kể cả dòng đã được người duyệt chốt bằng chứng.

Cần thống nhất cách lưu bằng chứng giải quyết xã bị chia, đồng bộ các trường có liên quan và cập nhật kiểm tra tương ứng. Chưa nên hướng dẫn nhóm dùng `--sync` như một bước đã hoàn chỉnh.

## 4. Độ phủ train/dev còn hạn chế

- Trong cả 5.000 mẫu, **0 mẫu có trường `ngo_ngach_hem` khác rỗng**. Chưa đủ dữ liệu học phần tách ngõ/ngách/hẻm.
- Phần sinh tổng hợp hiện có các nhóm xã cũ và xã mới riêng, chưa có nhánh sinh có chủ đích các tổ hợp cũ–mới như đầu vào đã thống nhất.
- Các nhóm biến thể tổng hợp gồm chuẩn, không dấu, viết tắt, thiếu thành phần và đổi thứ tự; chưa có nhóm lỗi gõ có chủ đích.
- Các nhãn dev vẫn là nhãn máy/tổng hợp; điểm trên chúng chưa đại diện cho độ chính xác trên nhãn được người duyệt.

## Trạng thái sử dụng

Danh mục đã khắc phục lỗi mốc loại tỉnh và có bộ train/dev ban đầu. Trước khi huấn luyện cần sửa quy tắc gán nhãn theo đầu vào, tái tạo và kiểm tra dữ liệu. Trước khi đưa tập test vào duyệt cần sửa validator và quy trình sync. Tập test cuối vẫn cần người duyệt thực tế.

Không dùng báo cáo PASS về schema/mã/không trùng chuỗi để thay cho kiểm tra nhãn ngữ nghĩa hoặc kiểm tra các nhánh xử lý chưa từng chạy.
