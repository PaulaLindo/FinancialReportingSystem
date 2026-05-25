/**
 * Asset Manager — my journals list.
 */
(function () {
    if (!window.location.pathname.includes('/asset-manager/journals')) return;

    const listEl = document.getElementById('assetManagerJournalsList');
    const filterEl = document.getElementById('journalStatusFilter');

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text == null ? '' : String(text);
        return div.innerHTML;
    }

    function journalTypeLabel(t) {
        if (t === 'useful_life_review') return 'Useful life review';
        if (t === 'impairment') return 'Impairment';
        if (t === 'disposal') return 'Disposal';
        return t || 'Journal';
    }

    function formatMoney(n) {
        const v = Number(n) || 0;
        return `R ${v.toLocaleString('en-ZA', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    }

    async function loadJournals() {
        const status = filterEl?.value || '';
        const qs = status ? `?status=${encodeURIComponent(status)}` : '';
        const res = await VarydianUtils.safeFetch(`/api/asset-manager/journals${qs}`);
        if (!res.success) throw new Error(res.error || 'Failed to load journals');
        return res.journals || [];
    }

    function render(journals) {
        if (!listEl) return;
        if (!journals.length) {
            listEl.innerHTML = '<p class="text-muted">No journals match this filter.</p>';
            return;
        }
        listEl.innerHTML = journals.map((j) => `
            <article class="asset-journal-card asset-journal-card--${escapeHtml(j.status)}">
                <div class="asset-journal-card__head">
                    <span class="asset-journal-type">${escapeHtml(journalTypeLabel(j.journal_type))}</span>
                    <span class="asset-journal-status status-${escapeHtml(j.status)}">${escapeHtml((j.status || '').replace(/_/g, ' '))}</span>
                </div>
                <p><a href="/asset-manager/assets/${encodeURIComponent(j.asset_id)}">${escapeHtml(j.asset_name || j.asset_id)}</a></p>
                <p>${escapeHtml(j.description || '')}</p>
                ${j.amount ? `<p class="text-muted">Amount: ${formatMoney(j.amount)}</p>` : ''}
                <p class="text-muted">Submitted ${escapeHtml((j.submitted_at || '').slice(0, 10))}</p>
                ${j.status === 'rejected' && j.rejection_reason ? `<p class="asset-journal-rejection"><strong>FM reason:</strong> ${escapeHtml(j.rejection_reason)}</p>` : ''}
            </article>`).join('');
    }

    async function refresh() {
        try {
            listEl.innerHTML = '<div class="queue-loading"><div class="loading-spinner"></div><p>Loading journals…</p></div>';
            render(await loadJournals());
        } catch (err) {
            listEl.innerHTML = `<p class="text-danger">${escapeHtml(err.message)}</p>`;
        }
    }

    filterEl?.addEventListener('change', refresh);
    document.addEventListener('DOMContentLoaded', refresh);
})();
