# Hiện trạng dự án

## 1. Mục tiêu và đầu vào

Nhận **một chuỗi địa chỉ tiếng Việt tự do**, chuẩn hóa các thành phần và
đối chiếu về mốc hành chính **01/07/2025**. Input có thể không dấu, viết
tắt mạnh, typo/Telex, dính chữ, thiếu cấp, đảo thứ tự, lặp tên hoặc trộn
tên cũ và mới ngay trong cùng chuỗi. Không có cờ cho biết input thuộc mốc nào.

Địa chỉ cuối gồm số nhà, ngõ/ngách/hẻm, thôn/xóm/tổ, đường, xã/phường và tỉnh;
huyện cũ là bằng chứng để giải nghĩa, không xuất trong địa chỉ mới.
Giữ mã, cảnh báo, dấu vết và các xã ứng viên khi chưa thể chọn một đích.

Các yêu cầu triển khai: offline khi suy luận, không gọi LLM/API để chuẩn hóa
từng địa chỉ; CPU và chi phí cloud quan trọng. Chưa xây web/service sản phẩm.
CLI xử lý một chuỗi đã có; luồng CSV/Excel hoàn chỉnh chưa được nghiệm thu.
Không xác minh số nhà có tồn tại thật hoặc định vị tọa độ.

**Lưu ý đặc tả:** `bai_toan.md` cũ có ví dụ diễn giải `12/5` thành số nhà/ngõ.
Các sửa sau này giữ nguyên số ghép khi chưa có căn cứ chia. Đọc thêm
`docs/HOP_DONG_NHAN_CHUAN_HOA.md`; chưa coi các tài liệu lịch sử là nhất quán
hoàn toàn. Quyết định thiếu thông tin/mơ hồ cần được chốt lại bằng ví dụ.

## 2. Repo và môi trường

- Repo đang làm: `D:\nlp_chuan_hoa_dia_chi`.
- Remote cấu hình: `https://github.com/AnDpTri/vietnamese-address-normalization.git`.
- HEAD lúc kiểm tra: `de2d41c`; commit trước là `d30b19c`.
- Có nhiều file sửa/chưa track. Không commit, push hoặc reset trong lượt bàn giao.
- Python3.12; PowerShell trên Windows. Máy đo là i5-11400H, 16GB RAM,
  RTX3050 Laptop4GB. Các số CPU không phải SLA server.
- `.venv-neural`: torch CPU2.15.0, numpy2.5.4, lightgbm4.7.0,
  python-crfsuite0.9.12; transformers4.57.1, pyvi0.1.1 và safetensors được
  dùng cho ViDeBERTa. Xem requirements và metadata thực tế, không giả định
  pin Windows có sẵn trên mọi Python/Linux.
- Môi trường venv không phải artifact bàn giao; tái tạo trong môi trường riêng.

## 3. Kiến trúc đang chạy

Luồng khái quát:

`input/offset → token lexical + nhận diện vai trò → ứng viên cũ/mới → beam
và quan hệ hành chính → chi tiết/định dạng từng nhánh → xếp hạng → tra tên
và quyết định mơ hồ → output/dấu vết`.

| Thành phần | File chính | Trách nhiệm/giới hạn |
|---|---|---|
| Unicode/token | `src/tien_xu_ly.py` | NFC, offset gốc, token lexical; không chọn thực thể |
| Tiền tố | `src/quy_tac.py` | Loại hành chính/chi tiết và dạng Telex từ từ chuẩn |
| Schema | `src/nhan.py` | BIO/7 vai trò dùng chung |
| Nhận diện | `src/char_cnn.py`, `videberta.py`, `crf_chi_tiet.py` | NN/CRF phát hiện span; không tự chứng thực tên chuẩn |
| Adapter neural | `src/ngu_canh_neural.py` | Chuyển span/emission sang token có offset |
| Tra ứng viên | `src/tim_kiem.py`, `tra_cuu_neural.py` | Trie, alias, fuzzy có giới hạn, hai lưới token |
| Dữ liệu/đồ thị | `src/danh_muc.py`, `chuyen_doi.py` | Mốc+mã, cha-con, mapping nhiều đích |
| Beam | `src/giai_ma.py` | Các tổ hợp khả dĩ, mặc định beam40 |
| Chi tiết/format | `src/tach_phan_con.py`, `dinh_dang.py` | Luật hoặc span model theo từng giả thuyết |
| Ranker | `src/xep_hang.py` | LightGBM LambdaRank tùy chọn, phải đúng checkpoint/catalogue |
| Tên đường | `src/chuan_ten_duong.py` | Tra tên train theo tỉnh, collision và dấu; chưa phải gazetteer chính thức |
| Giải thích | `src/hop_dong.py` | Bằng chứng/giả thuyết, chế độ thử nghiệm |
| Điều phối | `src/chuan_hoa.py`, `__main__.py` | API/CLI và quyết định cuối |

