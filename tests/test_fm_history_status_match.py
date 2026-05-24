"""FM history matches workflow status in metadata, not only DB status column."""

from types import SimpleNamespace

from utils.session_workflow import session_matches_settled_status


def test_budget_approved_by_manager_in_metadata_matches_approved_filter():
    session = SimpleNamespace(
        status='mapped',
        metadata={'workflow_status': 'approved_by_manager', 'submitted_at': '2026-05-20T10:00:00Z'},
    )
    assert session_matches_settled_status(session, 'approved_by_manager')
    assert session_matches_settled_status(session, 'approved')


def test_rejected_by_manager_matches_rejected_filter():
    session = SimpleNamespace(
        status='validated',
        metadata={'workflow_status': 'rejected_by_manager'},
    )
    assert session_matches_settled_status(session, 'rejected')
