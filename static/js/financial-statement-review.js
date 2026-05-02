/**
 * SADPMR Financial Reporting System - Financial Statement Review
 * Integration with formula modal for Finance Manager review workflow
 */

class FinancialStatementReview {
    constructor() {
        this.currentTransaction = null;
        this.statementData = null;
        this.reviewMode = null;
        this.initializeReviewMode();
    }

    initializeReviewMode() {
        // Check if we're in review mode
        const urlParams = new URLSearchParams(window.location.search);
        if (urlParams.get('review') === 'statement') {
            this.reviewMode = 'statement';
            const transactionId = urlParams.get('transaction');
            if (transactionId) {
                this.loadStatementForReview(transactionId);
            } else {
                this.showError('No transaction ID provided for review');
            }
        }
    }

    async loadStatementForReview(transactionId) {
        try {
            // Load transaction details
            const transactionResponse = await fetch(`/api/transactions/${transactionId}`);
            const transactionResult = await transactionResponse.json();
            
            if (!transactionResult.success) {
                this.showError('Failed to load transaction details');
                return;
            }

            this.currentTransaction = transactionResult.transaction;

            // Load financial statement data
            const statementResponse = await fetch(`/api/financial-statement/${transactionId}`);
            const statementResult = await statementResponse.json();

            if (statementResult.success) {
                this.statementData = statementResult.statement;
                this.renderStatementReview();
            } else {
                this.showError('Failed to load financial statement data');
            }

        } catch (error) {
            this.showError('Network error loading statement data');
        }
    }

