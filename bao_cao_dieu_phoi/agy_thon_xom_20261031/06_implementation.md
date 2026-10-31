# Báo cáo Triển khai: Sửa Logic Biên Thôn/Xóm Trong CRF (2026-10-31)

- **Worktree:** `D:\nlp_rf_gate\wt_thonxom_A`
- **Branch:** `agy/thon-xom-a-20261031`
- **Base commit:** `63a1f212f2d103eb0d9b7705555419f92744585d`
- **File sửa đổi duy nhất:** `src/tien_xu_ly/crf_chi_tiet.py`

---

## 1. Helper và Thuật toán Xác định Ranh giới Thôn/Xóm

Để giải quyết triệt để và thống nhất ba lỗi biên thôn/xóm mà không nhân bản logic, một helper nội bộ duy nhất `tim_bien_thon_xom(tokens, start, used, other_starts=None)` cùng hai hàm phụ trợ `_tim_marker_hanh_chinh` và `_co_bang_chung_ngu_canh` đã được thêm vào `src/tien_xu_ly/crf_chi_tiet.py`.

### Thuật toán xác định ranh giới:
1. **Điểm bắt đầu (`start`):** Vị trí ngay sau tiền tố thôn/xóm đã nhận diện (ví dụ ngay sau `xóm`, `thôn`, `khóm`).
2. **Quét tuần tự từng token từ `idx = start` đến cuối chuỗi:**
   - **Token đã chiếm dụng (`used`):** Dừng ngay lập tức nếu `idx in used`.
   - **Đầu span chi tiết khác (`other_starts`):** Chỉ dừng nếu `idx in other_starts` VÀ token tại `idx` thực sự khớp tiền tố chi tiết trong `CHI_TIET`. Điều này ngăn chặn việc nhầm lẫn các tên riêng như `Phương Nam` (bị mô hình neural dự đoán nhầm nhãn nhưng không có tiền tố đường) thành điểm ngắt.
   - **Dấu ngắt phân đoạn:**
     - Dấu câu cơ bản: `,`, `;`, `-`, `–`, `—`, `−`.
     - Dấu chấm `.` đứng riêng: Được coi là dấu ngắt trừ trường hợp là dấu chấm viết tắt tên người/tên riêng (ví dụ `P. Nam` có token trước đó độ dài $\le 2$ chữ cái và token sau là chữ/số).
   - **Tiền tố hành chính:**
     - Nhận diện marker hành chính tại `idx` và phân loại cấp: Cấp 1 (Tỉnh / TP trực thuộc TW), Cấp 2 (Quận / Huyện / Thị xã), Cấp 3 (Xã / Phường / Thị trấn).
     - **Marker mạnh (unambiguous):** Các tiền tố từ ghép (`thành phố`, `thị xã`, `thị trấn`, `đặc khu`), viết tắt 2 chữ cái (`tp`, `tx`, `tt`), tiếng Anh (`district`, `ward`, `city`, `province`), hoặc từ đơn có dấu thanh tiếng Việt chuẩn (`xã`, `phường`, `huyện`, `quận`, `tỉnh`) / Telex tường minh (`xax`, `phuowngf`, `huyenj`...). Các marker này được công nhận là điểm ngắt ngay lập tức mà không cần ngữ cảnh phụ.
     - **Marker yếu / mơ hồ:** Các viết tắt một chữ cái (`X.`, `P.`, `Q.`, `H.`, `T.`) hoặc từ không dấu (`xa`, `phuong`, `quan`, `huyen`, `tinh`). Chỉ được công nhận là điểm ngắt khi có bằng chứng xác nhận ngữ cảnh: hoặc có token nằm trong `used`, hoặc chuỗi hành chính kế tiếp tuân thủ thứ bậc hợp lệ (xem mục 4).
3. **Cắt tỉa ký tự không phải chữ/số ở đuôi:** Sau khi xác định `end_idx`, lùi bỏ các ký tự dấu câu không hợp lệ ở cuối span thôn/xóm.

---

