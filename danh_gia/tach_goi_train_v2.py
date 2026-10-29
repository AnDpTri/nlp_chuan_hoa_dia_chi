"""Tách bản dùng tiếp từ snapshot audit, không sửa gói agy đang làm."""
import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

from src.danh_muc import DanhMuc
from .du_lieu_char import char_record, family_char
from .chay_ban_thu import ROOT, digest
from .du_lieu_crf import doc_csv, doc_jsonl, ghi_jsonl


def ancestors(rec):
    out=set()
    if re.fullmatch(r'VNTRAIN_\d+',rec['id']):out.add(rec['id'])
    ref=rec['ref']
    out.update(re.findall(r'(?:parent_id=|derived_train:)(VNTRAIN_\d+)',ref.get('ghi_chu','')+';'+ref.get('nguon','')))
    return out


def run():
    snap=ROOT/'danh_gia/ket_qua/audit_agy_duong_train_v2_01/repo_snapshot'
    source=snap/'data/train_dev/bo_sung_v2'
    output=ROOT/'data/train_dev/duyet_v2_01'
    output.mkdir(parents=True,exist_ok=False)
    old=ROOT/'mo_hinh/thu_nghiem/char_v1_01'
    base_cnn=doc_jsonl(old/'data/train_cnn.jsonl')
    base_rank=doc_jsonl(old/'data/train_ranker.jsonl')
    cnn_parents=set().union(*(ancestors(r) for r in base_cnn))
    parent_groups={p:r['training_group'] for r in base_cnn for p in ancestors(r)}
    rank_parents=set().union(*(ancestors(r) for r in base_rank))
    assert not cnn_parents.intersection(rank_parents)
    blocked={family_char(r) for name in ('train_ranker','dev_goc','dev_kho') for r in doc_jsonl(old/'data'/f'{name}.jsonl')}
    seen={r['nfc'].casefold() for r in base_cnn}
    parents={r['id']:r for r in doc_csv(snap/'data/train_dev/train.csv')}
    rows=doc_csv(source/'train_bo_sung_v2.csv')
    span_by_id={r['id']:r for r in doc_jsonl(source/'train_spans_v2.jsonl')}
    token_by_id={r['id']:r for r in doc_jsonl(source/'token_spans_v2.jsonl')}
    dm=DanhMuc(old/'snapshot/clean')
    approved=[]; cnn_new=[]; reserve=[]; excluded=[]; reasons=Counter()
    for row in rows:
        spans=span_by_id[row['id']]['spans'];flags=token_by_id[row['id']]
        why=[]
        if not flags['usable_for_canonical_training']:why.append('nhan_chuan_chua_du_dieu_kien')
        details=[]
        for field,v in spans.items():
            if bool(row[field])!=bool(v):why.append('nhan_span_khong_dong_bo_'+field)
            if v:
                a,b=v['start'],v['end']
                if not 0<=a<b<=len(row['dau_vao']) or row['dau_vao'][a:b]!=v['text']:why.append('sai_offset')
                details.append((field,a,b))
        parent=parents.get(row['parent_id'])
        if not parent:why.append('khong_tim_thay_cha')
        else:
            expected=hashlib.sha256(json.dumps(parent,sort_keys=True).encode('utf-8')).hexdigest()
            if expected!=row['source_row_sha256']:why.append('hash_cha_sai')
            if row['parent_source_url']!=parent['nguon']:why.append('url_cha_sai')
            if any(row[f]!=parent[f] for f in ('ma_xa_cu','ma_huyen_cu','ma_tinh_cu')):why.append('ma_nguon_khac_cha')
        rec=None
        if not why:
            try:
                rec=char_record(row['dau_vao'],details,row,dm)
                rec.update(split='train_bo_sung_v2',canonical_usable=True,training_group='parent:'+row['parent_id'],source_family=row['family_id'])
                if family_char(rec) in blocked:why.append('giao_ho_dev_hoac_ranker')
                if rec['nfc'].casefold() in seen:why.append('trung_input_train_cnn')
            except (ValueError,KeyError) as e:why.append('char_record:'+str(e))
        if why:
            excluded.append({'id':row['id'],'parent_id':row['parent_id'],'reasons':why})
            reasons.update(why)
            continue
        approved.append(row)
        if row['parent_id'] in rank_parents:
            reserve.append({'id':row['id'],'parent_id':row['parent_id'],'reason':'giu_ho_rieng_cho_ranker'})
        elif row['parent_id'] not in cnn_parents:
            reserve.append({'id':row['id'],'parent_id':row['parent_id'],'reason':'cha_chua_co_trong_phan_chia_cnn_ranker_da_dong_bang'})
        else:
            rec['training_group']=parent_groups[row['parent_id']]
            cnn_new.append(rec);seen.add(rec['nfc'].casefold())
    # Kiểm các tên/mã đích trên phần thực dùng, không sửa nhãn để hợp lệ.
    for r in cnn_new:
        for code,name,level in [('ma_xa','xa_phuong','xa'),('ma_tinh','tinh','tinh')]:
            if r['ref'][code]:assert r['ref'][name]==dm.ten_day_du('moi',r['ref'][code]),r['id']
    with (output/'train_da_loc.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(approved)
    ghi_jsonl(output/'train_cnn_bo_sung.jsonl',cnn_new)
    ghi_jsonl(output/'train_cnn_ket_hop.jsonl',base_cnn+cnn_new)
    ghi_jsonl(output/'giu_rieng_theo_ho.jsonl',reserve)
    ghi_jsonl(output/'can_sua.jsonl',excluded)
    summary={'source':'audit snapshot, not live agy directory','source_sha256':{p.name:digest(p) for p in source.iterdir() if p.is_file()},
             'input_rows':len(rows),'passed_local_checks':len(approved),'reserved_by_family':len(reserve),
             'cnn_new_rows':len(cnn_new),'cnn_new_parent_families':len({r['ref']['parent_id'] for r in cnn_new}),
             'cnn_combined_rows':len(base_cnn)+len(cnn_new),'excluded_rows':len(excluded),'reasons_overlapping':dict(reasons),
             'dev_or_ranker_read_only':True,'models_retrained':False,
             'quality':'Chỉ qua cổng kiểm tra này, chưa phải gold/kiểm chứng ngữ nghĩa toàn bộ; chưa đưa vào runtime.'}
    (output/'TONG_KET.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    (output/'MANIFEST.json').write_text(json.dumps({p.name:digest(p) for p in output.iterdir() if p.is_file()},indent=2),encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__=='__main__':run()
