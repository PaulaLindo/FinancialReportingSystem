"""Shared metadata resolution for clerk history, correction workspace, and comments API."""
from __future__ import annotations

from typing import Any, Dict, List, Tuple


def _metadata_dict(metadata: Any) -> Dict[str, Any]:
    return metadata if isinstance(metadata, dict) else {}


def resolve_line_item_comments(metadata: Any) -> List[Dict[str, Any]]:
    """
    Line-item comments on session metadata, with fallback to the latest
    rejection_history snapshot (legacy rejections before preserve-on-reject).
    """
    md = _metadata_dict(metadata)
    comments = list(md.get('line_item_comments') or [])
    if comments:
        return comments

    history = md.get('rejection_history')
    if not isinstance(history, list):
        return []

    for entry in reversed(history):
        if not isinstance(entry, dict):
            continue
        archived = entry.get('line_item_comments')
        if isinstance(archived, list) and archived:
            return list(archived)
        snap = entry.get('snapshot')
        if isinstance(snap, dict):
            archived = snap.get('line_item_comments')
            if isinstance(archived, list) and archived:
                return list(archived)
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

    history = md.get('rejection_history')
    if isinstance(history, list):
        for entry in reversed(history):
            if not isinstance(entry, dict):
                continue
            legacy = str(entry.get('reason') or '').strip()
            if legacy:
                return legacy
    return ''


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
