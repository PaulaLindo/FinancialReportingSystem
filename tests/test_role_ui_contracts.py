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
        js = read('static/js/submission-history.js')
        self.assertIn('submission-history-page--clerk', html)
        self.assertIn('id="statusFilter"', html)
        self.assertIn('id="submissionsList"', html)
        self.assertIn('btn-view-statement', html)
        self.assertIn('canViewStatementInHistory', js)
        self.assertNotIn('submissionDetailsModal', html)
        self.assertNotIn('btn-view-details', html)

    def test_upload_page_has_process_flow(self):
        js = read('static/js/upload.js')
        self.assertIn('getUploadProcessButtonLabel', js)
        self.assertIn('Continue to mapping', js)
        self.assertIn('viewBalanceDetails', js)
        self.assertNotIn('Feature Coming Soon', js)
        self.assertNotIn('Save for Later (Coming Soon)', js)

    def test_modal_system_has_varydian_app_confirm(self):
        js = read('static/js/modal-system.js')
        self.assertIn('varydianAppConfirm', js)
        self.assertNotIn('window.confirm(', js)

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

    def test_line_item_comment_wired_in_statement_review(self):
        js = read('static/js/financial-statement-review.js')
        base = read('templates/base.html')
        styles = read('static/css/styles.css')
        self.assertIn('data-action="line-item-comment"', js)
        self.assertIn('data-action="line-item-comment-view"', js)
        self.assertIn('renderLineItemCommentsAuditPanel', js)
        self.assertIn('openLineItemCommentForRow', js)
        self.assertIn('line-item-comment-modal.html', base)
        self.assertIn('line-item-comment-system.js', base)
        self.assertIn('line-item-comment-modal.css', styles)

    def test_line_item_comments_in_clerk_history(self):
        js = read('static/js/submission-history.js')
        self.assertIn('openClerkStatementReview', js)
        self.assertIn('line_item_comments', read('controllers/routes.py'))

    def test_line_item_comment_readonly_mode(self):
        js = read('static/js/line-item-comment-system.js')
        css = read('static/css/line-item-comment-modal.css')
        self.assertIn('readOnlyMode', js)
        self.assertIn('line-item-comment-modal--readonly', css)

    def test_confirm_modal_prevents_click_through(self):
        js = read('static/js/modal-system.js')
        self.assertIn('_bindModalActions', js)
        self.assertIn('modal-system-open', js)
        self.assertIn('settled', js)

    def test_cfo_finalize_confirm_dialog(self):
        js = read('static/js/financial-statement-review.js')
        queue_js = read('static/js/finance-manager-review-queue.js')
        self.assertIn('varydianCfoFinalizeConfirm', js)
        self.assertIn('irreversible without an audit log entry', js)
        self.assertIn('varydianCfoFinalizeConfirm', queue_js)


class CfoDashboardUiContractTests(unittest.TestCase):
    def test_cfo_dashboard_kpi_strip(self):
        html = read('templates/dashboard.html')
        self.assertIn('dashboard-cfo', html)
        self.assertIn('pending_finalization_count', html)
        self.assertIn('pending_material_journals_count', html)
        self.assertIn('surplus_deficit_total', html)
        self.assertIn('budget_variance_total', html)

    def test_dashboard_route_loads_cfo_kpis(self):
        src = read('controllers/routes.py')
        self.assertIn('get_cfo_dashboard_kpis', src)
        self.assertIn('count_pending_cfo_journals', src)
        self.assertIn("user.role == 'CFO'", src)


