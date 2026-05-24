import unittest
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from decimal import Decimal

from services.budget_variance_service import (
    VARIANCE_EXPLANATION_THRESHOLD,
    compute_session_variance,
    enrich_budget_row,
    get_lines_requiring_explanation,
    get_variance_explanations_from_metadata,
    line_requires_explanation,
    merge_explanations_into_rows,
    resolve_line_variance,
    validate_variance_explanations,
)
from utils.period_lock import (
    attach_period_to_session_metadata,
    check_period_id_unlocked,
    check_session_period_unlocked,
    is_period_locked,
    period_lock_message,
    resolve_period_id_by_date,
    resolve_period_id_from_session,
    session_period_lock_status,
)
from utils.pdf_availability import resolve_pdf_availability


def _sample_rows():
    return [
        {
            "row_index": 1,
            "account_code": "100",
            "account_description": "Salaries",
            "budget_amount": 1000,
            "actual_amount": 1150,
            "variance": 150,
            "is_total_row": False,
            "is_subtotal_row": False,
        },
        {
            "row_index": 2,
            "account_code": "200",
            "account_description": "Travel",
            "budget_amount": 1000,
            "actual_amount": 1050,
            "variance": 50,
            "is_total_row": False,
            "is_subtotal_row": False,
        },
        {
            "row_index": 99,
            "account_description": "Total",
            "budget_amount": 2000,
            "variance": 200,
            "is_total_row": True,
            "is_subtotal_row": False,
        },
    ]


class BudgetVarianceServiceTests(unittest.TestCase):
    def test_threshold_is_ten_percent(self):
        self.assertEqual(VARIANCE_EXPLANATION_THRESHOLD, Decimal("0.10"))

    def test_line_requires_explanation_above_threshold(self):
        row = _sample_rows()[0]
        self.assertTrue(line_requires_explanation(row))

    def test_line_does_not_require_explanation_at_or_below_threshold(self):
        row = _sample_rows()[1]
        self.assertFalse(line_requires_explanation(row))

    def test_total_rows_never_require_explanation(self):
        row = _sample_rows()[2]
        self.assertFalse(line_requires_explanation(row))

    def test_zero_budget_never_requires_explanation(self):
        row = {"budget_amount": 0, "variance": 500, "is_total_row": False}
        self.assertFalse(line_requires_explanation(row))

    def test_validate_fails_without_explanations(self):
        rows = _sample_rows()
        passed, missing, required = validate_variance_explanations(rows, {})
        self.assertFalse(passed)
        self.assertEqual(missing, ["Salaries"])
        self.assertEqual(len(required), 1)

    def test_validate_passes_with_explanation(self):
        rows = _sample_rows()
        passed, missing, _ = validate_variance_explanations(rows, {"1": "Overtime costs"})
        self.assertTrue(passed)
        self.assertEqual(missing, [])

    def test_enrich_budget_row_adds_flags(self):
        enriched = enrich_budget_row(_sample_rows()[0])
        self.assertTrue(enriched["requires_variance_explanation"])
        self.assertAlmostEqual(enriched["variance_percentage"], 15.0)

    def test_merge_explanations_into_rows(self):
        merged = merge_explanations_into_rows(_sample_rows(), {"1": "Timing difference"})
        row1 = next(r for r in merged if r["row_index"] == 1)
        self.assertEqual(row1["variance_explanation"], "Timing difference")

    def test_get_variance_explanations_from_metadata(self):
        md = {"variance_explanations": {"1": "  note ", "2": ""}}
        self.assertEqual(get_variance_explanations_from_metadata(md), {"1": "note"})

    def test_get_lines_requiring_explanation(self):
        lines = get_lines_requiring_explanation(_sample_rows())
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["account_description"], "Salaries")

    def test_resolve_line_variance_prefers_actual_minus_budget(self):
        self.assertEqual(resolve_line_variance(1000, 1150, 9999), Decimal("150"))

    def test_resolve_line_variance_uses_file_when_amounts_missing(self):
        self.assertEqual(resolve_line_variance(None, None, 75), Decimal("75"))

    def test_enrich_budget_row_recomputes_stale_file_variance(self):
        row = {
            "row_index": 3,
            "budget_amount": 1000,
            "actual_amount": 1150,
            "variance": -50,
            "is_total_row": False,
            "is_subtotal_row": False,
        }
        enriched = enrich_budget_row(row)
        self.assertEqual(enriched["variance"], 150.0)
        self.assertTrue(enriched["requires_variance_explanation"])

    def test_compute_session_variance(self):
        self.assertEqual(compute_session_variance(2000, 2150), Decimal("150"))


