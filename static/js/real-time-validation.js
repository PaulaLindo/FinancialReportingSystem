/**
 * Real-Time Balance Validation Service
 * Provides instant feedback during file upload and balance checking
 * Uses debouncing and progressive enhancement for better UX
 */

class RealTimeValidator {
    constructor() {
        this.debounceTimers = {};
        this.validationCache = new Map();
        this.isProcessing = false;
        this.progressCallbacks = [];
        this.lastValidatedFile = null; // Track last validated file
        this.settings = {
            debounceDelay: 500, // Increased to reduce frequency
            maxCacheSize: 50, // Reduced cache size
            enableProgressive: true,
            enableVisualFeedback: true,
            enableRealTimeValidation: false // Disabled by default
        };
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.setupProgressIndicator();
    }

    setupEventListeners() {
        // Only set up file input events if real-time validation is enabled
        if (this.settings.enableRealTimeValidation) {
            const fileInput = document.getElementById('fileInput');
            if (fileInput) {
                fileInput.addEventListener('change', this.debounce((e) => {
                    this.handleFileChange(e);
                }, this.settings.debounceDelay));

                fileInput.addEventListener('dragover', this.handleDragOver.bind(this));
                fileInput.addEventListener('dragleave', this.handleDragLeave.bind(this));
                fileInput.addEventListener('drop', this.handleFileDrop.bind(this));
            }
        }

        // Form validation events
        const balanceForm = document.getElementById('balanceForm');
        if (balanceForm) {
            const inputs = balanceForm.querySelectorAll('input, select, textarea');
            inputs.forEach(input => {
                input.addEventListener('input', this.debounce((e) => {
                    this.handleFormInput(e);
                }, this.settings.debounceDelay));
                input.addEventListener('blur', this.handleFormBlur.bind(this));
            });
        }

        // Button events
        const processBtn = document.getElementById('processBtn');
        if (processBtn) {
            processBtn.addEventListener('click', this.handleProcessClick.bind(this));
        }
    }

    setupProgressIndicator() {
        // Create progress indicator if it doesn't exist
        if (!document.getElementById('realTimeProgress')) {
            const progressContainer = document.createElement('div');
            progressContainer.id = 'realTimeProgress';
            progressContainer.classList.add('progress-hidden');
            progressContainer.innerHTML = `
                <div class="real-time-progress">
                    <div class="progress-bar">
                        <div class="progress-fill"></div>
                    </div>
                    <div class="progress-text">Validating...</div>
                </div>
                <div class="progress-details" id="progressDetails"></div>
            `;
            
            // Add CSS styles
            const style = document.createElement('style');
            style.textContent = `
                #realTimeProgress {
                    position: fixed;
                    top: 20px;
                    right: 20px;
                    background: var(--white);
                    border: 1px solid var(--border-light);
                    border-radius: var(--radius-md);
                    padding: var(--fluid-space-md);
                    box-shadow: var(--shadow-lg);
                    z-index: 1000;
                    min-width: 300px;
                    opacity: 0;
                    transform: translateY(-20px);
                    transition: all 0.3s ease;
                }
                
                #realTimeProgress.show {
                    opacity: 1;
                    transform: translateY(0);
                }
                
                .real-time-progress .progress-bar {
                    width: 100%;
                    height: 8px;
                    background: var(--gray-200);
                    border-radius: var(--radius-sm);
                    overflow: hidden;
                    margin-bottom: var(--fluid-space-sm);
                }
                
                .real-time-progress .progress-fill {
                    height: 100%;
                    background: linear-gradient(90deg, var(--primary) 0%, var(--primary-dark) 100%);
                    width: 0%;
                    transition: width 0.3s ease;
                }
                
                .real-time-progress .progress-text {
                    font-size: var(--fluid-text-sm);
                    color: var(--text-primary);
                    margin: 0 0 var(--fluid-space-xs) 0;
                }
                
                .progress-details {
                    font-size: var(--fluid-text-xs);
                    color: var(--text-secondary);
                }
            `;
            document.head.appendChild(style);
            
            // Insert into DOM
            const uploadSection = document.querySelector('.upload-section');
            if (uploadSection) {
                uploadSection.appendChild(progressContainer);
            }
        }
    }

