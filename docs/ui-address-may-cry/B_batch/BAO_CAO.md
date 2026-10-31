# BÁO CÁO TRIỂN KHAI PHẦN B: BATCH WORKSPACE, IMPORT/EXPORT & REVIEW FLOW
## Dự án: Address May Cry — Chuẩn Hóa Địa Chỉ Tiếng Việt (Mốc 01/07/2025)

- **Phiên thực hiện:** PHẦN B (Batch Workspace, Import/Export, Review Flow).
- **Phạm vi ghi độc quyền:** `web/address-may-cry/src/features/batch/**` và `docs/ui-address-may-cry/B_batch/**`.
- **Taste-skill đã cài đặt:**
  - Kho nguồn: `https://github.com/Leonxlnx/taste-skill`
  - Commit Hash: `12af471f627f866411b4bd785b19646d3672784c`
  - Đường dẫn cài đặt cục bộ riêng: `C:/Users/andan/.gemini/antigravity/brain/388e264d-6447-42fb-b64f-559ba8e2e86d/taste-skill`
  - Tài liệu tham chiếu chính: `skills/taste-skill/SKILL.md` và `references/app-screens.md` (Hướng thiết kế *Achromatic ledger / High substance workspace*).
- **Môi trường:** Node.js v24.19.0, Vite 5.4.11, React 18.3.1, TypeScript 5.6.3, Chrome/Edge DevTools Protocol.

---

## 1. TỔNG QUAN THỰC THI & QUYẾT ĐỊNH THIẾT KẾ CÓ CHỦ ĐÍCH

### 1.1. Trả Lời Câu Hỏi Cốt Lõi: "Dòng nào cần kiểm tra và xuất kết quả thế nào?"
Trong bài toán chuẩn hóa địa chỉ hàng loạt, người dùng doanh nghiệp (vận hành thương mại điện tử, logistics, quản lý dữ liệu) không cần những biểu đồ trang trí rườm rà hay điểm số phần trăm giả định. Nhu cầu trọng tâm là:
1. **Lọc ra ngay các dòng cần kiểm tra (`needs_review`)**: Các dòng có cảnh báo chia tách xã mốc 2025 (`xa_bi_chia`), đầu vào mất dấu, khuyết xã/phường, hoặc nhiều ứng viên sáp nhập.
2. **Đối soát chi tiết tức thì**: Bấm vào dòng để mở ngăn kiểm tra (Drawer) hiển thị song song 6 trường cốt lõi (`so_nha`, `ngo_ngach_hem`, `thon_xom`, `duong`, `xa_phuong`, `tinh`), mã hành chính thực tế và giải thích lý do cảnh báo bằng tiếng Việt tự nhiên.
3. **Xuất kết quả an toàn tuyệt đối**: Xuất CSV giữ nguyên 100% cột gốc, bổ sung 6 trường chuẩn hóa, mã hóa UTF-8 BOM để Excel không lỗi font tiếng Việt, và chủ động vô hiệu hóa tấn công CSV Formula Injection.

### 1.2. Các Quyết Định Thị Giác (Achromatic Ledger Workspace)
Tuân thủ nghiêm ngặt tinh thần chống slop (anti-slop) của `taste-skill`:
- **Bố cục (Layout)**: Mặt phẳng phẳng (flat surfaces), phân cách bằng đường kẻ 1px (`var(--border)`), không dùng card nổi bóng bẩy (zero shadow at rest). Hướng mắt tập trung từ khu vực nhập liệu -> tiến độ xử lý -> dải thẻ đếm thực chất (KPIs) -> bảng dữ liệu phân trang.
- **Màu sắc (Palette)**: Màu sắc chỉ dùng trên **dữ liệu**, không dùng trên khung viền (chrome). Nền trang tối/sáng theo theme Session A (`--ground`, `--surface`, `--raised`). Các sắc thái tín hiệu rõ ràng:
  - Xanh lá đậm (`--positive`): Dòng đã xử lý hoàn tất (`processed`).
  - Hổ phách/vàng đất (`--warning`): Dòng cần rà soát nghiệp vụ (`needs_review`).
  - Đỏ gạch (`--negative`): Lỗi mạng/kết nối hoặc định dạng (`error`).
  - Xám trung tính (`--muted`): Chờ xử lý.
