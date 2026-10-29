# BẢN TRÍCH VĂN BẢN PHÁP LÝ VÀ CĂN CỨ NGOẠI TUYẾN PHỤC VỤ KIỂM TOÁN TẬP TEST

Tài liệu này lưu trữ các bản trích văn bản pháp lý chính thức, vị trí tệp đối chiếu nội bộ và căn cứ xác minh ranh giới ĐVHC mốc **01/07/2025** (theo Quyết định số 19/2025/QĐ-TTg). Dùng để đối soát các kết luận kiểm toán ngoại tuyến trong quy trình duyệt tập test.

> [!NOTE]
> **Đính chính sai sót pháp lý từ các đợt rà soát trước:**
> 1. Nghị quyết sắp xếp đơn vị hành chính cấp xã của **TP Hà Nội** là **Nghị quyết số 1286/NQ-UBTVQH15** (ban hành ngày 14/11/2024, có hiệu lực từ ngày 01/01/2025), không phải Nghị quyết 1192.
> 2. **Nghị quyết số 1192/NQ-UBTVQH15** là văn bản sắp xếp ĐVHC cấp xã của **TP Cần Thơ** (ban hành ngày 28/09/2024, có hiệu lực từ ngày 01/11/2024).
> 3. **Nghị quyết số 1232/NQ-UBTVQH15** (TP Hải Phòng, ban hành 24/10/2024, hiệu lực 01/01/2025): Tại Điều 1 Khoản 2, quy định nhập toàn bộ diện tích tự nhiên và quy mô dân số của phường Lạc Viên và phường Máy Tơ vào Phường Gia Viên thuộc Quận Ngô Quyền.
> 4. **Xã Lạc Đạo (Huyện Văn Lâm, Hưng Yên):** Trong bảng chuyển đổi `doi_chieu_xa_cu_moi.csv`, mã xã cũ `11989` được tách/chia thành 2 xã đích là Xã Lạc Đạo (mã `11992`) và Xã Đại Đồng (mã `11995`). Do đó, 3 ca `VNTEST0046`, `VNTEST0053`, `VNTEST0055` là xã bị chia (`fan-out = 2`), bắt buộc bảo lưu trạng thái `can_duyet`, để trống `ma_xa` và `xa_phuong`, giữ cờ `xa_bi_chia` và danh sách ứng viên.

---

## 1. NGHỊ QUYẾT SỐ 1286/NQ-UBTVQH15 (THÀNH PHỐ HÀ NỘI)

- **Cơ quan ban hành:** Ủy ban Thường vụ Quốc hội khóa XV.
- **Ngày ban hành:** 14/11/2024.
- **Mốc hiệu lực:** 01/01/2025.
- **URL chính thức:** `https://xaydungchinhsach.chinhphu.vn/toan-van-nghi-quyet-so-1286-nq-ubtvqh15-sap-xep-don-vi-hanh-chinh-cap-xa-cua-thanh-pho-ha-noi-119241121144810696.htm`
- **Tệp đối chiếu nội bộ:** `data/raw/goc/conversion-table.xlsx`, `data/clean/doi_chieu_xa_cu_moi.csv`.
- **Trường hợp áp dụng:** 8 ca xã bị chia tại Hà Nội (gồm `VNTEST0008` Mộ Lao Hà Đông, `VNTEST0011` Vĩnh Tuy Hai Bà Trưng, `VNTEST0018` Mỹ Đình 2 Nam Từ Liêm...).
- **Bản trích nội dung:**
  - *Điều 1 các khoản sắp xếp ĐVHC cấp huyện, cấp xã của TP Hà Nội:* Quy định việc sáp nhập, điều chỉnh diện tích tự nhiên và quy mô dân số của các phường/xã cũ để thành lập các phường/xã mới.
  - *Về ranh giới số nhà:* Toàn văn Nghị quyết 1286 chỉ phân định ranh giới theo diện tích tự nhiên và quy mô dân số (tổ dân phố, tim đường trục chính, địa giới tự nhiên). Nghị quyết **hoàn toàn không có phụ lục phân bổ chi tiết từng số nhà** cho các tuyến đường (như đường Trần Phú - Hà Đông, phố Vĩnh Tuy, đường Mỹ Đình).
  - *Kết luận kiểm toán:* Không có căn cứ pháp lý trong văn bản để khẳng định một số nhà cụ thể (ví dụ: `108 Trần Phú`, `38 Phố Vĩnh Tuy`, `Số 22 ngõ 20 Mỹ Đình`) thuộc về phường nào trong số các phường mới.
  - *Biện pháp xử lý:* **Bảo lưu `can_duyet`**, thu hồi về rỗng `ma_xa=""` và `xa_phuong=""`, giữ cờ `xa_bi_chia` và danh sách xã mới ứng viên theo nguyên tắc Input-Grounded.

