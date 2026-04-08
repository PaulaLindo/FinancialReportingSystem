/**
 * SADPMR Financial Reporting System - Authentication Module
 * Handles login functionality, form validation, and user authentication
 */

class AuthenticationModule {
    constructor() {
        this.elements = {};
        this.init();
    }

    /**
     * Initialize authentication module
     */
    init() {
        this.cacheElements();
        this.setupEventListeners();
        this.setupAutoHideAlerts();
    }

    /**
     * Cache DOM elements
     */
    cacheElements() {
        this.elements = {
            loginForm: document.getElementById('loginForm'),
            usernameInput: document.getElementById('username'),
            passwordInput: document.getElementById('password'),
            quickLoginButtons: document.querySelectorAll('.quick-login-btn'),
            alerts: document.querySelectorAll('.alert')
        };
    }

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // Form submission validation
        if (this.elements.loginForm) {
            this.elements.loginForm.addEventListener('submit', (e) => {
                this.handleFormSubmit(e);
            });
        }

        // Clear error states on input
        if (this.elements.usernameInput) {
            this.elements.usernameInput.addEventListener('input', () => {
                this.clearInputError(this.elements.usernameInput);
            });
        }

        if (this.elements.passwordInput) {
            this.elements.passwordInput.addEventListener('input', () => {
                this.clearInputError(this.elements.passwordInput);
            });
        }

        // Quick login buttons
        this.elements.quickLoginButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                const username = e.target.getAttribute('data-username') || 
                               this.extractUsernameFromText(e.target.textContent);
                const password = 'demo123';
                this.quickLogin(username, password);
            });
        });
    }

    /**
     * Handle form submission with validation
     */
    handleFormSubmit(e) {
        const username = this.elements.usernameInput;
        const password = this.elements.passwordInput;
        
        // Reset any previous error states
        this.clearInputError(username);
        this.clearInputError(password);
        
        let isValid = true;
        
        // Validate email
        if (!username.value || !username.value.includes('@')) {
            this.showInputError(username);
            isValid = false;
        }
        
        // Validate password
        if (!password.value || password.value.length < 1) {
            this.showInputError(password);
            isValid = false;
        }
        
        if (!isValid) {
            e.preventDefault();
        }
    }

    /**
     * Show input error state
     */
    showInputError(input) {
        input.style.borderColor = 'var(--error)';
    }

    /**
     * Clear input error state
     */
    clearInputError(input) {
        input.style.borderColor = 'var(--gray-300)';
    }

    /**
     * Quick login functionality
     */
    quickLogin(username, password) {
        if (this.elements.usernameInput) {
            this.elements.usernameInput.value = username;
        }
        if (this.elements.passwordInput) {
            this.elements.passwordInput.value = password;
        }
        if (this.elements.loginForm) {
            this.elements.loginForm.submit();
        }
    }

    /**
     * Extract username from button text
     */
    extractUsernameFromText(text) {
        // Extract email from text like "Quick Login: CFO"
        const roleMap = {
            'CFO': 'cfo@sadpmr.gov.za',
            'Accountant': 'accountant@sadpmr.gov.za',
            'Clerk': 'clerk@sadpmr.gov.za',
            'Auditor': 'auditor@agsa.gov.za'
        };
        
        for (const [role, email] of Object.entries(roleMap)) {
            if (text.includes(role)) {
                return email;
            }
        }
        
        return '';
    }

    /**
     * Setup auto-hide alerts
     */
    setupAutoHideAlerts() {
        setTimeout(() => {
            this.elements.alerts.forEach(alert => {
                alert.classList.add('auth__alert--animated');
                alert.classList.add('auth__alert--dismissing');
                setTimeout(() => alert.remove(), 500);
            });
        }, 5000);
    }

    /**
     * Cleanup method
     */
    destroy() {
        // Remove event listeners if needed
    }
}

// Global function for backward compatibility with inline onclick handlers
function quickLogin(username, password) {
    if (window.authModule) {
        window.authModule.quickLogin(username, password);
    }
}

// Initialize authentication module when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.authModule = new AuthenticationModule();
});

// Handle page unload for cleanup
window.addEventListener('beforeunload', () => {
    if (window.authModule) {
        window.authModule.destroy();
    }
});
