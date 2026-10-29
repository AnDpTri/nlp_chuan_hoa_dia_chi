"""Chẩn đoán bản v2 cố định trên dev; không sửa lõi, nhãn hoặc đọc test.

Oracle trong báo cáo chỉ là khả năng khớp NHÃN THAM CHIẾU trong các nhánh
đã xét. Nó không xác nhận nhãn đúng hoặc thông tin đầu vào đủ về ngữ nghĩa.
"""

import argparse
import csv
import io
import json
from collections import Counter, defaultdict
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from danh_gia.chay_ban_thu import ROOT, CORE, DETAIL, norm, pct, digest, align_detail, write_csv
from src.chuan_hoa import BoChuanHoa
from src.chuyen_doi import tap_dich, sang_cay_moi
from src.giai_ma import tim_duong_di
from src.kieu_du_lieu import DuongDi
from src.quy_tac import cac_tien_to
from src.tach_phan_con import tach_co_dau_vet
from src.tien_xu_ly import token_co_vi_tri, bo_dau
from src.tim_kiem import sinh_ung_vien


def same_core(a, b):
    return all(norm(a[f]) == norm(b[f]) for f in CORE)


def admin_match(wards, provinces, row):
    """Khớp mã đầu ra một nhánh, kể cả để trống khi tập đích chưa duy nhất."""
    w = next(iter(wards)) if len(wards) == 1 else ""
    p = next(iter(provinces)) if len(provinces) == 1 else ""
    return w == row['ma_xa'] and p == row['ma_tinh']


def supports(wards, provinces, ward, province):
    return ward in wards and (not province or province in provinces)


def retained_paths(model, text, beam, tokens=None, candidates=None):
    """Tái hiện điểm xếp hạng v2, không thay tham số của pipeline thật."""
    if tokens is None:
        tokens = [t.chu for t in token_co_vi_tri(text)]
    if candidates is None:
        candidates = sinh_ung_vien(tokens, model.trie)
    admin_spans = {(u.bat_dau, u.ket_thuc) for u in candidates
                   if u.co_tien_to and u.kieu_khop != 'sai_chinh_ta'}
    prefixes = {i: p for i, p in cac_tien_to(tokens).items()
                if not any(a < i < b for a, b in admin_spans)}
    ranked = []
    for path in tim_duong_di(candidates, len(tokens), model.danh_muc, beam):
        occupied = {i for u in path.ung_vien for i in range(u.bat_dau, u.ket_thuc)}
        detail, spans, unknown, inferred = tach_co_dau_vet(tokens, occupied, prefixes)
        score = path.diem - .12*len(unknown) + .05*sum(s['ket_thuc']-s['bat_dau'] for s in spans)
        w, p = tap_dich(path, model.danh_muc)
        ma_xa, ma_tinh, _ = sang_cay_moi(path, detail, model.danh_muc)
        ranked.append({'score': score, 'path': path, 'wards': w, 'provinces': p,
                       'core': {**{f: detail[f] for f in DETAIL}, 'ma_xa': ma_xa, 'ma_tinh': ma_tinh},
                       'unknown': unknown})
    ranked.sort(key=lambda x: -x['score'])
    return tokens, candidates, ranked


def compatible(a, b, dm):
    return (max(a.bat_dau, b.bat_dau) >= min(a.ket_thuc, b.ket_thuc)
            and not (a.cap == b.cap and a.cay == b.cay)
            and dm.tuong_thich(dm.lay(a.cay, a.ma), dm.lay(b.cay, b.ma)))


