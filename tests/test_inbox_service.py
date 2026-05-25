import unittest
from unittest.mock import MagicMock, patch

from services.inbox_service import (
    notify_asset_journal_pending_review,
    notify_submission_pending_review,
    notify_users_by_role,
)


class InboxServiceTests(unittest.TestCase):
    @patch("services.inbox_service.notify_user")
    @patch("services.inbox_service._users_with_role")
    def test_notify_submission_pending_review_targets_fm(self, mock_users, mock_notify):
        mock_users.return_value = [{"id": "fm-1", "is_active": True}]
        mock_notify.return_value = {"id": "msg-1"}

        sent = notify_submission_pending_review(
            session_id="sess-1",
            document_type="balance_sheet",
            submitter_id="clerk-1",
            submitter_name="Clerk One",
        )

        self.assertEqual(sent, 1)
        mock_users.assert_called_once_with("FINANCE_MANAGER")
        mock_notify.assert_called_once()
        _args, kwargs = mock_notify.call_args
        self.assertEqual(_args[0], "fm-1")
        self.assertEqual(kwargs["message_type"], "submission_pending_review")
        self.assertEqual(kwargs["metadata"]["document_type"], "balance_sheet")

    @patch("services.inbox_service.notify_user")
    @patch("services.inbox_service._users_with_role")
    def test_notify_users_by_role_no_users(self, mock_users, mock_notify):
        mock_users.return_value = []
        sent = notify_users_by_role(
            "FINANCE_MANAGER",
            message_type="test",
            title="T",
            body="B",
        )
        self.assertEqual(sent, 0)
        mock_notify.assert_not_called()

    @patch("services.inbox_service.notify_user")
    @patch("services.inbox_service._users_with_role")
    def test_notify_asset_journal_pending_review_targets_fm(self, mock_users, mock_notify):
        mock_users.return_value = [{"id": "fm-1", "is_active": True}]
        mock_notify.return_value = {"id": "msg-1"}

        sent = notify_asset_journal_pending_review(
            journal_id="AJ_1",
            journal_type="impairment",
            asset_id="AST_1",
            asset_name="Test asset",
            submitter_id="am-1",
            submitter_name="Asset Manager",
        )

        self.assertEqual(sent, 1)
        mock_notify.assert_called_once()
        _args, kwargs = mock_notify.call_args
        self.assertEqual(kwargs["message_type"], "asset_journal_pending_review")
        self.assertEqual(kwargs["metadata"]["action_url"], "/finance-manager/asset-journals")


if __name__ == "__main__":
    unittest.main()
