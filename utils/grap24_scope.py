"""
GRAP 24 scope — Statement of Comparison of Budget and Actual Amounts.

See also utils.grap_standards_scope for balance sheet (GRAP 1 / SFP) and
income statement (GRAP 1 / performance) rules.
"""

from typing import FrozenSet

GRAP24_DOCUMENT_TYPES: FrozenSet[str] = frozenset({"budget_report"})


def grap24_applies_to(document_type: str) -> bool:
    return (document_type or "").strip().lower() in GRAP24_DOCUMENT_TYPES
