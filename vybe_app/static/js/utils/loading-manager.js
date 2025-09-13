/* global module */
/**
 * Loading State Manager Utility
 * Addresses Bug #57: Missing Loading States
 * Provides consistent loading indicators and user feedback across the application
 */

class LoadingManager {
    constructor() {
        this.activeLoaders = new Map();
        this.loadingStates = new Map();
        this.globalLoadingState = false;
        this.cleanupFunctions = [];
        
        // Default loading templates
        this.templates = {
            spinner: '<div class="loading-spinner"></div>',
            dots: '<div class="loading-dots"><span></span><span></span><span></span></div>',
            progress: '<div class="loading-progress"><div class="progress-bar"></div></div>',
            skeleton: '<div class="loading-skeleton"></div>'
        };
        
        this.setupGlobalLoading();
        this.setupCleanup();
    }
    
    /**
     * Show loading state for an element
     */
    showLoading(element, options = {}) {
        const {
            type = 'spinner',
            message = 'Loading...',
            overlay = false,
            preserveContent = false,
            duration = 0,
            progress = null
        } = options;
        
        const loaderId = this.generateLoaderId();
        
        // Create loading element
        const loadingElement = this.createLoadingElement(type, message, progress);
        
        // Store original content if preserving
        let originalContent = null;
        if (preserveContent) {
            originalContent = element.innerHTML;
        }
        
        // Apply loading state
        if (overlay) {
            this.applyOverlayLoading(element, loadingElement, loaderId);
        } else {
            this.applyInlineLoading(element, loadingElement, loaderId, originalContent);
        }
        
        // Store loader info
        this.activeLoaders.set(loaderId, {
            element,
            loadingElement,
            originalContent,
            type,
            startTime: Date.now(),
            duration,
            progress
        });
        
        // Auto-hide if duration specified
        if (duration > 0) {
            setTimeout(() => {
                this.hideLoading(loaderId);
            }, duration);
        }
        
        return loaderId;
    }
    
    /**
     * Hide loading state
     */
    hideLoading(loaderId) {
        const loader = this.activeLoaders.get(loaderId);
        if (!loader) return;
        
        const { element, loadingElement, originalContent } = loader;
        
        // Remove loading element
        if (loadingElement && loadingElement.parentNode) {
            loadingElement.parentNode.removeChild(loadingElement);
        }
        
        // Restore original content if preserved
        if (originalContent !== null) {
            element.innerHTML = originalContent;
        }
        
        // Remove from active loaders
        this.activeLoaders.delete(loaderId);
    }
    
    /**
     * Update loading progress
     */
    updateProgress(loaderId, progress) {
        const loader = this.activeLoaders.get(loaderId);
        if (!loader) return;
        
        const progressBar = loader.loadingElement.querySelector('.progress-bar');
        if (progressBar) {
            progressBar.style.width = `${Math.min(100, Math.max(0, progress))}%`;
        }
        
        loader.progress = progress;
    }
    
    /**
     * Update loading message
     */
    updateMessage(loaderId, message) {
        const loader = this.activeLoaders.get(loaderId);
        if (!loader) return;
        
        const messageElement = loader.loadingElement.querySelector('.loading-message');
        if (messageElement) {
            messageElement.textContent = message;
        }
    }
    
    /**
     * Show global loading state
     */
    showGlobalLoading(message = 'Loading...', type = 'spinner') {
        this.globalLoadingState = true;
        
        // Create global loading overlay
        const overlay = this.createGlobalOverlay(message, type);
        document.body.appendChild(overlay);
        
        // Store global loading state
        this.loadingStates.set('global', {
            element: overlay,
            message,
            type,
            startTime: Date.now()
        });
        
        // Add body class
        document.body.classList.add('global-loading');
    }
    
    /**
     * Hide global loading state
     */
    hideGlobalLoading() {
        this.globalLoadingState = false;
        
        const globalState = this.loadingStates.get('global');
        if (globalState && globalState.element) {
            globalState.element.remove();
        }
        
        this.loadingStates.delete('global');
        document.body.classList.remove('global-loading');
    }
    
