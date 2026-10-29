# Sửa thiếu ứng viên hành chính — 29/10/2026

Đã xử lý hai nguyên nhân theo cấu trúc, không thêm ID/địa danh vào luật:

1. Tiền tố gõ Telex được nhận dạng từ từ vựng loại chuẩn bằng bộ mã hóa,
   gồm dấu thanh/biến thể gõ ươ. Chỉ khớp toàn từ tiền tố; không fuzzy tên
   riêng và không cho số đứng một mình tự trở thành phường. Ví dụ `phuowngf`
   được hiểu là cách gõ Phường để tra phần tên phía sau.
2. Ranh giới span model không được phủ quyết tokenization gốc. Nhánh tra
   cứu lexical gốc và nhánh token đã chia theo model đều sinh ứng viên;
   chiếu về cùng vị trí ký tự rồi gộp theo span/mốc/mã, không cộng điểm lặp.
   Không đặt thêm trọng số hoặc threshold theo các lỗi đã xem.

Ví dụ kiểm tra cho thấy ViDeBERTa chia `phuowngf` thành `phuown` + `gf`.
Chỉ sửa nhận dạng tiền tố chưa giúp được backend này. Giữ thêm nhánh lexical
giải quyết việc tiền tố hợp lệ bị phá do ranh giới model. Giữ dấu vết input gốc.

## Đo lại, không train thêm

| Model | Dev gốc | Dev khó trước → sau | Được/mất |
|---|---:|---:|---:|
| CNN + ranker | Giữ 941/1.136 — 82,835% | 333 → 337/464 — 72,629% | 4/0 |
| ViDeBERTa + điểm tay | Giữ 926/1.136 — 81,514% | 336 → 340/464 — 73,276% | 4/0 |

Bốn ca thiếu ứng viên ban đầu đã khớp mã đích theo reference. Ca Tam Dan
vẫn để mã xã trống và giữ cảnh báo mơ hồ; không ép một đích để tăng điểm.

87 bài unit test liên quan PASS, có fixture độc lập theo loại/số/tên khác,
ca không được sửa, NFD, ánh xạ giữa hai lưới và chống nhân đôi ứng viên.
Checkpoint, từ điển, nhãn giữ nguyên; dữ liệu927 mẫu bổ sung chưa được dùng.

Điểm là khớp nhãn máy/tổng hợp trên dev đã xem, không chứng minh tổng quát
hóa. Chỉ đo lại hai cấu hình này; chưa suy kết quả cho mọi backend/chế độ.
Giới hạn beam, cách chấm điểm và thiếu tên chuẩn vẫn tồn tại.

- [Số đo đầy đủ](../danh_gia/ket_qua/sua_tien_to_hanh_chinh_v2_01/BAO_CAO.md).
- [Output/các câu thay đổi](../danh_gia/ket_qua/sua_tien_to_hanh_chinh_v2_01/thay_doi_tung_cau.jsonl).
- [Bốn ca sửa và ca giữ mơ hồ](../danh_gia/ket_qua/sua_tien_to_hanh_chinh_v2_01/CAC_CA_KIEM_CHUNG.json).
- [Thống kê/hash](../danh_gia/ket_qua/sua_tien_to_hanh_chinh_v2_01/thong_ke.json).

Lượt chỉ sửa tiền tố trước khi bổ sung nhánh lexical được lưu riêng ở
`danh_gia/ket_qua/sua_tien_to_hanh_chinh_v1_01/` để thấy tác dụng từng bước.
