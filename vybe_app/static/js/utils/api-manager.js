/* global module */
/**
 * API Manager Utility
 * Provides centralized API call management with caching, debouncing, and request deduplication
 */

class ApiManager {
    constructor() {
        this.cache = new Map();
        this.pendingRequests = new Map();
        this.requestQueue = new Map();
        this.cacheConfig = {
            defaultTTL: 5 * 60 * 1000, // 5 minutes
            maxCacheSize: 100,
            enableCache: true,
            enableDeduplication: true,
            enableDebouncing: true
        };
        this.stats = {
            totalRequests: 0,
            cachedResponses: 0,
            deduplicatedRequests: 0,
            debouncedRequests: 0
        };
    }

    /**
     * Make an API request with caching and deduplication
     * @param {string} url - The API endpoint URL
     * @param {Object} options - Fetch options
     * @param {Object} config - Request configuration
     * @returns {Promise} - The API response
     */
    async request(url, options = {}, config = {}) {
        const requestConfig = { ...this.cacheConfig, ...config };
        const cacheKey = this.generateCacheKey(url, options);
        
        this.stats.totalRequests++;

        // Check cache first
        if (requestConfig.enableCache) {
            const cachedResponse = this.getCachedResponse(cacheKey);
            if (cachedResponse) {
                this.stats.cachedResponses++;
                return cachedResponse;
            }
        }

        // Check for pending requests (deduplication)
        if (requestConfig.enableDeduplication && this.pendingRequests.has(cacheKey)) {
            this.stats.deduplicatedRequests++;
            return this.pendingRequests.get(cacheKey);
        }

        // Create the request promise
        const requestPromise = this.executeRequest(url, options, cacheKey, requestConfig);
        
        // Store pending request for deduplication
        if (requestConfig.enableDeduplication) {
            this.pendingRequests.set(cacheKey, requestPromise);
        }

        try {
            const response = await requestPromise;
            
            // Cache successful responses
            if (requestConfig.enableCache && response.ok) {
                this.cacheResponse(cacheKey, response, requestConfig.ttl || requestConfig.defaultTTL);
            }
            
            return response;
        } finally {
            // Clean up pending request
            if (requestConfig.enableDeduplication) {
                this.pendingRequests.delete(cacheKey);
            }
        }
    }

    /**
     * Debounced API request
     * @param {string} url - The API endpoint URL
     * @param {Object} options - Fetch options
     * @param {number} delay - Debounce delay in milliseconds
     * @param {Object} config - Request configuration
     * @returns {Promise} - The API response
     */
    debouncedRequest(url, options = {}, delay = 300, config = {}) {
        const cacheKey = this.generateCacheKey(url, options);
        
        return new Promise((resolve, reject) => {
            // Clear existing timeout
            if (this.requestQueue.has(cacheKey)) {
                clearTimeout(this.requestQueue.get(cacheKey).timeoutId);
            }

            // Set new timeout
            const timeoutId = setTimeout(async () => {
                try {
                    this.stats.debouncedRequests++;
                    const response = await this.request(url, options, config);
                    resolve(response);
                } catch (error) {
                    reject(error);
                } finally {
                    this.requestQueue.delete(cacheKey);
                }
            }, delay);

            // Store timeout info
            this.requestQueue.set(cacheKey, { timeoutId, resolve, reject });
        });
    }

    /**
     * Execute the actual API request
     * @param {string} url - The API endpoint URL
     * @param {Object} options - Fetch options
     * @param {string} cacheKey - Cache key for this request
     * @param {Object} config - Request configuration
     * @returns {Promise} - The API response
     */
    async executeRequest(url, options, cacheKey, config) {
        const defaultOptions = {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            }
        };

        const fetchOptions = { ...defaultOptions, ...options };

        // Add CSRF token if available
        const csrfToken = document.querySelector('input[name="csrf_token"]')?.value;
        if (csrfToken) {
            fetchOptions.headers['X-CSRFToken'] = csrfToken;
        }

