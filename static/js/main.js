/**
 * Varydian Financial Reporting System - Main Application
 * Refactored main JavaScript with modular architecture
 */

class MainApplication {
    constructor() {
        this.elements = {};
        this.observers = {};
        this.init();
    }

    /**
     * Initialize the application
     */
    init() {
        this.cacheElements();
        this.setupEventListeners();
        this.setupIntersectionObservers();
        this.setupScrollEffects();
        this.setupAnimations();
        VarydianUtils.showBranding();
    }

    /**
     * Cache DOM elements
     */
    cacheElements() {
        this.elements = {
            navLinks: document.querySelectorAll('a[href^="#"]'),
            sections: document.querySelectorAll('section[id]'),
            navbar: document.querySelector('.navbar'),
            featureCards: document.querySelectorAll('.feature-card'),
            screenshotCards: document.querySelectorAll('.screenshot-card'),
            workflowSteps: document.querySelectorAll('.workflow-step'),
            stats: document.querySelectorAll('.stat-number'),
            pricingCards: document.querySelectorAll('.pricing-card'),
            pricingSection: document.querySelector('.pricing-section'),
            playButton: document.querySelector('.play-button'),
            screenshotPlaceholders: document.querySelectorAll('.screenshot-placeholder'),
            hero: document.querySelector('.hero'),
            // About page collapsible headers
            problemBoxHeaders: document.querySelectorAll('.problem-box h3'),
            solutionBoxHeaders: document.querySelectorAll('.solution-box h3')
        };
    }

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        this.setupNavigation();
        this.setupPlayButton();
        this.setupHoverEffects();
        this.setupPricingCards();
        this.setupCollapsibleHeaders();
    }

    /**
     * Setup navigation functionality
     */
    setupNavigation() {
        // Smooth scroll for navigation links
        this.elements.navLinks.forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const targetId = link.getAttribute('href');
                
                // Only process if it's an anchor link (starts with #)
                if (targetId && targetId.startsWith('#')) {
                    const targetSection = document.querySelector(targetId);
                    
                    if (targetSection) {
                        VarydianUtils.scrollToElement(targetSection);
                        this.updateActiveNavLink(link);
                    }
                } else if (targetId && !targetId.startsWith('#')) {
                    // For regular links (like /download/*), let them work normally
                    window.location.href = targetId;
                }
            });
        });
    }

    /**
     * Update active navigation link
     */
    updateActiveNavLink(activeLink) {
        this.elements.navLinks.forEach(link => link.classList.remove('active'));
        activeLink.classList.add('active');
    }

    /**
     * Setup intersection observers
     */
    setupIntersectionObservers() {
        this.setupFadeInObserver();
        this.setupNavigationObserver();
        this.setupStatsObserver();
        this.setupPricingObserver();
    }

    /**
     * Setup fade-in animation observer
     */
    setupFadeInObserver() {
        this.observers.fadeIn = VarydianUtils.createIntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    VarydianUtils.addFadeInAnimation([entry.target]);
                    this.observers.fadeIn.unobserve(entry.target);
                }
            });
        });

        // Observe elements
        [...this.elements.featureCards, ...this.elements.screenshotCards, ...this.elements.workflowSteps]
            .forEach((element, index) => {
                element.classList.add(`fade-in-element--delay-${Math.min(index + 1, 5)}`);
                this.observers.fadeIn.observe(element);
            });
    }

    /**
     * Setup navigation observer for active section highlighting
     */
    setupNavigationObserver() {
        this.observers.navigation = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const currentId = entry.target.getAttribute('id');
                    const activeLink = document.querySelector(`a[href="#${currentId}"]`);
                    if (activeLink) {
                        this.updateActiveNavLink(activeLink);
                    }
                }
            });
        }, { threshold: 0.3 });

        this.elements.sections.forEach(section => {
            this.observers.navigation.observe(section);
        });
    }

    /**
     * Setup stats counter observer
     */
    setupStatsObserver() {
        this.observers.stats = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const target = entry.target;
                    const finalValue = target.textContent;
                    
                    if (!isNaN(parseInt(finalValue))) {
                        VarydianUtils.animateCounter(target, finalValue);
                    }
                    
                    this.observers.stats.unobserve(target);
                }
            });
        }, { threshold: 0.5 });

        this.elements.stats.forEach(stat => {
            this.observers.stats.observe(stat);
        });
    }

    /**
     * Setup pricing section observer
     */
    setupPricingObserver() {
        if (!this.elements.pricingSection) return;

        this.observers.pricing = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const cards = entry.target.querySelectorAll('.pricing-card');
                    cards.forEach((card, index) => {
                        setTimeout(() => {
                            card.classList.add('fade-in-element--animated');
                            card.classList.remove('fade-in-element--initial');
                        }, index * 200);
                    });
                    this.observers.pricing.unobserve(entry.target);
                }
            });
        }, { threshold: 0.2 });

        this.observers.pricing.observe(this.elements.pricingSection);
        this.initializePricingCards();
    }

    /**
     * Initialize pricing cards
     */
    initializePricingCards() {
        if (!this.elements.pricingSection) return;

        const cards = this.elements.pricingSection.querySelectorAll('.pricing-card');
        cards.forEach(card => {
            if (!card.classList.contains('featured')) {
                card.classList.add('fade-in-element--initial');
                card.classList.remove('fade-in-element--animated');
            }
        });
    }

    /**
     * Setup scroll effects
     */
    setupScrollEffects() {
        let lastScroll = 0;

        window.addEventListener('scroll', VarydianUtils.throttle(() => {
            this.handleNavbarShadow();
            this.handleParallax();
            lastScroll = window.pageYOffset;
        }, 16)); // ~60fps
    }

    /**
     * Handle navbar shadow on scroll
     */
    handleNavbarShadow() {
        if (!this.elements.navbar) return;
        
        const currentScroll = window.pageYOffset;
        
        if (currentScroll > 100) {
            this.elements.navbar.classList.add('navbar--scrolled');
            this.elements.navbar.classList.remove('navbar--default');
        } else {
            this.elements.navbar.classList.add('navbar--default');
            this.elements.navbar.classList.remove('navbar--scrolled');
        }
    }

    /**
     * Handle parallax effect for hero section
     */
    handleParallax() {
        if (!this.elements.hero) return;
        
        const scrolled = window.pageYOffset;
        const parallax = scrolled * 0.5;
        this.elements.hero.classList.add('hero--parallax');
    }

    /**
     * Setup animations
     */
    setupAnimations() {
        // Additional animations can be added here
    }

    /**
     * Setup play button functionality
     */
    setupPlayButton() {
        if (!this.elements.playButton) return;

        this.elements.playButton.addEventListener('click', () => {
            const placeholder = this.elements.playButton.parentElement;
            placeholder.innerHTML = `
                <div class="demo-video-content">
                    <h3 class="demo-video-title">Demo Video</h3>
                    <p class="demo-video-text">
                        Live demonstration will be recorded and uploaded here after the February 3, 2026 presentation.
                    </p>
                    <p class="demo-video-subtext">
                        For now, please <a href="#contact" class="demo-video-link">contact us</a> 
                        to schedule a personalized live demo.
                    </p>
                </div>
            `;
        });
    }

    /**
     * Setup hover effects
     */
    setupHoverEffects() {
        // Screenshot placeholders
        this.elements.screenshotPlaceholders.forEach(placeholder => {
            placeholder.addEventListener('mouseenter', () => {
                placeholder.classList.add('screenshot-placeholder--hover');
                placeholder.classList.remove('screenshot-placeholder--default');
            });
            
            placeholder.addEventListener('mouseleave', () => {
                placeholder.classList.add('screenshot-placeholder--default');
                placeholder.classList.remove('screenshot-placeholder--hover');
            });
        });
    }

    /**
     * Setup pricing card hover effects
     */
    setupPricingCards() {
        this.elements.pricingCards.forEach(card => {
            card.addEventListener('mouseenter', () => {
                if (!card.classList.contains('featured')) {
                    card.classList.add('pricing-card--hover');
                    card.classList.remove('pricing-card--default');
                }
            });
            
            card.addEventListener('mouseleave', () => {
                if (!card.classList.contains('featured')) {
                    card.classList.add('pricing-card--default');
                    card.classList.remove('pricing-card--hover');
                }
            });
        });
    }

    /**
     * Setup collapsible headers for About page problem/solution boxes
     */
    setupCollapsibleHeaders() {
        const allHeaders = [...this.elements.problemBoxHeaders, ...this.elements.solutionBoxHeaders];
        
        allHeaders.forEach(header => {
            header.addEventListener('click', () => {
                this.toggleCollapsibleSection(header);
            });
        });
    }

    /**
     * Toggle collapsible section
     */
    toggleCollapsibleSection(header) {
        const isCollapsed = header.classList.contains('collapsed');
        const ul = header.nextElementSibling;
        
        if (isCollapsed) {
            // Expand
            header.classList.remove('collapsed');
            ul.classList.remove('collapsed');
        } else {
            // Collapse
            header.classList.add('collapsed');
            ul.classList.add('collapsed');
        }
    }

    /**
     * Cleanup method
     */
    destroy() {
        // Disconnect all observers
        Object.values(this.observers).forEach(observer => {
            if (observer && observer.disconnect) {
                observer.disconnect();
            }
        });
    }
}

