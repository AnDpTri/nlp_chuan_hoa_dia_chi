# Keep-alive trong tab Colab

Mở DevTools của tab Colab (F12), chọn Console, dán nội dung `keep_alive.js`
và Enter một lần. Script tự đặt timer ngẫu nhiên 90–150 giây, chạm nút tài
nguyên khi thấy runtime đang kết nối. Không chạy lại ô, không reload trang,
không tự reconnect, không gửi mã hay dữ liệu sang dịch vụ khác.

- Trạng thái: `colabKeepAlive.status()`.
- Thử một lượt ngay: `colabKeepAlive.pulse()`.
- Dừng: `colabKeepAlive.stop()`.

Script cần được khởi chạy trong Console, không phải ô Python. Khi reload
hoặc đóng tab, script kết thúc. Timer/nhấn bằng JavaScript không được Google
bảo đảm là hoạt động giữ phiên; phiên vẫn có thể ngắt. Checkpoint trên Drive
vẫn giữ nguyên. File này chưa được cài/chạy vào tab chỉ bằng việc lưu vào dự án.
