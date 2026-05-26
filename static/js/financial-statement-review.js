/**
 * Varydian Financial Reporting System - Financial Statement Review
 * Integration with formula modal for Finance Manager review workflow
 */

/** Mandatory rejection reason dialog (shared with review queue quick actions). */
function varydianMandatoryRejectionReason() {
    return new Promise((resolve) => {
        const overlay = document.createElement('div');
        overlay.className = 'custom-prompt-overlay fm-reject-modal-overlay';
        overlay.innerHTML = `
            <div class="custom-prompt-modal fm-reject-modal">
                <div class="custom-prompt-header">
                    <h3>Reject submission</h3>
                    <button type="button" class="custom-prompt-close" aria-label="Cancel">✕</button>
                </div>
                <div class="custom-prompt-body">
                    <p class="fm-reject-modal__hint">A rejection reason is required and is recorded permanently. The submission returns to the Finance Clerk for correction.</p>
                    <label for="fmRejectReasonInput" class="fm-reject-modal__label">Rejection reason <span class="required">*</span></label>
                    <textarea id="fmRejectReasonInput" class="custom-prompt-textarea fm-reject-modal__input" rows="4" required placeholder="Describe what must be corrected…"></textarea>
                    <p class="fm-reject-modal__error element--hidden" id="fmRejectReasonError">Please enter a rejection reason.</p>
                </div>
                <div class="custom-prompt-footer">
                    <button type="button" class="btn btn-secondary fm-reject-cancel">Cancel</button>
                    <button type="button" class="btn btn-danger fm-reject-confirm">Reject</button>
                </div>
            </div>
        `;

        const textarea = overlay.querySelector('#fmRejectReasonInput');
        const errorEl = overlay.querySelector('#fmRejectReasonError');

        const close = () => {
            overlay.remove();
            resolve(null);
        };

        overlay.querySelector('.custom-prompt-close')?.addEventListener('click', close);
        overlay.querySelector('.fm-reject-cancel')?.addEventListener('click', close);
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) close();
        });

        overlay.querySelector('.fm-reject-confirm')?.addEventListener('click', () => {
            const value = (textarea?.value || '').trim();
            if (!value) {
                VarydianUtils.showElement(errorEl);
                textarea?.focus();
                return;
            }
            overlay.remove();
            resolve(value);
        });

        document.body.appendChild(overlay);
        setTimeout(() => textarea?.focus(), 100);
    });
}

window.varydianMandatoryRejectionReason = varydianMandatoryRejectionReason;

/** In-app confirm — defined in modal-system.js; CFO finalize uses it below. */
async function varydianCfoFinalizeConfirm(options = {}) {
    const count = Math.max(1, Number(options.count) || 1);
    const plural = count > 1;
    const title = plural ? `Finalize ${count} submissions` : 'Finalize period';
    const lockNote =
        'The entire reporting period is locked on the first final approval — clerks cannot upload further documents for that month, even if other document types are not yet finalized.';
    const message = plural
        ? `${lockNote} This action will final-approve ${count} submission(s) and is irreversible without an audit log entry. An audit trail record is written for each finalization. Continue?`
        : `${lockNote} This action is irreversible without an audit log entry. An audit trail record will be created. Continue?`;
    return window.varydianAppConfirm(title, message, {
        confirmText: plural ? 'Finalize all and lock' : 'Finalize and lock',
        cancelText: 'Cancel',
    });
}
window.varydianCfoFinalizeConfirm = varydianCfoFinalizeConfirm;

class FinancialStatementReview {
    constructor() {
        this.currentTransaction = null;
        this.statementData = null;
        this.reviewMode = null;
        this._sessionMetadataPayload = {};
        this.initializeReviewMode();
    }

    isEmbeddedFmReviewQueuePage() {
        return window.location.pathname.includes('/finance-manager/review-queue');
    }

    shouldShowEmbeddedReviewPanel() {
        if (!this.isEmbeddedFmReviewQueuePage()) return true;
        return window.financeManagerReviewQueue?._reviewPanelOpen === true;
    }

    initializeReviewMode() {
        const urlParams = new URLSearchParams(window.location.search);
        const returnTo = this.sanitizeReturnTo(urlParams.get('returnTo'));
        if (returnTo) {
            this._returnToUrl = returnTo;
        }
        if (this.isEmbeddedFmReviewQueuePage()) {
            return;
        }
        if (urlParams.get('review') === 'statement') {
            this.reviewMode = 'statement';
            const transactionId = urlParams.get('transaction');
            const documentType = urlParams.get('type');
            if (transactionId) {
                this.loadStatementForReview(transactionId, documentType);
            } else {
                this.showError('No transaction ID provided for review');
            }
        }
    }

    /** Allow only same-app relative paths for post-review navigation. */
    sanitizeReturnTo(path) {
        if (!path || typeof path !== 'string') return null;
        let decoded;
        try {
            decoded = decodeURIComponent(path.trim());
        } catch {
            return null;
        }
        if (!decoded.startsWith('/') || decoded.startsWith('//') || decoded.includes('://')) {
            return null;
        }
        const allowedPrefixes = ['/finance-manager/', '/approvals', '/dashboard', '/submission-history', '/audit'];
        if (!allowedPrefixes.some((p) => decoded === p || decoded.startsWith(p))) {
            return null;
        }
        return decoded;
    }

    /**
     * FM/CFO (and submission history) may view mappings/calculations but must not edit them.
     */
    isApproverOnlyReview() {
        if (this.isStatementReviewReadOnly()) {
            return true;
        }
        const role = window.currentUserRole || '';
        return role === 'FINANCE_MANAGER' || role === 'CFO';
    }

    isStatementReviewReadOnly() {
        const role = window.currentUserRole || '';
        if (role === 'FINANCE_CLERK' || role === 'AUDITOR') {
            return true;
        }
        if (this._returnToUrl && (
            this._returnToUrl.includes('/finance-manager/history')
            || this._returnToUrl.includes('/submission-history')
        )) {
            return true;
        }
        try {
            const raw = new URLSearchParams(window.location.search).get('returnTo');
            const r = this.sanitizeReturnTo(raw);
            return !!(
                r && (
                    r.includes('/finance-manager/history')
                    || r.includes('/submission-history')
                )
            );
        } catch {
            return false;
        }
    }

    isRejectedSettlementStatus() {
        const s = this.getEffectiveSessionStatus();
        return ['rejected', 'rejected_by_manager', 'rejected_by_cfo'].includes(s);
    }

    /**
     * Canonical workflow label (metadata.workflow_status wins over DB status alias).
     */
    getEffectiveSessionStatus() {
        const md = this._sessionMetadataPayload
            || this._rawSessionData?.metadata
            || this.currentTransaction?.metadata
            || {};
        const wf = md.workflow_status != null ? String(md.workflow_status).trim().toLowerCase() : '';
        if (wf) return wf;
        const fromSession = this._rawSessionData?.workflow_status || this._rawSessionData?.status;
        if (fromSession) return String(fromSession).trim().toLowerCase();
        const tx = this.currentTransaction || {};
        return String(tx.session_status || tx.status || '').trim().toLowerCase();
    }

    isCfoFinalizeAllowed() {
        const st = this.getEffectiveSessionStatus();
        return st === 'approved_by_manager' || st === 'pending_cfo';
    }

    isFmApproveAllowed() {
        return this.getEffectiveSessionStatus() === 'pending_review';
    }

    async ensureGrap24CompleteBeforeFinalize() {
        const docT = this.currentTransaction?.transaction_type || this._documentType || '';
        if (docT !== 'budget_report' || !window.BudgetVarianceGrap24) {
            return true;
        }
        const rows = (this._rawSessionData && this._rawSessionData.budget_rows) || [];
        const panel = document.getElementById('grap24VariancePanel');
        let explanations = (this._rawSessionData && this._rawSessionData.variance_explanations) || {};
        if (panel && panel.querySelector('.grap24-variance-input')) {
            explanations = BudgetVarianceGrap24.collectFromDom(panel);
        }
        const check = BudgetVarianceGrap24.validateExplanations(rows, explanations);
        if (!check.passed) {
            this.showError(
                'GRAP 24: provide variance explanations for all line items exceeding 10%: '
                + check.missing.slice(0, 5).join(', ')
                + (check.missing.length > 5 ? '…' : '')
            );
            return false;
        }
        if (check.required.length > 0 && panel && panel.querySelector('.grap24-variance-input')) {
            const result = await BudgetVarianceGrap24.saveExplanations(
                this.currentTransaction.transaction_id,
                'budget_report',
                explanations
            );
            if (!result.success) {
                this.showError(result.error || 'Could not save variance explanations');
                return false;
            }
            if (this._rawSessionData) {
                this._rawSessionData.variance_explanations = explanations;
                this._rawSessionData.grap24_variance_complete = true;
            }
        }
        return true;
    }

    getRejectionReasonDisplay() {
        const md = this._sessionMetadataPayload || {};
        let r = (md.rejection_reason || '').toString().trim();
        if (!r && Array.isArray(md.rejection_history) && md.rejection_history.length) {
            const last = md.rejection_history[md.rejection_history.length - 1];
            if (last && last.reason) r = String(last.reason).trim();
        }
        if (!r && md.manager_rejection && md.manager_rejection.reason) {
            r = String(md.manager_rejection.reason).trim();
        }
        return r;
    }

    formatApprovalRoleLabel(role) {
        const r = String(role || '').toUpperCase();
        const map = {
            FINANCE_MANAGER: 'Finance Manager',
            CFO: 'CFO',
            SYSTEM_ADMIN: 'System Admin',
        };
        return map[r] || (role ? String(role).replace(/_/g, ' ') : 'Reviewer');
    }

    renderApprovalSignaturesPanel() {
        const md = this._sessionMetadataPayload || {};
        const sigs = Array.isArray(md.approval_signatures) ? md.approval_signatures : [];
        if (!sigs.length) {
            return '';
        }
        const rows = sigs.map((sig) => {
            if (!sig || typeof sig !== 'object') return '';
            const role = this.formatApprovalRoleLabel(sig.role);
            const userId = String(sig.user_id || '—');
            const at = sig.at ? this.formatDate(sig.at) : '—';
            return `
                <li class="approval-signature-item">
                    <span class="approval-signature-role">${this.escapeHtml(role)}</span>
                    <span class="approval-signature-user" title="${this.escapeHtml(userId)}">${this.escapeHtml(userId.slice(0, 8))}${userId.length > 8 ? '…' : ''}</span>
                    <span class="approval-signature-at">${this.escapeHtml(at)}</span>
                </li>`;
        }).join('');
        return `
            <div class="approval-signatures-panel" aria-label="Approval signatures">
                <h4 class="approval-signatures-panel__title">Approval signatures</h4>
                <p class="section-intro text-muted">Recorded approvers for this submission (audit trail).</p>
                <ul class="approval-signatures-list">${rows}</ul>
            </div>`;
    }

    getLineItemCommentsFromMetadata() {
        const md = this._sessionMetadataPayload || {};
        let comments = Array.isArray(md.line_item_comments) ? md.line_item_comments.slice() : [];
        if (comments.length) return comments;

        const history = md.rejection_history;
        if (!Array.isArray(history)) return [];

        for (let i = history.length - 1; i >= 0; i -= 1) {
            const entry = history[i];
            if (!entry || typeof entry !== 'object') continue;
            if (Array.isArray(entry.line_item_comments) && entry.line_item_comments.length) {
                return entry.line_item_comments.slice();
            }
            const snap = entry.snapshot;
            if (snap && Array.isArray(snap.line_item_comments) && snap.line_item_comments.length) {
                return snap.line_item_comments.slice();
            }
        }
        return [];
    }

    getLineItemCommentsByAccount() {
        const map = {};
        for (const comment of this.getLineItemCommentsFromMetadata()) {
            const code = String(comment.account_code || '').trim();
            if (!code) continue;
            if (!map[code]) map[code] = [];
            map[code].push(comment);
        }
        return map;
    }

    accountLineItemCommentCount(accountCode) {
        const code = String(accountCode || '').trim();
        if (!code) return 0;
        return (this.getLineItemCommentsByAccount()[code] || []).length;
    }

    isSettledSessionForCommentArchive() {
        const st = this.getEffectiveSessionStatus();
        return [
            'approved',
            'rejected',
            'rejected_by_manager',
            'rejected_by_cfo',
            'closed',
        ].includes(st);
    }

    canAddLineItemCommentInReview() {
        const role = window.currentUserRole || '';
        if (this.isStatementReviewReadOnly()) return false;
        if (role === 'FINANCE_MANAGER') return this.isFmApproveAllowed();
        if (role === 'CFO') return this.isCfoFinalizeAllowed();
        return false;
    }

    shouldOpenLineItemCommentReadOnly() {
        if (this.canAddLineItemCommentInReview()) return false;
        const role = window.currentUserRole || '';
        return role === 'FINANCE_MANAGER' || role === 'CFO' || role === 'FINANCE_CLERK';
    }

