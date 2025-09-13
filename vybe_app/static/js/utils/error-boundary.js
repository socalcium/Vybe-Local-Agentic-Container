/* global module */
/**
 * Error Boundary Utility
 * Provides comprehensive error handling for frontend failures
 */

class ErrorBoundary {
    constructor() {
        this.errorHandlers = new Map();
        this.recoveryStrategies = new Map();
        this.errorHistory = [];
        this.maxErrorHistory = 50;
        this.isEnabled = true;
        
        this.setupGlobalErrorHandling();
    }

    /**
     * Setup global error handling
     */
    setupGlobalErrorHandling() {
        // Handle unhandled promise rejections
        window.addEventListener('unhandledrejection', (event) => {
            this.handleError('unhandledrejection', event.reason, event);
        });

        // Handle JavaScript errors
        window.addEventListener('error', (event) => {
            this.handleError('javascript', event.error || event.message, event);
        });

        // Handle resource loading errors
        window.addEventListener('error', (event) => {
            if (event.target && event.target !== window) {
                this.handleError('resource', `Failed to load ${event.target.src || event.target.href}`, event);
            }
        }, true);

        // Handle console errors
        this.interceptConsoleErrors();
    }

    /**
     * Intercept console errors for better tracking
     */
    interceptConsoleErrors() {
        const originalError = console.error;
        const originalWarn = console.warn;

        console.error = (...args) => {
            this.handleError('console', args.join(' '), { args });
            originalError.apply(console, args);
        };

        console.warn = (...args) => {
            this.handleError('console_warning', args.join(' '), { args });
            originalWarn.apply(console, args);
        };
    }

    /**
     * Handle an error
     * @param {string} type - Error type
     * @param {Error|string} error - Error object or message
     * @param {Object} context - Additional context
     */
    handleError(type, error, context = {}) {
        if (!this.isEnabled) return;

        const errorInfo = {
            type,
            message: error instanceof Error ? error.message : error,
            stack: error instanceof Error ? error.stack : null,
            timestamp: new Date().toISOString(),
            url: window.location.href,
            userAgent: navigator.userAgent,
            context
        };

        // Add to error history
        this.errorHistory.push(errorInfo);
        if (this.errorHistory.length > this.maxErrorHistory) {
            this.errorHistory.shift();
        }

        // Log error
        console.error(`[ErrorBoundary] ${type}:`, errorInfo);

        // Execute custom error handler if registered
        const handler = this.errorHandlers.get(type);
        if (handler) {
            try {
                handler(errorInfo);
            } catch (handlerError) {
                console.error('Error in custom error handler:', handlerError);
            }
        }

        // Execute recovery strategy if available
        const recovery = this.recoveryStrategies.get(type);
        if (recovery) {
            try {
                recovery(errorInfo);
            } catch (recoveryError) {
                console.error('Error in recovery strategy:', recoveryError);
            }
        }

        // Show user-friendly error message
        this.showUserError(errorInfo);
    }

    /**
     * Register a custom error handler
     * @param {string} type - Error type to handle
     * @param {Function} handler - Error handler function
     */
    registerErrorHandler(type, handler) {
        this.errorHandlers.set(type, handler);
    }

    /**
     * Register a recovery strategy
     * @param {string} type - Error type to recover from
     * @param {Function} strategy - Recovery strategy function
     */
    registerRecoveryStrategy(type, strategy) {
        this.recoveryStrategies.set(type, strategy);
    }

    /**
     * Show user-friendly error message
     * @param {Object} errorInfo - Error information
     */
    showUserError(errorInfo) {
        // Don't show errors for console warnings
        if (errorInfo.type === 'console_warning') return;

        // Create error notification
        const notification = this.createErrorNotification(errorInfo);
        document.body.appendChild(notification);

        // Auto-remove after 10 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 10000);
    }

