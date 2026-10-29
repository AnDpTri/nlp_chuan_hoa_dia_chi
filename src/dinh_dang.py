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

