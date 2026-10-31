# 04 — Fix plan: ba lỗi HIGH của span thôn/xóm

**Ngày:** 2026-10-31  
**Phạm vi:** chỉ thiết kế sửa HIGH-01, HIGH-02, HIGH-03 theo `01_review_logic.md`.  
**Trạng thái:** đề xuất, chưa triển khai.

## Nguyên tắc chung

Sửa tập trung trong `src/tien_xu_ly/crf_chi_tiet.py`. Không đổi semantics toàn cục của `khop_tien_to()` / `khop_chu_tien_to()`, không sửa bảng tiền tố dùng chung, không thay đổi nhánh xử lý `so_nha`, `ngo_ngach_hem`, `duong`.

Nên tạo **một helper nội bộ chỉ dùng để xác định biên span `thon_xom`**, sau đó gọi helper ở cả nhánh CRF và nhánh `unknown_candidates`. Không dùng việc “khớp từ khóa” đơn thuần làm bằng chứng ranh giới: `Phương Nam` có thể trùng dạng ASCII `phuong`; `Đường Mới` có thể bắt đầu bằng đúng từ loại đường nhưng vẫn là tên thôn.

Thứ tự ưu tiên bằng chứng dừng:

1. Token đã nằm trong `used` (đã được chọn/chiếm bởi đơn vị khác).
2. Dấu phân đoạn hiện hành `,` hoặc `;`.
3. Tiền tố hành chính đủ tin cậy theo quy tắc ở HIGH-01/HIGH-03.
4. Đầu một BIO span chi tiết độc lập có trường khác `thon_xom` (lấy từ danh sách `spans` đã giải mã trước vòng lặp, không phụ thuộc span đó đã được xử lý trước hay chưa).

**Không dừng chỉ vì token bên trong tên khớp một tiền tố `CHI_TIET`.** Chỉ dừng ở tiền tố chi tiết khác khi có bằng chứng độc lập: token đã `used` hoặc đúng vị trí bắt đầu của BIO span trường khác. Quy tắc này bảo vệ `Đường Mới`; nếu mô hình không cung cấp bằng chứng phân trường và không có dấu ngắt thì không thể phân biệt chắc chắn tên riêng với trường đường kế tiếp chỉ bằng từ `Đường`.

---

## HIGH-01 — Cắt span CRF khi biên CRF đã vượt qua tiền tố hành chính

### Vị trí code

- `crf_chi_tiet.py:193-216`: vòng lặp `for f, a, b in spans`, nhận diện tiền tố thôn/xóm và mở rộng.
- Cụ thể `205-216`: nhánh `proper_field == 'thon_xom'`, `end_idx = marker[0]`, kiểm tra điểm dừng, nhưng chỉ gán `b = end_idx` khi `end_idx > b`.
- `crf_chi_tiet.py:217-230`: hậu xử lý và định dạng span sau khi đổi biên.

### Ví dụ gây lỗi

```text
xóm 5 xã mỹ hưng huyện mỹ lộc tỉnh nam định
```

Trạng thái cần mô phỏng: BIO span `thon_xom` bị gán liên tục từ `xóm` đến tận `định`, không có token hành chính nào trong `used`. Matcher tìm được `xã` ở vị trí trước biên `b`, nhưng điều kiện `end_idx > b` sai nên giữ nguyên biên cũ.

**Kết quả mong muốn:** `thon_xom = Xóm 5`; các token từ `xã` trở đi không được đưa vào span thôn/xóm.

### Phương án ít xâm lấn

