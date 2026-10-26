"""Bước 3: ghép ứng viên thành đường đi hợp lệ trên cây hành chính.

Tạo đường đi từ từng ứng viên, ghép tổ tiên tương thích và giữ top-k.
Chạy trên cả cây cũ và cây mới; chưa dùng ranker học máy.
"""

from .danh_muc import DanhMuc
from .kieu_du_lieu import DuongDi, UngVien


def cham_diem(duong_di: DuongDi, so_token: int) -> float:
    """Hàm chấm điểm. Bản đầu đặt trọng số bằng tay, sau thay bằng mô hình."""
    covered = set(i for c in duong_di.ung_vien for i in range(c.bat_dau, c.ket_thuc))
    return sum(c.diem for c in duong_di.ung_vien) + len(covered) / max(so_token, 1)


def tim_duong_di(
    ung_vien: list[UngVien], so_token: int, danh_muc: DanhMuc, beam: int = 5
) -> list[DuongDi]:
    """Trả về các đường đi hợp lệ, sắp xếp theo điểm giảm dần."""
    paths = []

    def overlap(a, b):
        return a.bat_dau < b.ket_thuc and b.bat_dau < a.ket_thuc

    for leaf in ung_vien:
        unit = danh_muc.lay(leaf.cay, leaf.ma)
        ancestors = danh_muc.to_tien(unit)
        chain = {(u.cay, u.ma) for u in ancestors}
        selected = [leaf]
        for level in ["huyen", "tinh"]:
            if unit.cap == level:
                continue
            matches = [
                c
                for c in ung_vien
                if (c.cay, c.ma) in chain
                and danh_muc.lay(c.cay, c.ma).cap == level
                and not any(overlap(c, v) for v in selected)
            ]
            if level == "tinh" and not matches:
                root = ancestors[-1]
                target = (
                    danh_muc.tinh_cu_moi.get(root.ma) if root.cay == "cu" else root.ma
                )
                matches = [
                    c
                    for c in ung_vien
                    if danh_muc.lay(c.cay, c.ma).cap == "tinh"
                    and (danh_muc.tinh_cu_moi.get(c.ma) if c.cay == "cu" else c.ma)
                    == target
                    and not any(overlap(c, v) for v in selected)
                ]
            if matches:
                selected.append(max(matches, key=lambda c: c.diem))
        path = DuongDi(leaf.cay, selected, 0)
        path.diem = cham_diem(path, so_token) + (
            {"xa": 2, "huyen": 1, "tinh": 0}[unit.cap]
        )
        paths.append(path)
    unique = {}
    for path in paths:
        key = tuple(sorted((u.bat_dau, u.ket_thuc, u.cay, u.ma) for u in path.ung_vien))
        if key not in unique or path.diem > unique[key].diem:
            unique[key] = path
    return sorted(unique.values(), key=lambda p: p.diem, reverse=True)[:beam]
