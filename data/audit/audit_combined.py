"""Audit derived CNN train snapshot provenance, without model training."""
import hashlib,json,csv
from collections import Counter,defaultdict
from pathlib import Path
from audit_du_lieu import normalize,masked_family,sha256
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"data/audit/release_ai_20261030"
DIR=ROOT/"data/train_dev/duyet_v2_01"
def get_csv(p):
    with p.open(encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))
def get_jsonl(p):
    return [json.loads(s) for s in p.read_text(encoding="utf-8").splitlines() if s.strip()]
def main():
    meta=json.loads((DIR/"TONG_KET.json").read_text(encoding="utf-8"))
    source_sha=meta.get("source_sha256",{})
    current_v2=sha256(ROOT/"data/train_dev/bo_sung_v2/train_bo_sung_v2.csv")
    combined=get_jsonl(DIR/"train_cnn_ket_hop.jsonl")
    dev=get_csv(ROOT/"data/train_dev/dev.csv")
    test=get_csv(ROOT/"data/test/dia_chi_test.csv")
    devnorm={normalize(r["dau_vao"]) for r in dev}
    testnorm={normalize(r["dau_vao"]) for r in test}
    norm_index=defaultdict(list)
    src_counter=Counter()
    id_counter=Counter()
    for r in combined:
        norm_index[normalize(r.get("text") or r.get("dau_vao") or "")].append(r)
        ref=r.get("ref") or {}
        src_id=ref.get("id","") if isinstance(ref,dict) else ""
        src_counter["v2_source" if src_id.startswith("VNTRAIN_V2_") else "base_or_other"]+=1
        if src_id:id_counter[src_id]+=1
    duplicates={k:v for k,v in norm_index.items() if len(v)>1 and k}
    clash_keys=[]
    for k,rr in duplicates.items():
        labels={tuple((r.get("ref") or {}).get(f,"") for f in
                      ("so_nha","ngo_ngach_hem","thon_xom","duong","ma_xa_cu","ma_xa","ma_tinh")) for r in rr}
        if len(labels)>1:clash_keys.append(k)
    summary={
        "combined_rows":len(combined),
        "total_unique_normalized_texts":len(norm_index),
        "duplicate_normalized_text_keys":len(duplicates),
        "conflicting_labels_on_duplicate_text_keys":len(clash_keys),
        "normalized_input_overlap_dev":sum(k in devnorm for k in norm_index if k),
        "normalized_input_overlap_test":sum(k in testnorm for k in norm_index if k),
        "record_sources":dict(src_counter),
        "repeated_source_row_ids":sum(n>1 for n in id_counter.values()),
        "original_v2_sha256_in_combined_meta":source_sha.get("train_bo_sung_v2.csv"),
        "current_v2_sha256":current_v2,
        "derived_from_current_v2":source_sha.get("train_bo_sung_v2.csv")==current_v2,
        "safe_reuse_policy":"Old combined source hash does not match current V2: do not silently merge current release with old 5768-row artifact.",
    }
    (OUT/"combined_cnn_provenance_audit.json").write_text(
        json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=="__main__":main()
