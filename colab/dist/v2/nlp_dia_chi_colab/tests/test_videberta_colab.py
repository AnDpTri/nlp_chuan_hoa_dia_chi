"""Smoke test với DeBERTa tí hon ngẫu nhiên; không tải/train backbone đầy đủ."""

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import unicodedata
import zipfile

AVAILABLE = all(importlib.util.find_spec(m) for m in ('torch', 'transformers', 'pyvi', 'safetensors'))
if AVAILABLE:
    import torch
    from transformers import DebertaV2Config, DebertaV2Model, PreTrainedTokenizerFast
    from tokenizers import Tokenizer, models, pre_tokenizers, processors
    from src.videberta import ViDebertaCharCRF, segment_with_map, encode_text, save_model, BoTachViDeberta
    from src.char_cnn import TAGS, TAG_ID
    from src.chuan_hoa import BoChuanHoa
    from colab.train_videberta import pack_batch, train
    from colab.export_results import export


@unittest.skipUnless(AVAILABLE, 'Cần colab/requirements.txt và torch')
class ViDebertaColabTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)

    def tiny(self):
        words = ['[PAD]', '[CLS]', '[SEP]', '[UNK]', 'Số', '12', 'Đường', 'Lê_Lợi', ',']
        tokenizer = Tokenizer(models.WordLevel({s: i for i, s in enumerate(words)}, unk_token='[UNK]'))
        tokenizer.pre_tokenizer = pre_tokenizers.Whitespace()
        tokenizer.post_processor = processors.TemplateProcessing(single='[CLS] $A [SEP]', special_tokens=[('[CLS]', 1), ('[SEP]', 2)])
        fast = PreTrainedTokenizerFast(tokenizer_object=tokenizer, pad_token='[PAD]', cls_token='[CLS]', sep_token='[SEP]', unk_token='[UNK]')
        config = DebertaV2Config(vocab_size=len(words), hidden_size=24, num_hidden_layers=1,
                   num_attention_heads=3, attention_head_size=8, intermediate_size=48,
                   max_position_embeddings=64, hidden_dropout_prob=0., attention_probs_dropout_prob=0.,
                   relative_attention=True, pos_att_type=['p2c', 'c2p'], position_buckets=8,
                   max_relative_positions=32, norm_rel_ebd='layer_norm', share_att_key=True)
        vocab = {c: i + 2 for i, c in enumerate(sorted(set('Số 12, Đường Lê Lợi')))}
        model = ViDebertaCharCRF(DebertaV2Model(config), len(vocab) + 2, char_dim=8, head_dim=16, dropout=0.)
        return model, fast, vocab

    def test_segment_map_va_fallback_khong_doi_chu(self):
        text = 'Đường Lê Lợi'
        segmented, mapping, fallback = segment_with_map(text, lambda _: 'Đường Lê_Lợi')
        self.assertFalse(fallback)
        self.assertEqual(text[slice(*mapping[8])], ' ')
        self.assertEqual(segmented[8], '_')
        raw, mapping, fallback = segment_with_map(text, lambda _: 'Đường Lê Lơi')
        self.assertTrue(fallback)
        self.assertEqual(raw, text)
        self.assertEqual(mapping, [(i, i + 1) for i in range(len(text))])

    def test_encoding_khong_cat_ngan_va_giu_ky_tu(self):
        _, tokenizer, _ = self.tiny()
        text = 'Số 12, Đường Lê Lợi'
        e = encode_text(text, tokenizer)
        self.assertEqual(len(e['piece_for_char']), len(text))
        self.assertTrue(all(0 <= i < len(e['input_ids']) for i in e['piece_for_char']))
        with self.assertRaisesRegex(ValueError, 'không cắt'):
            encode_text('a' * 2049, tokenizer)

    def test_gradient_toi_backbone_va_luu_nap_offline(self):
        torch.manual_seed(4)
        model, tokenizer, vocab = self.tiny()
        text = 'Số 12, Đường Lê Lợi'
        allowed = [[0] for _ in text]
        for a, b, role in [(0, 5, 'so_nha'), (7, len(text), 'duong')]:
            for i in range(a, b):
                allowed[i] = [TAG_ID[('B-' if i == a else 'I-') + role]]
        row = {'nfc': text, 'allowed': allowed, 'encoding': encode_text(text, tokenizer)}
        ids, attention, chars, pieces, mask, constraints = pack_batch([row], vocab, tokenizer.pad_token_id)
        model.train()
        optimizer = torch.optim.AdamW(model.parameters(), lr=.001)
        logits = model(ids, attention, chars, pieces, mask)
        loss = model.crf.loss(logits, mask, constraints)
        loss.backward()
        gradient = model.encoder.embeddings.word_embeddings.weight.grad
        self.assertTrue(torch.isfinite(gradient).all())
        self.assertGreater(gradient.abs().sum().item(), 0.)
        optimizer.step()
        model.eval()
        expected = model(ids, attention, chars, pieces, mask).detach()
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d) / 'model'
            save_model(model, tokenizer, vocab, folder, epoch=1)
            loaded = BoTachViDeberta(folder)
            actual = loaded.model(ids, attention, chars, pieces, mask).detach()
            self.assertTrue(torch.allclose(expected, actual, atol=1e-6))
            self.assertEqual(next(loaded.model.parameters()).device.type, 'cpu')
            raw = unicodedata.normalize('NFD', text)
            normalizer = BoChuanHoa(bo_tach=loaded)
            result = normalizer.chuan_hoa(raw)
            self.assertIn('videberta', result.thong_ke['mo_hinh'])
            for span in result.dau_vet:
                self.assertEqual(span['doan_goc'], raw[span['ky_tu_bat_dau']:span['ky_tu_ket_thuc']])
            self.assertEqual(normalizer.chuan_hoa('').dia_chi_chuan, '')

    def test_export_bo_optimizer_va_kiem_tra_zip(self):
        model, tokenizer, vocab = self.tiny()
        with tempfile.TemporaryDirectory() as d:
            run = Path(d) / 'tiny_run'
            run.mkdir()
            save_model(model, tokenizer, vocab, run / 'model', 1)
            (run / 'training.json').write_text(json.dumps({'training_complete': True}), encoding='utf-8')
            (run / 'run_config.json').write_text('{}', encoding='utf-8')
            (run / 'resume.pt').write_bytes(b'optimizer-fixture')
            output = Path(d) / 'result.zip'
            export(run, output)
            with zipfile.ZipFile(output) as z:
                self.assertIn('tiny_run/model/model.safetensors', z.namelist())
                self.assertFalse(any(n.endswith('resume.pt') for n in z.namelist()))
            with self.assertRaises(FileExistsError):
                export(run, output)

    def test_train_khong_co_gpu_phai_dung_truoc_khi_doc_du_lieu(self):
        if torch.cuda.is_available():
            self.skipTest('Chỉ kiểm tra guard khi không có CUDA')
        with self.assertRaisesRegex(RuntimeError, 'Cần bật GPU'):
            train(None)


if __name__ == '__main__':
    unittest.main()
