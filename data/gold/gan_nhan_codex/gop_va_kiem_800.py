"""Merge 16 manually decided files with exact package and 800-row identity validation.
No inference. Refuse to create any missing rows or overwrite output.
"""
import csv,json,sys
from collections import Counter
from pathlib import Path
HERE=Path(__file__).resolve().parent
BASE=HERE.parent
sys.path.insert(0,str(BASE))
from kiem_nhan import check_file,validate_bundle
from gold_common import load_sample

def main():
    blocks=[]
    for i in range(1,17):
        package=BASE/f"goi_gan_nhan/goi_{i:02d}"
        with (package/"dau_vao.csv").open(encoding="utf-8-sig",newline="") as f:
            expected={r["id"]:r["dau_vao"] for r in csv.DictReader(f)}
        path=HERE/f"codex_gpt_goi_{i:02d}.json"
        bundle,errors=check_file(path,expected)
        if errors:raise ValueError(f"goi_{i:02d} kiem_nhan FAIL: "+str(errors[:8]))
        if bundle["bo_gan"]!="codex_gpt":raise ValueError("Wrong annotator ID")
        blocks.extend(bundle["nhan"])
        print("GOI_PASS",i,len(bundle["nhan"]),sum(x["abstain"] for x in bundle["nhan"]))
    whole={"bo_gan":"codex_gpt","nhan":blocks}
    expected={r["id"]:r["dau_vao"] for r in load_sample()}
    errors=validate_bundle(whole,expected)
    if errors:raise ValueError("800 validation failed: "+str(errors[:12]))
    outfile=HERE/"codex_gpt_800.json"
    if outfile.exists():raise FileExistsError(outfile)
    outfile.write_text(json.dumps(whole,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    reasons=Counter(row["ly_do_abstain"].split(";")[0] for row in blocks if row["abstain"])
    metrics={"annotator":"codex_gpt","all_count":len(blocks),
             "abstain_count":sum(r["abstain"] for r in blocks),
             "abstain_pct":round(100*sum(r["abstain"] for r in blocks)/len(blocks),3),
             "common_reasons":reasons.most_common(25),
             "annotation_method":"One model; manually authored (field, literal substring, ordinal occurrence) per item; converter only finds offsets",
             "manual_ground_truth":False,"not_human_gold":True}
    (HERE/"THONG_KE_NHAN_UNG_VIEN.json").write_text(
        json.dumps(metrics,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    print("ANNOTATION_800_PASS",json.dumps(metrics,ensure_ascii=False),flush=True)
if __name__=="__main__":main()
