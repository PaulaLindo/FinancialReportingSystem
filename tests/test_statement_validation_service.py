import unittest

from services.statement_validation_service import (
    compute_sfp_totals_from_lines,
    group_mapped_accounts_for_statements,
    sla_status_for_session,
    validate_balance_sheet,
    validate_for_review,
    validate_negative_balances,
)


class StatementValidationTests(unittest.TestCase):
    def test_balance_sheet_balanced(self):
        lines = [
            {"grap_category": "assets", "current_amount": 1000},
            {"grap_category": "liabilities", "current_amount": 600},
            {"grap_category": "equity", "current_amount": 400},
        ]
        result = validate_balance_sheet(lines)
        self.assertTrue(result["passed"])

    def test_balance_sheet_balanced_with_grap_codes(self):
        lines = [
            {"grap_code": "CA100", "grap_category": "Cash and Cash Equivalents", "amount": 1000},
            {"grap_code": "CL200", "grap_category": "Payables", "amount": -600},
            {"grap_code": "EQ300", "grap_category": "Capital and Reserves", "amount": 400},
        ]
        result = validate_balance_sheet(lines)
        self.assertTrue(result["passed"])

    def test_balance_sheet_out_of_balance(self):
        lines = [
            {"grap_category": "assets", "current_amount": 1000},
            {"grap_category": "liabilities", "current_amount": 500},
            {"grap_category": "equity", "current_amount": 400},
        ]
        result = validate_balance_sheet(lines)
        self.assertFalse(result["passed"])

    def test_balance_sheet_allows_credit_normal_negative_amounts(self):
        """Liability/equity TB lines often submit as negative net amounts."""
        lines = [
            {"grap_code": "CA100", "grap_category": "Cash", "current_amount": 45000},
            {"grap_code": "CL200", "grap_category": "Payables", "current_amount": -22000},
            {"grap_code": "EQ300", "grap_category": "Capital", "current_amount": -35000},
        ]
        neg = validate_negative_balances(lines, document_type="balance_sheet")
        self.assertTrue(neg["passed"])
        report = validate_for_review(document_type="balance_sheet", lines=lines)
        neg_checks = [c for c in report["checks"] if c["check"] == "negative_balances"]
        self.assertTrue(neg_checks[0]["passed"])

    def test_balance_sheet_uses_net_balance_field(self):
        """Mapping UI submits net_balance + code — must not read as zero."""
        lines = [
            {"grap_code": "CA100", "grap_category": "Cash", "name": "Cash and Bank", "code": "1001", "net_balance": 45000},
            {"grap_code": "CA120", "grap_category": "Receivables", "name": "Trade Receivables", "code": "1002", "net_balance": 25000},
            {"grap_code": "CA130", "grap_category": "Inventories", "name": "Inventory", "code": "1003", "net_balance": 15000},
            {"grap_code": "CA160", "grap_category": "PPE", "name": "PPE", "code": "1004", "net_balance": 15000},
            {"grap_code": "CA140", "grap_category": "Other Current Assets", "name": "Accrued Liabilities", "code": "2002", "net_balance": -8000},
            {"grap_code": "CL200", "grap_category": "Payables", "name": "Trade Payables", "code": "2001", "net_balance": -22000},
            {"grap_code": "CL220", "grap_category": "Non-Current Liabilities", "name": "Short-term Borrowings", "code": "2003", "net_balance": -10000},
            {"grap_code": "EQ300", "grap_category": "Capital", "name": "Share Capital", "code": "3001", "net_balance": -35000},
            {"grap_code": "EQ300", "grap_category": "Capital", "name": "Retained Earnings", "code": "3002", "net_balance": -25000},
        ]
        result = validate_balance_sheet(lines)
        self.assertTrue(result["passed"])
        self.assertEqual(result["details"]["difference"], 0.0)

    def test_balance_sheet_liability_misplaced_in_asset_category(self):
        """Borrowings mapped to a CA* bucket still classify as liabilities."""
        lines = [
            {"grap_code": "CA100", "grap_category": "Cash and Cash Equivalents", "account_name": "Cash and Bank", "amount": 50000},
            {"grap_code": "CA150", "grap_category": "Non-Current Financial Assets", "account_name": "Short-term Borrowings", "amount": -10000},
            {"grap_code": "CL200", "grap_category": "Payables", "account_name": "Trade Payables", "amount": -20000},
            {"grap_code": "EQ300", "grap_category": "Capital and Reserves", "account_name": "Share Capital", "amount": -20000},
        ]
        result = validate_balance_sheet(lines)
        self.assertTrue(result["passed"])

    def test_group_mapped_excludes_cogs_from_sfp_assets(self):
        """COGS (5001) mapped to CA130 must appear on SFPER, not inflate SFP assets."""
        mapped = [
            {"account_code": "1001", "grap_code": "CA100", "net_balance": 25000},
            {"account_code": "2001", "grap_code": "CL200", "net_balance": -18000},
            {"account_code": "3001", "grap_code": "EQ300", "net_balance": -7000},
            {"account_code": "5001", "grap_code": "CA130", "net_balance": 45000},
            {"account_code": "4001", "grap_code": "RV400", "net_balance": -85000},
        ]
        grouped = group_mapped_accounts_for_statements(mapped)
        sfp = grouped["statement_of_financial_position"]
        self.assertEqual(len(sfp["assets"]["accounts"]), 1)
        self.assertEqual(sfp["assets"]["accounts"][0]["account_code"], "1001")
        self.assertEqual(len(grouped["statement_of_financial_performance"]["expenses"]["accounts"]), 1)
        totals = compute_sfp_totals_from_lines(
            sfp["assets"]["accounts"] + sfp["liabilities"]["accounts"] + sfp["equity"]["accounts"]
        )
        self.assertEqual(totals["assets"], 25000)

    def test_balance_sheet_contra_asset_net(self):
        """Accumulated depreciation (credit) must reduce assets, not inflate them."""
        lines = [
            {"grap_code": "CA200", "grap_category": "Equipment", "debit_balance": 80000, "credit_balance": 0},
            {
                "grap_code": "CA200",
                "grap_category": "Accumulated Depreciation - Equipment",
                "debit_balance": 0,
                "credit_balance": 20000,
            },
            {"grap_code": "CL200", "grap_category": "Payables", "debit_balance": 0, "credit_balance": 40000},
            {"grap_code": "EQ300", "grap_category": "Capital", "debit_balance": 0, "credit_balance": 20000},
        ]
        result = validate_balance_sheet(lines)
        self.assertTrue(result["passed"])
        self.assertEqual(result["details"]["assets"], 60000)

    def test_metadata_mapping_check(self):
        report = validate_for_review(
            document_type="income_statement",
            session_metadata={"total_mapped_accounts": 12, "balance_check_passed": True},
        )
        self.assertTrue(report["valid"])
        self.assertGreaterEqual(report["score"], 50)

    def test_sla_section_when_submitted(self):
        report = validate_for_review(
            document_type="balance_sheet",
            session_metadata={"submitted_at": "2020-01-01T00:00:00"},
        )
        self.assertIn("sla", report)
        self.assertIsNotNone(sla_status_for_session({"submitted_at": "2020-01-01T00:00:00"}, "balance_sheet"))


if __name__ == "__main__":
    unittest.main()
