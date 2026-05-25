/**
 * FM nav badge — pending asset journal count.
 */
(function () {
    const badge = document.getElementById('navAssetJournalBadge');
    if (!badge) return;

    async function refresh() {
        try {
            const r = await fetch('/api/asset-journals/pending', { credentials: 'same-origin' });
            const j = await r.json();
            const n = Number(j.count ?? (j.journals || []).length ?? 0);
            if (n > 0) {
                badge.textContent = n > 99 ? '99+' : String(n);
                badge.hidden = false;
                badge.removeAttribute('hidden');
                badge.setAttribute('aria-label', `${n} pending asset journals`);
            } else {
                badge.textContent = '';
                badge.hidden = true;
                badge.setAttribute('hidden', '');
            }
        } catch (_) {
            /* ignore */
        }
    }

    document.addEventListener('DOMContentLoaded', refresh);
    window.VarydianAssetJournalNav = { refreshPendingBadge: refresh };
})();
