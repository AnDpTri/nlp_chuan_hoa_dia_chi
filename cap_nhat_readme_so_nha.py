from pathlib import Path
p=Path(r'D:\nlp_chuan_hoa_dia_chi\data\tham_chieu_so_nha_toan_quoc\README.md')
t=p.read_text(encoding='utf-8')
t=t.replace(
'- so_nha_osm_20261024_toan_quoc.csv: 85.218 đối tượng OSM Việt Nam có thẻ addr:housenumber, 73.417 đối tượng còn có addr:street. Trong đó 56.664 đối tượng node có tọa độ gốc; 28.378 way chỉ có tọa độ đại diện ước lượng từ đỉnh, 176 relation không gán tọa độ.',
'- so_nha_osm_20261027_toan_quoc.csv: 85.346 đối tượng OSM Việt Nam có thẻ addr:housenumber; 73.537 đối tượng có addr:street. Trong đó 56.684 node có tọa độ gốc; 28.475 way dùng tọa độ đại diện ước lượng; 187 relation không có tọa độ.'
)
t=t.replace(
'- so_nha_gan_xa_moi_GIS_CHUA_XAC_MINH.csv: kết quả xác định **ứng viên mã xã mới** theo giao điểm địa lý; chỉ tồn tại nếu bước ghép thành công. Cột trang_thai_GIS cho biết điểm/ước lượng và độ chắc chắn vị trí. KHÔNG chứa mã xã cũ được xác thực.',
'- so_nha_gan_xa_moi_GIS_CHUA_XAC_MINH_20261027.csv: kết quả xác định **ứng viên mã xã mới** theo giao điểm địa lý; chỉ tồn tại nếu bước ghép thành công. Cột trang_thai_GIS cho biết điểm/ước lượng và độ chắc chắn vị trí. KHÔNG chứa mã xã cũ được xác thực.'
)
t=t.replace(
'- thong_ke_osm_20261024.json, nguon_ranh_gioi.json, bao_cao_gan_GIS.json: số liệu, nguồn, hash để kiểm chứng.',
'- thong_ke_osm_20261027.json, nguon_ranh_gioi.json, bao_cao_gan_GIS_20261027.json: số liệu, nguồn, hash để kiểm chứng.'
)
append="""

## Bổ sung nguồn số nhà tại các tỉnh còn thiếu (cập nhật 31/10/2026)

- bo_sung_dia_chi_so_nha_cac_tinh_thieu.csv: tệp tổng hợp **3.658 địa chỉ duy nhất thuộc đủ 34 tỉnh/thành**, ghép từ các nguồn bổ sung cấp tỉnh và nguồn Bộ Y tế. Đây là bộ tham chiếu nghiên cứu, không phải sổ địa chỉ dân cư.
- bo_sung_so_nha_co_so_y_te_moh_2021_2026_tinh_con_thieu.csv: 588 địa chỉ cơ sở y tế duy nhất trích từ dashboard bệnh án điện tử của Bộ Y tế trong các năm 2021–2026; bổ sung 25 tỉnh/thành trước đó chưa có nguồn bổ sung trong thư mục.
- Trong 588 địa chỉ Bộ Y tế: 456 dòng có căn cứ đối chiếu xã hiện hành hoặc crosswalk ghi nhập toàn bộ; 132 dòng cần rà soát thủ công. Không tự động chốt các dòng chưa xác minh.
- nguon_moh_emr_snapshot/: HTML snapshot của dashboard theo từng năm, kèm SHA256 trong bao_cao_bo_sung_moh_emr.json.
- bao_cao_bo_sung_cac_tinh.json: báo cáo tổng hợp theo tỉnh, trạng thái đối chiếu và SHA256.
- bo_sung_dia_chi_so_nha_9_tinh_truoc_moh.csv: bản sao tệp tổng hợp trước khi thêm nguồn Bộ Y tế.
- gop_moh_vao_bo_sung.py, bo_sung_moh_emr.py: script tái tạo phần trích xuất và ghép dữ liệu.

**Giới hạn và quyền sử dụng:** Nguồn Bộ Y tế là danh sách cơ sở y tế có triển khai bệnh án điện tử, không phải danh bạ mọi địa chỉ. Một số địa chỉ còn dùng địa danh cũ; chỉ gán xã mới khi khớp tên xã hiện hành hoặc crosswalk thể hiện nhập toàn bộ. Dữ liệu này không phải Train/Dev/Test, không phải nhãn Gold và không được dùng để tự động xác nhận địa chỉ pháp lý. Các cổng tỉnh và dashboard Bộ Y tế chưa xác nhận giấy phép tái phân phối hàng loạt; chỉ dùng nội bộ nghiên cứu cho đến khi xác minh quyền. OSM tuân thủ ODbL 1.0 và nghĩa vụ ghi công tương ứng.
"""
if '## Bổ sung nguồn số nhà tại các tỉnh còn thiếu' not in t:t+=append
p.write_text(t,encoding='utf-8')
print('UPDATED',p,'LINES',len(t.splitlines()))
