"""Fine-tune GPU Colab từ snapshot, có resume theo epoch; không đọc test."""

import argparse
import json
import math
import random
import shutil
import time
from pathlib import Path

import torch
from torch.nn import functional as F

from src.videberta import REPO_ID, REVISION, ViDebertaCharCRF, load_tokenizer, encode_text, save_model
from src.char_cnn import TAGS
from danh_gia.du_lieu_crf import doc_jsonl
from danh_gia.huan_luyen_char import make_batch, save_json
from danh_gia.chay_ban_thu import digest


def pack_batch(rows, vocab, pad_id):
    chars, char_mask, allowed = make_batch(rows, vocab)
    length = max(len(r['encoding']['input_ids']) for r in rows)
    ids = torch.full((len(rows), length), pad_id, dtype=torch.long)
    attention = torch.zeros_like(ids)
    pieces = torch.zeros_like(chars)
    for i, rec in enumerate(rows):
        e = rec['encoding']
        n = len(e['input_ids'])
        ids[i, :n] = torch.tensor(e['input_ids'])
        attention[i, :n] = 1
        pieces[i, :len(rec['nfc'])] = torch.tensor(e['piece_for_char'])
    return ids, attention, chars, pieces, char_mask, allowed


def validate_input(data_root):
    from danh_gia.du_lieu_char import family_char
    rows = {s: doc_jsonl(data_root / 'data' / (s + '.jsonl')) for s in ('train_cnn', 'train_ranker', 'dev_goc', 'dev_kho')}
    a, b = rows['train_cnn'], rows['train_ranker']
    if {r['training_group'] for r in a} & {r['training_group'] for r in b}:
        raise ValueError('CNN/ranker trùng nhóm')
    train_families = {family_char(r) for r in a + b}
    dev_families = {family_char(r) for s in ('dev_goc', 'dev_kho') for r in rows[s]}
    if train_families & dev_families:
        raise ValueError('Train/dev trùng họ che số nhà')
    manifest = json.loads((data_root / 'snapshot/sha256.json').read_text(encoding='utf-8'))
    for name, h in manifest.items():
        # Bundle chỉ kèm những file cần chạy; manifest con liệt kê đúng chúng.
        if digest(data_root / 'snapshot' / name) != h:
            raise ValueError('Snapshot khác checksum: ' + name)
    return rows


