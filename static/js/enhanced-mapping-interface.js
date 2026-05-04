// Enhanced GRAP Mapping Interface with Better Drag & Drop and Mobile Support
class EnhancedGRAPMappingInterface {
    constructor(sessionId) {
        this.state = {
            sessionId: sessionId,
            unmappedAccounts: [],
            mappedAccounts: {},
            autoMappedAccounts: [],
            grapCategories: [],
            isDragging: false,
            draggedAccount: null,
            isReviewMode: false,
            mappingData: null,
            touchStartX: 0,
            touchStartY: 0,
            draggedElement: null,
            dragGhost: null
        };
        
        this.elements = {};
        this.init();
    }

    init() {
        console.log('🚀 Enhanced GRAP Mapping Interface initializing...');
        console.log('📋 Session ID:', this.state.sessionId);
        
        this.cacheElements();
        this.setupEventListeners();
        this.checkReviewMode();
        console.log('🔍 Review mode:', this.state.isReviewMode);
        
        this.loadGRAPCategories();
        this.loadData();
        this.createDragGhost();
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

    createDragGhost() {
        // Create a custom drag ghost element for better visual feedback
        this.state.dragGhost = document.createElement('div');
        this.state.dragGhost.className = 'drag-ghost';
        this.state.dragGhost.style.cssText = `
            position: fixed;
            top: -1000px;
            left: -1000px;
            pointer-events: none;
            z-index: 1000;
            background: var(--primary-600);
            color: white;
            padding: 8px 12px;
            border-radius: 6px;
            font-size: 14px;
            font-weight: 600;
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
            transform: rotate(-2deg);
            transition: none;
        `;
        document.body.appendChild(this.state.dragGhost);
    }

    checkReviewMode() {
        const urlParams = new URLSearchParams(window.location.search);
        this.state.isReviewMode = urlParams.get('review') === 'true';
        
        if (this.state.isReviewMode && window.mappingData) {
            this.state.mappingData = window.mappingData;
            this.state.autoMappedAccounts = window.mappingData.mapped_accounts || [];
        }
    }

    loadData() {
        // Always load data from APIs
        this.loadUnmappedAccounts();
    }

    loadReviewData() {
        try {
            if (!this.state.mappingData) {
                this.showError('No mapping data available');
                return;
            }
            
            const unmappedRaw = this.state.mappingData.unmapped_accounts || [];
            const mappedRaw = this.state.mappingData.mapped_accounts || [];
            
            this.state.unmappedAccounts = unmappedRaw;
            this.state.mappedAccounts = {};
            
            mappedRaw.forEach((account, index) => {
                const grapCategory = account.grap_category || account.grap_name || 'Unknown';
                const grapCode = account.grap_code || '';
                
                const standardAccount = {
                    id: account.id || account.account_id || Date.now().toString(),
                    name: account.account_desc || account.name || 'Unknown Account',
                    code: account.account_code || account.code || '',
                    amount: account.net_balance || account.balance || account.amount || 0,
                    grapCategory: grapCategory,
                    grapCode: grapCode,
                    confidence: account.confidence || 0
                };
                
                if (!this.state.mappedAccounts[grapCode]) {
                    this.state.mappedAccounts[grapCode] = [];
                }
                this.state.mappedAccounts[grapCode].push(standardAccount);
            });
            
            if (this.elements.mappedAccountsReview) {
                this.elements.mappedAccountsReview.style.display = 'none';
            }
            
            this.renderUnmappedAccounts();
            this.renderCategories();
            this.updateProgress();
            this.updateConfidenceSummary();
            this.updateReviewStatus();
            
        } catch (error) {
            console.error('Error loading review data:', error);
            this.showError('Failed to load mapping review data');
        }
    }

    setupEventListeners() {
        // Enhanced drag and drop events
        if (this.elements.unmappedAccountsList) {
            this.elements.unmappedAccountsList.addEventListener('dragstart', this.handleDragStart.bind(this));
            this.elements.unmappedAccountsList.addEventListener('dragend', this.handleDragEnd.bind(this));
            
            // Touch events for mobile
            this.elements.unmappedAccountsList.addEventListener('touchstart', this.handleTouchStart.bind(this), { passive: false });
            this.elements.unmappedAccountsList.addEventListener('touchmove', this.handleTouchMove.bind(this), { passive: false });
            this.elements.unmappedAccountsList.addEventListener('touchend', this.handleTouchEnd.bind(this), { passive: false });
        }
        
        if (this.elements.grapCategories) {
            this.elements.grapCategories.addEventListener('dragover', this.handleDragOver.bind(this));
            this.elements.grapCategories.addEventListener('drop', this.handleDrop.bind(this));
            
            // Touch events for categories
            this.elements.grapCategories.addEventListener('touchmove', this.handleCategoryTouchMove.bind(this), { passive: false });
            this.elements.grapCategories.addEventListener('touchend', this.handleCategoryTouchEnd.bind(this), { passive: false });
        }
        
        // Button events
        if (this.elements.submitMappingBtn) {
            this.elements.submitMappingBtn.addEventListener('click', this.submitMapping.bind(this));
        }
        
        const saveMappingBtn = document.getElementById('saveMappingBtn');
        if (saveMappingBtn) {
            saveMappingBtn.addEventListener('click', this.saveMappingProgress.bind(this));
        }
        
        // TODO: Implement submitForReview and editMapping methods if needed
        // if (this.elements.submitForReviewBtn && this.submitForReview) {
        //     this.elements.submitForReviewBtn.addEventListener('click', this.submitForReview.bind(this));
        // }
        
        // if (this.elements.editMappingBtn && this.editMapping) {
        //     this.elements.editMappingBtn.addEventListener('click', this.editMapping.bind(this));
        // }
        
        // Search/filter events
        const searchInput = document.getElementById('searchInput');
        if (searchInput) {
            searchInput.addEventListener('input', this.filterAccounts.bind(this));
        }
        
        // Keyboard navigation
        document.addEventListener('keydown', this.handleKeyDown.bind(this));
    }

    // Enhanced Drag and Drop Handlers
    handleDragStart(e) {
        const accountEl = e.target.closest('.unmapped-account, .mapped-account');
        if (!accountEl) return;
        
        this.state.isDragging = true;
        this.state.draggedAccount = {
            id: accountEl.dataset.accountId,
            element: accountEl,
            sourceType: accountEl.classList.contains('unmapped-account') ? 'unmapped' : 'mapped'
        };
        
        accountEl.classList.add('dragging');
        
        // Set drag data
        e.dataTransfer.effectAllowed = 'move';
        e.dataTransfer.setData('text/plain', this.state.draggedAccount.id);
        e.dataTransfer.setData('sourceType', this.state.draggedAccount.sourceType);
        
        // Update drag ghost
        const accountName = accountEl.querySelector('.account-name')?.textContent || 'Account';
        this.state.dragGhost.textContent = `📄 ${accountName}`;
        
        // Set custom drag image
        e.dataTransfer.setDragImage(this.state.dragGhost, 0, 0);
        
        // Add haptic feedback on supported devices
        if ('vibrate' in navigator) {
            navigator.vibrate(50);
        }
    }

    handleDragEnd(e) {
        this.state.isDragging = false;
        this.state.draggedAccount = null;
        
        const draggingEl = document.querySelector('.dragging');
        if (draggingEl) {
            draggingEl.classList.remove('dragging');
        }
        
        // Clear all drag-over states
        document.querySelectorAll('.drag-over').forEach(el => {
            el.classList.remove('drag-over');
        });
    }

    handleDragOver(e) {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
        
        const categoryEl = e.target.closest('.grap-category');
        if (categoryEl && this.state.isDragging) {
            // Remove previous drag-over states
            document.querySelectorAll('.drag-over').forEach(el => {
                el.classList.remove('drag-over');
            });
            
            categoryEl.classList.add('drag-over');
            
            // Highlight the drop zone
            const dropZone = categoryEl.querySelector('.mapped-accounts');
            if (dropZone) {
                dropZone.style.background = 'var(--primary-50)';
                dropZone.style.borderColor = 'var(--primary-300)';
            }
        }
    }

    handleDrop(e) {
        e.preventDefault();
        
        const categoryEl = e.target.closest('.grap-category');
        if (!categoryEl || !this.state.draggedAccount) return;
        
        categoryEl.classList.remove('drag-over');
        
        // Reset drop zone styling
        const dropZone = categoryEl.querySelector('.mapped-accounts');
        if (dropZone) {
            dropZone.style.background = '';
            dropZone.style.borderColor = '';
        }
        
        const categoryId = categoryEl.dataset.categoryId;
        const accountId = this.state.draggedAccount.id;
        
        this.addMapping(accountId, categoryId);
        
        // Haptic feedback
        if ('vibrate' in navigator) {
            navigator.vibrate([50, 50, 100]);
        }
    }

    // Touch Event Handlers for Mobile
    handleTouchStart(e) {
        const accountEl = e.target.closest('.unmapped-account, .mapped-account');
        if (!accountEl) return;
        
        const touch = e.touches[0];
        this.state.touchStartX = touch.clientX;
        this.state.touchStartY = touch.clientY;
        this.state.draggedElement = accountEl;
        
        accountEl.classList.add('dragging');
        
        // Prevent default scrolling
        e.preventDefault();
    }

    handleTouchMove(e) {
        if (!this.state.draggedElement) return;
        
        const touch = e.touches[0];
        const deltaX = touch.clientX - this.state.touchStartX;
        const deltaY = touch.clientY - this.state.touchStartY;
        
        // Check if it's a drag (more than 10px movement)
        if (Math.abs(deltaX) > 10 || Math.abs(deltaY) > 10) {
            // Create visual feedback
            this.createTouchFeedback(touch.clientX, touch.clientY);
            
            // Prevent scrolling
            e.preventDefault();
        }
    }

    handleTouchEnd(e) {
        if (!this.state.draggedElement) return;
        
        const touch = e.changedTouches[0];
        const targetElement = document.elementFromPoint(touch.clientX, touch.clientY);
        
        // Remove dragging class
        this.state.draggedElement.classList.remove('dragging');
        
        // Check if dropped on a category
        const categoryEl = targetElement?.closest('.grap-category');
        if (categoryEl) {
            const accountId = this.state.draggedElement.dataset.accountId;
            const categoryId = categoryEl.dataset.categoryId;
            this.addMapping(accountId, categoryId);
        }
        
        // Clean up
        this.removeTouchFeedback();
        this.state.draggedElement = null;
        
        e.preventDefault();
    }

    handleCategoryTouchMove(e) {
        if (!this.state.isDragging) return;
        
        const touch = e.touches[0];
        const categoryEl = e.target.closest('.grap-category');
        
        if (categoryEl) {
            // Remove previous drag-over states
            document.querySelectorAll('.drag-over').forEach(el => {
                el.classList.remove('drag-over');
            });
            
            categoryEl.classList.add('drag-over');
        }
        
        e.preventDefault();
    }

    handleCategoryTouchEnd(e) {
        if (!this.state.isDragging) return;
        
        const touch = e.changedTouches[0];
        const categoryEl = e.target.closest('.grap-category');
        
        if (categoryEl && this.state.draggedAccount) {
            const categoryId = categoryEl.dataset.categoryId;
            const accountId = this.state.draggedAccount.id;
            this.addMapping(accountId, categoryId);
        }
        
        // Clear drag states
        document.querySelectorAll('.drag-over').forEach(el => {
            el.classList.remove('drag-over');
        });
        
        this.state.isDragging = false;
        this.state.draggedAccount = null;
    }

    createTouchFeedback(x, y) {
        // Remove existing feedback
        this.removeTouchFeedback();
        
        const feedback = document.createElement('div');
        feedback.className = 'touch-feedback';
        feedback.style.cssText = `
            position: fixed;
            left: ${x}px;
            top: ${y}px;
            width: 60px;
            height: 60px;
            background: var(--primary-600);
            color: white;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 24px;
            z-index: 1000;
            pointer-events: none;
            transform: translate(-50%, -50%);
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            animation: touchPulse 0.6s ease-in-out infinite;
        `;
        feedback.textContent = '📄';
        
        document.body.appendChild(feedback);
        this.state.touchFeedback = feedback;
    }

    removeTouchFeedback() {
        if (this.state.touchFeedback) {
            this.state.touchFeedback.remove();
            this.state.touchFeedback = null;
        }
    }

    // Keyboard Navigation
    handleKeyDown(e) {
        if (!this.state.draggedAccount) return;
        
        // Escape key to cancel drag
        if (e.key === 'Escape') {
            this.cancelDrag();
        }
        
        // Arrow keys for navigation
        if (e.key === 'ArrowDown' || e.key === 'ArrowUp' || e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
            this.navigateWithKeyboard(e);
        }
    }

    navigateWithKeyboard(e) {
        const focusedElement = document.activeElement;
        const accounts = Array.from(document.querySelectorAll('.unmapped-account, .mapped-account'));
        const currentIndex = accounts.indexOf(focusedElement);
        
        let nextIndex = currentIndex;
        
        switch (e.key) {
            case 'ArrowDown':
            case 'ArrowRight':
                nextIndex = (currentIndex + 1) % accounts.length;
                break;
            case 'ArrowUp':
            case 'ArrowLeft':
                nextIndex = currentIndex === 0 ? accounts.length - 1 : currentIndex - 1;
                break;
        }
        
        if (nextIndex !== currentIndex && accounts[nextIndex]) {
            accounts[nextIndex].focus();
            e.preventDefault();
        }
    }

    cancelDrag() {
        if (this.state.draggedElement) {
            this.state.draggedElement.classList.remove('dragging');
            this.state.draggedElement = null;
        }
        
        this.removeTouchFeedback();
        this.state.isDragging = false;
        this.state.draggedAccount = null;
        
        // Clear all drag-over states
        document.querySelectorAll('.drag-over').forEach(el => {
            el.classList.remove('drag-over');
        });
    }

    async loadGRAPCategories() {
        try {
            console.log('🔄 Loading GRAP categories for session:', this.state.sessionId);
            
            const response = await fetch(`/api/grap-categories/${this.state.sessionId}`);
            console.log('📡 API Response status:', response.status);
            
            const result = await response.json();
            console.log('📊 API Response data:', result);
            
            if (result.categories && Array.isArray(result.categories)) {
                this.state.grapCategories = result.categories;
                console.log('✅ Categories loaded:', this.state.grapCategories.length);
                console.log('📋 Categories:', this.state.grapCategories);
                this.renderCategories();
                
                // Update category count
                if (this.elements.categoryCount) {
                    this.elements.categoryCount.textContent = `${this.state.grapCategories.length} categories`;
                }
            } else if (result.error) {
                console.error('❌ API Error:', result.error);
                this.showError(result.error);
            } else {
                console.error('❌ Unexpected response format:', result);
                this.showError('Unexpected response format from server');
            }
        } catch (error) {
            console.error('💥 Network Error:', error);
            this.showError('Failed to load GRAP categories. Please try again.');
        }
    }

    async loadUnmappedAccounts() {
        try {
            console.log('🔄 Loading unmapped accounts for session:', this.state.sessionId);
            
            const response = await fetch(`/api/unmapped-accounts/${this.state.sessionId}`);
            console.log('📡 Unmapped accounts API status:', response.status);
            
            const result = await response.json();
            console.log('📊 Unmapped accounts API response:', result);
            
            if (result.success) {
                this.state.unmappedAccounts = result.accounts || [];
                this.state.mappedAccounts = result.mapped_accounts || {};
                
                console.log('✅ Unmapped accounts loaded:', this.state.unmappedAccounts.length);
                console.log('📋 Unmapped accounts:', this.state.unmappedAccounts);
                console.log('📋 Mapped accounts:', this.state.mappedAccounts);
                
                this.renderUnmappedAccounts();
                this.updateStats();
                
                // Update unmapped count
                if (this.elements.unmappedCount) {
                    this.elements.unmappedCount.textContent = `${this.state.unmappedAccounts.length} accounts`;
                }
            } else {
                console.error('❌ Unmapped accounts API Error:', result.error);
                this.showError(result.error || 'Failed to load accounts');
            }
        } catch (error) {
            console.error('💥 Unmapped accounts Network Error:', error);
            this.showError('Failed to load accounts. Please try again.');
        }
    }

    renderCategories() {
        if (!this.elements.grapCategories) return;
        
        this.elements.grapCategories.innerHTML = '';
        
        this.state.grapCategories.forEach(category => {
            const categoryEl = document.createElement('div');
            categoryEl.className = 'grap-category';
            categoryEl.dataset.categoryId = category.code;
            categoryEl.setAttribute('tabindex', '0');
            categoryEl.setAttribute('role', 'button');
            categoryEl.setAttribute('aria-label', `GRAP Category: ${category.name}`);
            
            categoryEl.innerHTML = `
                <div class="category-header">
                    <h3>${category.name}</h3>
                    <span class="category-code">${category.code}</span>
                </div>
                <div class="mapped-accounts" data-category="${category.code}">
                    ${this.renderMappedAccounts(category.code)}
                </div>
            `;
            
            // Add keyboard event listeners
            categoryEl.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    categoryEl.querySelector('.mapped-accounts').focus();
                }
            });
            
            this.elements.grapCategories.appendChild(categoryEl);
        });
    }

    renderMappedAccounts(categoryId) {
        const mappedAccounts = this.state.mappedAccounts[categoryId] || [];
        
        if (mappedAccounts.length === 0) {
            return '<div class="empty-category">Drop accounts here</div>';
        }
        
        return mappedAccounts.map(account => {
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
            
            const accountName = account.account_desc || account.name || 'Unknown Account';
            const accountCode = account.account_code || account.code || '';
            const accountAmount = account.net_balance || account.amount || 0;
            const accountId = account.id || account.account_code || 'unknown';
            
            return `
                <div class="mapped-account" data-account-id="${accountId}" draggable="true" tabindex="0" role="button" aria-label="Account: ${accountName}">
                    <div class="account-info">
                        <div class="account-name">${accountName}</div>
                        <div class="account-code">${accountCode}</div>
                        <div class="account-amount">${this.formatCurrency(accountAmount)}</div>
                    </div>
                    <div class="confidence-score ${confidenceClass}">
                        <span class="confidence-label">${confidenceLabel}</span>
                        <span class="confidence-value">${Math.round(confidence * 100)}%</span>
                    </div>
                    <button class="remove-account" onclick="window.mappingInterface.removeMapping('${accountId}')" aria-label="Remove account">×</button>
                </div>
            `;
        }).join('');
    }

    renderUnmappedAccounts() {
        if (!this.elements.unmappedAccountsList) return;
        
        this.elements.unmappedAccountsList.innerHTML = '';
        
        if (this.state.unmappedAccounts.length === 0) {
            this.elements.unmappedAccountsList.innerHTML = '<div class="no-accounts">No accounts to map</div>';
            return;
        }
        
        this.state.unmappedAccounts.forEach((account, index) => {
            const accountEl = document.createElement('div');
            accountEl.className = 'unmapped-account';
            accountEl.draggable = true;
            accountEl.dataset.accountId = account.id || account.account_code || index.toString();
            accountEl.setAttribute('tabindex', '0');
            accountEl.setAttribute('role', 'button');
            accountEl.setAttribute('aria-label', `Unmapped account: ${account.account_desc || account.name}`);
            
            accountEl.innerHTML = `
                <div class="account-name">${account.account_desc || account.name || 'Unknown Account'}</div>
                <div class="account-code">${account.account_code || account.code || ''}</div>
                <div class="account-amount">${this.formatCurrency(account.net_balance || account.amount || 0)}</div>
                <div class="account-description">${account.account_desc || account.description || ''}</div>
            `;
            
            // Add keyboard event listener
            accountEl.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    this.startKeyboardDrag(accountEl);
                }
            });
            
            this.elements.unmappedAccountsList.appendChild(accountEl);
        });
    }

    startKeyboardDrag(element) {
        this.state.draggedAccount = {
            id: element.dataset.accountId,
            element: element,
            sourceType: 'unmapped'
        };
        
        element.classList.add('dragging');
        this.showNotification('Use arrow keys to navigate to a category, then press Enter to drop', 'info');
    }

    addMapping(accountId, categoryId) {
        try {
            const account = this.state.unmappedAccounts.find(a => 
                a.account_code === accountId || a.id === accountId);
            
            if (account) {
                // Remove from unmapped
                this.state.unmappedAccounts = this.state.unmappedAccounts.filter(a => 
                    a.account_code !== accountId && a.id !== accountId);
                
                // Add to mapped
                if (!this.state.mappedAccounts[categoryId]) {
                    this.state.mappedAccounts[categoryId] = [];
                }
                this.state.mappedAccounts[categoryId].push(account);
                
                // Update UI
                this.renderUnmappedAccounts();
                this.renderCategories();
                this.updateStats();
                
                this.showSuccess(`Account "${account.account_desc}" mapped to ${categoryId}`);
            } else {
                this.showError('Account not found for mapping.');
            }
        } catch (error) {
            this.showError('Failed to add mapping. Please try again.');
        }
    }

    removeMapping(accountId) {
        try {
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
                
                this.showSuccess('Account removed from mapping');
            }
        } catch (error) {
            this.showError('Failed to remove mapping. Please try again.');
        }
    }

    updateStats() {
        const totalAccounts = this.state.unmappedAccounts.length + this.getTotalMappedAccounts();
        const mappedAccounts = this.getTotalMappedAccounts();
        const remainingAccounts = this.state.unmappedAccounts.length;
        const completionPercentage = totalAccounts > 0 ? 
            Math.round((mappedAccounts / totalAccounts) * 100) : 0;

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

        // Update submit button
        this.updateSubmitButton();
        
        // Check if mapping is complete
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

    checkMappingCompletion() {
        const unmappedCount = this.state.unmappedAccounts.length;
        const submissionStatus = this.elements.submissionStatus;
        
        if (submissionStatus) {
            if (unmappedCount === 0) {
                submissionStatus.classList.remove('display-none');
                this.updateReviewStatus();
            } else {
                submissionStatus.classList.add('display-none');
            }
        }
    }

    updateReviewStatus() {
        const statusBadge = this.elements.statusBadge;
        const statusMessage = this.elements.statusMessage;
        
        if (statusBadge) {
            statusBadge.textContent = 'Ready for Review';
            statusBadge.className = 'status-badge';
            statusBadge.style.background = 'var(--success)';
            statusBadge.style.color = 'var(--white)';
        }
        
        if (statusMessage) {
            statusMessage.textContent = 'All accounts have been mapped. You can now submit for manager review.';
        }
    }

    updateConfidenceSummary() {
        // Implementation for confidence summary would go here
        // This would calculate and display confidence statistics
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
        notification.setAttribute('role', 'alert');
        notification.setAttribute('aria-live', 'polite');
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.remove();
        }, 3000);
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

    getMappedDataForSubmission() {
        const mappedData = {};
        
        for (const [categoryId, accounts] of Object.entries(this.state.mappedAccounts)) {
            mappedData[categoryId] = accounts.map(account => ({
                id: account.id,
                name: account.name,
                code: account.code,
                amount: account.amount,
                confidence: account.confidence
            }));
        }
        
        return mappedData;
    }

    async saveMappingProgress() {
        try {
            const mappedData = this.getMappedDataForSubmission();
            
            const response = await fetch('/api/save-mapping-progress', {
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
                this.showSuccess('Mapping progress saved successfully');
            } else {
                this.showError(result.error || 'Failed to save mapping progress');
            }
        } catch (error) {
            this.showError('Failed to save mapping progress. Please try again.');
        }
    }
}

// Add custom CSS for touch feedback
const touchFeedbackStyles = `
    @keyframes touchPulse {
        0%, 100% { transform: translate(-50%, -50%) scale(1); }
        50% { transform: translate(-50%, -50%) scale(1.1); }
    }
    
    .touch-feedback {
        animation: touchPulse 0.6s ease-in-out infinite;
    }
    
    .drag-ghost {
        transition: none !important;
    }
`;

// Inject styles
const styleSheet = document.createElement('style');
styleSheet.textContent = touchFeedbackStyles;
document.head.appendChild(styleSheet);

// Initialize the enhanced interface immediately or when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        if (window.sessionId) {
            console.log('📋 Initializing from DOMContentLoaded event');
            window.mappingInterface = new EnhancedGRAPMappingInterface(window.sessionId);
        }
    });
} else {
    // DOM is already ready
    if (window.sessionId) {
        console.log('📋 Initializing immediately - DOM already ready');
        window.mappingInterface = new EnhancedGRAPMappingInterface(window.sessionId);
    }
}
