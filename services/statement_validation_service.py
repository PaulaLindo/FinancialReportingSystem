"""GRAP statement validation helpers for review and approval."""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def _account_text(line: Dict[str, Any]) -> str:
    parts = [
        line.get("account_name"),
        line.get("name"),
        line.get("account_desc"),
        line.get("description"),
    ]
    return " ".join(str(p) for p in parts if p).lower()


def _classify_by_account_code(line: Dict[str, Any]) -> Optional[str]:
    """Trial-balance account code ranges: 1xxx assets, 2xxx liabilities, 3xxx equity."""
    code = str(line.get("account_code") or line.get("code") or "").strip()
    if not code or not code[0].isdigit():
        return None
    lead = code[0]
    if lead == "1":
        return "asset"
    if lead == "2":
        return "liability"
    if lead == "3":
        return "equity"
    return None


def _classify_statement_line(line: Dict[str, Any], *, for_balance_sheet: bool) -> Optional[str]:
    """
    Classify a mapped line as asset, liability, equity, revenue, or expense.
    Account nature (name/description) takes precedence over GRAP bucket codes when
    a liability was dropped into an asset category (e.g. borrowings under CA150).
    """
    code = str(line.get("grap_code") or line.get("grap_category") or line.get("category") or "").strip().upper()
    label = str(line.get("grap_category") or line.get("category") or "").lower()
    account_text = _account_text(line)
    text = f"{label} {account_text}".strip()

    if for_balance_sheet:
        by_code = _classify_by_account_code(line)
        if by_code:
            return by_code
        if any(k in text for k in ("borrowing", "payable", "loan", "provision")) or (
            "liabilit" in text and "receivable" not in text
        ):
            return "liability"
        if any(k in text for k in ("equity", "capital", "reserve", "retained", "share")):
            return "equity"
        if code.startswith("CA") or code.startswith("NC"):
            return "asset"
        if code.startswith("CL") or code.startswith("NL"):
            return "liability"
        if code.startswith("EQ"):
            return "equity"
        if any(k in text for k in ("cash", "receivable", "inventory", "investment", "property", "asset", "prepaid")):
            if "liabilit" not in text:
                return "asset"
        return None

    if code.startswith("RV"):
        return "revenue"
    if code.startswith("EX"):
        return "expense"
    if any(k in text for k in ("revenue", "income", "grant")):
        return "revenue"
    if any(k in text for k in ("expense", "cost", "expenditure")):
        return "expense"
    return None


def _line_balance_for_sfp(line: Dict[str, Any], kind: str) -> float:
    """Signed balance for SFP: assets debit-normal; liabilities and equity credit-normal."""
    debit = line.get("debit_balance")
    if debit is None:
        debit = line.get("debit")
    credit = line.get("credit_balance")
    if credit is None:
        credit = line.get("credit")
    if debit is not None or credit is not None:
        d = float(debit or 0)
        c = float(credit or 0)
        if kind == "asset":
            return d - c
        return c - d
    raw = _amount(line)
    if kind in ("liability", "equity"):
        return abs(raw)
    return raw


def validate_balance_sheet(lines: List[Dict[str, Any]], *, tolerance: float = 0.01) -> Dict[str, Any]:
    """Check assets ≈ liabilities + equity from mapped line amounts (GRAP SFP)."""
    assets = 0.0
    liabilities = 0.0
    equity = 0.0
    for line in lines or []:
        kind = _classify_statement_line(line, for_balance_sheet=True)
        if kind not in ("asset", "liability", "equity"):
            continue
        amount = _line_balance_for_sfp(line, kind)
        if kind == "asset":
            assets += amount
        elif kind == "liability":
            liabilities += amount
        elif kind == "equity":
            equity += amount
    le = liabilities + equity
    diff = abs(assets - le)
    balanced = diff <= tolerance
    return {
        "check": "balance_sheet_equation",
        "passed": balanced,
        "message": "Assets equal liabilities plus equity"
        if balanced
        else f"Out of balance by {diff:,.2f}",
        "details": {"assets": assets, "liabilities": liabilities, "equity": equity, "difference": diff},
    }