class LegacyRoutesRemovedTests(unittest.TestCase):
    def test_admin_page_requires_system_admin(self):
        src = read('controllers/routes.py')
        self.assertIn('can_manage_users()', src)
        self.assertIn('System Administrator privileges required', src)
        self.assertNotIn("user.role != 'CFO'", src)

    def test_login_redirects_by_role(self):
        src = read('controllers/routes.py')
        self.assertIn('_login_redirect_for_role', src)
        self.assertIn("url_for('finance_manager_review_queue')", src)
        self.assertIn("url_for('auditor_workspace_page')", src)
        self.assertIn("url_for('admin_page')", src)

    def test_finance_manager_api_routes_removed(self):
        src = read('controllers/routes_finance_manager.py')
        self.assertNotRegex(src, r"@app\.route\('/api/finance-manager/")
        self.assertIn('finance_manager_review_queue', src)
        self.assertIn('finance_manager_history', src)

    def test_clerk_statement_review_scripts_in_base(self):
        base = read('templates/base.html')
        self.assertIn("current_user.role == 'FINANCE_CLERK'", base)
        self.assertIn('financial-statement-review.js', base)
        self.assertIn('formula-modal.js', base)

    def test_clerk_can_open_statement_review_route(self):
        src = read('controllers/routes.py')
        self.assertIn("review_statement and user.role == 'FINANCE_CLERK'", src)
        self.assertIn('openClerkStatementReview', read('static/js/submission-history.js'))
        self.assertIn('/submission-history', read('static/js/financial-statement-review.js'))

    def test_submission_history_clerk_only_guard(self):
        src = read('controllers/routes.py')
        self.assertIn('def _finance_clerk_page_guard', src)
        self.assertIn('def _finance_clerk_api_guard', src)
        self.assertIn('_finance_clerk_page_guard(user)', src)
        self.assertIn('_finance_clerk_api_guard(user)', src)
        self.assertIn("redirect(url_for('finance_manager_history'))", src)

    def test_clerk_workflow_redirects_to_history(self):
        src = read('controllers/routes.py')
        self.assertIn("redirect(url_for('submission_history_page'))", src)
        self.assertIn('/finance-clerk-workflow', src)

    def test_session_metadata_helpers_used(self):
        src = read('controllers/routes.py')
        self.assertIn('resolve_line_item_comments', src)
        self.assertIn('clerk_submission_account_counts', src)
        self.assertIn('resolve_rejection_reason', src)

    def test_correction_workspace_reviewer_feedback(self):
        html = read('templates/mapping_interface.html')
        js = read('static/js/mapping-interface.js')
        self.assertIn('revisionReviewerFeedback', html)
        self.assertIn('revisionLineCommentsMount', html)
        self.assertIn('renderRevisionReviewerFeedback', js)
        self.assertIn('renderCategories()', js)


    def test_asset_manager_nav_badge_markup(self):
        base = read('templates/base.html')
        self.assertIn('data-journal-badge="am"', base)
        self.assertIn('/api/asset-manager/journals/pending/count', read('static/js/asset-journal-nav-badge.js'))

    def test_auditor_mobile_nav_journal_trail(self):
        base = read('templates/base.html')
        mobile_block = base.split('<!-- Mobile Menu -->', 1)[1]
        self.assertIn('/audit/asset-journals', mobile_block)
        self.assertIn('Journal trail', mobile_block)

    def test_mobile_inbox_nav_badge(self):
        base = read('templates/base.html')
        mobile_block = base.split('<!-- Mobile Menu -->', 1)[1]
        self.assertIn('nav-inbox-badge', mobile_block)
        self.assertIn('nav-inbox', mobile_block)
    def test_asset_manager_pages_and_nav(self):
        html = read('templates/asset_manager/register.html')
        base = read('templates/base.html')
        routes = read('controllers/routes_asset_manager.py')
        self.assertIn('asset-register-page', html)
        self.assertIn('btnOpenRegisterAsset', html)
        self.assertIn('asset-manager/reconciliation', base)
        self.assertIn('asset-manager/journals', base)
        self.assertIn('dashboard-asset-manager', read('templates/dashboard.html'))
        self.assertIn('disposal-journal', read('static/js/asset-detail.js'))
        self.assertIn('ASSET_MANAGER', base)
        self.assertIn('asset_manager_register_page', routes)
        self.assertIn('/api/asset-journals/pending', routes)

    def test_asset_manager_js_wired(self):
        reg_js = read('static/js/asset-register.js')
        self.assertIn('/api/asset-manager', reg_js)
        self.assertIn('useful-life-journal', read('static/js/asset-detail.js'))
        self.assertIn('/api/asset-journals/', read('static/js/fm-asset-journals.js'))

    def test_auth_redirects_asset_manager_to_dashboard(self):
        self.assertIn("'/dashboard'", read('static/js/auth.js'))
        self.assertIn("'ASSET_MANAGER'", read('static/js/auth.js'))

    def test_auditor_pages_and_nav(self):
        base = read('templates/base.html')
        dash = read('templates/dashboard.html')
        routes = read('controllers/routes_auditor.py')
        self.assertIn('/audit', base)
        self.assertIn('auditor_workspace_page', routes)
        self.assertIn('dashboard-auditor', dash)
        self.assertIn("'AUDITOR': '/audit'", read('static/js/auth.js'))
        self.assertIn("role === 'AUDITOR'", read('static/js/financial-statement-review.js'))


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