1. Giữ nguyên điều kiện kích hoạt hiện tại: chỉ áp dụng cho span được xác định là `thon_xom` và tiền tố thuộc phạm vi đang hỗ trợ.
2. Tính một biên kết thúc đáng tin cậy duy nhất từ sau tiền tố thôn/xóm: gặp `used`, dấu ngắt, tiền tố hành chính đã xác nhận, hoặc đầu BIO span của trường chi tiết khác.
3. Coi biên này là **giới hạn trên bắt buộc**, không chỉ là điểm để mở rộng. Nếu span CRF dài hơn giới hạn thì cắt; nếu span CRF ngắn hơn thì chỉ mở rộng đến giới hạn đó.
4. Về mặt biên chỉ số, ý tưởng là giới hạn `b` vào khoảng từ sau toàn bộ tiền tố đến điểm dừng đầu tiên. Không giữ `b` cũ khi nó đã vượt điểm dừng.
5. Nếu điểm dừng nằm ngay sau tiền tố, không phát ra giá trị chỉ có nhãn như `Xóm`/ `Thôn` mà không có tên thân; không lấy phần hành chính để lấp chỗ trống.

Tận dụng danh sách BIO span đã có trong hàm để nhận biết đầu span `duong`/trường khác. Không cần đổi định dạng nhãn hoặc mô hình.

### Bảo vệ tên riêng

- `Thôn Phương Nam xã Mỹ Hưng huyện Mỹ Lộc` phải giữ `Phương Nam`. Với chính tả có dấu, `Phương` không phải chính tả của `Phường`; không nới matcher theo kiểu bỏ qua khác biệt dấu để biến nó thành điểm dừng.
- Với chuỗi không dấu `Thôn Phuong Nam xa My Hung ...`, `phuong` là dạng ASCII mơ hồ. Không coi riêng token này là ranh giới chắc chắn; chỉ xác nhận khi có bằng chứng độc lập hoặc chuỗi cấp hành chính kế tiếp phù hợp về thứ bậc. `phuong` rồi đến `xa` không phải chuỗi cấp hợp lệ cho cách hiểu `Phường` rồi đến `xã`, nên phải giữ `Phuong Nam`.
- `Xóm Đường Mới`: không dừng tại `Đường` chỉ vì `Đường` khớp tiền tố `duong`. Chỉ tách nếu BIO có span `duong` độc lập bắt đầu tại đó, hoặc có bằng chứng biên độc lập khác.
- Không thay đổi `khop_chu_tien_to()` dùng chung: hàm đó phục vụ nhiều trường và cho phép biến thể dấu/Telex. Quy tắc chặt hơn chỉ áp dụng cho quyết định dừng thôn/xóm.

### Nguy cơ hồi quy

- **Cắt thiếu:** quy tắc quá chặt có thể không dừng ở một tiền tố hành chính bị viết sai dấu/không dấu và không có bằng chứng xác nhận. Khi đó phần còn lại có thể ở `phan_chua_phan_loai`; đây là lựa chọn an toàn hơn việc tự gộp hành chính vào tên thôn.
- **Cắt nhầm tên:** nếu dùng matcher hành chính hiện tại mà không phân biệt dạng ASCII mơ hồ, `Phuong Nam` có thể bị cắt. Nếu dừng ở mọi `CHI_TIET`, `Đường Mới` có thể bị cắt. Hai trường hợp này phải là test bắt buộc.
- **Ảnh hưởng trường khác:** tránh bằng cách chỉ áp dụng giới hạn biên cho `f == 'thon_xom'`; giữ nguyên nhánh `so_nha`, `ngo_ngach_hem`, `duong` và các lần gọi `loc_va_chinh_bien_span()`.

### Test hồi quy tối thiểu đề xuất

Dùng `NguCanhCRF` với tokens/labels dựng trực tiếp, không cần nạp mô hình:

1. **Span cố ý quá dài:** gán toàn bộ `xóm 5 xã mỹ hưng huyện mỹ lộc tỉnh nam định` thành một BIO span `thon_xom`, `occupied=set()`. Kỳ vọng giá trị là `Xóm 5`, span kết thúc ngay trước `xã`.
2. **Tên riêng có từ gần tiền tố hành chính:** `Thôn Phương Nam xã Mỹ Hưng huyện Mỹ Lộc`. Kỳ vọng giữ nguyên `Thôn Phương Nam`.
3. **Tên riêng trùng tiền tố chi tiết:** `Xóm Đường Mới xã Mỹ Hưng`. Kỳ vọng giữ `Xóm Đường Mới`, chỉ dừng ở `xã`.
4. Kiểm tra thêm biến thể ASCII `Thon Phuong Nam xa My Hung ...`: không cắt tại `Phuong` chỉ vì trùng khóa ASCII; chỉ dừng tại điểm hành chính có đủ bằng chứng.

