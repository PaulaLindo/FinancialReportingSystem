/**
 * Submission History Manager
 * Handles loading and displaying user's own trial balance submissions
 */

// Status messages for display formatting
const StatusMessages = {
    get_message: function(status) {
        const messages = {
            'uploaded': 'Uploaded',           // Trial balance uploaded
            'processing': 'Processing',      // Being processed/mapped
            'mapped': 'Pending Review',      // Accounts mapped - pending finance manager approval
            'approved': 'Approved',          // Approved by finance manager
            'rejected': 'Rejected',          // Rejected by finance manager
            'archived': 'Archived',          // Archived submission
            'draft': 'Draft',
            'pending': 'Pending Review'      // Pending submission
        };
        return messages[status] || status;
    }
};

class SubmissionHistoryManager {
    constructor() {
        this.submissions = [];
        this.filteredSubmissions = [];
        this.currentPage = 1;
        this.perPage = 10;
        this.totalPages = 1;
        this.selectedSubmission = null;
        
        this.state = {
            loading: false,
            error: null
        };
        
        this.elements = {
            loadingState: document.getElementById('loadingState'),
            emptyState: document.getElementById('emptyState'),
            submissionsList: document.getElementById('submissionsList'),
            paginationControls: document.getElementById('paginationControls'),
            searchInput: document.getElementById('searchInput'),
            statusFilter: document.getElementById('statusFilter'),
            dateFilter: document.getElementById('dateFilter'),
            prevPageBtn: document.getElementById('prevPageBtn'),
            nextPageBtn: document.getElementById('nextPageBtn'),
            pageInfo: document.getElementById('pageInfo'),
            modal: document.getElementById('submissionDetailsModal'),
            modalCloseBtn: document.getElementById('modalCloseBtn')
        };
        
        this.init();
    }
    
    init() {
        this.bindEvents();
        this.loadSubmissions();
    }
    
    bindEvents() {
        // Search and filter events
        if (this.elements.searchInput) {
            this.elements.searchInput.addEventListener('input', this.debounce(() => this.applyFilters(), 300));
        }
        
        if (this.elements.statusFilter) {
            this.elements.statusFilter.addEventListener('change', () => this.applyFilters());
        }
        
        if (this.elements.dateFilter) {
            this.elements.dateFilter.addEventListener('change', () => this.applyFilters());
        }
        
        // Pagination events
        if (this.elements.prevPageBtn) {
            this.elements.prevPageBtn.addEventListener('click', () => this.goToPage(this.currentPage - 1));
        }
        
        if (this.elements.nextPageBtn) {
            this.elements.nextPageBtn.addEventListener('click', () => this.goToPage(this.currentPage + 1));
        }
        
        // Modal events
        if (this.elements.modalCloseBtn) {
            this.elements.modalCloseBtn.addEventListener('click', () => this.closeModal());
        }
        
        // Close modal when clicking on overlay
        const overlay = this.elements.modal?.querySelector('.submission-details-overlay');
        if (overlay) {
            overlay.addEventListener('click', (e) => {
                if (e.target === e.currentTarget) {
                    this.closeModal();
                }
            });
        }
        
        // View details buttons (event delegation)
        if (this.elements.submissionsList) {
            this.elements.submissionsList.addEventListener('click', (e) => {
                const viewBtn = e.target.closest('.btn-view-details');
                if (viewBtn) {
                    const submissionItem = viewBtn.closest('.submission-item');
                    const submissionId = submissionItem?.dataset.submissionId;
                    if (submissionId) {
                        this.showSubmissionDetails(submissionId);
                    }
                }
            });
        }
    }
    
    async loadSubmissions(page = 1) {
        this.showLoading(true);
        this.currentPage = page;
        
        try {
            const url = `/api/submissions/user?page=${page}&per_page=${this.perPage}`;
            const response = await SADPMRUtils.safeFetch(url);
            
            console.log('🔍 Debug - API Response:', response);
            
            if (response.success) {
                this.submissions = response.submissions || [];
                console.log('🔍 Debug - Submissions loaded:', this.submissions.length, this.submissions);
                this.updateSubmissionStats();
                this.applyFilters();
                this.showLoading(false);
                this.hideError();
            } else {
                throw new Error(response.error || 'Failed to load submissions');
            }
        } catch (error) {
            console.error('🔍 Debug - Error loading submissions:', error);
            this.showLoading(false);
            this.showError(error.message);
        }
    }
    
