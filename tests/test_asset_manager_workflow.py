"""Asset Manager workflow — register, journals, FM approval, reconciliation."""
import unittest
from unittest.mock import patch

from models.asset_register_models import InMemoryAssetRegisterModel
from services.asset_register_service import (
    JOURNAL_APPROVED,
    JOURNAL_PENDING,
    JOURNAL_REJECTED,
    AssetRegisterService,
)


class AssetRegisterServiceTests(unittest.TestCase):
    def setUp(self):
        self.svc = AssetRegisterService(model=InMemoryAssetRegisterModel())
    def _register_sample(self):
        return self.svc.register_asset(
            {
                'asset_name': 'Test vehicle',
                'asset_category': 'property_plant_equipment',
                'purchase_date': '2023-01-01',
                'purchase_cost': 100_000,
                'residual_value': 10_000,
                'useful_life_years': 5,
            },
            'am-user-1',
        )

    def test_register_and_list_assets(self):
        result = self._register_sample()
        self.assertTrue(result['success'])
        assets = self.svc.list_assets()
        self.assertEqual(len(assets), 1)
        self.assertEqual(assets[0]['asset_name'], 'Test vehicle')
        self.assertEqual(assets[0]['carrying_value'], 100_000)

    def test_useful_life_journal_pending_until_fm_approves(self):
        reg = self._register_sample()
        asset_id = reg['asset_id']
        before_carrying = self.svc.get_asset(asset_id)['carrying_value']

        journal = self.svc.create_useful_life_journal(
            asset_id,
            new_useful_life=8,
            reason='Extended service life based on condition assessment.',
            user_id='am-user-1',
            user_name='Asset Manager',
        )
        self.assertTrue(journal['success'])
        self.assertEqual(journal['journal']['status'], JOURNAL_PENDING)

        asset_mid = self.svc.get_asset(asset_id)
        self.assertEqual(asset_mid['remaining_useful_life'], 5)
        self.assertEqual(asset_mid['carrying_value'], before_carrying)

        approved = self.svc.approve_journal(journal['journal']['journal_id'], 'fm-user-1', 'Finance Manager')
        self.assertTrue(approved['success'])
        self.assertEqual(approved['journal']['status'], JOURNAL_APPROVED)

        asset_after = self.svc.get_asset(asset_id)
        self.assertEqual(asset_after['remaining_useful_life'], 8)

    def test_impairment_journal_reduces_carrying_on_approval(self):
        reg = self._register_sample()
        asset_id = reg['asset_id']

        journal = self.svc.create_impairment_journal(
            asset_id,
            impairment_amount=15_000,
            reason='Indicator of impairment — reduced recoverable amount.',
            user_id='am-user-1',
        )
        self.assertTrue(journal['success'])
        self.assertEqual(self.svc.get_asset(asset_id)['carrying_value'], 100_000)

        approved = self.svc.approve_journal(journal['journal']['journal_id'], 'fm-user-1')
        self.assertTrue(approved['success'])
        self.assertEqual(self.svc.get_asset(asset_id)['carrying_value'], 85_000)

    def test_reject_journal_does_not_apply_change(self):
        reg = self._register_sample()
        asset_id = reg['asset_id']
        journal = self.svc.create_impairment_journal(
            asset_id,
            impairment_amount=5_000,
            reason='Test impairment proposal for rejection path.',
            user_id='am-user-1',
        )
        rejected = self.svc.reject_journal(
            journal['journal']['journal_id'],
            'fm-user-1',
            'Insufficient supporting documentation.',
        )
        self.assertTrue(rejected['success'])
        self.assertEqual(rejected['journal']['status'], JOURNAL_REJECTED)
        self.assertEqual(self.svc.get_asset(asset_id)['carrying_value'], 100_000)

    def test_reconciliation_returns_variance(self):
        self._register_sample()
        recon = self.svc.get_reconciliation()
        self.assertTrue(recon['success'])
        self.assertEqual(recon['register_asset_count'], 1)
        self.assertIn('variance', recon)
        self.assertIn('gl_ppe_control_balance', recon)

    def test_list_settled_journals_for_fm_history(self):
        reg = self._register_sample()
        asset_id = reg['asset_id']
        j1 = self.svc.create_impairment_journal(
            asset_id,
            impairment_amount=5_000,
            reason='First proposal for history listing test.',
            user_id='am-user-1',
        )
        j2 = self.svc.create_impairment_journal(
            asset_id,
            impairment_amount=3_000,
            reason='Second proposal for approval history test.',
            user_id='am-user-1',
        )
        self.svc.approve_journal(j1['journal']['journal_id'], 'fm-user-1', 'FM One')
        self.svc.reject_journal(j2['journal']['journal_id'], 'fm-user-1', 'Not supported.', 'FM One')

        all_settled = self.svc.list_settled_journals(status_filter='all')
        self.assertEqual(len(all_settled), 2)
        approved = self.svc.list_settled_journals(status_filter='approved')
        self.assertEqual(len(approved), 1)
        self.assertEqual(approved[0]['status'], JOURNAL_APPROVED)
        rejected = self.svc.list_settled_journals(status_filter='rejected')
        self.assertEqual(len(rejected), 1)
        self.assertEqual(rejected[0]['rejection_reason'], 'Not supported.')

    @patch('services.asset_register_service.AssetRegisterService._notify_journal_submitted')
    def test_create_journal_triggers_fm_inbox_hook(self, mock_notify):
        reg = self._register_sample()
        self.svc.create_useful_life_journal(
            reg['asset_id'],
            new_useful_life=7,
            reason='Notify FM on submit for useful life review.',
            user_id='am-user-1',
            user_name='Asset Manager',
        )
        mock_notify.assert_called_once()

    def test_disposal_journal_disposes_on_approval(self):
        reg = self._register_sample()
        asset_id = reg['asset_id']
        journal = self.svc.create_disposal_journal(
            asset_id,
            disposal_proceeds=25_000,
            reason='Vehicle sold at auction — end of useful life.',
            user_id='am-user-1',
        )
        self.assertTrue(journal['success'])
        self.assertEqual(self.svc.get_asset(asset_id)['status'], 'active')

        forwarded = self.svc.approve_journal(
            journal['journal']['journal_id'],
            'fm-user-1',
            reviewer_role='FINANCE_MANAGER',
        )
        self.assertTrue(forwarded['success'])
        self.assertEqual(forwarded['journal']['status'], 'pending_cfo')
        self.assertEqual(self.svc.get_asset(asset_id)['status'], 'active')

        approved = self.svc.approve_journal(
            journal['journal']['journal_id'],
            'cfo-user-1',
            reviewer_role='CFO',
        )
        self.assertTrue(approved['success'])
        asset_after = self.svc.get_asset(asset_id)
        self.assertEqual(asset_after['status'], 'disposed')
        self.assertEqual(asset_after['carrying_value'], 0)

    def test_annual_depreciation_reduces_carrying_value(self):
        from datetime import datetime

        reg = self._register_sample()
        asset_id = reg['asset_id']
        before = self.svc.get_asset(asset_id)['carrying_value']
        year = datetime.now().year
        result = self.svc.process_annual_depreciation(year, 'am-user-1')
        self.assertTrue(result['success'])
        after = self.svc.get_asset(asset_id)['carrying_value']
        self.assertLess(after, before)

    def test_export_register_csv(self):
        self._register_sample()
        csv_body = self.svc.export_register_csv()
        self.assertIn('Asset ID', csv_body)
        self.assertIn('Test vehicle', csv_body)

    def test_dashboard_stats(self):
        self._register_sample()
        stats = self.svc.get_dashboard_stats('am-user-1')
        self.assertTrue(stats['success'])
        self.assertGreaterEqual(stats['asset_count'], 1)

    def test_manual_gl_balance_update(self):
        self._register_sample()
        updated = self.svc.update_gl_balance_manual(500_000, note='Test GL', user_id='fm-1')
        self.assertTrue(updated['success'])
        recon = self.svc.get_reconciliation()
        self.assertEqual(recon['gl_ppe_control_balance'], 500_000)
        self.assertEqual(recon['gl_balance_note'], 'Test GL')
        self.assertEqual(recon['gl_balance_source'], 'manual')

    def test_manual_override_replaces_trial_balance_note(self):
        self._register_sample()
        store = self.svc._read_store()
        store['gl_ppe_control_balance'] = 15_000.0
        store['gl_balance_note'] = 'Synced from balance sheet session abc — 1 fixed-asset GL line(s)'
        store['gl_balance_source'] = 'trial_balance'
        store['gl_balance_session_id'] = 'abc'
        self.svc._write_store(store)

        manual = self.svc.update_gl_balance_manual(16_000, note='Adjusted per FM review', user_id='am-1')
        self.assertTrue(manual['success'])
        recon = self.svc.get_reconciliation()
        self.assertEqual(recon['gl_balance_source'], 'manual')
        self.assertEqual(recon['gl_balance_note'], 'Adjusted per FM review')
        self.assertIsNone(recon.get('gl_balance_session_id'))

    def test_preview_sync_detects_no_change(self):
        self._register_sample()
        store = self.svc._read_store()
        store['gl_ppe_control_balance'] = 15_000.0
        store['gl_balance_source'] = 'trial_balance'
        store['gl_balance_session_id'] = 'session-abc'
        self.svc._write_store(store)

        with patch.object(self.svc, 'compute_gl_sync_from_trial_balance') as mock_compute:
            mock_compute.return_value = {
                'success': True,
                'session_id': 'session-abc',
                'proposed_gl_balance': 15_000.0,
                'matched_lines': 1,
                'already_synced': True,
                'would_change': False,
            }
            result = self.svc.sync_gl_from_trial_balance(user_id='am-1')

        self.assertTrue(result['success'])
        self.assertTrue(result.get('no_change'))


