/**
 * Advanced Notification Manager
 * Professional notification system with queuing, persistence, and smart management
 */

export class NotificationManager {
    constructor() {
        this.notifications = new Map();
        this.queue = [];
        this.settings = {
            maxVisible: 4,
            defaultDuration: 5000,
            animationDuration: 300,
            position: 'top-right', // top-right, top-left, bottom-right, bottom-left
            enableSound: false,
            enablePersistence: true
        };

        // Cleanup functions for event listeners
        this.cleanupFunctions = [];
        
        this.container = null;
        this.soundEnabled = false;
        this.nextId = 1;
        
        this.init();
    }

    // Destroy method to prevent memory leaks
    destroy() {
        // Remove all event listeners
        this.cleanupFunctions.forEach(cleanup => {
            try {
                cleanup();
            } catch (error) {
                console.error('Error during cleanup:', error);
            }
        });
        this.cleanupFunctions = [];
    }
    
    init() {
        this.createContainer();
        this.loadSettings();
        this.bindEvents();
        this.loadPersistedNotifications();
    }
    
    createContainer() {
        this.container = document.createElement('div');
        this.container.className = `notification-container notification-${this.settings.position}`;
        this.container.setAttribute('aria-live', 'polite');
        this.container.setAttribute('aria-label', 'Notifications');
        document.body.appendChild(this.container);
    }
    
    loadSettings() {
        const saved = localStorage.getItem('vybe_notification_settings');
        if (saved) {
            try {
                const settings = JSON.parse(saved);
                this.settings = { ...this.settings, ...settings };
            } catch (error) {
                console.warn('Failed to load notification settings:', error);
            }
        }
    }
    
    saveSettings() {
        localStorage.setItem('vybe_notification_settings', JSON.stringify(this.settings));
    }
    
    bindEvents() {
        // Initialize event manager if not available
        if (!window.eventManager) {
            console.warn('EventManager not available, using direct event listeners');
            this.setupDirectEventListeners();
            return;
        }

        // Listen for page visibility changes
        const visibilityCleanup = window.eventManager.add(document, 'visibilitychange', () => {
            if (!document.hidden) {
                this.processQueue();
            }
        });
        this.cleanupFunctions.push(visibilityCleanup);
        
        // Listen for keyboard shortcuts (Escape to dismiss all)
        const keydownCleanup = window.eventManager.add(document, 'keydown', (e) => {
            if (e.key === 'Escape' && this.getVisibleCount() > 0) {
                e.preventDefault();
                this.dismissAll();
            }
        });
        this.cleanupFunctions.push(keydownCleanup);

        // Listen for window focus changes
        const focusCleanup = window.eventManager.add(window, 'focus', () => {
            this.processQueue();
        });
        this.cleanupFunctions.push(focusCleanup);
        
        // Handle system notifications permission
        if ('Notification' in window && Notification.permission === 'default') {
            this.requestNotificationPermission();
        }

        // Listen for online/offline status
        const onlineCleanup = window.eventManager.add(window, 'online', () => {
            this.info('Connection restored', { duration: 3000 });
        });
        this.cleanupFunctions.push(onlineCleanup);

        const offlineCleanup = window.eventManager.add(window, 'offline', () => {
            this.warning('Connection lost', { persistent: true });
        });
        this.cleanupFunctions.push(offlineCleanup);
    }

    setupDirectEventListeners() {
        // Fallback for when event manager is not available
        const visibilityHandler = () => {
            if (!document.hidden) {
                this.processQueue();
            }
        };
        document.addEventListener('visibilitychange', visibilityHandler);
        this.cleanupFunctions.push(() => {
            document.removeEventListener('visibilitychange', visibilityHandler);
        });

        const keydownHandler = (e) => {
            if (e.key === 'Escape' && this.getVisibleCount() > 0) {
                e.preventDefault();
                this.dismissAll();
            }
        };
        document.addEventListener('keydown', keydownHandler);
        this.cleanupFunctions.push(() => {
            document.removeEventListener('keydown', keydownHandler);
        });
    }
    
    async requestNotificationPermission() {
        try {
            const permission = await Notification.requestPermission();
            if (permission === 'granted') {
                console.log('System notifications enabled');
            }
        } catch (error) {
            console.warn('System notifications not supported:', error);
        }
    }
    
