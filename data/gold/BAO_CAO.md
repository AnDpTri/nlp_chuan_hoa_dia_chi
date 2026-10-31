# BÁO CÁO DỰNG CÔNG CỤ NHÃN ỨNG VIÊN — 30/10/2026

**TRẠNG THÁI: CHƯA CÓ GOLD.** Chưa có hai bộ AI độc lập gán nhãn thật, chưa có phán quyết con người, chưa kiểm sai số thật. Mọi tệp ở đây chỉ là ứng viên, quy ước nháp hoặc dữ liệu kiểm công cụ.

## 1. Phạm vi và chứng cứ

- Worktree ghi duy nhất: `D:\nlp_gold`, nhánh `data/gold-20261030`. Repo refactor và các nguồn tham chiếu chỉ đọc.
- Test 400 **chỉ đọc cột** `id,dau_vao,nguon` để loại trừ; không đọc nhãn, trạng thái duyệt, thống kê điểm hay kết quả inference test.
- OSM source: `D:\nlp_chuan_hoa_dia_chi\data\test\goc\osm_public_candidates.jsonl`; dữ liệu `input_mode=structured_tags_joined` có cấu trúc thẻ nhưng thẻ không được gửi cho AI trong prompt.
- Hàm fingerprint `normalize, masked_family, osm_identity` nạp **read-only** từ `D:\nlp_chuan_hoa_dia_chi\data\audit\audit_du_lieu.py`; matcher hành chính `src.danh_muc.DanhMuc` cũng chỉ đọc.

## 2. Chọn 800 mẫu ứng viên mới — số liệu đã đo

- Tổng bản ghi nguồn OSM đã quét: **31,374**.
- Loại do nguồn/chuỗi thiếu: **1**.
- Loại vì đụng ít nhất một khóa nguồn đã dùng: **6,007**.
- Loại trùng khóa với ứng viên khác bên trong pool: **12,204** bản ghi.
- Đủ điều kiện sau loại trừ và loại trùng nội bộ: **13,162**.
- Lấy mẫu ngẫu nhiên seed **20261030** bằng phân bổ tỷ lệ Hamilton theo tầng `(nhom_tinh, nhom_dac_diem, input_mode)`: **800** dòng.
- Số tầng có pool: **359**.
- SHA-256 `mau_ung_vien.csv`: **`2d0284b46f6a082efd8fcf020d72bfa1e0b31e0e11b3f7cf5cf5c63ca9c3006b`** (UTF-8 BOM, CRLF, ID `UNGVIEN_####`).

### Số lượt dính theo từng khóa (không cộng trực tiếp)

- Chuỗi chuẩn hóa: **2,730**.
- Cùng OSM identity: **2,400**.
- Cùng khóa họ che số nhà: **5,991**.
- Một ứng viên có thể trùng nhiều khóa/nhiều nguồn; tổng theo khóa hoặc theo nguồn không bằng số bản ghi bị loại.

| Nhóm dữ liệu loại trừ | Dòng địa chỉ đã đọc | Trùng text | Trùng OSM ID | Trùng họ che số nhà |
|---|---:|---:|---:|---:|
| train | 4564 | 1806 | 1600 | 4879 |
| dev | 1136 | 467 | 400 | 2331 |
| bo_sung_v1 | 10821 | 0 | 0 | 10 |
| bo_sung_v2 | 9000 | 0 | 0 | 8 |
| bo_sung_v3 | 397 | 0 | 0 | 0 |
| release_ai | 6204 | 0 | 0 | 8 |
| test_exclusion_ONLY_id_dau_vao_nguon | 400 | 457 | 400 | 692 |

### Kiểm tra rò rỉ độc lập

- `kiem_ro_ri_doc_lap.py`: **PASS**, đã quét lại toàn bộ thư mục con (rglob) của v1/v2, không chỉ file cấp đầu. Mỗi tập đối chiếu ba khóa riêng; cả ba giao đều **0 trên 800 mẫu cuối**.
- Test trong verifier cũng chỉ dùng ba cột được phép; file báo cáo `BAO_CAO_RO_RI_DOC_LAP.json` ghi số dòng đọc thực tế theo từng nguồn.

### Phân bố mẫu theo chiều tầng

| Kiểu đầu vào (ưu tiên phân loại) | Số mẫu | Tỷ lệ |
|---|---:|---:|
| co_dau_khac | 418 | 52.250% |
| thieu_thanh_phan | 345 | 43.125% |
| khong_dau | 26 | 3.250% |
| viet_tat | 11 | 1.375% |

| input_mode OSM | Số mẫu | Tỷ lệ |
|---|---:|---:|
| structured_tags_joined | 792 | 99.000% |
| addr:full | 8 | 1.000% |

