import unittest
from types import SimpleNamespace

from controllers.routes_universal import (
    _balance_result_payload,
    _calculate_balance_for_document_type,
    _should_skip_balance_row,
)


class BalanceCheckHelperTests(unittest.TestCase):
    def test_skip_totals_row(self):
        row = SimpleNamespace(
            account_code="TOTALS",
            account_description="TOTALS",
            debit_balance=315000,
            credit_balance=315000,
            is_total_row=False,
        )
        self.assertTrue(_should_skip_balance_row(row))

    def test_balance_sheet_debits_credits_excludes_totals(self):
        rows = [
            SimpleNamespace(
                account_code="1001",
                debit_balance=100,
                credit_balance=0,
                is_total_row=False,
            ),
            SimpleNamespace(
                account_code="2001",
                debit_balance=0,
                credit_balance=100,
                is_total_row=False,
            ),
            SimpleNamespace(
                account_code="TOTALS",
                debit_balance=100,
                credit_balance=100,
                is_total_row=False,
            ),
        ]
        result = _calculate_balance_for_document_type("balance_sheet", rows)
        self.assertTrue(result["is_balanced"])
        self.assertEqual(result["total_debits"], 100)
        self.assertEqual(result["total_credits"], 100)
        self.assertEqual(result["balance_difference"], 0)

    def test_balance_result_payload_includes_balance_difference(self):
        payload = _balance_result_payload(
            total_debits=100,
            total_credits=35,
            difference=65,
            balance_type="debits_vs_credits",
        )
        self.assertEqual(payload["balance_difference"], 65)
        self.assertFalse(payload["is_balanced"])


if __name__ == "__main__":
    unittest.main()
