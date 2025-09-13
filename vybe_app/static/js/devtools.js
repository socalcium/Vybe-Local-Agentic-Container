/**
 * Developer Tools JavaScript
 * Handles system monitoring, log viewing, and configuration display
 */

// Import the centralized notification manager (attaches to window.notificationManager)
import './services/NotificationManager.js';

class DevToolsManager {
    constructor() {
        this.autoRefreshInterval = null;
        this.autoRefreshEnabled = false;
        this.systemInfoRefreshRate = 5000; // 5 seconds
        this.logRefreshRate = 10000; // 10 seconds
        this.eventListeners = []; // Track event listeners for cleanup
        
        // Cleanup functions for event listeners
        this.cleanupFunctions = [];
        
        console.log('[DevTools] Initializing DevTools Manager...');
        this.initializeElements();
        this.bindEvents();
        this.initializeTabs();
        this.loadInitialData();
        
        // Cleanup on page unload
        window.addEventListener('beforeunload', () => {
            this.cleanup();
        });
        
        console.log('[DevTools] DevTools Manager initialized successfully');
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
    
    cleanup() {
        // Clear auto-refresh interval
        if (this.autoRefreshInterval) {
            clearInterval(this.autoRefreshInterval);
            this.autoRefreshInterval = null;
        }
        
        // Remove all tracked event listeners
        this.eventListeners.forEach(({element, event, handler}) => {
            if (element && element.removeEventListener) {
                element.removeEventListener(event, handler);
            }
        });
        this.eventListeners = [];
    }
    
    addEventListener(element, event, handler) {
        window.eventManager.add(element, event, handler);
        this.eventListeners.push({element, event, handler});
    }

    initializeElements() {
        // System info elements
        this.cpuUsage = document.getElementById('cpu-usage');
        this.cpuProgress = document.getElementById('cpu-progress');
        this.memoryUsage = document.getElementById('memory-usage');
        this.memoryProgress = document.getElementById('memory-progress');
        this.memoryDetails = document.getElementById('memory-details');
        this.gpuUsage = document.getElementById('gpu-usage');
        this.gpuProgress = document.getElementById('gpu-progress');
        this.gpuDetails = document.getElementById('gpu-details');
        this.diskUsage = document.getElementById('disk-usage');
        this.diskProgress = document.getElementById('disk-progress');
        this.diskDetails = document.getElementById('disk-details');

        // Log viewer elements
        this.logViewer = document.getElementById('log-viewer');
        this.logLevelFilter = document.getElementById('log-level-filter');
        this.logLinesCount = document.getElementById('log-lines-count');
        this.autoRefreshToggle = document.getElementById('auto-refresh-toggle');

        // Config elements
        this.configTabs = document.querySelectorAll('.config-tab');
        this.configPanels = document.querySelectorAll('.config-panel');

        // Status elements
        this.llmStatus = document.getElementById('llm-status');
        this.databaseStatus = document.getElementById('database-status');
        this.ragStatus = document.getElementById('rag-status');
        this.jobManagerStatus = document.getElementById('job-manager-status');

        // Button elements
        this.refreshSystemInfoBtn = document.getElementById('refresh-system-info');
        this.refreshLogsBtn = document.getElementById('refresh-logs');
        this.clearLogsBtn = document.getElementById('clear-logs');
        this.refreshConfigBtn = document.getElementById('refresh-config');
        this.refreshStatusBtn = document.getElementById('refresh-status');
    }

    bindEvents() {
        console.log('[DevTools] Binding event handlers...');
        
        // System info refresh
        if (this.refreshSystemInfoBtn) {
            const systemInfoHandler = () => {
                console.log('[DevTools] Refresh system info button clicked');
                window.notificationManager.showInfo('Refreshing system information...');
                this.loadSystemInfo();
            };
            this.refreshSystemInfoBtn.addEventListener('click', systemInfoHandler);
            this.cleanupFunctions.push(() => this.refreshSystemInfoBtn.removeEventListener('click', systemInfoHandler));
            console.log('[DevTools] System info refresh button bound');
        } else {
            console.warn('[DevTools] Refresh system info button not found');
        }

        // Log controls
        if (this.refreshLogsBtn) {
            const refreshLogsHandler = () => {
                console.log('[DevTools] Refresh logs button clicked');
                window.notificationManager.showInfo('Refreshing system logs...');
                this.loadLogs();
            };
            this.refreshLogsBtn.addEventListener('click', refreshLogsHandler);
            this.cleanupFunctions.push(() => this.refreshLogsBtn.removeEventListener('click', refreshLogsHandler));
            console.log('[DevTools] Refresh logs button bound');
        } else {
            console.warn('[DevTools] Refresh logs button not found');
        }
        
        if (this.clearLogsBtn) {
            const clearLogsHandler = () => {
                console.log('[DevTools] Clear logs button clicked');
                window.notificationManager.showInfo('Clearing log view...');
                this.clearLogView();
            };
            this.clearLogsBtn.addEventListener('click', clearLogsHandler);
            this.cleanupFunctions.push(() => this.clearLogsBtn.removeEventListener('click', clearLogsHandler));
            console.log('[DevTools] Clear logs button bound');
        } else {
            console.warn('[DevTools] Clear logs button not found');
        }
        
        if (this.autoRefreshToggle) {
            const autoRefreshHandler = () => {
                console.log('[DevTools] Auto refresh toggle clicked');
                this.toggleAutoRefresh();
            };
            this.autoRefreshToggle.addEventListener('click', autoRefreshHandler);
            this.cleanupFunctions.push(() => this.autoRefreshToggle.removeEventListener('click', autoRefreshHandler));
            console.log('[DevTools] Auto refresh toggle bound');
        } else {
            console.warn('[DevTools] Auto refresh toggle not found');
        }
        
        if (this.logLevelFilter) {
            const filterHandler = () => {
                console.log('[DevTools] Log level filter changed');
                this.filterLogs();
            };
            this.logLevelFilter.addEventListener('change', filterHandler);
            this.cleanupFunctions.push(() => this.logLevelFilter.removeEventListener('change', filterHandler));
            console.log('[DevTools] Log level filter bound');
        } else {
            console.warn('[DevTools] Log level filter not found');
        }
        
        if (this.logLinesCount) {
            const linesCountHandler = () => {
                console.log('[DevTools] Log lines count changed');
                window.notificationManager.showInfo('Updating log display...');
                this.loadLogs();
            };
            this.logLinesCount.addEventListener('change', linesCountHandler);
            this.cleanupFunctions.push(() => this.logLinesCount.removeEventListener('change', linesCountHandler));
            console.log('[DevTools] Log lines count bound');
        } else {
            console.warn('[DevTools] Log lines count not found');
        }

        // Config refresh
        if (this.refreshConfigBtn) {
            const refreshConfigHandler = () => {
                console.log('[DevTools] Refresh config button clicked');
                window.notificationManager.showInfo('Refreshing configuration...');
                this.loadAllConfigs();
            };
            this.refreshConfigBtn.addEventListener('click', refreshConfigHandler);
            this.cleanupFunctions.push(() => this.refreshConfigBtn.removeEventListener('click', refreshConfigHandler));
            console.log('[DevTools] Refresh config button bound');
        } else {
            console.warn('[DevTools] Refresh config button not found');
        }

        // Status refresh
        if (this.refreshStatusBtn) {
            const refreshStatusHandler = () => {
                console.log('[DevTools] Refresh status button clicked');
                window.notificationManager.showInfo('Refreshing application status...');
                this.loadApplicationStatus();
            };
            this.refreshStatusBtn.addEventListener('click', refreshStatusHandler);
            this.cleanupFunctions.push(() => this.refreshStatusBtn.removeEventListener('click', refreshStatusHandler));
            console.log('[DevTools] Refresh status button bound');
        } else {
            console.warn('[DevTools] Refresh status button not found');
        }

        // Tab switching
        this.configTabs.forEach((tab, index) => {
            const tabHandler = () => {
                const tabName = tab.dataset.tab;
                console.log(`[DevTools] Config tab clicked: ${tabName}`);
                window.notificationManager.showInfo(`Switching to ${tabName} tab...`);
                this.switchConfigTab(tabName);
            };
            tab.addEventListener('click', tabHandler);
            this.cleanupFunctions.push(() => tab.removeEventListener('click', tabHandler));
            console.log(`[DevTools] Config tab ${index + 1} bound`);
        });
        
        console.log('[DevTools] All event handlers bound successfully');
    }

    initializeTabs() {
        // Set first tab as active
        this.switchConfigTab('app-config');
    }

    async loadInitialData() {
        // Load all data sections
        await Promise.all([
            this.loadSystemInfo(),
            this.loadLogs(),
            this.loadAllConfigs(),
            this.loadApplicationStatus()
        ]);
    }

    async loadSystemInfo() {
        console.log('[DevTools] Loading system information...');
        
        // Show loading state
        this.showSystemInfoLoading(true);
        
        try {
            const response = await fetch('/api/system/info');
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            if (data.success) {
                console.log('[DevTools] System info loaded from API:', data.data);
                this.updateSystemInfo(data.data);
                window.notificationManager.showSuccess('System information loaded successfully');
            } else {
                throw new Error(data.error || 'API returned unsuccessful response');
            }
        } catch (error) {
            console.error('[DevTools] Error loading system info:', error);
            window.notificationManager.showError('Failed to load system information from API');
            this.showSystemInfoError();
        } finally {
            this.showSystemInfoLoading(false);
        }
    }
    
    showSystemInfoLoading(isLoading) {
        const loadingElements = document.querySelectorAll('.system-metric .metric-value');
        loadingElements.forEach(el => {
            if (isLoading) {
                el.textContent = '...';
                el.classList.add('loading');
            } else {
                el.classList.remove('loading');
            }
        });
    }
    


    updateSystemInfo(data) {
        // Update CPU
        const cpuPercent = data.cpu_percent || 0;
        this.cpuUsage.textContent = cpuPercent.toFixed(1);
        this.cpuProgress.style.width = `${cpuPercent}%`;
        this.cpuProgress.className = `metric-progress ${this.getMetricClass(cpuPercent)}`;

        // Update Memory
        const memoryPercent = data.memory_percent || 0;
        const memoryUsed = data.memory_used || 0;
        const memoryTotal = data.memory_total || 0;
        this.memoryUsage.textContent = memoryPercent.toFixed(1);
        this.memoryProgress.style.width = `${memoryPercent}%`;
        this.memoryProgress.className = `metric-progress ${this.getMetricClass(memoryPercent)}`;
        this.memoryDetails.textContent = `${(memoryUsed / 1024**3).toFixed(2)} / ${(memoryTotal / 1024**3).toFixed(2)} GB`;

        // Update GPU
        if (data.gpu_percent !== undefined) {
            const gpuPercent = data.gpu_percent;
            this.gpuUsage.textContent = gpuPercent.toFixed(1);
            this.gpuProgress.style.width = `${gpuPercent}%`;
            this.gpuProgress.className = `metric-progress ${this.getMetricClass(gpuPercent)}`;
            this.gpuDetails.textContent = data.gpu_name || 'GPU Available';
        } else {
            this.gpuUsage.textContent = 'N/A';
            this.gpuProgress.style.width = '0%';
            this.gpuDetails.textContent = 'Not available';
        }

        // Update Disk
        const diskPercent = data.disk_percent || 0;
        const diskUsed = data.disk_used || 0;
        const diskTotal = data.disk_total || 0;
        this.diskUsage.textContent = diskPercent.toFixed(1);
        this.diskProgress.style.width = `${diskPercent}%`;
        this.diskProgress.className = `metric-progress ${this.getMetricClass(diskPercent)}`;
        this.diskDetails.textContent = `${(diskUsed / 1024**3).toFixed(2)} / ${(diskTotal / 1024**3).toFixed(2)} GB`;
    }

    getMetricClass(percent) {
        if (percent >= 80) return 'danger';
        if (percent >= 60) return 'warning';
        return '';
    }

    showSystemInfoError() {
        [this.cpuUsage, this.memoryUsage, this.gpuUsage, this.diskUsage].forEach(el => {
            el.textContent = 'Error';
        });
    }

    async loadLogs() {
        console.log('[DevTools] Loading system logs...');
        const lines = parseInt(this.logLinesCount ? this.logLinesCount.value : 100) || 100;
        
        // Show loading state
        this.showLogViewerLoading(true);
        
        try {
            const response = await fetch(`/api/system/logs?lines=${lines}`);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            if (data.success) {
                console.log(`[DevTools] Logs loaded from API: ${data.data.length} entries`);
                this.displayLogs(data.data || []);
                window.notificationManager.showSuccess(`Loaded ${data.data.length} log entries`);
            } else {
                throw new Error(data.error || 'API returned unsuccessful response');
            }
        } catch (error) {
            console.error('[DevTools] Error loading logs:', error);
            window.notificationManager.showError('Failed to load system logs from API');
            this.displayLogs([]);
        } finally {
            this.showLogViewerLoading(false);
        }
    }
    
    showLogViewerLoading(isLoading) {
        if (isLoading) {
            this.logViewer.innerHTML = '<div class="log-loading">Loading logs...</div>';
        }
    }
    


    displayLogs(logs) {
        if (!logs.length) {
            this.logViewer.innerHTML = '<div class="log-loading">No logs available</div>';
            return;
        }

        const logHtml = logs.map(log => {
            const level = (log.level || 'info').toLowerCase();
            return `<div class="log-entry ${level}">
                <span class="log-timestamp">${log.timestamp}</span>
                <span class="log-level">[${log.level}]</span>
                <span class="log-message">${this.escapeHtml(log.message)}</span>
            </div>`;
        }).join('');

        this.logViewer.innerHTML = logHtml;
        this.logViewer.scrollTop = this.logViewer.scrollHeight;
        this.filterLogs();
    }

    filterLogs() {
        const filterLevel = this.logLevelFilter.value;
        const logEntries = this.logViewer.querySelectorAll('.log-entry');
        
        logEntries.forEach(entry => {
            if (!filterLevel || entry.classList.contains(filterLevel.toLowerCase())) {
                entry.style.display = 'block';
            } else {
                entry.style.display = 'none';
            }
        });
    }

    clearLogView() {
        this.logViewer.innerHTML = '<div class="log-loading">Log view cleared</div>';
    }

    toggleAutoRefresh() {
        this.autoRefreshEnabled = !this.autoRefreshEnabled;
        
        if (this.autoRefreshEnabled) {
            this.autoRefreshToggle.textContent = '⏱️ Auto Refresh: ON';
            this.autoRefreshToggle.classList.add('active');
            this.startAutoRefresh();
        } else {
            this.autoRefreshToggle.textContent = '⏱️ Auto Refresh: OFF';
            this.autoRefreshToggle.classList.remove('active');
            this.stopAutoRefresh();
        }
    }

    startAutoRefresh() {
        this.autoRefreshInterval = setInterval(() => {
            this.loadSystemInfo();
            this.loadLogs();
        }, this.logRefreshRate);
    }

    stopAutoRefresh() {
        if (this.autoRefreshInterval) {
            clearInterval(this.autoRefreshInterval);
            this.autoRefreshInterval = null;
        }
    }

    switchConfigTab(tabName) {
        // Update tab buttons
        this.configTabs.forEach(tab => {
            tab.classList.toggle('active', tab.dataset.tab === tabName);
        });

        // Update panels
        this.configPanels.forEach(panel => {
            panel.classList.toggle('active', panel.id === tabName);
        });

        // Load data for the selected tab if needed
        if (tabName === 'app-config') {
            this.loadAppConfig();
        } else if (tabName === 'app-settings') {
            this.loadAppSettings();
        } else if (tabName === 'environment') {
            this.loadEnvironmentInfo();
        }
    }

    async loadAllConfigs() {
        console.log('[DevTools] Loading all configuration data...');
        
        // Show loading state for all config sections
        this.showConfigLoading(true);
        
        try {
            await Promise.all([
                this.loadAppConfig(),
                this.loadAppSettings(),
                this.loadEnvironmentInfo()
            ]);
            
            window.notificationManager.showSuccess('All configuration data loaded');
        } catch (error) {
            console.error('[DevTools] Error loading configurations:', error);
            window.notificationManager.showError('Failed to load some configuration data');
        } finally {
            this.showConfigLoading(false);
        }
    }
    
    showConfigLoading(isLoading) {
        const configContainers = ['app-config', 'app-settings', 'environment'];
        configContainers.forEach(containerId => {
            const container = document.getElementById(containerId);
            if (container) {
                if (isLoading) {
                    container.innerHTML = '<div class="config-loading">Loading configuration...</div>';
                }
            }
        });
    }

    async loadAppConfig() {
        console.log('[DevTools] Loading application configuration...');
        try {
            const response = await fetch('/api/config/app');
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            if (data.success) {
                console.log('[DevTools] App config loaded from API');
                this.displayConfig('app-config', data.data);
            } else {
                throw new Error(data.error || 'API returned unsuccessful response');
            }
        } catch (error) {
            console.error('[DevTools] Error loading app config:', error);
            this.displayConfig('app-config', null);
        }
    }
    


    async loadAppSettings() {
        console.log('[DevTools] Loading application settings...');
        try {
            const response = await fetch('/api/config/settings');
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            if (data.success) {
                console.log('[DevTools] App settings loaded from API');
                this.displayConfig('app-settings', data.data);
            } else {
                throw new Error(data.error || 'API returned unsuccessful response');
            }
        } catch (error) {
            console.error('[DevTools] Error loading app settings:', error);
            this.displayConfig('app-settings', null);
        }
    }
    


    async loadEnvironmentInfo() {
        console.log('[DevTools] Loading environment information...');
        try {
            // For environment info, we can use client-side detection as fallback
            // since this information is available in the browser
            this.displayConfig('environment', this.getClientEnvironmentInfo());
        } catch (error) {
            console.error('[DevTools] Error loading environment info:', error);
            this.displayConfig('environment', null);
        }
    }
    
    getClientEnvironmentInfo() {
        return {
            'platform': navigator.platform,
            'user_agent': navigator.userAgent,
            'screen_resolution': `${screen.width}x${screen.height}`,
            'color_depth': screen.colorDepth,
            'timezone': Intl.DateTimeFormat().resolvedOptions().timeZone,
            'language': navigator.language,
            'online_status': navigator.onLine,
            'cookie_enabled': navigator.cookieEnabled,
            'local_storage_available': typeof(Storage) !== "undefined",
            'webgl_supported': !!window.WebGLRenderingContext,
            'websocket_supported': !!window.WebSocket,
            'service_worker_supported': 'serviceWorker' in navigator,
            'notification_permission': 'Notification' in window ? Notification.permission : 'not-supported'
        };
    }
    


    displayConfig(containerId, configData) {
        const container = document.getElementById(containerId);
        if (!configData) {
            container.innerHTML = '<div class="config-loading">No configuration data available</div>';
            return;
        }

        const configHtml = Object.entries(configData).map(([key, value]) => {
            const isRedacted = key.toLowerCase().includes('secret') || 
                             key.toLowerCase().includes('key') || 
                             key.toLowerCase().includes('password');
            
            const displayValue = isRedacted ? '[REDACTED]' : String(value);
            const valueClass = isRedacted ? 'config-value redacted' : 'config-value';
            
            return `<div class="config-item">
                <div class="config-key">${this.escapeHtml(key)}</div>
                <div class="${valueClass}">${this.escapeHtml(displayValue)}</div>
            </div>`;
        }).join('');

        container.innerHTML = `<div class="config-grid">${configHtml}</div>`;
    }

    async loadApplicationStatus() {
        console.log('[DevTools] Loading application status...');
        
        // Show loading state
        this.showApplicationStatusLoading(true);
        
        try {
            const response = await fetch('/api/system/status');
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            if (data.success) {
                console.log('[DevTools] App status loaded from API:', data.data);
                this.updateApplicationStatus(data.data);
                window.notificationManager.showSuccess('Application status loaded successfully');
            } else {
                throw new Error(data.error || 'API returned unsuccessful response');
            }
        } catch (error) {
            console.error('[DevTools] Error loading app status:', error);
            window.notificationManager.showError('Failed to load application status from API');
            this.showApplicationStatusError();
        } finally {
            this.showApplicationStatusLoading(false);
        }
    }
    
    showApplicationStatusLoading(isLoading) {
        [this.llmStatus, this.databaseStatus, this.ragStatus, this.jobManagerStatus].forEach(element => {
            const dot = element.querySelector('.status-dot');
            const text = element.querySelector('.status-text');
            if (isLoading) {
                dot.className = 'status-dot loading';
                text.textContent = 'Checking...';
            }
        });
    }
    


    updateApplicationStatus(status) {
        this.updateStatusIndicator(this.llmStatus, status.llm_backend);
        this.updateStatusIndicator(this.databaseStatus, status.database);
        this.updateStatusIndicator(this.ragStatus, status.rag);
        this.updateStatusIndicator(this.jobManagerStatus, status.job_manager);
    }

    updateStatusIndicator(element, statusData) {
        const dot = element.querySelector('.status-dot');
        const text = element.querySelector('.status-text');
        
        if (statusData.online) {
            dot.className = 'status-dot online';
            text.textContent = statusData.message || 'Online';
        } else if (statusData.warning) {
            dot.className = 'status-dot warning';
            text.textContent = statusData.message || 'Warning';
        } else {
            dot.className = 'status-dot offline';
            text.textContent = statusData.message || 'Offline';
        }
    }

    showApplicationStatusError() {
        [this.llmStatus, this.databaseStatus, this.ragStatus, this.jobManagerStatus].forEach(element => {
            const dot = element.querySelector('.status-dot');
            const text = element.querySelector('.status-text');
            dot.className = 'status-dot unknown';
            text.textContent = 'Error checking status';
        });
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    // Static initialization method
    static initialize() {
        console.log('[DevTools] Static initialization called');
        if (!window.devToolsManager) {
            window.devToolsManager = new DevToolsManager();
            console.log('[DevTools] Global instance created');
        }
        return window.devToolsManager;
    }
}

// Enhanced initialization with multiple fallbacks
(() => {
    console.log('[DevTools] Module loaded, setting up initialization...');
    
    const initializeManager = () => {
        try {
            if (!window.devToolsManager) {
                window.devToolsManager = new DevToolsManager();
                console.log('[DevTools] Successfully initialized global instance');
                window.notificationManager.showSuccess('DevTools Manager ready');
            }
        } catch (error) {
            console.error('[DevTools] Initialization error:', error);
            window.notificationManager.showError('DevTools Manager initialization failed');
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
            if (!window.devToolsManager) {
                console.log('[DevTools] Fallback initialization on window load');
                initializeManager();
            }
        });
    }
})();
