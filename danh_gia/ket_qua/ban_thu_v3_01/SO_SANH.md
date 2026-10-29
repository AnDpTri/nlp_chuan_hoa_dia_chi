# So sánh baseline_luat_v2 và baseline_luat_v3

Cùng 1136 mẫu dev và sáu bảng danh mục, đã đối chiếu mã băm.

Khớp đồng thời sáu trường: **839/1136 (73.856%) → 869/1136 (76.496%)**.

Có **32 mẫu mới khớp đủ sáu trường**, **2 mẫu từ khớp đủ sáu trường thành không khớp**. Các số này so với nhãn dev máy/tổng hợp, không phải đánh giá độc lập về độ chính xác thực tế.

| Trường | Trước (%) | Sau (%) | Mới khớp | Mất khớp |
|---|---:|---:|---:|---:|
| so_nha | 95.423 | 96.567 | 13 | 0 |
| ngo_ngach_hem | 99.384 | 99.384 | 0 | 0 |
| thon_xom | 99.472 | 99.472 | 0 | 0 |
| duong | 81.69 | 82.13 | 7 | 2 |
| ma_xa | 93.222 | 95.423 | 25 | 0 |
| ma_tinh | 98.944 | 99.12 | 2 | 0 |
| xa_phuong | 92.694 | 94.894 | 25 | 0 |
| tinh | 98.944 | 99.12 | 2 | 0 |
| dia_chi_chuan | 73.415 | 76.056 | 32 | 2 |

Một số trường riêng vẫn có thể mất khớp ở mẫu vốn chưa khớp toàn bộ; xem bảng và CSV đầy đủ. Không sửa nhãn tham chiếu để tăng điểm.

- OSM: 57.0% → 60.0%.
- Tổng hợp: 83.016% → 85.462%.

## Input và output thực tế

**VNDEV_00024**

Input: `Số 1 Lô 2 tập thể Viện Kỹ thuật quân sự, Phường Nghĩa Đô, Quận Cầu Giấy, Hà Nội`

Trước (baseline_luat_v2): `Số 1, Đường Lô 2 Tập Thể Viện Kỹ Thuật Quân Sự, Thành phố Hà Nội`

Sau (baseline_luat_v3): `Số 1, Thành phố Hà Nội`

Nhãn tham chiếu: `Số 1, Thành phố Hà Nội`

Cảnh báo sau: `["xa_bi_chia", "nhieu_cach_hieu", "mo_ho_moc_cu_moi", "phan_chua_phan_loai", "thieu_xa"]`

**VNDEV_00031**

Input: `154-156, Phan Thanh, P. Thạc Gián, Q. Thanh Khê, TP. Đà Nẵng`

Trước (baseline_luat_v2): `Số 154, Phường Thanh Khê, Thành phố Đà Nẵng`

Sau (baseline_luat_v3): `Số 154-156, Đường Phan Thanh, Phường Thanh Khê, Thành phố Đà Nẵng`

Nhãn tham chiếu: `Số 154-156, Đường Phan Thanh, Phường Thanh Khê, Thành phố Đà Nẵng`

Cảnh báo sau: `["duong_suy_tu_vi_tri", "so_nha_can_duyet", "ten_chi_tiet_chua_xac_minh_dau"]`

**VNDEV_00036**

Input: `Số 24B-24 Tôn Đản, Phường 13, quận 4, TP HCM`

Trước (baseline_luat_v2): `Số 24B, Đường - 24 Tôn Đản, Phường Xóm Chiếu, Thành phố Hồ Chí Minh`

Sau (baseline_luat_v3): `Số 24B-24, Đường Tôn Đản, Phường Xóm Chiếu, Thành phố Hồ Chí Minh`

Nhãn tham chiếu: `Số 24B-24, Đường Tôn Đản, Phường Xóm Chiếu, Thành phố Hồ Chí Minh`

Cảnh báo sau: `["duong_suy_tu_vi_tri", "so_nha_can_duyet"]`

**VNDEV_00342**

Input: `129, Quốc lộ 27, D'Ran, Đơn Dương, Lâm Đồng`

Trước (baseline_luat_v2): `Số 129, Quốc lộ 27, Đường ' Ran, Tỉnh Lâm Đồng`

Sau (baseline_luat_v3): `Số 129, Quốc lộ 27, Xã D’Ran, Tỉnh Lâm Đồng`

Nhãn tham chiếu: `Số 129, Quốc lộ 27, Xã D’Ran, Tỉnh Lâm Đồng`

Cảnh báo sau: `[]`

**VNDEV_00505**

