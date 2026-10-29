# Rà soát thiết kế chuẩn hóa địa chỉ

Ngày: 29/10/2026. Đối chiếu session Claude **NLP - Chuẩn hóa địa chỉ (chính)**, đặc tả `D:\nlp_chuan_hoa_dia_chi\bai_toan.md` và khung mã nguồn hiện tại. Đây là rà soát thiết kế và đề xuất điều chỉnh; chưa sửa mã nguồn hoặc dữ liệu dự án.

## Kết luận

Giữ kiến trúc Claude đã bàn: **trie sinh ứng viên, hai cây hành chính cùng quan hệ chuyển đổi, chấm điểm toàn địa chỉ, các bước có giao diện rõ ràng**. Chỗ cần thiết kế lại cụ thể là trạng thái giải mã và cách kiểm tra tính tương thích. Một địa chỉ có thể chứa đồng thời thành phần cũ, mới, thiếu cấp, đảo thứ tự và lỗi nhập.

Không yêu cầu người dùng chọn mốc, không phân loại toàn bộ đầu vào thành một mốc trước khi giải mã. Mốc là thuộc tính của từng đơn vị ứng viên. Đầu ra hành chính theo một mốc đích cố định.

## 1. Những phần giữ nguyên

- Nạp danh mục và chỉ mục một lần vào RAM; CSV và dữ liệu nguồn lưu trên đĩa.
- Trie chứa tên và biến thể; một khóa trỏ đến nhiều đơn vị khi trùng tên hoặc viết tắt.
- Các đơn vị liên kết bằng mã kèm mốc; tên chỉ phục vụ so khớp và hiển thị.
- Hai cây lưu quan hệ cha–con trong từng mốc; bảng chuyển đổi nối các mốc.
- Duy trì nhiều cách hiểu và chấm điểm toàn tổ hợp.
- Phiên bản đầu dùng luật và trọng số đặt tay. Logistic regression và CRF được thử sau khi có dữ liệu, phép đo và bản đầu chạy được.
- Giữ dấu vết, cảnh báo và các ứng viên khi không đủ bằng chứng.

## 2. Các điểm cần sửa trước khi cài đặt

| Mức | Vị trí trong khung hiện tại | Vấn đề | Điều chỉnh |
|---|---|---|---|
| Cao | `src/kieu_du_lieu.py:35`, `src/giai_ma.py:16` | `DuongDi.cay` biểu diễn một cây cho cả tổ hợp, chưa mô tả đầy đủ bằng chứng trộn mốc | Trạng thái giả thuyết giữ mốc ở từng ứng viên và tập đích mới còn phù hợp |
| Cao | `src/giai_ma.py:1` | Mô tả đọc phải → trái, tỉnh trước rồi chỉ xét con chưa bao quát đảo thứ tự, thiếu tỉnh hoặc tỉnh gõ sai | Sinh ứng viên trên toàn chuỗi; thứ tự chữ là đặc trưng mềm, không là ràng buộc hành chính |
| Cao | `src/giai_ma.py`, `src/chuyen_doi.py` | Chỉ chuyển đổi sau khi chốt một cây sẽ không dùng được quan hệ chuyển đổi để gỡ nhập nhằng đầu vào trộn | Dùng bảng chuyển đổi trong lúc giải mã; bước cuối vẫn chịu trách nhiệm quyết định đích và cảnh báo |
| Cao | Bước giải mã đề xuất | Cùng một đích mới không chứng minh các thành phần cũ tương thích | Kiểm tra quan hệ cha–con tại mốc nguồn và quan hệ chuyển đổi giữa các mốc |
| Cao | `src/tach_phan_con.py:9` và thứ tự gọi | Chốt hành chính trước rồi tách phần còn lại có thể lấy nhầm tên đường làm xã và không sửa lại được | Tách phần còn lại cho nhiều giả thuyết đang giữ, dùng kết quả chấm lại trước khi chốt |
| Vừa | `src/tien_xu_ly.py:17` | Docstring hứa giữ vị trí gốc nhưng giao diện chỉ trả `list[str]` | Có token mang khoảng ký tự nguồn và các dạng so khớp |
| Vừa | `src/tim_kiem.py:15` | Chỉ mục bỏ dấu và kết quả `(mã, cây, số_lỗi)` chưa đủ để phân biệt khớp có dấu với mất dấu, tiền tố và dạng viết tắt | Giữ dạng tên đã khớp, nguồn biến thể và đặc trưng để tính điểm |
| Vừa | `src/danh_muc.py:19` | Chỉ mô tả chuyển đổi theo xã cũ; dữ liệu còn có nguồn huyện không có xã | Quan hệ chuyển đổi có mã/cấp nguồn rõ ràng, cho phép nguồn cấp huyện theo bản ghi có thật |
| Vừa | `src/chuyen_doi.py:11`, `src/kieu_du_lieu.py:44` | Đầu ra chưa có trường riêng cho các xã ứng viên, phần chưa hiểu và dấu vết | Kết quả có cấu trúc để giữ các nội dung này, ngoài danh sách mã cảnh báo |

