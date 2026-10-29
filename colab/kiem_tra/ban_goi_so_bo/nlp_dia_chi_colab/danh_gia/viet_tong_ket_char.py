"""Tổng kết artifact đã đo, không train hay chạy lại benchmark."""

import argparse
import json
from pathlib import Path


def write_summary(run_dir, output):
    read = lambda p: json.loads(p.read_text(encoding='utf-8'))
    report = read(output / 'thong_ke.json')
    train = read(run_dir / 'training.json')
    rank = read(run_dir / 'ranker.json')
    audit = read(output / 'KIEM_TRA.json')
    ram = read(output / 'RAM_SUY_LUAN.json')
    lines = ['# Kết quả triển khai Char-CNN + CRF và LightGBM Ranker', '',
             'Đã triển khai, huấn luyện và chạy toàn pipeline trên CPU. Tốc độ đủ nhẹ cho bản thử; chất lượng chưa vượt CRF cũ đồng đều. Mặc định vẫn giữ luật v3.', '',
             '**Các tỷ lệ dưới đây là độ khớp nhãn máy/tổng hợp trên dev, chưa phải độ chính xác trên gold độc lập.**', '',
             '## Huấn luyện', '',
             f"- CNN: {train['samples']:,} mẫu, {train['parameters']:,} tham số, {len(train['history'])} vòng, **{train['train_seconds']:.2f} giây** trên {train['torch_threads']} luồng CPU.",
             f"- Ranker: {rank['group_count']:,} nhóm từ phần train riêng, {rank['hypotheses']:,} giả thuyết; **{rank['fit_seconds_including_features']:.2f} giây** kể cả sinh đặc trưng.",
             '- Chia theo họ che số nhà và ID mẫu cha; 0 nhóm giao giữa CNN và ranker, 0 họ che số nhà giao với dev đã kiểm tra.',
             '- Không sinh thêm câu train, không dùng nhãn test cuối để train/tune/đo.',
             '- Dữ liệu CNN và ranker không trùng nhóm nên CNN chỉ được học 4.841 mẫu, ít hơn CRF kết hợp 5.966 mẫu. Đây là đối chứng cả hệ thống, không phải so sánh encoder trên cùng số mẫu train.', '',
             '## End-to-end sáu trường', '',
             '| Tập | Luật v3 | CRF cũ kết hợp | CNN + điểm tay | CNN + ranker |',
             '|---|---:|---:|---:|---:|']
    modes = ('luat_v3', 'crf_cu', 'char_diem_tay', 'char_ranker')
    for split, ds in report['datasets'].items():
        cells = [f"{ds['modes'][m]['dung_toan_bo_6_truong']}/{ds['rows']} ({ds['modes'][m]['khop_toan_bo_6_truong_pct']:.2f}%)" for m in modes]
        lines.append('| ' + split + ' | ' + ' | '.join(cells) + ' |')
    lines += ['', 'Ranker giúp dev gốc so với CNN dùng điểm tay, nhưng giảm nhẹ dev khó. So với CRF cũ, bản đầy đủ được thêm 20 ca/mất 22 ca ở dev gốc, thêm 10 ca/mất 4 ca ở dev khó. Chưa chọn nó làm bản mặc định.', '',
              '## Từ nhận diện đến chọn kết quả', '',
              '| Phép đo CNN + ranker | Dev gốc | Dev khó |', '|---|---:|---:|']
    datasets = [report['datasets'][s] for s in ('dev_goc', 'dev_kho')]
    vals = lambda f: ' | '.join(f(d) for d in datasets)
    lines.append('| F1 span chi tiết độc lập | ' + vals(lambda d: f"{d['standalone_char_spans']['detail_span_micro']['f1_pct']:.2f}% ({d['standalone_char_spans']['rows']} câu)") + ' |')
    lines.append('| Mean riêng bộ nhận diện | ' + vals(lambda d: f"{d['standalone_char_spans']['latency']['mean_ms']:.2f} ms") + ' |')
    lines.append('| Ứng viên chứa xã tham chiếu, khi nhãn xã có giá trị | ' + vals(lambda d: f"{d['modes']['char_ranker']['stages']['candidate_contains_ward']}/{d['modes']['char_ranker']['stages']['reference_ward_nonempty']}") + ' |')
    lines.append('| Beam còn phương án đúng mã xã/tỉnh tham chiếu | ' + vals(lambda d: f"{d['modes']['char_ranker']['stages']['beam_has_reference_admin']}/{d['rows']}") + ' |')
    lines.append('| Beam còn phương án khớp cả sáu trường | ' + vals(lambda d: f"{d['modes']['char_ranker']['stages']['beam_has_reference_six_fields']}/{d['rows']}") + ' |')
    lines.append('| Cuối cùng khớp cả sáu trường | ' + vals(lambda d: f"{d['modes']['char_ranker']['dung_toan_bo_6_truong']}/{d['rows']}") + ' |')
    lines += ['', 'F1 đo đúng ranh giới ký tự và loại thành phần, gồm tiền tố trong span. Dev khó không có nhãn ngõ/hẻm, nên không dùng tỷ lệ trường trống để kết luận nhận diện ngõ tốt. Hành chính chỉ có nhãn căn chỉnh yếu một phần; recall từng cấp ở thong_ke.json, không báo precision giả.', '',
              'Trong tập phương án hiện có, ranker không thể vượt số ca mà beam còn giữ được đầy đủ sáu trường. Thiếu tên đường chuẩn, sai ranh giới và lỗi nhãn đều có thể làm mất phương án khớp; con số oracle này không xác định riêng từng nguyên nhân.', '',
              '## Tốc độ CPU', '',
              '| Chế độ | Dev gốc mean / P95 | Dev khó mean / P95 |', '|---|---:|---:|']
    for m in modes:
        cells = [f"{d['modes'][m]['latency']['mean_ms']:.2f} / {d['modes'][m]['latency']['p95_ms']:.2f} ms" for d in datasets]
        lines.append('| ' + m + ' | ' + ' | '.join(cells) + ' |')
    lines += ['', report['latency_scope'], '',
              f"RAM suy luận tiến trình riêng sau nạp và 21 lần gọi: **{ram['after_21_addresses']['working_set_mib']:.1f} MiB working set**, private committed {ram['after_21_addresses']['private_mib']:.1f} MiB. Khởi tạo kể cả import thư viện: {ram['initialization_including_optional_imports_seconds']:.2f} giây. Đây là Python + PyTorch + LightGBM + danh mục/trie/model, không phải chỉ file trọng số. Chưa đo cache sau chạy dài.", '',
              '## Kiểm chứng và cách dùng', '',
              '- 61 bài test đạt: CRF so với vét cạn, gradient nhãn một phần, padding, Unicode NFD/offset, cắt giữa token, train/load ranker, checksum và các hồi quy pipeline trước đó.',
              '- Toàn bộ kết quả luật v3 và CRF cũ giữ nguyên trên 1.136 + 464 câu; so sánh tất cả trường kết quả, cảnh báo và dấu vết.',
              '- Snapshot, train/dev gốc và sáu CSV danh mục giữ nguyên checksum.',
              '- Chưa có danh mục đường chứng thực; chưa tự phục hồi dấu hoặc mở rộng viết tắt tên đường.',
              '- Điểm neural/ranker chưa hiệu chỉnh thành xác suất; ngưỡng nhập nhằng cố định. Beam vẫn dùng điểm tay trước ranker.', '',
              'Hướng dẫn chạy/train/API: docs/THU_NGHIEM_CHAR_CNN_V1.md. Checkpoint: mo_hinh/thu_nghiem/char_v1_01/char_cnn.pt và ranker.txt.', '',
              'Dữ liệu kiểm chứng: thong_ke.json, KIEM_TRA.json, RAM_SUY_LUAN.json, kiem_thu.txt; JSONL chứa đầy đủ input/nhãn/output; so_sanh_loi.csv chứa các lỗi và thay đổi so với CRF; VI_DU_DUNG_SAI.json có ví dụ được thêm/mất khớp.', '']
    (output / 'TONG_KET.md').write_text('\n'.join(lines), encoding='utf-8', newline='\n')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--run-dir', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    args = p.parse_args()
    write_summary(args.run_dir.resolve(), args.output.resolve())


if __name__ == '__main__':
    main()
