/**
 * Cloud Sync Manager
 * Provides frontend interface for managing cloud synchronization
 */

// Import the centralized notification manager (attaches to window.notificationManager)
import './services/NotificationManager.js';

// Safety check for Bootstrap
if (typeof window.bootstrap === 'undefined' || !window.bootstrap?.Modal) {
    console.warn('Bootstrap is not defined. Using placeholder for modals.');
    window.bootstrap = {
        Modal: class {
            constructor(element) { this.element = element; console.log('Placeholder Modal created for:', this.element); }
            show() { console.log('Placeholder Modal show().'); }
            hide() { console.log('Placeholder Modal hide().'); }
        }
    };
}

class CloudSyncManager {
    constructor() {
        this.providers = {};
        this.syncConfigs = {};
        this.syncHistory = [];
        this.currentProvider = null;
        this.isInitialized = false;
        
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
    
    async init() {
        try {
            await this.loadProviders();
            await this.loadSyncStatus();
            await this.loadSyncHistory();
            this.bindEvents();
            this.isInitialized = true;
            console.log('Cloud Sync Manager initialized');
        } catch (error) {
            console.error('Failed to initialize Cloud Sync Manager:', error);
            window.notificationManager.showError('Failed to initialize Cloud Sync Manager. Please refresh the page and try again.');
        }
    }
    
    async loadProviders() {
        try {
            // Show loading state
            const container = document.getElementById('providersContainer');
            if (container) {
                container.innerHTML = '<div class="text-center"><i class="bi bi-arrow-repeat spinner-border me-2"></i>Loading providers...</div>';
            }
            
            const response = await fetch('/api/cloud_sync/providers');
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.success) {
                this.providers = data.providers || {};
                this.renderProviders();
            } else {
                throw new Error(data.error || 'Failed to load providers');
            }
        } catch (error) {
            console.error('Error loading providers:', error);
            this.showNotification('Failed to load cloud providers. Please check your connection and try again.', 'error');
            
            // Show error state in container
            const container = document.getElementById('providersContainer');
            if (container) {
                container.innerHTML = `
                    <div class="alert alert-danger">
                        <i class="bi bi-exclamation-triangle me-2"></i>
                        Failed to load providers. Please refresh to try again.
                    </div>
                `;
            }
        }
    }
    
    async loadSyncStatus() {
        try {
            const response = await fetch('/api/cloud_sync/status');
            const data = await response.json();
            
            if (data.success) {
                this.syncConfigs = data.status;
                this.renderSyncStatus();
            }
        } catch (error) {
            console.error('Error loading sync status:', error);
            window.notificationManager.showError('Failed to load sync status. Please refresh and try again.');
        }
    }
    
    async loadSyncHistory(limit = 20) {
        try {
            const response = await fetch(`/api/cloud_sync/history?limit=${limit}`);
            const data = await response.json();
            
            if (data.success) {
                this.syncHistory = data.history;
                this.renderSyncHistory();
            }
        } catch (error) {
            console.error('Error loading sync history:', error);
            window.notificationManager.showError('Failed to load sync history. Please refresh and try again.');
        }
    }
    
    bindEvents() {
        // Provider selection
        window.eventManager.add(document, 'click', (e) => {
            if (e.target.matches('.provider-card')) {
                this.selectProvider(e.target.dataset.provider);
            }
            
            if (e.target.matches('.add-provider-btn')) {
                this.showAddProviderModal();
            }
            
            if (e.target.matches('.sync-now-btn')) {
                this.syncNow();
            }
            
            if (e.target.matches('.remove-provider-btn')) {
                this.removeProvider(e.target.dataset.provider);
            }
            
            if (e.target.matches('.test-connection-btn')) {
                this.testConnection(e.target.dataset.provider);
            }
            
            if (e.target.matches('.browse-files-btn')) {
                this.browseFiles(e.target.dataset.provider);
            }
        });
        
        // Modal events
        window.eventManager.add(document, 'click', (e) => {
            if (e.target.matches('.modal-close') || e.target.matches('.modal-backdrop')) {
                this.closeModals();
            }
        });
        
        // Form submissions
        window.eventManager.add(document, 'submit', (e) => {
            if (e.target.matches('#addProviderForm')) {
                e.preventDefault();
                this.addProvider();
            }
            
            if (e.target.matches('#syncSettingsForm')) {
                e.preventDefault();
                this.updateSyncSettings();
            }
        });
    }
    
