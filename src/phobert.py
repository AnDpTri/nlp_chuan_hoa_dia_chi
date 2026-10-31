"""PhoBERT-base-v2 adapter token classification; suy luận CPU offline."""

import hashlib
import json
from pathlib import Path

import torch
from transformers import AutoModelForTokenClassification, AutoTokenizer

from .char_cnn import LinearCRF
from .ngu_canh_neural import NguCanhChar
from .nhan import TAGS, TAG_ID
from .tien_xu_ly import nfc_offsets

_DEFAULT_TOKENIZER = None
_DEFAULT_VOCAB_SIZE = 64001
_DEFAULT_UNK_ID = 3


def _load_default_tokenizer(model_dir=None):
    global _DEFAULT_TOKENIZER, _DEFAULT_VOCAB_SIZE, _DEFAULT_UNK_ID
    if _DEFAULT_TOKENIZER is None:
        import os
        path = model_dir or os.environ.get(
            'PHOBERT_MODEL_DIR',
            r'G:\My Drive\PhoBERT_Address_Colab_20261030_v2\runs\phobert_base_v2_20261030T060548404237Z\best_model'
        )
        folder = Path(path)
        if folder.exists():
            _DEFAULT_TOKENIZER = AutoTokenizer.from_pretrained(str(folder))
            cfg_file = folder / 'config.json'
            if cfg_file.exists():
                cfg = json.loads(cfg_file.read_text(encoding='utf-8'))
                _DEFAULT_VOCAB_SIZE = cfg.get('vocab_size', 64001)
            _DEFAULT_UNK_ID = _DEFAULT_TOKENIZER.unk_token_id
    return _DEFAULT_TOKENIZER


def _train_segment_with_map(raw):
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


def segment_with_map(raw):
    try:
        segmented, mapping = _train_segment_with_map(raw)
        return segmented, mapping, False
    except ValueError:
        return raw, [(i, i + 1) for i in range(len(raw))], True


def encode_ids(text, max_len=None, tokenizer=None, vocab_size=None, unk_id=None):
    if tokenizer is None:
        tokenizer = _load_default_tokenizer()
    if vocab_size is None:
        vocab_size = _DEFAULT_VOCAB_SIZE
    if unk_id is None:
        unk_id = _DEFAULT_UNK_ID if _DEFAULT_UNK_ID is not None else (tokenizer.unk_token_id if tokenizer else 3)
    if tokenizer is None:
        raise ValueError("Chưa nạp được PhoBERT tokenizer")
    seg, mapping, fallback = segment_with_map(text)
    enc = tokenizer(seg, add_special_tokens=True, truncation=False)
    ids = [unk_id if i >= vocab_size else i for i in enc['input_ids']]
    if max_len is not None and len(ids) > max_len:
        raise ValueError(f"Văn bản vượt quá {max_len} subword ({len(ids)} > {max_len}); không cắt ngắn")
    return ids


class BoTachPhoBERT:
    phien_ban = 'phobert_base_v2_20261030'
    ten_mo_hinh = 'phobert_base_v2'
    bao_ve_chi_tiet = False

    def __init__(self, model_dir, threads=1, device='cpu'):
        if threads < 1:
            raise ValueError('threads phải >= 1')
        torch.set_num_threads(threads)
        folder = Path(model_dir)
        config_path = folder / 'config.json'
        if not config_path.exists():
            raise FileNotFoundError(f"Không tìm thấy config.json tại {folder}")
        self.config = json.loads(config_path.read_text(encoding='utf-8'))
        self.vocab_size = self.config['vocab_size']
        self.tokenizer = AutoTokenizer.from_pretrained(str(folder))
        self.model = AutoModelForTokenClassification.from_pretrained(str(folder))
        self.device = torch.device(device)
        self.model.to(self.device).eval()
        self.crf = LinearCRF()

        h = hashlib.sha256()
        for name in ('model.safetensors', 'config.json', 'tokenizer.json', 'token_id_policy.json'):
            file_p = folder / name
            with file_p.open('rb') as f:
                for chunk in iter(lambda: f.read(1024 * 1024), b''):
                    h.update(chunk)
        self.ma_bam = h.hexdigest()

        global _DEFAULT_TOKENIZER, _DEFAULT_VOCAB_SIZE, _DEFAULT_UNK_ID
        _DEFAULT_TOKENIZER = self.tokenizer
        _DEFAULT_VOCAB_SIZE = self.vocab_size
        _DEFAULT_UNK_ID = self.tokenizer.unk_token_id

    def encode_ids(self, text, max_len=None):
        return encode_ids(
            text,
            max_len=max_len,
            tokenizer=self.tokenizer,
            vocab_size=self.vocab_size,
            unk_id=self.tokenizer.unk_token_id
        )

    def chuan_bi_chuoi(self, raw):
        text, offsets = nfc_offsets(raw)
        if not text:
            ctx = NguCanhChar(raw, text, offsets, [], torch.empty(0, len(TAGS)))
            ctx.segmentation_fallback = False
            return ctx

        segmented, mapping, fallback = segment_with_map(text)
        encoding = self.tokenizer(segmented, return_offsets_mapping=True, truncation=False)
        input_ids = [self.tokenizer.unk_token_id if i >= self.vocab_size else i for i in encoding['input_ids']]

        piece_for_char = [-1] * len(text)
        for index, (a, b) in enumerate(encoding['offset_mapping']):
            if a == b:
                continue
            for x, y in mapping[a:b]:
                for j in range(x, y):
                    piece_for_char[j] = index
        first = next((i for i in piece_for_char if i >= 0), 0)
        previous = first
        for j, i in enumerate(piece_for_char):
            if i >= 0:
                previous = i
            else:
                piece_for_char[j] = previous

        seq_len = len(input_ids)
        with torch.inference_mode():
            if seq_len <= 256:
                ids_t = torch.tensor([input_ids], dtype=torch.long, device=self.device)
                logits = self.model(ids_t).logits[0]
            else:
                chunks = []
                for start in range(0, seq_len, 256):
                    end = min(start + 256, seq_len)
                    chunk_ids = input_ids[start:end]
                    ids_t = torch.tensor([chunk_ids], dtype=torch.long, device=self.device)
                    out = self.model(ids_t).logits[0]
                    chunks.append(out)
                logits = torch.cat(chunks, dim=0)

            subword_logp = torch.log_softmax(logits.float().cpu(), dim=-1)

            roles = ('so_nha', 'ngo_ngach_hem', 'thon_xom', 'duong', 'xa', 'huyen', 'tinh')
            b_ids = [TAG_ID['B-' + r] for r in roles]
            i_ids = [TAG_ID['I-' + r] for r in roles]

            char_logp = torch.zeros((len(text), len(TAGS)), dtype=torch.float32)
            for j in range(len(text)):
                p = piece_for_char[j]
                slp = subword_logp[p].clone()
                is_first = (j == 0 or piece_for_char[j] != piece_for_char[j - 1])
                if not is_first:
                    for b_idx, i_idx in zip(b_ids, i_ids):
                        slp[i_idx] = torch.logaddexp(slp[i_idx], slp[b_idx])
                        slp[b_idx] = -30.0
                char_logp[j] = torch.clamp(slp, min=-30.0, max=0.0)

            decoded = self.crf.decode(char_logp)
            tags = [TAGS[i] for i in decoded]

        ctx = NguCanhChar(raw, text, offsets, tags, char_logp)
        ctx.segmentation_fallback = fallback
        return ctx
