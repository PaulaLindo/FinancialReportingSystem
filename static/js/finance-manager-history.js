/**
 * Finance Manager / CFO history — financial submissions and asset journals.
 */
(function () {
    const HISTORY_PATH = '/finance-manager/history';
    const RETURN_TO = '/finance-manager/history';

    const FILTER_OPTIONS = {
        CFO: [
            { value: 'all', label: 'All' },
            { value: 'approved', label: 'Approved' },
            { value: 'rejected', label: 'Rejected' },
        ],
        FINANCE_MANAGER: [
            { value: 'all', label: 'All' },
            { value: 'approved', label: 'Approved' },
            { value: 'rejected', label: 'Rejected' },
        ],
    };

    function escapeHtml(text) {
        if (window.TransactionCardUI && TransactionCardUI.escapeHtml) {
            return TransactionCardUI.escapeHtml(text);
        }
        const div = document.createElement('div');
        div.textContent = text == null ? '' : String(text);
        return div.innerHTML;
    }

    function formatMoney(n) {
        const v = Number(n) || 0;
        return `R ${v.toLocaleString('en-ZA', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    }

    function journalTypeLabel(t) {
        if (t === 'useful_life_review') return 'Useful life review';
        if (t === 'impairment') return 'Impairment';
        return (t || 'Journal').replace(/_/g, ' ');
    }

    class FinanceManagerHistory {
        constructor() {
            if (!this.isHistoryPage()) return;
            this.role = window.currentUserRole || '';
            this.recordType = 'submissions';
            this.items = [];
            this.filtered = [];
            this.searchQuery = '';
            this.init();
        }

        isHistoryPage() {
            const p = window.location.pathname;
            return p === HISTORY_PATH || p.endsWith(HISTORY_PATH);
        }

        populateStatusFilter() {
            const select = document.getElementById('fmHistoryStatusFilter');
            if (!select) return;
            const roleKey = this.role === 'CFO' ? 'CFO' : 'FINANCE_MANAGER';
            const options = FILTER_OPTIONS[roleKey] || FILTER_OPTIONS.FINANCE_MANAGER;
            select.innerHTML = options
                .map((o) => `<option value="${escapeHtml(o.value)}">${escapeHtml(o.label)}</option>`)
                .join('');
        }

        init() {
            const container = document.getElementById('fmHistoryContainer');
            TransactionCardUI.mountTransactionListActions(container, { returnTo: RETURN_TO });

            this.populateStatusFilter();

            document.querySelector('[data-action="refresh-fm-history"]')?.addEventListener('click', () => this.load());
            document.getElementById('fmHistoryRecordTypeFilter')?.addEventListener('change', (e) => {
                this.recordType = e.target.value || 'submissions';
                this.load();
            });
            document.getElementById('fmHistoryStatusFilter')?.addEventListener('change', () => this.load());
            document.getElementById('fmHistorySearchInput')?.addEventListener('input', (e) => {
                this.searchQuery = (e.target.value || '').toLowerCase().trim();
                this.applySearchAndRender();
            });
            this.load();
        }

        async load() {
            const container = document.getElementById('fmHistoryContainer');
            if (!container) return;

            const recordTypeEl = document.getElementById('fmHistoryRecordTypeFilter');
            this.recordType = recordTypeEl?.value || 'submissions';

            container.innerHTML = `
                <div class="queue-loading">
                    <div class="loading-spinner"></div>
                    <p>Loading history…</p>
                </div>`;

            try {
                const statusEl = document.getElementById('fmHistoryStatusFilter');
                const statusFilter = (statusEl?.value ?? 'all').trim();

                if (this.recordType === 'asset_journals') {
                    const params = new URLSearchParams();
                    if (statusFilter && statusFilter !== 'all') {
                        params.append('status', statusFilter);
                    }
                    const response = await fetch(`/api/asset-journals/history?${params}`, { credentials: 'same-origin' });
                    const result = await response.json();
                    if (!result.success) throw new Error(result.error || 'Failed to load asset journal history');
                    this.items = result.journals || [];
                } else {
                    const params = new URLSearchParams();
                    params.append('limit', '100');
                    if (statusFilter && statusFilter !== 'all') {
                        params.append('status', statusFilter);
                    }
                    const response = await fetch(`/api/transactions/history?${params}`, { credentials: 'same-origin' });
                    const result = await response.json();
                    if (!result.success) throw new Error(result.error || 'Failed to load history');
                    this.items = result.transactions || [];
                }
                this.applySearchAndRender();
            } catch (err) {
                container.innerHTML = `
                    <div class="approval-empty-state">
                        <div class="approval-empty-icon">⚠️</div>
                        <h3>Could not load history</h3>
                        <p>${escapeHtml(err.message)}</p>
                    </div>`;
            }
        }

        applySearchAndRender() {
            if (!this.searchQuery) {
                this.filtered = this.items;
            } else {
                const q = this.searchQuery;
                if (this.recordType === 'asset_journals') {
                    this.filtered = this.items.filter((j) => {
                        const blob = [
                            j.journal_id,
                            j.asset_id,
                            j.asset_name,
                            j.description,
                            j.reason,
                            j.rejection_reason,
                            j.submitter_name,
                            j.reviewer_name,
                            j.journal_type,
                            j.status,
                        ].join(' ').toLowerCase();
                        return blob.includes(q);
                    });
                } else {
                    this.filtered = this.items.filter((tx) => {
                        const blob = [
                            tx.transaction_id,
                            tx.creator_name,
                            tx.reason,
                            tx.transaction_type,
                            tx.status,
                        ].join(' ').toLowerCase();
                        return blob.includes(q);
                    });
                }
            }
            this.render();
        }

        renderAssetJournalHistory() {
            const container = document.getElementById('fmHistoryContainer');
            if (!this.filtered.length) {
                container.innerHTML = `
                    <div class="approval-empty-state">
                        <div class="approval-empty-icon">📚</div>
                        <h3>No asset journal records</h3>
                        <p>No approve/reject decisions match the current filter.</p>
                    </div>`;
                return;
            }

            container.innerHTML = `<div class="asset-journals-list asset-journals-list--fm asset-journals-list--history">${this.filtered.map((j) => {
                const status = j.status || '';
                const reviewed = (j.reviewed_at || '').slice(0, 10);
                return `
                <article class="asset-journal-card asset-journal-card--${escapeHtml(status)}">
                    <div class="asset-journal-card__head">
                        <span class="asset-journal-type">${escapeHtml(journalTypeLabel(j.journal_type))}</span>
                        <span class="asset-journal-status status-${escapeHtml(status)}">${escapeHtml(status.replace(/_/g, ' '))}</span>
                    </div>
                    <h3>${escapeHtml(j.asset_name || j.asset_id)}</h3>
                    <p>${escapeHtml(j.description || '')}</p>
                    ${j.amount ? `<p><strong>${formatMoney(j.amount)}</strong></p>` : ''}
                    <p class="text-muted">Submitted by ${escapeHtml(j.submitter_name || 'Asset Manager')} · ${escapeHtml((j.submitted_at || '').slice(0, 10))}</p>
                    <p class="asset-journal-reason"><strong>Asset Manager reason:</strong> ${escapeHtml(j.reason || '—')}</p>
                    ${status === 'approved' && reviewed ? `<p class="asset-journal-outcome asset-journal-outcome--approved">You approved on ${escapeHtml(reviewed)}${j.reviewer_name ? ` (${escapeHtml(j.reviewer_name)})` : ''}</p>` : ''}
                    ${status === 'rejected' ? `<p class="asset-journal-outcome asset-journal-outcome--rejected">Rejected on ${escapeHtml(reviewed || '—')}${j.reviewer_name ? ` by ${escapeHtml(j.reviewer_name)}` : ''}</p>` : ''}
                    ${j.rejection_reason ? `<p class="asset-journal-rejection"><strong>Rejection reason:</strong> ${escapeHtml(j.rejection_reason)}</p>` : ''}
                    <p class="asset-journal-history-meta text-muted">${escapeHtml(j.journal_id)} · ${escapeHtml(j.asset_id)}</p>
                </article>`;
            }).join('')}</div>`;
        }

        render() {
            const container = document.getElementById('fmHistoryContainer');
            if (!container) return;

            if (this.recordType === 'asset_journals') {
                this.renderAssetJournalHistory();
                return;
            }

            if (!this.filtered.length) {
                container.innerHTML = `
                    <div class="approval-empty-state">
                        <div class="approval-empty-icon">📚</div>
                        <h3>No records</h3>
                        <p>No submissions match the current filter.</p>
                    </div>`;
                return;
            }

            container.innerHTML = TransactionCardUI.renderTransactionList(this.filtered, {
                variant: 'history',
                returnTo: RETURN_TO,
                reviewLabel: 'View Details',
            });
        }
    }

    document.addEventListener('DOMContentLoaded', () => {
        const role = window.currentUserRole || '';
        if (role === 'FINANCE_MANAGER' || role === 'CFO') {
            window.financeManagerHistory = new FinanceManagerHistory();
        }
    });
})();
