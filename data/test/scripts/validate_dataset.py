"""Fail closed on corpus/provenance/schema/coverage errors; this is not a model evaluation."""
import csv
import hashlib
import json
import re
import unicodedata
from datetime import datetime
from collections import Counter
from pathlib import Path
from admin_lookup import Catalogues, norm
from build_labels import FIELDS, full
from pin_catalogues import verify

ROOT = Path(__file__).resolve().parents[1]

ADMIN_PREFIX_REGEX = re.compile(
    r'\b(q\.|q|quan|quận|h\.|h|huyen|huyện|tx\.|tx|thi xa|thị xã|p\.|p|phuong|phường|x\.|x|xa|xã|tp\.|tp|thanh pho|thành phố)\s*$',
    re.IGNORECASE
)

def build_normalized_mapping(s):
    norm_chars = []
    orig_starts = []
    orig_ends = []
    i = 0
    n = len(s)
    while i < n:
        start_idx = i
        ch = s[i]
        i += 1
        while i < n and unicodedata.combining(s[i]):
            i += 1
        end_idx = i
        cluster = s[start_idx:end_idx]
        cluster_nfc = unicodedata.normalize('NFC', cluster).lower()
        c_decomp = unicodedata.normalize('NFD', cluster_nfc)
        c_norm = ''.join(c for c in c_decomp if not unicodedata.combining(c))
        c_norm = c_norm.replace('đ', 'd').replace('Đ', 'd')
        for single_char in c_norm:
            norm_chars.append(single_char)
            orig_starts.append(start_idx)
            orig_ends.append(end_idx)
    norm_text = ''.join(norm_chars)
    return norm_text, orig_starts, orig_ends

def remove_diacritics(s):
    norm_t, _, _ = build_normalized_mapping(s)
    return norm_t

def extract_core_token(val, field):
    val = val.strip()
    if not val:
        return ''
    if field == 'so_nha':
        prefixes = ['số nhà ', 'số: ', 'số ', 'no. ', 'no ', 'lô ', 'thửa ', 'căn ', 'phòng ', 'kiot ', 'nhà số ']
    elif field == 'duong':
        prefixes = ['đường ', 'phố ', 'đại lộ ', 'quốc lộ ', 'tỉnh lộ ', 'đ. ', 'đ.', 'p. ', 'ql. ', 'ql ', 'đt. ', 'đt ', 'ngõ ', 'ngách ', 'hẻm ', 'kiệt ']
    elif field == 'ngo_ngach_hem':
        prefixes = ['ngách ', 'ngõ ', 'hẻm ', 'kiệt ']
    elif field == 'thon_xom':
        prefixes = ['khu phố ', 'khu ', 'thôn ', 'xóm ', 'ấp ', 'bản ', 'tổ dân phố ', 'tổ ', 'tdp ', 'kp ']
    else:
        prefixes = []
    val_lower = val.lower()
    for p in prefixes:
        if val_lower.startswith(p):
            return val[len(p):].strip()
    return val

def is_valid_house_number_val(val):
    v = val.lower().strip()
    if re.search(r'\d', v):
        return True
    if re.search(r'\b(lo|lô|thua|thửa|can|căn|phong|phòng|kiot|kio|gian)\s+[a-z0-9]', v):
        return True
    return False

def check_token_boundary(text, s, e, fld):
    n = len(text)
    if fld == 'so_nha':
        if s > 0 and (text[s-1].isalnum() or text[s-1] in ('/', '-')):
            return False
        if e < n and (text[e].isalnum() or text[e] in ('/', '-')):
            return False
    else:
        if s > 0 and text[s-1].isalnum():
            return False
        if e < n and text[e].isalnum():
            return False
    return True

def check_context_role(text, s, fld):
    preceding = text[:s].rstrip()
    if fld in ('so_nha', 'duong'):
        if ADMIN_PREFIX_REGEX.search(preceding):
            return False
    return True

HAMLET_PREFIX_ABBREVS = {
    'khu pho': ['khu pho', 'kp', 'k.p'],
    'to dan pho': ['to dan pho', 'tdp', 't.d.p', 'to'],
    'thon': ['thon'],
    'xom': ['xom'],
    'ap': ['ap'],
    'ban': ['ban']
}

