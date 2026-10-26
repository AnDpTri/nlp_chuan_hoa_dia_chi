"""Bước 5: chuyển đường đi trên cây cũ sang đơn vị hành chính mới.

Xã cũ nhập nguyên vào một xã mới thì đổi thẳng. Xã cũ bị chia thì dùng
thôn/xóm, đường nếu dữ liệu cho phép, không thì gắn cờ xa_bi_chia.
"""

from .danh_muc import DanhMuc
from .kieu_du_lieu import DuongDi


def sang_cay_moi(
    duong_di: DuongDi, phan_con: dict[str, str], danh_muc: DanhMuc
) -> tuple[str, str, list[str]]:
    """Trả về (ma_xa_moi, ma_tinh_moi, canh_bao)."""
    units = [danh_muc.lay(c.cay, c.ma) for c in duong_di.ung_vien]
    units.sort(key=lambda u: {"xa": 0, "huyen": 1, "tinh": 2}[u.cap])
    if not units:
        return "", "", ["thieu_xa", "thieu_tinh"]
    leaf = units[0]
    province = danh_muc.to_tien(leaf)[-1]
    if leaf.cay == "moi":
        return (
            (leaf.ma if leaf.cap == "xa" else ""),
            province.ma,
            ([] if leaf.cap == "xa" else ["thieu_xa"]),
        )
    target_province = danh_muc.tinh_cu_moi.get(province.ma, "")
    if leaf.cap != "xa":
        return "", target_province, ["thieu_xa"]
    targets = sorted(set(ma for ma, _ in danh_muc.doi_chieu.get(leaf.ma, [])))
    if len(targets) == 1:
        target = danh_muc.lay("moi", targets[0])
        return target.ma, target.ma_cha, []
    if len(targets) > 1:
        return "", target_province, ["xa_bi_chia"]
    return "", target_province, ["khong_co_doi_chieu"]
