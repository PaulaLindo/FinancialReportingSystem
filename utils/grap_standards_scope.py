"""
GRAP standards applied per document type in the universal workflow.

- budget_report: GRAP 24 — Statement of Comparison of Budget and Actual Amounts
  (mandatory variance explanations when |variance/budget| > 10%).
- balance_sheet: GRAP 1 presentation + accounting equation (assets = liabilities + equity).
- income_statement: GRAP 1 presentation + performance structure (revenue/expense recognition).

Income statements do not use GRAP 24; there is no budget-vs-actual variance narrative for SFP/SFPER.
"""

from typing import FrozenSet

from utils.grap24_scope import GRAP24_DOCUMENT_TYPES, grap24_applies_to

# Aliases for clarity in workflow code
BALANCE_SHEET_DOCUMENT_TYPES: FrozenSet[str] = frozenset({"balance_sheet"})
INCOME_STATEMENT_DOCUMENT_TYPES: FrozenSet[str] = frozenset({"income_statement"})

# Statement-of-financial-position / performance compliance (not GRAP 24)
GRAP_STATEMENT_COMPLIANCE_TYPES: FrozenSet[str] = (
    BALANCE_SHEET_DOCUMENT_TYPES | INCOME_STATEMENT_DOCUMENT_TYPES
)


def statement_compliance_applies_to(document_type: str) -> bool:
    return (document_type or "").strip().lower() in GRAP_STATEMENT_COMPLIANCE_TYPES


def standard_label_for_document(document_type: str) -> str:
    dt = (document_type or "").strip().lower()
    if grap24_applies_to(dt):
        return "GRAP 24 (Budget vs Actual)"
    if dt == "balance_sheet":
        return "GRAP 1 (SFP)"
    if dt == "income_statement":
        return "GRAP 1 (Performance)"
    return "GRAP compliance"


def standard_short_label(document_type: str) -> str:
    """Short label for buttons and toasts."""
    return standard_label_for_document(document_type)


def submit_review_button_label(document_type: str) -> str:
    dt = (document_type or "").strip().lower()
    if grap24_applies_to(dt):
        return "Submit for Review — GRAP 24"
    if dt == "balance_sheet":
        return "Submit for Review — GRAP 1 (SFP)"
    if dt == "income_statement":
        return "Submit for Review — GRAP 1 (Performance)"
    return "Submit for Review"


def submit_success_message(document_type: str) -> str:
    from utils.constants import ClerkWorkflowMessages

    return ClerkWorkflowMessages.FORWARDED_TO_MANAGER


def compliance_intro_for_document(document_type: str) -> dict:
    """Copy for the mapping-page compliance panel before submit."""
    dt = (document_type or "").strip().lower()
    if grap24_applies_to(dt):
        return {
            "title": "GRAP 24 — Budget vs Actual",
            "intro": (
                "Before submit for review, provide written variance explanations for "
                "every line item where variance as a share of budget exceeds 10%."
            ),
        }
    if dt == "balance_sheet":
        return {
            "title": "GRAP 1 — Statement of Financial Position (SFP)",
            "intro": (
                "Before submit for review, all accounts must be mapped to GRAP categories and "
                "assets must equal liabilities plus equity (trial balance must already be balanced)."
            ),
        }
    if dt == "income_statement":
        return {
            "title": "GRAP 1 — Statement of Financial Performance",
            "intro": (
                "Before submit for review, all accounts must be mapped to GRAP categories and "
                "revenue and expense lines must be present for performance reporting."
            ),
        }
    return {"title": "GRAP compliance", "intro": "Complete mapping before submitting for review."}