| Nhóm địa danh tỉnh **suy từ thẻ nguồn (chỉ dùng phân tầng)** | Số mẫu | Tỷ lệ |
|---|---:|---:|
| khong_co_the_tinh | 419 | 52.375% |
| ha noi | 71 | 8.875% |
| thanh pho ho chi minh | 38 | 4.750% |
| bac ninh | 35 | 4.375% |
| ho chi minh | 35 | 4.375% |
| thanh pho ha noi | 32 | 4.000% |
| ho chi minh city | 22 | 2.750% |
| da nang | 12 | 1.500% |
| can tho | 11 | 1.375% |
| lam dong | 10 | 1.250% |
| khanh hoa | 5 | 0.625% |
| quang nam | 5 | 0.625% |
| binh duong | 4 | 0.500% |
| dong nai | 4 | 0.500% |
| hanoi | 4 | 0.500% |
| hung yen | 4 | 0.500% |
| tay ninh | 4 | 0.500% |
| tinh dong nai | 4 | 0.500% |
| an giang | 3 | 0.375% |
| ba ria vung tau | 3 | 0.375% |
| ben tre | 3 | 0.375% |
| hai phong | 3 | 0.375% |
| hoi an | 3 | 0.375% |
| long an | 3 | 0.375% |
| binh dinh | 2 | 0.250% |
| binh thuan | 2 | 0.250% |
| dak lak | 2 | 0.250% |
| dong thap | 2 | 0.250% |
| gia lai | 2 | 0.250% |
| hue | 2 | 0.250% |
| kien giang | 2 | 0.250% |
| my tho | 2 | 0.250% |
| nghe an | 2 | 0.250% |
| ninh binh | 2 | 0.250% |
| quang binh | 2 | 0.250% |
| thua thien hue | 2 | 0.250% |
| tien giang | 2 | 0.250% |
| tp ho chi minh | 2 | 0.250% |
| ba ria | 1 | 0.125% |
| binh phuoc | 1 | 0.125% |
| dalat | 1 | 0.125% |
| danang | 1 | 0.125% |
| di an binh duong | 1 | 0.125% |
| ha giang | 1 | 0.125% |
| ha tinh | 1 | 0.125% |
| hai duong | 1 | 0.125% |
| hcmc | 1 | 0.125% |
| hoa binh | 1 | 0.125% |
| kon tum | 1 | 0.125% |
| lao cai | 1 | 0.125% |
| nam dinh | 1 | 0.125% |
| nha trang | 1 | 0.125% |
| ninh thuan | 1 | 0.125% |
| phan thiet | 1 | 0.125% |
| phu tho | 1 | 0.125% |
| phu yen | 1 | 0.125% |
| quang ngai | 1 | 0.125% |
| quang ninh | 1 | 0.125% |
| thai nguyen | 1 | 0.125% |
| thanh hoa | 1 | 0.125% |
| thanh pho da nang | 1 | 0.125% |
| thanh pho hai phong | 1 | 0.125% |
| thanh pho thu duc | 1 | 0.125% |
| tinh binh duong | 1 | 0.125% |
| tinh khanh hoa | 1 | 0.125% |
| tinh lam dong | 1 | 0.125% |
| tinh long an | 1 | 0.125% |
| tinh tay ninh | 1 | 0.125% |
| tp hcm | 1 | 0.125% |
| viet nam | 1 | 0.125% |
| vietnam | 1 | 0.125% |
| vinh long | 1 | 0.125% |
| vung tau | 1 | 0.125% |
| 05113628339 | 0 | 0.000% |
| 10000 | 0 | 0.000% |
| 12 | 0 | 0.000% |
| abc | 0 | 0.000% |
| an khanh | 0 | 0.000% |
| an thoi | 0 | 0.000% |
| ap 3 phuoc kien nha | 0 | 0.000% |
| apollotechnology | 0 | 0.000% |
| bac giang | 0 | 0.000% |
| bavet | 0 | 0.000% |
| ben | 0 | 0.000% |
| binh chanh | 0 | 0.000% |
| br vt | 0 | 0.000% |
| buon ma thuot | 0 | 0.000% |
| ca mau | 0 | 0.000% |
| cai rong van don | 0 | 0.000% |
| cao bang | 0 | 0.000% |
| cat ba town | 0 | 0.000% |
| da lat | 0 | 0.000% |
| da nanag | 0 | 0.000% |
| da nang city | 0 | 0.000% |
| dac khu cat hai | 0 | 0.000% |
| dac lak | 0 | 0.000% |
| dak nong | 0 | 0.000% |
| daklak | 0 | 0.000% |
| dawsk lak | 0 | 0.000% |
| di linh | 0 | 0.000% |
| dien bien | 0 | 0.000% |
| district 1 | 0 | 0.000% |
| dong anh | 0 | 0.000% |
| dong ha | 0 | 0.000% |
| dong hoi | 0 | 0.000% |
| dong van | 0 | 0.000% |
| duong dong | 0 | 0.000% |
| ea drang | 0 | 0.000% |
| ha long | 0 | 0.000% |
| ha nam | 0 | 0.000% |
| ha noi viet nam | 0 | 0.000% |
| ha tinh vietnam | 0 | 0.000% |
| hai phong city | 0 | 0.000% |
| haiphong | 0 | 0.000% |
| ham thuan nam | 0 | 0.000% |
| ham tien mui ne | 0 | 0.000% |
| hau giang | 0 | 0.000% |
| hcm | 0 | 0.000% |
| hn | 0 | 0.000% |
| ho chi minh ciry | 0 | 0.000% |
| ho chinh minh | 0 | 0.000% |
| hoa binh province | 0 | 0.000% |
| hoang hoa | 0 | 0.000% |
| hoc mon | 0 | 0.000% |
| hochiminh cit | 0 | 0.000% |
| hochiminh city | 0 | 0.000% |
| hon dat | 0 | 0.000% |
| hue thua thien hue | 0 | 0.000% |
| hung yen province | 0 | 0.000% |
| khanh khoa | 0 | 0.000% |
| kien giang vietnam | 0 | 0.000% |
| kieng gian | 0 | 0.000% |
| lai vung | 0 | 0.000% |
| laocai | 0 | 0.000% |
| mai chau | 0 | 0.000% |
| mui ne | 0 | 0.000% |
| mui ne ham tien | 0 | 0.000% |
| mui ne phan thiet | 0 | 0.000% |
| nha be | 0 | 0.000% |
| ninh hoa | 0 | 0.000% |
| ninh kieu can tho | 0 | 0.000% |
| phan dinh phung thai nguyen | 0 | 0.000% |
| phan rang thap cham | 0 | 0.000% |
| pho ha noi | 0 | 0.000% |
| pho to vinh dien | 0 | 0.000% |
| phong nha | 0 | 0.000% |
| phu hoi | 0 | 0.000% |
| phu ly | 0 | 0.000% |
| phu nhuan | 0 | 0.000% |
| phu quoc | 0 | 0.000% |
| phu quoc island | 0 | 0.000% |
| phuong 1 | 0 | 0.000% |
| phuong 17 | 0 | 0.000% |
| phuong 2 | 0 | 0.000% |
| phuong 25 | 0 | 0.000% |
| phuong 3 | 0 | 0.000% |
| phuong 6 | 0 | 0.000% |
| phuong 7 | 0 | 0.000% |
| phuong 7 quan phu nhuan | 0 | 0.000% |
| phuong 8 | 0 | 0.000% |
| phuong an lac | 0 | 0.000% |
| phuong bien giang | 0 | 0.000% |
| phuong co nhue 1 | 0 | 0.000% |
| phuong dai mo | 0 | 0.000% |
| phuong duc thang | 0 | 0.000% |
| phuong giang bien | 0 | 0.000% |
| phuong hoa xuan | 0 | 0.000% |
| phuong long thanh my | 0 | 0.000% |
| phuong pham ngu lao q1 | 0 | 0.000% |
| phuong phu thuong | 0 | 0.000% |
| phuong quang an | 0 | 0.000% |
| phuong rach soi | 0 | 0.000% |
| phuong sa dec | 0 | 0.000% |
| phuong tan chanh hiep | 0 | 0.000% |
| phuong tan khanh | 0 | 0.000% |
| phuong tan quy | 0 | 0.000% |
| phuong tan thoi hiep | 0 | 0.000% |
| phuong tan thoi nhat | 0 | 0.000% |
| phuong thao dien | 0 | 0.000% |
| phuong vinh hung | 0 | 0.000% |
| phuong xuan phuong | 0 | 0.000% |
| quan 1 | 0 | 0.000% |
| quan 3 | 0 | 0.000% |
| quang nam province | 0 | 0.000% |
| quang tri | 0 | 0.000% |
| quy nhon | 0 | 0.000% |
| rach gia | 0 | 0.000% |
| sa pa | 0 | 0.000% |
| sai gon | 0 | 0.000% |
| saigon | 0 | 0.000% |
| soc trang | 0 | 0.000% |
| t lam dong | 0 | 0.000% |
| t p hcm | 0 | 0.000% |
| t son la | 0 | 0.000% |
| t vinh long | 0 | 0.000% |
| tan thanh | 0 | 0.000% |
| tay ninh provine | 0 | 0.000% |
| thai binh | 0 | 0.000% |
| thai ngyen | 0 | 0.000% |
| thanh pho ba ria | 0 | 0.000% |
| thanh pho bac ninh | 0 | 0.000% |
| thanh pho can tho | 0 | 0.000% |
| thanh pho ho chi minhminh | 0 | 0.000% |
| thanh pho hue | 0 | 0.000% |
| thanh pho phu quoc | 0 | 0.000% |
| thanh pho vung tau | 0 | 0.000% |
| thao dien | 0 | 0.000% |
| thi tran di linh | 0 | 0.000% |
| thi tran hau nghia | 0 | 0.000% |
| thi tran lac duong | 0 | 0.000% |
| thot not | 0 | 0.000% |
| thu dau mot | 0 | 0.000% |
| thu duc | 0 | 0.000% |
| thu duc ho chi minh | 0 | 0.000% |
| tien yen | 0 | 0.000% |
| tinh | 0 | 0.000% |
| tinh an giang | 0 | 0.000% |
| tinh ba ria vung tau | 0 | 0.000% |
| tinh bac ninh | 0 | 0.000% |
| tinh ben tre | 0 | 0.000% |
| tinh binh dinh | 0 | 0.000% |
| tinh ca mau | 0 | 0.000% |
| tinh dak lak | 0 | 0.000% |
| tinh gia lai | 0 | 0.000% |
| tinh hung yen | 0 | 0.000% |
| tinh kon tum | 0 | 0.000% |
| tinh lao cai | 0 | 0.000% |
| tinh phu tho | 0 | 0.000% |
| tinh quang ngai | 0 | 0.000% |
| tinh thai binh | 0 | 0.000% |
| tinh thanh hoa | 0 | 0.000% |
| tinh thua thien hue | 0 | 0.000% |
| tinh tra vinh | 0 | 0.000% |
| tinh vinh long | 0 | 0.000% |
| tp ben tre | 0 | 0.000% |
| tp buon ma thuot | 0 | 0.000% |
| tp can tho | 0 | 0.000% |
| tp cao lanh | 0 | 0.000% |
| tp da nang | 0 | 0.000% |
| tp dong nai | 0 | 0.000% |
| tp ha noi | 0 | 0.000% |
| tp ha tinh | 0 | 0.000% |
| tp ho chinh minh | 0 | 0.000% |
| tphcm | 0 | 0.000% |
| tra vinh | 0 | 0.000% |
| trang bom | 0 | 0.000% |
| tuy hoa | 0 | 0.000% |
| tuyen quang | 0 | 0.000% |
| vie | 0 | 0.000% |
| vinh phuc | 0 | 0.000% |
| vn | 0 | 0.000% |
| vung tau baria | 0 | 0.000% |
| xa go cong dong | 0 | 0.000% |
| xa hoa long | 0 | 0.000% |
| xa hoang quy | 0 | 0.000% |
| xa lai vung | 0 | 0.000% |
| xa tan xa | 0 | 0.000% |
| xa xuan thoi son | 0 | 0.000% |
| yen bai | 0 | 0.000% |

