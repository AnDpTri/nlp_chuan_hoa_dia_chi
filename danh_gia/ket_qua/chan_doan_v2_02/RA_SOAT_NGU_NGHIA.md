# Rà ngữ nghĩa các ca chẩn đoán v2

Rà 20/20 ca lệch không cảnh báo và 13 ca đại diện khác. Đây là kiểm tra theo input và danh mục cục bộ, chưa xác minh độc lập thực địa. Không chỉnh nhãn hoặc tính lại điểm sau khi loại mẫu.

Các nhận xét tách lỗi xử lý có bằng chứng trực tiếp, nhãn trái hợp đồng span, quy ước chưa chốt và nhập nhằng cần nguồn bổ sung. Không suy rằng mọi output đều đúng khi nhãn có vấn đề.

## VNDEV_00056 — nhan_thieu_dich_theo_danh_muc

- Input: Thôn Tiên Đỏa, X Bình Sa, H Thăng Bình, T. Quảng Nam
- Output: Thôn Tiên Đỏa, Xã Thăng Trường, Thành phố Đà Nẵng
- Tham chiếu: Thôn Tiên Đỏa, Thành phố Đà Nẵng
- Trường lệch: ma_xa
- Cảnh báo: không có

Input ghi X Bình Sa, H Thăng Bình; nhánh phù hợp danh mục chuyển sang Thăng Trường. Nhãn xã trống cần rà lại, chưa coi output là sai.

## VNDEV_00091 — nhan_trai_hop_dong_span

- Input: Ngõ 78 Phố Yên Lã, Phường Tân Hồng, Thành phố Từ Sơn, Bắc Ninh, Bac Ninh
- Output: Ngõ 78, Phố Yên Lã, Phường Từ Sơn, Tỉnh Bắc Ninh
- Tham chiếu: Ngõ 78, Đường Ngõ 78 Phố Yên Lã, Phường Từ Sơn, Tỉnh Bắc Ninh
- Trường lệch: duong
- Cảnh báo: không có

Nhãn đường chứa lại Ngõ 78 trong khi cùng đoạn đã gán ngõ. Output phân riêng Ngõ 78 và Phố Yên Lã, phù hợp hợp đồng span không chồng.

## VNDEV_00103 — nhan_thieu_dich_theo_danh_muc

- Input: Đường Tân Mỹ - Nhân Nghĩa, Xuân Bảo, Cẩm Mỹ, Đồng Nai
- Output: Đường Tân Mỹ - Nhân Nghĩa, Xã Xuân Định, Tỉnh Đồng Nai
- Tham chiếu: Đường Tân Mỹ - Nhân Nghĩa, Tỉnh Đồng Nai
- Trường lệch: ma_xa
- Cảnh báo: không có

Xuân Bảo, Cẩm Mỹ khớp nhánh danh mục dẫn đến Xuân Định. Nhãn xã trống cần rà; tên không tiền tố vẫn cần kiểm tra vai trò theo nguồn.

## VNDEV_00110 — quy_uoc_chuan_hoa_chua_chot

- Input: 120, Xa lộ Hà Nội, Phường Tăng Nhơn Phú, Khu phố 8, Thành phố Hồ Chí Minh
- Output: Số 120, Khu phố 8, Xa lộ Hà Nội, Phường Tăng Nhơn Phú, Thành phố Hồ Chí Minh
- Tham chiếu: Số 120, Khu phố 8, Đường Xa Lộ Hà Nội, Phường Tăng Nhơn Phú, Thành phố Hồ Chí Minh
- Trường lệch: duong
- Cảnh báo: không có

Output Xa lộ Hà Nội và nhãn Đường Xa Lộ Hà Nội cùng nội dung tên; khác cách giữ/gắn loại đường. Cần chốt quy ước, chưa coi là sai nhận diện tên.

## VNDEV_00113 — nhan_trai_hop_dong_span

- Input: Tổ 1, ấp 4, Mỹ Long, Cao Lãnh, Đồng Tháp.
- Output: Tổ 1, Ấp 4, Xã Mỹ Hiệp, Tỉnh Đồng Tháp
- Tham chiếu: Ấp 4, Đường Tổ 1, Ấp 4, Mỹ Long, Cao Lãnh, Đồng Tháp., Tỉnh Đồng Tháp
- Trường lệch: thon_xom, duong, ma_xa
- Cảnh báo: không có

