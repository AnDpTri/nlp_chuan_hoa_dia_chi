"""Deterministic, proportionally stratified OSM candidate sample. No labels are read from TEST.
Reads only id,dau_vao,nguon from the test CSV, never any other test fields.
"""
from __future__ import annotations
import argparse,csv,hashlib,io,json,math,random,re,unicodedata
from collections import Counter,defaultdict
from pathlib import Path
from gold_common import ROOT,GOLD,EXTERNAL,AUDIT,source_keys,sha256,name_and_source,jsonl_rows

SEED=20261030
COUNT=800
COLUMNS=("id","dau_vao","nguon","osm_id","input_mode","nhom_tinh","nhom_dac_diem","tang")
OSM=EXTERNAL/"data/test/goc/osm_public_candidates.jsonl"

def exclusion_sources():
    files={
        "train": [ROOT/"data/train_dev/train.csv"],
        "dev": [ROOT/"data/train_dev/dev.csv"],
        "bo_sung_v1": sorted((ROOT/"data/train_dev/bo_sung_v1").glob("*.csv"))+
                       sorted((ROOT/"data/train_dev/bo_sung_v1").glob("*.jsonl")),
        "bo_sung_v2": sorted((ROOT/"data/train_dev/bo_sung_v2").glob("*.csv"))+
                       sorted((ROOT/"data/train_dev/bo_sung_v2").glob("*.jsonl")),
        "bo_sung_v3": sorted((EXTERNAL/"data/train_dev/bo_sung_v3_viet_tat_sieu_kho").glob("*.csv"))+
                       sorted((EXTERNAL/"data/train_dev/bo_sung_v3_viet_tat_sieu_kho").glob("*.jsonl")),
        "release_ai":sorted(p for p in (EXTERNAL/"data/audit/release_ai_20261030").glob("*")
                            if p.name.startswith("train_") and p.suffix in (".csv",".jsonl")),
        "test_exclusion_ONLY_id_dau_vao_nguon":[ROOT/"data/test/dia_chi_test.csv"]
    }
    for group,paths in files.items():
        if not paths:raise FileNotFoundError(f"Required source group missing: {group}")
        for p in paths:
            if not p.is_file():raise FileNotFoundError(str(p))
    return files

def restricted_source_rows(path,test_only=False):
    if path.suffix==".csv":
        with path.open(encoding="utf-8-sig",newline="") as f:
            reader=csv.DictReader(f)
            if test_only:
                if not {"id","dau_vao","nguon"}.issubset(reader.fieldnames or []):
                    raise ValueError("TEST EXCLUSION schema mismatch")
                for row in reader:
                    # Explicit projection: NO access to other test fields.
                    yield row["dau_vao"],row["nguon"]
            else:
                for row in reader:yield name_and_source(row)
    else:
        for row in jsonl_rows(path):yield name_and_source(row)

def load_exclusions():
    sources=exclusion_sources()
    groups={}
    meta={}
    for group,paths in sources.items():
        buckets={k:set() for k in ("text","osm","masked")}
        seen=0
        for p in paths:
            testonly=group.startswith("test_exclusion_")
            for address,source in restricted_source_rows(p,testonly):
                if not address: continue
                seen+=1
                keys=source_keys(address,source)
                for k,v in keys.items():
                    if v:buckets[k].add(v)
        groups[group]=buckets
        meta[group]={"source_rows_with_address":seen,
                      "fingerprints":{k:len(v) for k,v in buckets.items()},
                      "paths":[str(p) for p in paths]}
    return groups,meta

def features(record):
    text=record["dau_vao"]
    tags=record.get("tags") or {}
    province=next((tags.get(k) for k in ("addr:province","addr:state","addr:city")
                   if tags.get(k)), "")
    # Purely a sampling stratum, not a target label.
    province_key=AUDIT.normalize(province)
    province_key=" ".join(province_key.split()[:5]) if province_key else "khong_co_the_tinh"
    if len(province_key)>40:province_key=province_key[:40]
    n=AUDIT.normalize(text)
    letters=[c for c in text if c.isalpha()]
    accented=any(c in "àáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵđ" for c in text.lower())
    abbrev=bool(re.search(r"(?i)(?:^|\W)(?:tp\.?hcm|hcm|hn|q\.?\d*|p\.?\d*|ng\.?|kp\.?|ql\s?\d+|cmt8)(?=\W|$)",text))
    if letters and not accented:kind="khong_dau"
    elif abbrev:kind="viet_tat"
    elif len([x for x in re.split(r"[,;]",text) if x.strip()])<3:kind="thieu_thanh_phan"
    else:kind="co_dau_khac"
    return province_key,kind,record.get("input_mode") or "khong_ro"

