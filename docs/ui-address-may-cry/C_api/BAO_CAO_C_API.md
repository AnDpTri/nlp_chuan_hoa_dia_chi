# Báo Cáo Nghiệm Thu Kỹ Thuật: Real API Adapter & App Backend (Phiên C)

**Sản phẩm:** Address May Cry — Ứng dụng chuẩn hóa địa chỉ tiếng Việt mốc **01/07/2025**  
**Phân vùng quyền ghi:** `web/address-may-cry/api/**` và `docs/ui-address-may-cry/C_api/**`  
**Ngày hoàn thành:** 30/10/2026  
**Trạng thái máy chủ:** Sẵn sàng tại `http://127.0.0.1:8080` (PID: **6616**)

---

## 1. Ghi Nhận Cài Đặt & Nghiên Cứu `taste-skill`

Theo yêu cầu bắt buộc của dự án, bộ công cụ thiết kế anti-slop `taste-skill` đã được cài đặt và nghiên cứu trong phạm vi riêng của phiên:

- **Repository nguồn:** `https://github.com/Leonxlnx/taste-skill`
- **Commit hash cài đặt:** `12af471f627f866411b4bd785b19646d3672784c`
- **Đường dẫn cài đặt:** `C:\Users\andan\.gemini\antigravity\brain\feca2faf-c8c5-4c07-8293-c9f0c9e553e4\tools\taste-skill`
- **Tài liệu đã nghiên cứu:** Đã đọc đầy đủ `skills/taste-skill/SKILL.md` và `references/app-screens.md` (chuyên sâu cho app workspace, dashboard, form xử lý nghiệp vụ).

### Vận dụng tinh thần `taste-skill` vào thiết kế Backend & API Contract:
1. **Dữ liệu trung thực (Honest Data States):**
   - Tuyệt đối không bịa số liệu: không sinh chỉ số phần trăm độ tin cậy giả (`confidence %`), không tự điền bừa các trường thiếu (`so_nha`, `duong`) khi mô hình không tìm thấy.
   - Trường trống hiển thị rỗng `""`, không chèn chuỗi giữ chỗ giả lập.
2. **Phân định trạng thái rõ ràng (`processed` vs `needs_review`):**
   - Phân biệt minh bạch giữa việc máy đã xử lý (`processed`) và việc kết quả có độ chắc chắn ngữ nghĩa.
   - Gán cờ `needs_review` ngay khi có bất kỳ cảnh báo nào (`canh_bao`), khi xã bị chia tách dẫn đến nhiều xã mới khả dĩ (`xa_moi_ung_vien > 1`), hoặc khi còn phần văn bản chưa phân loại (`phan_chua_phan_loai`).
3. **Microcopy và mã lỗi tiếng Việt rõ nghĩa:**
   - Thông báo lỗi người dùng tự nhiên, dễ hiểu, mang tính hướng dẫn thao tác (ví dụ: `Địa chỉ đầu vào không được để trống`, `Địa chỉ vượt quá giới hạn tối đa 2048 ký tự`).
   - Mã lỗi máy ổn định (`EMPTY_ADDRESS`, `ADDRESS_TOO_LONG`, `PAYLOAD_TOO_LARGE`, `INVALID_JSON`, `NOT_FOUND`).

---

## 2. Kiến Trúc & Cấu Hình Máy Chủ Thực Tế

### 2.1. Cấu hình Runtime
- **Máy chủ:** Python Standard Library `http.server.ThreadingHTTPServer` (không cài thêm FastAPI/Uvicorn để bảo toàn tài nguyên đĩa ~8-10GB).
- **Môi trường:** `D:\nlp_chuan_hoa_dia_chi\.venv-neural\Scripts\python.exe` (Torch 2.15.0+cpu, LightGBM 4.7.0).
- **Cấu hình NLP Engine:**
  - Mô hình: CharCNN v2 (`mo_hinh/thu_nghiem/char_v2_01/char_cnn.pt`).
  - Ranker: LambdaRank v2 (`mo_hinh/thu_nghiem/char_v2_01/ranker.txt`).
  - Từ điển đường: Train v5 (`danh_gia/ket_qua/tu_dien_duong_v5.json`).
  - Danh mục hành chính: `data/clean`.
  - Tham số: `CPU 1 thread` (`torch.set_num_threads(1)`), `bao_ve_duong=True`, `tien_to_mac_dinh=True`.
