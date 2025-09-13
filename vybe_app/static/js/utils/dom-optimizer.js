/* global module */
/**
 * DOM Optimizer Utility
 * Addresses Bug #56: Inefficient DOM Manipulation
 * Provides cached DOM queries and optimized manipulation methods
 */

class DOMOptimizer {
    constructor() {
        this.cache = new Map();
        this.observers = new Map();
        this.batchUpdates = new Set();
        this.isBatching = false;
        this.cleanupFunctions = [];
        
        // Initialize performance monitoring
        this.performanceMetrics = {
            queries: 0,
            manipulations: 0,
            cacheHits: 0,
            cacheMisses: 0
        };
        
        // Setup cleanup
        this.setupCleanup();
    }
    
    /**
     * Get element with caching
     */
    getElement(selector, context = document) {
        const cacheKey = `${context === document ? 'doc' : 'ctx'}:${selector}`;
        
        if (this.cache.has(cacheKey)) {
            this.performanceMetrics.cacheHits++;
            return this.cache.get(cacheKey);
        }
        
        this.performanceMetrics.cacheMisses++;
        this.performanceMetrics.queries++;
        
        const element = context.querySelector(selector);
        if (element) {
            this.cache.set(cacheKey, element);
        }
        
        return element;
    }
    
    /**
     * Get multiple elements with caching
     */
    getElements(selector, context = document) {
        const cacheKey = `${context === document ? 'doc' : 'ctx'}:${selector}:all`;
        
        if (this.cache.has(cacheKey)) {
            this.performanceMetrics.cacheHits++;
            return this.cache.get(cacheKey);
        }
        
        this.performanceMetrics.cacheMisses++;
        this.performanceMetrics.queries++;
        
        const elements = Array.from(context.querySelectorAll(selector));
        this.cache.set(cacheKey, elements);
        
        return elements;
    }
    
    /**
     * Get element by ID with caching
     */
    getElementById(id) {
        return this.getElement(`#${id}`);
    }
    
    /**
     * Batch DOM updates for better performance
     */
    batchUpdate(callback) {
        if (this.isBatching) {
            callback();
            return;
        }
        
        this.isBatching = true;
        
        // Use requestAnimationFrame for smooth updates
        requestAnimationFrame(() => {
            try {
                callback();
            } finally {
                this.isBatching = false;
            }
        });
    }
    
    /**
     * Optimized element creation
     */
    createElement(tag, attributes = {}, children = []) {
        const element = document.createElement(tag);
        
        // Set attributes efficiently
        Object.entries(attributes).forEach(([key, value]) => {
            if (key === 'className') {
                element.className = value;
            } else if (key === 'textContent') {
                element.textContent = value;
            } else if (key === 'innerHTML') {
                element.innerHTML = value;
            } else if (key.startsWith('data-')) {
                element.setAttribute(key, value);
            } else {
                element[key] = value;
            }
        });
        
        // Add children efficiently
        children.forEach(child => {
            if (typeof child === 'string') {
                element.appendChild(document.createTextNode(child));
            } else if (child instanceof Node) {
                element.appendChild(child);
            }
        });
        
        return element;
    }
    
    /**
     * Optimized innerHTML update with sanitization
     */
    setInnerHTML(element, html) {
        this.performanceMetrics.manipulations++;
        
        // Basic sanitization (in production, use a proper sanitizer)
        const sanitized = this.sanitizeHTML(html);
        element.innerHTML = sanitized;
    }
    
    /**
     * Optimized text content update
     */
    setTextContent(element, text) {
        this.performanceMetrics.manipulations++;
        element.textContent = text;
    }
    
    /**
     * Optimized class manipulation
     */
    addClass(element, className) {
        this.performanceMetrics.manipulations++;
        element.classList.add(className);
    }
    
    removeClass(element, className) {
        this.performanceMetrics.manipulations++;
        element.classList.remove(className);
    }
    
    toggleClass(element, className) {
        this.performanceMetrics.manipulations++;
        element.classList.toggle(className);
    }
    
