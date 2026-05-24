import unittest
from types import SimpleNamespace

from services.grap_compliance_service import run_session_grap_compliance
from services.statement_validation_service import group_mapped_accounts_for_statements
from utils.grap_standards_scope import (
    grap24_applies_to,
    statement_compliance_applies_to,
    submit_review_button_label,
    submit_success_message,
    standard_label_for_document,
)


class GrapStandardsScopeTests(unittest.TestCase):
    def test_grap24_only_budget(self):
        self.assertTrue(grap24_applies_to("budget_report"))
        self.assertFalse(grap24_applies_to("balance_sheet"))
        self.assertFalse(statement_compliance_applies_to("budget_report"))

    def test_statement_compliance_bs_is(self):
        self.assertTrue(statement_compliance_applies_to("balance_sheet"))
        self.assertTrue(statement_compliance_applies_to("income_statement"))

    def test_submit_labels_by_document_type(self):
        self.assertIn("GRAP 24", submit_review_button_label("budget_report"))
        self.assertIn("GRAP 1 (SFP)", submit_review_button_label("balance_sheet"))
        self.assertIn("GRAP 1 (Performance)", submit_review_button_label("income_statement"))
        self.assertEqual(
            "Data forwarded to Finance Manager for review.",
            submit_success_message("balance_sheet"),
        )
        self.assertEqual(
            "Data forwarded to Finance Manager for review.",
            submit_success_message("income_statement"),
        )
        self.assertEqual("GRAP 1 (SFP)", standard_label_for_document("balance_sheet"))


class GrapComplianceServiceTests(unittest.TestCase):
    def test_balance_sheet_passes_when_balanced(self):
        session = SimpleNamespace(
            id="s1",
            metadata={
                "document_type": "balance_sheet",
                "total_mapped_accounts": 3,
                "balance_check_passed": True,
                "mapped_accounts": [
                    {"grap_category": "assets", "current_amount": 1000},
                    {"grap_category": "liabilities", "current_amount": 600},
                    {"grap_category": "equity", "current_amount": 400},
                ],
            },
        )
        out = run_session_grap_compliance(session, "balance_sheet")
        self.assertTrue(out["passed"])

    def test_income_statement_requires_revenue_or_expense(self):
        session = SimpleNamespace(
            id="s2",
            metadata={
                "document_type": "income_statement",
                "total_mapped_accounts": 1,
                "mapped_accounts": [
                    {"grap_category": "other", "current_amount": 100},
                ],
            },
        )
        out = run_session_grap_compliance(session, "income_statement")
        self.assertFalse(out["passed"])

    def test_budget_skips_statement_compliance(self):
        session = SimpleNamespace(id="s3", metadata={"document_type": "budget_report"})
        out = run_session_grap_compliance(session, "budget_report")
        self.assertTrue(out["passed"])

    def test_group_mapped_puts_cogs_on_performance(self):
        mapped = [
            {"account_code": "1001", "grap_code": "CA100", "net_balance": 25000},
            {"account_code": "5001", "grap_code": "CA130", "net_balance": 45000},
            {"account_code": "2001", "grap_code": "CL200", "net_balance": -18000},
            {"account_code": "3001", "grap_code": "EQ300", "net_balance": -7000},
        ]
        grouped = group_mapped_accounts_for_statements(mapped)
        self.assertEqual(len(grouped["statement_of_financial_position"]["assets"]["accounts"]), 1)
        self.assertEqual(
            grouped["statement_of_financial_performance"]["expenses"]["accounts"][0]["account_code"],
            "5001",
        )


if __name__ == "__main__":
    unittest.main()
