import unittest
from types import SimpleNamespace

from utils.session_workflow import effective_workflow_status, session_pending_approval


class FmPendingQueueTests(unittest.TestCase):
    def test_mapped_db_status_with_submitted_at_is_pending_review(self):
        session = SimpleNamespace(
            status="mapped",
            metadata={
                "submitted_at": "2026-05-20T12:00:00",
                "committed": True,
            },
        )
        self.assertEqual(effective_workflow_status(session), "pending_review")
        self.assertTrue(session_pending_approval(session))

    def test_workflow_status_in_metadata_wins(self):
        session = SimpleNamespace(
            status="mapped",
            metadata={
                "workflow_status": "pending_review",
                "submitted_at": "2026-05-20T12:00:00",
            },
        )
        self.assertEqual(effective_workflow_status(session), "pending_review")

    def test_validated_db_status_with_pending_review_metadata(self):
        session = SimpleNamespace(
            status="validated",
            metadata={
                "workflow_status": "pending_review",
                "submitted_at": "2026-05-20T12:00:00",
            },
        )
        self.assertEqual(effective_workflow_status(session), "pending_review")
        self.assertTrue(session_pending_approval(session))


if __name__ == "__main__":
    unittest.main()
