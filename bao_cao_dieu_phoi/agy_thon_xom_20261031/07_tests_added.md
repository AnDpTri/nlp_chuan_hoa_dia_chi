# Báo Cáo Kiểm Thử Độc Lập Ranh Giới Thôn/Xóm

**Mã đối chiếu thực nghiệm:**
- **Thời gian thực hiện**: 2026-10-31
- **Dự án gốc**: `D:\nlp_rf_E`
- **Worktree cô lập**: `D:\nlp_rf_gate\wt_thonxom_B`
- **Branch**: `agy/thon-xom-b-20261031`
- **Base commit**: `63a1f212f2d103eb0d9b7705555419f92744585d`
- **File test mới tạo**: `tests/test_thon_xom_boundary.py`
- **SHA-256 test file**: `1958CD23B7B4BE7E9BB390AFCCCBF448572742BE093A5E851C654209FC1D50C7`

---

## 1. Phương Pháp & Kiến Trúc Kiểm Thử

Kiểm thử được thiết kế hoàn toàn độc lập với cách cài đặt helper nội bộ của phiên sửa mã nguồn, tuân thủ các nguyên tắc:
1. **Kiểm tra trực tiếp qua API chuẩn `NguCanhCRF.tach(set())`**: Không mock helper nội bộ, không nạp mô hình nặng, không yêu cầu GPU hay thư viện `pycrfsuite`.
2. **Tokenizer thực tế**: Sử dụng trực tiếp `src.tien_xu_ly.tach_token` để chia token; ánh xạ BIO labels dựa trên số lượng và chỉ số token thực tế (`len(labels) == len(tokens)`).
3. **Xác minh runtime module**: Kiểm tra `NguCanhCRF.__module__ == 'src.tien_xu_ly.crf_chi_tiet'` nhằm bảo đảm wrapper `src.crf_chi_tiet` chuyển tiếp chính xác đến runtime thực tế.
4. **Hai kịch bản cốt lõi (Fixtures)**:
   - *CRF span gán quá dài*: Nhãn `B-thon_xom` và `I-thon_xom` bao trùm toàn bộ chuỗi chứa cả phần địa giới hành chính xã/huyện/tỉnh.
   - *Fallback all-O*: Tất cả nhãn là `'O'`, kích hoạt cơ chế nhận diện từ khóa bổ sung của bộ tách.
5. **Kỷ luật kỹ thuật & Đánh giá thực chất**: Không làm assertion lỏng lẻo để che giấu lỗi; giữ nguyên các ca kiểm thử phản ánh đúng hành vi ngữ nghĩa mong đợi theo đặc tả.

---

## 2. Lệnh Chạy Kiểm Thử

```powershell
Set-Location D:\nlp_rf_gate\wt_thonxom_B
py -3.12 -X utf8 -B -m unittest discover -s tests -p test_thon_xom_boundary.py -v
```

---

## 3. Tổng Hợp Kết Quả Kiểm Thử Trên Patch Ban Đầu

- **Tổng số ca kiểm thử**: 15 tests (trong đó có 4 subtests cho dấu phân cách).
- **Ca đạt cơ học (Pass)**: 6 tests (các ca bảo vệ chống hồi quy và xác minh harness).
- **Ca phát hiện lỗi (Fail - Tái hiện lỗi thực tế của patch ban đầu)**: 9 tests (12 lượt thất bại tính cả subtests).
- **Lỗi Test Harness**: 0 (toàn bộ assertions và fixtures thực thi hợp lệ, không có lỗi cú pháp hay schema).

```
test_00_xac_minh_module_runtime ... ok
test_01_crf_span_bao_trum_xom_5 ... FAIL
test_02_fallback_all_o_xom_5 ... FAIL
test_03_thon_3_xa_hoang_loc ... FAIL
test_04_thon_dong_xa_nam_hong ... FAIL
test_05_xom_khe_cat_xa_lam_dien ... FAIL
test_06_thon_phuong_nam_khong_cat_nham ... ok
test_07_xom_duong_moi_khong_coi_duong_la_tien_to_hanh_chinh ... ok
test_08_khom_cau_den ... FAIL
test_09a_viet_tat_chuoi_thu_bac_x_h_t ... FAIL
test_09b_viet_tat_chuoi_thu_bac_p_q_tp ... FAIL
test_09c_viet_tat_khong_du_bang_chung_thu_bac_ambiguity_abstain ... ok
test_10a_dau_ngat_gach_ngang_va_cham_dung_rieng (separator='-') ... FAIL
test_10a_dau_ngat_gach_ngang_va_cham_dung_rieng (separator='–') ... FAIL
test_10a_dau_ngat_gach_ngang_va_cham_dung_rieng (separator='—') ... FAIL
test_10a_dau_ngat_gach_ngang_va_cham_dung_rieng (separator='.') ... FAIL
test_10b_dau_cham_viet_tat_khong_bi_tach_sai ... ok
test_11_khong_tac_dong_ngoai_thon_xom ... ok
```

