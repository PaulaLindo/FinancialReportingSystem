// GRAP Mapping Interface
class GRAPMappingInterface {
    constructor(sessionId) {
        this.state = {
            sessionId: sessionId,
            unmappedAccounts: [],
            mappedAccounts: {},
            autoMappedAccounts: [], // New: for review workflow
            grapCategories: [],
            isDragging: false,
            draggedAccount: null,
            isReviewMode: false, // New: review mode flag
            mappingData: null // New: review data from upload
        };
        
        this.elements = {};
        this.init();
    }

    init() {
        this.cacheElements();
        this.setupEventListeners();
        this.checkReviewMode();
        this.loadGRAPCategories();
        this.loadData();
    }

    cacheElements() {
        this.elements = {
            unmappedAccountsList: document.getElementById('unmappedAccountsList'),
            grapCategories: document.getElementById('grapCategories'),
            unmappedCount: document.getElementById('unmappedCount'),
            mappedCount: document.getElementById('mappedCount'),
            totalAccounts: document.getElementById('totalAccounts'),
            mappedAccounts: document.getElementById('mappedAccounts'),
            remainingAccounts: document.getElementById('remainingAccounts'),
            completionPercentage: document.getElementById('completionPercentage'),
                        submitMappingBtn: document.getElementById('submitMappingBtn'),
            submissionStatus: document.getElementById('submissionStatus'),
            statusBadge: document.getElementById('statusBadge'),
            statusMessage: document.getElementById('statusMessage'),
            statusActions: document.getElementById('statusActions'),
            submitForReviewBtn: document.getElementById('submitForReviewBtn'),
            editMappingBtn: document.getElementById('editMappingBtn'),
            // New: Review mode elements
            mappedAccountsReview: document.getElementById('mappedAccountsReview'),
            mappedAccountsList: document.getElementById('mappedAccountsList'),
            confidenceSummary: document.getElementById('confidenceSummary'),
            avgConfidence: document.getElementById('avgConfidence'),
            highConfidenceCount: document.getElementById('highConfidenceCount'),
            mediumConfidenceCount: document.getElementById('mediumConfidenceCount'),
            lowConfidenceCount: document.getElementById('lowConfidenceCount'),
            reviewWarnings: document.getElementById('reviewWarnings'),
            saveMappingBtn: document.getElementById('saveMappingBtn'),
            categoryCount: document.getElementById('categoryCount')
        };
    }

    checkReviewMode() {
        // Check if this is a review session
        const urlParams = new URLSearchParams(window.location.search);
        this.state.isReviewMode = urlParams.get('review') === 'true';
        
        if (this.state.isReviewMode && window.mappingData) {
            this.state.mappingData = window.mappingData;
            this.state.autoMappedAccounts = window.mappingData.mapped_accounts || [];
            console.log('Review mode activated with data:', this.state.mappingData);
        }
    }

    loadData() {
        if (this.state.isReviewMode && this.state.mappingData) {
            // Load from review data (from upload processing)
            this.loadReviewData();
        } else if (this.state.isReviewMode && !this.state.mappingData) {
            // Review mode but no mapping data - fall back to database loading
            console.log('Review mode detected but no mapping data - loading from database');
            this.loadUnmappedAccounts();
        } else {
            // Load from database (traditional mapping)
            this.loadUnmappedAccounts();
        }
    }

    loadReviewData() {
        try {
            console.log('🔄 Loading review data...');
            console.log('📊 Raw mappingData:', this.state.mappingData);
            
            // Check if mappingData exists
            if (!this.state.mappingData) {
                console.error('❌ No mappingData found!');
                this.showError('No mapping data available');
                return;
            }
            
            // Inspect the structure of unmapped_accounts
            const unmappedRaw = this.state.mappingData.unmapped_accounts || [];
            const mappedRaw = this.state.mappingData.mapped_accounts || [];
            
            console.log('  - Raw unmapped_accounts:', unmappedRaw);
            console.log('  - Raw mapped_accounts:', mappedRaw);
            console.log('  - First unmapped account:', unmappedRaw[0]);
            console.log('  - First mapped account:', mappedRaw[0]);
            
            // Debug: Check if unmapped accounts have proper structure
            if (unmappedRaw.length > 0) {
                console.log('🔍 Unmapped account structure analysis:');
                console.log('  - Keys in first unmapped account:', Object.keys(unmappedRaw[0]));
                console.log('  - Sample account data:', JSON.stringify(unmappedRaw[0], null, 2));
            }
            
            // Debug: Check if mapped accounts have proper structure
            if (mappedRaw.length > 0) {
                console.log('🔍 Mapped account structure analysis:');
                console.log('  - Keys in first mapped account:', Object.keys(mappedRaw[0]));
                console.log('  - Sample account data:', JSON.stringify(mappedRaw[0], null, 2));
            }
            
            // Set unmapped accounts
            this.state.unmappedAccounts = unmappedRaw;
            
            // Initialize mapped accounts structure organized by GRAP category
            this.state.mappedAccounts = {};
            
            // Process auto-mapped accounts and place them in their GRAP categories
            mappedRaw.forEach((account, index) => {
                console.log(`Processing mapped account ${index}:`, account);
                
                const grapCategory = account.grap_category || account.grap_name || 'Unknown';
                const grapCode = account.grap_code || '';
                
                console.log(`  - GRAP Category: ${grapCategory}`);
                console.log(`  - GRAP Code: ${grapCode}`);
                
                // Create standardized account object
                const standardAccount = {
                    id: account.id || account.account_id || Date.now().toString(),
                    name: account.account_desc || account.name || 'Unknown Account',
                    code: account.account_code || account.code || '',
                    amount: account.net_balance || account.balance || account.amount || 0,
                    grapCategory: grapCategory,
                    grapCode: grapCode,
                    confidence: account.confidence || 0
                };
                
                console.log(`  - Standardized account:`, standardAccount);
                
                // Add to the appropriate GRAP category using the CODE as key
                if (!this.state.mappedAccounts[grapCode]) {
                    this.state.mappedAccounts[grapCode] = [];
                }
                this.state.mappedAccounts[grapCode].push(standardAccount);
            });
            
            console.log('✅ Processed mapped accounts by category:', this.state.mappedAccounts);
            console.log('✅ Final unmapped accounts:', this.state.unmappedAccounts);
            
            // Hide the review section since we're putting accounts directly in categories
            if (this.elements.mappedAccountsReview) {
                this.elements.mappedAccountsReview.style.display = 'none';
            }
            
            // Render all data
            this.renderUnmappedAccounts();
            this.renderCategories(); // This will show auto-mapped accounts in their categories
            this.updateProgress();
            this.updateConfidenceSummary();
            this.updateReviewStatus();
            
        } catch (error) {
            console.error('Error loading review data:', error);
            this.showError('Failed to load mapping review data');
        }
    }

