"""require_balanced_session enforces upload rules for all document types."""

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from controllers.routes_universal import require_balanced_session


def _row(**kwargs):
    return SimpleNamespace(**kwargs)


class RequireBalancedSessionAllDocsTests(unittest.TestCase):
    def _mock_fetch(self, rows):
        model = MagicMock()
        model.get_session.return_value = SimpleNamespace(id='s1')
        service = MagicMock()
        return service, model, rows

    @patch('controllers.routes_universal.upload_handler')
    @patch('controllers.routes_universal._fetch_session_data_rows')
    @patch('controllers.routes_universal._document_service_model')
    def test_balance_sheet_blocks_unbalanced(self, mock_model_fn, mock_fetch, mock_upload):
        service, model, rows = self._mock_fetch([
            _row(account_code='1001', debit_balance=100.0, credit_balance=0.0),
            _row(account_code='2001', debit_balance=0.0, credit_balance=50.0),
        ])
        mock_upload.get_service.return_value = service
        mock_model_fn.return_value = model
        mock_fetch.return_value = rows

        ok, err = require_balanced_session('s1', 'balance_sheet')
        self.assertFalse(ok)
        self.assertIn('Trial balance must be balanced', err)

    @patch('controllers.routes_universal.upload_handler')
    @patch('controllers.routes_universal._fetch_session_data_rows')
    @patch('controllers.routes_universal._document_service_model')
    def test_income_statement_blocks_empty(self, mock_model_fn, mock_fetch, mock_upload):
        service, model, rows = self._mock_fetch([])
        mock_upload.get_service.return_value = service
        mock_model_fn.return_value = model
        mock_fetch.return_value = rows

        ok, err = require_balanced_session('s1', 'income_statement')
        self.assertFalse(ok)
        self.assertIn('No data found', err)

    @patch('controllers.routes_universal.upload_handler')
    @patch('controllers.routes_universal._fetch_session_data_rows')
    @patch('controllers.routes_universal._document_service_model')
    def test_income_statement_blocks_no_performance_lines(self, mock_model_fn, mock_fetch, mock_upload):
        service, model, rows = self._mock_fetch([
            _row(account_code='9999', category='Header', debit_balance=0.0, credit_balance=0.0),
        ])
        mock_upload.get_service.return_value = service
        mock_model_fn.return_value = model
        mock_fetch.return_value = rows

        ok, err = require_balanced_session('s1', 'income_statement')
        self.assertFalse(ok)
        self.assertIn('revenue or expense', err.lower())

    @patch('controllers.routes_universal.upload_handler')
    @patch('controllers.routes_universal._fetch_session_data_rows')
    @patch('controllers.routes_universal._document_service_model')
    def test_income_statement_blocks_unbalanced_debits_credits(self, mock_model_fn, mock_fetch, mock_upload):
        service, model, rows = self._mock_fetch([
            _row(account_code='4100', category='Revenue', debit_balance=0.0, credit_balance=100.0),
            _row(account_code='5100', category='Expenses', debit_balance=80.0, credit_balance=0.0),
        ])
        mock_upload.get_service.return_value = service
        mock_model_fn.return_value = model
        mock_fetch.return_value = rows

        ok, err = require_balanced_session('s1', 'income_statement')
        self.assertFalse(ok)
        self.assertIn('Trial balance must be balanced', err)

    @patch('controllers.routes_universal.upload_handler')
    @patch('controllers.routes_universal._fetch_session_data_rows')
    @patch('controllers.routes_universal._document_service_model')
    def test_budget_report_blocks_empty_lines(self, mock_model_fn, mock_fetch, mock_upload):
        service, model, rows = self._mock_fetch([
            _row(account_code='6001', budget_amount=0.0, actual_amount=0.0),
        ])
        mock_upload.get_service.return_value = service
        mock_model_fn.return_value = model
        mock_fetch.return_value = rows

        ok, err = require_balanced_session('s1', 'budget_report')
        self.assertFalse(ok)
        self.assertIn('budget and actual', err.lower())

    @patch('controllers.routes_universal.upload_handler')
    @patch('controllers.routes_universal._fetch_session_data_rows')
    @patch('controllers.routes_universal._document_service_model')
    def test_budget_report_allows_variance(self, mock_model_fn, mock_fetch, mock_upload):
        service, model, rows = self._mock_fetch([
            _row(account_code='6001', budget_amount=1000.0, actual_amount=800.0),
        ])
        mock_upload.get_service.return_value = service
        mock_model_fn.return_value = model
        mock_fetch.return_value = rows

        ok, err = require_balanced_session('s1', 'budget_report')
        self.assertTrue(ok)
        self.assertIsNone(err)


if __name__ == '__main__':
    unittest.main()