    renderLineItemCommentsAuditPanel() {
        const comments = this.getLineItemCommentsFromMetadata();
        if (!comments.length) return '';

        const byAccount = this.getLineItemCommentsByAccount();
        const accountCodes = Object.keys(byAccount).sort();

        const groups = accountCodes.map((acct) => {
            const items = byAccount[acct];
            const body = items.map((c) => {
                const author = c.author_name || c.author_id || 'Reviewer';
                const text = c.comment_text || c.correction_suggestion || '';
                const subject = c.subject
                    ? `<div class="line-item-audit-comment__subject"><strong>${this.escapeHtml(c.subject)}</strong></div>`
                    : '';
                const correction = c.correction_suggestion && c.comment_text
                    ? `<p class="line-item-audit-comment__correction"><strong>Suggested fix:</strong> ${this.escapeHtml(c.correction_suggestion)}</p>`
                    : '';
                return `
                    <article class="line-item-audit-comment line-item-audit-comment--${this.escapeHtml(c.urgency_level || 'medium')}">
                        <header class="line-item-audit-comment__head">
                            <span class="line-item-audit-comment__meta">${this.escapeHtml(author)} · ${this.escapeHtml(c.comment_type || 'general')}</span>
                        </header>
                        ${subject}
                        <p class="line-item-audit-comment__text">${this.escapeHtml(text) || '<em class="text-muted">No comment text</em>'}</p>
                        ${correction}
                    </article>`;
            }).join('');

            return `
                <div class="line-item-audit-group">
                    <div class="line-item-audit-group__head">
                        <span class="line-item-audit-group__code">Account ${this.escapeHtml(acct)}</span>
                        <span class="line-item-audit-group__count">${items.length} comment${items.length === 1 ? '' : 's'}</span>
                    </div>
                    <div class="line-item-audit-group__body">${body}</div>
                </div>`;
        }).join('');

        return `
            <div class="line-item-comments-audit-panel" aria-label="Line item review comments">
                <h4 class="line-item-comments-audit-panel__title">Line item review comments</h4>
                <p class="section-intro text-muted">Reviewer notes recorded during statement review — preserved on approve, reject, and in history.</p>
                <div class="line-item-comments-audit-panel__groups">${groups}</div>
            </div>`;
    }

    getReviewReturnContext() {
        const urlParams = new URLSearchParams(window.location.search);
        const fromQuery = this.sanitizeReturnTo(urlParams.get('returnTo'));
        if (fromQuery) {
            return { url: fromQuery, label: this.labelForReturnUrl(fromQuery) };
        }
        if (this._returnToUrl) {
            return { url: this._returnToUrl, label: this.labelForReturnUrl(this._returnToUrl) };
        }
        if (this._returnToReviewQueue || window.location.pathname.includes('/finance-manager/review-queue')) {
            return { url: '/finance-manager/review-queue', label: 'review queue' };
        }
        if (this._returnToHistory || window.location.pathname.includes('/finance-manager/history')) {
            return { url: '/finance-manager/history', label: 'submission history' };
        }
        const role = window.currentUserRole || '';
        if (role === 'FINANCE_CLERK') {
            return { url: '/submission-history', label: 'submission history' };
        }
        if (role === 'FINANCE_MANAGER' || role === 'CFO') {
            return { url: '/finance-manager/review-queue', label: 'review queue' };
        }
        if (role === 'AUDITOR') {
            return { url: '/audit', label: 'audit workspace' };
        }
        return { url: '/dashboard', label: 'dashboard' };
    }

    labelForReturnUrl(url) {
        if (url.includes('/submission-history')) return 'submission history';
        if (url.includes('/finance-manager/history')) return 'submission history';
        if (url.includes('/finance-manager/review-queue')) return 'review queue';
        if (url.includes('/finance-manager/dashboard')) return 'review queue';
        if (url.includes('/audit')) return 'audit workspace';
        if (url.includes('/dashboard')) return 'dashboard';
        return 'review queue';
    }

    /**
     * Show dedicated review layout (hide approval queue chrome). Requires #statementReviewPanel on the page.
     */
    showStatementReviewLayout() {
        if (!this.shouldShowEmbeddedReviewPanel()) return;
        const panel = document.getElementById('statementReviewPanel');
        if (!panel) return;
        const page = document.querySelector('.approval-page');
        if (page) {
            VarydianUtils.hideElement(page.querySelector('.approval-header'));
            VarydianUtils.hideElement(page.querySelector('.approval-content'));
        }
        VarydianUtils.hideElement(document.querySelector('.fm-review-queue-section'));
        VarydianUtils.hideElement(document.querySelector('.fm-settled-history-section'));
        VarydianUtils.showElement(panel);
        this.updateStatementReviewBackLink();
    }

    updateStatementReviewBackLink() {
        const ctx = this.getReviewReturnContext();
        const bar = document.querySelector('.statement-review-panel__bar');
        if (!bar) return;

        const label = `← Back to ${ctx.label}`;
        const anchorBack = bar.querySelector('#statementReviewBackLink');
        if (anchorBack) {
            anchorBack.href = ctx.url;
            anchorBack.textContent = label;
            if (!anchorBack.dataset.statementReviewBackBound) {
                anchorBack.dataset.statementReviewBackBound = '1';
                anchorBack.addEventListener('click', (e) => {
                    if (e.button !== 0 || e.ctrlKey || e.metaKey || e.shiftKey || e.altKey) return;
                    e.preventDefault();
                    this.navigateBackFromStatementReview(e);
                });
            }
            return;
        }

        const embeddedBtn = bar.querySelector('a.btn, button.btn');
        if (embeddedBtn) {
            embeddedBtn.textContent = label;
            /* Finance Manager queue/history pages attach their own handler (e.g. hide embedded panel). */
        }
    }

    hideStatementReviewLayout() {
        const panel = document.getElementById('statementReviewPanel');
        if (!panel) return;
        VarydianUtils.hideElement(panel);
        const page = document.querySelector('.approval-page');
        if (page) {
            VarydianUtils.showElement(page.querySelector('.approval-header'));
            VarydianUtils.showElement(page.querySelector('.approval-content'));
        }
        if (this.isEmbeddedFmReviewQueuePage()) {
            if (window.financeManagerReviewQueue?.resetPageLayout) {
                window.financeManagerReviewQueue.resetPageLayout();
            } else {
                VarydianUtils.showElement(document.querySelector('.fm-review-queue-section'));
            }
            return;
        }
        VarydianUtils.showElement(document.querySelector('.fm-review-queue-section'));
        VarydianUtils.showElement(document.querySelector('.fm-settled-history-section'));
    }

    getReviewRedirectUrl() {
        return this.getReviewReturnContext().url;
    }

    /** After approve/reject on embedded review queue — return to list without full page reload. */
    completeReviewWorkflowAndReturn() {
        if (
            (this._returnToReviewQueue || window.location.pathname.includes('/finance-manager/review-queue'))
            && window.financeManagerReviewQueue
            && typeof window.financeManagerReviewQueue.hideReviewPanel === 'function'
        ) {
            window.financeManagerReviewQueue.hideReviewPanel();
            return true;
        }
        return false;
    }

    /**
     * When opening full-page statement review in a new tab from the formula modal, attach ?returnTo=...
     * so the dedicated review page knows where “back” should go if opener handling fails.
     */
    currentReturnToForAuxiliaryTab() {
        if (this._returnToUrl) {
            const s = this.sanitizeReturnTo(this._returnToUrl);
            if (s) return s;
        }
        const params = new URLSearchParams(window.location.search);
        if (window.location.pathname === '/approvals' && params.get('review') === 'statement') {
            return null;
        }
        const path = window.location.pathname + window.location.search;
        return this.sanitizeReturnTo(path) || null;
    }

    /**
     * Full-page statement review opened via window.open: focus the opener tab and close this tab when allowed.
     * Falls back to same-tab navigation when there is no opener (bookmark, typed URL, etc.).
     */
    navigateBackFromStatementReview(ev) {
        if (ev) {
            if (ev.button !== 0) return;
            if (ev.ctrlKey || ev.metaKey || ev.shiftKey || ev.altKey) return;
        }
        const fallback = this.getReviewRedirectUrl();
        try {
            if (window.opener && !window.opener.closed) {
                const o = window.opener;
                if (o.location.origin === window.location.origin) {
                    o.focus();
                    window.close();
                    return;
                }
            }
        } catch (_) {
            /* opener may be cross-origin or inaccessible */
        }
        if (this.isEmbeddedFmReviewQueuePage() && window.financeManagerReviewQueue?.hideReviewPanel) {
            window.financeManagerReviewQueue.hideReviewPanel();
            return;
        }
        window.location.href = fallback;
    }

    async loadStatementForReview(transactionId, documentType) {
        if (this.isEmbeddedFmReviewQueuePage() && window.financeManagerReviewQueue) {
            window.financeManagerReviewQueue._reviewPanelOpen = true;
        }
        this.showStatementReviewLayout();
        if (!this.shouldShowEmbeddedReviewPanel()) {
            return;
        }
        const reviewRoot = document.getElementById('statementReviewContent');
        if (reviewRoot) {
            reviewRoot.innerHTML = `
                <div class="approval-empty-state">
                    <div class="approval-empty-icon">📊</div>
                    <h3>Loading statement review…</h3>
                    <p>Fetching session and financial statements (position & performance).</p>
                </div>
            `;
        }
        console.log('📋 [Review] Loading statement for review:', transactionId);
        let targetType = documentType;
        if (!targetType) {
            if (transactionId.includes('-')) {
                const prefix = transactionId.split('-')[0].toUpperCase();
                const prefixMap = {
                    'INC': 'income_statement',
                    'BAL': 'balance_sheet',
                    'BUD': 'budget_report'
                };
                targetType = prefixMap[prefix] || 'balance_sheet';
                console.log(`🔍 [Review] Inferred document type from prefix "${prefix}": ${targetType}`);
            } else {
                targetType = 'balance_sheet';
                console.log(`🔍 [Review] Using default document type (balance_sheet) for UUID format`);
            }
        } else {
            console.log(`✅ [Review] Using provided document type: ${targetType}`);
        }

        try {
            console.log('📡 [Review] Fetching session from /api/universal/session/' + transactionId);
            const transactionResponse = await fetch(`/api/universal/session/${encodeURIComponent(transactionId)}?document_type=${encodeURIComponent(targetType)}`);
            const transactionResult = await transactionResponse.json();
            console.log('📊 [Review] Session response:', transactionResult);

            if (!transactionResponse.ok || transactionResult.error) {
                const err = transactionResult.error || `HTTP ${transactionResponse.status}`;
                console.error('❌ [Review] Failed to load session:', err);
                this.showError('Failed to load session: ' + err);
                this.renderReviewLoadError('Failed to load session: ' + err);
                return;
            }
            if (!transactionResult.session_id) {
                this.showError('Invalid session response (missing session_id)');
                this.renderReviewLoadError('Invalid session response (missing session_id)');
                return;
            }

            const sessionData = transactionResult;
            this._sessionId = sessionData.session_id;
            this._documentType = targetType;
            this._sessionMetadataPayload = sessionData.metadata || {};

            this.currentTransaction = {
                transaction_id: sessionData.session_id,
                transaction_type: targetType,
                session_status: sessionData.workflow_status || sessionData.status || '',
                creator_name: (function () {
                    const top = sessionData.creator_name && String(sessionData.creator_name).trim();
                    if (top) return top;
                    const md = sessionData.metadata || {};
                    const fromMd = (md.creator_name || md.submitted_by_name || '').toString().trim();
                    if (fromMd) return fromMd;
                    return 'Unknown submitter';
                })(),
                created_at: sessionData.created_at || new Date().toISOString(),
                filename: sessionData.filename || 'Document',
                status: sessionData.workflow_status || sessionData.status || 'pending',
                total_rows: sessionData.total_rows || 0,
                total_columns: sessionData.total_columns || 0
            };

            const built = this.buildStatementDataFromSession(sessionData);
            this.statementData = this.mergeSessionDerivedCalculations(sessionData, built);
            this._rawSessionData = sessionData;

            if (!this.shouldShowEmbeddedReviewPanel()) {
                return;
            }
            this.renderStatementReview();
        } catch (error) {
            console.error('💥 [Review] Network error:', error);
            this.showError('Network error loading statement data');
            if (!this.shouldShowEmbeddedReviewPanel()) {
                return;
            }
            this.renderReviewLoadError('Network error loading statement data');
        }
    }

    renderReviewLoadError(message) {
        if (!this.shouldShowEmbeddedReviewPanel()) {
            return;
        }
        const el = document.getElementById('statementReviewContent');
        if (!el) return;
        el.innerHTML = `
            <div class="approval-error-state">
                <div class="approval-error-icon">⚠️</div>
                <h3>Could not open review</h3>
                <p>${this.escapeHtml(message)}</p>
                <p><a class="btn btn-secondary btn-sm" data-statement-review-back href="${this.escapeHtml(this.getReviewRedirectUrl())}">← Back to ${this.escapeHtml(this.getReviewReturnContext().label)}</a></p>
            </div>
        `;
        el.querySelector('[data-statement-review-back]')?.addEventListener('click', (e) => {
            if (e.button !== 0 || e.ctrlKey || e.metaKey || e.shiftKey || e.altKey) return;
            e.preventDefault();
            this.navigateBackFromStatementReview(e);
        });
    }

