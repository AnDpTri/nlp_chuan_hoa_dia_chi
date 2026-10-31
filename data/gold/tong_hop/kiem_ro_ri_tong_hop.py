"""Independent normalized-text-only leakage check, recursive for train augmentations.

External TEST CSV: read only id, dau_vao, nguon (projected explicitly).
No TEST labels, scores, logs or public/private answer fields used for training.
Checks BOTH public synthetics and their pre-transform source strings.
"""
import argparse,csv,json,sys
from collections import Counter
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
BASE=ROOT/"data/gold"
sys.path.insert(0,str(BASE))
from gold_common import EXTERNAL,AUDIT,sha256

def source_groups():
    return {
      "train":[ROOT/"data/train_dev/train.csv"],
      "dev":[ROOT/"data/train_dev/dev.csv"],
      "bo_sung_v1":sorted((ROOT/"data/train_dev/bo_sung_v1").rglob("*.csv"))+
                    sorted((ROOT/"data/train_dev/bo_sung_v1").rglob("*.jsonl")),
      "bo_sung_v2":sorted((ROOT/"data/train_dev/bo_sung_v2").rglob("*.csv"))+
                    sorted((ROOT/"data/train_dev/bo_sung_v2").rglob("*.jsonl")),
      "bo_sung_v3":sorted((EXTERNAL/"data/train_dev/bo_sung_v3_viet_tat_sieu_kho").rglob("*.csv"))+
                    sorted((EXTERNAL/"data/train_dev/bo_sung_v3_viet_tat_sieu_kho").rglob("*.jsonl")),
      "test_three_columns_only":[ROOT/"data/test/dia_chi_test.csv"],
      "mau_ung_vien":[BASE/"mau_ung_vien.csv"],
    }

def candidate_texts(path,test_only=False):
    if path.suffix==".csv":
        with path.open(encoding="utf-8-sig",newline="") as src:
            reader=csv.DictReader(src)
            if test_only:
                if not {"id","dau_vao","nguon"}.issubset(reader.fieldnames or []):
                    raise ValueError("Missing restricted TEST columns")
                # Explicit read/access ONLY the three authorized columns.
                for raw in reader:
                    permitted={"id":raw["id"],"dau_vao":raw["dau_vao"],"nguon":raw["nguon"]}
                    if permitted["dau_vao"]: yield permitted["dau_vao"]
            else:
                for row in reader:
                    text=next((row.get(k) for k in ("dau_vao","text","nfc","input") if row.get(k)),"")
                    if text:yield text
    else:
        with path.open(encoding="utf8") as src:
            for line in src:
                if not line.strip():continue
                row=json.loads(line)
                text=next((row.get(k) for k in ("dau_vao","text","nfc","input") if row.get(k)),"")
                if text:yield text

def run():
    with (HERE/"tong_hop_dau_vao.csv").open(encoding="utf-8-sig",newline="") as f:
        public=list(csv.DictReader(f))
    with (BASE/"mau_ung_vien.csv").open(encoding="utf-8-sig",newline="") as f:
        original=list(csv.DictReader(f))
    with (HERE/"doi_chieu_id_RIENG_KHONG_GUI_AI.json").open(encoding="utf8") as f:
        provenance=json.load(f)
    if len(public)!=400 or len(provenance)!=400:raise ValueError("Incorrect synthetic size")
    if set(r["id"] for r in public) & set(r["id"] for r in original):
        raise ValueError("Synthetic and real candidate IDs overlap")
    public_norm={AUDIT.normalize(r["dau_vao"]) for r in public}
    source_norm={AUDIT.normalize(v["origin_full"]) for v in provenance.values()}
    if "" in public_norm or "" in source_norm:
        raise ValueError("Empty normalized address")
    if len(public_norm)!=400:raise ValueError("Duplicate synthetic public address")
    grouped={}
    for group,paths in source_groups().items():
        if not paths:raise FileNotFoundError(group)
        seen=set()
        source_rows=0
        for path in paths:
            if not path.is_file():raise FileNotFoundError(path)
            for text in candidate_texts(path,test_only=group=="test_three_columns_only"):
                source_rows+=1
                value=AUDIT.normalize(text)
                if value:seen.add(value)
        grouped[group]={
          "read_rows":source_rows,
          "overlap_public":len(public_norm&seen),
          "overlap_origin":len(source_norm&seen)
        }
    good=all(not item["overlap_public"] and not item["overlap_origin"] for item in grouped.values())
    return {"status":"PASS" if good else "FAIL",
            "public_rows":len(public),
            "origin_rows":len(provenance),
            "sha256_public":sha256(HERE/"tong_hop_dau_vao.csv"),
            "all_sources_readonly":True,"test_only_id_dau_vao_nguon":True,
            "external_test_labels_read":False,"per_source":grouped}

def main():
    a=argparse.ArgumentParser()
    a.add_argument("--output",type=Path,default=HERE/"BAO_CAO_RO_RI_TONG_HOP.json")
    options=a.parse_args()
    result=run()
    if options.output.exists():raise FileExistsError(options.output)
    options.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    print("TONG_HOP_INDEPENDENT_LEAKAGE_"+result["status"],
          json.dumps(result,ensure_ascii=False),flush=True)
    if result["status"]!="PASS":raise SystemExit(2)
if __name__=="__main__":main()