    updateSubmissionStats() {
        const stats = {
            total: this.submissions.length,
            pending: this.submissions.filter(s => s.status === 'pending').length,
            mapped: this.submissions.filter(s => s.status === 'mapped').length,
            processing: this.submissions.filter(s => s.status === 'processing').length,
            uploaded: this.submissions.filter(s => s.status === 'uploaded').length,
            approved: this.submissions.filter(s => s.status === 'approved').length,
            rejected: this.submissions.filter(s => s.status === 'rejected').length
        };
        
        // Update DOM
        const totalEl = document.getElementById('totalSubmissionsCount');
        const pendingEl = document.getElementById('pendingSubmissionsCount');
        const approvedEl = document.getElementById('approvedSubmissionsCount');
        const rejectedEl = document.getElementById('rejectedSubmissionsCount');
        
        if (totalEl) totalEl.textContent = stats.total;
        if (pendingEl) pendingEl.textContent = stats.pending + stats.mapped + stats.processing + stats.uploaded; // All submissions needing attention
        if (approvedEl) approvedEl.textContent = stats.approved;
        if (rejectedEl) rejectedEl.textContent = stats.rejected;
    }
    
    applyFilters() {
        console.log('🔍 Debug - About to apply filters:', {
            searchValue: this.elements.searchInput?.value,
            statusFilter: this.elements.statusFilter?.value,
            dateFilter: this.elements.dateFilter?.value
        });
        
        this.filteredSubmissions = this.submissions.filter(submission => {
            // Search filter
            const searchTerm = this.elements.searchInput?.value.toLowerCase() || '';
            const filename = submission.filepath ? submission.filepath.split('\\').pop().toLowerCase() : '';
            const matchesSearch = filename.includes(searchTerm);
            
            // Status filter
            const statusFilter = this.elements.statusFilter?.value || 'all';
            const matchesStatus = statusFilter === 'all' || submission.status === statusFilter;
            
            // Date filter
            const dateFilter = this.elements.dateFilter?.value || 'all';
            const submissionDate = new Date(submission.submission_timestamp);
            const matchesDate = this.matchesDateFilter(submissionDate, dateFilter);
            
            return matchesSearch && matchesStatus && matchesDate;
        });
        
        console.log('🔍 Debug - After filtering:', {
            originalCount: this.submissions.length,
            filteredCount: this.filteredSubmissions.length,
            firstFiltered: this.filteredSubmissions[0]
        });
        
        this.renderSubmissions();
        this.updatePaginationControls();
    }
    
    matchesDateFilter(submissionDate, filter) {
        const now = new Date();
        const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
        
        switch (filter) {
            case 'today':
                return submissionDate >= today;
            case 'week':
                const weekAgo = new Date(today);
                weekAgo.setDate(weekAgo.getDate() - 7);
                return submissionDate >= weekAgo;
            case 'month':
                const monthAgo = new Date(today);
                monthAgo.setMonth(monthAgo.getMonth() - 1);
                return submissionDate >= monthAgo;
            default:
                return true;
        }
    }
    
    renderSubmissions() {
        if (this.filteredSubmissions.length === 0) {
            console.log('🔍 Debug - Showing empty state because no filtered submissions');
            this.showEmptyState();
            return;
        }
        
        this.showSubmissionsList();
        
        // Clear existing submissions
        this.elements.submissionsList.innerHTML = '';
        
        // Add submission items
        this.filteredSubmissions.forEach(submission => {
            const submissionElement = this.createSubmissionElement(submission);
            this.elements.submissionsList.appendChild(submissionElement);
        });
    }
    
    createSubmissionElement(submission) {
        const template = document.getElementById('submissionItemTemplate');
        const clone = template.content.cloneNode(true);
        
        // Set submission data
        const submissionItem = clone.querySelector('.submission-item');
        submissionItem.dataset.submissionId = submission.session_id;
        
        // Set icon (always trial balance for submissions)
        const trialBalanceIcon = clone.querySelector('.icon-trial-balance');
        const pdfReportIcon = clone.querySelector('.icon-pdf-report');
        
        trialBalanceIcon.classList.remove('element--hidden');
        trialBalanceIcon.classList.add('element--visible');
        pdfReportIcon.classList.add('element--hidden');
        pdfReportIcon.classList.remove('element--visible');
        
        // Set submission info
        const submissionName = clone.querySelector('.submission-name');
        const submissionDate = clone.querySelector('.submission-date');
        const submissionStatus = clone.querySelector('.submission-status');
        const submissionAccounts = clone.querySelector('.submission-accounts');
        
        const filename = submission.filepath ? submission.filepath.split('\\').pop() : `submission_${submission.session_id}.xlsx`;
        submissionName.textContent = filename;
        submissionName.title = filename;
        
        submissionDate.textContent = this.formatDate(submission.submission_timestamp);
        submissionStatus.textContent = this.formatStatus(submission.status);
        submissionAccounts.textContent = `${submission.mapped_accounts_count || 0} accounts mapped`;
        
        // Set status class
        submissionStatus.className = `submission-status status-${submission.status}`;
        
        return clone;
    }
    
