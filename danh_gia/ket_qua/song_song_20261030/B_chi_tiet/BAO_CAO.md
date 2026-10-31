# BÁO CÁO KỸ THUẬT NHIỆM VỤ B: TÁCH SAI SPAN / FORMAT / TÊN CHUẨN / NHÃN NGHI VẤN

- **Người thực hiện:** Phiên B (Độc quyền vùng ghi `danh_gia/ket_qua/song_song_20261030/B_chi_tiet/`).
- **Thời điểm đo:** 30/10/2026.
- **Môi trường & Ràng buộc:** CPU 1 thread (`torch.set_num_threads(1)`), Python 3.12, PyTorch 2.15.0+cpu.
- **Toàn vẹn Baseline:** Đã kiểm tra 100% SHA-256 của toàn bộ 37 files trong `BASELINE_MANIFEST.json` trước và sau khi chạy; không có bất kỳ file nào bị thay đổi. Tuyệt đối không đọc/chạy/mở `data/test` hay `dia_chi_test.csv`.

---

## 1. TÓM TẮT ĐIỀU HÀNH & TRẢ LỜI CÁC CÂU HỎI CỐT LÕI

### 1.1. Năng lực trích xuất (Extraction) có thực sự là bottleneck của hệ thống?
**TRẢ LỜI DỨT KHOÁT: KHÔNG.**
- Trên tập **Dev gốc (1.026 mẫu có nhãn span)**: CNN v2 đạt **Overall Exact Span F1 = 98.58%**, **Character-level Offset F1 = 99.01%** trên 4 trường chi tiết (`so_nha`, `ngo_ngach_hem`, `duong`, `thon_xom`).
  - `so_nha`: Exact F1 = 99.04%, Char F1 = 98.96% (Support 883, TP 877).
  - `ngo_ngach_hem`: Exact F1 = 100.0%, Char F1 = 100.0% (Support 96, TP 96).
  - `duong`: Exact F1 = 98.33%, Char F1 = 99.11% (Support 924, TP 915).
  - `thon_xom`: Exact F1 = 81.08%, Char F1 = 86.38% (Support 18, TP 15).
- Trên tập **Dev Khó (464 mẫu)**: CNN v2 đạt **Overall Exact Span F1 = 98.76%**, **Character-level Offset F1 = 99.24%**.
  - `so_nha`: Exact F1 = 99.68%, Char F1 = 99.91% (Support 464, TP 462).
  - `duong`: Exact F1 = 97.91%, Char F1 = 98.96% (Support 452, TP 445).
  - `thon_xom`: Exact F1 = 96.00%, Char F1 = 97.30% (Support 12, TP 12).
  - `ngo_ngach_hem`: Support = 0 mẫu -> Báo cáo chính xác **N/A** (không ép điểm giả tạo).
- **Phân rã nhóm 112 ca "lỗi chi tiết làm hỏng beam"**: Thực tế **chỉ có 18 / 112 ca (16.1%)** là do CNN v2 cắt sai span thô. Có tới **58 / 112 ca (51.8%)** là do **thiếu từ điển đường (OOV)** và **19 ca (17.0%)** là do **lỗi xếp hạng canonical / beam selection**.
- **Kết luận:** Tuyên bố trước đây cho rằng 112 ca đều là "lỗi trích xuất vi mô làm hỏng beam" là **hoàn toàn sai lệch**. Bottleneck thực sự nằm ở **độ phủ từ điển tên đường (Dictionary Coverage)** và **cơ chế liên kết thực thể (Canonicalization / Disambiguation)**, không phải ở tầng trích xuất span thô.

