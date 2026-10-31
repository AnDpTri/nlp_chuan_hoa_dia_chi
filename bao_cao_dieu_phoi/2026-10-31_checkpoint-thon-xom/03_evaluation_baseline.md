# Xác minh bốn kết quả v3_tc — baseline 31/10/2026

**Phạm vi:** chỉ kiểm tra bốn thư mục kết quả được chỉ định trong D:\nlp_rf_gate\train_v3. Không chạy pipeline, scorer, huấn luyện hay test. Chỉ đọc metadata/nội dung JSONL, tính SHA-256 và đếm split. Đọc BAO_CAO_SANG.md và NHAT_KY.md ở mức cần thiết để đối chiếu metric và nguồn bộ khó.

## 1. Metadata và tính đồng nhất

Timestamp gốc là UTC; bảng đã chuyển sang giờ Việt Nam (UTC+7).

| Kết quả | Tạo (31/10, +07) | Sửa cuối (+07) | Kích thước | Dòng |
|---|---:|---:|---:|---:|
| ket_v3_tc | 01:45:20 | 01:47:26 | 6.575.245 B | 3.100 |
| ket_v3_tc_luat | 01:48:28 | 01:50:37 | 6.575.215 B | 3.100 |
| ket_v3_tc_lan2 | 04:50:46 | 04:54:04 | 6.575.215 B | 3.100 |
| ket_v3_tc_ranh_gioi | 05:00:55 | 05:04:12 | 6.575.215 B | 3.100 |

SHA-256 tính trực tiếp từ từng file:

| Kết quả | SHA-256 |
|---|---|
| ket_v3_tc | 7d90e8495f9efdc5dac0b44de79d09209aee5dca62621f5d55cd61b74110ab31 |
| ket_v3_tc_luat | 417a1ce6101ee2601cff67c87cbcd3766e6e5463bb8391720ab0d04900405982 |
| ket_v3_tc_lan2 | 417a1ce6101ee2601cff67c87cbcd3766e6e5463bb8391720ab0d04900405982 |
| ket_v3_tc_ranh_gioi | 417a1ce6101ee2601cff67c87cbcd3766e6e5463bb8391720ab0d04900405982 |

**Kết luận:** ket_v3_tc_luat, ket_v3_tc_lan2 và ket_v3_tc_ranh_gioi là cùng một file kết quả từng byte; không được tính thành ba lần chạy/ba phép đo độc lập. ket_v3_tc là output khác.

## 2. Số lượng mẫu

Đếm trực tiếp trường split trên cả 3.100 JSONL record của từng file:

| Split | Số mẫu mỗi file |
|---|---:|
| dev_goc | 1.136 |
| dev_kho | 464 |
| kho | 1.500 |
| **Tổng** | **3.100** |

Cơ cấu mẫu giống nhau ở cả bốn file. kho là bộ khó 1.500 mẫu; không đồng nhất nó với dev_kho 464 mẫu.

## 3. Model/checkpoint

Metadata trong từng record của cả bốn file thống nhất một cấu hình:

| Trường metadata | Giá trị |
|---|---|
| mo_hinh | char_cnn_crf_va_lambdarank |
| phien_ban | char_cnn_crf_v1_lambdarank_bao_ve_duong_ten_train |
| crf_model_sha256 | 655db4a128c210765b267defa33c5a566debfe220d23837dcfaa3d566ab71075 |
| ranker_sha256 | 4712bb6e64037ce681fac4f53b5459dc952eb016624aaff48222f4cecc115a89 |

Đây là bằng chứng trực tiếp về checkpoint được khai trong output. JSONL **không ghi Git commit hoặc hash source code chạy inference**. Hash crf_model_sha256 ở đây là hash artifact model, không phải hash mã nguồn CRF.

## 4. Metric và kết quả có thể xác nhận

BAO_CAO_SANG.md ghi cho cấu hình **v3_tc + luật mới**:

| Metric | Kết quả |
|---|---:|
| End-to-end, khớp đồng thời 6 trường trên dev_goc | 993/1.136 = **87,4%** |
| End-to-end, khớp đồng thời 6 trường trên dev_kho | 422/464 = **90,9%** |
| Riêng tiền xử lý, dev 1.600 | **85,7%** |
| Riêng tiền xử lý, bộ khó 1.500 | **82,7%** |

