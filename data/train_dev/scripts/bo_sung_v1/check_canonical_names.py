import sys
import csv
import unicodedata
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

PROJECT_DIR = Path(__file__).resolve().parents[4]
CLEAN_DIR = PROJECT_DIR / 'data' / 'clean'
BO_SUNG_DIR = PROJECT_DIR / 'data' / 'train_dev' / 'bo_sung_v1'

new_w = {r['ma_xa']: r for r in csv.DictReader(open(CLEAN_DIR / 'moi_tinh_xa.csv', encoding='utf-8-sig'))}
new_p = {r['ma_tinh']: r for r in csv.DictReader(open(CLEAN_DIR / 'moi_tinh.csv', encoding='utf-8-sig'))}

def canonical_full_name(row, level):
    if not row:
        return ''
    name = unicodedata.normalize('NFC', row['ten_' + level]).strip()
    kind = unicodedata.normalize('NFC', row['loai_' + level]).strip()
    if name.lower().startswith(kind.lower() + ' '):
        return name
    return f"{kind} {name}"

def check_split(split_name):
    csv_path = BO_SUNG_DIR / f"{split_name}.csv"
    rows = list(csv.DictReader(open(csv_path, encoding='utf-8-sig')))
    diffs = []
    for r in rows:
        mx = r.get('ma_xa', '').strip()
        mp = r.get('ma_tinh', '').strip()
        xp = r.get('xa_phuong', '').strip()
        tp = r.get('tinh', '').strip()
        
        expected_xp = canonical_full_name(new_w.get(mx), 'xa') if mx else ''
        expected_tp = canonical_full_name(new_p.get(mp), 'tinh') if mp else ''
        
        if xp != expected_xp:
            diffs.append((r['id'], 'xa_phuong', mx, xp, expected_xp))
        if tp != expected_tp:
            diffs.append((r['id'], 'tinh', mp, tp, expected_tp))
            
    print(f"=== {split_name}: {len(rows)} rows ===")
    print(f"Total mismatches with canonical clean dictionary: {len(diffs)}")
    for d in diffs:
        print(f"  ID={d[0]}: field={d[1]}, code={d[2]}, current='{d[3]}', expected='{d[4]}'")
    return diffs

train_diffs = check_split('train_bo_sung')
dev_diffs = check_split('dev_kho')
