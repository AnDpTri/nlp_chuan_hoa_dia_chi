"""Đối chứng cùng CPU; mỗi bộ nhận diện chạy một lần/câu, tái dùng cho các nhánh."""
import copy
import json
import time
from collections import Counter
from dataclasses import asdict
from pathlib import Path

from src.chuan_hoa import BoChuanHoa
from src.char_cnn import BoTachCharCNN
from src.videberta import BoTachViDeberta
from src.crf_chi_tiet import BoTachCRF, bio_spans
from src.chuan_ten_duong import TuDienDuong
from src.chuyen_doi import sang_cay_moi
from src.danh_muc import DanhMuc
from src.tien_xu_ly import token_co_vi_tri
from src.xep_hang import BoXepHang
from .chay_ban_thu import ROOT, CORE, aggregate, norm, digest
from .do_char import latency
from .du_lieu_crf import doc_csv, doc_jsonl, ghi_jsonl

OUT = ROOT / 'danh_gia/ket_qua/ma_tran_v1_01'
CNN = ROOT / 'mo_hinh/thu_nghiem/char_v1_01'
VI = ROOT / 'mo_hinh/thu_nghiem/videberta_v1_01'


class Cached:
    def __init__(self, backend):
        self.backend = backend
    def __getattr__(self, name):
        if name == 'chuan_bi_chuoi' and not hasattr(self.backend, name):
            raise AttributeError(name)
        return getattr(self.backend, name)
    def chuan_bi(self, tokens):
        return self.context


class NeuralCached(Cached):
    def chuan_bi_chuoi(self, text):
        return self.context


class Measured(BoChuanHoa):
    def tao_gia_thuyet(self, text):
        value = super().tao_gia_thuyet(text)
        self.last = value
        return value


def exact(p, r):
    return all(norm(p[f]) == norm(r[f]) for f in CORE)