    renderStatementReview() {
        const container = document.getElementById('statementReviewContent');
        if (!container) return;

        const reviewHTML = `
            <div class="statement-review-container">
                <!-- Review Header -->
                <div class="review-header-info">
                    <div class="transaction-info">
                        <h3>${this.getTransactionTypeLabel(this.currentTransaction.transaction_type)}</h3>
                        <div class="transaction-meta">
                            <span class="transaction-id">${this.currentTransaction.transaction_id}</span>
                            <span class="creator">Created by ${this.currentTransaction.creator_name}</span>
                            <span class="created-date">${this.formatDate(this.currentTransaction.created_at)}</span>
                        </div>
                    </div>
                    <div class="review-actions">
                        <button class="btn btn-primary" data-action="view-calculations">
                            🔍 View Calculations
                        </button>
                        <button class="btn btn-success" data-action="approve-forward">
                            ✓ Approve & Forward to CFO
                        </button>
                        <button class="btn btn-danger" data-action="reject-with-comment">
                            ✗ Reject with Comments
                        </button>
                    </div>
                </div>

                <!-- Statement Content -->
                <div class="statement-content-section">
                    <div class="statement-tabs">
                        <button class="tab-btn active" data-tab="statement">Financial Statement</button>
                        <button class="tab-btn" data-tab="mappings">Account Mappings</button>
                        <button class="tab-btn" data-tab="calculations">Calculations</button>
                    </div>

                    <div class="tab-content">
                        <!-- Financial Statement Tab -->
                        <div class="tab-pane active" id="statement-tab">
                            ${this.renderFinancialStatement()}
                        </div>

                        <!-- Account Mappings Tab -->
                        <div class="tab-pane" id="mappings-tab">
                            ${this.renderAccountMappings()}
                        </div>

                        <!-- Calculations Tab -->
                        <div class="tab-pane" id="calculations-tab">
                            ${this.renderCalculationsSummary()}
                        </div>
                    </div>
                </div>

                <!-- Review Comments Section -->
                <div class="review-comments-section">
                    <h4>Review Comments & Notes</h4>
                    <div class="comments-container">
                        <div class="existing-comments" id="existingComments">
                            <!-- Existing comments will be loaded here -->
                        </div>
                        <div class="add-comment">
                            <textarea id="reviewComment" class="comment-textarea" placeholder="Add review comments or notes..."></textarea>
                            <div class="comment-actions">
                                <button class="btn btn-secondary btn-sm" data-action="save-comment">
                                    💾 Save Comment
                                </button>
                                <button class="btn btn-primary btn-sm" data-action="approve-with-comment">
                                    ✓ Approve with Comment
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;

        container.innerHTML = reviewHTML;
        this.attachReviewListeners();
        this.initializeTabs();
    }

    renderFinancialStatement() {
        if (!this.statementData) return '<p>No statement data available</p>';

        const statementType = this.currentTransaction.transaction_data?.statement_type || 'financial_position';
        
        return `
            <div class="financial-statement-review">
                <div class="statement-header">
                    <h3>${this.getStatementTitle(statementType)}</h3>
                    <div class="statement-period">
                        Period: ${this.statementData.period || 'FY 2025-2026'}
                    </div>
                </div>
                
                <div class="statement-table-container">
                    <table class="financial-statement-table review-table">
                        <thead>
                            <tr>
                                <th>Account Code</th>
                                <th>Account Description</th>
                                <th>Note</th>
                                <th class="amount-column">Amount (R)</th>
                                <th class="actions-column">Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${this.renderStatementLines(this.statementData.lines || [])}
                        </tbody>
                        <tfoot>
                            <tr class="total-row">
                                <td colspan="3"><strong>Total</strong></td>
                                <td class="amount-column"><strong>R${this.formatNumber(this.statementData.total || 0)}</strong></td>
                                <td></td>
                            </tr>
                        </tfoot>
                    </table>
                </div>
            </div>
        `;
    }

    renderStatementLines(lines) {
        return lines.map(line => `
            <tr class="statement-line" data-account-code="${line.account_code}" data-grap-code="${line.grap_code}">
                <td class="account-code">${line.account_code}</td>
                <td class="account-description">${line.description}</td>
                <td class="note-column">${line.note || '-'}</td>
                <td class="amount-column">R${this.formatNumber(line.amount || 0)}</td>
                <td class="actions-column">
                    <div class="line-actions">
                        <button class="btn btn-xs btn-secondary" data-action="view-calculation" data-account="${line.account_code}" data-grap="${line.grap_code}">
                            🔍 Formula
                        </button>
                        <button class="btn btn-xs btn-info" data-action="add-line-comment" data-account="${line.account_code}">
                            💬 Comment
                        </button>
                        ${line.has_mapping_issue ? `
                            <button class="btn btn-xs btn-warning" data-action="fix-mapping" data-account="${line.account_code}">
                                ⚠️ Fix Mapping
                            </button>
                        ` : ''}
                    </div>
                </td>
            </tr>
        `).join('');
    }

    renderAccountMappings() {
        if (!this.statementData) return '<p>No mapping data available</p>';

        const mappings = this.statementData.mappings || [];
        
        return `
            <div class="account-mappings-review">
                <div class="mappings-summary">
                    <div class="mapping-stats">
                        <div class="stat-item">
                            <span class="stat-value">${mappings.length}</span>
                            <span class="stat-label">Total Accounts</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-value">${mappings.filter(m => m.mapped).length}</span>
                            <span class="stat-label">Mapped</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-value">${mappings.filter(m => !m.mapped).length}</span>
                            <span class="stat-label">Unmapped</span>
                        </div>
                    </div>
                </div>
                
                <div class="mappings-table-container">
                    <table class="mappings-table">
                        <thead>
                            <tr>
                                <th>Trial Balance Account</th>
                                <th>GRAP Category</th>
                                <th>Mapping Status</th>
                                <th>Confidence</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${mappings.map(mapping => `
                                <tr class="mapping-row ${mapping.mapped ? 'mapped' : 'unmapped'}">
                                    <td>
                                        <div class="account-info">
                                            <span class="account-code">${mapping.tb_account_code}</span>
                                            <span class="account-desc">${mapping.tb_account_description}</span>
                                        </div>
                                    </td>
                                    <td>
                                        <div class="grap-info">
                                            <span class="grap-code">${mapping.grap_code}</span>
                                            <span class="grap-desc">${mapping.grap_description}</span>
                                        </div>
                                    </td>
                                    <td>
                                        <span class="mapping-status ${mapping.mapped ? 'status-mapped' : 'status-unmapped'}">
                                            ${mapping.mapped ? '✓ Mapped' : '⚠️ Unmapped'}
                                        </span>
                                    </td>
                                    <td>
                                        <div class="confidence-indicator">
                                            <div class="confidence-bar confidence-bar-dynamic" style="--confidence-width: ${mapping.confidence || 0}%"></div>
                                            <span class="confidence-text">${Math.round(mapping.confidence || 0)}%</span>
                                        </div>
                                    </td>
                                    <td>
                                        <div class="mapping-actions">
                                            <button class="btn btn-xs btn-secondary" data-action="edit-mapping" data-account="${mapping.tb_account_code}">
                                                ✏️ Edit
                                            </button>
                                            ${!mapping.mapped ? `
                                                <button class="btn btn-xs btn-primary" data-action="map-account" data-account="${mapping.tb_account_code}">
                                                    📍 Map
                                                </button>
                                            ` : ''}
                                        </div>
                                    </td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            </div>
        `;
    }

    renderCalculationsSummary() {
        if (!this.statementData) return '<p>No calculation data available</p>';

        const calculations = this.statementData.calculations || [];
        
        return `
            <div class="calculations-review">
                <div class="calculations-summary">
                    <h4>Calculation Summary</h4>
                    <div class="calc-stats">
                        <div class="stat-item">
                            <span class="stat-value">${calculations.length}</span>
                            <span class="stat-label">Calculations</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-value">${calculations.filter(c => c.verified).length}</span>
                            <span class="stat-label">Verified</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-value">${calculations.filter(c => !c.verified).length}</span>
                            <span class="stat-label">Need Review</span>
                        </div>
                    </div>
                </div>
                
                <div class="calculations-list">
                    ${calculations.map(calc => `
                        <div class="calculation-item ${calc.verified ? 'verified' : 'needs-review'}">
                            <div class="calc-header">
                                <h5>${calc.description}</h5>
                                <span class="calc-status ${calc.verified ? 'status-verified' : 'status-needs-review'}">
                                    ${calc.verified ? '✓ Verified' : '⚠️ Needs Review'}
                                </span>
                            </div>
                            <div class="calc-formula">
                                <strong>Formula:</strong> <code>${calc.formula}</code>
                            </div>
                            <div class="calc-result">
                                <strong>Result:</strong> R${this.formatNumber(calc.result)}
                            </div>
                            <div class="calc-actions">
                                <button class="btn btn-xs btn-primary" data-action="view-calculation-detail" data-calc-id="${calc.id}">
                                    🔍 View Details
                                </button>
                                ${!calc.verified ? `
                                    <button class="btn btn-xs btn-success" data-action="verify-calculation" data-calc-id="${calc.id}">
                                        ✓ Verify
                                    </button>
                                ` : ''}
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }

    attachReviewListeners() {
        // Main action buttons
        document.querySelector('[data-action="view-calculations"]')?.addEventListener('click', () => {
            this.openFormulaModal();
        });

        document.querySelector('[data-action="approve-forward"]')?.addEventListener('click', () => {
            this.approveAndForward();
        });

        document.querySelector('[data-action="reject-with-comment"]')?.addEventListener('click', () => {
            this.rejectWithComment();
        });

        // Line item actions
        document.querySelectorAll('[data-action="view-calculation"]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const accountCode = e.target.dataset.account;
                const grapCode = e.target.dataset.grap;
                this.viewLineItemCalculation(accountCode, grapCode);
            });
        });

