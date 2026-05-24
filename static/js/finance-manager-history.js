/**
 * Finance Manager / CFO submission history (settled decisions only — no pending).
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

    class FinanceManagerHistory {
        constructor() {
            if (!this.isHistoryPage()) return;
            this.role = window.currentUserRole || '';
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
                .map((o) => `<option value="${TransactionCardUI.escapeHtml(o.value)}">${TransactionCardUI.escapeHtml(o.label)}</option>`)
                .join('');
        }

        init() {
            const container = document.getElementById('fmHistoryContainer');
            TransactionCardUI.mountTransactionListActions(container, { returnTo: RETURN_TO });

            this.populateStatusFilter();

            document.querySelector('[data-action="refresh-fm-history"]')?.addEventListener('click', () => this.load());
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

            try {
                const statusEl = document.getElementById('fmHistoryStatusFilter');
                const statusFilter = (statusEl?.value ?? '').trim();
                const params = new URLSearchParams();
                params.append('limit', '100');
                if (statusFilter && statusFilter !== 'all') {
                    params.append('status', statusFilter);
                }

                const response = await fetch(`/api/transactions/history?${params}`, { credentials: 'same-origin' });
                const result = await response.json();
                if (!result.success) {
                    throw new Error(result.error || 'Failed to load history');
                }
                this.items = result.transactions || [];
                this.applySearchAndRender();
            } catch (err) {
                container.innerHTML = `
                    <div class="approval-empty-state">
                        <div class="approval-empty-icon">⚠️</div>
                        <h3>Could not load history</h3>
                        <p>${TransactionCardUI.escapeHtml(err.message)}</p>
                    </div>`;
            }
        }

        applySearchAndRender() {
            if (!this.searchQuery) {
                this.filtered = this.items;
            } else {
                const q = this.searchQuery;
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
            const countEl = document.getElementById('fmHistoryTotalCount');
            if (countEl) countEl.textContent = String(this.filtered.length);
            this.render();
        }

        render() {
            const container = document.getElementById('fmHistoryContainer');
            if (!container) return;

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
