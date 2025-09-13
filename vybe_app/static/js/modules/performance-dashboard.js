/**
 * Performance Dashboard Widget
 * Displays real-time performance metrics in a compact widget
 */

export class PerformanceDashboard {
    constructor() {
        this.isVisible = false;
        this.widget = null;
        this.updateInterval = null;
        this.performanceMonitor = null;
        
        // Cleanup functions for event listeners
        this.cleanupFunctions = [];
        
        this.init();
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
        this.createWidget();
        this.bindEvents();
        this.connectToMonitor();
    }
    
    createWidget() {
        this.widget = document.createElement('div');
        this.widget.className = 'performance-dashboard';
        this.widget.innerHTML = `
            <div class="performance-dashboard-header">
                <span class="performance-dashboard-title">⚡ Performance</span>
                <button class="performance-dashboard-toggle" title="Toggle Dashboard">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M7.41 8.84L12 13.42l4.59-4.58L18 10.25l-6 6-6-6z"/>
                    </svg>
                </button>
            </div>
            <div class="performance-dashboard-content">
                <div class="performance-metric">
                    <div class="metric-label">Health Score</div>
                    <div class="metric-value" id="health-score">--</div>
                    <div class="metric-bar">
                        <div class="metric-bar-fill" id="health-bar"></div>
                    </div>
                </div>
                <div class="performance-metric">
                    <div class="metric-label">Memory Usage</div>
                    <div class="metric-value" id="memory-usage">--</div>
                    <div class="metric-bar">
                        <div class="metric-bar-fill" id="memory-bar"></div>
                    </div>
                </div>
                <div class="performance-metric">
                    <div class="metric-label">API Response</div>
                    <div class="metric-value" id="api-response">--</div>
                </div>
                <div class="performance-metric">
                    <div class="metric-label">Error Rate</div>
                    <div class="metric-value" id="error-rate">--</div>
                </div>
                <div class="performance-metric">
                    <div class="metric-label">CPU Usage</div>
                    <div class="metric-value" id="cpu-usage">--</div>
                    <div class="metric-bar">
                        <div class="metric-bar-fill" id="cpu-bar"></div>
                    </div>
                </div>
                <div class="performance-metric">
                    <div class="metric-label">Disk I/O</div>
                    <div class="metric-value" id="disk-io">--</div>
                </div>
                <div class="performance-metric">
                    <div class="metric-label">Network</div>
                    <div class="metric-value" id="network-usage">--</div>
                </div>
                <div class="performance-actions">
                    <button class="performance-action-btn" id="export-metrics" title="Export Metrics">
                        📊 Export
                    </button>
                    <button class="performance-action-btn" id="clear-cache" title="Clear Cache">
                        🗑️ Clear
                    </button>
                    <button class="performance-action-btn" id="optimize-system" title="Optimize System">
                        ⚡ Optimize
                    </button>
                </div>
            </div>
        `;
        
        // Position widget
        this.widget.style.cssText = `
            position: fixed;
            top: 80px;
            right: 20px;
            width: 250px;
            background: var(--surface-color);
            border: 1px solid var(--border-color);
            border-radius: var(--border-radius-lg);
            box-shadow: var(--shadow-lg);
            z-index: 1000;
            font-size: 0.85rem;
            transform: translateX(100%);
            transition: transform 0.3s ease;
        `;
        
        document.body.appendChild(this.widget);
    }
    