Đây là thiếu sót của hợp đồng và mô tả thiết kế; các hàm chính đang là khung nên chưa có lỗi thực thi để đo bằng chạy pipeline.

## 3. Bẫy cần tránh: chỉ so đích mới là chưa đủ

Kiểm tra trực tiếp các CSV hiện tại cho thấy:

- Xã/phường cũ mã `00004`: Phường Trúc Bạch, thuộc Quận Ba Đình (`001`), Hà Nội (`01`).
- Phường mới mã `00004`: Phường Ba Đình, Hà Nội.
- Bảng đối chiếu nối Trúc Bạch cũ với Ba Đình mới.
- Phường Ba Đình mới cũng có nguồn từ các xã/phường thuộc Quận Tây Hồ cũ (`003`).

Với đầu vào thử thiết kế `phường Trúc Bạch, quận Tây Hồ, Hà Nội`, cả hai thành phần có thể cùng liên hệ tới phường Ba Đình mới, nhưng quan hệ cũ **Trúc Bạch thuộc Tây Hồ** vẫn sai theo danh mục.

Vì vậy phải phát hiện xung đột nguồn. Có thể giữ một kết quả tốt nhất theo quy tắc đặc tả, nhưng phải kèm cảnh báo và phần bằng chứng mâu thuẫn. Không được coi địa chỉ này là hoàn toàn nhất quán chỉ vì có giao giữa các tập đích mới.

Ngược lại, `phường Ba Đình, quận Ba Đình, Hà Nội` có thể là đầu vào trộn mốc hợp lệ. Chỉ sự xuất hiện đồng thời tên mới và huyện cũ không phải là lỗi.

## 4. Pipeline sau điều chỉnh

```text
Chuỗi nguyên văn
    ↓
Chuẩn hóa phục vụ so khớp, token có vị trí nguồn
    ↓
Sinh nhiều ứng viên trên toàn chuỗi, từ cả hai mốc
    ↓
Giải mã các tổ hợp tương thích:
  - không dùng chồng lấn một đoạn chữ
  - quan hệ cha–con tại mốc nguồn
  - quan hệ chuyển đổi giữa các mốc
  - cho phép thiếu cấp, thứ tự bất kỳ và bằng chứng xung đột
    ↓
Với các giả thuyết còn giữ: tách số nhà/ngõ/thôn/đường
    ↓
Chấm lại theo toàn bộ bằng chứng, nhóm theo kết quả đích
    ↓
Quyết định phần xác định được, phần còn nhập nhằng
    ↓
Ghép tên chuẩn + cảnh báo + ứng viên + dấu vết
```

Đây là điều chỉnh bên trong kiến trúc cũ. Không cần thêm một mô hình lớn hoặc một loại cây tìm kiếm khác.

### Trạng thái giải mã

Đề xuất thay trạng thái chỉ có một `cay` bằng một giả thuyết gồm:

- Các ứng viên đã chọn; mỗi ứng viên có khoảng token, mã, cấp và mốc.
- Các khoảng token đã dùng.
- Quan hệ nguồn được kiểm chứng và các mâu thuẫn phát hiện được.
- Các đích mới có thể tương ứng, kèm quan hệ làm bằng chứng.
- Các phần chưa giải thích hoặc đang có nhiều cách phân loại.
- Điểm và các thành phần đóng góp vào điểm.

Quan hệ cha–con và chuyển đổi là ràng buộc của một cách hiểu nhất quán. Khi đầu vào có lỗi, thuật toán được giữ giả thuyết không sử dụng một phần bằng chứng, nhưng phải ghi nhận phần bị loại và xung đột liên quan. Không xóa mọi bằng chứng bất tiện để tạo cảm giác chắc chắn.