Nhãn đường chép cả Tổ 1, Ấp 4 và hành chính, đồng thời Ấp 4 có nhãn thôn. Không thể dùng nguyên nhãn này cho BIO không chồng. Phần xã cần duyệt riêng.

## VNDEV_00158 — nhan_trai_hop_dong_span

- Input: Thôn Thượng Bái, Diên Hà, Hưng Yên
- Output: Thôn Thượng Bái, Xã Diên Hà, Tỉnh Hưng Yên
- Tham chiếu: Thôn Thượng Bái, Đường Thôn Thượng Bái, Xã Diên Hà, Tỉnh Hưng Yên
- Trường lệch: duong
- Cảnh báo: không có

Thôn Thượng Bái bị gán đồng thời thôn và đường trong tham chiếu. Đây là xung đột hợp đồng span, không nên ép parser lặp lại.

## VNDEV_00162 — nhan_gop_tien_to_ngo_vao_so_nha

- Input: 3 Ng.1, Phố Văn Hội, Đức Thắng, Bắc Từ Liêm, Hà Nội
- Output: Số 3, Ngõ 1, Phố Văn Hội, Phường Đông Ngạc, Thành phố Hà Nội
- Tham chiếu: Số 3 NG.1, Phố Văn Hội, Phường Đông Ngạc, Thành phố Hà Nội
- Trường lệch: so_nha, ngo_ngach_hem
- Cảnh báo: không có

Nhãn Số 3 NG.1 gộp cả tiền tố ngõ vào số nhà; output tách Số 3, Ngõ 1 theo quy tắc hiện hành. Cần sửa nhãn theo hợp đồng đã chọn, không đổi dữ liệu trong lượt này.

## VNDEV_00185 — nhan_lay_so_duong_lam_so_nha

- Input: 24, Hẻm 79 đường số 4, Bình Hưng Hòa, Bình Tân, Thành phố Hồ Chí Minh
- Output: Số 24, Hẻm 79, Đường Số 4, Phường Bình Hưng Hòa, Thành phố Hồ Chí Minh
- Tham chiếu: Số 4, Hẻm 79, Đường Hẻm 79 Đường Số 4, Phường Bình Hưng Hòa, Thành phố Hồ Chí Minh
- Trường lệch: so_nha, duong
- Cảnh báo: không có

Input bắt đầu 24, Hẻm 79 đường số 4; tham chiếu lấy Số 4 và lặp hẻm vào đường. Có bằng chứng trực tiếp nhãn nhầm vai trò số và chồng span.

## VNDEV_00191 — nhan_lay_so_duong_lam_so_nha

- Input: 73, Đường số 27, Phường An Lạc, Thành phố Hồ Chí Minh
- Output: Số 73, Đường Số 27, Phường An Lạc, Thành phố Hồ Chí Minh
- Tham chiếu: Số 27, Đường Số 27, Phường An Lạc, Thành phố Hồ Chí Minh
- Trường lệch: so_nha
- Cảnh báo: không có

Input 73, Đường số 27 nhưng tham chiếu Số 27. Output giữ Số 73; không nên sửa thuật toán để lấy số trong tên đường.

## VNDEV_00223 — nhan_lay_so_duong_lam_so_nha

- Input: 163, Đường số 1, Phường An Lạc, Thành phố Hồ Chí Minh
- Output: Số 163, Đường Số 1, Phường An Lạc, Thành phố Hồ Chí Minh
- Tham chiếu: Số 1, Đường Số 1, Phường An Lạc, Thành phố Hồ Chí Minh
- Trường lệch: so_nha
- Cảnh báo: không có

Input 163, Đường số 1 nhưng tham chiếu Số 1. Output giữ Số 163.

## VNDEV_00225 — quy_uoc_ngo_co_ten_can_chot

