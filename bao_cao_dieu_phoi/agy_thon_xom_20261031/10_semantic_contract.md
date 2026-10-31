# Báo Cáo Kiểm Toán Hợp Đồng Ngữ Nghĩa Ranh Giới Thôn/Xóm (Nhiệm Vụ E)

- **Dự án gốc**: `D:\nlp_rf_E`
- **Worktree kiểm toán (Chỉ đọc)**: `D:\nlp_rf_gate\wt_thonxom_E`
- **Nhánh**: `agy/thon-xom-e-20261031` (commit `63a1f21`)
- **Tài liệu & mã nguồn đối chiếu**: `bai_toan.md`, `src/tien_xu_ly/quy_tac.py`, `src/tien_xu_ly/tach_phan_con.py`, `src/tien_xu_ly/dinh_dang.py`, `src/tien_xu_ly/tien_xu_ly.py`, `tests/test_telex_tien_to.py` (và liên đới `src/tien_xu_ly/crf_chi_tiet.py`).
- **Nguyên tắc kiểm toán**: Đánh giá thực chất, đối chiếu mã nguồn tĩnh, phân loại rõ ràng (Rõ / Nguy cơ / Mơ hồ), không tuyên bố hoàn thành sớm khi chưa đủ bằng chứng định lượng.

---

## 1. Quy ước định dạng và phân chia thon_xom với xã/huyện/tỉnh và với tên đường

### 1.1. Căn cứ đặc tả và mã nguồn
- **Đặc tả bài toán** (`bai_toan.md:31-41`, `bai_toan.md:52`):
  - `thon_xom`: Thôn, xóm, ấp, bản, tổ dân phố, khu phố.
  - `duong`: Tên đường, phố.
  - `xa_phuong`, `tinh`: Cấp hành chính chính thức sau sáp nhập (1/7/2025). Cấp huyện chỉ dùng làm căn cứ xác định ngữ cảnh, không xuất ra đầu ra (`bai_toan.md:46`).
  - Phần chi tiết (`thon_xom`, `duong`, `so_nha`, `ngo_ngach_hem`) không đổi theo địa giới sáp nhập, chỉ chuẩn hóa hình thức và viết hoa đúng (`bai_toan.md:52`).
- **Từ điển tiền tố quy tắc** (`src/tien_xu_ly/quy_tac.py:8-64`):
  - `HANH_CHINH` (`quy_tac.py:8-22`): Đăng ký tiền tố cấp hành chính (`thanh pho`, `thi xa`, `thi tran`, `dac khu`, `tinh`, `tp`, `huyen`, `quan`, `phuong`, `xa`, v.v.).
  - `CHI_TIET` (`quy_tac.py:38-64`): Đăng ký tiền tố chi tiết gồm `thon_xom` (`thon`, `thoon`, `xom`, `ap`, `ban`, `khu pho`, `kp`, `to dan pho`, `tdp`, `to`, `khoi pho`, `khoi`, `khom`, `buon`, `cum`) và `duong` (`duong`, `dduong`, `pho`, `quoc lo`, `ql`, `tinh lo`, `tl`, v.v.).
- **Quy tắc biên ngắt** (`src/tien_xu_ly/tach_phan_con.py:48-67`, `crf_chi_tiet.py:201-208`):
  - `boundary(j, start, field)` (`tach_phan_con.py:48`): Ranh giới cứng là dấu ngắt `,`, `;` (`tokens[j] in {",", ";"}`).
  - Khi gặp tiền tố thuộc `HANH_CHINH`, span chi tiết buộc phải dừng (`tach_phan_con.py:57-58`).
  - `implicit_road()` (`tach_phan_con.py:69-87`): Chỉ suy diễn tên đường từ sau `so_nha` hoặc `ngo_ngach_hem`, tuyệt đối không suy diễn đường từ sau `thon_xom`.

### 1.2. Phân loại kiểm toán
- **Rõ**:
  - Biên phân tách giữa `thon_xom` và các cấp hành chính (`xa_phuong`, `huyen`, `tinh`) được bảo vệ khi có dấu phẩy hoặc khi từ tiếp theo khớp với tiền tố trong `HANH_CHINH`.