### 1.2. Đợt bổ sung dữ liệu huấn luyện tiếp theo nên nhắm vào role và biến thể nào?
Dựa trên thống kê số đếm thực tế của 18 ca sai span thô và các ca lệch trên tập khó:
1. **Ưu tiên 1 (Cực kỳ cấp thiết) - Thôn/Xóm và Biến thể cụm dân cư nông thôn**:
   - Vai trò `thon_xom` có F1 thấp nhất trên Dev gốc (81.08%) do dữ liệu huấn luyện rất nghèo mẫu (support chỉ có 18 mẫu). Cần bổ sung các định dạng thôn, xóm, ấp, tổ dân phố, bản, buôn.
2. **Ưu tiên 2 - Phân biệt từ đa nghĩa giữa tên riêng và danh xưng hành chính**:
   - Điển hình: Các tên đường chứa từ trùng với cấp hành chính như "Xô Viết Nghệ **TĨNH**", "Phố **Cần Thơ**", "Đường **Hà Nội**", "Đường **Bình Dương**". CNN v2 bị nhầm từ "TĨNH" hoặc "CẦN THƠ" thành đơn vị hành chính và cắt đứt tên đường (như ca VNDEV_00003). Cần sinh thêm dữ liệu chứa các tên đường đặc thù này.
3. **Ưu tiên 3 - Xử lý số nhà phức hợp / kiệt hẻm lồng ghép**:
   - Các dạng số nhà phức tạp có dấu xẹt dài như `99/18/5/36`, số lô `LK 16-19`, hoặc số nhà đi kèm số tầng/phòng.

### 1.3. Đã đủ căn cứ để chọn thay thế extractor (ViDeBERTa vs CNN v2) chưa?
- **Chưa đủ căn cứ.**
- Extractor CNN v2 đã đạt F1 > 98.5% trên cả dev gốc lẫn dev khó với độ trễ cực thấp (~4.66ms/câu).
- Thí nghiệm ghép ViDeBERTa cũ chỉ gọi fallback 5 ca dev gốc và 1 ca dev khó nhưng không làm thay đổi kết quả 6 trường, trong khi độ trễ CPU tăng vọt lên ~255ms.
- Thay thế extractor không giải quyết được vấn đề cốt lõi (51.8% lỗi do thiếu từ điển và 17% do xếp hạng canonical). Chưa có bằng chứng thực nghiệm độc lập nào cho thấy ViDeBERTa vượt trội CNN v2 về mặt thực chất để bù đắp chi phí tài nguyên CPU.

---

## 2. BẢNG SỐ LIỆU ĐỊNH LƯỢNG CHI TIẾT

### 2.1. Độ Phủ Gắn Nhãn (Annotation Coverage)
- **Tập Dev Gốc (`data/train_dev/dev.csv`)**:
  - Tổng số mẫu: 1.136 mẫu.
  - Số mẫu có nhãn span đóng băng (`dev_goc.jsonl`): 1.026 mẫu (**Độ phủ: 90.32%**).
  - Số mẫu KHÔNG có nhãn span: 110 mẫu (**9.68%**). Nhóm này được giữ riêng biệt, support = N/A, không tự ý gán nhãn giả định.
- **Tập Dev Khó (`dev_kho.csv` / `dev_kho.jsonl`)**:
  - Tổng số mẫu: 464 mẫu.
  - Số mẫu có nhãn span: 464 mẫu (**Độ phủ: 100.0%**).

---

### 2.2. Đo Lường Chi Tiết 4 Vai Trò Span (CNN v2 Raw Extraction)

