/**
 * Professional-grade Notification Manager for Vybe AI Desktop
 * Provides a centralized system for displaying toast notifications with smooth animations
 */

class NotificationManager {
    constructor() {
        this.notifications = [];
        this.maxNotifications = 5;
        this.defaultDuration = 3000;
        this.container = null;
        
        this.init();
        console.log('[NotificationManager] Initialized successfully');
    }

    init() {
        // Create the notification container
        this.container = document.createElement('div');
        this.container.id = 'notification-container';
        this.container.className = 'notification-container';
        
        // Add CSS styles if not already present
        this.addStyles();
        
        // Append to body
        document.body.appendChild(this.container);
    }

    addStyles() {
        // Check if styles are already added
        if (document.getElementById('notification-manager-styles')) {
            return;
        }

        const styles = document.createElement('style');
        styles.id = 'notification-manager-styles';
        styles.textContent = `
            .notification-container {
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 10000;
                max-width: 400px;
                pointer-events: none;
            }

            .toast {
                display: flex;
                align-items: center;
                margin-bottom: 10px;
                padding: 12px 16px;
                background: #333;
                color: #fff;
                border-radius: 8px;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                font-size: 14px;
                line-height: 1.4;
                border-left: 4px solid #007bff;
                pointer-events: auto;
                cursor: pointer;
                animation: toastSlideIn 0.3s ease-out;
                transition: all 0.3s ease;
                position: relative;
                overflow: hidden;
            }

            .toast:hover {
                transform: translateX(-5px);
                box-shadow: 0 6px 20px rgba(0, 0, 0, 0.2);
            }

            .toast-success {
                background: #155724;
                border-left-color: #28a745;
            }

            .toast-error {
                background: #721c24;
                border-left-color: #dc3545;
            }

            .toast-warning {
                background: #856404;
                border-left-color: #ffc107;
            }

            .toast-info {
                background: #0c5460;
                border-left-color: #17a2b8;
            }

            .toast-icon {
                margin-right: 10px;
                font-size: 16px;
                flex-shrink: 0;
            }

            .toast-message {
                flex: 1;
                word-wrap: break-word;
            }

            .toast-close {
                margin-left: 12px;
                background: none;
                border: none;
                color: rgba(255, 255, 255, 0.7);
                font-size: 18px;
                cursor: pointer;
                padding: 0;
                line-height: 1;
                transition: color 0.2s;
            }

            .toast-close:hover {
                color: #fff;
            }

            .toast-progress {
                position: absolute;
                bottom: 0;
                left: 0;
                height: 3px;
                background: rgba(255, 255, 255, 0.3);
                transition: width linear;
            }

            @keyframes toastSlideIn {
                from {
                    transform: translateX(100%);
                    opacity: 0;
                }
                to {
                    transform: translateX(0);
                    opacity: 1;
                }
            }

            @keyframes toastSlideOut {
                from {
                    transform: translateX(0);
                    opacity: 1;
                    max-height: 100px;
                }
                to {
                    transform: translateX(100%);
                    opacity: 0;
                    max-height: 0;
                    margin-bottom: 0;
                    padding-top: 0;
                    padding-bottom: 0;
                }
            }

            .toast.removing {
                animation: toastSlideOut 0.3s ease-in forwards;
            }

            /* Dark theme support */
            @media (prefers-color-scheme: dark) {
                .toast {
                    background: #2d3748;
                    color: #e2e8f0;
                }
                
                .toast-success {
                    background: #276749;
                }
                
                .toast-error {
                    background: #742a2a;
                }
                
                .toast-warning {
                    background: #975a16;
                }
                
                .toast-info {
                    background: #2a69ac;
                }
            }

            /* Mobile responsive */
            @media (max-width: 768px) {
                .notification-container {
                    top: 10px;
                    right: 10px;
                    left: 10px;
                    max-width: none;
                }
                
                .toast {
                    margin-bottom: 8px;
                }
            }
        `;
        
        document.head.appendChild(styles);
    }

    /**
     * Main method to show a notification
     * @param {string} message - The notification message
     * @param {string} type - Type of notification (info, success, error, warning)
     * @param {number} duration - Duration in milliseconds (0 for persistent)
     * @param {Object} options - Additional options
     */
    show(message, type = 'info', duration = null, options = {}) {
        if (!message || typeof message !== 'string') {
            console.warn('[NotificationManager] Invalid message provided:', message);
            return null;
        }

        // Use default duration if not specified
        if (duration === null) {
            duration = this.defaultDuration;
        }

        // Limit number of notifications
        if (this.notifications.length >= this.maxNotifications) {
            this.removeOldest();
        }

        // Create notification element
        const notification = this.createNotificationElement(message, type, options);
        
        // Add to container
        this.container.appendChild(notification);
        this.notifications.push({
            element: notification,
            timestamp: Date.now(),
            type: type
        });

        // Auto-remove after duration (if not persistent)
        if (duration > 0) {
            setTimeout(() => {
                this.remove(notification);
            }, duration);
        }

        // Add progress bar animation
        if (duration > 0) {
            const progressBar = notification.querySelector('.toast-progress');
            if (progressBar) {
                // Animate progress bar
                progressBar.style.width = '100%';
                progressBar.style.transitionDuration = `${duration}ms`;
                setTimeout(() => {
                    if (progressBar.parentElement) {
                        progressBar.style.width = '0%';
                    }
                }, 50);
            }
        }

        return notification;
    }