    bindEvents() {
        // Toggle button event
        const toggle = this.widget.querySelector('.performance-dashboard-toggle');
        if (toggle) {
            const toggleHandler = () => {
                console.log('Performance dashboard toggle clicked');
                this.toggle();
            };
            
            if (window.eventManager) {
                const cleanup = window.eventManager.add(toggle, 'click', toggleHandler);
                this.cleanupFunctions.push(cleanup);
            } else {
                toggle.addEventListener('click', toggleHandler);
                this.cleanupFunctions.push(() => toggle.removeEventListener('click', toggleHandler));
            }
        }
        
        // Export metrics button
        const exportBtn = this.widget.querySelector('#export-metrics');
        if (exportBtn) {
            const exportHandler = () => {
                console.log('Export metrics button clicked');
                this.exportMetrics();
            };
            
            if (window.eventManager) {
                const cleanup = window.eventManager.add(exportBtn, 'click', exportHandler);
                this.cleanupFunctions.push(cleanup);
            } else {
                exportBtn.addEventListener('click', exportHandler);
                this.cleanupFunctions.push(() => exportBtn.removeEventListener('click', exportHandler));
            }
        }
        
        // Clear cache button
        const clearBtn = this.widget.querySelector('#clear-cache');
        if (clearBtn) {
            const clearHandler = () => {
                console.log('Clear cache button clicked');
                this.clearCache();
            };
            
            if (window.eventManager) {
                const cleanup = window.eventManager.add(clearBtn, 'click', clearHandler);
                this.cleanupFunctions.push(cleanup);
            } else {
                clearBtn.addEventListener('click', clearHandler);
                this.cleanupFunctions.push(() => clearBtn.removeEventListener('click', clearHandler));
            }
        }
        
        // Optimize system button
        const optimizeBtn = this.widget.querySelector('#optimize-system');
        if (optimizeBtn) {
            const optimizeHandler = () => {
                console.log('Optimize system button clicked');
                this.optimizeSystem();
            };
            
            if (window.eventManager) {
                const cleanup = window.eventManager.add(optimizeBtn, 'click', optimizeHandler);
                this.cleanupFunctions.push(cleanup);
            } else {
                optimizeBtn.addEventListener('click', optimizeHandler);
                this.cleanupFunctions.push(() => optimizeBtn.removeEventListener('click', optimizeHandler));
            }
        }
        
        // Hide dashboard when clicking outside
        const outsideClickHandler = (e) => {
            if (this.isVisible && !this.widget.contains(e.target)) {
                console.log('Clicked outside dashboard, hiding');
                this.hide();
            }
        };
        
        if (window.eventManager) {
            const cleanup = window.eventManager.add(document, 'click', outsideClickHandler);
            this.cleanupFunctions.push(cleanup);
        } else {
            document.addEventListener('click', outsideClickHandler);
            this.cleanupFunctions.push(() => document.removeEventListener('click', outsideClickHandler));
        }
        
        // Keyboard shortcut (Ctrl+Shift+P)
        const keydownHandler = (e) => {
            if (e.ctrlKey && e.shiftKey && e.key === 'P') {
                e.preventDefault();
                console.log('Keyboard shortcut Ctrl+Shift+P pressed');
                this.toggle();
            }
        };
        
        if (window.eventManager) {
            const cleanup = window.eventManager.add(document, 'keydown', keydownHandler);
            this.cleanupFunctions.push(cleanup);
        } else {
            document.addEventListener('keydown', keydownHandler);
            this.cleanupFunctions.push(() => document.removeEventListener('keydown', keydownHandler));
        }
    }
    
    connectToMonitor() {
        // Wait for performance monitor to be available
        const checkMonitor = () => {
            if (window.performanceMonitor) {
                this.performanceMonitor = window.performanceMonitor;
                this.performanceMonitor.addObserver((metrics) => {
                    this.updateMetrics(metrics);
                });
            } else {
                setTimeout(checkMonitor, 1000);
            }
        };
        checkMonitor();
    }
    
    updateMetrics(metrics) {
        console.log('Updating performance metrics:', metrics);
        
        if (!this.isVisible) {
            console.log('Dashboard not visible, skipping metrics update');
            return;
        }
        
        try {
            // Health Score
            if (this.performanceMonitor) {
                const healthScore = this.performanceMonitor.getHealthScore();
                this.updateMetric('health-score', `${healthScore}%`);
                this.updateBar('health-bar', healthScore, this.getHealthColor(healthScore));
                console.log(`Health score updated: ${healthScore}%`);
            }
            
            // Memory Usage
            if (metrics && metrics.memory_usage) {
                const memoryPercent = Math.round(metrics.memory_usage.percentage);
                const memoryMB = Math.round(metrics.memory_usage.used / (1024 * 1024));
                this.updateMetric('memory-usage', `${memoryPercent}% (${memoryMB}MB)`);
                this.updateBar('memory-bar', memoryPercent, this.getMemoryColor(memoryPercent));
                console.log(`Memory usage updated: ${memoryPercent}% (${memoryMB}MB)`);
            }
            
            // CPU Usage (enhanced)
            if (metrics && metrics.cpu_usage !== undefined) {
                const cpuPercent = Math.round(metrics.cpu_usage);
                this.updateMetric('cpu-usage', `${cpuPercent}%`);
                this.updateBar('cpu-bar', cpuPercent, this.getCpuColor(cpuPercent));
                console.log(`CPU usage updated: ${cpuPercent}%`);
            }
            
            // API Response Time
            if (metrics && metrics.avg_response_time !== undefined) {
                const responseTime = Math.round(metrics.avg_response_time);
                this.updateMetric('api-response', `${responseTime}ms`);
                console.log(`API response time updated: ${responseTime}ms`);
            }
            
            // Error Rate
            if (metrics && metrics.error_rate !== undefined) {
                const errorRate = Math.round(metrics.error_rate * 10) / 10;
                this.updateMetric('error-rate', `${errorRate}%`);
                console.log(`Error rate updated: ${errorRate}%`);
            }
            
            // Disk I/O (enhanced)
            if (metrics && metrics.disk_io) {
                const diskIO = `${metrics.disk_io.read || 0}/${metrics.disk_io.write || 0} MB/s`;
                this.updateMetric('disk-io', diskIO);
                console.log(`Disk I/O updated: ${diskIO}`);
            }
            
            // Network Usage (enhanced)
            if (metrics && metrics.network) {
                const networkUsage = `↓${metrics.network.download || 0} ↑${metrics.network.upload || 0} KB/s`;
                this.updateMetric('network-usage', networkUsage);
                console.log(`Network usage updated: ${networkUsage}`);
            }
            
            this.showToast('Metrics updated', 'info');
            
        } catch (error) {
            console.error('Error updating metrics:', error);
            this.showToast('Failed to update metrics', 'error');
        }
    }
    
