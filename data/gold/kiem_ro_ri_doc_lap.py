"""Independent second-pass scan of every exclusion source with all three audit keys.
Never accesses TEST labels: explicitly projects id/dau_vao/nguon only.
"""
import csv,json
from collections import Counter
from pathlib import Path
from gold_common import ROOT,EXTERNAL,GOLD,AUDIT,load_sample,output_json

def scan():
    sample=load_sample()
    keys={
        "text":{AUDIT.normalize(r["dau_vao"]) for r in sample},
        "osm":{AUDIT.osm_identity(r["nguon"]) for r in sample},
        "masked":{AUDIT.masked_family(r["dau_vao"]) for r in sample}
    }
    sources={
        "train": [ROOT/"data/train_dev/train.csv"],
        "dev":[ROOT/"data/train_dev/dev.csv"],
        "bo_sung_v1":list((ROOT/"data/train_dev/bo_sung_v1").rglob("*.csv"))+
                      list((ROOT/"data/train_dev/bo_sung_v1").rglob("*.jsonl")),
        "bo_sung_v2":list((ROOT/"data/train_dev/bo_sung_v2").rglob("*.csv"))+
                      list((ROOT/"data/train_dev/bo_sung_v2").rglob("*.jsonl")),
        "bo_sung_v3":list((EXTERNAL/"data/train_dev/bo_sung_v3_viet_tat_sieu_kho").rglob("*.csv"))+
                      list((EXTERNAL/"data/train_dev/bo_sung_v3_viet_tat_sieu_kho").rglob("*.jsonl")),
        "release_ai_train_only":[p for p in (EXTERNAL/"data/audit/release_ai_20261030").rglob("*")
                                if p.is_file() and p.name.startswith("train_") and p.suffix in (".csv",".jsonl")],
        "test_only_allowed_three_columns":[ROOT/"data/test/dia_chi_test.csv"]
    }
    intersections={}
    for group,paths in sources.items():
        if not paths:raise FileNotFoundError(group)
        totals=Counter()
        for path in paths:
            if path.suffix==".csv":
                with path.open(encoding="utf-8-sig",newline="") as f:
                    reader=csv.DictReader(f)
                    if group.startswith("test_"):
                        if not {"id","dau_vao","nguon"}.issubset(reader.fieldnames):raise ValueError("Test source missing allowed columns")
                        raw=({"dau_vao":r["dau_vao"],"nguon":r["nguon"]} for r in reader)
                    else:raw=reader
                    for r in raw:
                        text=next((r.get(k,"") for k in ("dau_vao","text","nfc","input") if r.get(k)),"")
                        origin=next((r.get(k,"") for k in ("nguon","source_url","osm_url","url") if r.get(k)),"")
                        if not origin and r.get("osm_id") and r.get("osm_type"):
                            origin=f"https://www.openstreetmap.org/{r['osm_type']}/{r['osm_id']}"
                        if not text:continue
                        totals["read"]+=1
                        triples={"text":AUDIT.normalize(text),"osm":AUDIT.osm_identity(origin),
                                 "masked":AUDIT.masked_family(text)}
                        for k,v in triples.items():
                            if v and v in keys[k]:totals[k]+=1
            else:
                with path.open(encoding="utf8") as f:
                    for line in f:
                        if not line.strip():continue
                        r=json.loads(line)
                        text=next((r.get(k,"") for k in ("dau_vao","text","nfc","input") if r.get(k)),"")
                        origin=next((r.get(k,"") for k in ("nguon","source_url","osm_url","url") if r.get(k)),"")
                        if not origin and r.get("osm_id") and r.get("osm_type"):
                            origin=f"https://www.openstreetmap.org/{r['osm_type']}/{r['osm_id']}"
                        if not text:continue
                        totals["read"]+=1
                        triples={"text":AUDIT.normalize(text),"osm":AUDIT.osm_identity(origin),
                                 "masked":AUDIT.masked_family(text)}
                        for k,v in triples.items():
                            if v and v in keys[k]:totals[k]+=1
        intersections[group]=dict(totals)
    passing=not any(x.get(k,0) for x in intersections.values()
                    for k in ("text","osm","masked"))
    return {"status":"PASS" if passing else "FAIL","sample_count":len(sample),
            "independent_rglob_scan":True,"test_labels_accessed":False,
            "sources":intersections}
def main():
    result=scan()
    path=GOLD/"BAO_CAO_RO_RI_DOC_LAP.json"
    if path.exists():raise FileExistsError(path)
    output_json(path,result)
    print("INDEPENDENT_LEAKAGE_"+result["status"],json.dumps(result,ensure_ascii=False))
    if result["status"]!="PASS":raise SystemExit(2)
if __name__=="__main__":main()
