# BÁO CÁO KIỂM ĐỊNH AN TOÀN QUY TRÌNH ĐÁNH GIÁ CRF PRE-PATCH / POST-PATCH

- **Dự án gốc**: `D:\nlp_rf_E`
- **Worktree kiểm định**: `D:\nlp_rf_gate\wt_thonxom_C` (pre-patch read-only)
- **Branch**: `agy/thon-xom-c-20261031` | **Base commit**: `63a1f212f2d103eb0d9b7705555419f92744585d`
- **Thời điểm kiểm tra**: 2026-10-31
- **Người thực hiện**: Antigravity Inspector (Agent C)

---

## 1. Runtime thực sự import module CRF nào?

- **Căn cứ mã nguồn**:
  - `src\crf_chi_tiet.py` (dòng 1-3):
    ```python
    import sys
    from .tien_xu_ly import crf_chi_tiet as _m
    sys.modules[__name__] = _m
    ```
  - `danh_gia\do_crf.py` (dòng 15): `from src.crf_chi_tiet import BoTachCRF, bio_spans, tao_nhan`
  - `danh_gia\du_lieu_crf.py` (dòng 10): `from src.crf_chi_tiet import tao_nhan`
  - `danh_gia\huan_luyen_crf.py` (dòng 15): `from src.crf_chi_tiet import dac_trung`
  - `src\chuan_hoa.py` (dòng 5, 26-35) nạp `BoLamSach` từ `src.tien_xu_ly.lam_sach`, nơi trực tiếp quản lý đối tượng `bo_tach` (`BoTachCRF`).
- **Phân tích kỹ thuật**:
  File `src\crf_chi_tiet.py` là một wrapper chuyển tiếp hoàn toàn: khi nạp module này, nó gán đè `sys.modules[__name__] = _m`, trỏ trực tiếp đến `src.tien_xu_ly.crf_chi_tiet`. Tất cả các lớp và hàm nghiệp vụ (`BoTachCRF`, `NguCanhCRF`, `dac_trung`, `bio_spans`, `tao_nhan`, `loc_va_chinh_bien_span`) đều được thực thi tại `src\tien_xu_ly\crf_chi_tiet.py`.
- **Kết luận**: **CONFIRMED** (Wrapper chuyển tiếp hoàn toàn; runtime thực sự chạy trên `src.tien_xu_ly.crf_chi_tiet`).

---

## 2. Checkpoint CRF phù hợp để đánh giá thay đổi biên thôn/xóm

- **Căn cứ manifest & training summary**:
  - `mo_hinh\thu_nghiem\crf_v1_01\training_summary.json`:
    - `train_goc.crfsuite` (SHA-256: `1b64518446d8e9da6e9ae4afe7eb3f6d3f634cc1751a85ae55a5110ba6be01ae`):
      - 3,973 mẫu, 67,866 tokens.
      - Phân bố nhãn thôn/xóm: `B-thon_xom`: 60, `I-thon_xom`: 91 (tổng số span: 60).
    - `train_ket_hop.crfsuite` (SHA-256: `c8a9e30bb0dcf1adb56337a9af8f5f133c6cb1b1c8ad6eec1a996874a3e9d935`):
      - 5,966 mẫu (3,973 gốc + 1,993 bổ sung), 102,019 tokens.
      - Phân bố nhãn thôn/xóm: `B-thon_xom`: 126, `I-thon_xom`: 157 (tổng số span: 126, tăng gấp 2.1 lần so với bản gốc).
      - Chứa các ca biến thể ranh giới khó trong `summary_bo_sung.json` (dính ranh giới không phẩy, mất dấu viết tắt, số nhà nhiều xuyệt).
