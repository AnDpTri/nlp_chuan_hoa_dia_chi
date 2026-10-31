"""Generate fixed, closed-book synthetic address benchmark from catalogue only.
NO train or API calls. Only id/dau_vao/nguon fields of test CSV ever opened,
via read-only exclusion code. Answers/ID mapping are kept separate from prompts.

Not representative of real-world user addresses. Invented street/house combos.
"""
from __future__ import annotations
import argparse,csv,hashlib,io,json,random,re,sys,unicodedata
from collections import Counter
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/"data/gold"))
from gold_common import AUDIT,source_keys,FIELDS,sha256
from chon_mau import load_exclusions
from src.danh_muc import DanhMuc

SEED=20261030
N=400
STREETS=("Nguyễn Trãi","Lê Lợi","Trần Phú","Phan Đình Phùng","Nguyễn Huệ",
         "Hoàng Diệu","Lý Thường Kiệt","Nguyễn Thị Minh Khai",
         "Trần Hưng Đạo","Đinh Tiên Hoàng","Lê Duẩn","Điện Biên Phủ",
         "Nguyễn Văn Cừ","Hoàng Quốc Việt","Phạm Văn Đồng","Cách Mạng Tháng Tám")
COLS=("id","dau_vao")

def acronym(text):
    pieces=[x for x in AUDIT.normalize(text).split() if x]
    return "".join(x[0] for x in pieces)

def no_accent(t):
    s=unicodedata.normalize("NFD",t)
    return "".join(c for c in s if not unicodedata.combining(c)).replace("đ","d").replace("Đ","D")

def typed(unit):
    return unit.ten if AUDIT.normalize(unit.ten).startswith(AUDIT.normalize(unit.loai)+" ") else unit.loai+" "+unit.ten

_LOOKUP_INDEX={}
def candidates(admin_units,field,display):
    if not display:return admin_units
    # Cache only catalogue surface forms, never answer codes or sample origins.
    key=AUDIT.normalize(display)
    idx_key=(admin_units[0].cay,field)
    if idx_key not in _LOOKUP_INDEX:
        index={}
        for unit in admin_units:
            for spelling in (typed(unit),unit.ten,acronym(unit.ten),acronym(typed(unit))):
                norm=AUDIT.normalize(spelling)
                index.setdefault(norm,{})[unit.ma]=unit
        _LOOKUP_INDEX[idx_key]=index
    return list(_LOOKUP_INDEX[idx_key].get(key,{}).values())

def code_answer(units,visible,tree):
    byfield={"xa":[u for u in units if u.cay==tree and u.cap=="xa"],
             "huyen":[u for u in units if u.cay=="cu" and u.cap=="huyen"],
             "tinh":[u for u in units if u.cay==tree and u.cap=="tinh"]}
    ps=candidates(byfield["tinh"],"tinh",visible.get("tinh",""))
    ds=candidates(byfield["huyen"],"huyen",visible.get("huyen",""))
    ws=candidates(byfield["xa"],"xa",visible.get("xa",""))
    # Context filter uses only the relationships encoded in the source catalogue.
    # For old units: district -> old province, ward -> old district.
    # For new: ward -> new province.
    if visible.get("tinh"):
        p_ids={p.ma for p in ps}
        if tree=="moi":
            ws=[w for w in ws if w.ma_cha in p_ids]
        else:
            ds=[d for d in ds if d.ma_cha in p_ids]
            ds_ids={d.ma for d in ds}
            if visible.get("huyen"):ws=[w for w in ws if w.ma_cha in ds_ids]
            else:ws=[w for w in ws if any(d.ma==w.ma_cha for d in byfield["huyen"] if d.ma_cha in p_ids)]
    if tree=="cu" and visible.get("huyen"):
        d_ids={d.ma for d in ds}
        ws=[w for w in ws if w.ma_cha in d_ids]
    return ws,ps

