"""Sinh khung bộ kiểm khó. Mỗi dòng: đơn vị thật từ danh mục + chi tiết tự đặt + loại nhiễu.
Khung (cho agy) không chứa mã/đáp án; dap_an_giu_kin.json chứa mã và chi tiết chuẩn."""
import csv, json, random, unicodedata, collections
C = r'D:\nlp_rf_combined\data\clean'


def rd(n):
    return list(csv.DictReader(open(C + '\\' + n, encoding='utf-8')))


def fold(s):
    s = unicodedata.normalize('NFD', s.replace('đ', 'd').replace('Đ', 'D'))
    return ''.join(c for c in s if unicodedata.category(c) != 'Mn').casefold().replace(' ', '')


cu_h = {r['ma_huyen']: r for r in rd('cu_huyen.csv')}
cu_t = {r['ma_tinh']: r for r in rd('cu_tinh.csv')}
cu_x = rd('cu_tinh_huyen_xa.csv')
moi_t = {r['ma_tinh']: r for r in rd('moi_tinh.csv')}
moi_x = rd('moi_tinh_xa.csv')
dc = collections.defaultdict(set)
for r in rd('doi_chieu_xa_cu_moi.csv'):
    if r['ma_xa_cu']:
        dc[r['ma_xa_cu']].add((r['ma_xa_moi'], r['ma_tinh_moi']))
idx_cu = collections.defaultdict(list)
idx_moi = collections.defaultdict(list)
for r in cu_x:
    idx_cu[fold(r['ten_xa'])].append(r)
for r in moi_x:
    idx_moi[fold(r['ten_xa'])].append(r)
TRAIN = {fold(e['canonical']) for e in json.load(open(r'D:\nlp_rf_gate\inputs\tu_dien_train.json', encoding='utf-8'))['entries']}

DUONG = ("Lê Lợi|Trần Hưng Đạo|Nguyễn Huệ|Hoàng Văn Thụ|Phạm Văn Đồng|Võ Thị Sáu|Lý Thường Kiệt|Nguyễn Trãi|Hai Bà Trưng|"
         "Điện Biên Phủ|Cách Mạng Tháng Tám|Nguyễn Văn Linh|Trường Chinh|Lê Duẩn|Quang Trung|Nguyễn Thị Minh Khai|Phan Đình Phùng|"
         "Lạc Long Quân|Âu Cơ|Bạch Đằng|Hùng Vương|Trần Phú|Nguyễn Du|Lê Hồng Phong|Đinh Tiên Hoàng|Ngô Quyền|Yersin|Tôn Đức Thắng|"
         "Phan Chu Trinh|Nguyễn Đình Chiểu|Huỳnh Thúc Kháng|Lương Văn Can|Bà Triệu|Thái Hà|Xuân Thủy|Cầu Giấy|Giải Phóng|Láng Hạ|"
         "Kim Mã|Nguyễn Chí Thanh|Hoàng Quốc Việt|Trần Duy Hưng|Tây Sơn|Chùa Bộc|Đê La Thành|Nguyễn Lương Bằng|Phạm Ngũ Lão|"
         "Nguyễn Thái Học|Pasteur|Nam Kỳ Khởi Nghĩa|Lê Văn Sỹ|Cống Quỳnh|Võ Văn Tần|Hồ Xuân Hương|Mạc Đĩnh Chi|Đồng Khởi|Phạm Hùng|"
         "Nguyễn Hữu Cảnh|Bình Giã|Hậu Giang|Tân Kỳ Tân Quý|Cộng Hòa|Hoàng Diệu|Bùi Thị Xuân|Đoàn Thị Điểm|Lê Quý Đôn|Ông Ích Khiêm|"
         "Nguyễn Tri Phương|Hàm Nghi|Núi Thành|Duy Tân|Phan Bội Châu|Phan Văn Trị|Mai Hắc Đế|Chu Văn An|Nguyễn Công Trứ|"
         "Trần Quốc Toản|Lê Thánh Tông|Dã Tượng|Cao Thắng|Trương Định|Nguyễn Văn Cừ|Hà Huy Tập|Võ Nguyên Giáp|Ngô Gia Tự|"
         "Nguyễn Tất Thành|Đặng Thai Mai|Hoa Lư|An Dương Vương|Trần Nhân Tông|Dương Đình Nghệ|Phú Lợi|Đại Cồ Việt|Nguyễn An Ninh|"
         "Hoàng Hoa Thám|Vạn Phúc|Nguyễn Bỉnh Khiêm|Lê Đại Hành|Thống Nhất|Bắc Sơn|Nguyễn Văn Trỗi|Lê Văn Việt|Đặng Văn Bi|"
         "Kha Vạn Cân|Lương Định Của|Dương Bá Trạc|Nguyễn Thượng Hiền|Cô Giang|Cô Bắc|Lý Tự Trọng|Ngô Thì Nhậm|Nguyễn Khuyến|"
         "Tô Hiến Thành|Trần Cao Vân|Vĩnh Viễn").split('|')
