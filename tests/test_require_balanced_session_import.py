"""Ensure require_balanced_session is importable (regression for process-grap-mapping 500)."""

import unittest


class TestRequireBalancedSessionImport(unittest.TestCase):
    def test_import_from_routes_universal(self):
        from controllers.routes_universal import require_balanced_session, compute_submission_balance_totals

        self.assertTrue(callable(require_balanced_session))
        self.assertTrue(callable(compute_submission_balance_totals))


if __name__ == "__main__":
    unittest.main()
