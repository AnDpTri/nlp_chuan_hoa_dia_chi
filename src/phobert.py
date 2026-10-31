"""Bộ nhận diện PhoBERT-base-v2 fine-tuned cho chuẩn hóa địa chỉ Việt Nam."""

import hashlib
import json
import os
from pathlib import Path
from typing import List, Optional, Tuple

import torch
from transformers import AutoModelForTokenClassification, AutoTokenizer

from .char_cnn import LinearCRF
from .ngu_canh_neural import NguCanhChar
from .nhan import TAGS
from .tien_xu_ly import nfc_offsets

_GLOBAL_TOKENIZER = None
_GLOBAL_VOCAB_SIZE = None
_GLOBAL_UNK_TOKEN_ID = None


def segment_with_map(raw: str) -> Tuple[str, List[Tuple[int, int]], bool]:
    """Tách từ bằng PyVi tương thích với colab/phobert_v1/train.py.

    Trả về (segmented, mapping, fallback).
    Nếu PyVi thay đổi ký tự hoặc không khớp offset, fallback về (raw, [(i, i+1)...], True).
    """
    from pyvi import ViTokenizer
    try:
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
        return seg, mapping, False
    except ValueError:
        return raw, [(i, i + 1) for i in range(len(raw))], True


def _ensure_global_tokenizer(model_dir: Optional[str] = None):
    global _GLOBAL_TOKENIZER, _GLOBAL_VOCAB_SIZE, _GLOBAL_UNK_TOKEN_ID
    if _GLOBAL_TOKENIZER is None:
        if model_dir is None:
            model_dir = os.environ.get("PHOBERT_MODEL_DIR") or r"G:\My Drive\PhoBERT_Address_Colab_20261030_v2\runs\phobert_base_v2_20261030T060548404237Z\best_model"
        tok = AutoTokenizer.from_pretrained(model_dir)
        cfg_path = Path(model_dir) / "config.json"
        vocab_size = json.loads(cfg_path.read_text(encoding="utf-8"))["vocab_size"]
        _GLOBAL_TOKENIZER = tok
        _GLOBAL_VOCAB_SIZE = vocab_size
        _GLOBAL_UNK_TOKEN_ID = tok.unk_token_id


def encode_ids(text: str, max_len: Optional[int] = None, tokenizer=None,
               vocab_size: Optional[int] = None, unk_token_id: Optional[int] = None) -> List[int]:
    """Mã hóa văn bản thành danh sách subword ID đã remap ID >= vocab_size thành UNK."""
    if tokenizer is None:
        _ensure_global_tokenizer()
        tokenizer = _GLOBAL_TOKENIZER
        vocab_size = _GLOBAL_VOCAB_SIZE if vocab_size is None else vocab_size
        unk_token_id = _GLOBAL_UNK_TOKEN_ID if unk_token_id is None else unk_token_id
    elif vocab_size is None or unk_token_id is None:
        _ensure_global_tokenizer()
        vocab_size = _GLOBAL_VOCAB_SIZE if vocab_size is None else vocab_size
        unk_token_id = _GLOBAL_UNK_TOKEN_ID if unk_token_id is None else unk_token_id

    seg, _, _ = segment_with_map(text)
    encoded = tokenizer(seg, add_special_tokens=True, truncation=False)
    ids = encoded["input_ids"]
    if vocab_size is not None and unk_token_id is not None:
        ids = [unk_token_id if i >= vocab_size else i for i in ids]
    if max_len is not None and len(ids) > max_len:
        raise ValueError(f"Input exceeds model {max_len}-token limit: {len(ids)}")
    return ids


