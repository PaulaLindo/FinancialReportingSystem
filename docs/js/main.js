/**
 * SADPMR Financial Reporting System - Main Application
 * Refactored main JavaScript with modular architecture
 */

class MainApplication {
    constructor() {
        this.elements = {};
        this.observers = {};
        this.init();
    }

    /**
     * Initialize the application
     */
    init() {
        this.cacheElements();
        this.setupEventListeners();
        this.setupIntersectionObservers();
        this.setupScrollEffects();
        this.setupAnimations();
        SADPMRUtils.showBranding();
    }

    /**
     * Cache DOM elements
     */
    cacheElements() {
        this.elements = {
            navLinks: document.querySelectorAll('a[href^="#"]'),
            sections: document.querySelectorAll('section[id]'),
            navbar: document.querySelector('.navbar'),
            featureCards: document.querySelectorAll('.feature-card'),
            screenshotCards: document.querySelectorAll('.screenshot-card'),
            workflowSteps: document.querySelectorAll('.workflow-step'),
            stats: document.querySelectorAll('.stat-number'),
            pricingCards: document.querySelectorAll('.pricing-card'),
            pricingSection: document.querySelector('.pricing-section'),
            playButton: document.querySelector('.play-button'),
            screenshotPlaceholders: document.querySelectorAll('.screenshot-placeholder'),
            hero: document.querySelector('.hero'),
            // About page collapsible headers
            problemBoxHeaders: document.querySelectorAll('.problem-box h3'),
            solutionBoxHeaders: document.querySelectorAll('.solution-box h3')
        };
    }

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        this.setupNavigation();
        this.setupPlayButton();
        this.setupHoverEffects();
        this.setupPricingCards();
        this.setupCollapsibleHeaders();
    }

    /**
     * Setup navigation functionality
     */
    setupNavigation() {
        // Smooth scroll for navigation links
        this.elements.navLinks.forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const targetId = link.getAttribute('href');
                
                // Only process if it's an anchor link (starts with #)
                if (targetId && targetId.startsWith('#')) {
                    const targetSection = document.querySelector(targetId);
                    
                    if (targetSection) {
                        SADPMRUtils.scrollToElement(targetSection);
                        this.updateActiveNavLink(link);
                    }
                } else if (targetId && !targetId.startsWith('#')) {
                    // For regular links (like /download/*), let them work normally
                    window.location.href = targetId;
                }
            });
        });
    }

    /**
     * Update active navigation link
     */
    updateActiveNavLink(activeLink) {
        this.elements.navLinks.forEach(link => link.classList.remove('active'));
        activeLink.classList.add('active');
    }

    /**
     * Setup intersection observers
     */
    setupIntersectionObservers() {
        this.setupFadeInObserver();
        this.setupNavigationObserver();
        this.setupStatsObserver();
        this.setupPricingObserver();
    }

    /**
     * Setup fade-in animation observer
     */
    setupFadeInObserver() {
        this.observers.fadeIn = SADPMRUtils.createIntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    SADPMRUtils.addFadeInAnimation([entry.target]);
                    this.observers.fadeIn.unobserve(entry.target);
                }
            });
        });

        // Observe elements
        [...this.elements.featureCards, ...this.elements.screenshotCards, ...this.elements.workflowSteps]
            .forEach((element, index) => {
                element.style.transitionDelay = `${index * 0.1}s`;
                this.observers.fadeIn.observe(element);
            });
    }

    /**
     * Setup navigation observer for active section highlighting
     */
    setupNavigationObserver() {
        this.observers.navigation = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const currentId = entry.target.getAttribute('id');
                    const activeLink = document.querySelector(`a[href="#${currentId}"]`);
                    if (activeLink) {
                        this.updateActiveNavLink(activeLink);
                    }
                }
            });
        }, { threshold: 0.3 });

        this.elements.sections.forEach(section => {
            this.observers.navigation.observe(section);
        });
    }

    /**
     * Setup stats counter observer
     */
    setupStatsObserver() {
        this.observers.stats = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const target = entry.target;
                    const finalValue = target.textContent;
                    
                    if (!isNaN(parseInt(finalValue))) {
                        SADPMRUtils.animateCounter(target, finalValue);
                    }
                    
                    this.observers.stats.unobserve(target);
                }
            });
        }, { threshold: 0.5 });

        this.elements.stats.forEach(stat => {
            this.observers.stats.observe(stat);
        });
    }

    /**
     * Setup pricing section observer
     */
    setupPricingObserver() {
        if (!this.elements.pricingSection) return;

        this.observers.pricing = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const cards = entry.target.querySelectorAll('.pricing-card');
                    cards.forEach((card, index) => {
                        setTimeout(() => {
                            card.style.opacity = '1';
                            card.style.transform = 'translateY(0)';
                        }, index * 200);
                    });
                    this.observers.pricing.unobserve(entry.target);
                }
            });
        }, { threshold: 0.2 });

        this.observers.pricing.observe(this.elements.pricingSection);
        this.initializePricingCards();
    }

    /**
     * Initialize pricing cards
     */
    initializePricingCards() {
        if (!this.elements.pricingSection) return;

        const cards = this.elements.pricingSection.querySelectorAll('.pricing-card');
        cards.forEach(card => {
            if (!card.classList.contains('featured')) {
                card.style.opacity = '0';
                card.style.transform = 'translateY(30px)';
                card.style.transition = `all 600ms ${SADPMRUtils.CONFIG.ANIMATION.EASING}`;
            }
        });
    }

    /**
     * Setup scroll effects
     */
    setupScrollEffects() {
        let lastScroll = 0;

        window.addEventListener('scroll', SADPMRUtils.throttle(() => {
            this.handleNavbarShadow();
            this.handleParallax();
            lastScroll = window.pageYOffset;
        }, 16)); // ~60fps
    }

    /**
     * Handle navbar shadow on scroll
     */
    handleNavbarShadow() {
        if (!this.elements.navbar) return;
        
        const currentScroll = window.pageYOffset;
        
        if (currentScroll > 100) {
            this.elements.navbar.style.boxShadow = '0 4px 12px rgba(0, 0, 0, 0.1)';
        } else {
            this.elements.navbar.style.boxShadow = '0 1px 2px rgba(0, 0, 0, 0.05)';
        }
    }

    /**
     * Handle parallax effect for hero section
     */
    handleParallax() {
        if (!this.elements.hero) return;
        
        const scrolled = window.pageYOffset;
        const parallax = scrolled * 0.5;
        this.elements.hero.style.backgroundPositionY = `${parallax}px`;
    }

    /**
     * Setup animations
     */
    setupAnimations() {
        // Additional animations can be added here
    }

    /**
     * Setup play button functionality
     */
    setupPlayButton() {
        if (!this.elements.playButton) return;

        this.elements.playButton.addEventListener('click', () => {
            const placeholder = this.elements.playButton.parentElement;
            placeholder.innerHTML = `
                <div style="padding: 2rem; text-align: center;">
                    <h3 style="color: var(--primary-900); margin-bottom: 1rem;">Demo Video</h3>
                    <p style="color: var(--gray-700);">
                        Live demonstration will be recorded and uploaded here after the February 3, 2026 presentation.
                    </p>
                    <p style="color: var(--gray-600); margin-top: 1rem; font-size: 0.9rem;">
                        For now, please <a href="#contact" style="color: var(--primary-600); text-decoration: underline;">contact us</a> 
                        to schedule a personalized live demo.
                    </p>
                </div>
            `;
        });
    }

    /**
     * Setup hover effects
     */
    setupHoverEffects() {
        // Screenshot placeholders
        this.elements.screenshotPlaceholders.forEach(placeholder => {
            placeholder.addEventListener('mouseenter', () => {
                placeholder.style.transform = 'scale(1.05)';
                placeholder.style.transition = 'transform 0.3s ease';
            });
            
            placeholder.addEventListener('mouseleave', () => {
                placeholder.style.transform = 'scale(1)';
            });
        });
    }

    /**
     * Setup pricing card hover effects
     */
    setupPricingCards() {
        this.elements.pricingCards.forEach(card => {
            card.addEventListener('mouseenter', () => {
                if (!card.classList.contains('featured')) {
                    card.style.transform = 'translateY(-8px) scale(1.02)';
                }
            });
            
            card.addEventListener('mouseleave', () => {
                if (!card.classList.contains('featured')) {
                    card.style.transform = 'translateY(0) scale(1)';
                }
            });
        });
    }

    /**
     * Setup collapsible headers for About page problem/solution boxes
     */
    setupCollapsibleHeaders() {
        const allHeaders = [...this.elements.problemBoxHeaders, ...this.elements.solutionBoxHeaders];
        
        allHeaders.forEach(header => {
            header.addEventListener('click', () => {
                this.toggleCollapsibleSection(header);
            });
        });
    }

    /**
     * Toggle collapsible section
     */
    toggleCollapsibleSection(header) {
        const isCollapsed = header.classList.contains('collapsed');
        const ul = header.nextElementSibling;
        
        if (isCollapsed) {
            // Expand
            header.classList.remove('collapsed');
            ul.classList.remove('collapsed');
        } else {
            // Collapse
            header.classList.add('collapsed');
            ul.classList.add('collapsed');
        }
    }

    /**
     * Cleanup method
     */
    destroy() {
        // Disconnect all observers
        Object.values(this.observers).forEach(observer => {
            if (observer && observer.disconnect) {
                observer.disconnect();
            }
        });
    }
}

// Initialize application when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.mainApp = new MainApplication();
});

// Handle page unload for cleanup
window.addEventListener('beforeunload', () => {
    if (window.mainApp) {
        window.mainApp.destroy();
    }
});
