# Bàn giao dự án chuẩn hóa địa chỉ

Ngày tiếp quản: **29/10/2026**, giờ Việt Nam. Dự án làm việc: `D:\nlp_chuan_hoa_dia_chi`.

## 1. Bối cảnh đã đọc

- Hai bản lịch sử Claude Code cùng tên **NLP - Chuẩn hóa địa chỉ (chính)**: session `6dcac78f-0148-41f2-b648-5f796922daba` và `864928ef-b8a6-4310-b6cd-3dc878f464dd`, lưu trong `C:\Users\andan\.claude\projects\D--nlp-chuan-hoa-dia-chi`. Hai bản có nhiều nội dung trùng nhau; phần tiếp nối có trao đổi đến sáng 26/10/2026 giờ Việt Nam.
- Chat Codex **Tiếp tục session NLP chuẩn hóa địa**, ID `01a17393-8b28-7692-badf-924f5b2b6d2d`: thu thập danh mục, làm sạch qua agy, giải thích chênh lệch số huyện, xây tập 400 địa chỉ và push commit `de2d41c`.
- Đã đối chiếu với đặc tả, README, báo cáo tuần 3, toàn bộ module `src/`, tài liệu/script dữ liệu và trạng thái Git hiện tại.

Các đoạn lịch sử là bối cảnh ra quyết định. Các con số hiện trạng dưới đây được kiểm tra lại từ file trên máy.

## 2. Mục tiêu và cách phối hợp

Đề tài môn NLP, lớp KHMT K22A: nhận địa chỉ tiếng Việt nhập tự do, xử lý thiếu dấu, viết tắt, lỗi gõ, thứ tự lộn xộn và địa giới cũ; xuất địa chỉ theo **mốc 01/07/2025**, đến cấp xã/phường trong giới hạn dữ liệu đối chiếu.

- Hệ thống chạy offline, không dùng LLM hoặc API khi chuẩn hóa. Việc trước đây dùng agy/Gemini để chuẩn bị dữ liệu là bước riêng.
- Chuẩn hóa là mục tiêu chính. Cấp huyện cũ giúp xác định địa chỉ, không xuất trong kết quả mới.
- Thiếu thông tin thì để trống; nhập nhằng thì cảnh báo. Xã cũ bị chia mà thiếu bằng chứng thì giữ các xã mới ứng viên, không tự chốt.
- Số nhà, ngõ, thôn/xóm, đường được tách và chuẩn hóa cách viết. Việc xác nhận một địa chỉ có tồn tại không, hoặc định vị bản đồ, nằm ngoài phạm vi đặc tả.
- Người dùng muốn tự học, hiểu và tham gia thiết kế; từng yêu cầu không khóa cứng phương pháp. Khi tiếp tục cần giải thích quyết định và làm theo phần được giao, giữ không gian tự học của nhóm.
- Ưu tiên cách viết trực diện, rõ trạng thái đã làm/chưa làm, đủ bằng chứng trước khi khẳng định dữ liệu đúng và đủ.

## 3. Hiện trạng đã kiểm tra

| Hạng mục | Kết quả |
|---|---|
| Danh mục mới | 34 tỉnh/thành, 3.321 xã/phường/đặc khu |
| Danh mục cũ | 63 tỉnh/thành, 696 huyện, 10.033 xã |
| Đối chiếu cũ → mới | 10.569 dòng, 440 xã cũ có nhiều đích |
| Tập địa chỉ thử nghiệm | 400 dòng; 168 `tu_dong_khop`, 232 `can_duyet`, 0 `da_duyet` |
| Nguồn đầu vào thử nghiệm | 150 `addr:full` nguyên văn, 250 ghép từ thẻ OSM |
| Phủ địa lý trong nhãn | 32/34 tỉnh/thành mới |
| Dữ liệu OSM dự phòng trên máy | 31.374 dòng, 27.089 chuỗi khác nhau sau chuẩn hóa |
| Mã nguồn hệ thống | 15 hàm/phương thức vẫn ném `NotImplementedError` |
| Chấm điểm và thư viện mốc | Chỉ có README kế hoạch, chưa có script |
| Huấn luyện | Chưa có tập train hoặc mô hình đã huấn luyện trong repo |

Kiểm tra khóa chính, khóa tham chiếu, quan hệ cha con của danh mục và bao phủ mã xã trong bảng chuyển đổi không phát hiện lỗi ở các phép kiểm tra đã chạy. Mỗi tỉnh cũ có một tỉnh mới đích trong bảng.

Đã chạy lại validator hiện có cho tập 400 địa chỉ, chuyển file báo cáo sang thư mục làm việc của chat để giữ nguyên dữ liệu dự án. Kết quả **PASS**, hash CSV khớp báo cáo lưu trước đó. PASS này kiểm tra cấu trúc, nguồn và tính nhất quán theo danh mục; chưa chứng minh nhãn ngữ nghĩa đúng.

Kho OSM còn chứa các bản trùng của đầu vào test: **457 dòng** khớp với **400 chuỗi test** sau chuẩn hóa. Loại toàn bộ các chuỗi này sẽ còn **26.689 chuỗi khác nhau** làm nguồn tiềm năng cho train/dev; chúng chưa phải dữ liệu huấn luyện đã gán nhãn.