    show(message, type = 'info', options = {}) {
        try {
            // Validate inputs
            if (!message || typeof message !== 'string') {
                console.error('Notification message must be a non-empty string');
                return null;
            }

            const notification = this.createNotification(message, type, options);
            
            if (this.getVisibleCount() >= this.settings.maxVisible) {
                this.queue.push(notification);
                this.emitEvent('notificationQueued', { 
                    id: notification.id, 
                    queueLength: this.queue.length,
                    timestamp: Date.now() 
                });
                return notification.id;
            }
            
            this.displayNotification(notification);
            this.emitEvent('notificationShown', { 
                id: notification.id, 
                type: notification.type,
                timestamp: Date.now() 
            });
            
            return notification.id;
        } catch (error) {
            console.error('Error showing notification:', error);
            return null;
        }
    }
    
    createNotification(message, type, options) {
        const id = `notification_${this.nextId++}`;
        
        const notification = {
            id,
            message,
            type,
            timestamp: Date.now(),
            duration: options.duration || this.settings.defaultDuration,
            persistent: options.persistent || false,
            actions: options.actions || [],
            icon: options.icon || this.getDefaultIcon(type),
            title: options.title || '',
            progress: options.progress || null,
            dismissible: options.dismissible !== false,
            sound: options.sound || false,
            systemNotification: options.systemNotification || false
        };
        
        this.notifications.set(id, notification);
        
        if (this.settings.enablePersistence && notification.persistent) {
            this.persistNotification(notification);
        }
        
        return notification;
    }
    
    displayNotification(notification) {
        const element = this.createNotificationElement(notification);
        this.container.appendChild(element);
        
        // Trigger animation
        requestAnimationFrame(() => {
            element.classList.add('show');
        });
        
        // Play sound if enabled
        if (notification.sound && this.soundEnabled) {
            this.playNotificationSound(notification.type);
        }
        
        // Show system notification if requested
        if (notification.systemNotification && this.canShowSystemNotifications()) {
            this.showSystemNotification(notification);
        }
        
        // Auto-dismiss if not persistent
        if (!notification.persistent && notification.duration > 0) {
            setTimeout(() => {
                this.dismiss(notification.id);
            }, notification.duration);
        }
    }
    
    createNotificationElement(notification) {
        const element = document.createElement('div');
        element.className = `notification notification-${notification.type}`;
        element.setAttribute('data-id', notification.id);
        element.setAttribute('role', 'alert');
        element.setAttribute('aria-describedby', `notification-message-${notification.id}`);
        
        let progressHTML = '';
        if (notification.progress !== null) {
            progressHTML = `
                <div class="notification-progress">
                    <div class="notification-progress-bar" style="width: ${notification.progress}%"></div>
                </div>
            `;
        }
        
        let actionsHTML = '';
        if (notification.actions.length > 0) {
            actionsHTML = `
                <div class="notification-actions">
                    ${notification.actions.map(action => `
                        <button class="notification-action" data-action="${action.id}">
                            ${action.label}
                        </button>
                    `).join('')}
                </div>
            `;
        }
        
        element.innerHTML = `
            <div class="notification-content">
                ${notification.icon ? `<div class="notification-icon">${notification.icon}</div>` : ''}
                <div class="notification-body">
                    ${notification.title ? `<div class="notification-title">${notification.title}</div>` : ''}
                    <div class="notification-message" id="notification-message-${notification.id}">
                        ${notification.message}
                    </div>
                    <div class="notification-timestamp">
                        ${this.formatTimestamp(notification.timestamp)}
                    </div>
                </div>
                ${notification.dismissible ? `
                    <button class="notification-close" aria-label="Close notification">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
                        </svg>
                    </button>
                ` : ''}
            </div>
            ${progressHTML}
            ${actionsHTML}
        `;
        
        // Bind events
        this.bindNotificationEvents(element, notification);
        
        return element;
    }
    