**Giới hạn tầng:** nhãn nhóm tỉnh được suy từ các thẻ OSM `addr:province/state/city`, **không được xác thực là tỉnh hành chính**; có thể là tên thành phố cấp dưới, biến thể viết tắt hoặc thiếu thẻ. Quy tắc loại input ưu tiên không dấu → viết tắt → thiếu thành phần → còn lại; đây là **một phân lớp ưu tiên, không phải các cờ độc lập**. Mẫu đang rất lệch về `structured_tags_joined`; không đại diện cho phân bố địa chỉ người dùng gõ tự do. Cần người quyết cơ cấu và lấy mẫu mới nếu cần phân tầng cân bằng.

### Bảng đầy đủ 359 tầng (đếm pool/số chọn/tỷ trọng trên 800)

| Nhóm tỉnh nguồn | Nhóm đặc điểm | input_mode | Pool | Chọn | Tỷ lệ % |
|---|---|---|---:|---:|---:|
| 05113628339 | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |
| 10000 | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |
| 12 | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |
| abc | co_dau_khac | structured_tags_joined | 2 | 0 | 0.000 |
| an giang | co_dau_khac | structured_tags_joined | 41 | 3 | 0.375 |
| an giang | khong_dau | structured_tags_joined | 2 | 0 | 0.000 |
| an khanh | thieu_thanh_phan | structured_tags_joined | 2 | 0 | 0.000 |
| an thoi | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |
| ap 3 phuoc kien nha | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |
| apollotechnology | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |
| ba ria | co_dau_khac | structured_tags_joined | 5 | 1 | 0.125 |
| ba ria | thieu_thanh_phan | structured_tags_joined | 1 | 0 | 0.000 |
| ba ria vung tau | co_dau_khac | structured_tags_joined | 52 | 3 | 0.375 |
| ba ria vung tau | khong_dau | structured_tags_joined | 3 | 0 | 0.000 |
| ba ria vung tau | thieu_thanh_phan | structured_tags_joined | 1 | 0 | 0.000 |
| ba ria vung tau | viet_tat | structured_tags_joined | 1 | 0 | 0.000 |
| bac giang | co_dau_khac | structured_tags_joined | 2 | 0 | 0.000 |
| bac ninh | co_dau_khac | structured_tags_joined | 579 | 35 | 4.375 |
| bac ninh | thieu_thanh_phan | structured_tags_joined | 1 | 0 | 0.000 |
| bac ninh | viet_tat | structured_tags_joined | 1 | 0 | 0.000 |
| bavet | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |
| bavet | khong_dau | structured_tags_joined | 1 | 0 | 0.000 |
| ben | co_dau_khac | structured_tags_joined | 3 | 0 | 0.000 |
| ben tre | co_dau_khac | structured_tags_joined | 52 | 3 | 0.375 |
| ben tre | thieu_thanh_phan | structured_tags_joined | 1 | 0 | 0.000 |
| binh chanh | viet_tat | structured_tags_joined | 1 | 0 | 0.000 |
| binh dinh | co_dau_khac | structured_tags_joined | 31 | 2 | 0.250 |
| binh duong | co_dau_khac | structured_tags_joined | 64 | 4 | 0.500 |
| binh duong | khong_dau | structured_tags_joined | 1 | 0 | 0.000 |
| binh duong | viet_tat | structured_tags_joined | 4 | 0 | 0.000 |
| binh phuoc | co_dau_khac | structured_tags_joined | 7 | 1 | 0.125 |
| binh thuan | co_dau_khac | structured_tags_joined | 34 | 2 | 0.250 |
| br vt | viet_tat | structured_tags_joined | 1 | 0 | 0.000 |
| buon ma thuot | co_dau_khac | structured_tags_joined | 2 | 0 | 0.000 |
| ca mau | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |
| cai rong van don | khong_dau | structured_tags_joined | 1 | 0 | 0.000 |
| can tho | co_dau_khac | addr:full | 2 | 0 | 0.000 |
| can tho | co_dau_khac | structured_tags_joined | 169 | 10 | 1.250 |
| can tho | khong_dau | structured_tags_joined | 1 | 0 | 0.000 |
| can tho | thieu_thanh_phan | structured_tags_joined | 6 | 1 | 0.125 |
| can tho | viet_tat | structured_tags_joined | 4 | 0 | 0.000 |
| cao bang | co_dau_khac | structured_tags_joined | 2 | 0 | 0.000 |
| cat ba town | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |
| da lat | co_dau_khac | structured_tags_joined | 4 | 0 | 0.000 |
| da lat | thieu_thanh_phan | structured_tags_joined | 2 | 0 | 0.000 |
| da nanag | khong_dau | structured_tags_joined | 1 | 0 | 0.000 |
| da nang | co_dau_khac | structured_tags_joined | 201 | 12 | 1.500 |
| da nang | khong_dau | structured_tags_joined | 3 | 0 | 0.000 |
| da nang | thieu_thanh_phan | structured_tags_joined | 2 | 0 | 0.000 |
| da nang | viet_tat | structured_tags_joined | 1 | 0 | 0.000 |
| da nang city | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |
| dac khu cat hai | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |
| dac lak | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |
| dak lak | co_dau_khac | structured_tags_joined | 24 | 2 | 0.250 |
| dak nong | co_dau_khac | structured_tags_joined | 2 | 0 | 0.000 |
| daklak | co_dau_khac | structured_tags_joined | 3 | 0 | 0.000 |
| dalat | co_dau_khac | structured_tags_joined | 6 | 1 | 0.125 |
| dalat | khong_dau | structured_tags_joined | 1 | 0 | 0.000 |
| danang | co_dau_khac | structured_tags_joined | 19 | 1 | 0.125 |
| danang | khong_dau | structured_tags_joined | 2 | 0 | 0.000 |
| danang | thieu_thanh_phan | structured_tags_joined | 1 | 0 | 0.000 |
| dawsk lak | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |
| di an binh duong | co_dau_khac | structured_tags_joined | 6 | 1 | 0.125 |
| di linh | khong_dau | structured_tags_joined | 1 | 0 | 0.000 |
| dien bien | co_dau_khac | structured_tags_joined | 2 | 0 | 0.000 |
| district 1 | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |
| dong anh | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |
| dong ha | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |
| dong hoi | co_dau_khac | structured_tags_joined | 4 | 0 | 0.000 |
| dong hoi | thieu_thanh_phan | structured_tags_joined | 1 | 0 | 0.000 |
| dong nai | co_dau_khac | structured_tags_joined | 56 | 4 | 0.500 |
| dong nai | viet_tat | structured_tags_joined | 1 | 0 | 0.000 |
| dong thap | co_dau_khac | structured_tags_joined | 34 | 2 | 0.250 |
| dong van | khong_dau | structured_tags_joined | 1 | 0 | 0.000 |
| duong dong | co_dau_khac | structured_tags_joined | 2 | 0 | 0.000 |
| duong dong | viet_tat | structured_tags_joined | 1 | 0 | 0.000 |
| ea drang | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |
| gia lai | co_dau_khac | structured_tags_joined | 33 | 2 | 0.250 |
| gia lai | khong_dau | structured_tags_joined | 1 | 0 | 0.000 |
| ha giang | co_dau_khac | structured_tags_joined | 5 | 1 | 0.125 |
| ha giang | khong_dau | structured_tags_joined | 1 | 0 | 0.000 |
| ha long | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |
| ha nam | co_dau_khac | structured_tags_joined | 3 | 0 | 0.000 |
| ha noi | co_dau_khac | structured_tags_joined | 1139 | 69 | 8.625 |
| ha noi | khong_dau | structured_tags_joined | 2 | 0 | 0.000 |
| ha noi | thieu_thanh_phan | structured_tags_joined | 13 | 1 | 0.125 |
| ha noi | viet_tat | structured_tags_joined | 15 | 1 | 0.125 |
| ha noi viet nam | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |
| ha tinh | co_dau_khac | structured_tags_joined | 12 | 1 | 0.125 |
| ha tinh vietnam | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |
| hai duong | co_dau_khac | structured_tags_joined | 8 | 1 | 0.125 |
| hai phong | co_dau_khac | structured_tags_joined | 51 | 3 | 0.375 |
| hai phong | thieu_thanh_phan | structured_tags_joined | 1 | 0 | 0.000 |
| hai phong | viet_tat | structured_tags_joined | 2 | 0 | 0.000 |
| hai phong city | khong_dau | structured_tags_joined | 1 | 0 | 0.000 |
| haiphong | co_dau_khac | structured_tags_joined | 3 | 0 | 0.000 |
| haiphong | khong_dau | structured_tags_joined | 1 | 0 | 0.000 |
| ham thuan nam | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |
| ham tien mui ne | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |
| hanoi | co_dau_khac | structured_tags_joined | 42 | 3 | 0.375 |
| hanoi | khong_dau | structured_tags_joined | 9 | 1 | 0.125 |
| hanoi | viet_tat | structured_tags_joined | 1 | 0 | 0.000 |
| hau giang | co_dau_khac | structured_tags_joined | 2 | 0 | 0.000 |
| hcm | viet_tat | structured_tags_joined | 1 | 0 | 0.000 |
| hcmc | co_dau_khac | structured_tags_joined | 8 | 1 | 0.125 |
| hcmc | khong_dau | structured_tags_joined | 1 | 0 | 0.000 |
| hn | viet_tat | structured_tags_joined | 1 | 0 | 0.000 |
| ho chi minh | co_dau_khac | structured_tags_joined | 558 | 34 | 4.250 |
| ho chi minh | khong_dau | structured_tags_joined | 1 | 0 | 0.000 |
| ho chi minh | thieu_thanh_phan | structured_tags_joined | 3 | 0 | 0.000 |
| ho chi minh | viet_tat | structured_tags_joined | 11 | 1 | 0.125 |
| ho chi minh ciry | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |
| ho chi minh city | co_dau_khac | structured_tags_joined | 325 | 20 | 2.500 |
| ho chi minh city | khong_dau | structured_tags_joined | 10 | 1 | 0.125 |
| ho chi minh city | thieu_thanh_phan | structured_tags_joined | 1 | 0 | 0.000 |
| ho chi minh city | viet_tat | structured_tags_joined | 6 | 1 | 0.125 |
| ho chinh minh | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |
| hoa binh | co_dau_khac | structured_tags_joined | 5 | 1 | 0.125 |
| hoa binh | viet_tat | structured_tags_joined | 1 | 0 | 0.000 |
| hoa binh province | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |
| hoang hoa | thieu_thanh_phan | structured_tags_joined | 1 | 0 | 0.000 |
| hoc mon | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |
| hochiminh cit | co_dau_khac | structured_tags_joined | 2 | 0 | 0.000 |
| hochiminh city | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |
| hoi an | co_dau_khac | structured_tags_joined | 33 | 2 | 0.250 |
| hoi an | khong_dau | structured_tags_joined | 6 | 1 | 0.125 |
| hoi an | thieu_thanh_phan | structured_tags_joined | 2 | 0 | 0.000 |
| hon dat | thieu_thanh_phan | structured_tags_joined | 1 | 0 | 0.000 |
| hue | co_dau_khac | structured_tags_joined | 32 | 2 | 0.250 |
| hue thua thien hue | co_dau_khac | structured_tags_joined | 2 | 0 | 0.000 |
| hung yen | co_dau_khac | structured_tags_joined | 62 | 4 | 0.500 |
| hung yen | thieu_thanh_phan | structured_tags_joined | 2 | 0 | 0.000 |
| hung yen province | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |
| khanh hoa | co_dau_khac | structured_tags_joined | 72 | 5 | 0.625 |
| khanh hoa | khong_dau | structured_tags_joined | 2 | 0 | 0.000 |
| khanh hoa | thieu_thanh_phan | structured_tags_joined | 3 | 0 | 0.000 |
| khanh khoa | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |
| khong_co_the_tinh | co_dau_khac | addr:full | 71 | 5 | 0.625 |
| khong_co_the_tinh | co_dau_khac | structured_tags_joined | 742 | 45 | 5.625 |
| khong_co_the_tinh | khong_dau | addr:full | 2 | 0 | 0.000 |
| khong_co_the_tinh | khong_dau | structured_tags_joined | 349 | 21 | 2.625 |
| khong_co_the_tinh | thieu_thanh_phan | addr:full | 6 | 1 | 0.125 |
| khong_co_the_tinh | thieu_thanh_phan | structured_tags_joined | 5585 | 340 | 42.500 |
| khong_co_the_tinh | viet_tat | addr:full | 27 | 2 | 0.250 |
| khong_co_the_tinh | viet_tat | structured_tags_joined | 83 | 5 | 0.625 |
| kien giang | co_dau_khac | structured_tags_joined | 27 | 2 | 0.250 |
| kien giang | khong_dau | structured_tags_joined | 3 | 0 | 0.000 |
| kien giang vietnam | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |
| kieng gian | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |
| kon tum | co_dau_khac | structured_tags_joined | 9 | 1 | 0.125 |
| lai vung | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |
| lam dong | co_dau_khac | structured_tags_joined | 165 | 10 | 1.250 |
| lam dong | khong_dau | structured_tags_joined | 1 | 0 | 0.000 |
| lam dong | thieu_thanh_phan | structured_tags_joined | 2 | 0 | 0.000 |
| lam dong | viet_tat | structured_tags_joined | 2 | 0 | 0.000 |
| lao cai | co_dau_khac | structured_tags_joined | 20 | 1 | 0.125 |
| lao cai | khong_dau | structured_tags_joined | 3 | 0 | 0.000 |
| laocai | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |
| laocai | khong_dau | structured_tags_joined | 1 | 0 | 0.000 |
| long an | co_dau_khac | structured_tags_joined | 42 | 3 | 0.375 |
| mai chau | khong_dau | structured_tags_joined | 1 | 0 | 0.000 |
| mui ne | co_dau_khac | structured_tags_joined | 2 | 0 | 0.000 |
| mui ne | khong_dau | structured_tags_joined | 1 | 0 | 0.000 |
| mui ne ham tien | khong_dau | structured_tags_joined | 1 | 0 | 0.000 |
| mui ne phan thiet | khong_dau | structured_tags_joined | 1 | 0 | 0.000 |
| my tho | co_dau_khac | structured_tags_joined | 2 | 0 | 0.000 |
| my tho | thieu_thanh_phan | structured_tags_joined | 22 | 2 | 0.250 |
| nam dinh | co_dau_khac | structured_tags_joined | 6 | 1 | 0.125 |
| nam dinh | thieu_thanh_phan | structured_tags_joined | 1 | 0 | 0.000 |
| nghe an | co_dau_khac | structured_tags_joined | 25 | 2 | 0.250 |
| nghe an | thieu_thanh_phan | structured_tags_joined | 1 | 0 | 0.000 |
| nha be | co_dau_khac | structured_tags_joined | 2 | 0 | 0.000 |
| nha trang | co_dau_khac | structured_tags_joined | 12 | 1 | 0.125 |
| nha trang | khong_dau | structured_tags_joined | 1 | 0 | 0.000 |
| nha trang | thieu_thanh_phan | structured_tags_joined | 1 | 0 | 0.000 |
| ninh binh | co_dau_khac | structured_tags_joined | 29 | 2 | 0.250 |
| ninh hoa | khong_dau | structured_tags_joined | 1 | 0 | 0.000 |
| ninh kieu can tho | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |
| ninh thuan | co_dau_khac | structured_tags_joined | 11 | 1 | 0.125 |
| phan dinh phung thai nguyen | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |
| phan rang thap cham | co_dau_khac | structured_tags_joined | 2 | 0 | 0.000 |
| phan rang thap cham | thieu_thanh_phan | structured_tags_joined | 2 | 0 | 0.000 |
| phan thiet | co_dau_khac | structured_tags_joined | 5 | 1 | 0.125 |
| phan thiet | thieu_thanh_phan | structured_tags_joined | 1 | 0 | 0.000 |
| pho ha noi | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |
| pho to vinh dien | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |
| phong nha | khong_dau | structured_tags_joined | 1 | 0 | 0.000 |
| phu hoi | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |
| phu ly | co_dau_khac | structured_tags_joined | 3 | 0 | 0.000 |
| phu nhuan | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |
| phu quoc | co_dau_khac | structured_tags_joined | 2 | 0 | 0.000 |
| phu quoc island | khong_dau | structured_tags_joined | 2 | 0 | 0.000 |
| phu tho | co_dau_khac | structured_tags_joined | 5 | 1 | 0.125 |
| phu yen | co_dau_khac | structured_tags_joined | 13 | 1 | 0.125 |
| phuong 1 | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |
| phuong 17 | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |
| phuong 2 | co_dau_khac | structured_tags_joined | 2 | 0 | 0.000 |
| phuong 25 | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |
| phuong 3 | co_dau_khac | structured_tags_joined | 2 | 0 | 0.000 |
| phuong 6 | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |
| phuong 7 | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |
| phuong 7 quan phu nhuan | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |
| phuong 8 | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |
| phuong 8 | thieu_thanh_phan | structured_tags_joined | 1 | 0 | 0.000 |
| phuong an lac | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |
| phuong bien giang | thieu_thanh_phan | structured_tags_joined | 1 | 0 | 0.000 |
| phuong co nhue 1 | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |
| phuong dai mo | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |
| phuong duc thang | co_dau_khac | structured_tags_joined | 3 | 0 | 0.000 |
| phuong giang bien | thieu_thanh_phan | structured_tags_joined | 1 | 0 | 0.000 |
| phuong hoa xuan | thieu_thanh_phan | structured_tags_joined | 1 | 0 | 0.000 |
| phuong long thanh my | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |
| phuong pham ngu lao q1 | viet_tat | structured_tags_joined | 2 | 0 | 0.000 |
| phuong phu thuong | thieu_thanh_phan | structured_tags_joined | 1 | 0 | 0.000 |
| phuong quang an | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |
| phuong rach soi | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |
| phuong sa dec | thieu_thanh_phan | structured_tags_joined | 1 | 0 | 0.000 |
| phuong tan chanh hiep | thieu_thanh_phan | structured_tags_joined | 1 | 0 | 0.000 |
| phuong tan khanh | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |
| phuong tan quy | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |
| phuong tan quy | thieu_thanh_phan | structured_tags_joined | 1 | 0 | 0.000 |
| phuong tan thoi hiep | co_dau_khac | structured_tags_joined | 2 | 0 | 0.000 |
| phuong tan thoi nhat | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |
| phuong thao dien | co_dau_khac | structured_tags_joined | 2 | 0 | 0.000 |
| phuong vinh hung | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |
| phuong xuan phuong | thieu_thanh_phan | structured_tags_joined | 1 | 0 | 0.000 |
| quan 1 | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |
| quan 3 | khong_dau | structured_tags_joined | 1 | 0 | 0.000 |
| quang binh | co_dau_khac | structured_tags_joined | 11 | 1 | 0.125 |
| quang binh | khong_dau | structured_tags_joined | 5 | 1 | 0.125 |
| quang nam | co_dau_khac | structured_tags_joined | 70 | 4 | 0.500 |
| quang nam | khong_dau | structured_tags_joined | 6 | 1 | 0.125 |
| quang nam | thieu_thanh_phan | structured_tags_joined | 1 | 0 | 0.000 |
| quang nam province | co_dau_khac | structured_tags_joined | 2 | 0 | 0.000 |
| quang ngai | co_dau_khac | structured_tags_joined | 5 | 1 | 0.125 |
| quang ngai | thieu_thanh_phan | structured_tags_joined | 1 | 0 | 0.000 |
| quang ninh | co_dau_khac | structured_tags_joined | 17 | 1 | 0.125 |
| quang ninh | thieu_thanh_phan | structured_tags_joined | 1 | 0 | 0.000 |
| quang tri | co_dau_khac | structured_tags_joined | 5 | 0 | 0.000 |
| quang tri | thieu_thanh_phan | structured_tags_joined | 2 | 0 | 0.000 |
| quy nhon | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |
| rach gia | khong_dau | structured_tags_joined | 1 | 0 | 0.000 |
| sa pa | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |
| sa pa | khong_dau | structured_tags_joined | 2 | 0 | 0.000 |
| sai gon | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |
| saigon | co_dau_khac | structured_tags_joined | 5 | 0 | 0.000 |
| soc trang | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |
| t lam dong | viet_tat | structured_tags_joined | 1 | 0 | 0.000 |
| t p hcm | khong_dau | structured_tags_joined | 1 | 0 | 0.000 |
| t son la | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |
| t vinh long | viet_tat | structured_tags_joined | 1 | 0 | 0.000 |
| tan thanh | thieu_thanh_phan | structured_tags_joined | 2 | 0 | 0.000 |
| tay ninh | co_dau_khac | structured_tags_joined | 58 | 4 | 0.500 |
| tay ninh | khong_dau | structured_tags_joined | 1 | 0 | 0.000 |
| tay ninh | thieu_thanh_phan | structured_tags_joined | 1 | 0 | 0.000 |
| tay ninh | viet_tat | structured_tags_joined | 4 | 0 | 0.000 |
| tay ninh provine | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |
| tay ninh provine | khong_dau | structured_tags_joined | 1 | 0 | 0.000 |
| thai binh | co_dau_khac | structured_tags_joined | 5 | 0 | 0.000 |
| thai nguyen | co_dau_khac | structured_tags_joined | 19 | 1 | 0.125 |
| thai ngyen | khong_dau | structured_tags_joined | 1 | 0 | 0.000 |
| thanh hoa | co_dau_khac | structured_tags_joined | 9 | 1 | 0.125 |
| thanh pho ba ria | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |
| thanh pho bac ninh | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |
| thanh pho can tho | co_dau_khac | structured_tags_joined | 5 | 0 | 0.000 |
| thanh pho da nang | co_dau_khac | structured_tags_joined | 21 | 1 | 0.125 |
| thanh pho ha noi | co_dau_khac | addr:full | 2 | 0 | 0.000 |
| thanh pho ha noi | co_dau_khac | structured_tags_joined | 529 | 32 | 4.000 |
| thanh pho ha noi | thieu_thanh_phan | structured_tags_joined | 1 | 0 | 0.000 |
| thanh pho ha noi | viet_tat | addr:full | 2 | 0 | 0.000 |
| thanh pho ha noi | viet_tat | structured_tags_joined | 5 | 0 | 0.000 |
| thanh pho hai phong | co_dau_khac | structured_tags_joined | 10 | 1 | 0.125 |
| thanh pho hai phong | thieu_thanh_phan | structured_tags_joined | 1 | 0 | 0.000 |
| thanh pho ho chi minh | co_dau_khac | structured_tags_joined | 615 | 38 | 4.750 |
| thanh pho ho chi minh | thieu_thanh_phan | structured_tags_joined | 2 | 0 | 0.000 |
| thanh pho ho chi minh | viet_tat | structured_tags_joined | 2 | 0 | 0.000 |
| thanh pho ho chi minhminh | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |
| thanh pho hue | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |
| thanh pho phu quoc | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |
| thanh pho thu duc | co_dau_khac | structured_tags_joined | 12 | 1 | 0.125 |
| thanh pho vung tau | co_dau_khac | structured_tags_joined | 3 | 0 | 0.000 |
| thao dien | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |
| thi tran di linh | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |
| thi tran hau nghia | thieu_thanh_phan | structured_tags_joined | 1 | 0 | 0.000 |
| thi tran lac duong | thieu_thanh_phan | structured_tags_joined | 1 | 0 | 0.000 |
| thot not | co_dau_khac | structured_tags_joined | 3 | 0 | 0.000 |
| thu dau mot | co_dau_khac | structured_tags_joined | 2 | 0 | 0.000 |
| thu duc | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |
| thu duc | thieu_thanh_phan | structured_tags_joined | 1 | 0 | 0.000 |
| thu duc ho chi minh | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |
| thua thien hue | co_dau_khac | structured_tags_joined | 23 | 2 | 0.250 |
| tien giang | co_dau_khac | structured_tags_joined | 24 | 2 | 0.250 |
| tien yen | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |
| tinh | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |
| tinh an giang | co_dau_khac | structured_tags_joined | 2 | 0 | 0.000 |
| tinh ba ria vung tau | co_dau_khac | structured_tags_joined | 3 | 0 | 0.000 |
| tinh bac ninh | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |
| tinh ben tre | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |
| tinh binh dinh | co_dau_khac | structured_tags_joined | 5 | 0 | 0.000 |
| tinh binh duong | co_dau_khac | structured_tags_joined | 6 | 1 | 0.125 |
| tinh binh duong | viet_tat | structured_tags_joined | 1 | 0 | 0.000 |
| tinh ca mau | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |
| tinh dak lak | co_dau_khac | structured_tags_joined | 3 | 0 | 0.000 |
| tinh dong nai | co_dau_khac | structured_tags_joined | 61 | 4 | 0.500 |
| tinh gia lai | co_dau_khac | structured_tags_joined | 4 | 0 | 0.000 |
| tinh hung yen | co_dau_khac | structured_tags_joined | 5 | 0 | 0.000 |
| tinh khanh hoa | co_dau_khac | structured_tags_joined | 13 | 1 | 0.125 |
| tinh kon tum | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |
| tinh lam dong | co_dau_khac | structured_tags_joined | 9 | 1 | 0.125 |
| tinh lao cai | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |
| tinh long an | co_dau_khac | structured_tags_joined | 9 | 1 | 0.125 |
| tinh phu tho | co_dau_khac | structured_tags_joined | 4 | 0 | 0.000 |
| tinh quang ngai | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |
| tinh tay ninh | co_dau_khac | structured_tags_joined | 6 | 1 | 0.125 |
| tinh thai binh | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |
| tinh thanh hoa | co_dau_khac | structured_tags_joined | 2 | 0 | 0.000 |
| tinh thua thien hue | co_dau_khac | structured_tags_joined | 5 | 0 | 0.000 |
| tinh tra vinh | co_dau_khac | structured_tags_joined | 4 | 0 | 0.000 |
| tinh vinh long | co_dau_khac | structured_tags_joined | 2 | 0 | 0.000 |
| tinh vinh long | thieu_thanh_phan | structured_tags_joined | 1 | 0 | 0.000 |
| tp ben tre | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |
| tp buon ma thuot | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |
| tp can tho | viet_tat | structured_tags_joined | 1 | 0 | 0.000 |
| tp cao lanh | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |
| tp da nang | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |
| tp dong nai | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |
| tp ha noi | co_dau_khac | structured_tags_joined | 4 | 0 | 0.000 |
| tp ha noi | viet_tat | structured_tags_joined | 2 | 0 | 0.000 |
| tp ha tinh | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |
| tp ha tinh | thieu_thanh_phan | structured_tags_joined | 4 | 0 | 0.000 |
| tp hcm | viet_tat | structured_tags_joined | 15 | 1 | 0.125 |
| tp ho chi minh | co_dau_khac | structured_tags_joined | 30 | 2 | 0.250 |
| tp ho chi minh | viet_tat | structured_tags_joined | 1 | 0 | 0.000 |
| tp ho chinh minh | co_dau_khac | structured_tags_joined | 2 | 0 | 0.000 |
| tphcm | viet_tat | structured_tags_joined | 5 | 0 | 0.000 |
| tra vinh | co_dau_khac | structured_tags_joined | 4 | 0 | 0.000 |
| trang bom | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |
| tuy hoa | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |
| tuyen quang | co_dau_khac | structured_tags_joined | 3 | 0 | 0.000 |
| vie | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |
| viet nam | co_dau_khac | structured_tags_joined | 19 | 1 | 0.125 |
| vietnam | co_dau_khac | structured_tags_joined | 14 | 1 | 0.125 |
| vietnam | khong_dau | structured_tags_joined | 3 | 0 | 0.000 |
| vietnam | viet_tat | structured_tags_joined | 1 | 0 | 0.000 |
| vinh long | co_dau_khac | structured_tags_joined | 13 | 1 | 0.125 |
| vinh phuc | co_dau_khac | structured_tags_joined | 2 | 0 | 0.000 |
| vn | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |
| vung tau | co_dau_khac | structured_tags_joined | 11 | 1 | 0.125 |
| vung tau | khong_dau | structured_tags_joined | 2 | 0 | 0.000 |
| vung tau | viet_tat | structured_tags_joined | 1 | 0 | 0.000 |
| vung tau baria | viet_tat | structured_tags_joined | 1 | 0 | 0.000 |
| xa go cong dong | thieu_thanh_phan | structured_tags_joined | 1 | 0 | 0.000 |
| xa hoa long | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |
| xa hoang quy | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |
| xa lai vung | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |
| xa lai vung | thieu_thanh_phan | structured_tags_joined | 1 | 0 | 0.000 |
| xa tan xa | thieu_thanh_phan | structured_tags_joined | 1 | 0 | 0.000 |
| xa xuan thoi son | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |
| yen bai | co_dau_khac | structured_tags_joined | 1 | 0 | 0.000 |

