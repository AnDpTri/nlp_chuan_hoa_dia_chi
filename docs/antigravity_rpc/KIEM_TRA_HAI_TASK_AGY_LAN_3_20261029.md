# Kiểm tra bàn giao agy lượt 3 — 29/10/2026

**Kết luận: có sửa thực chất, chưa nghiệm thu toàn bộ.** Gói train sửa đúng 24 tên chuẩn nhưng không thêm/cải thiện nhãn span so với snapshot đã dùng thử CRF. Quy trình test giữ được chỉnh sửa hiện hành và gắn grounding vào output, nhưng còn chấp nhận nhãn sai vai trò/ranh giới hoặc mã hành chính không có bằng chứng trong input. Tài liệu căn cứ pháp lý có nội dung sai kiểm chứng được từ nguồn Chính phủ.

## Phạm vi và bảo toàn

- Cả hai hội thoại IDLE: test 1.844 bước; train 539 bước, model cuối `gemini-3.8-flash-high`.
- Chụp dữ liệu/scripts/tests/src sang `work/audit_agy_round3/repo_snapshot` của chat. Các engine, validator, unit test và fixture chỉ chạy trên bản sao.
- Chạy lại 13 bài train và 24 bài test: đều PASS; hai validator tập bàn giao cũng PASS cấu trúc. Các con số này không xác nhận ngữ nghĩa vàng.
- Hash các file dự án trước/sau audit không đổi; source/CRF giống manifest sau lần train. Train/dev gốc, danh mục, test thật và dữ liệu bổ sung thật được giữ nguyên trong lượt kiểm tra này.
- Không chạy mô hình trên test để chỉnh thuật toán, không huấn luyện lại, không gửi thêm yêu cầu cho agy trong lượt kiểm tra.

## 1. Gói train/dev bổ sung

| Phép kiểm độc lập | Kết quả |
|---|---:|
| Train / dev | 2.037 / 464 |
| Sai tên tỉnh/xã theo mã đích | 0 |
| Sai ba mã nguồn so với mẫu cha | 0 |
| Họ trùng train/dev sau che span số nhà | 0 |
| Dòng thay so với lượt audit trước | 24 |
| Trường thay ở cả 24 dòng | `xa_phuong`, `dia_chi_chuan` |
| File train/dev/token spans so với lượt trước | Giống nguyên byte cả ba file |

Lỗi `Phương Liệt` đã sửa thành `Phường Phương Liệt`, kể cả chuỗi ghép. Đây là sửa đúng và giữ nguyên input/ID/span. Phần CRF hiện có không nhận thêm dữ liệu học vai trò từ lượt sửa này.

### Giới hạn nhãn span và độ phủ vẫn còn

- Không có span ngõ/hẻm trong cả train lẫn dev bổ sung. Train có 66 span thôn/tổ, dev có 12.
- 56 dòng vẫn có ranh giới span cắt giữa token lõi hiện tại: 44 train, 12 dev. Ví dụ `151Đ.LêLợi` tách `151` thành số nhà ở bản nhãn, còn tokenizer lõi giữ `151Đ` thành một token. Đây là bất tương thích giữa hai bộ token, không phải tất cả 56 span đều sai về ý nghĩa. Không thể đưa nguyên chúng vào CRF hiện tại rồi tuyên bố tương thích 100%.
- Báo cáo 30 ca đã có input/output/span chi tiết; việc tự ghi `usable=True` và phân tích bằng template chưa đủ để chứng nhận toàn bộ 2.501 mẫu đúng ngữ nghĩa.

### [P2] Bảng đối chiếu dữ liệu cũ–mới chưa đáng tin

Trong 1.305 dòng được gắn `regenerated_clean_corpus`:

- **1.127 dòng không có ID đối ứng mới**: chưa đủ để truy vết việc kế thừa từng mẫu.
- **122 dòng có đối ứng nhưng đổi mã xã cũ**, trái phần mô tả kế thừa địa bàn.

Ví dụ:

- Cũ `VNTRAIN_BS_01503`: `118Đ.BàTriệu, P12, Q5, Thành phố Hồ Chí Minh`, mã xã cũ `27310`.
- Đối ứng gán mới `VNTRAIN_BS_01799`: `151Đ.LêLợi, P3, Q3, Thành phố Hồ Chí Minh`, mã xã cũ `27154`.

Script `build_snapshot_comparison.py` chọn đối ứng qua `(split, parent_id, loại biến thể)`. Các mẫu tổng hợp có parent_id rỗng có thể bị ghép tùy ý với mẫu khác; phần mô tả kế thừa vẫn lấy thông tin cũ mà không kiểm tra mã địa bàn đối ứng. Không được dùng bảng này làm căn cứ dữ liệu cũ đã được giữ/tái sử dụng đúng. Sai bảng đối chiếu không đồng nghĩa toàn bộ nhãn dữ liệu mới đều sai.

## 2. Gói test

Giữ đủ 400 ID/input/URL nguồn như bản đóng băng; hiện 292 `da_duyet_ai`, 108 `can_duyet`. 33 ca xã chia đều để trống xã đích.

### Phần đã sửa được, có tái hiện

- Fixture chỉnh `Đường Tây Thạnh` và ghi chú `CURRENT_EDIT_SENTINEL_KEEP_ME` không gắn human: engine giữ được cả giá trị và ghi chú.
- Thay nhãn đường ở file extraction riêng không còn tự tác động tới căn cứ output; engine dùng đúng dữ liệu hiện hành.
- Cài `ABSENT FROM INPUT SENTINEL` vào đường của dữ liệu hiện hành: engine giữ giá trị để kiểm tra nhưng chuyển `can_duyet`/`chua_du_can_cu`, ghi rõ không quan sát được. Validator trả PASS cấu trúc cho dòng đang cần duyệt, không đồng nghĩa chấp nhận nhãn đó để nghiệm thu.
- Bài kiểm thử âm tính mới đã chạy engine/validator thật trên fixture, tốt hơn bài chỉ kiểm regex trước đây.

### [P1] Grounding vẫn chỉ là tìm chuỗi con, chưa xác minh token và vai trò

Hai fixture có cùng input thật:

`181 Tây Thạnh,P. Tây Thạnh, Q Tân Phú, HCM`

| Nhãn cố ý sai | Engine | Validator |
|---|---|---|
| `so_nha = Số 81` | `da_duyet_ai`, `du_can_cu_tham_chieu`; căn cứ `81` tại `[1:3]` bên trong `181` | PASS |
| `so_nha = Số Tân Phú` | `da_duyet_ai`, `du_can_cu_tham_chieu`; lấy tên quận làm số nhà | PASS |

Có substring không chứng minh đúng ranh giới token hoặc đúng vai trò địa chỉ. Các fixture không chứng minh toàn bộ 292 dòng hiện tại sai; chúng chứng minh cơ chế chưa kiểm soát được loại sai này.

### [P1] Có thể thay bằng một chuỗi mã hợp lệ nhưng không khớp input

Giữ input Tây Thạnh/Tân Phú ở trên, thay cả bộ mã nguồn/đích bằng chuỗi hợp lệ trong danh mục:

- Xã cũ `26740` — Bến Nghé, huyện cũ `760` — Quận 1.
- Xã mới `26740` — Phường Sài Gòn, tỉnh `79`.

Engine vẫn ghi `du_can_cu_tham_chieu`, `da_duyet_ai`; validator PASS vì mã/cha-con/cạnh chuyển đổi tự nhất quán. Chưa có kiểm tra đủ chặt rằng đơn vị nguồn được gán thật sự có bằng chứng trong input. Chỉ kiểm tra mã tồn tại và cạnh hợp lệ chưa đủ.

### [P2] Căn chỉnh không dấu sai offset khi input là Unicode phân rã

