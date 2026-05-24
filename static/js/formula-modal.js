/**
 * Formula Transparency Modal JavaScript Controller
 * Handles formula breakdown display for CFO and AUDITOR roles
 */

/** Registered ledger/source URLs only — omit per-variable buttons when `source` is not listed (e.g. session metadata). */
const FORMULA_SOURCE_LEDGER_URLS = {
    asset_sub_ledger: '/assets/sub-ledger',
    depreciation_schedule: '/assets/depreciation-schedule',
    asset_register: '/assets/register',
    asset_policy: '/policies/asset-management',
    loan_register: '/liabilities/loan-register',
    loan_agreement: '/liabilities/loan-agreements',
    loan_schedule: '/liabilities/loan-schedules',
    impairment_test: '/assets/impairment-tests',
    general_ledger: '/accounting/general-ledger',
};

class FormulaModalController {
    constructor() {
        this.currentData = null;
        this.modal = null;
        this.isOpen = false;
        this.formulaData = new Map(); // Cache formula data
        this.currentBalanceSheetId = null;
        this.currentProcessingState = null;
        this.currentAccess = null;
        /** Set when loading universal session formula breakdown (same-origin API / statement links). */
        this.currentUniversalDocumentType = null;
        this.initializeEventListeners();
    }

    /** Safe text for HTML body interpolation */
    _escapeHtml(s) {
        if (s == null || s === '') return '';
        const d = document.createElement('div');
        d.textContent = String(s);
        return d.innerHTML;
    }

