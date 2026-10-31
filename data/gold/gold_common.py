"""Shared, pre-label tooling for provisional Vietnamese address annotations only."""
from __future__ import annotations
import csv
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GOLD = Path(__file__).resolve().parent
EXTERNAL = Path(r"D:\nlp_chuan_hoa_dia_chi")
FIELDS = ("so_nha","ngo_ngach_hem","thon_xom","duong","xa","huyen","tinh")
DETAIL = FIELDS[:4]
ADMIN = FIELDS[4:]

def audit_logic():
    path = EXTERNAL / "data/audit/audit_du_lieu.py"
    spec = importlib.util.spec_from_file_location("_gold_readonly_audit", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

AUDIT = audit_logic()

def sha256(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda:f.read(1024*1024),b""):h.update(block)
    return h.hexdigest()

def source_keys(text,source):
    return {"text":AUDIT.normalize(text), "osm":AUDIT.osm_identity(source),
            "masked":AUDIT.masked_family(text)}

def csv_rows(path, columns=None):
    with Path(path).open(encoding="utf-8-sig",newline="") as f:
        reader=csv.DictReader(f)
        if columns:
            missing=set(columns)-set(reader.fieldnames or [])
            if missing: raise ValueError(f"Missing required columns in {path}: {sorted(missing)}")
        for row in reader:
            if columns:
                yield {key:row.get(key,"") for key in columns}
            else:
                yield row

def jsonl_rows(path):
    with Path(path).open(encoding="utf-8") as f:
        for line in f:
            if line.strip(): yield json.loads(line)

def name_and_source(row):
    text=next((str(row.get(k) or "") for k in ("dau_vao","text","nfc","input") if row.get(k)), "")
    source=next((str(row.get(k) or "") for k in ("nguon","source_url","osm_url","url") if row.get(k)),"")
    if not source and row.get("osm_type") and row.get("osm_id"):
        source=f"https://www.openstreetmap.org/{row['osm_type']}/{row['osm_id']}"
    return text,source

def load_sample(path=None):
    path=Path(path or GOLD/"mau_ung_vien.csv")
    return list(csv_rows(path,("id","dau_vao","nguon","osm_id","input_mode","nhom_tinh","nhom_dac_diem","tang")))

def validate_annotation(row):
    errors=[]
    if not isinstance(row,dict): return ["Mục không phải object"]
    required={"id","dau_vao","spans","abstain","ly_do_abstain"}
    missing=required-set(row)
    if missing: errors.append("Thiếu khóa "+", ".join(sorted(missing)))
    extra=set(row)-required
    if extra: errors.append("Khóa không được phép (bao gồm mã hành chính): "+", ".join(sorted(extra)))
    text=row.get("dau_vao")
    if not isinstance(row.get("id"),str) or not row.get("id"):
        errors.append("id không hợp lệ")
    if not isinstance(text,str) or not text: errors.append("dau_vao phải là chuỗi không rỗng")
    if not isinstance(row.get("abstain"),bool): errors.append("abstain phải là boolean")
    reason=row.get("ly_do_abstain")
    if not isinstance(reason,str) or (row.get("abstain") and not reason.strip()) or (not row.get("abstain") and reason):
        errors.append("ly_do_abstain phải có khi abstain=true, trống khi false")
    spans=row.get("spans")
    if not isinstance(spans,list): return errors+["spans phải là list"]
    used=set()
    for i,span in enumerate(spans):
        if not isinstance(span,dict): errors.append(f"span[{i}]: không phải object");continue
        if set(span)!={"truong","start","end","van_ban"}:
            errors.append(f"span[{i}]: schema phải đúng truong/start/end/van_ban");continue
        field=span["truong"]
        if field not in FIELDS: errors.append(f"span[{i}]: trường không được phép: {field}")
        a,b=span["start"],span["end"]
        if type(a)!=int or type(b)!=int or not isinstance(text,str) or not (0<=a<b<=len(text)):
            errors.append(f"span[{i}]: offset ngoài phạm vi");continue
        if span["van_ban"]!=text[a:b]: errors.append(f"span[{i}]: văn bản không khớp lát cắt")
        occupied=set(range(a,b))
        if occupied&used:errors.append(f"span[{i}]: chồng span")
        used|=occupied
    return errors

def output_json(path,obj):
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    Path(path).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

def output_csv(path,rows,columns):
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    with Path(path).open("w",encoding="utf-8-sig",newline="") as f:
        wr=csv.DictWriter(f,fieldnames=columns,extrasaction="ignore");wr.writeheader();wr.writerows(rows)
