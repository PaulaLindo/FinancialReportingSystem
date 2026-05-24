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
            TIMEOUT: 60000,
            /** Large file upload + row persistence can exceed the default timeout. */
            UPLOAD_TIMEOUT: 180000
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
     * Human-readable workflow status (no underscores), e.g. pending_review → Pending Review.
     */
    static formatWorkflowStatus(status) {
        if (status == null || status === '') return '—';
        const key = String(status).toLowerCase().trim();
        const labels = {
            pending_review: 'Pending Review',
            pending_cfo: 'Pending CFO Approval',
            pending: 'Pending Review',
            approved_by_manager: 'Approved by Manager',
            approved: 'Approved',
            rejected_by_manager: 'Rejected by Manager',
            rejected_by_cfo: 'Rejected by CFO',
            rejected: 'Rejected',
            finalized: 'Finalized',
            draft: 'Draft',
            submitted: 'Submitted',
            completed: 'Completed',
            processing: 'Processing',
        };
        if (labels[key]) return labels[key];
        return key
            .split('_')
            .filter(Boolean)
            .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
            .join(' ');
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
     * Centered toast (mapping, review, upload). Stays visible longer; click or × to dismiss.
     * @param {string} message
     * @param {'success'|'error'|'info'|'warning'} [type='info']
     * @param {{ duration?: number }} [options]
     */
    static showToast(message, type = 'info', options = {}) {
        const duration =
            options.duration != null
                ? options.duration
                : type === 'error'
                  ? 12000
                  : 8000;

        let stack = document.getElementById('varydianToastStack');
        if (!stack) {
            stack = document.createElement('div');
            stack.id = 'varydianToastStack';
            stack.className = 'varydian-toast-stack';
            stack.setAttribute('aria-live', 'polite');
            document.body.appendChild(stack);
        }

        const toast = document.createElement('div');
        toast.className = `varydian-toast varydian-toast--${type}`;
        toast.setAttribute('role', 'alert');

        const text = document.createElement('p');
        text.className = 'varydian-toast__message';
        text.textContent = message;

        const closeBtn = document.createElement('button');
        closeBtn.type = 'button';
        closeBtn.className = 'varydian-toast__close';
        closeBtn.setAttribute('aria-label', 'Dismiss');
        closeBtn.textContent = '×';

        const remove = () => {
            toast.classList.remove('varydian-toast--visible');
            window.setTimeout(() => toast.remove(), 280);
        };

        closeBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            remove();
        });
        toast.addEventListener('click', remove);

        toast.appendChild(text);
        toast.appendChild(closeBtn);
        stack.appendChild(toast);

        requestAnimationFrame(() => toast.classList.add('varydian-toast--visible'));

        const timer = window.setTimeout(remove, duration);
        const cancelTimer = () => window.clearTimeout(timer);
        closeBtn.addEventListener('click', cancelTimer, { once: true });
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
        const { timeout = this.CONFIG.API.TIMEOUT, ...fetchOptions } = options;
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), timeout);

        try {
            // Use base URL for API requests
            const fullUrl = url.startsWith('/') ? `${this.CONFIG.BASE_URL}${url}` : url;
            
                        
            const response = await fetch(fullUrl, {
                ...fetchOptions,
                signal: controller.signal,
                credentials: 'include' // Include cookies for authentication
            });
            clearTimeout(timeoutId);
            
            if (!response.ok) {
                let errorMessage = `HTTP error! status: ${response.status}`;
                let responseData = null;
                try {
                    const errorText = await response.text();
                    if (errorText) {
                        try {
                            responseData = JSON.parse(errorText);
                            if (responseData.error) {
                                errorMessage = `HTTP error! status: ${response.status} - ${JSON.stringify(responseData)}`;
                            } else {
                                errorMessage += ` - ${errorText}`;
                            }
                        } catch (_parseErr) {
                            errorMessage += ` - ${errorText}`;
                        }
                    }
                } catch (e) {
                    // If we can't read the response text, just use the status
                }

                const httpError = new Error(errorMessage);
                httpError.status = response.status;
                httpError.responseData = responseData;
                throw httpError;
            }
            
            return await response.json();
        } catch (error) {
            clearTimeout(timeoutId);
            if (error.name === 'AbortError' || String(error.message || '').includes('aborted')) {
                const timeoutError = new Error(
                    `Request timed out after ${timeout / 1000} seconds. Please try again.`
                );
                timeoutError.name = 'AbortError';
                throw timeoutError;
            }
            throw error;
        }
    }

    /**
     * Format date/time for UI display: ``2026-05-03 21:46`` (matches server display_datetime).
     */
    static formatDate(dateString) {
        return VarydianUtils.formatDateTime(dateString);
    }

    static formatDateTime(dateString) {
        if (dateString == null || dateString === '') return '';

        if (dateString instanceof Date && !isNaN(dateString.getTime())) {
            const pad = (n) => String(n).padStart(2, '0');
            return `${dateString.getFullYear()}-${pad(dateString.getMonth() + 1)}-${pad(dateString.getDate())} ${pad(dateString.getHours())}:${pad(dateString.getMinutes())}`;
        }

        let text = String(dateString).trim();
        if (!text) return '';

        text = text.replace('Z', '');
        if (text.includes('+')) {
            text = text.split('+', 1)[0];
        }
        if (text.includes('.')) {
            text = text.split('.', 1)[0];
        }

        const isoMatch = text.match(/^(\d{4}-\d{2}-\d{2})[T ](\d{2}):(\d{2})/);
        if (isoMatch) {
            return `${isoMatch[1]} ${isoMatch[2]}:${isoMatch[3]}`;
        }

        const dateOnly = text.match(/^(\d{4}-\d{2}-\d{2})/);
        if (dateOnly) {
            return dateOnly[1];
        }

        const date = new Date(text);
        if (isNaN(date.getTime())) {
            return String(dateString).trim();
        }

        const pad = (n) => String(n).padStart(2, '0');
        return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`;
    }

    /**
     * Show branding information
     */
    static showBranding() {
        console.log('🏛️ Varydian Financial Reporting System');
        console.log('📊 GRAP-Compliant Financial Statement Automation');
        console.log('🔐 Secure, Efficient, User-Friendly');
    }

    /**
     * Show an element without breaking flex/grid layouts (pairs with visibility-layout.css).
     * @param {HTMLElement|null} el
     * @param {'block'|'flex'|'grid'} [displayMode='block']
     */
    static showElement(el, displayMode = 'block') {
        if (!el) return;
        el.classList.remove('element--hidden', 'element--visible-flex', 'element--visible-grid');
        el.classList.add('element--visible');
        if (displayMode === 'flex') el.classList.add('element--visible-flex');
        if (displayMode === 'grid') el.classList.add('element--visible-grid');
    }

    /**
     * Hide an element and clear layout visibility modifiers.
     * @param {HTMLElement|null} el
     */
    static hideElement(el) {
        if (!el) return;
        el.classList.add('element--hidden');
        el.classList.remove('element--visible', 'element--visible-flex', 'element--visible-grid');
    }

    /** Icon slot inside cards (visibility-layout.css scopes display). */
    static showIcon(el) {
        VarydianUtils.showElement(el);
    }

    static hideIcon(el) {
        VarydianUtils.hideElement(el);
    }

    /**
     * Show inline spinner on a button while an async action runs.
     * @param {HTMLButtonElement|null} btn
     * @param {boolean} busy
     * @param {string} [labelWhileBusy='Processing…']
     */
    static setButtonBusy(btn, busy, labelWhileBusy = 'Processing…') {
        if (!btn) return;
        if (busy) {
            if (!btn.dataset.varydianBusyLabel) {
                btn.dataset.varydianBusyLabel = (btn.textContent || '').trim();
            }
            btn.disabled = true;
            btn.setAttribute('aria-busy', 'true');
            btn.classList.add('btn-is-busy');
            btn.replaceChildren();
            const spinner = document.createElement('span');
            spinner.className = 'spinner spinner-sm btn-busy-spinner';
            spinner.setAttribute('aria-hidden', 'true');
            const labelEl = document.createElement('span');
            labelEl.className = 'btn-busy-label';
            labelEl.textContent = labelWhileBusy;
            btn.append(spinner, labelEl);
            const card = btn.closest('.transaction-actions');
            if (card) {
                card.querySelectorAll('button').forEach((other) => {
                    if (other !== btn) other.disabled = true;
                });
            }
        } else {
            VarydianUtils.clearButtonBusy(btn);
        }
    }

    /**
     * Restore button label after setButtonBusy.
     * @param {HTMLButtonElement|null} btn
     */
    static clearButtonBusy(btn) {
        if (!btn) return;
        btn.disabled = false;
        btn.removeAttribute('aria-busy');
        btn.classList.remove('btn-is-busy');
        const orig = btn.dataset.varydianBusyLabel;
        if (orig) {
            btn.textContent = orig;
        }
        delete btn.dataset.varydianBusyLabel;
        const card = btn.closest('.transaction-actions');
        if (card) {
            card.querySelectorAll('button').forEach((other) => {
                other.disabled = false;
            });
        }
    }
}

// Export for global use
window.VarydianUtils = VarydianUtils;
/** @param {string|Date|null|undefined} value */
window.formatDisplayDateTime = (value) => VarydianUtils.formatDateTime(value);
/** @param {string|null|undefined} status */
window.formatWorkflowStatus = (status) => VarydianUtils.formatWorkflowStatus(status);