---

## 4. Chi Tiết Từng Ca Kiểm Thử

| Mã Test | Tên Test / Mục Tiêu | Dữ Liệu Đầu Vào | Kỳ Vọng Đặc Tả | Kết Quả Trên Patch Claude | Trạng Thái |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **00** | Xác minh runtime module wrapper | Import qua `src.crf_chi_tiet` | `module == 'src.tien_xu_ly.crf_chi_tiet'` | Đúng module runtime | **ĐẠT** |
| **01** | CRF span thon_xom bao trùm toàn bộ chuỗi | `xóm 5 xã mỹ hưng huyện mỹ lộc tỉnh nam định` (nhãn `B-thon_xom`, `I-thon_xom` toàn chuỗi) | `thon_xom: "Xóm 5"`, span `[0, 2]` | `thon_xom: "Xóm 5 Xã Mỹ Hưng Huyện Mỹ Lộc Tỉnh Nam Định"` (span `[0, 11]`) | **FAIL (Lỗi patch)** |
| **02** | Fallback all-O cùng địa chỉ | `xóm 5 xã mỹ hưng huyện mỹ lộc tỉnh nam định` (nhãn `'O'` toàn chuỗi) | `thon_xom: "Xóm 5"`, span `[0, 2]` | `thon_xom: "Xóm 5 Xã Mỹ Hưng Huyện Mỹ Lộc Tỉnh Nam Định"` (span `[0, 11]`) | **FAIL (Lỗi patch)** |
| **03** | Ranh giới xã Hoằng Lộc (CRF + Fallback) | `Thôn 3 xã Hoằng Lộc huyện Hoằng Hóa tỉnh Thanh Hóa` | `thon_xom: "Thôn 3"` | `thon_xom: "Thôn 3 Xã Hoằng Lộc Huyện Hoằng Hóa Tỉnh Thanh Hóa"` | **FAIL (Lỗi patch)** |
| **04** | Tên thôn một từ chữ cái (CRF + Fallback) | `Thôn Đông xã Nam Hồng huyện Tiền Hải Thái Bình` | `thon_xom: "Thôn Đông"` | `thon_xom: "Thôn Đông Xã Nam Hồng Huyện Tiền Hải Thái Bình"` | **FAIL (Lỗi patch)** |
| **05** | Tên thôn nhiều từ (Khe Cát) | `Xóm Khe Cát Xã Lam Điền` | `thon_xom: "Xóm Khe Cát"`, span `[0, 3]` | `thon_xom: "Xóm Khe Cát Xã Lam Điền"`, span `[0, 6]` | **FAIL (Lỗi patch)** |
| **06** | Không cắt nhầm chữ Phương/Phuong | `Thôn Phương Nam` và `Thon Phuong Nam` | `thon_xom: "Thôn Phương Nam"` / `"Thôn Phuong Nam"` | Giữ nguyên đủ tên thôn | **ĐẠT** |
| **07** | Không coi 'Đường' trong 'Đường Mới' là tiền tố hành chính/đường | `Xóm Đường Mới` | `thon_xom: "Xóm Đường Mới"`, `duong: ""` | `thon_xom: "Xóm Đường Mới"`, `duong: ""` | **ĐẠT** |
| **08** | Tiền tố Khóm (đơn lẻ & kèm cấp hành chính) | `Khóm Cầu Đen Phường 1 Thị xã Giá Rai` | `thon_xom: "Khóm Cầu Đen"`, span `[0, 3]` | `thon_xom: "Khóm Cầu Đen Phường 1 Thị Xã Giá Rai"` (span `[0, 9]`) | **FAIL (Lỗi patch)** |
| **09a**| Viết tắt chuỗi thứ bậc X., H., T. | `Xóm 1 X. Mỹ Hưng H. Mỹ Lộc T. Nam Định` | `thon_xom: "Xóm 1"`, span `[0, 2]` | `thon_xom: "Xóm 1 X. Mỹ Hưng H. Mỹ Lộc T. Nam Định"` | **FAIL (Lỗi patch)** |
| **09b**| Viết tắt chuỗi thứ bậc P., Q., TP. | `Khóm 2 P. 1 Q. Ninh Kiều TP. Cần Thơ` | `thon_xom: "Khóm 2"`, span `[0, 2]` | `thon_xom: "Khóm 2 P. 1 Q. Ninh Kiều Tp. Cần Thơ"` | **FAIL (Lỗi patch)** |
| **09c**| Ambiguity: Viết tắt không đủ bằng chứng thứ bậc | `Thôn X. Văn` (CRF span toàn chuỗi) | `thon_xom: "Thôn X. Văn"` (kiềm chế/abstain, không cắt nhầm) | Giữ nguyên `"Thôn X. Văn"` | **ĐẠT** |
| **10a**| Dấu phân cách `-`, `–`, `—`, `.` | `Thôn 1 [sep] Xã Nam Hồng` với `sep` $\in \{-, –, —, .\}$ | `thon_xom: "Thôn 1"` | Nuốt cả dấu và phần sau dấu (ví dụ: `"Thôn 1 - Xã Nam Hồng"`) | **FAIL (Lỗi patch)** |
| **10b**| Dấu chấm đi liền chữ viết tắt (X.) | `Xóm 1 X. Nam Hồng` | Tokenizer tách đúng `['Xóm', '1', 'X', '.']` | Tokenizer tách đúng | **ĐẠT** |
| **11** | Kiểm tra độc lập ngoài trường thon_xom | `Đường Giải Phóng Xã Nam Hồng` và `Ngõ 10 Phố Huế` | Trường `duong`, `ngo_ngach_hem` nhận đúng, không bị ảnh hưởng | Các trường khác hoạt động chính xác | **ĐẠT** |