class PeriodLockUtilsTests(unittest.TestCase):
    def _period(self, locked=False, name="FY 2025-26"):
        return SimpleNamespace(
            id="period-1",
            name=name,
            is_locked=locked,
            metadata={"is_locked": locked, "locked_at": "2026-01-01"} if locked else {},
        )

    def test_is_period_locked_from_field(self):
        self.assertTrue(is_period_locked(self._period(locked=True)))

    def test_is_period_locked_from_metadata(self):
        p = SimpleNamespace(id="p", name="Q1", is_locked=False, metadata={"is_locked": True})
        self.assertTrue(is_period_locked(p))

    def test_resolve_period_id_from_metadata(self):
        session = SimpleNamespace(metadata={"period_id": "abc-123"}, reporting_period="")
        self.assertEqual(resolve_period_id_from_session(session), "abc-123")

    @patch("utils.period_lock.period_model.get_all_periods")
    def test_resolve_period_id_from_reporting_period_label(self, mock_all):
        mock_all.return_value = [self._period()]
        session = SimpleNamespace(
            metadata={},
            reporting_period="FY 2025-26",
        )
        self.assertEqual(resolve_period_id_from_session(session), "period-1")

    @patch("utils.period_lock.period_model.get_period")
    def test_check_session_period_unlocked_when_locked(self, mock_get):
        mock_get.return_value = self._period(locked=True)
        session = SimpleNamespace(metadata={"period_id": "period-1"}, reporting_period="")
        allowed, msg = check_session_period_unlocked(session)
        self.assertFalse(allowed)
        self.assertIn("locked", msg.lower())

    @patch("utils.period_lock.period_model.get_period")
    def test_check_period_id_unlocked_when_open(self, mock_get):
        mock_get.return_value = self._period(locked=False)
        allowed, msg = check_period_id_unlocked("period-1")
        self.assertTrue(allowed)
        self.assertEqual(msg, "")

    def test_period_lock_message(self):
        msg = period_lock_message(self._period(name="March 2026"))
        self.assertIn("March 2026", msg)

    @patch("utils.period_lock.period_model.get_period")
    def test_session_period_lock_status(self, mock_get):
        mock_get.return_value = self._period(locked=True)
        session = SimpleNamespace(metadata={"period_id": "period-1"}, reporting_period="")
        status = session_period_lock_status(session)
        self.assertTrue(status["period_locked"])
        self.assertEqual(status["period_id"], "period-1")

    @patch("utils.period_lock.period_model.get_period")
    def test_attach_period_to_session_metadata_sets_name(self, mock_get):
        mock_get.return_value = self._period(name="May 2026")
        session = SimpleNamespace(metadata={})
        attach_period_to_session_metadata(session, "period-1")
        self.assertEqual(session.metadata["period_id"], "period-1")
        self.assertEqual(session.metadata["period_name"], "May 2026")
        self.assertEqual(session.metadata["reporting_period"], "May 2026")

    @patch("utils.period_lock.period_model.get_all_periods")
    def test_resolve_period_id_by_date_single_match(self, mock_all):
        mock_all.return_value = [
            SimpleNamespace(
                id="period-may",
                name="May 2026",
                status="open",
                start_date="2026-05-01T00:00:00",
                end_date="2026-05-31T23:59:59",
            )
        ]
        session = SimpleNamespace(
            metadata={"submitted_at": "2026-05-15T10:00:00"},
            reporting_period="",
        )
        self.assertEqual(resolve_period_id_by_date(session), "period-may")

    @patch("utils.period_lock.period_model.get_all_periods")
    def test_resolve_period_id_by_date_ambiguous_returns_none(self, mock_all):
        mock_all.return_value = [
            SimpleNamespace(
                id="p1",
                name="H1",
                status="open",
                start_date="2026-01-01T00:00:00",
                end_date="2026-06-30T23:59:59",
            ),
            SimpleNamespace(
                id="p2",
                name="Q2",
                status="open",
                start_date="2026-04-01T00:00:00",
                end_date="2026-06-30T23:59:59",
            ),
        ]
        session = SimpleNamespace(
            metadata={"submitted_at": "2026-05-15T10:00:00"},
            reporting_period="",
        )
        self.assertIsNone(resolve_period_id_by_date(session))


