# Mục lục báo cáo và kết quả kiểm chứng

Toàn bộ báo cáo/gói bàn giao đã tạo trong hội thoại được lưu ngay trong
dự án. Bản lưu trữ ngày 29/10/2026 ở [bao_cao/2026-10-29](../bao_cao/2026-10-29/),
gồm **194 file gốc, 46.394.613 byte**, đã đối chiếu SHA-256 từng file với
nguồn trước và sau sao chép. Chi tiết trong
[manifest lưu trữ](../bao_cao/2026-10-29/MANIFEST_LUU_TRU.json).

## Cập nhật ngày 30/10/2026

- [Address May Cry — thiết kế, phân công UI/API và hồ sơ triển khai](ui-address-may-cry/README.md)


Đọc bản kiểm tra độc lập cùng báo cáo của agy: một số chỉ số oracle và phân loại nguyên nhân trong bản chẩn đoán chưa hợp lệ, chưa dùng để quyết định train mô hình mới.

| Nội dung | Tài liệu trong dự án |
|---|---|
| Tổng hợp nghiệm thu ba nhiệm vụ agy A/B/C: phần dùng được, lỗi phép đo và hướng tiếp theo | [Kiểm tra độc lập](../danh_gia/ket_qua/song_song_20261030/KIEM_TRA_DOC_LAP/BAO_CAO.md), [số đếm đối chiếu](../danh_gia/ket_qua/song_song_20261030/KIEM_TRA_DOC_LAP/KIEM_CHUNG.json) |
| Ba nhiệm vụ agy chạy song song: oracle, lỗi chi tiết và ứng viên tên đường | [Phân công và baseline](../danh_gia/ket_qua/song_song_20261030/README.md) |
| Kiểm tra độc lập chẩn đoán ứng viên, lỗi oracle và giới hạn kết luận | [Phân tích mới nhất](../bao_cao/2026-10-30/kiem_tra_nhanh_agy/PHAN_TICH_CHAN_DOAN_UNG_VIEN.md), [số đếm đối chiếu](../bao_cao/2026-10-30/kiem_tra_nhanh_agy/AUDIT_CHAN_DOAN.json) |
| Chẩn đoán do agy bàn giao — cần đọc kèm kiểm tra độc lập | [Báo cáo agy](../danh_gia/ket_qua/chan_doan_ung_vien_20261030/BAO_CAO.md), [số liệu](../danh_gia/ket_qua/chan_doan_ung_vien_20261030/thong_ke.json), [lỗi dev](../danh_gia/ket_qua/chan_doan_ung_vien_20261030/loi_tung_ca_dev.jsonl) |
| Kiểm tra Hybrid CNN + ViDeBERTa, tách tác dụng mô hình và tra từ điển | [Phân tích](../bao_cao/2026-10-30/kiem_tra_nhanh_agy/PHAN_TICH_HYBRID_MOI_NHAT.md), [kiểm chứng 4 ca](../bao_cao/2026-10-30/kiem_tra_nhanh_agy/HYBRID_4_CA.json), [log](../bao_cao/2026-10-30/kiem_tra_nhanh_agy/HYBRID_LOG.json) |
| Kiểm tra ban đầu nhánh nghiên cứu agy | [Nhận xét](../bao_cao/2026-10-30/kiem_tra_nhanh_agy/NHAN_XET.md), [bằng chứng](../bao_cao/2026-10-30/kiem_tra_nhanh_agy/BANG_CHUNG.json) |
| Kiểm tra cấu trúc nhãn bổ sung v2.1 — chưa nghiệm thu ngữ nghĩa toàn bộ | [Kết quả](../bao_cao/2026-10-30/kiem_tra_nhanh_agy/KIEM_TRA_NHAN_BO_SUNG_V2_1.json) |

## Các bản nên đọc trước

