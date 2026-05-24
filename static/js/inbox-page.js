/**
 * Inbox page: expand messages, mark read on open, mark all read.
 */

(function () {
    const reload = () => window.location.reload();

    async function post(url) {
        const r = await fetch(url, { method: 'POST', credentials: 'same-origin' });
        const body = await r.json().catch(() => ({}));
        if (!r.ok) {
            const msg = body.error || r.statusText;
            window.alert(typeof msg === 'string' ? msg : 'Could not update inbox');
            return false;
        }
        return true;
    }

    function refreshNavBadge() {
        if (window.VarydianInboxNav && typeof window.VarydianInboxNav.refreshUnreadBadge === 'function') {
            window.VarydianInboxNav.refreshUnreadBadge({ force: true });
        }
    }

    function setMessageRead(li) {
        if (!li || li.dataset.unread !== 'true') return;
        li.dataset.unread = 'false';
        li.classList.remove('inbox-msg--unread');
        const btn = li.querySelector('.inbox-mark-read');
        if (btn) {
            const label = document.createElement('span');
            label.className = 'inbox-msg__readlabel muted';
            label.textContent = 'Read';
            btn.replaceWith(label);
        }
    }

    async function markMessageRead(messageId, li) {
        if (!messageId) return false;
        const ok = await post('/api/inbox/' + encodeURIComponent(messageId) + '/read');
        if (ok) {
            setMessageRead(li);
            refreshNavBadge();
        }
        return ok;
    }

    document.querySelectorAll('.inbox-msg').forEach(function (li) {
        const toggle = li.querySelector('.inbox-msg__toggle');
        const panel = li.querySelector('.inbox-msg__panel');
        if (!toggle || !panel) return;

        toggle.addEventListener('click', async function () {
            const isOpen = toggle.getAttribute('aria-expanded') === 'true';
            if (isOpen) {
                toggle.setAttribute('aria-expanded', 'false');
                panel.hidden = true;
                li.classList.remove('inbox-msg--open');
                return;
            }

            toggle.setAttribute('aria-expanded', 'true');
            panel.hidden = false;
            li.classList.add('inbox-msg--open');

            if (li.dataset.unread === 'true') {
                const id = li.getAttribute('data-message-id');
                toggle.disabled = true;
                await markMessageRead(id, li);
                toggle.disabled = false;
            }
        });

        const openLink = li.querySelector('.inbox-msg__open-link');
        if (openLink) {
            openLink.addEventListener('click', async function (ev) {
                if (li.dataset.unread !== 'true') return;
                ev.preventDefault();
                const href = openLink.href;
                const id = li.getAttribute('data-message-id');
                await markMessageRead(id, li);
                window.location.href = href;
            });
        }
    });

    document.querySelectorAll('.inbox-mark-read').forEach(function (btn) {
        btn.addEventListener('click', async function (ev) {
            ev.stopPropagation();
            const id = btn.getAttribute('data-message-id');
            if (!id) return;
            const li = btn.closest('.inbox-msg');
            btn.disabled = true;
            const ok = await markMessageRead(id, li);
            if (!ok) btn.disabled = false;
        });
    });

    const markAll = document.getElementById('inboxMarkAllRead');
    if (markAll) {
        markAll.addEventListener('click', async function () {
            markAll.disabled = true;
            const ok = await post('/api/inbox/mark-all-read');
            if (ok) {
                refreshNavBadge();
                reload();
            } else {
                markAll.disabled = false;
            }
        });
    }
})();