- Input: 2, Ngõ Đền, Phường Châu Khê, Thành phố Từ Sơn, Bắc Ninh, Bac Ninh
- Output: Số 2, Ngõ Đền, Phường Phù Khê, Tỉnh Bắc Ninh
- Tham chiếu: Số 2, Đường Ngõ Đền, Phường Phù Khê, Tỉnh Bắc Ninh
- Trường lệch: ngo_ngach_hem, duong
- Cảnh báo: không có

Ngõ Đền được gán ngõ ở output và đường ở nhãn. Cần quy ước ngõ có tên và nguồn tên chính thức; chưa đủ để xác nhận bên nào sai.

## VNDEV_00253 — nhan_trai_hop_dong_span

- Input: Ngõ 75 Phố Yên Lã, Phường Tân Hồng, Thành phố Từ Sơn, Bắc Ninh, Bac Ninh
- Output: Ngõ 75, Phố Yên Lã, Phường Từ Sơn, Tỉnh Bắc Ninh
- Tham chiếu: Ngõ 75, Đường Ngõ 75 Phố Yên Lã, Phường Từ Sơn, Tỉnh Bắc Ninh
- Trường lệch: duong
- Cảnh báo: không có

Nhãn đường chứa lại Ngõ 75 đã gán vào ngõ, còn output tách Ngõ 75 và Phố Yên Lã.

## VNDEV_00274 — nhan_lay_so_duong_lam_so_nha

- Input: 6, Đường Số 3, Xã Tân Nhựt, Bình Chánh, Thị trấn Tân Túc, Thành phố Hồ Chí Minh
- Output: Số 6, Đường Số 3, Xã Tân Nhựt, Thành phố Hồ Chí Minh
- Tham chiếu: Số 3, Đường Số 3, Xã Tân Nhựt, Thành phố Hồ Chí Minh
- Trường lệch: so_nha
- Cảnh báo: không có

Input 6, Đường Số 3 nhưng tham chiếu Số 3. Chỉ kết luận vấn đề số nhà; các tên hành chính trộn trong input cần xét riêng.

## VNDEV_00301 — nhan_trai_hop_dong_span

- Input: thôn đòn, lương nội, bá thước, thanh hóa
- Output: Thôn Đòn, Xã Quý Lương, Tỉnh Thanh Hóa
- Tham chiếu: Thôn Đòn, Đường Thôn Đòn, Xã Quý Lương, Tỉnh Thanh Hóa
- Trường lệch: duong
- Cảnh báo: không có

Thôn Đòn bị dùng lại làm đường trong tham chiếu dù đã có nhãn thôn. Output không nhân đôi đoạn chữ.

## VNDEV_00305 — nhan_lay_so_duong_lam_so_nha

- Input: 30, Đường số 8A, Phường An Lạc, Thành phố Hồ Chí Minh
- Output: Số 30, Đường Số 8A, Phường An Lạc, Thành phố Hồ Chí Minh
- Tham chiếu: Số 8A, Đường Số 8A, Phường An Lạc, Thành phố Hồ Chí Minh
- Trường lệch: so_nha
- Cảnh báo: không có

Input 30, Đường số 8A nhưng tham chiếu Số 8A; output giữ Số 30.

## VNDEV_00318 — nhan_trai_hop_dong_span

- Input: Số 5A, Hẻm 18 Đường Số 8, Phường Long Bình, Thủ Đức, Hồ Chí Minh
- Output: Số 5A, Hẻm 18, Đường Số 8, Phường Long Bình, Thành phố Hồ Chí Minh
- Tham chiếu: Số 5A, Hẻm 18, Đường Hẻm 18 Đường Số 8, Phường Long Bình, Thành phố Hồ Chí Minh
- Trường lệch: duong
- Cảnh báo: không có

Hẻm 18 nằm đồng thời trong nhãn hẻm và nhãn đường; output tách riêng Hẻm 18 và Đường Số 8.

## VNDEV_00327 — nhan_trai_hop_dong_span

- Input: Ngõ 160 Đường Lý Thường Kiệt, Phường Thị Cầu, Thành phố Bắc Ninh, Bắc Ninh, Bac Ninh
- Output: Ngõ 160, Đường Lý Thường Kiệt, Phường Vũ Ninh, Tỉnh Bắc Ninh
- Tham chiếu: Ngõ 160, Đường Ngõ 160 Đường Lý Thường Kiệt, Phường Vũ Ninh, Tỉnh Bắc Ninh
- Trường lệch: duong
- Cảnh báo: không có

