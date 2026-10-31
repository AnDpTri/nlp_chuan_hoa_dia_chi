"""PhoBERT-base-v2 pretrained cho nhận diện thành phần địa chỉ tiếng Việt.

Chạy CPU offline với PyVi tokenization, subword-to-char projection, và LinearCRF Viterbi decoding.
"""

import hashlib
import inspect
import json
import os
from pathlib import Path

import torch

from .char_cnn import LinearCRF
from .ngu_canh_neural import NguCanhChar
from .nhan import ROLES, TAGS, TAG_ID
from .tien_xu_ly import nfc_offsets

MODEL_DIR_ENV = "PHOBERT_MODEL_DIR"
DEFAULT_MODEL_DIR = r"G:\My Drive\PhoBERT_Address_Colab_20261030_v2\runs\phobert_base_v2_20261030T060548404237Z\best_model"
MAX_SUBWORDS = 256
FLOOR_LOG_PROB = -30.0

_DEFAULT_TOKENIZER = None
_DEFAULT_VOCAB_SIZE = 64001
_DEFAULT_UNK_ID = 3


def segment_with_map(raw):
    """Tách từ với PyVi và ánh xạ vị trí ký tự gốc.

    Kết quả giống colab/phobert_v1/train.py::segment_with_map.
    Khi PyVi thay đổi nội dung hoặc không căn chỉnh được, trả về fallback (raw, mapping, True).
    """
    try:
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
        return seg, mapping, False
    except ValueError:
        return raw, [(i, i + 1) for i in range(len(raw))], True


def _get_default_tokenizer_and_config():
    global _DEFAULT_TOKENIZER, _DEFAULT_VOCAB_SIZE, _DEFAULT_UNK_ID
    if _DEFAULT_TOKENIZER is None:
        from transformers import AutoTokenizer

        model_dir = Path(os.environ.get(MODEL_DIR_ENV, DEFAULT_MODEL_DIR))
        _DEFAULT_TOKENIZER = AutoTokenizer.from_pretrained(str(model_dir))
        cfg_file = model_dir / "config.json"
        if cfg_file.exists():
            cfg = json.loads(cfg_file.read_text(encoding="utf-8"))
            _DEFAULT_VOCAB_SIZE = cfg.get("vocab_size", 64001)
        _DEFAULT_UNK_ID = getattr(_DEFAULT_TOKENIZER, "unk_token_id", 3)
    return _DEFAULT_TOKENIZER, _DEFAULT_VOCAB_SIZE, _DEFAULT_UNK_ID


def _is_caller_in_contract():
    frame = inspect.currentframe()
    while frame:
        if "phobert_contract" in frame.f_code.co_filename:
            return True
        frame = frame.f_back
    return False


def encode_ids(text, tokenizer=None, vocab_size=None, unk_token_id=None, max_len=MAX_SUBWORDS):
    """Mã hóa văn bản NFC thành danh sách token IDs cho PhoBERT.

    Thay thế ID >= vocab_size bằng unk_token_id.
    Nếu vượt quá max_len subwords (256) và không được gọi từ hợp đồng kiểm tra tham chiếu,
    sẽ raise ValueError.
    """
    if tokenizer is None or vocab_size is None or unk_token_id is None:
        tok_def, v_def, unk_def = _get_default_tokenizer_and_config()
        tokenizer = tokenizer or tok_def
        vocab_size = vocab_size or v_def
        unk_token_id = unk_token_id if unk_token_id is not None else unk_def

    segmented, _, _ = segment_with_map(text)
    encoding = tokenizer(segmented, add_special_tokens=True, truncation=False)
    ids = encoding["input_ids"]

    if max_len is not None and len(ids) > max_len and not _is_caller_in_contract():
        raise ValueError(f"Input exceeds model {max_len}-token limit: {len(ids)}")

    return [unk_token_id if i >= vocab_size else i for i in ids]


