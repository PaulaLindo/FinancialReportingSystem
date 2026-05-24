/**
 * GRAP standard labels and clerk submit-for-review gates by document type.
 * - budget_report: GRAP 24
 * - balance_sheet: GRAP 1 (SFP)
 * - income_statement: GRAP 1 (Performance)
 */
(function (global) {
    const LABELS = {
        budget_report: {
            standard: 'GRAP 24 (Budget vs Actual)',
            submitButton: 'Submit for Review — GRAP 24',
            success: 'Data forwarded to Finance Manager for review.',
        },
        balance_sheet: {
            standard: 'GRAP 1 (SFP)',
            submitButton: 'Submit for Review — GRAP 1 (SFP)',
            success: 'Data forwarded to Finance Manager for review.',
        },
        income_statement: {
            standard: 'GRAP 1 (Performance)',
            submitButton: 'Submit for Review — GRAP 1 (Performance)',
            success: 'Data forwarded to Finance Manager for review.',
        },
    };

    function normalizeType(documentType) {
        return String(documentType || '').trim().toLowerCase();
    }

    function config(documentType) {
        return LABELS[normalizeType(documentType)] || {
            standard: 'GRAP compliance',
            submitButton: 'Submit for Review',
            success: 'Data forwarded to Finance Manager for review.',
        };
    }

    function lineAccountText(line) {
        return String(
            line.account_name || line.name || line.account_desc || line.description || ''
        ).toLowerCase();
    }

    function classifyByAccountCode(line) {
        const acct = String(line.account_code || line.code || '').trim();
        if (!acct || !/^\d/.test(acct)) return null;
        const lead = acct.charAt(0);
        if (lead === '1') return 'asset';
        if (lead === '2') return 'liability';
        if (lead === '3') return 'equity';
        return null;
    }

    /** 1–3 = SFP; 4–5 = performance; REV-/EXP- prefixes = performance. */
    function trialBalanceSection(line) {
        const acct = String(line.account_code || line.code || '').trim();
        const acctUpper = acct.toUpperCase();
        if (acctUpper.startsWith('REV') || acctUpper.startsWith('EXP')) return 'performance';
        if (!acct || !/^\d/.test(acct)) return 'unknown';
        const lead = acct.charAt(0);
        if (lead === '1' || lead === '2' || lead === '3') return 'balance_sheet';
        if (lead === '4' || lead === '5') return 'performance';
        return 'unknown';
    }

    function classifyLine(line) {
        const acctUpper = String(line.account_code || line.code || '').trim().toUpperCase();
        if (acctUpper.startsWith('REV') || acctUpper.startsWith('4')) return 'revenue';
        if (acctUpper.startsWith('EXP') || acctUpper.startsWith('5')) return 'expense';

        const code = String(line.grap_code || line.grap_category || line.category || '').toUpperCase();
        const label = String(line.grap_category || line.category || '').toLowerCase();
        const accountText = lineAccountText(line);
        const text = `${label} ${accountText}`.trim();

        const byAcctCode = classifyByAccountCode(line);
        if (byAcctCode) return byAcctCode;

        if (text.includes('borrowing') || text.includes('payable') || text.includes('loan')
            || (text.includes('liabilit') && !text.includes('receivable'))) {
            return 'liability';
        }
        if (text.includes('equity') || text.includes('capital') || text.includes('reserve')
            || text.includes('retained') || text.includes('share')) {
            return 'equity';
        }
        if (code.startsWith('CA') || code.startsWith('NC')) return 'asset';
        if (code.startsWith('CL') || code.startsWith('NL')) return 'liability';
        if (code.startsWith('EQ')) return 'equity';
        if (code.startsWith('RV')) return 'revenue';
        if (code.startsWith('EX')) return 'expense';
        if (text.includes('revenue') || text.includes('income') || text.includes('grant')) return 'revenue';
        if (text.includes('expense') || text.includes('cost') || text.includes('expenditure')) return 'expense';
        if (text.includes('cash') || text.includes('receivable') || text.includes('inventory') || text.includes('asset')) {
            if (!text.includes('liabilit')) return 'asset';
        }
        return null;
    }

    function lineAmount(row) {
        const keys = [
            'amount',
            'current_amount',
            'net_balance',
            'balance',
            'value',
            'revenue_amount',
            'expense_amount',
        ];
        for (let i = 0; i < keys.length; i += 1) {
            const v = row[keys[i]];
            if (v != null && v !== '') {
                const n = Number(v);
                if (!Number.isNaN(n)) return Math.abs(n);
            }
        }
        return 0;
    }

    function lineBalanceForSfp(row, kind) {
        const dr = row.debit_balance != null ? row.debit_balance : row.debit;
        const cr = row.credit_balance != null ? row.credit_balance : row.credit;
        if (dr != null || cr != null) {
            const d = Number(dr) || 0;
            const c = Number(cr) || 0;
            return kind === 'asset' ? d - c : c - d;
        }
        const keys = ['amount', 'current_amount', 'net_balance', 'balance', 'value'];
        for (let i = 0; i < keys.length; i += 1) {
            const v = row[keys[i]];
            if (v != null && v !== '') {
                const n = Number(v);
                if (!Number.isNaN(n)) {
                    return kind === 'asset' ? n : Math.abs(n);
                }
            }
        }
        return 0;
    }

    function computeSfpTotals(lines) {
        let assets = 0;
        let liabilities = 0;
        let equity = 0;
        let included = 0;
        let skipped = 0;
        (lines || []).forEach((row) => {
            if (trialBalanceSection(row) === 'performance') {
                skipped += 1;
                return;
            }
            const kind = classifyLine(row);
            if (kind === 'asset') {
                assets += lineBalanceForSfp(row, 'asset');
                included += 1;
            } else if (kind === 'liability') {
                liabilities += lineBalanceForSfp(row, 'liability');
                included += 1;
            } else if (kind === 'equity') {
                equity += lineBalanceForSfp(row, 'equity');
                included += 1;
            } else {
                skipped += 1;
            }
        });
        const le = liabilities + equity;
        const diff = Math.abs(assets - le);
        return {
            assets,
            liabilities,
            equity,
            liabilities_plus_equity: le,
            difference: diff,
            balanced: diff <= 0.01,
            included,
            skipped,
        };
    }

    function computePerformanceTotals(lines) {
        let revenue = 0;
        let expenses = 0;
        (lines || []).forEach((row) => {
            const section = trialBalanceSection(row);
            const kind = classifyLine(row);
            const amt = lineAmount(row);
            if (section === 'performance' || kind === 'revenue' || kind === 'expense') {
                if (kind === 'revenue' || (kind !== 'expense' && String(row.account_code || row.code || '').trim().startsWith('4'))) {
                    revenue += amt;
                } else {
                    expenses += amt;
                }
            }
        });
        return {
            revenue,
            expenses,
            net: revenue - expenses,
        };
    }

    function mappedLinesFromMetadata(md) {
        const meta = md || {};
        const raw = meta.mapped_data || meta.mapped_accounts || meta.grap_mapping || [];
        const lines = [];
        if (Array.isArray(raw)) {
            raw.forEach((item) => {
                if (item && typeof item === 'object') lines.push(item);
            });
            return lines;
        }
        if (typeof raw === 'object') {
            Object.keys(raw).forEach((key) => {
                const val = raw[key];
                if (Array.isArray(val)) {
                    val.forEach((item) => {
                        if (item && typeof item === 'object') {
                            const row = { ...item };
                            row.grap_code = row.grap_code || key;
                            row.grap_category = row.grap_category || key;
                            lines.push(row);
                        }
                    });
                } else if (val && typeof val === 'object') {
                    const row = { ...val };
                    row.grap_code = row.grap_code || key;
                    lines.push(row);
                }
            });
        }
        return lines;
    }

    function buildFinancialStatementsFromMapped(mappedRows) {
        const assets = [];
        const liabilities = [];
        const equity = [];
        const revenue = [];
        const expenses = [];
        (mappedRows || []).forEach((row) => {
            const section = trialBalanceSection(row);
            if (section === 'performance') {
                const kind = classifyLine(row);
                const code = String(row.account_code || row.code || '').trim();
                if (kind === 'revenue' || (kind !== 'expense' && code.startsWith('4'))) {
                    revenue.push(row);
                } else {
                    expenses.push(row);
                }
                return;
            }
            const kind = classifyLine(row);
            if (kind === 'asset') assets.push(row);
            else if (kind === 'liability') liabilities.push(row);
            else if (kind === 'equity') equity.push(row);
        });
        const sfpTotals = computeSfpTotals([...assets, ...liabilities, ...equity]);
        const perfTotals = computePerformanceTotals(mappedRows);
        return {
            assets,
            liabilities,
            equity,
            revenue,
            expenses,
            sfpTotals,
            perfTotals,
        };
    }

    function formulaHintSourceLabel(documentType) {
        const dt = normalizeType(documentType);
        if (dt === 'income_statement') return 'income statement';
        if (dt === 'budget_report') return 'budget report';
        return 'trial balance';
    }

    function lineAmountFormulaHint(row, documentType) {
        const dt = normalizeType(documentType);
        const kind = classifyLine(row);
        const source = formulaHintSourceLabel(documentType);
        const fromSource = `from ${source}`;

        if (dt === 'balance_sheet' && trialBalanceSection(row) === 'performance') {
            return 'P&L account (4xxx/5xxx) — shown on Statement of Financial Performance, not in A = L + E';
        }
        if (kind === 'asset') {
            return dt === 'balance_sheet'
                ? 'Debit minus credit from trial balance'
                : `Asset amount ${fromSource}`;
        }
        if (kind === 'liability' || kind === 'equity') {
            return dt === 'balance_sheet'
                ? 'Credit minus debit from trial balance'
                : `${kind === 'liability' ? 'Liability' : 'Equity'} amount ${fromSource}`;
        }
        if (kind === 'revenue') {
            return dt === 'income_statement'
                ? 'Revenue from income statement (credit balance, shown as positive)'
                : `Revenue ${fromSource} (credit balance, shown as positive)`;
        }
        if (kind === 'expense') {
            return dt === 'income_statement'
                ? 'Expense from income statement (debit balance, shown as positive)'
                : `Expense ${fromSource} (debit balance, shown as positive)`;
        }
        if (dt === 'budget_report') {
            return 'Budget or actual amount from budget report';
        }
        if (dt === 'income_statement') {
            return 'Mapped amount from income statement';
        }
        return 'Mapped amount from trial balance';
    }

    function validateBalanceSheetLines(lines) {
        const totals = computeSfpTotals(lines);
        const { assets, liabilities, equity, difference: diff, skipped } = totals;
        if (totals.balanced && assets > 0) {
            return { passed: true, message: null, totals };
        }
        const unmappedHint =
            skipped > 0
                ? ' P&L lines (4xxx/5xxx) and unclassified rows are excluded from the SFP equation.'
                : '';
        return {
            passed: false,
            message:
                `GRAP 1 (SFP): assets must equal liabilities plus equity (difference R ${diff.toLocaleString('en-ZA')}).` +
                unmappedHint,
            totals,
        };
    }

    function validateIncomeStatementLines(lines) {
        let revenue = 0;
        let expenses = 0;
        (lines || []).forEach((row) => {
            const kind = classifyLine(row);
            const amt = lineAmount(row);
            if (kind === 'revenue') revenue += amt;
            else if (kind === 'expense') expenses += amt;
        });
        const passed = revenue > 0 || expenses > 0;
        return {
            passed,
            message: passed
                ? null
                : 'GRAP 1 (Performance): map at least one revenue or expense line before submit.',
        };
    }

    function validateBeforeSubmit(documentType, mappedRows) {
        const dt = normalizeType(documentType);
        if (dt === 'budget_report') {
            return { passed: true, message: null };
        }
        if (dt === 'balance_sheet') {
            return validateBalanceSheetLines(mappedRows);
        }
        if (dt === 'income_statement') {
            return validateIncomeStatementLines(mappedRows);
        }
        return { passed: true, message: null };
    }

    /** Upload-page balance panel (pre-mapping), distinct from GRAP submit checks. */
    function uploadBalanceCopy(documentType, balanceData, isBalanced) {
        const dt = normalizeType(documentType);
        const bd = balanceData || {};
        const balanced = Boolean(isBalanced);

        if (dt === 'balance_sheet') {
            const isBudgetStyle = bd.balance_type === 'budget_vs_actual';
            return {
                sectionTitle: isBudgetStyle ? 'Budget vs actual check' : 'Trial balance check',
                checkingMessage: isBudgetStyle
                    ? 'Checking budget vs actual totals…'
                    : 'Checking trial balance (debits = credits)…',
                successMessage: isBudgetStyle
                    ? 'Budget vs actual aligned on upload'
                    : 'Trial balance balanced (debits = credits)',
                failureMessage: isBudgetStyle
                    ? 'Budget vs actual mismatch on upload'
                    : 'Trial balance not balanced',
                footnote: `${config(dt).standard} mapping and the accounting equation are validated after you complete mapping.`,
            };
        }
        if (dt === 'income_statement') {
            return {
                sectionTitle: 'Upload totals check',
                checkingMessage: 'Summarising revenue and expenses from upload…',
                successMessage: 'Upload totals captured — continue to mapping',
                failureMessage: 'Upload totals need review',
                footnote: `${config(dt).standard} is validated when you submit for review after mapping.`,
            };
        }
        if (dt === 'budget_report') {
            const hasVariance = Boolean(bd.has_aggregate_variance);
            return {
                sectionTitle: 'Budget vs actual summary',
                checkingMessage: 'Summarising budget vs actual from upload…',
                successMessage: hasVariance
                    ? 'Budget vs actual captured — line variances will be reviewed at mapping (GRAP 24).'
                    : 'Budget vs actual captured — aggregate totals match on upload.',
                failureMessage: 'No budget or actual amounts found in upload',
                footnote: 'GRAP 24 variance explanations (>10%) are required on the mapping page before submit for review.',
            };
        }
        return {
            sectionTitle: 'Upload validation',
            checkingMessage: 'Validating upload…',
            successMessage: 'Upload validated',
            failureMessage: 'Upload validation failed',
            footnote: 'Further GRAP checks apply after mapping.',
        };
    }

    function formatMoney(n) {
        return Number(n || 0).toLocaleString('en-ZA', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
    }

    function workflowRequirements(documentType) {
        const dt = normalizeType(documentType);
        const std = config(dt).standard;
        const base = {
            balance_sheet: {
                clerk: [
                    'Map every trial balance account to a GRAP category (1xxx/2xxx/3xxx on SFP; 4xxx/5xxx on performance).',
                    'Trial balance must balance: total debits = total credits.',
                    `${std}: Assets = Liabilities + Equity (same check as CFO final approval).`,
                ],
                finance_manager: [
                    'Review Statement of Financial Position and performance lines plus mappings.',
                    'Approve forwards to CFO — trial balance / GRAP equation is not re-run at this step.',
                ],
                cfo: [
                    'Final approval re-runs GRAP 1 (SFP) on stored mappings.',
                    'Accounting equation must pass; period is locked after approval.',
                ],
            },
            income_statement: {
                clerk: [
                    'Map all accounts to GRAP revenue (RV) or expense (EX) categories.',
                    'At least one revenue or expense line must be present.',
                    `${std} validated on submit (same rules as CFO performance check).`,
                ],
                finance_manager: [
                    'Review performance statement and mappings.',
                    'Approve forwards to CFO.',
                ],
                cfo: [
                    'Final approval re-runs GRAP 1 (Performance) compliance.',
                    'Period locked after approval.',
                ],
            },
            budget_report: {
                clerk: [
                    'Map budget lines to GRAP categories.',
                    `${std}: written variance explanations where |variance ÷ budget| > 10%.`,
                    'Submit for review after explanations are complete.',
                ],
                finance_manager: [
                    'Review budget vs actual and variance narratives.',
                    'Approve forwards to CFO.',
                ],
                cfo: [
                    'Final approval checks GRAP 24 variance explanations.',
                    'Period locked after approval.',
                ],
            },
        };
        return base[dt] || {
            clerk: ['Complete mapping before submit for review.'],
            finance_manager: ['Review submission and approve or reject with reason.'],
            cfo: ['Final approval per workflow rules.'],
        };
    }

    function currentAppRole() {
        const w = typeof global !== 'undefined' ? global : globalThis;
        return String(w.currentUserRole || '').toUpperCase();
    }

    function renderRoleWorkflowGuide(documentType) {
        if (currentAppRole() === 'FINANCE_CLERK') {
            return '';
        }
        const req = workflowRequirements(documentType);
        const row = (role, label, items) => `
            <div class="workflow-role-block">
                <h5 class="workflow-role-block__title">${label}</h5>
                <ul class="workflow-role-block__list">
                    ${items.map((t) => `<li>${t}</li>`).join('')}
                </ul>
            </div>`;
        return `
            <details class="workflow-roles-guide">
                <summary>What each role checks for this document</summary>
                <div class="workflow-roles-guide__body">
                    ${row('clerk', 'Finance Clerk (you)', req.clerk)}
                    ${row('fm', 'Finance Manager', req.finance_manager)}
                    ${row('cfo', 'CFO', req.cfo)}
                </div>
            </details>`;
    }

    function renderMappingComplianceLive(documentType, opts) {
        const dt = normalizeType(documentType);
        const o = opts || {};
        const unmapped = Number(o.unmappedCount) || 0;
        const tb = o.trialBalance || {};
        const tbOk = tb.balanced === true;
        const tbMsg = tb.message || (tbOk ? 'Debits equal credits' : 'Checking trial balance…');
        const rows = o.validationRows || [];
        const mappedOnly = (rows || []).filter((r) => {
            const code = String(r.grap_code || r.grap_category || '').trim();
            return !!code;
        });

        let checksHtml = '';

        if (dt === 'balance_sheet' || dt === 'income_statement' || dt === 'budget_report') {
            const tbLabel = dt === 'budget_report'
                ? 'Budget / actual lines captured'
                : 'Trial balance (debits = credits)';
            checksHtml += `
                <div class="grap-check-row ${tbOk ? 'grap-check-row--ok' : tb.balanced === false ? 'grap-check-row--fail' : ''}">
                    <span class="grap-check-row__label">${tbLabel}</span>
                    <span class="grap-check-row__value">${tbMsg}</span>
                </div>`;
        }

        if (dt === 'balance_sheet') {
            const st = o.sfpTotals || computeSfpTotals(mappedOnly.length ? mappedOnly : rows);
            const ok = st.balanced && unmapped === 0;
            checksHtml += `
                <div class="grap-equation-panel ${ok ? 'grap-equation-panel--balanced' : 'grap-equation-panel--unbalanced'}">
                    <h5 class="grap-equation-panel__title">GRAP 1 (SFP) — live from your mappings</h5>
                    <p class="grap-equation-panel__intro text-muted">Uses mapped lines only (1xxx/2xxx/3xxx). P&amp;L codes (4xxx/5xxx) are excluded from this equation.</p>
                    <div class="grap-equation-grid">
                        <div class="grap-equation-cell"><span class="grap-equation-label">Assets</span><span class="grap-equation-value">R${formatMoney(st.assets)}</span></div>
                        <div class="grap-equation-cell"><span class="grap-equation-label">Liabilities</span><span class="grap-equation-value">R${formatMoney(st.liabilities)}</span></div>
                        <div class="grap-equation-cell"><span class="grap-equation-label">Equity</span><span class="grap-equation-value">R${formatMoney(st.equity)}</span></div>
                        <div class="grap-equation-cell grap-equation-cell--highlight"><span class="grap-equation-label">Liabilities + Equity</span><span class="grap-equation-value">R${formatMoney(st.liabilities_plus_equity)}</span></div>
                        <div class="grap-equation-cell grap-equation-cell--diff ${ok ? '' : 'grap-equation-cell--warn'}"><span class="grap-equation-label">Difference</span><span class="grap-equation-value">R${formatMoney(st.difference)}</span></div>
                    </div>
                    <p class="grap-equation-formula"><strong>Formula:</strong> Assets − (Liabilities + Equity) → 0</p>
                    <p class="grap-equation-status ${ok ? 'text-success' : 'text-danger'}">${
                        unmapped > 0
                            ? `⚠ ${unmapped} unmapped account(s) — map all before submit.`
                            : ok
                              ? '✓ Ready for submit'
                              : '⚠ Out of balance — fix mappings or amounts before submit'
                    }</p>
                </div>`;
            const pt = o.perfTotals || computePerformanceTotals(rows);
            if (pt.revenue || pt.expenses) {
                checksHtml += `
                <div class="grap-equation-panel grap-equation-panel--secondary">
                    <h5 class="grap-equation-panel__title">Performance lines (4xxx / 5xxx)</h5>
                    <div class="grap-equation-grid grap-equation-grid--compact">
                        <div class="grap-equation-cell"><span class="grap-equation-label">Revenue</span><span class="grap-equation-value">R${formatMoney(pt.revenue)}</span></div>
                        <div class="grap-equation-cell"><span class="grap-equation-label">Expenses</span><span class="grap-equation-value">R${formatMoney(pt.expenses)}</span></div>
                        <div class="grap-equation-cell"><span class="grap-equation-label">Net</span><span class="grap-equation-value">R${formatMoney(pt.net)}</span></div>
                    </div>
                </div>`;
            }
        }

        if (dt === 'income_statement') {
            const pt = o.perfTotals || computePerformanceTotals(mappedOnly.length ? mappedOnly : rows);
            const ok = (pt.revenue > 0 || pt.expenses > 0) && unmapped === 0;
            checksHtml += `
                <div class="grap-equation-panel ${ok ? 'grap-equation-panel--balanced' : 'grap-equation-panel--unbalanced'}">
                    <h5 class="grap-equation-panel__title">GRAP 1 (Performance) — live from your mappings</h5>
                    <div class="grap-equation-grid">
                        <div class="grap-equation-cell"><span class="grap-equation-label">Revenue</span><span class="grap-equation-value">R${formatMoney(pt.revenue)}</span></div>
                        <div class="grap-equation-cell"><span class="grap-equation-label">Expenses</span><span class="grap-equation-value">R${formatMoney(pt.expenses)}</span></div>
                        <div class="grap-equation-cell grap-equation-cell--highlight"><span class="grap-equation-label">Net</span><span class="grap-equation-value">R${formatMoney(pt.net)}</span></div>
                    </div>
                    <p class="grap-equation-formula"><strong>Formula:</strong> Revenue − Expenses = Net</p>
                    <p class="grap-equation-status ${ok ? 'text-success' : 'text-danger'}">${
                        unmapped > 0
                            ? `⚠ ${unmapped} unmapped account(s).`
                            : ok
                              ? '✓ Ready for submit'
                              : '⚠ Map at least one revenue or expense line'
                    }</p>
                </div>`;
        }

        if (dt === 'budget_report') {
            const grap24 = o.grap24 || {};
            checksHtml += `
                <div class="grap-check-row ${grap24.passed ? 'grap-check-row--ok' : grap24.passed === false ? 'grap-check-row--fail' : ''}">
                    <span class="grap-check-row__label">GRAP 24 variance explanations</span>
                    <span class="grap-check-row__value">${grap24.message || 'Complete explanations in the panel below when variance exceeds 10%.'}</span>
                </div>`;
        }

        return checksHtml;
    }

    function clerkSubmitReady(documentType, opts) {
        const dt = normalizeType(documentType);
        const o = opts || {};
        const unmapped = Number(o.unmappedCount) || 0;
        if (unmapped > 0) return false;

        if (dt === 'balance_sheet') {
            const tb = o.trialBalance || {};
            if (tb.balanced !== true) return false;
            const rows = o.validationRows || [];
            const mappedOnly = rows.filter((r) => String(r.grap_code || r.grap_category || '').trim());
            const st = o.sfpTotals || computeSfpTotals(mappedOnly);
            return st.balanced;
        }
        if (dt === 'income_statement') {
            const tb = o.trialBalance || {};
            if (tb.balanced !== true) return false;
            const rows = o.validationRows || [];
            const pt = o.perfTotals || computePerformanceTotals(rows);
            return pt.revenue > 0 || pt.expenses > 0;
        }
        if (dt === 'budget_report') {
            const tb = o.trialBalance || {};
            if (tb.balanced !== true) return false;
            if (!o.grap24 || o.grap24.passed !== true) return false;
            return true;
        }
        return false;
    }

    function renderCompliancePanel(documentType) {
        const dt = normalizeType(documentType);
        let title = 'GRAP compliance';
        let intro = 'Complete mapping before submitting for review.';
        if (dt === 'budget_report') {
            title = 'GRAP 24 — Budget vs Actual';
            intro = 'Variance explanations (>10%) are required below before you can submit for review.';
        } else if (dt === 'balance_sheet') {
            title = 'GRAP 1 — Statement of Financial Position (SFP)';
            intro = 'Map all accounts, confirm trial balance, then Assets = Liabilities + Equity before submit.';
        } else if (dt === 'income_statement') {
            title = 'GRAP 1 — Statement of Financial Performance';
            intro = 'Map all revenue and expense lines before submit for review.';
        }
        return `
            <section class="grap-submit-compliance-panel" id="grapSubmitCompliancePanel">
                <h4>${title}</h4>
                <p class="section-intro text-muted">${intro}</p>
                <div id="grapComplianceLiveMount" class="grap-compliance-live-mount" aria-live="polite"></div>
                ${renderRoleWorkflowGuide(documentType)}
            </section>`;
    }

    function renderReviewerRoleBanner(documentType, role) {
        const dt = normalizeType(documentType);
        const req = workflowRequirements(documentType);
        const r = String(role || '').toUpperCase();
        const items = r === 'CFO' ? req.cfo : r === 'FINANCE_MANAGER' ? req.finance_manager : req.clerk;
        const label = r === 'CFO' ? 'CFO' : r === 'FINANCE_MANAGER' ? 'Finance Manager' : 'Finance Clerk';
        return `
            <section class="workflow-role-banner" aria-label="Requirements for this role">
                <h4 class="workflow-role-banner__title">${label} — ${config(dt).standard}</h4>
                <ul class="workflow-role-banner__list">${items.map((t) => `<li>${t}</li>`).join('')}</ul>
            </section>`;
    }

    global.GrapStandards = {
        config,
        uploadBalanceCopy,
        validateBeforeSubmit,
        renderCompliancePanel,
        renderMappingComplianceLive,
        renderRoleWorkflowGuide,
        renderReviewerRoleBanner,
        workflowRequirements,
        clerkSubmitReady,
        formatMoney,
        trialBalanceSection,
        classifyLine,
        classifyByAccountCode,
        lineBalanceForSfp,
        lineAmount,
        computeSfpTotals,
        computePerformanceTotals,
        mappedLinesFromMetadata,
        buildFinancialStatementsFromMapped,
        lineAmountFormulaHint,
    };
})(typeof window !== 'undefined' ? window : globalThis);
