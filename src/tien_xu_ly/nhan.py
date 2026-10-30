"""Schema nhãn dùng chung, độc lập kiến trúc model."""
from .tach_phan_con import FIELDS

ROLES = (*FIELDS, "xa", "huyen", "tinh")
TAGS = ["O"] + [prefix + role for role in ROLES for prefix in ("B-", "I-")]
TAG_ID = {t: i for i, t in enumerate(TAGS)}

def tag_spans(tags):
    out, role, start = [], None, 0
    for i, tag in enumerate([*tags, 'O']):
        current = tag[2:] if tag[:2] in ('B-', 'I-') else None
        continuation = current is not None and tag.startswith('I-') and role == current
        if role is not None and not continuation:
            out.append((role, start, i))
        if not continuation:
            role, start = current, i
    return out

