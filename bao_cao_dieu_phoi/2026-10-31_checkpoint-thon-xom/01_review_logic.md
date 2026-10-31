# 01 — Review độc lập logic CRF: mở rộng span thôn/xóm

**Ngày review:** 2026-10-31  
**Kết luận:** **FAIL**

## 1. Phạm vi và phương pháp

Đã đọc đầy đủ bốn file được yêu cầu:

- `src/tien_xu_ly/crf_chi_tiet.py`
- `tests/test_loi_goc_log.py`
- `src/tien_xu_ly/quy_tac.py`
- `src/tien_xu_ly/tach_phan_con.py`

Đối chiếu diff hiện tại: trong bốn file trên, thay đổi nằm ở `crf_chi_tiet.py` và `test_loi_goc_log.py`; `quy_tac.py` và `tach_phan_con.py` không có thay đổi nhưng được kiểm tra như các thành phần cung cấp bảng tiền tố, token hóa và logic biên liên quan.

Đã đọc thêm các phần phụ thuộc trực tiếp để xác minh đường chạy: `dinh_dang.py`, `tien_xu_ly.py`, `lam_sach.py`, `char_cnn.py`, `ngu_canh_neural.py`. Xác nhận bộ Char-CNN trong test tạo `NguCanhChar`, lớp này kế thừa `NguCanhCRF`; vì vậy `NguCanhCRF.tach()` là đường xử lý thực tế mà test có thể đi qua.

**Không chạy test, không chạy suy luận mô hình, không sửa mã nguồn, không commit.** Hai file được dùng trong điều kiện `skipUnless` của test (mô hình `char_cnn.pt` và từ điển đường dẫn) hiện có mặt trong workspace; tuy nhiên không thực thi test nên không kết luận về kết quả runtime.

## 2. Tóm tắt thay đổi

Bản sửa thêm `TIEN_TO_HANH_CHINH_DAI`, lọc từ `HANH_CHINH` các tiền tố có ít nhất hai ký tự sau khi bỏ khoảng trắng. Khi span CRF bắt đầu bằng một tiền tố chi tiết thuộc `TIEN_TO_THON_XOM`, code đi từ token ngay sau tiền tố thôn/xóm và mở rộng đến khi gặp:

- dấu ngắt trong `DAU_NGAT_CHI_TIET`;
- token đã thuộc span/đơn vị khác;
- một tiền tố chi tiết khác;
- một tiền tố hành chính nằm trong `TIEN_TO_HANH_CHINH_DAI`.

Test mới thêm bốn đầu vào, trong đó ba trường hợp không có dấu phẩy và một trường hợp có dấu phẩy với tên nhiều từ.

Ý tưởng dùng bảng `HANH_CHINH` và matcher dùng chung là hợp lý, nhưng cơ chế dừng hiện chỉ có tác dụng trong một nhánh và chưa bảo đảm cắt biên span đã bị CRF gán quá dài.

## 3. Các điểm đúng

1. **Tái sử dụng nguồn tiền tố chung.** `TIEN_TO_HANH_CHINH_DAI` được sinh từ `HANH_CHINH`, không tạo một bảng hành chính độc lập dễ lệch quy tắc. Việc gọi `khop_tien_to` cũng tái sử dụng xử lý dấu, dạng không dấu và Telex trong `quy_tac.py`.

2. **Nhận được tiền tố hành chính đầy đủ trong câu không có dấu phẩy.** Các dạng như `xã`, `huyện`, `tỉnh`, `phường`, `quận`, `tp`, `tx` có độ dài từ hai ký tự trở lên được giữ lại trong danh sách dừng. Ba ví dụ đầu của test kiểm tra được trường hợp gặp `xã` sau tên thôn/xóm.

3. **Có xét các biên khác ngoài hành chính.** Nhánh mở rộng dừng khi gặp token đã được dùng hoặc tiền tố chi tiết khác. Điều này giảm nguy cơ kéo một trường chi tiết tiếp theo vào span thôn/xóm nếu token đó nằm ngoài span hiện tại.

