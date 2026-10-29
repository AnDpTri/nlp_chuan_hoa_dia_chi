# Chạy và kiểm chứng bản thử pipeline

Bản mặc định ngày 29/10/2026 chạy luật offline bằng thư viện chuẩn Python 3.12. Đã có [thử nghiệm CRF CPU](THU_NGHIEM_CRF_V1.md) với thư viện tùy chọn và `--crf-model`; logistic regression chưa huấn luyện. Hướng dẫn bên dưới mô tả bản luật dùng làm mốc.

Phiên bản hiện tại là [v3](SUA_LOI_PIPELINE_V3.md): giữ dấu khi chấm tên, xét đầy đủ đuôi tên, hỗ trợ dấu nháy nội tên, cụm số nhà và hạn chế suy đường. Kết quả ở `danh_gia/ket_qua/ban_thu_v3_cuoi/`; v1/v2 giữ làm mốc trước sửa. Quy ước rà dữ liệu tại [hợp đồng nhãn](HOP_DONG_NHAN_CHUAN_HOA.md).

## Chạy một địa chỉ

```powershell
Set-Location -LiteralPath 'D:\nlp_chuan_hoa_dia_chi'
py -3.12 -X utf8 -B -m src 'Số 12, Ngõ 5, Đường Lê Lợi, Phường Trúc Bạch, Quận Ba Đình, Hà Nội'
```

Lệnh in JSON gồm các trường chi tiết, tên/mã hành chính mới, địa chỉ ghép, cảnh báo, xã đích ứng viên khi chưa quyết định được và dấu vết đoạn chữ gốc. Ca trên chuyển Trúc Bạch cũ sang Ba Đình mới; huyện chỉ hỗ trợ xác định, không xuất trong địa chỉ chuẩn.

Gọi trong Python để xử lý nhiều chuỗi với một lần nạp danh mục:

```python
from dataclasses import asdict
from src.chuan_hoa import BoChuanHoa

bo = BoChuanHoa(beam=40)
ket_qua = asdict(bo.chuan_hoa("Phường Ba Đình, quận Ba Đình, Hà Nội"))
```

Không khởi tạo `BoChuanHoa` mới cho từng dòng khi xử lý một lô.

## Pipeline đã cài đặt

1. Tách token kèm khoảng ký tự trong chuỗi gốc, giữ cả dấu câu và số nhà có '/'. Tách được một số dạng dính chữ có ranh giới viết hoa như `DịchVọng`.
2. Tra trie tên cũ và mới, dạng không dấu, tiền tố viết tắt và một số bí danh tỉnh. Tìm gần đúng Levenshtein một ký tự khi có tiền tố hành chính rõ ràng và tên đủ dài.
3. Beam search giữ các tổ hợp không chồng đoạn và tương thích cả quan hệ nguồn lẫn chuyển đổi đích. Các thành phần trong một tổ hợp có thể thuộc các mốc khác nhau; không yêu cầu thứ tự tỉnh/huyện/xã trong input.
4. Với từng tổ hợp, dùng luật tách số nhà, ngõ/ngách/hẻm, thôn/xóm và đường trên các đoạn còn lại. Luật dùng vị trí sau số nhà/ngõ để nhận một số đường không có tiền tố, kèm cảnh báo.
5. Xếp hạng bằng trọng số đặt tay, có xét phần chưa phân loại. Gộp các cách hiểu gần điểm cùng kết quả; khác kết quả thì cảnh báo và để trống phần chưa đồng thuận. Điểm không phải xác suất đã hiệu chuẩn.
6. Chuyển về mốc 01/07/2025 bằng danh mục và bảng đối chiếu. Xã nhiều đích chưa đủ thông tin thì giữ danh sách ứng viên. Huyện chỉ được chuyển trực tiếp thành đặc khu khi bảng đối chiếu nói rõ chuyển toàn bộ huyện.

Danh mục và trie ở trong RAM, dựng một lần lúc khởi tạo từ sáu CSV sạch. Cache tra tên có giới hạn 16.000 khóa; chưa có cache ghi ra ổ đĩa. Khóa thực thể luôn có mốc cùng mã để tránh nhầm các mã được dùng lại giữa hai mốc.

