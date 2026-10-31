# Protocol đánh giá dev và bộ khó

Ngày đọc mã: 2026-10-31. **Chỉ đọc mã/cấu hình; không chạy pipeline, không sửa code, không huấn luyện, không tạo dữ liệu.**

## 1. Lệnh và interpreter

CLI inference chính xác: `chay_mo_hinh.py <char_cnn.pt> <ranker.txt> <out_dir>` (3 đối số vị trí; `chay_mo_hinh.py:1-2,19,42-43`).

Interpreter script không pin. Interpreter sẵn có phù hợp đã xác minh:
`D:\\nlp_chuan_hoa_dia_chi\\.venv-neural\\Scripts\\python.exe` — Python **3.12.10** (`pyvenv.cfg:3-5`; executable tồn tại). Dùng môi trường này vì pipeline cần PyTorch, LightGBM và NumPy (`src/char_cnn.py:11-12`; `src/xep_hang.py:39,50-52`). Không tạo/cài môi trường.

Script mặc định nạp code từ `D:\\nlp_exp_h1`, không phải `D:\\nlp_rf_E`: `CODE_ROOT` hoặc mặc định này được chèn vào `sys.path` (`chay_mo_hinh.py:7-13`). Để tái hiện đúng script hiện tại, đặt `$env:CODE_ROOT='D:\\nlp_exp_h1'`. Chỉ đổi sang `D:\\nlp_rf_E` nếu chủ đích đánh giá code ở đó; đó là một code root khác.

## 2. Model/checkpoint đầu vào

- CharCNN: file `char_cnn.pt` truyền ở đối số 1. Loader đọc checkpoint PyTorch, yêu cầu `format == 1`, `tags`, `vocab`, `config`, `state_dict`; chạy CPU, 1 thread, `eval()` (`src/char_cnn.py:118-130`).
- Ranker: file LightGBM `ranker.txt` truyền ở đối số 2 **và sidecar cùng basename** `ranker.json`. Sidecar phải khớp `features`, SHA-256 của extractor và catalogue, có `close_margin`; nếu không sẽ raise lỗi (`src/xep_hang.py:37-48`).
- Hai checkpoint phải là một cặp tương thích. Script không hard-code vị trí/tên file checkpoint; không thể suy ra đường dẫn thực tế chỉ từ ba script được phép đọc. Không tự đoán đường dẫn.
- Cấu hình pipeline: `bao_ve_duong=True`, `tien_to_mac_dinh=True`, CharCNN + ranker + từ điển đường (`chay_mo_hinh.py:21-24`).

## 3. Dataset và tài nguyên được đọc

Inference đọc:
- `D:\\nlp_rf_gate\\inputs\\dev_goc.csv` và `dev_kho.csv`; dùng cột `id`, `dau_vao` (`chay_mo_hinh.py:15,25-28`).
- Bộ khó: tất cả `D:\\nlp_rf_gate\\reports\\ten_cu\\bo_kho\\ra\\ra_*.csv`, sắp xếp theo tên file; dùng cột `id`, `dia_chi`, gắn split `kho` (`chay_mo_hinh.py:16,29-31`).
- Từ điển train-only: `D:\\nlp_rf_gate\\inputs\\tu_dien_train.json`; loader kiểm tra `format=1`, `source_scope=train_only` (`chay_mo_hinh.py:23-24`; `src/chuan_ten_duong.py:105-111`).
- Catalogue hành chính ở `D:\\nlp_exp_h1\\data\\clean`: `cu_tinh.csv`, `moi_tinh.csv`, `cu_huyen.csv`, `cu_tinh_huyen_xa.csv`, `moi_tinh_xa.csv`, `doi_chieu_xa_cu_moi.csv` (`src/danh_muc.py:13,30-58`).

Gold dùng riêng khi chấm: thư mục chứa `dev_goc.csv` và `dev_kho.csv`. `so_hai_lan.py` mặc định dùng `D:\\nlp_rf_gate\\do_nhan\\inputs_sua`; truyền rõ thư mục này để tránh phụ thuộc mặc định (`so_hai_lan.py:24-25`). `do_dau_cuoi_sua.py` bắt buộc nhận thư mục nhãn làm đối số 1 (`do_dau_cuoi_sua.py:1-3,21-25,53-54`).

## 4. Metric và phạm vi chấm

`do_dau_cuoi_sua.py` chấm 6 trường: `so_nha`, `ngo_ngach_hem`, `thon_xom`, `duong`, `ma_xa`, `ma_tinh` (`do_dau_cuoi_sua.py:7`).
- Với 4 trường text: NFD, bỏ dấu thanh, `đ -> d`, casefold, bỏ dấu cách; riêng `duong`, `Phố X` được quy về tương đương `Đường X` (`do_dau_cuoi_sua.py:10-18,35-42`).
- `ma_xa`, `ma_tinh`: so sánh chuỗi chính xác (`do_dau_cuoi_sua.py:38-40`).
- Trường có tên trong `bo_qua` bị loại khỏi mẫu số; báo cáo accuracy từng trường và accuracy đồng thời tất cả trường còn được chấm (`do_dau_cuoi_sua.py:33-50`). Không tính precision/recall/F1.
- Chỉ gold `dev_goc`, `dev_kho` được nạp. Kết quả split `kho` không có gold key nên bị bỏ qua; **script này không tính accuracy bộ khó** (`do_dau_cuoi_sua.py:22-31`).
- Chỉ các prediction có key khớp gold mới được đếm; cần kiểm tra độ phủ ID riêng. Inference bắt exception theo từng dòng và ghi `out: {"EXCEPTION": ...}`; không được coi chỉ dòng `xong N` là mọi mẫu đều thành công (`chay_mo_hinh.py:32-39`).

