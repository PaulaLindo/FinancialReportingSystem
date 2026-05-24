"""Tests for Export Center service and PDF download permissions."""

import unittest
from unittest.mock import MagicMock, patch

from services.export_center_service import build_pdf_results_from_summary, export_center_service


class TestExportPermissions(unittest.TestCase):
    def test_fm_can_download_not_generate(self):
        perms = {
            "FINANCE_MANAGER": ["review", "approve", "process", "view_all", "download_pdf"],
            "CFO": ["final_approve", "generate_pdf", "view_all", "export", "export_audit", "review", "process"],
        }

        def has_perm(role, perm):
            return perm in perms.get(role, [])

        self.assertTrue(has_perm("FINANCE_MANAGER", "download_pdf"))
        self.assertFalse(has_perm("FINANCE_MANAGER", "generate_pdf"))
        self.assertFalse(has_perm("FINANCE_MANAGER", "export"))
        self.assertTrue(has_perm("CFO", "generate_pdf"))
        self.assertTrue(has_perm("CFO", "export"))


class TestBuildPdfResults(unittest.TestCase):
    def test_builds_sofp_and_sofe_from_mapped_metadata(self):
        summary = {
            "session_id": "abc-123",
            "document_type": "balance_sheet",
            "metadata": {
                "mapped_data": [
                    {
                        "account_code": "1001",
                        "account_name": "Cash",
                        "grap_code": "CA110",
                        "amount": 1000,
                    },
                    {
                        "account_code": "2001",
                        "account_name": "Payables",
                        "grap_code": "CL210",
                        "amount": 400,
                    },
                    {
                        "account_code": "3001",
                        "account_name": "Equity",
                        "grap_code": "EQ310",
                        "amount": 600,
                    },
                ]
            },
        }
        results = build_pdf_results_from_summary(summary)
        self.assertIn("sofp", results)
        self.assertIn("sofe", results)
        self.assertAlmostEqual(results["summary"]["total_assets"], 1000.0, places=2)
        self.assertIn("ratios", results["summary"])
        self.assertIn("current_ratio", results["summary"]["ratios"])

    def test_income_statement_summary_includes_ratios(self):
        summary = {
            "session_id": "inc-1",
            "document_type": "income_statement",
            "metadata": {
                "mapped_data": [
                    {
                        "account_code": "4001",
                        "account_name": "Grants",
                        "grap_code": "RV410",
                        "amount": 1000,
                        "category": "revenue",
                    },
                    {
                        "account_code": "5001",
                        "account_name": "Salaries",
                        "grap_code": "EX510",
                        "amount": 600,
                        "category": "expense",
                    },
                ]
            },
        }
        results = build_pdf_results_from_summary(summary)
        ratios = results["summary"]["ratios"]
        self.assertEqual(ratios["operating_margin"], 40.0)

    def test_budget_report_uses_budget_layout(self):
        summary = {
            "session_id": "bud-1",
            "document_type": "budget_report",
            "total_budget": 50000.0,
            "total_actual": 42000.0,
            "total_variance": -8000.0,
            "budget_rows": [
                {
                    "account_description": "Salaries",
                    "department": "All Departments",
                    "budget_amount": 30000,
                    "actual_amount": 28000,
                },
                {
                    "account_description": "IT Infrastructure",
                    "department": "All Departments",
                    "budget_amount": 20000,
                    "actual_amount": 14000,
                },
            ],
        }
        results = build_pdf_results_from_summary(summary)
        self.assertEqual(results["summary"]["document_type"], "budget_report")
        self.assertAlmostEqual(results["summary"]["total_budget"], 50000.0, places=2)
        self.assertAlmostEqual(results["summary"]["total_actual"], 42000.0, places=2)
        self.assertEqual(len(results["sofe"]["expenses"]), 2)
        self.assertIn("ratios", results["summary"])

class TestExportCsvBytes(unittest.TestCase):
    def test_csv_from_mapped_metadata(self):
        summary = {
            "document_type": "income_statement",
            "metadata": {
                "mapped_data": [
                    {
                        "account_code": "4001",
                        "account_name": "Grants",
                        "grap_code": "RV410",
                        "amount": 500,
                    }
                ]
            },
        }
        content = export_center_service.export_csv_bytes(summary)
        self.assertIn(b"account_code", content)
        self.assertIn(b"4001", content)

    def test_budget_csv_uses_session_field_names(self):
        summary = {
            "document_type": "budget_report",
            "budget_rows": [
                {
                    "account_code": "5100",
                    "account_description": "Salaries",
                    "department": "All Departments",
                    "budget_amount": 30000,
                    "actual_amount": 28000,
                    "variance": -2000,
                    "variance_percentage": 6.67,
                    "mapped_to_grap": "EX510",
                    "variance_explanation": "Timing difference",
                }
            ],
        }
        content = export_center_service.export_csv_bytes(summary)
        self.assertIn(b"Salaries", content)
        self.assertIn(b"30000", content)
        self.assertIn(b"28000", content)
        self.assertIn(b"Timing difference", content)

class TestPdfDownloadGuardFmAccess(unittest.TestCase):
    @patch("utils.pdf_download_guard.resolve_pdf_availability")
    def test_locked_period_allows_download_without_user_match(self, mock_avail):
        from utils.pdf_download_guard import verify_pdf_download_allowed
        import tempfile
        import json
        import os

        mock_avail.return_value = {"can_generate_pdf": True, "reason": ""}
        tmp = tempfile.mkdtemp()
        meta = {
            "filename": "report.pdf",
            "session_id": "sess-1",
            "document_type": "balance_sheet",
            "user_id": "cfo-user",
        }
        with open(os.path.join(tmp, "report.pdf.meta.json"), "w", encoding="utf-8") as fh:
            json.dump(meta, fh)
        with open(os.path.join(tmp, "report.pdf"), "wb") as fh:
            fh.write(b"%PDF-1.4")

        allowed, err = verify_pdf_download_allowed(
            tmp,
            "report.pdf",
            user_id="fm-user",
        )
        self.assertTrue(allowed, err)


if __name__ == "__main__":
    unittest.main()
