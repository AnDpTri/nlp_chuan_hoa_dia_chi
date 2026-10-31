# Báo cáo nhãn ứng viên và phép kiểm tổng hợp (30/10/2026)

> **Trạng thái:** NHÃN ỨNG VIÊN do một bộ gán AI `codex_gpt` cung cấp. KHÔNG phải tập gold/đáp án đã được người xác nhận. Không suy ra độ chính xác trên địa chỉ thật từ số liệu tổng hợp này.

## 1. Phạm vi và nguồn

- Chỉ thực hiện trong worktree `D:\nlp_gold`, nhánh `data/gold-20261030`. Không commit, push, checkout, reset, stash.
- Không sửa mã nguồn hay công cụ có sẵn. Chỉ tạo file tại `data/gold/gan_nhan_codex/`, `data/gold/tong_hop/`, `tests/test_tong_hop*.py`, và tài liệu này.
- Không dùng mô hình/API khác trong mã. Chính bộ gán `codex_gpt` quyết định thủ công `(truong, van_ban, thu_tu_xuat_hien)` cho từng dòng, còn `doi_span_thu_cong.py` chỉ tìm chuỗi để tính offset và chạy schema validator.
- Không dùng POI/OSM tags, tọa độ, URL hoặc dữ liệu nhãn/kết quả của test để gán nhãn. Tập tổng hợp dùng danh mục hành chính và logic sinh mã đã cố định; đánh giá không dùng làm train/dev/test.

## 2. Phần A — nhãn ứng viên 800 địa chỉ

| Kiểm tra | Kết quả |
|---|---:|
| Gói có file nhãn và quyết định riêng | 16/16 |
| Số dòng gán ứng viên | 800/800 |
| Số dòng `kiem_nhan.py` báo PASS | 800/800 |
| `abstain=true` | **315/800 (39,375%)** |
| Không abstain | 485/800 (60,625%) |

Lý do abstain điển hình: tỉnh/phường trùng lặp; số nhà `12/5`, `51/18` và dải `90–92` chưa chốt quy ước; ngõ/hẻm gạch chéo, viết tắt ĐT/QL/TL/CMT8; địa danh có thể là xã hoặc đường; mã tòa nhà, mã lô, ký tự lỗi; câu không đủ thành phần. Cụ thể trong `data/gold/gan_nhan_codex/THONG_KE_NHAN_UNG_VIEN.json` và `quyet_dinh_goi_XX.tsv`.

Tệp chính: `data/gold/gan_nhan_codex/codex_gpt_800.json`. Hash SHA-256: `50df98dbb642a288960f967c802da3740c9ae8fd88487e57b45d020fcefe4ebd`.

**Không đo độ chính xác thực tế của 800 nhãn bằng cách tự đối chiếu với chính bộ gán.** Cần đồng thuận giữa các AI khác họ và kiểm tra sai số tổng hợp riêng.

## 3. Phần B — bộ kiểm tổng hợp có đáp án cố định

- Seed: `20261030`. Tổng **400 câu**: (a) viết tắt tăng dần 140 câu; (b) bỏ dấu/thiếu thành phần/đảo thứ tự/bưu chính/tòa nhà 140 câu; (c) câu rõ ràng đối chứng 120 câu.
- Địa chỉ nguồn và câu biến đổi đều được đối chiếu bằng chuỗi chuẩn hóa trước khi lưu. `ma_xa`, `ma_tinh` được tính bằng danh mục/chuyển đổi từ cấu trúc sinh; khi không phân biệt được từ chuỗi đầu vào thì gắn `khong_xac_dinh=true`; một trường có thể vẫn phân giải được trong khi toàn câu mơ hồ.
- `tong_hop_dau_vao.csv` chỉ chứa `id,dau_vao`; đáp án và span nguồn trong `tong_hop_dap_an.json`, **không chuyển đáp án cho bộ gán**.
- 8 gói x 50 câu trong `tong_hop/goi_gan_nhan/goi_01..08/`; bộ gán này đã xử lý đủ 8 gói và `kiem_nhan.py` báo PASS. Nhãn riêng từng gói `codex_gpt_tong_hop_goi_XX.json`, bản gộp `codex_gpt_tong_hop_400.json`.
- Tập thực sự trộn mù cho các mô hình khác họ: **24 gói x 50 câu** trong `tong_hop/goi_tron_mau_id_an/goi_01..24/`, lấy 800 địa chỉ thật + 400 câu tổng hợp, rồi **đổi ID ngẫu nhiên, cùng dạng `UNGVIEN_xxxx`**. Chỉ chuyển thư mục gói này. Giữ `doi_chieu_id_tron_an_RIENG_KHONG_GUI_AI.json` riêng. Gói trộn cũ trong `goi_tron_ung_vien_va_tong_hop/` giữ lại để truy vết, **không dùng để phát ngoài** vì ID liên tục có thể tiết lộ nhóm tổng hợp.
- Sau khi các bộ gán khác trả 24 file nhãn, dùng `tach_nhan_tu_goi_tron_id_an.py` để kiểm đủ 1.200 dòng và tách 400 câu tổng hợp (phục hồi ID ban đầu), rồi mới dùng `score_tong_hop.py`. Script tách không đọc đáp án.