## 2. Cách Xử lý CRF Span Quá Dài (Lỗi 1)

### Cơ chế lỗi cũ:
Trong `NguCanhCRF.tach`, logic cũ duyệt tìm `end_idx` nhưng chỉ cập nhật biên khi `end_idx > b`. Khi nhãn BIO từ mô hình CRF/CNN bao trùm quá dài (ví dụ gán liên tục qua cả xã/huyện/tỉnh thành `thon_xom`), `b` ban đầu lớn hơn `end_idx`, dẫn đến điều kiện sai và span giữ nguyên độ dài nuốt toàn bộ phần hành chính.

### Cơ chế khắc phục:
```python
if proper_field == 'thon_xom' and marker[1][1] in TIEN_TO_THON_XOM_DAY_DU:
    end_idx = tim_bien_thon_xom(self.tokens, marker[0], used, other_starts)
    while end_idx > a and not any(c.isalnum() for c in self.tokens[end_idx - 1]):
        end_idx -= 1
    if end_idx > a:
        b = end_idx
```
- Khi `end_idx` được tìm thấy, nếu `end_idx > a`, gán thẳng `b = end_idx`.
- Xử lý đồng thời cả hai chiều:
  - **Mở rộng (expansion):** Nếu span ban đầu chỉ có `Xóm` (`b = 1`), `end_idx` nới đến trước dấu phẩy/hành chính (`b = 3` -> `Xóm Khe Cát`).
  - **Thu ngắn (contraction):** Nếu span ban đầu nuốt hết câu (`b = 11`), `end_idx` dừng trước `xã` (`b = 2` -> `Xóm 5`), giải phóng các token hành chính phía sau cho các bước phân giải tiếp theo.

---

## 3. Cách Xử lý Fallback `unknown_candidates` (Lỗi 2)

### Cơ chế lỗi cũ:
Vòng lặp `unknown_candidates` khi gặp tiền tố chi tiết chỉ dừng khi gặp `DAU_NGAT_CHI_TIET` (`,` hoặc `;`) hoặc `used`. Nếu địa chỉ không có dấu phẩy (như `xóm 5 xã mỹ hưng...`), fallback nuốt trọn cả câu vào `thon_xom`.

### Cơ chế khắc phục:
Tích hợp trực tiếp helper `tim_bien_thon_xom` vào nhánh fallback dành riêng cho `thon_xom`:
```python
if f == 'thon_xom' and label in TIEN_TO_THON_XOM_DAY_DU:
    j = tim_bien_thon_xom(self.tokens, end, used, set())
    while j > i and not any(c.isalnum() for c in self.tokens[j - 1]):
        j -= 1
else:
    j = end
    while j < len(self.tokens) and j not in used and self.tokens[j] not in DAU_NGAT_CHI_TIET:
        j += 1
```
- Chỉ thay đổi cách tính biên `j` cho trường `thon_xom` với các nhãn hợp lệ.
- Nhánh `else` cho `duong`, `so_nha`, `ngo_ngach_hem` được bảo toàn nguyên vẹn, không làm thay đổi ngữ nghĩa hay quy tắc fallback của các trường khác.

---

## 4. Quy Tắc Nhận Diện Viết Tắt Hành Chính Một Chữ Cái (Lỗi 3)

