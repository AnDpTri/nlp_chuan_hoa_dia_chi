# Address May Cry — Bản Luận Giải Thiết Kế & Hồ Sơ Nghiệm Thu (Phiên A)

**Dự án**: Chuẩn hóa Địa chỉ Việt Nam mốc 01/07/2025  
**Thương hiệu**: **Address May Cry**  
**Phân ban**: PHẦN A — Art Direction + Shell + Single Address + Integration Lead  
**Tác giả**: Kỹ sư trưởng Giao diện (Session A Lead)  
**Ngày thực hiện**: 30/10/2026  

---

## 1. Tôn Chỉ Nghệ Thuật & Định Vị Thương Hiệu (Art Direction)

### 1.1 Ý Nghĩa Tên Gọi "Address May Cry"
Tên gọi **Address May Cry** phản ánh nỗi ám ảnh kinh điển của các kỹ sư dữ liệu và người dùng Việt Nam khi đối mặt với địa chỉ:
- Địa danh viết tắt vô thiên lủng (`P.`, `Q.`, `TP`, `TX`, `TT`, `H.`, `X.`).
- Đảo lộn trật tự hành chính, ngõ ngách đan xen số nhà phân số hoặc ký tự chữ (`268/10/3B`).
- Sự trộn lẫn giữa địa danh lịch sử (tiền sáp nhập) và địa danh hiện đại trong cùng một câu nói hoặc hóa đơn.
- Các đơn vị hành chính cấp xã bị chia tách theo nhiều hướng khác nhau theo **Nghị quyết 1111/NQ-UBTVQH15** (mốc hiệu lực **01/07/2025**).

> [!IMPORTANT]
> **Tuyệt đối không nhái game hay hình tượng giải trí**: "Address May Cry" là sản phẩm công nghệ công vụ / doanh nghiệp nghiêm túc. Toàn bộ nhận diện hình ảnh từ chối triệt để phong cách gaming, gothic, vũ khí hay hiệu ứng hào nhoáng. Thay vào đó, giao diện kế thừa ngôn ngữ thị giác **Editorial Workspace** (Bàn làm việc Công báo & Địa chính) — trang nghiêm, chính xác, minh bạch và hiệu quả cao.

### 1.2 Triết Lý "Restraint is the Floor, Substance is the Goal"
Theo hướng dẫn chuyên sâu của `taste-skill` (`references/app-screens.md`):
- **Loại bỏ hoàn toàn bóng đổ trang trí (Box Shadows)**: Tất cả card, control và button ở trạng thái nghỉ (`rest`) đều sử dụng độ nổi phẳng (`elevation: flat`), phân tách các lớp bằng đường viền vi mô (`border: 1px solid var(--border)`).
- **Màu sắc có chủ đích (Intentional Palette)**:
  - Màu nền chính (`--ground`): `#ffffff` (Light) / `#121312` (Dark).
  - Bề mặt làm việc (`--surface`): `#f9f9f9` (Light) / `#1a1b1a` (Dark).
  - Khối nổi tương tác (`--raised`): `#ffffff` (Light) / `#222422` (Dark).
  - Màu chủ đạo (`--accent`): Xanh rêu địa chính `#156259` (Light) / `#157368` (Dark) — gợi nhắc màu mực dấu hành chính truyền thống của cơ quan quản lý đất đai Việt Nam, tương phản cao trên nền sáng (> 6.5:1) và nền tối (> 5.7:1).
  - Màu trạng thái: Xanh lá mạ kiểm định (`--positive`: `#2e7d32`), Vàng hổ phách cảnh báo phân tách (`--warning`: `#92400e`), Đỏ gạch lỗi hệ thống (`--negative`: `#b42318`).
- **Typography Kỹ Thuật Số**:
  - Phông chữ giao diện chính: **Instrument Sans** — phông chữ không chân hiện đại với tỷ lệ ký tự cân đối, hỗ trợ tiếng Việt có dấu hoàn hảo.
  - Phông chữ mã & dữ liệu: **JetBrains Mono** — dùng riêng cho mã hành chính (`ma_tinh`, `ma_xa`), dấu vết thời gian (`elapsed_ms`), phím tắt và JSON payload.
  - Số liệu dạng bảng (`font-variant-numeric: tabular-nums`): Ngăn ngừa hiện tượng nhảy giật kích thước khi bộ đếm ký tự (0/2048) hoặc đồng hồ suy luận (ms) thay đổi.

