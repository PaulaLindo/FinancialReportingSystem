(function () {
    if (!window.location.pathname.includes('/admin')) return;

    const ROLE_LABELS = {
        FINANCE_CLERK: 'Finance Clerk',
        FINANCE_MANAGER: 'Finance Manager',
        CFO: 'CFO',
        ASSET_MANAGER: 'Asset Manager',
        AUDITOR: 'Auditor',
        SYSTEM_ADMIN: 'System Admin',
        CLERK: 'Clerk',
        ACCOUNTANT: 'Accountant',
    };

    const ROLE_ICONS = {
        FINANCE_CLERK: '📋',
        FINANCE_MANAGER: '✅',
        CFO: '👔',
        ASSET_MANAGER: '🏢',
        AUDITOR: '🔍',
        SYSTEM_ADMIN: '⚙️',
        CLERK: '📋',
        ACCOUNTANT: '📊',
    };

    const EXPECTED_REQUIRED_UPLOADS = 3;

    function escapeHtml(value) {
        return String(value ?? '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    function formatDate(value) {
        if (!value) return '—';
        return String(value).slice(0, 10);
    }

    function statusPill(text, kind) {
        return `<span class="admin-status admin-status--${escapeHtml(kind)}">${escapeHtml(text)}</span>`;
    }

    function notify(message, type = 'info') {
        if (window.VarydianUtils && typeof VarydianUtils.showToast === 'function') {
            VarydianUtils.showToast(message, type);
            return;
        }
        console.warn('[admin]', message);
    }

    async function appConfirm(title, message) {
        if (window.modalSystem?.confirm) {
            return window.modalSystem.confirm(title, message, {
                confirmText: 'Confirm',
                cancelText: 'Cancel',
            });
        }
        return false;
    }

    class AdminPage {
        constructor() {
            this.overviewEl = document.getElementById('adminOverviewStats');
            this.periodsEl = document.getElementById('adminPeriodsList');
            this.usersEl = document.getElementById('adminUsersList');
            this.migrationsEl = document.getElementById('adminMigrationsPanel');
            this.periodForm = document.getElementById('adminCreatePeriodForm');
            this.userForm = document.getElementById('adminCreateUserForm');
            this.periods = [];
            this.users = [];
            this.periodStatusFilter = 'all';
            this.userRoleFilter = 'all';
            this.userStatusFilter = 'all';
            this.userSearchQuery = '';
            this.bindForms();
            this.setDefaultPeriodDates();
            this.loadAll();
        }

        setDefaultPeriodDates() {
            if (!this.periodForm) return;
            const now = new Date();
            const y = now.getFullYear();
            const m = String(now.getMonth() + 1).padStart(2, '0');
            const start = `${y}-${m}-01`;
            const endDate = new Date(y, now.getMonth() + 1, 0);
            const end = endDate.toISOString().slice(0, 10);
            const due = end;
            if (this.periodForm.start_date && !this.periodForm.start_date.value) {
                this.periodForm.start_date.value = start;
            }
            if (this.periodForm.end_date && !this.periodForm.end_date.value) {
                this.periodForm.end_date.value = end;
            }
            if (this.periodForm.due_date && !this.periodForm.due_date.value) {
                this.periodForm.due_date.value = due;
            }
        }

        bindForms() {
            this.periodForm?.addEventListener('submit', async (ev) => {
                ev.preventDefault();
                const fd = new FormData(this.periodForm);
                const payload = Object.fromEntries(fd.entries());
                payload.required_uploads = EXPECTED_REQUIRED_UPLOADS;
                try {
                    const res = await VarydianUtils.safeFetch('/api/periods', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(payload),
                    });
                    if (!res.success) throw new Error(res.error || 'Create failed');
                    this.periodForm.reset();
                    this.setDefaultPeriodDates();
                    await this.loadAll();
                    notify('Period created', 'success');
                } catch (err) {
                    notify(err.message || 'Failed to create period', 'error');
                }
            });

            this.userForm?.addEventListener('submit', async (ev) => {
                ev.preventDefault();
                const fd = new FormData(this.userForm);
                const email = String(fd.get('email') || '').trim();
                const payload = {
                    full_name: fd.get('full_name'),
                    email,
                    username: email,
                    password: fd.get('password'),
                    role: fd.get('role'),
                };
                try {
                    const res = await VarydianUtils.safeFetch('/api/admin/users', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(payload),
                    });
                    if (!res.success) throw new Error(res.error || 'Create failed');
                    this.userForm.reset();
                    await this.loadAll();
                    notify('User created', 'success');
                } catch (err) {
                    notify(err.message || 'Failed to create user', 'error');
                }
            });

            this.periodsEl?.addEventListener('click', async (ev) => {
                const mergeBtn = ev.target.closest('[data-period-merge]');
                if (mergeBtn) {
                    const periodId = mergeBtn.getAttribute('data-period-id');
                    if (!periodId) return;
                    const confirmed = await appConfirm(
                        'Merge duplicate period rows',
                        'Relink any uploads and delete empty duplicate rows for this reporting month in Supabase? Locked empty duplicates are included. This cannot be undone.'
                    );
                    if (!confirmed) return;
                    mergeBtn.disabled = true;
                    try {
                        const res = await VarydianUtils.safeFetch(
                            `/api/admin/periods/${encodeURIComponent(periodId)}/merge-duplicates`,
                            { method: 'POST' }
                        );
                        if (!res.success) throw new Error(res.error || 'Merge failed');
                        await this.loadAll();
                        const skipped = Array.isArray(res.skipped) ? res.skipped.length : 0;
                        const msg = res.message || `Merged ${(res.removed_ids || []).length} duplicate row(s).`;
                        notify(skipped ? `${msg} (${skipped} skipped)` : msg, skipped ? 'warning' : 'success');
                    } catch (err) {
                        notify(err.message || 'Could not merge duplicate rows', 'error');
                    } finally {
                        mergeBtn.disabled = false;
                    }
                    return;
                }

                const btn = ev.target.closest('[data-period-action],[data-period-delete]');
                if (!btn) return;
                const periodId = btn.getAttribute('data-period-id');
                if (!periodId) return;

                if (btn.hasAttribute('data-period-delete')) {
                    const confirmed = await appConfirm(
                        'Delete reporting period',
                        'Delete this reporting period? This cannot be undone.'
                    );
                    if (!confirmed) return;
                    btn.disabled = true;
                    try {
                        const res = await VarydianUtils.safeFetch(
                            `/api/admin/periods/${encodeURIComponent(periodId)}`,
                            { method: 'DELETE' }
                        );
                        if (!res.success) throw new Error(res.error || 'Delete failed');
                        await this.loadAll();
                        notify(res.message || 'Period deleted', 'success');
                    } catch (err) {
                        notify(err.message || 'Could not delete period', 'error');
                    } finally {
                        btn.disabled = false;
                    }
                    return;
                }

                const action = btn.getAttribute('data-period-action');
                if (action !== 'open') return;
                btn.disabled = true;
                try {
                    const res = await VarydianUtils.safeFetch(
                        `/api/periods/${encodeURIComponent(periodId)}/open`,
                        { method: 'POST' }
                    );
                    if (!res.success) throw new Error(res.error || 'Action failed');
                    await this.loadAll();
                    notify('Period opened for clerk uploads', 'success');
                } catch (err) {
                    notify(err.message || 'Could not open period', 'error');
                } finally {
                    btn.disabled = false;
                }
            });

            this.periodsEl?.addEventListener('change', (ev) => {
                if (ev.target.id === 'adminPeriodStatusFilter') {
                    this.periodStatusFilter = ev.target.value || 'all';
                    this.renderPeriods();
                }
            });

            this.usersEl?.addEventListener('change', (ev) => {
                if (ev.target.id === 'adminUserRoleFilter') {
                    this.userRoleFilter = ev.target.value || 'all';
                    this.renderUsers();
                }
                if (ev.target.id === 'adminUserStatusFilter') {
                    this.userStatusFilter = ev.target.value || 'all';
                    this.renderUsers();
                }
            });

            this.usersEl?.addEventListener('input', (ev) => {
                if (ev.target.id === 'adminUserSearch') {
                    this.userSearchQuery = ev.target.value.trim().toLowerCase();
                    this.renderUsers();
                }
            });

            this.usersEl?.addEventListener('click', async (ev) => {
                const deactivateBtn = ev.target.closest('[data-user-deactivate]');
                const activateBtn = ev.target.closest('[data-user-activate]');
                const btn = deactivateBtn || activateBtn;
                if (!btn) return;
                const userId = btn.getAttribute('data-user-deactivate') || btn.getAttribute('data-user-activate');
                if (!userId) return;

                if (activateBtn) {
                    btn.disabled = true;
                    try {
                        const res = await VarydianUtils.safeFetch(
                            `/api/admin/users/${encodeURIComponent(userId)}/activate`,
                            { method: 'POST' }
                        );
                        if (!res.success) throw new Error(res.error || 'Activate failed');
                        await this.loadAll();
                        notify('User reactivated', 'success');
                    } catch (err) {
                        notify(err.message || 'Failed to reactivate user', 'error');
                    } finally {
                        btn.disabled = false;
                    }
                    return;
                }

                const confirmed = await appConfirm(
                    'Deactivate user',
                    'Deactivate this user? They will no longer be able to log in. You can reactivate them later from this list.'
                );
                if (!confirmed) return;
                btn.disabled = true;
                try {
                    const res = await VarydianUtils.safeFetch(
                        `/api/admin/users/${encodeURIComponent(userId)}/deactivate`,
                        { method: 'POST' }
                    );
                    if (!res.success) throw new Error(res.error || 'Deactivate failed');
                    await this.loadAll();
                    notify('User deactivated', 'success');
                } catch (err) {
                    notify(err.message || 'Failed to deactivate user', 'error');
                } finally {
                    btn.disabled = false;
                }
            });
        }

        async loadAll() {
            await Promise.all([this.loadOverview(), this.loadPeriods(), this.loadUsers()]);
        }

        async loadOverview() {
            try {
                const res = await VarydianUtils.safeFetch('/api/admin/overview');
                if (!res.success) throw new Error(res.error || 'Overview failed');
                const stats = res.stats || {};
                this.overviewEl?.querySelectorAll('[data-stat]').forEach((el) => {
                    const key = el.getAttribute('data-stat');
                    if (key === 'migrations_ok') {
                        el.textContent = stats.migrations_ok ? 'OK' : 'Check';
                        el.classList.toggle('status-ok', !!stats.migrations_ok);
                        el.classList.toggle('status-warn', !stats.migrations_ok);
                        return;
                    }
                    el.textContent = stats[key] ?? '—';
                });
                this.renderMigrations(res.migrations || {});
            } catch (err) {
                if (this.migrationsEl) {
                    this.migrationsEl.innerHTML = `<p class="text-danger">${escapeHtml(err.message)}</p>`;
                }
            }
        }

        renderMigrations(report) {
            if (!this.migrationsEl) return;
            const probes = report.probes || [];
            const migrations = report.migrations || [];
            if (!probes.length && !migrations.length) {
                this.migrationsEl.innerHTML = `<p class="admin-migrations__empty text-muted">${escapeHtml(report.error || report.detail || 'No migration data')}</p>`;
                return;
            }

            const allOk = !!(report.all_applied || report.success);
            const bannerClass = allOk ? 'admin-migrations__banner--ok' : 'admin-migrations__banner--fail';
            const bannerIcon = allOk ? '✓' : '!';
            const bannerTitle = allOk ? 'All applied' : 'Action required';
            const bannerHint = allOk
                ? 'Schema probes and registered migrations look healthy.'
                : 'One or more checks failed — run the scripts in Supabase SQL editor.';

            const renderItem = (name, statusLabel, statusKind, detail) => {
                const itemClass = statusKind === 'ok' ? 'admin-migration-item--ok' : 'admin-migration-item--fail';
                const dot = statusKind === 'ok' ? '●' : '●';
                return `
                <li class="admin-migration-item ${itemClass}">
                    <span class="admin-migration-item__indicator" aria-hidden="true">${dot}</span>
                    <div class="admin-migration-item__body">
                        <div class="admin-migration-item__head">
                            <span class="admin-migration-item__name">${escapeHtml(name)}</span>
                            ${statusPill(statusLabel, statusKind)}
                        </div>
                        ${detail ? `<p class="admin-migration-item__detail">${escapeHtml(detail)}</p>` : ''}
                    </div>
                </li>`;
            };

            const probeHtml = probes.map((p) => renderItem(
                p.name || p.id || 'Probe',
                p.passed ? 'Pass' : 'Fail',
                p.passed ? 'ok' : 'fail',
                p.detail || '',
            )).join('');

            const migHtml = migrations.map((m) => renderItem(
                m.id || m.description || 'Migration',
                m.registered ? 'Applied' : 'Missing',
                m.registered ? 'ok' : 'fail',
                m.description && m.id ? m.description : '',
            )).join('');

            const groups = [];
            if (probes.length) {
                groups.push(`
                <section class="admin-migrations__group">
                    <h3 class="admin-migrations__group-title">Live probes</h3>
                    <ul class="admin-migration-list">${probeHtml}</ul>
                </section>`);
            }
            if (migrations.length) {
                groups.push(`
                <section class="admin-migrations__group">
                    <h3 class="admin-migrations__group-title">Registered migrations</h3>
                    <ul class="admin-migration-list">${migHtml}</ul>
                </section>`);
            }

            this.migrationsEl.innerHTML = `
                <div class="admin-migrations__banner ${bannerClass}">
                    <span class="admin-migrations__banner-icon" aria-hidden="true">${bannerIcon}</span>
                    <div class="admin-migrations__banner-text">
                        <strong class="admin-migrations__banner-title">${escapeHtml(bannerTitle)}</strong>
                        <p class="admin-migrations__banner-hint">${escapeHtml(bannerHint)}</p>
                    </div>
                </div>
                <div class="admin-migrations__groups">${groups.join('')}</div>`;
        }

        async loadPeriods() {
            if (!this.periodsEl) return;
            try {
                const res = await VarydianUtils.safeFetch('/api/admin/periods');
                if (!res.success) throw new Error(res.error || 'Load periods failed');
                this.periods = this.sortPeriodsChronologically(res.periods || []);
                this.renderPeriods();
            } catch (err) {
                this.periodsEl.innerHTML = `<p class="text-danger">${escapeHtml(err.message)}</p>`;
            }
        }

        sortPeriodsChronologically(periods) {
            return [...periods].sort((a, b) => {
                const aStart = String(a.start_date || '').slice(0, 10);
                const bStart = String(b.start_date || '').slice(0, 10);
                if (aStart !== bStart) {
                    return aStart.localeCompare(bStart);
                }
                return String(a.name || '').localeCompare(String(b.name || ''));
            });
        }

        filteredPeriods() {
            if (this.periodStatusFilter === 'all') return this.periods;
            return this.periods.filter((p) => String(p.status || 'draft').toLowerCase() === this.periodStatusFilter);
        }

        renderPeriods() {
            if (!this.periodsEl) return;
            const periods = this.filteredPeriods();
            if (!this.periods.length) {
                this.periodsEl.innerHTML = '<p class="admin-periods__empty text-muted">No reporting periods yet. Create one above to unblock Finance Clerks.</p>';
                return;
            }

            const filterBar = `
                <div class="admin-periods__toolbar">
                    <label class="admin-periods__filter" for="adminPeriodStatusFilter">
                        <span>Status</span>
                        <select id="adminPeriodStatusFilter" class="admin-periods__filter-select">
                            <option value="all"${this.periodStatusFilter === 'all' ? ' selected' : ''}>All periods</option>
                            <option value="draft"${this.periodStatusFilter === 'draft' ? ' selected' : ''}>Draft</option>
                            <option value="open"${this.periodStatusFilter === 'open' ? ' selected' : ''}>Open</option>
                            <option value="closed"${this.periodStatusFilter === 'closed' ? ' selected' : ''}>Closed</option>
                        </select>
                    </label>
                    <span class="admin-periods__count">${periods.length} of ${this.periods.length} shown</span>
                </div>`;

            if (!periods.length) {
                this.periodsEl.innerHTML = `${filterBar}<p class="admin-periods__empty text-muted">No periods match this filter.</p>`;
                return;
            }

            this.periodsEl.innerHTML = `${filterBar}
                <div class="admin-period-grid">
                    ${periods.map((p) => this.renderPeriodCard(p)).join('')}
                </div>`;
        }

        renderPeriodCard(p) {
            const locked = p.is_locked || p.locked || (p.metadata && p.metadata.is_locked);
            const rawStatus = String(p.status || 'draft').toLowerCase();
            const status = locked ? 'closed' : rawStatus;
            const required = Number(p.required_uploads || EXPECTED_REQUIRED_UPLOADS);
            const uploaded = Number(p.uploaded_count || 0);
            const progress = Math.min(100, Math.round(Number(p.completion_percentage) || ((uploaded / required) * 100) || 0));
            const statusLabel = locked ? 'Closed' : status.charAt(0).toUpperCase() + status.slice(1);
            const statusKind = locked ? 'muted' : (status === 'open' ? 'ok' : (status === 'closed' ? 'muted' : 'warn'));

            let actions = '';
            if (locked) {
                actions = '<span class="admin-period-card__locked-note">CFO locked — no admin changes</span>';
            } else {
                if (status !== 'open') {
                    actions += `<button type="button" class="btn btn-primary btn-sm" data-period-action="open" data-period-id="${escapeHtml(p.id)}">Open for uploads</button>`;
                }
                actions += `<button type="button" class="btn btn-secondary btn-sm admin-btn-danger" data-period-delete data-period-id="${escapeHtml(p.id)}">Delete</button>`;
            }

            const duplicateNote = p.is_duplicate
                ? `<p class="admin-period-card__warn">${Number(p.extra_copy_count || 1)} legacy duplicate row${Number(p.extra_copy_count || 1) === 1 ? '' : 's'} for this month. Activity is tracked on this card.</p>`
                : '';

            const mergeDuplicateBtn = p.is_duplicate
                ? `<button type="button" class="btn btn-secondary btn-sm" data-period-merge data-period-id="${escapeHtml(p.id)}">Merge duplicate rows</button>`
                : '';

            const docTypes = (p.metadata && p.metadata.uploaded_document_types) || [];
            const docHint = docTypes.length
                ? `<span class="admin-period-card__docs">${escapeHtml(docTypes.join(', ').replace(/_/g, ' '))}</span>`
                : '';

            return `
                <article class="admin-period-card admin-period-card--${escapeHtml(status)}" data-status="${escapeHtml(status)}">
                    <header class="admin-period-card__head">
                        <h3 class="admin-period-card__title">${escapeHtml(p.name)}</h3>
                        <div class="admin-period-card__badges">
                            ${statusPill(statusLabel, statusKind)}
                            ${locked ? statusPill('CFO locked', 'fail') : statusPill('Editable', 'ok')}
                        </div>
                    </header>
                    ${duplicateNote}
                    ${p.description ? `<p class="admin-period-card__desc text-muted">${escapeHtml(p.description)}</p>` : ''}
                    <ul class="admin-period-card__meta">
                        <li><span aria-hidden="true">📅</span> ${formatDate(p.start_date)} → ${formatDate(p.end_date)}</li>
                        <li><span aria-hidden="true">⏰</span> Due ${formatDate(p.due_date)}</li>
                        <li><span aria-hidden="true">📄</span> ${uploaded}/${required} documents submitted</li>
                    </ul>
                    ${docHint}
                    <div class="admin-period-card__progress">
                        <div class="admin-period-card__progress-label">
                            <span>Upload progress</span>
                            <span>${progress}%</span>
                        </div>
                        <div class="admin-period-card__progress-bar" role="progressbar" aria-valuenow="${progress}" aria-valuemin="0" aria-valuemax="100">
                            <div class="admin-period-card__progress-fill" style="width: ${progress}%;"></div>
                        </div>
                    </div>
                    <footer class="admin-period-card__actions">${mergeDuplicateBtn}${actions}</footer>
                </article>`;
        }

        async loadUsers() {
            if (!this.usersEl) return;
            try {
                const res = await VarydianUtils.safeFetch('/api/admin/users');
                if (!res.success) throw new Error(res.error || 'Load users failed');
                this.users = res.users || [];
                this.renderUsers();
            } catch (err) {
                this.usersEl.innerHTML = `<p class="text-danger">${escapeHtml(err.message)}</p>`;
            }
        }

        filteredUsers() {
            return this.users.filter((u) => {
                const role = String(u.role || '').toUpperCase();
                const active = u.is_active !== false;
                const name = String(u.full_name || u.username || '').toLowerCase();
                const email = String(u.email || u.username || '').toLowerCase();
                const q = this.userSearchQuery;

                if (this.userRoleFilter !== 'all' && role !== this.userRoleFilter) return false;
                if (this.userStatusFilter === 'active' && !active) return false;
                if (this.userStatusFilter === 'inactive' && active) return false;
                if (q && !name.includes(q) && !email.includes(q)) return false;
                return true;
            });
        }

        renderUsers() {
            if (!this.usersEl) return;
            const users = this.filteredUsers();
            if (!this.users.length) {
                this.usersEl.innerHTML = '<p class="admin-users__empty text-muted">No users found.</p>';
                return;
            }

            const roleOptions = Object.entries(ROLE_LABELS).map(([value, label]) =>
                `<option value="${escapeHtml(value)}"${this.userRoleFilter === value ? ' selected' : ''}>${escapeHtml(label)}</option>`
            ).join('');

            const countText = `${users.length} of ${this.users.length} shown`;
            const gridHtml = users.length
                ? `<div class="admin-user-grid">${users.map((u) => this.renderUserCard(u)).join('')}</div>`
                : '<p class="admin-users__empty text-muted">No users match this filter.</p>';

            const existingToolbar = this.usersEl.querySelector('.admin-users__toolbar');
            if (existingToolbar) {
                const countEl = existingToolbar.querySelector('.admin-users__count');
                if (countEl) countEl.textContent = countText;
                const roleSelect = existingToolbar.querySelector('#adminUserRoleFilter');
                const statusSelect = existingToolbar.querySelector('#adminUserStatusFilter');
                if (roleSelect) roleSelect.value = this.userRoleFilter;
                if (statusSelect) statusSelect.value = this.userStatusFilter;
                const next = existingToolbar.nextElementSibling;
                if (next) {
                    next.outerHTML = gridHtml;
                } else {
                    existingToolbar.insertAdjacentHTML('afterend', gridHtml);
                }
                return;
            }

            const toolbar = `
                <div class="admin-users__toolbar">
                    <label class="admin-users__filter" for="adminUserSearch">
                        <span>Search</span>
                        <input type="search" id="adminUserSearch" class="admin-users__search" placeholder="Name or email" value="${escapeHtml(this.userSearchQuery)}" autocomplete="off">
                    </label>
                    <label class="admin-users__filter" for="adminUserRoleFilter">
                        <span>Role</span>
                        <select id="adminUserRoleFilter" class="admin-users__filter-select">
                            <option value="all"${this.userRoleFilter === 'all' ? ' selected' : ''}>All roles</option>
                            ${roleOptions}
                        </select>
                    </label>
                    <label class="admin-users__filter" for="adminUserStatusFilter">
                        <span>Status</span>
                        <select id="adminUserStatusFilter" class="admin-users__filter-select">
                            <option value="all"${this.userStatusFilter === 'all' ? ' selected' : ''}>All</option>
                            <option value="active"${this.userStatusFilter === 'active' ? ' selected' : ''}>Active</option>
                            <option value="inactive"${this.userStatusFilter === 'inactive' ? ' selected' : ''}>Inactive</option>
                        </select>
                    </label>
                    <span class="admin-users__count">${countText}</span>
                </div>`;

            this.usersEl.innerHTML = `${toolbar}${gridHtml}`;
        }

        roleSlug(role) {
            return String(role || 'unknown').toLowerCase().replace(/_/g, '-');
        }

        renderUserCard(u) {
            const active = u.is_active !== false;
            const isSelf = String(u.id) === String(window.currentUserId || '');
            const role = String(u.role || '').toUpperCase();
            const roleLabel = ROLE_LABELS[role] || role.replace(/_/g, ' ') || '—';
            const roleIcon = ROLE_ICONS[role] || '👤';
            const email = u.email || u.username || '—';
            const name = u.full_name || u.username || '—';
            const slug = this.roleSlug(role);

            let actions = '';
            if (isSelf) {
                actions = '<span class="admin-user-card__self-note">Signed in as you</span>';
            } else if (active) {
                actions = `<button type="button" class="btn btn-secondary btn-sm admin-btn-danger" data-user-deactivate="${escapeHtml(u.id)}">Deactivate</button>`;
            } else {
                actions = `<button type="button" class="btn btn-primary btn-sm" data-user-activate="${escapeHtml(u.id)}">Reactivate</button>`;
            }

            return `
                <article class="admin-user-card admin-user-card--${escapeHtml(slug)}${active ? '' : ' admin-user-card--inactive'}">
                    <div class="admin-user-card__avatar" aria-hidden="true">${roleIcon}</div>
                    <header class="admin-user-card__head">
                        <h3 class="admin-user-card__name">${escapeHtml(name)}</h3>
                        <div class="admin-user-card__badges">
                            <span class="admin-user-card__role">${escapeHtml(roleLabel)}</span>
                            ${active ? statusPill('Active', 'ok') : statusPill('Inactive', 'muted')}
                        </div>
                    </header>
                    <p class="admin-user-card__email">${escapeHtml(email)}</p>
                    <footer class="admin-user-card__actions">${actions}</footer>
                </article>`;
        }
    }

    document.addEventListener('DOMContentLoaded', () => new AdminPage());
})();
