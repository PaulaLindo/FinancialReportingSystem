"""Batch approve service tests."""

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from services.universal_workflow_service import UniversalWorkflowService


class BatchApproveTests(unittest.TestCase):
    @patch('services.universal_workflow_service.supabase_auth.get_user_by_id')
    def test_batch_approve_all_succeed(self, mock_get_user):
        mock_get_user.return_value = {'role': 'CFO', 'email': 'cfo@test.com'}

        svc = UniversalWorkflowService()
        svc.approve_document = MagicMock(side_effect=[
            {'success': True, 'new_status': 'approved'},
            {'success': True, 'new_status': 'approved'},
        ])

        result = svc.batch_approve(
            [
                {'document_type': 'balance_sheet', 'session_id': 's1'},
                {'document_type': 'income_statement', 'session_id': 's2'},
            ],
            user_id='cfo-1',
            notes='Batch',
        )

        self.assertTrue(result['success'])
        self.assertFalse(result.get('partial'))
        self.assertEqual(result['approved_count'], 2)
        self.assertEqual(result['total'], 2)
        self.assertEqual(svc.approve_document.call_count, 2)

    @patch('services.universal_workflow_service.supabase_auth.get_user_by_id')
    def test_batch_approve_partial(self, mock_get_user):
        mock_get_user.return_value = {'role': 'CFO', 'email': 'cfo@test.com'}

        svc = UniversalWorkflowService()
        svc.approve_document = MagicMock(side_effect=[
            {'success': True, 'new_status': 'approved'},
            {'success': False, 'error': 'Period lock failed'},
        ])

        result = svc.batch_approve(
            [
                {'document_type': 'balance_sheet', 'session_id': 's1'},
                {'document_type': 'budget_report', 'session_id': 's2'},
            ],
            user_id='cfo-1',
        )

        self.assertFalse(result['success'])
        self.assertTrue(result.get('partial'))
        self.assertEqual(result['approved_count'], 1)
        self.assertEqual(result['total'], 2)


if __name__ == '__main__':
    unittest.main()
