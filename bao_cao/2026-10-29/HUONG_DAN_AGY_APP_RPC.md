# Gửi yêu cầu vào hội thoại Antigravity bằng lệnh và kiểm chứng kết quả

Ngày kiểm chứng: **29/10/2026**. Môi trường: Windows, Python 3.12, ứng dụng Antigravity đang đăng nhập trên máy này.

Mục đích: gửi yêu cầu vào một hội thoại có sẵn trong app, sau đó tự kiểm tra đúng hội thoại, đúng nội dung và trạng thái chạy bằng lệnh. Tài liệu kèm script dùng lại, nội dung yêu cầu đã gửi và biên nhận lần gửi thực tế.

## 1. Mở nhanh bộ tài liệu

Các file trong cùng thư mục:

| File | Công dụng |
|---|---|
| `agy_app_rpc.py` | Liệt kê hội thoại, đọc trạng thái, gửi yêu cầu, xác minh biên nhận |
| `yeu_cau_sua_du_lieu.txt` | Nguyên nội dung yêu cầu sửa dữ liệu đã được gửi |
| `lan_gui_sua_du_lieu.json` | Biên nhận và bằng chứng của lần gửi đó |

Mở PowerShell và vào thư mục:

```powershell
Set-Location -LiteralPath 'C:\Users\andan\Documents\Codex\2026-10-29\d-nlp-chuan-hoa-dia-chi\outputs'
```

Tất cả lệnh bên dưới chạy từ thư mục này. Script dùng thư viện chuẩn Python, không cần cài thêm package.

## 2. Kiểm chứng ngay lần gửi vừa rồi

Chạy:

```powershell
py -3.12 -X utf8 -B .\agy_app_rpc.py verify --receipt .\lan_gui_sua_du_lieu.json --wait-seconds 0
```

Kiểm tra các trường:

```json
{
  "conversation_id": "feca2faf-c8c5-4c07-8293-c9f0c9e553e4",
  "state": "confirmed_in_conversation",
  "verification": {
    "prompt_present": true,
    "status": "CASCADE_RUN_STATUS_RUNNING"
  }
}
```

Đây là ví dụ rút gọn. Trạng thái `RUNNING` có thể đã đổi khi bạn kiểm tra. Các trường `checked_at_utc`, `num_total_steps` và `last_step_types` phản ánh lần đọc mới nhất.

Lệnh `verify` chỉ đọc trạng thái từ app rồi cập nhật file biên nhận cục bộ; **không gửi lại yêu cầu**. Trường `initial_verification` giữ bằng chứng lúc đầu, còn `verification` là bằng chứng mới nhất.

Bằng chứng ban đầu của lần gửi thật:

- Hội thoại: **Chuẩn Hóa Dữ Liệu Địa Chỉ**.
- ID: `feca2faf-c8c5-4c07-8293-c9f0c9e553e4`.
- Trước khi gửi: 227 bước, `CASCADE_RUN_STATUS_IDLE`.
- Server nhận request `SendUserCascadeMessage`.
- Lần đọc tiếp: 230 bước, có bước `USER_INPUT` chứa đúng nội dung yêu cầu, agent ở trạng thái `RUNNING` và đã có bước thực thi lệnh.
- SHA-256 của nội dung đã gửi: `d91fc5551fa19ea236e6396acdd4b280b3f441bec97391c7185c934948249ca0`.

Hash được tính trên **chuỗi UTF-8 sau khi đọc file và bỏ khoảng trắng ở hai đầu**, không phải hash byte nguyên file. Ký tự xuống dòng và BOM được xử lý khi đọc file. Có thể tự tính lại:

```powershell
py -3.12 -X utf8 -c "from pathlib import Path; import hashlib; s=Path('yeu_cau_sua_du_lieu.txt').read_text(encoding='utf-8-sig').strip(); print(hashlib.sha256(s.encode('utf-8')).hexdigest())"
```

## 3. Kiểm tra đúng hội thoại

Liệt kê theo tên:

```powershell
py -3.12 -X utf8 -B .\agy_app_rpc.py list --query 'Chuẩn Hóa Dữ Liệu Địa Chỉ'
```

