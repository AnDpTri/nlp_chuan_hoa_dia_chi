# DANH MỤC TÊN ĐƯỜNG PHỐ VIỆT NAM V1.1 (CÓ NGUỒN CHỨNG THỰC ĐỘC LẬP)
## (VIETNAM STREET GAZETTEER V1.1 - POST-AUDIT INDEPENDENT EVIDENCE)

- **Phiên bản:** 1.1.0 (Post-Audit Correction)
- **Ngày cập nhật:** 29/10/2026
- **Tình trạng:** Đã hoàn thành đính chính và xác minh nguồn độc lập (PASS 100%)
- **Căn cứ đính chính:** Báo cáo kiểm tra độc lập tại `danh_gia/ket_qua/audit_agy_duong_train_v2_01/BAO_CAO.md` và `KIEM_TRA_DOC_LAP.json`
- **Phạm vi lưu trữ:** `data/duong/v1/`
- **Bộ công cụ và kiểm thử:** `data/duong/scripts/`, `data/duong/tests/`

---

## 1. MỤC TIÊU VÀ NGUYÊN TẮC THIẾT KẾ ĐỘC LẬP SAU AUDIT

### 1.1. Bối cảnh và Tiếp thu Audit độc lập
Kiểm tra độc lập ngày 29/10/2026 đã chỉ ra các vấn đề căn cốt trong gói dữ liệu ban đầu:
1. **Vòng tròn tự chứng minh (Self-referential):** Bản cũ dùng `generate_sources.py` ghi các danh sách hằng từ `definitions/*.py` ra file `.txt` rồi băm chính file đó. Kiểm tra tên xuất hiện trong các file tự tạo này không phải bằng chứng chứng thực từ bên thứ ba.
2. **Nguồn dẫn là trang chủ (Portal Roots):** 8/10 URL chỉ là trang gốc (`https://congbao.hanoi.gov.vn`, `https://danang.gov.vn`, `https://vanban.chinhphu.vn`...), không dẫn tới văn bản cụ thể; không có HTTP status, không có thời điểm fetch `fetched_at_utc`, không lưu raw payload.
3. **Sai đối tượng văn bản docid 204000:** URL `https://vanban.chinhphu.vn/?docid=204000&pageid=27160` bị ghi nhầm là QĐ 1454/QĐ-TTg, nhưng thực tế trang chính thức là **QĐ 89/QĐ-TCTĐB ngày 09/09/2021** (Quy chế hoạt động Tổ công tác đặc biệt của Thủ tướng Chính phủ).

### 1.2. Các Nguyên tắc Thiết kế Mới (V1.1)
- **Hạ trạng thái minh bạch (Downgrade Policy):** Toàn bộ 1.461 bản ghi cũ chưa có bằng chứng độc lập bị **hạ trạng thái từ `confirmed` xuống `candidate_unverified_source`**, bảo toàn lịch sử tại `data/duong/v1/legacy_v1_snapshot/`. Tuyệt đối không gọi chúng là nguồn pháp lý hay thực địa khi chưa có bằng chứng thô.
- **Ưu tiên chất lượng, không ép số lượng (Quality over Quantity):** Tuyệt đối **không tự sinh thêm danh sách tên để bù số lượng 1.000 tên**. Tập `confirmed` được rút gọn về đúng quy mô một lô thực tế (**53 bản ghi**) có bằng chứng nguồn thật 100%, trích xuất exact snippets và lưu trữ raw response trên đĩa.
- **Bắt buộc lưu trữ Raw Responses:** Mọi nguồn chứng thực phải lưu trữ tệp phản hồi HTTP nguyên bản (`raw_sources/`), ghi nhận URL bài viết/văn bản cụ thể (cấm URL trang chủ), mã HTTP status = 200, thời điểm tải UTC và mã băm SHA-256.
- **Textual Grounding từng câu chữ:** Mọi bản ghi `confirmed` phải có `evidence_snippet` xuất hiện nguyên văn (exact substring) trong raw content.
- **Bảo toàn phạm vi tuyệt đối:** Chỉ tạo/sửa đổi trong `data/duong/` và `docs/DANH_MUC_DUONG_V1.md`. Tuyệt đối không can thiệp vào `src/`, `danh_gia/`, `mo_hinh/`, `data/train_dev/` (đặc biệt không chạm vào `duyet_v2_01`), `data/test/`, `data/clean/`, `tests/` gốc.

---

## 2. NGUỒN CHỨNG THỰC ĐỘC LẬP VÀ BẢO TỒN RAW EVIDENCE

