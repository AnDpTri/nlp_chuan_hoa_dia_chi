"""Return only synthetic labels (with ORIGINAL synthetic IDs) from 24 blind
mixed+rekeyed packages after a separate model has annotated all 1200.

Public packages must never receive the private mapping or reference answers.
Does not open/read synthetic answers. Validates package-by-package and global
completeness (including 800 real inputs), then converts ID only. No inference.
"""
from __future__ import annotations
import argparse,csv,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
GOLD=HERE.parent
sys.path.insert(0,str(GOLD))
from kiem_nhan import check_file,validate_bundle

def read_mixed_labels(paths):
    mapping_file=HERE/"doi_chieu_id_tron_an_RIENG_KHONG_GUI_AI.json"
    mapping=json.loads(mapping_file.read_text(encoding="utf8"))["source_by_pseudo_id"]
    source=(HERE/"goi_tron_mau_id_an")
    if len(paths)!=24:raise ValueError("Require exactly 24 labeled blind packages")
    blocks=[]
    annotated_by={}
    for n,path in enumerate(paths,1):
        with (source/f"goi_{n:02d}/dau_vao.csv").open(encoding="utf-8-sig",newline="") as f:
            expected={r["id"]:r["dau_vao"] for r in csv.DictReader(f)}
        bundle,errors=check_file(path,expected)
        if errors:raise ValueError(f"Blind package {n}: "+str(errors[:8]))
        annotated_by.setdefault(bundle["bo_gan"],0)
        annotated_by[bundle["bo_gan"]]+=len(bundle["nhan"])
        blocks.extend(bundle["nhan"])
    if len(annotated_by)!=1:raise ValueError("Cannot mix model annotator IDs")
    annotated_id=next(iter(annotated_by))
    exact_expected={}
    for n in range(1,25):
        with (source/f"goi_{n:02d}/dau_vao.csv").open(encoding="utf-8-sig",newline="") as f:
            exact_expected.update({r["id"]:r["dau_vao"] for r in csv.DictReader(f)})
    bundle={"bo_gan":annotated_id,"nhan":blocks}
    errors=validate_bundle(bundle,exact_expected)
    if errors:raise ValueError("1200 blind labels invalid/incomplete: "+str(errors[:8]))
    if set(mapping)!=set(exact_expected):raise ValueError("Private ID mapping mismatch")
    synthetic=[]
    for row in blocks:
        m=mapping[row["id"]]
        if m["loai_RIENG"]=="synthetic":
            synthetic.append({**row,"id":m["id_goc"]})
    if len(synthetic)!=400 or len(set(r["id"] for r in synthetic))!=400:
        raise AssertionError("Did not retrieve exactly 400 synthetic labels")
    with (HERE/"tong_hop_dau_vao.csv").open(encoding="utf-8-sig",newline="") as f:
        expected_synthetic={r["id"]:r["dau_vao"] for r in csv.DictReader(f)}
    result={"bo_gan":annotated_id,"nhan":synthetic}
    errors=validate_bundle(result,expected_synthetic)
    if errors:raise ValueError("Recovered labels fail original IDs: "+str(errors[:8]))
    return result

def main():
    a=argparse.ArgumentParser()
    a.add_argument("labels",nargs=24,type=Path,
                   help="24 JSON bundles in EXACT order goi_01..goi_24")
    a.add_argument("--out",required=True,type=Path)
    args=a.parse_args()
    if args.out.exists():raise FileExistsError(args.out)
    result=read_mixed_labels(args.labels)
    args.out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    print("REKEYED_BLIND_SYNTHETIC_RECOVERED_PASS",len(result["nhan"]),
          "annotator",result["bo_gan"],"ABSTAIN",
          sum(r["abstain"] for r in result["nhan"]))
    print("Now score with: python score_tong_hop.py",args.out)
if __name__=="__main__":main()
