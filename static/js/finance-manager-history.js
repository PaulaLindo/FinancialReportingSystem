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
        if (t === 'disposal') return 'Disposal';
        return (t || 'Journal').replace(/_/g, ' ');
    }

    const VALID_JOURNAL_TYPES = new Set(['useful_life_review', 'impairment', 'disposal']);

    function isAssetJournalRecord(j) {
        return !!(j && j.journal_id && VALID_JOURNAL_TYPES.has(j.journal_type));
    }

    function journalStatusLabel(j, userRole) {
        const status = j.status || '';
        if (status === 'approved') {
            if (j.metadata?.cfo_final_approval || j.metadata?.fm_forward) {
                return 'Approved · CFO final';
            }
            return 'Approved · FM';
        }
        if (status === 'rejected') {
            const reviewer = j.reviewer_name || '';
            return reviewer ? `Rejected · ${reviewer}` : 'Rejected';
        }
        return status.replace(/_/g, ' ');
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
                    this.items = (result.journals || []).filter(isAssetJournalRecord);
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
                const submitted = (j.submitted_at || '').slice(0, 10);
                const statusClass = status === 'approved' ? 'approved' : status === 'rejected' ? 'rejected' : status;
                return `
                <article class="asset-journal-card asset-journal-card--${escapeHtml(statusClass)}">
                    <div class="asset-journal-card__head">
                        <span class="asset-journal-type">${escapeHtml(journalTypeLabel(j.journal_type))}</span>
                        <span class="asset-journal-status status-${escapeHtml(statusClass)}">${escapeHtml(journalStatusLabel(j, this.role))}</span>
                    </div>
                    <h3>${escapeHtml(j.asset_name || j.asset_id || 'Asset journal')}</h3>
                    <p>${escapeHtml(j.description || '')}</p>
                    ${j.amount ? `<p><strong>${formatMoney(j.amount)}</strong></p>` : ''}
                    <p class="text-muted">Submitted by ${escapeHtml(j.submitter_name || 'Asset Manager')}${submitted ? ` · ${escapeHtml(submitted)}` : ''}</p>
                    <p class="asset-journal-reason"><strong>Asset Manager reason:</strong> ${escapeHtml(j.reason || '—')}</p>
                    ${j.fm_reviewer_name ? `<p class="text-muted">FM forwarded ${escapeHtml((j.fm_forwarded_at || '').slice(0, 10) || '—')} · ${escapeHtml(j.fm_reviewer_name)}</p>` : ''}
                    ${status === 'approved' && reviewed ? `<p class="asset-journal-outcome asset-journal-outcome--approved">Approved on ${escapeHtml(reviewed)}${j.reviewer_name ? ` · ${escapeHtml(j.reviewer_name)}` : ''}</p>` : ''}
                    ${status === 'rejected' ? `<p class="asset-journal-outcome asset-journal-outcome--rejected">Rejected on ${escapeHtml(reviewed || '—')}${j.reviewer_name ? ` · ${escapeHtml(j.reviewer_name)}` : ''}</p>` : ''}
                    ${j.rejection_reason ? `<p class="asset-journal-rejection"><strong>Rejection reason:</strong> ${escapeHtml(j.rejection_reason)}</p>` : ''}
                    <p class="asset-journal-history-meta text-muted">${escapeHtml(j.journal_id || '—')} · ${escapeHtml(j.asset_id || '—')}</p>
                </article>`;
            }).join('')}</div>`;
        }

        periodGroupKey(tx) {
            const md = tx.metadata || {};
            return (
                tx.period_name
                || md.period_name
                || md.reporting_period
                || md.period
                || 'Other submissions'
            ).trim() || 'Other submissions';
        }

        groupTransactionsByPeriod(transactions) {
            const groups = new Map();
            transactions.forEach((tx) => {
                const key = this.periodGroupKey(tx);
                if (!groups.has(key)) groups.set(key, []);
                groups.get(key).push(tx);
            });
            const latestTs = (items) => Math.max(
                ...items.map((t) => Date.parse(t.updated_at || t.created_at) || 0),
                0,
            );
            return [...groups.entries()]
                .sort((a, b) => latestTs(b[1]) - latestTs(a[1]))
                .map(([label, items]) => ({
                    label,
                    items: items.sort(
                        (a, b) => (Date.parse(b.updated_at || b.created_at) || 0)
                            - (Date.parse(a.updated_at || a.created_at) || 0),
                    ),
                }));
        }

        docTypeOrder() {
            return ['balance_sheet', 'income_statement', 'budget_report'];
        }

        docTypeLabel(dtype) {
            if (window.TransactionCardUI && typeof TransactionCardUI.typeLabel === 'function') {
                return TransactionCardUI.typeLabel(dtype);
            }
            return (dtype || 'Document').replace(/_/g, ' ');
        }

        groupTransactionsByDocType(transactions) {
            const groups = new Map();
            transactions.forEach((tx) => {
                const key = tx.transaction_type || 'other';
                if (!groups.has(key)) groups.set(key, []);
                groups.get(key).push(tx);
            });

            const ordered = [];
            this.docTypeOrder().forEach((dtype) => {
                if (!groups.has(dtype)) return;
                ordered.push({
                    type: dtype,
                    label: this.docTypeLabel(dtype),
                    items: groups.get(dtype),
                });
                groups.delete(dtype);
            });

            [...groups.entries()]
                .sort((a, b) => a[0].localeCompare(b[0]))
                .forEach(([dtype, items]) => {
                    ordered.push({
                        type: dtype,
                        label: this.docTypeLabel(dtype),
                        items,
                    });
                });

            return ordered;
        }

        renderHistorySummary() {
            const summaryEl = document.getElementById('fmHistorySummary');
            const countEl = document.getElementById('fmHistoryCount');
            const shown = this.filtered.length;
            const total = this.items.length;

            if (countEl) {
                countEl.textContent = String(shown);
            }

            if (!summaryEl) return;

            if (this.recordType === 'asset_journals' || !this.items.length) {
                summaryEl.innerHTML = '';
                return;
            }

            const approved = this.filtered.filter((tx) => {
                const s = String(tx.status || '').toLowerCase();
                return s === 'approved' || s === 'approved_by_manager';
            }).length;
            const rejected = this.filtered.filter((tx) => {
                const s = String(tx.status || '').toLowerCase();
                return s.includes('reject');
            }).length;

            summaryEl.innerHTML = `
                <span class="fm-history-summary__chip fm-history-summary__chip--total">${shown}${shown !== total ? ` of ${total}` : ''} shown</span>
                <span class="fm-history-summary__chip fm-history-summary__chip--approved">${approved} approved</span>
                <span class="fm-history-summary__chip fm-history-summary__chip--rejected">${rejected} rejected</span>`;
        }

        render() {
            const container = document.getElementById('fmHistoryContainer');
            if (!container) return;

            if (this.recordType === 'asset_journals') {
                this.renderHistorySummary();
                this.renderAssetJournalHistory();
                return;
            }

            if (!this.filtered.length) {
                this.renderHistorySummary();
                container.innerHTML = `
                    <div class="approval-empty-state fm-history-empty">
                        <div class="approval-empty-icon">📚</div>
                        <h3>No records</h3>
                        <p>No submissions match the current filter.</p>
                    </div>`;
                return;
            }

            this.renderHistorySummary();
            const groups = this.groupTransactionsByPeriod(this.filtered);
            container.innerHTML = groups.map((group) => {
                const docGroups = this.groupTransactionsByDocType(group.items);
                const docSections = docGroups.map((docGroup) => `
                    <div class="fm-history-doc-type-group">
                        <header class="fm-history-doc-type-group__head">
                            <h3 class="fm-history-doc-type-group__title">${escapeHtml(docGroup.label)}</h3>
                            <span class="fm-history-doc-type-group__count">${docGroup.items.length}</span>
                        </header>
                        ${TransactionCardUI.renderTransactionList(docGroup.items, {
                            variant: 'history',
                            returnTo: RETURN_TO,
                            reviewLabel: 'View Details',
                        })}
                    </div>`).join('');

                return `
                <section class="fm-history-period-group">
                    <header class="fm-history-period-group__head">
                        <h2 class="fm-history-period-group__title">${escapeHtml(group.label)}</h2>
                        <span class="fm-history-period-group__count">${group.items.length} submission${group.items.length === 1 ? '' : 's'}</span>
                    </header>
                    ${docSections}
                </section>`;
            }).join('');
        }
    }

    document.addEventListener('DOMContentLoaded', () => {
        const role = window.currentUserRole || '';
        if (role === 'FINANCE_MANAGER' || role === 'CFO') {
            window.financeManagerHistory = new FinanceManagerHistory();
        }
    });
})();