    renderProviders() {
        const container = document.getElementById('providersContainer');
        if (!container) return;
        
        container.innerHTML = '';
        
        Object.entries(this.providers).forEach(([key, provider]) => {
            const card = this.createProviderCard(key, provider);
            container.appendChild(card);
        });
        
        // Add "Add Provider" card
        const addCard = this.createAddProviderCard();
        container.appendChild(addCard);
    }
    
    createProviderCard(key, provider) {
        const card = document.createElement('div');
        card.className = 'provider-card';
        card.dataset.provider = key;
        
        const isConfigured = key in this.syncConfigs;
        const status = isConfigured ? 'configured' : 'not-configured';
        
        card.innerHTML = `
            <div class="card ${status}">
                <div class="card-body">
                    <div class="d-flex align-items-center mb-3">
                        <i class="${provider.icon} fs-2 me-3"></i>
                        <div>
                            <h5 class="card-title mb-1">${provider.name}</h5>
                            <p class="card-text text-muted mb-0">${provider.description}</p>
                        </div>
                    </div>
                    
                    <div class="provider-status mb-3">
                        <span class="badge bg-${isConfigured ? 'success' : 'secondary'}">
                            ${isConfigured ? 'Configured' : 'Not Configured'}
                        </span>
                        ${provider.available ? '' : '<span class="badge bg-warning ms-2">Not Available</span>'}
                    </div>
                    
                    <div class="provider-features mb-3">
                        ${provider.features.map(feature => 
                            `<span class="badge bg-info me-1">${feature}</span>`
                        ).join('')}
                    </div>
                    
                    <div class="provider-actions">
                        ${isConfigured ? `
                            <button class="btn btn-primary btn-sm sync-now-btn me-2" data-provider="${key}">
                                <i class="bi bi-arrow-repeat"></i> Sync Now
                            </button>
                            <button class="btn btn-info btn-sm test-connection-btn me-2" data-provider="${key}">
                                <i class="bi bi-wifi"></i> Test Connection
                            </button>
                            <button class="btn btn-secondary btn-sm browse-files-btn me-2" data-provider="${key}">
                                <i class="bi bi-folder"></i> Browse Files
                            </button>
                            <button class="btn btn-danger btn-sm remove-provider-btn" data-provider="${key}">
                                <i class="bi bi-trash"></i> Remove
                            </button>
                        ` : `
                            <button class="btn btn-success btn-sm configure-provider-btn" data-provider="${key}">
                                <i class="bi bi-gear"></i> Configure
                            </button>
                        `}
                    </div>
                </div>
            </div>
        `;
        
        return card;
    }
    
    createAddProviderCard() {
        const card = document.createElement('div');
        card.className = 'add-provider-card';
        
        card.innerHTML = `
            <div class="card add-provider">
                <div class="card-body d-flex align-items-center justify-content-center" style="min-height: 200px;">
                    <button class="btn btn-outline-primary add-provider-btn">
                        <i class="bi bi-plus-circle fs-1 d-block mb-2"></i>
                        Add Cloud Provider
                    </button>
                </div>
            </div>
        `;
        
        return card;
    }
    
    renderSyncStatus() {
        const container = document.getElementById('syncStatusContainer');
        if (!container) return;
        
        container.innerHTML = '';
        
        if (Object.keys(this.syncConfigs).length === 0) {
            container.innerHTML = `
                <div class="alert alert-info">
                    <i class="bi bi-info-circle"></i>
                    No cloud providers configured. Add a provider to start syncing your files.
                </div>
            `;
            return;
        }
        
        Object.entries(this.syncConfigs).forEach(([provider, config]) => {
            const statusCard = this.createSyncStatusCard(provider, config);
            container.appendChild(statusCard);
        });
    }
    
