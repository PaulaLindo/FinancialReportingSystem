// Main JavaScript for SADPMR Financial Reporting System

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
        card.style.transitionDelay = `${index * 0.1}s`;
        fadeInObserver.observe(card);
    });

    // Observe screenshot cards
    const screenshotCards = document.querySelectorAll('.screenshot-card');
    screenshotCards.forEach((card, index) => {
        card.style.transitionDelay = `${index * 0.15}s`;
        fadeInObserver.observe(card);
    });

    // Observe workflow steps
    const workflowSteps = document.querySelectorAll('.workflow-step');
    workflowSteps.forEach((step, index) => {
        step.style.transitionDelay = `${index * 0.2}s`;
        fadeInObserver.observe(step);
    });

    // Active section highlighting in navigation
    const sections = document.querySelectorAll('section[id]');
    const navObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const currentId = entry.target.getAttribute('id');
                navLinks.forEach(link => {
                    link.classList.remove('active');
                    if (link.getAttribute('href') === `#${currentId}`) {
                        link.classList.add('active');
                    }
                });
            }
        });
    }, {
        threshold: 0.3
    });

    sections.forEach(section => {
        navObserver.observe(section);
    });

    // Sticky navbar on scroll
    const navbar = document.querySelector('.navbar');
    let lastScroll = 0;

    window.addEventListener('scroll', () => {
        const currentScroll = window.pageYOffset;
        
        if (currentScroll > 100) {
            navbar.style.boxShadow = '0 4px 12px rgba(0, 0, 0, 0.1)';
        } else {
            navbar.style.boxShadow = '0 1px 2px rgba(0, 0, 0, 0.05)';
        }
        
        lastScroll = currentScroll;
    });

    // Animate stats counter
    const stats = document.querySelectorAll('.stat-number');
    const statsObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const target = entry.target;
                const finalValue = target.textContent;
                
                // Only animate if it's a number
                if (!isNaN(parseInt(finalValue))) {
                    animateCounter(target, finalValue);
                }
                
                statsObserver.unobserve(target);
            }
        });
    }, { threshold: 0.5 });

    stats.forEach(stat => {
        statsObserver.observe(stat);
    });

    function animateCounter(element, finalValue) {
        const isPercentage = finalValue.includes('%');
        const numValue = parseInt(finalValue);
        const duration = 2000;
        const steps = 60;
        const increment = numValue / steps;
        let current = 0;

        const timer = setInterval(() => {
            current += increment;
            if (current >= numValue) {
                element.textContent = finalValue;
                clearInterval(timer);
            } else {
                element.textContent = Math.floor(current) + (isPercentage ? '%' : 's');
            }
        }, duration / steps);
    }

    // Demo video placeholder click
    const playButton = document.querySelector('.play-button');
    if (playButton) {
        playButton.addEventListener('click', function() {
            const placeholder = this.parentElement;
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

    // Add hover effect to screenshot placeholders
    const screenshotPlaceholders = document.querySelectorAll('.screenshot-placeholder');
    screenshotPlaceholders.forEach(placeholder => {
        placeholder.addEventListener('mouseenter', function() {
            this.style.transform = 'scale(1.05)';
            this.style.transition = 'transform 0.3s ease';
        });
        
        placeholder.addEventListener('mouseleave', function() {
            this.style.transform = 'scale(1)';
        });
    });

    // Pricing card hover effects
    const pricingCards = document.querySelectorAll('.pricing-card');
    pricingCards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            if (!this.classList.contains('featured')) {
                this.style.transform = 'translateY(-8px) scale(1.02)';
            }
        });
        
        card.addEventListener('mouseleave', function() {
            if (!this.classList.contains('featured')) {
                this.style.transform = 'translateY(0) scale(1)';
            }
        });
    });

    // Console easter egg
    console.log('%c SADPMR Financial Reporting System ', 'background: #0a1128; color: #d4a574; font-size: 18px; padding: 10px; font-weight: bold;');
    console.log('%c Built with precision for public sector excellence ', 'background: #10b981; color: white; font-size: 12px; padding: 5px;');
    console.log('%c February 3, 2026 Demo | Schedule 3A PFMA Compliance ', 'color: #1e3a5f; font-size: 11px;');
    console.log('\n👋 Interested in the technology behind this system?\nGet in touch: demo@sadpmr-system.co.za');
});

// Add parallax effect to hero section
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
