// Global JavaScript functionality - loaded on all pages

// Enhanced toast notification function with fallback support
function showToast(message, type = 'info') {
    console.log(`[Global Toast: ${type}] ${message}`);
    
    // Try to use global toast manager if available
    if (window.showToast && typeof window.showToast === 'function') {
        window.showToast(message, type);
        return;
    }
    
    // Use VybeGlobal notification system if available
    if (window.VybeGlobal && window.VybeGlobal.showNotification) {
        window.VybeGlobal.showNotification(message, type);
        return;
    }
    
    // Fallback to simple notification display
    const notification = document.createElement('div');
    notification.className = `toast toast-${type}`;
    notification.textContent = message;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: ${type === 'error' ? '#dc3545' : type === 'success' ? '#28a745' : '#007bff'};
        color: white;
        padding: 12px 20px;
        border-radius: 6px;
        z-index: 10000;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        max-width: 350px;
    `;
    
    document.body.appendChild(notification);
    setTimeout(() => {
        if (notification.parentNode) {
            notification.parentNode.removeChild(notification);
        }
    }, 5000);
}

// Enhanced initialization with error handling
const initializeGlobal = () => {
    console.log('[Global] Initializing global functionality...');
    
    try {
        initializeTheme();
        console.log('[Global] Theme initialized');
    } catch (error) {
        console.error('[Global] Error initializing theme:', error);
        showToast('Failed to initialize theme system', 'error');
    }
    
    try {
        initializeHeader();
        console.log('[Global] Header functionality initialized');
    } catch (error) {
        console.error('[Global] Error initializing header:', error);
        showToast('Failed to initialize header functionality', 'error');
    }
    
    try {
        initializeMobileNavigation();
        console.log('[Global] Mobile navigation initialized');
    } catch (error) {
        console.error('[Global] Error initializing mobile navigation:', error);
        showToast('Failed to initialize mobile navigation', 'error');
    }
    
    console.log('[Global] Global initialization complete');
    showToast('Application ready', 'success');
};

// Enhanced event listener with fallback
if (window.eventManager && window.eventManager.add) {
    window.eventManager.add(document, 'DOMContentLoaded', initializeGlobal);
} else {
    document.addEventListener('DOMContentLoaded', initializeGlobal);
}

// Enhanced theme initialization with better error handling and user feedback
function initializeTheme() {
    console.log('[Global Theme] Initializing theme system...');
    
    try {
        // Get saved theme or default to dark
        const savedTheme = localStorage.getItem('vybe_theme') || 'dark';
        console.log(`[Global Theme] Applying saved theme: ${savedTheme}`);
        
        // Apply theme immediately
        document.documentElement.setAttribute('data-theme', savedTheme);
        document.body.classList.remove('theme-light', 'theme-dark');
        document.body.classList.add(`theme-${savedTheme}`);
        
        // Update any theme toggles that might exist
        const themeToggles = document.querySelectorAll('.theme-toggle');
        themeToggles.forEach(toggle => {
            try {
                if (toggle.type === 'checkbox') {
                    toggle.checked = savedTheme === 'dark';
                    
                    // Add change event listener
                    const handleThemeToggle = (e) => {
                        try {
                            const newTheme = e.target.checked ? 'dark' : 'light';
                            console.log(`[Global Theme] Toggle switching to: ${newTheme}`);
                            setTheme(newTheme);
                            showToast(`Switched to ${newTheme} theme`, 'success');
                        } catch (error) {
                            console.error('[Global Theme] Error in toggle handler:', error);
                            showToast('Failed to change theme', 'error');
                        }
                    };
                    
                    // Remove existing listener to prevent duplicates
                    toggle.removeEventListener('change', handleThemeToggle);
                    toggle.addEventListener('change', handleThemeToggle);
                }
            } catch (error) {
                console.warn('[Global Theme] Error setting up theme toggle:', error);
            }
        });
        
        console.log(`[Global Theme] Theme system initialized with: ${savedTheme}`);
        
    } catch (error) {
        console.error('[Global Theme] Critical error during theme initialization:', error);
        // Fallback to dark theme
        document.documentElement.setAttribute('data-theme', 'dark');
        document.body.classList.add('theme-dark');
        throw error;
    }
}

// Enhanced theme setting function
function setTheme(theme) {
    if (!theme || (theme !== 'light' && theme !== 'dark')) {
        console.warn(`[Global Theme] Invalid theme: ${theme}, defaulting to dark`);
        theme = 'dark';
    }
    
    try {
        console.log(`[Global Theme] Setting theme to: ${theme}`);
        
        // Update DOM
        document.documentElement.setAttribute('data-theme', theme);
        document.body.classList.remove('theme-light', 'theme-dark');
        document.body.classList.add(`theme-${theme}`);
        
        // Save to localStorage
        localStorage.setItem('vybe_theme', theme);
        
        // Update all theme toggles
        const themeToggles = document.querySelectorAll('.theme-toggle');
        themeToggles.forEach(toggle => {
            if (toggle.type === 'checkbox') {
                toggle.checked = theme === 'dark';
            }
        });
        
        // Dispatch custom event for other components
        window.dispatchEvent(new CustomEvent('themeChanged', { 
            detail: { theme: theme } 
        }));
        
        console.log(`[Global Theme] Theme successfully set to: ${theme}`);
        
    } catch (error) {
        console.error('[Global Theme] Error setting theme:', error);
        showToast('Failed to save theme preference', 'error');
        throw error;
    }
}

// Enhanced header initialization with robust dropdown handling
function initializeHeader() {
    console.log('[Global Header] Initializing header functionality...');
    
    try {
        // Enhanced user menu dropdown functionality
        const userMenuButton = document.querySelector('.user-menu-button');
        const userDropdown = document.querySelector('.user-dropdown');
        
        if (userMenuButton && userDropdown) {
            console.log('[Global Header] Setting up user menu dropdown');
            
            const handleUserMenuToggle = (e) => {
                try {
                    e.preventDefault();
                    e.stopPropagation();
                    
                    const isOpen = userDropdown.classList.contains('show');
                    
                    // Close all other dropdowns first
                    document.querySelectorAll('.dropdown-menu.open, .dropdown-menu.show').forEach(menu => {
                        if (menu !== userDropdown) {
                            menu.classList.remove('open', 'show', 'active');
                        }
                    });
                    
                    // Toggle user dropdown
                    userDropdown.classList.toggle('show');
                    console.log(`[Global Header] User dropdown ${isOpen ? 'closed' : 'opened'}`);
                    
                } catch (error) {
                    console.error('[Global Header] Error in user menu toggle:', error);
                    showToast('Dropdown menu error', 'error');
                }
            };
            
            // Use eventManager if available, otherwise fall back to direct event listener
            if (window.eventManager && window.eventManager.add) {
                window.eventManager.add(userMenuButton, 'click', handleUserMenuToggle);
            } else {
                userMenuButton.addEventListener('click', handleUserMenuToggle);
            }
        }
        
        // Enhanced universal dropdown functionality
        const allDropdownToggles = document.querySelectorAll('.dropdown-toggle');
        console.log(`[Global Header] Found ${allDropdownToggles.length} dropdown toggles`);
        
        allDropdownToggles.forEach((toggle, index) => {
            try {
                const handleDropdownToggle = function(e) {
                    try {
                        e.preventDefault();
                        e.stopPropagation();
                        
                        // Find the dropdown menu (could be sibling or in parent)
                        let menu = this.nextElementSibling;
                        if (!menu || !menu.classList.contains('dropdown-menu')) {
                            menu = this.parentElement.querySelector('.dropdown-menu');
                        }
                        
                        if (menu) {
                            const isOpen = menu.classList.contains('open') || menu.classList.contains('show');
                            
                            // Close other dropdowns
                            document.querySelectorAll('.dropdown-menu.open, .dropdown-menu.show').forEach(otherMenu => {
                                if (otherMenu !== menu) {
                                    otherMenu.classList.remove('open', 'show', 'active');
                                }
                            });
                            document.querySelectorAll('.nav-dropdown.active').forEach(dropdown => {
                                if (!dropdown.contains(menu)) {
                                    dropdown.classList.remove('active');
                                }
                            });
                            
                            // Toggle current dropdown
                            menu.classList.toggle('open');
                            menu.classList.toggle('show');
                            const parentDropdown = this.closest('.nav-dropdown');
                            if (parentDropdown) {
                                parentDropdown.classList.toggle('active');
                            }
                            
                            console.log(`[Global Header] Dropdown ${index} ${isOpen ? 'closed' : 'opened'}`);
                            
                        } else {
                            console.warn(`[Global Header] No dropdown menu found for toggle ${index}`);
                        }
                        
                    } catch (error) {
                        console.error(`[Global Header] Error in dropdown toggle ${index}:`, error);
                        showToast('Dropdown error', 'error');
                    }
                };
                
                // Use eventManager if available
                if (window.eventManager && window.eventManager.add) {
                    window.eventManager.add(toggle, 'click', handleDropdownToggle);
                } else {
                    toggle.addEventListener('click', handleDropdownToggle);
                }
                
            } catch (error) {
                console.error(`[Global Header] Error setting up dropdown toggle ${index}:`, error);
            }
        });
        
        // Enhanced outside click handler to close dropdowns
        const handleOutsideClick = (e) => {
            try {
                // Check if click is outside all dropdowns
                const isInsideDropdown = e.target.closest('.dropdown-toggle, .dropdown-menu, .user-menu-button, .user-dropdown, .nav-dropdown');
                
                if (!isInsideDropdown) {
                    // Close all dropdowns
                    document.querySelectorAll('.dropdown-menu.open, .dropdown-menu.show').forEach(menu => {
                        menu.classList.remove('open', 'show', 'active');
                    });
                    document.querySelectorAll('.nav-dropdown.active').forEach(dropdown => {
                        dropdown.classList.remove('active');
                    });
                    document.querySelectorAll('.user-dropdown.show').forEach(dropdown => {
                        dropdown.classList.remove('show');
                    });
                }
            } catch (error) {
                console.error('[Global Header] Error in outside click handler:', error);
            }
        };
        
        // Use eventManager if available
        if (window.eventManager && window.eventManager.add) {
            window.eventManager.add(document, 'click', handleOutsideClick);
        } else {
            document.addEventListener('click', handleOutsideClick);
        }
        
        console.log('[Global Header] Header functionality initialized successfully');
        
    } catch (error) {
        console.error('[Global Header] Critical error during header initialization:', error);
        throw error;
    }
}
    //     
    //     if (trigger && menu) {
    //         window.eventManager.add(trigger, click, function(e, {}) {
    //             e.preventDefault();
    //             e.stopPropagation();
    //             
    //             // Close other dropdowns
    //             navDropdowns.forEach(otherDropdown => {
    //                 if (otherDropdown !== dropdown) {
    //                     otherDropdown.querySelector('.nav-dropdown-menu')?.classList.remove('show');
    //                 }
    //             });
    //             
    //             menu.classList.toggle('show');
    //         });
    //         
    //         // Close dropdown when clicking outside
    //         window.eventManager.add(document, click, function(e, {}) {
    //             if (!dropdown.contains(e.target)) {
    //                 menu.classList.remove('show');
    //             }
    //         });
    //     }
    // });
    
    // Tools dropdown functionality (specific handling for header)
    const toolsDropdown = document.getElementById('toolsDropdown');
    if (toolsDropdown) {
        const dropdownToggle = toolsDropdown.querySelector('.dropdown-toggle');
        const dropdownMenu = toolsDropdown.querySelector('.dropdown-menu');
        
        if (dropdownToggle && dropdownMenu) {
            window.eventManager.add(dropdownToggle, 'click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                
                // Close other dropdowns first
                document.querySelectorAll('.dropdown-menu.open, .dropdown-menu.show').forEach(menu => {
                    if (menu !== dropdownMenu) {
                        menu.classList.remove('open', 'show', 'active');
                    }
                });
                
                // Toggle tools dropdown
                toolsDropdown.classList.toggle('active');
                dropdownMenu.classList.toggle('show');
            });
        }
    }

// Enhanced mobile navigation with robust error handling
function initializeMobileNavigation() {
    console.log('[Global Mobile] Initializing mobile navigation...');
    
    try {
        // Enhanced mobile menu toggle functionality
        const mobileMenuButton = document.querySelector('.mobile-menu-button');
        const mobileNavOverlay = document.querySelector('.mobile-nav-overlay');
        const mobileNavClose = document.querySelector('.mobile-nav-close');
        
        if (mobileMenuButton && mobileNavOverlay) {
            console.log('[Global Mobile] Setting up mobile menu toggle');
            
            const openMobileNav = (e) => {
                try {
                    e.preventDefault();
                    console.log('[Global Mobile] Opening mobile navigation');
                    mobileNavOverlay.classList.add('show');
                    document.body.style.overflow = 'hidden';
                    document.body.classList.add('mobile-nav-open');
                    showToast('Navigation opened', 'info');
                } catch (error) {
                    console.error('[Global Mobile] Error opening mobile nav:', error);
                    showToast('Failed to open navigation', 'error');
                }
            };
            
            // Close mobile nav function with error handling
            const closeMobileNav = () => {
                try {
                    console.log('[Global Mobile] Closing mobile navigation');
                    mobileNavOverlay.classList.remove('show');
                    document.body.style.overflow = '';
                    document.body.classList.remove('mobile-nav-open');
                } catch (error) {
                    console.error('[Global Mobile] Error closing mobile nav:', error);
                    showToast('Navigation close error', 'error');
                }
            };
            
            // Use eventManager if available
            if (window.eventManager && window.eventManager.add) {
                window.eventManager.add(mobileMenuButton, 'click', openMobileNav);
                
                // Close button handler
                if (mobileNavClose) {
                    window.eventManager.add(mobileNavClose, 'click', closeMobileNav);
                }
                
                // Close on overlay click
                window.eventManager.add(mobileNavOverlay, 'click', function(e) {
                    if (e.target === mobileNavOverlay) {
                        closeMobileNav();
                    }
                });
                
                // Close on escape key with debouncing
                if (window.eventManager.debounce) {
                    window.eventManager.add(document, 'keydown', window.eventManager.debounce(function(e) {
                        if (e.key === 'Escape' && mobileNavOverlay.classList.contains('show')) {
                            closeMobileNav();
                        }
                    }, 100));
                } else {
                    // Fallback without debouncing
                    window.eventManager.add(document, 'keydown', function(e) {
                        if (e.key === 'Escape' && mobileNavOverlay.classList.contains('show')) {
                            closeMobileNav();
                        }
                    });
                }
            } else {
                // Fallback to direct event listeners
                mobileMenuButton.addEventListener('click', openMobileNav);
                if (mobileNavClose) {
                    mobileNavClose.addEventListener('click', closeMobileNav);
                }
                mobileNavOverlay.addEventListener('click', function(e) {
                    if (e.target === mobileNavOverlay) {
                        closeMobileNav();
                    }
                });
                document.addEventListener('keydown', function(e) {
                    if (e.key === 'Escape' && mobileNavOverlay.classList.contains('show')) {
                        closeMobileNav();
                    }
                });
            }
        }
        
        // Enhanced mobile user menu functionality
        const mobileUserButton = document.querySelector('.mobile-user-button');
        const mobileUserMenu = document.querySelector('.mobile-user-menu');
        const mobileUserClose = document.querySelector('.mobile-user-close');
        
        if (mobileUserButton && mobileUserMenu) {
            console.log('[Global Mobile] Setting up mobile user menu');
            
            const openMobileUserMenu = (e) => {
                try {
                    e.preventDefault();
                    console.log('[Global Mobile] Opening mobile user menu');
                    mobileUserMenu.classList.add('show');
                    document.body.style.overflow = 'hidden';
                    document.body.classList.add('mobile-user-menu-open');
                } catch (error) {
                    console.error('[Global Mobile] Error opening mobile user menu:', error);
                    showToast('Failed to open user menu', 'error');
                }
            };
            
            const closeMobileUserMenu = () => {
                try {
                    console.log('[Global Mobile] Closing mobile user menu');
                    mobileUserMenu.classList.remove('show');
                    document.body.style.overflow = '';
                    document.body.classList.remove('mobile-user-menu-open');
                } catch (error) {
                    console.error('[Global Mobile] Error closing mobile user menu:', error);
                    showToast('User menu close error', 'error');
                }
            };
            
            // Use eventManager if available
            if (window.eventManager && window.eventManager.add) {
                window.eventManager.add(mobileUserButton, 'click', openMobileUserMenu);
                
                if (mobileUserClose) {
                    window.eventManager.add(mobileUserClose, 'click', closeMobileUserMenu);
                }
                
                // Close on overlay click
                window.eventManager.add(mobileUserMenu, 'click', function(e) {
                    if (e.target === mobileUserMenu) {
                        closeMobileUserMenu();
                    }
                });
            } else {
                // Fallback to direct event listeners
                mobileUserButton.addEventListener('click', openMobileUserMenu);
                if (mobileUserClose) {
                    mobileUserClose.addEventListener('click', closeMobileUserMenu);
                }
                mobileUserMenu.addEventListener('click', function(e) {
                    if (e.target === mobileUserMenu) {
                        closeMobileUserMenu();
                    }
                });
            }
        }
        
        console.log('[Global Mobile] Mobile navigation initialized successfully');
        
    } catch (error) {
        console.error('[Global Mobile] Critical error during mobile navigation initialization:', error);
        throw error;
    }
}

// Utility functions available globally
window.VybeGlobal = {
    // Show notification
    showNotification: function(message, type = 'info', duration = 3000) {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 1rem 1.5rem;
            border-radius: 8px;
            color: white;
            font-weight: 500;
            z-index: 1000;
            animation: slideInRight 0.3s ease;
        `;
        
        // Set background color based on type
        const colors = {
            info: '#3b82f6',
            success: '#22c55e',
            warning: '#f59e0b',
            error: '#ef4444'
        };
        notification.style.background = colors[type] || colors.info;
        
        document.body.appendChild(notification);
        
        // Auto remove
        setTimeout(() => {
            notification.style.animation = 'slideOutRight 0.3s ease';
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 300);
        }, duration);
    },
    
    // Copy text to clipboard
    copyToClipboard: function(text) {
        if (!text || typeof text !== 'string') {
            window.showToast('error', 'No valid text to copy');
            return Promise.resolve(false);
        }
        
        if (!navigator.clipboard) {
            window.showToast('error', 'Clipboard API not supported in this browser');
            return Promise.resolve(false);
        }
        
        return navigator.clipboard.writeText(text).then(() => {
            this.showNotification('Copied to clipboard!', 'success', 2000);
            return true;
        }).catch(err => {
            console.error('Failed to copy text: ', err);
            window.showToast('error', 'Failed to copy to clipboard. Please try again.');
            return false;
        });
    },
    
    // Format file size
    formatFileSize: function(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    },
    
    // Format date
    formatDate: function(date) {
        return new Date(date).toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    }
};

