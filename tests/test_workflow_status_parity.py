"""Workflow status parity for budget/income (metadata vs DB status column)."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from models.budget_report_models import budget_report_session_from_row
from utils.session_workflow import (
    db_statuses_for_workflow_query,
    effective_workflow_status,
    hydrate_session_status_from_row,
    query_sessions_by_workflow_status,
)


def test_hydrate_budget_row_uses_metadata_workflow_status():
    row = {
        'id': 'sess-1',
        'user_id': 'u1',
        'document_type': 'budget_report',
        'filename': 'budget.xlsx',
        'status': 'mapped',
        'metadata': {'workflow_status': 'approved_by_manager', 'submitted_at': '2026-05-20T10:00:00Z'},
        'total_rows': 1,
        'total_columns': 1,
    }
    assert hydrate_session_status_from_row(row) == 'approved_by_manager'
    session = budget_report_session_from_row(row)
    assert effective_workflow_status(session) == 'approved_by_manager'


def test_db_statuses_for_cfo_queue_includes_mapped_alias():
    statuses = db_statuses_for_workflow_query('approved_by_manager')
    assert 'mapped' in statuses
    assert 'approved_by_manager' in statuses


def test_db_statuses_for_fm_queue_includes_validated_alias():
    statuses = db_statuses_for_workflow_query('pending_review')
    assert 'validated' in statuses
    assert 'mapped' in statuses


def test_query_sessions_filters_by_effective_status():
    row_a = {
        'id': 'a',
        'user_id': 'u1',
        'document_type': 'budget_report',
        'filename': 'a.xlsx',
        'status': 'mapped',
        'metadata': {'workflow_status': 'approved_by_manager'},
        'total_rows': 0,
        'total_columns': 0,
    }
    row_b = {
        'id': 'b',
        'user_id': 'u1',
        'document_type': 'budget_report',
        'filename': 'b.xlsx',
        'status': 'mapped',
        'metadata': {'workflow_status': 'pending_review', 'submitted_at': '2026-05-20T09:00:00Z'},
        'total_rows': 0,
        'total_columns': 0,
    }
    row_c = {
        'id': 'c',
        'user_id': 'u1',
        'document_type': 'budget_report',
        'filename': 'c.xlsx',
        'status': 'validated',
        'metadata': {'workflow_status': 'pending_review', 'submitted_at': '2026-05-20T08:00:00Z'},
        'total_rows': 0,
        'total_columns': 0,
    }
    mock_result = MagicMock()
    mock_result.data = [row_a, row_b, row_c]
    mock_table = MagicMock()
    mock_table.select.return_value.order.return_value.limit.return_value.execute.return_value = (
        mock_result
    )
    client = MagicMock()
    client.table.return_value = mock_table

    sessions = query_sessions_by_workflow_status(
        client,
        'budget_report_sessions',
        budget_report_session_from_row,
        'approved_by_manager',
        limit=10,
    )
    assert len(sessions) == 1
    assert sessions[0].id == 'a'

    pending = query_sessions_by_workflow_status(
        client,
        'budget_report_sessions',
        budget_report_session_from_row,
        'pending_review',
        limit=10,
    )
    assert len(pending) == 2
    assert {s.id for s in pending} == {'b', 'c'}


@patch('services.universal_workflow_service.supabase_auth')
def test_cfo_can_finalize_when_db_status_mapped(mock_auth):
    from services.universal_workflow_service import UniversalWorkflowService

    mock_auth.get_user_by_id.return_value = {'role': 'CFO', 'email': 'cfo@test.com'}
    session = SimpleNamespace(
        id='sess-cfo-1',
        user_id='clerk-1',
        document_type='budget_report',
        filename='budget.xlsx',
        status='mapped',
        metadata={
            'workflow_status': 'approved_by_manager',
            'manager_approval': {'at': '2026-05-20T11:00:00Z', 'by': 'fm-1'},
            'submitted_at': '2026-05-20T10:00:00Z',
        },
        processing_log=[],
        updated_at=None,
    )
    model = MagicMock()
    model.get_session.return_value = session
    model.update_session.side_effect = lambda s: s

    svc = UniversalWorkflowService()
    svc._get_model_for_document_type = MagicMock(return_value=model)
    svc._get_workflow_transition = MagicMock(
        return_value=MagicMock(conditions=['manager_review_complete', 'manager_approved'])
    )
    svc._validate_workflow_conditions = MagicMock(return_value={'all_passed': True})
    svc._create_workflow_record = MagicMock(return_value={'id': 'wf-1'})
    svc.period_service.lock_period = MagicMock(return_value=SimpleNamespace(name='FY 2025-26'))

    with patch('utils.period_lock.find_period_id_for_finalization', return_value='period-cfo-test'):
        result = svc.approve_document('budget_report', 'sess-cfo-1', 'cfo-user-id', notes='Final')

    assert result['success'] is True
    assert result['new_status'] == 'approved'


@patch('services.universal_workflow_service.supabase_auth')
def test_cfo_pending_queue_includes_all_document_types(mock_auth):
    from services.universal_workflow_service import UniversalWorkflowService

    mock_auth.get_user_by_id.side_effect = lambda uid: (
        {'role': 'CFO', 'full_name': 'CFO User'}
        if uid == 'cfo-1'
        else {'role': 'FINANCE_CLERK', 'full_name': 'Clerk'}
    )

    def _row(doc_type, sid, workflow):
        return {
            'id': sid,
            'user_id': 'clerk-1',
            'document_type': doc_type,
            'filename': f'{doc_type}.xlsx',
            'status': 'validated',
            'metadata': {
                'workflow_status': workflow,
                'submitted_at': '2026-05-20T10:00:00Z',
                'manager_approval': {'at': '2026-05-20T11:00:00Z'},
            },
            'total_rows': 1,
            'total_columns': 1,
            'updated_at': '2026-05-20T11:00:00Z',
            'created_at': '2026-05-20T09:00:00Z',
        }

    bs_row = _row('balance_sheet', 'bs-1', 'approved_by_manager')
    inc_row = _row('income_statement', 'inc-1', 'approved_by_manager')
    bud_row = _row('budget_report', 'bud-1', 'approved_by_manager')
    noise_row = _row('balance_sheet', 'noise-1', 'pending_review')

    mock_table = MagicMock()
    mock_table.select.return_value.order.return_value.limit.return_value.execute.side_effect = [
        MagicMock(data=[bs_row, noise_row]),
        MagicMock(data=[inc_row]),
        MagicMock(data=[bud_row]),
    ]
    mock_client = MagicMock()
    mock_client.table.return_value = mock_table

    svc = UniversalWorkflowService()
    for doc_type, model in (
        ('balance_sheet', MagicMock(client=mock_client, table_name='balance_sheet_sessions')),
        ('income_statement', MagicMock(client=mock_client, table_name='income_statement_sessions')),
        ('budget_report', MagicMock(client=mock_client, table_name='budget_report_sessions')),
    ):
        pass

    def fake_get_model(doc_type):
        return MagicMock(client=mock_client, table_name={
            'balance_sheet': 'balance_sheet_sessions',
            'income_statement': 'income_statement_sessions',
            'budget_report': 'budget_report_sessions',
        }[doc_type])

    svc._get_model_for_document_type = fake_get_model

    result = svc.get_pending_approvals('cfo-1', limit=200)
    assert result['success'] is True
    types = {item['document_type'] for item in result['pending_approvals']}
    assert types == {'balance_sheet', 'income_statement', 'budget_report'}


@patch('services.universal_workflow_service.supabase_auth')
def test_cfo_reject_sets_rejected_by_cfo(mock_auth):
    from services.universal_workflow_service import UniversalWorkflowService, SubmissionStatus

    mock_auth.get_user_by_id.return_value = {'role': 'CFO', 'email': 'cfo@test.com'}
    session = SimpleNamespace(
        id='sess-rej-1',
        user_id='clerk-1',
        document_type='budget_report',
        filename='budget.xlsx',
        status='validated',
        metadata={'workflow_status': 'approved_by_manager', 'manager_approval': {'at': '2026-05-20T11:00:00Z'}},
        processing_log=[],
        updated_at=None,
    )
    model = MagicMock()
    model.get_session.return_value = session
    model.update_session.side_effect = lambda s: s

    svc = UniversalWorkflowService()
    svc._get_model_for_document_type = MagicMock(return_value=model)
    svc._get_workflow_transition = MagicMock(return_value=MagicMock(conditions=['rejection_reason']))
    svc._capture_rejection_snapshot = MagicMock(return_value={})
    svc._create_workflow_record = MagicMock(return_value={'id': 'wf-2'})
    svc._enqueue_clerk_rejection_alert = MagicMock()
    svc._clear_forward_approvals_on_cfo_rejection = MagicMock()

    with patch('services.workflow_timeline_service.append_timeline_event'):
        with patch('services.inbox_service.notify_submitter_of_rejection'):
            result = svc.reject_document('budget_report', 'sess-rej-1', 'cfo-user-id', 'Needs correction')

    assert result['success'] is True
    assert session.status == SubmissionStatus.REJECTED_BY_CFO.value
    assert session.metadata['workflow_status'] == SubmissionStatus.REJECTED_BY_CFO.value
