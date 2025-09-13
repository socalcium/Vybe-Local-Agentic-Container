/**
 * Responsive Navigation Handler for Vybe AI
 * Handles dynamic navigation resizing, hamburger menus, and overflow management
 * Enhanced with comprehensive error handling, logging, and accessibility features
 * 
 * Features:
 * - Dynamic breakpoint management
 * - Mobile hamburger menu with overlay
 * - Desktop dropdown management
 * - Overflow navigation with "More" menu
 * - Keyboard accessibility
 * - Memory leak prevention
 * - Real-time responsive adjustments
 */

class ResponsiveNavigation {
    constructor() {
        this.breakpoints = {
            mobile: 768,
            compact: 900,
            standard: 1000,
            wide: 1200,
            ultra: 1400
        };
        
        // Cleanup functions for event listeners
        this.cleanupFunctions = [];
        
        // State tracking
        this.currentBreakpoint = null;
        this.isInitialized = false;
        this.lastWidth = 0;
        
        console.log('[ResponsiveNav] Initializing responsive navigation...');
        this.init();
    }
    
    // Destroy method to prevent memory leaks
    destroy() {
        console.log('[ResponsiveNav] Cleaning up event listeners...');
        
        // Remove all event listeners
        this.cleanupFunctions.forEach(cleanup => {
            try {
                cleanup();
            } catch (error) {
                console.error('[ResponsiveNav] Error during cleanup:', error);
            }
        });
        this.cleanupFunctions = [];
        
        // Reset state
        this.isInitialized = false;
        console.log('[ResponsiveNav] Cleanup completed');
    }

    // Helper method to add event listeners with cleanup tracking
    addEventListener(element, event, handler) {
        if (element && typeof element.addEventListener === 'function') {
            element.addEventListener(event, handler);
            this.cleanupFunctions.push(() => {
                element.removeEventListener(event, handler);
            });
        }
    }

    // Debounce utility method
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
    
    init() {
        try {
            console.log('[ResponsiveNav] Starting initialization...');
            
            this.bindEvents();
            this.handleResize();
            this.setupMobileMenu();
            this.setupDropdowns();
            
            // Enhanced resize handling with debouncing
            this.addEventListener(window, 'resize', this.debounce(() => {
                console.log('[ResponsiveNav] Window resized, updating layout...');
                this.handleResize();
            }, 100));
            
            this.addEventListener(document, 'DOMContentLoaded', () => {
                console.log('[ResponsiveNav] DOM loaded, performing initial resize...');
                this.handleResize();
            });
            
            // Keyboard accessibility
            this.addEventListener(document, 'keydown', (e) => {
                this.handleKeyboardNavigation(e);
            });
            
            this.isInitialized = true;
            console.log('[ResponsiveNav] Initialization completed successfully');
            
        } catch (error) {
            console.error('[ResponsiveNav] Initialization failed:', error);
            if (window.notificationManager) {
                window.notificationManager.showError('Navigation initialization failed');
            }
        }
    }
    
    bindEvents() {
        console.log('[ResponsiveNav] Binding events...');
        
        try {
            // Mobile menu toggle
            const mobileMenuToggle = document.getElementById('mobile-menu-toggle');
            const mobileNavOverlay = document.getElementById('mobile-nav-overlay');
            const mobileNavClose = document.getElementById('mobile-nav-close');
            
            if (mobileMenuToggle) {
                this.addEventListener(mobileMenuToggle, 'click', () => {
                    console.log('[ResponsiveNav] Mobile menu toggle clicked');
                    this.toggleMobileMenu();
                });
            }
            
            if (mobileNavClose) {
                this.addEventListener(mobileNavClose, 'click', () => {
                    console.log('[ResponsiveNav] Mobile menu close clicked');
                    this.closeMobileMenu();
                });
            }
            
            if (mobileNavOverlay) {
                this.addEventListener(mobileNavOverlay, 'click', (e) => {
                    if (e.target === mobileNavOverlay) {
                        console.log('[ResponsiveNav] Mobile overlay clicked, closing menu');
                        this.closeMobileMenu();
                    }
                });
            }
            
            // Desktop dropdown toggles
            document.querySelectorAll('.nav-dropdown').forEach(dropdown => {
                const button = dropdown.querySelector('.nav-button');
                const menu = dropdown.querySelector('.dropdown-menu');
                
                if (button && menu) {
                    this.addEventListener(button, 'click', (e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        console.log('[ResponsiveNav] Dropdown toggle clicked:', button.textContent?.trim());
                        this.toggleDropdown(dropdown);
                    });
                }
            });
            
            // Close dropdowns when clicking outside
            this.addEventListener(document, 'click', (e) => {
                if (!e.target.closest('.nav-dropdown')) {
                    this.closeAllDropdowns();
                }
            });
            
            console.log('[ResponsiveNav] Events bound successfully');
            
        } catch (error) {
            console.error('[ResponsiveNav] Error binding events:', error);
            if (window.notificationManager) {
                window.notificationManager.showError('Navigation events binding failed');
            }
        }
    }
    