    createSyncStatusCard(provider, config) {
        const card = document.createElement('div');
        card.className = 'sync-status-card mb-3';
        
        const lastSync = config.last_sync ? new Date(config.last_sync).toLocaleString() : 'Never';
        
        card.innerHTML = `
            <div class="card">
                <div class="card-header d-flex justify-content-between align-items-center">
                    <h6 class="mb-0">
                        <i class="bi bi-cloud"></i>
                        ${provider.charAt(0).toUpperCase() + provider.slice(1)} Sync Status
                    </h6>
                    <span class="badge bg-${config.status === 'connected' ? 'success' : 'warning'}">
                        ${config.status}
                    </span>
                </div>
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-6">
                            <p><strong>Auto Sync:</strong> ${config.auto_sync ? 'Enabled' : 'Disabled'}</p>
                            <p><strong>Sync Interval:</strong> ${config.sync_interval} seconds</p>
                            <p><strong>Items:</strong> ${config.items_count}</p>
                        </div>
                        <div class="col-md-6">
                            <p><strong>Last Sync:</strong> ${lastSync}</p>
                            <p><strong>Status:</strong> ${config.status}</p>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        return card;
    }
    
    renderSyncHistory() {
        const container = document.getElementById('syncHistoryContainer');
        if (!container) return;
        
        container.innerHTML = '';
        
        if (this.syncHistory.length === 0) {
            container.innerHTML = `
                <div class="alert alert-info">
                    <i class="bi bi-info-circle"></i>
                    No sync history available.
                </div>
            `;
            return;
        }
        
        const table = document.createElement('table');
        table.className = 'table table-striped';
        
        table.innerHTML = `
            <thead>
                <tr>
                    <th>Provider</th>
                    <th>Started</th>
                    <th>Completed</th>
                    <th>Items Processed</th>
                    <th>Success</th>
                    <th>Failed</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
                ${this.syncHistory.map(item => `
                    <tr>
                        <td>${item.provider}</td>
                        <td>${new Date(item.started_at).toLocaleString()}</td>
                        <td>${item.completed_at ? new Date(item.completed_at).toLocaleString() : '-'}</td>
                        <td>${item.items_processed}</td>
                        <td><span class="badge bg-success">${item.items_succeeded}</span></td>
                        <td><span class="badge bg-danger">${item.items_failed}</span></td>
                        <td>
                            <span class="badge bg-${item.items_failed === 0 ? 'success' : 'warning'}">
                                ${item.items_failed === 0 ? 'Success' : 'Partial'}
                            </span>
                        </td>
                    </tr>
                `).join('')}
            </tbody>
        `;
        
        container.appendChild(table);
    }
    
    selectProvider(provider) {
        this.currentProvider = provider;
        this.showProviderDetails(provider);
    }
    
    showProviderDetails(provider) {
        // Implementation for showing detailed provider information
        console.log('Showing details for provider:', provider);
    }
    
    showAddProviderModal() {
        const modal = document.createElement('div');
        modal.className = 'modal fade';
        modal.id = 'addProviderModal';
        
        modal.innerHTML = `
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">Add Cloud Provider</h5>
                        <button type="button" class="btn-close modal-close"></button>
                    </div>
                    <div class="modal-body">
                        <form id="addProviderForm">
                            <div class="mb-3">
                                <label for="providerSelect" class="form-label">Provider</label>
                                <select class="form-select" id="providerSelect" required>
                                    <option value="">Select a provider...</option>
                                    ${Object.entries(this.providers).map(([key, provider]) => 
                                        `<option value="${key}">${provider.name}</option>`
                                    ).join('')}
                                </select>
                            </div>
                            
                            <div class="mb-3">
                                <label for="localPath" class="form-label">Local Path</label>
                                <input type="text" class="form-control" id="localPath" 
                                       placeholder="/path/to/local/folder" required>
                            </div>
                            
                            <div class="mb-3">
                                <label for="remotePath" class="form-label">Remote Path</label>
                                <input type="text" class="form-control" id="remotePath" 
                                       placeholder="/remote/folder" required>
                            </div>
                            
                            <div class="mb-3">
                                <label for="syncDirection" class="form-label">Sync Direction</label>
                                <select class="form-select" id="syncDirection">
                                    <option value="bidirectional">Bidirectional</option>
                                    <option value="upload">Upload Only</option>
                                    <option value="download">Download Only</option>
                                </select>
                            </div>
                            
                            <div class="mb-3">
                                <label for="syncInterval" class="form-label">Sync Interval (minutes)</label>
                                <input type="number" class="form-control" id="syncInterval" 
                                       value="5" min="1" max="1440">
                            </div>
                            
                            <div class="form-check mb-3">
                                <input class="form-check-input" type="checkbox" id="autoSync" checked>
                                <label class="form-check-label" for="autoSync">
                                    Enable automatic sync
                                </label>
                            </div>
                            
                            <div class="form-check mb-3">
                                <input class="form-check-input" type="checkbox" id="encryption" checked>
                                <label class="form-check-label" for="encryption">
                                    Enable encryption
                                </label>
                            </div>
                            
                            <div class="form-check mb-3">
                                <input class="form-check-input" type="checkbox" id="compression" checked>
                                <label class="form-check-label" for="compression">
                                    Enable compression
                                </label>
                            </div>
                        </form>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary modal-close">Cancel</button>
                        <button type="submit" form="addProviderForm" class="btn btn-primary">Add Provider</button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        // Initialize Bootstrap modal
        const bootstrapModal = new window.bootstrap.Modal(modal);
        bootstrapModal.show();
        
        // Clean up when modal is hidden
        window.eventManager.add(modal, 'hidden.bs.modal', () => {
            modal.remove();
        });
    }
    
