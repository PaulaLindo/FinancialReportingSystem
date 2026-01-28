/**
 * Mobile Menu Component - Extracted from Working mobile-menu.js
 * SADPMR Financial Reporting System
 */

// Mobile menu namespace
SADPMR.mobileMenu = {
    elements: {
        toggle: null,
        menu: null,
        overlay: null,
        body: null
    },

    config: {
        activeClass: 'active',
        breakpoint: 768,
        animationDuration: 250
    },

    /**
     * Initialize mobile menu
     */
    init() {
        this.cacheElements();
        if (!this.elements.toggle) {
            console.warn('Mobile menu elements not found - may not be on a page with navigation');
            return;
        }
        this.bindEvents();
        this.setupAccessibility();
    },

    /**
     * Cache DOM elements
     */
    cacheElements() {
        this.elements = {
            toggle: document.getElementById('mobileMenuToggle'),
            menu: document.getElementById('navMenu'),
            overlay: document.getElementById('mobileMenuOverlay'),
            body: document.body
        };
    },

    /**
     * Bind event listeners
     */
    bindEvents() {
        const { toggle, menu, overlay, body } = this.elements;

        // Toggle mobile menu
        toggle.addEventListener('click', (e) => {
            e.stopPropagation();
            this.toggle();
        });

        // Close menu when clicking overlay
        overlay.addEventListener('click', () => {
            this.close();
        });

        // Close menu when clicking outside the menu
        document.addEventListener('click', (e) => {
            const isClickInsideMenu = menu.contains(e.target);
            const isClickOnToggle = toggle.contains(e.target);
            const isMenuOpen = menu.classList.contains('active');
            
            if (isMenuOpen && !isClickInsideMenu && !isClickOnToggle) {
                this.close();
            }
        });

        // Close menu when clicking nav links
        const navLinks = menu.querySelectorAll('.nav-menu a');
        navLinks.forEach(link => {
            link.addEventListener('click', () => {
                this.close();
            });
        });

        // Close menu on escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.isOpen()) {
                this.close();
                this.elements.toggle.focus();
            }
        });

        // Close menu when resizing to desktop
        window.addEventListener('resize', 
            SADPMR.utils.debounce(() => {
                if (window.innerWidth > this.config.breakpoint && this.isOpen()) {
                    this.close();
                }
            }, 250)
        );
    },

    /**
     * Setup accessibility features
     */
    setupAccessibility() {
        const { toggle, menu } = this.elements;

        // ARIA attributes
        toggle.setAttribute('aria-expanded', 'false');
        toggle.setAttribute('aria-controls', 'navMenu');
        menu.setAttribute('aria-hidden', 'true');

        // Focus management
        menu.addEventListener('keydown', (e) => {
            this.handleKeyboardNavigation(e);
        });
    },

    /**
     * Handle keyboard navigation
     * @param {Event} e - Keyboard event
     */
    handleKeyboardNavigation(e) {
        const { menu } = this.elements;
        const focusableElements = menu.querySelectorAll(
            'a, button, input, select, textarea, [tabindex]:not([tabindex="-1"])'
        );
        
        const firstElement = focusableElements[0];
        const lastElement = focusableElements[focusableElements.length - 1];

        switch (e.key) {
            case 'Tab':
                if (e.shiftKey) {
                    if (document.activeElement === firstElement) {
                        e.preventDefault();
                        lastElement.focus();
                    }
                } else {
                    if (document.activeElement === lastElement) {
                        e.preventDefault();
                        firstElement.focus();
                    }
                }
                break;
            case 'ArrowDown':
                e.preventDefault();
                this.focusNextElement(focusableElements);
                break;
            case 'ArrowUp':
                e.preventDefault();
                this.focusPreviousElement(focusableElements);
                break;
        }
    },

    /**
     * Focus next element in menu
     * @param {NodeList} elements - Focusable elements
     */
    focusNextElement(elements) {
        const currentIndex = Array.from(elements).indexOf(document.activeElement);
        const nextIndex = (currentIndex + 1) % elements.length;
        elements[nextIndex].focus();
    },

    /**
     * Focus previous element in menu
     * @param {NodeList} elements - Focusable elements
     */
    focusPreviousElement(elements) {
        const currentIndex = Array.from(elements).indexOf(document.activeElement);
        const prevIndex = currentIndex === 0 ? elements.length - 1 : currentIndex - 1;
        elements[prevIndex].focus();
    },

    /**
     * Toggle menu open/closed
     */
    toggle() {
        const isOpen = this.isOpen();
        
        if (isOpen) {
            this.close();
        } else {
            this.open();
        }
    },

    /**
     * Open menu
     */
    open() {
        const { toggle, menu, overlay, body } = this.elements;

        // Add active classes
        toggle.classList.add(this.config.activeClass);
        menu.classList.add(this.config.activeClass);
        overlay.classList.add(this.config.activeClass);

        // Update ARIA attributes
        toggle.setAttribute('aria-expanded', 'true');
        menu.setAttribute('aria-hidden', 'false');

        // Prevent body scroll
        body.style.overflow = 'hidden';

        // Focus first menu item
        const firstMenuItem = menu.querySelector('.nav-menu a');
        if (firstMenuItem) {
            setTimeout(() => firstMenuItem.focus(), 100);
        }

        // Emit custom event
        this.emitEvent('menu:opened');
    },

    /**
     * Close menu
     */
    close() {
        const { toggle, menu, overlay, body } = this.elements;

        // Remove active classes
        toggle.classList.remove(this.config.activeClass);
        menu.classList.remove(this.config.activeClass);
        overlay.classList.remove(this.config.activeClass);

        // Update ARIA attributes
        toggle.setAttribute('aria-expanded', 'false');
        menu.setAttribute('aria-hidden', 'true');

        // Restore body scroll
        body.style.overflow = '';

        // Emit custom event
        this.emitEvent('menu:closed');
    },

    /**
     * Check if menu is open
     * @returns {boolean} True if menu is open
     */
    isOpen() {
        const { menu } = this.elements;
        return menu && menu.classList.contains(this.config.activeClass);
    },

    /**
     * Check if click is inside menu
     * @param {Element} target - Click target element
     * @returns {boolean} True if click is inside menu
     */
    isClickInsideMenu(target) {
        const { toggle, menu } = this.elements;
        return toggle.contains(target) || menu.contains(target);
    },

    /**
     * Emit custom event
     * @param {string} eventName - Event name
     */
    emitEvent(eventName) {
        const event = new CustomEvent(eventName, {
            detail: {
                isOpen: this.isOpen()
            }
        });
        document.dispatchEvent(event);
    },

    /**
     * Get menu state
     * @returns {Object} Menu state information
     */
    getState() {
        return {
            isOpen: this.isOpen(),
            isMobile: window.innerWidth <= this.config.breakpoint,
            breakpoint: this.config.breakpoint
        };
    },

    /**
     * Destroy mobile menu
     */
    destroy() {
        const { toggle, menu, overlay } = this.elements;

        // Remove event listeners
        if (toggle) {
            toggle.removeEventListener('click', this.toggle);
        }
        
        if (overlay) {
            overlay.removeEventListener('click', this.close);
        }

        // Remove active classes
        this.close();

        // Clear cache
        this.elements = {
            toggle: null,
            menu: null,
            overlay: null,
            body: null
        };

        console.log('Mobile menu destroyed');
    }
};

// Auto-initialize if DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        SADPMR.mobileMenu.init();
    });
} else {
    SADPMR.mobileMenu.init();
}
