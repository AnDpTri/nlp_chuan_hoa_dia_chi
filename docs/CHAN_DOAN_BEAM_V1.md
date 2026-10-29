# Chẩn đoán phần thiếu phương án — 29/10/2026

Chỉ chạy lại các câu chưa khớp dev khó: 168 câu CNN+ranker và 165 câu
ViDeBERTa+điểm tay. Các output sáu trường tái hiện đúng lượt đo ma trận.
Không train, sửa nhãn hoặc đổi lõi; không đọc test cuối.

## Phân loại đủ các câu sai

Các nhóm dưới đây loại trừ nhau, được tính trên toàn bộ beam, không chỉ output:

| Nhóm | CNN | ViDeBERTa |
|---|---:|---:|
| Có đáp án đúng trong beam, output chưa khớp | 13 | 13 |
| Beam chỉ thiếu phục hồi dấu để khớp sáu trường | 56 | 57 |
| Khác dấu/khoảng trắng/dấu câu | 1 | 1 |
| Có mã hành chính đúng, chi tiết chưa khớp | 94 | 91 |
| Không có mã hành chính đúng và cũng thiếu chi tiết đúng | 4 | 3 |
| **Tổng chưa khớp output** | **168** | **165** |
| **Trong đó chưa có đáp án sáu trường trong beam** | **155** | **152** |

Trong nhóm 94/91 câu có hành chính đúng nhưng chi tiết sai:

| Nhóm nhỏ, phân loại cơ học theo phương án gần reference nhất | CNN | ViDeBERTa |
|---|---:|---:|
| Thừa chữ đầu tên; có thể là tiền tố nhập lỗi chưa được xử lý | 53 | 54 |
| Span model không khớp nhãn span | 10 | 7 |
| Reference đường trống nhưng phương án có đường, cần rà soát | 18 | 18 |
| Nội dung chi tiết khác, còn cần rà soát | 13 | 12 |

Nhóm nhỏ là dấu hiệu kiểm tra, không phải chứng nhận nguyên nhân ngữ nghĩa
của từng câu. Phương án gần nhất dùng reference để chẩn đoán hậu kiểm, không
được dùng làm output triển khai.

## Bằng chứng lỗi sau nhận diện

Trong các câu chưa có đáp án sáu trường, cả hai model đều có **144 câu span
chi tiết gốc khớp hoàn toàn reference span**, nhưng output chuẩn hóa chưa đủ.
Ở ViDeBERTa chỉ 8/165 câu sai output có span chi tiết không khớp; CNN 11/168.
Span reference này cũng là nhãn máy/tổng hợp nên chưa chứng minh model đúng
ngữ nghĩa trong mọi ca. Tuy nhiên, nó xác định rõ lỗi so với chính hợp đồng
nhãn đang đo chủ yếu xuất hiện sau nhận diện.

Ví dụ thực tế VNDEV_KHO_00005:

- Input: `118 dduowngf Hùng Vương, phuowngf Tân Sơn Nhì, Quận Tân Phú, Thành phố Hồ Chí Minh`.
- Reference: `Đường Hùng Vương`.
- Phương án gần nhất: `Đường Dduowngf Hùng Vương`; số nhà và hai mã hành chính khớp.
- Model đã khoanh được đoạn đường, nhưng bộ định dạng không giải tiền tố
  gõ Telex lỗi nên giữ nó trong thân tên, rồi thêm một tiền tố `Đường` nữa.

Một ca khác VNDEV_KHO_00016 có `d. quoc lo 14b`: reference `Quốc lộ 14B`,
phương án xuất `Đường Quoc Lo 14b`. Cần xử lý tiền tố lồng và quy tắc định
dạng; đổi encoder không tự sửa logic này.

18 ca reference đường trống được đánh dấu cần rà riêng. Chưa kết luận cả
18 nhãn sai, không điền hay xóa nhãn để tăng điểm. 12/13 ca nội dung khác
và 3/4 ca thiếu cả hành chính lẫn chi tiết vẫn cần đọc từng trường trước khi
khẳng định nguyên nhân cụ thể.

## Hướng sửa sau chẩn đoán

1. Sửa bộ định dạng tiền tố/Telex và tiền tố lồng theo cấu trúc chung, có
   fixture độc lập, giữ dấu vết chữ gốc. Đo riêng trước/sau, chưa train thêm.
2. Bổ sung tên có dấu có căn cứ để tăng độ phủ; không đoán dấu tùy ý hoặc lấy
   nhãn dev làm từ điển. 57/56 ca trên là nhu cầu đối chiếu, chưa đồng nghĩa
   mọi tên đều có thể xác minh từ nguồn bên ngoài.
3. Rà nhóm reference trống và nội dung khác bằng chứng riêng. Sau đó mới xét
   13 ca chọn/từ chối mơ hồ dù beam có đáp án và số ít lỗi span/admin.

## File kiểm chứng

- [Thống kê](../danh_gia/ket_qua/chan_doan_beam_v1_01/thong_ke.json).
- [ViDeBERTa: đủ 165 câu, input/nhãn/output/span/phương án gần nhất/toàn beam](../danh_gia/ket_qua/chan_doan_beam_v1_01/videberta_tung_cau.jsonl).
- [CNN: đủ 168 câu và toàn beam](../danh_gia/ket_qua/chan_doan_beam_v1_01/cnn_tung_cau.jsonl).
- [Script tái hiện](../danh_gia/chan_doan_beam.py).

Lượt này dừng ở chẩn đoán. Chưa áp dụng các hướng sửa nêu trên.
