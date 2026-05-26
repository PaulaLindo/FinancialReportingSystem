"""System Admin routes and auditor audit-pack inbox notifications."""
import unittest
from pathlib import Path
from unittest.mock import patch

from services.inbox_service import notify_auditors_audit_pack_ready

ROOT = Path(__file__).resolve().parents[1]


class AuditorAuditPackInboxTests(unittest.TestCase):
    @patch("services.inbox_service.notify_users_by_role")
    def test_notify_auditors_audit_pack_ready_targets_auditor_role(self, mock_notify):
        mock_notify.return_value = 2

        sent = notify_auditors_audit_pack_ready(
            period_id="period-1",
            period_name="May 2026",
            session_id="sess-1",
            document_type="balance_sheet",
            actor_id="cfo-1",
        )

        self.assertEqual(sent, 2)
        mock_notify.assert_called_once()
        _args, kwargs = mock_notify.call_args
        self.assertEqual(_args[0], "AUDITOR")
        self.assertEqual(kwargs["message_type"], "audit_pack_ready")
        self.assertEqual(kwargs["metadata"]["action_url"], "/audit")
        self.assertIn("May 2026", kwargs["body"])


class AdminRoutesContractTests(unittest.TestCase):
    def test_admin_routes_registered(self):
        app_py = (ROOT / "app.py").read_text(encoding="utf-8")
        routes_admin = (ROOT / "controllers" / "routes_admin.py").read_text(encoding="utf-8")
        inbox_src = (ROOT / "services" / "inbox_service.py").read_text(encoding="utf-8")
        self.assertIn("register_admin_routes", app_py)
        self.assertIn("/api/admin/overview", routes_admin)
        self.assertIn("/api/admin/users", routes_admin)
        self.assertIn("api_admin_activate_user", routes_admin)
        self.assertIn("/api/admin/periods", routes_admin)
        self.assertIn("merge-duplicates", routes_admin)
        self.assertIn("/admin/cleanup", routes_admin)
        self.assertIn("api_admin_delete_period", routes_admin)
        routes_py = (ROOT / "controllers" / "routes.py").read_text(encoding="utf-8")
        self.assertIn("@permission_required('manage_users')", routes_py)
        self.assertNotIn("@permission_required('admin')", routes_py)
        base = (ROOT / "templates" / "base.html").read_text(encoding="utf-8")
        self.assertIn("current_user.role != 'SYSTEM_ADMIN'", base)
        self.assertIn("notify_auditors_audit_pack_ready", inbox_src)


if __name__ == "__main__":
    unittest.main()