    bindNotificationEvents(element, notification) {
        // Close button
        const closeBtn = element.querySelector('.notification-close');
        if (closeBtn) {
            if (window.eventManager) {
                const cleanup = window.eventManager.add(closeBtn, 'click', () => {
                    this.dismiss(notification.id);
                });
                // Store cleanup function on the element for later removal
                element._cleanupFunctions = element._cleanupFunctions || [];
                element._cleanupFunctions.push(cleanup);
            } else {
                const handler = () => this.dismiss(notification.id);
                closeBtn.addEventListener('click', handler);
                element._cleanupFunctions = element._cleanupFunctions || [];
                element._cleanupFunctions.push(() => closeBtn.removeEventListener('click', handler));
            }
        }
        
        // Action buttons
        const actionBtns = element.querySelectorAll('.notification-action');
        actionBtns.forEach(btn => {
            const actionHandler = (e) => {
                const actionId = e.target.getAttribute('data-action');
                const action = notification.actions.find(a => a.id === actionId);
                if (action && action.handler) {
                    try {
                        action.handler(notification);
                    } catch (error) {
                        console.error('Error executing notification action:', error);
                        this.error('Action failed to execute');
                    }
                }
                
                if (action && action.dismissOnClick !== false) {
                    this.dismiss(notification.id);
                }
            };

            if (window.eventManager) {
                const cleanup = window.eventManager.add(btn, 'click', actionHandler);
                element._cleanupFunctions = element._cleanupFunctions || [];
                element._cleanupFunctions.push(cleanup);
            } else {
                btn.addEventListener('click', actionHandler);
                element._cleanupFunctions = element._cleanupFunctions || [];
                element._cleanupFunctions.push(() => btn.removeEventListener('click', actionHandler));
            }
        });
        
        // Click to dismiss (if enabled)
        if (notification.dismissible) {
            const clickHandler = (e) => {
                if (!e.target.closest('.notification-action') && !e.target.closest('.notification-close')) {
                    this.dismiss(notification.id);
                }
            };

            if (window.eventManager) {
                const cleanup = window.eventManager.add(element, 'click', clickHandler);
                element._cleanupFunctions = element._cleanupFunctions || [];
                element._cleanupFunctions.push(cleanup);
            } else {
                element.addEventListener('click', clickHandler);
                element._cleanupFunctions = element._cleanupFunctions || [];
                element._cleanupFunctions.push(() => element.removeEventListener('click', clickHandler));
            }
        }

        // Add hover pause for auto-dismiss
        if (!notification.persistent && notification.duration > 0) {
            let resumeTimeout;
            let remainingTime = notification.duration;
            let startTime = Date.now();

            const pauseHandler = () => {
                if (resumeTimeout) {
                    clearTimeout(resumeTimeout);
                    resumeTimeout = null;
                }
                const elapsed = Date.now() - startTime;
                remainingTime = Math.max(0, remainingTime - elapsed);
            };

            const resumeHandler = () => {
                if (remainingTime > 0) {
                    startTime = Date.now();
                    resumeTimeout = setTimeout(() => {
                        this.dismiss(notification.id);
                    }, remainingTime);
                }
            };

            if (window.eventManager) {
                const mouseenterCleanup = window.eventManager.add(element, 'mouseenter', pauseHandler);
                const mouseleaveCleanup = window.eventManager.add(element, 'mouseleave', resumeHandler);
                element._cleanupFunctions = element._cleanupFunctions || [];
                element._cleanupFunctions.push(mouseenterCleanup, mouseleaveCleanup);
            } else {
                element.addEventListener('mouseenter', pauseHandler);
                element.addEventListener('mouseleave', resumeHandler);
                element._cleanupFunctions = element._cleanupFunctions || [];
                element._cleanupFunctions.push(
                    () => element.removeEventListener('mouseenter', pauseHandler),
                    () => element.removeEventListener('mouseleave', resumeHandler)
                );
            }
        }
    }
    
    dismiss(id) {
        const element = this.container.querySelector(`[data-id="${id}"]`);
        if (!element) return;
        
        // Clean up event listeners
        if (element._cleanupFunctions) {
            element._cleanupFunctions.forEach(cleanup => {
                try {
                    cleanup();
                } catch (error) {
                    console.error('Error cleaning up notification events:', error);
                }
            });
            element._cleanupFunctions = [];
        }
        
        element.classList.add('dismissing');
        
        setTimeout(() => {
            if (element.parentNode) {
                element.parentNode.removeChild(element);
            }
            this.notifications.delete(id);
            
            // Remove from localStorage if it was persisted
            const key = `vybe_notification_${id}`;
            if (localStorage.getItem(key)) {
                localStorage.removeItem(key);
            }
            
            this.processQueue();
        }, this.settings.animationDuration);
        
        // Emit custom event for dismiss
        this.emitEvent('notificationDismissed', { id, timestamp: Date.now() });
    }
    
