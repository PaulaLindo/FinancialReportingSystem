/**
 * Varydian Financial Reporting System - Financial Statements Module
 * Handles financial statement table functionality and mobile card view
 */

class FinancialStatementsModule {
    constructor() {
        this.elements = {};
        this.init();
    }

    /**
     * Initialize financial statements module
     */
    init() {
        this.cacheElements();
        this.setupMobileCardView();
    }

    /**
     * Cache DOM elements
     */
    cacheElements() {
        this.elements = {
            financialTables: document.querySelectorAll('.financial-table')
        };
    }

    /**
     * Setup mobile card view by adding data-label attributes
     */
    setupMobileCardView() {
        this.elements.financialTables.forEach(table => {
            this.addMobileCardLabels(table);
        });
    }

    /**
     * Add data-label attributes to table cells for mobile card view
     */
    addMobileCardLabels(table) {
        if (!table) return;
        
        const headers = Array.from(table.querySelectorAll('th')).map(th => th.textContent.trim());
        const rows = table.querySelectorAll('tbody tr');
        
        rows.forEach(row => {
            const cells = row.querySelectorAll('td');
            cells.forEach((cell, index) => {
                if (headers[index]) {
                    cell.setAttribute('data-label', headers[index]);
                }
            });
        });
    }

    /**
     * Cleanup method
     */
    destroy() {
        // Cleanup if needed
    }
}

// Initialize financial statements module when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.financialStatementsModule = new FinancialStatementsModule();
});

// Handle page unload for cleanup
window.addEventListener('beforeunload', () => {
    if (window.financialStatementsModule) {
        window.financialStatementsModule.destroy();
    }
});
