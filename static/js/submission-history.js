/**
 * Clerk submission history — own submitted documents across all types.
 */

const REJECTED_HISTORY_STATUSES = new Set([
    'rejected',
    'rejected_by_manager',
    'rejected_by_cfo',
]);

const DOCUMENT_TYPE_LABELS = {
    balance_sheet: 'Balance sheet',
    income_statement: 'Income statement',
    budget_report: 'Budget report',
};

function normalizeDocumentType(documentType) {
    const raw = String(documentType || 'balance_sheet').trim().toLowerCase();
    return raw.replace(/-/g, '_');
}

function isRejectedHistoryStatus(status) {
    return REJECTED_HISTORY_STATUSES.has(String(status || '').toLowerCase());
}

const STATEMENT_VIEW_STATUSES = new Set([
    'pending_review',
    'pending_cfo',
    'approved_by_manager',
    'rejected_by_manager',
    'submitted',
    'approved',
    'rejected',
    'rejected_by_cfo',
    'finalized',
]);

const DRAFT_HISTORY_STATUSES = new Set([
    'uploaded',
    'processing',
    'mapped',
    'draft',
    'in_progress',
    'pending_mapping',
    'open',
    'closed',
]);

function canViewStatementInHistory(submission) {
    const status = String(submission?.status || '').toLowerCase();
    if (DRAFT_HISTORY_STATUSES.has(status)) return false;
    if (STATEMENT_VIEW_STATUSES.has(status) || isRejectedHistoryStatus(status)) return true;
    return !!(submission?.submitted_at || submission?.submission_timestamp);
}

function isClosedHistoryStatus(status) {
    return String(status || '').toLowerCase() === 'closed';
}

const StatusMessages = {
    get_message(status) {
        const messages = {
            uploaded: 'Pending review',
            processing: 'Processing',
            mapped: 'Pending review',
            approved: 'Approved',
            rejected: 'Rejected',
            rejected_by_manager: 'Rejected by manager',
            rejected_by_cfo: 'Rejected by CFO',
            approved_by_manager: 'Awaiting CFO',
            archived: 'Archived',
            draft: 'Draft',
            pending: 'Pending review',
            pending_review: 'In review',
            pending_cfo: 'Awaiting CFO',
            submitted: 'In review',
        };
        const key = String(status || '').toLowerCase();
        return messages[key] || status;
    },
};

class SubmissionHistoryManager {
    constructor() {
        this.submissions = [];
        this.filteredSubmissions = [];
        this.currentPage = 1;
        this.perPage = 12;
        this.totalPages = 1;

        this.state = {
            loading: false,
            error: null,
        };

        this.elements = {
            loadingState: document.getElementById('loadingState'),
            emptyState: document.getElementById('emptyState'),
            submissionsList: document.getElementById('submissionsList'),
            paginationControls: document.getElementById('paginationControls'),
            resultsSummary: document.getElementById('historyResultsSummary'),
            searchInput: document.getElementById('searchInput'),
            documentTypeFilter: document.getElementById('documentTypeFilter'),
            statusFilter: document.getElementById('statusFilter'),
            dateFilter: document.getElementById('dateFilter'),
            prevPageBtn: document.getElementById('prevPageBtn'),
            nextPageBtn: document.getElementById('nextPageBtn'),
            pageInfo: document.getElementById('pageInfo'),
        };

        this.init();
    }

    init() {
        this.bindEvents();
        this.loadSubmissions();
    }

    bindEvents() {
        if (this.elements.searchInput) {
            this.elements.searchInput.addEventListener('input', this.debounce(() => {
                this.currentPage = 1;
                this.applyFilters();
            }, 300));
        }

        [this.elements.documentTypeFilter, this.elements.statusFilter, this.elements.dateFilter].forEach((el) => {
            if (el) {
                el.addEventListener('change', () => {
                    this.currentPage = 1;
                    this.applyFilters();
                });
            }
        });

        if (this.elements.prevPageBtn) {
            this.elements.prevPageBtn.addEventListener('click', () => this.goToPage(this.currentPage - 1));
        }

        if (this.elements.nextPageBtn) {
            this.elements.nextPageBtn.addEventListener('click', () => this.goToPage(this.currentPage + 1));
        }

        if (this.elements.submissionsList) {
            this.elements.submissionsList.addEventListener('click', (e) => {
                const mapBtn = e.target.closest('.btn-open-mapping');
                if (mapBtn) {
                    const submissionId = mapBtn.closest('.submission-item')?.dataset.submissionId;
                    if (submissionId) this.openMappingWorkspace(submissionId);
                    return;
                }
                const stmtBtn = e.target.closest('.btn-view-statement');
                if (stmtBtn) {
                    const item = stmtBtn.closest('.submission-item');
                    const submissionId = item?.dataset.submissionId;
                    const submission = this.submissions.find((s) => s.session_id === submissionId);
                    if (submission) {
                        this.openClerkStatementReview(
                            submission.session_id,
                            submission.document_type
                        );
                    }
                }
            });
        }
    }