def run():
    OUT.mkdir(parents=True, exist_ok=False)
    dm = DanhMuc(CNN / 'snapshot/clean')
    names_path = ROOT / 'danh_gia/ket_qua/sua_pipeline_cnn_v1_01/tu_dien_duong_train.json'
    names = TuDienDuong(names_path)
    paths = [CNN / 'char_cnn.pt', CNN / 'ranker.txt', VI / 'model/model.safetensors', VI / 'ranker.txt', names_path,
             *list((CNN / 'snapshot').glob('*.csv'))]
    hashes = {str(p.relative_to(ROOT)): digest(p) for p in paths}
    report = {'no_training': True, 'heldout_test_read': False, 'cpu_threads': 1,
              'timing': 'Cùng CPU laptop. Mỗi extractor đo một lần/câu; mỗi nhánh đo phần pipeline riêng. Tổng = extract + pipeline, không gồm deepcopy cache, JSON, I/O, khởi tạo hoặc oracle hậu kiểm. Đây là tổng thành phần, không phải các lượt full độc lập.',
              'labels': 'Khớp nhãn máy/tổng hợp trên dev đã dùng phát triển, không phải gold.',
              'hashes': hashes, 'datasets': {}}
    for split, filename in [('dev_goc', 'dev.csv'), ('dev_kho', 'dev_kho.csv')]:
        refs = doc_csv(CNN / 'snapshot' / filename)
        report['datasets'][split] = {'rows': len(refs), 'modes': {}, 'spans': {}}
    backends = [('luat', None), ('crf', BoTachCRF(ROOT / 'mo_hinh/thu_nghiem/crf_v1_01/train_ket_hop.crfsuite')),
                ('cnn', BoTachCharCNN(CNN / 'char_cnn.pt', threads=1)),
                ('videberta', BoTachViDeberta(VI / 'model', threads=1))]
    for name, backend in backends:
        print('START ' + name, flush=True)
        neural = name in ('cnn', 'videberta')
        cached = NeuralCached(backend) if neural else Cached(backend) if backend else None
        ranker = BoXepHang((CNN if name == 'cnn' else VI) / 'ranker.txt', backend.ma_bam, dm.ma_bam) if neural else None
        models = {}
        for fixed in (False, True):
            for ranked in ([False, True] if neural else [False]):
                key = name + ('_ranker' if ranked else '_tay') + ('_sua' if fixed else '_cu')
                models[key] = Measured(danh_muc=dm, bo_tach=cached, bo_xep_hang=ranker if ranked else None,
                                       tu_dien_duong=names if fixed else None, bao_ve_duong=fixed)
        # Warm-up một lần mỗi nhánh trên train.
        for row in doc_jsonl(CNN / 'data/train_cnn.jsonl')[:3]:
            if backend:
                ctx = backend.chuan_bi_chuoi(row['text']) if neural else backend.chuan_bi([t.chu for t in token_co_vi_tri(row['text'])])
            for model in models.values():
                if cached:
                    cached.context = copy.deepcopy(ctx)
                model.chuan_hoa(row['text'])
        for split, filename in [('dev_goc', 'dev.csv'), ('dev_kho', 'dev_kho.csv')]:
            refs = doc_csv(CNN / 'snapshot' / filename)
            span_refs = {r['id']: r for r in doc_jsonl(CNN / 'data' / (split + '.jsonl'))}
            outputs = {k: [] for k in models}
            timing = {k: [] for k in models}
            extract_times, counts = [], Counter()
            stage = {k: Counter() for k in models}
            for i, ref in enumerate(refs):
                start = time.perf_counter()
                if backend:
                    ctx = backend.chuan_bi_chuoi(ref['dau_vao']) if neural else backend.chuan_bi([t.chu for t in token_co_vi_tri(ref['dau_vao'])])
                extract_ms = (time.perf_counter() - start) * 1000 if backend else 0.
                extract_times.append(extract_ms)
                if backend and ref['id'] in span_refs:
                    gold = {tuple(s) for s in span_refs[ref['id']]['detail_spans_raw']}
                    if neural:
                        pred = {s for s in ctx.char_spans if s[0] in CORE[:4]}
                    else:
                        records = token_co_vi_tri(ref['dau_vao'])
                        pred = set()
                        for f, a, b in bio_spans(ctx.labels)[0]:
                            while a < b and not any(c.isalnum() for c in records[a].chu): a += 1
                            while b > a and not any(c.isalnum() for c in records[b-1].chu): b -= 1
                            if a < b: pred.add((f, records[a].bat_dau, records[b-1].ket_thuc))
                    counts.update(rows=1, tp=len(pred & gold), predicted=len(pred), reference=len(gold), exact=int(pred == gold))
                for key, model in models.items():
                    if cached:
                        cached.context = copy.deepcopy(ctx)
                    start = time.perf_counter()
                    pred = asdict(model.chuan_hoa(ref['dau_vao']))
                    total = extract_ms + (time.perf_counter() - start) * 1000
                    timing[key].append(total)
                    outputs[key].append({'id': ref['id'], 'input': ref['dau_vao'], 'reference': {f: ref[f] for f in CORE},
                                         'latency_ms': total, 'prediction': pred})
                    _, candidates, _, items = model.last
                    targets = set().union(*(dm.dich_xa(u.cay, u.ma) for u in candidates))
                    stage[key]['reference_ward_nonempty'] += bool(ref['ma_xa'])
                    stage[key]['candidate_contains_ward'] += bool(ref['ma_xa']) and ref['ma_xa'] in targets
                    admin, full = False, False
                    for _, path, detail, *_ in items:
                        w, p, _ = sang_cay_moi(path.ung_vien, detail, dm)
                        same = (w, p) == (ref['ma_xa'], ref['ma_tinh'])
                        admin |= same
                        detail = dict(detail)
                        if model.tu_dien_duong:
                            detail['duong'] = names.chuan_hoa(detail['duong'], p)[0]
                        full |= same and all(norm(detail[f]) == norm(ref[f]) for f in CORE[:4])
                    stage[key]['beam_admin'] += admin
                    stage[key]['beam_six_fields'] += full
                if (i + 1) % 400 == 0:
                    print(f'{name} {split} {i+1}/{len(refs)}', flush=True)
            if backend:
                report['datasets'][split]['spans'][name] = {**dict(counts),
                    'f1_pct': 200 * counts['tp'] / max(1, counts['predicted'] + counts['reference']),
                    'extract_latency': latency(extract_times)}
            for key, rows in outputs.items():
                stats = aggregate([(r, o['prediction']) for r, o in zip(refs, rows)])
                stats.update(latency=latency(timing[key]), stages=dict(stage[key]))
                report['datasets'][split]['modes'][key] = stats
                ghi_jsonl(OUT / f'{key}_{split}.jsonl', rows)
                print(json.dumps({'split': split, 'mode': key, 'correct': stats['dung_toan_bo_6_truong'],
                                  'mean_ms': stats['latency']['mean_ms']}, ensure_ascii=False), flush=True)
            (OUT / 'thong_ke.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    assert all(digest(ROOT / p) == h for p, h in hashes.items())
    report['frozen_unchanged_after'] = True
    for split in report['datasets']:
        cnn = doc_jsonl(OUT / f'cnn_ranker_sua_{split}.jsonl')
        vi = doc_jsonl(OUT / f'videberta_ranker_sua_{split}.jsonl')
        cells = Counter()
        pairs = []
        for a, b in zip(cnn, vi):
            assert a['id'] == b['id'] and a['reference'] == b['reference']
            ok_a, ok_b = exact(a['prediction'], a['reference']), exact(b['prediction'], b['reference'])
            kind = 'both_correct' if ok_a and ok_b else 'cnn_only' if ok_a else 'videberta_only' if ok_b else 'both_wrong'
            cells[kind] += 1
            pairs.append({'id': a['id'], 'input': a['input'], 'kind': kind, 'reference': a['reference'],
                          'cnn': a['prediction'], 'videberta': b['prediction']})
        report['datasets'][split]['cnn_vs_videberta_ranker_fixed'] = dict(cells)
        ghi_jsonl(OUT / f'doi_chieu_{split}.jsonl', pairs)
    (OUT / 'thong_ke.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    lines = ['# Ma trận cùng pipeline và CPU', '', report['labels'], '', report['timing'], '',
             '| Tập | Cấu hình | Đúng | % | Mean/P95 ms | Beam có đủ 6 trường |', '|---|---|---:|---:|---:|---:|']
    for split, ds in report['datasets'].items():
        for key, m in ds['modes'].items():
            lines.append(f"| {split} | {key} | {m['dung_toan_bo_6_truong']} | {m['khop_toan_bo_6_truong_pct']:.3f} | {m['latency']['mean_ms']:.2f}/{m['latency']['p95_ms']:.2f} | {m['stages']['beam_six_fields']} |")
    lines += ['', 'Không train/tune thêm, không đọc test cuối. Ranker đúng checkpoint. Từ điển train và bộ bảo vệ đường giống nhau ở các nhánh sửa. Luật không có span model nên bộ bảo vệ span không tác động.',
              'Oracle beam là hậu kiểm với nhãn, chưa áp dụng cơ chế từ chối mơ hồ của output cuối. Không dùng oracle để chọn output.', '']
    (OUT / 'BAO_CAO.md').write_text('\n'.join(lines), encoding='utf-8')


if __name__ == '__main__':
    run()
