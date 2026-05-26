const CLERK_LOCKED_STATUSES = new Set([
    'pending',
    'pending_review',
    'submitted',
    'approved',
    'pending_cfo',
    'approved_by_manager',
]);

const CLERK_CORRECTION_STATUSES = new Set([
    'rejected',
    'rejected_by_manager',
    'rejected_by_cfo',
]);

const CLERK_FORWARD_SUCCESS_MESSAGE = 'Data forwarded to Finance Manager for review.';

// GRAP Mapping Interface
class GRAPMappingInterface {
    constructor(sessionId) {
        this.state = {
            sessionId: sessionId,
            unmappedAccounts: [],
            mappedAccounts: {},
            autoMappedAccounts: [],
            grapCategories: [],
            isDragging: false,
            draggedAccount: null,
            isReviewMode: false,
            mappingData: null,
            currentStatus: null,
            touchStartX: 0,
            touchStartY: 0,
            draggedElement: null,
            dragGhost: null,
            touchFeedback: null,
            isRevisionMode: false,
            revisionRequestedFromUrl: false,
            correctionNote: '',
            balanceCheck: { balanced: null, message: 'Checking balance…' },
            trialBalanceCheck: { balanced: null, message: 'Checking trial balance…' },
            _balanceDebounce: null,
            _trialBalanceDebounce: null,
        };
        
        this.elements = {};
        this.init();
    }

    init() {
        this.cacheElements();
        this.createDragGhost();
        this.setupEventListeners();
        this.checkReviewMode();
        this.detectRevisionModeFromUrl();
        void this.bootstrapMappingPage();
    }

    async bootstrapMappingPage() {
        await this.loadGRAPCategories();
        if (this.state.isReviewMode && this.state.mappingData) {
            this.loadReviewData();
        } else {
            await this.loadUnmappedAccounts();
        }
        await this.bootstrapWorkspace();
    }

    async bootstrapWorkspace() {
        this.hideRevisionWorkspaceChrome();
        await this.applySessionLockFromServer();
        if (this.state.isRevisionMode) {
            await this.maybeEnterRevisionMode();
            return;
        }
        this.hideRevisionWorkspaceChrome();
        await this.loadGrapSubmitPanels();
    }

    hideRevisionWorkspaceChrome() {
        const section = document.querySelector('.mapping-section');
        if (section) section.classList.remove('revision-mode');

        VarydianUtils.hideElement(document.getElementById('revisionRejectionBanner'));
        VarydianUtils.hideElement(document.getElementById('revisionBalanceStrip'));
        VarydianUtils.hideElement(document.getElementById('revisionResubmitPanel'));
        VarydianUtils.hideElement(document.getElementById('revisionReviewerFeedback'));
        VarydianUtils.hideElement(document.getElementById('revisionFlaggedAccountsStrip'));
        VarydianUtils.showElement(document.getElementById('mappingStandardActions'), 'flex');
    }

    detectRevisionModeFromUrl() {
        const params = new URLSearchParams(window.location.search);
        if (params.get('revision') === '1') {
            this.state.revisionRequestedFromUrl = true;
        }
    }

    getPeriodId() {
        const params = new URLSearchParams(window.location.search);
        const fromUrl = params.get('period');
        if (fromUrl) {
            return fromUrl;
        }
        try {
            for (const key of ['mappingReviewData', 'mappingData']) {
                const raw = sessionStorage.getItem(key);
                if (!raw) continue;
                const parsed = JSON.parse(raw);
                if (parsed && parsed.period_id) {
                    return parsed.period_id;
                }
            }
        } catch (_) {
            /* ignore */
        }
        return null;
    }

    getGrapSubmitConfig() {
        const dt = this.state.documentType || '';
        if (window.GrapStandards) {
            return GrapStandards.config(dt);
        }
        return { standard: 'GRAP compliance', submitButton: 'Submit for Review', success: CLERK_FORWARD_SUCCESS_MESSAGE };
    }

    submitButtonLabel(unmappedCount) {
        const base = this.getGrapSubmitConfig().submitButton;
        if (unmappedCount === 0) return base;
        return `${base} (${unmappedCount} remaining)`;
    }

    createDragGhost() {
        this.state.dragGhost = document.createElement('div');
        this.state.dragGhost.className = 'drag-ghost';
        this.state.dragGhost.style.cssText = `
            position: fixed;
            top: -1000px;
            left: -1000px;
            pointer-events: none;
            z-index: 1000;
            background: var(--primary-600);
            color: white;
            padding: 8px 12px;
            border-radius: 6px;
            font-size: 14px;
            font-weight: 600;
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
            transform: rotate(-2deg);
        `;
        document.body.appendChild(this.state.dragGhost);
    }

    async resolveDocumentType() {
        if (this.state.documentType) return this.state.documentType;
        if (this.state.mappingData && this.state.mappingData.document_type) {
            return this.state.mappingData.document_type;
        }
        const types = ['balance_sheet', 'income_statement', 'budget_report'];
        for (const dt of types) {
            try {
                const res = await fetch(
                    `/api/universal/session/${encodeURIComponent(this.state.sessionId)}?document_type=${dt}`
                );
                const data = await res.json();
                if (data && data.success !== false && !data.error) {
                    if (dt === 'budget_report' && Array.isArray(data.budget_rows)) {
                        return dt;
                    }
                    if (dt !== 'budget_report' && (data.total_rows != null || data.session_id || data.id)) {
                        return dt;
                    }
                }
            } catch (_e) {
                /* try next type */
            }
        }
        return '';
    }

    async loadGrapSubmitPanels() {
        const complianceMount = document.getElementById('grapSubmitComplianceMount');
        const budgetTableMount = document.getElementById('grap24BudgetTableMount');
        const varianceMount = document.getElementById('grap24VarianceMount');
        if (!this.state.sessionId) return;
        let documentType = await this.resolveDocumentType();
        this.state.documentType = documentType || this.state.documentType;
        if (complianceMount && window.GrapStandards) {
            complianceMount.innerHTML = GrapStandards.renderCompliancePanel(this.state.documentType);
        }
        if (this.state.isRevisionMode) {
            if (budgetTableMount) budgetTableMount.innerHTML = '';
            this.scheduleTrialBalanceCheck();
            this.refreshGrapComplianceDashboard();
            return;
        }
        const isLocked = CLERK_LOCKED_STATUSES.has(this.state.currentStatus);
        if (!varianceMount || !window.BudgetVarianceGrap24) {
            if (budgetTableMount) budgetTableMount.innerHTML = '';
            this.scheduleTrialBalanceCheck();
            this.refreshGrapComplianceDashboard();
            this.updateSubmitButton();
            return;
        }
        try {
            if (documentType === 'budget_report') {
                const res = await fetch(
                    `/api/universal/session/${encodeURIComponent(this.state.sessionId)}?document_type=budget_report`
                );
                const data = await res.json();
                if (data.budget_rows) {
                    this.state.budgetRows = data.budget_rows;
                    this.state.varianceExplanations = data.variance_explanations || {};
                    const periodLabel =
                        data.period_name ||
                        (data.metadata && (data.metadata.period_name || data.metadata.reporting_period)) ||
                        '';
                    if (budgetTableMount) {
                        budgetTableMount.innerHTML = BudgetVarianceGrap24.renderComparisonTable(
                            data.budget_rows,
                            { period: periodLabel }
                        );
                    }
                    varianceMount.innerHTML = BudgetVarianceGrap24.renderVariancePanel(
                        data.budget_rows,
                        data.variance_explanations || {},
                        { readOnly: isLocked }
                    );
                    if (!isLocked && !varianceMount.dataset.grap24LiveBound) {
                        varianceMount.dataset.grap24LiveBound = '1';
                        varianceMount.addEventListener('input', () => {
                            this.refreshGrapComplianceDashboard();
                            this.updateSubmitButton();
                        });
                    }
                }
            } else {
                if (budgetTableMount) budgetTableMount.innerHTML = '';
                if (varianceMount) varianceMount.innerHTML = '';
            }
        } catch (_err) {
            // Non-fatal
        }
        this.scheduleTrialBalanceCheck();
        this.refreshGrapComplianceDashboard();
        this.updateSubmitButton();
    }

    scheduleTrialBalanceCheck() {
        if (this.state.isRevisionMode) {
            this.scheduleBalanceRecheck();
            return;
        }
        if (this.state._trialBalanceDebounce) clearTimeout(this.state._trialBalanceDebounce);
        this.state._trialBalanceDebounce = window.setTimeout(() => this.runTrialBalanceCheck(), 400);
    }

