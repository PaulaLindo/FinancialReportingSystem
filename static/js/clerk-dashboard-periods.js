/**
 * Clerk dashboard — load all closed reporting periods on demand.
 */
(function () {
    function escapeHtml(value) {
        return String(value ?? '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    function formatDate(value) {
        if (!value) return '—';
        if (window.VarydianUtils && typeof VarydianUtils.formatDateTime === 'function') {
            return VarydianUtils.formatDateTime(value) || String(value).slice(0, 10);
        }
        return String(value).slice(0, 10);
    }

    function renderTaskCard(period) {
        const status = String(period.status || 'closed').toLowerCase();
        const isOpen = status === 'open' && !period.is_locked;
        const isLocked = !!period.is_locked;
        const showUrgent = !!(period.is_urgent && isOpen);
        const progress = Math.min(100, Math.round(Number(period.completion_percentage) || 0));
        const progressWidth = Math.min(progress, 100);
        const uploaded = Number(period.uploaded_count) || 0;
        const required = Number(period.required_uploads) || 3;
        const slotsRemaining = Number(period.upload_slots_remaining) || 0;

        let actionHtml = '';
        if (isOpen && slotsRemaining > 0) {
            actionHtml = `
                <a href="/upload?period=${encodeURIComponent(period.id)}" class="btn-upload btn-upload--primary">
                    <span aria-hidden="true">📤</span>
                    ${uploaded > 0 ? 'Upload next document' : 'Upload document'}
                </a>`;
        } else if (isOpen) {
            actionHtml = `
                <button type="button" class="btn-upload btn-upload--done" disabled>
                    <span aria-hidden="true">✅</span>
                    All documents uploaded
                </button>`;
        } else if (isLocked) {
            actionHtml = `
                <button type="button" class="btn-upload btn-upload--locked" disabled>
                    <span aria-hidden="true">🔒</span>
                    Locked by CFO
                </button>`;
        } else {
            actionHtml = `
                <button type="button" class="btn-upload btn-upload--closed" disabled>
                    <span aria-hidden="true">📁</span>
                    No new uploads
                </button>`;
        }

        const viewSubmissions = uploaded > 0
            ? `<a href="/submission-history" class="btn-view">View submissions</a>`
            : '';

        let badgeHtml = '';
        if (isLocked) {
            badgeHtml = '<span class="task-badge task-badge--locked">CFO locked</span>';
        } else if (isOpen) {
            badgeHtml = '<span class="task-badge task-badge--open">Open</span>';
        } else {
            badgeHtml = '<span class="task-badge task-badge--closed">Closed</span>';
        }
        if (showUrgent) {
            badgeHtml += '<span class="task-badge task-badge--urgent">Due soon</span>';
        }

        const lastUpload = period.last_upload
            ? `<div class="task-info-item task-info-item--muted">
                    <dt class="task-info-icon" aria-hidden="true">🕐</dt>
                    <dd>Last upload ${escapeHtml(formatDate(period.last_upload))}</dd>
               </div>`
            : '';

        const cardClasses = [
            'task-card',
            `task-card--${status}`,
            isLocked ? 'task-card--locked' : '',
            showUrgent ? 'task-card--urgent' : '',
        ].filter(Boolean).join(' ');

        return `
            <article class="${cardClasses}"
                 data-period-id="${escapeHtml(period.id)}"
                 data-status="${escapeHtml(status)}"
                 data-period-kind="closed"
                 data-urgency="${showUrgent ? 'urgent' : 'normal'}">
                <div class="task-header">
                    <div class="task-period">${escapeHtml(period.name)}</div>
                    <div class="task-badges">${badgeHtml}</div>
                </div>
                <div class="task-details">
                    <dl class="task-info">
                        <div class="task-info-item">
                            <dt class="task-info-icon" aria-hidden="true">📅</dt>
                            <dd>${escapeHtml(formatDate(period.start_date))} – ${escapeHtml(formatDate(period.end_date))}</dd>
                        </div>
                        <div class="task-info-item">
                            <dt class="task-info-icon" aria-hidden="true">📊</dt>
                            <dd>${uploaded}/${required} documents</dd>
                        </div>
                        <div class="task-info-item">
                            <dt class="task-info-icon" aria-hidden="true">⏰</dt>
                            <dd>Due ${escapeHtml(formatDate(period.due_date))}</dd>
                        </div>
                        ${lastUpload}
                    </dl>
                </div>
                <div class="task-progress">
                    <div class="task-progress__label">
                        <span class="progress-text">Upload progress</span>
                        <span class="progress-value">${progress}%</span>
                    </div>
                    <div class="task-progress__bar task-progress__bar--${escapeHtml(status)}" role="progressbar" aria-valuenow="${progress}" aria-valuemin="0" aria-valuemax="100" aria-label="Upload progress for ${escapeHtml(period.name)}">
                        <div class="task-progress__fill" style="width: ${progressWidth}%;"></div>
                    </div>
                </div>
                <div class="task-actions">
                    ${actionHtml}
                    ${viewSubmissions}
                </div>
            </article>`;
    }

    function setClosedPanelExpanded(expanded) {
        const closedToggle = document.getElementById('clerkClosedPeriodsToggle');
        const closedPanel = document.getElementById('clerkClosedPeriodsPanel');
        if (!closedToggle || !closedPanel) return;
        closedToggle.setAttribute('aria-expanded', expanded ? 'true' : 'false');
        closedPanel.classList.toggle('is-expanded', expanded);
        closedPanel.hidden = !expanded;
        closedToggle.textContent = expanded ? 'Hide closed periods' : 'Show closed periods';
    }

    function ensureClosedPanelVisible() {
        setClosedPanelExpanded(true);
    }

    function bindClosedPeriodsToggle() {
        const closedToggle = document.getElementById('clerkClosedPeriodsToggle');
        const closedPanel = document.getElementById('clerkClosedPeriodsPanel');
        if (!closedToggle || !closedPanel || closedToggle.dataset.bound === 'true') return;
        closedToggle.dataset.bound = 'true';

        closedToggle.addEventListener('click', (ev) => {
            ev.preventDefault();
            ev.stopPropagation();
            const expanded = closedToggle.getAttribute('aria-expanded') === 'true';
            setClosedPanelExpanded(!expanded);
        });
    }

    document.addEventListener('DOMContentLoaded', () => {
        bindClosedPeriodsToggle();

        const btn = document.getElementById('clerkShowAllClosedBtn');
        const closedGrid = document.getElementById('clerkClosedPeriodsGrid');
        const toolbar = document.getElementById('clerkClosedPeriodsToolbar');
        if (!btn || !closedGrid) return;

        btn.addEventListener('click', async () => {
            btn.disabled = true;
            const originalLabel = btn.textContent;
            btn.textContent = 'Loading…';

            try {
                const res = await fetch('/api/periods/dashboard?closed_scope=all', { credentials: 'same-origin' });
                const data = await res.json();
                if (!data.success) throw new Error(data.error || 'Could not load closed periods');

                const existingIds = new Set(
                    [...closedGrid.querySelectorAll('.task-card[data-period-id]')]
                        .map((el) => el.getAttribute('data-period-id'))
                        .filter(Boolean),
                );

                const closedPeriods = (data.periods || []).filter((p) => {
                    const status = String(p.status || '').toLowerCase();
                    return status !== 'open' || p.is_locked;
                });

                const toAppend = closedPeriods.filter((p) => !existingIds.has(String(p.id)));
                if (toAppend.length) {
                    closedGrid.insertAdjacentHTML('beforeend', toAppend.map(renderTaskCard).join(''));
                }

                ensureClosedPanelVisible();

                const closedCount = closedGrid.querySelectorAll('.task-card').length;
                if (toolbar) {
                    toolbar.innerHTML = `
                        <p class="clerk-closed-periods-toolbar__note text-muted clerk-closed-periods-toolbar__note--all">
                            Showing all ${closedCount} closed period(s).
                        </p>`;
                }

                document.dispatchEvent(new Event('clerk-periods-expanded'));
            } catch (err) {
                btn.disabled = false;
                btn.textContent = originalLabel;
                if (window.VarydianUtils && typeof VarydianUtils.showToast === 'function') {
                    VarydianUtils.showToast(err.message || 'Could not load closed periods', 'error');
                }
            }
        });
    });
})();