## 4. Hướng thiết kế đang có

Luồng dự kiến:

`tiền xử lý → sinh ứng viên bằng trie → ghép đường đi hợp lệ trên cây hành chính → tách số nhà/ngõ/thôn/đường → chuyển cũ sang mới → kết quả và cảnh báo`

Ý tưởng nhóm đã trao đổi là xét các thành phần cùng nhau theo quan hệ tỉnh–huyện–xã, thay vì sửa từng tên độc lập. Có hai cây hành chính cũ/mới cùng cạnh đối chiếu. Mã đơn vị phải đi kèm mốc cũ/mới vì cùng một mã có thể mang tên khác nhau qua hai mốc.

Phiên bản đầu dự kiến dùng luật và điểm đặt tay. Logistic regression cho điểm đường đi, CRF cho phần tách còn lại và LightGBM là các hướng đã bàn, chưa được cài đặt hay chứng minh bằng thực nghiệm.

## 5. Việc cần xử lý tiếp

1. **Sửa mốc loại tỉnh ở nguồn sinh dữ liệu sạch.** `data/clean/moi_tinh.csv` hiện có 9 dòng `Thành phố`, 25 dòng `Tỉnh`. Ba mã `22`, `24`, `75` (Quảng Ninh, Bắc Ninh, Đồng Nai) lệch với bảng mốc 2025 trong workbook đã lưu. Script làm sạch đang lấy loại trực tiếp từ `current-provinces.json`. Tập test có lớp `asof_2025.py` sửa loại đích khi tra cứu, nhưng danh mục sạch chưa được sửa. Cần sửa script, sinh lại các bảng liên quan và bổ sung kiểm tra mốc.
2. **Quản lý phiên bản tập test khi sửa danh mục.** Sáu bảng sạch được ghim SHA-256 trong `data/test/catalogue_manifest.json`; sửa chúng sẽ khiến bước tái lập từ chối chạy. Cần rà ảnh hưởng, ghi thay đổi phiên bản và cập nhật manifest có chủ đích, tránh làm đáp án đổi âm thầm.
3. **Duyệt nhãn và thống nhất quy tắc.** Cả 400 dòng đều cần người duyệt, kể cả 168 dòng tự khớp. Ưu tiên 232 dòng có nghi vấn và duyệt chéo một phần. Validator hiện chỉ chấp nhận hai trạng thái sơ bộ và ghi cứng số dòng duyệt là 0; khi đưa vào quy trình duyệt thật cần cập nhật validator cùng metadata người/ngày duyệt.
4. **Tách tập phát triển khỏi tập đánh giá cuối.** Dùng train/dev hoặc ca kiểm tra riêng để sửa thuật toán. Không dùng tập đánh giá cuối để chọn trọng số, kiểu lỗi sinh hoặc mô hình. Loại trùng theo chuỗi chuẩn hóa và nguồn khi lấy kho OSM còn lại làm dữ liệu.
5. **Viết phần đo trước khi so sánh.** Chấm từng trường, tỷ lệ đúng toàn bộ, chuyển đổi cũ–mới, xử lý xã bị chia và tốc độ. Chỉ công bố điểm cuối khi nhãn đã được duyệt. Các thư viện mốc từng được đề xuất là `vietnamadminunits` và `vietnam-address-converter`; cần kiểm tra khả năng và phiên bản khi thực sự triển khai.
6. **Làm bản đầu chạy được theo phần nhóm giao.** Bắt đầu từ nạp danh mục và các hợp đồng dữ liệu. Cần bổ sung cách trả danh sách xã ứng viên và dấu vết quyết định vì `KetQua` hiện chưa có trường riêng cho hai nội dung này. Thuật toán cũng cần xét thiếu tỉnh, thứ tự lộn xộn và nhập nhằng mốc cũ/mới.

Các ghi chép cũ có con số 10.571 quan hệ hoặc 441/442 xã bị chia. Trạng thái file hiện tại là **10.569 quan hệ, 440 xã bị chia**. Có tài liệu làm sạch còn sót con số cũ; khi chỉnh tài liệu cần thống nhất lại.

## 6. Git và phạm vi tiếp quản lần này

- Nhánh `main`, commit hiện tại `de2d41c`. Trạng thái so với remote ở đây dựa trên ref cục bộ; chưa fetch trong lần đọc này.
- Thay đổi có sẵn trước khi tiếp quản: `bao_cao_tuan_3.md` đang sửa, `bao_cao_tuan_3.docx` và `prompts/` chưa được Git theo dõi.
- Lần tiếp quản này đọc lịch sử, kiểm tra và ghi bàn giao; không chỉnh mã nguồn hoặc dữ liệu dự án, không commit/push hay gửi tin sang chat khác.
- Chưa đối chiếu mới với văn bản hoặc dịch vụ bên ngoài. Các mô tả nguồn và mốc là bối cảnh của dự án, cần kiểm chứng nguồn khi xử lý sửa dữ liệu cụ thể.

Điểm tiếp tục phù hợp: xử lý nhất quán mốc dữ liệu, chuẩn bị quy trình duyệt/đánh giá và trao đổi từng phần triển khai với nhóm.
