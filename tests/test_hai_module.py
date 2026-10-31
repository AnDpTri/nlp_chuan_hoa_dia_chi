"""Kiểm thử cấu trúc và tính đúng đắn của refactor hai module: tien_xu_ly và chuyen_doi."""

import ast
from pathlib import Path
import unittest

from src.danh_muc import DanhMuc
from src.kieu_du_lieu import DiaChiSach, DonViNhan, KetQua
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
        self.assertIn(DonViNhan(cap="xa", ma="00004", cay="cu"), sach.don_vi)
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


if __name__ == "__main__":
    unittest.main()
