/**
 * Installation Monitor Manager
 * Manages the display and interaction with AI tool installation status
 */

export class InstallationMonitorManager {
    constructor() {
        this.status = {};
        
        // Cleanup functions for event listeners
        this.cleanupFunctions = [];
        
        this.monitoring = false;
        this.updateInterval = null;
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

    async initialize() {
        console.log('Initializing InstallationMonitorManager...');
        
        // Create status display if it doesn't exist
        this.createStatusDisplay();
        
        // Start monitoring
        await this.startMonitoring();
        
        // Set up event listeners
        this.setupEventListeners();
    }

    createStatusDisplay() {
        // Check if status display already exists
        if (document.getElementById('installation-status-panel')) {
            return;
        }

        const statusPanel = document.createElement('div');
        statusPanel.id = 'installation-status-panel';
        statusPanel.className = 'installation-status-panel';
        statusPanel.innerHTML = `
            <div class="status-header">
                <h3>AI Tools Installation Status</h3>
                <button id="refresh-installation-status" class="btn btn-sm btn-secondary">
                    <i class="fas fa-sync-alt"></i> Refresh
                </button>
            </div>
            <div id="installation-status-content" class="status-content">
                <div class="loading">Loading installation status...</div>
            </div>
            <div class="status-actions">
                <button id="repair-all-installations" class="btn btn-warning">
                    <i class="fas fa-wrench"></i> Repair All Installations
                </button>
                <button id="start-installation-monitor" class="btn btn-info">
                    <i class="fas fa-play"></i> Start Background Monitor
                </button>
            </div>
        `;

        // Insert into page (look for common containers)
        const containers = [
            document.querySelector('.sidebar'),
            document.querySelector('.main-content'),
            document.querySelector('.container'),
            document.body
        ];

        for (const container of containers) {
            if (container) {
                container.appendChild(statusPanel);
                break;
            }
        }

        // Add CSS if not already present
        this.addStyles();
    }

    addStyles() {
        if (document.getElementById('installation-monitor-styles')) {
            return;
        }

        const style = document.createElement('style');
        style.id = 'installation-monitor-styles';
        style.textContent = `
            .installation-status-panel {
                background: var(--card-bg);
                border: 1px solid var(--border-color);
                border-radius: 8px;
                padding: 1rem;
                margin: 1rem 0;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }

            .status-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 1rem;
                padding-bottom: 0.5rem;
                border-bottom: 1px solid var(--border-color);
            }

            .status-header h3 {
                margin: 0;
                color: var(--text-color);
            }

            .status-content {
                margin-bottom: 1rem;
            }

            .installation-item {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 0.75rem;
                margin: 0.5rem 0;
                background: var(--bg-secondary);
                border-radius: 6px;
                border-left: 4px solid var(--border-color);
            }

            .installation-item.healthy {
                border-left-color: #28a745;
            }

            .installation-item.needs-repair {
                border-left-color: #dc3545;
            }

            .installation-item.warning {
                border-left-color: #ffc107;
            }

            .installation-info {
                flex: 1;
            }

            .installation-name {
                font-weight: 600;
                margin-bottom: 0.25rem;
            }

            .installation-status {
                font-size: 0.875rem;
                color: var(--text-muted);
            }

            .installation-actions {
                display: flex;
                gap: 0.5rem;
            }

            .status-actions {
                display: flex;
                gap: 0.5rem;
                flex-wrap: wrap;
            }

            .essential-files {
                font-size: 0.75rem;
                color: var(--text-muted);
                margin-top: 0.25rem;
            }

            .file-status {
                display: inline-block;
                margin-right: 0.5rem;
            }

            .file-status.present {
                color: #28a745;
            }

            .file-status.missing {
                color: #dc3545;
            }
        `;

        document.head.appendChild(style);
    }

    setupEventListeners() {
        // Refresh button
        const refreshBtn = document.getElementById('refresh-installation-status');
        if (refreshBtn) {
            window.eventManager.add(refreshBtn, 'click', () => this.refreshStatus());
        }

        // Repair all button
        const repairBtn = document.getElementById('repair-all-installations');
        if (repairBtn) {
            window.eventManager.add(repairBtn, 'click', () => this.repairAllInstallations());
        }

        // Start monitor button
        const startMonitorBtn = document.getElementById('start-installation-monitor');
        if (startMonitorBtn) {
            window.eventManager.add(startMonitorBtn, 'click', () => this.startBackgroundMonitor());
        }
    }

    async startMonitoring() {
        if (this.monitoring) {
            return;
        }

        this.monitoring = true;
        
        // Initial status check
        await this.refreshStatus();
        
        // Set up periodic updates
        this.updateInterval = setInterval(() => {
            this.refreshStatus();
        }, 30000); // Check every 30 seconds
    }

    stopMonitoring() {
        this.monitoring = false;
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
            this.updateInterval = null;
        }
    }

