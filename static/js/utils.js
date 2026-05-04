/**
 * Varydian Financial Reporting System - Shared Utilities
 * Common utility functions used across the application
 */

class VarydianUtils {
    // Configuration constants
    static CONFIG = {
        // Base URL for API requests - helps identify routing issues
        BASE_URL: window.location.origin,
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
            ALLOWED_TYPES: [
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',  // .xlsx
                'application/vnd.ms-excel',  // .xls
                'text/csv',  // .csv
                'application/csv',  // Alternative CSV MIME type
                'text/plain',  // Some systems send CSV as plain text
                'application/octet-stream',  // Generic binary - let server validate
                'application/excel',  // Some older systems
                'application/x-excel',  // Alternative Excel MIME type
                'application/x-msexcel',  // Another Excel variant
                'application/vnd.ms-excel.sheet.macroEnabled.12',  // .xlsm
                'application/vnd.ms-excel.sheet.binary.macroEnabled.12',  // .xlsb
                'text/comma-separated-values',  // CSV variant
                'text/tab-separated-values'  // TSV files
            ],
            ALLOWED_EXTENSIONS: ['xlsx', 'xls', 'csv', 'xlsm', 'xlsb', 'tsv']
        },
        API: {
            TIMEOUT: 60000
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
            errorEl.classList.add('error-message--visible');
            errorEl.classList.remove('error-message--hidden');
            this.scrollToElement(errorEl, { block: 'center' });
        }
    }

    /**
     * Hide error message
     */
    static hideError(errorElement = null) {
        const errorEl = errorElement || document.getElementById('errorMessage');
        if (errorEl) {
            errorEl.classList.add('error-message--hidden');
            errorEl.classList.remove('error-message--visible');
        }
    }

    /**
     * Validate file type and size
     */
    static validateFile(file) {
        // Check file size first
        const maxSizeBytes = this.CONFIG.FILE.MAX_SIZE_MB * 1024 * 1024;
        if (file.size > maxSizeBytes) {
            return {
                valid: false,
                error: `File too large. Maximum size is ${this.CONFIG.FILE.MAX_SIZE_MB}MB.`
            };
        }

        // Check file extension - be more permissive and let server handle detailed validation
        const fileExtension = file.name.toLowerCase().split('.').pop();
        const supportedExtensions = ['xlsx', 'xls', 'csv', 'xlsm', 'xlsb', 'tsv'];
        
        if (!supportedExtensions.includes(fileExtension)) {
            return {
                valid: false,
                error: `Unsupported file format: .${fileExtension}\n\n` +
                      `Supported formats: ${supportedExtensions.map(ext => '.' + ext).join(', ')}\n\n` +
                      `Please export your balance sheet as an Excel file (.xlsx, .xls) or CSV file (.csv).`
            };
        }

        // For supported extensions, be permissive with MIME types
        // The server will handle detailed format validation
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
            element.classList.add('fade-in-element--initial');
            element.classList.remove('fade-in-element--animated');
            
            // Add delay class if needed
            if (index === 0 && delay > 0) {
                element.classList.add('fade-in-element--delay-1');
            }
            
            setTimeout(() => {
                element.classList.add('fade-in-element--animated');
                element.classList.remove('fade-in-element--initial');
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
            // Use base URL for API requests
            const fullUrl = url.startsWith('/') ? `${this.CONFIG.BASE_URL}${url}` : url;
            
                        
            const response = await fetch(fullUrl, {
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
                
                // Add helpful context for common routing issues
                if (response.status === 404 && url.startsWith('/api/')) {
                    errorMessage += `\n\n⚠️ Routing Issue Detected:\nIf you're seeing this error, make sure you're accessing the app through http://localhost:5000 (not through IDE preview or direct file opening).`;
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
     * Format date string consistently across the application
     */
    static formatDate(dateString, options = {}) {
        if (!dateString) return 'Invalid Date';
        
        const date = new Date(dateString);
        if (isNaN(date.getTime())) return 'Invalid Date';
        
        const defaultOptions = {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        };
        
        return date.toLocaleDateString('en-US', { ...defaultOptions, ...options });
    }

    /**
     * Show branding information
     */
    static showBranding() {
        console.log('🏛️ Varydian Financial Reporting System');
        console.log('📊 GRAP-Compliant Financial Statement Automation');
        console.log('🔐 Secure, Efficient, User-Friendly');
    }

    }

// Export for global use
window.VarydianUtils = VarydianUtils;
