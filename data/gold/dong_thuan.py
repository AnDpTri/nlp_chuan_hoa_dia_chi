"""Strict multi-annotator field consensus; Fleiss kappa and human disagreement queue.
Does not assign or promote 'gold'. Completely independent label inputs required.
"""
import argparse,csv,json
from collections import Counter,defaultdict
from pathlib import Path
from gold_common import FIELDS,output_csv,output_json,load_sample
from kiem_nhan import check_file

def field_value(item,field):
    return tuple(sorted((s["start"],s["end"],s["van_ban"])
                        for s in item["spans"] if s["truong"]==field))

def fleiss_kappa(vectors):
    # Values per item, n raters, nominal categories; chance agreement from pooled marginals.
    if not vectors:return None
    n=len(vectors[0])
    if n<2:raise ValueError("Need >=2 annotators")
    k=len(vectors)
    counts=Counter(v for vct in vectors for v in vct)
    p_e=sum((v/(k*n))**2 for v in counts.values())
    p_o=sum((sum(c*(c-1) for c in Counter(v).values())/(n*(n-1))) for v in vectors)/k
    return None if 1-p_e<1e-12 else round((p_o-p_e)/(1-p_e),6)

def combine(bundles):
    if len(bundles)<2:raise ValueError("Requires >=2 independent annotators")
    checked=[]
    for b in bundles:
        from kiem_nhan import validate_bundle
        errors=validate_bundle(b)
        if errors:raise ValueError("; ".join(errors[:10]))
        checked.append({r["id"]:r for r in b["nhan"]})
    names=[b["bo_gan"] for b in bundles]
    if len(set(names))!=len(names):raise ValueError("Annotator name repeated; independence not verifiable")
    ids=set(checked[0])
    if any(set(data)!=ids for data in checked[1:]):
        raise ValueError("Missing/extra item between annotators")
    for key in ids:
        texts={table[key]["dau_vao"] for table in checked}
        if len(texts)!=1:raise ValueError("Input mismatch across annotators for "+key)
    stats={f:{"all_agree":0,"items":len(ids),"vectors":[]} for f in FIELDS}
    queue=[]
    records=[]
    for ident in sorted(ids):
        items=[table[ident] for table in checked]
        abstains=[(x["abstain"],x["ly_do_abstain"]) for x in items]
        any_abstain=any(x["abstain"] for x in items)
        all_agree=True
        per_field={}
        for f in FIELDS:
            values=[field_value(x,f) for x in items]
            agree=all(v==values[0] for v in values)
            stats[f]["all_agree"]+=int(agree)
            stats[f]["vectors"].append(values)
            per_field[f]=[{"start":a,"end":b,"van_ban":v} for a,b,v in values[0]] if agree else None
            if not agree:
                all_agree=False
                queue.append({"id":ident,"dau_vao":items[0]["dau_vao"],
                              "truong":f,**{name:json.dumps(v,ensure_ascii=False) for name,v in zip(names,values)}})
        if any_abstain or len(set(abstains))>1:
            all_agree=False
            queue.append({"id":ident,"dau_vao":items[0]["dau_vao"],"truong":"__abstain__",
                          **{name:json.dumps(v,ensure_ascii=False) for name,v in zip(names,abstains)}})
        records.append({"id":ident,"dau_vao":items[0]["dau_vao"],
                        "nhat_tri_tat_ca":all_agree and not any_abstain,
                        "co_abstain":any_abstain,"truong_dong_thuan":per_field})
    metrics={f:{"nhat_tri":v["all_agree"],"tong":v["items"],
                "ty_le_nhat_tri":round(v["all_agree"]/v["items"],6) if v["items"] else None,
                "fleiss_kappa":fleiss_kappa(v["vectors"])}
             for f,v in stats.items()}
    return {"ten_bo_gan":names,"tong":len(ids),"nhat_tri_tat_ca":sum(r["nhat_tri_tat_ca"] for r in records),
            "thong_ke_theo_truong":metrics,"nhan_dong_thuan_ung_vien":records,
            "not_gold":True},queue

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("labels",nargs="+",type=Path)
    parser.add_argument("--sample",type=Path,required=True)
    parser.add_argument("--output-dir",type=Path,required=True)
    a=parser.parse_args()
    expected={r["id"]:r["dau_vao"] for r in load_sample(a.sample)}
    bundles=[]
    for p in a.labels:
        b,errors=check_file(p,expected)
        if errors:raise ValueError(str(p)+": "+"; ".join(errors[:8]))
        bundles.append(b)
    out,queue=combine(bundles)
    if a.output_dir.exists():raise FileExistsError(a.output_dir)
    a.output_dir.mkdir(parents=True)
    output_json(a.output_dir/"nhan_dong_thuan_UNG_VIEN.json",out)
    output_csv(a.output_dir/"hang_doi_bat_dong.csv",queue,["id","dau_vao","truong",*out["ten_bo_gan"]])
    print("DONG_THUAN",out["tong"],"full",out["nhat_tri_tat_ca"],
          "queue_rows",len(queue),"kappa",
          {f:v["fleiss_kappa"] for f,v in out["thong_ke_theo_truong"].items()})
if __name__=="__main__":main()
