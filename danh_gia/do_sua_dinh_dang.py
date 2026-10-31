"""Đo sửa formatter trên hai cấu hình giữ nguyên checkpoint, không train."""
import json
import argparse
import time
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from src.tien_xu_ly.char_cnn import BoTachCharCNN
from src.tien_xu_ly.videberta import BoTachViDeberta
from src.chuan_hoa import BoChuanHoa
from src.tien_xu_ly.chuan_ten_duong import TuDienDuong
from src.danh_muc import DanhMuc
from src.tien_xu_ly.xep_hang import BoXepHang
from .chay_ban_thu import ROOT, CORE, aggregate, norm, digest
from .do_char import latency
from .du_lieu_crf import doc_jsonl, doc_csv, ghi_jsonl


def same(p, r):
    return all(norm(p[f]) == norm(r[f]) for f in CORE)


def run(output=None, hop_dong=False, baseline=None):
    out = output or ROOT / 'danh_gia/ket_qua/sua_dinh_dang_v1_01'
    out.mkdir(parents=True, exist_ok=True)
    if any(out.iterdir()):
        raise FileExistsError('Không ghi đè kết quả đã có')
    old = baseline or ROOT / 'danh_gia/ket_qua/ma_tran_v1_01'
    cnn = ROOT / 'mo_hinh/thu_nghiem/char_v1_01'
    vi = ROOT / 'mo_hinh/thu_nghiem/videberta_v1_01'
    dm = DanhMuc(cnn / 'snapshot/clean')
    names_path = ROOT / 'danh_gia/ket_qua/sua_pipeline_cnn_v1_01/tu_dien_duong_train.json'
    names = TuDienDuong(names_path)
    paths = [cnn/'char_cnn.pt',cnn/'ranker.txt',vi/'model/model.safetensors',vi/'ranker.txt',names_path,
             cnn/'snapshot/dev.csv',cnn/'snapshot/dev_kho.csv']
    hashes = {str(p.relative_to(ROOT)):digest(p) for p in paths}
    report = {'no_training':True,'labels_changed':False,'heldout_test_read':False,'hop_dong':hop_dong,
              'baseline':str(old),'hashes':hashes,'datasets':{}}
    changes = []
    for key, backend in [('cnn_ranker',BoTachCharCNN(cnn/'char_cnn.pt')),('videberta_tay',BoTachViDeberta(vi/'model'))]:
        ranker = BoXepHang(cnn/'ranker.txt',backend.ma_bam,dm.ma_bam) if key=='cnn_ranker' else None
        model = BoChuanHoa(danh_muc=dm,bo_tach=backend,bo_xep_hang=ranker,tu_dien_duong=names,bao_ve_duong=True,hop_dong=hop_dong)
        for rec in doc_jsonl(cnn/'data/train_cnn.jsonl')[:3]: model.chuan_hoa(rec['text'])
        for split in ('dev_goc','dev_kho'):
            refs = {r['id']: r for r in doc_csv(cnn/'snapshot'/('dev.csv' if split=='dev_goc' else 'dev_kho.csv'))}
            source = old/f'{key}_{split}.jsonl'
            rows=doc_jsonl(source if source.exists() else old/f'{key}_sua_{split}.jsonl')
            outputs=[]; times=[]; delta=Counter()
            for i,row in enumerate(rows):
                start=time.perf_counter(); result=model.chuan_hoa(row['input']); times.append(1000*(time.perf_counter()-start))
                pred=asdict(result); ref=row['reference']; prev=row['prediction']
                ok0,ok1=same(prev,ref),same(pred,ref)
                delta['gained']+=not ok0 and ok1; delta['lost']+=ok0 and not ok1
                occupied=set()
                for s in pred['dau_vet']:
                    a,b=s['ky_tu_bat_dau'],s['ky_tu_ket_thuc']
                    assert s['doan_goc']==row['input'][a:b] and not occupied.intersection(range(a,b))
                    occupied.update(range(a,b))
                outputs.append({**row,'prediction':pred,'latency_ms':times[-1]})
                if any(norm(prev[f])!=norm(pred[f]) for f in CORE):
                    changes.append({'model':key,'split':split,'id':row['id'],'input':row['input'],'reference':ref,
                                    'before':{f:prev[f] for f in CORE},'after':{f:pred[f] for f in CORE},
                                    'before_correct':ok0,'after_correct':ok1})
                if (i+1)%400==0:print(key,split,i+1,flush=True)
            stats=aggregate([(refs[r['id']],r['prediction']) for r in outputs])
            stats.update(delta=dict(delta),latency=latency(times))
            report['datasets'].setdefault(split,{})[key]=stats
            ghi_jsonl(out/f'{key}_{split}.jsonl',outputs)
            print(json.dumps({'model':key,'split':split,'correct':stats['dung_toan_bo_6_truong'],'delta':dict(delta)},ensure_ascii=False),flush=True)
            (out/'thong_ke.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    assert all(digest(ROOT/p)==h for p,h in hashes.items())
    report['frozen_unchanged_after']=True
    (out/'thong_ke.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    ghi_jsonl(out/'thay_doi_tung_cau.jsonl',changes)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path)
    parser.add_argument('--baseline',type=Path)
    parser.add_argument('--hop-dong',action='store_true')
    args=parser.parse_args()
    if args.hop_dong and args.output is None:
        parser.error('--hop-dong cần --output riêng')
    run(args.output.resolve() if args.output else None,args.hop_dong,
        args.baseline.resolve() if args.baseline else None)