### Hash đầu vào khóa cố định

```text
TONG_HOP_REPRODUCIBLE_PASS 91ad0115eed9c82448ba2949c526754335e66dcb8b107b845ced8bd3c01064a5
SHA256_TONG_HOP=91ad0115eed9c82448ba2949c526754335e66dcb8b107b845ced8bd3c01064a5
SHA256_ANSWERS=b92a5f9602e46ae00f8a300604c7ce15fcfae8983da738a02a0f2089b4a29368
SHA256_LABEL_B=e2e82ce331e1fcde685d92557b2f62e464b65add22be25bf1411f3724983bf53
```

## 4. Chấm `codex_gpt` trên 400 câu tổng hợp

**Kết quả thực thu, không hiệu chỉnh bộ gán sau khi mở đáp án:**

| Nhóm | Số câu | Đúng đồng thời 6 trường | Abstain | Mơ hồ | Abstain đúng khi mơ hồ | **Gán chắc nhưng sai** |
|---|---:|---:|---:|---:|---:|---:|
| a — viết tắt | 140 | 49 (35,000%) | 112 (80,000%) | 46 | 45/46 (97,826%) | **1 (0,714%)** |
| b — biến đổi khó | 140 | 87 (62,143%) | 1 (0,714%) | 36 | 0/36 (0,000%) | **88 (62,857%)** |
| c — rõ ràng | 120 | 78 (65,000%) | 1 (0,833%) | 0 | N/A | **41 (34,167%)** |
| **Toàn bộ** | **400** | **214 (53,500%)** | **114 (28,500%)** | **82** | **45/82 (54,878%)** | **130 (32,500%)** |

Định nghĩa `gán chắc nhưng sai`: `abstain=false` và **(ít nhất một trường sai hoặc đáp án toàn câu được đánh dấu mơ hồ)**. Tỷ lệ lấy mẫu số *tất cả câu của nhóm*, không phải chỉ số câu bộ gán không abstain. `Đúng đồng thời 6 trường` chấm độc lập với cờ abstain.

| Trường | Nhóm a: đúng/sai | Nhóm b: đúng/sai | Nhóm c: đúng/sai | Tổng đúng/sai |
|---|---:|---:|---:|---:|
| `so_nha` | 140/0 | 140/0 | 120/0 | **400/0** |
| `ngo_ngach_hem` | 140/0 | 140/0 | 120/0 | **400/0** |
| `thon_xom` | 140/0 | 140/0 | 120/0 | **400/0** |
| `duong` | 140/0 | 140/0 | 120/0 | **400/0** |
| `ma_xa` | **62/78** | **94/46** | **78/42** | **234/166** (58,500% đúng) |
| `ma_tinh` | **99/41** | **120/20** | **120/0** | **339/61** (84,750% đúng) |

`abstain` được định nghĩa **theo toàn dòng**, không phải mỗi trường; do đó số abstain áp dụng cho mọi trường trong từng nhóm là a=112, b=1, c=1, tổng=114. Scorer vẫn đo sự khớp từng trường ngay cả trên dòng abstain; không nên dùng các tỷ lệ khớp này làm tỷ lệ quyết định tự động thành công. Bốn trường span đạt 100% chỉ trên **các câu do mã tạo ra**; không áp dụng cho 800 địa chỉ thật.

**Cảnh báo quan trọng:** bộ gán quá tự tin ở nhóm b (88/140 câu gán chắc nhưng sai) và mã xã ở nhóm c vẫn sai 42/120. Không dùng các tỷ lệ này để khẳng định độ chính xác địa chỉ thực tế; chúng là phép đo lỗi trên phân phối câu tổng hợp và cách ánh xạ mã hiện tại. Báo cáo máy đầy đủ: `tong_hop/ket_qua_codex_gpt.json`.

## 5. Nghiệm thu và chống rò rỉ

Kết quả chạy trên nhánh `data/gold-20261030` bằng Python `D:\nlp_chuan_hoa_dia_chi\.venv-neural\Scripts\python.exe -X utf8 -B`:

```text
> python -X utf8 -B -m unittest tests.test_gold_tooling tests.test_tong_hop
----------------------------------------------------------------------
Ran 36 tests in 10.580s

OK

> python -X utf8 -B -m unittest tests.test_tong_hop_an_danh
----------------------------------------------------------------------
Ran 3 tests in 0.569s

OK

> python -X utf8 -B data/gold/tong_hop/sinh_tong_hop.py --verify
TONG_HOP_REPRODUCIBLE_PASS 91ad0115eed9c82448ba2949c526754335e66dcb8b107b845ced8bd3c01064a5

> kiem_nhan.py on 8 synthetic package JSONs, combined synthetic JSON, and original 800 JSON
NHAN_UNG_VIEN_PASS 50 bo_gan codex_gpt   [8 of 8 packages]
NHAN_UNG_VIEN_PASS 400 bo_gan codex_gpt
NHAN_UNG_VIEN_PASS 800 bo_gan codex_gpt

TONG_HOP_INDEPENDENT_LEAKAGE_PASS
```

