"""Maroon URL normalization."""
import unittest

from utils.integration_urls import normalize_maroon_app_url, maroon_intro_url


class MaroonUrlTests(unittest.TestCase):
    def test_normalize_strip_and_trailing_slash(self):
        self.assertEqual(
            normalize_maroon_app_url("  https://maroondemo.vercel.app/  "),
            "https://maroondemo.vercel.app",
        )

    def test_normalize_empty_none(self):
        self.assertIsNone(normalize_maroon_app_url(None))
        self.assertIsNone(normalize_maroon_app_url(""))
        self.assertIsNone(normalize_maroon_app_url("   "))

    def test_intro_from_root_only(self):
        base = normalize_maroon_app_url("https://example.app/")
        self.assertEqual(maroon_intro_url(base), "https://example.app/intro")

    def test_intro_none_when_base_missing(self):
        self.assertIsNone(maroon_intro_url(None))


if __name__ == "__main__":
    unittest.main()
