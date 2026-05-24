"""
GRAP 24 budget variance analysis — mandatory explanations when variance exceeds 10%.

Applies only to budget_report (Statement of Comparison of Budget and Actual Amounts).
See utils.grap24_scope — not used for balance sheet or income statement.
"""

from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

VARIANCE_EXPLANATION_THRESHOLD = Decimal("0.10")


def _dec(val: Any) -> Decimal:
    if val is None:
        return Decimal("0")
    try:
        return Decimal(str(val))
    except Exception:
        return Decimal("0")


def resolve_line_variance(
    budget_amount: Any,
    actual_amount: Any,
    file_variance: Any = None,
) -> Decimal:
    """
    Canonical GRAP 24 line variance: actual − budget when both amounts are known.
    File variance is only used when budget or actual is missing.
    """
    if budget_amount is not None and actual_amount is not None:
        return _dec(actual_amount) - _dec(budget_amount)
    if file_variance is not None:
        return _dec(file_variance)
    return Decimal("0")


def compute_session_variance(total_budget: Any, total_actual: Any) -> Decimal:
    """Session-level variance: total actual − total budget."""
    return _dec(total_actual) - _dec(total_budget)


def line_variance_pct(budget_amount: Any, variance: Any) -> float:
    """Return absolute variance as a fraction of budget (e.g. 0.12 = 12%)."""
    budget = _dec(budget_amount)
    if budget == 0:
        return 0.0
    return float(abs(_dec(variance)) / abs(budget))


def line_requires_explanation(row: Dict[str, Any]) -> bool:
    if row.get("is_total_row") or row.get("is_subtotal_row"):
        return False
    budget = _dec(row.get("budget_amount"))
    if budget == 0:
        return False
    variance = resolve_line_variance(
        row.get("budget_amount"),
        row.get("actual_amount"),
        row.get("variance"),
    )
    pct = line_variance_pct(budget, variance)
    return pct > float(VARIANCE_EXPLANATION_THRESHOLD)


def enrich_budget_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """Add GRAP 24 variance metadata to a budget row dict."""
    enriched = dict(row)
    if not enriched.get("is_total_row") and not enriched.get("is_subtotal_row"):
        enriched["variance"] = float(
            resolve_line_variance(
                enriched.get("budget_amount"),
                enriched.get("actual_amount"),
                enriched.get("variance"),
            )
        )
    budget = _dec(enriched.get("budget_amount"))
    variance = _dec(enriched.get("variance"))
    pct = line_variance_pct(budget, variance)
    requires = line_requires_explanation(enriched)
    enriched["variance_percentage"] = round(pct * 100, 2)
    enriched["requires_variance_explanation"] = requires
    return enriched


def get_lines_requiring_explanation(budget_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [enrich_budget_row(r) for r in (budget_rows or []) if line_requires_explanation(r)]


def get_variance_explanations_from_metadata(metadata: Optional[Dict[str, Any]]) -> Dict[str, str]:
    md = metadata or {}
    raw = md.get("variance_explanations") or {}
    if not isinstance(raw, dict):
        return {}
    return {str(k): str(v).strip() for k, v in raw.items() if str(v).strip()}


def validate_variance_explanations(
    budget_rows: List[Dict[str, Any]],
    explanations: Optional[Dict[str, str]] = None,
) -> Tuple[bool, List[str], List[Dict[str, Any]]]:
    """
    Validate that every line with |variance/budget| > 10% has a non-empty explanation.

    Returns (passed, missing_row_keys, lines_requiring_explanation).
    """
    required = get_lines_requiring_explanation(budget_rows)
    expl = explanations or {}
    missing: List[str] = []
    for row in required:
        key = str(row.get("row_index", row.get("account_code", "")))
        text = (expl.get(key) or expl.get(str(row.get("account_code", ""))) or "").strip()
        if not text:
            label = row.get("account_description") or row.get("expense_category") or key
            missing.append(label)
    return len(missing) == 0, missing, required


def merge_explanations_into_rows(
    budget_rows: List[Dict[str, Any]],
    explanations: Optional[Dict[str, str]] = None,
) -> List[Dict[str, Any]]:
    expl = explanations or {}
    merged: List[Dict[str, Any]] = []
    for row in budget_rows or []:
        enriched = enrich_budget_row(row)
        key = str(enriched.get("row_index", enriched.get("account_code", "")))
        alt = str(enriched.get("account_code", ""))
        enriched["variance_explanation"] = (
            expl.get(key) or expl.get(alt) or enriched.get("variance_explanation") or ""
        ).strip()
        merged.append(enriched)
    return merged