### Quy tắc kỹ thuật:
1. **Yêu cầu dấu chấm bắt buộc:** Tiền tố một chữ cái `x`, `p`, `q`, `h`, `t` (không phân biệt hoa thường) bắt buộc phải đi kèm dấu chấm `.` ngay sau đó và theo sau là một token tên (chữ hoặc số). Các chữ cái trần đứng một mình tuyệt đối không được coi là tiền tố hành chính để tránh cắt nhầm tên riêng.
2. **Xác thực thứ bậc hành chính kế tiếp (`_co_bang_chung_ngu_canh`):**
   - Viết tắt cấp 3 (`X.`, `P.`): Chỉ được coi là ranh giới khi phía sau xuất hiện một đơn vị hành chính cấp 2 (`H.`, `Q.`, `huyện`, `quận`...) hoặc cấp 1 (`T.`, `tỉnh`, `TP.`...).
   - Viết tắt cấp 2 (`Q.`, `H.`): Chỉ được coi là ranh giới khi phía sau có đơn vị hành chính cấp 1 (`T.`, `tỉnh`, `TP.`...).
   - Nếu gặp đơn vị cùng cấp hoặc cấp thấp hơn ngay phía sau (ví dụ `phuong` rồi đến `xa`), chuỗi vi phạm phân cấp hành chính chuẩn của Việt Nam, chứng tỏ từ phía trước là tên riêng (ví dụ `Thon Phuong Nam xa My Hung`), helper sẽ từ chối marker giả này và tiếp tục quét.
   - Nhờ đó, trường hợp như `Thôn P. Nam` không có đơn vị cấp cao hơn đi kèm sẽ không bị cắt nhầm.

---

## 5. Xử Lý Nhãn "Khóm"

- Trong `src/tien_xu_ly/quy_tac.py`, bảng `CHI_TIET` đã có định nghĩa `("khom", "thon_xom", "Khóm")`, nhưng bộ hằng số `TIEN_TO_THON_XOM` chỉ gồm 5 mục (`Thôn`, `Ấp`, `Xóm`, `Bản`, `Buôn`).
- Giải pháp ít xâm lấn nhất: Không sửa file `quy_tac.py` dùng chung; định nghĩa tập mở rộng ngay trong `src/tien_xu_ly/crf_chi_tiet.py`:
  ```python
  TIEN_TO_THON_XOM_DAY_DU = frozenset(TIEN_TO_THON_XOM) | {'Khóm'}
  ```
- Áp dụng `TIEN_TO_THON_XOM_DAY_DU` tại cả hai nhánh kiểm tra marker của CRF span và fallback `unknown_candidates`, đảm bảo các địa chỉ như `Khóm Cầu Đen` được nhận diện đồng nhất kể cả khi không có dấu phẩy ngăn cách.

---

## 6. Git Diff Chi Tiết (`src/tien_xu_ly/crf_chi_tiet.py`)

