from pathlib import Path
p=Path(r'D:\nlp_chuan_hoa_dia_chi\README.md')
t=p.read_text(encoding='utf-8')
section="""

## Dữ liệu đối chiếu địa chỉ cũ → mới

Bộ cặp địa chỉ chi tiết có bằng chứng nguồn được lưu riêng tại data/doi_chieu_dia_chi_cu_moi/README.md. Tệp chính là cap_nha_duong_dia_chi_cu_moi.csv, hiện có 19 cặp, trong đó 18 cặp có số nhà/chi tiết đường. Đây là dữ liệu tham chiếu được trích từ các văn bản công khai; chưa phải Gold và không được trộn với bộ 4.398 địa chỉ độc lập ở data/tham_chieu_so_nha_toan_quoc.
"""
if '## Dữ liệu đối chiếu địa chỉ cũ → mới' not in t:t+=section
p.write_text(t,encoding='utf-8')
print('UPDATED',p,'LINES',len(t.splitlines()))
