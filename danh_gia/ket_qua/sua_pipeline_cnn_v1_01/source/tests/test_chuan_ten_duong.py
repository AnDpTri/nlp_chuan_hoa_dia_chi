"""Fixture độc lập: tỉnh, va chạm tên, dấu đã nhập và provenance train."""

import json
from pathlib import Path
import tempfile
import unicodedata
import unittest

from src.chuan_ten_duong import TuDienDuong, tao_tu_dien
from src.chuan_hoa import BoChuanHoa
from src.crf_chi_tiet import NguCanhCRF


class TenDuongTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def dictionary(self, entries):
        path = self.root / 'names.json'
        path.write_text(json.dumps({'format': 1, 'source_scope': 'train_only', 'entries': [
            {'province': p, 'canonical': name, 'train_ids': ['fixture_train']} for p, name in entries
        ]}, ensure_ascii=False), encoding='utf-8')
        return TuDienDuong(path)

    def test_phuc_hoi_dau_nhung_can_dung_tinh_va_loai_duong(self):
        d = self.dictionary([('01', 'Đường Nguyễn Văn An')])
        self.assertEqual(d.chuan_hoa('Đường Nguyen Van An', '01')[0], 'Đường Nguyễn Văn An')
        for value, province in [('Đường Nguyen Van An', ''), ('Đường Nguyen Van An', '02'),
                                ('Phố Nguyen Van An', '01'), ('Đường Tên Chưa Biết', '01')]:
            self.assertEqual(d.chuan_hoa(value, province), (value, None))

    def test_khong_sua_dau_da_nhap_ke_ca_NFD(self):
        d = self.dictionary([('01', 'Đường Hòa Bình')])
        for value in ('Đường Hóa Binh', unicodedata.normalize('NFD', 'Đường Hóa Binh')):
            self.assertEqual(d.chuan_hoa(value, '01'), (value, None))
        self.assertEqual(d.chuan_hoa('Đường Hòa Binh', '01')[0], 'Đường Hòa Bình')

    def test_viet_tat_co_va_cham_phai_tu_choi(self):
        d = self.dictionary([('01', 'Đường Nguyễn Văn An'), ('01', 'Đường Nguyễn Văn Anh'),
                             ('02', 'Đường Nguyễn Văn An')])
        self.assertEqual(d.chuan_hoa('Đường NVA', '01'), ('Đường NVA', None))
        self.assertEqual(d.chuan_hoa('Đường NVA', '02')[0], 'Đường Nguyễn Văn An')

    def test_cung_khoa_khac_dau_khong_chon_theo_tan_suat(self):
        d = self.dictionary([('01', 'Đường Hòa Bình'), ('01', 'Đường Hóa Bình')])
        self.assertEqual(d.chuan_hoa('Đường Hoa Binh', '01'), ('Đường Hoa Binh', None))

    def test_builder_khong_doc_dev_va_khong_nhan_ten_khong_co_trong_span(self):
        row = {'id': 'train-fixture', 'split': 'train_goc', 'canonical_usable': True,
               'text': '7 Đường Hoa Binh', 'detail_spans_raw': [['duong', 2, 16]],
               'ref': {'duong': 'Đường Hòa Bình', 'ma_tinh': '01'}}
        train = self.root / 'train.jsonl'
        train.write_text(json.dumps(row, ensure_ascii=False) + '\n', encoding='utf-8')
        payload = tao_tu_dien(train, self.root / 'built.json')
        self.assertEqual(len(payload['entries']), 1)
        row['ref']['duong'] = 'Đường Bịa Tên'
        train.write_text(json.dumps(row, ensure_ascii=False) + '\n', encoding='utf-8')
        self.assertEqual(tao_tu_dien(train, self.root / 'rejected.json')['entries'], [])
        row['split'] = 'dev_goc'
        train.write_text(json.dumps(row, ensure_ascii=False) + '\n', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'ngoài train'):
            tao_tu_dien(train, self.root / 'bad.json')

    def test_pipeline_co_dau_vet_goc_va_nguon_tra_cuu(self):
        d = self.dictionary([('01', 'Đường Hòa Bình')])
        text = unicodedata.normalize('NFD', 'Số 7 Đường Hoa Binh, Thành phố Hà Nội')
        result = BoChuanHoa(tu_dien_duong=d).chuan_hoa(text)
        self.assertEqual(result.duong, 'Đường Hòa Bình')
        self.assertIn('ten_duong_tham_chieu_train_chua_xac_minh', result.canh_bao)
        road = next(s for s in result.dau_vet if s['truong'] == 'duong')
        self.assertEqual(road['doan_goc'], text[road['ky_tu_bat_dau']:road['ky_tu_ket_thuc']])
        self.assertEqual(road['chuan_hoa_ten']['gia_tri_sau'], result.duong)

    def test_bao_ve_ten_duong_nhung_giu_hanh_chinh_co_tien_to(self):
        class Extractor:
            bao_ve_chi_tiet = False

            def chuan_bi(self, tokens):
                labels = ['O'] * len(tokens)
                labels[:4] = ['B-duong', 'I-duong', 'I-duong', 'I-duong']
                return NguCanhCRF(tokens, labels, [.5] * len(tokens))

        text = 'Đường Lê Đại Hành, Phường Lê Đại Hành, Hà Nội'
        base = BoChuanHoa(bo_tach=Extractor())
        fixed = BoChuanHoa(danh_muc=base.danh_muc, bo_tach=Extractor(), bao_ve_duong=True)
        candidates0 = base.tao_gia_thuyet(text)[1]
        candidates1 = fixed.tao_gia_thuyet(text)[1]
        inside = lambda u: 1 <= u.bat_dau and u.ket_thuc <= 4 and not u.co_tien_to
        self.assertTrue(any(inside(u) for u in candidates0))
        self.assertFalse(any(inside(u) for u in candidates1))
        explicit = [u for u in candidates0 if u.co_tien_to and u.bat_dau == 5]
        self.assertTrue(explicit)
        self.assertTrue(all(u in candidates1 for u in explicit))


if __name__ == '__main__':
    unittest.main()
