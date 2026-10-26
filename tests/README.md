# Kiểm tra nhanh

Vài chục ca mẫu kèm đáp án để chạy sau mỗi lần sửa code. Đây không phải tập test dùng để chấm điểm trong báo cáo (tập đó nằm ở `data/test`).

Chạy `python -m unittest discover -s tests -v` sau khi cài `requirements.txt`. Các ca chỉ dùng ví dụ trong đặc tả và danh mục công khai, không lấy nhãn của 400 địa chỉ held-out. Kiểm tra gồm hash danh mục, Unicode, viết tắt, sửa một lỗi, phân cấp, xã bị chia, mâu thuẫn tỉnh, không suy diễn xã từ tên đường, CSV/Excel và quy tắc chỉ chấm nhãn đã duyệt.
