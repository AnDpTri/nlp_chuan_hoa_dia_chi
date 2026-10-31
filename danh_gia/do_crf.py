"""Đo từ BIO/span đến field, hành chính và end-to-end trên dev đóng băng."""

import argparse
import hashlib
import json
import math
import time
from collections import Counter, defaultdict
from dataclasses import asdict
from pathlib import Path

from .chay_ban_thu import CORE, DETAIL, aggregate, norm, memory, write_csv
from .du_lieu_crf import doc_csv, doc_jsonl, ghi_jsonl
from src.chuan_hoa import BoChuanHoa
from src.tien_xu_ly.crf_chi_tiet import BoTachCRF, bio_spans, tao_nhan
from src.tien_xu_ly import bo_dau, token_co_vi_tri
from src.tien_xu_ly.tim_kiem import sinh_ung_vien


def prf(tp, fp, fn):
    p, r = tp/(tp+fp) if tp+fp else 0., tp/(tp+fn) if tp+fn else 0.
    return {'tp': tp, 'fp': fp, 'fn': fn, 'precision_pct': round(p*100, 3),
            'recall_pct': round(r*100, 3), 'f1_pct': round(200*p*r/(p+r), 3) if p+r else 0.,
            'reference_spans': tp+fn}


def sequence_metrics(pairs):
    counts = {f: Counter() for f in DETAIL}
    token, exact, invalid, confusion = Counter(), 0, 0, Counter()
    for gold, pred in pairs:
        if len(gold) != len(pred):
            raise ValueError('Khác số token khi đo')
        exact += gold == pred
        gs, _ = bio_spans(gold)
        ps, bad = bio_spans(pred)
        invalid += bad
        for f in DETAIL:
            a, b = {(x, y) for role, x, y in gs if role == f}, {(x, y) for role, x, y in ps if role == f}
            counts[f].update(tp=len(a & b), fp=len(b-a), fn=len(a-b))
        for g, p in zip(gold, pred):
            token['total'] += 1
            token['correct'] += g == p
            token['tp_non_o'] += g == p and g != 'O'
            token['fp_non_o'] += p != 'O' and p != g
            token['fn_non_o'] += g != 'O' and p != g
            if g != p:
                confusion[(g, p)] += 1
    total = sum((c for c in counts.values()), Counter())
    per = {f: prf(c['tp'], c['fp'], c['fn']) for f, c in counts.items()}
    supported = [m['f1_pct'] for m in per.values() if m['reference_spans']]
    return {'sequences': len(pairs), 'tokens': token['total'],
            'token_accuracy_pct': round(100*token['correct']/token['total'], 3) if token['total'] else None,
            'token_non_o': prf(token['tp_non_o'], token['fp_non_o'], token['fn_non_o']),
            'sequence_exact_pct': round(100*exact/len(pairs), 3) if pairs else None,
            'span_micro': prf(total['tp'], total['fp'], total['fn']), 'span_per_field': per,
            'span_macro_f1_supported_pct': round(sum(supported)/len(supported), 3) if supported else None,
            'orphan_i_before_repair': invalid,
            'confusions': [{'gold': g, 'pred': p, 'count': n} for (g, p), n in confusion.most_common(20)]}


def labels_from_trace(text, pred):
    n = len(token_co_vi_tri(text))
    spans = [(s['truong'], s['token_bat_dau'], s['token_ket_thuc']) for s in pred['dau_vet'] if s['truong'] in DETAIL]
    return tao_nhan(n, spans)


def small_metrics(backend, records):
    pairs, ms = [], []
    for row in records:
        start = time.perf_counter()
        context = backend.chuan_bi(row['tokens'])
        ms.append((time.perf_counter()-start)*1000)
        pairs.append((row['tags'], context.labels))
    return {**sequence_metrics(pairs), 'inference_ms_mean': sum(ms)/len(ms) if ms else None}


def latency(times):
    ordered = sorted(times)
    return {'mean_ms': sum(times)/len(times), 'p50_ms': ordered[math.ceil(.5*len(times))-1],
            'p95_ms': ordered[math.ceil(.95*len(times))-1], 'max_ms': max(times),
            'addresses_per_s': 1000*len(times)/sum(times)}