    _incomeStatementPayloadFromSession(sessionData) {
        const docType = sessionData.document_type || '';
        if (docType !== 'income_statement') return null;
        const rows = sessionData.income_rows;
        if (!Array.isArray(rows) || !rows.length) return null;

        const md = sessionData.metadata || {};
        const lines = rows
            .filter((r) => !r.is_total_row && !r.is_subtotal_row)
            .map((r) => {
                const nb = Number(r.net_balance);
                const am = Number(r.amount);
                const rev = Number(r.revenue_amount);
                const exp = Number(r.expense_amount);
                let amount = 0;
                if (!Number.isNaN(rev) && Math.abs(rev) > 0.0001) amount = rev;
                else if (!Number.isNaN(exp) && Math.abs(exp) > 0.0001) amount = -Math.abs(exp);
                else if (!Number.isNaN(nb) && r.net_balance != null && String(r.net_balance).trim() !== '') {
                    amount = nb;
                } else if (!Number.isNaN(am)) {
                    amount = am;
                }
                const noteBits = [r.category, r.period].filter(Boolean);
                const unmapped =
                    r.mapping_status === 'unmapped' || !(r.mapped_to_grap || '').toString().trim();
                return {
                    account_code: String(
                        r.account_code != null && r.account_code !== '' ? r.account_code : `row-${r.row_index}`
                    ),
                    description: r.account_description || '—',
                    category: r.category || '',
                    grap_code: (r.mapped_to_grap || '').toString(),
                    amount,
                    note: noteBits.length ? noteBits.join(' · ') : 'Revenue/expense line from upload',
                    has_mapping_issue: unmapped,
                    needs_mapping_fix: unmapped,
                };
            });

        if (!lines.length) return null;

        const G = this._grap();
        let perfTotals = null;
        if (G && G.computePerformanceTotals) {
            const mapped = lines.map((l) => ({
                account_code: l.account_code,
                amount: l.amount,
                grap_code: l.grap_code,
            }));
            perfTotals = G.computePerformanceTotals(mapped);
        } else {
            const rev = lines.filter((l) => Number(l.amount) > 0).reduce((s, l) => s + Number(l.amount), 0);
            const exp = lines.filter((l) => Number(l.amount) < 0).reduce((s, l) => s + Math.abs(Number(l.amount)), 0);
            perfTotals = { revenue: rev, expenses: exp, net: rev - exp };
        }

        const period = sessionData.reporting_period || md.period || md.reporting_period || 'FY 2025-2026';
        return {
            lines,
            positionLines: [],
            performanceLines: lines,
            mappings: this._mappingsFromMetadata(md),
            calculations: [],
            total: perfTotals ? perfTotals.net : lines.reduce((s, l) => s + (parseFloat(l.amount) || 0), 0),
            period: String(period),
            financial_statements: null,
            document_type: docType,
            perfTotals,
        };
    }

    buildStatementDataFromSession(sessionData) {
        const md = sessionData.metadata || {};
        const docType = sessionData.document_type || '';

        if (docType === 'budget_report' && Array.isArray(sessionData.budget_rows) && sessionData.budget_rows.length) {
            const lines = sessionData.budget_rows
                .filter((r) => !r.is_total_row)
                .map((r) => {
                    const b = Number(r.budget_amount);
                    const a = Number(r.actual_amount);
                    const v = Number(r.variance);
                    const useActual = !Number.isNaN(a) && Math.abs(a) > 0.0001;
                    const amount = useActual ? a : (Number.isNaN(b) ? 0 : b);
                    const noteParts = [];
                    if (!Number.isNaN(b)) noteParts.push(`Budget ${this.formatNumber(b)}`);
                    if (!Number.isNaN(a)) noteParts.push(`Actual ${this.formatNumber(a)}`);
                    if (!Number.isNaN(v)) noteParts.push(`Var ${this.formatNumber(v)}`);
                    const unmapped = (r.mapping_status === 'unmapped') || !(r.mapped_to_grap || '').toString().trim();
                    return {
                        account_code: String(r.account_code != null && r.account_code !== '' ? r.account_code : `row-${r.row_index}`),
                        description: r.account_description || r.expense_category || '—',
                        grap_code: (r.mapped_to_grap || '').toString(),
                        amount,
                        note: noteParts.length ? noteParts.join(' · ') : '-',
                        has_mapping_issue: unmapped,
                        needs_mapping_fix: unmapped
                    };
                });
            const total = lines.reduce((s, l) => s + (parseFloat(l.amount) || 0), 0);
            const period = sessionData.reporting_period || md.period || md.reporting_period || 'FY 2025-2026';
            return {
                lines,
                positionLines: [],
                performanceLines: [],
                mappings: this._mappingsFromMetadata(md),
                calculations: [],
                total,
                period: String(period),
                financial_statements: null,
                document_type: docType
            };
        }

        const incomePayload = this._incomeStatementPayloadFromSession(sessionData);
        if (incomePayload) {
            return incomePayload;
        }

        const mappedLayout = this._statementLayoutFromMapped(docType, md);
        if (mappedLayout) {
            return {
                ...mappedLayout,
                mappings: this._mappingsFromMetadata(md),
                period: md.period || sessionData.reporting_period || 'FY 2025-2026',
                financial_statements:
                    sessionData.financial_statements || mappedLayout.financial_statements,
                document_type: docType || mappedLayout.document_type
            };
        }

        const legacy = md.statement_data;
        if (legacy && Array.isArray(legacy.lines) && legacy.lines.length) {
            return {
                ...legacy,
                mappings: legacy.mappings || this._mappingsFromMetadata(md),
                calculations: legacy.calculations || [],
                financial_statements: sessionData.financial_statements || null
            };
        }

        const fs = sessionData.financial_statements;
        if (
            fs &&
            fs.statement_of_financial_position &&
            docType !== 'income_statement' &&
            docType !== 'budget_report'
        ) {
            const positionLines = this.flattenPositionAccounts(fs.statement_of_financial_position);
            const perf = fs.statement_of_financial_performance || {};
            const performanceLines = [
                ...this.flattenPerformanceAccounts(perf.revenue, 'Revenue'),
                ...this.flattenPerformanceAccounts(perf.expenses, 'Expenses')
            ];
            const surplus = perf.surplus;
            const calculations = [];
            if (typeof surplus === 'number') {
                calculations.push({
                    id: 'surplus',
                    description: 'Surplus / (deficit) for the period',
                    formula: 'Total revenue − Total expenses',
                    result: surplus,
                    verified: false
                });
            }
            return {
                lines: [...positionLines, ...performanceLines],
                positionLines,
                performanceLines,
                mappings: this._mappingsFromMetadata(md),
                calculations,
                total: fs.statement_of_financial_position.assets?.total || 0,
                period: md.period || 'FY 2025-2026',
                financial_statements: fs,
                document_type: sessionData.document_type || 'balance_sheet'
            };
        }

        return {
            lines: [],
            positionLines: [],
            performanceLines: [],
            mappings: this._mappingsFromMetadata(md),
            calculations: [],
            total: 0,
            period: md.period || 'FY 2025-2026',
            financial_statements: null
        };
    }

    /**
     * Add calculation rows from session summary + structured statements so the Calculations tab
     * and formula modal show real numbers (not only placeholders) when Supabase/session returns them.
     */
    _grap() {
        return typeof window !== 'undefined' ? window.GrapStandards : null;
    }

    _mappedLinesFromMetadata(md) {
        const G = this._grap();
        if (G && G.mappedLinesFromMetadata) {
            return G.mappedLinesFromMetadata(md || {});
        }
        return [];
    }

    _statementLayoutFromMapped(docType, md) {
        const dt = String(docType || '').toLowerCase();
        const G = this._grap();
        if (!G || !G.buildFinancialStatementsFromMapped) return null;
        const mapped = this._mappedLinesFromMetadata(md);
        if (!mapped.length) return null;

        if (dt === 'balance_sheet') {
            const built = G.buildFinancialStatementsFromMapped(mapped);
            const positionLines = [
                ...this.flattenPerformanceAccounts({ accounts: built.assets }, 'Assets'),
                ...this.flattenPerformanceAccounts({ accounts: built.liabilities }, 'Liabilities'),
                ...this.flattenPerformanceAccounts({ accounts: built.equity }, 'Equity')
            ];
            const performanceLines = [
                ...this.flattenPerformanceAccounts({ accounts: built.revenue }, 'Revenue'),
                ...this.flattenPerformanceAccounts({ accounts: built.expenses }, 'Expenses')
            ];
            const calculations = [];
            const st = built.sfpTotals;
            if (st) {
                calculations.push({
                    id: 'grap-sfp-assets',
                    description: 'GRAP 1 (SFP) — Total assets',
                    formula: 'Σ asset balances (1xxx / CA·NC, debit-normal)',
                    result: st.assets,
                    verified: true
                });
                calculations.push({
                    id: 'grap-sfp-liabilities',
                    description: 'GRAP 1 (SFP) — Total liabilities',
                    formula: 'Σ liability balances (2xxx / CL·NL, credit-normal)',
                    result: st.liabilities,
                    verified: true
                });
                calculations.push({
                    id: 'grap-sfp-equity',
                    description: 'GRAP 1 (SFP) — Total equity',
                    formula: 'Σ equity balances (3xxx / EQ, credit-normal)',
                    result: st.equity,
                    verified: true
                });
                calculations.push({
                    id: 'grap-sfp-difference',
                    description: 'GRAP 1 (SFP) — Accounting equation',
                    formula: 'Assets − (Liabilities + Equity)',
                    result: st.difference,
                    verified: st.balanced
                });
            }
            const pt = built.perfTotals;
            if (pt && (pt.revenue || pt.expenses)) {
                calculations.push({
                    id: 'sfper-net',
                    description: 'SFPER — Surplus / (deficit)',
                    formula: 'Total revenue − Total expenses (4xxx/5xxx)',
                    result: pt.net,
                    verified: false
                });
            }
            return {
                lines: [...positionLines, ...performanceLines],
                positionLines,
                performanceLines,
                calculations,
                sfpTotals: st,
                perfTotals: pt,
                total: st ? st.assets : 0,
                document_type: 'balance_sheet',
                financial_statements: {
                    statement_of_financial_position: {
                        assets: { accounts: built.assets, total: st.assets },
                        liabilities: { accounts: built.liabilities, total: st.liabilities },
                        equity: { accounts: built.equity, total: st.equity }
                    },
                    statement_of_financial_performance: {
                        revenue: { accounts: built.revenue, total: pt.revenue },
                        expenses: { accounts: built.expenses, total: pt.expenses },
                        surplus: pt.net
                    }
                }
            };
        }

        if (dt === 'income_statement') {
            const built = G.buildFinancialStatementsFromMapped(mapped);
            const performanceLines = [
                ...this.flattenPerformanceAccounts({ accounts: built.revenue }, 'Revenue'),
                ...this.flattenPerformanceAccounts({ accounts: built.expenses }, 'Expenses')
            ];
            const pt = built.perfTotals;
            if (!performanceLines.length && !(pt && (pt.revenue || pt.expenses))) {
                return null;
            }
            const calculations = [
                {
                    id: 'grap-perf-revenue',
                    description: 'GRAP 1 (Performance) — Total revenue',
                    formula: 'Σ |amount| for revenue / 4xxx lines',
                    result: pt.revenue,
                    verified: pt.revenue > 0
                },
                {
                    id: 'grap-perf-expenses',
                    description: 'GRAP 1 (Performance) — Total expenses',
                    formula: 'Σ |amount| for expense / 5xxx lines',
                    result: pt.expenses,
                    verified: pt.expenses > 0
                },
                {
                    id: 'grap-perf-net',
                    description: 'GRAP 1 (Performance) — Net surplus / (deficit)',
                    formula: 'Revenue − Expenses',
                    result: pt.net,
                    verified: pt.revenue > 0 || pt.expenses > 0
                }
            ];
            return {
                lines: performanceLines,
                positionLines: [],
                performanceLines,
                calculations,
                perfTotals: pt,
                total: pt.net,
                document_type: 'income_statement',
                financial_statements: null
            };
        }

        return null;
    }

