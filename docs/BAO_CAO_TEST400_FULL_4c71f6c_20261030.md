# Đánh giá đủ 400 mẫu test — nhánh 4c71f6c — 30/10/2026

## Cấu hình
- Nhánh: `feature/pipeline-quality-isolated-20261030`, commit mã đang kiểm tra `4c71f6c`.
- Worktree: `D:\nlp_chuan_hoa_dia_chi_fix_20261030`.
- Thực thi **toàn bộ 400/400** địa chỉ từ `data/test/dia_chi_test.csv`, không lấy mẫu.
- SHA-256 CSV: `eec94298e599589a0778b4009fbeae621bb98fa27f2cb0d27a53fdb6e130b7e9`, trùng lượt đánh giá trước.
- CNN v2: `mo_hinh/thu_nghiem/char_v2_01/char_cnn.pt`.
- Ranker v2: `mo_hinh/thu_nghiem/char_v2_01/ranker.txt`.
- Từ điển đường v5: `danh_gia/ket_qua/tu_dien_duong_v5.json`.
- `tien_to_mac_dinh=False` theo schema các trường chi tiết thô của CSV test.
- Mã test `danh_gia/do_kiem_tra_test400.py` mặc định đọc **toàn bộ** tập CSV; có thể dùng `--output` để lưu tại đường dẫn *chưa tồn tại*.

## Kết quả và so sánh

| Metric | Lượt trước (commit 6102728) | Sau sửa (commit 4c71f6c) | Chênh lệch |
|---|---:|---:|---:|
| Exact match 6 trường thô | 261/400 = 65,25% | **262/400 = 65,50%** | +1 câu (+0,25 điểm %) |
| Khớp nguyên chuỗi `dia_chi_chuan` | 281/400 = 70,25% | **285/400 = 71,25%** | +4 câu (+1 điểm %) |
| Mã xã | 360/400 = 90,00% | **367/400 = 91,75%** | +7 câu (+1,75 điểm %) |
| Tên đường | 329/400 = 82,25% | **329/400 = 82,25%** | Không đổi |
| Số nhà | 333/400 = 83,25% | **333/400 = 83,25%** | Không đổi |

Nhóm `da_duyet_ai` có 289 mẫu: 209/289 exact sáu trường và 220/289 khớp chuỗi chuẩn, **không đổi**.
Nhóm `can_duyet` có 111 mẫu: 52 -> 53 exact sáu trường; 61 -> 65 khớp chuỗi chuẩn.
Các chênh lệch là *net*, không thay cho đối chiếu gained/lost từng mẫu.

CPU: mean latency 75,39 ms, P95 150,22 ms, thông lượng 13,3 địa chỉ/giây.

## Cách chạy lần tiếp theo

Trong worktree nhánh mới, chạy lệnh sau với **tên thư mục output mới** mỗi lần đo:

```powershell
& 'D:\nlp_chuan_hoa_dia_chi\.venv-neural\Scripts\python.exe' -X utf8 -B -m danh_gia.do_kiem_tra_test400 --char-model 'mo_hinh/thu_nghiem/char_v2_01/char_cnn.pt' --ranker 'mo_hinh/thu_nghiem/char_v2_01/ranker.txt' --tu-dien-duong 'danh_gia/ket_qua/tu_dien_duong_v5.json' --output 'danh_gia/ket_qua/ten_luot_test_moi/BAO_CAO.json'
```

## Giới hạn

Tập test hiện có nhãn sơ bộ AI, **chưa có nhãn gold được con người duyệt**. Vì đã dùng test nhiều lần để kiểm tra phiên bản, đây không phải blind test. Không dùng lỗi trong test để chọn luật, sửa nhãn, bổ sung từ điển hoặc huấn luyện; muốn nghiệm thu 95% cần bộ gold độc lập mới.

Báo cáo JSON gốc của lượt chạy: `danh_gia/ket_qua/test400_full_4c71f6c_20261030/BAO_CAO.json`.
