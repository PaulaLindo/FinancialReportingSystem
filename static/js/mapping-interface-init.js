/**
 * Varydian Financial Reporting System - Mapping Interface Initialization
 * Passes data to JavaScript for mapping interface page
 */

// Initialize mapping data from sessionStorage or template
window.mappingData = null;

// Check if this is a review session (from upload processing)
const urlParams = new URLSearchParams(window.location.search);
const isReview = urlParams.get('review') === 'true';
const sessionId = urlParams.get('session_id') || window.sessionId;

// Get mapping review data from sessionStorage if available
if (isReview && sessionStorage.getItem('mappingReviewData')) {
    try {
        window.mappingData = JSON.parse(sessionStorage.getItem('mappingReviewData'));
        console.log('Loaded mapping review data:', window.mappingData);
    } catch (error) {
        console.error('Error loading mapping review data:', error);
        window.mappingData = null;
    }
}

// Set global session ID
window.sessionId = sessionId;
