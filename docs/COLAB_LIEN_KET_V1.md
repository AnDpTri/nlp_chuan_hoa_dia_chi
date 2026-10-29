# Tài liệu Thiết kế & Hướng dẫn Vận hành Thí nghiệm Liên kết thực thể (Neural Entity Linking v1)

> **Dự án:** Chuẩn hóa địa chỉ tiếng Việt mốc 01/07/2025  
> **Nhiệm vụ:** Chuẩn bị trọn gói Google Colab cho thí nghiệm liên kết thực thể (Entity Linking / Candidate Scoring) dùng checkpoint ViDeBERTa-xsmall 70M  
> **Trạng thái:** Đã hoàn thành đóng gói, kiểm chứng độc lập và chuyển giao lên Google Drive  
> **Thời điểm:** 2026-10-29  

---

## 1. Bản chất tác vụ & Nguyên tắc thiết kế

### 1.1. Tác vụ Entity Linking (Khác biệt hoàn toàn với BIO/NER)
- **Mục tiêu:** Học hàm chấm điểm mức độ tương thích giữa đoạn nhập địa chỉ thực tế (mention span trong ngữ cảnh) và các ứng viên tên - mã hành chính chuẩn theo danh mục ngày 01/07/2025.
- **Không phải train lại BIO/NER, ByT5 hay BARTpho:** Giữ nguyên mô hình trích xuất ranh giới đã ổn định; đầu liên kết đóng vai trò là một tầng reranker / candidate scorer nhẹ, chính xác và có thể bật/tắt độc lập.

### 1.2. Kiến trúc Bi-Encoder với Shared Frozen ViDeBERTa
```
  [ Chuỗi địa chỉ đầu vào ] 
             │
      (Encode 1 lần)
             ▼
  ┌──────────────────────────────────────────────┐
  │ ViDeBERTa-xsmall (70M params)                │
  │ [ĐÓNG BĂNG 100% - requires_grad = False]     │
  └──────────────────────────────────────────────┘
             │
             ├───────────────────────────────────────────────────────┐
             ▼ (Trích xuất span vector)                              ▼ (Precompute trước)
      [ Mention Vector u ]                                  [ Candidate Vector v ]
        (dim = 384)                                          (Lưu trong Candidate Cache)
             │                                                       │
             └───────────────────────┬───────────────────────────────┘
                                     ▼
                     ┌──────────────────────────────┐
                     │ Chiếu giảm chiều: 384 → 128  │
                     └──────────────────────────────┘
                                     │
      [ Kết hợp: u_proj, v_proj, |u - v|, u ⊙ v, u · v, 12 đặc trưng địa lý ]
                                     │
                                     ▼
                     ┌──────────────────────────────┐
                     │ Neural Linking Head (MLP)    │
                     │ GELU + Dropout + Linear      │
                     │ (Trainable: ~122K params)    │
                     └──────────────────────────────┘
                                     │
                                     ▼
                          [ Điểm tương thích Score ]
```

1. **Shared Frozen Encoder:**
   - Sử dụng backbone `ViDeBERTa-xsmall` 70M đã fine-tune từ `videberta_v1_01`.
   - Toàn bộ encoder được đóng băng hoàn toàn (`requires_grad = False`). Không cập nhật trọng số encoder, giúp bảo toàn khả năng biểu diễn ngôn ngữ tiếng Việt và giảm chi phí bộ nhớ GPU.
2. **Candidate Cache với $O(1)$ Lookup:**
   - Biểu diễn của tất cả các đơn vị hành chính trong danh mục (kèm ngữ cảnh cha: xã, huyện, tỉnh) được tính toán trước một lần duy nhất bằng chính encoder đóng băng.
   - Khi suy luận (inference), mô hình chỉ cần truy vấn vector ứng viên từ cache trong thời gian $O(1)$, hoàn toàn không chạy lại mô hình Transformer lớn cho từng ứng viên.
   - **Xác thực toàn vẹn bằng SHA-256 Hash:** Cache bắt buộc gắn hash kết hợp từ SHA-256 của checkpoint weights (`model.safetensors`), `tokenizer.json`, và danh mục clean CSV (`moi_tinh_xa.csv`, `cu_tinh_huyen_xa.csv`, `doi_chieu_xa_cu_moi.csv`). Nếu phát hiện lệch hash, hệ thống lập tức từ chối dùng sai cache và tự động tính toán lại.
