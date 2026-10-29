"""Kiểm từ vựng tiền tố/role, không lấy ID hoặc địa danh lỗi dev làm luật."""
import unittest
from src.quy_tac import dang_go_telex, cac_tien_to, khop_chu_tien_to
from src.tien_xu_ly import token_co_vi_tri
from src.danh_muc import DanhMuc
from src.tim_kiem import dung_trie, sinh_ung_vien
from src.tim_kiem import bo_sung_tu_luoi_goc
from src.tien_xu_ly import Token
import unicodedata


class TelexPrefixTests(unittest.TestCase):
    def test_ma_hoa_tu_chuan(self):
        for word, expected in [('Phường','phuowngf'),('Huyện','huyeenj'),('Quận','quaanj'),
                               ('Tỉnh','tinhr'),('Thị','thij'),('Xã','xax')]:
            self.assertIn(expected, dang_go_telex(word))

    def test_tien_to_khong_phu_thuoc_ten_hoac_so(self):
        for prefix in ('phuowngf','phuwowngf'):
            for name in ('3','19','Hải Âu'):
                tokens=[t.chu for t in token_co_vi_tri(prefix+' '+name)]
                end,kind,spec=cac_tien_to(tokens)[0]
                self.assertEqual((end,kind,spec[0]),(1,'hanh_chinh',{'xa'}))

    def test_khong_fuzzy_tu_gan_giong_va_dau_mau_thuan(self):
        for word in ('phuowngs','phuowngfxyz','Phướng','Phượng'):
            self.assertFalse(khop_chu_tien_to(word,'phuong'))
        self.assertFalse(khop_chu_tien_to('Tô','to'))

    def test_so_dung_mot_minh_khong_tu_thanh_phuong(self):
        dm=DanhMuc();trie=dung_trie(dm)
        self.assertFalse(sinh_ung_vien(['3'],trie,False))
        raw=[t.chu for t in token_co_vi_tri('phuowngf 3')]
        candidates=sinh_ung_vien(raw,trie,False)
        self.assertTrue(candidates)
        self.assertTrue(all(u.cap=='xa' and u.co_tien_to for u in candidates))

    def test_ranh_gioi_model_khong_duoc_lam_mat_cach_chia_goc(self):
        dm=DanhMuc();trie=dung_trie(dm)
        for number in ('3','19'):
            raw='phuowngf '+number
            original=token_co_vi_tri(raw)
            refined=[Token(raw[:5],0,5),Token(raw[5:8],5,8),*original[1:]]
            old=sinh_ung_vien([t.chu for t in refined],trie,False)
            new,added=bo_sung_tu_luoi_goc(original,refined,trie,old)
            expected=sinh_ung_vien([t.chu for t in original],trie,False)
            self.assertTrue(added)
            for u in expected:
                self.assertTrue(any((v.cay,v.ma)==(u.cay,u.ma) and
                                    (refined[v.bat_dau].bat_dau,refined[v.ket_thuc-1].ket_thuc)==(0,len(raw)) for v in new))
            again,added=bo_sung_tu_luoi_goc(original,refined,trie,new)
            self.assertEqual(new,again);self.assertEqual(added,0)

    def test_chieu_offset_NFD(self):
        raw=unicodedata.normalize('NFD','Phường 3')
        original=token_co_vi_tri(raw);tok=original[0]
        refined=[Token(raw[:2],0,2),Token(unicodedata.normalize('NFC',raw[2:tok.ket_thuc]),2,tok.ket_thuc),original[1]]
        dm=DanhMuc();trie=dung_trie(dm)
        result,_=bo_sung_tu_luoi_goc(original,refined,trie,[])
        self.assertTrue(result)
        self.assertTrue(all(raw[refined[u.bat_dau].bat_dau:refined[u.ket_thuc-1].ket_thuc]==raw for u in result))

    def test_hau_to_hanh_chinh_tieng_anh(self):
        dm = DanhMuc()
        trie = dung_trie(dm)
        # Test commune postfix
        toks = [t.chu for t in token_co_vi_tri("Thai Hoa commune")]
        cands = sinh_ung_vien(toks, trie, False)
        xa_cands = [u for u in cands if u.cap == 'xa' and u.co_tien_to]
        self.assertTrue(xa_cands)
        self.assertEqual(xa_cands[0].bat_dau, 0)
        self.assertEqual(xa_cands[0].ket_thuc, 3)

        # Test district postfix
        toks = [t.chu for t in token_co_vi_tri("Lap Thach district")]
        cands = sinh_ung_vien(toks, trie, False)
        huyen_cands = [u for u in cands if u.cap == 'huyen' and u.co_tien_to]
        self.assertTrue(huyen_cands)
        self.assertEqual(huyen_cands[0].bat_dau, 0)
        self.assertEqual(huyen_cands[0].ket_thuc, 3)

        # Test province postfix
        toks = [t.chu for t in token_co_vi_tri("Vinh Phuc province")]
        cands = sinh_ung_vien(toks, trie, False)
        tinh_cands = [u for u in cands if u.cap == 'tinh' and u.co_tien_to]
        self.assertTrue(tinh_cands)
        self.assertEqual(tinh_cands[0].bat_dau, 0)
        self.assertEqual(tinh_cands[0].ket_thuc, 3)



if __name__=='__main__':unittest.main()