    openMappingWorkspace(sessionId, { revision = true } = {}) {
        const sid = encodeURIComponent(String(sessionId || '').trim());
        if (!sid) return;
        const rev = revision ? '&revision=1' : '';
        window.location.href = `/mapping?session_id=${sid}${rev}`;
    }

    openClerkStatementReview(sessionId, documentType) {
        const sid = encodeURIComponent(String(sessionId || '').trim());
        const docType = encodeURIComponent(normalizeDocumentType(documentType));
        const returnTo = encodeURIComponent('/submission-history');
        if (!sid) return;
        window.location.href = `/approvals?review=statement&transaction=${sid}&type=${docType}&returnTo=${returnTo}`;
    }

    async loadSubmissions(retryCount = 0) {
        this.showLoading(true);

        try {
            const response = await VarydianUtils.safeFetch('/api/submissions/user');

            if (response.success) {
                this.submissions = (response.submissions || []).filter((s) => !isClosedHistoryStatus(s.status));
                this.submissions.sort((a, b) => {
                    const da = new Date(a.submitted_at || a.submission_timestamp || 0).getTime();
                    const db = new Date(b.submitted_at || b.submission_timestamp || 0).getTime();
                    return db - da;
                });
                this.updateSubmissionStats();
                this.applyFilters();
                this.showLoading(false);
                this.hideError();
            } else if (response.error?.includes('401')) {
                throw new Error('Authentication required. Please log in again.');
            } else if (response.error?.includes('403')) {
                throw new Error('Permission denied. You do not have access to view submissions.');
            } else {
                throw new Error(response.error || 'Failed to load submissions');
            }
        } catch (error) {
            if (retryCount < 2 && (error.name === 'AbortError' || String(error.message).includes('timed out'))) {
                setTimeout(() => this.loadSubmissions(retryCount + 1), 2000 * (retryCount + 1));
                return;
            }
            this.showLoading(false);
            if (error.name === 'AbortError') {
                this.showError('Request timed out. Please refresh and try again.');
            } else {
                this.showError(error.message || 'Failed to load submissions.');
            }
        }
    }

    updateSubmissionStats() {
        const todayYmd = new Intl.DateTimeFormat('en-CA', {
            timeZone: 'Africa/Johannesburg',
        }).format(new Date());

        const pendingStatuses = new Set(['pending', 'pending_review', 'pending_cfo', 'approved_by_manager', 'submitted']);
        const approvedStatuses = new Set(['approved']);
        const submittedTimestamp = (submission) => submission.submitted_at || submission.submission_timestamp;

        const isSubmittedToday = (submission) => {
            const formatted = VarydianUtils.formatDateTime(submittedTimestamp(submission));
            const datePart = formatted.slice(0, 10);
            return Boolean(datePart && datePart === todayYmd);
        };

        const stats = {
            total: this.submissions.length,
            pending: this.submissions.filter(
                (s) => s.pending_approval || pendingStatuses.has(String(s.status || '').toLowerCase())
            ).length,
            approved: this.submissions.filter((s) => approvedStatuses.has(String(s.status || '').toLowerCase())).length,
            rejected: this.submissions.filter((s) => isRejectedHistoryStatus(s.status)).length,
            submittedToday: this.submissions.filter(isSubmittedToday).length,
        };

        const set = (id, val) => {
            const el = document.getElementById(id);
            if (el) el.textContent = val;
        };
        set('totalSubmissionsCount', stats.total);
        set('pendingSubmissionsCount', stats.pending);
        set('approvedSubmissionsCount', stats.approved);
        set('rejectedSubmissionsCount', stats.rejected);
        set('submittedTodayCount', stats.submittedToday);
    }

