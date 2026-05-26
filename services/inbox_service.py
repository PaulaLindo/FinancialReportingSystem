"""Durable user inbox backed by Supabase ``user_inbox_messages``."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

TABLE = "user_inbox_messages"


def _client():
    from utils.supabase_service_client import get_service_supabase_client

    return get_service_supabase_client()


def notify_user(
    user_id: str,
    *,
    message_type: str,
    title: str,
    body: str,
    severity: str = "info",
    metadata: Optional[Dict[str, Any]] = None,
    actor_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Insert inbox row for a user; returns inserted row dict or None on failure/no client."""
    client = _client()
    if not client or not user_id:
        return None
    row = {
        "user_id": str(user_id),
        "message_type": message_type,
        "severity": severity,
        "title": title[:500],
        "body": body[:8000] if body else "",
        "metadata": metadata or {},
        "actor_id": str(actor_id) if actor_id else None,
    }
    try:
        res = client.table(TABLE).insert(row).execute()
        if res.data and len(res.data) > 0:
            inserted = res.data[0]
            try:
                from services.email_notification_service import notify_user_email

                notify_user_email(
                    str(user_id),
                    message_type=message_type,
                    title=title,
                    body=body,
                )
            except Exception:
                pass
            return inserted
    except Exception as exc:
        logger.warning("inbox insert failed for user %s: %s", user_id, exc)
    return None


def _users_with_role(role: str) -> List[Dict[str, Any]]:
    """Load notify targets; prefer service role so RLS on ``users`` does not block inserts."""
    client = _client()
    if client:
        try:
            res = (
                client.table("users")
                .select("id, full_name, role, is_active")
                .eq("role", role)
                .eq("is_active", True)
                .execute()
            )
            if res.data:
                return list(res.data)
        except Exception as exc:
            logger.warning("inbox: service-role user lookup failed for %s: %s", role, exc)
    try:
        from models.supabase_auth_models import SupabaseAuthModel

        return [
            u
            for u in (SupabaseAuthModel().get_users_by_role(role) or [])
            if u.get("is_active", True)
        ]
    except Exception as exc:
        logger.warning("inbox: fallback user lookup failed for %s: %s", role, exc)
        return []


def notify_users_by_role(
    role: str,
    *,
    message_type: str,
    title: str,
    body: str,
    severity: str = "info",
    metadata: Optional[Dict[str, Any]] = None,
    actor_id: Optional[str] = None,
) -> int:
    """Notify every active user with the given role. Returns count sent."""
    users = _users_with_role(role)
    if not users:
        logger.warning("inbox: no active users found for role %s", role)
    sent = 0
    for u in users:
        uid = u.get("id")
        if uid and notify_user(
            str(uid),
            message_type=message_type,
            title=title,
            body=body,
            severity=severity,
            metadata=metadata,
            actor_id=actor_id,
        ):
            sent += 1
    return sent


def notify_submission_pending_review(
    *,
    session_id: str,
    document_type: str,
    submitter_id: str,
    submitter_name: str = "",
) -> int:
    label = document_type.replace("_", " ")
    return notify_users_by_role(
        "FINANCE_MANAGER",
        message_type="submission_pending_review",
        title=f"New submission awaiting review",
        body=f"{submitter_name or 'A clerk'} submitted a {label} for your review.",
        severity="info",
        metadata={
            "session_id": session_id,
            "document_type": document_type,
            "submitter_id": submitter_id,
            "action_url": "/finance-manager/review-queue",
            "action_label": "Open review queue",
        },
        actor_id=submitter_id,
    )


def notify_forwarded_to_cfo(
    *,
    session_id: str,
    document_type: str,
    manager_id: str,
) -> int:
    label = document_type.replace("_", " ")
    return notify_users_by_role(
        "CFO",
        message_type="submission_pending_cfo",
        title="Submission forwarded for final approval",
        body=f"A {label} was approved by the Finance Manager and needs your final sign-off.",
        severity="info",
        metadata={
            "session_id": session_id,
            "document_type": document_type,
            "action_url": "/finance-manager/review-queue",
            "action_label": "Open review queue",
        },
        actor_id=manager_id,
    )


def notify_submitter_final_approval(
    submitter_user_id: Optional[str],
    *,
    session_id: str,
    document_type: str,
    approver_id: str,
) -> Optional[Dict[str, Any]]:
    if not submitter_user_id:
        return None
    label = document_type.replace("_", " ")
    return notify_user(
        str(submitter_user_id),
        message_type="submission_approved",
        title="Submission approved",
        body=f"Your {label} has received final CFO approval.",
        severity="info",
        metadata={
            "session_id": session_id,
            "document_type": document_type,
            "action_url": "/submission-history",
            "action_label": "View submission history",
        },
        actor_id=approver_id,
    )


