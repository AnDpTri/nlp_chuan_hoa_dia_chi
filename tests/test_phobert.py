"""Unit tests cho adapter PhoBERT (src.phobert).

Được chạy bởi gate nghiệm thu luồng P.
Sử dụng biến môi trường PHOBERT_MODEL_DIR. Nếu thiếu biến thì skipTest.
"""

import importlib.util
import os
from pathlib import Path
import unicodedata
import unittest

import torch

from src.nhan import TAGS
from src.phobert import BoTachPhoBERT, encode_ids, segment_with_map
from src.tien_xu_ly import nfc_offsets

MODEL_DIR = os.environ.get("PHOBERT_MODEL_DIR")


class TestPhoBERTAdapter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not MODEL_DIR or not Path(MODEL_DIR).exists():
            raise unittest.SkipTest("Thiếu biến môi trường PHOBERT_MODEL_DIR hoặc thư mục không tồn tại")
        cls.model_dir = Path(MODEL_DIR)
        cls.adapter = BoTachPhoBERT(str(cls.model_dir), threads=1)

        # Nạp segment_with_map tham chiếu từ train.py
        import sys
        root = Path(__file__).resolve().parents[1]
        colab_dir = str(root / "colab" / "phobert_v1")
        if colab_dir not in sys.path:
            sys.path.insert(0, colab_dir)
        train_path = root / "colab" / "phobert_v1" / "train.py"
        spec = importlib.util.spec_from_file_location("train_ref", train_path)
        cls.train_ref = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.train_ref)

    def test_segment_with_map_khop_train_py(self):
        """(1) segment_with_map khớp train.py trên một tập câu, gồm câu làm train.py raise ValueError."""
        sentences = [
            "Số 12, Phố Hàng Bài, Hà Nội",
            "12 Trần Phú, Hà Nội",
            "Đường Lê Lợi, Phường Bến Nghé, Quận 1, TP Hồ Chí Minh",
            "Thôn 1, Xã Hòa Phong, Huyện Hòa Vang, Đà Nẵng",
            "x5,mh,ml,nd",
            "Số 1, Phường Trúc Bạch, Quận Ba Đình, Hà Nội",
        ]
        for s in sentences:
            nfc, _ = nfc_offsets(s)
            ref_seg, ref_map = self.train_ref.segment_with_map(nfc)
            got_seg, got_map, fallback = segment_with_map(nfc)
            self.assertFalse(fallback, f"Câu bình thường không được fallback: {s}")
            self.assertEqual(got_seg, ref_seg)
            self.assertEqual([tuple(x) for x in got_map], [tuple(x) for x in ref_map])

        # Câu làm train.py raise ValueError
        err_sentence = "108 Đ.TâySơn, X.Ninh Đông, TX.Ninh Hòa, Tỉnh Khánh Hòa"
        nfc_err, _ = nfc_offsets(err_sentence)
        with self.assertRaises(ValueError):
            self.train_ref.segment_with_map(nfc_err)

        got_seg, got_map, fallback = segment_with_map(nfc_err)
        self.assertTrue(fallback)
        self.assertEqual(got_seg, nfc_err)
        self.assertEqual(got_map, [(i, i + 1) for i in range(len(nfc_err))])

    def test_encode_ids_oov_va_khong_vuot_vocab_size(self):
        """(2) encode_ids không bao giờ ra ID >= vocab_size, và thay đúng ID ở câu có ID ngoài embedding."""
        # Câu thật có OOV token id >= 64001 trong dev.csv (ROW 174: token 'Hắc' có id 65883)
        oov_text = "36B, Phố Mai Hắc Đế, Nguyễn Du, Hai Bà Trưng, Hà Nội"
        nfc, _ = nfc_offsets(oov_text)

        seg, _, _ = segment_with_map(nfc)
        raw_ids = self.adapter.tokenizer(seg, add_special_tokens=True, truncation=False)["input_ids"]
        oov_indices = [i for i, tid in enumerate(raw_ids) if tid >= self.adapter.vocab_size]
        self.assertGreater(len(oov_indices), 0, "Câu thử phải có token ID >= vocab_size trong tokenizer fast")

        processed_ids = self.adapter.encode_ids(nfc)
        self.assertEqual(len(processed_ids), len(raw_ids))
        for idx in oov_indices:
            self.assertEqual(processed_ids[idx], self.adapter.unk_token_id, f"Token OOV tại vị trí {idx} phải thành UNK")

        for tid in processed_ids:
            self.assertLess(tid, self.adapter.vocab_size, "Không token ID nào được >= vocab_size")

    def test_chuan_bi_chuoi_bien_va_unicode_phan_ra(self):
        """(3) chuan_bi_chuoi không lỗi với chuỗi rỗng, chuỗi 300 ký tự, chữ Unicode phân rã."""
        # Chuỗi rỗng
        ctx_empty = self.adapter.chuan_bi_chuoi("")
        self.assertEqual(len(ctx_empty.tokens), 0)
        self.assertEqual(len(ctx_empty.labels), 0)
        self.assertEqual(len(ctx_empty.role_log_probs), 0)

        # Chuỗi chỉ khoảng trắng
        ctx_space = self.adapter.chuan_bi_chuoi("   ")
        self.assertEqual(len(ctx_space.tokens), 0)
        self.assertEqual(len(ctx_space.labels), 0)

        # Chuỗi 300 ký tự
        long_text = ("Số 1234 đường Nguyễn Thị Minh Khai, Phường Bến Nghé, Quận 1, Thành phố Hồ Chí Minh " * 4)[:300]
        ctx_long = self.adapter.chuan_bi_chuoi(long_text)
        self.assertEqual(len(ctx_long.tokens), len(ctx_long.labels))
        self.assertEqual(len(ctx_long.labels), len(ctx_long.role_log_probs))
        self.assertGreater(len(ctx_long.tokens), 0)

        # Chuỗi Unicode phân rã (NFD)
        nfd_text = unicodedata.normalize("NFD", "Số 12, Ngõ 5, Phố Nguyễn Trãi, Hà Nội")
        ctx_nfd = self.adapter.chuan_bi_chuoi(nfd_text)
        self.assertEqual(len(ctx_nfd.tokens), len(ctx_nfd.labels))
        for r, a, b in ctx_nfd.char_spans:
            self.assertTrue(0 <= a <= b <= len(nfd_text))

    def test_hai_lan_goi_cung_ket_qua(self):
        """(4) hai lần gọi cho cùng kết quả (tính tất định)."""
        samples = [
            "Số 12, Phố Hàng Bài, Hà Nội",
            "12 Trần Phú, Hà Nội",
            "Xã Ninh Đông, TX Ninh Hòa, Khánh Hòa",
        ]
        for text in samples:
            ctx1 = self.adapter.chuan_bi_chuoi(text)
            ctx2 = self.adapter.chuan_bi_chuoi(text)
            self.assertEqual(ctx1.tokens, ctx2.tokens)
            self.assertEqual(ctx1.labels, ctx2.labels)
            lp1 = torch.tensor(ctx1.role_log_probs)
            lp2 = torch.tensor(ctx2.role_log_probs)
            self.assertTrue(torch.allclose(lp1, lp2, atol=1e-5))

    def test_chieu_ky_tu_khong_vo_span(self):
        """(5) kiểm tra chiếu ký tự: 'Số 12, Phố Hàng Bài, Hà Nội' cho span đường là MỘT span liền chứ không vỡ theo ký tự."""
        raw = "Số 12, Phố Hàng Bài, Hà Nội"
        ctx = self.adapter.chuan_bi_chuoi(raw)
        spans = [(r, raw[a:b]) for r, a, b in ctx.char_spans]

        road_spans = [s for s in spans if s[0] == "duong"]
        self.assertEqual(len(road_spans), 1, f"Span đường phải là 1 span duy nhất, không vỡ: {road_spans}")
        self.assertEqual(road_spans[0][1], "Phố Hàng Bài")

        house_spans = [s for s in spans if s[0] == "so_nha"]
        self.assertEqual(len(house_spans), 1)
        self.assertEqual(house_spans[0][1], "Số 12")

        prov_spans = [s for s in spans if s[0] == "tinh"]
        self.assertEqual(len(prov_spans), 1)
        self.assertEqual(prov_spans[0][1], "Hà Nội")


if __name__ == "__main__":
    unittest.main()