    mergeSessionDerivedCalculations(sessionData, sd) {
        const calcs = [...(sd.calculations || [])];
        const pushCalc = (id, description, formula, result, verified = false) => {
            if (!id || calcs.some(c => c && c.id === id)) return;
            const r = typeof result === 'number' && !Number.isNaN(result) ? result : result;
            calcs.push({ id, description, formula, result: r, verified: !!verified });
        };

        const docType = sessionData.document_type || sd.document_type || '';
        const md = sessionData.metadata || {};
        const G = this._grap();
        const mapped = this._mappedLinesFromMetadata(md);
        if (G && mapped.length) {
            if (docType === 'balance_sheet' && G.computeSfpTotals) {
                const st = G.computeSfpTotals(mapped);
                pushCalc('grap-mapped-assets', 'GRAP 1 (SFP) — Assets (mapped, approval check)', 'Σ classified asset balances', st.assets, true);
                pushCalc('grap-mapped-liabilities', 'GRAP 1 (SFP) — Liabilities (mapped)', 'Σ classified liability balances', st.liabilities, true);
                pushCalc('grap-mapped-equity', 'GRAP 1 (SFP) — Equity (mapped)', 'Σ classified equity balances', st.equity, true);
                pushCalc('grap-mapped-le', 'GRAP 1 (SFP) — Liabilities + Equity', 'Liabilities + Equity', st.liabilities_plus_equity, true);
                pushCalc('grap-mapped-diff', 'GRAP 1 (SFP) — Difference', 'Assets − (Liabilities + Equity)', st.difference, st.balanced);
            }
            if ((docType === 'balance_sheet' || docType === 'income_statement') && G.computePerformanceTotals) {
                const pt = G.computePerformanceTotals(mapped);
                pushCalc('grap-mapped-revenue', 'SFPER — Revenue (mapped)', 'Σ |amount| revenue / 4xxx', pt.revenue, pt.revenue > 0);
                pushCalc('grap-mapped-expenses', 'SFPER — Expenses (mapped)', 'Σ |amount| expense / 5xxx', pt.expenses, pt.expenses > 0);
                pushCalc('grap-mapped-surplus', 'SFPER — Net surplus / (deficit)', 'Revenue − Expenses', pt.net, pt.revenue > 0 || pt.expenses > 0);
            }
        }

        const fs = sessionData.financial_statements || sd.financial_statements;
        if (fs && fs.statement_of_financial_position) {
            const sfp = fs.statement_of_financial_position;
            const assetsT = sfp.assets?.total;
            const liabT = sfp.liabilities?.total;
            const eqT = sfp.equity?.total;
            if (typeof assetsT === 'number' && !Number.isNaN(assetsT)) {
                pushCalc('sfp-assets', 'SFP — total assets', 'statement_of_financial_position.assets.total', assetsT, true);
            }
            if (typeof liabT === 'number' && !Number.isNaN(liabT)) {
                pushCalc('sfp-liabilities', 'SFP — total liabilities', 'statement_of_financial_position.liabilities.total', liabT, true);
            }
            if (typeof eqT === 'number' && !Number.isNaN(eqT)) {
                pushCalc('sfp-equity', 'SFP — total equity', 'statement_of_financial_position.equity.total', eqT, true);
            }
            if (typeof assetsT === 'number' && typeof liabT === 'number' && typeof eqT === 'number') {
                const rhs = liabT + eqT;
                const diff = assetsT - rhs;
                pushCalc('sfp-balance', 'SFP — accounting equation', 'Assets − (Liabilities + Equity)', diff, Math.abs(diff) < 0.02);
            }
        }

        const perf = fs && fs.statement_of_financial_performance;
        if (perf) {
            const sumBlock = (block) => ((block && block.accounts) || []).reduce(
                (s, a) => s + (Number(a.net_balance != null ? a.net_balance : a.amount) || 0),
                0
            );
            const rev = sumBlock(perf.revenue);
            const exp = sumBlock(perf.expenses);
            if (rev !== 0 || (perf.revenue && perf.revenue.accounts && perf.revenue.accounts.length)) {
                pushCalc('sfper-revenue', 'SFPER — total revenue', 'Sum of revenue accounts', rev, true);
            }
            if (exp !== 0 || (perf.expenses && perf.expenses.accounts && perf.expenses.accounts.length)) {
                pushCalc('sfper-expenses', 'SFPER — total expenses', 'Sum of expense accounts', exp, true);
            }
        }

        const pos = sd.positionLines || [];
        const pl = sd.performanceLines || [];
        const legacyLines = sd.lines || [];
        if (pos.length) {
            const t = this._sumLineAmounts(pos);
            pushCalc('sum-position-lines', 'Sum of SFP line amounts (flattened)', 'Σ amount for position lines', t, false);
        }
        if (pl.length) {
            const t = this._sumLineAmounts(pl);
            pushCalc('sum-performance-lines', 'Sum of SFPER line amounts (flattened)', 'Σ amount for performance lines', t, false);
        }
        if (legacyLines.length && !pos.length && !pl.length) {
            const t = this._sumLineAmounts(legacyLines);
            pushCalc('legacy-line-total', 'Total of statement lines (legacy payload)', 'Σ line.amount', t, false);
        }

        const mapArr = md.grap_mapping?.mapping_data;
        if (Array.isArray(mapArr) && mapArr.length) {
            pushCalc('mapping-rows', 'Mapped trial-balance rows', 'metadata.grap_mapping.mapping_data.length', mapArr.length, true);
        }
        if (sessionData.total_rows != null && sessionData.total_rows !== '') {
            const n = Number(sessionData.total_rows);
            if (!Number.isNaN(n)) {
                pushCalc('session-rows', 'Uploaded data rows', 'session.total_rows (database)', n, true);
            }
        }
        if (sessionData.mapped_accounts_count != null && sessionData.mapped_accounts_count !== '') {
            const n = Number(sessionData.mapped_accounts_count);
            if (!Number.isNaN(n)) {
                pushCalc('session-mapped-count', 'Mapped accounts (session summary)', 'session.mapped_accounts_count', n, false);
            }
        }

        if (sessionData.document_type === 'budget_report') {
            const tb = Number(sessionData.total_budget);
            const ta = Number(sessionData.total_actual);
            const tv = Number(sessionData.total_variance);
            if (!Number.isNaN(tb)) {
                pushCalc('budget-total-budget', 'Budget — total budget (session)', 'session.total_budget', tb, false);
            }
            if (!Number.isNaN(ta)) {
                pushCalc('budget-total-actual', 'Budget — total actual (session)', 'session.total_actual', ta, false);
            }
            if (!Number.isNaN(tv)) {
                pushCalc('budget-total-variance', 'Budget — total variance', 'session.total_variance', tv, false);
            }
            const br = sessionData.budget_rows;
            if (Array.isArray(br) && br.length) {
                pushCalc('budget-data-rows', 'Budget line items loaded', 'budget_rows.length', br.length, true);
            }
        }

        if (sessionData.document_type === 'income_statement') {
            const trv = Number(sessionData.total_revenue);
            const tex = Number(sessionData.total_expenses);
            const tni = Number(sessionData.net_income);
            if (!Number.isNaN(trv)) {
                pushCalc('is-total-revenue', 'Income — total revenue (session)', 'session.total_revenue', trv, false);
            }
            if (!Number.isNaN(tex)) {
                pushCalc('is-total-expenses', 'Income — total expenses (session)', 'session.total_expenses', tex, false);
            }
            if (!Number.isNaN(tni)) {
                pushCalc('is-net-income', 'Income — net income (session)', 'session.net_income', tni, false);
            }
            const ir = sessionData.income_rows;
            if (Array.isArray(ir) && ir.length) {
                pushCalc('income-data-rows', 'Income line items loaded', 'income_rows.length', ir.length, true);
            }
            const pt = this._resolvePerformanceTotals('income_statement', sd, sessionData);
            if (this._hasPerformanceTotals(pt)) {
                pushCalc('grap-perf-revenue', 'GRAP 1 (Performance) — Total revenue', 'Σ revenue / REV / 4xxx lines', pt.revenue, pt.revenue > 0);
                pushCalc('grap-perf-expenses', 'GRAP 1 (Performance) — Total expenses', 'Σ expense / EXP / 5xxx lines', pt.expenses, pt.expenses > 0);
                pushCalc('grap-perf-net', 'GRAP 1 (Performance) — Net surplus / (deficit)', 'Revenue − Expenses', pt.net, pt.revenue > 0 || pt.expenses > 0);
            }
        }

        const vmap = md.calculation_verifications;
        if (vmap && typeof vmap === 'object') {
            for (const c of calcs) {
                const rec = vmap[String(c.id)];
                if (rec && rec.verified) {
                    c.verified = true;
                }
            }
        }

        const out = { ...sd, calculations: calcs };
        if (sd.sfpTotals) out.sfpTotals = sd.sfpTotals;
        const resolvedPerfTotals = this._resolvePerformanceTotals(sessionData.document_type, sd, sessionData);
        if (this._hasPerformanceTotals(resolvedPerfTotals)) {
            out.perfTotals = resolvedPerfTotals;
        } else if (sd.perfTotals) {
            out.perfTotals = sd.perfTotals;
        }
        return out;
    }

    _sumLineAmounts(lines) {
        return (lines || []).reduce((s, l) => s + (parseFloat(l.amount) || 0), 0);
    }

    flattenPositionAccounts(sfp) {
        const out = [];
        const sections = [
            ['Assets', sfp.assets],
            ['Liabilities', sfp.liabilities],
            ['Equity', sfp.equity]
        ];
        for (const [label, block] of sections) {
            const accounts = (block && block.accounts) || [];
            for (const acc of accounts) {
                out.push(this.normalizedAccountRow(acc, `${label}`));
            }
        }
        return out;
    }

    flattenPerformanceAccounts(block, label) {
        const accounts = (block && block.accounts) || [];
        return accounts.map(acc => this.normalizedAccountRow(acc, label));
    }

    normalizedAccountRow(acc, sectionPrefix) {
        const code = acc.account_code || acc.tb_account_code || acc.grap_code || '—';
        const descRaw = acc.account_desc || acc.tb_account_description || acc.description || acc.grap_name || '';
        const desc = sectionPrefix ? `${sectionPrefix}: ${descRaw}` : descRaw;
        const nb = acc.net_balance;
        const am = acc.amount;
        const hasNb = nb != null && String(nb).trim() !== '' && !Number.isNaN(Number(nb));
        const hasAm = am != null && String(am).trim() !== '' && !Number.isNaN(Number(am));
        const amount = hasNb ? Number(nb) : (hasAm ? Number(am) : 0);
        const needs_mapping_fix = !hasNb && !hasAm;
        return {
            account_code: String(code),
            description: desc,
            grap_code: acc.grap_code || '',
            amount,
            note: acc.note || '-',
            has_mapping_issue: acc.confidence != null && acc.confidence < 0.5,
            needs_mapping_fix
        };
    }

    _mappingsFromMetadata(md) {
        const gm = md.grap_mapping;
        if (gm && Array.isArray(gm.mapping_data)) {
            return gm.mapping_data.map(m => ({
                tb_account_code: m.tb_account || m.account_code || '',
                tb_account_description: m.tb_account_description || m.account_desc || '',
                grap_code: m.grap_code || m.grap_line_item || '',
                grap_description: m.grap_name || '',
                mapped: true,
                confidence: (m.confidence != null ? m.confidence : 1) * 100
            }));
        }
        const mapped = md.mapped_data;
        if (Array.isArray(mapped)) {
            return mapped.map(m => ({
                tb_account_code: m.account_code || m.tb_account_code || '',
                tb_account_description: m.account_desc || m.tb_account_description || '',
                grap_code: m.grap_code || '',
                grap_description: m.grap_name || '',
                mapped: !!m.grap_code,
                confidence: (m.confidence != null ? m.confidence : 0.8) * 100
            }));
        }
        return [];
    }

    renderStatementReview() {
        if (!this.shouldShowEmbeddedReviewPanel()) {
            return;
        }
        const container = document.getElementById('statementReviewContent');
        if (!container) {
            console.warn('[Review] #statementReviewContent missing — add statement review panel to approvals template.');
            return;
        }
        this.showStatementReviewLayout();

        const role = window.currentUserRole || '';
        const isCfo = role === 'CFO';
        const isFm = role === 'FINANCE_MANAGER';
        const isClerk = role === 'FINANCE_CLERK';
        const readOnly = this.isStatementReviewReadOnly();
        const sessionStatus = this.getEffectiveSessionStatus();
        const cfoCanFinalize = isCfo && this.isCfoFinalizeAllowed();
        const fmCanApprove = isFm && this.isFmApproveAllowed();
        const canWorkflowAct = readOnly
            ? false
            : isClerk
                ? false
                : isCfo
                    ? cfoCanFinalize
                    : isFm
                        ? fmCanApprove
                        : false;
        const approveLabel = isCfo ? '✓ Finalize' : '✓ Approve';
        const finalizeTitle = isCfo && !cfoCanFinalize
            ? ' title="Awaiting Finance Manager approval before finalization"'
            : '';
        const approveDisabledAttr = canWorkflowAct ? '' : ' disabled';
        const shortTid = this.formatShortTransactionId(this.currentTransaction.transaction_id);
        const docT = this.currentTransaction.transaction_type || this._documentType || '';
        const statementTabLabel = this.getStatementTabLabel(docT);
        const md = this._sessionMetadataPayload || {};
        const canFmCertificate =
            isFm &&
            (this.getEffectiveSessionStatus() === 'pending_cfo' ||
                !!(md.manager_approval && md.manager_approval.at));

        const workflowButtons = readOnly || isClerk
            ? ''
            : `
                        <button type="button" class="btn btn-success" data-action="approve-forward"${approveDisabledAttr}${finalizeTitle}>
                            ${approveLabel}
                        </button>
                        <button type="button" class="btn btn-danger" data-action="reject-statement"${approveDisabledAttr}>
                            ✗ Reject
                        </button>`;

        let commentsSectionHtml = '';
        const lineItemAuditPanel = this.renderLineItemCommentsAuditPanel();
        if (readOnly) {
            if (this.isRejectedSettlementStatus()) {
                const reason = this.getRejectionReasonDisplay();
                commentsSectionHtml = `
                ${lineItemAuditPanel}
                <div class="review-comments-section review-comments-section--readonly">
                    <h4>Rejection reason</h4>
                    <p class="section-intro text-muted" style="margin: 0 0 0.75rem;">Recorded when this submission was returned for correction.</p>
                    <div class="rejection-reason-display">${
                        reason
                            ? `<p class="rejection-reason-text">${this.escapeHtml(reason)}</p>`
                            : '<p class="text-muted">No detailed reason was recorded.</p>'
                    }</div>
                </div>`;
            } else {
                commentsSectionHtml = lineItemAuditPanel;
            }
        } else {
            commentsSectionHtml = `
                <div class="review-comments-section">
                    <h4>Review notes (optional approval)</h4>
                    <p class="section-intro text-muted" style="margin: 0 0 0.5rem;">Approval may include these notes below (optional). <strong>Rejection</strong> always opens a mandatory reason dialog.</p>
                    <div class="comments-container">
                        <div class="existing-comments" id="existingComments"></div>
                        <div class="add-comment">
                            <textarea id="reviewComment" class="comment-textarea" placeholder="Optional; these notes are sent with approval when you use Approve above or below."></textarea>
                            <div class="comment-actions">
                                <button type="button" class="btn btn-primary btn-sm" data-action="approve-with-notes"${approveDisabledAttr}${finalizeTitle}>
                                    ✓ ${isCfo ? 'Finalize' : 'Approve'} with notes
                                </button>
                                <button type="button" class="btn btn-danger btn-sm" data-action="reject-statement"${approveDisabledAttr}>
                                    ✗ Reject (reason required)
                                </button>
                            </div>
                        </div>
                    </div>
                </div>`;
        }

        const reviewHTML = `
            <div class="statement-review-container">
                <!-- Review Header -->
                <div class="review-header-info">
                    <div class="transaction-info">
                        <h3>${this.escapeHtml(this.getStatementTitle(docT))}</h3>
                        <div class="transaction-meta">
                            <span class="transaction-id" title="${this.escapeHtml(shortTid.full)}">${this.escapeHtml(shortTid.display)}</span>
                            <span class="transaction-type-label">${this.escapeHtml(this.getTransactionTypeLabel(docT))}</span>
                            <span class="creator">Submitted by ${this.escapeHtml(this.currentTransaction.creator_name)}</span>
                            <span class="created-date">${this.formatDate(this.currentTransaction.created_at)}</span>
                            <span class="transaction-status">Status: ${this.escapeHtml(VarydianUtils.formatWorkflowStatus(this.getEffectiveSessionStatus() || ''))}</span>
                        </div>
                    </div>
                    <div class="review-actions">
                        <button type="button" class="btn btn-primary" data-action="view-calculations">
                            🔍 View Calculations
                        </button>
                        ${canFmCertificate ? `
                        <button type="button" class="btn btn-outline-secondary btn-sm" data-action="download-manager-certificate" title="Generate and download the manager’s certificate PDF">
                            📄 Manager’s certificate
                        </button>` : ''}
                        ${workflowButtons}
                    </div>
                </div>

                ${this.renderReviewerRoleBanner()}

                ${this.renderApprovalSignaturesPanel()}

                ${lineItemAuditPanel && !readOnly ? lineItemAuditPanel : ''}

                <!-- Statement Content -->
                <div class="statement-content-section">
                    <div class="statement-tabs">
                        <button class="tab-btn active" data-tab="statement">${this.escapeHtml(statementTabLabel)}</button>
                        <button class="tab-btn" data-tab="mappings">Account Mappings</button>
                        <button class="tab-btn" data-tab="calculations">Calculations</button>
                        <button class="tab-btn" data-tab="history" data-history-tab-label="Submission history">Submission history</button>
                    </div>

                    <div class="tab-content">
                        <!-- Financial Statement Tab -->
                        <div class="tab-pane active" id="statement-tab">
                            ${this.renderFinancialStatement()}
                        </div>

                        <!-- Account Mappings Tab -->
                        <div class="tab-pane" id="mappings-tab">
                            ${this.renderAccountMappings()}
                        </div>

                        <!-- Calculations Tab -->
                        <div class="tab-pane" id="calculations-tab">
                            ${this.renderCalculationsSummary()}
                        </div>

                        <!-- Audit timeline (original submit → rejection → clerk correction) -->
                        <div class="tab-pane" id="history-tab">
                            <div id="workflowTimelineMount" class="workflow-timeline-mount">
                                <p class="muted">Loading workflow history…</p>
                            </div>
                        </div>
                    </div>
                </div>

                ${commentsSectionHtml}
            </div>
        `;

        container.innerHTML = reviewHTML;
        if (!this.isStatementReviewReadOnly()) {
            this.populateReviewCommentDraftFromSession();
        }
        this.attachReviewListeners();
        this.initializeTabs();
        this.loadWorkflowTimelineForReview();
    }

