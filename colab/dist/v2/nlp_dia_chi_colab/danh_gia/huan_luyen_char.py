"""Train CNN/CRF CPU và ranker từ các họ train tách biệt; không đọc test.

python -m danh_gia.huan_luyen_char --run-dir mo_hinh/thu_nghiem/char_v1_01
"""

import argparse
import hashlib
import json
import random
import shutil
import time
from collections import Counter
from pathlib import Path

import torch
from torch.nn import functional as F

from src.char_cnn import BoTachCharCNN, CharCNNCRF, TAGS
from src.chuan_hoa import BoChuanHoa
from src.chuyen_doi import sang_cay_moi
from src.danh_muc import DanhMuc
from src.xep_hang import FEATURES, dac_trung_gia_thuyet
from .chay_ban_thu import ROOT, CORE, digest, memory, norm
from .du_lieu_char import prepare
from .du_lieu_crf import doc_jsonl, ghi_jsonl


def save_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8', newline='\n')


def freeze(run_dir):
    old = ROOT / 'mo_hinh/thu_nghiem/crf_v1_01'
    source = old / 'du_lieu_dong_bang'
    snap = run_dir / 'snapshot'
    snap.mkdir()
    for name in ('train.csv', 'dev.csv', 'train_bo_sung.csv', 'dev_kho.csv', 'train_spans.jsonl', 'dev_spans.jsonl'):
        shutil.copy2(source / name, snap / name)
    dm = DanhMuc()
    (snap / 'clean').mkdir()
    for name in dm.ma_bam:
        shutil.copy2(ROOT / 'data/clean' / name, snap / 'clean' / name)
    shutil.copytree(old / 'du_lieu_crf', snap / 'prepared_crf')
    save_json(snap / 'sha256.json', {p.relative_to(snap).as_posix(): digest(p) for p in snap.rglob('*') if p.is_file()})
    return snap


def make_batch(records, vocab):
    n, length = len(records), max(len(r['nfc']) for r in records)
    ids = torch.zeros(n, length, dtype=torch.long)
    mask = torch.zeros(n, length, dtype=torch.bool)
    allowed = torch.ones(n, length, len(TAGS), dtype=torch.bool)
    for i, rec in enumerate(records):
        l = len(rec['nfc'])
        ids[i, :l] = torch.tensor([vocab.get(c, 1) for c in rec['nfc']])
        mask[i, :l] = True
        allowed[i, :l] = False
        for j, choices in enumerate(rec['allowed']):
            allowed[i, j, choices] = True
    return ids, mask, allowed


def train_cnn(run_dir, epochs=12, threads=2, batch_size=32):
    torch.set_num_threads(threads)
    torch.manual_seed(20261029)
    rng = random.Random(20261029)
    rows = doc_jsonl(run_dir / 'data/train_cnn.jsonl')
    if not rows or any(not r['nfc'] or len(r['nfc']) > 2048 for r in rows):
        raise ValueError('Train rỗng hoặc vượt giới hạn ký tự')
    vocab = {c: i + 2 for i, c in enumerate(sorted({c for r in rows for c in r['nfc']}))}
    config = {'embedding': 64, 'channels': 96, 'dilations': [1, 2, 4, 8, 16, 32], 'dropout': .15}
    model = CharCNNCRF(len(vocab) + 2, **config)
    optimizer = torch.optim.AdamW(model.parameters(), lr=.002, weight_decay=.0001)
    # Tensor hóa một lần, tránh tạo mask nhãn trong vòng train.
    order = sorted(rows, key=lambda r: len(r['nfc']))
    batches = [make_batch(order[i:i + batch_size], vocab) for i in range(0, len(order), batch_size)]
    history = []
    start = time.perf_counter()
    for epoch in range(1, epochs + 1):
        model.train()
        rng.shuffle(batches)
        loss_sum, count = 0., 0
        t0 = time.perf_counter()
        for ids, mask, allowed in batches:
            optimizer.zero_grad(set_to_none=True)
            emissions = model(ids, mask)
            loss = model.crf.loss(emissions, mask, allowed)
            singleton = allowed.sum(-1).eq(1) & mask
            aux = F.cross_entropy(emissions[singleton], allowed[singleton].long().argmax(-1))
            loss = loss + .2 * aux
            if not torch.isfinite(loss):
                raise RuntimeError('Loss NaN/Inf')
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 5.)
            optimizer.step()
            loss_sum += loss.item() * ids.size(0)
            count += ids.size(0)
        entry = {'epoch': epoch, 'loss': loss_sum / count, 'seconds': time.perf_counter() - t0}
        history.append(entry)
        print(json.dumps(entry), flush=True)
        checkpoint = {'format': 1, 'tags': TAGS, 'vocab': vocab, 'config': config,
                      'state_dict': model.state_dict(), 'epoch': epoch}
        torch.save(checkpoint, run_dir / 'char_cnn.pt')
        save_json(run_dir / 'training.json', {'device': 'cpu', 'torch_threads': threads,
                  'torch_version': str(torch.__version__), 'samples': len(rows), 'batch_size': batch_size,
                  'parameters': sum(p.numel() for p in model.parameters()), 'seed': 20261029,
                  'epochs_requested': epochs, 'history': history, 'train_seconds': time.perf_counter() - start,
                  'objective': 'partial BIO CRF NLL/length + 0.2 CE trên ký tự có nhãn đơn',
                  'validation_used_for_fitting': False, 'memory': memory()})
    return history


