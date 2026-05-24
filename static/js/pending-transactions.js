/**
 * Pending Transactions and History Loader
 * Handles loading and display of pending transactions and transaction history
 */

class PendingTransactionsManager {
    constructor() {
        this.hasPendingContainer = !!document.getElementById('workflowContainer');
        this.hasHistoryContainer = !!document.getElementById('transactionHistoryContainer');
        if (!this.hasPendingContainer && !this.hasHistoryContainer) {
            return;
        }
        this.currentUser = null;
        this.pendingTransactions = [];
        this.transactionHistory = [];
        this.initializeEventListeners();
        this.loadCurrentUser();
    }

    async loadCurrentUser() {
        try {
            const response = await fetch('/api/current-user', {
                credentials: 'same-origin'
            });
            if (response.ok) {
                const data = await response.json();
                this.currentUser = data.data;
                if (this.hasPendingContainer) await this.loadPendingTransactions();
                if (this.hasHistoryContainer) await this.loadTransactionHistory();
            } else {
                console.error('Failed to load current user');
                // Fallback to global context
                if (window.currentUserId) {
                    this.currentUser = {
                        id: window.currentUserId,
                        role: window.currentUserRole,
                        full_name: window.currentUserFullName
                    };
                    await this.loadPendingTransactions();
                    await this.loadTransactionHistory();
                }
            }
        } catch (error) {
            console.error('Error loading current user:', error);
        }
    }

    initializeEventListeners() {
        // Filter change listeners for transaction history
        document.addEventListener('change', (e) => {
            if (e.target.matches('[data-action="load-transaction-history"]')) {
                this.loadTransactionHistory();
            }
        });
    }

    async loadPendingTransactions() {
        try {
            console.log('🔄 Loading pending transactions...');
            
            const response = await fetch('/api/transactions/pending', {
                credentials: 'same-origin'
            });

            if (response.ok) {
                const data = await response.json();
                console.log('✅ Pending transactions loaded:', data);
                
                this.pendingTransactions = (data.pending_transactions || []).filter(
                    (tx) => (tx.status || '').toLowerCase() === 'pending_review'
                );
                this.renderPendingTransactions();
                
                const n = data.count ?? this.pendingTransactions.length;
                this.updatePendingCount(n);
            } else {
                console.error('Failed to load pending transactions:', response.status);
                this.showError('workflowContainer', 'Failed to load pending transactions');
            }
        } catch (error) {
            console.error('Error loading pending transactions:', error);
            this.showError('workflowContainer', 'Error loading pending transactions');
        }
    }

    async loadTransactionHistory() {
        try {
            console.log('🔄 Loading transaction history...');
            
            const statusEl = document.getElementById('transactionHistoryStatusFilter');
            const statusFilter = (statusEl?.value ?? '').trim();
            const userEl = document.getElementById('transactionHistoryUserFilter');
            const userFilter = (userEl?.value ?? '').trim();
            
            // Build query parameters (omit status for API default: approved + rejected)
            const params = new URLSearchParams();
            if (statusFilter) params.append('status', statusFilter);
            if (userFilter) params.append('user_id', userFilter);
            
            const response = await fetch(`/api/transactions/history?${params}`, {
                credentials: 'same-origin'
            });

            if (response.ok) {
                const data = await response.json();
                console.log('✅ Transaction history loaded:', data);
                
                this.transactionHistory = data.transactions || [];
                this.renderTransactionHistory();
            } else {
                console.error('Failed to load transaction history:', response.status);
                this.showError('transactionHistoryContainer', 'Failed to load transaction history');
            }
        } catch (error) {
            console.error('Error loading transaction history:', error);
            this.showError('transactionHistoryContainer', 'Error loading transaction history');
        }
    }

    renderPendingTransactions() {
        const container = document.getElementById('workflowContainer');
        if (!container) return;

        if (this.pendingTransactions.length === 0) {
            container.innerHTML = `
                <div class="approval-empty-state">
                    <div class="approval-empty-icon">📋</div>
                    <h3>No Pending Transactions</h3>
                    <p>There are currently no transactions pending your approval.</p>
                </div>
            `;
            return;
        }

        const transactionsHtml = this.pendingTransactions.map(transaction => 
            this.renderPendingTransactionCard(transaction)
        ).join('');

        container.innerHTML = `
            <div class="transaction-list">
                ${transactionsHtml}
            </div>
        `;
    }