| Nội dung | Báo cáo/kết quả trong dự án |
|---|---|
| Bàn giao toàn dự án, lịch sử công việc và yêu cầu cải tiến độc lập | [Đọc trước](../ban_giao/2026-10-29/README_BAN_GIAO.md), [hiện trạng](../ban_giao/2026-10-29/HIEN_TRANG.md), [lịch sử](../ban_giao/2026-10-29/LICH_SU.md), [thư mục gửi](../ban_giao/2026-10-29/goi_gui_di/) |
| Module hiện tại và số đo riêng tiền xử lý/model/định dạng/end-to-end | [Bản đồ module và số đo](MODULE_VA_SO_DO.md), [thống kê](../danh_gia/ket_qua/tung_module_v1_01/thong_ke.json) |
| Sửa tiền tố hành chính và bảo toàn lưới token gốc | [Nhận định](SUA_TRA_CUU_HANH_CHINH_V1.md), [số đo](../danh_gia/ket_qua/sua_tien_to_hanh_chinh_v2_01/BAO_CAO.md) |
| Tách dữ liệu dùng tiếp, giao phần lỗi cho hai agy | [Bản lọc và phân chia](DU_LIEU_DUNG_TIEP_V2_01.md), [kiểm chứng](../data/train_dev/duyet_v2_01/KIEM_CHUNG.json) |
| Audit agy danh mục đường v1 và train khó v2: chưa nghiệm thu | [Báo cáo](../danh_gia/ket_qua/audit_agy_duong_train_v2_01/BAO_CAO.md), [kiểm độc lập](../danh_gia/ket_qua/audit_agy_duong_train_v2_01/KIEM_TRA_DOC_LAP.json) |
| Phân tích kỹ sau đo: tên chuẩn, mơ hồ, nhãn và giới hạn bản hợp đồng | [Phân tích](PHAN_TICH_DIEM_NGHEN_SAU_DO.md) |
| Đo chế độ hợp đồng: điểm giảm và phân loại phần giảm | [Báo cáo](../danh_gia/ket_qua/do_hop_dong_v1_01/BAO_CAO.md), [gợi ý/hồi quy](../danh_gia/ket_qua/do_hop_dong_v1_01/PHAN_TICH_GOI_Y.json) |
| Chế độ pipeline có căn cứ, train chỉ gợi ý và giữ nhiều giả thuyết | [Hợp đồng, giới hạn và cách chạy](HOP_DONG_PIPELINE_V1.md) |
| Sửa định dạng Telex/tiền tố lồng, đo lại CNN và ViDeBERTa | [Nhận định](SUA_DINH_DANG_TIEN_TO_V1.md), [số đo/output](../danh_gia/ket_qua/sua_dinh_dang_v1_01/BAO_CAO.md) |
| Phân loại 152/155 ca dev khó thiếu phương án, bằng chứng sau nhận diện | [Chẩn đoán](CHAN_DOAN_BEAM_V1.md), [thống kê và toàn bộ beam](../danh_gia/ket_qua/chan_doan_beam_v1_01/) |
| Ma trận 12 cấu hình luật/CRF/CNN/ViDeBERTa trên cùng CPU và pipeline | [Kết luận](DO_MA_TRAN_MODEL_V1.md), [bảng số đo](../danh_gia/ket_qua/ma_tran_v1_01/BAO_CAO.md) |
| Sửa lõi giữ nguyên CNN/ranker: tra tên và bảo vệ ranh giới đường | [Nhận định và cách chạy](SUA_PIPELINE_CNN_V1.md), [số đo tách từng sửa](../danh_gia/ket_qua/sua_pipeline_cnn_v1_01/BAO_CAO.md), [mọi câu thay đổi](../danh_gia/ket_qua/sua_pipeline_cnn_v1_01/thay_doi_tung_cau.csv) |
| ViDeBERTa đã train trên T4, số đo CPU Colab và đối chiếu CRF/CNN | [Tổng kết](../danh_gia/ket_qua/videberta_v1_01_colab/TONG_KET.md), [kiểm chứng 49 file và output](../danh_gia/ket_qua/videberta_v1_01_colab/KIEM_TRA_NHAP.json), [input/nhãn/output đúng sai](../danh_gia/ket_qua/videberta_v1_01_colab/VI_DU_DUNG_SAI.json) |
| Sửa lỗi Colab Windows/Linux, khôi phục notebook sạch, gói v2 | [Ghi chú sửa](../colab/kiem_tra/SUA_LOI_COLAB_V2.md), [kiểm chứng ZIP v2](../colab/kiem_tra/BUNDLE_V2_KIEM_TRA.json), [ZIP v2](../colab/dist/nlp_dia_chi_colab_v2.zip) |
| Rà soát các ô sửa Gemini trong notebook Colab | [Báo cáo](../colab/kiem_tra/gemini_review_01/BAO_CAO.md), [đối chiếu và tái hiện cú pháp](../colab/kiem_tra/gemini_review_01/KIEM_TRA.json) |
| Luồng Colab đọc và ghi thẳng Drive, không dùng widget upload | [Notebook Drive](../colab/ViDeBERTa_Drive.ipynb), [biên nhận chuyển file](../colab/kiem_tra/DRIVE_TRANSFER.json), [hướng dẫn](../colab/README.md) |
| Gói ViDeBERTa để train GPU trên Colab | [Hướng dẫn](../colab/README.md), [notebook](../colab/ViDeBERTa_Colab.ipynb), [ZIP v2](../colab/dist/nlp_dia_chi_colab_v2.zip), [kiểm tra gói](../colab/kiem_tra/) |
| Kết quả Char-CNN + CRF và LightGBM Ranker mới nhất | [Tổng kết](../danh_gia/ket_qua/char_v1_01_cuoi/TONG_KET.md), [thống kê](../danh_gia/ket_qua/char_v1_01_cuoi/thong_ke.json), [kiểm chứng](../danh_gia/ket_qua/char_v1_01_cuoi/KIEM_TRA.json) |
| Chạy, train lại và kiểm tra bản neural | [Hướng dẫn Char-CNN](THU_NGHIEM_CHAR_CNN_V1.md) |
| Input, nhãn và output neural/đối chứng | [Thư mục kết quả đầy đủ](../danh_gia/ket_qua/char_v1_01_cuoi/), [so sánh lỗi](../danh_gia/ket_qua/char_v1_01_cuoi/so_sanh_loi.csv), [ví dụ đúng/sai](../danh_gia/ket_qua/char_v1_01_cuoi/VI_DU_DUNG_SAI.json) |
| Thử nghiệm CRF trước đó | [Hướng dẫn và nhận định](THU_NGHIEM_CRF_V1.md), [tổng kết số đo](../danh_gia/ket_qua/crf_v1_01/TONG_KET.md) |
| Luật v3 và thay đổi so với v2 | [Ghi chú sửa lỗi](SUA_LOI_PIPELINE_V3.md), [báo cáo](../danh_gia/ket_qua/ban_thu_v3_cuoi/BAO_CAO.md), [so sánh](../danh_gia/ket_qua/ban_thu_v3_cuoi/SO_SANH.md) |
| Chẩn đoán hướng đi và lỗi nhãn | [Nhận định](DANH_GIA_HUONG_DI_PIPELINE.md), [chẩn đoán](../danh_gia/ket_qua/chan_doan_v2_02/BAO_CAO.md), [rà soát ngữ nghĩa](../danh_gia/ket_qua/chan_doan_v2_02/RA_SOAT_NGU_NGHIA.md) |
| Kiểm tra hai gói dữ liệu agy, lần 4 mới nhất | [Tóm tắt](antigravity_rpc/KIEM_TRA_HAI_TASK_AGY_LAN_4_20261029.md), [báo cáo và fixture độc lập](../bao_cao/2026-10-29/kiem_tra_agy_lan_4/BAO_CAO.md) |
| Kiểm tra hai gói dữ liệu agy, lần 3 trước đó | [Báo cáo](antigravity_rpc/KIEM_TRA_HAI_TASK_AGY_LAN_3_20261029.md), [fixture và chứng cứ](../bao_cao/2026-10-29/kiem_tra_agy_lan_3/) |
| Thiết kế và hợp đồng nhãn | [Thiết kế lõi](THIET_KE_LOI.md), [hợp đồng nhãn](HOP_DONG_NHAN_CHUAN_HOA.md) |