- **Nguy cơ**:
  - Địa chỉ thiếu dấu phẩy (văn bản tự do): Nếu chuỗi có dạng `Thôn 3 An Bình Thái Thụy Thái Bình`, ranh giới kết thúc của `thon_xom` hoàn toàn phụ thuộc vào việc Trie hành chính có nhận diện được `An Bình` hay không. Nếu Trie trượt, `thon_xom` có thể nuốt luôn cả tên xã.
- **Mơ hồ**:
  - Giao thoa giữa `thon_xom` và `duong`: Một số địa phương vùng nông thôn dùng tên đường gắn liền xóm (ví dụ: `Xóm 4 Đường Trục Xã`), hoặc tên thôn có chứa chữ `Đường` (ví dụ: `Thôn Đường Nhạn`). Luật ngắt hiện tại dễ gây tách nhầm thành phần.

---

## 2. Kiểu token thực tế của dấu chấm, dấu gạch ngang, tiền tố X./H./T./P./Q./TP., 'x5'

### 2.1. Phân tích tokenizer thực tế (`src/tien_xu_ly/tien_xu_ly.py`)
- **Biểu thức chính quy tách từ** (`tien_xu_ly.py:23`):
  `r"[\w\u0300-\u036f]+(?:[/\u0027\u2019\u02bc][\w\u0300-\u036f]+)*|[^\w\s]"`
  - **Dấu chấm (`.`)**: Không thuộc `\w` hay `\s`, do đó khớp `[^\w\s]` và luôn tạo thành một **token độc lập riêng biệt** `"."` với offset ký tự riêng.
  - **Dấu gạch ngang (`-`, `–`, `—`)**: Tương tự, luôn bị tách thành **token độc lập** `"-"`.
  - **Dấu gạch chéo (`/`)**: Được giữ liền trong token từ/số nếu nằm giữa 2 ký tự từ (ví dụ `12/5`), nhưng tách riêng nếu đứng rời.
- **Quy tắc tách tiền tố dính số (`glued`)** (`tien_xu_ly.py:34-37`):
  `r"(p|q|h|x|ngõ|ngách|hẻm|kiệt|ngo|ngach|hem|kiet|ng)(\d+[A-Za-z]?(?:/\d+[A-Za-z]?)*)"`
  - Chuỗi `'x5'` được nhận diện bởi nhóm `(x)(\d...)` -> Tách thành **2 token riêng biệt**: `Token('x')` và `Token('5')`.
  - Tương tự: `P7` -> `['P', '7']`, `Q10` -> `['Q', '10']`, `H1` -> `['H', '1']`.
- **Tiền tố viết tắt kèm dấu chấm**:
  - `X.` -> `['X', '.']` (2 token).
  - `H.` -> `['H', '.']` (2 token).
  - `T.` -> `['T', '.']` (2 token).
  - `P.` -> `['P', '.']` (2 token).
  - `Q.` -> `['Q', '.']` (2 token).
  - `TP.` -> `['TP', '.']` (2 token).
- **Cơ chế nuốt dấu chấm của tiền tố** (`src/tien_xu_ly/quy_tac.py:156-157`):
  ```python
  if j < len(tokens) and tokens[j] == ".":
      j += 1
  ```
  Khi so khớp tiền tố qua `khop_tien_to`, token `"."` đứng liền sau tiền tố hợp lệ sẽ được cộng vào bước nhảy `j`, giúp tiền tố dạng viết tắt có chấm (`P.`, `Q.`, `X.`, `H.`) được nhận diện trọn vẹn.

### 2.2. Xung đột ngữ nghĩa token `'x'` và `'x5'`
- Trong `quy_tac.py:19` (`HANH_CHINH`): `("x", {"xa"}, "xa")` -> Token `'x'` được gán nhãn tiền tố của **Cấp Xã**.
- Trong `quy_tac.py:38-64` (`CHI_TIET`): Hoàn toàn **không có** tiền tố `'x'` cho `thon_xom` (chỉ có `'xom'`).
- Nhưng trong `dinh_dang.py:27-47` (`_sinh_viet_tat_trong_span`):
  Hệ thống tự động sinh quy tắc viết tắt trong span: do `xom` là tiền tố duy nhất của `thon_xom` bắt đầu bằng `x`, nên nếu token đã nằm trong span `thon_xom` thì `'x'` được mở rộng thành `'Xóm'` (`tach_viet_tat: 'x5' -> 'Xóm 5'`).
