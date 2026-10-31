from pathlib import Path
p=Path(r'D:\nlp_chuan_hoa_dia_chi\data\tham_chieu_so_nha_toan_quoc\README.md')
t=p.read_text(encoding='utf-8')
t=t.replace('Chi tiết SHA256: nguon_ranh_gioi.json, thong_ke_osm_20261024.json.','Chi tiết SHA256: nguon_ranh_gioi.json, thong_ke_osm_20261027.json, bao_cao_gan_GIS_20261027.json.')
t=t.replace('**3.658 địa chỉ duy nhất thuộc đủ 34 tỉnh/thành**','**4.398 địa chỉ duy nhất thuộc đủ 34 tỉnh/thành**')
t=t.replace('## Bổ sung nguồn số nhà tại các tỉnh còn thiếu (cập nhật 31/10/2026)','## Bổ sung nguồn số nhà tại các tỉnh còn thiếu (cập nhật 31/10/2026)')
t=t.replace('- bo_sung_dia_chi_so_nha_9_tinh_truoc_moh.csv: bản sao tệp tổng hợp trước khi thêm nguồn Bộ Y tế.\\n- gop_moh_vao_bo_sung.py, bo_sung_moh_emr.py: script tái tạo phần trích xuất và ghép dữ liệu.',
'''- bo_sung_dak_lak_so_y_te_20250513_so_nha.csv: 654 địa chỉ từ danh sách Sở Y tế Đắk Lắk; 203 dòng có căn cứ đối chiếu xã, 451 dòng cần rà soát.
- bo_sung_tay_ninh_so_y_te_20260409_so_nha.csv: 86 địa chỉ từ Cổng dữ liệu mở Tây Ninh; 83 dòng khớp xã hiện hành, 3 dòng cần rà soát.
- Hai nguồn trên bổ sung ròng 740 địa chỉ vào tệp tổng hợp, nâng tổng số từ 3.658 lên 4.398; vẫn phủ đủ 34 tỉnh/thành.
- bo_sung_dia_chi_so_nha_9_tinh_truoc_moh.csv: bản sao tệp tổng hợp trước khi thêm nguồn Bộ Y tế.
- bo_sung_dia_chi_so_nha_34_tinh_truoc_nguon_y_te_them.csv: bản sao tệp tổng hợp trước khi thêm hai nguồn Đắk Lắk và Tây Ninh.
- bao_cao_bo_sung_dak_lak.json, bao_cao_bo_sung_tay_ninh_y_te.json: thống kê trích xuất và hash nguồn.
- gop_moh_vao_bo_sung.py, bo_sung_moh_emr.py, bo_sung_daklak.py, bo_sung_tayninh.py, gop_nguon_y_te_them_vao_tong_hop.py: script tái tạo các phần bổ sung.''')
t=t.replace('Trong 588 địa chỉ Bộ Y tế: 456 dòng có căn cứ đối chiếu xã hiện hành hoặc crosswalk ghi nhập toàn bộ; 132 dòng cần rà soát thủ công. Không tự động chốt các dòng chưa xác minh.',
'''Trong 588 địa chỉ Bộ Y tế: 456 dòng có căn cứ đối chiếu xã hiện hành hoặc crosswalk ghi nhập toàn bộ; 132 dòng cần rà soát thủ công. Không tự động chốt các dòng chưa xác minh.''')
p.write_text(t,encoding='utf-8')
print('UPDATED',p,'LINES',len(t.splitlines()))