    async loadWorkflowTimelineForReview() {
        const mount = document.getElementById('workflowTimelineMount');
        if (!mount) return;
        const sessionId = this._sessionId || (this.currentTransaction && this.currentTransaction.transaction_id);
        const docType = this._documentType || (this.currentTransaction && this.currentTransaction.transaction_type);
        if (!sessionId || !docType) {
            mount.innerHTML = '<p class="muted">No session context for timeline.</p>';
            return;
        }
        try {
            const res = await fetch(
                `/api/universal/session/${encodeURIComponent(sessionId)}/workflow-timeline?document_type=${encodeURIComponent(docType)}`,
                { credentials: 'same-origin' }
            );
            const data = await res.json();
            if (!data.success) {
                mount.innerHTML = `<p class="muted">${this.escapeHtml(data.error || 'Could not load history')}</p>`;
                return;
            }
            const timeline = data.timeline || [];
            this.updateHistoryTabLabel(timeline, data.timeline_tab_label);
            mount.innerHTML = this.renderWorkflowTimelineHtml(timeline);
        } catch (_e) {
            mount.innerHTML = '<p class="muted">Could not load submission history.</p>';
        }
    }

    timelineHasResubmission(events) {
        return (events || []).some((ev) => ev && ev.type === 'clerk_resubmission');
    }

    updateHistoryTabLabel(events, apiLabel) {
        const label =
            apiLabel ||
            (this.timelineHasResubmission(events) ? 'Resubmission history' : 'Submission history');
        const btn = document.querySelector('#statementReviewContent .tab-btn[data-tab="history"]');
        if (btn) {
            btn.textContent = label;
            btn.setAttribute('data-history-tab-label', label);
        }
    }

    getStatementTabLabel(docType) {
        const labels = {
            balance_sheet: 'Financial position',
            income_statement: 'Financial performance',
            budget_report: 'Budget vs actual',
        };
        return labels[docType] || 'Financial statements';
    }

    renderWorkflowTimelineHtml(events) {
        if (!events || !events.length) {
            const local = this.buildTimelineFromSessionMetadata();
            if (local.length) {
                this.updateHistoryTabLabel(local);
                return this.renderWorkflowTimelineList(local);
            }
            return '<p class="muted">No prior submissions or rejections recorded for this session yet.</p>';
        }
        this.updateHistoryTabLabel(events);
        return this.renderWorkflowTimelineList(events);
    }

    buildTimelineFromSessionMetadata() {
        const md = this._sessionMetadataPayload || {};
        const items = [];
        if (md.submitted_at || md.first_submitted_at) {
            items.push({
                type: 'clerk_submission',
                at_display: md.submitted_at || md.first_submitted_at,
                label: 'Clerk original submission',
                detail: md.submission_notes || '',
            });
        }
        const reason = this.getRejectionReasonDisplay();
        if (reason) {
            items.push({
                type: 'rejection',
                at_display: (md.rejected_at || md.manager_rejection?.at || ''),
                label: 'Manager rejection',
                detail: reason,
            });
        }
        const hist = md.resubmission_history;
        if (Array.isArray(hist)) {
            hist.forEach((entry) => {
                if (!entry || typeof entry !== 'object') return;
                items.push({
                    type: 'clerk_resubmission',
                    at_display: entry.at || '',
                    label: 'Clerk correction and resubmission',
                    detail: entry.clerk_correction_note || entry.note || '',
                    changes_summary: entry.changes_summary,
                });
            });
        }
        return items;
    }

    renderWorkflowTimelineList(events) {
        const rows = events
            .map((ev) => {
                const type = ev.type || 'event';
                const icon =
                    type === 'rejection' ? '❌' : type === 'clerk_resubmission' ? '🔄' : '📤';
                const detail = [ev.detail, ev.changes_summary].filter(Boolean).join(' — ');
                return `
                <li class="workflow-timeline__item workflow-timeline__item--${this.escapeHtml(type)}">
                    <div class="workflow-timeline__marker" aria-hidden="true">${icon}</div>
                    <div class="workflow-timeline__body">
                        <div class="workflow-timeline__meta">
                            <strong>${this.escapeHtml(ev.label || type)}</strong>
                            <time class="workflow-timeline__time">${this.escapeHtml(ev.at_display || ev.at || '—')}</time>
                        </div>
                        ${detail ? `<p class="workflow-timeline__detail">${this.escapeHtml(detail)}</p>` : ''}
                    </div>
                </li>`;
            })
            .join('');
        const ariaLabel = this.timelineHasResubmission(events)
            ? 'Resubmission history'
            : 'Submission history';
        return `<ol class="workflow-timeline" aria-label="${this.escapeHtml(ariaLabel)}">${rows}</ol>`;
    }

    escapeHtml(s) {
        if (!s) return '';
        const d = document.createElement('div');
        d.textContent = s;
        return d.innerHTML;
    }

    /** Short display for UUID session ids; full value in title/tooltip. */
    formatShortTransactionId(fullId) {
        const s = (fullId || '').toString().trim();
        if (!s) return { display: '—', full: '' };
        const uuidRe =
            /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
        if (uuidRe.test(s)) {
            return { display: `${s.slice(0, 8)}…`, full: s };
        }
        if (s.length > 28) {
            return { display: `${s.slice(0, 14)}…`, full: s };
        }
        return { display: s, full: s };
    }

    _hasPerformanceTotals(pt) {
        return pt && (Math.abs(Number(pt.revenue) || 0) > 0.001 || Math.abs(Number(pt.expenses) || 0) > 0.001);
    }

    _resolvePerformanceTotals(docType, sd, sessionData) {
        const dt = String(docType || '').toLowerCase();
        const G = this._grap();
        const data = sd || this.statementData || {};
        const raw = sessionData || this._rawSessionData || {};
        const md = raw.metadata || {};

        if (this._hasPerformanceTotals(data.perfTotals)) {
            return data.perfTotals;
        }

        const lineSources = [...(data.performanceLines || []), ...(data.lines || [])];
        if (lineSources.length && G && G.computePerformanceTotals) {
            const fromLines = G.computePerformanceTotals(lineSources);
            if (this._hasPerformanceTotals(fromLines)) {
                return fromLines;
            }
        }

        if (dt === 'income_statement') {
            const tr = Number(raw.total_revenue);
            const te = Number(raw.total_expenses);
            const tn = Number(raw.net_income);
            if (!Number.isNaN(tr) || !Number.isNaN(te)) {
                const revenue = Number.isNaN(tr) ? 0 : tr;
                const expenses = Number.isNaN(te) ? 0 : te;
                const net = Number.isNaN(tn) ? revenue - expenses : tn;
                if (this._hasPerformanceTotals({ revenue, expenses, net })) {
                    return { revenue, expenses, net };
                }
            }

            const rows = raw.income_rows || [];
            if (rows.length) {
                let revenue = 0;
                let expenses = 0;
                rows.forEach((r) => {
                    if (r.is_total_row || r.is_subtotal_row) return;
                    const cat = String(r.category || '').toLowerCase();
                    const ra = Number(r.revenue_amount);
                    const ea = Number(r.expense_amount);
                    const am = Number(r.amount);
                    const nb = Number(r.net_balance);
                    if (!Number.isNaN(ra) && Math.abs(ra) > 0.0001) {
                        revenue += ra;
                    } else if (!Number.isNaN(ea) && Math.abs(ea) > 0.0001) {
                        expenses += Math.abs(ea);
                    } else if (!Number.isNaN(am) && am > 0) {
                        revenue += am;
                    } else if (!Number.isNaN(am) && am < 0) {
                        expenses += Math.abs(am);
                    } else if (!Number.isNaN(nb) && nb > 0) {
                        revenue += nb;
                    } else if (!Number.isNaN(nb) && nb < 0) {
                        expenses += Math.abs(nb);
                    } else if (cat.includes('revenue') || cat.includes('income')) {
                        const val = !Number.isNaN(am) ? Math.abs(am) : Math.abs(nb || 0);
                        revenue += val;
                    } else if (cat.includes('expense')) {
                        const val = !Number.isNaN(am) ? Math.abs(am) : Math.abs(nb || 0);
                        expenses += val;
                    }
                });
                if (this._hasPerformanceTotals({ revenue, expenses, net: revenue - expenses })) {
                    return { revenue, expenses, net: revenue - expenses };
                }
            }
        }

        const mapped = this._mappedLinesFromMetadata(md);
        if (mapped.length && G && G.computePerformanceTotals) {
            const fromMapped = G.computePerformanceTotals(mapped);
            if (this._hasPerformanceTotals(fromMapped)) {
                return fromMapped;
            }
        }

        return data.perfTotals || { revenue: 0, expenses: 0, net: 0 };
    }

    renderReviewerRoleBanner() {
        const G = this._grap();
        const docT = this.currentTransaction?.transaction_type || this.statementData?.document_type || '';
        const role = window.currentUserRole || '';
        if (G && G.renderReviewerRoleBanner) {
            return G.renderReviewerRoleBanner(docT, role);
        }
        return '';
    }