    async runTrialBalanceCheck() {
        const dt = this.state.documentType || (await this.resolveDocumentType()) || 'balance_sheet';
        if (dt !== 'balance_sheet' && dt !== 'income_statement' && dt !== 'budget_report') {
            this.state.trialBalanceCheck = { balanced: true, message: 'N/A for this document type' };
            this.refreshGrapComplianceDashboard();
            return;
        }
        if (!this.state.sessionId) return;
        try {
            const res = await fetch('/api/universal/validate-balance', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'same-origin',
                body: JSON.stringify({
                    session_id: this.state.sessionId,
                    document_type: dt,
                }),
            });
            const data = await res.json();
            const bc = data.balance_check || data;
            const balanced = !!(bc.is_balanced ?? bc.balanced ?? data.success);
            const diff = bc.difference ?? bc.balance_difference ?? 0;
            let message;
            if (dt === 'budget_report') {
                message = balanced
                    ? 'Budget and actual lines captured'
                    : 'Add budget and actual amounts before submit';
            } else if (balanced) {
                message = 'Debits equal credits';
            } else if (dt === 'income_statement' && bc.debit_credit_balanced === false) {
                message = `Out of balance by R ${Math.abs(Number(diff)).toLocaleString('en-ZA', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
            } else if (dt === 'income_statement') {
                message = 'Map at least one revenue or expense line';
            } else {
                message = `Out of balance by R ${Math.abs(Number(diff)).toLocaleString('en-ZA', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
            }
            this.state.trialBalanceCheck = { balanced, message };
        } catch (_e) {
            this.state.trialBalanceCheck = { balanced: null, message: 'Could not verify trial balance' };
        }
        this.refreshGrapComplianceDashboard();
        this.updateSubmitButton();
        if (this.state.isRevisionMode) {
            this.updateRevisionResubmitButton();
        }
    }

    getGrapComplianceOpts() {
        const G = window.GrapStandards;
        const documentType = this.state.documentType || 'balance_sheet';
        const validationRows = this.getTrialBalanceRowsForValidation();
        const unmappedCount = this.state.unmappedAccounts.length;
        const opts = {
            validationRows,
            unmappedCount,
            trialBalance: this.state.trialBalanceCheck || {},
        };
        if (G && documentType === 'balance_sheet') {
            const mappedOnly = validationRows.filter((r) =>
                String(r.grap_code || r.grap_category || '').trim()
            );
            opts.sfpTotals = G.computeSfpTotals(mappedOnly);
            opts.perfTotals = G.computePerformanceTotals(validationRows);
        }
        if (G && documentType === 'income_statement') {
            opts.perfTotals = G.computePerformanceTotals(validationRows);
        }
        if (documentType === 'budget_report' && window.BudgetVarianceGrap24 && this.state.budgetRows) {
            const explanations = BudgetVarianceGrap24.collectFromDom(
                document.getElementById('grap24VarianceMount')
            );
            const check = BudgetVarianceGrap24.validateExplanations(
                this.state.budgetRows,
                explanations
            );
            opts.grap24 = {
                passed: check.passed,
                message: check.passed
                    ? check.required.length
                        ? `✓ ${check.required.length} variance explanation(s) complete`
                        : '✓ No variances above 10% require explanation'
                    : `Missing explanations for ${check.missing.length} line(s)`,
            };
        }
        return opts;
    }

    refreshGrapComplianceDashboard() {
        const live = document.getElementById('grapComplianceLiveMount');
        const G = window.GrapStandards;
        if (!live || !G || !G.renderMappingComplianceLive) return;
        live.innerHTML = G.renderMappingComplianceLive(
            this.state.documentType || 'balance_sheet',
            this.getGrapComplianceOpts()
        );
    }

    isClerkSubmitReady() {
        const G = window.GrapStandards;
        if (!G || !G.clerkSubmitReady) {
            return this.state.unmappedAccounts.length === 0;
        }
        return G.clerkSubmitReady(this.state.documentType, this.getGrapComplianceOpts());
    }

    async ensureBudgetVarianceExplanationsSaved() {
        if (this.state.documentType !== 'budget_report' || !this.state.budgetRows || !window.BudgetVarianceGrap24) {
            return true;
        }
        const explanations = BudgetVarianceGrap24.collectFromDom(document.getElementById('grap24VarianceMount'));
        const check = BudgetVarianceGrap24.validateExplanations(this.state.budgetRows, explanations);
        if (!check.passed) {
            this.showError(
                'GRAP 24: provide variance explanations for all line items exceeding 10%: '
                + check.missing.slice(0, 5).join(', ')
                + (check.missing.length > 5 ? '…' : '')
            );
            return false;
        }
        if (check.required.length === 0) return true;
        const result = await BudgetVarianceGrap24.saveExplanations(
            this.state.sessionId,
            'budget_report',
            explanations
        );
        if (!result.success) {
            this.showError(result.error || 'Could not save variance explanations');
            return false;
        }
        return true;
    }

    async applySessionLockFromServer() {
        if (!this.state.sessionId) return;
        try {
            const response = await fetch(`/api/submission-status/${this.state.sessionId}`);
            const result = await response.json();
            if (result.success && result.status) {
                this.state.currentStatus = result.status;
                if (result.is_correction_mode) {
                    this.state.isRevisionMode = true;
                } else {
                    this.state.isRevisionMode = false;
                    if (this.state.revisionRequestedFromUrl) {
                        this.showError(
                            'This session is not in correction mode. Upload a new file or open a rejected submission from history.'
                        );
                    }
                }
                this.state.revisionRequestedFromUrl = false;
                if (result.is_correction_mode && result.rejection_reason) {
                    this.state.rejectionReason = result.rejection_reason;
                } else if (!result.is_correction_mode) {
                    this.state.rejectionReason = '';
                }
                if (result.locked || CLERK_LOCKED_STATUSES.has(result.status)) {
                    this.showSubmissionStatus(result.status);
                    this.updateMappingInterfaceState(result.status);
                }
            }
        } catch (_err) {
            // Non-fatal: mapping still usable in draft/uploaded state
        }
    }

    async maybeEnterRevisionMode() {
        if (!this.state.isRevisionMode || !this.state.sessionId) return;
        await this.loadRevisionContext();
        this.activateRevisionWorkspace();
        this.renderUnmappedAccounts();
        this.renderCategories();
        this.updateSectionBadges();
        this.refreshFlaggedAccountsStrip();
    }

    async loadRevisionContext() {
        try {
            const docType = await this.resolveDocumentType();
            const q = docType ? `?document_type=${encodeURIComponent(docType)}` : '';
            const res = await fetch(
                `/api/universal/correction-workspace/${encodeURIComponent(this.state.sessionId)}${q}`,
                { credentials: 'same-origin' }
            );
            const data = await res.json();
            if (!data.success) {
                this.showError(data.error || 'Could not load correction workspace');
                return;
            }
            this.state.documentType = data.document_type || this.state.documentType;
            this.state.currentStatus = data.status || this.state.currentStatus;
            this.state.rejectionBanner = data.rejection_banner || {};
            this.state.revisionTimeline = data.timeline || [];
            this.state.revisionLineComments = data.line_item_comments || [];
            if (data.rejection_reason) {
                this.state.rejectionReason = data.rejection_reason;
            }
        } catch (err) {
            this.showError('Failed to load rejection details.');
        }
    }

    activateRevisionWorkspace() {
        const section = document.querySelector('.mapping-section');
        if (section) section.classList.add('revision-mode');

        const title = document.getElementById('mappingPageTitle');
        const subtitle = document.getElementById('mappingPageSubtitle');
        if (title) title.textContent = 'Correction workspace';
        if (subtitle) {
            subtitle.textContent =
                'Mapping is unlocked. Apply the manager’s feedback, confirm the trial balance still balances, then resubmit.';
        }

        const banner = document.getElementById('revisionRejectionBanner');
        const bannerTitle = document.getElementById('revisionRejectionTitle');
        const bannerReason = document.getElementById('revisionRejectionReason');
        const rb = this.state.rejectionBanner || {};
        if (banner) VarydianUtils.showElement(banner, 'flex');
        if (bannerTitle) {
            bannerTitle.textContent = rb.title || 'Rejected — correction required';
        }
        if (bannerReason) {
            bannerReason.textContent =
                rb.reason || this.state.rejectionReason || 'Review the manager comment and update mappings.';
        }

        VarydianUtils.showElement(document.getElementById('revisionBalanceStrip'), 'flex');
        VarydianUtils.showElement(document.getElementById('revisionResubmitPanel'), 'flex');
        this.renderRevisionReviewerFeedback();
        this.refreshFlaggedAccountsStrip();
        VarydianUtils.hideElement(document.getElementById('mappingStandardActions'));

        this.enableMapping();
        if (this.elements.submitMappingBtn) {
            this.elements.submitMappingBtn.disabled = true;
        }

        const noteEl = document.getElementById('clerkCorrectionNote');
        if (noteEl && !noteEl.dataset.bound) {
            noteEl.dataset.bound = '1';
            noteEl.addEventListener('input', () => {
                this.state.correctionNote = noteEl.value.trim();
                this.updateRevisionResubmitButton();
            });
        }

        const resubmitBtn = document.getElementById('revisionResubmitBtn');
        if (resubmitBtn && !resubmitBtn.dataset.bound) {
            resubmitBtn.dataset.bound = '1';
            resubmitBtn.addEventListener('click', () => this.resubmitAfterCorrection());
        }

        this.scheduleBalanceRecheck();
        this.updateRevisionResubmitButton();
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text == null ? '' : String(text);
        return div.innerHTML;
    }

    revisionAccountDomId(accountCode) {
        const code = String(accountCode || '').trim();
        return `revision-account-${code.replace(/[^a-zA-Z0-9_-]/g, '_')}`;
    }

    getReviewerCommentsByAccount() {
        const map = {};
        for (const comment of this.state.revisionLineComments || []) {
            const code = String(comment.account_code || '').trim();
            if (!code) continue;
            if (!map[code]) map[code] = [];
            map[code].push(comment);
        }
        return map;
    }

    accountHasReviewerComments(accountCode) {
        const code = String(accountCode || '').trim();
        if (!code || !this.state.isRevisionMode) return false;
        return (this.getReviewerCommentsByAccount()[code] || []).length > 0;
    }

    renderAccountReviewerNotesHtml(accountCode) {
        if (!this.state.isRevisionMode) return '';
        const code = String(accountCode || '').trim();
        const comments = this.getReviewerCommentsByAccount()[code] || [];
        if (!comments.length) return '';

        const items = comments.map((c) => {
            const author = c.author_name || c.author_id || 'Reviewer';
            const body = c.comment_text || c.correction_suggestion || '';
            const type = c.comment_type || 'general';
            const correction = c.correction_suggestion && c.comment_text
                ? `<p class="account-reviewer-notes__correction"><strong>Suggested fix:</strong> ${this.escapeHtml(c.correction_suggestion)}</p>`
                : '';
            return `
                <div class="account-reviewer-notes__item">
                    <span class="account-reviewer-notes__type">${this.escapeHtml(type)} · ${this.escapeHtml(author)}</span>
                    <p class="account-reviewer-notes__text">${this.escapeHtml(body) || '<em>No comment text</em>'}</p>
                    ${correction}
                </div>`;
        }).join('');

        return `
            <div class="account-reviewer-notes" role="note" aria-label="Reviewer feedback for account ${this.escapeHtml(code)}">
                <span class="account-reviewer-notes__label">Reviewer feedback</span>
                ${items}
            </div>`;
    }

    scrollToRevisionAccount(accountCode) {
        const domId = this.revisionAccountDomId(accountCode);
        const el = document.getElementById(domId);
        if (!el) return;
        el.scrollIntoView({ behavior: 'smooth', block: 'center' });
        el.classList.add('revision-account--highlight');
        window.setTimeout(() => el.classList.remove('revision-account--highlight'), 2200);
    }

    refreshFlaggedAccountsStrip() {
        const strip = document.getElementById('revisionFlaggedAccountsStrip');
        if (!strip || !this.state.isRevisionMode) return;

        const byAccount = this.getReviewerCommentsByAccount();
        const codes = Object.keys(byAccount).sort();
        if (!codes.length) {
            VarydianUtils.hideElement(strip);
            strip.innerHTML = '';
            return;
        }

        VarydianUtils.showElement(strip, 'block');
        strip.innerHTML = `
            <p class="revision-flagged-accounts__title">
                ${codes.length} account${codes.length === 1 ? '' : 's'} flagged by reviewer — jump to account in the grid
            </p>
            <div class="revision-flagged-accounts__chips">
                ${codes.map((code) => {
                    const count = byAccount[code].length;
                    const label = count > 1 ? `${code} (${count})` : code;
                    return `<button type="button" class="revision-flagged-accounts__chip" data-account-code="${this.escapeHtml(code)}">${this.escapeHtml(label)}</button>`;
                }).join('')}
            </div>`;

        strip.querySelectorAll('.revision-flagged-accounts__chip').forEach((chip) => {
            if (chip.dataset.bound) return;
            chip.dataset.bound = '1';
            chip.addEventListener('click', () => {
                this.scrollToRevisionAccount(chip.dataset.accountCode);
            });
        });
    }

    renderRevisionReviewerFeedback() {
        const panel = document.getElementById('revisionReviewerFeedback');
        const timelineMount = document.getElementById('revisionTimelineMount');
        const commentsMount = document.getElementById('revisionLineCommentsMount');
        if (!panel || !timelineMount || !commentsMount) return;

        const timeline = this.state.revisionTimeline || [];
        const comments = this.state.revisionLineComments || [];
        const hasTimeline = timeline.length > 0;
        const hasComments = comments.length > 0;

        if (!hasTimeline && !hasComments) {
            VarydianUtils.hideElement(panel);
            return;
        }

        VarydianUtils.showElement(panel, 'block');

        if (hasTimeline) {
            timelineMount.innerHTML = `
                <section class="revision-timeline-section" aria-label="Workflow timeline">
                    <h3 class="revision-subsection-title">Workflow timeline</h3>
                    <ol class="revision-timeline-list">
                        ${timeline.map((ev) => `
                            <li class="revision-timeline-item revision-timeline-item--${this.escapeHtml(ev.type || 'event')}">
                                <div class="revision-timeline-item__head">
                                    <strong>${this.escapeHtml(ev.label || ev.type || 'Event')}</strong>
                                    <span class="revision-timeline-item__date">${this.escapeHtml(ev.at_display || ev.at || '')}</span>
                                </div>
                                ${ev.detail ? `<p class="revision-timeline-item__detail">${this.escapeHtml(ev.detail)}</p>` : ''}
                            </li>
                        `).join('')}
                    </ol>
                </section>`;
        } else {
            timelineMount.innerHTML = '';
        }

        if (hasComments) {
            const grouped = {};
            for (const c of comments) {
                const acct = String(c.account_code || '—').trim() || '—';
                if (!grouped[acct]) grouped[acct] = [];
                grouped[acct].push(c);
            }
            const accountCodes = Object.keys(grouped).sort();

            commentsMount.innerHTML = `
                <section class="revision-line-comments-section" aria-label="Line item comments by account">
                    <h3 class="revision-subsection-title">Line item comments by account</h3>
                    <div class="revision-line-comments-by-account">
                        ${accountCodes.map((acct) => {
                            const items = grouped[acct];
                            const jump = acct !== '—'
                                ? `<button type="button" class="revision-line-comment-group__jump" data-account-code="${this.escapeHtml(acct)}">View in grid ↓</button>`
                                : '';
                            const body = items.map((c) => {
                                const author = c.author_name || c.author_id || 'Reviewer';
                                const text = c.comment_text || c.correction_suggestion || '';
                                const subject = c.subject
                                    ? `<div class="revision-line-comment__subject"><strong>${this.escapeHtml(c.subject)}</strong></div>`
                                    : '';
                                const correction = c.correction_suggestion && c.comment_text
                                    ? `<p class="revision-line-comment__correction"><strong>Suggested fix:</strong> ${this.escapeHtml(c.correction_suggestion)}</p>`
                                    : '';
                                return `
                                    <article class="revision-line-comment revision-line-comment--${this.escapeHtml(c.urgency_level || 'medium')}">
                                        <header class="revision-line-comment__head">
                                            <span class="revision-line-comment__meta">${this.escapeHtml(author)} · ${this.escapeHtml(c.comment_type || 'general')}</span>
                                        </header>
                                        ${subject}
                                        <p class="revision-line-comment__text">${this.escapeHtml(text) || '<em class="text-muted">No comment text</em>'}</p>
                                        ${correction}
                                    </article>`;
                            }).join('');
                            return `
                                <div class="revision-line-comment-group">
                                    <div class="revision-line-comment-group__head">
                                        <span class="revision-line-comment-group__code">Account ${this.escapeHtml(acct)}</span>
                                        ${jump}
                                    </div>
                                    <div class="revision-line-comment-group__body">${body}</div>
                                </div>`;
                        }).join('')}
                    </div>
                </section>`;

            commentsMount.querySelectorAll('.revision-line-comment-group__jump').forEach((btn) => {
                btn.addEventListener('click', () => this.scrollToRevisionAccount(btn.dataset.accountCode));
            });
        } else {
            commentsMount.innerHTML = '';
        }
    }

    scheduleBalanceRecheck() {
        if (this.state._balanceDebounce) clearTimeout(this.state._balanceDebounce);
        this.state._balanceDebounce = window.setTimeout(() => this.runRevisionBalanceCheck(), 400);
    }

    async runRevisionBalanceCheck() {
        const strip = document.getElementById('revisionBalanceStrip');
        const valueEl = document.getElementById('revisionBalanceValue');
        const labelEl = document.getElementById('revisionBalanceLabel');
        if (!this.state.sessionId) return;

        let documentType = this.state.documentType || (await this.resolveDocumentType());
        this.state.documentType = documentType || 'balance_sheet';

        if (labelEl) {
            labelEl.textContent =
                documentType === 'budget_report' ? 'Budget vs actual check' : 'Trial balance check (Debits = Credits)';
        }
        if (valueEl) valueEl.textContent = 'Checking…';
        if (strip) strip.classList.remove('revision-balance-strip--balanced', 'revision-balance-strip--unbalanced');

        try {
            const res = await fetch('/api/universal/validate-balance', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'same-origin',
                body: JSON.stringify({
                    session_id: this.state.sessionId,
                    document_type: documentType,
                }),
            });
            const data = await res.json();
            const bc = data.balance_check || data;
            const balanced = !!(bc.is_balanced ?? bc.balanced ?? data.success);
            const diff = bc.difference ?? bc.balance_difference ?? 0;
            this.state.balanceCheck = {
                balanced,
                message: balanced
                    ? 'Balanced — debits equal credits.'
                    : `Out of balance by R ${Math.abs(Number(diff)).toLocaleString('en-ZA', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
            };
            if (valueEl) valueEl.textContent = this.state.balanceCheck.message;
            if (strip) {
                strip.classList.add(
                    balanced ? 'revision-balance-strip--balanced' : 'revision-balance-strip--unbalanced'
                );
            }
        } catch (_e) {
            this.state.balanceCheck = { balanced: false, message: 'Could not verify balance.' };
            if (valueEl) valueEl.textContent = this.state.balanceCheck.message;
        }
        this.state.trialBalanceCheck = { ...this.state.balanceCheck };
        this.refreshGrapComplianceDashboard();
        this.updateRevisionResubmitButton();
    }

    updateRevisionResubmitButton() {
        const btn = document.getElementById('revisionResubmitBtn');
        if (!btn) return;
        const noteLen = (this.state.correctionNote || '').length;
        const noteOk = noteLen >= 10;
        const mappedOk = this.state.unmappedAccounts.length === 0;
        const balanced = this.state.balanceCheck.balanced === true;
        const grapOk = this.isClerkSubmitReady();
        btn.disabled = !(noteOk && mappedOk && balanced && grapOk);
        btn.title = !noteOk
            ? 'Enter at least 10 characters explaining your correction.'
            : !mappedOk
              ? 'Map all accounts before resubmitting.'
              : !balanced
                ? 'Trial balance must be balanced before resubmitting.'
                : !grapOk
                  ? 'GRAP compliance checks must pass before resubmitting.'
                  : '';

        const counter = document.getElementById('clerkCorrectionNoteCount');
        if (counter) {
            counter.textContent = noteOk
                ? `${noteLen} characters — requirement met`
                : `${noteLen} characters (${10 - noteLen} more needed)`;
            counter.classList.toggle('revision-resubmit-panel__counter--ok', noteOk);
        }

        const checklist = document.getElementById('revisionResubmitChecklist');
        if (checklist) {
            const setDone = (req, done) => {
                const item = checklist.querySelector(`[data-req="${req}"]`);
                if (!item) return;
                item.classList.toggle('revision-resubmit-checklist__item--done', done);
                const icon = item.querySelector('.revision-resubmit-checklist__icon');
                if (icon) icon.textContent = done ? '✓' : '○';
            };
            setDone('note', noteOk);
            setDone('mapped', mappedOk);
            setDone('balanced', balanced);
            setDone('grap', grapOk);
        }
    }

    async resubmitAfterCorrection() {
        const note = (this.state.correctionNote || '').trim();
        if (note.length < 10) {
            this.showError('Please enter a correction note (at least 10 characters).');
            return;
        }
        if (this.state.unmappedAccounts.length > 0) {
            this.showError('Complete all account mappings before resubmitting.');
            return;
        }
        if (this.state.balanceCheck.balanced !== true) {
            this.showError('Trial balance must be balanced before resubmitting.');
            return;
        }
        if (!this.isClerkSubmitReady()) {
            const grapCheck = window.GrapStandards
                ? GrapStandards.validateBeforeSubmit(documentType, this.getTrialBalanceRowsForValidation())
                : { passed: false, message: 'GRAP checks failed.' };
            this.showError(grapCheck.message || 'GRAP compliance checks must pass before resubmitting.');
            return;
        }

        const documentType = this.state.documentType || (await this.resolveDocumentType()) || 'balance_sheet';
        const mappedData = this.getMappedDataForSubmission();
        const btn = document.getElementById('revisionResubmitBtn');
        if (btn) {
            btn.disabled = true;
            btn.textContent = 'Resubmitting…';
        }

        try {
            const response = await fetch('/api/submit-mapping', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'same-origin',
                body: JSON.stringify({
                    session_id: this.state.sessionId,
                    document_type: documentType,
                    mapped_data: mappedData,
                    clerk_correction_note: note,
                    period_id: this.getPeriodId(),
                }),
            });
            const result = await response.json();
            if (result.success) {
                this.showSuccess(result.message || CLERK_FORWARD_SUCCESS_MESSAGE);
                window.setTimeout(() => {
                    window.location.href = '/submission-history';
                }, 1500);
            } else {
                this.showError(result.error || 'Resubmit failed');
            }
        } catch (err) {
            this.showError('Resubmit failed. Please try again.');
        } finally {
            if (btn) {
                btn.textContent = 'Resubmit for review';
                this.updateRevisionResubmitButton();
            }
        }
    }

    cacheElements() {
        this.elements = {
            unmappedAccountsList: document.getElementById('unmappedAccountsList'),
            grapCategories: document.getElementById('grapCategories'),
            unmappedCount: document.getElementById('unmappedCount'),
            mappedCount: document.getElementById('mappedCount'),
            totalAccounts: document.getElementById('totalAccounts'),
            mappedAccounts: document.getElementById('mappedAccounts'),
            remainingAccounts: document.getElementById('remainingAccounts'),
            completionPercentage: document.getElementById('completionPercentage'),
            backToUploadBtn: document.getElementById('backToUploadBtn'),
                        submitMappingBtn: document.getElementById('submitMappingBtn'),
            submissionStatus: document.getElementById('submissionStatus'),
            statusBadge: document.getElementById('statusBadge'),
            statusMessage: document.getElementById('statusMessage'),
            statusActions: document.getElementById('statusActions'),
            editMappingBtn: document.getElementById('editMappingBtn'),
            // New: Review mode elements
            mappedAccountsReview: document.getElementById('mappedAccountsReview'),
            mappedAccountsList: document.getElementById('mappedAccountsList'),
            confidenceSummary: document.getElementById('confidenceSummary'),
            avgConfidence: document.getElementById('avgConfidence'),
            highConfidenceCount: document.getElementById('highConfidenceCount'),
            mediumConfidenceCount: document.getElementById('mediumConfidenceCount'),
            lowConfidenceCount: document.getElementById('lowConfidenceCount'),
            reviewWarnings: document.getElementById('reviewWarnings'),
            saveMappingBtn: document.getElementById('saveMappingBtn'),
            categoryCount: document.getElementById('categoryCount')
        };
    }

    checkReviewMode() {
        // Check if this is a review session
        const urlParams = new URLSearchParams(window.location.search);
        this.state.isReviewMode = urlParams.get('review') === 'true';
        
        if (this.state.isReviewMode && window.mappingData) {
            this.state.mappingData = window.mappingData;
            this.state.autoMappedAccounts = [];
            console.log('Review mode activated with data:', this.state.mappingData);
        }
    }

    loadData() {
        if (this.state.isReviewMode && this.state.mappingData) {
            // Load from review data (from upload processing)
            this.loadReviewData();
        } else if (this.state.isReviewMode && !this.state.mappingData) {
            // Review mode but no mapping data - fall back to database loading
            console.log('Review mode detected but no mapping data - loading from database');
            this.loadUnmappedAccounts();
        } else {
            // Load from database (traditional mapping)
            this.loadUnmappedAccounts();
        }
    }

    loadReviewData() {
        try {
            if (this.state.mappingData && this.state.mappingData.document_type) {
                this.state.documentType = this.state.mappingData.document_type;
            }
            console.log('🔄 Loading review data...');
            console.log('📊 Raw mappingData:', this.state.mappingData);
            
            // Check if mappingData exists
            if (!this.state.mappingData) {
                console.error('❌ No mappingData found!');
                this.showError('No mapping data available');
                return;
            }
            
            // Inspect the structure of unmapped_accounts
            const unmappedRaw = this.state.mappingData.unmapped_accounts || [];
            const mappedRaw = this.state.mappingData.mapped_accounts || [];
            
            console.log('  - Raw unmapped_accounts:', unmappedRaw);
            console.log('  - Raw mapped_accounts:', mappedRaw);
            console.log('  - First unmapped account:', unmappedRaw[0]);
            console.log('  - First mapped account:', mappedRaw[0]);
            
            // Debug: Check if unmapped accounts have proper structure
            if (unmappedRaw.length > 0) {
                console.log('🔍 Unmapped account structure analysis:');
                console.log('  - Keys in first unmapped account:', Object.keys(unmappedRaw[0]));
                console.log('  - Sample account data:', JSON.stringify(unmappedRaw[0], null, 2));
            }
            
            // Debug: Check if mapped accounts have proper structure
            if (mappedRaw.length > 0) {
                console.log('🔍 Mapped account structure analysis:');
                console.log('  - Keys in first mapped account:', Object.keys(mappedRaw[0]));
                console.log('  - Sample account data:', JSON.stringify(mappedRaw[0], null, 2));
            }
            
            // Set unmapped accounts
            this.state.unmappedAccounts = unmappedRaw;
            
            // Initialize mapped accounts structure organized by GRAP category
            this.state.mappedAccounts = {};
            
            // Process auto-mapped accounts and place them in their GRAP categories
            mappedRaw.forEach((account, index) => {
                console.log(`Processing mapped account ${index}:`, account);
                
                const grapCategory = account.grap_category || account.grap_name || 'Unknown';
                const grapCode = account.grap_code || '';
                
                console.log(`  - GRAP Category: ${grapCategory}`);
                console.log(`  - GRAP Code: ${grapCode}`);
                
                // Create standardized account object
                const code = account.account_code || account.code || '';
                const standardAccount = {
                    id: account.id || account.account_id || (code ? `${code}-${index}` : `mapped-${index}`),
                    account_desc: account.account_desc || account.name || 'Unknown Account',
                    account_code: code,
                    name: account.account_desc || account.name || 'Unknown Account',
                    code,
                    net_balance: account.net_balance ?? account.balance ?? account.amount ?? 0,
                    amount: account.net_balance ?? account.balance ?? account.amount ?? 0,
                    grapCategory: grapCategory,
                    grapCode: grapCode,
                    confidence: account.confidence || 0,
                };
                
                console.log(`  - Standardized account:`, standardAccount);
                
                // Add to the appropriate GRAP category using the CODE as key
                if (!this.state.mappedAccounts[grapCode]) {
                    this.state.mappedAccounts[grapCode] = [];
                }
                this.state.mappedAccounts[grapCode].push(standardAccount);
            });
            
            console.log('✅ Processed mapped accounts by category:', this.state.mappedAccounts);
            console.log('✅ Final unmapped accounts:', this.state.unmappedAccounts);
            
            // Hide the review section since we're putting accounts directly in categories
            if (this.elements.mappedAccountsReview) {
                this.elements.mappedAccountsReview.style.display = 'none';
            }
            
            // Render all data
            this.renderUnmappedAccounts();
            this.renderCategories(); // This will show auto-mapped accounts in their categories
            this.updateStats();
            this.updateConfidenceSummary();
            this.updateReviewStatus();
            
        } catch (error) {
            console.error('Error loading review data:', error);
            this.showError('Failed to load mapping review data');
        }
    }

    renderAutoMappedAccounts() {
        const container = this.elements.mappedAccountsList;
        if (!container) return;

        container.innerHTML = '';

        if (this.state.autoMappedAccounts.length === 0) {
            container.innerHTML = `
                <div class="no-accounts">
                    <p>No auto-mapped accounts found. All accounts require manual mapping.</p>
                </div>
            `;
            return;
        }

        this.state.autoMappedAccounts.forEach((account, index) => {
            const accountElement = this.createAutoMappedAccountElement(account, index);
            container.appendChild(accountElement);
        });
    }

    createAutoMappedAccountElement(account, index) {
        const div = document.createElement('div');
        div.className = 'mapped-account';
        div.draggable = true;
        div.dataset.index = index;

        // Determine confidence level
        const confidence = account.confidence || 0;
        let confidenceClass = 'confidence-low';
        let confidenceLabel = 'Low';
        
        if (confidence >= 0.8) {
            confidenceClass = 'confidence-high';
            confidenceLabel = 'High';
        } else if (confidence >= 0.5) {
            confidenceClass = 'confidence-medium';
            confidenceLabel = 'Medium';
        }

        div.innerHTML = `
            <div class="account-info">
                <div class="account-name">${account.name || account.account_name || 'Unknown Account'}</div>
                <div class="account-code">${account.code || account.account_code || ''}</div>
                <div class="account-amount">${this.formatCurrency(account.balance || account.amount || 0)}</div>
            </div>
            <div class="mapping-info">
                <div class="grap-category">${account.grap_name || account.grap_category || 'Unknown Category'}</div>
                <div class="grap-code">${account.grap_code || ''}</div>
                <div class="confidence-score ${confidenceClass}">
                    <span class="confidence-label">${confidenceLabel}</span>
                    <span class="confidence-value">${Math.round(confidence * 100)}%</span>
                </div>
            </div>
            <div class="account-actions">
                <button class="btn-edit-mapping" onclick="window.mappingInterface.editAccountMapping(${index})">
                    ✏️ Edit
                </button>
            </div>
        `;

        // Add drag event listeners
        div.addEventListener('dragstart', (e) => {
            e.dataTransfer.effectAllowed = 'move';
            e.dataTransfer.setData('text/plain', index);
            e.dataTransfer.setData('accountType', 'autoMapped');
            div.classList.add('dragging');
        });

        div.addEventListener('dragend', () => {
            div.classList.remove('dragging');
        });

        return div;
    }

    setupEventListeners() {
        if (this.elements.unmappedAccountsList) {
            this.elements.unmappedAccountsList.addEventListener('dragstart', this.handleDragStart.bind(this));
            this.elements.unmappedAccountsList.addEventListener('dragend', this.handleDragEnd.bind(this));
            this.elements.unmappedAccountsList.addEventListener('touchstart', this.handleTouchStart.bind(this), { passive: false });
            this.elements.unmappedAccountsList.addEventListener('touchmove', this.handleTouchMove.bind(this), { passive: false });
            this.elements.unmappedAccountsList.addEventListener('touchend', this.handleTouchEnd.bind(this), { passive: false });
        }

        if (this.elements.grapCategories) {
            this.elements.grapCategories.addEventListener('dragover', this.handleDragOver.bind(this));
            this.elements.grapCategories.addEventListener('drop', this.handleDrop.bind(this));
            this.elements.grapCategories.addEventListener('touchmove', this.handleCategoryTouchMove.bind(this), { passive: false });
            this.elements.grapCategories.addEventListener('touchend', this.handleCategoryTouchEnd.bind(this), { passive: false });
            this.elements.grapCategories.addEventListener('click', this.handleMappedAccountsClick.bind(this));
        }

        document.addEventListener('keydown', this.handleKeyDown.bind(this));

        if (this.elements.backToUploadBtn) {
            this.elements.backToUploadBtn.addEventListener('click', (e) => {
                const href = this.elements.backToUploadBtn.getAttribute('href') || '/upload';
                const dt = this.state.documentType || '';
                if (dt) {
                    e.preventDefault();
                    window.location.href = `${href}${href.includes('?') ? '&' : '?'}document_type=${encodeURIComponent(dt)}`;
                }
            });
        }

        if (this.elements.submitMappingBtn) {
            this.elements.submitMappingBtn.addEventListener('click', this.submitMapping.bind(this));
        }
        
        // Save mapping button event
        const saveMappingBtn = document.getElementById('saveMappingBtn');
        if (saveMappingBtn) {
            saveMappingBtn.addEventListener('click', this.saveMappingProgress.bind(this));
        }
        
        // Submission events
        if (this.elements.editMappingBtn) {
            this.elements.editMappingBtn.addEventListener('click', this.editMapping.bind(this));
        }
        
        // Search/filter events
        const searchInput = document.getElementById('searchInput');
        if (searchInput) {
            searchInput.addEventListener('input', this.filterAccounts.bind(this));
        }
    }

    async loadGRAPCategories() {
        try {
            const response = await fetch(`/api/grap-categories/${this.state.sessionId}`);
            const result = await response.json();
            
            // Check if we have categories (API returns categories directly, not wrapped in success)
            if (result.categories && Array.isArray(result.categories)) {
                this.state.grapCategories = result.categories;
                this.renderCategories();
                this.updateSectionBadges();
            } else if (result.error) {
                this.showError(result.error);
            } else {
                this.showError('Unexpected response format from server');
            }
        } catch (error) {
            this.showError('Failed to load GRAP categories. Please try again.');
        }
    }

    async loadUnmappedAccounts() {
        try {
            console.log('🔄 Loading unmapped accounts for session:', this.state.sessionId);
            
            // Load from Supabase API
            const response = await fetch(`/api/unmapped-accounts/${this.state.sessionId}`);
            const result = await response.json();
            
            console.log('📊 API Response:', result);
            
            if (result.success) {
                this.state.unmappedAccounts = result.accounts;
                this.state.mappedAccounts = result.mapped_accounts || {};
                
                console.log('✅ Data loaded successfully:');
                console.log('  - Unmapped accounts:', this.state.unmappedAccounts.length);
                console.log('  - Mapped categories:', Object.keys(this.state.mappedAccounts).length);
                
                this.renderUnmappedAccounts();
                this.renderCategories();
                this.updateStats();
                this.updateSectionBadges();
                this.updateConfidenceSummary();
            } else {
                console.error('❌ API Error:', result.error);
                this.showError(result.error || 'Failed to load accounts');
            }
        } catch (error) {
            console.error('💥 Network Error:', error);
            this.showError('Failed to load accounts. Please try again.');
        }
    }

    renderCategories() {
        if (!this.elements.grapCategories) return;
        console.log('🎨 Rendering GRAP categories...');
        console.log('  - Element exists:', !!this.elements.grapCategories);
        console.log('  - Categories available:', this.state.grapCategories.length);
        console.log('  - Mapped accounts:', this.state.mappedAccounts);
        
        this.elements.grapCategories.innerHTML = '';
        
        this.state.grapCategories.forEach(category => {
            console.log(`  Rendering category: ${category.name} (${category.code})`);
            
            const categoryEl = document.createElement('div');
            categoryEl.className = 'grap-category';
            categoryEl.dataset.categoryId = category.code;
            categoryEl.setAttribute('tabindex', '0');
            categoryEl.setAttribute('role', 'button');
            categoryEl.setAttribute('aria-label', `GRAP Category: ${category.name}`);

            categoryEl.innerHTML = `
                <div class="category-header">
                    <h3>${category.name}</h3>
                    <span class="category-code">${category.code}</span>
                </div>
                <div class="mapped-accounts" data-category="${category.code}">
                    ${this.renderMappedAccounts(category.code)}
                </div>
            `;
            
            this.elements.grapCategories.appendChild(categoryEl);
        });
        
        console.log('✅ GRAP categories rendered successfully');
    }

    renderMappedAccounts(categoryId) {
        const mappedAccounts = this.state.mappedAccounts[categoryId] || [];
        
        if (mappedAccounts.length === 0) {
            return '<div class="empty-category">Drop accounts here</div>';
        }
        
        return mappedAccounts.map((account, index) => {
            // Determine confidence level
            const confidence = account.confidence || 0;
            let confidenceClass = 'confidence-low';
            let confidenceLabel = 'Low';
            
            if (confidence >= 0.8) {
                confidenceClass = 'confidence-high';
                confidenceLabel = 'High';
            } else if (confidence >= 0.5) {
                confidenceClass = 'confidence-medium';
                confidenceLabel = 'Medium';
            }
            
            const accountName = account.account_desc || account.name || 'Unknown Account';
            const accountCode = account.account_code || account.code || '';
            const accountAmount = account.net_balance ?? account.amount ?? account.balance ?? 0;
            const accountKey = this.accountKey(account, `${categoryId}-${index}`);
            const flaggedClass = this.accountHasReviewerComments(accountCode)
                ? ' mapped-account--reviewer-flagged'
                : '';
            const domId = accountCode ? ` id="${this.revisionAccountDomId(accountCode)}"` : '';
            const reviewerNotes = this.renderAccountReviewerNotesHtml(accountCode);
            
            return `
                <div class="mapped-account${flaggedClass}"${domId} data-account-id="${accountKey}" data-category-id="${categoryId}" data-account-code="${this.escapeHtml(accountCode)}" draggable="true">
                    <div class="account-info">
                        <div class="account-name">${accountName}</div>
                        <div class="account-code">${accountCode}</div>
                        <div class="account-amount">${this.formatCurrency(accountAmount)}</div>
                    </div>
                    ${reviewerNotes}
                    <div class="confidence-score ${confidenceClass}">
                        <span class="confidence-label">${confidenceLabel}</span>
                        <span class="confidence-value">${Math.round(confidence * 100)}%</span>
                    </div>
                    <button type="button" class="remove-account" aria-label="Remove mapping for ${accountName}">×</button>
                </div>
            `;
        }).join('');
    }

    accountKey(account, fallback = '') {
        if (account == null) return String(fallback || 'unknown');
        const id = account.id ?? account.account_id;
        if (id != null && id !== '') return String(id);
        const code = account.account_code ?? account.code;
        if (code != null && code !== '') return String(code);
        return String(fallback || 'unknown');
    }

    accountMatchesKey(account, key) {
        const want = String(key);
        return [account.id, account.account_id, account.account_code, account.code]
            .filter((v) => v != null && v !== '')
            .some((v) => String(v) === want);
    }

    normalizeAccountForUnmapped(account) {
        const code = account.account_code || account.code || '';
        return {
            ...account,
            id: account.id || account.account_id || code || account.id,
            account_code: code,
            account_desc: account.account_desc || account.name || account.description || '',
            code,
            name: account.account_desc || account.name || '',
            net_balance: account.net_balance ?? account.amount ?? account.balance ?? 0,
            amount: account.net_balance ?? account.amount ?? account.balance ?? 0,
        };
    }

    handleMappedAccountsClick(e) {
        const btn = e.target.closest('.remove-account');
        if (!btn) return;
        e.preventDefault();
        e.stopPropagation();

        if (this.elements.grapCategories?.classList.contains('mapping-locked')) {
            return;
        }

        const row = btn.closest('.mapped-account');
        const categoryEl = btn.closest('.grap-category');
        if (!row || !categoryEl) return;

        this.removeMapping(row.dataset.accountId, categoryEl.dataset.categoryId);
    }

    renderUnmappedAccounts() {
        if (!this.elements.unmappedAccountsList) return;

        this.elements.unmappedAccountsList.innerHTML = '';
        
        if (this.state.unmappedAccounts.length === 0) {
            console.log('⚠️ No unmapped accounts to render');
            this.elements.unmappedAccountsList.innerHTML = '<div class="no-accounts">No accounts to map</div>';
            return;
        }
        
        this.state.unmappedAccounts.forEach((account, index) => {
            console.log(`  Rendering account ${index + 1}: ${account.account_code || account.code} - ${account.account_desc || account.name}`);
            
            const accountCode = account.account_code || account.code || '';
            const accountEl = document.createElement('div');
            accountEl.className = 'unmapped-account';
            if (this.accountHasReviewerComments(accountCode)) {
                accountEl.classList.add('unmapped-account--reviewer-flagged');
            }
            if (accountCode) {
                accountEl.id = this.revisionAccountDomId(accountCode);
            }
            accountEl.draggable = true;
            accountEl.dataset.accountId = account.id || account.account_code || index.toString();
            accountEl.dataset.accountCode = accountCode;
            
            accountEl.innerHTML = `
                <div class="account-name">${account.account_desc || account.name || 'Unknown Account'}</div>
                <div class="account-code">${accountCode}</div>
                <div class="account-amount">${this.formatCurrency(account.net_balance || account.amount || 0)}</div>
                <div class="account-description">${account.account_desc || account.description || ''}</div>
                ${this.renderAccountReviewerNotesHtml(accountCode)}
            `;
            
            this.elements.unmappedAccountsList.appendChild(accountEl);
        });
        
        console.log('✅ Unmapped accounts rendered successfully');
    }

    handleDragStart(e) {
        if (e.target.closest('.remove-account')) {
            e.preventDefault();
            return;
        }
        const accountEl = e.target.closest('.unmapped-account, .mapped-account');
        if (!accountEl) return;

        this.state.isDragging = true;
        this.state.draggedAccount = {
            id: accountEl.dataset.accountId,
            element: accountEl,
            sourceType: accountEl.classList.contains('unmapped-account') ? 'unmapped' : 'mapped',
        };

        accountEl.classList.add('dragging');
        e.dataTransfer.effectAllowed = 'move';
        e.dataTransfer.setData('text/plain', this.state.draggedAccount.id);
        e.dataTransfer.setData('sourceType', this.state.draggedAccount.sourceType);

        if (this.state.dragGhost) {
            const accountName = accountEl.querySelector('.account-name')?.textContent || 'Account';
            this.state.dragGhost.textContent = accountName;
            e.dataTransfer.setDragImage(this.state.dragGhost, 0, 0);
        }

        if ('vibrate' in navigator) {
            navigator.vibrate(50);
        }
    }

    handleDragEnd() {
        this.state.isDragging = false;
        this.state.draggedAccount = null;

        const draggingEl = document.querySelector('.dragging');
        if (draggingEl) {
            draggingEl.classList.remove('dragging');
        }

        document.querySelectorAll('.drag-over').forEach((el) => el.classList.remove('drag-over'));
    }

    handleDragOver(e) {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';

        const categoryEl = e.target.closest('.grap-category');
        if (!categoryEl || !this.state.isDragging) return;

        document.querySelectorAll('.drag-over').forEach((el) => el.classList.remove('drag-over'));
        categoryEl.classList.add('drag-over');

        const dropZone = categoryEl.querySelector('.mapped-accounts');
        if (dropZone) {
            dropZone.style.background = 'var(--primary-50)';
            dropZone.style.borderColor = 'var(--primary-300)';
        }
    }

    handleDrop(e) {
        e.preventDefault();

        const categoryEl = e.target.closest('.grap-category');
        if (!categoryEl || !this.state.draggedAccount) return;

        categoryEl.classList.remove('drag-over');

        const dropZone = categoryEl.querySelector('.mapped-accounts');
        if (dropZone) {
            dropZone.style.background = '';
            dropZone.style.borderColor = '';
        }

        this.addMapping(this.state.draggedAccount.id, categoryEl.dataset.categoryId);

        if ('vibrate' in navigator) {
            navigator.vibrate([50, 50, 100]);
        }
    }

    handleTouchStart(e) {
        const accountEl = e.target.closest('.unmapped-account, .mapped-account');
        if (!accountEl) return;

        const touch = e.touches[0];
        this.state.touchStartX = touch.clientX;
        this.state.touchStartY = touch.clientY;
        this.state.draggedElement = accountEl;
        accountEl.classList.add('dragging');
        e.preventDefault();
    }

    handleTouchMove(e) {
        if (!this.state.draggedElement) return;

        const touch = e.touches[0];
        const deltaX = touch.clientX - this.state.touchStartX;
        const deltaY = touch.clientY - this.state.touchStartY;

        if (Math.abs(deltaX) > 10 || Math.abs(deltaY) > 10) {
            this.createTouchFeedback(touch.clientX, touch.clientY);
            e.preventDefault();
        }
    }

    handleTouchEnd(e) {
        if (!this.state.draggedElement) return;

        const touch = e.changedTouches[0];
        const targetElement = document.elementFromPoint(touch.clientX, touch.clientY);
        const categoryEl = targetElement?.closest('.grap-category');

        this.state.draggedElement.classList.remove('dragging');

        if (categoryEl) {
            this.addMapping(this.state.draggedElement.dataset.accountId, categoryEl.dataset.categoryId);
        }

        this.removeTouchFeedback();
        this.state.draggedElement = null;
        e.preventDefault();
    }

    handleCategoryTouchMove(e) {
        if (!this.state.draggedElement) return;

        const categoryEl = e.target.closest('.grap-category');
        if (categoryEl) {
            document.querySelectorAll('.drag-over').forEach((el) => el.classList.remove('drag-over'));
            categoryEl.classList.add('drag-over');
        }
        e.preventDefault();
    }

    handleCategoryTouchEnd(e) {
        if (!this.state.draggedElement) return;

        const categoryEl = e.target.closest('.grap-category');
        if (categoryEl) {
            this.addMapping(this.state.draggedElement.dataset.accountId, categoryEl.dataset.categoryId);
        }

        document.querySelectorAll('.drag-over').forEach((el) => el.classList.remove('drag-over'));
        this.state.draggedElement = null;
        e.preventDefault();
    }

    createTouchFeedback(x, y) {
        this.removeTouchFeedback();
        const feedback = document.createElement('div');
        feedback.className = 'touch-feedback';
        feedback.style.cssText = `
            position: fixed;
            left: ${x}px;
            top: ${y}px;
            width: 60px;
            height: 60px;
            background: var(--primary-600);
            color: white;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 24px;
            z-index: 1000;
            pointer-events: none;
            transform: translate(-50%, -50%);
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        `;
        feedback.textContent = '📄';
        document.body.appendChild(feedback);
        this.state.touchFeedback = feedback;
    }

    removeTouchFeedback() {
        if (this.state.touchFeedback) {
            this.state.touchFeedback.remove();
            this.state.touchFeedback = null;
        }
    }

    handleKeyDown(e) {
        if (e.key === 'Escape') {
            this.cancelDrag();
        }
    }

    cancelDrag() {
        if (this.state.draggedElement) {
            this.state.draggedElement.classList.remove('dragging');
            this.state.draggedElement = null;
        }
        this.removeTouchFeedback();
        this.state.isDragging = false;
        this.state.draggedAccount = null;
        document.querySelectorAll('.drag-over').forEach((el) => el.classList.remove('drag-over'));
    }

    startKeyboardDrag(element) {
        this.state.draggedAccount = {
            id: element.dataset.accountId,
            element,
            sourceType: 'unmapped',
        };
        element.classList.add('dragging');
        this.showNotification('Select a GRAP category and press Enter to map the account', 'info');
    }

    addMapping(accountId, categoryId) {
        try {
            console.log('🔄 Adding mapping:', { accountId, categoryId });
            
            // Update local state directly (no API call needed for demo)
            const account = this.state.unmappedAccounts.find(a => a.account_code === accountId || a.id === accountId);
            console.log('  - Found account:', account);
            
            if (account) {
                // Remove from unmapped
                this.state.unmappedAccounts = this.state.unmappedAccounts.filter(a => a.account_code !== accountId && a.id !== accountId);
                
                // Add to mapped
                if (!this.state.mappedAccounts[categoryId]) {
                    this.state.mappedAccounts[categoryId] = [];
                }
                this.state.mappedAccounts[categoryId].push(account);
                
                console.log('  - Account added to category:', categoryId);
                console.log('  - Updated mapped accounts:', this.state.mappedAccounts);
                console.log('  - Updated unmapped accounts:', this.state.unmappedAccounts);
                
                // Update UI
                this.renderUnmappedAccounts();
                this.renderCategories();
                this.updateStats();
                
                this.showSuccess(`Account "${account.account_desc}" mapped to ${categoryId}`);
            } else {
                console.error('❌ Account not found:', accountId);
                this.showError('Account not found for mapping.');
            }
        } catch (error) {
            console.error('💥 Error in addMapping:', error);
            this.showError('Failed to add mapping. Please try again.');
        }
    }

    removeMapping(accountId, categoryId) {
        try {
            let foundAccount = null;

            const removeFromCategory = (catId) => {
                const accounts = this.state.mappedAccounts[catId];
                if (!Array.isArray(accounts)) return false;
                const accountIndex = accounts.findIndex((a) => this.accountMatchesKey(a, accountId));
                if (accountIndex < 0) return false;
                foundAccount = accounts.splice(accountIndex, 1)[0];
                if (!accounts.length) {
                    delete this.state.mappedAccounts[catId];
                }
                return true;
            };

            if (categoryId && !removeFromCategory(categoryId)) {
                for (const catId of Object.keys(this.state.mappedAccounts)) {
                    if (catId !== categoryId && removeFromCategory(catId)) break;
                }
            } else if (!categoryId) {
                for (const catId of Object.keys(this.state.mappedAccounts)) {
                    if (removeFromCategory(catId)) break;
                }
            }

            if (foundAccount) {
                const restored = this.normalizeAccountForUnmapped(foundAccount);
                const alreadyUnmapped = this.state.unmappedAccounts.some((a) =>
                    this.accountMatchesKey(a, accountId)
                );
                if (!alreadyUnmapped) {
                    this.state.unmappedAccounts.push(restored);
                }

                this.renderUnmappedAccounts();
                this.renderCategories();
                this.updateStats();
                this.showSuccess(
                    `Removed "${restored.account_desc || restored.name || restored.account_code}" from mapping`
                );
            } else {
                this.showError('Could not find that account in the selected category.');
            }
        } catch (error) {
            console.error('removeMapping failed:', error);
            this.showError('Failed to remove mapping. Please try again.');
        }
    }

    async autoMap() {
        try {
            this.elements.autoMapBtn.disabled = true;
            this.elements.autoMapBtn.textContent = 'Auto-mapping...';
            
            const response = await fetch(`/api/auto-map/${this.state.sessionId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            const result = await response.json();
            
            if (result.success) {
                
                // Apply the auto-mapping results
                if (result.mapping_results) {
                    for (const [categoryId, accounts] of Object.entries(result.mapping_results)) {
                        if (!this.state.mappedAccounts[categoryId]) {
                            this.state.mappedAccounts[categoryId] = [];
                        }
                        
                        accounts.forEach(account => {
                            // Remove from unmapped accounts using flexible field matching
                            const accountIndex = this.state.unmappedAccounts.findIndex(ua => {
                                // Try multiple field combinations to find matching account
                                return ua.code === account['Account Code'] || 
                                       ua['Account Code'] === account['Account Code'] ||
                                       ua.code === account.code ||
                                       ua.name === account['Account Description'] ||
                                       ua.name === account.name;
                            });
                            if (accountIndex > -1) {
                                const unmappedAccount = this.state.unmappedAccounts.splice(accountIndex, 1)[0];
                                // Add to mapped accounts
                                this.state.mappedAccounts[categoryId].push(unmappedAccount);
                            }
                        });
                    }
                    
                    // Update the UI
                    this.renderUnmappedAccounts();
                    this.renderCategories();
                    this.updateStats();
                }
                
                this.showSuccess(`Auto-mapped ${result.mapped_count} out of ${result.total_accounts} accounts`);
            } else {
                this.showError(result.error || 'Auto-mapping failed');
            }
        } catch (error) {
            this.showError('Auto-mapping failed. Please try again.');
        } finally {
            this.elements.autoMapBtn.disabled = false;
            this.elements.autoMapBtn.textContent = 'Auto Map';
        }
    }

    formatAccountLabel(count) {
        if (count === 1) {
            return '1 account';
        }
        return `${count} accounts`;
    }

    formatCategoryLabel(populatedCount, totalAvailable) {
        if (totalAvailable > 0 && populatedCount !== totalAvailable) {
            return `${populatedCount} of ${totalAvailable} categories`;
        }
        if (populatedCount === 1) {
            return '1 category';
        }
        return `${populatedCount} categories`;
    }

    getPopulatedCategoryCount() {
        return Object.values(this.state.mappedAccounts || {})
            .filter((accounts) => Array.isArray(accounts) && accounts.length > 0)
            .length;
    }

    updateSectionBadges() {
        const unmapped = this.state.unmappedAccounts.length;
        const populatedCategories = this.getPopulatedCategoryCount();
        const totalCategories = (this.state.grapCategories || []).length;

        if (this.elements.unmappedCount) {
            this.elements.unmappedCount.textContent = this.formatAccountLabel(unmapped);
        }
        if (this.elements.categoryCount) {
            this.elements.categoryCount.textContent = this.formatCategoryLabel(
                populatedCategories,
                totalCategories
            );
        }
    }

    updateStats() {
        console.log('📊 Updating statistics...');
        
        const totalAccounts = this.state.unmappedAccounts.length + this.getTotalMappedAccounts();
        const mappedAccounts = this.getTotalMappedAccounts();
        const remainingAccounts = this.state.unmappedAccounts.length;
        const populatedCategories = this.getPopulatedCategoryCount();
        const completionPercentage = totalAccounts > 0 ? Math.round((mappedAccounts / totalAccounts) * 100) : 0;

        console.log('  - Total accounts:', totalAccounts);
        console.log('  - Mapped accounts:', mappedAccounts);
        console.log('  - Remaining accounts:', remainingAccounts);
        console.log('  - Categories in use:', populatedCategories);
        console.log('  - Completion percentage:', completionPercentage + '%');

        if (this.elements.totalAccounts) {
            this.elements.totalAccounts.textContent = totalAccounts;
        }
        if (this.elements.mappedAccounts) {
            this.elements.mappedAccounts.textContent = mappedAccounts;
        }
        if (this.elements.remainingAccounts) {
            this.elements.remainingAccounts.textContent = remainingAccounts;
        }
        if (this.elements.completionPercentage) {
            this.elements.completionPercentage.textContent = completionPercentage + '%';
        }

        this.updateSectionBadges();

        console.log('✅ Statistics updated');

        this.updateSubmitButton();
        this.checkMappingCompletion();
        this.scheduleTrialBalanceCheck();
        this.refreshGrapComplianceDashboard();
        if (this.state.isRevisionMode) {
            this.updateRevisionResubmitButton();
        }
    }

    getTotalMappedAccounts() {
        let total = 0;
        for (const categoryId in this.state.mappedAccounts) {
            total += this.state.mappedAccounts[categoryId].length;
        }
        return total;
    }

    updateSubmitButton() {
        if (this.state.isRevisionMode) return;
        const unmappedCount = this.state.unmappedAccounts.length;
        const submitBtn = this.elements.submitMappingBtn;
        const ready = this.isClerkSubmitReady();

        if (submitBtn) {
            if (unmappedCount === 0 && ready) {
                submitBtn.disabled = false;
                submitBtn.textContent = this.submitButtonLabel(0);
                submitBtn.classList.remove('disabled');
                submitBtn.title = '';
            } else {
                submitBtn.disabled = true;
                submitBtn.textContent = this.submitButtonLabel(unmappedCount);
                submitBtn.classList.add('disabled');
                if (unmappedCount > 0) {
                    submitBtn.title = 'Map all accounts before submit';
                } else if (!ready) {
                    const dt = this.state.documentType || 'balance_sheet';
                    submitBtn.title =
                        dt === 'balance_sheet'
                            ? 'Trial balance and GRAP 1 (SFP) equation must pass'
                            : dt === 'income_statement'
                              ? 'Map revenue/expense lines for GRAP 1 (Performance)'
                              : 'Complete GRAP 24 variance explanations';
                }
            }
        }
    }

    async submitMapping() {
        const documentType = this.state.documentType || (await this.resolveDocumentType()) || 'balance_sheet';
        this.state.documentType = documentType;
        const grapConfig = this.getGrapSubmitConfig();
        const unmappedCount = this.state.unmappedAccounts.length;
        if (unmappedCount > 0) {
            const confirmed = await showConfirm(
                grapConfig.submitButton,
                `You still have ${unmappedCount} unmapped accounts. Submit for review under ${grapConfig.standard}?`
            );
            if (!confirmed) return;
        }

        if (!(await this.ensureBudgetVarianceExplanationsSaved())) {
            return;
        }

        const mappedData = this.getMappedDataForSubmission();
        if (window.GrapStandards) {
            const validationRows = this.getTrialBalanceRowsForValidation();
            const grapCheck = GrapStandards.validateBeforeSubmit(documentType, validationRows);
            if (!grapCheck.passed) {
                let msg = grapCheck.message || `${grapConfig.standard}: checks failed before submit.`;
                if (this.state.unmappedAccounts.length) {
                    const names = this.state.unmappedAccounts
                        .map((a) => a.account_desc || a.name || a.account_code || a.code)
                        .filter(Boolean)
                        .join(', ');
                    msg += ` Map these unmapped accounts before submit: ${names}.`;
                }
                this.showError(msg);
                return;
            }
            if (
                documentType === 'balance_sheet' &&
                this.state.unmappedAccounts.length > 0
            ) {
                this.showError(
                    'All trial balance accounts must be mapped to a GRAP category before submit.'
                );
                return;
            }
        }
        
        try {
            this.elements.submitMappingBtn.disabled = true;
            this.elements.submitMappingBtn.textContent = 'Submitting...';
            
            const response = await fetch('/api/submit-mapping', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    mapped_data: mappedData,
                    session_id: this.state.sessionId,
                    document_type: documentType,
                    period_id: this.getPeriodId(),
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showSuccess(result.message || grapConfig.success || CLERK_FORWARD_SUCCESS_MESSAGE);
                setTimeout(() => {
                    // Redirect to the submission status page using the submission_id returned
                    window.location.href = `/submission/${result.submission_id}`;
                }, 1500);
            } else {
                this.showError(result.error || 'Failed to submit mapping');
            }
        } catch (error) {
            this.showError('Failed to submit mapping. Please try again.');
        } finally {
            if (!CLERK_LOCKED_STATUSES.has(this.state.currentStatus)) {
                this.elements.submitMappingBtn.disabled = false;
                this.updateSubmitButton();
            }
        }
    }

    filterAccounts(e) {
        const searchTerm = e.target.value.toLowerCase();
        const accountEls = this.elements.unmappedAccountsList.querySelectorAll('.unmapped-account');
        
        accountEls.forEach(accountEl => {
            const accountName = accountEl.querySelector('.account-name').textContent.toLowerCase();
            const accountCode = accountEl.querySelector('.account-code').textContent.toLowerCase();
            
            if (accountName.includes(searchTerm) || accountCode.includes(searchTerm)) {
                accountEl.classList.remove('account-hidden');
            } else {
                accountEl.classList.add('account-hidden');
            }
        });
    }

    formatCurrency(amount) {
        return 'R ' + new Intl.NumberFormat('en-ZA', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        }).format(amount);
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
        notification.className = `notification notification-${type} notification--center`;
        notification.textContent = message;
        notification.setAttribute('role', 'alert');
        document.body.appendChild(notification);
        setTimeout(() => notification.remove(), 8000);
    }

    // Submission workflow methods
    showSubmissionStatus(status = 'draft') {
        if (!this.elements.submissionStatus) return;
        
        this.elements.submissionStatus.classList.remove('submission-hidden');
        this.updateSubmissionUI(status);
    }

    updateSubmissionUI(status) {
        if (!this.elements.statusBadge || !this.elements.statusMessage) return;
        
        // Update badge
        this.elements.statusBadge.className = `status-badge ${status}`;
        this.elements.statusBadge.textContent = status.charAt(0).toUpperCase() + status.slice(1);
        
        // Update message
        const messages = {
            draft: 'Your balance sheet mapping is ready for submission.',
            pending: 'Data forwarded to Finance Manager for review. This record is read-only.',
            pending_review: 'Data forwarded to Finance Manager for review. This record is read-only.',
            submitted: 'Data forwarded to Finance Manager for review. This record is read-only.',
            approved: 'This submission was approved. Export is handled by the CFO after finalization.',
            rejected: 'Your balance sheet was rejected. You can edit the mapping and resubmit.',
            rejected_by_manager: 'Rejected by the Finance Manager. Review the feedback, correct mappings, and resubmit.'
        };
        
        this.elements.statusMessage.textContent = messages[status] || 'Status unknown.';
        
        // Update buttons
        this.updateSubmissionActions(status);
        
        // Update mapping interface state
        this.updateMappingInterfaceState(status);
    }

    updateSubmissionActions(status) {
        if (!this.elements.statusActions) return;
        
        const submitBtn = this.elements.submitMappingBtn;
        const editBtn = this.elements.editMappingBtn;
        
        switch (status) {
            case 'draft':
                if (submitBtn) {
                    submitBtn.classList.remove('button-hidden');
                    submitBtn.classList.add('button-visible');
                }
                if (editBtn) {
                    editBtn.classList.add('button-hidden');
                    editBtn.classList.remove('button-visible');
                }
                break;
            case 'pending':
            case 'pending_review':
            case 'submitted':
            case 'pending_cfo':
                if (submitBtn) {
                    submitBtn.classList.add('button-hidden');
                    submitBtn.classList.remove('button-visible');
                }
                if (editBtn) {
                    editBtn.classList.add('button-hidden');
                    editBtn.classList.remove('button-visible');
                }
                break;
            case 'rejected':
            case 'rejected_by_manager':
                if (submitBtn) {
                    submitBtn.classList.remove('button-hidden');
                    submitBtn.classList.add('button-visible');
                }
                if (editBtn) {
                    editBtn.classList.remove('button-hidden');
                    editBtn.classList.add('button-visible');
                }
                break;
            case 'approved':
                if (submitBtn) {
                    submitBtn.classList.add('button-hidden');
                    submitBtn.classList.remove('button-visible');
                }
                if (editBtn) {
                    editBtn.classList.add('button-hidden');
                    editBtn.classList.remove('button-visible');
                }
                break;
        }
    }

    updateMappingInterfaceState(status) {
        const isLocked = CLERK_LOCKED_STATUSES.has(status);
        
        // Disable drag and drop if locked
        if (isLocked) {
            this.disableMapping();
        } else {
            this.enableMapping();
        }
        
        // Update submit mapping button
        if (this.elements.submitMappingBtn) {
            this.elements.submitMappingBtn.disabled = isLocked;
            if (isLocked) {
                this.elements.submitMappingBtn.textContent = 'Locked — Pending Review';
                this.elements.submitMappingBtn.disabled = true;
            } else {
                this.updateSubmitButton();
            }
        }
    }

    disableMapping() {
        // Disable drag and drop
        this.state.isDragging = false;
        
        // Add visual indication that mapping is locked
        if (this.elements.unmappedAccountsList) {
            this.elements.unmappedAccountsList.classList.add('mapping-locked');
        }
        
        if (this.elements.grapCategories) {
            this.elements.grapCategories.classList.add('mapping-locked');
        }

        ['grap24VarianceMount', 'grap24BudgetTableMount', 'grapSubmitComplianceMount'].forEach((id) => {
            const el = document.getElementById(id);
            if (el) el.classList.add('mapping-locked');
        });
        void this.lockGrapSubmitPanelsReadOnly();
    }

    lockGrapSubmitPanelsReadOnly() {
        const varianceMount = document.getElementById('grap24VarianceMount');
        if (
            !varianceMount
            || this.state.documentType !== 'budget_report'
            || !this.state.budgetRows
            || !window.BudgetVarianceGrap24
        ) {
            return;
        }
        varianceMount.innerHTML = BudgetVarianceGrap24.renderVariancePanel(
            this.state.budgetRows,
            this.state.varianceExplanations || {},
            { readOnly: true }
        );
    }

    enableMapping() {
        // Enable drag and drop
        if (this.elements.unmappedAccountsList) {
            this.elements.unmappedAccountsList.classList.remove('mapping-locked');
        }
        
        if (this.elements.grapCategories) {
            this.elements.grapCategories.classList.remove('mapping-locked');
        }

        ['grap24VarianceMount', 'grap24BudgetTableMount', 'grapSubmitComplianceMount'].forEach((id) => {
            const el = document.getElementById(id);
            if (el) el.classList.remove('mapping-locked');
        });
    }

    accountDedupeKey(account) {
        const code = String(account.account_code || account.code || '').trim();
        if (code) return `code:${code}`;
        const name = String(account.account_desc || account.name || '').trim().toLowerCase();
        return name ? `name:${name}` : `id:${account.id || ''}`;
    }

    /** Full trial balance for GRAP equation checks (mapped + unmapped, no duplicates). */
    getTrialBalanceRowsForValidation() {
        const seen = new Set();
        const rows = [];

        const pushRow = (account, categoryCode) => {
            const row =
                categoryCode != null && categoryCode !== ''
                    ? this.normalizeMappedRowForSubmit(account, categoryCode)
                    : this.normalizeMappedRowForSubmit(
                          { ...account, grap_code: '', grap_category: '' },
                          ''
                      );
            const key = this.accountDedupeKey(row);
            if (seen.has(key)) return;
            seen.add(key);
            rows.push(row);
        };

        Object.entries(this.state.mappedAccounts).forEach(([categoryCode, accounts]) => {
            (accounts || []).forEach((account) => pushRow(account, categoryCode));
        });

        this.state.unmappedAccounts.forEach((account) => pushRow(account, null));

        this.state.autoMappedAccounts.forEach((account) => {
            const cat = account.grap_code || '';
            if (cat && this.state.mappedAccounts[cat]) return;
            pushRow(account, cat || null);
        });

        return rows;
    }

    getMappedDataForSubmission() {
        const mappedData = [];
        const seen = new Set();

        const pushMapped = (account, categoryCode) => {
            const row = this.normalizeMappedRowForSubmit(account, categoryCode);
            const key = this.accountDedupeKey(row);
            if (seen.has(key)) return;
            seen.add(key);
            mappedData.push(row);
        };

        Object.entries(this.state.mappedAccounts).forEach(([categoryCode, accounts]) => {
            (accounts || []).forEach((account) => pushMapped(account, categoryCode));
        });

        this.state.autoMappedAccounts.forEach((account) => {
            const cat = account.grap_code || '';
            if (!cat || this.state.mappedAccounts[cat]) return;
            pushMapped(account, cat);
        });

        return mappedData;
    }

    resolveAccountBalance(account) {
        if (account == null) return 0;
        const net = account.net_balance ?? account.amount ?? account.balance;
        if (net != null && net !== '' && !Number.isNaN(Number(net))) {
            return Number(net);
        }
        const dr = Number(account.debit_balance ?? account.debit ?? 0) || 0;
        const cr = Number(account.credit_balance ?? account.credit ?? 0) || 0;
        if (dr !== 0 || cr !== 0) {
            return dr - cr;
        }
        return 0;
    }

    normalizeMappedRowForSubmit(account, categoryCode) {
        const name = account.account_desc || account.name || account.description || '';
        const code = account.account_code || account.code || '';
        const balance = this.resolveAccountBalance(account);
        return {
            ...account,
            account_name: account.account_name || name,
            account_desc: account.account_desc || name,
            account_code: code,
            name,
            code,
            net_balance: balance,
            amount: account.amount ?? balance,
            grap_code: categoryCode,
            grap_category: this.getGRAPCategoryName(categoryCode),
            confidence: account.confidence != null ? account.confidence : 1.0,
        };
    }
    
    getGRAPCategoryName(categoryCode) {
        const category = this.state.grapCategories.find(cat => cat.code === categoryCode);
        return category ? category.name : categoryCode;
    }

    editMapping() {
        // Enable editing for rejected submissions
        this.updateSubmissionUI('draft');
        this.showSuccess('You can now edit your mapping and resubmit.');
    }

    editAccountMapping(accountIndex) {
        // Move an auto-mapped account back to unmapped for manual mapping
        const account = this.state.autoMappedAccounts[accountIndex];
        if (!account) return;

        // Remove from auto-mapped accounts
        this.state.autoMappedAccounts.splice(accountIndex, 1);
        
        // Add to unmapped accounts
        this.state.unmappedAccounts.push(account);
        
        // Re-render both sections
        this.renderAutoMappedAccounts();
        this.renderUnmappedAccounts();
        this.updateStats();
        this.updateConfidenceSummary();
        this.updateReviewStatus();
        
        this.showSuccess(`Account "${account.name}" moved to manual mapping`);
    }

    async saveMappingProgress() {
        this.showError(
            'Draft save is not available. Complete mapping and use Submit for Review.'
        );
    }

    startStatusPolling() {
        if (!this.state.submissionId) return;
        
        // Poll every 30 seconds for status updates
        this.statusPollingInterval = setInterval(async () => {
            try {
                const response = await fetch(`/api/submission-status/${this.state.submissionId}`);
                const result = await response.json();
                
                if (result.success && result.status !== this.state.currentStatus) {
                    this.state.currentStatus = result.status;
                    this.updateSubmissionUI(result.status);
                    
                    if (result.status === 'approved') {
                        this.showSuccess('Your balance sheet has been approved! 🎉');
                        clearInterval(this.statusPollingInterval);
                    } else if (result.status === 'rejected') {
                        this.showError('Your balance sheet was rejected. Please review the feedback.');
                    }
                }
            } catch (error) {
                // Status polling error
            }
        }, 30000);
    }

    updateProgress() {
        // Legacy alias — keep callers in sync with mapping progress + section badges
        this.updateStats();
    }

    updateConfidenceSummary() {
        if (!this.elements.confidenceSummary) return;

        const autoMappedAccounts = this.state.autoMappedAccounts;
        if (autoMappedAccounts.length === 0) {
            this.elements.confidenceSummary.innerHTML = `
                <div class="confidence-empty">
                    <p>No auto-mapped accounts to analyze</p>
                </div>
            `;
            return;
        }

        // Calculate confidence breakdown
        let highConfidence = 0;
        let mediumConfidence = 0;
        let lowConfidence = 0;
        let totalConfidence = 0;

        autoMappedAccounts.forEach(account => {
            const confidence = account.confidence || 0;
            totalConfidence += confidence;
            
            if (confidence >= 0.8) {
                highConfidence++;
            } else if (confidence >= 0.5) {
                mediumConfidence++;
            } else {
                lowConfidence++;
            }
        });

        const avgConfidence = totalConfidence / autoMappedAccounts.length;

        // Update UI elements
        if (this.elements.avgConfidence) {
            this.elements.avgConfidence.textContent = `${Math.round(avgConfidence * 100)}%`;
        }
        
        if (this.elements.highConfidenceCount) {
            this.elements.highConfidenceCount.textContent = highConfidence;
        }
        
        if (this.elements.mediumConfidenceCount) {
            this.elements.mediumConfidenceCount.textContent = mediumConfidence;
        }
        
        if (this.elements.lowConfidenceCount) {
            this.elements.lowConfidenceCount.textContent = lowConfidence;
        }

        // Show/hide warnings based on confidence levels
        this.updateReviewWarnings(avgConfidence, lowConfidence);
    }

    updateReviewWarnings(avgConfidence, lowConfidenceCount) {
        if (!this.elements.reviewWarnings) return;

        let warnings = [];

        if (avgConfidence < 0.7) {
            warnings.push('Overall mapping confidence is below 70%. Manual review recommended.');
        }

        if (lowConfidenceCount > 0) {
            warnings.push(`${lowConfidenceCount} account(s) have low confidence mapping and should be reviewed manually.`);
        }

        if (this.state.unmappedAccounts.length > 0) {
            warnings.push(`${this.state.unmappedAccounts.length} account(s) require manual mapping.`);
        }

        if (warnings.length === 0) {
            this.elements.reviewWarnings.innerHTML = `
                <div class="warning-success">
                    ✅ All mappings look good! Ready for submission.
                </div>
            `;
        } else {
            this.elements.reviewWarnings.innerHTML = warnings.map(warning => `
                <div class="warning-item">
                    ⚠️ ${warning}
                </div>
            `).join('');
        }
    }

    updateReviewStatus() {
        // Update submit button state based on confidence and completion
        const submitBtn = this.elements.submitMappingBtn;
        if (!submitBtn) return;

        const hasUnmappedAccounts = this.state.unmappedAccounts.length > 0;
        const autoMappedAccounts = this.state.autoMappedAccounts;
        
        // Calculate average confidence
        let avgConfidence = 0;
        if (autoMappedAccounts.length > 0) {
            const totalConfidence = autoMappedAccounts.reduce((sum, account) => sum + (account.confidence || 0), 0);
            avgConfidence = totalConfidence / autoMappedAccounts.length;
        }

        // Enable submit if no unmapped accounts and confidence is acceptable
        const canSubmit = !hasUnmappedAccounts && avgConfidence >= 0.5;
        
        submitBtn.disabled = !canSubmit;
        
        if (hasUnmappedAccounts) {
            submitBtn.textContent = '📋 Complete Mapping First';
        } else if (avgConfidence < 0.5) {
            submitBtn.textContent = '📋 Low Confidence - Review Required';
        } else {
            submitBtn.textContent = '📋 Submit for Manager Review';
        }
    }

    // Show submission status when mapping is complete
    checkMappingCompletion() {
        const remainingCount = this.state.unmappedAccounts.length;
        
        if (remainingCount === 0 && !this.state.submissionShown) {
            this.state.submissionShown = true;
            this.showSubmissionStatus('draft');
        }
    }
}

const MAPPING_TOUCH_STYLES = `
    @keyframes touchPulse {
        0%, 100% { transform: translate(-50%, -50%) scale(1); }
        50% { transform: translate(-50%, -50%) scale(1.1); }
    }
    .touch-feedback { animation: touchPulse 0.6s ease-in-out infinite; }
    .drag-ghost { transition: none !important; }
`;
if (!document.getElementById('mapping-touch-styles')) {
    const styleSheet = document.createElement('style');
    styleSheet.id = 'mapping-touch-styles';
    styleSheet.textContent = MAPPING_TOUCH_STYLES;
    document.head.appendChild(styleSheet);
}

function normalizeMappingSessionId(raw) {
    const s = String(raw == null ? '' : raw).trim();
    if (!s || s === 'None' || s === 'null' || s === 'undefined') return '';
    return s;
}

function showMappingSessionRequired() {
    const container = document.querySelector('.mapping-container');
    if (!container || document.getElementById('mappingSessionRequired')) return;
    const banner = document.createElement('div');
    banner.id = 'mappingSessionRequired';
    banner.className = 'alert alert-warning mapping-session-required';
    banner.setAttribute('role', 'alert');
    banner.innerHTML =
        '<p><strong>No session selected.</strong> Open a returned submission from your ' +
        '<a href="/inbox">Inbox</a> or <a href="/submission-history">Submission history</a>, ' +
        'or upload a new file from <a href="/upload">Upload</a>.</p>';
    container.prepend(banner);
}

function initMappingInterface() {
    const urlParams = new URLSearchParams(window.location.search);
    const sessionId = normalizeMappingSessionId(urlParams.get('session_id') || window.sessionId);
    if (!sessionId) {
        showMappingSessionRequired();
        return;
    }
    window.sessionId = sessionId;
    window.mappingInterface = new GRAPMappingInterface(sessionId);
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initMappingInterface);
} else {
    initMappingInterface();
}

