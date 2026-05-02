/**
 * SADPMR File Management System
 * Handles file listing, filtering, searching, and operations
 */

class FileManager {
    constructor() {
        this.files = [];
        this.filteredFiles = [];
        this.currentPage = 1;
        this.perPage = 20;
        this.totalPages = 1;
        this.totalFiles = 0;
        this.searchQuery = '';
        this.filters = {
            fileType: 'all',
            dateRange: 'all'
        };
        this.selectedFile = null;
        
        // Detect mobile for pagination
        this.isMobile = /Mobile|Android|iPhone|iPad/.test(navigator.userAgent);
        if (this.isMobile) {
            this.perPage = 10;
        }
        
        this.init();
    }

    init() {
        this.bindEvents();
        this.loadFiles();
    }

    bindEvents() {
        // Search input handler
        const searchInput = document.getElementById('searchInput');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                this.searchQuery = e.target.value.toLowerCase().trim();
                this.applyFilters();
            });
        }

        // Filter change handlers
        document.querySelectorAll('[data-filter]').forEach(filter => {
            filter.addEventListener('change', (e) => {
                this.filters[e.target.dataset.filter] = e.target.value;
                this.applyFilters();
            });
        });

        // Action buttons
        document.querySelectorAll('[data-action]').forEach(button => {
            button.addEventListener('click', (e) => {
                const action = e.target.dataset.action;
                switch (action) {
                    case 'refresh-files':
                        this.loadFiles(1);
                        break;
                    case 'download-all':
                        this.downloadAllFiles();
                        break;
                }
            });
        });

        // Retry button
        document.getElementById('retryLoadBtn')?.addEventListener('click', () => {
            this.loadFiles(1);
        });

        // Pagination buttons
        document.getElementById('prevPageBtn')?.addEventListener('click', () => {
            if (this.currentPage > 1) {
                this.loadFiles(this.currentPage - 1);
            }
        });

        document.getElementById('nextPageBtn')?.addEventListener('click', () => {
            if (this.currentPage < this.totalPages) {
                this.loadFiles(this.currentPage + 1);
            }
        });

        // Modal events using data-action attributes
        document.querySelectorAll('[data-action="close-file-details-modal"]').forEach(element => {
            element.addEventListener('click', () => {
                this.closeModal();
            });
        });

        // Close modal when clicking on overlay background
        document.querySelector('#fileDetailsModal .file-details-overlay').addEventListener('click', (e) => {
            if (e.target === e.currentTarget) {
                this.closeModal();
            }
        });

        document.getElementById('modalDownloadBtn').addEventListener('click', () => {
            if (this.selectedFile) {
                this.downloadFile(this.selectedFile);
            }
        });

        document.getElementById('modalDeleteBtn').addEventListener('click', () => {
            if (this.selectedFile) {
                this.deleteFile(this.selectedFile);
            }
        });
    }

    async loadFiles(page = 1) {
        this.showLoading(true);
        this.currentPage = page;
        
        try {
            const response = await SADPMRUtils.safeFetch(`/api/submissions/user?page=${page}&per_page=${this.perPage}`);
            
            if (response.success) {
                // Transform submission data to file format
                this.files = response.submissions.map(submission => ({
                    id: submission.session_id,
                    filename: submission.filepath ? submission.filepath.split('\\').pop() : `submission_${submission.session_id}.xlsx`,
                    original_filename: submission.filepath ? submission.filepath.split('\\').pop() : `submission_${submission.session_id}.xlsx`,
                    file_size: 0, // Not available in submission data
                    upload_date: submission.submission_timestamp,
                    status: submission.status,
                    type: 'trial_balance',
                    user_id: submission.user_id,
                    username: submission.username,
                    full_name: submission.full_name,
                    filepath: submission.filepath,
                    mapped_accounts_count: submission.mapped_accounts_count,
                    locked: submission.locked,
                    review_notes: submission.review_notes
                }));
                
                this.totalFiles = this.files.length;
                this.totalPages = 1;  // API doesn't support pagination yet
                this.updateSummaryStats({ total_files: this.files.length });
                this.applyFilters();
                this.updatePaginationControls();
                this.showLoading(false);
                this.hideError();
            } else {
                throw new Error(response.error || 'Failed to load submissions');
            }
        } catch (error) {
            this.showLoading(false);
            this.showError(error.message);
        }
    }

    applyFilters() {
        this.filteredFiles = this.files.filter(file => {
            // Search filter
            if (this.searchQuery) {
                const searchableText = [
                    file.filename || '',
                    file.original_filename || '',
                    file.file_size || '',
                    file.status || ''
                ].join(' ').toLowerCase();
                
                if (!searchableText.includes(this.searchQuery)) {
                    return false;
                }
            }

            // File type filter
            if (this.filters.fileType !== 'all' && file.type !== this.filters.fileType) {
                return false;
            }
            
            // Date range filter
            if (this.filters.dateRange !== 'all') {
                const fileDate = new Date(file.upload_date);
                const now = new Date();
                
                switch (this.filters.dateRange) {
                    case 'today':
                        if (!this.isToday(file.upload_date)) return false;
                        break;
                    case 'week':
                        const weekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
                        if (fileDate < weekAgo) return false;
                        break;
                    case 'month':
                        const monthAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
                        if (fileDate < monthAgo) return false;
                        break;
                    case 'year':
                        const yearAgo = new Date(now.getTime() - 365 * 24 * 60 * 60 * 1000);
                        if (fileDate < yearAgo) return false;
                        break;
                }
            }
            
            return true;
        });
        
        this.renderFiles();
    }

    isToday(dateString) {
        const date = new Date(dateString);
        const today = new Date();
        return date.toDateString() === today.toDateString();
    }

    hasActiveFilters() {
        // Check if any filters are active (search, file type, date range)
        return this.searchQuery !== '' || 
               this.filters.fileType !== 'all' || 
               this.filters.dateRange !== 'all';
    }

    renderFiles() {
        const filesList = document.getElementById('filesList');
        const emptyState = document.getElementById('emptyState');
        
        if (this.filteredFiles.length === 0) {
            filesList.classList.add('element--hidden');
            filesList.classList.remove('element--visible');
            emptyState.classList.remove('element--hidden');
            emptyState.classList.add('element--visible');
            return;
        }
        
        filesList.classList.remove('element--hidden');
        filesList.classList.add('element--visible');
        emptyState.classList.add('element--hidden');
        emptyState.classList.remove('element--visible');
        
        // Clear existing files
        filesList.innerHTML = '';
        
        // Add file items
        this.filteredFiles.forEach(file => {
            const fileElement = this.createFileElement(file);
            filesList.appendChild(fileElement);
        });
    }

    createFileElement(file) {
        const template = document.getElementById('fileItemTemplate');
        const clone = template.content.cloneNode(true);
        
        // Set file data
        const fileItem = clone.querySelector('.file-item');
        fileItem.setAttribute('data-file-id', file.id);
        fileItem.setAttribute('data-file-type', file.type);
        
        // Set icon
        const trialBalanceIcon = clone.querySelector('.icon-trial-balance');
        const pdfReportIcon = clone.querySelector('.icon-pdf-report');
        
        if (file.type === 'trial_balance') {
            trialBalanceIcon.classList.remove('element--hidden');
            trialBalanceIcon.classList.add('element--visible');
            pdfReportIcon.classList.add('element--hidden');
            pdfReportIcon.classList.remove('element--visible');
        } else {
            trialBalanceIcon.classList.add('element--hidden');
            trialBalanceIcon.classList.remove('element--visible');
            pdfReportIcon.classList.remove('element--hidden');
            pdfReportIcon.classList.add('element--visible');
        }
        
        // Set file info
        const fileName = clone.querySelector('.file-name');
        const fileSize = clone.querySelector('.file-size');
        const fileDate = clone.querySelector('.file-date');
        const fileStatus = clone.querySelector('.file-status');
        
        fileName.textContent = file.original_filename || file.filename;
        fileName.title = file.original_filename || file.filename;
        
        fileSize.textContent = this.formatFileSize(file.file_size);
        fileDate.textContent = this.formatDate(file.upload_date);
        fileStatus.textContent = this.formatStatus(file.status);
        
        // Set status class
        fileStatus.className = `file-status status-${file.status}`;
        
        // Add event listeners
        const downloadBtn = clone.querySelector('.btn-download-file');
        const viewBtn = clone.querySelector('.btn-view-details');
        const deleteBtn = clone.querySelector('.btn-delete-file');
        
        downloadBtn.addEventListener('click', () => this.downloadFile(file));
        viewBtn.addEventListener('click', () => this.showFileDetails(file));
        deleteBtn.addEventListener('click', () => this.deleteFile(file));
        
        return clone;
    }

    async downloadFile(file) {
        try {
            let downloadUrl;
            
            if (file.type === 'trial_balance') {
                const response = await SADPMRUtils.safeFetch(`/api/download-trial-balance/${file.id}?user_id=demo_user`);
                
                if (!response.success) {
                    throw new Error(response.error);
                }
                
                downloadUrl = response.download_url;
            } else if (file.type === 'pdf_report') {
                const response = await SADPMRUtils.safeFetch(`/api/download-pdf-report/${file.id}?user_id=demo_user`);
                
                if (!response.success) {
                    throw new Error(response.error);
                }
                
                downloadUrl = response.download_url;
            }
            
            // Trigger download
            const link = document.createElement('a');
            link.href = downloadUrl;
            link.download = file.original_filename || file.filename;
            link.classList.add('element--hidden');
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            
        } catch (error) {
            alert('Download failed. Please try again.');
            SADPMRUtils.showError(`Failed to download file: ${error.message}`);
        }
    }

    showFileDetails(file) {
        this.selectedFile = file;
        
        // Update modal content
        document.getElementById('detailFilename').textContent = file.filename;
        document.getElementById('detailOriginalFilename').textContent = file.original_filename || 'N/A';
        document.getElementById('detailFileType').textContent = this.formatFileType(file.type);
        document.getElementById('detailFileSize').textContent = this.formatFileSize(file.file_size);
        document.getElementById('detailUploadDate').textContent = this.formatDate(file.upload_date);
        document.getElementById('detailStatus').textContent = this.formatStatus(file.status);
        
        // Show/hide trial balance info
        const trialBalanceRow = document.getElementById('detailTrialBalanceRow');
        if (file.type === 'pdf_report' && file.trial_balance_id) {
            trialBalanceRow.classList.remove('element--hidden');
            trialBalanceRow.classList.add('element--visible');
            // Find associated trial balance
            const trialBalance = this.files.find(f => f.id === file.trial_balance_id);
            if (trialBalance) {
                document.getElementById('detailTrialBalance').textContent = trialBalance.original_filename || trialBalance.filename;
            }
        } else {
            trialBalanceRow.classList.add('element--hidden');
            trialBalanceRow.classList.remove('element--visible');
        }
        
        // Show modal
        const modal = document.getElementById('fileDetailsModal');
        modal.classList.remove('element--hidden');
        modal.classList.add('element--visible');
        
        // Auto-scroll to modal
        setTimeout(() => {
            modal.scrollIntoView({
                behavior: 'smooth',
                block: 'center',
                inline: 'center'
            });
        }, 100);
    }

    closeModal() {
        const modal = document.getElementById('fileDetailsModal');
        modal.classList.add('element--hidden');
        modal.classList.remove('element--visible');
        this.selectedFile = null;
    }

    async deleteFile(file) {
        if (!confirm(`Are you sure you want to delete "${file.original_filename || file.filename}"? This action cannot be undone.`)) {
            return;
        }
        
        try {
            let deleteUrl;
            
            if (file.type === 'trial_balance') {
                deleteUrl = `/api/delete-trial-balance/${file.id}?user_id=demo_user`;
            } else if (file.type === 'pdf_report') {
                deleteUrl = `/api/delete-pdf-report/${file.id}?user_id=demo_user`;
            }
            
            const response = await SADPMRUtils.safeFetch(deleteUrl, { method: 'DELETE' });
            
            if (response.success) {
                // Remove from local array
                this.files = this.files.filter(f => f.id !== file.id);
                this.applyFilters();
                this.closeModal();
                SADPMRUtils.showSuccess('File deleted successfully');
            } else {
                throw new Error(response.error);
            }
        } catch (error) {
            SADPMRUtils.showError(`Failed to delete file: ${error.message}`);
        }
    }

    async downloadAllFiles() {
        if (this.filteredFiles.length === 0) {
            SADPMRUtils.showError('No files to download');
            return;
        }
        
        if (!confirm(`Download all ${this.filteredFiles.length} files?`)) {
            return;
        }
        
        try {
            // Download files one by one
            for (const file of this.filteredFiles) {
                await this.downloadFile(file);
                // Small delay between downloads
                await new Promise(resolve => setTimeout(resolve, 500));
            }
            
            SADPMRUtils.showSuccess(`Downloaded ${this.filteredFiles.length} files successfully`);
        } catch (error) {
            SADPMRUtils.showError(`Failed to download some files: ${error.message}`);
        }
    }

    updateSummaryStats(summary) {
        document.getElementById('totalFilesCount').textContent = summary.total_files || 0;
        document.getElementById('trialBalancesCount').textContent = summary.trial_balances || 0;
        document.getElementById('pdfReportsCount').textContent = summary.pdf_reports || 0;
        document.getElementById('storageUsed').textContent = this.formatFileSize(summary.total_size_mb * 1024 * 1024) + ' MB';
    }

    formatFileSize(bytes) {
        if (!bytes) return '0 B';
        
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(1024));
        const size = (bytes / Math.pow(1024, i)).toFixed(1);
        
        return `${size} ${sizes[i]}`;
    }

    formatDate(dateString) {
        return SADPMRUtils.formatDate(dateString);
    }

    formatStatus(status) {
        const statusMap = {
            'uploaded': '✓ Uploaded',
            'completed': '✓ Complete',
            'processing': '⏳ Processing',
            'pending': '⏸ Pending',
            'failed': '✗ Failed'
        };
        
        return statusMap[status] || status;
    }

    formatFileType(type) {
        const typeMap = {
            'trial_balance': 'Trial Balance',
            'pdf_report': 'PDF Report'
        };
        
        return typeMap[type] || type;
    }

    showLoading(show) {
        const loadingElement = document.getElementById('filesLoading');
        const filesList = document.getElementById('filesList');
        
        if (show) {
            loadingElement.classList.remove('element--hidden');
            loadingElement.classList.add('element--visible');
            filesList.classList.add('element--hidden');
            filesList.classList.remove('element--visible');
        } else {
            loadingElement.classList.add('element--hidden');
            loadingElement.classList.remove('element--visible');
            filesList.classList.remove('element--hidden');
            filesList.classList.add('element--visible');
        }
    }

    showError(message) {
        const errorElement = document.getElementById('filesError');
        const filesList = document.getElementById('filesList');
        const errorMessage = document.getElementById('errorMessage');
        
        errorElement.classList.remove('element--hidden');
        errorElement.classList.add('element--visible');
        filesList.classList.add('element--hidden');
        filesList.classList.remove('element--visible');
        errorMessage.textContent = message;
    }

    hideError() {
        const errorElement = document.getElementById('filesError');
        const filesList = document.getElementById('filesList');
        
        errorElement.classList.add('element--hidden');
        errorElement.classList.remove('element--visible');
        filesList.classList.remove('element--hidden');
        filesList.classList.add('element--visible');
    }

    updatePaginationControls() {
        const paginationControls = document.getElementById('paginationControls');
        const prevBtn = document.getElementById('prevPageBtn');
        const nextBtn = document.getElementById('nextPageBtn');
        const pageNumbers = document.getElementById('pageNumbers');
        const paginationInfo = document.getElementById('paginationInfo');

        if (this.totalPages > 1) {
            paginationControls.classList.remove('element--hidden');
            paginationControls.classList.add('element--visible');
            
            // Update button states
            prevBtn.disabled = this.currentPage === 1;
            nextBtn.disabled = this.currentPage === this.totalPages;
            
            // Update pagination info
            const startItem = (this.currentPage - 1) * this.perPage + 1;
            const endItem = Math.min(this.currentPage * this.perPage, this.totalFiles);
            paginationInfo.textContent = `Showing ${startItem}-${endItem} of ${this.totalFiles} files`;
            
            // Generate page numbers
            pageNumbers.innerHTML = '';
            const maxPages = Math.min(5, this.totalPages);
            let startPage = Math.max(1, this.currentPage - 2);
            let endPage = Math.min(this.totalPages, startPage + maxPages - 1);
            
            if (startPage > 1) {
                this.addPageNumber(1);
                if (startPage > 2) {
                    this.addPageNumber('...');
                }
            }
            
            for (let i = startPage; i <= endPage; i++) {
                this.addPageNumber(i);
            }
            
            if (endPage < this.totalPages) {
                if (endPage < this.totalPages - 1) {
                    this.addPageNumber('...');
                }
                this.addPageNumber(this.totalPages);
            }
            
            // Add click handlers to page numbers
            pageNumbers.querySelectorAll('.page-number').forEach(btn => {
                const pageNum = parseInt(btn.textContent);
                if (!isNaN(pageNum)) {
                    btn.addEventListener('click', () => {
                        this.loadFiles(pageNum);
                    });
                }
            });
        } else {
            paginationControls.classList.add('element--hidden');
            paginationControls.classList.remove('element--visible');
        }
    }

    addPageNumber(pageNum) {
        const pageNumbers = document.getElementById('pageNumbers');
        const pageBtn = document.createElement('button');
        pageBtn.className = 'page-number';
        if (pageNum === this.currentPage) {
            pageBtn.classList.add('active');
        }
        pageBtn.textContent = pageNum;
        pageNumbers.appendChild(pageBtn);
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new FileManager();
});