    renderAutoMappedAccounts() {
        const container = this.elements.mappedAccountsList;
        if (!container) return;

        container.innerHTML = '';

        if (this.state.autoMappedAccounts.length === 0) {
            container.innerHTML = `
                <div class="no-accounts">
                    <p>No auto-mapped accounts found. All accounts require manual mapping.</p>
                </div>
            `;
            return;
        }

        this.state.autoMappedAccounts.forEach((account, index) => {
            const accountElement = this.createAutoMappedAccountElement(account, index);
            container.appendChild(accountElement);
        });
    }

    createAutoMappedAccountElement(account, index) {
        const div = document.createElement('div');
        div.className = 'mapped-account';
        div.draggable = true;
        div.dataset.index = index;

        // Determine confidence level
        const confidence = account.confidence || 0;
        let confidenceClass = 'confidence-low';
        let confidenceLabel = 'Low';
        
        if (confidence >= 0.8) {
            confidenceClass = 'confidence-high';
            confidenceLabel = 'High';
        } else if (confidence >= 0.5) {
            confidenceClass = 'confidence-medium';
            confidenceLabel = 'Medium';
        }

        div.innerHTML = `
            <div class="account-info">
                <div class="account-name">${account.name || account.account_name || 'Unknown Account'}</div>
                <div class="account-code">${account.code || account.account_code || ''}</div>
                <div class="account-amount">${this.formatCurrency(account.balance || account.amount || 0)}</div>
            </div>
            <div class="mapping-info">
                <div class="grap-category">${account.grap_name || account.grap_category || 'Unknown Category'}</div>
                <div class="grap-code">${account.grap_code || ''}</div>
                <div class="confidence-score ${confidenceClass}">
                    <span class="confidence-label">${confidenceLabel}</span>
                    <span class="confidence-value">${Math.round(confidence * 100)}%</span>
                </div>
            </div>
            <div class="account-actions">
                <button class="btn-edit-mapping" onclick="window.mappingInterface.editAccountMapping(${index})">
                    ✏️ Edit
                </button>
            </div>
        `;

        // Add drag event listeners
        div.addEventListener('dragstart', (e) => {
            e.dataTransfer.effectAllowed = 'move';
            e.dataTransfer.setData('text/plain', index);
            e.dataTransfer.setData('accountType', 'autoMapped');
            div.classList.add('dragging');
        });

        div.addEventListener('dragend', () => {
            div.classList.remove('dragging');
        });

        return div;
    }

    setupEventListeners() {
        // Drag and drop events - check if elements exist
        if (this.elements.unmappedAccountsList) {
            this.elements.unmappedAccountsList.addEventListener('dragstart', this.handleDragStart.bind(this));
            this.elements.unmappedAccountsList.addEventListener('dragend', this.handleDragEnd.bind(this));
        }
        
        if (this.elements.grapCategories) {
            this.elements.grapCategories.addEventListener('dragover', this.handleDragOver.bind(this));
            this.elements.grapCategories.addEventListener('drop', this.handleDrop.bind(this));
        }
        
                
        if (this.elements.submitMappingBtn) {
            this.elements.submitMappingBtn.addEventListener('click', this.submitMapping.bind(this));
        }
        
        // Save mapping button event
        const saveMappingBtn = document.getElementById('saveMappingBtn');
        if (saveMappingBtn) {
            saveMappingBtn.addEventListener('click', this.saveMappingProgress.bind(this));
        }
        
        // Submission events
        if (this.elements.submitForReviewBtn) {
            this.elements.submitForReviewBtn.addEventListener('click', this.submitForReview.bind(this));
        }
        
        if (this.elements.editMappingBtn) {
            this.elements.editMappingBtn.addEventListener('click', this.editMapping.bind(this));
        }
        
        // Search/filter events
        const searchInput = document.getElementById('searchInput');
        if (searchInput) {
            searchInput.addEventListener('input', this.filterAccounts.bind(this));
        }
    }

