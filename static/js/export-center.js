/**
 * Export Center — session picker and wired Excel / CSV / archive / PDF actions.
 */
(function (global) {
    const state = {
        sessions: [],
        selectedSessionId: null,
        selectedDocumentType: null,
        readOnly: false,
        readOnlyPdfLog: false,
        canGeneratePdf: false,
        canExport: false,
        canExportAudit: false,
    };

    function qs(sel) {
        return document.querySelector(sel);
    }

    function toast(msg, isError) {
        if (global.VarydianUtils && VarydianUtils.showToast) {
            VarydianUtils.showToast(msg, isError ? 'error' : 'success');
            return;
        }
        window.alert(msg);
    }

    function setBusy(btn, busy, label) {
        if (!btn) return;
        btn.disabled = !!busy;
        if (label) btn.textContent = label;
    }

    function readUrlSessionContext() {
        const params = new URLSearchParams(window.location.search);
        const sessionId = params.get('session_id');
        const documentType = params.get('document_type');
        if (!sessionId || !documentType) return null;
        return { session_id: sessionId, document_type: documentType };
    }

    function selectionPayload() {
        const select = qs('#exportSessionSelect');
        if (!select) {
            return readUrlSessionContext();
        }
        const value = select.value;
        if (!value) {
            return null;
        }
        const [sessionId, documentType] = value.split('|');
        if (sessionId && documentType) {
            return { session_id: sessionId, document_type: documentType };
        }
        return null;
    }

    function updateSelection() {
        const payload = selectionPayload();
        state.selectedSessionId = payload ? payload.session_id : null;
        state.selectedDocumentType = payload ? payload.document_type : null;

        if (global.PdfPeriodGate) {
            if (payload) {
                PdfPeriodGate.saveContext(payload);
                PdfPeriodGate.init(payload);
            } else {
                PdfPeriodGate.clearContext();
                PdfPeriodGate.init({ session_id: null, document_type: null });
            }
        }

        const notice = qs('[data-export-selection-notice]');
        if (notice) {
            if (!payload) {
                notice.textContent = 'Select a finalized submission to export.';
            } else {
                notice.textContent = `Selected: ${payload.document_type.replace(/_/g, ' ')} — ${payload.session_id.slice(0, 8)}…`;
            }
        }

        refreshPdfActions();
        refreshExportActions();
        loadExportLog();
    }

    function formatLogTimestamp(value) {
        if (global.VarydianUtils && VarydianUtils.formatDateTime) {
            return VarydianUtils.formatDateTime(value) || '—';
        }
        return value || '—';
    }

    function renderExportLog(events, filtered) {
        const list = qs('[data-export-history-list]');
        const subtitle = qs('[data-export-log-subtitle]');
        if (!list) return;

        if (subtitle) {
            if (state.readOnlyPdfLog) {
                subtitle.textContent = filtered
                    ? 'PDF activity for the selected submission.'
                    : 'PDF generation and download activity for finalized submissions.';
            } else {
                subtitle.textContent = filtered
                    ? 'Export activity for the selected submission.'
                    : 'Recent export activity across finalized submissions.';
            }
        }

        if (!events || !events.length) {
            const emptyMsg = state.readOnlyPdfLog
                ? 'No PDF exports recorded yet. Once the CFO generates an official PDF, activity will appear here.'
                : 'No exports recorded yet. Generate or download a file above to see activity here.';
            list.innerHTML = `<p class="export-history-empty text-muted">${emptyMsg}</p>`;
            return;
        }

        list.innerHTML = events
            .map(
                (row) => `
            <div class="export-history-item">
                <div class="export-history-date">${formatLogTimestamp(row.timestamp)}</div>
                <div class="export-history-title">${row.title || row.export_format || 'Export'}</div>
                <div class="export-history-status">${row.actor_label || row.user_name || '—'}</div>
            </div>`
            )
            .join('');
    }

    async function loadExportLog() {
        const list = qs('[data-export-history-list]');
        if (!list) return;

        const payload = selectionPayload();
        const params = new URLSearchParams({ limit: '25' });
        if (payload && payload.session_id) {
            params.set('session_id', payload.session_id);
        }

        try {
            const res = await fetch(`/api/export/log?${params.toString()}`, { credentials: 'same-origin' });
            const data = await res.json();
            if (!res.ok || !data.success) {
                throw new Error(data.error || 'Could not load export log');
            }
            renderExportLog(data.events || [], !!payload);
        } catch (err) {
            list.innerHTML = `<p class="export-history-empty text-muted">Could not load export log: ${err.message || 'error'}</p>`;
        }
    }

    function refreshExportActions() {
        const payload = selectionPayload();
        document.querySelectorAll('[data-export-action]').forEach((btn) => {
            btn.disabled = !payload;
        });
    }

    function setFmPdfDownloadNotice(message, show) {
        const wrap = qs('[data-pdf-gate-wrap][data-pdf-gate-mode="download"]');
        if (!wrap) return;
        const notice = wrap.querySelector('[data-pdf-gate-notice]');
        if (!notice) return;
        if (show && message) {
            notice.textContent = message;
            notice.classList.remove('pdf-gate-notice--hidden');
            wrap.classList.add('pdf-gate-wrap--blocked');
            wrap.classList.remove('pdf-gate-wrap--allowed');
        } else if (!message) {
            notice.classList.add('pdf-gate-notice--hidden');
            notice.textContent = '';
        }
    }

    async function refreshPdfActions() {
        const payload = selectionPayload();
        const downloadBtn = qs('[data-export-download-pdf]');
        const generateBtn = qs('[data-export-generate-pdf]');
        if (!payload) {
            if (downloadBtn) downloadBtn.disabled = true;
            if (generateBtn) generateBtn.disabled = true;
            setFmPdfDownloadNotice('', false);
            return;
        }

        if (state.canGeneratePdf && generateBtn) {
            generateBtn.disabled = false;
        }

        if (downloadBtn && state.canGeneratePdf === false && state.readOnly) {
            try {
                const q = new URLSearchParams(payload);
                const res = await fetch(`/api/export/session-pdf?${q.toString()}`, { credentials: 'same-origin' });
                const data = await res.json();
                if (data.success && data.found && data.download_url) {
                    downloadBtn.disabled = false;
                    downloadBtn.dataset.downloadUrl = data.download_url;
                    setFmPdfDownloadNotice('', false);
                } else {
                    downloadBtn.disabled = true;
                    downloadBtn.removeAttribute('data-download-url');
                    setFmPdfDownloadNotice(
                        'No official PDF has been generated for this submission yet. Ask the CFO to generate one from Export Center.',
                        true
                    );
                }
            } catch (_e) {
                downloadBtn.disabled = true;
                setFmPdfDownloadNotice(
                    'Could not verify whether a PDF exists for this submission. Try again or contact the CFO.',
                    true
                );
            }
        }
    }

    async function loadSessions() {
        const select = qs('#exportSessionSelect');
        if (!select) return;
        select.innerHTML = '<option value="">Loading finalized sessions…</option>';
        try {
            const res = await fetch('/api/export/sessions?limit=50', { credentials: 'same-origin' });
            const data = await res.json();
            if (!res.ok || !data.success) {
                throw new Error(data.error || 'Could not load sessions');
            }
            state.sessions = data.sessions || [];
            const options = ['<option value="">— Select a finalized submission —</option>'];
            state.sessions.forEach((row) => {
                const label = [
                    (row.document_type || 'document').replace(/_/g, ' '),
                    row.period_name || 'Period',
                    row.filename || row.session_id.slice(0, 8),
                ].join(' · ');
                options.push(
                    `<option value="${row.session_id}|${row.document_type}">${label}</option>`
                );
            });

            const params = new URLSearchParams(window.location.search);
            const sid = params.get('session_id');
            const dtype = params.get('document_type');
            if (sid && dtype) {
                const key = `${sid}|${dtype}`;
                const inList = state.sessions.some(
                    (row) => row.session_id === sid && row.document_type === dtype
                );
                if (!inList) {
                    options.push(
                        `<option value="${key}">Linked submission · ${dtype.replace(/_/g, ' ')} · ${sid.slice(0, 8)}…</option>`
                    );
                }
            }

            if (options.length === 1 && !sid) {
                select.innerHTML = '<option value="">No finalized exports available yet</option>';
                updateSelection();
                return;
            }

            select.innerHTML = options.join('');

            if (sid && dtype) {
                select.value = `${sid}|${dtype}`;
            }
            updateSelection();
        } catch (err) {
            const urlCtx = readUrlSessionContext();
            if (urlCtx) {
                const key = `${urlCtx.session_id}|${urlCtx.document_type}`;
                select.innerHTML = [
                    '<option value="">— Select a finalized submission —</option>',
                    `<option value="${key}">Linked submission · ${urlCtx.document_type.replace(/_/g, ' ')} · ${urlCtx.session_id.slice(0, 8)}…</option>`,
                ].join('');
                select.value = key;
                updateSelection();
                return;
            }
            select.innerHTML = `<option value="">Error: ${err.message || 'load failed'}</option>`;
        }
    }

    async function postDownload(url, payload, btn, busyLabel, idleLabel) {
        const body = payload || selectionPayload();
        if (!body) {
            toast('Select a finalized submission first.', true);
            return;
        }
        setBusy(btn, true, busyLabel);
        try {
            const res = await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'same-origin',
                body: JSON.stringify(body),
            });
            if (!res.ok) {
                const errData = await res.json().catch(() => ({}));
                throw new Error(errData.error || `Export failed (${res.status})`);
            }
            const blob = await res.blob();
            const disposition = res.headers.get('Content-Disposition') || '';
            const match = disposition.match(/filename="?([^";]+)"?/i);
            const filename = match ? match[1] : 'export.dat';
            const link = document.createElement('a');
            link.href = URL.createObjectURL(blob);
            link.download = filename;
            document.body.appendChild(link);
            link.click();
            link.remove();
            toast('Download started.');
            await loadExportLog();
        } catch (err) {
            toast(err.message || 'Export failed.', true);
        } finally {
            setBusy(btn, false, idleLabel);
        }
    }

    async function downloadPdfFile(url, btn, idleLabel) {
        if (!url) {
            toast('No PDF found for this session. Ask the CFO to generate one.', true);
            return false;
        }
        if (btn) setBusy(btn, true, 'Downloading…');
        try {
            const res = await fetch(url, { credentials: 'same-origin' });
            if (!res.ok) {
                const errData = await res.json().catch(() => ({}));
                throw new Error(errData.error || `Download failed (${res.status})`);
            }
            const blob = await res.blob();
            const disposition = res.headers.get('Content-Disposition') || '';
            const match = disposition.match(/filename="?([^";]+)"?/i);
            const filename = match ? match[1] : 'report.pdf';
            const link = document.createElement('a');
            const objectUrl = URL.createObjectURL(blob);
            link.href = objectUrl;
            link.download = filename;
            document.body.appendChild(link);
            link.click();
            link.remove();
            URL.revokeObjectURL(objectUrl);
            toast('Download started.');
            await loadExportLog();
            return true;
        } catch (err) {
            toast(err.message || 'Download failed.', true);
            return false;
        } finally {
            if (btn) setBusy(btn, false, idleLabel || 'Download PDF');
        }
    }

    async function generatePdf(btn) {
        const body = selectionPayload();
        if (!body) {
            toast('Select a finalized submission first.', true);
            return;
        }
        setBusy(btn, true, 'Generating…');
        try {
            const res = await fetch('/api/export/generate-pdf', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'same-origin',
                body: JSON.stringify(body),
            });
            const data = await res.json();
            if (!res.ok || !data.success) {
                throw new Error(data.error || 'PDF generation failed');
            }
            toast('PDF generated.');
            if (data.download_url) {
                await downloadPdfFile(data.download_url, null, null);
            } else {
                await loadExportLog();
            }
            await refreshPdfActions();
        } catch (err) {
            toast(err.message || 'PDF generation failed.', true);
        } finally {
            setBusy(btn, false, 'Generate PDF');
        }
    }

    function bind() {
        qs('#exportSessionSelect')?.addEventListener('change', updateSelection);

        qs('[data-export-excel]')?.addEventListener('click', (e) => {
            postDownload('/api/export/excel', null, e.currentTarget, 'Exporting…', 'Export to Excel');
        });
        qs('[data-export-csv]')?.addEventListener('click', (e) => {
            postDownload('/api/export/csv', null, e.currentTarget, 'Exporting…', 'Export CSV');
        });
        qs('[data-export-archive]')?.addEventListener('click', (e) => {
            postDownload('/api/export/archive', null, e.currentTarget, 'Building…', 'Download Archive');
        });
        qs('[data-export-generate-pdf]')?.addEventListener('click', (e) => {
            generatePdf(e.currentTarget);
        });
        qs('[data-export-download-pdf]')?.addEventListener('click', (e) => {
            downloadPdfFile(e.currentTarget.dataset.downloadUrl, e.currentTarget, 'Download PDF');
        });
    }

    function init(options) {
        const opts = options || {};
        state.readOnly = !!opts.readOnly;
        state.readOnlyPdfLog = !!opts.readOnlyPdfLog;
        state.canGeneratePdf = !!opts.canGeneratePdf;
        state.canExport = !!opts.canExport;
        state.canExportAudit = !!opts.canExportAudit;
        bind();
        const urlCtx = readUrlSessionContext();
        if (urlCtx && global.PdfPeriodGate) {
            global.PdfPeriodGate.init(urlCtx);
        } else if (global.PdfPeriodGate) {
            global.PdfPeriodGate.init({ session_id: null, document_type: null });
        }
        loadSessions();
        loadExportLog();
    }

    global.ExportCenter = { init };
})(typeof window !== 'undefined' ? window : globalThis);