Char-CNN hiện vẫn là tùy chọn thử nghiệm; mặc định giữ luật v3. Các tỷ lệ
đo trên dev là độ khớp nhãn máy/tổng hợp, không tự trở thành độ chính xác
gold. Báo cáo dữ liệu agy phản ánh đúng thời điểm từng lần kiểm tra, không
thay thế kết luận của một lần kiểm tra mới hơn.

## Toàn bộ gói lưu trữ từ hội thoại

Các gói giữ nguyên nội dung, tên file, JSON/CSV/JSONL, kiểm chứng, fixture,
checkpoint và bản mã tham chiếu đã có trong nguồn bàn giao. Không cần
thư mục hội thoại để đọc các file đã sao chép.

| Gói | Nội dung |
|---|---|
| [ban_thu_pipeline_v1](../bao_cao/2026-10-29/ban_thu_pipeline_v1/) | Pipeline dùng luật ban đầu, thống kê, output và hướng dẫn |
| [sua_nen_pipeline_v2](../bao_cao/2026-10-29/sua_nen_pipeline_v2/) | Sửa nền, kiểm chứng và so sánh v1 → v2 |
| [chan_doan_huong_di_v2](../bao_cao/2026-10-29/chan_doan_huong_di_v2/) | Oracle, lỗi từng tầng, rà ngữ nghĩa và kết luận hướng đi |
| [sua_loi_pipeline_v3](../bao_cao/2026-10-29/sua_loi_pipeline_v3/) | Luật v3, hợp đồng nhãn và so sánh từng mẫu |
| [thu_nghiem_crf_v1](../bao_cao/2026-10-29/thu_nghiem_crf_v1/) | Hai CRF CPU, mô hình, thống kê và ca sai |
| [thu_nghiem_char_v1](../bao_cao/2026-10-29/thu_nghiem_char_v1/) | Neural + ranker, mô hình, mã tham chiếu, thống kê, tốc độ/RAM và output |
| [kiem_tra_agy_duyet_test](../bao_cao/2026-10-29/kiem_tra_agy_duyet_test/) | Chứng cứ kiểm tra lượt duyệt test trước đây |
| [kiem_tra_hai_task_agy](../bao_cao/2026-10-29/kiem_tra_hai_task_agy/) | Kiểm tra độc lập ban đầu cho hai task dữ liệu |
| [kiem_tra_agy_lan_2_20261029](../bao_cao/2026-10-29/kiem_tra_agy_lan_2_20261029/) | Audit test, train, provenance và giữ dữ liệu cũ, lần 2 |
| [kiem_tra_agy_lan_3](../bao_cao/2026-10-29/kiem_tra_agy_lan_3/) | Audit lần 3, fixture âm độc lập và đối chiếu dữ liệu |
| [kiem_tra_agy_lan_4](../bao_cao/2026-10-29/kiem_tra_agy_lan_4/) | Audit mới: 2.669 mẫu, provenance, 400 test, fixture âm và đối chiếu nguồn pháp lý |

