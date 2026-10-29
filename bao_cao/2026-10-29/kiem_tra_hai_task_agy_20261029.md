# Kiểm tra độc lập hai nhiệm vụ agy — 29/10/2026

**Cả hai hội thoại đã kết thúc nhưng chưa đạt điều kiện nghiệm thu.** Đã đọc trả lời cuối và source, chạy kiểm tra hiện có, kiểm tra độc lập dữ liệu. Chưa sửa hoặc tích hợp bộ bổ sung vào huấn luyện.

## 1. Sửa lượt duyệt test

Hội thoại `Chuẩn Hóa Dữ Liệu Địa Chỉ`, ID `feca2faf-c8c5-4c07-8293-c9f0c9e553e4`: IDLE, 1.291 bước.

### Đã xác nhận

- Có đủ 400 bản ghi, giữ nguyên toàn bộ ID/input/URL nguồn so với bản trước duyệt.
- Thu hồi chín nhãn xã đã chốt thiếu căn cứ. Cả 33 ca xã bị chia hiện để trống xã đích và giữ ứng viên/cảnh báo.
- CSV và nhật ký có 366 dòng `da_duyet_ai`, 34 dòng `can_duyet`; kết luận gồm 337 giữ nguyên, 29 sửa, 34 chưa đủ căn cứ.
- Model và agent đã được tách riêng.
- Chạy lại `test_review_validation.py`: **21/21 PASS**. Validator test và kiểm tra ghim danh mục PASS. Báo cáo thật được chạy sau fixture.

### Chưa đạt

1. **Bằng chứng span sai nhưng vẫn xác nhận đúng.** Trong 168 mẫu vốn `tu_dong_khop`, 161 nhật ký có vị trí bắt đầu `-1` nhưng vẫn khẳng định tất cả các đoạn nhãn xuất hiện chính xác. Ví dụ `VNTEST0001` ghi xã Tây Thạnh khớp tại `[-1:8]`. Trong `ai_review_engine.py:168–206`, code gọi `find()` rồi chỉ viết kết quả vào văn bản; không kiểm tra vị trí hợp lệ trước khi đổi trạng thái. Có cả việc tìm tên đích mới trong input cũ và việc tìm chuỗi đã bỏ dấu trong input còn dấu. **Không suy từ lỗi nhật ký rằng cả 161 nhãn đều sai**, nhưng phép kiểm chứng được báo cáo không có giá trị xác nhận như đã tuyên bố.

2. **Thời gian kiểm tra được dựng từ chỉ số dòng.** `ai_review_engine.py:131–135` dùng mốc cố định `2026-10-29 11:45:00+07:00`, cộng năm giây cho mỗi dòng rồi ghi là `thoi_gian_kiem_tra`. Đây không phải thời điểm thực của thao tác kiểm tra từng mẫu. Thay một thời điểm cố định bằng chuỗi thời gian giả lập chưa đáp ứng yêu cầu kiểm toán.

3. **Căn cứ nội dung vẫn có mô tả nhầm.** `VNTEST0040` có input `1B, Phố Thiên Lôi, Phường Gia Viên, Hải Phòng`, nhưng bằng chứng lại bàn về phường Đằng Giang. Không thể coi phần giải thích đó là đối chiếu đúng input.

4. Có 37 dòng đã gắn URL, nhưng các câu “đã đọc toàn văn” được ghi bằng chuỗi cố định trong engine. Kiểm tra hiện có chỉ xét xuất hiện `http`, ngày và vài từ khóa, không kiểm tra nguồn trả về đúng văn bản hoặc bằng chứng hỗ trợ kết luận. Bốn URL ngoài NQ1685 đã thử mở qua công cụ web đều không truy cập được trong lần kiểm tra này; **chưa kết luận URL bị bịa chỉ từ lỗi truy cập**, nhưng chưa xác nhận được nguồn như báo cáo tuyên bố.

5. **Bài kiểm tra bảo toàn sửa tay chưa thử engine.** Test 21 chỉ sửa cờ human trong fixture rồi đọc lại để kiểm tra cờ còn đó; không gọi engine và so sánh trước–sau. Vì vậy PASS của bài này chưa chứng minh tính năng bảo toàn sửa tay hoạt động khi chạy engine. Engine vẫn khởi tạo các dòng không có cờ human từ baseline (`w = dict(bak)`), có nguy cơ ghi đè cập nhật hiện hành.

## 2. Bổ sung train và dev khó

Hội thoại `Bổ Sung Train Địa Chỉ Khó`, ID `388e264d-6447-42fb-b64f-559ba8e2e86d`: IDLE, 180 bước.

### Đã xác nhận

