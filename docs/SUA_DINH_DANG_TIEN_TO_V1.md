# Sửa định dạng tiền tố đường — 29/10/2026

Đã sửa `dinh_dang_span` dùng chung CRF/CNN/ViDeBERTa. Chỉ nhận các cách
gõ Telex rõ ràng ở đầu span đường (`dduowngf`, `dduwowngf`, các biến thể
tương ứng, `phoos`); không fuzzy tên riêng. Giữ nguyên dấu đã nhập.

Tiền tố chung `Đường`/`d.` đứng trước `Quốc lộ`/`Tỉnh lộ` và số tuyến được
định dạng theo loại cụ thể, ví dụ `d. ql 8a` → `Quốc lộ 8A`. Không xóa
`Phố` trong `Đường Phố Mới`, không đổi `Dương Quảng Hàm`, không sửa số nhà.
Thân tên chưa có dấu vẫn cần dữ liệu tra cứu có căn cứ; sửa này không đoán dấu.

Giữ nguyên checkpoint, ranker, từ điển train và toàn bộ nhãn. So sánh với
pipeline đã có tra tên/bảo vệ đường trong lượt ma trận trước:

| Model | Dev gốc trước → sau | Dev khó trước → sau | Được/mất dev khó |
|---|---:|---:|---:|
| CNN + ranker | 941 → 941/1.136 (82,835%) | 296 → 333/464 (71,767%) | 37/0 |
| ViDeBERTa + điểm tay | 926 → 926/1.136 (81,514%) | 299 → 336/464 (72,414%) | 37/0 |

Không mất câu vốn khớp đủ sáu trường trên hai tập đo. Đây là độ khớp nhãn
máy/tổng hợp trên dev đã dùng phát triển, không phải gold độc lập. Không
khẳng định an toàn cho mọi input từ kết quả này.

73 unit test liên quan PASS; có fixture độc lập cho Telex, tuyến có tiền tố
lồng, dấu đã nhập, Unicode NFD, số nhà và các tên riêng dễ bị xóa nhầm.
Trong phép đo kiểm mọi trace trỏ đúng input gốc và không chồng vị trí.
Hash các model, ranker, từ điển và CSV dev được ghim khớp trước/sau.

- [Số đo và tốc độ](../danh_gia/ket_qua/sua_dinh_dang_v1_01/BAO_CAO.md).
- [Mọi câu thay đổi: input/nhãn/trước/sau](../danh_gia/ket_qua/sua_dinh_dang_v1_01/thay_doi_tung_cau.jsonl).
- [Thống kê/hash](../danh_gia/ket_qua/sua_dinh_dang_v1_01/thong_ke.json).
- [Output CNN dev khó](../danh_gia/ket_qua/sua_dinh_dang_v1_01/cnn_ranker_dev_kho.jsonl).
- [Output ViDeBERTa dev khó](../danh_gia/ket_qua/sua_dinh_dang_v1_01/videberta_tay_dev_kho.jsonl).

Chỉ đo lại hai cấu hình trên để tiết kiệm chi phí. Chưa đo lại đầy đủ luật,
CRF và các biến thể chọn phương án sau sửa này. Chưa train thêm, tích hợp
dữ liệu agy hoặc sửa những nhóm lỗi khác.