    async loadGRAPCategories() {
        try {
            const response = await fetch(`/api/grap-categories/${this.state.sessionId}`);
            const result = await response.json();
            
            // Check if we have categories (API returns categories directly, not wrapped in success)
            if (result.categories && Array.isArray(result.categories)) {
                this.state.grapCategories = result.categories;
                this.renderCategories();
            } else if (result.error) {
                this.showError(result.error);
            } else {
                this.showError('Unexpected response format from server');
            }
        } catch (error) {
            this.showError('Failed to load GRAP categories. Please try again.');
        }
    }

    async loadUnmappedAccounts() {
        try {
            console.log('🔄 Loading unmapped accounts for session:', this.state.sessionId);
            
            // Load from Supabase API
            const response = await fetch(`/api/unmapped-accounts/${this.state.sessionId}`);
            const result = await response.json();
            
            console.log('📊 API Response:', result);
            
            if (result.success) {
                this.state.unmappedAccounts = result.accounts;
                this.state.mappedAccounts = result.mapped_accounts || {};
                
                console.log('✅ Data loaded successfully:');
                console.log('  - Unmapped accounts:', this.state.unmappedAccounts.length);
                console.log('  - Mapped categories:', Object.keys(this.state.mappedAccounts).length);
                
                this.renderUnmappedAccounts();
                this.updateStats();
                
                console.log('🎨 UI updated');
            } else {
                console.error('❌ API Error:', result.error);
                this.showError(result.error || 'Failed to load accounts');
            }
        } catch (error) {
            console.error('💥 Network Error:', error);
            this.showError('Failed to load accounts. Please try again.');
        }
    }

    renderCategories() {
        console.log('🎨 Rendering GRAP categories...');
        console.log('  - Element exists:', !!this.elements.grapCategories);
        console.log('  - Categories available:', this.state.grapCategories.length);
        console.log('  - Mapped accounts:', this.state.mappedAccounts);
        
        this.elements.grapCategories.innerHTML = '';
        
        this.state.grapCategories.forEach(category => {
            console.log(`  Rendering category: ${category.name} (${category.code})`);
            
            const categoryEl = document.createElement('div');
            categoryEl.className = 'grap-category';
            categoryEl.dataset.categoryId = category.code;
            
            categoryEl.innerHTML = `
                <div class="category-header">
                    <h3>${category.name}</h3>
                    <span class="category-code">${category.code}</span>
                </div>
                <div class="mapped-accounts" data-category="${category.code}">
                    ${this.renderMappedAccounts(category.code)}
                </div>
            `;
            
            this.elements.grapCategories.appendChild(categoryEl);
        });
        
        console.log('✅ GRAP categories rendered successfully');
    }

    renderMappedAccounts(categoryId) {
        const mappedAccounts = this.state.mappedAccounts[categoryId] || [];
        
        if (mappedAccounts.length === 0) {
            return '<div class="empty-category">Drop accounts here</div>';
        }
        
        return mappedAccounts.map(account => {
            // Determine confidence level
            const confidence = account.confidence || 0;
            let confidenceClass = 'confidence-low';
            let confidenceLabel = 'Low';
            
            if (confidence >= 0.8) {
                confidenceClass = 'confidence-high';
                confidenceLabel = 'High';
            } else if (confidence >= 0.5) {
                confidenceClass = 'confidence-medium';
                confidenceLabel = 'Medium';
            }
            
            // Use correct field names for both unmapped and pre-mapped accounts
            const accountName = account.account_desc || account.name || 'Unknown Account';
            const accountCode = account.account_code || account.code || '';
            const accountAmount = account.net_balance || account.amount || 0;
            const accountId = account.id || account.account_code || 'unknown';
            
            return `
                <div class="mapped-account" data-account-id="${accountId}" draggable="true">
                    <div class="account-info">
                        <div class="account-name">${accountName}</div>
                        <div class="account-code">${accountCode}</div>
                        <div class="account-amount">${this.formatCurrency(accountAmount)}</div>
                    </div>
                    <div class="confidence-score ${confidenceClass}">
                        <span class="confidence-label">${confidenceLabel}</span>
                        <span class="confidence-value">${Math.round(confidence * 100)}%</span>
                    </div>
                    <button class="remove-account" onclick="window.mappingInterface.removeMapping('${accountId}')">×</button>
                </div>
            `;
        }).join('');
    }

