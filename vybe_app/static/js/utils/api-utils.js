/**
 * API Utilities Module
 * Handles API communication, authentication, and response processing
 * with comprehensive error handling and logging
 */

export class ApiUtils {
    static logLevel = 'INFO'; // DEBUG, INFO, WARN, ERROR
    
    /**
     * Log messages with level checking
     */
    static log(level, message, ...args) {
        const levels = { DEBUG: 0, INFO: 1, WARN: 2, ERROR: 3 };
        if (levels[level] >= levels[this.logLevel]) {
            console[level.toLowerCase()](
                `[${new Date().toISOString()}] ${level}: ${message}`,
                ...args
            );
        }
    }

    /**
     * Handle API responses properly, including authentication redirects
     * @param {Response} response - Fetch response object
     * @returns {Object|null} - Parsed JSON data or null if redirect needed
     */
    static async handleApiResponse(response) {
        this.log('DEBUG', `API Response: ${response.status} ${response.statusText} for ${response.url}`);
        
        // Check if response is ok
        if (!response.ok) {
            // Check if we're being redirected to login (common auth failure)
            if (response.status === 401 || response.url.includes('/login')) {
                this.log('WARN', 'Authentication failed, redirecting to login');
                window.location.href = '/login';
                return null;
            }
            
            let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
            try {
                const errorData = await response.json();
                if (errorData.error) {
                    errorMessage = errorData.error;
                    if (errorData.details) {
                        errorMessage += ` - ${errorData.details}`;
                    }
                }
            } catch {
                this.log('DEBUG', 'Could not parse error response as JSON');
            }
            
            this.log('ERROR', `API Error: ${errorMessage}`);
            throw new Error(errorMessage);
        }

        // Check if response is JSON
        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
            const data = await response.json();
            this.log('DEBUG', 'Successfully parsed JSON response', data);
            return data;
        } else {
            // If it's not JSON, it might be an authentication redirect
            const text = await response.text();
            if (text.includes('<!doctype') || text.includes('<html')) {
                this.log('WARN', 'Received HTML response, likely auth redirect');
                window.location.href = '/login';
                return null;
            }
            this.log('ERROR', 'Unexpected response format');
            throw new Error('Expected JSON response but received: ' + text.substring(0, 100));
        }
    }

    /**
     * Safe fetch wrapper with authentication handling
     * @param {string} url - API endpoint URL
     * @param {Object} options - Fetch options
     * @returns {Object|null} - API response data
     */
    static async safeFetch(url, options = {}) {
        const startTime = Date.now();
        this.log('DEBUG', `Making API request to: ${url}`, options);
        
        try {
            const response = await fetch(url, {
                credentials: 'same-origin', // Include cookies for authentication
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers
                },
                ...options
            });
            
            const result = await this.handleApiResponse(response);
            const duration = Date.now() - startTime;
            this.log('INFO', `API request completed in ${duration}ms: ${url}`);
            
            return result;
        } catch (error) {
            console.error(`API call failed for ${url}:`, error);
            throw error;
        }
    }

    /**
     * Show global status message
     * Uses native notifications in Tauri, fallback to HTML notifications in browser
     * @param {string} message - Status message
     * @param {string} type - Message type (success, error, warning, info)
     */
    static async showGlobalStatus(message, type = 'info') {
        // Check if running inside Tauri
        if (typeof window !== 'undefined' && window.__TAURI__) {
            try {
                const title = this.getNotificationTitle(type);
                await window.__TAURI__.tauri.invoke('show_notification', { title, message });
                this.log('DEBUG', 'Native notification shown:', message);
                return;
            } catch (error) {
                this.log('WARN', 'Failed to show native notification:', error);
                // Fall through to HTML notification
            }
        }
        
        // HTML notification fallback
        this.showHtmlNotification(message, type);
    }

    /**
     * Get appropriate notification title based on type
     */
    static getNotificationTitle(type) {
        switch (type) {
            case 'success':
                return 'Vybe - Success';
            case 'error':
                return 'Vybe - Error';
            case 'warning':
                return 'Vybe - Warning';
            case 'info':
            default:
                return 'Vybe - Info';
        }
    }

    /**
     * Show HTML-based notification (original implementation)
     */
    static showHtmlNotification(message, type = 'info') {
        // Try to find existing notification system
        const notificationContainer = document.getElementById('notifications-container') || 
                                    document.getElementById('global-status') ||
                                    document.querySelector('.notifications');
        
        if (notificationContainer) {
            const notification = document.createElement('div');
            notification.className = `notification ${type}`;
            notification.textContent = message;
            
            // Auto-remove after 5 seconds
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 5000);
            
            notificationContainer.appendChild(notification);
        } else {
            // Fallback to alert if no notification system found
            alert(message);
        }
    }

    /**
     * Check if running inside Tauri
     */
    static isTauri() {
        return typeof window !== 'undefined' && window.__TAURI__;
    }
}

// For backwards compatibility, also export as global functions
window.safeFetch = ApiUtils.safeFetch.bind(ApiUtils);
window.showGlobalStatus = ApiUtils.showGlobalStatus.bind(ApiUtils);