Metric end-to-end là exact match đồng thời sáu trường; không phải điểm riêng của CRF hay span F1. Hai số 85,7% và 82,7% là metric riêng tiền xử lý, không được thay thế hoặc trộn với exact sáu trường.

**Giới hạn gắn metric vào thư mục:** báo cáo sáng nêu cấu hình v3_tc + luật mới nhưng không ghi rõ tên thư mục JSONL được chấm. Vì ba file ket_v3_tc_luat, ket_v3_tc_lan2, ket_v3_tc_ranh_gioi byte-identical nên chúng có cùng dự đoán; số 87,4%/90,9% phù hợp với nhóm output này nếu dùng cùng nhãn và scorer. Tuy nhiên, không có bằng chứng trực tiếp để gán chắc chắn số điểm đó cho từng tên thư mục. ket_v3_tc có hash khác; không có metric riêng được tài liệu hóa rõ cho file này.

JSONL có 1.500 mẫu kho, nhưng số 82,7% trong báo cáo là **tiền xử lý**. Không tìm thấy điểm end-to-end sáu trường trên 1.500 mẫu trong bằng chứng được phép kiểm tra.

## 5. Có phải baseline trước bản sửa ngày 31/10?

- Cả bốn file được tạo và sửa trong ngày 31/10/2026, từ 01:45 đến 05:04 giờ Việt Nam.
- Chúng là các artifact có timestamp sớm trong ngày, nên **có thể dùng làm ứng viên baseline lịch sử**.
- Tuy nhiên, bốn thư mục không chứa Git commit, source hash hay dấu thời gian của patch. Hash được ghi trong JSONL chỉ nhận diện model/ranker, không nhận diện phiên bản code.
- Vì vậy, **không thể chứng minh chỉ từ bốn thư mục này rằng chúng được tạo trước chính xác bản sửa CRF ngày 31/10**. Muốn khẳng định cần có timestamp/commit của patch để đối chiếu với thời điểm sửa cuối 05:04:12; không được suy ra từ tên thư mục.

## 6. Tính công bằng và rủi ro

1. **Dùng làm mốc chất lượng sản phẩm:** có thể, với điều kiện giữ nguyên bộ nhãn và scorer. ket_v3_tc_luat là ứng viên đại diện hợp lý nhất cho cấu hình v3_tc + luật mới; lan2 và ranh_gioi không tạo thêm bằng chứng độc lập vì trùng hash.
2. **Dùng làm đối chứng trực tiếp cho patch CRF:** chưa đủ điều kiện. Output không có source commit/hash và không có bằng chứng xác nhận code trước patch. Cùng model/checkpoint không đồng nghĩa cùng phiên bản code.
3. **Bộ khó 1.500:** NHAT_KY.md ghi train và bộ khó đều do Agy tạo, khác seed nhưng có thể cùng văn phong; còn 13 tên quốc lộ/ngày tháng trùng sau lọc. Vì vậy không xem kho là phép kiểm độc lập mạnh. Ưu tiên dev_goc làm mốc chính; báo riêng dev_kho.
4. **Metric:** chỉ so sánh trước/sau nếu cùng phiên bản nhãn, cùng chuẩn hóa và cùng scorer. Không so điểm tiền xử lý với exact sáu trường end-to-end.

## 7. Kết luận

**Độ tin cậy: trung bình cho baseline sản phẩm; thấp/chưa xác lập cho baseline trước patch CRF.**

Có một mốc output có thể xác minh bằng hash, số mẫu và checkpoint: ket_v3_tc_luat (cùng nội dung với ket_v3_tc_lan2 và ket_v3_tc_ranh_gioi). Metric được tài liệu hóa cho cấu hình v3_tc + luật mới là 87,4% trên dev_goc và 90,9% trên dev_kho. ket_v3_tc là một output khác nhưng không có điểm riêng gắn chắc chắn với nó.

**Không kết luận ba thư mục trùng hash là ba lần tái lập. Không kết luận bốn output chắc chắn là pre-patch chỉ dựa vào tên hoặc ngày tạo.** Để xác nhận baseline trước/sau CRF công bằng, cần đối chiếu thời điểm patch và chạy cặp đánh giá có lưu source commit/hash, giữ nguyên checkpoint, dữ liệu, nhãn và scorer. Lần xác minh này không chạy bất kỳ đánh giá nào.