#### Bảng 1: Kết quả trên Dev Gốc (1.026 mẫu có nhãn span)
| Vai trò (Role) | Gold Support | Pred Count | Exact TP | Exact P | Exact R | Exact F1 | Char Gold | Char Pred | Char TP | Char P | Char R | Char F1 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `so_nha` | 883 | 888 | 877 | 0.9876 | 0.9932 | **0.9904** | 3.376 | 3.431 | 3.368 | 0.9816 | 0.9976 | **0.9896** |
| `ngo_ngach_hem` | 96 | 96 | 96 | 1.0000 | 1.0000 | **1.0000** | 686 | 686 | 686 | 1.0000 | 1.0000 | **1.0000** |
| `duong` | 924 | 937 | 915 | 0.9765 | 0.9903 | **0.9833** | 14.315 | 14.417 | 14.238 | 0.9876 | 0.9946 | **0.9911** |
| `thon_xom` | 18 | 19 | 15 | 0.7895 | 0.8333 | **0.8108** | 160 | 141 | 130 | 0.9220 | 0.8125 | **0.8638** |
| **Tổng hợp (Micro)** | **1.921** | **1.940** | **1.903** | **0.9809** | **0.9906** | **0.9858** | **18.537** | **18.675** | **18.422** | **0.9865** | **0.9938** | **0.9901** |

> [!NOTE]
> Nhóm 110 mẫu không có span annotation trên Dev gốc được giữ riêng biệt (support = N/A), không đưa vào bảng tính trên để tránh làm sai lệch mẫu số thật.

#### Bảng 2: Kết quả trên Dev Khó (464 mẫu)
| Vai trò (Role) | Gold Support | Pred Count | Exact TP | Exact P | Exact R | Exact F1 | Char Gold | Char Pred | Char TP | Char P | Char R | Char F1 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `so_nha` | 464 | 463 | 462 | 0.9978 | 0.9957 | **0.9968** | 3.222 | 3.224 | 3.220 | 0.9988 | 0.9994 | **0.9991** |
| `ngo_ngach_hem` | 0 | 0 | 0 | **N/A** | **N/A** | **N/A** | 0 | 0 | 0 | **N/A** | **N/A** | **N/A** |
| `duong` | 452 | 457 | 445 | 0.9737 | 0.9845 | **0.9791** | 7.017 | 6.877 | 6.875 | 0.9997 | 0.9798 | **0.9896** |
| `thon_xom` | 12 | 13 | 12 | 0.9231 | 1.0000 | **0.9600** | 90 | 95 | 90 | 0.9474 | 1.0000 | **0.9730** |
| **Tổng hợp (Micro)** | **928** | **933** | **919** | **0.9850** | **0.9903** | **0.9876** | **10.329** | **10.196** | **10.185** | **0.9989** | **0.9861** | **0.9924** |

> [!IMPORTANT]
> Trên Dev Khó, vai trò `ngo_ngach_hem` có Support = 0. Tuân thủ tuyệt đối quy tắc chuẩn mực thực nghiệm: báo cáo rõ ràng **N/A**, không đưa ra con số 0% hay 100% gây hiểu lầm.

---

### 2.3. Phân Rã Kỹ Thuật Chi Tiết 112 Ca "Lỗi Chi Tiết" và 95 Ca "Lỗi Đường"

Trong báo cáo chẩn đoán cũ, nhóm 112 ca được gắn cờ `LOI_CHI_TIET_LAM_HONG_BEAM` (trong đó có 95 ca cờ `loi_duong`). Đối chiếu độc lập từng ca với nhãn span frozen, từ điển đường `tu_dien_duong_v5.json`, bộ xếp hạng và mã hành chính, chúng tôi phân rã thành 6 tầng nguyên nhân kỹ thuật cụ thể:

#### Bảng 3: Phân rã 112 ca lỗi chi tiết và 95 ca lỗi đường
| Tầng nguyên nhân kỹ thuật | Số ca (trong 112 ca) | Tỷ lệ (%) | Số ca (trong 95 ca đường) | Tỷ lệ (%) | Bản chất kỹ thuật |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Tầng 3: Thiếu từ điển đường (OOV)** | **58** | **51.8%** | **52** | **54.7%** | CNN trích đúng tên đường, nhưng tên đường vắng mặt trong `tu_dien_duong_v5.json` cho tỉnh tương ứng. |
| **Tầng 4: Xếp hạng canonical sai** | **19** | **17.0%** | **13** | **13.7%** | Tên đường có trong từ điển, nhưng ranker/heuristic chọn sai ứng viên hoặc liên kết nhầm xã. |
| **Tầng 1: Sai trích xuất span thô** | **18** | **16.1%** | **13** | **13.7%** | CNN v2 cắt sai ranh giới span (thừa/thiếu ký tự, ngắt nhầm từ đa nghĩa hành chính). |
| **Tầng 2: Lệch bộ định dạng (Formatter)** | **15** | **13.4%** | **15** | **15.8%** | Raw span đúng ngữ nghĩa, nhưng formatter thêm/bớt tiền tố "Đường", "Số" lệch so với ref. |
| **Tầng 6: Chưa xác định** | **2** | **1.8%** | **2** | **2.1%** | Thông tin đầu vào viết tắt dị biệt (`KT - HN`, thôn xã không dấu lạ), chưa đủ bằng chứng. |
| **Tổng cộng** | **112** | **100.0%** | **95** | **100.0%** |  |

---

### 2.4. Đo Lường Tiềm Năng Cải Thiện Độc Lập (Joint Gained Potential Oracles)

Tuân thủ quy tắc **không cộng dồn tỷ lệ chồng lấn**, chúng tôi đo đạc độc lập trần cải thiện (potential ceiling) của từng tầng nếu tầng đó được sửa hoàn hảo:

#### Bảng 4: Tiềm năng độc lập từng tầng
| Phép thử Oracle độc lập | Số ca đúng thêm | Mẫu số đo lường | Tỷ lệ độc lập (%) | Cơ chế kiểm chứng |
| :--- | :---: | :---: | :---: | :--- |
| **Oracle Dictionary Coverage** | **117** | 152 ca lỗi có nhãn span | **76.97%** | Giả định từ điển đường bao phủ 100% các tên đường trích xuất được. |
| **Oracle Ranking Selection** | **67** | 220 ca lỗi dev | **30.45%** | Giả định bộ chọn beam luôn chọn giả thuyết đúng 6 trường đã có sẵn trong beam (`beam_oracle_6`). |
| **Oracle Span Extraction** | **16** | 152 ca lỗi có nhãn span | **10.53%** | Thay thế hoàn toàn CNN v2 bằng Gold Spans đóng băng và chạy lại pipeline `BoChuanHoa`. |
| **Oracle Formatter Normalization**| **6** | 220 ca lỗi dev | **2.73%** | Đồng nhất quy ước tiền tố ("Số", "Đường", casefold, whitespace). |

> [!WARNING]
> Bốn giá trị phần trăm trên **KHÔNG ĐƯỢC CỘNG DỒN** vì có sự giao thoa lớn giữa các tầng (ví dụ: một ca vừa có thể giải quyết bằng từ điển đầy đủ, vừa có thể cần xếp hạng đúng ứng viên).

---

## 3. PHÂN TÍCH 17 CA KIỂM CHỨNG ĐẠI DIỆN ĐA DẠNG

