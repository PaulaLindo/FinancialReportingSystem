/**
 * Navbar unread badge — fetch count only when useful (no periodic polling).
 */
(function () {
    const uid = window.currentUserId;
    if (!uid) {
        return;
    }

    const badges = document.querySelectorAll('.nav-inbox-badge');

    let refreshTimer = null;
    let inFlight = false;
    let lastRefreshAt = 0;
    const MIN_PASSIVE_REFRESH_MS = 60000;
    let lastHidden =
        typeof document.visibilityState === 'string'
            ? document.visibilityState === 'hidden'
            : false;

    async function refresh(options) {
        const force = options && options.force === true;
        const now = Date.now();
        if (!force && now - lastRefreshAt < MIN_PASSIVE_REFRESH_MS) {
            return;
        }
        if (inFlight) {
            return;
        }
        inFlight = true;
        try {
            const r = await fetch('/api/inbox/unread-count', { credentials: 'same-origin' });
            const j = await r.json();
            lastRefreshAt = Date.now();
            const n = Number(j.count ?? 0);
            if (!badges.length) {
                return;
            }
            badges.forEach(function (badge) {
                if (n > 0) {
                    badge.textContent = n > 99 ? '99+' : String(n);
                    badge.hidden = false;
                    badge.removeAttribute('hidden');
                    badge.setAttribute('aria-label', `${n} unread messages`);
                } else {
                    badge.textContent = '';
                    badge.hidden = true;
                    badge.setAttribute('hidden', '');
                }
            });
        } catch (_) {
            /* ignore */
        } finally {
            inFlight = false;
        }
    }

    function refreshSoon(options) {
        if (refreshTimer !== null) {
            clearTimeout(refreshTimer);
        }
        refreshTimer = window.setTimeout(function () {
            refreshTimer = null;
            refresh(options);
        }, 150);
    }

    /** One call on first paint for this navigation. */
    refresh({ force: true });

    /** User returns to this tab after another tab or app. */
    document.addEventListener('visibilitychange', function () {
        if (document.visibilityState === 'hidden') {
            lastHidden = true;
            return;
        }
        if (document.visibilityState === 'visible' && lastHidden) {
            lastHidden = false;
            refreshSoon();
        }
    });

    /** Back/forward cache restore (mobile Safari et al.) */
    window.addEventListener('pageshow', function (ev) {
        if (ev.persisted) {
            refreshSoon();
        }
    });

    /** Lets other scripts update the badge after inbox actions without a full poll loop. */
    window.VarydianInboxNav = {
        refreshUnreadBadge: function (options) {
            return refresh(options || { force: true });
        },
        refreshUnreadBadgeSoon: refreshSoon,
    };
})();
