# Dữ liệu dưới xã cho các xã cũ bị chia

Mục tiêu: biết thôn, xóm, tổ dân phố, đường (và dải số nhà) nào của 440 xã cũ bị chia đã về xã mới nào, để bước chuyển đổi trả được kết quả thay vì để trống.

- `tao_danh_sach.py`: lập danh sách 440 xã cũ bị chia, chia 3 luồng thu thập (luồng 1 Hà Nội 199 xã; luồng 2 phía Bắc và Bắc Trung Bộ 117 xã; luồng 3 còn lại 124 xã).
- `prompt_mau.txt`: yêu cầu giao cho agy; bản riêng từng luồng ở `rieng/du_lieu_duoi_xa/luong_<n>/prompt.txt`.
- `kiem_tra.py`: cổng kiểm. Một dòng chỉ được nhận khi: xã cũ thuộc danh sách bị chia, xã mới là đích hợp lệ của xã cũ theo bảng đối chiếu, có file nguồn gốc và bản văn bản đã lưu, trích dẫn có nguyên văn trong văn bản và nhắc đúng tên, không mâu thuẫn với dòng khác.

Dữ liệu thu được nằm ở `rieng/du_lieu_duoi_xa/` (chưa rõ giấy phép từng nguồn nên chưa đưa lên git). Kết quả cổng kiểm: `rieng/du_lieu_duoi_xa/ket_qua/`.