Tất cả 17 ca dưới đây đã được lưu trữ cấu trúc đầy đủ tại [`mau_kiem_chung_12_ca.json`](file:///D:/nlp_chuan_hoa_dia_chi/danh_gia/ket_qua/song_song_20261030/B_chi_tiet/mau_kiem_chung_12_ca.json). Dưới đây là 8 ca mổ xẻ chuyên sâu điển hình đại diện cho toàn bộ các nhóm lỗi:

### Ca 1: Tầng 1 - Sai raw span do ngắt nhầm từ đa nghĩa hành chính
- **ID:** `VNDEV_00003`
- **Đầu vào:** `45 XÔ VIẾT NGHỆ TĨNH P.AN CƯ- NINH KIỀU- CẦN THƠ`
- **Nhãn tham chiếu (Ref 6):** `so_nha: 'Số 45', duong: '', ma_xa: '', ma_tinh: '92'`
- **CNN v2 Spans:** `so_nha: '45' (0:2), duong: 'XÔ VIẾT NGHỆ' (3:15), xa: 'TĨNH' (16:20), xa: 'P.AN CƯ' (21:28)`
- **Dự đoán cuối (Final Pred):** `so_nha: 'Số 45', duong: 'Đường Xô Viết Nghệ TĨNH', ma_xa: '31135', ma_tinh: '92'`
- **Giải thích tầng lỗi:** Từ "TĨNH" trong tên danh nhân "Xô Viết Nghệ Tĩnh" viết hoa hoa không dấu huyền chuẩn và trùng âm với danh từ hành chính "tỉnh". CNN v2 nhận diện nhầm "TĨNH" thành nhãn `xa/huyen/tinh`, khiến span đường bị chặt đứt thành "XÔ VIẾT NGHỆ". Đây là lỗi trích xuất span thô thực sự (Tầng 1). Đồng thời, nhãn ref lại để trống trường `duong`, cho thấy ref cũng có vấn đề về tính đầy đủ.

### Ca 2: Tầng 1 - Sai raw span do gộp dính ranh giới
- **ID:** `VNDEV_00005`
- **Đầu vào:** `268/10 NGUYỄN VĂN LINH, PHƯỜNG XUÂN KHÁNH, QUẬN NINH KIỀU, THÀNH PHỐ CẦN THƠ`
- **Nhãn tham chiếu (Ref 6):** `so_nha: 'Số 268/10', duong: 'Đường Nguyễn Văn Linh', ma_xa: '31144', ma_tinh: '92'`
- **CNN v2 Spans:** `so_nha: '268/10' (0:6), duong: 'NGUYỄN VĂN LINH' (7:22)`
- **Dự đoán cuối (Final Pred):** `so_nha: 'Số 268/10', duong: 'Đường Nguyễn Văn Linh', ma_xa: '31135', ma_tinh: '92'`
- **Giải thích tầng lỗi:** Raw span trích xuất số nhà và đường hoàn toàn đúng. Lỗi 6 trường ở đây là lệch mã xã (`31135` vs ref `31144` - Phường Xuân Khánh sáp nhập vào Phường Ninh Kiều mốc 2025). Gốc rễ là xếp hạng chuyển đổi mốc lịch sử, không phải lỗi span.

### Ca 3: Tầng 2 - Lệch Formatter (Raw span đúng ngữ nghĩa nhưng khác tiền tố)
- **ID:** `VNDEV_00110`
- **Đầu vào:** `120, Xa lộ Hà Nội, Phường Tăng Nhơn Phú, Thành phố Thủ Đức, Thành phố Hồ Chí Minh`
- **Nhãn tham chiếu (Ref 6):** `so_nha: 'Số 120', duong: 'Đường Xa lộ Hà Nội', ma_xa: '26803', ma_tinh: '79'`
- **CNN v2 Spans:** `so_nha: '120' (0:3), duong: 'Xa lộ Hà Nội' (5:17)`
- **Dự đoán cuối (Final Pred):** `so_nha: 'Số 120', duong: 'Xa lộ Hà Nội', ma_xa: '26803', ma_tinh: '79'`
- **Giải thích tầng lỗi:** CNN v2 cắt đúng chính xác `Xa lộ Hà Nội`. Bộ định dạng chuẩn hóa giữ nguyên tiền tố "Xa lộ" nên không thêm từ "Đường" phía trước (`Xa lộ Hà Nội`). Trong khi đó, ref lại ép thêm chữ "Đường" thành `Đường Xa lộ Hà Nội`. Đây là lỗi định dạng hình thức thuần túy (Tầng 2), hai bên hoàn toàn đồng thuận về ngữ nghĩa và thực thể.

### Ca 4: Tầng 3 - Thiếu từ điển đường (Dictionary OOV)
- **ID:** `VNDEV_00055`
- **Đầu vào:** `296 Lý Thái Tổ, P. Hương Sơ, TP. Huế, Thừa Thiên Huế`
- **Nhãn tham chiếu (Ref 6):** `so_nha: 'Số 296', duong: 'Đường Lý Thái Tổ', ma_xa: '21979', ma_tinh: '46'`
- **CNN v2 Spans:** `so_nha: '296' (0:3), duong: 'Lý Thái Tổ' (4:14)`
- **Tra cứu từ điển:** `td_duong.ung_vien('Lý Thái Tổ', '46')` trả về rỗng `[]`!
- **Dự đoán cuối (Final Pred):** `so_nha: 'Số 296', duong: '', ma_xa: '21979', ma_tinh: '46'`
- **Giải thích tầng lỗi:** Extractor CNN v2 cắt span `Lý Thái Tổ` chuẩn xác 100%. Tuy nhiên, trong `tu_dien_duong_v5.json` của tỉnh Thừa Thiên Huế (mã `46`) hoàn toàn không có mục từ "Lý Thái Tổ". Pipeline buộc phải trả về rỗng vì không tìm thấy tên chuẩn được bảo vệ. Lỗi nằm hoàn toàn ở độ phủ từ điển (Tầng 3).

### Ca 5: Tầng 4 - Xếp hạng Canonical / Beam Selection sai
- **ID:** `VNDEV_00004`
- **Đầu vào:** `313, NGUYỄN VĂN LINH, PHƯỜNG AN KHÁNH, QUẬN NINH KIỀU, THÀNH PHỐ CẦN THƠ`
- **Nhãn tham chiếu (Ref 6):** `so_nha: 'Số 313', duong: 'Đường Nguyễn Văn Linh', ma_xa: '31149', ma_tinh: '92'`
- **CNN v2 Spans:** `so_nha: '313' (0:3), duong: 'NGUYỄN VĂN LINH' (5:20)`
- **Tra cứu từ điển:** Tìm thấy ứng viên hợp lệ trong từ điển v5.
- **Dự đoán cuối (Final Pred):** `so_nha: 'Số 313', duong: 'Đường Nguyễn Văn Linh', ma_xa: '31135', ma_tinh: '92'`
- **Giải thích tầng lỗi:** Cả span và từ điển đường đều đúng. Tuy nhiên, ranker chọn nhầm mã xã mới `31135` (Phường Ninh Kiều) thay vì mã `31149` (Phường An Khánh vẫn giữ nguyên sau sáp nhập 2025). Đây là lỗi của bộ chọn beam / xếp hạng hành chính (Tầng 4).

### Ca 6: Tầng 5 - Nhãn tham chiếu (Ref) bị nhiễu nặng
- **ID:** `VNDEV_00113`
- **Đầu vào:** `Tổ 1, ấp 4, Mỹ Long, Cao Lãnh, Đồng Tháp.`
- **Nhãn tham chiếu (Ref 6):** `so_nha: '', duong: 'Đường Tổ 1, Ấp 4, Mỹ Long, Cao Lãnh, Đồng Tháp.', thon_xom: 'Ấp 4'`
- **CNN v2 Spans:** `thon_xom: 'Tổ 1, ấp 4' (0:12)`
- **Dự đoán cuối (Final Pred):** `so_nha: '', duong: '', thon_xom: 'Tổ 1, Ấp 4', ma_xa: '30112', ma_tinh: '82'`
- **Giải thích tầng lỗi:** Nhãn tham chiếu máy bị lỗi ghép trường: toàn bộ địa chỉ bị dồn vào trường `duong` (`'Đường Tổ 1, Ấp 4, Mỹ Long, Cao Lãnh, Đồng Tháp.'`). Mô hình CNN v2 trích đúng `Tổ 1, ấp 4` là thôn xóm và không có đường. Việc đánh giá model "sai đường" ở ca này là do nhãn tham chiếu bị ô nhiễm (Tầng 5).

### Ca 7: Tầng 5 - Xã bị chia tách mốc 2025 không đủ căn cứ chọn 1 đích
- **ID:** `VNDEV_00012`
- **Đầu vào:** `Số 16 ngõ 12 Trần Quý Kiên tổ 58A, phường Dịch Vọng, quận Cầu Giấy, Hà Nội`
- **Nhãn tham chiếu (Ref 6):** `so_nha: 'Số 16', ngo_ngach_hem: 'Ngõ 12', duong: 'Đường Trần Quý Kiên', ma_xa: '00157', ma_tinh: '01'`
- **Dự đoán cuối (Final Pred):** `ma_xa: ''` (bật cảnh báo `xa_bi_chia`)
- **Giải thích tầng lỗi:** Phường Dịch Vọng bị chia tách/điều chỉnh địa giới năm 2025. Đầu vào chỉ có "phường Dịch Vọng" chung chung, không có ranh giới số nhà chi tiết để xác định chắc chắn thuộc về xã đích mới nào. Hệ thống hạ cờ an toàn (`ma_xa = ''`) để bảo toàn tính trung thực ngữ nghĩa, đúng theo hợp đồng dữ liệu. Ép nhãn lấy điểm số ở ca này là vi phạm nguyên tắc khoa học.

### Ca 8: Dev Khó - Biến thể mất dấu và viết tắt tiền tố
- **ID:** `VNDEV_KHO_00017`
- **Đầu vào:** `so 369A d. hoang thi loan, phuong hoa minh, quan lien chieu, thanh pho da nang`
- **Nhãn tham chiếu (Ref 6):** `so_nha: 'Số 369A', duong: 'Đường Hoàng Thị Loan', ma_xa: '20194', ma_tinh: '48'`
- **CNN v2 Spans:** `so_nha: '369A' (3:7), duong: 'hoang thi loan' (11:25)`
- **Dự đoán cuối (Final Pred):** `so_nha: 'Số 369A', duong: 'Đường Hoàng Thị Loan', ma_xa: '20203', ma_tinh: '48'`
- **Giải thích tầng lỗi:** CNN v2 khôi phục và cắt span không dấu viết tắt `d. hoang thi loan` rất tốt. Sai lệch ở 6 trường xảy ra do mã xã `20203` vs ref `20194` (sai lệch ở tầng tra cứu / beam hành chính).

---

## 4. KẾT LUẬN & ĐỀ XUẤT HÀNH ĐỘNG THỰC TẾ

1. **Khép lại nghi ngờ về Extractor:**
   - Dữ liệu chứng minh rành mạch rằng CNN v2 không phải là nguyên nhân làm sụt giảm độ chính xác hệ thống (Exact F1 đạt 98.58% trên Dev gốc và 98.76% trên Dev khó).
   - Ngừng ngay các nỗ lực tốn kém tài nguyên nhằm thay thế CNN v2 bằng các mô hình Transformer nặng nề trên CPU khi chưa giải quyết tầng từ điển và ranking.
2. **Tập trung nguồn lực vào Tầng 3 (Từ điển đường) và Tầng 4 (Xếp hạng Beam):**
   - Hơn **51.8% lỗi chi tiết** là do OOV trong từ điển đường. Cần mở rộng `tu_dien_duong` bằng cách thu thập tên đường chính quy từ danh mục địa chính cấp tỉnh/huyện.
   - Cải tiến cơ chế chọn lọc canonical của `BoXepHang` để tận dụng trần 30.45% tiềm năng có sẵn trong beam.
3. **Kế hoạch bổ sung dữ liệu huấn luyện:**
   - Tập trung vào các mẫu hiếm: vai trò `thon_xom` (ấp, tổ, thôn nông thôn).
   - Huấn luyện giải quyết các trường hợp từ đa nghĩa hành chính trong tên đường ("Xô Viết Nghệ Tĩnh", "Phố Cần Thơ").

---
*Báo cáo được tạo tự động và kiểm chứng độc lập bởi Script `tach_loi_chi_tiet.py`.*
