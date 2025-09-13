/**
 * Responsive Navigation System
 * Dynamically manages navigation visibility based on available space
 * Enhanced with comprehensive error handling, logging, and accessibility features
 * 
 * Features:
 * - Dynamic space calculation and item overflow management
 * - Intelligent "More" menu population
 * - ResizeObserver support with fallbacks
 * - Priority-based navigation item management
 * - Memory leak prevention
 * - Comprehensive error handling and logging
 */

class ResponsiveNavigation {
    constructor() {
        console.log('[ResponsiveNavigation] Initializing responsive navigation system...');
        
        this.header = document.querySelector('.desktop-header');
        this.headerRight = document.querySelector('.header-right');
        this.moreDropdown = document.querySelector('.more-menu');
        this.moreMenu = document.querySelector('.more-menu .dropdown-menu');
        this.navGroups = document.querySelectorAll('.nav-group');
        
        this.originalItems = new Map();
        this.isInitialized = false;
        this.lastAvailableWidth = 0;
        
        // Cleanup functions for event listeners
        this.cleanupFunctions = [];
        
        if (this.header) {
            this.init();
        } else {
            console.warn('[ResponsiveNavigation] Header element not found, navigation will not be responsive');
        }
    }
    
    // Destroy method to prevent memory leaks
    destroy() {
        console.log('[ResponsiveNavigation] Cleaning up event listeners...');
        
        // Remove all event listeners
        this.cleanupFunctions.forEach(cleanup => {
            try {
                cleanup();
            } catch (error) {
                console.error('[ResponsiveNavigation] Error during cleanup:', error);
            }
        });
        this.cleanupFunctions = [];
        
        // Reset state
        this.isInitialized = false;
        console.log('[ResponsiveNavigation] Cleanup completed');
    }
    
    init() {
        try {
            console.log('[ResponsiveNavigation] Starting initialization...');
            
            // Store original positions of navigation items
            this.storeOriginalPositions();
            
            // Set up resize observer
            this.setupResizeObserver();
            
            // Set up dropdown functionality
            this.setupDropdowns();
            
            // Initial check with delay to ensure DOM is ready
            setTimeout(() => {
                console.log('[ResponsiveNavigation] Performing initial navigation check...');
                this.checkNavigation();
            }, 100);
            
            this.isInitialized = true;
            console.log('[ResponsiveNavigation] Initialization completed successfully');
            
        } catch (error) {
            console.error('[ResponsiveNavigation] Initialization failed:', error);
            if (window.notificationManager) {
                window.notificationManager.showError('Responsive navigation initialization failed');
            }
        }
    }
    
    storeOriginalPositions() {
        console.log('[ResponsiveNavigation] Storing original positions of navigation items...');
        
        this.navGroups.forEach((group, groupIndex) => {
            const buttons = group.querySelectorAll('.nav-button:not(.dropdown-toggle)');
            console.log(`[ResponsiveNavigation] Group ${groupIndex} has ${buttons.length} buttons`);
            
            buttons.forEach((button, buttonIndex) => {
                if (!button.closest('.more-menu')) {
                    this.originalItems.set(button, {
                        group: group,
                        groupIndex: groupIndex,
                        buttonIndex: buttonIndex,
                        originalParent: group,
                        originalNextSibling: button.nextElementSibling
                    });
                }
            });
        });
        
        console.log(`[ResponsiveNavigation] Stored ${this.originalItems.size} navigation items`);
    }
    
    setupResizeObserver() {
        console.log('[ResponsiveNavigation] Setting up resize observer...');
        
        if ('ResizeObserver' in window) {
            const resizeObserver = new ResizeObserver((entries) => {
                for (let entry of entries) {
                    if (entry.target === this.header) {
                        console.log('[ResponsiveNavigation] Header resize detected, checking navigation...');
                        this.checkNavigation();
                    }
                }
            });
            resizeObserver.observe(this.header);
            
            // Add cleanup
            this.cleanupFunctions.push(() => {
                resizeObserver.disconnect();
            });
            
            console.log('[ResponsiveNavigation] ResizeObserver setup complete');
        } else {
            // Fallback for browsers without ResizeObserver
            console.log('[ResponsiveNavigation] ResizeObserver not available, using window resize fallback');
            this.addEventListener(window, 'resize', this.debounce(() => {
                console.log('[ResponsiveNavigation] Window resize detected, checking navigation...');
                this.checkNavigation();
            }, 150));
        }
    }
    