        try {
            const response = await fetch(url, fetchOptions);
            
            // Handle rate limiting
            if (response.status === 429) {
                const retryAfter = response.headers.get('Retry-After') || 60;
                await this.delay(retryAfter * 1000);
                return this.executeRequest(url, options, cacheKey, config);
            }

            return response;
        } catch (error) {
            console.error(`API request failed for ${url}:`, error);
            throw error;
        }
    }

    /**
     * Generate cache key from URL and options
     * @param {string} url - The API endpoint URL
     * @param {Object} options - Fetch options
     * @returns {string} - Cache key
     */
    generateCacheKey(url, options) {
        const keyData = {
            url,
            method: options.method || 'GET',
            body: options.body,
            headers: options.headers
        };
        return btoa(JSON.stringify(keyData));
    }

    /**
     * Get cached response
     * @param {string} cacheKey - Cache key
     * @returns {Object|null} - Cached response or null
     */
    getCachedResponse(cacheKey) {
        const cached = this.cache.get(cacheKey);
        if (!cached) return null;

        // Check if cache is expired
        if (Date.now() > cached.expiresAt) {
            this.cache.delete(cacheKey);
            return null;
        }

        return cached.response;
    }

    /**
     * Cache response
     * @param {string} cacheKey - Cache key
     * @param {Object} response - Response to cache
     * @param {number} ttl - Time to live in milliseconds
     */
    cacheResponse(cacheKey, response, ttl) {
        // Clone response for caching
        const responseClone = response.clone();
        
        this.cache.set(cacheKey, {
            response: responseClone,
            expiresAt: Date.now() + ttl,
            cachedAt: Date.now()
        });

        // Enforce cache size limit
        if (this.cache.size > this.cacheConfig.maxCacheSize) {
            const oldestKey = this.cache.keys().next().value;
            this.cache.delete(oldestKey);
        }
    }

    /**
     * Clear cache
     * @param {string} pattern - Optional pattern to match cache keys
     */
    clearCache(pattern = null) {
        if (!pattern) {
            this.cache.clear();
        } else {
            for (const [key] of this.cache) {
                if (key.includes(pattern)) {
                    this.cache.delete(key);
                }
            }
        }
    }

    /**
     * Invalidate cache for specific URL pattern
     * @param {string} urlPattern - URL pattern to invalidate
     */
    invalidateCache(urlPattern) {
        for (const [key] of this.cache) {
            const keyData = JSON.parse(atob(key));
            if (keyData.url.includes(urlPattern)) {
                this.cache.delete(key);
            }
        }
    }

    /**
     * Get cache statistics
     * @returns {Object} - Cache statistics
     */
    getCacheStats() {
        const now = Date.now();
        let expiredEntries = 0;
        let totalSize = 0;

        for (const [key, value] of this.cache) {
            if (now > value.expiresAt) {
                expiredEntries++;
            }
            totalSize += key.length + JSON.stringify(value).length;
        }

        return {
            totalEntries: this.cache.size,
            expiredEntries,
            totalSize: `${(totalSize / 1024).toFixed(2)} KB`,
            hitRate: this.stats.totalRequests > 0 ? 
                (this.stats.cachedResponses / this.stats.totalRequests * 100).toFixed(2) + '%' : '0%'
        };
    }

    /**
     * Get API manager statistics
     * @returns {Object} - API manager statistics
     */
    getStats() {
        return {
            ...this.stats,
            cache: this.getCacheStats(),
            pendingRequests: this.pendingRequests.size,
            queuedRequests: this.requestQueue.size
        };
    }

    /**
     * Utility function to delay execution
     * @param {number} ms - Milliseconds to delay
     * @returns {Promise} - Promise that resolves after delay
     */
    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    /**
     * Preload API endpoints
     * @param {Array} endpoints - Array of endpoint URLs to preload
     */
    async preloadEndpoints(endpoints) {
        const preloadPromises = endpoints.map(endpoint => 
            this.request(endpoint, {}, { ttl: 10 * 60 * 1000 }) // 10 minute TTL for preloaded data
        );

        try {
            await Promise.allSettled(preloadPromises);
            console.log(`Preloaded ${endpoints.length} API endpoints`);
        } catch (error) {
            console.warn('Some preload requests failed:', error);
        }
    }

    /**
     * Configure API manager
     * @param {Object} config - Configuration options
     */
    configure(config) {
        this.cacheConfig = { ...this.cacheConfig, ...config };
    }

    /**
     * Destroy API manager and cleanup
     */
    destroy() {
        // Clear all pending requests
        this.pendingRequests.clear();
        
        // Clear all queued requests
        this.requestQueue.forEach(({ timeoutId }) => {
            clearTimeout(timeoutId);
        });
        this.requestQueue.clear();
        
        // Clear cache
        this.cache.clear();
    }
}

// Create global instance
window.apiManager = new ApiManager();

// Override global fetch for automatic caching
const originalFetch = window.fetch;
window.fetch = function(url, options = {}) {
    // Only cache GET requests by default
    if (options.method === 'GET' || !options.method) {
        return window.apiManager.request(url, options);
    }
    return originalFetch(url, options);
};

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (window.apiManager) {
        window.apiManager.destroy();
    }
});

// Export for module systems
if (typeof module !== 'undefined' && typeof module.exports !== 'undefined') {
    module.exports = ApiManager;
}
