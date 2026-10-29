"""Hợp đồng theo cấu trúc; fixture viết tay, không đọc train/dev/test dataset."""
import itertools
import json
import tempfile
import unittest
import unicodedata
from dataclasses import asdict
from pathlib import Path

from src.chuan_hoa import BoChuanHoa
from src.chuan_ten_duong import TuDienDuong
from src.crf_chi_tiet import NguCanhCRF


class ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = BoChuanHoa()

    def dictionary(self, names):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        p = Path(tmp.name) / 'names.json'
        p.write_text(json.dumps({'format': 1, 'source_scope': 'train_only', 'entries': [
            {'canonical': n, 'province': '01', 'train_ids': ['independent_fixture']} for n in names
        ]}, ensure_ascii=False), encoding='utf-8')
        return TuDienDuong(p)

    def model(self, **kwargs):
        return BoChuanHoa(danh_muc=self.base.danh_muc, hop_dong=True, **kwargs)

    def test_mot_ten_train_cung_khong_tu_thanh_ten_chac_chan(self):
        names = self.dictionary(['Đường Hòa Bình'])
        text = 'Số 6 Đường Hoa Binh, Thành phố Hà Nội'
        new = self.model(tu_dien_duong=names).chuan_hoa(text)
        old = BoChuanHoa(danh_muc=self.base.danh_muc, tu_dien_duong=names).chuan_hoa(text)
        self.assertEqual(new.duong, 'Đường Hoa Binh')
        self.assertEqual(old.duong, 'Đường Hòa Bình')
        evidence = new.thong_ke['hop_dong']['truong']['duong']
        self.assertEqual(evidence['ung_vien_ten'][0]['gia_tri'], 'Đường Hòa Bình')
        self.assertFalse(evidence['ung_vien_ten'][0]['xac_minh_doc_lap'])

    def test_trung_khoa_giu_du_cac_ten_khong_chon_theo_tan_suat(self):
        names = self.dictionary(['Đường Hòa Bình', 'Đường Hóa Bình'])
        r = self.model(tu_dien_duong=names).chuan_hoa('Số 6 Đường Hoa Binh, Thành phố Hà Nội')
        candidates = r.thong_ke['hop_dong']['truong']['duong']['ung_vien_ten']
        self.assertEqual(len(candidates), 2)
        self.assertEqual(r.duong, 'Đường Hoa Binh')

    def test_dau_mau_thuan_duoc_ghi_ro_khong_sua(self):
        names = self.dictionary(['Đường Hòa Bình'])
        r = self.model(tu_dien_duong=names).chuan_hoa('Số 6 Đường Hóa Binh, Thành phố Hà Nội')
        candidates = r.thong_ke['hop_dong']['truong']['duong']['ung_vien_ten']
        self.assertFalse(candidates[0]['tuong_thich_dau'])
        self.assertEqual(r.duong, 'Đường Hóa Binh')

    def test_khong_tu_suy_tinh_tu_ten_duong(self):
        names = self.dictionary(['Đường Hòa Bình'])
        r = self.model(tu_dien_duong=names).chuan_hoa('Số 6 Đường Hoa Binh')
        self.assertEqual(r.thong_ke['hop_dong']['truong']['duong']['ung_vien_ten'], [])

    def test_model_khong_duoc_xoa_ung_vien_hanh_chinh(self):
        class Extractor:
            bao_ve_chi_tiet = False
            ma_bam = 'independent_fixture'

            def chuan_bi(self, tokens):
                labels = ['O'] * len(tokens)
                labels[:4] = ['B-duong', 'I-duong', 'I-duong', 'I-duong']
                return NguCanhCRF(tokens, labels, [.5] * len(tokens))
        text = 'Đường Lê Đại Hành, Phường Lê Đại Hành, Hà Nội'
        old = BoChuanHoa(danh_muc=self.base.danh_muc, bo_tach=Extractor(), bao_ve_duong=True)
        new = self.model(bo_tach=Extractor(), bao_ve_duong=True)
        old_candidates = old.tao_gia_thuyet(text)[1]
        candidates = new.tao_gia_thuyet(text)[1]
        inside = lambda u: 1 <= u.bat_dau and u.ket_thuc <= 4 and not u.co_tien_to
        self.assertFalse(any(inside(u) for u in old_candidates))
        self.assertTrue(any(inside(u) for u in candidates))
        self.assertTrue(all(u in candidates for u in old_candidates))
        r = new.chuan_hoa(text)
        self.assertTrue(r.thong_ke['hop_dong']['xung_dot_model_hanh_chinh'])
        evidence = r.thong_ke['hop_dong']
        self.assertEqual(len(evidence['gia_thuyet_da_xet']), evidence['so_gia_thuyet_da_xet'])
        self.assertEqual(evidence['quan_sat_model_truoc_ghep'][0]['doan_goc'], 'Đường Lê Đại Hành')
        self.assertEqual(evidence['chi_tiet_khi_khong_chon_hanh_chinh']['duong'], 'Đường Lê Đại Hành')

    def test_tien_to_telex_khong_gia_lam_dinh_dang_don_thuan(self):
        # Gán span rõ ràng để kiểm riêng hợp đồng, không phụ thuộc đoán của model.
        class Extractor:
            bao_ve_chi_tiet = False
            ma_bam = 'fixture'
            def chuan_bi(self, tokens):
                labels = ['B-duong'] + ['I-duong'] * (len(tokens)-1)
                return NguCanhCRF(tokens, labels, [.5]*len(tokens))
        r = self.model(bo_tach=Extractor()).chuan_hoa('dduwowngf Zeta Omega')
        op = r.thong_ke['hop_dong']['truong']['duong']['thao_tac'][0]
        self.assertEqual(op['loai'], 'giai_nghia_tien_to_telex')
        self.assertEqual(op['gia_thuyet_giu_chu_goc'], 'dduwowngf Zeta Omega')

    def test_nhieu_thu_tu_NFD_so_nha_va_ten_chua_biet(self):
        model = self.model()
        cases = 0
        for road, number, reverse, nfd in itertools.product(
            ['Hải Âu', 'Hoa Sen', 'Sao Mai'], ['17C', '21/4B'], [False, True], [False, True]):
            chunks = [f'Số {number}, Đường {road}', 'Thành phố Hà Nội']
            raw = ', '.join(reversed(chunks) if reverse else chunks)
            if nfd: raw = unicodedata.normalize('NFD', raw)
            r = model.chuan_hoa(raw)
            self.assertEqual(r.so_nha, 'Số ' + number)
            self.assertEqual(r.duong, 'Đường ' + road)
            self.assertEqual(r.ma_tinh, '01')
            self.assertTrue(r.thong_ke['hop_dong']['gia_thuyet_gan'])
            occupied = set()
            for span in r.dau_vet:
                a, b = span['ky_tu_bat_dau'], span['ky_tu_ket_thuc']
                self.assertEqual(raw[a:b], span['doan_goc'])
                self.assertFalse(occupied.intersection(range(a, b)))
                occupied.update(range(a,b))
            json.dumps(asdict(r), ensure_ascii=False)
            cases += 1
        self.assertEqual(cases, 24)

    def test_rong_va_goi_lap_khong_roi_trang_thai(self):
        model = self.model()
        self.assertEqual(model.chuan_hoa('').dia_chi_chuan, '')
        first = asdict(model.chuan_hoa('Số 17C, Đường Sao Mai, Thành phố Hà Nội'))
        model.chuan_hoa('Số 21/4B, Đường Hải Âu')
        self.assertEqual(first, asdict(model.chuan_hoa('Số 17C, Đường Sao Mai, Thành phố Hà Nội')))


if __name__ == '__main__':
    unittest.main()
