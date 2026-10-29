# Sửa lõi với CNN/ranker giữ nguyên — 29/10/2026

Đã chạy đối chứng trên snapshot train/dev cũ. Không train lại CNN/ranker,
không đổi nhãn hoặc dữ liệu. Baseline tái hiện **toàn bộ output từng câu**
của lần CNN trước, không chỉ cùng điểm tổng.

| Cấu hình | Dev gốc / 1.136 | Dev khó / 464 |
|---|---:|---:|
| CNN + ranker cũ | 893 — 78,609% | 280 — 60,345% |
| Chỉ tra tên từ train | 941 — 82,835% | 295 — 63,578% |
| Chỉ bảo vệ ranh giới đường | 893 — 78,609% | 281 — 60,560% |
| Kết hợp hai sửa | 941 — 82,835% | 296 — 63,793% |

Kết hợp sửa đúng thêm 48 câu dev gốc, 16 câu dev khó; không có câu trước
khớp đủ sáu trường bị sai thêm trong hai tập đã đo. Tốc độ trên CPU laptop
một luồng, đã nạp model: trung bình 14,08 / 15,67 ms, P95 21,29 / 35,50 ms.
Không diễn giải chênh lệch tốc độ giữa các lượt thành tăng tốc: cache và tải
máy có thể làm thay đổi thời gian. Đây là khớp nhãn máy/tổng hợp trên dev
đã dùng để phát triển, chưa phải gold độc lập.

## Đổi những gì

### Tra tên đường

Từ điển có 1.018 cặp tên/tỉnh, chỉ lấy từ 4.841 hàng `train_cnn.jsonl`
đã đóng băng. Chỉ dùng hàng cho phép nhãn chuẩn, có span đường căn chỉnh
được với tên chuẩn bằng dạng không dấu hoặc viết tắt. Không lấy nhãn dev,
test hoặc train_ranker để lập từ điển. Không tạo thêm mẫu địa chỉ.

Tra cứu dùng **tỉnh pipeline dự đoán**, không dùng tỉnh tham chiếu. Giữ loại
đường, giữ dấu đã nhập; chỉ khôi phục/mở rộng khi khóa có duy nhất một tên
trong tỉnh. Thiếu tỉnh, tên chưa thấy, khóa trùng tên hoặc dấu mâu thuẫn
thì giữ đầu ra cũ. Không đoán typo.

Đây là tên lấy từ nhãn train, **chưa phải danh mục đường được chứng thực**.
Khi đổi có cảnh báo `ten_duong_tham_chieu_train_chua_xac_minh`, SHA-256,
ID train làm căn cứ và giá trị trước/sau trong dấu vết; đoạn gốc và offset
không đổi. Dạng tra cứu chỉ là từ điển tên theo tỉnh, không chứng minh con
đường thật sự nằm trong phường/xã đang xuất ra.

Ví dụ output đo được:

- `72 duong Doi Can, Xa Nga Lien, Huyen Nga Son, Thanh Hoa`:
  `Đường Doi Can` → `Đường Đội Cấn`; năm trường còn lại giữ nguyên, khớp nhãn.
- Tra tên riêng đóng góp 48 câu khớp thêm ở dev gốc và 15 câu ở dev khó.

### Bảo vệ ranh giới đường

Không lấy một ứng viên hành chính không tiền tố nằm hoàn toàn trong span
CNN gán là đường có tiền tố rõ ràng. Ứng viên có tiền tố hành chính vẫn giữ.
Đây là sửa xung đột sau nhận diện, không thay trọng số hoặc nhãn CNN.

Ví dụ dev khó `Số 554, Đường Nguyễn Thị Minh Khai, Huyện Thạch An,
Tỉnh Cao Bằng`: trước đó bị lấy `Minh Khai` làm xã, đường bị cắt thành
`Đường Nguyễn Thị`. Sau sửa giữ đủ đường và không tự điền xã; khớp nhãn.

