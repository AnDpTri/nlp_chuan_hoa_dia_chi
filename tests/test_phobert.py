"""Kiểm thử hợp đồng và chức năng cho adapter PhoBERT (src.phobert)."""

import importlib.util
import json
import math
import os
import sys
import unicodedata
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.nhan import TAGS
from src.phobert import BoTachPhoBERT, encode_ids, segment_with_map


def _load_train_ref():
    colab_dir = str(ROOT / "colab/phobert_v1")
    if colab_dir not in sys.path:
        sys.path.insert(0, colab_dir)
    train_path = ROOT / "colab/phobert_v1/train.py"
    spec = importlib.util.spec_from_file_location("train_ref", train_path)
    train = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(train)
    return train


class TestPhoBERT(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model_dir = os.environ.get("PHOBERT_MODEL_DIR")
        if not cls.model_dir or not Path(cls.model_dir).exists():
            raise unittest.SkipTest("Biến môi trường PHOBERT_MODEL_DIR không được đặt hoặc thư mục không tồn tại")
        cls.adapter = BoTachPhoBERT(cls.model_dir, threads=1)
        cfg = json.loads((Path(cls.model_dir) / "config.json").read_text(encoding="utf-8"))
        cls.vocab_size = cfg["vocab_size"]

    def test_segment_with_map(self):
        """(1) segment_with_map khớp train.py trên một tập câu, gồm một câu làm train.py raise ValueError."""
        train_ref = _load_train_ref()
        normal_cases = [
            "Số 12, Phố Hàng Bài, Hà Nội",
            "12 Trần Phú, Hà Nội",
            "x5,mh,ml,nd",
            "Số 1, Phường Trúc Bạch, Quận Ba Đình, Hà Nội",
        ]
        for s in normal_cases:
            seg_got, map_got, fb_got = segment_with_map(s)
            seg_ref, map_ref = train_ref.segment_with_map(s)
            self.assertEqual(seg_got, seg_ref, f"Khác segmented trên câu {s}")
            self.assertEqual([tuple(x) for x in map_got], [tuple(x) for x in map_ref], f"Khác mapping trên câu {s}")
            self.assertFalse(fb_got)

        # Câu làm train.py::segment_with_map raise ValueError
        err_case = "108 Đ.TâySơn, X.Ninh Đông, TX.Ninh Hòa, Tỉnh Khánh Hòa"
        with self.assertRaises(ValueError):
            train_ref.segment_with_map(err_case)

        seg_err, map_err, fb_err = segment_with_map(err_case)
        self.assertEqual(seg_err, err_case)
        self.assertEqual(map_err, [(i, i + 1) for i in range(len(err_case))])
        self.assertTrue(fb_err)

    def test_encode_ids_oov(self):
        """(2) encode_ids không bao giờ ra ID >= vocab_size, và thay đúng ID ở một câu thật có ID ngoài embedding."""
        # Câu trong data/train_dev/dev.csv có từ "Hắc_Đế" sinh token ID 65883 >= vocab_size (64001)
        oov_sentence = "36B, Phố Mai Hắc Đế, Nguyễn Du, Hai Bà Trưng, Hà Nội"
        seg, _, _ = segment_with_map(oov_sentence)
        raw_ids = self.adapter.tokenizer(seg)["input_ids"]
        oov_tokens = [i for i in raw_ids if i >= self.vocab_size]
        self.assertTrue(len(oov_tokens) > 0, "Câu mẫu phải có ít nhất 1 token ID ngoài embedding")
        self.assertIn(65883, oov_tokens)

        # encode_ids phải thay thế token này bằng unk_token_id (=3)
        remapped_ids = self.adapter.encode_ids(oov_sentence)
        self.assertTrue(all(i < self.vocab_size for i in remapped_ids), "Tất cả token IDs phải < vocab_size")
        self.assertNotIn(65883, remapped_ids)
        self.assertIn(self.adapter.unk_token_id, remapped_ids)

        # Kiểm tra kiểm soát max_len
        with self.assertRaises(ValueError):
            self.adapter.encode_ids("a" * 300, max_len=256)

    def test_chuan_bi_chuoi_edge_cases(self):
        """(3) chuan_bi_chuoi không lỗi với chuỗi rỗng, chuỗi 300 ký tự, chữ Unicode phân rã."""
        # 1. Chuỗi rỗng
        ctx_empty = self.adapter.chuan_bi_chuoi("")
        self.assertEqual(len(ctx_empty.tokens), 0)
        self.assertEqual(len(ctx_empty.labels), 0)
        self.assertEqual(len(ctx_empty.role_log_probs), 0)
        tach_empty = ctx_empty.tach(set())
        self.assertIsInstance(tach_empty, tuple)
        self.assertEqual(len(tach_empty), 4)

        # 2. Chuỗi 300 ký tự
        ctx_long = self.adapter.chuan_bi_chuoi("a" * 300)
        self.assertEqual(len(ctx_long.tokens), len(ctx_long.labels))
        self.assertEqual(len(ctx_long.tokens), len(ctx_long.role_log_probs))
        for row in ctx_long.role_log_probs:
            self.assertEqual(len(row), len(TAGS))
            self.assertTrue(all(math.isfinite(x) and x <= 1e-6 for row in ctx_long.role_log_probs for x in row))
        tach_long = ctx_long.tach(set())
        self.assertIsInstance(tach_long, tuple)
        self.assertEqual(len(tach_long), 4)

        # 3. Unicode phân rã (NFD)
        nfd_raw = unicodedata.normalize("NFD", "Số 12, Ngõ 5, Phố Nguyễn Trãi, Hà Nội")
        ctx_nfd = self.adapter.chuan_bi_chuoi(nfd_raw)
        self.assertEqual(len(ctx_nfd.tokens), len(ctx_nfd.labels))
        self.assertEqual(len(ctx_nfd.tokens), len(ctx_nfd.role_log_probs))
        for row in ctx_nfd.role_log_probs:
            self.assertEqual(len(row), len(TAGS))
            self.assertTrue(all(math.isfinite(x) and x <= 1e-6 for row in ctx_nfd.role_log_probs for x in row))
        tach_nfd = ctx_nfd.tach(set())
        self.assertIsInstance(tach_nfd, tuple)
        self.assertEqual(len(tach_nfd), 4)

    def test_chuan_bi_chuoi_deterministic(self):
        """(4) hai lần gọi cho cùng kết quả."""
        sample = "Số 12, Phố Hàng Bài, Hà Nội"
        ctx1 = self.adapter.chuan_bi_chuoi(sample)
        ctx2 = self.adapter.chuan_bi_chuoi(sample)

        self.assertEqual(ctx1.tokens, ctx2.tokens)
        self.assertEqual(ctx1.labels, ctx2.labels)
        self.assertEqual(len(ctx1.role_log_probs), len(ctx2.role_log_probs))
        for r1, r2 in zip(ctx1.role_log_probs, ctx2.role_log_probs):
            for x, y in zip(r1, r2):
                self.assertAlmostEqual(x, y, delta=1e-5)

    def test_projection_span_continuous(self):
        """(5) kiểm tra chiếu ký tự: ví dụ 'Số 12, Phố Hàng Bài, Hà Nội' cho span đường là MỘT span liền chứ không vỡ theo ký tự."""
        sample = "Số 12, Phố Hàng Bài, Hà Nội"
        ctx = self.adapter.chuan_bi_chuoi(sample)
        duong_spans = [r for r in ctx.char_spans if r[0] == "duong"]

        self.assertEqual(len(duong_spans), 1, f"Kỳ vọng đúng 1 span đường liền, nhưng nhận được: {duong_spans}")
        role, start, end = duong_spans[0]
        extracted_text = sample[start:end]
        self.assertIn("Hàng Bài", extracted_text)
        # Kiểm tra không có span lẻ từng ký tự
        for r in ctx.char_spans:
            self.assertTrue(r[2] - r[1] > 1 or sample[r[1]:r[2]].isalnum(), f"Span quá ngắn hoặc bất thường: {r}")


if __name__ == "__main__":
    unittest.main()
