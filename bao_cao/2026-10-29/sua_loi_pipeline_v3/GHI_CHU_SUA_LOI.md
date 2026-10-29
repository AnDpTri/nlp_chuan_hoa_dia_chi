# Sửa lỗi pipeline v3 sau chẩn đoán

Ngày 29/10/2026. Source hiện tại mang phiên bản `baseline_luat_v3`, beam vẫn là 40. Chưa huấn luyện CRF/logistic regression. Không đổi train/dev, danh mục hay dữ liệu hai task agy; không dùng test cuối để sửa thuật toán.

## Những thay đổi

1. **Giữ dấu đã nhập khi chấm tên.** Trie vẫn tra khóa không dấu để sinh ứng viên. Với các tên cùng khóa, mỗi ký tự có dấu trong input nhưng khác danh mục bị giảm một điểm; ký tự không dấu không bị phạt vì có thể thiếu dấu. Giữ ứng viên khác dấu cho trường hợp người nhập gõ sai. Không so kiểu này giữa bí danh khác chữ như Sài Gòn/Hồ Chí Minh. Nhánh khác dấu được chọn có dấu vết `khac_dau` và cảnh báo `dau_ten_khac_danh_muc` (nếu nhánh đồng thời khác loại, vẫn dùng cảnh báo khác loại).
2. **Phạt phần tên bị cắt ngắn.** Nếu có tên đầy đủ khớp trực tiếp ở cùng vị trí/cấp/cách có tiền tố, nhánh ngắn giảm một điểm cho mỗi token tên chưa lấy. Giữ nhánh ngắn để quan hệ cha-con và ngữ cảnh vẫn có thể chọn nó. Không cộng lặp vì tên có ở cả hai mốc; ứng viên fuzzy/khác dấu/khác loại không dùng làm bằng chứng tên đầy đủ để phạt nhánh khác. Cách này giải quyết cạnh tranh Cát Tiên/Cát Tiên 2 và An Phú/An Phú Đông.
3. **Dấu nháy nằm trong tên riêng.** Tokenizer nối các phần tên có `'`, `’`, `ʼ` giữa chữ; dấu nháy bao ngoài vẫn là dấu câu. Khóa tên thống nhất cách viết dấu nháy, kể cả U+02BC được Unicode coi là chữ. Offset vẫn trỏ đúng chuỗi gốc và Unicode phân rã.
4. **Bảo toàn cụm số nhà.** Giữ `24B-24`, `154-156`, `46-48-50-52`, `1031F;1031G`, kể cả dấu gạch có khoảng trắng hoặc các dạng gạch dài. Dấu gạch chuẩn hóa thành `-`, không mở rộng thành danh sách số hay đoán ý nghĩa địa bàn. Cụm có `/`, gạch hoặc `;` mang `so_nha_can_duyet`. Không lấy số trong tên đường làm số nhà.
5. **Hạn chế suy đường.** Các cụm bắt đầu bằng lô, tập thể, khu đô thị, khu dân cư, căn hộ, dãy nhà được giữ ở phần chưa phân loại nếu chưa có tiền tố đường. So cụm chặn có xét dấu để không loại Lò Đúc hoặc Tăng Bạt Hổ. Mã như K18 không bị chặn chỉ vì có chữ số; cách hiểu đường suy ra vẫn có cảnh báo, chưa mở thành tên chính thức.

Các trọng số mới vẫn là luật đặt tay, không phải độ tin cậy đã được hiệu chuẩn. Không áp dụng quy tắc ưu tiên mốc mới: Lam Sơn cũ/mới và các địa chỉ thiếu bằng chứng vẫn giữ mơ hồ.

## Kết quả trên cùng 1.136 mẫu dev

| Chỉ số | v2 | v3 |
|---|---:|---:|
| Khớp đồng thời sáu trường | 839 — 73,856% | 870 — 76,585% |
| Số nhà | 95,423% | 96,567% |
| Đường | 81,690% | 82,218% |
| Mã xã | 93,222% | 95,423% |
| Mã tỉnh | 98,944% | 99,120% |
| Nhóm OSM | 57,000% | 60,250% |
| Nhóm tổng hợp | 83,016% | 85,462% |
| Có đích xã tham chiếu trong ứng viên | 903/916 | 912/916 |

Thêm **32 mẫu khớp đủ sáu trường**, mất khớp **1 mẫu**, tăng ròng 31. Từng trường: số nhà thêm 13, đường thêm 7/mất 1, mã xã thêm 25, mã tỉnh thêm 2; ngõ và thôn không đổi. Các số có thể chồng mẫu. Đây là mức khớp với nhãn máy/tổng hợp, không phải đánh giá vàng về độ chính xác thực tế.

Mẫu mất khớp là `VNDEV_00089`:

- Input: `9, Khu dân cư số 9, Xuân Khánh, Ninh Kiều, Cần Thơ`.
- v2/tham chiếu: `Số 9, Đường Khu Dân Cư Số 9, Phường Ninh Kiều, Thành phố Cần Thơ`.
- v3: `Số 9, Phường Ninh Kiều, Thành phố Cần Thơ`; `Khu dân cư số 9` ở phần chưa phân loại, có cảnh báo.

