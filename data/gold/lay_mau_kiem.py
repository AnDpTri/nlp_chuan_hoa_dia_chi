"""Random, preregistered human-check sample from full-field candidate consensus only."""
import argparse,json,random
from pathlib import Path
from gold_common import FIELDS,output_csv

def choose(consensus,n=150,seed=20261030):
    population=[r for r in consensus["nhan_dong_thuan_ung_vien"]
                if r["nhat_tri_tat_ca"] and not r["co_abstain"]
                and all(r["truong_dong_thuan"][f] is not None for f in FIELDS)]
    if n>len(population):raise ValueError(f"Need {n} consensus items; only {len(population)}")
    rng=random.Random(seed)
    selected=rng.sample(sorted(population,key=lambda r:r["id"]),n)
    return [{"id":r["id"],"dau_vao":r["dau_vao"],
             "truong":f,"gia_tri_dong_thuan":json.dumps(r["truong_dong_thuan"][f],ensure_ascii=False),
             "dung_sai":"","ghi_chu_nguoi_duyet":""}
            for r in selected for f in FIELDS]

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("consensus_json",type=Path)
    ap.add_argument("--n",type=int,default=150)
    ap.add_argument("--seed",type=int,default=20261030)
    ap.add_argument("--output",type=Path,required=True)
    a=ap.parse_args()
    content=json.loads(a.consensus_json.read_text(encoding="utf8"))
    if a.output.exists():raise FileExistsError(a.output)
    records=choose(content,a.n,a.seed)
    output_csv(a.output,records,("id","dau_vao","truong","gia_tri_dong_thuan",
                                "dung_sai","ghi_chu_nguoi_duyet"))
    print("HUMAN_REVIEW_SHEET_BLANK",len(records)//len(FIELDS),"items",len(records),"rows")
if __name__=="__main__":main()
