# Đánh giá hướng đi pipeline sau chẩn đoán v2

Ngày 29/10/2026. Chẩn đoán trên 1.136 mẫu dev hiện có, giữ nguyên source v2, sáu danh mục và nhãn dev. Không đọc test cuối, không huấn luyện, không đổi cấu hình chạy chính. Kết quả chi tiết tại `danh_gia/ket_qua/chan_doan_v2_02/`.

## Kết luận kiến trúc

Giữ hướng sinh nhiều ứng viên từ hai mốc, kiểm tra nguồn và đích, xét toàn địa chỉ, xuất phần xác định được cùng cảnh báo. Chưa có bằng chứng cần thay trie hoặc tăng beam. Cần sửa các lỗi mất thông tin ở tầng token/so khớp/quyết định và chuẩn hóa hợp đồng nhãn trước khi đánh giá lợi ích của mô hình học máy.

CRF vẫn là thử nghiệm hợp lý cho tách vai trò chi tiết; logistic regression vẫn có thể học điểm xếp hạng. Hai lựa chọn này chưa được chứng minh bằng thực nghiệm. Không ép mô hình học một đích khi đầu vào có nhiều cách hiểu hợp lệ hoặc học lại lỗi của nhãn máy.

## Chẩn đoán có thể kết luận từ số đo

- Khớp đồng thời bốn trường chi tiết và hai mã: 839/1.136 (73,856%). Đây là mức khớp nhãn, không phải độ chính xác thực tế đã xác minh.
- Trong 916 mẫu có nhãn xã: 903 có đích trong ứng viên; cả 903 đều có nhánh trong beam 40 chốt duy nhất đúng cặp mã xã/tỉnh tham chiếu. Không thấy mất đích xã ở bước cắt beam trên tập này.
- Có 890 mẫu mà ít nhất một nhánh trong beam gốc khớp đủ sáu trường. Chênh 51 mẫu với output cuối gồm 30 mẫu nhánh khớp xếp sau và 21 mẫu nhánh đầu khớp nhưng bước giữ mơ hồ làm output lệch nhãn. Không mặc định cả 51 là lỗi cần sửa theo nhãn.
- Trên các mẫu lệch không có nhánh khớp đủ sáu trường, chạy đối chứng beam 160 không tìm thêm nhánh khớp. Đây là chẩn đoán giữ nguyên bộ sinh và parser, không phải chứng minh mọi địa chỉ đều chỉ cần beam 40.

Phân hoạch 297 ca lệch sáu trường:

| Cơ chế quan sát | Số mẫu | Ý nghĩa và giới hạn |
|---|---:|---|
| Có nhánh khớp mã hành chính nhưng chi tiết chưa khớp nhãn | 228 | Bao gồm lỗi parser, khôi phục dấu, quy ước và nhãn sai/thiếu |
| Có nhánh khớp sáu trường nhưng xếp sau | 30 | Có 12 ca nhãn xã trống nhưng output điền; cần rà trước khi học xếp hạng |
| Nhánh đầu khớp nhưng quyết định giữ mơ hồ làm lệch nhãn | 21 | Có cả mơ hồ thực sự lẫn mơ hồ do thuật toán tạo ra |
| Chưa tách được hành chính, chi tiết và vấn đề nhãn | 18 | Giữ riêng, không gán cưỡng bức một nguyên nhân |

Riêng đường có 208 ca lệch, trong đó 97 ca chỉ khác dấu ở trường đường. 97 không đồng nghĩa toàn bộ sáu trường của những mẫu này chỉ sai dấu. Khôi phục tên chính thức cần nguồn tra; CRF tách vai trò không tự cung cấp bằng chứng về tên chuẩn.

## Lỗi thuật toán có bằng chứng cụ thể