    applyFilters() {
        const searchTerm = (this.elements.searchInput?.value || '').toLowerCase();
        const statusFilter = this.elements.statusFilter?.value || 'all';
        const dateFilter = this.elements.dateFilter?.value || 'all';
        const docFilter = this.elements.documentTypeFilter?.value || 'all';

        this.filteredSubmissions = this.submissions.filter((submission) => {
            const filename = this.getFilename(submission).toLowerCase();
            const matchesSearch = !searchTerm || filename.includes(searchTerm);

            let matchesStatus = statusFilter === 'all';
            if (!matchesStatus) {
                if (statusFilter === 'rejected') {
                    matchesStatus = isRejectedHistoryStatus(submission.status);
                } else if (statusFilter === 'pending_review') {
                    matchesStatus = ['pending_review', 'pending', 'submitted', 'pending_cfo', 'approved_by_manager']
                        .includes(String(submission.status || '').toLowerCase());
                } else {
                    matchesStatus = String(submission.status || '').toLowerCase() === statusFilter;
                }
            }

            const rawDate = submission.submitted_at || submission.submission_timestamp;
            const submissionDate = rawDate ? new Date(rawDate) : null;
            const matchesDate = !submissionDate || Number.isNaN(submissionDate.getTime())
                ? dateFilter === 'all'
                : this.matchesDateFilter(submissionDate, dateFilter);

            const docType = String(submission.document_type || 'balance_sheet').toLowerCase();
            const matchesDoc = docFilter === 'all' || docType === docFilter;

            return matchesSearch && matchesStatus && matchesDate && matchesDoc;
        });

        this.renderSubmissions();
        this.updatePaginationControls();
        this.updateResultsSummary();
    }

    updateResultsSummary() {
        const el = this.elements.resultsSummary;
        if (!el) return;
        if (this.state.loading || this.submissions.length === 0) {
            VarydianUtils.hideElement(el);
            return;
        }
        const total = this.filteredSubmissions.length;
        const all = this.submissions.length;
        el.textContent = total === all
            ? `Showing ${total} submission${total === 1 ? '' : 's'}`
            : `Showing ${total} of ${all} submissions`;
        VarydianUtils.showElement(el);
    }

    matchesDateFilter(submissionDate, filter) {
        const now = new Date();
        const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());

