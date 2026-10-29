# Hướng dẫn Duyệt Nhãn Tập Kiểm Tra (Test Set Review Guide)

Tài liệu này hướng dẫn quy trình đối chiếu và duyệt nhãn 400 địa chỉ trong tập test (`data/test/dia_chi_test.csv`). Toàn bộ 400 mẫu hiện tại là **nhãn sơ bộ do máy gán** và bắt buộc phải được con người duyệt xác nhận trước khi dùng làm bộ đáp án vàng (Ground Truth) để chấm điểm mô hình NLP.

---

## 1. Tệp làm việc và công cụ hỗ trợ

- **Tệp bảng duyệt chính:** [`data/test/bang_duyet_test.csv`](bang_duyet_test.csv)
  - Đã được sắp xếp sẵn theo mức độ ưu tiên: **232 dòng `1_CAN_DUYET`** ở phía trên, tiếp theo là **168 dòng `2_TU_DONG_KHOP`**.
  - Tích hợp sẵn tên cơ sở/POI (`poi_name`), phương thức trích xuất (`input_mode`), cảnh báo máy (`canh_bao`) và danh sách xã mới ứng viên (`xa_ung_vien`).
- **Script kiểm tra tiến độ duyệt:**
  ```powershell
  py -3.12 data/test/scripts/kiem_tra_tien_do_duyet.py
  ```
- **Script đồng bộ sau khi duyệt:**
  ```powershell
  py -3.12 data/test/scripts/kiem_tra_tien_do_duyet.py --sync
  ```

---

## 2. Quy tắc duyệt từng trường

### 2.1. Các trường TUYỆT ĐỐI KHÔNG sửa đổi
- `id`: Mã định danh mẫu test (từ `VNTEST0001` đến `VNTEST0400`).
- `dau_vao`: Chuỗi địa chỉ đầu vào nguyên văn.
- `nguon`: Liên kết URL tới đối tượng OpenStreetMap (OSM node/way/relation).

### 2.2. Kiểm tra các thành phần địa chỉ chi tiết
1. **`so_nha`:**
   - Chuẩn hóa theo quy ước `Số <giá_trị>` (ví dụ: `12` -> `Số 12`).
   - Nếu số nhà có gạch chéo (`12/5`), xem xét ngữ cảnh: nếu là số nhà kèm ngõ/hẻm thì tách sang `ngo_ngach_hem` (`Số 12`, `Ngõ 5` hoặc `Hẻm 5`); nếu là số nhà kép giữ nguyên.
2. **`ngo_ngach_hem`:** Viết hoa tiền tố đúng quy ước: `Ngõ`, `Ngách`, `Hẻm`, `Kiệt`.
3. **`thon_xom`:** Viết hoa đúng tiền tố: `Thôn`, `Xóm`, `Ấp`, `Bản`, `Tổ dân phố`, `Khu phố`.
4. **`duong`:** Viết hoa tiền tố: `Đường`, `Phố`, `Đại lộ`, `Quốc lộ`, `Tỉnh lộ`. Tên riêng viết hoa đúng chính tả tiếng Việt.

### 2.3. Kiểm tra cấp hành chính & mốc chuyển đổi (01/07/2025)
1. **Địa chỉ theo mốc cũ:**
   - Xác định đúng `ma_xa_cu`, `ma_huyen_cu`, `ma_tinh_cu` từ danh mục 63 tỉnh/thành.
   - Tra bảng đối chiếu sang mốc mới 01/07/2025 (34 tỉnh, 3.321 xã).
2. **Xã cũ bị chia tách (`xa_bi_chia`):**
   - **Trường hợp A (Có chứng cứ chi tiết):** Nếu đầu vào có thông tin thôn, xóm hoặc tên đường đặc trưng mà văn bản hành chính phân định rõ thuộc xã mới nào -> Điền `ma_xa` và `xa_phuong` tương ứng; ghi rõ lý do và chứng cứ vào cột `ly_do_duyet`.
   - **Trường hợp B (Không đủ chứng cứ):** Giữ nguyên `ma_xa` rỗng, `xa_phuong` rỗng; giữ cờ `"xa_bi_chia"` trong `canh_bao`; bảo lưu danh sách `xa_ung_vien`. **Tuyệt đối không chọn bừa một xã.**
