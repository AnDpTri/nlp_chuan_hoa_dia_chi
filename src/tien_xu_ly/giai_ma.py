"""Beam search trên các đoạn ứng viên; không khóa mốc cho toàn chuỗi.

Thứ tự xét ưu tiên bằng chứng cấp cao để giảm nhánh tên trùng, nhưng không
yêu cầu tỉnh/huyện hiện diện hay một thứ tự token cố định trong đầu vào.
"""

from collections import defaultdict

from ..danh_muc import DanhMuc
from ..kieu_du_lieu import DuongDi, UngVien


def nhom_bang_chung(ung_vien):
    """Các đoạn ghi rõ cấp hoặc tên tỉnh, chỉ dùng khớp không sửa ký tự."""
    groups = defaultdict(list)
    for u in ung_vien:
        if u.kieu_khop != "sai_chinh_ta" and (u.co_tien_to or u.cap == "tinh"):
            groups[u.bat_dau].append(u)
    out = []
    for us in groups.values():
        end = max(u.ket_thuc for u in us)
        out.append(tuple(u for u in us if u.ket_thuc == end))
    return out


def chi_phi_mau_thuan(path, groups, compatible):
    """Phạt việc bỏ bằng chứng có sẵn để chọn một đơn vị mâu thuẫn với nó.

    Thiếu một cấp không phải mâu thuẫn. Đây là ưu tiên mềm, vẫn cho phép
    giữ giả thuyết khi input tự mâu thuẫn và xuất cảnh báo.
    """
    cost = 0.0
    for group in groups:
        a, b = group[0].bat_dau, group[0].ket_thuc
        if any(max(a, u.bat_dau) < min(b, u.ket_thuc) for u in path.ung_vien):
            continue
        if path.ung_vien and not any(all(compatible(g, u) for u in path.ung_vien) for g in group):
            weights = {"tinh": 8.0, "huyen": 5.0, "xa": 2.0}
            cost += max(weights[g.cap] if g.co_tien_to else 4.0 for g in group)
    return cost


def cham_diem(duong_di: DuongDi, so_token: int) -> float:
    """Hàm chấm điểm. Bản đầu đặt trọng số bằng tay, sau thay bằng mô hình."""
    # Các cấp cùng tên ở hai mốc không được thưởng lặp chỉ vì nhiều cách tra.
    by_level = {}
    used = set()
    for u in duong_di.ung_vien:
        by_level[u.cap] = max(by_level.get(u.cap, 0.0), u.diem)
        used.update(range(u.bat_dau, u.ket_thuc))
    return sum(by_level.values()) + .12*len(used) + .4*max(0, len(by_level)-1)


def tim_duong_di(ung_vien: list[UngVien], so_token: int, danh_muc: DanhMuc, beam: int = 40) -> list[DuongDi]:
    """Trả về các đường đi hợp lệ, sắp xếp theo điểm giảm dần."""
    if beam < 1:
        raise ValueError("beam phải >= 1")
    evidence = nhom_bang_chung(ung_vien)
    pair_cache = {}
    def compatible(a, b):
        key = (a.cay, a.ma, b.cay, b.ma)
        if key not in pair_cache:
            pair_cache[key] = danh_muc.tuong_thich(danh_muc.lay(a.cay, a.ma), danh_muc.lay(b.cay, b.ma))
        return pair_cache[key]
    groups = defaultdict(list)
    for u in ung_vien:
        groups[u.bat_dau].append(u)
    order = {"tinh": 0, "huyen": 1, "xa": 2}
    groups = sorted(groups.values(), key=lambda us: (min(order[u.cap] for u in us), -max(u.diem for u in us), us[0].bat_dau))
    states = [DuongDi("", [], 0)]
    for options in groups:
        expanded = list(states)  # Luôn giữ phương án bỏ qua đoạn này.
        for state in states:
            for u in options:
                if any(max(u.bat_dau, v.bat_dau) < min(u.ket_thuc, v.ket_thuc) or
                       (u.cap == v.cap and u.cay == v.cay) or
                       not compatible(u, v) for v in state.ung_vien):
                    continue
                selected = state.ung_vien + [u]
                eras = {v.cay for v in selected}
                nxt = DuongDi(next(iter(eras)) if len(eras) == 1 else "tron", selected, 0)
                nxt.diem = cham_diem(nxt, so_token) - chi_phi_mau_thuan(nxt, evidence, compatible)
                expanded.append(nxt)
        unique = {}
        for s in expanded:
            key = tuple(sorted((u.bat_dau, u.ket_thuc, u.cay, u.ma) for u in s.ung_vien))
            unique[key] = s
        states = sorted(unique.values(), key=lambda s: (-s.diem, tuple((u.bat_dau, u.cay, u.ma) for u in s.ung_vien)))[:beam]
    # Nhánh không chọn hành chính vẫn đi qua parser chi tiết.
    if not any(not s.ung_vien for s in states):
        states.append(DuongDi("", [], 0))
    return states
