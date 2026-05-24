"""
PDF generation availability — requires reporting period to be locked (CFO finalized).
"""

from typing import Any, Dict, Optional, Tuple

from models.period_models import period_model
from utils.period_lock import (
    find_period_id_for_finalization,
    is_period_locked,
    resolve_period_id_from_session,
    session_is_cfo_finalized,
)


def _load_workflow_session(
    session_id: str, document_type: str
) -> Tuple[Optional[Any], Optional[str]]:
    """Load session via universal workflow models (lazy import for testability)."""
    from services.universal_workflow_service import UniversalWorkflowService

    wf = UniversalWorkflowService()
    model = wf._get_model_for_document_type(document_type)
    session = model.get_session(session_id) if model else None
    resolved_period_id = resolve_period_id_from_session(session) if session else None
    return session, resolved_period_id


def resolve_pdf_availability(
    session_id: Optional[str] = None,
    document_type: Optional[str] = None,
    period_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Return whether PDF generation is allowed for a session/period.

    PDF is allowed only when the linked reporting period is locked (CFO finalization).
    """
    period_locked = False
    period_name = None
    resolved_period_id = period_id
    lock_source = None

    session = None
    if session_id and document_type:
        session, resolved_from_session = _load_workflow_session(session_id, document_type)
        if not resolved_period_id:
            resolved_period_id = resolved_from_session
        if session:
            md = session.metadata or {}
            if md.get("period_locked"):
                period_locked = True
                lock_source = "session_metadata"
            elif session_is_cfo_finalized(session):
                period_locked = True
                lock_source = "cfo_finalized"
                if not resolved_period_id:
                    resolved_period_id = find_period_id_for_finalization(session)
            period_name = md.get("period_name")

    if resolved_period_id:
        period = period_model.get_period(resolved_period_id)
        if period:
            period_name = period_name or period.name
            if is_period_locked(period):
                period_locked = True
                lock_source = lock_source or "financial_periods"

    can_download = period_locked
    reason = ""
    if not can_download:
        reason = (
            "PDF download is available only after the reporting period has been "
            "finalized and locked by the CFO."
        )

    return {
        "can_generate_pdf": can_download,
        "can_download_pdf": can_download,
        "period_locked": period_locked,
        "period_id": resolved_period_id,
        "period_name": period_name,
        "lock_source": lock_source,
        "reason": reason,
        "session_id": session_id,
        "document_type": document_type,
    }
