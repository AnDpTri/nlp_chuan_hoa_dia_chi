# Address May Cry — hợp đồng phối hợp UI/API

Mục tiêu: một ứng dụng chuẩn hóa địa chỉ tiếng Việt dùng được, có cá tính thương hiệu, xử lý input lẫn mốc cũ/mới mà không bắt chọn mốc nguồn. Đích hành chính 01/07/2025. Không phải trang quảng cáo hoặc mockup. Không bịa độ chính xác/confidence/geocoding.

Frontend React + TypeScript + Vite trong thư mục này; dev5173 proxy /api tới127.0.0.1:8080. Backend Python adapter trong api/, không sửa src/ NLP. Cùng origin khi serve dist bằng backend. Mọi route /api/v1/. Client/types tại src/shared là hợp đồng chung đã tạo, không sửa tuỳ ý.

- GET health: {status:'ok'|'loading'|'error',engine:string,target_date:'2025-07-01',limits:{max_chars:2048,max_batch:100},message?:string}
- POST normalize body {address:string}; HTTP200 NormalizeResponse theo shared/contracts.ts. HTTP400/413/503 lỗi {error:{code,message}}.
- POST batch body {addresses:[{id:string,address:string}]} max100; HTTP200 {items:BatchItem[],elapsed_ms:number}. Từng lỗi trong item giữ id/input và error, không mất thứ tự. UI gửi chunk20, giới hạn1000hàng/phiên, dừng gửi chunk mới khi huỷ. Không hứa giết inference request đã chạy.
- result là dataclass KetQua thực từ pipeline (giữ Unicode, cảnh báo, candidate xã mới, dấu vết nếu có). status needs_review khi backend xác định có cảnh báo/thiếu/mơ hồ; processed chỉ có nghĩa đã xử lý, không phải verified. elapsed_ms là số đo thực.
- Đầu ra chi tiết mới (bổ sung tùy chọn trong NormalizeResponse và BatchItem):
  + thanh_phan: danh sách thành phần theo thứ tự xuất hiện, phủ toàn bộ chuỗi đầu vào (trừ khoảng trắng/dấu phân cách). Mỗi phần tử gồm { doan_goc, bat_dau, ket_thuc, nhan_la ('so_nha'|'ngo_ngach_hem'|'thon_xom'|'duong'|'xa'|'huyen'|'tinh'|'bo_qua'), chuan_hoa, doi_chieu ('co'|'khong'|'bo_qua'), ly_do (câu tiếng Việt ngắn giải thích chuyển đổi/phân loại), ket_qua_moi (tên đơn vị mới sau 01/07/2025; 'Không còn cấp huyện' với huyện; giống chuẩn hóa với chi tiết; rỗng với bỏ qua) }.
  + ket_qua_hai_dong: gồm co_doi_chieu { xa_phuong, ma_xa, tinh, ma_tinh, chuoi } và thieu_du_lieu_doi_chieu { so_nha, ngo_ngach_hem, thon_xom, duong, chuoi, ghi_chu: 'Chỉ chuẩn hóa cách viết, không có dữ liệu để kiểm đúng sai' }. Không có cấp huyện ở kết quả mới.

Phân công: A sở hữu toàn bộ shell, src/App.tsx, main, index/css/tokens và single feature, package/config/README/artdirection. B CHỈ src/features/batch/** và docs/ui-address-may-cry/B_batch/**. C CHỈ api/** và docs/ui-address-may-cry/C_api/**. Không sửa src/shared nếu chưa đồng thuận; A chỉ đọc/import B. Không sửa mã/dữ liệu/model NLP. Không commit/push/deploy. Không đọc test NLP hoặc dùng test làm demo.

BatchWorkspace.tsx default export React component với props {onInspect?:(item:BatchItem)=>void}; B không tạo shell/main/global CSS và dùng CSS variables: --ground,--surface,--raised,--active,--border,--control,--text,--muted,--accent,--positive,--negative,--font,--radius-card,--radius-control,--gap. Fallback biến trong CSS module nếu A chưa xong. A import './features/batch/BatchWorkspace' và ghép khi file có.

Nội dung UX: Chuẩn hóa một địa chỉ, dán danh sách/CSV chọn cột, tiến độ theo dòng thực, lọc cần kiểm tra/lỗi, xem input/output và6trường+nhãn hành chính, lý do cảnh báo và ứng viên nếu có, sao chép/xuấtCSV/JSON. Các ví dụ chỉ điềninput, gọi engine thật khi chạy; lịch sử theo phiên, không tự lưu rawđịa chỉ vào localStorage. Không login/avatar/KPI giả/map giả/độ tin cậy giả. Không ép chọn cũ/mới. Không hiển thị đầu ra thành chắc chắn khi thiếu căn cứ.

Mọi thành phần phải có mục đích; typography, spacing, màu, chuyển động, hình ảnh phải giải thích được tác dụng trong docs/ui-address-may-cry. Chữ Việt đủ dấu, tương phản/focus/keyboard/touch44px, reducedmotion, mobile390/tablet768/desktop1440. Giữ sáng tạo mạnh; yêu cầu sáng tạo trực tiếp có ưu tiên hơn gu mặc định của skill. Không lấy texture/logo/nhạc game Devil May Cry; thương hiệu Address May Cry có bộ nhận diện riêng.
