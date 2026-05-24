"""
GRAP compliance checks for universal workflow (balance sheet, income statement, budget).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from services.statement_validation_service import mapped_lines_from_metadata, validate_for_review
from utils.grap24_scope import grap24_applies_to
from utils.grap_standards_scope import statement_compliance_applies_to


def _mapped_lines_from_session(session) -> List[Dict[str, Any]]:
    return mapped_lines_from_metadata(getattr(session, "metadata", None) or {})


def run_session_grap_compliance(
    session,
    document_type: str,
) -> Dict[str, Any]:
    """
    Run document-appropriate GRAP checks and return workflow-friendly result.

    Budget reports defer variance rules to budget_variance_service (GRAP 24).
    """
    dt = (document_type or "").strip().lower()
    md = getattr(session, "metadata", None) or {}

    if grap24_applies_to(dt):
        return {"passed": True, "message": None, "report": None}

    if not statement_compliance_applies_to(dt):
        return {"passed": True, "message": None, "report": None}

    lines = _mapped_lines_from_session(session)
    report = validate_for_review(
        document_type=dt,
        lines=lines if lines else None,
        session_metadata=md,
    )
    passed = bool(report.get("valid"))
    failed_checks = [c for c in report.get("checks") or [] if not c.get("passed")]
    message = None
    if not passed and failed_checks:
        parts = [c.get("message") or c.get("check", "") for c in failed_checks[:4]]
        message = (
            f"{standard_failure_prefix(dt)}: " + "; ".join(p for p in parts if p)
        )
    return {"passed": passed, "message": message, "report": report}


def standard_failure_prefix(document_type: str) -> str:
    from utils.grap_standards_scope import standard_label_for_document

    return standard_label_for_document(document_type)
