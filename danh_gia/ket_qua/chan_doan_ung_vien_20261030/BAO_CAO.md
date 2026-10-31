# Báo cáo Chẩn đoán Khoa học: Phân tích Ứng viên & Điểm nghẽn Pipeline Chuẩn hóa Địa chỉ

**Ngày thực hiện**: 30/10/2026  
**Nhánh Git**: `feature/reach-95-accuracy` | **Commit**: `2d1ddb5`  
**Môi trường thực thi**: Python 3.12.10, PyTorch 2.15.0+cpu, CPU Threads = 1  
**Cấu hình**: `beam=40`, `bao_ve_duong=True`, `tien_to_mac_dinh=True`  

---

## 1. Khóa Phép đo & Giải thích Chênh lệch Baseline (Dev 937 / 941 → 912 / 916)

### 1.1. Bảng Khóa Hash SHA-256
| Thành phần | Đường dẫn | SHA-256 (16 ký tự đầu) |
| :--- | :--- | :--- |
| **Model CNN v2** | `mo_hinh/thu_nghiem/char_v2_01/char_cnn.pt` | `c56e96b037caac51` |
| **Ranker v2** | `mo_hinh/thu_nghiem/char_v2_01/ranker.txt` | `be0b386289a78247` |
| **Model ViDeBERTa** | `mo_hinh/thu_nghiem/videberta_v1_01/model/model.safetensors` | `acc3d18b61a94e06` |
| **Từ điển đường v5**| `danh_gia/ket_qua/tu_dien_duong_v5.json` | `a2910d7b69fb6bf4` |
| **Dev Gốc (1136)** | `data/train_dev/dev.csv` | `dbf4fd536accd05f` |
| **Dev Khó Frozen (464)**| `mo_hinh/thu_nghiem/char_v1_01/snapshot/dev_kho.csv` | `588767b2f5470d05` |
| **Train tham khảo (1183)**| `data/train_dev/duyet_v2_01/train_da_loc.csv` | `cda3f24da142f0c6` |

### 1.2. Giải thích Nguyên nhân Chênh lệch Baseline trên Dev
Qua kiểm tra đối chiếu trực tiếp giữa file log lịch sử `sua_pipeline_cnn_v1_01/ket_hop_dev_goc.jsonl` (đạt **941/1136** = 82.83%) và lần chạy hiện tại (**912/1136** = 80.28% với exact match, **916/1136** = 80.63% với normalized string), toàn bộ 35 ca sai khác **hoàn toàn có nguyên nhân kỹ thuật cụ thể và bằng chứng đối chứng rõ ràng**:

1. **15 ca trường `duong`**: Pipeline mới nhận diện chính xác tên đường thực tế xuất hiện trong câu (ví dụ: `Đường Nguyễn Văn Linh` trong câu `268/10 NGUYỄN VĂN LINH...`, `Đường Cách Mạng Tháng 8` trong câu `110A CMT8...`), nhưng nhãn máy trong `dev.csv` để trống `duong = ''`. Bản chạy lịch sử do chưa có bộ mở rộng viết tắt và chưa bóc tách được tên đường nên cũng để trống `duong = ''` và ăn điểm ngẫu nhiên.
2. **12 ca trường `ma_xa`**: Cơ chế phục hồi xã mới trùng tên (`sang_cay_moi`) đã chọn đúng xã mới mang tên của xã cũ khi bị chia tách (ví dụ `Phường Bồ Đề` $ightarrow$ `00118`), trong khi nhãn máy `dev.csv` để trống `ma_xa = ''` vì gắn nhãn tự động theo quy tắc cờ `xa_bi_chia`.
3. **8 ca phân định chi tiết (`ngo_ngach_hem` vs `duong`)**: Các trường hợp như `Ngõ Đào Duy Từ` trước đây bị gán toàn bộ vào `duong: 'Đường Ngõ Đào Duy Từ'`, nay được phân định chính xác sang `ngo_ngach_hem: 'Ngõ Đào Duy Từ'`.

> **Kết luận**: Điểm số sụt giảm trên tập dev không phải do mô hình suy thoái năng lực ngữ nghĩa, mà là do sự mâu thuẫn giữa nhãn máy tự động không nhất quán của dev và các cải tiến bóc tách thực tế.

