"""Build offline synthetic extreme-abbreviation TRAIN data.

Contains one user-confirmed historical example and catalogue-derived
abbreviation chains. Never insert into dev/test or pretend independent Gold.
"""
import csv
import hashlib
import itertools
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "data/train_dev/bo_sung_v3_viet_tat_sieu_kho"
CLEAN = ROOT / "data/clean"
TRAIN = ROOT / "data/train_dev"
COLUMNS = ("id","dau_vao","nguon","so_nha","ngo_ngach_hem","thon_xom",
           "duong","ma_xa_cu","ma_huyen_cu","ma_tinh_cu","ma_xa",
           "ma_tinh","xa_phuong","tinh","dia_chi_chuan","canh_bao",
           "loai_nhan","nguon_du_lieu","ghi_chu")
USER_SEED = "x5,mh,ml,nd"
USER_CANONICAL = "Xóm 5, Phường Mỹ Lộc, Tỉnh Ninh Bình"


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path, rows):
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fold(s):
    t = unicodedata.normalize("NFD", (s or "").casefold().replace("đ","d"))
    return "".join(c for c in t if not unicodedata.combining(c))


def norm(s):
    return re.sub(r"[^a-z0-9]+", " ", fold(s)).strip()


def initials(s):
    parts = re.findall(r"[a-z0-9]+", fold(s))
    return "".join(p[0] for p in parts)


def full_unit(row, level):
    kind = row["loai_" + level].strip()
    name = row["ten_" + level].strip()
    return name if norm(name).startswith(norm(kind) + " ") else kind + " " + name


def join_parts(parts, sep):
    """Return text and exact char spans without parsing model predictions."""
    text, positions = "", []
    for level, surface in parts:
        if text:
            text += sep
        start = len(text)
        text += surface
        positions.append({"level":level,"start":start,"end":len(text),
                          "surface":surface})
    assert all(text[p["start"]:p["end"]] == p["surface"] for p in positions)
    return text, positions


def row_of(text, num, kind, old_codes, new_codes, new_full, canonical,
           hamlet="", note="", provenance=""):
    r = dict.fromkeys(COLUMNS, "")
    r.update({
       "id": f"VNTRAIN_HARD3_{num:05d}",
       "dau_vao":text,
       "nguon":provenance,
       "thon_xom":hamlet,
       "ma_xa_cu":old_codes.get("ma_xa_cu",""),
       "ma_huyen_cu":old_codes.get("ma_huyen_cu",""),
       "ma_tinh_cu":old_codes.get("ma_tinh_cu",""),
       "ma_xa":new_codes.get("ma_xa",""),
       "ma_tinh":new_codes.get("ma_tinh",""),
       "xa_phuong":new_full.get("xa_phuong",""),
       "tinh":new_full.get("tinh",""),
       "dia_chi_chuan":canonical,
       "canh_bao":json.dumps(
           ["bien_the_tong_hop","viet_tat_cuc_do",
            "tham_chieu_nguoi_dung" if kind=="user_temporal_alias"
            else "tham_chieu_danh_muc"],ensure_ascii=False
       ),
       "loai_nhan":"train_synthetic_provisional",
       "nguon_du_lieu":kind,
       "ghi_chu":note,
    })
    return r


