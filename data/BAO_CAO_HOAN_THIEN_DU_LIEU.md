# BÁO CÁO HOÀN THIỆN DỮ LIỆU DỰ ÁN (CẬP NHẬT TOÀN DIỆN ĐỢT 3)

**Đề tài:** Xây dựng hệ thống chuẩn hóa địa chỉ tiếng Việt theo đơn vị hành chính mới sau sáp nhập 2025  
**Môn:** Xử lý ngôn ngữ tự nhiên, lớp KHMT K22A  
**Mã nguồn:** `D:\nlp_chuan_hoa_dia_chi`  
**Mốc dữ liệu chuẩn hóa:** **01/07/2025** (theo Quyết định số 19/2025/QĐ-TTg)  
**Thời điểm hoàn thành:** Tháng 10/2026  

---

## 1. TÓM TẮT KẾT QUẢ THỰC HIỆN

Nhiệm vụ đã hoàn thiện toàn diện các khâu xử lý dữ liệu hành chính, tạo lập tập huấn luyện/phát triển và thiết lập quy trình kiểm chuẩn tập test, tuân thủ nguyên tắc **phân biệt rõ phần kiểm tra bằng code với phần cần con người xác nhận**:

| Hạng mục | Trạng thái kỹ thuật | Trạng thái dữ liệu | Ghi chú |
|---|:---:|:---:|---|
| **Sửa nhãn Train/Dev theo span `dau_vao`** | **PASS** (100% tự động bằng script) | Khắc phục 100% lỗi span | Sửa dứt điểm việc lấy thẻ OSM đè lên input. Sửa các ca số nhà `18B`, `402`, `4A` và không tự ý thêm đường cho `Chung cư C2 Xuân Đỉnh`. |
| **Xử lý nhập nhằng mốc cũ/mới** | **PASS** (100% tự động) | Không mặc định mốc cũ | Loại bỏ các ca mốc nhập nhằng không có huyện chứng thực khỏi tập nhãn tin cậy (`mo_ho_moc_cu_moi`). |
| **Bổ sung Ngõ/Ngách/Hẻm, Trộn mốc & Lỗi gõ** | **PASS** (100% tự động bằng script) | Corpus 5.700 mẫu (Train: 4.564, Dev: 1.136) | 611 mẫu có `ngo_ngach_hem`, 380 mẫu trộn mốc hợp lệ (topologically verified), 500 mẫu lỗi gõ có chủ đích. |
| **Sửa Validator & Kiểm thử hồi quy test** | **PASS** (24/24 tests đạt 100%) | Độc lập Human vs AI review | Bổ sung `da_duyet_ai`, kiểm tra ngày lịch, tên reviewer, cơ chế duyệt xã bị chia, tính lũy đắc, kiểm tra span offset >= 0 không chồng lấn, kiểm tra căn cứ pháp lý HTTP 200/404, thực sự chạy engine trên fixture và bộ negative tests (boundary, role, admin grounding, NFD alignment). |
| **Đồng bộ bảng duyệt & Xã bị chia** | **PASS** (100% tự động) | Bảng đối chiếu hoàn chỉnh | `kiem_tra_tien_do_duyet.py --sync` đồng bộ nhất quán nhãn, cảnh báo, ứng viên; mang tính lũy đắc tuyệt đối; `tao_bang_duyet.py` bảo toàn ô người dùng đã nhập. |
| **Tự duyệt toàn bộ 400 mẫu test bằng AI** | **PASS** (100% tự động bởi Agent) | **400 / 400 mẫu đã kiểm toán** | **289 dòng** đạt `da_duyet_ai` (263 đủ căn cứ tham chiếu, 26 sửa nhãn theo span chuỗi `grounded_29_patches.py`); **111 dòng** bảo lưu `can_duyet` (36 ca xã bị chia được thu hồi về rỗng, 1 ca VNTEST0040 và 74 ca thiếu/chưa xác định xã); 37 ca tra cứu web và văn bản nghị quyết. |

---

## 2. BẰNG CHỨNG MÃ BĂM VÀ TOÀN VẸN TẬP TEST

