/**
 * Shared transaction card markup for FM queue, review, history, and approvals.
 */
(function () {
    const UNIVERSAL_TYPES = ['balance_sheet', 'income_statement', 'budget_report'];

    function escapeHtml(s) {
        if (s == null || s === '') return '';
        const d = document.createElement('div');
        d.textContent = String(s);
        return d.innerHTML;
    }

    function typeLabel(dtype) {
        const labels = {
            balance_sheet: 'Balance Sheet',
            income_statement: 'Income Statement',
            budget_report: 'Budget Report',
            financial_statement: 'Financial Statement',
        };
        return labels[dtype] || (dtype || 'Document').replace(/_/g, ' ');
    }

    function statusClass(status) {
        const s = (status || '').toLowerCase();
        const map = {
            pending_review: 'status-pending',
            pending_cfo: 'status-pending',
            approved_by_manager: 'status-approved',
            approved: 'status-approved',
            rejected: 'status-rejected',
            rejected_by_manager: 'status-rejected',
            finalized: 'status-completed',
            pending: 'status-pending',
        };
        return map[s] || 'status-unknown';
    }

    function statusLabel(status) {
        if (window.VarydianUtils && typeof window.VarydianUtils.formatWorkflowStatus === 'function') {
            return window.VarydianUtils.formatWorkflowStatus(status);
        }
        const s = (status || 'unknown').toLowerCase();
        return s.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
    }

    /** UUID → first 8 chars + ellipsis for display; full id in title. */
    function shortSessionIdForDisplay(sessionId, transactionId) {
        const full = (sessionId || transactionId || '').toString().trim();
        if (!full) return { short: '—', full: '' };
        const uuidRe =
            /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
        if (uuidRe.test(full)) {
            return { short: `${full.slice(0, 8)}…`, full: full };
        }
        if (full.length > 28) {
            return { short: `${full.slice(0, 14)}…`, full: full };
        }
        return { short: full, full: full };
    }

    function isFinalizedExportAcknowledged(sessionId, dtype, tx) {
        if (tx && tx.export_acknowledged) return true;
        if (tx && tx.pdf_exported) return true;
        if (!sessionId || !dtype) return false;
        try {
            return sessionStorage.getItem(`varydianFinalizedExportAck:${sessionId}|${dtype}`) === '1';
        } catch (_e) {
            return false;
        }
    }

    function isPdfExported(tx) {
        return !!(tx && tx.pdf_exported);
    }

    function exportCardState(tx) {
        if (isPdfExported(tx)) return 'exported';
        if (isFinalizedExportAcknowledged(tx.session_id, tx.transaction_type, tx)) return 'noted';
        return 'pending';
    }

    function markFinalizedExportAcknowledged(sessionId, dtype) {
        if (!sessionId || !dtype) return;
        try {
            sessionStorage.setItem(`varydianFinalizedExportAck:${sessionId}|${dtype}`, '1');
        } catch (_e) {
            /* ignore */
        }
    }

    function finalizedExportMessage() {
        const role = (window.currentUserRole || '').toUpperCase();
        if (role === 'CFO') {
            return (
                'This submission is finalized. Finish any remaining approvals in Review, ' +
                'then open Export Center to generate PDFs and other exports.'
            );
        }
        return (
            'This submission is finalized. The CFO generates official PDFs in Export Center; ' +
            'you can download them once available.'
        );
    }

    async function persistExportAcknowledged(sessionId, dtype) {
        markFinalizedExportAcknowledged(sessionId, dtype);
        try {
            await fetch(`/api/universal/session/${encodeURIComponent(sessionId)}/export-acknowledged`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'same-origin',
                body: JSON.stringify({ document_type: dtype }),
            });
        } catch (_e) {
            /* sessionStorage fallback remains */
        }
    }

    function applyExportCardVisual(cardEl, state) {
        if (!cardEl) return;
        cardEl.classList.remove('transaction-card--export-noted', 'transaction-card--exported');
        if (state === 'exported') {
            cardEl.classList.add('transaction-card--exported');
        } else if (state === 'noted') {
            cardEl.classList.add('transaction-card--export-noted');
        }
    }

    async function handleFinalizedExportClick(btn) {
        if (!btn || btn.disabled) return;
        const sessionId = btn.dataset.sessionId || '';
        const dtype = btn.dataset.documentType || '';
        const cardEl = btn.closest('.transaction-card');

        if (btn.dataset.exportState === 'exported') {
            return;
        }

        const title = 'Finalized — ready for export';
        const message = finalizedExportMessage();

        if (window.modalSystem && typeof window.modalSystem.alert === 'function') {
            await window.modalSystem.alert(title, message, { confirmText: 'OK' });
        } else if (window.VarydianUtils && VarydianUtils.showToast) {
            VarydianUtils.showToast(message, false);
        } else {
            window.alert(`${title}\n\n${message}`);
        }

        await persistExportAcknowledged(sessionId, dtype);
        applyExportCardVisual(cardEl, 'noted');

        const actions = cardEl && cardEl.querySelector('.transaction-actions');
        if (actions) {
            const badge = document.createElement('span');
            badge.className = 'finalized-export-badge finalized-export-badge--noted';
            badge.textContent = 'Export noted';
            btn.replaceWith(badge);
        } else {
            btn.disabled = true;
            btn.setAttribute('aria-disabled', 'true');
            btn.textContent = 'Export noted';
            btn.classList.add('finalized-export-btn--acknowledged');
        }
    }

    function canApproveTransactions() {
        const role = window.currentUserRole || '';
        return ['FINANCE_MANAGER', 'CFO', 'SYSTEM_ADMIN'].includes(role);
    }

    function grapStandardLabel(dtype) {
        const labels = {
            balance_sheet: 'GRAP 1 — Statement of Financial Position',
            income_statement: 'GRAP 1 — Statement of Financial Performance',
            budget_report: 'GRAP 24 — Budget vs Actual',
        };
        return labels[dtype] || '';
    }

    function rowCountLabel(dtype, count) {
        if (count == null || count === '') return '';
        const n = Number(count);
        if (Number.isNaN(n)) return '';
        if (dtype === 'budget_report') return `${n} budget line${n === 1 ? '' : 's'}`;
        if (dtype === 'income_statement') return `${n} income line${n === 1 ? '' : 's'}`;
        return `${n} account${n === 1 ? '' : 's'}`;
    }

    function documentContextLine(tx) {
        const dtype = tx.transaction_type || '';
        const md = tx.metadata || {};
        const td = tx.transaction_data || {};
        const parts = [];
        const grap = grapStandardLabel(dtype);
        if (grap) parts.push(grap);
        const period = tx.period_name || md.period_name || md.period || md.reporting_period || '';
        if (period) parts.push(String(period));
        const rows = td.total_rows ?? tx.total_rows ?? md.total_mapped_accounts;
        const rowLabel = rowCountLabel(dtype, rows);
        if (rowLabel) parts.push(rowLabel);
        return parts.join(' · ');
    }

    /**
     * @param {object} tx API transaction row
     * @param {object} opts
     * @param {'pending'|'history'|'queue'} opts.variant
     * @param {boolean} opts.showApproveReject
     * @param {string} opts.returnTo path for statement review
     * @param {string} opts.reviewLabel
     */
    function renderTransactionCard(tx, opts = {}) {
        const variant = opts.variant || 'queue';
        const sessionId = tx.session_id || '';
        const dtype = tx.transaction_type || '';
        const st = (tx.status || '').toLowerCase();
        const cardStatusClass = statusClass(st);
        const createdDate = VarydianUtils.formatDateTime(tx.created_at) || '—';
        const reason = tx.reason || tx.filename || '';
        const showApproveReject = opts.showApproveReject === true && canApproveTransactions();
        const isPending = variant === 'pending' || st === 'pending_review' || st === 'pending_cfo';
        const cardModifier = isPending ? 'pending' : cardStatusClass;
        const reviewLabel = opts.reviewLabel || (variant === 'history' ? 'View Details' : 'Review');
        const reviewBtnClass = variant === 'history' ? 'btn-secondary' : 'btn-primary';

        const reviewBtn = sessionId
            ? `<button type="button" class="btn btn-sm ${reviewBtnClass} view-transaction-btn"
                data-transaction-id="${escapeHtml(tx.transaction_id || '')}"
                data-session-id="${escapeHtml(sessionId)}"
                data-transaction-type="${escapeHtml(dtype)}"
                data-return-to="${escapeHtml(opts.returnTo || '')}">
                ${reviewLabel}
            </button>`
            : '';

        const approveReject = showApproveReject && isPending ? `
            <button type="button" class="btn btn-sm btn-success approve-transaction-btn"
                data-transaction-id="${escapeHtml(tx.transaction_id || '')}"
                data-session-id="${escapeHtml(sessionId)}"
                data-transaction-type="${escapeHtml(dtype)}">Approve</button>
            <button type="button" class="btn btn-sm btn-danger reject-transaction-btn"
                data-transaction-id="${escapeHtml(tx.transaction_id || '')}"
                data-session-id="${escapeHtml(sessionId)}"
                data-transaction-type="${escapeHtml(dtype)}">Reject</button>
        ` : '';

        const canFinalizedExport = st === 'approved' && sessionId && dtype && (
            window.currentUserCanDownloadPdf === true || ['FINANCE_MANAGER', 'CFO'].includes(window.currentUserRole || '')
        );
        const exportState = canFinalizedExport ? exportCardState(tx) : null;
        let exportBtn = '';
        if (canFinalizedExport) {
            if (exportState === 'exported') {
                exportBtn = '<span class="finalized-export-badge finalized-export-badge--exported">PDF exported</span>';
            } else if (exportState === 'noted') {
                exportBtn = '<span class="finalized-export-badge finalized-export-badge--noted">Export noted</span>';
            } else {
                exportBtn = `<button type="button" class="btn btn-sm btn-outline-secondary finalized-export-btn"
                data-session-id="${escapeHtml(sessionId)}"
                data-document-type="${escapeHtml(dtype)}"
                data-export-state="pending">Finalized export</button>`;
            }
        }

        const cardExportClass =
            exportState === 'exported'
                ? ' transaction-card--exported'
                : exportState === 'noted'
                  ? ' transaction-card--export-noted'
                  : '';

        const priorityBadge = isPending
            ? '<span class="priority-badge priority-medium">PENDING</span>'
            : '';

        const idForDisplay = shortSessionIdForDisplay(sessionId, tx.transaction_id);
        const docContext = documentContextLine(tx);

        return `
            <div class="transaction-card ${cardModifier}${cardExportClass}" data-transaction-id="${escapeHtml(tx.transaction_id || '')}"
                data-session-id="${escapeHtml(sessionId)}" data-document-type="${escapeHtml(dtype)}">
                <div class="transaction-header">
                    <div class="transaction-info">
                        <h3 class="transaction-title">${escapeHtml(typeLabel(dtype))}</h3>
                        <p class="transaction-id" title="${escapeHtml(idForDisplay.full || tx.transaction_id || '')}">ID: ${escapeHtml(idForDisplay.short)}</p>
                        ${docContext ? `<p class="transaction-doc-context">${escapeHtml(docContext)}</p>` : ''}
                        <p class="transaction-creator">Submitted by: ${escapeHtml(tx.creator_name || 'Unknown')}</p>
                    </div>
                    <div class="transaction-status">
                        <span class="status-badge ${cardStatusClass}">${escapeHtml(statusLabel(st))}</span>
                        ${priorityBadge}
                    </div>
                </div>
                <div class="transaction-details">
                    <div class="transaction-meta">
                        <span class="transaction-date">${escapeHtml(createdDate)}</span>
                        <span class="transaction-type">${escapeHtml(typeLabel(dtype))}</span>
                    </div>
                    <div class="transaction-reason">
                        <strong>File:</strong> ${escapeHtml(reason || '—')}
                    </div>
                </div>
                <div class="transaction-actions">
                    ${reviewBtn}
                    ${exportBtn}
                    ${approveReject}
                </div>
            </div>`;
    }

    function renderTransactionList(transactions, opts = {}) {
        if (!transactions || !transactions.length) {
            return '';
        }
        return `<div class="transaction-list">${transactions.map((tx) => renderTransactionCard(tx, opts)).join('')}</div>`;
    }

    function openStatementReview(sessionId, documentType, returnTo) {
        if (!sessionId) return;
        const typeParam = documentType ? `&type=${encodeURIComponent(documentType)}` : '';
        const returnParam = returnTo ? `&returnTo=${encodeURIComponent(returnTo)}` : '';
        window.location.href = `/approvals?review=statement&transaction=${encodeURIComponent(sessionId)}${typeParam}${returnParam}`;
    }

    function mountTransactionListActions(container, callbacks = {}) {
        if (!container) return;
        container.addEventListener('click', (e) => {
            const viewBtn = e.target.closest('.view-transaction-btn');
            if (viewBtn) {
                e.preventDefault();
                const sessionId = viewBtn.dataset.sessionId;
                const docType = viewBtn.dataset.transactionType;
                const returnTo = viewBtn.dataset.returnTo || callbacks.returnTo || '';
                if (typeof callbacks.onView === 'function') {
                    callbacks.onView(sessionId, docType, returnTo);
                } else {
                    openStatementReview(sessionId, docType, returnTo);
                }
                return;
            }
            const approveBtn = e.target.closest('.approve-transaction-btn');
            if (approveBtn && callbacks.onApprove) {
                e.preventDefault();
                callbacks.onApprove(approveBtn);
                return;
            }
            const rejectBtn = e.target.closest('.reject-transaction-btn');
            if (rejectBtn && callbacks.onReject) {
                e.preventDefault();
                callbacks.onReject(rejectBtn);
                return;
            }
            const exportBtn = e.target.closest('.finalized-export-btn');
            if (exportBtn) {
                e.preventDefault();
                handleFinalizedExportClick(exportBtn);
            }
        });
    }

    window.TransactionCardUI = {
        escapeHtml,
        typeLabel,
        grapStandardLabel,
        documentContextLine,
        statusClass,
        shortSessionIdForDisplay,
        renderTransactionCard,
        renderTransactionList,
        openStatementReview,
        mountTransactionListActions,
        handleFinalizedExportClick,
        isFinalizedExportAcknowledged,
        isPdfExported,
        exportCardState,
        UNIVERSAL_TYPES,
    };
})();
