"""Tra tên đường từ train; không phải danh mục đường đã xác minh.

Chỉ bổ sung dấu/mở rộng dạng viết tắt có một kết quả trong tỉnh đã chọn.
Không sửa dấu đã nhập, không đoán gần đúng và không dùng nhãn dev/test.
"""

import hashlib
import itertools
import json
import unicodedata
from collections import defaultdict
from pathlib import Path

from .quy_tac import CHI_TIET, khop_tien_to
from .tien_xu_ly import bo_dau, token_co_vi_tri


def tach_ten(value):
    tokens = [t.chu for t in token_co_vi_tri(value)]
    marker = khop_tien_to(tokens, 0, CHI_TIET) if tokens else None
    if not marker or marker[1][0] != 'duong':
        return None
    end, (_, kind) = marker
    body = tokens[end:]
    if not body or any(not t.isalnum() for t in body):
        return None
    return kind, body


def khoa(words):
    return ''.join(bo_dau(w) for w in words)


def cac_dang(words):
    """Dạng đầy đủ và tổ hợp nguyên từ/chữ đầu, không sinh biến thể địa chỉ."""
    folded = [bo_dau(w) for w in words]
    out = {''.join(folded)}
    if 2 <= len(words) <= 7 and all(w.isalpha() for w in folded):
        for parts in itertools.product(*[(w, w[0]) for w in folded]):
            key = ''.join(parts)
            if len(key) >= 3:
                out.add(key)
    return out


def tuong_thich_dau(actual, canonical):
    actual = unicodedata.normalize('NFC', ''.join(actual)).casefold()
    canonical = unicodedata.normalize('NFC', ''.join(canonical)).casefold()
    if bo_dau(actual) != bo_dau(canonical):
        # Chỉ mở rộng viết tắt hoàn toàn không dấu.
        return actual == bo_dau(actual)
    return len(actual) == len(canonical) and all(a == b or a == bo_dau(b) for a, b in zip(actual, canonical))


class TuDienDuong:
    def __init__(self, path):
        path = Path(path)
        self.ma_bam = hashlib.sha256(path.read_bytes()).hexdigest()
        payload = json.loads(path.read_text(encoding='utf-8'))
        if payload.get('format') != 1 or payload.get('source_scope') != 'train_only':
            raise ValueError('Từ điển đường phải có schema train_only phiên bản 1')
        self.index = defaultdict(dict)
        for item in payload['entries']:
            parsed = tach_ten(item['canonical'])
            if not parsed or not item['province']:
                raise ValueError('Tên/tỉnh từ điển không hợp lệ')
            kind, words = parsed
            for key in cac_dang(words):
                self.index[item['province'], kind, key][item['canonical'].casefold()] = item

    def ung_vien(self, value, ma_tinh):
        """Trả cả va chạm và xung đột dấu; không chọn tên thay caller."""
        parsed = tach_ten(value)
        if not parsed or not ma_tinh:
            return []
        kind, words = parsed
        choices = list(self.index.get((ma_tinh, kind, khoa(words)), {}).values())
        out = []
        for item in sorted(choices, key=lambda x: x['canonical']):
            _, canonical_words = tach_ten(item['canonical'])
            out.append({'gia_tri': kind + ' ' + ' '.join(canonical_words),
                        'tuong_thich_dau': tuong_thich_dau(words, canonical_words),
                        'nguon': 'tu_dien_train_chua_xac_minh', 'ma_tinh': ma_tinh,
                        'train_ids': list(item['train_ids']), 'tu_dien_sha256': self.ma_bam,
                        'xac_minh_doc_lap': False})
        return out

    def chuan_hoa(self, value, ma_tinh):
        choices = self.ung_vien(value, ma_tinh)
        # Không chọn bằng tần suất khi cùng khóa có nhiều tên, kể cả khác dấu.
        if len(choices) != 1:
            return value, None
        item = choices[0]
        if not item['tuong_thich_dau']:
            return value, None
        new = item['gia_tri']
        if new.casefold() == value.casefold():
            return value, None
        return new, {'nguon': 'tu_dien_train_chua_xac_minh', 'ma_tinh': ma_tinh,
                     'gia_tri_truoc': value, 'gia_tri_sau': new,
                     'train_ids': item['train_ids'], 'tu_dien_sha256': self.ma_bam}


def tao_tu_dien(train_path, output):
    train_path, output = Path(train_path), Path(output)
    entries = {}
    rejected = defaultdict(int)
    rows = 0
    for line in train_path.read_text(encoding='utf-8').splitlines():
        row = json.loads(line)
        if row.get('split') not in ('train_goc', 'train_bo_sung'):
            raise ValueError('Không chấp nhận hàng ngoài train')
        rows += 1
        ref = row['ref']
        value = ref.get('duong', '')
        parsed = tach_ten(value)
        if not row.get('canonical_usable') or not parsed or not ref.get('ma_tinh'):
            rejected['thieu_ten_tinh_hoac_nhan_khong_dung_duoc'] += 1
            continue
        _, words = parsed
        aliases = cac_dang(words)
        observed = []
        for field, a, b in row['detail_spans_raw']:
            if field != 'duong':
                continue
            raw = row['text'][a:b]
            raw_parsed = tach_ten(raw)
            raw_words = raw_parsed[1] if raw_parsed else [t.chu for t in token_co_vi_tri(raw)]
            if raw_words and khoa(raw_words) in aliases and tuong_thich_dau(raw_words, words):
                observed.append(raw)
        if not observed:
            rejected['ten_khong_can_chinh_voi_span_train'] += 1
            continue
        key = ref['ma_tinh'], value.casefold()
        item = entries.setdefault(key, {'province': ref['ma_tinh'], 'canonical': value,
                                        'train_ids': [], 'observed_forms': []})
        item['train_ids'].append(row['id'])
        item['observed_forms'] = sorted(set(item['observed_forms'] + observed))
    payload = {'format': 1, 'source_scope': 'train_only', 'label_quality': 'nhan_train_chua_phai_danh_muc_duong_chung_thuc',
               'source_sha256': hashlib.sha256(train_path.read_bytes()).hexdigest(),
               'source_rows': rows, 'rejected': dict(rejected),
               'entries': sorted(entries.values(), key=lambda r: (r['province'], r['canonical']))}
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x', encoding='utf-8', newline='\n') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return payload
