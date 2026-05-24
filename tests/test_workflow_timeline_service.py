"""Workflow timeline and clerk correction helpers."""

from services.workflow_timeline_service import (
    append_timeline_event,
    build_timeline_from_metadata,
    is_correction_status,
    rejection_banner_text,
    timeline_has_resubmission,
    timeline_tab_label,
)


def test_is_correction_status():
    assert is_correction_status('rejected_by_manager')
    assert is_correction_status('rejected_by_cfo')
    assert not is_correction_status('pending_review')


def test_build_timeline_from_rejection_history():
    md = {
        'submitted_at': '2026-01-01T10:00:00+00:00',
        'submission_notes': 'First submit',
        'rejection_history': [
            {
                'at': '2026-01-02T11:00:00+00:00',
                'reason': 'Remap account 4015',
                'rejector_role': 'FINANCE_MANAGER',
            }
        ],
        'resubmission_history': [
            {
                'at': '2026-01-03T12:00:00+00:00',
                'clerk_correction_note': 'Fixed mapping to GRAP 23.',
            }
        ],
    }
    events = build_timeline_from_metadata(md)
    types = [e['type'] for e in events]
    assert 'clerk_submission' in types
    assert 'rejection' in types
    assert 'clerk_resubmission' in types


def test_append_timeline_event_preserves_prior():
    md = {}
    append_timeline_event(md, {'type': 'rejection', 'at': 't1', 'label': 'Reject', 'detail': 'A'})
    append_timeline_event(md, {'type': 'clerk_resubmission', 'at': 't2', 'label': 'Resubmit', 'detail': 'B'})
    assert len(md['workflow_timeline']) == 2
    assert md['workflow_timeline'][0]['detail'] == 'A'


def test_rejection_banner_text():
    banner = rejection_banner_text(
        {'rejection_reason': 'Account 4015 mapped incorrectly.'},
        'rejected_by_manager',
    )
    assert banner['title'] == 'Rejected by Finance Manager'
    assert '4015' in banner['reason']


def test_timeline_tab_label_first_submission():
    md = {'submitted_at': '2026-01-01T10:00:00+00:00', 'submission_notes': 'First submit'}
    events = build_timeline_from_metadata(md)
    assert not timeline_has_resubmission(events)
    assert timeline_tab_label(events) == 'Submission history'


def test_timeline_tab_label_after_resubmission():
    md = {
        'workflow_timeline': [
            {'type': 'clerk_submission', 'at': 't1', 'label': 'Clerk original submission'},
            {'type': 'rejection', 'at': 't2', 'label': 'Manager rejection', 'detail': 'Fix mapping'},
            {'type': 'clerk_resubmission', 'at': 't3', 'label': 'Clerk correction and resubmission'},
        ]
    }
    events = build_timeline_from_metadata(md)
    assert timeline_has_resubmission(events)
    assert timeline_tab_label(events) == 'Resubmission history'