    dismissAll() {
        const elements = this.container.querySelectorAll('.notification');
        const dismissPromises = [];
        
        elements.forEach(element => {
            const id = element.getAttribute('data-id');
            dismissPromises.push(new Promise(resolve => {
                // Clean up event listeners
                if (element._cleanupFunctions) {
                    element._cleanupFunctions.forEach(cleanup => {
                        try {
                            cleanup();
                        } catch (error) {
                            console.error('Error cleaning up notification events:', error);
                        }
                    });
                    element._cleanupFunctions = [];
                }
                
                element.classList.add('dismissing');
                
                setTimeout(() => {
                    if (element.parentNode) {
                        element.parentNode.removeChild(element);
                    }
                    this.notifications.delete(id);
                    
                    // Remove from localStorage if it was persisted
                    const key = `vybe_notification_${id}`;
                    if (localStorage.getItem(key)) {
                        localStorage.removeItem(key);
                    }
                    
                    resolve();
                }, this.settings.animationDuration);
            }));
        });
        
        Promise.all(dismissPromises).then(() => {
            this.processQueue();
            this.emitEvent('allNotificationsDismissed', { count: elements.length, timestamp: Date.now() });
        });
    }

    emitEvent(eventName, data) {
        try {
            const event = new CustomEvent(`vybeNotification:${eventName}`, {
                detail: data,
                bubbles: true,
                cancelable: true
            });
            document.dispatchEvent(event);
        } catch (error) {
            console.error('Error emitting notification event:', error);
        }
    }
    
    updateProgress(id, progress) {
        const element = this.container.querySelector(`[data-id="${id}"]`);
        if (!element) return false;
        
        const progressBar = element.querySelector('.notification-progress-bar');
        if (progressBar) {
            const clampedProgress = Math.max(0, Math.min(100, progress));
            progressBar.style.width = `${clampedProgress}%`;
            
            // Add progress text if not present
            let progressText = element.querySelector('.notification-progress-text');
            if (!progressText) {
                progressText = document.createElement('div');
                progressText.className = 'notification-progress-text';
                const progressContainer = element.querySelector('.notification-progress');
                if (progressContainer) {
                    progressContainer.appendChild(progressText);
                }
            }
            if (progressText) {
                progressText.textContent = `${Math.round(clampedProgress)}%`;
            }
        }
        
        const notification = this.notifications.get(id);
        if (notification) {
            notification.progress = progress;
            
            // Auto-dismiss when progress reaches 100%
            if (progress >= 100 && notification.type === 'loading') {
                setTimeout(() => {
                    this.success('Operation completed successfully', { duration: 2000 });
                    this.dismiss(id);
                }, 500);
            }
        }
        
        this.emitEvent('progressUpdated', { id, progress, timestamp: Date.now() });
        return true;
    }
    
    processQueue() {
        while (this.queue.length > 0 && this.getVisibleCount() < this.settings.maxVisible) {
            const notification = this.queue.shift();
            this.displayNotification(notification);
        }
    }
    
    getVisibleCount() {
        return this.container.querySelectorAll('.notification:not(.dismissing)').length;
    }
    
    getDefaultIcon(type) {
        const icons = {
            success: '✅',
            error: '❌',
            warning: '⚠️',
            info: 'ℹ️',
            loading: '⏳'
        };
        return icons[type] || icons.info;
    }
    
    formatTimestamp(timestamp) {
        const now = Date.now();
        const diff = now - timestamp;
        
        if (diff < 60000) { // Less than 1 minute
            return 'just now';
        } else if (diff < 3600000) { // Less than 1 hour
            const minutes = Math.floor(diff / 60000);
            return `${minutes}m ago`;
        } else {
            const hours = Math.floor(diff / 3600000);
            return `${hours}h ago`;
        }
    }
    