---

## HIGH-02 — Bổ sung quy tắc dừng cho nhánh `unknown_candidates`

### Vị trí code

- `crf_chi_tiet.py:232-249`: tạo `unknown_candidates`, nhận diện tiền tố chi tiết và mở rộng `j`.
- Cụ thể `245-247`: vòng lặp hiện chỉ dừng khi hết token, gặp `used` hoặc `DAU_NGAT_CHI_TIET`; không dùng logic dừng hành chính của nhánh CRF.

### Ví dụ gây lỗi

```text
xóm 5 xã mỹ hưng huyện mỹ lộc tỉnh nam định
```

Trạng thái cần mô phỏng: nhãn CRF của các token là `O`, `occupied=set()`. Fallback nhận ra tiền tố `xóm`, nhưng vòng lặp `j` đi đến hết chuỗi vì không có dấu phẩy/chấm phẩy.

**Kết quả mong muốn:** `thon_xom = Xóm 5`; cụm hành chính không bị đưa vào giá trị này.

### Phương án ít xâm lấn

1. Dùng lại **chính helper xác định biên thôn/xóm** được đề xuất cho HIGH-01; không viết một bộ điều kiện dừng thứ hai.
2. Chỉ thay cách tính `j` khi `f == 'thon_xom'`. Các trường khác giữ nguyên vòng lặp hiện tại để không đổi hành vi fallback của đường, số nhà, ngõ/ngách.
3. Biên fallback phải xét cùng các bằng chứng: `used`, dấu ngắt, tiền tố hành chính đã xác nhận và đầu BIO span khác trường.
4. Không coi mọi tiền tố `CHI_TIET` là điểm dừng. Nếu fallback gặp `Đường` trong `Xóm Đường Mới` mà không có span đường độc lập, phải tiếp tục lấy `Mới`.
5. Sau khi tính biên, giữ nguyên quy trình định dạng, lọc số nhà và cập nhật `used` hiện tại. Không thay đổi cách xử lý các trường fallback khác.

### Nguy cơ hồi quy

- **Nuốt hành chính vẫn còn:** nếu helper chỉ kiểm tra BIO span mà không kiểm tra tiền tố hành chính rõ ràng, trường hợp nhãn toàn `O` vẫn lỗi. Fallback phải dùng cùng nhận diện tiền tố hành chính như HIGH-01.
- **Cắt mất tên thôn:** nếu dừng tại mọi tiền tố chi tiết, `Xóm Đường Mới` hoặc tên có từ `Tổ`, `Khu` sẽ bị cắt. Chỉ dùng biên BIO khác trường/biên độc lập, không dùng match từ vựng đơn lẻ.
- **Ảnh hưởng trường khác:** giới hạn nhánh mới vào `f == 'thon_xom'`; không thay vòng lặp cũ cho `duong`, `so_nha`, `ngo_ngach_hem`.

### Test hồi quy tối thiểu đề xuất

1. **Fallback toàn O:** tokens của `xóm 5 xã mỹ hưng huyện mỹ lộc tỉnh nam định`, labels toàn `O`, `occupied=set()`. Kỳ vọng fallback tạo `Xóm 5`, không nuốt phần hành chính.
2. **Không cắt tên:** tokens của `Xóm Đường Mới`, labels toàn `O`, `occupied=set()`. Kỳ vọng `thon_xom = Xóm Đường Mới`.
3. **Không đổi trường khác:** dựng một trường hợp fallback đường có tiền tố `đường` và xác nhận biên/giá trị vẫn theo hành vi cũ. Test này là guard hẹp, không mở rộng sửa fallback cho các trường khác.

