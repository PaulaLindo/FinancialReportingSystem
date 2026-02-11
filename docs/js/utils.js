/**
 * SADPMR Financial Reporting System - Shared Utilities
 * Common utility functions used across the application
 */

class SADPMRUtils {
    // Configuration constants
    static CONFIG = {
        ANIMATION: {
            DURATION: 800,
            EASING: 'cubic-bezier(0.4, 0, 0.2, 1)',
            SCROLL_OFFSET: -50
        },
        BREAKPOINTS: {
            // Mobile Devices
            TINY_MOBILE: 280,      // Very small phones (< 320px)
            SMALL_MOBILE: 320,    // Small phones (320px - 374px)
            MOBILE: 375,          // Standard mobile (375px - 480px)
            MOBILE_LARGE: 481,    // Large mobile (481px - 767px)
            
            // Tablet Devices
            TABLET: 768,          // Standard tablet (768px - 1023px)
            TABLET_LARGE: 1024,   // Large tablets (1024px - 1365px)
            TABLET_PRO: 1366,     // iPad Pro/Large tablets (1366px - 1439px)
            
            // Desktop Devices
            DESKTOP: 1440,        // Standard desktop (1440px - 1919px)
            DESKTOP_LARGE: 1920,  // Large desktop (1920px - 2559px)
            DESKTOP_2K: 2560,     // 2K/4K displays (2560px+)
            
            // Helper breakpoints
            MOBILE_MAX: 767,      // Maximum mobile width
            TABLET_MAX: 1023,     // Maximum tablet width
            TABLET_LARGE_MAX: 1365, // Maximum large tablet width
            DESKTOP_MIN: 1440     // Minimum desktop width
        },
        FILE: {
            MAX_SIZE_MB: 16,
            ALLOWED_TYPES: ['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 
                           'application/vnd.ms-excel', 
                           'text/csv'],
            ALLOWED_EXTENSIONS: ['xlsx', 'xls', 'csv']
        },
        API: {
            TIMEOUT: 30000
        }
    };

    /**
     * Format currency with South African formatting
     */
    static formatCurrency(amount, currency = 'R') {
        const sign = amount >= 0 ? '' : '-';
        const abs = Math.abs(amount);
        return sign + currency + ' ' + abs.toLocaleString('en-ZA', { 
            minimumFractionDigits: 2, 
            maximumFractionDigits: 2 
        });
    }

    /**
     * Debounce function to limit function calls
     */
    static debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    /**
     * Throttle function to limit function calls
     */
    static throttle(func, limit) {
        let inThrottle;
        return function(...args) {
            if (!inThrottle) {
                func.apply(this, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }

    /**
     * Smooth scroll to element
     */
    static scrollToElement(element, options = {}) {
        if (!element) return;
        
        const defaultOptions = {
            behavior: 'smooth',
            block: 'start',
            inline: 'nearest'
        };
        
        element.scrollIntoView({ ...defaultOptions, ...options });
    }

    /**
     * Animate number counter
     */
    static animateCounter(element, finalValue, duration = 2000) {
        const isPercentage = finalValue.includes('%');
        const numValue = parseInt(finalValue);
        const steps = 60;
        const increment = numValue / steps;
        let current = 0;

        const timer = setInterval(() => {
            current += increment;
            if (current >= numValue) {
                element.textContent = finalValue;
                clearInterval(timer);
            } else {
                element.textContent = Math.floor(current) + (isPercentage ? '%' : 's');
            }
        }, duration / steps);
    }

    /**
     * Show error message
     */
    static showError(message, errorElement = null) {
        const errorEl = errorElement || document.getElementById('errorMessage');
        if (errorEl) {
            errorEl.textContent = '❌ ' + message;
            errorEl.style.display = 'block';
            this.scrollToElement(errorEl, { block: 'center' });
        }
    }

    /**
     * Hide error message
     */
    static hideError(errorElement = null) {
        const errorEl = errorElement || document.getElementById('errorMessage');
        if (errorEl) {
            errorEl.style.display = 'none';
        }
    }

    /**
     * Validate file type and size
     */
    static validateFile(file) {
        // Check file type
        const isValidType = this.CONFIG.FILE.ALLOWED_TYPES.includes(file.type) || 
                           this.CONFIG.FILE.ALLOWED_EXTENSIONS.some(ext => 
                               file.name.toLowerCase().endsWith(`.${ext}`)
                           );
        
        if (!isValidType) {
            return {
                valid: false,
                error: `Invalid file type. Please upload ${this.CONFIG.FILE.ALLOWED_EXTENSIONS.join(', ').toUpperCase()} file.`
            };
        }

        // Check file size
        const maxSizeBytes = this.CONFIG.FILE.MAX_SIZE_MB * 1024 * 1024;
        if (file.size > maxSizeBytes) {
            return {
                valid: false,
                error: `File too large. Maximum size is ${this.CONFIG.FILE.MAX_SIZE_MB}MB.`
            };
        }

        return { valid: true };
    }

    /**
     * Format file size for display
     */
    static formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    /**
     * Create intersection observer with default options
     */
    static createIntersectionObserver(callback, options = {}) {
        const defaultOptions = {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        };
        
        return new IntersectionObserver(callback, { ...defaultOptions, ...options });
    }

    /**
     * Add fade-in animation to elements
     */
    static addFadeInAnimation(elements, delay = 0) {
        elements.forEach((element, index) => {
            element.style.opacity = '0';
            element.style.transform = 'translateY(30px)';
            element.style.transition = `all ${this.CONFIG.ANIMATION.DURATION}ms ${this.CONFIG.ANIMATION.EASING}`;
            element.style.transitionDelay = `${delay + index * 0.1}s`;
            
            setTimeout(() => {
                element.style.opacity = '1';
                element.style.transform = 'translateY(0)';
            }, 100);
        });
    }

    /**
     * Check if device is mobile
     */
    static isMobile() {
        return window.innerWidth <= this.CONFIG.BREAKPOINTS.MOBILE;
    }

    /**
     * Safe fetch with timeout and error handling
     */
    static async safeFetch(url, options = {}) {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), this.CONFIG.API.TIMEOUT);

        try {
            const response = await fetch(url, {
                ...options,
                signal: controller.signal,
                credentials: 'include' // Include cookies for authentication
            });
            clearTimeout(timeoutId);
            
            if (!response.ok) {
                // Try to get more error details
                let errorMessage = `HTTP error! status: ${response.status}`;
                try {
                    const errorText = await response.text();
                    if (errorText) {
                        errorMessage += ` - ${errorText}`;
                    }
                } catch (e) {
                    // If we can't read the response text, just use the status
                }
                throw new Error(errorMessage);
            }
            
            return await response.json();
        } catch (error) {
            clearTimeout(timeoutId);
            throw error;
        }
    }

    /**
     * Console branding
     */
    static showBranding() {
        console.log('%c SADPMR Financial Reporting System ', 'background: #0a1128; color: #d4a574; font-size: 18px; padding: 10px; font-weight: bold;');
        console.log('%c Built with precision for public sector excellence ', 'background: #10b981; color: white; font-size: 12px; padding: 5px;');
        console.log('%c February 3, 2026 Demo | Schedule 3A PFMA Compliance ', 'color: #1e3a5f; font-size: 11px;');
        console.log('\n👋 Interested in the technology behind this system?\nGet in touch: demo@sadpmr-system.co.za');
    }
}

// Export for global use
window.SADPMRUtils = SADPMRUtils;
