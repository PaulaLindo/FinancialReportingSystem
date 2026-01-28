// Mobile Menu Functionality for SADPMR Financial Reporting System

document.addEventListener('DOMContentLoaded', function() {
    const mobileMenuToggle = document.getElementById('mobileMenuToggle');
    const navMenu = document.getElementById('navMenu');
    const mobileMenuOverlay = document.getElementById('mobileMenuOverlay');
    
    if (!mobileMenuToggle || !navMenu || !mobileMenuOverlay) {
        console.warn('Mobile menu elements not found - may not be on a page with navigation');
        return;
    }
    
    // Toggle mobile menu
    mobileMenuToggle.addEventListener('click', function(e) {
        e.stopPropagation();
        toggleMenu();
    });
    
    // Close menu when clicking overlay
    mobileMenuOverlay.addEventListener('click', function() {
        closeMenu();
    });
    
    // Close menu when clicking outside the menu
    document.addEventListener('click', function(e) {
        const isClickInsideMenu = navMenu.contains(e.target);
        const isClickOnToggle = mobileMenuToggle.contains(e.target);
        const isMenuOpen = navMenu.classList.contains('active');
        
        if (isMenuOpen && !isClickInsideMenu && !isClickOnToggle) {
            closeMenu();
        }
    });
    
    // Close menu when clicking nav links - target links inside nav-menu
    const navLinks = navMenu.querySelectorAll('.nav-menu a');
    navLinks.forEach(link => {
        link.addEventListener('click', function() {
            closeMenu();
        });
    });
    
    // Close menu on escape key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && navMenu.classList.contains('active')) {
            closeMenu();
        }
    });
    
    // Close menu when resizing to desktop
    window.addEventListener('resize', function() {
        if (window.innerWidth > 768 && navMenu.classList.contains('active')) {
            closeMenu();
        }
    });
    
    function toggleMenu() {
        const isOpen = navMenu.classList.contains('active');
        
        if (isOpen) {
            closeMenu();
        } else {
            openMenu();
        }
    }
    
    function openMenu() {
        navMenu.classList.add('active');
        mobileMenuOverlay.classList.add('active');
        mobileMenuToggle.classList.add('active');
        document.body.style.overflow = 'hidden';
    }
    
    function closeMenu() {
        navMenu.classList.remove('active');
        mobileMenuOverlay.classList.remove('active');
        mobileMenuToggle.classList.remove('active');
        document.body.style.overflow = '';
    }
});

// Global function for onclick handlers (backup)
function toggleMobileMenu() {
    const navMenu = document.getElementById('navMenu');
    const mobileMenuOverlay = document.getElementById('mobileMenuOverlay');
    const mobileMenuToggle = document.getElementById('mobileMenuToggle');
    
    if (!navMenu || !mobileMenuOverlay || !mobileMenuToggle) {
        console.error('Elements not found in global function');
        return;
    }
    
    const isOpen = navMenu.classList.contains('active');
    
    if (isOpen) {
        navMenu.classList.remove('active');
        mobileMenuOverlay.classList.remove('active');
        mobileMenuToggle.classList.remove('active');
        document.body.style.overflow = '';
    } else {
        navMenu.classList.add('active');
        mobileMenuOverlay.classList.add('active');
        mobileMenuToggle.classList.add('active');
        document.body.style.overflow = 'hidden';
    }
}

console.log('Mobile menu initialization complete');