    renderGrapComplianceSummary(docType) {
        const dt = String(docType || '').toLowerCase();
        const G = this._grap();
        const cfg = G && G.config ? G.config(dt) : { standard: 'GRAP compliance' };
        const md = (this._rawSessionData && this._rawSessionData.metadata) || {};
        const mapped = this._mappedLinesFromMetadata(md);
        let panel = '';

        if (dt === 'balance_sheet' && G && mapped.length) {
            const st = this.statementData.sfpTotals || G.computeSfpTotals(mapped);
            const ok = st.balanced;
            panel = `
                <section class="grap-equation-panel ${ok ? 'grap-equation-panel--balanced' : 'grap-equation-panel--unbalanced'}" aria-label="GRAP 1 accounting equation">
                    <h4 class="grap-equation-panel__title">${this.escapeHtml(cfg.standard)} — accounting equation</h4>
                    <p class="grap-equation-panel__intro text-muted">Same rules as clerk submit and CFO final approval. P&amp;L accounts (4xxx/5xxx) are excluded from this check.</p>
                    <div class="grap-equation-grid">
                        <div class="grap-equation-cell">
                            <span class="grap-equation-label">Assets</span>
                            <span class="grap-equation-value">R${this.formatNumber(st.assets)}</span>
                        </div>
                        <div class="grap-equation-cell">
                            <span class="grap-equation-label">Liabilities</span>
                            <span class="grap-equation-value">R${this.formatNumber(st.liabilities)}</span>
                        </div>
                        <div class="grap-equation-cell">
                            <span class="grap-equation-label">Equity</span>
                            <span class="grap-equation-value">R${this.formatNumber(st.equity)}</span>
                        </div>
                        <div class="grap-equation-cell grap-equation-cell--highlight">
                            <span class="grap-equation-label">Liabilities + Equity</span>
                            <span class="grap-equation-value">R${this.formatNumber(st.liabilities_plus_equity)}</span>
                        </div>
                        <div class="grap-equation-cell grap-equation-cell--diff ${ok ? '' : 'grap-equation-cell--warn'}">
                            <span class="grap-equation-label">Difference</span>
                            <span class="grap-equation-value">R${this.formatNumber(st.difference)}</span>
                        </div>
                    </div>
                    <p class="grap-equation-formula"><strong>Formula:</strong> Assets − (Liabilities + Equity) = Difference (target 0)</p>
                    <p class="grap-equation-status ${ok ? 'text-success' : 'text-danger'}">${ok ? '✓ Balanced for approval' : '⚠ Out of balance — CFO final approval will be blocked until mapping/amounts are corrected'}</p>
                </section>`;
            const pt = this.statementData.perfTotals || (G.computePerformanceTotals ? G.computePerformanceTotals(mapped) : null);
            const resolvedPt = this._resolvePerformanceTotals('balance_sheet', this.statementData, this._rawSessionData);
            const showPt = this._hasPerformanceTotals(resolvedPt) ? resolvedPt : pt;
            if (showPt && this._hasPerformanceTotals(showPt)) {
                panel += `
                <section class="grap-equation-panel grap-equation-panel--secondary" aria-label="Statement of financial performance summary">
                    <h4 class="grap-equation-panel__title">Statement of Financial Performance (from mapped trial balance)</h4>
                    <div class="grap-equation-grid grap-equation-grid--compact">
                        <div class="grap-equation-cell"><span class="grap-equation-label">Revenue</span><span class="grap-equation-value">R${this.formatNumber(showPt.revenue)}</span></div>
                        <div class="grap-equation-cell"><span class="grap-equation-label">Expenses</span><span class="grap-equation-value">R${this.formatNumber(showPt.expenses)}</span></div>
                        <div class="grap-equation-cell"><span class="grap-equation-label">Net</span><span class="grap-equation-value">R${this.formatNumber(showPt.net)}</span></div>
                    </div>
                    <p class="grap-equation-formula"><strong>Formula:</strong> Revenue − Expenses = Net surplus / (deficit)</p>
                </section>`;
            }
        } else if (dt === 'income_statement') {
            const pt = this._resolvePerformanceTotals(dt, this.statementData, this._rawSessionData);
            if (this._hasPerformanceTotals(pt)) {
                panel = `
                <section class="grap-equation-panel" aria-label="GRAP 1 performance summary">
                    <h4 class="grap-equation-panel__title">${this.escapeHtml(cfg.standard)}</h4>
                    <div class="grap-equation-grid">
                        <div class="grap-equation-cell"><span class="grap-equation-label">Revenue</span><span class="grap-equation-value">R${this.formatNumber(pt.revenue)}</span></div>
                        <div class="grap-equation-cell"><span class="grap-equation-label">Expenses</span><span class="grap-equation-value">R${this.formatNumber(pt.expenses)}</span></div>
                        <div class="grap-equation-cell grap-equation-cell--highlight"><span class="grap-equation-label">Net</span><span class="grap-equation-value">R${this.formatNumber(pt.net)}</span></div>
                    </div>
                    <p class="grap-equation-formula"><strong>Formula:</strong> Revenue − Expenses = Net</p>
                </section>`;
            }
        } else if (dt === 'budget_report') {
            const raw = this._rawSessionData || {};
            const tb = Number(raw.total_budget);
            const ta = Number(raw.total_actual);
            const tv = Number(raw.total_variance);
            const hasBudgetTotals = !Number.isNaN(tb) || !Number.isNaN(ta);
            panel = `
                <section class="grap-equation-panel" aria-label="GRAP 24 summary">
                    <h4 class="grap-equation-panel__title">${this.escapeHtml(cfg.standard)}</h4>
                    ${
                        hasBudgetTotals
                            ? `<div class="grap-equation-grid">
                        <div class="grap-equation-cell"><span class="grap-equation-label">Total budget</span><span class="grap-equation-value">R${this.formatNumber(tb)}</span></div>
                        <div class="grap-equation-cell"><span class="grap-equation-label">Total actual</span><span class="grap-equation-value">R${this.formatNumber(ta)}</span></div>
                        <div class="grap-equation-cell grap-equation-cell--highlight"><span class="grap-equation-label">Variance</span><span class="grap-equation-value">R${this.formatNumber(Number.isNaN(tv) ? ta - tb : tv)}</span></div>
                    </div>
                    <p class="grap-equation-formula"><strong>Formula:</strong> Actual − Budget = Variance</p>`
                            : '<p class="text-muted">Budget vs actual and mandatory variance explanations (&gt;10%) are validated on submit and CFO approval. See the budget table and variance panel below.</p>'
                    }
                </section>`;
        }
        return panel;
    }

    renderIncomeStatementTotalsFallback(sessionData, period) {
        const pt = this._resolvePerformanceTotals('income_statement', null, sessionData);
        if (this._hasPerformanceTotals(pt)) {
            return `
            <section class="grap-equation-panel" aria-label="Income statement totals">
                <h4 class="grap-equation-panel__title">Statement totals (session summary)</h4>
                <div class="grap-equation-grid">
                    <div class="grap-equation-cell"><span class="grap-equation-label">Revenue</span><span class="grap-equation-value">R${this.formatNumber(pt.revenue)}</span></div>
                    <div class="grap-equation-cell"><span class="grap-equation-label">Expenses</span><span class="grap-equation-value">R${this.formatNumber(pt.expenses)}</span></div>
                    <div class="grap-equation-cell grap-equation-cell--highlight"><span class="grap-equation-label">Net</span><span class="grap-equation-value">R${this.formatNumber(pt.net)}</span></div>
                </div>
                <p class="text-muted" style="margin-top:0.75rem;">Line-level detail was not returned for this session. Check the <strong>Account Mappings</strong> tab or ask the clerk to resubmit if rows are missing.</p>
            </section>`;
        }

        const rev = Number(sessionData && sessionData.total_revenue);
        const exp = Number(sessionData && sessionData.total_expenses);
        const net = Number(sessionData && sessionData.net_income);
        const hasTotals =
            (!Number.isNaN(rev) && Math.abs(rev) > 0) ||
            (!Number.isNaN(exp) && Math.abs(exp) > 0) ||
            (!Number.isNaN(net) && Math.abs(net) > 0);
        if (!hasTotals) return '';

        return `
            <section class="grap-equation-panel" aria-label="Income statement totals">
                <h4 class="grap-equation-panel__title">Statement totals (session summary)</h4>
                <div class="grap-equation-grid">
                    <div class="grap-equation-cell"><span class="grap-equation-label">Revenue</span><span class="grap-equation-value">R${this.formatNumber(rev)}</span></div>
                    <div class="grap-equation-cell"><span class="grap-equation-label">Expenses</span><span class="grap-equation-value">R${this.formatNumber(exp)}</span></div>
                    <div class="grap-equation-cell grap-equation-cell--highlight"><span class="grap-equation-label">Net</span><span class="grap-equation-value">R${this.formatNumber(net)}</span></div>
                </div>
                <p class="text-muted" style="margin-top:0.75rem;">Line-level detail was not returned for this session. Check the <strong>Account Mappings</strong> tab or ask the clerk to resubmit if rows are missing.</p>
            </section>`;
    }

    renderFinancialStatement() {
        if (!this.statementData) return '<p>No statement data available</p>';

        const pos = this.statementData.positionLines;
        const perf = this.statementData.performanceLines;
        const docT = this.currentTransaction?.transaction_type || this.statementData.document_type || '';
        const flatLines = this.statementData.lines || [];
        const compliancePanel = this.renderGrapComplianceSummary(docT);

        if (docT === 'budget_report' && !(pos && pos.length) && !(perf && perf.length) && !flatLines.length) {
            const period = this.escapeHtml(this.statementData.period || 'FY 2025-2026');
            return `
                <div class="financial-statement-review">
                    <div class="statement-period">Period: ${period}</div>
                    <div class="approval-empty-state" style="margin-top:1rem;">
                        <p><strong>No budget line items in the API response.</strong></p>
                        <p>The review screen reads <code>budget_rows</code> from <code>/api/universal/session</code> (Supabase table <code>budget_report_data_rows</code>). If your Excel had data but this is empty, rows were not persisted for this session.</p>
                    </div>
                </div>`;
        }

        if (docT === 'income_statement' && !(pos && pos.length) && !(perf && perf.length) && !flatLines.length) {
            const period = this.escapeHtml(this.statementData.period || 'FY 2025-2026');
            const raw = this._rawSessionData || {};
            const totalsPanel = this.renderIncomeStatementTotalsFallback(raw, period);
            const rowHint =
                raw.income_line_count != null
                    ? `Uploaded rows recorded: ${raw.income_line_count}.`
                    : '';
            return `
                <div class="financial-statement-review">
                    <div class="statement-header">
                        <h3>${this.escapeHtml(this.getStatementTitle('income_statement'))}</h3>
                        <div class="statement-period">Period: ${period}</div>
                    </div>
                    ${compliancePanel}
                    ${totalsPanel}
                    <div class="approval-empty-state" style="margin-top:1rem;">
                        <p><strong>No income statement line items to display.</strong></p>
                        <p>${rowHint} Expected source: mapped accounts or <code>income_rows</code> from the session API.</p>
                    </div>
                </div>`;
        }

        if (docT === 'balance_sheet' && (pos && pos.length || perf && perf.length)) {
            const period = this.statementData.period || 'FY 2025-2026';
            const posTable = this.renderStatementTable('Statement of Financial Position', pos || [], {
                mode: 'sfp',
                sfpTotals: this.statementData.sfpTotals
            });
            const perfPt = this._resolvePerformanceTotals('income_statement', this.statementData, this._rawSessionData);
            const perfTable = perf && perf.length
                ? this.renderStatementTable('Statement of Financial Performance', perf, {
                    mode: 'sfper',
                    perfTotals: this._hasPerformanceTotals(perfPt) ? perfPt : this.statementData.perfTotals,
                })
                : '';
            return `
                <div class="financial-statement-review">
                    <div class="statement-period">Period: ${this.escapeHtml(period)}</div>
                    ${compliancePanel}
                    ${posTable}
                    ${perfTable}
                </div>
            `;
        }

        if (docT === 'income_statement' && (perf && perf.length || flatLines.length)) {
            const period = this.statementData.period || 'FY 2025-2026';
            const tableLines = perf && perf.length ? perf : flatLines;
            const pt = this._resolvePerformanceTotals(docT, this.statementData, this._rawSessionData);
            const perfTable = this.renderStatementTable('Statement of Financial Performance', tableLines, {
                mode: 'sfper',
                perfTotals: this._hasPerformanceTotals(pt) ? pt : this.statementData.perfTotals,
            });
            return `
                <div class="financial-statement-review">
                    <div class="statement-header">
                        <h3>${this.escapeHtml(this.getStatementTitle('income_statement'))}</h3>
                        <div class="statement-period">Period: ${this.escapeHtml(period)}</div>
                    </div>
                    ${compliancePanel}
                    ${perfTable}
                </div>
            `;
        }

        if (docT === 'budget_report') {
            const period = this.escapeHtml(this.statementData.period || 'FY 2025-2026');
            const budgetRows = (this._rawSessionData && this._rawSessionData.budget_rows) || [];
            if (!budgetRows.length) {
                return `
                <div class="financial-statement-review">
                    ${compliancePanel}
                    <p class="text-muted">No budget line items loaded for this session.</p>
                </div>`;
            }
            const explanations = (this._rawSessionData && this._rawSessionData.variance_explanations) || {};
            const readOnly = this.isStatementReviewReadOnly();
            let variancePanel = '';
            let budgetComparison = '';
            if (window.BudgetVarianceGrap24 && budgetRows.length) {
                budgetComparison = BudgetVarianceGrap24.renderComparisonTable(budgetRows, { period });
                variancePanel = BudgetVarianceGrap24.renderVariancePanel(budgetRows, explanations, { readOnly });
            }
            return `
                <div class="financial-statement-review">
                    ${compliancePanel}
                    ${budgetComparison}
                    ${variancePanel}
                </div>`;
        }

        const docOnly = docT === 'income_statement' ? 'sfper' : 'generic';
        return `
            <div class="financial-statement-review">
                ${compliancePanel}
                <div class="statement-header">
                    <h3>${this.escapeHtml(this.getStatementTitle(docT))}</h3>
                    <div class="statement-period">
                        Period: ${this.statementData.period || 'FY 2025-2026'}
                    </div>
                </div>
                ${this.renderStatementTable(
                    docT === 'income_statement' ? 'Statement of Financial Performance' : '',
                    this.statementData.lines || [],
                    {
                        mode: docOnly,
                        perfTotals: this._resolvePerformanceTotals(
                            docT,
                            this.statementData,
                            this._rawSessionData
                        ),
                    }
                )}
            </div>
        `;
    }

    renderStatementTable(title, lines, tableOpts) {
        const opts = tableOpts && typeof tableOpts === 'object' ? tableOpts : { mode: 'generic' };
        const titleHtml = title ? `<h3 class="statement-subheading">${this.escapeHtml(title)}</h3>` : '';
        const docT = this.currentTransaction?.transaction_type || this.statementData?.document_type || '';
        const foot = this.renderStatementTableFooter(opts, lines);
        const intro =
            opts.mode === 'sfp'
                ? '<p class="statement-table-intro text-muted">Balance sheet accounts only (1xxx / 2xxx / 3xxx). Click any line to open TB→GRAP calculation breakdown.</p>'
                : opts.mode === 'sfper'
                  ? '<p class="statement-table-intro text-muted">Revenue and expense accounts (4xxx / 5xxx and RV/EX mappings). Click any line to open TB→GRAP calculation breakdown.</p>'
                  : '<p class="statement-table-intro text-muted">Click any line item to open the Formula Transparency modal (TB→GRAP mapping).</p>';
        return `
            ${titleHtml}
            ${intro}
            <div class="statement-table-container">
                <table class="financial-statement-table review-table">
                    <thead>
                        <tr>
                            <th>Account Code</th>
                            <th>Account Description</th>
                            <th>GRAP / Note</th>
                            <th class="amount-column">Amount (R)</th>
                            <th class="actions-column">Calculation</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${this.renderStatementLines(lines, docT)}
                    </tbody>
                    <tfoot>
                        ${foot}
                    </tfoot>
                </table>
            </div>
        `;
    }

