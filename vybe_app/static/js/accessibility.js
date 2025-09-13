/**
 * Accessibility utilities for Vybe application
 * Provides enhanced keyboard navigation, screen reader support, and ARIA management
 */

class AccessibilityManager {
    constructor() {
        this.focusableElements = [
            'a[href]',
            'button:not([disabled])',
            'input:not([disabled])',
            'textarea:not([disabled])',
            'select:not([disabled])',
            '[tabindex]:not([tabindex="-1"])',
            '[contenteditable="true"]'
        ].join(', ');
        
        this.announcer = null;
        
        // Create dedicated event manager for accessibility
        this.eventManager = new window.EventManager('AccessibilityManager');
        
        this.init();
    }
    
    /**
     * Destroy the accessibility manager and clean up event listeners
     */
    destroy() {
        this.eventManager.destroy();
        
        // Remove announcer element
        if (this.announcer && this.announcer.parentNode) {
            this.announcer.parentNode.removeChild(this.announcer);
        }
    }

    init() {
        this.createAnnouncer();
        this.setupKeyboardNavigation();
        this.setupFocusManagement();
        this.setupScreenReaderSupport();
        console.log('Accessibility manager initialized');
    }

    /**
     * Create a live region for screen reader announcements
     */
    createAnnouncer() {
        this.announcer = document.createElement('div');
        this.announcer.setAttribute('aria-live', 'polite');
        this.announcer.setAttribute('aria-atomic', 'true');
        this.announcer.setAttribute('class', 'sr-only');
        this.announcer.setAttribute('id', 'accessibility-announcer');
        document.body.appendChild(this.announcer);
    }

    /**
     * Announce a message to screen readers
     */
    announce(message, priority = 'polite') {
        if (!this.announcer) return;
        
        // Clear previous message
        this.announcer.textContent = '';
        
        // Set priority
        this.announcer.setAttribute('aria-live', priority);
        
        // Slight delay to ensure screen readers pick up the change
        setTimeout(() => {
            this.announcer.textContent = message;
        }, 100);
        
        // Clear after announcement
        setTimeout(() => {
            this.announcer.textContent = '';
        }, 1000);
    }