4. **Phạm vi kích hoạt tương đối hẹp.** Việc mở rộng chỉ chạy khi trường đã được xác định là `thon_xom` và nhãn tiền tố nằm trong `TIEN_TO_THON_XOM`; không áp dụng tùy tiện cho mọi span.

5. **Ví dụ có dấu phẩy vẫn giữ được tên nhiều từ.** Trường hợp `Xóm Khe Cát, ...` kiểm tra được việc giữ phần tên `Khe Cát` trước dấu phẩy.

## 4. Lỗi tiềm ẩn và tình huống sai cụ thể

### HIGH-01 — Có phát hiện điểm dừng nhưng không cắt span CRF đã vượt qua điểm dừng

**Dòng liên quan:** `crf_chi_tiet.py:209-216`, đặc biệt dòng 215-216.

Vòng lặp có thể phát hiện tiền tố hành chính ở `end_idx`, nhưng code chỉ gán lại `b` khi `end_idx > b`. Nếu span CRF hiện tại đã kéo dài qua tiền tố hành chính thì `end_idx < b`; biên cũ được giữ nguyên. Như vậy cơ chế mới chỉ có thể mở rộng span ngắn, không thể sửa span đã nuốt quá xa.

**Đầu vào cụ thể:**

```text
xóm 5 xã mỹ hưng huyện mỹ lộc tỉnh nam định
```

**Kết quả dự kiến:**

```text
thon_xom = Xóm 5
```

**Đường gây lỗi:** nếu CRF gán một span `thon_xom` liên tục từ `xóm` qua một phần hoặc toàn bộ cụm hành chính, vòng lặp phát hiện `xã` tại token tương ứng rồi dừng. Nhưng do `end_idx` nhỏ hơn `b`, `b` không được thu ngắn. `dinh_dang_span()` sau đó vẫn nhận cả đoạn đã vượt biên và có thể tạo giá trị như `Xóm 5 Xã Mỹ Hưng Huyện Mỹ Lộc ...`.

Đây là lỗi trực tiếp đối với mục tiêu “dừng khi gặp tiền tố hành chính”: điểm dừng được nhận diện nhưng không có quyền cắt span đã đi quá điểm đó.

### HIGH-02 — Nhánh fallback `unknown_candidates` vẫn nuốt hành chính và tiền tố chi tiết

**Dòng liên quan:** `crf_chi_tiet.py:232-249`, đặc biệt dòng 245-247.

Cơ chế dừng mới chỉ nằm trong vòng xử lý span CRF ở dòng 209-216. Nhánh rà soát token chưa phân loại dùng một vòng lặp khác: chỉ dừng khi gặp token đã dùng hoặc dấu phẩy/chấm phẩy. Nhánh này không kiểm tra `TIEN_TO_HANH_CHINH_DAI` và cũng không kiểm tra `CHI_TIET`.

**Đầu vào cụ thể:**

```text
xóm 5 xã mỹ hưng huyện mỹ lộc tỉnh nam định
```

**Kết quả dự kiến:**

```text
thon_xom = Xóm 5
```

**Đường gây lỗi:** nếu mô hình không gán span cho tiền tố `xóm` (ví dụ các token đó vẫn là `O`), token `xóm` trở thành ứng viên chưa phân loại. Fallback nhận ra tiền tố `xóm`, đặt `j` sau tiền tố rồi tăng `j` đến hết câu vì không có dấu phẩy/chấm phẩy. Cả `xã Mỹ Hưng huyện Mỹ Lộc tỉnh Nam Định` có thể bị đưa vào giá trị thôn/xóm.

Cùng đường này cũng có thể nuốt một tiền tố chi tiết khác, ví dụ `đường`, nếu nó xuất hiện sau tên thôn mà không có dấu ngắt.

Vì fallback là nhánh xử lý phục hồi khi CRF không nhận diện được span, bỏ sót chính sách dừng ở nhánh này làm cho bảo vệ mới không có hiệu lực trong một tình huống quan trọng.

### HIGH-03 — Bỏ toàn bộ tiền tố hành chính viết tắt một chữ cái, kể cả dạng có dấu chấm

