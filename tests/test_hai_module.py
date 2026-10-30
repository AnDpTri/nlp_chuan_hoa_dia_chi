"""Kiểm thử cấu trúc và tính đúng đắn của refactor hai module: tien_xu_ly và chuyen_doi."""

import ast
import importlib
from pathlib import Path
import unittest

from src.danh_muc import DanhMuc
from src.kieu_du_lieu import DiaChiSach, KetQua
from src.tien_xu_ly.lam_sach import BoLamSach
from src.chuyen_doi import chuyen_doi
from src.chuan_hoa import BoChuanHoa


class TestHaiModule(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.danh_muc = DanhMuc()
        cls.bo_lam_sach = BoLamSach(danh_muc=cls.danh_muc)
        cls.bo_chuan_hoa = BoChuanHoa(danh_muc=cls.danh_muc)
        cls.dia_chi_mau = "Số 12 Đường Lê Lợi, Phường Trúc Bạch, Quận Ba Đình, Hà Nội"

    def test_1_bo_lam_sach(self):
        """(1) BoLamSach.lam_sach(...) -> DiaChiSach có duong, so_nha, đơn vị cấp xã đúng."""
        sach = self.bo_lam_sach.lam_sach(self.dia_chi_mau)
        self.assertIsInstance(sach, DiaChiSach)
        self.assertEqual(sach.duong, "Đường Lê Lợi")
        self.assertEqual(sach.so_nha, "Số 12")
        self.assertIsNotNone(sach.don_vi_xa)
        self.assertEqual(sach.don_vi_xa.ma, "00004")
        self.assertEqual(sach.ma_xa, "00004")
        self.assertIn("Trúc Bạch", sach.xa)

    def test_2_chuyen_doi(self):
        """(2) chuyen_doi(DiaChiSach, danh_muc) cho xã Trúc Bạch cũ ra Phường Ba Đình mới (mã 00004)."""
        sach = self.bo_lam_sach.lam_sach(self.dia_chi_mau)
        kq = chuyen_doi(sach, self.danh_muc)
        self.assertIsInstance(kq, KetQua)
        self.assertEqual(kq.xa_phuong, "Phường Ba Đình")
        self.assertEqual(kq.ma_xa, "00004")

    def test_3_chuyen_doi_khong_import_tien_xu_ly(self):
        """(3) src/chuyen_doi/*.py không import module tiền xử lý (ast)."""
        cd_dir = Path(__file__).resolve().parent.parent / "src" / "chuyen_doi"
        for py_path in cd_dir.glob("*.py"):
            tree = ast.parse(py_path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    mod = node.module or ""
                    self.assertFalse("tien_xu_ly" in mod, f"{py_path.name} import {mod}")
                elif isinstance(node, ast.Import):
                    for a in node.names:
                        self.assertFalse("tien_xu_ly" in a.name, f"{py_path.name} import {a.name}")

    def test_4_tien_xu_ly_khong_import_chuyen_doi(self):
        """(4) tien_xu_ly không import chuyen_doi (ast)."""
        tx_dir = Path(__file__).resolve().parent.parent / "src" / "tien_xu_ly"
        for py_path in tx_dir.rglob("*.py"):
            tree = ast.parse(py_path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    mod = node.module or ""
                    self.assertFalse("chuyen_doi" in mod, f"{py_path.name} import {mod}")
                elif isinstance(node, ast.Import):
                    for a in node.names:
                        self.assertFalse("chuyen_doi" in a.name, f"{py_path.name} import {a.name}")

    def test_5_chuan_hoa_bang_ghep_tay(self):
        """(5) BoChuanHoa().chuan_hoa(chuỗi trên) == ghép tay chuyen_doi(lam_sach(...))."""
        kq_chuan_hoa = self.bo_chuan_hoa.chuan_hoa(self.dia_chi_mau)
        sach = self.bo_chuan_hoa.bo_lam_sach.lam_sach(self.dia_chi_mau)
        kq_ghep_tay = chuyen_doi(sach, self.bo_chuan_hoa.danh_muc)
        self.assertEqual(kq_chuan_hoa, kq_ghep_tay)

    def test_6_shim_bi_danh(self):
        """(6) Mỗi shim bí danh: module cũ is module mới."""
        shims = [
            ("src.char_cnn", "src.tien_xu_ly.char_cnn"),
            ("src.chuan_ten_duong", "src.tien_xu_ly.chuan_ten_duong"),
            ("src.crf_chi_tiet", "src.tien_xu_ly.crf_chi_tiet"),
            ("src.dinh_dang", "src.tien_xu_ly.dinh_dang"),
            ("src.duong_dan", "src.tien_xu_ly.duong_dan"),
            ("src.giai_ma", "src.tien_xu_ly.giai_ma"),
            ("src.hop_dong", "src.tien_xu_ly.hop_dong"),
            ("src.ngu_canh_neural", "src.tien_xu_ly.ngu_canh_neural"),
            ("src.nhan", "src.tien_xu_ly.nhan"),
            ("src.phuc_hoi_duong", "src.tien_xu_ly.phuc_hoi_duong"),
            ("src.quy_tac", "src.tien_xu_ly.quy_tac"),
            ("src.tach_phan_con", "src.tien_xu_ly.tach_phan_con"),
            ("src.tim_kiem", "src.tien_xu_ly.tim_kiem"),
            ("src.tra_cuu_neural", "src.tien_xu_ly.tra_cuu_neural"),
            ("src.videberta", "src.tien_xu_ly.videberta"),
            ("src.xep_hang", "src.tien_xu_ly.xep_hang"),
            ("src.lien_ket_v1.adapter_linking", "src.tien_xu_ly.lien_ket_v1.adapter_linking"),
            ("src.lien_ket_v1.cache_ung_vien", "src.tien_xu_ly.lien_ket_v1.cache_ung_vien"),
            ("src.lien_ket_v1.du_lieu_linking", "src.tien_xu_ly.lien_ket_v1.du_lieu_linking"),
            ("src.lien_ket_v1.mo_hinh_linking", "src.tien_xu_ly.lien_ket_v1.mo_hinh_linking"),
        ]
        for old_name, new_name in shims:
            old_mod = importlib.import_module(old_name)
            new_mod = importlib.import_module(new_name)
            self.assertIs(old_mod, new_mod, f"Module {old_name} is not {new_mod}")


if __name__ == "__main__":
    unittest.main()
