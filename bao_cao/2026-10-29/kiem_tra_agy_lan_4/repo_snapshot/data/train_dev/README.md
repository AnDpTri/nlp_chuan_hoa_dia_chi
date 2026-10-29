# Bộ dữ liệu Huấn luyện (Train) và Phát triển (Dev)

Bộ dữ liệu này được xây dựng độc lập phục vụ phát triển và kiểm chứng các mô hình NLP trong dự án chuẩn hóa địa chỉ theo đơn vị hành chính sau sáp nhập mốc 01/07/2025.

> [!IMPORTANT]
> **Tập test được cô lập 100%**: Toàn bộ 400 mẫu trong tập test cuối (`data/test/dia_chi_test.csv`), các URL nguồn OSM và các chuỗi chuẩn hóa liên quan đã bị loại bỏ hoàn toàn khỏi tập train/dev. Tuyệt đối không dùng nhãn hoặc lỗi của tập test để can thiệp vào quá trình sinh train/dev.

---

## 1. Nguồn dữ liệu và phân loại nhãn

Bộ dữ liệu bao gồm hai nguồn thành phần được phân định rạch ròi qua các trường `loai_nhan` và `nguon_du_lieu`:

| Nguồn | Số mẫu Train | Số mẫu Dev | Tổng | Loại nhãn (`loai_nhan`) | Nguồn dữ liệu (`nguon_du_lieu`) | Mô tả & Độ tin cậy |
|---|:---:|:---:|:---:|:---:|:---:|---|
| **Địa chỉ thật từ OpenStreetMap (OSM)** | 1.600 | 400 | 2.000 | `nhan_may` | `osm_public` | Địa chỉ tự nhiên trích xuất từ các đối tượng công cộng trên OSM (đã loại 457 dòng rò rỉ/trùng test). Toàn bộ nhãn số nhà, đường, ngõ/hẻm được đối chiếu span trực tiếp từ `dau_vao`. **Nhãn là nhãn máy, chưa qua duyệt tay.** |
| **Địa chỉ tổng hợp từ Danh mục hành chính** | 2.964 | 736 | 3.700 | `tong_hop` | `danh_muc_hanh_chinh` | Sinh từ 500 đơn vị hành chính cơ sở đại diện, bao gồm cả mốc cũ, mốc mới, các xã bị chia, các ca có ngõ/ngách/hẻm, trộn mốc cũ-mới hợp lệ và lỗi gõ có chủ đích. **Số nhà và tên đường là giả định, không coi là địa chỉ thật đã xác minh.** |
| **Tổng cộng** | **4.564** | **1.136** | **5.700** | - | - | Tỷ lệ phân chia 80% Train / 20% Dev cố định bằng `seed = 42`. |

---

## 2. Các điểm cải tiến và chuẩn hóa dữ liệu quan trọng

1. **Gắn nhãn dựa hoàn toàn trên chuỗi `dau_vao` (Span-grounded Labels):**
   - Không lấy số nhà hoặc tên đường trực tiếp từ thẻ OSM nếu mâu thuẫn với chuỗi đầu vào.
   - Các lỗi span đã được khắc phục triệt để:
     * `Số 18B` trong `dau_vao` được gán nhãn đúng `Số 18B` (thay vì bị thẻ ghi đè thành `Số 18`).
     * `Số 402` trong `dau_vao` được gán nhãn đúng `Số 402` (thay vì bị thẻ ghi đè thành `Số 404`).
     * `Số 4A` trong `dau_vao` được gán nhãn đúng `Số 4A` (thay vì bị thẻ ghi đè thành `Số 4`).
     * `Chung cư C2 Xuân Đỉnh` không có tên đường trong `dau_vao` thì để trống trường `duong`, không bịa đặt thêm `Đường Ngách 1/2 Đỗ Nhuận`.
   - Mọi bản ghi đều có `osm_id` và `osm_type` trong `ghi_chu` để truy vết nguồn gốc 100%.

2. **Bổ sung trường Ngõ / Ngách / Hẻm / Kiệt (`ngo_ngach_hem`):**
   - Trích xuất tự nhiên từ các mẫu OSM có chứa ngõ, ngách, hẻm, kiệt.
   - Bổ sung biến thể tổng hợp có chứa ngõ/ngách/hẻm kết hợp số nhà và đường.
   - Tổng cộng: **611 mẫu** có trường `ngo_ngach_hem` khác rỗng (Train: **482 mẫu**, Dev: **129 mẫu**).

3. **Bổ sung các ca trộn mốc hành chính cũ-mới hợp lệ (`tron_moc_cu_moi`):**
   - Mô phỏng thực tế người dân viết kết hợp tên Xã mới sau sáp nhập nhưng vẫn giữ tên Quận/Huyện cũ.
   - Tính tương thích được kiểm tra nghiêm ngặt: Quận/Huyện cũ bắt buộc phải là đơn vị cha thực tế của xã cũ đã sáp nhập vào Xã mới theo bảng đối chiếu `doi_chieu_xa_cu_moi.csv`.
   - Tổng cộng: **380 mẫu** (Train: **307 mẫu**, Dev: **73 mẫu**).

