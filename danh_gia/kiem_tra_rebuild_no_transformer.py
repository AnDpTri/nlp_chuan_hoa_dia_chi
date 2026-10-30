"""Kiểm chứng 4 fixture train từng được quy sai lợi ích cho Transformer.
Chỉ dùng ví dụ đã lưu trong báo cáo train; không đọc tập test cuối.
"""
from src.char_cnn import BoTachCharCNN
from src.chuan_hoa import BoChuanHoa
from src.chuan_ten_duong import TuDienDuong
from src.danh_muc import DanhMuc
from src.xep_hang import BoXepHang

CASES = (
    ("37/21ĐườngPhạmVănThuận, Phường Tam Hiệp, Tỉnh Đồng Nai", "Đường Phạm Văn Thuận"),
    ("47/9ĐườngTrầnHưngĐạo, Đặc khu Phú Quốc, Tỉnh An Giang", "Đường Trần Hưng Đạo"),
    ("35/6ĐườngChuVănAn, Phường Thuận Hóa, Thành phố Huế", "Đường Chu Văn An"),
    ("68/5AĐườngTrầnQuangKhải, Phường Tân Định, Thành phố Hồ Chí Minh", "Đường Trần Quang Khải"),
)


def main():
    dm = DanhMuc()
    cnn = BoTachCharCNN("mo_hinh/thu_nghiem/char_v2_01/char_cnn.pt", threads=1)
    ranker = BoXepHang("mo_hinh/thu_nghiem/char_v2_01/ranker.txt", cnn.ma_bam, dm.ma_bam)
    names = TuDienDuong("danh_gia/ket_qua/tu_dien_duong_v5.json")
    pipeline = BoChuanHoa(danh_muc=dm, bo_tach=cnn,
                          bo_xep_hang=ranker, tu_dien_duong=names,
                          bao_ve_duong=True, tien_to_mac_dinh=False)
    ok = 0
    for raw, expected in CASES:
        got = pipeline.chuan_hoa(raw).duong
        passed = got == expected
        ok += passed
        print(f"{'PASS' if passed else 'FAIL'}: {got!r}; expected={expected!r}", flush=True)
    print(f"{ok}/{len(CASES)} đúng, Transformer không được nạp", flush=True)
    if ok != len(CASES):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