def build():
    OUT.mkdir(parents=True, exist_ok=True)
    new_wards = {r["ma_xa"]:r for r in read_csv(CLEAN/"moi_tinh_xa.csv")}
    new_prov = {r["ma_tinh"]:r for r in read_csv(CLEAN/"moi_tinh.csv")}
    old_wards = read_csv(CLEAN/"cu_tinh_huyen_xa.csv")
    old_prov = {r["ma_tinh"]:r for r in read_csv(CLEAN/"cu_tinh.csv")}
    old_dist = {r["ma_huyen"]:r for r in read_csv(CLEAN/"cu_huyen.csv")}
    maps = read_csv(CLEAN/"doi_chieu_xa_cu_moi.csv")
    targets = defaultdict(set)
    for r in maps:
        if r["ma_xa_cu"]:
            targets[r["ma_xa_cu"]].add(r["ma_xa_moi"])

    # User reference is an additional historical temporal alias, NOT a
    # fabricated old administrative code in the frozen old catalogue.
    assert old_prov["36"]["ten_tinh"] == "Nam Định"
    assert new_prov["37"]["ten_tinh"] == "Ninh Bình"
    assert new_wards["13708"]["ten_xa"] == "Mỹ Lộc"
    assert new_wards["13708"]["loai_xa"] == "Phường"
    assert new_wards["13708"]["ma_tinh"] == "37"
    assert not any(r["ten_xa"] == "Mỹ Hưng" and r["ma_tinh"] == "36" for r in old_wards)

    old_codes={"ma_tinh_cu":"36"}  # no invented old ward / old district codes
    new_codes={"ma_xa":"13708","ma_tinh":"37"}
    new_full={"xa_phuong":"Phường Mỹ Lộc","tinh":"Tỉnh Ninh Bình"}

    # Candidate strings retain all four independent slots provided by the user.
    # No new geographic assertion is made by changing spelling/punctuation.
    user_forms = [
        ("x5","mh","ml","nd"), ("x5","mh","ml","nđ"),
        ("x5","mh","ml","Nam Định"), ("x5","m.h","m.l","n.đ"),
        ("xóm 5","mỹ hưng","mỹ lộc","nam định"),
        ("Xóm 5","Mỹ Hưng","Mỹ Lộc","Nam Định"),
        ("xom 5","my hung","my loc","nam dinh"),
        ("xóm5","MH","ML","NĐ"),
        ("x5","Mỹ Hưng","Mỹ Lộc","NĐ"),
        ("xóm 5","mh","ml","nd"),
        ("x 5","MH","ML","ND"), ("x.5","m.h","m.l","n.d"),
        ("xóm số 5","Mỹ Hưng","Mỹ Lộc","Nam Định"),
        ("X5","M H","M L","N Đ"),
        ("xóm 5","mh","mỹ lộc","nam định"),
        ("xóm 5","mỹ hưng","ml","nđ"),
        ("x5","my hung","my loc","nd"),
        ("x5","mỹ hưng","ml","nam định"),
        ("x5","mh","mỹ lộc","nd"),
        ("xóm5","m.h","ml","N.Đ"),
        ("x5","mh","ML","Nam Định"),
        ("xóm 5","MH","Mỹ Lộc","NĐ"),
        ("x5","Mỹ Hưng","ML","nam dinh"),
        ("xom5","M.H","M.L","N.D"),
    ]
    separators=[(",", ", ", " / ", " - ", " ; ", " | ")[i % 6]
                for i in range(len(user_forms))]
    assert len(user_forms)==len(separators)
    all_rows,meta=[],[]
    seen=set()
    def add(text, parts, family, kind, old_c, new_c, rendered, canonical,
            hamlet="", note="", provenance=""):
        k=norm(text)
        if not k or k in seen:
            return False
        seen.add(k)
        n=len(all_rows)+1
        r=row_of(text,n,kind,old_c,new_c,rendered,canonical,
                 hamlet=hamlet,note=note,provenance=provenance)
        all_rows.append(r)
        meta.append({"id":r["id"],"family_id":family,
          "provenance_kind":kind,
          "training_partition":"train_only",
          "spans":parts,
          "reference_status":"user_provided_historical_reference_not_external_verified"
             if kind=="user_temporal_alias"
             else "structural_catalogue_mapping_not_independently_semantic_verified"})
        return True

    for values,sep in zip(user_forms,separators):
        segments=list(zip(("hamlet","old_ward_historical_alias",
                          "old_district_historical_alias","old_province"),values))
        text,spans=join_parts(segments,sep)
        add(text,spans,"FAM_USER_MH_ML_ND_01","user_temporal_alias",
            old_codes,new_codes,new_full,USER_CANONICAL,
            hamlet="Xóm 5",note="MH=Mỹ Hưng (tên lịch sử do người dùng xác nhận); "
            "ML=Mỹ Lộc; NĐ=Nam Định. Không tự tạo mã xã/huyện cũ.",
            provenance="user_confirmed_example:MH_ML_ND_01")

    # Catalogue-derived old administrative chains. Require uniqueness of
    # initialism triple across the FULL old catalogue before assigning gold.
    triples=defaultdict(list)
    for ward in old_wards:
        district=old_dist.get(ward["ma_huyen"])
        province=old_prov.get(ward["ma_tinh"])
        if not district or not province:
            continue
        key=(initials(ward["ten_xa"]),initials(district["ten_huyen"]),
             initials(province["ten_tinh"]))
        if all(len(x)>=2 for x in key):
            triples[key].append(ward)

    candidates=[]
    for key,wards in triples.items():
        if len(wards)!=1:
            continue
        ward=wards[0]
        t=targets.get(ward["ma_xa"],set())
        if len(t)!=1:
            continue
        new_code=next(iter(t))
        new_ward=new_wards.get(new_code)
        if not new_ward or new_ward["ma_tinh"] not in new_prov:
            continue
        candidates.append((ward,key,new_ward))

    # Balanced round-robin selection across historical provinces.
    by_province=defaultdict(list)
    for w,key,nw in candidates:
        by_province[w["ma_tinh"]].append((w,key,nw))
    for entries in by_province.values():
        entries.sort(key=lambda x:x[0]["ma_xa"])
    chosen=[]
    for i in range(50):
        for prov in sorted(by_province):
            if len(chosen)>=120:
                break
            group=by_province[prov]
            if i<len(group):
                chosen.append(group[i])
        if len(chosen)>=120:
            break
    assert len(chosen)>=90, "Not enough distinct grounded administrative chains"

    for w,key,nw in chosen:
        d=old_dist[w["ma_huyen"]]
        p=old_prov[w["ma_tinh"]]
        target_p=new_prov[nw["ma_tinh"]]
        new_names={"xa_phuong":full_unit(nw,"xa"),
                   "tinh":full_unit(target_p,"tinh")}
        canonical=", ".join((new_names["xa_phuong"],new_names["tinh"]))
        old_c={"ma_xa_cu":w["ma_xa"],
               "ma_huyen_cu":w["ma_huyen"],"ma_tinh_cu":w["ma_tinh"]}
        new_c={"ma_xa":nw["ma_xa"],"ma_tinh":nw["ma_tinh"]}
        wa,di,pr=key
        variants=[
           (("old_ward",wa),("old_district",di),("old_province",pr)),
           (("old_ward",w["ten_xa"]),("old_district",di),("old_province",pr)),
           (("old_ward",wa),("old_district",d["ten_huyen"]),
            ("old_province",pr)),
        ]
        joins=[","," / ",", "]
        for fragments,joiner in zip(variants,joins):
            text,spans=join_parts(fragments,joiner)
            add(text,spans,f"FAM_ADMIN_ABBR_{w['ma_xa']}",
                "synthetic_clean_catalogue_chain",old_c,new_c,new_names,
                canonical,note="Viet tat ba cap cu; moi cap duoc xac thuc "
                "bang chuoi ma tinh-huyen-xa. Du lieu tong hop khong phai OSM.",
                provenance=f"clean_mapping:old_ward_{w['ma_xa']}")

    # Negative abstain examples. NEVER train these as empty canonical gold.
    abstain_inputs=[
      "x5,mh,ml","x5,mh,nd","x5,ml,nd","mh,ml,nd",
      "xóm 5,mh","x5,mh","x5,ml","x5,nd","mh,ml",
      "mỹ hưng,ml","xóm 5, mỹ hưng","xóm 5, mỹ lộc",
      "x5 mh ml","x5, MH","xom 5,ml","x.5, nđ",
      "xóm 5, Mỹ Hưng, Mỹ Lộc","Mỹ Hưng","ML","MH",
    ]
    abstain=[]
    for i,t in enumerate(abstain_inputs,1):
        abstain.append({
           "id":f"VNTRAIN_HARD3_ABSTAIN_{i:03d}",
           "dau_vao":t,
           "decision":"ABSTAIN",
           "ma_xa":"",
           "ma_tinh":"",
           "reason":"Thieu it nhat mot ngu canh cua vi du user (xom, MH, ML, ND); "
                    "khong gan ma duoc.",
           "family_id":"FAM_USER_MH_ML_ND_01",
           "training_partition":"contrast_only_not_canonical_training",
        })

    train_norm={norm(r["dau_vao"]) for r in read_csv(TRAIN/"train.csv")}
    dev_norm={norm(r["dau_vao"]) for r in read_csv(TRAIN/"dev.csv")}
    test_norm={norm(r["dau_vao"]) for r in read_csv(ROOT/"data/test/dia_chi_test.csv")}
    v2_norm={norm(r["dau_vao"]) for r in read_csv(TRAIN/"bo_sung_v2/train_bo_sung_v2.csv")}
    overlaps=Counter()
    for r in all_rows:
        k=norm(r["dau_vao"])
        if k in train_norm: overlaps["train"]+=1
        if k in dev_norm: overlaps["dev"]+=1
        if k in test_norm: overlaps["test"]+=1
        if k in v2_norm: overlaps["v2"]+=1
    assert not overlaps, f"Trung input voi dataset hien co: {dict(overlaps)}"

    for row,source_meta in zip(all_rows,meta):
        t=row["dau_vao"]
        assert source_meta["training_partition"]=="train_only"
        assert all(t[seg["start"]:seg["end"]]==seg["surface"] for seg in source_meta["spans"])
        assert row["ma_xa"] in new_wards
        assert new_wards[row["ma_xa"]]["ma_tinh"]==row["ma_tinh"]
        if row["ma_xa_cu"]:
            assert targets[row["ma_xa_cu"]]=={row["ma_xa"]}
        if source_meta["provenance_kind"]=="user_temporal_alias":
            assert row["dia_chi_chuan"]==USER_CANONICAL
            assert row["ma_xa_cu"]==row["ma_huyen_cu"]==""

    write_csv(OUT/"train_abbreviation_extreme.csv",all_rows)
    with (OUT/"source_spans_and_family.jsonl").open("w",encoding="utf-8",newline="\n") as f:
        for r in meta:
            f.write(json.dumps(r,ensure_ascii=False)+"\n")
    with (OUT/"contrast_abstain.csv").open("w",encoding="utf-8",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=list(abstain[0]))
        writer.writeheader()
        writer.writerows(abstain)
    summary={
       "version":"v3.0",
       "scope":"train_only_synthetic_abbreviations",
       "authoritative_claim":"Only user example is user-asserted; other mappings derived from clean snapshot, not independently proven current geographic address.",
       "input_user_example":USER_SEED,
       "user_target":USER_CANONICAL,
       "user_target_codes":{"ma_xa":"13708","ma_tinh":"37"},
       "historical_old_province":"36",
       "historical_old_ward_code":"UNAVAILABLE_IN_FROZEN_OLD_CATALOGUE",
       "positive_rows":len(all_rows),
       "user_example_variants":sum(r["nguon_du_lieu"]=="user_temporal_alias" for r in all_rows),
       "catalogue_derived_variants":sum(r["nguon_du_lieu"]=="synthetic_clean_catalogue_chain" for r in all_rows),
       "catalogue_derived_families":len(chosen),
       "abstain_contrast":len(abstain),
       "overlap_by_normalized_input":dict(overlaps),
       "family_policy":"All variants of one administrative chain in TRAIN only; no dev/test injection.",
       "usage_policy":"Provisional synthetic train data; not gold, not independent accuracy evaluation. Abstain file excluded from canonical training.",
       "src_sha256":{
          "old_wards":sha256(CLEAN/"cu_tinh_huyen_xa.csv"),
          "mapping":sha256(CLEAN/"doi_chieu_xa_cu_moi.csv"),
          "new_wards":sha256(CLEAN/"moi_tinh_xa.csv"),
       },
       "output_sha256":{
          f:sha256(OUT/f) for f in
          ("train_abbreviation_extreme.csv","source_spans_and_family.jsonl",
           "contrast_abstain.csv")
       }
    }
    (OUT/"manifest.json").write_text(
        json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(summary,ensure_ascii=True,indent=2))


if __name__=="__main__":
    build()