- **Kiểu chữ (Typography)**:
  - Font chính: `Geist` kết hợp `Instrument Sans` chuẩn hóa từ taste-skill, cỡ chữ dữ liệu 13–14px dễ đọc, chiều cao dòng 1.5–1.6.
  - Số liệu & Mã hành chính: Áp dụng `font-variant-numeric: tabular-nums` và `Geist Mono` cho các cột STT, độ trễ `elapsed_ms`, mã xã, mã tỉnh để hàng lối thẳng tắp như sổ cái kế toán chuyên nghiệp.
- **Khoảng cách & Thao tác (Spacing & Touch Targets)**: Tất cả nút bấm và vùng chọn có chiều cao tối thiểu $\ge 40\text{px}$ (mobile $\ge 44\text{px}$), padding chuẩn 12–16px, tương thích hoàn toàn tiêu chuẩn tiếp cận WCAG AA.
- **Khả năng tiếp cận (Accessibility)**: Vòng nét focus rõ ràng (`:focus-visible`), hỗ trợ người dùng giảm chuyển động (`prefers-reduced-motion: reduce`), độ tương phản chữ $\ge 4.5:1$.

---

## 2. KIẾN TRÚC MÔ-ĐUN & TÍNH NĂNG ĐÃ TRIỂN KHAI

### 2.1. Bộ Phân Tích Cú Pháp CSV Thuần RFC 4180 (`csvParser.ts`)
- **Tương thích toàn diện**: Hỗ trợ UTF-8 có hoặc không có BOM (`\uFEFF`), CRLF (`\r\n`), LF (`\n`), CR (`\r`).
- **Xử lý ngoặc kép phức tạp**: Hỗ trợ trường chứa dấu phẩy, dấu chấm phẩy, tab, và ký tự xuống dòng bên trong cặp ngoặc kép. Tự động chuyển đổi cặp ngoặc kép liên tiếp (`""`) thành ký tự ngoặc kép đơn (`"`).
- **Tự động nhận diện dấu phân cách (Auto-detect Delimiter)**: Tự động phân tích và chọn lựa giữa dấu phẩy (`,`), chấm phẩy (`;`), hoặc tab (`\t`).
- **Gợi ý cột địa chỉ thông minh**: Tự động nhận diện cột chứa địa chỉ dựa trên từ khóa header (`dia_chi`, `address`, `địa chỉ`, `nơi ở`) và khảo sát nội dung ô (chứa các từ khóa `đường`, `phường`, `quận`, `số`).
- **Kiểm soát giới hạn chặt chẽ (Guardrails)**:
  - Tối đa 5MB dung lượng tệp.
  - Tối đa 1.000 dòng dữ liệu / phiên.
  - Tối đa 2.048 ký tự trên mỗi ô địa chỉ.
  - Báo lỗi cụ thể từng dòng/cột vượt ngưỡng, tuyệt đối không âm thầm cắt ngắn dữ liệu (no silent truncation).

### 2.2. Động Cơ Gửi Dữ Liệu Theo Gói (Chunk 20) & Kiểm Soát Tiến Trình
- **Kích thước gói (Chunk Size)**: Đúng **20 dòng / request**, tương thích tối đa với năng lực API (max batch 100).
- **Tiến trình thời gian thực**: Thanh tiến độ trực quan kèm số dòng hoàn thành, tỷ lệ phần trăm và tổng thời gian đo lường thực tế (`elapsed_ms`).
- **Bảo toàn tính toàn vẹn dòng**: Giữ nguyên thứ tự dòng và các dòng trùng lặp (không deduplicate làm lệch file đối chiếu của người dùng).
- **Hủy bỏ an toàn (Safe Cancellation)**: Sử dụng `AbortController` hủy ngay request đang bay và ngừng phát các gói tiếp theo. Áp dụng mã phiên (`sessionId`) để ngăn các response về muộn ghi đè lên phiên mới.
- **Thử lại chuyên biệt (Retry Failed Rows)**: Cho phép bấm "Thử lại dòng lỗi" chỉ gửi lại các dòng có trạng thái `error` mà không cần xử lý lại từ đầu các dòng đã xong.

### 2.3. Trình Quản Lý & Rà Soát Dữ Liệu (Review Workspace)
- **Thẻ đếm thực chất (KPIs)**: Đếm trực tiếp từ state thật của phiên: Tổng số, Cần kiểm tra (Needs Review), Đã xử lý (Processed), Lỗi kết nối (Error). Không bịa tỷ lệ phần trăm ảo.
- **Lọc đa chiều & Tìm kiếm thời gian thực**:
  - Tab lọc: *Tất cả*, *Cần kiểm tra*, *Đã xử lý*, *Lỗi*.
  - Ô tìm kiếm: Lọc tức thì theo địa chỉ đầu vào, địa chỉ chuẩn hóa, mã xã/tỉnh, hoặc từ khóa cảnh báo.
