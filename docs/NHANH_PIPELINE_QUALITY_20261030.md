# Nhánh thí nghiệm cải thiện pipeline — 30/10/2026

## Phạm vi cô lập

- Nhánh: `feature/pipeline-quality-isolated-20261030`, tách từ commit `2d1ddb5`.
- Worktree: `D:\nlp_chuan_hoa_dia_chi_fix_20261030`.
- Dự án gốc: `D:\nlp_chuan_hoa_dia_chi` (không chuyển nhánh, không sửa kết quả cũ).
- Không viết lại checkpoint, từ điển, danh mục, nhãn train/dev hoặc các kết quả lưu từ trước.
- **Cấm dùng test cuối để phát triển**: script mới chỉ đọc `data/train_dev/dev.csv` và snapshot `dev_kho.csv`.

## Đã sửa

1. `src/dinh_dang.py`: khi người dùng viết rõ tiền tố `Số`, cờ tắt *tự thêm tiền tố* không được xóa tiền tố quan sát. Nếu input không có `Số`, hành vi bật/tắt tự thêm vẫn được giữ.
2. `src/chuan_hoa.py`: tách bước dựng lại ứng viên đường từ span CNN thành nhánh không cần Transformer. Transformer chỉ được dùng khi thực sự cần mở rộng span.
3. Nhánh fallback Transformer ghép theo offset ký tự gốc, không dùng chỉ số token CNN truy cập nhãn ViDeBERTa. Khi đề xuất không qua từ điển, span và danh sách token chưa phân loại được giữ nguyên (thay đổi theo transaction).
4. `tests/test_pipeline_quality_isolated.py`: fixture độc lập cho hợp đồng tiền tố và căn chỉnh ký tự.
5. `danh_gia/do_kiem_tra_test400.py`: mặc định bật hợp đồng tiền tố chuẩn, cho phép `--no-tien-to-mac-dinh` khi cần tái hiện chế độ cũ. Lấy mẫu số thực tế khi in báo cáo và từ chối ghi đè file output.
6. `danh_gia/do_thong_ke_truong.py`: thống nhất cờ tiền tố với hợp đồng chuẩn và in mẫu số nhóm thực tế (không gắn cứng 292/108). **Chỉ sửa mã; chưa thực thi lại tập test**.

## Phép đo DEV mới

`danh_gia/so_sanh_hop_dong_dev.py` dùng cùng CNN v2, ranker v2, từ điển v5; chỉ thay cờ `tien_to_mac_dinh` từ false sang true. Kết quả lưu tại thư mục mới, từ chối ghi đè.

Chạy tại thư mục worktree:

```powershell
& 'D:\nlp_chuan_hoa_dia_chi\.venv-neural\Scripts\python.exe' -X utf8 -B -m unittest tests.test_pipeline_quality_isolated -v
& 'D:\nlp_chuan_hoa_dia_chi\.venv-neural\Scripts\python.exe' -X utf8 -B -m danh_gia.so_sanh_hop_dong_dev --output-dir danh_gia/ket_qua/pipeline_quality_moi
```

Đây là đo khớp sáu trường theo nhãn máy/tổng hợp trên dev, không phải gold độc lập. Đo hai chế độ để tìm sai lệch hợp đồng, không dùng kết quả test để chọn phương án.

## Kết quả đối chứng đầy đủ

Kết quả trong `danh_gia/ket_qua/pipeline_quality_full_20261030/BAO_CAO.json`:

| Tập dev | Tắt tự thêm tiền tố | Bật tự thêm tiền tố | Gained / lost (exact 6 trường) |
|---|---:|---:|---:|
| Dev gốc (1.136) | 497 (43,750%) | 916 (80,634%) | +419 / 0 |
| Dev khó (464) | 280 (60,345%) | 330 (71,121%) | +50 / 0 |

Các số là exact-match 6 trường theo nhãn dev máy/tổng hợp, **không phải cải thiện năng lực NLP tương đương**. Thay đổi cờ chỉ ảnh hưởng định dạng tiền tố và từ đó cách chấm. Trên dev gốc, `dia_chi_chuan` nguyên chuỗi khớp 913/1.136 khi tắt so với 910/1.136 khi bật, vì vậy không được tuyên bố mọi metric đều không hồi quy.

- **70/70** unit tests pipeline/char/formatter/evaluator và các test mới đạt.
- **4/4** fixture tên đường dính chữ (ví dụ train đã lưu) đúng với `bo_tach_phu=None`, không nạp Transformer, qua `danh_gia/kiem_tra_rebuild_no_transformer.py`.
- Không suy ra được accuracy trên test cuối từ các lượt dev này.

## Việc chưa làm

- Chưa huấn luyện lại mô hình hoặc xếp hạng.
- Chưa tái tạo tập gold được người duyệt.
- Không thể kết luận đạt 95% từ kết quả dev.
- Từ điển tên đường v5 còn bao gồm dữ liệu chưa chứng thực độc lập; chỉ sử dụng làm đối chứng cùng snapshot, không khẳng định provenance đã được sửa.