| Tên tệp | SHA-256 nguyên bản sơ bộ | SHA-256 sau khi AI duyệt đợt 3 | Tình trạng |
|---|---|---|:---:|
| `data/test/dia_chi_test.csv` | `11c79938a041c22351cd88338d216d7cd094d313b6a1c045c48262a13c178c3a` | `eec94298e599589a0778b4009fbeae621bb98fa27f2cb0d27a53fdb6e130b7e9` | **400 ID, đầu vào, URL nguồn bảo toàn 100%** |
| Bản sao lưu gốc (`backup_before_ai_review/`) | `11c79938a041c22351cd88338d216d7cd094d313b6a1c045c48262a13c178c3a` | `11c79938a041c22351cd88338d216d7cd094d313b6a1c045c48262a13c178c3a` | Lưu trữ nguyên trạng để đối chiếu phục hồi |
| `data/clean/moi_tinh.csv` | `e18687784707867b3b44a70265fc37881dea5b8f41fd4f00d8b3462c6345da96` | `e18687784707867b3b44a70265fc37881dea5b8f41fd4f00d8b3462c6345da96` | Giữ nguyên mốc 01/07/2025 (34 tỉnh/thành) |

- Số lượng mẫu tập test: **400 dòng** (232 dòng ban đầu là `can_duyet`, 168 dòng ban đầu là `tu_dong_khop`).
- Phân loại kiểm toán AI sau rà soát độc lập đợt 3: **400 / 400 dòng**:
  + **289 dòng** đạt `da_duyet_ai` (72.2%): gồm 263 dòng đủ căn cứ tham chiếu và 26 dòng sửa nhãn theo span chuỗi.
  + **111 dòng** giữ `can_duyet` (27.8%): gồm 36 ca xã bị chia (33 ca baseline + 3 ca Xã Lạc Đạo Hưng Yên), 1 ca VNTEST0040 và 74 ca thiếu/chưa xác định xã.