def render(parts,rng,group,mode):
    # parts: explicit (field,value) pairs known at generation, no generated labels from parsing
    segments=list(parts)
    if group=="b" and mode in (1,4):rng.shuffle(segments)
    if group=="b" and mode==2:segments=[x for x in segments if x[0]!="tinh"]
    if group=="b" and mode==3:segments=[x for x in segments if x[0]!="xa"]
    segments=[(f,no_accent(v) if group=="b" and mode in (0,3) else v) for f,v in segments]
    noise=[]
    if group=="b" and mode in (1,3):noise=["Tòa nhà Sen Việt, tầng 8"]
    if group=="b" and mode in (0,4):noise=["700000"]
    pieces=[]
    for f,v in segments:
        pieces.append((f,v))
    for v in noise:pieces.append((None,v))
    sep=", " if mode%2==0 else " - "
    text=""
    spans=[]
    visible={}
    for field,value in pieces:
        if text:text+=sep
        start=len(text)
        text+=value
        if field:
            spans.append({"truong":field,"start":start,"end":len(text),"van_ban":value})
            visible[field]=value
    return text,spans,visible

def synthetic():
    rng=random.Random(SEED)
    dm=DanhMuc(ROOT/"data/clean")
    units=list(dm.don_vi.values())
    olds=[x for x in units if x.cay=="cu" and x.cap=="xa" and dm.dich_xa("cu",x.ma)]
    news=[x for x in units if x.cay=="moi" and x.cap=="xa"]
    rng.shuffle(olds);rng.shuffle(news)
    requested={"a":140,"b":140,"c":120}
    source_exclusions,_=load_exclusions()
    pooled={k:set().union(*(x[k] for x in source_exclusions.values())) for k in ("text","osm","masked")}
    with (ROOT/"data/gold/mau_ung_vien.csv").open(encoding="utf-8-sig",newline="") as f:
        original_sample=list(csv.DictReader(f))
    for row in original_sample:
        keys=source_keys(row["dau_vao"],row["nguon"])
        for k,v in keys.items():
            if v:pooled[k].add(v)
    seen=set()
    answers=[]
    rejected=Counter()
    groups=Counter()
    # Alternating old/new allows unusual cases while ensuring deterministic sequence.
    for group,source in (("a",olds),("b",news),("c",news[::-1])):
        for candidate in source:
            if groups[group]>=requested[group]:break
            try:
                if group=="a":
                    district=dm.lay("cu",candidate.ma_cha)
                    province=dm.lay("cu",district.ma_cha)
                    mode=groups[group]%5
                    unitparts={
                        "xa":acronym(candidate.ten) if mode<4 else typed(candidate),
                        "huyen":acronym(district.ten) if mode<3 else typed(district),
                        "tinh":acronym(province.ten) if mode<2 else typed(province)}
                    parts=[("thon_xom","x"+str(1+groups[group]%8)),
                           ("xa",unitparts["xa"]),("huyen",unitparts["huyen"]),
                           ("tinh",unitparts["tinh"])]
                    base=[("thon_xom","Xóm "+str(1+groups[group]%8)),
                          ("xa",typed(candidate)),("huyen",typed(district)),
                          ("tinh",typed(province))]
                    tree="cu"
                    visible=unitparts
                else:
                    province=dm.lay("moi",candidate.ma_cha)
                    mode=groups[group]%5 if group=="b" else 2
                    number=1000+groups[group]*11+(37 if group=="c" else 0)
                    street=STREETS[(groups[group]*7+(2 if group=="c" else 0))%len(STREETS)]
                    parts=[("so_nha",str(number)),("duong","Đường "+street),
                           ("xa",typed(candidate)),("tinh",typed(province))]
                    if group=="c":
                        parts=[("so_nha","Số "+str(number)),("ngo_ngach_hem","Ngõ "+str(4+groups[group]%55)),
                               ("thon_xom","Tổ "+str(1+groups[group]%10)),
                               ("duong","Đường "+street),("xa",typed(candidate)),
                               ("tinh",typed(province))]
                    base=list(parts)
                    tree="moi"
                text,spans,vis=render(parts,rng,group,mode)
                base_text=", ".join(value for _,value in base)
                # Exclude BOTH generated and original full source by normalized-text key
                # plus conservative masked family. No OSM IDs exist for synthesized rows.
                keys=source_keys(text,"")
                base_keys=source_keys(base_text,"")
                if any(v and v in pooled[k] for k,v in keys.items()):
                    rejected["generated_leakage_"+group]+=1;continue
                if any(v and v in pooled[k] for k,v in base_keys.items()):
                    rejected["source_leakage_"+group]+=1;continue
                if keys["text"] in seen or base_keys["text"] in seen:
                    rejected["generated_duplicate_"+group]+=1;continue
                # Compute ambiguity ONLY from the written fields (not source truth).
                possible,provs=code_answer(units,vis,tree)
                possible_codes=set()
                for w in possible:
                    possible_codes|=(set(dm.dich_xa("cu",w.ma)) if tree=="cu" else {w.ma})
                p_codes=set()
                for p in provs:
                    p_codes|=(set(dm.dich_tinh("cu",p.ma)) if tree=="cu" else {p.ma})
                if not vis.get("tinh") and possible_codes:
                    p_codes={dm.lay("moi",x).ma_cha for x in possible_codes}
                unique_ward=len(possible_codes)==1 and len(possible)==1
                unique_province=len(p_codes)==1
                ambiguous=not(unique_ward and unique_province)
                answers.append({"id":f"UNGVIEN_{len(answers)+801:04d}",
                    "dau_vao":text,"nhom":group,"mode":mode,
                    "spans":spans,
                    "ma_xa":next(iter(possible_codes)) if unique_ward else "",
                    "ma_tinh":next(iter(p_codes)) if unique_province else "",
                    "khong_xac_dinh":ambiguous,
                    "ly_do_mo_ho":"khong_phan_biet_duoc_ngu_canh_danh_muc" if ambiguous else "",
                    "so_ung_vien_xa":len(possible_codes),
                    "ma_xa_goc_bi_an":candidate.ma,
                    "ma_tinh_goc_bi_an":province.ma,
                    "chuoi_nguon_day_du":base_text})
                groups[group]+=1
                for k,v in keys.items():
                    if v:pooled[k].add(v)
                seen.add(keys["text"]);seen.add(base_keys["text"])
            except KeyError:
                rejected["unmapped_"+group]+=1
        if groups[group]!=requested[group]:
            raise RuntimeError(f"Cannot make {requested[group]} unique examples for group {group}; got {groups[group]}")
    # Mix groups before giving to annotators; IDs resemble the real sample IDs.
    rng.shuffle(answers)
    # Keep IDs unique as generated; order mixed across groups.
    return answers,{"seed":SEED,"groups":dict(groups),"rejected":dict(rejected),
                    "sample_count":N,"test_labels_accessed":False}

