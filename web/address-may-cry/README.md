# Address May Cry — Ứng Dụng Chuẩn Hóa Địa Chỉ Việt Nam (01/07/2025)

Giao diện sản phẩm chuẩn hóa địa chỉ Việt Nam theo mốc cải cách hành chính **01/07/2025** (Nghị quyết 1111/NQ-UBTVQH15).

---

## 1. Cấu Trúc Dự Án Frontend

```
web/address-may-cry/
├── index.html                 # HTML shell nạp Instrument Sans & JetBrains Mono
├── package.json               # React 18.3 + TypeScript 5.6 + Vite 5.4
├── tsconfig.json              # TypeScript strict configuration
├── vite.config.ts             # Cấu hình proxy /api -> 127.0.0.1:8080 & batchFallbackPlugin
├── public/
│   └── favicon.svg            # Huy hiệu cột mốc địa chính / biển số nhà bản sắc Việt
└── src/
    ├── main.tsx               # Điểm khởi động React
    ├── App.tsx                # Shell ứng dụng chính (Header, Tabs, Live API Health)
    ├── index.css              # Hệ thống biến CSS Design Tokens (Light/Dark mode)
    ├── components/
    │   ├── Header.tsx         # Thanh điều hướng thương hiệu, mốc thời gian & trạng thái
    │   └── Icons.tsx          # 13 bespoke SVG icons nhẹ và sắc nét
    ├── features/
    │   ├── single/
    │   │   ├── SingleWorkspace.tsx  # Không gian làm việc chuẩn hóa đơn địa chỉ (Phiên A)
    │   │   └── BatchStub.tsx        # Fallback stub dự phòng khi chưa tải module Batch
    │   └── batch/
    │       └── BatchWorkspace.tsx   # Không gian xử lý hàng loạt qua CSV (Phiên B)
    └── shared/
        ├── api.ts             # Client API gọi Backend (Normalize, Batch, Health)
        └── contracts.ts       # Hợp đồng kiểu dữ liệu TypeScript chuẩn
```

---

## 2. Hướng Dẫn Chạy Cục Bộ (Local Development)

### 2.1 Khởi Động Backend API (Phiên C)
Backend API chạy bằng Python trên cổng `8080`:
```powershell
# Chạy backend từ thư mục gốc
python web/address-may-cry/api/server.py --port 8080
```
Tệp PID được lưu tại `web/address-may-cry/api/server.pid`. Dừng server bằng:
```powershell
python web/address-may-cry/api/stop.py
```

### 2.2 Khởi Động Frontend Web (Phiên A & B)
Frontend chạy bằng Node.js / Vite trên cổng `5173`:
```powershell
cd web/address-may-cry
npm install
npm run dev
```
Truy cập ứng dụng tại: `http://127.0.0.1:5173/`

### 2.3 Đóng Gói Bản Build Sản Xuất
```powershell
cd web/address-may-cry
npm run build
npm run preview
```

---

## 3. Các Tính Năng Nổi Bật

1. **Chuẩn Hóa Đơn Địa Chỉ (Single Workspace)**:
   - Cho phép nhập văn bản tự do, hỗ trợ cả địa chỉ viết tắt, thiếu cấp, hoặc lẫn lộn mốc cũ và mới.
   - Giới hạn an toàn 2048 ký tự kèm bộ đếm số liệu tabular.
   - Thao tác nhanh: `Ctrl + Enter` gửi xử lý ngay lập tức, nút Dán và Xóa nhanh.
   - Ba mẫu thử nghiệm thực tế (Cần Thơ, Hà Nội, Thanh Hóa) kiểm chứng các trường hợp địa danh đặc thù.
   - Ma trận 6 trường hành chính bóc tách rõ ràng: *Số nhà*, *Ngõ/hẻm*, *Thôn/xóm*, *Tuyến đường*, *Phường/xã mới* (kèm mã xã), *Tỉnh/TP mới* (kèm mã tỉnh).
   - Nút sao chép 1 chạm cho toàn bộ địa chỉ chuẩn hóa hoặc từng trường và từng mã số riêng biệt.
2. **Xử Lý Trung Thực Độ Mơ Hồ (Anti-Hallucination & Ambiguity)**:
   - Khi gặp xã/phường bị chia tách theo Nghị quyết (cờ `xa_bi_chia`), hệ thống không đoán mò.
   - Đánh dấu trạng thái `needs_review`, kích hoạt cảnh báo người dùng và cung cấp danh sách ứng viên xã mới thay thế.
   - Hiển thị rõ phần chuỗi ký tự chưa phân loại (`phan_chua_phan_loai`) để người dùng kiểm tra.
3. **Bảo Mật Dữ Liệu Riêng Tư (Privacy First)**:
   - Toàn bộ lịch sử phiên (10 lượt gần nhất) được lưu tạm trong RAM của tab làm việc.
   - Tuyệt đối không ghi thông tin địa chỉ cá nhân vào `localStorage` hay cookie trình duyệt.
4. **Xử Lý Hàng Loạt (Batch Workspace)**:
   - Hỗ trợ tải lên tệp CSV địa chỉ lớn.
   - Tiến trình xử lý theo thời gian thực (Progress bar, tỷ lệ thành công, tỷ lệ cần xem lại).
   - Cho phép xuất kết quả ra CSV kèm nút kiểm tra chuyên sâu từng địa chỉ trên giao diện Đơn.
5. **Kiểm Định Định Lượng Theo Taste-Skill**:
   - Được thiết kế và kiểm thử với bộ công cụ `taste-skill` (`references/app-screens.md`).
   - Đạt **0 FAIL**, độ tương phản WCAG AA > 5.5:1, bố cục 2 cột cân bằng phẳng, responsive hoàn chỉnh trên Mobile (390px), Tablet (768px), Desktop (1440px).