- Số lượng con người đã duyệt thực tế: **0 dòng** (`human_reviewed_rows: 0`).
- Trạng thái đánh giá vàng: `is_ready_for_gold_evaluation: false`, `provisional_only: true` (bảo đảm liêm chính khoa học, chỉ kích hoạt khi có con người nghiệm thu).
- Tệp bàn giao phân loại chi tiết 400 ID: [phan_loai_chi_tiet_400_id.csv](file:///D:/nlp_chuan_hoa_dia_chi/data/test/phan_loai_chi_tiet_400_id.csv) và [phan_loai_chi_tiet_400_id.md](file:///D:/nlp_chuan_hoa_dia_chi/data/test/phan_loai_chi_tiet_400_id.md).

---

## 3. CÁC CẢI TIẾN VÀ SỬA ĐỔI ĐỢT 3 THEO KIỂM TRA ĐỘC LẬP

### 3.1. Chặn khớp chuỗi con sai ranh giới token và sai vai trò
1. **Ranh giới token số nhà (`check_token_boundary`):**
   - Số nhà bắt buộc phải là token độc lập, ký tự liền trước và liền sau không được là ký tự chữ số `[a-z0-9]` hoặc ký tự phân cách số nhà (`/`, `-`).
   - Ngăn chặn hoàn toàn lỗi bóc tách chuỗi con như ca fixture `house_substring_81`: chuỗi đầu vào `181 Tây Thạnh...` cài `so_nha = 'Số 81'`, hệ thống bắt lỗi vi phạm ranh giới vì trước `'81'` là `'1'` (thuộc token `'181'`).
2. **Kiểm tra vai trò ngữ cảnh (`check_context_role` & `is_valid_house_number_val`):**
   - Giá trị `so_nha` bắt buộc phải chứa chữ số hoặc định danh lô/thửa (`lô`, `thửa`, `sh`), không được thuần túy là tên địa danh hành chính.
   - Ngăn chặn hoàn toàn ca fixture `house_role_district`: cài `so_nha = 'Số Tân Phú'`, hệ thống phát hiện `'Tân Phú'` là tên quận/huyện và từ chối cấp nhãn. Đồng thời vị trí span xuất hiện sau các tiền tố ĐVHC (`Q.`, `Quận`, `P.`, `Phường`, `H.`, `Huyện`, `X.`, `Xã`...) không được bóc tách làm số nhà hay tên đường.

### 3.2. Chứng minh chuỗi đơn vị hành chính từ chuỗi đầu vào (`check_admin_grounding`)
- Hệ thống kiểm tra trực tiếp bằng chứng tên xã cũ (`old_wi`) hoặc xã mới (`new_wi`) có xuất hiện trong chuỗi `dau_vao` hay không.
- Kiểm tra tính nhất quán của quận/huyện, không cho phép gán mã huyện mâu thuẫn với quận/huyện xuất hiện trên đầu vào.
- Bắt lỗi ca fixture `unobserved_valid_admin_chain`: chuỗi đầu vào `181 Tây Thạnh...` cài gán chuỗi hành chính hợp lệ Bến Nghé (mã `26740`) / Quận 1 (mã `760`) -> Cả engine và validator đều bắt lỗi `unobserved administrative ward in input` và từ chối `da_duyet_ai`.

### 3.3. Ánh xạ offset trỏ đúng chuỗi gốc hỗ trợ Unicode NFD
- Xây dựng hàm `build_normalized_mapping(s)` duyệt từng grapheme cluster (ký tự gốc kèm dấu tổ hợp), xây dựng bảng ánh xạ index chính xác từ chuỗi chuẩn hóa về ký tự bắt đầu/kết thúc trên chuỗi gốc.
- Đối soát thành công ca fixture `nfd_alignment_api`: với chuỗi Unicode NFD `'12 Tây Thạnh'`, output đường `'Tay Thanh'` được ánh xạ trỏ đúng `[3:14]` cắt chuỗi gốc thành `'Tây Thạnh'` (đủ 11 code points NFD), chuẩn hóa bỏ dấu cho ra đúng `'tay thanh'`, không còn bị cắt cụt lệch offset thành `[3:12]` (`'Tây Thạ'`).

### 3.4. Đính chính văn bản pháp lý và xử lý mốc thời gian
1. **Nghị quyết TP Hà Nội:** Đính chính sai sót gọi nhầm trước đây; văn bản chính thức của Quốc hội về sắp xếp ĐVHC cấp xã của TP Hà Nội là **Nghị quyết số 1286/NQ-UBTVQH15** (ban hành ngày 14/11/2024, có hiệu lực từ ngày 01/01/2025; URL chính thức: `https://xaydungchinhsach.chinhphu.vn/toan-van-nghi-quyet-so-1286-nq-ubtvqh15-sap-xep-don-vi-hanh-chinh-cap-xa-cua-thanh-pho-ha-noi-119241121144810696.htm`).
2. **Nghị quyết số 1192/NQ-UBTVQH15:** Là văn bản sắp xếp ĐVHC cấp xã của **TP Cần Thơ** (ban hành 28/09/2024, hiệu lực 01/11/2024), lưu trữ phục vụ đối soát Cần Thơ.
3. **Nghị quyết số 1232/NQ-UBTVQH15 (TP Hải Phòng):** Ban hành 24/10/2024, hiệu lực 01/01/2025. Tại Điều 1 khoản 2 sáp nhập Lạc Viên và Máy Tơ vào Phường Gia Viên (Q. Ngô Quyền). Giải trình rõ ca `VNTEST0040` (`1B Thiên Lôi, P. Gia Viên`) có mâu thuẫn ranh giới giữa Phường Gia Viên thuộc Q. Ngô Quyền và Phố Thiên Lôi thuộc Q. Lê Chân; bảo lưu trạng thái `can_duyet`.
4. **Xã Lạc Đạo (Hưng Yên):** Trong bảng chuyển đổi `doi_chieu_xa_cu_moi.csv`, mã cũ `11989` (Xã Lạc Đạo, Huyện Văn Lâm) chia thành 2 xã đích: Xã Lạc Đạo (`11992`) và Xã Đại Đồng (`11995`). Chuyển 3 ca `VNTEST0046`, `VNTEST0053`, `VNTEST0055` sang nhóm xã bị chia (`fan-out = 2`), để trống `ma_xa`, giữ cờ `xa_bi_chia` và danh sách ứng viên `['11992', '11995']`, bảo lưu `can_duyet`.
5. **Đính chính 16 mã `ma_xa_cu` trong 29 patches:** Sửa triệt để các mã bị nhầm sang mã đích mới thành đúng mã xã cũ tương ứng với tên gọi trên `dau_vao` (An Khánh `31149`, Cát Lái `27109`, Nam Mẫu `01909`, Điện Dương `20581`, Nghĩa Thành `24612`, Tân Xuân `25204`, Điện Nam Bắc `20578`, P17 Gò Vấp `26875`, Tả Van `03040`, Tam Thái `20386`, Tiến Hưng `25213`, Tóc Tiên `26731`, La Pán Tẩn `04483`, Duy Sơn `20620`, Quản Bạ `00898`, Quế Châu `20680`).
6. **Bỏ hardcode thời gian:** Bỏ hoàn toàn chuỗi hardcode `thoi_diem_tra_cuu = '2026-10-29T14:15:00+07:00'`; để trống `""` khi chưa có hồ sơ mốc thời gian riêng từng nguồn.

---

## 4. QUY TRÌNH DUYỆT TẬP TEST VÀ BỘ KIỂM THỬ HỒI QUY

### 4.1. Bộ kiểm thử hồi quy độc lập (`tests/test_review_validation.py`)
Được thiết kế chạy trên bản sao tạm (`tempfile.mkdtemp`), tuyệt đối không ghi đè hay thay đổi dữ liệu test thật. Kết quả chạy **24/24 tests PASS 100%**:
1. *Test 1:* Kiểm tra tập test thật hiện tại -> PASS cấu trúc, 0 dòng da_duyet, `is_ready_for_gold = False`.
2. *Test 2:* Dòng da_duyet có metadata hợp lệ -> PASS, đếm đúng số dòng đã duyệt.
3. *Test 3:* Đánh dấu da_duyet nhưng tên người là bot/rỗng -> Bị từ chối (FAIL).
4. *Test 4:* Ngày duyệt không tồn tại theo lịch (`2026-02-30`) -> Bị từ chối (FAIL).
5. *Test 5:* Thiếu lý do duyệt -> Bị từ chối (FAIL).
6. *Test 6:* Người duyệt giải quyết xã bị chia với bằng chứng hợp lệ -> PASS.
7. *Test 7:* Tự ý điền xã đích khi chưa có người duyệt -> Bị từ chối (FAIL).
8. *Test 8:* Người duyệt chọn xã đích bịa đặt ngoài bảng đối chiếu -> Bị từ chối (FAIL).
9. *Test 9:* Người duyệt xem xét xã bị chia nhưng để trống vì thiếu căn cứ -> PASS.
10. *Test 10:* Tái chạy `--sync` nhiều lần không nhân đôi nhật ký -> PASS.
11. *Test 11:* Tái tạo bảng duyệt bảo toàn dữ liệu người dùng đã nhập -> PASS.
12. *Test 12:* AI review ghi nhận `da_duyet_ai`, tăng `ai_reviewed_rows`, không tăng `human_reviewed_rows`, `is_ready_for_gold = False` -> PASS.
13. *Test 13:* AI review giải quyết xã bị chia có bằng chứng đối chiếu hợp lệ -> PASS.
14. *Test 14:* AI review gán sai đích không thuộc tập chuyển đổi cho xã bị chia -> Bị từ chối (FAIL).
15. *Test 15:* Kiểm tra giải thuật căn chỉnh span thật: 168 ca `tu_dong_khop` đều có offset `[start:end]` với `start >= 0`, `end > start`, chuỗi con `dau_vao[start:end]` khớp chính xác token quan sát được, không chồng lấn, 0 ca có span âm `[-1:8]` -> PASS.
16. *Test 16:* Kiểm tra 37 ca có `can_cu_web`: phân biệt minh bạch giữa 12 ca trực tuyến HTTP 200 (NQ 1685 TP.HCM) và 25 ca tra cứu dẫn chiếu căn cứ nghị quyết/đề án chính thức, có mốc hiệu lực 01/07/2025 và thời điểm rà soát 2026-10-29 -> PASS.
17. *Test 17:* Toàn bộ 36 ca xã bị chia (kể cả 9 ca kiểm toán và 3 ca Lạc Đạo) đều để trống `ma_xa` và `xa_phuong`, giữ cờ `xa_bi_chia` và trạng thái `can_duyet` -> PASS.
18. *Test 18:* Lệnh `--sync` bảo lưu đúng 111 dòng `can_duyet` / `chua_du_can_cu`, không bao giờ chuyển các dòng này sang `da_duyet_ai` trong `dia_chi_test.csv` -> PASS.
19. *Test 19:* Tính lũy đắc (idempotency) của `--sync` khi chạy 2 lần liên tiếp: diff = 0 -> PASS.
20. *Test 20:* Công cụ tiến độ đếm diff nhãn thực tế báo đúng chính xác 28 dòng có diff nhãn so với baseline -> PASS.
21. *Test 21:* Engine tự duyệt và đồng bộ thực sự chạy trên fixture tạm thời (`tempdir`), bảo toàn 100% dữ liệu do con người nhập (`loai_nguoi_duyet == 'human'`), giữ đủ 400 ID trong audit log và validator đếm đúng số dòng human -> PASS.
22. *Test 22:* Bộ kiểm toán âm tính chạy trực tiếp trên fixture engine và validator thực tế (`tempdir`):
    - Bảo toàn chỉnh sửa hiện hành không cờ human (`w = dict(cur)`), bảo toàn ghi chú tùy chỉnh (`CURRENT_EDIT_SENTINEL_KEEP_ME`).
    - Bắt lỗi nhãn trích xuất không quan sát được trên đầu vào (`ABSENT FROM INPUT SENTINEL`).
    - Bảo lưu `can_duyet` khi xung đột với patch.
    - Bắt lỗi mã xã đích không tồn tại trong danh mục.
    - Bắt lỗi khớp chuỗi con sai ranh giới token (`house_substring_81`).
    - Bắt lỗi sai vai trò ĐVHC làm số nhà (`house_role_district`).
    - Bắt lỗi gán chuỗi hành chính không quan sát được trong đầu vào (`unobserved_valid_admin_chain`).
    - Kiểm toán ánh xạ offset Unicode NFD (`nfd_alignment_api` ra đúng `[3:14]`).
    - Xác nhận fixture cô lập tuyệt đối, không làm thay đổi các tệp thật -> PASS.
23. *Test 23:* Kiểm tra tệp phân loại chi tiết 400 ID (`phan_loai_chi_tiet_400_id.csv` và `.md`): đủ 400 ID, 263 `du_can_cu_tham_chieu`, 26 `nhan_can_sua`, 111 `chua_du_can_cu` -> PASS.
24. *Test 24:* Kiểm tra chuyên sâu `VNTEST0040`: Input `1B, Phố Thiên Lôi, Phường Gia Viên, Hải Phòng`, xác nhận giải trình đúng việc Phường Gia Viên (Q. Ngô Quyền) theo NQ 1232 sáp nhập Lạc Viên và Máy Tơ, mâu thuẫn ranh giới với Phố Thiên Lôi (Q. Lê Chân), không nhầm sang Đằng Giang -> PASS.

---

## 5. TỔNG KẾT KẾT QUẢ KIỂM CHỨNG TOÀN DỰ ÁN

| STT | Kịch bản kiểm tra | Lệnh chạy | Kết quả | Ghi chú |
|:---:|---|---|:---:|---|
| 1 | Làm sạch danh mục ĐVHC | `py -3.12 data/clean/scripts/clean_and_validate.py` | **PASS** | 34 tỉnh, 6 thành phố TW, 0 lỗi mốc 2026. |
| 2 | Ghim mã băm danh mục | `py -3.12 data/test/scripts/pin_catalogues.py` | **PASS** | Khớp 100% `catalogue_manifest.json`. |
| 3 | Lớp đối soát mốc 2025 | `py -3.12 data/test/scripts/asof_2025.py` | **PASS** | `type_overrides: 0`. |
| 4 | Chạy Engine tự duyệt AI | `py -3.12 data/test/scripts/ai_review_engine.py` | **PASS** | 400/400 mẫu kiểm toán; 100% span offset >= 0 không chồng lấn; bỏ thời gian giả; xuất tệp phân loại chi tiết 400 ID. |
| 5 | Kiểm chuẩn tập test sau duyệt | `py -3.12 data/test/scripts/validate_dataset.py` | **PASS** | Cấu trúc PASS; 289 `da_duyet_ai`, 111 `can_duyet`, 0 `human_reviewed_rows`, `is_ready_for_gold: false`, `provisional_only: true`. |
| 6 | Theo dõi tiến độ duyệt & sync | `py -3.12 data/test/scripts/kiem_tra_tien_do_duyet.py --sync` | **PASS** | Đồng bộ lũy đắc (idempotent); đếm đúng 28 diff nhãn thực tế; bảo lưu 111 `can_duyet`. |
| 7 | Hồi quy kiểm chuẩn quy trình duyệt | `py -3.12 tests/test_review_validation.py` | **PASS** | **24/24 tests pass 100%** trên fixture tạm thời (bao gồm bộ negative tests). |
| 8 | Sinh tập Train/Dev | `py -3.12 data/train_dev/scripts/prepare_train_dev.py` | **PASS** | 4.564 Train / 1.136 Dev. Đối chiếu span 100%. |
| 9 | Chống rò rỉ & span Train/Dev | `py -3.12 data/train_dev/scripts/validate_train_dev.py` | **PASS** | 0% rò rỉ, 100% span hợp lệ, 100% tương thích topo. |
| 10 | Phân loại chi tiết 400 ID test | `data/test/phan_loai_chi_tiet_400_id.csv` & `.md` | **PASS** | Đủ 400 ID: 263 đủ căn cứ tham chiếu, 26 nhãn cần sửa, 111 chưa đủ căn cứ bảo lưu (36 xã bị chia). |

---

## 6. PHẦN VIỆC CÒN CẦN CON NGƯỜI THỰC HIỆN

Toàn bộ script, validator, pipeline, engine tự duyệt AI và kiểm thử tự động đã hoàn thành xuất sắc và đạt 100% PASS. Các phần việc bắt buộc cần con người thực hiện trước khi công bố bộ test vàng:
1. **Nghiệm thu kết quả AI duyệt trong `data/test/bang_duyet_test.csv` và `data/test/nhat_ky_ai_duyet.csv`:**
   - Đối soát 26 ca AI đã sửa đổi nhãn theo span chuỗi đầu vào (`grounded_29_patches.py`).
   - Xác nhận chữ ký người duyệt thật bằng cách chuyển đổi trạng thái sang `da_duyet`, cập nhật cột `nguoi_duyet` (tên thật con người), `ngay_duyet` (ngày thật) và `loai_nguoi_duyet = human`.
2. **Thẩm định 36 ca xã bị chia còn bảo lưu:**
   - Sử dụng hồ sơ địa chính hoặc bản đồ giải thửa chi tiết của địa phương để xác định số nhà cụ thể thuộc phường nào (khi cần đạt tỷ lệ 100% xã có mã).
3. **Kích hoạt tập test vàng chính thức:**
   - Chạy `py -3.12 data/test/scripts/kiem_tra_tien_do_duyet.py --sync` để đồng bộ chữ ký người duyệt vào `dia_chi_test.csv`.
   - Chạy `py -3.12 data/test/scripts/validate_dataset.py` để hệ thống tự động xác nhận `is_ready_for_gold_evaluation: true`, hoàn tất bộ đáp án vàng phục vụ đánh giá mô hình.