- **Căn cứ cấu hình runtime trong `danh_gia\do_crf.py` (dòng 177-180)**:
  ```python
  modes = {'luat_v3': None,
           'crf_train_goc_mo': (experiment/'train_goc.crfsuite', False),
           'crf_ket_hop_mo': (experiment/'train_ket_hop.crfsuite', False),
           'crf_ket_hop_bao_ve': (experiment/'train_ket_hop.crfsuite', True)}
  ```
  - Mode `crf_ket_hop_bao_ve` kích hoạt `bao_ve_chi_tiet=True`, ngăn chặn Trie hành chính nuốt nhầm các token thuộc tiền tố hoặc ranh giới thôn/xóm.
  - Script `do_crf.py` yêu cầu **cả hai** checkpoint `train_goc` và `train_ket_hop` phải tồn tại để chạy vòng lặp kiểm tra sha256 và đo đạc đơn lẻ (dòng 169-175).
- **Kết luận**: **CONFIRMED**
  - Checkpoint phản ánh rõ nét nhất thay đổi biên thôn/xóm là **`train_ket_hop.crfsuite`** (chế độ `crf_ket_hop_bao_ve`).
  - Quy trình đánh giá chuẩn mực của `do_crf.py` bắt buộc chạy song song cả `train_goc.crfsuite` và `train_ket_hop.crfsuite` để đảm bảo tính đối chiếu toàn diện và kiểm soát hồi quy.

---

## 3. Snapshot dev_goc / dev_kho đóng băng và mã hash

- **Căn cứ các tệp manifest**:
  - `mo_hinh\thu_nghiem\crf_v1_01\snapshot_manifest.json`
  - `mo_hinh\thu_nghiem\crf_v1_01\du_lieu_dong_bang\manifest.json`
  - `mo_hinh\thu_nghiem\crf_v1_01\du_lieu_crf\summary.json`
- **Bảng đối chiếu dữ liệu đóng băng**:

| Tập dữ liệu | Tệp vật lý | Số mẫu Input (E2E) | Số mẫu Aligned (Span) | SHA-256 Checksum | Manifest ghi nhận |
|---|---|---:|---:|---|---|
| **dev_goc** | `du_lieu_dong_bang\dev.csv` | 1,136 | 1,026 | `dbf4fd536accd05f7fbd716e2c1e7d83e7db20854b60cf0c78c2fc36d2087cfe` | `snapshot_manifest.json` & `du_lieu_dong_bang\manifest.json` |
| **dev_kho** | `du_lieu_dong_bang\dev_kho.csv` | 464 | 452 | `588767b2f5470d05a45296de24a6167f811296ed099a1b044165e5f0f9201421` | `snapshot_manifest.json` & `du_lieu_dong_bang\manifest.json` |
| **dev_spans** | `du_lieu_dong_bang\dev_spans.jsonl` | 464 | 452 | `73d68663c1d43837021febac30a3857524257f88064b7dc7051d021e9a673f16` | `snapshot_manifest.json` & `du_lieu_dong_bang\manifest.json` |

- **Cơ chế tự kiểm định an toàn dữ liệu**:
  Hàm `check_snapshot()` trong `danh_gia\do_crf.py` (dòng 162-166 và dòng 206) tự động hash SHA-256 các tệp trên đĩa và so khớp với `snapshot_manifest.json` ở cả đầu và cuối tiến trình đánh giá. Nếu có bất kỳ sự sai lệch nào, chương trình lập tức ném lỗi `ValueError('Snapshot đã đổi ' + name)`.
- **Kết luận**: **CONFIRMED** (Dữ liệu đã đóng băng nghiêm ngặt, hash đồng nhất giữa 2 manifest).

---

## 4. Script đánh giá, phân biệt Span và End-to-End (Exact-6)