Hai ca dev gốc cho thấy giới hạn của nhãn: `244, Đường Điện Biên Phủ`
và `30/13, Đại lộ Bình Dương` không cung cấp địa phương riêng. Sửa giữ
đủ tên đường và bỏ tỉnh từng suy ra từ chữ trong tên đường. Nhãn cũ vẫn
yêu cầu tỉnh `11` và `79`, nên hai câu vẫn bị tính sai. Đã ghi riêng,
không tự sửa nhãn để tăng điểm.

## Phần còn lại

Sau hai sửa còn 195 câu chưa khớp dev gốc và 168 câu dev khó:

| Loại sai sáu trường | Dev gốc | Dev khó |
|---|---:|---:|
| Chỉ chi tiết | 141 | 145 |
| Chỉ mã hành chính | 36 | 13 |
| Cả hai | 18 | 10 |

Trong đó có 46 / 50 câu chỉ khác dấu; tên đường tham chiếu tương ứng đều
chưa có trong từ điển train **theo tỉnh tham chiếu**. Đây là phân tích hậu
kiểm, không đưa reference vào inference. Nó cho thấy thiếu độ phủ tên còn
gây mất điểm, không chứng minh mọi câu sai còn lại là thiếu từ điển.

Các lỗi còn lại vẫn gồm cắt/ghép span, viết tắt/typo chưa giải được,
quyết định hành chính/mơ hồ và nhãn thiếu hoặc sai. Không thể suy từ kết
quả này rằng thêm tên đường là sẽ đạt 95%. Cần danh mục có căn cứ và lượt
đánh giá ngữ nghĩa độc lập trước khi khẳng định độ chính xác thực tế.

## Chạy và kiểm chứng

Các sửa đang là tùy chọn để so sánh và kiểm chứng; luật mặc định giữ nguyên.
Từ thư mục dự án:

```powershell
.\.venv-neural\Scripts\python.exe -X utf8 -B -m src 'Số 30, Đường le loi, phuong xuan khanh, quan ninh kieu, thanh pho can tho' --char-model mo_hinh/thu_nghiem/char_v1_01/char_cnn.pt --ranker mo_hinh/thu_nghiem/char_v1_01/ranker.txt --tu-dien-duong danh_gia/ket_qua/sua_pipeline_cnn_v1_01/tu_dien_duong_train.json --bao-ve-duong --threads 1
```

Đo lại vào thư mục mới (từ chối ghi đè):

```powershell
.\.venv-neural\Scripts\python.exe -X utf8 -B -m danh_gia.do_sua_pipeline_cnn --output danh_gia/ket_qua/sua_pipeline_cnn_lan_moi
```

- [Báo cáo số đo](../danh_gia/ket_qua/sua_pipeline_cnn_v1_01/BAO_CAO.md).
- [Thống kê đầy đủ và hash dữ liệu/model](../danh_gia/ket_qua/sua_pipeline_cnn_v1_01/thong_ke.json).
- [Mọi câu thay đổi, gồm input/nhãn/trước/sau](../danh_gia/ket_qua/sua_pipeline_cnn_v1_01/thay_doi_tung_cau.csv).
- [Chẩn đoán phần còn lại và ví dụ](../danh_gia/ket_qua/sua_pipeline_cnn_v1_01/CHAN_DOAN_SAU_SUA.json).
- [Output dev gốc sau sửa](../danh_gia/ket_qua/sua_pipeline_cnn_v1_01/ket_hop_dev_goc.jsonl).
- [Output dev khó sau sửa](../danh_gia/ket_qua/sua_pipeline_cnn_v1_01/ket_hop_dev_kho.jsonl).

Các hash CNN, ranker, bốn tập prepared và toàn bộ snapshot được kiểm trước/
sau phép đo; code thực thi có bản sao và SHA-256 trong thư mục kết quả.
Đã chạy 79 bài kiểm thử, tất cả đạt; gồm fixture độc lập về dấu đã nhập,
va chạm viết tắt, thiếu/sai tỉnh, provenance và xung đột đường–hành chính.
[Log kiểm thử](../danh_gia/ket_qua/sua_pipeline_cnn_v1_01/KIEM_THU.txt).