- **Phân loại kiểm toán**:
  - **Rõ**: Tokenizer phân tách nhất quán dấu câu và tiền tố dính số (`x5` -> `['x', '5']`).
  - **Nguy cơ cao**: Xung đột vai trò của token `'x'`. Đứng ở vị trí tiền tố, `'x'` bị tranh chấp trực tiếp giữa `Xã` (theo `HANH_CHINH`) và `Xóm` (theo thực tế sử dụng dân gian). Nếu không có ngữ cảnh hành chính phía sau, mô hình rất dễ đoán sai nhãn cấp xã cho xóm.

---

## 3. Tiền tố chi tiết thon_xom còn thiếu trong luật nới span; Phân biệt khóm/khu phố/tổ dân phố & tên riêng có từ 'Đường', 'Phương'

### 3.1. Thiếu sót trong luật nới span (`TIEN_TO_THON_XOM`)
- **Mã nguồn liên quan**:
  - `src/tien_xu_ly/crf_chi_tiet.py:201-208`:
    ```python
    if proper_field == 'thon_xom' and marker[1][1] in TIEN_TO_THON_XOM:
        end_idx = marker[0]
        while end_idx < len(self.tokens) and self.tokens[end_idx] not in DAU_NGAT_CHI_TIET:
            if khop_tien_to(self.tokens, end_idx, CHI_TIET):
                break
            end_idx += 1
        if end_idx > b:
            b = end_idx
    ```
  - `src/tien_xu_ly/quy_tac.py:88`:
    ```python
    TIEN_TO_THON_XOM = ('Thôn', 'Ấp', 'Xóm', 'Bản', 'Buôn')
    ```
- **Lỗ hổng kiểm toán**:
  Trong khi `CHI_TIET` (`quy_tac.py:43-51`) hỗ trợ đầy đủ các tiền tố `thon_xom`, hằng số `TIEN_TO_THON_XOM` dùng để kích hoạt nới span (span expansion) lại **bỏ sót 7 tiền tố đô thị và đặc thù**:
  1. `Khu phố` (và viết tắt `kp`)
  2. `Tổ dân phố` (và viết tắt `tdp`)
  3. `Tổ` (`to`)
  4. `Khối phố` (`khoi pho`)
  5. `Khối` (`khoi`)
  6. `Khóm` (`khom`)
  7. `Cụm` (`cum`)
- **Hệ quả thực tế**: Khi CRF dự đoán thiếu nhãn tiếp diễn (`I-thon_xom`), chỉ các tiền tố nông thôn (`Thôn`, `Ấp`, `Xóm`, `Bản`, `Buôn`) mới được kích hoạt kéo dài span đến dấu ngắt. Toàn bộ các thực thể đô thị như `Khu phố 4`, `Tổ dân phố 12`, `Khóm 3` sẽ bị cắt cụt span nếu CRF chỉ gán nhãn token đầu.

### 3.2. Phân biệt các nhãn khóm / khu phố / tổ dân phố
- `khom`: Đơn vị tương đương tổ dân phố/thôn, phổ biến tại Nam Bộ (An Giang, Đồng Tháp, Cần Thơ...).
- `khu pho` (`kp`): Đơn vị tương đương tổ dân phố/thôn tại các đô thị phía Nam (TP.HCM, Bình Dương...).
- `to dan pho` (`tdp`): Đơn vị đô thị phổ biến tại miền Bắc và miền Trung (Hà Nội, Đà Nẵng...).
- Cả ba đều là thực thể hợp lệ thuộc nhãn `thon_xom` theo đặc tả `bai_toan.md:35`.
- **Nguy cơ**: Trong `quy_tac.py:90`, có `GIA_TRI_THON_XOM_LOAI_BO = ('khu', 'khu đô thị')` và `crf_chi_tiet.py:215` hủy span nếu giá trị là `khu`. Cần bảo đảm không loại bỏ nhầm `khu phố` khi bị cắt cụt thành `khu`.

