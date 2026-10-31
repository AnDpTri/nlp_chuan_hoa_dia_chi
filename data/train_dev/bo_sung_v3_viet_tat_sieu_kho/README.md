# Bổ sung V3 — viết tắt địa chỉ cực khó theo ngữ cảnh cũ/mới

Ngày tạo: 30/10/2026. Mốc chuẩn hóa hành chính: 01/07/2025.

## Ví dụ nguồn do người dùng xác nhận

Đầu vào thời kỳ cũ: **x5,mh,ml,nd**

Đầu ra mục tiêu: **Xóm 5, Phường Mỹ Lộc, Tỉnh Ninh Bình**

Mã mới được đối chiếu với danh mục sạch:
- ma_xa: **13708** — Phường Mỹ Lộc
- ma_tinh: **37** — Tỉnh Ninh Bình
- ma_tinh_cu: **36** — Tỉnh Nam Định

Diễn giải nguồn do người dùng xác nhận: x5 = Xóm 5; MH = Mỹ Hưng;
ML = Mỹ Lộc; ND = Nam Định. **Không khẳng định "MH" đơn lẻ là Mỹ Hưng.**
Trong danh mục xã cũ hiện tại không có mục xã Mỹ Hưng thuộc tỉnh Nam Định.
Đây có thể là biệt danh hành chính từ mốc lịch sử trước bản chụp cũ đang
dùng. Không tự điền ma_xa_cu hoặc ma_huyen_cu. Việc gắn đích 13708 cho
chuỗi đầy đủ bốn thành phần dựa trên xác nhận người dùng, **không phải
chứng cứ hành chính độc lập**.

## Kích thước và tệp

- train_abbreviation_extreme.csv: 377 mẫu train-only theo schema 19 trường
  của Train gốc, gồm 17 biến thể từ một mẫu người dùng và 360 biến thể
  từ 120 chuỗi xã/huyện/tỉnh cũ với ánh xạ tới xã mới duy nhất.
- source_spans_and_family.jsonl: offset từng chuỗi con, family_id, loại
  nguồn, ràng buộc chỉ ở train.
- contrast_abstain.csv: 20 mẫu thiếu ngữ cảnh, bắt buộc trả trạng thái
  ABSTAIN và **không đưa thành mẫu đích chuẩn rỗng cho canonical training**.
- manifest.json: mã băm nguồn, mã băm đầu ra, số lượng, chống trùng input.
- data/train_dev/scripts/tao_sieu_kho_viet_tat.py: script tái lập offline.
- data/train_dev/scripts/test_sieu_kho_viet_tat.py: kiểm thử hợp đồng dữ liệu.

## Quy tắc chống suy diễn

Các biến thể từ "x5,mh,ml,nd" giữ đủ bốn yếu tố, chỉ khác chữ hoa,
dấu, cách viết tắt và dấu phân cách. Chúng thuộc **cùng một family**
FAM_USER_MH_ML_ND_01, không phải 17 địa chỉ độc lập.

120 chuỗi khác được sinh từ bảng danh mục hành chính sạch: chỉ dùng
các bộ chữ cái đầu của xã/huyện/tỉnh cũ xuất hiện **đúng một lần trong
toàn bộ danh mục cũ**, và xã cũ chỉ có **một** đích mới. Chúng là câu
tổng hợp dùng để huấn luyện nhận diện ngữ cảnh hành chính, **không phải
địa chỉ OSM được xác minh**. Mỗi chuỗi gốc là một family có 3 biến thể.

Khi thiếu một ngữ cảnh trong ví dụ người dùng (ví dụ "x5,mh,ml"
hoặc "mh,ml"), **không tự gán mã xã mới**. Không tự biến một thành phần
thôn/xóm thành mã xã, không suy rộng "MH" thành quy tắc toàn quốc.

Kiểm tra chéo chỉ chứng minh không có chuỗi input chuẩn hóa trùng
Train/Dev/Test/V2 và quan hệ mã nguồn/đích hợp lệ theo danh mục. Không
chứng minh không có rò rỉ ngữ nghĩa cùng địa danh.

## Cách dùng

Ưu tiên dùng bộ này trong thử nghiệm **candidate retrieval, Entity
Linking có ngữ cảnh và nhận biết viết tắt**, cùng chính sách abstain.
Không tự nạp bộ này vào CNN NER hoặc mô hình canonical hiện tại trước
khi có bộ chuyển nhãn và chia theo family phù hợp, vì các trường admin
viết tắt và từ đồng nghĩa lịch sử không giống BIO của dataset gốc.

Không dùng V3 để đánh giá trên Dev/Test đã biết hoặc tối ưu trực tiếp
dựa vào nhãn Test. Nếu tạo một tập đánh giá mới từ bộ này, bắt buộc
tách theo family và ghi rõ là kiểm tra synthetic cùng nguồn, không Gold.

## Tái lập

Từ gốc dự án (không gọi mạng):

    py -3.12 -B data/train_dev/scripts/tao_sieu_kho_viet_tat.py
    py -3.12 -B -m unittest data.train_dev.scripts.test_sieu_kho_viet_tat -v

Đầu ra mã băm SHA-256 được lưu ở manifest.json.
