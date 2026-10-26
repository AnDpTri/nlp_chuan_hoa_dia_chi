# Nguồn và phạm vi dữ liệu runtime

`loai_moc_2025.csv` lấy loại của 34 tỉnh/thành ở bảng `data/raw/goc/conversion-table.xlsx` đã có trong repo; manifest ghi SHA-256. Đây là lớp tra cứu theo mốc 01/07/2025, không sửa sáu bảng clean được tập test ghim hash. Xem nguồn và giới hạn trong `data/raw/NGUON.md`, `data/test/README.md`; không coi bảng tổng hợp cộng đồng là văn bản pháp lý độc lập.

`streets.csv` là cơ sở tên đường dẫn xuất từ dữ liệu © OpenStreetMap contributors, trích xuất Vietnam Geofabrik ngày 24/10/2026. Nguồn: [OpenStreetMap copyright](https://www.openstreetmap.org/copyright), [Geofabrik Vietnam](https://download.geofabrik.de/asia/vietnam.html). Cơ sở dữ liệu dẫn xuất được cung cấp theo [ODbL 1.0](https://opendatacommons.org/licenses/odbl/1-0/).

Chỉ giữ tên đường trong `addr:street` và số nguồn; không đưa tên người, số điện thoại, tài khoản hoặc địa chỉ nhà cụ thể vào từ điển này. Loại 400 URL nguồn giữ lại cho đánh giá và các dòng trùng đầu vào chuẩn hóa: 456 dòng bị loại, 30.517 dòng công khai còn lại đóng góp 6.066 tên đường không mơ hồ. Không đọc cột đáp án để xây từ điển. Đây không phải phép tách biệt theo vùng địa lý hoặc theo mọi tên đường; các địa chỉ khác có thể cùng tên đường.

Kho từ điển OSM chụp năm 2026 có thể chứa tên đường chưa tồn tại ở mốc 2025. Mốc 01/07/2025 của đầu ra áp dụng cho **đơn vị hành chính**; hiện chưa có dữ liệu lịch sử đầy đủ để xác nhận mốc thời gian của từng tên đường. Nếu không tìm được tên duy nhất, giữ tên đầu vào và gắn cờ chưa khôi phục dấu.