    showSubmissionDetails(submissionId) {
        const submission = this.submissions.find(s => s.session_id === submissionId);
        if (!submission) return;
        
        this.selectedSubmission = submission;
        
        // Update modal content
        const filename = submission.filepath ? submission.filepath.split('\\').pop() : `submission_${submission.session_id}.xlsx`;
        
        document.getElementById('detailFilename').textContent = filename;
        document.getElementById('detailStatus').textContent = this.formatStatus(submission.status);
        document.getElementById('detailSubmissionDate').textContent = this.formatDate(submission.submission_timestamp);
        document.getElementById('detailMappedAccounts').textContent = submission.mapped_accounts_count || 0;
        document.getElementById('detailReviewNotes').textContent = submission.review_notes || 'No review notes';
        document.getElementById('detailLocked').textContent = submission.locked ? 'Yes' : 'No';
        
        // Set status class
        const statusEl = document.getElementById('detailStatus');
        statusEl.className = `submission-status status-${submission.status}`;
        
        // Update modal button
        const modalViewBtn = document.getElementById('modalViewBtn');
        if (modalViewBtn) {
            modalViewBtn.onclick = () => {
                window.location.href = `/submission/${submission.session_id}`;
            };
        }
        
        this.showModal();
    }
    
    goToPage(page) {
        if (page < 1 || page > this.totalPages) return;
        this.loadSubmissions(page);
    }
    
    updatePaginationControls() {
        const totalItems = this.filteredSubmissions.length;
        this.totalPages = Math.ceil(totalItems / this.perPage) || 1;
        
        if (this.elements.prevPageBtn) {
            this.elements.prevPageBtn.disabled = this.currentPage <= 1;
        }
        
        if (this.elements.nextPageBtn) {
            this.elements.nextPageBtn.disabled = this.currentPage >= this.totalPages;
        }
        
        if (this.elements.pageInfo) {
            this.elements.pageInfo.textContent = `Page ${this.currentPage} of ${this.totalPages}`;
        }
        
        // Show/hide pagination controls
        if (this.totalPages > 1) {
            this.elements.paginationControls.classList.remove('element--hidden');
            this.elements.paginationControls.classList.add('element--visible');
        } else {
            this.elements.paginationControls.classList.add('element--hidden');
            this.elements.paginationControls.classList.remove('element--visible');
        }
    }
    
    // UI State Management
    showLoading(show) {
        if (this.elements.loadingState) {
            if (show) {
                this.elements.loadingState.classList.remove('element--hidden');
                this.elements.loadingState.classList.add('element--visible');
            } else {
                this.elements.loadingState.classList.add('element--hidden');
                this.elements.loadingState.classList.remove('element--visible');
            }
        }
        
        this.state.loading = show;
    }
    
    showEmptyState() {
        if (this.elements.submissionsList) {
            this.elements.submissionsList.classList.add('element--hidden');
            this.elements.submissionsList.classList.remove('element--visible');
        }
        
        if (this.elements.emptyState) {
            this.elements.emptyState.classList.remove('element--hidden');
            this.elements.emptyState.classList.add('element--visible');
        }
        
        if (this.elements.paginationControls) {
            this.elements.paginationControls.classList.add('element--hidden');
            this.elements.paginationControls.classList.remove('element--visible');
        }
    }
    
    showSubmissionsList() {
        if (this.elements.emptyState) {
            this.elements.emptyState.classList.add('element--hidden');
            this.elements.emptyState.classList.remove('element--visible');
        }
        
        if (this.elements.submissionsList) {
            this.elements.submissionsList.classList.remove('element--hidden');
            this.elements.submissionsList.classList.add('element--visible');
        }
    }
    
    showError(message) {
        this.state.error = message;
        if (typeof SADPMRUtils !== 'undefined') {
            SADPMRUtils.showError(message);
        }
    }
    
    hideError() {
        this.state.error = null;
    }
    
    showModal() {
        if (this.elements.modal) {
            this.elements.modal.classList.remove('element--hidden');
            this.elements.modal.classList.add('element--visible');
        }
    }
    
    closeModal() {
        if (this.elements.modal) {
            this.elements.modal.classList.add('element--hidden');
            this.elements.modal.classList.remove('element--visible');
        }
        this.selectedSubmission = null;
    }
    
    // Utility Functions
    formatDate(dateString) {
        return SADPMRUtils.formatDate(dateString);
    }
    
    formatStatus(status) {
        return StatusMessages.get_message(status);
    }
    
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
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.submissionHistoryManager = new SubmissionHistoryManager();
});
