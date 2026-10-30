"""Synthetic tests only: no production addresses, no held-out labels."""
import unittest

from data.audit.audit_du_lieu import normalize, masked_family, osm_identity, compare, fingerprints


class TestDataAudit(unittest.TestCase):
    def test_unicode_and_case(self):
        self.assertEqual(normalize("Đường Hòa Bình"), normalize("duong hoa binh"))

    def test_masked_family_is_only_heuristic(self):
        self.assertEqual(masked_family("Số 12 Đường Hoa Đào, Hà Nội"),
                         masked_family("Số 90 Đường Hoa Đào, Hà Nội"))
        self.assertEqual(masked_family(""), "")
        self.assertEqual(masked_family("12"), "")

    def test_osm_identity_ignores_query(self):
        self.assertEqual(osm_identity("https://www.openstreetmap.org/node/123?foo=bar"),
                         osm_identity("https://openstreetmap.org/node/123"))
        self.assertNotEqual(osm_identity("https://openstreetmap.org/node/123"),
                            osm_identity("https://openstreetmap.org/way/123"))
        self.assertEqual(osm_identity("https://example.org/node/123"), "")

    def test_fingerprints_return_sets_not_private_rows(self):
        data = [{"dau_vao": "Số 1 Đường Hoa Đào, Hà Nội",
                 "nguon": "https://www.openstreetmap.org/node/123",
                 "id": "synthetic-1"}]
        keys = fingerprints(data)
        self.assertEqual(set(keys), {"text", "osm", "masked"})
        self.assertNotIn("synthetic-1", str(keys))

    def test_overlap_counts(self):
        left = fingerprints([{"dau_vao": "Số 1 Đường Hoa Đào, Hà Nội",
                              "nguon": "https://openstreetmap.org/way/123"}])
        right = fingerprints([{"dau_vao": "Số 2 Đường Hoa Đào, Hà Nội",
                               "nguon": "https://openstreetmap.org/way/123?ref=4"}])
        result = compare(left, right)
        self.assertEqual(result, {"text": 0, "osm": 1, "masked": 1})


if __name__ == "__main__":
    unittest.main()