    handleResize() {
        const width = window.innerWidth;
        
        // Skip unnecessary reflows if width hasn't changed significantly
        if (Math.abs(width - this.lastWidth) < 10) {
            return;
        }
        this.lastWidth = width;
        
        console.log(`[ResponsiveNav] Handling resize: ${width}px`);
        
        // Determine current breakpoint
        let currentBreakpoint = 'ultra';
        if (width <= this.breakpoints.mobile) {
            currentBreakpoint = 'mobile';
        } else if (width <= this.breakpoints.compact) {
            currentBreakpoint = 'compact';
        } else if (width <= this.breakpoints.standard) {
            currentBreakpoint = 'standard';
        } else if (width <= this.breakpoints.wide) {
            currentBreakpoint = 'wide';
        }
        
        // Only update if breakpoint has changed
        if (this.currentBreakpoint !== currentBreakpoint) {
            console.log(`[ResponsiveNav] Breakpoint changed: ${this.currentBreakpoint} → ${currentBreakpoint}`);
            this.currentBreakpoint = currentBreakpoint;
            
            // Apply responsive classes
            document.body.className = document.body.className.replace(/nav-\w+/g, '');
            document.body.classList.add(`nav-${currentBreakpoint}`);
        }
        
        // Handle desktop navigation layout
        if (width > this.breakpoints.mobile) {
            this.handleDesktopLayout();
        }
        
        // Close mobile menu if switched to desktop
        if (width > this.breakpoints.mobile) {
            this.closeMobileMenu();
        }
    }
    
    handleDesktopLayout() {
        console.log('[ResponsiveNav] Handling desktop layout...');
        
        try {
            const extendedNavItems = document.querySelectorAll('.nav-button.extended');
            const moreNav = document.getElementById('more-nav');
            const moreDropdown = document.getElementById('more-dropdown');
            
            if (!moreNav || !moreDropdown) {
                console.warn('[ResponsiveNav] More nav elements not found');
                return;
            }
            
            // Reset all items to visible first
            extendedNavItems.forEach(item => {
                item.style.display = 'flex';
                item.classList.remove('nav-hidden');
            });
            moreNav.style.display = 'none';
            moreDropdown.innerHTML = '';
            
            // Calculate available space and hide items that don't fit
            const headerCenter = document.querySelector('.header-center');
            const coreNav = document.querySelector('.core-nav');
            const extendedNav = document.querySelector('.extended-nav');
            
            if (!headerCenter || !coreNav || !extendedNav) {
                console.warn('[ResponsiveNav] Required layout elements not found');
                return;
            }
            
            const availableWidth = headerCenter.offsetWidth;
            const coreWidth = coreNav.offsetWidth;
            const settingsWidth = 120; // Approximate width of settings dropdown
            const moreButtonWidth = 80; // Width of "More" button
            
            let usedWidth = coreWidth + settingsWidth;
            const hiddenItems = [];
            
            console.log(`[ResponsiveNav] Layout calculation - Available: ${availableWidth}px, Core: ${coreWidth}px`);
            
            // Check each extended item
            extendedNavItems.forEach((item, index) => {
                const itemWidth = item.offsetWidth || 100; // Fallback width
                
                if (usedWidth + itemWidth + moreButtonWidth > availableWidth) {
                    // Hide this item and add to "More" menu
                    item.style.display = 'none';
                    item.classList.add('nav-hidden');
                    hiddenItems.push(item);
                    console.log(`[ResponsiveNav] Hiding item ${index}: ${item.textContent?.trim()}`);
                } else {
                    usedWidth += itemWidth;
                }
            });
            
            // Show "More" button if we have hidden items
            if (hiddenItems.length > 0) {
                moreNav.style.display = 'flex';
                console.log(`[ResponsiveNav] Showing "More" menu with ${hiddenItems.length} items`);
                
                // Add hidden items to dropdown
                hiddenItems.forEach(item => {
                    const dropdownItem = document.createElement('a');
                    dropdownItem.href = item.href || '#';
                    dropdownItem.className = 'dropdown-item';
                    
                    const icon = item.querySelector('.nav-icon');
                    const label = item.querySelector('.nav-label');
                    
                    dropdownItem.innerHTML = `
                        ${icon ? icon.outerHTML : ''}
                        ${label ? label.textContent : item.textContent?.trim() || 'Menu Item'}
                    `;
                    moreDropdown.appendChild(dropdownItem);
                });
            }
            
        } catch (error) {
            console.error('[ResponsiveNav] Error in desktop layout:', error);
        }
    }
    