_TEST = {fold(x) for x in DUONG}
_ENTRIES = json.load(open(r'D:\nlp_rf_gate\inputs\tu_dien_train.json', encoding='utf-8'))['entries']
# Tên đường cho bộ TRAIN: từ điển train, bỏ mọi tên trùng danh sách của bộ khó (bộ khó vẫn đo được tên lạ)
DUONG = sorted({e['canonical'].split(' ', 1)[1] for e in _ENTRIES
                if ' ' in e['canonical'] and fold(e['canonical'].split(' ', 1)[1]) not in _TEST
                and not any(ch.isdigit() for ch in e['canonical'])})
SPECIAL = ['Quốc lộ 1A', 'Quốc lộ 5', 'Quốc lộ 14', 'Quốc lộ 51', 'Tỉnh lộ 8', 'Tỉnh lộ 10', 'Đường 3 Tháng 2',
           'Đường 30 Tháng 4', 'Đường 2 Tháng 9', 'Đường số 7', 'Đường số 12', 'Đường D5', 'Đường N3']
THON = ['Thôn', 'Xóm', 'Ấp', 'Bản', 'Tổ dân phố', 'Khu phố', 'Khu', 'Tổ']
NGO = ['Ngõ', 'Hẻm', 'Ngách', 'Kiệt']
TEN_THON = ['Na', 'Làng', 'Mới', 'Đông', 'Tây', 'Trung', 'Hạ', 'Khe Cát']
NHIEU = {
    'sach': 'Viết sạch, đúng chính tả, đầy đủ dấu, dấu phẩy chuẩn.',
    'khong_dau': 'Bỏ hết dấu tiếng Việt, viết thường toàn bộ.',
    'dinh_dau_phay': 'Bỏ dấu phẩy và dấu ngăn cách, viết liền một dòng như gõ nhanh trên điện thoại; có thể bỏ vài chữ loại.',
    'viet_tat': 'Viết tắt chữ loại theo lối quen dùng (X., H., T., P., Q., TT., TP., Tx., đ., kp., tdp) và tên tỉnh/thành phố lớn dạng thông dụng (HN, HCM, SG, ĐN...) nếu đúng; viết tắt nhiều chỗ cho nhanh.',
    'go_sai': 'Có 1 đến 2 lỗi gõ sai thật (thiếu/thừa/đổi/đảo ký tự, sai dấu, lỗi telex) trong tên hành chính hoặc tên đường. Lỗi phải là lỗi người ta hay gặp, tên vẫn đọc ra được.',
    'tap_nham': 'Chèn thêm thông tin không phải địa chỉ: số điện thoại, tên người nhận, tên tòa nhà/tầng/phòng, ghi chú giao hàng (gần chợ, gọi trước khi đến). Phần địa chỉ thật vẫn đầy đủ.',
    'doi_thu_tu_hoa': 'Đảo thứ tự các thành phần (từ lớn đến nhỏ hoặc xáo trộn), HOẶC viết HOA toàn bộ, HOẶC dấu cách/dấu câu thừa thiếu lộn xộn.',
    'chi_tiet_kho': 'Giữ phần chi tiết (số nhà, ngõ, thôn, đường) ở dạng khó: viết tắt (ng., h., đ., đ/c), thứ tự lạ, dính liền với chữ khác (ví dụ so12ngo47), số nhà có chữ cái hoặc dấu gạch.',
}
random.seed(20261031)


def chon_chi_tiet(kho):
    d = {}
    if random.random() < .72:
        b = str(random.choice([random.randint(1, 99), random.randint(1, 400), random.randint(1, 999)]))
        r = random.random()
        if r < .15:
            b += random.choice('ABCD')
        elif r < .25 or (kho and r < .5):
            b += '/' + str(random.randint(1, 60))
        d['so_nha'] = 'Số ' + b
    if random.random() < .18 + (.25 if kho else 0):
        d['ngo_ngach_hem'] = f"{random.choice(NGO)} {random.randint(1, 300)}"
    if random.random() < .15:
        k = random.choice(THON)
        d['thon_xom'] = f"{k} {random.randint(1, 15)}" if random.random() < .7 else f"{k} {random.choice(TEN_THON)}"
    if (random.random() < .6 and 'thon_xom' not in d) or random.random() < .1:
        if random.random() < .12:
            d['duong'] = random.choice(SPECIAL)
        else:
            d['duong'] = f"{random.choice(['Đường', 'Đường', 'Đường', 'Phố'])} {random.choice(DUONG)}"
    return d


def dem_khop(era, xa, huyen, tinh, hien):
    if era == 'moi':
        lst = [r for r in idx_moi[fold(xa['ten_xa'])] if 'tinh' not in hien or fold(r['ten_tinh']) == fold(tinh['ten_tinh'])]
        return {(r['ma_xa'], r['ma_tinh']) for r in lst}
    lst = [r for r in idx_cu[fold(xa['ten_xa'])]
           if ('huyen' not in hien or fold(r['ten_huyen']) == fold(huyen['ten_huyen']))
           and ('tinh' not in hien or fold(r['ten_tinh']) == fold(tinh['ten_tinh']))]
    out = set()
    for r in lst:
        out |= dc[r['ma_xa']]
    return out