    /**
     * Setup enhanced keyboard navigation
     */
    setupKeyboardNavigation() {
        this.eventManager.add(document, 'keydown', (event) => {
            // Escape key handling for modals and dialogs
            if (event.key === 'Escape') {
                this.handleEscape();
            }
            
            // Tab trapping for modals
            if (event.key === 'Tab') {
                const modal = document.querySelector('[role="dialog"][aria-hidden="false"], .modal.show');
                if (modal) {
                    this.trapFocus(event, modal);
                }
            }
            
            // Arrow key navigation for lists and menus
            if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(event.key)) {
                this.handleArrowNavigation(event);
            }
        });
    }

    /**
     * Handle Escape key to close modals and panels
     */
    handleEscape() {
        // Close settings panel
        const settingsPanel = document.getElementById('chat-settings-panel');
        if (settingsPanel && !settingsPanel.hasAttribute('aria-hidden')) {
            this.closePanel(settingsPanel);
            return;
        }
        
        // Close other modals or panels
        const modal = document.querySelector('[role="dialog"][aria-hidden="false"]');
        if (modal) {
            this.closeModal(modal);
        }
    }

    /**
     * Close a modal or panel
     */
    closePanel(panel) {
        panel.setAttribute('aria-hidden', 'true');
        const trigger = document.querySelector(`[aria-controls="${panel.id}"]`);
        if (trigger) {
            trigger.focus();
        }
        this.announce('Panel closed');
    }

    /**
     * Close a modal
     */
    closeModal(modal) {
        modal.setAttribute('aria-hidden', 'true');
        // Return focus to trigger element if available
        const trigger = modal.dataset.trigger;
        if (trigger) {
            const element = document.getElementById(trigger);
            if (element) element.focus();
        }
        this.announce('Modal closed');
    }

    /**
     * Trap focus within a modal
     */
    trapFocus(event, container) {
        const focusableElements = container.querySelectorAll(this.focusableElements);
        const firstElement = focusableElements[0];
        const lastElement = focusableElements[focusableElements.length - 1];

        if (event.shiftKey && document.activeElement === firstElement) {
            event.preventDefault();
            lastElement.focus();
        } else if (!event.shiftKey && document.activeElement === lastElement) {
            event.preventDefault();
            firstElement.focus();
        }
    }

    /**
     * Handle arrow key navigation
     */
    handleArrowNavigation(event) {
        const target = event.target;
        
        // Check if we're in a list or menu
        const list = target.closest('[role="list"], [role="menu"], [role="listbox"]');
        if (!list) return;
        
        const items = list.querySelectorAll('[role="listitem"], [role="menuitem"], [role="option"], button, a');
        const currentIndex = Array.from(items).indexOf(target);
        
        if (currentIndex === -1) return;
        
        let nextIndex = currentIndex;
        
        switch (event.key) {
            case 'ArrowDown':
                nextIndex = Math.min(currentIndex + 1, items.length - 1);
                break;
            case 'ArrowUp':
                nextIndex = Math.max(currentIndex - 1, 0);
                break;
            case 'Home':
                nextIndex = 0;
                break;
            case 'End':
                nextIndex = items.length - 1;
                break;
            default:
                return;
        }
        
        if (nextIndex !== currentIndex) {
            event.preventDefault();
            items[nextIndex].focus();
        }
    }

    /**
     * Setup focus management
     */
    setupFocusManagement() {
        // Add focus indicators for custom elements
        this.eventManager.add(document, 'focusin', (event) => {
            const target = event.target;
            if (target.classList.contains('custom-focus')) {
                target.setAttribute('data-focused', 'true');
            }
        });

        this.eventManager.add(document, 'focusout', (event) => {
            const target = event.target;
            if (target.classList.contains('custom-focus')) {
                target.removeAttribute('data-focused');
            }
        });
    }

    /**
     * Setup screen reader support
     */
    setupScreenReaderSupport() {
        // Announce page changes
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.type === 'childList') {
                    mutation.addedNodes.forEach((node) => {
                        if (node.nodeType === Node.ELEMENT_NODE) {
                            // Announce new chat messages
                            if (node.classList && node.classList.contains('chat-message')) {
                                const messageType = node.classList.contains('ai') ? 'AI' : 'User';
                                const content = node.querySelector('.chat-bubble')?.textContent;
                                if (content) {
                                    this.announce(`New ${messageType} message: ${content.substring(0, 100)}`, 'assertive');
                                }
                            }
                            
                            // Announce status updates
                            if (node.classList && (node.classList.contains('notification') || node.classList.contains('alert'))) {
                                const content = node.textContent;
                                if (content) {
                                    this.announce(content, 'assertive');
                                }
                            }
                        }
                    });
                }
            });
        });

        // Observe chat messages container
        const chatMessages = document.getElementById('chat-messages');
        if (chatMessages) {
            observer.observe(chatMessages, { childList: true, subtree: true });
        }

        // Observe notifications container
        const notifications = document.getElementById('notifications-container');
        if (notifications) {
            observer.observe(notifications, { childList: true, subtree: true });
        }
    }

    /**
     * Update ARIA attributes dynamically
     */
    updateAriaAttribute(element, attribute, value) {
        if (element) {
            element.setAttribute(attribute, value);
        }
    }

    /**
     * Set focus to an element with announcement
     */
    setFocus(element, announcement = null) {
        if (element) {
            element.focus();
            if (announcement) {
                this.announce(announcement);
            }
        }
    }

    /**
     * Get the first focusable element in a container
     */
    getFirstFocusable(container) {
        return container.querySelector(this.focusableElements);
    }

    /**
     * Get all focusable elements in a container
     */
    getAllFocusable(container) {
        return container.querySelectorAll(this.focusableElements);
    }
}

// Initialize accessibility manager when DOM is ready
if (document.readyState === 'loading') {
    if (window.eventManager) {
        window.eventManager.add(document, 'DOMContentLoaded', () => {
            window.accessibilityManager = new AccessibilityManager();
        });
    } else {
        document.addEventListener('DOMContentLoaded', () => {
            window.accessibilityManager = new AccessibilityManager();
        });
    }
} else {
    window.accessibilityManager = new AccessibilityManager();
}

// Make available globally
window.AccessibilityManager = AccessibilityManager;
