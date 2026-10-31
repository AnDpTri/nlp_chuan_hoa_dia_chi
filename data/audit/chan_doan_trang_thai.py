"""Aggregate-only diagnosis. No addresses, labels or source URLs are printed."""
import csv, json, sys, hashlib, re
from pathlib import Path
from collections import Counter,defaultdict

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"data"/"test"/"scripts"))
from validate_dataset import check_field_grounding
from audit_du_lieu import normalize, masked_family, osm_identity
def getcsv(p):
    with (ROOT/p).open(encoding="utf-8-sig",newline="") as f:
        return list(csv.DictReader(f))
def getjsonl(p):
    return [json.loads(x) for x in (ROOT/p).read_text(encoding="utf-8").splitlines() if x.strip()]
def audit():
    tr=getcsv("data/train_dev/train.csv");de=getcsv("data/train_dev/dev.csv")
    v2=getcsv("data/train_dev/bo_sung_v2/train_bo_sung_v2.csv")
    test=getcsv("data/test/dia_chi_test.csv");review=getcsv("data/test/bang_duyet_test.csv")
    logs=getjsonl("data/test/nhat_ky_ai_duyet.jsonl")
    rby={r["id"]:r for r in review};lby={r["id"]:r for r in logs}
    safe={"rows": {"train":len(tr),"dev":len(de),"v2":len(v2),"test":len(test),
                   "review":len(review),"log":len(logs)},
          "test_status":dict(Counter(r["trang_thai_nhan"] for r in test)),
          "review_status":dict(Counter(r.get("trang_thai_duyet","") for r in review)),
          "log_verdict":dict(Counter(r.get("ket_luan","") for r in logs)),
          "review_log_overlap":len(set(rby)&set(lby)),
          "review_missing_log":[r["id"] for r in test if r["id"] not in lby],
          "test_review_status_mismatch":[r["id"] for r in test if r["trang_thai_nhan"]!=rby.get(r["id"],{}).get("trang_thai_duyet")],
          "test_log_status_mismatch":[r["id"] for r in test if r["trang_thai_nhan"]!=lby.get(r["id"],{}).get("trang_thai_sau")],
          "statuses_by_logs":{},
          "grounding_failed":{},
          "unresolved_warning_counts":{},
          "approved_warning_counts":{},
          "v2_train_duplicate":{},
          "masked_pair_counts":{},
          "full_review_metadata":{}
          }
    for status in ("da_duyet_ai","can_duyet"):
        group=[r for r in test if r["trang_thai_nhan"]==status]
        warnings=Counter()
        fails=defaultdict(list)
        for r in group:
            try:
                for w in json.loads(r.get("canh_bao") or "[]"):warnings[w]+=1
            except Exception: fails["canh_bao"].append(r["id"])
            for fld in ("so_nha","ngo_ngach_hem","thon_xom","duong"):
                try:
                    if r.get(fld) and not check_field_grounding(r["dau_vao"],r[fld],fld):
                        fails[fld].append(r["id"])
                except Exception:
                    fails[fld].append(r["id"])
        safe["grounding_failed"][status]={k:{"count":len(v),"ids":v[:30]} for k,v in fails.items()}
        safe[("approved_warning_counts" if status=="da_duyet_ai" else "unresolved_warning_counts")]=dict(warnings)
        safe["statuses_by_logs"][status]=dict(Counter(lby.get(r["id"],{}).get("ket_luan","NO_LOG") for r in group))
    v2_by_norm=defaultdict(list)
    for r in v2:v2_by_norm[normalize(r["dau_vao"])].append(r)
    train_by_norm=defaultdict(list)
    for r in tr:train_by_norm[normalize(r["dau_vao"])].append(r)
    shared=set(v2_by_norm)&set(train_by_norm)
    label_keys=["so_nha","ngo_ngach_hem","thon_xom","duong","ma_xa","ma_tinh","ma_xa_cu","ma_tinh_cu"]
    diffs=Counter()
    conflicting=[]
    for text in shared:
        for v in v2_by_norm[text]:
            for t in train_by_norm[text]:
                changes=[k for k in label_keys if v.get(k,"")!=t.get(k,"")]
                if changes:
                    diffs.update(changes);conflicting.append(v.get("id",""))
    safe["v2_train_duplicate"]={"shared_normalized_texts":len(shared),
        "duplicate_v2_rows":sum(len(v2_by_norm[x]) for x in shared),
        "v2_rows_conflicting_labels":len(set(conflicting)),
        "conflict_fields":dict(diffs),
        "conflict_row_ids":sorted(set(conflicting))[:30]}
    for a,b,x,y in (("train","dev",tr,de),("train","test",tr,test),("dev","test",de,test)):
        left=defaultdict(list);right=defaultdict(list)
        for r in x:
            m=masked_family(r["dau_vao"])
            if m:left[m].append(r)
        for r in y:
            m=masked_family(r["dau_vao"])
            if m:right[m].append(r)
        share=set(left)&set(right)
        same_prov=0
        for m in share:
            if {r.get("nguon","") for r in left[m] if r.get("nguon")}&{r.get("nguon","") for r in right[m] if r.get("nguon")}:
                same_prov+=1
        safe["masked_pair_counts"][a+"_"+b]={
           "shared_masked_texts":len(share),
           "shared_source_ids":same_prov,
           "blank_or_too_short_keys_in_first":sum(not masked_family(r["dau_vao"]) for r in x)
        }
    safe["full_review_metadata"]={
        "review_ai_row_count":sum(r.get("loai_nguoi_duyet")=="ai" for r in review),
        "review_signed_ai_resolved":sum(r.get("loai_nguoi_duyet")=="ai" and r.get("ngay_duyet") and r.get("ly_do_duyet") and r.get("trang_thai_duyet")=="da_duyet_ai" for r in review),
        "logs_with_four_evidence_fields":sum(all(key in r for key in ("can_cu_input","can_cu_danh_muc","can_cu_osm_dong_bang","can_cu_web")) for r in logs)
    }
    print(json.dumps(safe,ensure_ascii=False,indent=2))
if __name__=="__main__":audit()