### 3.3. Tên riêng chứa từ 'Đường', 'Phương'
- **Tên riêng chứa chữ 'Đường'** (ví dụ: `Thôn Đường Nhạn`, `Xóm Cầu Đường`, `Ấp Đường Long`):
  - `quy_tac.py:52`: `'duong'` là tiền tố của trường `duong`.
  - Trong vòng lặp nới span của `crf_chi_tiet.py:204`:
    `if khop_tien_to(self.tokens, end_idx, CHI_TIET): break`
  - Khi quét tới từ `Đường` trong tên thôn, `khop_tien_to` nhận diện `Đường` là tiền tố chi tiết -> Lập tức `break`!
  - **Hậu quả**: Span thôn xóm bị cắt đứt thành `Thôn`, còn `Đường Nhạn` bị đẩy sang trường `duong` một cách sai lệch.
- **Tên riêng chứa chữ 'Phương'** (ví dụ: `Thôn Phương Trạch`, `Xóm Phương Cầu`):
  - Trong `quy_tac.py:18`: `("phuong", {"xa"}, "phuong")` là tiền tố cấp Phường.
  - Khi gặp văn bản không dấu (`thon phuong trach`), từ `phuong` dễ bị bộ quy tắc hoặc Trie nhận diện nhầm thành tiền tố hành chính của Phường, bẻ gãy ranh giới của thôn xóm.

### 3.4. Phân loại kiểm toán
- **Nguy cơ cao**: `TIEN_TO_THON_XOM` thiếu hụt 7 tiền tố đô thị/Nam Bộ.
- **Nguy cơ cao**: Tên riêng chứa từ loại `Đường` bị cơ chế `khop_tien_to(...) break` xé nát span thôn xóm.

---

## 4. Ranh giới ngữ nghĩa: Điểm rõ ràng vs Điểm mơ hồ (Unknown/Abstain)

### 4.1. Vùng RÕ ngữ nghĩa (Determinable)
1. Cấu trúc tiền tố định danh hoàn chỉnh kèm số hoặc từ phân biệt rõ:
   - `Thôn + <Số/Tên>` có dấu phẩy: `Thôn 3,`, `Ấp 2,`, `Xóm Tân Lập,`.
   - Viết tắt chuẩn hoá đi kèm số: `kp4`, `KP 14`, `tdp 3`, `TDP 05`.
   - Có dấu ngắt `,` hoặc `;` ngăn cách với đơn vị hành chính tiếp theo: `..., Xóm 5, Xã Hồng Phong, ...`.
2. Định dạng span bảo toàn:
   - Khi span đã được xác định vai trò `thon_xom`, hàm `tach_viet_tat` trong `dinh_dang.py` chuyển đổi an toàn các tiền tố đơn nghĩa (`kp` -> `Khu phố`, `tdp` -> `Tổ dân phố`).

### 4.2. Vùng MƠ HỒ nội tại (Ambiguous) - Bắt buộc giữ Unknown / Abstain
1. **Viết tắt một ký tự trùng lặp đa nghĩa (Ambiguous Single-Letter Shorthand)**:
   - `'t' + số` (ví dụ `t5`): Đã được quy ước tại `tests/test_viet_tat_chi_tiet.py:30-31`: `'t'` vừa có thể là `Thôn 5`, vừa có thể là `Tổ 5`, vừa có thể là `Tỉnh`. Hệ thống **bắt buộc không đoán bừa**, giữ nguyên token hoặc cảnh báo.
   - `'x' + số` (ví dụ `x5`): Nếu đứng độc lập không có cấp xã đi kèm (ví dụ `x5, Ba Đình`), không đủ cơ sở xác định là `Xã 5` hay `Xóm 5`.
   - `'k' + số` (ví dụ `k98`): Có thể là `Kiệt 98` (`ngo_ngach_hem`), `Khu phố 98` hay `Khóm 98` (`thon_xom`).
2. **Từ không dấu có hình thái trùng tiền tố nhưng không có số phụ trợ**:
   - Từ `to`: Đã có luật chặn tại `quy_tac.py:160`: `"to" không dấu đứng trước tên riêng chưa đủ để gọi là tổ` (`tokens[i].casefold() == "to" and not tokens[j][0].isdigit()`). Ví dụ: `Tô Hiệu` không được biến thành `Tổ Hiệu`.
   - Tương tự với `Đồng`, `Cụm`, `Bản` khi đứng trước danh từ riêng.
