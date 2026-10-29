# Kiểm tra hai gói agy: danh mục đường v1 / train khó v2

Ngày 29/10/2026. Hai hội thoại IDLE; đã có gói bàn giao và tài liệu. Chụp
snapshot dữ liệu, scripts/tests, danh mục và source cần thiết trước kiểm tra.
Validator/unit test của gói chỉ chạy trên repo_snapshot. Không chạy builder,
không sửa gói thật, không tích hợp danh mục và không train model.

## Kết luận

**Cả hai gói chưa đạt để nghiệm thu toàn bộ.** Kết quả PASS của kiểm tra
cấu trúc không chứng minh nội dung hoặc nguồn tham chiếu đúng.

## Danh mục đường

- Có 1.461 bản ghi confirmed / 1.007 tên canonical phân biệt, 23 pending/rejected.
- Validator và 11 tests hiện hành đều PASS khi chạy trên bản sao.
- `generate_sources.py` import bảng hằng từ `definitions/*.py`, ghép chuỗi
  và tự ghi các file `.txt` vào `sources/`, rồi băm chính các file đó.
  Kiểm tên xuất hiện trong các file tự tạo không phải kiểm chứng với văn bản
  nguồn độc lập. Điều này chưa chứng minh từng tên sai, nhưng không đủ căn
  cứ gán confirmed/pháp lý/thực địa như tài liệu khẳng định.
- 8/10 URL nguồn là trang gốc, không định vị văn bản/bản ghi chứng minh.
  Metadata source manifest không có fetched_at_utc hoặc HTTP status; không
  thấy bản tải HTML/PDF/Overpass tương ứng trong tập nguồn bàn giao này.
- URL `https://vanban.chinhphu.vn/?docid=204000&pageid=27160` được ghi là
  QĐ 1454/QĐ-TTg quy hoạch mạng lưới đường bộ. Trang chính thức thực tế là
  **89/QĐ-TCTĐB ngày 09/09/2021**, quy chế hoạt động Tổ công tác đặc biệt
  về rà soát/thúc đẩy dự án đầu tư. Đây là sai đối tượng nguồn, không chỉ
  lỗi hash hoặc khác định dạng văn bản.
- Cần tải nguồn thật, lưu URL cụ thể/thời điểm/hash và liên kết từng record
  với evidence; các dòng chưa đủ chứng cứ chỉ nên là candidate/pending.
  Chưa nghiệm thu alias, địa bàn hoặc mốc của từng dòng chỉ vì mã có trong
  danh mục. Không dùng gói này làm từ điển tên đường đã chứng thực.

## Train khó v2

- Có 3.000 mẫu, 650 family_id, tối đa 5 dòng/family theo khai báo thực tế.
- Kiểm độc lập không thấy char span sai substring/offset, span chồng nhau,
  token offset sai hoặc input CSV lệch input JSONL trong các phép kiểm đã chạy.
- Validator và 16 tests hiện hành PASS trên bản sao. Chưa tự xác nhận kết
  luận "0% leakage tuyệt đối" ngoài các phép kiểm mà gói triển khai.
- Có **654** nhãn `ngo_ngach_hem` khác rỗng nhưng span tương ứng null;
  **433** trong số này vẫn `usable_for_canonical_training=true`.
- Có **79** nhãn `thon_xom` khác rỗng nhưng span tương ứng null;
  **66** trong số này vẫn `usable_for_canonical_training=true`.
  Đây là số theo từng trường, không cộng thành số dòng phân biệt.
- Ví dụ VNTRAIN_V2_00021: input `Số 27, Duong Han Thuyen, Phường Thủ Đức,
  Thành phố Hồ Chí Minh`; nhãn `thon_xom=Khu phố 3`, span null, canonical
  usable true. Input không cung cấp căn cứ cho việc điền Khu phố 3.
- VNTRAIN_V2_00001 input chỉ có số 528 và đường Ngô Gia Tự, nhưng nhãn vẫn
  giữ `Ngõ 528` từ mẫu cha dù span null. Dòng này canonical usable false,
  song cho thấy cùng cơ chế kế thừa trường khi biến thể đã bỏ thành phần.
- Bảo toàn nhãn cha không đồng nghĩa nhãn đúng với input biến thể. Khi bỏ
  thành phần, phải bỏ/cập nhật nhãn tương ứng hoặc phân định missing/unknown,
  không để model học suy thông tin vắng mặt.

Có thể tận dụng phần span sau kiểm tra ngữ nghĩa và lọc đúng mục đích; chưa
đưa cả gói vào train chuẩn hóa. Không tự sửa những trường này trong audit.

## Bằng chứng và giới hạn

- `audit_doc_lap.py`: script kiểm tra độc lập, chỉ đọc snapshot.
- `KIEM_TRA_DOC_LAP.json`: số liệu, ví dụ ID/input/nhãn/span/cờ sử dụng.
- `SNAPSHOT_SHA256.json`: hash các file chụp trước kiểm tra.
- `repo_snapshot/`: gói/script/fixture tại thời điểm kiểm tra.
- `FETCH_NGUON_THAT.json` và HTML nguồn chính thức nếu tải thành công.
- Nguồn web đã đối chiếu: [văn bản docid 204000](https://vanban.chinhphu.vn/?docid=204000&pageid=27160).

Audit này xác nhận các lỗi trên, chưa phải rà toàn bộ ngữ nghĩa của 3.000
mẫu hoặc xác minh độc lập 1.007 tên đường. Chưa gửi thêm nhiệm vụ sửa cho agy.
