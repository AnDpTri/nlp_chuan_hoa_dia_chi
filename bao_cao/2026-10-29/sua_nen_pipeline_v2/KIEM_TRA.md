# Kiểm chứng sửa nền v2 — 29/10/2026

- `py -3.12 -X utf8 -B -m unittest discover -s tests -p test_pipeline.py -q`: 30 bài đạt.
- `py -3.12 -X utf8 -B -m unittest discover -s tests -p test_danh_gia.py -q`: 4 bài đạt.
- `git diff --check -- src danh_gia tests/test_pipeline.py`: đạt, không lỗi khoảng trắng.
- Đã đo đủ 1.136 mẫu dev và đối chiếu với bản v1_02: cùng mã băm dev, cùng mã băm sáu danh mục.
- Mã băm source được kiểm tra lại sau phép đo, trùng `code_sha256.json`.
- Bản snapshot mã băm train/dev và các CSV sạch trước sửa được kiểm tra lại: không có file nào thay đổi.
- Không chạy script sinh lại dữ liệu hoặc đồng bộ duyệt, không dùng nhãn test cuối để sửa lõi. Các thay đổi của hai hội thoại agy nằm ngoài phạm vi sửa này.
- So sánh trước–sau có đủ input, output v1, output v2, nhãn tham chiếu, trường lệch và cảnh báo của từng ID trong `so_sanh_tung_mau.csv`.

Các kiểm tra này xác nhận những hành vi đã thử và tính tái lập của phép đo, không chứng minh toàn bộ địa chỉ ngoài thực tế đều được xử lý đúng.
