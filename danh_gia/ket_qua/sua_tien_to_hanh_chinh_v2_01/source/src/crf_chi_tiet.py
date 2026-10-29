"""CRF bốn vai trò chi tiết + O; không gọi API, không tự phục hồi tên riêng."""

import hashlib
import math
import re
from pathlib import Path

from .tien_xu_ly import bo_dau
from .quy_tac import CHI_TIET, cac_tien_to, khop_tien_to
from .tach_phan_con import FIELDS, viet_ten


def dac_trung(tokens):
    """Đặc trưng quan sát toàn chuỗi, không dùng nhãn/mã/mốc tham chiếu."""
    markers = cac_tien_to(tokens)
    mark = {}
    for i, (end, kind, attrs) in markers.items():
        for j in range(i, end):
            mark[j] = kind + ':' + (attrs[0] if kind == 'chi_tiet' else 'admin')
    shapes = []
    for t in tokens:
        shape = ''.join('d' if c.isdigit() else 'X' if c.isupper() else 'x' if c.isalpha() else c for c in t)
        shapes.append(re.sub(r'(.)\1+', r'\1', shape))
    seq = []
    for i, t in enumerate(tokens):
        low, plain = t.casefold(), bo_dau(t)
        f = {'bias': 1., 'w': low, 'plain': plain, 'shape': shapes[i],
             'upper': t.isupper(), 'title': t.istitle(), 'digit': t.isdigit(),
             'has_digit': any(c.isdigit() for c in t), 'alpha': t.isalpha(),
             'punct': not any(c.isalnum() for c in t), 'accent': low != plain,
             'slash': '/' in t, 'mark': mark.get(i, ''), 'bos': i == 0, 'eos': i == len(tokens)-1}
        for size in (2, 3, 4):
            f['pre'+str(size)] = plain[:size]
            f['suf'+str(size)] = plain[-size:]
        for delta in (-2, -1, 1, 2):
            j = i+delta
            if 0 <= j < len(tokens):
                p = str(delta)+':'
                f[p+'w'] = tokens[j].casefold()
                f[p+'plain'] = bo_dau(tokens[j])
                f[p+'shape'] = shapes[j]
                f[p+'mark'] = mark.get(j, '')
                f[p+'digit'] = tokens[j].isdigit()
        seq.append(f)
    return seq


def bio_spans(labels):
    """I mồ côi mở span mới, đồng thời đếm lỗi BIO gốc để không che lỗi đo."""
    spans, invalid = [], 0
    field, start = None, 0
    for i, tag in enumerate([*labels, 'O']):
        role = tag[2:] if tag[:2] in {'B-', 'I-'} and tag[2:] in FIELDS else None
        continuation = role is not None and tag.startswith('I-') and role == field
        if tag.startswith('I-') and not continuation:
            invalid += 1
        if field is not None and not continuation:
            spans.append((field, start, i))
        if not continuation:
            field, start = role, i
    return spans, invalid


def tao_nhan(n, spans):
    tags = ['O'] * n
    for field, a, b in spans:
        if field not in FIELDS or not 0 <= a < b <= n:
            raise ValueError('Span sai phạm vi/nhãn')
        for i in range(a, b):
            if tags[i] != 'O':
                raise ValueError('Span chồng lấn')
            tags[i] = ('B-' if i == a else 'I-')+field
    return tags


def tien_to_hien_thi(tokens, field):
    """Chỉ giải tiền tố trong span đã nhận diện; không sửa tên riêng bên trong."""
    marker = khop_tien_to(tokens, 0, CHI_TIET) if tokens else None
    if marker and marker[1][0] == field:
        return marker
    # Các cách gõ Telex của đúng từ loại, gồm cách gõ ươ bằng uow/uwow.
    # Không fuzzy mọi từ đầu tên và không đổi dấu đã có.
    if field == 'duong' and tokens:
        raw = tokens[0].casefold()
        telex = {'dduowngf': 'Đường', 'duowngf': 'Đường',
                 'dduwowngf': 'Đường', 'duwowngf': 'Đường',
                 'dduongf': 'Đường', 'duongf': 'Đường', 'phoos': 'Phố'}
        if raw in telex:
            end = 2 if len(tokens) > 1 and tokens[1] == '.' else 1
            if end < len(tokens):
                return end, (field, telex[raw])
    return None


