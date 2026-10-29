from danh_gia.do_kiem_tra_test400 import danh_gia_test_set
from src.danh_muc import DanhMuc
from src.char_cnn import BoTachCharCNN
from src.xep_hang import BoXepHang
from src.chuan_ten_duong import TuDienDuong
from src.chuan_hoa import BoChuanHoa
from pathlib import Path

dm = DanhMuc()
m = BoTachCharCNN("mo_hinh/thu_nghiem/char_v2_01/char_cnn.pt")
td = TuDienDuong("danh_gia/ket_qua/tu_dien_duong_v2.json")
rk = BoXepHang("mo_hinh/thu_nghiem/char_v2_01/ranker.txt", m.ma_bam, dm.ma_bam)
pipeline = BoChuanHoa(
    danh_muc=dm,
    bo_tach=m,
    bo_xep_hang=rk,
    tu_dien_duong=td,
    bao_ve_duong=True,
    tien_to_mac_dinh=False,
)

res = danh_gia_test_set(pipeline)
print("=== Tap da duyet AI (292 mau) ===")
print("Exact 6 fields:", res["tap_da_duyet_ai_292_mau"]["dung_toan_bo_6_truong"], "/ 292")
for f, info in res["tap_da_duyet_ai_292_mau"]["tung_truong"].items():
    print(f"  {f}: {info['dung']}/292 ({info['ty_le_khop_pct']}%)")

print("\n=== Tap can duyet (108 mau) ===")
print("Exact 6 fields:", res["tap_can_duyet_108_mau"]["dung_toan_bo_6_truong"], "/ 108")
for f, info in res["tap_can_duyet_108_mau"]["tung_truong"].items():
    print(f"  {f}: {info['dung']}/108 ({info['ty_le_khop_pct']}%)")