---

## 2. NGHỊ QUYẾT SỐ 1232/NQ-UBTVQH15 (THÀNH PHỐ HẢI PHÒNG)

- **Cơ quan ban hành:** Ủy ban Thường vụ Quốc hội khóa XV.
- **Ngày ban hành:** 24/10/2024.
- **Mốc hiệu lực:** 01/01/2025.
- **URL chính thức:** `https://xaydungchinhsach.chinhphu.vn/nghi-quyet-1232-nq-ubtvqh-sap-xep-don-vi-hanh-chinh-thanh-pho-hai-phong-119241103063654234.htm`
- **Tệp đối chiếu nội bộ:** `data/raw/goc/conversion-table.xlsx`, `data/clean/doi_chieu_xa_cu_moi.csv`.
- **Trường hợp áp dụng:** `VNTEST0040` (Input: `1B, Phố Thiên Lôi, Phường Gia Viên, Hải Phòng`).
- **Bản trích nội dung:**
  - *Điều 1, Khoản 2 (Sắp xếp ĐVHC cấp xã thuộc quận Ngô Quyền):* Nhập toàn bộ diện tích tự nhiên và quy mô dân số của phường Lạc Viên và phường Máy Tơ vào Phường Gia Viên.
  - *Về tuyến đường Thiên Lôi:* Tuyến đường Thiên Lôi theo dữ liệu địa giới và phân cấp quản lý đô thị TP Hải Phòng thuộc địa bàn Quận Lê Chân (chạy dọc từ Cầu Rào qua Vĩnh Niệm, Kênh Dương, An Dương), không thuộc Quận Ngô Quyền.
  - *Kết luận kiểm toán:* Tồn tại mâu thuẫn ranh giới/địa bàn trực tiếp trong chuỗi đầu vào giữa Phường Gia Viên (Quận Ngô Quyền) và Phố Thiên Lôi (thuộc Quận Lê Chân). Đồng thời, số nhà `1B` không đủ cơ sở để xác định vị trí thuộc đơn vị hành chính nào trong bối cảnh mâu thuẫn quận.
  - *Biện pháp xử lý:* **Bảo lưu trạng thái `can_duyet`**, để trống `ma_xa` và `xa_phuong`, ghi nhận xung đột địa bàn để chuyên gia xác minh thực địa.

---

## 3. NGHỊ QUYẾT SỐ 1248/NQ-UBTVQH15 (TỈNH HƯNG YÊN)

- **Cơ quan ban hành:** Ủy ban Thường vụ Quốc hội khóa XV.
- **Ngày ban hành:** 24/10/2024.
- **Mốc hiệu lực:** 01/01/2025.
- **URL chính thức:** `https://vanban.chinhphu.vn/?classid=2&docid=211625&pageid=27160`
- **Tệp đối chiếu nội bộ:** `data/clean/doi_chieu_xa_cu_moi.csv`.
- **Trường hợp áp dụng:** `VNTEST0046`, `VNTEST0053`, `VNTEST0055` (Input: `Xã Lạc Đạo, Huyện Văn Lâm, Tỉnh Hưng Yên`).
- **Bản trích nội dung & Đối chiếu danh mục:**
  - Trong bảng chuyển đổi `doi_chieu_xa_cu_moi.csv`, mã xã cũ `11989` (Xã Lạc Đạo, Huyện Văn Lâm) được chia thành 2 xã đích: `11992` (Xã Lạc Đạo) và `11995` (Xã Đại Đồng).
  - Đây là trường hợp xã bị chia (`fan-out > 1`). Do chuỗi đầu vào không có thông tin chi tiết thôn/xóm hoặc số nhà cụ thể để đối chiếu phân chia địa bàn sang `11992` hay `11995`, hệ thống không được tự ý gán đích.
  - *Kết luận kiểm toán:* **Bảo lưu trạng thái `can_duyet`**, để trống `ma_xa` và `xa_phuong`, duy trì cờ `xa_bi_chia` và lưu danh sách ứng viên `['11992', '11995']`.