Lệnh này đọc chỉ mục SQLite ở:

```text
C:\Users\andan\.gemini\antigravity\conversation_summaries.db
```

Kết nối dùng chế độ chỉ đọc. Kiểm tra `title` và `conversation_id`; nếu có nhiều tên giống nhau, dùng ID để phân biệt. `project_id = outside-of-project` là vị trí của hội thoại trong app, không phải kết luận nó không được truy cập dự án D:.

Đây là chỉ mục của **app**, khác với thư mục `antigravity-cli`. Trạng thái trong chỉ mục có thể cập nhật chậm; dùng lệnh `status` để đọc từ server đang chạy.

## 4. Xem trạng thái trực tiếp

```powershell
py -3.12 -X utf8 -B .\agy_app_rpc.py status --conversation feca2faf-c8c5-4c07-8293-c9f0c9e553e4
```

| Trường | Cách đọc |
|---|---|
| `conversation_id` | Phải đúng ID bạn định gửi |
| `status` | Trạng thái hiện tại từ server |
| `num_total_steps` | Tổng bước trong hội thoại, không phải số tin nhắn hoặc phần trăm tiến độ |
| `loaded_steps` | Số bước được server trả về trong lần đọc này |
| `last_step_types` | Các loại bước mới nhất, ví dụ đọc file hoặc chạy lệnh |
| `last_model_name` | Model trong cấu hình lần chạy gần nhất; không phải phép đọc trực tiếp ô chọn model trong UI |

`CASCADE_RUN_STATUS_RUNNING` cho biết hội thoại đang chạy. `CASCADE_RUN_STATUS_IDLE` chỉ cho biết nó hiện không chạy; muốn biết nhiệm vụ thành công phải đọc trả lời cuối trong app và kiểm tra file/kết quả tương ứng.

Lệnh này chỉ đọc, không gửi tin, không đổi cấu hình hay thao tác giao diện.

## 5. Gửi một yêu cầu mới

Trước tiên, viết nội dung mới vào file UTF-8, ví dụ `yeu_cau_moi.txt`, rồi đọc lại nội dung. Bản `yeu_cau_sua_du_lieu.txt` đi kèm là yêu cầu **đã gửi**, dùng để kiểm chứng chứ không cần gửi lại.

Kiểm tra trạng thái hội thoại bằng lệnh ở mục 4. Script chỉ cho gửi khi hội thoại `IDLE`.

Gửi yêu cầu mới và tạo một biên nhận mới:

```powershell
py -3.12 -X utf8 -B .\agy_app_rpc.py send --conversation feca2faf-c8c5-4c07-8293-c9f0c9e553e4 --prompt-file .\yeu_cau_moi.txt --receipt .\lan_gui_002.json
```

Lệnh này **thực sự gửi nội dung file cho agent trong app**. Mỗi lần gửi dùng một tên biên nhận riêng. File prompt không rỗng, file biên nhận chưa tồn tại, và đúng nội dung đó chưa có trong hội thoại thì script mới gửi.

Quy trình của script:

1. Xác định server app cục bộ và đọc CSRF token từ trang app, chỉ giữ trong bộ nhớ.
2. Đọc đúng hội thoại bằng `GetCascadeTrajectory` và kiểm tra ID trả về.
3. Kiểm tra hội thoại đang rảnh và chưa chứa nguyên nội dung prompt này.
4. Lấy cấu hình override và agent của lần chạy trước trong chính hội thoại.
5. Ghi biên nhận trước khi gửi, rồi gọi `SendUserCascadeMessage` đúng **một lần**.
6. Đọc lại hội thoại tối đa 10 giây để xác nhận nội dung xuất hiện trong bước `USER_INPUT`.

Script không tự bấm nút, không điều khiển chuột/bàn phím và không chạy `agy --print` hay `agy --conversation`. Nội dung và tiến trình được lưu trong hội thoại của app, nơi bạn có thể xem trực tiếp.

