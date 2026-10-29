# Rà soát thay đổi notebook sau các ô sửa Gemini

Ngày 29/10/2026. Chỉ đọc notebook và tái hiện các phép thay chuỗi trong bộ
nhớ để kiểm cú pháp; không thực thi mã các ô sửa, không sửa/hoàn tác notebook.
Bản đang xem được lưu thành `NOTEBOOK_HIEN_TAI.ipynb`; bản trước sửa là
`NOTEBOOK_TRUOC_SUA.ipynb`. Chi tiết phép so sánh ở `KIEM_TRA.json` và
`THAY_DOI.diff`, mã cùng output gốc ở `O_MA_VA_DAU_RA.json`.

## Lỗi gốc

Lỗi ban đầu thuộc gói bàn giao: manifest snapshot được tạo trên Windows,
lưu đường dẫn như `clean\cu_huyen.csv`. Colab/Linux hiểu dấu backslash là
một phần tên file nên phát sinh `FileNotFoundError`. Output ô `cell-08`
đã xác nhận đúng đường dẫn lỗi này. Trong ZIP có 12 key manifest dạng đó;
đổi separator khi đọc sẽ tìm được tất cả file, không cần đổi dữ liệu.

## Thay đổi thấy trong notebook

Notebook tăng từ 19 lên 23 ô. Một ô cũ thay mã và bốn ô mã được thêm.

1. **Ô kiểm tra `cell-08` bắt lỗi rồi không ném lại.** Phần capture stdout/stderr
   giúp đọc được lỗi gốc. Tuy nhiên `except CalledProcessError` chỉ in thông báo,
   khiến ô kết thúc bình thường dù verify thất bại; các test phía sau chưa chạy.
2. **Ô `5dd84852`, đã chạy ở execution 16:** sửa hàm `digest` trong runtime
   `danh_gia/chay_ban_thu.py` bằng regex. Tái hiện chính các literal và phép
   `re.sub` trên bản gốc tạo lỗi `SyntaxError` tại dòng 43 do escape backslash.
   Câu in “Đã sửa thành công” không kiểm tra cú pháp hoặc kết quả thay thế.
3. **Ô `16e02787`, đã chạy ở execution 17:** thay đoạn kiểm tra path trong runtime
   `colab/train_videberta.py`. Tái hiện tạo `unterminated string literal` tại
   dòng 49 vì chuỗi backslash không được escape đúng.
4. **Ô `8af3e948`, đã chạy ở execution 13:** chẩn đoán manifest theo schema sai.
   `manifest['files']` thực tế là dict, nhưng mã coi mỗi key string là object
   và truy cập `file_info['path']`. Output xác nhận `string indices must be
   integers, not 'str'`. Ô này không sửa file.
5. **Ô `ddf69ce1`, chưa có dấu vết thực thi:** đề xuất thay cả `validate_input`
   dựa trên `manifest.json` và các tập `sets['train']`/`sets['dev']` không khớp
   cấu trúc chương trình thật. Không kết luận ô này đã thay runtime.

Sửa trực tiếp hai file trong bundle cũng làm chúng không còn khớp checksum
đã bàn giao. Muốn thay mã đúng quy trình cần gói phiên bản mới có kiểm chứng,
không chỉ sửa runtime rồi tiếp tục dùng manifest cũ.

## Trạng thái và giới hạn

- Ô train `cell-12` execution 21 vẫn kết thúc bằng `CalledProcessError`.
- Không thấy thư mục run `My Drive/nlp_chuan_hoa_dia_chi/videberta_v1_01`
  tại thời điểm audit; chưa có bằng chứng lần train này thành công.
- Cấu hình notebook vẫn là 5 epoch, batch 8, gradient accumulation 2.
- 35 file Python trên ổ D có trong gói bàn giao vẫn khớp checksum; các
  đoạn sửa thấy được nhắm vào runtime Colab, chưa lan vào mã nguồn này.
- Mã trong `/content` chưa được đọc trực tiếp. Các lỗi cú pháp trên là
  kết quả tái hiện phép sửa lưu trong notebook, không phải bản dump runtime.
- Chưa thấy bằng chứng các ô đó sửa dữ liệu train/dev hoặc checkpoint.
- SHA-256 notebook không đổi trong lúc audit; không có thao tác ghi vào
  notebook hiện hành, dữ liệu hay mã nguồn ứng dụng từ bước rà soát này.

Hướng xử lý: dùng lại mã sạch, sửa việc đọc key manifest Windows/Linux đúng
chỗ, hiển thị log subprocess và giữ lỗi verify/test là lỗi chặn. Không cần
thay schema dữ liệu hay viết lại toàn bộ hàm kiểm tra.