    async refreshStatus() {
        try {
            const response = await fetch('/api/setup/installation-status');
            const data = await response.json();

            if (data.success) {
                this.status = data.installations;
                this.updateStatusDisplay();
            } else {
                console.error('Failed to get installation status:', data.error);
                this.showError('Failed to get installation status: ' + data.error);
            }
        } catch (error) {
            console.error('Error refreshing installation status:', error);
            this.showError('Error refreshing installation status: ' + error.message);
        }
    }

    updateStatusDisplay() {
        const content = document.getElementById('installation-status-content');
        if (!content) return;

        if (!this.status || Object.keys(this.status).length === 0) {
            content.innerHTML = '<div class="no-data">No installation data available</div>';
            return;
        }

        let html = '';
        
        for (const [toolId, info] of Object.entries(this.status)) {
            const statusClass = this.getStatusClass(info);
            const statusText = this.getStatusText(info);
            
            html += `
                <div class="installation-item ${statusClass}">
                    <div class="installation-info">
                        <div class="installation-name">${info.name}</div>
                        <div class="installation-status">${statusText}</div>
                        ${this.renderEssentialFiles(info)}
                    </div>
                    <div class="installation-actions">
                        ${this.renderActions(toolId, info)}
                    </div>
                </div>
            `;
        }

        content.innerHTML = html;
    }

    getStatusClass(info) {
        if (!info.exists) {
            return 'needs-repair';
        }
        if (info.needs_repair) {
            return 'needs-repair';
        }
        return 'healthy';
    }

    getStatusText(info) {
        if (!info.exists) {
            return 'Not installed';
        }
        if (info.needs_repair) {
            return 'Needs repair';
        }
        return 'Healthy';
    }

    renderEssentialFiles(info) {
        if (!info.essential_files || Object.keys(info.essential_files).length === 0) {
            return '';
        }

        let filesHtml = '<div class="essential-files">';
        for (const [file, present] of Object.entries(info.essential_files)) {
            const statusClass = present ? 'present' : 'missing';
            const icon = present ? '✓' : '✗';
            filesHtml += `<span class="file-status ${statusClass}">${icon} ${file}</span>`;
        }
        filesHtml += '</div>';
        
        return filesHtml;
    }

    renderActions(toolId, info) {
        if (info.needs_repair) {
            return `<button class="btn btn-sm btn-warning" onclick="window.installationMonitor.repairInstallation('${toolId}')">
                <i class="fas fa-wrench"></i> Repair
            </button>`;
        }
        return '';
    }

    async repairAllInstallations() {
        if (!confirm('This will attempt to repair all failed installations. Continue?')) {
            return;
        }

        try {
            const button = document.getElementById('repair-all-installations');
            button.textContent = 'Repairing...';
            button.disabled = true;

            const response = await fetch('/api/setup/repair-installations', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            const data = await response.json();

            if (data.success) {
                this.showSuccess('Installation repair completed');
                await this.refreshStatus();
            } else {
                this.showError('Repair failed: ' + data.error);
            }
        } catch (error) {
            console.error('Error repairing installations:', error);
            this.showError('Error repairing installations: ' + error.message);
        } finally {
            const button = document.getElementById('repair-all-installations');
            button.textContent = 'Repair All Installations';
            button.disabled = false;
        }
    }

    async repairInstallation(toolId) {
        if (!confirm(`Repair ${this.status[toolId]?.name || toolId} installation?`)) {
            return;
        }

        try {
            const response = await fetch('/api/setup/repair-installations', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            const data = await response.json();

            if (data.success) {
                this.showSuccess(`${this.status[toolId]?.name || toolId} repair completed`);
                await this.refreshStatus();
            } else {
                this.showError('Repair failed: ' + data.error);
            }
        } catch (error) {
            console.error('Error repairing installation:', error);
            this.showError('Error repairing installation: ' + error.message);
        }
    }

    async startBackgroundMonitor() {
        try {
            const response = await fetch('/api/setup/start-installation-monitor', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            const data = await response.json();

            if (data.success) {
                this.showSuccess('Background monitor started');
            } else {
                this.showError('Failed to start monitor: ' + data.error);
            }
        } catch (error) {
            console.error('Error starting background monitor:', error);
            this.showError('Error starting background monitor: ' + error.message);
        }
    }

    showSuccess(message) {
        console.log('InstallationMonitor Success:', message);
        // Use existing notification system if available
        if (window.showNotification) {
            window.showNotification(message, 'success');
        } else {
            alert('Success: ' + message);
        }
    }

    showError(message) {
        console.error('InstallationMonitor Error:', message);
        // Use existing notification system if available
        if (window.showNotification) {
            window.showNotification(message, 'error');
        } else {
            alert('Error: ' + message);
        }
    }
}

// Global instance
window.installationMonitor = new InstallationMonitorManager();
