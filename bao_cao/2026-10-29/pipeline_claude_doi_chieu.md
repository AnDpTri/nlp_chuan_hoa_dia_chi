# Pipeline đã bàn trong session Claude

Đọc lại ngày 29/10/2026 từ hai bản session mang tên **NLP - Chuẩn hóa địa chỉ (chính)** trong `C:\Users\andan\.claude\projects\D--nlp-chuan-hoa-dia-chi`. Nội dung trùng được loại khi đối chiếu. Thời gian dưới đây theo giờ Việt Nam (UTC+7).

## 26/10/2026, 00:09 — chọn cấu trúc tìm kiếm

Claude viết:

> Nếu chọn một thì chọn **trie**.

Sau phần giải thích khớp không dấu, tìm gần đúng và chữ cái đầu, Claude kết luận:

> Mỗi nút cuối trong trie trỏ tới các nút tương ứng trong **cây hành chính**. Cây hành chính thì không phải là một lựa chọn, vì đó chính là dữ liệu.
>
> Vậy toàn bộ chỉ gồm **trie + cây hành chính**.

## 26/10/2026, 00:26 — tổng kết thiết kế

Nguyên văn phần tổng kết của Claude:

> - **Pipeline:** tiền xử lý → sinh ứng viên → ghép đường đi hợp lệ trên cây hành chính (giải cả địa chỉ cùng lúc) → tách phần còn lại → chuyển đổi cũ sang mới → sinh đầu ra.
> - **Cấu trúc dữ liệu:** trie + cây hành chính (cũ, mới, có cạnh đối chiếu).
> - **Mô hình nhẹ:** logistic regression để chấm điểm đường đi, CRF để tách số nhà/ngõ/thôn/đường. Sau này có thể nâng lên LightGBM.
> - **Công nghệ:** Python, làm cho chạy được trước rồi mới tối ưu, theo 6 nguyên tắc thiết kế.
> - **Mốc so sánh:** `vietnamadminunits`, `vietnam-address-converter`.

Phần còn để ngỏ trong chính thông điệp này gồm đặc trưng hàm điểm, cách sinh dữ liệu, xử lý xã bị chia, chia việc và tài liệu thiết kế. Số xã bị chia trong thông điệp cũ là 441; con số kiểm tra ở thời điểm tiếp quản là 440.

## Phạm vi đã xác định và điểm chưa mô tả đầy đủ

Trong phần khởi đầu pipeline ngày 25/10/2026, 23:42, Claude nêu câu hỏi:

> Một địa chỉ ghi lẫn cả tên cũ lẫn tên mới thì sao?

Trong mô tả chi tiết sau đó, Claude viết:

> Dò cả cây cũ lẫn cây mới, cây nào cho điểm cao hơn thì địa chỉ ghi theo kiểu đó.

Như vậy session đã xác định bài toán suy luận toàn địa chỉ và có cạnh đối chiếu cũ–mới, nhưng chưa mô tả đầy đủ thuật toán chọn tổ hợp chứa đồng thời thành phần của hai mốc. Không có căn cứ để khẳng định trường hợp trộn đã được giải quyết hoàn chỉnh.

## Đối chiếu khung mã nguồn ngày 29/10/2026

- `src/tim_kiem.py`: trie và sinh ứng viên, mỗi ứng viên giữ đoạn token, mã, cây và kiểu khớp.
- `src/giai_ma.py`: tìm đường đi trên cả cây cũ và mới bằng beam search; bản đầu điểm đặt tay.
- `src/tach_phan_con.py`: tách số nhà/ngõ/thôn/đường, bản đầu dùng luật.
- `src/chuyen_doi.py`: chuyển cũ sang mới, giữ cảnh báo cho xã bị chia.
- `src/chuan_hoa.py`: điểm ghép pipeline.
- `DuongDi` hiện có một trường `cay`, còn các hàm xử lý chính vẫn là `NotImplementedError`.

Kết luận đối chiếu: **đã có thiết kế pipeline và khung giao tiếp giữa các bước; chưa có cài đặt chạy được**. Cần kế thừa thiết kế này và ghi rõ phần bổ sung cho đầu vào trộn mốc, tránh trình bày phần đề xuất mới như nội dung Claude đã hoàn tất.
