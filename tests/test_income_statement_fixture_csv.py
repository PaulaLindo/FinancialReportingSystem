"""Regression: sample income_statement_perfectly_balanced.csv must pass upload balance gates."""

import unittest
from pathlib import Path

import pandas as pd

from controllers.routes_universal import _calculate_balance_for_document_type
from services.income_statement_service import IncomeStatementService


class IncomeStatementFixtureCsvTests(unittest.TestCase):
    def test_perfectly_balanced_fixture_passes_validation(self):
        csv_path = (
            Path(__file__).resolve().parents[1]
            / "financial_documents"
            / "income_statements"
            / "income_statement_perfectly_balanced.csv"
        )
        self.assertTrue(csv_path.is_file(), f"Missing fixture: {csv_path}")

        svc = IncomeStatementService()
        df = pd.read_csv(csv_path)
        mapping = svc._detect_columns(df)
        rows = [
            svc._create_data_row_from_row("fixture", idx, row, mapping)
            for idx, row in df.iterrows()
        ]

        result = _calculate_balance_for_document_type("income_statement", rows)
        self.assertTrue(result["has_performance_lines"])
        self.assertTrue(result["is_balanced"])
        self.assertTrue(result.get("debit_credit_balanced", True))


if __name__ == "__main__":
    unittest.main()
