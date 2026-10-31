"""Đánh giá cuối trên tập test 400 (chỉ đọc, không dùng để chỉnh). Cùng bộ chấm danh_gia_test_set của nhánh hai module.
Dùng: CODE_ROOT=<mã> chay_test.py <char_cnn.pt> <ranker.txt> <ten> """
import importlib.util, json, os, sys
from pathlib import Path

import duong_dan as dd  # gốc repo, CODE_ROOT vào sys.path
CODE = str(dd.CODE_ROOT)
from src.danh_muc import DanhMuc  # noqa: E402
from src.char_cnn import BoTachCharCNN  # noqa: E402
from src.xep_hang import BoXepHang  # noqa: E402
from src.chuan_ten_duong import TuDienDuong  # noqa: E402
from src.chuan_hoa import BoChuanHoa  # noqa: E402

spec = importlib.util.spec_from_file_location('cham', dd.CODE_ROOT / 'danh_gia' / 'do_kiem_tra_test400.py')
cham = importlib.util.module_from_spec(spec); spec.loader.exec_module(cham)

cnn, ranker, ten = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
dm = DanhMuc(); ext = BoTachCharCNN(cnn, threads=1)
pipe = BoChuanHoa(danh_muc=dm, bo_tach=ext, bo_xep_hang=BoXepHang(ranker, ext.ma_bam, dm.ma_bam),
                  tu_dien_duong=TuDienDuong(dd.TU_DIEN_TRAIN),
                  bao_ve_duong=True, tien_to_mac_dinh=os.environ.get("TIEN_TO", "0") == "1")
kq = cham.danh_gia_test_set(pipe, dd.TEST)
out = (dd.KET_QUA / 'test400') / f'{ten}.json'
out.write_text(json.dumps(kq, ensure_ascii=False, indent=2), encoding='utf-8')
toan = kq['toan_bo_400_mau']
print(ten, '| 400 mẫu: đúng 6 trường', toan['dung_toan_bo_6_truong'], f"({toan['khop_toan_bo_6_truong_pct']}%)")
for k, v in kq.items():
    if isinstance(v, dict) and 'khop_toan_bo_6_truong_pct' in v and k != 'toan_bo_400_mau':
        print(f"   {k}: {v['dung_toan_bo_6_truong']}/{v['so_mau']} ({v['khop_toan_bo_6_truong_pct']}%)")
print('   từng trường:', {f: m['ty_le_khop_pct'] for f, m in toan['tung_truong'].items() if f in ('so_nha', 'ngo_ngach_hem', 'thon_xom', 'duong', 'ma_xa', 'ma_tinh')})
