"""Mặt tiền ghép hai module: chuan_hoa(chuoi) -> KetQua."""

from .danh_muc import DanhMuc
from .kieu_du_lieu import KetQua
from .tien_xu_ly.lam_sach import BoLamSach
from .chuyen_doi import chuyen_doi, chan_doan_chuyen_doi


def _token_trong_span_ky_tu(context, token, role):
    """Ghép hai bộ token khác nhau qua offset ký tự gốc, không dùng chỉ số token."""
    return any(r == role and a <= token.bat_dau and token.ket_thuc <= b
               for r, a, b in getattr(context, "char_spans", ()))


def _chuan_chuoi_dia_chi(res: KetQua) -> str:
    from .chuyen_doi.doi_chieu import _chuan_chuoi_dia_chi as _fn
    return _fn(res)


_THUOC_TINH_UY_QUYEN = frozenset((
    "danh_muc", "beam", "bo_tach", "bo_xep_hang", "tu_dien_duong", "bao_ve_duong",
    "tien_to_mac_dinh", "tien_to_so_nha", "tien_to_duong", "PHIEN_BAN", "trie", "tra_cuu_neural",
))


class BoChuanHoa:
    def __init__(self, danh_muc: DanhMuc | None = None, beam: int = 40, bo_tach=None, bo_xep_hang=None,
                 tu_dien_duong=None, bao_ve_duong=False, tien_to_mac_dinh: bool = True,
                 tien_to_so_nha: bool | None = None, tien_to_duong: bool | None = None):
        self.bo_lam_sach = BoLamSach(
            danh_muc=danh_muc, beam=beam, bo_tach=bo_tach, bo_xep_hang=bo_xep_hang,
            tu_dien_duong=tu_dien_duong, bao_ve_duong=bao_ve_duong,
            tien_to_mac_dinh=tien_to_mac_dinh, tien_to_so_nha=tien_to_so_nha,
            tien_to_duong=tien_to_duong
        )

    def __getattr__(self, ten):
        """Các thuộc tính cấu hình đọc thẳng từ bo_lam_sach (danh_muc, beam, trie, PHIEN_BAN...)."""
        if ten in _THUOC_TINH_UY_QUYEN:
            return getattr(self.bo_lam_sach, ten)
        raise AttributeError(ten)

    def tao_gia_thuyet(self, chuoi):
        return self.bo_lam_sach.tao_gia_thuyet(chuoi)

    def chuan_hoa(self, chuoi: str) -> KetQua:
        return self._chay(chuoi)[0]

    def chuan_hoa_chan_doan(self, chuoi: str) -> tuple[KetQua, dict]:
        """Như chuan_hoa, kèm bản ghi các bước trung gian của cả hai module (dùng cho nhật ký phát triển)."""
        from .tien_xu_ly.chan_doan import tao_chan_doan
        result, dia_chi_sach, noi_bo = self._chay(chuoi)
        chan_doan = {"tien_xu_ly": tao_chan_doan(dia_chi_sach, noi_bo, self.danh_muc),
                     "chuyen_doi": chan_doan_chuyen_doi(dia_chi_sach, self.danh_muc)}
        return result, chan_doan

    def _chay(self, chuoi: str):
        dia_chi_sach, noi_bo = self.bo_lam_sach.lam_sach_chi_tiet(chuoi)
        result = chuyen_doi(dia_chi_sach, self.danh_muc)
        return result, dia_chi_sach, noi_bo