Input: `Số 18B, Đường Tây Sơn, Xã Tam Đàn, Huyện Phú Ninh, Tỉnh Quảng Nam`

Trước (baseline_luat_v2): `Số 18B, Đường Tây Sơn, Thành phố Đà Nẵng`

Sau (baseline_luat_v3): `Số 18B, Đường Tây Sơn, Xã Chiên Đàn, Thành phố Đà Nẵng`

Nhãn tham chiếu: `Số 18B, Đường Tây Sơn, Xã Chiên Đàn, Thành phố Đà Nẵng`

Cảnh báo sau: `[]`

**VNDEV_00553**

Input: `Số 10, Đường Trường Chinh, Thị trấn M'Drắk, Huyện M'Đrắk, Tỉnh Đắk Lắk`

Trước (baseline_luat_v2): `Số 10, Đường Trường Chinh, Tỉnh Đắk Lắk`

Sau (baseline_luat_v3): `Số 10, Đường Trường Chinh, Xã M'Drắk, Tỉnh Đắk Lắk`

Nhãn tham chiếu: `Số 10, Đường Trường Chinh, Xã M'Drắk, Tỉnh Đắk Lắk`

Cảnh báo sau: `[]`

**VNDEV_01041**

Input: `Số 204, Đường Phan Bội Châu, Xã Cát Tiên 2, Tỉnh Lâm Đồng`

Trước (baseline_luat_v2): `Số 204, Đường Phan Bội Châu, Tỉnh Lâm Đồng`

Sau (baseline_luat_v3): `Số 204, Đường Phan Bội Châu, Xã Cát Tiên 2, Tỉnh Lâm Đồng`

Nhãn tham chiếu: `Số 204, Đường Phan Bội Châu, Xã Cát Tiên 2, Tỉnh Lâm Đồng`

Cảnh báo sau: `[]`

**VNDEV_01095**

Input: `Số 35, Đường Phạm Văn Đồng, Xã Lam Sơn, Tỉnh Thanh Hóa`

Trước (baseline_luat_v2): `Số 35, Đường Phạm Văn Đồng, Tỉnh Thanh Hóa`

Sau (baseline_luat_v3): `Số 35, Đường Phạm Văn Đồng, Tỉnh Thanh Hóa`

Nhãn tham chiếu: `Số 35, Đường Phạm Văn Đồng, Xã Lam Sơn, Tỉnh Thanh Hóa`

Cảnh báo sau: `["nhieu_cach_hieu", "mo_ho_moc_cu_moi", "thieu_xa"]`

**VNDEV_00044**

Input: `185 Đường 3/2, phường 11, Quận 10, Hồ Chí Minh, Việt Nam`

Trước (baseline_luat_v2): `Số 185, Đường 3/2, Thành phố Hồ Chí Minh`

Sau (baseline_luat_v3): `Số 185, Đường 3/2, Thành phố Hồ Chí Minh`

Nhãn tham chiếu: `Số 185, Đường 3/2, Phường Nhiêu Lộc, Thành phố Hồ Chí Minh`

Cảnh báo sau: `["mau_thuan_hanh_chinh", "phan_chua_phan_loai", "thieu_xa"]`

**VNDEV_00201**

Input: `844E, Đường Song Hành Xa lộ Hà Nội`

Trước (baseline_luat_v2): `Số 844E, Đường Song Hành Xa Lộ Hà Nội`

Sau (baseline_luat_v3): `Số 844E, Đường Song Hành Xa Lộ Hà Nội`

Nhãn tham chiếu: `Số 844E, Đường Song Hành Xa Lộ Hà Nội, Thành phố Hà Nội`

Cảnh báo sau: `["thieu_xa", "thieu_tinh"]`

## Giới hạn và tệp đi kèm

- Chưa giải mọi tên riêng viết tắt hoặc phục hồi dấu mọi tên đường/thôn; nhãn dev vẫn có lỗi và nhiều mẫu chưa xác định được.
- Thiếu căn cứ về xã bị chia hay mốc cũ/mới thì giữ cảnh báo/ứng viên; không ép một đích để khớp nhãn.
- Tốc độ/RAM trong BAO_CAO.md là một lượt trên máy hiện tại, không phải phép so sánh hiệu năng có kiểm soát hay phép đo tải máy chủ.
- du_doan.jsonl: output đầy đủ và dấu vết từng mẫu.
- so_sanh_tung_mau.csv: input/output trước–sau và nhãn nguồn cho đủ 1.136 mẫu.
- loi_tung_truong.csv: chênh lệch còn lại.
- code_sha256.json và thong_ke.json: phiên bản source, dữ liệu và phép đo.