def find_unique_witness(candidates, dm, ward, province, max_nodes=100000):
    """Tìm tập ứng viên hợp lệ chốt duy nhất đích, độc lập điểm/cắt beam.

    Chỉ loại ứng viên không thể thuộc một chứng cứ cho đích đang xét:
    giao các tập đích không thể đưa trở lại phần tử đã thiếu. Duyệt tất cả
    tập con còn lại nếu chưa tìm thấy chứng cứ; có giới hạn và báo riêng.
    Không chứng minh cách hiểu đó đúng về ngữ nghĩa hoặc bao phủ hết input.
    """
    eligible = []
    for u in candidates:
        w, p = tap_dich(DuongDi(u.cay, [u], 0), dm)
        is_provider = u.cap == 'xa' or (u.cay == 'cu' and u.ma in dm.huyen_thanh_dac_khu)
        if province not in p or (is_provider and ward not in w):
            continue
        eligible.append(u)
    # Xét ứng viên có xã trước chỉ thay thứ tự duyệt, không loại tập con.
    eligible.sort(key=lambda u: (u.cap != 'xa', u.bat_dau, u.cay, u.ma))
    nodes = 0
    limited = False

    def search(start, selected):
        nonlocal nodes, limited
        nodes += 1
        if nodes > max_nodes:
            limited = True
            return None
        if selected:
            w, p = tap_dich(DuongDi('', selected, 0), dm)
            if w == {ward} and p == {province}:
                return selected
        for j in range(start, len(eligible)):
            u = eligible[j]
            if all(compatible(u, v, dm) for v in selected):
                result = search(j+1, selected+[u])
                if result is not None or limited:
                    return result
        return None

    witness = search(0, [])
    return {'status': 'found' if witness is not None else 'limit' if limited else 'absent',
            'nodes': nodes, 'witness': witness or []}


def field_decision_counts(pairs, field):
    counts = Counter()
    for row, pred in pairs:
        r, p = row[field], pred[field]
        key = ('dien_khop' if norm(r) == norm(p) else 'dien_lech_nhan') if p else (
            'de_trong_khi_nhan_co' if r else 'cung_trong')
        counts[key] += 1
    filled = counts['dien_khop'] + counts['dien_lech_nhan']
    return {**{k: counts[k] for k in ('dien_khop', 'dien_lech_nhan', 'de_trong_khi_nhan_co', 'cung_trong')},
            'so_dien': filled, 'ty_le_dien_pct': pct(filled, len(pairs)),
            'ty_le_lech_trong_so_dien_pct': pct(counts['dien_lech_nhan'], filled)}


def reference_flags(row, dm):
    """Cờ cần rà nhãn; tuyệt đối không tự sửa hoặc coi mọi cờ là nhãn sai."""
    flags = []
    for field, name_field in (('ma_xa', 'xa_phuong'), ('ma_tinh', 'tinh')):
        if row[field]:
            if ('moi', row[field]) not in dm.don_vi:
                flags.append('ma_dich_khong_trong_danh_muc:'+field)
            elif norm(row[name_field]) != norm(dm.ten_day_du('moi', row[field])):
                flags.append('ten_dich_khac_ma:'+name_field)
    cu = dm.don_vi.get(('cu', row.get('ma_xa_cu', '')))
    if cu:
        if row.get('ma_huyen_cu') and cu.ma_cha != row['ma_huyen_cu']:
            flags.append('xa_cu_khac_huyen_nhan')
        actual_province = dm.lay('cu', cu.ma_cha).ma_cha
        if row.get('ma_tinh_cu') and actual_province != row['ma_tinh_cu']:
            flags.append('xa_cu_khac_tinh_nhan')
        if row['ma_xa'] and row['ma_xa'] not in dm.dich_xa('cu', cu.ma):
            flags.append('xa_dich_ngoai_doi_chieu_xa_cu')
        if len(dm.dich_xa('cu', cu.ma)) > 1 and row['ma_xa']:
            flags.append('xa_cu_nhieu_dich_nhung_nhan_chot_xa')
    occupied = set()
    for field in DETAIL:
        if not row[field]:
            continue
        spans = align_detail(row['dau_vao'], field, row[field])
        if not spans:
            flags.append('noi_dung_nhan_khong_can_chinh:'+field)
        elif len(spans) > 1:
            flags.append('noi_dung_nhan_nhieu_vi_tri:'+field)
        else:
            inds = set(range(*spans[0]))
            if occupied & inds:
                flags.append('noi_dung_nhan_chong_lan:'+field)
            occupied.update(inds)
    return flags


