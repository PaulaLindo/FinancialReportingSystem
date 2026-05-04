/**
 * Varydian Financial Reporting System - Upload Page Initialization
 * Handles upload page-specific initialization and debug console functions
 */

// Debug Console Functions
function debugLog(message, type = 'info') {
    const debugLog = document.getElementById('debugLog');
    if (!debugLog) return;
    
    const timestamp = new Date().toLocaleTimeString();
    const colorMap = {
        'info': 'var(--info)',
        'success': 'var(--success)',
        'warning': 'var(--warning)',
        'error': 'var(--danger)',
        'lock': 'var(--warning-dark)',
        'permission': 'var(--primary)'
    };
    
    const logEntry = document.createElement('div');
    logEntry.className = `debug-log-entry debug-log-${type}`;
    logEntry.innerHTML = `<span class="debug-log-timestamp">[${timestamp}]</span> ${message}`;
    
    debugLog.appendChild(logEntry);
    debugLog.scrollTop = debugLog.scrollHeight;
}

function clearDebugConsole() {
    const debugLog = document.getElementById('debugLog');
    if (debugLog) {
        debugLog.innerHTML = '<div class="debug-log-cleared">🚀 Debug console cleared...</div>';
    }
}

// Initialize upload functionality when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    debugLog('📁 Upload page loaded', 'info');
    
    // Initialize upload service
    if (typeof window.uploadService === 'undefined') {
        // The upload service will be initialized by upload.js
    }
    
    // Initialize real-time validation when DOM is ready
    if (typeof window.realTimeValidator === 'undefined') {
        // The validator will be initialized by real-time-validation.js
        
        // Note: Real-time validation is disabled by default to save resources
        // Users can enable it manually if needed:
        // window.realTimeValidator.enableRealTimeValidation();
        
        // Set up manual validation on file selection
        const fileInput = document.getElementById('fileInput');
        
        if (fileInput) {
            fileInput.addEventListener('change', async (e) => {
                const file = e.target.files[0];
                if (file) {
                    try {
                        const validation = await window.realTimeValidator.validateFile(file);
                    } catch (error) {
                        // File validation failed
                    }
                }
            });
        }
    }
});
