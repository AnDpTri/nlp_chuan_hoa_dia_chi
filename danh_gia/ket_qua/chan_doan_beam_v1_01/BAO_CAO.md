# Chẩn đoán câu sai dev khó

Chẩn đoán các câu chưa khớp dev khó. Không đổi nhãn/model, không dùng test cuối.

Phân loại cơ học theo reference yếu, không xác nhận nhãn đúng ngữ nghĩa. Các nhãn cần rà chỉ là nghi vấn.

| Nhóm loại trừ nhau | CNN ranker | ViDeBERTa điểm tay |
|---|---:|---:|
| chi_thieu_phuc_hoi_dau | 56 | 57 |
| co_dap_an_trong_beam_nhung_output_chua_khop | 13 | 13 |
| co_hanh_chinh_dung_nhung_chi_tiet_chua_khop | 94 | 91 |
| khac_dau_khoang_trang_dau_cau | 1 | 1 |
| thieu_ca_hanh_chinh_va_chi_tiet | 4 | 3 |

Mỗi JSONL chứa input/reference/output, span gốc, phương án gần nhất và toàn bộ beam. Nhánh gần nhất được chọn hậu kiểm bằng reference, không phải output triển khai.