    debounce(func, delay) {
        return (...args) => {
            const key = JSON.stringify(args);
            
            if (this.debounceTimers[key]) {
                clearTimeout(this.debounceTimers[key]);
            }
            
            this.debounceTimers[key] = setTimeout(() => {
                delete this.debounceTimers[key];
                func.apply(this, args);
            }, delay);
        };
    }

    async handleFileChange(event) {
        const file = event.target.files[0];
        if (!file) {
            this.clearValidation();
            return; // Early return if no file
        }
        
        // Skip validation if it's the same file
        const currentFileKey = `${file.name}_${file.size}_${file.lastModified}`;
        if (this.lastValidatedFile === currentFileKey) {
            return; // Already validated this file
        }

        // Show initial progress
        this.showProgress('Analyzing file...', 0);
        
        // Start file analysis
        this.isProcessing = true;
        
        try {
            // Quick file validation (only if not already cached)
            const validation = await this.validateFileQuick(file);
            
            if (validation.isValid) {
                this.showProgress('File format is valid', 25);
                await this.delay(500);
                this.showProgress('Checking balance...', 50);
                
                // Start balance check
                const balanceCheck = await this.checkBalance(file);
                
                if (balanceCheck.isValid) {
                    this.showProgress('Balance validated!', 100);
                    this.hideProgress();
                    
                    // Update UI
                    this.updateBalanceUI(balanceCheck);
                } else {
                    this.showProgress('Balance check failed', 75);
                    
                    // Show balance issues
                    this.showBalanceErrors(balanceCheck.errors);
                }
            } else {
                this.showProgress('Invalid file format', 0);
                this.showValidationErrors(validation.errors);
            }
            
            // Remember this file to avoid re-validation
            this.lastValidatedFile = currentFileKey;
            
        } catch (error) {
            this.showProgress('Validation error', 0);
            this.showErrorMessage(error.message);
        } finally {
            this.isProcessing = false;
        }
    }

    async validateFileQuick(file) {
        const cacheKey = `file_${file.name}_${file.size}_${file.lastModified}`;
        
        // Check cache first
        if (this.validationCache.has(cacheKey)) {
            return this.validationCache.get(cacheKey);
        }
        
        const validation = {
            isValid: false,
            errors: [],
            warnings: [],
            fileInfo: {
                name: file.name,
                size: file.size,
                type: file.type,
                lastModified: file.lastModified
            }
        };
        
        try {
            // Basic file checks
            if (!file.name) {
                validation.errors.push('No file selected');
                return validation;
            }
            
            // File extension check
            const validExtensions = ['xlsx', 'xls', 'csv'];
            const fileExtension = file.name.split('.').pop().toLowerCase();
            
            if (!validExtensions.includes(fileExtension)) {
                validation.errors.push(`Invalid file type: ${fileExtension}. Only ${validExtensions.join(', ')} are supported.`);
                return validation;
            }
            
            // File size check (max 16MB)
            const maxSize = 16 * 1024 * 1024; // 16MB
            if (file.size > maxSize) {
                validation.errors.push(`File too large: ${this.formatFileSize(file.size)}. Maximum size is ${this.formatFileSize(maxSize)}.`);
                return validation;
            }
            
            // File name check
            if (file.name.length > 100) {
                validation.warnings.push(`File name is very long: ${file.name.length} characters`);
            }
            
            validation.isValid = validation.errors.length === 0;
            
            // Cache the result
            if (this.validationCache.size < this.settings.maxCacheSize) {
                this.validationCache.set(cacheKey, validation);
            }
            
        } catch (error) {
            validation.errors.push(`Validation error: ${error.message}`);
        }
        
        return validation;
    }