class FixedAssetGlMatchingTests(unittest.TestCase):
    def test_matches_grap_account_labels(self):
        from services.asset_register_service import _is_fixed_asset_account_row

        self.assertTrue(_is_fixed_asset_account_row({
            'grap_account': 'Property, Plant and Equipment',
            'account_code': '1004',
        }))
        self.assertTrue(_is_fixed_asset_account_row({
            'grap_account': 'Intangible Assets',
            'account_code': '2200',
        }))

    def test_matches_ppe_description_when_unmapped(self):
        from services.asset_register_service import _is_fixed_asset_account_row

        self.assertTrue(_is_fixed_asset_account_row({
            'account_code': '1004',
            'account_description': 'Property, Plant and Equipment',
        }))

    def test_excludes_receivables_on_1200_range(self):
        from services.asset_register_service import _is_fixed_asset_account_row

        self.assertFalse(_is_fixed_asset_account_row({
            'grap_account': 'Trade and Other Receivables',
            'account_code': '1200',
            'account_description': 'Trade Receivables',
        }))

    def test_reconciliation_source_label(self):
        from services.asset_register_service import _gl_balance_source_label

        self.assertEqual(_gl_balance_source_label('trial_balance'), 'Trial balance')
        self.assertEqual(_gl_balance_source_label('manual'), 'Manual entry')

    def test_gl_sync_note_uses_filename_and_short_session_id(self):
        from services.asset_register_service import _format_gl_sync_note

        note = _format_gl_sync_note(
            'sample_balanced_trial_balance.xlsx',
            '86be47f2-ea0c-4cb7-86e6-5782e1ab5502',
            1,
        )
        self.assertIn('sample_balanced_trial_balance.xlsx', note)
        self.assertIn('86be47f2…', note)
        self.assertNotIn('5782e1ab5502', note)
        self.assertIn('1 fixed-asset GL line', note)


