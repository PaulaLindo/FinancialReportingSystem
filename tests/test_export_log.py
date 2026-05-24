"""Tests for export activity log."""

import unittest
from unittest.mock import MagicMock, patch

from services.export_log_service import ExportLogService, export_log_service


def _isolated_export_log_svc() -> ExportLogService:
    """In-memory export log only — avoids Supabase bleed between tests."""
    svc = ExportLogService()
    svc._audit._svc = None
    return svc


class TestExportLogService(unittest.TestCase):
    def test_record_and_list_in_memory(self):
        svc = _isolated_export_log_svc()
        svc.record(
            export_format="excel",
            session_id="sess-abc-123",
            document_type="income_statement",
            user_id="user-1",
            user_name="Sarah Nkosi",
            user_role="CFO",
            filename="Varydian_income_statement_abc.xlsx",
            period_name="May 2026",
        )
        events = svc.list_events(limit=10, session_id="sess-abc-123")
        self.assertGreaterEqual(len(events), 1)
        latest = events[0]
        self.assertEqual(latest["export_format"], "excel")
        self.assertIn("Excel exported", latest["title"])
        self.assertIn("Sarah Nkosi", latest["actor_label"])

    def test_format_labels(self):
        svc = _isolated_export_log_svc()
        svc.record(
            export_format="pdf_generate",
            session_id="sess-pdf",
            document_type="budget_report",
            user_name="CFO User",
            user_role="CFO",
            filename="report.pdf",
        )
        events = svc.list_events(session_id="sess-pdf")
        self.assertTrue(any("PDF generated" in e["title"] for e in events))

    def test_pdf_only_filter(self):
        svc = _isolated_export_log_svc()
        sid = "sess-mix-pdf-filter-test"
        svc.record(
            export_format="excel",
            session_id=sid,
            document_type="income_statement",
            user_name="CFO User",
            user_role="CFO",
        )
        svc.record(
            export_format="pdf_generate",
            session_id=sid,
            document_type="income_statement",
            user_name="CFO User",
            user_role="CFO",
            filename="report.pdf",
        )
        pdf_events = svc.list_events(
            session_id=sid,
            export_formats={"pdf_generate", "pdf_download"},
        )
        self.assertEqual(len(pdf_events), 1)
        self.assertEqual(pdf_events[0]["export_format"], "pdf_generate")
        self.assertFalse(any(e["export_format"] == "excel" for e in pdf_events))

    def test_session_ids_with_pdf_export(self):
        svc = _isolated_export_log_svc()
        svc.record(
            export_format="pdf_generate",
            session_id="sess-exported-1",
            document_type="balance_sheet",
            user_name="CFO",
            user_role="CFO",
        )
        svc.record(
            export_format="excel",
            session_id="sess-not-pdf",
            document_type="budget_report",
            user_name="CFO",
            user_role="CFO",
        )
        exported = svc.session_ids_with_pdf_export(["sess-exported-1", "sess-not-pdf", "sess-missing"])
        self.assertIn("sess-exported-1", exported)
        self.assertNotIn("sess-not-pdf", exported)
        self.assertNotIn("sess-missing", exported)

    def test_module_singleton(self):
        self.assertIsNotNone(export_log_service)


if __name__ == "__main__":
    unittest.main()