def compact_path(item, tokens, dm):
    return {'score': round(item['score'], 4), 'output_6_truong': item['core'],
            'xa_co_the': sorted(item['wards']), 'tinh_co_the': sorted(item['provinces']),
            'hanh_chinh': [{'doan': ' '.join(tokens[u.bat_dau:u.ket_thuc]),
                           'moc': u.cay, 'ma': u.ma, 'cap': u.cap,
                           'ten': dm.ten_day_du(u.cay, u.ma), 'kieu_khop': u.kieu_khop}
                          for u in item['path'].ung_vien]}


def analyse(row, pred, model, wide_beam):
    tokens, candidates, paths = retained_paths(model, row['dau_vao'], model.beam)
    top = paths[0]
    # Bắt drift khi tái hiện điểm: phải cùng nhánh tốt nhất và điểm với lõi.
    selected = sorted((u.bat_dau, u.ket_thuc, u.cay, u.ma) for u in top['path'].ung_vien)
    actual = sorted((u['token_bat_dau'], u['token_ket_thuc'], u['moc'], u['ma'])
                    for u in pred['dau_vet'] if u['truong'] in {'xa', 'huyen', 'tinh'})
    if selected != actual or abs(top['score']-pred['thong_ke']['diem']) > .00006:
        raise RuntimeError('Tái hiện nhánh không khớp lõi: '+row['id'])
    detail_same = all(norm(top['core'][f]) == norm(pred[f]) for f in DETAIL)
    if not detail_same:
        raise RuntimeError('Tái hiện chi tiết không khớp lõi: '+row['id'])
    exact = same_core(row, pred)
    matching = [p for p in paths if same_core(row, p['core'])]
    admins = [p for p in paths if admin_match(p['wards'], p['provinces'], row)]
    wide = None
    if not exact and not matching:
        _, _, wide = retained_paths(model, row['dau_vao'], wide_beam, tokens, candidates)
    wide_matching = [p for p in wide or [] if same_core(row, p['core'])]
    wrong_fields = [f for f in CORE if norm(row[f]) != norm(pred[f])]
    flags = reference_flags(row, model.danh_muc)
    d = {'id': row['id'], 'dau_vao': row['dau_vao'], 'nguon': row.get('nguon', ''),
         'nguon_du_lieu': row.get('nguon_du_lieu', ''), 'loai_nhan': row['loai_nhan'],
         'tham_chieu': {f: row[f] for f in (*CORE, 'dia_chi_chuan')},
         'du_doan': {f: pred[f] for f in (*CORE, 'dia_chi_chuan')},
         'canh_bao': pred['canh_bao'], 'truong_lech': wrong_fields,
         'khop_6': exact, 'co_nhanh_khop_6_beam40': bool(matching),
         'co_nhanh_khop_hanh_chinh_beam40': bool(admins),
         'co_nhanh_khop_6_beam_rong': bool(wide_matching) if wide is not None else None,
         'co_can_ra_nhan': flags,
         'chi_tiet': {f: {'khop_output': norm(row[f]) == norm(pred[f]),
                         'co_nhanh_khop_truong': any(norm(p['core'][f]) == norm(row[f]) for p in paths),
                         'chi_khac_dau': norm(row[f]) != norm(pred[f]) and bo_dau(norm(row[f])) == bo_dau(norm(pred[f]))}
                     for f in DETAIL},
         'nhanh_duoc_xep_dau': compact_path(top, tokens, model.danh_muc)}
    if matching:
        d['nhanh_khop_tham_chieu'] = compact_path(matching[0], tokens, model.danh_muc)
    elif wide_matching:
        d['nhanh_khop_tham_chieu_beam_rong'] = compact_path(wide_matching[0], tokens, model.danh_muc)
    if row['ma_xa']:
        possible = set().union(*(model.danh_muc.dich_xa(u.cay, u.ma) for u in candidates))
        in_candidates = row['ma_xa'] in possible
        support = any(supports(p['wards'], p['provinces'], row['ma_xa'], row['ma_tinh']) for p in paths)
        unique = bool(admins)  # nhãn xã có giá trị nên admin_match yêu cầu duy nhất.
        witness = None
        if not unique and in_candidates:
            witness = find_unique_witness(candidates, model.danh_muc, row['ma_xa'], row['ma_tinh'])
        if pred['ma_xa'] == row['ma_xa'] and pred['ma_tinh'] == row['ma_tinh']:
            stage = 'khop_ma_xa_va_tinh'
        elif not in_candidates:
            stage = 'khong_sinh_dich_tham_chieu'
        elif not unique:
            stage = ('co_nhanh_duy_nhat_nhung_bi_cat_beam' if witness['status'] == 'found' else
                     'chua_ket_luan_vi_gioi_han_duyet' if witness['status'] == 'limit' else
                     'khong_co_nhanh_chot_duy_nhat_tu_ung_vien')
        elif admin_match(top['wards'], top['provinces'], row):
            stage = 'giu_mo_ho_o_buoc_quyet_dinh'
        else:
            stage = 'co_nhanh_dung_ma_nhung_xep_sau'
        d['hanh_chinh'] = {'dich_trong_ung_vien': in_candidates, 'beam40_con_nhanh_chua_dich': support,
                          'beam40_co_nhanh_chot_duy_nhat': unique, 'nhom': stage}
        if witness:
            d['hanh_chinh']['duyet_tap_con'] = {'status': witness['status'], 'nodes': witness['nodes'],
                                               'witness': [asdict(u) for u in witness['witness']]}
    else:
        d['hanh_chinh'] = {'nhom': 'nhan_xa_trong_du_doan_co' if pred['ma_xa'] else 'nhan_va_du_doan_cung_trong_xa'}
    # Nhóm cơ chế lệch nhãn, không phải kết luận lỗi ngữ nghĩa đã xác minh.
    if exact:
        mechanism = 'khop_6_truong'
    elif same_core(row, top['core']):
        mechanism = 'quyet_dinh_giu_mo_ho_lam_lech_nhan'
    elif matching:
        mechanism = 'co_nhanh_khop_6_nhung_xep_sau'
    elif wide_matching:
        mechanism = 'beam40_mat_nhanh_khop_6_beam_rong_giu_duoc'
    elif admins and any(f in DETAIL for f in wrong_fields):
        mechanism = 'co_nhanh_dung_ma_nhung_chi_tiet_chua_khop_nhan'
    else:
        mechanism = 'chua_tach_duoc_hanh_chinh_chi_tiet_va_nhan'
    d['nhom_co_che'] = mechanism
    return d


