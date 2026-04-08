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
        
        // Check authentication on page load
        this.checkAuthentication();
        
        // Setup logout functionality
        this.setupLogout();
        
        // Setup periodic authentication check
        this.setupAuthCheck();
    }

    /**
     * Check if user is authenticated
     */
    isAuthenticated() {
        const authData = localStorage.getItem('sadpmr_auth');
        if (!authData) return false;
        
        try {
            const parsed = JSON.parse(authData);
            const now = Date.now();
            
            // Check if session is still valid (1 hour)
            return parsed.loginTime && (now - parsed.loginTime) < 3600000;
        } catch {
            return false;
        }
    }

    /**
     * Get current user data
     */
    getCurrentUser() {
        if (!this.isAuthenticated()) return null;
        
        try {
            const authData = localStorage.getItem('sadpmr_auth');
            return JSON.parse(authData).user;
        } catch {
            return null;
        }
    }

    /**
     * Check authentication and redirect if needed
     */
    checkAuthentication() {
        const currentPage = window.location.pathname.split('/').pop() || 'index.html';
        const publicPages = ['login.html', 'about.html'];
        
        // If not authenticated and not on public page, redirect to login
        if (!this.isAuthenticated() && !publicPages.includes(currentPage)) {
            // Store the intended destination for redirect after login
            localStorage.setItem('sadpmr_redirect', currentPage);
            window.location.href = 'login.html';
            return false;
        }
        
        // If authenticated and on login page, redirect to dashboard
        if (this.isAuthenticated() && currentPage === 'login.html') {
            const redirect = localStorage.getItem('sadpmr_redirect') || 'index.html';
            localStorage.removeItem('sadpmr_redirect');
            window.location.href = redirect;
            return false;
        }
        
        // Update UI with user data if authenticated
        if (this.isAuthenticated()) {
            this.updateUIWithUserData();
        }
        
        return true;
    }

    /**
     * Update UI elements with current user data
     */
    updateUIWithUserData() {
        const user = this.getCurrentUser();
        if (!user) return;

        // Update user name
        const userNameElements = document.querySelectorAll('.user-name');
        userNameElements.forEach(el => {
            el.textContent = user.fullName || user.username || 'User';
        });

        // Update user role
        const userRoleElements = document.querySelectorAll('.user-role');
        userRoleElements.forEach(el => {
            el.textContent = user.role || 'USER';
            // Update role class for styling
            el.className = `user-role user-role--${(user.role || 'user').toLowerCase()}`;
        });

        // Update welcome message
        const welcomeElements = document.querySelectorAll('h1');
        welcomeElements.forEach(el => {
            if (el.textContent.includes('Welcome back')) {
                el.textContent = `Welcome back, ${user.fullName || user.username || 'User'}!`;
            }
        });
    }

    /**
     * Setup logout functionality
     */
    setupLogout() {
        const logoutButtons = document.querySelectorAll('.logout-btn');
        logoutButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                e.preventDefault();
                this.logout();
            });
        });
    }

    /**
     * Logout user
     */
    logout() {
        localStorage.removeItem('sadpmr_auth');
        localStorage.removeItem('sadpmr_redirect');
        window.location.href = 'login.html';
    }

    /**
     * Setup periodic authentication check
     */
    setupAuthCheck() {
        // Check authentication every 30 seconds
        setInterval(() => {
            this.checkAuthentication();
        }, 30000);
    }

    /**
     * Login user (called after successful login)
     */
    login(userData) {
        const authData = {
            user: userData,
            loginTime: Date.now()
        };
        
        localStorage.setItem('sadpmr_auth', JSON.stringify(authData));
        
        // Redirect to intended page or dashboard
        const redirect = localStorage.getItem('sadpmr_redirect') || 'index.html';
        localStorage.removeItem('sadpmr_redirect');
        window.location.href = redirect;
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
        } else {
            // Process login
            e.preventDefault();
            this.processLogin(username.value, password.value);
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
     * Process login authentication
     */
    processLogin(username, password) {
        // Demo user credentials
        const demoUsers = {
            'cfo@sadpmr.gov.za': {
                fullName: 'Sarah Nkosi',
                username: 'sarah.nkosi',
                role: 'CFO',
                permissions: ['upload', 'process', 'generate_pdf', 'admin']
            },
            'accountant@sadpmr.gov.za': {
                fullName: 'Thabo Molefe',
                username: 'thabo.molefe',
                role: 'Accountant',
                permissions: ['upload', 'process', 'generate_pdf']
            },
            'clerk@sadpmr.gov.za': {
                fullName: 'Zama Khumalo',
                username: 'zama.khumalo',
                role: 'Clerk',
                permissions: ['upload']
            },
            'auditor@agsa.gov.za': {
                fullName: 'Peter Ndlovu',
                username: 'peter.ndlovu',
                role: 'Auditor',
                permissions: []
            }
        };

        // Check credentials
        if (demoUsers[username] && password === 'demo123') {
            const userData = demoUsers[username];
            this.login(userData);
        } else {
            // Show error
            this.showLoginError('Invalid username or password');
        }
    }

    /**
     * Show login error message
     */
    showLoginError(message) {
        // Create error alert if it doesn't exist
        let errorAlert = document.querySelector('.alert-error');
        if (!errorAlert) {
            errorAlert = document.createElement('div');
            errorAlert.className = 'alert alert-error';
            errorAlert.textContent = message;
            
            const loginBox = document.querySelector('.login-box');
            const form = document.querySelector('#loginForm');
            loginBox.insertBefore(errorAlert, form);
            
            // Auto-hide after 5 seconds
            setTimeout(() => {
                errorAlert.remove();
            }, 5000);
        }
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
        
        // Process the login
        this.processLogin(username, password);
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