Mã đơn vị luôn phải đi với mốc vì cùng mã số có thể chỉ đơn vị khác nhau.
Không ép toàn input vào một mốc. Không dùng giao của các tập đích mới để
thay thế kiểm cha-con ở nguồn cũ. Không chọn tùy ý một đích cho xã bị chia.

Mặc định CLI không truyền model vẫn là luật v3; backend neural và các cờ
thử nghiệm phải bật rõ. `--hop-dong` là chế độ chính sách khác, chưa được
chọn làm mặc định và đã làm giảm khớp sáu trường trong phép đo.

## 4. Dữ liệu và mức tin cậy

### Danh mục hành chính đã ghim để đo

Snapshot chuẩn ở `mo_hinh/thu_nghiem/char_v1_01/snapshot/clean/`:
63 tỉnh cũ,696 huyện cũ,10.033 xã cũ;34 tỉnh mới,3.321 xã mới;
10.569 dòng mapping. Lần kiểm tra tiếp quản ghi nhận440 xã cũ nhiều đích.
Sáu CSV catalogue live khớp byte snapshot tại thời điểm kiểm tra bàn giao.
Mọi sửa tiếp theo cần kiểm hash lại, không mặc định live mãi trùng snapshot.

### Train/dev đã dùng để có số đo

- Train gốc CSV4.564, dev gốc1.136; nhãn phần lớn máy/tổng hợp.
- CRF dùng3.973 train gốc hoặc5.966 kết hợp sau lọc.
- CNN dùng4.841 train;1.169 dòng train khác để fit ranker, theo nhóm cha/họ.
- Dev khó đóng băng để đối chứng hiện tại:464 dòng. Không thay bằng500 dòng
  live chỉ vì tên file giống nhau.
- Đo raw span trên1.026/1.136 dev gốc và464 câu khó; CRF token lịch sử chỉ
  căn chỉnh được452 câu khó. Không so trực tiếp những F1 khác tập con/đơn vị.
- Dev khó có0 span ngõ/hẻm và12 span thôn/tổ; điểm tổng cao không chứng minh
  đủ năng lực cho các nhóm hiếm. Các biến thể có quan hệ nguồn, không độc lập.

### Test400

Là địa chỉ OSM và hồ sơ duyệt, chưa phải bộ gold ngữ nghĩa hoàn chỉnh.
Lịch sử nhiều audit đã bắt lỗi engine/validator dù unit test PASS.
Mốc audit4 ghi289 duyệt AI/111 cần duyệt và36 xã chia giữ đích trống;
đây là số lịch sử, không coi là tình trạng live đã nghiệm thu mới nhất.
Không dùng nhãn test này để sửa thuật toán hoặc chọn tham số.

### Dữ liệu bổ sung và phần dùng tiếp

- `bo_sung_v1`: có lịch sử2.037/464 rồi2.169/500; snapshots khác nhau phải
  giữ riêng. Có lỗi provenance/đối ứng đã được nêu trong các audit.
- `bo_sung_v2`: bàn giao3.000 mẫu/650family; audit độc lập bắt nhãn ngõ/thôn
  còn giữ dù đã mất khỏi input. Có654 trường ngõ và79 trường thôn không có
  span;433 và66 tương ứng vẫn được gắn canonical usable. Số theo trường
  có thể chồng dòng. Char/token offset cơ học không thấy lỗi trong audit đó.
