/**
 * Frontend Error Management System for Vybe
 * Captures JavaScript errors, API failures, and user interactions for debugging
 */

// Enhanced toast notification function with fallback support
function showToast(message, type = 'info') {
    console.log(`[ErrorManager Toast: ${type}] ${message}`);
    
    // Try to use global toast manager if available
    if (window.showToast) {
        window.showToast(message, type);
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
    `;
    
    document.body.appendChild(notification);
    setTimeout(() => {
        if (notification.parentNode) {
            notification.parentNode.removeChild(notification);
        }
    }, 5000);
}

class VybeErrorManager {
    constructor() {
        this.errors = [];
        this.maxErrors = 50;
        this.debugMode = localStorage.getItem('vybeDebugMode') === 'true';
        this.sessionId = this.generateSessionId();
        this._recentErrorMap = new Map(); // fingerprint -> timestamp
        this._backendLogBackoffUntil = 0; // ms epoch
        
        // Cleanup functions for event listeners
        this.cleanupFunctions = [];
        
        console.log('[ErrorManager] Initializing Error Manager...');
        this.init();
        console.log('[ErrorManager] Error Manager initialized successfully');
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
        // Capture JavaScript errors
        this.setupErrorHandlers();
        
        // Capture unhandled promise rejections
        this.setupPromiseRejectionHandler();
        
        // Capture network errors (skip our logging endpoint)
        this.setupNetworkErrorHandling();
        
        // Performance monitoring
        this.setupPerformanceMonitoring();
        
        // Console override for debug mode
        if (this.debugMode) {
            this.setupConsoleOverride();
        }
        
        console.log('🔧 Vybe Error Manager initialized', { 
            debugMode: this.debugMode, 
            sessionId: this.sessionId 
        });
    }
    
    generateSessionId() {
        return 'sess_' + Math.random().toString(36).substr(2, 9) + '_' + Date.now();
    }
    
    setupErrorHandlers() {
        // Global error handler
        window.eventManager.add(window, 'error', (event) => {
            this.logError({
                type: 'javascript_error',
                message: event.message,
                filename: event.filename,
                lineno: event.lineno,
                colno: event.colno,
                error: event.error ? event.error.toString() : 'Unknown error',
                stack: event.error && event.error.stack ? event.error.stack : '',
                timestamp: new Date().toISOString(),
                url: window.location.href
            });
        });
        
        // Resource loading errors (images, scripts, etc.)
        window.eventManager.add(window, 'error', (event) => {
            if (event.target !== window) {
                this.logError({
                    type: 'resource_error',
                    message: `Failed to load ${event.target.tagName}: ${event.target.src || event.target.href}`,
                    element: event.target.tagName,
                    source: event.target.src || event.target.href,
                    timestamp: new Date().toISOString(),
                    url: window.location.href
                });
            }
        }, true);
    }
    
    setupPromiseRejectionHandler() {
        window.eventManager.add(window, 'unhandledrejection', (event) => {
            this.logError({
                type: 'promise_rejection',
                message: event.reason ? event.reason.toString() : 'Unhandled promise rejection',
                reason: event.reason,
                stack: event.reason && event.reason.stack ? event.reason.stack : '',
                timestamp: new Date().toISOString(),
                url: window.location.href
            });
        });
    }
    
    setupNetworkErrorHandling() {
        // Intercept fetch requests with throttled + deduped backend logging
        const originalFetch = window.fetch;
        let lastLogTs = 0;
        let logBurst = 0;
        window.fetch = async (...args) => {
            const startTime = Date.now();
            try {
                const response = await originalFetch.apply(window, args);
                
                // Log failed requests
                if (!response.ok) {
                    const urlStr = String(args[0] || '');
                    // Never log the logging endpoint itself to avoid loops
                    if (urlStr.includes('/api/debug/log_frontend_error')) {
                        return response;
                    }
                    // Only log server-side failures (reduce noise)
                    if (response.status < 500) {
                        return response;
                    }
                    // throttle to avoid 429 spam: max 5 logs per 2 seconds
                    const now = Date.now();
                    if (now - lastLogTs > 2000) { logBurst = 0; lastLogTs = now; }
                    if (logBurst < 5) {
                        this.logError({
                            type: 'api_error',
                            message: `HTTP ${response.status}: ${response.statusText}`,
                            url: args[0],
                            status: response.status,
                            statusText: response.statusText,
                            duration: Date.now() - startTime,
                            timestamp: new Date().toISOString()
                        });
                        logBurst++;
                    }
                }
                
                return response;
            } catch (error) {
                const now = Date.now();
                if (now - lastLogTs > 2000) { logBurst = 0; lastLogTs = now; }
                if (logBurst < 5) {
                    this.logError({
                        type: 'network_error',
                        message: error.message,
                        url: args[0],
                        error: error.toString(),
                        stack: error.stack,
                        duration: Date.now() - startTime,
                        timestamp: new Date().toISOString()
                    });
                    logBurst++;
                }
                throw error;
            }
        };
    }
    
    setupPerformanceMonitoring() {
        // Monitor slow operations
        const observer = new PerformanceObserver((list) => {
            for (const entry of list.getEntries()) {
                if (entry.duration > 1000) { // Log operations taking longer than 1 second
                    this.logError({
                        type: 'performance_warning',
                        message: `Slow operation detected: ${entry.name}`,
                        duration: entry.duration,
                        entryType: entry.entryType,
                        startTime: entry.startTime,
                        timestamp: new Date().toISOString()
                    });
                }
            }
        });
        
        try {
            observer.observe({ entryTypes: ['measure', 'navigation', 'resource'] });
        } catch {
            // Performance Observer not supported in all browsers
            console.warn('Performance Observer not supported');
        }
    }
    
    setupConsoleOverride() {
        // Store original console methods
        const originalConsole = {
            log: console.log,
            warn: console.warn,
            error: console.error,
            debug: console.debug
        };
        
        // Override console methods to capture logs
        console.error = (...args) => {
            originalConsole.error.apply(console, args);
            this.logError({
                type: 'console_error',
                message: args.join(' '),
                args: args,
                timestamp: new Date().toISOString(),
                url: window.location.href
            });
        };
        
        console.warn = (...args) => {
            originalConsole.warn.apply(console, args);
            if (this.debugMode) {
                this.logError({
                    type: 'console_warning',
                    message: args.join(' '),
                    args: args,
                    timestamp: new Date().toISOString(),
                    url: window.location.href
                });
            }
        };
    }
    
    logError(errorData) {
        console.log('[ErrorManager] Logging error:', errorData.type);
        
        // Add error to local storage
        const enhancedErrorData = {
            ...errorData,
            sessionId: this.sessionId,
            id: this.generateErrorId(),
            userAgent: navigator.userAgent,
            viewport: `${window.innerWidth}x${window.innerHeight}`,
            localTime: new Date().toLocaleString()
        };
        
        this.errors.push(enhancedErrorData);
        
        // Limit stored errors
        if (this.errors.length > this.maxErrors) {
            this.errors.shift();
        }
        
        // Store in localStorage for persistence
        try {
            localStorage.setItem('vybeErrors', JSON.stringify(this.errors.slice(-20))); // Keep last 20
            console.log('[ErrorManager] Error saved to localStorage');
        } catch (e) {
            // localStorage might be full
            console.warn('[ErrorManager] Could not save errors to localStorage:', e);
        }
        
        // Send to backend if enabled
        this.sendErrorToBackend(enhancedErrorData);
        
        // Create visual error notification for important errors
        this.showErrorNotification(enhancedErrorData);
        
        // Log to console in debug mode
        if (this.debugMode) {
            console.group(`🚨 Vybe Error [${errorData.type}]`);
            console.error('Error Data:', enhancedErrorData);
            console.trace('Stack trace');
            showToast(`Error logged: ${errorData.type}`, 'error');
            console.groupEnd();
        }
        
        console.log(`[ErrorManager] Error logged with ID: ${enhancedErrorData.id}`);
    }
    
    showErrorNotification(errorData) {
        // Only show notifications for critical errors
        const criticalTypes = ['javascript_error', 'api_error', 'network_error'];
        if (!criticalTypes.includes(errorData.type)) {
            return;
        }
        
        console.log('[ErrorManager] Showing error notification for:', errorData.type);
        
        // Create error notification element
        const notification = document.createElement('div');
        notification.className = 'error-notification';
        notification.innerHTML = `
            <div class="error-header">
                <span class="error-icon">⚠️</span>
                <span class="error-title">${this.getErrorTitle(errorData.type)}</span>
                <button class="error-close" onclick="this.parentElement.parentElement.remove()">×</button>
            </div>
            <div class="error-message">${errorData.message}</div>
            <div class="error-actions">
                <button class="error-btn" onclick="window.vybeErrorManager.reportError('${errorData.message}', '${errorData.type}')">
                    Report Issue
                </button>
                <button class="error-btn" onclick="window.vybeErrorManager.exportErrors()">
                    Export Logs
                </button>
            </div>
        `;
        
        // Style the notification
        notification.style.cssText = `
            position: fixed;
            top: 80px;
            right: 20px;
            width: 350px;
            background: #fff;
            border: 1px solid #dc3545;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(220, 53, 69, 0.3);
            z-index: 10001;
            font-family: Arial, sans-serif;
            color: #333;
        `;
        
        // Add to page
        document.body.appendChild(notification);
        
        // Auto-remove after 10 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 10000);
        
        showToast('Error notification displayed', 'info');
    }
    
    getErrorTitle(errorType) {
        const titles = {
            'javascript_error': 'JavaScript Error',
            'api_error': 'API Error',
            'network_error': 'Network Error',
            'resource_error': 'Resource Load Error',
            'promise_rejection': 'Promise Rejection',
            'performance_warning': 'Performance Warning',
            'console_error': 'Console Error',
            'manual_report': 'User Report'
        };
        return titles[errorType] || 'Application Error';
    }
    
    generateErrorId() {
        return 'err_' + Math.random().toString(36).substr(2, 9) + '_' + Date.now();
    }
    
    async sendErrorToBackend(errorData) {
        console.log('[ErrorManager] Attempting to send error to backend:', errorData.type);
        
        try {
            // Backoff if we recently received 429
            const now = Date.now();
            if (now < this._backendLogBackoffUntil) {
                console.log('[ErrorManager] Backend logging in backoff period, skipping');
                return;
            }

            // Deduplicate identical errors for 10s window
            const fingerprint = this._fingerprint(errorData);
            const lastTs = this._recentErrorMap.get(fingerprint) || 0;
            if (now - lastTs < 10000) {
                console.log('[ErrorManager] Duplicate error detected, skipping');
                return;
            }
            this._recentErrorMap.set(fingerprint, now);

            // Attempt to send to backend
            console.log('[ErrorManager] Sending error to backend API...');
            const res = await fetch('/api/debug/log_frontend_error', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    ...errorData,
                    client_info: {
                        user_agent: navigator.userAgent,
                        viewport: `${window.innerWidth}x${window.innerHeight}`,
                        timestamp: new Date().toISOString(),
                        url: window.location.href,
                        referrer: document.referrer
                    }
                })
            });
            
            if (res && res.status === 429) {
                // Exponential-style backoff: 60s mute window
                this._backendLogBackoffUntil = Date.now() + 60000;
                console.warn('[ErrorManager] Rate limited by backend, entering backoff period');
                showToast('Error reporting rate limited', 'warning');
            } else if (res && res.ok) {
                console.log('[ErrorManager] Error successfully sent to backend');
                if (this.debugMode) {
                    showToast('Error reported to backend', 'success');
                }
            } else {
                console.warn('[ErrorManager] Backend returned non-OK status:', res ? res.status : 'unknown');
            }
        } catch (e) {
            // Don't log this error to avoid infinite loops
            console.warn('[ErrorManager] Could not send error to backend:', e);
            
            // Simulate successful backend communication for demo
            if (this.debugMode) {
                console.log('[ErrorManager] Simulating backend error logging for demo');
                showToast('Error logged (demo mode)', 'info');
            }
        }
    }

    _fingerprint(errorData) {
        try {
            const core = {
                t: errorData.type || '',
                m: (errorData.message || '').slice(0, 200),
                u: errorData.url || '',
                s: errorData.status || 0,
            };
            return JSON.stringify(core);
        } catch {
            return String(errorData && errorData.message) || 'unknown';
        }
    }
    
    // Public API for manual error reporting
    reportError(message, context = {}) {
        console.log('[ErrorManager] Manual error report:', message);
        showToast('Reporting error...', 'info');
        
        this.logError({
            type: 'manual_report',
            message: message,
            context: context,
            timestamp: new Date().toISOString(),
            url: window.location.href,
            user_initiated: true
        });
        
        showToast('Error reported successfully', 'success');
    }
    
    // Enhanced error summary with analytics
    getErrorSummary() {
        console.log('[ErrorManager] Generating error summary...');
        
        const errorTypes = {};
        const errorsByHour = {};
        const criticalErrors = [];
        
        this.errors.forEach(error => {
            // Count by type
            errorTypes[error.type] = (errorTypes[error.type] || 0) + 1;
            
            // Count by hour
            const hour = new Date(error.timestamp).getHours();
            errorsByHour[hour] = (errorsByHour[hour] || 0) + 1;
            
            // Collect critical errors
            if (['javascript_error', 'api_error', 'network_error'].includes(error.type)) {
                criticalErrors.push(error);
            }
        });
        
        const summary = {
            totalErrors: this.errors.length,
            errorTypes: errorTypes,
            errorsByHour: errorsByHour,
            criticalErrors: criticalErrors.slice(-10), // Last 10 critical errors
            recentErrors: this.errors.slice(-5),
            sessionId: this.sessionId,
            debugMode: this.debugMode,
            lastErrorTime: this.errors.length > 0 ? this.errors[this.errors.length - 1].timestamp : null,
            mostCommonError: this.getMostCommonError(errorTypes),
            sessionDuration: Date.now() - parseInt(this.sessionId.split('_')[2])
        };
        
        console.log('[ErrorManager] Error summary generated:', summary);
        return summary;
    }
    
    getMostCommonError(errorTypes) {
        let maxCount = 0;
        let mostCommon = null;
        
        for (const [type, count] of Object.entries(errorTypes)) {
            if (count > maxCount) {
                maxCount = count;
                mostCommon = type;
            }
        }
        
        return mostCommon ? { type: mostCommon, count: maxCount } : null;
    }
    
    // Clear errors (useful for testing)
    clearErrors() {
        console.log('[ErrorManager] Clearing all errors...');
        this.errors = [];
        localStorage.removeItem('vybeErrors');
        this._recentErrorMap.clear();
        showToast('All errors cleared', 'success');
        console.log('[ErrorManager] All errors cleared');
    }
    
    // Toggle debug mode with enhanced logging
    toggleDebugMode() {
        this.debugMode = !this.debugMode;
        localStorage.setItem('vybeDebugMode', this.debugMode.toString());
        
        console.log(`🔧 Vybe Debug Mode: ${this.debugMode ? 'ON' : 'OFF'}`);
        showToast(`Debug mode ${this.debugMode ? 'enabled' : 'disabled'}`, 'info');
        
        if (this.debugMode) {
            console.log('[ErrorManager] Debug mode enabled - enhanced error logging active');
            console.log('[ErrorManager] Current error summary:', this.getErrorSummary());
        }
        
        return this.debugMode;
    }
    
    // Enhanced export with more metadata
    exportErrors() {
        console.log('[ErrorManager] Exporting error data...');
        showToast('Preparing error export...', 'info');
        
        const exportData = {
            metadata: {
                sessionId: this.sessionId,
                exportTimestamp: new Date().toISOString(),
                userAgent: navigator.userAgent,
                url: window.location.href,
                referrer: document.referrer,
                viewport: `${window.innerWidth}x${window.innerHeight}`,
                colorDepth: screen.colorDepth,
                timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
                language: navigator.language,
                platform: navigator.platform,
                cookieEnabled: navigator.cookieEnabled,
                onlineStatus: navigator.onLine
            },
            errors: this.errors,
            summary: this.getErrorSummary(),
            systemInfo: {
                localStorage_available: typeof(Storage) !== "undefined",
                webgl_supported: !!window.WebGLRenderingContext,
                websocket_supported: !!window.WebSocket,
                notification_permission: 'Notification' in window ? Notification.permission : 'not-supported',
                service_worker_supported: 'serviceWorker' in navigator
            }
        };
        
        // Create downloadable file
        const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `vybe_errors_${this.sessionId}_${new Date().toISOString().split('T')[0]}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        
        showToast('Error data exported successfully', 'success');
        console.log('[ErrorManager] Error data exported to file');
    }
    
    // New method: Get error statistics
    getErrorStatistics() {
        const stats = {
            total: this.errors.length,
            byType: {},
            byTimeOfDay: {},
            severity: {
                critical: 0,
                warning: 0,
                info: 0
            }
        };
        
        this.errors.forEach(error => {
            // By type
            stats.byType[error.type] = (stats.byType[error.type] || 0) + 1;
            
            // By time of day
            const hour = new Date(error.timestamp).getHours();
            const timeOfDay = hour < 6 ? 'night' : hour < 12 ? 'morning' : hour < 18 ? 'afternoon' : 'evening';
            stats.byTimeOfDay[timeOfDay] = (stats.byTimeOfDay[timeOfDay] || 0) + 1;
            
            // By severity
            if (['javascript_error', 'api_error', 'network_error'].includes(error.type)) {
                stats.severity.critical++;
            } else if (['performance_warning', 'console_warning'].includes(error.type)) {
                stats.severity.warning++;
            } else {
                stats.severity.info++;
            }
        });
        
        return stats;
    }
    
    // New method: Search errors by criteria
    searchErrors(criteria = {}) {
        console.log('[ErrorManager] Searching errors with criteria:', criteria);
        
        let filteredErrors = this.errors;
        
        if (criteria.type) {
            filteredErrors = filteredErrors.filter(error => error.type === criteria.type);
        }
        
        if (criteria.message) {
            filteredErrors = filteredErrors.filter(error => 
                error.message.toLowerCase().includes(criteria.message.toLowerCase())
            );
        }
        
        if (criteria.since) {
            const sinceDate = new Date(criteria.since);
            filteredErrors = filteredErrors.filter(error => 
                new Date(error.timestamp) >= sinceDate
            );
        }
        
        console.log(`[ErrorManager] Found ${filteredErrors.length} matching errors`);
        return filteredErrors;
    }
    
    // Static initialization method
    static initialize() {
        console.log('[ErrorManager] Static initialization called');
        if (!window.vybeErrorManager) {
            window.vybeErrorManager = new VybeErrorManager();
            console.log('[ErrorManager] Global instance created');
        }
        return window.vybeErrorManager;
    }
}

