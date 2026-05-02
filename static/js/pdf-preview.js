/**
 * SADPMR Financial Reporting System - PDF Preview Module
 * Handles PDF preview, download, and fullscreen functionality
 */

class PdfPreviewModule {
    constructor() {
        this.elements = {};
        this.loadingStates = {
            LOADING: 'loading',
            SUCCESS: 'success',
            ERROR: 'error',
            READY: 'ready'
        };
        this.init();
    }

    /**
     * Initialize PDF preview module
     */
    init() {
        this.cacheElements();
        this.setupEventListeners();
        this.initializePdfPreview();
    }

    /**
     * Cache DOM elements
     */
    cacheElements() {
        this.elements = {
            pdfPreview: document.getElementById('pdfPreview'),
            downloadBtn: document.getElementById('downloadPdf'),
            fullscreenBtn: document.getElementById('fullscreenBtn'),
            generatePdfBtn: document.getElementById('generatePdfBtn'),
            fullscreenCloseBtn: document.getElementById('fullscreenCloseBtn'),
            fullscreenDownloadBtn: document.getElementById('fullscreenDownloadBtn')
        };
    }

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        if (this.elements.downloadBtn) {
            this.elements.downloadBtn.addEventListener('click', () => {
                this.handleDownload();
            });
        }

        if (this.elements.fullscreenBtn) {
            this.elements.fullscreenBtn.addEventListener('click', () => {
                this.handleFullscreen();
            });
        }

        if (this.elements.generatePdfBtn) {
            this.elements.generatePdfBtn.addEventListener('click', () => {
                this.handleGeneratePdf();
            });
        }

        if (this.elements.fullscreenCloseBtn) {
            this.elements.fullscreenCloseBtn.addEventListener('click', () => {
                this.closeFullscreen();
            });
        }

        if (this.elements.fullscreenDownloadBtn) {
            this.elements.fullscreenDownloadBtn.addEventListener('click', () => {
                this.handleFullscreenDownload();
            });
        }

