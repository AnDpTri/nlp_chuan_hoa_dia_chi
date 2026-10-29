# Ma trận cùng pipeline và CPU

Khớp nhãn máy/tổng hợp trên dev đã dùng phát triển, không phải gold.

Cùng CPU laptop. Mỗi extractor đo một lần/câu; mỗi nhánh đo phần pipeline riêng. Tổng = extract + pipeline, không gồm deepcopy cache, JSON, I/O, khởi tạo hoặc oracle hậu kiểm. Đây là tổng thành phần, không phải các lượt full độc lập.

| Tập | Cấu hình | Đúng | % | Mean/P95 ms | Beam có đủ 6 trường |
|---|---|---:|---:|---:|---:|
| dev_goc | luat_tay_cu | 870 | 76.585 | 7.86/13.49 | 909 |
| dev_goc | luat_tay_sua | 918 | 80.810 | 8.00/14.14 | 957 |
| dev_goc | crf_tay_cu | 895 | 78.785 | 14.61/26.41 | 930 |
| dev_goc | crf_tay_sua | 943 | 83.011 | 14.03/25.36 | 978 |
| dev_goc | cnn_tay_cu | 886 | 77.993 | 20.68/33.68 | 928 |
| dev_goc | cnn_ranker_cu | 893 | 78.609 | 21.49/34.30 | 928 |
| dev_goc | cnn_tay_sua | 934 | 82.218 | 19.74/32.50 | 976 |
| dev_goc | cnn_ranker_sua | 941 | 82.835 | 20.84/34.26 | 976 |
| dev_goc | videberta_tay_cu | 878 | 77.289 | 105.51/143.55 | 915 |
| dev_goc | videberta_ranker_cu | 879 | 77.377 | 106.30/145.97 | 915 |
| dev_goc | videberta_tay_sua | 926 | 81.514 | 104.91/141.85 | 963 |
| dev_goc | videberta_ranker_sua | 927 | 81.602 | 105.76/143.90 | 963 |
| dev_kho | luat_tay_cu | 228 | 49.138 | 12.32/46.38 | 238 |
| dev_kho | luat_tay_sua | 241 | 51.940 | 12.68/44.14 | 251 |
| dev_kho | crf_tay_cu | 274 | 59.052 | 14.56/38.43 | 286 |
| dev_kho | crf_tay_sua | 289 | 62.284 | 14.08/38.12 | 302 |
| dev_kho | cnn_tay_cu | 281 | 60.560 | 21.91/51.00 | 293 |
| dev_kho | cnn_ranker_cu | 280 | 60.345 | 23.00/51.06 | 293 |
| dev_kho | cnn_tay_sua | 296 | 63.793 | 21.20/49.09 | 309 |
| dev_kho | cnn_ranker_sua | 296 | 63.793 | 22.38/52.09 | 309 |
| dev_kho | videberta_tay_cu | 284 | 61.207 | 106.88/143.02 | 296 |
| dev_kho | videberta_ranker_cu | 282 | 60.776 | 107.67/144.56 | 296 |
| dev_kho | videberta_tay_sua | 299 | 64.440 | 105.88/146.34 | 312 |
| dev_kho | videberta_ranker_sua | 297 | 64.009 | 106.73/143.62 | 312 |

Không train/tune thêm, không đọc test cuối. Ranker đúng checkpoint. Từ điển train và bộ bảo vệ đường giống nhau ở các nhánh sửa. Luật không có span model nên bộ bảo vệ span không tác động.
Oracle beam là hậu kiểm với nhãn, chưa áp dụng cơ chế từ chối mơ hồ của output cuối. Không dùng oracle để chọn output.
