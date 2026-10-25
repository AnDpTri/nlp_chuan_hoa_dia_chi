# Đặc tả bài toán

**Đề tài:** Xây dựng hệ thống chuẩn hóa địa chỉ tiếng Việt theo đơn vị hành chính mới sau sáp nhập 2025

Tài liệu này mô tả hệ thống phải làm gì. Cách làm (kiến trúc, mô hình) do người thiết kế đề xuất.

---

## 1. Hệ thống làm gì

Nhận vào một chuỗi địa chỉ tiếng Việt do người dùng nhập tự do, trả ra địa chỉ đã chuẩn hóa: tách đúng từng thành phần, viết đúng tên chính thức, theo đơn vị hành chính sau ngày 1/7/2025 (34 tỉnh, chỉ còn cấp tỉnh và cấp xã, không còn cấp huyện).

Địa chỉ ghi theo địa giới cũ phải được chuyển đổi đến **cấp sâu nhất** (tỉnh và xã/phường), triệt để trong giới hạn dữ liệu đối chiếu có sẵn.

## 2. Đầu vào

Một chuỗi địa chỉ, có thể gặp:
- Không dấu hoặc sai dấu: `cau giay`, `Cầu Giâý`
- Sai chính tả, lỗi gõ
- Viết tắt: `HN`, `TP.HCM`, `Q.`, `P.`, `ng.`, `kp`
- Lộn thứ tự, thiếu dấu phẩy
- Ghi theo địa giới cũ (còn quận/huyện, tên xã cũ, tên tỉnh cũ)
- Thiếu thành phần (không ghi tỉnh, không ghi số nhà…)

Hệ thống phải xử lý được cả **một địa chỉ** lẻ và **một file nhiều địa chỉ** (CSV/Excel).

## 3. Đầu ra

Với mỗi địa chỉ, trả về:

| Trường | Ý nghĩa |
|---|---|
| `so_nha` | Số nhà |
| `ngo_ngach_hem` | Ngõ, ngách, hẻm, kiệt |
| `thon_xom` | Thôn, xóm, ấp, bản, tổ dân phố, khu phố |
| `duong` | Tên đường, phố |
| `xa_phuong` | Tên xã/phường/đặc khu chính thức (sau sáp nhập) |
| `tinh` | Tên tỉnh/thành phố chính thức (sau sáp nhập) |
| `dia_chi_chuan` | Địa chỉ đầy đủ ghép lại theo đúng thứ tự |
| `canh_bao` | Danh sách cờ báo vấn đề (xem mục 4) |

## 4. Quy tắc

1. **Thiếu thì để trống.** Không có thông tin thì để trống trường đó, không đoán bừa.
2. **Không chắc thì gắn cờ.** Có thông tin nhưng không xác định được chắc chắn (ví dụ tên trùng ở nhiều nơi) thì vẫn trả kết quả tốt nhất nhưng thêm cờ vào `canh_bao`.
3. **Cấp huyện chỉ dùng để xác định, không xuất ra.** Đầu vào có quận/huyện thì phải nhận diện được và dùng nó để xác định đúng xã/tỉnh (nhiều xã cũ trùng tên, chỉ phân biệt được nhờ huyện). Đầu ra không có cấp huyện.
4. **Tỉnh cũ đổi sang tỉnh mới.** Mỗi tỉnh cũ được gộp nguyên vào đúng một tỉnh mới.
5. **Xã/phường cũ đổi sang xã/phường mới.**
   - Xã cũ được gộp nguyên vào một xã mới: đổi thẳng.
   - Xã cũ bị chia ra nhiều xã mới: dùng thôn/xóm, tên đường để xác định xã mới, nếu dữ liệu đối chiếu cho phép.
   - Dữ liệu không đủ để quyết định: gắn cờ `xa_bi_chia`, kèm danh sách các xã mới có thể là đáp án.
6. **Những phần không đổi theo luật:** số nhà, ngõ/ngách/hẻm, thôn/xóm/ấp/tổ dân phố, tên đường. Chỉ chuẩn hóa cách viết: `12/5` thành `Số 12, Ngõ 5`, `ng.` thành `Ngõ`, viết hoa đúng.

## 5. Ví dụ

| Đầu vào | Đầu ra mong muốn |
|---|---|
| `12 ngo 5 tran thai tong cau giay hn` | Số 12, Ngõ 5, Đường Trần Thái Tông, Phường Cầu Giấy, Thành phố Hà Nội |
| `xom 3, xa A, huyen B, Thai Binh` *(địa chỉ cũ)* | Xóm 3, Xã [xã mới mà xã A được gộp vào], Tỉnh Hưng Yên. Huyện B được dùng để xác định đúng xã A, không xuất ra |
| `xom 3, xa C, huyen D, tinh E` *(xã C bị chia, dữ liệu không đủ)* | Xóm 3, `xa_phuong` để trống, `tinh` = tỉnh mới; `canh_bao` = `xa_bi_chia` kèm các xã mới có thể là đáp án |
| `duong Le Loi` | Chỉ điền `duong`, các trường khác để trống; `canh_bao` = thiếu xã, thiếu tỉnh |

## 6. Phạm vi

**Làm**
- Tách và chuẩn hóa tất cả các trường ở mục 3.
- Chuyển địa chỉ cũ sang mới đến cấp xã/phường, theo quy tắc 3 đến 5.

**Không làm**
- Địa chỉ nước ngoài.
- Địa chỉ mô tả kiểu "gần chợ", "đối diện trường": phần đó bỏ qua, không phân tích.
- Kiểm tra số nhà có tồn tại thật hay không.
- Định vị tọa độ, bản đồ.

## 7. Ràng buộc

- Chạy offline trên máy, **không dùng LLM, không gọi API bên ngoài**.
- Tốc độ là tiêu chí quan trọng ngang độ chính xác.
- Phương pháp không bị giới hạn. Người thiết kế tự chọn và giải thích vì sao chọn.

## 8. Dữ liệu có thể dùng

- **Danh mục hành chính hiện hành** (tỉnh, xã/phường): dùng để tra tên chính thức. Lấy bản mới nhất, ghi ngày lấy.
- **Bảng đối chiếu cũ sang mới** (tỉnh, huyện, xã/phường): dùng cho quy tắc 3 đến 5. Mức độ chi tiết của bảng này quyết định chuyển đổi được triệt để đến đâu.
- **Không có sẵn bộ địa chỉ gán nhãn để đánh giá.** Phải tự tạo. Tập kiểm tra cuối cần có địa chỉ thật do nhóm tự gom.

## 9. Đánh giá

- **Độ chính xác:** tỷ lệ đúng của từng trường, và tỷ lệ địa chỉ đúng hoàn toàn.
- **Chuyển đổi cũ sang mới:** tỷ lệ địa chỉ cũ được đổi đúng, và tỷ lệ phải gắn cờ `xa_bi_chia`.
- **Tốc độ:** số địa chỉ/giây, độ trễ mỗi địa chỉ, tài nguyên cần để chạy.