Các tệp phản hồi HTTP nguyên bản được lưu trữ tại `data/duong/v1/raw_sources/` và quản lý bằng `raw_sources_manifest.json`:

| STT | Mã Nguồn (`source_id`) | URL Nguồn Cụ Thể (Deep URL) | Loại Nguồn | Cơ Quan Ban Hành / Căn Cứ | HTTP Status | Dung Lượng (bytes) | SHA-256 (Rút gọn) |
|---|---|---|---|---|:---:|:---:|---|
| 1 | `SRC_RAW_01_HANOI_QD3862` | `https://ttpvhcc.hanoi.gov.vn/chi-dao-cua-lanh-dao-thanh-pho/ha-noi-dat-ten-moi-cho-38-tuyen-pho-14-cong-trinh-cong-cong-trong-nam-2025-2850250724141348377.htm` | `van_ban_quy_pham` | UBND TP. Hà Nội (QĐ số 3862/QĐ-UBND ngày 20/07/2025 đặt tên 38 tuyến đường phố mới) | 200 | 193.051 | `7c053d11bdae...` |
| 2 | `SRC_RAW_02_TPHCM_HDND_QUOCLO` | `https://www.hcmcpv.org.vn/tin-tuc/tphcm-dat-ten-cac-dong-chi-lanh-dao-dang-nha-nuoc-va-cac-dong-chi-chi-huy-chien-dich-ho-chi-minh-tr-1491933298` | `van_ban_quy_pham` | HĐND & UBND TP.HCM (Nghị quyết kỳ họp 20 HĐND khóa X đặt tên 7 tuyến Quốc lộ) | 200 | 81.600 | `f88ec99395d8...` |
| 3 | `SRC_RAW_03_QUOC_LO_QD1454` | `https://baochinhphu.vn/phe-duyet-quy-hoach-phat-trien-mang-luoi-duong-bo-thoi-ky-2021-2030-tam-nhin-den-nam-2050-102299665.htm` | `van_ban_quy_pham` | Thủ tướng Chính phủ (QĐ số 1454/QĐ-TTg ngày 01/09/2021 đăng trên Báo Chính Phủ) | 200 | 347.255 | `885f6352c0d2...` |
| 4 | `SRC_RAW_04_DANANG_1022` | `https://1022.vn/hdnd-thanh-pho-da-nang-thong-qua-nghi-quyet-dat-doi-ten-cho-88-duong-va-cong-trinh/` | `van_ban_quy_pham` | HĐND TP. Đà Nẵng (Nghị quyết kỳ họp thứ 5 đặt đổi tên đường) | 200 | 216.570 | `b312aa486cf9...` |
| 5 | `SRC_RAW_05_DANANG_BAO` | `https://baodanang.vn/dat-ten-duong-cho-pho-3235621.html` | `bao_chi_chinh_thong` | Báo Đà Nẵng trích dẫn Quy chế QĐ 47/2019/QĐ-UBND & tuyến đường Ngũ Hành Sơn | 200 | 110.240 | `b7944de1ae86...` |
| 6 | `SRC_COUNTER_DOCID204000` | `https://vanban.chinhphu.vn/?docid=204000&pageid=27160` | `van_ban_quy_pham` | Tổ công tác đặc biệt (QĐ số 89/QĐ-TCTĐB - Tệp phản chứng đối soát của audit) | 200 | 84.553 | `d70ac973be49...` |

---

## 3. THỐNG KÊ CHI TIẾT TẬP DỮ LIỆU SAU ĐÍNH CHÍNH (V1.1)

