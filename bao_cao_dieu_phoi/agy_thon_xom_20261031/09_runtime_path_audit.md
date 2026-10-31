# BÁO CÁO KIỂM TOÁN ĐƯỜNG THỰC THI THẬT VÀ ẢNH HƯỞNG CỦA SỬA CRF LÊN PIPELINE SẢN PHẨM

- **Thời điểm kiểm toán**: 2026-10-31
- **Mã commit kiểm toán**: `63a1f21` (nhánh `agy/thon-xom-d-20261031`)
- **Phạm vi kiểm toán**: Worktree độc lập chỉ đọc `D:\nlp_rf_gate\wt_thonxom_D`
- **Tập trung 8 file trọng tâm**:
  1. `src/chuan_hoa.py`
  2. `src/tien_xu_ly/lam_sach.py`
  3. `src/crf_chi_tiet.py`
  4. `src/tien_xu_ly/crf_chi_tiet.py`
  5. `src/tien_xu_ly/char_cnn.py`
  6. `tests/test_loi_goc_log.py`
  7. `tests/test_crf.py`
  8. `src/__main__.py`

---

## I. Call Chain Tổng Thể: CLI -> BoChuanHoa -> BoLamSach -> Bộ Tách

```mermaid
flowchart TD
    CLI["CLI (src/__main__.py)"] -->|--crf-model| CRF_Backend["BoTachCRF (pycrfsuite)"]
    CLI -->|--char-model (mặc định sp)| CNN_Backend["BoTachCharCNN (PyTorch LinearCRF)"]
    CLI -->|Không truyền cờ| Rule_Backend["None (baseline_luat_v3)"]
    
    CRF_Backend --> BCH["BoChuanHoa (src/chuan_hoa.py:27)"]
    CNN_Backend --> BCH
    Rule_Backend --> BCH
    
    BCH --> BLS["BoLamSach (src/tien_xu_ly/lam_sach.py:160)"]
    
    BLS -->|tao_gia_thuyet| Ctx_Branch{Kiểm tra bo_tach}
    Ctx_Branch -->|hasattr 'chuan_bi_chuoi'| CNN_Call["BoTachCharCNN.chuan_bi_chuoi() -> NguCanhChar"]
    Ctx_Branch -->|không có chuan_bi_chuoi| CRF_Call["BoTachCRF.chuan_bi() -> NguCanhCRF"]
    Ctx_Branch -->|bo_tach is None| No_Ctx["crf_context = None"]
    
    CNN_Call --> Span_Parse["crf_context.tach() (KẾ THỪA NguCanhCRF.tach)"]
    CRF_Call --> Span_Parse
    No_Ctx --> Rule_Tach["tach_co_dau_vet() (src/tien_xu_ly/tach_phan_con.py)"]
```

### Chi tiết các mắt xích:
1. **Khởi tạo và chọn Backend**:
   - `src/__main__.py:28-36`: CLI kiểm tra cờ độc quyền giữa `--crf-model`, `--char-model`, và `--videberta-model`. Nếu chọn `--crf-model`, khởi tạo `BoTachCRF`. Nếu chọn `--char-model`, khởi tạo `BoTachCharCNN`. Mặc định nếu không truyền cờ là `backend = None`.
   - `src/__main__.py:47`: Khởi tạo `BoChuanHoa(..., bo_tach=backend, ...)`.
2. **Ủy quyền thực thi**:
   - `src/chuan_hoa.py:30-35`: `BoChuanHoa.__init__` khởi tạo `self.bo_lam_sach = BoLamSach(..., bo_tach=bo_tach, ...)`.
   - `src/chuan_hoa.py:65`: `BoChuanHoa.chuan_hoa` gọi `self.bo_lam_sach.lam_sach_chi_tiet(chuoi)`.
