/**
 * Processing State Management JavaScript
 * Handles processing state indicators and draft statement viewer integration
 */

class ProcessingStateManager {
    constructor() {
        this.currentTrialBalance = null;
        this.currentPeriod = null;
        this.processingState = null;
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

    async initialize() {
        // Get current trial balance and period from page context
        this.currentTrialBalance = this.getTrialBalanceFromPage();
        this.currentPeriod = this.getPeriodFromPage();
        
        if (this.currentTrialBalance) {
            await this.loadProcessingState();
            this.updateProcessingStateIndicator();
        }
    }

    getTrialBalanceFromPage() {
        // Try to get trial balance ID from page context
        const tbElement = document.querySelector('[data-trial-balance-id]');
        if (tbElement) {
            return tbElement.dataset.trialBalanceId;
        }
        
        // Try to get from URL or global variable
        if (window.currentTrialBalanceId) {
            return window.currentTrialBalanceId;
        }
        
        return null;
    }

    getPeriodFromPage() {
        // Try to get period from page context
        const periodElement = document.querySelector('[data-period]');
        if (periodElement) {
            return periodElement.dataset.period;
        }
        
        // Try to get from URL or global variable
        if (window.currentPeriod) {
            return window.currentPeriod;
        }
        
        // Default to current fiscal year
        return 'FY 2025-2026';
    }

    async loadProcessingState() {
        if (!this.currentTrialBalance) return;

        try {
            const response = await fetch(`/api/processing/state/${this.currentTrialBalance}`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });

            if (response.ok) {
                const result = await response.json();
                this.processingState = result.data;
                return this.processingState;
            } else {
                return null;
            }
        } catch (error) {
            return null;
        }
    }

    updateProcessingStateIndicator() {
        const indicator = document.getElementById('processingStateIndicator');
        const valueElement = document.getElementById('processingStateValue');
        
        if (!indicator || !valueElement) return;

        if (!this.processingState) {
            valueElement.textContent = 'Unknown';
            valueElement.className = 'state-value state-unknown';
            return;
        }

        const status = this.processingState.status || 'unknown';
        const visibility = this.processingState.formula_visibility || 'unknown';

        // Update status display
        valueElement.textContent = this.formatProcessingStatus(status);
        valueElement.className = `state-value state-${status}`;

        // Add access mode indicator
        const accessMode = this.determineAccessMode();
        if (accessMode) {
            this.addAccessModeIndicator(accessMode, status);
        }

        // Update draft statement button visibility
        this.updateDraftStatementButton(status);
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

    determineAccessMode() {
        if (!this.processingState) return null;

        // This would normally come from the API response
        // For now, determine based on processing status
        const status = this.processingState.status;
        
        if (status === 'finalized') {
            return 'audit';
        } else if (status === 'review') {
            return 'review';
        } else if (status === 'mapping') {
            return 'draft';
        }
        
        return null;
    }

    addAccessModeIndicator(accessMode, processingStatus) {
        const indicator = document.getElementById('processingStateIndicator');
        if (!indicator) return;

        // Remove existing access mode indicator
        const existing = indicator.querySelector('.access-mode-indicator');
        if (existing) {
            existing.remove();
        }

        // Create new access mode indicator
        const accessIndicator = document.createElement('div');
        accessIndicator.className = `access-mode-indicator access-mode-${accessMode}`;
        accessIndicator.innerHTML = `
            <span class="access-mode-icon">${this.getAccessModeIcon(accessMode)}</span>
            <span class="access-mode-text">${this.getAccessModeText(accessMode)}</span>
        `;

        indicator.appendChild(accessIndicator);
    }

    getAccessModeIcon(accessMode) {
        const icons = {
            'draft': '📝',
            'review': '🔍',
            'audit': '🔒',
            'readonly': '👁️',
            'limited': '👁️'
        };
        return icons[accessMode] || '📊';
    }

    getAccessModeText(accessMode) {
        const texts = {
            'draft': 'Draft Mode',
            'review': 'Review Mode',
            'audit': 'Audit Mode',
            'readonly': 'Read-Only',
            'limited': 'Limited Access'
        };
        return texts[accessMode] || accessMode;
    }

    updateDraftStatementButton(status) {
        const button = document.querySelector('.draft-statement-controls button');
        if (!button) return;

        // Show button during mapping and processing phases
        if (status === 'mapping' || status === 'processing') {
            button.classList.add('display-inline-flex');
            button.disabled = false;
        } else {
            button.classList.add('display-none');
        }
    }

    
    // Public API methods
    async refreshProcessingState() {
        if (this.currentTrialBalance) {
            await this.loadProcessingState();
            this.updateProcessingStateIndicator();
        }
    }

    setTrialBalance(trialBalanceId) {
        this.currentTrialBalance = trialBalanceId;
        this.refreshProcessingState();
    }

    getCurrentProcessingState() {
        return this.processingState;
    }

    canViewFormulas() {
        if (!this.processingState) return false;
        
        const status = this.processingState.status;
        return status !== 'uploaded' && status !== 'unknown';
    }
}

// Global functions for template integration
function openDraftStatementViewer(trialBalanceId, statementType) {
    if (window.draftStatementViewerController) {
        window.draftStatementViewerController.open(trialBalanceId, statementType);
    }
}

function refreshProcessingState() {
    if (window.processingStateManager) {
        window.processingStateManager.refreshProcessingState();
    }
}

// Initialize the manager
window.processingStateManager = new ProcessingStateManager();

// Export for use in other scripts
window.ProcessingStateManager = ProcessingStateManager;