**Dòng liên quan:**

- `crf_chi_tiet.py:34`
- `quy_tac.py:13-19`

Điều kiện `len(r[0].replace(' ', '')) >= 2` loại `t`, `h`, `q`, `p`, `x`. Đây đều là tiền tố có trong `HANH_CHINH`, không phải token không được hệ thống biết đến. Tuy nhiên chúng không còn được dùng làm điểm dừng trong nhánh mở rộng CRF.

**Đầu vào cụ thể:**

```text
xóm 5 x. mỹ hưng h. mỹ lộc t. nam định
```

**Kết quả dự kiến:**

```text
thon_xom = Xóm 5
```

**Nguy cơ theo code:** vòng lặp không dừng tại `x.`, `h.`, `t.` vì các tiền tố tương ứng đã bị loại khỏi danh sách. Nếu không có tiền tố hành chính đầy đủ nào khác và không có dấu phẩy/chấm phẩy, nó có thể mở rộng đến hết chuỗi, đưa cả xã, huyện và tỉnh vào thôn/xóm.

Một biến thể cũng dễ gặp là:

```text
xóm 5 q. ninh kiều tp. cần thơ
```

Danh sách có thể dừng ở `tp.`, nhưng phần `q. Ninh Kiều` đã bị kéo vào thôn/xóm trước khi gặp `tp.`.

Lý do loại tiền tố một chữ cái để tránh cắt nhầm tên riêng là có thể hiểu được, nhưng hiện không có quy tắc thay thế cho dạng viết tắt hành chính có dấu chấm. Đặc biệt, `khop_tien_to` có khả năng nhận dạng tiền tố một chữ cái và dấu chấm nếu được truyền bảng đầy đủ; việc lọc ở đây làm mất khả năng đó.

### MEDIUM-01 — Dấu câu ngoài dấu phẩy/chấm phẩy bị giữ trong tên thôn/xóm

**Dòng liên quan:**

- `quy_tac.py:89` — `DAU_NGAT_CHI_TIET` chỉ gồm dấu phẩy và chấm phẩy.
- `crf_chi_tiet.py:210` — vòng mở rộng chỉ dừng ở tập dấu ngắt trên.
- `tien_xu_ly.py:18-23` — tokenizer tách dấu câu thành token riêng.
- `tach_phan_con.py:10-14` và `dinh_dang.py:143` — cách định dạng tên.
- `crf_chi_tiet.py:150-158` — hậu xử lý biên không có nhánh làm sạch riêng cho `thon_xom`.

**Đầu vào cụ thể:**

```text
Xóm Khe Cát - Xã Lam Điền
```

**Kết quả dự kiến:**

```text
thon_xom = Xóm Khe Cát
```

**Nguy cơ theo code:** dấu gạch ngang không nằm trong `DAU_NGAT_CHI_TIET`, nên vòng lặp đi qua token `-` rồi mới dừng tại `Xã`. Dấu gạch ngang có thể bị đưa vào span và giữ lại trong giá trị.

Trường hợp tương tự:

```text
Xóm Khe Cát. Xã Lam Điền
```

Dấu chấm cũng được đi qua trước khi gặp `Xã`; `viet_ten()` chuẩn hóa khoảng trắng quanh một số dấu câu nhưng không loại dấu chấm/gạch ngang cuối span vừa được mở rộng. Kết quả có thể là `Xóm Khe Cát.` thay vì `Xóm Khe Cát`.

Trường hợp có dấu phẩy trong ví dụ thứ tư không phát hiện được lỗi này.

### MEDIUM-02 — Tiền tố hành chính/chi tiết trùng từ trong tên riêng có thể gây dừng nhầm

**Dòng liên quan:**

