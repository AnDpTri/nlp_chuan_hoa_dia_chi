"""Đo thời gian chuẩn hóa mỗi câu (ms), CPU 1 luồng, cùng 300 câu dev cho mọi mô hình.
Dùng: do_toc_do.py <char_cnn.pt | thu_muc_model_videberta> <ranker.txt> [ten]"""
import csv, sys, time
from pathlib import Path

import duong_dan as dd  # gốc repo, CODE_ROOT vào sys.path
from src.danh_muc import DanhMuc  # noqa: E402
from src.char_cnn import BoTachCharCNN  # noqa: E402
from src.videberta import BoTachViDeberta  # noqa: E402
from src.xep_hang import BoXepHang  # noqa: E402
from src.chuan_ten_duong import TuDienDuong  # noqa: E402
from src.chuan_hoa import BoChuanHoa  # noqa: E402

mo_hinh, ranker = Path(sys.argv[1]), Path(sys.argv[2])
dm = DanhMuc()
ext = BoTachViDeberta(mo_hinh, threads=1) if mo_hinh.is_dir() else BoTachCharCNN(mo_hinh, threads=1)
pipe = BoChuanHoa(danh_muc=dm, bo_tach=ext, bo_xep_hang=BoXepHang(ranker, ext.ma_bam, dm.ma_bam),
                  tu_dien_duong=TuDienDuong(dd.TU_DIEN_TRAIN),
                  bao_ve_duong=True, tien_to_mac_dinh=True)
cau = [r['dau_vao'] for r in csv.DictReader(open(dd.DEV / 'dev_goc.csv', encoding='utf-8-sig'))][:300]
for c in cau[:20]:
    pipe.chuan_hoa(c)  # làm nóng
ms = []
for c in cau:
    t0 = time.perf_counter(); pipe.chuan_hoa(c); ms.append((time.perf_counter() - t0) * 1000)
ms.sort()
print(f"{sys.argv[3] if len(sys.argv) > 3 else mo_hinh.name}: n={len(ms)} trung binh {sum(ms) / len(ms):.1f} ms | "
      f"trung vi {ms[len(ms) // 2]:.1f} | p95 {ms[int(len(ms) * .95)]:.1f}")
