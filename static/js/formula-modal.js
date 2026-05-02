/**
 * Formula Transparency Modal JavaScript Controller
 * Handles formula breakdown display for CFO and AUDITOR roles
 */

class FormulaModalController {
    constructor() {
        this.currentData = null;
        this.modal = null;
        this.isOpen = false;
        this.formulaData = new Map(); // Cache formula data
        this.currentTrialBalanceId = null;
        this.currentProcessingState = null;
        this.currentAccess = null;
        this.initializeEventListeners();
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
            }
        });
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
        const cacheKey = `${this.currentTrialBalanceId || 'legacy'}_${lineItemId}`;
        if (this.formulaData.has(cacheKey)) {
            return this.formulaData.get(cacheKey);
        }

        // Show loading
        this.showLoading();

        try {
            // Determine API endpoint based on processing state
            let apiUrl;
            if (this.currentTrialBalanceId && this.currentProcessingState) {
                // Use processing state-aware endpoint
                apiUrl = `/api/formula/breakdown/${this.currentTrialBalanceId}/${lineItemId}`;
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
        let auditText = `${data.grapReference} Asset Class: ${data.assetClass} | Period: ${period}`;
        
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
        
        // Update calculation steps
        this.updateCalculationSteps(data.steps);
        
        // Update final result
        document.getElementById('finalValue').textContent = data.finalResult;
        
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
                    Mapped Trial Balance Accounts
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
                            <small>Mapped by ${mapping.mapped_by} on ${new Date(mapping.mapped_at).toLocaleDateString()}</small>
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
                            <small>Validated by ${validation.validated_by} on ${new Date(validation.validated_at).toLocaleDateString()}</small>
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
        const sourceLedgerButton = modalActions.querySelector('button[onclick="viewRawTrialBalance()"]');
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
                    View Raw Trial Balance Data
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
                <div class="audit-seal-timestamp">${new Date().toLocaleDateString()}</div>
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

        grid.innerHTML = variables.map(variable => `
            <div class="variable-item">
                <div class="variable-label">${variable.name}</div>
                <div class="variable-value">${variable.value}</div>
                <button type="button" class="variable-source-link" 
                        onclick="window.formulaModalController.viewSourceLedger('${variable.source}', '${variable.name}')"
                        aria-label="View ${variable.sourceLabel}">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6"></path>
                        <polyline points="15,3 21,3 21,9"></polyline>
                        <line x1="10" y1="14" x2="21" y2="3"></line>
                    </svg>
                    ${variable.sourceLabel}
                </button>
            </div>
        `).join('');
    }

    updateCalculationSteps(steps) {
        const stepsContainer = document.getElementById('calculationSteps');
        if (!stepsContainer) return;

        const stepsHTML = steps.map((step, index) => `
            <div class="calculation-step">
                <div class="step-number">${index + 1}</div>
                <div class="step-content">
                    <div class="step-formula">${step.formula}</div>
                    <div class="step-result">= ${step.result}</div>
                </div>
                ${index < steps.length - 1 ? `
                    <div class="step-arrow">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <line x1="5" y1="12" x2="19" y2="12"></line>
                            <polyline points="12,5 19,12 12,19"></polyline>
                        </svg>
                    </div>
                ` : ''}
            </div>
        `).join('');

        stepsContainer.innerHTML = stepsHTML + `
            <div class="calculation-final">
                <div class="final-label">Final Result:</div>
                <div class="final-value">${this.currentData?.finalResult || 'N/A'}</div>
            </div>
        `;
    }

    show() {
        if (!this.modal) return;
        
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
        
        this.modal.classList.add('display-none');
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
    
    setProcessingContext(trialBalanceId, processingState) {
        // Set processing context for formula requests
        this.currentTrialBalanceId = trialBalanceId;
        this.currentProcessingState = processingState;
        
        // Clear cache when context changes
        if (trialBalanceId) {
            this.formulaData.clear();
        }
    }
    
    clearProcessingContext() {
        // Clear processing context and revert to legacy mode
        this.currentTrialBalanceId = null;
        this.currentProcessingState = null;
        this.currentAccess = null;
    }

    // Action methods
    viewSourceLedger(sourceType, variableName) {
        // Create a new modal or navigate to source
        const sourceUrls = {
            'asset_sub_ledger': '/assets/sub-ledger',
            'depreciation_schedule': '/assets/depreciation-schedule',
            'asset_register': '/assets/register',
            'asset_policy': '/policies/asset-management',
            'loan_register': '/liabilities/loan-register',
            'loan_agreement': '/liabilities/loan-agreements',
            'loan_schedule': '/liabilities/loan-schedules',
            'impairment_test': '/assets/impairment-tests',
            'general_ledger': '/accounting/general-ledger'
        };

        const url = sourceUrls[sourceType];
        if (url) {
            // Open in new tab or modal
            window.open(url, '_blank', 'width=1200,height=800,scrollbars=yes');
        } else {
            alert(`Source ledger for ${sourceType} is not available in this demo.`);
        }
    }

    viewRawTrialBalance() {
        // Navigate to trial balance or open in modal
        const tbUrl = '/accounting/trial-balance';
        window.open(tbUrl, '_blank', 'width=1200,height=800,scrollbars=yes');
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

exportFormulaBreakdown() {
    // Create PDF export request
    const exportData = {
        itemName: this.currentData.itemName,
        formula: this.currentData.formula,
        result: this.currentData.result,
        auditReference: this.currentData.auditReference,
        timestamp: new Date().toISOString()
    };

    // Send to backend for PDF generation
    fetch('/api/export/formula-breakdown-pdf', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        },
        body: JSON.stringify(exportData)
    })
        .then(response => {
            if (response.ok) {
                return response.blob();
            }
            throw new Error('PDF export failed');
        })
        .then(blob => {
            // Download the PDF
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `formula-breakdown-${this.currentData.itemName.toLowerCase().replace(/\s+/g, '-')}-${Date.now()}.pdf`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        })
        .catch(error => {
            alert('PDF export failed. Please try again.');
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

function viewRawTrialBalance() {
    if (window.formulaModalController) {
        window.formulaModalController.viewRawTrialBalance();
    }
}

function exportBreakdownPDF() {
    if (window.formulaModalController) {
        window.formulaModalController.exportBreakdownPDF();
    }
}

// Initialize the controller when DOM is ready
window.formulaModalController = new FormulaModalController();
