"""Deterministic administrative code mapping from AI-marked spans, never AI-generated codes.
Conservative: conflicting era, homonyms and split wards yield empty code/abstain.
Read-only src.danh_muc.DanhMuc from the GOLD worktree.
"""
from __future__ import annotations
import argparse,json,re,sys
from collections import defaultdict
from pathlib import Path
from gold_common import ROOT,AUDIT
sys.path.insert(0,str(ROOT))
from src.danh_muc import DanhMuc

PREFIXES=("thanh pho","thi tran","thi xa","dac khu","phuong","huyen","quan","tinh","xa","tp","tt","tx","q","p")
def bare(t):
    n=AUDIT.normalize(t)
    for pref in PREFIXES:
        if n.startswith(pref+" "):return n[len(pref)+1:]
    return n

class Mapper:
    def __init__(self,clean=None):
        self.dm=DanhMuc(Path(clean or ROOT/"data/clean"))
        self.provinces=defaultdict(list)
        self.wards=defaultdict(list)
        self.districts=defaultdict(list)
        for (era,code),unit in self.dm.don_vi.items():
            keys={bare(unit.ten),bare(unit.loai+" "+unit.ten)}
            index=self.provinces if unit.cap=="tinh" else self.wards if unit.cap=="xa" else self.districts
            for key in keys:index[key].append(unit)
        self.province_alias={
            "hn":"ha noi","hcm":"ho chi minh","tphcm":"ho chi minh",
            "tp hcm":"ho chi minh","sai gon":"ho chi minh"}

    def province_targets(self,item):
        if item.cay=="moi":return {item.ma}
        return set(self.dm.dich_tinh(item.cay,item.ma))

    def ward_targets(self,item):
        return set(self.dm.dich_xa(item.cay,item.ma))

    def admin_from_spans(self,spans):
        labels=defaultdict(list)
        for s in spans:
            if s["truong"] in ("xa","huyen","tinh"): labels[s["truong"]].append(s["van_ban"])
        out={"ma_xa":"","ma_tinh":"","xa_bi_chia":False,
             "ung_vien_ma_xa":[],"abstain":False,"ly_do":[]}
        ps=[]
        for text in labels["tinh"]:
            term=self.province_alias.get(bare(text),bare(text))
            ps+=self.provinces.get(term,[])
        p_ids=set().union(*(self.province_targets(x) for x in ps)) if ps else set()
        if labels["tinh"] and not ps:out["ly_do"].append("tinh_khong_khop_danh_muc")
        if len(p_ids)>1:out["ly_do"].append("tinh_trung_ten_hoac_nhieu_dich")
        ds=[]
        for text in labels["huyen"]:ds+=self.districts.get(bare(text),[])
        if labels["huyen"] and not ds:out["ly_do"].append("huyen_khong_khop_danh_muc")
        if ds and p_ids:
            ds=[d for d in ds if self.province_targets(d)&p_ids]
        wards=[]
        for text in labels["xa"]:
            wards+=self.wards.get(bare(text),[])
        if labels["xa"] and not wards:out["ly_do"].append("xa_khong_khop_danh_muc")
        if p_ids:
            wards=[w for w in wards if self.province_targets(w)&p_ids]
        if ds:
            old_ds={d.ma for d in ds if d.cay=="cu"}
            def compatible(w):
                if w.cay=="cu":return w.ma_cha in old_ds
                return any(w.ma in self.dm.dich_xa("cu",x.ma)
                           for x in self.dm.don_vi.values()
                           if x.cay=="cu" and x.cap=="xa" and x.ma_cha in old_ds)
            wards=[w for w in wards if compatible(w)]
        all_targets=set().union(*(self.ward_targets(w) for w in wards)) if wards else set()
        out["ung_vien_ma_xa"]=sorted(all_targets)
        out["xa_bi_chia"]=any(len(self.ward_targets(w))>1 for w in wards if w.cay=="cu")
        if out["xa_bi_chia"]:
            out["ly_do"].append("xa_bi_chia")
        elif len(all_targets)==1:
            out["ma_xa"]=next(iter(all_targets))
        elif len(all_targets)>1:
            out["ly_do"].append("xa_trung_ten_khac_tinh_hoac_moc")
        if labels["xa"] and not all_targets:
            out["ly_do"].append("xa_khong_xac_dinh_duoc")
        # Province can be fixed from an explicit unique province mention, or
        # inferred only if all surviving ward/district candidates imply one province.
        implied=set(p_ids)
        if not implied and wards:
            implied=set().union(*(self.province_targets(w) for w in wards))
        if not implied and ds:
            implied=set().union(*(self.province_targets(d) for d in ds))
        if len(implied)==1:out["ma_tinh"]=next(iter(implied))
        elif len(implied)>1:out["ly_do"].append("tinh_khong_duy_nhat")
        elif not labels["tinh"]:out["ly_do"].append("thieu_tinh_khong_the_suy_ra")
        # Existing text may contradict catalogue; never silently choose another.
        if labels["tinh"] and not out["ma_tinh"]:
            out["ly_do"].append("khong_chot_duoc_tinh")
        out["ly_do"]=list(dict.fromkeys(out["ly_do"]))
        out["abstain"]=bool(out["ly_do"])
        return out

def main():
    p=argparse.ArgumentParser()
    p.add_argument("label_json",type=Path)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    from kiem_nhan import check_file
    source,errors=check_file(a.label_json)
    if errors:raise ValueError("Candidate labels invalid: "+str(errors[:10]))
    mapper=Mapper()
    mapped=[]
    for row in source["nhan"]:
        m=mapper.admin_from_spans(row["spans"])
        mapped.append({"id":row["id"],**m,
                       "abstain_bo_gan":row["abstain"],
                       "ly_do_abstain_bo_gan":row["ly_do_abstain"]})
    if a.output.exists():raise FileExistsError(str(a.output))
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(mapped,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("MAPPED_READONLY",len(mapped),"ABSTAIN",sum(x["abstain"] for x in mapped))
if __name__=="__main__":main()
