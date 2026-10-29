# Tài liệu Gói Dữ liệu Huấn luyện Khó Bổ sung v2 (`bo_sung_v2`)
## Đặc tả Kỹ thuật, Báo cáo Khắc phục Nhãn Grounding, Phân bố Thực thể & Kiểm toán Chống Rò rỉ

- **Dự án**: Chuẩn hóa địa chỉ tiếng Việt mốc 01/07/2025 (`nlp_chuan_hoa_dia_chi`)
- **Tên gói**: Gói Dữ liệu Train Khó v2 (`bo_sung_v2_hard_train`)
- **Phiên bản**: `v2.1_grounded_labels_clean`
- **Ngày phát hành**: 29/10/2026 (Cập nhật sau kiểm toán độc lập audit_agy_duong_train_v2_01)
- **Căn cứ kỹ thuật**:
  * [docs/HOP_DONG_NHAN_CHUAN_HOA.md](file:///D:/nlp_chuan_hoa_dia_chi/docs/HOP_DONG_NHAN_CHUAN_HOA.md)
  * Kiểm toán độc lập `danh_gia/ket_qua/audit_agy_duong_train_v2_01/KIEM_TRA_DOC_LAP.json`
  * Hệ thống mã chuẩn hóa hành chính mốc 01/07/2025 ([data/clean/danh_sach_tinh_xa_2025.csv](file:///D:/nlp_chuan_hoa_dia_chi/data/clean/danh_sach_tinh_xa_2025.csv))

---

## 1. Tôn chỉ & Nguyên tắc Thiết kế Gói v2

Gói dữ liệu `bo_sung_v2` được phát triển hoàn toàn độc lập với gói `bo_sung_v1` (giữ nguyên gói v1 để nghiệm thu riêng), nhằm cung cấp tập huấn luyện khó chuyên sâu cho mô hình CNN / Sequence Tagger và Ranker của dự án mà không chỉ đơn thuần nhân bản số dòng bằng cách thay số nhà.

Các nguyên tắc thiết kế bất khả xâm phạm:
1. **Nhiều họ thực (High Family Diversity)**: Xây dựng trên 650 họ độc lập từ tập `train.csv` gốc. Mỗi họ sinh tối đa 5 biến thể (không vượt quá ngưỡng an toàn 6 biến thể/họ).
2. **100% Provenance Nguồn cha**: Từng bản ghi con đều lưu vết chính xác `parent_id`, `parent_source_url`, `parent_snapshot_sha256`, `family_id` và kế thừa chuẩn xác mã hành chính cũ (`ma_xa_cu`, `ma_huyen_cu`, `ma_tinh_cu`), tên đường gốc từ mẫu cha.
3. **Căn cứ Đúng Vai Trò Ngữ Nghĩa (Strict Grounding & Role Consistency)**:
   - Mọi nhãn chi tiết (`so_nha`, `ngo_ngach_hem`, `thon_xom`, `duong`) nếu khác rỗng bắt buộc phải có span thực tế trong `dau_vao`.
   - **Tuyệt đối không gán thông tin vắng mặt**: Khi biến thể con đã bỏ ngõ hoặc thôn thì nhãn đầu ra tương ứng phải là rỗng `""` theo đúng hợp đồng missing/unknown. Không dùng số nhà làm ngõ, không dùng quận/đường làm xã.
4. **Khai báo Minh bạch Biến đổi**: Mọi trường bị bỏ so với mẫu cha đều được ghi nhận trung thực trong `ghi_chu` (`bo_ngo_ngach_hem_tu_cha`, `bo_thon_xom_tu_cha`) và lưu trong `provenance`.
5. **Cách ly Triệt để & 0% Rò rỉ Holdout (Zero Leakage)**:
   - Loại trừ triệt để 208 họ mẫu train có nguy cơ xung đột với toàn bộ tập đánh giá (Dev gốc, Dev khó v1, và Test).
   - Kiểm toán độc lập đạt **0% trùng input**, **0% trùng URL**, **0% trùng họ mẫu sau khi che span số nhà (`<SO_NHA>`)**.
6. **Độc lập Namespace**: Sử dụng dải định danh độc lập `VNTRAIN_V2_00001` đến `VNTRAIN_V2_03000`.

---

## 2. Khắc Phục Tận Gốc Lỗi Nhãn Thừa Ngõ/Thôn Khi Input Không Có Căn Cứ

### 2.1. Phân tích Nguyên nhân Gốc rễ (Root Cause)
Kiểm toán độc lập tại `KIEM_TRA_DOC_LAP.json` phát hiện trong bản v2.0 trước đó:
- Có **654 mẫu `ngo_ngach_hem`** khác rỗng nhưng span = `null`.
- Có **79 mẫu `thon_xom`** khác rỗng nhưng span = `null`.
- Trùng lặp giữa hai trường: 5 mẫu $\rightarrow$ Tổng số **728 bản ghi phân biệt** bị ảnh hưởng.
- **Ví dụ điển hình**:
  * `VNTRAIN_V2_00001`: Input `"Số 528, Đường Ngô Gia Tự, Phường Đức Giang, Quận Long Biên, Thành phố Hà Nội"` nhưng nhãn mang `ngo_ngach_hem = "Ngõ 528"` kế thừa mù quáng từ mẫu cha `VNTRAIN_00067`.
  * `VNTRAIN_V2_00021`: Input `"Số 27, Duong Han Thuyen, Phường Thủ Đức, Thành phố Hồ Chí Minh"` nhưng nhãn mang `thon_xom = "Khu phố 3"` kế thừa từ cha `VNTRAIN_00092`.
- **Nguyên nhân**: Script `build_bo_sung_v2.py` ở lượt trước khởi tạo `cur_ngo = p_row.get('ngo_ngach_hem')` và `cur_thon = p_row.get('thon_xom')` ở đầu vòng lặp. Khi tạo các biến thể (như `khong_dau_mot_phan`, `viet_tat_manh`, `dinh_token_so_nha_duong`, `dao_thu_tu`, `thieu_cap`), chuỗi `dau_vao` không đưa ngõ hoặc thôn vào, nhưng nhãn đầu ra CSV và `dia_chi_chuan` vẫn giữ nguyên giá trị cha.

### 2.2. Biện pháp Khắc phục Đồng bộ (v2.1)
1. **Thiết lập Nhãn theo Hợp đồng Missing/Unknown**:
   - Khi `spans_dict['ngo_ngach_hem'] is None`: Gán nhãn `ngo_ngach_hem = ""` (chuỗi rỗng).
   - Khi `spans_dict['thon_xom'] is None`: Gán nhãn `thon_xom = ""` (chuỗi rỗng).
   - Cập nhật lại `dia_chi_chuan`: Chỉ ghép các thành phần thực tế có trong nhãn sau biến đổi, loại bỏ hoàn toàn các thông tin vắng mặt.
2. **Khai báo Minh bạch Trường bị bỏ**:
   - Nếu cha có ngõ mà con bị bỏ: Bổ sung `bo_ngo_ngach_hem_tu_cha` trong `ghi_chu`, lưu vết `ngo_cha='...'` trong `provenance`.
   - Nếu cha có thôn mà con bị bỏ: Bổ sung `bo_thon_xom_tu_cha` trong `ghi_chu`, lưu vết `thon_cha='...'` trong `provenance`.
3. **Phân định Cờ Usable Chính Xác**:
   - Không hạ mù quáng cờ `usable_for_canonical_training` xuống `False`.
   - Các ca sau khi đã gán rỗng ngõ/thôn đúng theo hợp đồng, nếu địa bàn hành chính và tên đường đã được chuẩn hóa đơn nhất chính xác thì `usable_for_canonical_training = True` (ví dụ `VNTRAIN_V2_00021`).
   - Các ca mơ hồ theo đúng thiết kế (`xa_bi_chia_mo_ho`, `viet_tat_ten_rieng_mo_ho`) tiếp tục giữ `usable_for_canonical_training = False` (ví dụ `VNTRAIN_V2_00001` do xã Đức Giang cũ bị chia tách).
4. **Báo cáo Diff Chi tiết Từng Dòng**:
   - Toàn bộ 728 bản ghi sửa đổi được xuất chi tiết tại [data/train_dev/bo_sung_v2/label_fix_diff.json](file:///D:/nlp_chuan_hoa_dia_chi/data/train_dev/bo_sung_v2/label_fix_diff.json).

---

## 3. Thống kê Quy mô & Cấu trúc Dữ liệu Sau Sửa

### 3.1. Quy mô Tổng thể
| Chỉ số | Giá trị | Trạng thái |
| :--- | :--- | :--- |
| **Tổng số mẫu huấn luyện** | **3.000 mẫu** | Đủ 100% |
| **Số họ nguồn cha (`family_id`)** | **650 họ** | Độc lập từ train.csv gốc |
| **Số biến thể tối đa / họ** | **5 biến thể** | Nằm trong ngưỡng an toàn $\le 6$ |
| **Số bản ghi nhãn được cập nhật (diff)** | **728 bản ghi** | Khắc phục triệt để ngõ/thôn thừa |
| **Số nhãn khác rỗng nhưng span null** | **0 mẫu (0,00%)** | Triệt tiêu hoàn toàn (trước: 654 ngõ, 79 thôn) |
| **Tỷ lệ bảo toàn mã hành chính cha** | **100%** | Kiểm tra tự động 3.000/3.000 dòng |
| **Tỷ lệ rò rỉ holdout** | **0,00%** | Cách ly 100% với Dev/Test |

### 3.2. Phân bố 12 Loại Biến thể Khó
| Mã Biến Thể | Số Lượng | Tỷ Lệ | Mô Tả Kỹ Thuật |
| :--- | :---: | :---: | :--- |
| `to_hop_bien_the_kho` | 445 | 14,83% | Kết hợp đa biến thể (viết tắt + đảo từ + lỗi gõ + thiếu từ) |
| `dao_thu_tu_thanh_phan` | 305 | 10,17% | Đảo thứ tự: Xã/Phường lên trước Đường/Số nhà |
| `dinh_token_so_nha_duong` | 304 | 10,13% | Dính chữ giữa số nhà và tiền tố đường (`528Đường`, `12Phố`) |
| `thieu_cap_hanh_chinh` | 304 | 10,13% | Khuyết cấp hành chính (mất xã/phường hoặc huyện) |
| `khong_dau_mot_phan` | 299 | 9,97% | Mất dấu một phần tại tiền tố hoặc tên đường/xã |
| `viet_tat_manh_va_ket_hop` | 263 | 8,77% | Viết tắt kết hợp (`P.DV`, `Q.CG`, `TTT`, `BVT`, `P7`, `Q10`) |
| `viet_tat_ten_rieng_mo_ho` | 262 | 8,73% | Viết tắt tên riêng đa nghĩa (`Đ.NQ`, `Đ.LTT`) giữ trạng thái mơ hồ |
| `tron_moc_cu_moi` | 220 | 7,33% | Trộn Huyện cũ với Xã mới chuẩn topological 100% |
| `loi_go_telex_typo` | 163 | 5,43% | Lỗi gõ bàn phím Telex (`dd`, `ee`, `s`, `r`, `x`, `w`) |
| `lap_chong_ten_dia_danh` | 163 | 5,43% | Lặp chập tên địa danh (`Hà Nội, Hà Nội`, `P. Bến Nghé Bến Nghé`) |
| `ngo_ngach_hem_thon_xom` | 162 | 5,40% | Phủ sâu cấp ngõ hẻm (77) và thôn xóm (85) có căn cứ span |
| `xa_bi_chia_mo_ho` | 110 | 3,67% | Xã cũ bị chia tách sang nhiều xã mới (giữ mơ hồ chuẩn tắc) |
| **Tổng cộng** | **3.000** | **100%** | **Đa dạng hóa biến thể theo đúng thực tế vận hành** |

### 3.3. Phân bố Độ Phủ Thực thể Có Căn Cứ (Entity Spans)
- **Số nhà (`so_nha`)**: 3.000 / 3.000 mẫu (100% có span).
- **Đường phố (`duong`)**: 3.000 / 3.000 mẫu (100% có span).
- **Thôn xóm (`thon_xom`)**: 85 mẫu chuyên biệt (100% có span).
- **Ngõ ngách hẻm (`ngo_ngach_hem`)**: 77 mẫu chuyên biệt (100% có span).
- **Nhãn có giá trị nhưng span null**: **ĐÚNG 0 MẪU**.

---

## 4. Phân tích Ranh giới Token & Cách ly Rèn luyện Tokenizer v2

- **Hiện tượng cắt token**: 304 ca dính chữ (`dinh_token_so_nha_duong`) có span `so_nha` cắt ngang bên trong token `\w+` của runtime tokenizer hiện tại.
- **Giải pháp**:
  * Trong `token_spans_v2.jsonl`: Tách token tại ranh giới ngữ nghĩa để chuỗi BIO sequence tags luôn chuẩn cú pháp (tuyệt đối không có `I-tag` đi sau `O`).
  * Gắn cờ minh bạch: `usable_for_span_training = False`, `tokenizer_runtime_compatible = False`, `tokenizer_version_required = "v2.0_glued_boundary"`.
  * **2.696 mẫu còn lại (89,87%)** hoàn toàn tương thích với runtime tokenizer hiện tại (`usable_for_span_training = True`).

---

## 5. Bảng So Sánh Mã Băm SHA-256 Trước & Sau Cập Nhật

| Tệp Dữ Liệu | Trước Sửa (v2.0) SHA-256 / Size | Sau Sửa (v2.1) SHA-256 / Size | Ghi Chú Thay Đổi |
| :--- | :--- | :--- | :--- |
| **`train_bo_sung_v2.csv`** | `b61ace0964f7a313...` (2.262.331 B) | `e334ea617d958c818b3a8be989b0311fb4a79b51677eb5def0cb9cdae1746375` (2.309.794 B) | Sửa 728 dòng thừa ngõ/thôn, cập nhật địa chỉ chuẩn & provenance |
| **`train_spans_v2.jsonl`** | `1fad639e3b398776...` (880.155 B) | `1fad639e3b3987766db32ca6bf733f1a9e6a91c0d1acf5c07912c859ded479db` (880.155 B) | Giữ nguyên 100% (spans ký tự vốn đã chuẩn) |
| **`token_spans_v2.jsonl`** | `4db2e8f387474323...` (4.398.904 B) | `4db2e8f387474323fd37a369c6a7c03f1fbc209f64e49fa7d32c3d42687d3032` (4.398.904 B) | Giữ nguyên 100% (token BIO và cờ usable) |
| **`label_fix_diff.json`** | *(Chưa có)* | `8d9a70dce90d10af2f77758722f89a9dbf398777cb685dac3b40c684678650c8` (674.316 B) | File mới: Báo cáo Before/After chi tiết 728 bản ghi |
| **`anti_leakage_audit.json`**| `49782c9329137b6f...` (1.941 B) | `49782c9329137b6f9d41bdd936beb123db7922d82ba515f28bf07dc88431f443` (1.941 B) | Giữ nguyên 100% (0% rò rỉ holdout) |
| **`distribution_summary.json`**| `fab066f84fe575b0...` (1.325 B) | `fab066f84fe575b0fa9fcd3c11d7f298880acd39af3e108f6ff2e67d5bd174c6` (1.325 B) | Giữ nguyên 100% |
| **`manifest.json`** | `32a4ec503299de90...` (2.541 B) | `ec356694121901fba9a2aa49afa133522a66f9c5197cac5491caf20557ac49cc` (2.692 B) | Đóng băng toàn bộ checksum phiên bản mới |

---

## 6. Kết Quả Kiểm Thử & Lệnh Tái Hiện

Bộ công cụ kiểm định của gói đặt trong phạm vi thư mục riêng:
- **Script kiểm định chất lượng & grounding**: [data/train_dev/scripts/bo_sung_v2/validate_bo_sung_v2.py](file:///D:/nlp_chuan_hoa_dia_chi/data/train_dev/scripts/bo_sung_v2/validate_bo_sung_v2.py)
- **Bộ kiểm thử đơn vị & 11 Negative Fixtures**: [data/train_dev/bo_sung_v2/tests/test_train_bo_sung_v2.py](file:///D:/nlp_chuan_hoa_dia_chi/data/train_dev/bo_sung_v2/tests/test_train_bo_sung_v2.py)

### Lệnh Tái hiện Kiểm tra:
```bash
# 1. Chạy thẩm định toàn vẹn chất lượng, grounding & chống rò rỉ:
python data/train_dev/scripts/bo_sung_v2/validate_bo_sung_v2.py

# 2. Chạy toàn bộ 22 ca kiểm thử đơn vị & negative fixtures:
python -m unittest data/train_dev/bo_sung_v2/tests/test_train_bo_sung_v2.py
```
**Kết quả kiểm tra thực tế:**
- `validate_bo_sung_v2.py`: **PASS 100%** trên toàn bộ 9 tiêu chí.
- `test_train_bo_sung_v2.py`: **Ran 22 tests in 0.661s — OK (22/22 tests PASS 100%)**.

---

## 7. Khuyến Cáo Sử Dụng & Giới Hạn Cần Lưu Ý

> [!NOTE]
> Mặc dù toàn bộ 3.000 mẫu đã vượt qua các bộ kiểm tra cơ học, grounding và kiểm toán chống rò rỉ với kết quả PASS 100%, dự án **không coi toàn bộ gói là dữ liệu gold hoặc xác minh ngữ nghĩa 100% một cách giáo điều**.
> Khi đưa vào huấn luyện thực tế, khuyến nghị các nhóm thực nghiệm lưu ý:
> 1. **304 ca dính chữ**: Sử dụng cờ `usable_for_span_training = False` khi chạy pipeline Tokenizer v1 hiện tại. Chỉ bật khi đánh giá hoặc huấn luyện Tokenizer v2 cải tiến.
> 2. **372 ca mơ hồ (`xa_bi_chia` và `viet_tat_ten_rieng`)**: Sử dụng cờ `usable_for_canonical_training = False` để tránh làm nhiễu hàm loss chuẩn hóa đơn nhất của Ranker.
> 3. **Bản lọc độc lập tại `data/train_dev/duyet_v2_01`**: Phục vụ các thí nghiệm lọc riêng của nhóm nghiên cứu, không can thiệp hoặc ghi đè.