    canApproveTransactions() {
        const role = this.currentUser?.role || window.currentUserRole || '';
        return ['FINANCE_MANAGER', 'CFO', 'SYSTEM_ADMIN'].includes(role);
    }

    renderPendingTransactionCard(transaction) {
        const showApprovalActions = this.canApproveTransactions();
        const createdDate = VarydianUtils.formatDateTime(transaction.created_at) || '—';

        return `
            <div class="transaction-card pending" data-transaction-id="${transaction.transaction_id}">
                <div class="transaction-header">
                    <div class="transaction-info">
                        <h3 class="transaction-title">${transaction.transaction_type}</h3>
                        <p class="transaction-id">ID: ${transaction.transaction_id}</p>
                        <p class="transaction-creator">Submitted by: ${transaction.creator_name}</p>
                    </div>
                    <div class="transaction-status">
                        <span class="status-badge status-pending">PENDING</span>
                        <span class="priority-badge priority-medium">MEDIUM</span>
                    </div>
                </div>
                
                <div class="transaction-details">
                    <div class="transaction-meta">
                        <span class="transaction-date">${createdDate}</span>
                        <span class="transaction-type">${transaction.transaction_type}</span>
                    </div>
                    <div class="transaction-reason">
                        <strong>Reason:</strong> ${transaction.reason || 'No reason provided'}
                    </div>
                </div>
                
                <div class="transaction-actions">
                    <button class="btn btn-sm btn-primary view-transaction-btn" 
                            data-transaction-id="${transaction.transaction_id}"
                            data-session-id="${transaction.session_id}"
                            data-transaction-type="${transaction.transaction_type}">
                        Review
                    </button>
                    ${showApprovalActions ? `
                    <button class="btn btn-sm btn-success approve-transaction-btn" 
                            data-transaction-id="${transaction.transaction_id}"
                            data-session-id="${transaction.session_id}"
                            data-transaction-type="${transaction.transaction_type}">
                        Approve
                    </button>
                    <button class="btn btn-sm btn-danger reject-transaction-btn" 
                            data-transaction-id="${transaction.transaction_id}"
                            data-session-id="${transaction.session_id}"
                            data-transaction-type="${transaction.transaction_type}">
                        Reject
                    </button>
                    ` : ''}
                </div>
            </div>
        `;
    }

    renderTransactionHistory() {
        const container = document.getElementById('transactionHistoryContainer');
        if (!container) return;

        if (this.transactionHistory.length === 0) {
            container.innerHTML = `
                <div class="approval-empty-state">
                    <div class="approval-empty-icon">📚</div>
                    <h3>No Transaction History</h3>
                    <p>No transactions found matching the current filters.</p>
                </div>
            `;
            return;
        }

        const transactionsHtml = this.transactionHistory.map(transaction => 
            this.renderHistoryTransactionCard(transaction)
        ).join('');

        container.innerHTML = `
            <div class="transaction-list">
                ${transactionsHtml}
            </div>
        `;
    }

    renderHistoryTransactionCard(transaction) {
        const createdDate = VarydianUtils.formatDateTime(transaction.created_at) || '—';

        const statusClass = this.getStatusClass(transaction.status);
        const statusText = transaction.status?.toUpperCase() || 'UNKNOWN';

        return `
            <div class="transaction-card ${statusClass}" data-transaction-id="${transaction.transaction_id}">
                <div class="transaction-header">
                    <div class="transaction-info">
                        <h3 class="transaction-title">${transaction.transaction_type}</h3>
                        <p class="transaction-id">ID: ${transaction.transaction_id}</p>
                        <p class="transaction-creator">Submitted by: ${transaction.creator_name}</p>
                    </div>
                    <div class="transaction-status">
                        <span class="status-badge ${statusClass}">${statusText}</span>
                    </div>
                </div>
                
                <div class="transaction-details">
                    <div class="transaction-meta">
                        <span class="transaction-date">${createdDate}</span>
                        <span class="transaction-type">${transaction.transaction_type}</span>
                    </div>
                    ${transaction.reason ? `
                        <div class="transaction-reason">
                            <strong>Reason:</strong> ${transaction.reason}
                        </div>
                    ` : ''}
                </div>
                
                <div class="transaction-actions">
                    <button class="btn btn-sm btn-secondary view-transaction-btn" 
                            data-transaction-id="${transaction.transaction_id}"
                            data-session-id="${transaction.session_id}">
                        View Details
                    </button>
                </div>
            </div>
        `;
    }