3. **Phân nhánh xử lý ngữ cảnh nhận diện**:
   - `src/tien_xu_ly/lam_sach.py:223`: Kiểm tra `hasattr(self.bo_tach, 'chuan_bi_chuoi')`.
     - `BoTachCharCNN` có phương thức này (`src/tien_xu_ly/char_cnn.py:132`) -> trả về đối tượng `NguCanhChar`.
     - `BoTachCRF` **không** có `chuan_bi_chuoi`, nên `crf_context` tạm thời là `None`.
   - `src/tien_xu_ly/lam_sach.py:205-206`: Nếu `crf_context is None and self.bo_tach is not None`, gọi `crf_context = self.bo_tach.chuan_bi(tokens)`. Tại đây, `BoTachCRF.chuan_bi` (`src/tien_xu_ly/crf_chi_tiet.py:267`) mới được kích hoạt và trả về `NguCanhCRF`.
4. **Phân tách chi tiết (Span Parsing)**:
   - `src/tien_xu_ly/lam_sach.py:234-239`: Gọi `crf_context.tach(occupied, ...)`.
     - Với `BoTachCRF`: chạy `NguCanhCRF.tach()` (`src/tien_xu_ly/crf_chi_tiet.py:174`).
     - Với `BoTachCharCNN`: đối tượng `NguCanhChar` kế thừa trực tiếp từ `NguCanhCRF` (`class NguCanhChar(NguCanhCRF)`) và **không override phương thức `tach()`**, do đó chạy chính `NguCanhCRF.tach()` trong `src/tien_xu_ly/crf_chi_tiet.py`!
     - Với `backend = None`: chạy `tach_co_dau_vet()` của thuần luật.

---

## II. Trả Lời 5 Câu Hỏi Trọng Tâm

### 1. Khi nào `src/tien_xu_ly/crf_chi_tiet.py` được thực thi thật, lúc nào không? Phân biệt CRF độc lập với CharCNN và phần CRF của CharCNN

- **Khi nào thực thi thật?**
  1. *Toàn bộ file (gồm cả mô hình pycrfsuite và trích xuất đặc trưng)*: Chỉ thực thi khi pipeline được cấu hình chạy với `BoTachCRF` (truyền `--crf-model` từ CLI hoặc gọi trực tiếp trong code như `tests/test_crf.py:73-75`).
  2. *Một phần file (hàm tiện ích và phân tách span `NguCanhCRF.tach`)*: **Luôn luôn thực thi** ngay cả khi chạy pipeline mặc định `BoTachCharCNN`!
     - `NguCanhChar` kế thừa `NguCanhCRF` (`src/tien_xu_ly/ngu_canh_neural.py:2`), do đó lời gọi `crf_context.tach()` tại `src/tien_xu_ly/lam_sach.py:234` thực chất thực thi mã nguồn `NguCanhCRF.tach()` tại `src/tien_xu_ly/crf_chi_tiet.py:174-252` cùng các hàm phụ trợ `loc_va_chinh_bien_span` (dòng 146), `chinh_bien_so_nha` (dòng 131), `loc_so_nha_ma_buu_chinh` (dòng 156).
     - Hàm `bio_spans()` (`src/tien_xu_ly/crf_chi_tiet.py:69-82`) được import và thực thi trực tiếp tại `src/tien_xu_ly/lam_sach.py:208` khi cờ `bao_ve_duong=True`.
- **Lúc nào KHÔNG thực thi?**
  - Khi chạy pipeline thuần luật (`bo_tach=None`, không cờ nhận diện): `crf_context` là `None`, luồng rẽ sang `tach_co_dau_vet()` tại `src/tien_xu_ly/lam_sach.py:238`, toàn bộ `crf_chi_tiet.py` bị bỏ qua.
  - Khi chạy `BoTachCharCNN`: phần trích xuất đặc trưng `dac_trung()` (`src/tien_xu_ly/crf_chi_tiet.py:34-66`) và lớp mô hình `BoTachCRF` (`src/tien_xu_ly/crf_chi_tiet.py:255-272`) **không bao giờ** được gọi.