- **Script đánh giá**: `danh_gia\do_crf.py` (hàm `run()`).
- **Phân tầng chỉ số đo lường**:
  1. **CRF Đơn lẻ (Standalone / BIO Sequence)**:
     - `token_accuracy_pct`: Độ chính xác trên mọi token (bị loãng bởi nhãn 'O' chiếm ~72%).
     - `token_non_o.f1_pct`: F1 trên các token thực thể (`g != 'O'` hoặc `p != 'O'`).
     - `sequence_exact_pct`: Tỷ lệ chuỗi gán đúng 100% tất cả các token BIO.
     - `span_micro.f1_pct`: F1 trên thực thể trích xuất qua `bio_spans()`. **Yêu cầu đúng cả loại nhãn (role) VÀ đúng cả hai biên (start, end)**. Lệch 1 token ranh giới tính là 1 FP và 1 FN.
  2. **Pipeline End-to-End**:
     - `actual_pipeline_spans_on_aligned_subset`: Đo lại span sau khi đã qua Beam Search, lọc đường, tiền tố và giải mã hành chính.
     - `detail_4_exact_pct`: Tỷ lệ khớp chính xác chuỗi văn bản đã chuẩn hóa của 4 trường chi tiết (`so_nha`, `ngo_ngach_hem`, `duong`, `thon_xom`).
     - `khop_toan_bo_6_truong_pct` (**Exact-6**): Tiêu chuẩn khắt khe nhất, đo độ khớp đồng thời của cả 6 trường:
       `CORE = ('so_nha', 'ngo_ngach_hem', 'duong', 'thon_xom', 'ma_xa', 'ma_tinh')`.
- **Bản chất khác biệt**:
  Span F1 chỉ đo mức nhận diện nhãn ranh giới cục bộ. Exact-6 đòi hỏi toàn bộ hệ thống phải đúng: span thôn/xóm đúng nhưng chuyển đổi sai mã xã đích thì Exact-6 vẫn tính là sai. Ngược lại, token accuracy cao không bảo đảm ranh giới thực thể nguyên vẹn.
- **Kết luận**: **CONFIRMED**.

---

## 5. Rủi ro đường dẫn tuyệt đối, CWD, Cache và Sparse Checkout

Phát hiện 3 rủi ro kỹ thuật có thể gây sai lệch kết quả kiểm định:

1. **Rủi ro CWD và `PYTHONPATH` (NGHIÊM TRỌNG)**:
   Nếu kỹ sư đứng ở thư mục khác (như `wt_thonxom_A` hoặc `D:\nlp_rf_E`) mà gọi script của `wt_thonxom_C`, Python sẽ nạp module `src` từ thư mục hiện hành (`sys.path[0]`) thay vì từ worktree C.
   => **Biện pháp**: Bắt buộc `Set-Location` vào đúng thư mục gốc của worktree trước khi chạy và gán rõ biến môi trường `$env:PYTHONPATH`.
2. **Rủi ro thiếu tệp tham chiếu baseline v3 do Sparse Checkout (GÂY CRASH)**:
   - Trong `danh_gia\do_crf.py` dòng 198-200:
     ```python
     prior = experiment.parents[2]/'danh_gia/ket_qua/ban_thu_v3_cuoi/du_doan.jsonl'
     base = {r['id']: r for r in doc_jsonl(prior)}
     ```
   - Kiểm tra thực tế tại `D:\nlp_rf_gate\wt_thonxom_C`: Tệp `danh_gia\ket_qua\ban_thu_v3_cuoi\du_doan.jsonl` **chưa được checkout** do cấu hình sparse-checkout hiện hành (chỉ nạp 12% tệp).
   - Nếu chạy trực tiếp, script sẽ lập tức văng `FileNotFoundError`.
   - Lưu ý thêm: Dòng 201-205 kiểm tra độ bất biến của baseline `luat_v3`. Nếu patch mới trên Worktree A vô tình làm đổi kết quả của `luat_v3` trên `dev_goc`, script sẽ raise `ValueError('Adapter làm đổi baseline ...')`.
3. **Rủi ro Bytecode Cache (`__pycache__`)**:
   Các tệp `.pyc` cũ có thể nạp sai logic giữa các lần sửa đổi.
   => **Biện pháp**: Bắt buộc dùng cờ `-B` (`PYTHONDONTWRITEBYTECODE=1`).
- **Kết luận**: **CONFIRMED RỦI RO** (Cần thiết lập CWD, PYTHONPATH, bytecode flag, và bổ sung file `ban_thu_v3_cuoi/du_doan.jsonl` vào sparse checkout trước khi chạy).

---

## 6. Đề xuất quy trình chạy Pre-patch (Worktree C) và Post-patch (Worktree A)