```diff
diff --git a/src/tien_xu_ly/crf_chi_tiet.py b/src/tien_xu_ly/crf_chi_tiet.py
index 86556b2..d093fe7 100644
--- a/src/tien_xu_ly/crf_chi_tiet.py
+++ b/src/tien_xu_ly/crf_chi_tiet.py
@@ -8,6 +8,7 @@ from pathlib import Path
 from .tien_xu_ly import bo_dau
 from .quy_tac import (
     CHI_TIET,
+    HANH_CHINH,
     CHU_CAI_LOAI_TRU_SO_NHA,
     DAU_NGAT_CHI_TIET,
     DAU_NGAT_SO_NHA,
@@ -28,9 +29,95 @@ from .quy_tac import (
     khop_tien_to,
 )
 from .tach_phan_con import FIELDS, viet_ten
+
+# Tiền tố hành chính từ 2 chữ cái trở lên (bỏ 't', 'h', 'x', 'p', 'q' để không cắt nhầm tên thôn một chữ cái).
+TIEN_TO_HANH_CHINH_DAI = [r for r in HANH_CHINH if len(r[0].replace(' ', '')) >= 2]
+TIEN_TO_THON_XOM_DAY_DU = frozenset(TIEN_TO_THON_XOM) | {'Khóm'}
+DAU_NGAT_CO_BAN = {',', ';', '-', '–', '—', '−'}
 from .dinh_dang import tien_to_hien_thi, dinh_dang_span
 
 
+def _tim_marker_hanh_chinh(tokens, k):
+    """Xác định marker hành chính tại vị trí k:
+    Trả về (end_k, cấp_hành_chính, là_marker_mạnh) hoặc None.
+    Cấp hành chính: 1 (Tỉnh/TP), 2 (Quận/Huyện/Thị xã), 3 (Xã/Phường/Thị trấn).
+    """
+    tok = tokens[k].casefold()
+    if tok in ('x', 'p', 'q', 'h', 't') and k + 1 < len(tokens) and tokens[k + 1] == '.' and k + 2 < len(tokens) and any(c.isalnum() for c in tokens[k + 2]):
+        lvl = 3 if tok in ('x', 'p') else (2 if tok in ('q', 'h') else 1)
+        return k + 2, lvl, False
+
+    m = khop_tien_to(tokens, k, TIEN_TO_HANH_CHINH_DAI)
+    if m:
+        end_k, attrs = m
+        key = attrs[0]
+        if attrs[1] == 'thanh pho' or 'thanh pho' in key or 'tinh' in key:
+            lvl = 1
+        elif 'huyen' in key:
+            lvl = 2
+        elif 'xa' in key:
+            lvl = 3
+        else:
+            lvl = 2
+
+        raw_first = tokens[k].casefold()
+        words = tokens[k:end_k]
+        if len(words) >= 2 or raw_first in ('tp', 'tx', 'tt', 'city', 'province', 'district', 'ward'):
+            return end_k, lvl, True
+        if raw_first in ('xã', 'phường', 'huyện', 'quận', 'tỉnh', 'thị'):
+            return end_k, lvl, True
+        if raw_first in ('xax', 'phuowngf', 'phuongf', 'huyenj', 'quanj', 'tinhr'):
+            return end_k, lvl, True
+        return end_k, lvl, False
+    return None
+
+
+def _co_bang_chung_ngu_canh(tokens, start_k, cur_lvl, used):
+    """Kiểm tra có bằng chứng xác nhận cấp hành chính tiếp theo hoặc token đã used."""
+    k = start_k
+    while k < len(tokens):
+        if k in used:
+            return True
+        m = _tim_marker_hanh_chinh(tokens, k)
+        if m:
+            next_end, next_lvl, _ = m
+            if next_lvl >= cur_lvl:
+                return False
+            return True
+        k += 1
+    return False
+
+
+def tim_bien_thon_xom(tokens, start, used, other_starts=None):
+    """Helper nội bộ dùng chung xác định biên kết thúc thôn/xóm cho cả CRF và fallback."""
+    valid_other_starts = {idx for idx in other_starts if khop_tien_to(tokens, idx, CHI_TIET)} if other_starts else set()
+    idx = start
+    while idx < len(tokens):
+        if idx in used or idx in valid_other_starts:
+            break
+        tok = tokens[idx]
+        if tok in DAU_NGAT_CO_BAN:
+            break
+        if tok == '.':
+            if idx > start and idx + 1 < len(tokens):
+                prev = tokens[idx - 1]
+                nxt = tokens[idx + 1]
+                if len(prev) <= 2 and prev.isalpha() and any(c.isalnum() for c in nxt):
+                    idx += 1
+                    continue
+            break
+        m = _tim_marker_hanh_chinh(tokens, idx)
+        if m:
+            end_k, lvl, is_strong = m
+            if is_strong:
+                break
+            if any(p in used for p in range(idx, min(end_k + 2, len(tokens)))):
+                break
+            if _co_bang_chung_ngu_canh(tokens, end_k, lvl, used):
+                break
+        idx += 1
+    return idx
+
+
 def dac_trung(tokens):
     """Đặc trưng quan sát toàn chuỗi, không dùng nhãn/mã/mốc tham chiếu."""
     markers = cac_tien_to(tokens)
@@ -181,6 +268,7 @@ class NguCanhCRF:
         values = {f: [] for f in FIELDS}
         output_spans, used = [], set(occupied)
         inferred = False
+        other_starts = {span_a for sf, span_a, _ in spans if sf != 'thon_xom'}
         for f, a, b in spans:
             # Dấu câu ngoài đoạn không thành tên; phần giữa đoạn vẫn giữ.
             while a < b and not any(c.isalnum() for c in self.tokens[a]):
@@ -198,13 +286,11 @@ class NguCanhCRF:
                 proper_field = marker[1][0]
                 if proper_field in FIELDS:
                     f = proper_field
-                    if proper_field == 'thon_xom' and marker[1][1] in TIEN_TO_THON_XOM:
-                        end_idx = marker[0]
-                        while end_idx < len(self.tokens) and self.tokens[end_idx] not in DAU_NGAT_CHI_TIET:
-                            if khop_tien_to(self.tokens, end_idx, CHI_TIET):
-                                break
-                            end_idx += 1
-                        if end_idx > b:
+                    if proper_field == 'thon_xom' and marker[1][1] in TIEN_TO_THON_XOM_DAY_DU:
+                        end_idx = tim_bien_thon_xom(self.tokens, marker[0], used, other_starts)
+                        while end_idx > a and not any(c.isalnum() for c in self.tokens[end_idx - 1]):
+                            end_idx -= 1
+                        if end_idx > a:
                             b = end_idx
             # Áp dụng lại khối luật sau khi tiền tố có thể đổi f hoặc b (lần 2)
             hop_le, b = loc_va_chinh_bien_span(self.tokens, f, a, b)
@@ -234,9 +320,14 @@ class NguCanhCRF:
                 end, (f, label) = marker
                 if f == 'duong' and la_duong_thanh_pho(self.tokens, i):
                     continue
-                j = end
-                while j < len(self.tokens) and j not in used and self.tokens[j] not in DAU_NGAT_CHI_TIET:
-                    j += 1
+                if f == 'thon_xom' and label in TIEN_TO_THON_XOM_DAY_DU:
+                    j = tim_bien_thon_xom(self.tokens, end, used, set())
+                    while j > i and not any(c.isalnum() for c in self.tokens[j - 1]):
+                        j -= 1
+                else:
+                    j = end
+                    while j < len(self.tokens) and j not in used and self.tokens[j] not in DAU_NGAT_CHI_TIET:
+                        j += 1
                 if j > i:
                     val, g = dinh_dang_span(self.tokens[i:j], f, tien_to_mac_dinh=tien_to_mac_dinh,
                                             tien_to_so_nha=tien_to_so_nha, tien_to_duong=tien_to_duong)
```

