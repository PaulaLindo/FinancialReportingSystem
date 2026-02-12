/**
 * SADPMR Financial Reporting System - Upload Functionality
 * Refactored upload service with better error handling and state management
 */

class UploadService {
    constructor() {
        this.state = {
            uploadedFilePath: null,
            resultsFile: null,
            isProcessing: false,
            currentStep: null
        };
        
        this.elements = {};
        this.boundMethods = {};
        this.init();
    }

    /**
     * Initialize upload service
     */
    init() {
        this.cacheElements();
        this.validateElements();
        this.bindMethods();
        this.setupEventListeners();
        this.initializeUI();
    }

    /**
     * Cache DOM elements
     */
    cacheElements() {
        this.elements = {
            uploadBox: document.getElementById('uploadBox'),
            fileInput: document.getElementById('fileInput'),
            fileInfo: document.getElementById('fileInfo'),
            fileName: document.getElementById('fileName'),
            fileSize: document.getElementById('fileSize'),
            fileRows: document.getElementById('fileRows'),
            processBtn: document.getElementById('processBtn'),
            processingLoader: document.getElementById('processingLoader'),
            errorMessage: document.getElementById('errorMessage'),
            resultsSection: document.getElementById('resultsSection'),
            generatePdfBtn: document.getElementById('generatePdfBtn'),
            uploadAnotherBtn: document.getElementById('uploadAnotherBtn'),
            pdfLoader: document.getElementById('pdfLoader'),
            pdfSuccess: document.getElementById('pdfSuccess'),
            downloadLink: document.getElementById('downloadLink')
        };
        
        // Log missing elements for debugging
        const missingElements = Object.keys(this.elements)
            .filter(key => !this.elements[key])
            .map(key => key);
            
        if (missingElements.length > 0) {
            console.warn('Missing elements in upload service:', missingElements);
        }
    }

    /**
     * Validate required elements
     */
    validateElements() {
        const required = ['uploadBox', 'fileInput', 'processBtn'];
        const missing = required.filter(id => !this.elements[id]);
        
        if (missing.length > 0) {
            console.error('Missing required elements:', missing);
            return false;
        }
        return true;
    }

    /**
     * Bind methods to maintain context
     */
    bindMethods() {
        this.boundMethods = {
            handleFile: this.handleFile.bind(this),
            handleDragOver: this.handleDragOver.bind(this),
            handleDragLeave: this.handleDragLeave.bind(this),
            handleDrop: this.handleDrop.bind(this),
            handleFileInput: this.handleFileInput.bind(this),
            processFile: this.processFile.bind(this),
            generatePDF: this.generatePDF.bind(this),
            uploadAnother: this.uploadAnother.bind(this)
        };
    }

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        const { uploadBox, fileInput, processBtn, generatePdfBtn, uploadAnotherBtn } = this.elements;
        
        // Upload box events
        uploadBox.addEventListener('click', () => fileInput.click());
        uploadBox.addEventListener('dragover', this.boundMethods.handleDragOver);
        uploadBox.addEventListener('dragleave', this.boundMethods.handleDragLeave);
        uploadBox.addEventListener('drop', this.boundMethods.handleDrop);
        
        // File input events
        fileInput.addEventListener('change', this.boundMethods.handleFileInput);
        
