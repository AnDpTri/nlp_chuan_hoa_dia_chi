"""Regression tests on administrative mapping, without user/test addresses."""
import unittest
from types import SimpleNamespace

from src.danh_muc import DanhMuc
from src.chuyen_doi import sang_cay_moi
from src.tien_xu_ly import bo_dau


class TestSplitWardPolicy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dm = DanhMuc()

    @staticmethod
    def path(old_ward):
        return SimpleNamespace(ung_vien=[
            SimpleNamespace(cay="cu", ma=old_ward, cap="xa")
        ])

    def test_multi_target_must_not_auto_select_by_same_name(self):
        example = None
        for old_code, links in self.dm.doi_chieu.items():
            target_codes = {m for m, _ in links}
            if len(target_codes) < 2:
                continue
            old_name = bo_dau(self.dm.lay("cu", old_code).ten.casefold())
            same_name = [
                new_code for new_code in target_codes
                if bo_dau(self.dm.lay("moi", new_code).ten.casefold()) == old_name
            ]
            if len(same_name) == 1:
                example = old_code
                break
        self.assertIsNotNone(example, "Fixture needs one real split ward with a same-named target")
        new_ward, _, warnings = sang_cay_moi(self.path(example), {}, self.dm)
        self.assertEqual(new_ward, "")
        self.assertIn("xa_bi_chia", warnings)

    def test_single_target_still_maps(self):
        for old_code, links in self.dm.doi_chieu.items():
            targets = {m for m, _ in links}
            if len(targets) == 1:
                expected = next(iter(targets))
                actual, _, warnings = sang_cay_moi(self.path(old_code), {}, self.dm)
                self.assertEqual(actual, expected)
                self.assertNotIn("xa_bi_chia", warnings)
                return
        self.fail("No unique mapping fixture")


if __name__ == "__main__":
    unittest.main()
