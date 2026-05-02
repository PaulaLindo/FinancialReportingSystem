/**
 * Draft Statement Viewer JavaScript
 * Handles draft statement viewing during Balance Sheet mapping phase
 */

// This file is already included in the draft-statement-viewer.html component
// The controller is defined in the component template
// This file serves as a reference and additional utilities

// Global functions for template integration
function openDraftStatementViewer(balanceSheetId, statementType) {
    if (window.draftStatementViewerController) {
        window.draftStatementViewerController.open(balanceSheetId, statementType);
    }
}

function closeDraftStatementViewer() {
    if (window.draftStatementViewerController) {
        window.draftStatementViewerController.close();
    }
}

function refreshDraftStatement() {
    if (window.draftStatementViewerController && window.draftStatementViewerController.currentBalanceSheet) {
        window.draftStatementViewerController.open(
            window.draftStatementViewerController.currentBalanceSheet,
            window.draftStatementViewerController.currentStatement
        );
    }
}

function exportDraftStatement() {
    if (window.draftStatementViewerController) {
        const draftData = window.draftStatementViewerController.currentData;
        if (draftData) {
            // Create export data
            const exportData = {
                statementType: draftData.statementType,
                balanceSheetId: draftData.balanceSheetId,
                period: draftData.period,
                generatedAt: new Date().toISOString(),
                data: draftData
            };
            
            // Trigger download
            const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `draft-statement-${draftData.statementType}-${new Date().toISOString().split('T')[0]}.json`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }
    }
}

function mapAccount(accountCode) {
    // Implementation would open account mapping interface
    // For now, show a simple alert
    alert(`Account mapping interface for ${accountCode} would be opened here.`);
}

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        // The controller is already initialized in the component template
    });
} else {
        // The controller is already initialized in the component template
    }
