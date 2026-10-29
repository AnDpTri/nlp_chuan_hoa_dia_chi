# Pipeline có căn cứ và nhiều giả thuyết — phiên bản thử nghiệm 1

Ngày đóng băng: 29/10/2026. Bản này tách quyết định có căn cứ khỏi phép
định dạng, không thêm ngoại lệ theo ID/địa danh hoặc lấy nhãn dev làm nguồn.

## Hành vi đã triển khai

Bật bằng `--hop-dong` hoặc `BoChuanHoa(hop_dong=True, ...)`.
Đường chạy cũ giữ lại để đối chứng; chưa tự thay mặc định.

1. **Quan sát:** giữ nguyên input và offset Unicode gốc, lưu span model trước
   khi ghép hành chính. Giữ cả kết quả chi tiết nếu không chọn hành chính.
2. **Định dạng/giải nghĩa:** ghi riêng thao tác định dạng vai trò, giải tiền tố
   Telex, giải loại tuyến lồng và gán loại đường từ model. Các phép giải nghĩa
   không được ghi như thao tác chỉ đổi khoảng trắng. Mỗi thao tác giữ chữ gốc.
3. **Tên chuẩn:** từ điển train trả về toàn bộ gợi ý, kể cả trùng khóa và xung
   đột dấu. Dấu mâu thuẫn được đánh dấu. Một gợi ý duy nhất từ train vẫn chưa
   được tự thay vào trường `duong`; giá trị đang có được giữ, gợi ý và ID/hash
   nguồn được xuất riêng. Thiếu tỉnh không tự đoán tỉnh để tra tên.
4. **Ghép:** chế độ này bỏ bộ lọc cứng theo span model dù bật `--bao-ve-duong`.
   Ứng viên vẫn đi qua beam/điểm vai trò hiện có; ghi xung đột model–hành chính.
   Không đặt trọng số hay threshold mới bằng lỗi dev.
5. **Lựa chọn:** xuất các giả thuyết đã xét và nhóm gần nhất, từng nguồn giữ
   `(mốc, mã, cấp, vị trí)`, chi tiết và mã đích tương ứng. Quyết định mơ hồ
   dùng cơ chế cũ; không ép một mã chỉ để có đầu ra.

Phần bổ sung nằm trong `thong_ke.hop_dong`, gồm `truong`, `gia_thuyet_da_xet`,
`gia_thuyet_gan`, `quan_sat_model_truoc_ghep`,
`chi_tiet_khi_khong_chon_hanh_chinh` và `xung_dot_model_hanh_chinh`.
Các trường đầu ra cũ và dấu vết vẫn dùng được.

## Giới hạn phải hiểu đúng

- Đây chưa phải bộ giải mã mới được huấn luyện chung. Beam hữu hạn và hàm
  điểm/ngưỡng gần vẫn từ phiên bản trước, chưa được hiệu chỉnh xác suất.
- Không lọc cứng ứng viên không bảo đảm beam giữ hết mọi cách hiểu. Output
  vẫn có thể chọn sai, nhưng những nhánh đã xét có thể kiểm tra lại.
- Một phép Telex có lý do vẫn có thể giải sai. Chữ gốc và giả thuyết giữ nguyên
  được giữ để kiểm chứng; chưa bổ sung sửa Telex tùy ý trong tên riêng.
- Danh mục hành chính chứng minh quan hệ tra cứu/mapping, không tự chứng minh
  địa chỉ thực hay đường nằm trong phường. Tên từ train vẫn là nguồn yếu.
- Từ điển có nguồn chứng thực của nhánh dữ liệu chưa được tích hợp tại đây;
  chế độ mới chưa tự nâng bất kỳ nguồn nào thành đã xác minh độc lập.

## Kiểm thử và nghiệm thu

Kiểm thử cấu trúc bằng fixture viết tay, không đọc dataset train/dev/test:
tên cùng khóa, dấu mâu thuẫn, thiếu tỉnh, gợi ý duy nhất nhưng nguồn yếu,
xung đột tên đường–hành chính, Telex có nguồn gốc, input rỗng và gọi lặp.
Có 24 tổ hợp thứ tự, NFC/NFD, tên và số nhà để kiểm offset/giữ thông tin.
Đây là kiểm thử phần mềm, **không phải tập gold mới** và không cho ra độ
chính xác thực tế. Log kiểm thử ở `docs/hop_dong_v1_kiem_thu.txt`.

Trước phép đánh giá chất lượng tiếp theo, đóng băng hash code/checkpoint/
từ điển/cấu hình. Bộ đánh giá độc lập cần nguồn/họ địa chỉ chưa dùng để sửa
lõi, có nhãn phân biệt thiếu thông tin, mơ hồ, nhiều đích và lỗi nhập. Chấm:

- Span và vai trò từng trường.
- Giá trị khôi phục đúng trong những trường hệ thống quyết định khẳng định.
- Tỷ lệ giữ chưa rõ/có gợi ý; không đổi lấy điểm bằng cách bỏ trống mọi trường.
- Mã đích và quyết định mơ hồ, cùng tỷ lệ khớp đủ sáu trường để nối báo cáo cũ.
- Thời gian và kích thước output có/không xuất giải thích trên cùng máy.

Không sử dụng kết quả tập độc lập để chỉnh tiếp rồi giữ tên gọi test độc lập.
Không dùng điểm dev cũ làm điều kiện để bật mặc định chế độ này.

## Chạy

```powershell
.\.venv-neural\Scripts\python.exe -X utf8 -B -m src 'Số 17C, Đường Hoa Binh, Thành phố Hà Nội' --char-model mo_hinh/thu_nghiem/char_v1_01/char_cnn.pt --ranker mo_hinh/thu_nghiem/char_v1_01/ranker.txt --tu-dien-duong danh_gia/ket_qua/sua_pipeline_cnn_v1_01/tu_dien_duong_train.json --hop-dong --threads 1
```

Không cần train thêm. Có thể thay `--char-model` bằng `--videberta-model`
và dùng đúng ranker tương ứng. Giữ cùng hợp đồng khi so sánh các backend.