    renderUnmappedAccounts() {
        console.log('🎨 Rendering unmapped accounts...');
        console.log('  - Element exists:', !!this.elements.unmappedAccountsList);
        console.log('  - Accounts to render:', this.state.unmappedAccounts.length);
        
        this.elements.unmappedAccountsList.innerHTML = '';
        
        if (this.state.unmappedAccounts.length === 0) {
            console.log('⚠️ No unmapped accounts to render');
            this.elements.unmappedAccountsList.innerHTML = '<div class="no-accounts">No accounts to map</div>';
            return;
        }
        
        this.state.unmappedAccounts.forEach((account, index) => {
            console.log(`  Rendering account ${index + 1}: ${account.account_code || account.code} - ${account.account_desc || account.name}`);
            
            const accountEl = document.createElement('div');
            accountEl.className = 'unmapped-account';
            accountEl.draggable = true;
            accountEl.dataset.accountId = account.id || account.account_code || index.toString();
            
            accountEl.innerHTML = `
                <div class="account-name">${account.account_desc || account.name || 'Unknown Account'}</div>
                <div class="account-code">${account.account_code || account.code || ''}</div>
                <div class="account-amount">${this.formatCurrency(account.net_balance || account.amount || 0)}</div>
                <div class="account-description">${account.account_desc || account.description || ''}</div>
            `;
            
            this.elements.unmappedAccountsList.appendChild(accountEl);
        });
        
        console.log('✅ Unmapped accounts rendered successfully');
    }

    handleDragStart(e) {
        const accountEl = e.target.closest('.unmapped-account');
        if (!accountEl) return;
        
        this.state.isDragging = true;
        this.state.draggedAccount = {
            id: accountEl.dataset.accountId,
            element: accountEl
        };
        
        accountEl.classList.add('dragging');
        e.dataTransfer.effectAllowed = 'move';
    }

    handleDragEnd(e) {
        this.state.isDragging = false;
        this.state.draggedAccount = null;
        
        const draggingEl = document.querySelector('.dragging');
        if (draggingEl) {
            draggingEl.classList.remove('dragging');
        }
    }

    handleDragOver(e) {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
        
        const categoryEl = e.target.closest('.grap-category');
        if (categoryEl) {
            categoryEl.classList.add('drag-over');
        }
    }

    handleDrop(e) {
        e.preventDefault();
        
        const categoryEl = e.target.closest('.grap-category');
        if (!categoryEl || !this.state.draggedAccount) return;
        
        categoryEl.classList.remove('drag-over');
        
        const categoryId = categoryEl.dataset.categoryId;
        const accountId = this.state.draggedAccount.id;
        
        this.addMapping(accountId, categoryId);
    }

    addMapping(accountId, categoryId) {
        try {
            console.log('🔄 Adding mapping:', { accountId, categoryId });
            
            // Update local state directly (no API call needed for demo)
            const account = this.state.unmappedAccounts.find(a => a.account_code === accountId || a.id === accountId);
            console.log('  - Found account:', account);
            
            if (account) {
                // Remove from unmapped
                this.state.unmappedAccounts = this.state.unmappedAccounts.filter(a => a.account_code !== accountId && a.id !== accountId);
                
                // Add to mapped
                if (!this.state.mappedAccounts[categoryId]) {
                    this.state.mappedAccounts[categoryId] = [];
                }
                this.state.mappedAccounts[categoryId].push(account);
                
                console.log('  - Account added to category:', categoryId);
                console.log('  - Updated mapped accounts:', this.state.mappedAccounts);
                console.log('  - Updated unmapped accounts:', this.state.unmappedAccounts);
                
                // Update UI
                this.renderUnmappedAccounts();
                this.renderCategories();
                this.updateStats();
                
                this.showSuccess(`Account "${account.account_desc}" mapped to ${categoryId}`);
            } else {
                console.error('❌ Account not found:', accountId);
                this.showError('Account not found for mapping.');
            }
        } catch (error) {
            console.error('💥 Error in addMapping:', error);
            this.showError('Failed to add mapping. Please try again.');
        }
    }

    removeMapping(accountId) {
        try {
            // Find the account in mapped accounts
            let foundAccount = null;
            let sourceCategoryId = null;
            
            for (const [categoryId, accounts] of Object.entries(this.state.mappedAccounts)) {
                const accountIndex = accounts.findIndex(a => a.id === accountId);
                if (accountIndex > -1) {
                    foundAccount = accounts.splice(accountIndex, 1)[0];
                    sourceCategoryId = categoryId;
                    break;
                }
            }
            
            if (foundAccount) {
                // Add back to unmapped
                this.state.unmappedAccounts.push(foundAccount);
                
                // Update UI
                this.renderUnmappedAccounts();
                this.renderCategories();
                this.updateStats();
            } else {
                // Mapped account not found
            }
        } catch (error) {
            this.showError('Failed to remove mapping. Please try again.');
        }
    }

