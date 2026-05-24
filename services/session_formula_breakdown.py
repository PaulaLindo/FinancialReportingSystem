"""
Session-scoped formula / calculation breakdown for universal document review.
Builds transparency payloads from get_session_summary() output (Supabase-backed sessions).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from urllib.parse import quote


def _review_navigation_links(session_id: str, document_type: str) -> Dict[str, str]:
    """Same-origin URLs (browser tab uses the user's login cookie)."""
    sid = quote(str(session_id).strip(), safe="")
    dt = quote(str(document_type).strip(), safe="")
    if not sid or not dt:
        return {}
    return {
        "session_json": f"/api/universal/session/{sid}?document_type={dt}",
        "statement_review": f"/approvals?review=statement&transaction={sid}&type={dt}",
    }


def _attach_session_variable_links(
    variables: List[Dict[str, Any]],
    session_id: str,
    doc_type: str,
) -> None:
    """Add same-origin links only where the target is clearly useful (avoid generic /dashboard, /reports)."""
    links = _review_navigation_links(session_id, doc_type)
    if not links:
        return
    for v in variables:
        name = str(v.get("name") or "")
        if name == "Document upload session":
            v["linkHref"] = links["session_json"]
            v["linkLabel"] = "Open saved submission data (JSON)"
        elif name == "Document type":
            v["linkHref"] = links["statement_review"]
            v["linkLabel"] = "Open full-page statement review"


def _num(v: Any) -> Optional[float]:
    if v is None:
        return None
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(str(v).replace(",", "").replace("R", "").strip())
    except (TypeError, ValueError):
        return None


def _sum_block_accounts(block: Any, *, use_abs: bool = False) -> float:
    if not block or not isinstance(block, dict):
        return 0.0
    accounts = block.get("accounts") or []
    total = 0.0
    for a in accounts:
        if not isinstance(a, dict):
            continue
        n = _num(a.get("net_balance"))
        if n is None:
            n = _num(a.get("amount"))
        if n is not None:
            total += abs(n) if use_abs else n
    return total


def _append_grap_approval_calculations(
    summary: Dict[str, Any],
    push: Any,
    seen: set,
) -> None:
    """
    Calculations aligned with clerk mapping, review UI, and CFO approve
    (metadata.mapped_data + statement_validation_service).
    """
    from services.statement_validation_service import (
        _classify_statement_line,
        _trial_balance_statement_section,
        compute_sfp_totals_from_lines,
        mapped_lines_from_metadata,
        validate_income_statement,
    )

    md = summary.get("metadata") or {}
    if not isinstance(md, dict):
        return
    lines = mapped_lines_from_metadata(md)
    if not lines:
        return

    doc_t = str(summary.get("document_type") or "").strip().lower()

    if doc_t == "balance_sheet":
        sfp_lines = [
            ln
            for ln in lines
            if _trial_balance_statement_section(ln) != "performance"
            and str(ln.get("grap_code") or ln.get("grap_category") or "").strip()
        ]
        totals = compute_sfp_totals_from_lines(sfp_lines)
        push(
            "grap-mapped-assets",
            "GRAP 1 (SFP) — Assets (approval check)",
            "Σ classified asset balances (1xxx / CA·NC; debit-normal)",
            totals["assets"],
            True,
        )
        push(
            "grap-mapped-liabilities",
            "GRAP 1 (SFP) — Liabilities (approval check)",
            "Σ classified liability balances (2xxx / CL·NL; credit-normal)",
            totals["liabilities"],
            True,
        )
        push(
            "grap-mapped-equity",
            "GRAP 1 (SFP) — Equity (approval check)",
            "Σ classified equity balances (3xxx / EQ; credit-normal)",
            totals["equity"],
            True,
        )
        push(
            "grap-mapped-le",
            "GRAP 1 (SFP) — Liabilities + Equity",
            "Liabilities + Equity",
            totals["liabilities_plus_equity"],
            True,
        )
        push(
            "grap-mapped-diff",
            "GRAP 1 (SFP) — Accounting equation",
            "Assets − (Liabilities + Equity)",
            totals["difference"],
            totals["balanced"],
        )

        rev = exp = 0.0
        for ln in lines:
            if _trial_balance_statement_section(ln) != "performance":
                continue
            kind = _classify_statement_line(ln, for_balance_sheet=False)
            amt = abs(_num(ln.get("net_balance")) or _num(ln.get("amount")) or 0)
            if kind == "revenue":
                rev += amt
            elif kind == "expense":
                exp += amt
            else:
                code = str(ln.get("account_code") or ln.get("code") or "").strip()
                if code.startswith("4"):
                    rev += amt
                else:
                    exp += amt
        if rev or exp:
            push(
                "grap-mapped-revenue",
                "SFPER — Revenue (mapped P&L lines)",
                "Σ |amount| for revenue / 4xxx on combined trial balance",
                rev,
                rev > 0,
            )
            push(
                "grap-mapped-expenses",
                "SFPER — Expenses (mapped P&L lines)",
                "Σ |amount| for expense / 5xxx on combined trial balance",
                exp,
                exp > 0,
            )
            push(
                "grap-mapped-surplus",
                "SFPER — Net surplus / (deficit)",
                "Revenue − Expenses",
                rev - exp,
                rev > 0 or exp > 0,
            )

    elif doc_t == "income_statement":
        perf = validate_income_statement(lines)
        details = perf.get("details") or {}
        rev = float(details.get("revenue") or 0)
        exp = float(details.get("expenses") or 0)
        net = float(details.get("net") or 0)
        push(
            "grap-mapped-revenue",
            "GRAP 1 (Performance) — Revenue",
            "Σ |amount| for revenue-classified mapped lines",
            rev,
            rev > 0,
        )
        push(
            "grap-mapped-expenses",
            "GRAP 1 (Performance) — Expenses",
            "Σ |amount| for expense-classified mapped lines",
            exp,
            exp > 0,
        )
        push(
            "grap-mapped-surplus",
            "GRAP 1 (Performance) — Net",
            "Revenue − Expenses",
            net,
            bool(perf.get("passed")),
        )


def compute_calculations_from_summary(summary: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Derive calculation rows (aligned with financial-statement-review.js merge logic)."""
    calcs: List[Dict[str, Any]] = []
    seen = set()

    def push(
        cid: str,
        desc: str,
        formula: str,
        result: Any,
        verified: bool = False,
        *,
        result_kind: str = "currency",
    ) -> None:
        if not cid or cid in seen:
            return
        seen.add(cid)
        calcs.append(
            {
                "id": cid,
                "description": desc,
                "formula": formula,
                "result": result,
                "verified": bool(verified),
                "result_kind": result_kind,
            }
        )

    fs = summary.get("financial_statements") or {}
    sfp = fs.get("statement_of_financial_position") or {}
    perf = fs.get("statement_of_financial_performance") or {}

    surplus = _num(perf.get("surplus")) if isinstance(perf, dict) else None
    if surplus is not None:
        push(
            "surplus",
            "Surplus / (deficit) for the period",
            "Total revenue − Total expenses",
            surplus,
            False,
        )

    if isinstance(sfp, dict) and sfp:
        assets_t = _num((sfp.get("assets") or {}).get("total"))
        liab_t = _num((sfp.get("liabilities") or {}).get("total"))
        eq_t = _num((sfp.get("equity") or {}).get("total"))
        if assets_t is not None:
            push("sfp-assets", "SFP — total assets", "statement_of_financial_position.assets.total", assets_t, True)
        if liab_t is not None:
            push("sfp-liabilities", "SFP — total liabilities", "statement_of_financial_position.liabilities.total", liab_t, True)
        if eq_t is not None:
            push("sfp-equity", "SFP — total equity", "statement_of_financial_position.equity.total", eq_t, True)
        if assets_t is not None and liab_t is not None and eq_t is not None:
            rhs = liab_t + eq_t
            diff = assets_t - rhs
            push(
                "sfp-balance",
                "SFP — accounting equation",
                "Assets − (Liabilities + Equity)",
                diff,
                abs(diff) < 0.02,
            )

    if isinstance(perf, dict) and perf:
        rev = _sum_block_accounts(perf.get("revenue"), use_abs=True)
        exp = _sum_block_accounts(perf.get("expenses"), use_abs=True)
        rev_block = perf.get("revenue") or {}
        exp_block = perf.get("expenses") or {}
        if rev != 0 or (isinstance(rev_block, dict) and rev_block.get("accounts")):
            push("sfper-revenue", "SFPER — total revenue", "Sum of revenue accounts", rev, True)
        if exp != 0 or (isinstance(exp_block, dict) and exp_block.get("accounts")):
            push("sfper-expenses", "SFPER — total expenses", "Sum of expense accounts", exp, True)

    md = summary.get("metadata") or {}
    if not isinstance(md, dict):
        md = {}
    gm = md.get("grap_mapping") or {}
    if isinstance(gm, dict):
        map_data = gm.get("mapping_data")
        if isinstance(map_data, list) and len(map_data):
            push(
                "mapping-rows",
                "Mapped trial-balance rows",
                "metadata.grap_mapping.mapping_data.length",
                len(map_data),
                True,
                result_kind="count",
            )

    tr = summary.get("total_rows")
    if tr is not None and str(tr).strip() != "":
        n = _num(tr)
        if n is not None:
            push("session-rows", "Uploaded data rows", "session.total_rows", int(n), True, result_kind="count")

    doc_t = str(summary.get("document_type") or "")
    if doc_t == "budget_report":
        tb = _num(summary.get("total_budget"))
        ta = _num(summary.get("total_actual"))
        tv = _num(summary.get("total_variance"))
        if tb is not None:
            push(
                "budget-total-budget",
                "Budget — total budget (session)",
                "session.total_budget",
                tb,
                False,
            )
        if ta is not None:
            push(
                "budget-total-actual",
                "Budget — total actual (session)",
                "session.total_actual",
                ta,
                False,
            )
        if tv is not None:
            push(
                "budget-total-variance",
                "Budget — variance (actual − budget)",
                "session.total_variance",
                tv,
                False,
            )
        br = summary.get("budget_rows")
        if isinstance(br, list) and len(br) > 0:
            push(
                "budget-data-rows",
                "Budget line items in session payload",
                "len(budget_rows)",
                len(br),
                True,
                result_kind="count",
            )

    if doc_t == "income_statement":
        trv = _num(summary.get("total_revenue"))
        tex = _num(summary.get("total_expenses"))
        tni = _num(summary.get("net_income"))
        if trv is not None:
            push("is-total-revenue", "Income — total revenue (session)", "session.total_revenue", trv, False)
        if tex is not None:
            push("is-total-expenses", "Income — total expenses (session)", "session.total_expenses", tex, False)
        if tni is not None:
            push("is-net-income", "Income — net income (session)", "session.net_income", tni, False)
        ir = summary.get("income_rows")
        if isinstance(ir, list) and len(ir) > 0:
            push(
                "income-data-rows",
                "Income line items in session payload",
                "len(income_rows)",
                len(ir),
                True,
                result_kind="count",
            )

    mac = summary.get("mapped_accounts_count")
    if mac is not None and str(mac).strip() != "":
        n = _num(mac)
        if n is not None:
            push(
                "session-mapped-count",
                "Mapped accounts (session summary)",
                "session.mapped_accounts_count",
                int(n),
                False,
                result_kind="count",
            )

    # Top-level totals from flexible_balance_sheet_service summary (when present)
    for key, cid, desc, formula in (
        ("total_assets", "summary-total-assets", "Summary — total assets", "processing summary field"),
        ("total_liabilities", "summary-total-liab", "Summary — total liabilities", "processing summary field"),
        ("total_equity", "summary-total-equity", "Summary — total equity", "processing summary field"),
        ("total_revenue", "summary-total-revenue", "Summary — total revenue", "processing summary field"),
        ("total_expenses", "summary-total-expenses", "Summary — total expenses", "processing summary field"),
        ("surplus_deficit", "summary-surplus", "Summary — surplus / deficit", "processing summary field"),
    ):
        val = _num(summary.get(key))
        if val is not None and cid not in seen:
            push(cid, desc, formula, val, False)

    _append_grap_approval_calculations(summary, push, seen)

    ver_map = md.get("calculation_verifications") or {}
    if isinstance(ver_map, dict):
        for c in calcs:
            rec = ver_map.get(str(c["id"]))
            if isinstance(rec, dict) and rec.get("verified"):
                c["verified"] = True

    return calcs


def _fmt_money(n: float) -> str:
    return f"R{n:,.2f}"


def _fmt_step_result(res: Any, result_kind: str) -> str:
    """Format a step result — counts must not use currency formatting."""
    if result_kind == "count":
        if isinstance(res, (int, float)):
            n = int(res)
            return f"{n} row{'s' if n != 1 else ''}"
        return str(res)
    if isinstance(res, (int, float)):
        return _fmt_money(float(res))
    return str(res)


def _pick_final_result(calcs: List[Dict[str, Any]]) -> str:
    """Prefer a meaningful monetary total, not row counts."""
    pref = (
        "grap-mapped-diff",
        "sfp-balance",
        "grap-mapped-surplus",
        "surplus",
        "budget-total-variance",
        "is-net-income",
        "budget-total-actual",
        "budget-total-budget",
    )
    for pid in pref:
        c = next((x for x in calcs if x.get("id") == pid), None)
        if not c:
            continue
        if c.get("result_kind", "currency") != "currency":
            continue
        r = c.get("result")
        if not isinstance(r, (int, float)):
            continue
        out = _fmt_money(float(r))
        if pid == "surplus":
            out += " (surplus / deficit)"
        return out
    for c in reversed(calcs):
        if c.get("result_kind", "currency") == "count":
            continue
        r = c.get("result")
        if isinstance(r, (int, float)):
            return _fmt_money(float(r))
    return "—"


def build_formula_breakdown_response(
    summary: Dict[str, Any],
    scope: str = "session",
    *,
    calc_id: Optional[str] = None,
    account_code: Optional[str] = None,
    grap_code: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Return a payload compatible with formula-modal.js updateModalContent(data, ...).
    """
    calcs = compute_calculations_from_summary(summary)
    md = summary.get("metadata") or {}
    if not isinstance(md, dict):
        md = {}
    period = (
        summary.get("reporting_period")
        or md.get("period")
        or md.get("reporting_period")
        or "FY 2025-2026"
    )
    session_id = summary.get("session_id") or ""
    doc_type = summary.get("document_type") or "document"
    filename = summary.get("filename") or ""

    variables: List[Dict[str, Any]] = [
        {
            "name": "Document upload session",
            "detail": (
                "Stored record for this file submission—upload, mappings, and totals in our database. "
                "This is not your browser login session."
            ),
            "value": str(session_id),
            "source": "session",
            "sourceLabel": "Submission record",
        },
        {
            "name": "Document type",
            "detail": (
                "Same submission as above. Opens the full-page statement review for this session "
                "(not a different document)."
            ),
            "value": str(doc_type),
            "source": "session",
            "sourceLabel": "Type",
        },
        {
            "name": "File",
            "detail": "Original file name from the submission record (no generic file-management link).",
            "value": str(filename),
            "source": "session",
            "sourceLabel": "Upload",
        },
        {
            "name": "Period",
            "detail": "Reporting period label for this submission (not a dashboard filter).",
            "value": str(period),
            "source": "session",
            "sourceLabel": "Reporting",
        },
    ]
    _attach_session_variable_links(variables, str(session_id), str(doc_type))

    if scope == "line" and account_code:
        return _build_line_breakdown(summary, variables, period, account_code, grap_code)

    if scope == "calculation" and calc_id:
        match = next((c for c in calcs if str(c.get("id")) == str(calc_id)), None)
        if not match:
            return _empty_payload(
                variables,
                period,
                f"No calculation with id «{calc_id}» for this session.",
            )
        rk = match.get("result_kind", "currency")
        fr = match.get("result")
        res_s = _fmt_step_result(fr, rk)
        steps = [
            {
                "formula": f"{match['description']} — {match['formula']}",
                "result": res_s,
            }
        ]
        final = res_s
        return {
            "grapReference": str(grap_code or "GRAP"),
            "assetClass": "Calculation detail (server)",
            "formula": match.get("formula") or match.get("description") or "Derived from session summary",
            "variables": variables,
            "steps": steps,
            "finalResult": final,
            "accessMode": "review",
            "processingStatus": "review",
            "itemName": match.get("description") or str(calc_id),
        }

    # scope == session (default): full step list
    steps = []
    for c in calcs:
        res = c.get("result")
        rk = c.get("result_kind", "currency")
        res_s = _fmt_step_result(res, rk)
        steps.append({"formula": f"{c.get('description', '')} — {c.get('formula', '')}", "result": res_s})

    if not steps:
        steps.append(
            {
                "formula": "No structured financial_statements or totals on this session yet",
                "result": "—",
            }
        )

    final_result = _pick_final_result(calcs)

    return {
        "grapReference": "GRAP",
        "assetClass": "Session review (server-derived)",
        "formula": (
            "Values are computed on the server from saved session data. "
            "GRAP 1 (SFP) rows labelled «approval check» use the same rules as clerk submit "
            "and CFO final approve (mapped_data, account-code sections, A = L + E)."
        ),
        "variables": variables,
        "steps": steps,
        "finalResult": final_result,
        "accessMode": "review",
        "processingStatus": "review",
        "itemName": "Session calculations",
    }


def _mapping_workspace_href(session_id: str) -> str:
    from utils.session_workflow import mapping_workspace_url

    return mapping_workspace_url(session_id)


def _build_line_breakdown(
    summary: Dict[str, Any],
    variables: List[Dict[str, Any]],
    period: str,
    account_code: str,
    grap_code: Optional[str],
) -> Dict[str, Any]:
    md = summary.get("metadata") or {}
    if not isinstance(md, dict):
        md = {}
    from services.statement_validation_service import (
        _classify_statement_line,
        _line_balance_for_sfp,
        _trial_balance_statement_section,
        mapped_lines_from_metadata,
    )

    rows = mapped_lines_from_metadata(md)
    match = None
    want = str(account_code).strip()
    for m in rows:
        ac = str(m.get("tb_account") or m.get("account_code") or m.get("code") or "").strip()
        if ac == want:
            match = m
            break

    session_id = str(summary.get("session_id") or "").strip()
    map_href = _mapping_workspace_href(session_id)

    variables.append({"name": "Account code", "value": str(account_code), "source": "tb", "sourceLabel": "Trial balance"})
    if grap_code:
        variables.append({"name": "GRAP code", "value": str(grap_code), "source": "mapping", "sourceLabel": "GRAP"})

    links = _review_navigation_links(session_id, str(summary.get("document_type") or ""))
    if links:
        for v in variables:
            if v.get("name") == "Account code":
                v["linkHref"] = links["session_json"]
                v["linkLabel"] = "Open saved submission data (JSON)"
                break
        for v in variables:
            if v.get("name") == "GRAP code":
                v["linkHref"] = links["statement_review"]
                v["linkLabel"] = "Open full-page statement review"
                break

    if not match:
        if map_href:
            variables.append(
                {
                    "name": "Mapping workspace",
                    "detail": "No row matched this account_code in metadata.grap_mapping.mapping_data. Open mapping to attach or correct the account.",
                    "value": "—",
                    "source": "session",
                    "sourceLabel": "Process",
                    "linkHref": map_href,
                    "linkLabel": "Open mapping workspace",
                }
            )
        return {
            "grapReference": str(grap_code or "GRAP"),
            "assetClass": "Line item (server)",
            "formula": "No mapping row found for this account_code in session metadata.grap_mapping.mapping_data.",
            "variables": variables,
            "steps": [{"formula": "Lookup mapping_data by tb_account / account_code", "result": "Not found"}],
            "finalResult": "—",
            "showFinalBand": False,
            "accessMode": "review",
            "processingStatus": "review",
            "itemName": f"Account {account_code}",
        }

    amt = _num(match.get("net_balance"))
    if amt is None:
        amt = _num(match.get("amount")) or _num(match.get("balance"))
    grap = match.get("grap_code") or match.get("grap_line_item") or grap_code or "—"
    grap_nm = match.get("grap_name") or match.get("description") or match.get("account_desc") or "—"
    doc_t = str(summary.get("document_type") or "").strip().lower()
    tb_section = _trial_balance_statement_section(match)
    kind = _classify_statement_line(match, for_balance_sheet=(doc_t == "balance_sheet"))
    if amt is None and map_href:
        variables.append(
            {
                "name": "Mapping workspace",
                "detail": "This mapping row has no amount/balance saved; totals cannot be derived until the clerk processes or updates mapping.",
                "value": "—",
                "source": "session",
                "sourceLabel": "Process",
                "linkHref": map_href,
                "linkLabel": "Open mapping workspace",
            }
        )

    amt_label = _fmt_money(float(amt)) if amt is not None else "Missing (no amount/balance on mapping row)."
    section_note = (
        "P&L account (4xxx/5xxx) — on Statement of Financial Performance, excluded from SFP A = L + E"
        if tb_section == "performance"
        else f"Trial-balance section: {tb_section or 'unknown'}"
    )
    class_note = f"GRAP classification for equation: {kind or 'unclassified'}"
    if kind in ("asset", "liability", "equity") and amt is not None:
        signed = _line_balance_for_sfp(match, kind)
        class_note += f" → contributes R{_fmt_money(signed)} to {kind} total"
    steps = [
        {"formula": f"GRAP category — {grap_nm} ({grap})", "result": str(match.get("grap_code") or grap_code or "—")},
        {"formula": section_note, "result": "—"},
        {"formula": class_note, "result": "—"},
        {"formula": "Amount (net_balance or amount on mapping row)", "result": amt_label},
    ]
    final = _fmt_money(float(amt)) if amt is not None else "—"
    return {
        "grapReference": str(grap),
        "assetClass": "Line item (server)",
        "formula": "Trial balance account mapped to GRAP for this upload session.",
        "variables": variables,
        "steps": steps,
        "finalResult": final,
        "showFinalBand": amt is not None,
        "accessMode": "review",
        "processingStatus": "review",
        "itemName": f"Account {account_code}",
    }


def _empty_payload(variables: List[Dict[str, Any]], period: str, message: str) -> Dict[str, Any]:
    return {
        "grapReference": "GRAP",
        "assetClass": "Session",
        "formula": message,
        "variables": variables,
        "steps": [{"formula": message, "result": "—"}],
        "finalResult": "—",
        "accessMode": "review",
        "processingStatus": "review",
        "itemName": "Calculation",
    }