def evaluate(model, rows, aligned, output_path, canonical_usable=None):
    pairs, elapsed, seq_pairs = [], [], []
    details_ok, details_plain_ok = 0, 0
    warnings, candidate_counts, hypothesis_counts = Counter(), [], []
    candidate_total, candidate_hit = 0, 0
    joint_predictions = []
    for idx, row in enumerate(rows, 1):
        start = time.perf_counter()
        pred = asdict(model.chuan_hoa(row['dau_vao']))
        elapsed.append((time.perf_counter()-start)*1000)
        pairs.append((row, pred))
        warnings.update(pred['canh_bao'])
        details_ok += all(norm(row[f]) == norm(pred[f]) for f in DETAIL)
        details_plain_ok += all(bo_dau(norm(row[f])) == bo_dau(norm(pred[f])) for f in DETAIL)
        if row['id'] in aligned:
            seq_pairs.append((aligned[row['id']]['tags'], labels_from_trace(row['dau_vao'], pred)))
        candidate_counts.append(pred['thong_ke']['so_ung_vien'])
        hypothesis_counts.append(pred['thong_ke']['so_gia_thuyet'])
        tokens = [t.chu for t in token_co_vi_tri(row['dau_vao'])]
        if row['ma_xa']:
            candidate_total += 1
            cs = sinh_ung_vien(tokens, model.trie, bao_ve_chi_tiet=model.bo_tach is None or model.bo_tach.bao_ve_chi_tiet)
            target = set().union(*(model.danh_muc.dich_xa(u.cay, u.ma) for u in cs))
            candidate_hit += row['ma_xa'] in target
        used = set()
        for s in pred['dau_vet']:
            if s['doan_goc'] != row['dau_vao'][s['ky_tu_bat_dau']:s['ky_tu_ket_thuc']]:
                raise ValueError('Dấu vết sai '+row['id'])
            inds = set(range(s['token_bat_dau'], s['token_ket_thuc']))
            if used & inds:
                raise ValueError('Dấu vết chồng '+row['id'])
            used |= inds
        joint_predictions.append({'id': row['id'], 'dau_vao': row['dau_vao'], 'ms': elapsed[-1], **pred})
        if idx % 400 == 0:
            print(f'{output_path.stem}: {idx}/{len(rows)}', flush=True)
    ghi_jsonl(output_path, joint_predictions)
    groups = defaultdict(list)
    for row, pred in pairs:
        groups['source:'+row.get('nguon_du_lieu', '')].append((row, pred))
        if row.get('loai_bien_the'):
            groups['variant:'+row['loai_bien_the']].append((row, pred))
        if canonical_usable is not None and canonical_usable.get(row['id'], False):
            groups['usable_for_canonical_training'].append((row, pred))
    return {**aggregate(pairs), 'detail_4_exact_pct': round(100*details_ok/len(rows), 3),
            'detail_4_ignore_accents_pct': round(100*details_plain_ok/len(rows), 3),
            'actual_pipeline_spans_on_aligned_subset': sequence_metrics(seq_pairs),
            'candidate_target_recall': {'reference_nonempty': candidate_total, 'found': candidate_hit,
                                        'pct': round(100*candidate_hit/candidate_total, 3) if candidate_total else None},
            'candidate_count_mean': sum(candidate_counts)/len(rows), 'hypothesis_count_mean': sum(hypothesis_counts)/len(rows),
            'groups': {k: aggregate(v) for k, v in groups.items()},
            'latency': latency(elapsed), 'warnings': dict(warnings), 'memory_after': memory()}


def compare_examples(rows, before, after, out):
    a, b = {r['id']: r for r in doc_jsonl(before)}, {r['id']: r for r in doc_jsonl(after)}
    counts, output = Counter(), []
    for row in rows:
        key = row['id']
        x, y = all(norm(row[f]) == norm(a[key][f]) for f in CORE), all(norm(row[f]) == norm(b[key][f]) for f in CORE)
        state = 'giu_khop' if x and y else 'moi_khop' if y else 'mat_khop' if x else 'van_lech'
        counts[state] += 1
        output.append({'id': key, 'state': state, 'input': row['dau_vao'], 'before': a[key]['dia_chi_chuan'],
                       'after': b[key]['dia_chi_chuan'], 'reference': row['dia_chi_chuan'],
                       'before_6': json.dumps({f: a[key][f] for f in CORE}, ensure_ascii=False),
                       'after_6': json.dumps({f: b[key][f] for f in CORE}, ensure_ascii=False),
                       'reference_6': json.dumps({f: row[f] for f in CORE}, ensure_ascii=False),
                       'wrong_after': ','.join(f for f in CORE if norm(row[f]) != norm(b[key][f])),
                       'warnings': json.dumps(b[key]['canh_bao'], ensure_ascii=False)})
    write_csv(out, tuple(output[0]), output)
    return dict(counts)


