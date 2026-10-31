"""Đo RIÊNG tiền xử lý: đơn vị pipeline chọn (cây cũ/mới, theo dau_vet) và trường chi tiết, so với nhãn TRƯỚC chuyển đổi.
Hành chính, mỗi cấp xã/huyện/tỉnh, xếp loại:
  dung      : chọn đúng đơn vị (cũ đúng mã cũ, hoặc mới đúng mã mới)
  dung_cheo : chọn cây kia nhưng cùng đơn vị (cũ mà ánh xạ duy nhất sang đúng mã mới nhãn) -> tính đúng
  sai       : chọn đơn vị khác
  thieu     : nhãn có, pipeline không chọn
  thua      : nhãn không có, pipeline chọn (chỉ thống kê, không tính vào độ chính xác)
Chi tiết: so khớp sau khi bỏ dấu và khoảng trắng; nhãn rỗng và đoán rỗng thì không tính.
Dùng: do_tien_xu_ly.py dev | kho"""
import duong_dan as dd  # gốc repo, CODE_ROOT vào sys.path
import csv, json, sys, unicodedata, collections, random
from pathlib import Path

C = dd.CLEAN
dc = collections.defaultdict(set)
for r in csv.DictReader(open(C / 'doi_chieu_xa_cu_moi.csv', encoding='utf-8')):
    if r['ma_xa_cu']: dc[r['ma_xa_cu']].add(r['ma_xa_moi'])
tinh_cu_moi = collections.defaultdict(set)
for r in csv.DictReader(open(C / 'doi_chieu_xa_cu_moi.csv', encoding='utf-8')):
    tinh_cu_moi[r['ma_tinh_cu']].add(r['ma_tinh_moi'])
FIELDS = ('so_nha', 'ngo_ngach_hem', 'thon_xom', 'duong')


def fold(s):
    s = unicodedata.normalize('NFD', (s or '').replace('đ', 'd').replace('Đ', 'D'))
    return ''.join(c for c in s if unicodedata.category(c) != 'Mn').casefold().replace(' ', '')


cha_cu_xa = {r['ma_xa']: (r['ma_huyen'], r['ma_tinh']) for r in csv.DictReader(open(C / 'cu_tinh_huyen_xa.csv', encoding='utf-8'))}
cha_cu_huyen = {r['ma_huyen']: r['ma_tinh'] for r in csv.DictReader(open(C / 'cu_huyen.csv', encoding='utf-8'))}
cha_moi_xa = {r['ma_xa']: r['ma_tinh'] for r in csv.DictReader(open(C / 'moi_tinh_xa.csv', encoding='utf-8'))}


def chon(dau_vet, out_ma_tinh=''):
    """Đơn vị pipeline chọn; cấp cha không có đoạn chữ riêng thì suy từ cấp con theo danh mục (pipeline đã ngầm chọn)."""
    out = {}
    for d in dau_vet or []:
        if d.get('truong') in ('xa', 'huyen', 'tinh') and d.get('ma'):
            out.setdefault(d['truong'], (d.get('moc'), d['ma'], d.get('doan_goc', '')))
    x = out.get('xa')
    if x and x[0] == 'cu' and x[1] in cha_cu_xa:
        h, t = cha_cu_xa[x[1]]
        out.setdefault('huyen', ('cu', h, '(suy)')); out.setdefault('tinh', ('cu', t, '(suy)'))
    if x and x[0] == 'moi' and x[1] in cha_moi_xa:
        out.setdefault('tinh', ('moi', cha_moi_xa[x[1]], '(suy)'))
    h = out.get('huyen')
    if h and h[0] == 'cu' and h[1] in cha_cu_huyen:
        out.setdefault('tinh', ('cu', cha_cu_huyen[h[1]], '(suy)'))
    if 'tinh' not in out and out_ma_tinh:
        out['tinh'] = ('moi', out_ma_tinh, '(dau ra)')
    return out


def xep(cap, pick, g_cu, g_moi):
    if not g_cu and not g_moi:
        return 'thua' if pick else None
    if not pick:
        return 'thieu'
    moc, ma, _ = pick
    if (moc == 'cu' and ma == g_cu) or (moc == 'moi' and ma == g_moi):
        return 'dung'
    if moc == 'cu' and g_moi and not g_cu:
        m = dc[ma] if cap == 'xa' else (tinh_cu_moi[ma] if cap == 'tinh' else set())
        if m == {g_moi}: return 'dung'
    if moc == 'moi' and g_cu and not g_moi:
        if cap == 'xa' and dc[g_cu] == {ma}: return 'dung'
        if cap == 'tinh' and tinh_cu_moi[g_cu] == {ma}: return 'dung'
    return 'sai'


def cham(items):
    """items: (nhom, input, out, gold) ; gold có ma_*_cu, ma_*_moi, các trường chi tiết."""
    st = collections.defaultdict(collections.Counter); vd = collections.defaultdict(list)
    for nhom, inp, out, g in items:
        p = chon(out.get('dau_vet'), out.get('ma_tinh', ''))
        dung_ca = True
        for cap in ('tinh', 'huyen', 'xa'):
            k = xep(cap, p.get(cap), g.get(f'ma_{cap}_cu', ''), g.get(f'ma_{cap}_moi', ''))
            if k is None: continue
            for n in ('tat', nhom):
                st[n][f'{cap}_{k}'] += 1
            if k in ('sai', 'thieu'):
                dung_ca = False; vd[f'{cap}_{k}'].append((inp, p.get(cap), g.get(f'ma_{cap}_cu'), g.get(f'ma_{cap}_moi')))
        for f in FIELDS:
            a, b = fold(out.get(f, '')), fold(g.get(f, ''))
            if not a and not b: continue
            k = 'dung' if a == b else ('thieu' if not a else ('thua' if not b else 'sai'))
            for n in ('tat', nhom):
                st[n][f'{f}_{k}'] += 1
            if k != 'dung':
                dung_ca = False; vd[f'{f}_{k}'].append((inp, out.get(f, ''), g.get(f, '')))
        for n in ('tat', nhom):
            st[n]['n'] += 1; st[n]['dung_ca'] += dung_ca
    return st, vd


