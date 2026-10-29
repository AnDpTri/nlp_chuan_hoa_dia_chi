# Project Engineering Discipline & Scientific Verification Rules

## 1. Kỷ Luật Kỹ Thuật & Đánh Giá Thực Chất
- **Hạn chế ăn mừng, không tuyên bố sớm**: Tuyệt đối không tự mãn, không dùng từ "PASS" hay tuyên bố "đạt độ chính xác cao / hoàn hảo" khi chưa tạo được đột phá thực chất và chưa có bằng chứng định lượng độc lập.
- **Phân biệt kiểm thử cơ học và kiểm chứng ngữ nghĩa**: Việc unit test hay validator chạy qua (`PASS`) chỉ chứng minh không có lỗi cú pháp hoặc vi phạm schema cơ học, không tự trở thành bằng chứng về tính đúng đắn ngữ nghĩa hay chất lượng mô hình.

## 2. Chuẩn Mực Thực Nghiệm & Đo Lường
- **Đối chiếu trên Baseline đóng băng**: Mọi cải tiến, refactor hay thay đổi mô hình phải đo đạc đối chiếu với baseline có hash (SHA-256) dữ liệu và checkpoint được ghi nhận rõ ràng.
- **Báo cáo hai chiều (Đúng thêm / Hồi quy)**: Khi so sánh phiên bản, bắt buộc báo cáo cả hai chiều: số trường hợp đúng thêm và số trường hợp bị sai thêm (hồi quy/regression). Không chỉ đưa ra một tỷ lệ phần trăm tổng quát.
- **Chống Overfitting tập phát triển**: Không được tối ưu điểm số bằng cách bắt ngoại lệ (hardcoding), ép nhãn hay lấy từ vựng/địa danh từ chính tập dev/test để đưa vào từ điển rồi coi đó là khả năng tổng quát hóa.
- **Bảo toàn chi phí tài nguyên**: Điểm số chính xác luôn phải đi kèm đo lường tài nguyên thực tế: độ trễ CPU (Mean/P95 latency), dung lượng RAM và footprint mô hình.

## 3. Minh Bạch Tuyệt Đối Về Giới Hạn & Thất Bại
- **Báo cáo phương án thất bại**: Phải ghi chép và phân tích các phương án không thành công, giải thích rõ nguyên nhân kỹ thuật và điều kiện loại bỏ.
- **Tôn trọng độ mơ hồ nội tại**: Nếu thông tin đầu vào không đủ căn cứ để chọn một đáp án duy nhất (ví dụ xã bị chia tách, tên viết tắt nhiều nghĩa, từ không dấu trùng lặp), phải giữ cờ cảnh báo hoặc danh sách ứng viên, tuyệt đối không đoán mò để lấy điểm số ảo.
