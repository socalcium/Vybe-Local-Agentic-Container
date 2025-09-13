/* global module */
/**
 * Performance Monitor Utility
 * Tracks memory usage, event listeners, and performance metrics
 * to help identify memory leaks and performance issues
 */

class PerformanceMonitor {
    constructor() {
        this.metrics = {
            memory: [],
            eventListeners: [],
            performance: [],
            errors: []
        };
        this.isMonitoring = false;
        this.monitoringInterval = null;
        this.maxDataPoints = 100; // Keep last 100 data points
        this.startTime = Date.now();
        
        // Performance thresholds
        this.thresholds = {
            memoryWarning: 50 * 1024 * 1024, // 50MB
            memoryCritical: 100 * 1024 * 1024, // 100MB
            eventListenerWarning: 100,
            eventListenerCritical: 200,
            slowHandlerThreshold: 16, // ms
            errorThreshold: 5 // errors per minute
        };
    }

    /**
     * Start monitoring performance metrics
     * @param {number} interval - Monitoring interval in milliseconds (default: 5000)
     */
    start(interval = 5000) {
        if (this.isMonitoring) {
            console.warn('Performance monitoring is already active');
            return;
        }

        this.isMonitoring = true;
        this.monitoringInterval = setInterval(() => {
            this.collectMetrics();
        }, interval);

        console.log('Performance monitoring started');
    }

    /**
     * Stop monitoring performance metrics
     */
    stop() {
        if (!this.isMonitoring) {
            console.warn('Performance monitoring is not active');
            return;
        }

        this.isMonitoring = false;
        if (this.monitoringInterval) {
            clearInterval(this.monitoringInterval);
            this.monitoringInterval = null;
        }

        console.log('Performance monitoring stopped');
    }

    /**
     * Collect current performance metrics
     */
    collectMetrics() {
        const timestamp = Date.now();
        const uptime = timestamp - this.startTime;

        // Memory metrics
        const memoryInfo = this.getMemoryInfo();
        this.addMetric('memory', {
            timestamp,
            uptime,
            used: memoryInfo.usedJSHeapSize,
            total: memoryInfo.totalJSHeapSize,
            limit: memoryInfo.jsHeapSizeLimit,
            percentage: (memoryInfo.usedJSHeapSize / memoryInfo.jsHeapSizeLimit) * 100
        });

        // Event listener metrics
        const eventStats = window.eventManager ? window.eventManager.getStats() : { total: 0 };
        this.addMetric('eventListeners', {
            timestamp,
            uptime,
            total: eventStats.total,
            byEvent: eventStats.byEvent || {},
            byElement: eventStats.byElement || {}
        });

        // Performance metrics
        const perfMetrics = this.getPerformanceMetrics();
        this.addMetric('performance', {
            timestamp,
            uptime,
            ...perfMetrics
        });

        // Check for warnings
        this.checkWarnings();
    }

    /**
     * Get memory information
     * @returns {Object} Memory usage information
     */
    getMemoryInfo() {
        if (performance.memory) {
            return {
                usedJSHeapSize: performance.memory.usedJSHeapSize,
                totalJSHeapSize: performance.memory.totalJSHeapSize,
                jsHeapSizeLimit: performance.memory.jsHeapSizeLimit
            };
        }

        // Fallback for browsers without performance.memory
        return {
            usedJSHeapSize: 0,
            totalJSHeapSize: 0,
            jsHeapSizeLimit: 0
        };
    }

    /**
     * Get performance metrics
     * @returns {Object} Performance metrics
     */
    getPerformanceMetrics() {
        const metrics = {};

        // Navigation timing
        if (performance.timing) {
            const timing = performance.timing;
            metrics.loadTime = timing.loadEventEnd - timing.navigationStart;
            metrics.domReadyTime = timing.domContentLoadedEventEnd - timing.navigationStart;
            metrics.firstPaint = timing.responseStart - timing.navigationStart;
        }

        // Resource timing
        if (performance.getEntriesByType) {
            const resources = performance.getEntriesByType('resource');
            metrics.resourceCount = resources.length;
            metrics.avgResourceLoadTime = resources.length > 0 
                ? resources.reduce((sum, r) => sum + r.duration, 0) / resources.length 
                : 0;
        }

        // Frame rate estimation
        metrics.frameRate = this.estimateFrameRate();

        return metrics;
    }

    /**
     * Estimate frame rate
     * @returns {number} Estimated FPS
     */
    estimateFrameRate() {
        let frameCount = 0;
        let lastTime = performance.now();
        
        const countFrame = () => {
            frameCount++;
            const currentTime = performance.now();
            
            if (currentTime - lastTime >= 1000) { // 1 second
                const fps = Math.round((frameCount * 1000) / (currentTime - lastTime));
                frameCount = 0;
                lastTime = currentTime;
                return fps;
            }
            
            requestAnimationFrame(countFrame);
        };
        
        requestAnimationFrame(countFrame);
        return 60; // Default assumption
    }

    /**
     * Add a metric to the collection
     * @param {string} type - Metric type
     * @param {Object} data - Metric data
     */
    addMetric(type, data) {
        if (!this.metrics[type]) {
            this.metrics[type] = [];
        }

        this.metrics[type].push(data);

        // Keep only the last maxDataPoints
        if (this.metrics[type].length > this.maxDataPoints) {
            this.metrics[type] = this.metrics[type].slice(-this.maxDataPoints);
        }
    }

