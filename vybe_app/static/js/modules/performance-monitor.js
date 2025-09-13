/**
 * Advanced Performance Monitor
 * Real-time system monitoring and optimization
 */

export class PerformanceMonitor {
    constructor() {
        this.metrics = {
            memory_usage: 0,
            response_times: [],
            api_calls: 0,
            errors: 0,
            concurrent_users: 1
        };
        
        this.observers = [];
        this.isMonitoring = false;
        this.updateInterval = 5000; // 5 seconds
        this.maxDataPoints = 50;
        
        this.perfObserver = null;
        this.memoryObserver = null;
        this.networkObserver = null;
        
        this.init();
    }
    
    init() {
        this.setupPerformanceObservers();
        this.bindEvents();
    }
    
    setupPerformanceObservers() {
        // Performance Observer for navigation and resource timing
        if ('PerformanceObserver' in window) {
            this.perfObserver = new PerformanceObserver((list) => {
                for (const entry of list.getEntries()) {
                    this.processPerformanceEntry(entry);
                }
            });
            
            try {
                this.perfObserver.observe({
                    entryTypes: ['navigation', 'resource', 'measure', 'paint']
                });
            } catch (e) {
                console.warn('Performance Observer not fully supported:', e);
            }
        }
        
        // Memory usage monitoring
        if ('memory' in performance) {
            this.startMemoryMonitoring();
        }
        
        // Network monitoring
        this.setupNetworkMonitoring();
    }
    
    processPerformanceEntry(entry) {
        switch (entry.entryType) {
            case 'navigation':
                this.metrics.page_load_time = entry.loadEventEnd - entry.fetchStart;
                break;
            case 'resource':
                if (entry.name.includes('/api/')) {
                    this.metrics.response_times.push({
                        url: entry.name,
                        duration: entry.duration,
                        timestamp: Date.now()
                    });
                    this.trimArray(this.metrics.response_times);
                }
                break;
            case 'paint':
                if (entry.name === 'first-contentful-paint') {
                    this.metrics.first_contentful_paint = entry.startTime;
                }
                break;
        }
    }
    
    startMemoryMonitoring() {
        const updateMemory = () => {
            if ('memory' in performance) {
                this.metrics.memory_usage = {
                    used: performance.memory.usedJSHeapSize,
                    total: performance.memory.totalJSHeapSize,
                    limit: performance.memory.jsHeapSizeLimit,
                    percentage: (performance.memory.usedJSHeapSize / performance.memory.jsHeapSizeLimit) * 100
                };
            }
        };
        
        updateMemory();
        setInterval(updateMemory, this.updateInterval);
    }
    
    setupNetworkMonitoring() {
        // Monitor fetch requests
        const originalFetch = window.fetch;
        window.fetch = async (...args) => {
            const startTime = performance.now();
            const url = args[0];
            
            try {
                const response = await originalFetch(...args);
                const endTime = performance.now();
                
                this.recordAPICall(url, endTime - startTime, response.status);
                return response;
            } catch (error) {
                const endTime = performance.now();
                this.recordAPICall(url, endTime - startTime, 0, error);
                throw error;
            }
        };
    }
    
    recordAPICall(url, duration, status, error = null) {
        this.metrics.api_calls++;
        
        if (error || status >= 400) {
            this.metrics.errors++;
        }
        
        // Track API response times
        if (typeof url === 'string' && url.includes('/api/')) {
            this.metrics.response_times.push({
                url: url,
                duration: duration,
                status: status,
                timestamp: Date.now(),
                error: error ? error.message : null
            });
            this.trimArray(this.metrics.response_times);
        }
    }
    