    async checkBalance(file) {
        const cacheKey = `balance_${file.name}_${file.size}_${file.lastModified}`;
        
        // Check cache first
        if (this.validationCache.has(cacheKey)) {
            return this.validationCache.get(cacheKey);
        }
        
        const balanceCheck = {
            isValid: false,
            errors: [],
            warnings: [],
            balanceData: {
                totalDebits: 0,
                totalCredits: 0,
                difference: 0,
                debitColumns: [],
                creditColumns: []
            }
        };
        
        try {
            // Read file content for balance checking
            const fileContent = await this.readFileContent(file);
            
            if (!fileContent) {
                balanceCheck.errors.push('Could not read file content');
                return balanceCheck;
            }
            
            // Parse file content (basic CSV/Excel parsing)
            const data = this.parseFileContent(fileContent, file.name);
            
            if (!data || data.length === 0) {
                balanceCheck.errors.push('No data found in file');
                return balanceCheck;
            }
            
            // Find debit and credit columns
            const { debitColumns, creditColumns } = this.findBalanceColumns(data);
            
            if (debitColumns.length === 0 || creditColumns.length === 0) {
                balanceCheck.errors.push('No debit or credit columns found');
                return balanceCheck;
            }
            
            // Calculate totals
            let totalDebits = 0;
            let totalCredits = 0;
            
            data.forEach(row => {
                debitColumns.forEach(col => {
                    const value = parseFloat(row[col]) || 0;
                    if (!isNaN(value)) {
                        totalDebits += value;
                    }
                });
                
                creditColumns.forEach(col => {
                    const value = parseFloat(row[col]) || 0;
                    if (!isNaN(value)) {
                        totalCredits += value;
                    }
                });
            });
            
            const difference = Math.abs(totalDebits - totalCredits);
            
            balanceCheck.balanceData = {
                totalDebits,
                totalCredits,
                difference,
                debitColumns,
                creditColumns
            };
            
            balanceCheck.isValid = difference < 0.01; // Allow small rounding differences
            balanceCheck.warnings = difference > 0.01 ? [`Balance difference: R${difference.toFixed(2)}`] : [];
            
            // Cache the result
            if (this.validationCache.size < this.settings.maxCacheSize) {
                this.validationCache.set(cacheKey, balanceCheck);
            }
            
        } catch (error) {
            balanceCheck.errors.push(`Balance check error: ${error.message}`);
        }
        
        return balanceCheck;
    }