/**
 * Event Delegation System
 * Handles all data-action events from HTML templates
 */
class EventDelegationSystem {
    constructor() {
        this.actionHandlers = new Map();
        this.init();
    }

    init() {
        this.setupEventDelegation();
        this.registerHandlers();
    }

    /**
     * Setup event delegation on document
     */
    setupEventDelegation() {
        document.addEventListener('click', this.handleClick.bind(this));
        document.addEventListener('change', this.handleChange.bind(this));
        document.addEventListener('submit', this.handleSubmit.bind(this));
    }

    /**
     * Handle click events
     */
    handleClick(event) {
        const element = event.target.closest('[data-action]');
        if (!element) return;

        const action = element.dataset.action;
        const data = this.getElementData(element);
        
        this.executeAction(action, data, element, event);
    }

    /**
     * Handle change events
     */
    handleChange(event) {
        const element = event.target.closest('[data-action]');
        if (!element) return;

        const action = element.dataset.action;
        const data = this.getElementData(element);
        
        this.executeAction(action, data, element, event);
    }

    /**
     * Handle submit events
     */
    handleSubmit(event) {
        const element = event.target.closest('[data-action]');
        if (!element) return;

        const action = element.dataset.action;
        const data = this.getElementData(element);
        
        this.executeAction(action, data, element, event);
    }

