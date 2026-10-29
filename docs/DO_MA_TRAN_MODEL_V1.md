# Đo lại các phương pháp, giữ checkpoint — 29/10/2026

Đã chạy 12 cấu hình trên cùng 1.136 dev gốc và 464 dev khó, cùng snapshot
hành chính và cùng CPU laptop một luồng. Không train/tune thêm, không đọc test
cuối và không gọi API mô hình. Các nhánh sửa dùng cùng từ điển train và cùng
cơ chế bảo vệ đường; luật không có span model nên phần bảo vệ span không tác động.

| Phương pháp | Dev gốc cũ → sửa | Dev khó cũ → sửa |
|---|---:|---:|
| Luật, điểm tay | 76,585 → 80,810% | 49,138 → 51,940% |
| CRF, điểm tay | 78,785 → **83,011%** | 59,052 → 62,284% |
| CNN, điểm tay | 77,993 → 82,218% | 60,560 → 63,793% |
| CNN, ranker | 78,609 → 82,835% | 60,345 → 63,793% |
| ViDeBERTa, điểm tay | 77,289 → 81,514% | 61,207 → **64,440%** |
| ViDeBERTa, ranker | 77,377 → 81,602% | 60,776 → 64,009% |

Đây là độ khớp nhãn máy/tổng hợp trên dev đã dùng phát triển, chưa phải gold
độc lập. Ranker của mỗi model được kiểm đúng checkpoint và danh mục lúc train.

## Kết luận của lượt đo

- Model có tác động: ViDeBERTa điểm tay hơn CNN điểm tay 3 câu dev khó,
  nhưng ít hơn 8 câu dev gốc. CRF tốt nhất dev gốc, ViDeBERTa tốt nhất dev khó;
  chưa có bộ nhận diện thắng mọi phía. Ranker hiện không tăng chất lượng đồng đều.
- Đổi model chưa giải quyết phần lớn lỗi. Với hai bản ranker đã sửa:
  dev gốc 912 cùng đúng, 29 chỉ CNN đúng, 15 chỉ ViDeBERTa đúng, 180 cùng sai;
  dev khó 292 cùng đúng, 4 chỉ CNN đúng, 5 chỉ ViDeBERTa đúng, 163 cùng sai.
  Đây là hậu kiểm bằng nhãn, không phải cơ chế chọn model lúc triển khai.
- Beam CNN sau sửa chỉ có phương án khớp sáu trường ở 976/1.136 và 309/464;
  ViDeBERTa tương ứng 963/1.136 và 312/464. Với tập phương án hiện có, chọn
  hoàn hảo cũng còn thiếu nhiều. Không quy hết cho ranker hoặc khẳng định trần
  của kiến trúc model: thiếu tên chuẩn, lỗi phân đoạn và nhãn yếu đều có thể
  làm phương án tham chiếu vắng mặt.
- F1 span trên cùng tập char reference 1.026/464 câu: CNN 98,132/98,761%,
  ViDeBERTa 97,566/98,925%, CRF 98,573/97,032%. Số CRF này dùng chuẩn raw
  char và cùng 464 câu khó, khác phép đo token/subset 452 câu ở báo cáo cũ.
- Giữ CNN làm mốc để sửa lõi là hợp lý về chi phí, nhưng không bỏ ViDeBERTa
  khỏi đối chứng. Chưa có căn cứ train lớn hơn ngay hoặc kỳ vọng thay model
  riêng sẽ đưa kết quả tới 95%.

## Tốc độ và kiểm chứng

Mỗi extractor chỉ chạy một lần/câu; từng nhánh dùng bản sao context riêng để
tránh rò trạng thái. Thời gian báo cáo là tổng extract đo thực tế + phần
pipeline riêng, không gồm deepcopy cache, khởi tạo, JSON/I/O hoặc oracle hậu
kiểm. Không gọi đây là các lượt end-to-end độc lập. Trên lượt này CNN ranker
sau sửa khoảng 20,84/22,38 ms, ViDeBERTa ranker 105,76/106,73 ms; tải nền
có thể ảnh hưởng tốc độ. Phép đo chủ yếu phục vụ đối chứng chất lượng.

Các baseline tái hiện mọi trường output cũ. ViDeBERTa điểm tay có chênh lệch
score số thực/làm tròn giữa CPU laptop và Colab; mọi trường output/cảnh báo/
trace còn lại giống. Các baseline khác giống toàn bộ prediction. Hash các
file đã ghim được kiểm lại sau đo; code có bản sao và SHA-256.

- [Bảng đủ 12 cấu hình](../danh_gia/ket_qua/ma_tran_v1_01/BAO_CAO.md).
- [Thống kê từng tầng, trường, span và latency](../danh_gia/ket_qua/ma_tran_v1_01/thong_ke.json).
- [Đối chiếu từng câu dev gốc](../danh_gia/ket_qua/ma_tran_v1_01/doi_chieu_dev_goc.jsonl).
- [Đối chiếu từng câu dev khó](../danh_gia/ket_qua/ma_tran_v1_01/doi_chieu_dev_kho.jsonl).
- [Kiểm chứng tái hiện](../danh_gia/ket_qua/ma_tran_v1_01/KIEM_CHUNG.json).

Lượt này dừng ở đo và kết luận; chưa sửa thêm thuật toán hoặc tích hợp dữ liệu agy.
