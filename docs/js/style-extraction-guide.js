// JavaScript Style Extraction Guide - SADPMR Financial Reporting System
// Convert all inline style manipulations to BEM class-based approaches
// This guide shows the before/after for each inline style found

// ========================================
// HERO PARALLAX EFFECT
// ========================================

// BEFORE (main.js line 248)
this.elements.hero.style.setProperty('--parallax-y', `${parallax}px`);

// AFTER
this.elements.hero.classList.add('hero--parallax');
this.elements.hero.style.setProperty('--parallax-y', parallax + 'px');

// ========================================
// NAVBAR SCROLL SHADOW
// ========================================

// BEFORE (main.js line 232)
this.elements.navbar.style.boxShadow = '0 4px 12px rgba(0, 0, 0, 0.1)';

// AFTER
this.elements.navbar.classList.add('navbar--scrolled');

// BEFORE (main.js line 234)
this.elements.navbar.style.boxShadow = '0 1px 2px rgba(0, 0, 0, 0.05)';

// AFTER
this.elements.navbar.classList.remove('navbar--scrolled');

// ========================================
// HERO BACKGROUND POSITION
// ========================================

// BEFORE (main.js line 246)
this.elements.hero.style.backgroundPositionY = parallax + 'px';

// AFTER
this.elements.hero.classList.add('hero--parallax');
this.elements.hero.style.setProperty('--parallax-y', parallax + 'px');

// ========================================
// UPLOAD BOX DRAG STATES
// ========================================

// BEFORE (docs/js/upload.js line 132-133)
this.elements.uploadBox.style.borderColor = '#3f51b5';
this.elements.uploadBox.style.background = '#f0f4ff';

// AFTER
this.elements.uploadBox.classList.add('upload-box--drag-over');

// BEFORE (docs/js/upload.js line 141-142)
this.elements.uploadBox.style.borderColor = '#e0e0e0';
this.elements.uploadBox.style.background = '';

// AFTER
this.elements.uploadBox.classList.remove('upload-box--drag-over');

// BEFORE (docs/js/upload.js line 150-151)
this.elements.uploadBox.style.borderColor = '#e0e0e0';
this.elements.uploadBox.style.background = '';

// AFTER
this.elements.uploadBox.classList.remove('upload-box--drag-over');

// ========================================
// UPLOAD VISIBILITY STATES
// ========================================

// BEFORE (docs/js/upload.js line 231-232)
uploadBox.style.display = 'none';
fileInfo.style.display = 'block';

// AFTER
uploadBox.classList.add('u-display-none');
fileInfo.classList.add('upload__file-info--visible');

// BEFORE (docs/js/upload.js line 245-246)
this.elements.fileInfo.style.display = 'none';
this.setProcessingState(true, 'Processing your Trial Balance...', 'Mapping accounts to GRAP line items');

// AFTER
this.elements.fileInfo.classList.remove('upload__file-info--visible');
this.elements.fileInfo.classList.add('u-display-none');
this.setProcessingState(true, 'Processing your Trial Balance...', 'Mapping accounts to GRAP line items');

// BEFORE (docs/js/upload.js line 269)
this.elements.fileInfo.style.display = 'block';

// AFTER
this.elements.fileInfo.classList.remove('u-display-none');
this.elements.fileInfo.classList.add('upload__file-info--visible');

// BEFORE (docs/js/upload.js line 295)
this.elements.resultsSection.style.display = 'block';

// AFTER
this.elements.resultsSection.classList.add('upload__results-section--visible');

// BEFORE (docs/js/upload.js line 311-312)
pdfLoader.style.display = 'block';
pdfSuccess.style.display = 'none';

// AFTER
pdfLoader.classList.add('pdf-loader--visible');
pdfSuccess.classList.remove('pdf-success--visible');

// BEFORE (docs/js/upload.js line 331)
pdfSuccess.style.display = 'block';

// AFTER
pdfSuccess.classList.add('pdf-success--visible');

// BEFORE (docs/js/upload.js line 337)
pdfLoader.style.display = 'none';

// AFTER
pdfLoader.classList.remove('pdf-loader--visible');

// BEFORE (docs/js/upload.js line 350-351)
this.elements.uploadBox.style.display = 'block';
this.elements.fileInfo.style.display = 'none';

// AFTER
this.elements.uploadBox.classList.remove('u-display-none');
this.elements.fileInfo.classList.remove('upload__file-info--visible');
this.elements.fileInfo.classList.add('u-display-none');

// BEFORE (docs/js/upload.js line 358-362)
if (this.elements.pdfLoader) {
    this.elements.pdfLoader.style.display = 'none';
}
if (this.elements.pdfSuccess) {
    this.elements.pdfSuccess.style.display = 'none';
}

// AFTER
if (this.elements.pdfLoader) {
    this.elements.pdfLoader.classList.remove('pdf-loader--visible');
}
if (this.elements.pdfSuccess) {
    this.elements.pdfSuccess.classList.remove('pdf-success--visible');
}

// BEFORE (docs/js/upload.js line 389-390)
uploadBox.style.display = 'none';
processingLoader.style.display = 'block';

// AFTER
uploadBox.classList.add('u-display-none');
processingLoader.classList.add('upload__loader--visible');

// BEFORE (docs/js/upload.js line 402-406)
processingLoader.style.display = 'none';
if (this.state.uploadedFilePath) {
    this.elements.fileInfo.style.display = 'block';
} else {
    uploadBox.style.display = 'block';
}

