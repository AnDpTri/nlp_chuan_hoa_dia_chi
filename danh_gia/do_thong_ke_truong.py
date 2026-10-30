import sys
from danh_gia.do_kiem_tra_test400 import danh_gia_test_set
from src.danh_muc import DanhMuc
from src.char_cnn import BoTachCharCNN
from src.xep_hang import BoXepHang
from src.chuan_ten_duong import TuDienDuong
from src.chuan_hoa import BoChuanHoa
from pathlib import Path

dm = DanhMuc()
m = BoTachCharCNN("mo_hinh/thu_nghiem/char_v3_tc/char_cnn.pt")
td = TuDienDuong("danh_gia/ket_qua/tu_dien_duong_v5.json")
rk = BoXepHang("mo_hinh/thu_nghiem/char_v3_tc/ranker.txt", m.ma_bam, dm.ma_bam)

pipeline = BoChuanHoa(
    danh_muc=dm,
    bo_tach=m,
    bo_xep_hang=rk,
    tu_dien_duong=td,
    bao_ve_duong=True,
    tien_to_mac_dinh=False,  # Schema test: các trường chi tiết là giá trị thô.
)

res = danh_gia_test_set(pipeline)
for key, name in (("tap_da_duyet_ai_292_mau", "Tap da duyet AI"),
                  ("tap_can_duyet_108_mau", "Tap can duyet")):
    group = res.get(key)
    if group is None:
        continue
    n = group["so_mau"]
    print(f"=== {name} ({n} mau) ===")
    print("Exact 6 fields:", group["dung_toan_bo_6_truong"], f"/ {n}")
    for f, info in group["tung_truong"].items():
        print(f"  {f}: {info['dung']}/{n} ({info['ty_le_khop_pct']}%)")