class AssetJournalMaterialityTests(unittest.TestCase):
    def setUp(self):
        self.svc = AssetRegisterService(model=InMemoryAssetRegisterModel())

    def _register_sample(self):
        return self.svc.register_asset(
            {
                'asset_name': 'Test vehicle',
                'asset_category': 'property_plant_equipment',
                'purchase_date': '2023-01-01',
                'purchase_cost': 450_000,
                'residual_value': 50_000,
                'useful_life_years': 10,
            },
            'am-user-1',
        )

    def test_useful_life_fm_approves_without_cfo(self):
        reg = self._register_sample()
        journal = self.svc.create_useful_life_journal(
            reg['asset_id'],
            new_useful_life=8,
            reason='Revised estimate based on usage.',
            user_id='am-user-1',
        )
        approved = self.svc.approve_journal(
            journal['journal']['journal_id'],
            'fm-user-1',
            'FM One',
            reviewer_role='FINANCE_MANAGER',
        )
        self.assertTrue(approved['success'])
        self.assertEqual(approved['journal']['status'], 'approved')
        self.assertNotIn('forwarded_to_cfo', approved)

    def test_material_impairment_forwards_to_cfo(self):
        reg = self._register_sample()
        journal = self.svc.create_impairment_journal(
            reg['asset_id'],
            impairment_amount=150_000,
            reason='Indicator of impairment identified during review.',
            user_id='am-user-1',
        )
        forwarded = self.svc.approve_journal(
            journal['journal']['journal_id'],
            'fm-user-1',
            'FM One',
            reviewer_role='FINANCE_MANAGER',
        )
        self.assertTrue(forwarded['success'])
        self.assertTrue(forwarded.get('forwarded_to_cfo'))
        self.assertEqual(forwarded['journal']['status'], 'pending_cfo')

        cfo_approved = self.svc.approve_journal(
            journal['journal']['journal_id'],
            'cfo-user-1',
            'CFO One',
            reviewer_role='CFO',
        )
        self.assertTrue(cfo_approved['success'])
        self.assertEqual(cfo_approved['journal']['status'], 'approved')

    def test_material_journal_audit_trail_excludes_routine_fm_only(self):
        reg = self._register_sample()
        routine = self.svc.create_useful_life_journal(
            reg['asset_id'],
            new_useful_life=6,
            reason='Routine useful life update.',
            user_id='am-user-1',
        )
        self.svc.approve_journal(
            routine['journal']['journal_id'],
            'fm-user-1',
            'FM One',
            reviewer_role='FINANCE_MANAGER',
        )
        disposal = self.svc.create_disposal_journal(
            reg['asset_id'],
            disposal_proceeds=20_000,
            reason='End of useful life disposal.',
            user_id='am-user-1',
        )
        self.svc.approve_journal(
            disposal['journal']['journal_id'],
            'fm-user-1',
            'FM One',
            reviewer_role='FINANCE_MANAGER',
        )
        self.svc.approve_journal(
            disposal['journal']['journal_id'],
            'cfo-user-1',
            'CFO One',
            reviewer_role='CFO',
        )

        trail = self.svc.list_material_journal_audit_trail()
        journal_ids = {j['journal_id'] for j in trail}
        self.assertIn(disposal['journal']['journal_id'], journal_ids)
        self.assertNotIn(routine['journal']['journal_id'], journal_ids)
        self.assertTrue(all(j.get('requires_cfo_escalation') for j in trail))

    def test_cfo_cannot_approve_fm_queue(self):
        reg = self._register_sample()
        journal = self.svc.create_useful_life_journal(
            reg['asset_id'],
            new_useful_life=7,
            reason='Routine useful life update.',
            user_id='am-user-1',
        )
        denied = self.svc.approve_journal(
            journal['journal']['journal_id'],
            'cfo-user-1',
            'CFO One',
            reviewer_role='CFO',
        )
        self.assertFalse(denied['success'])

    def test_settled_history_excludes_invalid_records(self):
        reg = self._register_sample()
        j = self.svc.create_impairment_journal(
            reg['asset_id'],
            impairment_amount=5_000,
            reason='Small impairment for history filter test.',
            user_id='am-user-1',
        )
        self.svc.approve_journal(
            j['journal']['journal_id'],
            'fm-user-1',
            'FM One',
            reviewer_role='FINANCE_MANAGER',
        )
        store = self.svc._read_store()
        store.setdefault('journals', []).append({
            'journal_id': 'bad-history-row',
            'journal_type': 'balance_sheet',
            'status': 'approved_by_manager',
            'reason': 'budget_report_perfectly_balanced.csv',
        })
        self.svc._write_store(store)
        settled = self.svc.list_settled_journals(status_filter='all')
        ids = [row['journal_id'] for row in settled]
        self.assertIn(j['journal']['journal_id'], ids)
        self.assertNotIn('bad-history-row', ids)


if __name__ == '__main__':
    unittest.main()
