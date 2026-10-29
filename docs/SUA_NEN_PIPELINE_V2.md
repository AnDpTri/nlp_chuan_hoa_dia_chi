# Sửa nền pipeline v2 — 29/10/2026

Đã sửa phần dùng luật trước khi huấn luyện mô hình. Các phép đo chỉ dùng cùng tập dev 1.136 mẫu; không đọc nhãn test cuối để sửa lõi, không bổ sung hoặc đổi nhãn train/dev, không sửa danh mục.

## Các thay đổi

1. So khớp tiền tố giữ bằng chứng dấu đã gõ, vẫn cho phép thiếu dấu một phần. Tô không thành Tổ, Tĩnh không thành Tỉnh. Chấp nhận Đ. và dạng lỗi tiền tố telex đã có trong dữ liệu.
2. Nhận cụm tiền tố dài trước: Thành phố, Khu phố, Tổ dân phố, Tỉnh lộ. Không tách chữ phố bên trong Thành phố thành tiền tố đường.
3. Bảo vệ tên chi tiết và tên hành chính theo ngữ cảnh. Đường Xã Đàn vẫn là đường; Xã Bản Xèo, Phường Phố Mới và Xã Đường Lâm vẫn là hành chính khi có ứng viên tra được. Phần chưa nhận diện không bị ép thành một trường đã biết.
4. Tách P7/Q10/ngõ5 thành token tiền tố và số nhưng giữ nguyên offset về chuỗi gốc, kể cả Unicode phân rã. Số nhà 18B và số nhà chứa '/' vẫn được giữ nguyên.
5. Beam search có phạt mềm khi bỏ qua bằng chứng cấp tỉnh/huyện đã ghi rõ để chọn một đơn vị mâu thuẫn. Thiếu cấp khác với mâu thuẫn. Không chốt xã khi các xã khớp tên đều mâu thuẫn huyện nguồn; giữ huyện/tỉnh phù hợp và cảnh báo.
6. Loại hành chính trong input khác danh mục được giữ thành giả thuyết tại cấp mà tiền tố cho phép, có giảm điểm (mạnh hơn ở cấp xã) và cờ `loai_hanh_chinh_khac_danh_muc`. Không bỏ tiền tố để đổi cấp xã thành tỉnh hay ngược lại. Không coi việc khớp tên là bằng chứng rằng loại ghi trong input đúng ở mốc đích; vẫn cần quan hệ nguồn/đích và ngữ cảnh.
7. Nhánh bỏ qua tỉnh không được coi là bằng chứng phủ định một tỉnh đã được nhận diện. Mơ hồ xã vẫn có thể giữ phần tỉnh đồng thuận.
8. Tính tiền tố một lần cho mỗi input và dùng lại khi phân tích các giả thuyết. Dấu vết hành chính và chi tiết giữ các khoảng token/ký tự không chồng nhau.

## Kết quả và tái lập

Đã qua **30 bài kiểm tra pipeline và 4 bài kiểm tra cách chấm**. Trên cùng 1.136 mẫu dev, mức khớp đồng thời sáu trường tăng **60,299% → 73,856%** (685 → 839 mẫu); thêm 154 mẫu khớp và không mất mẫu nào ở chỉ số toàn bộ sáu trường. Một số trường riêng vẫn mất khớp ở mẫu vốn chưa khớp toàn bộ; bảng so sánh ghi đầy đủ các trường hợp đó.

Mã tỉnh: **96,743% → 98,944%**; mã xã: **90,845% → 93,222%**; đường: **68,398% → 81,690%**. Đây là mức khớp với nhãn dev máy/tổng hợp, chưa phải độ chính xác thực tế được xác minh độc lập.

Kết quả đo cuối, mã băm source/dữ liệu, chênh lệch từng trường và input/output từng mẫu lưu tại `danh_gia/ket_qua/ban_thu_v2_cuoi/`. So sánh với mốc v1 trong `SO_SANH_V1_V2.md`; xem cả những trường lệch riêng dù toàn địa chỉ có thể chưa đạt ở cả hai bản.

```powershell
Set-Location -LiteralPath 'D:\nlp_chuan_hoa_dia_chi'
py -3.12 -X utf8 -B -m unittest discover -s tests -p test_pipeline.py -v
py -3.12 -X utf8 -B -m unittest discover -s tests -p test_danh_gia.py -v
py -3.12 -X utf8 -B -m danh_gia.chay_ban_thu --output-dir danh_gia/ket_qua/lan_do_moi
```

Thư mục lần đo mới phải chưa tồn tại. Các lần v2 trung gian được giữ để truy vết; dùng thư mục `ban_thu_v2_cuoi` để đối chiếu source bàn giao.

## Giới hạn còn lại

- Nhãn dev là nhãn máy và tổng hợp, có lỗi; tỷ lệ khớp nhãn không phải độ chính xác đã được xác minh độc lập. Không thay nhãn chỉ để tăng điểm.
- Chưa có từ điển để mở rộng mọi tên riêng viết tắt như TTT/BVT/DV/CG hay khôi phục dấu mọi tên đường. Những phần này có thể vẫn chưa xác định được.
- Địa chỉ không tiền tố/dấu phân cách, tên trùng giữa đường và hành chính, dữ liệu mốc cũ thiếu các đơn vị lịch sử hoặc nhiều lỗi cùng lúc vẫn có thể bị phân tích sai.
- Trọng số xếp hạng và ngưỡng mơ hồ vẫn đặt tay; chưa được hiệu chuẩn thành độ tin cậy xác suất.
- Xã bị chia không có bằng chứng địa bàn chi tiết vẫn giữ danh sách ứng viên, không tự chọn một đích.