def draw(n=COUNT,seed=SEED):
    sources,meta=load_exclusions()
    pooled={k:set().union(*(g[k] for g in sources.values())) for k in ("text","osm","masked")}
    exclusions=Counter()
    reasons_by_source={g:Counter() for g in sources}
    strata=defaultdict(list)
    from_osm=0
    source_dupes=0
    source_local={k:set() for k in ("text","osm","masked")}
    for row in jsonl_rows(OSM):
        from_osm+=1
        text,source=name_and_source(row)
        keys=source_keys(text,source)
        if not text.strip() or not keys["text"] or not keys["osm"]:
            exclusions["invalid_source_or_text"]+=1;continue
        flags=[k for k,v in keys.items() if v and v in pooled[k]]
        for group,buckets in sources.items():
            for k,v in keys.items():
                if v and v in buckets[k]:reasons_by_source[group][k]+=1
        if flags:
            for k in flags:exclusions["independent_"+k]+=1
            exclusions["excluded_any_cross_source"]+=1
            exclusions["precedence_"+flags[0]]+=1
            continue
        duplicates=[k for k,v in keys.items() if v and v in source_local[k]]
        if duplicates:
            source_dupes+=1
            for k in duplicates:exclusions["internal_pool_"+k]+=1
            continue
        for k,v in keys.items():
            if v:source_local[k].add(v)
        kind=features(row)
        strata[kind].append({
            "dau_vao":text,"nguon":source,"osm_id":keys["osm"],
            "input_mode":kind[2],"nhom_tinh":kind[0],
            "nhom_dac_diem":kind[1],"tang":" | ".join(kind)})
    pool_n=sum(len(v) for v in strata.values())
    if pool_n<n:raise RuntimeError(f"Only {pool_n} eligible candidates, requested {n}")
    rng=random.Random(seed)
    # Hamilton proportional allocation with deterministic tie breaks.
    allocations={}
    floors={}
    for key,items in strata.items():
        exact=len(items)*n/pool_n
        floors[key]=math.floor(exact)
    remaining=n-sum(floors.values())
    residual=sorted(strata,key=lambda k:(-(len(strata[k])*n/pool_n-floors[k]),k))
    allocations=dict(floors)
    for key in residual[:remaining]:allocations[key]+=1
    chosen=[]
    for key in sorted(strata):
        group=sorted(strata[key],key=lambda x:(x["osm_id"],x["dau_vao"]))
        rng.shuffle(group)
        chosen.extend(group[:allocations[key]])
    chosen.sort(key=lambda r:(r["tang"],r["osm_id"]))
    rng.shuffle(chosen)
    for i,row in enumerate(chosen,1):
        row["id"]=f"UNGVIEN_{i:04d}"
    if len(chosen)!=n:raise AssertionError("Allocation lost samples")
    # Independent final per-source three-key validation.
    sample_keys={k:set() for k in ("text","osm","masked")}
    for row in chosen:
        keys=source_keys(row["dau_vao"],row["nguon"])
        for k,v in keys.items():
            if v:
                if v in sample_keys[k]:raise AssertionError("Internal duplicate "+k)
                sample_keys[k].add(v)
                for group,buckets in sources.items():
                    if v in buckets[k]:raise AssertionError(f"Leakage {group}:{k}")
    statistics={
        "seed":seed,"requested":n,"osm_rows_scanned":from_osm,
        "excluded_counts":dict(exclusions),"eligible_after_all_gates":pool_n,
        "internal_pool_duplicate_records":source_dupes,
        "exclusion_sources":meta,
        "excluded_by_source_and_key":{g:dict(v) for g,v in reasons_by_source.items()},
        "distribution":[{"nhom_tinh":a,"nhom_dac_diem":b,"input_mode":c,
                         "pool":len(strata[(a,b,c)]),"selected":allocations[(a,b,c)],
                         "sample_pct":round(100*allocations[(a,b,c)]/n,3)}
                        for a,b,c in sorted(strata)],
        "sample_feature_counts":dict(Counter(r["nhom_dac_diem"] for r in chosen)),
        "sample_input_modes":dict(Counter(r["input_mode"] for r in chosen)),
        "independent_leakage_verification":"PASS: each selected item checked against each source on text, OSM identity, masked family; blank keys ignored",
        "test_labels_accessed":False}
    return chosen,statistics

def serialize(rows):
    buf=io.StringIO(newline="")
    wr=csv.DictWriter(buf,fieldnames=COLUMNS,lineterminator="\r\n")
    wr.writeheader();wr.writerows(rows)
    return ("\ufeff"+buf.getvalue()).encode("utf-8")

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--seed",type=int,default=SEED)
    parser.add_argument("--count",type=int,default=COUNT)
    parser.add_argument("--verify",action="store_true",help="Regenerate in-memory and compare existing CSV bytes; never write")
    args=parser.parse_args()
    chosen,info=draw(args.count,args.seed)
    data=serialize(chosen)
    digest=hashlib.sha256(data).hexdigest()
    file=GOLD/"mau_ung_vien.csv"
    if args.verify:
        if not file.exists() or file.read_bytes()!=data:
            raise AssertionError(f"Reproducibility FAIL, regenerated sha256={digest}")
        print("SAMPLE_REPRODUCIBLE_PASS",digest,flush=True)
    else:
        if file.exists(): raise FileExistsError("Refusing to replace existing sample: "+str(file))
        file.write_bytes(data)
        info["sample_csv_sha256"]=digest
        (GOLD/"thong_ke_chon_mau.json").write_text(json.dumps(info,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        print("SAMPLE_CREATED",len(chosen),"SHA256",digest,flush=True)
    print("CANDIDATES",info["osm_rows_scanned"],"ELIGIBLE",info["eligible_after_all_gates"],
          "EXCLUDED",info["excluded_counts"],flush=True)
if __name__=="__main__":main()