    async addProvider() {
        // Get form elements and submit button for UI state management
        const submitButton = document.querySelector('#addProviderForm button[type="submit"]');
        const originalButtonText = submitButton ? submitButton.innerHTML : '';
        
        try {
            // Show loading state
            if (submitButton) {
                submitButton.disabled = true;
                submitButton.innerHTML = '<i class="bi bi-arrow-repeat spinner-border spinner-border-sm me-2"></i>Adding Provider...';
            }
            
            const provider = document.getElementById('providerSelect').value;
            
            const syncItem = {
                local_path: document.getElementById('localPath').value,
                remote_path: document.getElementById('remotePath').value,
                direction: document.getElementById('syncDirection').value
            };
            
            const config = {
                provider: provider,
                credentials: {}, // Will be filled during OAuth
                sync_items: [syncItem],
                auto_sync: document.getElementById('autoSync').checked,
                sync_interval: parseInt(document.getElementById('syncInterval').value) * 60,
                encryption_enabled: document.getElementById('encryption').checked,
                compression_enabled: document.getElementById('compression').checked
            };
            
            const response = await fetch('/api/cloud_sync/providers', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(config)
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.success) {
                this.showNotification('Provider added successfully', 'success');
                await this.loadSyncStatus();
                this.renderProviders(); // Refresh provider list
                this.closeModals();
            } else {
                this.showNotification('Failed to add provider: ' + (data.error || 'Unknown error'), 'error');
            }
        } catch (error) {
            console.error('Error adding provider:', error);
            this.showNotification('Failed to add provider. Please check your credentials and try again.', 'error');
        } finally {
            // Restore button state
            if (submitButton) {
                submitButton.disabled = false;
                submitButton.innerHTML = originalButtonText;
            }
        }
    }
    
