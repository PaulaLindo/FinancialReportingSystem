/**
 * Gate PDF actions until the reporting period is locked (CFO finalized).
 */
(function (global) {
    const STORAGE_KEY = 'varydianPdfSessionContext';

    function readContext(overrides) {
        const o = overrides || {};
        let stored = {};
        try {
            stored = JSON.parse(sessionStorage.getItem(STORAGE_KEY) || '{}');
        } catch (_e) {
            stored = {};
        }
        const params = new URLSearchParams(global.location.search);
        const pick = (key) => {
            if (Object.prototype.hasOwnProperty.call(o, key)) {
                return o[key] || null;
            }
            return stored[key] || params.get(key) || null;
        };
        return {
            session_id: pick('session_id'),
            document_type: pick('document_type'),
            period_id: pick('period_id'),
        };
    }

    function clearContext() {
        try {
            sessionStorage.removeItem(STORAGE_KEY);
        } catch (_e) {
            /* ignore */
        }
    }

    const AWAITING_SELECTION = {
        can_generate_pdf: false,
        can_download_pdf: false,
        period_locked: false,
        reason: 'Select a finalized submission above to generate or download a PDF.',
    };

    function saveContext(ctx) {
        try {
            sessionStorage.setItem(STORAGE_KEY, JSON.stringify(ctx));
        } catch (_e) {
            /* ignore */
        }
    }

    async function fetchAvailability(ctx) {
        const q = new URLSearchParams();
        if (ctx.session_id) q.set('session_id', ctx.session_id);
        if (ctx.document_type) q.set('document_type', ctx.document_type);
        if (ctx.period_id) q.set('period_id', ctx.period_id);
        const res = await fetch(`/api/pdf/availability?${q.toString()}`, {
            credentials: 'same-origin',
        });
        let data = {};
        try {
            data = await res.json();
        } catch (_e) {
            data = {};
        }
        if (!res.ok || data.success === false) {
            return {
                can_generate_pdf: false,
                can_download_pdf: false,
                period_locked: false,
                reason: data.error || data.reason || 'Could not verify PDF availability.',
            };
        }
        return data;
    }

    function applyGate(root, availability) {
        const scope = root || document;
        const reason = availability.reason
            || 'PDF is available only after the CFO finalizes and locks the reporting period.';

        scope.querySelectorAll('[data-pdf-gate-wrap]').forEach((wrap) => {
            const mode = wrap.getAttribute('data-pdf-gate-mode') || 'download';
            const allowed = mode === 'generate'
                ? !!availability.can_generate_pdf
                : !!availability.can_download_pdf;

            wrap.querySelectorAll('[data-pdf-gate-action]').forEach((el) => {
                if (allowed) {
                    el.classList.remove('pdf-gate-action--hidden');
                    el.removeAttribute('disabled');
                    el.removeAttribute('aria-disabled');
                } else {
                    el.classList.add('pdf-gate-action--hidden');
                    el.setAttribute('disabled', 'disabled');
                    el.setAttribute('aria-disabled', 'true');
                }
            });

            wrap.querySelectorAll('[data-pdf-gate-notice]').forEach((el) => {
                if (allowed) {
                    el.classList.add('pdf-gate-notice--hidden');
                    el.textContent = '';
                } else {
                    el.classList.remove('pdf-gate-notice--hidden');
                    el.textContent = reason;
                }
            });

            wrap.classList.toggle('pdf-gate-wrap--allowed', allowed);
            wrap.classList.toggle('pdf-gate-wrap--blocked', !allowed);
        });

        const allowedAny = !!(availability.can_download_pdf || availability.can_generate_pdf);
        return allowedAny;
    }

    async function init(options) {
        const ctx = readContext(options);
        if (!ctx.session_id || !ctx.document_type) {
            applyGate(document, AWAITING_SELECTION);
            global.pdfPeriodAvailability = AWAITING_SELECTION;
            return AWAITING_SELECTION;
        }

        saveContext(ctx);

        let availability;
        try {
            availability = await fetchAvailability(ctx);
        } catch (err) {
            availability = {
                can_generate_pdf: false,
                can_download_pdf: false,
                period_locked: false,
                reason: err.message || 'Could not verify PDF availability.',
            };
        }
        applyGate(document, availability);
        global.pdfPeriodAvailability = availability;
        return availability;
    }

    global.PdfPeriodGate = {
        init,
        readContext,
        saveContext,
        clearContext,
        fetchAvailability,
        applyGate,
        AWAITING_SELECTION,
    };
})(typeof window !== 'undefined' ? window : globalThis);
