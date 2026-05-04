/**
 * Document Type Selector
 * Handles document type selection and dynamic UI updates
 */

class DocumentTypeSelector {
    constructor() {
        this.selectedType = null;
        this.documentTypes = {
            balance_sheet: {
                title: 'Upload Balance Sheet',
                subtitle: 'Import your Balance Sheet from Pastel or Excel to generate GRAP-compliant financial statements',
                requirements: [
                    'Must contain columns: Account Code, Account Description, Debit Balance, Credit Balance',
                    'File format: Excel (.xlsx, .xls) or CSV (.csv)',
                    'Maximum file size: 16MB',
                    'Balance Sheet must be balanced (Total Debits = Total Credits)'
                ],
                accept: '.xlsx,.xls,.csv'
            },
            income_statement: {
                title: 'Upload Income Statement',
                subtitle: 'Import your Income Statement to generate GRAP-compliant financial performance reports',
                requirements: [
                    'Must contain columns: Account Description, Revenue/Expense Amounts',
                    'File format: Excel (.xlsx, .xls) or CSV (.csv)',
                    'Maximum file size: 16MB',
                    'Revenue and expenses should be clearly categorized',
                    'Period information should be included (monthly, quarterly, or annual)'
                ],
                accept: '.xlsx,.xls,.csv'
            },
            budget_report: {
                title: 'Upload Budget Report',
                subtitle: 'Import your Budget vs Actual report for variance analysis and GRAP compliance',
                requirements: [
                    'Must contain columns: Budget Amount, Actual Amount, Variance',
                    'File format: Excel (.xlsx, .xls) or CSV (.csv)',
                    'Maximum file size: 16MB',
                    'Department or expense categories should be clearly identified',
                    'Budget and actual periods should align'
                ],
                accept: '.xlsx,.xls,.csv'
            }
        };
        
        this.init();
    }
    
    init() {
        this.bindEvents();
        this.setupInitialState();
    }
    
    bindEvents() {
        // Card click events
        document.querySelectorAll('.document-type-card').forEach(card => {
            card.addEventListener('click', (e) => this.handleCardClick(e));
            card.addEventListener('keydown', (e) => this.handleCardKeydown(e));
        });
        
        // Form submission validation
        const uploadForm = document.querySelector('#uploadForm');
        if (uploadForm) {
            uploadForm.addEventListener('submit', (e) => this.handleFormSubmit(e));
        }
    }
    
    setupInitialState() {
        console.log('🚀 Setting up initial state for document type selector');
        // Set balance sheet as default selection
        const balanceSheetCard = document.querySelector('[data-type="balance_sheet"]');
        if (balanceSheetCard) {
            console.log('📊 Found balance sheet card, setting as default');
            this.selectDocumentType('balance_sheet');
        } else {
            console.log('❌ Balance sheet card not found');
        }
    }
    
    handleCardClick(e) {
        const card = e.currentTarget;
        const documentType = card.dataset.type;
        
        if (documentType) {
            this.selectDocumentType(documentType);
        }
    }
    
