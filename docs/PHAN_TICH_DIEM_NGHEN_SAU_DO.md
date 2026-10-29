# Phân tích sau các lượt đo — 29/10/2026

Phân tích dùng output bản đã sửa định dạng tiền tố, không lấy bản hợp đồng
bị giảm điểm làm baseline mới. Không sửa dữ liệu, model hoặc thuật toán ở
lượt phân tích này. Điểm vẫn dựa trên nhãn máy/tổng hợp của dev phát triển.

## Phần chưa khớp hiện tại trên dev khó

| Nhóm loại trừ nhau, xét output cuối | CNN + ranker | ViDeBERTa + điểm tay |
|---|---:|---:|
| Chỉ khác dấu, sáu trường khớp sau bỏ dấu | 50 | 50 |
| Nhãn đường trống nhưng output có đường | 18 | 18 |
| Chỉ lệch mã hành chính | 17 | 17 |
| Các lỗi khác, gồm lỗi kết hợp | 46 | 43 |
| Tổng chưa khớp | 131 | 128 |

Theo trường, có chồng lấn: CNN lệch đường 114 câu, mã xã 23, số nhà 2;
ViDeBERTa lệch đường 111, mã xã 25, số nhà 2. Không thấy lệch mã tỉnh trong
các output dev khó này. Các số này khác phân loại beam trước sửa formatter.

Các nhóm là mô tả cơ học, không tự chứng minh nguyên nhân ngữ nghĩa.

## Phải phân biệt tên chưa giải được với nhãn thiếu

Metadata của các ví dụ cuối tập khai rõ `mo_ho=true` và tập tên ứng viên.
Chẳng hạn `Đ. NTT` có Nguyễn Tất Thành / Nguyễn Thị Thập / Nguyễn Trọng
Tuyển. Vì vậy 18 dòng nhãn đường trống không thể tự gọi là nhãn thiếu hoặc
sai. Các dòng này chỉ gồm 3 họ input sau che số nhà, không phải 18 tình
huống độc lập. Có đường trong input không đồng nghĩa biết tên chuẩn duy nhất.

Lõi hiện đưa `Đường Ntt` vào trường `duong`, trong khi nhãn dùng trường đó
như tên chuẩn đã giải được. Đây là lệch hợp đồng: giá trị quan sát/chưa giải
và tên chuẩn đang dùng chung một trường. Cần giữ chữ gốc và ứng viên riêng,
với trạng thái mơ hồ; không xóa thông tin hay ép một tên để tăng điểm.

## Thiếu tên chuẩn có thật, nhưng chưa đủ để quy mọi lỗi cho dữ liệu

50 câu chỉ khác dấu là nhu cầu khôi phục tên rõ ràng; chưa phải lỗi model
cắt đoạn. Danh mục đường có nguồn và địa bàn phù hợp có thể giúp trực tiếp.
Nhưng tỉnh một mình không chứng minh tên đường nằm trong phường/xã đã chọn;
alias trùng cần đủ ngữ cảnh hoặc giữ nhiều khả năng. Không lấy tên dev bổ
sung từ điển rồi coi điểm tăng là tổng quát hóa.

Train là nguồn học thống kê, không phải nguồn chứng thực độc lập. Cấm mọi
khôi phục từ train cũng không chứng minh an toàn hơn. Cần giữ provenance và
hiệu chỉnh quyết định khẳng định thay vì đánh đồng dự đoán với chứng thực.

## Hành chính có ít nhất hai vấn đề khác nhau

Hậu kiểm 17 câu CNN chỉ lệch mã hành chính, dùng beam chế độ hợp đồng giữ
ứng viên, thấy 13 câu có đích tham chiếu, 4 câu không có. Do cơ chế lọc khác,
đây không phải khẳng định chính xác beam bản cũ có cùng phân bố.

- 4 câu vắng đích: kiểm tra sinh ứng viên, nhận tiền tố, tra tên/mốc và
  pruning; thêm dữ liệu đường không tự giải được.
