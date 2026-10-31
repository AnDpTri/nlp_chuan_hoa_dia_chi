"""Produce a sealed, auditable AI-only dataset release.

No external calls. Keep original train/dev/test, original V2 and checkpoints unchanged.
Do not treat AI-reviewed or structurally verified labels as human gold.
"""
import csv
import hashlib
import json
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "data" / "test" / "scripts"))
from admin_lookup import Catalogues
from validate_dataset import check_field_grounding, check_admin_grounding
from audit_du_lieu import normalize, masked_family, osm_identity, sha256

OUTPUT = ROOT / "data" / "audit" / "release_ai_20261030"
V2DIR = ROOT / "data" / "train_dev" / "bo_sung_v2"
QA_FIELDS = ("so_nha","ngo_ngach_hem","thon_xom","duong",
             "ma_xa_cu","ma_huyen_cu","ma_tinh_cu","ma_xa","ma_tinh",
             "xa_phuong","tinh","dia_chi_chuan","canh_bao")
LABEL_FIELDS = QA_FIELDS[:-1]
SERIOUS_WARNINGS = {
    "xa_bi_chia","chua_xac_dinh_xa","thieu_xa","mo_ho_moc_cu_moi",
    "phan_chua_phan_loai","phan_du_khong_dau_can_duyet",
    "mau_thuan_the_osm","so_nha_can_duyet","khong_khop_huyen",
    "khong_khop_tinh","thieu_tinh","trung_ten_xa",
}