class PdfAvailabilityTests(unittest.TestCase):
    @patch("utils.pdf_availability.period_model.get_period")
    @patch("utils.pdf_availability._load_workflow_session")
    def test_pdf_blocked_when_period_open(self, mock_load_session, mock_get_period):
        session = SimpleNamespace(
            metadata={"period_id": "period-1", "period_locked": False},
            reporting_period="",
        )
        mock_load_session.return_value = (session, "period-1")
        mock_get_period.return_value = SimpleNamespace(
            id="period-1", name="FY 2025", is_locked=False, metadata={}
        )

        result = resolve_pdf_availability("sess-1", "budget_report")
        self.assertFalse(result["can_generate_pdf"])
        self.assertFalse(result["period_locked"])
        self.assertIn("CFO", result["reason"])

    @patch("utils.pdf_availability.period_model.get_period")
    @patch("utils.pdf_availability._load_workflow_session")
    def test_pdf_allowed_when_period_locked(self, mock_load_session, mock_get_period):
        session = SimpleNamespace(
            metadata={"period_id": "period-1", "period_locked": True, "period_name": "FY 2025"},
            reporting_period="",
        )
        mock_load_session.return_value = (session, "period-1")
        mock_get_period.return_value = SimpleNamespace(
            id="period-1", name="FY 2025", is_locked=True, metadata={"is_locked": True}
        )

        result = resolve_pdf_availability("sess-1", "balance_sheet")
        self.assertTrue(result["can_generate_pdf"])
        self.assertTrue(result["period_locked"])
        self.assertEqual(result["reason"], "")

    @patch("utils.pdf_availability.period_model.get_period")
    @patch("utils.pdf_availability._load_workflow_session")
    def test_pdf_allowed_when_cfo_finalized_without_period_locked_flag(
        self, mock_load_session, mock_get_period
    ):
        """Budget/income rows CFO-approved before period metadata was persisted."""
        session = SimpleNamespace(
            id="bud-1",
            status="approved",
            metadata={
                "cfo_approval": {"at": "2026-05-20T12:00:00Z", "by": "cfo-1"},
                "approved_at": "2026-05-20T12:00:00Z",
            },
            reporting_period="2026",
            fiscal_year=2026,
        )
        mock_load_session.return_value = (session, None)
        mock_get_period.return_value = None

        result = resolve_pdf_availability("bud-1", "budget_report")
        self.assertTrue(result["period_locked"])
        self.assertTrue(result["can_generate_pdf"])
        self.assertEqual(result["lock_source"], "cfo_finalized")
        self.assertEqual(result["reason"], "")