    bindEvents() {
        // Monitor page visibility changes
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this.pauseMonitoring();
            } else {
                this.resumeMonitoring();
            }
        });
        
        // Monitor user interactions
        ['click', 'keypress', 'scroll'].forEach(event => {
            document.addEventListener(event, () => {
                this.recordUserActivity(event);
            });
        });
    }
    
    recordUserActivity(eventType) {
        const now = Date.now();
        if (!this.metrics.user_activity) {
            this.metrics.user_activity = [];
        }
        
        this.metrics.user_activity.push({
            type: eventType,
            timestamp: now
        });
        
        this.trimArray(this.metrics.user_activity);
    }
    
    startMonitoring() {
        if (this.isMonitoring) return;
        
        this.isMonitoring = true;
        this.monitoringInterval = setInterval(() => {
            this.collectSystemMetrics();
            this.notifyObservers();
        }, this.updateInterval);
        
        console.log('🔍 Performance monitoring started');
    }
    
    stopMonitoring() {
        if (!this.isMonitoring) return;
        
        this.isMonitoring = false;
        if (this.monitoringInterval) {
            clearInterval(this.monitoringInterval);
        }
        
        console.log('⏹️ Performance monitoring stopped');
    }
    
    pauseMonitoring() {
        if (this.monitoringInterval) {
            clearInterval(this.monitoringInterval);
        }
    }
    
    resumeMonitoring() {
        if (this.isMonitoring) {
            this.monitoringInterval = setInterval(() => {
                this.collectSystemMetrics();
                this.notifyObservers();
            }, this.updateInterval);
        }
    }
    
    async collectSystemMetrics() {
        // Collect additional metrics
        this.metrics.timestamp = Date.now();
        
        // Connection quality
        if ('connection' in navigator) {
            this.metrics.connection = {
                type: navigator.connection.effectiveType,
                downlink: navigator.connection.downlink,
                rtt: navigator.connection.rtt
            };
        }
        
        // Battery status (if available)
        if ('getBattery' in navigator) {
            try {
                const battery = await navigator.getBattery();
                this.metrics.battery = {
                    level: battery.level,
                    charging: battery.charging
                };
            } catch {
                // Battery API not available
            }
        }
        
        // Calculate averages
        this.calculateAverages();
    }
    
    calculateAverages() {
        // Average API response time
        if (this.metrics.response_times.length > 0) {
            const recent = this.metrics.response_times.slice(-10);
            this.metrics.avg_response_time = recent.reduce((sum, entry) => sum + entry.duration, 0) / recent.length;
        }
        
        // Error rate
        const recentCalls = Math.max(this.metrics.api_calls, 1);
        this.metrics.error_rate = (this.metrics.errors / recentCalls) * 100;
    }
    
    addObserver(callback) {
        this.observers.push(callback);
    }
    
    removeObserver(callback) {
        this.observers = this.observers.filter(obs => obs !== callback);
    }
    
    notifyObservers() {
        this.observers.forEach(callback => {
            try {
                callback(this.getMetrics());
            } catch (e) {
                console.warn('Performance observer callback error:', e);
            }
        });
    }
    
    getMetrics() {
        return { ...this.metrics };
    }
    
    getHealthScore() {
        let score = 100;
        
        // Deduct points for high memory usage
        if (this.metrics.memory_usage && this.metrics.memory_usage.percentage > 80) {
            score -= 20;
        } else if (this.metrics.memory_usage && this.metrics.memory_usage.percentage > 60) {
            score -= 10;
        }
        
        // Deduct points for slow API responses
        if (this.metrics.avg_response_time > 2000) {
            score -= 20;
        } else if (this.metrics.avg_response_time > 1000) {
            score -= 10;
        }
        
        // Deduct points for high error rate
        if (this.metrics.error_rate > 10) {
            score -= 30;
        } else if (this.metrics.error_rate > 5) {
            score -= 15;
        }
        
        // Deduct points for poor connection
        if (this.metrics.connection && this.metrics.connection.type === 'slow-2g') {
            score -= 15;
        }
        
        return Math.max(0, score);
    }
    
    getOptimizationSuggestions() {
        const suggestions = [];
        
        if (this.metrics.memory_usage && this.metrics.memory_usage.percentage > 70) {
            suggestions.push({
                type: 'memory',
                severity: 'high',
                message: 'High memory usage detected. Consider refreshing the page.',
                action: 'refresh_page'
            });
        }
        
        if (this.metrics.avg_response_time > 1500) {
            suggestions.push({
                type: 'performance',
                severity: 'medium',
                message: 'API responses are slower than optimal. Check your connection.',
                action: 'check_connection'
            });
        }
        
        if (this.metrics.error_rate > 5) {
            suggestions.push({
                type: 'reliability',
                severity: 'high',
                message: 'High error rate detected. Some features may be unstable.',
                action: 'report_issue'
            });
        }
        
        return suggestions;
    }
    
    exportMetrics() {
        const exportData = {
            timestamp: Date.now(),
            session_duration: Date.now() - (this.metrics.session_start || Date.now()),
            metrics: this.getMetrics(),
            health_score: this.getHealthScore(),
            suggestions: this.getOptimizationSuggestions()
        };
        
        return JSON.stringify(exportData, null, 2);
    }
    
    trimArray(array, maxLength = this.maxDataPoints) {
        if (array.length > maxLength) {
            array.splice(0, array.length - maxLength);
        }
    }
    
    // Public API methods
    static getInstance() {
        if (!window._performanceMonitor) {
            window._performanceMonitor = new PerformanceMonitor();
        }
        return window._performanceMonitor;
    }
}

// Auto-initialize
document.addEventListener('DOMContentLoaded', () => {
    const monitor = PerformanceMonitor.getInstance();
    monitor.startMonitoring();
    
    // Make available globally for debugging
    window.performanceMonitor = monitor;
});
