"""Hậu kiểm điểm và gợi ý; không coi gợi ý chứa reference là output đúng."""
import json
import shutil
from collections import Counter
from pathlib import Path
from .chay_ban_thu import ROOT, CORE, norm, digest
from .du_lieu_crf import doc_jsonl


def same(p,r,fields=CORE):
    return all(norm(p[f])==norm(r[f]) for f in fields)


def run():
    out=ROOT/'danh_gia/ket_qua/do_hop_dong_v1_01'
    baseline=ROOT/'danh_gia/ket_qua/sua_dinh_dang_v1_01'
    report=json.loads((out/'thong_ke.json').read_text(encoding='utf-8'))
    extra={}
    for split,models in report['datasets'].items():
        extra[split]={}
        for model in models:
            before=doc_jsonl(baseline/f'{model}_{split}.jsonl')
            after=doc_jsonl(out/f'{model}_{split}.jsonl')
            counts=Counter()
            examples={}
            for old,new in zip(before,after):
                assert old['id']==new['id'] and old['reference']==new['reference']
                p,r=new['prediction'],new['reference']
                candidates=p['thong_ke']['hop_dong']['truong']['duong']['ung_vien_ten']
                compatible=[x for x in candidates if x['tuong_thich_dau']]
                covered=any(norm(x['gia_tri'])==norm(r['duong']) for x in compatible)
                counts['rows_with_name_suggestions']+=bool(candidates)
                counts['suggestions_contain_reference_road']+=covered and bool(r['duong'])
                counts['reference_road_nonempty']+=bool(r['duong'])
                counts['name_suggestions_ambiguous']+=len(compatible)>1
                counts['name_suggestions_accent_conflict']+=any(not x['tuong_thich_dau'] for x in candidates)
                if not same(p,r):
                    counts['wrong_six_fields']+=1
                    counts['wrong_but_only_road_and_suggestion_matches']+=same(p,r,CORE[:3]+CORE[4:]) and covered
                if same(old['prediction'],r) and not same(p,r):
                    changed={f for f in CORE if norm(old['prediction'][f])!=norm(p[f])}
                    kind='only_road_with_correct_suggestion' if changed=={'duong'} and covered else 'changed_admin_or_other_detail'
                    counts['lost_'+kind]+=1
                    examples.setdefault(kind,[])
                    if len(examples[kind])<2:examples[kind].append({'id':new['id'],'input':new['input'],'reference':r,
                        'before':{f:old['prediction'][f] for f in CORE},'after':{f:p[f] for f in CORE},'suggestions':candidates})
            extra[split][model]={'counts':dict(counts),'examples':examples}
    (out/'PHAN_TICH_GOI_Y.json').write_text(json.dumps(extra,ensure_ascii=False,indent=2),encoding='utf-8')
    lines=['# Đo chế độ hợp đồng v1','','Giữ nguyên checkpoint/dữ liệu/từ điển. Không train, không đọc test cuối. So với bản đã sửa định dạng tiền tố.',
           'Đây là khớp nhãn máy/tổng hợp trên dev cũ, chưa là kiểm chứng tổng quát hóa. Gợi ý chứa tên reference không được tính thành câu output đúng.','',
           '| Tập | Model | Đúng trước → sau | % sau | Được / mất | Mean/P95 ms |','|---|---|---:|---:|---:|---:|']
    for split,models in report['datasets'].items():
        for model,m in models.items():
            b=doc_jsonl(baseline/f'{model}_{split}.jsonl')
            n=sum(same(x['prediction'],x['reference']) for x in b)
            lines.append(f"| {split} | {model} | {n} → {m['dung_toan_bo_6_truong']} / {len(b)} | {m['khop_toan_bo_6_truong_pct']:.3f} | {m['delta']['gained']}/{m['delta']['lost']} | {m['latency']['mean_ms']:.2f}/{m['latency']['p95_ms']:.2f} |")
    lines+=['','## Phân tích phần giảm điểm','']
    for split,models in extra.items():
        for model,m in models.items():lines.append(f"- {split}, {model}: {json.dumps(m['counts'],ensure_ascii=False)}")
    lines+=['','Chế độ mới giữ tên từ train ở gợi ý và bỏ lọc cứng theo span model. Đây là thay đổi chính sách đầu ra, không phải bằng chứng chất lượng tốt hơn.',
            'Điểm giảm phải được báo đầy đủ; không chọn mặc định mới chỉ vì output giải thích rõ hơn. Các quyết định hành chính thay đổi cần rà từng ca.',
            'Latency gồm core + tạo cấu trúc giải thích + asdict, không gồm JSON/I/O/khởi tạo; một lượt CPU một luồng, tải nền có thể ảnh hưởng.',
            'Output từng câu ở JSONL; thay_doi_tung_cau.jsonl chứa mọi câu đổi; PHAN_TICH_GOI_Y.json chứa phân loại phần giảm và ví dụ.', '']
    (out/'BAO_CAO.md').write_text('\n'.join(lines),encoding='utf-8')
    files=[*list((ROOT/'src').glob('*.py')),Path(__file__),ROOT/'danh_gia/do_sua_dinh_dang.py']
    manifest={}
    for p in files:
        q=out/'source'/p.relative_to(ROOT);q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q)
        manifest[p.relative_to(ROOT).as_posix()]=digest(p)
    (out/'code_sha256.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(json.dumps(extra,ensure_ascii=False,indent=2))


if __name__=='__main__':run()
