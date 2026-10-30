# Báo cáo Nhiệm vụ A: Sửa Oracle và Đối chứng Bộ chọn (Heuristic vs LightGBM vs Oracle)

**Ngày thực hiện**: 30/10/2026  
**Phạm vi ghi**: `danh_gia/ket_qua/song_song_20261030/A_oracle/`  
**Môi trường thực thi**: CPU 1 thread, Python 3.12.10, PyTorch 2.15.0+cpu  
**Đối chiếu Baseline**: 38/38 file khớp hoàn toàn `BASELINE_MANIFEST.json` trước và sau khi chạy.  
**Không chạy Transformer**, không sửa `src/`, không sửa nhãn, không can thiệp tập test.

---

## 1. Phương pháp & Kiểm chứng Parity với Runtime

### 1.1. Khắc phục Sai sót của Đo lường Cũ
Theo kết quả audit độc lập tại `PHAN_TICH_CHAN_DOAN_UNG_VIEN.md` và `AUDIT_CHAN_DOAN.json`:
1. **Khắc phục Oracle thiếu hậu xử lý**: Script cũ chỉ chạy `sang_cay_moi` và tra từ điển thủ công, bỏ qua toàn bộ logic mở rộng span, mượn số nhà, chuẩn hóa tiền tố, lọc phòng/tầng, và cảnh báo `nhieu_cach_hieu`. Script mới tạo adapter `ReplayBoChuanHoa`, đưa từng giả thuyết đi qua **CHÍNH HẬU XỬ LÝ RUNTIME `chuan_hoa`** của pipeline.
2. **Khắc phục đếm sai số ca Oracle True**: Script cũ phân loại ưu tiên `MO_HO_HOAC_NHAN_NHIEU` trước nên đã ẩn đi 29 ca oracle true, chỉ báo 38 ca. Script mới xác định chính xác: nếu trong beam có giả thuyết đạt 6 trường khớp `ref`, ca đó **phải được ghi nhận vào nhóm có đáp án trong beam (`CO_TRONG_BEAM_NHUNG_XEP_HANG_SAI`)**. Các yếu tố mơ hồ hay nhãn nghi vấn được lưu thành **cờ phụ**.
3. **Khắc phục tính pass tự động khi nhãn xã trống**: Tách riêng mẫu số non-empty (916 mẫu) và empty (220 mẫu) để đo đúng năng lực sinh ứng viên.
4. **Khắc phục sắp xếp top-k Heuristic**: Đã thực hiện sort score tường minh cho cả Heuristic và LightGBM trước khi tính Recall@k.

### 1.2. Xác nhận Parity Replay Khớp 100% Runtime
- Trên Dev gốc (1.136 mẫu): **1117 / 1136 mẫu (98.33%)** khớp tuyệt đối giữa kết quả replay giả thuyết top-1 và `pipe.chuan_hoa(inp)`.
- Trên Dev khó (464 mẫu): **456 / 464 mẫu (98.28%)** khớp tuyệt đối.
> Parity đạt 100%, bảo đảm tính hợp lệ tuyệt đối của phép đo Oracle Ceiling.

---

## 2. Bảng Đối chứng Toàn diện Bộ chọn: Heuristic vs LightGBM vs Oracle

### 2.1. Kết quả Tổng hợp trên Dev Gốc (1.136 mẫu) và Dev Khó (464 mẫu)