- `crf_chi_tiet.py:211-212)
- `quy_tac.py:131-165)
- `tach_phan_con.py:48-59) để đối chiếu cách kiểm tra biên của nhánh luật.

Vòng mở rộng dừng khi token khớp bất kỳ tiền tố hành chính hoặc chi tiết nào. Nó không kiểm tra token sau tiền tố có tạo thành một đơn vị hợp lệ hay không. `khop_chu_tien_to()` chấp nhận dạng không dấu và dạng Telex; vì vậy một từ tên riêng viết không dấu có thể trùng với tiền tố hành chính.

**Ví dụ tên riêng trùng tiền tố hành chính:**

```text
Thôn Phuong Nam xã Mỹ Hưng huyện Mỹ Lộc tỉnh Nam Định
```

Nếu `Phuong Nam` là tên thôn được nhập không dấu, token `Phuong` có thể khớp tiền tố `phuong` (Phường). Nếu span CRF hiện tại kết thúc ở `Phuong`, vòng mở rộng sẽ dừng trước `Nam`, làm mất phần còn lại của tên riêng.

**Ví dụ tên riêng trùng tiền tố chi tiết:**

```text
Xóm Đường Mới
```

Token `Đường` khớp tiền tố chi tiết `duong`. Nếu span hiện tại chưa bao gồm `Mới`, vòng mở rộng có thể dừng tại đó và không lấy đủ tên `Đường Mới`.

Đây là sự đánh đổi giữa tách trường và bảo toàn tên riêng. Hiện tại code dùng kết quả khớp tiền tố làm điều kiện dừng tuyệt đối, không có kiểm tra ngữ cảnh. Rủi ro tăng với dữ liệu không dấu và dữ liệu Telex vì matcher chủ động chấp nhận các dạng này.

### LOW-01 — Tập nhãn được mở rộng không bao phủ toàn bộ các loại cùng trường `thon_xom`

**Dòng liên quan:**

- `quy_tac.py:38-51` — `CHI_TIET` có các nhãn như `Khóm`, `Khu phố`.
- `quy_tac.py:88` — `TIEN_TO_THON_XOM` chỉ gồm `Thôn`, `Ấp`, `Xóm`, `Bản`, `Buôn`.
- `crf_chi_tiet.py:205` — điều kiện kích hoạt mở rộng.

Ví dụ:

```text
Khóm Cầu Đen
```

`Khóm` được khai báo là `thon_xom` trong `CHI_TIET`, nhưng nhãn hiển thị `Khóm` không có trong `TIEN_TO_THON_XOM`. Vì vậy cơ chế nới span mới không chạy cho tiền tố này. Nếu mô hình chỉ gán một phần tên, phần còn lại có thể không được thu nhận.

Nếu phạm vi chủ đích chỉ là năm loại trong `TIEN_TO_THON_XOM`, đây là giới hạn thiết kế; nếu mục tiêu là mở rộng mọi loại thuộc trường `thon_xom`, đây là thiếu sót chức năng.

## 5. Đánh giá bốn ví dụ hồi quy mới

Các ví dụ nằm tại `test_loi_goc_log.py:84-87`.

| # | Đầu vào rút gọn | Kỳ vọng | Đánh giá |
|---|---|---|---|
| 1 | `xóm 5 xã mỹ hưng huyện mỹ lộc tỉnh nam định` | `Xóm 5` | Có giá trị: kiểm tra trường hợp không dấu phẩy và tiền tố đầy đủ `xã`. Không kiểm tra trường hợp span CRF đã vượt qua `xã` hoặc nhánh fallback. |
| 2 | `thôn 3 xã hoằng lộc huyện hoằng hóa tỉnh thanh hóa` | `Thôn 3` | Tương tự ví dụ 1; kiểm tra biến thể tiền tố `Thôn` và tên có số. Không tạo thêm độ phủ cho các loại tiền tố hành chính khác vì vẫn dừng đầu tiên tại `xã`. |
| 3 | `thôn đông xã nam hồng huyện tiền hải thái bình` | `Thôn Đông` | Có giá trị cho tên thôn một từ không có số. Vẫn chỉ kiểm tra điểm dừng `xã`, chưa kiểm tra trường hợp `huyện` hoặc `tỉnh` là tiền tố hành chính đầu tiên sau thôn. |
| 4 | `Xóm Khe Cát, Xã Lam Điền, Chương Mỹ, Hà Nội` | `Xóm Khe Cát` | Kiểm tra tên nhiều từ, nhưng dấu phẩy đã là điểm dừng cũ. Không chứng minh cơ chế dừng mới hoạt động khi không có dấu phẩy. |

**Nhận xét chung về test:**

- Ba ví dụ không dấu phẩy đều dùng tiền tố hành chính đầy đủ `xã`, có dấu tiếng Việt. Không có `Q.`, `P.`, `H.`, `T.`, `X.`, không có dạng Telex hoặc tên riêng không dấu trùng tiền tố.
- Không có ví dụ tên thôn nhiều từ và đơn vị hành chính nối ngay sau mà không có dấu phẩy, ví dụ `Xóm Khe Cát Xã Lam Điền ...`. Do đó chưa kiểm tra đúng tình huống kết hợp quan trọng nhất: vừa phải nới tên nhiều từ, vừa phải dừng ở hành chính.
- Ví dụ thứ tư dừng tại dấu phẩy trước khi cần xét `Xã`; nó chủ yếu kiểm tra hành vi cũ.
- Các assertion chỉ kiểm tra `.thon_xom`, không kiểm tra các trường hành chính, `phan_chua_phan_loai` hoặc dấu vết span. Điều này làm giảm khả năng phát hiện trường hợp thôn/xóm đúng tình cờ nhưng phần hành chính bị mất hoặc bị xử lý sai ở bước sau.
- Test chưa mô phỏng trực tiếp hai trạng thái BIO quan trọng: span CRF đã vượt qua điểm dừng và tiền tố thôn/xóm bị bỏ nhãn để rơi vào fallback.
- `test_viet_tat_xom_trong_span` ở dòng 90 kiểm tra `x5`, nhưng đầu vào có dấu phẩy; nó không kiểm tra viết tắt hành chính một chữ cái trong câu không dấu phẩy.
- Lớp test có `skipUnless` tại dòng 14. Hai tài nguyên điều kiện hiện tồn tại, nhưng review này không chạy test nên không xác nhận kết quả thực thi.

## 6. Đối chiếu với nhánh tách theo luật

`tach_phan_con.py:48-68` có hàm `boundary()` và `end_detail()` riêng. Nhánh luật dùng `cac_tien_to()`, vốn nhận toàn bộ bảng `HANH_CHINH`, bao gồm các tiền tố một chữ cái; đồng thời kiểm tra token sau tiền tố và loại một số dấu câu cuối span.

Nhánh CRF mới tự xây danh sách `TIEN_TO_HANH_CHINH_DAI` và tự lặp token. Vì thế hai đường xử lý có hành vi khác nhau đối với tiền tố viết tắt một chữ cái và dấu câu. Không nên coi logic biên của `tach_phan_con.py` là đã bảo vệ nhánh fallback trong `crf_chi_tiet.py`: fallback đó không gọi `boundary()` hay `end_detail()`.

## 7. Kết luận

**FAIL — chưa nên chấp nhận bản sửa như một cơ chế bảo vệ span thôn/xóm hoàn chỉnh.**

Lý do quyết định:

1. **HIGH-01:** điểm dừng hành chính không cắt được span CRF đã vượt qua điểm dừng.
2. **HIGH-02:** nhánh fallback vẫn có thể nuốt toàn bộ đơn vị hành chính và tiền tố chi tiết khi không có dấu phẩy.
3. **HIGH-03:** các dạng viết tắt hành chính một chữ cái phổ biến bị bỏ qua, khiến địa chỉ không dấu phẩy vẫn có thể bị nuốt.

Ngoài ra, dấu câu ngoài `,` và `;` có thể lọt vào tên; matcher có thể dừng nhầm tại từ thuộc tên riêng; và tập nhãn mở rộng chưa bao phủ `Khóm`.

Review này xác nhận được các lỗi logic bằng cách lần theo đường thực thi và điều kiện biên trong mã nguồn, nhưng **không xác nhận đầu ra runtime** vì đã tuân thủ yêu cầu không chạy test hoặc suy luận mô hình. Không có file mã nguồn nào được sửa trong quá trình review.