    async autoMap() {
        try {
            this.elements.autoMapBtn.disabled = true;
            this.elements.autoMapBtn.textContent = 'Auto-mapping...';
            
            const response = await fetch(`/api/auto-map/${this.state.sessionId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            const result = await response.json();
            
            if (result.success) {
                
                // Apply the auto-mapping results
                if (result.mapping_results) {
                    for (const [categoryId, accounts] of Object.entries(result.mapping_results)) {
                        if (!this.state.mappedAccounts[categoryId]) {
                            this.state.mappedAccounts[categoryId] = [];
                        }
                        
                        accounts.forEach(account => {
                            // Remove from unmapped accounts using flexible field matching
                            const accountIndex = this.state.unmappedAccounts.findIndex(ua => {
                                // Try multiple field combinations to find matching account
                                return ua.code === account['Account Code'] || 
                                       ua['Account Code'] === account['Account Code'] ||
                                       ua.code === account.code ||
                                       ua.name === account['Account Description'] ||
                                       ua.name === account.name;
                            });
                            if (accountIndex > -1) {
                                const unmappedAccount = this.state.unmappedAccounts.splice(accountIndex, 1)[0];
                                // Add to mapped accounts
                                this.state.mappedAccounts[categoryId].push(unmappedAccount);
                            }
                        });
                    }
                    
                    // Update the UI
                    this.renderUnmappedAccounts();
                    this.renderCategories();
                    this.updateStats();
                }
                
                this.showSuccess(`Auto-mapped ${result.mapped_count} out of ${result.total_accounts} accounts`);
            } else {
                this.showError(result.error || 'Auto-mapping failed');
            }
        } catch (error) {
            this.showError('Auto-mapping failed. Please try again.');
        } finally {
            this.elements.autoMapBtn.disabled = false;
            this.elements.autoMapBtn.textContent = 'Auto Map';
        }
    }

    updateStats() {
        console.log('📊 Updating statistics...');
        
        const totalAccounts = this.state.unmappedAccounts.length + this.getTotalMappedAccounts();
        const mappedAccounts = this.getTotalMappedAccounts();
        const remainingAccounts = this.state.unmappedAccounts.length;
        const completionPercentage = totalAccounts > 0 ? Math.round((mappedAccounts / totalAccounts) * 100) : 0;

        console.log('  - Total accounts:', totalAccounts);
        console.log('  - Mapped accounts:', mappedAccounts);
        console.log('  - Remaining accounts:', remainingAccounts);
        console.log('  - Completion percentage:', completionPercentage + '%');

        // Update stats display
        if (this.elements.totalAccounts) {
            this.elements.totalAccounts.textContent = totalAccounts;
        }
        if (this.elements.mappedAccounts) {
            this.elements.mappedAccounts.textContent = mappedAccounts;
        }
        if (this.elements.remainingAccounts) {
            this.elements.remainingAccounts.textContent = remainingAccounts;
        }
        if (this.elements.completionPercentage) {
            this.elements.completionPercentage.textContent = completionPercentage + '%';
        }

        console.log('✅ Statistics updated');

        // Update submit button
        this.updateSubmitButton();
        
        // Check if mapping is complete and show submission status
        this.checkMappingCompletion();
    }

    getTotalMappedAccounts() {
        let total = 0;
        for (const categoryId in this.state.mappedAccounts) {
            total += this.state.mappedAccounts[categoryId].length;
        }
        return total;
    }

    updateSubmitButton() {
        const unmappedCount = this.state.unmappedAccounts.length;
        const submitBtn = this.elements.submitMappingBtn;
        
        if (submitBtn) {
            if (unmappedCount === 0) {
                submitBtn.disabled = false;
                submitBtn.textContent = 'Submit for Review';
                submitBtn.classList.remove('disabled');
            } else {
                submitBtn.disabled = true;
                submitBtn.textContent = `Submit for Review (${unmappedCount} remaining)`;
                submitBtn.classList.add('disabled');
            }
        }
    }

    async submitMapping() {
        const unmappedCount = this.state.unmappedAccounts.length;
        if (unmappedCount > 0) {
            if (!confirm(`You still have ${unmappedCount} unmapped accounts. Are you sure you want to submit?`)) {
                return;
            }
        }
        
        try {
            this.elements.submitMappingBtn.disabled = true;
            this.elements.submitMappingBtn.textContent = 'Submitting...';
            
            // Get mapped data for submission
            const mappedData = this.getMappedDataForSubmission();
            
            const response = await fetch('/api/submit-mapping', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    mapped_data: mappedData,
                    session_id: this.state.sessionId
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showSuccess('Mapping submitted successfully');
                setTimeout(() => {
                    // Redirect to the submission status page using the submission_id returned
                    window.location.href = `/submission/${result.submission_id}`;
                }, 1500);
            } else {
                this.showError(result.error || 'Failed to submit mapping');
            }
        } catch (error) {
            this.showError('Failed to submit mapping. Please try again.');
        } finally {
            this.elements.submitMappingBtn.disabled = false;
            this.elements.submitMappingBtn.textContent = 'Submit Mapping & Continue';
        }
    }

    filterAccounts(e) {
        const searchTerm = e.target.value.toLowerCase();
        const accountEls = this.elements.unmappedAccountsList.querySelectorAll('.unmapped-account');
        
        accountEls.forEach(accountEl => {
            const accountName = accountEl.querySelector('.account-name').textContent.toLowerCase();
            const accountCode = accountEl.querySelector('.account-code').textContent.toLowerCase();
            
            if (accountName.includes(searchTerm) || accountCode.includes(searchTerm)) {
                accountEl.classList.remove('account-hidden');
            } else {
                accountEl.classList.add('account-hidden');
            }
        });
    }

    formatCurrency(amount) {
        return 'R ' + new Intl.NumberFormat('en-ZA', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        }).format(amount);
    }

    showSuccess(message) {
        this.showNotification(message, 'success');
    }

    showError(message) {
        this.showNotification(message, 'error');
    }

    showNotification(message, type) {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.remove();
        }, 3000);
    }

    // Submission workflow methods
    showSubmissionStatus(status = 'draft') {
        if (!this.elements.submissionStatus) return;
        
        this.elements.submissionStatus.classList.remove('submission-hidden');
        this.updateSubmissionUI(status);
    }

    updateSubmissionUI(status) {
        if (!this.elements.statusBadge || !this.elements.statusMessage) return;
        
        // Update badge
        this.elements.statusBadge.className = `status-badge ${status}`;
        this.elements.statusBadge.textContent = status.charAt(0).toUpperCase() + status.slice(1);
        
        // Update message
        const messages = {
            draft: 'Your balance sheet mapping is ready for submission.',
            pending: 'Your balance sheet has been submitted for review. You will be notified when it\'s approved or rejected.',
            approved: 'Your balance sheet has been approved! You can now generate financial statements.',
            rejected: 'Your balance sheet was rejected. You can edit the mapping and resubmit.'
        };
        
        this.elements.statusMessage.textContent = messages[status] || 'Status unknown.';
        
        // Update buttons
        this.updateSubmissionActions(status);
        
        // Update mapping interface state
        this.updateMappingInterfaceState(status);
    }

    updateSubmissionActions(status) {
        if (!this.elements.statusActions) return;
        
        const submitBtn = this.elements.submitForReviewBtn;
        const editBtn = this.elements.editMappingBtn;
        
        switch (status) {
            case 'draft':
                if (submitBtn) {
                    submitBtn.classList.remove('button-hidden');
                    submitBtn.classList.add('button-visible');
                }
                if (editBtn) {
                    editBtn.classList.add('button-hidden');
                    editBtn.classList.remove('button-visible');
                }
                break;
            case 'pending':
                if (submitBtn) {
                    submitBtn.classList.add('button-hidden');
                    submitBtn.classList.remove('button-visible');
                }
                if (editBtn) {
                    editBtn.classList.add('button-hidden');
                    editBtn.classList.remove('button-visible');
                }
                break;
            case 'rejected':
                if (submitBtn) {
                    submitBtn.classList.remove('button-hidden');
                    submitBtn.classList.add('button-visible');
                }
                if (editBtn) {
                    editBtn.classList.remove('button-hidden');
                    editBtn.classList.add('button-visible');
                }
                break;
            case 'approved':
                if (submitBtn) {
                    submitBtn.classList.add('button-hidden');
                    submitBtn.classList.remove('button-visible');
                }
                if (editBtn) {
                    editBtn.classList.add('button-hidden');
                    editBtn.classList.remove('button-visible');
                }
                break;
        }
    }

    updateMappingInterfaceState(status) {
        const isLocked = status === 'pending' || status === 'approved';
        
        // Disable drag and drop if locked
        if (isLocked) {
            this.disableMapping();
        } else {
            this.enableMapping();
        }
        
        // Update submit mapping button
        if (this.elements.submitMappingBtn) {
            this.elements.submitMappingBtn.disabled = isLocked;
            if (isLocked) {
                this.elements.submitMappingBtn.textContent = 'Locked - Pending Review';
            } else {
                this.updateSubmitButton();
            }
        }
    }

    disableMapping() {
        // Disable drag and drop
        this.state.isDragging = false;
        
        // Add visual indication that mapping is locked
        if (this.elements.unmappedAccountsList) {
            this.elements.unmappedAccountsList.classList.add('mapping-locked');
        }
        
        if (this.elements.grapCategories) {
            this.elements.grapCategories.classList.add('mapping-locked');
        }
    }

    enableMapping() {
        // Enable drag and drop
        if (this.elements.unmappedAccountsList) {
            this.elements.unmappedAccountsList.classList.remove('mapping-locked');
        }
        
        if (this.elements.grapCategories) {
            this.elements.grapCategories.classList.remove('mapping-locked');
        }
    }

    async submitForReview() {
        if (!this.state.sessionId) {
            this.showError('No session found. Please start over.');
            return;
        }

        try {
            // Disable button during submission
            if (this.elements.submitForReviewBtn) {
                this.elements.submitForReviewBtn.disabled = true;
                this.elements.submitForReviewBtn.textContent = 'Submitting...';
            }

            // Get mapped data
            const mappedData = this.getMappedDataForSubmission();
            
            const response = await fetch('/api/submit-mapping', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    filepath: `session_${this.state.sessionId}`,
                    mapped_data: mappedData,
                    uploaded_filepath: this.state.uploadedFilePath,
                    session_id: this.state.sessionId
                })
            });
            
            const result = await response.json();

            if (result.success) {
                this.showSuccess('Balance sheet submitted for review successfully!');
                this.updateSubmissionUI('pending');
                
                // Store submission ID for status checking
                this.state.submissionId = result.submission_id;
                
                setTimeout(() => {
                    window.location.href = `/submission/${result.submission_id}`;
                }, 2000);
            } else {
                this.showError(result.error || 'Submission failed');
            }
        } catch (error) {
            this.showError('Submission failed. Please try again.');
        } finally {
            // Re-enable submit button
            if (this.elements.submitForReviewBtn) {
                this.elements.submitForReviewBtn.disabled = false;
                this.elements.submitForReviewBtn.textContent = 'Submit for Review';
            }
        }
    }
        

    getMappedDataForSubmission() {
        const mappedData = [];
        
        // Add auto-mapped accounts
        this.state.autoMappedAccounts.forEach(account => {
            mappedData.push({
                ...account,
                grap_code: account.grap_code,
                grap_category: account.grap_name || this.getGRAPCategoryName(account.grap_code),
                confidence: account.confidence
            });
        });
        
        // Add manually mapped accounts from categories
        Object.entries(this.state.mappedAccounts).forEach(([categoryCode, accounts]) => {
            accounts.forEach(account => {
                mappedData.push({
                    ...account,
                    grap_code: categoryCode,
                    grap_category: this.getGRAPCategoryName(categoryCode),
                    confidence: 1.0 // Manual mapping has 100% confidence
                });
            });
        });

        return mappedData;
    }
    
    getGRAPCategoryName(categoryCode) {
        const category = this.state.grapCategories.find(cat => cat.code === categoryCode);
        return category ? category.name : categoryCode;
    }

    editMapping() {
        // Enable editing for rejected submissions
        this.updateSubmissionUI('draft');
        this.showSuccess('You can now edit your mapping and resubmit.');
    }

    editAccountMapping(accountIndex) {
        // Move an auto-mapped account back to unmapped for manual mapping
        const account = this.state.autoMappedAccounts[accountIndex];
        if (!account) return;

        // Remove from auto-mapped accounts
        this.state.autoMappedAccounts.splice(accountIndex, 1);
        
        // Add to unmapped accounts
        this.state.unmappedAccounts.push(account);
        
        // Re-render both sections
        this.renderAutoMappedAccounts();
        this.renderUnmappedAccounts();
        this.updateProgress();
        this.updateConfidenceSummary();
        this.updateReviewStatus();
        
        this.showSuccess(`Account "${account.name}" moved to manual mapping`);
    }

    async saveMappingProgress() {
        try {
            // Disable button during save
            const saveBtn = document.getElementById('saveMappingBtn');
            if (saveBtn) {
                saveBtn.disabled = true;
                saveBtn.textContent = 'Saving...';
            }

            // Prepare data to save
            const saveData = {
                session_id: this.state.sessionId,
                auto_mapped_accounts: this.state.autoMappedAccounts,
                unmapped_accounts: this.state.unmappedAccounts,
                saved_at: new Date().toISOString()
            };

            const response = await fetch('/api/save-mapping-progress', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(saveData)
            });

            const result = await response.json();

            if (result.success) {
                this.showSuccess('Mapping progress saved successfully!');
            } else {
                this.showError(result.error || 'Failed to save mapping progress');
            }
        } catch (error) {
            this.showError('Failed to save mapping progress. Please try again.');
        } finally {
            // Re-enable save button
            const saveBtn = document.getElementById('saveMappingBtn');
            if (saveBtn) {
                saveBtn.disabled = false;
                saveBtn.textContent = ' Save Mapping Progress';
            }
        }
    }

    startStatusPolling() {
        if (!this.state.submissionId) return;
        
        // Poll every 30 seconds for status updates
        this.statusPollingInterval = setInterval(async () => {
            try {
                const response = await fetch(`/api/submission-status/${this.state.submissionId}`);
                const result = await response.json();
                
                if (result.success && result.status !== this.state.currentStatus) {
                    this.state.currentStatus = result.status;
                    this.updateSubmissionUI(result.status);
                    
                    if (result.status === 'approved') {
                        this.showSuccess('Your balance sheet has been approved! 🎉');
                        clearInterval(this.statusPollingInterval);
                    } else if (result.status === 'rejected') {
                        this.showError('Your balance sheet was rejected. Please review the feedback.');
                    }
                }
            } catch (error) {
                // Status polling error
            }
        }, 30000);
    }

    updateProgress() {
        // Calculate total accounts (auto-mapped + unmapped)
        const autoMappedCount = this.state.autoMappedAccounts.length;
        const unmappedCount = this.state.unmappedAccounts.length;
        const totalAccounts = autoMappedCount + unmappedCount;
        
        // Update counts in UI
        if (this.elements.totalAccounts) {
            this.elements.totalAccounts.textContent = totalAccounts;
        }
        
        if (this.elements.mappedCount) {
            this.elements.mappedCount.textContent = autoMappedCount;
        }
        
        if (this.elements.unmappedCount) {
            this.elements.unmappedCount.textContent = unmappedCount;
        }
        
        if (this.elements.remainingAccounts) {
            this.elements.remainingAccounts.textContent = unmappedCount;
        }
        
        // Calculate completion percentage
        const completionPercentage = totalAccounts > 0 ? 
            Math.round((autoMappedCount / totalAccounts) * 100) : 0;
        
        if (this.elements.completionPercentage) {
            this.elements.completionPercentage.textContent = `${completionPercentage}%`;
        }
        
        // Update category count
        if (this.elements.categoryCount && this.state.grapCategories) {
            this.elements.categoryCount.textContent = this.state.grapCategories.length;
        }
    }

    updateConfidenceSummary() {
        if (!this.elements.confidenceSummary) return;

        const autoMappedAccounts = this.state.autoMappedAccounts;
        if (autoMappedAccounts.length === 0) {
            this.elements.confidenceSummary.innerHTML = `
                <div class="confidence-empty">
                    <p>No auto-mapped accounts to analyze</p>
                </div>
            `;
            return;
        }

        // Calculate confidence breakdown
        let highConfidence = 0;
        let mediumConfidence = 0;
        let lowConfidence = 0;
        let totalConfidence = 0;

        autoMappedAccounts.forEach(account => {
            const confidence = account.confidence || 0;
            totalConfidence += confidence;
            
            if (confidence >= 0.8) {
                highConfidence++;
            } else if (confidence >= 0.5) {
                mediumConfidence++;
            } else {
                lowConfidence++;
            }
        });

        const avgConfidence = totalConfidence / autoMappedAccounts.length;

        // Update UI elements
        if (this.elements.avgConfidence) {
            this.elements.avgConfidence.textContent = `${Math.round(avgConfidence * 100)}%`;
        }
        
        if (this.elements.highConfidenceCount) {
            this.elements.highConfidenceCount.textContent = highConfidence;
        }
        
        if (this.elements.mediumConfidenceCount) {
            this.elements.mediumConfidenceCount.textContent = mediumConfidence;
        }
        
        if (this.elements.lowConfidenceCount) {
            this.elements.lowConfidenceCount.textContent = lowConfidence;
        }

        // Show/hide warnings based on confidence levels
        this.updateReviewWarnings(avgConfidence, lowConfidence);
    }

    updateReviewWarnings(avgConfidence, lowConfidenceCount) {
        if (!this.elements.reviewWarnings) return;

        let warnings = [];

        if (avgConfidence < 0.7) {
            warnings.push('Overall mapping confidence is below 70%. Manual review recommended.');
        }

        if (lowConfidenceCount > 0) {
            warnings.push(`${lowConfidenceCount} account(s) have low confidence mapping and should be reviewed manually.`);
        }

        if (this.state.unmappedAccounts.length > 0) {
            warnings.push(`${this.state.unmappedAccounts.length} account(s) require manual mapping.`);
        }

        if (warnings.length === 0) {
            this.elements.reviewWarnings.innerHTML = `
                <div class="warning-success">
                    ✅ All mappings look good! Ready for submission.
                </div>
            `;
        } else {
            this.elements.reviewWarnings.innerHTML = warnings.map(warning => `
                <div class="warning-item">
                    ⚠️ ${warning}
                </div>
            `).join('');
        }
    }

    updateReviewStatus() {
        // Update submit button state based on confidence and completion
        const submitBtn = this.elements.submitForReviewBtn;
        if (!submitBtn) return;

        const hasUnmappedAccounts = this.state.unmappedAccounts.length > 0;
        const autoMappedAccounts = this.state.autoMappedAccounts;
        
        // Calculate average confidence
        let avgConfidence = 0;
        if (autoMappedAccounts.length > 0) {
            const totalConfidence = autoMappedAccounts.reduce((sum, account) => sum + (account.confidence || 0), 0);
            avgConfidence = totalConfidence / autoMappedAccounts.length;
        }

        // Enable submit if no unmapped accounts and confidence is acceptable
        const canSubmit = !hasUnmappedAccounts && avgConfidence >= 0.5;
        
        submitBtn.disabled = !canSubmit;
        
        if (hasUnmappedAccounts) {
            submitBtn.textContent = '📋 Complete Mapping First';
        } else if (avgConfidence < 0.5) {
            submitBtn.textContent = '📋 Low Confidence - Review Required';
        } else {
            submitBtn.textContent = '📋 Submit for Manager Review';
        }
    }

    // Show submission status when mapping is complete
    checkMappingCompletion() {
        const remainingCount = this.state.unmappedAccounts.length;
        
        if (remainingCount === 0 && !this.state.submissionShown) {
            this.state.submissionShown = true;
            this.showSubmissionStatus('draft');
        }
    }
}

// Initialize mapping interface
document.addEventListener('DOMContentLoaded', function() {
    // Extract session ID from uploaded file path or generate one
    let sessionId = window.sessionId || '';
    
    // Session ID managed server-side via Supabase
    if (sessionId) {
        window.sessionId = sessionId;
    }
    
    window.mappingInterface = new GRAPMappingInterface(sessionId);
});

