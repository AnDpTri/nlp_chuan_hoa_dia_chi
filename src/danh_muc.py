"""Nạp danh mục hành chính từ data/clean và dựng hai cây (cũ, mới).

Nạp một lần lúc khởi động. Mọi liên kết dùng mã, không dùng tên.
"""

from pathlib import Path
import csv
import hashlib
from collections import defaultdict

from .kieu_du_lieu import DonVi

THU_MUC_DU_LIEU = Path(__file__).resolve().parent.parent / "data" / "clean"
TEP_TEN_CU = Path(__file__).resolve().parent.parent / "data" / "ten_cu" / "ten_cu_alias.csv"


class DanhMuc:
    """Hai cây hành chính và cạnh đối chiếu từ xã cũ sang xã mới."""

    def __init__(self, thu_muc: Path = THU_MUC_DU_LIEU, tep_ten_cu: Path | None = TEP_TEN_CU):
        self.don_vi: dict[tuple[str, str], DonVi] = {}  # (cay, ma) -> DonVi
        self.con: dict[tuple[str, str], list[str]] = {}  # (cay, ma cha) -> mã con
        self.doi_chieu: dict[str, list[tuple[str, str]]] = {}  # mã xã cũ -> [(mã xã mới, kiểu)]
        self.tinh_cu_moi: dict[str, set[str]] = defaultdict(set)
        self.huyen_cua_xa_moi: dict[str, set[str]] = defaultdict(set)
        self.tinh_cu_cua_xa_moi: dict[str, set[str]] = defaultdict(set)
        self.ma_bam: dict[str, str] = {}
        self.huyen_thanh_dac_khu: dict[str, set[str]] = defaultdict(set)
        # Tên/bí danh cũ của huyện, xã (đã nhập, đổi tên trước khi danh mục cũ được chụp).
        # Không nằm trong ma_bam: không đổi cây, chỉ thêm khóa tra cứu vào đơn vị đã có.
        self.ten_cu: list[tuple[str, str, str]] = []  # (cấp, mã cũ, khóa không dấu)
        self._nap(thu_muc)
        if tep_ten_cu and Path(tep_ten_cu).exists():
            self._nap_ten_cu(Path(tep_ten_cu))

    def _nap_ten_cu(self, tep: Path) -> None:
        with tep.open(encoding="utf-8-sig", newline="") as f:
            for r in csv.DictReader(f):
                if ("cu", r["ma_cu"]) in self.don_vi:
                    self.ten_cu.append((r["cap"], r["ma_cu"], r["khoa_alias"]))

    def _nap(self, thu_muc: Path) -> None:
        def doc(ten):
            p = Path(thu_muc) / ten
            self.ma_bam[ten] = hashlib.sha256(p.read_bytes()).hexdigest()
            with p.open(encoding="utf-8-sig", newline="") as f:
                return list(csv.DictReader(f))

        def them(cay, cap, ma, loai, ten, cha=None):
            dv = DonVi(ma, cap, loai, ten, cha, cay)
            key = (cay, ma)
            if key in self.don_vi:
                if self.don_vi[key] != dv:
                    raise ValueError(f"Mã trùng, khác nội dung: {key}")
                return
            self.don_vi[key] = dv
            if cha:
                self.con.setdefault((cay, cha), []).append(ma)

        for cay, ten in [("cu", "cu_tinh.csv"), ("moi", "moi_tinh.csv")]:
            for r in doc(ten):
                them(cay, "tinh", r["ma_tinh"], r["loai_tinh"], r["ten_tinh"])
        for r in doc("cu_huyen.csv"):
            them("cu", "huyen", r["ma_huyen"], r["loai_huyen"], r["ten_huyen"], r["ma_tinh"])
        for r in doc("cu_tinh_huyen_xa.csv"):
            them("cu", "xa", r["ma_xa"], r["loai_xa"], r["ten_xa"], r["ma_huyen"])
        for r in doc("moi_tinh_xa.csv"):
            them("moi", "xa", r["ma_xa"], r["loai_xa"], r["ten_xa"], r["ma_tinh"])
        for r in doc("doi_chieu_xa_cu_moi.csv"):
            cu, moi = r["ma_xa_cu"], r["ma_xa_moi"]
            self.lay("moi", moi)
            if cu:
                self.lay("cu", cu)
                edge = (moi, r["ghi_chu"])
                if edge not in self.doi_chieu.setdefault(cu, []):
                    self.doi_chieu[cu].append(edge)
            elif "toàn bộ huyện" in r["ghi_chu"].casefold():
                # Dòng không có xã nguồn chỉ ánh xạ cả huyện khi bảng nói rõ.
                self.huyen_thanh_dac_khu[r["ma_huyen_cu"]].add(moi)
            self.tinh_cu_moi[r["ma_tinh_cu"]].add(r["ma_tinh_moi"])
            self.huyen_cua_xa_moi[moi].add(r["ma_huyen_cu"])
            self.tinh_cu_cua_xa_moi[moi].add(r["ma_tinh_cu"])
        # Cache nguồn/đích theo đơn vị, không đọc file trong từng truy vấn.
        self._dich_xa = {}
        self._dich_tinh = {}
        for key, dv in self.don_vi.items():
            if dv.cap == "xa":
                wards = {dv.ma} if dv.cay == "moi" else {x[0] for x in self.doi_chieu.get(dv.ma, [])}
                self._dich_xa[key] = frozenset(wards)
                self._dich_tinh[key] = frozenset(self.lay("moi", x).ma_cha for x in wards)
            elif dv.cap == "tinh":
                self._dich_tinh[key] = frozenset({dv.ma} if dv.cay == "moi" else self.tinh_cu_moi[dv.ma])
            else:
                self._dich_tinh[key] = frozenset(self.tinh_cu_moi[dv.ma_cha])
                if dv.ma in self.huyen_thanh_dac_khu:
                    self._dich_xa[key] = frozenset(self.huyen_thanh_dac_khu[dv.ma])

    def lay(self, cay: str, ma: str) -> DonVi:
        return self.don_vi[cay, ma]

    def cac_con(self, cay: str, ma: str) -> list[DonVi]:
        return [self.lay(cay, x) for x in self.con.get((cay, ma), [])]

    def dich_xa(self, cay: str, ma: str) -> frozenset[str]:
        return self._dich_xa.get((cay, ma), frozenset())

    def dich_tinh(self, cay: str, ma: str) -> frozenset[str]:
        return self._dich_tinh[cay, ma]

    def tuong_thich(self, a: DonVi, b: DonVi) -> bool:
        if a.cay == b.cay:
            if a.cap == b.cap:
                return a.ma == b.ma
            # Quan hệ nguồn phải đúng ngay cả khi các đơn vị cùng đích mới.
            for child, parent in [(a, b), (b, a)]:
                cha = child.ma_cha
                while cha:
                    if cha == parent.ma:
                        return True
                    cha = self.lay(child.cay, cha).ma_cha
            return False
        cu, moi = (a, b) if a.cay == "cu" else (b, a)
        if moi.cap == "tinh":
            return moi.ma in self.dich_tinh("cu", cu.ma)
        if cu.cap == "xa":
            return moi.ma in self.dich_xa("cu", cu.ma)
        if cu.cap == "huyen":
            return cu.ma in self.huyen_cua_xa_moi.get(moi.ma, set())
        return cu.ma in self.tinh_cu_cua_xa_moi.get(moi.ma, set())

    def ten_day_du(self, cay: str, ma: str) -> str:
        dv = self.lay(cay, ma)
        # Một số nguồn đã chứa loại trong trường tên.
        return dv.ten if dv.ten.casefold().startswith(dv.loai.casefold() + " ") else f"{dv.loai} {dv.ten}"
