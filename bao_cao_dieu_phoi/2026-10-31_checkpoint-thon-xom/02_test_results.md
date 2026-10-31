# Kết quả kiểm thử độc lập — 2026-10-31

- Dự án: `D:\\nlp_rf_E`
- Thư mục báo cáo: `D:\\nlp_rf_E\\bao_cao_dieu_phoi\\2026-10-31_checkpoint-thon-xom`
- Báo cáo: `02_test_results.md`
- Ngày thực hiện: 2026-10-31
- Hệ điều hành: Windows (thiết bị MSI)

## 1. Phạm vi và bảo toàn dữ liệu

Đã thực hiện kiểm tra Git, xác định interpreter, chạy đúng hai lệnh unittest được yêu cầu, kiểm tra Git lần nữa và ghi báo cáo này.

Không cài package, không sửa mã nguồn, không commit, không chạy script huấn luyện dự án. Không có thao tác Git làm thay đổi index hoặc working tree.

**Lưu ý về huấn luyện nằm bên trong unit test:** hai test trong bộ hồi quy tự tạo mô hình fixture nhỏ trong `TemporaryDirectory`:
- `tests.test_crf.CRFContractTests.test_train_luu_nap_va_chay_pipeline_that` dùng `pycrfsuite.Trainer` với một câu fixture và `max_iterations=10`, lưu `tiny.crfsuite` trong thư mục tạm.
- `tests.test_char.CharTests.test_ranker_that_luu_nap_va_chan_sai_checkpoint` dùng `lightgbm.train` với 4 dòng dữ liệu tổng hợp và `num_boost_round=4`, lưu ranker trong thư mục tạm.

Cả hai test đều đã chạy và PASS; thư mục tạm được quản lý bằng `TemporaryDirectory`. Đây **không phải** huấn luyện lại mô hình dự án/checkpoint sản phẩm và không ghi mô hình huấn luyện vào thư mục dự án. Tuy nhiên, nếu yêu cầu “không huấn luyện” được hiểu là cấm cả huấn luyện fixture bên trong unit test, cần lưu ý hai test trên có thực hiện thao tác huấn luyện tổng hợp như mô tả.

## 2. Python interpreter

Interpreter ưu tiên được yêu cầu đã tồn tại:

```text
D:\\nlp_chuan_hoa_dia_chi\\.venv-neural\\Scripts\\python.exe
Python 3.12.10
```

Lệnh kiểm tra version trả về exit code `0`. Không tạo môi trường mới và không cài dependency.

## 3. Kiểm thử độc lập

**Lệnh thực tế** (chạy tại `D:\\nlp_rf_E`, dùng interpreter tuyệt đối ở trên):

```powershell
python -m unittest -v tests.test_loi_goc_log
```

| Chỉ số | Kết quả |
|---|---:|
| Tổng số test | 9 |
| PASS | 9 |
| FAIL | 0 |
| ERROR | 0 |
| SKIP | 0 |
| Exit code | 0 |
| Thời gian unittest | 10.561 giây |

Output kết thúc thực tế:

```text
Ran 9 tests in 10.561s
OK
=== EXIT_CODE=0 ===
```

Cả 9 test thực sự chạy (mỗi test trả về `ok`):
- `test_bang_chung_khac_nhau_van_chon`
- `test_bang_chung_ngang_nhau_thi_khong_chon_bua`
- `test_don_vi_nhan_ra_nhung_khong_tra_duoc_co_dau_vet`
- `test_duong_khoi_phuc_co_dau_vet_va_khong_con_chua_phan_loai`
- `test_khop_gan_dung_khong_cam_ten_duong`
- `test_so_dien_thoai_cuoi_cau_khong_lam_mat_tinh`
- `test_thon_xom_khong_nuot_hanh_chinh_khi_khong_dau_phay`
- `test_tinh_khop_dung_khong_thanh_ten_duong`
- `test_viet_tat_xom_trong_span`

## 4. Bộ kiểm thử hồi quy

Chỉ sau khi lệnh độc lập kết thúc không có test thất bại, bộ hồi quy mới được chạy.

**Lệnh thực tế:**

```powershell
python -m unittest -v tests.test_ten_cu tests.test_pipeline tests.test_chan_doan_pipeline tests.test_pipeline_quality_isolated tests.test_hai_module tests.test_chuyen_doi_dia_chi_sach tests.test_viet_tat_chi_tiet tests.test_char tests.test_crf tests.test_hop_dong tests.test_pipeline_v3 tests.test_chuan_ten_duong tests.test_loi_goc_log
```

| Chỉ số | Kết quả |
|---|---:|
| Tổng số test | 119 |
| PASS | 119 |
| FAIL | 0 |
| ERROR | 0 |
| SKIP | 0 |
| Exit code | 0 |
| Thời gian unittest | 16.497 giây |

