"""Ablation sửa lõi: CNN/ranker giữ nguyên, từ điển chỉ từ train đóng băng."""

import argparse
import json
import platform
import shutil
import time
from collections import Counter
from dataclasses import asdict
from pathlib import Path

from src.tien_xu_ly.char_cnn import BoTachCharCNN
from src.chuan_hoa import BoChuanHoa
from src.tien_xu_ly.chuan_ten_duong import TuDienDuong, tao_tu_dien
from src.danh_muc import DanhMuc
from src.tien_xu_ly.duong_dan import tu_manifest
from src.tien_xu_ly.xep_hang import BoXepHang
from .chay_ban_thu import ROOT, CORE, aggregate, digest, norm, write_csv
from .do_char import latency
from .du_lieu_crf import doc_csv, doc_jsonl, ghi_jsonl
from .huan_luyen_char import save_json


def exact(p, r):
    return all(norm(p[f]) == norm(r[f]) for f in CORE)


def evaluate(output):
    output.mkdir(parents=True, exist_ok=False)
    run = ROOT / 'mo_hinh/thu_nghiem/char_v1_01'
    old = ROOT / 'danh_gia/ket_qua/char_v1_01_cuoi'
    frozen = json.loads((run / 'snapshot/sha256.json').read_text(encoding='utf-8'))
    assert all(digest(tu_manifest(run / 'snapshot', n)) == h for n, h in frozen.items())
    checked_paths = [run / 'char_cnn.pt', run / 'ranker.txt',
                     *[run / 'data' / (s + '.jsonl') for s in ('train_cnn', 'train_ranker', 'dev_goc', 'dev_kho')]]
    before = {str(p.relative_to(ROOT)): digest(p) for p in checked_paths}
    lex = tao_tu_dien(run / 'data/train_cnn.jsonl', output / 'tu_dien_duong_train.json')
    names = TuDienDuong(output / 'tu_dien_duong_train.json')
    extractor = BoTachCharCNN(run / 'char_cnn.pt', threads=1)
    dm = DanhMuc(run / 'snapshot/clean')
    ranker = BoXepHang(run / 'ranker.txt', extractor.ma_bam, dm.ma_bam)
    common = dict(danh_muc=dm, bo_tach=extractor, bo_xep_hang=ranker)
    models = {'baseline': BoChuanHoa(**common),
              'ten_train': BoChuanHoa(**common, tu_dien_duong=names),
              'bao_ve_duong': BoChuanHoa(**common, bao_ve_duong=True),
              'ket_hop': BoChuanHoa(**common, tu_dien_duong=names, bao_ve_duong=True)}
    warm = doc_jsonl(run / 'data/train_cnn.jsonl')[:10]
    for model in models.values():
        for row in warm:
            model.chuan_hoa(row['text'])
    report = {'heldout_test_read': False, 'model_or_ranker_retrained': False,
              'labels_changed': False, 'dictionary_train_rows': lex['source_rows'],
              'dictionary_entries': len(lex['entries']), 'dictionary_sha256': names.ma_bam,
              'dictionary_is_verified_gazetteer': False, 'frozen_inputs_sha256': before,
              'python': platform.python_version(), 'cpu_threads': 1,
              'measurement': 'CPU laptop, end-to-end đã nạp model; không gồm I/O/JSON/khởi tạo; 10 train warmup.',
              'label_quality': 'Khớp nhãn máy/tổng hợp trên dev đã dùng để phát triển, chưa phải gold độc lập.',
              'datasets': {}}
    comparison = []
    for split, filename in [('dev_goc', 'dev.csv'), ('dev_kho', 'dev_kho.csv')]:
        refs = doc_csv(run / 'snapshot' / filename)
        historical = doc_jsonl(old / f'char_ranker_{split}.jsonl')
        assert len(refs) == len(historical)
        result_modes = {}
        report['datasets'][split] = {'rows': len(refs), 'modes': {}}
        for mode, model in models.items():
            predictions, pairs, times = [], [], []
            for index, ref in enumerate(refs):
                start = time.perf_counter()
                result = model.chuan_hoa(ref['dau_vao'])
                times.append((time.perf_counter() - start) * 1000)
                pred = asdict(result)
                assert historical[index]['id'] == ref['id']
                if mode == 'baseline':
                    assert pred == historical[index]['prediction'], ('Baseline khác output cũ', ref['id'])
                occupied = set()
                for span in result.dau_vet:
                    a, b = span['ky_tu_bat_dau'], span['ky_tu_ket_thuc']
                    assert 0 <= a < b <= len(ref['dau_vao'])
                    assert span['doan_goc'] == ref['dau_vao'][a:b]
                    assert not occupied.intersection(range(a, b))
                    occupied.update(range(a, b))
                predictions.append({'id': ref['id'], 'input': ref['dau_vao'], 'latency_ms': times[-1],
                                    'reference': {f: ref[f] for f in CORE}, 'prediction': pred})
                pairs.append((ref, pred))
            stats = aggregate(pairs)
            stats['latency'] = latency(times)
            result_modes[mode] = predictions
            if mode != 'baseline':
                counts, fields = Counter(), {f: Counter() for f in CORE}
                for base, new in zip(result_modes['baseline'], predictions):
                    p0, p1, r = base['prediction'], new['prediction'], new['reference']
                    counts['gained'] += not exact(p0, r) and exact(p1, r)
                    counts['lost'] += exact(p0, r) and not exact(p1, r)
                    counts['changed_six_fields'] += any(norm(p0[f]) != norm(p1[f]) for f in CORE)
                    for f in CORE:
                        fields[f]['fixed'] += norm(p0[f]) != norm(r[f]) and norm(p1[f]) == norm(r[f])
                        fields[f]['broken'] += norm(p0[f]) == norm(r[f]) and norm(p1[f]) != norm(r[f])
                    if any(norm(p0[f]) != norm(p1[f]) for f in CORE):
                        comparison.append({'split': split, 'mode': mode, 'id': new['id'], 'input': new['input'],
                                           'reference': r, 'before': {f: p0[f] for f in CORE},
                                           'after': {f: p1[f] for f in CORE},
                                           'before_correct': exact(p0, r), 'after_correct': exact(p1, r)})
                stats['vs_baseline'] = dict(counts)
                stats['field_changes'] = {f: dict(v) for f, v in fields.items()}
            report['datasets'][split]['modes'][mode] = stats
            ghi_jsonl(output / f'{mode}_{split}.jsonl', predictions)
            print(json.dumps({'split': split, 'mode': mode, 'correct': stats['dung_toan_bo_6_truong'],
                              'pct': stats['khop_toan_bo_6_truong_pct'], 'latency': stats['latency'],
                              'vs_baseline': stats.get('vs_baseline')}, ensure_ascii=False), flush=True)
    assert all(digest(ROOT / n) == h for n, h in before.items())
    assert all(digest(tu_manifest(run / 'snapshot', n)) == h for n, h in frozen.items())
    report['baseline_matches_previous_full_outputs'] = True
    report['frozen_inputs_unchanged_after_eval'] = True
    save_json(output / 'thong_ke.json', report)
    ghi_jsonl(output / 'thay_doi_tung_cau.jsonl', comparison)
    write_csv(output / 'thay_doi_tung_cau.csv',
              ['split', 'mode', 'id', 'input', 'reference', 'before', 'after', 'before_correct', 'after_correct'],
              [{**r, **{k: json.dumps(r[k], ensure_ascii=False) for k in ('reference', 'before', 'after')}} for r in comparison])
    source = output / 'source'
    source.mkdir()
    files = [*list((ROOT / 'src').glob('*.py')), Path(__file__), ROOT / 'tests/test_chuan_ten_duong.py']
    for p in files:
        dest = source / p.relative_to(ROOT)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, dest)
    save_json(output / 'code_sha256.json', {p.relative_to(ROOT).as_posix(): digest(p) for p in files})
    lines = ['# Sửa pipeline, giữ nguyên CNN/ranker', '', report['label_quality'], '',
             '| Tập | Cấu hình | Đúng / tổng | Khớp 6 trường | Được / mất so mốc | Mean / P95 ms |',
             '|---|---|---:|---:|---:|---:|']
    for split, ds in report['datasets'].items():
        for mode, m in ds['modes'].items():
            delta = m.get('vs_baseline', {})
            lines.append(f"| {split} | {mode} | {m['dung_toan_bo_6_truong']}/{ds['rows']} | {m['khop_toan_bo_6_truong_pct']:.3f}% | {delta.get('gained', 0)}/{delta.get('lost', 0)} | {m['latency']['mean_ms']:.2f}/{m['latency']['p95_ms']:.2f} |")
    lines += ['', '## Kiểm soát phép thử', '',
              '- Không train lại CNN/ranker, không đổi nhãn, snapshot hoặc train/dev. Baseline tái hiện nguyên output cũ.',
              f"- Từ điển có {len(lex['entries'])} tên/tỉnh, chỉ từ {lex['source_rows']} mẫu train_cnn. Không đọc train_ranker để lập từ điển, không đọc test cuối.",
              '- Tên từ nhãn train chưa phải danh mục chứng thực; thêm cảnh báo và provenance khi đổi. Tra theo tỉnh dự đoán, không lấy tỉnh từ reference.',
              '- Giữ loại đường, không sửa dấu đã nhập, không đoán typo, không chọn khi trùng khóa khác tên. Dạng đầy đủ/viết tắt được đối chiếu riêng.',
              '- bao_ve_duong là thí nghiệm loại ứng viên admin không tiền tố nằm hoàn toàn trong span đường có tiền tố; không mặc định bật.',
              '- Mỗi sửa là tùy chọn; mặc định và model cũ được giữ để tái hiện. Dev đã dùng để phát triển nên điểm tăng chưa phải bằng chứng tổng quát hóa trên gold.',
              '- Tốc độ cùng lượt chạy trên laptop, không so trực tiếp với CPU Colab. Không gồm nạp model và I/O.',
              '- Output đầy đủ mỗi cấu hình nằm trong JSONL; thay_doi_tung_cau.csv/jsonl giữ mọi câu đổi, kể cả hồi quy. Code đo có snapshot và SHA-256.', '']
    (output / 'BAO_CAO.md').write_text('\n'.join(lines), encoding='utf-8', newline='\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    evaluate(parser.parse_args().output.resolve())
