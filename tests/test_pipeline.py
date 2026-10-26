import tempfile
import unicodedata
import unittest
import hashlib
import json
from dataclasses import asdict
from pathlib import Path

from src.chuan_hoa import BoChuanHoa
from src.cli import read_rows, write_rows
from src.tien_xu_ly import bo_dau, tach_token
from danh_gia.cham_diem import score


class PipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = BoChuanHoa()
        cls.d = cls.model.danh_muc

    def test_catalogue_and_2025_types(self):
        new = [u for u in self.d.don_vi.values() if u.cay == "moi"]
        self.assertEqual(sum(u.cap == "xa" for u in new), 3321)
        self.assertEqual(sum(u.cap == "tinh" for u in new), 34)
        for code in ["22", "24", "75"]:
            self.assertEqual(self.d.lay("moi", code).loai, "Tỉnh")
        for u in new:
            if u.cap == "xa":
                self.assertEqual(self.d.lay("moi", u.ma_cha).cap, "tinh")

    def test_pinned_catalogue_bytes(self):
        root = Path(__file__).resolve().parents[1]
        expected = json.loads(
            (root / "data/test/catalogue_manifest.json").read_text(encoding="utf-8")
        )
        actual = {
            k: hashlib.sha256((root / "data/clean" / k).read_bytes()).hexdigest()
            for k in expected
        }
        self.assertEqual(actual, expected)

    def test_spec_example_alias_and_street(self):
        r = self.model.chuan_hoa("12 ngo 5 tran thai tong cau giay hn")
        self.assertEqual(r.ma_xa, "00166")
        self.assertEqual(r.ma_tinh, "01")
        self.assertEqual(
            (r.so_nha, r.ngo_ngach_hem, r.duong),
            ("12", "Ngõ 5", "Đường Trần Thái Tông"),
        )
        self.assertNotIn("Quận", r.dia_chi_chuan)

    def test_unicode_and_fuzzy(self):
        original = "Phường Cầu Giấy, Hà Nội"
        a = self.model.chuan_hoa(original)
        for text in [unicodedata.normalize("NFD", original), bo_dau(original)]:
            self.assertEqual(self.model.chuan_hoa(text).ma_xa, a.ma_xa)
        r = self.model.chuan_hoa("Phường Cầu Giấ, Hà Nội")
        self.assertEqual(r.ma_xa, a.ma_xa)
        self.assertIn("sua_chinh_ta", r.canh_bao)

    def test_old_ward_unique(self):
        old = self.d.lay("cu", "00001")
        text = ", ".join(self.d.ten_day_du(u.cay, u.ma) for u in self.d.to_tien(old))
        r = self.model.chuan_hoa(text)
        self.assertEqual(r.ma_xa, "00097")
        self.assertEqual(r.ma_tinh, "01")
        self.assertNotIn("Quận", r.dia_chi_chuan)

    def test_old_split_is_not_guessed(self):
        old = self.d.lay("cu", "00007")
        text = ", ".join(self.d.ten_day_du(u.cay, u.ma) for u in self.d.to_tien(old))
        r = self.model.chuan_hoa(text)
        self.assertEqual(r.ma_xa, "")
        self.assertEqual(r.xa_phuong, "")
        self.assertIn("xa_bi_chia", r.canh_bao)
        self.assertEqual({v["ma_xa"] for v in r.ung_vien_xa}, {"00008", "00025"})

    def test_empty_street_only_missing_and_number(self):
        self.assertIn("dia_chi_rong", self.model.chuan_hoa("").canh_bao)
        street = self.model.chuan_hoa("Đường Lê Lợi")
        self.assertEqual((street.ma_xa, street.ma_tinh), ("", ""))
        province = self.model.chuan_hoa("Hà Nội")
        self.assertEqual(province.ma_xa, "")
        self.assertIn("thieu_xa", province.canh_bao)
        r = self.model.chuan_hoa("12/5 Đường Lê Lợi, Phường Cầu Giấy, Hà Nội")
        self.assertEqual((r.so_nha, r.ngo_ngach_hem), ("12", "Ngõ 5"))
        self.assertEqual(tach_token("p. 1, q. 2"), ["p", "1", ",", "q", "2"])

    def test_conflict_not_disguised_as_street(self):
        r = self.model.chuan_hoa("Phường Bến Thành, Hà Nội")
        self.assertIn("mau_thuan_hanh_chinh", r.canh_bao)
        self.assertNotIn("Hà Nội", r.duong)

    def test_ambiguous_ward_and_large_input(self):
        r = self.model.chuan_hoa("Xã Tân Phú")
        self.assertIn("mo_ho_hanh_chinh", r.canh_bao)
        self.assertGreater(len(r.ung_vien_xa), 1)
        with self.assertRaises(ValueError):
            self.model.chuan_hoa("abc " * 121)

    def test_csv_and_excel_preserve_string_codes(self):
        rows = [
            dict(id="0001", dau_vao="=1+1", **asdict(self.model.chuan_hoa("Hà Nội")))
        ]
        with tempfile.TemporaryDirectory() as directory:
            for suffix in ["csv", "xlsx"]:
                path = Path(directory) / ("out." + suffix)
                write_rows(path, rows)
                row = read_rows(path)[0]
                self.assertEqual(row["id"], "0001")
                self.assertEqual(row["ma_tinh"], "01")
                self.assertEqual(row["dau_vao"], "=1+1")

    def test_evaluation_requires_reviewed_labels(self):
        gold = [dict(id="001", trang_thai_nhan="tu_dong_khop", ma_xa="00001")]
        a = score(gold, [dict(id="001", ma_xa="00001")])
        self.assertEqual(a["status"], "awaiting_manual_review")
        self.assertIsNone(a["exact_match"])
        gold[0]["trang_thai_nhan"] = "da_duyet"
        b = score(gold, [])
        self.assertEqual(b["exact_match"], 0)
        self.assertEqual(b["missing_reviewed_predictions"], 1)
        self.assertEqual(score(gold, [dict(gold[0])])["exact_match"], 1)
        with self.assertRaises(ValueError):
            score(gold, gold * 2)


if __name__ == "__main__":
    unittest.main()
