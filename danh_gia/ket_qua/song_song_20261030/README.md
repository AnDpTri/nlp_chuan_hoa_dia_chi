# Ba nhiệm vụ agy song song — 30/10/2026

Đã gửi và xác nhận prompt có trong cả ba hội thoại, trạng thái RUNNING tại lúc giao việc. Mỗi nhiệm vụ ghi riêng; không được sửa src/checkpoint/dữ liệu gốc, không đọc test, không train hoặc tiếp tục loop95%. Khoảng15–20phút là phạm vi công việc mong muốn, không phải bảo đảm thời gian hoàn thành.

| Việc | Hội thoại agy | Phạm vi đầu ra |
|---|---|---|
| A: Oracle cùng hậu xử lý inference, đối chứng điểm tay/LightGBM | Vietnamese Address Normalization Project Research | A_oracle/ |
| B: Tách lỗi span, định dạng, tên chuẩn và nhãn nghi vấn | Bổ Sung Train Địa Chỉ Khó | B_chi_tiet/ |
| C: Prototype sinh nhiều ứng viên tên đường, chưa thêm model | Chuẩn Hóa Dữ Liệu Địa Chỉ | C_ung_vien_duong/ |

Baseline chung ở BASELINE_MANIFEST.json. Prompt và biên nhận ở docs/antigravity_rpc/yeu_cau_song_song_{A,B,C}_20261030.txt và lan_gui_song_song_{A,B,C}_20261030.json, tính từ gốc dự án. Chỉ nghiệm thu sau khi đối chiếu số liệu và kiểm tra baseline không đổi. Không đồng nhất candidate coverage với end-to-end accuracy. Các kết quả chưa có lúc lập kế hoạch này.