## 3. Bằng chứng bất nhất của nhãn máy trên dev

Đọc `data/train_dev/dev.csv`: **1136** dòng; phép đếm regex, không kiểm toán ngữ nghĩa; nhóm chồng nhau.

| Dấu hiệu | Số dòng dev | ID ví dụ đầu tiên |
|---|---:|---|
| ngo_hem_ngach_kiet | 170 | VNDEV_00012 |
| nha_khoang | 13 | VNDEV_00022 |
| nha_gach_cheo | 42 | VNDEV_00005 |
| tien_to_so | 419 | VNDEV_00012 |
| tien_to_duong | 756 | VNDEV_00004 |
| thon_to_kp_ap | 43 | VNDEV_00012 |
| viet_tat_cmt_ql | 10 | VNDEV_00007 |
| ma_buu_chinh_cuoi | 1 | VNDEV_00150 |
| toa_nha_tang_phong | 63 | VNDEV_00009 |
| tieng_anh | 26 | VNDEV_00001 |
| ngo_text_and_road_contains_ngo | 59 | VNDEV_00012 |
| ngo_text_and_separate_field | 129 | VNDEV_00012 |
| ngo_text_both_fields | 31 | VNDEV_00012 |
| ngo_text_but_no_ngo_field | 41 | VNDEV_00099 |

