"""Chỉ chạy trên repo_snapshot cạnh script, không ghi dự án thật."""
import contextlib
import csv
import io
import json
from pathlib import Path
import shutil
import sys
import unicodedata

WORK=Path(__file__).resolve().parent
ROOT=WORK/'repo_snapshot'
sys.path.insert(0,str(ROOT/'data/test/scripts'))
import ai_review_engine as engine
import validate_dataset as validator
from build_labels import full

def read(path):
    with path.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))

def save(path, rows):
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def main():
    cat=engine.Catalogues()
    outputs=[]
    for mode in ['absent_current_output','house_substring_81','house_role_district','unobserved_valid_admin_chain']:
        dest=WORK/('fixture_'+mode)
        dest.mkdir(exist_ok=False)
        for name in ['dia_chi_test.csv','bang_duyet_test.csv']:
            shutil.copyfile(ROOT/'data/test'/name,dest/name)
        rows=read(dest/'dia_chi_test.csv')
        row=next(r for r in rows if r['id']=='VNTEST0001')
        if mode=='absent_current_output':row['duong']='ABSENT FROM INPUT SENTINEL'
        if mode=='house_substring_81':row['so_nha']='Số 81'
        if mode=='house_role_district':row['so_nha']='Số Tân Phú'
        if mode=='unobserved_valid_admin_chain':
            old=next(w for w in cat.old_w if w['ten_xa']=='Bến Nghé' and len({m['ma_xa_moi'] for m in cat.to_new[w['ma_xa']]})==1)
            target=cat.new_wi[cat.to_new[old['ma_xa']][0]['ma_xa_moi']]
            row.update(ma_xa_cu=old['ma_xa'],ma_huyen_cu=old['ma_huyen'],ma_tinh_cu=old['ma_tinh'],
                       ma_xa=target['ma_xa'],ma_tinh=target['ma_tinh'],xa_phuong=full(target,'xa'),tinh=full(cat.new_pi[target['ma_tinh']],'tinh'))
        inserted={k:row[k] for k in ['so_nha','duong','ma_xa_cu','ma_huyen_cu','ma_xa','xa_phuong']}
        save(dest/'dia_chi_test.csv',rows)
        stream=io.StringIO()
        with contextlib.redirect_stdout(stream):
            engine.main(test_csv_arg=dest/'dia_chi_test.csv',bang_duyet_arg=dest/'bang_duyet_test.csv',
                        jsonl_arg=dest/'audit.jsonl',csv_arg=dest/'audit.csv',checkpoint_dir_arg=dest/'checkpoints',
                        phan_loai_csv_arg=dest/'classification.csv',phan_loai_md_arg=dest/'classification.md',
                        backup_csv_arg=ROOT/'data/test/backup_before_ai_review/dia_chi_test.csv',
                        sources_arg=ROOT/'data/test/goc/selected_sources.jsonl',labels_dir_arg=ROOT/'data/test/agy')
            try:
                report=validator.main(csv_file=str(dest/'dia_chi_test.csv'))
            except SystemExit:
                report=json.loads((ROOT/'data/test/validation.json').read_text(encoding='utf-8'))
        (dest/'execution.log').write_text(stream.getvalue(),encoding='utf-8',newline='\n')
        final=next(r for r in read(dest/'dia_chi_test.csv') if r['id']=='VNTEST0001')
        log=next(r for r in (json.loads(s) for s in (dest/'audit.jsonl').read_text(encoding='utf-8').splitlines()) if r['id']=='VNTEST0001')
        outputs.append({'fixture':mode,'input':final['dau_vao'],'inserted':inserted,
                        'output':{k:final[k] for k in inserted},'status':final['trang_thai_nhan'],'conclusion':log['ket_luan'],
                        'evidence':log['can_cu_input'],'catalogue_evidence':log['can_cu_danh_muc'],
                        'validator':report['status'],'validator_errors':report['errors']})
    nfd=unicodedata.normalize('NFD','12 Tây Thạnh')
    align=engine.align_output_components(nfd,{'duong':'Tay Thanh'})
    outputs.append({'fixture':'nfd_alignment_api','input':nfd,'alignment':align,
                    'normalized_matched':engine.remove_diacritics(align['duong']['matched']),
                    'expected_normalized':'tay thanh'})
    (WORK/'independent_negative_fixtures.json').write_text(json.dumps(outputs,ensure_ascii=False,indent=2),encoding='utf-8',newline='\n')
    print(json.dumps(outputs,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