Gọi API căn chỉnh với NFD của `12 Tây Thạnh`, output đường `Tay Thanh`: engine trả `[3:12]` và substring `Tây Thạ`, khi bỏ dấu chỉ còn `tay tha`, thiếu phần cuối. Nguyên nhân dùng vị trí chuỗi đã xóa dấu để cắt chuỗi gốc mà không có ánh xạ. Đây là lỗi API đã tái hiện, không suy rằng mọi dòng test hiện tại đều có lỗi NFD.

### [P1] Tài liệu căn cứ ngoại tuyến có nội dung sai

File mới `data/test/can_cu_phap_ly_ngoai_tuyen.md` được mô tả như bản trích chính thức, nhưng:

1. Ghi NQ **1192/NQ-UBTVQH15** là của Hà Nội, ban hành 14/11/2024, hiệu lực 01/07/2025. [Cơ sở dữ liệu Chính phủ](https://vanban.chinhphu.vn/?docid=211381&pageid=27160) xác định nghị quyết này là của **Cần Thơ**, ban hành **28/09/2024**, hiệu lực **01/11/2024**. Có **11 bản ghi audit** dẫn NQ1192 như căn cứ Hà Nội.
2. Ghi NQ **1232/NQ-UBTVQH15** hiệu lực 01/07/2025; [bản chính thức](https://vanban.chinhphu.vn/?classid=2&docid=211609&pageid=27160) ghi **01/01/2025**. Nội dung nói Gia Viên chia ba phường cũng không khớp [văn bản được Chính phủ đăng](https://xaydungchinhsach.chinhphu.vn/nghi-quyet-1232-nq-ubtvqh-sap-xep-don-vi-hanh-chinh-thanh-pho-hai-phong-119241103063654234.htm): phần Ngô Quyền của nghị quyết này nhập Lạc Viên và Máy Tơ vào Gia Viên.

Vì thế không thể coi file Markdown mới là bằng chứng đã lưu đúng bản văn nguồn. Không thay nhãn hành chính trong lượt kiểm tra này chỉ từ các phát hiện về căn cứ; cần rà lại theo đúng văn bản/mốc và từng input.

Ngoài ra engine còn ghi cứng thời điểm tra cứu `2026-10-29T14:15:00+07:00` cho 37 bản ghi. Không có cơ chế lấy thời điểm truy cập riêng từ mỗi chứng cứ. Điều này chưa tự chứng minh nguồn chưa từng được đọc, nhưng chưa đủ để coi timestamp đó là nhật ký truy cập từng nguồn đã được kiểm chứng.

## 3. Cách dùng hiện tại

- Có thể giữ gói train mới với tên chuẩn đã sửa để tiếp tục thử nghiệm; nhãn span giống snapshot cũ, không có lý do kỳ vọng CRF tự cải thiện nhờ lượt sửa tên này. Vẫn lọc hoặc thống nhất 56 ca tokenizer và bổ sung độ phủ ngõ/hẻm.
- Không dùng bảng đối chiếu cũ–mới làm provenance chắc chắn cho tới khi sửa đối ứng.
- Chưa dùng trạng thái 292 duyệt AI hoặc PASS cấu trúc làm chứng nhận test vàng. Cần đóng các lỗ hổng role/token/nguồn hành chính và thay căn cứ pháp lý sai bằng nguồn đúng.

## 4. Bằng chứng

Trong `work/audit_agy_round3` của chat và bản xuất ở `outputs/kiem_tra_agy_lan_3`:

- `train_independent_audit.json`, `train_name_errors.json`, `train_diff_vs_round2.json`.
- `snapshot_counterpart_mismatch.json`, `train_runtime_incompatible.json`.
- `independent_negative_fixtures.json`, script `negative_fixtures.py`, fixture riêng từng tình huống và log.
- `reproduced_*/results.json`: chạy lại phép thử vòng trước với engine mới.
- `checks.json`, log hai validator, `original_sha256_before.json`, phản hồi cuối hội thoại đã lọc bỏ suy luận nội bộ.

Các phép kiểm dùng bản sao. Dữ liệu thật và lõi/CRF không bị sửa trong lượt kiểm tra này.
