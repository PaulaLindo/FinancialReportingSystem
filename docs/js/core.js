/**
 * Core JavaScript - Global utilities and initialization
 * SADPMR Financial Reporting System
 */

// Global namespace
window.SADPMR = window.SADPMR || {};

// Core utilities
SADPMR.utils = {
    /**
     * Debounce function to limit function calls
     * @param {Function} func - Function to debounce
     * @param {number} wait - Wait time in milliseconds
     * @returns {Function} Debounced function
     */
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },

    /**
     * Throttle function to limit function calls
     * @param {Function} func - Function to throttle
     * @param {number} limit - Limit time in milliseconds
     * @returns {Function} Throttled function
     */
    throttle(func, limit) {
        let inThrottle;
        return function(...args) {
            if (!inThrottle) {
                func.apply(this, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    },

    /**
     * Check if element is in viewport
     * @param {Element} element - Element to check
     * @returns {boolean} True if element is in viewport
     */
    isInViewport(element) {
        const rect = element.getBoundingClientRect();
        return (
            rect.top >= 0 &&
            rect.left >= 0 &&
            rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
            rect.right <= (window.innerWidth || document.documentElement.clientWidth)
        );
    },

    /**
     * Smooth scroll to element
     * @param {string|Element} target - Target element or selector
     * @param {number} offset - Offset from top
     */
    scrollToElement(target, offset = 0) {
        const element = typeof target === 'string' ? document.querySelector(target) : target;
        if (element) {
            const top = element.offsetTop - offset;
            window.scrollTo({
                top,
                behavior: 'smooth'
            });
        }
    },

    /**
     * Format currency
     * @param {number} amount - Amount to format
     * @param {string} currency - Currency code
     * @returns {string} Formatted currency
     */
    formatCurrency(amount, currency = 'ZAR') {
        return new Intl.NumberFormat('en-ZA', {
            style: 'currency',
            currency: currency,
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        }).format(amount);
    },

    /**
     * Show loading state
     * @param {Element} element - Element to show loading in
     * @param {string} message - Loading message
     */
    showLoading(element, message = 'Loading...') {
        if (!element) return;
        
        const originalContent = element.innerHTML;
        element.dataset.originalContent = originalContent;
        
        const spinner = document.createElement('div');
        spinner.className = 'spinner';
        spinner.setAttribute('role', 'status');
        spinner.setAttribute('aria-label', message);
        
        element.innerHTML = '';
        element.appendChild(spinner);
        element.disabled = true;
    },

    /**
     * Hide loading state
     * @param {Element} element - Element to hide loading from
     */
    hideLoading(element) {
        if (!element || !element.dataset.originalContent) return;
        
        element.innerHTML = element.dataset.originalContent;
        element.disabled = false;
        delete element.dataset.originalContent;
    },

    /**
     * Show alert message
     * @param {string} message - Alert message
     * @param {string} type - Alert type (success, error, warning, info)
     * @param {number} duration - Duration in milliseconds
     */
    showAlert(message, type = 'info', duration = 5000) {
        const alertContainer = document.getElementById('alertContainer') || this.createAlertContainer();
        
        const alert = document.createElement('div');
        alert.className = `alert alert-${type}`;
        alert.textContent = message;
        alert.setAttribute('role', 'alert');
        
        alertContainer.appendChild(alert);
        
        // Auto remove after duration
        setTimeout(() => {
            if (alert.parentNode) {
                alert.parentNode.removeChild(alert);
            }
        }, duration);
        
        // Remove on click
        alert.addEventListener('click', () => {
            if (alert.parentNode) {
                alert.parentNode.removeChild(alert);
            }
        });
    },

    /**
     * Create alert container
     * @returns {Element} Alert container element
     */
    createAlertContainer() {
        const container = document.createElement('div');
        container.id = 'alertContainer';
        container.className = 'alert-container';
        container.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 9999;
            max-width: 400px;
        `;
        document.body.appendChild(container);
        return container;
    },

    /**
     * Get CSRF token
     * @returns {string} CSRF token
     */
    getCSRFToken() {
        const meta = document.querySelector('meta[name="csrf-token"]');
        return meta ? meta.getAttribute('content') : '';
    },

    /**
     * Make API request
     * @param {string} url - Request URL
     * @param {Object} options - Request options
     * @returns {Promise} Response promise
     */
    async fetch(url, options = {}) {
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCSRFToken()
            }
        };

        const finalOptions = {
            ...defaultOptions,
            ...options,
            headers: {
                ...defaultOptions.headers,
                ...options.headers
            }
        };

        try {
            const response = await fetch(url, finalOptions);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error('API request failed:', error);
            this.showAlert('Request failed. Please try again.', 'error');
            throw error;
        }
    }
};

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', function() {
    console.log('SADPMR Financial Reporting System initialized');
    
    // Initialize components
    if (typeof SADPMR.mobileMenu !== 'undefined') {
        SADPMR.mobileMenu.init();
    }
    
    if (typeof SADPMR.upload !== 'undefined') {
        SADPMR.upload.init();
    }
    
    // Add smooth scroll behavior for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            const target = this.getAttribute('href');
            SADPMR.utils.scrollToElement(target, 80);
        });
    });
    
    // Initialize responsive behavior
    SADPMR.utils.handleResponsive = SADPMR.utils.debounce(function() {
        // Handle responsive changes
        const isMobile = window.innerWidth <= 768;
        document.body.classList.toggle('mobile', isMobile);
        document.body.classList.toggle('desktop', !isMobile);
    }, 250);
    
    window.addEventListener('resize', SADPMR.utils.handleResponsive);
    SADPMR.utils.handleResponsive();
});

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SADPMR;
}
