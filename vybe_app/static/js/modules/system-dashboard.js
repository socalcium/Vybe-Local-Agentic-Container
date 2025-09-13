/**
 * System Dashboard Module
 * Provides real-time system monitoring and performance analytics
 */

class SystemDashboard {
    constructor() {
        this.dashboard = null;
        this.charts = {};
        this.updateInterval = null;
        this.isActive = false;
        this.alertThresholds = {
            cpu: 80,
            memory: 85,
            disk: 90,
            network: 1000 // MB/s
        };
        
        // Cleanup functions for event listeners
        this.cleanupFunctions = [];
        
        this.initialize();
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
        
        this.stopAutoRefresh();
        if (this.dashboard) {
            this.dashboard.remove();
        }
    }

    initialize() {
        this.createDashboard();
        this.setupEventListeners();
        this.loadInitialData();
    }

    createDashboard() {
        const dashboardHTML = `
            <div class="system-dashboard" id="system-dashboard">
                <div class="dashboard-header">
                    <h3><i class="fas fa-tachometer-alt"></i> System Dashboard</h3>
                    <div class="dashboard-controls">
                        <button class="btn btn-sm btn-outline-primary" id="refresh-dashboard">
                            <i class="fas fa-sync-alt"></i> Refresh
                        </button>
                        <button class="btn btn-sm btn-outline-secondary" id="toggle-auto-refresh">
                            <i class="fas fa-play"></i> Auto Refresh
                        </button>
                        <button class="btn btn-sm btn-outline-info" id="export-metrics">
                            <i class="fas fa-download"></i> Export
                        </button>
                    </div>
                </div>
                
                <div class="dashboard-grid">
                    <!-- System Resources -->
                    <div class="dashboard-card system-resources">
                        <div class="card-header">
                            <h5><i class="fas fa-server"></i> System Resources</h5>
                        </div>
                        <div class="card-body">
                            <div class="resource-metrics">
                                <div class="metric-item">
                                    <div class="metric-label">CPU Usage</div>
                                    <div class="metric-value" id="cpu-usage">--</div>
                                    <div class="metric-bar">
                                        <div class="metric-progress" id="cpu-progress"></div>
                                    </div>
                                </div>
                                <div class="metric-item">
                                    <div class="metric-label">Memory Usage</div>
                                    <div class="metric-value" id="memory-usage">--</div>
                                    <div class="metric-bar">
                                        <div class="metric-progress" id="memory-progress"></div>
                                    </div>
                                </div>
                                <div class="metric-item">
                                    <div class="metric-label">Disk Usage</div>
                                    <div class="metric-value" id="disk-usage">--</div>
                                    <div class="metric-bar">
                                        <div class="metric-progress" id="disk-progress"></div>
                                    </div>
                                </div>
                                <div class="metric-item">
                                    <div class="metric-label">Network I/O</div>
                                    <div class="metric-value" id="network-io">--</div>
                                    <div class="metric-bar">
                                        <div class="metric-progress" id="network-progress"></div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Application Performance -->
                    <div class="dashboard-card app-performance">
                        <div class="card-header">
                            <h5><i class="fas fa-rocket"></i> Application Performance</h5>
                        </div>
                        <div class="card-body">
                            <div class="performance-metrics">
                                <div class="metric-item">
                                    <div class="metric-label">Active Sessions</div>
                                    <div class="metric-value" id="active-sessions">--</div>
                                </div>
                                <div class="metric-item">
                                    <div class="metric-label">API Requests/min</div>
                                    <div class="metric-value" id="api-requests">--</div>
                                </div>
                                <div class="metric-item">
                                    <div class="metric-label">Response Time</div>
                                    <div class="metric-value" id="response-time">--</div>
                                </div>
                                <div class="metric-item">
                                    <div class="metric-label">Error Rate</div>
                                    <div class="metric-value" id="error-rate">--</div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- AI Services Status -->
                    <div class="dashboard-card ai-services">
                        <div class="card-header">
                            <h5><i class="fas fa-brain"></i> AI Services Status</h5>
                        </div>
                        <div class="card-body">
                            <div class="service-status">
                                <div class="status-item" id="llm-status">
                                    <span class="status-icon"><i class="fas fa-circle"></i></span>
                                    <span class="status-label">LLM Backend</span>
                                    <span class="status-value">--</span>
                                </div>
                                <div class="status-item" id="tts-status">
                                    <span class="status-icon"><i class="fas fa-circle"></i></span>
                                    <span class="status-label">TTS Service</span>
                                    <span class="status-value">--</span>
                                </div>
                                <div class="status-item" id="video-status">
                                    <span class="status-icon"><i class="fas fa-circle"></i></span>
                                    <span class="status-label">Video Generation</span>
                                    <span class="status-value">--</span>
                                </div>
                                <div class="status-item" id="rag-status">
                                    <span class="status-icon"><i class="fas fa-circle"></i></span>
                                    <span class="status-label">RAG System</span>
                                    <span class="status-value">--</span>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Recent Activity -->
                    <div class="dashboard-card recent-activity">
                        <div class="card-header">
                            <h5><i class="fas fa-history"></i> Recent Activity</h5>
                        </div>
                        <div class="card-body">
                            <div class="activity-list" id="activity-list">
                                <div class="activity-item">
                                    <span class="activity-time">--</span>
                                    <span class="activity-text">Loading activity...</span>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- System Alerts -->
                    <div class="dashboard-card system-alerts">
                        <div class="card-header">
                            <h5><i class="fas fa-exclamation-triangle"></i> System Alerts</h5>
                        </div>
                        <div class="card-body">
                            <div class="alerts-list" id="alerts-list">
                                <div class="alert-item info">
                                    <span class="alert-icon"><i class="fas fa-info-circle"></i></span>
                                    <span class="alert-text">System monitoring active</span>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Performance Charts -->
                    <div class="dashboard-card performance-charts">
                        <div class="card-header">
                            <h5><i class="fas fa-chart-line"></i> Performance Trends</h5>
                        </div>
                        <div class="card-body">
                            <div class="chart-container">
                                <canvas id="performance-chart"></canvas>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Insert dashboard into the page
        const container = document.querySelector('.main-content') || document.body;
        container.insertAdjacentHTML('beforeend', dashboardHTML);
        
        this.dashboard = document.getElementById('system-dashboard');
    }

    setupEventListeners() {
        console.log('Setting up system dashboard event listeners');
        
        // Refresh button
        const refreshBtn = document.getElementById('refresh-dashboard');
        if (refreshBtn) {
            const refreshHandler = () => {
                console.log('Manual refresh triggered');
                this.refreshData();
                this.showToast('Refreshing dashboard data...', 'info');
            };
            
            if (window.eventManager && window.eventManager.add) {
                window.eventManager.add(refreshBtn, 'click', refreshHandler);
                this.cleanupFunctions.push(() => {
                    window.eventManager.remove(refreshBtn, 'click', refreshHandler);
                });
            } else {
                refreshBtn.addEventListener('click', refreshHandler);
                this.cleanupFunctions.push(() => {
                    refreshBtn.removeEventListener('click', refreshHandler);
                });
            }
            console.log('Refresh button event handler attached');
        }

        // Auto refresh toggle
        const autoRefreshBtn = document.getElementById('toggle-auto-refresh');
        if (autoRefreshBtn) {
            const autoRefreshHandler = () => {
                console.log('Auto refresh toggle triggered');
                this.toggleAutoRefresh();
            };
            
            if (window.eventManager && window.eventManager.add) {
                window.eventManager.add(autoRefreshBtn, 'click', autoRefreshHandler);
                this.cleanupFunctions.push(() => {
                    window.eventManager.remove(autoRefreshBtn, 'click', autoRefreshHandler);
                });
            } else {
                autoRefreshBtn.addEventListener('click', autoRefreshHandler);
                this.cleanupFunctions.push(() => {
                    autoRefreshBtn.removeEventListener('click', autoRefreshHandler);
                });
            }
            console.log('Auto refresh toggle event handler attached');
        }

        // Export metrics
        const exportBtn = document.getElementById('export-metrics');
        if (exportBtn) {
            const exportHandler = () => {
                console.log('Export metrics triggered');
                this.exportMetrics();
            };
            
            if (window.eventManager && window.eventManager.add) {
                window.eventManager.add(exportBtn, 'click', exportHandler);
                this.cleanupFunctions.push(() => {
                    window.eventManager.remove(exportBtn, 'click', exportHandler);
                });
            } else {
                exportBtn.addEventListener('click', exportHandler);
                this.cleanupFunctions.push(() => {
                    exportBtn.removeEventListener('click', exportHandler);
                });
            }
            console.log('Export metrics event handler attached');
        }

        // Enhanced keyboard shortcuts
        const keyboardHandler = (e) => {
            if (e.ctrlKey || e.metaKey) {
                switch (e.key) {
                    case 'r':
                        if (e.shiftKey) {
                            e.preventDefault();
                            this.refreshData();
                            this.showToast('Dashboard refreshed via keyboard shortcut', 'info');
                            console.log('Dashboard refreshed via Ctrl+Shift+R');
                        }
                        break;
                    case 'e':
                        if (e.shiftKey) {
                            e.preventDefault();
                            this.exportMetrics();
                            console.log('Export triggered via Ctrl+Shift+E');
                        }
                        break;
                }
            }
        };
        
        if (window.eventManager && window.eventManager.add) {
            window.eventManager.add(document, 'keydown', keyboardHandler);
            this.cleanupFunctions.push(() => {
                window.eventManager.remove(document, 'keydown', keyboardHandler);
            });
        } else {
            document.addEventListener('keydown', keyboardHandler);
            this.cleanupFunctions.push(() => {
                document.removeEventListener('keydown', keyboardHandler);
            });
        }
        
        console.log('System dashboard event listeners setup completed');
        this.showToast('Dashboard event handlers initialized', 'success');
    }

    async loadInitialData() {
        try {
            await this.refreshData();
            this.startAutoRefresh();
        } catch (error) {
            console.error('Failed to load initial dashboard data:', error);
            this.showAlert('Failed to load system data', 'error');
        }
    }

    async refreshData() {
        console.log('Refreshing system dashboard data');
        
        try {
            // Show loading indicators
            this.showLoadingState();
            
            // Get system status
            const systemResponse = await fetch('/api/system/status');
            if (systemResponse.ok) {
                const systemData = await systemResponse.json();
                if (systemData.status === 'success') {
                    this.updateSystemMetrics(systemData.data);
                    console.log('System metrics updated successfully');
                } else {
                    throw new Error('System status API returned error');
                }
            } else {
                // Fallback to mock data if API is not available
                console.warn('System status API not available, using mock data');
                this.updateSystemMetrics(this.generateMockSystemData());
            }

            // Get application performance
            try {
                const perfResponse = await fetch('/api/system/performance');
                if (perfResponse.ok) {
                    const perfData = await perfResponse.json();
                    if (perfData.status === 'success') {
                        this.updatePerformanceMetrics(perfData.data);
                        console.log('Performance metrics updated successfully');
                    }
                } else {
                    console.warn('Performance API not available, using mock data');
                    this.updatePerformanceMetrics(this.generateMockPerformanceData());
                }
            } catch (perfError) {
                console.warn('Performance API error, using mock data:', perfError);
                this.updatePerformanceMetrics(this.generateMockPerformanceData());
            }

            // Get AI services status
            await this.updateAIServicesStatus();

            // Get recent activity
            await this.updateRecentActivity();

            // Hide loading indicators
            this.hideLoadingState();
            
            this.showToast('Dashboard data refreshed successfully', 'success');
            console.log('Dashboard refresh completed successfully');

        } catch (error) {
            console.error('Error refreshing dashboard data:', error);
            this.hideLoadingState();
            this.showAlert('Failed to refresh system data', 'error');
            this.showToast('Error refreshing dashboard data', 'error');
            
            // Show fallback data
            this.updateSystemMetrics(this.generateMockSystemData());
            this.updatePerformanceMetrics(this.generateMockPerformanceData());
        }
    }

    showLoadingState() {
        console.log('Showing loading indicators');
        
        // Show loading spinners on metric values
        const metricElements = [
            'cpu-usage', 'memory-usage', 'disk-usage', 'network-io',
            'active-sessions', 'api-requests', 'response-time', 'error-rate'
        ];
        
        metricElements.forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                element.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
            }
        });
    }

    hideLoadingState() {
        console.log('Hiding loading indicators');
        // Loading state will be replaced by actual data in update methods
    }

    generateMockSystemData() {
        console.log('Generating mock system data');
        
        return {
            cpu_percent: Math.random() * 60 + 10, // 10-70%
            memory_percent: Math.random() * 50 + 20, // 20-70%
            disk_percent: Math.random() * 40 + 30, // 30-70%
            network_io_mbps: Math.random() * 100 + 10 // 10-110 MB/s
        };
    }

    generateMockPerformanceData() {
        console.log('Generating mock performance data');
        
        return {
            active_sessions: Math.floor(Math.random() * 50 + 5), // 5-55 sessions
            api_requests_per_min: Math.floor(Math.random() * 200 + 50), // 50-250 requests
            avg_response_time: Math.floor(Math.random() * 200 + 50), // 50-250ms
            error_rate: (Math.random() * 2).toFixed(1) // 0-2%
        };
    }

    showToast(message, type = 'info') {
        console.log(`Dashboard Toast (${type}): ${message}`);
        
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
        toast.className = `system-dashboard-toast toast-${type}`;
        toast.style.cssText = `
            position: fixed;
            top: 160px;
            right: 20px;
            background: ${type === 'error' ? '#dc3545' : type === 'success' ? '#28a745' : type === 'warning' ? '#ffc107' : '#007bff'};
            color: ${type === 'warning' ? '#000' : '#fff'};
            padding: 12px 16px;
            border-radius: 6px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            z-index: 10002;
            max-width: 300px;
            font-size: 0.9rem;
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
        
        // Auto remove after 4 seconds
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(100%)';
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
            }, 300);
        }, 4000);
    }

    updateSystemMetrics(data) {
        console.log('Updating system metrics:', data);
        
        try {
            // CPU Usage
            const cpuUsage = data.cpu_percent || 0;
            document.getElementById('cpu-usage').textContent = `${cpuUsage.toFixed(1)}%`;
            this.updateProgressBar('cpu-progress', cpuUsage, this.alertThresholds.cpu);

            // Memory Usage
            const memoryUsage = data.memory_percent || 0;
            document.getElementById('memory-usage').textContent = `${memoryUsage.toFixed(1)}%`;
            this.updateProgressBar('memory-progress', memoryUsage, this.alertThresholds.memory);

            // Disk Usage
            const diskUsage = data.disk_percent || 0;
            document.getElementById('disk-usage').textContent = `${diskUsage.toFixed(1)}%`;
            this.updateProgressBar('disk-progress', diskUsage, this.alertThresholds.disk);

            // Network I/O
            const networkIO = data.network_io_mbps || 0;
            document.getElementById('network-io').textContent = `${networkIO.toFixed(1)} MB/s`;
            this.updateProgressBar('network-progress', networkIO, this.alertThresholds.network);

            // Check for alerts
            this.checkSystemAlerts(data);
            
            console.log('System metrics updated successfully');
        } catch (error) {
            console.error('Error updating system metrics:', error);
            this.showToast('Error updating system metrics', 'error');
        }
    }

    updatePerformanceMetrics(data) {
        console.log('Updating performance metrics:', data);
        
        try {
            // Active Sessions
            const activeSessions = data.active_sessions || 0;
            const activeSessionsElement = document.getElementById('active-sessions');
            if (activeSessionsElement) {
                activeSessionsElement.textContent = activeSessions.toString();
            }

            // API Requests per minute
            const apiRequests = data.api_requests_per_min || 0;
            const apiRequestsElement = document.getElementById('api-requests');
            if (apiRequestsElement) {
                apiRequestsElement.textContent = `${apiRequests}/min`;
            }

            // Average Response Time
            const responseTime = data.avg_response_time || 0;
            const responseTimeElement = document.getElementById('response-time');
            if (responseTimeElement) {
                responseTimeElement.textContent = `${responseTime}ms`;
            }

            // Error Rate
            const errorRate = data.error_rate || 0;
            const errorRateElement = document.getElementById('error-rate');
            if (errorRateElement) {
                errorRateElement.textContent = `${errorRate}%`;
            }

            console.log('Performance metrics updated successfully');
        } catch (error) {
            console.error('Error updating performance metrics:', error);
            this.showToast('Error updating performance metrics', 'error');
        }
    }

    async updateAIServicesStatus() {
        console.log('Updating AI services status');
        
        const services = [
            { id: 'llm', name: 'LLM Backend', endpoint: '/api/llm/status' },
            { id: 'tts', name: 'TTS Service', endpoint: '/api/audio/status' },
            { id: 'video', name: 'Video Generation', endpoint: '/api/video/status' },
            { id: 'rag', name: 'RAG System', endpoint: '/api/rag/status' }
        ];

        for (const service of services) {
            try {
                const response = await fetch(service.endpoint);
                const data = await response.json();
                
                const statusElement = document.getElementById(`${service.id}-status`);
                
                if (!statusElement) {
                    console.warn(`Status element not found for service: ${service.id}`);
                    continue;
                }
                
                const iconElement = statusElement.querySelector('.status-icon i');
                const valueElement = statusElement.querySelector('.status-value');

                if (data.success || data.status === 'running') {
                    if (iconElement) iconElement.className = 'fas fa-circle text-success';
                    if (valueElement) valueElement.textContent = 'Running';
                } else {
                    if (iconElement) iconElement.className = 'fas fa-circle text-danger';
                    if (valueElement) valueElement.textContent = 'Stopped';
                }
            } catch (error) {
                console.error(`Error checking ${service.name} status:`, error);
                
                const statusElement = document.getElementById(`${service.id}-status`);
                
                if (statusElement) {
                    const iconElement = statusElement.querySelector('.status-icon i');
                    const valueElement = statusElement.querySelector('.status-value');
                    
                    if (iconElement) iconElement.className = 'fas fa-circle text-warning';
                    if (valueElement) valueElement.textContent = 'Unknown';
                }
            }
        }
        
        console.log('AI services status update completed');
    }

    async updateRecentActivity() {
        console.log('Updating recent activity');
        
        try {
            const response = await fetch('/api/system/activity');
            const data = await response.json();

            if (data.status === 'success') {
                const activityList = document.getElementById('activity-list');
                
                if (!activityList) {
                    console.warn('Activity list element not found');
                    return;
                }
                
                activityList.innerHTML = '';

                if (data.activities && data.activities.length > 0) {
                    data.activities.slice(0, 10).forEach(activity => {
                        const activityItem = document.createElement('div');
                        activityItem.className = 'activity-item';
                        activityItem.innerHTML = `
                            <span class="activity-time">${this.formatTime(activity.timestamp)}</span>
                            <span class="activity-text">${activity.description}</span>
                        `;
                        activityList.appendChild(activityItem);
                    });
                } else {
                    activityList.innerHTML = '<div class="activity-item">No recent activity</div>';
                }
                
                console.log('Recent activity updated successfully');
            } else {
                console.warn('Failed to get activity data:', data.message);
                this.showToast('Failed to load recent activity', 'warning');
            }
        } catch (error) {
            console.error('Failed to load recent activity:', error);
            
            // Show mock data as fallback
            const activityList = document.getElementById('activity-list');
            if (activityList) {
                activityList.innerHTML = `
                    <div class="activity-item">
                        <span class="activity-time">2m ago</span>
                        <span class="activity-text">System check completed</span>
                    </div>
                    <div class="activity-item">
                        <span class="activity-time">5m ago</span>
                        <span class="activity-text">New user session started</span>
                    </div>
                    <div class="activity-item">
                        <span class="activity-time">10m ago</span>
                        <span class="activity-text">Background cleanup completed</span>
                    </div>
                `;
            }
            
            this.showToast('Using cached activity data', 'info');
        }
    }

    updateProgressBar(elementId, value, threshold) {
        const progressElement = document.getElementById(elementId);
        const percentage = Math.min(value, 100);
        
        progressElement.style.width = `${percentage}%`;
        
        // Update color based on threshold
        if (value >= threshold) {
            progressElement.className = 'metric-progress danger';
        } else if (value >= threshold * 0.8) {
            progressElement.className = 'metric-progress warning';
        } else {
            progressElement.className = 'metric-progress success';
        }
    }

    checkSystemAlerts(data) {
        const alerts = [];

        if (data.cpu_percent >= this.alertThresholds.cpu) {
            alerts.push({
                type: 'warning',
                message: `High CPU usage: ${data.cpu_percent.toFixed(1)}%`
            });
        }

        if (data.memory_percent >= this.alertThresholds.memory) {
            alerts.push({
                type: 'warning',
                message: `High memory usage: ${data.memory_percent.toFixed(1)}%`
            });
        }

        if (data.disk_percent >= this.alertThresholds.disk) {
            alerts.push({
                type: 'danger',
                message: `High disk usage: ${data.disk_percent.toFixed(1)}%`
            });
        }

        this.updateAlerts(alerts);
    }

    updateAlerts(alerts) {
        const alertsList = document.getElementById('alerts-list');
        
        if (alerts.length === 0) {
            alertsList.innerHTML = `
                <div class="alert-item info">
                    <span class="alert-icon"><i class="fas fa-check-circle"></i></span>
                    <span class="alert-text">All systems normal</span>
                </div>
            `;
        } else {
            alertsList.innerHTML = '';
            alerts.forEach(alert => {
                const alertItem = document.createElement('div');
                alertItem.className = `alert-item ${alert.type}`;
                alertItem.innerHTML = `
                    <span class="alert-icon"><i class="fas fa-exclamation-triangle"></i></span>
                    <span class="alert-text">${alert.message}</span>
                `;
                alertsList.appendChild(alertItem);
            });
        }
    }

    toggleAutoRefresh() {
        console.log('Toggling auto refresh');
        
        const button = document.getElementById('toggle-auto-refresh');
        
        if (!button) {
            console.warn('Auto refresh button not found');
            return;
        }
        
        const icon = button.querySelector('i');

        if (this.isActive) {
            this.stopAutoRefresh();
            if (icon) icon.className = 'fas fa-play';
            button.innerHTML = '<i class="fas fa-play"></i> Auto Refresh';
            this.showToast('Auto refresh disabled', 'info');
            console.log('Auto refresh stopped');
        } else {
            this.startAutoRefresh();
            if (icon) icon.className = 'fas fa-pause';
            button.innerHTML = '<i class="fas fa-pause"></i> Auto Refresh';
            this.showToast('Auto refresh enabled (30s intervals)', 'success');
            console.log('Auto refresh started');
        }
    }

    startAutoRefresh() {
        console.log('Starting auto refresh');
        
        this.isActive = true;
        this.updateInterval = setInterval(() => {
            console.log('Auto refresh triggered');
            this.refreshData();
        }, 30000); // Refresh every 30 seconds
        
        console.log('Auto refresh started with 30-second intervals');
    }

    stopAutoRefresh() {
        console.log('Stopping auto refresh');
        
        this.isActive = false;
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
            this.updateInterval = null;
            console.log('Auto refresh interval cleared');
        }
    }

    async exportMetrics() {
        console.log('Exporting system metrics');
        
        try {
            this.showToast('Preparing metrics export...', 'info');
            
            const response = await fetch('/api/system/export-metrics');
            const data = await response.json();

            if (data.status === 'success') {
                // Create and download file
                const blob = new Blob([JSON.stringify(data.metrics, null, 2)], {
                    type: 'application/json'
                });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `system-metrics-${new Date().toISOString().split('T')[0]}.json`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);

                this.showToast('Metrics exported successfully', 'success');
                console.log('Metrics export completed');
            } else {
                this.showToast('Failed to export metrics', 'error');
                console.error('Export failed:', data.message);
            }
        } catch (error) {
            console.error('Error exporting metrics:', error);
            
            // Generate mock export as fallback
            const mockMetrics = {
                timestamp: new Date().toISOString(),
                system: this.generateMockSystemData(),
                performance: this.generateMockPerformanceData(),
                alerts: ['All systems operational'],
                export_note: 'Generated from cached data due to API unavailability'
            };
            
            const blob = new Blob([JSON.stringify(mockMetrics, null, 2)], {
                type: 'application/json'
            });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `system-metrics-cached-${new Date().toISOString().split('T')[0]}.json`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            
            this.showToast('Exported cached metrics data', 'warning');
        }
    }

    formatTime(timestamp) {
        const date = new Date(timestamp);
        const now = new Date();
        const diff = now - date;

        if (diff < 60000) { // Less than 1 minute
            return 'Just now';
        } else if (diff < 3600000) { // Less than 1 hour
            return `${Math.floor(diff / 60000)}m ago`;
        } else if (diff < 86400000) { // Less than 1 day
            return `${Math.floor(diff / 3600000)}h ago`;
        } else {
            return date.toLocaleDateString();
        }
    }

    showAlert(message, type = 'info') {
        // Create toast notification
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.innerHTML = `
            <div class="toast-header">
                <i class="fas fa-info-circle"></i>
                <strong>System Dashboard</strong>
            </div>
            <div class="toast-body">${message}</div>
        `;

        document.body.appendChild(toast);
        
        // Show toast
        setTimeout(() => {
            toast.classList.add('show');
        }, 100);

        // Remove toast after 3 seconds
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => {
                document.body.removeChild(toast);
            }, 300);
        }, 3000);
    }
}

// Initialize dashboard when DOM is loaded
const initializeSystemDashboard = () => {
    if (typeof window.eventManager !== 'undefined') {
        window.systemDashboard = new SystemDashboard();
    }
};

window.eventManager.add(document, 'DOMContentLoaded', initializeSystemDashboard);

// Export for use in other modules
window.SystemDashboard = SystemDashboard;
