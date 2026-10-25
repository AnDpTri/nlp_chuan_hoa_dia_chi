"""Download a pinned extract and stream public POI addresses (no residential sampling)."""
import argparse
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone
import urllib.request
import osmium

ROOT = Path(__file__).resolve().parents[1]
URL = 'https://download.geofabrik.de/asia/vietnam-261024.osm.pbf'
PUBLIC_KEYS = ('amenity', 'shop', 'office', 'tourism', 'craft', 'healthcare', 'leisure')
ADDRESS_ORDER = ('addr:housenumber', 'addr:street', 'addr:place', 'addr:hamlet', 'addr:village', 'addr:subdistrict', 'addr:suburb',
                 'addr:ward', 'addr:quarter', 'addr:district', 'addr:city',
                 'addr:province', 'addr:state')

def download():
    folder = ROOT / 'goc'
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / URL.rsplit('/', 1)[1]
    was_present = target.exists()
    if not target.exists():
        temporary = target.with_suffix('.part')
        print('Downloading', URL, flush=True)
        with urllib.request.urlopen(URL, timeout=120) as src, temporary.open('wb') as out:
            while chunk := src.read(1024 * 1024):
                out.write(chunk)
        temporary.replace(target)
    with target.open('rb') as stream:
        checksum = hashlib.file_digest(stream, 'md5').hexdigest()
    with urllib.request.urlopen(URL + '.md5', timeout=60) as response:
        upstream_md5 = response.read().decode().split()[0]
    if checksum != upstream_md5:
        raise ValueError('PBF checksum mismatch')
    metadata_path = folder / 'download.json'
    previous = json.loads(metadata_path.read_text(encoding='utf-8')) if was_present and metadata_path.exists() else {}
    retrieved = previous.get('retrieved_utc') if previous.get('url') == URL and previous.get('md5') == checksum else None
    meta = {'url': URL, 'retrieved_utc': retrieved or datetime.now(timezone.utc).isoformat(),
            'bytes': target.stat().st_size, 'md5': checksum, 'md5_verified': True,
            'license': 'ODbL-1.0', 'attribution': '© OpenStreetMap contributors'}
    metadata_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8', newline='\n')
    return target

class PublicAddresses(osmium.SimpleHandler):
    def __init__(self, output):
        super().__init__()
        self.output = output
        self.count = 0
    def visit(self, obj, kind):
        tags = dict(obj.tags)
        if not tags.get('name') or not any(tags.get(k) for k in PUBLIC_KEYS):
            return
        if tags.get('access') == 'private' or tags.get('amenity') in ('bench', 'waste_basket', 'toilets', 'parking_space'):
            return
        full = tags.get('addr:full', '')
        mode = 'addr:full'
        if not full:
            if not (tags.get('addr:street') or tags.get('addr:place')):
                return
            # Preserve every source value verbatim; the separator is explicitly documented.
            parts = []
            for key in ADDRESS_ORDER:
                value = tags.get(key)
                if value and value not in parts:
                    parts.append(value)
            full = ', '.join(parts)
            mode = 'structured_tags_joined'
        if len(full) < 12 or len(full) > 500 or '\n' in full:
            return
        record = {'osm_type': kind, 'osm_id': obj.id,
                  'source_url': f'https://www.openstreetmap.org/{kind}/{obj.id}',
                  'name': tags['name'], 'dau_vao': full, 'input_mode': mode,
                  'tags': {k: v for k, v in tags.items() if k.startswith('addr:') or k in PUBLIC_KEYS or k in ('name', 'website', 'contact:website', 'access')},
                  'osm_version': obj.version, 'osm_timestamp': str(obj.timestamp)}
        self.output.write(json.dumps(record, ensure_ascii=False) + '\n')
        self.count += 1
    def node(self, obj): self.visit(obj, 'node')
    def way(self, obj): self.visit(obj, 'way')
    def relation(self, obj): self.visit(obj, 'relation')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--download-only', action='store_true')
    args = parser.parse_args()
    pbf = download()
    if args.download_only: return
    with (ROOT / 'goc' / 'osm_public_candidates.jsonl').open('w', encoding='utf-8', newline='\n') as out:
        handler = PublicAddresses(out)
        processor = (osmium.FileProcessor(str(pbf))
                     .with_filter(osmium.filter.KeyFilter(*PUBLIC_KEYS))
                     .with_filter(osmium.filter.KeyFilter('addr:full', 'addr:street', 'addr:place'))
                     .with_filter(osmium.filter.KeyFilter('name')))
        for obj in processor:
            kind = {'n': 'node', 'w': 'way', 'r': 'relation'}[obj.type_str()]
            handler.visit(obj, kind)
    print('Public address candidates:', handler.count, flush=True)

if __name__ == '__main__': main()