def get_hamlet_patterns(val):
    val_norm = remove_diacritics(val).strip()
    patterns = []
    patterns.append(rf'\b{re.escape(val_norm)}\b')
    for prefix, abbrevs in HAMLET_PREFIX_ABBREVS.items():
        if val_norm.startswith(prefix):
            core = val_norm[len(prefix):].strip()
            if core:
                for ab in abbrevs:
                    patterns.append(rf'\b{re.escape(ab)}\s*{re.escape(core)}\b')
            break
    return list(dict.fromkeys(patterns))

def check_field_grounding(inp, val, fld):
    val = val.strip()
    if not val:
        return True
    if fld == 'so_nha' and not is_valid_house_number_val(val):
        return False
    core = extract_core_token(val, fld)
    if fld == 'so_nha' and not is_valid_house_number_val(core):
        return False
    norm_inp, starts, ends = build_normalized_mapping(inp)
    
    if fld == 'thon_xom':
        pats = get_hamlet_patterns(val)
        for pat in pats:
            for m in re.finditer(pat, norm_inp):
                s, e = m.start(), m.end()
                if not check_token_boundary(norm_inp, s, e, fld):
                    continue
                return True
        if core and not core.isdigit():
            core_norm = remove_diacritics(core)
            if core_norm and re.search(rf'\b{re.escape(core_norm)}\b', norm_inp):
                return True
        return False

    candidates = []
    if core: candidates.append(core)
    if val and val != core: candidates.append(val)
    for cand in candidates:
        cand_norm = remove_diacritics(cand)
        if not cand_norm:
            continue
        pattern = re.escape(cand_norm)
        for m in re.finditer(pattern, norm_inp):
            s, e = m.start(), m.end()
            if not check_token_boundary(norm_inp, s, e, fld):
                continue
            if not check_context_role(norm_inp, s, fld):
                continue
            s_orig = starts[s]
            e_orig = ends[e - 1]
            matched_raw = inp[s_orig:e_orig]
            if remove_diacritics(matched_raw) == cand_norm:
                return True
    return False

def has_ward_evidence(ward_name_norm, inp_norm):
    if not ward_name_norm:
        return False
    if re.match(r'^\d+$', ward_name_norm):
        return bool(re.search(rf'\b(p\b|p\.|phuong\b|xa\b)\s*0*{re.escape(ward_name_norm)}\b', inp_norm)) or bool(re.search(rf',\s*0*{re.escape(ward_name_norm)}\s*,', inp_norm))
    pattern = rf'\b{re.escape(ward_name_norm)}\b'
    matches = list(re.finditer(pattern, inp_norm))
    if not matches:
        return False
    for m in matches:
        start = m.start()
        prefix = inp_norm[:start].rstrip(' .,/-')
        if re.search(r'\b(q\b|q\.|quan\b|quận\b|h\b|h\.|huyen\b|huyện\b|tx\b|tx\.|thi xa\b|thị xã\b|tp\b|tp\.|thanh pho\b|thành phố\b)$', prefix):
            continue
        if re.search(r'\b(duong\b|đường\b|pho\b|phố\b|ngo\b|ngõ\b|ngach\b|ngách\b|hem\b|hẻm\b)$', prefix):
            continue
        return True
    return False