Dữ liệu được trích xuất trực tiếp từ [data/duong/v1/statistics.json](file:///D:/nlp_chuan_hoa_dia_chi/data/duong/v1/statistics.json):

```
======================================================================
THỐNG KÊ DANH MỤC ĐƯỜNG PHỐ VIỆT NAM V1.1 (POST-AUDIT)
======================================================================
1. TẬP BẢN GHI CONFIRMED (ĐÃ XÁC MINH BẰNG CHỨNG THỰC TẾ 100%):
   - Tổng số bản ghi confirmed:                 53 bản ghi
   - Số tên đường phân biệt (canonical_name):   53 tên
   - Tỉnh/thành phố được phủ:                   Hà Nội (01), TP. Hồ Chí Minh (79), 
                                                Đà Nẵng (48), Trục liên tỉnh toàn quốc
   - Phân bố theo loại đường (road_type):
     + Đường:                                   34 bản ghi
     + Phố:                                     16 bản ghi
     + Cao tốc:                                  2 bản ghi
     + Quốc lộ:                                  1 bản ghi
   - Tình trạng kỹ thuật:                       ALL_CONFIRMED_HAVE_RAW_EVIDENCE_HTTP200

2. TẬP BẢN GHI CANDIDATES & PENDING (HẠ TRẠNG THÁI MINH BẠCH):
   - Tổng số bản ghi candidate / pending:       1.484 bản ghi
   - Bản ghi cũ từ V1 hạ xuống candidate:       1.461 bản ghi
   - Bản ghi pending / rejected ban đầu:           23 bản ghi
   - Tình trạng kỹ thuật:                       AWAITING_INDEPENDENT_EVIDENCE_FETCH

3. BẢNG MÃ NGUỒN CHỨNG THỰC ĐỘC LẬP (RAW SOURCES):
   - Tổng số tệp phản hồi HTTP nguyên bản:      6 tệp (lưu tại raw_sources/)
   - Nguồn văn bản quy phạm pháp luật:          4 tệp
   - Nguồn cơ quan báo chí chính thống:         1 tệp
   - Nguồn phản chứng đối soát:                 1 tệp
======================================================================
```

---

## 4. CHI TIẾT LÔ 53 BẢN GHI CONFIRMED CÓ BẰNG CHỨNG NGUỒN THẬT

Toàn bộ 53 bản ghi confirmed được lưu tại [danh_muc_duong.jsonl](file:///D:/nlp_chuan_hoa_dia_chi/data/duong/v1/danh_muc_duong.jsonl) và [danh_muc_duong.csv](file:///D:/nlp_chuan_hoa_dia_chi/data/duong/v1/danh_muc_duong.csv), kèm ánh xạ trích dẫn chi tiết tại [record_evidence_mapping.json](file:///D:/nlp_chuan_hoa_dia_chi/data/duong/v1/record_evidence_mapping.json):

### 4.1. Tuyến đường phố Hà Nội (38 bản ghi từ QĐ 3862/QĐ-UBND ngày 20/07/2025)
- **ID từ `STR_CONF_0001` đến `STR_CONF_0038`:**
  - `Phố Nguyễn Hữu Liêu` (phường Xuân Đỉnh)
  - `Phố Doãn Khuê` (phường Xuân Đỉnh)
  - `Phố Học Phi` (phường Yên Hòa)
  - `Phố Hàng Lọng` (phường Cửa Nam)
  - `Phố Hồ Linh Quang` (phường Văn Miếu - Quốc Tử Giám)
  - `Phố Phạm Khắc Hòe` (phường Dương Nội)
  - `Phố Phan Hiền` (phường Dương Nội)
  - `Đường Viên Chiếu` (phường Phúc Lợi, phường Việt Hưng)
  - `Phố Dương Bá Trạc` (phường Long Biên)
  - `Phố Lê Đại` (phường Bồ Đề)
  - `Phố Nguyễn Huy Thảo` (phường Việt Hưng)
  - `Phố Nguyễn Thế Rục` (phường Bồ Đề)
  - `Phố Phan Tây Nhạc` (phường Xuân Phương)
  - `Phố Bạch Thành Phong` (phường Đại Mỗ)
  - `Phố Lê Giản` (phường Đại Mỗ)
  - `Phố Tưởng Dân Bảo` (phường Thanh Liệt)
  - `Đường Xuân Mai` (xã Xuân Mai)
  - `Đường Dương Viết Điển` (xã Xuân Mai)
  - `Đường Ba Đảm Đang` (xã Đan Phượng, xã Liên Minh)
  - `Đường Lê Xá` (xã Bát Tràng)
  - `Đường Ngọc Động` (xã Bát Tràng)
  - `Đường Xuân Thụy` (xã Bát Tràng, xã Gia Lâm)
  - `Đường Chử Đồng Tử` (xã Bát Tràng)
  - `Đường Tiên Dung` (xã Gia Lâm)
  - `Đường Lê Trần Cẩn` (xã Gia Lâm)
  - `Đường Kim Hoa` (xã Tiến Thắng, xã Quang Minh)
  - `Đường An Phú` (xã Mỹ Đức)
  - `Đường Hùng Tiến` (xã Hương Sơn)
  - `Đường Mỹ Xuyên` (xã Phúc Sơn)
  - `Đường Phúc Lâm` (xã Phúc Sơn)
  - `Đường Phùng Xá` (xã Hồng Sơn)
  - `Đường Tam Đức` (xã Hồng Sơn)
  - `Đường Phương Nhị` (xã Ngọc Hồi)
  - `Đường Tam Hiệp` (xã Đại Thanh)
  - `Đường Yên Ngưu` (xã Đại Thanh)
  - `Phố Vũ Đức Úy` (phường Thanh Liệt)
  - `Đường Doãn Tuế` (xã Thường Tín, xã Thượng Phúc)
  - `Đường Lê Công Hành` (xã Thường Tín, xã Thượng Phúc)

### 4.2. Tuyến đường TP. Hồ Chí Minh (7 bản ghi từ Nghị quyết HĐND TP khóa X)
- **ID từ `STR_CONF_0039` đến `STR_CONF_0045`:**
  - `Đường Đỗ Mười`: Quốc lộ 1 đoạn từ nút giao Thủ Đức đến nút giao An Sương.
  - `Đường Lê Đức Anh`: Quốc lộ 1 đoạn từ nút giao An Sương đến vòng xoay An Lạc.
  - `Đường Lê Khả Phiêu`: Quốc lộ 1 đoạn từ vòng xoay An Lạc đến ranh tỉnh Long An.
  - `Đường Lê Quang Đạo`: Quốc lộ 22 đoạn từ Quốc lộ 1 đến cầu An Hạ.
  - `Đường Phan Văn Khải`: Quốc lộ 22 đoạn từ cầu An Hạ đến ranh tỉnh Tây Ninh.
  - `Đường Văn Tiến Dũng`: Quốc lộ 50 đoạn từ đường Nguyễn Văn Linh đến ranh tỉnh Long An.
  - `Đường Hoàng Cầm`: Quốc lộ 1K đoạn từ Quốc lộ 1 đến ranh tỉnh Bình Dương.

### 4.3. Tuyến trục quốc gia (4 bản ghi từ QĐ 1454/QĐ-TTg trên Báo Chính Phủ)
- **ID từ `STR_CONF_0046` đến `STR_CONF_0049`:**
  - `Cao tốc Bắc - Nam phía Đông`: Trục cao tốc dọc quốc gia (Lạng Sơn - Cà Mau).
  - `Cao tốc Bắc - Nam phía Tây`: Trục cao tốc dọc phía Tây.
  - `Đường bộ ven biển`: Tuyến đường bộ kết nối 28 tỉnh/thành ven biển toàn quốc.
  - `Quốc lộ 45`: Tuyến quốc lộ kết nối Ninh Bình - Thanh Hóa (đoạn Mai Sơn - QL45).

### 4.4. Tuyến đường TP. Đà Nẵng (4 bản ghi từ Báo Đà Nẵng / Cổng 1022)
- **ID từ `STR_CONF_0050` đến `STR_CONF_0053`:**
  - `Đường Bình Kỳ`: Phường Hòa Quý, quận Ngũ Hành Sơn.
  - `Đường Lưu Quang Vũ`: Phường Hòa Quý, quận Ngũ Hành Sơn.
  - `Đường Trần Hưng Đạo`: Phường An Hải, quận Sơn Trà.
  - `Đường Hùng Vương`: Phường Bàn Thạch.

---

## 5. HẠ TRẠNG THÁI VÀ BẢO TỒN LỊCH SỬ (DOWNGRADED CANDIDATES)

Tệp [danh_muc_candidates_pending.jsonl](file:///D:/nlp_chuan_hoa_dia_chi/data/duong/v1/danh_muc_candidates_pending.jsonl) lưu trữ **1.484 bản ghi**:
- **1.461 bản ghi hạ từ V1 cũ:** Được đổi ID sang tiền tố `CAND_STR_...`, giữ nguyên `legacy_id` cũ để truy vết.
  + Ghi rõ `status = "candidate_unverified_source"`
  + Ghi rõ lý do: `"CHUA_THU_THAP_DUOC_RAW_EVIDENCE_DOC_LAP (Bản ghi từ definitions cũ chưa có tệp phản hồi HTTP nguyên bản độc lập)"`
  + `verification_status = "pending_evidence_fetch"`
- **23 bản ghi ngoại lệ ban đầu:** Gồm 8 bản ghi `pending` (đề xuất dự thảo, đường dân gian) và 15 bản ghi `rejected` (ngõ ngách, tên tòa nhà, tên bãi bỏ thời thuộc địa, lỗi chính tả).

---

## 6. HƯỚNG DẪN KIỂM CHỨNG ĐỘC LẬP VÀ BỘ TEST RIGOROUS

Hệ thống cung cấp hai công cụ kiểm tra tự động độc lập:

### 6.1. Công cụ Validator 6 bước (`validate_duong.py`)
Chạy lệnh từ thư mục gốc của dự án:
```powershell
powershell -NoProfile -Command "Set-Location D:\nlp_chuan_hoa_dia_chi; python data/duong/scripts/validate_duong.py"
```
Các quy tắc kiểm tra:
1. Xác thực mã băm SHA-256 toàn bộ 30 tệp phân phối so với `manifest.json`.
2. Xác thực 6 tệp raw sources so với `raw_sources_manifest.json`: BẮT BUỘC HTTP 200, có fetched time, CẤM URL trang chủ.
3. Kiểm tra tệp đối chứng docid 204000: Bắt lỗi nếu có bản ghi nào gán docid 204000 cho QĐ 1454/QĐ-TTg.
4. Kiểm tra Textual Grounding & Exact Snippets: 100% bản ghi confirmed phải có exact snippet xuất hiện trong raw HTML.
5. Kiểm tra minh bạch hạ trạng thái: CẤM bất kỳ bản ghi candidate/pending nào được gán status `confirmed`.
6. Kiểm tra tính nhất quán của khóa tra cứu, va chạm và schema.

*Kết quả:* Trả về mã thoát `0`, hiển thị `✅ TOÀN BỘ CÁC BƯỚC KIỂM TRA ĐỀU ĐẠT CHUẨN (PASS 100%)!`.

### 6.2. Bộ kiểm thử tự động, Positive và Negative Fixtures (`test_duong_fixtures.py`)
Chạy lệnh:
```powershell
powershell -NoProfile -Command "Set-Location D:\nlp_chuan_hoa_dia_chi; python data/duong/tests/test_duong_fixtures.py"
```
Bộ kiểm thử gồm **12 bài test** (7 bài kiểm tra tính toàn vẹn/positive fixture + 5 bài Negative Fixtures):
- `test_01_confirmed_records_have_verified_raw_evidence`: 100% confirmed có raw source thật.
- `test_02_all_legacy_records_downgraded_to_candidate`: 1.461 bản ghi cũ đã hạ trạng thái.
- `test_03_road_type_distinction`: Phân định chính xác 16 Phố và 34 Đường.
- `test_04_exact_evidence_snippet_grounding`: 100% snippet khớp nguyên văn trong raw HTML.
- `test_05_technical_keys_generation`: Khóa kỹ thuật chuẩn tắc.
- `test_06_positive_fixture_valid_confirmed_record`: Positive Fixture mẫu đạt chuẩn.
- `test_07_full_dataset_passes_validator`: Toàn bộ bộ dữ liệu đạt mã thoát 0.
- `test_neg_01_reject_homepage_url`: Negative Fixture bắt và từ chối URL trang chủ / portal root.
- `test_neg_02_reject_wrong_document_reference_docid204000`: Negative Fixture chặn sai đối tượng docid 204000.
- `test_neg_03_reject_snippet_not_in_raw_content`: Negative Fixture chặn trích đoạn bịa đặt.
- `test_neg_04_reject_tampered_source_hash`: Negative Fixture chặn tệp nguồn bị can thiệp làm sai SHA-256.
- `test_neg_05_reject_unverified_record_claiming_confirmed`: Negative Fixture chặn bản ghi tự xưng confirmed khi thiếu raw evidence.

*Kết quả:* `Ran 12 tests ... OK`.

---

## 7. GIỚI HẠN THỰC TẾ VÀ LỘ TRÌNH MỞ RỘNG (REALISTIC BOUNDARIES)

1. **Giới hạn quy mô hiện tại:** Lô confirmed hiện tại gồm **53 tuyến đường** được chứng thực tuyệt đối. Đây là cơ sở dữ liệu "sạch 100%" làm nền móng chuẩn tắc.
2. **Không tự tích hợp vào lõi:** Gói này tồn tại độc lập tại `data/duong/v1/`. Tuyệt đối không can thiệp vào pipeline hay mô hình dự đoán khi chưa có quy trình kiểm tra đầu cuối riêng biệt.
3. **Lộ trình mở rộng:** Các đợt tiếp theo sẽ mở rộng tập confirmed bằng cách tiếp tục thu thập thêm các tệp raw response từ các quyết định đặt tên đường chính thức của các tỉnh thành khác (Hải Phòng, Cần Thơ, Thừa Thiên Huế, Nghệ An, Khánh Hòa...) theo đúng quy trình: URL cụ thể -> Tải raw HTML/PDF -> Băm SHA-256 -> Trích xuất exact snippet -> Kiểm tra Textual Grounding.
