import csv
import json
from collections import Counter
from pathlib import Path
from src.danh_muc import DanhMuc
from src.char_cnn import BoTachCharCNN
from src.xep_hang import BoXepHang
from src.chuan_ten_duong import TuDienDuong
from src.chuan_hoa import BoChuanHoa
from danh_gia.chay_ban_thu import CORE, norm

dm = DanhMuc()
char_model = Path("mo_hinh/thu_nghiem/char_v2_01/char_cnn.pt")
ranker_p = Path("mo_hinh/thu_nghiem/char_v2_01/ranker.txt")
td_p = Path("danh_gia/ket_qua/tu_dien_duong_v5.json")

extractor = BoTachCharCNN(char_model)
pipeline = BoChuanHoa(
    danh_muc=dm,
    bo_tach=extractor,
    bo_xep_hang=BoXepHang(ranker_p, extractor.ma_bam, dm.ma_bam),
    tu_dien_duong=TuDienDuong(td_p),
    bao_ve_duong=True,
    tien_to_mac_dinh=True
)

rows = list(csv.DictReader(open("data/train_dev/dev.csv", encoding="utf-8-sig")))
fail_fields = Counter()
total_fail = 0
examples = []

for r in rows:
    inp = r.get("dau_vao", "").strip()
    res = pipeline.chuan_hoa(inp)
    diffs = [f for f in CORE if norm(r[f]) != norm(getattr(res, f, ""))]
    if diffs:
        total_fail += 1
        fail_fields.update(diffs)
        if len(examples) < 25:
            examples.append({
                "id": r.get("id"),
                "inp": inp,
                "diffs": {f: {"ref": r[f], "pred": getattr(res, f, "")} for f in diffs}
            })

print(f"Total failed on dev.csv: {total_fail}/{len(rows)} (Accuracy: {round(100*(len(rows)-total_fail)/len(rows), 2)}%)")
print("Failure frequency by field:")
for f, cnt in fail_fields.most_common():
    print(f"  {f}: {cnt}")

print("\nFirst 15 failure examples on dev.csv:")
for ex in examples[:15]:
    print(f"ID: {ex['id']} | INP: {ex['inp']}")
    for f, d in ex['diffs'].items():
        print(f"   [{f}] ref: '{d['ref']}' vs pred: '{d['pred']}'")