Output kết thúc thực tế:

```text
Ran 119 tests in 16.497s
OK
=== EXIT_CODE=0 ===
```

### 4.1. Module và test thực sự chạy

Tất cả 119 test dưới đây thực sự chạy và trả về `ok`. Không có test nào bị skip.

**`tests.test_ten_cu` — 4 test**
- `test_co_thon_xom`
- `test_ten_hien_tai_van_dung`
- `test_thi_tran_my_loc`
- `test_xa_my_hung_nam_dinh`

**`tests.test_pipeline` — 30 test**
- `test_cu_cung_ma_khac_thuc_the`
- `test_dao_thu_tu`
- `test_dau_vao_rong_va_kieu`
- `test_dau_vet_khong_chong_lan`
- `test_giu_huyen_ro_khi_xa_mau_thuan`
- `test_giu_so_nha_co_gach_cheo`
- `test_huyen_thanh_dac_khu`
- `test_khac_loai_tinh_van_giu_ten_va_canh_bao`
- `test_khac_loai_xa_duoc_kiem_tra_theo_ngu_canh`
- `test_khong_bien_xa_chua_biet_thanh_so_nha`
- `test_khong_dau_viet_tat`
- `test_levenshtein_trie`
- `test_ngo_dinh_so_unicode_phan_ra`
- `test_nguon_khong_tuong_thich_du_cung_dich`
- `test_ten_duong_bat_dau_bang_tu_hanh_chinh`
- `test_ten_duong_khong_bi_nhan_la_tinh`
- `test_ten_hanh_chinh_chua_tien_to_duong_thon`
- `test_ten_to_khong_thanh_tien_to_to`
- `test_thanh_pho_khong_bi_nhan_la_duong`
- `test_thieu_tinh_suy_tu_nguon_du_nhat`
- `test_tien_to_chi_tiet_that_van_duoc_nhan`
- `test_tinh_co_gach_noi`
- `test_tinh_trong_ten_duong_khong_la_tinh`
- `test_tron_moc`
- `test_tu_doi_dien_khong_loai_nham_ten_duong`
- `test_unicode_span_goc`
- `test_viet_tat_dinh_so_va_dau_vet`
- `test_viet_tat_duong_va_loi_telex`
- `test_xa_bi_chia_khong_chon_bua`
- `test_xa_lo_trong_ten_duong_khong_thanh_xa_tinh`

**`tests.test_chan_doan_pipeline` — 6 test**
- `test_chan_test_truoc_khi_doc`
- `test_co_dich_trong_xa_chia_khong_phai_chot_duy_nhat`
- `test_gioi_han_duyet_khong_duoc_bao_la_khong_co`
- `test_mau_trong_khong_lam_giam_ty_le_lech_trong_so_dien`
- `test_nhan_xa_co_gia_tri_khong_khop_tap_dich_nhieu_phan_tu`
- `test_them_bang_chung_moi_co_the_chot_dich`

**`tests.test_pipeline_quality_isolated` — 11 test**
- `test_khong_lay_span_chi_phu_mot_phan_token`
- `test_span_char_offset_khong_phu_thuoc_chi_so_token`
- `test_nhan_rong_va_du_doan_rong_duoc_phan_biet`
- `test_phan_biet_mat_dau_voi_sai_noi_dung`
- `test_giu_tien_to_duong_khi_tat_tu_dong`
- `test_khong_tu_them_tien_to_khi_da_tat`
- `test_so_nha_co_tien_to_ro_rang_khong_bi_xoa`
- `test_so_nha_nam_sau_chu_so_khong_duoc_loai`
- `test_sau_truong_tho_khac_chuoi_chuan`
- `test_chuyen_doi_duy_nhat_van_duoc_chon`
- `test_trung_ten_nhung_bi_chia_thi_khong_tu_chon`

**`tests.test_hai_module` — 6 test**
- `test_1_bo_lam_sach`
- `test_2_chuyen_doi`
- `test_3_chuyen_doi_khong_import_tien_xu_ly`
- `test_4_tien_xu_ly_khong_import_chuyen_doi`
- `test_5_chuan_hoa_bang_ghep_tay`
- `test_6_shim_bi_danh`

**`tests.test_chuyen_doi_dia_chi_sach` — 6 test**
- `test_don_vi_moc_moi`
- `test_hai_cach_hieu_khac_xa`
- `test_thieu_tinh_dau_vao`
- `test_xa_cu_bi_chia_de_trong`
- `test_xa_cu_bi_chia_phan_giai_theo_duong`
- `test_xa_cu_nhap_tron`

