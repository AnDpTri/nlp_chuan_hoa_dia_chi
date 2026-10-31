"""Bộ kiểm thử cho adapter PhoBERT (BoTachPhoBERT, segment_with_map, encode_ids)."""

import importlib.util
import json
import os
from pathlib import Path
import sys
import unicodedata
import unittest

ROOT = Path(__file__).resolve().parent.parent


def _load_train_module():
    train_dir = ROOT / "colab/phobert_v1"
    if str(train_dir) not in sys.path:
        sys.path.insert(0, str(train_dir))
    train_path = train_dir / "train.py"
    spec = importlib.util.spec_from_file_location("phobert_train_ref", train_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class PhoBERTTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model_dir = os.environ.get("PHOBERT_MODEL_DIR")
        if not cls.model_dir or not Path(cls.model_dir).exists():
            raise unittest.SkipTest("Thiếu biến môi trường PHOBERT_MODEL_DIR hoặc thư mục không tồn tại")
        cls.train_mod = _load_train_module()

        from transformers import AutoTokenizer
        cls.tokenizer = AutoTokenizer.from_pretrained(cls.model_dir)
        cfg = json.loads((Path(cls.model_dir) / "config.json").read_text(encoding="utf-8"))
        cls.vocab_size = cfg.get("vocab_size", 64001)

        from src.phobert import BoTachPhoBERT
        cls.adapter = BoTachPhoBERT(cls.model_dir, threads=1)

    def test_1_segment_with_map_khop_train_py(self):
        """(1) segment_with_map khớp train.py trên một tập câu, gồm một câu làm train.py raise ValueError."""
        from src.phobert import segment_with_map

        normal_cases = [
            "Số 12, Phố Hàng Bài, Hà Nội",
            "123 đường Lê Lợi, Phường Bến Nghé, Quận 1, TP Hồ Chí Minh",
            "Thôn Đồng, Xã Tân Triều, Huyện Thanh Trì, Hà Nội",
            "12\tTrần Phú,\nHà Nội",
            "x5,mh,ml,nd"
        ]
        for text in normal_cases:
            ref_seg, ref_map = self.train_mod.segment_with_map(text)
            my_seg, my_map, my_fallback = segment_with_map(text)
            self.assertFalse(my_fallback, f"Không nên fallback với câu hợp lệ: {text}")
            self.assertEqual(ref_seg, my_seg, f"Segmented text khác lúc train: {text}")
            self.assertEqual([tuple(x) for x in ref_map], [tuple(x) for x in my_map], f"Mapping khác lúc train: {text}")

        # Câu làm train.py raise ValueError do PyVi chèn gạch dưới lệch:
        err_case = "Số 14 - đường Nguyễn Thái Sơn - phường 3 - quận Gò Vấp - Tp.HCM"
        with self.assertRaises(ValueError):
            self.train_mod.segment_with_map(err_case)

        my_seg, my_map, my_fallback = segment_with_map(err_case)
        self.assertTrue(my_fallback, "Phải fallback khi train.segment_with_map raise ValueError")
        self.assertEqual(my_seg, err_case, "Khi fallback, segmented phải bằng raw")
        self.assertEqual(my_map, [(i, i + 1) for i in range(len(err_case))], "Khi fallback, mapping là 1-1")

    def test_2_encode_ids_oov_policy(self):
        """(2) encode_ids không bao giờ ra ID >= vocab_size, và thay đúng ID ở câu thật có ID ngoài embedding."""
        from src.phobert import encode_ids

        # Câu thật trong data/train_dev/dev.csv có token ID 65883 >= 64001:
        text = "36B, Phố Mai Hắc Đế, Nguyễn Du, Hai Bà Trưng, Hà Nội"
        from src.phobert import segment_with_map
        seg, _ = self.train_mod.segment_with_map(text)
        raw_ids = self.tokenizer(seg, add_special_tokens=True)["input_ids"]
        oov_indices = [idx for idx, token_id in enumerate(raw_ids) if token_id >= self.vocab_size]
        self.assertTrue(len(oov_indices) > 0, "Câu mẫu phải chứa ít nhất một token ID >= vocab_size")
        target_idx = oov_indices[0]
        self.assertGreaterEqual(raw_ids[target_idx], self.vocab_size)

        # encode_ids phải thay thế ID đó bằng unk_token_id (= 3):
        remapped_ids = encode_ids(text, tokenizer=self.tokenizer, vocab_size=self.vocab_size)
        self.assertEqual(len(remapped_ids), len(raw_ids))
        self.assertTrue(all(0 <= i < self.vocab_size for i in remapped_ids), "Tất cả ID phải < vocab_size")
        self.assertEqual(remapped_ids[target_idx], self.tokenizer.unk_token_id)

    def test_3_chuan_bi_chuoi_edge_cases(self):
        """(3) chuan_bi_chuoi không lỗi với chuỗi rỗng, chuỗi 300 ký tự, chữ Unicode phân rã."""
        # Chuỗi rỗng:
        ctx_empty = self.adapter.chuan_bi_chuoi("")
        self.assertEqual(len(ctx_empty.records), 0)
        self.assertEqual(len(ctx_empty.tokens), 0)
        self.assertEqual(len(ctx_empty.labels), 0)

        # Chuỗi toàn khoảng trắng:
        ctx_space = self.adapter.chuan_bi_chuoi("   ")
        self.assertEqual(len(ctx_space.records), 0)

        # Chuỗi 300 ký tự tiếng Việt thực tế:
        long_text = ("Số 123 đường Nguyễn Văn Cừ, phường An Khánh, quận Ninh Kiều, TP Cần Thơ. " * 5)[:300]
        self.assertEqual(len(long_text), 300)
        ctx_long = self.adapter.chuan_bi_chuoi(long_text)
        self.assertGreater(len(ctx_long.records), 0)
        self.assertEqual(len(ctx_long.tokens), len(ctx_long.labels))
        self.assertEqual(len(ctx_long.tokens), len(ctx_long.role_log_probs))

        # Chuỗi ký tự lặp 'a' * 300 (vượt 256 subword):
        ctx_a300 = self.adapter.chuan_bi_chuoi("a" * 300)
        self.assertIsNotNone(ctx_a300)

        # Chữ Unicode phân rã (NFD):
        raw_nfd = unicodedata.normalize("NFD", "Số 12, Ngõ 5, Phố Nguyễn Trãi, Hà Nội")
        ctx_nfd = self.adapter.chuan_bi_chuoi(raw_nfd)
        self.assertGreater(len(ctx_nfd.records), 0)
        self.assertEqual(len(ctx_nfd.tokens), len(ctx_nfd.labels))

    def test_4_hai_lan_goi_cho_cung_ket_qua(self):
        """(4) hai lần gọi cho cùng kết quả (xác định)."""
        text = "Số 12, Phố Hàng Bài, Hà Nội"
        ctx1 = self.adapter.chuan_bi_chuoi(text)
        ctx2 = self.adapter.chuan_bi_chuoi(text)
        self.assertEqual(ctx1.tokens, ctx2.tokens)
        self.assertEqual(ctx1.labels, ctx2.labels)
        self.assertEqual(len(ctx1.role_log_probs), len(ctx2.role_log_probs))
        for r1, r2 in zip(ctx1.role_log_probs, ctx2.role_log_probs):
            self.assertEqual(len(r1), len(r2))
            for a, b in zip(r1, r2):
                self.assertAlmostEqual(a, b, places=5)

    def test_5_chieu_ky_tu_mot_span_duong_lien(self):
        """(5) kiểm tra chiếu ký tự: ví dụ 'Số 12, Phố Hàng Bài, Hà Nội' cho span đường là MỘT span liền chứ không vỡ theo ký tự."""
        text = "Số 12, Phố Hàng Bài, Hà Nội"
        ctx = self.adapter.chuan_bi_chuoi(text)

        duong_spans = [s for s in ctx.char_spans if s[0] == "duong"]
        self.assertEqual(len(duong_spans), 1, f"Kỳ vọng đúng 1 span đường, nhận được {len(duong_spans)}: {duong_spans}")

        role, start, end = duong_spans[0]
        self.assertEqual(text[start:end], "Phố Hàng Bài", f"Span đường phải trỏ đúng 'Phố Hàng Bài', nhận được: '{text[start:end]}'")

        # Kiểm tra không có span đường nào bị vỡ 1 ký tự:
        for r, a, b in ctx.char_spans:
            if r == "duong":
                self.assertGreater(b - a, 1, "Span đường không được vỡ thành từng ký tự đơn lẻ")


if __name__ == "__main__":
    unittest.main()
