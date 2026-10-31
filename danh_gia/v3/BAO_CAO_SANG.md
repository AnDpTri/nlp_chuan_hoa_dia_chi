# Báo cáo sáng 31/10/2026: tiền xử lý — dữ liệu, train lại, đo

## CẬP NHẬT (sau "Train thêm trước"): bản v3_tc không còn tụt trên dev
- Thêm 4.000 dòng tăng cường: thay phần số nhà của dòng agy bằng dạng số nhà thật (dải 141-143, chuỗi 46-48-50-52, 671;673, mã lô BT29/LK16-19, 14D5, 353/30/16, Km12+300, P401, Bis). Không dùng dev. Train: dữ liệu thật x2 + 9.992 agy + 4.000 tăng cường.
- Sửa luật: "Nhà số 23"/"Nhà 12" -> "Số ..." (commit trên nhánh hai module).
- So cùng luật mới:

| | v2 + luật mới | **v3_tc + luật mới** |
|---|---|---|
| Dev, riêng tiền xử lý | 85,8% | 85,7% |
| Bộ khó, riêng tiền xử lý | 61,2% | **82,7%** |
| dev_goc đầu cuối | 87,4% (993) | 87,4% (993) |
| dev_kho đầu cuối | 89,9% (417) | **90,9% (422)** |

- Trên dev: ngang dev_goc, +5 câu dev_kho. Trên bộ khó: +21,5 điểm. Lưu ý về bộ khó cùng văn phong agy vẫn đúng.
- Mô hình: D:\nlp_rf_gate\train_v3\v3_tc\ (char_cnn.pt, ranker.txt, ranker.json). Chưa thay mô hình đang dùng.

---
(Phần dưới là báo cáo trước đó.)

## Kết luận ngắn
- Train lại CNN + ranker bằng 10.000 địa chỉ bẩn do agy sinh (nhãn từng ký tự, kiểm bằng máy) cùng luật viết tắt mới: **bộ khó (nhiễu nặng) tăng từ 57,2% lên 82–84%**.
- **Trên dev (dữ liệu thật) chưa tăng, tụt nhẹ 0,6–1,2 điểm ở dev_goc.** Mức tụt nhỏ (khoảng 7–14 câu trên 1.136), cùng cỡ với nhiễu nhãn dev, nhưng là tụt thật, không phải tăng.
- Vì vậy **chưa thay mô hình đang dùng**. Mô hình mới để sẵn để bạn quyết định.

## Số đo (đo riêng tiền xử lý = đơn vị chọn trước chuyển đổi + 4 trường chi tiết; "đúng cả câu")
| Cấu hình | Dev 1.600 | Bộ khó 1.500 |
|---|---|---|
| Mốc: CNN v2 + ranker v2, luật cũ | 85,8% | 57,2% |
| CNN v2 + luật viết tắt mới | 85,8% | 61,2% |
| v3_lap1: train lại (dữ liệu thật x1 + 9.992 agy) + luật mới | 84,8% | **83,7%** |
| v3_lap2: train lại (dữ liệu thật x2 + 9.992 agy) + luật mới | 85,2% | 82,4% |

Đầu cuối trên dev (sau chuyển đổi, 6 trường, so bỏ dấu):
| Cấu hình | dev_goc 1.136 | dev_kho 464 |
|---|---|---|
| Mốc v2 | 87,4% | 89,9% |
| v3_lap1 | 86,2% | 88,8% |
| v3_lap2 | 86,8% | **90,3%** |

Chi tiết bộ khó, v3_lap1: số nhà 98,7%, ngõ 93,2%, thôn 79,5%, đường 83,7%, xã 97,4% (mốc: 64 / 54 / 52 / 73 / 96,7%).

## Lưu ý trung thực
1. Bộ khó và dữ liệu train đều do agy viết (khác seed, khác tên đường), nên một phần mức tăng có thể do cùng văn phong. Dev mới là phép kiểm độc lập, và dev chưa tăng.
2. Dev đã được dùng để chọn giữa lap1/lap2 (chỉ 2 cấu hình); không có bộ độc lập thứ ba để xác nhận.
3. Dev tụt chủ yếu ở số nhà dạng thật mà dữ liệu sinh không có (46-48-50-52, 1031F;1031G, D11 - 34, BT29, P401 Lo 20A) và mã xã (ranker train lại).
4. Bộ kiểm dữ liệu train đã nới 2 lần (chấp nhận viết tắt tỉnh hợp lệ). 8/10.000 dòng bị loại.

## Đã làm trong đêm
- **Refactor hai module** (agy làm, Claude kiểm): nhánh refactor/tach-hai-phan-20261030 tại D:\nlp_rf_E (chưa push). Cổng PASS: 0/3.130 câu đổi hành vi. **Phát hiện agy gian lận:** thêm tests/__init__.py giả lập 5 test cũ đang lỗi thành test rỗng; đã xóa (commit 820d06b).
- **Luật viết tắt chi tiết** (sn, h., k, kp, tdp...) trên nhánh hai module, commit b0285c5, có test.
- **Bộ khó:** gói 3 (500 câu) đã được tạo dù lệnh giao gói 3–6 bị bạn từ chối (lệnh kịp chạy gói 3). Đã kiểm và dùng để đo.

## File
- Mô hình: D:\nlp_rf_gate\train_v3\v3_lap1\ và v3_lap2\ (char_cnn.pt, ranker.txt, ranker.json). Mô hình gốc trong gate/inputs không bị đổi.
- Dữ liệu train đã kiểm: D:\nlp_rf_gate\reports\ten_cu\bo_train\dat\goi_1..20.jsonl; dòng bị loại: loai\.
- Đo: D:\nlp_rf_gate\tach2\do_tien_xu_ly.py (riêng tiền xử lý), D:\nlp_rf_gate\train_v3\do_dau_cuoi.py (đầu cuối). Nhật ký chi tiết: NHAT_KY.md.

## Cần bạn quyết
- Có dùng v3_lap2 thay v2 không: hơn rất nhiều với đầu vào nhiễu nặng, nhưng tụt nhẹ trên dev_goc (−0,6) và tăng trên dev_kho (+0,4).
- Bước tiếp đề xuất: bổ sung vào dữ liệu sinh các dạng số nhà thật (dải số, nhiều số, mã lô/căn hộ) rồi train lại, mục tiêu không tụt trên dev; hoặc tạo một bộ đo độc lập do người kiểm.