- **Phân biệt 3 thành phần bản chất khác nhau**:
  - **CRF độc lập (`BoTachCRF`)**: Định nghĩa tại `src/tien_xu_ly/crf_chi_tiet.py:255-272`. Sử dụng thư viện ngoài `pycrfsuite` (C++). Hoạt động ở mức từ/token, trích xuất đặc trưng thủ công theo luật từ điển/ký tự (`dac_trung()`).
  - **CharCNN (`BoTachCharCNN`)**: Định nghĩa tại `src/tien_xu_ly/char_cnn.py:114-146`. Mạng neural tích chập ký tự 1D sâu (`CharCNNCRF`, dòng 95-109) viết bằng PyTorch, nhận diện nhãn chuỗi trên từng ký tự Unicode NFC.
  - **Phần CRF của CharCNN (`LinearCRF`)**: Định nghĩa tại `src/tien_xu_ly/char_cnn.py:28-80`. Là một `nn.Module` PyTorch nằm trên cùng của mạng CharCNN, quản lý ma trận chuyển trạng thái nhãn ($19 \times 19$ trong `TAGS`) và thuật toán giải mã Viterbi CPU (`decode()`). CRF này hoàn toàn độc lập với thư viện `pycrfsuite` và không liên quan gì đến logic trong `src/tien_xu_ly/crf_chi_tiet.py`.

---

### 2. Bốn test tích hợp trong `tests/test_loi_goc_log.py` gọi CharCNN hay CRF module đang sửa? Những test đó có thật sự kiểm chứng patch CRF không?

- **Module được gọi**:
  Trong `tests/test_loi_goc_log.py:18-24`:
  ```python
  from src.tien_xu_ly.char_cnn import BoTachCharCNN
  from src.tien_xu_ly.xep_hang import BoXepHang
  from src.tien_xu_ly.chuan_ten_duong import TuDienDuong
  dm = DanhMuc()
  cnn = BoTachCharCNN(MO_HINH / 'char_cnn.pt', threads=1)
  cls.bo = BoChuanHoa(danh_muc=dm, bo_tach=cnn, bo_xep_hang=BoXepHang(MO_HINH / 'ranker.txt', cnn.ma_bam, dm.ma_bam),
                      tu_dien_duong=TuDienDuong(TU_DIEN), bao_ve_duong=True, tien_to_mac_dinh=True)
  ```
  Tất cả các ca kiểm thử trong `test_loi_goc_log.py` khởi tạo và chạy thông qua **`BoTachCharCNN` + `BoXepHang` (Char-CNN + LambdaRank)**. **Không có bất kỳ test nào khởi tạo hay gọi `BoTachCRF`**.
  *(Các comment trong test ghi "CRF gán tỉnh" ở dòng 27 hay "CRF gán nhầm" ở dòng 43 chỉ là cách gọi quen miệng trong nhật ký, thực chất backend chạy là Char-CNN).*
- **Có thật sự kiểm chứng patch CRF không?**:
  **HOÀN TOÀN KHÔNG**.
  1. Nếu bản sửa nhằm vào mô hình CRF (`BoTachCRF` / `dac_trung` / train CRF), các test này hoàn toàn bỏ qua patch vì chúng đang nạp trọng số pre-trained `char_v3_tc/char_cnn.pt`.
  2. Việc bộ test `test_loi_goc_log.py` chạy qua (PASS) chỉ chứng minh pipeline cũ của CharCNN không bị sập cú pháp, hoàn toàn **không thể làm bằng chứng** xác nhận mô hình CRF độc lập đã được sửa đúng.
  3. Kể cả đối với các luật span chung trong `NguCanhCRF.tach` mà CharCNN kế thừa, các ca kiểm thử trong `test_loi_goc_log.py` chỉ kiểm tra các hành vi xử lý đơn vị hành chính và tên đường (số điện thoại cuối câu, bảo vệ tên tỉnh, xung đột mốc), không kiểm tra các ca biên chi tiết thôn/xóm hay số nhà của patch CRF.

