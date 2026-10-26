"""Hai thư viện mốc offline, không thay đổi pipeline hay danh mục của dự án."""

from dataclasses import asdict
from src.chuan_hoa import BoChuanHoa
from src.tien_xu_ly import bo_dau


def adapters():
    import vietnamadminunits as vau
    from vietnam_address_converter import create_converter

    converter = create_converter()
    model = BoChuanHoa()
    exact = BoChuanHoa(fuzzy=False)
    # Thư viện converter dùng mã nội bộ, không phải mã hành chính đã ghim.
    # Chỉ chuyển định dạng qua tên chính thức + cha; không sửa quyết định nhận diện.
    catalogue = model.danh_muc
    province_names = {
        bo_dau(u.ten): u.ma
        for u in catalogue.don_vi.values()
        if u.cay == "moi" and u.cap == "tinh"
    }
    ward_names = {}
    for u in catalogue.don_vi.values():
        if u.cay == "moi" and u.cap == "xa":
            ward_names.setdefault((u.ma_cha, bo_dau(u.loai + " " + u.ten)), []).append(
                u.ma
            )

    def code(value, width):
        return str(value).zfill(width) if value is not None and str(value) else ""

    def admin(text):
        # Dùng chế độ tự nhận/convert cũ của thư viện; nếu không có xã thì thử parser mới.
        result = vau.convert_address(text)
        if not result.ward_code:
            result = vau.parse_address(text)
        return {
            "ma_xa": code(result.ward_code, 5),
            "ma_tinh": code(result.province_code, 2),
        }

    def converter_adapter(text):
        result = converter.auto_convert_address(text)
        new = result.get("converted_new") or {}
        province = province_names.get(
            bo_dau((new.get("province") or {}).get("name") or ""), ""
        )
        ward = (new.get("ward") or {}).get("name_with_type") or ""
        matches = ward_names.get((province, bo_dau(ward)), [])
        return {"ma_xa": matches[0] if len(matches) == 1 else "", "ma_tinh": province}

    return {
        "pipeline": lambda t: asdict(model.chuan_hoa(t)),
        "ablation_no_fuzzy": lambda t: asdict(exact.chuan_hoa(t)),
        "vietnamadminunits_1.0.4": admin,
        "vietnam_address_converter_1.0.5": converter_adapter,
    }