- 13 câu có đích: có thể chọn sai, từ chối vì mơ hồ, hoặc reference ép một
  đích. Không tự động coi tất cả là lỗi ranker.
- VNDEV_KHO_00177 có `xa tam dan, huyen phu ninh, tinh quang nam`:
  hai nhánh gần giữ mã 20364 và 20392 (Tam Đàn/Tam Dân). Input không dấu
  chưa đủ phân biệt, nhưng reference yêu cầu một mã. Hợp đồng chấm cần
  phân biệt quyết định giữ mơ hồ hợp lý với chọn sai.
- VNDEV_KHO_00021 có đích tham chiếu vắng trong beam chế độ hợp đồng;
  không thể chữa riêng bằng đổi điểm ranker của các phương án đã có.

## Giới hạn của bản hợp đồng vừa triển khai

Bản đó bổ sung provenance/giả thuyết và thay chính sách chọn tên, chưa phải
một bộ giải mã tốt hơn. Nó giữ tên đúng ở gợi ý nên mỗi model mất 48 câu
gốc/15 câu khó. CNN mất thêm 1 câu khó do bỏ lọc span. Nó còn giữ giá trị
chưa giải như Ntt trong trường đường, nên chưa thực thi trọn vẹn việc tách
quan sát khỏi canonical. Chưa có bằng chứng giảm lỗi khẳng định sai để bù
mức giảm khớp sáu trường. Không thay bản mặc định bằng chế độ này.

## Hướng kỹ thuật có thể kiểm chứng

1. Thống nhất schema: giá trị gốc, giá trị chuẩn được chọn, tập ứng viên,
   trạng thái (thiếu input/chưa giải/mơ hồ/đã chọn) và nguồn. Chấm riêng
   khôi phục đúng, khẳng định sai và giữ mơ hồ; vẫn giữ metric sáu trường
   cũ để nối lịch sử, không lặng lẽ đổi nhãn hoặc loại mẫu.
2. Sinh phương án từ cả span model, loại tiền tố, alias danh mục và đồ thị
   hành chính theo từng mốc. Không xóa ứng viên chỉ vì span model, cũng
   không cho ứng viên trùng chữ chiếm đường vô điều kiện. Điểm vai trò và
   quan hệ địa bàn cùng tham gia lựa chọn; thiếu dữ kiện không ép một đích.
3. Tích hợp nguồn đường của agy sau kiểm chứng, đo độ phủ và collision theo
   địa bàn. Kiểm tra riêng 4 ca vắng đích và từng nhóm lựa chọn/mơ hồ;
   không thêm ngoại lệ theo ID hay địa danh để đuổi điểm dev.
4. Đóng băng thiết kế trước phép đánh giá độc lập. Báo theo họ nguồn/kiểu
   biến đổi và trường; các mẫu chỉ thay số nhà không được coi là nhiều
   bằng chứng độc lập. Nếu dùng kết quả đó để sửa tiếp, nó thành tập phát triển.

ViDeBERTa vẫn là đối chứng cần giữ, nhưng chênh 3 câu ở dev khó không đủ
giải thích phần lớn 128/131 câu chưa khớp. Chưa có căn cứ train lớn hơn ngay,
cũng chưa thể coi một bộ dữ liệu lớn hơn là giải pháp duy nhất.

## Nguồn đối chiếu

- `danh_gia/ket_qua/sua_dinh_dang_v1_01/*_dev_kho.jsonl`: output mốc chính.
- `mo_hinh/thu_nghiem/char_v1_01/data/dev_kho.jsonl`: metadata nguồn/biến đổi.
- `danh_gia/ket_qua/do_hop_dong_v1_01/cnn_ranker_dev_kho.jsonl`: các beam giữ ứng viên.
- `danh_gia/ket_qua/do_hop_dong_v1_01/PHAN_TICH_GOI_Y.json`: phần giảm do chính sách tên.
