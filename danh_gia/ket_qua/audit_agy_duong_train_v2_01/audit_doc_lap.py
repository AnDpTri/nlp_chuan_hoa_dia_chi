"""Đọc snapshot; không ghi vào gói bàn giao hoặc chạy builder."""
import csv
import hashlib
import json
from collections import Counter,defaultdict
from pathlib import Path
from urllib.parse import urlsplit

OUT=Path(__file__).resolve().parent
ROOT=OUT/'repo_snapshot'
def csvrows(p):return list(csv.DictReader(p.open(encoding='utf-8-sig',newline='')))
def jsonrows(p):return [json.loads(s) for s in p.read_text(encoding='utf-8').splitlines() if s.strip()]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

train=ROOT/'data/train_dev/bo_sung_v2'
rows=csvrows(train/'train_bo_sung_v2.csv')
spans={r['id']:r for r in jsonrows(train/'train_spans_v2.jsonl')}
tokens={r['id']:r for r in jsonrows(train/'token_spans_v2.jsonl')}
counts=Counter(); examples=defaultdict(list)
for r in rows:
    s=spans[r['id']]; t=tokens[r['id']]
    counts['canonical_usable']+=t['usable_for_canonical_training']
    counts['runtime_compatible']+=t['tokenizer_runtime_compatible']
    occupied=set()
    for f,v in s['spans'].items():
        if v:
            a,b=v['start'],v['end']
            counts['invalid_char_span']+=not(0<=a<b<=len(r['dau_vao']) and r['dau_vao'][a:b]==v['text'])
            counts['overlapping_char_span']+=bool(occupied.intersection(range(a,b)))
            occupied.update(range(a,b))
        if r[f] and not v:
            counts['nonempty_label_without_span_'+f]+=1
            counts['canonical_usable_nonempty_label_without_span_'+f]+=t['usable_for_canonical_training']
            if len(examples[f])<4:
                examples[f].append({'id':r['id'],'input':r['dau_vao'],'field':f,'label':r[f],
                                    'canonical_usable':t['usable_for_canonical_training'],'span':v,
                                    'parent_id':r['parent_id']})
    for tok in t['tokens']:
        counts['invalid_token_offset']+=r['dau_vao'][tok['start']:tok['end']]!=tok['token']
    counts['csv_input_differs_spans']+=r['dau_vao']!=s['dau_vao'] or r['dau_vao']!=t['dau_vao']

streets=ROOT/'data/duong/v1'
roads=jsonrows(streets/'danh_muc_duong.jsonl')
sources=json.loads((streets/'sources/sources_manifest.json').read_text(encoding='utf-8'))['sources']
source_info=[]
for s in sources:
    source_info.append({'file':s['filename'],'hash_matches':sha(ROOT/s['path'])==s['sha256'],
                        'url':s['url'],'is_homepage':urlsplit(s['url']).path in ('','/') and not urlsplit(s['url']).query,
                        'has_fetch_time':'fetched_at_utc' in s,'has_http_status':'http_status' in s})
newcodes={r['ma_tinh'] for r in csvrows(ROOT/'data/clean/moi_tinh.csv')}
bad_era=[r for r in roads if r['administrative_era']=='hien_hanh' and r['ma_tinh'] not in newcodes]
report={'train':{'rows':len(rows),'families':len({r['family_id'] for r in rows}),
                  'max_rows_per_family':max(Counter(r['family_id'] for r in rows).values()),
                  'counts':dict(counts),'examples':dict(examples)},
        'roads':{'rows':len(roads),'unique_names':len({r['canonical_name'] for r in roads}),
                 'sources':source_info,'claimed_current_era_but_code_not_in_new_catalogue':len(bad_era),
                 'bad_era_examples':bad_era[:4],
                 'source_generation':'generate_sources.py writes imported definitions/*.py lists into source .txt files; this is not fetched independent evidence',
                 'wrong_external_reference':{'url':'https://vanban.chinhphu.vn/?docid=204000&pageid=27160',
                     'claimed':'1454/QĐ-TTg, quy hoạch mạng lưới đường bộ',
                     'observed_on_official_page':'89/QĐ-TCTĐB, Quy chế hoạt động Tổ công tác đặc biệt, 09-09-2021'}}}
(OUT/'KIEM_TRA_DOC_LAP.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'train':{'rows':len(rows),'families':report['train']['families'],'counts':dict(counts)},
                  'roads':{'rows':len(roads),'unique_names':report['roads']['unique_names'],'bad_era':len(bad_era),
                           'homepages':sum(s['is_homepage'] for s in source_info)}},ensure_ascii=False,indent=2))