---

## HIGH-03 — Nhận diện viết tắt hành chính một chữ cái mà không coi chữ cái đơn lẻ là ranh giới

### Vị trí code

- `crf_chi_tiet.py:34`: `TIEN_TO_HANH_CHINH_DAI` chỉ lấy khóa có ít nhất hai ký tự.
- `quy_tac.py:8-20`: `HANH_CHINH` có các khóa một chữ cái `t`, `h`, `q`, `p`, `x`.
- `quy_tac.py:131-158`: `khop_chu_tien_to()` và `khop_tien_to()`; matcher có thể tiêu thụ dấu chấm sau tiền tố, nhưng cũng có thể khớp token chữ cái không có dấu chấm.

### Ví dụ gây lỗi

```text
xóm 5 x. mỹ hưng h. mỹ lộc t. nam định
```

**Kết quả mong muốn:** `thon_xom = Xóm 5`; `x.`, `h.`, `t.` là các tiền tố hành chính viết tắt, không thuộc tên xóm.

Biến thể:

```text
xóm 5 q. ninh kiều tp. cần thơ
```

**Kết quả mong muốn:** `thon_xom = Xóm 5`; `q.` mở đầu đơn vị quận, không bị gộp vào tên xóm.

### Phương án ít xâm lấn

1. **Không** đưa thẳng `t/h/q/p/x` vào `TIEN_TO_HANH_CHINH_DAI`. Làm vậy sẽ khiến chữ cái đơn lẻ không có dấu chấm cũng trở thành điểm dừng và dễ cắt tên.
2. Giữ danh sách tiền tố dài hiện tại; tạo một tập viết tắt một chữ cái riêng từ các hàng tương ứng trong `HANH_CHINH`.
3. Với tập riêng này, chỉ chấp nhận dạng viết tắt có dấu chấm rõ ràng: `X.`, `P.`, `Q.`, `H.`, `T.`. `khop_tien_to()` có thể trả vị trí sau dấu chấm; cần xác minh token ngay trước vị trí trả về thực sự là `.`. Không chấp nhận chữ cái trần như `x` hoặc `p` làm biên.
4. Sau dấu chấm phải có token tên đơn vị hợp lệ (token chữ/số), không phải dấu câu, hết chuỗi hoặc một tiền tố khác ngay lập tức.
5. Vì chữ cái + dấu chấm vẫn có thể là chữ viết tắt tên riêng, chỉ xác nhận nó là biên khi có bằng chứng bổ sung: ứng viên hành chính đã được chọn/đã `used`, hoặc chuỗi cấp hành chính kế tiếp tương thích về thứ bậc. Ví dụ `x. Mỹ Hưng h. Mỹ Lộc t. Nam Định` là chuỗi có xác nhận tiếp theo; `P. Nam` đứng một mình không đủ bằng chứng để cắt tên.
6. Với khóa ASCII không dấu nhiều ký tự như `phuong`, `xa`, `quan`, `huyen`, áp dụng nguyên tắc tương tự: dạng ASCII trần là bằng chứng yếu nếu nó cũng có thể là tên riêng. Không dùng một match đơn lẻ để cắt. Dạng tiếng Việt đúng dấu hoặc Telex đúng chính tả có độ tin cậy cao hơn; trường hợp không dấu cần bằng chứng ngữ cảnh.
7. Nếu không đủ bằng chứng, giữ token trong phần tên/unknown thay vì cắt nhầm. Không thể phân biệt tuyệt đối `Phuong Nam` (tên riêng không dấu) với một cụm hành chính không dấu chỉ từ một token; muốn quyết định chắc chắn cần ứng viên hành chính độc lập hoặc dữ liệu ngữ cảnh.

### Nguy cơ hồi quy

