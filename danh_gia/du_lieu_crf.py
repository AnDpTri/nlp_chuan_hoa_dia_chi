"""Chuẩn bị bản dữ liệu thử CRF từ snapshot; không sửa dữ liệu nguồn."""

import csv
import json
from collections import Counter

from .chay_ban_thu import DETAIL, align_detail, norm
from src.tien_xu_ly import token_co_vi_tri, bo_dau
from src.tien_xu_ly.quy_tac import cac_tien_to
from src.tien_xu_ly.crf_chi_tiet import tao_nhan


def doc_csv(path):
    with path.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def doc_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8-sig').splitlines() if line.strip()]


def ghi_jsonl(path, rows):
    path.write_text(''.join(json.dumps(r, ensure_ascii=False)+'\n' for r in rows), encoding='utf-8', newline='\n')


def tu_csv(row):
    records = token_co_vi_tri(row['dau_vao'])
    tokens = [t.chu for t in records]
    prefixes = cac_tien_to(tokens)
    spans = []
    for field in DETAIL:
        if not row[field]:
            continue
        positions = align_detail(row['dau_vao'], field, row[field])
        if len(positions) != 1:
            raise ValueError('nhan_khong_co_mot_vi_tri:'+field)
        a, b = positions[0]
        if any(end == a and kind == 'hanh_chinh' for end, kind, _ in prefixes.values()):
            raise ValueError('noi_dung_sau_tien_to_hanh_chinh:'+field)
        for start, (end, kind, attrs) in prefixes.items():
            if end == a and kind == 'chi_tiet' and attrs[0] == field:
                a = start
                break
        spans.append((field, a, b))
    tags = tao_nhan(len(tokens), spans)
    for start, (_, kind, attrs) in prefixes.items():
        if kind == 'chi_tiet' and not any(a <= start < b for _, a, b in spans):
            raise ValueError('tien_to_chi_tiet_chua_co_nhan:'+attrs[0])
    return {'id': row['id'], 'text': row['dau_vao'], 'tokens': tokens, 'tags': tags,
            'spans': spans, 'origin': 'csv_can_chinh_yeu'}


def tu_span(row, ref):
    if row['dau_vao'] != ref['dau_vao']:
        raise ValueError('input_span_khac_csv')
    if not row.get('usable_for_span_training'):
        raise ValueError('khong_duoc_dung_span')
    text = row['dau_vao']
    # Kiểm tra bản nhãn đã bàn giao trước khi chiếu sang tokenizer runtime.
    old_tags, old_spans = [], []
    for t in row['tokens']:
        if text[t['start']:t['end']] != t['token']:
            raise ValueError('token_offset_ban_giao_sai')
        old_tags.append(t['bio_tag'])
    from src.tien_xu_ly.crf_chi_tiet import bio_spans
    if bio_spans(old_tags)[1]:
        raise ValueError('bio_ban_giao_sai')
    records = token_co_vi_tri(text)
    spans = []
    for field, s in row['spans'].items():
        if s is None:
            continue
        if text[s['start']:s['end']] != s['text'] or s['start'] >= s['end']:
            raise ValueError('char_span_ban_giao_sai')
        inds = [i for i, t in enumerate(records) if max(t.bat_dau, s['start']) < min(t.ket_thuc, s['end'])]
        if not inds or records[inds[0]].bat_dau != s['start'] or records[inds[-1]].ket_thuc != s['end']:
            raise ValueError('span_cat_giua_token_runtime')
        spans.append((field, inds[0], inds[-1]+1))
        old_inds = [i for i, t in enumerate(row['tokens']) if s['start'] <= t['start'] < t['end'] <= s['end']]
        if not old_inds:
            raise ValueError('span_khong_co_token_ban_giao')
        old_spans.append((field, old_inds[0], old_inds[-1]+1))
    if tao_nhan(len(old_tags), old_spans) != old_tags:
        raise ValueError('bio_khong_khop_char_span')
    tokens = [t.chu for t in records]
    return {'id': row['id'], 'text': text, 'tokens': tokens, 'tags': tao_nhan(len(tokens), spans),
            'spans': spans, 'origin': 'span_tong_hop_da_kiem_tra_co_hoc',
            'usable_for_canonical_training': row.get('usable_for_canonical_training', False)}


def family(record):
    removed = {i for f, a, b in record['spans'] if f == 'so_nha' for i in range(a, b)}
    return ' '.join(bo_dau(t) for i, t in enumerate(record['tokens']) if i not in removed and any(c.isalnum() for c in t))