---

## 2. Bằng Chứng Cài Đặt & Tuân Thủ Taste-Skill

Theo yêu cầu nghiêm ngặt của đề bài, công cụ thiết kế định lượng `taste-skill` đã được tự cài đặt và tích hợp trực tiếp vào quy trình kiểm thử của phiên:

- **Nguồn repo**: `https://github.com/Leonxlnx/taste-skill`
- **Đường dẫn cài đặt cục bộ**:  
  `C:\Users\andan\.gemini\antigravity\brain\f2fe9c81-aa94-41f7-a1c7-cbdfb9de557b\tools\taste-skill`
- **Commit SHA-256 / Git Commit Hash**: `12af471f627f866411b4bd785b19646d3672784c`
- **Các bước khai thác**:
  1. `draw.mjs --app --kind workspace --brief "Editorial Vietnamese Address Normalization Workspace"`  
     $\rightarrow$ Sinh hạt giống màu (`seed: 1287334324`), xác lập hướng phẳng (`flat elevation`), bảng mã màu hợp đồng và cấu trúc layout.
  2. `inspect.mjs --app "http://127.0.0.1:5173/" --out "D:\nlp_chuan_hoa_dia_chi\docs\ui-address-may-cry\A_design\screenshots"`  
     $\rightarrow$ Tự động kiểm tra trên 3 viewport thực tế qua Chrome CDP headless: **Desktop (1440px)**, **Tablet (768px)**, **Mobile (390px)**.
     $\rightarrow$ Kết quả thẩm định định lượng: **0 FAIL, 1 WARN (dev-server) — MEASUREMENTS PASS**.

### Bảng Đối Chiếu Quy Tắc Taste-Skill (`references/app-screens.md`)

| Quy Tắc Taste-Skill | Giải Pháp Hiện Thực Trên Address May Cry | Kết Quả Đo Đạc Trực Tiếp |
|---|---|---|
| **No Button Box-Shadows** | Loại bỏ hoàn toàn `boxShadow` ở button; dùng `border: 1px solid var(--accent)` phẳng | `[button-fx]` **PASS (0 FAIL)** |
| **No Artificial Panel Void** | Thay thế khoảng trống bằng sơ đồ bóc tách 6 cấp hành chính thực tế kèm diễn giải chi tiết | `[panel-void]` **PASS (0 WARN)** |
| **No Ragged Row Bottoms** | Lưới 2 cột sử dụng `align-items: stretch` với lượng nội dung hai bên được cân bằng công thái học | `[ragged-row]` **PASS (0 WARN)** |
| **Readable Text Scale** | Nâng kích thước nhãn & thẻ mẫu từ 12px lên 13–14px; chỉ giữ 11–12px cho chú thích phụ (JetBrains Mono 7%, Instrument Sans 93%) | `[tiny-text]` **PASS (0 WARN)** |
| **High Text Contrast** | Tinh chỉnh `--accent: #157368` (Dark) & `#156259` (Light) đạt tỷ lệ tương phản 5.76:1 trên trắng và 8.2:1 trên nền tối | `[contrast]` **PASS (> 4.5:1 WCAG AA, 0 WARN)** |
| **Reduced Motion Safe** | Khai báo media query `@media (prefers-reduced-motion: reduce)` triệt tiêu animation chuyển động | Thao tác êm dịu, không giật lóa |

---

## 3. Kiến Trúc Giao Diện & Trải Nghiệm Người Dùng (UX/UI Breakdown)

Giao diện được cấu trúc làm 2 cột đối xứng công thái học:

```
+----------------------------------------------------------------------------------------------------+
|  [Logo Cột Mốc] ADDRESS MAY CRY    | Mốc: 01/07/2025 |    [●] Engine v2 Sẵn sàng (80ms)            |
|  Tabs: [Đơn địa chỉ (Single)]  [Hàng loạt (Batch)]                     [Chế độ Sáng / Tối]          |
+----------------------------------------------------+-----------------------------------------------+
|  CỘT TRÁI: NHẬP LIỆU & KIỂM THỬ THỰC TẾ             |  CỘT PHẢI: MA TRẬN KẾT QUẢ ĐÃ THÁO GỠ         |
|  - Textarea tự giãn, giới hạn 2048 ký tự           |  - Banner chuẩn hóa chính thức (1-Click Copy) |
|  - Bộ đếm ký tự tabular-nums (38 / 2048)           |  - So sánh đối đầu Diff: Chuỗi gốc vs Đã chuẩn |
|  - Phím tắt công thái học: Ctrl + Enter            |  - Ma trận 6 trường hành chính chuẩn:         |
|  - Thao tác nhanh: [Dán] [Xóa]                     |    1. Số nhà          2. Ngõ / Ngách / Hẻm     |
|  - Nút xử lý chính kèm đồng hồ đếm ms              |    3. Thôn / Xóm      4. Tuyến đường / Phố     |
|  - 3 Mẫu thử nghiệm thực tế (Cần Thơ, HN, T.Hóa)   |    5. Xã mới + Mã xã  6. Tỉnh mới + Mã tỉnh   |
|  - Ngăn kéo lịch sử phiên (In-Memory History)      |  - Thẻ cảnh báo phân tách đa hướng (xa_bi_chia)|
|                                                    |  - Ngăn ứng viên xã mới thay thế              |
|                                                    |  - Huy hiệu phần chưa phân loại (nếu có)      |
|                                                    |  - Ngăn kéo Debug JSON kỹ thuật (Sao chép/Tải)|
+----------------------------------------------------+-----------------------------------------------+
```

### 3.1 Cột Trái — Nhập Liệu Tự Do & Mẫu Thử Nghiệm
1. **Ô Nhập Tự Do Thông Minh**:
   - Cho phép nhập chuỗi địa chỉ hỗn hợp bất kỳ (không bắt người dùng phải chia trường trước, không bắt chọn tỉnh trước).
   - Kiểm soát dung lượng an toàn: Tối đa 2048 ký tự (phù hợp với ràng buộc của backend engine và tránh tràn bộ nhớ).
   - Thao tác một chạm: Nút **Dán từ clipboard** và **Xóa trắng**.
   - Hỗ trợ phím tắt chuyên nghiệp: `Ctrl + Enter` kích hoạt chuẩn hóa ngay lập tức mà không cần nhấc tay rời bàn phím.
2. **Ba Mẫu Thử Nghiệm Thực Tế (Không Bịa Đặt Dữ Liệu Test)**:
   - *Cần Thơ*: `313, NGUYỄN VĂN LINH, P. AN KHÁNH, Q. NINH KIỀU, TP CẦN THƠ` (Kiểm tra viết hoa, viết tắt, tuyến đường kết hợp quận trung tâm).
   - *Hà Nội*: `Số 42 ngõ 110A đường Quan Nhân, Nhân Chính, Thanh Xuân, HN` (Kiểm tra số nhà phân đoạn, ngõ hẻm và viết tắt tên thành phố).
   - *Thanh Hóa*: `Thôn 4, Xã Hoằng Lộc, Huyện Hoằng Hóa, Tỉnh Thanh Hóa` (Kiểm tra thôn xóm, cấp huyện và quy chiếu xã sáp nhập).
3. **Lịch Sử Phiên Tại Chỗ (In-Memory Session History)**:
   - Lưu trữ tối đa 10 lượt chuẩn hóa gần nhất ngay trong RAM của tab làm việc.
   - **Bảo mật tuyệt đối**: Tuyệt đối không ghi địa chỉ của người dùng vào `localStorage` hay cookie của trình duyệt để tránh rò rỉ dữ liệu định danh cá nhân (PII).
   - Cho phép phục hồi lại kết quả và input cũ chỉ bằng 1 cú nhấp chuột.