Nếu bạn vừa đổi lựa chọn model hoặc chế độ trong UI nhưng chưa chạy lượt nào, cấu hình lần trước có thể khác lựa chọn chưa dùng đó. Kiểm tra trước khi dùng helper; bản này không tự sao chép trạng thái dropdown chưa được thực thi.

## 6. Phân biệt nhận request, xuất hiện tin và hoàn tất công việc

| Bằng chứng | Điều được xác nhận |
|---|---|
| `state = attempt_started` | Đã ghi ý định gửi; chưa đủ biết server có nhận không |
| `state = outcome_unknown` | Gửi bị lỗi/timeout, có thể server đã nhận; chưa được gửi lại ngay |
| `state = accepted` | RPC trả thành công; chưa đủ biết tin đã có trong lịch sử |
| `state = confirmed_in_conversation` và `prompt_present = true` | Đúng nội dung đã xuất hiện trong bước người dùng của đúng hội thoại |
| `verification.status = RUNNING` | Agent đang chạy tại thời điểm kiểm tra |
| `verification.status = IDLE` | Agent hiện không chạy; chưa chứng minh nó đã làm đúng yêu cầu |

Khi gửi timeout hoặc chưa thấy tin xuất hiện, dùng **biên nhận cũ** để kiểm tra:

```powershell
py -3.12 -X utf8 -B .\agy_app_rpc.py verify --receipt .\lan_gui_002.json --wait-seconds 15
```

`verify` không thử gửi lại. Không xóa biên nhận để vượt chặn gửi trùng. Nếu vẫn chưa rõ, đối chiếu hội thoại trong app trước khi quyết định có cần gửi một lượt mới.

Các chỉ báo trên kiểm chứng việc gửi và trạng thái thực thi. Với nhiệm vụ sửa dữ liệu, vẫn cần xem diff, chạy kiểm tra và kiểm tra nhãn; một lượt chạy kết thúc không tự chứng minh dữ liệu đúng.

## 7. Khi app đổi cổng hoặc khởi động lại

Cổng `22143` là cổng đã quan sát trong phiên kiểm chứng, **không phải cổng cố định**.

Mặc định script tìm cổng HTTPS cuối cùng trong log app:

```text
C:\Users\andan\AppData\Roaming\Antigravity\logs\language_server.log
```

Script chỉ trích số cổng để dùng, không in nội dung log. Nếu đường dẫn log khác:

```powershell
py -3.12 -X utf8 -B .\agy_app_rpc.py status --conversation feca2faf-c8c5-4c07-8293-c9f0c9e553e4 --log-file 'D:\duong_dan_log\language_server.log'
```

Hoặc cung cấp origin hiện tại, ví dụ **chỉ khi app vẫn đang dùng cổng 22143**:

```powershell
py -3.12 -X utf8 -B .\agy_app_rpc.py status --conversation feca2faf-c8c5-4c07-8293-c9f0c9e553e4 --base-url 'https://127.0.0.1:22143'
```

Sau khi app khởi động lại, đọc lại trang sẽ lấy CSRF token mới. Không sao chép token cũ vào script hoặc tài liệu.

## 8. Cơ chế đã xác định từ mã ứng dụng

Trong JavaScript frontend được app phục vụ tại `/main.js`, nút có `data-testid="send-button"` gọi chuỗi xử lý gửi, qua hàm `sendUserCascadeMessage`. Client dùng Connect RPC, JSON và header CSRF.

Hai RPC được dùng:

```text
POST https://127.0.0.1:<port>/exa.language_server_pb.LanguageServerService/SendUserCascadeMessage
POST https://127.0.0.1:<port>/exa.language_server_pb.LanguageServerService/GetCascadeTrajectory
```

Phần payload cốt lõi của lệnh gửi:

```json
{
  "cascadeId": "ID-hội-thoại",
  "items": [{"text": "Nội dung cần gửi"}],
  "cascadeConfig": "Cấu hình override lấy từ lần chạy trước",
  "customAgentSpec": "Đặc tả agent lấy từ lần chạy trước"
}
```

