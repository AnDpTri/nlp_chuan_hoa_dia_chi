# Kiểm toán dữ liệu địa chỉ — 30/10/2026

## Phạm vi bảo mật

Chỉ thao tác trên máy nội bộ; không gửi dataset hoặc raw địa chỉ, nguồn hay nhãn ra ngoài.
Không sửa các CSV dữ liệu gốc/test/train/dev hoặc model checkpoint đang có.
Báo cáo audit chỉ chứa số đếm và các cảnh báo tổng hợp.

## Đã triển khai

- data/audit/audit_du_lieu.py: kiểm tra hash các gói, đối chiếu norm/OSM
  giữa train/dev/v2/test, quét cùng họ địa chỉ che số nhà, kiểm tra
  số liệu trạng thái test từ snapshot hiện hành.
- src/lien_ket_v1/du_lieu_linking.py: loại bỏ đặc trưng hardcoded theo
  positive/negative, nạp quan hệ cũ-mới mặc định, bỏ negative trùng,
  chọn gold Linking theo mã thay vì đơn vị cùng tên xuất hiện đầu tiên.
- colab/linking_v1/train_linking.py và evaluate_linking.py: áp dụng lựa
  chọn gold theo mã cho tạo instance.
- data/audit/test_audit_du_lieu.py, test_linking_data_leakage.py,
  test_split_ward_policy.py: kiểm thử không dùng tập test địa chỉ.
- src/chuyen_doi.py: không tự chọn xã mới theo tên trùng khi xã cũ bị
  chia nhiều đích; bắt buộc bảo lưu cờ xa_bi_chia.

## Kết quả mới đo

| Cặp | Trùng chuỗi chuẩn | Trùng OSM | Trùng masked-family nghi vấn |
|---|---:|---:|---:|
| Train / Dev | 0 | 0 | 75 |
| Train / Test | 0 | 0 | 17 |
| Dev / Test | 0 | 0 | 6 |
| V2 / Dev | 0 | 0 | 0 |
| V2 / Test | 0 | 0 | 0 |
| V2 / Train | 78 | 0 | 81 |

Masked-family chỉ là phép dò, không chứng minh rò rỉ: hai số nhà khác
trên cùng phố có thể đụng nhau. Trùng V2/Train là dữ liệu tăng cường
có chung nguồn; lọc khi ghép để không đếm lặp.

Tất cả 6 checksum trong manifest V2 khớp. CSV test khớp checksum ở
validation.json. Trạng thái CSV test: 289 da_duyet_ai, 111 can_duyet,
0 người duyệt. statistics.json còn ghi 292/108 và chưa đồng bộ.

## Giới hạn bắt buộc

- Test hiện chưa đủ điều kiện Gold Test.
- Không dùng tập test hoặc các lỗi riêng trên test để chọn luật hay
  tối ưu siêu tham số. Audit chỉ xuất thống kê, không trả mẫu.
- Checkpoint Linking cũ được tạo từ đặc trưng khác; cần huấn luyện lại
  và đánh giá độc lập trước khi đưa vào runtime.
- evaluate_linking.py đã chỉnh lại tên trường input/tỉnh theo schema dev
  và gắn nhãn phép đo E2E là baseline luật thuần; hiện vẫn CHƯA tích hợp
  Linking Adapter. KHÔNG xem kết quả E2E là điểm của mô hình Linking.
  Các báo cáo cũ vẫn là artifact lịch sử không được tự xác minh lại.
- Đã sửa src/chuyen_doi.py để mọi xã cũ nhiều đích không tự chốt
  đích bằng tên trùng; các ca mơ hồ giữ mã xã đích trống và cờ
  xa_bi_chia. Muốn chốt phải có bằng chứng chi tiết địa bàn độc lập.
- Kiểm định cấu trúc không chứng minh nhãn ngữ nghĩa đã đúng.

## Tái lập offline

Chạy từ gốc dự án:

    py -3.12 -B data/audit/audit_du_lieu.py --output data/audit/bao_cao_audit_20261030.json
    py -3.12 -B -m unittest data.audit.test_audit_du_lieu data.audit.test_linking_data_leakage data.audit.test_split_ward_policy -v

Lưu ý: một số validator cũ ghi lại JSON report mỗi lần chạy; audit mới
chỉ ghi report nếu yêu cầu rõ bằng --output.

## Bộ dữ liệu siêu khó V3 theo yêu cầu người dùng (30/10/2026)

Bộ train-only ở data/train_dev/bo_sung_v3_viet_tat_sieu_kho/ gồm 377
biến thể viết tắt, 20 mẫu cần từ chối kết luận và manifest chứng cứ.
Mốc người dùng cung cấp: x5,mh,ml,nd -> Xóm 5, Phường Mỹ Lộc,
Tỉnh Ninh Bình; mã xã 13708, tỉnh 37. MH chỉ có hiệu lực trong đúng
ngữ cảnh ví dụ, không sinh mã hành chính cũ không có trong catalogue.
Chi tiết và giới hạn dùng ở README.md trong thư mục V3.