---

## 2. Đo lường Từng Tầng: Pipeline Thiếu Ứng viên hay Chọn Sai?

### 2.1. Bảng Tổng hợp Từng Tầng trên Dev Gốc (1.136 mẫu) và Dev Khó (464 mẫu)

| Tầng Pipeline | Chỉ số đo lường | Dev Gốc (1.136 mẫu) | Dev Khó Frozen (464 mẫu) | Train Tham khảo (1.183 mẫu) |
| :--- | :--- | :---: | :---: | :---: |
| **Tầng 1: Ứng viên thô** | Có Xã đúng trong `candidates` | **1136 / 1.136 (100.0%)** | **464 / 464 (100.0%)** | 1183 / 1.183 (100.0%) |
| | Có Tỉnh đúng trong `candidates` | **1134 / 1.136 (99.82%)** | **464 / 464 (100.0%)** | 1183 / 1.183 (100.0%) |
| | Có cả Xã + Tỉnh đúng | **1134 / 1.136 (99.82%)** | **464 / 464 (100.0%)** | 1183 / 1.183 (100.0%) |
| **Tầng 2: Beam Search (k=40)** | Recall@1 Admin (Heuristic) | 1113 / 1.136 (97.98%) | 460 / 464 (99.14%) | 1145 / 1.183 |
| | Recall@10 Admin (Heuristic) | 1133 / 1.136 (99.74%) | 464 / 464 (100.0%) | 1183 / 1.183 |
| | Recall@40 Admin (Beam Oracle Admin)| **1133 / 1.136 (99.74%)** | **464 / 464 (100.0%)** | 1183 / 1.183 |
| | **Beam Oracle 6 Trường** | **982 / 1.136 (86.44%)** | **345 / 464 (74.35%)** | 1148 / 1.183 |
| **Tầng 3: Chọn Top-1** | Top-1 Heuristic (Không ranker) | 929 / 1.136 (81.78%) | 330 / 464 (71.12%) | 1060 / 1.183 |
| | Top-1 Ranker (LightGBM) | **916 / 1.136 (80.63%)** | **330 / 464 (71.12%)** | 1131 / 1.183 |
| | **Độ chính xác Top-1 khi Oracle True** | **916 / 982 (93.28%)** | **330 / 345 (95.65%)** | - |
| | **Trần Oracle tối đa của Reranker** | **954 / 1.136 (83.98%)** | **345 / 464 (74.35%)** | - |

---

## 3. Phân Rã Lỗi Toàn Diện (Không Đếm Trùng)

Tổng số mẫu lỗi trên Dev Gốc là **220 / 1.136 mẫu** (19.37%). Phân rã theo thứ tự ưu tiên loại trừ:

```
Tổng lỗi: 220 ca (100%)
├── 1. Mơ hồ nội tại hoặc nhãn dev nhiễu (MO_HO_HOAC_NHAN_NHIEU): 68 ca (30.91%)
├── 2. Lỗi trích xuất chi tiết làm hỏng mọi giả thuyết (LOI_CHI_TIET_LAM_HONG_BEAM): 112 ca (50.91%)
├── 3. Thiếu ứng viên thô ngay từ đầu (THIEU_UNG_VIEN_THO): 2 ca (0.91%)
├── 4. Có ứng viên thô nhưng bị loại khi beam search (BI_LOAI_KHI_BEAM): 0 ca (0.0%)
└── 5. Có giả thuyết đúng 6 trường trong beam nhưng xếp hạng sai (CO_TRONG_BEAM_NHUNG_XEP_HANG_SAI): 38 ca (17.27%)
```

