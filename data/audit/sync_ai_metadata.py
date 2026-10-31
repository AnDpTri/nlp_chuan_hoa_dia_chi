"""Synchronize derived AI-only review metadata without altering any test labels."""
import csv
import json
from collections import Counter
from datetime import date
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
T=ROOT/"data/test"
Q=ROOT/"data/audit/release_ai_20261030"


def read_csv(path):
    with path.open(encoding="utf-8-sig",newline="") as f:
        return list(csv.DictReader(f))


def main():
    test=read_csv(T/"dia_chi_test.csv")
    baseline=read_csv(T/"backup_before_ai_review/dia_chi_test.csv")
    logs=[json.loads(line) for line in (T/"nhat_ky_ai_duyet.jsonl").read_text(encoding="utf-8").splitlines() if line]
    reviews=read_csv(T/"bang_duyet_test.csv")
    assert len(test)==len(baseline)==len(logs)==len(reviews)==400
    assert len({r["id"] for r in test})==400
    assert {r["id"] for r in test}=={r["id"] for r in logs}=={r["id"] for r in reviews}
    assert all(r["loai_nguoi_duyet"]=="ai" for r in reviews)

    counts=Counter(r["trang_thai_nhan"] for r in test)
    verdict=Counter(r["ket_luan"] for r in logs)
    bby={r["id"]:r for r in baseline}
    qa_keys=("so_nha","ngo_ngach_hem","thon_xom","duong","ma_xa_cu",
             "ma_huyen_cu","ma_tinh_cu","ma_xa","ma_tinh",
             "xa_phuong","tinh","dia_chi_chuan","canh_bao")
    changed=sum(any(r.get(k,"")!=bby[r["id"]].get(k,"") for k in qa_keys) for r in test)
    warning=Counter(w for r in test for w in json.loads(r["canh_bao"] or "[]"))
    pending_split=sum(r["trang_thai_nhan"]=="can_duyet" and
                      "xa_bi_chia" in json.loads(r["canh_bao"] or "[]")
                      for r in test)
    release=json.loads((Q/"report.json").read_text(encoding="utf-8"))
    tiers=release["test"]["tiers"]
    assert sum(tiers.values())==400
    assert counts["da_duyet_ai"]==tiers["AI_STRICT_PROVISIONAL"]+tiers["AI_ACCEPTED_WITH_RISK"]
    assert counts["can_duyet"]==tiers["AI_ABSTAIN"]
    stats_path=T/"statistics.json"
    stats=json.loads(stats_path.read_text(encoding="utf-8"))
    stats["status_ai_review"]={
        "da_duyet_ai":counts.get("da_duyet_ai",0),
        "can_duyet":counts.get("can_duyet",0),
    }
    breakdown=stats.setdefault("ai_review_breakdown",{})
    for k,source in (
        ("du_can_cu_tham_chieu","du_can_cu_tham_chieu"),
        ("nhan_can_sua","nhan_can_sua"),
        ("chua_du_can_cu","chua_du_can_cu"),
    ):
        breakdown[k]=verdict.get(source,0)
    breakdown["xa_bi_chia_thu_hoi_bao_luu"]=pending_split
    breakdown["nhan_thuc_te_diff"]=changed
    stats["ai_only_quality_tiers"]=tiers
    stats["ai_audited_all_rows"]=len(logs)
    stats["ai_only_is_gold"]=False
    stats["ai_only_release"]="data/audit/release_ai_20261030/report.json"
    stats["derived_metadata_note"]="AI-reviewed is not human Gold. 111 rows abstained; do not force ward labels."
    # Keep historical distribution, categories and original selection metadata unchanged.
    stats_path.write_text(json.dumps(stats,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({
      "test_status":dict(counts),"historical_ai_verdict":dict(verdict),
      "human_verified":0,"changed_from_initial_labels":changed,
      "pending_split":pending_split,"ai_quality_tiers":tiers,
      "stats_file":str(stats_path)
    },ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
