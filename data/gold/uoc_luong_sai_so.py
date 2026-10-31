"""Exact one-sided 95% Clopper-Pearson upper bound, stdlib only.
Rows: one per (selected address, field), human marks 'dung' or 'sai'.
Per-field error rates; full-address union requires every field marked on each ID.
No gold claims without actual human review.
"""
import argparse,csv,json,math
from collections import Counter,defaultdict
from pathlib import Path
from gold_common import FIELDS

def binom_cdf_leq(k,n,p):
    if p<=0:return 1.
    if p>=1:return 0. if k<n else 1.
    # Recursive binomial PMF, stable for typical n<=10000/p; CP by bisection.
    term=(1-p)**n
    total=term
    for j in range(1,k+1):
        term*=((n-j+1)/j)*(p/(1-p))
        total+=term
    return total

def cp_upper(errors,n,confidence=.95):
    if not isinstance(errors,int) or not isinstance(n,int) or n<=0 or not 0<=errors<=n:
        raise ValueError("Require n>0 and 0<=errors<=n")
    if not 0<confidence<1:raise ValueError("Confidence must be (0,1)")
    if errors==n:return 1.0
    alpha=1-confidence
    low,high=0.,1.
    for _ in range(100):
        mid=(low+high)/2
        cdf=binom_cdf_leq(errors,n,mid)
        if cdf>alpha:low=mid
        else:high=mid
    return (low+high)/2

def estimate(rows):
    groups=defaultdict(list)
    by_item=defaultdict(dict)
    for row in rows:
        field=row["truong"]
        if field not in FIELDS:raise ValueError("Invalid field "+field)
        value=row["dung_sai"].strip().casefold()
        if value not in ("dung","sai"):raise ValueError("Missing/invalid human judgment; must be dung or sai")
        ident=row["id"]
        if field in by_item[ident]:raise ValueError("Duplicate field "+ident+" "+field)
        by_item[ident][field]=value
        groups[field].append(value)
    if not by_item:raise ValueError("Empty human check file")
    if any(set(cols)!=set(FIELDS) for cols in by_item.values()):
        raise ValueError("Incomplete field checks for at least one selected address")
    n=len(by_item)
    report={"num_addresses":n,"confidence_one_sided":0.95,
            "human_verified":True,"fields":{}}
    for field in FIELDS:
        values=groups[field]
        k=values.count("sai")
        report["fields"][field]={"errors":k,"n":len(values),
                                "error_rate_pct":round(100*k/len(values),4),
                                "cp_upper_95_pct":round(100*cp_upper(k,len(values)),4)}
    complete_errors=sum(any(v=="sai" for v in fields.values()) for fields in by_item.values())
    report["all_fields"]={"errors":complete_errors,"n":n,
        "error_rate_pct":round(100*complete_errors/n,4),
        "cp_upper_95_pct":round(100*cp_upper(complete_errors,n),4)}
    return report

def main():
    a=argparse.ArgumentParser()
    a.add_argument("human_csv",type=Path)
    a.add_argument("--output",type=Path,required=True)
    args=a.parse_args()
    if args.output.exists():raise FileExistsError(args.output)
    with args.human_csv.open(encoding="utf-8-sig",newline="") as f:
        result=estimate(list(csv.DictReader(f)))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    print("HUMAN_CP_95",result["all_fields"])
if __name__=="__main__":main()
