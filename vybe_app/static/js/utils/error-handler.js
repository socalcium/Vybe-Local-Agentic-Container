/**
 * Error Handling Utilities for Vybe Frontend
 * Provides consistent error display and logging
 */

export class ErrorHandler {
    static errorContainer = null;
    
    /**
     * Initialize error handler with container element
     */
    static init(containerId = 'error-container') {
        this.errorContainer = document.getElementById(containerId);
        if (!this.errorContainer) {
            // Create error container if it doesn't exist
            this.errorContainer = document.createElement('div');
            this.errorContainer.id = containerId;
            this.errorContainer.className = 'error-container';
            this.errorContainer.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 10000;
                max-width: 400px;
            `;
            document.body.appendChild(this.errorContainer);
        }
    }
    
    /**
     * Display error message to user
     */
    static showError(message, type = 'error', duration = 5000) {
        this.init();
        
        const errorElement = document.createElement('div');
        errorElement.className = `alert alert-${type} alert-dismissible fade show`;
        errorElement.style.cssText = `
            margin-bottom: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        `;
        
        errorElement.innerHTML = `
            <strong>${type === 'error' ? 'Error:' : 'Warning:'}</strong> ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        this.errorContainer.appendChild(errorElement);
        
        // Auto-remove after duration
        if (duration > 0) {
            setTimeout(() => {
                if (errorElement.parentNode) {
                    errorElement.remove();
                }
            }, duration);
        }
        
        // Log to console
        console.error(`[Frontend Error] ${message}`);
    }
    
    /**
     * Show success message
     */
    static showSuccess(message, duration = 3000) {
        this.showError(message, 'success', duration);
    }
    
    /**
     * Show warning message
     */
    static showWarning(message, duration = 4000) {
        this.showError(message, 'warning', duration);
    }
    
    /**
     * Handle API errors consistently
     */
    static handleApiError(error, context = '') {
        let message = 'An unexpected error occurred';
        
        if (error.message) {
            message = error.message;
        } else if (typeof error === 'string') {
            message = error;
        }
        
        if (context) {
            message = `${context}: ${message}`;
        }
        
        this.showError(message);
        
        // Send error to backend for logging (optional)
        this.logErrorToBackend(error, context);
    }
    
    /**
     * Log frontend errors to backend
     */
    static async logErrorToBackend(error, context = '') {
        try {
            await fetch('/api/frontend-error', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'same-origin',
                body: JSON.stringify({
                    error: error.message || error.toString(),
                    context: context,
                    url: window.location.href,
                    userAgent: navigator.userAgent,
                    timestamp: new Date().toISOString()
                })
            });
        } catch (e) {
            console.warn('Could not log error to backend:', e);
        }
    }
    
    /**
     * Clear all error messages
     */
    static clearErrors() {
        if (this.errorContainer) {
            this.errorContainer.innerHTML = '';
        }
    }
}

// Global error handler for uncaught errors
window.eventManager.add(window, 'error', (event) => {
    ErrorHandler.logError(event.error || new Error('Uncaught error'));
});

window.eventManager.add(window, 'unhandledrejection', (event) => {
    ErrorHandler.logError(event.reason || new Error('Unhandled promise rejection'));
});

// Initialize error handler when DOM is ready
window.eventManager.add(document, 'DOMContentLoaded', () => {
    ErrorHandler.init();
});