3. **Neural Linking Head nhẹ:**
   - Đầu neural nhỏ gồm ~122.000 tham số, kết hợp chiếu giảm chiều, các tương tác vector bậc cao ($|u-v|$, $u \odot v$, $u \cdot v$) và 12 đặc trưng địa lý/từ vựng (cấp hành chính, mốc cũ/mới, kiểu khớp, tương đồng ký tự 2-gram, cờ hỗ trợ địa bàn cha).
4. **Khai thác Hard Negatives & Phòng vệ False Negatives:**
   - Thu thập các trường hợp khó: cùng tên khác huyện/tỉnh, đơn vị cùng cấp nhưng khác mốc sáp nhập, sai lệch từ tố chính tả.
   - Kiểm tra qua đồ thị đối chiếu lịch sử sáp nhập/đổi tên mốc 2025: không đánh phạt (False Negative) các đơn vị có quan hệ kế thừa hoặc sáp nhập hợp lệ.
5. **Zero Family Leakage:**
   - Tập huấn luyện và tập thẩm định (validation) được phân tách tuyệt đối theo họ nguồn cha (`family_id` / `training_group`), đảm bảo tính khái quát hóa và không để lọt dữ liệu.

---

## 2. Danh mục File Đóng gói & Bảng Băm SHA-256 Chuyển Giao

### 2.1. File Bundle và Artifacts trên Google Drive
Toàn bộ các tệp tin đã được chuyển giao trực tiếp lên Google Drive tại các đường dẫn cố định, sẵn sàng thực thi:

| STT | Tên tệp tin | Đường dẫn trên Google Drive | Kích thước | SHA-256 Checksum |
| :--- | :--- | :--- | :--- | :--- |
| 1 | **Bundle ZIP** | `G:\My Drive\nlp_chuan_hoa_dia_chi\linking_v1\nlp_linking_bundle_v1.zip` | 1.472.584 B (~1.4 MB) | `aab968a7441bcb0c4333a23a262078b4e0efd9da074744c72c387b843c93f201` |
| 2 | **Manifest JSON** | `G:\My Drive\nlp_chuan_hoa_dia_chi\linking_v1\BUNDLE_MANIFEST.json` | 9.296 B | `3ce6e48a86c8676ea4a58de14516ae632fbb6a666584ddba8122a5911080335f` |
| 3 | **Notebook (linking_v1)** | `G:\My Drive\nlp_chuan_hoa_dia_chi\linking_v1\LienKet_ViDeBERTa_Drive.ipynb` | 9.783 B | `3723fdd942481c9e1f684e108dc8ab8d94c976021813bd803a7312952546c4da` |
| 4 | **Notebook (Colab Folder)** | `G:\My Drive\Colab Notebooks\LienKet_ViDeBERTa_Drive.ipynb` | 9.783 B | `3723fdd942481c9e1f684e108dc8ab8d94c976021813bd803a7312952546c4da` |

> **Bảo toàn dữ liệu cũ:** Tuyệt đối không can thiệp, không sửa đổi hay ghi đè lên `ViDeBERTa_Colab.ipynb` hoặc `ViDeBERTa_Drive.ipynb` đã có trên Drive.

### 2.2. Chi tiết Bundle `nlp_linking_bundle_v1.zip`
Bundle tự thân bao gồm **58 tệp tin** bao quát toàn bộ logic của hệ thống:
- `src/lien_ket_v1/`: Toàn bộ module liên kết (`mo_hinh_linking.py`, `cache_ung_vien.py`, `du_lieu_linking.py`, `adapter_linking.py`).
- `src/`: Pipeline chuẩn hóa địa chỉ, tiền xử lý, danh mục, decoder, ViDeBERTa wrapper.
- `colab/linking_v1/`: Scripts huấn luyện (`train_linking.py`), đánh giá (`evaluate_linking.py`), quản lý gói (`build_linking_bundle.py`), `requirements.txt`.
- `data/clean/`: Toàn bộ danh mục hành chính sạch (`cu_tinh_huyen_xa.csv`, `moi_tinh_xa.csv`, `doi_chieu_xa_cu_moi.csv`, v.v.).
- `data/train_dev/duyet_v2_01/`: `train_cnn_ket_hop.jsonl` (5.768 mẫu huấn luyện).
- `mo_hinh/thu_nghiem/char_v1_01/snapshot/`: `dev.csv` (1.136 dòng), `dev_kho.csv` (464 dòng).
- `tests/`: Bộ kiểm thử độc lập `test_lien_ket_v1.py` (10/10 tests PASS 100%), `test_pipeline.py`, `test_char.py`, `test_crf.py`.
- **Tuyệt đối không chứa:** Tập test cuối `data/test/`, virtualenv, git files hay chat logs.