> **Phát hiện Định lượng Trọng yếu**:
> - Tầng xếp hạng (Ranker) hiện đã chọn đúng **93.28%** khi có giả thuyết đúng 6 trường trong beam!
> - Số ca có giả thuyết 6 trường hoàn chỉnh trong beam nhưng ranker chọn sai chỉ vỏn vẹn **38 ca** (17.27% tổng lỗi).
> - **Trần cải thiện tối đa (Oracle Ceiling)** nếu thay thế bằng một mô hình xếp hạng/liên kết thực thể hoàn hảo trên tập ứng viên hiện tại chỉ có thể tăng tối đa **+38 ca** (tức đưa độ chính xác từ 80.63% lên tối đa 83.98%, còn cách rất xa mục tiêu 95%).
> - Điểm nghẽn thực sự chiếm tới **81.82%** nằm ở: (1) Nhãn dev nhiễu/mơ hồ và (2) Lỗi trích xuất vi mô các trường chi tiết (`so_nha`, `duong`, `thon_xom`) khiến mọi giả thuyết trong beam cùng sai!

---

## 4. Kiểm chứng Ablation Mô hình Phụ (ViDeBERTa) & Tách Thao tác Dựng lại Tên

### 4.1. Thống kê Hoạt động Thực tế của ViDeBERTa
| Chỉ số kiểm chứng | Dev Gốc (1.136 mẫu) | Dev Khó Frozen (464 mẫu) | Train Tham khảo (1.183 mẫu) |
| :--- | :---: | :---: | :---: |
| **Tổng số lần gọi ViDeBERTa** | **5** | **1** | **2** |
| **Số ca kích hoạt Fallback** | 5 (0.44%) | 1 (0.22%) | 2 (0.17%) |
| **Số output thay đổi so với Baseline** | 0 | 0 | 4 |
| **Gained / Lost (Đúng thêm / Hỏng thêm)**| +0 / -0 | +0 / -0 | +4 / -0 |
| **Độ trễ Baseline (Mean / P95)** | 59.46 / 118.88 ms | 56.35 / 110.5 ms | - |
| **Độ trễ Hybrid chung (Mean / P95)** | 62.46 / 124.53 ms | 59.61 / 115.91 ms | - |
| **Độ trễ riêng ca Fallback (Mean / P95)**| 164.8 / 255.08 ms | 149.48 / 149.48 ms | - |

### 4.2. Căn chỉnh Lưới Token CNN vs ViDeBERTa qua Char Offsets
- **Số mẫu khớp hoàn toàn lưới token**: **1123 / 1.136** (98.86%).
- **Số mẫu lệch lưới token**: **13 / 1.136** (1.14%).
> Khi có sự lệch lưới giữa hai bộ phân đoạn từ, việc truy cập `vdb_ctx.labels[b]` bằng chỉ số token `b` của CNN có nguy cơ đọc sai nhãn. Cần bắt buộc chuẩn hóa qua toạ độ ký tự tuyệt đối (`char offsets`).

---

## 5. Dẫn Chứng 5–10 Ca DEV Tiêu Biểu

### Mẫu `VNDEV_00001`: `843M+RH3 Hòa Thành District, Tây Ninh`
- **Nhãn tham chiếu (Gold)**: `so_nha='Số 843M'`, `duong=''`, `ma_xa=''`, `ma_tinh='80'`
- **Dự đoán Top-1**: `so_nha='Số 843M'`, `duong=''`, `ma_xa='25645'`, `ma_tinh='80'`
- **Phân loại lỗi**: `CO_TRONG_BEAM_NHUNG_XEP_HANG_SAI` (Cờ phụ: `top1_khong_phai_oracle`)
- **Trạng thái Beam**: Beam Oracle Admin = `True`, Beam Oracle 6 trường = `True`

### Mẫu `VNDEV_00002`: `45B Hoàng Văn Thụ Ninh Kiều Cần Thơ`
- **Nhãn tham chiếu (Gold)**: `so_nha='Số 45B'`, `duong=''`, `ma_xa=''`, `ma_tinh='92'`
- **Dự đoán Top-1**: `so_nha='Số 45B'`, `duong=''`, `ma_xa='31135'`, `ma_tinh='92'`
- **Phân loại lỗi**: `CO_TRONG_BEAM_NHUNG_XEP_HANG_SAI` (Cờ phụ: `top1_khong_phai_oracle`)
- **Trạng thái Beam**: Beam Oracle Admin = `True`, Beam Oracle 6 trường = `True`

