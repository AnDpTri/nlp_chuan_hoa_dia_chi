"""Dựng run dir train CNN v3: dữ liệu v2 gốc + các dòng agy đã qua kiem_train.py.
Dùng: python chuan_bi.py <run_dir>  """
import json, shutil, sys
from pathlib import Path

import duong_dan as dd  # gốc repo, CODE_ROOT vào sys.path
from src.char_cnn import TAG_ID, nfc_offsets

V2 = dd.MO_HINH / 'char_v2_01'
DAT = dd.BO_TRAIN_DAT


def record(x):
    text = x['text']
    normalized, offsets = nfc_offsets(text)
    starts = {a: i for i, (a, _) in enumerate(offsets)}
    ends = {b: i + 1 for i, (_, b) in enumerate(offsets)}
    spans = []
    for role, a, b in x['spans']:
        if a not in starts or b not in ends:
            raise ValueError('offset')
        spans.append((role, starts[a], ends[b]))
    # Dữ liệu tổng hợp có nhãn đầy đủ: ngoài span chắc chắn là O.
    allowed = [[0] for _ in normalized]
    used = set()
    for role, a, b in spans:
        for i in range(a, b):
            if i in used: raise ValueError('chong')
            used.add(i)
            allowed[i] = [TAG_ID[('B-' if i == a else 'I-') + role]]
    return {'id': x['id'], 'text': text, 'nfc': normalized, 'spans': spans, 'detail_spans_raw': [],
            'allowed': allowed, 'admin_alignment': 'tong_hop_agy_nhan_day_du', 'ref': {'id': x['id']}}


def main(run_dir, lap_goc='1'):
    run = Path(run_dir); (run / 'data').mkdir(parents=True, exist_ok=False)
    shutil.copytree(V2 / 'snapshot', run / 'snapshot')
    for f in ('train_ranker.jsonl', 'dev_goc.jsonl', 'dev_kho.jsonl'):
        shutil.copy2(V2 / 'data' / f, run / 'data' / f)
    goc = (V2 / 'data' / 'train_cnn.jsonl').read_text(encoding='utf-8').splitlines()
    them, loi = [], 0
    for p in sorted(DAT.glob('goi_*.jsonl')):
        for ln in p.read_text(encoding='utf-8').splitlines():
            try:
                them.append(json.dumps(record(json.loads(ln)), ensure_ascii=False))
            except ValueError:
                loi += 1
    # Lặp dữ liệu thật gốc để mô hình không quên kiểu số nhà thật mà dữ liệu sinh không có.
    (run / 'data' / 'train_cnn.jsonl').write_text('\n'.join(goc * int(lap_goc) + them) + '\n', encoding='utf-8', newline='\n')
    info = {'goc_v2': len(goc), 'lap_goc': int(lap_goc), 'tong_hop_agy': len(them), 'loai_khi_chuyen': loi}
    (run / 'data' / 'nguon.json').write_text(json.dumps(info, ensure_ascii=False), encoding='utf-8')
    print(info)


if __name__ == '__main__':
    main(*sys.argv[1:3])
