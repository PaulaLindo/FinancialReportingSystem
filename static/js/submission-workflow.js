// Submission Workflow Interface
class SubmissionWorkflow {
    constructor(sessionId, submission = {}) {
        this.state = {
            sessionId: sessionId,
            submission: submission,
            isSubmitting: false
        };
        
        this.elements = {};
        this.init();
    }

    init() {
        this.cacheElements();
        this.setupEventListeners();
        this.startStatusPolling();
    }

    cacheElements() {
        this.elements = {
            submitBtn: document.getElementById('submitBtn'),
            editBtn: document.getElementById('editBtn'),
            deleteBtn: document.getElementById('deleteBtn'),
            withdrawBtn: document.getElementById('withdrawBtn'),
            generateBtn: document.getElementById('generateBtn'),
            resubmitBtn: document.getElementById('resubmitBtn'),
            viewFeedbackBtn: document.getElementById('viewFeedbackBtn')
        };
    }

    setupEventListeners() {
        // Submit button
        if (this.elements.submitBtn) {
            this.elements.submitBtn.addEventListener('click', this.submitForReview.bind(this));
        }
        
        // Edit button
        if (this.elements.editBtn) {
            this.elements.editBtn.addEventListener('click', this.editMapping.bind(this));
        }
        
        // Delete button
        if (this.elements.deleteBtn) {
            this.elements.deleteBtn.addEventListener('click', this.deleteSubmission.bind(this));
        }
        
        // Withdraw button
        if (this.elements.withdrawBtn) {
            this.elements.withdrawBtn.addEventListener('click', this.withdrawSubmission.bind(this));
        }
        
        // Generate button
        if (this.elements.generateBtn) {
            this.elements.generateBtn.addEventListener('click', this.generateStatements.bind(this));
        }
        
        // Resubmit button
        if (this.elements.resubmitBtn) {
            this.elements.resubmitBtn.addEventListener('click', this.resubmitForReview.bind(this));
        }
        
        // View feedback button
        if (this.elements.viewFeedbackBtn) {
            this.elements.viewFeedbackBtn.addEventListener('click', this.viewFeedback.bind(this));
        }
    }

    async submitForReview() {
        if (this.state.isSubmitting) return;
        
        try {
            this.state.isSubmitting = true;
            this.elements.submitBtn.disabled = true;
            this.elements.submitBtn.textContent = 'Submitting...';
            
            const response = await fetch(`/api/submission/${this.state.sessionId}/submit`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showSuccess('Submission submitted for review successfully');
                this.updateUIState('submitted');
            } else {
                this.showError(result.error || 'Submission failed');
            }
        } catch (error) {
            this.showError('Submission failed. Please try again.');
        } finally {
            this.state.isSubmitting = false;
            this.elements.submitBtn.disabled = false;
            this.elements.submitBtn.textContent = 'Submit for Review';
        }
    }