def csv_bytes(records):
    buffer=io.StringIO(newline="")
    wr=csv.DictWriter(buffer,fieldnames=["id","dau_vao"],lineterminator="\r\n")
    wr.writeheader()
    wr.writerows({"id":x["id"],"dau_vao":x["dau_vao"]} for x in records)
    return ("\ufeff"+buffer.getvalue()).encode("utf8")

def run():
    ap=argparse.ArgumentParser()
    ap.add_argument("--verify",action="store_true")
    args=ap.parse_args()
    rows,stats=synthetic()
    public=csv_bytes(rows)
    digest=hashlib.sha256(public).hexdigest()
    output=HERE/"tong_hop_dau_vao.csv"
    if args.verify:
        if not output.is_file() or output.read_bytes()!=public:
            raise AssertionError("Synthetic input is not reproducible")
        print("TONG_HOP_REPRODUCIBLE_PASS",digest,flush=True)
        return
    if output.exists() or (HERE/"tong_hop_dap_an.json").exists():
        raise FileExistsError("Synthetic set is locked. Use --verify to compare.")
    output.write_bytes(public)
    private=[{k:v for k,v in r.items() if k not in ("ma_xa_goc_bi_an","ma_tinh_goc_bi_an","chuoi_nguon_day_du")}
             for r in rows]
    (HERE/"tong_hop_dap_an.json").write_text(
        json.dumps({"not_gold":True,"construction_known_answer":True,"seed":SEED,
                    "sample_sha256":digest,"items":private},ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    (HERE/"doi_chieu_id_RIENG_KHONG_GUI_AI.json").write_text(
        json.dumps({r["id"]:{"origin_ward":r["ma_xa_goc_bi_an"],
                             "origin_province":r["ma_tinh_goc_bi_an"],
                             "origin_full":r["chuoi_nguon_day_du"],
                             "group":r["nhom"]} for r in rows},ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    (HERE/"thong_ke_sinh.json").write_text(
        json.dumps({**stats,"sha256_input":digest},ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    print("TONG_HOP_CREATED",len(rows),"GROUPS",stats["groups"],
          "SHA256",digest,"REJECTED",stats["rejected"],flush=True)
if __name__=="__main__":run()
