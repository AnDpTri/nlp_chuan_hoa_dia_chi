"""Kiểm chứng toán CRF, offset và đường chạy neural thật trên fixture độc lập."""

import itertools
import importlib.util
import json
from pathlib import Path
import tempfile
import unicodedata
import unittest

HAS_NEURAL = all(importlib.util.find_spec(m) is not None for m in ('torch', 'numpy', 'lightgbm'))
if HAS_NEURAL:
    import torch
    from src.tien_xu_ly.char_cnn import CharCNNCRF, LinearCRF, TAGS, TAG_ID, NguCanhChar, nfc_offsets, BoTachCharCNN
    from src.chuan_hoa import BoChuanHoa
    from danh_gia.du_lieu_char import char_record
    from src.danh_muc import DanhMuc
    from src.tien_xu_ly.tra_cuu_neural import TraCuuNeural
    from src.tien_xu_ly.tim_kiem import dung_trie, sinh_ung_vien
    from src.tien_xu_ly.xep_hang import BoXepHang, FEATURES


@unittest.skipUnless(HAS_NEURAL, 'Cần requirements-neural.txt trong .venv-neural')
class CharTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)

    def test_crf_partition_va_viterbi_so_voi_vet_can(self):
        torch.manual_seed(21)
        crf = LinearCRF()
        with torch.no_grad():
            crf.transitions.copy_(torch.randn_like(crf.transitions) * .2)
        e = torch.randn(1, 3, len(TAGS))
        scores, paths = [], []
        for path in itertools.product(range(len(TAGS)), repeat=3):
            if not crf.start_ok[path[0]] or not all(crf.legal[a, b] for a, b in zip(path, path[1:])):
                continue
            score = sum(e[0, t, j] for t, j in enumerate(path)) + sum(crf.transitions[a, b] for a, b in zip(path, path[1:]))
            scores.append(score)
            paths.append(path)
        expected = torch.logsumexp(torch.stack(scores), 0)
        actual = crf.partition(e, torch.ones(1, 3, dtype=torch.bool))[0]
        self.assertAlmostEqual(expected.item(), actual.item(), places=5)
        self.assertEqual(crf.decode(e[0]), list(paths[torch.stack(scores).argmax().item()]))

    def test_partial_crf_loss_gradient_va_padding(self):
        crf = LinearCRF()
        e = torch.randn(2, 4, len(TAGS), requires_grad=True)
        mask = torch.tensor([[1, 1, 1, 1], [1, 1, 0, 0]], dtype=torch.bool)
        allowed = torch.ones_like(e, dtype=torch.bool)
        self.assertAlmostEqual(crf.loss(e, mask, allowed).item(), 0., places=5)
        allowed[0, 0] = False
        allowed[0, 0, TAG_ID['B-so_nha']] = True
        loss = crf.loss(e, mask, allowed)
        self.assertGreater(loss.item(), 0)
        loss.backward()
        self.assertTrue(torch.isfinite(e.grad).all())
        self.assertTrue(e.grad[1, 2:].eq(0).all())

    def test_padding_khong_doi_emissions_cua_cau_ngan(self):
        torch.manual_seed(1)
        m = CharCNNCRF(20, embedding=8, channels=8, dilations=[1, 2], dropout=0).eval()
        ids = torch.tensor([[2, 3, 4]])
        one = m(ids, torch.ones_like(ids, dtype=torch.bool))
        padded = torch.tensor([[2, 3, 4, 0, 0, 0], [5, 6, 7, 8, 9, 2]])
        two = m(padded, padded.ne(0))[:1, :3]
        self.assertTrue(torch.allclose(one, two, atol=1e-6))

    def test_NFD_offset_va_span_cat_giua_token(self):
        raw = unicodedata.normalize('NFD', '151Đ. Tây Thạnh')
        text, offsets = nfc_offsets(raw)
        tags = ['O'] * len(text)
        for role, a, b in [('so_nha', 0, 3), ('duong', 3, len(text))]:
            for i in range(a, b):
                tags[i] = ('B-' if i == a else 'I-') + role
        ctx = NguCanhChar(raw, text, offsets, tags, torch.log_softmax(torch.zeros(len(text), len(TAGS)), -1))
        detail, spans, _, _ = ctx.tach(set())
        self.assertEqual(detail['so_nha'], 'Số 151')
        self.assertEqual(detail['duong'], 'Đường Tây Thạnh')
        for role, a, b in ctx.char_spans:
            self.assertEqual(unicodedata.normalize('NFC', raw[a:b]), '151' if role == 'so_nha' else 'Đ. Tây Thạnh')

    def test_hanh_chinh_chua_can_chinh_khong_bi_ep_O(self):
        dm = DanhMuc()
        rec = char_record('12 NTMK XYZ', [('so_nha', 0, 2), ('duong', 3, 7)], {'id': 'fixture'}, dm)
        self.assertEqual(rec['allowed'][0], [TAG_ID['B-so_nha']])
        self.assertIn(TAG_ID['B-xa'], rec['allowed'][8])
        self.assertNotIn(TAG_ID['B-duong'], rec['allowed'][8])

    def test_checkpoint_cpu_va_pipeline_rong(self):
        config = {'embedding': 8, 'channels': 8, 'dilations': [1], 'dropout': 0.}
        model = CharCNNCRF(3, **config)
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'tiny.pt'
            torch.save({'format': 1, 'tags': TAGS, 'vocab': {'a': 2}, 'config': config, 'state_dict': model.state_dict()}, p)
            extractor = BoTachCharCNN(p)
            normalizer = BoChuanHoa(bo_tach=extractor)
            self.assertEqual(normalizer.chuan_hoa('').dia_chi_chuan, '')
            result = normalizer.chuan_hoa('a')
            self.assertEqual(result.thong_ke['phien_ban'], 'char_cnn_crf_v1')
            self.assertEqual(next(extractor.model.parameters()).device.type, 'cpu')
            with self.assertRaisesRegex(ValueError, 'không cắt'):
                normalizer.chuan_hoa('a' * 2049)

    def test_viet_tat_hanh_chinh_va_sai_chinh_ta_co_ngu_canh(self):
        dm = DanhMuc()
        lookup, trie = TraCuuNeural(dm), dung_trie(dm)
        for name in ('P. TB', 'Phường Thớ Bình'):
            raw = name + ', TP Cần Thơ'
            normalized, offsets = nfc_offsets(raw)
            tags = ['B-xa'] + ['I-xa'] * (len(name) - 1) + ['O'] * (len(raw) - len(name))
            ctx = NguCanhChar(raw, normalized, offsets, tags, torch.zeros(len(tags), len(TAGS)))
            candidates = sinh_ung_vien(ctx.tokens, trie, bao_ve_chi_tiet=False)
            found = lookup.mo_rong(ctx, ctx.tokens, trie, candidates)
            self.assertTrue(any(u.ma == '31123' and u.cay == 'cu' for u in found))

    def test_ranker_that_luu_nap_va_chan_sai_checkpoint(self):
        import lightgbm as lgb
        import numpy as np
        x = np.zeros((4, len(FEATURES)))
        x[:, 0] = [0, 1, 1, 0]
        data = lgb.Dataset(x, label=[0, 2, 2, 0], group=[2, 2], feature_name=FEATURES)
        model = lgb.train({'objective': 'lambdarank', 'num_leaves': 2, 'min_data_in_leaf': 1,
                           'min_data_in_bin': 1, 'verbosity': -1, 'num_threads': 1}, data, num_boost_round=4)
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'ranker.txt'
            model.save_model(str(path))
            path.with_suffix('.json').write_text(json.dumps({'features': FEATURES, 'extractor_sha256': 'cnn',
                                                            'catalogue_sha256': {'a': 'hash'}, 'close_margin': .05}), encoding='utf-8')
            loaded = BoXepHang(path, 'cnn', {'a': 'hash'})
            scores = loaded.cham_diem(x.tolist())
            self.assertGreater(scores[1], scores[0])
            self.assertTrue(np.allclose(scores, model.predict(x, num_threads=1)))
            with self.assertRaisesRegex(ValueError, 'nhận diện'):
                BoXepHang(path, 'khac_cnn', {'a': 'hash'})
            with self.assertRaisesRegex(ValueError, 'Danh mục'):
                BoXepHang(path, 'cnn', {'a': 'khac'})


if __name__ == '__main__':
    unittest.main()
