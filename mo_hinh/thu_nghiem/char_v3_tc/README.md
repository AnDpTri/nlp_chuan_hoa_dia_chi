# char_v3_tc — mô hình tiền xử lý đang dùng (thay char_v2_01 từ 31/10/2026)

- CNN ký tự + ranker LightGBM, ranker gắn với CNN này (extractor_sha256 655db4a1…).
- Dữ liệu train: dữ liệu thật của char_v2_01 x2 + 9.992 địa chỉ bẩn do agy sinh (nhãn từng ký tự, kiểm bằng máy) + 4.000 dòng tăng cường dạng số nhà thật (dải số, nhiều số, mã lô, căn hộ, Km...). Không dùng dev.
- Nơi train và nhật ký: D:\nlp_rf_gate\train_v3 (v3_tc, NHAT_KY.md, BAO_CAO_SANG.md).

| | char_v2_01 | char_v3_tc |
|---|---|---|
| Dev 1.600, riêng tiền xử lý | 85,8% | 85,7% |
| Bộ khó 1.500, riêng tiền xử lý | 61,2% | 82,7% |
| dev_goc đầu cuối 6 trường | 87,4% (993) | 87,4% (993) |
| dev_kho đầu cuối 6 trường | 89,9% (417) | 90,9% (422) |

Lưu ý: bộ khó và dữ liệu train đều do agy viết, mức tăng trên bộ khó có thể bị thổi phồng. Dev đã dùng để chọn cấu hình.
Quay lại bản cũ: đổi đường dẫn về mo_hinh/thu_nghiem/char_v2_01 (vẫn giữ nguyên).