- **Quản lý đồng thời (Thread-Safety):**
  - Khởi tạo 1 lần duy nhất (Singleton).
  - Khóa toàn bộ bước dự đoán bằng `threading.Lock()` để ngăn chặn triệt để xung đột trạng thái (race condition) trên PyTorch CharCNN khi nhiều request đến cùng lúc, trong khi server đa luồng vẫn phản hồi tức thì endpoint `/api/v1/health`.

---

## 3. Bằng Chứng Đối Chiếu Pipeline Thực và HTTP API

Để chứng minh **NỐI THẬT** (không mock, không fake dữ liệu), bộ kiểm thử [`test_api_contract.py`](file:///D:/nlp_chuan_hoa_dia_chi/web/address-may-cry/api/tests/test_api_contract.py) đã thực hiện gọi trực tiếp `BoChuanHoa.chuan_hoa()` và đối chiếu từng trường với kết quả trả về từ endpoint `POST /api/v1/normalize`:

```
Input: "Số 10 Lê Lợi, Phường Bến Nghé, Quận 1, TP Hồ Chí Minh"
Direct Pipeline KetQua asdict:
  - so_nha: 'Số 10'
  - duong: 'Đường Lê Lợi'
  - xa_phuong: 'Phường Sài Gòn'
  - ma_xa: '26740'
  - tinh: 'Thành phố Hồ Chí Minh'
  - ma_tinh: '79'
  - dia_chi_chuan: 'Số 10, Đường Lê Lợi, Phường Sài Gòn, Thành phố Hồ Chí Minh'
HTTP API Response (POST /api/v1/normalize):
  - result: Khớp 100% toàn bộ 14 trường của dataclass KetQua!
  - elapsed_ms: 71.20 ms (đo thực tế)
  - status: 'needs_review' (do Phường Bến Nghé có biến động sáp nhập địa giới 01/07/2025)
```

---

## 4. Kết Quả Kiểm Thử Hợp Đồng API (100% ĐẠT)

Bộ kiểm thử độc lập gồm 6 nhóm kịch bản đã chạy và vượt qua toàn bộ:

```
=================================================================
CHẠY BỘ KIỂM THỬ HỢP ĐỒNG API - ADDRESS MAY CRY
=================================================================
1. Kiểm tra GET /api/v1/health...
   [PASS] Health OK: engine='CNN v2 (char_v2_01) + Ranker v2 + Dict v5 (CPU 1 thread)', status='ok'
2. Kiểm tra POST /api/v1/normalize & đối chứng pipeline thực...
   [PASS] Chuẩn hóa thực khớp 100% pipeline: dia_chi_chuan='Số 10, Đường Lê Lợi, Phường Sài Gòn, Thành phố Hồ Chí Minh' (71.2ms)
3. Kiểm tra bảo toàn Unicode NFD và NFC...
   [PASS] NFD Unicode xử lý chính xác, không lỗi mã hóa.
4. Kiểm tra các trường hợp validation và mã lỗi...
   [PASS] Tất cả các mã lỗi (EMPTY_ADDRESS, ADDRESS_TOO_LONG, INVALID_JSON, PAYLOAD_TOO_LARGE) đều chuẩn xác.
5. Kiểm tra POST /api/v1/batch (hỗn hợp hợp lệ và lỗi item)...
   [PASS] Batch hỗn hợp thành công: 2 hợp lệ, 1 lỗi riêng biệt được cô lập, elapsed=56.63ms.
6. Kiểm tra route /api 404 JSON và CORS preflight OPTIONS...
   [PASS] 404 trả về JSON đúng chuẩn; CORS preflight OPTIONS trả về 204.
=================================================================
TẤT CẢ KIỂM THỬ HỢP ĐỒNG API ĐÃ HOÀN TẤT THÀNH CÔNG 100%!
=================================================================
```

---

## 5. Mẫu Phản Hồi API Thực Tế (Health & Batch Live)

### 5.1. Live Health Check
```json
GET http://127.0.0.1:8080/api/v1/health
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8

{
  "status": "ok",
  "engine": "CNN v2 (char_v2_01) + Ranker v2 + Dict v5 (CPU 1 thread)",
  "target_date": "2025-07-01",
  "limits": {
    "max_chars": 2048,
    "max_batch": 100
  },
  "message": "Sẵn sàng chuẩn hóa địa chỉ Việt Nam theo mốc 01/07/2025."
}
```

### 5.2. Live Batch Normalization (Cô lập lỗi từng item)
```json
POST http://127.0.0.1:8080/api/v1/batch
Request Body:
{
  "addresses": [
    {"id": "hn_01", "address": "Số 1 Tràng Tiền, Hoàn Kiếm, Hà Nội"},
    {"id": "dn_02", "address": "37/21 Đường Phạm Văn Thuận, Phường Tam Hiệp, TP Biên Hòa, Đồng Nai"},
    {"id": "err_03", "address": ""},
    {"id": "hcm_04", "address": "123 Lê Lợi, Bến Nghé, Quận 1, TP Hồ Chí Minh"}
  ]
}

Response HTTP 200 OK:
{
  "items": [
    {
      "id": "hn_01",
      "input": "Số 1 Tràng Tiền, Hoàn Kiếm, Hà Nội",
      "status": "needs_review",
      "result": {
        "so_nha": "Số 1",
        "duong": "Phố Tràng Tiền",
        "tinh": "Thành phố Hà Nội",
        "ma_tinh": "01",
        "dia_chi_chuan": "Số 1, Phố Tràng Tiền, Thành phố Hà Nội",
        ...
      },
      "elapsed_ms": 34.67
    },
    {
      "id": "dn_02",
      "input": "37/21 Đường Phạm Văn Thuận, Phường Tam Hiệp, TP Biên Hòa, Đồng Nai",
      "status": "needs_review",
      "result": {
        "so_nha": "Số 37/21",
        "duong": "Đường Phạm Văn Thuận",
        "tinh": "Tỉnh Đồng Nai",
        "ma_tinh": "75",
        "dia_chi_chuan": "Số 37/21, Đường Phạm Văn Thuận, Phường Tam Hiệp, Tỉnh Đồng Nai",
        ...
      },
      "elapsed_ms": 101.40
    },
    {
      "id": "err_03",
      "input": "",
      "status": "error",
      "error": {
        "code": "EMPTY_ADDRESS",
        "message": "Địa chỉ đầu vào không được để trống."
      }
    },
    {
      "id": "hcm_04",
      "input": "123 Lê Lợi, Bến Nghé, Quận 1, TP Hồ Chí Minh",
      "status": "needs_review",
      "result": {
        "so_nha": "Số 123",
        "duong": "Đường Lê Lợi",
        "tinh": "Thành phố Hồ Chí Minh",
        "ma_tinh": "79",
        "dia_chi_chuan": "Số 123, Đường Lê Lợi, Phường Sài Gòn, Thành phố Hồ Chí Minh",
        ...
      },
      "elapsed_ms": 110.60
    }
  ],
  "elapsed_ms": 246.87
}
```

---

## 6. Hướng Dẫn Tích Hợp Dành Cho Phiên A & Phiên B

1. **Kết nối Frontend Vite:**
   - Frontend Vite chạy tại `http://localhost:5173` đã có cấu hình proxy chuyển tiếp `/api` sang `http://127.0.0.1:8080`.
   - Máy chủ hiện đang chạy nền tại cổng 8080 (PID: `6616`), sẵn sàng phục vụ ngay lập tức.
2. **File Handoff:**
   - Phiên A và B có thể đọc tệp [`HANDOFF_API.json`](file:///D:/nlp_chuan_hoa_dia_chi/docs/ui-address-may-cry/C_api/HANDOFF_API.json) để biết địa chỉ, cổng, cấu hình limits và quy tắc trạng thái.
3. **Quản lý vòng đời máy chủ:**
   - Dừng máy chủ an toàn bằng lệnh:
     ```powershell
     & "D:\nlp_chuan_hoa_dia_chi\.venv-neural\Scripts\python.exe" web/address-may-cry/api/stop.py
     ```
   - Khởi động lại:
     ```powershell
     & "D:\nlp_chuan_hoa_dia_chi\.venv-neural\Scripts\python.exe" web/address-may-cry/api/run.py
     ```
   - Chạy kiểm thử tự động:
     ```powershell
     & "D:\nlp_chuan_hoa_dia_chi\.venv-neural\Scripts\python.exe" web/address-may-cry/api/tests/test_api_contract.py
     ```

---

## 7. Kiểm Tra Phạm Vi & Toàn Vẹn Hệ Thống

- **Phạm vi quyền ghi:** Tuyệt đối chỉ ghi trong `web/address-may-cry/api/**` và `docs/ui-address-may-cry/C_api/**`.
- **Toàn vẹn mã nguồn:** Không sửa đổi bất kỳ tệp nào trong `src/` NLP lõi, `data/clean/`, `data/train_dev/`, `mo_hinh/`, checkpoint, hoặc các thư mục của phiên A/B.
- **Không can thiệp git:** Không commit, không push, không reset/checkout.
- **Không đọc test NLP:** Không đọc hay mở `data/test/` hoặc `dia_chi_test.csv`.
