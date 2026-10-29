"""Lưu nguồn công khai và kết quả HTTP thực để đối chiếu hồ sơ pháp lý."""
import concurrent.futures
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import urllib.request

OUT = Path(__file__).resolve().parent
sources = {
    'hanoi_1286_claimed': 'https://xaydungchinhsach.chinhphu.vn/toan-van-nghi-quyet-so-1286-nq-ubtvqh15-sap-xep-don-vi-hanh-chinh-cap-xa-cua-thanh-pho-ha-noi-119241121144810696.htm',
    'hanoi_1286_official': 'https://xaydungchinhsach.chinhphu.vn/nghi-quyet-so-1286-nq-ubtvqh15-ve-viec-sap-xep-don-vi-hanh-chinh-cap-xa-cua-thanh-pho-ha-noi-119241122151657096.htm',
    'hanoi_1656_official': 'https://vanban.chinhphu.vn/?docid=214008&pageid=27160',
    'haiphong_1232_official': 'https://xaydungchinhsach.chinhphu.vn/nghi-quyet-1232-nq-ubtvqh-sap-xep-don-vi-hanh-chinh-thanh-pho-hai-phong-119241103063654234.htm',
}
def fetch(item):
    name, url = item
    record = {'id': name, 'requested_url': url, 'retrieved_at_utc': datetime.now(timezone.utc).isoformat()}
    try:
        request = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(request, timeout=20) as response:
            raw = response.read()
            record.update(http_status=response.status, final_url=response.url,
                          sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))
        (OUT / (name + '.html')).write_bytes(raw)
    except Exception as exc:
        record.update(error_type=type(exc).__name__, error=str(exc))
    return record
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
    results = list(executor.map(fetch, sources.items()))
(OUT / 'legal_source_fetch.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8', newline='\n')
print(json.dumps(results, ensure_ascii=False, indent=2))
