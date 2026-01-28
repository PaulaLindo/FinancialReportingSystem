/**
 * Main JavaScript - Extracted from Working main.js
 * SADPMR Financial Reporting System
 */

document.addEventListener('DOMContentLoaded', function() {
    // Smooth scroll for navigation links
    const navLinks = document.querySelectorAll('a[href^="#"]');
    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const targetId = this.getAttribute('href');
            const targetSection = document.querySelector(targetId);
            
            if (targetSection) {
                targetSection.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
                
                // Update active nav link
                navLinks.forEach(l => l.classList.remove('active'));
                this.classList.add('active');
            }
        });
    });

    // Intersection Observer for scroll animations
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const fadeInObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '0';
                entry.target.style.transform = 'translateY(30px)';
                
                setTimeout(() => {
                    entry.target.style.transition = 'all 0.8s cubic-bezier(0.4, 0, 0.2, 1)';
                    entry.target.style.opacity = '1';
                    entry.target.style.transform = 'translateY(0)';
                }, 100);
                
                fadeInObserver.unobserve(entry.target);
            }
        });
    }, observerOptions);

    // Observe feature cards
    const featureCards = document.querySelectorAll('.feature-card');
    featureCards.forEach((card, index) => {
        fadeInObserver.observe(card);
    });

    // Observe step elements
    const stepElements = document.querySelectorAll('.step');
    stepElements.forEach((step, index) => {
        fadeInObserver.observe(step);
    });

    // Parallax effect on scroll
    window.addEventListener('scroll', function() {
        const hero = document.querySelector('.hero');
        if (hero) {
            const scrolled = window.pageYOffset;
            const parallax = scrolled * 0.5;
            hero.style.backgroundPositionY = `${parallax}px`;
        }
    });

    // Lazy load effect for pricing cards
    const pricingSection = document.querySelector('.pricing-section');
    if (pricingSection) {
        const pricingObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.querySelectorAll('.pricing-card').forEach((card, index) => {
                        setTimeout(() => {
                            card.style.opacity = '1';
                            card.style.transform = 'translateY(0)';
                        }, index * 200);
                    });
                    pricingObserver.unobserve(entry.target);
                }
            });
        }, { threshold: 0.2 });

        pricingObserver.observe(pricingSection);
        
        // Set initial state
        pricingSection.querySelectorAll('.pricing-card').forEach(card => {
            if (!card.classList.contains('featured')) {
                card.style.opacity = '0';
                card.style.transform = 'translateY(30px)';
                card.style.transition = 'all 0.6s cubic-bezier(0.4, 0, 0.2, 1)';
            }
        });
    }

    // Console branding
    console.log('%c February 3, 2026 Demo | Schedule 3A PFMA Compliance ', 'color: #1e3a5f; font-size: 11px;');
    console.log('\n👋 Interested in the technology behind this system?\nGet in touch: demo@sadpmr-system.co.za');
});

// Global scroll animations
window.addEventListener('scroll', SADPMR.utils.throttle(function() {
    // Add any scroll-based animations here if needed
}, 16));

// Window resize handling
window.addEventListener('resize', SADPMR.utils.debounce(function() {
    // Handle responsive changes
    const isMobile = window.innerWidth <= 768;
    document.body.classList.toggle('mobile', isMobile);
    document.body.classList.toggle('desktop', !isMobile);
}, 250));