Đây là hình minh họa: hai trường cấu hình thực tế là object JSON, không phải chuỗi. Header `Content-Type: application/json`, `Connect-Protocol-Version: 1` và `x-codeium-csrf-token` được script tự tạo; không điền token thủ công.

**Phạm vi tương đương đã kiểm chứng:** helper gọi cùng RPC gửi tin của backend app và tin đã xuất hiện trong cùng hội thoại. Nó không tái hiện toàn bộ handler React, hiệu ứng UI tạm thời, file đang đính kèm, lựa chọn chưa chạy hay mọi telemetry của một lần bấm nút. Bản này chỉ hỗ trợ gửi văn bản vào hội thoại có sẵn, không tạo hội thoại mới hoặc đính kèm ảnh/file.

Kết nối tới app là cục bộ; việc app gọi model vẫn theo cơ chế mạng và tài khoản của Antigravity. Dùng chung RPC không chứng minh Google coi tích hợp này là được hỗ trợ hoặc bảo đảm tài khoản không bị hạn chế.

## 9. Giới hạn và cách xử lý lỗi

| Hiện tượng | Cách xử lý |
|---|---|
| Không tìm thấy log/cổng | Mở app, kiểm tra log hoặc truyền `--base-url` hiện tại |
| Connection refused | App/server chưa chạy hoặc cổng đã đổi; dùng `status` để kiểm tra lại |
| HTTP 401/403 hoặc lỗi CSRF | Chạy lại thao tác đọc sau khi app ổn định. Nếu lỗi ở lệnh gửi, xác minh biên nhận trước; không tự gửi lại |
| Hội thoại không `IDLE` | Theo dõi lượt đang chạy; helper không chèn thêm lượt song song |
| Biên nhận đã tồn tại | Dùng `verify`; nếu là một nhiệm vụ mới thật sự thì dùng nội dung và biên nhận mới |
| Nội dung đã có trong hội thoại | Kiểm tra lượt cũ; tránh gửi lại cùng nhiệm vụ |
| Chưa thấy `prompt_present` ngay | Kiểm tra lại bằng `verify`, do trạng thái có thể cập nhật chậm |
| Không có cấu hình lần chạy trước | Helper này chỉ hỗ trợ hội thoại đã có lượt chạy trong app |
| API/schema thay đổi sau cập nhật | Dừng gửi, đối chiếu lại mã app; không đoán endpoint hoặc payload |

Token được giữ trong bộ nhớ; script không in header, không lưu token/API key và không sửa cơ sở dữ liệu hội thoại. Do server localhost dùng chứng chỉ riêng, client bỏ kiểm tra chứng chỉ cho origin HTTPS loopback đã được giới hạn; không đổi cấu hình TLS hoặc bảo mật toàn máy.

Đây là helper cho giao thức nội bộ quan sát trên bản cài hiện tại, không phải SDK công khai hay cam kết tương thích của Google. Các biên nhận không có chữ ký số: chúng là bằng chứng thực dụng để đối chiếu với server/app, không phải chứng thực độc lập chống sửa đổi.

## 10. Phần đã thử nghiệm khi bàn giao

- Lần gửi thật đã được server nhận và xuất hiện trong bước người dùng của đúng hội thoại.
- Script bàn giao đã chạy thực tế các lệnh `list`, `status` và `verify` trên hội thoại đó; không gửi thêm yêu cầu khi viết tài liệu.
- 9 ca kiểm tra giả lập đạt: prompt nhiều dòng, nội dung không khớp, giữ cấu hình lần trước, xác nhận nội dung, chặn biên nhận trùng, không tự gửi lại khi timeout, chặn hội thoại đang chạy, chặn prompt đã có, phát hiện cổng và giới hạn origin loopback. Một ca có thể kiểm tra nhiều điều kiện.
- Các ca giả lập không tạo hội thoại hoặc gửi tin thật. Chưa dùng script bàn giao để gửi thêm một prompt mới vào app chỉ nhằm thử nghiệm.

Quy trình kiểm chứng thường dùng: **list đúng ID → status → send một lần với biên nhận mới → verify → đọc kết quả và kiểm tra thay đổi thực tế**.