1. **Mất dấu đã nhập ở khâu chấm tên.** `Xã Tam Đàn, Huyện Phú Ninh, Tỉnh Quảng Nam` sinh cả Tam Đàn và Tam Dân, hai nhánh cùng 31,23 điểm. Nhánh đúng đứng đầu nhưng output bỏ xã do cạnh tranh với tên khác dấu. Bỏ dấu nên phục vụ tìm kiếm, không xóa bằng chứng khi đánh giá khớp.
2. **Tên bị cắt ngắn vẫn cạnh tranh như một cách hiểu đủ.** `Xã Cát Tiên 2` được 21,29 điểm; cách chỉ lấy `Xã Cát Tiên` để sót số 2 được 20,70. Chênh 0,59 nằm trong ngưỡng 0,65 nên bị gộp mơ hồ. Cần đánh giá phần còn sót và ranh giới tên.
3. **Dấu nháy trong tên riêng làm ngắt quét.** Có 9/13 ca không sinh được đích tham chiếu liên quan D'Ran và tám biến thể M'Drắk; bốn ca còn lại có số đứng riêng không có tiền tố xã. Không được coi 13 mẫu là 13 nguyên nhân độc lập. D'Ran còn bị nhận D thành tiền tố đường và sinh `Đường ' Ran`.
4. **Cắt mất cụm số nhà.** `154-156` còn `154`; `Số 24B-24` bị tách và đẩy phần còn lại vào đường. Đây là mất thông tin quan sát được trực tiếp.
5. **Suy đường quá rộng.** Sau `Số 1`, cụm `Lô 2 tập thể Viện Kỹ thuật quân sự` bị gán đường. Cần cho phép phần ngoài bốn trường ở lại O hoặc có thiết kế trường phụ phù hợp.

Các ví dụ kèm input/output/tham chiếu và nhánh thực thi ở `RA_SOAT_NGU_NGHIA.md` và `ra_soat_ngu_nghia.json`.

## Mơ hồ thật và hợp đồng nhãn

- `Xã Lam Sơn, Tỉnh Thanh Hóa` có thể chỉ xã cũ dẫn đến Minh Sơn hoặc xã mới Lam Sơn. Cả hai khớp tên và tỉnh trong danh mục. Chưa có dữ liệu đường để phân biệt; nhãn một đích từ bộ sinh tổng hợp không chứng minh chuỗi đủ thông tin.
- `Hai Bà Trưng, Hà Nội` có thể là quận cũ hoặc phường mới. Không tự mặc định mốc mới vì bài toán cho phép trộn mốc và thiếu tiền tố.
- Nhãn của `185 Đường 3/2, phường 11, Quận 10, ...` lại dùng Phường 11 thuộc Quận 3 trong danh mục. Có thể tái hiện nhãn bằng cách bỏ bằng chứng Quận 10; đó không phải lý do đủ để chọn nhánh ấy.
- Một số nhãn lấy số trong tên đường làm số nhà, ví dụ input `73, Đường số 27` nhưng nhãn `Số 27`; một số gán cùng ngõ/thôn vào cả trường chi tiết và đường.
- Cần chốt quy ước cho `Xa lộ` so với `Đường Xa lộ`, ngõ có tên, cụm số nhà, và cách đánh giá xã cũ nhiều đích/nhập nhằng cũ mới. Nên có tập đích chấp nhận hoặc nhãn chưa đủ căn cứ thay vì ép một mã ẩn từ bộ sinh.

Rà 33 ca có ghi nhận cụ thể: toàn bộ 20 ca lệch không có cảnh báo và 13 ca đại diện khác. Chỉ kiểm tra theo chuỗi và danh mục cục bộ; chưa xác minh độc lập thực địa, chưa rà vàng toàn bộ 297 ca. Có 80/1.136 mẫu mang ít nhất một cờ tự động cần rà nhãn; các cờ có thể trùng, không tự kết luận cả 80 nhãn sai. Không loại các mẫu này để công bố điểm cao hơn.

## Cảnh báo chưa phải độ tin cậy

| Nhóm | Mẫu không cảnh báo | Lệch sáu trường trong nhóm | Tỷ lệ lệch nhãn |
|---|---:|---:|---:|
| Tổng hợp | 550 | 0 | 0% |
| OSM | 105 | 20 | 19,048% |
| Chung | 655 | 20 | 3,053% |

Tỷ lệ gộp che khuất khác biệt nguồn. 20 ca OSM đã được rà và thấy vấn đề nhãn/quy ước ở nhiều ca, nên 19,048% cũng không được gọi là tỷ lệ sai ngữ nghĩa đã xác minh. Chưa có căn cứ biến `không cảnh báo` thành cam kết tự động chuẩn hóa đúng.

## Độ phủ tình huống khó

Không có mẫu nào trong dev khớp regex token riêng `TTT|BVT|DV|CG|NTT` (không phân biệt hoa thường). Kết luận này chỉ nói về những token đã kiểm tra, không phải không có bất kỳ viết tắt nào. Nhãn biến thể `loi_chinh_ta` có trong dev nhưng output không hề chọn nhánh `khop_gan_dung`; do đó mức khớp cao của nhóm biến thể ấy chưa chứng minh khả năng sửa tên riêng sai chính tả. Tên viết tắt mạnh, lỗi tên riêng và tổ hợp nhiều lỗi vẫn cần một bộ kiểm tra độc lập, có căn cứ, chia theo địa chỉ gốc; chưa dùng bộ bổ sung agy đang sửa để thay số đo ở đây.

## Thứ tự công việc sau đánh giá

1. Chốt hợp đồng nhãn và các kết quả được phép khi mơ hồ; rà nhãn span trước khi đưa vào CRF. Rà độc lập các nhóm nghi nhãn, không sửa nhãn để chạy theo output.
2. Trong lượt sửa lõi tiếp theo, xử lý các nguyên nhân có bằng chứng: giữ dấu đã nhập, ranh giới tên/số, dấu nháy nội tên, cụm số nhà và giới hạn suy đường. Mỗi nguyên nhân cần kiểm tra hồi quy theo cấu trúc, không vá theo ID dev.
3. Sau khi nhãn span đáng tin, thử CRF cho tách chi tiết và so với v2 trên cùng phép đo. Phục hồi tên đường/viết tắt cần nguồn tra riêng, giữ rõ phần chưa xác minh.
4. Chỉ học xếp hạng khi đã có các nhóm giả thuyết đúng/sai đáng tin, tách tương đương cùng đích và các ca không thể phân biệt bằng input. So với điểm tay; chưa ưu tiên logistic regression chỉ vì đã có tên trong sơ đồ.
5. Khi có dữ liệu tình huống khó đã được kiểm tra độc lập, đo lại khả năng giữ đáp án, độ chính xác trong phần quyết định và độ phủ theo nguồn/biến thể. Chỉ thay beam hoặc cấu trúc tìm kiếm khi xuất hiện bằng chứng mất đáp án.

## Kiểm chứng và tái lập

Script `danh_gia/chan_doan_pipeline.py` xác nhận source/danh mục/dev trùng lần đo v2 trước khi chạy, gọi lại API trên toàn bộ 1.136 mẫu và so sánh toàn bộ kết quả với dự đoán đã lưu. Nhánh chẩn đoán được kiểm tra trùng nhánh API về danh sách ứng viên đã chọn, điểm và chi tiết. Hash được kiểm tra lại sau chạy. Sáu kiểm tra chẩn đoán xác nhận cách tách có đích/chốt duy nhất, giới hạn tìm chứng cứ, mẫu trống và rào chắn test.

```powershell
py -3.12 -X utf8 -B -m unittest discover -s tests -p test_chan_doan_pipeline.py -v
py -3.12 -X utf8 -B -m danh_gia.chan_doan_pipeline --output-dir danh_gia/ket_qua/chan_doan_lan_moi
```

Thư mục mới phải chưa tồn tại. Ghi chú rà cụ thể lưu ở `danh_gia/ra_soat_chan_doan_v2.json`. Không có thay đổi source thuật toán, dữ liệu hay mô hình trong lượt đánh giá này.