def family_csv(row):
    tokens = [t.chu for t in token_co_vi_tri(row['dau_vao'])]
    positions = align_detail(row['dau_vao'], 'so_nha', row['so_nha']) if row['so_nha'] else []
    spans = []
    if len(positions) == 1:
        a, b = positions[0]
        for start, (end, kind, attrs) in cac_tien_to(tokens).items():
            if end == a and kind == 'chi_tiet' and attrs[0] == 'so_nha':
                a = start
        spans = [('so_nha', a, b)]
    return family({'tokens': tokens, 'spans': spans})


def prepare(snapshot, output):
    output.mkdir(parents=True, exist_ok=False)
    refs = {name: doc_csv(snapshot/file) for name, file in (
        ('train_goc', 'train.csv'), ('dev_goc', 'dev.csv'),
        ('train_bo_sung', 'train_bo_sung.csv'), ('dev_kho', 'dev_kho.csv'))}
    prepared, rejected, summaries = {}, [], {}
    for split, rows in refs.items():
        by_id = {r['id']: r for r in rows}
        if len(by_id) != len(rows):
            raise ValueError('Trùng ID '+split)
        raw = doc_jsonl(snapshot/('train_spans.jsonl' if split == 'train_bo_sung' else 'dev_spans.jsonl')) if split in {'train_bo_sung', 'dev_kho'} else rows
        if split in {'train_bo_sung', 'dev_kho'} and {r['id'] for r in raw} != set(by_id):
            raise ValueError('ID span/CSV không đồng bộ')
        result, reasons = [], Counter()
        for row in raw:
            try:
                rec = tu_span(row, by_id[row['id']]) if split in {'train_bo_sung', 'dev_kho'} else tu_csv(row)
                rec['source_split'] = split
                result.append(rec)
            except ValueError as e:
                reasons[str(e)] += 1
                rejected.append({'id': row['id'], 'split': split, 'reason': str(e), 'input': row['dau_vao']})
        prepared[split] = result
        summaries[split] = {'input_rows': len(rows), 'mechanically_accepted': len(result), 'reasons': dict(reasons)}
    heldout = {family_csv(r) for key in ('dev_goc', 'dev_kho') for r in refs[key]}
    heldout.update(family(r) for key in ('dev_goc', 'dev_kho') for r in prepared[key])
    for split in ('train_goc', 'train_bo_sung'):
        kept = []
        for rec in prepared[split]:
            if family(rec) in heldout:
                rejected.append({'id': rec['id'], 'split': split, 'reason': 'ho_input_trung_dev_sau_che_so_nha', 'input': rec['text']})
            else:
                kept.append(rec)
        summaries[split]['excluded_heldout_family'] = len(prepared[split])-len(kept)
        prepared[split] = kept
    # Dedup cùng input/BIO; nếu cùng input khác nhãn, không lấy một nhãn tùy ý.
    def dedup(records):
        groups = {}
        for rec in records:
            groups.setdefault(norm(rec['text']), []).append(rec)
        kept = []
        for group in groups.values():
            labels = {tuple(r['tags']) for r in group}
            if len(labels) == 1:
                kept.append(group[0])
                rejected.extend({'id': r['id'], 'split': r['source_split'], 'reason': 'trung_input_va_bio', 'input': r['text']} for r in group[1:])
            else:
                rejected.extend({'id': r['id'], 'split': r['source_split'], 'reason': 'cung_input_khac_bio', 'input': r['text']} for r in group)
        return kept
    original = dedup(prepared['train_goc'])
    combined = dedup(prepared['train_goc']+prepared['train_bo_sung'])
    sets = {'train_goc': original, 'train_ket_hop': combined,
            'dev_goc': prepared['dev_goc'], 'dev_kho': prepared['dev_kho']}
    for key, records in sets.items():
        ghi_jsonl(output/(key+'.jsonl'), records)
        summaries[key] = {**summaries.get(key, {}), 'used_rows': len(records),
                          'tokens': sum(len(r['tokens']) for r in records),
                          'tags': dict(Counter(t for r in records for t in r['tags'])),
                          'spans': dict(Counter(f for r in records for f, _, _ in r['spans']))}
    ghi_jsonl(output/'excluded.jsonl', rejected)
    summary = {'datasets': summaries, 'training_exclusions': dict(Counter(r['reason'] for r in rejected if r['split'].startswith('train'))),
               'heldout_family_overlap_after_filter': len({family(r) for r in combined} & heldout),
               'label_quality': 'Nhãn máy/tổng hợp; các phép lọc cơ học không xác nhận ngữ nghĩa vàng.',
               'original_csv_alignment': 'Chỉ giữ vị trí duy nhất, không chồng, không có tiền tố chi tiết thiếu nhãn; không lấy output luật làm nhãn.',
               'new_training_samples_generated': 0}
    (output/'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8', newline='\n')
    return summary