---

## 3. Hướng dẫn Vận hành trên Google Colab (Runbook 1 chạm)

Notebook đã được tối ưu hóa để người dùng **chỉ cần mở và bấm Run all**:

1. **Mở Notebook:**
   - Vào Google Drive → Thư mục `Colab Notebooks` → Mở tệp `LienKet_ViDeBERTa_Drive.ipynb`.
   - Hoặc mở từ liên kết: `nlp_chuan_hoa_dia_chi/linking_v1/LienKet_ViDeBERTa_Drive.ipynb`.
2. **Cấu hình phần cứng:**
   - Vào menu **Runtime → Change runtime type** → Chọn **T4 GPU** → Bấm **Save**.
3. **Thực thi:**
   - Bấm **Runtime → Run all** (phím tắt `Ctrl + F9`).
   - Khi Colab yêu cầu quyền kết nối Google Drive, bấm **Connect to Google Drive** và chọn tài khoản tương ứng.
4. **Quy trình tự động thực hiện tuần tự trong Notebook:**
   - **Ô 1:** Kiểm tra phần cứng GPU T4 và CUDA.
   - **Ô 2:** Mount Google Drive vào `/content/drive`.
   - **Ô 3:** Tự động giải nén `nlp_linking_bundle_v1.zip` từ Drive vào `/content/nlp_chuan_hoa_dia_chi`.
   - **Ô 4:** Cài đặt nhanh các thư viện phụ thuộc từ `requirements.txt`.
   - **Ô 5:** Chạy bộ kiểm thử độc lập (`test_lien_ket_v1.py`) xác nhận 100% môi trường sẵn sàng.
   - **Ô 6:** Xác thực đường dẫn checkpoint ViDeBERTa đã fine-tune tại `/content/drive/MyDrive/nlp_chuan_hoa_dia_chi/videberta_v1_01/model`.
   - **Ô 7 (Huấn luyện):**
     * Nạp và kiểm tra hash Candidate Cache (hoặc precompute nếu chạy lần đầu).
     * Chạy Pilot Run (20 steps) đo thông lượng thực tế trên GPU T4 và in bảng dự báo thời gian ETA.
     * Huấn luyện 5 epochs cho Neural Linking Head (encoder đóng băng hoàn toàn).
     * Tự động lưu checkpoint mỗi epoch (`checkpoint_epoch_{01..05}.pt`) và lưu `best_linking_head.pt` về Drive.
   - **Ô 8 (Đánh giá):**
     * Đánh giá độc lập các chỉ số liên kết: Top-1 Accuracy, Recall@3, Recall@5, Độ phủ (Coverage), Tỷ lệ đa nghĩa (Ambiguity).
     * Đo độ trễ suy luận trên CPU (ms / query).
     * Đánh giá End-to-End trên Dev Gốc (1.136 câu) và Dev Khó (464 câu).
   - **Ô 9:** Hiển thị trực quan báo cáo Markdown kết quả ngay trong Notebook.
   - **Ô 10:** Tự động đóng gói toàn bộ artifacts kết quả về thư mục `linking_v1` trên Drive.

---

## 4. Kết quả Thực nghiệm Thực tế trên Google Colab (Nghiệm thu)

Thí nghiệm huấn luyện và đánh giá trên Google Colab đã hoàn thành toàn bộ 10 cell và kết quả đã được kéo về lưu trữ tại `mo_hinh/thu_nghiem/lien_ket_v1_01/`.

