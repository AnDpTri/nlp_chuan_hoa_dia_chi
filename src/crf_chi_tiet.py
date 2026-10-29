"""CRF bốn vai trò chi tiết + O; không gọi API, không tự phục hồi tên riêng."""

import hashlib
import math
import re
from pathlib import Path

from .tien_xu_ly import bo_dau
from .quy_tac import CHI_TIET, cac_tien_to, khop_tien_to
from .tach_phan_con import FIELDS, viet_ten
from .dinh_dang import tien_to_hien_thi, dinh_dang_span


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


class NguCanhCRF:
    def __init__(self, tokens, labels, p_o):
        self.tokens, self.labels, self.p_o = tokens, labels, p_o
        self.loi_bio = bio_spans(labels)[1]

    def diem_hanh_chinh(self, occupied):
        return sum(math.log(max(self.p_o[i], 1e-8)) for i in occupied)

    def tach(self, occupied, tien_to_mac_dinh=True, tien_to_so_nha=None, tien_to_duong=None):
        if tien_to_so_nha is None:
            tien_to_so_nha = tien_to_mac_dinh
        if tien_to_duong is None:
            tien_to_duong = tien_to_mac_dinh
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
            if a >= b:
                continue
            # Không lấy thành phần là 'thành phố' làm đường
            if f == 'duong' and a > 0:
                prev_tok = bo_dau(self.tokens[a-1].casefold())
                curr_tok = bo_dau(self.tokens[a].casefold())
                if prev_tok in ('thanh', 'tp') and curr_tok == 'pho':
                    continue
            marker = khop_tien_to(self.tokens, a, CHI_TIET)
            if marker:
                proper_field = marker[1][0]
                if proper_field in FIELDS:
                    f = proper_field
            if f == 'duong' and a > 0:
                prev_tok = bo_dau(self.tokens[a-1].casefold())
                curr_tok = bo_dau(self.tokens[a].casefold())
                if prev_tok in ('thanh', 'tp') and curr_tok == 'pho':
                    continue
            value, guessed = dinh_dang_span(self.tokens[a:b], f, tien_to_mac_dinh=tien_to_mac_dinh,
                                           tien_to_so_nha=tien_to_so_nha, tien_to_duong=tien_to_duong)
            if f == 'thon_xom' and value.casefold() in ('khu', 'khu đô thị'):
                value = ''
            if f == 'so_nha':
                num_val = value.casefold().replace('số', '').strip()
                if num_val.isdigit() and len(num_val) in (5, 6) and (b >= len(self.tokens) - 2 or all(not any(c.isalnum() for c in self.tokens[k]) for k in range(b, len(self.tokens)))):
                    value = ''
            if value and a < b:
                values[f].append(value)
                output_spans.append({'truong': f, 'bat_dau': a, 'ket_thuc': b, 'gia_tri': value})
                used.update(range(a, b))
                inferred |= guessed
        # Rà soát phần chưa phân loại (unknown) có tiền tố chi tiết rõ ràng
        unknown_candidates = [i for i, t in enumerate(self.tokens) if i not in used and any(c.isalnum() for c in t)]
        for i in unknown_candidates:
            if i in used:
                continue
            if i > 0:
                prev_tok = bo_dau(self.tokens[i-1].casefold())
                curr_tok = bo_dau(self.tokens[i].casefold())
                if prev_tok in ('thanh', 'tp') and curr_tok == 'pho':
                    continue
                if prev_tok in ('khu', 'to', 'khoi') and curr_tok == 'pho':
                    continue
            marker = khop_tien_to(self.tokens, i, CHI_TIET)
            if marker:
                end, (f, label) = marker
                if f == 'duong' and i > 0:
                    prev_tok = bo_dau(self.tokens[i-1].casefold())
                    curr_tok = bo_dau(self.tokens[i].casefold())
                    if prev_tok in ('thanh', 'tp') and curr_tok == 'pho':
                        continue
                j = end
                while j < len(self.tokens) and j not in used and self.tokens[j] not in {',', ';'}:
                    j += 1
                if j > i:
                    val, g = dinh_dang_span(self.tokens[i:j], f, tien_to_mac_dinh=tien_to_mac_dinh,
                                            tien_to_so_nha=tien_to_so_nha, tien_to_duong=tien_to_duong)
                    if f == 'so_nha':
                        num_val = val.casefold().replace('số', '').strip()
                        if num_val.isdigit() and len(num_val) in (5, 6) and (j >= len(self.tokens) - 2 or all(not any(c.isalnum() for c in self.tokens[k]) for k in range(j, len(self.tokens)))):
                            val = ''
                    if val:
                        values[f].append(val)
                        output_spans.append({'truong': f, 'bat_dau': i, 'ket_thuc': j, 'gia_tri': val})
                        used.update(range(i, j))
                        inferred |= g
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
