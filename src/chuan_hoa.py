"""Ghép cả pipeline: chuan_hoa(chuoi) -> KetQua."""

from .danh_muc import DanhMuc
from .kieu_du_lieu import KetQua
from .tien_xu_ly import tach_token, bo_dau
from .tim_kiem import dung_trie, sinh_ung_vien
from .giai_ma import tim_duong_di
from .tach_phan_con import tach
from .chuyen_doi import sang_cay_moi
from dataclasses import asdict
import csv
import re
from pathlib import Path


class BoChuanHoa:
    def __init__(self, danh_muc: DanhMuc | None = None, fuzzy: bool = True):
        self.danh_muc = danh_muc or DanhMuc()
        self.trie = dung_trie(self.danh_muc)
        self.fuzzy = fuzzy
        self.streets = {}
        file = Path(__file__).resolve().parents[1] / "data/runtime/streets.csv"
        if file.exists():
            with file.open(encoding="utf-8-sig", newline="") as f:
                self.streets = {
                    r["khong_dau"]: r["ten_duong"] for r in csv.DictReader(f)
                }

    def chuan_hoa(self, chuoi: str) -> KetQua:
        tokens = tach_token(chuoi)
        if len(tokens) > 120:
            raise ValueError("Địa chỉ tối đa 120 token; hãy kiểm tra đầu vào.")
        result = KetQua()
        if not tokens:
            result.canh_bao = ["dia_chi_rong", "thieu_xa", "thieu_tinh"]
            return result
        candidates = sinh_ung_vien(tokens, self.trie, self.fuzzy)
        paths = tim_duong_di(candidates, len(tokens), self.danh_muc, beam=12)
        used = set()
        if paths:
            best = paths[0]
            used = {i for c in best.ung_vien for i in range(c.bat_dau, c.ket_thuc)}
            parts = tach(tokens, used)
            ward, province, warnings = sang_cay_moi(best, parts, self.danh_muc)
            # Không biến một tỉnh/quận mâu thuẫn thành tên đường trong phần dư.
            for candidate in candidates:
                span = set(range(candidate.bat_dau, candidate.ket_thuc))
                unit = self.danh_muc.lay(candidate.cay, candidate.ma)
                if span & used or unit.cap not in {"tinh", "huyen"}:
                    continue
                root = self.danh_muc.to_tien(unit)[-1]
                target = (
                    self.danh_muc.tinh_cu_moi.get(root.ma, "")
                    if root.cay == "cu"
                    else root.ma
                )
                if target and target != province:
                    warnings.append("mau_thuan_hanh_chinh")
                    used.update(span)
            parts = tach(tokens, used)
            result.ma_xa = ward
            result.ma_tinh = province
            result.canh_bao.extend(warnings)
            if ward:
                result.xa_phuong = self.danh_muc.ten_day_du("moi", ward)
            if province:
                result.tinh = self.danh_muc.ten_day_du("moi", province)
            results = {(ward, province)}
            depth = min(
                {"xa": 0, "huyen": 1, "tinh": 2}[self.danh_muc.lay(c.cay, c.ma).cap]
                for c in best.ung_vien
            )
            for other in paths[1:]:
                if best.diem - other.diem > 1:
                    break
                other_depth = min(
                    {"xa": 0, "huyen": 1, "tinh": 2}[self.danh_muc.lay(c.cay, c.ma).cap]
                    for c in other.ung_vien
                )
                if other_depth != depth:
                    continue
                w, p, _ = sang_cay_moi(other, parts, self.danh_muc)
                results.add((w, p))
            if len(results) > 1:
                result.canh_bao.append("mo_ho_hanh_chinh")
                for w, p in sorted(results):
                    if w:
                        result.ung_vien_xa.append(
                            {
                                "ma_xa": w,
                                "xa_phuong": self.danh_muc.ten_day_du("moi", w),
                                "ma_tinh": p,
                                "tinh": self.danh_muc.ten_day_du("moi", p),
                            }
                        )
            if not any(
                self.danh_muc.lay(c.cay, c.ma).cap == "tinh" for c in best.ung_vien
            ):
                result.canh_bao.append("thieu_tinh_dau_vao")
            for c in best.ung_vien:
                result.dau_vet.append(
                    dict(asdict(c), chuoi=" ".join(tokens[c.bat_dau : c.ket_thuc]))
                )
                u = self.danh_muc.lay(c.cay, c.ma)
                if u.cap == "xa" and u.cay == "cu" and "xa_bi_chia" in warnings:
                    for ma, _ in self.danh_muc.doi_chieu[u.ma]:
                        x = self.danh_muc.lay("moi", ma)
                        option = {
                            "ma_xa": ma,
                            "xa_phuong": self.danh_muc.ten_day_du("moi", ma),
                            "ma_tinh": x.ma_cha,
                            "tinh": self.danh_muc.ten_day_du("moi", x.ma_cha),
                        }
                        if option not in result.ung_vien_xa:
                            result.ung_vien_xa.append(option)
                if c.kieu_khop == "sai_chinh_ta":
                    result.canh_bao.append("sua_chinh_ta")
        else:
            parts = tach(tokens, set())
            result.canh_bao.extend(["thieu_xa", "thieu_tinh"])
        for field, value in parts.items():
            setattr(result, field, value)
        if result.duong:
            name = re.sub(r"^(Đường|Phố)\s+", "", result.duong)
            canonical = self.streets.get(bo_dau(name))
            if canonical:
                result.dau_vet.append(
                    {"buoc": "tu_dien_duong", "dau_vao": name, "dau_ra": canonical}
                )
                result.duong = "Đường " + canonical
        # Tên riêng chưa có dấu phải được giữ dấu vết, không bịa tên ngoài danh mục.
        for key in ["duong", "thon_xom"]:
            value = re.sub(
                r"^(Đường|Phố|Thôn|Xóm|Ấp|Bản|Khu phố)\s+", "", getattr(result, key)
            )
            if (
                value
                and any(c.isalpha() for c in value)
                and bo_dau(value) == value.lower()
            ):
                result.canh_bao.append("phan_con_chua_khoi_phuc_dau")
        result.canh_bao = list(dict.fromkeys(result.canh_bao))
        result.dia_chi_chuan = ", ".join(
            v
            for v in [
                ("Số " + result.so_nha) if result.so_nha else "",
                result.ngo_ngach_hem,
                result.thon_xom,
                result.duong,
                result.xa_phuong,
                result.tinh,
            ]
            if v
        )
        return result