    /**
     * Get all data attributes from element
     */
    getElementData(element) {
        const data = {};
        for (const attr of element.attributes) {
            if (attr.name.startsWith('data-')) {
                const key = attr.name.replace('data-', '').replace(/-([a-z])/g, (match, letter) => letter.toUpperCase());
                data[key] = attr.value;
            }
        }
        return data;
    }

    /**
     * Execute action handler
     */
    executeAction(action, data, element, event) {
        const handler = this.actionHandlers.get(action);
        if (handler && typeof handler === 'function') {
            try {
                handler(data, element, event);
            } catch (error) {
                // Error executing action
            }
        } else {
            // No handler found for action
        }
    }

    /**
     * Register action handlers
     */
    registerHandlers() {
        // Budget page handlers
        this.registerHandler('create-budget', this.handleCreateBudget.bind(this));
        this.registerHandler('clear-form', this.handleClearForm.bind(this));
        this.registerHandler('import-actual-data', this.handleImportActualData.bind(this));
        this.registerHandler('calculate-variance', this.handleCalculateVariance.bind(this));
        this.registerHandler('export-budget-report', this.handleExportBudgetReport.bind(this));
        this.registerHandler('create-revision', this.handleCreateRevision.bind(this));
        this.registerHandler('delete-budget', this.handleDeleteBudget.bind(this));
        this.registerHandler('close-revision-modal', this.handleCloseRevisionModal.bind(this));
        this.registerHandler('submit-revision', this.handleSubmitRevision.bind(this));

        // Tab switching handlers
        this.registerHandler('show-tab', (data) => this.showTab(data.tab));

        // Approvals page handlers
        this.registerHandler('load-transaction-history', this.handleLoadTransactionHistory.bind(this));
        this.registerHandler('load-compliance-report', this.handleLoadComplianceReport.bind(this));
        this.registerHandler('export-compliance-report', this.handleExportComplianceReport.bind(this));
        this.registerHandler('close-approval-chain-modal', this.handleCloseApprovalChainModal.bind(this));

        // Formula modal handlers
        this.registerHandler('close-formula-modal', this.handleCloseFormulaModal.bind(this));
        this.registerHandler('view-source-ledger', this.handleViewSourceLedger.bind(this));
        this.registerHandler('view-raw-balance-sheet', this.handleViewRawBalanceSheet.bind(this));
        this.registerHandler('export-breakdown-pdf', this.handleExportBreakdownPDF.bind(this));

        // Draft statement viewer handlers
        this.registerHandler('refresh-draft-statement', this.handleRefreshDraftStatement.bind(this));
        this.registerHandler('export-draft-statement', this.handleExportDraftStatement.bind(this));
        this.registerHandler('close-draft-statement-viewer', this.handleCloseDraftStatementViewer.bind(this));

        // Financial statement handlers
        this.registerHandler('open-draft-statement-viewer', this.handleOpenDraftStatementViewer.bind(this));
    }