- `data/train_dev/duyet_v2_01/`: bản lọc độc lập từ snapshot audit, không sửa
  corpus gốc.1.183 qua cổng lọc;927 dòng/301cha dùng bổ sung phần CNN,
  256 giữ riêng theo họ; bộ kết hợp5.768 dòng. Có ID/lý do loại/hash.
  **Chưa dùng bộ927 này để tạo các điểm model/end-to-end đang báo.**
- Bản lọc là đủ điều kiện theo kiểm tra hiện tại, không phải gold hoặc bảo
  đảm đúng ngữ nghĩa toàn bộ. Không coi dòng bị loại vì trùng/giữ họ là nhãn sai.

### Danh mục đường

Audit đầu:1.461 confirmed/1.007 tên nhưng nguồn TXT tự tạo từ bảng Python;
8/10 URL là trang gốc; một URL QĐ1454 dẫn sang QĐ89 khác văn bản.
Gói chưa được tích hợp làm nguồn chứng thực.

File live thống kê phiên bản1.1 đã đổi thành53 confirmed theo khai báo và
1.484 candidate/pending (gồm các dòng cũ hạ trạng thái), có6 raw sources.
**Bản sửa này chưa có audit độc lập mới trong mốc bàn giao.** Không hiểu
audit cũ như kết luận rằng mọi file live vẫn giống bản cũ, và cũng không
hiểu53 confirmed tự khai là đã được nghiệm thu. Dùng hash/nguồn để kiểm lại.

## 5. Các checkpoint và đường dẫn

| Artifact | Đường dẫn |
|---|---|
| CRF gốc/kết hợp | `mo_hinh/thu_nghiem/crf_v1_01/train_goc.crfsuite`, `train_ket_hop.crfsuite` |
| CNN351.246 tham số | `mo_hinh/thu_nghiem/char_v1_01/char_cnn.pt` |
| Ranker CNN | `mo_hinh/thu_nghiem/char_v1_01/ranker.txt` + `.json` |
| ViDeBERTa70.753.742 tham số | `mo_hinh/thu_nghiem/videberta_v1_01/model/` |
| Ranker ViDeBERTa | `mo_hinh/thu_nghiem/videberta_v1_01/ranker.txt` + `.json` |
| Từ điển train1.018 cặp tên/tỉnh | `danh_gia/ket_qua/sua_pipeline_cnn_v1_01/tu_dien_duong_train.json` |

ViDeBERTa từ `Fsoft-AIC/videberta-xsmall`, revision
`029b6b1b1d7636221bd2d1a98b46a2fdba3af34e`; checkpoint cục bộ đã fine-tune.
Không cần tải encoder mới để chạy checkpoint này. Ranker kiểm hash encoder
và catalogue; không ghép tùy ý ranker CNN/ViDeBERTa.

CNN train12epoch/4.841 mẫu trên CPU khoảng263,27s. ViDeBERTa train5epoch
trên T4, tổng vòng epoch412,37s; chưa gồm download/preprocessing/ghi model.
Hai thời gian khác môi trường và không phải cam kết thời gian train lại.

## 6. Chất lượng: tách loại chỉ số

### Tiền xử lý, phép đo mới sau tách module

Trên1.600 câu: offset không chồng, NFC/mapping và giữ ký tự không phải khoảng
trắng đều hợp lệ100%. Đây là invariants kỹ thuật, **không phải accuracy token**.
Biên lexical khớp1.921/1.921 span gốc và904/928 span khó (97,414%);
452/464 câu khó có mọi biên phù hợp. Chưa có nhãn token độc lập đầy đủ để
đo cả ranh giới thừa/sai; không gọi tiền xử lý chính xác100% ngữ nghĩa.

### Model nhận diện raw span chi tiết

| Model | F1 gốc /1.026 câu | F1 khó /464 câu | Câu đúng toàn bộ span gốc/khó |
|---|---:|---:|---:|
| CNN |98,132%|98,761%|988/1.026;453/464|
| ViDeBERTa |97,566%|98,925%|974/1.026;456/464|

