"""Tests for _manager_approved status parity and schema migration checks."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest


def test_manager_approved_passes_when_db_status_is_validated_alias():
    from services.universal_workflow_service import UniversalWorkflowService

    session = SimpleNamespace(
        status='validated',
        metadata={
            'workflow_status': 'approved_by_manager',
            'manager_approval': {'at': '2026-05-20T11:00:00Z', 'by': 'fm-1'},
        },
    )
    svc = UniversalWorkflowService()
    result = svc._manager_approved(session)
    assert result['passed'] is True


def test_manager_approved_fails_without_manager_approval_metadata():
    from services.universal_workflow_service import UniversalWorkflowService

    session = SimpleNamespace(
        status='validated',
        metadata={'workflow_status': 'approved_by_manager'},
    )
    svc = UniversalWorkflowService()
    result = svc._manager_approved(session)
    assert result['passed'] is False
    assert 'Finance Manager approval' in (result.get('message') or '')


@patch('services.universal_workflow_service.supabase_auth')
def test_cfo_finalize_manager_approved_condition_with_validated_db_status(mock_auth):
    """CFO finalize runs real manager_approved check (not mocked)."""
    from services.universal_workflow_service import UniversalWorkflowService

    mock_auth.get_user_by_id.return_value = {'role': 'CFO', 'email': 'cfo@test.com'}
    session = SimpleNamespace(
        id='sess-cfo-2',
        user_id='clerk-1',
        document_type='budget_report',
        filename='budget.xlsx',
        status='validated',
        metadata={
            'workflow_status': 'approved_by_manager',
            'manager_approval': {'at': '2026-05-20T11:00:00Z', 'by': 'fm-1'},
            'submitted_at': '2026-05-20T10:00:00Z',
            'variance_explanations': {},
        },
        processing_log=[],
        updated_at=None,
    )
    model = MagicMock()
    model.get_session.return_value = session
    model.update_session.side_effect = lambda s: s
    model.get_data_rows.return_value = []

    svc = UniversalWorkflowService()
    svc._get_model_for_document_type = MagicMock(return_value=model)
    svc._create_workflow_record = MagicMock(return_value={'id': 'wf-1'})
    svc.period_service.lock_period = MagicMock(return_value=SimpleNamespace(name='FY 2025-26'))

    with patch('utils.period_lock.find_period_id_for_finalization', return_value='period-cfo-test'):
        with patch('models.budget_report_models.budget_report_model.get_data_rows', return_value=[]):
            result = svc.approve_document('budget_report', 'sess-cfo-2', 'cfo-user-id', notes='Final')

    assert result['success'] is True
    assert result['new_status'] == 'approved'
    assert session.metadata.get('period_locked') is True


@patch('services.universal_workflow_service.supabase_auth')
def test_cfo_finalize_blocked_without_resolvable_period(mock_auth):
    """CFO finalize must not complete when no reporting period can be resolved."""
    from services.universal_workflow_service import UniversalWorkflowService

    mock_auth.get_user_by_id.return_value = {'role': 'CFO', 'email': 'cfo@test.com'}
    session = SimpleNamespace(
        id='sess-cfo-no-period',
        user_id='clerk-1',
        document_type='budget_report',
        filename='budget.xlsx',
        status='validated',
        metadata={
            'workflow_status': 'approved_by_manager',
            'manager_approval': {'at': '2026-05-20T11:00:00Z', 'by': 'fm-1'},
            'submitted_at': '2026-05-20T10:00:00Z',
            'variance_explanations': {},
        },
        processing_log=[],
        updated_at=None,
    )
    model = MagicMock()
    model.get_session.return_value = session
    model.update_session.side_effect = lambda s: s

    svc = UniversalWorkflowService()
    svc._get_model_for_document_type = MagicMock(return_value=model)

    with patch('utils.period_lock.find_period_id_for_finalization', return_value=None):
        with patch('models.budget_report_models.budget_report_model.get_data_rows', return_value=[]):
            result = svc.approve_document('budget_report', 'sess-cfo-no-period', 'cfo-user-id', notes='Final')

    assert result['success'] is False
    assert result.get('code') == 'period_id_unresolved'
    assert 'reporting period' in (result.get('error') or '').lower()
    assert session.metadata.get('period_locked') is not True
    assert session.metadata.get('cfo_approval') is None
    model.update_session.assert_not_called()


@patch('services.universal_workflow_service.supabase_auth')
def test_cfo_finalize_blocked_on_db_lock_failure(mock_auth):
    """CFO finalize must not complete when financial_periods lock write fails."""
    from services.universal_workflow_service import UniversalWorkflowService

    mock_auth.get_user_by_id.return_value = {'role': 'CFO', 'email': 'cfo@test.com'}
    session = SimpleNamespace(
        id='sess-cfo-db-fail',
        user_id='clerk-1',
        document_type='budget_report',
        filename='budget.xlsx',
        status='validated',
        metadata={
            'workflow_status': 'approved_by_manager',
            'manager_approval': {'at': '2026-05-20T11:00:00Z', 'by': 'fm-1'},
            'period_id': 'period-1',
            'variance_explanations': {},
        },
        processing_log=[],
        updated_at=None,
    )
    model = MagicMock()
    model.get_session.return_value = session
    model.update_session.side_effect = lambda s: s

    svc = UniversalWorkflowService()
    svc._get_model_for_document_type = MagicMock(return_value=model)
    svc.period_service.lock_period = MagicMock(side_effect=Exception('RLS denied'))

    with patch('utils.period_lock.find_period_id_for_finalization', return_value='period-1'):
        with patch('models.budget_report_models.budget_report_model.get_data_rows', return_value=[]):
            result = svc.approve_document('budget_report', 'sess-cfo-db-fail', 'cfo-user-id', notes='Final')

    assert result['success'] is False
    assert result.get('code') == 'period_lock_db_sync_failed'
    assert result.get('period_id') == 'period-1'
    assert session.metadata.get('period_locked') is not True
    assert session.metadata.get('cfo_approval') is None
    model.update_session.assert_not_called()


def test_get_session_summary_exposes_workflow_status():
    from services.financial_document_service import FinancialDocumentService

    class _StubDocService(FinancialDocumentService):
        def get_model(self):
            return MagicMock()

        def create_session(self, *args, **kwargs):
            raise NotImplementedError

        def validate_document_structure(self, *args, **kwargs):
            return {'valid': True}

        def get_document_specific_patterns(self):
            return {}

    session = SimpleNamespace(
        id='00000000-0000-4000-8000-000000000001',
        document_type='budget_report',
        filename='b.xlsx',
        status='validated',
        total_rows=1,
        total_columns=1,
        created_at=None,
        metadata={'workflow_status': 'approved_by_manager', 'submitted_at': '2026-01-01'},
        processing_log=[],
        user_id='u1',
    )
    svc = _StubDocService('budget_report')
    svc.get_model = MagicMock(return_value=MagicMock(get_session=MagicMock(return_value=session)))

    with patch('services.financial_document_service.supabase_auth.get_user_by_id', return_value=None):
        summary = svc.get_session_summary('00000000-0000-4000-8000-000000000001')

    assert summary['status'] == 'approved_by_manager'
    assert summary['workflow_status'] == 'approved_by_manager'
    assert summary['db_status'] == 'validated'


def test_schema_migration_report_all_applied():
    from services.schema_migration_service import check_cfo_period_lock_migrations

    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.execute.side_effect = [
        MagicMock(data=[
            {
                'id': 'add_period_lock_and_variance_explanations',
                'description': 'col',
                'applied_at': '2026-01-01T00:00:00Z',
                'applied_by': 'postgres',
            },
            {
                'id': 'enable_financial_periods_cfo_lock_rls',
                'description': 'rls',
                'applied_at': '2026-01-01T00:00:00Z',
                'applied_by': 'postgres',
            },
            {
                'id': 'consolidate_financial_periods_rls',
                'description': 'consolidated',
                'applied_at': '2026-01-01T00:00:00Z',
                'applied_by': 'postgres',
            },
        ]),
        MagicMock(data=[{'is_locked': False}]),
    ]

    with patch('services.schema_migration_service._get_client', return_value=mock_client):
        report = check_cfo_period_lock_migrations()

    assert report['success'] is True
    assert report['all_applied'] is True
    assert len(report['migrations']) == 3
    assert report['probes'][0]['passed'] is True
