/**
 * Nav badges — pending asset journal counts (FM/CFO queue + Asset Manager own pending).
 */
(function () {
    const fmBadges = document.querySelectorAll('[data-journal-badge="fm"]');
    const amBadges = document.querySelectorAll('[data-journal-badge="am"]');
    if (!fmBadges.length && !amBadges.length) return;

    const role = String(window.currentUserRole || '').toUpperCase();

    function setBadges(badges, count, ariaLabel) {
        const n = Number(count ?? 0);
        badges.forEach((badge) => {
            if (n > 0) {
                badge.textContent = n > 99 ? '99+' : String(n);
                badge.hidden = false;
                badge.removeAttribute('hidden');
                badge.setAttribute('aria-label', ariaLabel);
            } else {
                badge.textContent = '';
                badge.hidden = true;
                badge.setAttribute('hidden', '');
            }
        });
    }

    async function refreshFmCfo() {
        if (!fmBadges.length) return;
        try {
            const r = await fetch('/api/asset-journals/pending/count', { credentials: 'same-origin' });
            const j = await r.json();
            const queueLabel = role === 'CFO'
                ? 'material asset journals awaiting CFO sign-off'
                : 'pending asset journals';
            setBadges(fmBadges, j.count, `${j.count ?? 0} ${queueLabel}`);
        } catch (_) {
            /* ignore */
        }
    }

    async function refreshAssetManager() {
        if (!amBadges.length) return;
        try {
            const r = await fetch('/api/asset-manager/journals/pending/count', { credentials: 'same-origin' });
            const j = await r.json();
            setBadges(amBadges, j.count, `${j.count ?? 0} of your journals awaiting FM approval`);
        } catch (_) {
            /* ignore */
        }
    }

    async function refresh() {
        await Promise.all([refreshFmCfo(), refreshAssetManager()]);
    }

    document.addEventListener('DOMContentLoaded', refresh);
    window.VarydianAssetJournalNav = { refreshPendingBadge: refresh };
})();