    renderStatementTableFooter(opts, lines) {
        if (opts.mode === 'sfp') {
            const st = opts.sfpTotals || this.statementData?.sfpTotals;
            if (st) {
                return `
                        <tr class="subtotal-row"><td colspan="3"><strong>Total assets</strong></td><td class="amount-column"><strong>R${this.formatNumber(st.assets)}</strong></td><td class="formula-hint">Σ assets</td></tr>
                        <tr class="subtotal-row"><td colspan="3"><strong>Total liabilities</strong></td><td class="amount-column"><strong>R${this.formatNumber(st.liabilities)}</strong></td><td class="formula-hint">Σ liabilities</td></tr>
                        <tr class="subtotal-row"><td colspan="3"><strong>Total equity</strong></td><td class="amount-column"><strong>R${this.formatNumber(st.equity)}</strong></td><td class="formula-hint">Σ equity</td></tr>
                        <tr class="total-row ${st.balanced ? '' : 'total-row--warn'}"><td colspan="3"><strong>Difference (A − (L + E))</strong></td><td class="amount-column"><strong>R${this.formatNumber(st.difference)}</strong></td><td class="formula-hint">${st.balanced ? '✓' : '⚠'}</td></tr>`;
            }
        }
        if (opts.mode === 'sfper') {
            const pt = opts.perfTotals || this.statementData?.perfTotals;
            if (pt) {
                return `
                        <tr class="subtotal-row"><td colspan="3"><strong>Total revenue</strong></td><td class="amount-column"><strong>R${this.formatNumber(pt.revenue)}</strong></td><td></td></tr>
                        <tr class="subtotal-row"><td colspan="3"><strong>Total expenses</strong></td><td class="amount-column"><strong>R${this.formatNumber(pt.expenses)}</strong></td><td></td></tr>
                        <tr class="total-row"><td colspan="3"><strong>Net surplus / (deficit)</strong></td><td class="amount-column"><strong>R${this.formatNumber(pt.net)}</strong></td><td class="formula-hint">Rev − Exp</td></tr>`;
            }
        }
        const total = (lines || []).reduce((s, l) => s + (parseFloat(l.amount) || 0), 0);
        return `
                        <tr class="total-row">
                            <td colspan="3"><strong>Σ line amounts</strong> <span class="text-muted">(informational)</span></td>
                            <td class="amount-column"><strong>R${this.formatNumber(total)}</strong></td>
                            <td></td>
                        </tr>`;
    }

    renderStatementLines(lines, documentType) {
        const G = this._grap();
        const docT = documentType || this.currentTransaction?.transaction_type || this.statementData?.document_type || '';
        const canAddComment = this.canAddLineItemCommentInReview();
        const canViewComment = this.shouldOpenLineItemCommentReadOnly();
        const breakdownTitle =
            docT === 'income_statement'
                ? 'Click to view income statement → GRAP calculation breakdown'
                : docT === 'budget_report'
                  ? 'Click to view budget line → GRAP calculation breakdown'
                  : 'Click to view trial balance → GRAP calculation breakdown';
        return lines.map(line => {
            const formulaHint = G && G.lineAmountFormulaHint
                ? G.lineAmountFormulaHint(line, documentType)
                : 'Mapped amount';
            const grapNote = [line.grap_code, line.note].filter(Boolean).join(' · ') || '-';
            const accountCode = String(line.account_code || '');
            const description = String(line.description || '');
            const commentCount = this.accountLineItemCommentCount(accountCode);
            const flaggedClass = commentCount > 0 ? ' statement-line--has-comments' : '';
            let commentBtn = '';
            if (canAddComment) {
                commentBtn = `<button type="button" class="btn btn-xs btn-outline-secondary line-item-comment-btn"
                        data-action="line-item-comment"
                        data-account-code="${this.escapeHtml(accountCode)}"
                        data-description="${this.escapeHtml(description)}"
                        data-amount="${this.escapeHtml(String(line.amount || 0))}"
                        data-grap-code="${this.escapeHtml(String(line.grap_code || ''))}"
                        title="Add comment or reject with correction"
                        aria-label="Comment on line ${this.escapeHtml(accountCode || description)}">💬</button>`;
            } else if (canViewComment && (commentCount > 0 || this.isStatementReviewReadOnly() || this.isSettledSessionForCommentArchive())) {
                commentBtn = `<button type="button" class="btn btn-xs btn-outline-secondary line-item-comment-btn line-item-comment-btn--view"
                        data-action="line-item-comment-view"
                        data-account-code="${this.escapeHtml(accountCode)}"
                        data-description="${this.escapeHtml(description)}"
                        data-amount="${this.escapeHtml(String(line.amount || 0))}"
                        data-grap-code="${this.escapeHtml(String(line.grap_code || ''))}"
                        title="View reviewer comments for this line"
                        aria-label="View comments on line ${this.escapeHtml(accountCode || description)}">${commentCount > 0 ? `💬 ${commentCount}` : '💬'}</button>`;
            }
            return `
            <tr class="statement-line statement-line--clickable${flaggedClass}" role="button" tabindex="0"
                data-account-code="${this.escapeHtml(accountCode)}"
                data-grap-code="${this.escapeHtml(String(line.grap_code || ''))}"
                data-description="${this.escapeHtml(description)}"
                data-amount="${this.escapeHtml(String(line.amount || 0))}"
                title="${this.escapeHtml(breakdownTitle)}">
                <td class="account-code">${this.escapeHtml(accountCode)}</td>
                <td class="account-description">${this.escapeHtml(description)}</td>
                <td class="note-column">${this.escapeHtml(grapNote)}</td>
                <td class="amount-column">R${this.formatNumber(line.amount || 0)}</td>
                <td class="actions-column formula-hint" title="${this.escapeHtml(formulaHint)}">
                    <span class="formula-hint-text">${this.escapeHtml(formulaHint)}</span>
                    <button type="button" class="btn btn-xs btn-secondary" data-action="view-calculation" data-account="${this.escapeHtml(accountCode)}" data-grap="${this.escapeHtml(String(line.grap_code || ''))}">
                        Detail
                    </button>
                    ${commentBtn}
                </td>
            </tr>`;
        }).join('');
    }

    openLineItemCommentForRow(rowEl, readOnly = false) {
        if (!rowEl || !window.openLineItemComment) {
            this.showError('Line item comments are not available.');
            return;
        }
        const accountCode = rowEl.dataset.accountCode || '';
        const sessionId = this._sessionId || this.currentTransaction?.transaction_id;
        const docT = this.currentTransaction?.transaction_type || this._documentType || 'balance_sheet';
        if (!sessionId) {
            this.showError('Cannot open comment (missing session).');
            return;
        }
        const viewOnly = readOnly || this.shouldOpenLineItemCommentReadOnly();
        window.openLineItemComment(
            accountCode,
            {
                description: rowEl.dataset.description || '',
                amount: rowEl.dataset.amount || 0,
                grap_code: rowEl.dataset.grapCode || '',
            },
            sessionId,
            docT,
            { readOnly: viewOnly }
        );
    }

