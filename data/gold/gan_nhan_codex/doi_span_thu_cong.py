"""FORMAT CONVERTER ONLY. No regex NER, classification, inference or model calls.
Every span and abstain decision is authored explicitly in TSV by this annotator.

TSV: id<TAB>truong~van_ban~thu_tu_xuat_hien;...<TAB>ly_do_abstain
Empty span list '-'. Occurrence count is 1-based. Strict substring on NFC
source. Never infer missing items, never invent labels.
"""
from __future__ import annotations
import argparse,csv,json,unicodedata
from pathlib import Path
BASE=Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0,str(BASE))
from gold_common import FIELDS
from kiem_nhan import validate_bundle

def convert_lines(source_csv,decision_tsv,annotator="codex_gpt"):
    with Path(source_csv).open(encoding="utf-8-sig",newline="") as f:
        source=list(csv.DictReader(f))
    by_id={r["id"]:r["dau_vao"] for r in source}
    if len(by_id)!=len(source):raise ValueError("Duplicate source ids")
    specs={}
    with Path(decision_tsv).open(encoding="utf-8-sig",newline="") as f:
        for lineno,line in enumerate(f,1):
            if not line.strip() or line.startswith("#"):continue
            fields=line.rstrip("\r\n").split("\t")
            if len(fields)!=3:raise ValueError(f"TSV line {lineno}: expected exactly 3 columns")
            ident,encoded,reason=fields
            if ident in specs:raise ValueError("Repeated decision id "+ident)
            if ident not in by_id:raise ValueError("Unknown decision id "+ident)
            specs[ident]=(encoded,reason)
    missing=set(by_id)-set(specs)
    if missing:raise ValueError(f"UNLABELED ITEMS NOT ALLOWED: {len(missing)}; first "+repr(sorted(missing)[:6]))
    result=[]
    for ident,text in by_id.items():
        raw,reason=specs[ident]
        spans=[]
        for item in ([] if raw=="-" else raw.split(";")):
            parts=item.split("~")
            if len(parts)!=3:raise ValueError(f"{ident}: each span is (truong,van_ban,thu_tu_xuat_hien)")
            field,needle,occurrence=parts
            if field not in FIELDS:raise ValueError(ident+" illegal field "+field)
            # Some upstream OSM Unicode is decomposed; offsets MUST refer to
            # the original raw input, never silently normalized/rewritten.
            if not needle:raise ValueError(ident+" empty needle")
            occurrence=int(occurrence)
            if occurrence<1:raise ValueError("Occurrence must start at 1")
            pos=0
            for k in range(occurrence):
                found=text.find(needle,pos)
                if found<0:raise ValueError(f"{ident}: missing {needle!r} occurrence {occurrence}")
                pos=found+len(needle)
            spans.append({"truong":field,"start":found,"end":found+len(needle),
                          "van_ban":needle})
        spans.sort(key=lambda x:(x["start"],x["end"],x["truong"]))
        result.append({"id":ident,"dau_vao":text,"spans":spans,
                       "abstain":bool(reason),"ly_do_abstain":reason})
    bundle={"bo_gan":annotator,"nhan":result}
    errors=validate_bundle(bundle,by_id)
    if errors:raise ValueError("Schema/offset validation failed: "+str(errors[:10]))
    return bundle

def main():
    a=argparse.ArgumentParser()
    a.add_argument("source_csv",type=Path)
    a.add_argument("decision_tsv",type=Path)
    a.add_argument("--output",type=Path,required=True)
    a.add_argument("--annotator",default="codex_gpt")
    args=a.parse_args()
    if args.output.exists():raise FileExistsError(args.output)
    result=convert_lines(args.source_csv,args.decision_tsv,args.annotator)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    print("CONVERTED_EXPLICIT_MANUAL_DECISIONS",len(result["nhan"]),
          "ABSTAIN",sum(r["abstain"] for r in result["nhan"]))
if __name__=="__main__":main()