        switch (filter) {
            case 'today':
                return submissionDate >= today;
            case 'week': {
                const weekAgo = new Date(today);
                weekAgo.setDate(weekAgo.getDate() - 7);
                return submissionDate >= weekAgo;
            }
            case 'month': {
                const monthAgo = new Date(today);
                monthAgo.setMonth(monthAgo.getMonth() - 1);
                return submissionDate >= monthAgo;
            }
            default:
                return true;
        }
    }

    getPageSlice() {
        const start = (this.currentPage - 1) * this.perPage;
        return this.filteredSubmissions.slice(start, start + this.perPage);
    }

    renderSubmissions() {
        if (this.filteredSubmissions.length === 0) {
            this.showEmptyState();
            return;
        }

        this.showSubmissionsList();
        this.elements.submissionsList.innerHTML = '';

        this.getPageSlice().forEach((submission) => {
            this.elements.submissionsList.appendChild(this.createSubmissionElement(submission));
        });
    }

    getFilename(submission) {
        const path = submission.filename || submission.filepath || '';
        if (path) {
            const parts = String(path).split(/[/\\]/);
            return parts[parts.length - 1] || path;
        }
        return `submission_${submission.session_id}`;
    }

    formatDocumentType(documentType) {
        return DOCUMENT_TYPE_LABELS[documentType] || String(documentType || 'Document').replace(/_/g, ' ');
    }

    createSubmissionElement(submission) {
        const template = document.getElementById('submissionItemTemplate');
        const clone = template.content.cloneNode(true);

        const submissionItem = clone.querySelector('.submission-item');
        submissionItem.dataset.submissionId = submission.session_id;

        const balanceSheetIcon = clone.querySelector('.icon-balance-sheet');
        const incomeStatementIcon = clone.querySelector('.icon-income-statement');
        const budgetReportIcon = clone.querySelector('.icon-budget-report');

        [balanceSheetIcon, incomeStatementIcon, budgetReportIcon].forEach((el) => {
            if (el) VarydianUtils.hideIcon(el);
        });

        const documentType = normalizeDocumentType(submission.document_type);
        const iconByType = {
            income_statement: incomeStatementIcon,
            budget_report: budgetReportIcon,
            balance_sheet: balanceSheetIcon,
        };
        const activeIcon = iconByType[documentType] || balanceSheetIcon;
        if (activeIcon) VarydianUtils.showIcon(activeIcon);

        const submissionName = clone.querySelector('.submission-name');
        const docBadge = clone.querySelector('.submission-doc-badge');
        const submissionDate = clone.querySelector('.submission-date');
        const submissionStatus = clone.querySelector('.submission-status');
        const submissionAccounts = clone.querySelector('.submission-accounts');

        const filename = this.getFilename(submission);
        submissionName.textContent = filename;
        submissionName.title = filename;

        if (docBadge) {
            docBadge.textContent = this.formatDocumentType(documentType);
            docBadge.className = `submission-doc-badge submission-doc-badge--${documentType}`;
        }

        submissionDate.textContent = this.formatDate(submission.submitted_at || submission.submission_timestamp);
        submissionStatus.textContent = this.formatStatus(submission.status);

        const mappedCount = typeof submission.mapped_accounts_count === 'number'
            ? submission.mapped_accounts_count
            : (Array.isArray(submission.mapped_accounts_count) ? submission.mapped_accounts_count.length : 0);
        submissionAccounts.textContent = `${mappedCount} account${mappedCount === 1 ? '' : 's'} mapped`;

        submissionStatus.className = `submission-status status-${String(submission.status || '').toLowerCase()}`;

        const mapBtn = clone.querySelector('.btn-open-mapping');
        if (mapBtn && isRejectedHistoryStatus(submission.status)) {
            VarydianUtils.showElement(mapBtn);
        }

        const stmtBtn = clone.querySelector('.btn-view-statement');
        if (stmtBtn && !canViewStatementInHistory(submission)) {
            VarydianUtils.hideElement(stmtBtn);
        }

        return clone;
    }

    goToPage(page) {
        if (page < 1 || page > this.totalPages) return;
        this.currentPage = page;
        this.renderSubmissions();
        this.updatePaginationControls();
        this.elements.submissionsList?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    updatePaginationControls() {
        const totalItems = this.filteredSubmissions.length;
        this.totalPages = Math.max(1, Math.ceil(totalItems / this.perPage));

        if (this.currentPage > this.totalPages) {
            this.currentPage = this.totalPages;
        }

        if (this.elements.prevPageBtn) {
            this.elements.prevPageBtn.disabled = this.currentPage <= 1;
        }
        if (this.elements.nextPageBtn) {
            this.elements.nextPageBtn.disabled = this.currentPage >= this.totalPages;
        }
        if (this.elements.pageInfo) {
            this.elements.pageInfo.textContent = `Page ${this.currentPage} of ${this.totalPages}`;
        }

        if (this.totalPages > 1) {
            VarydianUtils.showElement(this.elements.paginationControls, 'flex');
        } else {
            VarydianUtils.hideElement(this.elements.paginationControls);
        }
    }

    showLoading(show) {
        if (this.elements.loadingState) {
            if (show) VarydianUtils.showElement(this.elements.loadingState);
            else VarydianUtils.hideElement(this.elements.loadingState);
        }
        this.state.loading = show;
    }

    showEmptyState() {
        VarydianUtils.hideElement(this.elements.submissionsList);
        VarydianUtils.showElement(this.elements.emptyState);
        VarydianUtils.hideElement(this.elements.paginationControls);
        if (this.elements.resultsSummary) VarydianUtils.hideElement(this.elements.resultsSummary);
    }

    showSubmissionsList() {
        VarydianUtils.hideElement(this.elements.emptyState);
        VarydianUtils.showElement(this.elements.submissionsList, 'grid');
    }

    showError(message) {
        this.state.error = message;
        if (typeof VarydianUtils !== 'undefined') VarydianUtils.showError(message);
    }

    hideError() {
        this.state.error = null;
    }

    formatDate(dateString) {
        return VarydianUtils.formatDate(dateString);
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

document.addEventListener('DOMContentLoaded', () => {
    window.submissionHistoryManager = new SubmissionHistoryManager();
});
