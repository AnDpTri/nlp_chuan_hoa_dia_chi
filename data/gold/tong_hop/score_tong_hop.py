"""Score one candidate AI annotator on fixed synthetic references.

Read TRUE answers only here, never in the annotator/converter path.
No API calls, no labels modified. Fails if prediction set incomplete/invalid.
Important: computed admin mapping is the frozen read-only Mapper, not AI-supplied codes.
"""
import argparse,csv,json,sys
from collections import Counter,defaultdict
from pathlib import Path
BASE=Path(__file__).resolve().parent
GOLD=BASE.parent
sys.path.insert(0,str(GOLD))
from kiem_nhan import validate_bundle,check_file
from anh_xa_hanh_chinh import Mapper
from gold_common import FIELDS,sha256

FIELDS_TO_SCORE=("so_nha","ngo_ngach_hem","thon_xom","duong","ma_xa","ma_tinh")
SOURCE_FIELDS=("so_nha","ngo_ngach_hem","thon_xom","duong")

def surface_spans(spans,field):
    return tuple(sorted((x["start"],x["end"],x["van_ban"]) for x in spans if x["truong"]==field))

def prepare_refs(ref_file,public_file):
    ref=json.loads(Path(ref_file).read_text(encoding="utf8"))
    if sha256(public_file)!=ref["sample_sha256"]:raise ValueError("Synthetic sample reference hash mismatch")
    with Path(public_file).open(encoding="utf-8-sig",newline="") as f:
        public=list(csv.DictReader(f))
    refs={x["id"]:x for x in ref["items"]}
    if len(public)!=len(refs) or len(refs)!=len(set(refs)):
        raise ValueError("Synthetic reference count mismatch")
    if {(x["id"],x["dau_vao"]) for x in public}!={(x["id"],x["dau_vao"]) for x in refs.values()}:
        raise ValueError("Synthetic public/private identity mismatch")
    return refs,{x["id"]:x["dau_vao"] for x in public}

def compare(candidate,refs,mapper=None):
    mapper=mapper or Mapper()
    errors=validate_bundle(candidate,{i:r["dau_vao"] for i,r in refs.items()})
    if errors:raise ValueError("Invalid or incomplete candidate labels: "+"; ".join(errors[:10]))
    scores={}
    for group in ("all","a","b","c"):
        scores[group]={"n":0,"abstain":0,"ambiguous":0,"abstain_correct_ambiguous":0,
                       "sure_wrong":0,"sure_correct":0,"full_span_correct":0,
                       "all_six_correct":0,"field":{k:Counter() for k in FIELDS_TO_SCORE},
                       "wrong_examples":[]}
    for row in candidate["nhan"]:
        ref=refs[row["id"]]
        groups=("all",ref["nhom"])
        mapped=mapper.admin_from_spans(row["spans"])
        comparisons={}
        for name in SOURCE_FIELDS:
            comparisons[name]=(surface_spans(row["spans"],name)==surface_spans(ref["spans"],name))
        comparisons["ma_xa"]=(mapped["ma_xa"]==ref["ma_xa"])
        comparisons["ma_tinh"]=(mapped["ma_tinh"]==ref["ma_tinh"])
        true_abstain=bool(ref["khong_xac_dinh"])
        sure=not row["abstain"]
        correct_all=all(comparisons.values())
        # For ambiguous input, claiming a sure answer is unsafe regardless of
        # whether an accidental match to an empty code happens.
        sure_wrong=sure and (not correct_all or true_abstain)
        for name in groups:
            s=scores[name]
            s["n"]+=1
            s["ambiguous"]+=int(true_abstain)
            s["abstain"]+=int(row["abstain"])
            s["abstain_correct_ambiguous"]+=int(row["abstain"] and true_abstain)
            s["sure_wrong"]+=int(sure_wrong)
            s["sure_correct"]+=int(sure and correct_all and not true_abstain)
            s["all_six_correct"]+=int(correct_all)
            s["full_span_correct"]+=int(all(comparisons[k] for k in SOURCE_FIELDS))
            for f,correct in comparisons.items():
                s["field"][f]["correct"]+=int(correct)
                s["field"][f]["wrong"]+=int(not correct)
            if sure_wrong and len(s["wrong_examples"])<6:
                s["wrong_examples"].append({"id":row["id"],"group":ref["nhom"],
                    "incorrect_fields":[k for k,c in comparisons.items() if not c],
                    "expected_abstain":true_abstain})
    clean={}
    for group,s in scores.items():
        n=s["n"]
        if not n:raise AssertionError("Empty generated group "+group)
        clean[group]={
            **{k:v for k,v in s.items() if k not in ("field",)},
            "abstain_pct":round(100*s["abstain"]/n,3),
            "ambiguous_pct":round(100*s["ambiguous"]/n,3),
            "abstain_on_ambiguous_pct":round(100*s["abstain_correct_ambiguous"]/s["ambiguous"],3)
                if s["ambiguous"] else None,
            "sure_wrong_pct":round(100*s["sure_wrong"]/n,3),
            "all_six_correct_pct":round(100*s["all_six_correct"]/n,3),
            "full_span_correct_pct":round(100*s["full_span_correct"]/n,3),
            "field":{f:{"correct":v["correct"],"wrong":v["wrong"],
                        "total":n,"correct_pct":round(100*v["correct"]/n,3)}
                     for f,v in s["field"].items()}}
    return clean

def read_and_combine(files,expected):
    all_rows=[]
    annotator=None
    for p in files:
        b,errors=check_file(p)
        if errors:raise ValueError(f"{p}: "+"; ".join(errors[:10]))
        if annotator is None:annotator=b["bo_gan"]
        elif annotator!=b["bo_gan"]:raise ValueError("Different annotator IDs")
        all_rows+=b["nhan"]
    bundle={"bo_gan":annotator,"nhan":all_rows}
    errors=validate_bundle(bundle,expected)
    if errors:raise ValueError("Inconsistent/incomplete eight packages: "+"; ".join(errors[:10]))
    return bundle

def main():
    a=argparse.ArgumentParser()
    a.add_argument("labels",nargs="+",type=Path)
    a.add_argument("--public",type=Path,default=BASE/"tong_hop_dau_vao.csv")
    a.add_argument("--answers",type=Path,default=BASE/"tong_hop_dap_an.json")
    a.add_argument("--out",type=Path)
    args=a.parse_args()
    refs,expected=prepare_refs(args.answers,args.public)
    bundle=read_and_combine(args.labels,expected)
    results=compare(bundle,refs)
    report={"kind":"synthetic_constructed_answers_NOT_HUMAN_GOLD",
            "annotator":bundle["bo_gan"],"public_sha256":sha256(args.public),
            "true_answers_only_used_during_scoring":True,"metrics":results}
    if args.out:
        if args.out.exists():raise FileExistsError(args.out)
        args.out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    print("SCORE_TONG_HOP",json.dumps({"annotator":bundle["bo_gan"],"metrics":results},
          ensure_ascii=False),flush=True)
if __name__=="__main__":main()
