# Kiểm tra hai task agy — lượt sửa tiếp, 29/10/2026

**Kết luận: chưa nghiệm thu hoàn tất.** Gói train/dev bổ sung đã sửa được lỗi trùng họ và sai mã nguồn; có phần dùng được cho thử nghiệm tách span. Gói chuẩn hóa canonical còn lỗi tên. Quy trình duyệt test vẫn có hai lỗi thực chất và một phép kiểm thử âm tính chưa kiểm tra chương trình thật.

## Phạm vi và phương pháp

Hai hội thoại đều IDLE khi đọc: task test 1.609 bước, task train 354 bước; mô hình cuối ghi `gemini-3.8-flash-high`. Kiểm tra các tệp bàn giao và yêu cầu sửa, không gửi thêm lệnh cho agy.

Chụp dữ liệu, scripts và tests sang `work/audit_agy_round2/repo_snapshot`, chạy lại kiểm thử/validator hoàn toàn trên bản sao. Không tái sinh gói dữ liệu, không chạy engine ghi vào test thật, không sửa nhãn hay lõi. Kiểm tra độc lập thêm họ mẫu, ba mã nguồn, tên theo mã đích, mapping, offsets/BIO, nguồn cha và ba fixture có lỗi cố ý.

## 1. Phần đã sửa được

### Gói bổ sung

| Phép kiểm | Kết quả độc lập |
|---|---:|
| Train / dev mới | 2.037 / 464 |
| Họ trùng sau che span số nhà, chuẩn hóa chữ và dấu | 0 |
| Sai ba mã xã/huyện/tỉnh cũ so với cha | 0 |
| Lỗi offset, chồng span, BIO và ký tự không trắng bị bỏ | 0 / 2.501 mẫu |
| Mã xã đích nằm ngoài mapping xã nguồn đã ghi | 0 |
| URL cha của mẫu dẫn xuất trùng nguồn test | 0 |
| Dev mới trùng xã cũ + tên đường với train gốc | 0 |
| Cờ usable span / canonical bàn giao | 2.501 / 2.340 |

Phân bố cha xác nhận đúng tài liệu: 1.600 dẫn xuất train gồm 514 OSM và 1.086 tổng hợp; 350 dẫn xuất dev gồm 104 OSM và 246 tổng hợp. 83 ca tên riêng viết tắt mơ hồ để trống tên đường chuẩn và không cho dùng canonical; 78 ca xã bị chia cũng không dùng canonical. Giữ được hai mục đích riêng: học vị trí đoạn chữ và học đầu ra chuẩn hóa.

Chạy lại 12 unit test và validator của gói bổ sung: PASS. Đây là kết quả cơ học và quan hệ danh mục, không xác nhận toàn bộ 2.501 nhãn ngữ nghĩa là vàng.

### Gói test

- Đủ 400 ID, input và URL nguồn không đổi so với bản dự phòng.
- Thực tế 292 `da_duyet_ai`, 108 `can_duyet`; phân loại 263 `du_can_cu_tham_chieu`, 29 `nhan_can_sua`, 108 `chua_du_can_cu`.
- 33 ca mang cờ xã bị chia đều giữ xã đích trống.
- Căn chỉnh lại toàn bộ thành phần trích xuất ở 400 mẫu bằng hàm mới: không có thành phần nào trả offset âm. Các span đang ghi có tiến bộ thực tế so với vòng trước.
- Bỏ lịch thời gian cộng 5 giây giả lập; hiện ghi cùng timestamp thực thi một lượt cho 400 bản ghi. Đây là thời gian chạy tự động, không phải bằng chứng đã đọc từng nguồn vào thời điểm đó.
- Test bảo toàn dòng human hiện thực sự gọi engine và sync trên fixture; đã cải thiện so với vòng trước.
- 37 căn cứ web đã phân biệt 12 chuỗi HTTP 200 và 25 chuỗi báo HTTP 404. Không còn coi tất cả đường dẫn là truy cập thành công. Tuy nhiên các căn cứ “ngoại tuyến” chưa kèm bản văn/đường dẫn tệp để kiểm tra nội dung từng kết luận.

Chạy lại 24 bài test và validator: PASS cấu trúc. Tập test vẫn chưa là gold; không tự dùng số 292 làm số nhãn ngữ nghĩa đã được chứng thực độc lập.