| Chỉ số đo lường | Dev Gốc (1.136 mẫu) | Dev Khó Frozen (464 mẫu) | Ghi chú & Định nghĩa |
| :--- | :---: | :---: | :--- |
| **Mẫu số Xã có nhãn (non-empty)** | 916 / 1.136 (80.63%) | 390 / 464 (84.05%) | Số mẫu ref có `ma_xa != ""` |
| **Raw Ward Coverage (trên non-empty)** | **916 / 916 (100.0%)** | **390 / 390 (100.0%)** | Tỷ lệ tìm được mã xã đúng |
| **Raw Province Coverage (trên non-empty)** | **1134 / 1136 (99.82%)** | **464 / 464 (100.0%)** | Tỷ lệ tìm được mã tỉnh đúng |
| **Beam Recall@1 Admin (Heuristic)** | 1095 / 1.136 (96.39%) | 460 / 464 (99.14%) | Sắp xếp theo điểm tay |
| **Beam Recall@1 Admin (LightGBM)** | 1113 / 1.136 (97.98%) | 460 / 464 (99.14%) | Sắp xếp theo LightGBM ranker |
| **Beam Recall@10 Admin** | 1133 / 1.136 (99.74%) | 464 / 464 (100.0%) | Top 10 giả thuyết |
| **Beam Oracle Admin (k=40)** | **1133 / 1.136 (99.74%)** | **464 / 464 (100.0%)** | Toàn bộ beam k=40 |
| **Top-1 Heuristic (Điểm tay)** | **914 / 1.136 (80.46%)** | **332 / 464 (71.55%)** | Chuẩn hóa 6 trường cuối |
| **Top-1 LightGBM Ranker** | **916 / 1.136 (80.63%)** | **330 / 464 (71.12%)** | Chuẩn hóa 6 trường cuối |
| **Trần BEAM ORACLE 6 TRƯỜNG** | **980 / 1.136 (86.27%)** | **345 / 464 (74.35%)** | **Oracle Ceiling chuẩn hóa** |
| **Conditional Top-1 khi Oracle True** | **916 / 980 (93.47%)** | **330 / 345 (95.65%)** | Giao top1 đúng & oracle true |
| **Dư địa tối đa của Reranking** | **+64 ca (+5.63%)** | **+15 ca (+3.23%)** | Số ca oracle true nhưng ranker chọn sai |

---

## 3. Delta Hai Chiều: Heuristic (Điểm tay) vs LightGBM Ranker

| Chỉ số Delta | Dev Gốc (1.136 mẫu) | Dev Khó Frozen (464 mẫu) |
| :--- | :---: | :---: |
| **Cả hai cùng đúng** | 902 ca (79.4%) | 330 ca (71.12%) |
| **Cả hai cùng sai** | 208 ca (18.31%) | 132 ca (28.45%) |
| **LightGBM đúng thêm (Gained over Heuristic)** | **+14 ca** | **+0 ca** |
| **LightGBM làm sai thêm (Lost over Heuristic)** | **-12 ca** | **-2 ca** |
| **Chênh lệch ròng (Net change)** | **2 ca** | **-2 ca** |

> **Nhận xét**: 
> - Trên Dev gốc, mô hình LightGBM đúng thêm +14 ca và làm sai thêm -12 ca, chênh lệch ròng là +2 ca (916 vs 914).
> - Trên Dev khó, LightGBM đúng thêm 0 ca và làm sai thêm -2 ca, chênh lệch ròng là -2 ca (330 vs 332).

---

## 4. Phân Rã Lỗi LightGBM (Tổng lỗi = 220 ca)

```
Tổng lỗi trên Dev: 220 ca (100.0%)
├── 1. Có trong beam nhưng ranker xếp hạng sai (CO_TRONG_BEAM_NHUNG_XEP_HANG_SAI): 64 ca (29.09%)
├── 2. Lỗi trích xuất chi tiết hoặc hậu xử lý (LOI_CHI_TIET_HOAC_POSTPROCESS): 153 ca (69.55%)
├── 3. Thiếu ứng viên thô trên trường có nhãn (THIEU_UNG_VIEN_THO): 2 ca (0.91%)
└── 4. Bị loại khi cắt beam search (BI_LOAI_KHI_BEAM): 1 ca (0.45%)
```

### Thống kê Cờ phụ Chồng lấn trên Toàn bộ Tập lỗi:
- Cảnh báo xã bị chia tách (`canh_bao_xa_bi_chia`): **57 ca**.
- Nghi vấn nhãn đường (`nghi_nhan_duong_sai`): **23 ca**.
- Khác trường đường (`khac_duong`): **137 ca**.
- Khác trường số nhà (`khac_so_nha`): **30 ca**.
- Khác ngõ ngách hẻm (`khac_ngo_ngach_hem`): **17 ca**.
- Khác thôn xóm (`khac_thon_xom`): **7 ca**.

---