3. **Loại hình cấp tỉnh:**
   - Đảm bảo tuân thủ mốc 01/07/2025: Toàn quốc chỉ có 6 Thành phố trực thuộc Trung ương (Hà Nội, Hải Phòng, Huế, Đà Nẵng, TP.HCM, Cần Thơ).
   - Quảng Ninh, Bắc Ninh, Đồng Nai tại mốc này là `Tỉnh` (không ghi `Thành phố`).

---

## 3. Điền thông tin kiểm toán bắt buộc (Audit Trail)

Với mỗi dòng sau khi người duyệt kiểm tra hoặc chỉnh sửa, bắt buộc phải điền đầy đủ 5 cột kiểm toán tại `bang_duyet_test.csv`:

| Cột kiểm toán | Giá trị quy định | Ví dụ |
|---|---|---|
| `trang_thai_duyet` | Bắt buộc điền `da_duyet` (hoặc `can_xem_lai` nếu chưa chốt được) | `da_duyet` |
| `nguoi_duyet` | Họ tên hoặc mã định danh của thành viên nhóm trực tiếp duyệt | `NguyenVanA` |
| `ngay_duyet` | Ngày thực hiện duyệt theo định dạng ISO `YYYY-MM-DD` | `2026-10-30` |
| `thay_doi` | Tóm tắt các trường đã điều chỉnh, hoặc ghi `Không thay đổi` | `Sửa đường: Đường Lê Lợi -> Phố Lê Lợi` hoặc `Không thay đổi` |
| `ly_do_duyet` | Căn cứ pháp lý, đối chiếu biển hiệu POI OSM hoặc xác minh bản đồ | `Đối chiếu biển hiệu cửa hàng trên OSM node 123456` |

> [!CAUTION]
> Hệ thống kiểm tra tự động (`validate_dataset.py`) sẽ **báo lỗi FAIL ngay lập tức** nếu phát hiện:
> - Dòng nào đánh dấu `da_duyet` nhưng để trống `nguoi_duyet`, `ngay_duyet` hoặc `ly_do_duyet`.
> - Chữ ký mang tên robot/bot tự động (`bot`, `ai`, `agy`, `gemini`). Chỉ chấp nhận xác nhận từ con người thực tế.

---

## 4. Quy trình phối hợp duyệt nhóm

1. **Bước 1:** Mở tệp `data/test/bang_duyet_test.csv` bằng Excel hoặc trình chỉnh sửa CSV.
2. **Bước 2:** Ưu tiên duyệt trước **232 dòng `1_CAN_DUYET`** (các dòng có cảnh báo phức tạp, số nhà gạch chéo, hoặc xã bị chia).
3. **Bước 3:** Đối soát **168 dòng `2_TU_DONG_KHOP`** (kiểm tra nhanh tên đường và số nhà).
4. **Bước 4:** Kiểm tra tiến độ và tính hợp lệ của chữ ký:
   ```powershell
   py -3.12 data/test/scripts/kiem_tra_tien_do_duyet.py
   ```
5. **Bước 5:** Khi hoàn tất một đợt duyệt, chạy lệnh đồng bộ để cập nhật nhãn chính thức vào `dia_chi_test.csv`:
   ```powershell
   py -3.12 data/test/scripts/kiem_tra_tien_do_duyet.py --sync
   ```
6. **Bước 6:** Chạy kiểm tra toàn diện:
   ```powershell
   py -3.12 data/test/scripts/validate_dataset.py
   ```
   Khi toàn bộ 400 dòng đã có chữ ký người duyệt hợp lệ, thuộc tính `is_ready_for_gold_evaluation` trong `validation.json` sẽ chuyển sang `true`, xác nhận tập test chính thức sẵn sàng dùng để đánh giá mô hình.
