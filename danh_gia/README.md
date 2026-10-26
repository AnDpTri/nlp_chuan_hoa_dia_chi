# Đánh giá

- `cham_diem.py`: ghép bằng `id`, từ chối ID trùng, chỉ chấm dòng `da_duyet`. Xuất accuracy từng trường (gồm cả trường rỗng và riêng trường không rỗng), đúng toàn bộ thành phần, chuỗi chuẩn, tỷ lệ cờ, đổi địa chỉ cũ và xử lý xã bị chia. Thiếu dự đoán tính là sai. Nếu chưa có nhãn đã duyệt thì các metric là `null`.
- `chay_moc.py`: adapter hai thư viện `vietnamadminunits==1.0.4` và `vietnam-address-converter==1.0.5`, kèm pipeline và ablation tắt fuzzy. Converter dùng mã nội bộ nên adapter chỉ ánh xạ tên đầu ra + tỉnh cha về mã của danh mục; không dùng nhãn để sửa quyết định thư viện.
- `python -m tools.benchmark_synthetic`: chạy cả bốn phương pháp trên 480 ca sinh từ danh mục, seed 42, chặn socket mạng khi suy luận. Kết quả là kiểm tra phát triển, không phải accuracy trên địa chỉ thực. Thời gian P50/P95 là từng truy vấn sau warmup, không gồm khởi tạo. Máy có thể đang chạy tác vụ khác nên không suy diễn chuẩn hiệu năng triển khai.

```powershell
python -m pip install -r requirements-baselines.txt
python -m tools.benchmark_synthetic
python -m src.cli --input data/test/dia_chi_test.csv --output results/predictions/heldout.json
python -m danh_gia.cham_diem --predictions results/predictions/heldout.json --output results/heldout_review_status.json
```

Không dùng 400 nhãn để điều chỉnh luật, từ điển hoặc trọng số. Hiện 0/400 dòng được duyệt thủ công nên chưa thể công bố độ chính xác cuối cùng. Có thể chạy lại các adapter trên cùng chuỗi đầu vào khi đủ nhãn đã duyệt; mọi adapter phải giữ cùng ID và không được chọn thuật toán dựa vào đáp án của từng dòng.