---

## 7. Lệnh và Kết Quả Kiểm Chứng Thực Tế

### 7.1. Kiểm thử biên dịch cú pháp
```powershell
& "D:\nlp_chuan_hoa_dia_chi\.venv-neural\Scripts\python.exe" -m py_compile "D:\nlp_rf_gate\wt_thonxom_A\src\tien_xu_ly\crf_chi_tiet.py"
```
- **Exit code:** 0 (không có lỗi cú pháp).

### 7.2. Bộ hồi quy hẹp `test_loi_goc_log` và `test_crf`
```powershell
& "D:\nlp_chuan_hoa_dia_chi\.venv-neural\Scripts\python.exe" -m unittest -v tests.test_loi_goc_log tests.test_crf
```
- **Kết quả:** Ran 17 tests in 7.287s — `OK`.
- Toàn bộ 9 test trong `test_loi_goc_log` và 8 test hợp đồng trong `test_crf` đều chạy thực chất và đạt kết quả mong muốn.

### 7.3. Kiểm chứng các ví dụ bắt buộc qua toàn bộ Pipeline (`BoChuanHoa`)
```powershell
& "D:\nlp_chuan_hoa_dia_chi\.venv-neural\Scripts\python.exe" -c "<script kiểm tra pipeline>"
```
**Output thực tế:**
```text
[OK] xóm 5 xã mỹ hưng huyện mỹ lộc tỉnh nam định          -> thon_xom: 'Xóm 5' (expected 'Xóm 5')
[OK] thôn 3 xã hoằng lộc huyện hoằng hóa tỉnh thanh hóa   -> thon_xom: 'Thôn 3' (expected 'Thôn 3')
[OK] thôn đông xã nam hồng huyện tiền hải thái bình       -> thon_xom: 'Thôn Đông' (expected 'Thôn Đông')
[OK] Xóm Khe Cát, Xã Lam Điền, Chương Mỹ, Hà Nội          -> thon_xom: 'Xóm Khe Cát' (expected 'Xóm Khe Cát')
[OK] x5, Mỹ Hưng, Mỹ Lộc, Nam Định                        -> thon_xom: 'Xóm 5' (expected 'Xóm 5')
[OK] Thôn Phương Nam, Xã Lam Điền, Chương Mỹ, Hà Nội      -> thon_xom: 'Thôn Phương Nam' (expected 'Thôn Phương Nam')
[OK] Xóm Đường Mới, Xã Lam Điền, Chương Mỹ, Hà Nội        -> thon_xom: 'Xóm Đường Mới' (expected 'Xóm Đường Mới')
[OK] Khóm Cầu Đen, Xã Lam Điền, Chương Mỹ, Hà Nội         -> thon_xom: 'Khóm Cầu Đen' (expected 'Khóm Cầu Đen')
[OK] Khóm Cầu Đen Xã Lam Điền Chương Mỹ Hà Nội            -> thon_xom: 'Khóm Cầu Đen' (expected 'Khóm Cầu Đen')
[OK] xóm 5 x. mỹ hưng h. mỹ lộc t. nam định               -> thon_xom: 'Xóm 5' (expected 'Xóm 5')
[OK] xóm 5 q. ninh kiều tp. cần thơ                       -> thon_xom: 'Xóm 5' (expected 'Xóm 5')
```