def notify_auditors_audit_pack_ready(
    *,
    period_id: str,
    period_name: str,
    session_id: str,
    document_type: str,
    actor_id: str,
) -> int:
    """Notify AGSA auditors when a reporting period is locked and audit-ready."""
    label = document_type.replace("_", " ")
    display_period = (period_name or period_id or "Reporting period").strip()
    return notify_users_by_role(
        "AUDITOR",
        message_type="audit_pack_ready",
        title="Reporting period locked — audit pack ready",
        body=(
            f"{display_period} is locked with CFO-finalized submissions available "
            f"for read-only audit (including {label})."
        ),
        severity="info",
        metadata={
            "period_id": period_id,
            "period_name": period_name,
            "session_id": session_id,
            "document_type": document_type,
            "action_url": "/audit",
            "action_label": "Open audit workspace",
        },
        actor_id=actor_id,
    )


def notify_workflow_comment(
    workflow: Any,
    *,
    comment: Dict[str, Any],
    actor_id: str,
) -> None:
    """Notify workflow participants except the comment author (best-effort)."""
    if isinstance(workflow, dict):
        wf = workflow
    elif hasattr(workflow, "to_dict"):
        wf = workflow.to_dict()
    else:
        wf = {k: getattr(workflow, k) for k in dir(workflow) if not k.startswith("_")}
    doc_id = wf.get("document_id") or wf.get("session_id") or ""
    participants = set()
    for key in ("submitter_id", "created_by", "user_id"):
        if wf.get(key):
            participants.add(str(wf[key]))
    submitter = wf.get("metadata", {}) if isinstance(wf.get("metadata"), dict) else {}
    if submitter.get("submitted_by"):
        participants.add(str(submitter["submitted_by"]))
    participants.discard(str(actor_id))
    author = comment.get("author_name") or "A colleague"
    snippet = (comment.get("text") or "")[:240]
    for uid in participants:
        notify_user(
            uid,
            message_type="workflow_comment",
            title="New comment on a submission",
            body=f"{author} commented: {snippet}",
            severity="info",
            metadata={"workflow_id": wf.get("id"), "document_id": doc_id},
            actor_id=actor_id,
        )


def notify_asset_journal_pending_review(
    *,
    journal_id: str,
    journal_type: str,
    asset_id: str,
    asset_name: str,
    submitter_id: str,
    submitter_name: str = "",
) -> int:
    label = journal_type.replace("_", " ")
    return notify_users_by_role(
        "FINANCE_MANAGER",
        message_type="asset_journal_pending_review",
        title="Asset journal awaiting review",
        body=(
            f"{submitter_name or 'Asset Manager'} submitted a {label} for "
            f"{asset_name or asset_id} — approval required before the register updates."
        ),
        severity="info",
        metadata={
            "journal_id": journal_id,
            "journal_type": journal_type,
            "asset_id": asset_id,
            "asset_name": asset_name,
            "submitter_id": submitter_id,
            "action_url": "/finance-manager/asset-journals",
            "action_label": "Open asset journals",
        },
        actor_id=submitter_id,
    )


def notify_asset_journal_pending_cfo(
    *,
    journal_id: str,
    journal_type: str,
    asset_id: str,
    asset_name: str,
    fm_reviewer_id: str,
    fm_reviewer_name: str = "",
    escalation_reason: str = "",
) -> int:
    label = journal_type.replace("_", " ")
    reason_line = f" {escalation_reason.strip()}" if escalation_reason else ""
    return notify_users_by_role(
        "CFO",
        message_type="asset_journal_pending_cfo",
        title="Material asset journal — CFO sign-off",
        body=(
            f"{fm_reviewer_name or 'Finance Manager'} forwarded a {label} for "
            f"{asset_name or asset_id}.{reason_line} Final approval is required before the register updates."
        ),
        severity="warning",
        metadata={
            "journal_id": journal_id,
            "journal_type": journal_type,
            "asset_id": asset_id,
            "asset_name": asset_name,
            "action_url": "/finance-manager/asset-journals",
            "action_label": "Review asset journals",
        },
        actor_id=fm_reviewer_id,
    )


def notify_asset_journal_forwarded_to_cfo(
    submitter_user_id: Optional[str],
    *,
    journal_id: str,
    journal_type: str,
    asset_id: str,
    asset_name: str,
    fm_reviewer_name: str = "",
) -> Optional[Dict[str, Any]]:
    if not submitter_user_id:
        return None
    label = journal_type.replace("_", " ")
    return notify_user(
        str(submitter_user_id),
        message_type="asset_journal_forwarded_to_cfo",
        title="Asset journal forwarded to CFO",
        body=(
            f"Your {label} for {asset_name or asset_id} was reviewed by "
            f"{fm_reviewer_name or 'Finance Manager'} and forwarded to the CFO for materiality sign-off."
        ),
        severity="info",
        metadata={
            "journal_id": journal_id,
            "journal_type": journal_type,
            "asset_id": asset_id,
            "action_url": f"/asset-manager/assets/{asset_id}",
            "action_label": "View asset",
        },
        actor_id=submitter_user_id,
    )