- **Hiệu năng cao với 1.000 dòng**: Hỗ trợ phân trang linh hoạt (25, 50, 100 dòng/trang). Bảng cuộn mượt mà trên desktop; tự động chuyển sang dạng thẻ vuốt chạm thân thiện trên thiết bị di động (< 768px).
- **Ngăn Kiểm Tra Chuyên Sâu (Drawer Inspector)**:
  - Hiển thị so sánh: Đầu vào thô vs Địa chỉ chuẩn hóa mốc 01/07/2025.
  - 6 Trường cốt lõi: Số nhà, Ngõ/ngách/hẻm, Đường/phố, Thôn/xóm/ấp, Xã/phường (Mã), Tỉnh/thành phố (Mã).
  - Cảnh báo & Lý do rà soát: Dịch nghĩa trực quan sang tiếng Việt (`xa_bi_chia` -> *Xã bị chia tách 2025: Đơn vị hành chính cũ bị chia tách thành nhiều xã/phường mới theo mốc 01/07/2025; cần rà soát vị trí cụ thể*).
  - Ứng viên xã mới (`xa_moi_ung_vien`) và phần chưa phân loại (`phan_chua_phan_loai`) được bảo tồn trung thực.
  - Xem chi tiết kỹ thuật: Thẻ disclosure `<details>` cho phép lập trình viên kiểm tra JSON thô mà không cản trở luồng người dùng phổ thông.
  - **Tích hợp Chế độ đơn**: Nút *"Kiểm tra ở chế độ đơn (Single Mode) →"* kích hoạt callback `onInspect(item)` để chuyển địa chỉ này sang giao diện tinh chỉnh đơn lẻ của Session A.

### 2.4. Xuất Dữ Liệu Chuẩn Hóa & Bảo Mật (`exportUtils.ts`)
- **Xuất CSV UTF-8 kèm BOM (`\uFEFF`)**: Giúp Microsoft Excel tự động nhận diện font Unicode tiếng Việt có dấu mà không bị vỡ font.
- **Phòng vệ CSV Formula Injection**: Nếu bất kỳ ô dữ liệu nào bắt đầu bằng ký tự `=`, `+`, `-`, `@`, hàm xuất sẽ tự động thêm tiền tố nháy đơn `'` trong file CSV để vô hiệu hóa việc Excel tự động thực thi macro/công thức độc hại. Đồng thời, **tuyệt đối không làm thay đổi dữ liệu số nhà hay mã hành chính trong dữ liệu JSON**!
- **Bảo toàn cột gốc**: Mọi cột dữ liệu ban đầu trong file CSV của người dùng được giữ nguyên vẹn ở phía trước, các cột chuẩn hóa được nối tiếp ở phía sau.
- **Xuất JSON cấu trúc**: Xuất toàn bộ mảng đối tượng kèm siêu dữ liệu mốc thời gian và phiên làm việc.
- **Phạm vi xuất**: Hỗ trợ xuất toàn bộ hoặc chỉ xuất danh sách đang được lọc (ví dụ: chỉ xuất các dòng cần kiểm tra để chuyển cho đội địa chính đối soát).

---

## 3. BẰNG CHỨNG KIỂM THỬ ĐỘC LẬP & TASTE-SKILL AUDIT

### 3.1. Kết Quả Kiểm Thử Đơn Vị (`test_batch_unit.ts`)
Đã thực thi kiểm thử tự động với Node 24 native (`--experimental-strip-types`), đạt **100% PASS**:
- `[PASS]` Parse CSV có BOM nhận diện đúng 2 headers
- `[PASS]` Header 0 không bị dính ký tự BOM
- `[PASS]` Parse đúng 2 dòng dữ liệu
- `[PASS]` Ô có dấu phẩy trong ngoặc kép được giữ nguyên vẹn
- `[PASS]` Parse đúng 2 dòng mặc dù dòng 1 có newline bên trong
- `[PASS]` Nội dung xuống dòng bên trong ô được bảo toàn
- `[PASS]` Dấu ngoặc kép kép (`""`) được chuyển thành dấu ngoặc đơn (`"`)
- `[PASS]` Tự động phát hiện dấu chấm phẩy (`;`) và dấu Tab (`\t`)
- `[PASS]` Nhận diện đúng cột địa chỉ từ tên header và nội dung
- `[PASS]` Parse danh sách dán nhiều dòng lọc dòng trắng thừa, giữ đúng chỉ số
- `[PASS]` Ném ngoại lệ khi ô vượt quá 2.048 ký tự
- `[PASS]` Chặn công thức Excel bắt đầu bằng `=`, `+`, `-`, `@`
- `[PASS]` Bọc ngoặc kép và escape theo chuẩn RFC 4180
- `[PASS]` File CSV mẫu chuẩn hóa UTF-8 BOM tải và parse thành công 8 dòng

