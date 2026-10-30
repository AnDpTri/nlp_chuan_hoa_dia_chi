"""Bước 5: chuyển đường đi trên cây cũ sang đơn vị hành chính mới.

Xã cũ nhập nguyên vào một xã mới thì đổi thẳng. Xã cũ bị chia thì dùng
thôn/xóm, đường nếu dữ liệu cho phép, không thì gắn cờ xa_bi_chia.
"""

from .danh_muc import DanhMuc
from .kieu_du_lieu import DuongDi


def tap_dich(duong_di: DuongDi, danh_muc: DanhMuc):
    wards = None
    provinces = None
    for u in duong_di.ung_vien:
        ps = set(danh_muc.dich_tinh(u.cay, u.ma))
        provinces = ps if provinces is None else provinces & ps
        if danh_muc.lay(u.cay, u.ma).cap == "xa" or (u.cay == "cu" and u.ma in danh_muc.huyen_thanh_dac_khu):
            ws = set(danh_muc.dich_xa(u.cay, u.ma))
            wards = ws if wards is None else wards & ws
    wards = set() if wards is None else wards
    provinces = set() if provinces is None else provinces
    wards = {w for w in wards if danh_muc.lay("moi", w).ma_cha in provinces}
    return wards, provinces


def sang_cay_moi(duong_di: DuongDi, phan_con: dict[str, str], danh_muc: DanhMuc) -> tuple[str, str, list[str]]:
    """Trả về (ma_xa_moi, ma_tinh_moi, canh_bao)."""
    wards, provinces = tap_dich(duong_di, danh_muc)
    warnings = []
    selected_ward = ""
    if len(wards) == 1:
        selected_ward = next(iter(wards))
    elif len(wards) > 1:
        # Tên xã đích trùng tên xã cũ KHÔNG chứng minh toàn bộ địa giới
        # thuộc xã đích đó. Không chốt mã khi thiếu chứng cứ phân tách
        # thôn/xóm, số nhà hoặc địa giới có thể kiểm chứng.
        warnings.append("xa_bi_chia")
    if not wards and any(u.cap == "xa" for u in duong_di.ung_vien):
        warnings.append("khong_co_doi_chieu")
    return (selected_ward, next(iter(provinces)) if len(provinces) == 1 else "", warnings)
