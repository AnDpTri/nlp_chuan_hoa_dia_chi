# Address May Cry — giao diện ứng dụng

Đang triển khai song song: A thương hiệu/shell/chuẩn hóa đơn; B xử lý hàng loạt; C API engine thật. Hợp đồng chung tại web/address-may-cry/CONTRACT.md. Mỗi phiên phải tự cài và đọc https://github.com/Leonxlnx/taste-skill, áp dụng nhánh app screens và tự kiểm tra trong browser. Yêu cầu trực tiếp: sáng tạo có chủ đích, mỗi chi tiết có ý nghĩa, đẹp và hiệu quả.

Chưa hoàn thành, chưa có ảnh/bản build được nghiệm thu tại lúc giao việc. Mã frontend tại web/address-may-cry/, backend tại web/address-may-cry/api/, tài liệu từng phần và design rationale tại thư mục này.

## Đã giao việc

Cả ba phiên xác nhận nhận đúng prompt và RUNNING lúc 09:01 ngày30/10/2026 (Asia/Saigon).

| Phần | Hội thoại | Phạm vi |
|---|---|---|
| A — thương hiệu, single, shell, tích hợp | Vietnamese Address Normalization Project Research | web/address-may-cry ngoại trừ shared/batch/api; A_design/ |
| B — batch, CSV, progress, review, export | Bổ Sung Train Địa Chỉ Khó | src/features/batch/; B_batch/ |
| C — API nối engine thật, localhost server | Chuẩn Hóa Dữ Liệu Địa Chỉ | api/; C_api/ |

Prompt và biên nhận xác nhận tại docs/antigravity_rpc/yeu_cau_ui_address_may_cry_{A,B,C}_20261030.txt và lan_gui_ui_address_may_cry_{A,B,C}_20261030.json (tính từ gốc dự án). Mỗi phiên được yêu cầu tự cài taste-skill, ghi nguồn/commit, thực hiện browser QA và lưu giải thích thiết kế. Chưa tuyên bố đã cài hoặc hoàn thành trước khi có bằng chứng bàn giao.
