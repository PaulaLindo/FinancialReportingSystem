"""Shared metadata resolution for clerk history, correction workspace, and comments API."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Optional, Tuple

REJECTED_WORKFLOW_STATUSES = frozenset({
    'rejected',
    'rejected_by_manager',
    'rejected_by_cfo',
})


def _metadata_dict(metadata: Any) -> Dict[str, Any]:
    return metadata if isinstance(metadata, dict) else {}


def _comment_list(value: Any) -> List[Dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def metadata_indicates_rejection(metadata: Any) -> bool:
    """True when session metadata reflects a clerk-actionable rejection state."""
    md = _metadata_dict(metadata)
    workflow_status = str(md.get('workflow_status') or '').lower()
    if workflow_status in REJECTED_WORKFLOW_STATUSES:
        return True
    if md.get('rejected_at') or md.get('manager_rejection') or md.get('cfo_rejection'):
        return True
    history = md.get('rejection_history')
    return isinstance(history, list) and len(history) > 0


def _comments_from_snapshot(snapshot: Any) -> List[Dict[str, Any]]:
    if not isinstance(snapshot, dict):
        return []
    return _comment_list(snapshot.get('line_item_comments'))


def _collect_archived_line_item_comments(metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Resolve comments from legacy archives without reading top-level line_item_comments."""
    seen: set = set()
    collected: List[Dict[str, Any]] = []

    def add_comments(comments: List[Dict[str, Any]]) -> None:
        for comment in comments:
            key = (
                str(comment.get('account_code') or ''),
                str(comment.get('comment_text') or comment.get('correction_suggestion') or ''),
                str(comment.get('author_id') or comment.get('author_name') or ''),
            )
            if key in seen:
                continue
            seen.add(key)
            collected.append(dict(comment))

    history = metadata.get('rejection_history')
    if isinstance(history, list):
        for entry in reversed(history):
            if not isinstance(entry, dict):
                continue
            add_comments(_comment_list(entry.get('line_item_comments')))
            if collected:
                break
            add_comments(_comments_from_snapshot(entry.get('snapshot')))
            if collected:
                break

    if not collected:
        add_comments(_comments_from_snapshot(metadata.get('rejection_snapshot')))

    return collected