    playNotificationSound(type) {
        // Create audio context if needed
        if (!this.audioContext) {
            try {
                this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
            } catch (error) {
                console.warn('Audio context not supported:', error);
                return; // Audio not supported
            }
        }
        
        // Play different tones for different notification types
        const frequencies = {
            success: 523.25, // C5
            error: 261.63,   // C4
            warning: 392.00, // G4
            info: 440.00     // A4
        };
        
        const frequency = frequencies[type] || frequencies.info;
        this.playTone(frequency, 0.1, 200);
    }
    
    playTone(frequency, volume, duration) {
        if (!this.audioContext) return;
        
        const oscillator = this.audioContext.createOscillator();
        const gainNode = this.audioContext.createGain();
        
        oscillator.connect(gainNode);
        gainNode.connect(this.audioContext.destination);
        
        oscillator.frequency.value = frequency;
        oscillator.type = 'sine';
        
        gainNode.gain.setValueAtTime(0, this.audioContext.currentTime);
        gainNode.gain.linearRampToValueAtTime(volume, this.audioContext.currentTime + 0.01);
        gainNode.gain.linearRampToValueAtTime(0, this.audioContext.currentTime + duration / 1000);
        
        oscillator.start(this.audioContext.currentTime);
        oscillator.stop(this.audioContext.currentTime + duration / 1000);
    }
    
    canShowSystemNotifications() {
        return 'Notification' in window && Notification.permission === 'granted';
    }
    
    showSystemNotification(notification) {
        if (!this.canShowSystemNotifications()) return;
        
        try {
            const systemNotif = new Notification(notification.title || 'Vybe AI', {
                body: notification.message,
                icon: '/static/assets/icons/icon-192.png',
                badge: '/static/assets/icons/icon-192.png',
                tag: notification.id
            });
            
            systemNotif.onclick = () => {
                window.focus();
                systemNotif.close();
            };
            
            setTimeout(() => systemNotif.close(), notification.duration);
        } catch (error) {
            console.warn('Failed to show system notification:', error);
        }
    }
    
    persistNotification(notification) {
        const key = `vybe_notification_${notification.id}`;
        const data = {
            ...notification,
            persisted: true
        };
        localStorage.setItem(key, JSON.stringify(data));
    }
    
    loadPersistedNotifications() {
        const keys = Object.keys(localStorage).filter(key => key.startsWith('vybe_notification_'));
        
        keys.forEach(key => {
            try {
                const data = JSON.parse(localStorage.getItem(key));
                if (data.persisted && Date.now() - data.timestamp < 86400000) { // 24 hours
                    this.notifications.set(data.id, data);
                    if (this.getVisibleCount() < this.settings.maxVisible) {
                        this.displayNotification(data);
                    }
                } else {
                    localStorage.removeItem(key);
                }
            } catch (error) {
                console.warn('Failed to parse persisted notification:', error);
                localStorage.removeItem(key);
            }
        });
    }
    
    // Convenience methods
    success(message, options = {}) {
        return this.show(message, 'success', {
            icon: '✅',
            duration: options.duration || 4000,
            sound: this.settings.enableSound,
            ...options
        });
    }
    
    error(message, options = {}) {
        return this.show(message, 'error', { 
            icon: '❌',
            persistent: true, 
            sound: this.settings.enableSound,
            ...options 
        });
    }
    
    warning(message, options = {}) {
        return this.show(message, 'warning', {
            icon: '⚠️',
            duration: options.duration || 6000,
            sound: this.settings.enableSound,
            ...options
        });
    }
    
    info(message, options = {}) {
        return this.show(message, 'info', {
            icon: 'ℹ️',
            duration: options.duration || 5000,
            ...options
        });
    }
    
    loading(message, options = {}) {
        return this.show(message, 'loading', { 
            icon: '⏳',
            progress: 0, 
            persistent: true,
            dismissible: false,
            ...options 
        });
    }

    // New convenience methods
    confirm(message, options = {}) {
        const defaultActions = [
            {
                id: 'confirm',
                label: 'OK',
                handler: options.onConfirm || (() => {}),
                dismissOnClick: true
            },
            {
                id: 'cancel',
                label: 'Cancel',
                handler: options.onCancel || (() => {}),
                dismissOnClick: true
            }
        ];

        return this.show(message, 'info', {
            icon: '❓',
            persistent: true,
            actions: options.actions || defaultActions,
            dismissible: false,
            ...options
        });
    }