## Đo trên tập dev

```powershell
py -3.12 -X utf8 -B -m danh_gia.chay_ban_thu --output-dir danh_gia/ket_qua/lan_do_moi
```

Script mặc định đọc `data/train_dev/dev.csv`, từ chối đọc đầu vào trong `data/test` và không sửa train/dev hoặc danh mục. Thư mục kết quả phải chưa tồn tại. Mã băm input và sáu danh mục được ghi lại và đối chiếu sau khi đo để phát hiện thay đổi đồng thời.

Lần đo hiện tại lưu tại `danh_gia/ket_qua/ban_thu_v3_cuoi/`:

| Tệp | Nội dung |
|---|---|
| `BAO_CAO.md` | Bảng chỉ số, nhóm nguồn/biến thể, tốc độ, RAM và giới hạn |
| `thong_ke.json` | Chỉ số đầy đủ, cấu hình, môi trường và mã băm dữ liệu |
| `du_doan.jsonl` | Kết quả, cảnh báo và dấu vết từng mẫu |
| `loi_tung_truong.csv` | Các chênh lệch giữa pipeline và nhãn tham chiếu |
| `can_chinh_nhan.csv` | Khả năng định vị nội dung nhãn chi tiết trong token input |
| `code_sha256.json` | Mã băm source của lần đo |

So khớp NFC, không phân biệt chữ hoa và gom khoảng trắng, nhưng vẫn phân biệt dấu. Tỷ lệ khớp từng trường có tính cả trường trống; xem thêm recall trên nhãn khác rỗng và precision trên dự đoán khác rỗng. Tỷ lệ khớp toàn bộ sáu trường tính bốn trường chi tiết cùng hai mã xã/tỉnh. Có bảng riêng cho nguồn OSM, tổng hợp và các biến thể.

Thời gian đo chỉ tính lời gọi pipeline, không gồm chuyển kết quả sang dict, đọc/ghi file hoặc chẩn đoán. Một lượt tuần tự, không warm-up riêng; cache được dùng tự nhiên trong lượt chạy. RAM đo working set của cả tiến trình đánh giá, có cả dữ liệu và kết quả đang giữ; không dùng trực tiếp làm dự toán cấu hình cloud.

## Kiểm tra hành vi

```powershell
py -3.12 -X utf8 -B -m unittest discover -s tests -p 'test_pipeline*.py' -v
py -3.12 -X utf8 -B -m unittest discover -s tests -p test_danh_gia.py -v
```

## Giới hạn cần hiểu khi đọc kết quả

- Nhãn dev gồm nhãn máy và dữ liệu tổng hợp; chênh lệch chưa khẳng định pipeline sai hay nhãn sai. Thống kê không phải điểm đánh giá cuối.
- Chưa có từ điển đường/thôn để khôi phục dấu. CRF dự kiến tách vai trò của token, không tự giải quyết việc xác minh tên chính thức.
- Địa chỉ không có tiền tố, thiếu dấu câu hoặc có tên đường trùng tên hành chính còn có thể bị bỏ sót hay phân tích nhầm.
- Số nhà dạng `12/5`, `24B-24`, `1031F;1031G` được giữ nguyên và cảnh báo vì chưa có căn cứ chắc chắn để diễn giải thành nhà/ngõ, khoảng số hoặc nhiều địa chỉ.
- Kiểm tra căn chỉnh nhãn chỉ tìm nội dung tương ứng trong token, có cho phép khác dấu và tiền tố chuẩn hóa; chưa tạo BIO. Nhãn trùng vị trí, không tìm thấy hoặc chồng nhau cần được xử lý trước khi huấn luyện CRF.
- Chưa có giao diện web hoặc nhập Excel. Script đánh giá hiện xử lý một file dev CSV; lõi hỗ trợ một chuỗi mỗi lần gọi và có thể dùng lại một instance cho cả lô.

Các phép đo này là mốc ban đầu. Bước tiếp theo là phân tích lỗi trên dev, chuẩn bị nhãn span hợp lệ rồi so sánh CRF với luật ở cùng cấu hình và cách chấm.