    async readFileContent(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            
            reader.onload = (e) => {
                try {
                    const content = e.target.result;
                    resolve(content);
                } catch (error) {
                    reject(error);
                }
            };
            
            reader.onerror = (error) => {
                reject(new Error(`File reading error: ${error}`));
            };
            
            if (file.type === 'text/csv' || file.name.endsWith('.csv')) {
                reader.readAsText(file);
            } else {
                reader.readAsArrayBuffer(file);
            }
        });
    }

    parseFileContent(content, fileName) {
        // Simple CSV/Excel parsing
        const lines = content.split('\n').filter(line => line.trim());
        
        if (lines.length === 0) {
            return [];
        }
        
        // Parse headers
        const headers = lines[0].split(',').map(h => h.trim());
        
        // Parse data rows
        const data = [];
        for (let i = 1; i < lines.length; i++) {
            const values = lines[i].split(',').map(v => v.trim());
            
            if (values.length === headers.length) {
                const row = {};
                headers.forEach((header, index) => {
                    row[header] = values[index];
                });
                data.push(row);
            }
        }
        
        return data;
    }

    findBalanceColumns(data) {
        const debitColumns = [];
        const creditColumns = [];
        
        if (data.length === 0) return { debitColumns, creditColumns };
        
        const headers = Object.keys(data[0]);
        
        headers.forEach(header => {
            const headerLower = header.toLowerCase();
            
            // Check for debit indicators
            if (headerLower.includes('debit') || headerLower.includes('dr') || 
                headerLower.includes('expense') || headerLower.includes('outflow')) {
                debitColumns.push(header);
            }
            
            // Check for credit indicators
            if (headerLower.includes('credit') || headerLower.includes('cr') || 
                headerLower.includes('income') || headerLower.includes('inflow') || 
                headerLower.includes('revenue') || headerLower.includes('receipt')) {
                creditColumns.push(header);
            }
        });
        
        return { debitColumns, creditColumns };
    }

    showProgress(message, percentage) {
        const progressContainer = document.getElementById('realTimeProgress');
        if (!progressContainer) return;
        
        const progressFill = progressContainer.querySelector('.progress-fill');
        const progressText = progressContainer.querySelector('.progress-text');
        
        // Show the container
        progressContainer.classList.remove('progress-hidden');
        
        if (progressFill) {
            progressFill.classList.add('progress-bar-dynamic');
            // Set progress using CSS variable
            progressFill.style.setProperty('--progress-width', `${percentage}%`);
            progressFill.setAttribute('aria-valuenow', percentage);
        }
        
        if (progressText) {
            progressText.textContent = message;
        }
        
        progressContainer.classList.add('show');
        
        // Auto-hide after 3 seconds
        setTimeout(() => {
            progressContainer.classList.remove('show');
        }, 3000);
    }

    hideProgress() {
        const progressContainer = document.getElementById('realTimeProgress');
        if (progressContainer) {
            progressContainer.classList.remove('show');
            // Hide the container after the transition
            setTimeout(() => {
                progressContainer.classList.add('progress-hidden');
            }, 300);
        }
    }

    showValidationErrors(errors) {
        const errorContainer = document.getElementById('validationErrors');
        if (!errorContainer) {
            // Create error container if it doesn't exist
            const container = document.querySelector('.upload-section');
            if (container) {
                const errorDiv = document.createElement('div');
                errorDiv.id = 'validationErrors';
                errorDiv.className = 'validation-errors';
                container.appendChild(errorDiv);
            }
        }
        
        if (errorContainer && errors.length > 0) {
            errorContainer.innerHTML = `
                <h4 class="validation-error-header">Validation Errors</h4>
                <ul class="validation-error-list">
                    ${errors.map(error => `<li class="validation-error-item">• ${error}</li>`).join('')}
                </ul>
            `;
        } else {
            errorContainer.classList.add('error-hidden');
        }
    }

    showBalanceErrors(errors) {
        const errorContainer = document.getElementById('balanceErrors');
        if (!errorContainer) {
            // Create balance error container if it doesn't exist
            const container = document.querySelector('.upload-section');
            if (container) {
                const errorDiv = document.createElement('div');
                errorDiv.id = 'balanceErrors';
                errorDiv.className = 'balance-errors';
                container.appendChild(errorDiv);
            }
        }
        
        if (errorContainer && errors.length > 0) {
            errorContainer.innerHTML = `
                <h4 class="validation-error-header">Balance Validation Errors</h4>
                <ul class="validation-error-list">
                    ${errors.map(error => `<li class="validation-error-item">• ${error}</li>`).join('')}
                </ul>
            `;
        } else {
            errorContainer.classList.add('error-hidden');
        }
    }

    showErrorMessage(message) {
        const errorContainer = document.getElementById('validationErrors');
        if (errorContainer) {
            errorContainer.innerHTML = `
                <h4 class="error-title">Error</h4>
                <p class="error-message">${message}</p>
            `;
            errorContainer.classList.remove('error-hidden');
        }
    }

    updateBalanceUI(balanceData) {
        // Update balance display elements
        const totalDebitsEl = document.getElementById('totalDebits');
        const totalCreditsEl = document.getElementById('totalCredits');
        const differenceEl = document.getElementById('balanceDifference');
        const balanceStatusEl = document.getElementById('balanceStatus');
        
        if (totalDebitsEl) {
            totalDebitsEl.textContent = this.formatCurrency(balanceData.totalDebits);
        }
        
        if (totalCreditsEl) {
            totalCreditsEl.textContent = this.formatCurrency(balanceData.totalCredits);
        }
        
        if (differenceEl) {
            differenceEl.textContent = this.formatCurrency(Math.abs(balanceData.difference));
            differenceEl.classList.add(balanceData.difference > 0.01 ? 'difference-error' : 'difference-success');
        }
        
        if (balanceStatusEl) {
            if (balanceData.difference < 0.01) {
                balanceStatusEl.textContent = '✅ Balanced';
                balanceStatusEl.className = 'balance-status balanced';
            } else {
                balanceStatusEl.textContent = '⚠️ Not Balanced';
                balanceStatusEl.className = 'balance-status not-balanced';
            }
        }
    }

    formatCurrency(amount) {
        return new Intl.NumberFormat('en-ZA', {
            style: 'currency',
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        }).format(amount);
    }

    async delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    // Public methods
    
    /**
     * Enable real-time validation (call this when user wants real-time feedback)
     */
    enableRealTimeValidation() {
        if (!this.settings.enableRealTimeValidation) {
            this.settings.enableRealTimeValidation = true;
            this.setupEventListeners(); // Re-setup with real-time enabled
        }
    }
    
    /**
     * Disable real-time validation to save resources
     */
    disableRealTimeValidation() {
        if (this.settings.enableRealTimeValidation) {
            this.settings.enableRealTimeValidation = false;
            this.cleanup(); // Remove event listeners
        }
    }
    
    /**
     * Manual file validation (call this instead of relying on real-time)
     */
    async validateFile(file) {
        return await this.validateFileQuick(file);
    }
    
    /**
     * Cleanup resources and event listeners
     */
    cleanup() {
        // Clear all debounce timers
        Object.keys(this.debounceTimers).forEach(key => {
            clearTimeout(this.debounceTimers[key]);
            delete this.debounceTimers[key];
        });
        
        // Clear cache if it's too large
        if (this.validationCache.size > this.settings.maxCacheSize) {
            const entriesToDelete = this.validationCache.size - this.settings.maxCacheSize;
            const keysToDelete = Array.from(this.validationCache.keys()).slice(0, entriesToDelete);
            keysToDelete.forEach(key => this.validationCache.delete(key));
        }
        
        // Remove event listeners
        const fileInput = document.getElementById('fileInput');
        if (fileInput) {
            fileInput.removeEventListener('change', this.handleFileChange);
            fileInput.removeEventListener('dragover', this.handleDragOver);
            fileInput.removeEventListener('dragleave', this.handleDragLeave);
            fileInput.removeEventListener('drop', this.handleFileDrop);
        }
    }

    async checkFileBalance(file) {
        return await this.checkBalance(file);
    }

    clearCache() {
        this.validationCache.clear();
    }

    updateSettings(newSettings) {
        this.settings = { ...this.settings, ...newSettings };
    }

    getValidationSummary() {
        return {
            cacheSize: this.validationCache.size,
            maxCacheSize: this.settings.maxCacheSize,
            isProcessing: this.isProcessing,
            settings: this.settings
        };
    }

    // Missing handler methods that were referenced but didn't exist
    handleDragOver(event) {
        event.preventDefault();
        event.stopPropagation();
        
        const fileInput = document.getElementById('fileInput');
        if (fileInput) {
            fileInput.classList.add('upload-zone--hover');
        }
        
        this.showProgress('Drag file over...', 25);
    }

    handleDragLeave(event) {
        event.preventDefault();
        event.stopPropagation();
        
        const fileInput = document.getElementById('fileInput');
        if (fileInput) {
            fileInput.classList.remove('upload-zone--hover');
        }
        
        this.hideProgress();
    }

    handleFileDrop(event) {
        event.preventDefault();
        event.stopPropagation();
        
        const fileInput = document.getElementById('fileInput');
        if (fileInput) {
            fileInput.classList.remove('upload-zone--hover');
        }
        
        const files = event.dataTransfer.files;
        if (files && files.length > 0) {
            // Simulate file input change
            const dataTransfer = new DataTransfer();
            dataTransfer.items.add(files[0]);
            fileInput.files = dataTransfer.files;
            
            // Trigger change event
            fileInput.dispatchEvent(new Event('change', { bubbles: true }));
        }
    }

    handleFormInput(event) {
        const input = event.target;
        const value = input.value.trim();
        
        if (value.length > 0) {
            input.classList.remove('error');
            this.showProgress('Validating input...', 50);
        } else {
            this.hideProgress();
        }
    }

    handleFormBlur(event) {
        const input = event.target;
        const value = input.value.trim();
        
        if (value.length === 0) {
            input.classList.add('error');
        } else {
            input.classList.remove('error');
        }
    }

    handleProcessClick(event) {
        const processBtn = document.getElementById('processBtn');
        if (processBtn) {
            processBtn.disabled = true;
            processBtn.textContent = 'Processing...';
            this.showProgress('Processing file...', 75);
        }
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.realTimeValidator = new RealTimeValidator();
    
    // Cleanup on page unload to prevent memory leaks
    window.addEventListener('beforeunload', () => {
        if (window.realTimeValidator) {
            window.realTimeValidator.cleanup();
        }
    });
    
    // Cleanup on visibility change (user switches tabs)
    document.addEventListener('visibilitychange', () => {
        if (document.hidden && window.realTimeValidator) {
            // Disable real-time validation when tab is not visible
            window.realTimeValidator.disableRealTimeValidation();
        }
    });
    
    // Real-Time Balance Validator ready
});