3. **Địa danh hành chính chính thức trùng từ tố thôn xóm**:
   - Các xã/phường có tên dạng: Xã `Ấp Bắc`, Xã `Thôn Mười`, Phường `Khu Phố Mới`. Nếu chuỗi chỉ có một cụm từ, không được bóc tách phần đầu thành `thon_xom` nếu Trie xác định đó là tên chính thức của đơn vị cấp xã.
4. **Xã cũ bị chia tách theo địa giới sáp nhập** (`bai_toan.md:50-51`):
   - Khi xã cũ bị chia thành nhiều xã mới, nếu chuỗi địa chỉ chỉ có thôn/xóm chung chung mà bảng đối chiếu không có ánh xạ 1-1 với xã mới: Bắt buộc để trống `xa_phuong`, ghi nhận cờ `xa_bi_chia` và danh sách xã ứng viên. Tuyệt đối không chọn mò.

---

## 5. Bộ 12 Fixture Kiểm Chứng Ngữ Nghĩa (Độc lập, Không lấy từ Dev/Test)

| STT | Chuỗi đầu vào | Kỳ vọng trường mục tiêu | Mức tin cậy | Mục đích kiểm toán & Chống cắt nhầm |
|---|---|---|---|---|
| 1 | `Thôn Đường Nhạn, Xã Xuân Nộn, Huyện Đông Anh, Hà Nội` | `thon_xom` = "Thôn Đường Nhạn"<br>`duong` = "" | Cao | Phản ví dụ: Chống cắt nhầm chữ "Đường" trong tên thôn sang trường đường. |
| 2 | `Xóm Cầu Đường, Xã Bạch Đằng, Huyện Tiên Lãng, Hải Phòng` | `thon_xom` = "Xóm Cầu Đường"<br>`duong` = "" | Cao | Phản ví dụ: Từ "Đường" nằm trong tên riêng ghép của xóm, không phải tên đường. |
| 3 | `Thôn Phương Trạch, Xã Vĩnh Ngọc, Đông Anh, Hà Nội` | `thon_xom` = "Thôn Phương Trạch"<br>`xa_phuong` = "Xã Vĩnh Ngọc" | Cao | Phản ví dụ: Chống nhận nhầm "Phương" thành tiền tố "Phường" khi thiếu dấu/telex. |
| 4 | `Tổ Phố Mới, Phường Sông Cầu, Thành phố Bắc Kạn, Bắc Kạn` | `thon_xom` = "Tổ Phố Mới"<br>`duong` = "" | Cao | Phản ví dụ: Từ "Phố" đi sau tiền tố "Tổ" là tên riêng của tổ, không phải trường đường. |
| 5 | `Khu phố 4, Phường Linh Trung, Thành phố Thủ Đức, TP.HCM` | `thon_xom` = "Khu phố 4" | Cao | Kiểm tra tiền tố đô thị "Khu phố" (hiện đang thiếu trong `TIEN_TO_THON_XOM`). |
| 6 | `Tổ dân phố 12, Phường Nghĩa Đô, Quận Cầu Giấy, Hà Nội` | `thon_xom` = "Tổ dân phố 12" | Cao | Kiểm tra tiền tố "Tổ dân phố" (hiện đang thiếu trong `TIEN_TO_THON_XOM`). |
| 7 | `Khóm Bình Đức 3, Phường Bình Đức, TP Long Xuyên, An Giang` | `thon_xom` = "Khóm Bình Đức 3" | Cao | Kiểm tra tiền tố Nam Bộ "Khóm" (hiện đang thiếu trong `TIEN_TO_THON_XOM`). |
| 8 | `Số 45 Đường Tô Hiệu, Phường Nghĩa Tân, Cầu Giấy, Hà Nội` | `duong` = "Đường Tô Hiệu"<br>`thon_xom` = "" | Cao | Phản ví dụ: Từ "Tô" trong tên người Tô Hiệu không được gán nhầm thành tiền tố "Tổ". |
| 9 | `Ấp Bắc, Phường 5, Thành phố Mỹ Tho, Tiền Giang` | `duong` hoặc `thon_xom` tùy đối chiếu danh mục | Mơ hồ (Abstain) | Phản ví dụ: "Ấp Bắc" là tên đường lịch sử nhưng có chứa chữ "Ấp", cần tra cứu trie/danh mục. |
| 10 | `t5, Xã Quảng Minh, Huyện Việt Yên, Bắc Giang` | `thon_xom` = "t5" (giữ nguyên, không đoán) | Mơ hồ (Abstain) | Ranh giới đa nghĩa: "t" có thể là Thôn hoặc Tổ; bắt buộc abstain theo quy ước test. |
| 11 | `x5, Xã Hồng Phong, Huyện Nam Sách, Hải Dương` | `thon_xom` = "Xóm 5" | Trung bình | Kiểm tra giải nghĩa viết tắt "x5" khi đã có ngữ cảnh xác định rõ cấp xã phía sau. |
| 12 | `12A Đường Số 3, Khu phố 2, Phường An Khánh, TP Thủ Đức` | `so_nha` = "Số 12A"<br>`duong` = "Đường Số 3"<br>`thon_xom` = "Khu phố 2" | Cao | Kiểm tra phân tách đồng thời đường đánh số và thôn xóm, không để span nuốt nhau. |

