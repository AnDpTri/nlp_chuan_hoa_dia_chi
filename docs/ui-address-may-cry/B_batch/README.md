# BATCH WORKSPACE, IMPORT/EXPORT, REVIEW FLOW
## ADDRESS MAY CRY — PHÂN HỆ XỬ LÝ HÀNG LOẠT (PHIÊN B)

---

### 1. Giới thiệu & Phạm vi bàn giao
Phân hệ **Batch Workspace** (`web/address-may-cry/src/features/batch`) chịu trách nhiệm toàn bộ luồng xử lý địa chỉ hàng loạt, nhập xuất tệp CSV/JSON, bộ lọc trạng thái kiểm duyệt (`needs_review`, `processed`, `error`), và thanh tra chi tiết (`drawer inspector`) cho ứng dụng **Address May Cry**.

Toàn bộ mã nguồn và tài liệu tuân thủ tuyệt đối thẩm quyền ghi độc quyền của Phiên B:
- `web/address-may-cry/src/features/batch/**`
- `docs/ui-address-may-cry/B_batch/**`

---

### 2. Thông tin Skill & Định hướng thiết kế
- **Taste Skill Repo:** [https://github.com/Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill)
- **Commit Hash:** `12af471f627f866411b4bd785b19646d3672784c`
- **Vị trí cài đặt độc lập:** `C:\Users\andan\.gemini\antigravity\brain\388e264d-6447-42fb-b64f-559ba8e2e86d\taste-skill`
- **Chế độ taste-skill:** `--app --kind workspace`
- **Phong cách thị giác chủ đạo:** **Achromatic Ledger / High Substance Workspace**.
  - Không trang trí rườm rà (zero marketing gradients, zero decorative badges).
  - Bảng dữ liệu sắc nét, căn chỉnh `tabular-nums` cho số liệu định lượng, độ tương phản $\ge 4.5:1$.
  - Màu sắc chỉ dùng trên dữ liệu (`processed` xanh muted, `needs_review` hổ phách, `error` đỏ gạch).
  - Hỗ trợ đầy đủ tương tác bàn phím (`:focus-visible`), cảm ứng di động (touch target $\ge 44\text{px}$), và `prefers-reduced-motion`.

---

### 3. Cấu trúc tệp bàn giao

```text
web/address-may-cry/src/features/batch/
├── BatchWorkspace.tsx       # Component chính (Default export, nhận { onInspect?: (item) => void })
├── batch.module.css         # CSS Module scoped hoàn toàn, tiêu thụ CSS variables từ CONTRACT.md
├── batch.module.css.d.ts    # Khai báo TypeScript cho CSS Module
├── csvParser.ts             # RFC 4180 CSV parser native TS (BOM, quotes, newline, auto-delimiter)
├── exportUtils.ts           # Xuất CSV UTF-8 BOM, JSON, phòng vệ CSV Formula Injection
├── sampleData.ts            # Dữ liệu 8 ca địa chỉ thực tế (mốc 01/07/2025, sáp nhập, OOV, v.v.)
├── harness.html             # Trang HTML harness độc lập kiểm thử batch trên Vite
└── harnessMount.tsx         # Điểm mount React cho harness HTML

docs/ui-address-may-cry/B_batch/
├── README.md                # Tệp này
├── BAO_CAO.md               # Báo cáo kỹ thuật chi tiết kèm bảng ảnh kiểm chứng
├── test_batch_unit.ts       # Bộ kiểm thử đơn vị độc lập 14 ca cho parser, export, injection
├── capture_all_screens.mjs  # Kịch bản tự động hóa CDP chụp màn hình thực tế (1440, 768, 390px)
└── screenshots/             # Thư mục chứa 7 ảnh chụp thực tế từ browser
    ├── 01_initial_state_1440.png
    ├── 02_csv_dropzone_1440.png
    ├── 03_processed_results_1440.png
    ├── 04_drawer_inspector_1440.png
    ├── 05_filter_needs_review_1440.png
    ├── 06_tablet_view_768.png
    └── 07_mobile_cards_390.png
```

---

### 4. Các tính năng kỹ thuật chính
1. **Parser CSV Native (Zero dependencies ngoài):**
   - Hỗ trợ UTF-8 BOM (`\uFEFF`), ngắt dòng CRLF/LF.
   - Tự động phát hiện ký tự phân tách: Dấu phẩy `,`, chấm phẩy `;`, hoặc Tab `\t`.
   - Hỗ trợ ô chứa dấu phân tách và xuống dòng trong ngoặc kép: `"đoạn 1\nđoạn 2"`.
   - Giới hạn nghiêm ngặt: Dung lượng $\le 5\text{MB}$, tối đa $1.000$ dòng, tối đa $2.048$ ký tự/địa chỉ (báo lỗi rõ ràng, không cắt gọt âm thầm).
2. **Phòng vệ CSV Formula Injection:**
   - Các trường văn bản bắt đầu bằng `=`, `+`, `-`, `@` được tự động tiền tố `'` khi xuất CSV để ngăn mã độc thực thi macro trên Microsoft Excel hoặc Google Sheets.
   - Không làm thay đổi chuỗi nguyên bản trong dữ liệu JSON.
3. **Quản lý xử lý hàng loạt theo Chunk:**
   - Phân đoạn `chunk_size = 20` theo khuyến nghị của `CONTRACT.md` (tối đa 100 API).
   - `AbortController` cho phép hủy an toàn giữa chừng; các dòng đã xong được giữ nguyên vẹn.
   - Cơ chế Retry độc lập từng dòng bị lỗi mà không phải chạy lại toàn bộ danh sách.
4. **Thanh tra chi tiết (Drawer Inspector):**
   - Hiển thị đầy đủ 6 trường chuẩn hóa mốc **01/07/2025**: `original_input`, `house_number_street`, `ward_commune`, `district`, `province_city`, `country`.
   - Mã hành chính phân cấp: `ward_code`, `district_code`, `province_code`.
   - Danh sách xã/phường ứng viên thực tế (`candidate_wards`) và văn bản chưa phân loại (`unclassified`).
   - Diễn giải cảnh báo tiếng Việt rõ ràng, kèm debug JSON disclosure có thể sao chép 1-click.

---

### 5. Hướng dẫn chạy & Tái lập kiểm chứng

#### A. Chạy Unit Test (100% PASS)
Chạy bằng Node.js tích hợp sẵn hỗ trợ TypeScript:
```bash
node --experimental-strip-types docs/ui-address-may-cry/B_batch/test_batch_unit.ts
```

#### B. Kiểm tra Lint với taste-skill
```bash
node C:/Users/andan/.gemini/antigravity/brain/388e264d-6447-42fb-b64f-559ba8e2e86d/taste-skill/skills/taste-skill/scripts/lint.mjs web/address-may-cry/src/features/batch
```
*(Kết quả: 0 FAIL)*

#### C. Chạy Harness & Chụp ảnh kiểm chứng trình duyệt
Đảm bảo Backend adapter đang chạy tại cổng `8080` và Vite đang chạy tại cổng `5173`:
```bash
node docs/ui-address-may-cry/B_batch/capture_all_screens.mjs
```
Kịch bản tự động tải dữ liệu mẫu, gọi API backend thật, kiểm tra phản hồi sáp nhập hành chính (ví dụ: Phường Xuân Khánh, Ninh Kiều, Cần Thơ), và xuất 7 ảnh độ phân giải cao vào thư mục `docs/ui-address-may-cry/B_batch/screenshots/`.
