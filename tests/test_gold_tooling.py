"""Tooling-only tests; no external models/APIs, no TEST labels read."""
import copy,json,math,sys,unittest
from collections import Counter,defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
GOLD=ROOT/"data/gold"
sys.path.insert(0,str(GOLD))
from gold_common import validate_annotation,load_sample,source_keys,FIELDS,AUDIT
from kiem_nhan import validate_bundle
from dong_thuan import combine, fleiss_kappa
from uoc_luong_sai_so import cp_upper,estimate
from anh_xa_hanh_chinh import Mapper,bare
from chon_mau import load_exclusions,draw,serialize,sha256
from kiem_ro_ri_doc_lap import scan as independent_leakage_scan

def row(text="12 Trần Phú, Hà Nội",id="a"):
    return {"id":id,"dau_vao":text,
            "spans":[{"truong":"so_nha","start":0,"end":2,"van_ban":"12"},
                     {"truong":"duong","start":3,"end":11,"van_ban":"Trần Phú"}],
            "abstain":False,"ly_do_abstain":""}

class SchemaTests(unittest.TestCase):
    def test_valid(self):
        self.assertFalse(validate_annotation(row()))
    def test_offset_out_of_bounds(self):
        r=row();r["spans"][0]["end"]=100
        self.assertTrue(any("offset" in x for x in validate_annotation(r)))
    def test_overlap(self):
        r=row();r["spans"][1]["start"]=1
        self.assertTrue(any("chồng" in x for x in validate_annotation(r)))
    def test_text_mismatch(self):
        r=row();r["spans"][0]["van_ban"]="15"
        self.assertTrue(any("khớp" in x for x in validate_annotation(r)))
    def test_forbid_model_codes(self):
        r=row();r["ma_xa"]="fake"
        self.assertTrue(any("Khóa không" in x for x in validate_annotation(r)))
    def test_abstain_reason_required(self):
        r=row();r["abstain"]=True
        self.assertTrue(validate_annotation(r))
    def test_missing_sample_member(self):
        bundle={"bo_gan":"A","nhan":[row()]}
        self.assertTrue(validate_bundle(bundle,{"a":bundle["nhan"][0]["dau_vao"],"b":"x"}))

class ConsensusTests(unittest.TestCase):
    def b(self,name,rs):
        return {"bo_gan":name,"nhan":rs}
    def test_complete_consensus(self):
        out,queue=combine([self.b("A",[row()]),self.b("B",[row()])])
        self.assertEqual(out["nhat_tri_tat_ca"],1)
        self.assertEqual(queue,[])
        self.assertEqual(out["thong_ke_theo_truong"]["duong"]["ty_le_nhat_tri"],1.)
    def test_disagreement(self):
        other=row()
        other["spans"][1]={"truong":"duong","start":3,"end":7,"van_ban":"Trần"}
        out,queue=combine([self.b("A",[row()]),self.b("B",[other])])
        self.assertEqual(out["nhat_tri_tat_ca"],0)
        self.assertTrue(any(x["truong"]=="duong" for x in queue))
    def test_missing_id(self):
        with self.assertRaisesRegex(ValueError,"Missing/extra"):
            combine([self.b("A",[row()]),self.b("B",[row(),row(id="b")])])
    def test_duplicate_annotator_id(self):
        with self.assertRaises(ValueError):
            combine([self.b("A",[row()]),self.b("A",[row()])])
    def test_kappa(self):
        self.assertAlmostEqual(fleiss_kappa([["A","A"],["B","B"]]),1.)
        self.assertAlmostEqual(fleiss_kappa([["A","B"],["B","A"]]),-1.)

class IntervalTests(unittest.TestCase):
    def test_zero_out_of_150(self):
        self.assertAlmostEqual(cp_upper(0,150),0.01977,delta=.00025)
    def test_three_out_of_150(self):
        self.assertAlmostEqual(cp_upper(3,150),0.051,delta=.004)
    def test_missing_human_marks_rejected(self):
        with self.assertRaises(ValueError):
            estimate([{"id":"a","truong":"so_nha","dung_sai":""}])
    def test_all_fields_union(self):
        rows=[{"id":"a","truong":field,"dung_sai":"sai" if field=="duong" else "dung"}
              for field in FIELDS]
        out=estimate(rows)
        self.assertEqual(out["all_fields"]["errors"],1)

class MappingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mapper=Mapper()
    def mark(self,field,text):
        return [{"truong":field,"van_ban":text,"start":0,"end":len(text)}]
    def test_unique_ward(self):
        m=self.mapper
        # Search by actual names, not guessed administrative codes.
        for name,units in m.wards.items():
            targets=set().union(*(m.ward_targets(u) for u in units))
            if len(targets)==1 and any(u.cay=="moi" for u in units):
                out=m.admin_from_spans(self.mark("xa",name))
                if out["ma_xa"]==next(iter(targets)):
                    self.assertEqual(out["ma_xa"],next(iter(targets)))
                    return
        self.fail("No unambiguous real ward found")
    def test_split_ward(self):
        m=self.mapper
        for name,units in m.wards.items():
            if any(u.cay=="cu" and len(m.ward_targets(u))>1 for u in units):
                out=m.admin_from_spans(self.mark("xa",name))
                if out["xa_bi_chia"]:
                    self.assertEqual(out["ma_xa"],"")
                    self.assertGreaterEqual(len(out["ung_vien_ma_xa"]),2)
                    return
        self.fail("No split ward found")
    def test_homonym_without_province(self):
        m=self.mapper
        for name,units in m.wards.items():
            if len(set().union(*(m.ward_targets(u) for u in units)))>1:
                out=m.admin_from_spans(self.mark("xa",name))
                if not out["xa_bi_chia"]:
                    self.assertEqual(out["ma_xa"],"")
                    return
        self.fail("No unambiguous homonym case found")
    def test_missing_province_no_invent(self):
        out=self.mapper.admin_from_spans([])
        self.assertEqual(out["ma_tinh"],"")
        self.assertEqual(out["ma_xa"],"")
        self.assertTrue(out["abstain"])

    def test_homonym_with_explicit_province(self):
        m=self.mapper
        for name,units in m.wards.items():
            targets=set().union(*(m.ward_targets(u) for u in units))
            if len(targets)<2: continue
            for ward in units:
                if ward.cay!="moi": continue
                province=m.dm.lay("moi",ward.ma_cha)
                spans=self.mark("xa",name)+self.mark("tinh",province.ten)
                result=m.admin_from_spans(spans)
                if result["ma_xa"]==ward.ma:
                    self.assertEqual(result["ma_xa"],ward.ma)
                    self.assertEqual(result["ma_tinh"],province.ma)
                    return
        self.fail("No province-resolvable real homonym found")

class LeakageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.samples=load_sample()
        cls.groups,_=load_exclusions()
    def test_all_800_unique_and_zero_overlap_per_source_three_keys(self):
        self.assertEqual(len(self.samples),800)
        local={k:set() for k in ("text","osm","masked")}
        for r in self.samples:
            keys={"text":AUDIT.normalize(r["dau_vao"]),
                  "osm":AUDIT.osm_identity(r["nguon"]),
                  "masked":AUDIT.masked_family(r["dau_vao"])}
            for key,value in keys.items():
                if not value: continue
                self.assertNotIn(value,local[key])
                local[key].add(value)
                for group,buckets in self.groups.items():
                    self.assertNotIn(value,buckets[key],msg=group+"/"+key)
    def test_independent_recursive_leakage_audit(self):
        self.assertEqual(independent_leakage_scan()["status"],"PASS")

    def test_deterministic_regeneration_sha256(self):
        rows,_=draw()
        actual=serialize(rows)
        saved=(GOLD/"mau_ung_vien.csv").read_bytes()
        self.assertEqual(actual,saved)
        self.assertEqual(__import__("hashlib").sha256(saved).hexdigest(),
                         "2d0284b46f6a082efd8fcf020d72bfa1e0b31e0e11b3f7cf5cf5c63ca9c3006b")

if __name__=="__main__":unittest.main()
