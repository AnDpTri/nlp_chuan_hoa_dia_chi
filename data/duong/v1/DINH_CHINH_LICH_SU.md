# ĐÍNH CHÍNH LỊCH SỬ VÀ GIẢI TRÌNH THAY ĐỔI TRẠNG THÁI DANH MỤC ĐƯỜNG
## (HISTORICAL CORRECTION & STATUS DOWNGRADE REPORT)

- **Thời điểm lập:** 29/10/2026
- **Căn cứ:** Báo cáo kiểm tra độc lập tại `danh_gia/ket_qua/audit_agy_duong_train_v2_01/BAO_CAO.md` và `KIEM_TRA_DOC_LAP.json`
- **Phiên bản áp dụng:** Danh mục đường phố V1.1 (Post-Audit)

---

## 1. NGUYÊN NHÂN VÀ CÁC LỖI ĐÃ ĐƯỢC XÁC NHẬN TỪ BẢN V1 CŨ

Báo cáo audit độc lập ngày 29/10/2026 đã chỉ ra các vấn đề nghiêm trọng trong gói `data/duong/v1/` ban đầu:

1. **Vòng tròn tự chứng minh (Self-referential Source Generation):**
   - Script `generate_sources.py` import các bảng hằng định nghĩa từ `definitions/*.py`, tự nối chuỗi rồi ghi ra các tệp `.txt` trong thư mục `sources/`, sau đó băm SHA-256 chính các tệp đó.
   - Việc `validate_duong.py` kiểm tra tên đường xuất hiện trong các tệp `.txt` tự tạo chỉ là kiểm tra khớp với chính danh sách đã viết, không phải đối soát với văn bản nguồn độc lập được tải từ bên thứ ba.
   - Do đó, việc tự gắn nhãn `confirmed`, `pháp lý`, `xác minh thực địa` trên 1.461 bản ghi cũ là **chưa đủ căn cứ khoa học**.

2. **Nguồn dẫn thiếu định vị cụ thể (Portal Root URLs):**
   - 8/10 URL nguồn trong `sources_manifest.json` cũ là URL trang chủ (portal root: `https://congbao.hanoi.gov.vn`, `https://danang.gov.vn`, `https://haiphong.gov.vn`, `https://cantho.gov.vn`, `https://thuathienhue.gov.vn`, `https://vanban.chinhphu.vn`, `https://www.openstreetmap.org`).
   - Không có trường `fetched_at_utc`, không có `http_status`, không lưu tệp phản hồi HTTP nguyên bản (raw response).

3. **Sai đối tượng văn bản tại URL docid 204000:**
   - URL `https://vanban.chinhphu.vn/?docid=204000&pageid=27160` được bản cũ ghi là Quyết định số 1454/QĐ-TTg ngày 01/09/2021 về quy hoạch mạng lưới đường bộ.
   - Thực tế trang chính thức tại URL này là **Quyết định số 89/QĐ-TCTĐB ngày 09/09/2021** ban hành Quy chế hoạt động của Tổ công tác đặc biệt của Thủ tướng Chính phủ về rà soát, tháo gỡ khó khăn, vướng mắc và thúc đẩy thực hiện dự án đầu tư. Đây là sai đối tượng văn bản, không phải lỗi định dạng hay lỗi mã băm.

---

## 2. CÁC BIỆN PHÁP XỬ LÝ KỸ THUẬT VÀ BẢO TỒN DỮ LIỆU

### 2.1. Bảo toàn lịch sử nguyên trạng (Archival Snapshot)
- Toàn bộ dữ liệu của phiên bản V1 cũ đã được sao chép và đóng băng nguyên trạng tại:
  `data/duong/v1/legacy_v1_snapshot/`
- Tệp `data/duong/v1/legacy_v1_snapshot/LEGACY_MANIFEST.json` lưu giữ mã băm SHA-256 của từng tệp thuộc gói cũ để đảm bảo tính truy vết tuyệt đối.

### 2.2. Hạ trạng thái (Downgrade) toàn bộ 1.461 bản ghi chưa có bằng chứng độc lập
- Toàn bộ 1.461 bản ghi cũ trong `danh_muc_duong.jsonl` ban đầu được **hạ trạng thái từ `confirmed` xuống `candidate_unverified_source`**.
- Các bản ghi này được chuyển toàn bộ sang tệp:
  `data/duong/v1/danh_muc_candidates_pending.jsonl` và `data/duong/v1/danh_muc_candidates_pending.csv`
- Mỗi bản ghi hạ trạng thái đều được gán thêm:
  + `legacy_id`: Giữ nguyên ID cũ (`STR_00001` đến `STR_01461`)
  + `id`: Gán tiền tố `CAND_STR_...`
  + `status`: `candidate_unverified_source`
  + `downgrade_reason`: `CHUA_THU_THAP_DUOC_RAW_EVIDENCE_DOC_LAP (Bản ghi từ definitions cũ chưa có tệp phản hồi HTTP nguyên bản độc lập)`
  + `verification_status`: `pending_evidence_fetch`
  + `source_id`: `LEGACY_V1_UNVERIFIED`