class UniversalWorkflowPeriodLockTests(unittest.TestCase):
    def test_cfo_approve_locks_period(self):
        with patch("utils.supabase_client.create_admin_supabase_client", return_value=MagicMock()):
            with patch("services.universal_workflow_service.supabase_auth.get_user_by_id") as mock_get_user:
                from services.universal_workflow_service import (
                    SubmissionStatus,
                    UniversalWorkflowService,
                )

                session = SimpleNamespace(
                    id="sess-99",
                    status=SubmissionStatus.APPROVED_BY_MANAGER.value,
                    metadata={"period_id": "period-1", "manager_approval": {"at": "2026-01-01"}},
                    processing_log=[],
                    updated_at=None,
                )
                mock_model = MagicMock()
                mock_model.get_session.return_value = session
                mock_model.update_session.side_effect = lambda s: s
                mock_get_user.return_value = {"role": "CFO", "email": "cfo@test.com"}

                svc = UniversalWorkflowService()
                mock_period_svc = MagicMock()
                mock_period_svc.lock_period.return_value = SimpleNamespace(name="FY 2025-26")
                svc.period_service = mock_period_svc

                with patch.object(svc, "_get_model_for_document_type", return_value=mock_model):
                    with patch.object(svc, "_get_workflow_transition", return_value=MagicMock(conditions=[])):
                        with patch.object(
                            svc, "_validate_workflow_conditions", return_value={"all_passed": True}
                        ):
                            with patch.object(svc, "_create_workflow_record", return_value={}):
                                with patch("services.inbox_service.notify_submitter_final_approval"):
                                    result = svc.approve_document(
                                        "budget_report", "sess-99", "cfo-user", "Final"
                                    )

                self.assertTrue(result["success"])
                mock_period_svc.lock_period.assert_called_once_with("period-1", "cfo-user")
                self.assertTrue(session.metadata.get("period_locked"))

    def test_cfo_finalize_rejected_without_period_id(self):
        with patch("utils.supabase_client.create_admin_supabase_client", return_value=MagicMock()):
            with patch("services.universal_workflow_service.supabase_auth.get_user_by_id") as mock_get_user:
                from services.universal_workflow_service import (
                    SubmissionStatus,
                    UniversalWorkflowService,
                )

                session = SimpleNamespace(
                    id="sess-no-period",
                    status=SubmissionStatus.APPROVED_BY_MANAGER.value,
                    metadata={"manager_approval": {"at": "2026-01-01"}},
                    processing_log=[],
                    updated_at=None,
                )
                mock_model = MagicMock()
                mock_model.get_session.return_value = session
                mock_get_user.return_value = {"role": "CFO", "email": "cfo@test.com"}

                svc = UniversalWorkflowService()
                with patch.object(svc, "_get_model_for_document_type", return_value=mock_model):
                    with patch.object(svc, "_get_workflow_transition", return_value=MagicMock(conditions=[])):
                        with patch.object(
                            svc, "_validate_workflow_conditions", return_value={"all_passed": True}
                        ):
                            with patch(
                                "utils.period_lock.find_period_id_for_finalization",
                                return_value=None,
                            ):
                                result = svc.approve_document(
                                    "budget_report", "sess-no-period", "cfo-user", "Final"
                                )

                self.assertFalse(result["success"])
                self.assertEqual(result.get("code"), "period_id_unresolved")
                mock_model.update_session.assert_not_called()
                self.assertIsNone(session.metadata.get("cfo_approval"))

    def test_cfo_finalize_rejected_when_db_lock_fails(self):
        with patch("utils.supabase_client.create_admin_supabase_client", return_value=MagicMock()):
            with patch("services.universal_workflow_service.supabase_auth.get_user_by_id") as mock_get_user:
                from services.universal_workflow_service import (
                    SubmissionStatus,
                    UniversalWorkflowService,
                )

                session = SimpleNamespace(
                    id="sess-db-lock-fail",
                    status=SubmissionStatus.APPROVED_BY_MANAGER.value,
                    metadata={"period_id": "period-1", "manager_approval": {"at": "2026-01-01"}},
                    processing_log=[],
                    updated_at=None,
                )
                mock_model = MagicMock()
                mock_model.get_session.return_value = session
                mock_get_user.return_value = {"role": "CFO", "email": "cfo@test.com"}

                svc = UniversalWorkflowService()
                mock_period_svc = MagicMock()
                mock_period_svc.lock_period.side_effect = Exception("database lock failed")
                svc.period_service = mock_period_svc

                with patch.object(svc, "_get_model_for_document_type", return_value=mock_model):
                    with patch.object(svc, "_get_workflow_transition", return_value=MagicMock(conditions=[])):
                        with patch.object(
                            svc, "_validate_workflow_conditions", return_value={"all_passed": True}
                        ):
                            with patch(
                                "utils.period_lock.find_period_id_for_finalization",
                                return_value="period-1",
                            ):
                                result = svc.approve_document(
                                    "budget_report", "sess-db-lock-fail", "cfo-user", "Final"
                                )

                self.assertFalse(result["success"])
                self.assertEqual(result.get("code"), "period_lock_db_sync_failed")
                mock_model.update_session.assert_not_called()
                self.assertIsNone(session.metadata.get("cfo_approval"))


