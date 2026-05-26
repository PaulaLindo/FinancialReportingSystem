/** Read-only material asset journal trail for Auditor role. */
(function () {
    if (!window.location.pathname.includes('/audit/asset-journals')) return;

    const API = '/api/audit/asset-journals';

    function formatMoney(n) {
        const num = Number(n);
        if (!Number.isFinite(num)) return '—';
        return `R ${num.toLocaleString('en-ZA', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    }

    function escapeHtml(value) {
        return String(value ?? '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    function journalTypeLabel(type) {
        const labels = {
            disposal: 'Disposal',
            impairment: 'Impairment',
            useful_life_review: 'Useful life review',
        };
        return labels[type] || type || 'Journal';
    }

    class AuditAssetJournalsPage {
        constructor() {
            this.summaryEl = document.getElementById('auditAssetJournalsSummary');
            this.listEl = document.getElementById('auditAssetJournalsList');
            this.loadJournals();
        }

        async loadJournals() {
            try {
                const res = await VarydianUtils.safeFetch(API);
                if (!res.success) throw new Error(res.error || 'Failed to load journal trail');
                const journals = res.journals || [];
                this.renderSummary(journals);
                this.renderList(journals);
            } catch (err) {
                if (this.listEl) {
                    this.listEl.innerHTML = `<p class="text-danger">${escapeHtml(err.message || 'Load failed')}</p>`;
                }
            }
        }

        renderSummary(journals) {
            if (!this.summaryEl) return;
            const disposals = journals.filter((j) => j.journal_type === 'disposal').length;
            const impairments = journals.filter((j) => j.journal_type === 'impairment').length;
            this.summaryEl.innerHTML = `
                <div class="stat-card"><div class="stat-number">${journals.length}</div><div class="stat-label">CFO-approved material journals</div></div>
                <div class="stat-card"><div class="stat-number">${disposals}</div><div class="stat-label">Disposals</div></div>
                <div class="stat-card"><div class="stat-number">${impairments}</div><div class="stat-label">Material impairments</div></div>`;
        }

        renderList(journals) {
            if (!this.listEl) return;
            if (!journals.length) {
                this.listEl.innerHTML = `
                    <div class="approval-empty-state">
                        <div class="approval-empty-icon">📚</div>
                        <h3>No material journal records</h3>
                        <p>CFO-approved disposals and material impairments will appear here once settled.</p>
                    </div>`;
                return;
            }

            this.listEl.innerHTML = journals.map((j) => {
                const reviewed = (j.reviewed_at || '').slice(0, 10);
                const submitted = (j.submitted_at || '').slice(0, 10);
                return `
                <article class="asset-journal-card asset-journal-card--approved">
                    <div class="asset-journal-card__head">
                        <span class="asset-journal-type">${escapeHtml(journalTypeLabel(j.journal_type))}</span>
                        <span class="asset-journal-status status-approved">CFO approved</span>
                    </div>
                    <h3>${escapeHtml(j.asset_name || j.asset_id || 'Asset journal')}</h3>
                    <p>${escapeHtml(j.description || '')}</p>
                    ${j.amount ? `<p><strong>${formatMoney(j.amount)}</strong></p>` : ''}
                    ${j.escalation_reason ? `<p class="asset-journal-escalation">${escapeHtml(j.escalation_reason)}</p>` : ''}
                    <p class="text-muted">Submitted by ${escapeHtml(j.submitter_name || 'Asset Manager')}${submitted ? ` · ${escapeHtml(submitted)}` : ''}</p>
                    <p class="asset-journal-reason"><strong>Asset Manager reason:</strong> ${escapeHtml(j.reason || '—')}</p>
                    ${j.fm_reviewer_name ? `<p class="text-muted">FM forwarded ${escapeHtml((j.fm_forwarded_at || '').slice(0, 10) || '—')} · ${escapeHtml(j.fm_reviewer_name)}</p>` : ''}
                    ${reviewed ? `<p class="asset-journal-outcome asset-journal-outcome--approved">CFO approved on ${escapeHtml(reviewed)}${j.reviewer_name ? ` · ${escapeHtml(j.reviewer_name)}` : ''}</p>` : ''}
                    <p class="asset-journal-history-meta text-muted">${escapeHtml(j.journal_id || '—')} · ${escapeHtml(j.asset_id || '—')}</p>
                </article>`;
            }).join('');
        }
    }

    document.addEventListener('DOMContentLoaded', () => new AuditAssetJournalsPage());
})();