def run(input_path, output_dir, baseline_dir, wide_beam=160):
    input_path = Path(input_path).resolve()
    baseline_dir = Path(baseline_dir).resolve()
    output_dir = Path(output_dir).resolve()
    if input_path.is_relative_to(ROOT / 'data' / 'test'):
        raise ValueError('Không đọc tập test cuối')
    raw = input_path.read_bytes()
    rows = list(csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))))
    if not rows or len({r['id'] for r in rows}) != len(rows):
        raise ValueError('Dev rỗng hoặc trùng ID')
    baseline = json.loads((baseline_dir / 'thong_ke.json').read_text(encoding='utf-8-sig'))
    manifest = json.loads((baseline_dir / 'code_sha256.json').read_text(encoding='utf-8-sig'))
    if baseline['input_sha256'] != digest(input_path):
        raise ValueError('Input khác lần đo v2')
    changed = [name for name, value in manifest.items() if digest(ROOT / name) != value]
    if changed:
        raise ValueError('Source khác lần đo v2: '+str(changed))
    predictions = [json.loads(line) for line in (baseline_dir / 'du_doan.jsonl').read_text(encoding='utf-8-sig').splitlines()]
    by_id = {r['id']: r for r in predictions}
    if len(by_id) != len(predictions) or set(by_id) != {r['id'] for r in rows}:
        raise ValueError('ID baseline khác input')
    model = BoChuanHoa(beam=baseline['beam'])
    if wide_beam <= model.beam:
        raise ValueError('Beam đối chứng phải lớn hơn beam gốc')
    if model.danh_muc.ma_bam != baseline['catalogue_sha256']:
        raise ValueError('Danh mục khác lần đo v2')
    output_dir.mkdir(parents=True, exist_ok=False)
    diagnostics = []
    pairs = []
    with (output_dir / 'chan_doan_tung_mau.jsonl').open('w', encoding='utf-8', newline='\n') as f:
        for i, row in enumerate(rows, 1):
            # Kiểm tra lại bằng API thật, không chỉ dựa bản mô phỏng chẩn đoán.
            pred = asdict(model.chuan_hoa(row['dau_vao']))
            old = by_id[row['id']]
            if pred != {k: v for k, v in old.items() if k not in {'id', 'dau_vao', 'thoi_gian_ms'}}:
                raise RuntimeError('Kết quả API khác baseline: '+row['id'])
            d = analyse(row, pred, model, wide_beam)
            diagnostics.append(d)
            pairs.append((row, pred))
            f.write(json.dumps(d, ensure_ascii=False)+'\n')
            if i % 200 == 0:
                print(f'Đã chẩn đoán {i}/{len(rows)}', flush=True)
    groups = defaultdict(list)
    for d in diagnostics:
        groups['tat_ca'].append(d)
        groups['nguon:'+d['nguon_du_lieu']].append(d)
        groups['co_co_ra_nhan' if d['co_can_ra_nhan'] else 'khong_co_co_ra_nhan'].append(d)
    selections = {}
    for name, selected_pairs in (
        ('tat_ca', pairs),
        ('khong_co_bat_ky_canh_bao_nao', [(r, p) for r, p in pairs if not p['canh_bao']]),
        ('co_it_nhat_mot_canh_bao', [(r, p) for r, p in pairs if p['canh_bao']])):
        correct = sum(same_core(r, p) for r, p in selected_pairs)
        selections[name] = {'so_mau': len(selected_pairs), 'bao_phu_pct': pct(len(selected_pairs), len(pairs)),
                            'khop_6': correct, 'lech_6': len(selected_pairs)-correct,
                            'ty_le_lech_6_pct': pct(len(selected_pairs)-correct, len(selected_pairs))}
    by_source_warning = {}
    for source in sorted({r.get('nguon_du_lieu', '') for r, _ in pairs}):
        source_pairs = [(r, p) for r, p in pairs if r.get('nguon_du_lieu', '') == source]
        by_source_warning[source] = {}
        for warned in (False, True):
            subset = [(r, p) for r, p in source_pairs if bool(p['canh_bao']) == warned]
            correct = sum(same_core(r, p) for r, p in subset)
            by_source_warning[source]['co_canh_bao' if warned else 'khong_canh_bao'] = {
                'so_mau': len(subset), 'bao_phu_nguon_pct': pct(len(subset), len(source_pairs)),
                'khop_6': correct, 'lech_6': len(subset)-correct,
                'ty_le_lech_6_pct': pct(len(subset)-correct, len(subset))}
    ward_known = [d for d in diagnostics if d['tham_chieu']['ma_xa']]
    report = {'thoi_diem_utc': datetime.now(timezone.utc).isoformat(), 'phien_ban_loi': model.PHIEN_BAN,
              'so_mau': len(rows), 'beam_goc': model.beam, 'beam_doi_chung': wide_beam,
              'khop_6': sum(d['khop_6'] for d in diagnostics),
              'oracle_6_trong_beam_goc': sum(d['co_nhanh_khop_6_beam40'] for d in diagnostics),
              'them_nhanh_khop_6_khi_mo_beam': sum(d['co_nhanh_khop_6_beam_rong'] is True for d in diagnostics),
              'co_che': dict(Counter(d['nhom_co_che'] for d in diagnostics)),
              'hanh_chinh': dict(Counter(d['hanh_chinh']['nhom'] for d in diagnostics)),
              'giu_dich_xa_qua_cac_buoc': {
                  'nhan_xa_co_gia_tri': len(ward_known),
                  'co_dich_trong_ung_vien': sum(d['hanh_chinh']['dich_trong_ung_vien'] for d in ward_known),
                  'beam40_con_nhanh_chua_dich': sum(d['hanh_chinh']['beam40_con_nhanh_chua_dich'] for d in ward_known),
                  'beam40_co_nhanh_chot_duy_nhat': sum(d['hanh_chinh']['beam40_co_nhanh_chot_duy_nhat'] for d in ward_known)},
              'theo_nhom': {key: {'so_mau': len(ds), 'khop_6': sum(d['khop_6'] for d in ds),
                                  'co_che': dict(Counter(d['nhom_co_che'] for d in ds))} for key, ds in groups.items()},
              'quyet_dinh_tung_truong': {f: field_decision_counts(pairs, f) for f in CORE},
              'loc_theo_canh_bao': selections,
              'loc_canh_bao_theo_nguon': by_source_warning,
              'chi_tiet': {f: {'lech': sum(not d['chi_tiet'][f]['khop_output'] for d in diagnostics),
                              'lech_chi_khac_dau': sum(d['chi_tiet'][f]['chi_khac_dau'] for d in diagnostics),
                              'lech_nhung_co_nhanh_khop': sum(not d['chi_tiet'][f]['khop_output'] and d['chi_tiet'][f]['co_nhanh_khop_truong'] for d in diagnostics)} for f in DETAIL},
              'co_ra_nhan': dict(Counter(flag for d in diagnostics for flag in d['co_can_ra_nhan'])),
              'ma_bam_dau_vao': digest(input_path), 'ma_bam_danh_muc': model.danh_muc.ma_bam,
              'ma_bam_source': {**manifest, str(Path(__file__).relative_to(ROOT)): digest(Path(__file__))},
              'bao_toan_du_lieu_source': True,
              'gioi_han': ['Mọi khớp/lệch đều so với nhãn máy/tổng hợp chưa xác minh độc lập.',
                           'Oracle là khả năng khớp nhãn trong nhánh đã xét, không là độ chính xác mô hình có thể đạt.',
                           'Nhánh chứng cứ tập con có thể bỏ qua bằng chứng khác trong input; không bảo đảm đúng ngữ nghĩa.',
                           'Không có nhánh chốt duy nhất không chứng minh đầu vào thực tế thiếu thông tin; nguồn tra/ứng viên có thể thiếu.',
                           'Beam rộng chỉ chẩn đoán trên các mẫu lệch và không có nhánh khớp trong beam gốc; không tối ưu cấu hình.',
                           'Các cờ căn chỉnh là dấu hiệu cần duyệt, không tự xác nhận nhãn sai.',
                           'Không cảnh báo không đồng nghĩa xác suất đúng cao; chưa hiệu chuẩn độ tin cậy.']}
    if digest(input_path) != report['ma_bam_dau_vao'] or digest(input_path) != baseline['input_sha256']:
        raise RuntimeError('Dev thay đổi trong lúc đo')
    if any(digest(ROOT / name) != value for name, value in manifest.items()):
        raise RuntimeError('Source thay đổi trong lúc đo')
    if any(digest(ROOT / 'data' / 'clean' / name) != value for name, value in model.danh_muc.ma_bam.items()):
        raise RuntimeError('Danh mục thay đổi trong lúc đo')
    (output_dir / 'thong_ke_chan_doan.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8', newline='\n')
    flat = []
    for d in diagnostics:
        flat.append({'id': d['id'], 'dau_vao': d['dau_vao'], 'nguon_du_lieu': d['nguon_du_lieu'],
                     'nhom_co_che': d['nhom_co_che'], 'nhom_hanh_chinh': d['hanh_chinh']['nhom'],
                     'truong_lech': ';'.join(d['truong_lech']),
                     'output': d['du_doan']['dia_chi_chuan'], 'tham_chieu': d['tham_chieu']['dia_chi_chuan'],
                     'output_6_truong': json.dumps(d['du_doan'], ensure_ascii=False),
                     'tham_chieu_6_truong': json.dumps(d['tham_chieu'], ensure_ascii=False),
                     'canh_bao': json.dumps(d['canh_bao'], ensure_ascii=False),
                     'co_ra_nhan': ';'.join(d['co_can_ra_nhan'])})
    write_csv(output_dir / 'doi_chieu_day_du.csv', tuple(flat[0]), flat)
    errors = [r for r, d in zip(flat, diagnostics) if not d['khop_6']]
    write_csv(output_dir / 'cac_ca_lech.csv', tuple(flat[0]), errors)
    write_report(output_dir / 'BAO_CAO.md', report, diagnostics)
    print(json.dumps({k: report[k] for k in ('so_mau', 'khop_6', 'oracle_6_trong_beam_goc', 'them_nhanh_khop_6_khi_mo_beam', 'co_che', 'hanh_chinh')}, ensure_ascii=False, indent=2))
    return report


