"""Chuyển đổi địa giới hành chính sang mô hình mới (01/07/2025).

Chỉ tra bảng DanhMuc, không có logic nhận diện hay xếp hạng.
"""

from ..danh_muc import DanhMuc, khoa_duong
from ..kieu_du_lieu import DiaChiSach, DonViNhan, KetQua


def xa_chia_theo_duong(don_vi: list[DonViNhan], duong: str, wards: set[str], danh_muc: DanhMuc) -> str:
    """Xã cũ bị chia: tra bảng (xã cũ, tên đường) -> xã mới. Chỉ khi giả thuyết có đúng một xã cũ
    và xã mới tra được nằm trong tập đích. Không có thì trả rỗng (giữ nguyên để trống)."""
    xa_cu = {u.ma for u in don_vi if u.cap == "xa" and u.cay == "cu"}
    if len(xa_cu) != 1 or not duong:
        return ""
    ma = next(iter(xa_cu))
    khoa = khoa_duong(duong)
    moi = danh_muc.xa_chia_theo_duong.get((ma, khoa), "") or _duong_gan_dung(ma, khoa, danh_muc)
    return moi if moi in wards else ""


def _khoang_cach(a: str, b: str) -> int:
    truoc = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        sau = [i]
        for j, cb in enumerate(b, 1):
            sau.append(min(truoc[j] + 1, sau[j - 1] + 1, truoc[j - 1] + (ca != cb)))
        truoc = sau
    return truoc[-1]


def _duong_gan_dung(ma_xa_cu: str, khoa: str, danh_muc: DanhMuc) -> str:
    """Tên đường gõ sai (Trần Quys Kiên, Ph.Trần Quý Kiên): so với các đường của chính xã cũ này trong bảng.
    Nhận khi lệch tối đa 2 ký tự (tên từ 10 chữ) hoặc 1 (6-9 chữ) và đường gần nhất hơn hẳn đường kế tiếp."""
    ds = sorted((_khoang_cach(khoa, k), moi) for (m, k), moi in danh_muc.xa_chia_theo_duong.items() if m == ma_xa_cu)
    if not ds or len(khoa) < 6:
        return ""
    toi_da = 2 if len(khoa) >= 10 else 1
    gan, moi = ds[0]
    if gan > toi_da or (len(ds) > 1 and ds[1][0] <= gan + 1 and ds[1][1] != moi):
        return ""
    return moi


def tap_dich(don_vi: list[DonViNhan], danh_muc: DanhMuc):
    """Tập xã mới và tỉnh mới mà các đơn vị đã nhận cùng trỏ tới (giao các tập)."""
    wards = None
    provinces = None
    for u in don_vi:
        ps = set(danh_muc.dich_tinh(u.cay, u.ma))
        provinces = ps if provinces is None else provinces & ps
        if danh_muc.lay(u.cay, u.ma).cap == "xa" or (u.cay == "cu" and u.ma in danh_muc.huyen_thanh_dac_khu):
            ws = set(danh_muc.dich_xa(u.cay, u.ma))
            wards = ws if wards is None else wards & ws
    wards = set() if wards is None else wards
    provinces = set() if provinces is None else provinces
    wards = {w for w in wards if danh_muc.lay("moi", w).ma_cha in provinces}
    return wards, provinces


def sang_cay_moi(don_vi: list[DonViNhan], phan_con: dict[str, str], danh_muc: DanhMuc) -> tuple[str, str, list[str]]:
    """Trả về (ma_xa_moi, ma_tinh_moi, canh_bao)."""
    wards, provinces = tap_dich(don_vi, danh_muc)
    warnings = []
    selected_ward = ""
    if len(wards) == 1:
        selected_ward = next(iter(wards))
    elif len(wards) > 1:
        warnings.append("xa_bi_chia")
    if not wards and any(u.cap == "xa" for u in don_vi):
        warnings.append("khong_co_doi_chieu")
    return (selected_ward, next(iter(provinces)) if len(provinces) == 1 else "", warnings)


def chan_doan_chuyen_doi(dia_chi_sach: DiaChiSach, danh_muc: DanhMuc) -> list[dict]:
    """Từng cách hiểu gần bằng đổi ra tập xã mới / tỉnh mới nào (để đọc lại vì sao để trống hay chọn)."""
    out = []
    for don_vi in dia_chi_sach.cach_hieu_gan or [dia_chi_sach.don_vi]:
        wards, provinces = tap_dich(don_vi, danh_muc)
        out.append({"don_vi": [[u.cap, u.ma, u.cay] for u in don_vi],
                    "xa_moi": sorted(wards), "tinh_moi": sorted(provinces)})
    return out


