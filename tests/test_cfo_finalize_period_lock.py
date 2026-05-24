"""CFO finalize → period lock integration (service layer)."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def budget_session_awaiting_cfo():
    return SimpleNamespace(
        id='sess-cfo-final-1',
        user_id='clerk-1',
        document_type='budget_report',
        filename='budget_report.csv',
        status='validated',
        metadata={
            'workflow_status': 'approved_by_manager',
            'period_id': 'period-may-2026',
            'mapped_data': [{'account_code': '5001', 'grap_code': 'EX01', 'amount': 100}],
        },
        processing_log=[],
        updated_at=None,
    )


@patch('services.universal_workflow_service.period_management_service')
@patch('services.universal_workflow_service.supabase_auth')
def test_cfo_finalize_calls_period_lock(mock_auth, mock_period_svc, budget_session_awaiting_cfo):
    from services.universal_workflow_service import UniversalWorkflowService

    mock_auth.get_user_by_id.return_value = {
        'id': 'cfo-1',
        'role': 'CFO',
        'email': 'cfo@example.com',
    }
    locked_period = SimpleNamespace(name='May 2026 Financial Period', is_locked=True)
    mock_period_svc.lock_period.return_value = locked_period

    svc = UniversalWorkflowService()
    model = MagicMock()
    model.get_session.return_value = budget_session_awaiting_cfo
    model.update_session.side_effect = lambda s: s
    svc._get_model_for_document_type = MagicMock(return_value=model)

    with patch.object(svc, '_validate_workflow_conditions', return_value={'all_passed': True}), patch.object(
        svc, '_create_workflow_record', return_value=None
    ), patch('utils.period_lock.find_period_id_for_finalization', return_value='period-may-2026'), patch(
        'utils.period_lock.attach_period_to_session_metadata'
    ), patch('services.inbox_service.notify_submitter_final_approval'):
        result = svc.approve_document(
            document_type='budget_report',
            session_id='sess-cfo-final-1',
            user_id='cfo-1',
            notes='Finalized for export',
        )

    assert result['success'] is True
    mock_period_svc.lock_period.assert_called_once_with('period-may-2026', 'cfo-1')
    assert budget_session_awaiting_cfo.metadata.get('period_locked') is True
    assert budget_session_awaiting_cfo.metadata.get('period_lock_db_synced') is True
