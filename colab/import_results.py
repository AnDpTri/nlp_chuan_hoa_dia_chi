"""Nhập ZIP kết quả từ Drive, kiểm SHA-256 và tổng hợp đối chứng, không train."""

import argparse
from collections import Counter
import hashlib
import json
import shutil
import unicodedata
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORE = ('so_nha', 'ngo_ngach_hem', 'thon_xom', 'duong', 'ma_xa', 'ma_tinh')
def digest(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()
def norm(s):
    return ' '.join(unicodedata.normalize('NFC', s).casefold().split())
def plain(s):
    return ''.join(c for c in unicodedata.normalize('NFD', norm(s).replace('đ', 'd')) if unicodedata.category(c) != 'Mn')
def read_json(p):
    return json.loads(p.read_text(encoding='utf-8'))
def read_rows(p):
    return [json.loads(line) for line in p.read_text(encoding='utf-8').splitlines() if line.strip()]


def import_results(archive):
    destination = ROOT / 'mo_hinh/thu_nghiem/videberta_v1_01'
    report_dir = ROOT / 'danh_gia/ket_qua/videberta_v1_01_colab'
    if destination.exists() or report_dir.exists():
        raise FileExistsError('Kết quả đã nhập; không ghi đè')
    with zipfile.ZipFile(archive) as z:
        manifest = json.loads(z.read('videberta_v1_01/SHA256_EXPORT.json'))
        for name in z.namelist():
            target = (destination.parent / name).resolve()
            if not target.is_relative_to(destination.resolve()):
                raise ValueError('ZIP có đường dẫn ngoài thư mục run')
        z.extractall(destination.parent)
    for name, expected in manifest.items():
        if digest(destination / name) != expected:
            raise ValueError('Checksum không khớp: ' + name)
    shutil.copytree(destination / 'reports_cpu_colab_01', report_dir)
    for name in ('training.json', 'run_config.json', 'ranker.json'):
        shutil.copy2(destination / name, report_dir / name)
    train = read_json(destination / 'training.json')
    stats = read_json(report_dir / 'thong_ke.json')
    local_data = ROOT / 'mo_hinh/thu_nghiem/char_v1_01/data'
    data_checks = {s: digest(local_data / (s + '.jsonl')) == h == digest(destination / 'data' / (s + '.jsonl'))
                   for s, h in train['config']['input_sha256'].items()}
    assert all(data_checks.values())
    snapshot = read_json(destination / 'snapshot/sha256.json')
    assert all(digest(destination / 'snapshot' / name.replace('\\', '/')) == h for name, h in snapshot.items())
    code_hashes = read_json(report_dir / 'code_sha256.json')
    with zipfile.ZipFile(ROOT / 'colab/dist/nlp_dia_chi_colab_v2.zip') as z:
        shipped = read_json(ROOT / 'colab/dist/v2/nlp_dia_chi_colab/BUNDLE_MANIFEST.json')['files']
        code_checks = {name: shipped.get(name, {}).get('sha256') == h for name, h in code_hashes.items()}
    # Script đánh giá tự đổi một trường metadata sau đo; code đo vẫn phải đúng gói.
    assert all(code_checks.values()), code_checks
    comparison, examples, breakdown = {}, [], {}
    for split in ('dev_goc', 'dev_kho'):
        new = read_rows(report_dir / f'videberta_ranker_{split}.jsonl')
        old = read_rows(report_dir / f'crf_cu_{split}.jsonl')
        cnn = read_rows(ROOT / 'danh_gia/ket_qua/char_v1_01_cuoi' / f'char_ranker_{split}.jsonl')
        ok = lambda p, r: all(norm(p[f]) == norm(r[f]) for f in CORE)
        c, errors, seen = Counter(), Counter(), Counter()
        for n, o, a in zip(new, old, cnn):
            assert n['id'] == o['id'] == a['id']
            assert n['reference'] == a['reference']
            r, pred = n['reference'], n['prediction']
            new_ok, old_ok = ok(pred, r), ok(o['prediction'], r)
            cnn_ok = ok(a['prediction'], r)
            c['vs_crf_gain'] += new_ok and not old_ok
            c['vs_crf_loss'] += old_ok and not new_ok
            c['vs_cnn_gain'] += new_ok and not cnn_ok
            c['vs_cnn_loss'] += cnn_ok and not new_ok
            bad_detail = any(norm(pred[f]) != norm(r[f]) for f in CORE[:4])
            bad_admin = any(norm(pred[f]) != norm(r[f]) for f in CORE[4:])
            if not new_ok:
                errors['both' if bad_detail and bad_admin else 'detail_only' if bad_detail else 'admin_only'] += 1
                errors['road_mismatch'] += norm(pred['duong']) != norm(r['duong'])
                errors['six_fields_only_accents'] += all(plain(pred[f]) == plain(r[f]) for f in CORE)
            kind = 'gain_vs_crf' if new_ok and not old_ok else 'loss_vs_crf' if old_ok and not new_ok else 'both_wrong'
            if kind != 'both_wrong' and seen[kind] < 2:
                examples.append({'split': split, 'kind': kind, 'input': n['input'], 'reference': r,
                                 'old_crf': {f: o['prediction'][f] for f in CORE}, 'videberta': {f: pred[f] for f in CORE}})
                seen[kind] += 1
        comparison[split], breakdown[split] = dict(c), dict(errors)
        assert sum(ok(n['prediction'], n['reference']) for n in new) == stats['datasets'][split]['modes']['videberta_ranker']['dung_toan_bo_6_truong']
    checks = {'zip_sha256': digest(archive), 'export_files_verified': len(manifest), 'all_export_hashes_match': True,
              'input_sha256_matches_cnn_experiment': data_checks, 'evaluation_code_matches_delivered_v2': code_checks,
              'comparison': comparison, 'mismatch_breakdown': breakdown,
              'gpu_epoch_training_seconds_sum': sum(x['seconds'] for x in train['history']),
              'limitations': 'Kiểm manifest và tính lại số khớp từ output, không đo lại inference hoặc xác nhận gold; latency là CPU Colab.'}
    (report_dir / 'KIEM_TRA_NHAP.json').write_text(json.dumps(checks, ensure_ascii=False, indent=2), encoding='utf-8', newline='\n')
    (report_dir / 'VI_DU_DUNG_SAI.json').write_text(json.dumps(examples, ensure_ascii=False, indent=2), encoding='utf-8', newline='\n')
    cnn_stats = read_json(ROOT / 'danh_gia/ket_qua/char_v1_01_cuoi/thong_ke.json')
    lines = ['# Kết quả ViDeBERTa-xsmall từ Colab', '',
             'Train đã hoàn tất. Lần thử này chưa vượt CRF/CNN đồng đều; chưa có căn cứ thay bản cũ bằng ViDeBERTa.', '',
             '| Cấu hình | Dev gốc (1136) | Dev khó (464) |', '|---|---:|---:|']
    for mode in ('luat_v3', 'crf_cu', 'cnn_ranker', 'videberta_diem_tay', 'videberta_ranker'):
        vals = [cnn_stats['datasets'][s]['modes']['char_ranker'] if mode == 'cnn_ranker' else stats['datasets'][s]['modes'][mode]
                for s in ('dev_goc', 'dev_kho')]
        lines.append('| ' + mode + ' | ' + ' | '.join(f"{v['dung_toan_bo_6_truong']} ({v['khop_toan_bo_6_truong_pct']:.3f}%)" for v in vals) + ' |')
    lines += ['', '**Đây là độ khớp nhãn máy/tổng hợp trên dev, không phải độ chính xác gold.**', '',
              f"GPU T4: {train['samples']} mẫu, {train['parameters']:,} tham số, 5 epoch; tổng thời gian vòng train {checks['gpu_epoch_training_seconds_sum']:.2f} giây, chưa gồm tải model/preprocessing/ghi checkpoint. Peak GPU allocated {train['peak_gpu_allocated_mib']:.1f} MiB.", '',
              '## Suy luận CPU Colab', '', '| Cấu hình | Dev gốc mean/P95 ms | Dev khó mean/P95 ms |', '|---|---:|---:|']
    for mode in ('crf_cu', 'videberta_diem_tay', 'videberta_ranker'):
        ms = [stats['datasets'][s]['modes'][mode]['latency'] for s in ('dev_goc', 'dev_kho')]
        lines.append('| ' + mode + ' | ' + ' | '.join(f"{v['mean_ms']:.2f}/{v['p95_ms']:.2f}" for v in ms) + ' |')
    lines += ['', 'Các số đo tốc độ trong bảng cùng CPU Colab, không gán cho CPU laptop. CNN trước đó đo trên laptop nên chỉ đối chiếu chất lượng bằng cùng dữ liệu, không lấy tỷ số latency khác máy.', '',
              '## Nhận định', '',
              '- ViDeBERTa + ranker giảm 16 câu khớp dev gốc, tăng 8 câu dev khó so với CRF kết hợp.',
              '- So với CNN + ranker, giảm 14 câu dev gốc, tăng 2 câu dev khó.',
              '- Ranker chỉ tăng 1 câu dev gốc nhưng giảm 2 câu dev khó so với ViDeBERTa điểm tay.',
              '- F1 span chi tiết: dev gốc 97.566% (1026 câu), dev khó 98.925% (464 câu). CNN tương ứng 98.132% và 98.761%: độ tốt không đồng đều ngay ở bước nhận diện.',
              '- Không chỉ là lỗi xếp hạng: beam chỉ có phương án khớp đủ 6 trường ở 915/1136 và 296/464 câu. Ranker chọn trong các phương án này, không tự bổ sung tên chuẩn còn thiếu.',
              '- Chưa có danh mục đường chứng thực, nhãn còn yếu, thôn/tổ train ít. Đây vẫn là các giới hạn; kết quả chưa chứng minh đổi encoder là đủ và cũng chưa chứng minh trần năng lực của ViDeBERTa.',
              '- Chưa thử ONNX/INT8 hoặc nhiều cấu hình fine-tune; chưa nên tối ưu tốc độ để che việc chưa tăng chất lượng.', '',
              '## Kiểm chứng và file', '',
              f"- Đã nhập checkpoint, tokenizer, ranker và report vào mo_hinh/thu_nghiem/videberta_v1_01; đối chiếu {len(manifest)} file với SHA256_EXPORT.json.",
              '- Bốn tập dữ liệu khớp SHA-256 với thử nghiệm CNN; code đánh giá khớp gói v2; tính lại số khớp từ JSONL đúng với thống kê.',
              '- KIEM_TRA_NHAP.json có kiểm chứng, số ca được/mất và phân loại lỗi. VI_DU_DUNG_SAI.json có input, nhãn, CRF cũ và output mới.',
              '- Các JSONL gốc, thong_ke.json, so_sanh_loi.csv được giữ nguyên. Không dùng kết quả test cuối, không tự thay dữ liệu hoặc mô hình mặc định.', '']
    (report_dir / 'TONG_KET.md').write_text('\n'.join(lines), encoding='utf-8', newline='\n')
    print(json.dumps(checks, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--zip', type=Path, required=True)
    import_results(parser.parse_args().zip)
