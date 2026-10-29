# So sánh bản nền v1 và v2

Cùng 1136 mẫu dev và sáu bảng danh mục, đã đối chiếu mã băm.

Khớp đồng thời sáu trường: **685/1136 (60.299%) → 839/1136 (73.856%)**.

Có **154 mẫu mới khớp đủ sáu trường**, **0 mẫu từ khớp đủ sáu trường thành không khớp**. Các số này so với nhãn dev máy/tổng hợp, không phải đánh giá độc lập về độ chính xác thực tế.

| Trường | v1 (%) | v2 (%) | Mới khớp | Mất khớp |
|---|---:|---:|---:|---:|
| so_nha | 95.423 | 95.423 | 0 | 0 |
| ngo_ngach_hem | 96.479 | 99.384 | 34 | 1 |
| thon_xom | 98.944 | 99.472 | 6 | 0 |
| duong | 68.398 | 81.69 | 152 | 1 |
| ma_xa | 90.845 | 93.222 | 28 | 1 |
| ma_tinh | 96.743 | 98.944 | 26 | 1 |
| xa_phuong | 90.581 | 92.694 | 25 | 1 |
| tinh | 96.743 | 98.944 | 26 | 1 |
| dia_chi_chuan | 60.211 | 73.415 | 150 | 0 |

Một số trường riêng vẫn có thể mất khớp ở mẫu vốn chưa khớp toàn bộ; xem bảng và CSV đầy đủ. Không sửa nhãn tham chiếu để tăng điểm.

- OSM: 45.5% → 57.0%.
- Tổng hợp: 68.342% → 83.016%.

## Input và output thực tế

**VNDEV_00011**

Input: `Số nhà 3, phố Tô Vĩnh Diện, phường Khương Trung, quận Thanh Xuân, Hà Nội`

v1: `Số 3, Tổ Vĩnh Diện, Thành phố Hà Nội`

v2: `Số 3, Phố Tô Vĩnh Diện, Thành phố Hà Nội`

Nhãn tham chiếu: `Số 3, Phố Tô Vĩnh Diện, Thành phố Hà Nội`

Cảnh báo v2: `["xa_bi_chia", "thieu_xa"]`

**VNDEV_00017**

Input: `59 Tô Ngọc Vân, Khu phố 4, Phường Linh Tây, Quận Thủ Đức, Tp. HCM`

v1: `Số 59, Tổ Ngọc Vân, Khu phố 4, Thành phố Hồ Chí Minh`

v2: `Số 59, Khu phố 4, Đường Tô Ngọc Vân, Thành phố Hồ Chí Minh`

Nhãn tham chiếu: `Số 59, Khu phố 4, Đường Tô Ngọc Vân, Thành phố Hồ Chí Minh`

Cảnh báo v2: `["xa_bi_chia", "loai_hanh_chinh_khac_danh_muc", "duong_suy_tu_vi_tri", "thieu_xa"]`

**VNDEV_00003**

Input: `45 XÔ VIẾT NGHỆ TĨNH P.AN CƯ- NINH KIỀU- CẦN THƠ`

v1: `Số 45, Đường Xô Viết Nghệ, Thành phố Cần Thơ`

v2: `Số 45, Đường Xô Viết Nghệ Tĩnh, Thành phố Cần Thơ`

Nhãn tham chiếu: `Số 45, Thành phố Cần Thơ`

Cảnh báo v2: `["nhieu_cach_hieu", "mau_thuan_hanh_chinh", "phan_chua_phan_loai", "duong_suy_tu_vi_tri", "thieu_xa"]`

**VNDEV_00083**

Input: `386, Tên Lửa, Phường An Lạc, Thành phố Hồ Chí Minh`

v1: `Số 386, Đường Tên Lửa`

v2: `Số 386, Đường Tên Lửa, Phường An Lạc, Thành phố Hồ Chí Minh`