---

## 4. NGHỊ QUYẾT SỐ 1192/NQ-UBTVQH15 (THÀNH PHỐ CẦN THƠ)

- **Cơ quan ban hành:** Ủy ban Thường vụ Quốc hội khóa XV.
- **Ngày ban hành:** 28/09/2024.
- **Mốc hiệu lực:** 01/11/2024.
- **URL chính thức:** `https://xaydungchinhsach.chinhphu.vn/nghi-quyet-so-1192-nq-ubtvqh15-sap-xep-don-vi-hanh-chinh-cap-xa-thanh-pho-can-tho-119241014163428945.htm`
- **Nội dung:** Sắp xếp đơn vị hành chính cấp xã của TP Cần Thơ giai đoạn 2023 - 2025 (sáp nhập các phường thuộc Quận Ninh Kiều). Lưu trữ phục vụ đối soát các mẫu thử nghiệm liên quan đến Cần Thơ.

---

## 5. NGHỊ QUYẾT SỐ 1685/NQ-UBTVQH15 (THÀNH PHỐ HỒ CHÍ MINH)

- **Cơ quan ban hành:** Ủy ban Thường vụ Quốc hội khóa XV.
- **URL chính thức:** `https://xaydungchinhsach.chinhphu.vn/toan-van-nghi-quyet-so-1685-nq-ubtvqh15-sap-xep-cac-dvhc-cap-xa-cua-thanh-pho-ho-chi-minh-nam-2025-119250616211341304.htm`
- **Kết quả tra cứu:** HTTP 200 (đã kiểm tra toàn văn trực tuyến).
- **Mốc hiệu lực:** 01/07/2025.
- **Tệp đối chiếu nội bộ:** `data/raw/goc/conversion-table.xlsx`, `data/clean/doi_chieu_xa_cu_moi.csv`.
- **Trường hợp áp dụng:** 12 ca xã bị chia tại TP.HCM (Sơn Kỳ, Cầu Ông Lãnh, Phường 7 Quận 8, Tân Tạo A...).
- **Bản trích nội dung:**
  - *Điều 1 các khoản 3, 4, 22, 24, 39, 40, 41, 62, 63:* Phân chia ranh giới theo quy mô dân số và diện tích khu phố, tim đường; hoàn toàn không có phụ lục phân bổ từng số nhà cụ thể (ví dụ: không có số 30 Bờ Bao Tân Thắng tại Điều 1 khoản 41/62/63; không có số 45 Cô Giang tại Điều 1 khoản 3/4).
  - *Kết luận kiểm toán:* Đã kiểm tra toàn văn trực tuyến; văn bản xác nhận không có phụ lục số nhà chi tiết -> **Bảo lưu `can_duyet`**, để trống `ma_xa`.

---

## 6. ĐỀ ÁN SẮP XẾP ĐVHC TỈNH BÌNH DƯƠNG VÀ CÁC ĐỊA PHƯƠNG KHÁC

- **Văn bản pháp lý:** Đề án sắp xếp ĐVHC cấp huyện, cấp xã giai đoạn 2023 - 2025 của UBND tỉnh Bình Dương và các tỉnh thành liên quan.
- **Mốc hiệu lực:** 01/07/2025.
- **Tệp đối chiếu nội bộ:** `data/clean/doi_chieu_xa_cu_moi.csv`.
- **Trường hợp áp dụng:** `VNTEST0050` (Vĩnh Phú, Thuận An, Bình Dương) và các ca xã chia tại các địa phương khác.
- **Bản trích nội dung:**
  - Đề án sắp xếp quy định phân chia ranh giới theo tổ/khu phố; không ban hành quy chế đánh số nhà chuyển tiếp tại thời điểm ban hành đề án.
  - *Kết luận kiểm toán:* Không có căn cứ phân định số nhà chi tiết cho tuyến đường này -> **Bảo lưu `can_duyet`**, để trống `ma_xa`.
