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


class AuditorMaterialJournalTrailTests(unittest.TestCase):
    def test_list_material_journal_audit_trail_filters_cfo_material_only(self):
        from models.asset_register_models import InMemoryAssetRegisterModel
        from services.asset_register_service import AssetRegisterService

        svc = AssetRegisterService(model=InMemoryAssetRegisterModel())
        reg = svc.register_asset(
            {
                'asset_name': 'Audit trail asset',
                'asset_category': 'property_plant_equipment',
                'purchase_date': '2023-01-01',
                'purchase_cost': 200_000,
                'residual_value': 0,
                'useful_life_years': 5,
            },
            'am-user-1',
        )
        self.assertTrue(reg.get('success'))
        asset_id = reg['asset_id']
        disposal = svc.create_disposal_journal(
            asset_id,
            disposal_proceeds=10_000,
            reason='Audit trail disposal test.',
            user_id='am-user-1',
        )
        svc.approve_journal(
            disposal['journal']['journal_id'],
            'fm-user-1',
            'FM One',
            reviewer_role='FINANCE_MANAGER',
        )
        svc.approve_journal(
            disposal['journal']['journal_id'],
            'cfo-user-1',
            'CFO One',
            reviewer_role='CFO',
        )

        trail = svc.list_material_journal_audit_trail()
        self.assertEqual(len(trail), 1)
        self.assertEqual(trail[0]['journal_id'], disposal['journal']['journal_id'])
        self.assertTrue(trail[0]['requires_cfo_escalation'])


if __name__ == '__main__':
    unittest.main()
