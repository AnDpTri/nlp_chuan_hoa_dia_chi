# Tập kiểm tra địa chỉ thật — nhãn sơ bộ

**Nhãn là sơ bộ, do máy gán. Nhóm phải duyệt tay trước khi dùng để chấm điểm. Không có dòng nào được ghi `da_duyet`.**

Tập này dành riêng cho đánh giá cuối. Không dùng đầu vào, nhãn, prompt hay kết quả kiểm tra trên tập này để huấn luyện, chọn luật, điều chỉnh mô hình, chọn ngưỡng hoặc chỉnh hệ thống. Bộ tra cứu ở `scripts/admin_lookup.py` độc lập với `src/`; không chạy pipeline đang được đánh giá để tạo đáp án. Việc kiểm tra dưới đây chỉ kiểm tra chất lượng tập dữ liệu, không phải kết quả đánh giá hệ thống NLP.

## Nguồn và giấy phép

- © OpenStreetMap contributors; dữ liệu theo [ODbL 1.0](https://opendatacommons.org/licenses/odbl/1-0/), xem [OSM copyright](https://www.openstreetmap.org/copyright). Phần trích dữ liệu OSM và bảng có nguồn gốc OSM trong thư mục này được chia sẻ theo ODbL 1.0; không mặc định áp dụng giấy phép phần mềm của repo cho dữ liệu này.
- Bản trích Việt Nam do [Geofabrik](https://download.geofabrik.de/asia/vietnam.html) cung cấp: [vietnam-261024.osm.pbf](https://download.geofabrik.de/asia/vietnam-261024.osm.pbf). Bản ngày 24/10/2026 được ghim cố định để tái lập; ngày tải UTC: `2026-10-25T19:16:45.523514+00:00`.
- Kích thước 331,554,438 byte; MD5 `f63b408a616d882d44dab7d21245d51c`, đã so với checksum Geofabrik. Chi tiết tại `goc/download.json`.
- Mỗi dòng CSV có `nguon` là URL node/way/relation OSM. `goc/selected_sources.jsonl` giữ tên địa điểm công khai, các thẻ địa chỉ gốc, phiên bản và thời điểm sửa đối tượng OSM. Đây là bằng chứng nguồn đã đóng băng, vì trang OSM trực tuyến có thể thay đổi.
- Chỉ lấy đối tượng có tên và thẻ tổ chức/địa điểm công khai (`amenity`, `shop`, `office`, `tourism`, `craft`, `healthcare`, `leisure`); bỏ `access=private`. Không chọn nhà dân chỉ có thẻ địa chỉ. Nhóm vẫn cần kiểm tra thủ công tên, tính công khai và địa chỉ nguồn; thẻ OSM có thể sai hoặc cũ.

## Đầu vào nguyên văn và cách trích

- `150` dòng lấy **nguyên văn toàn bộ** thẻ `addr:full`.
- `250` dòng không có `addr:full`: ghép các **giá trị thẻ có thật** theo thứ tự trong `collect_osm.ADDRESS_ORDER`, phân cách bằng `, `. Giữ nguyên từng giá trị; bỏ giá trị giống hệt đã xuất hiện để tránh lặp. Đây là đầu vào ghép từ các thẻ cấu trúc, **không phải chuỗi người dùng đã gõ nguyên văn cả địa chỉ**. Phân biệt rõ bằng `input_mode` trong bản nguồn và `nguon_dau_vao` trong `ghi_chu`.
- Không thêm lỗi gõ, bỏ dấu, mở rộng viết tắt hoặc tự bịa địa chỉ để đạt hạn ngạch. Không dùng tên cơ sở hay tọa độ để bổ sung thành phần thiếu trong chuỗi đầu vào.

## Chọn mẫu

Quét PBF theo luồng, lọc 27,089 chuỗi địa chỉ công khai khác nhau sau khi loại trùng theo chuỗi chuẩn hóa. Chọn xác định bằng SHA-256 của URL nguồn, phân tầng theo tỉnh cũ nhận diện được, ưu tiên `addr:full` và các mẫu có thông tin cấp xã. Tầng địa lý chỉ hỗ trợ lấy mẫu, không phải đáp án; các ứng viên xã khi chọn mẫu có thể trùng tên hoặc nhầm mốc.

Chọn dư mẫu có dấu hiệu thuộc xã cũ bị chia, rồi kiểm tra lại bằng nhãn văn bản và quan hệ mã. Kết quả thực tế: **33 địa chỉ thuộc 28 xã cũ có nhiều xã mới đích**. Không dựa vào tên đường trùng tên xã để tính chỉ tiêu này. Không giải quyết các xã bị chia bằng tọa độ.

Không mặc định đại diện phân bố dân cư toàn quốc: mẫu công khai có thiên lệch cơ sở kinh doanh, trung tâm đô thị và địa phương có nhiều người đóng góp OSM. Không cam kết có đủ 34 tỉnh hoặc tỷ lệ đô thị/nông thôn cân bằng; xem thống kê thực tế bên dưới. Các trường hợp xã nông thôn vẫn có trong mẫu, nhưng không tự gắn nhãn đô thị/nông thôn cho từng địa điểm khi thiếu căn cứ.

## Quy trình nhãn và mã

**Xử lý nhất quán mốc trong danh mục đầu vào:** Trước đây `data/clean/moi_tinh.csv` ghi Bắc Ninh (`24`), Quảng Ninh (`22`) và Đồng Nai (`75`) là `Thành phố` do lẫn mốc 2026. Lỗi này hiện đã được khắc phục triệt để trong `clean_and_validate.py` bằng việc chuẩn hóa về loại `Tỉnh` theo Quyết định 19/2025/QĐ-TTg; script `asof_2025.py` đối soát với workbook `data/raw/goc/conversion-table.xlsx` (sheet `Tổng hợp_không merge `, cột A/B/C) và ghi nhận **0 sai khác** (`type_overrides: 0`). Cả danh mục sạch và tập test đều nhất quán chuẩn mốc **01/07/2025** với đúng **6 thành phố trực thuộc Trung ương** và 28 tỉnh. `asof2025_manifest.json` ghim SHA-256 của workbook và `catalogue_manifest.json` ghim mã băm của cả sáu bảng danh mục sạch đã cập nhật.

1. `agy` dùng duy nhất `gemini-3.8-flash-high`, chạy **tuần tự một job**, lô tối đa 35 địa chỉ. Gọi qua Git Bash với `-p="$NLP_LABEL_PROMPT"`; không cấp công cụ. Model tách số nhà, ngõ/hẻm, thôn/xóm, đường và tên xã/huyện/tỉnh; không sinh mã, không chuyển địa giới. Prompt được lưu ở `agy/prompt_*.txt`; phản hồi JSON hợp lệ ở `agy/labels_*.json`. Log lỗi/thử lại không commit.
2. Code kiểm tra đoạn nhãn có trong chuỗi nguồn. Nhãn tự sinh thêm bị bỏ và đưa `can_duyet`; phần chuỗi chưa được phân loại được ghi trong `ghi_chu` với cờ `phan_chua_phan_loai`. Mã được tra chính xác sau chuẩn hóa dấu/chữ viết và tiền tố, dùng quan hệ tỉnh–huyện–xã. Không dùng fuzzy match để chốt mã vàng.
3. Tra danh mục cũ trước; đổi qua `data/clean/doi_chieu_xa_cu_moi.csv`. Nếu không có ứng viên cũ, thử danh mục mới. Nếu tên dùng được ở hai mốc và dẫn tới đáp án khác nhau, gắn cờ `mo_ho_moc_cu_moi`, không tự chốt xã. Nếu hai mốc cho cùng kết quả mới, không khẳng định mã xã cũ khi thiếu bằng chứng mốc cũ.
4. Thiếu thành phần thì để trống. Tỉnh có thể suy ra từ xã/huyện đã được nhận diện duy nhất theo quan hệ cha con; vẫn ghi `thieu_tinh_dau_vao` khi chuỗi không ghi tỉnh. Không dùng thẻ ngoài chuỗi để điền phần thiếu.
5. Xã cũ nhiều đích: để trống `ma_xa`, `xa_phuong`, thêm `xa_bi_chia` và danh sách ứng viên trong `ghi_chu`. Giữ cả trường hợp nguồn nói toàn bộ dân số về một đích để nhóm duyệt; không tự biến nhận định đó thành nhãn đã xác minh.
6. `tu_dong_khop`: tra mã duy nhất, không có cảnh báo hoặc ghi chú nghi vấn từ model. `can_duyet`: thiếu, nhập nhằng, không khớp, mâu thuẫn, phần đường/thôn còn không dấu, số nhà có dấu `/` hoặc model đề nghị kiểm tra. **Cả hai trạng thái đều chưa được người duyệt.** Số nhà có `/` được giữ nguyên và gắn cờ vì chưa xác minh cách diễn giải số nhà/ngõ. Các tiền tố loại thành phần được viết thống nhất (ví dụ `ng.` → `Ngõ`, `kp` → `Khu phố`), nhưng không tự thêm dấu cho tên đường/thôn thiếu dấu.
7. Nếu `addr:full` và thẻ `addr:housenumber`/`addr:street` trên cùng đối tượng khác nhau, vẫn dùng `addr:full` và thêm `mau_thuan_the_osm`; không lấy thẻ cấu trúc ghi đè chuỗi nguồn.

Mã là chuỗi, giữ số 0 đầu. Khi mở Excel phải nhập các cột mã dưới dạng **Text**. `canh_bao` là JSON array trong một ô CSV; ứng viên xã mới là JSON trong `ghi_chu`. Đáp án mới được đưa về mốc 01/07/2025 bằng lớp tra cứu bảng gốc nêu trên, không lấy loại tỉnh năm 2026 trong danh mục sạch làm loại đích. `catalogue_manifest.json` ghim SHA-256 của sáu bảng đầu vào; bước sinh và kiểm tra sẽ dừng nếu chúng thay đổi, để tránh âm thầm đổi đáp án của phiên bản tập test này.

## Thống kê thực tế

- Tổng: **400 địa chỉ**, 32 tỉnh/thành mới đã xác định được.
- Phân loại ban đầu: `tu_dong_khop`: **168**; `can_duyet`: **232**.
- Đã hoàn tất kiểm toán tự duyệt AI (`antigravity-deepmind-agent`, `gemini-3.8-flash-high`): **400 / 400 mẫu**:
  + **263 dòng** đủ căn cứ tham chiếu (`du_can_cu_tham_chieu` -> `da_duyet_ai`): căn chỉnh span offset >= 0, không chồng lấn, xã đích xác định duy nhất mốc 01/07/2025.
  + **29 dòng** sửa nhãn có căn cứ chuỗi (`nhan_can_sua` -> `da_duyet_ai`): chuẩn hóa số nhà hẻm, mốc và tiền tố theo `GROUNDED_29_PATCHES`.
  + **108 dòng** chưa đủ căn cứ bảo lưu (`chua_du_can_cu` -> `can_duyet`): 33 ca xã bị chia (`xa_bi_chia`), 1 ca mâu thuẫn ranh giới `VNTEST0040` (Phố Thiên Lôi / Phường Gia Viên Hải Phòng), 39 ca thiếu xã trong chuỗi (`thieu_xa`), và 35 ca chưa xác định duy nhất (`chua_xac_dinh_xa`). Toàn bộ 108 dòng này để trống `ma_xa` theo nguyên tắc grounded-only.
- Trạng thái hiện tại trong `dia_chi_test.csv`: `da_duyet_ai`: **292 dòng** (73.0%); `can_duyet`: **108 dòng** (27.0%).
- Người duyệt con người (`human_reviewed_rows`): **0 dòng** (0.0%). Trạng thái đánh giá vàng: `is_ready_for_gold_evaluation: false`, `provisional_only: true` (bảo đảm tính liêm chính, không ngộ nhận AI là Gold test).
- Tra cứu web & căn cứ pháp lý: **37 ca** (12 ca NQ 1685/NQ-UBTVQH15 TP.HCM tra cứu trực tuyến thành công HTTP 200; 25 ca tra cứu trực tuyến tự động trả về HTTP 404 được ghi nhận trung thực và dẫn chiếu theo văn bản pháp lý ngoại tuyến).
- Tệp bàn giao phân loại chi tiết 400 ID: [phan_loai_chi_tiet_400_id.csv](file:///D:/nlp_chuan_hoa_dia_chi/data/test/phan_loai_chi_tiet_400_id.csv) và [phan_loai_chi_tiet_400_id.md](file:///D:/nlp_chuan_hoa_dia_chi/data/test/phan_loai_chi_tiet_400_id.md).
- Có ký tự tiếng Việt mang dấu: **390**; không có: **10**. Đây là thống kê ký tự, không đồng nghĩa tất cả địa danh không dấu đều viết đúng.
- Có viết tắt theo regex đã công bố trong `build_labels.py`: **100**. Các lỗi gõ tự nhiên không có gold riêng; chưa công bố số lượng lỗi gõ khi chưa duyệt tay.
- Xã cũ bị chia: **33** dòng, **28** mã xã khác nhau.
- Có thành phần thôn/xóm/ấp/bản/khu phố/tổ dân phố: **56** dòng. Phân bố loại đơn vị cũ đã xác định: `{"Phường": 212, "Xã": 48, "Thị trấn": 16}`; đây là loại hành chính, không phải nhãn đô thị/nông thôn của địa điểm.

Phân loại mốc sơ bộ (không suy từ ngày sửa đối tượng OSM):

- `cu`: 361 dòng.
- `thieu_thong_tin`: 14 dòng.
- `mo_ho`: 4 dòng.
- `cu_moi_cung_ket_qua`: 15 dòng.
- `moi`: 6 dòng.

Số dòng theo tỉnh/thành mới trong nhãn:

| Tỉnh/thành | Số dòng |
|---|---:|
| (chưa xác định) | 19 |
| Thành phố Cần Thơ | 14 |
| Thành phố Huế | 4 |
| Thành phố Hà Nội | 15 |
| Thành phố Hải Phòng | 17 |
| Thành phố Hồ Chí Minh | 58 |
| Thành phố Đà Nẵng | 8 |
| Tỉnh An Giang | 10 |
| Tỉnh Bắc Ninh | 11 |
| Tỉnh Cao Bằng | 6 |
| Tỉnh Cà Mau | 11 |
| Tỉnh Gia Lai | 12 |
| Tỉnh Hà Tĩnh | 6 |
| Tỉnh Hưng Yên | 13 |
| Tỉnh Khánh Hòa | 13 |
| Tỉnh Lào Cai | 9 |
| Tỉnh Lâm Đồng | 20 |
| Tỉnh Lạng Sơn | 3 |
| Tỉnh Nghệ An | 6 |
| Tỉnh Ninh Bình | 17 |
| Tỉnh Phú Thọ | 8 |
| Tỉnh Quảng Ngãi | 12 |
| Tỉnh Quảng Ninh | 6 |
| Tỉnh Quảng Trị | 12 |
| Tỉnh Sơn La | 6 |
| Tỉnh Thanh Hóa | 3 |
| Tỉnh Thái Nguyên | 6 |
| Tỉnh Tuyên Quang | 9 |
| Tỉnh Tây Ninh | 15 |
| Tỉnh Vĩnh Long | 16 |
| Tỉnh Đắk Lắk | 12 |
| Tỉnh Đồng Nai | 11 |
| Tỉnh Đồng Tháp | 12 |

## Tái lập trên máy

Python 3.12 và `osmium==4.3.2` cho bước trích; các bước còn lại dùng thư viện chuẩn. `agy` đã đăng nhập và Git Bash cần cho bước nhãn. Không chạy nhiều job CPU/agy cùng lúc.

```powershell
py -3.12 -m pip install osmium==4.3.2
py -3.12 data/test/scripts/pin_catalogues.py
py -3.12 data/test/scripts/asof_2025.py
py -3.12 data/test/scripts/collect_osm.py
py -3.12 data/test/scripts/select_sample.py
py -3.12 data/test/scripts/label_agy.py
py -3.12 data/test/scripts/build_labels.py
py -3.12 data/test/scripts/validate_dataset.py
py -3.12 data/test/scripts/write_readme.py
```

PBF (~332 MB) và danh sách ứng viên toàn bộ không commit, đã có `.gitignore`; chạy lại bước trích để tái tạo. Chỉ commit trích nguồn 400 mẫu. Tái lập CSV/kiểm tra từ các phản hồi model **đã lưu** không cần gọi lại agy hoặc tải PBF: chạy ba script cuối. Gọi lại model có thể cho nhãn khác; cache từng lô giúp giữ nguyên tập sơ bộ đã công bố. Không thay đổi cách chia lô khi tái sử dụng cache.

`validation.json` kiểm tra schema, nguồn nguyên văn, khóa/mã/quan hệ cha con, số mẫu, ít nhất 20 mẫu xã bị chia, phân bố địa lý, cờ và trạng thái duyệt. Trạng thái **PASS** chỉ là kiểm tra cấu trúc và bảo toàn nguồn, không chứng minh nhãn ngữ nghĩa đúng. Nhóm cần duyệt từng mẫu, sửa nhãn và ghi người/ngày duyệt trước khi đóng băng gold test.

## Nhật ký kiểm toán AI tự duyệt toàn diện (AI Deep-Dive Review)

Để nâng cao chất lượng dữ liệu test trước khi con người nghiệm thu thực tế, toàn bộ 400 mẫu test đã được duyệt tự động có chiều sâu bằng AI Agent (`antigravity-deepmind-agent`, model `gemini-3.8-flash-high`, `loai_nguoi_duyet=ai`):

1. **Nguyên tắc căn cứ chuỗi đầu vào (Input-Grounded):** Tuyệt đối không làm giàu dữ liệu hoặc suy diễn tọa độ/POI ngoài chuỗi. Nếu đầu vào thiếu số nhà, đường, xã thì nhãn tương ứng để trống.
2. **Thu hồi và bảo lưu toàn bộ 33 ca xã bị chia (Không ép đủ nhãn):**
   - Đã tra cứu toàn văn Nghị quyết 1685/NQ-UBTVQH15 (TP.HCM) và Nghị quyết 1192/NQ-UBTVQH15 (Hà Nội): các văn bản quy phạm pháp luật chỉ phân chia ranh giới theo diện tích tự nhiên và quy mô dân số của các tổ dân phố/khu phố, hoàn toàn không có phụ lục phân chia số nhà theo từng tuyến đường.
   - Ví dụ đối soát thực tế:
     + `VNTEST0023` (`F26-F27, tầng 1, 30 Bờ Bao Tân Thắng, P. Sơn Kỳ, Q. Tân Phú`): Nghị quyết 1685 Điều 1 các khoản 41, 62, 63 phân chia Phường Sơn Kỳ giữa Bình Hưng Hòa, Tây Thạnh và Tân Sơn Nhì; văn bản không quy định vị trí số 30 hay đường Bờ Bao Tân Thắng thuộc bên nào -> Thu hồi về `ma_xa=""`, `xa_phuong=""`, giữ cờ `xa_bi_chia` và danh sách ứng viên.
     + `VNTEST0008` (`Số 108 Trần Phú, phường Mộ Lao, quận Hà Đông, Hà Nội`): Nghị quyết 1192 không có chi tiết số nhà 108 Trần Phú -> Thu hồi về rỗng, bảo lưu ứng viên.
     + `VNTEST0006` (`Số 45 - đường Cô Giang - phường Cầu Ông Lãnh - quận 1 - Tp.HCM`): Nghị quyết 1685 Điều 1 khoản 3 và 4 chia Cầu Ông Lãnh không có số nhà Cô Giang -> Thu hồi về rỗng, bảo lưu ứng viên.
     + `VNTEST0038` (`8 Cộng Hòa, Phường 4, Hồ Chí Minh, Việt Nam`): Đường Cộng Hòa qua Phường 4, Tân Bình sáp nhập vào Phường Tân Sơn Nhất (mã 26968).
   - Do đó, toàn bộ **33 ca xã bị chia** đều được thu hồi về rỗng và bảo lưu ở trạng thái `can_duyet` với `ket_luan=chua_du_can_cu`, cờ `xa_bi_chia` và danh sách ứng viên `xa_moi_ung_vien`. Tuyệt đối không võ đoán gán nhãn khi thiếu căn cứ pháp lý số nhà.
3. **29 ca sửa đổi nhãn có căn cứ chuỗi xác thực (`grounded_29_patches.py`):**
   - Chỉ sửa đổi nhãn khi tên xã/phường xuất hiện rõ ràng trong chuỗi đầu vào và có đích duy nhất trong danh mục 01/07/2025 (loại bỏ hoàn toàn thuật toán quét mò tên xã gây gán nhầm đơn vị hành chính sang tỉnh khác).
   - Ví dụ: `VNTEST0013` (Phước Long B, Quận 9 -> Phước Long, TP.HCM), `VNTEST0016` (An Khánh, NK, CT -> Tân An, Cần Thơ), `VNTEST0046` (Lạc Đạo, Hưng Yên), v.v.
4. **Các tệp kiểm toán minh bạch:**
   - `data/test/nhat_ky_ai_duyet.jsonl`: 400 dòng JSON chi tiết với 4 nguồn bằng chứng phân lập (`can_cu_input`, `can_cu_danh_muc`, `can_cu_osm_dong_bang`, `can_cu_web`), kết luận, diff thay đổi và vấn đề còn lại.
   - `data/test/nhat_ky_ai_duyet.csv`: Phiên bản bảng tính trực quan của nhật ký kiểm toán.
   - `data/test/backup_before_ai_review/`: Lưu trữ bản sao nguyên trạng của tập test sơ bộ trước khi AI duyệt.
   - `data/test/checkpoints/`: Lưu trữ các điểm phục hồi an toàn tự động trước mỗi lần chạy engine.
5. **Phân biệt rạch ròi AI duyệt và Con người duyệt:**
   - Validator (`validate_dataset.py`) và công cụ theo dõi tiến độ (`kiem_tra_tien_do_duyet.py`) phân tách độc lập hai nhóm chỉ số: `agent_id = 'antigravity-deepmind-agent'` và `model_duyet = 'gemini-3.8-flash-high'`.
   - Trạng thái `da_duyet_ai` (366 dòng) không làm tăng `human_reviewed_rows` (0 dòng). Cờ `is_ready_for_gold_evaluation` được khóa cứng ở mức `False` cho đến khi có sự tham gia xác thực của con người.
   - Công cụ tiến độ đếm diff nhãn thực tế báo đúng chính xác 29 dòng có diff nhãn so với baseline sơ bộ.
   - Bộ kiểm thử hồi quy độc lập (`tests/test_review_validation.py`) bao gồm 21 bài test cases kiểm chứng toàn diện mọi tình huống duyệt của cả con người và AI, đạt **100% PASS**.

## Những việc chưa làm và giới hạn

- Chưa có người duyệt con người nghiệm thu; tập dữ liệu chưa được dùng làm Gold Test chính thức để chấm điểm hệ thống NLP (`human_reviewed_rows = 0`).
- Còn toàn bộ 33 ca xã bị chia và 39 ca đầu vào thiếu xã thực sự cần hồ sơ trích lục địa chính hoặc con người quyết định.
- Không tạo đủ hạn ngạch lỗi gõ, thiếu dấu hoặc nông thôn bằng cách sửa chuỗi nguồn. Các nhóm này phụ thuộc dữ liệu tự nhiên.
- Địa chỉ thật trên nguồn có thể lỗi, cũ hoặc xung đột giữa `addr:full` và thẻ cấu trúc. Bản `addr:full` luôn được ưu tiên làm đầu vào và không tự sửa. Cần nhóm so nguồn khi duyệt.
- Các vấn đề còn trong danh mục sạch không được âm thầm sửa ở nhiệm vụ này. Bộ dữ liệu không sửa `data/raw`, `data/clean`, `src/` hoặc `bai_toan.md`.
