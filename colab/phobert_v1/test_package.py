"""Offline unit tests for char -> PhoBERT subword alignment, no pretrained model needed."""
import re
import unittest
from unittest.mock import patch
import train


class FakeTokenizer:
    unk_token_id = 3

    def __call__(self, text, **kwargs):
        spans = [(m.start(), m.end()) for m in re.finditer(r"\S+", text)]
        return {"input_ids": [0] + list(range(5, 5 + len(spans))) + [2],
                "offset_mapping": [(0, 0)] + spans + [(0, 0)]}


class AlignmentTests(unittest.TestCase):
    def test_entity_first_word_B_and_continuation_I(self):
        raw = "Số 12"
        allowed = [[1], [2], [0], [2], [2]]
        row = {"id": "a", "nfc": raw, "allowed": allowed}
        with patch.object(train, "segment_with_map", lambda x: (x, [(i, i + 1) for i in range(len(x))])):
            result = train.encode_one(row, FakeTokenizer(), 100)
        self.assertTrue(result["allowed"][1][1])
        self.assertTrue(result["allowed"][2][2])
        self.assertEqual(result["conflicts"], 0)

    def test_weak_ward_not_forced_to_O(self):
        raw = "An Khánh"
        row = {"id": "b", "nfc": raw, "allowed": [[0, 9, 10]] * len(raw)}
        with patch.object(train, "segment_with_map", lambda x: (x, [(i, i + 1) for i in range(len(x))])):
            result = train.encode_one(row, FakeTokenizer(), 100)
        self.assertTrue(result["allowed"][1][0])
        self.assertTrue(result["allowed"][1][9])
        self.assertTrue(result["allowed"][1][10])

    def test_cross_role_subword_is_not_invented(self):
        raw = "AB"
        row = {"id": "c", "nfc": raw, "allowed": [[1], [7]]}
        with patch.object(train, "segment_with_map", lambda x: (x, [(i, i + 1) for i in range(len(x))])):
            result = train.encode_one(row, FakeTokenizer(), 100)
        self.assertFalse(any(result["allowed"][1]))
        self.assertEqual(result["conflicts"], 1)

    def test_oov_token_maps_to_unk_not_invalid_gpu_index(self):
        ids, replaced = train.remap_invalid_token_ids([0, 65364, 2], 64001, 3)
        self.assertEqual(ids, [0, 3, 2])
        self.assertEqual(replaced, 1)
        self.assertLess(max(ids), 64001)

    def test_oov_unk_itself_invalid_is_hard_error(self):
        with self.assertRaises(ValueError):
            train.remap_invalid_token_ids([64002], 64001, 65000)

    def test_oov_in_actual_encoding(self):
        raw = "AB"
        row = {"id": "d", "nfc": raw, "allowed": [[1], [2]]}
        fake = FakeTokenizer()
        fake.__class__ = FakeTokenizer
        with patch.object(train, "segment_with_map", lambda x: (x, [(i, i + 1) for i in range(len(x))])), patch.object(
                FakeTokenizer, "__call__", return_value={
                "input_ids": [0, 65364, 2],
                "offset_mapping": [(0, 0), (0, 2), (0, 0)]}):
            result = train.encode_one(row, fake, 64001)
        self.assertEqual(result["ids"], [0, 3, 2])
        self.assertEqual(result["replaced_oov_tokens"], 1)


if __name__ == "__main__":
    unittest.main()
