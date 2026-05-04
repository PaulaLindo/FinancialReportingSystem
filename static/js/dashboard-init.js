/**
 * Varydian Financial Reporting System - Dashboard Initialization
 * Handles dashboard-specific initialization and task filtering functionality
 */

// Task List filtering functionality
document.addEventListener('DOMContentLoaded', function() {
    const periodFilter = document.getElementById('periodFilter');
    const urgencyFilter = document.getElementById('urgencyFilter');
    const taskGrid = document.getElementById('taskGrid');
    
    if (periodFilter && urgencyFilter && taskGrid) {
        function filterTasks() {
            const statusValue = periodFilter.value;
            const urgencyValue = urgencyFilter.value;
            const taskCards = taskGrid.querySelectorAll('.task-card');
            
            taskCards.forEach(card => {
                const cardStatus = card.dataset.status || 'open';
                const cardUrgency = card.dataset.urgency || 'normal';
                
                let showCard = true;
                
                // Filter by status
                if (statusValue !== 'all' && cardStatus !== statusValue) {
                    showCard = false;
                }
                
                // Filter by urgency
                if (urgencyValue !== 'all' && cardUrgency !== urgencyValue) {
                    showCard = false;
                }
                
                // Show or hide card
                if (showCard) {
                    card.classList.remove('display-none');
                    card.classList.add('display-block');
                } else {
                    card.classList.remove('display-block');
                    card.classList.add('display-none');
                }
            });
            
            // Show message if no cards match
            const visibleCards = Array.from(taskCards).filter(card => !card.classList.contains('display-none'));
            const emptyState = taskGrid.nextElementSibling;
            
            if (visibleCards.length === 0 && emptyState && emptyState.classList.contains('empty-state')) {
                emptyState.classList.remove('display-none');
                emptyState.classList.add('display-block');
                taskGrid.classList.remove('display-grid');
                taskGrid.classList.add('display-none');
            } else {
                taskGrid.classList.remove('display-none');
                taskGrid.classList.add('display-grid');
                if (emptyState && emptyState.classList.contains('empty-state')) {
                    emptyState.classList.remove('display-block');
                    emptyState.classList.add('display-none');
                }
            }
        }
        
        // Add event listeners
        periodFilter.addEventListener('change', filterTasks);
        urgencyFilter.addEventListener('change', filterTasks);
        
        // Initial filter
        filterTasks();
    }
});