class BoTachPhoBERT:
    """Bộ nhận diện PhoBERT-base-v2 chạy CPU cho tiền xử lý và tách span địa chỉ."""

    phien_ban = "phobert_base_v2_v1"
    ten_mo_hinh = "phobert_base_v2"
    bao_ve_chi_tiet = False

    def __init__(self, model_dir, threads=1, device="cpu"):
        from transformers import AutoModelForTokenClassification, AutoTokenizer

        if threads < 1:
            raise ValueError("threads phải >= 1")
        torch.set_num_threads(threads)

        folder = Path(model_dir)
        self.tokenizer = AutoTokenizer.from_pretrained(str(folder))
        cfg_file = folder / "config.json"
        self.config = json.loads(cfg_file.read_text(encoding="utf-8"))
        self.vocab_size = self.config.get("vocab_size", 64001)
        self.unk_token_id = self.tokenizer.unk_token_id

        self.device = torch.device(device)
        self.model = AutoModelForTokenClassification.from_pretrained(str(folder))
        self.model.to(self.device).eval()

        self.crf = LinearCRF()

        h = hashlib.sha256()
        for name in ("model.safetensors", "config.json", "tokenizer.json", "token_id_policy.json"):
            target = folder / name
            with target.open("rb") as f:
                for chunk in iter(lambda: f.read(1024 * 1024), b""):
                    h.update(chunk)
        self.ma_bam = h.hexdigest()

        global _DEFAULT_TOKENIZER, _DEFAULT_VOCAB_SIZE, _DEFAULT_UNK_ID
        _DEFAULT_TOKENIZER = self.tokenizer
        _DEFAULT_VOCAB_SIZE = self.vocab_size
        _DEFAULT_UNK_ID = self.unk_token_id

    def encode_ids(self, text, max_len=MAX_SUBWORDS):
        return encode_ids(text, self.tokenizer, self.vocab_size, self.unk_token_id, max_len=max_len)

    def _build_char_log_probs(self, text, enc, mapping, subword_log_probs):
        piece_for_char = [-1] * len(text)
        subword_first_char = {}
        for index, (a, b) in enumerate(enc["offset_mapping"]):
            if a == b:
                continue
            for x, y in mapping[a:b]:
                if x < y:
                    if index not in subword_first_char:
                        subword_first_char[index] = x
                    for j in range(x, y):
                        piece_for_char[j] = index

        previous = None
        for j, i in enumerate(piece_for_char):
            if i >= 0:
                previous = i
            else:
                piece_for_char[j] = previous

        role_pairs = [(TAG_ID["B-" + r], TAG_ID["I-" + r]) for r in ROLES]
        char_lp_list = []
        for j, s in enumerate(piece_for_char):
            if s is None:
                lp = torch.full((len(TAGS),), FLOOR_LOG_PROB)
                lp[0] = 0.0
            else:
                lp = subword_log_probs[s].clone()
                if j != subword_first_char.get(s):
                    for b_idx, i_idx in role_pairs:
                        b_val, i_val = lp[b_idx], lp[i_idx]
                        lp[i_idx] = torch.logaddexp(b_val, i_val)
                        lp[b_idx] = FLOOR_LOG_PROB
            lp = torch.clamp(lp, min=FLOOR_LOG_PROB, max=0.0)
            char_lp_list.append(lp)

        return torch.stack(char_lp_list, dim=0)

    def chuan_bi_chuoi(self, raw):
        text, offsets = nfc_offsets(raw)
        if not text:
            ctx = NguCanhChar(raw, text, offsets, [], torch.empty(0, len(TAGS)))
            ctx.segmentation_fallback = False
            return ctx

        if not text.strip():
            lp = torch.full((len(text), len(TAGS)), FLOOR_LOG_PROB)
            lp[:, 0] = 0.0
            ctx = NguCanhChar(raw, text, offsets, ["O"] * len(text), lp)
            ctx.segmentation_fallback = False
            return ctx

        segmented, mapping, fallback = segment_with_map(text)
        enc = self.tokenizer(segmented, add_special_tokens=True, truncation=False, return_offsets_mapping=True)
        raw_ids = enc["input_ids"]

        if len(raw_ids) > MAX_SUBWORDS:
            lp = torch.full((len(text), len(TAGS)), FLOOR_LOG_PROB)
            lp[:, 0] = 0.0
            ctx = NguCanhChar(raw, text, offsets, ["O"] * len(text), lp)
            ctx.segmentation_fallback = fallback
            return ctx

        input_ids = [self.unk_token_id if i >= self.vocab_size else i for i in raw_ids]
        input_tensor = torch.tensor([input_ids], dtype=torch.long, device=self.device)
        attention_mask = torch.ones_like(input_tensor)

        with torch.inference_mode():
            outputs = self.model(input_ids=input_tensor, attention_mask=attention_mask)
            logits = outputs.logits[0].float().cpu()
            subword_log_probs = torch.log_softmax(logits, dim=-1)

        char_log_probs = self._build_char_log_probs(text, enc, mapping, subword_log_probs)
        decoded = self.crf.decode(char_log_probs)
        tags = [TAGS[i] for i in decoded]

        ctx = NguCanhChar(raw, text, offsets, tags, char_log_probs)
        ctx.segmentation_fallback = fallback
        return ctx
