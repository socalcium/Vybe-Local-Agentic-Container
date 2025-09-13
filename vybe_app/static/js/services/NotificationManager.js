/**
 * Centralized Notification Manager for Vybe
 * Provides a consistent interface for displaying notifications across the application
 */

class NotificationManager {
    constructor() {
        this.notifications = new Map();
        this.nextId = 1;
        this.defaultDuration = 5000;
        this.maxNotifications = 5;
        
        // Create container for notifications
        this.createContainer();
        
        // Add CSS styles
        this.injectStyles();
    }
    
    createContainer() {
        // Remove existing container if present
        const existing = document.getElementById('notification-container');
        if (existing) {
            existing.remove();
        }
        
        this.container = document.createElement('div');
        this.container.id = 'notification-container';
        this.container.className = 'notification-container';
        document.body.appendChild(this.container);
    }
    
    injectStyles() {
        const styleId = 'notification-manager-styles';
        
        // Remove existing styles if present
        const existing = document.getElementById(styleId);
        if (existing) {
            existing.remove();
        }
        
        const style = document.createElement('style');
        style.id = styleId;
        style.textContent = `
            .notification-container {
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 10000;
                pointer-events: none;
            }
            
            .notification {
                background: white;
                border-radius: 8px;
                box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
                margin-bottom: 12px;
                padding: 16px;
                min-width: 320px;
                max-width: 400px;
                border-left: 4px solid;
                pointer-events: auto;
                transform: translateX(100%);
                opacity: 0;
                transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
                position: relative;
                overflow: hidden;
            }
            
            .notification.show {
                transform: translateX(0);
                opacity: 1;
            }
            
            .notification.hide {
                transform: translateX(100%);
                opacity: 0;
                margin-bottom: 0;
                padding: 0;
                min-height: 0;
            }
            
            .notification-success {
                border-left-color: #28a745;
                background: linear-gradient(135deg, #d4edda 0%, #ffffff 100%);
                color: #155724;
            }
            
            .notification-error {
                border-left-color: #dc3545;
                background: linear-gradient(135deg, #f8d7da 0%, #ffffff 100%);
                color: #721c24;
            }
            
            .notification-warning {
                border-left-color: #ffc107;
                background: linear-gradient(135deg, #fff3cd 0%, #ffffff 100%);
                color: #856404;
            }
            
            .notification-info {
                border-left-color: #17a2b8;
                background: linear-gradient(135deg, #d1ecf1 0%, #ffffff 100%);
                color: #0c5460;
            }
            
            .notification-header {
                display: flex;
                align-items: center;
                justify-content: space-between;
                margin-bottom: 8px;
            }
            
            .notification-icon {
                display: flex;
                align-items: center;
                font-size: 18px;
                margin-right: 12px;
            }
            
            .notification-title {
                display: flex;
                align-items: center;
                font-weight: 600;
                font-size: 14px;
                flex-grow: 1;
            }
            
            .notification-close {
                background: none;
                border: none;
                color: currentColor;
                cursor: pointer;
                padding: 4px;
                border-radius: 4px;
                opacity: 0.7;
                transition: opacity 0.2s ease;
            }
            
            .notification-close:hover {
                opacity: 1;
                background: rgba(0, 0, 0, 0.1);
            }
            
            .notification-message {
                font-size: 13px;
                line-height: 1.4;
                margin: 0;
            }
            
            .notification-progress {
                position: absolute;
                bottom: 0;
                left: 0;
                height: 3px;
                background: currentColor;
                opacity: 0.3;
                transition: width linear;
            }
            
            @media (max-width: 768px) {
                .notification-container {
                    left: 20px;
                    right: 20px;
                    top: 20px;
                }
                
                .notification {
                    min-width: auto;
                    max-width: none;
                }
            }
        `;
        
        document.head.appendChild(style);
    }
    
