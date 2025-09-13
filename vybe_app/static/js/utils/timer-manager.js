/* global module */
/**
 * Timer Manager Utility
 * Provides centralized timer management to prevent memory leaks
 * and improve performance
 */

class TimerManager {
    constructor() {
        this.timers = new Map();
        this.intervals = new Map();
        this.cleanupCallbacks = new Set();
        this.isDestroyed = false;
    }

    /**
     * Set a timeout with automatic cleanup tracking
     * @param {Function} callback - The function to execute
     * @param {number} delay - The delay in milliseconds
     * @param {string} name - Optional name for debugging
     * @returns {number} - The timer ID
     */
    setTimeout(callback, delay, name = 'unnamed') {
        if (this.isDestroyed) {
            console.warn('TimerManager is destroyed, cannot set timeout');
            return -1;
        }

        const wrappedCallback = this.wrapCallback(callback, name);
        const timerId = setTimeout(wrappedCallback, delay);
        
        this.timers.set(timerId, {
            callback: wrappedCallback,
            originalCallback: callback,
            delay,
            name,
            startTime: Date.now(),
            type: 'timeout'
        });

        return timerId;
    }

    /**
     * Set an interval with automatic cleanup tracking
     * @param {Function} callback - The function to execute
     * @param {number} delay - The delay in milliseconds
     * @param {string} name - Optional name for debugging
     * @returns {number} - The interval ID
     */
    setInterval(callback, delay, name = 'unnamed') {
        if (this.isDestroyed) {
            console.warn('TimerManager is destroyed, cannot set interval');
            return -1;
        }

        const wrappedCallback = this.wrapCallback(callback, name);
        const intervalId = setInterval(wrappedCallback, delay);
        
        this.intervals.set(intervalId, {
            callback: wrappedCallback,
            originalCallback: callback,
            delay,
            name,
            startTime: Date.now(),
            type: 'interval',
            executionCount: 0
        });

        return intervalId;
    }

    /**
     * Clear a timeout
     * @param {number} timerId - The timer ID to clear
     */
    clearTimeout(timerId) {
        if (this.timers.has(timerId)) {
            clearTimeout(timerId);
            this.timers.delete(timerId);
        }
    }

    /**
     * Clear an interval
     * @param {number} intervalId - The interval ID to clear
     */
    clearInterval(intervalId) {
        if (this.intervals.has(intervalId)) {
            clearInterval(intervalId);
            this.intervals.delete(intervalId);
        }
    }

    /**
     * Clear all timers and intervals
     */
    clearAll() {
        // Clear all timeouts
        for (const [timerId] of this.timers) {
            clearTimeout(timerId);
        }
        this.timers.clear();

        // Clear all intervals
        for (const [intervalId] of this.intervals) {
            clearInterval(intervalId);
        }
        this.intervals.clear();

        // Execute cleanup callbacks
        for (const callback of this.cleanupCallbacks) {
            try {
                callback();
            } catch (error) {
                console.error('Error in timer cleanup callback:', error);
            }
        }
        this.cleanupCallbacks.clear();
    }

    /**
     * Clear all timers and intervals for a specific name
     * @param {string} name - The name to match
     */
    clearByName(name) {
        // Clear timeouts by name
        for (const [timerId, timer] of this.timers) {
            if (timer.name === name) {
                clearTimeout(timerId);
                this.timers.delete(timerId);
            }
        }

        // Clear intervals by name
        for (const [intervalId, interval] of this.intervals) {
            if (interval.name === name) {
                clearInterval(intervalId);
                this.intervals.delete(intervalId);
            }
        }
    }

    /**
     * Wrap callback to add error handling and logging
     * @param {Function} callback - The original callback
     * @param {string} name - The timer name
     * @returns {Function} - Wrapped callback
     */
    wrapCallback(callback, name) {
        return (...args) => {
            try {
                // Add performance monitoring
                const startTime = performance.now();
                
                // Call the original callback
                const result = callback.apply(this, args);
                
                // Log slow callbacks
                const duration = performance.now() - startTime;
                if (duration > 16) { // Longer than one frame
                    console.warn(`Slow timer callback (${duration.toFixed(2)}ms): ${name}`);
                }

                // Update execution count for intervals
                this.intervals.forEach((interval) => {
                    if (interval.callback === arguments.callee) {
                        interval.executionCount++;
                        
                        // Warn about long-running intervals
                        if (interval.executionCount > 1000) {
                            console.warn(`Long-running interval detected: ${name} (${interval.executionCount} executions)`);
                        }
                        return; // Early exit equivalent to break
                    }
                });

                return result;
            } catch (error) {
                console.error(`Error in timer callback ${name}:`, error);
                
                // Auto-clear problematic intervals
                for (const [intervalId, interval] of this.intervals) {
                    if (interval.callback === arguments.callee) {
                        console.warn(`Auto-clearing problematic interval: ${name}`);
                        this.clearInterval(intervalId);
                        break;
                    }
                }
            }
        };
    }

    /**
     * Add a cleanup callback to be executed when clearAll is called
     * @param {Function} callback - The cleanup callback
     */
    addCleanupCallback(callback) {
        this.cleanupCallbacks.add(callback);
    }

    /**
     * Get statistics about active timers and intervals
     * @returns {Object} - Statistics object
     */
    getStats() {
        return {
            activeTimeouts: this.timers.size,
            activeIntervals: this.intervals.size,
            totalTimers: this.timers.size + this.intervals.size,
            timeoutNames: Array.from(this.timers.values()).map(t => t.name),
            intervalNames: Array.from(this.intervals.values()).map(t => t.name)
        };
    }

    /**
     * Destroy the timer manager and clear all timers
     */
    destroy() {
        this.isDestroyed = true;
        this.clearAll();
    }
}

// Create global instance
window.timerManager = new TimerManager();

// Override global setTimeout and setInterval
window.setTimeout = function(callback, delay) {
    return window.timerManager.setTimeout(callback, delay, 'global-timeout');
};

window.setInterval = function(callback, delay) {
    return window.timerManager.setInterval(callback, delay, 'global-interval');
};

window.clearTimeout = function(timerId) {
    window.timerManager.clearTimeout(timerId);
};

window.clearInterval = function(intervalId) {
    window.timerManager.clearInterval(intervalId);
};

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (window.timerManager) {
        window.timerManager.destroy();
    }
});

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = TimerManager;
}
