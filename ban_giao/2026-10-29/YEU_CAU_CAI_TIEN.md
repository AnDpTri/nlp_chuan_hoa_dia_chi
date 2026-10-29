# Yêu cầu tiếp nhận và cải tiến độc lập

Bạn tiếp nhận một prototype chuẩn hóa địa chỉ Việt Nam có mã nguồn, dữ liệu,
checkpoint, output từng câu và lịch sử thử nghiệm kèm theo.

**Hãy tự đánh giá hướng đi và đề xuất giải pháp của bạn.** Không mặc định
kiến trúc hoặc các kết luận phân tích trước là đúng. Có thể thay một phần
hoặc toàn bộ phương pháp nếu chứng minh được lợi ích và chi phí. Không có
yêu cầu phải nối tiếp một kế hoạch mô hình cụ thể.

## Việc đầu tiên

1. Đọc `HIEN_TRANG.md` và `LICH_SU.md`, sau đó kiểm tra code/output thực.
2. Tái hiện baseline phù hợp trên dữ liệu/hash đã ghim; phân biệt mốc nào
   có fullbenchmark với mốc nào chỉ có parity/refactor.
3. Ghi lại các mâu thuẫn giữa tài liệu, code, nhãn và hành vi mong muốn.
   Không hợp thức hóa nhãn bằng cách bỏ bằng chứng trong input.
4. Phân loại lỗi theo trách nhiệm thực tế của từng tầng, kèm input/reference/
   output. Tách lỗi thuật toán, dữ liệu thiếu/sai và mơ hồ không thể giải từinput.

## Đầu bài không đổi

- Input tự do, có thể trộn cũ/mới, viết tắt, sai dấu, dính chữ và đảo thứ tự.
- Đích mốc01/07/2025; huyện cũ dùng làm bằng chứng, không xuất trong địa chỉ mới.
- Không cần dịch vụLLM/API khi suy luận; ưu tiên vận hànhCPU, tốc độ/tài nguyên
  có trọng số đáng kể bên cạnh chất lượng.
- Không đoán tùy ý xã chia nhiều đích hoặc tên viết tắt nhiều nghĩa.
- Giữ thông tin quan sát được và dấu vết; đừng tăng điểm bằng cách xóa hết
  trường khó hoặc ép tất cả thành một đáp án.

## Cách cải tiến mong muốn

- Đề xuất ít nhất một phương án do bạn tự lập luận, chỉ rõ giả thuyết, phần
  cần dữ liệu gì, chi phí và điều kiện để loại bỏ phương án nếu không hiệu quả.
- Ưu tiên sửa nguyên nhân theo cấu trúc thay vì ngoại lệ ID/địa danh/giá trị
  trong dev. Không khóa vào một họ thuật toán hoặc một kiến trúc sẵn có.
- Nếu cần thêm dữ liệu, xác định loại và căn cứ, không chỉ tăng số dòng.
  Không lấy nhãn test/dev đã xem làm từ điển rồi công bố tổng quát hóa.
- Quyết định đầu ra/nhãn cho thiếu thông tin, mơ hồ và nhiều đích phải được
  mô tả trước khi chọn metric. Không tự thay nhãn/cách chấm mà vẫn gọi cùng
  một benchmark; giữ phép đolegacy để nối lịch sử và thêm metric hợp lý riêng.
- Không cần giữ các chính sách thử nghiệm làm giảm điểm chỉ vì chúng có
  thêm giải thích. Provenance và độ đúng là hai tiêu chí khác nhau.

## Kiểm chứng và báo cáo bắt buộc

- Kết quả trên từng trường và cả địa chỉ, độ phủ tình huống/nguồn/họ;
  nêu rõ mẫu số, nhãn yếu hay gold, seen/unseen và những trường không có mẫu.
- Output từng câu trước/sau, số được/mất, ca không chắc và ví dụ hồi quy.
- Phân tích thay đổi có kiểm soát: đổi nhiều thành phần cùng lúc thì có
  ablation hoặc lý do rõ, không quy mức tăng cho một module chưa tách được.
- Đo latencyCPUmean/P95, RAM, thời gian khởi tạo và giới hạn độ dài; ghi
  máy/luồng/batch/cache để không so sai các môi trường.
- Chia theo nguồn/địa chỉ cha/họ trước tạo biến thể. Giữ tập đánh giá độc lập
  với sửa thuật toán; nếu dùng kết quả để sửa thì đổi trạng thái thành dev.
- Không dùng nhãn400test để tune. Không gọi bộ đó là gold hoàn chỉnh chỉ vì
  schema/validatorPASS. Gói dữ liệu chưa nghiệm thu phải được đánh dấu.
- Giữ checkpoint/data/source cũ và manifest. Mỗi lượt mới vào thư mục riêng;
  không đè báo cáo để viết lại lịch sử.

## Sản phẩm bàn giao lại

1. Nhận định độc lập: hướng cũ đúng/sai/chưa đủ bằng chứng ở đâu.
2. Thiết kế đề xuất và các lựa chọn đã loại, có căn cứ.
3. Code chạy được, lệnh tái hiện và dependency tách môi trường.
4. Dữ liệu/nguồn/manifest và kiểm chứng nếu có thay đổi.
5. Báo cáo đầy đủ cả phương án không thành công và giới hạn còn lại.

Không hứa95% hoặc tốc độ triển khai trước khi có phép đo tương ứng. Mục
tiêu là tăng chất lượng có thể kiểm chứng, không phải bám một con số dev.