## 5. Cấu trúc kết quả và file ghi

Một dòng JSONL cho mỗi mẫu:
`{"split":"dev_goc|dev_kho|kho","id":"...","out":{...KetQua...}}`.
`out` bình thường là `asdict(KetQua)`, gồm các trường địa chỉ, mã, cảnh báo, ứng viên, dấu vết, phần chưa phân loại và thống kê (`src/kieu_du_lieu.py:45-62`); lỗi từng mẫu dùng object `EXCEPTION`. Output là UTF-8, một JSON object mỗi dòng (`chay_mo_hinh.py:32-38`).

**File có thể bị ghi đè:** duy nhất file output được ghi rõ trong script là `<out_dir>\\ket_qua.jsonl`, mở mode `w` (`chay_mo_hinh.py:32`). Thư mục output được tạo nếu chưa có (`chay_mo_hinh.py:20`). Không dùng thư mục input hoặc thư mục gold làm `out_dir`. Hai script chấm/so sánh chỉ đọc JSONL và CSV rồi in stdout; không ghi báo cáo/file (`do_dau_cuoi_sua.py:21-50`; `so_hai_lan.py:15-37`).

## 6. Một lượt đánh giá an toàn

PowerShell; thay **hai placeholder checkpoint** bằng đường dẫn thật đã xác minh. Dùng một thư mục output mới, tách khỏi inputs/gold:

```powershell
$py = 'D:\\nlp_chuan_hoa_dia_chi\\.venv-neural\\Scripts\\python.exe'
$env:CODE_ROOT = 'D:\\nlp_exp_h1'
$out = 'D:\\nlp_rf_gate\\reports\\ten_cu\\eval_20261031_run1'

& $py 'D:\\nlp_rf_gate\\train_v3\\chay_mo_hinh.py' '<absolute-path>\\char_cnn.pt' '<absolute-path>\\ranker.txt' $out

& $py 'D:\\nlp_rf_gate\\train_v3\\do_dau_cuoi_sua.py' 'D:\\nlp_rf_gate\\do_nhan\\inputs_sua' "$out\\ket_qua.jsonl"
```

Inference không mở thư mục gold; scorer chỉ đọc gold CSV để tính dev metric, không sửa chúng. Nếu yêu cầu là tuyệt đối không đọc gold, chỉ chạy inference và bỏ lệnh scorer — khi đó không có metric dev. Kiểm tra số dòng `EXCEPTION` trong JSONL trước khi diễn giải điểm. Bộ khó hiện chỉ có inference, chưa có metric accuracy trong ba script này.

## 7. Hai lượt và kiểm tra ổn định

Chạy cả hai lượt trong cùng một PowerShell session, cùng interpreter, `CODE_ROOT`, checkpoint + sidecar, inputs và catalogue; chỉ khác output directory. Hai thư mục phải mới, không tái sử dụng vì `ket_qua.jsonl` bị truncate/ghi đè.

```powershell
$py = 'D:\\nlp_chuan_hoa_dia_chi\\.venv-neural\\Scripts\\python.exe'
$env:CODE_ROOT = 'D:\\nlp_exp_h1'
$cnn = '<absolute-path>\\char_cnn.pt'
$ranker = '<absolute-path>\\ranker.txt'
$out1 = 'D:\\nlp_rf_gate\\reports\\ten_cu\\eval_20261031_run1'
$out2 = 'D:\\nlp_rf_gate\\reports\\ten_cu\\eval_20261031_run2'

& $py 'D:\\nlp_rf_gate\\train_v3\\chay_mo_hinh.py' $cnn $ranker $out1
& $py 'D:\\nlp_rf_gate\\train_v3\\chay_mo_hinh.py' $cnn $ranker $out2

& $py 'D:\\nlp_rf_gate\\train_v3\\do_dau_cuoi_sua.py' 'D:\\nlp_rf_gate\\do_nhan\\inputs_sua' "$out1\\ket_qua.jsonl" "$out2\\ket_qua.jsonl"
& $py 'D:\\nlp_rf_gate\\train_v3\\so_hai_lan.py' "$out1\\ket_qua.jsonl" "$out2\\ket_qua.jsonl" 'D:\\nlp_rf_gate\\do_nhan\\inputs_sua'
Get-FileHash -Path "$out1\\ket_qua.jsonl","$out2\\ket_qua.jsonl" -Algorithm SHA256
```

`so_hai_lan.py` liệt kê mẫu dev mà trạng thái đúng/sai đồng thời 6 trường đổi, và đếm số mẫu split `kho` có ít nhất một trong 6 trường đầu ra khác (`so_hai_lan.py:19-37`). Đây **không phải** phép so sánh toàn bộ JSONL: dùng SHA-256 để xác nhận hai file giống hệt byte; hash giống nhau là kiểm tra ổn định chặt hơn. Hàm `fold` trong script so sánh này quy `Phố` về `Đường` cho mọi trường text, khác scorer ở chỗ chỉ áp dụng quy tắc đó cho trường `duong` (`so_hai_lan.py:9-12,19-21`; `do_dau_cuoi_sua.py:15-18,41-42`).

## 8. Giới hạn kết luận

- Ba script xác định được quy trình inference, chấm dev và so sánh hai lượt; không có script chấm accuracy cho split `kho`.
- Tên/đường dẫn checkpoint thực tế không được hard-code trong ba script; cần xác minh riêng trước khi chạy, không đoán.
- Code root mặc định là `D:\\nlp_exp_h1`; không được âm thầm coi nó là `D:\\nlp_rf_E`.
- Báo cáo này là phân tích tĩnh; không có lệnh đánh giá nào được thực thi.
