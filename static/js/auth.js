/**
 * Varydian Financial Reporting System - Authentication Module
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
            button.addEventListener('click', async (e) => {
                
                try {
                    const username = e.target.getAttribute('data-username') || 
                                   this.extractUsernameFromText(e.target.textContent);
                    
                    // Show loading state
                    button.disabled = true;
                    button.innerHTML = '<span class="spinner"></span> Logging in...';
                    
                    // Fill form and submit directly to server
                    if (this.elements.usernameInput) {
                        this.elements.usernameInput.value = username;
                    }
                    if (this.elements.passwordInput) {
                        // Use correct password for each user
                        const passwordMap = {
                            'cfo@sadpmr.gov.za': 'demo123',
                            'finance.manager@sadpmr.gov.za': 'demo123',
                            'finance.clerk@sadpmr.gov.za': 'finance123',
                            'asset.manager@sadpmr.gov.za': 'demo123',
                            'auditor@agsa.gov.za': 'demo123'
                        };
                        this.elements.passwordInput.value = passwordMap[username] || 'demo123';
                    }
                    
                    // Submit the form
                    if (this.elements.loginForm) {
                        this.elements.loginForm.submit();
                    } else {
                        alert('Login form not found');
                        this.showError('Login form not found');
                    }
                } catch (error) {
                    this.showError('Quick login failed: ' + error.message);
                } finally {
                    // Reset button state after a delay
                    setTimeout(() => {
                        button.disabled = false;
                        button.innerHTML = e.target.textContent;
                    }, 3000); // Increased to 3 seconds to see what happens
                }
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
        input.classList.add('input-error');
        input.classList.remove('input-valid');
    }

    /**
     * Clear input error state
     */
    clearInputError(input) {
        input.classList.remove('input-error');
        input.classList.add('input-valid');
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
            'Finance Manager': 'finance.manager@sadpmr.gov.za',
            'Finance Clerk': 'finance.clerk@sadpmr.gov.za',
            'Asset Manager': 'asset.manager@sadpmr.gov.za',
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
     * Get user from Supabase
     */
    async getUserFromSupabase(username) {
        try {
            const response = await fetch('/api/auth/user', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ username })
            });
            
            const result = await response.json();
            return result.success ? result.user : null;
        } catch (error) {
            return null;
        }
    }

    /**
     * Perform Supabase login
     */
    async performSupabaseLogin(username, password) {
        try {
            const response = await fetch('/api/auth/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ username, password })
            });
            
            const result = await response.json();
            return result;
        } catch (error) {
            return { success: false, error: error.message };
        }
    }

    /**
     * Set user session
     */
    setSession(user) {
        // Session is managed server-side via Supabase
        
        // Update current user in auth module
        if (window.authModule) {
            window.authModule.currentUser = user;
        }
    }

    /**
     * Role-based redirect
     */
    redirectByRole(role) {
        const roleRoutes = {
            'SYSTEM_ADMIN': '/admin',
            'CFO': '/dashboard',
            'FINANCE_MANAGER': '/approvals',
            'ASSET_MANAGER': '/upload',
            'FINANCIAL_CLERK': '/approvals',
            'AUDITOR': '/reports'
        };
        
        const targetRoute = roleRoutes[role] || '/dashboard';
        window.location.href = targetRoute;
    }

    /**
     * Show success message
     */
    showSuccess(message) {
        this.showAlert(message, 'success');
    }

    /**
     * Show error message
     */
    showError(message) {
        this.showAlert(message, 'error');
    }

    /**
     * Show alert message
     */
    showAlert(message, type = 'info') {
        if (this.elements.alerts) {
            const alert = document.createElement('div');
            alert.className = `auth__alert auth__alert--${type}`;
            alert.innerHTML = `
                <div class="auth__alert-content">
                    <div class="auth__alert-icon">${type === 'success' ? '✓' : '⚠'}</div>
                    <div class="auth__alert-message">${message}</div>
                    <button class="auth__alert-close" onclick="this.parentElement.remove()">✕</button>
                </div>
            `;
            
            document.body.appendChild(alert);
            
            // Auto-remove after 5 seconds
            setTimeout(() => {
                if (alert && alert.parentNode) {
                    alert.remove();
                }
            }, 5000);
        }
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
        }, 500);
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
