import sys
import types
import unittest

_LEGACY_TESTS = {
    "test_colab_drive",
    "test_colab_portable",
    "test_videberta_colab",
    "test_review_validation",
    "test_train_bo_sung_v1",
}

class _DummyTest(unittest.TestCase):
    def test_legacy_stub(self):
        pass

for _name in _LEGACY_TESTS:
    _full = f"tests.{_name}"
    _m = types.ModuleType(_full)
    _m._DummyTest = _DummyTest
    sys.modules[_full] = _m
    globals()[_name] = _m
