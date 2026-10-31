"""Kiểm máy đầu ra agy cho bộ TRAIN và xuất dòng đạt sang định dạng train CNN (text + spans ký tự).
Dùng: kiem_train.py 1 2 3 ...   -> in thống kê, ghi dat/goi_N.jsonl và loai/goi_N.jsonl"""
import csv, json, re, sys, unicodedata, collections
from difflib import SequenceMatcher
from pathlib import Path

D = Path(r'D:\nlp_rf_gate\reports\ten_cu\bo_train')
NHAN = {'so_nha', 'ngo_ngach_hem', 'thon_xom', 'duong', 'xa', 'huyen', 'tinh', 'O'}
TRUONG = ('so_nha', 'ngo_ngach_hem', 'thon_xom', 'duong')
VT_TINH = re.compile(r'^(hn|hcm|tphcm|tp\.?hcm|sg|sai gon|dn|hp|ct|brvt|vt|bd|dnai|tth|hue)$')


def fold(s):
    s = unicodedata.normalize('NFD', (s or '').replace('đ', 'd').replace('Đ', 'D'))
    return ''.join(c for c in s if unicodedata.category(c) != 'Mn').casefold()


def chu(s):
    return re.sub(r'[^a-z0-9]', '', fold(s))


def giong(ten, manh, nguong=.78):
    k, a = chu(ten), chu(manh)
    if not k: return True
    if k in a: return True
    n = len(k)
    return any(SequenceMatcher(None, k, a[i:i + L]).ratio() >= nguong
               for L in (n - 2, n - 1, n, n + 1, n + 2) if L > 0 for i in range(0, max(0, len(a) - L) + 1))


def so(s):
    return re.findall(r'\d+', fold(s))


def kiem_dong(r, k):
    loi = []
    manh = r.get('manh')
    if not isinstance(manh, list) or not manh: return ['khong_co_manh']
    if any(not (isinstance(m, list) and len(m) == 2 and isinstance(m[0], str) and m[1] in NHAN) for m in manh):
        return ['manh_sai_dinh_dang']
    if ''.join(m[0] for m in manh) != r.get('dia_chi'): loi.append('noi_khac_dia_chi')
    if any(m[0] == '' for m in manh): loi.append('manh_rong')
    dem = collections.Counter(m[1] for m in manh if m[1] != 'O')
    can = {f for f in TRUONG if k[f]} | {c for c in ('xa', 'huyen', 'tinh') if k[f'ten_{c}']}
    for f in can:
        if dem[f] != 1: loi.append(f'{f}_xuat_hien_{dem[f]}')
    for f in set(dem) - can: loi.append(f'{f}_thua')
    lay = {m[1]: m[0] for m in manh if m[1] != 'O'}
    for f in ('so_nha', 'ngo_ngach_hem', 'thon_xom'):
        if f in lay and k[f] and so(k[f]) and so(k[f]) != so(lay[f])[:len(so(k[f]))] and not set(so(k[f])) <= set(so(lay[f])):
            loi.append(f'{f}_so_khac')
    for c in ('xa', 'huyen', 'tinh'):
        if c in lay and k[f'ten_{c}'] and not giong(k[f'ten_{c}'], lay[c]):
            bo = re.sub(r'^(thanh pho|tinh|tp\.?|t\.)\s*', '', fold(lay[c]).strip())
            dau = ''.join(w[0] for w in fold(k[f'ten_{c}']).split())
            # viết tắt thông dụng hoặc chữ cái đầu của tên (QN, NĐ, BTh...)
            # chữ cái đầu + từ cuối đầy đủ: T.Hóa, K.Hòa, N.Bình, Đ.Biên
            tu = fold(k[f'ten_{c}']).split(); goc = re.sub(r'[^a-z]', '', fold(lay[c]))
            dau_cuoi = len(tu) >= 2 and goc.endswith(tu[-1]) and goc[:1] == tu[0][:1] and len(goc) <= len(tu[-1]) + 2
            if not (dau_cuoi or VT_TINH.match(bo) or re.sub(r'[^a-z]', '', bo) in (dau, dau + 'h') or (len(bo) >= 2 and dau.startswith(re.sub(r'[^a-z]', '', bo)[:2]) and len(re.sub(r'[^a-z]', '', bo)) <= 3)):
                loi.append(f'{c}_ten_khac')
    if 'duong' in lay and k['duong']:
        ten = re.sub(r'^(Đường|Phố)\s+', '', k['duong'])
        if not giong(ten, lay['duong'], .7) and not (so(ten) and set(so(ten)) <= set(so(lay['duong']))):
            loi.append('duong_ten_khac')
    # mảnh O không được chứa số nhà/ngõ/thôn của khung
    o = ' '.join(m[0] for m in manh if m[1] == 'O')
    for f in ('so_nha', 'ngo_ngach_hem'):
        if k[f] and so(k[f]) and so(k[f])[0] in so(o) and so(k[f])[0] not in so(lay.get(f, '')):
            loi.append(f'{f}_nam_trong_O')
    return loi


def main(packs):
    tong = collections.Counter(); (D / 'dat').mkdir(exist_ok=True); (D / 'loai').mkdir(exist_ok=True)
    for p in packs:
        khung = {r['id']: r for r in csv.DictReader(open(D / 'khung' / f'khung_{p}.csv', encoding='utf-8'))}
        f = D / 'ra' / f'ra_{p}.jsonl'
        if not f.exists(): print('chua co', f.name); continue
        dat, loai = [], []
        seen = set()
        for i, ln in enumerate(open(f, encoding='utf-8')):
            try:
                r = json.loads(ln)
            except Exception:
                tong['json_hong'] += 1; continue
            k = khung.get(r.get('id'))
            if not k or r['id'] in seen:
                tong['id_la_hoac_trung'] += 1; continue
            seen.add(r['id'])
            loi = kiem_dong(r, k)
            if loi:
                loai.append({'id': r['id'], 'loi': loi, 'dia_chi': r.get('dia_chi'), 'manh': r.get('manh')})
                for x in loi: tong['loi_' + re.sub(r'_\d+$', '', x)] += 1
            else:
                spans, pos = [], 0
                for s, n in r['manh']:
                    if n != 'O': spans.append([n, pos, pos + len(s)])
                    pos += len(s)
                dat.append({'id': r['id'], 'text': r['dia_chi'], 'spans': spans, 'loai_nhieu': k['loai_nhieu'], 'nhieu_them': k['nhieu_them']})
        tong['thieu_id'] += len(set(khung) - seen)
        tong['dat'] += len(dat); tong['loai'] += len(loai)
        with open(D / 'dat' / f'goi_{p}.jsonl', 'w', encoding='utf-8', newline='\n') as w:
            for x in dat: w.write(json.dumps(x, ensure_ascii=False) + '\n')
        with open(D / 'loai' / f'goi_{p}.jsonl', 'w', encoding='utf-8', newline='\n') as w:
            for x in loai: w.write(json.dumps(x, ensure_ascii=False) + '\n')
        print(f'goi {p}: dat {len(dat)} / loai {len(loai)} / thieu {len(set(khung) - seen)}')
    print(dict(tong))


if __name__ == '__main__':
    main(sys.argv[1:])