    renderAccountMappings() {
        if (!this.statementData) return '<p>No mapping data available</p>';

        const mappings = this.statementData.mappings || [];
        const viewOnly = this.isApproverOnlyReview();
        const docT = this.currentTransaction?.transaction_type || this.statementData.document_type || '';
        const accountCol =
            docT === 'budget_report'
                ? 'Budget line'
                : docT === 'income_statement'
                  ? 'Income statement account'
                  : 'Trial balance account';
        
        return `
            <div class="account-mappings-review">
                <p class="section-intro text-muted">GRAP mapping used for ${this.escapeHtml(this.getStatementTitle(docT))} validation and statement layout.</p>
                <div class="mappings-summary">
                    <div class="mapping-stats">
                        <div class="stat-item">
                            <span class="stat-value">${mappings.length}</span>
                            <span class="stat-label">Total Accounts</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-value">${mappings.filter(m => m.mapped).length}</span>
                            <span class="stat-label">Mapped</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-value">${mappings.filter(m => !m.mapped).length}</span>
                            <span class="stat-label">Unmapped</span>
                        </div>
                    </div>
                </div>
                
                <div class="mappings-table-container">
                    <table class="mappings-table">
                        <thead>
                            <tr>
                                <th>${this.escapeHtml(accountCol)}</th>
                                <th>GRAP Category</th>
                                <th>Mapping Status</th>
                                <th>Confidence</th>
                                ${viewOnly ? '' : '<th>Actions</th>'}
                            </tr>
                        </thead>
                        <tbody>
                            ${mappings.map(mapping => `
                                <tr class="mapping-row ${mapping.mapped ? 'mapped' : 'unmapped'}">
                                    <td>
                                        <div class="account-info">
                                            <span class="account-code">${mapping.tb_account_code}</span>
                                            <span class="account-desc">${mapping.tb_account_description}</span>
                                        </div>
                                    </td>
                                    <td>
                                        <div class="grap-info">
                                            <span class="grap-code">${mapping.grap_code}</span>
                                            <span class="grap-desc">${mapping.grap_description}</span>
                                        </div>
                                    </td>
                                    <td>
                                        <span class="mapping-status ${mapping.mapped ? 'status-mapped' : 'status-unmapped'}">
                                            ${mapping.mapped ? '✓ Mapped' : '⚠️ Unmapped'}
                                        </span>
                                    </td>
                                    <td>
                                        <div class="confidence-indicator">
                                            <div class="confidence-bar confidence-bar-dynamic" style="--confidence-width: ${mapping.confidence || 0}%"></div>
                                            <span class="confidence-text">${Math.round(mapping.confidence || 0)}%</span>
                                        </div>
                                    </td>
                                    ${viewOnly ? '' : `<td><div class="mapping-actions">
                                            <button class="btn btn-xs btn-secondary" data-action="edit-mapping" data-account="${mapping.tb_account_code}">
                                                ✏️ Edit
                                            </button>
                                            ${!mapping.mapped ? `
                                                <button class="btn btn-xs btn-primary" data-action="map-account" data-account="${mapping.tb_account_code}">
                                                    📍 Map
                                                </button>
                                            ` : ''}
                                        </div></td>`}
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            </div>
        `;
    }

    renderCalculationsSummary() {
        if (!this.statementData) return '<p>No calculation data available</p>';

        const viewOnly = this.isApproverOnlyReview();
        const calculations = this.statementData.calculations || [];
        if (!calculations.length) {
            return `
            <div class="calculations-review">
                <div class="approval-empty-state">
                    <div class="approval-empty-icon">📐</div>
                    <h3>No calculations yet</h3>
                    <p>This session did not return enough structured data to derive totals (for example <code>financial_statements</code>, line payloads, or mapping metadata). Check processing status in Supabase or open the <strong>Financial statements</strong> tab for raw lines.</p>
                </div>
            </div>`;
        }

        const resultCell = (calc) => {
            if (typeof calc.result === 'number' && !Number.isNaN(calc.result)) {
                return `R${this.formatNumber(calc.result)}`;
            }
            return this.escapeHtml(String(calc.result ?? '—'));
        };

        const docT = this.currentTransaction?.transaction_type || this.statementData.document_type || '';
        const compliancePanel = this.renderGrapComplianceSummary(docT);

        return `
            <div class="calculations-review">
                ${compliancePanel}
                <div class="calculations-summary">
                    <h4>Calculation Summary</h4>
                    <p class="section-intro text-muted">Values match clerk submit and CFO approval checks (mapped_data + GRAP rules). Legacy “sum of all lines” rows are informational only.</p>
                    <div class="calc-stats">
                        <div class="stat-item">
                            <span class="stat-value">${calculations.length}</span>
                            <span class="stat-label">Calculations</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-value">${calculations.filter(c => c.verified).length}</span>
                            <span class="stat-label">Verified</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-value">${calculations.filter(c => !c.verified).length}</span>
                            <span class="stat-label">Need Review</span>
                        </div>
                    </div>
                </div>
                
                <div class="calculations-list">
                    ${calculations.map(calc => `
                        <div class="calculation-item ${calc.verified ? 'verified' : 'needs-review'}">
                            <div class="calc-header">
                                <h5>${this.escapeHtml(calc.description || '')}</h5>
                                <span class="calc-status ${calc.verified ? 'status-verified' : 'status-needs-review'}">
                                    ${calc.verified ? '✓ Verified' : '⚠️ Needs Review'}
                                </span>
                            </div>
                            <div class="calc-formula">
                                <strong>Source / formula:</strong> <code>${this.escapeHtml(String(calc.formula || ''))}</code>
                            </div>
                            <div class="calc-result">
                                <strong>Result:</strong> ${resultCell(calc)}
                            </div>
                            <div class="calc-actions">
                                <button type="button" class="btn btn-xs btn-primary" data-action="view-calculation-detail" data-calc-id="${calc.id || ''}">
                                    🔍 View Details
                                </button>
                                ${
                                    !viewOnly && !calc.verified
                                        ? `
                                    <button type="button" class="btn btn-xs btn-success" data-action="verify-calculation" data-calc-id="${calc.id || ''}">
                                        ✓ Verify
                                    </button>`
                                        : ''
                                }
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }

    attachReviewListeners() {
        const root = document.getElementById('statementReviewContent');
        if (!root) return;

        if (!this._reviewRootClickBound) {
            this._reviewRootClickBound = true;
            root.addEventListener('click', (e) => {
                const detailBtn = e.target.closest('[data-action="view-calculation-detail"]');
                if (detailBtn) {
                    e.preventDefault();
                    const cid = detailBtn.getAttribute('data-calc-id');
                    if (cid) {
                        this.openCalculationDetailFromServer(cid);
                    }
                    return;
                }
                const verifyBtn = e.target.closest('[data-action="verify-calculation"]');
                if (verifyBtn) {
                    e.preventDefault();
                    const cid = verifyBtn.getAttribute('data-calc-id');
                    if (cid) {
                        this.verifyCalculationOnServer(cid);
                    }
                }
            });
        }

        root.querySelector('[data-action="view-calculations"]')?.addEventListener('click', () => {
            this.openFormulaModal();
        });

        root.querySelector('[data-action="download-manager-certificate"]')?.addEventListener('click', () => {
            this.generateManagersCertificate();
        });

        root.querySelector('[data-action="approve-forward"]')?.addEventListener('click', (e) => {
            this.approveCurrentSubmission(e.currentTarget);
        });

        root.querySelectorAll('[data-action="reject-statement"]').forEach((btn) => {
            btn.addEventListener('click', () => this.rejectSubmissionWithMandatoryReason(btn));
        });

        root.querySelector('[data-action="approve-with-notes"]')?.addEventListener('click', (e) => {
            this.approveCurrentSubmission(e.currentTarget);
        });

        root.querySelectorAll('.statement-line--clickable').forEach((row) => {
            const openLine = (e) => {
                if (e.target.closest('button, a, input, textarea, select')) return;
                const accountCode = row.dataset.accountCode;
                const grapCode = row.dataset.grapCode;
                this.viewLineItemCalculation(accountCode, grapCode);
            };
            row.addEventListener('click', openLine);
            row.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    openLine(e);
                }
            });
        });

        // Line item actions
        root.querySelectorAll('[data-action="view-calculation"]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const el = e.currentTarget;
                const accountCode = el.dataset.account;
                const grapCode = el.dataset.grap;
                this.viewLineItemCalculation(accountCode, grapCode);
            });
        });

        root.querySelectorAll('[data-action="line-item-comment"]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                const row = e.currentTarget.closest('.statement-line');
                if (row) {
                    this.openLineItemCommentForRow(row, false);
                }
            });
        });
        root.querySelectorAll('[data-action="line-item-comment-view"]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                const row = e.currentTarget.closest('.statement-line');
                if (row) {
                    this.openLineItemCommentForRow(row, true);
                }
            });
        });
        root.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const el = e.currentTarget;
                this.switchTab(el.dataset.tab);
            });
        });
    }

    initializeTabs() {
        // Tab functionality is handled by switchTab method
    }

    switchTab(tabName) {
        const root = document.getElementById('statementReviewContent');
        if (!root) return;
        root.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tab === tabName);
        });

        root.querySelectorAll('.tab-pane').forEach(pane => {
            pane.classList.toggle('active', pane.id === `${tabName}-tab`);
        });
    }

    openFormulaModal() {
        const sessionId = this._sessionId || (this.currentTransaction && this.currentTransaction.transaction_id);
        if (window.formulaModal && sessionId) {
            window.formulaModal.loadFormulaData(sessionId);
            window.formulaModal.showModal();
        } else {
            this.showError('Formula modal not available');
        }
    }

    viewLineItemCalculation(accountCode, grapCode) {
        if (window.formulaModal) {
            window.formulaModal.loadLineItemFormula(accountCode, grapCode);
            window.formulaModal.showModal();
        } else {
            this.showError('Formula modal not available');
        }
    }

    async openCalculationDetailFromServer(calcId) {
        const sessionId = this._sessionId || (this.currentTransaction && this.currentTransaction.transaction_id);
        const docType = this._documentType || (this.currentTransaction && this.currentTransaction.transaction_type);
        const c = window.formulaModalController;
        if (!c || !sessionId || !docType) {
            this.showError('Cannot load calculation detail (missing session or document type).');
            return;
        }
        try {
            await c.loadUniversalSessionBreakdown(sessionId, docType, { scope: 'calculation', calcId });
        } catch (err) {
            console.error('[Review] formula-breakdown failed:', err);
            this.showError('Failed to load calculation breakdown from server.');
        }
    }

    async verifyCalculationOnServer(calcId) {
        const sessionId = this._sessionId || (this.currentTransaction && this.currentTransaction.transaction_id);
        const docType = this._documentType || (this.currentTransaction && this.currentTransaction.transaction_type);
        if (!sessionId || !docType) {
            this.showError('Cannot verify (missing session or document type).');
            return;
        }
        try {
            const res = await fetch(`/api/universal/session/${encodeURIComponent(sessionId)}/calculation-verify`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ document_type: docType, calc_id: calcId, verified: true })
            });
            const j = await res.json();
            if (!res.ok || !j.success) {
                this.showError(j.error || 'Verification failed');
                return;
            }
            await this.loadStatementForReview(sessionId, docType);
            this.showSuccess('Calculation marked verified.');
        } catch (err) {
            console.error('[Review] calculation-verify failed:', err);
            this.showError('Failed to save verification.');
        }
    }

    populateReviewCommentDraftFromSession() {
        const ta = document.getElementById('reviewComment');
        if (!ta) return;
        const md = this._sessionMetadataPayload || {};
        ta.value = md.review_panel_draft_notes != null ? String(md.review_panel_draft_notes) : '';
    }

    showMandatoryRejectionPrompt() {
        return varydianMandatoryRejectionReason();
    }

    async approveCurrentSubmission(triggerBtn) {
        const role = window.currentUserRole || '';
        if (role === 'FINANCE_CLERK') {
            this.showError('Finance Clerks cannot approve or finalize submissions.');
            return;
        }
        if (role === 'CFO' && !this.isCfoFinalizeAllowed()) {
            this.showError('Cannot finalize until the Finance Manager has approved this submission.');
            return;
        }
        if (role === 'CFO' && !(await this.ensureGrap24CompleteBeforeFinalize())) {
            return;
        }

        if (role === 'CFO') {
            const confirmed = window.varydianCfoFinalizeConfirm
                ? await window.varydianCfoFinalizeConfirm({ count: 1 })
                : await window.varydianAppConfirm(
                    'Finalize period',
                    'This action will lock all records for this submission\'s reporting period and is irreversible without an audit log entry. An audit trail record will be created. Continue?',
                    { confirmText: 'Finalize and lock', cancelText: 'Cancel' }
                );
            if (!confirmed) {
                return;
            }
        }

        const commentEl = document.getElementById('reviewComment');
        const notesFromTextarea = commentEl ? commentEl.value.trim() : '';

        VarydianUtils.setButtonBusy(triggerBtn, true, 'Approving…');
        try {
            const response = await fetch('/api/universal/approve', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    document_type: this.currentTransaction.transaction_type,
                    session_id: this.currentTransaction.transaction_id,
                    notes: notesFromTextarea || '',
                }),
            });

            const result = await response.json();

            if (result.success) {
                const newStatus = result.new_status;
                const role = window.currentUserRole || '';

                const scheduleRedirect = () => {
                    if (this.completeReviewWorkflowAndReturn()) {
                        return;
                    }
                    window.setTimeout(() => {
                        window.location.href = this.getReviewRedirectUrl();
                    }, 2000);
                };

                if (role === 'FINANCE_MANAGER' && (newStatus === 'approved_by_manager' || newStatus === 'pending_cfo')) {
                    this.showSuccess(result.message || 'Approved by manager — forwarded to CFO.');
                    window.setTimeout(async () => {
                        const downloadNow = await window.varydianAppConfirm(
                            "Manager's certificate",
                            "Download the manager's certificate (PDF) now? You can generate it later from the review tools after the session is forwarded.",
                            { confirmText: 'Download PDF', cancelText: 'Skip for now' }
                        );
                        if (downloadNow) {
                            await this.generateManagersCertificate();
                        }
                        scheduleRedirect();
                    }, 500);
                } else if (role === 'CFO' && newStatus === 'approved') {
                    const lockNote = result.period_locked || result.period_name
                        ? ` Reporting period${result.period_name ? ` (${result.period_name})` : ''} is now locked.`
                        : ' Reporting period is now locked.';
                    this.showSuccess(
                        (result.message || 'Submission final-approved.') +
                        lockNote +
                        ' Generate PDFs from Export Center.'
                    );
                    scheduleRedirect();
                } else {
                    this.showSuccess(result.message || 'Approval recorded.');
                    scheduleRedirect();
                }
            } else {
                const errMsg = result.error || 'Unknown error';
                if (result.code === 'period_id_unresolved') {
                    this.showError(
                        errMsg + ' The clerk may need to re-upload with a financial period selected.'
                    );
                } else if (result.code === 'period_lock_db_sync_failed') {
                    this.showError(
                        errMsg + ' No changes were saved — resolve the database configuration and try Finalize again.'
                    );
                } else {
                    this.showError('Approval failed: ' + errMsg);
                }
            }
        } catch (error) {
            this.showError('Failed to approve transaction: ' + error.message);
        } finally {
            VarydianUtils.clearButtonBusy(triggerBtn);
        }
    }

    async rejectSubmissionWithMandatoryReason(triggerBtn) {
        const role = window.currentUserRole || '';
        if (role === 'FINANCE_CLERK') {
            this.showError('Finance Clerks cannot reject submissions.');
            return;
        }
        const reason = await varydianMandatoryRejectionReason();
        if (!reason) {
            return;
        }

        VarydianUtils.setButtonBusy(triggerBtn, true, 'Rejecting…');
        try {
            const response = await fetch('/api/universal/reject', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    document_type: this.currentTransaction.transaction_type,
                    session_id: this.currentTransaction.transaction_id,
                    reason,
                }),
            });

            const result = await response.json();

            if (result.success) {
                const msg = result.new_status === 'rejected_by_manager'
                    ? 'Rejected by manager — returned to the clerk for correction.'
                    : 'Submission rejected.';
                this.showSuccess(msg);
                if (!this.completeReviewWorkflowAndReturn()) {
                    setTimeout(() => {
                        window.location.href = this.getReviewRedirectUrl();
                    }, 2000);
                }
            } else {
                this.showError('Rejection failed: ' + (result.error || 'Unknown error'));
            }
        } catch (error) {
            this.showError('Failed to reject transaction: ' + error.message);
        } finally {
            VarydianUtils.clearButtonBusy(triggerBtn);
        }
    }

    async generateManagersCertificate() {
        try {
            const response = await fetch(`/api/certificate/generate/${encodeURIComponent(this.currentTransaction.transaction_id)}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    document_type: this._documentType || this.currentTransaction.transaction_type
                })
            });

            const result = await response.json();

            if (result.success && result.certificate_url) {
                const dl = await fetch(result.certificate_url, { credentials: 'same-origin' });
                if (!dl.ok) {
                    let errMsg = `Download failed (${dl.status})`;
                    try {
                        const errBody = await dl.json();
                        if (errBody?.error) errMsg = errBody.error;
                    } catch (_e) { /* not JSON */ }
                    this.showError(errMsg);
                    return;
                }
                const blob = await dl.blob();
                const objectUrl = URL.createObjectURL(blob);
                const link = document.createElement('a');
                link.href = objectUrl;
                link.download = result.certificate_filename || 'Managers_Certificate.pdf';
                document.body.appendChild(link);
                link.click();
                link.remove();
                URL.revokeObjectURL(objectUrl);
            } else if (!result.success) {
                this.showError(result.error || 'Could not generate Manager\'s certificate');
            }
        } catch (error) {
            console.error('Certificate generation failed:', error);
            this.showError('Certificate generation failed: ' + (error.message || 'unknown error'));
        }
    }

    // Helper methods
    getTransactionTypeLabel(type) {
        const labels = {
            'financial_statement': 'Financial Statement',
            'balance_sheet': 'Balance Sheet',
            'income_statement': 'Income Statement',
            'budget_report': 'Budget Report',
            'journal_entry': 'Journal Entry',
            'asset_impairment': 'Asset Impairment',
            'budget_adjustment': 'Budget Adjustment'
        };
        return labels[type] || type.replace('_', ' ').toUpperCase();
    }

    getStatementTitle(type) {
        const titles = {
            financial_position: 'Statement of Financial Position',
            financial_performance: 'Statement of Financial Performance',
            cash_flows: 'Statement of Cash Flows',
            balance_sheet: 'Statement of Financial Position (GRAP 1 SFP)',
            income_statement: 'Statement of Financial Performance (GRAP 1)',
            budget_report: 'Budget vs Actual (GRAP 24)',
        };
        return titles[type] || 'Financial Statement';
    }

    formatNumber(num) {
        return parseFloat(num || 0).toLocaleString('en-ZA', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
    }

    formatDate(dateString) {
        return VarydianUtils.formatDate(dateString);
    }

    showSuccess(message) {
        this.showNotification(message, 'success');
    }

    showError(message) {
        this.showNotification(message, 'error');
    }

    showNotification(message, type) {
        if (window.VarydianUtils && typeof VarydianUtils.showToast === 'function') {
            VarydianUtils.showToast(message, type);
            return;
        }
        const notification = document.createElement('div');
        notification.className = `notification notification--${type}`;
        notification.innerHTML = `
            <div class="notification-content">
                <span class="notification-message">${message}</span>
                <button class="notification-close" onclick="this.parentElement.parentElement.remove()">✕</button>
            </div>
        `;

        document.body.appendChild(notification);
        setTimeout(() => {
            if (notification.parentElement) {
                notification.remove();
            }
        }, 8000);
    }
}

// Initialize Financial Statement Review (also when script loads after DOMContentLoaded)
function initFinancialStatementReview() {
    if (!window.financialStatementReview) {
        window.financialStatementReview = new FinancialStatementReview();
    }
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initFinancialStatementReview);
} else {
    initFinancialStatementReview();
}

// Export for use in other scripts
window.FinancialStatementReview = FinancialStatementReview;
