"""Join the 8 frozen self-label outputs and make validator-compatible sample CSVs.

These CSVs contain only input ID + text + six EMPTY metadata columns,
not target answers or source group. No annotation decisions are made here.
"""
import csv,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
GOLD=HERE.parent
sys.path.insert(0,str(GOLD))
from kiem_nhan import validate_bundle,check_file
from gold_common import output_csv
COLS=("id","dau_vao","nguon","osm_id","input_mode","nhom_tinh","nhom_dac_diem","tang")
def run():
    combined=[]
    full_expected={}
    for n in range(1,9):
        folder=HERE/f"goi_gan_nhan/goi_{n:02d}"
        with (folder/"dau_vao.csv").open(encoding="utf-8-sig",newline="") as f:
            expected={r["id"]:r["dau_vao"] for r in csv.DictReader(f)}
        content,errors=check_file(HERE/f"codex_gpt_tong_hop_goi_{n:02d}.json",expected)
        if errors:raise ValueError("Package failed "+str(n)+" "+str(errors[:8]))
        if content["bo_gan"]!="codex_gpt":raise ValueError("Unexpected annotator")
        combined.extend(content["nhan"])
        full_expected.update(expected)
        sample_file=HERE/f"mau_kiem_schema_goi_{n:02d}.csv"
        if sample_file.exists():raise FileExistsError(sample_file)
        output_csv(sample_file,({"id":i,"dau_vao":v} for i,v in expected.items()),COLS)
    public_expected={}
    with (HERE/"tong_hop_dau_vao.csv").open(encoding="utf-8-sig",newline="") as f:
        public_expected={r["id"]:r["dau_vao"] for r in csv.DictReader(f)}
    if full_expected!=public_expected:raise AssertionError("Missing or altered input")
    result={"bo_gan":"codex_gpt","nhan":combined}
    errors=validate_bundle(result,public_expected)
    if errors:raise ValueError("Combined 400 labels invalid: "+str(errors[:8]))
    output=HERE/"codex_gpt_tong_hop_400.json"
    sample=HERE/"mau_kiem_schema_codex_tong_hop_400.csv"
    if output.exists() or sample.exists():raise FileExistsError("Locked output already exists")
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    output_csv(sample,({"id":i,"dau_vao":v} for i,v in public_expected.items()),COLS)
    print("COMBINED_400_PASS",len(combined),"ABSTAIN",sum(r["abstain"] for r in combined),flush=True)
if __name__=="__main__":run()
