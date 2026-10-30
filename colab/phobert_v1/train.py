"""PhoBERT-base-v2 partial-label token classifier. Run in Colab GPU, NEVER reads test.
Selection metric: only strong-label accuracy of dev_goc, dev_kho is final report only.
"""
import argparse
import hashlib
import json
import os
import random
import time
from pathlib import Path

from check_data import TAGS, inspect, sha256

MODEL_ID = "vinai/phobert-base-v2"
MODEL_REVISION = "86cd7fd"  # immutable Hugging Face commit identifier
MAX_LEN = 256
LABELS = len(TAGS)


def write_json(path, payload):
    path = Path(path)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def segment_with_map(raw):
    from pyvi import ViTokenizer
    seg = ViTokenizer.tokenize(raw)
    mapping, pos = [], 0
    for ch in seg:
        if ch.isspace() or (ch == "_" and (pos >= len(raw) or raw[pos] != "_")):
            start = pos
            while pos < len(raw) and raw[pos].isspace():
                pos += 1
            if ch == "_" and start == pos:
                raise ValueError("Invalid inserted underscore alignment")
            mapping.append((start, pos))
            continue
        while pos < len(raw) and raw[pos].isspace():
            pos += 1
        if pos >= len(raw) or ch != raw[pos]:
            raise ValueError("PyVi changed content: raw/segmented text cannot align")
        mapping.append((pos, pos + 1))
        pos += 1
    if raw[pos:].strip():
        raise ValueError("PyVi lost source suffix")
    assert len(mapping) == len(seg)
    return seg, mapping


def role(label_id):
    return 0 if label_id == 0 else (label_id + 1) // 2


def remap_invalid_token_ids(ids, vocab_size, unk_token_id):
    """PhoBERT tokenizer may emit ids outside the pretrained encoder embedding."""
    if not 0 <= unk_token_id < vocab_size:
        raise ValueError("Tokenizer UNK id outside model vocab")
    if vocab_size < 1:
        raise ValueError("Invalid model vocab size")
    count = sum(not (0 <= x < vocab_size) for x in ids)
    return [x if 0 <= x < vocab_size else unk_token_id for x in ids], count


def encode_one(row, tokenizer, vocab_size):
    raw = row["nfc"]
    fallback = False
    try:
        segmented, mapping = segment_with_map(raw)
    except ValueError:
        # Existing project used the same no-loss fallback: no changed characters/offsets.
        # This is reported and subject to a strict <=1% fallback gate per split.
        segmented, mapping = raw, [(i, i + 1) for i in range(len(raw))]
        fallback = True
    encoded = tokenizer(segmented, add_special_tokens=True, truncation=False,
                        return_offsets_mapping=True)
    if len(encoded["input_ids"]) > MAX_LEN:
        raise ValueError("Input exceeds model 256-token limit: " + row["id"])
    model_ids, replaced = remap_invalid_token_ids(
        encoded["input_ids"], vocab_size, tokenizer.unk_token_id)
    allowed = []
    conflicted = 0
    strong = 0
    for a, b in encoded["offset_mapping"]:
        labels = [False] * LABELS
        if b > a:
            chars = sorted({j for m, n in mapping[a:b] for j in range(m, n)
                            if not raw[j].isspace()})
            if chars:
                common = set(role(k) for k in row["allowed"][chars[0]])
                for index in chars[1:]:
                    common &= set(role(k) for k in row["allowed"][index])
                if not common:
                    conflicted += 1  # no invented BIO label when tokenizer crosses entity boundary
                else:
                    first_mask = row["allowed"][chars[0]]
                    for r in common:
                        if r == 0:
                            labels[0] = True
                        else:
                            b_tag, i_tag = 2 * r - 1, 2 * r
                            # First subword of entity is B, later subwords are I.
                            # For ambiguous BIO both possibilities remain trainable.
                            if b_tag in first_mask:
                                labels[b_tag] = True
                            if i_tag in first_mask:
                                labels[i_tag] = True
            else:
                labels[0] = True
        allowed.append(labels)
        strong += int(sum(labels) == 1)
    assert len(allowed) == len(encoded["input_ids"])
    return {"ids": model_ids, "allowed": allowed, "conflicts": conflicted,
            "strong": strong, "source_id": row["id"], "segmented": segmented,
            "segmentation_fallback": fallback, "replaced_oov_tokens": replaced}


