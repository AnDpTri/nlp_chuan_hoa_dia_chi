"""Offline coverage audit of street-name evidence, not a street truth validator."""
import csv
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"data/audit/release_ai_20261030"


def norm(text):
    t=unicodedata.normalize("NFD",(text or "").casefold().replace("đ","d"))
    t="".join(c for c in t if not unicodedata.combining(c))
    t=re.sub(r"[^a-z0-9]+"," ",t).strip()
    return re.sub(r"^(duong|pho|dai lo|quoc lo|tinh lo|cao toc)\s+","",t)


def csv_rows(path):
    with path.open(encoding="utf-8-sig",newline="") as f:
        return list(csv.DictReader(f))


def main():
    conf=csv_rows(ROOT/"data/duong/v1/danh_muc_duong.csv")
    pending=csv_rows(ROOT/"data/duong/v1/danh_muc_candidates_pending.csv")
    confirmed= {(norm(r["canonical_name"]),r.get("ma_tinh","")) for r in conf}
    pending_names={norm(r.get("canonical_name","")) for r in pending}
    conf_names={x for x,_ in confirmed}
    rows={
        "train":csv_rows(ROOT/"data/train_dev/train.csv"),
        "dev":csv_rows(ROOT/"data/train_dev/dev.csv"),
        "train_v2_safe":csv_rows(OUT/"train_v2_anti_overlap.csv"),
        "test":csv_rows(ROOT/"data/test/dia_chi_test.csv"),
    }
    # Name+province is evidence of a similar string in a legal/official document;
    # it does not prove this specific road was correctly assigned to an address.
    all_stats={}
    for dataset,group in rows.items():
        tally=Counter()
        for r in group:
            street=norm(r.get("duong",""))
            province=r.get("ma_tinh","")
            if not street:
                classification="missing_road_label"
            elif (street,province) in confirmed:
                classification="confirmed_name_and_province"
            elif street in conf_names:
                classification="confirmed_name_other_or_unspecified_province"
            elif street in pending_names:
                classification="unverified_candidate_name"
            else:
                classification="no_matching_independent_evidence_in_v1"
            tally[classification]+=1
        all_stats[dataset]=dict(tally)
    data={
        "scope":"offline street-source coverage, NOT semantic ground truth",
        "confirmed_dictionary_records":len(conf),
        "unverified_candidates":len(pending),
        "datasets":all_stats,
        "policy":"Unverified or unknown street names require source review; do not auto correct to nearest confirmed street.",
    }
    (OUT/"street_evidence_coverage.json").write_text(
        json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(data,ensure_ascii=False,indent=2))


if __name__=="__main__": main()