def train(args):
    if not torch.cuda.is_available():
        raise RuntimeError('Cần bật GPU trong Colab: Runtime → Change runtime type → GPU. Không tự chuyển sang train CPU.')
    if min(args.epochs, args.batch_size, args.gradient_accumulation) < 1:
        raise ValueError('epochs/batch/gradient-accumulation phải >= 1')
    rows = validate_input(args.data_root)
    if args.run_dir.exists() and not args.resume:
        raise FileExistsError('Run đã tồn tại; chọn tên mới hoặc bật --resume')
    if not args.run_dir.exists():
        args.run_dir.mkdir(parents=True)
        for name in ('data', 'snapshot'):
            shutil.copytree(args.data_root / name, args.run_dir / name)
    # Chặn resume bằng dữ liệu khác, kể cả khi ID/nhóm vẫn giống.
    input_sha = {s: digest(args.data_root / 'data' / (s + '.jsonl')) for s in rows}
    for s, h in input_sha.items():
        if digest(args.run_dir / 'data' / (s + '.jsonl')) != h:
            raise ValueError('Dữ liệu run khác bundle: ' + s)
    config = {'epochs': args.epochs, 'batch_size': args.batch_size, 'gradient_accumulation': args.gradient_accumulation,
              'encoder_lr': 2e-5, 'head_lr': 1e-3, 'seed': 20261029, 'repo_id': REPO_ID, 'revision': REVISION,
              'input_sha256': input_sha, 'loss': 'partial BIO CRF / length + 0.2 CE singleton'}
    resume_path = args.run_dir / 'resume.pt'
    config_path = args.run_dir / 'run_config.json'
    state = None
    if args.resume:
        if not config_path.exists() or json.loads(config_path.read_text(encoding='utf-8')) != config:
            raise ValueError('Resume khác cấu hình hoặc dữ liệu; không đổi số vòng/batch giữa run')
        if resume_path.exists():
            state = torch.load(resume_path, map_location='cpu', weights_only=True)
            if state['config'] != config:
                raise ValueError('Checkpoint resume khác cấu hình')
        else:
            print('Chưa hoàn thành epoch nào; bắt đầu lại epoch 1 trên cùng dữ liệu.', flush=True)
    else:
        save_json(config_path, config)
    torch.manual_seed(config['seed'])
    torch.cuda.manual_seed_all(config['seed'])
    random.seed(config['seed'])
    torch.set_num_threads(2)
    rng = random.Random(config['seed'])
    from huggingface_hub import snapshot_download
    from transformers import DebertaV2Model
    # Checkpoint public, không cần nhập token Hugging Face.
    cache = Path(snapshot_download(REPO_ID, revision=REVISION, cache_dir=str(args.cache_dir),
                    allow_patterns=['config.json', 'pytorch_model.bin', 'tokenizer.json', 'tokenizer_config.json', 'special_tokens_map.json']))
    tokenizer = load_tokenizer(cache)
    vocab = {c: i + 2 for i, c in enumerate(sorted({c for r in rows['train_cnn'] for c in r['nfc']}))}
    model = ViDebertaCharCRF(DebertaV2Model.from_pretrained(str(cache), local_files_only=True), len(vocab) + 2)
    if state:
        model.load_state_dict(state['model_state'])
    model = model.to('cuda')
    head = [p for name, p in model.named_parameters() if not name.startswith('encoder.')]
    optimizer = torch.optim.AdamW([{'params': model.encoder.parameters(), 'lr': config['encoder_lr']},
                                   {'params': head, 'lr': config['head_lr']}], weight_decay=.01)
    prep_start = time.perf_counter()
    train_rows = rows['train_cnn']
    for rec in train_rows:
        rec['encoding'] = encode_text(rec['nfc'], tokenizer)
    ordered = sorted(train_rows, key=lambda r: len(r['nfc']))
    batches = [pack_batch(ordered[i:i + args.batch_size], vocab, tokenizer.pad_token_id)
               for i in range(0, len(ordered), args.batch_size)]
    total_updates = args.epochs * math.ceil(len(batches) / args.gradient_accumulation)
    warmup = max(1, int(total_updates * .1))
    def lr_factor(step):
        return (step + 1) / warmup if step < warmup else max(0., (total_updates - step) / max(1, total_updates - warmup))
    scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lr_factor)
    scaler = torch.amp.GradScaler('cuda')
    history, completed_epoch = [], 0
    if state:
        optimizer.load_state_dict(state['optimizer'])
        scheduler.load_state_dict(state['scheduler'])
        scaler.load_state_dict(state['scaler'])
        history, completed_epoch = state['history'], state['completed_epoch']
        torch.set_rng_state(state['torch_rng'])
        torch.cuda.set_rng_state_all(state['cuda_rng'])
        rng.setstate(state['batch_rng'])
    for epoch in range(completed_epoch + 1, args.epochs + 1):
        # Trộn index từ thứ tự gốc; resume cho cùng thứ tự với chạy liên tục.
        order = list(range(len(batches)))
        rng.shuffle(order)
        model.train()
        optimizer.zero_grad(set_to_none=True)
        start, loss_sum, examples = time.perf_counter(), 0., 0
        for position, batch_index in enumerate(order):
            ids, attention, chars, pieces, mask, allowed = [x.to('cuda') for x in batches[batch_index]]
            with torch.autocast('cuda', dtype=torch.float16):
                emissions = model(ids, attention, chars, pieces, mask)
            logits = emissions.float()
            loss = model.crf.loss(logits, mask, allowed)
            singleton = allowed.sum(-1).eq(1) & mask
            if singleton.any():
                loss = loss + .2 * F.cross_entropy(logits[singleton], allowed[singleton].long().argmax(-1))
            if not torch.isfinite(loss):
                raise RuntimeError('Loss NaN/Inf; dừng, không bỏ mẫu')
            group_start = (position // args.gradient_accumulation) * args.gradient_accumulation
            group_size = min(args.gradient_accumulation, len(order) - group_start)
            scaler.scale(loss / group_size).backward()
            if (position + 1) % args.gradient_accumulation == 0 or position + 1 == len(order):
                scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.)
                previous_scale = scaler.get_scale()
                scaler.step(optimizer)
                scaler.update()
                if scaler.get_scale() >= previous_scale:
                    scheduler.step()
                optimizer.zero_grad(set_to_none=True)
            loss_sum += loss.item() * ids.size(0)
            examples += ids.size(0)
            if position == 9 or (position + 1) % 100 == 0:
                elapsed = time.perf_counter() - start
                print(json.dumps({'epoch': epoch, 'batch': position + 1, 'batches': len(order),
                                  'loss': loss_sum / examples, 'epoch_eta_seconds': elapsed / (position + 1) * (len(order) - position - 1)}), flush=True)
        torch.cuda.synchronize()
        history.append({'epoch': epoch, 'loss': loss_sum / examples, 'seconds': time.perf_counter() - start})
        save_model(model, tokenizer, vocab, args.run_dir / 'model', epoch)
        state = {'config': config, 'completed_epoch': epoch, 'optimizer': optimizer.state_dict(),
                 'scheduler': scheduler.state_dict(), 'scaler': scaler.state_dict(), 'history': history,
                 'torch_rng': torch.get_rng_state(), 'cuda_rng': torch.cuda.get_rng_state_all(), 'batch_rng': rng.getstate()}
        # Resume chứa cả weights để không phụ thuộc hai file được cập nhật cùng lúc.
        state['model_state'] = {k: v.detach().cpu() for k, v in model.state_dict().items()}
        temporary = args.run_dir / 'resume.tmp'
        torch.save(state, temporary)
        temporary.replace(resume_path)
        save_json(args.run_dir / 'training.json', {'config': config, 'history': history, 'completed_epoch': epoch,
                   'training_complete': epoch == args.epochs, 'device': torch.cuda.get_device_name(),
                   'parameters': sum(p.numel() for p in model.parameters()), 'samples': len(train_rows),
                   'preprocessing_seconds': time.perf_counter() - prep_start if epoch == 1 else None,
                   'segmentation_fallback_train_rows': sum(r['encoding']['segmentation_fallback'] for r in train_rows),
                   'peak_gpu_allocated_mib': torch.cuda.max_memory_allocated() / 2**20,
                   'torch_version': str(torch.__version__), 'dev_used_to_fit_or_select_checkpoint': False})
        print(json.dumps(history[-1]), flush=True)
        del state
        state = None


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--data-root', type=Path, default=Path('bundle_data'))
    p.add_argument('--run-dir', type=Path, required=True)
    p.add_argument('--cache-dir', type=Path, default=Path('/content/hf_cache'))
    p.add_argument('--epochs', type=int, default=5)
    p.add_argument('--batch-size', type=int, default=8)
    p.add_argument('--gradient-accumulation', type=int, default=2)
    p.add_argument('--resume', action='store_true')
    train(p.parse_args())


if __name__ == '__main__':
    main()
