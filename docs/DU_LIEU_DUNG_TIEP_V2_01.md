# Tách phần dùng tiếp và phần giao agy sửa

Ngày 29/10/2026. Dữ liệu lấy từ snapshot audit, không phụ thuộc thư mục
agy đang sửa. Không sửa gói bàn giao gốc, model, dev hoặc test.

## Phân chia

- Đã gửi sửa nguồn danh mục đường vào hội thoại `Chuẩn Hóa Dữ Liệu Địa Chỉ`.
  Cần nguồn tải thật và evidence theo record; không dùng nguồn TXT tự tạo
  để tự chứng minh. Có thể bàn giao ít tên nhưng đủ chứng cứ.
- Đã gửi sửa nhãn input–output không đồng bộ vào `Bổ Sung Train Địa Chỉ Khó`.
  Cần xử lý trường bị bỏ khỏi input mà nhãn còn giữ từ cha; không tái sinh
  toàn corpus hoặc đổi nội dung để né trùng train cũ.
- Cả hai prompt được xác nhận xuất hiện trong đúng hội thoại, trạng thái
  RUNNING tại thời điểm giao. Biên nhận ở `docs/antigravity_rpc/`.

## Phần giữ riêng

Từ 3.000 dòng train mới:

| Phần | Số mẫu |
|---|---:|
| Qua cổng kiểm tra/không trùng input CNN hiện tại | 1.183 |
| Trong đó giữ riêng theo họ ranker hoặc chưa gắn vào phân chia cũ | 256 |
| Trong đó bổ sung được vào phần CNN | **927** |
| Loại khỏi gói dùng tiếp theo các lý do đã ghi | 1.817 |

927 dòng bổ sung thuộc **301 parent_id**, đã ghép với 4.841 dòng CNN cũ
thành **5.768 dòng**. Giữ nguyên records cũ và training_group theo họ cha.
Không giao họ che số nhà với các tập prepared ranker/dev trong phép kiểm
đã chạy; không có input NFC trùng nhau trong tập CNN kết hợp.

Các lý do loại có chồng lấn: chưa đủ điều kiện nhãn chuẩn, nhãn/span không
đồng bộ, trùng input cũ, giao họ dev/ranker. Dòng bị loại không đồng nghĩa
tất cả đều nhãn sai; đặc biệt dữ liệu mơ hồ có thể dùng cho mục đích khác.
Không tự sửa nhãn của những dòng đó trong lượt tách.

Cổng lọc kiểm: cờ canonical của gói, sự hiện diện đồng bộ của nhãn/span
chi tiết, substring/offset, tồn tại cha và hash/URL/mã nguồn cha, nhóm CNN/
ranker đang đóng băng, trùng input và họ prepared dev/ranker; phần đưa vào
CNN kiểm thêm tên đích theo mã trong danh mục. Đây chưa phải rà toàn bộ
ngữ nghĩa độc lập và không biến dữ liệu tổng hợp thành gold.

Dữ liệu đưa về schema ký tự hiện có, giữ char span dù không khớp tokenizer
token cũ. Không dùng file này để train token CRF mà bỏ qua cờ tương thích.
Chưa train lại CNN/ranker hoặc đưa gói mới vào runtime.

## File dùng tiếp

- [927 mẫu char bổ sung](../data/train_dev/duyet_v2_01/train_cnn_bo_sung.jsonl).
- [5.768 mẫu CNN kết hợp](../data/train_dev/duyet_v2_01/train_cnn_ket_hop.jsonl).
- [CSV 1.183 dòng qua cổng lọc](../data/train_dev/duyet_v2_01/train_da_loc.csv).
- [Phần giữ riêng theo họ](../data/train_dev/duyet_v2_01/giu_rieng_theo_ho.jsonl).
- [ID và lý do không đưa vào gói](../data/train_dev/duyet_v2_01/can_sua.jsonl).
- [Tổng kết](../data/train_dev/duyet_v2_01/TONG_KET.json),
  [kiểm chứng](../data/train_dev/duyet_v2_01/KIEM_CHUNG.json),
  [manifest hash](../data/train_dev/duyet_v2_01/MANIFEST.json).
- [Script tách từ snapshot](../danh_gia/tach_goi_train_v2.py).

Danh mục đường mới có **0 bản ghi được nghiệm thu là nguồn chứng thực trong
lượt này**. Điều đó không khẳng định mọi tên đều sai: nguồn hiện chưa đủ căn
cứ cho mức tin cậy mà gói tuyên bố. Tiếp tục dùng từ điển train cũ theo đúng
mức tin cậy đã ghi; không đưa gói đường mới vào lõi để đuổi điểm.