def dinh_dang_span(tokens, field):
    marker = tien_to_hien_thi(tokens, field)
    if marker and marker[1][0] == field:
        end, (_, label) = marker
        body = tokens[end:]
    else:
        body = tokens
        label = {'so_nha': 'Số', 'duong': 'Đường'}.get(field, '')
    if not body:
        return '', False
    if field == 'duong' and label == 'Đường':
        inner = khop_tien_to(body, 0, CHI_TIET)
        # d. QL 5A là loại tuyến cụ thể. Không xóa chữ Phố/Đường trong tên riêng.
        if inner and inner[1][0] == 'duong' and inner[1][1] in ('Quốc lộ', 'Tỉnh lộ'):
            end = inner[0]
            if end < len(body) and re.fullmatch(r'\d+[A-Za-z]{0,2}', body[end]):
                label, body = inner[1][1], body[end:]
    if field == 'so_nha':
        value = ''.join(body).replace('–', '-').replace('—', '-')
    else:
        value = viet_ten(body)
        if field == 'duong' and label in ('Quốc lộ', 'Tỉnh lộ'):
            value = ' '.join(t.upper() if re.fullmatch(r'\d+[A-Za-z]{1,2}', t) else t for t in value.split())
    return ' '.join(x for x in (label, value) if x), field == 'duong' and not marker


class NguCanhCRF:
    def __init__(self, tokens, labels, p_o):
        self.tokens, self.labels, self.p_o = tokens, labels, p_o
        self.loi_bio = bio_spans(labels)[1]

    def diem_hanh_chinh(self, occupied):
        return sum(math.log(max(self.p_o[i], 1e-8)) for i in occupied)

    def tach(self, occupied):
        tags = ['O' if i in occupied else tag for i, tag in enumerate(self.labels)]
        spans, _ = bio_spans(tags)
        values = {f: [] for f in FIELDS}
        output_spans, used = [], set(occupied)
        inferred = False
        for f, a, b in spans:
            # Dấu câu ngoài đoạn không thành tên; phần giữa đoạn vẫn giữ.
            while a < b and not any(c.isalnum() for c in self.tokens[a]):
                a += 1
            while b > a and not any(c.isalnum() for c in self.tokens[b-1]):
                b -= 1
            value, guessed = dinh_dang_span(self.tokens[a:b], f)
            if value and a < b:
                values[f].append(value)
                output_spans.append({'truong': f, 'bat_dau': a, 'ket_thuc': b, 'gia_tri': value})
                used.update(range(a, b))
                inferred |= guessed
        unknown = [i for i, t in enumerate(self.tokens) if i not in used and any(c.isalnum() for c in t)]
        detail = {f: ', '.join(dict.fromkeys(values[f])) for f in FIELDS}
        detail['phan_chua_phan_loai'] = ' '.join(self.tokens[i] for i in unknown)
        return detail, output_spans, unknown, inferred


class BoTachCRF:
    def __init__(self, model_path, bao_ve_chi_tiet=False):
        try:
            import pycrfsuite
        except ImportError as e:
            raise ImportError('Cần cài requirements-crf.txt bằng Python của .venv-crf') from e
        p = Path(model_path)
        self.ma_bam = hashlib.sha256(p.read_bytes()).hexdigest()
        self.tagger = pycrfsuite.Tagger()
        self.tagger.open(str(p))
        self.bao_ve_chi_tiet = bao_ve_chi_tiet

    def chuan_bi(self, tokens):
        if not tokens:
            return NguCanhCRF([], [], [])
        labels = self.tagger.tag(dac_trung(tokens))
        p_o = [self.tagger.marginal('O', i) for i in range(len(tokens))]
        return NguCanhCRF(tokens, labels, p_o)