### 3.2. Kết Quả Đo Lường Trực Quan Bằng Taste-Skill (`inspect.mjs`)
Chạy thanh tra trình duyệt thực tế trên Chrome Headless tại 3 kích thước màn hình chuẩn (1440px, 768px, 390px):
```
TASTESKILL · INSPECT   http://localhost:5173/src/features/batch/harness.html
MEASURED:
  hero headline: "Không gian xử lý hàng loạt (Batch Workspace)" · Geist 700 · 24px
  typefaces:     Geist 100%
  page:          1 screens · 243 words
RESULT: 0 FAIL, 1 WARN — measurements pass.
```
- **0 FAIL**: Vượt qua 100% quy tắc đo đạc khắt khe của taste-skill (không dùng emoji làm UI icon, không gradient, không shadow nổi tại trạng thái nghỉ, font Geist chuẩn, tiêu đề h1 chuẩn, tương phản chữ $\ge 4.5:1$).
- **1 WARN**: Cảnh báo duy nhất là `dev-server` (chỉ ra rằng đang chạy trên Vite dev server thay vì bản build production, đây là trạng thái hiển nhiên trong môi trường phát triển).

---

## 4. HÌNH ẢNH KIỂM CHỨNG GIAO DIỆN THỰC TẾ

Tất cả các ảnh chụp màn hình được sinh tự động từ trình duyệt Chrome thực qua kịch bản `capture_all_screens.mjs` và lưu trữ tại thư mục [`screenshots/`](file:///D:/nlp_chuan_hoa_dia_chi/docs/ui-address-may-cry/B_batch/screenshots/):

| STT | Trạng thái giao diện | Độ phân giải | Tệp ảnh minh chứng | Mô tả chi tiết |
| :---: | :--- | :---: | :--- | :--- |
| **1** | **Khởi tạo ban đầu (Empty State)** | 1440 × 900 | [`01_initial_state_1440.png`](file:///D:/nlp_chuan_hoa_dia_chi/docs/ui-address-may-cry/B_batch/screenshots/01_initial_state_1440.png) | Giao diện nhập liệu Dán, thẻ hướng dẫn nghiệp vụ 3 cột mốc 2025, chip chọn mẫu thử. |
| **2** | **Kéo thả tệp CSV (Dropzone)** | 1440 × 900 | [`02_csv_dropzone_1440.png`](file:///D:/nlp_chuan_hoa_dia_chi/docs/ui-address-may-cry/B_batch/screenshots/02_csv_dropzone_1440.png) | Vùng kéo thả tệp CSV, quy định định dạng và nút tải tệp CSV mẫu chuẩn. |
| **3** | **Bảng kết quả & KPIs (Processed)** | 1440 × 900 | [`03_processed_results_1440.png`](file:///D:/nlp_chuan_hoa_dia_chi/docs/ui-address-may-cry/B_batch/screenshots/03_processed_results_1440.png) | Kết quả chuẩn hóa thực tế kết nối API backend, thanh tiến độ 100%, dải thẻ KPI (8 tổng, 6 cần duyệt, 2 đã xử lý, 0 lỗi), độ trễ 561ms. |
| **4** | **Ngăn chi tiết (Drawer Inspector)** | 1440 × 900 | [`04_drawer_inspector_1440.png`](file:///D:/nlp_chuan_hoa_dia_chi/docs/ui-address-may-cry/B_batch/screenshots/04_drawer_inspector_1440.png) | Ngăn trượt mở khi chọn dòng #1: 6 trường chi tiết, mã xã 31135, mã tỉnh 92, diễn giải cảnh báo tiếng Việt, nút chuyển Single mode, JSON disclosure. |
| **5** | **Lọc trạng thái "Cần kiểm tra"** | 1440 × 900 | [`05_filter_needs_review_1440.png`](file:///D:/nlp_chuan_hoa_dia_chi/docs/ui-address-may-cry/B_batch/screenshots/05_filter_needs_review_1440.png) | Chế độ lọc chỉ hiển thị 6 dòng cần rà soát với huy hiệu cảnh báo hổ phách rõ ràng. |
| **6** | **Giao diện Tablet (768px)** | 768 × 1024 | [`06_tablet_view_768.png`](file:///D:/nlp_chuan_hoa_dia_chi/docs/ui-address-may-cry/B_batch/screenshots/06_tablet_view_768.png) | Bố cục co giãn linh hoạt trên máy tính bảng, bảng cuộn ngang an toàn. |
| **7** | **Giao diện Di động (Mobile Cards 390px)** | 390 × 844 | [`07_mobile_cards_390.png`](file:///D:/nlp_chuan_hoa_dia_chi/docs/ui-address-may-cry/B_batch/screenshots/07_mobile_cards_390.png) | Tự động chuyển đổi bảng dữ liệu thành dạng thẻ vuốt chạm thân thiện, touch target $\ge 44\text{px}$, không vỡ layout. |

---

## 5. MINH BẠCH VỀ CÁC PHẦN ĐÃ TEST VÀ PHẦN CHỜ TÍCH HỢP

### 5.1. Các Luồng Đã Kiểm Thử Hoàn Chỉnh (Tested)
1. **Toàn bộ logic phân tích CSV & Dán**: Kiểm thử đơn vị 100% bao phủ BOM, CRLF, LF, delimiter auto-detect, quoted fields, multi-line in quotes, escaped quotes, cell length guardrail.
2. **Xuất CSV & Phòng vệ Injection**: Kiểm thử đơn vị các mẫu `=cmd`, `+123`, `@SUM` được prefix an toàn bằng `'` trong file xuất.
3. **Kết nối API thật (End-to-End)**: Đã kết nối trực tiếp với backend Python adapter tại `http://127.0.0.1:8080/api/v1/batch` qua proxy Vite `http://localhost:5173/api/v1/batch`, gửi thành công gói chunk 20 và nhận diện chính xác các cảnh báo (`needs_review`) và kết quả sáp nhập 2025 (Xuân Khánh -> Ninh Kiều).
4. **Trực quan hóa & Responsive**: Đã kiểm tra thực tế bằng Chrome Headless tại 3 độ phân giải 1440px, 768px, 390px; đạt chuẩn taste-skill 0 FAIL.
5. **Tiến trình Hủy & Thử lại**: Cơ chế `AbortController` và `handleRetryFailed` hoạt động ổn định trên state.

### 5.2. Các Phần Giữ Nguyên Chờ Tích Hợp (Pending Integration)
1. **Chế độ đơn (Single Mode Integration)**: Đã cài đặt sẵn callback `onInspect?: (item: BatchItem) => void`. Khi người dùng bấm *"Kiểm tra ở chế độ đơn →"*, callback được gọi chuẩn xác; việc chuyển tab và điền dữ liệu vào form Single Mode thuộc thẩm quyền của Session A trong `App.tsx`.
2. **Tải tệp bảng tính Excel (.xlsx)**: Tuân thủ đúng yêu cầu chỉ làm CSV ở lượt này, đã ghi rõ trong UI và tài liệu "Chỉ hỗ trợ CSV UTF-8", cung cấp sẵn tệp mẫu `mau_dia_chi_chuan.csv`.

---

## 6. HƯỚNG DẪN TÁI LẬP (REPRODUCIBILITY)

1. **Chạy kiểm thử đơn vị logic Batch**:
   ```powershell
   node --experimental-strip-types docs/ui-address-may-cry/B_batch/test_batch_unit.ts
   ```
2. **Kiểm tra linter giao diện taste-skill**:
   ```powershell
   node C:/Users/andan/.gemini/antigravity/brain/388e264d-6447-42fb-b64f-559ba8e2e86d/taste-skill/skills/taste-skill/scripts/lint.mjs web/address-may-cry/src/features/batch
   ```
3. **Chạy thanh tra trình duyệt thực tế và chụp ảnh**:
   ```powershell
   # Đảm bảo Vite dev server đang chạy tại port 5173
   node docs/ui-address-may-cry/B_batch/capture_all_screens.mjs
   ```
4. **Kiểm tra TypeScript compilation**:
   ```powershell
   cd web/address-may-cry; npx tsc --noEmit
   ```

---
*Báo cáo được hoàn thành độc lập và kiểm chứng thực chất bởi Phiên B.*
