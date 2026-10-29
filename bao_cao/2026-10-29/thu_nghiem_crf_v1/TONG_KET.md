# Thống kê CRF v1: từ dữ liệu đến địa chỉ đầu cuối

Đã train và tích hợp thử hai CRF CPU. **Mặc định vẫn là luật v3.** CRF chọn vai trò chi tiết, trie/bảng hành chính cung cấp ứng viên và quan hệ; điểm ghép toàn tuyến vẫn đặt tay. CRF không chỉ sửa output của luật: chế độ mở giữ ứng viên trước bộ lọc đường/hành chính để mô hình cùng tham gia quyết định.

**Mọi tỷ lệ khớp dưới đây so với nhãn máy/tổng hợp, chưa phải độ chính xác thực tế trên gold.** Không đọc test cuối; không thay nhãn hoặc sinh mẫu train mới. Tất cả cấu hình cố định được báo, không chọn siêu tham số để tối đa điểm dev.

## 1. Dữ liệu

| Tập | Mẫu dùng | Token | Cách dùng |
|---|---:|---:|---|
| train_goc | 3973 | 67866 | Huấn luyện đối chứng |
| train_ket_hop | 5966 | 102019 | Huấn luyện sau thêm khó |
| dev_goc | 1026 | 17395 | Đo BIO/span trên phần căn chỉnh được |
| dev_kho | 452 | 7715 | Đo BIO/span trên phần tương thích tokenizer |

End-to-end đo toàn bộ **1.136 dev gốc** và **464 dev khó**, kể cả mẫu không dùng được cho phép đo span. Hai tập dev có quan hệ nguồn, không cộng thành tập test độc lập.

- Train gốc đầu vào 4.564: 365 loại khi căn chỉnh/kiểm tra cơ học, 196 loại vì trùng họ dev sau che số nhà, 30 trùng input/BIO; còn 3.973.
- Bổ sung dùng snapshot 2.037/464 đã được nhánh audit chụp lại trước lượt agy sửa tiếp; 44 train và 12 dev có nhãn cắt giữa token runtime nên không dùng cho CRF/span. Ví dụ 151Đ. được tokenizer hiện tại giữ 151Đ thành một token, nhãn chỉ lấy 151.
- Kết hợp 3.973 + 1.993 = 5.966 mẫu. Không lấy mẫu dev vào fit. Sau lọc không còn họ input trùng theo phép che số nhà đang dùng; điều đó chưa chứng minh độc lập mọi template/nguồn.
- Snapshot bổ sung không có nhãn ngõ/hẻm. Train kết hợp vẫn chỉ có 379 span ngõ/hẻm từ train gốc. Dev khó có 0 span ngõ/hẻm, chỉ 12 span thôn/tổ: không suy chất lượng nhóm này từ tỷ lệ trường trống.
- excluded.jsonl ghi 787 sự kiện loại vì dùng hai nhánh train đối chứng; có 757 bộ ID/split/lý do duy nhất. Số trùng input/BIO ghi 60 sự kiện nhưng là 30 mẫu lặp lại ở hai nhánh, không phải 60 mẫu riêng.

## 2. Thời gian train và kích thước

| Model | Feature (s) | Fit CPU (s) | Kích thước (KiB) | RAM sau train (MiB) |
|---|---:|---:|---:|---:|
| train_goc | 8.83 | 9.77 | 248.63 | 85.055 |
| train_ket_hop | 16.11 | 13.91 | 281.86 | 117.105 |