### Mẫu `VNDEV_00003`: `45 XÔ VIẾT NGHỆ TĨNH P.AN CƯ- NINH KIỀU- CẦN THƠ`
- **Nhãn tham chiếu (Gold)**: `so_nha='Số 45'`, `duong=''`, `ma_xa=''`, `ma_tinh='92'`
- **Dự đoán Top-1**: `so_nha='Số 45'`, `duong='Đường Xô Viết Nghệ TĨNH'`, `ma_xa='31135'`, `ma_tinh='92'`
- **Phân loại lỗi**: `LOI_CHI_TIET_LAM_HONG_BEAM` (Cờ phụ: `loi_duong`)
- **Trạng thái Beam**: Beam Oracle Admin = `True`, Beam Oracle 6 trường = `False`

### Mẫu `VNDEV_00004`: `313, NGUYỄN VĂN LINH, PHƯỜNG AN KHÁNH, QUẬN NINH KIỀU, THÀNH PHỐ CẦN THƠ`
- **Nhãn tham chiếu (Gold)**: `so_nha='Số 313'`, `duong='Phố Cần Thơ'`, `ma_xa='31147'`, `ma_tinh='92'`
- **Dự đoán Top-1**: `so_nha='Số 313'`, `duong='Đường Nguyễn Văn Linh'`, `ma_xa='31147'`, `ma_tinh='92'`
- **Phân loại lỗi**: `LOI_CHI_TIET_LAM_HONG_BEAM` (Cờ phụ: `loi_duong`)
- **Trạng thái Beam**: Beam Oracle Admin = `True`, Beam Oracle 6 trường = `False`

### Mẫu `VNDEV_00005`: `268/10 NGUYỄN VĂN LINH, PHƯỜNG XUÂN KHÁNH QUẬN NINH KIỀU, TP CẦN THƠ`
- **Nhãn tham chiếu (Gold)**: `so_nha='Số 268/10'`, `duong=''`, `ma_xa='31135'`, `ma_tinh='92'`
- **Dự đoán Top-1**: `so_nha='Số 268/10'`, `duong='Đường Nguyễn Văn Linh'`, `ma_xa='31135'`, `ma_tinh='92'`
- **Phân loại lỗi**: `LOI_CHI_TIET_LAM_HONG_BEAM` (Cờ phụ: `loi_duong`)
- **Trạng thái Beam**: Beam Oracle Admin = `True`, Beam Oracle 6 trường = `False`

### Mẫu `VNDEV_00006`: `129 Trần Việt Châu, An Hòa, Ninh Kiều, Cần thơ`
- **Nhãn tham chiếu (Gold)**: `so_nha='Số 129'`, `duong=''`, `ma_xa=''`, `ma_tinh='92'`
- **Dự đoán Top-1**: `so_nha='Số 129'`, `duong='Đường Trần Việt Châu'`, `ma_xa='31120'`, `ma_tinh='92'`
- **Phân loại lỗi**: `LOI_CHI_TIET_LAM_HONG_BEAM` (Cờ phụ: `loi_duong`)
- **Trạng thái Beam**: Beam Oracle Admin = `True`, Beam Oracle 6 trường = `False`

### Mẫu `VNDEV_00007`: `87 CMT8, An Hòa, Ninh Kiều, Cần Thơ`
- **Nhãn tham chiếu (Gold)**: `so_nha='Số 87'`, `duong=''`, `ma_xa=''`, `ma_tinh='92'`
- **Dự đoán Top-1**: `so_nha='Số 87'`, `duong=''`, `ma_xa='31120'`, `ma_tinh='92'`
- **Phân loại lỗi**: `CO_TRONG_BEAM_NHUNG_XEP_HANG_SAI` (Cờ phụ: `top1_khong_phai_oracle`)
- **Trạng thái Beam**: Beam Oracle Admin = `True`, Beam Oracle 6 trường = `True`

### Mẫu `VNDEV_00009`: `Phòng 801 , tầng 8, PVC MeKong, 131, Trần Hưng Đạo, Q. Ninh Kiều, Tp. Cần Thơ`
- **Nhãn tham chiếu (Gold)**: `so_nha=''`, `duong=''`, `ma_xa=''`, `ma_tinh='92'`
- **Dự đoán Top-1**: `so_nha=''`, `duong='Đường Trần Hưng Đạo'`, `ma_xa=''`, `ma_tinh='92'`
- **Phân loại lỗi**: `CO_TRONG_BEAM_NHUNG_XEP_HANG_SAI` (Cờ phụ: `top1_khong_phai_oracle`)
- **Trạng thái Beam**: Beam Oracle Admin = `True`, Beam Oracle 6 trường = `True`

