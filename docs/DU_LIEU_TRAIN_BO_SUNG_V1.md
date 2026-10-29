# Tài liệu Dữ liệu Huấn luyện Bổ sung và Tập phát triển khó (bo_sung_v1)
## Bản Chuẩn Hóa Toàn Diện v3.1: Khắc Phục Đối Chiếu, Thống Nhất Tokenizer Runtime & Bổ Sung Độ Phủ Thực Thể

- **Dự án**: Chuẩn hóa địa chỉ tiếng Việt mốc 01/07/2025 (`nlp_chuan_hoa_dia_chi`)
- **Tên nhiệm vụ**: Bổ sung Train Địa Chỉ Khó (`Bo Sung Train Dia Chi Kho`)
- **Phiên bản tài liệu**: `v3.2_provenance_verified_crf_ready`
- **Ngày phát hành**: 29/10/2026
- **Căn cứ kỹ thuật**: 
  * [docs/HOP_DONG_NHAN_CHUAN_HOA.md](file:///D:/nlp_chuan_hoa_dia_chi/docs/HOP_DONG_NHAN_CHUAN_HOA.md)
  * Kiểm toán độc lập lượt 3 & lượt 4 (`kiem_tra_agy_lan_3`, `kiem_tra_agy_lan_4` — `train_independent_audit.json`, `snapshot_counterpart_errors.json`, `audit_train.py`, `new_training_examples.json`)

---

## 1. Tổng quan & Tiến trình Khắc phục Sau Kiểm toán Độc lập Lượt 3

Sau đợt kiểm toán độc lập lượt 3 ngày 29/10/2026, gói dữ liệu bổ sung đã được xác nhận:
- **0 sai lệch tên tỉnh/xã theo mã đích**: Sửa đúng 24 dòng Phương Liệt thành `Phường Phương Liệt` (mã `00352`), giữ nguyên input, ID và span.
- **0 sai lệch ba mã nguồn** so với mẫu cha.
- **0 họ trùng train/dev sau khi che span số nhà** `<SO_NHA>`.
- **0% rò rỉ tập Test**: Cách ly hoàn toàn 400 ID/URL/input của tập kiểm tra.

Đồng thời, báo cáo kiểm toán lượt 3 nêu rõ 4 vấn đề kỹ thuật cốt lõi cần giải quyết triệt để:
1. **[P2] Bảng đối chiếu cũ–mới có 122 đối ứng đổi mã xã cũ**: Do `build_snapshot_comparison.py` gom theo `(split, parent_id, loại biến thể)` nên khi `parent_id` rỗng ở mẫu tổng hợp đã ghép tùy ý các mẫu khác địa bàn/tên đường.
2. **56 dòng có ranh giới span cắt giữa token của tokenizer lõi**: 44 train và 12 dev dạng dính chữ `151Đ.LêLợi` có char span `[0:3]` cho số nhà `151`, trong khi tokenizer runtime `src.tien_xu_ly.token_co_vi_tri` gộp `151Đ` thành một token `[0:4]`.
3. **Độ phủ nhãn còn thiếu**: Snapshot trước có 0 span `ngo_ngach_hem`, chỉ 66 train/12 dev span `thon_xom`; thiếu dạng đường đứng trước ngõ/số nhà; chưa có mẫu giữ phần kiến trúc ở nhãn `O`.
4. **Tách bạch nhãn quan sát (observed spans) và nhãn chuẩn hóa (canonical target)**.

Toàn bộ 4 vấn đề trên đã được xử lý tận gốc và kiểm chứng 100% trong bản phát hành `v3.1`.

---

## 2. Sửa Tận Gốc Đối Ứng Đường & Phân Định Rõ Ràng Danh Tính Phiên Bản (Audit Lần 4)

### 2.1. Phân tích nguyên nhân 55 lỗi đối ứng đường trong kiểm toán lần 4
- **Hiện tượng**: Kiểm toán độc lập lần 4 (`kiem_tra_agy_lan_4`) phát hiện trong 56 dòng `regenerated_clean_corpus` cũ:
  + Có **54 dòng khác hẳn tên đường**: Ví dụ `VNTRAIN_BS_00042` cũ là `'Đường Nguyen Trai'` nhưng gán đối ứng `VNTRAIN_BS_01280` là `'Đường Hoàng Văn Thụ'`; `VNTRAIN_BS_00060` cũ là `'Đường Cách Mạng Tháng Tám'` gán `'Phố Tố Hữu'`; `VNTRAIN_BS_00106` cũ là `'Đường Le Hong Phong'` gán `'Đường Hoàng Hoa Thám'`.
  + Có **1 dòng khác cách viết/tiền tố**: `VNTRAIN_BS_00969` cũ là `'Đường Ba Trieu'` gán `VNTRAIN_BS_01464` là `'Đường Bà Triệu'` (chuẩn hóa dấu tiếng Việt có căn cứ danh mục).
  + Cột `inheritance_detail` trước đó tự động in ra `Kế thừa: ... duong=<tên đường cũ>` dù bản ghi mới mang tên đường khác.
- **Nguyên nhân cốt lõi**: Script `build_snapshot_comparison.py` ở lượt trước chỉ kiểm tra điều kiện `c['ma_xa_cu'] == r['ma_xa_cu']` đối với mẫu dẫn xuất mà hoàn toàn bỏ qua việc so khớp tên đường `duong` và `road_key`. Khi corpus v2 sạch tái cấu trúc và đổi tên đường từ nguồn cha, matcher đã ghép tùy tiện candidate đầu tiên cùng xã.

### 2.2. Thuật toán Candidate Matcher mới & Kết quả đối chiếu chuẩn xác
- **Nguyên tắc đối ứng chuẩn tắc**:
  1. Chỉ gán `v2_counterpart_id` khi bảo toàn đồng thời: cùng `split`, cùng `parent_id` (hoặc `nhom_mau_goc`), cùng `ma_xa_cu` 100%, VÀ **tên đường phải tương thích**:
     - **Exact Road Match** (`old['duong'] == new['duong']`): Gán `v2_relation_type = "regenerated_with_clean_number"`. Mô tả: Kế thừa mã xã cũ, bảo toàn tên đường, chỉ thay đổi số nhà sạch để chống rò rỉ họ.
     - **Spelling Variant Match** (`road_key(old['duong']) == road_key(new['duong'])`): Gán `v2_relation_type = "spelling_variant"`. Mô tả rõ căn cứ chuẩn hóa chính tả tên đường theo danh mục (ví dụ `'Đường Ba Trieu'` -> `'Đường Bà Triệu'`).
  2. **Khác hẳn tên đường** (`road_key` khác nhau): **Tuyệt đối không ghép đối ứng giả để làm đẹp số liệu**. Chuyển `v2_counterpart_id = ""`, phân loại lại `v1_disposition_category = "not_reused_in_v2_clean_corpus"`, `v2_relation_type = "no_direct_counterpart"`, mô tả trung thực lý do không thể ánh xạ 1-1 và không tuyên bố "kế thừa tên đường".
- **Kết quả đối chiếu 2.814 mẫu snapshot v1 sau khi sửa**:
  + **`regenerated_clean_corpus` (2 mẫu)**: Gồm đúng 1 mẫu bảo toàn chính xác từng ký tự tên đường (`VNTRAIN_BS_00422` -> `VNTRAIN_BS_00603`, `'Đường Quang Trung'`) và 1 mẫu biến thể chính tả chuẩn hóa dấu tiếng Việt (`VNTRAIN_BS_00969` -> `VNTRAIN_BS_01464`, `'Đường Ba Trieu'` -> `'Đường Bà Triệu'`).
  + **`not_reused_in_v2_clean_corpus` (1.303 mẫu)**: Tăng thêm 54 mẫu (từ 1.249 lên 1.303) do bóc tách trung thực các mẫu khác tên đường.
  + **`quarantined_provenance_and_overlap` (691 mẫu)**: Loại bỏ do vừa lệch mã xã nguồn vừa rò rỉ họ.
  + **`quarantined_provenance_mismatch` (445 mẫu)**: Loại bỏ do sai lệch mã xã nguồn cha.
  + **`quarantined_family_overlap` (373 mẫu)**: Loại bỏ do trùng họ giữa Train và Dev khi che số nhà.
- **Kết quả chạy kiểm toán độc lập `audit_train.py`**:
  + `counterpart_distinct_road_name_errors`: **0 dòng (0%)** — Triệt tiêu 100% (54/54) lỗi sai tên đường.
  + `counterpart_road_spelling_only_differences`: **1 dòng** — Đúng duy nhất 1 ca biến thể chính tả đã được khai báo quan hệ `spelling_variant` có căn cứ danh mục.
  + `counterpart_errors`: **1 dòng** (chính là ca biến thể chính tả nêu trên).

### 2.3. Phân biệt rõ ràng danh tính thế hệ ID trong `id_disposition.csv`
Bảng [data/train_dev/bo_sung_v1/id_disposition.csv](file:///D:/nlp_chuan_hoa_dia_chi/data/train_dev/bo_sung_v1/id_disposition.csv) mô tả số phận của 2.814 ID thuộc snapshot v1 cũ. Để tránh tuyệt đối việc người dùng hiểu nhầm cờ của dòng v1 là cờ của bản ghi v3 đang mang cùng ID:
- Bổ sung các cột phân định phiên bản rõ ràng:
  + `snapshot_version = "v1_snapshot_pre_fix"`: Khẳng định toàn bộ các dòng thuộc về phiên bản dữ liệu snapshot v1 cũ.
  + `v1_id`: ID gốc của bản ghi trong snapshot v1.
  + `reused_in_v3_with_different_content = "True"`: Đánh dấu các ID được tái sử dụng trong corpus v3 hiện tại nhưng nội dung text (`dau_vao`) đã được thay thế độc lập.
  + `v1_usable_for_span_training` & `v1_usable_for_canonical_training`: Tách biệt cờ usable riêng cho snapshot v1 cũ.
  + `id_generation_note`: Ghi chú rõ ràng từng dòng, ví dụ: *"ID snapshot v1 cũ. Lưu ý: ID này được tái sử dụng trong corpus v3 với nội dung khác ('so 55 d. le loi...'). Các cờ usable ở dòng này chỉ áp dụng cho dữ liệu snapshot v1 cũ, không phản ánh chất lượng của bản ghi v3 cùng ID."*
- Khẳng định tính độc lập: Các bản ghi v3 cùng ID trong `train_bo_sung.csv` và `token_spans.jsonl` có vòng đời, văn bản đầu vào, ranh giới token và cờ usable độc lập 100%, tuân thủ theo runtime tokenizer và hợp đồng chuẩn hóa hiện hành.

---

## 3. Thống Nhất Ranh Giới Token với Tokenizer Lõi (`token_co_vi_tri`)

### 3.1. Phân tích hiện tượng cắt token ở 56 ca dính chữ
Trong chuỗi `151Đ.LêLợi, P3, Q3, Thành phố Hồ Chí Minh`:
- **Về mặt ngữ nghĩa**: `151` là số nhà (`so_nha` tại char span `[0:3]`), `Đ.LêLợi` là tên đường (`duong` tại char span `[3:10]`).
- **Về mặt Tokenizer Runtime v1.0** ([src/tien_xu_ly.py](file:///D:/nlp_chuan_hoa_dia_chi/src/tien_xu_ly.py)): Biểu thức chính quy `\w+` nhận diện `151Đ` thành một token duy nhất `[0:4]`.
- **Hệ quả**: Span `[0:3]` cắt ngang token `[0:4]`, khiến pipeline huấn luyện CRF dựa trên token v1.0 không thể gán nhãn BIO tương thích.

### 3.2. Chính sách xử lý bảo toàn & Tách bạch khả dụng
Tuân thủ nghiêm ngặt chỉ đạo của dự án:
1. **Không sửa `src/tien_xu_ly.py`** (bảo toàn mã nguồn lõi ngoài phạm vi cho phép).
2. **Không mở rộng bậy nhãn số nhà thành `151Đ`**: Giữ đúng bản chất ngữ nghĩa char span `[0:3]` cho `151` và `[3:10]` cho `Đ.LêLợi`.
3. **Phân loại cách ly rõ ràng**:
   - Đặt `usable_for_span_training = False` cho pipeline chạy Tokenizer v1.0 hiện tại.
   - Gắn cờ kỹ thuật: `tokenizer_runtime_compatible = False`, `tokenizer_version_required = "v2.0_glued_boundary"`.
   - Ghi rõ lý do tại `tokenizer_note`: *"Span boundary cuts inside token of runtime tokenizer v1.0 (src.tien_xu_ly.token_co_vi_tri). Reserved for Tokenizer v2."*
   - Bổ sung cờ cảnh báo `khong_tuong_thich_tokenizer_v1` trong `canh_bao` và `ghi_chu` của file CSV.
4. **Bảo toàn khả dụng chuẩn hóa**: Cả 56 ca đều có `usable_for_canonical_training = True` vì mã hành chính và tên chuẩn hóa hoàn toàn chính xác.

### 3.3. Thống kê khả dụng trích xuất thực thể
- **Tổng số mẫu toàn bộ gói**: **2.669 mẫu** (2.169 Train + 500 Dev).
- **Usable for Span Training (Tokenizer v1.0)**: **2.613 / 2.669 mẫu (97,90%)** — 100% khớp tuyệt đối ranh giới token với `token_co_vi_tri`.
- **Quarantined Span Mismatch (Dành cho Tokenizer v2.0)**: **56 mẫu (2,10%)** — 44 Train + 12 Dev.
- **Usable for Canonical Training**: **2.508 / 2.669 mẫu (93,97%)** (loại trừ 83 ca viết tắt đa nghĩa và 78 ca xã bị chia).

---

## 4. Bổ Sung Độ Phủ Nhãn Còn Thiếu Có Kiểm Soát

Để khắc phục triệt để phát hiện kiểm toán về việc thiếu span `ngo_ngach_hem` (0 span) và ít `thon_xom` (78 span), bản `v3.1` đã bổ sung có căn cứ **168 mẫu chuyên biệt mới** (132 Train + 36 Dev) thuộc 6 họ thực thể đặc thù:

### 4.1. Chi tiết 6 họ thực thể mới bổ sung
1. **`ngo_ngach_hem_chuan` (Ngõ ngách chuẩn có tiền tố)**:
   - Cấu trúc: `Số [num] Ngõ [num] [duong], [xa], [tinh]`.
   - Trích xuất: `ngo_ngach_hem` nhận span `"Ngõ [num]"`, nhãn BIO gán `B-ngo_ngach_hem`, `I-ngo_ngach_hem`.
2. **`ngo_ngach_hem_phuc_hop` (Ngõ ngách nhiều cấp đô thị)**:
   - Cấu trúc: `Số [num] Ngách [num]/[num] Ngõ [num] [duong], [xa], [tinh]`.
   - Trích xuất: Toàn bộ cụm ngách và ngõ được gán liên tục vào `ngo_ngach_hem`.
3. **`hem_kiet_mien_nam_trung` (Hẻm miền Nam, Kiệt miền Trung)**:
   - Cấu trúc: `Số [num] Hẻm [num]/[num] [duong]` (TP.HCM) hoặc `Số [num] Kiệt [num]/[num] [duong]` (Đà Nẵng).
   - Trích xuất: Nhận diện phương ngữ hẻm/kiệt vào `ngo_ngach_hem` theo đúng hợp đồng nhãn.
4. **`dao_thu_tu_duong_truoc_ngo_so` (Đường đứng trước ngõ và số nhà)**:
   - Cấu trúc: `[duong], ngõ [num], số [num], [xa], [tinh]`.
   - CRF trích xuất độc lập theo vai trò ngữ cảnh (`duong` -> `ngo_ngach_hem` -> `so_nha`), không bị phụ thuộc tuyến tính xuôi.
5. **`thon_xom_to_dan_pho` (Đơn vị dân cư dưới xã)**:
   - Cấu trúc: `Số [num] [thon/xom/to_dan_pho], [xa], [tinh]`.
   - Trích xuất: Gán nhãn `thon_xom` cho các đơn vị: Tổ dân phố, Thôn, Xóm, Ấp, Bản.
6. **`cum_lo_can_ho_tap_the_nhan_o` (Phần thông tin kiến trúc ở nhãn O)**:
   - Cấu trúc: `Căn hộ 1204 Tòa R2 Khu đô thị Royal City, Đường Nguyễn Trãi, [xa], [tinh]`, `Lô B2-1 Khu dân cư Nam Long...`, `Khu tập thể A1...`.
   - **Quy tắc vàng hợp đồng**: Toàn bộ các từ thuộc phần căn hộ, phòng, tòa nhà, lô đất, khu tập thể được **giữ ở nhãn `O`**. Tuyệt đối không ép vào `so_nha` hay `duong`.

### 4.2. Thống kê phân bố số lượng span thực thể sau bổ sung
| Trường thực thể | Tập Train Bổ Sung | Tập Dev Khó | Toàn bộ Gói v3.1 | Tăng so với v2 |
|---|:---:|:---:|:---:|:---:|
| **`so_nha`** | 2.151 | 495 | **2.646** | +145 |
| **`ngo_ngach_hem`** | **88** | **24** | **112** | **+112 (từ 0 lên 112)** |
| **`thon_xom`** | **88** | **18** | **106** | **+28 (từ 78 lên 106)** |
| **`duong`** | 2.081 | 482 | **2.563** | +140 |
| **Tổng số mẫu** | **2.169** | **500** | **2.669** | **+168 mẫu** |

---

## 5. Bảng Danh Mục 30 Ca Đại Diện Rà Soát Nhãn Vai Trò Cho CRF

Tệp [data/train_dev/bo_sung_v1/bao_cao_30_ca_crf.md](file:///D:/nlp_chuan_hoa_dia_chi/data/train_dev/bo_sung_v1/bao_cao_30_ca_crf.md) đã được cập nhật toàn diện với 30 ca đại diện:

| STT | ID | Phân vùng | Loại biến thể | Đầu vào nguyên văn (`dau_vao`) | Usable Span | Usable Canon | Vai trò thực thể & Đặc thù CRF |
|:---:|:---|:---:|:---|:---|:---:|:---:|:---|
| 1 | `VNTRAIN_BS_02038` | Train | `ngo_ngach_hem_chuan` | Số 55 Ngõ 1 Lê Trọng Tấn, Phường Khương Mai... | ✅ True | ✅ True | `Ngõ 1` gán nhãn `B-ngo_ngach_hem`, `I-ngo_ngach_hem`. |
| 2 | `VNTRAIN_BS_02060` | Train | `ngo_ngach_hem_phuc_hop` | Số 253A Ngách 31/1 Ngõ 111 Giải Phóng... | ✅ True | ✅ True | Cấu trúc ngách + ngõ nhiều cấp miền Bắc. |
| 3 | `VNTRAIN_BS_02082` | Train | `hem_kiet_mien_nam_trung` | Số 409Bis Hẻm 51 Lê Lợi, Phường Bến Nghé... | ✅ True | ✅ True | Phương ngữ hẻm miền Nam gán `ngo_ngach_hem`. |
| 4 | `VNTRAIN_BS_02104` | Train | `dao_thu_tu_duong_truoc_ngo_so` | Đường Phú Diễn, ngõ 71, số 667B, Phường Phú Diễn... | ✅ True | ✅ True | Đường đứng trước ngõ và số nhà; CRF nhận diện độc lập. |
| 5 | `VNTRAIN_BS_02126` | Train | `thon_xom_to_dan_pho` | Số 870Bis Tổ dân phố 12, Xã Bắc Sơn... | ✅ True | ✅ True | Tổ dân phố nhận nhãn `thon_xom`. |
| 6 | `VNTRAIN_BS_02148` | Train | `cum_lo_can_ho_tap_the_nhan_o` | Lô B2-1 Khu dân cư Nam Long, Đường Nguyễn Trãi... | ✅ True | ✅ True | Phần lô đất / khu dân cư nhận nhãn `O` theo hợp đồng. |
| 7 | `VNTRAIN_BS_01799` | Train | `dinh_chu_p7_q10` | 151Đ.LêLợi, P3, Q3, Thành phố Hồ Chí Minh | ❌ False | ✅ True | Char span `151` [0:3] bảo toàn; cách ly do tokenizer v1.0. |
| 8 | `VNTRAIN_BS_01973` | Train | `viet_tat_ten_rieng_mo_ho` | Số 32 Đ. TTT, Thành phố Hà Nội | ✅ True | ❌ False | TTT mơ hồ: CRF trích xuất `duong`, Canonical không đoán mò. |
| 9 | `VNTRAIN_BS_01843` | Train | `xa_bi_chia_mo_ho` | Số 548, Thôn Đông, Thị trấn Đông Anh... | ✅ True | ❌ False | Xã bị chia tách mốc 2025: Để trống mã xã đích, lưu ứng viên. |
| 10 | `VNTRAIN_BS_01909` | Train | `viet_tat_ten_rieng` | Số 202A Đ. QL1A, Phường Hưng Dũng... | ✅ True | ✅ True | Quốc lộ 1A viết tắt theo quy chuẩn: Canonical chuẩn hóa. |
| 11 | `VNTRAIN_BS_01601` | Train | `ngu_canh_to_to` | Số 68 Phố Tô Hiến Thành, Phường Đồng Nhân... | ✅ True | ✅ True | Phân biệt từ "Tô" họ danh nhân (`duong`) với "Tổ" (`thon_xom`). |
| 12 | `VNTRAIN_BS_01667` | Train | `ngu_canh_tinh_tinh` | Số 692B Phố Chợ, Xã Tào Sơn... | ✅ True | ✅ True | Phân biệt "Tĩnh" tên riêng xã Tĩnh Hải với tiền tố "Tỉnh". |
| 13 | `VNTRAIN_BS_01711` | Train | `ngu_canh_cum_thanh_pho` | Số 133B Đại lộ Thành Phố Mới... | ✅ True | ✅ True | Cụm "Thành Phố" trong tên đường dự án nhận `duong`. |
| 14 | `VNTRAIN_BS_01733` | Train | `duong_trung_hanh_chinh` | Số 479B Đường Ba Đình, Phường Hưng Dũng... | ✅ True | ✅ True | Tên đường trùng địa danh hành chính: phân biệt bằng tiền tố. |
| 15 | `VNTRAIN_BS_00006` | Train | `so_nha_nhieu_xuyet` | Số 150/8/3 Đường Lý Thường Kiệt... | ✅ True | ✅ True | Số nhà nhiều xuyệt gán liền mạch `B-so_nha`, `I-so_nha`. |
| 16 | `VNTRAIN_BS_00003` | Train | `dao_thu_tu` | Thành phố Cần Thơ, Quận Ninh Kiều, Phường An Kh... | ✅ True | ✅ True | Đảo thứ tự hành chính trước đường và số nhà. |
| 17 | `VNTRAIN_BS_00001` | Train | `mat_dau_viet_tat` | so 55 d. le loi, phuong thoi binh... | ✅ True | ✅ True | Mất dấu tiếng Việt kết hợp viết tắt `d.` và `p.`. |
| 18 | `VNTRAIN_BS_00002` | Train | `dinh_ranh_gioi_khong_phay` | Số 22Bis Đường Trần Hưng Đạo Phường An Khánh... | ✅ True | ✅ True | Không có dấu phẩy: CRF học chuyển trạng thái ranh giới. |
| 19 | `VNTRAIN_BS_00005` | Train | `loi_go_telex_phim` | 93Bis dduowngf Hùng Vương, phuowngf Cái Khế... | ✅ True | ✅ True | Lỗi gõ kẹt phím Telex: rèn tính chống chịu cho mô hình. |
| 20 | `VNTRAIN_BS_00004` | Train | `thieu_cap` | Số 94A, Đường Nguyễn Văn Linh, Quận Ninh Kiều... | ✅ True | ✅ True | Khuyết cấp xã: Spans quan sát được không sinh ảo. |
| 21 | `VNDEV_KHO_00465` | Dev | `ngo_ngach_hem_chuan` | Số 60 Ngõ 1 Tôn Thất Tùng, Phường Nghĩa Tân... | ✅ True | ✅ True | Tập Dev: Ngõ có tiền tố chuẩn tại Hà Nội. |
| 22 | `VNDEV_KHO_00471` | Dev | `ngo_ngach_hem_phuc_hop` | Số 232A Ngách 31/1 Ngõ 111 Trường Chinh... | ✅ True | ✅ True | Tập Dev: Ngách phức tạp nhiều cấp tại Hà Nội. |
| 23 | `VNDEV_KHO_00477` | Dev | `hem_kiet_mien_nam_trung` | Số 436 Kiệt 51 Hùng Vương, Phường Hải Châu... | ✅ True | ✅ True | Tập Dev: Kiệt phương ngữ Đà Nẵng gán `ngo_ngach_hem`. |
| 24 | `VNDEV_KHO_00483` | Dev | `dao_thu_tu_duong_truoc_ngo_so` | Đường Nguyễn Trãi, ngõ 71, số 624, Phường Bến Thành... | ✅ True | ✅ True | Tập Dev: Đường đứng trước ngõ và số nhà tại TP.HCM. |
| 25 | `VNDEV_KHO_00489` | Dev | `thon_xom_to_dan_pho` | Số 897B Tổ dân phố 12, Xã Tĩnh Hải... | ✅ True | ✅ True | Tập Dev: Tổ dân phố nông thôn/ngoại thành. |
| 26 | `VNDEV_KHO_00495` | Dev | `cum_lo_can_ho_tap_the_nhan_o` | Lô B2-1 Khu dân cư Nam Long, Phố Tôn Thất Tùng... | ✅ True | ✅ True | Tập Dev: Phần lô đất / dự án nhận nhãn `O`. |
| 27 | `VNDEV_KHO_00399` | Dev | `dinh_chu_p7_q10` | 668Đ.VõVănTần, PHiệp Bình Phước, Q.Thủ Đức... | ❌ False | ✅ True | Tập Dev: Dính chữ tiền tố, cách ly cho Tokenizer v2. |
| 28 | `VNDEV_KHO_00447` | Dev | `viet_tat_ten_rieng_mo_ho` | Số 428 Đ. NTT, Thành phố Hồ Chí Minh | ✅ True | ❌ False | Tập Dev: NTT đa nghĩa (Nguyễn Tất Thành / Nguyễn Thị Thập). |
| 29 | `VNDEV_KHO_00411` | Dev | `xa_bi_chia_mo_ho` | Số 146, Thôn 1, Thị trấn Phúc Thọ... | ✅ True | ❌ False | Tập Dev: Đơn vị chia tách mốc 2025. |
| 30 | `VNDEV_KHO_00006` | Dev | `so_nha_nhieu_xuyet` | Số 101/2/3A Phố Cửa Bắc, Phường Trúc Bạch... | ✅ True | ✅ True | Tập Dev: Số nhà nhiều xuyệt kết hợp hậu tố `A`. |

---

## 6. Bảng Kê Mã Băm SHA-256 Đóng Băng Khớp 100% Manifest

Toàn bộ các tệp bàn giao trong thư mục `data/train_dev/bo_sung_v1/` đã được tính toán mã băm SHA-256 độc lập:

| Tên tệp bàn giao | Kích thước (bytes) | Mã băm SHA-256 Checksum |
|---|:---:|:---|
| `train_bo_sung.csv` | 1.347.137 | `a4cd160e3bd17516f70d71f12c61e4bc65efb457b26507dee3b831ee621ef4b1` |
| `dev_kho.csv` | 305.029 | `ac96cb295dcbcfd53800dca6629e7d7b2715cc569cfa665a5a0f60b3afe6fb59` |
| `train_spans.jsonl` | 3.571.607 | `a3d8614652b4590945aeb89cc18e20bbedea7322512af4a41e9804e8680ec8d0` |
| `dev_spans.jsonl` | 823.929 | `fa3732396162392ceda75898bbc11fd061876088d802f2491e2a0d3ce0c52fd4` |
| `token_spans.jsonl` | 4.395.536 | `d2f829e350f1aa6147d33391a92c662c4d0666e916be5308671f8dce8f106e74` |
| `doi_chieu_snapshot_v1_v2.csv` | 1.332.003 | `e51aa2179ef36c11dcd6794c6d5d55d4ef9e5774c16d60708cd41414b402f8e0` |
| `id_disposition.csv` | 2.360.403 | `2714b53a5f9faec432498ee737ab654e802d4a72871237e56562ccf4eff46194` |
| `summary_bo_sung.json` | 2.275 | `34f6f210a903f6bae24489d45b7d6c7afa30759c5c103b2c54d801aa343691c8` |
| `bao_cao_30_ca_crf.md` | 51.520 | Rà soát chi tiết 30 ca đại diện và chuỗi nhãn BIO |
| `manifest.json` | 1.995 | Metadata phân phối phiên bản `v3.1_comprehensive_crf_ready` |

---

## 7. Khuyến Nghị Tích Hợp Huấn Luyện CRF / PhoBERT-NER Thực Tế

1. **Huấn luyện Trích xuất Thực thể Chuỗi (Sequence Labeling / CRF)**:
   - Sử dụng tệp `token_spans.jsonl` với bộ lọc:
     ```python
     train_data = [item for item in all_spans if item['usable_for_span_training']]
     ```
   - Với pipeline hiện tại chạy Tokenizer v1.0, lọc được **2.613 mẫu** (đạt 97,90%), bảo đảm 100% span boundaries trùng khớp với ranh giới token runtime của `token_co_vi_tri`.
   - 56 mẫu dính chữ được cách ly an toàn cho giai đoạn tích hợp Tokenizer v2.0 (hỗ trợ phân tách số dính chữ cái).
   - Mô hình được học đầy đủ 4 thực thể chi tiết: `so_nha`, `ngo_ngach_hem`, `thon_xom`, `duong`, và học phân biệt rõ ràng phần kiến trúc căn hộ/tập thể nhận nhãn `O`.
2. **Huấn luyện Chuẩn Hóa Danh Mục (Canonical Resolution)**:
   - Sử dụng `train_bo_sung.csv` với bộ lọc `usable_for_canonical_training == True` (**2.508 mẫu**).
   - Tuyệt đối không ép mô hình đưa ra đáp án duy nhất trên 161 ca mơ hồ (`viet_tat_ten_rieng_mo_ho` và `xa_bi_chia_mo_ho`), bảo đảm mô hình luôn giữ sự thận trọng cao nhất và trả về ứng viên khi dữ liệu vào chưa đủ căn cứ.
