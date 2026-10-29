"""Đo từ nhận diện span tới end-to-end trên dev đóng băng, không đọc test."""

import argparse
import json
import math
import platform
import re
import time
from collections import Counter, defaultdict
from dataclasses import asdict
from pathlib import Path

from src.char_cnn import BoTachCharCNN, ROLES
from src.chuan_hoa import BoChuanHoa
from src.chuyen_doi import sang_cay_moi, tap_dich
from src.crf_chi_tiet import BoTachCRF
from src.danh_muc import DanhMuc
from src.tach_phan_con import FIELDS
from src.xep_hang import BoXepHang
from .chay_ban_thu import ROOT, CORE, aggregate, digest, memory, norm, pct, write_csv
from .du_lieu_crf import doc_csv, doc_jsonl, ghi_jsonl
from .huan_luyen_char import save_json


class InstrumentedNormalizer(BoChuanHoa):
    def tao_gia_thuyet(self, text):
        result = super().tao_gia_thuyet(text)
        self.last = result
        return result


def latency(times):
    values = sorted(times)
    q = lambda n: values[max(0, math.ceil(n * len(values)) - 1)]
    return {'mean_ms': sum(times) / len(times), 'p50_ms': q(.5), 'p95_ms': q(.95),
            'max_ms': max(times), 'sequential_addresses_per_second': len(times) * 1000 / sum(times)}


def span_metrics(extractor, rows):
    counts = {f: Counter() for f in ROLES}
    exact_details = 0
    predictions = []
    times = []
    for rec in rows:
        t0 = time.perf_counter()
        context = extractor.chuan_bi_chuoi(rec['text'])
        times.append((time.perf_counter() - t0) * 1000)
        raw_gold = {(r, a, b) for r, a, b in rec['detail_spans_raw']}
        pred = set(context.char_spans)
        detail_pred = {s for s in pred if s[0] in FIELDS}
        exact_details += detail_pred == raw_gold
        for field in FIELDS:
            g = {s for s in raw_gold if s[0] == field}
            p = {s for s in pred if s[0] == field}
            counts[field].update({'tp': len(g & p), 'reference': len(g), 'predicted': len(p)})
        # Admin chỉ có nhãn căn chỉnh một phần: đo recall trên phần đã gán,
        # không coi mọi dự đoán ngoài đó là false positive.
        from src.char_cnn import nfc_offsets
        _, offsets = nfc_offsets(rec['text'])
        for role, a, b in rec['spans']:
            if role in ('xa', 'huyen', 'tinh'):
                gold = (role, offsets[a][0], offsets[b - 1][1])
                counts[role].update({'reference_weak': 1, 'recovered_weak': int(gold in pred)})
        predictions.append({'id': rec['id'], 'input': rec['text'], 'reference_details': sorted(raw_gold),
                            'predicted_spans': sorted(pred), 'detail_spans_exact': detail_pred == raw_gold})
    def f1(c):
        return {'reference': c['reference'], 'predicted': c['predicted'], 'tp': c['tp'],
                'precision_pct': pct(c['tp'], c['predicted']), 'recall_pct': pct(c['tp'], c['reference']),
                'f1_pct': pct(2 * c['tp'], c['reference'] + c['predicted'])}
    total = Counter()
    for field in FIELDS:
        total.update(counts[field])
    return {'rows': len(rows), 'detail_span_micro': f1(total), 'detail_by_field': {f: f1(counts[f]) for f in FIELDS},
            'all_detail_spans_exact_pct': pct(exact_details, len(rows)),
            'admin_weak_alignment_recall_only': {f: {**dict(counts[f]), 'recall_pct': pct(counts[f]['recovered_weak'], counts[f]['reference_weak'])} for f in ('xa', 'huyen', 'tinh')},
            'latency': latency(times)}, predictions


