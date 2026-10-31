# Kiểm tra nhánh agy ngày 30/10/2026

Hội thoại: Vietnamese Address Normalization Project Research; ID f2fe9c81-aa94-41f7-a1c7-cbdfb9de557b. Git hiện tại: feature/reach-95-accuracy, HEAD 9dd0376. Đây là kiểm tra log và mã nguồn, không chạy lại benchmark, không đọc thêm nội dung các mẫu test.

## Kết quả có bằng chứng

- RPC báo IDLE; lịch sử có 4.054 bước, 852 bước runCommand. Một bước generic cuối còn trạng thái RUNNING; chưa đủ căn cứ nói mọi tiến trình con đều đã kết thúc.
- Đã train Char-CNN v2: 5.768 mẫu, 12 epoch, 325,48 giây CPU, 351.310 tham số (training.json).
- So sánh cuối: train_da_loc 1.130/1.183 = 95,52%; dev gốc 937/1.136 = 82,48%. Cả hai baseline/candidate +0/-0. Tập train đã lọc không phải test độc lập.
- Log bước 3954 thực sự in tổng test 286/400 = 71,50%, sau đó script lỗi KeyError ty_le_dung_toan_bo_pct. Không thể coi lần chạy này là báo cáo hoàn tất thành công.
- Transformer gần nhất chỉ thử 50 mẫu đầu của tập train đã lọc: 44/50 = 88%; mean 88,61 ms, P95 108,11 ms. Không phải benchmark đủ dev/test hay đối chứng công bằng toàn tập.

## Các vấn đề phải sửa trước khi tin báo cáo

1. Báo cáo ghi 221/292 = 76,47%, thực tế 75,68%; 288/292 = 98,63%, không phải 99,65%. Tên key evaluator gắn cứng 292/108 nhưng chia nhóm động: phải lấy so_mau thực từ kết quả, không suy mẫu số từ tên key. Chưa xác nhận mẫu số thực ở lần chạy cũ.
2. Báo cáo ghi ranker 10,9 MB, file hiện tại 177.874 byte. Tổng footprint và biểu đồ phân rã thời gian chưa đủ bằng chứng đo để chấp nhận. Latency cục bộ không chứng minh SLA cloud 1 vCPU/512 MB.
3. eval_test_scalar.py có vòng in độ chính xác từng trường test. Báo cáo cũng công bố và dùng thống kê từng trường để định hướng; trái giới hạn chỉ được biết một con số end-to-end trong yêu cầu tại bước 870. Chưa kết luận đã train trực tiếp trên test, nhưng không thể khẳng định giữ đúng chế độ hộp đen.
4. Từ điển v5 tự ghi verified/train_only, trong khi compiler nhập cả definitions cũ và danh_muc_candidates_pending.jsonl. Đây không phải bằng chứng nguồn đã được xác minh độc lập; audit trước từng bác độ tin cậy của phần definitions. Cần phân loại provenance lại.
5. 95,52% là đo trên dữ liệu train đã lọc; không chứng minh tổng quát hóa. Dev 82,48% còn thấp hơn mốc cũ 941/1.136 = 82,83% bốn ca, nhưng cần chạy lại hai cấu hình trên cùng snapshot để kết luận hồi quy chính xác.
6. Lặp nhiều: unittest discover xuất hiện 19 lần, cùng lệnh inspect_dev_buildings.py 7 lần, lệnh kiểm tra process phổ biến nhất 23 lần. Có dấu hiệu tiêu tốn lượt vào thử luật/quan sát tiến trình, chưa đạt mục tiêu test 95%.

## Kết luận

Có sản phẩm dùng để nghiên cứu tiếp: checkpoint CNN v2, ranker và sửa tiền/hậu xử lý. Chưa nghiệm thu mức cải thiện tổng quát; chưa đạt 95% trên test; chưa chấp nhận báo cáo tài nguyên hoặc tính hộp đen. Không thay mã hay gửi chỉ thị mới cho agy trong lần kiểm tra này. Giữ nguyên ZIP bàn giao cũ, vì các thay đổi này thuộc nhánh nghiên cứu phát sinh sau đó.