    /**
     * Register an action handler
     */
    registerHandler(action, handler) {
        this.actionHandlers.set(action, handler);
    }

    // Budget Page Handlers
    handleCreateBudget(data, element) {
        // Call existing budget functionality
        if (typeof createBudget === 'function') {
            createBudget();
        }
    }

    handleClearForm(data, element) {
        if (data.target) {
            const targetElement = document.getElementById(data.target);
            if (targetElement) {
                targetElement.value = '';
            }
        }
    }

    handleImportActualData(data, element) {
        if (typeof importActualData === 'function') {
            importActualData();
        }
    }

    handleCalculateVariance(data, element) {
        if (typeof calculateVariance === 'function') {
            calculateVariance();
        }
    }

    handleExportBudgetReport(data, element) {
        if (typeof exportBudgetReport === 'function') {
            exportBudgetReport();
        }
    }

    handleCreateRevision(data, element) {
        if (typeof createRevision === 'function') {
            createRevision();
        }
    }

    handleDeleteBudget(data, element) {
        if (typeof deleteBudget === 'function') {
            deleteBudget();
        }
    }

    handleCloseRevisionModal(data, element) {
        if (typeof closeRevisionModal === 'function') {
            closeRevisionModal();
        }
    }

    handleSubmitRevision(data, element) {
        if (typeof submitRevision === 'function') {
            submitRevision();
        }
    }

    // Tab switching
    showTab(tabName) {
        if (typeof showTab === 'function') {
            showTab(tabName);
        }
    }

    // Approvals Page Handlers
    handleLoadTransactionHistory(data, element) {
        if (window.approvalWorkflow && typeof approvalWorkflow.loadTransactionHistory === 'function') {
            approvalWorkflow.loadTransactionHistory();
        }
    }

    handleLoadComplianceReport(data, element) {
        if (window.approvalWorkflow && typeof approvalWorkflow.loadComplianceReport === 'function') {
            approvalWorkflow.loadComplianceReport();
        }
    }

    handleExportComplianceReport(data, element) {
        if (window.approvalWorkflow && typeof approvalWorkflow.exportComplianceReport === 'function') {
            approvalWorkflow.exportComplianceReport();
        }
    }

    handleCloseApprovalChainModal(data, element) {
        if (typeof closeApprovalChainModal === 'function') {
            closeApprovalChainModal();
        }
    }

    // Formula Modal Handlers
    handleCloseFormulaModal(data, element) {
        if (typeof closeFormulaModal === 'function') {
            closeFormulaModal();
        }
    }

    handleViewSourceLedger(data, element) {
        if (typeof viewSourceLedger === 'function') {
            viewSourceLedger(data.ledger);
        }
    }

    handleViewRawBalanceSheet(data, element) {
        if (typeof viewRawBalanceSheet === 'function') {
            viewRawBalanceSheet();
        }
    }

    handleExportBreakdownPDF(data, element) {
        if (typeof exportBreakdownPDF === 'function') {
            exportBreakdownPDF();
        }
    }

    // Draft Statement Viewer Handlers
    handleRefreshDraftStatement(data, element) {
        if (typeof refreshDraftStatement === 'function') {
            refreshDraftStatement();
        }
    }

    handleExportDraftStatement(data, element) {
        if (typeof exportDraftStatement === 'function') {
            exportDraftStatement();
        }
    }

    handleCloseDraftStatementViewer(data, element) {
        if (typeof closeDraftStatementViewer === 'function') {
            closeDraftStatementViewer();
        }
    }

    // Financial Statement Handlers
    handleOpenDraftStatementViewer(data, element) {
        if (typeof openDraftStatementViewer === 'function') {
            openDraftStatementViewer(data.balanceSheetId, data.statementType);
        }
    }
}

// Initialize application when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.mainApp = new MainApplication();
    window.eventDelegation = new EventDelegationSystem();
});

// Handle page unload for cleanup
window.addEventListener('beforeunload', () => {
    if (window.mainApp) {
        window.mainApp.destroy();
    }
});