    async syncNow(provider = null) {
        console.log('Starting sync operation for provider:', provider);
        
        // Get sync button for UI state management
        const syncButton = document.querySelector(`[data-provider="${provider}"] .sync-now-btn`);
        const originalButtonText = syncButton ? syncButton.innerHTML : '';
        
        try {
            // Show loading state on button
            if (syncButton) {
                syncButton.disabled = true;
                syncButton.innerHTML = '<i class="bi bi-arrow-repeat spinner-border spinner-border-sm me-2"></i>Syncing...';
            }
            
            // Show progress notification
            this.showNotification('Starting sync operation...', 'info');
            
            const requestBody = { provider: provider };
            
            // If no specific provider, sync all configured providers
            if (!provider && Object.keys(this.syncConfigs).length > 0) {
                requestBody.provider = 'all';
            }
            
            // Use the specific provider endpoint if provider is specified
            const endpoint = provider && provider !== 'all' 
                ? `/api/cloud_sync/sync/${provider}`
                : '/api/cloud_sync/sync';
                
            const response = await fetch(endpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestBody)
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.success) {
                const syncDetails = data.details || {};
                const message = `Sync completed successfully! ${syncDetails.files_synced || 0} files synced.`;
                console.log('Sync completed successfully:', syncDetails);
                
                this.showNotification(message, 'success');
                
                // Refresh UI data
                await this.loadSyncHistory();
                await this.loadSyncStatus();
                
                // Update last sync time in UI
                this.updateLastSyncDisplay(provider, new Date());
                
            } else {
                console.error('Sync failed:', data.error);
                this.showNotification('Sync failed: ' + (data.error || 'Unknown error'), 'error');
            }
        } catch (error) {
            console.error('Error during sync operation:', error);
            this.showNotification('Sync operation failed. Please check your connection and try again.', 'error');
        } finally {
            // Restore button state
            if (syncButton) {
                syncButton.disabled = false;
                syncButton.innerHTML = originalButtonText;
            }
        }
    }
    
    async removeProvider(provider) {
        if (!confirm(`Are you sure you want to remove ${provider}?`)) {
            return;
        }
        
        try {
            const response = await fetch('/api/cloud_sync/config/remove', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ provider: provider })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showNotification('Provider removed successfully', 'success');
                await this.loadSyncStatus();
                this.renderProviders();
            } else {
                this.showNotification('Failed to remove provider: ' + data.error, 'error');
            }
        } catch (error) {
            console.error('Error removing provider:', error);
            this.showNotification('Failed to remove provider. Please try again.', 'error');
        }
    }
    
    async testConnection(provider) {
        console.log('Testing connection for provider:', provider);
        
        // Get test button for UI state management
        const testButton = document.querySelector(`[data-provider="${provider}"] .test-connection-btn`);
        const originalButtonText = testButton ? testButton.innerHTML : '';
        
        try {
            // Show loading state on button
            if (testButton) {
                testButton.disabled = true;
                testButton.innerHTML = '<i class="bi bi-arrow-repeat spinner-border spinner-border-sm me-2"></i>Testing...';
            }
            
            // Show progress notification
            this.showNotification('Testing connection...', 'info');
            
            const response = await fetch(`/api/cloud_sync/test/${provider}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ 
                    credentials: this.syncConfigs[provider]?.credentials || {}
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.success) {
                const details = data.details || {};
                
                if (data.connection_successful) {
                    const message = `✓ Connection to ${provider} successful! ${details.info || ''}`;
                    console.log('Connection test passed:', details);
                    this.showNotification(message, 'success');
                    
                    // Update connection status in UI
                    this.updateConnectionStatus(provider, 'connected');
                    
                } else {
                    const message = `✗ Connection to ${provider} failed. ${details.error || 'Please check your credentials.'}`;
                    console.error('Connection test failed:', details);
                    this.showNotification(message, 'error');
                    
                    // Update connection status in UI
                    this.updateConnectionStatus(provider, 'failed');
                }
            } else {
                console.error('Connection test error:', data.error);
                this.showNotification('Connection test failed: ' + (data.error || 'Unknown error'), 'error');
                this.updateConnectionStatus(provider, 'error');
            }
        } catch (error) {
            console.error('Error testing connection:', error);
            this.showNotification('Connection test failed. Please check your credentials and try again.', 'error');
            this.updateConnectionStatus(provider, 'error');
        } finally {
            // Restore button state
            if (testButton) {
                testButton.disabled = false;
                testButton.innerHTML = originalButtonText;
            }
        }
    }
    
    async browseFiles(provider) {
        try {
            const response = await fetch('/api/cloud_sync/browse', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ 
                    provider: provider,
                    path: '/'
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showFileBrowser(data.files, provider);
            } else {
                this.showNotification('Failed to browse files: ' + data.error, 'error');
            }
        } catch (error) {
            console.error('Error browsing files:', error);
            this.showNotification('Failed to browse files. Please check your connection and try again.', 'error');
        }
    }
    
    showFileBrowser(files, provider) {
        const modal = document.createElement('div');
        modal.className = 'modal fade';
        modal.id = 'fileBrowserModal';
        
        modal.innerHTML = `
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">${provider} Files</h5>
                        <button type="button" class="btn-close modal-close"></button>
                    </div>
                    <div class="modal-body">
                        <div class="table-responsive">
                            <table class="table table-striped">
                                <thead>
                                    <tr>
                                        <th>Name</th>
                                        <th>Type</th>
                                        <th>Size</th>
                                        <th>Modified</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${files.map(file => `
                                        <tr>
                                            <td>
                                                <i class="bi bi-${file.type === 'folder' ? 'folder' : 'file'}"></i>
                                                ${file.name}
                                            </td>
                                            <td>${file.type}</td>
                                            <td>${file.size ? this.formatFileSize(file.size) : '-'}</td>
                                            <td>${new Date(file.modified).toLocaleString()}</td>
                                        </tr>
                                    `).join('')}
                                </tbody>
                            </table>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary modal-close">Close</button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        const bootstrapModal = new window.bootstrap.Modal(modal);
        bootstrapModal.show();
        
        window.eventManager.add(modal, 'hidden.bs.modal', () => {
            modal.remove();
        });
    }
    
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
    
    closeModals() {
        const modals = document.querySelectorAll('.modal');
        modals.forEach(modal => {
            const bootstrapModal = window.bootstrap.Modal.getInstance(modal);
            if (bootstrapModal) {
                bootstrapModal.hide();
            }
        });
    }
    
    showNotification(message, type = 'info') {
        // Use centralized notification manager
        if (window.notificationManager) {
            switch (type) {
                case 'success':
                    window.notificationManager.success(message);
                    break;
                case 'error':
                    window.notificationManager.error(message);
                    break;
                case 'warning':
                    window.notificationManager.warning(message);
                    break;
                default:
                    window.notificationManager.info(message);
                    break;
            }
        } else {
            // Fallback notification system
            console.log(`Cloud Sync Notification (${type}): ${message}`);
            
            const notification = document.createElement('div');
            notification.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show position-fixed`;
            notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
            
            notification.innerHTML = `
                <i class="bi bi-${this.getIconForType(type)}"></i>
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            `;
            
            document.body.appendChild(notification);
            
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 5000);
        }
    }
    
    showProgressToast(message) {
        const toast = document.createElement('div');
        toast.className = 'toast show position-fixed';
        toast.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
        
        toast.innerHTML = `
            <div class="toast-header">
                <i class="bi bi-arrow-repeat spinner-border spinner-border-sm me-2"></i>
                <strong class="me-auto">Cloud Sync</strong>
                <button type="button" class="btn-close" data-bs-dismiss="toast"></button>
            </div>
            <div class="toast-body">
                ${message}
            </div>
        `;
        
        document.body.appendChild(toast);
        return toast;
    }
    
    removeToast(toast) {
        if (toast && toast.parentNode) {
            toast.parentNode.removeChild(toast);
        }
    }
    
    getIconForType(type) {
        const icons = {
            'success': 'check-circle',
            'error': 'exclamation-triangle',
            'warning': 'exclamation-triangle',
            'info': 'info-circle'
        };
        return icons[type] || 'info-circle';
    }
    
    updateConnectionStatus(provider, status) {
        console.log(`Updating connection status for ${provider}: ${status}`);
        
        // Update internal state
        if (this.syncConfigs[provider]) {
            this.syncConfigs[provider].status = status;
        }
        
        // Update UI elements
        const providerCard = document.querySelector(`[data-provider="${provider}"]`);
        if (providerCard) {
            const statusBadge = providerCard.querySelector('.badge');
            if (statusBadge) {
                statusBadge.className = `badge bg-${status === 'connected' ? 'success' : 'danger'}`;
                statusBadge.textContent = status === 'connected' ? 'Connected' : 'Disconnected';
            }
        }
        
        // Refresh status display
        this.renderSyncStatus();
    }
    
    updateLastSyncDisplay(provider, timestamp) {
        console.log(`Updating last sync time for ${provider}:`, timestamp);
        
        // Update internal state
        if (this.syncConfigs[provider]) {
            this.syncConfigs[provider].last_sync = timestamp.toISOString();
        }
        
        // Refresh status display to show new sync time
        this.renderSyncStatus();
    }
    
    // Enhanced provider management
    async enableAutoSync(provider, enabled = true) {
        try {
            const response = await fetch('/api/cloud_sync/config/update', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    provider: provider,
                    auto_sync: enabled
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showNotification(`Auto-sync ${enabled ? 'enabled' : 'disabled'} for ${provider}`, 'success');
                await this.loadSyncStatus();
            } else {
                this.showNotification(`Failed to update auto-sync: ${data.error}`, 'error');
            }
        } catch (error) {
            console.error('Error updating auto-sync:', error);
            this.showNotification('Failed to update auto-sync settings', 'error');
        }
    }
    
    async updateSyncInterval(provider, intervalMinutes) {
        try {
            const response = await fetch('/api/cloud_sync/config/update', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    provider: provider,
                    sync_interval: intervalMinutes * 60 // Convert to seconds
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showNotification(`Sync interval updated to ${intervalMinutes} minutes for ${provider}`, 'success');
                await this.loadSyncStatus();
            } else {
                this.showNotification(`Failed to update sync interval: ${data.error}`, 'error');
            }
        } catch (error) {
            console.error('Error updating sync interval:', error);
            this.showNotification('Failed to update sync interval', 'error');
        }
    }
    
    // Export/Import configuration
    exportConfiguration() {
        const config = {
            providers: this.providers,
            syncConfigs: this.syncConfigs,
            exportedAt: new Date().toISOString()
        };
        
        const blob = new Blob([JSON.stringify(config, null, 2)], { 
            type: 'application/json' 
        });
        const url = URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.href = url;
        a.download = `vybe-cloud-sync-config-${new Date().toISOString().split('T')[0]}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        
        this.showNotification('Configuration exported successfully', 'success');
    }
    
    importConfiguration(file) {
        const reader = new FileReader();
        reader.onload = async (e) => {
            try {
                const config = JSON.parse(e.target.result);
                
                // Validate configuration structure
                if (!config.syncConfigs || typeof config.syncConfigs !== 'object') {
                    throw new Error('Invalid configuration format');
                }
                
                const response = await fetch('/api/cloud_sync/config/import', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(config)
                });
                
                const data = await response.json();
                
                if (data.success) {
                    this.showNotification('Configuration imported successfully', 'success');
                    await this.loadSyncStatus();
                    this.renderProviders();
                } else {
                    this.showNotification(`Import failed: ${data.error}`, 'error');
                }
                
            } catch (error) {
                console.error('Error importing configuration:', error);
                this.showNotification('Failed to import configuration. Please check the file format.', 'error');
            }
        };
        reader.readAsText(file);
    }
}

// Initialize when DOM is ready
window.eventManager.add(document, 'DOMContentLoaded', () => {
    window.cloudSyncManager = new CloudSyncManager();
});