---

## 5. Phân Tích Nguyên Nhân Kỹ Thuật Các Ca Thất Bại

Các ca thất bại ở trên hoàn toàn do khiếm khuyết trong patch sửa ban đầu của Claude tại `src/tien_xu_ly/crf_chi_tiet.py`, cụ thể:

1. **Khiếm khuyết chỉ mở rộng (Expand-only) trong xử lý CRF span**:
   - Trong `src/tien_xu_ly/crf_chi_tiet.py`, mã hiện tại viết:
     ```python
     if end_idx > b:
         b = end_idx
     ```
   - Khi CRF span dự đoán bao trùm toàn bộ chuỗi địa chỉ (tức `b = len(tokens)`), `end_idx` dừng tại tiền tố hành chính ("xã", index 2) luôn nhỏ hơn `b` ($2 < 11$). Do đó điều kiện `end_idx > b` không bao giờ thỏa mãn, dẫn tới `b` **không bao giờ được thu ngắn** lại ranh giới thực sự.

2. **Khiếm khuyết bỏ quên vòng lặp Fallback all-O**:
   - Vòng lặp quét `unknown_candidates` (dòng 246-247) chỉ dừng lại khi gặp `DAU_NGAT_CHI_TIET`:
     ```python
     while j < len(self.tokens) and j not in used and self.tokens[j] not in DAU_NGAT_CHI_TIET:
         j += 1
     ```
   - Vòng lặp này hoàn toàn **không kiểm tra** tiền tố hành chính hay mốc ngắt nào khác, khiến toàn bộ câu không có dấu phẩy bị gom hết vào trường thôn xóm.

3. **Thiếu tiền tố `"Khóm"` trong danh mục tiền tố thôn xóm**:
   - Biến `TIEN_TO_THON_XOM` tại `src/tien_xu_ly/quy_tac.py` chỉ định nghĩa `('Thôn', 'Ấp', 'Xóm', 'Bản', 'Buôn')`, thiếu `"Khóm"`. Do đó, điều kiện `marker[1][1] in TIEN_TO_THON_XOM` trả về `False` đối với tiền tố Khóm.

4. **Loại trừ quá mức tiền tố viết tắt 1 chữ cái**:
   - Biến `TIEN_TO_HANH_CHINH_DAI` cố tình loại bỏ các ký tự đơn `('t', 'h', 'x', 'p', 'q')`. Hệ quả là khi gặp chuỗi viết tắt có thứ bậc chuẩn như `X.`, `H.`, `T.` hay `P.`, `Q.`, thuật toán coi như không có tiền tố hành chính và không ngắt ranh giới.

5. **Thiếu tập ký tự phân cách ranh giới**:
   - Tập `DAU_NGAT_CHI_TIET` hiện chỉ có `{',', ';'}`. Các dấu gạch ngang (`-`, `–`, `—`) và dấu chấm đứng riêng (`.`) không được xử lý như ranh giới phân tách.

---

## 6. Tuân Thủ Kỷ Luật Kỹ Thuật

- **Không sửa file source**: Toàn bộ mã nguồn trong `src/` và `tests/test_loi_goc_log.py` được giữ nguyên vẹn 100%.
- **Không tự ý commit**: Không tạo commit mới trong git tree.
- **Minh bạch lỗi**: Báo cáo phản ánh trung thực kết quả chạy độc lập của bộ test, phân biệt rạch ròi giữa tính đúng đắn của bộ khung kiểm thử và các lỗi ngữ nghĩa của mã nguồn cần khắc phục ở phiên làm việc kế tiếp.
