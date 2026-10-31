"""Kiểm thử độc lập ranh giới thôn/xóm theo đặc tả kỹ thuật.

Kiểm tra trực tiếp API NguCanhCRF.tach(set()), không nạp mô hình, không cần pycrfsuite.
Sử dụng tokenizer thực tế (src.tien_xu_ly.tach_token) và BIO labels tự dựng.
"""

import unittest
from src.crf_chi_tiet import NguCanhCRF, tao_nhan
from src.tien_xu_ly import tach_token


class TestThonXomBoundary(unittest.TestCase):
    """Bộ kiểm thử độc lập cho ranh giới và tiền tố thôn/xóm."""

    def _tao_ngu_canh(self, text, span_field=None, span_range=None):
        """Fixture dựng NguCanhCRF từ text với token index thực tế."""
        tokens = tach_token(text)
        n = len(tokens)
        if span_field and span_range:
            a, b = span_range
            labels = tao_nhan(n, [(span_field, a, b)])
            p_o = [0.0] * n
        elif span_field:
            labels = tao_nhan(n, [(span_field, 0, n)])
            p_o = [0.0] * n
        else:
            labels = ['O'] * n
            p_o = [1.0] * n
        self.assertEqual(len(labels), n, f"Độ dài labels ({len(labels)}) khác tokens ({n})")
        return tokens, NguCanhCRF(tokens, labels, p_o)

    def test_00_xac_minh_module_runtime(self):
        """Xác minh NguCanhCRF import qua wrapper chạm đúng module runtime."""
        self.assertEqual(NguCanhCRF.__module__, "src.tien_xu_ly.crf_chi_tiet")

    def test_01_crf_span_bao_trum_xom_5(self):
        """Ca 1: CRF span thon_xom bao trùm toàn chuỗi phải thu ngắn về 'Xóm 5'."""
        text = "xóm 5 xã mỹ hưng huyện mỹ lộc tỉnh nam định"
        tokens, ctx = self._tao_ngu_canh(text, span_field="thon_xom")
        detail, spans, unknown, _ = ctx.tach(set())
        self.assertEqual(detail["thon_xom"], "Xóm 5")
        self.assertTrue(any(s["truong"] == "thon_xom" and s["bat_dau"] == 0 and s["ket_thuc"] == 2
                            and s["gia_tri"] == "Xóm 5" for s in spans))

    def test_02_fallback_all_o_xom_5(self):
        """Ca 2: Fallback all-O với cùng địa chỉ phải chỉ lấy 'Xóm 5'."""
        text = "xóm 5 xã mỹ hưng huyện mỹ lộc tỉnh nam định"
        tokens, ctx = self._tao_ngu_canh(text, span_field=None)
        detail, spans, unknown, _ = ctx.tach(set())
        self.assertEqual(detail["thon_xom"], "Xóm 5")
        self.assertTrue(any(s["truong"] == "thon_xom" and s["bat_dau"] == 0 and s["ket_thuc"] == 2
                            and s["gia_tri"] == "Xóm 5" for s in spans))

    def test_03_thon_3_xa_hoang_loc(self):
        """Ca 3: 'Thôn 3 xã Hoằng Lộc huyện Hoằng Hóa tỉnh Thanh Hóa' -> 'Thôn 3'."""
        text = "Thôn 3 xã Hoằng Lộc huyện Hoằng Hóa tỉnh Thanh Hóa"
        # 3a: CRF span bao trùm
        _, ctx_crf = self._tao_ngu_canh(text, span_field="thon_xom")
        det_crf, _, _, _ = ctx_crf.tach(set())
        self.assertEqual(det_crf["thon_xom"], "Thôn 3")

        # 3b: Fallback all-O
        _, ctx_fb = self._tao_ngu_canh(text, span_field=None)
        det_fb, _, _, _ = ctx_fb.tach(set())
        self.assertEqual(det_fb["thon_xom"], "Thôn 3")

    def test_04_thon_dong_xa_nam_hong(self):
        """Ca 4: 'Thôn Đông xã Nam Hồng huyện Tiền Hải Thái Bình' -> 'Thôn Đông'."""
        text = "Thôn Đông xã Nam Hồng huyện Tiền Hải Thái Bình"
        # 4a: CRF span bao trùm
        _, ctx_crf = self._tao_ngu_canh(text, span_field="thon_xom")
        det_crf, _, _, _ = ctx_crf.tach(set())
        self.assertEqual(det_crf["thon_xom"], "Thôn Đông")

        # 4b: Fallback all-O
        _, ctx_fb = self._tao_ngu_canh(text, span_field=None)
        det_fb, _, _, _ = ctx_fb.tach(set())
        self.assertEqual(det_fb["thon_xom"], "Thôn Đông")

    def test_05_xom_khe_cat_xa_lam_dien(self):
        """Ca 5: 'Xóm Khe Cát Xã Lam Điền': giữ đủ tên thôn nhiều chữ, không lấy xã."""
        text = "Xóm Khe Cát Xã Lam Điền"
        # 5a: CRF span bao trùm
        _, ctx_crf = self._tao_ngu_canh(text, span_field="thon_xom")
        det_crf, spans_crf, _, _ = ctx_crf.tach(set())
        self.assertEqual(det_crf["thon_xom"], "Xóm Khe Cát")
        self.assertTrue(any(s["truong"] == "thon_xom" and s["bat_dau"] == 0 and s["ket_thuc"] == 3
                            for s in spans_crf))

        # 5b: Fallback all-O
        _, ctx_fb = self._tao_ngu_canh(text, span_field=None)
        det_fb, spans_fb, _, _ = ctx_fb.tach(set())
        self.assertEqual(det_fb["thon_xom"], "Xóm Khe Cát")
        self.assertTrue(any(s["truong"] == "thon_xom" and s["bat_dau"] == 0 and s["ket_thuc"] == 3
                            for s in spans_fb))

    def test_06_thon_phuong_nam_khong_cat_nham(self):
        """Ca 6: 'Thôn Phương Nam' và 'Thon Phuong Nam' không cắt nhầm chữ Phương/Phuong."""
        # 6a: Có dấu
        text_dau = "Thôn Phương Nam"
        _, ctx_dau = self._tao_ngu_canh(text_dau, span_field="thon_xom")
        det_dau, _, _, _ = ctx_dau.tach(set())
        self.assertEqual(det_dau["thon_xom"], "Thôn Phương Nam")

        _, ctx_dau_fb = self._tao_ngu_canh(text_dau, span_field=None)
        det_dau_fb, _, _, _ = ctx_dau_fb.tach(set())
        self.assertEqual(det_dau_fb["thon_xom"], "Thôn Phương Nam")

        # 6b: Không dấu
        text_khong_dau = "Thon Phuong Nam"
        _, ctx_kd = self._tao_ngu_canh(text_khong_dau, span_field="thon_xom")
        det_kd, _, _, _ = ctx_kd.tach(set())
        self.assertEqual(det_kd["thon_xom"], "Thôn Phuong Nam")

        _, ctx_kd_fb = self._tao_ngu_canh(text_khong_dau, span_field=None)
        det_kd_fb, _, _, _ = ctx_kd_fb.tach(set())
        self.assertEqual(det_kd_fb["thon_xom"], "Thôn Phuong Nam")

    def test_07_xom_duong_moi_khong_coi_duong_la_tien_to_hanh_chinh(self):
        """Ca 7: 'Xóm Đường Mới': không coi 'Đường' là tiền tố làm đứt tên thôn."""
        text = "Xóm Đường Mới"
        # CRF span
        _, ctx_crf = self._tao_ngu_canh(text, span_field="thon_xom")
        det_crf, _, _, _ = ctx_crf.tach(set())
        self.assertEqual(det_crf["thon_xom"], "Xóm Đường Mới")
        self.assertEqual(det_crf["duong"], "")

        # Fallback all-O
        _, ctx_fb = self._tao_ngu_canh(text, span_field=None)
        det_fb, _, _, _ = ctx_fb.tach(set())
        self.assertEqual(det_fb["thon_xom"], "Xóm Đường Mới")
        self.assertEqual(det_fb["duong"], "")

    def test_08_khom_cau_den(self):
        """Ca 8: 'Khóm Cầu Đen': kiểm tra nhãn thon_xom cho tiền tố Khóm."""
        # 8a: Đứng độc lập
        text_doc_lap = "Khóm Cầu Đen"
        _, ctx_dl = self._tao_ngu_canh(text_doc_lap, span_field="thon_xom")
        det_dl, _, _, _ = ctx_dl.tach(set())
        self.assertEqual(det_dl["thon_xom"], "Khóm Cầu Đen")

        _, ctx_dl_fb = self._tao_ngu_canh(text_doc_lap, span_field=None)
        det_dl_fb, _, _, _ = ctx_dl_fb.tach(set())
        self.assertEqual(det_dl_fb["thon_xom"], "Khóm Cầu Đen")

        # 8b: Có đơn vị hành chính theo sau
        text_day_du = "Khóm Cầu Đen Phường 1 Thị xã Giá Rai"
        _, ctx_dd = self._tao_ngu_canh(text_day_du, span_field="thon_xom")
        det_dd, spans_dd, _, _ = ctx_dd.tach(set())
        self.assertEqual(det_dd["thon_xom"], "Khóm Cầu Đen")
        self.assertTrue(any(s["truong"] == "thon_xom" and s["bat_dau"] == 0 and s["ket_thuc"] == 3
                            for s in spans_dd))

        _, ctx_dd_fb = self._tao_ngu_canh(text_day_du, span_field=None)
        det_dd_fb, spans_dd_fb, _, _ = ctx_dd_fb.tach(set())
        self.assertEqual(det_dd_fb["thon_xom"], "Khóm Cầu Đen")
        self.assertTrue(any(s["truong"] == "thon_xom" and s["bat_dau"] == 0 and s["ket_thuc"] == 3
                            for s in spans_dd_fb))

    def test_09a_viet_tat_chuoi_thu_bac_x_h_t(self):
        """Ca 9a: Viết tắt chuỗi thứ bậc X., H., T.: phải dừng đúng trước X."""
        text = "Xóm 1 X. Mỹ Hưng H. Mỹ Lộc T. Nam Định"
        # 9a.1: CRF span bao trùm
        _, ctx_crf = self._tao_ngu_canh(text, span_field="thon_xom")
        det_crf, spans_crf, _, _ = ctx_crf.tach(set())
        self.assertEqual(det_crf["thon_xom"], "Xóm 1")
        self.assertTrue(any(s["truong"] == "thon_xom" and s["bat_dau"] == 0 and s["ket_thuc"] == 2
                            for s in spans_crf))

        # 9a.2: Fallback all-O
        _, ctx_fb = self._tao_ngu_canh(text, span_field=None)
        det_fb, spans_fb, _, _ = ctx_fb.tach(set())
        self.assertEqual(det_fb["thon_xom"], "Xóm 1")
        self.assertTrue(any(s["truong"] == "thon_xom" and s["bat_dau"] == 0 and s["ket_thuc"] == 2
                            for s in spans_fb))

    def test_09b_viet_tat_chuoi_thu_bac_p_q_tp(self):
        """Ca 9b: Viết tắt chuỗi thứ bậc P., Q., TP.: phải dừng đúng trước P."""
        text = "Khóm 2 P. 1 Q. Ninh Kiều TP. Cần Thơ"
        # 9b.1: CRF span bao trùm
        _, ctx_crf = self._tao_ngu_canh(text, span_field="thon_xom")
        det_crf, spans_crf, _, _ = ctx_crf.tach(set())
        self.assertEqual(det_crf["thon_xom"], "Khóm 2")
        self.assertTrue(any(s["truong"] == "thon_xom" and s["bat_dau"] == 0 and s["ket_thuc"] == 2
                            for s in spans_crf))

        # 9b.2: Fallback all-O
        _, ctx_fb = self._tao_ngu_canh(text, span_field=None)
        det_fb, spans_fb, _, _ = ctx_fb.tach(set())
        self.assertEqual(det_fb["thon_xom"], "Khóm 2")
        self.assertTrue(any(s["truong"] == "thon_xom" and s["bat_dau"] == 0 and s["ket_thuc"] == 2
                            for s in spans_fb))

    def test_09c_viet_tat_khong_du_bang_chung_thu_bac_ambiguity_abstain(self):
        """Ca 9c (Ambiguity): Chữ cái viết tắt không kèm chuỗi thứ bậc không được cắt đoán mò."""
        text = "Thôn X. Văn"
        # Khi span CRF gán toàn bộ tên 'Thôn X. Văn' và không có chuỗi thứ bậc tiếp nối,
        # hệ thống phải kiềm chế (abstain), không cắt nhầm thành 'Thôn'.
        _, ctx = self._tao_ngu_canh(text, span_field="thon_xom")
        detail, _, _, _ = ctx.tach(set())
        self.assertEqual(detail["thon_xom"], "Thôn X. Văn")

    def test_10a_dau_ngat_gach_ngang_va_cham_dung_rieng(self):
        """Ca 10a: Dấu -, –, — và dấu chấm đứng riêng làm dấu phân cách ranh giới."""
        for sep in ["-", "–", "—", "."]:
            text = f"Thôn 1 {sep} Xã Nam Hồng"
            with self.subTest(separator=sep):
                # CRF span bao trùm
                _, ctx_crf = self._tao_ngu_canh(text, span_field="thon_xom")
                det_crf, spans_crf, _, _ = ctx_crf.tach(set())
                self.assertEqual(det_crf["thon_xom"], "Thôn 1", f"CRF span thất bại tại dấu ngắt '{sep}'")
                self.assertTrue(any(s["truong"] == "thon_xom" and s["bat_dau"] == 0 and s["ket_thuc"] == 2
                                    for s in spans_crf))

                # Fallback all-O
                _, ctx_fb = self._tao_ngu_canh(text, span_field=None)
                det_fb, spans_fb, _, _ = ctx_fb.tach(set())
                self.assertEqual(det_fb["thon_xom"], "Thôn 1", f"Fallback all-O thất bại tại dấu ngắt '{sep}'")
                self.assertTrue(any(s["truong"] == "thon_xom" and s["bat_dau"] == 0 and s["ket_thuc"] == 2
                                    for s in spans_fb))

    def test_10b_dau_cham_viet_tat_khong_bi_tach_sai(self):
        """Ca 10b: Dấu chấm đi liền chữ viết tắt (X.) không bị tách làm dấu phân cách sai lệch."""
        text = "Xóm 1 X. Nam Hồng"
        tokens = tach_token(text)
        # Tokenizer phải tách 'X' và '.' thành 2 token liền kề theo quy tắc token_co_vi_tri
        self.assertEqual(tokens[:4], ["Xóm", "1", "X", "."])

    def test_11_khong_tac_dong_ngoai_thon_xom(self):
        """Ca 11: Bảo đảm các trường khác (duong, ngo_ngach_hem, so_nha) không bị tác động ngoài thon_xom."""
        # Trường duong
        text_duong = "Đường Giải Phóng Xã Nam Hồng"
        tokens_d = tach_token(text_duong)
        labels_d = tao_nhan(len(tokens_d), [("duong", 0, 3)])
        ctx_d = NguCanhCRF(tokens_d, labels_d, [0.0] * len(tokens_d))
        det_d, _, _, _ = ctx_d.tach(set())
        self.assertEqual(det_d["duong"], "Đường Giải Phóng")
        self.assertEqual(det_d["thon_xom"], "")

        # Trường ngo_ngach_hem và duong
        text_ngo = "Ngõ 10 Phố Huế"
        tokens_n = tach_token(text_ngo)
        labels_n = tao_nhan(len(tokens_n), [("ngo_ngach_hem", 0, 2), ("duong", 2, 4)])
        ctx_n = NguCanhCRF(tokens_n, labels_n, [0.0] * len(tokens_n))
        det_n, _, _, _ = ctx_n.tach(set())
        self.assertEqual(det_n["ngo_ngach_hem"], "Ngõ 10")
        self.assertEqual(det_n["duong"], "Phố Huế")
        self.assertEqual(det_n["thon_xom"], "")


if __name__ == "__main__":
    unittest.main()