Nhãn tham chiếu: `Số 386, Đường Tên Lửa, Phường An Lạc, Thành phố Hồ Chí Minh`

Cảnh báo v2: `["duong_suy_tu_vi_tri"]`

**VNDEV_00044**

Input: `185 Đường 3/2, phường 11, Quận 10, Hồ Chí Minh, Việt Nam`

v1: `Số 185, Đường 3/2, Thành phố Hồ Chí Minh`

v2: `Số 185, Đường 3/2, Thành phố Hồ Chí Minh`

Nhãn tham chiếu: `Số 185, Đường 3/2, Phường Nhiêu Lộc, Thành phố Hồ Chí Minh`

Cảnh báo v2: `["mau_thuan_hanh_chinh", "phan_chua_phan_loai", "thieu_xa"]`

**VNDEV_00098**

Input: `Đường Đỗ Thị Tặng, Thị trấn Hòa Thành, Huyện Hòa Thành, Tây Ninh`

v1: `Đường Đỗ Thị Tặng, Tỉnh Tây Ninh`

v2: `Đường Đỗ Thị Tặng, Phường Hòa Thành, Tỉnh Tây Ninh`

Nhãn tham chiếu: `Đường Đỗ Thị Tặng, Phường Hòa Thành, Tỉnh Tây Ninh`

Cảnh báo v2: `["loai_hanh_chinh_khac_danh_muc"]`

**VNDEV_00404**

Input: `72 Đ.ĐộiCấn, X.Nga Liên, H.Nga Sơn, Tỉnh Thanh Hóa`

v1: `Số 72, Đường Đội Cấn, Xã Hồ Vương, Tỉnh Thanh Hóa`

v2: `Số 72, Đường Đội Cấn, Xã Hồ Vương, Tỉnh Thanh Hóa`

Nhãn tham chiếu: `Số 72, Đường Đội Cấn, Xã Hồ Vương, Tỉnh Thanh Hóa`

Cảnh báo v2: `[]`

**VNDEV_01113**

Input: `Số 72, Đường Hoàng Hoa Thám, Xã Bản Xèo, Tỉnh Lào Cai`

v1: `Số 72, Đường Hoàng Hoa Thám, Xã Bản Xèo, Tỉnh Lào Cai`

v2: `Số 72, Đường Hoàng Hoa Thám, Xã Bản Xèo, Tỉnh Lào Cai`

Nhãn tham chiếu: `Số 72, Đường Hoàng Hoa Thám, Xã Bản Xèo, Tỉnh Lào Cai`

Cảnh báo v2: `[]`

**VNDEV_00201**

Input: `844E, Đường Song Hành Xa lộ Hà Nội`

v1: `Số 844E, Đường Song Hành, Thành phố Hà Nội`

v2: `Số 844E, Đường Song Hành Xa Lộ Hà Nội`

Nhãn tham chiếu: `Số 844E, Đường Song Hành Xa Lộ Hà Nội, Thành phố Hà Nội`

Cảnh báo v2: `["thieu_xa", "thieu_tinh"]`

## Giới hạn và tệp đi kèm

- Chưa giải mọi tên riêng viết tắt hoặc phục hồi dấu mọi tên đường/thôn; nhãn dev vẫn có lỗi và nhiều mẫu chưa xác định được.
- Thiếu căn cứ về xã bị chia hay mốc cũ/mới thì giữ cảnh báo/ứng viên; không ép một đích để khớp nhãn.
- Tốc độ/RAM trong BAO_CAO.md là một lượt trên máy hiện tại, không phải phép so sánh hiệu năng có kiểm soát hay phép đo tải máy chủ.
- du_doan.jsonl: output đầy đủ và dấu vết từng mẫu.
- so_sanh_tung_mau.csv: input/output trước–sau và nhãn nguồn cho đủ 1.136 mẫu.
- loi_tung_truong.csv: chênh lệch còn lại.
- code_sha256.json và thong_ke.json: phiên bản source, dữ liệu và phép đo.