## 2. Lỗi còn lại đã tái hiện

### [P1] Engine vẫn ghi đè chỉnh sửa hiện hành chưa gắn human

`data/test/scripts/ai_review_engine.py:288` vẫn dùng `w = dict(bak)`.

Fixture: ở cả CSV và bảng duyệt của VNTEST0001, sửa trường đường thành `Đường Tây Thạnh`, thêm ghi chú `CURRENT_EDIT_SENTINEL_KEEP_ME`, không gắn human. Chạy engine với mọi đường dẫn chuyển sang fixture. Kết quả đường trở lại `Tây Thạnh`, ghi chú bị mất. Nhánh human được bảo toàn không giải quyết việc ghi đè các sửa đổi hiện hành khác. Cần đọc dữ liệu hiện hành và áp dụng patch với điều kiện trước/sau, giữ xung đột để kiểm tra.

Bằng chứng: `engine_negative_fixtures.json`, fixture `work/audit_agy_round2/fixture_current_edit/`.

### [P1] Căn cứ kiểm tra không gắn với nhãn thực sự xuất ra

Engine căn chỉnh `lbl` từ `agy/labels_*.json`, sau đó xuất các giá trị `w` từ baseline/patch. Hai bộ giá trị này có thể khác nhau. Thành phần căn chỉnh thất bại bị bỏ khỏi mô tả, nhưng kết luận vẫn “Toàn bộ ... xuất hiện nguyên văn”, `du_can_cu_tham_chieu`.

Hai phép thử:

1. Thay nhãn trích xuất đường của VNTEST0001 bằng `ABSENT_FROM_INPUT_SENTINEL`. Căn chỉnh thất bại nhưng engine vẫn `da_duyet_ai`, `du_can_cu_tham_chieu`; mô tả chỉ bỏ trường đường.
2. Giữ input thật `181 Tây Thạnh,P. Tây Thạnh, Q Tân Phú, HCM`; cài nhãn đường sai `ABSENT FROM INPUT SENTINEL` vào baseline fixture. Engine xuất nguyên tên sai đó, vẫn ghi căn cứ đường `Tây Thạnh`, vẫn đủ căn cứ. Chạy validator trên output fixture cũng trả `PASS`, `structural_status=PASS`.

Phép thử thứ hai chứng minh một nhãn đường không có trong input có thể lọt qua cả engine lẫn validator cấu trúc. Không suy rằng toàn bộ 292 nhãn hiện tại đều sai; điều được chứng minh là quy trình chưa kiểm soát được loại sai này và tuyên bố nghiệm thu mạnh hơn khả năng kiểm tra.

Bằng chứng: `unobserved_output_fixture.json`, `engine_negative_fixtures.json`. Vị trí liên quan: engine dòng 320–330, 478–500.

### [P2] Bài test âm tính 22 vẫn chỉ kiểm tra dữ liệu tự tạo

`tests/test_review_validation.py:605–619` dùng regex để thấy số âm, so hai khoảng tự tạo và nhận ra dãy cách 5 giây. Không đưa lỗi vào engine/validator rồi kiểm tra chương trình chặn nó. Vì thế 24/24 PASS không mâu thuẫn với những lỗi đã tái hiện ở trên.

### [P2] 24 nhãn train thiếu loại đơn vị trong tên chuẩn

Tất cả 24 dòng đều ghi `xa_phuong = Phương Liệt` với mã `00352`; danh mục mốc đích là `Phường Phương Liệt`. Ví dụ VNTRAIN_BS_00198:

- Input: `Số 657/7/2B Phố Tôn Thất Tùng, Phường Khương Mai, Quận Thanh Xuân, Thành phố Hà Nội`.
- Nhãn: mã xã `00352`, tên `Phương Liệt`.
- Tên đầy đủ theo mã: `Phường Phương Liệt`.

Nguyên nhân: `generate_bo_sung_v1.py:195` bỏ dấu khi kiểm tra tiền tố loại, coi chữ **Phương** trong tên là loại **Phường** đã có. Các kiểm thử hiện tại chủ yếu kiểm mã và quan hệ nên bỏ sót tên đầy đủ. Lỗi này không làm hỏng offset của bốn trường BIO, nhưng cần sửa trước khi dùng nhãn đầu ra canonical và chuỗi địa chỉ ghép.