// AFTER
processingLoader.classList.remove('upload__loader--visible');
if (this.state.uploadedFilePath) {
    this.elements.fileInfo.classList.remove('u-display-none');
    this.elements.fileInfo.classList.add('upload__file-info--visible');
} else {
    uploadBox.classList.remove('u-display-none');
}

// BEFORE (docs/js/upload.js line 440)
this.elements.resultsSection.style.display = 'none';

// AFTER
this.elements.resultsSection.classList.remove('upload__results-section--visible');

// ========================================
// ERROR MESSAGE VISIBILITY
// ========================================

// BEFORE (docs/js/utils.js line 133)
errorEl.style.display = 'block';

// AFTER
errorEl.classList.add('error-message--visible');

// BEFORE (docs/js/utils.js line 144)
errorEl.style.display = 'none';

// AFTER
errorEl.classList.remove('error-message--visible');

// ========================================
// FADE IN ANIMATIONS
// ========================================

// BEFORE (docs/js/utils.js line 205-208)
element.style.opacity = '0';
element.style.transform = 'translateY(30px)';
element.style.transition = 'all ' + this.CONFIG.ANIMATION.DURATION + 'ms ' + this.CONFIG.ANIMATION.EASING;
element.style.transitionDelay = (delay + index * 0.1) + 's';

// AFTER
element.classList.add('fade-in');
element.classList.add('fade-in--delay-' + (index + 1));

// BEFORE (docs/js/utils.js line 211-212)
element.style.opacity = '1';
element.style.transform = 'translateY(0)';

// AFTER
element.classList.add('fade-in--visible');

// ========================================
// MOBILE MENU BODY SCROLL LOCK
// ========================================

// BEFORE (docs/js/mobile-menu.js line 103)
document.body.style.overflow = 'hidden';

// AFTER
document.body.classList.add('body--menu-open');

// BEFORE (docs/js/mobile-menu.js line 116)
document.body.style.overflow = '';

// AFTER
document.body.classList.remove('body--menu-open');

// ========================================
// FEATURE CARDS ANIMATIONS
// ========================================

// BEFORE (docs/js/main.js line 119)
element.style.transitionDelay = (index * 0.1) + 's';

// AFTER
element.classList.add('fade-in--delay-' + index);

// BEFORE (docs/js/main.js line 203-206)
card.style.opacity = '1';
card.style.transform = 'translateY(0)';

// AFTER
card.classList.add('fade-in--visible');

// BEFORE (docs/js/main.js line 203-206)
card.style.opacity = '0';
card.style.transform = 'translateY(30px)';
card.style.transition = 'all 600ms ' + SADPMRUtils.CONFIG.ANIMATION.EASING;

// AFTER
card.classList.add('fade-in');

// ========================================
// UTILITY FUNCTIONS FOR CONVERSION
// ========================================

// Helper function to replace style.display with classes
function setDisplayState(element, state) {
    const displayMap = {
        'none': 'u-display-none',
        'block': 'u-display-block',
        'flex': 'u-display-flex',
        'grid': 'u-display-grid'
    };
    
    // Remove all display classes
    Object.values(displayMap).forEach(cls => element.classList.remove(cls));
    
    // Add the desired display class
    if (displayMap[state]) {
        element.classList.add(displayMap[state]);
    }
}

// Helper function to replace style.opacity with classes
function setOpacityState(element, opacity) {
    element.classList.remove('u-opacity-0', 'u-opacity-1');
    if (opacity === '0' || opacity === 0) {
        element.classList.add('u-opacity-0');
    } else if (opacity === '1' || opacity === 1) {
        element.classList.add('u-opacity-1');
    }
}

// Helper function to replace style.transform with classes
function setTransformState(element, transform) {
    element.classList.remove('u-transform-none', 'u-transform-translate-y-0', 'u-transform-translate-y-30');
    if (transform === 'none') {
        element.classList.add('u-transform-none');
    } else if (transform === 'translateY(0)') {
        element.classList.add('u-transform-translate-y-0');
    } else if (transform === 'translateY(30px)') {
        element.classList.add('u-transform-translate-y-30');
    }
}

// ========================================
// CONVERSION CHECKLIST
// ========================================

// Files to update:
// ✅ static/js/main.js - Hero parallax, navbar shadow, animations
// ✅ docs/js/upload.js - Upload box states, visibility controls
// ✅ docs/js/utils.js - Error messages, fade animations
// ✅ docs/js/mobile-menu.js - Body scroll lock
// ✅ docs/js/main.js - Feature cards, pricing cards

// Style patterns to replace:
// ✅ element.style.display = 'value' → element.classList.add/remove('u-display-value')
// ✅ element.style.opacity = 'value' → element.classList.add/remove('u-opacity-value')
// ✅ element.style.transform = 'value' → element.classList.add/remove('u-transform-value')
// ✅ element.style.boxShadow = 'value' → element.classList.add/remove('component--state')
// ✅ element.style.background = 'value' → element.classList.add/remove('component--state')
// ✅ element.style.borderColor = 'value' → element.classList.add/remove('component--state')
// ✅ element.style.overflow = 'value' → element.classList.add/remove('component--state')

// Benefits of this conversion:
// ✅ Better separation of concerns
// ✅ Easier to maintain and debug
// ✅ Consistent styling approach
// ✅ Better performance (CSS handles transitions)
// ✅ More accessible and semantic
// ✅ Follows BEM methodology
