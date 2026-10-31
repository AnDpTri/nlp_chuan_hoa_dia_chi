# Kiểm tra độc lập kết quả chẩn đoán ứng viên — 30/10/2026

Đã đọc báo cáo, JSON số liệu, 220 dòng lỗi dev và mã danh_gia/chan_doan_ung_vien_20261030.py. SHA256 các file có hash trong manifest đều còn khớp. Không chạy thêm test hoặc huấn luyện.

## Các kết quả dùng được

- Dev gốc: heuristic929/1136=81,78%, ranker916/1136=80,63%. Dev khó: cả hai330/464=71,12%. Riêng cấu hình hiện tại, LightGBM chưa chứng minh tốt hơn điểm tay trên dev; không suy ra mọi ranker đều vô ích.
- Hybrid gọi Transformer5ca dev gốc,1ca dev khó, không thay đổi sáu trường đầu ra. Điều này đánh giá cơ chế ghép hiện tại, không phủ nhận năng lực của ViDeBERTa hoặc mọi thiết kế mô hình liên kết.
- Nhóm gắn nhãn lỗi chi tiết112ca có95ca khác trường đường,24số nhà,8ngõ,1thôn. Các cờ có thể chồng nhau. Đây là khác output với ref, không phải95ca sai span.
- Lưới tokenCNN/Vi khác trên13ca dev gốc; ghép theo cùng token index có rủi ro. Chưa đo13ca đó có nằm trong5ca fallback hay không.

## Sai sót khiến chưa chấp nhận kết luận chính

1. Oracle bị giảm do ưu tiên nhãn lỗi:982ca có giả thuyết6trường khớp ở phép oracle của script. Trong220ca top1 sai, thực tế67ca oracle true:38được gọi ranking sai và29bị chuyển sang mơ hồ/nhãn nhiễu. Không được loại29ca rồi nói chỉ38ca có đáp án trongbeam; câu182ca còn lại không có đáp án là sai. Từ số liệu hiện tại có153ca lỗi không có oracle theo phép đo này, không phải182.
2. Top1 và oracle không cùng phép hậu xử lý: oracle chỉ sang_cay_moi và chuẩn hóa từ điển trực tiếp; chuan_hoa thực tế còn mở rộng đường, đổi số nhà, lọc detail, guard và các bước khác. Trong916ca top1 đúng chỉ915ca thuộc oracle982 (suy từ982-67). Vì vậy916/982 không phải conditionalaccuracy đúng; trần954cũng không phải oracle ceiling chuẩn. Không thay bằng983 và gọi trần chính xác khi chưa replay cùng hậu xử lý cho mọi giả thuyết.
3. Nhóm112ca chỉ có điều kiện admincompatible và notoracle6. Không đo goldspan/canonicalcandidate/formatteroracle hay đầu ra model riêng. Có thể là sai span, mất dấu, canonicalname, hậu xử lý hoặc nhãn yếu. Không đủ căn cứ chuyển toàn bộ112ca thành lỗi trích xuấtvi mô hay kết luận phải thay extractor.
4. Nhóm68ca nghi nhiễu dùng heuristic: nhãn đường dài>40, chứa từ phường/quận/huyện/tỉnh/thànhphố, hoặc pred đường xuất hiện nguyên văn tronginput khi ref trống; hoặc warningxa_bi_chia. Đây chỉ là cờ nghi vấn, không phải chứng minh nhãn sai. Chính ví dụPhốCầnThơ nghi sai nhãn lại nằm nhómdetail. Không thể coi68ca là toàn bộ nhãn nhiễu hay112ca còn lại là model thật sự sai.
5. Adminrecall cho phép mãreftrống là wildcard. Dev có220/1136refxãtrống được tự tính pass rawcandidate; không đo khả năng abstain hay bảo toànmơhồ. 99,74% là compatibility trên các trường cólabel, không phải accuracy hành chính đầy đủ. Danh mục chia xã cần phân biệt đíchkhảdĩ và đích đượcinputchứngminh.
6. Heuristicrecall@k dùng ranked[:k] trước khi sắp score cuối, trong khi tao_gia_thuyet khôngsort ranked theo score tính bổ sung. Không đúng topkheuristic runtime.
7. Baselinelatency đo riêng tao_gia_thuyet; Hybridlatency đo đầy đủchuan_hoa. 59,46vs62,46ms không phải đối chứngendtoend công bằng. Fallback255,08msP95 chỉ từ5ca, là số đuôi mẫu nhỏ chưaổnđịnh.
8. Báo cáo tự khẳng định giải thích35ca chênh lịch sử đều là cải tiến đúng, nhưng script gắn cố định văn bản15/12/8, không lưu đầy đủdelta và chứng cứ chuẩn hành chính. Trùng tênxãcũ/xãmới không đủ chọnmộtđích khi xãbịchia. Chưa nghiệmthu lời giải thích toànbộgiảmđiểm.
9. Đầu linking trước chưa tích hợp vào inference mà đo ruledefault0,18%: không được dùng đó làm bằng chứng mô hìnhlinking làm chất lượng sụpđổ. Đề xuất mô hình12–15M15–25ms và sửa70%lỗi chưa cóbenchmark/chứngminh.

## Kết luận thực tế

Có bằng chứng đường xử lý chi tiết/tênchuẩn là vấn đề lớn; không thể chỉ thay bộchọn cuối rồi kỳvọng95%. Tuy nhiên chưa đo được phần lỗi chính xác do extractor hay canonical linking/formatting. Chưa đủ căn cứ bỏ hướnglinking, cũng chưa đủ căn cứ train extractor mới. Bước cần làm là đồngnhất oracle với inference, giữ nhãn mơhồ riêng, tách rawspan->formatter->canonicalcandidates->chọncuối và đoablations cùngconfig. Kết quả hiện tại là chẩn đoán sơbộ, không phải nghiệmthu kiếntrúc tiếp theo.
