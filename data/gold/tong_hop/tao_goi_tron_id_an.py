"""Make a BLIND mixed 1200-item evaluation set with randomized UNGVIEN_xxxx IDs.

Avoids leaking real-vs-synthetic origin from sequential original ID ranges.
The private remapping NEVER ships with the packages. No answers are read.
Run once; deterministic fixed seed. All outputs under data/gold/tong_hop.
"""
from __future__ import annotations
import csv,json,random,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
GOLD=HERE.parent
sys.path.insert(0,str(GOLD))
from tao_goi_gan_nhan import generate
from gold_common import output_csv
SEED=20261030
DEST=HERE/"goi_tron_mau_id_an"
MAP=HERE/"doi_chieu_id_tron_an_RIENG_KHONG_GUI_AI.json"

def records_and_map():
    r=random.Random(SEED)
    rows=[]
    for source,path in (("real",GOLD/"mau_ung_vien.csv"),("synthetic",HERE/"tong_hop_dau_vao.csv")):
        with path.open(encoding="utf-8-sig",newline="") as f:
            for item in csv.DictReader(f):
                rows.append({"id":item["id"],"dau_vao":item["dau_vao"],"source":source})
    if len(rows)!=1200 or len(set(row["id"] for row in rows))!=1200:
        raise ValueError("Expected 1200 distinct original IDs")
    original_ids=set(row["id"] for row in rows)
    r.shuffle(rows)
    shuffled_ids=r.sample(range(2000,10000),len(rows))
    mapping={}
    public=[]
    for n,(row,number) in enumerate(zip(rows,shuffled_ids)):
        public_id=f"UNGVIEN_{number:04d}"
        if public_id in mapping or public_id in original_ids:
            raise AssertionError("Pseudonym collisions")
        mapping[public_id]={"id_goc":row["id"],"loai_RIENG":row["source"]}
        public.append({"id":public_id,"dau_vao":row["dau_vao"]})
    return public,mapping

def main():
    if DEST.exists() or MAP.exists():raise FileExistsError("Sealed outputs already exist")
    rows,mapping=records_and_map()
    schema=json.loads((GOLD/"SCHEMA_NHAN.json").read_text(encoding="utf8"))
    convention=(GOLD/"QUY_UOC_NHAN.md").read_text(encoding="utf8")
    DEST.mkdir()
    for number,items,prompt in generate(rows,convention,schema,50):
        folder=DEST/f"goi_{number:02d}"
        folder.mkdir()
        output_csv(folder/"dau_vao.csv",items,("id","dau_vao"))
        (folder/"PROMPT_GAN_NHAN.txt").write_text(prompt,encoding="utf8")
    MAP.write_text(json.dumps({
        "type":"PRIVATE_DO_NOT_SEND_TO_ANNOTATORS","seed":SEED,"source_by_pseudo_id":mapping
    },ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    print("ANONYMIZED_MIXED_24_PACKAGES_PASS",len(rows),len(list(DEST.glob("goi_*"))),
          "real",sum(v["loai_RIENG"]=="real" for v in mapping.values()),
          "synthetic",sum(v["loai_RIENG"]=="synthetic" for v in mapping.values()))
if __name__=="__main__":main()