### 2.3. Thu thập nguồn thô độc lập và lưu trữ Raw HTTP Responses
- Đã tạo thư mục chuyên biệt: `data/duong/v1/raw_sources/`
- Tải trực tiếp và lưu trữ nguyên bản (raw HTML bytes) kèm mã băm SHA-256 thực tế, `http_status = 200` và thời điểm tải `fetched_at_utc` trong `raw_sources_manifest.json`:
  1. `SRC_RAW_01_HANOI_QD3862`: Quyết định 3862/QĐ-UBND ngày 20/07/2025 từ Cổng Giao tiếp điện tử / Dịch vụ công Hà Nội (`ttpvhcc.hanoi.gov.vn`).
  2. `SRC_RAW_02_TPHCM_HDND_QUOCLO`: Nghị quyết HĐND TP.HCM khóa X và QĐ công bố đặt tên Quốc lộ 1, 1K, 22, 50 từ Cổng TTĐT Thành ủy TP.HCM (`hcmcpv.org.vn`).
  3. `SRC_RAW_03_QUOC_LO_QD1454`: QĐ 1454/QĐ-TTg từ Báo Điện tử Chính phủ (`baochinhphu.vn`).
  4. `SRC_RAW_04_DANANG_1022`: Nghị quyết kỳ họp thứ 5 HĐND TP Đà Nẵng từ Cổng Dịch vụ công 1022 Đà Nẵng (`1022.vn`).
  5. `SRC_RAW_05_DANANG_BAO`: Bài viết trích xuất Quy chế QĐ 47/2019/QĐ-UBND từ Báo Đà Nẵng (`baodanang.vn`).
  6. `SRC_COUNTER_DOCID204000`: Tệp raw HTML phản chứng đối soát QĐ 89/QĐ-TCTĐB từ `vanban.chinhphu.vn/?docid=204000`.

---

## 3. THỐNG KÊ DANH MỤC ĐƯỜNG SAU ĐÍNH CHÍNH (V1.1)

| Phân nhóm | Số lượng bản ghi | Tỷ lệ | Nguồn chứng thực | Trạng thái kỹ thuật |
|---|:---:|:---:|---|---|
| **Confirmed** | **53** | 3,4% | 5 tệp raw response (Hà Nội QĐ 3862, TP.HCM HĐND, QĐ 1454 Báo Chính Phủ, Đà Nẵng) | Đã kiểm chứng 100% Textual Grounding & Exact Snippet |
| **Candidate (Hạ từ V1)** | **1.461** | 95,1% | Nguồn definitions cũ | `candidate_unverified_source` (Chờ thu thập raw evidence) |
| **Pending / Rejected (Cũ)** | **23** | 1,5% | Tổ thẩm định kỹ thuật | 8 pending, 15 rejected (ngõ ngách, tòa nhà, bãi bỏ) |
| **TỔNG CỘNG** | **1.537** | 100% | Toàn bộ các nhóm | Quản lý minh bạch, không phỏng đoán mơ hồ |

### 3.1. Phân bố 53 bản ghi CONFIRMED mới
- **38 tuyến đường phố Hà Nội:** Phố Nguyễn Hữu Liêu, Phố Doãn Khuê, Phố Học Phi, Phố Hàng Lọng, Phố Hồ Linh Quang, Phố Phạm Khắc Hòe, Phố Phan Hiền, Đường Viên Chiếu, Phố Dương Bá Trạc, Phố Lê Đại, Phố Nguyễn Huy Thảo, Phố Nguyễn Thế Rục, Phố Phan Tây Nhạc, Phố Bạch Thành Phong, Phố Lê Giản, Phố Tưởng Dân Bảo, Đường Xuân Mai, Đường Dương Viết Điển, Đường Ba Đảm Đang, Đường Lê Xá, Đường Ngọc Động, Đường Xuân Thụy, Đường Chử Đồng Tử, Đường Tiên Dung, Đường Lê Trần Cẩn, Đường Kim Hoa, Đường An Phú, Đường Hùng Tiến, Đường Mỹ Xuyên, Đường Phúc Lâm, Đường Phùng Xá, Đường Tam Đức, Đường Phương Nhị, Đường Tam Hiệp, Đường Yên Ngưu, Phố Vũ Đức Úy, Đường Doãn Tuế, Đường Lê Công Hành.
- **7 tuyến đường TP. Hồ Chí Minh:** Đường Đỗ Mười (Quốc lộ 1), Đường Lê Đức Anh (Quốc lộ 1), Đường Lê Khả Phiêu (Quốc lộ 1), Đường Lê Quang Đạo (Quốc lộ 22), Đường Phan Văn Khải (Quốc lộ 22), Đường Văn Tiến Dũng (Quốc lộ 50), Đường Hoàng Cầm (Quốc lộ 1K).
- **4 tuyến đường trục quốc gia:** Cao tốc Bắc - Nam phía Đông, Cao tốc Bắc - Nam phía Tây, Đường bộ ven biển, Quốc lộ 45.
- **4 tuyến đường TP. Đà Nẵng:** Đường Bình Kỳ, Đường Lưu Quang Vũ, Đường Trần Hưng Đạo, Đường Hùng Vương.

Mỗi bản ghi confirmed đều được lưu giữ trích dẫn bằng chứng nguyên văn trong tệp `record_evidence_mapping.json`.

---

## 4. BẢO ĐẢM NGUYÊN TẮC KHÔNG TỰ BÙ SỐ LƯỢNG

Theo chỉ đạo tại audit độc lập: **"Ưu tiên một lô nhỏ làm đúng hoàn toàn rồi mở rộng; không ép đạt 1.000 tên nếu chưa đủ nguồn."**
Phiên bản V1.1 kiên quyết không tự bịa đặt hay ghép thêm danh sách để đạt số lượng 1.000 tên. Thay vào đó, 53 bản ghi confirmed là 53 bản ghi đã được kiểm chứng ngữ nghĩa chặt chẽ từng câu chữ với raw responses được lưu trữ vật lý. Quá trình mở rộng lên các quy mô lớn hơn sẽ chỉ được thực hiện khi mỗi đợt có thêm các tệp raw evidence độc lập tương ứng.