4. **Bổ sung lỗi gõ chính tả có chủ đích (`loi_chinh_ta`):**
   - Mô phỏng các lỗi gõ tự nhiên phổ biến của người dùng Việt Nam:
     * Lỗi telex gõ thừa ký tự: `dduong`, `phuowng`, `thoon`.
     * Dính chữ không có dấu cách: `P.DịchVọng`, `Q.CầuGiấy`, `Đ.LêLợi`.
     * Mất dấu một từ thành phần: `Đuong`, `Phuong`.
   - Tổng cộng: **500 mẫu** (Train: **400 mẫu**, Dev: **100 mẫu**).

5. **Xử lý nhập nhằng mốc hành chính cũ / mới:**
   - Khi tên xã tồn tại ở cả mốc cũ và mới nhưng dẫn đến các kết quả khác nhau và không có huyện chứng thực, dữ liệu được phân loại `mo_ho_moc_cu_moi` và loại bỏ khỏi tập huấn luyện tin cậy thay vì mặc định mốc cũ.

---

## 3. Quy tắc chống rò rỉ dữ liệu (Data Leakage Prevention)

1. **Cô lập hoàn toàn với Tập Test:**
   - 457 dòng trong kho ứng viên OSM khớp với 400 địa chỉ test (theo URL nguồn, OSM ID, chuỗi nguyên văn hoặc chuỗi chuẩn hóa `norm()`) đã bị loại bỏ 100%.
   - Trùng lặp `Train` vs `Test`: **0 mẫu (0.00%)**.
   - Trùng lặp `Dev` vs `Test`: **0 mẫu (0.00%)**.
2. **Cô lập giữa Train và Dev (Group-based Split):**
   - Với dữ liệu tổng hợp: Phân chia theo `mau_goc_id`. Toàn bộ các biến thể sinh ra từ cùng một đơn vị hành chính cơ sở nằm trọn vẹn trong cùng một tập (cùng ở Train hoặc cùng ở Dev).
   - Với dữ liệu OSM: Phân chia theo đối tượng OSM (`osm_id` / `source_url`). Không có đối tượng nào bị rải rác sang cả hai tập.
   - Trùng lặp `Train` vs `Dev`: **0 mẫu (0.00%)**.
3. **Seed cố định:** Quá trình phân chia sử dụng `random.seed(42)` đảm bảo tính tái lập 100%.

---

## 4. Xử lý các xã bị chia tách (Fan-out > 1)

Tuân thủ nghiêm ngặt nguyên tắc mục 4 và 5 của `bai_toan.md`:
- Khi địa chỉ thuộc một xã cũ bị chia tách sang nhiều xã mới (440 xã cũ đa đích):
  - Hệ thống **KHÔNG tự ý chọn bừa một xã đích**.
  - Để trống `ma_xa` và `xa_phuong`.
  - Gắn cờ `"xa_bi_chia"` trong cột `canh_bao`.
  - Lưu đầy đủ danh sách các xã mới tiềm năng trong `ghi_chu` dưới dạng `xa_moi_ung_vien=[{"ma_xa": "...", "ten": "..."}, ...]`.
- Số lượng mẫu thuộc xã bị chia:
  - Tập Train: **563 mẫu**
  - Tập Dev: **137 mẫu**
  - Tổng cộng: **700 mẫu** giúp mô hình học cách phát hiện và xử lý đúng cờ `xa_bi_chia`.

---

## 5. Thống kê đặc trưng chi tiết

| Đặc trưng | Tập Train | Tập Dev | Toàn bộ Corpus |
|---|:---:|:---:|:---:|
| **Tổng số bản ghi** | **4.564** | **1.136** | **5.700** |
| Có ngõ/ngách/hẻm (`with_ngo_ngach_hem`) | 482 | 129 | 611 |
| Trộn mốc cũ-mới (`mixed_era_admin`) | 307 | 73 | 380 |
| Lỗi chính tả có chủ đích (`intentional_typos`) | 400 | 100 | 500 |
| Thuộc xã bị chia (`split_ward_count`) | 563 | 137 | 700 |
| Chuỗi không dấu (`unaccented_count`) | 405 | 102 | 507 |
| Chuỗi có viết tắt (`abbreviated_count`) | 352 | 88 | 440 |

---

## 6. Lệnh tái tạo và kiểm tra

```bash
# Sinh lại toàn bộ dữ liệu Train và Dev
py -3.12 data/train_dev/scripts/prepare_train_dev.py

# Kiểm tra toàn vẹn schema, quan hệ cha-con, span và chống rò rỉ
py -3.12 data/train_dev/scripts/validate_train_dev.py
```