    setupDropdowns() {
        console.log('[ResponsiveNavigation] Setting up dropdown functionality...');
        
        // Setup existing dropdowns
        document.querySelectorAll('.nav-dropdown').forEach((dropdown, index) => {
            const toggle = dropdown.querySelector('.nav-button, .dropdown-toggle');
            if (toggle) {
                console.log(`[ResponsiveNavigation] Setting up dropdown ${index}: ${toggle.textContent?.trim()}`);
                this.addEventListener(toggle, 'click', (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    console.log('[ResponsiveNavigation] Dropdown clicked:', toggle.textContent?.trim());
                    this.toggleDropdown(dropdown);
                });
            }
        });
        
        // Close dropdowns when clicking outside
        this.addEventListener(document, 'click', (e) => {
            if (!e.target.closest('.nav-dropdown')) {
                console.log('[ResponsiveNavigation] Clicked outside dropdowns, closing all');
                document.querySelectorAll('.nav-dropdown.open').forEach(dropdown => {
                    dropdown.classList.remove('open');
                });
            }
        });
        
        console.log('[ResponsiveNavigation] Dropdown setup complete');
    }
    
    toggleDropdown(dropdown) {
        // Close other dropdowns
        document.querySelectorAll('.nav-dropdown.open').forEach(other => {
            if (other !== dropdown) {
                other.classList.remove('open');
            }
        });
        
        // Toggle current dropdown
        dropdown.classList.toggle('open');
    }
    
    checkNavigation() {
        if (!this.headerRight || !this.isInitialized) {
            console.log('[ResponsiveNavigation] Navigation check skipped - not ready');
            return;
        }
        
        try {
            const headerWidth = this.header.offsetWidth;
            const availableWidth = headerWidth - this.getHeaderLeftWidth() - this.getSystemNavWidth() - 40; // 40px buffer
            
            // Skip if available width hasn't changed significantly
            if (Math.abs(availableWidth - this.lastAvailableWidth) < 20) {
                return;
            }
            this.lastAvailableWidth = availableWidth;
            
            console.log(`[ResponsiveNavigation] Navigation check - Header: ${headerWidth}px, Available: ${availableWidth}px`);
            
            // Check if navigation is overflowing
            const currentNavWidth = this.getCurrentNavWidth();
            
            console.log(`[ResponsiveNavigation] Current nav width: ${currentNavWidth}px`);
            
            if (currentNavWidth > availableWidth) {
                console.log('[ResponsiveNavigation] Navigation overflowing, moving items to more menu');
                this.moveItemsToMore();
            } else {
                console.log('[ResponsiveNavigation] Navigation has space, trying to move items back');
                this.moveItemsFromMore();
            }
            
        } catch (error) {
            console.error('[ResponsiveNavigation] Error during navigation check:', error);
            if (window.notificationManager) {
                window.notificationManager.showError('Navigation layout adjustment failed');
            }
        }
    }
    
    getHeaderLeftWidth() {
        const headerLeft = document.querySelector('.header-left');
        return headerLeft ? headerLeft.offsetWidth : 0;
    }
    
    getSystemNavWidth() {
        const systemNav = document.querySelector('.system-nav');
        return systemNav ? systemNav.offsetWidth : 0;
    }
    
    getCurrentNavWidth() {
        let width = 0;
        this.navGroups.forEach(group => {
            if (group !== this.moreDropdown?.parentElement && !group.classList.contains('system-nav')) {
                width += group.offsetWidth;
            }
        });
        return width;
    }
    
    moveItemsToMore() {
        console.log('[ResponsiveNavigation] Moving items to more menu...');
        
        const groups = Array.from(this.navGroups).filter(g => 
            g !== this.moreDropdown?.parentElement && 
            !g.classList.contains('system-nav')
        );
        
        // Start from the least important groups
        const priorityOrder = ['advanced-nav', 'creative-nav', 'core-nav'];
        let itemsMoved = 0;
        
        for (let priority of priorityOrder) {
            const group = groups.find(g => g.classList.contains(priority));
            if (!group) continue;
            
            const buttons = Array.from(group.querySelectorAll('.nav-button:not(.dropdown-toggle)'));
            console.log(`[ResponsiveNavigation] Checking ${priority} group with ${buttons.length} buttons`);
            
            // Move buttons from right to left within the group
            for (let i = buttons.length - 1; i >= 0; i--) {
                const button = buttons[i];
                if (this.getCurrentNavWidth() <= this.getAvailableWidth()) break;
                
                console.log(`[ResponsiveNavigation] Moving button to more menu: ${button.textContent?.trim()}`);
                this.moveToMoreMenu(button);
                itemsMoved++;
                
                // Show more menu if it has items
                if (this.moreMenu && this.moreMenu.children.length > 0) {
                    if (this.moreDropdown) {
                        this.moreDropdown.style.display = 'block';
                    }
                }
            }
            
            if (this.getCurrentNavWidth() <= this.getAvailableWidth()) break;
        }
        
        console.log(`[ResponsiveNavigation] Moved ${itemsMoved} items to more menu`);
    }
    
