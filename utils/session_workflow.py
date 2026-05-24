"""Helpers for upload session vs clerk submit-for-review workflow."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import quote

_INVALID_MAPPING_SESSION_TOKENS = frozenset({'', 'none', 'null', 'undefined'})

SUBMITTED_FOR_REVIEW_STATUSES = frozenset({
    'pending_review',
    'pending_cfo',
    'approved_by_manager',
    'rejected_by_manager',
    'submitted',
    'approved',
    'rejected',
})

PENDING_APPROVAL_STATUSES = frozenset({
    'pending_review',
    'pending_cfo',
    'approved_by_manager',
    'submitted',
    'pending',
})

CLERK_ACTIONABLE_REJECTION_STATUSES = frozenset({
    'rejected',
    'rejected_by_manager',
    'rejected_by_cfo',
})

# Clerk mapping UI is read-only after submit (matches static/js/mapping-interface.js)
CLERK_MAPPING_LOCKED_STATUSES = frozenset({
    'pending',
    'pending_review',
    'submitted',
    'approved',
    'pending_cfo',
    'approved_by_manager',
})

# History page — settled decisions only (no pending; active work stays on Review queue)

CFO_HISTORY_ALL_STATUSES = (
    'approved',
    'rejected',
)

FM_HISTORY_ALL_STATUSES = (
    'approved',
    'approved_by_manager',
    'rejected',
    'rejected_by_manager',
)

CFO_HISTORY_FILTER_MAP = {
    'all': CFO_HISTORY_ALL_STATUSES,
    'approved': ('approved',),
    'rejected': ('rejected',),
}

FM_HISTORY_FILTER_MAP = {
    'all': FM_HISTORY_ALL_STATUSES,
    'approved': ('approved', 'approved_by_manager'),
    'rejected': ('rejected', 'rejected_by_manager'),
}

# Legacy alias
FM_SETTLED_HISTORY_STATUSES = FM_HISTORY_ALL_STATUSES


def resolve_history_statuses(role: str, status_filter: str = '') -> List[str]:
    """Return DB status list for FM/CFO history API from role and filter key."""
    role_key = (role or '').upper()
    filter_key = (status_filter or 'all').strip().lower() or 'all'

    if role_key == 'CFO':
        mapping = CFO_HISTORY_FILTER_MAP
        default = CFO_HISTORY_ALL_STATUSES
    else:
        mapping = FM_HISTORY_FILTER_MAP
        default = FM_HISTORY_ALL_STATUSES

    if filter_key == 'all':
        return list(default)
    if filter_key in mapping:
        return list(mapping[filter_key])
    if ',' in filter_key:
        return [s.strip() for s in filter_key.split(',') if s.strip()]
    return [filter_key]


# Deprecated — use resolve_history_statuses
FM_HISTORY_STATUS_ALIASES = FM_HISTORY_FILTER_MAP

DRAFT_WORK_IN_PROGRESS_STATUSES = frozenset({
    'uploaded',
    'processing',
    'mapped',
    'validated',
    'draft',
})


def new_ephemeral_session_metadata(**extra: Any) -> Dict[str, Any]:
    """Metadata for upload/mapping staging — removed unless clerk submits for review."""
    meta: Dict[str, Any] = {
        'ephemeral': True,
        'committed': False,
        'upload_source': 'web_interface',
        'processing_stage': 'staging',
    }
    meta.update(extra)
    return meta


def mark_session_committed_metadata(metadata: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    meta = dict(metadata or {})
    meta['ephemeral'] = False
    meta['committed'] = True
    return meta


def session_is_ephemeral_staging(session: Any) -> bool:
    """In-progress upload/mapping not yet submitted for review (eligible for cleanup)."""
    if session_submitted_for_review(session):
        return False
    meta = session_metadata(session)
    if meta.get('committed') is True:
        return False
    if meta.get('ephemeral') is False:
        return False
    return True


def session_metadata(session: Any) -> Dict[str, Any]:
    meta = getattr(session, 'metadata', None) or {}
    if isinstance(meta, str):
        import json
        try:
            meta = json.loads(meta)
        except (json.JSONDecodeError, TypeError):
            meta = {}
    return meta if isinstance(meta, dict) else {}


def effective_workflow_status(session: Any) -> str:
    """
    Canonical workflow label for queues and filters.

    Balance sheet rows store ``pending_review`` in metadata but the DB
    ``status`` column may be the alias ``mapped`` — treat submitted
    ``mapped`` sessions as pending review for FM/CFO queues.
    """
    meta = session_metadata(session)
    workflow = meta.get('workflow_status')
    if workflow:
        return str(workflow)
    status = str(getattr(session, 'status', '') or '')
    if meta.get('submitted_at'):
        if status == 'mapped':
            return 'pending_review'
        if status == 'validated' and not workflow:
            return 'pending_cfo'
    return status


def session_submitted_for_review(session: Any) -> bool:
    """True only after the clerk clicks Submit for Review (metadata.submitted_at)."""
    meta = session_metadata(session)
    if meta.get('submitted_at'):
        return True
    workflow = meta.get('workflow_status')
    if workflow in SUBMITTED_FOR_REVIEW_STATUSES:
        return True
    status = getattr(session, 'status', '') or ''
    return status in SUBMITTED_FOR_REVIEW_STATUSES


def clerk_mapping_locked(session: Any) -> bool:
    """True when the clerk must not edit mappings or GRAP panels."""
    status = effective_workflow_status(session)
    return str(status or '').lower() in CLERK_MAPPING_LOCKED_STATUSES


def session_hidden_from_clerk_history(session: Any) -> bool:
    """Closed / archived rows are hidden from clerk history lists and summary stats."""
    st = str(getattr(session, 'status', '') or '').lower()
    if st == 'closed':
        return True
    wf = str(session_metadata(session).get('workflow_status') or '').lower()
    if wf == 'closed':
        return True
    return False


def parse_iso_datetime(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    try:
        text = str(value).replace('Z', '+00:00')
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None


def session_submitted_at(session: Any) -> Optional[datetime]:
    meta = session_metadata(session)
    submitted = parse_iso_datetime(meta.get('submitted_at'))
    if submitted:
        return submitted
    if session_submitted_for_review(session):
        return parse_iso_datetime(getattr(session, 'updated_at', None))
    return None


def session_pending_approval(session: Any) -> bool:
    if not session_submitted_for_review(session):
        return False
    return effective_workflow_status(session) in PENDING_APPROVAL_STATUSES


def session_is_draft_work(session: Any) -> bool:
    return session_is_ephemeral_staging(session)


def clerk_submission_stats(sessions: List[Any]) -> Dict[str, int]:
    """Aggregate counts for clerk dashboard / submission history."""
    visible = [s for s in sessions if not session_hidden_from_clerk_history(s)]
    today = datetime.now(timezone.utc).date()
    submitted = [s for s in visible if session_submitted_for_review(s)]

    submitted_today = 0
    for session in submitted:
        ts = session_submitted_at(session)
        if ts and ts.date() == today:
            submitted_today += 1

    pending = sum(1 for s in submitted if session_pending_approval(s))
    approved = sum(
        1
        for s in submitted
        if effective_workflow_status(s) == 'approved'
        or getattr(s, 'status', '') == 'approved'
    )
    rejected = sum(
        1
        for s in submitted
        if effective_workflow_status(s) in CLERK_ACTIONABLE_REJECTION_STATUSES
        or getattr(s, 'status', '') in CLERK_ACTIONABLE_REJECTION_STATUSES
    )
    pending_uploads = sum(1 for s in visible if session_is_draft_work(s))

    current_month = datetime.now(timezone.utc).month
    current_year = datetime.now(timezone.utc).year
    approved_this_month = 0
    for session in submitted:
        if effective_workflow_status(session) != 'approved' and getattr(session, 'status', '') != 'approved':
            continue
        meta = session_metadata(session)
        ts = parse_iso_datetime(meta.get('approved_at')) or parse_iso_datetime(
            getattr(session, 'updated_at', None)
        )
        if ts and ts.month == current_month and ts.year == current_year:
            approved_this_month += 1

    return {
        'total_submissions': len(submitted),
        'submitted_today': submitted_today,
        'pending': pending,
        'approved': approved,
        'rejected': rejected,
        'pending_uploads': pending_uploads,
        'approved_this_month': approved_this_month,
    }


def normalize_mapping_session_id(raw: Any) -> Optional[str]:
    """Return a usable session id for the mapping workspace, or None if missing/invalid."""
    if raw is None:
        return None
    sid = str(raw).strip()
    if sid.lower() in _INVALID_MAPPING_SESSION_TOKENS:
        return None
    return sid


def mapping_workspace_url(session_id: Any, *, revision: bool = False) -> str:
    """Clerk mapping page URL with session_id query param when id is valid."""
    sid = normalize_mapping_session_id(session_id)
    if not sid:
        return '/mapping?revision=1' if revision else '/mapping'
    q = f'session_id={quote(sid, safe="")}'
    if revision:
        q += '&revision=1'
    return f'/mapping?{q}'


def mapping_revision_workspace_url(session_id: Any) -> str:
    """Dedicated correction workspace after FM/CFO rejection."""
    return mapping_workspace_url(session_id, revision=True)


# Labels that may live in metadata.workflow_status while DB status stays mapped/validated
WORKFLOW_QUERY_LABELS = frozenset({
    'pending_review',
    'pending_cfo',
    'approved_by_manager',
    'rejected_by_manager',
    'rejected_by_cfo',
    'submitted',
    'resubmitted',
})


def hydrate_session_status_from_row(data: Dict[str, Any]) -> str:
    """Restore app workflow label from metadata when the DB column is a staging alias."""
    meta = data.get('metadata') if isinstance(data, dict) else {}
    if isinstance(meta, str):
        import json
        try:
            meta = json.loads(meta)
        except (json.JSONDecodeError, TypeError):
            meta = {}
    if not isinstance(meta, dict):
        meta = {}
    workflow = meta.get('workflow_status')
    if workflow:
        return str(workflow)
    return str(data.get('status') or 'draft')


def db_statuses_for_workflow_query(workflow_status: str) -> List[str]:
    """Supabase ``status`` column values to scan when resolving a workflow label."""
    key = str(workflow_status or '').strip().lower()
    buckets = {
        'pending_review': (
            'pending_review',
            'mapped',
            'validated',
            'uploaded',
            'processing',
            'submitted',
        ),
        'pending_cfo': ('pending_cfo', 'validated'),
        'approved_by_manager': (
            'approved_by_manager', 'validated', 'pending_cfo', 'mapped',
        ),
        'rejected_by_manager': ('rejected_by_manager', 'rejected'),
        'rejected_by_cfo': ('rejected_by_cfo', 'rejected'),
        'approved': ('approved',),
        'resubmitted': ('resubmitted', 'uploaded'),
    }
    if key in buckets:
        return list(dict.fromkeys(list(buckets[key]) + [key]))
    return [key] if key else []


def query_sessions_by_workflow_status(
    client: Any,
    table_name: str,
    from_row: Any,
    workflow_status: str,
    *,
    limit: int = 100,
) -> List[Any]:
    """
    Fetch sessions whose effective workflow status matches ``workflow_status``.

    Budget/income rows often keep DB ``status`` as mapped/validated while
    metadata.workflow_status holds pending_review / approved_by_manager.
    """
    ws = str(workflow_status or '').strip().lower()
    if not ws or not client or not table_name:
        return []

    if ws in WORKFLOW_QUERY_LABELS or ws in PENDING_APPROVAL_STATUSES or ws in SUBMITTED_FOR_REVIEW_STATUSES:
        # Scan recent rows and filter by effective status — budget/income often keep DB
        # status as validated/mapped while metadata.workflow_status is pending_review.
        fetch_limit = max(limit * 25, 500)
        result = (
            client.table(table_name)
            .select('*')
            .order('updated_at', desc=True)
            .limit(fetch_limit)
            .execute()
        )
        sessions: List[Any] = []
        for row in result.data or []:
            session = from_row(row)
            if effective_workflow_status(session) == ws:
                sessions.append(session)
                if len(sessions) >= limit:
                    break
        return sessions

    result = (
        client.table(table_name)
        .select('*')
        .eq('status', ws)
        .order('updated_at', desc=True)
        .limit(limit)
        .execute()
    )
    return [from_row(row) for row in (result.data or [])]


def session_matches_settled_status(session: Any, query_status: str) -> bool:
    """True if session belongs in FM/CFO history for the given workflow status key."""
    want = str(query_status or '').strip().lower()
    if not want:
        return False
    eff = str(effective_workflow_status(session) or '').lower()
    db = str(getattr(session, 'status', '') or '').lower()
    if eff == want:
        return True
    if db == want:
        return True
    if want == 'approved' and eff in ('approved', 'approved_by_manager'):
        return True
    if want == 'rejected' and eff in ('rejected', 'rejected_by_manager', 'rejected_by_cfo'):
        return True
    return False
