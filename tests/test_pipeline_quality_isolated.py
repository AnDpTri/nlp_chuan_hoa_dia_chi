"""Hồi quy cho nhánh pipeline-quality; chỉ dùng fixture độc lập, không đọc test cuối."""
import unittest
from types import SimpleNamespace

from src.chuan_hoa import _token_trong_span_ky_tu
from src.dinh_dang import dinh_dang_span
from src.tien_xu_ly import token_co_vi_tri


def fmt(text, field, default):
    tokens = [t.chu for t in token_co_vi_tri(text)]
    return dinh_dang_span(tokens, field, tien_to_mac_dinh=default)[0]


class TestHopDongDinhDang(unittest.TestCase):
    def test_so_nha_co_tien_to_ro_rang_khong_bi_xoa(self):
        self.assertEqual(fmt("Số 12B", "so_nha", False), "Số 12B")
        self.assertEqual(fmt("số 12", "so_nha", False), "Số 12")

    def test_khong_tu_them_tien_to_khi_da_tat(self):
        self.assertEqual(fmt("12B", "so_nha", False), "12B")
        self.assertEqual(fmt("12B", "so_nha", True), "Số 12B")

    def test_giu_tien_to_duong_khi_tat_tu_dong(self):
        self.assertEqual(fmt("Đường Lê Lợi", "duong", False), "Đường Lê Lợi")
        self.assertEqual(fmt("Lê Lợi", "duong", False), "Lê Lợi")

    def test_so_nha_nam_sau_chu_so_khong_duoc_loai(self):
        self.assertEqual(fmt("Số 12345", "so_nha", True), "Số 12345")
        self.assertEqual(fmt("123456", "so_nha", False), "123456")
        self.assertEqual(fmt("12 / 12345", "so_nha", False), "12/12345")
        self.assertEqual(fmt("12345 - 12346", "so_nha", True), "Số 12345-12346")


class TestCanChinhNeural(unittest.TestCase):
    def test_span_char_offset_khong_phu_thuoc_chi_so_token(self):
        # CNN tách 3 token, ViDeBERTa có thể tách 5 token.
        context = SimpleNamespace(labels=["O"] * 5, char_spans=[("duong", 6, 18)])
        tokens = [SimpleNamespace(bat_dau=0, ket_thuc=5),
                  SimpleNamespace(bat_dau=6, ket_thuc=10),
                  SimpleNamespace(bat_dau=11, ket_thuc=18)]
        self.assertFalse(_token_trong_span_ky_tu(context, tokens[0], "duong"))
        self.assertTrue(_token_trong_span_ky_tu(context, tokens[1], "duong"))
        self.assertTrue(_token_trong_span_ky_tu(context, tokens[2], "duong"))
        self.assertFalse(_token_trong_span_ky_tu(context, tokens[2], "xa"))

    def test_khong_lay_span_chi_phu_mot_phan_token(self):
        context = SimpleNamespace(char_spans=[("duong", 7, 12)])
        token = SimpleNamespace(bat_dau=6, ket_thuc=12)
        self.assertFalse(_token_trong_span_ky_tu(context, token, "duong"))


class TestXaBiChia(unittest.TestCase):
    class FakeCatalog:
        def __init__(self, targets):
            self.targets = targets
            self.huyen_thanh_dac_khu = {}

        def dich_tinh(self, cay, ma):
            return {"79"}

        def dich_xa(self, cay, ma):
            return set(self.targets)

        def lay(self, cay, ma):
            # Một xã mới cố tình trùng tên xã cũ.
            return SimpleNamespace(cap="xa", ten=("An Bình" if ma in ("old", "new_same") else "Tân An"),
                                   ma_cha="79")

    def test_trung_ten_nhung_bi_chia_thi_khong_tu_chon(self):
        from src.chuyen_doi import sang_cay_moi
        from src.kieu_du_lieu import DuongDi, UngVien
        u = UngVien(0, 2, "old", "cu", "chinh_xac", 1.0, cap="xa")
        route = DuongDi("cu", [u], 1.0)
        ward, province, warn = sang_cay_moi(route, {"duong": "Đường A"},
                                            self.FakeCatalog(("new_same", "new_other")))
        self.assertEqual((ward, province), ("", "79"))
        self.assertIn("xa_bi_chia", warn)

    def test_chuyen_doi_duy_nhat_van_duoc_chon(self):
        from src.chuyen_doi import sang_cay_moi
        from src.kieu_du_lieu import DuongDi, UngVien
        route = DuongDi("cu", [UngVien(0, 1, "old", "cu", "chinh_xac", 1.0, cap="xa")], 1.0)
        ward, province, warn = sang_cay_moi(route, {}, self.FakeCatalog(("new_same",)))
        self.assertEqual((ward, province), ("new_same", "79"))
        self.assertNotIn("xa_bi_chia", warn)


class TestChanDoanDev(unittest.TestCase):
    def test_phan_biet_mat_dau_voi_sai_noi_dung(self):
        from danh_gia.phan_tich_loi_dev_co_lap import problem
        ref = {"duong": "Đường Giải Phóng"}
        pred = {"duong": "Đường Giai Phong"}
        self.assertEqual(problem(ref, pred, "duong"), "chi_khac_dau_khoang_trang")
        self.assertEqual(problem(ref, {"duong": "Đường Lê Lợi"}, "duong"), "khac_noi_dung")

    def test_nhan_rong_va_du_doan_rong_duoc_phan_biet(self):
        from danh_gia.phan_tich_loi_dev_co_lap import problem
        self.assertEqual(problem({"ma_xa": ""}, {"ma_xa": "01234"}, "ma_xa"),
                         "nhan_rong_du_doan_co")
        self.assertEqual(problem({"ma_xa": "01234"}, {"ma_xa": ""}, "ma_xa"),
                         "bo_sot_truong")


class TestSchemaDanhGia(unittest.TestCase):
    def test_sau_truong_tho_khac_chuoi_chuan(self):
        from danh_gia.do_kiem_tra_test400 import aggregate_metrics
        ref = dict(so_nha="181", ngo_ngach_hem="", thon_xom="", duong="Tây Thạnh",
                   ma_xa="27013", ma_tinh="79", xa_phuong="Phường Tây Thạnh",
                   tinh="Thành phố Hồ Chí Minh",
                   dia_chi_chuan="Số 181, Đường Tây Thạnh, Phường Tây Thạnh, Thành phố Hồ Chí Minh")
        pred = {**ref, "so_nha": "Số 181", "duong": "Đường Tây Thạnh"}
        metrics = aggregate_metrics([(ref, pred)])
        self.assertEqual(metrics["dung_toan_bo_6_truong"], 0)
        self.assertEqual(metrics["tung_truong"]["dia_chi_chuan"]["dung"], 1)
        pred_raw = {**ref}
        self.assertEqual(aggregate_metrics([(ref, pred_raw)])["dung_toan_bo_6_truong"], 1)


if __name__ == "__main__":
    unittest.main()
