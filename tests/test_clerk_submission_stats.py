"""Clerk dashboard submission counters."""
import unittest
from datetime import datetime, timedelta
from types import SimpleNamespace

from utils.datetime_display import display_timezone, local_today
from utils.session_workflow import clerk_submission_stats


class ClerkSubmissionStatsTests(unittest.TestCase):
    def _session(self, submitted_at_iso, updated_at=None, status='pending_review'):
        return SimpleNamespace(
            status=status,
            metadata={
                'submitted_at': submitted_at_iso,
                'workflow_status': 'pending_review',
            },
            updated_at=updated_at,
        )

    def test_submitted_today_ignores_updated_at_when_submitted_yesterday(self):
        tz = display_timezone()
        yesterday_local = datetime.now(tz) - timedelta(days=1)
        today_local = datetime.now(tz)
        session = self._session(
            yesterday_local.astimezone(tz).isoformat(),
            updated_at=today_local,
        )

        stats = clerk_submission_stats([session])

        self.assertEqual(stats['submitted_today'], 0)

    def test_naive_local_submission_date_matches_display_not_utc_shift(self):
        """Naive submitted_at (SAST wall clock) must not roll to next day as UTC."""
        from utils.datetime_display import local_date, local_today, parse_app_timezone_timestamp

        session = self._session('2026-05-25T22:06:00')
        stats = clerk_submission_stats([session])

        self.assertEqual(local_date(parse_app_timezone_timestamp('2026-05-25T22:06:00')).isoformat(), '2026-05-25')
        if local_today().isoformat() == '2026-05-26':
            self.assertEqual(stats['submitted_today'], 0)
        elif local_today().isoformat() == '2026-05-25':
            self.assertEqual(stats['submitted_today'], 1)


if __name__ == '__main__':
    unittest.main()