        document.querySelectorAll('[data-action="add-line-comment"]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const accountCode = e.target.dataset.account;
                this.addLineItemComment(accountCode);
            });
        });

        // Tab switching
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.switchTab(e.target.dataset.tab);
            });
        });
    }

    initializeTabs() {
        // Tab functionality is handled by switchTab method
    }

    switchTab(tabName) {
        // Update tab buttons
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tab === tabName);
        });

        // Update tab panes
        document.querySelectorAll('.tab-pane').forEach(pane => {
            pane.classList.toggle('active', pane.id === `${tabName}-tab`);
        });
    }

    openFormulaModal() {
        if (window.formulaModal) {
            // Load formula data for the current statement
            window.formulaModal.loadFormulaData(this.currentTransaction.transaction_id);
            window.formulaModal.showModal();
        } else {
            this.showError('Formula modal not available');
        }
    }

    viewLineItemCalculation(accountCode, grapCode) {
        if (window.formulaModal) {
            window.formulaModal.loadLineItemFormula(accountCode, grapCode);
            window.formulaModal.showModal();
        } else {
            this.showError('Formula modal not available');
        }
    }

    addLineItemComment(accountCode) {
        // Find account data from statement
        const accountData = this.findAccountData(accountCode);
        
        if (window.lineItemCommentSystem && this.currentTransaction) {
            window.lineItemCommentSystem.openModal(accountCode, accountData, this.currentTransaction.transaction_id);
        } else {
            // Fallback to simple prompt
            const comment = prompt(`Add comment for account ${accountCode}:`);
            if (comment) {
                this.saveLineItemComment(accountCode, comment);
            }
        }
    }

    findAccountData(accountCode) {
        if (!this.statementData || !this.statementData.lines) return {};
        
        const line = this.statementData.lines.find(l => l.account_code === accountCode);
        return line || {
            account_code: accountCode,
            description: 'Unknown Account',
            grap_code: '',
            amount: 0
        };
    }

    async approveAndForward() {
        const reason = prompt('Please provide approval reason for forwarding to CFO:') || 'Approved by Finance Manager - calculations verified';
        
        try {
            const response = await fetch(`/api/transaction/approve/${this.currentTransaction.transaction_id}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ reason })
            });

            const result = await response.json();
            
            if (result.success) {
                // Generate Manager's Certificate
                await this.generateManagersCertificate();
                
                this.showSuccess('Transaction approved and forwarded to CFO');
                setTimeout(() => {
                    window.location.href = '/approvals';
                }, 2000);
            } else {
                this.showError(result.error);
            }
        } catch (error) {
            this.showError('Failed to approve transaction');
        }
    }

    async rejectWithComment() {
        const comment = document.getElementById('reviewComment').value;
        const reason = prompt('Please provide rejection reason:') || 'Rejected by Finance Manager';
        
        if (!reason && !comment) {
            this.showError('Please provide a reason for rejection');
            return;
        }

        try {
            const response = await fetch(`/api/transaction/reject/${this.currentTransaction.transaction_id}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ reason: reason + (comment ? `\n\nComments: ${comment}` : '') })
            });

            const result = await response.json();
            
            if (result.success) {
                this.showSuccess('Transaction rejected with comments');
                setTimeout(() => {
                    window.location.href = '/approvals';
                }, 2000);
            } else {
                this.showError(result.error);
            }
        } catch (error) {
            this.showError('Failed to reject transaction');
        }
    }

    async generateManagersCertificate() {
        try {
            const response = await fetch(`/api/certificate/generate/${this.currentTransaction.transaction_id}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });

            const result = await response.json();
            
            if (result.success) {
                // Download the certificate
                const link = document.createElement('a');
                link.href = result.certificate_url;
                link.download = result.certificate_filename;
                link.click();
            } else {
                // Failed to generate certificate
            }
        } catch (error) {
            // Error generating certificate
        }
    }

    // Helper methods
    getTransactionTypeLabel(type) {
        const labels = {
            'financial_statement': 'Financial Statement',
            'journal_entry': 'Journal Entry',
            'asset_impairment': 'Asset Impairment',
            'budget_adjustment': 'Budget Adjustment'
        };
        return labels[type] || type.replace('_', ' ').toUpperCase();
    }

    getStatementTitle(type) {
        const titles = {
            'financial_position': 'Statement of Financial Position',
            'financial_performance': 'Statement of Financial Performance',
            'cash_flows': 'Statement of Cash Flows'
        };
        return titles[type] || 'Financial Statement';
    }

    formatNumber(num) {
        return parseFloat(num || 0).toLocaleString('en-ZA', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
    }

    formatDate(dateString) {
        return SADPMRUtils.formatDate(dateString);
    }

    showSuccess(message) {
        this.showNotification(message, 'success');
    }

    showError(message) {
        this.showNotification(message, 'error');
    }

    showNotification(message, type) {
        const notification = document.createElement('div');
        notification.className = `notification notification--${type}`;
        notification.innerHTML = `
            <div class="notification-content">
                <span class="notification-message">${message}</span>
                <button class="notification-close" onclick="this.parentElement.parentElement.remove()">✕</button>
            </div>
        `;

        document.body.appendChild(notification);
        setTimeout(() => {
            if (notification.parentElement) {
                notification.remove();
            }
        }, 5000);
    }
}

// Initialize Financial Statement Review
document.addEventListener('DOMContentLoaded', () => {
    window.financialStatementReview = new FinancialStatementReview();
});

// Export for use in other scripts
window.FinancialStatementReview = FinancialStatementReview;
