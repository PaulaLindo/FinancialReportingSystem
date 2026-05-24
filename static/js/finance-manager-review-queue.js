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
            listEl?.addEventListener('change', (e) => {
                if (e.target.classList.contains('transaction-select-cb')) {
                    this.updateBatchBar();
                }
            });
            this.bindBatchBar();
            this.loadQueue();
            this.bindRefreshOnReturn();
        }

        bindBatchBar() {
            if (this.role !== 'CFO') return;
            document.getElementById('reviewQueueSelectAllBtn')?.addEventListener('click', () => {
                document.querySelectorAll('#fmReviewQueueList .transaction-select-cb').forEach((cb) => {
                    cb.checked = true;
                });
                this.updateBatchBar();
            });
            document.getElementById('reviewQueueClearSelectionBtn')?.addEventListener('click', () => {
                document.querySelectorAll('#fmReviewQueueList .transaction-select-cb').forEach((cb) => {
                    cb.checked = false;
                });
                this.updateBatchBar();
            });
            document.getElementById('reviewQueueBatchFinalizeBtn')?.addEventListener('click', () => {
                this.batchFinalizeSelected();
            });
        }

        getSelectedItems() {
            const selected = [];
            document.querySelectorAll('#fmReviewQueueList .transaction-select-cb:checked').forEach((cb) => {
                const sessionId = cb.dataset.sessionId;
                const docType = cb.dataset.transactionType;
                if (sessionId && docType) {
                    selected.push({ session_id: sessionId, document_type: docType });
                }
            });
            return selected;
        }

        updateBatchBar() {
            const bar = document.getElementById('reviewQueueBatchBar');
            const countEl = document.getElementById('reviewQueueBatchCount');
            const finalizeBtn = document.getElementById('reviewQueueBatchFinalizeBtn');
            if (!bar || this.role !== 'CFO') return;

            const count = this.getSelectedItems().length;
            if (this.items.length) {
                VarydianUtils.showElement(bar);
            } else {
                VarydianUtils.hideElement(bar);
            }
            if (countEl) countEl.textContent = `${count} selected`;
            if (finalizeBtn) finalizeBtn.disabled = count === 0;
        }

        async batchFinalizeSelected() {
            const items = this.getSelectedItems();
            if (!items.length) return;

            const confirmed = await (window.varydianCfoFinalizeConfirm
                ? window.varydianCfoFinalizeConfirm({ count: items.length })
                : window.varydianAppConfirm
                ? window.varydianAppConfirm(
                    'Finalize selected submissions',
                    `This action will final-approve ${items.length} submission(s), lock each reporting period, and is irreversible without an audit log entry. An audit trail record is written for each finalization. Continue?`,
                    { confirmText: 'Finalize all and lock', cancelText: 'Cancel' }
                )
                : Promise.resolve(window.confirm(`Finalize ${items.length} submission(s)?`)));
            if (!confirmed) return;

            const btn = document.getElementById('reviewQueueBatchFinalizeBtn');
            VarydianUtils.setButtonBusy(btn, true, 'Finalizing…');
            try {
                const response = await fetch('/api/universal/batch-approve', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    credentials: 'same-origin',
                    body: JSON.stringify({ items, notes: 'Batch finalization from review queue' }),
                });
                const result = await response.json();
                if (result.success) {
                    const msg = `Finalized ${result.approved_count || items.length} of ${result.total || items.length} submission(s).`;
                    if (window.modalSystem?.alert) {
                        await window.modalSystem.alert('Batch finalization complete', msg);
                    } else if (window.VarydianUtils?.showToast) {
                        VarydianUtils.showToast(msg, 'success');
                    }
                    await this.loadQueue();
                } else if (result.partial) {
                    const msg = `Partial success: ${result.approved_count || 0} of ${result.total || items.length} finalized. Check individual errors in the response.`;
                    if (window.modalSystem?.alert) {
                        await window.modalSystem.alert('Batch finalization partial', msg);
                    }
                    await this.loadQueue();
                } else {
                    const detail = result.error || 'Batch finalization failed';
                    if (window.modalSystem?.alert) {
                        await window.modalSystem.alert('Batch finalization failed', detail);
                    }
                }
            } catch (err) {
                if (window.modalSystem?.alert) {
                    await window.modalSystem.alert('Batch finalization failed', err.message || 'Network error');
                }
            } finally {
                VarydianUtils.clearButtonBusy(btn);
            }
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
            if (this.role === 'CFO') {
                const confirmed = window.varydianCfoFinalizeConfirm
                    ? await window.varydianCfoFinalizeConfirm({ count: 1 })
                    : true;
                if (!confirmed) return;
            }
            let notesFromPanel = '';
            try {
                const ta = document.querySelector('#statementReviewPanel:not(.element--hidden) #reviewComment');
                notesFromPanel = ta && ta.value ? String(ta.value).trim() : '';
            } catch (_) {}
            VarydianUtils.setButtonBusy(btn, true, this.role === 'CFO' ? 'Finalizing…' : 'Approving…');
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
                    const successMsg = result.message || 'Action completed successfully.';
                    if (window.modalSystem && window.modalSystem.alert) {
                        await window.modalSystem.alert('Success', successMsg);
                    } else if (window.VarydianUtils && VarydianUtils.showToast) {
                        VarydianUtils.showToast(successMsg, 'success');
                    }
                } else {
                    const detail = result.error || 'Action failed';
                    if (window.modalSystem && window.modalSystem.alert) {
                        await window.modalSystem.alert('Action failed', detail);
                    } else if (window.VarydianUtils && VarydianUtils.showToast) {
                        VarydianUtils.showToast(detail, 'error');
                    }
                }
            } catch (err) {
                const msg = err.message || 'Network error';
                if (window.modalSystem && window.modalSystem.alert) {
                    await window.modalSystem.alert('Action failed', msg);
                } else if (window.VarydianUtils && VarydianUtils.showToast) {
                    VarydianUtils.showToast(msg, 'error');
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
                this.updateBatchBar();
            } catch (err) {
                if (countEl) countEl.textContent = '—';
                container.innerHTML = `
                    <div class="approval-empty-state">
                        <div class="approval-empty-icon">⚠️</div>
                        <h3>Could not load queue</h3>
                        <p>${TransactionCardUI.escapeHtml(err.message)}</p>
                    </div>`;
                this.updateBatchBar();
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

            const isCfo = this.role === 'CFO';
            container.innerHTML = TransactionCardUI.renderTransactionList(this.items, {
                variant: 'pending',
                showApproveReject: isCfo,
                selectable: isCfo,
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