Ngõ 160 bị đưa đồng thời vào trường ngõ và đường; output giữ tên đường Lý Thường Kiệt riêng.

## VNDEV_00337 — quy_uoc_ngo_co_ten_can_chot

- Input: 16, Ngõ Thịnh Quang, Thịnh Quang, ĐốngĐa, Hà Nội
- Output: Số 16, Ngõ Thịnh Quang, Phường Đống Đa, Thành phố Hà Nội
- Tham chiếu: Số 16, Đường Ngõ Thịnh Quang, Phường Đống Đa, Thành phố Hà Nội
- Trường lệch: ngo_ngach_hem, duong
- Cảnh báo: không có

Ngõ Thịnh Quang: output coi là ngõ, tham chiếu coi là tên đường chứa chữ Ngõ. Cần hợp đồng và nguồn tra; chưa kết luận lỗi thuật toán.

## VNDEV_00381 — nhan_lay_so_duong_lam_so_nha

- Input: 77, Đường số 6, Phường An Lạc, Thành phố Hồ Chí Minh
- Output: Số 77, Đường Số 6, Phường An Lạc, Thành phố Hồ Chí Minh
- Tham chiếu: Số 6, Đường Số 6, Phường An Lạc, Thành phố Hồ Chí Minh
- Trường lệch: so_nha
- Cảnh báo: không có

Input 77, Đường số 6 nhưng tham chiếu Số 6; output giữ Số 77.

## VNDEV_00390 — vai_tro_hanh_chinh_hay_duong_can_duyet

- Input: Bình Hàng Tây, Cao Lãnh, Đồng Tháp.
- Output: Xã Bình Hàng Trung, Tỉnh Đồng Tháp
- Tham chiếu: Đường Bình Hàng Tây, Cao Lãnh, Đồng Tháp., Tỉnh Đồng Tháp
- Trường lệch: duong, ma_xa
- Cảnh báo: không có

Bình Hàng Tây, Cao Lãnh, Đồng Tháp khớp quan hệ hành chính trong danh mục; tham chiếu đưa cả chuỗi vào đường. Cần duyệt nguồn, không coi nhánh bỏ hết hành chính là đáp án chắc chắn.

## VNDEV_00024 — loi_thuat_toan_suy_duong_qua_rong

- Input: Số 1 Lô 2 tập thể Viện Kỹ thuật quân sự, Phường Nghĩa Đô, Quận Cầu Giấy, Hà Nội
- Output: Số 1, Đường Lô 2 Tập Thể Viện Kỹ Thuật Quân Sự, Thành phố Hà Nội
- Tham chiếu: Số 1, Thành phố Hà Nội
- Trường lệch: duong
- Cảnh báo: xa_bi_chia, nhieu_cach_hieu, mo_ho_moc_cu_moi, duong_suy_tu_vi_tri, thieu_xa

Parser suy Lô 2 tập thể Viện Kỹ thuật quân sự thành đường sau Số 1. Chưa có căn cứ trong input để gán cụm lô/tập thể thành tên đường; cần cho phép O hoặc nhãn phụ.

## VNDEV_00031 — loi_thuat_toan_cat_cum_so_nha

- Input: 154-156, Phan Thanh, P. Thạc Gián, Q. Thanh Khê, TP. Đà Nẵng
- Output: Số 154, Phường Thanh Khê, Thành phố Đà Nẵng
- Tham chiếu: Số 154-156, Đường Phan Thanh, Phường Thanh Khê, Thành phố Đà Nẵng
- Trường lệch: so_nha, duong
- Cảnh báo: phan_chua_phan_loai

Input 154-156 bị giữ thành Số 154. Cần bảo toàn cụm số trước khi chọn quy ước chuẩn hóa; hiện mất thông tin nguồn.

## VNDEV_00036 — loi_thuat_toan_cat_cum_so_nha

