/**
 * Fluid Navigation System - JavaScript Handler
 * SADPMR Financial Reporting System
 * 
 * Handles mobile menu toggle without relying on hardcoded breakpoints
 * The menu works on any screen size based on available space
 */

class FluidNavigation {
    constructor() {
        this.menuToggle = document.getElementById('mobileMenuToggle');
        this.navMenu = document.getElementById('navMenu');
        this.menuOverlay = document.getElementById('mobileMenuOverlay');
        this.isOpen = false;
        
        this.init();
    }
    
    init() {
        if (!this.menuToggle || !this.navMenu || !this.menuOverlay) {
            console.warn('Navigation elements not found');
            return;
        }
        
        // Fallback: Ensure mobile menu toggle is visible on mobile devices
        if (window.innerWidth <= 1023) {
            this.menuToggle.classList.add('mobile-menu-toggle--visible');
            this.menuToggle.classList.remove('mobile-menu-toggle--hidden');
        }
        
        // Bind event listeners
        this.bindEvents();
        
        // Check initial state based on viewport
        this.checkInitialState();
        
        // Listen for viewport changes
        this.bindViewportListener();
    }
    
    bindEvents() {
        // Menu toggle click
        this.menuToggle.addEventListener('click', (e) => {
            e.preventDefault();
            this.toggleMenu();
        });
        
        // Overlay click
        this.menuOverlay.addEventListener('click', () => {
            this.closeMenu();
        });
        
        // Escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.isOpen) {
                this.closeMenu();
            }
        });
        
        // Handle window resize
        window.addEventListener('resize', () => {
            this.handleResize();
        });
    }
    
    bindViewportListener() {
        // Use ResizeObserver to detect when navigation should collapse
        if (window.ResizeObserver) {
            const resizeObserver = new ResizeObserver((entries) => {
                for (const entry of entries) {
                    if (entry.contentRect.width <= 1023) {
                        this.menuToggle.classList.add('mobile-menu-toggle--visible');
                        this.menuToggle.classList.remove('mobile-menu-toggle--hidden');
                    } else {
                        this.menuToggle.classList.add('mobile-menu-toggle--hidden');
                        this.menuToggle.classList.remove('mobile-menu-toggle--visible');
                        // Close menu if open when expanding
                        if (this.isOpen) {
                            this.closeMenu();
                        }
                    }
                }
            });
            
            // Observe the navbar container
            const navbar = document.querySelector('.navbar');
            if (navbar) {
                resizeObserver.observe(navbar);
            }
        }
    }
    
    checkInitialState() {
        // Check if navigation should be collapsed based on available space
        const navbar = document.querySelector('.navbar');
        if (navbar) {
            const width = navbar.getBoundingClientRect().width;
            if (width <= 1023) {
                this.menuToggle.classList.add('mobile-menu-toggle--visible');
                this.menuToggle.classList.remove('mobile-menu-toggle--hidden');
            } else {
                this.menuToggle.classList.add('mobile-menu-toggle--hidden');
                this.menuToggle.classList.remove('mobile-menu-toggle--visible');
            }
        }
    }
    
    toggleMenu() {
        if (this.isOpen) {
            this.closeMenu();
        } else {
            this.openMenu();
        }
    }
    
    openMenu() {
        this.isOpen = true;
        
        // Add active classes
        this.menuToggle.classList.add('active');
        this.navMenu.classList.add('active');
        this.menuOverlay.classList.add('active');
        
        // Focus management
        this.menuToggle.setAttribute('aria-expanded', 'true');
        
        // Prevent body scroll
        document.body.classList.add('body-scroll-locked');
        document.body.classList.remove('body-scroll-unlocked');
        
        // Focus first menu item
        const firstMenuItem = this.navMenu.querySelector('.nav-menu a');
        if (firstMenuItem) {
            setTimeout(() => {
                firstMenuItem.focus();
            }, 100);
        }
    }
    
    closeMenu() {
        this.isOpen = false;
        
        // Remove active classes
        this.menuToggle.classList.remove('active');
        this.navMenu.classList.remove('active');
        this.menuOverlay.classList.remove('active');
        
        // Focus management
        this.menuToggle.setAttribute('aria-expanded', 'false');
        
        // Restore body scroll
        document.body.classList.add('body-scroll-unlocked');
        document.body.classList.remove('body-scroll-locked');
        
        // Return focus to toggle
        setTimeout(() => {
            this.menuToggle.focus();
        }, 100);
    }
    
    handleResize() {
        // Close menu on resize if it's open
        if (this.isOpen) {
            const navbar = document.querySelector('.navbar');
            if (navbar) {
                const width = navbar.getBoundingClientRect().width;
                if (width > 1023) {
                    this.closeMenu();
                }
            }
        }
    }
    
    // Public methods for external use
    open() {
        this.openMenu();
    }
    
    close() {
        this.closeMenu();
    }
    
    isMenuOpen() {
        return this.isOpen;
    }
}

// Initialize navigation when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    // Initialize fluid navigation
    window.fluidNavigation = new FluidNavigation();
    
    // Make it globally available for external scripts
    window.toggleMobileMenu = () => {
        if (window.fluidNavigation) {
            window.fluidNavigation.toggleMenu();
        }
    };
    
    window.closeMobileMenu = () => {
        if (window.fluidNavigation) {
            window.fluidNavigation.closeMenu();
        }
    };
});

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = FluidNavigation;
}
