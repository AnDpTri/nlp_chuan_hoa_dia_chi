"""Chạy pipeline (code ở gốc repo, hoặc CODE_ROOT) với CNN/ranker tùy chọn trên dev + bộ khó, ghi đầu ra đầy đủ.
Dùng: chay_mo_hinh.py <char_cnn.pt> <ranker.txt> <out_dir>"""
import csv, json, sys
from dataclasses import asdict
from pathlib import Path

import os
import duong_dan as dd  # gốc repo, CODE_ROOT vào sys.path
from src.tien_xu_ly.char_cnn import BoTachCharCNN
from src.chuan_hoa import BoChuanHoa
from src.tien_xu_ly.chuan_ten_duong import TuDienDuong
from src.danh_muc import DanhMuc
from src.tien_xu_ly.xep_hang import BoXepHang

INP = dd.DEV
KHO = dd.BO_KHO


def main(cnn, ranker, out_dir):
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    dm = DanhMuc(); ext = BoTachCharCNN(Path(cnn), threads=1)
    rk = BoXepHang(Path(ranker), ext.ma_bam, dm.ma_bam)
    pipe = BoChuanHoa(danh_muc=dm, bo_tach=ext, bo_xep_hang=rk, tu_dien_duong=TuDienDuong(dd.TU_DIEN_TRAIN),
                      bao_ve_duong=True, tien_to_mac_dinh=True)
    items = []
    for sp in ('dev_goc', 'dev_kho'):
        for r in csv.DictReader(open(INP / f'{sp}.csv', encoding='utf-8-sig')):
            items.append((sp, r['id'], r['dau_vao']))
    for p in sorted((KHO / 'ra').glob('ra_*.csv')):
        for r in csv.DictReader(open(p, encoding='utf-8')):
            items.append(('kho', r['id'], r['dia_chi']))
    with open(out / 'ket_qua.jsonl', 'w', encoding='utf-8', newline='\n') as f:
        for sp, rid, text in items:
            try:
                res = asdict(pipe.chuan_hoa(text))
            except Exception as e:
                res = {'EXCEPTION': str(e)[:200]}
            f.write(json.dumps({'split': sp, 'id': rid, 'out': res}, ensure_ascii=False) + '\n')
    print('xong', len(items))


if __name__ == '__main__':
    main(*sys.argv[1:4])