- Input: Số 24B-24 Tôn Đản, Phường 13, quận 4, TP HCM
- Output: Số 24B, Đường - 24 Tôn Đản, Phường Xóm Chiếu, Thành phố Hồ Chí Minh
- Tham chiếu: Số 24B-24, Đường Tôn Đản, Phường Xóm Chiếu, Thành phố Hồ Chí Minh
- Trường lệch: so_nha, duong
- Cảnh báo: duong_suy_tu_vi_tri

Input Số 24B-24 bị cắt thành Số 24B và đẩy - 24 sang tên đường. Có lỗi ranh giới quan sát được trực tiếp.

## VNDEV_00342 — loi_thuat_toan_dau_nhay_ten_rieng

- Input: 129, Quốc lộ 27, D'Ran, Đơn Dương, Lâm Đồng
- Output: Số 129, Quốc lộ 27, Đường ' Ran, Tỉnh Lâm Đồng
- Tham chiếu: Số 129, Quốc lộ 27, Xã D’Ran, Tỉnh Lâm Đồng
- Trường lệch: duong, ma_xa
- Cảnh báo: nhieu_cach_hieu, thieu_xa

Tên D'Ran bị chia ở dấu nháy, D bị nhận thành tiền tố đường, sinh Đường ' Ran; không có đích D’Ran trong ứng viên. Đây là lỗi token/quét tên, không do beam.

## VNDEV_00553 — loi_thuat_toan_dau_nhay_ten_rieng

- Input: Số 10, Đường Trường Chinh, Thị trấn M'Drắk, Huyện M'Đrắk, Tỉnh Đắk Lắk
- Output: Số 10, Đường Trường Chinh, Tỉnh Đắk Lắk
- Tham chiếu: Số 10, Đường Trường Chinh, Xã M'Drắk, Tỉnh Đắk Lắk
- Trường lệch: ma_xa
- Cảnh báo: phan_chua_phan_loai, thieu_xa

M'Drắk có trong tên danh mục nhưng dấu nháy làm ngắt quét; không sinh được xã đích. Cần hỗ trợ dấu nháy nằm trong tên và biến thể dấu nháy.

## VNDEV_00505 — loi_thuat_toan_khong_uu_tien_dau_da_nhap

- Input: Số 18B, Đường Tây Sơn, Xã Tam Đàn, Huyện Phú Ninh, Tỉnh Quảng Nam
- Output: Số 18B, Đường Tây Sơn, Thành phố Đà Nẵng
- Tham chiếu: Số 18B, Đường Tây Sơn, Xã Chiên Đàn, Thành phố Đà Nẵng
- Trường lệch: ma_xa
- Cảnh báo: nhieu_cach_hieu, thieu_xa

Xã Tam Đàn và Xã Tam Dân cùng huyện Phú Ninh được 31.23 điểm cho input có dấu Tam Đàn. Mất thông tin dấu khiến output để trống xã dù nhánh đúng đã đứng đầu.

## VNDEV_01041 — loi_thuat_toan_chap_nhan_ten_cat_ngan

- Input: Số 204, Đường Phan Bội Châu, Xã Cát Tiên 2, Tỉnh Lâm Đồng
- Output: Số 204, Đường Phan Bội Châu, Tỉnh Lâm Đồng
- Tham chiếu: Số 204, Đường Phan Bội Châu, Xã Cát Tiên 2, Tỉnh Lâm Đồng
- Trường lệch: ma_xa
- Cảnh báo: nhieu_cach_hieu, thieu_xa

Nhánh Xã Cát Tiên 2 được 21.29 điểm; nhánh chỉ lấy Xã Cát Tiên để sót số 2 được 20.70. Chênh 0.59 nằm trong ngưỡng 0.65 nên gộp mơ hồ. Cần đánh giá ranh giới và bằng chứng còn sót, không chỉ tăng beam.

## VNDEV_01095 — mo_ho_cu_moi_can_nhan_tap_dich

- Input: Số 35, Đường Phạm Văn Đồng, Xã Lam Sơn, Tỉnh Thanh Hóa
- Output: Số 35, Đường Phạm Văn Đồng, Tỉnh Thanh Hóa
- Tham chiếu: Số 35, Đường Phạm Văn Đồng, Xã Lam Sơn, Tỉnh Thanh Hóa
- Trường lệch: ma_xa
- Cảnh báo: nhieu_cach_hieu, mo_ho_moc_cu_moi, thieu_xa

