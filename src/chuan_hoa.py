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


def _tao_dau_vet(records, chuoi, a, b, **extra):
    return {"token_bat_dau": a, "token_ket_thuc": b, "ky_tu_bat_dau": records[a].bat_dau,
            "ky_tu_ket_thuc": records[b-1].ket_thuc,
            "doan_goc": chuoi[records[a].bat_dau:records[b-1].ket_thuc], **extra}


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
        self.danh_muc = self.bo_lam_sach.danh_muc
        self.beam = self.bo_lam_sach.beam
        self.bo_tach = self.bo_lam_sach.bo_tach
        self.bo_xep_hang = self.bo_lam_sach.bo_xep_hang
        self.tu_dien_duong = self.bo_lam_sach.tu_dien_duong
        self.bao_ve_duong = self.bo_lam_sach.bao_ve_duong
        self.tien_to_mac_dinh = self.bo_lam_sach.tien_to_mac_dinh
        self.tien_to_so_nha = self.bo_lam_sach.tien_to_so_nha
        self.tien_to_duong = self.bo_lam_sach.tien_to_duong
        self.PHIEN_BAN = self.bo_lam_sach.PHIEN_BAN
        self.trie = self.bo_lam_sach.trie
        self.tra_cuu_neural = self.bo_lam_sach.tra_cuu_neural

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