Giữ thay đổi này vì input chưa chỉ rõ tên đường và hệ thống chưa có nguồn tra để xác nhận cả cụm là đường. Chưa khẳng định tên đường đó không tồn tại; cần nguồn bổ sung nếu muốn nhận nó làm đường. Không sửa nhãn hoặc xóa mẫu để làm đẹp điểm.

## Ví dụ trước/sau đầy đủ

| Input | v2 | v3 |
|---|---|---|
| `Số 24B-24 Tôn Đản, Phường 13, quận 4, TP HCM` | Số 24B, Đường - 24 Tôn Đản, Phường Xóm Chiếu, Thành phố Hồ Chí Minh | Số 24B-24, Đường Tôn Đản, Phường Xóm Chiếu, Thành phố Hồ Chí Minh |
| `129, Quốc lộ 27, D'Ran, Đơn Dương, Lâm Đồng` | Số 129, Quốc lộ 27, Đường ' Ran, Tỉnh Lâm Đồng | Số 129, Quốc lộ 27, Xã D’Ran, Tỉnh Lâm Đồng |
| `Xã Tam Đàn, Huyện Phú Ninh, Tỉnh Quảng Nam` | Thành phố Đà Nẵng | Xã Chiên Đàn, Thành phố Đà Nẵng |
| `Số 204, Đường Phan Bội Châu, Xã Cát Tiên 2, Tỉnh Lâm Đồng` | Số 204, Đường Phan Bội Châu, Tỉnh Lâm Đồng | Số 204, Đường Phan Bội Châu, Xã Cát Tiên 2, Tỉnh Lâm Đồng |

Các chuỗi sau chuẩn hóa vẫn có thể kèm cảnh báo; đọc `du_doan.jsonl` để xem đầy đủ.

## Kiểm chứng và tái lập

- 30 kiểm tra pipeline cũ và 11 kiểm tra v3 đều đạt, có nhiều biến thể trong từng bài. Bốn kiểm tra cách chấm cũng đạt.
- Các kiểm tra mới viết tay theo cấu trúc lỗi, không thêm vào train/dev hay test cuối: hai tên cùng khóa nhưng khác dấu, thiếu dấu vẫn mơ hồ, tên cũ/mới vẫn mơ hồ, tên có đuôi số, ba loại dấu nháy và NFD, cụm số, phần ngoài địa chỉ và tên có dấu gần với cụm chặn.
- Đã đối chiếu toàn bộ 1.136 input/output trước/sau; rà 32 mẫu mới khớp và mẫu mất khớp; kiểm tra dấu vết ký tự/token không chồng nhau và truy về đúng chuỗi gốc.
- Kết quả cuối: `danh_gia/ket_qua/ban_thu_v3_cuoi/`. Lần trung gian `ban_thu_v3_01` được giữ để truy vết; không dùng làm số bàn giao.
- Bản source v2 trước sửa có snapshot tại thư mục `work/truoc_sua_v3` của chat; các báo cáo v2 cũ được giữ nguyên. Script chẩn đoán mặc định ghim v2 sẽ từ chối source hiện tại; muốn chẩn đoán v3, truyền `--baseline-dir danh_gia/ket_qua/ban_thu_v3_cuoi`.

```powershell
py -3.12 -X utf8 -B -m unittest discover -s tests -p 'test_pipeline*.py' -v
py -3.12 -X utf8 -B -m unittest discover -s tests -p test_danh_gia.py -v
py -3.12 -X utf8 -B -m danh_gia.chay_ban_thu --output-dir danh_gia/ket_qua/lan_do_moi
py -3.12 -X utf8 -B -m danh_gia.so_sanh_ban_thu --before danh_gia/ket_qua/ban_thu_v2_cuoi --after danh_gia/ket_qua/lan_do_moi
```

Mỗi lần đo cần thư mục mới. Trình so sánh hiện dùng tên phiên bản thật và xuất `SO_SANH.md`, các cột trước/sau; các báo cáo so sánh cũ giữ nguyên tên tệp cũ.

## Giới hạn và bước tiếp theo

Chưa giải quyết mọi tên riêng viết tắt, phục hồi dấu đường/thôn hoặc tên không tiền tố. Dữ liệu hai snapshot không đại diện mọi đơn vị ở mọi giai đoạn lịch sử. Dấu nhập có thể sai nên chỉ là ưu tiên mềm. Phạt tên ngắn có thể không phù hợp với địa chỉ thiếu dấu phân cách; cần tiếp tục đo trên bộ địa chỉ độc lập.

Hợp đồng dùng để rà nhãn được ghi ở [HOP_DONG_NHAN_CHUAN_HOA.md](HOP_DONG_NHAN_CHUAN_HOA.md). Chưa sửa nhãn cũ hay dùng dữ liệu bổ sung chưa được kiểm chứng để báo điểm. Tiếp theo là rà nhãn span và đo CRF so với luật, đồng thời chuẩn bị nguồn tra tên; chưa mặc định mô hình sẽ giải quyết mọi phần còn lại.
