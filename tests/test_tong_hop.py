"""Independent synthetic-tooling tests, including mock annotators and leakage.
These tests NEVER contact models, use TEST labels, or tune from scores.
"""
from __future__ import annotations
import csv,hashlib,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/"data/gold"
HERE=BASE/"tong_hop"
sys.path.insert(0,str(HERE))
sys.path.insert(0,str(BASE))
from gold_common import FIELDS,validate_annotation,AUDIT,sha256
from sinh_tong_hop import synthetic,csv_bytes
from kiem_ro_ri_tong_hop import run as independent_scan
from score_tong_hop import compare,read_and_combine,prepare_refs

def fixture():
    example="Số 11, Đường X, Xã Y, Tỉnh Z"
    specs=[
        ("so_nha","Số 11"),("duong","Đường X"),
        ("xa","Xã Y"),("tinh","Tỉnh Z")
    ]
    spans=[]
    for field,value in specs:
        begin=example.index(value)
        spans.append({"truong":field,"start":begin,"end":begin+len(value),
                      "van_ban":value})
    refs={}
    rows=[]
    for n,group in enumerate(("a","b","c"),1):
        ident=f"UNIT_{n:04d}"
        refs[ident]={"id":ident,"dau_vao":example,"nhom":group,
                     "spans":spans,"ma_xa":"M99","ma_tinh":"P88",
                     "khong_xac_dinh":False}
        rows.append({"id":ident,"dau_vao":example,
                     "spans":[dict(s) for s in spans],
                     "abstain":False,"ly_do_abstain":""})
    return refs,rows

class DummyMapper:
    def admin_from_spans(self,spans):
        return {"ma_xa":"M99" if any(s["truong"]=="xa" for s in spans) else "",
                "ma_tinh":"P88" if any(s["truong"]=="tinh" for s in spans) else ""}

class ScoreTests(unittest.TestCase):
    def test_fake_perfect(self):
        refs,rows=fixture()
        metric=compare({"bo_gan":"fake_correct","nhan":rows},refs,mapper=DummyMapper())
        self.assertEqual(metric["all"]["all_six_correct"],3)
        self.assertEqual(metric["all"]["sure_wrong"],0)
        self.assertEqual(metric["all"]["full_span_correct"],3)
        for field in ("so_nha","ngo_ngach_hem","thon_xom","duong","ma_xa","ma_tinh"):
            self.assertEqual(metric["all"]["field"][field]["correct"],3)
    def test_fake_wrong_all(self):
        refs,rows=fixture()
        for item in rows:item["spans"]=[]
        metric=compare({"bo_gan":"fake_wrong","nhan":rows},refs,mapper=DummyMapper())
        self.assertEqual(metric["all"]["all_six_correct"],0)
        self.assertEqual(metric["all"]["sure_wrong"],3)
        self.assertEqual(metric["all"]["sure_wrong_pct"],100)
    def test_fake_abstain_all(self):
        refs,rows=fixture()
        for item in rows:
            item["abstain"]=True
            item["ly_do_abstain"]="Không chắc (giả lập)"
        metric=compare({"bo_gan":"fake_abstain","nhan":rows},refs,mapper=DummyMapper())
        self.assertEqual(metric["all"]["abstain"],3)
        self.assertEqual(metric["all"]["abstain_pct"],100)
        self.assertEqual(metric["all"]["sure_wrong"],0)
    def test_ambiguous_safe_abstain_and_unsafe_claim(self):
        refs,rows=fixture()
        refs[rows[0]["id"]]["khong_xac_dinh"]=True
        rows[0]["abstain"]=True
        rows[0]["ly_do_abstain"]="Không đủ bằng chứng"
        ok=compare({"bo_gan":"fake","nhan":rows},refs,mapper=DummyMapper())
        self.assertEqual(ok["all"]["abstain_correct_ambiguous"],1)
        rows[0]["abstain"]=False
        rows[0]["ly_do_abstain"]=""
        bad=compare({"bo_gan":"fake","nhan":rows},refs,mapper=DummyMapper())
        self.assertEqual(bad["all"]["sure_wrong"],1)
    def test_missing_member_fails(self):
        refs,rows=fixture()
        with self.assertRaisesRegex(ValueError,"Thiếu|thừa"):
            compare({"bo_gan":"fake","nhan":rows[:2]},refs,mapper=DummyMapper())

class GeneratedDatasetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.refs,cls.input_id=prepare_refs(HERE/"tong_hop_dap_an.json",
                                           HERE/"tong_hop_dau_vao.csv")
    def test_400_counts_and_masked_id_distinct(self):
        self.assertEqual(len(self.refs),400)
        self.assertEqual({g:sum(x["nhom"]==g for x in self.refs.values())
                           for g in ("a","b","c")},{"a":140,"b":140,"c":120})
        with (BASE/"mau_ung_vien.csv").open(encoding="utf-8-sig",newline="") as f:
            real_ids={r["id"] for r in csv.DictReader(f)}
        self.assertFalse(set(self.refs)&real_ids)
        self.assertTrue(all(x.startswith("UNGVIEN_") for x in self.refs))
    def test_known_construction_spans_exact_and_nonoverlap(self):
        for ref in self.refs.values():
            projection={k:ref[k] for k in ("id","dau_vao","spans")}
            projection.update(abstain=False,ly_do_abstain="")
            self.assertFalse(validate_annotation(projection),ref["id"])
            self.assertIsInstance(ref["khong_xac_dinh"],bool)
            if ref["so_ung_vien_xa"]!=1:
                self.assertEqual(ref["ma_xa"],"")
            if ref["khong_xac_dinh"]:
                self.assertTrue(ref["ly_do_mo_ho"])
            # A globally ambiguous address may still have a uniquely resolved
            # individual province/ward field: score abstain at row level.
    def test_fixed_seed_regenerates_identical_csv_hash(self):
        rows,_=synthetic()
        actual=csv_bytes(rows)
        self.assertEqual(actual,(HERE/"tong_hop_dau_vao.csv").read_bytes())
        self.assertEqual(hashlib.sha256(actual).hexdigest(),
          "91ad0115eed9c82448ba2949c526754335e66dcb8b107b845ced8bd3c01064a5")
    def test_independent_recursive_leakage_both_source_and_input(self):
        result=independent_scan()
        self.assertEqual(result["status"],"PASS",result)
        for data in result["per_source"].values():
            self.assertEqual(data["overlap_public"],0)
            self.assertEqual(data["overlap_origin"],0)
    def test_8_valid_blind_packages_50_each(self):
        folders=sorted((HERE/"goi_gan_nhan").glob("goi_*"))
        self.assertEqual(len(folders),8)
        ids=set()
        for folder in folders:
            with (folder/"dau_vao.csv").open(encoding="utf-8-sig",newline="") as f:
                records=list(csv.DictReader(f))
            self.assertEqual(len(records),50)
            self.assertTrue((folder/"PROMPT_GAN_NHAN.txt").is_file())
            ids.update(r["id"] for r in records)
        self.assertEqual(ids,set(self.refs))
    def test_24_mixed_blind_packages(self):
        dirs=sorted((HERE/"goi_tron_ung_vien_va_tong_hop").glob("goi_*"))
        self.assertEqual(len(dirs),24)
        for folder in dirs:
            with (folder/"dau_vao.csv").open(encoding="utf-8-sig",newline="") as f:
                self.assertEqual(len(list(csv.DictReader(f))),50)
            prompt=(folder/"PROMPT_GAN_NHAN.txt").read_text(encoding="utf8")
            self.assertNotIn("ma_xa_goc_bi_an",prompt)
            self.assertNotIn("chuoi_nguon_day_du",prompt)
    def test_all_eight_self_label_bundles_pass(self):
        paths=sorted(HERE.glob("codex_gpt_tong_hop_goi_*.json"))
        self.assertEqual(len(paths),8)
        bundle=read_and_combine(paths,self.input_id)
        self.assertEqual(len(bundle["nhan"]),400)
        self.assertEqual(bundle["bo_gan"],"codex_gpt")

if __name__=="__main__":unittest.main()
