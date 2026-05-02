/**
 * SADPMR Financial Reporting System - Finance Manager Dashboard
 * Enhanced approvals queue and financial statement review functionality
 */

// Prevent duplicate class declaration
if (typeof FinanceManagerDashboard === 'undefined') {
class FinanceManagerDashboard {
    constructor() {
        // Early exit if not on dashboard page
        if (!this.isCurrentPageDashboard()) {
            return;
        }
        
        this.approvalQueue = [];
        this.filters = {
            submissionType: 'all',
            priority: 'all',
            dateRange: 'all'
        };
        this.searchQuery = '';
        this.currentUser = null;
        this.initialized = false;
        
        // Wait for DOM to be ready before initializing
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.initialize());
        } else {
            // DOM is already ready
            this.initialize();
        }
    }

    isCurrentPageDashboard() {
        // Check if current page is dashboard by looking at URL or path
        const currentPath = window.location.pathname;
        return currentPath === '/' || currentPath === '/dashboard' || 
               currentPath.endsWith('/dashboard');
    }

    initialize() {
        // Only initialize if we're on the dashboard page and haven't initialized yet
        if (this.initialized || !this.isDashboardPage()) {
            return;
        }
        
        this.initialized = true;
        this.initializeEventListeners();
        this.loadApprovalQueue();
    }

    isDashboardPage() {
        // Check if we're on the dashboard page by looking for dashboard-specific elements
        return document.getElementById('pendingCount') !== null;
    }

    initializeEventListeners() {
        // Search input handler
        const searchInput = document.getElementById('queueSearchInput');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                this.searchQuery = e.target.value.toLowerCase().trim();
                this.renderApprovalQueue();
            });
        }

        // Filter change handlers
        document.querySelectorAll('[data-filter]').forEach(filter => {
            filter.addEventListener('change', (e) => {
                this.filters[e.target.dataset.filter] = e.target.value;
                this.renderApprovalQueue();
            });
        });

        // Refresh button
        document.querySelector('[data-action="refresh-queue"]')?.addEventListener('click', () => {
            this.loadApprovalQueue();
        });

        // Auto-refresh every 30 seconds
        setInterval(() => {
            this.loadApprovalQueue();
        }, 30000);
    }

    async loadApprovalQueue() {
        // Only load if we're on the dashboard page (protects against auto-refresh)
        if (!this.initialized || !this.isDashboardPage()) {
            return;
        }

        try {
            const response = await fetch('/api/transactions/pending');
            const result = await response.json();
            
            if (result.success) {
                this.approvalQueue = result.pending_transactions;
                this.updateQueueStats();
                this.renderApprovalQueue();
            } else {
                this.showError('Failed to load approval queue');
            }
        } catch (error) {
            this.showError('Network error loading approval queue');
        }
    }

    updateQueueStats() {
        // Only update if we're initialized and on the dashboard page
        if (!this.initialized || !this.isDashboardPage()) {
            return;
        }

        const pendingCount = this.approvalQueue.length;
        const highPriorityCount = this.approvalQueue.filter(tx => 
            this.getPriorityLevel(tx) === 'high'
        ).length;
        const todayCount = this.approvalQueue.filter(tx => 
            this.isToday(tx.created_at)
        ).length;

        document.getElementById('pendingCount').textContent = pendingCount;
        document.getElementById('highPriorityCount').textContent = highPriorityCount;
        document.getElementById('todayCount').textContent = todayCount;
    }

    renderApprovalQueue() {
        // Only render if we're initialized
        if (!this.initialized) return;
        
        const container = document.getElementById('approvalsQueue');
        if (!container) return;

        const filteredQueue = this.filterQueue();
        
        if (filteredQueue.length === 0) {
            // Check if there are any transactions at all vs. if filters are hiding them
            const hasActiveFilters = this.hasActiveFilters();
            const hasAnyTransactions = this.approvalQueue.length > 0;
            
            let emptyMessage = '';
            let emptyTitle = '';
            
            if (!hasAnyTransactions) {
                // No transactions exist at all
                emptyTitle = 'No Clerk Submissions';
                emptyMessage = 'There are currently no pending submissions from finance clerks.';
            } else if (hasActiveFilters) {
                // Transactions exist but are filtered out
                emptyTitle = 'No Matching Submissions';
                emptyMessage = 'No pending submissions match your current filters.';
            } else {
                // This shouldn't happen, but fallback
                emptyTitle = 'No Clerk Submissions';
                emptyMessage = 'There are currently no pending submissions.';
            }
            
            container.innerHTML = `
                <div class="queue-empty">
                    <div class="empty-icon">📋</div>
                    <h3>${emptyTitle}</h3>
                    <p>${emptyMessage}</p>
                </div>
            `;
            return;
        }

        const queueHTML = filteredQueue.map(transaction => `
            <div class="queue-item queue-item--${this.getPriorityLevel(transaction)}" data-transaction-id="${transaction.transaction_id}">
                <div class="queue-item-header">
                    <div class="queue-item-info">
                        <div class="queue-item-title">
                            <span class="transaction-type">${this.getTransactionTypeLabel(transaction.transaction_type)}</span>
                            <span class="transaction-id">${transaction.transaction_id}</span>
                        </div>
                        <div class="queue-item-meta">
                            <span class="creator">Created by ${transaction.creator_name}</span>
                            <span class="created-time">${this.formatRelativeTime(transaction.created_at)}</span>
                        </div>
                    </div>
                    <div class="queue-item-priority">
                        <span class="priority-badge priority-${this.getPriorityLevel(transaction)}">
                            ${this.getPriorityLabel(this.getPriorityLevel(transaction))}
                        </span>
                    </div>
                </div>

                <div class="queue-item-content">
                    <div class="transaction-details">
                        ${transaction.reason ? `
                            <div class="transaction-reason">
                                <strong>Reason:</strong> ${transaction.reason}
                            </div>
                        ` : ''}
                        
                        ${transaction.transaction_data ? `
                            <div class="transaction-data">
                                ${this.formatTransactionData(transaction.transaction_data)}
                            </div>
                        ` : ''}
                    </div>

                    <div class="approval-progress">
                        <div class="approval-chain">
                            ${transaction.required_approvals.map(role => `
                                <div class="approval-step ${this.isApprovedByRole(transaction, role) ? 'approved' : 'pending'}">
                                    <div class="step-icon">${this.isApprovedByRole(transaction, role) ? '✓' : '⏳'}</div>
                                    <div class="step-label">${this.getRoleLabel(role)}</div>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                </div>

                <div class="queue-item-actions">
                    ${this.renderQueueActions(transaction)}
                </div>
            </div>
        `).join('');

        container.innerHTML = queueHTML;
        this.attachQueueItemListeners();
    }

    hasActiveFilters() {
        // Check if any filters are active (search, submission type, priority, date range)
        return this.searchQuery !== '' || 
               this.filters.submissionType !== 'all' || 
               this.filters.priority !== 'all' || 
               this.filters.dateRange !== 'all';
    }

    filterQueue() {
        return this.approvalQueue.filter(transaction => {
            // Apply search filter first
            if (this.searchQuery) {
                const searchableText = [
                    transaction.transaction_id || '',
                    transaction.creator_name || '',
                    transaction.reason || '',
                    transaction.transaction_type || '',
                    transaction.transaction_data?.account_code || '',
                    transaction.transaction_data?.account_description || '',
                    transaction.transaction_data?.amount || '',
                    transaction.required_approvals?.join(' ') || ''
                ].join(' ').toLowerCase();
                
                if (!searchableText.includes(this.searchQuery)) {
                    return false;
                }
            }

            // Filter by submission type
            if (this.filters.submissionType !== 'all') {
                const typeMap = {
                    'financial_statements': ['financial_statement'],
                    'journal_entries': ['journal_entry'],
                    'asset_impairment': ['asset_impairment'],
                    'budget_adjustment': ['budget_adjustment']
                };
                if (!typeMap[this.filters.submissionType]?.includes(transaction.transaction_type)) {
                    return false;
                }
            }

            // Filter by priority
            if (this.filters.priority !== 'all') {
                if (this.getPriorityLevel(transaction) !== this.filters.priority) {
                    return false;
                }
            }

            // Filter by date range
            if (this.filters.dateRange !== 'all') {
                const createdDate = new Date(transaction.created_at);
                const now = new Date();
                
                switch (this.filters.dateRange) {
                    case 'today':
                        if (!this.isToday(transaction.created_at)) return false;
                        break;
                    case 'week':
                        const weekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
                        if (createdDate < weekAgo) return false;
                        break;
                    case 'month':
                        const monthAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
                        if (createdDate < monthAgo) return false;
                        break;
                }
            }

            return true;
        });
    }

    renderQueueActions(transaction) {
        const actions = [];
        
        // Review action for financial statements
        if (transaction.transaction_type === 'financial_statement') {
            actions.push(`
                <button class="btn btn-primary btn-sm" data-action="review-statement" data-transaction-id="${transaction.transaction_id}">
                    🔍 Review Statement
                </button>
            `);
        }

        // Quick approve/reject for simple transactions
        if (['journal_entry', 'budget_adjustment'].includes(transaction.transaction_type)) {
            actions.push(`
                <button class="btn btn-success btn-sm" data-action="quick-approve" data-transaction-id="${transaction.transaction_id}">
                    ✓ Quick Approve
                </button>
            `);
            
            actions.push(`
                <button class="btn btn-danger btn-sm" data-action="quick-reject" data-transaction-id="${transaction.transaction_id}">
                    ✗ Quick Reject
                </button>
            `);
        }

        // Detailed review action
        actions.push(`
            <button class="btn btn-secondary btn-sm" data-action="detailed-review" data-transaction-id="${transaction.transaction_id}">
                📋 Detailed Review
            </button>
        `);

        return actions.join('');
    }

    attachQueueItemListeners() {
        document.querySelectorAll('[data-action]').forEach(button => {
            button.addEventListener('click', (e) => {
                const action = e.target.dataset.action;
                const transactionId = e.target.dataset.transactionId;
                
                switch (action) {
                    case 'review-statement':
                        this.reviewFinancialStatement(transactionId);
                        break;
                    case 'quick-approve':
                        this.quickApprove(transactionId);
                        break;
                    case 'quick-reject':
                        this.quickReject(transactionId);
                        break;
                    case 'detailed-review':
                        this.openDetailedReview(transactionId);
                        break;
                }
            });
        });
    }

    async reviewFinancialStatement(transactionId) {
        // Navigate to enhanced review screen
        window.location.href = `/approvals?review=statement&transaction=${transactionId}`;
    }

    async quickApprove(transactionId) {
        const reason = prompt('Please provide approval reason (optional):') || 'Quick approved by Finance Manager';
        
        try {
            const response = await fetch(`/api/transaction/approve/${transactionId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ reason })
            });

            const result = await response.json();
            
            if (result.success) {
                this.showSuccess('Transaction approved successfully');
                this.loadApprovalQueue();
            } else {
                this.showError(result.error);
            }
        } catch (error) {
            this.showError('Failed to approve transaction');
        }
    }

    async quickReject(transactionId) {
        const reason = prompt('Please provide rejection reason:');
        if (!reason) return;
        
        try {
            const response = await fetch(`/api/transaction/reject/${transactionId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ reason })
            });

            const result = await response.json();
            
            if (result.success) {
                this.showSuccess('Transaction rejected');
                this.loadApprovalQueue();
            } else {
                this.showError(result.error);
            }
        } catch (error) {
            this.showError('Failed to reject transaction');
        }
    }

    openDetailedReview(transactionId) {
        window.location.href = `/approvals?transaction=${transactionId}`;
    }

    // Helper methods
    getPriorityLevel(transaction) {
        // Determine priority based on transaction type and age
        const age = Date.now() - new Date(transaction.created_at).getTime();
        const hoursOld = age / (1000 * 60 * 60);
        
        if (transaction.transaction_type === 'financial_statement' || hoursOld > 48) {
            return 'high';
        } else if (hoursOld > 24) {
            return 'normal';
        } else {
            return 'low';
        }
    }

    getPriorityLabel(priority) {
        const labels = {
            'high': 'High Priority',
            'normal': 'Normal',
            'low': 'Low Priority'
        };
        return labels[priority] || priority;
    }

    getTransactionTypeLabel(type) {
        const labels = {
            'financial_statement': 'Financial Statement',
            'journal_entry': 'Journal Entry',
            'asset_impairment': 'Asset Impairment',
            'budget_adjustment': 'Budget Adjustment',
            'asset_disposal': 'Asset Disposal'
        };
        return labels[type] || type.replace('_', ' ').toUpperCase();
    }

    getRoleLabel(role) {
        const labels = {
            'FINANCE_MANAGER': 'Finance Manager',
            'CFO': 'CFO',
            'ASSET_MANAGER': 'Asset Manager',
            'FINANCE_CLERK': 'Finance Clerk'
        };
        return labels[role] || role;
    }

    isApprovedByRole(transaction, role) {
        return transaction.current_approvals.some(approval => approval.approver_role === role);
    }

    formatTransactionData(data) {
        if (!data) return '';
        
        const items = [];
        if (data.account_code) items.push(`Account: ${data.account_code}`);
        if (data.account_description) items.push(`Description: ${data.account_description}`);
        if (data.amount) items.push(`Amount: R${parseFloat(data.amount).toLocaleString()}`);
        if (data.debit_credit) items.push(`Type: ${data.debit_credit}`);
        
        return items.join(' | ');
    }

    formatRelativeTime(dateString) {
        const date = new Date(dateString);
        const now = new Date();
        const diffMs = now - date;
        const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
        const diffDays = Math.floor(diffHours / 24);

        if (diffHours < 1) return 'Just now';
        if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
        if (diffDays < 7) return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
        return date.toLocaleDateString();
    }

    isToday(dateString) {
        const date = new Date(dateString);
        const today = new Date();
        return date.toDateString() === today.toDateString();
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

// Initialize Finance Manager Dashboard
document.addEventListener('DOMContentLoaded', () => {
    // Only initialize for Finance Manager role and only on dashboard page
    if (window.currentUserRole === 'FINANCE_MANAGER') {
        const currentPath = window.location.pathname;
        const isDashboardPage = currentPath === '/' || currentPath === '/dashboard' || 
                               currentPath.endsWith('/dashboard');
        
        if (isDashboardPage) {
            window.financeManagerDashboard = new FinanceManagerDashboard();
        }
    }
});

// Export for use in other scripts
window.FinanceManagerDashboard = FinanceManagerDashboard;

} // End of duplicate class declaration guard
