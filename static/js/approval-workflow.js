/**
 * SADPMR Financial Reporting System - Four-Eyes Approval Workflow
 * JavaScript for transaction approval UI and workflow management
 */

class ApprovalWorkflow {
    constructor() {
        this.currentTransaction = null;
        this.pendingTransactions = [];
        this.approvalHistory = [];
        this.currentUser = null;
        this.initializeEventListeners();
    }

    initializeEventListeners() {
        // Transaction creation form
        const createForm = document.getElementById('createTransactionForm');
        if (createForm) {
            createForm.addEventListener('submit', this.handleCreateTransaction.bind(this));
        }

        // Approval buttons
        document.addEventListener('click', (e) => {
            if (e.target.matches('.approve-btn')) {
                this.handleApprove(e.target.dataset.transactionId);
            } else if (e.target.matches('.reject-btn')) {
                this.handleReject(e.target.dataset.transactionId);
            } else if (e.target.matches('.finalize-btn')) {
                this.handleFinalize(e.target.dataset.transactionId);
            }
        });

        // Load pending transactions on page load only if user has review permission
        this.loadPendingTransactionsIfPermitted();
    }

    async handleCreateTransaction(e) {
        e.preventDefault();
        
        const formData = new FormData(e.target);
        const transactionData = {
            transaction_type: formData.get('transaction_type'),
            transaction_data: {
                account_code: formData.get('account_code'),
                account_description: formData.get('account_description'),
                amount: parseFloat(formData.get('amount')),
                debit_credit: formData.get('debit_credit')
            },
            reason: formData.get('reason')
        };

        try {
            const response = await fetch('/api/transaction/create', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(transactionData)
            });

            const result = await response.json();
            
            if (result.success) {
                this.showSuccess('Transaction created and pending approval');
                e.target.reset();
                this.loadPendingTransactions();
                this.updateTransactionStatus(result.transaction);
            } else {
                this.showError(result.error);
            }
        } catch (error) {
            this.showError('Failed to create transaction: ' + error.message);
        }
    }

    async handleApprove(transactionId) {
        const reason = prompt('Please provide approval reason:');
        if (!reason) return;

        try {
            const response = await fetch(`/api/transaction/approve/${transactionId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ reason })
            });

            const result = await response.json();
            
            if (result.success) {
                this.showSuccess('Transaction approved successfully');
                this.loadPendingTransactions();
                this.updateTransactionStatus(result.transaction);
                
                if (result.fully_approved) {
                    this.showInfo('Transaction is fully approved and ready for finalization');
                }
            } else {
                this.showError(result.error);
            }
        } catch (error) {
            this.showError('Failed to approve transaction: ' + error.message);
        }
    }

    async handleReject(transactionId) {
        const reason = prompt('Please provide rejection reason:');
        if (!reason) return;

        try {
            const response = await fetch(`/api/transaction/reject/${transactionId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ reason })
            });

            const result = await response.json();
            
            if (result.success) {
                this.showSuccess('Transaction rejected');
                this.loadPendingTransactions();
                this.removeTransactionFromUI(transactionId);
            } else {
                this.showError(result.error);
            }
        } catch (error) {
            this.showError('Failed to reject transaction: ' + error.message);
        }
    }

    async handleFinalize(transactionId) {
        if (!confirm('Are you sure you want to finalize this transaction? This action cannot be undone.')) {
            return;
        }

        try {
            const response = await fetch(`/api/transaction/finalize/${transactionId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });

            const result = await response.json();
            
            if (result.success) {
                this.showSuccess('Transaction finalized successfully');
                this.loadPendingTransactions();
                this.updateTransactionStatus(result.transaction);
                this.removeTransactionFromUI(transactionId);
            } else {
                this.showError(result.error);
            }
        } catch (error) {
            this.showError('Failed to finalize transaction: ' + error.message);
        }
    }

    async loadPendingTransactions() {
        try {
            const response = await fetch('/api/transactions/pending');
            const result = await response.json();
            
            if (result.success) {
                this.pendingTransactions = result.pending_transactions;
                this.renderPendingTransactions();
            }
        } catch (error) {
            // Failed to load pending transactions
        }
    }

    async loadPendingTransactionsIfPermitted() {
        // Check if current user has review permission before loading
        try {
            const response = await fetch('/api/user/permissions');
            
            // Check if response is OK before trying to parse JSON
            if (!response.ok) {
                return;
            }
            
            const result = await response.json();
            
            if (result.success && result.permissions && result.permissions.can_review) {
                await this.loadPendingTransactions();
            } else {
                // User doesn't have review permission, show appropriate message
                
                // Hide pending transactions section if it exists
                const pendingSection = document.querySelector('.approval-section:has(#pendingTransactionsContainer)');
                if (pendingSection) {
                    pendingSection.classList.add('section-hidden');
                }
                
                // Show access denied message
                this.showAccessDeniedMessage();
            }
        } catch (error) {
            // Error checking permissions
        }
    }

    showAccessDeniedMessage() {
        const container = document.getElementById('pendingTransactionsContainer');
        if (container) {
            container.innerHTML = `
                <div class="approval-section approval-restricted-section">
                    <div class="card approval-restricted-card">
                        <div class="card-header">
                            <h3>Access Restricted</h3>
                        </div>
                        <div class="card-body">
                            <div class="approval-restricted-icon">🔒</div>
                            <p class="approval-restricted-message">
                                You do not have permission to review pending transactions.
                            </p>
                            <p class="approval-restricted-details">
                                <strong>Required Role:</strong> Finance Manager, CFO, Accountant, or System Administrator
                            </p>
                            <p class="approval-restricted-details">
                                <strong>Your Current Role:</strong> <span id="currentUserRole">Loading...</span>
                            </p>
                            <div class="approval-restricted-note">
                                <strong>Note:</strong> Contact your administrator to request the appropriate role assignment if you need review access.
                            </div>
                        </div>
                    </div>
                </div>
            `;
            
            // Load current user role
            this.loadCurrentUserRole();
        }
    }

    async loadCurrentUserRole() {
        try {
            const response = await fetch('/api/user/permissions');
            if (response.ok) {
                const result = await response.json();
                if (result.success && result.role) {
                    const roleElement = document.getElementById('currentUserRole');
                    if (roleElement) {
                        roleElement.textContent = result.role;
                    }
                }
            }
        } catch (error) {
            // Error loading current user role
        }
    }

    renderPendingTransactions() {
        const container = document.getElementById('pendingTransactionsContainer');
        if (!container) return;

        if (this.pendingTransactions.length === 0) {
            container.innerHTML = `
                <div class="approval-empty-state">
                    <div class="approval-empty-icon">📋</div>
                    <h3>No Pending Transactions</h3>
                    <p>All transactions have been processed.</p>
                </div>
            `;
            return;
        }

        const transactionsHTML = this.pendingTransactions.map(transaction => `
            <div class="approval-card" data-transaction-id="${transaction.transaction_id}">
                <div class="approval-header">
                    <div class="approval-info">
                        <h4>${transaction.transaction_type.replace('_', ' ').toUpperCase()}</h4>
                        <span class="approval-id">${transaction.transaction_id}</span>
                    </div>
                    <div class="approval-status approval-status--${transaction.status}">
                        ${this.getStatusLabel(transaction.status)}
                    </div>
                </div>
                
                <div class="approval-details">
                    <div class="approval-creator">
                        <strong>Created by:</strong> ${transaction.creator_name}
                    </div>
                    <div class="approval-date">
                        <strong>Created:</strong> ${this.formatDate(transaction.created_at)}
                    </div>
                    ${transaction.reason ? `
                        <div class="approval-reason">
                            <strong>Reason:</strong> ${transaction.reason}
                        </div>
                    ` : ''}
                </div>

                <div class="approval-approvals">
                    <h5>Required Approvals:</h5>
                    <div class="approval-required-list">
                        ${transaction.required_approvals.map(role => `
                            <span class="approval-role-badge approval-role--${role.toLowerCase()}">${role}</span>
                        `).join('')}
                    </div>
                    
                    ${transaction.current_approvals.length > 0 ? `
                        <div class="approval-current-list">
                            <h6>Current Approvals:</h6>
                            ${transaction.current_approvals.map(approval => `
                                <div class="approval-item">
                                    <span class="approval-approver">${approval.approver_name}</span>
                                    <span class="approval-role">${approval.approver_role}</span>
                                    <span class="approval-date">${this.formatDate(approval.approved_at)}</span>
                                    <span class="approval-reason">"${approval.reason}"</span>
                                </div>
                            `).join('')}
                        </div>
                    ` : ''}
                </div>

                <div class="approval-actions">
                    ${this.renderApprovalActions(transaction)}
                </div>
            </div>
        `).join('');

        container.innerHTML = transactionsHTML;
    }

    renderApprovalActions(transaction) {
        const userRole = this.getCurrentUserRole();
        const actions = [];

        // Check if user can approve
        if (userRole && transaction.required_approvals.includes(userRole)) {
            const alreadyApproved = transaction.current_approvals.some(
                approval => approval.approver_role === userRole
            );

            if (!alreadyApproved) {
                actions.push(`
                    <button class="btn btn-success approve-btn" data-transaction-id="${transaction.transaction_id}">
                        ✓ Approve
                    </button>
                `);
            }
        }

        // Check if user can reject (same permissions as approve)
        if (userRole && transaction.required_approvals.includes(userRole)) {
            actions.push(`
                <button class="btn btn-danger reject-btn" data-transaction-id="${transaction.transaction_id}">
                    ✗ Reject
                </button>
            `);
        }

        // Check if user can finalize (CFO only)
        if (userRole === 'CFO' && transaction.status === 'approved') {
            actions.push(`
                <button class="btn btn-primary finalize-btn" data-transaction-id="${transaction.transaction_id}">
                    ⚡ Finalize
                </button>
            `);
        }

        // View approval chain
        actions.push(`
            <button class="btn btn-secondary" onclick="approvalWorkflow.viewApprovalChain('${transaction.transaction_id}')">
                👁 View Chain
            </button>
        `);

        return actions.join('');
    }

    async viewApprovalChain(transactionId) {
        try {
            const response = await fetch(`/api/transactions/approval-chain/${transactionId}`);
            const result = await response.json();
            
            if (result.success) {
                this.showApprovalChainModal(result.approval_chain, result.source, result.transaction_status);
            } else {
                this.showError(`Failed to load approval chain: ${result.error}`);
            }
        } catch (error) {
            this.showError('Failed to load approval chain: ' + error.message);
        }
    }

    showApprovalChainModal(chain, source = 'unknown', status = null) {
        const modal = document.createElement('div');
        modal.className = 'approval-chain-modal';
        modal.innerHTML = `
            <div class="approval-chain-overlay">
                <div class="approval-chain-content">
                    <div class="approval-chain-header">
                        <h3>Approval Chain</h3>
                        <div class="approval-chain-meta">
                            <span class="source-indicator source-indicator--${source}">${source.toUpperCase()}</span>
                            ${status ? `<span class="status-indicator status-indicator--${status}">${status.replace('_', ' ').toUpperCase()}</span>` : ''}
                        </div>
                        <button class="approval-chain-close" onclick="this.closest('.approval-chain-modal').remove()">✕</button>
                    </div>
                    <div class="approval-chain-body">
                        ${chain.map(step => `
                            <div class="approval-chain-step approval-chain-step--${step.action}">
                                <div class="step-header">
                                    <span class="step-action">${step.action.toUpperCase()}</span>
                                    <span class="step-time">${this.formatDate(step.timestamp)}</span>
                                </div>
                                <div class="step-details">
                                    <div class="step-user">
                                        <strong>User:</strong> ${step.user_name} (${step.user_id})
                                        ${step.user_role ? `<span class="step-role">${step.user_role}</span>` : ''}
                                    </div>
                                    ${step.reason ? `
                                        <div class="step-reason">
                                            <strong>Reason:</strong> ${step.reason}
                                        </div>
                                    ` : ''}
                                    <div class="step-meta">
                                        <div class="step-ip">
                                            <strong>IP Address:</strong> ${step.ip_address || 'N/A'}
                                        </div>
                                        <div class="step-session">
                                            <strong>Session:</strong> ${step.session_id || 'N/A'}
                                        </div>
                                        <div class="step-entity">
                                            <strong>Entity:</strong> ${step.entity_type} (${step.entity_id})
                                        </div>
                                    </div>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
    }

    updateTransactionStatus(transaction) {
        const element = document.querySelector(`[data-transaction-id="${transaction.transaction_id}"]`);
        if (element) {
            // Update status badge
            const statusBadge = element.querySelector('.approval-status');
            if (statusBadge) {
                statusBadge.className = `approval-status approval-status--${transaction.status}`;
                statusBadge.textContent = this.getStatusLabel(transaction.status);
            }

            // Update approvals section
            const approvalsSection = element.querySelector('.approval-approvals');
            if (approvalsSection) {
                approvalsSection.innerHTML = `
                    <h5>Required Approvals:</h5>
                    <div class="approval-required-list">
                        ${transaction.required_approvals.map(role => `
                            <span class="approval-role-badge approval-role--${role.toLowerCase()}">${role}</span>
                        `).join('')}
                    </div>
                    
                    ${transaction.current_approvals.length > 0 ? `
                        <div class="approval-current-list">
                            <h6>Current Approvals:</h6>
                            ${transaction.current_approvals.map(approval => `
                                <div class="approval-item">
                                    <span class="approval-approver">${approval.approver_name}</span>
                                    <span class="approval-role">${approval.approver_role}</span>
                                    <span class="approval-date">${this.formatDate(approval.approved_at)}</span>
                                    <span class="approval-reason">"${approval.reason}"</span>
                                </div>
                            `).join('')}
                        </div>
                    ` : ''}
                `;

                // Update actions
                const actionsSection = element.querySelector('.approval-actions');
                if (actionsSection) {
                    actionsSection.innerHTML = this.renderApprovalActions(transaction);
                }
            }
        }
    }

    removeTransactionFromUI(transactionId) {
        const element = document.querySelector(`[data-transaction-id="${transactionId}"]`);
        if (element) {
            element.classList.add('removing');
            setTimeout(() => element.remove(), 300);
        }
    }

    getStatusLabel(status) {
        const labels = {
            'pending_approval': 'Pending Approval',
            'approved': 'Approved',
            'rejected': 'Rejected',
            'finalized': 'Finalized'
        };
        return labels[status] || status;
    }

    formatDate(dateString) {
        return SADPMRUtils.formatDate(dateString);
    }

    getCurrentUserRole() {
        // This should be populated from the template
        return window.currentUserRole || null;
    }

    showSuccess(message) {
        this.showNotification(message, 'success');
    }

    showError(message) {
        this.showNotification(message, 'error');
    }

    showInfo(message) {
        this.showNotification(message, 'info');
    }

    showNotification(message, type) {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification notification--${type}`;
        notification.innerHTML = `
            <div class="notification-content">
                <span class="notification-message">${message}</span>
                <button class="notification-close" onclick="this.parentElement.parentElement.remove()">✕</button>
            </div>
        `;

        // Add to page
        document.body.appendChild(notification);

        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (notification.parentElement) {
                notification.remove();
            }
        }, 5000);
    }
}

// Initialize the approval workflow
const approvalWorkflow = new ApprovalWorkflow();

// Export for use in other scripts
window.approvalWorkflow = approvalWorkflow;
