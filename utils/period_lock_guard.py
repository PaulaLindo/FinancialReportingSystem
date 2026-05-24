"""
Central period-lock enforcement for mutating API requests.

Blocks POST/PUT/PATCH/DELETE when the linked reporting period is locked (CFO finalized).
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from flask import jsonify, request

from utils.period_lock import (
    check_period_id_unlocked,
    check_session_period_unlocked,
)

# Paths that may mutate data but must not be blocked by period lock
PERIOD_LOCK_EXEMPT_PREFIXES = (
    "/api/auth/",
    "/api/pdf/availability",
    "/api/generate-pdf",
    "/api/export/",
    "/api/periods",
    "/api/certificate/",
    "/api/inbox/",
    "/api/clear-submission-lock",
)

_SESSION_ID_IN_PATH = re.compile(
    r"/api/(?:universal/)?session/([^/]+)",
    re.IGNORECASE,
)


def _request_payload() -> Dict[str, Any]:
    if request.is_json:
        data = request.get_json(silent=True)
        if isinstance(data, dict):
            return data
    if request.form:
        return dict(request.form)
    return {}


def _session_id_from_path() -> Optional[str]:
    match = _SESSION_ID_IN_PATH.search(request.path or "")
    return match.group(1) if match else None


def period_lock_contexts_from_request() -> List[Dict[str, Optional[str]]]:
    """
    Collect (session_id, document_type, period_id) tuples to validate.
    Empty list means nothing to check — caller should allow the request.
    """
    contexts: List[Dict[str, Optional[str]]] = []
    payload = _request_payload()
    path_session = _session_id_from_path()

    period_id = payload.get("period_id") or request.args.get("period_id")
    if period_id:
        contexts.append({"session_id": None, "document_type": None, "period_id": str(period_id)})

    session_id = (
        payload.get("session_id")
        or payload.get("transaction_id")
        or path_session
    )
    document_type = payload.get("document_type") or request.args.get("document_type")

    items = payload.get("items") or payload.get("sessions")
    if isinstance(items, list) and items:
        for item in items:
            if not isinstance(item, dict):
                continue
            sid = item.get("session_id") or item.get("transaction_id")
            dtype = item.get("document_type")
            if sid or dtype:
                contexts.append({
                    "session_id": str(sid) if sid else None,
                    "document_type": str(dtype) if dtype else None,
                    "period_id": None,
                })
        return contexts

    if session_id or document_type:
        contexts.append({
            "session_id": str(session_id) if session_id else None,
            "document_type": str(document_type) if document_type else None,
            "period_id": None,
        })

    return contexts


def _load_session(document_type: str, session_id: str):
    from services.universal_workflow_service import UniversalWorkflowService

    wf = UniversalWorkflowService()
    model = wf._get_model_for_document_type(document_type)
    return model.get_session(session_id) if model else None


def _infer_document_type(session_id: str) -> Optional[str]:
    from utils.period_lock import infer_document_type_from_session

    return infer_document_type_from_session(session_id)


def check_period_lock_contexts(
    contexts: List[Dict[str, Optional[str]]],
) -> Tuple[bool, str]:
    """Return (allowed, error_message)."""
    for ctx in contexts:
        period_id = ctx.get("period_id")
        if period_id:
            allowed, msg = check_period_id_unlocked(period_id)
            if not allowed:
                return False, msg

        session_id = ctx.get("session_id")
        document_type = ctx.get("document_type")
        if not session_id:
            continue

        if not document_type:
            document_type = _infer_document_type(session_id)
        if not document_type:
            continue

        sess = _load_session(document_type, session_id)
        if not sess:
            continue

        allowed, msg = check_session_period_unlocked(sess)
        if not allowed:
            return False, msg

    return True, ""


def period_lock_blocked_response(message: str):
    return jsonify({"success": False, "error": message, "period_locked": True}), 403


def is_period_lock_exempt_path(path: str) -> bool:
    path = path or ""
    for prefix in PERIOD_LOCK_EXEMPT_PREFIXES:
        if path.startswith(prefix):
            return True
    return False


def register_period_lock_middleware(app) -> None:
    """Register global before_request guard for mutating /api/* routes."""

    @app.before_request
    def _enforce_period_lock_on_mutations():
        if request.method not in ("POST", "PUT", "PATCH", "DELETE"):
            return None

        path = request.path or ""
        if not path.startswith("/api/"):
            return None

        if is_period_lock_exempt_path(path):
            return None

        contexts = period_lock_contexts_from_request()
        if not contexts:
            return None

        allowed, message = check_period_lock_contexts(contexts)
        if not allowed:
            return period_lock_blocked_response(message)

        return None
