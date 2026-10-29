# Đánh giá

- [Mục lục toàn bộ báo cáo](../docs/MUC_LUC_BAO_CAO.md): liên kết báo cáo hiện hành và các gói chứng cứ đã lưu trong dự án.
- `ket_qua/char_v1_01_cuoi/`: kết quả Char-CNN + CRF và LightGBM Ranker mới nhất; [tổng kết](ket_qua/char_v1_01_cuoi/TONG_KET.md), [hướng dẫn train/chạy/đo](../docs/THU_NGHIEM_CHAR_CNN_V1.md). `ket_qua/char_v1_01/` là lượt đo trước sửa tra cứu, giữ làm lịch sử.
- `huan_luyen_crf.py`, `du_lieu_crf.py`: chuẩn bị span từ snapshot và train hai đối chứng CPU, không dùng nhãn test cuối. `do_crf.py`: token/BIO, span, field, mã hành chính, end-to-end, nguồn/biến thể, latency và so sánh từng mẫu. `viet_tong_ket_crf.py`: dựng tài liệu từ số đo đã lưu.
- `ket_qua/crf_v1_01/`: toàn bộ kết quả CRF, gồm cả cấu hình tốt/kém hơn và fixture đảo thứ tự. Xem [tổng kết CRF](../docs/THU_NGHIEM_CRF_V1.md). Mô hình/snapshot ở `mo_hinh/thu_nghiem/crf_v1_01/`; mặc định vẫn giữ luật v3.
- `ket_qua/ban_thu_v3_cuoi/`: lần đo hiện tại sau sửa lỗi theo chẩn đoán. `SO_SANH.md` và `so_sanh_tung_mau.csv` đối chiếu với v2, có 32 mẫu mới khớp và 1 mẫu mất khớp sáu trường. Xem [ghi chú v3](../docs/SUA_LOI_PIPELINE_V3.md). Trình so sánh dùng nhãn phiên bản thật và các cột trước/sau.
- `chan_doan_pipeline.py`: chẩn đoán source v2 cố định trên dev; đo đích qua bộ sinh/beam, nhánh khớp nhãn, tác động xếp hạng/quyết định, điền/trống và cảnh báo theo nguồn. Kết quả `ket_qua/chan_doan_v2_02/`; xem [đánh giá hướng đi](../docs/DANH_GIA_HUONG_DI_PIPELINE.md). Có đối chứng beam 160 để chẩn đoán, không đổi cấu hình chạy chính. Không coi oracle hoặc lệch nhãn là độ chính xác ngữ nghĩa đã xác minh.
- `ra_soat_chan_doan_v2.json`: ghi chú rà 33 ca, gồm toàn bộ 20 ca lệch không cảnh báo; không sửa nhãn. Bản đầy đủ input/output/tham chiếu nằm trong `ket_qua/chan_doan_v2_02/RA_SOAT_NGU_NGHIA.md`.
- `chay_ban_thu.py`: chạy pipeline dùng luật trên dev, thống kê từng trường, nguồn/biến thể, cảnh báo xã bị chia, lỗi, tốc độ, RAM và khả năng căn chỉnh nhãn cho CRF. Script từ chối đầu vào trong `data/test`; không gọi API hoặc huấn luyện.
- `ket_qua/ban_thu_v2_cuoi/`: kết quả sau sửa nền, có so sánh từng mẫu với v1 trong `SO_SANH_V1_V2.md` và `so_sanh_tung_mau.csv`. Xem [ghi chú sửa nền](../docs/SUA_NEN_PIPELINE_V2.md).
- `ket_qua/ban_thu_v1_02/`: lần đo sau khi tách thời gian chuyển kết quả sang dict ra khỏi thời gian pipeline. Xem `BAO_CAO.md`, `thong_ke.json` và kết quả từng mẫu trong thư mục này. Lần đo sơ bộ `ban_thu_v1/` có tính cả chuyển dataclass sang dict trong thời gian, không dùng để dẫn số tốc độ của bản cuối.
- `cham_diem.py` (chưa có): đánh giá cuối trên tập test khi phiên bản nhãn và hệ thống đã được chốt.
- `chay_moc.py` (chưa có): chạy các thư viện có sẵn (`vietnamadminunits`, `vietnam-address-converter`) trên cùng tập test để làm mốc so sánh.

Từ thư mục gốc dự án, tạo **thư mục kết quả mới** cho mỗi lần đo:

```powershell
py -3.12 -X utf8 -B -m danh_gia.chay_ban_thu --output-dir danh_gia/ket_qua/lan_do_moi
```

Chi tiết cách đọc chỉ số và giới hạn: [hướng dẫn bản thử](../docs/HUONG_DAN_BAN_THU.md). Nhãn dev hiện là nhãn máy/tổng hợp; mức khớp với nhãn không phải xác nhận độc lập về độ chính xác thực tế.
