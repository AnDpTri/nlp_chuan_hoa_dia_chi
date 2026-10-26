"""Nạp danh mục hành chính từ data/clean và dựng hai cây (cũ, mới).

Nạp một lần lúc khởi động. Mọi liên kết dùng mã, không dùng tên.
"""

from pathlib import Path
import csv

from .kieu_du_lieu import DonVi

THU_MUC_DU_LIEU = Path(__file__).resolve().parent.parent / "data" / "clean"


class DanhMuc:
    """Hai cây hành chính và cạnh đối chiếu từ xã cũ sang xã mới."""

    def __init__(self, thu_muc: Path = THU_MUC_DU_LIEU):
        self.don_vi: dict[tuple[str, str], DonVi] = {}  # (cay, ma) -> DonVi
        self.con: dict[tuple[str, str], list[str]] = {}  # (cay, ma cha) -> mã con
        self.doi_chieu: dict[str, list[tuple[str, str]]] = (
            {}
        )  # mã xã cũ -> [(mã xã mới, kiểu)]
        self.tinh_cu_moi: dict[str, str] = {}
        self._nap(thu_muc)

    def _nap(self, thu_muc: Path) -> None:
        def rows(name):
            with (thu_muc / name).open(encoding="utf-8-sig", newline="") as f:
                return list(csv.DictReader(f))

        def add(unit):
            key = (unit.cay, unit.ma)
            if key in self.don_vi:
                raise ValueError(f"Mã trùng: {key}")
            self.don_vi[key] = unit
            if unit.ma_cha:
                self.con.setdefault((unit.cay, unit.ma_cha), []).append(unit.ma)

        # Chỉ áp dụng loại đơn vị đúng mốc bằng lớp runtime, không sửa dữ liệu clean đã ghim.
        overrides = {}
        runtime = thu_muc.parent / "runtime/loai_moc_2025.csv"
        if runtime.exists():
            with runtime.open(encoding="utf-8-sig", newline="") as f:
                overrides = {r["ma_tinh"]: r["loai_tinh"] for r in csv.DictReader(f)}
        for r in rows("moi_tinh.csv"):
            kind = overrides.get(r["ma_tinh"], r["loai_tinh"])
            add(DonVi(r["ma_tinh"], "tinh", kind, r["ten_tinh"], None, "moi"))
        for r in rows("moi_tinh_xa.csv"):
            add(DonVi(r["ma_xa"], "xa", r["loai_xa"], r["ten_xa"], r["ma_tinh"], "moi"))
        for r in rows("cu_tinh.csv"):
            add(DonVi(r["ma_tinh"], "tinh", r["loai_tinh"], r["ten_tinh"], None, "cu"))
        for r in rows("cu_huyen.csv"):
            add(
                DonVi(
                    r["ma_huyen"],
                    "huyen",
                    r["loai_huyen"],
                    r["ten_huyen"],
                    r["ma_tinh"],
                    "cu",
                )
            )
        for r in rows("cu_tinh_huyen_xa.csv"):
            add(DonVi(r["ma_xa"], "xa", r["loai_xa"], r["ten_xa"], r["ma_huyen"], "cu"))
        for r in rows("doi_chieu_xa_cu_moi.csv"):
            pair = (r["ma_xa_moi"], r["ghi_chu"])
            bucket = self.doi_chieu.setdefault(r["ma_xa_cu"], [])
            if pair not in bucket:
                bucket.append(pair)
            old, new = r["ma_tinh_cu"], r["ma_tinh_moi"]
            if old in self.tinh_cu_moi and self.tinh_cu_moi[old] != new:
                raise ValueError("Tỉnh cũ có nhiều tỉnh đích.")
            self.tinh_cu_moi[old] = new

    def lay(self, cay: str, ma: str) -> DonVi:
        return self.don_vi[(cay, ma)]

    def cac_con(self, cay: str, ma: str) -> list[DonVi]:
        return [self.lay(cay, c) for c in self.con.get((cay, ma), [])]

    def to_tien(self, unit):
        path = [unit]
        while path[-1].ma_cha:
            path.append(self.lay(unit.cay, path[-1].ma_cha))
        return path

    def ten_day_du(self, cay, ma):
        u = self.lay(cay, ma)
        return f"{u.loai} {u.ten}"