    moveItemsFromMore() {
        if (!this.moreMenu) {
            console.log('[ResponsiveNavigation] More menu not found, skipping move back');
            return;
        }
        
        const moreItems = Array.from(this.moreMenu.children);
        console.log(`[ResponsiveNavigation] Attempting to move ${moreItems.length} items back from more menu`);
        
        let itemsMoved = 0;
        
        // Try to move items back to their original positions
        moreItems.forEach(item => {
            const estimatedWidth = 100; // Approximate button width
            if (this.getCurrentNavWidth() + estimatedWidth > this.getAvailableWidth()) {
                return;
            }
            
            const originalData = this.originalItems.get(item);
            if (originalData && originalData.originalParent) {
                console.log(`[ResponsiveNavigation] Moving item back: ${item.textContent?.trim()}`);
                this.moveFromMoreMenu(item, originalData.originalParent, originalData.originalNextSibling);
                itemsMoved++;
            }
        });
        
        // Hide more menu if empty
        if (this.moreMenu.children.length === 0 && this.moreDropdown) {
            console.log('[ResponsiveNavigation] More menu is empty, hiding it');
            this.moreDropdown.style.display = 'none';
        }
        
        console.log(`[ResponsiveNavigation] Moved ${itemsMoved} items back from more menu`);
    }
    
    getAvailableWidth() {
        const headerWidth = this.header.offsetWidth;
        return headerWidth - this.getHeaderLeftWidth() - this.getSystemNavWidth() - 40;
    }
    
    moveToMoreMenu(button) {
        if (!this.moreMenu || button.closest('.more-menu')) {
            console.warn('[ResponsiveNavigation] Cannot move button to more menu - menu not found or button already there');
            return;
        }
        
        try {
            // Convert to dropdown item
            button.classList.remove('nav-button', 'primary');
            button.classList.add('dropdown-item');
            
            // Move to more menu
            this.moreMenu.appendChild(button);
            
            console.log(`[ResponsiveNavigation] Moved button to more menu: ${button.textContent?.trim()}`);
            
        } catch (error) {
            console.error('[ResponsiveNavigation] Error moving button to more menu:', error);
            if (window.notificationManager) {
                window.notificationManager.showWarning('Navigation item could not be moved to overflow menu');
            }
        }
    }
    
    moveFromMoreMenu(button, targetGroup, nextSibling = null) {
        if (!button || !targetGroup) {
            console.warn('[ResponsiveNavigation] Cannot move button from more menu - missing button or target');
            return;
        }
        
        try {
            // Convert back to nav button
            button.classList.remove('dropdown-item');
            button.classList.add('nav-button', 'primary');
            
            // Move back to original group at the correct position
            if (nextSibling && nextSibling.parentNode === targetGroup) {
                targetGroup.insertBefore(button, nextSibling);
            } else {
                targetGroup.appendChild(button);
            }
            
            console.log(`[ResponsiveNavigation] Moved button back from more menu: ${button.textContent?.trim()}`);
            
        } catch (error) {
            console.error('[ResponsiveNavigation] Error moving button from more menu:', error);
            if (window.notificationManager) {
                window.notificationManager.showWarning('Navigation item could not be restored from overflow menu');
            }
        }
    }
    
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

    // Helper method to add event listeners with cleanup tracking
    addEventListener(element, event, handler) {
        if (element && typeof element.addEventListener === 'function') {
            element.addEventListener(event, handler);
            this.cleanupFunctions.push(() => {
                element.removeEventListener(event, handler);
            });
        }
    }
}

// Initialize when DOM is ready with enhanced logging
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        console.log('[ResponsiveNavigation] DOM loaded, creating ResponsiveNavigation instance...');
        window.responsiveNavigation = new ResponsiveNavigation();
    });
} else {
    console.log('[ResponsiveNavigation] DOM already ready, creating ResponsiveNavigation instance...');
    window.responsiveNavigation = new ResponsiveNavigation();
}

// Export for potential external use
window.ResponsiveNavigation = ResponsiveNavigation;
