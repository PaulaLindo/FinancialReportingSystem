import unittest

from utils.datetime_display import format_display_datetime


class DatetimeDisplayTests(unittest.TestCase):
    def test_utc_z_shown_in_sast(self):
        # 13:47 UTC -> 15:47 SAST (May, no DST in South Africa)
        self.assertEqual(
            format_display_datetime("2026-05-20T13:47:00Z"),
            "2026-05-20 15:47",
        )

    def test_utc_offset_explicit(self):
        self.assertEqual(
            format_display_datetime("2026-05-20T13:47:00+00:00"),
            "2026-05-20 15:47",
        )

    def test_empty(self):
        self.assertEqual(format_display_datetime(None), "")
        self.assertEqual(format_display_datetime(""), "")


if __name__ == "__main__":
    unittest.main()
