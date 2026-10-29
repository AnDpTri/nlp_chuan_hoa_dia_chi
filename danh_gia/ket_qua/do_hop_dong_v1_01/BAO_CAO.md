# Đo chế độ hợp đồng v1

Giữ nguyên checkpoint/dữ liệu/từ điển. Không train, không đọc test cuối. So với bản đã sửa định dạng tiền tố.
Đây là khớp nhãn máy/tổng hợp trên dev cũ, chưa là kiểm chứng tổng quát hóa. Gợi ý chứa tên reference không được tính thành câu output đúng.

| Tập | Model | Đúng trước → sau | % sau | Được / mất | Mean/P95 ms |
|---|---|---:|---:|---:|---:|
| dev_goc | cnn_ranker | 941 → 893 / 1136 | 78.609 | 0/48 | 19.68/29.69 |
| dev_goc | videberta_tay | 926 → 878 / 1136 | 77.289 | 0/48 | 106.94/133.94 |
| dev_kho | cnn_ranker | 333 → 317 / 464 | 68.319 | 0/16 | 22.72/47.95 |
| dev_kho | videberta_tay | 336 → 321 / 464 | 69.181 | 0/15 | 109.97/146.52 |

## Phân tích phần giảm điểm

- dev_goc, cnn_ranker: {"rows_with_name_suggestions": 424, "suggestions_contain_reference_road": 417, "reference_road_nonempty": 1031, "name_suggestions_ambiguous": 0, "name_suggestions_accent_conflict": 1, "wrong_six_fields": 243, "wrong_but_only_road_and_suggestion_matches": 48, "lost_only_road_with_correct_suggestion": 48}
- dev_goc, videberta_tay: {"rows_with_name_suggestions": 421, "suggestions_contain_reference_road": 416, "reference_road_nonempty": 1031, "name_suggestions_ambiguous": 0, "name_suggestions_accent_conflict": 1, "wrong_six_fields": 258, "wrong_but_only_road_and_suggestion_matches": 48, "lost_only_road_with_correct_suggestion": 48}
- dev_kho, cnn_ranker: {"rows_with_name_suggestions": 96, "suggestions_contain_reference_road": 78, "reference_road_nonempty": 434, "name_suggestions_ambiguous": 12, "name_suggestions_accent_conflict": 1, "wrong_six_fields": 147, "wrong_but_only_road_and_suggestion_matches": 15, "lost_only_road_with_correct_suggestion": 15, "lost_changed_admin_or_other_detail": 1}
- dev_kho, videberta_tay: {"rows_with_name_suggestions": 96, "suggestions_contain_reference_road": 78, "reference_road_nonempty": 434, "name_suggestions_ambiguous": 12, "name_suggestions_accent_conflict": 1, "wrong_six_fields": 143, "wrong_but_only_road_and_suggestion_matches": 15, "lost_only_road_with_correct_suggestion": 15}

Chế độ mới giữ tên từ train ở gợi ý và bỏ lọc cứng theo span model. Đây là thay đổi chính sách đầu ra, không phải bằng chứng chất lượng tốt hơn.
Điểm giảm phải được báo đầy đủ; không chọn mặc định mới chỉ vì output giải thích rõ hơn. Các quyết định hành chính thay đổi cần rà từng ca.
Latency gồm core + tạo cấu trúc giải thích + asdict, không gồm JSON/I/O/khởi tạo; một lượt CPU một luồng, tải nền có thể ảnh hưởng.
Output từng câu ở JSONL; thay_doi_tung_cau.jsonl chứa mọi câu đổi; PHAN_TICH_GOI_Y.json chứa phân loại phần giảm và ví dụ.
