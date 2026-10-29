# Kiểm tra bản thử ngày 29/10/2026

- `py -3.12 -X utf8 -B -m unittest discover -s tests -p test_pipeline.py -v`: 14/14 đạt.
- `py -3.12 -X utf8 -B -m unittest discover -s tests -p test_danh_gia.py -v`: 4/4 đạt.
- `git diff --check -- src danh_gia tests/README.md README.md`: không có lỗi khoảng trắng.
- Không còn hàm ném `NotImplementedError` trong `src`.
- Đã đo đủ 1.136 dòng dev, không huấn luyện mô hình hoặc đọc tập test cuối.
- Kết quả dự đoán của cả 1.136 mẫu giống lần đo sơ bộ; thay đổi ở phép đo thời gian loại phần chuyển dataclass sang dict. Không điều chỉnh thuật toán hoặc trọng số dựa trên kết quả giữa hai lượt này.
- Mã băm source hiện tại trùng `code_sha256.json`. Mã băm dev và sáu danh mục được kiểm tra không đổi trong suốt lượt đo.

Các kiểm tra trên không chứng minh mọi nhãn dev hoặc mọi kết quả đều đúng; xem giới hạn và chênh lệch trong báo cáo.
