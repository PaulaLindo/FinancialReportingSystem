/**
 * SADPMR Financial Reporting System - Line Item Comment System
 * Allows Finance Manager to add comments on specific financial statement line items
 */

class LineItemCommentSystem {
    constructor() {
        this.currentAccount = null;
        this.currentTransaction = null;
        this.comments = [];
        this.initializeEventListeners();
    }

    initializeEventListeners() {
        // Close modal events
        document.querySelectorAll('[data-action="close-comment-modal"]').forEach(element => {
            element.addEventListener('click', () => this.closeModal());
        });

        // Modal overlay click
        document.querySelector('#lineItemCommentModal .modal-overlay')?.addEventListener('click', () => this.closeModal());

        // Action buttons
        document.querySelector('[data-action="save-comment-only"]')?.addEventListener('click', () => this.saveCommentOnly());
        document.querySelector('[data-action="reject-with-comment"]')?.addEventListener('click', () => this.rejectWithComment());
        document.querySelector('[data-action="approve-with-comment"]')?.addEventListener('click', () => this.approveWithComment());

        // Form validation
        document.getElementById('commentText')?.addEventListener('input', () => this.validateForm());

        // ESC key to close
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.isModalOpen()) {
                this.closeModal();
            }
        });
    }

    openModal(accountCode, accountData, transactionId) {
        this.currentAccount = {
            code: accountCode,
            ...accountData
        };
        this.currentTransaction = transactionId;

        // Populate account information
        this.populateAccountInfo();
        
        // Load previous comments
        this.loadPreviousComments();
        
        // Reset form
        this.resetForm();
        
        // Show modal
        const modal = document.getElementById('lineItemCommentModal');
        modal.classList.remove('visibility--hidden');
        
        // Focus on subject field
        setTimeout(() => {
            document.getElementById('commentSubject')?.focus();
        }, 100);
    }

    closeModal() {
        const modal = document.getElementById('lineItemCommentModal');
        modal.classList.add('visibility--hidden');
        
        // Clear current data
        this.currentAccount = null;
        this.currentTransaction = null;
        this.comments = [];
    }

    isModalOpen() {
        const modal = document.getElementById('lineItemCommentModal');
        return !modal.classList.contains('visibility--hidden');
    }

    populateAccountInfo() {
        if (!this.currentAccount) return;

        document.getElementById('commentAccountInfo').textContent = `Account: ${this.currentAccount.code}`;
        document.getElementById('accountCode').textContent = this.currentAccount.code || '-';
        document.getElementById('accountDescription').textContent = this.currentAccount.description || '-';
        document.getElementById('grapCode').textContent = this.currentAccount.grap_code || '-';
        document.getElementById('accountAmount').textContent = this.currentAccount.amount ? 
            `R${this.formatNumber(this.currentAccount.amount)}` : '-';
    }

    async loadPreviousComments() {
        if (!this.currentAccount || !this.currentTransaction) return;

        try {
            const response = await fetch(`/api/comments/line-item/${this.currentTransaction}/${this.currentAccount.code}`);
            const result = await response.json();
            
            if (result.success) {
                this.comments = result.comments || [];
                this.renderPreviousComments();
            } else {
                this.comments = [];
                this.renderPreviousComments();
            }
        } catch (error) {
            this.comments = [];
            this.renderPreviousComments();
        }
    }

    renderPreviousComments() {
        const container = document.getElementById('previousCommentsList');
        if (!container) return;

        if (this.comments.length === 0) {
            container.innerHTML = `
                <div class="no-comments">
                    <p>No previous comments for this line item.</p>
                </div>
            `;
            return;
        }

        const commentsHTML = this.comments.map(comment => `
            <div class="comment-item comment-item--${comment.urgency_level}">
                <div class="comment-header">
                    <div class="comment-meta">
                        <span class="comment-author">${comment.author_name}</span>
                        <span class="comment-date">${this.formatDate(comment.created_at)}</span>
                        <span class="comment-type">${this.getCommentTypeLabel(comment.comment_type)}</span>
                    </div>
                    <div class="comment-urgency urgency-${comment.urgency_level}">
                        ${this.getUrgencyLabel(comment.urgency_level)}
                    </div>
                </div>
                
                ${comment.subject ? `
                    <div class="comment-subject">
                        <strong>Subject:</strong> ${comment.subject}
                    </div>
                ` : ''}
                
                <div class="comment-text">
                    ${comment.comment_text}
                </div>
                
                ${comment.correction_suggestion ? `
                    <div class="correction-suggestion">
                        <strong>Suggested Correction:</strong> ${comment.correction_suggestion}
                    </div>
                ` : ''}
                
                <div class="comment-actions">
                    <button class="btn btn-xs btn-secondary" data-action="edit-comment" data-comment-id="${comment.id}">
                        ✏️ Edit
                    </button>
                    <button class="btn btn-xs btn-danger" data-action="delete-comment" data-comment-id="${comment.id}">
                        🗑️ Delete
                    </button>
                </div>
            </div>
        `).join('');

        container.innerHTML = commentsHTML;
        this.attachCommentActionListeners();
    }

    attachCommentActionListeners() {
        container.querySelectorAll('[data-action]').forEach(button => {
            button.addEventListener('click', (e) => {
                const action = e.target.dataset.action;
                const commentId = e.target.dataset.commentId;
                
                switch (action) {
                    case 'edit-comment':
                        this.editComment(commentId);
                        break;
                    case 'delete-comment':
                        this.deleteComment(commentId);
                        break;
                }
            });
        });
    }

    resetForm() {
        document.getElementById('commentSubject').value = '';
        document.getElementById('commentText').value = '';
        document.getElementById('correctionSuggestion').value = '';
        document.getElementById('urgencyLevel').value = 'medium';
        document.querySelector('input[name="commentType"][value="calculation"]').checked = true;
        this.validateForm();
    }

    validateForm() {
        const commentText = document.getElementById('commentText').value.trim();
        const hasContent = commentText.length > 0;
        
        // Enable/disable action buttons based on validation
        const actionButtons = document.querySelectorAll('[data-action="save-comment-only"], [data-action="reject-with-comment"], [data-action="approve-with-comment"]');
        actionButtons.forEach(button => {
            button.disabled = !hasContent;
        });
        
        return hasContent;
    }

    async saveCommentOnly() {
        if (!this.validateForm()) return;

        const commentData = this.getCommentData();
        
        try {
            const response = await fetch('/api/comments/line-item', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(commentData)
            });

            const result = await response.json();
            
            if (result.success) {
                this.showSuccess('Comment saved successfully');
                this.loadPreviousComments();
                this.resetForm();
            } else {
                this.showError(result.error || 'Failed to save comment');
            }
        } catch (error) {
            this.showError('Network error saving comment');
        }
    }

    async rejectWithComment() {
        if (!this.validateForm()) return;

        const commentData = this.getCommentData();
        
        try {
            // First save the comment
            const commentResponse = await fetch('/api/comments/line-item', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(commentData)
            });

            const commentResult = await commentResponse.json();
            
            if (!commentResult.success) {
                this.showError('Failed to save comment before rejection');
                return;
            }

            // Then reject the transaction
            const rejectReason = this.buildRejectionReason();
            const rejectResponse = await fetch(`/api/transaction/reject/${this.currentTransaction}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ reason: rejectReason })
            });

            const rejectResult = await rejectResponse.json();
            
            if (rejectResult.success) {
                this.showSuccess('Transaction rejected with comment');
                setTimeout(() => {
                    this.closeModal();
                    window.location.href = '/approvals';
                }, 2000);
            } else {
                this.showError(rejectResult.error || 'Failed to reject transaction');
            }
        } catch (error) {
            this.showError('Network error during rejection process');
        }
    }

    async approveWithComment() {
        if (!this.validateForm()) return;

        const commentData = this.getCommentData();
        
        try {
            // First save the comment
            const commentResponse = await fetch('/api/comments/line-item', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(commentData)
            });

            const commentResult = await commentResponse.json();
            
            if (!commentResult.success) {
                this.showError('Failed to save comment before approval');
                return;
            }

            // Then approve the transaction
            const approvalReason = this.buildApprovalReason();
            const approveResponse = await fetch(`/api/transaction/approve/${this.currentTransaction}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ reason: approvalReason })
            });

            const approveResult = await approveResponse.json();
            
            if (approveResult.success) {
                this.showSuccess('Transaction approved with comment');
                setTimeout(() => {
                    this.closeModal();
                    window.location.href = '/approvals';
                }, 2000);
            } else {
                this.showError(approveResult.error || 'Failed to approve transaction');
            }
        } catch (error) {
            this.showError('Network error during approval process');
        }
    }

    getCommentData() {
        const commentType = document.querySelector('input[name="commentType"]:checked').value;
        const subject = document.getElementById('commentSubject').value.trim();
        const commentText = document.getElementById('commentText').value.trim();
        const correctionSuggestion = document.getElementById('correctionSuggestion').value.trim();
        const urgencyLevel = document.getElementById('urgencyLevel').value;

        return {
            transaction_id: this.currentTransaction,
            account_code: this.currentAccount.code,
            comment_type: commentType,
            subject: subject,
            comment_text: commentText,
            correction_suggestion: correctionSuggestion,
            urgency_level: urgencyLevel,
            author_id: window.currentUserId,
            author_name: window.currentUserFullName
        };
    }

    buildRejectionReason() {
        const commentType = document.querySelector('input[name="commentType"]:checked').value;
        const subject = document.getElementById('commentSubject').value.trim();
        const commentText = document.getElementById('commentText').value.trim();
        const correctionSuggestion = document.getElementById('correctionSuggestion').value.trim();

        let reason = `Rejected by Finance Manager - ${this.getCommentTypeLabel(commentType)}`;
        
        if (subject) {
            reason += `\nSubject: ${subject}`;
        }
        
        reason += `\nComment: ${commentText}`;
        
        if (correctionSuggestion) {
            reason += `\nSuggested Correction: ${correctionSuggestion}`;
        }
        
        reason += `\nAccount: ${this.currentAccount.code} - ${this.currentAccount.description || ''}`;

        return reason;
    }

    buildApprovalReason() {
        const commentType = document.querySelector('input[name="commentType"]:checked').value;
        const subject = document.getElementById('commentSubject').value.trim();
        const commentText = document.getElementById('commentText').value.trim();

        let reason = `Approved by Finance Manager with comment - ${this.getCommentTypeLabel(commentType)}`;
        
        if (subject) {
            reason += `\nSubject: ${subject}`;
        }
        
        reason += `\nComment: ${commentText}`;
        reason += `\nAccount: ${this.currentAccount.code} - ${this.currentAccount.description || ''}`;

        return reason;
    }

    async editComment(commentId) {
        const comment = this.comments.find(c => c.id === commentId);
        if (!comment) return;

        // Populate form with comment data
        document.getElementById('commentSubject').value = comment.subject || '';
        document.getElementById('commentText').value = comment.comment_text;
        document.getElementById('correctionSuggestion').value = comment.correction_suggestion || '';
        document.getElementById('urgencyLevel').value = comment.urgency_level;
        document.querySelector(`input[name="commentType"][value="${comment.comment_type}"]`)?.click();

        // Change save button to update
        const saveButton = document.querySelector('[data-action="save-comment-only"]');
        saveButton.textContent = '💾 Update Comment';
        saveButton.dataset.action = 'update-comment';
        saveButton.dataset.commentId = commentId;

        // Re-attach event listener
        saveButton.removeEventListener('click', this.saveCommentOnly);
        saveButton.addEventListener('click', () => this.updateComment(commentId));
    }

    async updateComment(commentId) {
        if (!this.validateForm()) return;

        const commentData = this.getCommentData();
        commentData.comment_id = commentId;

        try {
            const response = await fetch(`/api/comments/line-item/${commentId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(commentData)
            });

            const result = await response.json();
            
            if (result.success) {
                this.showSuccess('Comment updated successfully');
                this.loadPreviousComments();
                this.resetForm();
                
                // Reset save button
                const saveButton = document.querySelector('[data-action="update-comment"]');
                saveButton.textContent = '💾 Save Comment';
                saveButton.dataset.action = 'save-comment-only';
                delete saveButton.dataset.commentId;
            } else {
                this.showError(result.error || 'Failed to update comment');
            }
        } catch (error) {
            this.showError('Network error updating comment');
        }
    }

    async deleteComment(commentId) {
        if (!confirm('Are you sure you want to delete this comment?')) return;

        try {
            const response = await fetch(`/api/comments/line-item/${commentId}`, {
                method: 'DELETE'
            });

            const result = await response.json();
            
            if (result.success) {
                this.showSuccess('Comment deleted successfully');
                this.loadPreviousComments();
            } else {
                this.showError(result.error || 'Failed to delete comment');
            }
        } catch (error) {
            this.showError('Network error deleting comment');
        }
    }

    // Helper methods
    getCommentTypeLabel(type) {
        const labels = {
            'calculation': 'Calculation Issue',
            'mapping': 'Mapping Issue',
            'data': 'Data Issue',
            'general': 'General Comment'
        };
        return labels[type] || type;
    }

    getUrgencyLabel(urgency) {
        const labels = {
            'low': 'Low Priority',
            'medium': 'Medium Priority',
            'high': 'High Priority'
        };
        return labels[urgency] || urgency;
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

// Initialize the line item comment system
document.addEventListener('DOMContentLoaded', () => {
    window.lineItemCommentSystem = new LineItemCommentSystem();
});

// Export for use in other scripts
window.LineItemCommentSystem = LineItemCommentSystem;

// Global function for opening modal from other scripts
window.openLineItemComment = (accountCode, accountData, transactionId) => {
    window.lineItemCommentSystem.openModal(accountCode, accountData, transactionId);
};
