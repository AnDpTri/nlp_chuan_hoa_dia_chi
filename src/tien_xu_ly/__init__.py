from .lam_sach import BoLamSach
from .tien_xu_ly import (
    Token,
    tach_token,
    token_co_vi_tri,
    bo_dau,
    nfc_offsets,
)

__all__ = ["BoLamSach", "Token", "tach_token", "token_co_vi_tri", "bo_dau", "nfc_offsets"]


def __getattr__(name):
    from . import tien_xu_ly as _tx
    return getattr(_tx, name)
