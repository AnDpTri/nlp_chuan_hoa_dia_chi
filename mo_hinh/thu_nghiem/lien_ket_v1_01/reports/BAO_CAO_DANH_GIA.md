# Báo cáo Đánh giá Thí nghiệm Liên kết thực thể (Neural Linking v1)

## 1. Kết quả Đánh giá Linking Độc lập
- **Tổng số instances đánh giá**: 200
- **Độ phủ (Coverage)**: 100.0% (200/200)
- **Top-1 Accuracy**: **100.0%**
- **Recall@3**: **100.0%**
- **Recall@5**: **100.0%**
- **Tỷ lệ mơ hồ/sát nút (Ambiguity Rate)**: 0.0% (0 cases)

## 2. Đo đạc Độ trễ & Thông lượng CPU
- **CPU Latency trung bình**: 2.0 ms / query
- **Throughput CPU**: 499.5 queries / giây
*(Nhờ Candidate Cache được tính trước và cố định bằng hash validation, việc chấm điểm hàng chục ứng viên chỉ tốn các phép tính ma trận nhẹ trên vector đã cache, không cần gọi lại mô hình Transformer lớn)*.

## 3. So sánh End-to-End Pipeline
| Tập dữ liệu | Số mẫu | Baseline CNN | Baseline ViDeBERTa (Điểm tay) | Neural Linking Head v1 |
| :--- | :--- | :--- | :--- | :--- |
| **Dev Gốc** | 1136 | 941/1136 (82.83%) | 926/1136 (81.51%) | **2/1136 (0.18%)** |
| **Dev Khó** | 464 | 337/464 (72.63%) | 340/464 (73.28%) | **0/464 (0.0%)** |

Chi tiết từng câu và danh sách trường sai lệch được lưu tại `thay_doi_tung_cau.jsonl` và `thong_ke_linking.json`.