// Add CSS animations for notifications
const style = document.createElement('style');
style.textContent = `
    @keyframes slideInRight {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOutRight {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

// Global utility functions exposed to window for onclick handlers
window.toggleHelp = function() {
    const helpContent = document.getElementById('help-content');
    if (helpContent) {
        const isVisible = helpContent.style.display !== 'none';
        helpContent.style.display = isVisible ? 'none' : 'block';
        
        // Update toggle button text if it exists
        const helpToggle = document.querySelector('.help-toggle span');
        if (helpToggle) {
            helpToggle.textContent = isVisible ? 'Help' : 'Hide Help';
        }
    }
};

// Global modal close function for onclick handlers
window.closeModal = function(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'none';
    }
};

// Global function for login/register switching
window.showRegister = function() {
    const loginForm = document.getElementById('login-form');
    const registerForm = document.getElementById('register-form');
    if (loginForm && registerForm) {
        loginForm.style.display = 'none';
        registerForm.style.display = 'block';
    }
};

window.showLogin = function() {
    const loginForm = document.getElementById('login-form');
    const registerForm = document.getElementById('register-form');
    if (loginForm && registerForm) {
        loginForm.style.display = 'block';
        registerForm.style.display = 'none';
    }
};

// Settings dropdown function removed - using responsive-nav.js system instead

// Initialize installation monitor when available
if (window.installationMonitor) {
    window.installationMonitor.initialize().catch(error => {
        console.error('Failed to initialize installation monitor:', error);
        if (window.showToast) {
            window.showToast('Failed to initialize installation monitor. Please refresh the page.', 'error');
        }
    });
}