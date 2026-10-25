"""Nạp danh mục hành chính từ data/clean và dựng hai cây (cũ, mới).

Nạp một lần lúc khởi động. Mọi liên kết dùng mã, không dùng tên.
"""

from pathlib import Path

from .kieu_du_lieu import DonVi

THU_MUC_DU_LIEU = Path(__file__).resolve().parent.parent / "data" / "clean"


class DanhMuc:
    """Hai cây hành chính và cạnh đối chiếu từ xã cũ sang xã mới."""

    def __init__(self, thu_muc: Path = THU_MUC_DU_LIEU):
        self.don_vi: dict[tuple[str, str], DonVi] = {}  # (cay, ma) -> DonVi
        self.con: dict[tuple[str, str], list[str]] = {}  # (cay, ma cha) -> mã con
        self.doi_chieu: dict[str, list[tuple[str, str]]] = {}  # mã xã cũ -> [(mã xã mới, kiểu)]
        self._nap(thu_muc)

    def _nap(self, thu_muc: Path) -> None:
        raise NotImplementedError

    def lay(self, cay: str, ma: str) -> DonVi:
        raise NotImplementedError

    def cac_con(self, cay: str, ma: str) -> list[DonVi]:
        raise NotImplementedError