Danh sách đầy đủ: `train_name_mapping_errors.json`.

### [P2] Bàn giao thực tế là tái sinh gói mới, chưa phải lọc giữ các mẫu cũ hữu ích

Nhật ký cũ đánh dấu 1.464 `kept_valid`; tài liệu nói giữ làm hạt giống. Tuy nhiên generator mới đọc train/dev gốc, không đọc danh sách này để giữ mẫu. Trong gói mới chỉ 1 chuỗi input giữ nguyên từ 2.814 mẫu cũ; nếu che số nhà và chuẩn hóa hoa/thường/khoảng trắng thì giữ 18 trong 1.736 dạng input cũ. Có snapshot nên lịch sử chưa mất, nhưng cần mô tả đúng việc tái sinh và cung cấp ánh xạ/cơ chế tái sử dụng phần được giữ.

Đồng thời, cả 1.600 + 350 mẫu dẫn xuất đều thay số nhà so với cha; metadata nhiều dòng chỉ ghi bỏ dấu/viết tắt hoặc đảo thứ tự. Bảo toàn mã xã là cải thiện thật, nhưng không đồng nghĩa giữ nguyên ý nghĩa toàn địa chỉ nguồn. Cần ghi rõ phần được kế thừa và phần tổng hợp/thay thế.

## 3. Mức có thể dùng hiện tại

- **Thử nghiệm tách span:** có thể tận dụng gói bổ sung theo đúng train/dev đã chia. 2.501 mẫu qua kiểm tra cơ học độc lập; chưa khẳng định toàn bộ nhãn ngữ nghĩa đã chuẩn xác.
- **Huấn luyện chuẩn hóa canonical:** chưa nên đưa nguyên gói vào. Tôn trọng các cờ loại 161 ca mơ hồ; sửa 24 tên thiếu loại và rà tính đủ bằng chứng của phần canonical. Nhóm 88 ca “viết tắt tên riêng” chắc chắn hiện chủ yếu QL/TL/ĐCT, không chứng minh đã có từ điển mở rộng tên người viết tắt. Danh sách gợi ý BVT vẫn thiếu căn cứ và có những tên không khớp chữ đầu; các dòng này hiện đã bị loại canonical.
- **Test cuối và báo độ chính xác chính thức:** chưa nghiệm thu quy trình duyệt. Cần sửa hai lỗi P1, kiểm thử âm tính trên engine thật và rà lại căn cứ gắn với output hiện hành. Việc thiếu xã tự nó không làm một nhãn không dùng được; cần phân biệt phần xác định được, phần cố ý để trống và phần nhãn còn nghi ngờ.

Không tự sửa dữ liệu hoặc gửi task tiếp trong lượt kiểm tra này.

## 4. Tệp kiểm chứng

- `checks.json` và bốn file log: lệnh kiểm tra của hai task chạy lại trên snapshot.
- `train_independent_audit.json`, `train_name_mapping_errors.json`, `train_retention_audit.json`.
- `test_independent_audit.json`, `test_alignment_failures.json` (rỗng ở bộ hiện tại).
- `engine_negative_fixtures.json`, `unobserved_output_fixture.json`: bằng chứng fixture độc lập.
- `conversation_finals.json`: phản hồi cuối đã lọc khỏi dữ liệu suy luận nội bộ.
- `original_sha256_before.json`, `preservation_checks.json`: bằng chứng bảo toàn.

Script tái hiện nằm tại `work/audit_agy_round2/reproduce_engine_failures.py`, dùng snapshot cạnh script và tạo fixture mới; không chạy trên dự án thật. Những fixture đã chạy giữ tại `fixture_current_edit/`, `fixture_missing_span/`, `fixture_unobserved_output/` trong work.

**Ghi nhận thao tác song song:** so với lúc bắt đầu kiểm tra, `src/tim_kiem.py` và `src/tach_phan_con.py` thay đổi từ bên ngoài lượt audit này; không xác định tác nhân, không tự quy cho agy. Dữ liệu được ghim hash không đổi. Mọi phép kiểm dùng snapshot độc lập nên kết quả kiểm tra dữ liệu không phụ thuộc hai file lõi đó.
