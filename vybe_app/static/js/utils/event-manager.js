/* global module */
/**
 * Event Manager Utility
 * Provides centralized event management to prevent memory leaks
 * and improve performance
 */

class EventManager {
    constructor() {
        this.listeners = new Map();
        this.cleanupCallbacks = new Set();
        this.isDestroyed = false;
    }

    /**
     * Add an event listener with automatic cleanup tracking
     * @param {Element|Window|Document} element - The element to attach the listener to
     * @param {string} event - The event type
     * @param {Function} handler - The event handler function
     * @param {Object} options - Event listener options
     * @returns {Function} - Cleanup function to remove the listener
     */
    add(element, event, handler, options = {}) {
        if (this.isDestroyed) {
            console.warn('EventManager is destroyed, cannot add listener');
            return () => {};
        }

        const key = `${event}_${Date.now()}_${Math.random()}`;
        const wrappedHandler = this.wrapHandler(handler, key);
        
        element.addEventListener(event, wrappedHandler, options);
        
        this.listeners.set(key, {
            element,
            event,
            handler: wrappedHandler,
            originalHandler: handler,
            options
        });

        // Return cleanup function
        return () => this.remove(key);
    }

    /**
     * Remove a specific event listener
     * @param {string} key - The listener key
     */
    remove(key) {
        const listener = this.listeners.get(key);
        if (listener) {
            listener.element.removeEventListener(listener.event, listener.handler, listener.options);
            this.listeners.delete(key);
        }
    }

    /**
     * Remove all listeners for a specific element
     * @param {Element} element - The element to remove listeners from
     */
    removeAllForElement(element) {
        for (const [key, listener] of this.listeners.entries()) {
            if (listener.element === element) {
                this.remove(key);
            }
        }
    }

    /**
     * Remove all listeners for a specific event type
     * @param {string} event - The event type
     */
    removeAllForEvent(event) {
        for (const [key, listener] of this.listeners.entries()) {
            if (listener.event === event) {
                this.remove(key);
            }
        }
    }

    /**
     * Wrap handler to add error handling and logging
     * @param {Function} handler - The original handler
     * @param {string} key - The listener key
     * @returns {Function} - Wrapped handler
     */
    wrapHandler(handler, key) {
        return (event) => {
            try {
                // Add performance monitoring
                const startTime = performance.now();
                
                // Call the original handler
                const result = handler.call(this, event);
                
                // Log slow handlers
                const duration = performance.now() - startTime;
                if (duration > 16) { // Longer than one frame
                    console.warn(`Slow event handler (${duration.toFixed(2)}ms): ${key}`);
                }
                
                return result;
            } catch (error) {
                console.error(`Error in event handler ${key}:`, error);
                // Prevent error from bubbling up
                event.preventDefault();
                event.stopPropagation();
            }
        };
    }

    /**
     * Add a cleanup callback to be called when destroy() is called
     * @param {Function} callback - The cleanup function
     */
    addCleanupCallback(callback) {
        this.cleanupCallbacks.add(callback);
    }

    /**
     * Remove a cleanup callback
     * @param {Function} callback - The cleanup function to remove
     */
    removeCleanupCallback(callback) {
        this.cleanupCallbacks.delete(callback);
    }

    /**
     * Destroy the event manager and clean up all listeners
     */
    destroy() {
        if (this.isDestroyed) return;

        // Remove all event listeners
        for (const key of this.listeners.keys()) {
            this.remove(key);
        }

        // Call all cleanup callbacks
        for (const callback of this.cleanupCallbacks) {
            try {
                callback();
            } catch (error) {
                console.error('Error in cleanup callback:', error);
            }
        }

        this.cleanupCallbacks.clear();
        this.isDestroyed = true;
    }

    /**
     * Get statistics about current listeners
     * @returns {Object} - Listener statistics
     */
    getStats() {
        const stats = {
            total: this.listeners.size,
            byEvent: {},
            byElement: {}
        };

        for (const listener of this.listeners.values()) {
            // Count by event type
            stats.byEvent[listener.event] = (stats.byEvent[listener.event] || 0) + 1;
            
            // Count by element
            const elementName = listener.element.tagName || listener.element.constructor.name;
            stats.byElement[elementName] = (stats.byElement[elementName] || 0) + 1;
        }

        return stats;
    }

    /**
     * Debounce a function to prevent excessive calls
     * @param {Function} func - The function to debounce
     * @param {number} wait - The debounce delay in milliseconds
     * @returns {Function} - Debounced function
     */
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

    /**
     * Throttle a function to limit execution frequency
     * @param {Function} func - The function to throttle
     * @param {number} limit - The throttle limit in milliseconds
     * @returns {Function} - Throttled function
     */
    throttle(func, limit) {
        let inThrottle;
        return function executedFunction(...args) {
            if (!inThrottle) {
                func.apply(this, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }
}

// Global event manager instance
window.eventManager = new EventManager();

// Auto-cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (window.eventManager) {
        window.eventManager.destroy();
    }
});

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = EventManager;
}
