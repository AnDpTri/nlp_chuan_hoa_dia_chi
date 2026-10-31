# Đánh giá

- `v3/`: bộ train và đo hiện hành (xem README ở thư mục gốc). `v3/train_va_do.sh` gọi `danh_gia.huan_luyen_char`.
- `huan_luyen_char.py`, `du_lieu_char.py`: train Char-CNN + CRF và ranker.
- `huan_luyen_crf.py`, `du_lieu_crf.py`, `do_crf.py`: dữ liệu và độ đo CRF (test dùng).
- `chay_ban_thu.py`, `chan_doan_pipeline.py`, `do_kiem_tra_test400.py`, `phan_tich_loi_dev_co_lap.py`, `so_sanh_hop_dong_dev.py`: script đo mà test còn gọi.
- `ket_qua/tu_dien_duong_v5.json`: từ điển đường web dùng.

Script đo cũ đã chuyển sang `luu_tru/tu_repo_20261031/danh_gia/` (không lên git). Nhãn dev ban đầu là nhãn máy; mức khớp nhãn không phải xác nhận độc lập về độ chính xác.
