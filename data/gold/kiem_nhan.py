"""Validate candidate labels, source offsets and exact sample identity; no third-party libs."""
import argparse,json
from pathlib import Path
from gold_common import GOLD,validate_annotation,load_sample

def validate_bundle(bundle,expected=None):
    errors=[]
    if not isinstance(bundle,dict):
        return ["Bundle không phải object"]
    if set(bundle)!={"bo_gan","nhan"}:
        errors.append("Bundle chỉ được chứa bo_gan và nhan")
    if not isinstance(bundle.get("bo_gan"),str) or not bundle.get("bo_gan"):
        errors.append("bo_gan thiếu hoặc sai kiểu")
    rows=bundle.get("nhan")
    if not isinstance(rows,list):
        return errors+["nhan phải là list"]
    seen=set()
    for i,r in enumerate(rows):
        key=r.get("id","?") if isinstance(r,dict) else "?"
        prefix=f"nhan[{i}] id={key}: "
        if key in seen:errors.append(prefix+"id trùng")
        seen.add(key)
        errors.extend(prefix+e for e in validate_annotation(r))
        if expected is not None and isinstance(r,dict):
            if key not in expected:
                errors.append(prefix+"id không nằm trong gói mẫu")
            elif r.get("dau_vao") != expected[key]:
                errors.append(prefix+"dau_vao không đúng chuỗi gốc")
    if expected is not None:
        omitted=set(expected)-seen
        if omitted:errors.append("Thiếu mục trong gói: "+", ".join(sorted(omitted)[:15]))
        if len(rows)!=len(expected):errors.append(f"Thiếu/thừa số mục: {len(rows)} vs {len(expected)}")
    return errors

def check_file(path,expected=None):
    try:
        content=json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except (ValueError,OSError) as e:
        return None,[f"Không đọc được JSON {path}: {e}"]
    return content,validate_bundle(content,expected)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("label_file",type=Path)
    ap.add_argument("--sample",type=Path,help="CSV mẫu chứa id/dau_vao; bắt buộc so khớp toàn bộ")
    a=ap.parse_args()
    expected={r["id"]:r["dau_vao"] for r in load_sample(a.sample)} if a.sample else None
    b,errors=check_file(a.label_file,expected)
    if errors:
        for e in errors:print("INVALID",e)
        raise SystemExit(1)
    print("NHAN_UNG_VIEN_PASS",len(b["nhan"]),"bo_gan",b["bo_gan"])
if __name__=="__main__":main()
