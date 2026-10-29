# Quy trình tự duyệt tập test

Quy ước ngày 29/10/2026, áp dụng cho nhiệm vụ rà soát 400 mẫu trong `data/test`.

## Trách nhiệm thực hiện

Agy thực hiện quá trình đọc mẫu, đối chiếu, tìm kiếm, sửa nhãn, kiểm tra và lập báo cáo trong nhiệm vụ tự duyệt bằng AI.

Mẫu thiếu căn cứ được ghi nhận là chưa xác định, kèm ứng viên, cảnh báo và lý do. Hoàn tất rà soát toàn bộ mẫu không đồng nghĩa xác định được đáp án duy nhất cho mọi mẫu.

Prompt giao việc phải tuân thủ [quy tắc viết prompt](antigravity_rpc/HUONG_DAN_AGY_APP_RPC.md#5-gửi-một-yêu-cầu-mới): không nhắc người dùng, không nhắc Codex hoặc agent gửi tin như cầu nối; giao nhiệm vụ trực tiếp với yêu cầu và tiêu chí hoàn thành cụ thể. Đây là quy tắc diễn đạt prompt, không phải quy định bỏ bước duyệt dữ liệu.

## Cách đối chiếu

- Rà soát từng mẫu, bao gồm cả trạng thái sơ bộ `tu_dong_khop` và `can_duyet`.
- Giữ nguyên `id`, `dau_vao`, `nguon` và bản trích nguồn đã ghim. Chuẩn hóa về mốc 01/07/2025.
- Đối chiếu chuỗi đầu vào với danh mục, quan hệ hành chính, bảng chuyển đổi và nguồn OSM đóng băng. Dùng tool search/web khi cần xác minh; đọc nguồn gốc, ưu tiên văn bản chính thức có mốc hiệu lực phù hợp.
- Ghi nguồn, bằng chứng cụ thể và thời điểm truy cập cho nhận định dựa trên web. Không ghi đã tìm kiếm nếu chưa thực hiện hoặc công cụ không hoạt động.
- Nguồn ngoài phục vụ kiểm chứng cách hiểu và chuyển đổi. Không bổ sung thành phần vắng mặt trong đầu vào chỉ vì tìm được địa điểm tương ứng; chỉ suy ra khi quan hệ danh mục và bằng chứng trong đầu vào đủ xác định.
- Xã cũ nhiều đích hoặc cách hiểu còn mơ hồ phải giữ ứng viên/cảnh báo khi thiếu căn cứ chốt. Không ép nhãn để đạt tỷ lệ hoàn thành.

## Trạng thái và nhật ký

Kết quả duyệt ghi rõ chủ thể là AI và model thực tế, thời gian, nhãn trước/sau, căn cứ, nguồn và vấn đề còn lại. Phân biệt ba kết luận: giữ nguyên, sửa nhãn, chưa đủ căn cứ. Lưu checkpoint để tiếp tục nếu bị gián đoạn.

Metadata duyệt bằng AI phải tách khỏi metadata duyệt bởi người thật. Không giả tên người hoặc tính các dòng AI duyệt vào `human_reviewed`. Các chỉnh sửa hoặc chữ ký người thật đã có phải được bảo toàn; đây là yêu cầu truy vết, không phải bước phê duyệt mới.

Trạng thái AI đã duyệt phải được validator, đồng bộ nhãn và báo cáo hiểu nhất quán. Khi chức năng này chưa được cài đặt xong, không ghi trạng thái giả chỉ để vượt validator. Quy ước này mô tả yêu cầu cần thực hiện, không xác nhận công cụ hoặc việc duyệt đã hoàn tất.

## Kiểm tra và công bố kết quả

Sau khi cập nhật nhãn, kiểm tra bảo toàn đầu vào/nguồn, mã và tên, quan hệ cha con, snapshot, cảnh báo, nhật ký và tính lặp lại của thao tác đồng bộ. Chạy validator trên tập thật sau các phép thử fixture để báo cáo phản ánh dữ liệu cuối cùng.

Báo cáo nêu số mẫu thực sự đã rà soát trên tổng 400, số giữ nguyên/sửa/chưa đủ căn cứ, số đã đối chiếu web, các kiểm tra đã chạy và giới hạn còn lại. Mô tả bộ nhãn đúng là được AI đối chiếu; không suy từ validator PASS hoặc hoàn tất lượt rà soát sang kết luận mọi nhãn đều chính xác.

Tập test và kết quả rà soát được giữ độc lập: không dùng để huấn luyện, chọn luật, chọn ngưỡng hoặc điều chỉnh mô hình. Lõi chuẩn hóa khi chạy vẫn hoạt động offline; search chỉ là công cụ hỗ trợ chuẩn bị và kiểm chứng tập dữ liệu.
