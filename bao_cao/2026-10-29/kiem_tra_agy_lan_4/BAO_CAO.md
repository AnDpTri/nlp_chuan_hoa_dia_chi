# Kiểm tra độc lập hai task agy — lần 4, ngày 29/10/2026

**Cả hai đã bàn giao, có sửa đúng và có thêm dữ liệu dùng được, nhưng chưa
đạt để nghiệm thu toàn bộ.** Gói train/dev đạt các kiểm tra cơ học đã chạy;
bảng kế thừa còn khẳng định sai tên đường. Quy trình test đã chặn các ca
âm tính cũ nhưng vẫn duyệt hai kiểu nhãn sai trong fixture độc lập mới.

## 1. Phạm vi và cách kiểm tra

- Hội thoại test `feca2faf-c8c5-4c07-8293-c9f0c9e553e4`: IDLE, 2.168 bước.
- Hội thoại train `388e264d-6447-42fb-b64f-559ba8e2e86d`: IDLE, 919 bước.
- Chỉ đọc trả lời hiển thị cuối của hai hội thoại; lưu ở
  [conversation_finals.json](conversation_finals.json).
- Chụp bản sao 156 file, 40.395.433 byte vào `repo_snapshot/`, đối chiếu
  SHA-256 với dự án trước khi chạy. Không sao chép PBF, cache hay log lớn.
- Unit test, validator và engine đều chạy trong bản sao/fixture. Không
  sửa CSV/JSONL nguồn trong dự án, không train lại mô hình và không dùng
  nhãn test để điều chỉnh thuật toán chuẩn hóa.
- Script audit và fixture nằm cùng thư mục báo cáo, đủ để truy lại mọi
  kết luận bên dưới. Kiểm tra bảo toàn sau cùng ở `checks.json`.

## 2. Gói train/dev: phần đã xác nhận

| Chỉ số độc lập | Train | Dev |
|---|---:|---:|
| Tổng mẫu | 2.169 | 500 |
| Dùng được cho span theo tokenizer runtime hiện tại | 2.125 | 488 |
| Lệch ranh giới tokenizer, đã đánh dấu không dùng | 44 | 12 |
| Cờ dùng cho canonical training | 2.038 | 470 |
| Span ngõ/ngách/hẻm | 88 | 24 |
| Span thôn/xóm/tổ | 88 | 18 |
| Mẫu mới so với lần 3 | 132 | 36 |

Đã kiểm tra lại toàn bộ 2.669 mẫu:

- Không có lỗi token offset, char-span, BIO so với span hoặc chồng span
  trong phép kiểm độc lập. `token_spans.jsonl` khớp toàn bộ bản ghi của
  hai file train/dev span.
- Không có lỗi tên đích theo mã; không lệch ba mã nguồn so với mẫu cha
  được dẫn xuất; các kiểm tra quan hệ hành chính đã chạy đều qua.
- 56 ca cắt giữa token được đánh dấu đúng: `usable_for_span_training=false`
  và `tokenizer_runtime_compatible=false`. Char span vẫn được giữ.
- Không còn giao họ che số nhà giữa train/dev bổ sung, train bổ sung với
  dev gốc hoặc dev bổ sung với train gốc trong phép kiểm đã triển khai.
  Không có giao nhóm gốc được khai báo giữa train/dev bổ sung.
- Các hash và kích thước trong manifest khớp file thực.
- **17/17 unit test** và validator của agy đều chạy qua trên snapshot.

168 mẫu bổ sung mới hiện nằm trong **6 nhóm gốc khai báo ở train và 6
nhóm ở dev**. Số mẫu tăng không đồng nghĩa có 168 họ độc lập hoặc 168
địa chỉ thực đã được xác minh ngoài đời. Nhãn tổng hợp vẫn cần được phân
biệt với gold và số liệu này không chứng minh bao phủ toàn bộ biến thể.