N = 10000
khung, gold = [], []
kieu_ds = list(NHIEU)
for i in range(1, N + 1):
    era = random.choices(['cu', 'moi', 'lan'], [80, 14, 6])[0]
    if era == 'moi':
        xa = random.choice(moi_x); tinh = moi_t[xa['ma_tinh']]; huyen = None
    else:
        xa = random.choice(cu_x); huyen = cu_h[xa['ma_huyen']]; tinh = cu_t[xa['ma_tinh']]
    nhieu = random.choice(kieu_ds)
    nhieu2 = ''
    if nhieu != 'sach' and random.random() < .3:
        nhieu2 = random.choice([k for k in kieu_ds if k not in (nhieu, 'sach')])
    hien = {'xa', 'huyen', 'tinh'} if era != 'moi' else {'xa', 'tinh'}
    if random.random() < .22:
        hien.discard(random.choice([k for k in ('huyen', 'tinh') if k in hien]))
    ds = chon_chi_tiet(nhieu == 'chi_tiet_kho' or nhieu2 == 'chi_tiet_kho')
    loai_t, ten_t = (tinh['loai_tinh'], tinh['ten_tinh']) if 'tinh' in hien else ('', '')
    if era == 'lan':
        tm = {t for _, t in dc[xa['ma_xa']]}
        if len(tm) == 1 and 'tinh' in hien:
            t2 = moi_t[next(iter(tm))]
            loai_t, ten_t = t2['loai_tinh'], t2['ten_tinh']
        else:
            era = 'cu'
    ung_vien = dem_khop('moi' if era == 'moi' else 'cu', xa, huyen, tinh, hien) if era != 'lan' else dem_khop('cu', xa, huyen, tinh, hien - {'tinh'})
    kd = {'cu': 'địa chỉ CŨ (trước 2025): xã/huyện/tỉnh',
          'moi': 'địa chỉ MỚI (từ 01/07/2025): xã/phường + tỉnh, KHÔNG có cấp huyện',
          'lan': 'địa chỉ LẪN: tên xã và huyện cũ nhưng tên tỉnh viết theo tên tỉnh MỚI sau sáp nhập'}[era]
    d = dict(id=f"T{i:05d}", loai_nhieu=nhieu, nhieu_them=nhieu2,
             huong_dan=NHIEU[nhieu] + (' THÊM: ' + NHIEU[nhieu2] if nhieu2 else ''),
             kieu_dia_chi=kd, loai_xa=xa['loai_xa'], ten_xa=xa['ten_xa'],
             loai_huyen=huyen['loai_huyen'] if huyen and 'huyen' in hien else '',
             ten_huyen=huyen['ten_huyen'] if huyen and 'huyen' in hien else '',
             loai_tinh=loai_t, ten_tinh=ten_t,
             so_nha=ds.get('so_nha', ''), ngo_ngach_hem=ds.get('ngo_ngach_hem', ''),
             thon_xom=ds.get('thon_xom', ''), duong=ds.get('duong', ''))
    khung.append(d)
    gold.append(dict(
        id=d['id'], era=era, loai_nhieu=nhieu, nhieu_them=nhieu2, hien=sorted(hien),
        ma_xa_cu=xa['ma_xa'] if era != 'moi' else '', ma_huyen_cu=xa['ma_huyen'] if era != 'moi' else '',
        ma_tinh_cu=xa['ma_tinh'] if era != 'moi' else '',
        ma_xa_moi_ky_vong=sorted({x for x, _ in ung_vien}), ma_tinh_moi_ky_vong=sorted({t for _, t in ung_vien}),
        so_ung_vien=len({x for x, _ in ung_vien}),
        ma_xa_moi_that=xa['ma_xa'] if era == 'moi' else '', ma_tinh_moi_that=xa['ma_tinh'] if era == 'moi' else '',
        so_nha=ds.get('so_nha', ''), ngo_ngach_hem=ds.get('ngo_ngach_hem', ''),
        thon_xom=ds.get('thon_xom', ''), duong=ds.get('duong', ''),
        duong_trong_tu_dien_train=bool(ds.get('duong') and fold(ds['duong']) in TRAIN)))

for p in range(20):
    chunk = khung[p * 500:(p + 1) * 500]
    w = csv.DictWriter(open(f'../bo_train/khung/khung_{p + 1}.csv', 'w', encoding='utf-8', newline=''),
                       fieldnames=list(chunk[0].keys()), lineterminator='\n')
    w.writeheader()
    w.writerows(chunk)
json.dump(gold, open('../bo_train/dap_an.json', 'w', encoding='utf-8'), ensure_ascii=False)
print(collections.Counter(g['era'] for g in gold))
print(collections.Counter(g['loai_nhieu'] for g in gold))
print('ung vien>1:', sum(g['so_ung_vien'] > 1 for g in gold), '| ung vien=0:', sum(g['so_ung_vien'] == 0 for g in gold))
print('co duong:', sum(bool(g['duong']) for g in gold), '| duong trong tu dien train:', sum(g['duong_trong_tu_dien_train'] for g in gold))