- Trường hợp `VNDEV_00012`: “Số 16 ngõ 12 Trần Quý Kiên ...” có `ngo_ngach_hem=Ngõ 12` đồng thời `duong=Đường Ngõ 12 Trần Quý Kiên`. Trường hợp `VNDEV_00028`: “Số 3 ngõ 55 Đỗ Quang ...” tách `Ngõ 55` và `Đỗ Quang`. Tài liệu nháp `QUY_UOC_NHAN.md` nêu các phương án rõ và điểm cần người duyệt.

## 4. Công cụ đã xây và mẻ kiểm công cụ 60 địa chỉ

- `SCHEMA_NHAN.json`, `kiem_nhan.py`: schema strict, offset bằng lát cắt, chống chồng span, từ chối khóa mã do AI gửi.
- `tao_goi_gan_nhan.py`: **16 gói × 50 địa chỉ** trong `goi_gan_nhan/`, mỗi gói prompt độc lập và CSV đầu vào; **không gọi API/mô hình**.
- `anh_xa_hanh_chinh.py`: tra mã từ danh mục, mã xã bị chia/tên trùng hoặc không phân giải được -> để trống và abstain.
- `dong_thuan.py`: tất cả bộ gán phải có đủ cùng ID và input, đồng thuận riêng từng trường; Fleiss kappa, queue CSV.
- `lay_mau_kiem.py`: mặc định chọn ngẫu nhiên **150 mục đồng thuận đủ trường** với seed, xuất phiếu chưa đánh dấu cho người.
- `uoc_luong_sai_so.py`: cận trên một phía 95% Clopper–Pearson từ **phiếu đã được người thực sự kiểm đủ các trường**, thiếu nhãn thì fail.
- Mẻ `thu_nghiem/` dùng 60 địa chỉ **chỉ kiểm công cụ**: 59/60 đồng thuận giả lập, 1 dòng queue; phiếu giả lập 210 dòng kiểm trường (30 địa chỉ × 7), **0 bộ AI độc lập thật, 0 người duyệt**. Nhãn do một người viết bằng rule đơn giản và bản sao cơ học, **không phải gold**.
- Test Clopper–Pearson: 0 lỗi/150 -> cận trên ~**1,977%**; 3 lỗi/150 -> cận trên xấp xỉ **5,1%**. Các ví dụ này là toán kiểm phần mềm, không phải ước lượng dữ liệu thật.

