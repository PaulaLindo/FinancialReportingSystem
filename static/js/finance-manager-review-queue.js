/**
 * Finance Manager / CFO review — pending list filtered by role on the server payload.
 */
(function () {
    const RETURN_TO = '/finance-manager/review-queue';

    function pendingMatchesRole(tx, role) {
        const st = (tx.status || '').toLowerCase();
        if (role === 'CFO') {
            return st === 'pending_cfo' || st === 'approved_by_manager';
        }
        return st === 'pending_review';
    }

    function emptyCopy(role) {
        if (role === 'CFO') {
            return {
                title: 'No submissions awaiting CFO action',
                body: 'Items approved by the Finance Manager appear here when awaiting CFO approval.',
            };
        }
        return {
            title: 'No submissions pending review',
            body: 'Clerk submissions appear here after submit for review.',
        };
    }

    class FinanceManagerReviewQueue {
        constructor() {
            if (!window.location.pathname.includes('/finance-manager/review-queue')) {
                return;
            }
            this.role = window.currentUserRole || '';
            this.items = [];
            this._reviewPanelOpen = false;
            this._refreshTimer = null;
            this._lastHidden =
                typeof document.visibilityState === 'string'
                    ? document.visibilityState === 'hidden'
                    : false;
            this.init();
        }

        init() {
            this.resetPageLayout();
            document.getElementById('fmReviewQueueBackBtn')?.addEventListener('click', (e) => {
                e.preventDefault();
                this.hideReviewPanel();
            });
            const listEl = document.getElementById('fmReviewQueueList');
            TransactionCardUI.mountTransactionListActions(listEl, {
                returnTo: RETURN_TO,
                onView: (sessionId, docType) => this.openReview(sessionId, docType),
                onApprove: (btn) => this.quickAction('approve', btn),
                onReject: (btn) => this.quickAction('reject', btn),
            });
            this.loadQueue();
            this.bindRefreshOnReturn();
        }

        bindRefreshOnReturn() {
            document.addEventListener('visibilitychange', () => {
                if (document.visibilityState === 'hidden') {
                    this._lastHidden = true;
                    return;
                }
                if (document.visibilityState === 'visible' && this._lastHidden) {
                    this._lastHidden = false;
                    this.scheduleQueueRefresh();
                }
            });
            window.addEventListener('pageshow', (ev) => {
                if (ev.persisted) {
                    if (!this._reviewPanelOpen) {
                        this.resetPageLayout();
                    }
                    this.scheduleQueueRefresh();
                }
            });
        }

        resetPageLayout() {
            const hero = document.querySelector('.fm-review-queue-section');
            const panel = document.getElementById('statementReviewPanel');
            this._reviewPanelOpen = false;
            VarydianUtils.showElement(hero);
            VarydianUtils.hideElement(panel);
        }

        scheduleQueueRefresh() {
            if (this._refreshTimer !== null) {
                clearTimeout(this._refreshTimer);
            }
            this._refreshTimer = window.setTimeout(() => {
                this._refreshTimer = null;
                this.loadQueue();
            }, 150);
        }

        async quickAction(action, btn) {
            const sessionId = btn.dataset.sessionId;
            const docType = btn.dataset.transactionType;
            if (!sessionId || !docType) return;

            if (action === 'reject') {
                const reasonFn = window.varydianMandatoryRejectionReason;
                const reason =
                    typeof reasonFn === 'function' ? await reasonFn() : window.prompt('Rejection reason (required):');
                if (!reason || !String(reason).trim()) return;
                VarydianUtils.setButtonBusy(btn, true, 'Rejecting…');
                try {
                    await this.postAction('/api/universal/reject', {
                        document_type: docType,
                        session_id: sessionId,
                        reason: String(reason).trim(),
                    });
                } finally {
                    VarydianUtils.clearButtonBusy(btn);
                }
                return;
            }
            let notesFromPanel = '';
            try {
                const ta = document.querySelector('#statementReviewPanel:not(.element--hidden) #reviewComment');
                notesFromPanel = ta && ta.value ? String(ta.value).trim() : '';
            } catch (_) {}
            VarydianUtils.setButtonBusy(btn, true, 'Approving…');
            try {
                await this.postAction('/api/universal/approve', {
                    document_type: docType,
                    session_id: sessionId,
                    notes: notesFromPanel,
                });
            } finally {
                VarydianUtils.clearButtonBusy(btn);
            }
        }

        async postAction(url, body) {
            try {
                const response = await fetch(url, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    credentials: 'same-origin',
                    body: JSON.stringify(body),
                });
                const result = await response.json();
                if (result.success) {
                    await this.loadQueue();
                    if (window.modalSystem && window.modalSystem.alert) {
                        await window.modalSystem.alert(
                            'Success',
                            result.message || 'Action completed successfully.'
                        );
                    }
                } else {
                    const detail = result.error || 'Action failed';
                    if (window.modalSystem && window.modalSystem.alert) {
                        await window.modalSystem.alert('Action failed', detail);
                    } else {
                        alert(detail);
                    }
                }
            } catch (err) {
                const msg = err.message || 'Network error';
                if (window.modalSystem && window.modalSystem.alert) {
                    await window.modalSystem.alert('Action failed', msg);
                } else {
                    alert(msg);
                }
            }
        }

        async loadQueue() {
            const container = document.getElementById('fmReviewQueueList');
            const countEl = document.getElementById('reviewQueueCount');
            if (!container) return;

            try {
                const response = await fetch('/api/transactions/pending?limit=200', { credentials: 'same-origin' });
                const result = await response.json();
                if (!result.success) {
                    throw new Error(result.error || 'Failed to load queue');
                }
                const pending = result.pending_transactions || [];
                this.items = pending.filter((tx) => pendingMatchesRole(tx, this.role));
                if (countEl) countEl.textContent = String(this.items.length);
                this.renderQueue(container);
            } catch (err) {
                if (countEl) countEl.textContent = '—';
                container.innerHTML = `
                    <div class="approval-empty-state">
                        <div class="approval-empty-icon">⚠️</div>
                        <h3>Could not load queue</h3>
                        <p>${TransactionCardUI.escapeHtml(err.message)}</p>
                    </div>`;
            }
        }

        renderQueue(container) {
            const copy = emptyCopy(this.role);
            if (!this.items.length) {
                container.innerHTML = `
                    <div class="approval-empty-state">
                        <div class="approval-empty-icon">✓</div>
                        <h3>${TransactionCardUI.escapeHtml(copy.title)}</h3>
                        <p>${TransactionCardUI.escapeHtml(copy.body)}</p>
                    </div>`;
                return;
            }

            container.innerHTML = TransactionCardUI.renderTransactionList(this.items, {
                variant: 'pending',
                showApproveReject: true,
                returnTo: RETURN_TO,
            });
        }

        openReview(sessionId, documentType) {
            const hero = document.querySelector('.fm-review-queue-section');
            const panel = document.getElementById('statementReviewPanel');
            this._reviewPanelOpen = true;
            VarydianUtils.hideElement(hero);
            VarydianUtils.showElement(panel);

            if (window.financialStatementReview) {
                window.financialStatementReview._returnToReviewQueue = true;
                window.financialStatementReview._returnToUrl = RETURN_TO;
                window.financialStatementReview.loadStatementForReview(sessionId, documentType);
                return;
            }
            TransactionCardUI.openStatementReview(sessionId, documentType, RETURN_TO);
        }

        hideReviewPanel() {
            this._reviewPanelOpen = false;
            const content = document.getElementById('statementReviewContent');
            if (content) content.innerHTML = '';
            this.resetPageLayout();
            if (window.financialStatementReview) {
                window.financialStatementReview._returnToReviewQueue = false;
            }
            const url = new URL(window.location.href);
            if (url.searchParams.has('review') || url.searchParams.has('transaction')) {
                url.searchParams.delete('review');
                url.searchParams.delete('transaction');
                url.searchParams.delete('type');
                url.searchParams.delete('returnTo');
                window.history.replaceState({}, '', url.pathname + (url.search || ''));
            }
            this.loadQueue();
        }
    }

    document.addEventListener('DOMContentLoaded', () => {
        window.financeManagerReviewQueue = new FinanceManagerReviewQueue();
    });
})();