def notify_asset_journal_approved(
    submitter_user_id: Optional[str],
    *,
    journal_id: str,
    journal_type: str,
    asset_id: str,
    asset_name: str,
    reviewer_id: str,
    reviewer_name: str = "",
) -> Optional[Dict[str, Any]]:
    if not submitter_user_id:
        return None
    label = journal_type.replace("_", " ")
    return notify_user(
        str(submitter_user_id),
        message_type="asset_journal_approved",
        title="Asset journal approved",
        body=(
            f"Your {label} for {asset_name or asset_id} was approved by "
            f"{reviewer_name or 'Finance Manager'}. The asset register has been updated."
        ),
        severity="info",
        metadata={
            "journal_id": journal_id,
            "journal_type": journal_type,
            "asset_id": asset_id,
            "action_url": f"/asset-manager/assets/{asset_id}",
            "action_label": "View asset",
        },
        actor_id=reviewer_id,
    )


def notify_asset_journal_rejected(
    submitter_user_id: Optional[str],
    *,
    journal_id: str,
    journal_type: str,
    asset_id: str,
    asset_name: str,
    reason: str,
    reviewer_id: str,
    reviewer_name: str = "",
) -> Optional[Dict[str, Any]]:
    if not submitter_user_id:
        return None
    label = journal_type.replace("_", " ")
    body = (
        f"Your {label} for {asset_name or asset_id} was rejected by "
        f"{reviewer_name or 'Finance Manager'}.\n\n{reason.strip()}"
    )
    return notify_user(
        str(submitter_user_id),
        message_type="asset_journal_rejected",
        title="Asset journal rejected",
        body=body,
        severity="high",
        metadata={
            "journal_id": journal_id,
            "journal_type": journal_type,
            "asset_id": asset_id,
            "action_url": f"/asset-manager/assets/{asset_id}",
            "action_label": "View asset",
        },
        actor_id=reviewer_id,
    )


def notify_submitter_of_rejection(
    submitter_user_id: Optional[str],
    *,
    session_id: str,
    document_type: str,
    reason: str,
    rejector_id: str,
    new_status: str,
) -> Optional[Dict[str, Any]]:
    if not submitter_user_id:
        return None
    title = "Submission returned for correction"
    body = (
        f"Your {document_type.replace('_', ' ')} submission was rejected and must be corrected before resubmitting.\n\n"
        f"{reason.strip()}"
    )
    from utils.session_workflow import mapping_revision_workspace_url

    md = {
        "session_id": session_id,
        "document_type": document_type,
        "new_status": new_status,
        "rejector_id": rejector_id,
        "action_url": mapping_revision_workspace_url(session_id),
        "action_label": "Open correction workspace",
    }
    return notify_user(
        str(submitter_user_id),
        message_type="submission_rejected",
        title=title,
        body=body,
        severity="high",
        metadata=md,
        actor_id=str(rejector_id),
    )


def list_messages_for_user(
    user_id: str,
    *,
    limit: int = 50,
    unread_only: bool = False,
) -> List[Dict[str, Any]]:
    client = _client()
    if not client:
        return []
    try:
        q = client.table(TABLE).select("*").eq("user_id", str(user_id))
        if unread_only:
            q = q.is_("read_at", "null")
        res = (
            q.order("created_at", desc=True).limit(min(limit, 200)).execute()
        )
        return list(res.data or [])
    except Exception:
        return []


def unread_count(user_id: str) -> int:
    client = _client()
    if not client:
        return 0
    try:
        res = (
            client.table(TABLE)
            .select("id", count="exact")
            .eq("user_id", str(user_id))
            .is_("read_at", "null")
            .execute()
        )
        return res.count if res.count else 0
    except Exception:
        return 0


def mark_read(message_id: str, user_id: str) -> bool:
    """Mark one message read iff it belongs to user_id."""
    client = _client()
    if not client:
        return False
    try:
        now = datetime.utcnow().isoformat() + "Z"
        res = (
            client.table(TABLE)
            .update({"read_at": now})
            .eq("id", message_id)
            .eq("user_id", str(user_id))
            .execute()
        )
        return bool(res.data)
    except Exception:
        return False


def mark_all_read(user_id: str) -> int:
    client = _client()
    if not client:
        return 0
    try:
        now = datetime.utcnow().isoformat() + "Z"
        res = (
            client.table(TABLE)
            .update({"read_at": now})
            .eq("user_id", str(user_id))
            .is_("read_at", "null")
            .execute()
        )
        return len(res.data) if res.data else 0
    except Exception:
        return 0
