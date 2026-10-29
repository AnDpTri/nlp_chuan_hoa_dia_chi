# Chẩn đoán pipeline v2 trước khi tối ưu tiếp

Dev 1136 mẫu; lõi giữ nguyên baseline_luat_v2, beam=40. Không dùng test cuối, không huấn luyện, không sửa nhãn.

**Tất cả số khớp/lệch bên dưới đều so với nhãn máy/tổng hợp, chưa xác minh độc lập.**

## Khả năng khớp nhãn qua các bước

- Output cuối khớp sáu trường: 839/1136.
- Có ít nhất một nhánh khớp sáu trường trong beam gốc: 890/1136.
- Trong các ca lệch chưa có nhánh khớp, beam đối chứng 160 tìm thêm 0 nhánh khớp.

Oracle ở đây là khả năng tái hiện nhãn, không xác nhận nhãn đúng và không chứng minh mô hình thực tế đạt được tỷ lệ đó.

## Nhóm cơ chế lệch sáu trường

| Nhóm | Số mẫu |
|---|---:|
| co_nhanh_dung_ma_nhung_chi_tiet_chua_khop_nhan | 228 |
| co_nhanh_khop_6_nhung_xep_sau | 30 |
| khop_6_truong | 839 |
| chua_tach_duoc_hanh_chinh_chi_tiet_va_nhan | 18 |
| quyet_dinh_giu_mo_ho_lam_lech_nhan | 21 |

Nhóm có nhánh khớp nhưng xếp sau có thể bao gồm nhãn bỏ sót thông tin hoặc nhãn sai. Nhóm chi tiết bao gồm lỗi tách, phục hồi dấu và vấn đề nhãn; không tự quy toàn bộ cho parser.

## Chẩn đoán mã xã và tỉnh

| Nhóm | Số mẫu |
|---|---:|
| nhan_va_du_doan_cung_trong_xa | 198 |
| khop_ma_xa_va_tinh | 861 |
| nhan_xa_trong_du_doan_co | 22 |
| co_nhanh_dung_ma_nhung_xep_sau | 20 |
| khong_sinh_dich_tham_chieu | 13 |
| giu_mo_ho_o_buoc_quyet_dinh | 22 |

Với nhãn xã có giá trị: tìm tập con ứng viên hợp lệ chốt duy nhất đúng cặp mã. Nếu tìm được mà beam gốc không giữ được thì có chứng cứ cắt beam. Nếu duyệt hết không tìm được, chỉ kết luận không chốt được từ bộ ứng viên và quan hệ hiện tại; chưa kết luận địa chỉ thực tế bất khả định. Duyệt quá giới hạn được báo riêng. Chứng cứ có thể bỏ qua phần input khác, nên vẫn cần rà ngữ nghĩa.

## Điền trường và để trống

| Trường | Điền khớp | Điền lệch | Trống khi nhãn có | Cùng trống | Lệch / số điền (%) |
|---|---:|---:|---:|---:|---:|
| so_nha | 922 | 32 | 20 | 162 | 3.354 |
| ngo_ngach_hem | 129 | 7 | 0 | 1000 | 5.147 |
| thon_xom | 21 | 6 | 0 | 1109 | 22.222 |
| duong | 835 | 157 | 51 | 93 | 15.827 |
| ma_xa | 861 | 23 | 54 | 198 | 2.602 |
| ma_tinh | 1124 | 1 | 11 | 0 | 0.089 |

## Cảnh báo có phân biệt được ca lệch không?

| Nhóm | Mẫu | Bao phủ (%) | Khớp 6 | Lệch 6 | Lệch / nhóm (%) |
|---|---:|---:|---:|---:|---:|
| tat_ca | 1136 | 100.0 | 839 | 297 | 26.144 |
| khong_co_bat_ky_canh_bao_nao | 655 | 57.658 | 635 | 20 | 3.053 |
| co_it_nhat_mot_canh_bao | 481 | 42.342 | 204 | 277 | 57.588 |

Đây chỉ là phép lọc theo cảnh báo sẵn có; không phải bộ ước lượng xác suất hoặc chính sách tự động đã được kiểm định.

## Chênh lệch chi tiết

