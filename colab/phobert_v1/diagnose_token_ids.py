"""Check every token ID and label mask before sending to CUDA; no test data."""
from pathlib import Path
from collections import Counter
import sys
from huggingface_hub import hf_hub_download
from transformers import AutoConfig, AutoTokenizer, PreTrainedTokenizerFast
from train import load_encoded, MODEL_ID, MODEL_REVISION, MAX_LEN

f = hf_hub_download(MODEL_ID, "tokenizer.json", revision=MODEL_REVISION, local_files_only=True)
t = PreTrainedTokenizerFast(tokenizer_file=f, bos_token="<s>", eos_token="</s>",
     unk_token="<unk>", sep_token="</s>", cls_token="<s>", pad_token="<pad>", mask_token="<mask>")
c = AutoConfig.from_pretrained(MODEL_ID, revision=MODEL_REVISION)
official = AutoTokenizer.from_pretrained(MODEL_ID, use_fast=False, revision=MODEL_REVISION)
print("vocab_config", c.vocab_size, "tokenizer_len", len(t), "specials",
      t.all_special_tokens, t.all_special_ids, flush=True)
root = Path("mo_hinh/thu_nghiem/char_v2_01/data")
for name in ("train_cnn", "dev_goc", "dev_kho"):
    data, info = load_encoded(root / (name + ".jsonl"), t, c.vocab_size, official)
    bad, max_id, lens, bad_masks = [], 0, [], []
    for x in data:
        maximum = max(x["ids"])
        if maximum >= c.vocab_size or min(x["ids"]) < 0:
            bad.append((x["source_id"], maximum, x["ids"]))
        max_id = max(max_id, maximum)
        lens.append(len(x["ids"]))
        if any(len(m) != 15 for m in x["allowed"]):
            bad_masks.append(x["source_id"])
    print(name, "n", len(data), "max_token_id", max_id, "max_seq_len", max(lens),
          "bad_token_rows", len(bad), "bad_masks", bad_masks[:5], "preflight", info,
          "first_bad", bad[:2], flush=True)
    if bad: sys.exit(3)