    createNotificationElement(message, type, options = {}) {
        const notification = document.createElement('div');
        notification.className = `toast toast-${type}`;

        // Add icon based on type
        const icon = this.getIcon(type);
        
        // Use options for future extensibility
        const { closable = true } = options;
        
        // Add progress bar for timed notifications
        const progressBar = document.createElement('div');
        progressBar.className = 'toast-progress';

        notification.innerHTML = `
            <span class="toast-icon">${icon}</span>
            <span class="toast-message">${this.escapeHtml(message)}</span>
            ${closable ? '<button class="toast-close" aria-label="Close notification">&times;</button>' : ''}
        `;

        notification.appendChild(progressBar);

        // Add click to dismiss
        const closeButton = notification.querySelector('.toast-close');
        if (closeButton) {
            closeButton.addEventListener('click', (e) => {
                e.stopPropagation();
                this.remove(notification);
            });
        }

        // Click notification to dismiss
        notification.addEventListener('click', () => {
            this.remove(notification);
        });

        return notification;
    }

    getIcon(type) {
        const icons = {
            success: '✓',
            error: '✗',
            warning: '⚠',
            info: 'ℹ'
        };
        return icons[type] || icons.info;
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    remove(notification) {
        if (!notification || !notification.parentElement) {
            return;
        }

        // Add removing class for animation
        notification.classList.add('removing');

        // Remove from array
        this.notifications = this.notifications.filter(n => n.element !== notification);

        // Remove from DOM after animation
        setTimeout(() => {
            if (notification.parentElement) {
                notification.parentElement.removeChild(notification);
            }
        }, 300);
    }

    removeOldest() {
        if (this.notifications.length > 0) {
            const oldest = this.notifications[0];
            this.remove(oldest.element);
        }
    }

    /**
     * Convenience method for success notifications
     */
    success(message, duration = null) {
        return this.show(message, 'success', duration);
    }

    /**
     * Convenience method for error notifications
     */
    error(message, duration = null) {
        return this.show(message, 'error', duration);
    }

    /**
     * Convenience method for warning notifications
     */
    warning(message, duration = null) {
        return this.show(message, 'warning', duration);
    }

    /**
     * Convenience method for info notifications
     */
    info(message, duration = null) {
        return this.show(message, 'info', duration);
    }

    /**
     * Clear all notifications
     */
    clear() {
        this.notifications.forEach(notification => {
            this.remove(notification.element);
        });
    }

    /**
     * Get current notification count
     */
    getCount() {
        return this.notifications.length;
    }

    /**
     * Destroy the notification manager
     */
    destroy() {
        this.clear();
        if (this.container && this.container.parentElement) {
            this.container.parentElement.removeChild(this.container);
        }
        this.notifications = [];
        this.container = null;
        
        // Remove styles
        const styles = document.getElementById('notification-manager-styles');
        if (styles && styles.parentElement) {
            styles.parentElement.removeChild(styles);
        }
        
        console.log('[NotificationManager] Destroyed');
    }
}

// Export for module systems
/* global module */
if (typeof module !== 'undefined' && typeof module.exports !== 'undefined') {
    module.exports = NotificationManager;
}

// Create global instance when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    if (!window.notificationManager) {
        window.notificationManager = new NotificationManager();
        console.log('[NotificationManager] Global instance created successfully');
        
        // Also create a legacy showToast function for backward compatibility
        window.showToast = function(message, type = 'info', duration = 3000) {
            console.warn('[DEPRECATED] showToast is deprecated. Use window.notificationManager instead.');
            return window.notificationManager.show(message, type, duration);
        };
    }
});

// Immediate initialization if DOM is already ready
if (document.readyState === 'loading') {
    // DOM is still loading, event listener will handle it
} else {
    // DOM is already ready
    if (!window.notificationManager) {
        window.notificationManager = new NotificationManager();
        console.log('[NotificationManager] Global instance created successfully (immediate)');
        
        // Also create a legacy showToast function for backward compatibility
        window.showToast = function(message, type = 'info', duration = 3000) {
            console.warn('[DEPRECATED] showToast is deprecated. Use window.notificationManager instead.');
            return window.notificationManager.show(message, type, duration);
        };
    }
}