def mapped_lines_from_metadata(metadata: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Normalized mapped rows from session metadata (submit / mapping / grap_mapping)."""
    md = metadata or {}
    raw = md.get("mapped_data") or md.get("mapped_accounts") or md.get("grap_mapping") or []
    lines: List[Dict[str, Any]] = []

    if isinstance(raw, dict):
        for key, val in raw.items():
            if isinstance(val, list):
                for item in val:
                    if isinstance(item, dict):
                        row = dict(item)
                        row.setdefault("grap_code", row.get("grap_code") or key)
                        row.setdefault("grap_category", row.get("grap_category") or key)
                        lines.append(row)
                continue
            if isinstance(val, dict):
                row = dict(val)
                row.setdefault("grap_code", row.get("grap_code") or key)
                row.setdefault("grap_category", row.get("grap_category") or key)
                lines.append(row)
        return lines

    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, dict):
                row = dict(item)
                if not row.get("grap_category") and row.get("grap_code"):
                    row["grap_category"] = row["grap_code"]
                lines.append(row)
        return lines
    return []


def compute_sfp_totals_from_lines(lines: List[Dict[str, Any]], *, tolerance: float = 0.01) -> Dict[str, Any]:
    """Totals used for review UI and CFO approve — matches validate_balance_sheet."""
    bs = validate_balance_sheet(lines, tolerance=tolerance)
    details = bs.get("details") or {}
    assets = float(details.get("assets") or 0)
    liabilities = float(details.get("liabilities") or 0)
    equity = float(details.get("equity") or 0)
    diff = float(details.get("difference") or 0)
    return {
        "assets": assets,
        "liabilities": liabilities,
        "equity": equity,
        "liabilities_plus_equity": liabilities + equity,
        "difference": diff,
        "balanced": bool(bs.get("passed")),
        "message": bs.get("message"),
    }


def _trial_balance_statement_section(line: Dict[str, Any]) -> str:
    """Trial-balance account code ranges: 1–3 SFP, 4–5 performance."""
    code = str(line.get("account_code") or line.get("code") or "").strip()
    if not code or not code[0].isdigit():
        return "unknown"
    lead = code[0]
    if lead in ("1", "2", "3"):
        return "balance_sheet"
    if lead in ("4", "5"):
        return "performance"
    return "unknown"


def group_mapped_accounts_for_statements(mapped_accounts: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Build SFP / SFPER account buckets for display and stored financial_statements.

    Uses account code ranges (1/2/3 vs 4/5) so P&L lines are not shown on the SFP
    when mis-mapped to CA* buckets (e.g. COGS on CA130).
    """
    assets: List[Dict[str, Any]] = []
    liabilities: List[Dict[str, Any]] = []
    equity: List[Dict[str, Any]] = []
    revenue: List[Dict[str, Any]] = []
    expenses: List[Dict[str, Any]] = []

    for account in mapped_accounts or []:
        section = _trial_balance_statement_section(account)
        if section == "performance":
            kind = _classify_statement_line(account, for_balance_sheet=False)
            code = str(account.get("account_code") or account.get("code") or "").strip()
            if kind == "revenue" or (kind is None and code.startswith("4")):
                revenue.append(account)
            else:
                expenses.append(account)
            continue

        kind = _classify_statement_line(account, for_balance_sheet=True)
        if kind == "asset":
            assets.append(account)
        elif kind == "liability":
            liabilities.append(account)
        elif kind == "equity":
            equity.append(account)

    sfp_lines = assets + liabilities + equity
    totals = compute_sfp_totals_from_lines(sfp_lines)
    total_revenue = sum(abs(_amount(a)) for a in revenue)
    total_expenses = sum(abs(_amount(a)) for a in expenses)

    return {
        "statement_of_financial_position": {
            "assets": {"accounts": assets, "total": totals["assets"]},
            "liabilities": {"accounts": liabilities, "total": totals["liabilities"]},
            "equity": {"accounts": equity, "total": totals["equity"]},
            "equation": totals,
        },
        "statement_of_financial_performance": {
            "revenue": {"accounts": revenue, "total": total_revenue},
            "expenses": {"accounts": expenses, "total": total_expenses},
            "surplus": total_revenue - total_expenses,
        },
    }


def validate_session_metadata(session_metadata: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Run lightweight checks from session metadata when full lines are unavailable."""
    meta = session_metadata or {}
    results: List[Dict[str, Any]] = []
    mapped = meta.get("mapped_data") or meta.get("total_mapped_accounts")
    results.append(
        {
            "check": "mapping_present",
            "passed": bool(mapped),
            "message": "Account mapping completed" if mapped else "No mapped accounts on session",
        }
    )
    if meta.get("balance_check_passed") is not None:
        passed = bool(meta.get("balance_check_passed"))
        results.append(
            {
                "check": "trial_balance_balanced",
                "passed": passed,
                "message": "Trial balance debits equal credits"
                if passed
                else "Trial balance is not balanced",
            }
        )
    return results


def validate_income_statement(lines: List[Dict[str, Any]], *, tolerance: float = 0.01) -> Dict[str, Any]:
    """Simplified: revenue - expenses ≈ net surplus/deficit (GRAP performance)."""
    revenue = 0.0
    expenses = 0.0
    for line in lines or []:
        kind = _classify_statement_line(line, for_balance_sheet=False)
        amt = abs(_amount(line))
        if kind == "revenue":
            revenue += amt
        elif kind == "expense":
            expenses += amt
    net = revenue - expenses
    has_revenue = revenue > 0
    has_expenses = expenses > 0
    passed = has_revenue or has_expenses
    message = (
        f"Revenue {revenue:,.2f}, expenses {expenses:,.2f}, net {net:,.2f}"
        if passed
        else "No revenue or expense lines detected"
    )
    return {
        "check": "income_statement_totals",
        "passed": passed,
        "message": message,
        "details": {"revenue": revenue, "expenses": expenses, "net": net},
    }


def validate_negative_balances(
    lines: List[Dict[str, Any]],
    *,
    document_type: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Flag unexpected negative amounts.

    Balance sheet trial balances store credit-normal accounts (liabilities, equity)
    with negative net amounts (debit − credit). Those are valid and skipped here.
    """
    dt = (document_type or "").strip().lower()
    if dt == "balance_sheet":
        return {
            "check": "negative_balances",
            "passed": True,
            "message": "Credit balances on liability and equity accounts are allowed",
            "details": {"skipped": "balance_sheet_trial_balance"},
        }

    warnings = []
    for line in lines or []:
        amt = _amount(line)
        cat = (line.get("grap_category") or line.get("category") or "line").lower()
        if amt < 0:
            code = line.get("account_code") or line.get("Account Code") or "?"
            warnings.append(f"{code} ({cat}): {amt:,.2f}")
    return {
        "check": "negative_balances",
        "passed": len(warnings) == 0,
        "message": "No negative balances" if not warnings else f"{len(warnings)} line(s) with negative amounts",
        "details": {"warnings": warnings[:20]},
    }


def validate_grap_categories(lines: List[Dict[str, Any]]) -> Dict[str, Any]:
    missing = 0
    for line in lines or []:
        cat = (line.get("grap_category") or line.get("category") or "").strip()
        if not cat or cat.lower() in ("unmapped", "unknown"):
            missing += 1
    return {
        "check": "grap_mapping_complete",
        "passed": missing == 0,
        "message": "All lines mapped to GRAP categories"
        if missing == 0
        else f"{missing} line(s) missing GRAP category",
        "details": {"unmapped_count": missing},
    }


def _parse_iso_datetime(value: Any):
    from datetime import datetime

    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value
    text = str(value).replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def sla_status_for_session(
    session_metadata: Optional[Dict[str, Any]],
    document_type: str,
) -> Optional[Dict[str, Any]]:
    meta = session_metadata or {}
    submitted = meta.get("submitted_at")
    if not submitted and isinstance(meta.get("submission"), dict):
        submitted = meta["submission"].get("at")
    submitted_dt = _parse_iso_datetime(submitted)
    if not submitted_dt:
        return None
    try:
        from datetime import datetime

        from services.approval_rules_engine import approval_rules_engine

        req = approval_rules_engine.get_approval_requirements(document_type)
        now = datetime.now(submitted_dt.tzinfo) if submitted_dt.tzinfo else datetime.now()
        hours = max(0, int((now - submitted_dt).total_seconds() / 3600))
        breached = hours > req.sla_hours
        submitted_naive = submitted_dt.replace(tzinfo=None) if submitted_dt.tzinfo else submitted_dt
        at_risk = approval_rules_engine.is_sla_breached(submitted_naive, document_type)
        return {
            "sla_hours": req.sla_hours,
            "hours_elapsed": hours,
            "breached": breached,
            "at_risk": at_risk and not breached,
            "submitted_at": submitted_dt.isoformat(),
        }
    except Exception:
        return None


def validate_for_review(
    *,
    document_type: str,
    lines: Optional[List[Dict[str, Any]]] = None,
    session_metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = list(validate_session_metadata(session_metadata))
    if lines:
        checks.append(validate_grap_categories(lines))
        checks.append(validate_negative_balances(lines, document_type=document_type))
    if document_type == "balance_sheet" and lines:
        bs = validate_balance_sheet(lines)
        details = bs.get("details") or {}
        if details.get("assets", 0) == 0 and details.get("liabilities", 0) == 0 and details.get("equity", 0) == 0:
            checks.append({
                "check": "balance_sheet_equation",
                "passed": bool((session_metadata or {}).get("balance_check_passed")),
                "message": "Trial balance used for SFP check (map accounts to CA/CL/EQ categories)",
            })
        else:
            checks.append(bs)
    if document_type == "income_statement" and lines:
        checks.append(validate_income_statement(lines))
    passed = all(c.get("passed") for c in checks) if checks else True
    sla = sla_status_for_session(session_metadata, document_type)
    return {
        "document_type": document_type,
        "valid": passed,
        "checks": checks,
        "score": round(100 * sum(1 for c in checks if c.get("passed")) / max(len(checks), 1)),
        "sla": sla,
    }


def _amount(line: Dict[str, Any]) -> float:
    for key in ("current_amount", "amount", "net_balance", "balance", "value"):
        if key in line and line[key] is not None:
            try:
                return float(line[key])
            except (TypeError, ValueError):
                continue
    return 0.0