def write_report(path, r, diagnostics):
    lines = ['# Chẩn đoán pipeline v2 trước khi tối ưu tiếp', '',
             f"Dev {r['so_mau']} mẫu; lõi giữ nguyên {r['phien_ban_loi']}, beam={r['beam_goc']}. Không dùng test cuối, không huấn luyện, không sửa nhãn.", '',
             '**Tất cả số khớp/lệch bên dưới đều so với nhãn máy/tổng hợp, chưa xác minh độc lập.**', '',
             '## Khả năng khớp nhãn qua các bước', '',
             f"- Output cuối khớp sáu trường: {r['khop_6']}/{r['so_mau']}.",
             f"- Có ít nhất một nhánh khớp sáu trường trong beam gốc: {r['oracle_6_trong_beam_goc']}/{r['so_mau']}.",
             f"- Trong các ca lệch chưa có nhánh khớp, beam đối chứng {r['beam_doi_chung']} tìm thêm {r['them_nhanh_khop_6_khi_mo_beam']} nhánh khớp.", '',
             'Oracle ở đây là khả năng tái hiện nhãn, không xác nhận nhãn đúng và không chứng minh mô hình thực tế đạt được tỷ lệ đó.', '',
             '## Nhóm cơ chế lệch sáu trường', '', '| Nhóm | Số mẫu |', '|---|---:|']
    for k, v in r['co_che'].items():
        lines.append(f'| {k} | {v} |')
    lines += ['', 'Nhóm có nhánh khớp nhưng xếp sau có thể bao gồm nhãn bỏ sót thông tin hoặc nhãn sai. Nhóm chi tiết bao gồm lỗi tách, phục hồi dấu và vấn đề nhãn; không tự quy toàn bộ cho parser.', '',
              '## Chẩn đoán mã xã và tỉnh', '', '| Nhóm | Số mẫu |', '|---|---:|']
    for k, v in r['hanh_chinh'].items():
        lines.append(f'| {k} | {v} |')
    funnel = r['giu_dich_xa_qua_cac_buoc']
    lines += ['', f"Trong {funnel['nhan_xa_co_gia_tri']} mẫu nhãn xã có giá trị: {funnel['co_dich_trong_ung_vien']} có đích trong ứng viên; {funnel['beam40_con_nhanh_chua_dich']} còn nhánh chứa đích trong beam; {funnel['beam40_co_nhanh_chot_duy_nhat']} có nhánh chốt đúng duy nhất cả xã và tỉnh."]
    lines += ['', 'Với nhãn xã có giá trị: tìm tập con ứng viên hợp lệ chốt duy nhất đúng cặp mã. Nếu tìm được mà beam gốc không giữ được thì có chứng cứ cắt beam. Nếu duyệt hết không tìm được, chỉ kết luận không chốt được từ bộ ứng viên và quan hệ hiện tại; chưa kết luận địa chỉ thực tế bất khả định. Duyệt quá giới hạn được báo riêng. Chứng cứ có thể bỏ qua phần input khác, nên vẫn cần rà ngữ nghĩa.', '',
              '## Điền trường và để trống', '',
              '| Trường | Điền khớp | Điền lệch | Trống khi nhãn có | Cùng trống | Lệch / số điền (%) |', '|---|---:|---:|---:|---:|---:|']
    for k, m in r['quyet_dinh_tung_truong'].items():
        lines.append(f"| {k} | {m['dien_khop']} | {m['dien_lech_nhan']} | {m['de_trong_khi_nhan_co']} | {m['cung_trong']} | {m['ty_le_lech_trong_so_dien_pct']} |")
    lines += ['', '## Cảnh báo có phân biệt được ca lệch không?', '',
              '| Nhóm | Mẫu | Bao phủ (%) | Khớp 6 | Lệch 6 | Lệch / nhóm (%) |', '|---|---:|---:|---:|---:|---:|']
    for k, m in r['loc_theo_canh_bao'].items():
        lines.append(f"| {k} | {m['so_mau']} | {m['bao_phu_pct']} | {m['khop_6']} | {m['lech_6']} | {m['ty_le_lech_6_pct']} |")
    lines += ['', '| Nguồn | Cảnh báo | Mẫu | Bao phủ nguồn (%) | Lệch 6 | Lệch / nhóm (%) |', '|---|---|---:|---:|---:|---:|']
    for source, groups in r['loc_canh_bao_theo_nguon'].items():
        for name, m in groups.items():
            lines.append(f"| {source} | {name} | {m['so_mau']} | {m['bao_phu_nguon_pct']} | {m['lech_6']} | {m['ty_le_lech_6_pct']} |")
    lines += ['', 'Đây chỉ là phép lọc theo cảnh báo sẵn có; không phải bộ ước lượng xác suất hoặc chính sách tự động đã được kiểm định.', '',
              '## Chênh lệch chi tiết', '', '| Trường | Lệch | Chỉ khác dấu | Lệch nhưng có nhánh khớp trường |', '|---|---:|---:|---:|']
    for k, m in r['chi_tiet'].items():
        lines.append(f"| {k} | {m['lech']} | {m['lech_chi_khac_dau']} | {m['lech_nhung_co_nhanh_khop']} |")
    lines += ['', '## Cờ cần rà nhãn', '', '| Dấu hiệu | Số mẫu mang cờ |', '|---|---:|']
    for k, v in r['co_ra_nhan'].items():
        lines.append(f'| {k} | {v} |')
    lines += ['', 'Các cờ có thể chồng nhau. Căn chỉnh nội dung bỏ dấu không chứng minh vai trò địa chỉ; một cờ cũng không đủ để kết luận nhãn sai.', '',
              '## Ví dụ đầy đủ theo cơ chế', '']
    grouped = defaultdict(list)
    for d in diagnostics:
        if not d['khop_6']:
            grouped[d['nhom_co_che']].append(d)
    for kind, ds in grouped.items():
        lines += ['### '+kind, '']
        for d in ds[:3]:
            lines += [f"**{d['id']}** ({d['nguon_du_lieu']})", '',
                      '- Input: '+d['dau_vao'], '- Output: '+d['du_doan']['dia_chi_chuan'],
                      '- Tham chiếu: '+d['tham_chieu']['dia_chi_chuan'],
                      '- Trường lệch: '+', '.join(d['truong_lech']),
                      '- Cờ rà nhãn: '+('; '.join(d['co_can_ra_nhan']) or 'không có cờ tự động'), '']
    lines += ['## Tệp và tái lập', '',
              '- `doi_chieu_day_du.csv`: tất cả input/output/tham chiếu và sáu trường riêng.',
              '- `cac_ca_lech.csv`: chỉ các ca lệch sáu trường, không tự coi tham chiếu là chân lý.',
              '- `chan_doan_tung_mau.jsonl`: nhánh đầu, nhánh khớp nếu có, tập đích, điểm và chứng cứ duyệt tập con.',
              '- `thong_ke_chan_doan.json`: mã băm source/dev/danh mục và chỉ số đầy đủ.', '',
              '```powershell', 'py -3.12 -X utf8 -B -m danh_gia.chan_doan_pipeline --output-dir danh_gia/ket_qua/chan_doan_lan_moi', '```', '',
              'Mỗi lần chạy phải tạo thư mục mới. Kiểm tra source/danh mục/input trùng lần đo v2, chạy lại API thật và đối chiếu toàn bộ kết quả từng mẫu; kiểm tra nhánh tái hiện khớp API; kiểm tra hash lại khi kết thúc.', '',
              '## Giới hạn', '']
    lines += ['- '+s for s in r['gioi_han']]
    path.write_text('\n'.join(lines)+'\n', encoding='utf-8', newline='\n')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', type=Path, default=ROOT / 'data/train_dev/dev.csv')
    p.add_argument('--baseline-dir', type=Path, default=ROOT / 'danh_gia/ket_qua/ban_thu_v2_cuoi')
    p.add_argument('--output-dir', type=Path, required=True)
    p.add_argument('--wide-beam', type=int, default=160)
    a = p.parse_args()
    run(a.input, a.output_dir, a.baseline_dir, a.wide_beam)


if __name__ == '__main__':
    main()