def csv_read(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        return r.fieldnames, list(r)


def csv_write(path, fields, records):
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(records)


def jsonl_read(path):
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def jsonl_write(path, records):
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in records:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def hash_dict(d):
    raw = json.dumps(d, ensure_ascii=False, sort_keys=True, separators=(",",":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def issues_for_row(row, catalogue, old_ds):
    issues = []
    old_code = row.get("ma_xa_cu", "")
    new_code = row.get("ma_xa", "")
    new_prov = row.get("ma_tinh", "")
    old_prov = row.get("ma_tinh_cu", "")
    old_dist = row.get("ma_huyen_cu", "")
    try:
        warnings = json.loads(row.get("canh_bao") or "[]")
        if not isinstance(warnings, list):
            issues.append("warning_not_list")
            warnings = []
    except (ValueError, TypeError):
        issues.append("warning_invalid_json")
        warnings = []
    for f in ("so_nha","ngo_ngach_hem","thon_xom","duong"):
        if row.get(f) and not check_field_grounding(row.get("dau_vao",""), row[f], f):
            issues.append("unobserved_" + f)
    if new_code:
        w = catalogue.new_wi.get(new_code)
        if not w:
            issues.append("unknown_new_ward")
        elif w["ma_tinh"] != new_prov:
            issues.append("new_hierarchy_mismatch")
    if new_prov and new_prov not in catalogue.new_pi:
        issues.append("unknown_new_province")
    if old_code:
        old = catalogue.old_wi.get(old_code)
        if not old:
            issues.append("unknown_old_ward")
        elif (old["ma_huyen"], old["ma_tinh"]) != (old_dist, old_prov):
            issues.append("old_hierarchy_mismatch")
        targets = {m["ma_xa_moi"] for m in catalogue.to_new.get(old_code, [])}
        if new_code and targets and new_code not in targets:
            issues.append("invalid_old_to_new_mapping")
        if len(targets) > 1 and new_code:
            issues.append("split_ward_forced")
        if len(targets) > 1 and not new_code and "xa_bi_chia" not in warnings:
            issues.append("split_missing_warning")
    if old_dist and (old_dist not in old_ds or old_ds[old_dist]["ma_tinh"] != old_prov):
        issues.append("old_district_province_mismatch")
    if (not new_code) != (not row.get("xa_phuong","")):
        issues.append("new_ward_name_without_code")
    return sorted(set(issues)), warnings


def build():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    train_fields, train = csv_read(ROOT / "data/train_dev/train.csv")
    _, dev = csv_read(ROOT / "data/train_dev/dev.csv")
    v2_fields, v2 = csv_read(V2DIR / "train_bo_sung_v2.csv")
    _, test = csv_read(ROOT / "data/test/dia_chi_test.csv")
    _, review = csv_read(ROOT / "data/test/bang_duyet_test.csv")
    logs = jsonl_read(ROOT / "data/test/nhat_ky_ai_duyet.jsonl")
    source = jsonl_read(ROOT / "data/test/goc/selected_sources.jsonl")
    token_records = jsonl_read(V2DIR / "token_spans_v2.jsonl")
    span_records = jsonl_read(V2DIR / "train_spans_v2.jsonl")
    assert len(v2) == len(token_records) == len(span_records) == 3000
    assert len(test) == len(review) == len(logs) == len(source) == 400
    assert len({r["id"] for r in v2}) == len(v2)
    cat = Catalogues()
    old_ds = {r["ma_huyen"]:r for r in cat.old_d}
    rt = {r["id"]:r for r in review}
    lt = {r["id"]:r for r in logs}
    st = {r["id"]:r for r in source}
    tokens = {r["id"]:r for r in token_records}
    spans = {r["id"]:r for r in span_records}
    assert {r["id"] for r in v2} == set(tokens) == set(spans)
    assert {r["id"] for r in test} == set(rt) == set(lt) == set(st)
    base_norm = {normalize(r["dau_vao"]) for r in train}
    eval_norm = {normalize(r["dau_vao"]) for r in dev + test}
    base_osm = {osm_identity(r["nguon"]) for r in train}
    eval_osm = {osm_identity(r["nguon"]) for r in dev + test}
    base_osm.discard("");eval_osm.discard("")
    v2_by_norm = defaultdict(list)
    for r in v2:
        v2_by_norm[normalize(r["dau_vao"])].append(r)
    collisions = {
        k: group for k, group in v2_by_norm.items() if len(group) > 1
    }
    conflict_groups = {
        k for k, group in collisions.items()
        if len({tuple(r.get(f,"") for f in LABEL_FIELDS) for r in group}) > 1
    }
    seen_good = set()
    safe_v2, quarantine = [], []
    safe_errors = Counter()
    for r in v2:
        reasons = []
        k = normalize(r["dau_vao"])
        if k in base_norm:
            reasons.append("same_text_as_base_train")
        if k in eval_norm:
            reasons.append("same_text_as_dev_or_test")
        osm = osm_identity(r.get("nguon",""))
        if osm and osm in eval_osm:
            reasons.append("same_osm_as_dev_or_test")
        if k in conflict_groups:
            reasons.append("intra_v2_conflicting_labels")
        if k in seen_good:
            reasons.append("intra_v2_repeated_text")
        if r["id"] not in tokens or r["id"] not in spans:
            reasons.append("missing_span_record")
        # V2 may intentionally withhold new ward codes; only quarantine proven
        # hierarchy errors and forced split targets, not missing information.
        row_issues, _ = issues_for_row(r, cat, old_ds)
        severe = [x for x in row_issues if x in (
            "unknown_new_ward","new_hierarchy_mismatch","unknown_new_province",
            "unknown_old_ward","old_hierarchy_mismatch",
            "invalid_old_to_new_mapping","split_ward_forced",
            "old_district_province_mismatch","new_ward_name_without_code"
        )]
        reasons.extend(severe)
        if reasons:
            quarantine.append({"id":r["id"],"reasons":"|".join(sorted(set(reasons)))})
            safe_errors.update(set(reasons))
        else:
            safe_v2.append(r)
            seen_good.add(k)
    safe_ids = {r["id"] for r in safe_v2}
    span_safe = [spans[r["id"]] for r in safe_v2 if tokens[r["id"]].get("usable_for_span_training") is True]
    token_safe = [tokens[r["id"]] for r in safe_v2 if tokens[r["id"]].get("usable_for_span_training") is True]
    canonical_safe = [r for r in safe_v2 if tokens[r["id"]].get("usable_for_canonical_training") is True]
    csv_write(OUTPUT / "train_v2_anti_overlap.csv", v2_fields, safe_v2)
    csv_write(OUTPUT / "train_v2_canonical_eligible.csv", v2_fields, canonical_safe)
    jsonl_write(OUTPUT / "train_v2_spans_eligible.jsonl", span_safe)
    jsonl_write(OUTPUT / "train_v2_tokens_eligible.jsonl", token_safe)
    csv_write(OUTPUT / "v2_quarantine_ids.csv", ["id","reasons"], quarantine)

    reasons_counter = Counter()
    verdicts=[]
    for r in test:
        ident=r["id"]
        rev, log, source_row=rt[ident],lt[ident],st[ident]
        bad, warning=issues_for_row(r,cat,old_ds)
        reasons=[]
        if r["dau_vao"] != source_row.get("dau_vao") or r["nguon"] != source_row.get("source_url"):
            reasons.append("source_snapshot_mismatch")
        if r["trang_thai_nhan"] != rev.get("trang_thai_duyet") or r["trang_thai_nhan"] != log.get("trang_thai_sau"):
            reasons.append("review_status_disagreement")
        if rev.get("loai_nguoi_duyet") != "ai" or log.get("loai_nguoi_duyet") != "ai":
            reasons.append("missing_ai_audit_classification")
        if not rev.get("ly_do_duyet") or not rev.get("ngay_duyet") or not log.get("thoi_gian_kiem_tra"):
            reasons.append("review_metadata_incomplete")
        if not all(log.get(key) is not None for key in
                   ("can_cu_input","can_cu_danh_muc","can_cu_osm_dong_bang","can_cu_web")):
            reasons.append("incomplete_evidence_channels")
        if r["trang_thai_nhan"]=="da_duyet_ai":
            admin_ok,_=check_admin_grounding(r,cat,old_ds)
            if not admin_ok:
                reasons.append("unobserved_admin_in_input")
        reasons += bad
        reasons += [w for w in warning if w in SERIOUS_WARNINGS]
        if r["trang_thai_nhan"] != "da_duyet_ai":
            tier="AI_ABSTAIN"
            reasons.append("historical_ai_abstained_no_factual_basis")
        elif reasons:
            tier="AI_ACCEPTED_WITH_RISK"
        else:
            tier="AI_STRICT_PROVISIONAL"
        reasons_counter[tier]+=1
        verdicts.append({
            "id":ident,
            "previous_ai_status":r["trang_thai_nhan"],
            "historical_ai_verdict":log.get("ket_luan",""),
            "tier":tier,
            "risk_reasons":"|".join(sorted(set(reasons))),
            "historical_agent":log.get("agent_id",""),
            "historical_model":log.get("model_duyet",""),
            "evidence_type":"frozen_source+2025_catalogue+historical_ai_log+structural_cross_check",
            "input_sha256":hashlib.sha256(r["dau_vao"].encode("utf-8")).hexdigest(),
        })
    csv_write(OUTPUT / "test_ai_tiers_400.csv",
              list(verdicts[0].keys()),verdicts)
    # AI-only subset is NOT gold; only source-grounded accepted rows with
    # no structural/risk flags enter this optional locked diagnostic.
    strict_ids={r["id"] for r in verdicts if r["tier"]=="AI_STRICT_PROVISIONAL"}
    strict_test=[r for r in test if r["id"] in strict_ids]
    csv_write(OUTPUT / "test_ai_strict_PROVISIONAL_NOT_GOLD.csv",
              list(test[0].keys()),strict_test)
    report={
       "protocol":"ai_only_with_abstention_v1",
       "note":"Historical AI reviewers were not re-run. Secondary audit is rule-based; no human review occurred.",
       "anti_test_contamination":"No model scoring, training, thresholds, or development tuning based on test labels.",
       "v2":{"input_rows":len(v2),"safe_unique_rows":len(safe_v2),
             "canonical_eligible":len(canonical_safe),
             "span_eligible":len(span_safe),
             "quarantine":len(quarantine),
             "quarantine_reasons":dict(safe_errors),
             "intra_v2_duplicate_text_keys":len(collisions),
             "intra_v2_conflicting_label_keys":len(conflict_groups)},
       "test":{"total":len(test),"tiers":dict(reasons_counter),
               "risk_reasons":dict(Counter(
                   reason for r in verdicts for reason in r["risk_reasons"].split("|") if reason
               )),
               "historical_ai_verdicts":dict(Counter(log["ket_luan"] for log in logs)),
               "human_reviewed":0,
               "gold":False,
               "strict_subset":"AI-only provisional, not Gold, no generalization guarantee"},
       "input_hashes":{
            "train":sha256(ROOT/"data/train_dev/train.csv"),
            "dev":sha256(ROOT/"data/train_dev/dev.csv"),
            "v2":sha256(V2DIR/"train_bo_sung_v2.csv"),
            "test":sha256(ROOT/"data/test/dia_chi_test.csv"),
            "audit_log":sha256(ROOT/"data/test/nhat_ky_ai_duyet.jsonl")},
       "output_hashes":{},
    }
    for path in sorted(OUTPUT.iterdir()):
        if path.is_file() and path.name != "report.json":
            report["output_hashes"][path.name]=sha256(path)
    (OUTPUT/"report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({
        "v2":report["v2"],"test":report["test"],
        "report_path":str(OUTPUT/"report.json")
    },ensure_ascii=False,indent=2))


if __name__ == "__main__":
    build()