    updateMetric(elementId, value) {
        const element = this.widget.querySelector(`#${elementId}`);
        if (element) {
            element.textContent = value;
            console.log(`Metric ${elementId} updated to: ${value}`);
        } else {
            console.warn(`Metric element not found: ${elementId}`);
        }
    }
    
    updateBar(elementId, percentage, color) {
        const element = this.widget.querySelector(`#${elementId}`);
        if (element) {
            const clampedPercentage = Math.min(100, Math.max(0, percentage));
            element.style.width = `${clampedPercentage}%`;
            element.style.backgroundColor = color;
            console.log(`Bar ${elementId} updated: ${clampedPercentage}% (${color})`);
        } else {
            console.warn(`Bar element not found: ${elementId}`);
        }
    }
    
    getCpuColor(percentage) {
        if (percentage <= 50) return '#10b981'; // Green
        if (percentage <= 75) return '#f59e0b'; // Yellow
        return '#ef4444'; // Red
    }
    
    getHealthColor(score) {
        if (score >= 80) return '#10b981'; // Green
        if (score >= 60) return '#f59e0b'; // Yellow
        return '#ef4444'; // Red
    }
    
    getMemoryColor(percentage) {
        if (percentage <= 60) return '#10b981'; // Green
        if (percentage <= 80) return '#f59e0b'; // Yellow
        return '#ef4444'; // Red
    }