        // Handle escape key for fullscreen
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.closeFullscreen();
            }
        });

        // Handle window resize for responsive PDF
        window.addEventListener('resize', () => {
            this.handleResize();
        });
    }

    /**
     * Initialize PDF preview
     */
    initializePdfPreview() {
        if (this.elements.pdfPreview) {
            // Set initial ready state
            this.showPdfReady();
        }
    }

    /**
     * Load PDF preview
     */
    loadPdfPreview() {
        if (!this.elements.pdfPreview) return;
        
        // For demo purposes, use a sample PDF URL
        // In production, this would be the actual generated PDF URL
        const pdfUrl = '/static/sample-financial-statements.pdf';
        
        try {
            this.elements.pdfPreview.src = pdfUrl;
            this.elements.pdfPreview.onload = () => {
                this.showPdfReady();
            };
            
            this.elements.pdfPreview.onerror = () => {
                this.showPdfError();
            };
            
        } catch (error) {
            this.showPdfError();
        }
    }

    /**
     * Show PDF loading state
     */
    showPdfLoading() {
        if (!this.elements.pdfPreview) return;
        
        const container = this.elements.pdfPreview.parentElement;
        const loadingHtml = `
            <div class="pdf-loading">
                <div class="pdf-loading-spinner"></div>
                <p>Generating PDF preview...</p>
            </div>
        `;
        
        container.innerHTML = loadingHtml;
    }

    /**
     * Show PDF ready state
     */
    showPdfReady() {
        if (!this.elements.pdfPreview) return;
        
        // Ensure the iframe is visible
        this.elements.pdfPreview.classList.remove('element--hidden');
        this.elements.pdfPreview.classList.add('element--visible');
        
        // Add ready class to container
        const container = this.elements.pdfPreview.parentElement;
        container.classList.remove('pdf-loading', 'pdf-error');
        container.classList.add('pdf-ready');
    }

    /**
     * Show PDF error state
     */
    showPdfError() {
        if (!this.elements.pdfPreview) return;
        
        const container = this.elements.pdfPreview.parentElement;
        const errorHtml = `
            <div class="pdf-error">
                <div class="pdf-error-icon">!</div>
                <p>Failed to load PDF preview</p>
                <button class="btn btn-primary" onclick="window.pdfPreviewModule.loadPdfPreview()">
                    Retry
                </button>
            </div>
        `;
        
        container.innerHTML = errorHtml;
    }

    /**
     * Handle download button click
     */
    handleDownload() {
        if (!this.elements.downloadBtn) return;
        
        // Show loading state
        this.elements.downloadBtn.classList.add('download-button--success');
        
        // Create hidden download link
        const link = document.createElement('a');
        link.href = '/static/sample-financial-statements.pdf';
        link.download = 'financial-statements.pdf';
        link.classList.add('report__download-link');
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        // Reset button state after delay
        setTimeout(() => {
            this.elements.downloadBtn.classList.remove('download-button--success');
        }, 2000);
    }

    /**
     * Handle fullscreen button click
     */
    handleFullscreen() {
        const fullscreenContainer = document.getElementById('pdfFullscreen');
        if (fullscreenContainer) {
            fullscreenContainer.classList.remove('element--hidden');
            fullscreenContainer.classList.add('element--visible');
            document.body.classList.add('body--overflow-hidden');
            document.body.classList.remove('body--overflow-auto');
            
            // Load PDF in fullscreen if not already loaded
            const fullscreenPdf = document.getElementById('fullscreenPdf');
            if (fullscreenPdf && !fullscreenPdf.src) {
                fullscreenPdf.src = '/static/sample-financial-statements.pdf';
            }
        }
    }

    /**
     * Close fullscreen view
     */
    closeFullscreen() {
        const fullscreenContainer = document.getElementById('pdfFullscreen');
        if (fullscreenContainer) {
            fullscreenContainer.classList.add('element--hidden');
            fullscreenContainer.classList.remove('element--visible');
            document.body.classList.remove('body--overflow-hidden');
            document.body.classList.add('body--overflow-auto');
        }
    }

    /**
     * Handle fullscreen download
     */
    handleFullscreenDownload() {
        this.handleDownload();
    }

    /**
     * Handle generate PDF button click
     */
    handleGeneratePdf() {
        if (!this.elements.generatePdfBtn) return;
        
        // Show loading state
        this.elements.generatePdfBtn.disabled = true;
        this.elements.generatePdfBtn.textContent = 'Generating...';
        
        // Simulate PDF generation
        setTimeout(() => {
            this.elements.generatePdfBtn.disabled = false;
            this.elements.generatePdfBtn.textContent = 'Generate PDF';
            
            // Load the preview
            this.loadPdfPreview();
            
            // Show success message
            this.showSuccessMessage('PDF generated successfully!');
        }, 2000);
    }

    /**
     * Handle window resize for responsive PDF
     */
    handleResize() {
        if (!this.elements.pdfPreview) return;
        
        const container = this.elements.pdfPreview.parentElement;
        const containerWidth = container.clientWidth;
        
        // Adjust PDF scale based on container width
        if (containerWidth < 768) {
            this.elements.pdfPreview.classList.add('report__pdf-viewer--small');
            this.elements.pdfPreview.classList.remove('report__pdf-viewer--normal');
        } else {
            this.elements.pdfPreview.classList.add('report__pdf-viewer--normal');
            this.elements.pdfPreview.classList.remove('report__pdf-viewer--small');
        }
    }

    /**
     * Show success message
     */
    showSuccessMessage(message) {
        // Create success alert
        const alert = document.createElement('div');
        alert.className = 'alert alert-success';
        alert.textContent = message;
        
        // Add to page
        const container = document.querySelector('.results-section');
        if (container) {
            container.insertBefore(alert, container.firstChild);
            
            // Auto-hide after 3 seconds
            setTimeout(() => {
                alert.classList.add('auth__alert--animated');
                alert.classList.add('auth__alert--dismissing');
                setTimeout(() => alert.remove(), 500);
            }, 3000);
        }
    }

    /**
     * Cleanup method
     */
    destroy() {
        // Remove event listeners
        window.removeEventListener('resize', this.handleResize);
        document.removeEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.closeFullscreen();
            }
        });
    }
}

// Initialize PDF preview module when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.pdfPreviewModule = new PdfPreviewModule();
});

// Handle page unload for cleanup
window.addEventListener('beforeunload', () => {
    if (window.pdfPreviewModule) {
        window.pdfPreviewModule.destroy();
    }
});
