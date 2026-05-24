"""Clerk mapping lock guards."""

import unittest
from types import SimpleNamespace

from utils.session_workflow import clerk_mapping_locked


class ClerkMappingLockGuardTests(unittest.TestCase):
    def _locked_session(self):
        return SimpleNamespace(
            id='s1',
            user_id='u1',
            status='pending_review',
            metadata={'workflow_status': 'pending_review', 'submitted_at': '2026-01-01T00:00:00'},
        )

    def test_clerk_mapping_locked_detects_pending_review(self):
        self.assertTrue(clerk_mapping_locked(self._locked_session()))

    def test_clerk_mapping_locked_allows_draft(self):
        draft = SimpleNamespace(id='s2', status='mapped', metadata={})
        self.assertFalse(clerk_mapping_locked(draft))

    def test_clerk_mapping_locked_allows_rejection_correction(self):
        rejected = SimpleNamespace(
            id='s3',
            status='rejected_by_manager',
            metadata={'workflow_status': 'rejected_by_manager'},
        )
        self.assertFalse(clerk_mapping_locked(rejected))


if __name__ == '__main__':
    unittest.main()
