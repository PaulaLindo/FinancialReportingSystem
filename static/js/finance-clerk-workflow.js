/**
 * Varydian Financial Reporting System - Finance Clerk Workflow Manager
 * Handles finance clerk workflow navigation and state management
 */

// Finance Clerk Workflow Manager
class FinanceClerkWorkflow {
    constructor() {
        this.currentStep = 1;
        this.completedSteps = new Set();
        this.workflowData = {};
        this.init();
    }

    init() {
        this.loadWorkflowState();
        this.setupEventListeners();
        this.updateUI();
        this.startAutoSave();
    }

    loadWorkflowState() {
        // Workflow state managed server-side via Supabase
        this.currentStep = 1;
        this.completedSteps = new Set();
        this.workflowData = {};
        this.sessionData = {};
    }

    saveWorkflowState() {
        // Workflow state managed server-side via Supabase
    }

    setupEventListeners() {
        // Step navigation
        const dashboardBtn = document.getElementById('dashboardBtn');
        if (dashboardBtn) {
            dashboardBtn.addEventListener('click', () => {
                this.navigateToStep(1, '/dashboard');
            });
        }

        const uploadBtn = document.getElementById('uploadBtn');
        if (uploadBtn) {
            uploadBtn.addEventListener('click', () => {
                this.navigateToStep(2, '/upload');
            });
        }

        const mappingBtn = document.getElementById('mappingBtn');
        if (mappingBtn) {
            mappingBtn.addEventListener('click', () => {
                this.navigateToStep(3, '/mapping-interface');
            });
        }

        const submitBtn = document.getElementById('submitBtn');
        if (submitBtn) {
            submitBtn.addEventListener('click', () => {
                this.navigateToStep(4, '/submission-status');
            });
        }

        // Listen for iframe navigation
        const contentFrame = document.getElementById('contentFrame');
        if (contentFrame) {
            contentFrame.addEventListener('load', () => {
                this.updateStepCompletion();
            });
        }
    }

    navigateToStep(step, url) {
        if (step <= this.getMaxAccessibleStep()) {
            this.currentStep = step;
            this.loadContent(url);
            this.updateUI();
            this.saveWorkflowState();
        }
    }

    loadContent(url) {
        const frame = document.getElementById('contentFrame');
        frame.src = url;
    }

    getMaxAccessibleStep() {
        // Step 1 is always accessible
        if (this.completedSteps.size === 0) return 1;
        
        // Step 2 requires step 1 completion
        if (!this.completedSteps.has(1)) return 1;
        
        // Step 3 requires step 2 completion  
        if (!this.completedSteps.has(2)) return 2;
        
        // Step 4 requires step 3 completion
        if (!this.completedSteps.has(3)) return 3;
        
        return 4; // All steps accessible
    }

    updateStepCompletion() {
        const currentUrl = document.getElementById('contentFrame').contentWindow.location.pathname;
        
        // Check if user has completed requirements for each step
        if (currentUrl.includes('/dashboard') && !this.completedSteps.has(1)) {
            this.markStepCompleted(1);
        }
        
        if (currentUrl.includes('/upload') && !this.completedSteps.has(2)) {
            this.markStepCompleted(2);
        }
        
        if (currentUrl.includes('/mapping-interface') && !this.completedSteps.has(3)) {
            this.markStepCompleted(3);
        }
        
        if (currentUrl.includes('/submission-status') && !this.completedSteps.has(4)) {
            this.markStepCompleted(4);
        }
    }

    markStepCompleted(step) {
        this.completedSteps.add(step);
        this.workflowData[`step${step}Completed`] = new Date().toISOString();
        this.saveWorkflowState();
        this.updateUI();
        
        // Show completion notification
        this.showNotification(`Step ${step} completed!`, 'success');
    }

    updateUI() {
        // Update step visual states
        for (let i = 1; i <= 4; i++) {
            const stepElement = document.getElementById(`step${i}`);
            const btnElement = document.getElementById(this.getStepButtonId(i));
            
            stepElement.classList.remove('active', 'completed');
            btnElement.disabled = false;
            
            if (this.completedSteps.has(i)) {
                stepElement.classList.add('completed');
            } else if (i === this.currentStep) {
                stepElement.classList.add('active');
            } else if (i > this.getMaxAccessibleStep()) {
                btnElement.disabled = true;
            }
        }

        // Update progress bar
        this.updateProgressBar();
        
        // Update content frame if needed
        this.updateContentFrame();
    }

    updateProgressBar() {
        const progress = (this.completedSteps.size / 4) * 100;
        const progressBar = document.getElementById('progressBar');
        const progressPercentage = document.getElementById('progressPercentage');
        
        progressBar.classList.add('progress-bar-dynamic');
        // Set progress using CSS variable
        const progressValue = Math.round(progress);
        progressBar.setAttribute('data-progress', progressValue);
        progressBar.style.setProperty('--progress-width', `${progress}%`);
        if (progressPercentage) {
            progressPercentage.textContent = `${Math.round(progress)}%`;
        }
    }

    updateContentFrame() {
        const frame = document.getElementById('contentFrame');
        const currentStep = this.currentStep;
        
        // Load appropriate content based on current step
        const stepUrls = {
            1: '/dashboard',
            2: '/upload',
            3: '/mapping-interface',
            4: '/submission-status'
        };
        
        if (frame.src !== window.location.origin + stepUrls[currentStep]) {
            frame.src = stepUrls[currentStep];
        }
    }

    getStepButtonId(step) {
        const buttonMap = {
            1: 'dashboardBtn',
            2: 'uploadBtn', 
            3: 'mappingBtn',
            4: 'submitBtn'
        };
        return buttonMap[step];
    }

    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type} notification-fixed`;
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        // Animate in
        setTimeout(() => {
            notification.classList.add('notification-show');
        }, 100);
        
        // Remove after 3 seconds
        setTimeout(() => {
            notification.classList.remove('notification-show');
            notification.classList.add('notification-hide');
            setTimeout(() => {
                document.body.removeChild(notification);
            }, 300);
        }, 3000);
    }

    startAutoSave() {
        // Auto-save every 30 seconds
        setInterval(() => {
            this.saveWorkflowState();
        }, 30000);
    }

    // Public methods for external calls
    completeStep(step) {
        this.markStepCompleted(step);
    }

    resetWorkflow() {
        this.currentStep = 1;
        this.completedSteps.clear();
        this.workflowData = {};
        this.saveWorkflowState();
        this.updateUI();
        // Workflow state cleared - managed server-side
    }
}

// Initialize workflow
document.addEventListener('DOMContentLoaded', () => {
    if (typeof window.financeClerkWorkflow === 'undefined') {
        window.financeClerkWorkflow = new FinanceClerkWorkflow();
    }
});
