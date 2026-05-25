"""Auditor role — read-only access to finalized sessions."""
import unittest
from unittest.mock import MagicMock, patch

from models.supabase_auth_models import SupabaseUser
from services.export_center_service import export_center_service


class AuditorPermissionTests(unittest.TestCase):
    def _user(self, role: str) -> SupabaseUser:
        return SupabaseUser({
            'id': 'u1',
            'username': 'test',
            'full_name': 'Test User',
            'role': role,
            'email': 't@test.com',
            'is_active': True,
            'created_at': '2026-01-01',
        })

    def test_auditor_has_view_assets_and_export_audit(self):
        user = self._user('AUDITOR')
        self.assertTrue(user.can_export_audit())
        self.assertTrue(user.can_view_assets())
        self.assertTrue(user.can_access_audit_workspace())
        self.assertFalse(user.can_export())
        self.assertFalse(user.can_review())

    def test_cfo_not_audit_workspace_only(self):
        user = self._user('CFO')
        self.assertFalse(user.can_access_audit_workspace())
        self.assertTrue(user.can_access_export_center())


class ExportCenterAuditorViewTests(unittest.TestCase):
    @patch.object(export_center_service, 'session_is_exportable')
    @patch.object(export_center_service, 'load_session')
    def test_is_auditor_viewable_delegates_to_session_is_exportable(self, mock_load, mock_exportable):
        mock_load.return_value = MagicMock(id='sess-1')
        mock_exportable.return_value = (True, '')
        self.assertTrue(export_center_service.is_auditor_viewable('sess-1', 'balance_sheet'))
        mock_exportable.assert_called_once()

    @patch.object(export_center_service, 'session_is_exportable')
    @patch.object(export_center_service, 'load_session')
    def test_is_auditor_viewable_false_when_not_exportable(self, mock_load, mock_exportable):
        mock_load.return_value = MagicMock(id='sess-1')
        mock_exportable.return_value = (False, 'not locked')
        self.assertFalse(export_center_service.is_auditor_viewable('sess-1', 'balance_sheet'))


if __name__ == '__main__':
    unittest.main()