    /**
     * Show loading for API calls
     */
    showApiLoading(apiCall, options = {}) {
        const {
            element = null,
            message = 'Processing...',
            type = 'spinner',
            showGlobal = false
        } = options;
        
        let loaderId = null;
        
        // Show loading state
        if (element) {
            loaderId = this.showLoading(element, { type, message });
        } else if (showGlobal) {
            this.showGlobalLoading(message, type);
        }
        
        // Wrap API call
        return apiCall.then(result => {
            if (loaderId) {
                this.hideLoading(loaderId);
            } else if (showGlobal) {
                this.hideGlobalLoading();
            }
            return result;
        }).catch(error => {
            if (loaderId) {
                this.hideLoading(loaderId);
            } else if (showGlobal) {
                this.hideGlobalLoading();
            }
            throw error;
        });
    }
    
    /**
     * Show loading for button clicks
     */
    showButtonLoading(button, message = 'Processing...') {
        const originalText = button.textContent;
        const originalDisabled = button.disabled;
        
        button.textContent = message;
        button.disabled = true;
        
        // Add loading class
        button.classList.add('loading');
        
        return {
            hide: () => {
                button.textContent = originalText;
                button.disabled = originalDisabled;
                button.classList.remove('loading');
            }
        };
    }
    
    /**
     * Show loading for form submissions
     */
    showFormLoading(form, message = 'Submitting...') {
        const submitButton = form.querySelector('button[type="submit"]');
        const loader = submitButton ? this.showButtonLoading(submitButton, message) : null;
        
        // Disable all form inputs
        const inputs = form.querySelectorAll('input, select, textarea, button');
        inputs.forEach(input => {
            input.disabled = true;
        });
        
        return {
            hide: () => {
                if (loader) loader.hide();
                inputs.forEach(input => {
                    input.disabled = false;
                });
            }
        };
    }
    
    /**
     * Create loading element
     */
    createLoadingElement(type, message, progress = null) {
        const container = document.createElement('div');
        container.className = 'loading-container';
        
        // Add spinner/dots
        if (type === 'progress' && progress !== null) {
            container.innerHTML = `
                <div class="loading-progress">
                    <div class="progress-bar" style="width: ${progress}%"></div>
                </div>
                <div class="loading-message">${message}</div>
            `;
        } else {
            container.innerHTML = `
                ${this.templates[type] || this.templates.spinner}
                <div class="loading-message">${message}</div>
            `;
        }
        
        return container;
    }
    
    /**
     * Apply overlay loading
     */
    applyOverlayLoading(element, loadingElement, loaderId) {
        // Create overlay container
        const overlay = document.createElement('div');
        overlay.className = 'loading-overlay';
        overlay.dataset.loaderId = loaderId;
        
        // Position overlay
        overlay.style.position = 'absolute';
        overlay.style.top = '0';
        overlay.style.left = '0';
        overlay.style.width = '100%';
        overlay.style.height = '100%';
        overlay.style.backgroundColor = 'rgba(0, 0, 0, 0.7)';
        overlay.style.display = 'flex';
        overlay.style.alignItems = 'center';
        overlay.style.justifyContent = 'center';
        overlay.style.zIndex = '1000';
        
        overlay.appendChild(loadingElement);
        
        // Make element relative if not already
        if (getComputedStyle(element).position === 'static') {
            element.style.position = 'relative';
        }
        
        element.appendChild(overlay);
    }
    
    /**
     * Apply inline loading
     */
    applyInlineLoading(element, loadingElement, loaderId, originalContent) {
        if (originalContent === null) {
            element.innerHTML = '';
        }
        element.appendChild(loadingElement);
    }
    