**`tests.test_viet_tat_chi_tiet` — 4 test**
- `test_khong_doi_khi_khong_phai_viet_tat`
- `test_ngo_hem_kiet`
- `test_so_nha`
- `test_thon_xom`

**`tests.test_char` — 8 test**
- `test_NFD_offset_va_span_cat_giua_token`
- `test_checkpoint_cpu_va_pipeline_rong`
- `test_crf_partition_va_viterbi_so_voi_vet_can`
- `test_hanh_chinh_chua_can_chinh_khong_bi_ep_O`
- `test_padding_khong_doi_emissions_cua_cau_ngan`
- `test_partial_crf_loss_gradient_va_padding`
- `test_ranker_that_luu_nap_va_chan_sai_checkpoint`
- `test_viet_tat_hanh_chinh_va_sai_chinh_ta_co_ngu_canh`

**`tests.test_crf` — 8 test**
- `test_F1_span_khong_bi_token_O_lam_dep`
- `test_admin_mask_khong_noi_cac_doan_roi`
- `test_bio_khong_noi_qua_O_va_dem_I_mo_coi`
- `test_can_chinh_khong_tao_am_gia_cho_tien_to_duong`
- `test_formatter_khong_mo_rong_ten_rieng`
- `test_khong_hoc_nhan_cat_giua_token`
- `test_nhan_chong_phai_bi_chan`
- `test_train_luu_nap_va_chay_pipeline_that`

**`tests.test_hop_dong` — 8 test**
- `test_dau_mau_thuan_duoc_ghi_ro_khong_sua`
- `test_khong_tu_suy_tinh_tu_ten_duong`
- `test_model_khong_duoc_xoa_ung_vien_hanh_chinh`
- `test_mot_ten_train_cung_khong_tu_thanh_ten_chac_chan`
- `test_nhieu_thu_tu_NFD_so_nha_va_ten_chua_biet`
- `test_rong_va_goi_lap_khong_roi_trang_thai`
- `test_tien_to_telex_khong_gia_lam_dinh_dang_don_thuan`
- `test_trung_khoa_giu_du_cac_ten_khong_chon_theo_tan_suat`

**`tests.test_pipeline_v3` — 11 test**
- `test_bao_toan_cum_so_nha_va_canh_bao`
- `test_chan_suy_duong_khong_chan_ten_khac_dau`
- `test_dau_da_nhap_phan_biet_hai_ten_cung_khoa`
- `test_dau_nhay_khong_thanh_tien_to_duong`
- `test_dau_nhay_noi_ten_va_giu_offset_unicode`
- `test_khong_ep_moc_moi_khi_ten_cu_moi_deu_hop_le`
- `test_khong_lay_so_trong_ten_duong_lam_so_nha`
- `test_lo_tap_the_khu_dan_cu_khong_tu_thanh_duong`
- `test_ma_dau_cum_ten_khong_bi_chan_chi_vi_co_so`
- `test_ten_day_du_co_so_khong_bi_cat_mat_duoi`
- `test_thieu_dau_van_giu_cac_kha_nang`

**`tests.test_chuan_ten_duong` — 8 test**
- `test_bao_ve_ten_duong_nhung_giu_hanh_chinh_co_tien_to`
- `test_builder_khong_doc_dev_va_khong_nhan_ten_khong_co_trong_span`
- `test_cung_khoa_khac_dau_khong_chon_theo_tan_suat`
- `test_khong_sua_dau_da_nhap_ke_ca_NFD`
- `test_phuc_hoi_dau_nhung_can_dung_tinh_va_loai_duong`
- `test_pipeline_co_dau_vet_goc_va_nguon_tra_cuu`
- `test_toan_quoc_chi_bo_sung_dau_khi_duy_nhat_mot_dang`
- `test_viet_tat_co_va_cham_phai_tu_choi`

**`tests.test_loi_goc_log` — 9 test**
- `test_bang_chung_khac_nhau_van_chon`
- `test_bang_chung_ngang_nhau_thi_khong_chon_bua`
- `test_don_vi_nhan_ra_nhung_khong_tra_duoc_co_dau_vet`
- `test_duong_khoi_phuc_co_dau_vet_va_khong_con_chua_phan_loai`
- `test_khop_gan_dung_khong_cam_ten_duong`
- `test_so_dien_thoai_cuoi_cau_khong_lam_mat_tinh`
- `test_thon_xom_khong_nuot_hanh_chinh_khi_khong_dau_phay`
- `test_tinh_khop_dung_khong_thanh_ten_duong`
- `test_viet_tat_xom_trong_span`

Tổng cộng: **119 test**, khớp với dòng tổng kết của unittest.

### 4.2. SKIP và phụ thuộc mô hình

