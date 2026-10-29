"""Dữ liệu ký tự từ snapshot: nhãn chi tiết có sẵn và căn chỉnh hành chính yếu.

Không tạo thêm câu. Không đọc data/test. Vị trí chưa căn chỉnh hành chính
được gán tập nhãn cho phép, không ép O làm nhãn âm giả.
"""

import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from src.char_cnn import TAGS, TAG_ID, ROLES, nfc_offsets
from src.crf_chi_tiet import tao_nhan
from src.danh_muc import DanhMuc
from src.quy_tac import cac_tien_to
from src.tach_phan_con import FIELDS
from src.tien_xu_ly import bo_dau, token_co_vi_tri
from .du_lieu_crf import doc_csv, doc_jsonl, family_csv, ghi_jsonl


def align_admin(text, ref, dm, occupied):
    """Chỉ căn chỉnh tên/mã tham chiếu với chữ có trong input, không gọi pipeline."""
    toks = token_co_vi_tri(text)
    prefixes = cac_tien_to([t.chu for t in toks])
    keys = lambda s: ''.join(c for c in bo_dau(s) if c.isalnum())
    units = set()
    for role, col in (('xa', 'ma_xa_cu'), ('huyen', 'ma_huyen_cu'), ('tinh', 'ma_tinh_cu'), ('xa', 'ma_xa'), ('tinh', 'ma_tinh')):
        if ref.get(col):
            era = 'cu' if col.endswith('_cu') else 'moi'
            if (era, ref[col]) in dm.don_vi and dm.lay(era, ref[col]).cap == role:
                units.add((era, ref[col]))
    proposals = set()
    for era, code in sorted(units):
        dv = dm.lay(era, code)
        name = dv.ten
        if name.casefold().startswith(dv.loai.casefold() + ' '):
            name = name[len(dv.loai):].strip()
        aliases = {keys(name)}
        if dv.cap == 'tinh':
            aliases.update({'Hà Nội': {'hn'}, 'Hồ Chí Minh': {'hcm', 'tphcm', 'sg', 'saigon'}}.get(name, set()))
        matches = set()
        for a in range(len(toks)):
            for b in range(a + 1, min(len(toks), a + 8) + 1):
                if not all(any(c.isalnum() for c in t.chu) or t.chu in ('-', '–') for t in toks[a:b]):
                    break
                if keys(''.join(t.chu for t in toks[a:b])) not in aliases:
                    continue
                start = a
                for p, (end, kind, spec) in prefixes.items():
                    if end == a and kind == 'hanh_chinh' and dv.cap in spec[0]:
                        start = p
                lo, hi = toks[start].bat_dau, toks[b - 1].ket_thuc
                if any(max(lo, x) < min(hi, y) for _, x, y in occupied):
                    continue
                matches.add((dv.cap, lo, hi))
        if len(matches) == 1:
            proposals.update(matches)
    # Không áp đặt khi hai cấp dùng chung một đoạn, hoặc hai cách căn chỉnh chồng.
    return [p for p in sorted(proposals) if not any(p != q and max(p[1], q[1]) < min(p[2], q[2]) for q in proposals)]


def char_record(text, details, ref, dm):
    normalized, offsets = nfc_offsets(text)
    starts = {a: i for i, (a, _) in enumerate(offsets)}
    ends = {b: i + 1 for i, (_, b) in enumerate(offsets)}
    admin = align_admin(text, ref, dm, details)
    spans = []
    for role, a, b in [*details, *admin]:
        if a not in starts or b not in ends or not 0 <= a < b <= len(text):
            raise ValueError('span_cat_cum_Unicode_hoac_sai_offset')
        spans.append((role, starts[a], ends[b]))
    # O và mọi nhãn admin được phép ở vùng chưa có nhãn chắc chắn.
    uncertain = [0] + [TAG_ID[p + r] for r in ('xa', 'huyen', 'tinh') for p in ('B-', 'I-')]
    allowed = [list(uncertain) if c.isalnum() else [0] for c in normalized]
    used = set()
    for role, a, b in spans:
        for i in range(a, b):
            if i in used:
                raise ValueError('nhan_char_chong_lan')
            used.add(i)
            allowed[i] = [TAG_ID[('B-' if i == a else 'I-') + role]]
    return {'id': ref['id'], 'text': text, 'nfc': normalized, 'spans': spans,
            'detail_spans_raw': details, 'allowed': allowed,
            'admin_alignment': 'weak_unique_name_alignment', 'ref': ref}


def validate_span_row(row):
    text = row['dau_vao']
    if not row.get('usable_for_span_training'):
        raise ValueError('span_khong_duoc_dung')
    spans, token_spans = [], []
    for role, span in row['spans'].items():
        if span is None:
            continue
        a, b = span['start'], span['end']
        if role not in FIELDS or text[a:b] != span['text'] or not 0 <= a < b <= len(text):
            raise ValueError('span_nguon_sai')
        spans.append((role, a, b))
        inds = [i for i, t in enumerate(row['tokens']) if a <= t['start'] < t['end'] <= b]
        if not inds or row['tokens'][inds[0]]['start'] != a or row['tokens'][inds[-1]]['end'] != b:
            raise ValueError('span_khong_khop_token_ban_giao')
        token_spans.append((role, inds[0], inds[-1] + 1))
    for t in row['tokens']:
        if text[t['start']:t['end']] != t['token']:
            raise ValueError('token_offset_nguon_sai')
    if tao_nhan(len(row['tokens']), token_spans) != [t['bio_tag'] for t in row['tokens']]:
        raise ValueError('BIO_nguon_khong_khop_span')
    return spans


