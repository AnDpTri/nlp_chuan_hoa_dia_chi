"""Synthetic fixtures for candidate-feature leakage: no real addresses involved."""
import random
import unittest
from dataclasses import dataclass

from src.lien_ket_v1.du_lieu_linking import LinkingSampleBuilder, choose_gold_linking_candidate
from src.danh_muc import DanhMuc


@dataclass(frozen=True)
class Candidate:
    cay: str
    ma: str
    cap: str
    ten: str


class TinyCatalogue:
    def __init__(self):
        self.units = [
            Candidate("cu", "00001", "xa", "Bình An"),
            Candidate("cu", "00002", "xa", "Bình An"),
            Candidate("cu", "00003", "xa", "An Bình"),
            Candidate("moi", "00004", "xa", "Tân An"),
        ]
        self.don_vi = {(u.cay, u.ma): u for u in self.units}
        self.doi_chieu = {"00001": [("00004", "Nhập toàn bộ")]}
    def dich_tinh(self, cay, ma):
        return frozenset()


class TestLinkingDataLeakage(unittest.TestCase):
    def setUp(self):
        self.dm = TinyCatalogue()
        self.builder = LinkingSampleBuilder(self.dm)

    def test_features_do_not_encode_binary_label(self):
        first, same_name = self.dm.units[:2]
        self.assertEqual(
            self.builder.observable_features("Bình An", first),
            self.builder.observable_features("Bình An", same_name),
        )
        self.assertEqual(self.builder.observable_features("Bình An", first)[-1], 0.0)

    def test_same_name_hard_negative_not_separated_by_label_features(self):
        random.seed(7)
        first = self.dm.units[0]
        sample = self.builder.create_linking_instance("Bình An", ("Bình An", 0, 7), first)
        positives = [c for c in sample["candidates"] if c["is_positive"]]
        same_name_negatives = [c for c in sample["candidates"]
                               if not c["is_positive"] and c["ten"] == first.ten]
        self.assertEqual(len(positives), 1)
        self.assertTrue(same_name_negatives)
        self.assertEqual(positives[0]["geo_features"],
                         same_name_negatives[0]["geo_features"])
        self.assertEqual(len({(c["cay"], c["ma"]) for c in sample["candidates"]}),
                         len(sample["candidates"]))

    def test_default_catalogue_mapping_loaded(self):
        old, new = self.dm.units[0], self.dm.units[3]
        self.assertTrue(self.builder.is_equivalent_target(old, new))
        self.assertFalse(self.builder.is_equivalent_target(self.dm.units[1], new))

    def test_gold_candidate_uses_reference_code_not_lookup_order(self):
        left, right = self.dm.units[:2]
        lookup = {"bình an": [left, right]}
        chosen = choose_gold_linking_candidate(
            "Bình An", "xa", {"ma_xa_cu": right.ma}, lookup
        )
        self.assertEqual(chosen.ma, right.ma)
        # Không có mã hoặc có hai mã hợp lệ -> không tự chọn.
        self.assertIsNone(choose_gold_linking_candidate("Bình An", "xa", {}, lookup))
        self.assertIsNone(choose_gold_linking_candidate(
            "Bình An", "xa", {"ma_xa_cu": right.ma, "ma_xa": left.ma},
            {"bình an": [right, Candidate("moi", left.ma, "xa", left.ten)]}
        ))

    def test_real_catalogue_cross_era_mapping(self):
        dm = DanhMuc()
        builder = LinkingSampleBuilder(dm)
        old_id = next(k for k, v in dm.doi_chieu.items() if len(v) == 1)
        new_id = dm.doi_chieu[old_id][0][0]
        self.assertTrue(builder.is_equivalent_target(dm.lay("cu", old_id),
                                                      dm.lay("moi", new_id)))


if __name__ == "__main__":
    unittest.main()
