# Phân tích kết quả Hybrid mới nhất — 30/10/2026

Kiểm tra nhánh feature/reach-95-accuracy, commit 2d1ddb5; hội thoại agy 4.553 bước, IDLE. Đọc log/mã và chạy lại đúng bốn ví dụ train được báo cáo đúng thêm; không chạy lại hay mở nội dung mẫu test.

## Số liệu từ log

| Tập | Baseline cùng lượt | Hybrid | Chênh lệch |
|---|---:|---:|---:|
| Train đã lọc 1.183 | 1.131 (95,60%) | 1.135 (95,94%) | +4 đúng, -0 hồi quy |
| Dev 1.136 | 912 (80,28%) | 912 (80,28%) | +0/-0 |
| Test 400 | 281 (70,25%) | 281 (70,25%) | Không tăng số câu đúng; không có log delta từng câu để khẳng định +0/-0 |

Tổng test tính từ 220 + 61 ở hai phân tập không giao nhau trong log 4524/4539. Báo cáo mới bỏ tổng toàn tập và gắn cứng mẫu số 292/108 dù tỷ lệ dùng mẫu số động. Các phần trăm phải lấy so_mau thực, không lấy từ chuỗi tên key. Không lặp lại thống kê từng trường test.

Dev mới thấp hơn báo cáo trước 937 đúng tới 25 ca; thấp hơn mốc CNN v1 941 tới 29 ca. Đây là chênh lệch số tổng giữa các lần đo, chưa đủ quy toàn bộ cho Hybrid: baseline mới cũng 912; cần khóa hash dữ liệu, mã, checkpoint, từ điển và cờ để tìm nguyên nhân. Test trước 286/400, lần mới 281/400; tương tự chưa xác nhận cùng snapshot/config để kết luận hồi quy riêng từng ca.

## Phát hiện quan trọng qua kiểm tra trực tiếp

Bốn input được báo cáo Hybrid cứu đều thuộc dạng dính từ: ĐườngPhạmVănThuận, ĐườngTrầnHưngĐạo, ĐườngChuVănAn, ĐườngTrầnQuangKhải. Tôi gắn bộ đếm vào bo_tach_phu.chuan_bi_chuoi và chạy lại: cả bốn ra đúng tên đường, baseline vẫn sai, nhưng mỗi ca có ZERO lần gọi Transformer. Kết quả chi tiết ở HYBRID_4_CA.json.

Nguyên nhân trong mã: nhánh bo_tach_phu != None cuối cùng vẫn dựng lại cand bằng token gốc rồi tra từ điển, kể cả không có token unknown liền kề để kích hoạt mô hình. Chính việc dựng lại/tra tên tạo lợi ích. Không thể dùng +4 này làm bằng chứng ViDeBERTa tăng chất lượng. Có thể thử tách thao tác đó thành bước xử lý độc lập, rồi đo lại mà không tải Transformer.

## Độ trễ và chi phí

Log: train mean30,16/P95 57,63 ms; dev mean45,39/P95 82,40 ms. Script nạp ViDeBERTa threads=4; torch.set_num_threads là cấu hình dùng chung cho cả CNN. Không phải đối chứng cùng cấu hình CPU 1 thread trước đây. Chưa đo tỷ lệ gọi mô hình phụ toàn tập, latency riêng ca fallback, RAM thực, cold start, hoặc SLA cloud. Chưa đủ dữ kiện quy lợi ích tốc độ cho cascade hoặc cam kết mọi input dưới200ms. Test~87,5ms là số tự báo cáo, script do_thong_ke_truong.py không in latency để đối chiếu trực tiếp.

## Sai sót lập luận và kỹ thuật

- Báo cáo nói CNN có receptive field32 ký tự là sai: 6 block, mỗi block hai Conv1d kernel3, dilation1..32 => vùng tiếp nhận lý thuyết 1+4*(1+2+4+8+16+32)=253 ký tự, chưa tính giải mã CRF. Dilation lớn nhất32 không phải receptive field32.
- Không thể kết luận BPE gây lỗi gộp hẻm chỉ từ vài câu, cần phân tích căn chỉnh/nhãn huấn luyện/decoder. Chưa có ablation chứng minh.
- Guard gọi verified thực chất dựa trên từ điển train, ví dụ mã log cho thấy xac_minh_doc_lap=False. Không đồng nghĩa tên chuẩn được chứng thực. Không hồi quy trên một tập không chứng minh triệt tiêu100% rủi ro.
- Dùng cùng chỉ số token của CNN để truy cập vdb_ctx.labels mà không đối chiếu offset. Hai adapter có thể chia token khác nhau; bốn ca vừa đo có lưới giống nhau nhưng không bảo đảm toàn bộ input. Cần căn chỉnh bằng char offsets trước khi ghép.
- Cập nhật spans/unknown trước khi xác nhận ứng viên cuối có thể làm dấu vết không khớp output nếu ứng viên bị từ chối; cần kiểm chứng thêm, chưa tái hiện thành fixture trong lần đọc này.
- Script test tiếp tục in từng trường trái yêu cầu chỉ xem điểm end-to-end. Chưa khẳng định train trực tiếp trên test nhưng điều kiện đánh giá hộp đen đã không được giữ đúng.

## Kết luận và thứ tự tiếp theo

Chưa có bằng chứng mô hình mạnh hơn giúp tổng quát hóa. Lợi ích hiện xác nhận được là một sửa xử lý tên đường trên4ca train. Không nên tiếp tục mở rộng Hybrid theo báo cáo hiện tại. Giữ checkpoint và mã để nghiên cứu; tách dựng lại tên đường khỏi mô hình phụ; khóa toàn bộ cấu hình và đối chứng bản trước trên dev; xác định vì sao baseline mất25ca; chỉ sau đó đo ablation CNN + xử lý tên so với CNN + cùng xử lý tên + Transformer. Chưa chạy các benchmark mới này vì yêu cầu hiện tại là phân tích kết quả.