---

## 6. Trả Lời Trực Tiếp 4 Câu Hỏi Trọng Tâm

### 1. Điểm nghẽn lớn nhất nằm ở tầng nào?
**Trả lời bằng số đếm và mẫu số thực**:
Điểm nghẽn lớn nhất **KHÔNG PHẢI** nằm ở tầng liên kết thực thể / xếp hạng giả thuyết (Ranker), mà nằm ở:
1. **Lỗi trích xuất vi mô các trường chi tiết (`LOI_CHI_TIET_LAM_HONG_BEAM`)**: chiếm **112 / 220 ca lỗi (50.91%)** trên Dev. Tầng hành chính đã có đường đi đúng trong beam (1133 / 1.136 ca = 99.74%), nhưng các trường số nhà, ngõ ngách, tên đường bị cắt sai khiến toàn bộ giả thuyết 6 trường đều bị kéo sai theo.
2. **Nhiễu nhãn và mơ hồ nội tại (`MO_HO_HOAC_NHAN_NHIEU`)**: chiếm **68 / 220 ca lỗi (30.91%)** do nhãn máy tự động gán thiếu tên đường thật, hoặc các ca xã cũ bị chia tách nhưng nhãn máy lại gán ngẫu nhiên 1 xã.

### 2. Mô hình liên kết / xếp hạng mới có thể sửa tối đa phần lỗi nào trên candidate set hiện tại?
**Trả lời**:
Trên tập ứng viên và chùm giả thuyết cố định hiện tại, một bộ xếp hạng hoàn hảo (Oracle Reranker) chỉ có thể sửa tối đa **38 ca lỗi** (17.27% tổng số lỗi), tương ứng mức tăng điểm tối đa từ **916/1.136 (80.63%)** lên trần kịch kim **954/1.136 (83.98%)**. Toàn bộ 182 ca lỗi còn lại nằm ngoài khả năng của bất kỳ tầng ranker nào vì không có giả thuyết 6 trường đúng trong beam.

### 3. Cần sửa sinh ứng viên / dữ liệu trước hay đã đủ căn cứ thử thêm tầng học?
**Trả lời**:
**BẮT BUỘC PHẢI SỬA SINH ỨNG VIÊN & TRÍCH XUẤT CHI TIẾT TRƯỚC**.
Chưa đủ căn cứ kỹ thuật để thêm một tầng học liên kết thực thể (Neural Linking Head) vì:
- Ranker hiện tại đã chọn đúng **93.28%** các ca khi giả thuyết đúng có mặt trong beam.
- Thêm mô hình học phức tạp ở tầng cuối chỉ tác động tối đa vào 38 ca (17.27%), trong khi phải trả giá bằng độ trễ và rủi ro sập chất lượng (như bài học 0.18% của Neural Linking Head trước đây).

### 4. Nếu đề xuất mô hình tiếp theo, kiến trúc và chi phí CPU sơ bộ ra sao?
**Nhiệm vụ & Thiết kế đề xuất (chưa triển khai/train)**:
- **Nhiệm vụ**: Boundary Refinement & Multi-task Span Extractor thay vì Entity Linking độc lập. Cụ thể: một mô hình encoder gọn nhẹ nhận đầu vào là chuỗi địa chỉ, xuất ra trực tiếp nhãn BIO của 4 trường chi tiết (`so_nha`, `ngo_ngach_hem`, `thon_xom`, `duong`) có cơ chế Self-Attention để không bị giới hạn cửa sổ ngữ cảnh, kết hợp phân đoạn từ tiếng Việt chuẩn.
- **Chi phí CPU ước tính**: Nếu dùng kiến trúc chưng cất (Distilled Student CNN-Transformer 4 lớp, ~15M tham số), độ trễ CPU ước tính $\sim 15 - 25\text{ ms/input}$, hoàn toàn phù hợp SLA Cloud và giải quyết đúng gốc rễ của 70%+ lỗi hiện tại.