| Trường | Lệch | Chỉ khác dấu | Lệch nhưng có nhánh khớp trường |
|---|---:|---:|---:|
| so_nha | 52 | 0 | 1 |
| ngo_ngach_hem | 7 | 0 | 3 |
| thon_xom | 6 | 0 | 0 |
| duong | 208 | 97 | 9 |

## Cờ cần rà nhãn

| Dấu hiệu | Số mẫu mang cờ |
|---|---:|
| noi_dung_nhan_chong_lan:duong | 40 |
| noi_dung_nhan_nhieu_vi_tri:duong | 13 |
| noi_dung_nhan_nhieu_vi_tri:so_nha | 6 |
| noi_dung_nhan_khong_can_chinh:duong | 13 |
| noi_dung_nhan_khong_can_chinh:so_nha | 2 |
| noi_dung_nhan_nhieu_vi_tri:ngo_ngach_hem | 4 |
| noi_dung_nhan_chong_lan:ngo_ngach_hem | 1 |
| noi_dung_nhan_nhieu_vi_tri:thon_xom | 1 |
| ten_dich_khac_ma:xa_phuong | 6 |

Các cờ có thể chồng nhau. Căn chỉnh nội dung bỏ dấu không chứng minh vai trò địa chỉ; một cờ cũng không đủ để kết luận nhãn sai.

## Ví dụ đầy đủ theo cơ chế

### co_nhanh_dung_ma_nhung_chi_tiet_chua_khop_nhan

**VNDEV_00001** (osm_public)

- Input: 843M+RH3 Hòa Thành District, Tây Ninh
- Output: Tỉnh Tây Ninh
- Tham chiếu: Số 843M, Tỉnh Tây Ninh
- Trường lệch: so_nha
- Cờ rà nhãn: không có cờ tự động

**VNDEV_00002** (osm_public)

- Input: 45B Hoàng Văn Thụ Ninh Kiều Cần Thơ
- Output: Số 45B, Đường Hoàng Văn Thụ, Thành phố Cần Thơ
- Tham chiếu: Số 45B, Thành phố Cần Thơ
- Trường lệch: duong
- Cờ rà nhãn: không có cờ tự động

**VNDEV_00003** (osm_public)

- Input: 45 XÔ VIẾT NGHỆ TĨNH P.AN CƯ- NINH KIỀU- CẦN THƠ
- Output: Số 45, Đường Xô Viết Nghệ Tĩnh, Thành phố Cần Thơ
- Tham chiếu: Số 45, Thành phố Cần Thơ
- Trường lệch: duong
- Cờ rà nhãn: không có cờ tự động

### co_nhanh_khop_6_nhung_xep_sau

**VNDEV_00007** (osm_public)

- Input: 87 CMT8, An Hòa, Ninh Kiều, Cần Thơ
- Output: Số 87, Phường Cái Khế, Thành phố Cần Thơ
- Tham chiếu: Số 87, Thành phố Cần Thơ
- Trường lệch: ma_xa
- Cờ rà nhãn: không có cờ tự động

**VNDEV_00014** (osm_public)

- Input: TM28-CC.8X-Plus 22/1422/14A/22/1422/14Cvà 22/14D Đường Trường Chinh, Phường Tân Thới Nhât.Quận 12,Tp HCM
- Output: Đường Trường Chinh, Phường Đông Hưng Thuận, Thành phố Hồ Chí Minh
- Tham chiếu: Đường Trường Chinh, Thành phố Hồ Chí Minh
- Trường lệch: ma_xa
- Cờ rà nhãn: không có cờ tự động

**VNDEV_00033** (osm_public)

- Input: 343S Lạc Long Quân, Phường 5- Quận 11 - Tp. Hồ Chí Minh
- Output: Số 343S, Đường Lạc Long Quân, Phường Hòa Bình, Thành phố Hồ Chí Minh
- Tham chiếu: Số 343S, Đường Lạc Long Quân, Thành phố Hồ Chí Minh
- Trường lệch: ma_xa
- Cờ rà nhãn: không có cờ tự động

### chua_tach_duoc_hanh_chinh_chi_tiet_va_nhan

**VNDEV_00085** (osm_public)