def load_encoded(path, tokenizer, vocab_size, official_slow=None):
    data, total_conflicts, total_labeled, fallback_count = [], 0, 0, 0
    replaced_oov, oov_rows, slow_verified = 0, 0, 0
    with Path(path).open(encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            row = json.loads(line)
            item = encode_one(row, tokenizer, vocab_size)
            if official_slow is not None:
                official_ids = official_slow.encode(item["segmented"])
                if item["ids"] != official_ids:
                    raise ValueError(
                        f"PhoBERT fast/slow tokenizer mismatch after safe UNK remap: {row['id']} ({path}:{line_no}); STOP")
                slow_verified += 1
            data.append(item)
            replaced_oov += item["replaced_oov_tokens"]
            oov_rows += bool(item["replaced_oov_tokens"])
            total_conflicts += item["conflicts"]
            total_labeled += len(item["ids"])
            fallback_count += int(item["segmentation_fallback"])
    assert data, "Empty split"
    if fallback_count / len(data) > 0.01:
        raise ValueError(f"PyVi segmentation fallback {fallback_count}/{len(data)} >1%; STOP")
    if replaced_oov / total_labeled > 0.01 or oov_rows / len(data) > 0.02:
        raise ValueError(f"PhoBERT out-of-range tokenizer ids too frequent: {replaced_oov} tokens, {oov_rows} rows; STOP")
    if any(min(x["ids"]) < 0 or max(x["ids"]) >= vocab_size for x in data):
        raise ValueError("Embedding token id out of bounds after remap; STOP")
    # Treat alignment errors as a hard blocker, not as an excuse to train corrupted labels.
    ratio = total_conflicts / total_labeled
    if ratio > 0.01:
        raise ValueError(f"Cross-entity subword boundary conflict rate {ratio:.2%} >1%; STOP")
    return data, {"rows": len(data), "conflicted_subwords": total_conflicts,
                  "total_subwords": total_labeled, "conflict_rate": ratio,
                  "segmentation_fallback_rows": fallback_count,
                  "oov_tokens_replaced_with_unk": replaced_oov,
                  "oov_rows": oov_rows, "model_vocab_size": vocab_size,
                  "official_slow_verified_rows": slow_verified,
                  "strong_subwords": sum(x["strong"] for x in data)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--epochs", type=int, default=6)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--grad-accum", type=int, default=2)
    parser.add_argument("--seed", type=int, default=20261030)
    parser.add_argument("--lr", type=float, default=2e-5)
    parser.add_argument("--patience", type=int, default=2)
    parser.add_argument("--smoke", action="store_true",
                        help="Non-scoring plumbing test: 8 train, 4 dev examples; separate output folder")
    args = parser.parse_args()
    if args.out_dir.exists():
        parser.error("Output directory exists; choose a new run name to avoid overwriting")
    assert 1 <= args.epochs <= 20 and 1 <= args.batch_size <= 64
    assert 1 <= args.grad_accum <= 32 and args.patience >= 1
    integrity = inspect(args.data_dir, args.manifest)
    import numpy as np
    import torch
    from torch.utils.data import DataLoader
    from transformers import AutoConfig, AutoTokenizer, PreTrainedTokenizerFast, AutoModelForTokenClassification, get_linear_schedule_with_warmup
    from huggingface_hub import hf_hub_download
    if not torch.cuda.is_available():
        raise RuntimeError("NO CUDA: Colab Runtime > Change runtime type > GPU. No CPU training by mistake.")
    device = torch.device("cuda")
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    torch.cuda.manual_seed_all(args.seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    # Model advertises PhobertTokenizer (slow). Explicit tokenizer.json guarantees
    # offset_mapping availability, but must be cross-checked against slow official BPE.
    fast_json = hf_hub_download(repo_id=MODEL_ID, filename="tokenizer.json", revision=MODEL_REVISION)
    tokenizer = PreTrainedTokenizerFast(
        tokenizer_file=fast_json, bos_token="<s>", eos_token="</s>",
        unk_token="<unk>", sep_token="</s>", cls_token="<s>",
        pad_token="<pad>", mask_token="<mask>")
    if not tokenizer.is_fast:
        raise RuntimeError("Fast PhoBERT tokenizer with offsets is mandatory. STOP.")
    slow = AutoTokenizer.from_pretrained(MODEL_ID, use_fast=False, revision=MODEL_REVISION)
    examples = ["Tôi là sinh_viên .", "Số 85B Đường Nguyễn_Văn_Linh , Cần_Thơ .",
                "d. le loi , phuong an khanh", "12/5 phố Hàng_Bông , Hà_Nội"]
    for phrase in examples:
        if tokenizer.encode(phrase) != slow.encode(phrase):
            raise RuntimeError("Fast/slow PhoBERT ID mismatch; MUST fix tokenizer before training: " + phrase)
    # Full-split token-id validation even in smoke; never hide a rare OOV behind eight rows.
    cfg = AutoConfig.from_pretrained(MODEL_ID, revision=MODEL_REVISION)
    model_vocab = cfg.vocab_size
    train, train_info = load_encoded(args.data_dir / "train_cnn.jsonl", tokenizer, model_vocab, slow)
    dev, dev_info = load_encoded(args.data_dir / "dev_goc.jsonl", tokenizer, model_vocab, slow)
    # dev_kho is checked here but evaluated exactly once after selecting best checkpoint.
    hard, hard_info = load_encoded(args.data_dir / "dev_kho.jsonl", tokenizer, model_vocab, slow)
    if args.smoke:
        oov_example = next((x for x in train if x["replaced_oov_tokens"]), None)
        if not oov_example:
            raise ValueError("Smoke OOV coverage missing; STOP")
        train = train[:7] + [oov_example]  # exercise the previously failing rare vocabulary case
        dev, hard = dev[:4], hard[:4]
    max_tokens = max(len(x["ids"]) for x in train + dev + hard)
    def collate(rows):
        length = max(len(row["ids"]) for row in rows)
        ids = torch.full((len(rows), length), tokenizer.pad_token_id, dtype=torch.long)
        mask = torch.zeros((len(rows), length), dtype=torch.long)
        allowed = torch.zeros((len(rows), length, LABELS), dtype=torch.bool)
        for i, row in enumerate(rows):
            n = len(row["ids"])
            ids[i, :n] = torch.tensor(row["ids"])
            mask[i, :n] = 1
            allowed[i, :n] = torch.tensor(row["allowed"], dtype=torch.bool)
        if ids.min().item() < 0 or ids.max().item() >= model_vocab:
            raise ValueError("Unsafe token ids blocked before CUDA")
        return ids, mask, allowed
    g = torch.Generator().manual_seed(args.seed)
    train_loader = DataLoader(train, batch_size=args.batch_size, shuffle=True, collate_fn=collate, generator=g)
    dev_loader = DataLoader(dev, batch_size=args.batch_size, shuffle=False, collate_fn=collate)
    model = AutoModelForTokenClassification.from_pretrained(
        MODEL_ID, revision=MODEL_REVISION, num_labels=LABELS,
        id2label={i: t for i, t in enumerate(TAGS)},
        label2id={t: i for i, t in enumerate(TAGS)},
        ignore_mismatched_sizes=True).to(device)
    if model.get_input_embeddings().num_embeddings != model_vocab:
        raise ValueError("Loaded PhoBERT embedding size differs from preflight config; STOP")
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=0.01)
    steps = (len(train_loader) + args.grad_accum - 1) // args.grad_accum * args.epochs
    sched = get_linear_schedule_with_warmup(opt, num_warmup_steps=max(1, steps // 10),
                                            num_training_steps=steps)
    scaler = torch.amp.GradScaler("cuda")
    def loss_fn(logits, allowed):
        usable = allowed.any(dim=-1)
        assert usable.any(), "All subword labels missing"
        logp = torch.nn.functional.log_softmax(logits.float(), dim=-1)
        token_loss = -torch.logsumexp(logp.masked_fill(~allowed, -1e4), dim=-1)
        return token_loss.masked_select(usable).mean()
    @torch.no_grad()
    def evaluate(loader):
        model.eval()
        total_loss, steps_eval, strong_ok, strong_n, partial_ok, partial_n = 0., 0, 0, 0, 0, 0
        for ids, mask, allowed in loader:
            ids, mask, allowed = ids.to(device), mask.to(device), allowed.to(device)
            output = model(input_ids=ids, attention_mask=mask).logits
            total_loss += float(loss_fn(output, allowed))
            steps_eval += 1
            pred = output.argmax(-1)
            used = allowed.any(-1)
            strong = allowed.sum(-1) == 1
            accepted = allowed.gather(2, pred.unsqueeze(-1)).squeeze(-1)
            strong_ok += int((accepted & strong).sum())
            strong_n += int(strong.sum())
            partial_ok += int((accepted & used).sum())
            partial_n += int(used.sum())
        return {"loss": total_loss / max(1, steps_eval),
                "strong_acc": strong_ok / max(1, strong_n),
                "partial_consistency": partial_ok / max(1, partial_n),
                "strong_tokens": strong_n, "trainable_tokens": partial_n}
    args.out_dir.mkdir(parents=True, exist_ok=False)
    write_json(args.out_dir / "preflight.json",
               {"status": "PASS", "model": MODEL_ID, "revision": MODEL_REVISION, "tags": TAGS,
                "train": train_info, "dev_goc": dev_info, "dev_kho": hard_info, "integrity": integrity,
                "config": vars(args) | {"data_dir": str(args.data_dir),
                                        "manifest": str(args.manifest),
                                        "out_dir": str(args.out_dir)},
                "torch": torch.__version__, "transformers": __import__("transformers").__version__,
                "gpu": torch.cuda.get_device_name(0)})
    print("PREFLIGHT_TOKENIZER_PASS; training batches:", len(train_loader), flush=True)
    best_score = -1.
    best_epoch = 0
    no_improve = 0
    history = []
    started = time.monotonic()
    try:
        for epoch in range(1, args.epochs + 1):
            model.train()
            opt.zero_grad(set_to_none=True)
            epoch_losses = []
            for i, (ids, mask, allowed) in enumerate(train_loader, 1):
                ids, mask, allowed = ids.to(device), mask.to(device), allowed.to(device)
                with torch.autocast("cuda", dtype=torch.float16):
                    logits = model(input_ids=ids, attention_mask=mask).logits
                    loss = loss_fn(logits, allowed)
                scaler.scale(loss / args.grad_accum).backward()
                epoch_losses.append(float(loss.detach()))
                if i % args.grad_accum == 0 or i == len(train_loader):
                    scaler.unscale_(opt)
                    torch.nn.utils.clip_grad_norm_(model.parameters(), 1.)
                    scaler.step(opt)
                    scaler.update()
                    sched.step()
                    opt.zero_grad(set_to_none=True)
                if i % 40 == 0:
                    print(f"epoch={epoch} batch={i}/{len(train_loader)} loss={sum(epoch_losses[-40:])/len(epoch_losses[-40:]):.4f}", flush=True)
            metrics = evaluate(dev_loader)
            improved = metrics["strong_acc"] > best_score + 1e-5
            if improved:
                best_score = metrics["strong_acc"]
                best_epoch = epoch
                no_improve = 0
                # Write checkpoint atomically in a fresh run directory; never overwrite another run.
                model.save_pretrained(args.out_dir / "best_model", safe_serialization=True)
                tokenizer.save_pretrained(args.out_dir / "best_model")
                # Inference MUST apply the exact same model-vocab-safe ID policy.
                write_json(args.out_dir / "best_model" / "token_id_policy.json", {
                    "model_id": MODEL_ID, "revision": MODEL_REVISION,
                    "model_embedding_vocab_size": model_vocab,
                    "tokenizer_unk_token_id": tokenizer.unk_token_id,
                    "out_of_range_action": "replace_with_unk",
                    "all_train_dev_official_slow_token_ids_verified": True,
                    "oov_tokens_in_train": train_info["oov_tokens_replaced_with_unk"]})
            else:
                no_improve += 1
            record = {"epoch": epoch, "train_loss": sum(epoch_losses) / len(epoch_losses),
                      "dev_goc": metrics, "best_epoch": best_epoch,
                      "best_strong_acc": best_score, "seconds_elapsed": round(time.monotonic() - started, 1),
                      "gpu_max_allocated_mib": round(torch.cuda.max_memory_allocated() / 1048576, 1)}
            history.append(record)
            write_json(args.out_dir / "history.json", history)
            write_json(args.out_dir / "status.json", {"state": "TRAINING", **record})
            print("EPOCH_DONE", json.dumps(record, ensure_ascii=False), flush=True)
            if no_improve >= args.patience:
                print("EARLY_STOP", flush=True)
                break
        # Reload frozen best; dev_kho is evaluated only at the end, once.
        from transformers import AutoModelForTokenClassification as Model
        model = Model.from_pretrained(args.out_dir / "best_model").to(device)
        hard_result = evaluate(DataLoader(hard, batch_size=args.batch_size, collate_fn=collate))
        summary = {"state": "COMPLETE", "best_epoch": best_epoch, "dev_goc_best_strong_acc": best_score,
                   "dev_kho": hard_result, "dev_kho_integrity": hard_info,
                   "elapsed_seconds": round(time.monotonic() - started, 1),
                   "note": "Token BIO scores on weak labels; NOT end-to-end address accuracy, NOT gold."}
        write_json(args.out_dir / "summary.json", summary)
        write_json(args.out_dir / "status.json", summary)
        print("TRAINING_COMPLETE", json.dumps(summary, ensure_ascii=False), flush=True)
    except Exception as exc:
        write_json(args.out_dir / "status.json", {"state": "FAILED", "error": repr(exc)})
        raise


if __name__ == "__main__":
    main()
