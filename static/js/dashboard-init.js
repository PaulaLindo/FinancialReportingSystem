/**
 * Varydian Financial Reporting System - Dashboard Initialization
 * Clerk open-period urgency filter and closed-period section toggle.
 */
document.addEventListener('DOMContentLoaded', function () {
    const urgencyFilter = document.getElementById('urgencyFilter');
    const taskGrid = document.getElementById('taskGrid');

    if (urgencyFilter && taskGrid) {
        function filterOpenTasks() {
            const urgencyValue = urgencyFilter.value;
            const taskCards = taskGrid.querySelectorAll('.task-card');

            taskCards.forEach((card) => {
                const cardUrgency = card.dataset.urgency || 'normal';
                const showCard = urgencyValue === 'all' || cardUrgency === urgencyValue;
                card.classList.toggle('display-none', !showCard);
                card.classList.toggle('display-block', showCard);
            });
        }

        urgencyFilter.addEventListener('change', filterOpenTasks);
        filterOpenTasks();
        document.addEventListener('clerk-periods-expanded', filterOpenTasks);
    }
});
