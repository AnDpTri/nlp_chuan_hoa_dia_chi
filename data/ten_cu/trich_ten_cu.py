"""Trích bảng bí danh/tên cũ (huyện, xã) từ dataset.db của gói vietnamadminunits (MIT, tranngocminhhieu).

Chạy: python trich_ten_cu.py <duong_dan_dataset.db> <thu_muc_ra>
Ra: ten_cu_alias.csv gồm cap, ma_cu, ma_tinh_cu, khoa_alias (đã bỏ dấu, bỏ khoảng trắng).
Không lấy bí danh tỉnh (chỉ là viết tắt như 'hn').
"""
import csv
import json
import sqlite3
import sys
from pathlib import Path


def main(db, ra):
    con = sqlite3.connect(db)
    cap = {}
    for pc, dc, wc, da, wa in con.execute(
            'select provinceCode, districtCode, wardCode, districtAlias, wardAlias from admin_units_legacy'):
        for ten, ma, a in (('huyen', dc, da), ('xa', wc, wa)):
            if a:
                for k in json.loads(a):
                    cap[(ten, ma, k)] = pc
    dong = sorted((t, m, k, p) for (t, m, k), p in cap.items())
    out = Path(ra) / 'ten_cu_alias.csv'
    with open(out, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f, lineterminator='\n')
        w.writerow(['cap', 'ma_cu', 'ma_tinh_cu', 'khoa_alias'])
        for t, m, k, p in dong:
            w.writerow([t, m, p, k])
    print(len(dong), 'dong ->', out)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
