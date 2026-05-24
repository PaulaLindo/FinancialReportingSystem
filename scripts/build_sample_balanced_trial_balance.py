"""Regenerate sample_balanced_trial_balance.xlsx — BS-only trial balance that passes upload + GRAP 1 (SFP)."""
from pathlib import Path

import openpyxl
from openpyxl.styles import Font

# Assets = Liabilities + Equity; debits = credits = 100_000
ROWS = [
    ("1001", "Cash and Bank", 45000, 0),
    ("1002", "Trade Receivables", 25000, 0),
    ("1003", "Inventory", 15000, 0),
    ("1004", "Property, Plant and Equipment", 15000, 0),
    ("2001", "Trade Payables", 0, 22000),
    ("2002", "Accrued Liabilities", 0, 8000),
    ("2003", "Short-term Borrowings", 0, 10000),
    ("3001", "Share Capital", 0, 35000),
    ("3002", "Retained Earnings", 0, 25000),
]

OUT = Path(__file__).resolve().parents[1] / "financial_documents" / "balance_sheets" / "sample_balanced_trial_balance.xlsx"


def main():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Trial Balance"
    headers = ("Account Code", "Account Description", "Debit Balance", "Credit Balance")
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True)
    for row in ROWS:
        ws.append(row)
    total_dr = sum(r[2] for r in ROWS)
    total_cr = sum(r[3] for r in ROWS)
    assert total_dr == total_cr == 100000, (total_dr, total_cr)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    wb.save(OUT)
    print(f"Wrote {OUT} ({len(ROWS)} accounts, debits=credits=R {total_dr:,.0f})")


if __name__ == "__main__":
    main()