def _chuan_chuoi_dia_chi(res: KetQua) -> str:
    parts = []
    if res.so_nha:
        parts.append(res.so_nha if res.so_nha.startswith(("Số ", "Số")) else f"Số {res.so_nha}")
    if res.ngo_ngach_hem:
        parts.append(res.ngo_ngach_hem)
    if res.thon_xom:
        parts.append(res.thon_xom)
    if res.duong:
        road_pfx = ("Đường ", "Phố ", "Quốc lộ ", "Tỉnh lộ ", "Xa lộ ", "Đại lộ ", "ĐT ", "HL ", "Hương lộ ")
        parts.append(res.duong if any(res.duong.startswith(p) for p in road_pfx) else f"Đường {res.duong}")
    if res.xa_phuong:
        parts.append(res.xa_phuong)
    if res.tinh:
        parts.append(res.tinh)
    return ", ".join(parts)


def chuyen_doi(dia_chi_sach: DiaChiSach, danh_muc: DanhMuc | None = None) -> KetQua:
    if danh_muc is None:
        from ..danh_muc import DanhMuc as _DM
        danh_muc = _DM()
    best = dia_chi_sach.don_vi
    detail = {"so_nha": dia_chi_sach.so_nha, "ngo_ngach_hem": dia_chi_sach.ngo_ngach_hem,
              "thon_xom": dia_chi_sach.thon_xom, "duong": dia_chi_sach.duong,
              "phan_chua_phan_loai": dia_chi_sach.phan_chua_phan_loai}
    close_paths = dia_chi_sach.cach_hieu_gan
    target_sets = [tap_dich(p, danh_muc) for p in close_paths]
    wards, provinces = tap_dich(best, danh_muc)
    ma_xa, ma_tinh, warnings = sang_cay_moi(best, detail, danh_muc)
    outcomes = {(tuple(sorted(w)), tuple(sorted(p))) for w, p in target_sets}
    if len(outcomes) > 1:
        warnings.append("nhieu_cach_hieu")
        if len({u.cay for p in close_paths for u in p if u.cap == "xa"}) > 1:
            warnings.append("mo_ho_moc_cu_moi")
        if len({tuple(sorted(w)) for w, _ in target_sets}) > 1:
            ma_xa = ""
        positive_provinces = set().union(*(p for _, p in target_sets))
        ma_tinh = next(iter(positive_provinces)) if len(positive_provinces) == 1 else ""
    if len(wards) > 1:
        theo_duong = xa_chia_theo_duong(best, dia_chi_sach.duong, wards, danh_muc) if len(outcomes) <= 1 else ""
        if theo_duong:
            ma_xa = theo_duong
            warnings = [w for w in warnings if w != "xa_bi_chia"] + ["xa_chia_suy_tu_duong"]
        else:
            warnings.append("xa_bi_chia")
    warnings.extend(dia_chi_sach.canh_bao_giua)
    if not ma_xa:
        warnings.append("thieu_xa")
    if not ma_tinh:
        warnings.append("thieu_tinh")
    elif not any(u.cap == "tinh" for u in best):
        warnings.append("thieu_tinh_dau_vao")
    warnings.extend(dia_chi_sach.canh_bao_sau)
    all_wards = set().union(*(w for w, _ in target_sets))
    result = KetQua(
        so_nha=dia_chi_sach.so_nha, ngo_ngach_hem=dia_chi_sach.ngo_ngach_hem,
        thon_xom=dia_chi_sach.thon_xom, duong=dia_chi_sach.duong,
        xa_phuong=danh_muc.ten_day_du("moi", ma_xa) if ma_xa else "", ma_xa=ma_xa,
        tinh=danh_muc.ten_day_du("moi", ma_tinh) if ma_tinh else "", ma_tinh=ma_tinh,
        canh_bao=list(dict.fromkeys(warnings)), phan_chua_phan_loai=dia_chi_sach.phan_chua_phan_loai,
        dau_vet=list(dia_chi_sach.dau_vet), thong_ke=dict(dia_chi_sach.thong_ke)
    )
    result.dia_chi_chuan = _chuan_chuoi_dia_chi(result)
    if not ma_xa:
        result.xa_moi_ung_vien = [{"ma_xa": w, "ten": danh_muc.ten_day_du("moi", w),
                                   "ma_tinh": danh_muc.lay("moi", w).ma_cha} for w in sorted(all_wards)]
    result.thong_ke["so_ket_qua_dich_gan_nhat"] = len(outcomes)
    return result
