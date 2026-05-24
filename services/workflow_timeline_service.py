"""Build auditable workflow timelines from session metadata (append-only)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from utils.datetime_display import format_display_datetime
from utils.session_workflow import CLERK_ACTIONABLE_REJECTION_STATUSES


def _iso_to_display(iso_val: Any) -> str:
    if not iso_val:
        return '—'
    try:
        return format_display_datetime(str(iso_val))
    except Exception:
        return str(iso_val)


def append_timeline_event(metadata: Dict[str, Any], event: Dict[str, Any]) -> None:
    """Append one event; never remove prior rejection or submission records."""
    if metadata is None:
        return
    tl = metadata.get('workflow_timeline')
    if not isinstance(tl, list):
        tl = []
    row = dict(event)
    tl.append(row)
    metadata['workflow_timeline'] = tl[-100:]


def build_timeline_from_metadata(metadata: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Ordered timeline for FM/clerk UI.
    Prefer unified workflow_timeline; fall back to legacy rejection/resubmission lists.
    """
    md = metadata if isinstance(metadata, dict) else {}
    unified = md.get('workflow_timeline')
    if isinstance(unified, list) and unified:
        return [_normalize_event(e) for e in unified if isinstance(e, dict)]

    events: List[Dict[str, Any]] = []

    submitted_at = md.get('submitted_at') or md.get('first_submitted_at')
    if submitted_at:
        events.append(
            _normalize_event(
                {
                    'type': 'clerk_submission',
                    'at': submitted_at,
                    'label': 'Clerk original submission',
                    'detail': (md.get('submission_notes') or '').strip() or None,
                }
            )
        )

    for entry in md.get('rejection_history') or []:
        if not isinstance(entry, dict):
            continue
        role = entry.get('rejector_role') or 'Reviewer'
        events.append(
            _normalize_event(
                {
                    'type': 'rejection',
                    'at': entry.get('at'),
                    'label': f'Manager rejection' if role == 'FINANCE_MANAGER' else f'{role} rejection',
                    'detail': (entry.get('reason') or '').strip() or None,
                    'actor_role': role,
                    'prior_status': entry.get('prior_status'),
                }
            )
        )

    mgr = md.get('manager_rejection')
    if isinstance(mgr, dict) and mgr.get('reason'):
        if not any(e.get('type') == 'rejection' for e in events):
            events.append(
                _normalize_event(
                    {
                        'type': 'rejection',
                        'at': mgr.get('at'),
                        'label': 'Rejected by Finance Manager',
                        'detail': str(mgr.get('reason', '')).strip(),
                    }
                )
            )

    for entry in md.get('resubmission_history') or []:
        if not isinstance(entry, dict):
            continue
        events.append(
            _normalize_event(
                {
                    'type': 'clerk_resubmission',
                    'at': entry.get('at'),
                    'label': 'Clerk correction and resubmission',
                    'detail': (entry.get('clerk_correction_note') or entry.get('note') or '').strip() or None,
                    'changes_summary': entry.get('changes_summary'),
                }
            )
        )

    events.sort(key=lambda e: e.get('at') or '')
    return events


def _normalize_event(raw: Dict[str, Any]) -> Dict[str, Any]:
    at = raw.get('at') or raw.get('timestamp')
    return {
        'type': raw.get('type') or 'event',
        'at': at,
        'at_display': _iso_to_display(at),
        'label': raw.get('label') or raw.get('type') or 'Event',
        'detail': raw.get('detail') or raw.get('text') or raw.get('reason'),
        'actor_role': raw.get('actor_role'),
        'changes_summary': raw.get('changes_summary'),
        'prior_status': raw.get('prior_status'),
    }


def timeline_has_resubmission(events: Optional[List[Dict[str, Any]]]) -> bool:
    """True when the session was returned and resubmitted at least once."""
    for ev in events or []:
        if isinstance(ev, dict) and ev.get('type') == 'clerk_resubmission':
            return True
    return False


def timeline_tab_label(events: Optional[List[Dict[str, Any]]]) -> str:
    """UI label: first-time submissions use Submission history; resubmits use Resubmission history."""
    return 'Resubmission history' if timeline_has_resubmission(events) else 'Submission history'


def is_correction_status(status: str) -> bool:
    return str(status or '').lower() in CLERK_ACTIONABLE_REJECTION_STATUSES


def rejection_banner_text(metadata: Optional[Dict[str, Any]], status: str) -> Dict[str, Any]:
    """Pinned banner copy for clerk revision workspace."""
    md = metadata if isinstance(metadata, dict) else {}
    reason = (md.get('rejection_reason') or '').strip()
    if not reason and isinstance(md.get('manager_rejection'), dict):
        reason = (md['manager_rejection'].get('reason') or '').strip()
    if not reason and isinstance(md.get('rejection_history'), list) and md['rejection_history']:
        last = md['rejection_history'][-1]
        if isinstance(last, dict):
            reason = (last.get('reason') or '').strip()

    st = str(status or '').lower()
    if st == 'rejected_by_manager':
        title = 'Rejected by Finance Manager'
    elif st == 'rejected_by_cfo':
        title = 'Rejected by CFO'
    elif st == 'rejected':
        title = 'Submission rejected'
    else:
        title = 'Returned for correction'

    return {
        'title': title,
        'reason': reason or 'No rejection comment was recorded. Contact your reviewer if you need guidance.',
        'status': st,
    }


def correction_workspace_payload(
    session: Any,
    *,
    document_type: str,
    user_id: str,
) -> Dict[str, Any]:
    """Context for clerk revision page."""
    from utils.session_workflow import effective_workflow_status

    md = getattr(session, 'metadata', None) or {}
    status = effective_workflow_status(session)
    owner_id = str(getattr(session, 'user_id', '') or '')
    banner = rejection_banner_text(md, status)
    timeline = build_timeline_from_metadata(md)
    from utils.session_metadata_helpers import resolve_line_item_comments, resolve_rejection_reason

    line_item_comments = resolve_line_item_comments(md)
    rejection_reason = resolve_rejection_reason(md) or banner.get('reason') or ''
    return {
        'session_id': getattr(session, 'id', None),
        'document_type': document_type,
        'status': status,
        'is_correction_mode': is_correction_status(status),
        'is_owner': owner_id == str(user_id),
        'rejection_banner': banner,
        'timeline': timeline,
        'rejection_reason': rejection_reason,
        'filename': getattr(session, 'original_filename', None) or getattr(session, 'filename', None),
        'line_item_comments': line_item_comments,
    }