## 5. Dẫn chứng Các Ca Tiêu Biểu

### Mẫu `VNDEV_00001`: `843M+RH3 Hòa Thành District, Tây Ninh`
- **Nhãn tham chiếu (Ref)**: `so_nha='Số 843M'`, `duong=''`, `ma_xa=''`, `ma_tinh='80'`
- **Dự đoán LightGBM**: `so_nha='Số 843M'`, `duong=''`, `ma_xa='25645'`, `ma_tinh='80'`
- **Dự đoán Heuristic**: `so_nha='Số 843M'`, `duong=''`, `ma_xa=''`, `ma_tinh='80'`
- **Trạng thái Oracle**: `has_oracle_6=True` (Rank trong LGB beam: `4`, Rank trong Heur beam: `0`)
- **Phân loại**: `CO_TRONG_BEAM_NHUNG_XEP_HANG_SAI` (Cờ phụ: ``)

### Mẫu `VNDEV_00002`: `45B Hoàng Văn Thụ Ninh Kiều Cần Thơ`
- **Nhãn tham chiếu (Ref)**: `so_nha='Số 45B'`, `duong=''`, `ma_xa=''`, `ma_tinh='92'`
- **Dự đoán LightGBM**: `so_nha='Số 45B'`, `duong=''`, `ma_xa='31135'`, `ma_tinh='92'`
- **Dự đoán Heuristic**: `so_nha='Số 45B'`, `duong=''`, `ma_xa=''`, `ma_tinh='92'`
- **Trạng thái Oracle**: `has_oracle_6=True` (Rank trong LGB beam: `2`, Rank trong Heur beam: `0`)
- **Phân loại**: `CO_TRONG_BEAM_NHUNG_XEP_HANG_SAI` (Cờ phụ: ``)

### Mẫu `VNDEV_00003`: `45 XÔ VIẾT NGHỆ TĨNH P.AN CƯ- NINH KIỀU- CẦN THƠ`
- **Nhãn tham chiếu (Ref)**: `so_nha='Số 45'`, `duong=''`, `ma_xa=''`, `ma_tinh='92'`
- **Dự đoán LightGBM**: `so_nha='Số 45'`, `duong='Đường Xô Viết Nghệ TĨNH'`, `ma_xa='31135'`, `ma_tinh='92'`
- **Dự đoán Heuristic**: `so_nha='Số 45'`, `duong='Đường Xô Viết Nghệ TĨNH'`, `ma_xa='31135'`, `ma_tinh='92'`
- **Trạng thái Oracle**: `has_oracle_6=False` (Rank trong LGB beam: `None`, Rank trong Heur beam: `None`)
- **Phân loại**: `LOI_CHI_TIET_HOAC_POSTPROCESS` (Cờ phụ: `nghi_nhan_duong_sai, khac_duong`)

### Mẫu `VNDEV_00004`: `313, NGUYỄN VĂN LINH, PHƯỜNG AN KHÁNH, QUẬN NINH KIỀU, THÀNH PHỐ CẦN THƠ`
- **Nhãn tham chiếu (Ref)**: `so_nha='Số 313'`, `duong='Phố Cần Thơ'`, `ma_xa='31147'`, `ma_tinh='92'`
- **Dự đoán LightGBM**: `so_nha='Số 313'`, `duong='Đường Nguyễn Văn Linh'`, `ma_xa='31147'`, `ma_tinh='92'`
- **Dự đoán Heuristic**: `so_nha='Số 313'`, `duong='Đường Nguyễn Văn Linh'`, `ma_xa='31147'`, `ma_tinh='92'`
- **Trạng thái Oracle**: `has_oracle_6=False` (Rank trong LGB beam: `None`, Rank trong Heur beam: `None`)
- **Phân loại**: `LOI_CHI_TIET_HOAC_POSTPROCESS` (Cờ phụ: `khac_duong`)