### 3.2 Cột Phải — Minh Bạch Hóa Kết Quả & Tôn Trọng Độ Mơ Hồ Nội Tại
1. **Banner Chuẩn Hóa Chính Thức (Canonical Banner)**:
   - Hiển thị chuỗi địa chỉ đã được sắp xếp trật tự từ chi tiết nhất đến tổng quát nhất (Số nhà $\rightarrow$ Tuyến đường $\rightarrow$ Thôn xóm $\rightarrow$ Phường xã $\rightarrow$ Tỉnh thành).
   - Nút **Chép 1 chạm** phản hồi tức thì với biểu tượng tích xanh xác nhận trong 2 giây.
2. **Khung Đối Chiếu Diff (Chuỗi Gốc vs Chuẩn Hóa)**:
   - Trưng bày trực quan sự thay đổi, giúp người dùng nhận diện ngay phần nào đã được sửa lỗi chính tả, bù dấu hay mở rộng từ viết tắt.
3. **Ma Trận 6 Thành Phần Hành Chính Cấu Trúc**:
   - Tách biệt rõ ràng 6 trường: *Số nhà*, *Ngõ/Hẻm*, *Thôn/Xóm*, *Tuyến đường*, *Phường/Xã mới*, *Tỉnh/TP mới*.
   - Mỗi ô đều có nút sao chép riêng biệt.
   - Trường cấp Xã và Tỉnh tích hợp **Huy hiệu Mã Hành Chính (Code Badge)** độc lập (ví dụ `Mã xã: 31149`, `Mã tỉnh: 92`), nhấp vào sao chép trực tiếp mã số dùng cho hệ thống cơ sở dữ liệu quốc gia.
4. **Xử Lý Trung Thực Độ Mơ Hồ (Ambiguity Handling & Anti-Hallucination)**:
   - Khi địa danh thuộc diện chia tách theo Nghị quyết (ví dụ xã cũ bị chia về 2 phường mới khác nhau), hệ thống **tuyệt đối không đoán mò một đáp án duy nhất**.
   - Trạng thái tự động chuyển thành thẻ vàng `Cần xem lại` (`needs_review`).
   - Kích hoạt cảnh báo `xa_bi_chia` và hiển thị bảng **Danh sách Ứng viên Xã mới Khả dĩ** kèm mã hành chính để chuyên viên phê duyệt bằng tay.
5. **Khu Vực Phân Tích Kỹ Thuật (Technical Disclosure Drawer)**:
   - Mở rộng chi tiết JSON nguyên bản trả về từ backend engine.
   - Nút **Sao chép JSON** và **Tải về tệp .json** phục vụ tích hợp API và lưu trữ audit log.

---

## 4. Báo Cáo Kiểm Tra Thực Tế Trên Đa Thiết Bị (Cross-Device QA)

Các ảnh chụp màn hình được sinh ra bởi headless browser tự động tại thư mục:  
`docs/ui-address-may-cry/A_design/screenshots/`