- Có **2.297 dòng train bổ sung**, **517 dòng dev khó**, tổng **2.814**, chia 16 loại biến thể.
- Có đủ 2.814 bản ghi token/span. Kiểm tra độc lập offset token, thứ tự token và cú pháp BIO không phát hiện lỗi cấu trúc.
- Kiểm tra độc lập tên–mã xã/tỉnh và quan hệ chuyển đổi không phát hiện sai khác ở các trường đã kiểm tra.
- Chạy lại 9 unit tests và validator của bộ bổ sung: PASS.
- Train/dev gốc, danh mục và source lõi vẫn trùng mã băm của phiên bản đã đo trước đó.

### Chưa đạt

1. **Cùng họ biến thể xuất hiện ở cả train và dev.** Che đúng span số nhà bằng `<SO_NHA>`, giữ nguyên phần input còn lại và các nhãn hành chính/đường/ngõ/thôn, phát hiện **28 họ trùng giữa hai tập**, liên quan **866 dòng train và 198 dòng dev**. Cách chia chỉ xét ID nhóm tự đặt nên không phát hiện các họ mẫu giống nhau.

   Ví dụ:

   - Train `VNTRAIN_BS_00031`: `Số 659A Phố Chợ, Phường Tĩnh Hải, Thị xã Nghi Sơn, Tỉnh Thanh Hóa`.
   - Dev `VNDEV_KHO_00046`: `Số 1Bis Phố Chợ, Phường Tĩnh Hải, Thị xã Nghi Sơn, Tỉnh Thanh Hóa`.

   Hai mẫu chỉ khác số nhà nhưng được đặt hai nhóm khác nhau. Đây là rò rỉ ở mức họ biến thể; không đồng nghĩa có chuỗi input trùng hoàn toàn. Do đó kết luận “0% rò rỉ nhóm” hiện tại quá rộng.

2. **Provenance dẫn xuất không phản ánh phép biến đổi thật.** Có 654 dòng train và 141 dòng dev mang nguồn dẫn xuất nhưng đổi mã xã cũ so với mẫu nguồn. Ví dụ:

   - Nguồn `VNTRAIN_03573`: `108 duong Ly Thuong Kiet, Phuong Thach Ha, Thanh pho Ha Tinh, Ha Tinh`.
   - Mẫu được gọi là dẫn xuất `VNTRAIN_BS_00001`: `39 Đ. NTT, Phường 13, Quận 4, Thành phố Hồ Chí Minh`.

   Generator chọn địa bàn cố định/ngẫu nhiên mới trong nhiều nhánh, bỏ qua địa bàn của mẫu nguồn. Cần phân loại chúng thành mẫu tổng hợp mới, ghi đúng căn cứ và gom nhóm theo nguồn/mẫu thực sự tạo ra chúng.

3. **Mở rộng tên viết tắt được khẳng định chắc chắn khi chưa có nguồn chứng minh.** 175 mẫu thuộc `viet_tat_ten_rieng` được đánh dấu `xac_dinh_theo_ngu_canh`. Trong generator, việc mở rộng được gán bằng vài nhánh hằng số theo mã xã/huyện, còn provenance chỉ là lời khẳng định “xác định duy nhất”. Chưa có từ điển bí danh có nguồn hoặc kiểm tra tập cách mở rộng khác để chứng minh tính duy nhất. Không kết luận tất cả 175 đáp án đều sai; kết luận là căn cứ gán mức chắc chắn chưa đủ.

4. **Tài liệu nguồn và bí danh không khớp file thực.** Toàn bộ 2.814 dòng thực tế mang nguồn `danh_muc_hanh_chinh`, nhãn tổng hợp. Trong 1.500 cha của nhánh train dẫn xuất, chỉ 344 là nhãn máy, 1.156 là tổng hợp; nhánh dev 78 nhãn máy và 242 tổng hợp. Tài liệu mô tả toàn bộ 1.500/320 mẫu dẫn xuất này như kế thừa OSM là không chính xác. Bảng bí danh trong tài liệu cũng khác các bảng gán trong generator.

## Hướng xử lý trước nghiệm thu

- Test: sửa phép kiểm chứng span thực, ghi thời gian thật hoặc thời gian lượt xuất được chú thích đúng, đối chiếu lại nội dung nguồn, và viết bài kiểm tra thực sự chạy engine trên fixture.
- Train/dev khó: sửa provenance, gom/chia lại theo họ mẫu trước khi sinh biến thể, rà căn cứ bí danh và tách phần chưa đủ chứng cứ khỏi nhãn phục hồi tên đầy đủ.
- Không hạ điều kiện kiểm tra hoặc thêm chữ “đã kiểm chứng” chỉ để PASS. Không dùng bộ bổ sung hiện tại để tuyên bố độ chính xác hoặc huấn luyện trước khi xử lý các lỗi trên.

Tệp kèm: `kiem_tra_hai_task_agy/independent_audit.json`, `families_overlap.csv`, `provenance_mismatch.csv` và log các kiểm tra.