    /**
     * Optimized attribute manipulation
     */
    setAttribute(element, name, value) {
        this.performanceMetrics.manipulations++;
        element.setAttribute(name, value);
    }
    
    removeAttribute(element, name) {
        this.performanceMetrics.manipulations++;
        element.removeAttribute(name);
    }
    
    /**
     * Optimized style manipulation
     */
    setStyle(element, property, value) {
        this.performanceMetrics.manipulations++;
        element.style[property] = value;
    }
    
    setStyles(element, styles) {
        this.performanceMetrics.manipulations++;
        Object.assign(element.style, styles);
    }
    
    /**
     * Optimized event delegation
     */
    delegateEvent(container, selector, eventType, handler, options = {}) {
        const wrappedHandler = (event) => {
            const target = event.target.closest(selector);
            if (target && container.contains(target)) {
                handler.call(target, event, target);
            }
        };
        
        window.eventManager.add(container, eventType, wrappedHandler, options);
        
        // Store for cleanup
        this.cleanupFunctions.push(() => {
            window.eventManager.remove(container, eventType, wrappedHandler);
        });
        
        return wrappedHandler;
    }
    
    /**
     * Optimized element insertion
     */
    insertBefore(newElement, referenceElement) {
        this.performanceMetrics.manipulations++;
        referenceElement.parentNode.insertBefore(newElement, referenceElement);
    }
    
    insertAfter(newElement, referenceElement) {
        this.performanceMetrics.manipulations++;
        referenceElement.parentNode.insertBefore(newElement, referenceElement.nextSibling);
    }
    
    appendChild(parent, child) {
        this.performanceMetrics.manipulations++;
        parent.appendChild(child);
    }
    
    removeElement(element) {
        this.performanceMetrics.manipulations++;
        if (element.parentNode) {
            element.parentNode.removeChild(element);
        }
    }
    
    /**
     * Clear cache for specific selectors or all
     */
    clearCache(selector = null) {
        if (selector) {
            // Clear specific cache entries
            const keysToDelete = [];
            this.cache.forEach((value, key) => {
                if (key.includes(selector)) {
                    keysToDelete.push(key);
                }
            });
            keysToDelete.forEach(key => this.cache.delete(key));
        } else {
            // Clear all cache
            this.cache.clear();
        }
    }
    
    /**
     * Get performance metrics
     */
    getPerformanceMetrics() {
        return {
            ...this.performanceMetrics,
            cacheSize: this.cache.size,
            cacheHitRate: this.performanceMetrics.cacheHits / 
                         (this.performanceMetrics.cacheHits + this.performanceMetrics.cacheMisses) || 0
        };
    }
    
    /**
     * Reset performance metrics
     */
    resetPerformanceMetrics() {
        this.performanceMetrics = {
            queries: 0,
            manipulations: 0,
            cacheHits: 0,
            cacheMisses: 0
        };
    }
    
    /**
     * Basic HTML sanitization
     */
    sanitizeHTML(html) {
        // Basic sanitization - in production, use DOMPurify or similar
        const div = document.createElement('div');
        div.textContent = html;
        return div.innerHTML;
    }
    
    /**
     * Setup cleanup on page unload
     */
    setupCleanup() {
        const cleanup = () => {
            this.cleanupFunctions.forEach(fn => {
                try {
                    fn();
                } catch (error) {
                    console.error('Error during DOM optimizer cleanup:', error);
                }
            });
            this.cleanupFunctions = [];
            this.cache.clear();
            this.observers.clear();
        };
        
        window.addEventListener('beforeunload', cleanup);
        this.cleanupFunctions.push(() => {
            window.removeEventListener('beforeunload', cleanup);
        });
    }
    
    /**
     * Destroy the optimizer
     */
    destroy() {
        this.cleanupFunctions.forEach(fn => {
            try {
                fn();
            } catch (error) {
                console.error('Error during DOM optimizer destruction:', error);
            }
        });
        this.cleanupFunctions = [];
        this.cache.clear();
        this.observers.clear();
    }
}

// Create global instance
window.domOptimizer = new DOMOptimizer();

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = DOMOptimizer;
}