---

### 3. Wrapper `src/crf_chi_tiet.py` và import module có chỉ tới đúng file mới không?

- **Kiểm tra file wrapper**:
  File `src/crf_chi_tiet.py` gồm đúng 3 dòng:
  ```python
  import sys
  from .tien_xu_ly import crf_chi_tiet as _m
  sys.modules[__name__] = _m
  ```
  File này hoạt động như một module shim, hoán đổi chính nó trong `sys.modules` thành `src.tien_xu_ly.crf_chi_tiet`.
- **Kiểm tra các vị trí import**:
  - `src/__main__.py:29`: `from .crf_chi_tiet import BoTachCRF` -> thông qua shim trỏ đúng về `src.tien_xu_ly.crf_chi_tiet.BoTachCRF`.
  - `tests/test_crf.py:8`: `from src.crf_chi_tiet import bio_spans, ...` -> thông qua shim trỏ đúng về `src.tien_xu_ly.crf_chi_tiet`.
  - `src/tien_xu_ly/lam_sach.py:208`: `from .crf_chi_tiet import bio_spans` -> import relative nội bộ, trỏ trực tiếp đến `src/tien_xu_ly/crf_chi_tiet.py`.
  - `src/tien_xu_ly/char_cnn.py:15`: `from .crf_chi_tiet import NguCanhCRF` -> trỏ trực tiếp đến `src/tien_xu_ly/crf_chi_tiet.py`.
- **Cảnh báo lỗi kiến trúc / Rủi ro bảo trì**:
  Shim chuyển tiếp hoạt động được trong môi trường runtime tiêu chuẩn, nhưng tạo ra sự phân mảnh nguy hiểm: nếu lập trình viên sửa code vào file shim ở thư mục gốc `src/crf_chi_tiet.py` (tưởng là file chính), mã nguồn sửa đổi sẽ bị bỏ qua hoàn toàn do các module nội bộ của `src/tien_xu_ly/` import trực tiếp từ file con. Cần dọn dẹp triệt để các shim này.

---

### 4. Bản sửa chỉ giải quyết nhánh CRF thì có thể ảnh hưởng chất lượng sản phẩm chạy mặc định không?

Đánh dấu: **CONFIRMED (Về đường thực thi cơ học)** và **NOT PROVEN (Về cải thiện chất lượng sản phẩm)**.

- **CONFIRMED (Cơ học luồng chạy)**:
  Có ảnh hưởng trực tiếp đến pipeline mặc định nếu bản sửa nằm trong các hàm xử lý span của `src/tien_xu_ly/crf_chi_tiet.py`.
  *Bằng chứng kiến trúc*:
  `src/tien_xu_ly/ngu_canh_neural.py:2` định nghĩa:
  `class NguCanhChar(NguCanhCRF):`
  Lớp `NguCanhChar` của CharCNN kế thừa trực tiếp từ `NguCanhCRF` và **không ghi đè `tach()`**. Do đó, mọi sửa đổi trong `NguCanhCRF.tach()` (`src/tien_xu_ly/crf_chi_tiet.py:174-252`) hoặc các hàm lọc biên `loc_va_chinh_bien_span`, `chinh_bien_so_nha` đều được pipeline mặc định của sản phẩm (`BoTachCharCNN`) gọi tới.
  Ngược lại, nếu bản sửa chỉ nằm trong `BoTachCRF` hoặc `dac_trung()`, nó hoàn toàn không ảnh hưởng cơ học tới CharCNN.
