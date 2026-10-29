"""ViDeBERTa pretrained + đầu ký tự + CRF; train GPU, suy luận CPU offline."""

import hashlib
import json
from pathlib import Path

import torch
from torch import nn

from .char_cnn import LinearCRF, NguCanhChar, TAGS, nfc_offsets

REPO_ID = 'Fsoft-AIC/videberta-xsmall'
REVISION = '029b6b1b1d7636221bd2d1a98b46a2fdba3af34e'


def load_tokenizer(folder):
    from transformers import PreTrainedTokenizerFast
    folder = Path(folder)
    special = json.loads((folder / 'special_tokens_map.json').read_text(encoding='utf-8'))
    special = {k: v['content'] if isinstance(v, dict) else v for k, v in special.items()}
    return PreTrainedTokenizerFast(tokenizer_file=str(folder / 'tokenizer.json'), **special)


def segment_with_map(text, segmenter=None):
    if segmenter is None:
        from pyvi import ViTokenizer
        segmenter = ViTokenizer.tokenize
    segmented = segmenter(text)
    mapping, pos = [], 0
    for ch in segmented:
        if ch.isspace() or (ch == '_' and (pos >= len(text) or text[pos] != '_')):
            start = pos
            while pos < len(text) and text[pos].isspace():
                pos += 1
            if ch == '_' and start == pos:
                return text, [(i, i + 1) for i in range(len(text))], True
            mapping.append((start, pos))
            continue
        while pos < len(text) and text[pos].isspace():
            pos += 1
        if pos >= len(text) or ch != text[pos]:
            # Không sửa nội dung hoặc mất offset khi segmenter đổi ký tự.
            return text, [(i, i + 1) for i in range(len(text))], True
        mapping.append((pos, pos + 1))
        pos += 1
    if text[pos:].strip():
        return text, [(i, i + 1) for i in range(len(text))], True
    return segmented, mapping, False


def encode_text(text, tokenizer, segmenter=None):
    if not text or len(text) > 2048:
        raise ValueError('Bản thử cần 1–2048 ký tự NFC; không cắt ngắn')
    segmented, mapping, fallback = segment_with_map(text, segmenter)
    encoding = tokenizer(segmented, return_offsets_mapping=True, truncation=False)
    if len(encoding['input_ids']) > 512:
        raise ValueError('Địa chỉ vượt 512 subword; không cắt ngắn')
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
    return {'input_ids': encoding['input_ids'], 'piece_for_char': piece_for_char,
            'segmentation_fallback': fallback, 'segmented': segmented}


class ViDebertaCharCRF(nn.Module):
    def __init__(self, encoder, vocab_size, char_dim=32, head_dim=128, dropout=.1):
        super().__init__()
        self.encoder = encoder
        self.char_embedding = nn.Embedding(vocab_size, char_dim, padding_idx=0)
        self.project = nn.Linear(encoder.config.hidden_size + char_dim, head_dim)
        self.conv = nn.Conv1d(head_dim, head_dim, 3, padding=1)
        self.dropout = nn.Dropout(dropout)
        self.classifier = nn.Linear(head_dim, len(TAGS))
        self.crf = LinearCRF()

    def forward(self, input_ids, attention_mask, char_ids, piece_for_char, char_mask):
        hidden = self.encoder(input_ids=input_ids, attention_mask=attention_mask).last_hidden_state
        selected = hidden.gather(1, piece_for_char[..., None].expand(-1, -1, hidden.size(-1)))
        x = torch.cat([selected, self.char_embedding(char_ids)], dim=-1)
        x = self.dropout(torch.relu(self.project(x))) * char_mask[..., None]
        x = torch.relu(x + self.conv(x.transpose(1, 2)).transpose(1, 2)) * char_mask[..., None]
        return self.classifier(self.dropout(x))


def save_model(model, tokenizer, vocab, folder, epoch):
    from safetensors.torch import save_file
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    tokenizer.save_pretrained(folder)
    save_file({k: v.detach().cpu().contiguous() for k, v in model.state_dict().items()}, str(folder / 'model.safetensors'))
    meta = {'format': 1, 'repo_id': REPO_ID, 'revision': REVISION, 'tags': TAGS, 'vocab': vocab,
            'encoder_config': model.encoder.config.to_dict(), 'epoch': epoch,
            'head': {'char_dim': model.char_embedding.embedding_dim, 'head_dim': model.project.out_features, 'dropout': model.dropout.p}}
    (folder / 'model_config.json').write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8', newline='\n')


class BoTachViDeberta:
    phien_ban = 'videberta_xsmall_char_crf_v1'
    ten_mo_hinh = 'videberta_xsmall_char_crf'
    bao_ve_chi_tiet = False

    def __init__(self, model_dir, threads=1, device='cpu'):
        from transformers import DebertaV2Config, DebertaV2Model
        from safetensors.torch import load_file
        if threads < 1:
            raise ValueError('threads phải >= 1')
        torch.set_num_threads(threads)
        folder = Path(model_dir)
        self.meta = json.loads((folder / 'model_config.json').read_text(encoding='utf-8'))
        if self.meta['format'] != 1 or self.meta['tags'] != TAGS:
            raise ValueError('Schema ViDeBERTa không tương thích')
        self.vocab = self.meta['vocab']
        self.tokenizer = load_tokenizer(folder)
        config = DebertaV2Config.from_dict(self.meta['encoder_config'])
        self.model = ViDebertaCharCRF(DebertaV2Model(config), len(self.vocab) + 2, **self.meta['head'])
        self.model.load_state_dict(load_file(str(folder / 'model.safetensors'), device='cpu'))
        self.device = torch.device(device)
        self.model.to(self.device).eval()
        h = hashlib.sha256()
        for name in ('model.safetensors', 'model_config.json', 'tokenizer.json', 'special_tokens_map.json'):
            with (folder / name).open('rb') as f:
                for chunk in iter(lambda: f.read(1024 * 1024), b''):
                    h.update(chunk)
        self.ma_bam = h.hexdigest()

    def chuan_bi_chuoi(self, raw):
        text, offsets = nfc_offsets(raw)
        if not text:
            ctx = NguCanhChar(raw, text, offsets, [], torch.empty(0, len(TAGS)))
            ctx.segmentation_fallback = False
            return ctx
        enc = encode_text(text, self.tokenizer)
        tensors = [torch.tensor([x], dtype=torch.long, device=self.device) for x in
                   (enc['input_ids'], [1] * len(enc['input_ids']), [self.vocab.get(c, 1) for c in text], enc['piece_for_char'])]
        mask = torch.ones(1, len(text), dtype=torch.bool, device=self.device)
        with torch.inference_mode():
            logits = self.model(*tensors, mask)[0].float().cpu()
            tags = [TAGS[i] for i in self.model.crf.decode(logits)]
            lp = torch.log_softmax(logits, -1)
        ctx = NguCanhChar(raw, text, offsets, tags, lp)
        ctx.segmentation_fallback = enc['segmentation_fallback']
        return ctx