    getStatusClass(status) {
        const statusClasses = {
            'pending_approval': 'status-pending',
            'approved': 'status-approved',
            'rejected': 'status-rejected',
            'finalized': 'status-completed'
        };
        return statusClasses[status] || 'status-unknown';
    }

    updatePendingCount(count) {
        const pendingCountElement = document.getElementById('pendingCount');
        if (pendingCountElement) {
            pendingCountElement.textContent = count;
        }
    }

    showError(containerId, message) {
        const container = document.getElementById(containerId);
        if (container) {
            container.innerHTML = `
                <div class="approval-error-state">
                    <div class="approval-error-icon">⚠️</div>
                    <h3>Error</h3>
                    <p>${message}</p>
                    <button class="btn btn-secondary" onclick="location.reload()">
                        🔄 Reload
                    </button>
                </div>
            `;
        }
    }

    // Handle transaction actions
    async handleTransactionAction(action, transactionId, sessionId, notes = '', transactionType = '') {
        try {
            let endpoint, method, payload;

            switch (action) {
                case 'approve':
                    endpoint = `/api/universal/approve`;
                    method = 'POST';
                    payload = {
                        document_type: transactionType || 'balance_sheet', // Use actual document type
                        session_id: sessionId,
                        notes: notes
                    };
                    break;
                case 'reject':
                    endpoint = `/api/universal/reject`;
                    method = 'POST';
                    payload = {
                        document_type: transactionType || 'balance_sheet', // Use actual document type
                        session_id: sessionId,
                        reason: notes
                    };
                    break;
                case 'view':
                    // Full statement review (SFP + SFPER) on approvals page; line items open calculation / formula modal
                    console.log('📋 [Pending] Opening statement review for session:', sessionId);
                    const typeParam = transactionType ? `&type=${encodeURIComponent(transactionType)}` : '';
                    window.location.href = `/approvals?review=statement&transaction=${encodeURIComponent(sessionId)}${typeParam}`;
                    return;
            }

            const response = await fetch(endpoint, {
                method: method,
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'same-origin',
                body: JSON.stringify(payload)
            });

            const data = await response.json();

            if (response.ok) {
                const msg = data.message || `Transaction ${action}d successfully`;
                this.showSuccess(msg);
                // Reload the data
                if (this.hasPendingContainer) await this.loadPendingTransactions();
                if (this.hasHistoryContainer) await this.loadTransactionHistory();
            } else {
                throw new Error(data.error || `Failed to ${action} transaction`);
            }
        } catch (error) {
            console.error(`Error ${action}ing transaction:`, error);
            this.showError('workflowContainer', `Failed to ${action} transaction: ${error.message}`);
        }
    }

    showSuccess(message) {
        // Create success notification
        const notification = document.createElement('div');
        notification.className = 'notification notification-success';
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        // Auto remove after 3 seconds
        setTimeout(() => {
            notification.remove();
        }, 3000);
    }
}

// Initialize transaction action handlers
document.addEventListener('click', (e) => {
    const approveBtn = e.target.closest('.approve-transaction-btn');
    const rejectBtn = e.target.closest('.reject-transaction-btn');
    const viewBtn = e.target.closest('.view-transaction-btn');

    if (approveBtn) {
        e.preventDefault();
        const sessionId = approveBtn.dataset.sessionId;
        const transactionType = approveBtn.dataset.transactionType;
        const reason = prompt('Add approval notes (optional):');
        if (reason !== null) {
            window.pendingTransactionsManager.handleTransactionAction('approve', approveBtn.dataset.transactionId, sessionId, reason, transactionType);
        }
    } else if (rejectBtn) {
        e.preventDefault();
        const sessionId = rejectBtn.dataset.sessionId;
        const transactionType = rejectBtn.dataset.transactionType;
        const reason = prompt('Please provide rejection reason:');
        if (reason) {
            window.pendingTransactionsManager.handleTransactionAction('reject', rejectBtn.dataset.transactionId, sessionId, reason, transactionType);
        }
    } else if (viewBtn) {
        e.preventDefault();
        const sessionId = viewBtn.dataset.sessionId;
        const transactionType = viewBtn.dataset.transactionType;
        window.pendingTransactionsManager.handleTransactionAction('view', viewBtn.dataset.transactionId, sessionId, '', transactionType);
    }
});

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    const mgr = new PendingTransactionsManager();
    if (mgr.hasPendingContainer || mgr.hasHistoryContainer) {
        window.pendingTransactionsManager = mgr;
    }
});
