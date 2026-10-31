"""Cổng kiểm biến thể do agy sinh: chỉ nhận câu còn đủ ngữ cảnh và không bịa địa danh.

Một câu bị loại khi:
- trùng câu khác (sau khi gộp hoa/thường và khoảng trắng) hoặc trùng câu gốc;
- theo khai báo 'cap' của agy, các tên còn đọc được không chỉ ra đúng một xã cũ trong danh mục;
- tên xã của địa chỉ gốc không còn trong câu (so không dấu, bỏ khoảng trắng, cho phép sai 1 ký tự) dù agy khai là đọc được;
- câu chứa một tên đơn vị hành chính (2 âm tiết trở lên) không có trong địa chỉ gốc: agy đã thêm địa danh;
- số trong câu khác số của địa chỉ gốc (trừ số điện thoại 9 chữ số trở lên).

Dùng (từ gốc repo): py -3.12 data/bien_the/kiem_agy.py <goc.json> <ra.jsonl> <agy_raw.txt>...
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from sinh_to_hop import DanhMucCu, bo_dau, khoa  # noqa: E402

SO_CO_DAU = {'một': '1', 'hai': '2', 'ba': '3', 'bốn': '4', 'tư': '4', 'năm': '5', 'sáu': '6', 'bảy': '7',
             'tám': '8', 'chín': '9', 'mười': '10'}

GOC = Path(__file__).resolve().parents[2]


def doc_json(raw):
    m = re.search(r'\[.*\]', raw, re.S)
    if not m:
        raise ValueError('Không thấy mảng JSON trong đầu ra agy')
    return json.loads(m.group())


def phang(s):
    """Không dấu, thường, bỏ ký tự không phải chữ/số, coi i và y là một (mĩ = mỹ)."""
    return re.sub(r'[^a-z0-9]', '', khoa(s)).replace('y', 'i')


def gan_dung(a, b, toi_da=2):
    """Có đoạn con của a cách b không quá `toi_da` phép sửa (thêm/bớt/thay ký tự; telex 'myxhuwng' cách 'myhung' 2)."""
    a, b = phang(a), phang(b)
    truoc = [0] * (len(a) + 1)  # đoạn con: được bắt đầu ở bất kỳ vị trí nào của a
    for j, cb in enumerate(b, 1):
        sau = [j] + [0] * len(a)
        for i, ca in enumerate(a, 1):
            sau[i] = min(truoc[i] + 1, sau[i - 1] + 1, truoc[i - 1] + (ca != cb))
        truoc = sau
    return min(truoc) <= toi_da


def ten_hanh_chinh():
    """Tên đơn vị hành chính (2 âm tiết trở lên, không dấu) theo cấp: xa, huyen, tinh."""
    import csv
    ten = {'xa': set(), 'huyen': set(), 'tinh': set()}
    def them(cap, s):
        if len(s.split()) >= 2:
            ten[cap].add(bo_dau(s).casefold())
    for r in csv.DictReader(open(GOC / 'data/clean/cu_tinh_huyen_xa.csv', encoding='utf-8-sig')):
        them('xa', r['ten_xa']); them('huyen', r['ten_huyen']); them('tinh', r['ten_tinh'])
    for r in csv.DictReader(open(GOC / 'data/clean/moi_tinh_xa.csv', encoding='utf-8-sig')):
        them('xa', r['ten_xa']); them('tinh', r['ten_tinh'])
    return ten


# Chữ loại đứng trước tên xã/huyện; danh xưng và họ người đứng trước tên người (Chị Thảo, Nguyễn Văn An).
LOAI_TRUOC = r'(xa|x|phuong|p|ph|thi tran|tt|huyen|h|quan|q|thi xa|tx|thanh pho|tp|tinh|t)'
NGUOI_TRUOC = {'anh', 'chi', 'bac', 'chu', 'co', 'em', 'ong', 'ba', 'ban', 'a', 'c', 'e', 'nguyen', 'tran', 'le',
               'pham', 'hoang', 'huynh', 'phan', 'vu', 'vo', 'dang', 'bui', 'do', 'ho', 'ngo', 'duong', 'ly', 'van', 'thi'}


def dia_danh_la(cau, hc, am_tiet_goc):
    """Tên hành chính có âm tiết ngoài địa chỉ gốc. Tỉnh: luôn tính (hay viết trơn). Huyện: trừ khi đứng sau danh
    xưng/họ người. Xã: chỉ khi đứng ngay sau chữ loại (tên xã trùng tên người, cụm từ thường quá nhiều)."""
    la = []
    for cap, ds in hc.items():
        for t in ds:
            if f' {t} ' not in cau or set(t.split()) <= am_tiet_goc:
                continue
            truoc = [m.group(1).split()[-1] for m in re.finditer(rf'(\w+) {re.escape(t)} ', cau)]
            if cap == 'tinh' \
                    or cap == 'huyen' and not all(w in NGUOI_TRUOC for w in truoc) \
                    or re.search(rf' {LOAI_TRUOC} {re.escape(t)} ', cau):
                la.append(t)
    return sorted(la)


def main(goc_path, ra, *raw_paths):
    goc = json.loads(Path(goc_path).read_text(encoding='utf-8'))
    dm = DanhMucCu(GOC)
    ten_goc = {t['cap']: t['ten'] for t in goc['thanh_phan']}
    cho_phep = {bo_dau(t['ten']).casefold() for t in goc['thanh_phan']}
    # Số hợp lệ: mọi dãy số của địa chỉ gốc và số viết bằng chữ trong tên (Tháng Tám -> 8).
    so_goc = set(re.findall(r'\d+', goc['dia_chi'])) | {
        SO_CO_DAU[w] for t in goc['thanh_phan'] for w in t['ten'].casefold().split() if w in SO_CO_DAU}
    hc = {cap: ds - cho_phep for cap, ds in ten_hanh_chinh().items()}
    # Âm tiết gốc gồm cả chữ loại và cách đọc số (Quận 3 -> "quận ba"): ghép lại không thành địa danh bịa.
    am_tiet_goc = {w for c in cho_phep for w in c.split()} | {
        w for t in goc['thanh_phan'] for w in bo_dau(t['loai']).casefold().split()} | {
        bo_dau(k) for k, v in SO_CO_DAU.items() if v in so_goc}
    rows = []
    for p in raw_paths:
        try:
            rows += doc_json(Path(p).read_text(encoding='utf-8', errors='replace'))
        except ValueError as e:  # lượt agy lỗi (hết hạn mức, đầu ra rỗng): bỏ qua, báo ra
            print(f'bỏ qua {p}: {e}')
    nhan, loai, seen = [], [], {re.sub(r'\s+', ' ', goc['dia_chi']).casefold()}
    for i, r in enumerate(rows, 1):
        s = (r.get('dau_vao') or '').strip()
        cap = r.get('cap') or {}
        ly_do = []
        k = re.sub(r'\s+', ' ', s).casefold()
        if not s or k in seen:
            ly_do.append('trung_hoac_rong')
        seen.add(k)
        con = {c: ten_goc[c] for c in ('xa', 'huyen', 'tinh') if c in ten_goc and cap.get(c) == 'doc_duoc'}
        if dm.so_xa_khop(con) != 1:
            ly_do.append('khong_du_ngu_canh')
        if 'xa' in con and not gan_dung(s, ten_goc['xa']):
            ly_do.append('khong_thay_ten_xa')
        cau = ' ' + re.sub(r'[^\w]+', ' ', bo_dau(s).casefold()) + ' '
        # Địa danh bịa là tên có âm tiết không thuộc địa chỉ gốc; hai từ gốc đứng cạnh nhau ("hưng mỹ") không tính.
        la = dia_danh_la(cau, hc, am_tiet_goc)
        if la:
            ly_do.append('dia_danh_la:' + '|'.join(la[:3]))
        # Số đứng riêng cả cụm (không dính chữ: VNI 'd9inh5', 'xom5', '110A' không xét), bỏ số điện thoại trước
        # (từ 6 chữ số, kể cả số che bớt 0918234xxx).
        so = set(re.findall(r'(?<![^\W_])\d+(?![^\W_])', re.sub(r'\+?\d[\d.\s-]{5,}\d\w*', ' ', s)))
        if so - so_goc:
            ly_do.append('so_khac_goc:' + ','.join(sorted(so - so_goc)))
        out = {'id': f"{goc['id']}_a{i:03d}", 'goc': goc['id'], 'dau_vao': s, 'phep': r.get('phep', []),
               'so_phep': len(r.get('phep', [])), 'cap': cap, 'muc_thong_tin': 'du', 'nguon': 'agy',
               # Chỉ chấm thôn khi câu còn chữ loại của thôn (x5, xom 5, xóm năm); '5, Mỹ Hưng' có thể là số nhà.
               'cham_thon': bool(re.search(r'(?<![a-z])(xom|x)\.?\s*(\d+|nam)(?![0-9])', bo_dau(s).casefold()))}
        (loai if ly_do else nhan).append({**out, 'ly_do': ly_do} if ly_do else out)
    with open(ra, 'w', encoding='utf-8') as f:
        for r in nhan:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    Path(ra).with_suffix('.bi_loai.jsonl').write_text(
        ''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in loai), encoding='utf-8')
    print(f'nhận {len(nhan)}, loại {len(loai)}')
    for r in loai:
        print('  loại', repr(r['dau_vao']), r['ly_do'])


if __name__ == '__main__':
    main(*sys.argv[1:])