def family_char(rec):
    text = rec['text']
    chars = list(text)
    for role, a, b in rec['detail_spans_raw']:
        if role == 'so_nha':
            chars[a:b] = [' '] * (b - a)
    return ''.join(c for c in bo_dau(''.join(chars)) if c.isalnum())


def prepare(snapshot, prepared_crf, output):
    snapshot, prepared_crf, output = map(Path, (snapshot, prepared_crf, output))
    output.mkdir(parents=True, exist_ok=False)
    dm = DanhMuc(snapshot / 'clean')
    refs = {split: doc_csv(snapshot / filename) for split, filename in
            [('train_goc', 'train.csv'), ('dev_goc', 'dev.csv'), ('train_bo_sung', 'train_bo_sung.csv'), ('dev_kho', 'dev_kho.csv')]}
    by_id = {s: {r['id']: r for r in rows} for s, rows in refs.items()}
    rows, rejected = defaultdict(list), []
    for split in refs:
        if split.endswith('goc'):
            # Dùng cùng lọc nhãn chi tiết như thí nghiệm CRF để so sánh được.
            source = doc_jsonl(prepared_crf / ('train_goc.jsonl' if split == 'train_goc' else 'dev_goc.jsonl'))
        else:
            source = doc_jsonl(snapshot / ('train_spans.jsonl' if split == 'train_bo_sung' else 'dev_spans.jsonl'))
        for row in source:
            ref = by_id[split][row['id']]
            try:
                if split.endswith('goc'):
                    records = token_co_vi_tri(row['text'])
                    details = [(r, records[a].bat_dau, records[b - 1].ket_thuc) for r, a, b in row['spans']]
                else:
                    if row['dau_vao'] != ref['dau_vao']:
                        raise ValueError('input_span_khac_csv')
                    details = validate_span_row(row)
                rec = char_record(ref['dau_vao'], details, ref, dm)
                rec['split'] = split
                rec['canonical_usable'] = row.get('usable_for_canonical_training', True)
                # Nhãn tên chuẩn bổ sung snapshot cũ có lỗi: không dùng làm nhãn ranker.
                for col, role in [('xa_phuong', 'xa'), ('tinh', 'tinh')]:
                    code = ref.get('ma_xa' if role == 'xa' else 'ma_tinh', '')
                    if code and ref.get(col) != dm.ten_day_du('moi', code):
                        rec['canonical_usable'] = False
                rows[split].append(rec)
            except (ValueError, KeyError) as e:
                rejected.append({'id': row['id'], 'split': split, 'reason': str(e)})
    held = {family_char(r) for s in ('dev_goc', 'dev_kho') for r in rows[s]}
    # Bao gồm cả dev bị loại khỏi phép đo span; không cho chúng lọt vào train.
    held.update(''.join(c for c in family_csv(r) if c.isalnum()) for s in ('dev_goc', 'dev_kho') for r in refs[s])
    train, seen = [], {}
    conflicts = set()
    for rec in rows['train_goc'] + rows['train_bo_sung']:
        if family_char(rec) in held:
            rejected.append({'id': rec['id'], 'reason': 'family_trung_dev'})
            continue
        key = rec['nfc'].casefold()
        labels = json.dumps(rec['allowed'])
        if key in seen:
            if seen[key][0] != labels:
                conflicts.add(key)
            rejected.append({'id': rec['id'], 'reason': 'trung_input_hoac_nhan_mau_thuan'})
            continue
        seen[key] = labels, rec
        train.append(rec)
    train = [r for r in train if r['nfc'].casefold() not in conflicts]
    # Union-find theo họ che số nhà VÀ mẫu cha. Ranker không học trên câu CNN đã train.
    parent = list(range(len(train)))
    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    keys = {}
    for i, r in enumerate(train):
        ancestry = re.search(r'(?:parent_id=|derived_train:)(VNTRAIN_\d+)', r['ref'].get('ghi_chu', '') + ';' + r['ref'].get('nguon', ''))
        group_keys = ['family:' + family_char(r)]
        if ancestry:
            group_keys.append('parent:' + ancestry[1])
        if r['split'] == 'train_goc':
            group_keys.append('parent:' + r['id'])
        for key in group_keys:
            if key in keys:
                parent[root(i)] = root(keys[key])
            else:
                keys[key] = i
    groups = defaultdict(list)
    for i, rec in enumerate(train):
        groups[root(i)].append(rec)
    cnn, rank = [], []
    for group in groups.values():
        group_key = min(r['id'] for r in group)
        is_rank = int(hashlib.sha256(('char_v1:' + group_key).encode()).hexdigest()[:8], 16) % 5 == 0
        for r in group:
            r['training_group'] = group_key
        (rank if is_rank else cnn).extend(group)
    assert not ({r['training_group'] for r in cnn} & {r['training_group'] for r in rank})
    sets = {'train_cnn': cnn, 'train_ranker': rank, 'dev_goc': rows['dev_goc'], 'dev_kho': rows['dev_kho']}
    for name, records in sets.items():
        ghi_jsonl(output / (name + '.jsonl'), records)
    ghi_jsonl(output / 'excluded.jsonl', rejected)
    summary = {'datasets': {name: {'rows': len(rs), 'characters': sum(len(r['nfc']) for r in rs),
                                  'spans': dict(Counter(s[0] for r in rs for s in r['spans']))} for name, rs in sets.items()},
               'new_samples_generated': 0, 'heldout_test_read': False,
               'cnn_ranker_group_overlap': 0, 'excluded': len(rejected),
               'label_quality': 'Chi tiết nhãn máy/tổng hợp; hành chính căn chỉnh yếu theo tên tham chiếu. Không phải gold.'}
    (output / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8', newline='\n')
    return summary