Các tài liệu rời cũng đã có trong cùng thư mục lưu trữ:

- [Bàn giao dự án](../bao_cao/2026-10-29/ban_giao_du_an.md).
- [Đối chiếu pipeline trong session Claude](../bao_cao/2026-10-29/pipeline_claude_doi_chieu.md).
- [Rà soát thiết kế](../bao_cao/2026-10-29/ra_soat_thiet_ke.md).
- [Kiểm tra kết quả agy](../bao_cao/2026-10-29/kiem_tra_ket_qua_agy.md).
- [Kiểm tra hai task agy](../bao_cao/2026-10-29/kiem_tra_hai_task_agy_20261029.md).
- [Kiểm tra agy duyệt test](../bao_cao/2026-10-29/kiem_tra_agy_duyet_test.md).
- [Hướng dẫn RPC agy đã bàn giao](../bao_cao/2026-10-29/HUONG_DAN_AGY_APP_RPC.md).

## Nơi lưu các lần làm tiếp

- Báo cáo hướng dẫn, thiết kế và nhận định: `docs/`.
- Số đo, lỗi và output từng mẫu: thư mục riêng theo lần chạy trong `danh_gia/ket_qua/`.
- Checkpoint, metadata huấn luyện và snapshot dữ liệu: `mo_hinh/thu_nghiem/`.
- Audit agy: báo cáo ở `docs/antigravity_rpc/`, gói chứng cứ lưu trong dự án.
- Mỗi lần có báo cáo mới, cập nhật mục lục này; bản đưa lên hội thoại là
  bản sao để xem thuận tiện, không phải nơi lưu duy nhất.
