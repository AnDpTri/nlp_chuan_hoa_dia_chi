"""Read-only 2025 target view: types come from the dated national conversion workbook.

No edits to data/clean. Codes, parent links and cleaned names still come from that catalogue.
"""
import csv
import hashlib
import json
import re
import xml.etree.ElementTree as ET
import zipfile
import unicodedata
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT.parent / 'raw/goc/conversion-table.xlsx'
URL = 'https://raw.githubusercontent.com/zindont/vietnam-address-kit/main/data/source/conversion-table.xlsx'
NS = {'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}

@lru_cache(maxsize=1)
def snapshot():
    digest = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    saved = ROOT / 'asof2025_manifest.json'
    if saved.exists() and json.loads(saved.read_text(encoding='utf-8'))['source_sha256'] != digest:
        raise ValueError('2025 source workbook changed')
    provinces, wards = {}, {}
    with zipfile.ZipFile(SOURCE) as z:
        strings = [''.join(t.text or '' for t in si.iter('{'+NS['m']+'}t'))
                   for si in ET.fromstring(z.read('xl/sharedStrings.xml'))]
        for row in ET.fromstring(z.read('xl/worksheets/sheet2.xml')).findall('m:sheetData/m:row',NS):
            cells = {}
            for cell in row.findall('m:c',NS):
                value = cell.find('m:v',NS)
                text = value.text if value is not None else ''
                cells[re.sub(r'\d','',cell.attrib['r'])] = unicodedata.normalize('NFC',strings[int(text)] if cell.attrib.get('t') == 's' and text else text)
            province = re.fullmatch(r'(Thành phố|Tỉnh)\s+(.+?)\s+\((\d{2})\)',cells.get('A','').strip())
            code = cells.get('C','').strip()
            ward_text = cells.get('B','').strip()
            if ward_text.startswith('Xa '): ward_text = 'Xã ' + ward_text[3:]
            ward = re.fullmatch(r'(Phường|Xã|Đặc khu)\s+(.+)',ward_text)
            if not (province and code.isdigit() and ward): continue
            pc = province[3]; code = code.zfill(5)
            p = {'kind':province[1], 'name':province[2], 'cell':'A'+row.attrib['r']}
            w = {'kind':ward[1], 'name':ward[2], 'province':pc, 'cell':'B'+row.attrib['r']}
            if pc in provinces and provinces[pc]['kind'] != p['kind']: raise ValueError('Conflicting workbook province types')
            if code in wards and (wards[code]['kind'],wards[code]['province']) != (w['kind'],w['province']):
                raise ValueError('Conflicting workbook ward types')
            provinces.setdefault(pc,p); wards.setdefault(code,w)
    if len(provinces) != 34 or len(wards) != 3321: raise ValueError('Incomplete 2025 source snapshot')
    return provinces, wards, digest

def target_view(province_rows, ward_rows):
    provinces, wards, digest = snapshot()
    if set(provinces) != {r['ma_tinh'] for r in province_rows}: raise ValueError('2025 province code mismatch')
    if set(wards) != {r['ma_xa'] for r in ward_rows}: raise ValueError('2025 ward code mismatch')
    ps, ws, changes = [], [], []
    for level, rows, official, dest, key, kind in [('tinh',province_rows,provinces,ps,'ma_tinh','loai_tinh'),
                                                 ('xa',ward_rows,wards,ws,'ma_xa','loai_xa')]:
        for original in rows:
            r = dict(original); source = official[r[key]]
            if level == 'xa' and r['ma_tinh'] != source['province']: raise ValueError('2025 parent-code mismatch')
            if r[kind] != source['kind']:
                changes.append({'cap':level, 'ma':r[key], 'ten_clean':r['ten_'+level],
                                'loai_clean':r[kind], 'loai_moc_2025':source['kind'],
                                'o_nguon':"'Tổng hợp_không merge '!"+source['cell']})
            r[kind] = source['kind']; dest.append(r)
    return ps, ws, changes, digest

def main():
    def read(name):
        with (ROOT.parent/'clean'/name).open(encoding='utf-8-sig',newline='') as f: return list(csv.DictReader(f))
    ps, ws, changes, digest = target_view(read('moi_tinh.csv'),read('moi_tinh_xa.csv'))
    with (ROOT/'asof2025_overrides.csv').open('w',encoding='utf-8',newline='') as out:
        writer = csv.DictWriter(out,fieldnames=['cap','ma','ten_clean','loai_clean','loai_moc_2025','o_nguon'],lineterminator='\n')
        writer.writeheader(); writer.writerows(changes)
    report = {'as_of':'2025-07-01','source_url':URL,'source_sha256':digest,
              'sheet':'Tổng hợp_không merge ', 'province_count':len(ps),'ward_count':len(ws),
              'city_count':sum(r['loai_tinh']=='Thành phố' for r in ps),
              'type_overrides':len(changes),'policy':'Read-only target view; clean input files unchanged.'}
    (ROOT/'asof2025_manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8',newline='\n')
    print(json.dumps(report,ensure_ascii=True,indent=2))

if __name__ == '__main__': main()