Kiểm rò rỉ độc lập trên chuỗi chuẩn hóa đối chiếu **cả chuỗi sinh lẫn địa chỉ nguồn trước biến đổi**. Kết quả số trùng ở cả hai loại là 0, chi tiết:

| Nguồn đối chiếu | Số dòng đọc | Trùng câu sinh | Trùng chuỗi nguồn |
|---|---:|---:|---:|
| train | 4.564 | 0 | 0 |
| dev | 1.136 | 0 | 0 |
| bo_sung_v1 | 24.265 | 0 | 0 |
| bo_sung_v2 | 9.000 | 0 | 0 |
| bo_sung_v3 | 397 | 0 | 0 |
| test (chỉ cột id/dau_vao/nguon) | 400 | 0 | 0 |
| mau_ung_vien | 800 | 0 | 0 |

Chi tiết lưu `tong_hop/BAO_CAO_RO_RI_TONG_HOP.json`. Không đọc nhãn test hay kết quả test.

**Lỗi đã bắt và sửa trong quá trình dựng:** một số occurrence gây span chồng nhau được validator phát hiện ở bảng quyết định thủ công; đã sửa bảng quyết định và kiểm lại toàn bộ. Lần chạy unit test ban đầu bị **1 FAIL** vì giả định sai rằng mọi câu mơ hồ đều không thể có mã xã; đã sửa điều kiện kiểm thử theo từng trường. Lần kiểm cuối 36/36 PASS. Không sửa nhãn sau khi chấm mở đáp án.

## 6. File đầu ra và cách bàn giao

- `data/gold/gan_nhan_codex/`: `doi_span_thu_cong.py` (bộ chuyển offset, không có luật gán), `quyet_dinh_goi_01..16.tsv`, `codex_gpt_goi_01..16.json`, `gop_va_kiem_800.py`, `codex_gpt_800.json`, `THONG_KE_NHAN_UNG_VIEN.json`.
- `data/gold/tong_hop/`: `sinh_tong_hop.py`, `tong_hop_dau_vao.csv`, `tong_hop_dap_an.json`, `thong_ke_sinh.json`, `doi_chieu_id_RIENG_KHONG_GUI_AI.json`, `tao_goi_tong_hop.py`, `goi_gan_nhan/goi_01..08`, `quyet_dinh_codex_goi_01..08.tsv`, `codex_gpt_tong_hop_goi_01..08.json`, `codex_gpt_tong_hop_400.json`, `mau_kiem_schema*.csv`, `gop_kiem_codex_tong_hop.py`, `score_tong_hop.py`, `ket_qua_codex_gpt.json`, `kiem_ro_ri_tong_hop.py`, `BAO_CAO_RO_RI_TONG_HOP.json`.
- Bộ gói trộn mù khuyến nghị: `tao_goi_tron_id_an.py`, `goi_tron_mau_id_an/goi_01..24/`, `doi_chieu_id_tron_an_RIENG_KHONG_GUI_AI.json` và `tach_nhan_tu_goi_tron_id_an.py`. Gói trộn cũ `tao_goi_tron_mu.py`/`goi_tron_ung_vien_va_tong_hop/` để lưu vết, không phát ngoài vì ID còn nguyên.
- Test: `tests/test_tong_hop.py` và `tests/test_tong_hop_an_danh.py`; tài liệu này `docs/GOLD_BAO_CAO_NHAN_UNG_VIEN_TONG_HOP_20261030.md`.

**Chỉ gửi cho bên gán khác họ:** các `dau_vao.csv` + `PROMPT_GAN_NHAN.txt` của bộ gói trộn mù khuyến nghị (hoặc 16 + 8 gói gốc khi cần phép so sánh trực tiếp). **Không gửi** đáp án `tong_hop_dap_an.json`, bảng ánh xạ ID, báo cáo điểm, hay bảng quyết định nhãn `codex_gpt` khi họ chưa hoàn tất lượt gán.

## 7. Giới hạn

- Không có người xác nhận; mọi tệp tự gán là **nhãn ứng viên**. Đồng thuận giữa các mô hình khác họ chưa có và không giả định các lỗi AI độc lập.
- Đáp án tổng hợp được biết từ quá trình tạo câu/danh mục. Việc sinh và đối chiếu không thay thế kiểm định chuyên gia về tính đúng của bảng mã hành chính sau 01/07/2025.
- Dữ liệu tổng hợp dùng số nhà/tên đường ghép theo mẫu, không đại diện đầy đủ cho phân phối địa chỉ đời thực.
- Nhóm b và c bộc lộ hạn chế lớn của ánh xạ mã xã từ span. Nên xem xét với các AI khác họ trước khi sử dụng tập nhãn ứng viên để huấn luyện hay đánh giá ngoài miền.