    /** Safe double-quoted attribute (paths only — reject scheme-relative URLs) */
    _safeHrefAttr(href) {
        const h = String(href || '').trim();
        if (!h.startsWith('/') || h.startsWith('//')) return '';
        return h.replace(/&/g, '&amp;').replace(/"/g, '&quot;');
    }

    initializeEventListeners() {
        // Wait for DOM to be ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => {
                this.initialize();
            });
        } else {
            this.initialize();
        }
    }

    initialize() {
        this.modal = document.getElementById('formulaModal');
        if (!this.modal) {
            return;
        }

        this.attachCellHandlers();
        this.attachModalEventListeners();
        this.loadFormulaDataCache();
    }

    attachCellHandlers() {
        // Find all calculated cells in financial statements
        const calculatedCells = document.querySelectorAll('[data-critical="true"][data-amount="true"]');
        
        calculatedCells.forEach(cell => {
            // Skip if already processed
            if (cell.classList.contains('formula-modal-enabled')) {
                return;
            }

            // Make cell clickable
            cell.classList.add('cursor-pointer');
            cell.classList.add('calculated-cell', 'formula-modal-enabled');
            
            // Add click handler
            cell.addEventListener('click', (e) => {
                e.stopPropagation();
                this.openForCell(cell);
            });

            // Add keyboard accessibility
            cell.setAttribute('tabindex', '0');
            cell.setAttribute('role', 'button');
            cell.setAttribute('aria-label', 'View formula breakdown');
            
            cell.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    this.openForCell(cell);
                }
            });
        });
    }

    attachModalEventListeners() {
        // Close modal on overlay click
        this.modal.addEventListener('click', (e) => {
            if (e.target === this.modal) {
                this.close();
            }
        });

        // Close on Escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.isOpen) {
                this.close();
            }
        });

        // Trap focus within modal
        this.modal.addEventListener('keydown', (e) => {
            if (e.key === 'Tab' && this.isOpen) {
                this.trapFocus(e);
                return;
            }
            if ((e.key === 'Enter' || e.key === ' ') && this.isOpen) {
                const vlink = e.target.closest('a.variable-source-link');
                if (vlink && vlink.getAttribute('href')?.startsWith('/')) {
                    e.preventDefault();
                    vlink.click();
                }
            }
        });

        /** Plain-click opens same-origin targets via window.open so the tab may close + focus opener on return. */
        this.modal.addEventListener('click', (e) => this._onVariableSourceLinkClick(e));
    }

    /**
     * @param {MouseEvent} e
     */
    _onVariableSourceLinkClick(e) {
        const link = e.target.closest('a.variable-source-link');
        if (!link || !this.modal.contains(link)) return;
        const href = link.getAttribute('href');
        if (!href || !href.startsWith('/')) return;
        if (e.button !== 0 || e.ctrlKey || e.metaKey || e.shiftKey || e.altKey) return;
        e.preventDefault();
        try {
            const abs = new URL(href, window.location.origin);
            if (abs.origin !== window.location.origin) {
                window.open(abs.href, '_blank', 'noopener,noreferrer');
                return;
            }
            if (abs.pathname === '/approvals') {
                const sp = abs.searchParams;
                if (sp.get('review') === 'statement' && !sp.get('returnTo')) {
                    const fsr = window.financialStatementReview;
                    const rt =
                        fsr && typeof fsr.currentReturnToForAuxiliaryTab === 'function'
                            ? fsr.currentReturnToForAuxiliaryTab()
                            : null;
                    if (rt) sp.set('returnTo', rt);
                }
            }
            window.open(abs.href, '_blank');
        } catch (_) {
            window.open(href, '_blank', 'noopener,noreferrer');
        }
    }

    async openForCell(cellElement) {
        const row = cellElement.closest('tr');
        if (!row) return;

        const itemName = row.querySelector('[data-label="Particulars"]')?.textContent?.trim() || 'Unknown Item';
        const currentValue = cellElement.textContent.trim();
        const noteReference = row.querySelector('[data-label="Note"]')?.textContent?.trim() || '';
        
        // Extract line item ID
        const lineItemId = this.generateLineId(itemName);
        
        // Get current reporting period
        const period = this.getCurrentReportingPeriod();
        
        // Show loading state
        this.showLoading();
        
        try {
            // Load formula data
            const formulaData = await this.fetchFormulaData(lineItemId, itemName, currentValue);
            
            // Update modal content
            this.updateModalContent(formulaData, itemName, currentValue, period, noteReference);
            
            // Show modal
            this.show();
            
        } catch (error) {
            this.showError('Unable to load formula breakdown data. Please try again.');
        }
    }

    generateLineId(itemName) {
        return itemName.toLowerCase()
            .replace(/[^a-z0-9\s]/g, '')
            .replace(/\s+/g, '_')
            .substring(0, 50);
    }

    getCurrentReportingPeriod() {
        // Try to get period from page, otherwise use default
        const periodElement = document.querySelector('[data-period]');
        if (periodElement) {
            return periodElement.dataset.period;
        }
        
        // Get from URL or default
        const urlParams = new URLSearchParams(window.location.search);
        return urlParams.get('period') || 'FY 2025-2026';
    }

    async fetchFormulaData(lineItemId, itemName, currentValue) {
        // Check cache first
        const cacheKey = `${this.currentBalanceSheetId || 'legacy'}_${lineItemId}`;
        if (this.formulaData.has(cacheKey)) {
            return this.formulaData.get(cacheKey);
        }

        // Show loading
        this.showLoading();

        try {
            // Determine API endpoint based on processing state
            let apiUrl;
            if (this.currentBalanceSheetId && this.currentProcessingState) {
                // Use processing state-aware endpoint
                apiUrl = `/api/formula/breakdown/${this.currentBalanceSheetId}/${lineItemId}`;
            } else {
                // Use legacy endpoint
                apiUrl = `/api/formula/breakdown/${lineItemId}`;
            }

            const response = await fetch(apiUrl, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });

            if (response.ok) {
                const result = await response.json();
                const data = result.data || result; // Handle both response formats
                this.formulaData.set(cacheKey, data);
                
                // Store access information for display
                if (result.access) {
                    this.currentAccess = result.access;
                }
                
                return data;
            } else if (response.status === 403) {
                const error = await response.json();
                this.showError(error.error || 'Access denied. Formula visibility not available in current processing phase.');
                return null;
            }
        } catch (error) {
            return null;
        }
    }

    
    updateModalContent(data, itemName, currentValue, period, noteReference) {
        // Update title
        document.getElementById('modalTitle').textContent = `Calculation Breakdown: ${itemName}`;
        
        // Build audit reference with processing state
        let auditText = `Review context: ${data.assetClass} | Framework: ${data.grapReference} | Period: ${period}`;
        
        // Add processing status if available
        if (data.processingStatus) {
            auditText += ` | Status: ${this.formatProcessingStatus(data.processingStatus)}`;
        }
        
        // Add access mode if available
        if (data.accessMode) {
            auditText += ` | Access: ${this.formatAccessMode(data.accessMode)}`;
        }
        
        if (noteReference) {
            auditText += ` | Note: ${noteReference}`;
        }
        
        document.getElementById('auditReference').textContent = auditText;
        
        // Update variables grid
        this.updateVariablesGrid(data.variables);
        
        // Update formula
        document.getElementById('formulaExpression').textContent = data.formula;
        
        // Update calculation steps (recreates #finalValue inside this container)
        const showFinalBand = data.showFinalBand !== false;
        this.updateCalculationSteps(data.steps, data.finalResult, { showFinalBand });
        
        // Add mapped accounts section if available
        if (data.mappedAccounts && data.mappedAccounts.length > 0) {
            this.addMappedAccountsSection(data.mappedAccounts);
        }
        
        // Add GRAP validations section if available
        if (data.grapValidations && data.grapValidations.length > 0) {
            this.addGrapValidationsSection(data.grapValidations);
        }
        
        // Update modal footer based on access mode
        this.updateModalFooter(data.accessMode, data.processingStatus);
        
        // Store current data for export
        this.currentData = {
            ...data,
            itemName,
            period,
            currentValue,
            noteReference,
            timestamp: new Date().toISOString()
        };
    }
    
    formatProcessingStatus(status) {
        const statusMap = {
            'uploaded': 'Uploaded',
            'mapping': 'Mapping Phase',
            'processing': 'Processing',
            'review': 'Under Review',
            'finalized': 'Finalized'
        };
        return statusMap[status] || status;
    }
    
    formatAccessMode(mode) {
        const modeMap = {
            'draft': 'Draft Mode',
            'review': 'Review Mode',
            'audit': 'Audit Mode',
            'readonly': 'Read-Only',
            'limited': 'Limited Access',
            'legacy': 'Legacy Mode'
        };
        return modeMap[mode] || mode;
    }

    formatModalNumber(num) {
        const n = parseFloat(num);
        if (Number.isNaN(n)) return String(num);
        return n.toLocaleString('en-ZA', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    addMappedAccountsSection(mappedAccounts) {
        // Check if section already exists
        if (document.querySelector('.mapped-accounts-section')) {
            return;
        }
        
        const modalBody = document.querySelector('.formula-modal-body');
        const section = document.createElement('div');
        section.className = 'formula-section mapped-accounts-section';
        
        section.innerHTML = `
            <div class="formula-section-header">
                <h3 class="formula-section-title">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M9 11H3v10h6V11z"/>
                        <path d="M21 11h-6v10h6V11z"/>
                        <path d="M15 3H9v6h6V3z"/>
                    </svg>
                    Mapped Balance Sheet Accounts
                </h3>
                <div class="formula-section-badge">Account Mapping</div>
            </div>
            
            <div class="mapped-accounts-grid">
                ${mappedAccounts.map(mapping => `
                    <div class="mapped-account-item">
                        <div class="mapped-tb-account">${mapping.tb_account}</div>
                        <div class="mapping-arrow">→</div>
                        <div class="mapped-grap-item">${mapping.grap_line_item}</div>
                        <div class="mapping-info">
                            <small>Mapped by ${mapping.mapped_by} on ${VarydianUtils.formatDateTime(mapping.mapped_at)}</small>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
        
        modalBody.appendChild(section);
    }
    
    addGrapValidationsSection(grapValidations) {
        // Check if section already exists
        if (document.querySelector('.grap-validations-section')) {
            return;
        }
        
        const modalBody = document.querySelector('.formula-modal-body');
        const section = document.createElement('div');
        section.className = 'formula-section grap-validations-section';
        
        section.innerHTML = `
            <div class="formula-section-header">
                <h3 class="formula-section-title">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M12 2L2 7v10c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V7l-10-5z"/>
                    </svg>
                    GRAP Compliance Validations
                </h3>
                <div class="formula-section-badge">Compliance</div>
            </div>
            
            <div class="grap-validations-list">
                ${grapValidations.map(validation => `
                    <div class="validation-item validation-${validation.status}">
                        <div class="validation-header">
                            <span class="validation-standard">${validation.grap_standard}</span>
                            <span class="validation-status">${validation.status.toUpperCase()}</span>
                        </div>
                        <div class="validation-line-item">${validation.line_item}</div>
                        <div class="validation-details">${validation.details}</div>
                        <div class="validation-meta">
                            <small>Validated by ${validation.validated_by} on ${VarydianUtils.formatDateTime(validation.validated_at)}</small>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
        
        modalBody.appendChild(section);
    }
    
    updateModalFooter(accessMode, processingStatus) {
        const modalActions = document.querySelector('.modal-actions');
        if (!modalActions) return;
        
        // Adjust button visibility based on access mode
        const exportButton = modalActions.querySelector('button[onclick="exportBreakdownPDF()"]');
        const sourceLedgerButton = modalActions.querySelector('button[onclick="viewRawBalanceSheet()"]');
        const modalFooter = modalActions.closest('.formula-modal-footer');
        
        // Clear existing read-only indicators
        const existingReadOnlyIndicator = modalActions.querySelector('.read-only-indicator');
        if (existingReadOnlyIndicator) {
            existingReadOnlyIndicator.remove();
        }
        
        if (accessMode === 'readonly' || accessMode === 'audit') {
            // Audit mode - read-only access
            if (exportButton) {
                exportButton.classList.add('display-inline-flex');
                exportButton.innerHTML = `
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
                        <polyline points="7,10 12,15 17,10"/>
                        <line x1="12" y1="15" x2="12" y2="3"/>
                    </svg>
                    Export Audit Report
                `;
            }
            
            if (sourceLedgerButton) {
                sourceLedgerButton.classList.add('display-inline-flex');
                sourceLedgerButton.innerHTML = `
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>
                        <polyline points="14,2 14,8 20,8"/>
                        <line x1="16" y1="13" x2="8" y2="13"/>
                        <line x1="16" y1="17" x2="8" y2="17"/>
                        <polyline points="10,9 9,9 8,9"/>
                    </svg>
                    View Source Ledger (Read-Only)
                `;
            }
            
            // Add read-only indicator
            this.addReadOnlyIndicator(modalActions, accessMode, processingStatus);
            
            // Add audit seal to footer
            if (modalFooter) {
                this.addAuditSeal(modalFooter);
            }
            
        } else if (accessMode === 'limited') {
            // Limited access - hide some features
            if (exportButton) exportButton.classList.add('display-none');
            if (sourceLedgerButton) sourceLedgerButton.classList.add('display-inline-flex');
            
            // Add limited access indicator
            this.addReadOnlyIndicator(modalActions, accessMode, processingStatus);
            
        } else {
            // Full access - show all features
            if (exportButton) {
                exportButton.classList.add('display-inline-flex');
                exportButton.innerHTML = `
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
                        <polyline points="7,10 12,15 17,10"/>
                        <line x1="12" y1="15" x2="12" y2="3"/>
                    </svg>
                    Export This Breakdown (PDF)
                `;
            }
            
            if (sourceLedgerButton) {
                sourceLedgerButton.classList.add('display-inline-flex');
                sourceLedgerButton.innerHTML = `
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>
                        <polyline points="14,2 14,8 20,8"/>
                        <line x1="16" y1="13" x2="8" y2="13"/>
                        <line x1="16" y1="17" x2="8" y2="17"/>
                        <polyline points="10,9 9,9 8,9"/>
                    </svg>
                    View raw session
                `;
            }
        }
        
        // Add processing status indicator
        if (processingStatus) {
            const statusIndicator = document.createElement('div');
            statusIndicator.className = 'processing-status-indicator';
            statusIndicator.innerHTML = `
                <span class="status-label">Processing Status:</span>
                <span class="status-value status-${processingStatus}">${this.formatProcessingStatus(processingStatus)}</span>
            `;
            
            const existingIndicator = modalActions.querySelector('.processing-status-indicator');
            if (existingIndicator) {
                existingIndicator.replaceWith(statusIndicator);
            } else {
                modalActions.insertBefore(statusIndicator, modalActions.firstChild);
            }
        }
    }
    
    addReadOnlyIndicator(modalActions, accessMode, processingStatus) {
        const indicator = document.createElement('div');
        indicator.className = 'read-only-indicator';
        
        let icon, text, modeClass;
        
        if (accessMode === 'readonly' || accessMode === 'audit') {
            icon = '🔒';
            text = 'Audit Mode - Read-Only Access';
            modeClass = 'audit-mode';
        } else if (accessMode === 'limited') {
            icon = '👁️';
            text = 'Limited Access - View Only';
            modeClass = 'limited-mode';
        }
        
        indicator.innerHTML = `
            <div class="read-only-icon">${icon}</div>
            <div class="read-only-text">
                <span class="read-only-title">${text}</span>
                <span class="read-only-subtitle">Period: ${processingStatus === 'finalized' ? 'Locked' : 'Active'}</span>
            </div>
        `;
        
        indicator.classList.add(modeClass);
        
        // Insert after processing status indicator or at the beginning
        const processingIndicator = modalActions.querySelector('.processing-status-indicator');
        if (processingIndicator) {
            processingIndicator.parentNode.insertBefore(indicator, processingIndicator.nextSibling);
        } else {
            modalActions.insertBefore(indicator, modalActions.firstChild);
        }
    }
    
    addAuditSeal(modalFooter) {
        // Check if audit seal already exists
        const existingSeal = modalFooter.querySelector('.audit-seal-enhanced');
        if (existingSeal) {
            return; // Already added
        }
        
        const seal = document.createElement('div');
        seal.className = 'audit-seal-enhanced';
        seal.innerHTML = `
            <div class="audit-seal-icon">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M12 2L2 7v10c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V7l-10-5z"/>
                    <path d="M12 22l8-8-8 8"/>
                </svg>
            </div>
            <div class="audit-seal-content">
                <div class="audit-seal-title">AUDIT VERIFIED</div>
                <div class="audit-seal-subtitle">Final Period Locked</div>
                <div class="audit-seal-timestamp">${VarydianUtils.formatDateTime(new Date())}</div>
            </div>
            <div class="audit-seal-stamp">
                <div class="stamp-text">AUDIT</div>
                <div class="stamp-year">${new Date().getFullYear()}</div>
            </div>
        `;
        
        // Insert before the modal actions
        const modalActions = modalFooter.querySelector('.modal-actions');
        if (modalActions) {
            modalFooter.insertBefore(seal, modalActions);
        }
    }

    updateVariablesGrid(variables) {
        const grid = document.getElementById('variablesGrid');
        if (!grid) return;

        grid.innerHTML = variables.map((variable) => {
            const src = variable.source || '';
            const hrefRaw = variable.linkHref && variable.linkLabel ? String(variable.linkHref) : '';
            const safeHref = this._safeHrefAttr(hrefRaw);
            const labelAttr = String(variable.linkLabel || '').replace(/&/g, '&amp;').replace(/"/g, '&quot;');
            const link =
                safeHref && variable.linkLabel
                    ? `<a href="${safeHref}" class="variable-source-link"
                        aria-label="${labelAttr}">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6"></path>
                        <polyline points="15,3 21,3 21,9"></polyline>
                        <line x1="10" y1="14" x2="21" y2="3"></line>
                    </svg>
                    ${this._escapeHtml(variable.linkLabel)}
                </a>`
                    : '';

            const hasLedgerLink = Boolean(FORMULA_SOURCE_LEDGER_URLS[src]);
            const safeName = String(variable.name || '').replace(/\\/g, '\\\\').replace(/'/g, "\\'");
            const ledgerBtn =
                !link && hasLedgerLink
                    ? `<button type="button" class="variable-source-link"
                        onclick="window.formulaModalController.viewSourceLedger('${src}', '${safeName}')"
                        aria-label="Open ${variable.sourceLabel || src} source">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6"></path>
                        <polyline points="15,3 21,3 21,9"></polyline>
                        <line x1="10" y1="14" x2="21" y2="3"></line>
                    </svg>
                    ${this._escapeHtml(variable.sourceLabel || variable.source || 'Source')}
                </button>`
                    : '';

            const action = link || ledgerBtn;

            return `
            <div class="variable-item">
                <div class="variable-label">${this._escapeHtml(variable.name)}</div>
                ${variable.detail ? `<p class="variable-detail">${this._escapeHtml(variable.detail)}</p>` : ''}
                <div class="variable-value">${this._escapeHtml(variable.value)}</div>
                ${action}
            </div>`;
        }).join('');
    }

    updateCalculationSteps(steps, finalResult = 'N/A', opts = {}) {
        const stepsContainer = document.getElementById('calculationSteps');
        if (!stepsContainer) return;

        const showFinalBand = opts.showFinalBand !== false;

        const stepList = Array.isArray(steps) ? steps : [];
        const esc = (html) => String(html || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
        const stepsHTML = stepList.map((step, index) => `
            <div class="calculation-step">
                <div class="step-number">${index + 1}</div>
                <div class="step-content">
                    <div class="step-formula">${esc(step.formula)}</div>
                    <div class="step-result">= ${esc(step.result)}</div>
                </div>
                ${index < stepList.length - 1 ? `
                    <div class="step-arrow">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <line x1="5" y1="12" x2="19" y2="12"></line>
                            <polyline points="12,5 19,12 12,19"></polyline>
                        </svg>
                    </div>
                ` : ''}
            </div>
        `).join('');

        stepsContainer.innerHTML = stepsHTML;

        if (!showFinalBand) {
            return;
        }

        const finalBlock = document.createElement('div');
        finalBlock.className = 'calculation-final';
        const labelEl = document.createElement('div');
        labelEl.className = 'final-label';
        labelEl.textContent = 'Final Result:';
        const valueEl = document.createElement('div');
        valueEl.className = 'final-value';
        valueEl.id = 'finalValue';
        const fv = finalResult != null && finalResult !== '' ? String(finalResult) : 'N/A';
        valueEl.textContent = fv;
        finalBlock.appendChild(labelEl);
        finalBlock.appendChild(valueEl);
        stepsContainer.appendChild(finalBlock);
    }

    showSyntheticReviewLine(sessionId, accountCode, grapCode, displayAmount) {
        if (!this.modal) return;
        this.setProcessingContext(sessionId, 'review');
        const itemName = accountCode ? `Account ${accountCode}` : 'Line item';
        const period = this.getCurrentReportingPeriod();
        const data = {
            grapReference: grapCode || 'GRAP',
            assetClass: 'Financial statement review',
            formula: 'Mapped trial balance amounts are classified to GRAP codes and aggregated into statement line items.',
            variables: [
                { name: 'Account code', value: accountCode || '—', source: 'tb', sourceLabel: 'Trial balance' },
                { name: 'GRAP code', value: grapCode || '—', source: 'mapping', sourceLabel: 'Mapping' }
            ],
            steps: [
                { formula: 'Source balance (from mapped TB)', result: displayAmount || '—' }
            ],
            finalResult: displayAmount || '—',
            accessMode: 'review',
            processingStatus: 'review'
        };
        this.updateModalContent(data, itemName, displayAmount || '—', period, grapCode || '');
        this.show();
    }

    showReviewSessionCalculations(review, sessionId) {
        if (!this.modal) return;
        this.setProcessingContext(sessionId, 'review');
        const period = this.getCurrentReportingPeriod();
        const sd = review.statementData;
        const ct = review.currentTransaction;

        const variables = [
            {
                name: 'Document upload session',
                detail: 'Stored record for this submission (upload & mapping)—not your login session.',
                value: sessionId,
                source: 'session',
                sourceLabel: 'Submission record',
            },
            { name: 'Document type', value: (ct && ct.transaction_type) || '—', source: 'session', sourceLabel: 'Type' },
            { name: 'File', value: (ct && ct.filename) || '—', source: 'session', sourceLabel: 'Upload' },
        ];
        if (sd && sd.period) {
            variables.push({ name: 'Period', value: String(sd.period), source: 'session', sourceLabel: 'Reporting' });
        }
        const lineCount = sd
            ? (sd.lines || []).length + (sd.positionLines || []).length + (sd.performanceLines || []).length
            : 0;
        if (lineCount) {
            variables.push({ name: 'Statement lines (rendered)', value: String(lineCount), source: 'session', sourceLabel: 'GRAP view' });
        }
        const mapCount = (sd && sd.mappings && sd.mappings.length) || 0;
        if (mapCount) {
            variables.push({ name: 'Account mappings', value: String(mapCount), source: 'mapping', sourceLabel: 'Trial balance' });
        }

        const calcs = (sd && sd.calculations) || [];
        const steps = calcs.map((c) => ({
            formula: `${c.description} — ${c.formula || 'derived'}`,
            result: typeof c.result === 'number' && !Number.isNaN(c.result)
                ? `R${this.formatModalNumber(c.result)}`
                : String(c.result ?? '—')
        }));

        let finalResult = '—';
        const surplus = calcs.find((c) => c && c.id === 'surplus' && typeof c.result === 'number');
        if (surplus) {
            finalResult = `R${this.formatModalNumber(surplus.result)} (surplus / deficit)`;
        } else if (calcs.length) {
            const last = calcs[calcs.length - 1];
            finalResult = typeof last.result === 'number' && !Number.isNaN(last.result)
                ? `R${this.formatModalNumber(last.result)}`
                : String(last.result ?? '—');
        } else if (steps.length) {
            finalResult = steps[steps.length - 1].result;
        }

        const data = {
            grapReference: 'GRAP',
            assetClass: 'Live session review',
            formula: 'Figures below are computed from the session payload returned by /api/universal/session (statement totals, sums of flattened lines, mapping counts, and database row counts). Line-level GRAP detail is on the Financial statements and Account Mappings tabs.',
            variables,
            steps: steps.length ? steps : [
                { formula: 'No derived calculation rows — session may not yet include financial_statements or mapping metadata', result: '—' }
            ],
            finalResult,
            accessMode: 'review',
            processingStatus: 'review'
        };
        this.updateModalContent(data, 'Session calculations (from loaded data)', finalResult, period, '');
        this.show();
    }

    showSyntheticSessionCalculations(sessionId) {
        if (!this.modal) return;
        this.setProcessingContext(sessionId, 'review');
        const period = this.getCurrentReportingPeriod();
        const data = {
            grapReference: 'GRAP',
            assetClass: 'Session',
            formula: 'Statement totals are built from all mapped accounts for this upload session (see Account Mappings tab).',
            variables: [
                {
                    name: 'Document upload session',
                    detail: 'Stored record for this submission—not your login session.',
                    value: sessionId,
                    source: 'session',
                    sourceLabel: 'Submission record',
                },
            ],
            steps: [
                { formula: 'Review mapped accounts and GRAP categories', result: 'See Mappings tab' }
            ],
            finalResult: '—',
            accessMode: 'review',
            processingStatus: 'review'
        };
        this.updateModalContent(data, 'Session calculations', '—', period, '');
        this.show();
    }

    show() {
        if (!this.modal) return;

        this.modal.classList.remove('visibility--hidden');
        this.modal.classList.remove('display-none');
        this.modal.classList.add('display-flex');
        this.isOpen = true;
        document.body.classList.add('overflow-hidden');
        
        // Focus management
        const firstFocusable = this.modal.querySelector('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
        if (firstFocusable) {
            firstFocusable.focus();
        }

        // Announce to screen readers
        this.announceToScreenReader('Formula breakdown modal opened');
    }

    close() {
        if (!this.modal) return;

        this.modal.classList.add('visibility--hidden');
        this.modal.classList.remove('display-flex');
        this.modal.classList.remove('display-none');
        this.isOpen = false;
        document.body.classList.remove('overflow-hidden');
        
        // Return focus to triggering element
        if (this.lastFocusedElement) {
            this.lastFocusedElement.focus();
        }

        // Announce to screen readers
        this.announceToScreenReader('Formula breakdown modal closed');
    }

    showLoading() {
        if (!this.modal) return;
        
        document.getElementById('modalTitle').textContent = 'Loading...';
        document.getElementById('auditReference').textContent = 'Loading formula data...';
        document.getElementById('variablesGrid').innerHTML = '<div class="loading-spinner">Loading formula data...</div>';
        document.getElementById('formulaExpression').textContent = 'Loading...';
        document.getElementById('calculationSteps').innerHTML = '<div class="loading-spinner">Loading calculation steps...</div>';
    }

    showError(message) {
        if (!this.modal) return;
        
        document.getElementById('modalTitle').textContent = 'Error';
        document.getElementById('auditReference').textContent = 'Unable to load data';
        document.getElementById('variablesGrid').innerHTML = `<div class="error-message">${message}</div>`;
        document.getElementById('formulaExpression').textContent = 'N/A';
        document.getElementById('calculationSteps').innerHTML = `<div class="error-message">${message}</div>`;
    }

    trapFocus(e) {
        const focusableElements = this.modal.querySelectorAll(
            'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        );
        const firstElement = focusableElements[0];
        const lastElement = focusableElements[focusableElements.length - 1];

        if (e.shiftKey) {
            if (document.activeElement === firstElement) {
                lastElement.focus();
                e.preventDefault();
            }
        } else {
            if (document.activeElement === lastElement) {
                firstElement.focus();
                e.preventDefault();
            }
        }
    }

    announceToScreenReader(message) {
        const announcement = document.createElement('div');
        announcement.setAttribute('aria-live', 'polite');
        announcement.setAttribute('aria-atomic', 'true');
        announcement.className = 'sr-only';
        announcement.textContent = message;
        document.body.appendChild(announcement);
        
        setTimeout(() => {
            document.body.removeChild(announcement);
        }, 1000);
    }

    loadFormulaDataCache() {
        // Formula data will be loaded on-demand from Supabase API
    }
    
    setProcessingContext(balanceSheetId, processingState) {
        // Set processing context for formula requests
        this.currentBalanceSheetId = balanceSheetId;
        this.currentProcessingState = processingState;
        
        // Clear cache when context changes
        if (balanceSheetId) {
            this.formulaData.clear();
        }
    }

    /**
     * Load formula modal content from GET /api/universal/session/<id>/formula-breakdown
     * (Supabase-backed session summary on the server).
     */
    async loadUniversalSessionBreakdown(sessionId, documentType, opts = {}) {
        if (!this.modal) {
            return;
        }
        const scope = opts.scope || 'session';
        const params = new URLSearchParams({ document_type: documentType, scope });
        if (opts.calcId != null && String(opts.calcId).trim() !== '') {
            params.set('calc_id', String(opts.calcId));
        }
        if (opts.accountCode) {
            params.set('account_code', String(opts.accountCode));
        }
        if (opts.grapCode) {
            params.set('grap_code', String(opts.grapCode));
        }
        this.setProcessingContext(sessionId, 'review');
        this.currentUniversalDocumentType = documentType;
        this.showLoading();
        this.show();
        const url = `/api/universal/session/${encodeURIComponent(sessionId)}/formula-breakdown?${params.toString()}`;
        const response = await fetch(url);
        const result = await response.json();
        if (!response.ok || !result.success) {
            const msg = (result && result.error) || `HTTP ${response.status}`;
            this.showError(msg);
            throw new Error(msg);
        }
        const data = result.data;
        const period = this.getCurrentReportingPeriod();
        const itemName = (data && data.itemName) ? data.itemName : 'Calculation';
        const currentValue = data && data.finalResult != null && data.finalResult !== ''
            ? String(data.finalResult)
            : '—';
        this.updateModalContent(data, itemName, currentValue, period, '');
    }
    
    clearProcessingContext() {
        // Clear processing context and revert to legacy mode
        this.currentBalanceSheetId = null;
        this.currentProcessingState = null;
        this.currentAccess = null;
        this.currentUniversalDocumentType = null;
    }

    // Action methods
    viewSourceLedger(sourceType, variableName) {
        const url = FORMULA_SOURCE_LEDGER_URLS[sourceType];
        if (url) {
            window.open(url, '_blank', 'width=1200,height=800,scrollbars=yes');
            return;
        }
        console.warn('[formula-modal] No source ledger URL for:', sourceType, variableName);
    }

    viewRawBalanceSheet() {
        if (
            this.currentProcessingState === 'review'
            && this.currentBalanceSheetId
            && this.currentUniversalDocumentType
        ) {
            const q = new URLSearchParams({ document_type: this.currentUniversalDocumentType });
            const u = `/api/universal/session/${encodeURIComponent(this.currentBalanceSheetId)}?${q.toString()}`;
            window.open(u, '_blank');
            return;
        }
        const bsUrl = '/accounting/balance-sheet';
        window.open(bsUrl, '_blank', 'width=1200,height=800,scrollbars=yes');
    }

    exportFormulaBreakdown() {
        const d = this.currentData;
        if (!d) {
            showAlert('Export Failed', 'Open a calculation breakdown first.');
            return;
        }
        const exportData = {
            itemName: d.itemName,
            period: d.period,
            formula: d.formula,
            result: d.result,
            finalResult: d.finalResult,
            variables: Array.isArray(d.variables) ? d.variables : [],
            steps: Array.isArray(d.steps) ? d.steps : [],
            grapReference: d.grapReference,
            assetClass: d.assetClass,
            auditReference:
                document.getElementById('auditReference')?.textContent?.trim()
                || d.auditReference
                || '',
            processingStatus: d.processingStatus,
            accessMode: d.accessMode,
            noteReference: d.noteReference,
            auditTrail: Array.isArray(d.auditTrail) ? d.auditTrail : [],
            timestamp: new Date().toISOString(),
            generatedBy: typeof window.currentUserFullName === 'string' ? window.currentUserFullName : '',
        };

        fetch('/api/formula/export/formula-breakdown-pdf', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest',
            },
            body: JSON.stringify(exportData),
        })
            .then((response) => {
                const ct = response.headers.get('Content-Type') || '';
                if (!response.ok) {
                    return response.json().then((body) => {
                        throw new Error(body.error || `HTTP ${response.status}`);
                    }).catch(() => {
                        throw new Error(`HTTP ${response.status}`);
                    });
                }
                if (!ct.includes('pdf')) {
                    return response.json().then((body) => {
                        throw new Error(body.error || 'Server did not return a PDF');
                    });
                }
                return response.blob();
            })
            .then((blob) => {
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                const base = String(d.itemName || 'breakdown')
                    .toLowerCase()
                    .replace(/\s+/g, '-')
                    .replace(/[^a-z0-9_-]/gi, '');
                a.href = url;
                a.download = `formula-breakdown-${base || 'breakdown'}-${Date.now()}.pdf`;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);
            })
            .catch((error) => {
                showAlert('Export Failed', error.message || 'PDF export failed. Please try again.');
            });
    }
}

// Global functions for button handlers (for compatibility with inline onclick)
function closeFormulaModal() {
    if (window.formulaModalController) {
        window.formulaModalController.close();
    }
}

function viewSourceLedger(sourceType, variableName) {
    if (window.formulaModalController) {
        window.formulaModalController.viewSourceLedger(sourceType, variableName);
    }
}

function viewRawBalanceSheet() {
    if (window.formulaModalController) {
        window.formulaModalController.viewRawBalanceSheet();
    }
}

function exportBreakdownPDF() {
    if (window.formulaModalController) {
        window.formulaModalController.exportFormulaBreakdown();
    }
}

// Initialize the controller when DOM is ready
window.formulaModalController = new FormulaModalController();

/** Adapter for financial-statement-review.js */
window.formulaModal = {
    loadFormulaData(sessionId) {
        const c = window.formulaModalController;
        if (!c || !sessionId) {
            return;
        }
        const review = window.financialStatementReview;
        const docType = review && review._documentType;
        if (docType) {
            c.loadUniversalSessionBreakdown(sessionId, docType, { scope: 'session' }).catch(() => {
                if (review && review.statementData) {
                    c.showReviewSessionCalculations(review, sessionId);
                } else {
                    c.showSyntheticSessionCalculations(sessionId);
                }
            });
            return;
        }
        if (review && review.statementData) {
            c.showReviewSessionCalculations(review, sessionId);
            return;
        }
        c.showSyntheticSessionCalculations(sessionId);
    },
    loadLineItemFormula(accountCode, grapCode) {
        const c = window.formulaModalController;
        if (!c) {
            return;
        }
        const review = window.financialStatementReview;
        const sessionId = review && (review._sessionId || (review.currentTransaction && review.currentTransaction.transaction_id));
        const docType = review && review._documentType;
        let displayAmount = '—';
        if (review && typeof review.findAccountData === 'function') {
            const line = review.findAccountData(accountCode);
            if (line && line.amount != null) {
                displayAmount = 'R' + parseFloat(line.amount).toLocaleString('en-ZA', {
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2
                });
            }
        }
        if (sessionId && docType) {
            c.loadUniversalSessionBreakdown(sessionId, docType, {
                scope: 'line',
                accountCode,
                grapCode
            }).catch(() => {
                c.showSyntheticReviewLine(sessionId, accountCode, grapCode, displayAmount);
            });
            return;
        }
        c.showSyntheticReviewLine(sessionId, accountCode, grapCode, displayAmount);
    },
    showModal() {
        window.formulaModalController && window.formulaModalController.show();
    }
};
