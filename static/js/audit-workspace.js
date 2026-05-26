/** Auditor workspace — finalized session picker, read-only review, audit CSV. */
(function () {
    if (!window.location.pathname.includes('/audit')) return;

    const state = { sessionId: null, documentType: null };

    function qs(sel) {
        return document.querySelector(sel);
    }

    function toast(msg, isError) {
        if (window.VarydianUtils?.showToast) {
            VarydianUtils.showToast(msg, isError ? 'error' : 'success');
            return;
        }
        console.warn('[audit]', msg);
    }

    function selectionPayload() {
        const select = qs('#auditSessionSelect');
        if (!select?.value) return null;
        const [sessionId, documentType] = select.value.split('|');
        if (!sessionId || !documentType) return null;
        return { session_id: sessionId, document_type: documentType };
    }

    function updateSelection() {
        const payload = selectionPayload();
        state.sessionId = payload?.session_id || null;
        state.documentType = payload?.document_type || null;

        const notice = qs('[data-audit-selection-notice]');
        if (notice) {
            notice.textContent = payload
                ? `Selected: ${payload.document_type.replace(/_/g, ' ')} — ${payload.session_id.slice(0, 8)}…`
                : 'Select a submission to enable audit actions.';
        }

        qs('[data-audit-open-review]')?.toggleAttribute('disabled', !payload);
        qs('[data-audit-export-csv]')?.toggleAttribute('disabled', !payload);
    }

    async function loadSessions() {
        const select = qs('#auditSessionSelect');
        if (!select) return;
        try {
            const res = await VarydianUtils.safeFetch('/api/export/sessions?limit=200');
            const sessions = res.sessions || [];
            if (!sessions.length) {
                select.innerHTML = '<option value="">No finalized submissions in locked periods</option>';
                return;
            }
            select.innerHTML = '<option value="">Select a submission…</option>' + sessions.map((s) => {
                const label = [
                    s.period_name || 'Period',
                    (s.document_type || '').replace(/_/g, ' '),
                    s.filename || s.session_id?.slice(0, 8),
                ].filter(Boolean).join(' · ');
                return `<option value="${s.session_id}|${s.document_type}">${label}</option>`;
            }).join('');
        } catch (err) {
            select.innerHTML = '<option value="">Could not load submissions</option>';
            toast(err.message || 'Failed to load submissions', true);
        }
    }

    async function loadExportLog() {
        const list = qs('[data-audit-export-log]');
        if (!list) return;
        try {
            const res = await VarydianUtils.safeFetch('/api/export/log?limit=20');
            const events = (res.events || []).filter((e) => e.export_format === 'csv');
            if (!events.length) {
                list.innerHTML = '<p class="text-muted">No CSV exports recorded yet.</p>';
                return;
            }
            list.innerHTML = events.map((e) => `
                <div class="audit-export-log__row">
                    <strong>${(e.document_type || '').replace(/_/g, ' ')}</strong>
                    <span class="text-muted">${e.period_name || e.session_id?.slice(0, 8) || '—'}</span>
                    <span class="text-muted">${VarydianUtils.formatDateTime?.(e.created_at) || e.created_at || '—'}</span>
                </div>`).join('');
        } catch (_e) {
            list.innerHTML = '<p class="text-muted">Export log unavailable.</p>';
        }
    }

    function openReview() {
        const payload = selectionPayload();
        if (!payload) {
            toast('Select a finalized submission first.', true);
            return;
        }
        const params = new URLSearchParams({
            review: 'statement',
            transaction: payload.session_id,
            type: payload.document_type,
            returnTo: '/audit',
        });
        window.location.href = `/approvals?${params.toString()}`;
    }

    async function exportCsv(btn) {
        const payload = selectionPayload();
        if (!payload) {
            toast('Select a finalized submission first.', true);
            return;
        }
        const original = btn.textContent;
        btn.disabled = true;
        btn.textContent = 'Exporting…';
        try {
            const res = await fetch('/api/export/csv', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'same-origin',
                body: JSON.stringify(payload),
            });
            if (!res.ok) {
                const data = await res.json().catch(() => ({}));
                throw new Error(data.error || 'CSV export failed');
            }
            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `audit_${payload.document_type}_${payload.session_id.slice(0, 8)}.csv`;
            a.click();
            URL.revokeObjectURL(url);
            toast('Audit CSV downloaded.');
            loadExportLog();
        } catch (err) {
            toast(err.message || 'CSV export failed', true);
        } finally {
            btn.disabled = !selectionPayload();
            btn.textContent = original;
        }
    }

    document.addEventListener('DOMContentLoaded', () => {
        qs('#auditSessionSelect')?.addEventListener('change', updateSelection);
        qs('[data-audit-open-review]')?.addEventListener('click', openReview);
        qs('[data-audit-export-csv]')?.addEventListener('click', (e) => exportCsv(e.currentTarget));
        loadSessions().then(updateSelection);
        loadExportLog();
    });
})();