Chỉ gồm4 trường chi tiết, không phải F1 đầy đủ cả7 vai trò hoặc accuracy mã
hành chính/tên chuẩn. Nhãn hành chính là căn chỉnh yếu, chưa có gold đầy đủ.

### End-to-end sáu trường, mốc hoàn tất mới nhất

| Cấu hình | Dev gốc | Dev khó | CPU mean/P95 gốc; khó |
|---|---:|---:|---|
| CNN+ranker+tra tên train+bảo vệ đường |941/1.136=82,835%|337/464=72,629%|27,52/46,75ms;28,00/55,67ms|
| ViDeBERTa+điểm tay+cùng bước sau |926/1.136=81,514%|340/464=73,276%|118,58/163,34ms;116,67/151,65ms|

Số từ `danh_gia/ket_qua/sua_tien_to_hanh_chinh_v2_01/`. CPU laptop1luồng,
đã nạp model, một lượt tuần tự, không gồm JSON/I/O/khởi tạo. Tải nền có thể
ảnh hưởng. Không so tỷ số với CPU Colab hoặc các lần laptop khác tải.

Đã chạy ma trận12 cấu hình luật/CRF/CNN/ViDeBERTa trên cùng pipeline ở mốc
trước; chưa chạy lại đủ12 sau sửa cuối. Đừng tự gán điểm mới cho luật/CRF.

Tất cả là **khớp nhãn dev máy/tổng hợp đã dùng phát triển**, chưa phải accuracy
thực tế hoặc bằng chứng đạt95%. Không nhân F1 span với độ hợp lệ tiền xử lý.

### Phép đo định dạng có span hoàn hảo

Cho formatter span tham chiếu, không chạy NN/tra tên: khớp giá trị1.820/1.921
gốc (94,742%) và803/910khó (88,242%). Sau bỏ dấu1.909/1.921 và876/910.
18span có canonical trống ghi riêng. Đây là chẩn đoán thiếu thông tin sau
span, không phải ground truth độc lập để quy mọi sai khác cho formatter.

## 7. Lỗi và giới hạn còn mở

- Thiếu độ phủ khôi phục dấu/alias/tên đường và căn cứ địa bàn.
- Giá trị quan sát/chưa giải và tên chuẩn đang dùng chung trường `duong`.
  NTT có thể được xuất thành Đường Ntt dù reference cố ý để canonical trống.
- Mơ hồ thật: Tam Dan có Tam Đàn/Tam Dân; input có thể thiếu thông tin để
  chọn một mã. Không sửa bằng cách ép nhãn một đích.
- Còn lỗi span/số nhà/ghép đường, nhất là dính chữ hoặc thành phần lồng.
- Beam hữu hạn và điểm ranker/điểm tay chưa hiệu chỉnh như xác suất.
- Từ điển train là nguồn học yếu, không chứng minh đường thực thuộc phường.
- Một số test công cụ dữ liệu lọt lỗi ngữ nghĩa. PASS chỉ có giá trị trong
  phạm vi mà fixture/validator kiểm; không công bố100% verified từ đó.
- Dev đã được xem và sửa nhiều lần; có nguy cơ quá khớp. Các mẫu đổi số nhà
  không phải nhiều tình huống độc lập. Chưa có đánh giá thực địa/gold sạch.

## 8. Chạy lại

Từ gốc dự án, cài dependency trong venv riêng. Trên Linux dùng `python`
thay `py -3.12` và `.venv/bin/python` thay đường dẫn Scripts.

```powershell
py -3.12 -X utf8 -B -m src 'Số 17C, Đường Hoa Binh, Thành phố Hà Nội'

.\.venv-neural\Scripts\python.exe -X utf8 -B -m src 'Số 17C, Đường Hoa Binh, Thành phố Hà Nội' --char-model mo_hinh/thu_nghiem/char_v1_01/char_cnn.pt --ranker mo_hinh/thu_nghiem/char_v1_01/ranker.txt --tu-dien-duong danh_gia/ket_qua/sua_pipeline_cnn_v1_01/tu_dien_duong_train.json --bao-ve-duong --threads 1

.\.venv-neural\Scripts\python.exe -X utf8 -B -m src 'Số 17C, Đường Hoa Binh, Thành phố Hà Nội' --videberta-model mo_hinh/thu_nghiem/videberta_v1_01/model --tu-dien-duong danh_gia/ket_qua/sua_pipeline_cnn_v1_01/tu_dien_duong_train.json --bao-ve-duong --threads 1
```

