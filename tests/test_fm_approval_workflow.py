"""Finance Manager approve/reject workflow — status transitions and audit fields."""
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from services.universal_workflow_service import UniversalWorkflowService


def _pending_session(session_id='sess-fm-1'):
    return SimpleNamespace(
        id=session_id,
        user_id='clerk-1',
        document_type='balance_sheet',
        filename='trial_balance.csv',
        status='mapped',
        metadata={
            'workflow_status': 'pending_review',
            'submitted_at': '2026-05-20T10:00:00Z',
        },
        processing_log=[],
        updated_at=None,
    )


class FmApprovalWorkflowTests(unittest.TestCase):
    @patch('services.universal_workflow_service.supabase_auth.get_user_by_id')
    @patch('services.inbox_service.notify_forwarded_to_cfo')
    def test_fm_approve_sets_approved_by_manager_and_signature(self, _notify, mock_get_user):
        mock_get_user.return_value = {'role': 'FINANCE_MANAGER', 'email': 'fm@test.com', 'id': 'fm-user-1'}
        session = _pending_session()
        mock_model = MagicMock()
        mock_model.get_session.return_value = session
        mock_model.update_session.side_effect = lambda s: s

        svc = UniversalWorkflowService()
        svc._get_model_for_document_type = MagicMock(return_value=mock_model)
        svc._create_workflow_record = MagicMock(return_value={'id': 'wf-1'})
        svc._validate_workflow_conditions = MagicMock(
            return_value={'all_passed': True, 'failed_conditions': [], 'condition_results': []}
        )

        result = svc.approve_document('balance_sheet', 'sess-fm-1', 'fm-user-1', notes='Looks good')

        self.assertTrue(result['success'])
        self.assertEqual(result['new_status'], 'approved_by_manager')
        self.assertEqual(session.metadata['workflow_status'], 'approved_by_manager')
        signatures = session.metadata.get('approval_signatures', [])
        self.assertEqual(len(signatures), 1)
        self.assertEqual(signatures[0]['user_id'], 'fm-user-1')
        self.assertEqual(signatures[0]['role'], 'FINANCE_MANAGER')
        self.assertEqual(result.get('approval_signature'), signatures)

    @patch('services.universal_workflow_service.supabase_auth.get_user_by_id')
    def test_fm_reject_requires_reason(self, mock_get_user):
        mock_get_user.return_value = {'role': 'FINANCE_MANAGER', 'email': 'fm@test.com'}
        session = _pending_session('sess-fm-rej')
        mock_model = MagicMock()
        mock_model.get_session.return_value = session

        svc = UniversalWorkflowService()
        svc._get_model_for_document_type = MagicMock(return_value=mock_model)

        result = svc.reject_document('balance_sheet', 'sess-fm-rej', 'fm-user-1', '   ')
        self.assertFalse(result['success'])
        self.assertIn('reason', result.get('error', '').lower())

    @patch('services.universal_workflow_service.supabase_auth.get_user_by_id')
    @patch('services.universal_workflow_service.UniversalWorkflowService._enqueue_clerk_rejection_alert')
    def test_fm_reject_sets_rejected_by_manager_and_reason(self, _alert, mock_get_user):
        mock_get_user.return_value = {'role': 'FINANCE_MANAGER', 'email': 'fm@test.com'}
        session = _pending_session('sess-fm-rej-2')
        mock_model = MagicMock()
        mock_model.get_session.return_value = session
        mock_model.update_session.side_effect = lambda s: s

        svc = UniversalWorkflowService()
        svc._get_model_for_document_type = MagicMock(return_value=mock_model)
        svc._create_workflow_record = MagicMock(return_value={'id': 'wf-rej'})
        svc._validate_workflow_conditions = MagicMock(return_value=None)
        svc._get_workflow_transition = MagicMock(return_value=SimpleNamespace(conditions=[]))
        svc._capture_rejection_snapshot = MagicMock(return_value={'captured_at': '2026-05-20T12:00:00'})

        reason = 'Trial balance does not tie to supporting schedules.'
        result = svc.reject_document('balance_sheet', 'sess-fm-rej-2', 'fm-user-1', reason)

        self.assertTrue(result['success'])
        self.assertEqual(result['new_status'], 'rejected_by_manager')
        self.assertEqual(session.metadata['workflow_status'], 'rejected_by_manager')
        self.assertEqual(session.metadata['rejection_reason'], reason)
        self.assertEqual(session.metadata['manager_rejection']['reason'], reason)


if __name__ == '__main__':
    unittest.main()