    /**
     * Show a toast notification
     * @param {string} message - The message to display
     * @param {string} type - The type of notification (success, error, warning, info)
     * @param {number} duration - How long to show the notification (in ms)
     * @param {Object} options - Additional options
     */
    showToast(message, type = 'info', duration = this.defaultDuration, options = {}) {
        const id = this.nextId++;
        
        // Limit number of notifications
        if (this.notifications.size >= this.maxNotifications) {
            const oldestId = this.notifications.keys().next().value;
            this.hide(oldestId);
        }
        
        const notification = this.createNotificationElement(id, message, type, duration, options);
        this.notifications.set(id, notification);
        
        this.container.appendChild(notification.element);
        
        // Trigger animation
        requestAnimationFrame(() => {
            notification.element.classList.add('show');
        });
        
        // Auto-hide if duration is set
        if (duration > 0) {
            notification.timer = setTimeout(() => {
                this.hide(id);
            }, duration);
            
            // Add progress bar
            this.addProgressBar(notification, duration);
        }
        
        return id;
    }
    
    /**
     * Show a success notification
     * @param {string} message - The message to display
     * @param {number} duration - How long to show the notification (in ms)
     */
    showSuccess(message, duration = this.defaultDuration) {
        return this.showToast(message, 'success', duration);
    }
    
    /**
     * Show an error notification
     * @param {string} message - The message to display
     * @param {number} duration - How long to show the notification (0 = no auto-hide)
     */
    showError(message, duration = 0) {
        return this.showToast(message, 'error', duration);
    }
    
    /**
     * Show a warning notification
     * @param {string} message - The message to display
     * @param {number} duration - How long to show the notification (in ms)
     */
    showWarning(message, duration = this.defaultDuration) {
        return this.showToast(message, 'warning', duration);
    }
    
    /**
     * Show an info notification
     * @param {string} message - The message to display
     * @param {number} duration - How long to show the notification (in ms)
     */
    showInfo(message, duration = this.defaultDuration) {
        return this.showToast(message, 'info', duration);
    }
    
    /**
     * Hide a specific notification
     * @param {number} id - The notification ID
     */
    hide(id) {
        const notification = this.notifications.get(id);
        if (!notification) return;
        
        // Clear timer
        if (notification.timer) {
            clearTimeout(notification.timer);
        }
        
        // Animate out
        notification.element.classList.remove('show');
        notification.element.classList.add('hide');
        
        // Remove from DOM after animation
        setTimeout(() => {
            if (notification.element.parentNode) {
                notification.element.remove();
            }
            this.notifications.delete(id);
        }, 300);
    }
    
    /**
     * Hide all notifications
     */
    hideAll() {
        const ids = Array.from(this.notifications.keys());
        ids.forEach(id => this.hide(id));
    }
    
    createNotificationElement(id, message, type, duration, options) {
        const element = document.createElement('div');
        element.className = `notification notification-${type}`;
        element.dataset.id = id;
        
        const iconMap = {
            success: '✓',
            error: '✗',
            warning: '⚠',
            info: 'ℹ'
        };
        
        const titleMap = {
            success: 'Success',
            error: 'Error',
            warning: 'Warning',
            info: 'Info'
        };
        
        element.innerHTML = `
            <div class="notification-header">
                <div class="notification-title">
                    <span class="notification-icon">${iconMap[type] || iconMap.info}</span>
                    ${options.title || titleMap[type] || titleMap.info}
                </div>
                <button class="notification-close" aria-label="Close notification">×</button>
            </div>
            <div class="notification-message">${this.escapeHtml(message)}</div>
            ${duration > 0 ? '<div class="notification-progress"></div>' : ''}
        `;
        
        // Add close button functionality
        const closeButton = element.querySelector('.notification-close');
        closeButton.addEventListener('click', () => {
            this.hide(id);
        });
        
        return {
            element,
            timer: null,
            type,
            message,
            duration
        };
    }
    
    addProgressBar(notification, duration) {
        const progressBar = notification.element.querySelector('.notification-progress');
        if (!progressBar) return;
        
        progressBar.style.width = '100%';
        
        // Animate progress bar
        requestAnimationFrame(() => {
            progressBar.style.width = '0%';
            progressBar.style.transition = `width ${duration}ms linear`;
        });
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    /**
     * Get the number of active notifications
     */
    getActiveCount() {
        return this.notifications.size;
    }
    
    /**
     * Check if a notification exists
     * @param {number} id - The notification ID
     */
    exists(id) {
        return this.notifications.has(id);
    }
}

// Create and export the singleton instance
const notificationManager = new NotificationManager();

// Attach to window for global access
window.notificationManager = notificationManager;

// Export for module imports
export { notificationManager };
export default NotificationManager;