def train_ranker(run_dir, extractor=None):
    import lightgbm as lgb
    import numpy as np
    start = time.perf_counter()
    dm = DanhMuc(run_dir / 'snapshot/clean')
    if extractor is None:
        extractor = BoTachCharCNN(run_dir / 'char_cnn.pt', threads=1)
    normalizer = BoChuanHoa(danh_muc=dm, bo_tach=extractor)
    records = doc_jsonl(run_dir / 'data/train_ranker.jsonl')
    features, labels, groups, audit = [], [], [], []
    excluded = Counter()
    for rec in records:
        if not rec['canonical_usable']:
            excluded['canonical_usable_false'] += 1
            continue
        ref = rec['ref']
        tokens, candidates, context, items = normalizer.tao_gia_thuyet(rec['text'])
        words = [t.chu for t in tokens]
        relevance, vectors = [], []
        for item in items:
            _, path, detail, *_ = item
            ward, prov, _ = sang_cay_moi(path, detail, dm)
            same_admin = ward == ref['ma_xa'] and prov == ref['ma_tinh']
            same_detail = all(norm(detail[f]) == norm(ref[f]) for f in CORE[:4])
            relevance.append(3 if same_admin and same_detail else 2 if same_admin else 0)
            vectors.append(dac_trung_gia_thuyet(item, words, candidates, dm, context))
        # Không bắt mô hình chọn một âm khi ứng viên đúng không tồn tại.
        if not relevance or max(relevance) == 0 or len(set(relevance)) == 1:
            excluded['khong_co_cap_duong_am'] += 1
            continue
        features.extend(vectors)
        labels.extend(relevance)
        groups.append(len(vectors))
        audit.append({'id': rec['id'], 'group': rec['training_group'], 'relevance': relevance})
    if not groups:
        raise ValueError('Không có nhóm đủ điều kiện train ranker')
    params = {'objective': 'lambdarank', 'metric': 'ndcg', 'num_leaves': 15, 'max_depth': 4,
              'learning_rate': .05, 'min_data_in_leaf': 20, 'lambda_l2': 1.,
              'num_threads': 2, 'seed': 20261029, 'deterministic': True, 'force_col_wise': True,
              'verbosity': -1, 'label_gain': [0, 1, 3, 7]}
    dataset = lgb.Dataset(np.asarray(features), label=labels, group=groups, feature_name=FEATURES)
    model = lgb.train(params, dataset, num_boost_round=100)
    model.save_model(str(run_dir / 'ranker.txt'))
    save_json(run_dir / 'ranker.json', {'features': FEATURES, 'extractor_sha256': extractor.ma_bam,
              'catalogue_sha256': dm.ma_bam, 'close_margin': .05, 'margin_calibrated': False,
              'group_count': len(groups), 'hypotheses': len(labels), 'excluded': dict(excluded),
              'fit_seconds_including_features': time.perf_counter() - start, 'params': params,
              'boost_rounds': 100, 'lightgbm_version': lgb.__version__, 'heldout_dev_used_for_fit': False,
              'cnn_ranker_training_groups_disjoint': True,
              'feature_gain': dict(zip(FEATURES, model.feature_importance('gain').tolist()))})
    ghi_jsonl(run_dir / 'ranker_training_groups.jsonl', audit)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-dir', required=True, type=Path)
    parser.add_argument('--epochs', type=int, default=12)
    parser.add_argument('--threads', type=int, default=2)
    parser.add_argument('--batch-size', type=int, default=32)
    parser.add_argument('--stage', choices=['all', 'prepare', 'cnn', 'ranker'], default='all')
    args = parser.parse_args()
    if min(args.epochs, args.threads, args.batch_size) < 1:
        parser.error('epochs/threads/batch-size phải >= 1')
    run_dir = args.run_dir.resolve()
    if args.stage in ('all', 'prepare'):
        run_dir.mkdir(parents=True, exist_ok=False)
        snap = freeze(run_dir)
        summary = prepare(snap, snap / 'prepared_crf', run_dir / 'data')
        print(json.dumps(summary, ensure_ascii=False), flush=True)
        save_json(run_dir / 'code_sha256_prepare.json', {str(p.relative_to(ROOT)): digest(p) for p in
                  [ROOT / 'src/char_cnn.py', ROOT / 'danh_gia/du_lieu_char.py', Path(__file__)]})
    if args.stage in ('all', 'cnn'):
        train_cnn(run_dir, args.epochs, args.threads, args.batch_size)
    if args.stage in ('all', 'ranker'):
        train_ranker(run_dir)


if __name__ == '__main__':
    main()