def _synthetic_rejection_comments(metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
    reason = resolve_rejection_reason(metadata)
    if not reason:
        return []

    rejector_role = 'Reviewer'
    mgr = metadata.get('manager_rejection')
    cfo = metadata.get('cfo_rejection')
    if isinstance(mgr, dict):
        rejector_role = 'Finance Manager'
    elif isinstance(cfo, dict):
        rejector_role = 'CFO'

    history = metadata.get('rejection_history')
    if isinstance(history, list):
        for entry in reversed(history):
            if not isinstance(entry, dict):
                continue
            role = str(entry.get('rejector_role') or '').strip()
            if role == 'FINANCE_MANAGER':
                rejector_role = 'Finance Manager'
                break
            if role == 'CFO':
                rejector_role = 'CFO'
                break

    return [{
        'account_code': '—',
        'comment_text': reason,
        'comment_type': 'general',
        'author_name': rejector_role,
        'legacy_source': 'rejection_reason',
    }]


def resolve_line_item_comments(metadata: Any) -> List[Dict[str, Any]]:
    """
    Line-item comments on session metadata, with fallback to the latest
    rejection_history snapshot (legacy rejections before preserve-on-reject).
    """
    md = _metadata_dict(metadata)
    comments = _comment_list(md.get('line_item_comments'))
    if comments:
        return comments

    archived = _collect_archived_line_item_comments(md)
    if archived:
        return archived

    if metadata_indicates_rejection(md):
        return _synthetic_rejection_comments(md)
    return []


def resolve_rejection_reason(metadata: Any) -> str:
    """Rejection reason with legacy manager_rejection / rejection_history fallbacks."""
    md = _metadata_dict(metadata)
    reason = str(md.get('rejection_reason') or '').strip()
    if reason:
        return reason

    mgr = md.get('manager_rejection')
    if isinstance(mgr, dict):
        legacy = str(mgr.get('reason') or '').strip()
        if legacy:
            return legacy

    cfo = md.get('cfo_rejection')
    if isinstance(cfo, dict):
        legacy = str(cfo.get('reason') or '').strip()
        if legacy:
            return legacy

    history = md.get('rejection_history')
    if isinstance(history, list):
        for entry in reversed(history):
            if not isinstance(entry, dict):
                continue
            legacy = str(entry.get('reason') or '').strip()
            if legacy:
                return legacy
    return ''


def _build_rejection_history_entry_from_legacy(metadata: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    reason = resolve_rejection_reason(metadata)
    if not reason and not metadata_indicates_rejection(metadata):
        return None

    mgr = metadata.get('manager_rejection') if isinstance(metadata.get('manager_rejection'), dict) else {}
    cfo = metadata.get('cfo_rejection') if isinstance(metadata.get('cfo_rejection'), dict) else {}
    snapshot = metadata.get('rejection_snapshot') if isinstance(metadata.get('rejection_snapshot'), dict) else {}
    comments = resolve_line_item_comments(metadata)

    rejector_role = None
    if mgr:
        rejector_role = 'FINANCE_MANAGER'
    elif cfo:
        rejector_role = 'CFO'

    return {
        'at': metadata.get('rejected_at') or mgr.get('at') or cfo.get('at'),
        'by': metadata.get('rejected_by') or mgr.get('by') or cfo.get('by'),
        'reason': reason,
        'snapshot': snapshot or None,
        'line_item_comments': list(comments),
        'rejector_role': rejector_role,
        'legacy_source': 'metadata_backfill',
    }


def repair_legacy_rejection_metadata(metadata: Any) -> Tuple[Dict[str, Any], bool]:
    """
    Promote archived rejection comments and rebuild missing rejection_history entries
    for sessions rejected before comment preservation was added.
    """
    md = deepcopy(_metadata_dict(metadata))
    if not metadata_indicates_rejection(md):
        return md, False

    changed = False
    comments = resolve_line_item_comments(md)
    if comments and not _comment_list(md.get('line_item_comments')):
        md['line_item_comments'] = list(comments)
        changed = True

    reason = resolve_rejection_reason(md)
    if reason and not str(md.get('rejection_reason') or '').strip():
        md['rejection_reason'] = reason
        changed = True

    history = md.get('rejection_history')
    if not isinstance(history, list) or not history:
        entry = _build_rejection_history_entry_from_legacy(md)
        if entry:
            md['rejection_history'] = [entry]
            changed = True
    else:
        last = history[-1]
        if isinstance(last, dict):
            patched = dict(last)
            entry_changed = False
            if not _comment_list(patched.get('line_item_comments')) and comments:
                patched['line_item_comments'] = list(comments)
                entry_changed = True
            if not str(patched.get('reason') or '').strip() and reason:
                patched['reason'] = reason
                entry_changed = True
            if not isinstance(patched.get('snapshot'), dict) and isinstance(md.get('rejection_snapshot'), dict):
                patched['snapshot'] = md['rejection_snapshot']
                entry_changed = True
            if entry_changed:
                new_history = list(history)
                new_history[-1] = patched
                md['rejection_history'] = new_history
                changed = True

    return md, changed


def maybe_persist_legacy_rejection_repair(session: Any, model: Any = None) -> bool:
    """Repair legacy rejection metadata on the session and optionally persist it."""
    metadata = getattr(session, 'metadata', None) or {}
    repaired, changed = repair_legacy_rejection_metadata(metadata)
    if not changed:
        return False
    session.metadata = repaired
    if model is not None and hasattr(model, 'update_session'):
        model.update_session(session)
    return True


def clerk_submission_account_counts(metadata: Any) -> Tuple[int, int]:
    """Mapped and total account counts from session metadata only (no service calls)."""
    md = _metadata_dict(metadata)
    if not md:
        return 0, 0

    mapped = md.get('mapped_accounts', 0)
    total = md.get('total_accounts', 0)

    if isinstance(mapped, list):
        mapped = len(mapped)
    if not mapped:
        proc = md.get('processing_results') or {}
        if isinstance(proc, dict):
            mapped = proc.get('mapped_accounts', 0)
            if not total:
                total = proc.get('total_accounts', 0)
    if isinstance(mapped, bool):
        mapped = 0

    grap = md.get('grap_mapping')
    if not mapped and isinstance(grap, dict):
        mapped_accounts = grap.get('mapped_accounts', [])
        if isinstance(mapped_accounts, list):
            mapped = len(mapped_accounts)
        elif isinstance(mapped_accounts, int):
            mapped = mapped_accounts
        if not total:
            total = grap.get('total_accounts', 0)

    try:
        mapped_i = int(mapped or 0)
    except (TypeError, ValueError):
        mapped_i = 0
    try:
        total_i = int(total or 0)
    except (TypeError, ValueError):
        total_i = 0
    return mapped_i, total_i