- **NOT PROVEN (Chất lượng sản phẩm thực tế)**:
  Tuyên bố rằng việc sửa nhánh CRF "giúp cải thiện chất lượng sản phẩm chạy mặc định" là **CHƯA ĐƯỢC CHỨNG MINH (NOT PROVEN)** vì các lý do kỹ thuật sau:
  1. *Lệch phân phối nhãn*: Nhãn ký tự từ `CharCNNCRF` (19 nhãn BIO) có đặc tính dự đoán, độ nhạy và phân phối sai khác biệt so với mô hình thống kê `pycrfsuite`. Một luật heuristics viết cho `pycrfsuite` có thể gây hồi quy (regressions) trên đầu ra của `CharCNN`.
  2. *Thiếu đo đạc thực nghiệm đối chứng*: Không có số liệu đo đạc nào được thực hiện độc lập trên pipeline đầy đủ (`BoTachCharCNN` + `BoXepHang` + `TuDienDuong`) đối chiếu với baseline đóng băng có SHA-256 xác định.
  3. *Ngụy biện kiểm thử*: Việc unit test `tests/test_loi_goc_log.py` xanh chỉ chứng minh không phát sinh exception cú pháp trên tập test mẫu, không phải bằng chứng định lượng về độ chính xác hay chất lượng của pipeline sản phẩm.

---

### 5. Các Mục Tiêu Nghiệm Thu Cần Bổ Sung Để Không Ngộ Nhận Unit Test Xanh Là Hệ Thống Được Cải Thiện

Để tuân thủ nghiêm ngặt chuẩn mực thực nghiệm và kỷ luật kỹ thuật (Rule `user_global`), bắt buộc bổ sung 5 mục tiêu nghiệm thu sau:

1. **Tách biệt và độc lập hóa hai bộ kiểm chứng (Dual Pipeline Verification)**:
   - Khi nghiệm thu patch CRF: bắt buộc chạy bộ đo span chuyên biệt trên mô hình `BoTachCRF` (`danh_gia/do_crf.py`), đo đầy đủ Precision, Recall, Micro F1 trên từng trường (`duong`, `so_nha`, `thon_xom`, `ngo_ngach_hem`). Tuyệt đối không dùng token accuracy để che giấu lỗi span.
   - Khi nghiệm thu pipeline sản phẩm mặc định: bắt buộc đánh giá trên cấu hình `BoTachCharCNN` + `BoXepHang` + `TuDienDuong`.
2. **Đo lường hai chiều bắt buộc (Đúng thêm / Hồi quy)**:
   - Chạy kiểm thử trên tập dữ liệu dev/test chuẩn có hash SHA-256 cố định.
   - Bắt buộc lập bảng phân tích hai chiều: đếm chính xác số trường hợp đúng thêm và số trường hợp bị sai thêm (hồi quy). Không chấp nhận tỷ lệ phần trăm chung chung.
3. **Bẻ gãy Coupling kiến trúc ngầm (Decouple Span Extractor)**:
   - Tách phương thức `tach()` và các hàm `loc_va_chinh_bien_span`, `chinh_bien_so_nha` ra khỏi `src/tien_xu_ly/crf_chi_tiet.py` thành một module trung gian độc lập (ví dụ `src/tien_xu_ly/phan_tach_chi_tiet.py`).
   - Xóa bỏ quan hệ kế thừa `NguCanhChar(NguCanhCRF)` để ngăn chặn việc sửa đổi ngầm ở module CRF làm biến đổi hành vi của pipeline CharCNN ngoài tầm kiểm soát.
4. **Kiểm định siêu dữ liệu Runtime (Runtime Metadata Assertion)**:
   - Bổ sung assertion trong test tích hợp kiểm tra `r.thong_ke['mo_hinh']` và `r.thong_ke['crf_model_sha256']` / `ranker_sha256` để đảm bảo test đang chạy trên đúng backend kỳ vọng, ngăn chặn tình trạng test chạy CharCNN nhưng tưởng là đang test CRF.
5. **Bảo toàn chi phí tài nguyên (Resource & Latency Benchmark)**:
   - Đo Mean và P95 CPU latency trên tối thiểu 1.000 mẫu đại diện. Đảm bảo các vòng lặp kiểm tra và tiền tố mới bổ sung trong `tach()` không làm suy giảm thông lượng (throughput) của hệ thống phục vụ production.
