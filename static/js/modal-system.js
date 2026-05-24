/**
 * Modal System - Replaces browser-native dialogs with in-app modals
 * Provides consistent UI for prompts, confirms, and alerts
 */

class ModalSystem {
    constructor() {
        this.init();
    }

    init() {
        // Create modal container if it doesn't exist
        if (!document.getElementById('modalSystem')) {
            const container = document.createElement('div');
            container.id = 'modalSystem';
            document.body.appendChild(container);
        }
    }

    /**
     * Show a prompt modal
     * @param {string} title - Modal title
     * @param {string} message - Modal message
     * @param {string} defaultValue - Default input value
     * @param {Object} options - Additional options
     * @returns {Promise<string>} User input value
     */
    async prompt(title, message, defaultValue = '', options = {}) {
        return new Promise((resolve) => {
            const modal = this.createModal('prompt', title, message, defaultValue, options);
            const input = modal.querySelector('.modal-input');

            setTimeout(() => {
                input?.focus();
                input?.select();
            }, 100);

            this._bindModalActions(modal, {
                onConfirm: () => {
                    const value = input?.value.trim() || defaultValue;
                    this.removeModal(modal);
                    resolve(value);
                },
                onCancel: () => {
                    this.removeModal(modal);
                    resolve(null);
                },
            });

            input?.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    modal.querySelector('.modal-confirm')?.click();
                }
            });