    /**
     * Check for performance warnings
     */
    checkWarnings() {
        const latestMemory = this.metrics.memory[this.metrics.memory.length - 1];
        const latestEvents = this.metrics.eventListeners[this.metrics.eventListeners.length - 1];

        if (latestMemory) {
            if (latestMemory.used > this.thresholds.memoryCritical) {
                console.error(`CRITICAL: High memory usage: ${this.formatBytes(latestMemory.used)}`);
            } else if (latestMemory.used > this.thresholds.memoryWarning) {
                console.warn(`WARNING: High memory usage: ${this.formatBytes(latestMemory.used)}`);
            }
        }

        if (latestEvents) {
            if (latestEvents.total > this.thresholds.eventListenerCritical) {
                console.error(`CRITICAL: Too many event listeners: ${latestEvents.total}`);
            } else if (latestEvents.total > this.thresholds.eventListenerWarning) {
                console.warn(`WARNING: Many event listeners: ${latestEvents.total}`);
            }
        }
    }

    /**
     * Log an error for tracking
     * @param {Error} error - The error to log
     * @param {string} context - Error context
     */
    logError(error, context = '') {
        this.addMetric('errors', {
            timestamp: Date.now(),
            uptime: Date.now() - this.startTime,
            message: error.message,
            stack: error.stack,
            context
        });
    }

    /**
     * Get performance report
     * @returns {Object} Performance report
     */
    getReport() {
        const report = {
            uptime: Date.now() - this.startTime,
            isMonitoring: this.isMonitoring,
            currentMetrics: {},
            trends: {},
            warnings: []
        };

        // Current metrics
        if (this.metrics.memory.length > 0) {
            report.currentMetrics.memory = this.metrics.memory[this.metrics.memory.length - 1];
        }
        if (this.metrics.eventListeners.length > 0) {
            report.currentMetrics.eventListeners = this.metrics.eventListeners[this.metrics.eventListeners.length - 1];
        }
        if (this.metrics.performance.length > 0) {
            report.currentMetrics.performance = this.metrics.performance[this.metrics.performance.length - 1];
        }

        // Calculate trends
        report.trends = this.calculateTrends();

        // Generate warnings
        report.warnings = this.generateWarnings();

        return report;
    }

    /**
     * Calculate trends from collected data
     * @returns {Object} Trend analysis
     */
    calculateTrends() {
        const trends = {};

        // Memory trend
        if (this.metrics.memory.length >= 2) {
            const recent = this.metrics.memory.slice(-10);
            const memoryGrowth = recent[recent.length - 1].used - recent[0].used;
            trends.memoryGrowth = memoryGrowth;
            trends.memoryGrowthRate = memoryGrowth / (recent.length * 5); // per second
        }

        // Event listener trend
        if (this.metrics.eventListeners.length >= 2) {
            const recent = this.metrics.eventListeners.slice(-10);
            const eventGrowth = recent[recent.length - 1].total - recent[0].total;
            trends.eventListenerGrowth = eventGrowth;
        }

        return trends;
    }

    /**
     * Generate warnings based on current state
     * @returns {Array} Array of warnings
     */
    generateWarnings() {
        const warnings = [];
        const report = this.getReport();

        if (report.currentMetrics.memory) {
            const memory = report.currentMetrics.memory;
            if (memory.used > this.thresholds.memoryCritical) {
                warnings.push({
                    level: 'CRITICAL',
                    message: `Memory usage is critically high: ${this.formatBytes(memory.used)}`,
                    metric: 'memory'
                });
            } else if (memory.used > this.thresholds.memoryWarning) {
                warnings.push({
                    level: 'WARNING',
                    message: `Memory usage is high: ${this.formatBytes(memory.used)}`,
                    metric: 'memory'
                });
            }
        }

        if (report.currentMetrics.eventListeners) {
            const events = report.currentMetrics.eventListeners;
            if (events.total > this.thresholds.eventListenerCritical) {
                warnings.push({
                    level: 'CRITICAL',
                    message: `Too many event listeners: ${events.total}`,
                    metric: 'eventListeners'
                });
            } else if (events.total > this.thresholds.eventListenerWarning) {
                warnings.push({
                    level: 'WARNING',
                    message: `Many event listeners: ${events.total}`,
                    metric: 'eventListeners'
                });
            }
        }

        return warnings;
    }

    /**
     * Format bytes to human readable format
     * @param {number} bytes - Bytes to format
     * @returns {string} Formatted string
     */
    formatBytes(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    /**
     * Clear all collected metrics
     */
    clear() {
        for (const key in this.metrics) {
            this.metrics[key] = [];
        }
        console.log('Performance metrics cleared');
    }

    /**
     * Export metrics data
     * @returns {Object} Metrics data for export
     */
    export() {
        return {
            metadata: {
                startTime: this.startTime,
                uptime: Date.now() - this.startTime,
                isMonitoring: this.isMonitoring,
                maxDataPoints: this.maxDataPoints
            },
            metrics: this.metrics,
            report: this.getReport()
        };
    }
}

// Global performance monitor instance
window.performanceMonitor = new PerformanceMonitor();

// Auto-start monitoring in development mode
if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    window.performanceMonitor.start();
}

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = PerformanceMonitor;
}
