/**
 * iOS-inspired Mobile Navigation Controller
 * Handles mobile menu interactions and desktop dropdown functionality
 */

class MobileNavigation {
    constructor() {
        this.isMenuOpen = false;
        this.isUserMenuOpen = false;
        this.touchStartY = 0;
        this.touchStartX = 0;
        
        this.init();
    }
    
    init() {
        this.bindEvents();
        this.setupSwipeGestures();
        this.setupDropdowns();
        this.handleResize();
    }
    
    bindEvents() {
        // Mobile menu toggle
        const menuToggle = document.getElementById('mobileMenuToggle');
        const menuClose = document.getElementById('mobileNavClose');
        const menuOverlay = document.getElementById('mobileNavOverlay');
        
        if (menuToggle) {
            menuToggle.addEventListener('click', () => this.toggleMobileMenu());
        }
        
        if (menuClose) {
            menuClose.addEventListener('click', () => this.closeMobileMenu());
        }
        
        if (menuOverlay) {
            menuOverlay.addEventListener('click', (e) => {
                if (e.target === menuOverlay) {
                    this.closeMobileMenu();
                }
            });
        }
        
        // Mobile user menu
        const userBtn = document.getElementById('mobileUserBtn');
        
        if (userBtn) {
            userBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.toggleUserMenu();
            });
        }
        
        // Close menus when clicking outside
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.mobile-user-menu') && !e.target.closest('#mobileUserBtn')) {
                this.closeUserMenu();
            }
            
            if (!e.target.closest('.nav-dropdown')) {
                this.closeAllDropdowns();
            }
        });
        
        // Handle navigation clicks
        const navItems = document.querySelectorAll('.mobile-nav-item');
        navItems.forEach(item => {
            item.addEventListener('click', () => {
                // Add iOS-style selection feedback
                this.addSelectionFeedback(item);
                // Close menu after short delay for visual feedback
                setTimeout(() => this.closeMobileMenu(), 150);
            });
        });
        
        // Escape key handling
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.closeMobileMenu();
                this.closeUserMenu();
                this.closeAllDropdowns();
            }
        });
        
        // Handle window resize
        window.addEventListener('resize', () => this.handleResize());
    }
    
    setupSwipeGestures() {
        const overlay = document.getElementById('mobileNavOverlay');
        const content = document.querySelector('.mobile-nav-content');
        
        if (!overlay || !content) return;
        
        // Touch events for swipe to close
        overlay.addEventListener('touchstart', (e) => {
            this.touchStartX = e.touches[0].clientX;
            this.touchStartY = e.touches[0].clientY;
        }, { passive: true });
        
        overlay.addEventListener('touchmove', (e) => {
            if (!this.isMenuOpen) return;
            
            const touchX = e.touches[0].clientX;
            const deltaX = this.touchStartX - touchX;
            
            // Only allow left swipe on menu content
            if (deltaX > 0 && touchX < content.offsetWidth) {
                const progress = Math.min(deltaX / 200, 1);
                content.style.transform = `translateX(-${progress * 100}%)`;
                overlay.style.opacity = 1 - progress;
            }
        }, { passive: true });
        
        overlay.addEventListener('touchend', (e) => {
            if (!this.isMenuOpen) return;
            
            const touchX = e.changedTouches[0].clientX;
            const deltaX = this.touchStartX - touchX;
            
            // Reset styles
            content.style.transform = '';
            overlay.style.opacity = '';
            
            // Close if swipe was significant
            if (deltaX > 100) {
                this.closeMobileMenu();
            }
        }, { passive: true });
    }
    
    setupDropdowns() {
        const dropdowns = document.querySelectorAll('.nav-dropdown');
        
        dropdowns.forEach(dropdown => {
            const toggle = dropdown.querySelector('.dropdown-toggle');
            
            if (toggle) {
                toggle.addEventListener('click', (e) => {
                    e.stopPropagation();
                    this.toggleDropdown(dropdown);
                });
            }
        });
    }
    
    toggleMobileMenu() {
        if (this.isMenuOpen) {
            this.closeMobileMenu();
        } else {
            this.openMobileMenu();
        }
    }
    
    openMobileMenu() {
        const overlay = document.getElementById('mobileNavOverlay');
        const toggle = document.getElementById('mobileMenuToggle');
        
        if (overlay && toggle) {
            this.isMenuOpen = true;
            overlay.classList.add('active');
            toggle.classList.add('active');
            
            // Prevent body scroll on iOS
            document.body.style.overflow = 'hidden';
            document.body.style.position = 'fixed';
            document.body.style.width = '100%';
            
            // Focus trap
            this.trapFocus(overlay);
        }
    }
    
    closeMobileMenu() {
        const overlay = document.getElementById('mobileNavOverlay');
        const toggle = document.getElementById('mobileMenuToggle');
        
        if (overlay && toggle) {
            this.isMenuOpen = false;
            overlay.classList.remove('active');
            toggle.classList.remove('active');
            
            // Restore body scroll
            document.body.style.overflow = '';
            document.body.style.position = '';
            document.body.style.width = '';
        }
    }
    
    toggleUserMenu() {
        if (this.isUserMenuOpen) {
            this.closeUserMenu();
        } else {
            this.openUserMenu();
        }
    }
    
    openUserMenu() {
        const menu = document.getElementById('mobileUserMenu');
        
        if (menu) {
            this.isUserMenuOpen = true;
            menu.classList.add('active');
        }
    }
    
    closeUserMenu() {
        const menu = document.getElementById('mobileUserMenu');
        
        if (menu) {
            this.isUserMenuOpen = false;
            menu.classList.remove('active');
        }
    }
    
    toggleDropdown(dropdown) {
        const isOpen = dropdown.classList.contains('open');
        
        // Close all other dropdowns
        this.closeAllDropdowns();
        
        if (!isOpen) {
            dropdown.classList.add('open');
            
            // Position dropdown if it goes off screen
            const menu = dropdown.querySelector('.dropdown-menu');
            if (menu) {
                const rect = menu.getBoundingClientRect();
                if (rect.right > window.innerWidth) {
                    menu.style.left = 'auto';
                    menu.style.right = '0';
                }
            }
        }
    }
    
    closeAllDropdowns() {
        const dropdowns = document.querySelectorAll('.nav-dropdown');
        dropdowns.forEach(dropdown => {
            dropdown.classList.remove('open');
        });
    }
    
    addSelectionFeedback(element) {
        // iOS-style selection feedback
        element.style.transform = 'scale(0.95)';
        element.style.opacity = '0.6';
        
        setTimeout(() => {
            element.style.transform = '';
            element.style.opacity = '';
        }, 150);
    }
    
    trapFocus(container) {
        const focusableElements = container.querySelectorAll(
            'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        );
        
        if (focusableElements.length === 0) return;
        
        const firstElement = focusableElements[0];
        const lastElement = focusableElements[focusableElements.length - 1];
        
        // Focus first element
        firstElement.focus();
        
        container.addEventListener('keydown', (e) => {
            if (e.key === 'Tab') {
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
            }
        });
    }
    
    handleResize() {
        // Close mobile menu if screen becomes desktop size
        if (window.innerWidth > 768 && this.isMenuOpen) {
            this.closeMobileMenu();
        }
        
        // Close all menus on orientation change
        if (window.orientation !== undefined) {
            this.closeMobileMenu();
            this.closeUserMenu();
            this.closeAllDropdowns();
        }
    }
    
    // Public method to set active navigation item
    setActiveNavItem(page) {
        // Remove active class from all nav items
        const allNavItems = document.querySelectorAll('[data-page]');
        allNavItems.forEach(item => item.classList.remove('active'));
        
        // Add active class to current page
        const activeItems = document.querySelectorAll(`[data-page="${page}"]`);
        activeItems.forEach(item => item.classList.add('active'));
    }
}

// Initialize mobile navigation when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.mobileNav = new MobileNavigation();
    
    // Set active nav item based on current page
    const currentPath = window.location.pathname;
    let activePage = 'chat'; // default
    
    if (currentPath.includes('/rpg')) activePage = 'rpg';
    else if (currentPath.includes('/search')) activePage = 'search';
    else if (currentPath.includes('/settings')) activePage = 'settings';
    
    window.mobileNav.setActiveNavItem(activePage);
});

// Handle page visibility changes (iOS optimization)
document.addEventListener('visibilitychange', () => {
    if (document.hidden && window.mobileNav) {
        window.mobileNav.closeMobileMenu();
        window.mobileNav.closeUserMenu();
        window.mobileNav.closeAllDropdowns();
    }
});