Python 3.12, python-crfsuite 0.9.12, L-BFGS c1=0.1/c2=0.1, tối đa 100 vòng, CPU; máy có 12 luồng logic khả dụng, không khẳng định trainer dùng cả 12. RAM là cả tiến trình train. API sử dụng: [tài liệu python-crfsuite](https://python-crfsuite.readthedocs.io/en/latest/pycrfsuite.html).

## 3. CRF đơn lẻ, trước ghép hành chính

| Model | Dev | Token accuracy (%) | Non-O token F1 (%) | Span F1 (%) | Khớp cả chuỗi BIO (%) |
|---|---|---:|---:|---:|---:|
| train_goc | dev_goc | 99.442 | 98.868 | 98.78 | 97.173 |
| train_goc | dev_kho | 98.354 | 97.147 | 96.605 | 92.699 |
| train_ket_hop | dev_goc | 99.368 | 98.691 | 98.547 | 96.686 |
| train_ket_hop | dev_kho | 99.572 | 99.284 | 99.282 | 98.894 |

F1 span yêu cầu đúng vai trò và hai ranh giới, không chỉ đúng token. Train gốc đạt F1 span train 100%; train kết hợp 99,991%. Chênh với dev và các ví dụ lỗi cho thấy không thể dùng điểm train làm độ chính xác thực tế.

## 4. Span sau lựa chọn hành chính, trên dev gốc 1.026 mẫu căn chỉnh được

| Trường | Span tham chiếu | Luật F1 (%) | CRF gốc F1 (%) | CRF thêm khó F1 (%) |
|---|---:|---:|---:|---:|
| so_nha | 883 | 98.861 | 98.926 | 98.867 |
| ngo_ngach_hem | 96 | 96.97 | 100.0 | 100.0 |
| thon_xom | 18 | 100.0 | 90.909 | 85.714 |
| duong | 924 | 97.363 | 98.651 | 98.596 |

18 span thôn/tổ là quá ít để coi F1 là kết luận chắc chắn. Phần 110 dev gốc không căn chỉnh được không có mặt ở bảng này nhưng vẫn được đo end-to-end.

## 5. Chuỗi từng trường trên toàn bộ 1.136 dev gốc

| Trường | Luật khớp (%) | CRF gốc (%) | CRF thêm khó (%) |
|---|---:|---:|---:|
| so_nha | 96.567 | 97.183 | 97.183 |
| ngo_ngach_hem | 99.384 | 99.208 | 98.768 |
| thon_xom | 99.472 | 99.56 | 99.472 |
| duong | 82.218 | 85.387 | 85.563 |
| ma_xa | 95.423 | 95.335 | 95.423 |
| ma_tinh | 99.12 | 99.296 | 99.296 |
| dia_chi_chuan | 76.144 | 78.609 | 78.345 |

Các tỷ lệ trường có tính nhãn trống. Precision/recall trên phần khác rỗng nằm trong thong_ke.json. Tách span đúng chưa bảo đảm khôi phục dấu hoặc loại đường đúng.

## 6. Địa chỉ end-to-end

| Cấu hình | Dev | Khớp 4 chi tiết (%) | 4 chi tiết bỏ khác dấu (%) | Khớp 6 trường | Khớp 6 (%) | Chuỗi địa chỉ (%) |
|---|---|---:|---:|---:|---:|---:|
| Luật v3 | dev_goc | 80.37 | 88.908 | 870/1136 | 76.585 | 76.144 |
| Luật v3 | dev_kho | 51.293 | 65.948 | 228/464 | 49.138 | 49.138 |
| CRF gốc | dev_goc | 82.658 | 91.197 | 898/1136 | 79.049 | 78.609 |
| CRF gốc | dev_kho | 58.836 | 74.138 | 262/464 | 56.466 | 56.466 |
| CRF thêm khó | dev_goc | 82.306 | 90.845 | 895/1136 | 78.785 | 78.345 |
| CRF thêm khó | dev_kho | 61.638 | 77.371 | 274/464 | 59.052 | 59.052 |

Sáu trường = số nhà, ngõ/hẻm, thôn/tổ, đường, mã xã, mã tỉnh. Chuỗi địa chỉ còn chịu ảnh hưởng tên hành chính/định dạng. Dev khó có 434 mẫu được gắn usable canonical; khớp sáu trường riêng nhóm đó: luật 52,535%, CRF gốc 60,369%, CRF thêm khó 63,134%. Cờ usable vẫn không phải chứng nhận gold.

Trên 400 OSM trong dev gốc: luật 60,25%; CRF gốc 67,25%; CRF thêm khó 66,50%. Trên 736 mẫu tổng hợp, cả ba là 85,462%. Dữ liệu bổ sung giúp dev khó nhưng làm dev gốc giảm nhẹ so với CRF chỉ học gốc; chưa thể kết luận cứ thêm dữ liệu là tốt hơn.

Đối chứng CRF kết hợp giữ bộ lọc ứng viên cứng v3 cho cùng tỷ lệ khớp sáu trường (78,785%/59,052%), nhưng mã xã/tỉnh có đổi ở một vài mẫu. Chế độ mở đạt 95,423% mã xã, 99,296% mã tỉnh trên dev gốc; chế độ bảo vệ là 95,511%/99,208%. Chưa có bằng chứng cấu hình mở giải quyết xong mọi tranh chấp vai trò.

## 7. Theo nhóm khó: khớp sáu trường

| Biến thể | Mẫu | Luật (%) | CRF gốc (%) | CRF thêm khó (%) |
|---|---:|---:|---:|---:|
| mat_dau_viet_tat | 44 | 9.091 | 11.364 | 11.364 |
| dinh_ranh_gioi_khong_phay | 44 | 77.273 | 95.455 | 100.0 |
| dao_thu_tu | 44 | 81.818 | 100.0 | 100.0 |
| thieu_cap | 44 | 79.545 | 100.0 | 100.0 |
| loi_go_telex_phim | 44 | 2.273 | 6.818 | 2.273 |
| so_nha_nhieu_xuyet | 44 | 97.727 | 97.727 | 97.727 |
| tron_moc_cu_moi_kho | 43 | 79.07 | 97.674 | 97.674 |
| to_hop_kho | 43 | 6.977 | 6.977 | 6.977 |
| ngu_canh_to_to | 12 | 91.667 | 100.0 | 100.0 |
| ngu_canh_tinh_tinh | 12 | 91.667 | 100.0 | 100.0 |
| ngu_canh_cum_thanh_pho | 12 | 66.667 | 0.0 | 100.0 |
| duong_trung_hanh_chinh | 12 | 66.667 | 100.0 | 100.0 |
| dinh_chu_p7_q10 | 12 | 0.0 | 0.0 | 0.0 |
| xa_bi_chia_mo_ho | 12 | 0.0 | 0.0 | 0.0 |
| viet_tat_ten_rieng | 24 | 0.0 | 0.0 | 0.0 |
| viet_tat_ten_rieng_mo_ho | 18 | 0.0 | 0.0 | 0.0 |

Nhóm viết tắt tên riêng còn 0% khớp sáu trường; CRF chỉ nhận vai trò, chưa có nguồn mở tên riêng. Nhóm lỗi gõ có thể được nhận đúng span nhưng giữ nguyên tên lỗi nên vẫn lệch chuỗi chuẩn. Các ca xã chia/mơ hồ còn vấn đề nhãn/tập đích; 0% không chứng minh mọi trường đều sai.

## 8. Đảo thứ tự và ví dụ khó ngoài bảng dev

Một fixture gồm sáu thành phần có tiền tố rõ và dấu phẩy, hoán vị 720 cách: luật, CRF gốc và CRF thêm khó đều 720/720. Đây là một fixture chức năng, không phải 720 địa chỉ thực độc lập.

Input: `Hà Nội, Quận Ba Đình, Phường Trúc Bạch, Lê Lợi, 12, Ngõ 5`

- luat_v3: `Số 12, Ngõ 5, Phường Ba Đình, Thành phố Hà Nội`; chưa phân loại: `Lê Lợi`.
- crf_train_goc: `Ngõ 5, Phường Ba Đình, Thành phố Hà Nội`; chưa phân loại: `Lê Lợi 12`.
- crf_ket_hop: `Ngõ 5, Phường Ba Đình, Thành phố Hà Nội`; chưa phân loại: `Lê Lợi 12`.

Input: `Hà Nội Quận Ba Đình Phường Trúc Bạch Lê Lợi 12 Ngõ 5`

- luat_v3: `Ngõ 5, Phường Ba Đình, Thành phố Hà Nội`; chưa phân loại: `Lê Lợi 12`.
- crf_train_goc: `Đường Lê Lợi 12 Ngõ 5, Phường Ba Đình, Thành phố Hà Nội`; chưa phân loại: ``.
- crf_ket_hop: `Ngõ 5, Phường Ba Đình, Thành phố Hà Nội`; chưa phân loại: `Lê Lợi 12`.

Input: `12 ng5 TTT, P.DV, Q.CG, HN`

- luat_v3: `Số 12, Ngõ 5, Thành phố Hà Nội`; chưa phân loại: `TTT P DV Q CG`.
- crf_train_goc: `Số 12, Ngõ 5, Thành phố Hà Nội`; chưa phân loại: `TTT P DV Q CG`.
- crf_ket_hop: `Số 12ng5TTT, Thành phố Hà Nội`; chưa phân loại: `P DV Q CG`.

Các ca này cho thấy chưa giải quyết được đảo thứ tự thiếu tiền tố/dấu phân cách hay viết tắt mạnh, dù nhóm đảo thứ tự tổng hợp đạt cao. Không tự dùng chúng để điều chỉnh model trong lần thử này.

## 9. Ca tăng điểm và ca thoái lui cần đọc

### CRF gốc

**VNDEV_00051 — mat_khop**

- Input: Thôn Dương Lâm 1, Xã Hoà Phong,Hoà Vang,TP Đà Nẵng
- Luật: Thôn Dương Lâm 1, Xã Hòa Vang, Thành phố Đà Nẵng
- CRF: Đường Thôn Dương Lâm 1, Xã Hòa Vang, Thành phố Đà Nẵng
- Tham chiếu: Thôn Dương Lâm 1, Xã Hòa Vang, Thành phố Đà Nẵng

**VNDEV_00057 — mat_khop**

- Input: Quốc lộ 14B, Thôn Phú Sơn 1, Xã Hòa Tiến, TP Đà Nẵng
- Luật: Thôn Phú Sơn 1, Quốc lộ 14B, Xã Hòa Tiến, Thành phố Đà Nẵng
- CRF: Quốc lộ 14B, Đường Thôn Phú Sơn 1, Xã Hòa Tiến, Thành phố Đà Nẵng
- Tham chiếu: Thôn Phú Sơn 1, Quốc lộ 14B, Xã Hòa Tiến, Thành phố Đà Nẵng

**VNDEV_00058 — mat_khop**

- Input: Lô 98-99 đường Hoàng Thị Loan, P. Hoà Minh, Q. Liên Chiểu, TP. Đà Nẵng
- Luật: Đường Hoàng Thị Loan, Phường Hòa Khánh, Thành phố Đà Nẵng
- CRF: Số Lô98-99, Đường Hoàng Thị Loan, Phường Hòa Khánh, Thành phố Đà Nẵng
- Tham chiếu: Đường Hoàng Thị Loan, Phường Hòa Khánh, Thành phố Đà Nẵng

**VNDEV_00374 — mat_khop**

- Input: 09, Châu Thượng Văn, minh an, Hoi An, quang nam
- Luật: Số 09, Đường Châu Thượng Văn, Phường Hội An, Thành phố Đà Nẵng
- CRF: Số 09, Phường Hội An, Thành phố Đà Nẵng
- Tham chiếu: Số 09, Đường Châu Thượng Văn, Phường Hội An, Thành phố Đà Nẵng

**VNDEV_00387 — mat_khop**

- Input: Quốc lộ 80, Vàm Cống, Ấp Bình Lợi, Xã Lấp Vò, Đồng Tháp
- Luật: Ấp Bình Lợi, Quốc lộ 80, Xã Lấp Vò, Tỉnh Đồng Tháp
- CRF: Quốc lộ 80, Đường Vàm Cống, Xã Lấp Vò, Tỉnh Đồng Tháp
- Tham chiếu: Ấp Bình Lợi, Quốc lộ 80, Xã Lấp Vò, Tỉnh Đồng Tháp

**VNDEV_00001 — moi_khop**

- Input: 843M+RH3 Hòa Thành District, Tây Ninh
- Luật: Tỉnh Tây Ninh
- CRF: Số 843M, Tỉnh Tây Ninh
- Tham chiếu: Số 843M, Tỉnh Tây Ninh

**VNDEV_00003 — moi_khop**

- Input: 45 XÔ VIẾT NGHỆ TĨNH P.AN CƯ- NINH KIỀU- CẦN THƠ
- Luật: Số 45, Đường Xô Viết Nghệ Tĩnh, Thành phố Cần Thơ
- CRF: Số 45, Thành phố Cần Thơ
- Tham chiếu: Số 45, Thành phố Cần Thơ

**VNDEV_00034 — moi_khop**

- Input: Số 194 phố Minh Khai, tổ 14, phường Minh Khai, quận Hai Bà Trưng, Hà Nội
- Luật: Số 194, Tổ 14, Phố Minh Khai, Thành phố Hà Nội
- CRF: Số 194, Phố Minh Khai, Thành phố Hà Nội
- Tham chiếu: Số 194, Phố Minh Khai, Thành phố Hà Nội

**VNDEV_00066 — moi_khop**

- Input: Nguyễn Hữu Trí, Tân Túc, Bình Chánh, Thị trấn Tân Túc, Hồ Chí Minh
- Luật: Xã Tân Nhựt, Thành phố Hồ Chí Minh
- CRF: Đường Nguyễn Hữu Trí, Xã Tân Nhựt, Thành phố Hồ Chí Minh
- Tham chiếu: Đường Nguyễn Hữu Trí, Xã Tân Nhựt, Thành phố Hồ Chí Minh

**VNDEV_00068 — moi_khop**

- Input: Trần Hưng Đạo, Thành phố Châu Đốc, An Giang
- Luật: Tỉnh An Giang
- CRF: Đường Trần Hưng Đạo, Tỉnh An Giang
- Tham chiếu: Đường Trần Hưng Đạo, Tỉnh An Giang

### CRF thêm khó

**VNDEV_00024 — mat_khop**

- Input: Số 1 Lô 2 tập thể Viện Kỹ thuật quân sự, Phường Nghĩa Đô, Quận Cầu Giấy, Hà Nội
- Luật: Số 1, Thành phố Hà Nội
- CRF: Số 1, Đường Thể Viện Kỹ Thuật Quân Sự, Thành phố Hà Nội
- Tham chiếu: Số 1, Thành phố Hà Nội

**VNDEV_00036 — mat_khop**

- Input: Số 24B-24 Tôn Đản, Phường 13, quận 4, TP HCM
- Luật: Số 24B-24, Đường Tôn Đản, Phường Xóm Chiếu, Thành phố Hồ Chí Minh
- CRF: Số 24B, Đường Tôn Đản, Phường Xóm Chiếu, Thành phố Hồ Chí Minh
- Tham chiếu: Số 24B-24, Đường Tôn Đản, Phường Xóm Chiếu, Thành phố Hồ Chí Minh

**VNDEV_00051 — mat_khop**

- Input: Thôn Dương Lâm 1, Xã Hoà Phong,Hoà Vang,TP Đà Nẵng
- Luật: Thôn Dương Lâm 1, Xã Hòa Vang, Thành phố Đà Nẵng
- CRF: Thôn Dương, Đường Lâm 1, Xã Hòa Vang, Thành phố Đà Nẵng
- Tham chiếu: Thôn Dương Lâm 1, Xã Hòa Vang, Thành phố Đà Nẵng

**VNDEV_00057 — mat_khop**

- Input: Quốc lộ 14B, Thôn Phú Sơn 1, Xã Hòa Tiến, TP Đà Nẵng
- Luật: Thôn Phú Sơn 1, Quốc lộ 14B, Xã Hòa Tiến, Thành phố Đà Nẵng
- CRF: Thôn Phú, Quốc lộ 14B, Xã Hòa Tiến, Thành phố Đà Nẵng
- Tham chiếu: Thôn Phú Sơn 1, Quốc lộ 14B, Xã Hòa Tiến, Thành phố Đà Nẵng

**VNDEV_00058 — mat_khop**

- Input: Lô 98-99 đường Hoàng Thị Loan, P. Hoà Minh, Q. Liên Chiểu, TP. Đà Nẵng
- Luật: Đường Hoàng Thị Loan, Phường Hòa Khánh, Thành phố Đà Nẵng
- CRF: Số Lô98-99, Đường Hoàng Thị Loan, Phường Hòa Khánh, Thành phố Đà Nẵng
- Tham chiếu: Đường Hoàng Thị Loan, Phường Hòa Khánh, Thành phố Đà Nẵng

**VNDEV_00130 — mat_khop**

- Input: 2, Nội khu Mỹ Toàn 2, Phường Tân Hưng, Thành phố Hồ Chí Minh
- Luật: Số 2, Đường Nội Khu Mỹ Toàn 2, Phường Tân Hưng, Thành phố Hồ Chí Minh
- CRF: Số 2, Phường Tân Hưng, Thành phố Hồ Chí Minh
- Tham chiếu: Số 2, Đường Nội Khu Mỹ Toàn 2, Phường Tân Hưng, Thành phố Hồ Chí Minh

**VNDEV_00236 — mat_khop**

- Input: 13, Đô Đốc Lộc, Tân Quý, Tân Phú, Hồ Chí Minh
- Luật: Số 13, Đường Đô Đốc Lộc, Thành phố Hồ Chí Minh
- CRF: Số 13, Thành phố Hồ Chí Minh
- Tham chiếu: Số 13, Đường Đô Đốc Lộc, Thành phố Hồ Chí Minh

**VNDEV_00387 — mat_khop**

- Input: Quốc lộ 80, Vàm Cống, Ấp Bình Lợi, Xã Lấp Vò, Đồng Tháp
- Luật: Ấp Bình Lợi, Quốc lộ 80, Xã Lấp Vò, Tỉnh Đồng Tháp
- CRF: Quốc lộ 80, Đường Vàm Cống , Ấp Bình Lợi, Xã Lấp Vò, Tỉnh Đồng Tháp
- Tham chiếu: Ấp Bình Lợi, Quốc lộ 80, Xã Lấp Vò, Tỉnh Đồng Tháp

**VNDEV_00001 — moi_khop**

- Input: 843M+RH3 Hòa Thành District, Tây Ninh
- Luật: Tỉnh Tây Ninh
- CRF: Số 843M, Tỉnh Tây Ninh
- Tham chiếu: Số 843M, Tỉnh Tây Ninh

**VNDEV_00003 — moi_khop**

- Input: 45 XÔ VIẾT NGHỆ TĨNH P.AN CƯ- NINH KIỀU- CẦN THƠ
- Luật: Số 45, Đường Xô Viết Nghệ Tĩnh, Thành phố Cần Thơ
- CRF: Số 45, Thành phố Cần Thơ
- Tham chiếu: Số 45, Thành phố Cần Thơ

**VNDEV_00066 — moi_khop**

- Input: Nguyễn Hữu Trí, Tân Túc, Bình Chánh, Thị trấn Tân Túc, Hồ Chí Minh
- Luật: Xã Tân Nhựt, Thành phố Hồ Chí Minh
- CRF: Đường Nguyễn Hữu Trí, Xã Tân Nhựt, Thành phố Hồ Chí Minh
- Tham chiếu: Đường Nguyễn Hữu Trí, Xã Tân Nhựt, Thành phố Hồ Chí Minh

**VNDEV_00068 — moi_khop**

- Input: Trần Hưng Đạo, Thành phố Châu Đốc, An Giang
- Luật: Tỉnh An Giang
- CRF: Đường Trần Hưng Đạo, Tỉnh An Giang
- Tham chiếu: Đường Trần Hưng Đạo, Tỉnh An Giang

Điểm tăng có phần không phải cải thiện ngữ nghĩa: `843M+RH3` bị model lấy `843M` làm số nhà để khớp nhãn; có ca bỏ tên đường đang hiện diện hoặc bỏ Tổ 14 vì nhãn máy bỏ sót. Ngược lại, thôn bị nhận thành đường, lô bị nhận thành số nhà và một số tên đường bị bỏ là các thoái lui cần xử lý. Không tự sửa nhãn theo model hoặc thay model mặc định chỉ vì điểm tăng.

## 10. Hiệu năng và kiểm chứng

| Mode | Dev | Mean ms | p95 ms | Địa chỉ/s |
|---|---|---:|---:|---:|
| Luật v3 | dev_goc | 6.39 | 13.58 | 156.5 |
| Luật v3 | dev_kho | 8.27 | 34.59 | 120.9 |
| CRF gốc | dev_goc | 12.86 | 23.85 | 77.8 |
| CRF gốc | dev_kho | 15.72 | 41.23 | 63.6 |
| CRF thêm khó | dev_goc | 14.00 | 27.10 | 71.4 |
| CRF thêm khó | dev_kho | 15.88 | 45.83 | 63.0 |

Một lượt tuần tự trên máy đang làm việc, không phải so sánh tải máy chủ có kiểm soát. Đo chỉ pipeline, không tính ghi file/chẩn đoán. CRF được chạy một lần mỗi input, dùng lại nhãn/marginal cho các nhánh.

53 kiểm tra đạt: 41 pipeline, 4 cách chấm, 8 hợp đồng CRF có train/lưu/nạp/chạy API thật. Baseline sau thêm adapter giữ nguyên kết quả v3 trên 1.136 mẫu; snapshot đầu vào được kiểm hash. Mỗi output giữ offset đúng chuỗi gốc và span không chồng.

## Chạy lại

Tạo môi trường khi chưa có:

```powershell
py -3.12 -m venv .venv-crf
.\.venv-crf\Scripts\python.exe -m pip install -r requirements-crf.txt
```

Dùng model đã train hoặc đo lại vào thư mục mới:

```powershell
.\.venv-crf\Scripts\python.exe -X utf8 -B -m src "Số 12, Đường Lê Lợi, Phường Trúc Bạch, Quận Ba Đình, Hà Nội" --crf-model mo_hinh/thu_nghiem/crf_v1_01/train_goc.crfsuite
.\.venv-crf\Scripts\python.exe -X utf8 -B -m danh_gia.do_crf --experiment mo_hinh/thu_nghiem/crf_v1_01 --output-dir danh_gia/ket_qua/lan_do_crf_moi
```

Thư mục đo mới phải chưa tồn tại. Cài thư viện qua requirements-crf.txt trong .venv-crf nếu cần. Muốn train lại, sao chép du_lieu_dong_bang và snapshot_manifest.json sang thư mục thí nghiệm mới rồi chạy danh_gia.huan_luyen_crf --experiment <thư mục mới>; không ghi đè model đã lưu.

## Quyết định tiếp theo

Giữ hai model để so sánh và thu thập lỗi; mặc định v3 chưa thay. Ưu tiên rà nhãn sai/thiếu, bổ sung nhãn vai trò ngoài mẫu quen thuộc và các nhóm ít hỗ trợ, thống nhất tokenizer cho số dính tiền tố. Sau đó train lại cùng phép đo. Chuẩn hóa tên viết tắt/lỗi gõ cần bộ sinh ứng viên và nguồn tra; xếp hạng toàn giả thuyết còn dùng điểm tay. Chưa có kết quả test vàng để nghiệm thu.
