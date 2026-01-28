/**
 * Upload Module
 * SADPMR Financial Reporting System
 */

// Upload namespace
SADPMR.upload = {
    elements: {
        form: null,
        fileInput: null,
        uploadBox: null,
        dropZone: null,
        fileInfo: null,
        progressBar: null,
        submitBtn: null,
        resultsContainer: null,
        errorContainer: null
    },

    config: {
        maxFileSize: 16 * 1024 * 1024, // 16MB
        allowedTypes: [
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'application/vnd.ms-excel',
            'text/csv'
        ],
        allowedExtensions: ['.xlsx', '.xls', '.csv'],
        apiEndpoint: '/api/upload',
        chunkSize: 1024 * 1024, // 1MB chunks
        maxRetries: 3
    },

    state: {
        isUploading: false,
        currentFile: null,
        uploadProgress: 0,
        retryCount: 0
    },

    /**
     * Initialize upload functionality
     */
    init() {
        this.cacheElements();
        if (!this.elements.form) {
            console.warn('Upload elements not found');
            return;
        }
        this.bindEvents();
        this.setupDragDrop();
    },

    /**
     * Cache DOM elements
     */
    cacheElements() {
        this.elements = {
            form: document.getElementById('uploadForm'),
            fileInput: document.getElementById('fileInput'),
            uploadBox: document.getElementById('uploadBox'),
            dropZone: document.getElementById('dropZone'),
            fileInfo: document.getElementById('fileInfo'),
            progressBar: document.getElementById('progressBar'),
            submitBtn: document.getElementById('submitBtn'),
            resultsContainer: document.getElementById('resultsContainer'),
            errorContainer: document.getElementById('errorContainer')
        };
    },

    /**
     * Bind event listeners
     */
    bindEvents() {
        const { form, fileInput, submitBtn } = this.elements;

        // Form submission
        form.addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleUpload();
        });

        // File input change
        fileInput.addEventListener('change', (e) => {
            this.handleFileSelect(e.target.files[0]);
        });

        // Submit button click
        submitBtn.addEventListener('click', () => {
            this.handleUpload();
        });

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            // Ctrl/Cmd + O to open file dialog
            if ((e.ctrlKey || e.metaKey) && e.key === 'o') {
                e.preventDefault();
                fileInput.click();
            }
            
            // Escape to cancel upload
            if (e.key === 'Escape' && this.state.isUploading) {
                this.cancelUpload();
            }
        });
    },

    /**
     * Setup drag and drop functionality
     */
    setupDragDrop() {
        const { dropZone, uploadBox } = this.elements;

        if (!dropZone) return;

        // Prevent default drag behaviors
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, this.preventDefaults, false);
            document.body.addEventListener(eventName, this.preventDefaults, false);
        });

        // Highlight drop zone when item is dragged over it
        ['dragenter', 'dragover'].forEach(eventName => {
            dropZone.addEventListener(eventName, () => {
                this.highlight();
            }, false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, () => {
                this.unhighlight();
            }, false);
        });

        // Handle dropped files
        dropZone.addEventListener('drop', (e) => {
            const files = e.dataTransfer.files;
            this.handleFileSelect(files[0]);
        }, false);

        // Make upload box clickable
        if (uploadBox) {
            uploadBox.addEventListener('click', () => {
                this.elements.fileInput.click();
            });
        }
    },

    /**
     * Prevent default event behavior
     * @param {Event} e - Event object
     */
    preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    },

    /**
     * Highlight drop zone
     */
    highlight() {
        const { dropZone } = this.elements;
        if (dropZone) {
            dropZone.classList.add('dragover');
        }
    },

    /**
     * Unhighlight drop zone
     */
    unhighlight() {
        const { dropZone } = this.elements;
        if (dropZone) {
            dropZone.classList.remove('dragover');
        }
    },

    /**
     * Handle file selection
     * @param {File} file - Selected file
     */
    handleFileSelect(file) {
        if (!file) {
            this.clearFileInfo();
            return;
        }

        // Validate file
        const validation = this.validateFile(file);
        if (!validation.valid) {
            SADPMR.utils.showAlert(validation.error, 'error');
            this.clearFileInfo();
            return;
        }

        // Store file and update UI
        this.state.currentFile = file;
        this.updateFileInfo(file);
        this.enableSubmit();
    },

    /**
     * Validate file
     * @param {File} file - File to validate
     * @returns {Object} Validation result
     */
    validateFile(file) {
        // Check file size
        if (file.size > this.config.maxFileSize) {
            return {
                valid: false,
                error: `File size must be less than ${this.formatFileSize(this.config.maxFileSize)}`
            };
        }

        // Check file type
        if (!this.config.allowedTypes.includes(file.type)) {
            return {
                valid: false,
                error: `File type not supported. Please upload ${this.config.allowedExtensions.join(', ')}`
            };
        }

        // Check file extension
        const extension = '.' + file.name.split('.').pop().toLowerCase();
        if (!this.config.allowedExtensions.includes(extension)) {
            return {
                valid: false,
                error: `File extension not supported. Please upload ${this.config.allowedExtensions.join(', ')}`
            };
        }

        return { valid: true };
    },

    /**
     * Update file information display
     * @param {File} file - File to display info for
     */
    updateFileInfo(file) {
        const { fileInfo } = this.elements;
        if (!fileInfo) return;

        fileInfo.innerHTML = `
            <div class="file-info-content">
                <div class="file-icon">📄</div>
                <div class="file-details">
                    <div class="file-name">${this.escapeHtml(file.name)}</div>
                    <div class="file-meta">
                        <span class="file-size">${this.formatFileSize(file.size)}</span>
                        <span class="file-type">${file.type || 'Unknown'}</span>
                    </div>
                </div>
                <button type="button" class="file-remove" aria-label="Remove file">×</button>
            </div>
        `;

        // Bind remove button
        const removeBtn = fileInfo.querySelector('.file-remove');
        if (removeBtn) {
            removeBtn.addEventListener('click', () => {
                this.clearFileInfo();
            });
        }
    },

    /**
     * Clear file information
     */
    clearFileInfo() {
        const { fileInfo, fileInput } = this.elements;
        
        if (fileInfo) {
            fileInfo.innerHTML = '';
        }
        
        if (fileInput) {
            fileInput.value = '';
        }
        
        this.state.currentFile = null;
        this.disableSubmit();
    },

    /**
     * Enable submit button
     */
    enableSubmit() {
        const { submitBtn } = this.elements;
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.classList.remove('disabled');
        }
    },

    /**
     * Disable submit button
     */
    disableSubmit() {
        const { submitBtn } = this.elements;
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.classList.add('disabled');
        }
    },

    /**
     * Handle file upload
     */
    async handleUpload() {
        if (!this.state.currentFile || this.state.isUploading) {
            return;
        }

        this.state.isUploading = true;
        this.state.uploadProgress = 0;
        this.state.retryCount = 0;

        this.showProgress();
        this.disableSubmit();

        try {
            const result = await this.uploadFile(this.state.currentFile);
            this.handleUploadSuccess(result);
        } catch (error) {
            this.handleUploadError(error);
        } finally {
            this.state.isUploading = false;
            this.hideProgress();
            this.enableSubmit();
        }
    },

    /**
     * Upload file to server
     * @param {File} file - File to upload
     * @returns {Promise} Upload result
     */
    async uploadFile(file) {
        const formData = new FormData();
        formData.append('file', file);

        const response = await fetch(this.config.apiEndpoint, {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': SADPMR.utils.getCSRFToken()
            }
        });

        if (!response.ok) {
            throw new Error(`Upload failed: ${response.statusText}`);
        }

        return await response.json();
    },

    /**
     * Handle successful upload
     * @param {Object} result - Upload result
     */
    handleUploadSuccess(result) {
        SADPMR.utils.showAlert('File uploaded successfully!', 'success');
        this.displayResults(result);
        this.clearFileInfo();
        this.emitEvent('upload:success', result);
    },

    /**
     * Handle upload error
     * @param {Error} error - Upload error
     */
    handleUploadError(error) {
        console.error('Upload error:', error);
        
        const errorMessage = error.message || 'Upload failed. Please try again.';
        SADPMR.utils.showAlert(errorMessage, 'error');
        
        this.displayError(errorMessage);
        this.emitEvent('upload:error', error);
    },

    /**
     * Cancel upload
     */
    cancelUpload() {
        if (this.state.isUploading) {
            this.state.isUploading = false;
            this.hideProgress();
            this.enableSubmit();
            SADPMR.utils.showAlert('Upload cancelled', 'info');
            this.emitEvent('upload:cancelled');
        }
    },

    /**
     * Show progress indicator
     */
    showProgress() {
        const { progressBar } = this.elements;
        if (progressBar) {
            progressBar.style.display = 'block';
            this.updateProgress(0);
        }
    },

    /**
     * Hide progress indicator
     */
    hideProgress() {
        const { progressBar } = this.elements;
        if (progressBar) {
            progressBar.style.display = 'none';
        }
    },

    /**
     * Update progress
     * @param {number} progress - Progress percentage (0-100)
     */
    updateProgress(progress) {
        const { progressBar } = this.elements;
        if (progressBar) {
            const progressFill = progressBar.querySelector('.progress-fill');
            const progressText = progressBar.querySelector('.progress-text');
            
            if (progressFill) {
                progressFill.style.width = `${progress}%`;
            }
            
            if (progressText) {
                progressText.textContent = `${Math.round(progress)}%`;
            }
        }
        
        this.state.uploadProgress = progress;
    },

    /**
     * Display upload results
     * @param {Object} result - Upload results
     */
    displayResults(result) {
        const { resultsContainer } = this.elements;
        if (!resultsContainer || !result.data) return;

        // This would be implemented based on the actual result structure
        resultsContainer.innerHTML = this.generateResultsHTML(result.data);
        resultsContainer.style.display = 'block';
        
        // Scroll to results
        SADPMR.utils.scrollToElement(resultsContainer, 100);
    },

    /**
     * Display error message
     * @param {string} message - Error message
     */
    displayError(message) {
        const { errorContainer } = this.elements;
        if (!errorContainer) return;

        errorContainer.innerHTML = `
            <div class="alert alert-error">
                <strong>Error:</strong> ${this.escapeHtml(message)}
            </div>
        `;
        errorContainer.style.display = 'block';
    },

    /**
     * Generate results HTML
     * @param {Object} data - Results data
     * @returns {string} HTML string
     */
    generateResultsHTML(data) {
        // This would be implemented based on the actual data structure
        return `
            <div class="results-summary">
                <h3>Processing Complete</h3>
                <div class="summary-grid">
                    <div class="summary-card">
                        <h4>Total Assets</h4>
                        <div class="amount">${SADPMR.utils.formatCurrency(data.totalAssets || 0)}</div>
                    </div>
                    <div class="summary-card">
                        <h4>Total Liabilities</h4>
                        <div class="amount">${SADPMR.utils.formatCurrency(data.totalLiabilities || 0)}</div>
                    </div>
                </div>
            </div>
        `;
    },

    /**
     * Format file size
     * @param {number} bytes - File size in bytes
     * @returns {string} Formatted file size
     */
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    },

    /**
     * Escape HTML
     * @param {string} text - Text to escape
     * @returns {string} Escaped text
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },

    /**
     * Emit custom event
     * @param {string} eventName - Event name
     * @param {Object} data - Event data
     */
    emitEvent(eventName, data = {}) {
        const event = new CustomEvent(eventName, {
            detail: {
                file: this.state.currentFile,
                progress: this.state.uploadProgress,
                ...data
            }
        });
        document.dispatchEvent(event);
    },

    /**
     * Get upload state
     * @returns {Object} Current upload state
     */
    getState() {
        return {
            ...this.state,
            hasFile: !!this.state.currentFile,
            canUpload: !!this.state.currentFile && !this.state.isUploading
        };
    },

    /**
     * Destroy upload module
     */
    destroy() {
        const { form, fileInput } = this.elements;

        // Remove event listeners
        if (form) {
            form.removeEventListener('submit', this.handleUpload);
        }
        
        if (fileInput) {
            fileInput.removeEventListener('change', this.handleFileSelect);
        }

        // Clear state
        this.state = {
            isUploading: false,
            currentFile: null,
            uploadProgress: 0,
            retryCount: 0
        };

        // Clear cache
        this.elements = {};

        console.log('Upload module destroyed');
    }
};

// Auto-initialize if DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        SADPMR.upload.init();
    });
} else {
    SADPMR.upload.init();
}