Xã Lam Sơn, Thanh Hóa khớp cả xã cũ Lam Sơn dẫn Minh Sơn và xã mới Lam Sơn. Không có huyện/mốc hay nguồn đường để phân biệt. Nhãn một đích từ bộ sinh tổng hợp không chứng minh input tự đủ thông tin.

## VNDEV_01119 — dau_ten_va_mo_ho_cu_moi

- Input: Số 402, Đường Ngô Quyền, Xã Đông Thành, Tỉnh Nghệ An
- Output: Số 402, Đường Ngô Quyền, Tỉnh Nghệ An
- Tham chiếu: Số 402, Đường Ngô Quyền, Xã Đông Thành, Tỉnh Nghệ An
- Trường lệch: ma_xa
- Cảnh báo: nhieu_cach_hieu, mo_ho_moc_cu_moi, thieu_xa

Đông Thành và Đồng Thành bị cùng khóa bỏ dấu; đồng thời có Đông Thành cũ và mới tại Nghệ An dẫn đích khác nhau. Cần tách lỗi mất dấu đã nhập khỏi nhập nhằng thực sự giữa hai mốc.

## VNDEV_00072 — mo_ho_cu_moi_can_nhan_tap_dich

- Input: 352, Phố Huế, Hai Bà Trưng, Hà Nội
- Output: Số 352, Phố Huế, Thành phố Hà Nội
- Tham chiếu: Số 352, Phố Huế, Phường Hai Bà Trưng, Thành phố Hà Nội
- Trường lệch: ma_xa
- Cảnh báo: nhieu_cach_hieu, thieu_xa

Hai Bà Trưng có thể là quận cũ hoặc phường mới; cả hai nhánh cùng 12.90 điểm. Thiếu nguồn đường/địa bàn để xác nhận một đích. Không nên huấn luyện xếp hạng ép theo nhãn này trước khi duyệt.

## VNDEV_00044 — nhan_bo_bang_chung_huyen_trong_input

- Input: 185 Đường 3/2, phường 11, Quận 10, Hồ Chí Minh, Việt Nam
- Output: Số 185, Đường 3/2, Thành phố Hồ Chí Minh
- Tham chiếu: Số 185, Đường 3/2, Phường Nhiêu Lộc, Thành phố Hồ Chí Minh
- Trường lệch: ma_xa
- Cảnh báo: mau_thuan_hanh_chinh, phan_chua_phan_loai, thieu_xa

Input ghi Quận 10 nhưng tham chiếu dùng Phường 11 thuộc Quận 3 trong danh mục. Có nhánh tái hiện nhãn bằng cách bỏ Quận 10; việc tồn tại nhánh đó không chứng minh cần sửa ranker để chọn nó.

## VNDEV_00097 — nhan_suy_tinh_tu_ten_duong

- Input: 244, Đường Điện Biên Phủ
- Output: Số 244, Đường Điện Biên Phủ
- Tham chiếu: Số 244, Đường Điện Biên Phủ, Tỉnh Điện Biên
- Trường lệch: ma_tinh
- Cảnh báo: thieu_xa, thieu_tinh

Input chỉ có 244, Đường Điện Biên Phủ; tham chiếu thêm tỉnh Điện Biên. Không có bằng chứng tỉnh độc lập hay từ điển đường trong hệ thống để xác nhận.

## VNDEV_00201 — nhan_suy_tinh_tu_ten_duong

- Input: 844E, Đường Song Hành Xa lộ Hà Nội
- Output: Số 844E, Đường Song Hành Xa Lộ Hà Nội
- Tham chiếu: Số 844E, Đường Song Hành Xa Lộ Hà Nội, Thành phố Hà Nội
- Trường lệch: ma_tinh
- Cảnh báo: thieu_xa, thieu_tinh

Hà Nội nằm trong tên Đường Song Hành Xa lộ Hà Nội; tham chiếu thêm tỉnh/thành Hà Nội. Input không cung cấp bằng chứng hành chính độc lập, chưa được phép ép output thêm tỉnh.