def run(experiment, output):
    output.mkdir(parents=True, exist_ok=False)
    snap = experiment/'du_lieu_dong_bang'
    datasets = {'dev_goc': doc_csv(snap/'dev.csv'), 'dev_kho': doc_csv(snap/'dev_kho.csv')}
    aligned = {name: {r['id']: r for r in doc_jsonl(experiment/'du_lieu_crf'/(name+'.jsonl'))} for name in datasets}
    snapshot_manifest = json.loads((experiment/'snapshot_manifest.json').read_text(encoding='utf-8'))
    def check_snapshot():
        for name, info in snapshot_manifest.items():
            if hashlib.sha256((snap/name).read_bytes()).hexdigest() != info['sha256']:
                raise ValueError('Snapshot đã đổi '+name)
    check_snapshot()
    trained = json.loads((experiment/'training_summary.json').read_text(encoding='utf-8'))
    small = {}
    for name in ('train_goc', 'train_ket_hop'):
        backend = BoTachCRF(experiment/(name+'.crfsuite'))
        if backend.ma_bam != trained[name]['model_sha256']:
            raise ValueError('Model đã đổi')
        small[name] = {}
        for split in ('train_goc' if name == 'train_goc' else 'train_ket_hop', 'dev_goc', 'dev_kho'):
            small[name][split] = small_metrics(backend, doc_jsonl(experiment/'du_lieu_crf'/(split+'.jsonl')))
    print('Đã đo BIO/span đơn lẻ cho hai mô hình', flush=True)
    modes = {'luat_v3': None,
             'crf_train_goc_mo': (experiment/'train_goc.crfsuite', False),
             'crf_ket_hop_mo': (experiment/'train_ket_hop.crfsuite', False),
             'crf_ket_hop_bao_ve': (experiment/'train_ket_hop.crfsuite', True)}
    result = {}
    for name, spec in modes.items():
        start = time.perf_counter()
        backend = BoTachCRF(spec[0], bao_ve_chi_tiet=spec[1]) if spec else None
        model = BoChuanHoa(bo_tach=backend)
        result[name] = {'init_s': time.perf_counter()-start}
        for split, rows in datasets.items():
            usable = {r['id']: r.get('usable_for_canonical_training', False) for r in doc_jsonl(snap/'dev_spans.jsonl')} if split == 'dev_kho' else None
            result[name][split] = evaluate(model, rows, aligned[split], output/(name+'_'+split+'.jsonl'), usable)
    comparisons = {}
    for mode in modes:
        if mode == 'luat_v3':
            continue
        comparisons[mode] = {}
        for split, rows in datasets.items():
            comparisons[mode][split] = compare_examples(rows, output/('luat_v3_'+split+'.jsonl'), output/(mode+'_'+split+'.jsonl'), output/('so_sanh_'+mode+'_'+split+'.csv'))
    # Baseline sau khi thêm adapter phải giống baseline v3 đã bàn giao từng ô.
    prior = experiment.parents[2]/'danh_gia/ket_qua/ban_thu_v3_cuoi/du_doan.jsonl'
    # experiment = root/mo_hinh/thu_nghiem/run => parents[2] là root.
    base = {r['id']: r for r in doc_jsonl(prior)}
    for row in doc_jsonl(output/'luat_v3_dev_goc.jsonl'):
        old = base[row['id']]
        for f in CORE:
            if row[f] != old[f]:
                raise ValueError('Adapter làm đổi baseline '+row['id']+' '+f)
    check_snapshot()
    root = experiment.parents[2]
    sources = list((root/'src').glob('*.py'))+[Path(__file__), root/'danh_gia/du_lieu_crf.py', root/'danh_gia/huan_luyen_crf.py']
    report = {'experiment': str(experiment), 'data_quality': json.loads((experiment/'du_lieu_crf/summary.json').read_text(encoding='utf-8')),
              'training': trained, 'standalone': small, 'end_to_end': result, 'comparisons': comparisons,
              'baseline_v3_unchanged_on_all1136': True, 'snapshot_unchanged': True,
              'source_sha256': {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
              'limitations': ['Nhãn máy/tổng hợp, chưa phải gold ngữ nghĩa.',
                              'Dev gốc và dev khó có liên quan nguồn; không cộng thành test độc lập.',
                              'Span chỉ đo trên phần căn chỉnh được: báo riêng số mẫu và nhãn hỗ trợ.',
                              'Chuẩn hóa đo cả dấu và loại; CRF không phục hồi tên riêng không có nguồn tra.',
                              'Điểm ghép dùng marginal O và trọng số tay, chưa có mô hình xếp hạng học.',
                              'CRF dự đoán độc lập một lần; từng nhánh hành chính ép token đã chọn về O, không phải giải mã CRF có ràng buộc tối ưu.',
                              'Không chọn siêu tham số theo dev; bốn cấu hình được báo đầy đủ, không tự thay mặc định v3.',
                              'Tập test cuối không được đọc hoặc dùng trong thí nghiệm.']}
    (output/'thong_ke.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8', newline='\n')
    write_report(output/'BAO_CAO.md', report)
    print(json.dumps({name: {split: {'khop_6': data[split]['khop_toan_bo_6_truong_pct'], 'span_f1': data[split]['actual_pipeline_spans_on_aligned_subset']['span_micro']['f1_pct']} for split in datasets} for name, data in result.items()}, ensure_ascii=False, indent=2))
    return report


def write_report(path, r):
    lines = ['# Thử nghiệm CRF CPU: từ token đến end-to-end', '',
             '**Đây là phép thử trên nhãn máy/tổng hợp đã đóng băng, không phải điểm test vàng.** Mặc định sản phẩm giữ luật v3. Không dùng GPU, không đọc test cuối.', '',
             '## Dữ liệu và chất lượng nhãn', '', '| Tập | Input | Qua lọc cơ học | Dùng | Token |', '|---|---:|---:|---:|---:|']
    for name, d in r['data_quality']['datasets'].items():
        lines.append(f"| {name} | {d.get('input_rows', '—')} | {d.get('mechanically_accepted', '—')} | {d.get('used_rows', '—')} | {d.get('tokens', '—')} |")
    lines += ['', r['data_quality']['label_quality'], '',
              f"Số họ input train/dev trùng sau lọc: {r['data_quality']['heldout_family_overlap_after_filter']}. Phép kiểm này che span số nhà và chuẩn hóa chữ/dấu câu; không chứng minh độc lập về mọi nguồn/template.", '',
              '## Huấn luyện CPU', '', '| Mô hình | Mẫu | Token | Chuẩn bị feature (s) | Train (s) | Model (KiB) |', '|---|---:|---:|---:|---:|---:|']
    for name, d in r['training'].items():
        lines.append(f"| {name} | {d['rows']} | {d['tokens']} | {d['feature_preparation_s']:.2f} | {d['fit_s']:.2f} | {d['model_bytes']/1024:.1f} |")
    lines += ['', 'Cấu hình cố định: L-BFGS, c1=0.1, c2=0.1, tối đa 100 vòng, xét mọi chuyển nhãn. Không lấy dev làm dữ liệu fit/chọn siêu tham số.', '',
              '## CRF đơn lẻ: token và span', '', '| Mô hình | Tập | Mẫu | Token accuracy (%) | Non-O token F1 (%) | Span F1 (%) | Cả chuỗi BIO (%) |', '|---|---|---:|---:|---:|---:|---:|']
    for name, datasets in r['standalone'].items():
        for split, d in datasets.items():
            lines.append(f"| {name} | {split} | {d['sequences']} | {d['token_accuracy_pct']} | {d['token_non_o']['f1_pct']} | {d['span_micro']['f1_pct']} | {d['sequence_exact_pct']} |")
    lines += ['', 'Span F1 yêu cầu đúng vai trò và cả hai ranh giới. Không biến nhiều token O thành bằng chứng hiệu quả; xem thêm non-O và từng trường. I mồ côi được đếm trước khi sửa để tạo span.', '',
              '### Span theo trường trên dev khó', '', '| Model | Trường | Nhãn hỗ trợ | Precision (%) | Recall (%) | F1 (%) |', '|---|---|---:|---:|---:|---:|']
    for name, datasets in r['standalone'].items():
        for f, d in datasets['dev_kho']['span_per_field'].items():
            lines.append(f"| {name} | {f} | {d['reference_spans']} | {d['precision_pct']} | {d['recall_pct']} | {d['f1_pct']} |")
    lines += ['', 'Trường không có nhãn hỗ trợ không được coi F1=0 là bằng chứng model kém hoặc mọi trường trống là chính xác cao.', '',
              '## Tích hợp pipeline: span, field, hành chính, địa chỉ', '',
              '| Cấu hình | Tập | Span F1 (%) | Khớp 4 chi tiết (%) | 4 chi tiết bỏ khác dấu (%) | Mã xã (%) | Mã tỉnh (%) | Khớp 6 (%) |', '|---|---|---:|---:|---:|---:|---:|---:|']
    for mode, datasets in r['end_to_end'].items():
        for split in ('dev_goc', 'dev_kho'):
            d = datasets[split]
            lines.append(f"| {mode} | {split} | {d['actual_pipeline_spans_on_aligned_subset']['span_micro']['f1_pct']} | {d['detail_4_exact_pct']} | {d['detail_4_ignore_accents_pct']} | {d['tung_truong']['ma_xa']['ty_le_khop_pct']} | {d['tung_truong']['ma_tinh']['ty_le_khop_pct']} | {d['khop_toan_bo_6_truong_pct']} |")
    lines += ['', 'Các mẫu span và mẫu end-to-end có thể khác số lượng. End-to-end dùng toàn bộ CSV tương ứng, có cả nhãn nghi vấn. Bốn trường chi tiết và sáu trường đều tính cả nhãn trống.', '',
              '### Canonical được phép dùng trong dev khó', '', '| Cấu hình | Mẫu | Khớp 6 (%) |', '|---|---:|---:|']
    for mode, datasets in r['end_to_end'].items():
        d = datasets['dev_kho']['groups'].get('usable_for_canonical_training')
        if d:
            lines.append(f"| {mode} | {d['so_mau']} | {d['khop_toan_bo_6_truong_pct']} |")
    lines += ['', 'Tập được gắn usable canonical vẫn chưa phải gold. Các mẫu ngoài tập này có viết tắt/mơ hồ chủ ý; không ép mô hình mở tên riêng theo nhãn ẩn.', '',
              '## Thay đổi so với v3', '', '| Cấu hình | Tập | Mới khớp | Mất khớp | Giữ khớp | Vẫn lệch |', '|---|---|---:|---:|---:|---:|']
    for mode, datasets in r['comparisons'].items():
        for split, d in datasets.items():
            lines.append(f"| {mode} | {split} | {d.get('moi_khop',0)} | {d.get('mat_khop',0)} | {d.get('giu_khop',0)} | {d.get('van_lech',0)} |")
    lines += ['', '## Hiệu năng', '', '| Cấu hình | Tập | Mean (ms) | p95 (ms) | Địa chỉ/s | Mean ứng viên | Mean nhánh |', '|---|---|---:|---:|---:|---:|---:|']
    for mode, datasets in r['end_to_end'].items():
        for split in ('dev_goc', 'dev_kho'):
            d, t = datasets[split], datasets[split]['latency']
            lines.append(f"| {mode} | {split} | {t['mean_ms']:.3f} | {t['p95_ms']:.3f} | {t['addresses_per_s']:.1f} | {d['candidate_count_mean']:.1f} | {d['hypothesis_count_mean']:.1f} |")
    lines += ['', 'Một lượt trên máy hiện tại, các cấu hình chạy tuần tự; latency chỉ gồm pipeline, không gồm chẩn đoán/ghi file. RAM trong JSON là toàn tiến trình đánh giá, không phải riêng model hoặc dự toán cloud.', '',
              '## Đọc các mức đo', '',
              '- Bộ sinh: candidate_target_recall trong JSON đo đích có mặt trong hợp các ứng viên, không bảo đảm có nhánh hợp lệ/chọn đúng.',
              '- CRF đơn lẻ: đo nhãn vai trò trước khi gắn hành chính.',
              '- Span pipeline: đo nhãn sau lựa chọn hành chính và formatter, có thể khác CRF đơn lẻ.',
              '- Field: đo chuỗi chuẩn hóa, có thể lệch vì dấu, tiền tố hoặc loại dù span đúng.',
              '- Mã và sáu trường: đo toàn tuyến; model tách tốt không bảo đảm xếp hạng/chuyển đổi đúng.', '',
              '## Tệp kiểm chứng', '',
              '- thong_ke.json: toàn bộ chỉ số theo lớp/nguồn/biến thể, cảnh báo, train time, RAM và hash.',
              '- *_dev_*.jsonl: input/output và dấu vết đầy đủ cho từng cấu hình.',
              '- so_sanh_*.csv: toàn input/output trước/sau/tham chiếu và từng trường lệch; xem cả ca tăng và giảm.',
              '- Snapshot và *.crfsuite/*.json nằm trong thư mục thí nghiệm nêu trong JSON.', '',
              '## Giới hạn', '']
    lines += ['- '+x for x in r['limitations']]
    path.write_text('\n'.join(lines)+'\n', encoding='utf-8', newline='\n')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--experiment', type=Path, required=True)
    p.add_argument('--output-dir', type=Path, required=True)
    a = p.parse_args()
    run(a.experiment.resolve(), a.output_dir.resolve())