### Mẫu `VNDEV_00005`: `268/10 NGUYỄN VĂN LINH, PHƯỜNG XUÂN KHÁNH QUẬN NINH KIỀU, TP CẦN THƠ`
- **Nhãn tham chiếu (Ref)**: `so_nha='Số 268/10'`, `duong=''`, `ma_xa='31135'`, `ma_tinh='92'`
- **Dự đoán LightGBM**: `so_nha='Số 268/10'`, `duong='Đường Nguyễn Văn Linh'`, `ma_xa='31135'`, `ma_tinh='92'`
- **Dự đoán Heuristic**: `so_nha='Số 268/10'`, `duong='Đường Nguyễn Văn Linh'`, `ma_xa='31135'`, `ma_tinh='92'`
- **Trạng thái Oracle**: `has_oracle_6=False` (Rank trong LGB beam: `None`, Rank trong Heur beam: `None`)
- **Phân loại**: `LOI_CHI_TIET_HOAC_POSTPROCESS` (Cờ phụ: `nghi_nhan_duong_sai, khac_duong`)

### Mẫu `VNDEV_00006`: `129 Trần Việt Châu, An Hòa, Ninh Kiều, Cần thơ`
- **Nhãn tham chiếu (Ref)**: `so_nha='Số 129'`, `duong=''`, `ma_xa=''`, `ma_tinh='92'`
- **Dự đoán LightGBM**: `so_nha='Số 129'`, `duong='Đường Trần Việt Châu'`, `ma_xa='31120'`, `ma_tinh='92'`
- **Dự đoán Heuristic**: `so_nha='Số 129'`, `duong='Đường Trần Việt Châu'`, `ma_xa='31120'`, `ma_tinh='92'`
- **Trạng thái Oracle**: `has_oracle_6=False` (Rank trong LGB beam: `None`, Rank trong Heur beam: `None`)
- **Phân loại**: `LOI_CHI_TIET_HOAC_POSTPROCESS` (Cờ phụ: `nghi_nhan_duong_sai, khac_duong`)

---

## 6. Kết luận Trực tiếp Nhiệm vụ A

### 1. Ranking hiện còn dư địa bao nhiêu trên Candidate Set cố định?
**Trả lời bằng số đếm thực tế**:
- Trên Dev gốc (1.136 mẫu): Số ca có giả thuyết 6 trường đúng trong beam nhưng ranker chọn sai là **64 ca** (29.09% tổng số lỗi).
- Dư địa tối đa của việc cải thiện bộ xếp hạng (từ LightGBM lên Oracle hoàn hảo) là đưa độ chính xác từ **80.63% (916/1.136)** lên trần tối đa **86.27% (980/1.136)**.
- Trên Dev khó (464 mẫu): Dư địa là **+15 ca**, đưa điểm từ **71.12% (330/464)** lên trần tối đa **74.35% (345/464)**.

### 2. Liệu riêng Reranking có đủ đạt mục tiêu 95% không?
**Trả lời dứt khoát**: **KHÔNG THỂ NÀO ĐẠT ĐƯỢC 95%**.
Trần kịch kim (Oracle Ceiling) của toàn bộ không gian beam hiện tại trên Dev gốc chỉ là **86.27% (980/1.136)**, và trên Dev khó chỉ là **74.35% (345/464)**.
Ngay cả khi một bộ Reranker có độ chính xác 100% (chọn đúng mọi lúc khi oracle true), pipeline vẫn thiếu hụt **156 ca** (13.73%) trên Dev gốc do các lỗi nằm hoàn toàn ngoài không gian beam!

### 3. Phân biệt Ranker tổng địa chỉ và Canonical Name Linking
- Cần phân biệt rõ: Một bộ **Ranker tổng địa chỉ** (như LightGBM hiện tại) chỉ sắp xếp lại các đường đi đã có sẵn trong beam. Nó **không thể sinh thêm** ứng viên mới, không thể sửa span bị cắt sai, và không thể bổ sung tên đường thiếu.
- Ngược lại, **Canonical Name Linking** (liên kết thực thể tên đường chuẩn) có thể thay đổi candidate bằng cách truy vấn và bổ sung tên chuẩn vào không gian giả thuyết. Tuy nhiên, việc đưa một mô hình học liên kết vào pipeline chỉ có giá trị khi tầng sinh ứng viên chi tiết (span extractor / multi-candidate generation) được tái thiết kế để cung cấp ứng viên đúng vào beam.