def check_admin_grounding(row, cat, old_ds):
    inp_raw = row['dau_vao']
    inp_norm, _, _ = build_normalized_mapping(inp_raw)
    ma_xa_cu = row.get('ma_xa_cu', '').strip()
    ma_xa = row.get('ma_xa', '').strip()
    if ma_xa_cu and ma_xa_cu in cat.old_wi:
        w_old = cat.old_wi[ma_xa_cu]
        old_name_norm = remove_diacritics(w_old['ten_xa'])
        old_evidence = has_ward_evidence(old_name_norm, inp_norm)
            
        new_evidence = False
        if ma_xa and ma_xa in cat.new_wi:
            w_new = cat.new_wi[ma_xa]
            new_name_norm = remove_diacritics(w_new['ten_xa'])
            new_evidence = has_ward_evidence(new_name_norm, inp_norm)
        if not old_evidence and not new_evidence:
            return False, f"unobserved administrative ward in input: old_ward='{w_old['ten_xa']}' not found in input"
    elif ma_xa and ma_xa in cat.new_wi:
        w_new = cat.new_wi[ma_xa]
        new_name_norm = remove_diacritics(w_new['ten_xa'])
        if not has_ward_evidence(new_name_norm, inp_norm):
            return False, f"unobserved administrative ward in input: new_ward='{w_new['ten_xa']}' not found in input"
            
    ma_huyen_cu = row.get('ma_huyen_cu', '').strip()
    if ma_huyen_cu and ma_huyen_cu in old_ds:
        d_old = old_ds[ma_huyen_cu]
        d_name_norm = remove_diacritics(d_old['ten_huyen'])
        m_dist = re.search(r'\b(q\b|q\.|quan\b|quận\b|h\b|h\.|huyen\b|huyện\b|tx\b|tx\.|thi xa\b|thị xã\b|tp\b|tp\.|thanh pho\b|thành phố\b)\s*([a-z0-9\s]+?)(?:,|$)', inp_norm)
        if m_dist:
            dist_in_input = m_dist.group(2).strip()
            for t_name in ('hcm', 'ho chi minh', 'ha noi', 'hai phong', 'da nang', 'can tho'):
                if dist_in_input.endswith(' ' + t_name):
                    dist_in_input = dist_in_input[:-len(t_name)-1].strip()
            if dist_in_input and dist_in_input not in d_name_norm and d_name_norm not in dist_in_input:
                for other_d in old_ds.values():
                    if other_d['ma_tinh'] == d_old['ma_tinh'] and other_d['ma_huyen'] != ma_huyen_cu:
                        other_name_norm = remove_diacritics(other_d['ten_huyen'])
                        other_core = re.sub(r'^(quan|quận|huyen|huyện|thi xa|thị xã|thanh pho|thành phố)\s+', '', other_name_norm)
                        if other_name_norm == dist_in_input or other_core == dist_in_input or (dist_in_input in other_name_norm and len(dist_in_input) >= 3):
                            return False, f"conflicting administrative district in input: assigned='{d_old['ten_huyen']}' but input indicates '{dist_in_input}'"
    return True, ''

def is_valid_calendar_date(d_str):
    if not d_str or not re.match(r'^\d{4}-\d{2}-\d{2}$', str(d_str).strip()):
        return False
    try:
        dt = datetime.strptime(str(d_str).strip(), '%Y-%m-%d')
        # Kiểm tra tính hợp lý của năm (mốc dự án 2024-2030)
        return 2024 <= dt.year <= 2030
    except ValueError:
        return False

def is_valid_reviewer_name(name):
    if not name:
        return False
    name_clean = str(name).strip()
    if len(name_clean) < 2:
        return False
    if name_clean.lower() in ('bot', 'auto', 'ai', 'agy', 'gemini', 'none', 'null', 'unknown', 'test', 'reviewer'):
        return False
    return True

def is_valid_ai_reviewer_name(name):
    if not name:
        return False
    name_clean = str(name).strip().lower()
    return any(k in name_clean for k in ('ai', 'agent', 'gemini', 'antigravity', 'gpt', 'claude', 'deepmind')) or len(name_clean) >= 3