    /**
     * Create error notification element
     * @param {Object} errorInfo - Error information
     * @returns {HTMLElement} - Notification element
     */
    createErrorNotification(errorInfo) {
        const notification = document.createElement('div');
        notification.className = 'error-notification';
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #f44336;
            color: white;
            padding: 15px;
            border-radius: 5px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.3);
            z-index: 10000;
            max-width: 400px;
            font-family: Arial, sans-serif;
            font-size: 14px;
            animation: slideIn 0.3s ease-out;
        `;

        const title = document.createElement('div');
        title.style.cssText = 'font-weight: bold; margin-bottom: 8px;';
        title.textContent = this.getErrorTitle(errorInfo.type);

        const message = document.createElement('div');
        message.style.cssText = 'margin-bottom: 10px; font-size: 12px;';
        message.textContent = this.getErrorMessage(errorInfo);

        const actions = document.createElement('div');
        actions.style.cssText = 'display: flex; gap: 10px;';

        const dismissBtn = document.createElement('button');
        dismissBtn.textContent = 'Dismiss';
        dismissBtn.style.cssText = `
            background: rgba(255,255,255,0.2);
            border: none;
            color: white;
            padding: 5px 10px;
            border-radius: 3px;
            cursor: pointer;
            font-size: 12px;
        `;
        dismissBtn.onclick = () => notification.remove();

        const retryBtn = document.createElement('button');
        retryBtn.textContent = 'Retry';
        retryBtn.style.cssText = `
            background: rgba(255,255,255,0.2);
            border: none;
            color: white;
            padding: 5px 10px;
            border-radius: 3px;
            cursor: pointer;
            font-size: 12px;
        `;
        retryBtn.onclick = () => this.retryOperation(errorInfo);

        actions.appendChild(dismissBtn);
        actions.appendChild(retryBtn);

        notification.appendChild(title);
        notification.appendChild(message);
        notification.appendChild(actions);

        // Add CSS animation
        const style = document.createElement('style');
        style.textContent = `
            @keyframes slideIn {
                from { transform: translateX(100%); opacity: 0; }
                to { transform: translateX(0); opacity: 1; }
            }
        `;
        document.head.appendChild(style);

        return notification;
    }

    /**
     * Get error title based on type
     * @param {string} type - Error type
     * @returns {string} - Error title
     */
    getErrorTitle(type) {
        const titles = {
            'javascript': 'JavaScript Error',
            'unhandledrejection': 'Promise Rejection',
            'resource': 'Resource Loading Error',
            'api': 'API Error',
            'network': 'Network Error',
            'console': 'Application Error'
        };
        return titles[type] || 'Error';
    }

    /**
     * Get user-friendly error message
     * @param {Object} errorInfo - Error information
     * @returns {string} - User-friendly message
     */
    getErrorMessage(errorInfo) {
        const message = errorInfo.message || 'An unexpected error occurred';
        
        // Truncate long messages
        if (message.length > 100) {
            return message.substring(0, 100) + '...';
        }
        
        return message;
    }

    /**
     * Retry operation based on error type
     * @param {Object} errorInfo - Error information
     */
    retryOperation(errorInfo) {
        switch (errorInfo.type) {
            case 'resource':
                // Retry loading the resource
                if (errorInfo.context.target) {
                    // Force reload by triggering a new request
                    const src = errorInfo.context.target.src;
                    errorInfo.context.target.src = '';
                    errorInfo.context.target.src = src;
                }
                break;
            case 'api':
                // Retry API call if context contains retry function
                if (errorInfo.context.retry) {
                    errorInfo.context.retry();
                }
                break;
            case 'network':
                // Reload page for network errors
                window.location.reload();
                break;
            default:
                // Default retry strategy
                console.log('Retrying operation for:', errorInfo.type);
        }
    }

    /**
     * Wrap a function with error boundary
     * @param {Function} fn - Function to wrap
     * @param {string} context - Context for the function
     * @returns {Function} - Wrapped function
     */
    wrap(fn, context = 'unknown') {
        return (...args) => {
            try {
                return fn.apply(this, args);
            } catch (error) {
                this.handleError('wrapped', error, { context, args });
                throw error;
            }
        };
    }

    /**
     * Wrap an async function with error boundary
     * @param {Function} fn - Async function to wrap
     * @param {string} context - Context for the function
     * @returns {Function} - Wrapped async function
     */
    wrapAsync(fn, context = 'unknown') {
        return async (...args) => {
            try {
                return await fn.apply(this, args);
            } catch (error) {
                this.handleError('async_wrapped', error, { context, args });
                throw error;
            }
        };
    }

    /**
     * Get error statistics
     * @returns {Object} - Error statistics
     */
    getStats() {
        const stats = {};
        this.errorHistory.forEach(error => {
            stats[error.type] = (stats[error.type] || 0) + 1;
        });
        
        return {
            totalErrors: this.errorHistory.length,
            errorTypes: stats,
            recentErrors: this.errorHistory.slice(-10)
        };
    }

    /**
     * Clear error history
     */
    clearHistory() {
        this.errorHistory = [];
    }

    /**
     * Enable/disable error boundary
     * @param {boolean} enabled - Whether to enable error boundary
     */
    setEnabled(enabled) {
        this.isEnabled = enabled;
    }

    /**
     * Get error history
     * @returns {Array} - Error history
     */
    getErrorHistory() {
        return [...this.errorHistory];
    }
}

// Create global instance
window.errorBoundary = new ErrorBoundary();

// Register default recovery strategies
window.errorBoundary.registerRecoveryStrategy('resource', (errorInfo) => {
    console.log('Attempting to recover from resource error:', errorInfo.message);
});

window.errorBoundary.registerRecoveryStrategy('api', (errorInfo) => {
    console.log('Attempting to recover from API error:', errorInfo.message);
});

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ErrorBoundary;
}