### 7.4. Kiểm chứng mô phỏng độc lập trên `NguCanhCRF` (CRF span quá dài và Fallback all O)
- **Span gán BIO quá dài (cố ý gán `B-thon_xom` / `I-thon_xom` toàn chuỗi):** Đã thu ngắn chuẩn xác về đúng ranh giới thôn/xóm cho tất cả các câu mẫu.
- **Nhánh fallback (toàn bộ nhãn `O`):** Đã mở rộng dừng đúng trước marker hành chính cho tất cả các câu mẫu.
- **Bảo vệ tên riêng:**
  - `Thôn Phương Nam` và `Thon Phuong Nam xa My Hung huyen My Loc`: Giữ trọn vẹn `Thôn Phương Nam` / `Thôn Phuong Nam`.
  - `Xóm Đường Mới`: Giữ trọn vẹn `Xóm Đường Mới`.
  - `Thôn P. Nam`: Giữ nguyên dạng viết tắt tên riêng trong thôn, không bị cắt nhầm tại `P.`.

---

## 8. Rủi Ro Kỹ Thuật Còn Lại và Giới Hạn

1. **Địa chỉ viết tắt một chữ cái đơn độc không có ngữ cảnh:**
   - Nếu địa chỉ chỉ có dạng `xóm 5 x. mỹ hưng` mà không có huyện/tỉnh theo sau và token `mỹ hưng` chưa được nhận diện trong `used` (ví dụ ở lượt phân giải độc lập ban đầu), quy tắc an toàn sẽ không mạo hiểm coi `x.` là ranh giới vì `x.` có thể trùng tên riêng (như `Xuân`). Trong pipeline tích hợp, bước tìm ứng viên hành chính sẽ đưa `mỹ hưng` vào `used`, từ đó ranh giới được kích hoạt chính xác.
2. **Từ không dấu trùng tên riêng và tiền tố:**
   - Dạng không dấu như `Thon Phuong ...` nếu chỉ đứng một mình và không có bất kỳ đơn vị hành chính nào theo sau thì sự mơ hồ là nội tại. Thuật toán chọn phương án bảo toàn tên thôn (`Thon Phuong`) thay vì cắt cụt.
3. **Phạm vi kiểm thử:**
   - Đã tuân thủ nghiêm ngặt giới hạn thời gian và quy tắc kiểm thử: chỉ thực thi kiểm thử hẹp và hợp đồng liên quan trong worktree cô lập `D:\nlp_rf_gate\wt_thonxom_A`. Không chạy toàn bộ test suite, không huấn luyện lại mô hình, không can thiệp vào các worktree khác.
