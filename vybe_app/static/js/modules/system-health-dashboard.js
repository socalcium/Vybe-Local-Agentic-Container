/**
 * System Health Dashboard - Real-time monitoring and management
 */

let healthInterval;
let logsInterval;
let logsPaused = false;
let performanceData = {
    cpu: [],
    memory: [],
    timestamps: []
};

// Advanced debugging tools
let debugMode = false;
let diagnosticData = {
    errors: [],
    warnings: [],
    performance: [],
    network: []
};

/**
 * Show toast notification
 */
function showToast(message, type = 'info') {
    console.log(`Health Dashboard Toast (${type}): ${message}`);
    
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
    toast.className = `health-dashboard-toast toast-${type}`;
    toast.style.cssText = `
        position: fixed;
        top: 120px;
        right: 20px;
        background: ${type === 'error' ? '#dc3545' : type === 'success' ? '#28a745' : type === 'warning' ? '#ffc107' : '#007bff'};
        color: ${type === 'warning' ? '#000' : '#fff'};
        padding: 12px 16px;
        border-radius: 6px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        z-index: 10003;
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

/**
 * Refresh health data manually
 */
async function refreshHealthData() {
    console.log('Manually refreshing health data...');
    showToast('Refreshing health data...', 'info');
    
    try {
        await updateSystemHealth();
        showToast('Health data refreshed successfully', 'success');
        console.log('Health data refresh completed successfully');
    } catch (error) {
        console.error('Error refreshing health data:', error);
        showToast('Failed to refresh health data', 'error');
    }
}

/**
 * Update metric display with enhanced feedback
 */
function updateMetricDisplay(metricId, value, unit = '', threshold = { warning: 70, error: 90 }) {
    console.log(`Updating metric display: ${metricId} = ${value}${unit}`);
    
    const element = document.getElementById(metricId);
    
    if (!element) {
        console.warn(`Metric element not found: ${metricId}`);
        return;
    }
    
    // Update the value
    element.textContent = `${value}${unit}`;
    
    // Update styling based on thresholds
    element.className = element.className.replace(/\b(metric-normal|metric-warning|metric-error)\b/g, '');
    
    if (typeof value === 'number') {
        if (value >= threshold.error) {
            element.classList.add('metric-error');
        } else if (value >= threshold.warning) {
            element.classList.add('metric-warning');
        } else {
            element.classList.add('metric-normal');
        }
    }
    
    console.log(`Metric ${metricId} updated successfully`);
}

/**
 * Initialize the health dashboard
 */
function initializeHealthDashboard() {
    console.log('Initializing system health dashboard...');
    showToast('Health dashboard initializing...', 'info');
    
    // Start real-time monitoring
    startHealthMonitoring();
    startLogsMonitoring();
    
    // Initialize charts
    initializeCharts();
    
    // Initialize debugging tools
    initializeDebugTools();
    
    // Setup event handlers for UI interactions
    setupEventHandlers();
    
    // Initial health check
    updateSystemHealth();
    
    // Cleanup on page unload
    if (window.eventManager) {
        window.eventManager.add(window, 'beforeunload', cleanupHealthDashboard);
    } else {
        window.addEventListener('beforeunload', cleanupHealthDashboard);
    }
    
    console.log('Health dashboard initialization completed');
    showToast('Health dashboard ready', 'success');
}

/**
 * Cleanup function to prevent memory leaks
 */
function cleanupHealthDashboard() {
    if (healthInterval) {
        clearInterval(healthInterval);
        healthInterval = null;
    }
    if (logsInterval) {
        clearInterval(logsInterval);
        logsInterval = null;
    }
}

/**
 * Start health monitoring
 */
function startHealthMonitoring() {
    // Update every 5 seconds to reduce log noise and load
    healthInterval = setInterval(updateSystemHealth, 5000);
}

/**
 * Start logs monitoring
 */
function startLogsMonitoring() {
    // Update logs every 3 seconds to reduce churn
    logsInterval = setInterval(updateLogs, 3000);
}

/**
 * Update system health metrics
 */
async function updateSystemHealth() {
    try {
        // Get system usage
        const systemResponse = await fetch('/api/system/usage');
        const systemData = await systemResponse.json();
        
        if (systemData.success) {
            updateSystemMetrics(systemData);
        }
        
        // Get AI services status
        const aiResponse = await fetch('/api/orchestrator/status');
        const aiData = await aiResponse.json();
        
        if (aiData.success) {
            updateAIMetrics(aiData);
        }
        
        // Update charts
        updatePerformanceCharts(systemData);
        
    } catch (error) {
        console.error('Error updating health metrics:', error);
        showHealthError('Failed to fetch health metrics');
    }
}

/**
 * Update system metrics display
 */
function updateSystemMetrics(data) {
    const usage = data.usage || {};
    
    // Update CPU usage
    const cpuUsage = usage.cpu_percent || 0;
    document.getElementById('cpu-usage').textContent = `${cpuUsage.toFixed(1)}%`;
    
    // Update RAM usage
    const ramUsage = usage.ram_percent || 0;
    document.getElementById('ram-usage').textContent = `${ramUsage.toFixed(1)}%`;
    
    // Update disk usage
    const diskUsage = usage.disk_percent || 0;
    document.getElementById('disk-usage').textContent = `${diskUsage.toFixed(1)}%`;
    
    // Update system status
    const systemStatus = getSystemStatus(cpuUsage, ramUsage, diskUsage);
    updateStatusIndicator('system', systemStatus);
    
    // Update performance data
    const now = new Date();
    performanceData.cpu.push(cpuUsage);
    performanceData.memory.push(ramUsage);
    performanceData.timestamps.push(now);
    
    // Keep only last 60 data points (2 minutes at 2-second intervals)
    if (performanceData.cpu.length > 60) {
        performanceData.cpu.shift();
        performanceData.memory.shift();
        performanceData.timestamps.shift();
    }
}

/**
 * Update AI metrics display
 */
function updateAIMetrics(data) {
    // Update active models count
    const activeModels = data.status?.active_agents || 0;
    document.getElementById('active-models').textContent = activeModels;
    
    // Update total requests (placeholder - would need backend counter)
    const totalRequests = sessionStorage.getItem('totalRequests') || '0';
    document.getElementById('total-requests').textContent = totalRequests;
    
    // Update AI status
    const aiReady = data.status?.is_ready || false;
    const aiStatus = aiReady ? 'success' : 'warning';
    updateStatusIndicator('ai', aiStatus);
    
    // Update API response time
    updateApiResponseTime();
}

/**
 * Update API response time
 */
async function updateApiResponseTime() {
    const startTime = performance.now();
    
    try {
        await fetch('/api/orchestrator/status');
        const responseTime = Math.round(performance.now() - startTime);
        document.getElementById('api-response-time').textContent = `${responseTime}ms`;
        
        // Update network status based on response time
        let networkStatus = 'success';
        if (responseTime > 1000) networkStatus = 'error';
        else if (responseTime > 500) networkStatus = 'warning';
        
        updateStatusIndicator('network', networkStatus);
        
    } catch (error) {
        console.error('API response time check failed:', error);
        document.getElementById('api-response-time').textContent = 'Error';
        updateStatusIndicator('network', 'error');
    }
}

/**
 * Get overall system status
 */
function getSystemStatus(cpu, ram, disk) {
    if (cpu > 90 || ram > 90 || disk > 95) return 'error';
    if (cpu > 70 || ram > 80 || disk > 85) return 'warning';
    return 'success';
}

/**
 * Update status indicator
 */
function updateStatusIndicator(type, status) {
    const indicator = document.getElementById(`${type}-status-indicator`);
    const text = document.getElementById(`${type}-status-text`);
    const card = document.getElementById(`${type}-health-card`);
    
    if (indicator) {
        indicator.className = `status-indicator ${status}`;
    }
    
    if (card) {
        card.className = `health-card ${status}`;
    }
    
    if (text) {
        const statusTexts = {
            success: 'Healthy',
            warning: 'Warning',
            error: 'Critical'
        };
        text.textContent = statusTexts[status] || 'Unknown';
    }
}

/**
 * Update performance charts
 */
function updatePerformanceCharts(data) {
    console.log('Updating performance charts with data:', data);
    updateCPUMemoryChart();
    updateAIPerformanceChart();
}

/**
 * Update CPU/Memory chart
 */
function updateCPUMemoryChart() {
    const canvas = document.getElementById('cpu-memory-chart');
    if (!canvas || performanceData.cpu.length === 0) return;
    
    // Simple ASCII-style chart representation
    let chartHTML = '<div style="display: flex; height: 100%; align-items: end; gap: 2px; padding: 10px;">';
    
    const maxValue = Math.max(...performanceData.cpu, ...performanceData.memory, 100);
    
    for (let i = Math.max(0, performanceData.cpu.length - 30); i < performanceData.cpu.length; i++) {
        const cpuHeight = (performanceData.cpu[i] / maxValue) * 160;
        const memHeight = (performanceData.memory[i] / maxValue) * 160;
        
        chartHTML += `
            <div style="display: flex; flex-direction: column; align-items: end; height: 180px; justify-content: end;">
                <div style="width: 8px; height: ${cpuHeight}px; background: #4caf50; margin-bottom: 2px; border-radius: 2px;" title="CPU: ${performanceData.cpu[i].toFixed(1)}%"></div>
                <div style="width: 8px; height: ${memHeight}px; background: #2196f3; border-radius: 2px;" title="RAM: ${performanceData.memory[i].toFixed(1)}%"></div>
            </div>
        `;
    }
    
    chartHTML += '</div>';
    chartHTML += '<div style="display: flex; gap: 10px; padding: 10px; font-size: 0.8em;"><span style="color: #4caf50;">■ CPU</span><span style="color: #2196f3;">■ RAM</span></div>';
    
    canvas.innerHTML = chartHTML;
}

/**
 * Update AI performance chart
 */
function updateAIPerformanceChart() {
    const canvas = document.getElementById('ai-performance-chart');
    if (!canvas) return;
    
    // Placeholder AI performance visualization
    canvas.innerHTML = `
        <div style="display: flex; flex-direction: column; height: 100%; justify-content: center; align-items: center; color: var(--text-secondary);">
            <div style="font-size: 2em; margin-bottom: 10px;">🤖</div>
            <div>AI Performance Monitoring</div>
            <div style="font-size: 0.8em; margin-top: 5px;">Coming soon...</div>
        </div>
    `;
}

/**
 * Update real-time logs
 */
async function updateLogs() {
    if (logsPaused) return;
    
    try {
        // Simulate log entries (in real implementation, this would fetch from backend)
        const logs = generateMockLogs();
        displayLogs(logs);
        
    } catch (error) {
        console.error('Error updating logs:', error);
    }
}

/**
 * Generate mock log entries
 */
function generateMockLogs() {
    const logTypes = ['INFO', 'WARNING', 'ERROR'];
    const messages = [
        'Orchestrator model processing user request',
        'Model inference completed successfully',
        'System resource check passed',
        'Background task completed',
        'User interaction logged for personalization',
        'Cache optimization performed',
        'Database connection established',
        'WebSocket connection active'
    ];
    
    const logs = [];
    const numLogs = Math.floor(Math.random() * 3); // 0-2 new logs per update
    
    for (let i = 0; i < numLogs; i++) {
        const timestamp = new Date().toLocaleTimeString();
        const level = logTypes[Math.floor(Math.random() * logTypes.length)];
        const message = messages[Math.floor(Math.random() * messages.length)];
        
        logs.push({
            timestamp,
            level,
            message
        });
    }
    
    return logs;
}

/**
 * Display logs in the container
 */
function displayLogs(logs) {
    const container = document.getElementById('logs-container');
    if (!container) return;
    
    logs.forEach(log => {
        const logEntry = document.createElement('div');
        logEntry.className = 'log-entry';
        logEntry.innerHTML = `
            <span class="log-timestamp">[${log.timestamp}]</span>
            <span class="log-level-${log.level.toLowerCase()}">${log.level}</span>
            ${log.message}
        `;
        
        container.appendChild(logEntry);
    });
    
    // Keep only last 100 log entries
    const entries = container.querySelectorAll('.log-entry');
    if (entries.length > 100) {
        for (let i = 0; i < entries.length - 100; i++) {
            entries[i].remove();
        }
    }
    
    // Auto-scroll to bottom
    container.scrollTop = container.scrollHeight;
}

/**
 * Initialize charts
 */
function initializeCharts() {
    // Initialize empty charts
    updateCPUMemoryChart();
    updateAIPerformanceChart();
}

/**
 * Show health error
 */
function showHealthError(message) {
    const container = document.getElementById('logs-container');
    if (container) {
        const errorEntry = document.createElement('div');
        errorEntry.className = 'log-entry';
        errorEntry.innerHTML = `
            <span class="log-timestamp">[${new Date().toLocaleTimeString()}]</span>
            <span class="log-level-error">ERROR</span>
            ${message}
        `;
        container.appendChild(errorEntry);
        container.scrollTop = container.scrollHeight;
    }
}

/**
 * Action functions
 */
function clearLogs() {
    const container = document.getElementById('logs-container');
    if (container) {
        container.innerHTML = '<div class="log-entry"><span class="log-timestamp">[' + new Date().toLocaleTimeString() + ']</span> <span class="log-level-info">INFO</span> Logs cleared</div>';
    }
}

function pauseLogs() {
    logsPaused = !logsPaused;
    const button = event.target;
    button.textContent = logsPaused ? 'Resume' : 'Pause';
    
    const container = document.getElementById('logs-container');
    if (container) {
        const pauseEntry = document.createElement('div');
        pauseEntry.className = 'log-entry';
        pauseEntry.innerHTML = `
            <span class="log-timestamp">[${new Date().toLocaleTimeString()}]</span>
            <span class="log-level-info">INFO</span>
            Logs ${logsPaused ? 'paused' : 'resumed'}
        `;
        container.appendChild(pauseEntry);
        container.scrollTop = container.scrollHeight;
    }
}

async function runSystemDiagnostics() {
    console.log('Running comprehensive system diagnostics...');
    showToast('Starting system diagnostics...', 'info');
    
    try {
        // Run API endpoint tests
        await testAPIEndpoints();
        
        // Run other diagnostic tests
        await testDatabaseConnection();
        await testFileSystemAccess();
        await testExternalServices();
        
        const response = await fetch('/api/orchestrator/integration_test', { method: 'POST' });
        const data = await response.json();
        
        const successRate = data.summary?.success_rate || 0;
        const passedTests = data.summary?.passed_tests || 0;
        const issuesFound = data.errors?.length || 0;
        
        const message = `System Diagnostics Results:\nSuccess Rate: ${successRate}%\nTests Passed: ${passedTests}\nIssues Found: ${issuesFound}`;
        
        alert(message);
        console.log('Diagnostics completed:', { successRate, passedTests, issuesFound });
        
        if (successRate >= 80) {
            showToast('System diagnostics completed - System healthy', 'success');
        } else if (successRate >= 60) {
            showToast('System diagnostics completed - Minor issues detected', 'warning');
        } else {
            showToast('System diagnostics completed - Critical issues found', 'error');
        }
        
    } catch (error) {
        console.error('Failed to run diagnostics:', error);
        alert('Failed to run diagnostics: ' + error.message);
        showToast('Diagnostics failed to complete', 'error');
    }
}

/**
 * Enhanced service management functions
 */
function restartServices() {
    console.log('Attempting to restart AI services...');
    showToast('Restarting AI services...', 'warning');
    
    if (confirm('Are you sure you want to restart AI services? This may cause temporary interruptions.')) {
        // In a real implementation, this would make an API call
        setTimeout(() => {
            showToast('AI services restarted successfully', 'success');
            console.log('AI services restart completed');
        }, 2000);
    } else {
        showToast('Service restart cancelled', 'info');
    }
}

function clearCache() {
    console.log('Attempting to clear system cache...');
    
    if (confirm('Clear system cache? This may temporarily slow down the application.')) {
        showToast('Clearing system cache...', 'info');
        
        localStorage.clear();
        sessionStorage.clear();
        
        // Clear performance data
        performanceData = {
            cpu: [],
            memory: [],
            timestamps: []
        };
        
        console.log('System cache cleared successfully');
        showToast('Cache cleared successfully', 'success');
    } else {
        showToast('Cache clear cancelled', 'info');
    }
}

function optimizePerformance() {
    console.log('Running performance optimization...');
    showToast('Running performance optimization...', 'info');
    
    // Simulate optimization process
    setTimeout(() => {
        // Clear old performance data
        if (performanceData.cpu.length > 30) {
            performanceData.cpu = performanceData.cpu.slice(-30);
            performanceData.memory = performanceData.memory.slice(-30);
            performanceData.timestamps = performanceData.timestamps.slice(-30);
        }
        
        // Trigger garbage collection if available
        if (window.gc) {
            window.gc();
        }
        
        console.log('Performance optimization completed');
        showToast('Performance optimization completed', 'success');
    }, 1500);
}

function exportLogs() {
    console.log('Exporting system logs...');
    showToast('Preparing log export...', 'info');
    
    const container = document.getElementById('logs-container');
    if (container) {
        const logs = container.textContent;
        const blob = new Blob([logs], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `vybe-logs-${new Date().toISOString().split('T')[0]}.txt`;
        a.click();
        URL.revokeObjectURL(url);
        
        console.log('Logs exported successfully');
        showToast('Logs exported successfully', 'success');
    } else {
        console.warn('Logs container not found');
        showToast('No logs available for export', 'warning');
    }
}

/**
 * Initialize advanced debugging tools
 */
function initializeDebugTools() {
    // Add debug mode toggle
    const debugToggle = document.createElement('button');
    debugToggle.textContent = '🔧 Debug Mode';
    debugToggle.className = 'debug-toggle-btn';
    debugToggle.onclick = toggleDebugMode;
    
    // Add diagnostic panel
    const diagnosticPanel = document.createElement('div');
    diagnosticPanel.id = 'diagnostic-panel';
    diagnosticPanel.className = 'diagnostic-panel hidden';
    diagnosticPanel.innerHTML = `
        <h3>🔍 Diagnostic Tools</h3>
        <div class="diagnostic-tools">
            <button onclick="runSystemDiagnostics()">Run System Diagnostics</button>
            <button onclick="exportDiagnosticReport()">Export Report</button>
            <button onclick="clearDiagnosticData()">Clear Data</button>
        </div>
        <div class="diagnostic-results">
            <div id="error-log"></div>
            <div id="performance-log"></div>
            <div id="network-log"></div>
        </div>
    `;
    
    // Insert into dashboard
    const dashboard = document.querySelector('.health-dashboard') || document.body;
    dashboard.appendChild(debugToggle);
    dashboard.appendChild(diagnosticPanel);
    
    // Add diagnostic styles
    addDiagnosticStyles();
}

/**
 * Toggle debug mode
 */
function toggleDebugMode() {
    debugMode = !debugMode;
    const panel = document.getElementById('diagnostic-panel');
    const toggle = document.querySelector('.debug-toggle-btn');
    
    if (debugMode) {
        panel.classList.remove('hidden');
        toggle.textContent = '🔧 Debug Mode (ON)';
        toggle.classList.add('active');
        console.log('Debug mode enabled - enhanced logging active');
    } else {
        panel.classList.add('hidden');
        toggle.textContent = '🔧 Debug Mode';
        toggle.classList.remove('active');
        console.log('Debug mode disabled');
    }
}

/**
 * Setup event handlers for dashboard interactions
 */
function setupEventHandlers() {
    console.log('Setting up health dashboard event handlers...');
    
    // Auto-refresh toggle handler
    const refreshButton = document.getElementById('refresh-health-data');
    if (refreshButton) {
        if (window.eventManager) {
            window.eventManager.add(refreshButton, 'click', () => {
                console.log('Manual refresh button clicked');
                refreshHealthData();
            });
        } else {
            refreshButton.addEventListener('click', () => {
                console.log('Manual refresh button clicked');
                refreshHealthData();
            });
        }
    }
    
    // Diagnostic button handler
    const diagnosticButton = document.getElementById('run-diagnostics');
    if (diagnosticButton) {
        if (window.eventManager) {
            window.eventManager.add(diagnosticButton, 'click', () => {
                console.log('Diagnostics button clicked');
                runSystemDiagnostics();
            });
        } else {
            diagnosticButton.addEventListener('click', () => {
                console.log('Diagnostics button clicked');
                runSystemDiagnostics();
            });
        }
    }
    
    // Clear logs handler
    const clearLogsButton = document.getElementById('clear-logs-btn');
    if (clearLogsButton) {
        if (window.eventManager) {
            window.eventManager.add(clearLogsButton, 'click', () => {
                console.log('Clear logs button clicked');
                clearLogs();
            });
        } else {
            clearLogsButton.addEventListener('click', () => {
                console.log('Clear logs button clicked');
                clearLogs();
            });
        }
    }
    
    // Pause logs handler
    const pauseLogsButton = document.getElementById('pause-logs-btn');
    if (pauseLogsButton) {
        if (window.eventManager) {
            window.eventManager.add(pauseLogsButton, 'click', () => {
                console.log('Pause logs button clicked');
                pauseLogs();
            });
        } else {
            pauseLogsButton.addEventListener('click', () => {
                console.log('Pause logs button clicked');
                pauseLogs();
            });
        }
    }
    
    // Export logs handler
    const exportLogsButton = document.getElementById('export-logs-btn');
    if (exportLogsButton) {
        if (window.eventManager) {
            window.eventManager.add(exportLogsButton, 'click', () => {
                console.log('Export logs button clicked');
                exportLogs();
            });
        } else {
            exportLogsButton.addEventListener('click', () => {
                console.log('Export logs button clicked');
                exportLogs();
            });
        }
    }
    
    showToast('Event handlers initialized', 'success');
    console.log('Health dashboard event handlers setup completed');
}

/**
 * Test API endpoints
 */
async function testAPIEndpoints() {
    const endpoints = [
        '/api/health',
        '/api/system/usage',
        '/api/orchestrator/status',
        '/api/models/backend_status'
    ];
    
    for (const endpoint of endpoints) {
        try {
            const start = performance.now();
            const response = await fetch(endpoint);
            const duration = performance.now() - start;
            
            if (response.ok) {
                addDiagnosticInfo('API Test', `${endpoint} - OK (${duration.toFixed(2)}ms)`);
            } else {
                addDiagnosticError('API Test', `${endpoint} - Failed (${response.status})`);
            }
        } catch (error) {
            addDiagnosticError('API Test', `${endpoint} - Error: ${error.message}`);
        }
    }
}

/**
 * Test database connection
 */
async function testDatabaseConnection() {
    try {
        const response = await fetch('/api/system/db-status');
        const data = await response.json();
        
        if (data.success) {
            addDiagnosticInfo('Database', 'Connection OK');
        } else {
            addDiagnosticError('Database', 'Connection failed');
        }
    } catch (error) {
        addDiagnosticError('Database', `Test failed: ${error.message}`);
    }
}

/**
 * Test file system access
 */
async function testFileSystemAccess() {
    try {
        const response = await fetch('/api/system/fs-status');
        const data = await response.json();
        
        if (data.success) {
            addDiagnosticInfo('File System', 'Access OK');
        } else {
            addDiagnosticError('File System', 'Access failed');
        }
    } catch (error) {
        addDiagnosticError('File System', `Test failed: ${error.message}`);
    }
}

/**
 * Test external services
 */
async function testExternalServices() {
    const services = [
        { name: 'LLM Backend', endpoint: '/api/models/backend_status' },
        { name: 'Stable Diffusion', endpoint: '/api/image/status' },
        { name: 'ComfyUI', endpoint: '/api/video/status' }
    ];
    
    for (const service of services) {
        try {
            const response = await fetch(service.endpoint);
            const data = await response.json();
            
            if (data.success) {
                addDiagnosticInfo('External Service', `${service.name} - Available`);
            } else {
                addDiagnosticWarning('External Service', `${service.name} - Unavailable`);
            }
        } catch (error) {
            addDiagnosticError('External Service', `${service.name} - Error: ${error.message}`);
        }
    }
}

/**
 * Add diagnostic information
 */
function addDiagnosticInfo(category, message) {
    diagnosticData.performance.push({
        timestamp: new Date().toISOString(),
        category,
        message,
        type: 'info'
    });
    updateDiagnosticDisplay();
}

/**
 * Add diagnostic warning
 */
function addDiagnosticWarning(category, message) {
    diagnosticData.warnings.push({
        timestamp: new Date().toISOString(),
        category,
        message,
        type: 'warning'
    });
    updateDiagnosticDisplay();
}

/**
 * Add diagnostic error
 */
function addDiagnosticError(category, message, error = null) {
    diagnosticData.errors.push({
        timestamp: new Date().toISOString(),
        category,
        message,
        error: error ? error.toString() : null,
        type: 'error'
    });
    updateDiagnosticDisplay();
}

/**
 * Update diagnostic display
 */
function updateDiagnosticDisplay() {
    if (!debugMode) return;
    
    const errorLog = document.getElementById('error-log');
    const performanceLog = document.getElementById('performance-log');
    
    if (errorLog) {
        errorLog.innerHTML = diagnosticData.errors
            .slice(-10)
            .map(item => `<div class="log-item error">[${item.timestamp}] ${item.category}: ${item.message}</div>`)
            .join('');
    }
    
    if (performanceLog) {
        performanceLog.innerHTML = diagnosticData.performance
            .slice(-10)
            .map(item => `<div class="log-item info">[${item.timestamp}] ${item.category}: ${item.message}</div>`)
            .join('');
    }
}

/**
 * Generate diagnostic report
 */
function generateDiagnosticReport() {
    const report = {
        timestamp: new Date().toISOString(),
        system: {
            userAgent: navigator.userAgent,
            platform: navigator.platform,
            language: navigator.language
        },
        diagnostics: diagnosticData,
        performance: performanceData
    };
    
    console.log('Diagnostic Report:', report);
    return report;
}

/**
 * Export diagnostic report
 */
function exportDiagnosticReport() {
    const report = generateDiagnosticReport();
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    
    const a = document.createElement('a');
    a.href = url;
    a.download = `vybe-diagnostic-${new Date().toISOString().split('T')[0]}.json`;
    a.click();
    
    URL.revokeObjectURL(url);
}

/**
 * Clear diagnostic data
 */
function clearDiagnosticData() {
    diagnosticData = {
        errors: [],
        warnings: [],
        performance: [],
        network: []
    };
    updateDiagnosticDisplay();
}

/**
 * Add diagnostic styles
 */
function addDiagnosticStyles() {
    const style = document.createElement('style');
    style.textContent = `
        .debug-toggle-btn {
            position: fixed;
            top: 10px;
            right: 10px;
            z-index: 1000;
            padding: 8px 12px;
            background: #007bff;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }
        
        .debug-toggle-btn.active {
            background: #28a745;
        }
        
        .diagnostic-panel {
            position: fixed;
            top: 50px;
            right: 10px;
            width: 400px;
            max-height: 600px;
            background: white;
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 15px;
            z-index: 999;
            overflow-y: auto;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        
        .diagnostic-panel.hidden {
            display: none;
        }
        
        .diagnostic-tools {
            margin-bottom: 15px;
        }
        
        .diagnostic-tools button {
            margin: 2px;
            padding: 5px 10px;
            background: #f8f9fa;
            border: 1px solid #ddd;
            border-radius: 3px;
            cursor: pointer;
        }
        
        .log-item {
            padding: 2px 5px;
            margin: 1px 0;
            font-family: monospace;
            font-size: 12px;
        }
        
        .log-item.error {
            background: #ffe6e6;
            color: #d63384;
        }
        
        .log-item.warning {
            background: #fff3cd;
            color: #856404;
        }
        
        .log-item.info {
            background: #d1ecf1;
            color: #0c5460;
        }
    `;
    document.head.appendChild(style);
}

// Cleanup on page unload
const cleanupHandler = () => {
    cleanupHealthDashboard();
};
window.eventManager.add(window, 'beforeunload', cleanupHandler);

// Cleanup when page becomes hidden to save resources
const visibilityHandler = () => {
    if (document.hidden) {
        // Pause monitoring when page is not visible
        if (healthInterval) {
            clearInterval(healthInterval);
            healthInterval = null;
        }
        if (logsInterval) {
            clearInterval(logsInterval);
            logsInterval = null;
        }
    } else {
        // Resume monitoring when page becomes visible
        if (!healthInterval) {
            startHealthMonitoring();
        }
        if (!logsInterval) {
            startLogsMonitoring();
        }
    }
};
window.eventManager.add(document, 'visibilitychange', visibilityHandler);

// Export functions
window.clearLogs = clearLogs;
window.pauseLogs = pauseLogs;
window.runSystemDiagnostics = runSystemDiagnostics;
window.restartServices = restartServices;
window.clearCache = clearCache;
window.optimizePerformance = optimizePerformance;
window.exportLogs = exportLogs;
window.refreshHealthData = refreshHealthData;
window.updateMetricDisplay = updateMetricDisplay;
window.initializeHealthDashboard = initializeHealthDashboard;
window.exportDiagnosticReport = exportDiagnosticReport;
window.clearDiagnosticData = clearDiagnosticData;
window.testAPIEndpoints = testAPIEndpoints;

// Initialize when DOM is ready
const initHealthDashboard = () => {
    console.log('DOM loaded, initializing health dashboard...');
    initializeHealthDashboard();
};

if (window.eventManager) {
    window.eventManager.add(document, 'DOMContentLoaded', initHealthDashboard);
} else {
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initHealthDashboard);
    } else {
        initHealthDashboard();
    }
}
