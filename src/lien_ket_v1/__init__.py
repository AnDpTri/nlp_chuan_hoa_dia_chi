import sys
from ..tien_xu_ly import lien_ket_v1 as _m
for _name in ('adapter_linking', 'cache_ung_vien', 'du_lieu_linking', 'mo_hinh_linking'):
    sys.modules[f'{__name__}.{_name}'] = sys.modules[f'src.tien_xu_ly.lien_ket_v1.{_name}']
sys.modules[__name__] = _m