    async editMapping() {
        try {
            const response = await fetch(`/api/submission/${this.state.sessionId}/edit`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            const result = await response.json();
            
            if (result.success) {
                window.location.href = `/mapping/${this.state.sessionId}`;
            } else {
                this.showError(result.error || 'Failed to open mapping interface');
            }
        } catch (error) {
            this.showError('Failed to open mapping interface. Please try again.');
        }
    }

    async deleteSubmission() {
        if (!confirm('Are you sure you want to delete this submission? This action cannot be undone.')) {
            return;
        }
        
        try {
            const response = await fetch(`/api/submission/${this.state.sessionId}/delete`, {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showSuccess('Submission deleted successfully');
                setTimeout(() => {
                    window.location.href = '/dashboard';
                }, 1500);
            } else {
                this.showError(result.error || 'Failed to delete submission');
            }
        } catch (error) {
            this.showError('Failed to delete submission. Please try again.');
        }
    }

    async withdrawSubmission() {
        if (!confirm('Are you sure you want to withdraw this submission?')) {
            return;
        }
        
        try {
            const response = await fetch(`/api/submission/${this.state.sessionId}/withdraw`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showSuccess('Submission withdrawn successfully');
                this.updateUIState('draft');
            } else {
                this.showError(result.error || 'Failed to withdraw submission');
            }
        } catch (error) {
            this.showError('Failed to withdraw submission. Please try again.');
        }
    }

    async generateStatements() {
        try {
            this.elements.generateBtn.disabled = true;
            this.elements.generateBtn.textContent = 'Generating...';
            
            const response = await fetch(`/api/submission/${this.state.sessionId}/generate`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showSuccess('Financial statements generated successfully');
                setTimeout(() => {
                    window.location.href = `/reports/${this.state.sessionId}`;
                }, 1500);
            } else {
                this.showError(result.error || 'Failed to generate statements');
            }
        } catch (error) {
            this.showError('Failed to generate statements. Please try again.');
        } finally {
            this.elements.generateBtn.disabled = false;
            this.elements.generateBtn.textContent = 'Generate Statements';
        }
    }

    async resubmitForReview() {
        if (this.state.isSubmitting) return;
        
        try {
            this.state.isSubmitting = true;
            this.elements.resubmitBtn.disabled = true;
            this.elements.resubmitBtn.textContent = 'Resubmitting...';
            
            const response = await fetch(`/api/submission/${this.state.sessionId}/resubmit`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showSuccess('Submission resubmitted for review successfully');
                this.updateUIState('submitted');
            } else {
                this.showError(result.error || 'Resubmission failed');
            }
        } catch (error) {
            this.showError('Resubmission failed. Please try again.');
        } finally {
            this.state.isSubmitting = false;
            this.elements.resubmitBtn.disabled = false;
            this.elements.resubmitBtn.textContent = 'Resubmit for Review';
        }
    }

    async viewFeedback() {
        try {
            const response = await fetch(`/api/submission/${this.state.sessionId}/feedback`);
            const result = await response.json();
            
            if (result.success) {
                this.showFeedbackModal(result.feedback);
            } else {
                this.showError(result.error || 'Failed to load feedback');
            }
        } catch (error) {
            this.showError('Failed to load feedback. Please try again.');
        }
    }

    showFeedbackModal(feedback) {
        // Create modal if it doesn't exist
        let modal = document.getElementById('feedbackModal');
        if (!modal) {
            modal = document.createElement('div');
            modal.id = 'feedbackModal';
            modal.className = 'modal';
            modal.innerHTML = `
                <div class="modal-content">
                    <div class="modal-header">
                        <h3>Review Feedback</h3>
                        <button class="modal-close" onclick="this.closest('.modal').remove()">&times;</button>
                    </div>
                    <div class="modal-body">
                        <div id="feedbackContent"></div>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
        }
        
        // Populate feedback content
        const feedbackContent = modal.querySelector('#feedbackContent');
        feedbackContent.innerHTML = `
            <div class="feedback-section">
                <h4>Overall Status</h4>
                <p class="status-${feedback.status}">${feedback.status}</p>
            </div>
            ${feedback.comments ? `
                <div class="feedback-section">
                    <h4>Comments</h4>
                    <p>${feedback.comments}</p>
                </div>
            ` : ''}
            ${feedback.suggestions ? `
                <div class="feedback-section">
                    <h4>Suggestions</h4>
                    <ul>
                        ${feedback.suggestions.map(suggestion => `<li>${suggestion}</li>`).join('')}
                    </ul>
                </div>
            ` : ''}
        `;
        
        // Show modal
        modal.classList.add('modal-visible');
    }

    updateUIState(newState) {
        // Update button visibility based on state
        const buttonStates = {
            draft: {
                submitBtn: true,
                editBtn: true,
                deleteBtn: true,
                withdrawBtn: false,
                generateBtn: false,
                resubmitBtn: false,
                viewFeedbackBtn: false
            },
            submitted: {
                submitBtn: false,
                editBtn: false,
                deleteBtn: false,
                withdrawBtn: true,
                generateBtn: false,
                resubmitBtn: false,
                viewFeedbackBtn: false
            },
            approved: {
                submitBtn: false,
                editBtn: false,
                deleteBtn: false,
                withdrawBtn: false,
                generateBtn: true,
                resubmitBtn: false,
                viewFeedbackBtn: true
            },
            rejected: {
                submitBtn: false,
                editBtn: true,
                deleteBtn: true,
                withdrawBtn: false,
                generateBtn: false,
                resubmitBtn: true,
                viewFeedbackBtn: true
            }
        };
        
        const stateConfig = buttonStates[newState] || buttonStates.draft;
        
        Object.keys(stateConfig).forEach(buttonId => {
            const button = this.elements[buttonId];
            if (button) {
                if (stateConfig[buttonId]) {
                    button.classList.remove('button-hidden');
                    button.classList.add('button-visible');
                } else {
                    button.classList.add('button-hidden');
                    button.classList.remove('button-visible');
                }
            }
        });
    }

    startStatusPolling() {
        // Poll for status updates every 30 seconds
        setInterval(async () => {
            try {
                const response = await fetch(`/api/submission/${this.state.sessionId}/status`);
                const result = await response.json();
                
                if (result.success && result.status !== this.state.submission.status) {
                    this.state.submission.status = result.status;
                    this.updateUIState(result.status);
                    this.showStatusUpdate(result.status);
                }
            } catch (error) {
            } 
        }, 30000);
    }

    showStatusUpdate(status) {
        const message = `Submission status updated to: ${status}`;
        this.showInfo(message);
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
        notification.className = `notification notification-${type}`;
        notification.textContent = message;
        
        // Add to page
        document.body.appendChild(notification);
        
        // Remove after 3 seconds
        setTimeout(() => {
            notification.remove();
        }, 3000);
    }
}

// Initialize submission workflow
document.addEventListener('DOMContentLoaded', function() {
    // Get data from global variables set by template
    const sessionId = window.sessionId || '';
    const submission = window.submissionData || {};
    new SubmissionWorkflow(sessionId, submission);
});