Không cần khẳng định một mã xã cũ chỉ vì đã biết xã mới: nhiều xã cũ có thể cùng vào một xã mới. Suy luận ngược qua bảng chuyển đổi chỉ tạo các ứng viên nguồn, không chứng minh nguồn duy nhất.

### Cách tìm và chấm điểm

- Xây giả thuyết từ những ứng viên có bằng chứng tốt, không bắt buộc bắt đầu từ tỉnh hoặc cuối chuỗi. Dùng beam search để kiểm soát số nhánh; độ rộng beam cần đo trên tập phát triển.
- Điểm dựa trên độ khớp, bằng chứng tiền tố, ngữ cảnh, mức giải thích chuỗi và xung đột. Không thưởng mặc định cho cây cũ chỉ vì có thêm cấp huyện.
- Một đoạn chữ có nhiều biến thể khớp cùng đơn vị chỉ được tính một lần bằng chứng; không cộng điểm lặp do nhiều đường sinh ứng viên.
- Không loại mọi ứng viên gần đúng chỉ vì tồn tại một khớp chính xác cục bộ. Nếu khớp chính xác không tạo được tổ hợp phù hợp, cần có cơ chế mở rộng ứng viên.
- Không kết luận đã biết tỉnh rồi khóa cứng tìm kiếm vào một tỉnh nếu chính ứng viên tỉnh còn yếu.
- Nhóm những giả thuyết cho cùng kết quả đích để tránh báo nhập nhằng giả chỉ vì có nhiều cách giải thích mốc nguồn. Những đích khác nhau vẫn phải được giữ khi chưa đủ bằng chứng.
- Chênh lệch điểm và độ mạnh bằng chứng là tín hiệu cảnh báo. Điểm đặt tay không phải xác suất; đầu ra logistic cũng cần kiểm chứng độ tin cậy trước khi gọi là tỷ lệ chắc chắn.

### Quyết định đầu ra

- Xã mới được nhận diện rõ: giữ mã mới, không dùng cùng chuỗi mã để tra tiếp như mã xã cũ.
- Xã cũ có một đích: chuyển theo bảng, kiểm tra tương thích với phần còn lại.
- Xã cũ có nhiều đích: giữ tập ứng viên. Có thể dùng tên xã mới được ghi rõ trong cùng đầu vào hoặc dữ liệu đối chiếu địa phương để thu hẹp; quan hệ chuyển đổi phải cho phép kết hợp đó.
- Thiếu thông tin giải quyết xã bị chia: để trống xã đích, giữ tỉnh nếu xác định được, trả `xa_bi_chia` và các xã đích ứng viên.
- Tỉnh có thể lấy từ quan hệ cha đã xác định duy nhất của xã/huyện, nhưng phải ghi dấu vết suy ra; không coi đó là tỉnh người dùng đã ghi. Khi không có bằng chứng xác định, để trống.
- Không có ứng viên đáng tin: vẫn trả phần số nhà/ngõ/đường phân tích được, phần chưa hiểu và cảnh báo; không ép phải chọn một xã.
- Tên đường/thôn thiếu dấu không tự phục hồi chắc chắn chỉ nhờ danh mục hành chính. Giữ bằng chứng và cảnh báo khi không có nguồn tra phù hợp.

## 5. Điều chỉnh giao diện từng module

| Module | Nội dung giữ | Nội dung cần bổ sung |
|---|---|---|
| `kieu_du_lieu.py` | `DonVi`, `UngVien`, kết quả có cấu trúc | Token có vị trí, giả thuyết trộn mốc, quan hệ chuyển đổi có cấp nguồn, kết quả có ứng viên/dấu vết |
| `danh_muc.py` | Bảng đơn vị và chỉ mục con | Tra cha/quan hệ tổ tiên, quan hệ chuyển đổi có căn cứ, đích có thể tương ứng của từng cấp; các chỉ mục nạp một lần |
| `tien_xu_ly.py` | Chuẩn hóa Unicode và dạng tìm kiếm | Giữ chuỗi gốc, dấu câu và ánh xạ vị trí; giữ `/` và ký hiệu có ý nghĩa |
| `tim_kiem.py` | Trie và sinh ứng viên | Nhiều mốc cho mỗi span, metadata dạng khớp, cơ chế mở rộng tìm gần đúng khi giải mã thất bại |
| `giai_ma.py` | Tìm kiếm có giới hạn và điểm có thể thay thế | Giả thuyết trộn mốc, thứ tự không cố định, kiểm tra nguồn lẫn đích, giữ nhiều phương án |
| `tach_phan_con.py` | Luật trước, mô hình sau | Làm việc trên từng giả thuyết, giữ chữ gốc và phương án phân loại chưa chắc để chấm lại |
| `chuyen_doi.py` | Quyết định đầu ra theo mốc đích | Cho bước giải mã dùng chung phép kiểm tra tương thích; giữ đủ đích ứng viên và căn cứ |
| `chuan_hoa.py` | Điểm vào cho một chuỗi | Điều phối các bước, mở rộng ứng viên có giới hạn, chấm lại và sinh cảnh báo |

