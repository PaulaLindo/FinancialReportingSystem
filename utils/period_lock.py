"""
Period lock helpers — resolve period from sessions and enforce lock on mutating requests.
"""

from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from models.period_models import period_model, FinancialPeriod


def _session_metadata(session) -> Dict[str, Any]:
    return getattr(session, "metadata", None) or {}


def resolve_period_id_from_session(session) -> Optional[str]:
    """Resolve financial period ID from session metadata or reporting period label."""
    md = _session_metadata(session)
    period_id = md.get("period_id")
    if period_id:
        return str(period_id)

    period_name = (md.get("period_name") or "").strip()
    if period_name:
        label = period_name.lower()
        for period in period_model.get_all_periods():
            if period.name.strip().lower() == label:
                return period.id

    reporting_period = (
        getattr(session, "reporting_period", None)
        or md.get("reporting_period")
        or md.get("period")
        or ""
    )
    if reporting_period:
        label = str(reporting_period).strip().lower()
        for period in period_model.get_all_periods():
            if period.name.strip().lower() == label:
                return period.id
            if label and label in period.name.strip().lower():
                return period.id

    fiscal_year = getattr(session, "fiscal_year", None) or md.get("fiscal_year")
    if fiscal_year:
        year = str(fiscal_year).strip()
        matches = [
            p for p in period_model.get_all_periods()
            if year and year in p.name
        ]
        if len(matches) == 1:
            return matches[0].id

    return None


def _parse_iso_datetime(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    try:
        text = str(value).replace("Z", "+00:00")
        parsed = datetime.fromisoformat(text[:26])
        return parsed.replace(tzinfo=None)
    except Exception:
        return None


def session_reference_datetime(session) -> datetime:
    """Best reference instant for matching a submission to a financial period."""
    md = _session_metadata(session)
    for key in ("submitted_at", "created_at"):
        val = md.get(key) or getattr(session, key, None)
        parsed = _parse_iso_datetime(val)
        if parsed:
            return parsed
    return datetime.now()


def resolve_period_id_by_date(session) -> Optional[str]:
    """
    Match session to the financial period whose start/end dates contain the
    submission reference date. Returns None when ambiguous.
    """
    ref = session_reference_datetime(session)
    matches: list[FinancialPeriod] = []
    for period in period_model.get_all_periods():
        start = _parse_iso_datetime(period.start_date)
        end = _parse_iso_datetime(period.end_date)
        if not start or not end:
            continue
        if start <= ref <= end:
            matches.append(period)

    if len(matches) == 1:
        return matches[0].id

    from models.period_models import PeriodStatus

    open_matches = [p for p in matches if p.status == PeriodStatus.OPEN.value]
    if len(open_matches) == 1:
        return open_matches[0].id

    return None


def find_period_id_for_finalization(session) -> Optional[str]:
    """
    Best-effort period for CFO final approval when upload metadata is incomplete.

    Prefer explicit session linkage, date-range match, calendar open period,
    name match, then a single open period (typical demo / single-period setups).
    """
    period_id = resolve_period_id_from_session(session)
    if period_id:
        return period_id

    period_id = resolve_period_id_by_date(session)
    if period_id:
        return period_id

    open_period = find_open_period_for_today()
    if open_period:
        return open_period.id

    md = _session_metadata(session)
    period_name = (md.get("period_name") or "").strip().lower()
    if period_name:
        for period in period_model.get_all_periods():
            if period.name.strip().lower() == period_name:
                return period.id

    open_periods = period_model.get_open_periods()
    if len(open_periods) == 1:
        return open_periods[0].id

    return None


def session_is_cfo_finalized(session) -> bool:
    """True when the session has completed CFO final approval."""
    if not session:
        return False
    from utils.session_workflow import effective_workflow_status

    eff = str(effective_workflow_status(session) or "").lower()
    db = str(getattr(session, "status", "") or "").lower()
    if eff != "approved" and db != "approved":
        return False
    md = _session_metadata(session)
    return bool(md.get("cfo_approval") or md.get("approved_at") or md.get("approved_by"))


def is_period_locked(period: Optional[FinancialPeriod]) -> bool:
    if not period:
        return False
    if getattr(period, "is_locked", False):
        return True
    md = period.metadata or {}
    return bool(md.get("is_locked"))


def period_lock_message(period: Optional[FinancialPeriod]) -> str:
    name = period.name if period else "This period"
    return f"{name} is locked. No further changes are permitted for this reporting period."


def check_session_period_unlocked(session) -> Tuple[bool, str]:
    """Return (allowed, error_message). True when no period or period is not locked."""
    period_id = resolve_period_id_from_session(session)
    if not period_id:
        return True, ""
    period = period_model.get_period(period_id)
    if is_period_locked(period):
        return False, period_lock_message(period)
    return True, ""


def check_period_id_unlocked(period_id: Optional[str]) -> Tuple[bool, str]:
    if not period_id:
        return True, ""
    period = period_model.get_period(period_id)
    if not period:
        return True, ""
    if is_period_locked(period):
        return False, period_lock_message(period)
    return True, ""


def session_period_lock_status(session) -> Dict[str, Any]:
    """Lock status payload for API responses."""
    md = _session_metadata(session)
    if md.get("period_locked"):
        period_id = md.get("period_id") or resolve_period_id_from_session(session)
        return {
            "period_id": period_id,
            "period_locked": True,
            "period_name": md.get("period_name"),
            "locked_at": md.get("period_locked_at") or md.get("locked_at"),
        }
    period_id = resolve_period_id_from_session(session)
    if not period_id:
        return {"period_id": None, "period_locked": False, "period_name": None}
    period = period_model.get_period(period_id)
    locked = is_period_locked(period)
    return {
        "period_id": period_id,
        "period_locked": locked,
        "period_name": period.name if period else None,
        "locked_at": (period.metadata or {}).get("locked_at") if period else None,
    }


def attach_period_to_session_metadata(session, period_id: str) -> None:
    if session.metadata is None:
        session.metadata = {}
    session.metadata["period_id"] = str(period_id)
    try:
        period = period_model.get_period(str(period_id))
        if period:
            session.metadata["period_name"] = period.name
            session.metadata.setdefault("reporting_period", period.name)
    except Exception:
        pass


def infer_document_type_from_session(session_id: str) -> Optional[str]:
    """Infer document type by probing session tables (balance sheet, IS, budget)."""
    if not session_id:
        return None
    try:
        from models.balance_sheet_models import BalanceSheetModel

        if BalanceSheetModel().get_session(session_id):
            return "balance_sheet"
        from models.income_statement_models import IncomeStatementModel

        if IncomeStatementModel().get_session(session_id):
            return "income_statement"
        from models.budget_report_models import BudgetReportModel

        if BudgetReportModel().get_session(session_id):
            return "budget_report"
    except Exception:
        pass
    return None


def find_open_period_for_today() -> Optional[FinancialPeriod]:
    """Best-effort fallback when upload omits period_id."""
    now = datetime.now()
    for period in period_model.get_open_periods():
        try:
            start = datetime.fromisoformat(str(period.start_date).replace("Z", "+00:00")[:19])
            end = datetime.fromisoformat(str(period.end_date).replace("Z", "+00:00")[:19])
            if start.replace(tzinfo=None) <= now <= end.replace(tzinfo=None):
                return period
        except Exception:
            continue
    open_periods = period_model.get_open_periods()
    return open_periods[0] if open_periods else None
