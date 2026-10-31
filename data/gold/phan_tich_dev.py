"""Measure actual DEV inconsistencies for convention draft. Read-only dev inputs/labels."""
import csv,json,re
from collections import Counter
from pathlib import Path
from gold_common import ROOT,GOLD
DEV=ROOT/"data/train_dev/dev.csv"
PATTERNS={
 "ngo_hem_ngach_kiet":re.compile(r"(?i)\b(?:ngõ|ngo|ngách|ngach|hẻm|hem|kiệt|kiet)\b"),
 "nha_khoang":re.compile(r"\b\d+\s*[-–—]\s*\d+\b"),
 "nha_gach_cheo":re.compile(r"\b\d+[a-zA-Z]?/\d+\b"),
 "tien_to_so":re.compile(r"(?i)\b(?:số|so)\s+\d"),
 "tien_to_duong":re.compile(r"(?i)\b(?:đường|duong|phố|pho)\b"),
 "thon_to_kp_ap":re.compile(r"(?i)\b(?:tổ|khu phố|ấp|thôn|xóm|bản|buôn)\b"),
 "viet_tat_cmt_ql":re.compile(r"(?i)\b(?:cmt\s*8|cmt8|ql\s*\d+|quốc lộ|quoc lo)\b"),
 "ma_buu_chinh_cuoi":re.compile(r"\b\d{5,6}\s*$"),
 "toa_nha_tang_phong":re.compile(r"(?i)\b(?:chung cư|chung cu|tòa nhà|toa nha|tầng|tang|phòng|phong|căn hộ|can ho)\b"),
 "tieng_anh":re.compile(r"(?i)\b(?:district|ward|street|road|city|province)\b"),
}
def analyze():
    with DEV.open(encoding="utf-8-sig",newline="") as f:rows=list(csv.DictReader(f))
    result={"rows":len(rows),"cases":{}}
    for name,pat in PATTERNS.items():
        found=[r for r in rows if pat.search(r["dau_vao"])]
        result["cases"][name]={"count":len(found),"examples":[
            {k:r.get(k,"") for k in ("id","dau_vao","so_nha","ngo_ngach_hem","thon_xom","duong")}
            for r in found[:4]]}
    special=[r for r in rows if PATTERNS["ngo_hem_ngach_kiet"].search(r["dau_vao"])]
    road_has=[r for r in special if PATTERNS["ngo_hem_ngach_kiet"].search(r.get("duong",""))]
    split=[r for r in special if r.get("ngo_ngach_hem","").strip()]
    both=[r for r in special if r in road_has and r in split]
    missing=[r for r in special if not r.get("ngo_ngach_hem","").strip()]
    for name,group in [("ngo_text_and_road_contains_ngo",road_has),
                       ("ngo_text_and_separate_field",split),
                       ("ngo_text_both_fields",both),
                       ("ngo_text_but_no_ngo_field",missing)]:
        result["cases"][name]={"count":len(group),
            "examples":[{k:r.get(k,"") for k in ("id","dau_vao","so_nha","ngo_ngach_hem","duong")}
                        for r in group[:6]]}
    return result
if __name__=="__main__":
    report=analyze()
    (GOLD/"thong_ke_quy_uoc_dev.json").write_text(
        json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    for k,v in report["cases"].items():print(k,v["count"],v.get("examples",[])[:1])