## 5. QUYẾT ĐỊNH CẦN NGƯỜI DUYỆT

Chốt **từng điểm** trong `QUY_UOC_NHAN.md`: ngõ/hẻm tách khỏi đường; cách hiểu `37-39` và `12/5` (mâu thuẫn §4.6); tiền tố tự sinh; tổ/khu phố/ấp/thôn; CMT8/QL; mã bưu chính; tòa nhà/phòng/tầng; tiếng Anh; xã cũ bị chia; trùng tên/thiếu tỉnh; điều kiện công nhận ứng viên thành bộ đánh giá vàng.

## 6. Chưa làm và giới hạn bắt buộc

1. **Chưa gán nhãn thật bằng hai hoặc nhiều họ AI khác nhau**; prompt chỉ là file để đưa ra ngoài dự án. Không gọi API/LLM, không cài thư viện.
2. **Chưa có người kiểm 150 địa chỉ**, nên **chưa đo được sai số thực hoặc cận tin cậy thực**. Mọi ước lượng giả lập nằm trong thư mục KIEM_CONG_CU_KHONG_PHAI_GOLD.
3. Cơ cấu OSM bias về địa chỉ từ structured tags, đô thị có dữ liệu và tỉnh ghi trong tags. Tỷ lệ các loại địa chỉ khó còn thấp; cần chốt quota nếu mong đánh giá theo độ khó, không dùng trọng số mẫu hiện tại như phân bố quốc gia.
4. Bộ ánh xạ hành chính luôn conservative: tên trùng/xã bị chia không có căn cứ -> mã xã rỗng; thiếu địa giới chi tiết thì không được tự đoán. Không dùng tọa độ để gắn gold.
5. Khóa họ che số nhà là heuristic của audit; PASS không loại trừ được mọi trùng lặp ngữ nghĩa/diễn đạt khác.
6. Phần lớn dev và test cũ có nhãn máy; ví dụ dev chỉ chứng minh sự thiếu nhất quán, **không xác nhận đáp án**.

## 7. Chạy lại kiểm chứng offline

```powershell
cd D:\nlp_gold
& D:\nlp_chuan_hoa_dia_chi\.venv-neural\Scripts\python.exe -X utf8 -B -m unittest tests.test_gold_tooling
& D:\nlp_chuan_hoa_dia_chi\.venv-neural\Scripts\python.exe -X utf8 -B data/gold/chon_mau.py --verify
```

Không chạy `chon_mau.py` không có `--verify` khi file mẫu đã tồn tại: script sẽ từ chối ghi đè để bảo vệ hồ sơ.