Không thêm `--hop-dong` rồi so như cùng cấu hình. Nếu catalogue live đổi,
hãy nạp snapshot vào `DanhMuc(path)` qua API; không xóa kiểm hash của ranker.
`BoChuanHoa(danh_muc=...,bo_tach=...,bo_xep_hang=...,tu_dien_duong=...,
bao_ve_duong=True)` là cấu hình tương ứng. Schema `KetQua` ở `src/kieu_du_lieu.py`.

Đo lại hai backend vào thư mục MỚI, không đè số cũ:

```powershell
.\.venv-neural\Scripts\python.exe -X utf8 -B -m danh_gia.do_sua_dinh_dang --output danh_gia/ket_qua/doi_chung_moi --baseline danh_gia/ket_qua/sua_tien_to_hanh_chinh_v2_01
```

Script có tên lịch sử, hiện đo cấu hình đã ghép mọi sửa runtime hiện có.
Không thêm `--hop-dong` nếu muốn tái hiện chính sách baseline.

Kiểm thử core gần nhất:92bài PASS sau refactor, có các test CRF/NN/offset/
tiền tố/giữ mơ hồ và smoke Colab tiny. Không có nghĩa full GPU hoặc mọi
validator dữ liệu live đã nghiệm thu. Lệnh tương ứng:

```powershell
.\.venv-neural\Scripts\python.exe -X utf8 -B -m unittest tests.test_telex_tien_to tests.test_hop_dong tests.test_dinh_dang_tien_to tests.test_chuan_ten_duong tests.test_char tests.test_pipeline tests.test_pipeline_v3 tests.test_crf tests.test_danh_gia tests.test_videberta_colab
```

Refactor có parity mỗi backend8raw-span +4end-to-end, không chạy lại full
inference chỉ để đổi chỗ code. F1 được tính lại từ predictions đã lưu.

## 9. Bằng chứng nên đọc

- `docs/MODULE_VA_SO_DO.md` và `danh_gia/ket_qua/tung_module_v1_01/`.
- `danh_gia/ket_qua/sua_tien_to_hanh_chinh_v2_01/`: output đầy đủ, thay đổi,
  nguồn code, checkpoint/input hash, ca hồi quy.
- `danh_gia/ket_qua/ma_tran_v1_01/`:12cấu hình và đối chiếu từng câu.
- `danh_gia/ket_qua/chan_doan_beam_v1_01/`: toàn beam các câu sai ở mốc trước.
- `danh_gia/ket_qua/do_hop_dong_v1_01/`: thí nghiệm giảm điểm và giải thích.
- `danh_gia/ket_qua/audit_agy_duong_train_v2_01/`: audit, snapshot, fixture,
  HTML/HTTP/hash nguồn chính thức đã đối chiếu.
- `data/train_dev/duyet_v2_01/`: subset, manifest và lý do không dùng.
- `bao_cao/2026-10-29/`: gói lịch sử đã lưu, không sửa lại báo cáo cũ để hợp
  kết luận mới. Đường dẫn local chat trong tài liệu cũ có thể đã hết tác dụng.

## 10. Định nghĩa hoàn thành cho lượt cải tiến tiếp theo

Cần một phương án được giải thích độc lập, triển khai chạy được, baseline
tái hiện, output đầy đủ và phép đo đúng nhiệm vụ. Báo cả phương án không
hiệu quả, số câu đúng thêm/sai thêm, chi phí CPU/RAM và phần không thể biết
từ input. Không chỉ tăng điểm trên tập đã dùng để sửa. Yêu cầu chi tiết
trong `YEU_CAU_CAI_TIEN.md`; không bắt buộc tiếp tục kiến trúc hiện tại.
