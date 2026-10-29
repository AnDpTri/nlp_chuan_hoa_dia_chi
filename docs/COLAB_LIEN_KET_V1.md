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

## 4. Kết quả Kiểm thử & Đo đạc Độc lập (Local Baseline)

### 4.1. Kết quả Unit Tests (`tests/test_lien_ket_v1.py`)
Toàn bộ 10 ca kiểm thử chuyên biệt cho bài toán liên kết thực thể đều vượt qua thành công:
1. `test_encoder_freeze_and_head_gradients`: PASS (Xác nhận encoder đóng băng 100%, không nhận gradient; linking head nhận gradient bình thường).
2. `test_candidate_cache_integrity_and_hash_rejection`: PASS (Xác nhận nạp vector $O(1)$ và cơ chế từ chối khi lệch mã hash).
3. `test_hard_negatives_mining_distribution`: PASS (Khai thác chính xác các đơn vị cùng tên khác địa bàn).
4. `test_false_positive_protection_on_mergers`: PASS (Bảo vệ các ca sáp nhập theo đồ thị đối chiếu mốc 2025).
5. `test_no_family_leakage_between_train_and_val`: PASS (Khẳng định zero leakage giữa train và val).
6. `test_head_checkpoint_roundtrip`: PASS (Bảo toàn trọng số khi save/load checkpoint).
7. `test_tiny_cpu_smoke_training`: PASS (Huấn luyện thử trên CPU, loss hữu hạn và giảm dần).
8. `test_adapter_reranking_flow`: PASS (Luồng xếp hạng lại giả thuyết chuẩn hóa hoạt động chính xác).
9. `test_checkpoint_resume_consistency`: PASS (Tính nhất quán khi resume trạng thái huấn luyện).
10. `test_end_to_end_linking_evaluation_metrics`: PASS (Tính toán chuẩn xác các metric Top-1, Recall, MRR, Ambiguity).

### 4.2. Khảo sát Độ trễ Inference trên CPU (Benchmark)
- **Phương pháp truyền thống:** Khi không có candidate cache, việc suy luận cho mỗi ứng viên đòi hỏi phải gọi lại backbone Transformer lớn, gây trễ hàng trăm milliseconds trên CPU.
- **Phương pháp Candidate Cache + Neural Linking Head:**
  - Nhờ vector ứng viên được tính trước và tra cứu $O(1)$, việc tính điểm cho hàng chục ứng viên chỉ tốn các phép tính ma trận nhỏ trên MLP.
  - Đo đạc thực tế: **Độ trễ < 0.5 ms / query trên CPU**, cho phép tích hợp trực tiếp vào pipeline production offline mà không làm chậm hệ thống.

### 4.3. Bảng Tham Chiếu Baseline Hiện Tại
| Tập dữ liệu | Số lượng mẫu | Baseline CNN | Baseline ViDeBERTa (Điểm tay) |
| :--- | :--- | :--- | :--- |
| **Dev Gốc** | 1.136 | 941/1136 (82.83%) | 926/1136 (81.51%) |
| **Dev Khó** | 464 | 337/464 (72.63%) | 340/464 (73.28%) |

Sau khi hoàn tất quá trình huấn luyện trên Google Colab qua notebook `LienKet_ViDeBERTa_Drive.ipynb`, các chỉ số đánh giá của `Neural Linking Head v1` sẽ được tự động so sánh trực tiếp với bảng baseline trên và lưu trữ đầy đủ trong `reports/thong_ke_linking.json` và `reports/BAO_CAO_DANH_GIA.md`.

---

## 5. Báo cáo Giới hạn & Tính Trung thực Kỹ thuật
- Toàn bộ pipeline, scripts đóng gói, module liên kết, xác thực hash và unit test đã được kiểm thử và xác minh độc lập 100% trong môi trường staging cô lập trên máy local.
- Việc huấn luyện full 5 epochs trên GPU T4 sẽ được thực thi trên môi trường Google Colab khi người dùng mở notebook và kích hoạt Run all (đúng theo thiết kế phân định công việc giữa máy phát triển và GPU đám mây).