- Input: 19/10, Đường Bình Thới, 11, Ho Chi Minh City, Thành Phố Hồ Chí Minh
- Output: Số 19/10, Đường Bình Thới, Thành phố Hồ Chí Minh
- Tham chiếu: Số 19/10, Đường Bình Thới, Phường Phú Thọ, Thành phố Hồ Chí Minh
- Trường lệch: ma_xa
- Cờ rà nhãn: không có cờ tự động

**VNDEV_00087** (osm_public)

- Input: 22 Tân Hồng - tổ 85 - KT - HN
- Output: Số 22, Tổ 85 - Kt - Hn
- Tham chiếu: Số 22, Đường 22 Tân Hồng - Tổ 85 - Kt - Hn, Thành phố Hà Nội
- Trường lệch: thon_xom, duong, ma_tinh
- Cờ rà nhãn: noi_dung_nhan_chong_lan:duong

**VNDEV_00097** (osm_public)

- Input: 244, Đường Điện Biên Phủ
- Output: Số 244, Đường Điện Biên Phủ
- Tham chiếu: Số 244, Đường Điện Biên Phủ, Tỉnh Điện Biên
- Trường lệch: ma_tinh
- Cờ rà nhãn: không có cờ tự động

### quyet_dinh_giu_mo_ho_lam_lech_nhan

**VNDEV_00108** (osm_public)

- Input: Đường N2, Dĩ An, Bình Dương
- Output: Đường N2, Thành phố Hồ Chí Minh
- Tham chiếu: Đường N2, Phường Dĩ An, Thành phố Hồ Chí Minh
- Trường lệch: ma_xa
- Cờ rà nhãn: không có cờ tự động

**VNDEV_00128** (osm_public)

- Input: 268, Lý Thường Kiệt, 14, 10, Ho Chi Minh City
- Output: Số 268, Đường Lý Thường Kiệt
- Tham chiếu: Số 268, Đường Lý Thường Kiệt, Thành phố Hồ Chí Minh
- Trường lệch: ma_tinh
- Cờ rà nhãn: không có cờ tự động

**VNDEV_00129** (osm_public)

- Input: 194, Hoàng Văn Thụ, Ho Chi Minh City
- Output: Số 194, Đường Hoàng Văn Thụ
- Tham chiếu: Số 194, Đường Hoàng Văn Thụ, Thành phố Hồ Chí Minh
- Trường lệch: ma_tinh
- Cờ rà nhãn: không có cờ tự động

## Tệp và tái lập

- `doi_chieu_day_du.csv`: tất cả input/output/tham chiếu và sáu trường riêng.
- `cac_ca_lech.csv`: chỉ các ca lệch sáu trường, không tự coi tham chiếu là chân lý.
- `chan_doan_tung_mau.jsonl`: nhánh đầu, nhánh khớp nếu có, tập đích, điểm và chứng cứ duyệt tập con.
- `thong_ke_chan_doan.json`: mã băm source/dev/danh mục và chỉ số đầy đủ.

```powershell
py -3.12 -X utf8 -B -m danh_gia.chan_doan_pipeline --output-dir danh_gia/ket_qua/chan_doan_lan_moi
```

Mỗi lần chạy phải tạo thư mục mới. Kiểm tra source/danh mục/input trùng lần đo v2, chạy lại API thật và đối chiếu toàn bộ kết quả từng mẫu; kiểm tra nhánh tái hiện khớp API; kiểm tra hash lại khi kết thúc.

## Giới hạn

- Mọi khớp/lệch đều so với nhãn máy/tổng hợp chưa xác minh độc lập.
- Oracle là khả năng khớp nhãn trong nhánh đã xét, không là độ chính xác mô hình có thể đạt.
- Nhánh chứng cứ tập con có thể bỏ qua bằng chứng khác trong input; không bảo đảm đúng ngữ nghĩa.
- Không có nhánh chốt duy nhất không chứng minh đầu vào thực tế thiếu thông tin; nguồn tra/ứng viên có thể thiếu.
- Beam rộng chỉ chẩn đoán trên các mẫu lệch và không có nhánh khớp trong beam gốc; không tối ưu cấu hình.
- Các cờ căn chỉnh là dấu hiệu cần duyệt, không tự xác nhận nhãn sai.
- Không cảnh báo không đồng nghĩa xác suất đúng cao; chưa hiệu chuẩn độ tin cậy.
