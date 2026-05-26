/** Reconciliation — sync GL from trial balance or manual override. */
(function () {
    if (!window.location.pathname.includes('/asset-manager/reconciliation')) return;

    const API = '/api/asset-manager/reconciliation';

    function formatMoney(n) {
        const num = Number(n);
        if (!Number.isFinite(num)) return '—';
        return num.toLocaleString('en-ZA', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    async function refreshPanel() {
        try {
            const res = await VarydianUtils.safeFetch(API);
            if (!res.success) return;
            const panel = document.getElementById('reconciliationPanel');
            if (panel) panel.dataset.reconciled = res.reconciled ? 'true' : 'false';
        } catch (_e) {
            /* server-rendered values remain */
        }
    }

    document.addEventListener('DOMContentLoaded', () => {
        document.getElementById('btnSyncGlFromTb')?.addEventListener('click', async () => {
            const btn = document.getElementById('btnSyncGlFromTb');
            if (btn) {
                btn.disabled = true;
                btn.textContent = 'Checking…';
            }
            try {
                const preview = await VarydianUtils.safeFetch(`${API}/sync-tb/preview`);
                if (!preview.success) throw new Error(preview.error || 'Could not preview sync');

                if (preview.matched_lines === 0) {
                    VarydianUtils.showError(
                        'No fixed-asset GL lines matched in the approved trial balance. '
                        + 'Map PPE accounts first, or use manual override.'
                    );
                    return;
                }

                if (preview.already_synced) {
                    VarydianUtils.showSuccess(
                        'GL balance already matches the latest approved trial balance (no changes).'
                    );
                    return;
                }

                const delta = Number(preview.balance_delta) || 0;
                const deltaSign = delta >= 0 ? '+' : '−';
                const message = [
                    `Update GL balance from R ${formatMoney(preview.current_gl_balance)}`,
                    `to R ${formatMoney(preview.proposed_gl_balance)} (${deltaSign}R ${formatMoney(Math.abs(delta))})?`,
                    `${preview.matched_lines} fixed-asset line(s) from ${preview.session_label || 'trial balance'}.`,
                ].join('\n');

                const ok = window.varydianAppConfirm
                    ? await window.varydianAppConfirm('Sync from trial balance', message, {
                        confirmText: 'Apply sync',
                        cancelText: 'Cancel',
                    })
                    : false;
                if (!ok) return;

                if (btn) btn.textContent = 'Syncing…';
                const res = await VarydianUtils.safeFetch(`${API}/sync-tb`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ session_id: preview.session_id }),
                });
                if (!res.success) throw new Error(res.error || 'Sync failed');
                if (res.no_change) {
                    VarydianUtils.showSuccess(res.message || 'No changes needed');
                    return;
                }
                VarydianUtils.showSuccess(res.message || 'GL balance synced from trial balance');
                setTimeout(() => window.location.reload(), 600);
            } catch (err) {
                VarydianUtils.showError(err.message);
            } finally {
                if (btn) {
                    btn.disabled = false;
                    btn.textContent = 'Sync from trial balance';
                }
            }
        });

        document.getElementById('manualGlForm')?.addEventListener('submit', async (e) => {
            e.preventDefault();
            const form = e.target;
            const fd = new FormData(form);
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn) submitBtn.disabled = true;
            try {
                const res = await VarydianUtils.safeFetch(`${API}/gl-balance`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        balance: parseFloat(fd.get('balance')),
                        note: fd.get('note'),
                    }),
                });
                if (!res.success) throw new Error(res.error || 'Update failed');
                form.querySelector('[name="note"]')?.setAttribute('value', '');
                if (form.querySelector('[name="note"]')) {
                    form.querySelector('[name="note"]').value = '';
                }
                VarydianUtils.showSuccess(res.message || 'GL balance updated');
                setTimeout(() => window.location.reload(), 600);
            } catch (err) {
                VarydianUtils.showError(err.message);
            } finally {
                if (submitBtn) submitBtn.disabled = false;
            }
        });

        refreshPanel();
    });
})();
