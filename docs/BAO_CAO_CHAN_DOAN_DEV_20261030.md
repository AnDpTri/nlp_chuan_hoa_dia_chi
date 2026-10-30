# Giai đoạn 2 — Chẩn đoán lỗi dev và sửa pipeline (30/10/2026)

## Phạm vi và cô lập

- Nhánh: `feature/pipeline-quality-isolated-20261030`, worktree `D:\nlp_chuan_hoa_dia_chi_fix_20261030`.
- Điểm bắt đầu: `6102728` của nhánh cô lập (không thay `feature/reach-95-accuracy`).
- Model: CNN v2 (`char_cnn.pt`) + ranker v2 (`ranker.txt`) + từ điển đường v5; `bao_ve_duong=True`, `tien_to_mac_dinh=True`.
- Chỉ đọc `data/train_dev/dev.csv` (1.136) và `mo_hinh/thu_nghiem/char_v1_01/snapshot/dev_kho.csv` (464).
- Tuyệt đối không đọc/tinh chỉnh bằng tập test 400 trong giai đoạn này. Nhãn dev gồm nhãn máy và tổng hợp, **chưa phải gold**.

## Phân tích lỗi trước khi sửa

| Chỉ số dev | Dev gốc | Dev khó |
|---|---:|---:|
| Exact 6 trường | 916/1.136 (80,63%) | 330/464 (71,12%) |
| Số câu không khớp | 220 | 134 |
| Lỗi tên đường (không độc lập) | 137 | 119 |
| Lỗi mã xã (không độc lập) | 87 | 20 |
| Lỗi số nhà (không độc lập) | 30 | 3 |
| Lỗi ngõ/hẻm (không độc lập) | 17 | 0 |
| Lỗi thôn/xóm (không độc lập) | 7 | 1 |

Trong các lỗi tên đường, 46 trường hợp dev gốc và 55 trường hợp dev khó chỉ khác dấu/khoảng trắng theo chuẩn hóa sơ bộ, nhưng đây không phải xác minh tên đường chính thức. Một số nhãn máy/dev cũng không chắc chắn về vai trò trường (ví dụ tên địa phương bị đưa sang trường đường), nên không sửa luật để khớp một nhãn đáng nghi.

## Thay đổi đã thực hiện

1. `src/chuyen_doi.py`: khi một xã cũ chuyển đổi sang nhiều xã mới, không còn tự chọn xã trùng tên cũ. Giữ `ma_xa=""`, cảnh báo `xa_bi_chia`. Tên không phải bằng chứng địa giới. Quan hệ chuyển đổi duy nhất vẫn được chọn bình thường.
2. `src/dinh_dang.py`: không xóa token số nhà 5–6 chữ số vô điều kiện. Mã bưu chính chỉ có thể nhận diện từ ngữ cảnh; nếu span đã gán `so_nha`, formatter không được tự làm mất chữ số.
3. `danh_gia/phan_tich_loi_dev_co_lap.py`: thống kê chi tiết lỗi theo trường và nhóm nguyên nhân, lưu 354 dự đoán sai lúc baseline dev, kèm các nghi vấn nhãn chỉ để người duyệt xem lại.
4. `danh_gia/so_sanh_sua_loi_dev.py`: so sánh hai snapshot cùng hash dữ liệu, model, ranker, từ điển; thống kê gained/lost, không chấm trên test.
5. Thêm fixture độc lập kiểm tra xã trùng tên nhưng nhiều đích, xã duy nhất, số nhà dài, nhãn rỗng và lỗi mất dấu.

## Đối chứng cùng cấu hình trước / sau

| Tập dev | Trước | Sau | Được | Mất |
|---|---:|---:|---:|---:|
| Dev gốc (1.136) | 916 (80,63%) | **941 (82,83%)** | **25** | **0** |
| Dev khó (464) | 330 (71,12%) | **330 (71,12%)** | **0** | **0** |

Sửa formatter số nhà không làm thay đổi điểm trên hai dev. Sửa xử lý xã bị chia tạo +25 exact match dev gốc, -0 hồi quy. Số lỗi mã xã (không độc lập) trên dev gốc giảm 87 -> 55. Chỉ số chính là khớp nhãn dev, **không suy ra mức tăng tương tự trên test**.

Phép đo đã khóa SHA-256 dữ liệu dev, checkpoint CNN v2, ranker v2 và từ điển v5; comparer từ chối đối chiếu khác hash. `76/76` bài kiểm thử ở nhóm pipeline/char/formatter/evaluator liên quan PASS.

## Dữ liệu đầu ra và lệnh chạy

- Baseline: `danh_gia/ket_qua/chan_doan_chi_tiet_dev_20261030/` (`TONG_HOP.json`, `LOI_TUNG_CA.jsonl`).
- Số nhà riêng: `danh_gia/ket_qua/chan_doan_chi_tiet_dev_so_nha_20261030/`.
- Sau sửa xã bị chia: `danh_gia/ket_qua/chan_doan_chi_tiet_dev_xa_chia_20261030/`.
- Đối chứng: `danh_gia/ket_qua/doi_chung_chuyen_doi_xa_20261030/` (`THONG_KE.json`, `THAY_DOI.jsonl`).
- Thư mục output không được ghi đè; chạy lại phải dùng tên mới.

## Kết luận và giới hạn

Có cải thiện thực sự của thuật toán chuyển đổi khi tránh lựa chọn xã thiếu căn cứ. Điểm nghẽn còn lại là tên đường: sau sửa, lỗi tên đường trên dev gốc vẫn 137, dev khó 119, trong đó nhiều lỗi dấu. **Không được thêm ngoại lệ theo từng địa chỉ dev, đoán tên đường khi không có nguồn đáng tin, hoặc dùng lỗi test đã xem để tinh chỉnh.** Chưa có tập gold do người duyệt và chưa kiểm chứng độc lập năng lực tổng quát hóa mới trên test.
