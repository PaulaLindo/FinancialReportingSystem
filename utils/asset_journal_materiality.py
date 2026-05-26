"""
Materiality rules for GRAP 17 asset journal escalation (FM → CFO).

Routine useful-life reviews stay with Finance Manager.
Disposals and material impairments require CFO sign-off after FM review.
"""

from __future__ import annotations

import os
from typing import Any, Dict

DEFAULT_MATERIALITY_THRESHOLD = 100_000.0


def materiality_threshold() -> float:
    raw = os.environ.get('ASSET_JOURNAL_MATERIALITY_THRESHOLD', DEFAULT_MATERIALITY_THRESHOLD)
    try:
        return max(0.0, float(raw))
    except (TypeError, ValueError):
        return DEFAULT_MATERIALITY_THRESHOLD


def journal_materiality_amount(journal: Dict[str, Any]) -> float:
    """Amount used for escalation comparison (impairment / disposal proceeds)."""
    jtype = (journal.get('journal_type') or '').strip()
    amount = float(journal.get('amount') or 0)
    meta = journal.get('metadata') or {}

    if jtype == 'impairment':
        return max(amount, float(meta.get('impairment_amount') or 0))
    if jtype == 'disposal':
        return max(
            amount,
            float(meta.get('disposal_proceeds') or 0),
            float(meta.get('carrying_value_at_disposal') or meta.get('carrying_value_before') or 0),
        )
    return 0.0


def requires_cfo_escalation(journal: Dict[str, Any]) -> bool:
    jtype = (journal.get('journal_type') or '').strip()
    if jtype == 'useful_life_review':
        return False
    if jtype == 'disposal':
        return True
    if jtype == 'impairment':
        return journal_materiality_amount(journal) >= materiality_threshold()
    return False


def escalation_reason_label(journal: Dict[str, Any]) -> str:
    jtype = (journal.get('journal_type') or '').strip()
    if jtype == 'disposal':
        return 'Disposal requires CFO sign-off'
    if jtype == 'impairment':
        threshold = materiality_threshold()
        amount = journal_materiality_amount(journal)
        return f'Impairment R {amount:,.2f} meets materiality threshold (R {threshold:,.2f})'
    return 'CFO sign-off required'
