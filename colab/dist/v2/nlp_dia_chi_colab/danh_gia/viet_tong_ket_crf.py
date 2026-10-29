"""Xuất bản tổng kết đọc được từ các số đo đã lưu, không chạy lại model."""

import argparse
import csv
import json
from pathlib import Path


def run(folder, path):
    r = json.loads((folder/'thong_ke.json').read_text(encoding='utf-8'))
    functional = json.loads((folder/'kiem_tra_chuc_nang.json').read_text(encoding='utf-8'))
    modes = [('luat_v3', 'Luật v3'), ('crf_train_goc_mo', 'CRF gốc'), ('crf_ket_hop_mo', 'CRF thêm khó')]
    lines = ['# Thống kê CRF v1: từ dữ liệu đến địa chỉ đầu cuối', '',
             'Đã train và tích hợp thử hai CRF CPU. **Mặc định vẫn là luật v3.** CRF chọn vai trò chi tiết, trie/bảng hành chính cung cấp ứng viên và quan hệ; điểm ghép toàn tuyến vẫn đặt tay. CRF không chỉ sửa output của luật: chế độ mở giữ ứng viên trước bộ lọc đường/hành chính để mô hình cùng tham gia quyết định.', '',
             '**Mọi tỷ lệ khớp dưới đây so với nhãn máy/tổng hợp, chưa phải độ chính xác thực tế trên gold.** Không đọc test cuối; không thay nhãn hoặc sinh mẫu train mới. Tất cả cấu hình cố định được báo, không chọn siêu tham số để tối đa điểm dev.', '',
             '## 1. Dữ liệu', '', '| Tập | Mẫu dùng | Token | Cách dùng |', '|---|---:|---:|---|']
    data = r['data_quality']['datasets']
    for key, use in [('train_goc','Huấn luyện đối chứng'),('train_ket_hop','Huấn luyện sau thêm khó'),('dev_goc','Đo BIO/span trên phần căn chỉnh được'),('dev_kho','Đo BIO/span trên phần tương thích tokenizer')]:
        d = data[key]
        lines.append(f"| {key} | {d['used_rows']} | {d['tokens']} | {use} |")
    lines += ['', 'End-to-end đo toàn bộ **1.136 dev gốc** và **464 dev khó**, kể cả mẫu không dùng được cho phép đo span. Hai tập dev có quan hệ nguồn, không cộng thành tập test độc lập.', '',
              '- Train gốc đầu vào 4.564: 365 loại khi căn chỉnh/kiểm tra cơ học, 196 loại vì trùng họ dev sau che số nhà, 30 trùng input/BIO; còn 3.973.',
              '- Bổ sung dùng snapshot 2.037/464 đã được nhánh audit chụp lại trước lượt agy sửa tiếp; 44 train và 12 dev có nhãn cắt giữa token runtime nên không dùng cho CRF/span. Ví dụ 151Đ. được tokenizer hiện tại giữ 151Đ thành một token, nhãn chỉ lấy 151.',
              '- Kết hợp 3.973 + 1.993 = 5.966 mẫu. Không lấy mẫu dev vào fit. Sau lọc không còn họ input trùng theo phép che số nhà đang dùng; điều đó chưa chứng minh độc lập mọi template/nguồn.',
              '- Snapshot bổ sung không có nhãn ngõ/hẻm. Train kết hợp vẫn chỉ có 379 span ngõ/hẻm từ train gốc. Dev khó có 0 span ngõ/hẻm, chỉ 12 span thôn/tổ: không suy chất lượng nhóm này từ tỷ lệ trường trống.',
              '- excluded.jsonl ghi 787 sự kiện loại vì dùng hai nhánh train đối chứng; có 757 bộ ID/split/lý do duy nhất. Số trùng input/BIO ghi 60 sự kiện nhưng là 30 mẫu lặp lại ở hai nhánh, không phải 60 mẫu riêng.', '',
              '## 2. Thời gian train và kích thước', '', '| Model | Feature (s) | Fit CPU (s) | Kích thước (KiB) | RAM sau train (MiB) |', '|---|---:|---:|---:|---:|']
    for name in ('train_goc','train_ket_hop'):
        d = r['training'][name]
        lines.append(f"| {name} | {d['feature_preparation_s']:.2f} | {d['fit_s']:.2f} | {d['model_bytes']/1024:.2f} | {d['memory_after_training']['working_set_mib']} |")
    lines += ['', 'Python 3.12, python-crfsuite 0.9.12, L-BFGS c1=0.1/c2=0.1, tối đa 100 vòng, CPU; máy có 12 luồng logic khả dụng, không khẳng định trainer dùng cả 12. RAM là cả tiến trình train. API sử dụng: [tài liệu python-crfsuite](https://python-crfsuite.readthedocs.io/en/latest/pycrfsuite.html).', '',
              '## 3. CRF đơn lẻ, trước ghép hành chính', '', '| Model | Dev | Token accuracy (%) | Non-O token F1 (%) | Span F1 (%) | Khớp cả chuỗi BIO (%) |', '|---|---|---:|---:|---:|---:|']
    for name in ('train_goc','train_ket_hop'):
        for split in ('dev_goc','dev_kho'):
            d = r['standalone'][name][split]
            lines.append(f"| {name} | {split} | {d['token_accuracy_pct']} | {d['token_non_o']['f1_pct']} | {d['span_micro']['f1_pct']} | {d['sequence_exact_pct']} |")
    lines += ['', 'F1 span yêu cầu đúng vai trò và hai ranh giới, không chỉ đúng token. Train gốc đạt F1 span train 100%; train kết hợp 99,991%. Chênh với dev và các ví dụ lỗi cho thấy không thể dùng điểm train làm độ chính xác thực tế.', '',
              '## 4. Span sau lựa chọn hành chính, trên dev gốc 1.026 mẫu căn chỉnh được', '', '| Trường | Span tham chiếu | Luật F1 (%) | CRF gốc F1 (%) | CRF thêm khó F1 (%) |', '|---|---:|---:|---:|---:|']
    for field in ('so_nha','ngo_ngach_hem','thon_xom','duong'):
        values = [r['end_to_end'][mode]['dev_goc']['actual_pipeline_spans_on_aligned_subset']['span_per_field'][field] for mode,_ in modes]
        lines.append(f"| {field} | {values[0]['reference_spans']} | {values[0]['f1_pct']} | {values[1]['f1_pct']} | {values[2]['f1_pct']} |")
    lines += ['', '18 span thôn/tổ là quá ít để coi F1 là kết luận chắc chắn. Phần 110 dev gốc không căn chỉnh được không có mặt ở bảng này nhưng vẫn được đo end-to-end.', '',
              '## 5. Chuỗi từng trường trên toàn bộ 1.136 dev gốc', '', '| Trường | Luật khớp (%) | CRF gốc (%) | CRF thêm khó (%) |', '|---|---:|---:|---:|']
    for field in ('so_nha','ngo_ngach_hem','thon_xom','duong','ma_xa','ma_tinh','dia_chi_chuan'):
        values = [r['end_to_end'][mode]['dev_goc']['tung_truong'][field]['ty_le_khop_pct'] for mode,_ in modes]
        lines.append(f'| {field} | {values[0]} | {values[1]} | {values[2]} |')
    lines += ['', 'Các tỷ lệ trường có tính nhãn trống. Precision/recall trên phần khác rỗng nằm trong thong_ke.json. Tách span đúng chưa bảo đảm khôi phục dấu hoặc loại đường đúng.', '',
              '## 6. Địa chỉ end-to-end', '', '| Cấu hình | Dev | Khớp 4 chi tiết (%) | 4 chi tiết bỏ khác dấu (%) | Khớp 6 trường | Khớp 6 (%) | Chuỗi địa chỉ (%) |', '|---|---|---:|---:|---:|---:|---:|']
    for mode,label in modes:
        for split in ('dev_goc','dev_kho'):
            d=r['end_to_end'][mode][split]
            lines.append(f"| {label} | {split} | {d['detail_4_exact_pct']} | {d['detail_4_ignore_accents_pct']} | {d['dung_toan_bo_6_truong']}/{d['so_mau']} | {d['khop_toan_bo_6_truong_pct']} | {d['tung_truong']['dia_chi_chuan']['ty_le_khop_pct']} |")
    lines += ['', 'Sáu trường = số nhà, ngõ/hẻm, thôn/tổ, đường, mã xã, mã tỉnh. Chuỗi địa chỉ còn chịu ảnh hưởng tên hành chính/định dạng. Dev khó có 434 mẫu được gắn usable canonical; khớp sáu trường riêng nhóm đó: luật 52,535%, CRF gốc 60,369%, CRF thêm khó 63,134%. Cờ usable vẫn không phải chứng nhận gold.', '',
              'Trên 400 OSM trong dev gốc: luật 60,25%; CRF gốc 67,25%; CRF thêm khó 66,50%. Trên 736 mẫu tổng hợp, cả ba là 85,462%. Dữ liệu bổ sung giúp dev khó nhưng làm dev gốc giảm nhẹ so với CRF chỉ học gốc; chưa thể kết luận cứ thêm dữ liệu là tốt hơn.', '',
              'Đối chứng CRF kết hợp giữ bộ lọc ứng viên cứng v3 cho cùng tỷ lệ khớp sáu trường (78,785%/59,052%), nhưng mã xã/tỉnh có đổi ở một vài mẫu. Chế độ mở đạt 95,423% mã xã, 99,296% mã tỉnh trên dev gốc; chế độ bảo vệ là 95,511%/99,208%. Chưa có bằng chứng cấu hình mở giải quyết xong mọi tranh chấp vai trò.', '',
              '## 7. Theo nhóm khó: khớp sáu trường', '', '| Biến thể | Mẫu | Luật (%) | CRF gốc (%) | CRF thêm khó (%) |', '|---|---:|---:|---:|---:|']
    variants=[k for k in r['end_to_end']['luat_v3']['dev_kho']['groups'] if k.startswith('variant:')]
    for key in variants:
        ds=[r['end_to_end'][mode]['dev_kho']['groups'][key] for mode,_ in modes]
        lines.append(f"| {key[8:]} | {ds[0]['so_mau']} | {ds[0]['khop_toan_bo_6_truong_pct']} | {ds[1]['khop_toan_bo_6_truong_pct']} | {ds[2]['khop_toan_bo_6_truong_pct']} |")
    lines += ['', 'Nhóm viết tắt tên riêng còn 0% khớp sáu trường; CRF chỉ nhận vai trò, chưa có nguồn mở tên riêng. Nhóm lỗi gõ có thể được nhận đúng span nhưng giữ nguyên tên lỗi nên vẫn lệch chuỗi chuẩn. Các ca xã chia/mơ hồ còn vấn đề nhãn/tập đích; 0% không chứng minh mọi trường đều sai.', '',
              '## 8. Đảo thứ tự và ví dụ khó ngoài bảng dev', '',
              'Một fixture gồm sáu thành phần có tiền tố rõ và dấu phẩy, hoán vị 720 cách: luật, CRF gốc và CRF thêm khó đều 720/720. Đây là một fixture chức năng, không phải 720 địa chỉ thực độc lập.', '']
    for case in functional['stress_examples']:
        lines += ['Input: `'+case['input']+'`', '']
        for name,d in case['outputs'].items():
            lines += ['- '+name+': `'+d['address']+'`; chưa phân loại: `'+d['unknown']+'`.']
        lines += ['']
    lines += ['Các ca này cho thấy chưa giải quyết được đảo thứ tự thiếu tiền tố/dấu phân cách hay viết tắt mạnh, dù nhóm đảo thứ tự tổng hợp đạt cao. Không tự dùng chúng để điều chỉnh model trong lần thử này.', '',
              '## 9. Ca tăng điểm và ca thoái lui cần đọc', '']
    for mode,label in modes[1:]:
        with (folder/f'so_sanh_{mode}_dev_goc.csv').open(encoding='utf-8-sig',newline='') as f:
            rows=list(csv.DictReader(f))
        lines += ['### '+label, '']
        selected=[x for x in rows if x['state']=='mat_khop']
        for key in ('VNDEV_00001','VNDEV_00003','VNDEV_00034','VNDEV_00066','VNDEV_00068'):
            selected.extend(x for x in rows if x['id']==key and x['state']=='moi_khop')
        for x in selected:
            lines += ['**'+x['id']+' — '+x['state']+'**', '', '- Input: '+x['input'], '- Luật: '+x['before'], '- CRF: '+x['after'], '- Tham chiếu: '+x['reference'], '']
    lines += ['Điểm tăng có phần không phải cải thiện ngữ nghĩa: `843M+RH3` bị model lấy `843M` làm số nhà để khớp nhãn; có ca bỏ tên đường đang hiện diện hoặc bỏ Tổ 14 vì nhãn máy bỏ sót. Ngược lại, thôn bị nhận thành đường, lô bị nhận thành số nhà và một số tên đường bị bỏ là các thoái lui cần xử lý. Không tự sửa nhãn theo model hoặc thay model mặc định chỉ vì điểm tăng.', '',
              '## 10. Hiệu năng và kiểm chứng', '', '| Mode | Dev | Mean ms | p95 ms | Địa chỉ/s |', '|---|---|---:|---:|---:|']
    for mode,label in modes:
        for split in ('dev_goc','dev_kho'):
            t=r['end_to_end'][mode][split]['latency']
            lines.append(f"| {label} | {split} | {t['mean_ms']:.2f} | {t['p95_ms']:.2f} | {t['addresses_per_s']:.1f} |")
    lines += ['', 'Một lượt tuần tự trên máy đang làm việc, không phải so sánh tải máy chủ có kiểm soát. Đo chỉ pipeline, không tính ghi file/chẩn đoán. CRF được chạy một lần mỗi input, dùng lại nhãn/marginal cho các nhánh.', '',
              '53 kiểm tra đạt: 41 pipeline, 4 cách chấm, 8 hợp đồng CRF có train/lưu/nạp/chạy API thật. Baseline sau thêm adapter giữ nguyên kết quả v3 trên 1.136 mẫu; snapshot đầu vào được kiểm hash. Mỗi output giữ offset đúng chuỗi gốc và span không chồng.', '',
              '## Chạy lại', '', 'Tạo môi trường khi chưa có:', '', '```powershell',
              'py -3.12 -m venv .venv-crf',
              '.\\.venv-crf\\Scripts\\python.exe -m pip install -r requirements-crf.txt',
              '```', '', 'Dùng model đã train hoặc đo lại vào thư mục mới:', '', '```powershell',
              '.\\.venv-crf\\Scripts\\python.exe -X utf8 -B -m src "Số 12, Đường Lê Lợi, Phường Trúc Bạch, Quận Ba Đình, Hà Nội" --crf-model mo_hinh/thu_nghiem/crf_v1_01/train_goc.crfsuite',
              '.\\.venv-crf\\Scripts\\python.exe -X utf8 -B -m danh_gia.do_crf --experiment mo_hinh/thu_nghiem/crf_v1_01 --output-dir danh_gia/ket_qua/lan_do_crf_moi',
              '```', '', 'Thư mục đo mới phải chưa tồn tại. Cài thư viện qua requirements-crf.txt trong .venv-crf nếu cần. Muốn train lại, sao chép du_lieu_dong_bang và snapshot_manifest.json sang thư mục thí nghiệm mới rồi chạy danh_gia.huan_luyen_crf --experiment <thư mục mới>; không ghi đè model đã lưu.', '',
              '## Quyết định tiếp theo', '',
              'Giữ hai model để so sánh và thu thập lỗi; mặc định v3 chưa thay. Ưu tiên rà nhãn sai/thiếu, bổ sung nhãn vai trò ngoài mẫu quen thuộc và các nhóm ít hỗ trợ, thống nhất tokenizer cho số dính tiền tố. Sau đó train lại cùng phép đo. Chuẩn hóa tên viết tắt/lỗi gõ cần bộ sinh ứng viên và nguồn tra; xếp hạng toàn giả thuyết còn dùng điểm tay. Chưa có kết quả test vàng để nghiệm thu.', '']
    path.write_text('\n'.join(lines),encoding='utf-8',newline='\n')


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--folder',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    run(args.folder,args.output)
