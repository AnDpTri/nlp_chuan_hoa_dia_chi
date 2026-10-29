# Huấn luyện ViDeBERTa-xsmall trên Google Colab

**Bản sửa v2:** dùng `nlp_dia_chi_colab_v2.zip`. Đã sửa đọc key manifest
Windows trên Linux ở bước kiểm tra, train và đánh giá; giữ nguyên bytes
dữ liệu. Notebook in và lưu stdout/stderr của tiến trình con, nên lỗi gốc
và ETA train hiện ngay trong ô. Verify/test thất bại vẫn chặn, không bị nuốt lỗi.
Các ô vá trực tiếp do Gemini thêm được bỏ khi khôi phục notebook sạch;
bản notebook trước sửa được backup. Gói v1 giữ nguyên để đối chiếu.

**Luồng Drive hiện dùng:** ZIP đã được chép qua Google Drive for desktop
vào `G:\My Drive\nlp_chuan_hoa_dia_chi\`. Bản `ViDeBERTa_Drive.ipynb`
đọc ZIP trực tiếp từ Drive, kiểm SHA-256 rồi giải nén vào `/content`.
Checkpoint và ZIP kết quả lưu ngược về Drive; không dùng widget upload/download.
Notebook đã tải lên Colab trước đó cũng được sửa nội dung tại chỗ trên
ổ Drive; bản gốc có backup trong `colab/kiem_tra/drive_backup/`.
Biên nhận chuyển file ở `colab/kiem_tra/DRIVE_TRANSFER.json`.
Đồng bộ lên server do Drive for desktop thực hiện. Quyền mount Drive trong
runtime Colab vẫn do cơ chế đăng nhập Google quản lý, không lấy cookie/token.

Lệnh tạo/cập nhật bản Drive bằng filesystem:

```powershell
py -3.12 -X utf8 -B -m colab.prepare_drive --drive-root 'G:\My Drive'
```

Các bước upload thủ công bên dưới giữ cho gói cũ và máy không có Drive for desktop.

Gói này chuẩn bị cho chạy Colab; **chưa fine-tune ViDeBERTa đầy đủ và chưa
có số đo chất lượng/tốc độ của mô hình này**. Không train GPU tại máy.

## Bắt đầu

1. Mở https://colab.research.google.com/ → File → Upload notebook, chọn
   `ViDeBERTa_Colab.ipynb` trong thư mục `colab/` của dự án.
2. Chọn Runtime → Change runtime type → GPU. T4 đủ cho cấu hình thử này.
3. Chạy từng ô notebook. Ở ô upload, chọn `nlp_dia_chi_colab_v1.zip` từ
   `colab/dist/` của dự án.
4. Giữ `USE_DRIVE = True` để model/resume được lưu vào Drive sau mỗi epoch.
   Notebook sẽ yêu cầu đăng nhập Drive khi chạy ô mount. Không cần token
   Hugging Face hoặc GitHub: checkpoint là public và commit được chốt.
5. Sau train, chạy ô đánh giá CPU và ô xuất ZIP kết quả để tải về máy.

Ước lượng trước khi chạy: train GPU khoảng **10–30 phút** cho 5 epoch;
phụ thuộc GPU Colab cấp, batch và I/O Drive. Sau 10 batch sẽ có ETA từng
epoch từ thời gian thực. Chuẩn bị, train ranker, đánh giá và xuất ZIP cần
thêm thời gian. Độ trễ CPU chưa đo; không dùng dự đoán làm benchmark.

## Những gì đã đóng gói

- Mã nhận diện, chuẩn hóa, tra cứu, xếp hạng, huấn luyện, đánh giá và test.
- Dữ liệu đóng băng: 4.841 mẫu train bộ nhận diện; 1.169 mẫu train ranker
  riêng; 1.136 dev gốc cho end-to-end (1.026 có nhãn span); 464 dev khó.
- Sáu CSV danh mục và snapshot train/dev trước đó; model CRF cũ làm đối chứng.
- Manifest SHA-256 từng file; kiểm tra lại khi giải nén, trước huấn luyện.
- **Không có nhãn test cuối, thư mục venv, cache GPU, lịch sử hội thoại hoặc
  token tài khoản.** Không sinh thêm câu train.
- Trọng số ViDeBERTa pretrained không nằm trong ZIP; tải trực tiếp trên
  Colab từ `Fsoft-AIC/videberta-xsmall`, commit
  `029b6b1b1d7636221bd2d1a98b46a2fdba3af34e`.

## Thiết kế lần thử

Backbone có tiền huấn luyện tiếng Việt → biểu diễn subword → đầu ký tự
nhỏ → CRF BIO bảy vai trò. Đầu ký tự cho phép đặt ranh giới ngay bên trong
subword, ví dụ `151Đ.`, để không phải ép span đúng vào ranh giới tokenizer.

Theo quy trình tiền huấn luyện của dự án ViDeBERTa, dùng PyVi tách từ.
Có ánh xạ từ chuỗi đã tách từ về NFC và chuỗi gốc. Khi PyVi đổi nội dung
không căn chỉnh được, giữ raw và ghi rõ fallback; không tự thay ký tự hay
sửa nhãn. Số fallback được ghi trong metadata và đầu ra.

Huấn luyện mặc định 5 epoch, batch 8, tích lũy gradient 2, AMP FP16 trên
GPU; AdamW, learning rate backbone 2e-5, đầu nhận diện 1e-3, warm-up 10%.
Loss kế thừa partial CRF + 0.2 CE trên ký tự có nhãn đơn. Không dùng dev
để fit, chọn checkpoint hoặc dừng sớm. Nhãn vẫn là máy/tổng hợp và căn
chỉnh yếu; kết quả dev không tự trở thành độ chính xác gold.

Ranker LambdaRank học trên 1.169 mẫu thuộc nhóm riêng, không phải câu
backbone đã fine-tune. Bảng đánh giá có luật v3, CRF cũ, ViDeBERTa dùng
điểm tay và ViDeBERTa dùng ranker. Giới hạn dữ liệu tên đường vẫn giữ như
trước; nhận ra span không đồng nghĩa đã có tên đường chuẩn.

## Resume và lỗi thường gặp

- Khi Colab ngắt, mở lại notebook, upload lại ZIP, mount cùng Drive,
  giữ `RUN_ID`, epoch/batch/gradient accumulation. Notebook nhận ra run đã
  có và bật resume. Không phải train lại từ đầu nếu đã lưu xong epoch.
- Resume lưu optimizer, scheduler, AMP scaler, RNG và toàn bộ model trong
  một `resume.pt` được thay atomically. Nếu chưa hoàn thành epoch nào,
  bắt đầu lại epoch 1. Những batch sau checkpoint cuối chưa được giữ.
- Nếu cấu hình hay dữ liệu đổi, lệnh sẽ từ chối resume; dùng `RUN_ID` mới.
- Nếu hết VRAM: run mới với batch 4, gradient accumulation 4. Không tự bỏ
  mẫu hoặc cắt ngắn địa chỉ để tiếp tục.
- Nếu pip vừa thay thư viện mà Python báo lỗi import phiên bản, restart
  runtime rồi chạy lại các ô từ đầu, giữ nguyên Drive/run.
- `colab/requirements.txt` giữ nguyên torch CUDA của Colab; không cài
  `requirements-neural.txt` trong notebook vì đó là môi trường CPU khác.
- Train không có CUDA sẽ dừng rõ ràng; không âm thầm chuyển sang CPU.
- Ô đánh giá không ghi đè thư mục kết quả đã có. Muốn đo lại thì đổi
  `reports_cpu_colab_01` thành tên mới.

## Kết quả mang về máy

ZIP kết quả chứa thư mục mang tên `RUN_ID`, bao gồm:

- `model/model.safetensors`, tokenizer, cấu hình và vocab ký tự.
- `training.json`, `run_config.json`, `ranker.txt`/`ranker.json`.
- Snapshot dữ liệu và `reports_cpu_colab_01/`: thống kê từng trường,
  span, ứng viên, beam, end-to-end, latency và input/nhãn/output từng câu.
- `SHA256_EXPORT.json` để đối chiếu mọi file đã xuất.

Không xuất optimizer/resume lớn vào ZIP; chúng vẫn nằm trên Drive.
Độ trễ trong báo cáo là **CPU Colab**, chưa phải CPU i5-11400H ở máy.
Để đo máy thật, chạy lại đánh giá CPU sau tải checkpoint về.

Giải nén ZIP kết quả vào `D:\nlp_chuan_hoa_dia_chi\mo_hinh\thu_nghiem\`.
Từ gốc dự án, dùng môi trường CPU đã có, cài thêm thư viện Transformer:

```powershell
.\.venv-neural\Scripts\python.exe -m pip install -r colab/requirements.txt
.\.venv-neural\Scripts\python.exe -X utf8 -B -m src 'Số 12, Đường Lê Lợi, Phường Trúc Bạch, Quận Ba Đình, Hà Nội' --videberta-model mo_hinh/thu_nghiem/videberta_v1_01/model --ranker mo_hinh/thu_nghiem/videberta_v1_01/ranker.txt --threads 1
.\.venv-neural\Scripts\python.exe -X utf8 -B -m colab.evaluate_videberta --run-dir mo_hinh/thu_nghiem/videberta_v1_01 --output danh_gia/ket_qua/videberta_cpu_may_01
```

Lệnh CPU không tải lại backbone từ mạng: safetensors và tokenizer đã có
trong ZIP kết quả. Đừng thay checkpoint mà giữ ranker của model khác;
checksum sẽ chặn trường hợp đó.

## Kiểm tra trước bàn giao

Đã có smoke test bằng backbone DeBERTa rất nhỏ trên CPU: gradient tới
backbone, loss CRF, lưu/nạp safetensors offline, offset Unicode NFD,
tách từ/fallback, cấm train khi thiếu GPU, xuất ZIP và bỏ optimizer.
Đây là kiểm tra đường chạy, **không phải thử nghiệm chất lượng ViDeBERTa**.
Notebook có kiểm tra các bước này trước khi chạy GPU đầy đủ.

Tokenizer đúng commit và PyVi đã mã hóa được toàn bộ **7.500 mẫu** trong
snapshot, không lỗi offset/độ dài/vocab; dài nhất 55 subword. Có 33 mẫu
fallback giữ raw khi tách từ không căn chỉnh được (24 train nhận diện,
4 train ranker, 5 dev gốc); không có mẫu nào bị bỏ. Chi tiết trong
`colab/kiem_tra/TOKENIZER_SNAPSHOT.json`. Bộ test cục bộ gồm 66 bài đạt,
trong đó 5 bài cho đường chạy ViDeBERTa/Colab bằng backbone tí hon.

Nguồn: https://huggingface.co/Fsoft-AIC/videberta-xsmall và
https://github.com/Fsoft-AIC/ViDeBERTa (mục pre-tokenizer dùng PyVi).