- **Môi trường thực thi thống nhất**:
  - Python Interpreter: `D:\nlp_rf_gate\venv_gpu\Scripts\python.exe` (Python 3.12, `python-crfsuite 0.9.12`).
  - Dữ liệu thử nghiệm: Cùng trỏ tới snapshot đóng băng trong `crf_v1_01`.

### Bước 1: Mở rộng Sparse Checkout (thực hiện trên cả hai worktree)
```powershell
# Chạy tại worktree tương ứng (C và A):
git sparse-checkout add danh_gia/ket_qua/ban_thu_v3_cuoi/du_doan.jsonl
```

### Bước 2: Chạy đánh giá Pre-patch trên Worktree C
```powershell
Set-Location -Path "D:\nlp_rf_gate\wt_thonxom_C"
$env:PYTHONPATH = "D:\nlp_rf_gate\wt_thonxom_C"
$env:PYTHONDONTWRITEBYTECODE = "1"

& "D:\nlp_rf_gate\venv_gpu\Scripts\python.exe" -B danh_gia\do_crf.py `
  --experiment "D:\nlp_rf_gate\wt_thonxom_C\mo_hinh\thu_nghiem\crf_v1_01" `
  --output-dir "D:\nlp_rf_gate\wt_thonxom_C\danh_gia\ket_qua\eval_crf_pre_patch_20261031"
```

### Bước 3: Chạy đánh giá Post-patch trên Worktree A
```powershell
Set-Location -Path "D:\nlp_rf_gate\wt_thonxom_A"
$env:PYTHONPATH = "D:\nlp_rf_gate\wt_thonxom_A"
$env:PYTHONDONTWRITEBYTECODE = "1"

& "D:\nlp_rf_gate\venv_gpu\Scripts\python.exe" -B danh_gia\do_crf.py `
  --experiment "D:\nlp_rf_gate\wt_thonxom_A\mo_hinh\thu_nghiem\crf_v1_01" `
  --output-dir "D:\nlp_rf_gate\wt_thonxom_A\danh_gia\ket_qua\eval_crf_post_patch_20261031"
```
- **Kết luận**: **CONFIRMED**.

---

## 7. Các file có nguy cơ ghi đè và cách đặt Output Directory

- **Cơ chế chống ghi đè của mã nguồn**:
  - `danh_gia\do_crf.py` (dòng 157): `output.mkdir(parents=True, exist_ok=False)`. Nếu thư mục đầu ra đã tồn tại, tiến trình lập tức dừng với lỗi `FileExistsError`.
  - `danh_gia\huan_luyen_crf.py` (dòng 22): `if model_path.exists(): raise ValueError('Không ghi đè mô hình đã train; tạo thí nghiệm mới')`.
- **Danh sách file sinh ra trong output directory**:
  1. 08 file JSONL dự đoán: `luat_v3_{split}.jsonl`, `crf_train_goc_mo_{split}.jsonl`, `crf_ket_hop_mo_{split}.jsonl`, `crf_ket_hop_bao_ve_{split}.jsonl` (với split là `dev_goc` và `dev_kho`).
  2. 06 file CSV so sánh với luật v3: `so_sanh_{mode}_{split}.csv`.
  3. 02 file báo cáo: `thong_ke.json` và `BAO_CAO.md`.
- **Quy tắc đặt output directory an toàn**:
  - Đặt thư mục mới hoàn toàn, có gắn định danh commit và ngày giờ rõ ràng:
    - Pre-patch: `danh_gia\ket_qua\eval_crf_pre_patch_63a1f21_20261031`
    - Post-patch: `danh_gia\ket_qua\eval_crf_post_patch_<commit>_20261031`
  - Tuyệt đối không trỏ `--output-dir` vào `mo_hinh\thu_nghiem\crf_v1_01` hoặc các thư mục kết quả đã có trong kho lưu trữ.
- **Kết luận**: **CONFIRMED**.

---

## 8. Đề xuất so sánh hai chiều Gained / Lost theo từng ID

