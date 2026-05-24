"""GRAP mapping processing — shared by universal and legacy API paths."""

from typing import Any, Dict, Optional, Tuple

from flask import jsonify


def process_grap_mapping_request(
    session_id: str,
    user_id: str,
    document_type: Optional[str] = None,
) -> Tuple[Any, int]:
    """
    Run universal GRAP mapping for a session.

    Returns (Flask response, HTTP status).
    """
    from controllers.routes_universal import (
        _infer_document_type_from_session,
        require_balanced_session,
    )
    from services.universal_grap_service import universal_grap_service
    from services.universal_workflow_service import UniversalWorkflowService
    from utils.period_lock import check_session_period_unlocked

    if not session_id:
        return jsonify({"success": False, "error": "Session ID required"}), 400

    if not document_type:
        document_type = _infer_document_type_from_session(session_id)

    if document_type:
        wf = UniversalWorkflowService()
        model = wf._get_model_for_document_type(document_type)
        sess = model.get_session(session_id) if model else None
        if sess:
            allowed, lock_msg = check_session_period_unlocked(sess)
            if not allowed:
                return jsonify({
                    "success": False,
                    "error": lock_msg,
                    "period_locked": True,
                }), 403
            from utils.session_workflow import clerk_mapping_locked

            if clerk_mapping_locked(sess):
                return jsonify({
                    "success": False,
                    "error": "Session is locked pending review — mapping cannot be changed.",
                    "locked": True,
                }), 403

    if not document_type:
        return jsonify({
            "success": False,
            "error": "Document type is required and could not be inferred",
        }), 400

    balanced, balance_error = require_balanced_session(session_id, document_type)
    if not balanced:
        return jsonify({"success": False, "error": balance_error}), 400

    result = universal_grap_service.process_grap_mapping(
        session_id, user_id, document_type
    )
    if result.get("success"):
        return jsonify(result), 200
    return jsonify(result), 400
