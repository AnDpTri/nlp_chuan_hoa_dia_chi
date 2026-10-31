"""Kiểm chứng hợp đồng CRF/đo span; không dùng tập test cuối."""

import importlib.util
from pathlib import Path
import tempfile
import unittest

from src.tien_xu_ly.crf_chi_tiet import bio_spans, tao_nhan, NguCanhCRF, dinh_dang_span, dac_trung, BoTachCRF
from src.chuan_hoa import BoChuanHoa
from src.tien_xu_ly import tach_token
from danh_gia.do_crf import sequence_metrics
from danh_gia.du_lieu_crf import tu_csv, tu_span


class CRFContractTests(unittest.TestCase):
    def test_bio_khong_noi_qua_O_va_dem_I_mo_coi(self):
        spans, invalid = bio_spans(['I-duong', 'I-duong', 'O', 'I-duong'])
        self.assertEqual(spans, [('duong', 0, 2), ('duong', 3, 4)])
        self.assertEqual(invalid, 2)

    def test_nhan_chong_phai_bi_chan(self):
        with self.assertRaisesRegex(ValueError, 'chồng'):
            tao_nhan(3, [('so_nha', 0, 2), ('duong', 1, 3)])

    def test_admin_mask_khong_noi_cac_doan_roi(self):
        context = NguCanhCRF(['Lê', 'Lợi', 'Tân', 'An', 'Hoa'],
                            ['B-duong', 'I-duong', 'I-duong', 'I-duong', 'I-duong'], [.1]*5)
        detail, spans, _, _ = context.tach({2, 3})
        self.assertEqual([(s['bat_dau'], s['ket_thuc']) for s in spans], [(0, 2), (4, 5)])
        self.assertNotEqual(detail['duong'], 'Đường Lê Lợi Hoa')

    def test_formatter_khong_mo_rong_ten_rieng(self):
        self.assertEqual(dinh_dang_span(['24B', '-', '24'], 'so_nha')[0], 'Số 24B-24')
        self.assertEqual(dinh_dang_span(['Xa', 'lộ', 'Hà', 'Nội'], 'duong')[0], 'Xa lộ Hà Nội')
        self.assertEqual(dinh_dang_span(['NTT'], 'duong')[0], 'Đường Ntt')

    def test_F1_span_khong_bi_token_O_lam_dep(self):
        gold = ['O']*100+['B-duong', 'I-duong']
        pred = ['O']*101+['B-duong']
        m = sequence_metrics([(gold, pred)])
        self.assertGreater(m['token_accuracy_pct'], 97)
        self.assertEqual(m['span_micro']['f1_pct'], 0)
        self.assertEqual(m['span_per_field']['duong']['reference_spans'], 1)
        self.assertEqual(m['span_per_field']['ngo_ngach_hem']['reference_spans'], 0)

    def test_can_chinh_khong_tao_am_gia_cho_tien_to_duong(self):
        row = {'id': 'fixture', 'dau_vao': '12, Đường Lê Lợi', 'so_nha': 'Số 12',
               'duong': '', 'ngo_ngach_hem': '', 'thon_xom': ''}
        with self.assertRaisesRegex(ValueError, 'chua_co_nhan:duong'):
            tu_csv(row)

    def test_khong_hoc_nhan_cat_giua_token(self):
        row = {'id': 'fixture', 'dau_vao': '151Đ.', 'usable_for_span_training': True,
               'tokens': [{'token': '151', 'start': 0, 'end': 3, 'bio_tag': 'B-so_nha'},
                          {'token': 'Đ', 'start': 3, 'end': 4, 'bio_tag': 'O'},
                          {'token': '.', 'start': 4, 'end': 5, 'bio_tag': 'O'}],
               'spans': {'so_nha': {'start': 0, 'end': 3, 'text': '151'}}}
        with self.assertRaisesRegex(ValueError, 'span_cat_giua_token_runtime'):
            tu_span(row, {'dau_vao': '151Đ.'})

    @unittest.skipUnless(importlib.util.find_spec('pycrfsuite'), 'Cần requirements-crf.txt')
    def test_train_luu_nap_va_chay_pipeline_that(self):
        import pycrfsuite
        text = 'Số 12, Đường Lê Lợi, Phường Trúc Bạch, Quận Ba Đình, Hà Nội'
        tokens = tach_token(text)
        tags = tao_nhan(len(tokens), [('so_nha', 0, 2), ('duong', 3, 7)])
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'tiny.crfsuite'
            trainer = pycrfsuite.Trainer(algorithm='lbfgs', verbose=False)
            trainer.set_params({'max_iterations': 10})
            trainer.append(dac_trung(tokens), tags)
            trainer.train(str(path))
            first, second = BoTachCRF(path), BoTachCRF(path)
            self.assertEqual(first.chuan_bi(tokens).labels, second.chuan_bi(tokens).labels)
            r = BoChuanHoa(bo_tach=first).chuan_hoa(text)
            self.assertEqual(r.thong_ke['crf_model_sha256'], first.ma_bam)
            self.assertTrue(r.thong_ke['phien_ban'].startswith('thu_nghiem_crf'))
            self.assertEqual(BoChuanHoa(bo_tach=first).chuan_hoa('').dia_chi_chuan, '')
            used = set()
            for s in r.dau_vet:
                self.assertEqual(s['doan_goc'], text[s['ky_tu_bat_dau']:s['ky_tu_ket_thuc']])
                current = set(range(s['token_bat_dau'], s['token_ket_thuc']))
                self.assertFalse(current & used)
                used |= current


if __name__ == '__main__':
    unittest.main()
