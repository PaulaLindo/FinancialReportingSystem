"""CFO dashboard KPI aggregation from pending queue."""

import unittest
from decimal import Decimal
from unittest.mock import MagicMock, patch

from services.universal_workflow_service import UniversalWorkflowService


class SessionKpiSnapshotTests(unittest.TestCase):
    def test_income_statement_uses_net_income(self):
        session = MagicMock()
        session.metadata = {}
        session.processed_at = '2026-01-01T00:00:00Z'
        session.net_income = Decimal('125000.50')
        kpi = UniversalWorkflowService._session_kpi_snapshot(session, 'income_statement')
        self.assertEqual(kpi['surplus_deficit'], 125000.5)
        self.assertIsNone(kpi['budget_variance'])

    def test_income_statement_skips_unprocessed_zero_defaults(self):
        session = MagicMock()
        session.metadata = {}
        session.processed_at = None
        session.net_income = Decimal('0.00')
        session.total_revenue = Decimal('0.00')
        session.total_expenses = Decimal('0.00')
        kpi = UniversalWorkflowService._session_kpi_snapshot(session, 'income_statement')
        self.assertIsNone(kpi['surplus_deficit'])

    def test_budget_report_uses_total_variance(self):
        session = MagicMock()
        session.metadata = {}
        session.processed_at = '2026-01-01T00:00:00Z'
        session.total_variance = Decimal('-42000')
        session.variance_percentage = Decimal('-8.5')
        session.total_budget = Decimal('500000')
        session.total_actual = Decimal('542000')
        kpi = UniversalWorkflowService._session_kpi_snapshot(session, 'budget_report')
        self.assertEqual(kpi['budget_variance'], -42000.0)
        self.assertEqual(kpi['variance_percentage'], -8.5)

    def test_balance_sheet_reads_processing_summary(self):
        session = MagicMock()
        session.metadata = {'processing_summary': {'surplus_deficit': 88000}}
        kpi = UniversalWorkflowService._session_kpi_snapshot(session, 'balance_sheet')
        self.assertEqual(kpi['surplus_deficit'], 88000.0)


class CfoDashboardKpisTests(unittest.TestCase):
    @patch('services.universal_workflow_service.supabase_auth.get_user_by_id')
    def test_aggregates_pending_queue(self, mock_get_user):
        mock_get_user.return_value = {'role': 'CFO', 'id': 'cfo-1'}
        svc = UniversalWorkflowService()
        svc.get_pending_approvals = MagicMock(
            return_value={
                'success': True,
                'pending_approvals': [
                    {'kpi': {'surplus_deficit': 100000.0, 'budget_variance': None}},
                    {'kpi': {'surplus_deficit': -25000.0, 'budget_variance': None}},
                    {'kpi': {'surplus_deficit': None, 'budget_variance': 15000.0}},
                ],
                'total_count': 3,
                'has_more': False,
            }
        )
        result = svc.get_cfo_dashboard_kpis('cfo-1')
        self.assertTrue(result['success'])
        self.assertEqual(result['pending_finalization_count'], 3)
        self.assertEqual(result['surplus_deficit_total'], 75000.0)
        self.assertEqual(result['surplus_deficit_submission_count'], 2)
        self.assertEqual(result['budget_variance_total'], 15000.0)
        self.assertEqual(result['budget_variance_submission_count'], 1)

    @patch('services.universal_workflow_service.supabase_auth.get_user_by_id')
    def test_rejects_non_cfo(self, mock_get_user):
        mock_get_user.return_value = {'role': 'FINANCE_MANAGER', 'id': 'fm-1'}
        result = UniversalWorkflowService().get_cfo_dashboard_kpis('fm-1')
        self.assertFalse(result['success'])


if __name__ == '__main__':
    unittest.main()