- **Cắt nhầm chữ cái đầu/tên viết tắt:** nếu chỉ thêm các khóa một chữ cái vào danh sách hiện tại, các token `x`, `p`, `q`, `h`, `t` trong tên riêng có thể thành điểm dừng. Bắt buộc yêu cầu dấu chấm và bằng chứng bổ sung.
- **Bỏ sót địa chỉ viết tắt:** chính sách bảo thủ có thể không tách được một tiền tố một chữ cái đứng cuối chuỗi mà không có bằng chứng thứ hai. Chấp nhận giới hạn này thay vì tự động cắt một tên riêng mơ hồ; trường hợp đó còn được giữ ở unknown để xử lý sau.
- **Telex/không dấu:** không sửa matcher chung. Chỉ nâng độ tin cậy của stop decision; không làm thay đổi cách nhận diện ứng viên hành chính hoặc các trường chi tiết khác.
- **Ảnh hưởng trường khác:** tập viết tắt mới chỉ được dùng trong helper dừng span `thon_xom`, không thay đổi `HANH_CHINH`, `cac_tien_to()` hoặc hành vi định dạng.

### Test hồi quy tối thiểu đề xuất

1. **Viết tắt có dấu chấm, có chuỗi xác nhận:** `xóm 5 x. Mỹ Hưng h. Mỹ Lộc t. Nam Định` → `Xóm 5`.
2. **Viết tắt quận:** `xóm 5 q. Ninh Kiều tp. Cần Thơ` → `Xóm 5`.
3. **Bao phủ đủ năm khóa:** unit test tham số hóa helper cho `x.`, `p.`, `q.`, `h.`, `t.` với ngữ cảnh cấp hành chính tương thích; không chỉ kiểm tra `x.`.
4. **Không dấu chấm/không có xác nhận:** `Thôn P. Nam` phải không bị cắt chỉ vì `P.`; `Thôn Phuong Nam xã My Hung ...` không được cắt tại `Phuong` nếu chuỗi cấp sau đó không tương thích với cách hiểu `Phường`.
5. **Telex:** thêm một đầu vào dùng đúng dạng Telex của tiền tố hành chính (ví dụ dạng Telex của `xã`) để bảo đảm helper không làm mất hỗ trợ Telex vốn có.

---

## Thứ tự triển khai đề xuất

1. Xây và kiểm tra logic helper dừng riêng cho `thon_xom`, bao gồm phân biệt bằng chứng hành chính mạnh/yếu và biên BIO trường khác.
2. Dùng helper để giới hạn `b` trong nhánh span CRF (HIGH-01): vừa mở rộng khi cần, vừa cắt khi span đã vượt điểm dừng.
3. Dùng lại helper để tính `j` trong fallback `unknown_candidates` (HIGH-02), chỉ cho `f == 'thon_xom'`.
4. Bổ sung nhận diện viết tắt một chữ cái có dấu chấm và xác nhận ngữ cảnh (HIGH-03).
5. Chạy các test đơn vị dựng BIO/labels trực tiếp trước; sau đó mới chạy test tích hợp mô hình nếu được giao ở nhiệm vụ khác.

## Ranh giới thay đổi

- Dự kiến chỉ sửa `src/tien_xu_ly/crf_chi_tiet.py` khi triển khai.
- Không cần sửa `quy_tac.py`: tránh thay đổi matcher dùng chung.
- Không cần sửa `tach_phan_con.py`: không dùng lại nguyên xi `boundary()` vì nó có ngữ nghĩa riêng và không giải quyết đầy đủ tên riêng trùng tiền tố.
- Không thay đổi `dinh_dang_span()`, `viet_ten()`, tokenizer hoặc logic các trường khác.

**Kết luận thiết kế:** một helper biên dùng chung cho hai nhánh thôn/xóm, có phân biệt độ tin cậy của tiền tố hành chính và không dùng match `CHI_TIET` đơn lẻ làm điểm dừng, là phương án ít xâm lấn nhất. Ba lỗi HIGH có thể được xử lý mà không thay đổi semantics của các trường chi tiết khác; phần không thể phân biệt chắc chắn (ASCII không dấu/chữ viết tắt mơ hồ) phải được xử lý bảo thủ và có test chống cắt nhầm tên riêng.