    toast(message, duration = 2000) {
        return this.show(message, 'info', {
            duration,
            dismissible: false,
            position: 'bottom-center'
        });
    }

    progress(message, initialProgress = 0, options = {}) {
        return this.show(message, 'loading', {
            progress: initialProgress,
            persistent: true,
            dismissible: false,
            icon: '📊',
            ...options
        });
    }
    
    // Settings management
    updateSettings(newSettings) {
        this.settings = { ...this.settings, ...newSettings };
        this.saveSettings();
        this.updateContainer();
        this.emitEvent('settingsUpdated', { settings: this.settings });
    }
    
    updateContainer() {
        if (this.container) {
            this.container.className = `notification-container notification-${this.settings.position}`;
        }
    }

    // Batch operations
    showBatch(notifications) {
        const ids = [];
        notifications.forEach(notif => {
            const id = this.show(notif.message, notif.type || 'info', notif.options || {});
            if (id) ids.push(id);
        });
        return ids;
    }

    // Clear all notifications and queue
    clear() {
        this.dismissAll();
        this.queue = [];
        this.emitEvent('notificationsCleared', { timestamp: Date.now() });
    }

    // Get notification by ID
    getNotification(id) {
        return this.notifications.get(id);
    }

    // Get all active notifications
    getAllNotifications() {
        return Array.from(this.notifications.values());
    }

    // Get queue length
    getQueueLength() {
        return this.queue.length;
    }

    // Check if notification exists
    exists(id) {
        return this.notifications.has(id);
    }

    // Update notification content
    updateNotification(id, updates) {
        const notification = this.notifications.get(id);
        const element = this.container.querySelector(`[data-id="${id}"]`);
        
        if (!notification || !element) return false;
        
        // Update notification object
        Object.assign(notification, updates);
        
        // Update DOM elements
        if (updates.message) {
            const messageEl = element.querySelector('.notification-message');
            if (messageEl) messageEl.textContent = updates.message;
        }
        
        if (updates.title) {
            const titleEl = element.querySelector('.notification-title');
            if (titleEl) {
                titleEl.textContent = updates.title;
            } else if (updates.title) {
                // Create title element if it doesn't exist
                const titleEl = document.createElement('div');
                titleEl.className = 'notification-title';
                titleEl.textContent = updates.title;
                const body = element.querySelector('.notification-body');
                if (body) {
                    body.insertBefore(titleEl, body.firstChild);
                }
            }
        }
        
        if (updates.type) {
            element.className = element.className.replace(/notification-\w+/, `notification-${updates.type}`);
            
            if (updates.icon === undefined) {
                const iconEl = element.querySelector('.notification-icon');
                if (iconEl) iconEl.textContent = this.getDefaultIcon(updates.type);
            }
        }
        
        if (updates.icon !== undefined) {
            const iconEl = element.querySelector('.notification-icon');
            if (iconEl) iconEl.textContent = updates.icon;
        }
        
        this.emitEvent('notificationUpdated', { id, updates, timestamp: Date.now() });
        return true;
    }
    
    // Static getInstance method
    static getInstance() {
        if (!window._notificationManager) {
            window._notificationManager = new NotificationManager();
        }
        return window._notificationManager;
    }
}

// Auto-initialize and make globally available
const initializeNotificationManager = () => {
    try {
        if (!window.vybeNotification) {
            window.vybeNotification = new NotificationManager();
            console.log('Notification Manager initialized successfully');
        }
    } catch (error) {
        console.error('Failed to initialize Notification Manager:', error);
        // Fallback: create a minimal notification system
        window.vybeNotification = {
            show: (message) => console.log('Notification:', message),
            success: (message) => console.log('Success:', message),
            error: (message) => console.error('Error:', message),
            warning: (message) => console.warn('Warning:', message),
            info: (message) => console.info('Info:', message),
            loading: (message) => console.log('Loading:', message)
        };
    }
};

// Initialize when DOM is ready or immediately if already ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeNotificationManager);
} else {
    initializeNotificationManager();
}

// Export for module use
export default NotificationManager;
