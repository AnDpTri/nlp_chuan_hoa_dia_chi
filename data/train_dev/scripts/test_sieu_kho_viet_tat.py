"""Contract checks for the synthetic hard-abbreviation TRAIN-only release."""
import csv
import json
import unittest
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "data/train_dev/bo_sung_v3_viet_tat_sieu_kho"


def read_csv(p):
    with p.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


class TestHardAbbreviations(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows=read_csv(OUT/"train_abbreviation_extreme.csv")
        cls.abstain=read_csv(OUT/"contrast_abstain.csv")
        cls.meta=[json.loads(t) for t in (OUT/"source_spans_and_family.jsonl")
                  .read_text(encoding="utf-8").splitlines() if t]
        cls.manifest=json.loads((OUT/"manifest.json").read_text(encoding="utf-8"))
        cls.old=read_csv(ROOT/"data/clean/cu_tinh_huyen_xa.csv")
        cls.new={r["ma_xa"]:r for r in read_csv(ROOT/"data/clean/moi_tinh_xa.csv")}
        cls.prov={r["ma_tinh"]:r for r in read_csv(ROOT/"data/clean/moi_tinh.csv")}
        cls.mp=defaultdict(set)
        for m in read_csv(ROOT/"data/clean/doi_chieu_xa_cu_moi.csv"):
            if m["ma_xa_cu"]:
                cls.mp[m["ma_xa_cu"]].add(m["ma_xa_moi"])

    def test_seed_and_canonical(self):
        seed=[r for r in self.rows if r["dau_vao"] == "x5,mh,ml,nd"]
        self.assertEqual(len(seed),1)
        r=seed[0]
        self.assertEqual(r["thon_xom"],"Xóm 5")
        self.assertEqual((r["ma_xa"],r["ma_tinh"]),("13708","37"))
        self.assertEqual(r["dia_chi_chuan"],
                         "Xóm 5, Phường Mỹ Lộc, Tỉnh Ninh Bình")
        self.assertEqual((r["ma_xa_cu"],r["ma_huyen_cu"],r["ma_tinh_cu"]),
                         ("","","36"))

    def test_no_dangling_codes(self):
        for r in self.rows:
            self.assertIn(r["ma_xa"],self.new)
            self.assertEqual(r["ma_tinh"],self.new[r["ma_xa"]]["ma_tinh"])
            self.assertIn(r["ma_tinh"],self.prov)
            if r["ma_xa_cu"]:
                self.assertEqual(self.mp[r["ma_xa_cu"]],{r["ma_xa"]})

    def test_sources_and_offsets(self):
        self.assertEqual(len(self.rows),len(self.meta))
        metas={r["id"]:r for r in self.meta}
        self.assertEqual({r["id"] for r in self.rows},set(metas))
        for r in self.rows:
            m=metas[r["id"]]
            self.assertEqual(m["training_partition"],"train_only")
            self.assertTrue(m["family_id"])
            for s in m["spans"]:
                self.assertEqual(r["dau_vao"][s["start"]:s["end"]],s["surface"])

    def test_single_family_of_user_example(self):
        metas={r["id"]:r for r in self.meta}
        families={metas[r["id"]]["family_id"] for r in self.rows
                  if r["nguon_du_lieu"]=="user_temporal_alias"}
        self.assertEqual(families,{"FAM_USER_MH_ML_ND_01"})
        self.assertEqual(
            len({metas[r["id"]]["family_id"] for r in self.rows
                 if r["nguon_du_lieu"]=="synthetic_clean_catalogue_chain"}),120)

    def test_abstain_does_not_claim_canonical_label(self):
        self.assertEqual(len(self.abstain),20)
        for r in self.abstain:
            self.assertEqual(r["decision"],"ABSTAIN")
            self.assertFalse(r["ma_xa"])
            self.assertFalse(r["ma_tinh"])
            self.assertEqual(r["training_partition"],
                             "contrast_only_not_canonical_training")

    def test_manifest_no_direct_overlap(self):
        self.assertEqual(self.manifest["overlap_by_normalized_input"],{})
        self.assertEqual(self.manifest["positive_rows"],len(self.rows))
        self.assertEqual(self.manifest["abstain_contrast"],len(self.abstain))


if __name__=="__main__":
    unittest.main()