def main(csv_file=None):
    verify()
    errors, limitations = [], []
    def check(condition, message):
        if not condition: errors.append(message)
    cat = Catalogues()
    check(sum(r['loai_tinh']=='Thành phố' for r in cat.new_pi.values()) == 6, 'Target must use the six city types at 2025-07-01')
    target_csv = Path(csv_file) if csv_file else (ROOT / 'dia_chi_test.csv')
    with target_csv.open(encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f)
        check(reader.fieldnames == FIELDS, 'Incorrect final CSV schema/order')
        rows = list(reader)
    sources = [json.loads(s) for s in (ROOT / 'goc/selected_sources.jsonl').read_text(encoding='utf-8').splitlines()]
    by_id = {r['id']:r for r in sources}
    check(300 <= len(rows) <= 500, 'Corpus must contain 300–500 rows')
    check(len({r['id'] for r in rows}) == len(rows), 'Duplicate IDs')
    check(len({norm(r['dau_vao']) for r in rows}) == len(rows), 'Duplicate normalized input strings')
    check({r['id'] for r in rows} == set(by_id), 'Source/label ID mismatch')
    # Đọc thông tin đối chiếu duyệt từ bang_duyet_test.csv nếu có
    csv_path = Path(csv_file) if csv_file else ROOT / 'dia_chi_test.csv'
    bang_duyet_file = csv_path.parent / 'bang_duyet_test.csv'
    audit_by_id = {}
    if bang_duyet_file.exists():
        with bang_duyet_file.open(encoding='utf-8-sig') as f:
            audit_by_id = {row['id']: row for row in csv.DictReader(f)}

    def has_valid_human_evidence(r):
        identifier = r['id']
        # Kiểm tra metadata trong bang_duyet_test.csv nếu có
        if identifier in audit_by_id:
            audit = audit_by_id[identifier]
            reviewer = audit.get('nguoi_duyet', '').strip()
            date_str = audit.get('ngay_duyet', '').strip()
            reason = audit.get('ly_do_duyet', '').strip()
            status = audit.get('trang_thai_duyet', '').strip()
            loai = audit.get('loai_nguoi_duyet', '').strip().lower()
            if status == 'da_duyet' and loai != 'ai' and is_valid_reviewer_name(reviewer) and is_valid_calendar_date(date_str) and reason:
                return True
        # Kiểm tra metadata trong ghi_chu của tệp CSV
        ghi_chu = r.get('ghi_chu', '')
        m_rev = re.search(r'duyet_boi=([^;]+)', ghi_chu)
        m_date = re.search(r'ngay_duyet=([^;]+)', ghi_chu)
        m_reason = re.search(r'ly_do=([^;]+)', ghi_chu)
        m_loai = re.search(r'loai_nguoi_duyet=([^;]+)', ghi_chu)
        loai_val = m_loai.group(1).strip().lower() if m_loai else ""
        if m_rev and m_date and loai_val != 'ai':
            rev_name = m_rev.group(1).strip()
            date_str = m_date.group(1).strip()
            reason = m_reason.group(1).strip() if m_reason else ""
            if is_valid_reviewer_name(rev_name) and is_valid_calendar_date(date_str) and reason:
                return True
        return False

    def has_valid_ai_evidence(r):
        identifier = r['id']
        # Kiểm tra metadata trong bang_duyet_test.csv nếu có
        if identifier in audit_by_id:
            audit = audit_by_id[identifier]
            reviewer = audit.get('nguoi_duyet', '').strip()
            date_str = audit.get('ngay_duyet', '').strip()
            reason = audit.get('ly_do_duyet', '').strip()
            status = audit.get('trang_thai_duyet', '').strip()
            loai = audit.get('loai_nguoi_duyet', '').strip().lower()
            if (status in ('da_duyet_ai', 'da_duyet') or loai == 'ai') and is_valid_ai_reviewer_name(reviewer) and is_valid_calendar_date(date_str) and reason:
                return True
        # Kiểm tra metadata trong ghi_chu của tệp CSV
        ghi_chu = r.get('ghi_chu', '')
        m_rev = re.search(r'duyet_boi=([^;]+)', ghi_chu)
        m_date = re.search(r'ngay_duyet=([^;]+)', ghi_chu)
        m_reason = re.search(r'ly_do=([^;]+)', ghi_chu)
        if m_rev and m_date:
            rev_name = m_rev.group(1).strip()
            date_str = m_date.group(1).strip()
            reason = m_reason.group(1).strip() if m_reason else ""
            if is_valid_ai_reviewer_name(rev_name) and is_valid_calendar_date(date_str) and reason:
                return True
        return False

    old_ds = {r['ma_huyen']:r for r in cat.old_d}
    human_reviewed_count = 0
    ai_reviewed_count = 0
    for r in rows:
        identifier = r['id']; src = by_id[identifier]
        check(r['dau_vao'] == src['dau_vao'], identifier + ': input altered')
        check(r['nguon'] == src['source_url'], identifier + ': URL altered')
        check(src['name'] and any(src['tags'].get(k) for k in ('amenity','shop','office','tourism','craft','healthcare','leisure')), identifier + ': missing public POI evidence')
        if src['input_mode'] == 'addr:full':
            check(r['dau_vao'] == src['tags']['addr:full'], identifier + ': addr:full not verbatim')
        
        # Cho phép can_duyet, tu_dong_khop, da_duyet, da_duyet_ai
        check(r['trang_thai_nhan'] in ('can_duyet', 'tu_dong_khop', 'da_duyet', 'da_duyet_ai'), identifier + ': invalid review status')
        is_human_reviewed = False
        is_ai_reviewed = False
        if r['trang_thai_nhan'] == 'da_duyet':
            if has_valid_human_evidence(r):
                human_reviewed_count += 1
                is_human_reviewed = True
            else:
                check(False, identifier + ': trang_thai_nhan is da_duyet but missing valid human reviewer metadata')
        elif r['trang_thai_nhan'] == 'da_duyet_ai':
            if has_valid_ai_evidence(r):
                ai_reviewed_count += 1
                is_ai_reviewed = True
            else:
                check(False, identifier + ': trang_thai_nhan is da_duyet_ai but missing valid AI reviewer metadata')
        
        # BẮT BUỘC: Nếu đã duyệt (human hoặc ai), các thành phần trích xuất khác rỗng phải có grounding trên đầu vào
        if is_human_reviewed or is_ai_reviewed:
            for fld in ['so_nha', 'ngo_ngach_hem', 'thon_xom', 'duong']:
                val = r.get(fld, '').strip()
                if val:
                    check(check_field_grounding(r['dau_vao'], val, fld),
                          identifier + f': unobserved extracted component in input: {fld}={val}')
            # BẮT BUỘC: Đơn vị hành chính được gán nhãn phải có bằng chứng từ chuỗi đầu vào
            admin_ok, admin_msg = check_admin_grounding(r, cat, old_ds)
            check(admin_ok, identifier + ': ' + admin_msg)
        check(isinstance(json.loads(r['canh_bao']),list), identifier + ': warning JSON invalid')
        if r['ma_xa']:
            check(r['ma_xa'] in cat.new_wi, identifier + ': unknown new ward')
            if r['ma_xa'] in cat.new_wi:
                check(cat.new_wi[r['ma_xa']]['ma_tinh'] == r['ma_tinh'], identifier + ': new hierarchy mismatch')
                check(r['xa_phuong'] == full(cat.new_wi[r['ma_xa']],'xa'), identifier + ': target ward name/type differs from dated snapshot')
        if r['ma_tinh']:
            check(r['ma_tinh'] in cat.new_pi, identifier + ': unknown new province')
            if r['ma_tinh'] in cat.new_pi:
                check(r['tinh'] == full(cat.new_pi[r['ma_tinh']],'tinh'), identifier + ': target province name/type differs from dated snapshot')
        if r['ma_xa_cu']:
            ward = cat.old_wi.get(r['ma_xa_cu'])
            check(bool(ward), identifier + ': unknown old ward')
            if ward:
                check((ward['ma_huyen'],ward['ma_tinh']) == (r['ma_huyen_cu'],r['ma_tinh_cu']), identifier + ': old hierarchy mismatch')
            targets = {m['ma_xa_moi'] for m in cat.to_new[r['ma_xa_cu']]}
            if r['ma_xa']: check(r['ma_xa'] in targets, identifier + ': fabricated mapping')
            if len(targets) > 1:
                # Xã bị chia (fan-out > 1)
                if (is_human_reviewed or is_ai_reviewed) and r['ma_xa']:
                    # Người hoặc AI duyệt giải quyết xã bị chia khi có bằng chứng thực tế
                    check(r['ma_xa'] in targets, identifier + f': resolved split ward target {r["ma_xa"]} not in valid targets')
                    check(bool(r['xa_phuong']), identifier + ': resolved split ward must fill xa_phuong')
                    check('xa_bi_chia' not in json.loads(r['canh_bao']), identifier + ': resolved split ward should not retain xa_bi_chia warning')
                else:
                    # Chưa duyệt hoặc chưa đủ bằng chứng: bắt buộc để trống xã đích
                    check(not r['ma_xa'] and not r['xa_phuong'], identifier + ': split ward resolved without valid review')
                    check('xa_bi_chia' in json.loads(r['canh_bao']), identifier + ': missing split flag')
                    check('xa_moi_ung_vien=' in r['ghi_chu'], identifier + ': missing split candidates')
        if r['ma_huyen_cu']:
            check(r['ma_huyen_cu'] in old_ds and old_ds[r['ma_huyen_cu']]['ma_tinh'] == r['ma_tinh_cu'], identifier + ': district/province mismatch')
    stats = json.loads((ROOT / 'statistics.json').read_text(encoding='utf-8'))
    check(stats['confirmed_old_split_rows'] >= 20, 'Fewer than 20 code-confirmed old split-ward addresses')
    province_count = len({r['ma_tinh'] for r in rows if r['ma_tinh']})
    check(province_count >= 20, 'Insufficient geographic spread')
    check(stats['eras'].get('cu',0) > 0 and stats['eras'].get('moi',0) > 0, 'Need both old and new era examples')
    check(stats['no_diacritics'] > 0, 'No naturally unaccented inputs')
    check(stats['abbreviations'] > 0, 'No naturally abbreviated inputs')
    limitations += ['Nhãn sơ bộ do máy, chưa có dòng nào được người duyệt; chưa được dùng làm gold test.',
                    'OSM là dữ liệu cộng đồng: nguồn thật không đồng nghĩa địa chỉ luôn đúng hoặc còn hiện hành.',
                    'Xem statistics.json để phân biệt chuỗi addr:full nguyên văn và chuỗi ghép từ thẻ cấu trúc.',
                    'Không cố tình tạo lỗi gõ hay bỏ dấu; độ khó và tỷ lệ lỗi bị giới hạn bởi nguồn tự nhiên.',
                    'Không sử dụng tọa độ hay tên tổ chức để điền đơn vị hành chính thiếu trong đầu vào.',
                    'Các xã bị chia giữ nhiều ứng viên; cần đối chiếu chi tiết địa phương nếu muốn chốt đáp án.']
    is_ready_for_gold = (human_reviewed_count == len(rows) and not errors)
    provisional_only = (human_reviewed_count < len(rows))
    report = {'status': 'PASS' if not errors else 'FAIL',
              'structural_status': 'PASS' if not errors else 'FAIL',
              'is_ready_for_gold_evaluation': is_ready_for_gold,
              'provisional_only': provisional_only,
              'human_reviewed_rows': human_reviewed_count,
              'ai_reviewed_rows': ai_reviewed_count,
              'total_rows': len(rows),
              'review_progress': f"{human_reviewed_count}/{len(rows)} ({human_reviewed_count/len(rows)*100:.1f}%)",
              'ai_review_progress': f"{ai_reviewed_count}/{len(rows)} ({ai_reviewed_count/len(rows)*100:.1f}%)",
              'errors': errors,
              'rows': len(rows),
              'new_provinces_represented': province_count,
              'confirmed_old_split_rows': stats['confirmed_old_split_rows'],
              'limitations': limitations,
              'csv_sha256': hashlib.sha256(target_csv.read_bytes()).hexdigest()}
    # Phiên bản AI-only được đo riêng; không nâng nhãn AI thành human gold.
    ai_release = ROOT.parent / 'audit' / 'release_ai_20261030' / 'report.json'
    if ai_release.is_file():
        ai_meta = json.loads(ai_release.read_text(encoding='utf-8'))
        if ai_meta.get('input_hashes', {}).get('test') == report['csv_sha256']:
            tiers = ai_meta.get('test', {}).get('tiers', {})
            if sum(tiers.values()) == len(rows):
                report['ai_only_evaluation'] = {
                    'reviewed_in_existing_ai_log': len(rows),
                    'strict_provisional': tiers.get('AI_STRICT_PROVISIONAL', 0),
                    'accepted_with_risk': tiers.get('AI_ACCEPTED_WITH_RISK', 0),
                    'abstained': tiers.get('AI_ABSTAIN', 0),
                    'ready_for_ai_only_diagnostic': True,
                    'ready_for_human_gold': is_ready_for_gold,
                    'source': 'data/audit/release_ai_20261030/report.json',
                    'disclaimer': 'AI-only diagnostic, not human-verified Gold Test'
                }
        else:
            limitations.append('AI-only release hash differs from current test snapshot; re-run audit.')
    if csv_file is None:
        (ROOT / 'validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8', newline='\n')
    print(json.dumps(report, ensure_ascii=True, indent=2))
    if errors: raise SystemExit(1)
    return report

if __name__ == '__main__':
    main()