- Không có test nào bị skip.
- `tests.test_char` có 8/8 test chạy; điều kiện `HAS_NEURAL` được thỏa mãn (các dependency torch, numpy, lightgbm có sẵn).
- `tests.test_crf` có 8/8 test chạy; `pycrfsuite` có sẵn nên test có điều kiện `skipUnless` không bị skip.
- Không ghi nhận test bị bỏ qua do thiếu model/checkpoint.
- Hai test huấn luyện fixture tạm đã được mô tả tại mục 1.

## 5. Lỗi, traceback và cách diễn giải output

- FAIL: không có.
- ERROR: không có.
- SKIP: không có.
- Traceback của unittest: không có.
- Cả hai tiến trình Python kết thúc với exit code `0`.

PowerShell hiển thị một số dòng stderr của unittest dưới dạng `NativeCommandError` khi dùng `2>&1`; đó là cách PowerShell bọc luồng stderr. Các dòng test vẫn kết thúc bằng `ok`, unittest tổng kết `OK`, và exit code của Python là `0`. Đây không phải test ERROR.

## 6. Git status trước và sau

### Trước kiểm thử

Lệnh: `git status --short --branch` và `git status --porcelain=v1 --untracked-files=all`.

```text
## refactor/tach-hai-phan-20261030
 M src/tien_xu_ly/crf_chi_tiet.py
 M tests/test_loi_goc_log.py
?? data/xa_chia_theo_duong/bang_xa_chia_theo_duong_danh_gia.csv
?? data/xa_chia_theo_duong/diem_giu_lai_danh_gia.csv
```

### Sau kiểm thử (trước khi ghi báo cáo)

```text
## refactor/tach-hai-phan-20261030
 M src/tien_xu_ly/crf_chi_tiet.py
 M tests/test_loi_goc_log.py
?? data/xa_chia_theo_duong/bang_xa_chia_theo_duong_danh_gia.csv
?? data/xa_chia_theo_duong/diem_giu_lai_danh_gia.csv
```

Danh sách file tracked có diff trước và sau giống nhau:
- `src/tien_xu_ly/crf_chi_tiet.py`
- `tests/test_loi_goc_log.py`

Hai thay đổi tracked và hai CSV untracked đã có sẵn trước khi chạy test; trạng thái sau test giống hệt trạng thái trước test. Hai CSV cần bảo toàn vẫn hiện diện và giữ nguyên metadata quan sát được:
- `bang_xa_chia_theo_duong_danh_gia.csv`: 4,188 bytes; modified `2026-10-31 11:49:21`.
- `diem_giu_lai_danh_gia.csv`: 40,207 bytes; modified `2026-10-31 11:49:21`.

Không có thay đổi mã nguồn mới do kiểm thử. Báo cáo này là artifact được tạo theo yêu cầu; Git status cuối cùng sau khi ghi báo cáo được xác nhận riêng.

## 7. Kết luận

**PASS — các lệnh unittest được yêu cầu đều hoàn tất thành công.**

- Kiểm thử độc lập: 9/9 PASS, exit code 0.
- Bộ hồi quy: 119/119 PASS, exit code 0.
- Tổng lượt thực thi của hai lệnh: 128 (9 + 119); 9 test `test_loi_goc_log` xuất hiện ở cả lệnh độc lập và danh sách hồi quy theo đúng yêu cầu.
- Không có FAIL, ERROR, SKIP hoặc traceback.
- Không cài package, không sửa mã nguồn, không commit, không huấn luyện lại model sản phẩm.
- Lưu ý: hai unit test đã huấn luyện fixture nhỏ trong thư mục tạm; chi tiết ở mục 1.


## 8. Git status sau khi ghi báo cáo

Lệnh: `git status --short --branch` và `git status --porcelain=v1 --untracked-files=all`.

```text
## refactor/tach-hai-phan-20261030
 M src/tien_xu_ly/crf_chi_tiet.py
 M tests/test_loi_goc_log.py
?? bao_cao_dieu_phoi/2026-10-31_checkpoint-thon-xom/02_test_results.md
?? data/xa_chia_theo_duong/bang_xa_chia_theo_duong_danh_gia.csv
?? data/xa_chia_theo_duong/diem_giu_lai_danh_gia.csv
```

Báo cáo `02_test_results.md` là file untracked mới được tạo theo đúng yêu cầu đầu ra. So với trạng thái trước kiểm thử, đây là thay đổi duy nhất được bổ sung. Hai file mã nguồn đang `Modified` vẫn là đúng hai file đã Modified từ trước; `git diff --name-only` không có file mã nguồn mới. Hai CSV untracked được giữ nguyên và metadata sau cùng vẫn là 4,188 bytes / 40,207 bytes với thời điểm sửa đổi `2026-10-31 11:49:21`.
