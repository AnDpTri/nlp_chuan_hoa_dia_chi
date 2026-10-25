# Báo cáo tiến độ tuần 3

**Đề tài:** Xây dựng hệ thống chuẩn hóa địa chỉ tiếng Việt theo đơn vị hành chính mới sau sáp nhập 2025

**Môn:** Xử lý ngôn ngữ tự nhiên, lớp KHMT K22A

---

## 1. Tóm tắt

Nhóm đã chốt đề tài và phạm vi, viết xong đặc tả bài toán, thu thập và làm sạch toàn bộ dữ liệu đơn vị hành chính (cũ, mới và bảng đối chiếu), và có thiết kế sơ bộ cho hệ thống. Chưa bắt đầu code hệ thống chuẩn hóa.

## 2. Đã hoàn thành

### 2.1. Đề tài và phạm vi
- Đổi đề tài từ "mod trò chuyện với NPC Stardew Valley bằng LLM" sang đề tài chuẩn hóa địa chỉ, vì đề cũ khó đánh giá định lượng và phần NLP chưa rõ.
- Viết đặc tả bài toán (`bai_toan.md`): đầu vào, đầu ra theo từng trường, quy tắc xử lý, ví dụ, phạm vi, ràng buộc, cách đánh giá.
- Các quyết định chính:
  - Chuẩn hóa là mục tiêu chính; phân loại theo khu vực có được sau khi chuẩn hóa.
  - Chuyển địa chỉ cũ sang mới đến cấp sâu nhất (tỉnh và xã/phường). Cấp huyện chỉ dùng để xác định, không xuất ra.
  - Số nhà, ngõ, thôn/xóm, tên đường không đổi theo luật, chỉ chuẩn hóa cách viết.
  - Thiếu thông tin thì để trống, không chắc chắn thì gắn cờ cảnh báo.
  - Chạy offline, không dùng LLM, không gọi API; tốc độ là tiêu chí quan trọng.
- Lập board Trello cho nhóm.

### 2.2. Dữ liệu đơn vị hành chính
Thu thập từ danh mục hành chính của Tổng cục Thống kê, bảng chuyển đổi theo Quyết định 19/2025/QĐ-TTg và các nghị quyết của UBTVQH (qua bộ tổng hợp mở `vietnam-address-kit`). Nguồn và ngày truy cập ghi trong `data/raw/NGUON.md`.

| Bộ dữ liệu | Số lượng |
|---|---|
| Danh mục mới (sau 1/7/2025) | 34 tỉnh, 3.321 xã/phường/đặc khu |
| Danh mục cũ (trước sáp nhập) | 63 tỉnh, 696 huyện, 10.033 xã/phường/thị trấn |
| Bảng đối chiếu xã cũ sang xã mới | 10.571 dòng, trong đó 441 xã cũ bị chia ra nhiều xã mới |

### 2.3. Làm sạch và kiểm tra dữ liệu
- Viết script làm sạch và tự kiểm tra (`data/clean/scripts/clean_and_validate.py`). Dữ liệu gốc giữ nguyên, bản sạch sinh lại được bất cứ lúc nào.
- Các lỗi đã phát hiện và sửa (có ghi căn cứ trong `sua_doi.csv`):
  - Tên tỉnh cũ ghi không thống nhất (Quảng Trị), làm đếm ra 64 tỉnh.
  - Thành phố Tân An (Long An) bị gán nhầm sang Tiền Giang.
  - Một số xã có mã và tên không khớp giữa các bảng, tên mất dấu, sai loại đơn vị.
  - Lỗi đặt dấu thanh phát sinh trong bước làm sạch (Hoàng thành Hòang), đã sửa và thêm phép kiểm tra để không tái diễn.
  - Hai xã nghi vấn ở Cao Bằng và Tuyên Quang, đã xác minh theo nghị quyết sắp xếp năm 2025.
- Kết quả kiểm tra: không trùng mã, mọi liên kết giữa các bảng đều hợp lệ, xã cũ nào cũng có đích đến, xã mới nào cũng có nguồn, mỗi tỉnh cũ ứng với đúng một tỉnh mới, bỏ dấu đi thì tên khớp hoàn toàn với dữ liệu gốc.

### 2.4. Khảo sát các công trình liên quan
- Thư viện mã nguồn mở: `vietnamadminunits`, `vietnam-address-converter`, `vietnamese-address-parser`, parser địa chỉ của underthesea.
- API thương mại: TrackAsia, Vietmap.
- Nhận xét: các công cụ hiện có chủ yếu dựa trên luật và tra từ điển, nhiều công cụ cần đầu vào khá sạch. Chưa thấy công trình học thuật nào giải bài này bằng học máy. Nhóm sẽ dùng hai thư viện đầu làm mốc so sánh.

### 2.5. Thiết kế sơ bộ
- Pipeline: tiền xử lý → sinh ứng viên → ghép đường đi hợp lệ trên cây hành chính → tách số nhà, ngõ, thôn, đường → chuyển đổi cũ sang mới → sinh đầu ra.
- Ý tưởng chính: giải cả địa chỉ cùng lúc, chọn tổ hợp thành phần tạo thành một đường đi có thật trong cây hành chính, để các thành phần hỗ trợ nhau gỡ nhập nhằng.
- Cấu trúc dữ liệu: trie (tìm tên trong chuỗi, chịu được mất dấu, viết tắt, sai chính tả) và cây hành chính cũ, mới có cạnh đối chiếu.
- Mô hình dự kiến (nhẹ, chạy CPU): logistic regression để chấm điểm đường đi, CRF để tách số nhà, ngõ, thôn, đường. Có thể nâng lên LightGBM nếu cần.
- Công nghệ: Python. Làm cho chạy được trước, tối ưu sau.

## 3. Vấn đề còn tồn tại
- **Mốc dữ liệu:** dữ liệu đang theo mốc 1/7/2025. Năm 2026 có thêm thay đổi (Đồng Nai, Quảng Ninh, Bắc Ninh lên thành phố trực thuộc trung ương, 23 xã lên phường), đã lưu riêng nhưng chưa chốt có áp dụng không.
- **Xã bị chia:** văn bản chính thức phần lớn chỉ ghi "nhập một phần", không nói rõ thôn/xóm nào về đâu. Với các xã này, hệ thống nhiều khả năng chỉ gắn cờ được.
- **Chưa có tập test:** chưa có địa chỉ thật nào được gán nhãn.

## 4. Kế hoạch tuần 4
1. Gom 300–500 địa chỉ thật và gán nhãn làm tập test; hai người gán nhãn độc lập một phần để kiểm tra độ thống nhất.
2. Viết script đánh giá theo mục 9 của đặc tả.
3. Chạy hai thư viện có sẵn trên tập test để lấy mốc so sánh.
4. Bắt đầu làm bản đơn giản (trie, cây hành chính, điểm đặt bằng tay) chạy được từ đầu đến cuối.
5. Chia việc cụ thể cho các thành viên trên Trello.