Bằng chứng: [audit train](train_independent_audit.json),
[56 ca lệch tokenizer](train_runtime_incompatible.json),
[168 mẫu mới cùng nhãn/span](new_training_examples.json),
[log unit test](train_unit.log), [log validator](train_validator.log).

## 3. Gói train/dev: lỗi kế thừa còn lại

Đã sửa đúng việc ghép sang xã cũ khác: **0 đối ứng đổi mã xã cũ**.
1.249 mẫu không có đối ứng được đổi nhãn thành `not_reused_in_v2_clean_corpus`,
thay vì tiếp tục khẳng định chúng đã được giữ lại.

Tuy nhiên, trong **56 dòng còn gọi là `regenerated_clean_corpus`**:

- 55 dòng khác nguyên văn trường đường giữa bản cũ và đối ứng mới.
- Sau bỏ dấu và tiền tố loại đường, **54 dòng vẫn là tên đường khác hẳn**.
- Một dòng còn lại chỉ khác cách viết/tiền tố, không tính vào 54 lỗi tên.

Ví dụ kiểm tra được trực tiếp:

| Bản cũ | Đối ứng mới | Tên đường cũ → mới |
|---|---|---|
| `VNTRAIN_BS_00042` | `VNTRAIN_BS_01280` | Nguyễn Trãi → Hoàng Văn Thụ |
| `VNTRAIN_BS_00060` | `VNTRAIN_BS_00478` | Cách Mạng Tháng Tám → Tố Hữu |
| `VNTRAIN_BS_00106` | `VNTRAIN_BS_00304` | Lê Hồng Phong → Hoàng Hoa Thám |

Cột `inheritance_detail` vẫn ghi giữ tên đường cũ và chỉ thay số nhà.
Nhánh ghép theo parent trong `build_snapshot_comparison.py` kiểm tra cùng
parent và mã xã, nhưng chưa kiểm tra phần đường mà nó khẳng định đã kế thừa.
Validator và unit test chủ yếu kiểm tra mã xã đối ứng nên vẫn PASS.

Đây là lỗi về bảng provenance/khẳng định kế thừa; **không suy ra toàn bộ
nhãn span hiện tại đều sai**. Có thể dùng phần span đã lọc cho thử nghiệm,
nhưng chưa thể chứng nhận toàn bộ phần kế thừa là chính xác.

Bằng chứng đầy đủ 55 cặp nguyên văn:
[snapshot_counterpart_errors.json](snapshot_counterpart_errors.json).
Script tái hiện: [audit_train.py](audit_train.py).

## 4. Gói test: phần đã sửa đúng

- 400 ID, input và URL giữ nguyên so với snapshot lần 3.
- **289 `da_duyet_ai`, 111 `can_duyet`**: gồm 263 `du_can_cu_tham_chieu`,
  26 `nhan_can_sua`, 111 `chua_du_can_cu`.
- Theo mapping hiện hành có **36 ca xã bị chia**, đều giữ xã đích trống
  và có cảnh báo. Ba ca mới được nhận diện là `VNTEST0046`, `VNTEST0053`,
  `VNTEST0055` thuộc Lạc Đạo. Đây là cải thiện so với 33 ca lần trước.
- Audit JSONL hiện khớp các trường output được kiểm tra của CSV: 0 lệch.
- Bỏ timestamp tra cứu hardcode: toàn bộ 400 `thoi_diem_tra_cuu` để trống
  khi chưa có hồ sơ truy cập riêng, không giả timestamp của từng nguồn.
- **24/24 bài kiểm thử quy trình** và validator hiện hành đều qua.

Các fixture cũ được chạy lại bằng engine/validator thật:

| Ca | Validator trước engine | Kết quả engine |
|---|---|---|
| Đường hoàn toàn không có trong input | FAIL | `can_duyet` |
| `Số 81` nằm trong `181` | FAIL | `can_duyet` |
| Lấy `Tân Phú` làm số nhà | FAIL | `can_duyet` |
| Chuỗi mã Bến Nghé/Quận 1 hợp lệ nhưng vắng trong input | FAIL | `can_duyet` |
| Căn chỉnh NFD `Tay Thanh` | — | Offset cắt đủ `Tây Thạnh`, đạt |
| Chỉnh hiện hành đường + ghi chú sentinel | PASS | Giữ giá trị và ghi chú |

Sau khi engine hạ một nhãn lỗi xuống `can_duyet`, validator PASS cấu trúc
là hành vi có thể chấp nhận; không tính đó là đã xác nhận nhãn đúng.

Bằng chứng: [audit test](test_independent_audit.json),
[thay đổi so với lần 3](test_changes_vs_round3.json),
[unit test](test_unit.log), [validator](test_validator.log).

## 5. Hai fixture mới vẫn qua sai cả engine và validator

### 5.1. Lấy tên quận làm bằng chứng cho một phường khác

Input thật `VNTEST0001`, giữ nguyên:

```text
181 Tây Thạnh,P. Tây Thạnh, Q Tân Phú, HCM
```

Cài chuỗi mã hoàn toàn hợp lệ nhưng sai địa bàn:

```text
Xã/phường cũ: 26836 — Tân Phú, huyện/quận cũ 769 — Quận 9
Đích:        26842 — Phường Tăng Nhơn Phú, tỉnh 79
```

Kết quả: engine giữ chuỗi mã sai, ghi `du_can_cu_tham_chieu`, cấp
`da_duyet_ai`; validator PASS trước và sau engine.

Tên `Tân Phú` trong input là **quận**, còn phường đã ghi rõ là **Tây Thạnh**.
`check_admin_grounding` chấp nhận tên xã chỉ vì xuất hiện bất kỳ đâu;
kiểm tra huyện lại bỏ sót cách viết `Q Tân Phú` không có dấu chấm. Việc
đổi sang một chuỗi mã có cùng tên nhưng sai cấp/vị trí vẫn lọt qua.

### 5.2. `KP 1` chứng minh nhầm `Thôn 199999`

Input thật `VNTEST0288`, giữ nguyên:

```text
56 Dong Ho, KP 1, Phuong Dong, Ho, Tx. Ha Tien, Kien Giang
```

Cài `thon_xom="Thôn 199999"`. Engine giữ nguyên nhãn này, vẫn cấp
`da_duyet_ai` với kết luận `nhan_can_sua`; validator PASS trước và sau.

Nguyên nhân: nhánh viết tắt chấp nhận mọi nội dung thôn bắt đầu bằng `1`
khi input có `kp 1`. Nó không kiểm tra toàn bộ số và không bảo đảm loại
thành phần được phục hồi tương ứng. Các trường hợp này cần so đầy đủ tên,
số và vai trò; không chỉ thêm kiểm tra riêng cho ID hoặc giá trị fixture.

Hai fixture **không thay input/URL**, chỉ cài nhãn sai trên CSV bản sao.
Không kết luận rằng toàn bộ 289 nhãn hiện hành đều sai; chúng chứng minh
quy trình kiểm chứng còn có thể cấp trạng thái duyệt cho output sai.

Bằng chứng: [independent_negative_fixtures.json](independent_negative_fixtures.json),
script [independent_fixtures.py](independent_fixtures.py), CSV/audit/log trong
`fixture_v2_ward_name_only_in_district/` và `fixture_v2_hamlet_number_mismatch_kp1/`.
Lượt fixture đầu có lỗi BOM do script audit ghi CSV UTF-8 BOM, đã đổi sang
UTF-8 đúng cách đọc của validator rồi chạy lại trong thư mục `fixture_v2_*`;
không tính lượt lỗi harness đó là lỗi dữ liệu hoặc kết quả kiểm tra.