Không cần tạo một hệ chỉ mục mới cho mỗi mốc đầu vào dự đoán; mốc đầu vào không được biết trước. Cần đo để quyết định dùng trie chung, chỉ mục con hoặc bộ lọc theo phạm vi.

## 6. Các ca phải có khi triển khai

Các ví dụ dưới đây là ca kiểm tra thiết kế, không phải bổ sung nhãn vàng cho tập test 400 địa chỉ.

| Ca | Điều cần kiểm chứng |
|---|---|
| Toàn tên cũ | Nhận đúng cây nguồn, dùng huyện, chuyển theo bảng |
| Toàn tên mới | Giữ đúng mã đích, không chuyển đổi lần hai |
| Phường mới + huyện cũ | Sử dụng được bằng chứng trộn mốc nếu các quan hệ phù hợp |
| Xã cũ + tỉnh mới | Dùng đối chiếu để xác định tương thích |
| Đảo thứ tự các thành phần | Kết quả không phụ thuộc quy tắc đọc phải → trái |
| Thiếu tỉnh hoặc thiếu huyện | Giữ được ứng viên từ cấp khác; không đoán khi còn trùng tên |
| Tên đồng thời là đường và đơn vị hành chính | Không chốt hành chính trước khi đánh giá cách tách phần còn lại |
| Tên dùng được ở cả hai mốc | Cùng đích thì gộp; khác đích thì giữ nhập nhằng |
| Xã bị chia + thiếu bằng chứng | Xã đích trống, có ứng viên và cảnh báo |
| Xã bị chia + tên xã mới tương thích được ghi rõ | Có thể thu hẹp bằng chứng mà không tự chọn bừa |
| Trúc Bạch cũ + Tây Hồ cũ | Phát hiện mâu thuẫn nguồn dù có thể cùng liên hệ tới một đích mới |
| Tên tỉnh sai, xã/huyện rõ hơn | Không khóa tìm kiếm theo tỉnh yếu; có cảnh báo mâu thuẫn |
| Huyện đảo không có xã cũ | Áp dụng đúng bản ghi chuyển đổi có nguồn cấp huyện |
| Chỉ có đường/số nhà hoặc chuỗi rỗng | Không tự điền hành chính; trả phần xác định được |
| Số nhà có `/` | Bảo toàn nguồn, áp dụng quy tắc đã công bố và cảnh báo khi còn mơ hồ |

Quy tắc `12/5 → Số 12, Ngõ 5` hiện được ghi trong đặc tả, trong khi tập dữ liệu từng giữ số nhà có `/` để duyệt. Cần thống nhất quy tắc này trong dữ liệu và đầu ra trước khi đánh giá; không âm thầm đổi cách hiểu ở bước tiền xử lý.

## 7. Thứ tự triển khai đề xuất

1. Chốt các hợp đồng dữ liệu và phép kiểm tra tương thích bằng các ca trên.
2. Nạp danh mục, dựng trie và quan hệ chuyển đổi từ dữ liệu đã kiểm tra mốc.
3. Làm tìm kiếm chính xác/không dấu/viết tắt cùng giải mã đặt điểm tay; đo riêng khả năng sinh được đáp án và khả năng chọn đúng.
4. Tách phần còn lại và chấm lại các giả thuyết, hoàn thiện đầu ra và dấu vết.
5. Bổ sung tìm gần đúng có giới hạn, đo tác động đến recall và tốc độ.
6. Đánh giá trên tập phát triển riêng, rồi mới thử các mô hình nhẹ. Tập đánh giá cuối phải được duyệt và giữ độc lập.

Chưa cần cache kết quả hoặc cây/trie nén để xác lập tính đúng của thiết kế. Các tối ưu đó thực hiện sau khi đo thời gian nạp, RAM, số ứng viên và độ trễ xử lý.