    /**
     * Show toast notification (placeholder implementation)
     */
    showToast(message, type = 'info') {
        console.log(`Toast (${type}): ${message}`);
        
        // Use existing notification system if available
        if (window.vybeNotification) {
            if (window.vybeNotification[type]) {
                window.vybeNotification[type](message);
            } else {
                window.vybeNotification.info(message);
            }
            return;
        }
        
        if (window.showNotification) {
            window.showNotification(message, type);
            return;
        }
        
        // Fallback toast implementation
        const toast = document.createElement('div');
        toast.className = `performance-toast toast-${type}`;
        toast.style.cssText = `
            position: fixed;
            top: 120px;
            right: 20px;
            background: ${type === 'error' ? '#dc3545' : type === 'success' ? '#28a745' : type === 'warning' ? '#ffc107' : '#007bff'};
            color: ${type === 'warning' ? '#000' : '#fff'};
            padding: 8px 16px;
            border-radius: 4px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
            z-index: 10001;
            max-width: 250px;
            font-size: 0.85rem;
            transition: all 0.3s ease;
            opacity: 0;
            transform: translateX(100%);
        `;
        toast.textContent = message;
        
        document.body.appendChild(toast);
        
        // Animate in
        requestAnimationFrame(() => {
            toast.style.transform = 'translateX(0)';
            toast.style.opacity = '1';
        });
        
        // Auto remove after 3 seconds
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(100%)';
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
            }, 300);
        }, 3000);
    }
    
    show() {
        console.log('Showing performance dashboard');
        this.isVisible = true;
        this.widget.style.transform = 'translateX(0)';
        
        if (this.performanceMonitor) {
            const metrics = this.performanceMonitor.getMetrics();
            this.updateMetrics(metrics);
        } else {
            console.warn('Performance monitor not available');
            this.showToast('Performance monitor not ready', 'warning');
        }
        
        this.showToast('Performance dashboard opened', 'info');
    }
    
    hide() {
        console.log('Hiding performance dashboard');
        this.isVisible = false;
        this.widget.style.transform = 'translateX(100%)';
        this.showToast('Performance dashboard closed', 'info');
    }
    
    toggle() {
        console.log('Toggling performance dashboard');
        if (this.isVisible) {
            this.hide();
        } else {
            this.show();
        }
    }
    
    exportMetrics() {
        console.log('Exporting performance metrics');
        
        if (!this.performanceMonitor) {
            console.warn('Performance monitor not available for export');
            this.showToast('Performance monitor not available', 'error');
            return;
        }
        
        try {
            const data = this.performanceMonitor.exportMetrics();
            const blob = new Blob([data], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            
            const a = document.createElement('a');
            a.href = url;
            a.download = `vybe-performance-metrics-${new Date().toISOString().slice(0, 19)}.json`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            
            this.showToast('Performance metrics exported successfully', 'success');
            console.log('Performance metrics exported successfully');
        } catch (error) {
            console.error('Failed to export metrics:', error);
            this.showToast('Failed to export metrics', 'error');
        }
    }
    
    clearCache() {
        console.log('Clearing cache');
        
        let clearedItems = 0;
        
        // Clear various caches
        if ('caches' in window) {
            caches.keys().then(names => {
                names.forEach(name => {
                    if (name.includes('vybe')) {
                        caches.delete(name);
                        clearedItems++;
                        console.log('Cleared cache:', name);
                    }
                });
            }).catch(error => {
                console.error('Error clearing caches:', error);
            });
        }
        
        // Clear localStorage cache items
        const keysToRemove = [];
        Object.keys(localStorage).forEach(key => {
            if (key.includes('cache') || key.includes('temp')) {
                keysToRemove.push(key);
                localStorage.removeItem(key);
                clearedItems++;
            }
        });
        
        console.log(`Cleared ${clearedItems} cache items`);
        this.showToast(`Cache cleared successfully (${clearedItems} items)`, 'success');
    }
    
    async optimizeSystem() {
        console.log('Starting system optimization');
        
        try {
            // Show optimization in progress
            const optimizeBtn = this.widget.querySelector('#optimize-system');
            const originalText = optimizeBtn.textContent;
            optimizeBtn.textContent = '🔄 Optimizing...';
            optimizeBtn.disabled = true;
            
            this.showToast('System optimization in progress...', 'info');
            
            // Perform optimization tasks
            const optimizations = await this.performOptimizations();
            
            // Update button
            optimizeBtn.textContent = originalText;
            optimizeBtn.disabled = false;
            
            // Show results
            this.showToast(`System optimized: ${optimizations.length} improvements applied`, 'success');
            console.log('System optimization completed:', optimizations);
            
            // Refresh metrics
            this.updateMetrics();
            
        } catch (error) {
            console.error('Optimization failed:', error);
            this.showToast('Optimization failed: ' + error.message, 'error');
            
            // Reset button
            const optimizeBtn = this.widget.querySelector('#optimize-system');
            if (optimizeBtn) {
                optimizeBtn.textContent = '⚡ Optimize';
                optimizeBtn.disabled = false;
            }
        }
    }
    
    async performOptimizations() {
        const optimizations = [];
        
        // 1. Clear browser cache
        if ('caches' in window) {
            const cacheNames = await caches.keys();
            for (const name of cacheNames) {
                if (name.includes('vybe')) {
                    await caches.delete(name);
                    optimizations.push('Browser cache cleared');
                }
            }
        }
        
        // 2. Clear localStorage cache items
        const cacheKeys = Object.keys(localStorage).filter(key => 
            key.includes('cache') || key.includes('temp') || key.includes('session')
        );
        cacheKeys.forEach(key => {
            localStorage.removeItem(key);
        });
        if (cacheKeys.length > 0) {
            optimizations.push(`${cacheKeys.length} cache items cleared`);
        }
        
        // 3. Optimize memory usage
        if (window.gc) {
            window.gc();
            optimizations.push('Memory garbage collection triggered');
        }
        
        // 4. Clear session storage
        sessionStorage.clear();
        optimizations.push('Session storage cleared');
        
        // 5. Request system optimization via API
        try {
            const response = await fetch('/api/system/optimize', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content || ''
                }
            });
            
            if (response.ok) {
                const result = await response.json();
                if (result.optimizations) {
                    optimizations.push(...result.optimizations);
                }
            }
        } catch (error) {
            console.warn('System optimization API not available:', error);
        }
        
        return optimizations;
    }
    
    // Static method to create global instance
    static getInstance() {
        if (!window._performanceDashboard) {
            window._performanceDashboard = new PerformanceDashboard();
        }
        return window._performanceDashboard;
    }
}

// Auto-initialize
window.eventManager.add(document, 'DOMContentLoaded', () => {
    const dashboard = PerformanceDashboard.getInstance();
    
    // Add keyboard shortcut hint to help
    const helpText = document.createElement('div');
    helpText.style.cssText = `
        position: fixed;
        bottom: 20px;
        left: 20px;
        background: var(--bg-color-secondary);
        color: var(--text-color-muted);
        padding: 0.5rem 1rem;
        border-radius: var(--border-radius);
        font-size: 0.75rem;
        opacity: 0.7;
        z-index: 999;
        pointer-events: none;
    `;
    helpText.textContent = 'Press Ctrl+Shift+P for Performance Dashboard';
    
    document.body.appendChild(helpText);
    
    // Hide help text after 5 seconds
    setTimeout(() => {
        helpText.style.display = 'none';
    }, 5000);
    
    // Make available globally
    window.performanceDashboard = dashboard;
});