## 6. Căn cứ pháp lý: có đính chính, chưa đối chiếu đủ mốc

- Sửa đúng NQ1192 về Cần Thơ và ngày hiệu lực NQ1232 Hải Phòng. Nhưng
  hồ sơ Hà Nội nay dùng NQ1286 hiệu lực 01/01/2025 để giải trình các ca
  chia theo đợt 01/07/2025. NQ1286 thuộc đợt trước; hồ sơ cần nối thêm
  đúng quan hệ/mốc của NQ1656 về sắp xếp Hà Nội năm 2025. Có 11 audit
  record hiện dẫn NQ1286.
- URL NQ1286 mà agy ghi trong file ngoại tuyến trả **HTTP 404** khi truy
  cập trực tiếp. URL chính thức khác truy cập được và đã lưu HTML.
- `VNTEST0040` vẫn có câu trong audit rằng Gia Viên chia ba phường theo
  NQ1232, trong khi phần văn bản về Ngô Quyền là nhập Lạc Viên và Máy Tơ
  vào Gia Viên. Kết quả để trống có thể hợp lý khi thiếu căn cứ, nhưng lý
  do/nguồn được ghi chưa phải chuỗi chứng minh nhất quán.

Nguồn đã đối chiếu:

- [NQ1286 chính thức](https://xaydungchinhsach.chinhphu.vn/nghi-quyet-so-1286-nq-ubtvqh15-ve-viec-sap-xep-don-vi-hanh-chinh-cap-xa-cua-thanh-pho-ha-noi-119241122151657096.htm).
- [NQ1656 Hà Nội năm 2025](https://vanban.chinhphu.vn/?docid=214008&pageid=27160).
- [NQ1232 Hải Phòng](https://xaydungchinhsach.chinhphu.vn/nghi-quyet-1232-nq-ubtvqh-sap-xep-don-vi-hanh-chinh-thanh-pho-hai-phong-119241103063654234.htm).

HTML, HTTP status, URL thực, thời điểm tải UTC và SHA-256 đã lưu tại
[legal_source_fetch.json](legal_source_fetch.json) cùng các file HTML.
Đây là kiểm tra nguồn phục vụ audit, chưa phải rà soát pháp lý độc lập
toàn bộ 400 địa chỉ hoặc xác minh thực địa từng số nhà.

## 7. Kết luận sử dụng

**Train/dev:** phần span đã lọc có thể dùng cho thử nghiệm; các kiểm tra
cơ học/nhãn tên theo mã nêu trên đều qua. Cần đính chính 54 khẳng định
kế thừa sai tên đường, giữ nguyên giới hạn nguồn và dữ liệu tổng hợp.
Không coi provenance đã hoàn tất chỉ vì 0 đối ứng đổi mã xã.

**Test:** có tiến bộ thực ở các lỗi cũ và ba ca xã chia mới. Hai fixture
mới vẫn qua sai cả engine lẫn validator nên chưa thể nghiệm thu chất
lượng xác minh ngữ nghĩa hoặc dùng trạng thái `da_duyet_ai` làm bảo đảm
đáp án đúng. Không dùng test này để fit mô hình/luật trong lúc sửa workflow.

Lần kiểm tra này không gửi task mới cho agy, không sửa dữ liệu và không
đưa dữ liệu mới vào các checkpoint đã train.

Ghi chú làm việc song song: hai file `src/chuan_hoa.py` và `src/__main__.py`
ở cây dự án sống thay đổi trong lúc audit, với phần thêm adapter ViDeBERTa.
Các lệnh audit không sửa chúng và không ghi đè các thay đổi đó. Mọi kiểm
tra ở đây dùng `repo_snapshot/` đã đóng băng; toàn bộ file dữ liệu nguồn
đã chụp giữ nguyên hash, checkpoint Char-CNN/ranker cũng giữ nguyên.
Không quy các thay đổi lõi song song này cho hai task agy chỉ từ hash.