class FmForwardGrap24Tests(unittest.TestCase):
    @patch("services.universal_workflow_service.supabase_auth.get_user_by_id")
    def test_fm_cannot_forward_budget_without_grap24_explanations(self, mock_get_user):
        from services.universal_workflow_service import UniversalWorkflowService

        mock_get_user.return_value = {"role": "FINANCE_MANAGER", "email": "fm@test.com"}
        session = SimpleNamespace(
            id="sess-budget-fm",
            user_id="clerk-1",
            document_type="budget_report",
            filename="budget.xlsx",
            status="mapped",
            metadata={
                "workflow_status": "pending_review",
                "submitted_at": "2026-05-20T10:00:00Z",
                "variance_explanations": {},
            },
            processing_log=[],
            updated_at=None,
        )
        mock_model = MagicMock()
        mock_model.get_session.return_value = session
        mock_model.update_session.side_effect = lambda s: s

        svc = UniversalWorkflowService()
        svc._get_model_for_document_type = MagicMock(return_value=mock_model)

        row_objs = [
            SimpleNamespace(
                row_index=r["row_index"],
                account_code=r.get("account_code", ""),
                account_description=r.get("account_description", ""),
                budget_amount=r["budget_amount"],
                actual_amount=r.get("actual_amount", 0),
                variance=r["variance"],
                is_total_row=r.get("is_total_row", False),
                is_subtotal_row=r.get("is_subtotal_row", False),
            )
            for r in _sample_rows()
            if not r.get("is_total_row")
        ]

        with patch("models.budget_report_models.budget_report_model.get_data_rows", return_value=row_objs):
            result = svc.approve_document("budget_report", "sess-budget-fm", "fm-1", notes="Forward")

        self.assertFalse(result["success"])
        err = result.get("error", "")
        self.assertTrue("GRAP 24" in err or "grap24" in err.lower(), err)

    @patch("services.universal_workflow_service.supabase_auth.get_user_by_id")
    @patch("services.inbox_service.notify_forwarded_to_cfo")
    def test_fm_forwards_budget_when_grap24_complete(self, _notify, mock_get_user):
        from services.universal_workflow_service import UniversalWorkflowService

        mock_get_user.return_value = {"role": "FINANCE_MANAGER", "email": "fm@test.com"}
        rows = _sample_rows()
        explanations = {"1": "Salaries overrun due to overtime in Q4."}
        session = SimpleNamespace(
            id="sess-budget-fm-ok",
            user_id="clerk-1",
            document_type="budget_report",
            filename="budget.xlsx",
            status="mapped",
            metadata={
                "workflow_status": "pending_review",
                "submitted_at": "2026-05-20T10:00:00Z",
                "variance_explanations": explanations,
            },
            processing_log=[],
            updated_at=None,
        )
        mock_model = MagicMock()
        mock_model.get_session.return_value = session
        mock_model.update_session.side_effect = lambda s: s

        svc = UniversalWorkflowService()
        svc._get_model_for_document_type = MagicMock(return_value=mock_model)
        svc._create_workflow_record = MagicMock(return_value={"id": "wf-fm"})

        with patch("models.budget_report_models.budget_report_model.get_data_rows") as mock_rows:
            mock_rows.return_value = [
                SimpleNamespace(
                    row_index=1,
                    account_code="100",
                    account_description="Salaries",
                    budget_amount=1000,
                    actual_amount=1150,
                    variance=150,
                    is_total_row=False,
                    is_subtotal_row=False,
                ),
            ]
            result = svc.approve_document("budget_report", "sess-budget-fm-ok", "fm-1", notes="Forward")

        self.assertTrue(result["success"])
        self.assertEqual(result["new_status"], "approved_by_manager")


if __name__ == "__main__":
    unittest.main()
