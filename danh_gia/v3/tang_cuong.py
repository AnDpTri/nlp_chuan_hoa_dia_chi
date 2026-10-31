"""Tăng cường: thay phần thân số nhà trong các dòng agy đã kiểm bằng các dạng số nhà thật (dải, chuỗi, mã lô...).
Không dùng dev. Dạng lấy theo kiểu có trong nhãn tập train (train.csv) và sinh ngẫu nhiên.
Dùng: tang_cuong.py <so_dong_ra>  -> ghi bo_train/dat/goi_tc.jsonl"""
import duong_dan as dd  # gốc repo, CODE_ROOT vào sys.path
import json, random, re, sys
from pathlib import Path

DAT = dd.BO_TRAIN_DAT
R = random.Random(20261031)
CHU = 'ABCDEFGHKLMNPQRSTUVX'


def n(a=1, b=400):
    return str(R.randint(a, b))


def dang_so_nha():
    k = R.random()
    a = R.randint(1, 900)
    if k < .18:  # dải 2 số chẵn/lẻ liền: 141-143, 28-30
        return f"{a}-{a + 2}" if R.random() < .7 else f"{a} - {a + 2}"
    if k < .26:  # chuỗi nhiều số: 46-48-50-52
        m = R.randint(3, 4)
        return '-'.join(str(a + 2 * i) for i in range(m))
    if k < .34:  # liệt kê: 671;673 / 1031F;1031G
        if R.random() < .5:
            return f"{a};{a + 2}"
        c = R.choice(CHU[:6])
        return f"{a}{c};{a}{chr(ord(c) + 1)}"
    if k < .44:  # mã lô/căn: BT29, LK16-19, A1/1, C15, N45V
        p = R.choice(['BT', 'LK', 'TT', 'A', 'B', 'C', 'D', 'N', 'SH', 'NV', 'L'])
        q = R.random()
        if q < .3: return f"{p}{n(1, 60)}"
        if q < .55: return f"{p}{n(1, 30)}-{n(1, 40)}"
        if q < .75: return f"{p}{n(1, 20)}/{n(1, 30)}"
        return f"{p}{n(1, 9)} - {n(1, 60)}"
    if k < .52:  # số + chữ + số: 14D5, 105A2, 12B4
        return f"{a}{R.choice(CHU[:8])}{R.randint(1, 12)}"
    if k < .62:  # nhiều cấp gạch chéo: 353/30/16, 100C/4A, 53/7B
        q = R.random()
        if q < .5: return f"{a}/{n(1, 90)}/{n(1, 40)}"
        if q < .75: return f"{a}{R.choice('ABC')}/{n(1, 20)}{R.choice('AB')}"
        return f"{a}/{n(1, 60)}{R.choice('ABCD')}"
    if k < .68:  # Bis
        return f"{a}{R.choice(['Bis', ' Bis', 'bis', ' BIS'])}"
    if k < .74:  # km
        return f"Km{R.choice(['', ' '])}{n(1, 200)}{R.choice(['+', ' + '])}{R.randint(1, 9)}00"
    if k < .80:  # phòng/căn: P401, P.1203
        return f"P{R.choice(['', '.'])}{R.randint(1, 30)}{R.randint(1, 20):02d}"
    if k < .86:  # số - chữ: 57-57A, 131A-133, 40A - 40B
        q = R.random()
        if q < .4: return f"{a}-{a}{R.choice('ABC')}"
        if q < .7: return f"{a}A-{a + 2}"
        return f"{a}A - {a}B"
    if k < .92:  # mã chữ-số-gạch: S84-1, PG03-05A, SB23-395
        return f"{R.choice(['S', 'PG', 'SB', 'HH', 'TM'])}{R.randint(1, 99):02d}-{n(1, 400)}{R.choice(['', 'A', 'B'])}"
    return f"{a}{R.choice(CHU)}"


def thay(row):
    sp = [s for s in row['spans'] if s[0] == 'so_nha']
    if not sp:
        return None
    _, a, b = sp[0]
    goc = row['text'][a:b]
    m = re.match(r'^(\D*?)(\d.*)$', goc)  # tiền tố (Số / sn / so ...) + thân bắt đầu bằng chữ số
    if not m:
        return None
    tien_to = m.group(1)
    moi = dang_so_nha()
    if moi[0].isalpha() and tien_to and not tien_to.endswith((' ', '.')):
        tien_to += ' '
    if not tien_to and R.random() < .35:
        tien_to = R.choice(['Số ', 'số ', 'SN ', 'sn ', 'Nhà '])
    new = tien_to + moi
    d = len(new) - (b - a)
    text = row['text'][:a] + new + row['text'][b:]
    spans = []
    for f, x, y in row['spans']:
        if (x, y) == (a, b):
            spans.append([f, a, a + len(new)])
        elif x >= b:
            spans.append([f, x + d, y + d])
        else:
            spans.append([f, x, y])
    return {'id': row['id'] + '_tc', 'text': text, 'spans': spans, 'loai_nhieu': row['loai_nhieu'], 'nhieu_them': 'tang_cuong_so_nha'}


def main(so_dong):
    rows = [json.loads(l) for p in sorted(DAT.glob('goi_[0-9]*.jsonl')) for l in open(p, encoding='utf-8')]
    co = [r for r in rows if any(s[0] == 'so_nha' for s in r['spans'])]
    R.shuffle(co)
    out = [x for x in (thay(r) for r in co) if x][:int(so_dong)]
    for x in out:  # tự kiểm: span không chồng, nằm trong câu
        s = sorted(x['spans'], key=lambda z: z[1])
        assert all(0 <= a < b <= len(x['text']) for _, a, b in s)
        assert all(s[i][2] <= s[i + 1][1] for i in range(len(s) - 1))
    with open(DAT / 'goi_tc.jsonl', 'w', encoding='utf-8', newline='\n') as f:
        for x in out: f.write(json.dumps(x, ensure_ascii=False) + '\n')
    print(len(out), 'dong tang cuong')
    for x in out[:12]:
        print('  ', x['text'], '|', [x['text'][a:b] for f, a, b in x['spans'] if f == 'so_nha'])


if __name__ == '__main__':
    main(sys.argv[1])
