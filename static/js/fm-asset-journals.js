/**
 * Finance Manager — pending asset journal approval queue.
 */
(function () {
    if (!window.location.pathname.includes('/finance-manager/asset-journals')) return;

    const listEl = document.getElementById('fmAssetJournalsList');
    const countEl = document.getElementById('assetJournalCount');

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
        return t || 'Journal';
    }

    function setCardActionsEnabled(card, enabled) {
        if (!card) return;
        card.classList.toggle('asset-journal-card--rejecting', !enabled);
        card.querySelectorAll('.asset-journal-card__actions [data-action]').forEach((btn) => {
            btn.disabled = !enabled;
        });
    }

    function closeRejectPanels(exceptCard) {
        listEl?.querySelectorAll('.asset-reject-panel').forEach((panel) => {
            const card = panel.closest('[data-journal-id]');
            if (!exceptCard || !exceptCard.contains(panel)) {
                panel.remove();
                if (card) setCardActionsEnabled(card, true);
            }
        });
    }

    function showRejectPanel(card) {
        closeRejectPanels(card);
        if (card.querySelector('.asset-reject-panel')) return;

        setCardActionsEnabled(card, false);

        const panel = document.createElement('div');
        panel.className = 'asset-reject-panel';
        panel.innerHTML = `
            <label class="asset-field">
                <span class="asset-field__label">Rejection reason <span class="asset-field__hint">(required)</span></span>
                <textarea class="asset-field__control asset-field__control--textarea" rows="3" required minlength="5" placeholder="Explain why this journal is being rejected…"></textarea>
            </label>
            <div class="asset-reject-panel__actions">
                <button type="button" class="btn btn-danger btn-sm" data-action="confirm-reject">Confirm rejection</button>
                <button type="button" class="btn btn-secondary btn-sm" data-action="cancel-reject">Cancel</button>
            </div>`;

        const actions = card.querySelector('.asset-journal-card__actions');
        actions?.insertAdjacentElement('beforebegin', panel);

        const textarea = panel.querySelector('textarea');
        textarea?.focus();

        panel.querySelector('[data-action="cancel-reject"]')?.addEventListener('click', () => {
            panel.remove();
            setCardActionsEnabled(card, true);
        });

        panel.querySelector('[data-action="confirm-reject"]')?.addEventListener('click', async () => {
            const reason = textarea?.value.trim() || '';
            if (reason.length < 5) {
                VarydianUtils.showToast('Please enter a rejection reason (at least 5 characters).', 'warning');
                textarea?.focus();
                return;
            }
            const journalId = card.dataset.journalId;
            const confirmBtn = panel.querySelector('[data-action="confirm-reject"]');
            if (confirmBtn) {
                confirmBtn.disabled = true;
                confirmBtn.textContent = 'Rejecting…';
            }
            try {
                const res = await VarydianUtils.safeFetch(`/api/asset-journals/${encodeURIComponent(journalId)}/reject`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ reason }),
                });
                if (!res.success) throw new Error(res.error);
                VarydianUtils.showSuccess(res.message || 'Journal rejected');
                window.VarydianAssetJournalNav?.refreshPendingBadge?.();
                loadPending();
            } catch (err) {
                VarydianUtils.showError(err.message);
                if (confirmBtn) {
                    confirmBtn.disabled = false;
                    confirmBtn.textContent = 'Confirm rejection';
                }
            }
        });
    }

    async function loadPending() {
        try {
            const res = await VarydianUtils.safeFetch('/api/asset-journals/pending');
            if (!res.success) throw new Error(res.error || 'Load failed');
            const journals = res.journals || [];
            if (countEl) countEl.textContent = String(journals.length);
            render(journals);
        } catch (err) {
            if (listEl) listEl.innerHTML = `<p class="text-danger">${escapeHtml(err.message)}</p>`;
        }
    }

    function render(journals) {
        if (!listEl) return;
        if (!journals.length) {
            listEl.innerHTML = `
                <div class="queue-empty">
                    <h3>No asset journals pending</h3>
                    <p>Asset Manager useful life and impairment submissions appear here.</p>
                </div>`;
            return;
        }
        listEl.innerHTML = journals.map((j) => `
            <article class="asset-journal-card asset-journal-card--pending" data-journal-id="${escapeHtml(j.journal_id)}">
                <div class="asset-journal-card__head">
                    <span class="asset-journal-type">${escapeHtml(journalTypeLabel(j.journal_type))}</span>
                    <span class="asset-journal-status status-pending_review">Pending review</span>
                </div>
                <h3>${escapeHtml(j.asset_name || j.asset_id)}</h3>
                <p>${escapeHtml(j.description || '')}</p>
                ${j.amount ? `<p><strong>${formatMoney(j.amount)}</strong></p>` : ''}
                <p class="text-muted">Submitted by ${escapeHtml(j.submitter_name || 'Asset Manager')} · ${escapeHtml((j.submitted_at || '').slice(0, 10))}</p>
                <p class="asset-journal-reason"><strong>Reason:</strong> ${escapeHtml(j.reason || '—')}</p>
                <div class="asset-journal-card__actions">
                    <button type="button" class="btn btn-success btn-sm" data-action="approve-journal">Approve</button>
                    <button type="button" class="btn btn-danger btn-sm" data-action="reject-journal">Reject</button>
                </div>
            </article>`).join('');

        listEl.querySelectorAll('[data-action="approve-journal"]').forEach((btn) => {
            btn.addEventListener('click', () => act(btn, 'approve'));
        });
        listEl.querySelectorAll('[data-action="reject-journal"]').forEach((btn) => {
            btn.addEventListener('click', () => act(btn, 'reject'));
        });
    }

    async function act(btn, action) {
        const card = btn.closest('[data-journal-id]');
        const journalId = card?.dataset.journalId;
        if (!journalId) return;

        if (action === 'reject') {
            showRejectPanel(card);
            return;
        }

        const ok = typeof window.showConfirm === 'function'
            ? await window.showConfirm(
                'Approve asset journal',
                'Approve this asset journal and apply the change to the asset register?',
                { confirmText: 'Approve', cancelText: 'Cancel' }
            )
            : window.confirm('Approve this asset journal and apply the change to the asset register?');
        if (!ok) return;
        btn.disabled = true;
        const originalLabel = btn.textContent;
        btn.textContent = 'Approving…';
        try {
            const res = await VarydianUtils.safeFetch(`/api/asset-journals/${encodeURIComponent(journalId)}/approve`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({}),
            });
            if (!res.success) throw new Error(res.error);
            VarydianUtils.showSuccess(res.message || 'Journal approved');
            window.VarydianAssetJournalNav?.refreshPendingBadge?.();
            loadPending();
        } catch (err) {
            VarydianUtils.showError(err.message);
            btn.disabled = false;
            btn.textContent = originalLabel;
        }
    }

    document.addEventListener('DOMContentLoaded', loadPending);
})();
