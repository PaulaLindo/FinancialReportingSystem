"""UI contract tests — static assets encode role workflow requirements."""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel_path: str) -> str:
    path = ROOT / rel_path.replace('/', '\\') if '\\' in str(ROOT) else ROOT / rel_path
    return path.read_text(encoding='utf-8')


class ClerkUiContractTests(unittest.TestCase):
    def test_submission_history_has_filters_and_cards(self):
        html = read('templates/submission-history.html')
        self.assertIn('submission-history-page--clerk', html)
        self.assertIn('id="statusFilter"', html)
        self.assertIn('id="submissionsList"', html)
        self.assertIn('submissionDetailsModal', html)

    def test_upload_page_has_process_flow(self):
        js = read('static/js/upload.js')
        self.assertIn('getUploadProcessButtonLabel', js)
        self.assertIn('Continue to mapping', js)

    def test_mapping_interface_submit_path(self):
        js = read('static/js/mapping-interface.js')
        self.assertIn('/api/submit-mapping', js)
        self.assertIn('clerkSubmitReady', js)

    def test_clerk_cannot_approve_in_statement_review(self):
        js = read('static/js/financial-statement-review.js')
        self.assertIn("role === 'FINANCE_CLERK'", js)
        self.assertIn('Finance Clerks cannot approve', js)


class ReviewQueueUiContractTests(unittest.TestCase):
    def test_review_queue_template_cfo_batch_bar(self):
        html = read('templates/finance_manager_review_queue.html')
        self.assertIn('reviewQueueBatchBar', html)
        self.assertIn('reviewQueueBatchFinalizeBtn', html)
        self.assertIn('statementReviewPanel', html)

    def test_review_queue_js_role_filters(self):
        js = read('static/js/finance-manager-review-queue.js')
        self.assertIn("return st === 'pending_review'", js)
        self.assertIn('pending_cfo', js)
        self.assertIn('approved_by_manager', js)

    def test_fm_queue_no_card_approve_reject(self):
        js = read('static/js/finance-manager-review-queue.js')
        self.assertRegex(js, r'showApproveReject:\s*isCfo')
        self.assertNotRegex(js, r'showApproveReject:\s*true')

    def test_cfo_queue_has_quick_actions_and_batch(self):
        js = read('static/js/finance-manager-review-queue.js')
        self.assertIn('/api/universal/batch-approve', js)
        self.assertIn('selectable: isCfo', js)
        self.assertIn('transaction-select-cb', read('static/js/transaction-card-ui.js'))

    def test_approval_signatures_rendered_in_review(self):
        js = read('static/js/financial-statement-review.js')
        self.assertIn('renderApprovalSignaturesPanel', js)
        self.assertIn('approval_signatures', js)

    def test_formula_modal_line_click(self):
        js = read('static/js/financial-statement-review.js')
        self.assertIn('statement-line--clickable', js)
        self.assertIn('viewLineItemCalculation', js)


class LegacyRoutesRemovedTests(unittest.TestCase):
    def test_finance_manager_api_routes_removed(self):
        src = read('controllers/routes_finance_manager.py')
        self.assertNotRegex(src, r"@app\.route\('/api/finance-manager/")
        self.assertIn('finance_manager_review_queue', src)
        self.assertIn('finance_manager_history', src)

    def test_clerk_workflow_redirects_to_history(self):
        src = read('controllers/routes.py')
        self.assertIn("redirect(url_for('submission_history_page'))", src)
        self.assertIn('/finance-clerk-workflow', src)


class RlsVerificationScriptTests(unittest.TestCase):
    def test_verify_sql_documents_four_policies(self):
        sql = read('scripts/verify_supabase_cfo_migrations.sql')
        for name in (
            'Authenticated users can view financial periods',
            'CFO can lock financial periods',
            'Finance roles can create financial periods',
            'System admin can delete financial periods',
        ):
            self.assertIn(name, sql)


if __name__ == '__main__':
    unittest.main()
