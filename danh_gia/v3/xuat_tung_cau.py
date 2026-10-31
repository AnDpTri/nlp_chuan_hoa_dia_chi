"""Chạy pipeline trên tập test cũ (đã mở để phát triển), ghi đầu ra từng câu (+ chẩn đoán nếu có).
Dùng: CODE_ROOT=<mã> xuat_tung_cau.py <char_cnn.pt> <ranker.txt> <out.jsonl> [test.csv]"""
import csv, json, os, sys
from dataclasses import asdict
from pathlib import Path

import duong_dan as dd  # gốc repo, CODE_ROOT vào sys.path
from src.danh_muc import DanhMuc  # noqa: E402
from src.char_cnn import BoTachCharCNN  # noqa: E402
from src.xep_hang import BoXepHang  # noqa: E402
from src.chuan_ten_duong import TuDienDuong  # noqa: E402
from src.chuan_hoa import BoChuanHoa  # noqa: E402

cnn, ranker, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
test = sys.argv[4] if len(sys.argv) > 4 else dd.TEST
dm = DanhMuc(); ext = BoTachCharCNN(cnn, threads=1)
pipe = BoChuanHoa(danh_muc=dm, bo_tach=ext, bo_xep_hang=BoXepHang(ranker, ext.ma_bam, dm.ma_bam),
                  tu_dien_duong=TuDienDuong(dd.TU_DIEN_TRAIN),
                  bao_ve_duong=True, tien_to_mac_dinh=False)
co_cd = hasattr(pipe, 'chuan_hoa_chan_doan')
with open(out, 'w', encoding='utf-8', newline='\n') as f:
    for r in csv.DictReader(open(test, encoding='utf-8-sig')):
        if co_cd:
            kq, cd = pipe.chuan_hoa_chan_doan(r['dau_vao'])
        else:
            kq, cd = pipe.chuan_hoa(r['dau_vao']), None
        f.write(json.dumps({'id': r['id'], 'out': asdict(kq), 'chan_doan': cd}, ensure_ascii=False) + '\n')
print('xong', out)