- **Căn cứ kỹ thuật**:
  Hàm `compare_examples` trong `danh_gia\do_crf.py` (dòng 137-154) cung cấp logic phân loại 4 trạng thái chuẩn tắc cho từng ID:
  - `moi_khop` (**Gained**): Pre-patch sai Exact-6, Post-patch đúng Exact-6.
  - `mat_khop` (**Lost / Regression**): Pre-patch đúng Exact-6, Post-patch bị sai Exact-6 (hồi quy).
  - `giu_khop` (**Kept**): Cả hai đều đúng Exact-6.
  - `van_lech` (**Both Wrong**): Cả hai đều sai (phân tích chi tiết trường lệch: `wrong_after`).
- **Quy trình so sánh đối đầu Pre vs Post**:
  Sau khi có kết quả từ Mục 6, thực hiện so sánh trực tiếp giữa `pre_patch` và `post_patch` trên mode quan trọng nhất (`crf_ket_hop_bao_ve` trên `dev_kho` và `dev_goc`):
  1. Nạp `pre_predictions` từ `eval_crf_pre_patch\crf_ket_hop_bao_ve_{split}.jsonl`.
  2. Nạp `post_predictions` từ `eval_crf_post_patch\crf_ket_hop_bao_ve_{split}.jsonl`.
  3. Nạp ground-truth `reference` từ snapshot đóng băng (`dev.csv` / `dev_kho.csv`).
  4. Xuất bảng chi tiết `so_sanh_pre_vs_post_crf_ket_hop_bao_ve_{split}.csv` gồm:
     `id, state, input, pre_6, post_6, reference_6, wrong_fields_post, warnings_post`.
  5. Báo cáo bắt buộc nêu định lượng cả 2 chiều:
     $$\text{Đúng thêm (Gained)} = +X, \quad \text{Sai thêm (Regressed)} = -Y, \quad \text{Chênh lệch ròng (Net)} = +(X - Y)$$
     Tuyệt đối không chỉ đưa ra tỷ lệ phần trăm tổng thể.
- **Kết luận**: **CONFIRMED**.

---

## 9. Tổng hợp mức độ tin cậy kết luận

| Nội dung kiểm định | Trạng thái | Ghi chú & Điều kiện kích hoạt |
|---|---|---|
| 1. Wrapper và Runtime CRF | **CONFIRMED** | Chuyển tiếp trực tiếp sang `src.tien_xu_ly.crf_chi_tiet` qua `sys.modules`. |
| 2. Checkpoint phù hợp thôn/xóm | **CONFIRMED** | `train_ket_hop.crfsuite` (mode `crf_ket_hop_bao_ve`, 126 spans). Cần cả 2 checkpoint cho script. |
| 3. Snapshot dữ liệu đóng băng | **CONFIRMED** | `dev.csv` (1136) và `dev_kho.csv` (464) khớp SHA-256 hoàn toàn với 2 manifest. |
| 4. Đo lường Span & End-to-End | **CONFIRMED** | `danh_gia\do_crf.py` đo đầy đủ cả standalone span F1 và pipeline exact-6. |
| 5. An toàn đường dẫn & Cache | **CONFIRMED RỦI RO** | Phải cô lập CWD, gán `PYTHONPATH`, dùng `-B` và sparse checkout `ban_thu_v3_cuoi/du_doan.jsonl`. |
| 6. Kế hoạch chạy C và A | **CONFIRMED** | Dùng chung Python `venv_gpu`, chia output-dir độc lập. |
| 7. Ngăn ngừa ghi đè tệp | **CONFIRMED** | Cơ chế `exist_ok=False` đã có sẵn; đặt tên output-dir mới riêng biệt. |
| 8. Báo cáo hai chiều Gained/Lost | **CONFIRMED** | Đối chiếu theo từng ID qua 4 trạng thái (`moi_khop`, `mat_khop`, `giu_khop`, `van_lech`). |

> [!IMPORTANT]
> **Khuyến nghị trước khi điều phối chạy thực tế**:
> Không tự ý chạy pipeline khi chưa cập nhật `git sparse-checkout add danh_gia/ket_qua/ban_thu_v3_cuoi/du_doan.jsonl` tại các worktree, nhằm tránh lỗi gián đoạn tiến trình kiểm định.
