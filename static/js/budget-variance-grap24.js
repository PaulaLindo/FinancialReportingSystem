/**
 * GRAP 24 — mandatory variance explanations when |variance/budget| > 10%.
 */
(function (global) {
    const THRESHOLD = 0.10;

    function lineVariance(row) {
        const budget = Number(row.budget_amount);
        const actual = Number(row.actual_amount);
        if (
            row.budget_amount != null &&
            row.actual_amount != null &&
            !Number.isNaN(budget) &&
            !Number.isNaN(actual)
        ) {
            return actual - budget;
        }
        return Number(row.variance) || 0;
    }

    function pct(row) {
        const budget = Math.abs(Number(row.budget_amount) || 0);
        if (budget < 1e-9) return 0;
        return Math.abs(lineVariance(row)) / budget;
    }

    function requiresExplanation(row) {
        if (row.is_total_row || row.is_subtotal_row) return false;
        return pct(row) > THRESHOLD;
    }

    function enrichRow(row) {
        const p = pct(row) * 100;
        return {
            ...row,
            variance_percentage: Math.round(p * 100) / 100,
            requires_variance_explanation: requiresExplanation(row),
        };
    }

    function linesRequiringExplanation(rows) {
        return (rows || []).filter(requiresExplanation).map(enrichRow);
    }

    function validateExplanations(rows, explanations) {
        const required = linesRequiringExplanation(rows);
        const expl = explanations || {};
        const missing = [];
        required.forEach((row) => {
            const key = String(row.row_index != null ? row.row_index : row.account_code);
            const text = (expl[key] || expl[String(row.account_code)] || '').trim();
            if (!text) {
                missing.push(row.account_description || row.expense_category || key);
            }
        });
        return { passed: missing.length === 0, missing, required };
    }

    function escapeHtml(str) {
        return String(str || '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    function formatAmount(value) {
        return Number(value || 0).toLocaleString('en-ZA', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
    }

    function isTotalRow(row) {
        if (row.is_total_row || row.is_subtotal_row) return true;
        const code = String(row.account_code || '').trim().toUpperCase();
        const desc = String(row.account_description || row.expense_category || '').trim().toUpperCase();
        return code === 'TOTAL' || desc === 'TOTAL' || code === 'GRAND TOTAL';
    }

    function varianceTone(variancePct, requiresExplanation) {
        if (requiresExplanation) return 'critical';
        if (Math.abs(variancePct) > 5) return 'warn';
        if (Math.abs(variancePct) < 0.05) return 'neutral';
        return variancePct > 0 ? 'unfavorable' : 'favorable';
    }

    function computeSummary(rows) {
        const lineRows = (rows || []).filter((r) => !isTotalRow(r));
        const totalRow = (rows || []).find(isTotalRow);
        let budget = 0;
        let actual = 0;
        let variance = 0;
        let needsExplanation = 0;

        if (totalRow) {
            budget = Number(totalRow.budget_amount) || 0;
            actual = Number(totalRow.actual_amount) || 0;
            variance = totalRow.variance != null ? Number(totalRow.variance) : lineVariance(totalRow);
        } else {
            lineRows.forEach((row) => {
                budget += Number(row.budget_amount) || 0;
                actual += Number(row.actual_amount) || 0;
                variance += lineVariance(row);
            });
        }

        lineRows.forEach((row) => {
            if (requiresExplanation(row)) needsExplanation += 1;
        });

        const varPct = budget ? (Math.abs(variance) / Math.abs(budget)) * 100 : 0;
        return {
            lineCount: lineRows.length,
            budget,
            actual,
            variance,
            varPct,
            needsExplanation,
        };
    }

    function renderTableRow(row, options) {
        const enriched = enrichRow(row);
        const vp = enriched.variance_percentage != null
            ? enriched.variance_percentage
            : pct(row) * 100;
        const variance = row.variance != null ? row.variance : lineVariance(row);
        const total = isTotalRow(row);
        const tone = varianceTone(vp, enriched.requires_variance_explanation);
        const code = escapeHtml(row.account_code || '');
        const desc = escapeHtml(row.account_description || row.expense_category || code);
        const needsMark = enriched.requires_variance_explanation
            ? '<span class="grap24-budget-table__required" title="Variance explanation required">*</span>'
            : '';
        const rowClass = [
            'grap24-budget-table__row',
            total ? 'grap24-budget-table__row--total' : '',
            enriched.requires_variance_explanation ? 'grap24-budget-table__row--needs-explanation' : '',
            `grap24-budget-table__row--${tone}`,
        ].filter(Boolean).join(' ');

        return `<tr class="${rowClass}">
            <td data-label="Code"><span class="grap24-budget-table__code">${code}</span></td>
            <td data-label="Description"><span class="grap24-budget-table__desc">${desc}${needsMark}</span></td>
            <td data-label="Budget (R)" class="grap24-budget-table__amount">R${formatAmount(row.budget_amount)}</td>
            <td data-label="Actual (R)" class="grap24-budget-table__amount">R${formatAmount(row.actual_amount)}</td>
            <td data-label="Variance (R)" class="grap24-budget-table__amount grap24-budget-table__variance">R${formatAmount(variance)}</td>
            <td data-label="Var %"><span class="grap24-budget-table__pct grap24-budget-table__pct--${tone}">${Number(vp).toFixed(1)}%</span></td>
        </tr>`;
    }

    function renderComparisonTable(rows, options) {
        const opts = options || {};
        const period = escapeHtml(opts.period || '');
        const allRows = rows || [];
        const lineRows = allRows.filter((r) => !isTotalRow(r));
        const totalRows = allRows.filter(isTotalRow);
        const displayRows = lineRows.length ? [...lineRows, ...totalRows] : allRows;
        const summary = computeSummary(allRows);
        const body = displayRows.map((row) => renderTableRow(row)).join('');
        const summaryVarTone = varianceTone(summary.varPct, summary.needsExplanation > 0);

        const summaryHtml = `
            <div class="grap24-budget-comparison__stats" role="group" aria-label="Budget comparison summary">
                <div class="grap24-budget-comparison__stat">
                    <span class="grap24-budget-comparison__stat-label">Line items</span>
                    <strong class="grap24-budget-comparison__stat-value">${summary.lineCount}</strong>
                </div>
                <div class="grap24-budget-comparison__stat">
                    <span class="grap24-budget-comparison__stat-label">Total budget</span>
                    <strong class="grap24-budget-comparison__stat-value">R${formatAmount(summary.budget)}</strong>
                </div>
                <div class="grap24-budget-comparison__stat">
                    <span class="grap24-budget-comparison__stat-label">Total actual</span>
                    <strong class="grap24-budget-comparison__stat-value">R${formatAmount(summary.actual)}</strong>
                </div>
                <div class="grap24-budget-comparison__stat grap24-budget-comparison__stat--${summaryVarTone}">
                    <span class="grap24-budget-comparison__stat-label">Variance</span>
                    <strong class="grap24-budget-comparison__stat-value">R${formatAmount(summary.variance)}</strong>
                    <span class="grap24-budget-comparison__stat-meta">${summary.varPct.toFixed(1)}%</span>
                </div>
                ${summary.needsExplanation
                    ? `<div class="grap24-budget-comparison__stat grap24-budget-comparison__stat--critical">
                        <span class="grap24-budget-comparison__stat-label">Need explanation</span>
                        <strong class="grap24-budget-comparison__stat-value">${summary.needsExplanation}</strong>
                        <span class="grap24-budget-comparison__stat-meta">&gt;10% variance</span>
                    </div>`
                    : ''}
            </div>`;

        return `
            <section class="grap24-budget-comparison" aria-labelledby="grap24BudgetComparisonTitle">
                <header class="grap24-budget-comparison__header">
                    <div class="grap24-budget-comparison__title-block">
                        <span class="grap24-budget-comparison__badge">GRAP 24</span>
                        <h3 id="grap24BudgetComparisonTitle" class="grap24-budget-comparison__title">Budget vs Actual</h3>
                        ${period ? `<p class="grap24-budget-comparison__period">${period}</p>` : ''}
                    </div>
                    ${summaryHtml}
                </header>
                <p class="grap24-budget-comparison__intro">
                    Statement of Comparison of Budget and Actual Amounts.
                    Lines marked <span class="grap24-budget-table__required">*</span> require a written variance explanation when variance exceeds 10%.
                </p>
                <div class="grap24-budget-comparison__table-shell">
                    <div class="grap24-budget-comparison__table-scroll" tabindex="0" role="region" aria-label="Budget versus actual line items">
                        <table class="grap24-budget-table">
                            <thead>
                                <tr>
                                    <th scope="col">Code</th>
                                    <th scope="col">Description</th>
                                    <th scope="col" class="grap24-budget-table__amount">Budget (R)</th>
                                    <th scope="col" class="grap24-budget-table__amount">Actual (R)</th>
                                    <th scope="col" class="grap24-budget-table__amount">Variance (R)</th>
                                    <th scope="col">Var %</th>
                                </tr>
                            </thead>
                            <tbody>${body || '<tr><td colspan="6" class="grap24-budget-table__empty">No line items</td></tr>'}</tbody>
                        </table>
                    </div>
                    <p class="grap24-budget-comparison__scroll-hint" aria-hidden="true">Scroll horizontally on small screens to view all columns</p>
                </div>
            </section>`;
    }

    function renderVariancePanel(rows, explanations, options) {
        const opts = options || {};
        const readOnly = !!opts.readOnly;
        const required = linesRequiringExplanation(rows);
        if (!required.length) {
            return opts.emptyHtml || '';
        }

        const expl = explanations || {};
        const rowsHtml = required.map((row) => {
            const key = String(row.row_index != null ? row.row_index : row.account_code);
            const val = expl[key] || expl[String(row.account_code)] || '';
            const label = escapeHtml(row.account_description || row.expense_category || key);
            const varPct = (row.variance_percentage != null ? row.variance_percentage : pct(row) * 100).toFixed(1);
            if (readOnly) {
                return `
                    <div class="grap24-variance-row grap24-variance-row--readonly">
                        <div class="grap24-variance-row__head">
                            <strong>${label}</strong>
                            <span class="text-muted">Variance ${varPct}%</span>
                        </div>
                        <p class="grap24-variance-row__text">${escapeHtml(val) || '<em class="text-muted">No explanation provided</em>'}</p>
                    </div>`;
            }
            return `
                <div class="grap24-variance-row" data-row-key="${escapeHtml(key)}">
                    <label class="grap24-variance-row__label">
                        <strong>${label}</strong>
                        <span class="text-danger">(${varPct}% variance — explanation required)</span>
                    </label>
                    <textarea class="form-control grap24-variance-input" data-row-key="${escapeHtml(key)}"
                        rows="2" required placeholder="GRAP 24 variance explanation (mandatory)">${escapeHtml(val)}</textarea>
                </div>`;
        }).join('');

        return `
            <section class="grap24-variance-panel" id="grap24VariancePanel">
                <h4>Budget vs Actual — GRAP 24 variance explanations</h4>
                <p class="section-intro text-muted">Line items with variance exceeding 10% require a written explanation before submission.</p>
                <div class="grap24-variance-rows">${rowsHtml}</div>
            </section>`;
    }

    function collectFromDom(container) {
        const root = container || document;
        const out = {};
        root.querySelectorAll('.grap24-variance-input').forEach((el) => {
            const key = el.getAttribute('data-row-key');
            if (key) out[key] = el.value.trim();
        });
        return out;
    }

    async function saveExplanations(sessionId, documentType, explanations) {
        const res = await fetch(`/api/universal/session/${encodeURIComponent(sessionId)}/variance-explanations`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                document_type: documentType || 'budget_report',
                variance_explanations: explanations,
            }),
        });
        return res.json();
    }

    global.BudgetVarianceGrap24 = {
        THRESHOLD,
        requiresExplanation,
        linesRequiringExplanation,
        validateExplanations,
        renderComparisonTable,
        renderVariancePanel,
        collectFromDom,
        saveExplanations,
    };
})(typeof window !== 'undefined' ? window : globalThis);