def in_bang(st):
    for n in ['tat'] + sorted(x for x in st if x != 'tat'):
        c = st[n]; s = f"{n:16} n={c['n']:5} dung_ca={100 * c['dung_ca'] / c['n']:.1f}%"
        for cap in ('tinh', 'huyen', 'xa') + FIELDS:
            # hành chính: "thừa" (suy ra cấp mà nhãn không ghi) không tính; chi tiết: thừa là lỗi thật
            tong = sum(c[f'{cap}_{k}'] for k in (('dung', 'sai', 'thieu') if cap in ('tinh', 'huyen', 'xa') else ('dung', 'sai', 'thieu', 'thua')))
            if tong:
                s += f" | {cap} {100 * c[f'{cap}_dung'] / tong:.1f}% (sai {c[f'{cap}_sai']}, thieu {c[f'{cap}_thieu']}, thua {c[f'{cap}_thua']})"
        print(s)


def dev():
    G = dd.DEV
    gold = {}
    for sp in ('dev_goc', 'dev_kho'):
        for r in csv.DictReader(open(G / f'{sp}.csv', encoding='utf-8-sig')):
            gold[(sp, r['id'])] = dict(r, ma_xa_moi=r['ma_xa'], ma_tinh_moi=r['ma_tinh'], ma_huyen_moi='')
    items = []
    for l in open(Path(__file__).parent / 'ref_8ccec47_train_p1.jsonl', encoding='utf-8'):
        r = json.loads(l); k = (r['split'], r['id'])
        if k in gold: items.append((r['split'], gold[k]['dau_vao'], r['out'], gold[k]))
    return items


def kho(kq_path=None):
    D = dd.BO_KHO
    g = {x['id']: x for x in json.load(open(D / 'dap_an_giu_kin.json', encoding='utf-8'))}
    kq = json.load(open(kq_path or D / 'kq_ta_dauvet.json', encoding='utf-8'))
    raw = {r['id']: r['dia_chi'] for p in range(1, 7) if (D / 'ra' / f'ra_{p}.csv').exists() for r in csv.DictReader(open(D / 'ra' / f'ra_{p}.csv', encoding='utf-8'))}
    items = []
    for i, out in kq.items():
        x = g[i]; hien = set(x['hien'])
        gg = {f: x[f] for f in FIELDS}
        if x['era'] == 'moi':
            gg.update(ma_xa_moi=x['ma_xa_moi_that'], ma_tinh_moi=x['ma_tinh_moi_that'] if 'tinh' in hien else '')
        else:
            gg.update(ma_xa_cu=x['ma_xa_cu'], ma_huyen_cu=x['ma_huyen_cu'] if 'huyen' in hien else '')
            if x['era'] == 'lan':
                gg.update(ma_tinh_moi=x['ma_tinh_moi_ky_vong'][0] if 'tinh' in hien and len(x['ma_tinh_moi_ky_vong']) == 1 else '')
            else:
                gg.update(ma_tinh_cu=x['ma_tinh_cu'] if 'tinh' in hien else '')
        if x['so_ung_vien'] > 1 and len(hien) < (2 if x['era'] == 'moi' else 3):
            gg['ma_xa_cu'] = gg.get('ma_xa_cu', ''); gg['mo_ho'] = True
        items.append((x['loai_nhieu'], raw[i], out, gg))
    return items


def tu_file(path):
    """Chấm cả dev và bộ khó từ một ket_qua.jsonl (chay_mo_hinh.py)."""
    outs = {(r['split'], r['id']): r['out'] for r in map(json.loads, open(path, encoding='utf-8'))}
    G = dd.DEV; D = dd.BO_KHO
    dev_items = []
    for sp in ('dev_goc', 'dev_kho'):
        for r in csv.DictReader(open(G / f'{sp}.csv', encoding='utf-8-sig')):
            g = dict(r, ma_xa_moi=r['ma_xa'], ma_tinh_moi=r['ma_tinh'], ma_huyen_moi='')
            dev_items.append((sp, r['dau_vao'], outs[(sp, r['id'])], g))
    kq = {i: o for (sp, i), o in outs.items() if sp == 'kho'}
    json.dump(kq, open(D / 'kq_tam_cham.json', 'w', encoding='utf-8'), ensure_ascii=False)
    return dev_items, kho(D / 'kq_tam_cham.json')


if __name__ == '__main__':
    if sys.argv[1] == 'file':
        a, b = tu_file(sys.argv[2])
        for ten, items in (('DEV', a), ('BO_KHO', b)):
            print('=====', ten); in_bang(cham(items)[0])
        sys.exit(0)
    items = dev() if sys.argv[1] == 'dev' else kho()
    st, vd = cham(items)
    in_bang(st)
    random.seed(1)
    print('\nVI DU LOI (toi da 4 moi loai):')
    for k in sorted(vd, key=lambda k: -len(vd[k])):
        print(f'--- {k}: {len(vd[k])}')
        for x in random.sample(vd[k], min(4, len(vd[k]))): print('   ', x)