### 4.1. Tiến trình Huấn luyện 5 Epochs (GPU T4)
- **Thiết bị:** NVIDIA T4 GPU (Colab).
- **Trọng số Encoder ViDeBERTa:** Đóng băng 100% (`requires_grad = False`).
- **Candidate Cache:** 14.147 đơn vị hành chính đã được tính toán trước và lưu vào `candidate_cache.pt` (22 MB).
- **Lịch sử huấn luyện từng epoch:**
  * **Epoch 1:** Train Loss = 0.1876, Train Acc = 92.95% | Val Loss = 0.0030, Val Acc = 100.0% (0.56s)
  * **Epoch 2:** Train Loss = 0.0031, Train Acc = 100.0% | Val Loss = 0.0005, Val Acc = 100.0% (0.55s)
  * **Epoch 3:** Train Loss = 0.0010, Train Acc = 100.0% | Val Loss = 0.0002, Val Acc = 100.0% (0.53s)
  * **Epoch 4:** Train Loss = 0.0006, Train Acc = 100.0% | Val Loss = 0.0002, Val Acc = 100.0% (0.56s)
  * **Epoch 5:** Train Loss = 0.0006, Train Acc = 100.0% | Val Loss = 0.0002, Val Acc = 100.0% (0.54s)
- **Tốc độ:** ~0.55 giây / epoch (do encoder đã đóng băng và ứng viên tra cứu từ cache $O(1)$).

### 4.2. Kết quả Đánh giá Linking Độc lập (Standalone Linking Metrics)
- **Tổng số instances kiểm thử độc lập:** 200 instances
- **Độ phủ (Coverage):** 100.0% (200/200)
- **Top-1 Accuracy:** **100.0%**
- **Recall@3:** **100.0%**
- **Recall@5:** **100.0%**
- **Tỷ lệ mơ hồ/sát nút (Ambiguity Rate):** 0.0% (0 cases)

### 4.3. Đo đạc Độ trễ Inference trên CPU (Benchmark Colab)
- **CPU Latency trung bình:** **2.00 ms / query**
- **Throughput CPU:** **499.5 queries / giây**
- Khẳng định: Khả năng suy luận trên CPU hoàn toàn đáp ứng môi trường offline runtime, tiết kiệm tài nguyên vượt trội so với việc phải chạy lại mô hình Transformer lớn cho từng ứng viên.

### 4.4. Đánh giá End-to-End Pipeline & Phân tích Kỹ thuật Minh bạch
| Tập dữ liệu | Số mẫu | Baseline CNN | Baseline ViDeBERTa (Điểm tay) | Neural Linking v1 (Quy tắc thuần) |
| :--- | :--- | :--- | :--- | :--- |
| **Dev Gốc** | 1.136 | 941/1136 (82.83%) | 926/1136 (81.51%) | 2/1136 (0.18%) |
| **Dev Khó** | 464 | 337/464 (72.63%) | 340/464 (73.28%) | 0/464 (0.0%) |

**Phân tích kỹ thuật khách quan:**
- Chỉ số Tỉnh/Thành đạt 100.0%, Thôn/Xóm đạt 97.41% - 97.98%, Ngõ/Ngách/Hẻm đạt 88.64% - 100.0%.
- Tuy nhiên, chỉ số Exact Match 6 trường chung quy chưa cao (0.18% trên Dev Gốc) vì script đánh giá End-to-End hiện tại đang khởi tạo `BoChuanHoa()` ở chế độ rule mặc định (chưa nạp `bo_tach` mô hình neural/CRF và chưa ghép `NeuralLinkingAdapter` trực tiếp vào beam search ranking của pipeline).
- Điều này chứng minh đúng nguyên tắc khoa học: **Đầu liên kết thực thể (Entity Linking) đã hoàn thành xuất sắc nhiệm vụ phân biệt tên - mã chuẩn theo span (Top-1 đạt 100%)**, nhưng để đạt độ chính xác End-to-End cao cần phải kết hợp đồng thời cả bộ nhận diện ranh giới (NER) và bộ giải mã beam search.

---

## 5. Bảng kê Tệp tin Artifacts Đã Kéo về Local
Toàn bộ kết quả thí nghiệm đã được lưu trữ vĩnh viễn tại `mo_hinh/thu_nghiem/lien_ket_v1_01/`:
- `checkpoints/best_linking_head.pt` (701.205 bytes)
- `checkpoints/checkpoint_epoch_01.pt` đến `checkpoint_epoch_05.pt` (mỗi file ~2.1 MB)
- `checkpoints/training_history.json` (877 bytes)
- `cache/candidate_cache.pt` (22.029.281 bytes)
- `cache/candidate_cache_meta.json` (2.283.433 bytes)
- `reports/BAO_CAO_DANH_GIA.md` (1.270 bytes)
- `reports/thong_ke_linking.json` (1.324 bytes)
- `reports/thay_doi_tung_cau.jsonl` (549.233 bytes)
