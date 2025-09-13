/**
 * Enhanced Event Manager Utility
 * Centralized event management to prevent memory leaks and improve performance
 * 
 * Features:
 * - Automatic cleanup tracking
 * - Memory leak prevention
 * - Performance monitoring
 * - Error handling
 * - Debounce/throttle utilities
 * - Instance-based management per class
 */

class EventManager {
    constructor(debugName = 'EventManager') {
        this.debugName = debugName;
        this.listeners = new Map();
        this.cleanupCallbacks = new Set();
        this.isDestroyed = false;
        this.listenerCount = 0;
        
        // Performance monitoring
        this.stats = {
            totalListeners: 0,
            activeListeners: 0,
            removedListeners: 0,
            errorCount: 0
        };

        console.log(`EventManager "${this.debugName}" initialized`);
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
            console.warn(`EventManager "${this.debugName}" is destroyed, cannot add listener`);
            return () => {};
        }

        if (!element || typeof handler !== 'function') {
            console.error('Invalid parameters for addEventListener:', { element, event, handler });
            return () => {};
        }

        const key = `${event}_${this.listenerCount++}_${Date.now()}`;
        const wrappedHandler = this.wrapHandler(handler, key, event);
        
        try {
            element.addEventListener(event, wrappedHandler, options);
            
            this.listeners.set(key, {
                element,
                event,
                handler: wrappedHandler,
                originalHandler: handler,
                options,
                addedAt: new Date().toISOString()
            });

            this.stats.totalListeners++;
            this.stats.activeListeners++;

            console.debug(`Added listener: ${this.debugName}.${event} (${key})`);

            // Return cleanup function
            return () => this.remove(key);
        } catch (error) {
            console.error(`Failed to add event listener: ${error.message}`, error);
            return () => {};
        }
    }

    /**
     * Remove a specific event listener
     * @param {string} key - The listener key
     */
    remove(key) {
        const listener = this.listeners.get(key);
        if (listener) {
            try {
                listener.element.removeEventListener(listener.event, listener.handler, listener.options);
                this.listeners.delete(key);
                this.stats.activeListeners--;
                this.stats.removedListeners++;
                console.debug(`Removed listener: ${this.debugName}.${listener.event} (${key})`);
            } catch (error) {
                console.error(`Failed to remove event listener: ${error.message}`, error);
            }
        } else {
            console.warn(`Listener key not found: ${key}`);
        }
    }

    /**
     * Remove all listeners for a specific element
     * @param {Element} element - The element to remove listeners from
     */
    removeAllForElement(element) {
        let removed = 0;
        for (const [key, listener] of this.listeners.entries()) {
            if (listener.element === element) {
                this.remove(key);
                removed++;
            }
        }
        console.debug(`Removed ${removed} listeners for element`);
    }

    /**
     * Remove all listeners for a specific event type
     * @param {string} event - The event type
     */
    removeAllForEvent(event) {
        let removed = 0;
        for (const [key, listener] of this.listeners.entries()) {
            if (listener.event === event) {
                this.remove(key);
                removed++;
            }
        }
        console.debug(`Removed ${removed} listeners for event: ${event}`);
    }

    /**
     * Wrap handler to add error handling and performance monitoring
     * @param {Function} handler - The original handler
     * @param {string} key - The listener key
     * @param {string} eventType - The event type
     * @returns {Function} - Wrapped handler
     */
    wrapHandler(handler, key, eventType) {
        return (event) => {
            try {
                // Performance monitoring
                const startTime = performance.now();
                
                // Call the original handler
                const result = handler.call(this, event);
                
                // Log slow handlers (longer than one frame at 60fps)
                const duration = performance.now() - startTime;
                if (duration > 16.67) {
                    console.warn(`Slow event handler (${duration.toFixed(2)}ms): ${this.debugName}.${eventType} (${key})`);
                }
                
                return result;
            } catch (error) {
                this.stats.errorCount++;
                console.error(`Error in event handler ${this.debugName}.${eventType} (${key}):`, error);
                
                // Optionally prevent error from bubbling up
                if (event && event.preventDefault && event.stopPropagation) {
                    event.preventDefault();
                    event.stopPropagation();
                }
                
                // Notify global error manager if available
                if (window.errorManager) {
                    window.errorManager.handleError(error, `EventHandler:${this.debugName}.${eventType}`);
                }
            }
        };
    }

    /**
     * Add a cleanup callback to be called when destroy() is called
     * @param {Function} callback - The cleanup function
     */
    addCleanupCallback(callback) {
        if (typeof callback === 'function') {
            this.cleanupCallbacks.add(callback);
        }
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

        console.log(`Destroying EventManager "${this.debugName}" with ${this.listeners.size} listeners`);

        // Remove all event listeners
        const listenersToRemove = Array.from(this.listeners.keys());
        listenersToRemove.forEach(key => this.remove(key));

        // Call all cleanup callbacks
        for (const callback of this.cleanupCallbacks) {
            try {
                callback();
            } catch (error) {
                console.error(`Error in cleanup callback for ${this.debugName}:`, error);
            }
        }

        this.cleanupCallbacks.clear();
        this.isDestroyed = true;
        
        console.log(`EventManager "${this.debugName}" destroyed. Final stats:`, this.getStats());
    }

    /**
     * Clean up without destroying (removes all listeners but keeps manager active)
     */
    cleanup() {
        console.log(`Cleaning up EventManager "${this.debugName}" with ${this.listeners.size} listeners`);
        
        const listenersToRemove = Array.from(this.listeners.keys());
        listenersToRemove.forEach(key => this.remove(key));
        
        // Call cleanup callbacks but don't clear them
        for (const callback of this.cleanupCallbacks) {
            try {
                callback();
            } catch (error) {
                console.error(`Error in cleanup callback for ${this.debugName}:`, error);
            }
        }
    }

    /**
     * Get statistics about current listeners
     * @returns {Object} - Listener statistics
     */
    getStats() {
        const stats = {
            ...this.stats,
            activeListeners: this.listeners.size,
            byEvent: {},
            byElement: {}
        };

        for (const listener of this.listeners.values()) {
            // Count by event type
            stats.byEvent[listener.event] = (stats.byEvent[listener.event] || 0) + 1;
            
            // Count by element type
            const elementName = listener.element.tagName || listener.element.constructor.name || 'Unknown';
            stats.byElement[elementName] = (stats.byElement[elementName] || 0) + 1;
        }

        return stats;
    }

    /**
     * Debounce a function to prevent excessive calls
     * @param {Function} func - The function to debounce
     * @param {number} wait - The debounce delay in milliseconds
     * @param {boolean} immediate - Whether to execute immediately on first call
     * @returns {Function} - Debounced function
     */
    debounce(func, wait, immediate = false) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                timeout = null;
                if (!immediate) func.apply(this, args);
            };
            const callNow = immediate && !timeout;
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
            if (callNow) func.apply(this, args);
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

    /**
     * Add a one-time event listener that automatically removes itself
     * @param {Element|Window|Document} element - The element to attach the listener to
     * @param {string} event - The event type
     * @param {Function} handler - The event handler function
     * @param {Object} options - Event listener options
     * @returns {Function} - Cleanup function
     */
    once(element, event, handler, options = {}) {
        const onceHandler = (e) => {
            cleanup();
            handler.call(this, e);
        };
        
        const cleanup = this.add(element, event, onceHandler, options);
        return cleanup;
    }

    /**
     * Add multiple event listeners to the same element
     * @param {Element|Window|Document} element - The element to attach listeners to
     * @param {Object} events - Object with event types as keys and handlers as values
     * @param {Object} options - Event listener options
     * @returns {Function} - Cleanup function for all listeners
     */
    addMultiple(element, events, options = {}) {
        const cleanupFunctions = [];
        
        for (const [eventType, handler] of Object.entries(events)) {
            const cleanup = this.add(element, eventType, handler, options);
            cleanupFunctions.push(cleanup);
        }
        
        return () => {
            cleanupFunctions.forEach(cleanup => cleanup());
        };
    }
}

// Make available globally
if (typeof window !== 'undefined') {
    window.EventManager = EventManager;
}

console.log('Enhanced EventManager utility loaded');
