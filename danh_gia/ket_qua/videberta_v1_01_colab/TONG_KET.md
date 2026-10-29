# Kết quả ViDeBERTa-xsmall từ Colab

Train đã hoàn tất. Lần thử này chưa vượt CRF/CNN đồng đều; chưa có căn cứ thay bản cũ bằng ViDeBERTa.

| Cấu hình | Dev gốc (1136) | Dev khó (464) |
|---|---:|---:|
| luat_v3 | 870 (76.585%) | 228 (49.138%) |
| crf_cu | 895 (78.785%) | 274 (59.052%) |
| cnn_ranker | 893 (78.609%) | 280 (60.345%) |
| videberta_diem_tay | 878 (77.289%) | 284 (61.207%) |
| videberta_ranker | 879 (77.377%) | 282 (60.776%) |

**Đây là độ khớp nhãn máy/tổng hợp trên dev, không phải độ chính xác gold.**

GPU T4: 4841 mẫu, 70,753,742 tham số, 5 epoch; tổng thời gian vòng train 412.37 giây, chưa gồm tải model/preprocessing/ghi checkpoint. Peak GPU allocated 1373.9 MiB.

## Suy luận CPU Colab

| Cấu hình | Dev gốc mean/P95 ms | Dev khó mean/P95 ms |
|---|---:|---:|
| crf_cu | 12.64/19.61 | 13.87/33.96 |
| videberta_diem_tay | 90.65/106.59 | 93.25/113.63 |
| videberta_ranker | 92.19/108.35 | 94.86/117.18 |

Các số đo tốc độ trong bảng cùng CPU Colab, không gán cho CPU laptop. CNN trước đó đo trên laptop nên chỉ đối chiếu chất lượng bằng cùng dữ liệu, không lấy tỷ số latency khác máy.

## Nhận định

- ViDeBERTa + ranker giảm 16 câu khớp dev gốc, tăng 8 câu dev khó so với CRF kết hợp.
- So với CNN + ranker, giảm 14 câu dev gốc, tăng 2 câu dev khó.
- Ranker chỉ tăng 1 câu dev gốc nhưng giảm 2 câu dev khó so với ViDeBERTa điểm tay.
- F1 span chi tiết: dev gốc 97.566% (1026 câu), dev khó 98.925% (464 câu). CNN tương ứng 98.132% và 98.761%: độ tốt không đồng đều ngay ở bước nhận diện.
- Không chỉ là lỗi xếp hạng: beam chỉ có phương án khớp đủ 6 trường ở 915/1136 và 296/464 câu. Ranker chọn trong các phương án này, không tự bổ sung tên chuẩn còn thiếu.
- Chưa có danh mục đường chứng thực, nhãn còn yếu, thôn/tổ train ít. Đây vẫn là các giới hạn; kết quả chưa chứng minh đổi encoder là đủ và cũng chưa chứng minh trần năng lực của ViDeBERTa.
- Chưa thử ONNX/INT8 hoặc nhiều cấu hình fine-tune; chưa nên tối ưu tốc độ để che việc chưa tăng chất lượng.

## Kiểm chứng và file

- Đã nhập checkpoint, tokenizer, ranker và report vào mo_hinh/thu_nghiem/videberta_v1_01; đối chiếu 49 file với SHA256_EXPORT.json.
- Bốn tập dữ liệu khớp SHA-256 với thử nghiệm CNN; code đánh giá khớp gói v2; tính lại số khớp từ JSONL đúng với thống kê.
- KIEM_TRA_NHAP.json có kiểm chứng, số ca được/mất và phân loại lỗi. VI_DU_DUNG_SAI.json có input, nhãn, CRF cũ và output mới.
- Các JSONL gốc, thong_ke.json, so_sanh_loi.csv được giữ nguyên. Không dùng kết quả test cuối, không tự thay dữ liệu hoặc mô hình mặc định.
