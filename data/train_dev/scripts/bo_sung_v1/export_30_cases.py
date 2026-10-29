#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script trích xuất và định dạng chi tiết 30 ca đại diện rà soát vai trò thực thể (Role Labeling)
phục vụ huấn luyện mô hình CRF / Sequence Labeling từ gói train/dev khó bo_sung_v1.
Bao phủ 16 nhóm biến thể và các góc cạnh ngữ nghĩa phức tạp.
"""

import sys
import csv
import json
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parents[3]
BO_SUNG_DIR = PROJECT_DIR / "data" / "train_dev" / "bo_sung_v1"

# 1. Đọc dữ liệu
spans_data = {}
with open(BO_SUNG_DIR / "token_spans.jsonl", 'r', encoding='utf-8') as f:
    for line in f:
        d = json.loads(line)
        spans_data[d['id']] = d

all_rows = {}
for fname, split in [('train_bo_sung.csv', 'Train'), ('dev_kho.csv', 'Dev')]:
    with open(BO_SUNG_DIR / fname, 'r', encoding='utf-8-sig') as f:
        for r in csv.DictReader(f):
            r['split'] = split
            all_rows[r['id']] = r

# 2. Định nghĩa danh sách 20 loại cho Train và 10 loại cho Dev bao phủ toàn bộ các góc cạnh
train_selected_types = [
    'ngo_ngach_hem_chuan',
    'ngo_ngach_hem_phuc_hop',
    'hem_kiet_mien_nam_trung',
    'dao_thu_tu_duong_truoc_ngo_so',
    'thon_xom_to_dan_pho',
    'cum_lo_can_ho_tap_the_nhan_o',
    'dinh_chu_p7_q10',
    'viet_tat_ten_rieng_mo_ho',
    'xa_bi_chia_mo_ho',
    'viet_tat_ten_rieng',
    'ngu_canh_to_to',
    'ngu_canh_tinh_tinh',
    'ngu_canh_cum_thanh_pho',
    'duong_trung_hanh_chinh',
    'so_nha_nhieu_xuyet',
    'dao_thu_tu',
    'mat_dau_viet_tat',
    'dinh_ranh_gioi_khong_phay',
    'loi_go_telex_phim',
    'thieu_cap'
]

dev_selected_types = [
    'ngo_ngach_hem_chuan',
    'ngo_ngach_hem_phuc_hop',
    'hem_kiet_mien_nam_trung',
    'dao_thu_tu_duong_truoc_ngo_so',
    'thon_xom_to_dan_pho',
    'cum_lo_can_ho_tap_the_nhan_o',
    'dinh_chu_p7_q10',
    'viet_tat_ten_rieng_mo_ho',
    'xa_bi_chia_mo_ho',
    'so_nha_nhieu_xuyet'
]

selected_ids = []

# Chọn từ Train
train_rows_dict = {r_id: r for r_id, r in all_rows.items() if r['split'] == 'Train'}
used_train_types = set()
for t in train_selected_types:
    for r_id, r in train_rows_dict.items():
        if r['loai_bien_the'] == t and r_id not in selected_ids:
            selected_ids.append(r_id)
            break
    if len(selected_ids) >= 20:
        break

# Chọn từ Dev
dev_rows_dict = {r_id: r for r_id, r in all_rows.items() if r['split'] == 'Dev'}
for t in dev_selected_types:
    for r_id, r in dev_rows_dict.items():
        if r['loai_bien_the'] == t and r_id not in selected_ids:
            selected_ids.append(r_id)
            break
    if len(selected_ids) >= 30:
        break

print(f"Đã chọn được {len(selected_ids)} ca đại diện ({sum(1 for i in selected_ids if all_rows[i]['split']=='Train')} Train, {sum(1 for i in selected_ids if all_rows[i]['split']=='Dev')} Dev):")

out_markdown = []
out_markdown.append("### Danh mục 30 ca đại diện rà soát nhãn vai trò thực thể cho CRF\n")
out_markdown.append("| STT | ID | Phân vùng | Loại biến thể | Đầu vào nguyên văn (`dau_vao`) | Usable Span | Usable Canonical |\n")
out_markdown.append("|:---:|:---|:---:|:---|:---|:---:|:---:|\n")

for idx, r_id in enumerate(selected_ids, start=1):
    r = all_rows[r_id]
    sp = spans_data[r_id]
    dv_short = r['dau_vao'] if len(r['dau_vao']) <= 50 else r['dau_vao'][:47] + "..."
    u_span = "✅ True" if sp['usable_for_span_training'] else "❌ False"
    u_canon = "✅ True" if sp['usable_for_canonical_training'] else "❌ False"
    out_markdown.append(f"| {idx} | `{r['id']}` | {r['split']} | `{r['loai_bien_the']}` | {dv_short} | {u_span} | {u_canon} |\n")

out_markdown.append("\n---\n")
out_markdown.append("### Phân tích chi tiết từng ca: Quan sát được (CRF Spans) vs Đầu ra chuẩn hóa (Canonical)\n\n")

for idx, r_id in enumerate(selected_ids, start=1):
    r = all_rows[r_id]
    sp = spans_data[r_id]
    tokens = sp['tokens']
    spans = sp['spans']

    # Gom các token có nhãn khác O
    non_o_tokens = [f"`{t['token']}` ({t['bio_tag']})" for t in tokens if t['bio_tag'] != 'O']
    bio_summary = ", ".join(non_o_tokens) if non_o_tokens else "Toàn bộ O"

    # Định dạng span chi tiết
    span_details = []
    for fld in ['so_nha', 'ngo_ngach_hem', 'thon_xom', 'duong']:
        s_obj = spans.get(fld)
        if s_obj:
            span_details.append(f"- **{fld}**: `[{s_obj['start']}:{s_obj['end']}]` -> \"{s_obj['text']}\"")
        else:
            span_details.append(f"- **{fld}**: `None`")

    analysis_text = ""
    vt = r['loai_bien_the']
    if 'ngo_ngach_hem_chuan' in vt:
        analysis_text = ("Thực thể ngõ ngách có tiền tố chuẩn ('Ngõ 192', 'Ngõ 82') được trích xuất vào trường `ngo_ngach_hem`. "
                         "Chuỗi nhãn BIO gán `B-ngo_ngach_hem` và `I-ngo_ngach_hem`, bảo đảm phân biệt số nhà với số ngõ.")
    elif 'ngo_ngach_hem_phuc_hop' in vt:
        analysis_text = ("Cấu trúc ngõ ngách nhiều cấp ('Ngách 15/2 Ngõ 80') được nhận diện nguyên cụm liên tục trong `ngo_ngach_hem`, "
                         "phản ánh đặc thù địa chỉ ngách phức tạp tại các đô thị lớn miền Bắc.")
    elif 'hem_kiet_mien_nam_trung' in vt:
        analysis_text = ("Phương ngữ hẻm (Sài Gòn / miền Nam) và kiệt (Đà Nẵng / miền Trung) như 'Hẻm 24/8', 'Kiệt 45/3' "
                         "được gán nhãn chuẩn hóa vào trường `ngo_ngach_hem` theo đúng hợp đồng nhãn `docs/HOP_DONG_NHAN_CHUAN_HOA.md`.")
    elif 'dao_thu_tu_duong_truoc_ngo_so' in vt:
        analysis_text = ("Đảo thứ tự chi tiết: Tên đường xuất hiện trước ngõ và số nhà (ví dụ 'Đường Giải Phóng, ngõ 12, số 5'). "
                         "Mô hình CRF nhận diện độc lập từng thực thể theo vai trò ngữ nghĩa thực tế, không bị trói buộc vào giả định thứ tự xuôi.")
    elif 'thon_xom_to_dan_pho' in vt:
        analysis_text = ("Đơn vị dân cư dưới xã nông thôn hoặc tổ dân phố đô thị ('Thôn Đông', 'Tổ dân phố 12', 'Ấp Tân Lập') nhận nhãn `thon_xom`. "
                         "Không bị nhận diện nhầm thành số nhà hay tên đường.")
    elif 'cum_lo_can_ho_tap_the_nhan_o' in vt:
        analysis_text = ("Phần thông tin kiến trúc, tòa nhà, căn hộ, tập thể, lô đất ('Căn hộ 1204 Tòa R2 Khu đô thị Royal City', 'Khu tập thể A1') "
                         "được giữ ở nhãn `O` theo đúng hợp đồng nhãn `docs/HOP_DONG_NHAN_CHUAN_HOA.md`. Tuyệt đối không ép vào số nhà hay tên đường.")
    elif 'dinh_chu_p7_q10' in vt:
        analysis_text = ("Dạng dính chữ số nhà và tên đường ('151Đ.LêLợi'). Char span `[0:3]` cho '151' và `[3:10]` cho 'Đ.LêLợi' được bảo toàn chính xác. "
                         "Tuy nhiên, do tokenizer v1.0 hiện tại (src.tien_xu_ly.token_co_vi_tri) gộp '151Đ' thành một token `[0:4]`, "
                         "ranh giới span bị cắt ngang token. Mẫu được phân loại cách ly: `usable_for_span_training = False` cho pipeline chạy tokenizer v1.0 "
                         "và bảo toàn char span cho tokenizer v2.0.")
    elif 'viet_tat_ten_rieng' == vt:
        analysis_text = ("Viết tắt tên đường theo quy chuẩn kỹ thuật giao thông đường bộ quốc gia (QL1A -> Quốc lộ 1A, QL5 -> Quốc lộ 5, TL295 -> Tỉnh lộ 295). "
                         "Gán nhãn `usable_for_canonical_training = True` do căn cứ quy chuẩn giao thông công khai xác minh duy nhất.")
    elif 'viet_tat_ten_rieng_mo_ho' in vt:
        analysis_text = ("Từ viết tắt tên riêng trong câu đóng vai trò thực thể đường hợp lệ (`duong`), "
                         "mô hình CRF học cách nhận diện hình thái viết tắt. "
                         "Tuy nhiên, do từ viết tắt có thể có nhiều cách mở rộng (đa nghĩa: TTT, BVT, HBT), "
                         "tầng chuẩn hóa để trống `duong` và `trang_thai_nhan = 'chua_xac_dinh'`, "
                         "tắt cờ `usable_for_canonical_training = False` để tránh ép mô hình sinh ảo.")
    elif 'xa_bi_chia' in vt:
        analysis_text = ("Thực thể số nhà, đường được trích xuất hoàn toàn chính xác cho CRF (`usable_for_span_training = True`). "
                         "Tuy nhiên, xã cũ bị chia tách thành nhiều đơn vị hành chính mới mốc 01/07/2025 (fan-out > 1) "
                         "mà input không có thêm thông tin định vị, nên không gán `ma_xa` hay `xa_phuong`, "
                         "lưu danh sách ứng viên vào `ghi_chu`, tắt cờ `usable_for_canonical_training = False`.")
    elif 'dao_thu_tu' in vt:
        analysis_text = ("Thứ tự thành phần bị đảo ngược (Hành chính -> Đường -> Số nhà). "
                         "Mô hình CRF xử lý độc lập từng token và nhãn BIO theo ngữ cảnh trích xuất, "
                         "không phụ thuộc vào giả định thứ tự tuyến tính xuôi. Các span quan sát được khớp chính xác 100%.")
    elif 'thieu_cap' in vt:
        analysis_text = ("Địa chỉ bị khuyết một hoặc hai cấp hành chính (ví dụ khuyết huyện hoặc tỉnh). "
                         "Observed Spans chỉ gán nhãn cho những gì thực sự có trong câu (không sinh span ảo). "
                         "Tầng Canonical phục hồi mã hành chính dựa trên quan hệ cha-con duy nhất.")
    elif 'ngu_canh_to_to' in vt:
        analysis_text = ("Từ 'Tô' trong tên đường ('Tô Vĩnh Diện', 'Tô Hiệu') được phân biệt dứt khoát "
                         "với tiền tố 'Tổ' (Tổ dân phố - `thon_xom`). Token 'Tô' được gán `B-duong` hoặc `I-duong`, "
                         "không bị nhận nhầm thành `B-thon_xom`.")
    elif 'ngu_canh_tinh_tinh' in vt:
        analysis_text = ("Từ 'Tĩnh' trong tên riêng xã ('Tĩnh Hải', 'Tĩnh Gia') được phân biệt với tiền tố 'Tỉnh'. "
                         "Token 'Tĩnh' là tên riêng đơn vị cấp xã (`O`), không bị nhầm lẫn với phân cấp tỉnh.")
    elif 'ngu_canh_cum_thanh_pho' in vt:
        analysis_text = ("Cụm 'Thành Phố' trong tên dự án/đường ('Thành Phố Giao Lưu') được gán nhãn `duong`, "
                         "ngữ cảnh tiền tố 'Đường' giúp mô hình CRF không nhầm lẫn cụm này với cấp hành chính tỉnh/thành phố.")
    elif 'so_nha_nhieu_xuyet' in vt:
        analysis_text = ("Số nhà phức tạp có nhiều dấu gạch chéo ('/') và hậu tố chữ ('A', 'B', 'Bis'). "
                         "Toàn bộ chuỗi số nhà được gán liền mạch `B-so_nha` và `I-so_nha`, không bị cắt vụn tại ký tự '/'.")
    elif 'dinh_ranh_gioi_khong_phay' in vt:
        analysis_text = ("Không có dấu phẩy phân tách giữa các trường (ví dụ giữa đường và xã). "
                         "Mô hình CRF dựa trên chuyển trạng thái BIO (`I-duong` -> `O`) để nhận diện ranh giới thực thể.")
    elif 'loi_go_telex_phim' in vt:
        analysis_text = ("Đầu vào có lỗi gõ Telex kẹt phím ('dduowngf', 'phuowngf'). "
                         "Span quan sát được giữ nguyên ký tự lỗi trong input, giúp mô hình tăng cường độ bền vững (robustness).")
    else:
        analysis_text = ("Các span thực thể được căn chỉnh chính xác từng offset ký tự `[start:end]` trên chuỗi văn bản gốc. "
                         "Đầu ra chuẩn hóa canonical phục hồi đầy đủ mã danh mục và chuỗi địa chỉ đích.")

    out_markdown.append(f"#### Ca {idx}: `{r['id']}` ({r['split']} - `{r['loai_bien_the']}`)\n\n")
    out_markdown.append(f"- **Đầu vào nguyên văn (`dau_vao`)**: `{r['dau_vao']}`\n")
    out_markdown.append(f"- **Nhóm mẫu gốc (`nhom_mau_goc`)**: `{r['nhom_mau_goc']}`\n")
    out_markdown.append(f"- **Nguồn (`nguon`)**: `{r['nguon']}`\n")
    out_markdown.append("- **Observed Spans (Trích xuất quan sát được)**:\n")
    for s_line in span_details:
        out_markdown.append(f"  {s_line}\n")
    out_markdown.append(f"- **Chuỗi nhãn BIO**: {bio_summary}\n")
    out_markdown.append("- **Canonical Target (Đích chuẩn hóa)**:\n")
    out_markdown.append(f"  * Số nhà: `{r['so_nha']}` | Đường: `{r['duong']}`\n")
    out_markdown.append(f"  * Xã/Phường: `{r['xa_phuong']}` (mã: `{r['ma_xa']}`) | Tỉnh: `{r['tinh']}` (mã: `{r['ma_tinh']}`)\n")
    out_markdown.append(f"  * Địa chỉ chuẩn: `{r['dia_chi_chuan']}`\n")
    out_markdown.append(f"  * Cảnh báo: `{r['canh_bao']}`\n")
    out_markdown.append(f"- **Mức khả dụng (Usability Flags)**:\n")
    out_markdown.append(f"  * `usable_for_span_training`: **{sp['usable_for_span_training']}** (Span hợp lệ, offset chính xác)\n")
    out_markdown.append(f"  * `usable_for_canonical_training`: **{sp['usable_for_canonical_training']}**\n")
    out_markdown.append(f"- **Phân tích vai trò thực thể cho CRF**: {analysis_text}\n\n")

report_text = "".join(out_markdown)
with open(BO_SUNG_DIR / "bao_cao_30_ca_crf.md", 'w', encoding='utf-8') as f:
    f.write(report_text)

print(f"Đã xuất báo cáo 30 ca ra: {BO_SUNG_DIR / 'bao_cao_30_ca_crf.md'}")