class BoTachPhoBERT:
    phien_ban = "phobert_base_v2_token_crf_v1"
    ten_mo_hinh = "phobert_base_v2"
    bao_ve_chi_tiet = False

    def __init__(self, model_dir: str, threads: int = 1, device: str = "cpu"):
        global _GLOBAL_TOKENIZER, _GLOBAL_VOCAB_SIZE, _GLOBAL_UNK_TOKEN_ID
        if threads < 1:
            raise ValueError("threads phải >= 1")
        torch.set_num_threads(threads)
        self.device = torch.device(device)
        folder = Path(model_dir)

        cfg_path = folder / "config.json"
        self.config_data = json.loads(cfg_path.read_text(encoding="utf-8"))
        self.vocab_size = self.config_data["vocab_size"]

        self.tokenizer = AutoTokenizer.from_pretrained(str(folder))
        self.unk_token_id = self.tokenizer.unk_token_id
        self.model = AutoModelForTokenClassification.from_pretrained(str(folder))
        self.model.to(self.device).eval()
        self.crf = LinearCRF()

        _GLOBAL_TOKENIZER = self.tokenizer
        _GLOBAL_VOCAB_SIZE = self.vocab_size
        _GLOBAL_UNK_TOKEN_ID = self.unk_token_id

        h = hashlib.sha256()
        for name in ("model.safetensors", "config.json", "tokenizer.json", "token_id_policy.json"):
            with (folder / name).open("rb") as f:
                for chunk in iter(lambda: f.read(1024 * 1024), b""):
                    h.update(chunk)
        self.ma_bam = h.hexdigest()

    def encode_ids(self, text: str, max_len: Optional[int] = None) -> List[int]:
        return encode_ids(text, max_len=max_len, tokenizer=self.tokenizer,
                          vocab_size=self.vocab_size, unk_token_id=self.unk_token_id)

    def chuan_bi_chuoi(self, raw: str) -> NguCanhChar:
        text, offsets = nfc_offsets(raw)
        if not text:
            ctx = NguCanhChar(raw, text, offsets, [], torch.empty(0, len(TAGS)))
            ctx.segmentation_fallback = False
            return ctx

        segmented, mapping, fallback = segment_with_map(text)
        encoding = self.tokenizer(segmented, return_offsets_mapping=True,
                                  add_special_tokens=True, truncation=False)
        ids = encoding["input_ids"]
        ids = [self.unk_token_id if i >= self.vocab_size else i for i in ids]

        chunk_limit = 256
        with torch.inference_mode():
            if len(ids) <= chunk_limit:
                logits = self.model(torch.tensor([ids], dtype=torch.long, device=self.device)).logits[0].float().cpu()
            else:
                chunks = []
                cur = 0
                while cur < len(ids):
                    end = min(cur + chunk_limit, len(ids))
                    chunk_ids = ids[cur:end]
                    out = self.model(torch.tensor([chunk_ids], dtype=torch.long, device=self.device)).logits[0].float().cpu()
                    chunks.append(out)
                    cur = end
                logits = torch.cat(chunks, dim=0)

        sub_lp = torch.log_softmax(logits, dim=-1)

        piece_for_char = [-1] * len(text)
        for index, (a, b) in enumerate(encoding["offset_mapping"]):
            if a == b:
                continue
            for x, y in mapping[a:b]:
                for j in range(x, y):
                    if j < len(text):
                        piece_for_char[j] = index

        first = next((i for i in piece_for_char if i >= 0), 0)
        prev = first
        for j, i in enumerate(piece_for_char):
            if i >= 0:
                prev = i
            else:
                piece_for_char[j] = prev

        char_lp = torch.full((len(text), len(TAGS)), -30.0)
        for idx in range(len(ids)):
            chars = [j for j, p in enumerate(piece_for_char) if p == idx]
            if not chars:
                continue
            non_space = [j for j in chars if not text[j].isspace()]
            first_j = non_space[0] if non_space else chars[0]
            lp = sub_lp[idx]
            for j in chars:
                if j == first_j:
                    char_lp[j] = torch.clamp(lp, min=-30.0, max=0.0)
                else:
                    clp = lp.clone()
                    for r in range(1, 8):
                        b_i, i_i = 2 * r - 1, 2 * r
                        clp[i_i] = torch.logaddexp(clp[b_i], clp[i_i])
                        clp[b_i] = -30.0
                    char_lp[j] = torch.clamp(clp, min=-30.0, max=0.0)

        tags = [TAGS[i] for i in self.crf.decode(char_lp)]
        ctx = NguCanhChar(raw, text, offsets, tags, char_lp)
        ctx.segmentation_fallback = fallback
        return ctx
