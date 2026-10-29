# Kiểm tra nhanh

Vài chục ca mẫu kèm đáp án để chạy sau mỗi lần sửa code. Đây không phải tập test dùng để chấm điểm trong báo cáo (tập đó nằm ở `data/test`).

Các kiểm tra của bản thử chỉ đọc danh mục và dùng ca hành vi độc lập, không ghi vào dữ liệu:

```powershell
py -3.12 -X utf8 -B -m unittest discover -s tests -p 'test_pipeline*.py' -v
py -3.12 -X utf8 -B -m unittest discover -s tests -p test_danh_gia.py -v
```

`test_pipeline.py` kiểm tra trộn mốc, đảo thứ tự, quan hệ tại nguồn, mã trùng giữa hai mốc, xã bị chia, thiếu tỉnh, tên đường trùng tỉnh, số nhà có '/', dấu vết Unicode và huyện chuyển nguyên thành đặc khu. `test_danh_gia.py` kiểm tra cách chấm trường trống, căn chỉnh nhãn và chặn việc dùng test cuối.

Bản sửa nền v2 có 30 bài kiểm tra pipeline (có thêm các biến thể trong từng bài) và 4 bài kiểm tra cách chấm. Các hồi quy mới gồm Tô/Tổ, Tĩnh/Tỉnh, cụm Thành phố, Xã Bản Xèo/Phường Phố Mới/Xã Đường Lâm, Xa lộ/Xã Lộ, số dính P7/ngõ5, tên đường chứa từ hành chính, dấu vết Unicode phân rã và giữ huyện đã ghi rõ khi xã mâu thuẫn.

`test_review_validation.py` thuộc quy trình kiểm tra dữ liệu và metadata duyệt, tách biệt với các kiểm tra pipeline.

Thử nghiệm CRF có thêm 8 bài ở `test_crf.py`: BIO/ranh giới, không nối qua đoạn hành chính, không làm đẹp F1 bằng O, căn chỉnh nhãn, tokenizer không tương thích và train/lưu/nạp/chạy API thật. Chạy bằng `.venv-crf\Scripts\python.exe -X utf8 -B -m unittest discover -s tests -p test_crf.py -v`; bài train thật được skip nếu chưa cài `requirements-crf.txt`. Tổng lượt kiểm tra lõi này: 41 pipeline + 4 cách chấm + 8 CRF = 53.

V3 có tổng 41 bài kiểm tra pipeline: 30 bài cũ và 11 bài trong `test_pipeline_v3.py`. Các ca mới kiểm tra dấu đã nhập/thiếu dấu/mơ hồ cũ mới, tên có đuôi số, ba dấu nháy và offset NFD, cụm số nhà, tránh lấy số đường làm số nhà, chặn suy đường từ lô/khu dân cư và giữ tên gần dấu như Lò Đúc/Tăng Bạt Hổ. Đây là ca hồi quy viết tay, không được thêm vào train/dev hay test cuối. Bốn bài kiểm tra cách chấm giữ riêng.