---

## 6. Các ràng buộc kỹ thuật đối với Worker chỉnh sửa CRF

Worker tiếp nhận nhiệm vụ sửa CRF và hậu xử lý cần tuân thủ nghiêm ngặt các giới hạn kỹ thuật sau:

1. **Ràng buộc đồng bộ danh mục tiền tố nới span**:
   - Khi chỉnh sửa hàm nới span tại `crf_chi_tiet.py:201-208`, không được chỉ dựa vào bộ 5 tiền tố cổ điển (`Thôn`, `Ấp`, `Xóm`, `Bản`, `Buôn`). Bắt buộc phải đồng bộ hóa với đầy đủ các loại hình đơn vị tương đương thôn xóm trong `CHI_TIET` (`Khu phố`, `Tổ dân phố`, `Tổ`, `Khối phố`, `Khối`, `Khóm`, `Cụm`).
2. **Ràng buộc kiểm tra cấu trúc khi ngắt span bằng tiền tố**:
   - Không được thực hiện lệnh `break` ngắt span thôn xóm đơn thuần chỉ vì gặp từ khớp với tiền tố `duong` (`khop_tien_to(..., 'duong')`).
   - Phải có điều kiện kiểm tra ngữ cảnh phía sau: Chỉ ngắt span nếu từ loại đường đó đi kèm tên đường hoàn chỉnh hoặc có dấu phân cách `,` `;`. Nếu sau chữ `Đường` là tên riêng cụm thôn (như `Đường Nhạn`), phải bảo toàn trọn vẹn span thôn xóm.
3. **Ràng buộc bảo toàn vị trí token (Token Offset Invariance)**:
   - Dấu chấm `.` và gạch ngang `-` là các token riêng biệt. Mọi thao tác gộp hay chỉnh biên span phải tính toán trên chỉ số token gốc và bảo toàn chính xác ánh xạ ký tự (`bat_dau`, `ket_thuc`) từ `token_co_vi_tri`. Không được strip hoặc mutate làm lệch offset chuỗi gốc.
4. **Tuyệt đối không ép nhãn trường hợp viết tắt mơ hồ (Abstain Principle)**:
   - Với các tiền tố đa nghĩa đứng độc lập như `'t'`, `'k'` hoặc `'x'` (khi thiếu vắng cấp xã tường minh), tuyệt đối không tự ý nội suy sang một nhãn duy nhất để tăng điểm kiểm thử cơ học. Bắt buộc giữ nguyên giá trị thô hoặc gắn cờ cảnh báo nghi vấn.
5. **Chống Overfitting tập phát triển**:
   - Không được hardcode tên địa danh cụ thể vào mã nguồn quy tắc. Mọi giải pháp mở rộng phải dựa trên đặc trưng ngữ cảnh (ngữ pháp, dấu câu, tính chất từ loại và danh mục đối chiếu độc lập).
