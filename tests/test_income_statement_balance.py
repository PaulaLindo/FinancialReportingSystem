"""Income statement upload balance totals."""

import unittest
from types import SimpleNamespace

from controllers.routes_universal import _calculate_balance_for_document_type


def _row(**kwargs):
    return SimpleNamespace(**kwargs)


class TestIncomeStatementBalanceTotals(unittest.TestCase):
    def test_category_and_amount_columns(self):
        rows = [
            _row(account_code='REV-001', category='Revenue', credit_balance=250000.0, debit_balance=0.0),
            _row(account_code='EXP-001', category='Expenses', debit_balance=180000.0, credit_balance=0.0),
            _row(account_code='TOTAL', category='Summary', debit_balance=0.0, credit_balance=0.0, is_total_row=True),
        ]
        result = _calculate_balance_for_document_type('income_statement', rows)
        self.assertAlmostEqual(result['total_revenue'], 250000.0)
        self.assertAlmostEqual(result['total_expenses'], 180000.0)
        self.assertAlmostEqual(result['net_income'], 70000.0)
        self.assertTrue(result['has_performance_lines'])

    def test_account_code_ranges(self):
        rows = [
            _row(account_code='4100', account_description='Grants', amount=50000.0),
            _row(account_code='5100', account_description='Salaries', amount=30000.0),
        ]
        result = _calculate_balance_for_document_type('income_statement', rows)
        self.assertAlmostEqual(result['total_revenue'], 50000.0)
        self.assertAlmostEqual(result['total_expenses'], 30000.0)

    def test_empty_rows_not_validated(self):
        result = _calculate_balance_for_document_type('income_statement', [])
        self.assertEqual(result['total_revenue'], 0.0)
        self.assertEqual(result['total_expenses'], 0.0)
        self.assertFalse(result['has_performance_lines'])
        self.assertFalse(result['is_balanced'])

    def test_debit_credit_format_must_balance(self):
        rows = [
            _row(account_code='4100', category='Revenue', debit_balance=0.0, credit_balance=100.0),
            _row(account_code='5100', category='Expenses', debit_balance=80.0, credit_balance=0.0),
        ]
        result = _calculate_balance_for_document_type('income_statement', rows)
        self.assertTrue(result['has_performance_lines'])
        self.assertFalse(result['debit_credit_balanced'])
        self.assertFalse(result['is_balanced'])

    def test_debit_credit_format_balanced(self):
        rows = [
            _row(account_code='4100', category='Revenue', debit_balance=0.0, credit_balance=100.0),
            _row(account_code='5100', category='Expenses', debit_balance=100.0, credit_balance=0.0),
        ]
        result = _calculate_balance_for_document_type('income_statement', rows)
        self.assertTrue(result['is_balanced'])


class TestBalanceSheetBalanceTotals(unittest.TestCase):
    def test_debit_credit_from_row_attributes(self):
        rows = [
            _row(account_code='1001', debit_balance=45000.0, credit_balance=0.0),
            _row(account_code='2001', debit_balance=0.0, credit_balance=30000.0),
            _row(account_code='3001', debit_balance=0.0, credit_balance=70000.0),
        ]
        result = _calculate_balance_for_document_type('balance_sheet', rows)
        self.assertAlmostEqual(result['total_debits'], 45000.0)
        self.assertAlmostEqual(result['total_credits'], 100000.0)
        self.assertTrue(result['is_balanced'] is False)

    def test_credit_from_processed_data_when_attribute_null(self):
        rows = [
            _row(
                account_code='1001',
                debit_balance=50000.0,
                credit_balance=None,
                processed_data={'debit_balance': 50000.0, 'credit_balance': 0.0},
            ),
            _row(
                account_code='2001',
                debit_balance=None,
                credit_balance=None,
                processed_data={'debit_balance': 0.0, 'credit_balance': 50000.0},
            ),
        ]
        result = _calculate_balance_for_document_type('balance_sheet', rows)
        self.assertAlmostEqual(result['total_debits'], 50000.0)
        self.assertAlmostEqual(result['total_credits'], 50000.0)
        self.assertTrue(result['is_balanced'])


if __name__ == '__main__':
    unittest.main()