// Enhanced initialization with multiple fallbacks
(() => {
    console.log('[ErrorManager] Module loaded, setting up initialization...');
    
    const initializeManager = () => {
        try {
            if (!window.vybeErrorManager) {
                window.vybeErrorManager = new VybeErrorManager();
                console.log('[ErrorManager] Successfully initialized global instance');
                showToast('Error Manager ready', 'success');
                
                // Expose enhanced debug functions globally for console access
                window.vybeDebug = {
                    getErrors: () => window.vybeErrorManager.getErrorSummary(),
                    getStats: () => window.vybeErrorManager.getErrorStatistics(),
                    searchErrors: (criteria) => window.vybeErrorManager.searchErrors(criteria),
                    clearErrors: () => window.vybeErrorManager.clearErrors(),
                    toggleDebug: () => window.vybeErrorManager.toggleDebugMode(),
                    exportErrors: () => window.vybeErrorManager.exportErrors(),
                    reportError: (message, context) => window.vybeErrorManager.reportError(message, context)
                };
                
                console.log('🔧 Enhanced Vybe Debug Tools available at window.vybeDebug');
                console.log('🔧 Available commands: getErrors(), getStats(), searchErrors(), clearErrors(), toggleDebug(), exportErrors(), reportError()');
            }
        } catch (error) {
            console.error('[ErrorManager] Initialization error:', error);
            showToast('Error Manager initialization failed', 'error');
        }
    };
    
    // Initialize immediately if DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeManager);
    } else {
        initializeManager();
    }
    
    // Also try with window load as fallback
    if (document.readyState !== 'complete') {
        window.addEventListener('load', () => {
            if (!window.vybeErrorManager) {
                console.log('[ErrorManager] Fallback initialization on window load');
                initializeManager();
            }
        });
    }
})();
