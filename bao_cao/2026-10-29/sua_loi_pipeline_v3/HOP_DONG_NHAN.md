# Hợp đồng nhãn phục vụ chuẩn hóa và huấn luyện

Quy ước áp dụng khi rà dữ liệu cho pipeline v3. Tài liệu này không tự thay đổi CSV hoặc xác nhận nhãn máy hiện tại là đúng.

## Phân biệt chữ quan sát và kết quả chuẩn

- Span/BIO mô tả chữ thực sự có trong input, giữ offset về chuỗi gốc, không chèn tên đầy đủ vào span viết tắt.
- Tên/mã hành chính chuẩn lấy từ danh mục mốc đích 01/07/2025 sau khi kiểm tra nguồn và chuyển đổi. Tên đích có thể không xuất hiện nguyên văn trong input.
- Mở viết tắt hoặc phục hồi dấu tên riêng cần nguồn tra và ngữ cảnh; tên suy đoán chưa được xác minh không thành nhãn chuẩn chắc chắn.
- Phần không thuộc bốn nhóm chi tiết hoặc chưa hiểu được giữ `O`/phần chưa phân loại. Không bắt buộc mọi token có vai trò địa chỉ.

## Bốn trường chi tiết

1. **Số nhà:** giữ cụm chữ/số đã nhập. `24B-24`, `12/5`, `1031F;1031G` chưa được tự diễn giải thành danh sách nhà, ngõ hoặc khoảng số. Không dùng số nằm trong tên đường làm số nhà. Giữ cờ cần duyệt khi cấu trúc chưa rõ.
2. **Ngõ/ngách/hẻm/kiệt:** span riêng, không dùng lại chính đoạn này trong nhãn đường. Ngõ có tên cần quy ước và nguồn tên chính thức khi có thể được dùng như tên đường; không tự áp một cách cho mọi địa bàn.
3. **Thôn/xóm/ấp/bản/khu phố/tổ:** giữ riêng với đường. Không chép cùng đoạn thôn hoặc tổ vào đường để lấp trường trống.
4. **Đường/phố/quốc lộ/tỉnh lộ/xa lộ/đại lộ:** giữ loại đã ghi rõ, không tự thêm `Đường` trước `Xa lộ`. Khi input không có loại, nhãn tên/loại chính thức cần nguồn; cách suy từ vị trí sau số nhà là một giả thuyết có cảnh báo.

Span cho mô hình CRF một nhãn/token phải không chồng giữa bốn trường. Nếu cách gán cần lồng nhãn, phải đưa ra ngoài tập BIO hiện tại để rà hợp đồng, không lấy một cách gán tùy ý. So khớp nội dung thành công chưa đủ xác nhận vai trò.

Cụm như lô/tập thể/căn hộ/khu dân cư không tự biến thành đường. Nếu nguồn đáng tin xác nhận cả cụm là tên đường thì có thể gán đường, kèm nguồn; hiện chưa có nguồn ấy trong bộ tra runtime.

## Hành chính cũ, mới và nhập nhằng

- Một chuỗi có thể trộn các mốc. Mỗi đơn vị mang mốc và mã riêng; huyện cũ là bằng chứng, không xuất trong địa chỉ đích.
- Hai tên khớp chính xác vẫn có thể là các đơn vị khác nhau ở hai mốc. Không lấy mốc ẩn từ bộ sinh tổng hợp làm thông tin hệ thống được phép biết.
- Xã cũ nhiều đích chưa được chọn một xã mới chỉ bằng cấp tỉnh/huyện nếu không có bằng chứng địa bàn đủ phân biệt.
- Khi còn nhiều cách hiểu hợp lệ, ghi tập đích chấp nhận và lý do mơ hồ trong hồ sơ duyệt; kết quả có thể để trống trường chưa xác định và giữ ứng viên. Không dùng nhãn một đích tùy ý để ép mô hình học.
- Tách rõ trường trống vì thiếu input, vì chưa đối chiếu được, vì chia địa bàn hoặc vì nhiều cách hiểu. Trường trống đơn lẻ không chứng minh mọi output điền vào đều sai.
- Nếu bằng chứng tự mâu thuẫn, giữ dấu vết phần bị bỏ và cảnh báo. Nhánh bỏ một cấp để khớp nhãn không tự trở thành nhánh đúng.

Tập đích chấp nhận/lý do nêu trên là yêu cầu cho hồ sơ duyệt tiếp theo; schema train/dev cũ chưa được di trú trong lượt sửa lõi này.

## Cách đo

Giữ phép đo khớp sáu trường hiện tại để so sánh các phiên bản trên cùng dữ liệu, không lặng lẽ đổi nhãn hoặc cách chấm. Ghi riêng lỗi ranh giới/vai trò, nội dung tên, dấu, loại đường, mã đích và quyết định mơ hồ. Chỉ số có tính trường trống phải đi kèm tỷ lệ trên phần có nhãn và phần hệ thống quyết định điền.

Chất lượng span và chuẩn hóa đích được kiểm tra riêng. Mẫu chưa đủ căn cứ có thể dùng phần span đã xác minh nhưng chưa được dùng làm nhãn chắc chắn cho xếp hạng đích. Chia tập theo địa chỉ gốc trước khi tạo biến thể; giữ test cuối độc lập với sửa luật và huấn luyện.
