"""Định dạng giá trị từ span; không chạy model, không tra mã hành chính."""
import re
from .quy_tac import CHI_TIET, khop_tien_to
from .tach_phan_con import viet_ten

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


def ghep_so_nha(tokens):
    if not tokens:
        return ''
    norm_tokens = ['-' if t in ('–', '—') else t for t in tokens]
    no_space_chars = {'/', '\\', '-', '_', ';', '+'}
    parts = []
    for i, t in enumerate(norm_tokens):
        if i == 0:
            parts.append(t)
            continue
        prev = norm_tokens[i - 1]
        if t in no_space_chars or prev in no_space_chars:
            parts.append(t)
        elif prev.isdigit() and len(t) == 1 and t.isalpha():
            parts.append(t)
        elif len(prev) == 1 and prev.isalpha() and t.isdigit():
            parts.append(t)
        else:
            parts.append(' ' + t)
    res = ''.join(parts).strip()
    return re.sub(r'\s+([,.;:])', r'\1', res)


def dinh_dang_span(tokens, field, tien_to_mac_dinh=True, tien_to_so_nha=None, tien_to_duong=None):
    if tien_to_so_nha is None:
        tien_to_so_nha = tien_to_mac_dinh
    if tien_to_duong is None:
        tien_to_duong = tien_to_mac_dinh
    marker = tien_to_hien_thi(tokens, field)
    if marker and marker[1][0] == field:
        end, (_, label) = marker
        body = tokens[end:]
    else:
        body = tokens
        if field == 'so_nha':
            label = 'Số' if tien_to_so_nha else ''
        elif field == 'duong':
            label = 'Đường' if tien_to_duong else ''
        else:
            label = ''
    if not body:
        return '', False
    if field == 'duong' and label in ('Đường', ''):
        inner = khop_tien_to(body, 0, CHI_TIET)
        # d. QL 5A là loại tuyến cụ thể. Không xóa chữ Phố/Đường trong tên riêng.
        if inner and inner[1][0] == 'duong' and inner[1][1] in ('Quốc lộ', 'Tỉnh lộ', 'ĐT', 'HL', 'ĐH'):
            end = inner[0]
            if end < len(body) and re.fullmatch(r'\d+[A-Za-z]{0,2}', body[end]):
                label, body = inner[1][1], body[end:]
    if field == 'so_nha':
        clean_tokens = [t for t in body if not (t.isdigit() and len(t) in (5, 6))]
        if not clean_tokens:
            clean_tokens = body
        while clean_tokens and clean_tokens[0] in {',', ';', '.'}:
            clean_tokens.pop(0)
        while clean_tokens and clean_tokens[-1] in {',', ';', '.'}:
            clean_tokens.pop()
        value = ghep_so_nha(clean_tokens)
        # Cờ này chỉ điều khiển việc *tự thêm* tiền tố khi input không có.
        # Nếu input đã ghi rõ "Số", phải bảo toàn kiểu hiển thị đó.
        if not tien_to_so_nha and not marker:
            return value, False
    else:
        value = viet_ten(body)
        if field == 'duong' and label in ('Quốc lộ', 'Tỉnh lộ', 'ĐT', 'HL', 'ĐH'):
            value = ' '.join(t.upper() if re.fullmatch(r'\d+[A-Za-z]{1,2}', t) else t for t in value.split())
    return ' '.join(x for x in (label, value) if x), field == 'duong' and not marker