def evaluate(run_dir, output):
    output.mkdir(parents=True, exist_ok=False)
    frozen = json.loads((run_dir / 'snapshot/sha256.json').read_text(encoding='utf-8'))
    if any(digest(run_dir / 'snapshot' / name) != h for name, h in frozen.items()):
        raise ValueError('Snapshot bị thay đổi')
    dm = DanhMuc(run_dir / 'snapshot/clean')
    extractor = BoTachCharCNN(run_dir / 'char_cnn.pt', threads=1)
    ranker = BoXepHang(run_dir / 'ranker.txt', extractor.ma_bam, dm.ma_bam)
    original_crf = ROOT / 'mo_hinh/thu_nghiem/crf_v1_01/train_ket_hop.crfsuite'
    models = {
        'luat_v3': InstrumentedNormalizer(danh_muc=dm),
        'crf_cu': InstrumentedNormalizer(danh_muc=dm, bo_tach=BoTachCRF(original_crf)),
        'char_diem_tay': InstrumentedNormalizer(danh_muc=dm, bo_tach=extractor),
        'char_ranker': InstrumentedNormalizer(danh_muc=dm, bo_tach=extractor, bo_xep_hang=ranker),
    }
    # Warm-up trên train, không dùng nó để đo chất lượng dev.
    warm = doc_jsonl(run_dir / 'data/train_cnn.jsonl')[:10]
    for model in models.values():
        for r in warm:
            model.chuan_hoa(r['text'])
    report = {'label_quality': 'Độ khớp nhãn máy/tổng hợp trên dev, không phải độ chính xác gold.',
              'python': platform.python_version(), 'cpu_threads_neural': 1,
              'heldout_test_read': False, 'snapshot_unchanged': True,
              'latency_scope': 'Core end-to-end đã nạp mô hình, gồm neural/lookup/beam/ranker/trace; không gồm JSON, I/O, khởi tạo. Một lượt tuần tự, 10 câu train warm-up.',
              'model_sha256': {'char': extractor.ma_bam, 'ranker': ranker.ma_bam}, 'datasets': {}, 'memory_before_eval': memory()}
    comparison = []
    baseline_snapshots = {}
    for split, file in [('dev_goc', 'dev.csv'), ('dev_kho', 'dev_kho.csv')]:
        refs = doc_csv(run_dir / 'snapshot' / file)
        report['datasets'][split] = {'rows': len(refs), 'modes': {}}
        predictions_by_mode = {}
        for mode, model in models.items():
            pairs, times, predictions = [], [], []
            diagnostic = Counter()
            grouped = defaultdict(list)
            for row in refs:
                t0 = time.perf_counter()
                result = model.chuan_hoa(row['dau_vao'])
                times.append((time.perf_counter() - t0) * 1000)
                prediction = asdict(result)
                pairs.append((row, prediction))
                grouped['source:' + row.get('nguon_du_lieu', '')].append((row, prediction))
                variant = re.search(r'(?:^|;)\s*bien_the=([^;]+)', row.get('ghi_chu', ''))
                if variant:
                    grouped['variant:' + variant[1]].append((row, prediction))
                records, candidates, context, items = model.last
                candidate_targets = set().union(*(dm.dich_xa(u.cay, u.ma) for u in candidates))
                if row['ma_xa']:
                    diagnostic['reference_ward_nonempty'] += 1
                    diagnostic['candidate_contains_ward'] += row['ma_xa'] in candidate_targets
                oracle_admin, oracle_full = False, False
                for item in items:
                    _, path, detail, *_ = item
                    w, p, _ = sang_cay_moi(path, detail, dm)
                    same_admin = w == row['ma_xa'] and p == row['ma_tinh']
                    oracle_admin |= same_admin
                    oracle_full |= same_admin and all(norm(detail[f]) == norm(row[f]) for f in FIELDS)
                diagnostic['beam_has_reference_admin'] += oracle_admin
                diagnostic['beam_has_reference_six_fields'] += oracle_full
                # Kiểm chứng offset bằng chính chuỗi gốc và các khoảng không chồng.
                used = set()
                for span in result.dau_vet:
                    a, b = span['ky_tu_bat_dau'], span['ky_tu_ket_thuc']
                    if not 0 <= a < b <= len(row['dau_vao']) or span['doan_goc'] != row['dau_vao'][a:b]:
                        raise AssertionError('Trace offset sai ' + row['id'])
                    positions = set(range(a, b))
                    if used & positions:
                        raise AssertionError('Trace chồng ' + row['id'])
                    used |= positions
                predictions.append({'id': row['id'], 'input': row['dau_vao'], 'latency_ms': times[-1],
                                    'reference': {f: row[f] for f in CORE}, 'prediction': prediction})
            metrics = aggregate(pairs)
            metrics.update({'latency': latency(times), 'stages': dict(diagnostic),
                            'groups': {k: aggregate(v) for k, v in grouped.items()}})
            report['datasets'][split]['modes'][mode] = metrics
            ghi_jsonl(output / f'{mode}_{split}.jsonl', predictions)
            predictions_by_mode[mode] = predictions
            print(json.dumps({'split': split, 'mode': mode, 'six_fields_pct': metrics['khop_toan_bo_6_truong_pct'], 'latency': metrics['latency']}, ensure_ascii=False), flush=True)
        for i, ref in enumerate(refs):
            outputs = {m: rows[i]['prediction'] for m, rows in predictions_by_mode.items()}
            ok = lambda p: all(norm(p[f]) == norm(ref[f]) for f in CORE)
            if not ok(outputs['char_ranker']) or ok(outputs['char_ranker']) != ok(outputs['crf_cu']):
                comparison.append({'split': split, 'id': ref['id'], 'input': ref['dau_vao'],
                                   'reference': json.dumps({f: ref[f] for f in CORE}, ensure_ascii=False),
                                   **{m: json.dumps({f: p[f] for f in CORE}, ensure_ascii=False) for m, p in outputs.items()},
                                   'char_ranker_correct': ok(outputs['char_ranker']), 'old_crf_correct': ok(outputs['crf_cu'])})
        span_rows = doc_jsonl(run_dir / 'data' / (split + '.jsonl'))
        spans, predictions = span_metrics(extractor, span_rows)
        report['datasets'][split]['standalone_char_spans'] = spans
        ghi_jsonl(output / f'char_spans_{split}.jsonl', predictions)
    write_csv(output / 'so_sanh_loi.csv', ['split', 'id', 'input', 'reference', *models, 'char_ranker_correct', 'old_crf_correct'], comparison)
    report['memory_after_eval'] = memory()
    if any(digest(run_dir / 'snapshot' / name) != h for name, h in frozen.items()):
        raise ValueError('Snapshot thay đổi trong lúc đo')
    save_json(output / 'thong_ke.json', report)
    code = [*list((ROOT / 'src').glob('*.py')), Path(__file__)]
    save_json(output / 'code_sha256.json', {str(p.relative_to(ROOT)): digest(p) for p in code})
    lines = ['# Thử nghiệm Char-CNN + CRF và LambdaRank', '', report['label_quality'], '',
             '| Tập | Chế độ | Khớp 6 trường | Mean ms | P95 ms |', '|---|---|---:|---:|---:|']
    for split, dataset in report['datasets'].items():
        for name, m in dataset['modes'].items():
            lines.append(f"| {split} ({dataset['rows']}) | {name} | {m['khop_toan_bo_6_truong_pct']:.3f}% | {m['latency']['mean_ms']:.2f} | {m['latency']['p95_ms']:.2f} |")
    lines += ['', '## Phạm vi', '', report['latency_scope'], '',
              '- CNN và ranker dùng các họ train riêng; không fit hoặc chọn checkpoint bằng dev.',
              '- Nhãn hành chính nhận diện là căn chỉnh yếu, chưa phải BIO được kiểm chứng ngữ nghĩa.',
              '- Chưa có danh mục đường chứng thực; không tự phục hồi dấu hay mở rộng viết tắt tên đường.',
              '- Điểm ranker và emission không phải xác suất; ngưỡng gần nhau 0.05 chưa hiệu chỉnh.',
              '- Chi tiết từng tầng ở thong_ke.json; mọi input, nhãn, output ở JSONL; lỗi ở so_sanh_loi.csv.',
              '- P95 đo cục bộ một lượt, không phải SLA web hoặc benchmark máy chủ chuyên dụng.', '']
    (output / 'BAO_CAO.md').write_text('\n'.join(lines), encoding='utf-8', newline='\n')
    return report


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--run-dir', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    args = p.parse_args()
    evaluate(args.run_dir.resolve(), args.output.resolve())


if __name__ == '__main__':
    main()