    /**
     * Create global overlay
     */
    createGlobalOverlay(message, type) {
        const overlay = document.createElement('div');
        overlay.className = 'global-loading-overlay';
        overlay.innerHTML = `
            <div class="global-loading-content">
                ${this.templates[type] || this.templates.spinner}
                <div class="global-loading-message">${message}</div>
            </div>
        `;
        
        // Style overlay
        overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.8);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 9999;
        `;
        
        return overlay;
    }
    
    /**
     * Generate unique loader ID
     */
    generateLoaderId() {
        return `loader_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }
    
    /**
     * Setup global loading styles
     */
    setupGlobalLoading() {
        // Add CSS styles if not already present
        if (!document.getElementById('loading-manager-styles')) {
            const style = document.createElement('style');
            style.id = 'loading-manager-styles';
            style.textContent = `
                .loading-spinner {
                    width: 40px;
                    height: 40px;
                    border: 4px solid #f3f3f3;
                    border-top: 4px solid #3498db;
                    border-radius: 50%;
                    animation: spin 1s linear infinite;
                }
                
                .loading-dots {
                    display: flex;
                    gap: 4px;
                }
                
                .loading-dots span {
                    width: 8px;
                    height: 8px;
                    background-color: #3498db;
                    border-radius: 50%;
                    animation: dots 1.4s ease-in-out infinite both;
                }
                
                .loading-dots span:nth-child(1) { animation-delay: -0.32s; }
                .loading-dots span:nth-child(2) { animation-delay: -0.16s; }
                
                .loading-progress {
                    width: 200px;
                    height: 4px;
                    background-color: #f3f3f3;
                    border-radius: 2px;
                    overflow: hidden;
                }
                
                .loading-progress .progress-bar {
                    height: 100%;
                    background-color: #3498db;
                    transition: width 0.3s ease;
                }
                
                .loading-container {
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    gap: 12px;
                    padding: 20px;
                }
                
                .loading-message {
                    color: #666;
                    font-size: 14px;
                    text-align: center;
                }
                
                .global-loading-overlay .global-loading-content {
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    gap: 16px;
                    color: white;
                }
                
                .global-loading-message {
                    font-size: 16px;
                    font-weight: 500;
                }
                
                .global-loading button.loading {
                    position: relative;
                    color: transparent;
                }
                
                .global-loading button.loading::after {
                    content: '';
                    position: absolute;
                    top: 50%;
                    left: 50%;
                    transform: translate(-50%, -50%);
                    width: 16px;
                    height: 16px;
                    border: 2px solid transparent;
                    border-top: 2px solid currentColor;
                    border-radius: 50%;
                    animation: spin 1s linear infinite;
                }
                
                @keyframes spin {
                    0% { transform: translate(-50%, -50%) rotate(0deg); }
                    100% { transform: translate(-50%, -50%) rotate(360deg); }
                }
                
                @keyframes dots {
                    0%, 80%, 100% { transform: scale(0); }
                    40% { transform: scale(1); }
                }
            `;
            document.head.appendChild(style);
        }
    }
    
    /**
     * Setup cleanup on page unload
     */
    setupCleanup() {
        const cleanup = () => {
            // Hide all active loaders
            this.activeLoaders.forEach((loader, loaderId) => {
                this.hideLoading(loaderId);
            });
            
            // Hide global loading
            if (this.globalLoadingState) {
                this.hideGlobalLoading();
            }
            
            // Execute cleanup functions
            this.cleanupFunctions.forEach(fn => {
                try {
                    fn();
                } catch (error) {
                    console.error('Error during loading manager cleanup:', error);
                }
            });
        };
        
        window.addEventListener('beforeunload', cleanup);
        this.cleanupFunctions.push(() => {
            window.removeEventListener('beforeunload', cleanup);
        });
    }
    
    /**
     * Get loading statistics
     */
    getStats() {
        return {
            activeLoaders: this.activeLoaders.size,
            globalLoading: this.globalLoadingState,
            totalLoaders: this.loadingStates.size
        };
    }
    
    /**
     * Destroy the loading manager
     */
    destroy() {
        // Hide all loaders
        this.activeLoaders.forEach((loader, loaderId) => {
            this.hideLoading(loaderId);
        });
        
        if (this.globalLoadingState) {
            this.hideGlobalLoading();
        }
        
        // Execute cleanup functions
        this.cleanupFunctions.forEach(fn => {
            try {
                fn();
            } catch (error) {
                console.error('Error during loading manager destruction:', error);
            }
        });
        
        this.cleanupFunctions = [];
        this.activeLoaders.clear();
        this.loadingStates.clear();
    }
}

// Create global instance
window.loadingManager = new LoadingManager();

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = LoadingManager;
}
