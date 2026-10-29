"""Đo tiền xử lý/định dạng riêng, tính lại F1 model từ prediction đã lưu.

Không chạy lại full inference, không đổi nhãn hoặc gọi API mô hình.
"""
import csv
import hashlib
import json
import unicodedata
from collections import Counter
from pathlib import Path

from src.tien_xu_ly import token_co_vi_tri, nfc_offsets, bo_dau
from src.dinh_dang import dinh_dang_span

ROOT=Path(__file__).resolve().parents[1]
FIELDS=('so_nha','ngo_ngach_hem','thon_xom','duong')
def read(p):return [json.loads(s) for s in p.read_text(encoding='utf-8').splitlines() if s.strip()]
def norm(s):return ' '.join(unicodedata.normalize('NFC',s).casefold().split())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def metrics(c):
    return {**dict(c),'precision_pct':100*c['tp']/c['predicted'] if c['predicted'] else None,
            'recall_pct':100*c['tp']/c['reference'] if c['reference'] else None,
            'f1_pct':200*c['tp']/(c['predicted']+c['reference']) if c['predicted']+c['reference'] else None}


def run():
    out=ROOT/'danh_gia/ket_qua/tung_module_v1_01';out.mkdir(parents=True,exist_ok=False)
    base=ROOT/'mo_hinh/thu_nghiem/char_v1_01'
    report={'scope':'Không phải gold độc lập. Tiền xử lý đo mới; F1 model tính lại từ raw prediction đã lưu trước refactor.',
            'no_training':True,'datasets':{}}
    failures=[]
    for split,filename in [('dev_goc','dev.csv'),('dev_kho','dev_kho.csv')]:
        refs=list(csv.DictReader((base/'snapshot'/filename).open(encoding='utf-8-sig')))
        gold={r['id']:r for r in read(base/'data'/f'{split}.jsonl')}
        structural=Counter();capacity=Counter();formatting=Counter()
        for row in refs:
            raw=row['dau_vao'];tokens=token_co_vi_tri(raw);nfc,offsets=nfc_offsets(raw)
            occupied=set();bad=False
            for t in tokens:
                if not 0<=t.bat_dau<t.ket_thuc<=len(raw) or unicodedata.normalize('NFC',raw[t.bat_dau:t.ket_thuc])!=t.chu or occupied.intersection(range(t.bat_dau,t.ket_thuc)):
                    bad=True
                occupied.update(range(t.bat_dau,t.ket_thuc))
            expected={i for i,c in enumerate(raw) if not c.isspace()}
            structural['rows']+=1;structural['valid_offsets_no_overlap']+=not bad
            structural['all_nonspace_characters_covered']+=expected<=occupied
            nfc_ok=nfc==unicodedata.normalize('NFC',raw) and len(offsets)==len(nfc) and all(nfc[i] in unicodedata.normalize('NFC',raw[a:b]) for i,(a,b) in enumerate(offsets))
            structural['valid_NFC_mapping']+=nfc_ok
            if bad or not nfc_ok or not expected<=occupied:failures.append({'id':row['id'],'type':'preprocessing_invariant'})
            if row['id'] in gold:
                aligned=True;starts={t.bat_dau for t in tokens};ends={t.ket_thuc for t in tokens}
                for field,a,b in gold[row['id']]['detail_spans_raw']:
                    ok=a in starts and b in ends
                    capacity['spans']+=1;capacity['spans_with_lexical_boundaries']+=ok
                    aligned &= ok
                    expected_value=row[field]
                    if not expected_value:
                        formatting['span_without_unique_canonical_reference']+=1
                        continue
                    # Nhập span reference hoàn hảo, đo riêng phép định dạng.
                    value,_=dinh_dang_span([t.chu for t in token_co_vi_tri(raw[a:b])],field)
                    formatting['reference_nonempty']+=1
                    formatting['exact_value']+=norm(value)==norm(expected_value)
                    formatting['same_after_removing_accents']+=bo_dau(norm(value))==bo_dau(norm(expected_value))
                capacity['rows_with_span_labels']+=1;capacity['rows_all_boundaries_aligned']+=aligned
        models={}
        for method,folder,prefix in [('cnn','char_v1_01_cuoi','char'),('videberta','videberta_v1_01_colab','videberta')]:
            path=ROOT/'danh_gia/ket_qua'/folder/f'{prefix}_spans_{split}.jsonl'
            counts=Counter();fields={f:Counter() for f in FIELDS}
            preds=read(path)
            assert {r['id'] for r in preds}==set(gold)
            for rec in preds:
                g={tuple(s) for s in rec['reference_details']}
                p={tuple(s) for s in rec['predicted_spans'] if s[0] in FIELDS}
                assert g=={tuple(s) for s in gold[rec['id']]['detail_spans_raw']}
                counts.update(tp=len(g&p),reference=len(g),predicted=len(p),rows=1,all_spans_exact=int(g==p))
                for f in FIELDS:
                    gf={s for s in g if s[0]==f};pf={s for s in p if s[0]==f}
                    fields[f].update(tp=len(gf&pf),reference=len(gf),predicted=len(pf))
            models[method]={'micro':metrics(counts),'by_field':{f:metrics(c) for f,c in fields.items()},'prediction_sha256':sha(path)}
        report['datasets'][split]={'input_sha256':sha(base/'snapshot'/filename),'preprocessing_invariants':dict(structural),
                                  'lexical_boundary_capacity_not_accuracy':dict(capacity),
                                  'formatting_with_reference_spans_not_model_accuracy':dict(formatting),
                                  'models_raw_spans':models}
    (out/'thong_ke.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    (out/'failures.json').write_text(json.dumps(failures,ensure_ascii=False,indent=2),encoding='utf-8')
    for split,r in report['datasets'].items():
        print(json.dumps({'split':split,**r},ensure_ascii=False))
    assert not failures,failures


if __name__=='__main__':run()