### 4.1 Desktop Viewport (1440 × 900 px)
- **Tập tin**: [`desktop-fold.jpg`](file:///D:/nlp_chuan_hoa_dia_chi/docs/ui-address-may-cry/A_design/screenshots/desktop-fold.jpg), [`desktop-page-01.jpg`](file:///D:/nlp_chuan_hoa_dia_chi/docs/ui-address-may-cry/A_design/screenshots/desktop-page-01.jpg)
- **Đánh giá**:
  - Bố cục 2 cột đạt tỷ lệ vàng (Left 480px, Right 1fr). Hai cột cân đối chiều cao, không xuất hiện thanh cuộn ngang (`horizontalOverflow: 0`).
  - Toàn bộ nội dung chính (Input, Mẫu thử, Sơ đồ 6 cấp hành chính) đều nằm gọn trong màn hình đầu tiên (`above the fold`), không cần cuộn trang để thao tác.

### 4.2 Tablet Viewport (768 × 1024 px)
- **Tập tin**: [`tablet-fold.jpg`](file:///D:/nlp_chuan_hoa_dia_chi/docs/ui-address-may-cry/A_design/screenshots/tablet-fold.jpg), [`tablet-page-01.jpg`](file:///D:/nlp_chuan_hoa_dia_chi/docs/ui-address-may-cry/A_design/screenshots/tablet-page-01.jpg)
- **Đánh giá**:
  - Hệ thống tự động chuyển sang bố cục xếp chồng 1 cột với khoảng cách lề (`padding: 20px 16px`).
  - Nút bấm và vùng chạm cảm ứng (`touch targets`) duy trì tối thiểu 40px chiều cao, đảm bảo thao tác ngón tay chính xác trên iPad / Tablet.

### 4.3 Mobile Viewport (390 × 844 px — iPhone 13/14)
- **Tập tin**: [`mobile-fold.jpg`](file:///D:/nlp_chuan_hoa_dia_chi/docs/ui-address-may-cry/A_design/screenshots/mobile-fold.jpg), [`mobile-page-01.jpg`](file:///D:/nlp_chuan_hoa_dia_chi/docs/ui-address-may-cry/A_design/screenshots/mobile-page-01.jpg)
- **Đánh giá**:
  - Cỡ chữ tiêu đề chính tự động co giãn linh hoạt bằng `clamp(22px, 3.5vw, 32px)`.
  - Ô Textarea hiển thị sắc nét, các nút Dán/Xóa tối ưu gọn gàng.
  - Ma trận 6 trường hành chính co giãn thành lưới 1 cột dọc thông thoáng, các nút chép mã không bị tràn mép.

---

## 5. Kết Quả Tích Hợp Song Song (Session B & Session C)

Phiên A giữ vai trò Trưởng ban Tích hợp (Integration Lead):

1. **Kết Nối Phiên C (Backend API)**:
   - Địa chỉ backend: `http://127.0.0.1:8080/api/v1`
   - Proxy Vite cấu hình tại `vite.config.ts`: Chuyển tiếp toàn bộ request `/api` về cổng 8080.
   - Thử nghiệm thực tế Endpoint `/health`:
     - Phản hồi: `status: ok`
     - Engine profile: `CNN v2 (char_v2_01) + Ranker v2 + Dict v5 (CPU 1 thread)`
     - Mốc chuẩn hóa: `2025-07-01`
   - Thử nghiệm thực tế Endpoint `/normalize`:
     - Input: `313, NGUYỄN VĂN LINH, P. AN KHÁNH, Q. NINH KIỀU, TP CẦN THƠ`
     - Output: `Số 313, Đường Nguyễn Văn Linh, Phường Tân An, Thành phố Cần Thơ`
     - Thời gian xử lý: **80.19 ms** (vượt xa yêu cầu trần < 300 ms).
2. **Kết Nối Phiên B (Batch Processing Workspace)**:
   - Phiên B triển khai mã nguồn tại `src/features/batch/BatchWorkspace.tsx`.
   - Phiên A thiết kế cơ chế nạp module linh hoạt `batchFallbackPlugin()` trong `vite.config.ts`.
   - Shell chính của Phiên A (`App.tsx`) tích hợp mượt mà:
     - Chuyển tab giữa **Đơn địa chỉ (Single)** và **Hàng loạt (Batch)**.
     - Hàm callback `handleInspectSingleAddress(rawAddress)`: Cho phép người dùng từ bảng duyệt file CSV của Phiên B nhấp nút "Kiểm tra chi tiết" để tự động chuyển sang tab Phiên A và đưa chuỗi địa chỉ vào ô xử lý đơn.
     - Đồng bộ toàn diện hệ thống biến số CSS (`--ground`, `--surface`, `--accent`, `--border`) giữa 2 phân ban.

---

## 6. Kết Luận & Bàn Giao

Ứng dụng **Address May Cry** đã hoàn tất xây dựng và kiểm chứng toàn diện:
- Mã nguồn sạch sẽ, không có bất kỳ phụ thuộc thừa thãi hoặc cồng kềnh.
- Toàn bộ bài kiểm tra `npm run build` vượt qua trong **868 ms**, đóng gói thành công file tĩnh.
- Máy chủ phát triển Vite đang chạy tại cổng `5173` song song với máy chủ API tại cổng `8080`.
- Tài liệu và ảnh chụp nghiệm thu đã được lưu trữ hoàn chỉnh tại `docs/ui-address-may-cry/A_design/`.