    setupMobileMenu() {
        // Set active state for current page in mobile menu
        const currentPage = window.location.pathname;
        const mobileNavItems = document.querySelectorAll('.mobile-nav-item');
        
        mobileNavItems.forEach(item => {
            if (item.getAttribute('href') === currentPage) {
                item.classList.add('active');
            }
        });
    }
    
    setupDropdowns() {
        // Set active state for current page in dropdowns
        const currentPage = window.location.pathname;
        const dropdownItems = document.querySelectorAll('.dropdown-item');
        
        dropdownItems.forEach(item => {
            if (item.getAttribute('href') === currentPage) {
                item.classList.add('active');
            }
        });
        
        // If settings dropdown has no menu items, clicking it should navigate
        document.querySelectorAll('.nav-dropdown .nav-button.settings').forEach(btn => {
            const menu = btn.parentElement?.querySelector('.dropdown-menu');
            if (!menu || menu.children.length === 0) {
                this.addEventListener(btn, 'click', (e) => {
                    e.preventDefault();
                    window.location.href = btn.getAttribute('href') || '/settings';
                });
            }
        });
    }
    
    toggleMobileMenu() {
        const overlay = document.getElementById('mobile-nav-overlay');
        const toggle = document.getElementById('mobile-menu-toggle');
        
        if (overlay && toggle) {
            const isOpen = overlay.classList.contains('active');
            
            if (isOpen) {
                this.closeMobileMenu();
            } else {
                this.openMobileMenu();
            }
        }
    }
    
    openMobileMenu() {
        const overlay = document.getElementById('mobile-nav-overlay');
        const toggle = document.getElementById('mobile-menu-toggle');
        
        if (overlay && toggle) {
            overlay.classList.add('active');
            toggle.classList.add('active');
            document.body.classList.add('mobile-menu-open');
            
            // Prevent body scroll
            document.body.style.overflow = 'hidden';
        }
    }
    
    closeMobileMenu() {
        const overlay = document.getElementById('mobile-nav-overlay');
        const toggle = document.getElementById('mobile-menu-toggle');
        
        if (overlay && toggle) {
            overlay.classList.remove('active');
            toggle.classList.remove('active');
            document.body.classList.remove('mobile-menu-open');
            
            // Restore body scroll
            document.body.style.overflow = '';
        }
    }
    
    toggleDropdown(dropdown) {
        const isOpen = dropdown.classList.contains('open');
        
        // Close all other dropdowns
        this.closeAllDropdowns();
        
        if (!isOpen) {
            dropdown.classList.add('open');
            const button = dropdown.querySelector('.nav-button');
            if (button) {
                button.setAttribute('aria-expanded', 'true');
            }
        }
    }
    
    closeAllDropdowns() {
        document.querySelectorAll('.nav-dropdown').forEach(dropdown => {
            dropdown.classList.remove('open');
            const button = dropdown.querySelector('.nav-button');
            if (button) {
                button.setAttribute('aria-expanded', 'false');
            }
        });
    }
    
    // Public API for manual control
    setActiveNavItem(page) {
        console.log(`[ResponsiveNav] Setting active nav item: ${page}`);
        
        // Remove active from all nav items
        document.querySelectorAll('.nav-button, .mobile-nav-item, .dropdown-item').forEach(item => {
            item.classList.remove('active');
        });
        
        // Add active to matching items
        document.querySelectorAll(`[data-page="${page}"], [href*="${page}"]`).forEach(item => {
            item.classList.add('active');
        });
    }
    
    // Keyboard navigation handler
    handleKeyboardNavigation(event) {
        // Escape key closes all dropdowns and mobile menu
        if (event.key === 'Escape') {
            this.closeAllDropdowns();
            this.closeMobileMenu();
            return;
        }
        
        // Alt + M toggles mobile menu
        if (event.altKey && event.key === 'm') {
            event.preventDefault();
            this.toggleMobileMenu();
            return;
        }
        
        // Tab navigation for accessibility
        if (event.key === 'Tab') {
            // Let browser handle tab navigation naturally
            return;
        }
    }
    
    refresh() {
        console.log('[ResponsiveNav] Refreshing navigation...');
        this.handleResize();
    }
}

// Initialize responsive navigation
let responsiveNav;
document.addEventListener('DOMContentLoaded', () => {
    console.log('[ResponsiveNav] DOM loaded, creating ResponsiveNavigation instance...');
    responsiveNav = new ResponsiveNavigation();
});

// Export for external use
window.ResponsiveNavigation = ResponsiveNavigation;
window.getResponsiveNav = () => responsiveNav;