    handleCardKeydown(e) {
        if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            const card = e.currentTarget;
            const documentType = card.dataset.type;
            
            if (documentType) {
                this.selectDocumentType(documentType);
            }
        }
    }
    
    selectDocumentType(documentType) {
        console.log('🎯 Selecting document type:', documentType);
        
        // Update selected type
        this.selectedType = documentType;
        
        // Update card states
        document.querySelectorAll('.document-type-card').forEach(card => {
            card.classList.remove('selected');
        });
        
        const selectedCard = document.querySelector(`[data-type="${documentType}"]`);
        if (selectedCard) {
            selectedCard.classList.add('selected');
            selectedCard.classList.add('selecting');
            
            // Remove animation class after animation completes
            setTimeout(() => {
                selectedCard.classList.remove('selecting');
            }, 300);
        }
        
        // Update UI elements
        this.updateUIForDocumentType(documentType);
        
        // Update current selection indicator
        this.updateCurrentSelectionIndicator(documentType);
        
        // Update file input accept attribute
        this.updateFileInput(documentType);
        
        // Emit custom event
        this.emitSelectionChange(documentType);
    }
    
    updateUIForDocumentType(documentType) {
        const config = this.documentTypes[documentType];
        
        if (!config) return;
        
        // Update page title
        const pageTitle = document.getElementById('pageTitle');
        if (pageTitle) {
            pageTitle.textContent = config.title;
        }
        
        // Update page subtitle
        const pageSubtitle = document.getElementById('pageSubtitle');
        if (pageSubtitle) {
            pageSubtitle.textContent = config.subtitle;
        }
        
        // Update requirements
        const requirementsTitle = document.getElementById('requirementsTitle');
        if (requirementsTitle) {
            const typeNames = {
                balance_sheet: 'Balance Sheet',
                income_statement: 'Income Statement',
                budget_report: 'Budget Report'
            };
            requirementsTitle.textContent = `${typeNames[documentType]} Requirements`;
        }
        
        // Update requirements list
        const requirementsList = document.getElementById('requirementsList');
        if (requirementsList) {
            requirementsList.innerHTML = '';
            config.requirements.forEach(requirement => {
                const li = document.createElement('li');
                li.textContent = requirement;
                requirementsList.appendChild(li);
            });
        }
        
        // Update upload box text
        const uploadBox = document.querySelector('#uploadBox h3');
        if (uploadBox) {
            const typeNames = {
                balance_sheet: 'Balance Sheet',
                income_statement: 'Income Statement',
                budget_report: 'Budget Report'
            };
            uploadBox.textContent = `Drag & Drop Your ${typeNames[documentType]} Here`;
        }
    }
    
    updateFileInput(documentType) {
        const config = this.documentTypes[documentType];
        const fileInput = document.getElementById('fileInput');
        
        if (fileInput && config) {
            fileInput.accept = config.accept;
        }
    }
    
    handleFormSubmit(e) {
        if (!this.selectedType) {
            e.preventDefault();
            this.showSelectionError();
            return false;
        }
        
        // Add document type to form data
        const formData = new FormData(e.target);
        formData.append('document_type', this.selectedType);
        
        return true;
    }
    
    showSelectionError() {
        const firstCard = document.querySelector('.document-type-card');
        if (firstCard) {
            firstCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
            firstCard.classList.add('error');
            
            setTimeout(() => {
                firstCard.classList.remove('error');
            }, 2000);
        }
        
        // Show error message
        this.showNotification('Please select a document type before uploading', 'error');
    }
    
    showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification notification--${type}`;
        notification.textContent = message;
        
        // Add to page
        document.body.appendChild(notification);
        
        // Show notification
        setTimeout(() => {
            notification.classList.add('notification--show');
        }, 100);
        
        // Hide after delay
        setTimeout(() => {
            notification.classList.remove('notification--show');
            setTimeout(() => {
                document.body.removeChild(notification);
            }, 300);
        }, 3000);
    }
    
    updateCurrentSelectionIndicator(documentType) {
        const currentTypeElement = document.getElementById('currentDocumentType');
        if (currentTypeElement) {
            const typeNames = {
                'balance_sheet': 'Balance Sheet',
                'income_statement': 'Income Statement',
                'budget_report': 'Budget Report'
            };
            currentTypeElement.textContent = typeNames[documentType] || documentType;
        }
    }
    
    emitSelectionChange(documentType) {
        const event = new CustomEvent('documentTypeSelected', {
            detail: { documentType }
        });
        document.dispatchEvent(event);
    }
    
    // Public methods
    getSelectedType() {
        console.log('🔍 getSelectedType called, returning:', this.selectedType);
        return this.selectedType;
    }
    
    setSelectedType(documentType) {
        if (this.documentTypes[documentType]) {
            this.selectDocumentType(documentType);
        }
    }
    
    reset() {
        this.selectedType = null;
        document.querySelectorAll('.document-type-card').forEach(card => {
            card.classList.remove('selected', 'error', 'loading', 'success');
        });
        
        // Reset to balance sheet
        this.selectDocumentType('balance_sheet');
    }
    
    setLoading(loading = true) {
        const selectedCard = document.querySelector('.document-type-card.selected');
        if (selectedCard) {
            if (loading) {
                selectedCard.classList.add('loading');
            } else {
                selectedCard.classList.remove('loading');
            }
        }
    }
    
    setSuccess(success = true) {
        const selectedCard = document.querySelector('.document-type-card.selected');
        if (selectedCard) {
            if (success) {
                selectedCard.classList.add('success');
                setTimeout(() => {
                    selectedCard.classList.remove('success');
                }, 2000);
            } else {
                selectedCard.classList.add('error');
                setTimeout(() => {
                    selectedCard.classList.remove('error');
                }, 2000);
            }
        }
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    console.log('🎯 Initializing document type selector');
    window.documentTypeSelector = new DocumentTypeSelector();
    console.log('✅ Document type selector initialized');
});

// Export for global access
window.DocumentTypeSelector = DocumentTypeSelector;