        // Button events
        processBtn.addEventListener('click', this.boundMethods.processFile);
        if (generatePdfBtn) {
            generatePdfBtn.addEventListener('click', this.boundMethods.generatePDF);
        }
        if (uploadAnotherBtn) {
            uploadAnotherBtn.addEventListener('click', this.boundMethods.uploadAnother);
        }
    }

    /**
     * Initialize UI state
     */
    initializeUI() {
        this.hideError();
        this.hideResults();
        this.setProcessingState(false);
    }

    /**
     * Handle drag over event
     */
    handleDragOver(event) {
        event.preventDefault();
        this.elements.uploadBox.style.borderColor = '#3f51b5';
        this.elements.uploadBox.style.background = '#f0f4ff';
    }

    /**
     * Handle drag leave event
     */
    handleDragLeave(event) {
        event.preventDefault();
        this.elements.uploadBox.style.borderColor = '#e0e0e0';
        this.elements.uploadBox.style.background = '';
    }

    /**
     * Handle drop event
     */
    handleDrop(event) {
        event.preventDefault();
        this.elements.uploadBox.style.borderColor = '#e0e0e0';
        this.elements.uploadBox.style.background = '';
        
        const file = event.dataTransfer.files[0];
        if (file) {
            this.handleFile(file);
        }
    }

    /**
     * Handle file input change
     */
    handleFileInput(event) {
        const file = event.target.files[0];
        if (file) {
            this.handleFile(file);
        }
    }

    /**
     * Handle file processing
     */
    async handleFile(file) {
        try {
            this.hideResults();
            this.hideError();
            
            // Validate file
            const validation = SADPMRUtils.validateFile(file);
            if (!validation.valid) {
                this.showError(validation.error);
                return;
            }
            
            // Upload file
            await this.uploadFile(file);
            
        } catch (error) {
            this.showError('File processing failed: ' + error.message);
            console.error('File processing error:', error);
        }
    }

    /**
     * Upload file to server
     */
    async uploadFile(file) {
        this.setProcessingState(true, 'Uploading file...');
        
        const formData = new FormData();
        formData.append('file', file);
        
        try {
            const data = await SADPMRUtils.safeFetch('/api/upload', {
                method: 'POST',
                body: formData
            });
            
            if (data.success) {
                this.showFileInfo(file, data);
                this.state.uploadedFilePath = data.filepath;
            } else {
                throw new Error(data.error || 'Upload failed');
            }
            
        } catch (error) {
            this.showError('Upload failed: ' + error.message);
            throw error;
        } finally {
            this.setProcessingState(false);
        }
    }

    /**
     * Show file information
     */
    showFileInfo(file, data) {
        const { fileName, fileSize, fileRows, fileInfo, uploadBox } = this.elements;
        
        fileName.textContent = file.name;
        fileSize.textContent = `Size: ${SADPMRUtils.formatFileSize(file.size)}`;
        fileRows.textContent = `Accounts: ${data.row_count}`;
        
        uploadBox.style.display = 'none';
        fileInfo.style.display = 'block';
    }

    /**
     * Process uploaded file
     */
    async processFile() {
        if (!this.state.uploadedFilePath) {
            this.showError('No file uploaded');
            return;
        }
        
        try {
            this.elements.fileInfo.style.display = 'none';
            this.setProcessingState(true, 'Processing your Trial Balance...', 'Mapping accounts to GRAP line items');
            this.hideError();
            
            const data = await SADPMRUtils.safeFetch('/api/process', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    filepath: this.state.uploadedFilePath
                })
            });
            
            if (data.success) {
                this.state.resultsFile = data.results_file;
                this.displayResults(data.summary);
            } else {
                if (data.unmapped_accounts) {
                    this.showError('Unmapped accounts detected. Please review the mapping configuration.');
                    console.error('Unmapped accounts:', data.unmapped_accounts);
                } else {
                    this.showError(data.error || 'Processing failed');
                }
                this.elements.fileInfo.style.display = 'block';
            }
            
        } catch (error) {
            this.showError('Processing failed: ' + error.message);
            this.elements.fileInfo.style.display = 'block';
            console.error('Processing error:', error);
        } finally {
            this.setProcessingState(false);
        }
    }

    /**
     * Display processing results
     */
    displayResults(summary) {
        // Update summary cards
        this.updateElement('totalAssets', SADPMRUtils.formatCurrency(summary.total_assets));
        this.updateElement('totalLiabilities', SADPMRUtils.formatCurrency(summary.total_liabilities));
        this.updateElement('netAssets', SADPMRUtils.formatCurrency(summary.net_assets));
        this.updateElement('surplus', SADPMRUtils.formatCurrency(summary.surplus_deficit));
        
        // Update ratios
        if (summary.ratios) {
            this.updateElement('currentRatio', summary.ratios.current_ratio.toFixed(2));
            this.updateElement('debtToEquity', summary.ratios.debt_to_equity.toFixed(2));
            this.updateElement('operatingMargin', summary.ratios.operating_margin.toFixed(2) + '%');
            this.updateElement('returnOnAssets', summary.ratios.return_on_assets.toFixed(2) + '%');
        }
        
        // Show results section
        this.elements.resultsSection.style.display = 'block';
        SADPMRUtils.scrollToElement(this.elements.resultsSection);
    }

    /**
     * Generate PDF report
     */
    async generatePDF() {
        if (!this.state.resultsFile) {
            this.showError('No results available');
            return;
        }
        
        const { pdfLoader, pdfSuccess } = this.elements;
        
        pdfLoader.style.display = 'block';
        pdfSuccess.style.display = 'none';
        
        try {
            const data = await SADPMRUtils.safeFetch('/api/generate-pdf', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    results_file: this.state.resultsFile
                })
            });
            
            if (data.success) {
                // Update download link
                const downloadLink = this.elements.downloadLink;
                if (downloadLink) {
                    downloadLink.href = data.download_url;
                    downloadLink.download = data.pdf_filename;
                }
                
                pdfSuccess.style.display = 'block';
            } else {
                this.showError('PDF generation failed: ' + (data.error || 'Unknown error'));
            }
            
        } catch (error) {
            this.showError('PDF generation failed: ' + error.message);
            console.error('PDF generation error:', error);
        } finally {
            pdfLoader.style.display = 'none';
        }
    }

    /**
     * Upload another file
     */
    uploadAnother() {
        // Reset state
        this.state.uploadedFilePath = null;
        this.state.resultsFile = null;
        
        // Reset UI
        this.elements.uploadBox.style.display = 'block';
        this.elements.fileInfo.style.display = 'none';
        this.hideResults();
        this.hideError();
        this.elements.fileInput.value = '';
        
        // Hide PDF related elements
        if (this.elements.pdfLoader) {
            this.elements.pdfLoader.style.display = 'none';
        }
        if (this.elements.pdfSuccess) {
            this.elements.pdfSuccess.style.display = 'none';
        }
        
        // Scroll to upload area
        const uploadSection = this.elements.uploadBox.closest('.upload-section');
        if (uploadSection) {
            SADPMRUtils.scrollToElement(uploadSection, { top: 100 });
        } else {
            SADPMRUtils.scrollToElement(this.elements.uploadBox, { top: 100 });
        }
        
        // Focus on upload box for better UX
        this.elements.uploadBox.focus();
        
        // Open file explorer dialog
        setTimeout(() => {
            this.elements.fileInput.click();
        }, 300); // Small delay to ensure UI is updated
    }

    /**
     * Set processing state
     */
    setProcessingState(isProcessing, message = '', subtext = '') {
        this.state.isProcessing = isProcessing;
        const { processingLoader, uploadBox } = this.elements;
        
        if (isProcessing) {
            uploadBox.style.display = 'none';
            processingLoader.style.display = 'block';
            
            if (message) {
                processingLoader.querySelector('p').textContent = message;
            }
            if (subtext) {
                const subtextEl = processingLoader.querySelector('.loader-subtext');
                if (subtextEl) {
                    subtextEl.textContent = subtext;
                }
            }
        } else {
            processingLoader.style.display = 'none';
            if (this.state.uploadedFilePath) {
                this.elements.fileInfo.style.display = 'block';
            } else {
                uploadBox.style.display = 'block';
            }
        }
    }

    /**
     * Update element content safely
     */
    updateElement(id, content) {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = content;
        }
    }

    /**
     * Show error message
     */
    showError(message) {
        SADPMRUtils.showError(message, this.elements.errorMessage);
    }

    /**
     * Hide error message
     */
    hideError() {
        SADPMRUtils.hideError(this.elements.errorMessage);
    }

    /**
     * Hide results section
     */
    hideResults() {
        if (this.elements.resultsSection) {
            this.elements.resultsSection.style.display = 'none';
        }
    }

    /**
     * Get current state
     */
    getState() {
        return { ...this.state };
    }

    /**
     * Cleanup method
     */
    destroy() {
        // Remove event listeners
        const { uploadBox, fileInput, processBtn, generatePdfBtn, uploadAnotherBtn } = this.elements;
        
        uploadBox.removeEventListener('click', () => fileInput.click());
        uploadBox.removeEventListener('dragover', this.boundMethods.handleDragOver);
        uploadBox.removeEventListener('dragleave', this.boundMethods.handleDragLeave);
        uploadBox.removeEventListener('drop', this.boundMethods.handleDrop);
        
        fileInput.removeEventListener('change', this.boundMethods.handleFileInput);
        processBtn.removeEventListener('click', this.boundMethods.processFile);
        
        if (generatePdfBtn) {
            generatePdfBtn.removeEventListener('click', this.boundMethods.generatePDF);
        }
        if (uploadAnotherBtn) {
            uploadAnotherBtn.removeEventListener('click', this.boundMethods.uploadAnother);
        }
        
        // Reset state
        this.state = {
            uploadedFilePath: null,
            resultsFile: null,
            isProcessing: false,
            currentStep: null
        };
        
        console.log('Upload service cleanup complete');
    }
}

// Initialize upload service when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.uploadService = new UploadService();
});

// Handle page unload for cleanup
window.addEventListener('beforeunload', () => {
    if (window.uploadService) {
        window.uploadService.destroy();
    }
});
