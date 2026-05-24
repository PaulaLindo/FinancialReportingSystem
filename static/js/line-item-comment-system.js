/**
 * Line item comments for Finance Manager (scoped to #lineItemCommentModal).
 * data-action values must not collide with statement review / main.js delegation.
 */

class LineItemCommentSystem {
    constructor() {
        this.currentAccount = null;
        this.currentTransaction = null;
        this.documentType = null;
        this.comments = [];
        /** Element that opened the modal (avoid aria-hidden on an ancestor while it still has focus) */
        this._priorFocusEl = null;
        this.initializeEventListeners();
    }

    modalRoot() {
        return document.getElementById('lineItemCommentModal');
    }

    qs(sel) {
        return this.modalRoot()?.querySelector(sel) ?? null;
    }

    qsa(sel) {
        const r = this.modalRoot();
        return r ? Array.from(r.querySelectorAll(sel)) : [];
    }

    initializeEventListeners() {
        const root = this.modalRoot();
        if (!root) return;

        root.addEventListener('click', (e) => {
            const overlay = root.querySelector('.line-item-comment-modal__overlay');
            if (e.target === overlay) {
                e.preventDefault();
                this.closeModal();
                return;
            }

            const el = e.target.closest('[data-action]');
            if (!el || !root.contains(el)) return;

            const action = el.getAttribute('data-action');
            switch (action) {
                case 'close-line-item-comment-modal':
                    e.preventDefault();
                    this.closeModal();
                    break;
                case 'save-line-item-comment':
                    e.preventDefault();
                    this.saveCommentOnly();
                    break;
                case 'update-line-item-comment': {
                    e.preventDefault();
                    const id = el.getAttribute('data-comment-id');
                    if (id) this.updateComment(id);
                    break;
                }
                case 'reject-with-line-item-comment':
                    e.preventDefault();
                    this.rejectWithComment();
                    break;
                case 'approve-with-line-item-comment':
                    e.preventDefault();
                    this.approveWithComment();
                    break;
                case 'edit-line-item-comment': {
                    e.preventDefault();
                    const id = el.getAttribute('data-comment-id');
                    if (id) this.editComment(id);
                    break;
                }
                case 'delete-line-item-comment': {
                    e.preventDefault();
                    const id = el.getAttribute('data-comment-id');
                    if (id) this.deleteComment(id);
                    break;
                }
                default:
                    break;
            }
        });

        this.qs('#commentText')?.addEventListener('input', () => this.validateForm());
        this.qs('#commentSubject')?.addEventListener('input', () => this.validateForm());

        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.isModalOpen()) {
                this.closeModal();
            }
        });
    }

    postActionRedirect() {
        const p = (window.location.pathname || '').toLowerCase();
        if (p.includes('finance-manager')) return '/finance-manager/review-queue';
        return '/approvals';
    }

    openModal(accountCode, accountData, transactionId, documentType) {
        if (window.formulaModalController && typeof window.formulaModalController.close === 'function') {
            try {
                window.formulaModalController.close();
            } catch (_) {
                /* ignore */
            }
        }

        this.currentAccount = {
            code: accountCode,
            ...accountData
        };
        this.currentTransaction = transactionId;
        this.documentType = documentType || 'balance_sheet';

        this.populateAccountInfo();
        this.loadPreviousComments();
        this.resetForm();

        const modal = this.modalRoot();
        if (!modal) return;

        const ae = document.activeElement;
        this._priorFocusEl =
            ae instanceof HTMLElement && !modal.contains(ae) ? ae : null;

        modal.classList.remove('visibility--hidden');
        modal.setAttribute('aria-hidden', 'false');

        setTimeout(() => {
            this.qs('#commentSubject')?.focus();
        }, 100);
    }

    /** Move focus out of the dialog before marking it aria-hidden */
    releaseFocus(modal) {
        const active = document.activeElement;
        if (!(active instanceof HTMLElement) || !modal.contains(active)) return;

        const back =
            this._priorFocusEl &&
            document.contains(this._priorFocusEl) &&
            !modal.contains(this._priorFocusEl)
                ? this._priorFocusEl
                : document.querySelector('main') || document.body;

        if (back instanceof HTMLElement) {
            if ((back.tagName === 'MAIN' || back.tagName === 'BODY') && !back.hasAttribute('tabindex')) {
                back.setAttribute('tabindex', '-1');
            }
            try {
                back.focus({ preventScroll: true });
            } catch (_) {
                try {
                    active.blur();
                } catch (_) {}
            }
        }
    }

    closeModal() {
        const modal = this.modalRoot();
        if (!modal) return;

        const clearState = () => {
            this.currentAccount = null;
            this.currentTransaction = null;
            this.documentType = null;
            this.comments = [];
        };

        const applyHidden = () => {
            modal.classList.add('visibility--hidden');
            modal.setAttribute('aria-hidden', 'true');
            clearState();
        };

        this.releaseFocus(modal);
        this._priorFocusEl = null;

        if (modal.contains(document.activeElement)) {
            requestAnimationFrame(() => {
                requestAnimationFrame(applyHidden);
            });
            return;
        }

        applyHidden();
    }

    isModalOpen() {
        const modal = this.modalRoot();
        return modal && !modal.classList.contains('visibility--hidden');
    }

    populateAccountInfo() {
        if (!this.currentAccount) return;

        const code = this.currentAccount.code;
        const desc = this.currentAccount.description || '-';
        const grap = this.currentAccount.grap_code || '-';
        const amount = this.currentAccount.amount;

        this.qs('#commentAccountInfo').textContent = `Account: ${code}`;
        this.qs('#accountCode').textContent = code || '-';
        this.qs('#accountDescription').textContent = desc;
        this.qs('#grapCode').textContent = grap;
        this.qs('#accountAmount').textContent =
            amount != null && amount !== '' ? `R${this.formatNumber(amount)}` : '-';
    }

    async loadPreviousComments() {
        if (!this.currentAccount || !this.currentTransaction) return;

        try {
            const params = new URLSearchParams({
                account_code: this.currentAccount.code,
                document_type: this.documentType || 'balance_sheet'
            });
            const response = await fetch(`/api/comments/line-item/${this.currentTransaction}?${params.toString()}`);
            const result = await response.json();

            if (result.success) {
                this.comments = result.comments || [];
            } else {
                this.comments = [];
            }
        } catch (error) {
            this.comments = [];
        }
        this.renderPreviousComments();
    }

    renderPreviousComments() {
        const container = this.qs('#previousCommentsList');
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
                    <button type="button" class="btn btn-xs btn-secondary" data-action="edit-line-item-comment" data-comment-id="${comment.id}">
                        ✏️ Edit
                    </button>
                    <button type="button" class="btn btn-xs btn-danger" data-action="delete-line-item-comment" data-comment-id="${comment.id}">
                        🗑️ Delete
                    </button>
                </div>
            </div>
        `).join('');

        container.innerHTML = commentsHTML;
    }

    resetSaveButtonState() {
        const saveButton = this.qs('[data-action="update-line-item-comment"], [data-action="save-line-item-comment"]');
        if (!saveButton) return;
        saveButton.textContent = '💾 Save Comment';
        saveButton.setAttribute('data-action', 'save-line-item-comment');
        saveButton.removeAttribute('data-comment-id');
    }

    resetForm() {
        const subj = this.qs('#commentSubject');
        const txt = this.qs('#commentText');
        const corr = this.qs('#correctionSuggestion');
        const urg = this.qs('#urgencyLevel');
        if (subj) subj.value = '';
        if (txt) txt.value = '';
        if (corr) corr.value = '';
        if (urg) urg.value = 'medium';

        const calc = this.qs('input[name="lineItemCommentType"][value="calculation"]');
        if (calc) calc.checked = true;

        this.resetSaveButtonState();
        this.validateForm();
    }

    validateForm() {
        const root = this.modalRoot();
        if (!root) return false;

        const commentText = (this.qs('#commentText')?.value || '').trim();
        const hasContent = commentText.length > 0;

        const selectors = [
            '[data-action="save-line-item-comment"]',
            '[data-action="update-line-item-comment"]',
            '[data-action="reject-with-line-item-comment"]',
            '[data-action="approve-with-line-item-comment"]'
        ].join(', ');

        root.querySelectorAll(selectors).forEach((button) => {
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

            const rejectReason = this.buildRejectionReason();
            const rejectResponse = await fetch('/api/universal/reject', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    document_type: this.documentType || 'balance_sheet',
                    session_id: this.currentTransaction,
                    reason: rejectReason
                })
            });

            const rejectResult = await rejectResponse.json();

            if (rejectResult.success) {
                this.showSuccess('Transaction rejected with comment');
                setTimeout(() => {
                    this.closeModal();
                    window.location.href = this.postActionRedirect();
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

            const approvalReason = this.buildApprovalReason();
            const approveResponse = await fetch('/api/universal/approve', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    document_type: this.documentType || 'balance_sheet',
                    session_id: this.currentTransaction,
                    notes: approvalReason
                })
            });

            const approveResult = await approveResponse.json();

            if (approveResult.success) {
                this.showSuccess('Transaction approved with comment');
                setTimeout(() => {
                    this.closeModal();
                    window.location.href = this.postActionRedirect();
                }, 2000);
            } else {
                this.showError(approveResult.error || 'Failed to approve transaction');
            }
        } catch (error) {
            this.showError('Network error during approval process');
        }
    }

    getCommentData() {
        const typeInput = this.qs('input[name="lineItemCommentType"]:checked');
        const commentType = typeInput ? typeInput.value : 'general';
        const subject = (this.qs('#commentSubject')?.value || '').trim();
        const commentText = (this.qs('#commentText')?.value || '').trim();
        const correctionSuggestion = (this.qs('#correctionSuggestion')?.value || '').trim();
        const urgencyLevel = this.qs('#urgencyLevel')?.value || 'medium';

        return {
            transaction_id: this.currentTransaction,
            document_type: this.documentType || 'balance_sheet',
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
        const typeInput = this.qs('input[name="lineItemCommentType"]:checked');
        const commentType = typeInput ? typeInput.value : 'general';
        const subject = (this.qs('#commentSubject')?.value || '').trim();
        const commentText = (this.qs('#commentText')?.value || '').trim();
        const correctionSuggestion = (this.qs('#correctionSuggestion')?.value || '').trim();

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
        const typeInput = this.qs('input[name="lineItemCommentType"]:checked');
        const commentType = typeInput ? typeInput.value : 'general';
        const subject = (this.qs('#commentSubject')?.value || '').trim();
        const commentText = (this.qs('#commentText')?.value || '').trim();

        let reason = `Approved by Finance Manager with comment - ${this.getCommentTypeLabel(commentType)}`;

        if (subject) {
            reason += `\nSubject: ${subject}`;
        }

        reason += `\nComment: ${commentText}`;
        reason += `\nAccount: ${this.currentAccount.code} - ${this.currentAccount.description || ''}`;

        return reason;
    }

    editComment(commentId) {
        const comment = this.comments.find(c => String(c.id) === String(commentId));
        if (!comment) return;

        const subj = this.qs('#commentSubject');
        const txt = this.qs('#commentText');
        const corr = this.qs('#correctionSuggestion');
        const urg = this.qs('#urgencyLevel');
        if (subj) subj.value = comment.subject || '';
        if (txt) txt.value = comment.comment_text || '';
        if (corr) corr.value = comment.correction_suggestion || '';
        if (urg) urg.value = comment.urgency_level || 'medium';

        const radio = this.qs(`input[name="lineItemCommentType"][value="${comment.comment_type}"]`);
        if (radio) radio.checked = true;

        const saveButton = this.qs('[data-action="save-line-item-comment"], [data-action="update-line-item-comment"]');
        if (saveButton) {
            saveButton.textContent = '💾 Update Comment';
            saveButton.setAttribute('data-action', 'update-line-item-comment');
            saveButton.setAttribute('data-comment-id', commentId);
        }

        this.validateForm();
    }

    async updateComment(commentId) {
        if (!this.validateForm()) return;

        const commentData = this.getCommentData();
        commentData.comment_id = commentId;

        try {
            const response = await fetch(`/api/comments/line-item/${this.currentTransaction}/${commentId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ...commentData, document_type: this.documentType })
            });

            const result = await response.json();

            if (result.success) {
                this.showSuccess('Comment updated successfully');
                await this.loadPreviousComments();
                this.resetForm();
            } else {
                this.showError(result.error || 'Failed to update comment');
            }
        } catch (error) {
            this.showError('Network error updating comment');
        }
    }

    async deleteComment(commentId) {
        const confirmed = await showConfirm('Delete Comment', 'Are you sure you want to delete this comment?');
        if (!confirmed) return;

        try {
            const params = new URLSearchParams({ document_type: this.documentType || 'balance_sheet' });
            const response = await fetch(`/api/comments/line-item/${this.currentTransaction}/${commentId}?${params.toString()}`, {
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

    getCommentTypeLabel(type) {
        const labels = {
            calculation: 'Calculation Issue',
            mapping: 'Mapping Issue',
            data: 'Data Issue',
            general: 'General Comment'
        };
        return labels[type] || type;
    }

    getUrgencyLabel(urgency) {
        const labels = {
            low: 'Low Priority',
            medium: 'Medium Priority',
            high: 'High Priority'
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
        return VarydianUtils.formatDate(dateString);
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
                <button type="button" class="notification-close" onclick="this.parentElement.parentElement.remove()">✕</button>
            </div>
        `;

        document.body.appendChild(notification);
        setTimeout(() => {
            notification.remove();
        }, 5000);
    }
}

function initializeLineItemCommentSystem() {
    if (window.lineItemCommentSystem) {
        return;
    }
    window.lineItemCommentSystem = new LineItemCommentSystem();
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeLineItemCommentSystem);
} else {
    initializeLineItemCommentSystem();
}

window.LineItemCommentSystem = LineItemCommentSystem;

window.openLineItemComment = (accountCode, accountData, transactionId, documentType) => {
    window.lineItemCommentSystem?.openModal(accountCode, accountData, transactionId, documentType);
};
