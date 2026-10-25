"""Pin the six read-only administrative inputs; refuse silent changes during replay."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = ('moi_tinh.csv','moi_tinh_xa.csv','cu_tinh.csv','cu_huyen.csv',
         'cu_tinh_huyen_xa.csv','doi_chieu_xa_cu_moi.csv')

def verify():
    actual = {name:hashlib.sha256((ROOT.parent/'clean'/name).read_bytes()).hexdigest() for name in FILES}
    manifest = ROOT/'catalogue_manifest.json'
    if manifest.exists():
        expected = json.loads(manifest.read_text(encoding='utf-8'))
        if actual != expected: raise ValueError('Administrative inputs changed: review corpus version before rebuilding')
    else:
        manifest.write_text(json.dumps(actual,indent=2),encoding='utf-8',newline='\n')
    return actual

if __name__ == '__main__':
    verify(); print('Catalogue fingerprints verified/pinned')