            document.addEventListener('keydown', (e) => {
                if (e.key === 'Escape') {
                    modal.querySelector('.modal-cancel')?.click();
                }
            }, { once: true });
        });
    }

    /**
     * Show a confirm modal
     * @param {string} title - Modal title
     * @param {string} message - Modal message
     * @param {Object} options - Additional options
     * @returns {Promise<boolean>} True if confirmed, false if cancelled
     */
    async confirm(title, message, options = {}) {
        return new Promise((resolve) => {
            const modal = this.createModal('confirm', title, message, '', options);

            this._bindModalActions(modal, {
                onConfirm: () => {
                    this.removeModal(modal);
                    resolve(true);
                },
                onCancel: () => {
                    this.removeModal(modal);
                    resolve(false);
                },
            });

            document.addEventListener('keydown', (e) => {
                if (e.key === 'Escape') {
                    modal.querySelector('.modal-cancel')?.click();
                }
            }, { once: true });
        });
    }

    /**
     * Show an alert modal
     * @param {string} title - Modal title
     * @param {string} message - Modal message
     * @param {Object} options - Additional options
     * @returns {Promise<void>} Resolved when modal is closed
     */
    async alert(title, message, options = {}) {
        return new Promise((resolve) => {
            const modal = this.createModal('alert', title, message, '', options);

            const handleClose = () => {
                this.removeModal(modal);
                resolve();
            };

            this._bindModalActions(modal, {
                onConfirm: handleClose,
                onCancel: handleClose,
            });

            document.addEventListener('keydown', (e) => {
                if (e.key === 'Escape' || e.key === 'Enter') {
                    modal.querySelector('.modal-ok')?.click();
                }
            }, { once: true });
        });
    }

    /**
     * Create modal element
     * @param {string} type - Modal type (prompt, confirm, alert)
     * @param {string} title - Modal title
     * @param {string} message - Modal message
     * @param {string} defaultValue - Default value for prompts
     * @param {Object} options - Additional options
     * @returns {HTMLElement} Modal element
     */
    createModal(type, title, message, defaultValue = '', options = {}) {
        const container = document.getElementById('modalSystem');
        
        const modalHTML = `
            <div class="modal-overlay">
                <div class="modal-container modal-${type}">
                    <div class="modal-header">
                        <h3 class="modal-title">${this.escapeHtml(title)}</h3>
                        <button type="button" class="modal-close" aria-label="Close modal">
                            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <line x1="18" y1="6" x2="6" y2="18"></line>
                                <line x1="6" y1="6" x2="18" y2="18"></line>
                            </svg>
                        </button>
                    </div>
                    <div class="modal-body">
                        <p class="modal-message">${this.escapeHtml(message)}</p>
                        ${type === 'prompt' ? `
                            <input type="text" class="modal-input" value="${this.escapeHtml(defaultValue)}" placeholder="${options.placeholder || 'Enter value...'}">
                        ` : ''}
                    </div>
                    <div class="modal-footer">
                        ${type === 'prompt' ? `
                            <button type="button" class="btn btn-secondary modal-cancel">Cancel</button>
                            <button type="button" class="btn btn-primary modal-confirm">OK</button>
                        ` : ''}
                        ${type === 'confirm' ? `
                            <button type="button" class="btn btn-secondary modal-cancel">${options.cancelText || 'Cancel'}</button>
                            <button type="button" class="btn btn-primary modal-confirm">${options.confirmText || 'Confirm'}</button>
                        ` : ''}
                        ${type === 'alert' ? `
                            <button type="button" class="btn btn-primary modal-ok">OK</button>
                        ` : ''}
                    </div>
                </div>
            </div>
        `;

        container.insertAdjacentHTML('beforeend', modalHTML);
        return container.lastElementChild;
    }

    /**
     * Remove modal from DOM
     * @param {HTMLElement} modal - Modal element to remove
     */
    removeModal(modal) {
        if (modal && modal.parentNode) {
            modal.parentNode.removeChild(modal);
        }
        const host = document.getElementById('modalSystem');
        if (host && !host.children.length) {
            document.body.classList.remove('modal-system-open');
        }
    }

    /**
     * Bind dismiss/confirm handlers without click-through to elements beneath the overlay.
     */
    _bindModalActions(modal, { onConfirm, onCancel }) {
        let settled = false;
        const finish = (handler) => (e) => {
            if (e) {
                e.preventDefault();
                e.stopPropagation();
            }
            if (settled) return;
            settled = true;
            window.setTimeout(() => {
                handler();
            }, 0);
        };

        const confirmBtn = modal.querySelector('.modal-confirm');
        const cancelBtn = modal.querySelector('.modal-cancel');
        const closeBtn = modal.querySelector('.modal-close');
        const okBtn = modal.querySelector('.modal-ok');

        confirmBtn?.addEventListener('mousedown', (e) => e.preventDefault());
        cancelBtn?.addEventListener('mousedown', (e) => e.preventDefault());
        closeBtn?.addEventListener('mousedown', (e) => e.preventDefault());
        okBtn?.addEventListener('mousedown', (e) => e.preventDefault());

        confirmBtn?.addEventListener('click', finish(onConfirm));
        cancelBtn?.addEventListener('click', finish(onCancel));
        closeBtn?.addEventListener('click', finish(onCancel));
        okBtn?.addEventListener('click', finish(onConfirm));

        modal.addEventListener('mousedown', (e) => {
            if (e.target === modal) {
                e.preventDefault();
            }
        });
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                finish(onCancel)(e);
            }
        });

        document.body.classList.add('modal-system-open');
    }

    /**
     * Escape HTML to prevent XSS
     * @param {string} text - Text to escape
     * @returns {string} Escaped text
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Show a success notification (toast-style)
     * @param {string} message - Success message
     * @param {Object} options - Additional options
     */
    showSuccess(message, options = {}) {
        this.showToast(message, 'success', options);
    }

    /**
     * Show an error notification (toast-style)
     * @param {string} message - Error message
     * @param {Object} options - Additional options
     */
    showError(message, options = {}) {
        this.showToast(message, 'error', options);
    }

    /**
     * Show an info notification (toast-style)
     * @param {string} message - Info message
     * @param {Object} options - Additional options
     */
    showInfo(message, options = {}) {
        this.showToast(message, 'info', options);
    }

    /**
     * Show a toast notification
     * @param {string} message - Toast message
     * @param {string} type - Toast type (success, error, info)
     * @param {Object} options - Additional options
     */
    showToast(message, type = 'info', options = {}) {
        if (window.VarydianUtils && typeof VarydianUtils.showToast === 'function') {
            VarydianUtils.showToast(message, type, {
                duration: options.duration || (type === 'error' ? 12000 : 8000),
            });
            return;
        }
        const duration = options.duration || (type === 'error' ? 12000 : 8000);
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.innerHTML = `
            <div class="toast-content">
                <span class="toast-message">${this.escapeHtml(message)}</span>
                <button class="toast-close" aria-label="Close notification">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <line x1="18" y1="6" x2="6" y2="18"></line>
                        <line x1="6" y1="6" x2="18" y2="18"></line>
                    </svg>
                </button>
            </div>
        `;

        // Add to container or create one
        let container = document.querySelector('.toast-container');
        if (!container) {
            container = document.createElement('div');
            container.className = 'toast-container';
            document.body.appendChild(container);
        }

        container.appendChild(toast);

        // Handle close
        const closeToast = () => {
            toast.classList.add('toast-hiding');
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
            }, 300);
        };

        // Event listeners
        toast.querySelector('.toast-close').addEventListener('click', closeToast);

        // Auto-remove after duration
        if (duration > 0) {
            setTimeout(closeToast, duration);
        }

        // Handle hover to pause auto-remove
        let timeoutId;
        if (duration > 0) {
            timeoutId = setTimeout(closeToast, duration);
        }

        toast.addEventListener('mouseenter', () => {
            if (timeoutId) {
                clearTimeout(timeoutId);
            }
        });

        toast.addEventListener('mouseleave', () => {
            if (duration > 0) {
                timeoutId = setTimeout(closeToast, duration);
            }
        });
    }
}

// Initialize modal system
window.modalSystem = new ModalSystem();

// Global convenience functions that replace browser natives
window.showPrompt = (title, message, defaultValue, options) => window.modalSystem.prompt(title, message, defaultValue, options);
window.showConfirm = (title, message, options) => window.modalSystem.confirm(title, message, options);
window.showAlert = (title, message, options) => window.modalSystem.alert(title, message, options);

// Toast notifications
window.showSuccess = (message, options) => window.modalSystem.showSuccess(message, options);
window.showError = (message, options) => window.modalSystem.showError(message, options);
window.showInfo = (message, options) => window.modalSystem.showInfo(message, options);
