class MobileMenu {
    constructor() {
        this.elements = {};
        this.isOpen = false;
        this.boundMethods = {};
        this.init();
    }

    init() {
        this.cacheElements();
        if (!this.validateElements()) {
            console.warn('Mobile menu not found');
            return;
        }
        this.bindMethods();
        this.setupEventListeners();
    }

    cacheElements() {
        this.elements = {
            toggle: document.getElementById('mobileMenuToggle'),
            menu: document.getElementById('navMenu'),
            overlay: document.getElementById('mobileMenuOverlay'),
            navLinks: null
        };
    }

    validateElements() {
        const { toggle, menu, overlay } = this.elements;
        return toggle && menu && overlay;
    }

    bindMethods() {
        this.boundMethods = {
            toggle: this.toggle.bind(this),
            close: this.close.bind(this),
            handleKeydown: this.handleKeydown.bind(this),
            handleResize: this.handleResize.bind(this)
        };
    }

    setupEventListeners() {
        const { toggle, overlay, menu } = this.elements;
        
        toggle.addEventListener('click', this.boundMethods.toggle);
        overlay.addEventListener('click', this.boundMethods.close);
        
        // Add document click handler to close menu when clicking outside
        document.addEventListener('click', (event) => this.handleDocumentClick(event));
        // Add touch support for mobile
        document.addEventListener('touchend', (event) => this.handleDocumentClick(event));
        
        document.addEventListener('keydown', this.boundMethods.handleKeydown);
        window.addEventListener('resize', this.boundMethods.handleResize);
        
        this.setupNavLinkListeners();
    }

    handleDocumentClick(event) {
        if (!this.isOpen) return;
        
        // Check if click is outside the menu and toggle button
        const menu = this.elements.menu;
        const toggle = this.elements.toggle;
        
        const isClickOnMenu = menu && menu.contains(event.target);
        const isClickOnToggle = toggle && toggle.contains(event.target);
        const isClickOnOverlay = event.target.id === 'mobileMenuOverlay';
        
        // Close if clicked outside menu/toggle or on overlay
        if (!isClickOnMenu && !isClickOnToggle) {
            this.close();
        }
    }

    setupNavLinkListeners() {
        const navLinks = this.elements.menu.querySelectorAll('.nav-menu a');
        this.elements.navLinks = navLinks;
        
        navLinks.forEach(link => {
            link.addEventListener('click', this.boundMethods.close);
        });
    }

    toggle(event) {
        if (event) event.stopPropagation();
        
        if (this.isOpen) {
            this.close();
        } else {
            this.open();
        }
    }

    open() {
        if (this.isOpen) return;
        
        const { menu, overlay, toggle } = this.elements;
        
        menu.classList.add('active');
        overlay.classList.add('active');
        toggle.classList.add('active');
        document.body.style.overflow = 'hidden';
        
        this.isOpen = true;
    }

    close() {
        if (!this.isOpen) return;
        
        const { menu, overlay, toggle } = this.elements;
        
        menu.classList.remove('active');
        overlay.classList.remove('active');
        toggle.classList.remove('active');
        document.body.style.overflow = '';
        
        this.isOpen = false;
    }

    handleKeydown(event) {
        if (!this.isOpen) return;
        
        if (event.key === 'Escape') {
            event.preventDefault();
            this.close();
        }
    }

    handleResize() {
        if (!this.isOpen) return;
        
        if (window.innerWidth > 768) {
            this.close();
        }
    }

    destroy() {
        const { toggle, overlay } = this.elements;
        
        if (toggle) toggle.removeEventListener('click', this.boundMethods.toggle);
        if (overlay) overlay.removeEventListener('click', this.boundMethods.close);
        
        // Remove document event listeners
        document.removeEventListener('click', (event) => this.handleDocumentClick(event));
        document.removeEventListener('touchend', (event) => this.handleDocumentClick(event));
        document.removeEventListener('keydown', this.boundMethods.handleKeydown);
        window.removeEventListener('resize', this.boundMethods.handleResize);
        
        if (this.elements.navLinks) {
            this.elements.navLinks.forEach(link => {
                link.removeEventListener('click', this.boundMethods.close);
            });
        }
        
        if (this.isOpen) this.close();
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.mobileMenu = new MobileMenu();
});

window.addEventListener('beforeunload', () => {
    if (window.mobileMenu) window.mobileMenu.destroy();
});