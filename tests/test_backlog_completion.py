import unittest
from unittest.mock import MagicMock, patch

from services.certificate_registry_service import verify_certificate
from services.email_notification_service import is_configured, user_wants_email
from services.statement_validation_service import (
    validate_grap_categories,
    validate_income_statement,
    validate_negative_balances,
)
class EmailNotificationTests(unittest.TestCase):
    def test_not_configured_without_smtp(self):
        with patch.dict("os.environ", {}, clear=True):
            self.assertFalse(is_configured())

    @patch("utils.supabase_service_client.get_service_supabase_client")
    def test_user_wants_email_defaults_true(self, mock_client_fn):
        mock_client_fn.return_value = None
        with patch.dict("os.environ", {"SMTP_HOST": "smtp.test", "SMTP_FROM": "a@b.com"}):
            self.assertTrue(user_wants_email("user-1", "submission_pending_review"))


class ValidationExtendedTests(unittest.TestCase):
    def test_negative_balances_flagged(self):
        lines = [{"grap_category": "assets", "current_amount": -100}]
        result = validate_negative_balances(lines, document_type="income_statement")
        self.assertFalse(result["passed"])

    def test_grap_mapping_incomplete(self):
        lines = [{"grap_category": "unmapped", "current_amount": 50}]
        result = validate_grap_categories(lines)
        self.assertFalse(result["passed"])

    def test_income_statement_totals(self):
        lines = [
            {"grap_category": "revenue", "current_amount": 1000},
            {"grap_category": "expense", "current_amount": 400},
        ]
        result = validate_income_statement(lines)
        self.assertTrue(result["passed"])


class CertificateVerifyTests(unittest.TestCase):
    @patch("services.certificate_registry_service.get_certificate")
    def test_verify_missing_registry(self, mock_get):
        mock_get.return_value = None
        out = verify_certificate("CERT_missing")
        self.assertFalse(out["valid"])


if __name__ == "__main__":
    unittest.main()
