/**
 * Plugin Manager
 * Provides frontend interface for managing the plugin system
 */

// Import the centralized notification manager (attaches to window.notificationManager)
import './services/NotificationManager.js';

class PluginManager {
    constructor() {
        this.plugins = [];
        this.marketplacePlugins = [];
        this.isInitialized = false;
        this.currentPlugin = null;
        this.uploadProgress = 0;
        
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
        console.log('PluginManager: Starting initialization');
        window.notificationManager?.info('Initializing Plugin Manager...');
        
        try {
            console.log('PluginManager: Loading plugins...');
            await this.loadPlugins();
            
            console.log('PluginManager: Loading marketplace...');
            await this.loadMarketplace();
            
            console.log('PluginManager: Binding events...');
            this.bindEvents();
            
            this.isInitialized = true;
            console.log('PluginManager: Initialization completed successfully');
            window.notificationManager?.success('Plugin Manager initialized successfully');
        } catch (error) {
            console.error('PluginManager: Failed to initialize:', error);
            window.notificationManager?.error('Failed to initialize Plugin Manager: ' + error.message);
        }
    }

    async loadPlugins() {
        try {
            const response = await fetch('/api/plugins/status');
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();

            if (data.success) {
                this.plugins = data.plugins || [];
                this.renderPlugins();
            } else {
                throw new Error(data.error || 'Failed to load plugins');
            }
        } catch (error) {
            console.error('Error loading plugins:', error);
            window.notificationManager?.error('Failed to load plugins: ' + error.message);
        }
    }

    async loadMarketplace() {
        try {
            const response = await fetch('/api/plugins/marketplace');
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();

            if (data.success) {
                this.marketplacePlugins = data.plugins || [];
                this.renderMarketplace();
            } else {
                throw new Error(data.error || 'Failed to load marketplace');
            }
        } catch (error) {
            console.error('Error loading marketplace:', error);
            window.notificationManager?.error('Failed to load marketplace: ' + error.message);
        }
    }

    bindEvents() {
        console.log('PluginManager: Binding events');
        
        // Plugin actions with enhanced logging and feedback
        window.eventManager.add(document, 'click', (e) => {
            if (e.target.matches('.plugin-load-btn')) {
                const pluginId = e.target.dataset.pluginId;
                console.log(`PluginManager: Load button clicked for plugin: ${pluginId}`);
                window.notificationManager?.info(`Loading plugin: ${pluginId}`);
                this.loadPlugin(pluginId);
            }

            if (e.target.matches('.plugin-activate-btn')) {
                const pluginId = e.target.dataset.pluginId;
                console.log(`PluginManager: Activate button clicked for plugin: ${pluginId}`);
                window.notificationManager?.info(`Activating plugin: ${pluginId}`);
                this.activatePlugin(pluginId);
            }

            if (e.target.matches('.plugin-deactivate-btn')) {
                const pluginId = e.target.dataset.pluginId;
                console.log(`PluginManager: Deactivate button clicked for plugin: ${pluginId}`);
                window.notificationManager?.info(`Deactivating plugin: ${pluginId}`);
                this.deactivatePlugin(pluginId);
            }

            if (e.target.matches('.plugin-enable-btn')) {
                const pluginId = e.target.dataset.pluginId;
                console.log(`PluginManager: Enable button clicked for plugin: ${pluginId}`);
                window.notificationManager?.info(`Enabling plugin: ${pluginId}`);
                this.enablePlugin(pluginId);
            }

            if (e.target.matches('.plugin-disable-btn')) {
                const pluginId = e.target.dataset.pluginId;
                console.log(`PluginManager: Disable button clicked for plugin: ${pluginId}`);
                window.notificationManager?.warning(`Disabling plugin: ${pluginId}`);
                this.disablePlugin(pluginId);
            }

            if (e.target.matches('.plugin-unload-btn')) {
                const pluginId = e.target.dataset.pluginId;
                console.log(`PluginManager: Unload button clicked for plugin: ${pluginId}`);
                window.notificationManager?.warning(`Unloading plugin: ${pluginId}`);
                this.unloadPlugin(pluginId);
            }

            if (e.target.matches('.plugin-uninstall-btn')) {
                const pluginId = e.target.dataset.pluginId;
                console.log(`PluginManager: Uninstall button clicked for plugin: ${pluginId}`);
                window.notificationManager?.warning(`Uninstalling plugin: ${pluginId}`);
                this.uninstallPlugin(pluginId);
            }

            if (e.target.matches('.plugin-info-btn')) {
                const pluginId = e.target.dataset.pluginId;
                console.log(`PluginManager: Info button clicked for plugin: ${pluginId}`);
                window.notificationManager?.info(`Showing plugin info: ${pluginId}`);
                this.showPluginInfo(pluginId);
            }

            if (e.target.matches('.install-from-marketplace-btn')) {
                const pluginId = e.target.dataset.pluginId;
                console.log(`PluginManager: Marketplace install button clicked for plugin: ${pluginId}`);
                window.notificationManager?.info(`Installing from marketplace: ${pluginId}`);
                this.installFromMarketplace(pluginId);
            }

            if (e.target.matches('.discover-plugins-btn')) {
                console.log('PluginManager: Discover plugins button clicked');
                window.notificationManager?.info('Discovering plugins...');
                this.discoverPlugins();
            }

            if (e.target.matches('.plugin-settings-btn')) {
                console.log('PluginManager: Plugin settings button clicked');
                window.notificationManager?.info('Opening plugin settings...');
                this.showPluginSettings();
            }
        });

        // File upload events with enhanced feedback
        window.eventManager.add(document, 'change', (e) => {
            if (e.target.matches('#pluginFileInput')) {
                const file = e.target.files[0];
                console.log(`PluginManager: File selected: ${file ? file.name : 'none'}`);
                if (file) {
                    window.notificationManager?.info(`File selected: ${file.name}`);
                    this.handleFileUpload(file);
                }
            }
        });

        // Form submissions with enhanced logging
        window.eventManager.add(document, 'submit', (e) => {
            if (e.target.matches('#installPluginForm')) {
                e.preventDefault();
                console.log('PluginManager: Install plugin form submitted');
                window.notificationManager?.info('Installing plugin...');
                this.installPlugin();
            }

            if (e.target.matches('#pluginSettingsForm')) {
                e.preventDefault();
                console.log('PluginManager: Plugin settings form submitted');
                window.notificationManager?.info('Updating plugin settings...');
                this.updatePluginSettings();
            }
        });

        // Modal events with logging
        window.eventManager.add(document, 'click', (e) => {
            if (e.target.matches('.modal-close') || e.target.matches('.modal-backdrop')) {
                console.log('PluginManager: Modal close clicked');
                this.closeModals();
            }
        });

        console.log('PluginManager: All events bound successfully');
    }

    renderPlugins() {
        const container = document.getElementById('pluginsContainer');
        if (!container) return;

        container.innerHTML = '';

        if (this.plugins.length === 0) {
            container.innerHTML = `
                <div class="alert alert-info">
                    <i class="bi bi-info-circle"></i>
                    No plugins discovered. Use the "Discover Plugins" button to scan for plugins or install from the marketplace.
                </div>
            `;
            return;
        }

        this.plugins.forEach(plugin => {
            const card = this.createPluginCard(plugin);
            container.appendChild(card);
        });
    }

    createPluginCard(plugin) {
        const card = document.createElement('div');
        card.className = 'plugin-card mb-3';

        const statusBadge = this.getStatusBadge(plugin.status);
        const actionButtons = this.getActionButtons(plugin);

        card.innerHTML = `
            <div class="card">
                <div class="card-header d-flex justify-content-between align-items-center">
                    <h6 class="mb-0">
                        <i class="bi bi-puzzle"></i>
                        ${plugin.metadata.name}
                    </h6>
                    ${statusBadge}
                </div>
                <div class="card-body">
                    <p class="card-text">${plugin.metadata.description}</p>
                    
                    <div class="row mb-3">
                        <div class="col-md-6">
                            <small class="text-muted">
                                <strong>Author:</strong> ${plugin.metadata.author}<br>
                                <strong>Version:</strong> ${plugin.metadata.version}<br>
                                <strong>Type:</strong> ${plugin.metadata.plugin_type}
                            </small>
                        </div>
                        <div class="col-md-6">
                            <small class="text-muted">
                                <strong>ID:</strong> ${plugin.id}<br>
                                ${plugin.load_time ? `<strong>Loaded:</strong> ${new Date(plugin.load_time).toLocaleString()}<br>` : ''}
                                ${plugin.last_used ? `<strong>Last Used:</strong> ${new Date(plugin.last_used).toLocaleString()}` : ''}
                            </small>
                        </div>
                    </div>

                    <div class="plugin-tags mb-3">
                        ${plugin.metadata.tags.map(tag => 
                            `<span class="badge bg-secondary me-1">${tag}</span>`
                        ).join('')}
                    </div>

                    <div class="plugin-actions">
                        ${actionButtons}
                    </div>

                    ${plugin.error_message ? `
                        <div class="alert alert-danger mt-3">
                            <i class="bi bi-exclamation-triangle"></i>
                            <strong>Error:</strong> ${plugin.error_message}
                        </div>
                    ` : ''}
                </div>
            </div>
        `;

        return card;
    }

    getStatusBadge(status) {
        const statusConfig = {
            'active': { class: 'success', icon: 'check-circle', text: 'Active' },
            'loaded': { class: 'info', icon: 'box', text: 'Loaded' },
            'disabled': { class: 'secondary', icon: 'pause-circle', text: 'Disabled' },
            'error': { class: 'danger', icon: 'exclamation-triangle', text: 'Error' },
            'not_loaded': { class: 'warning', icon: 'question-circle', text: 'Not Loaded' }
        };

        const config = statusConfig[status] || { class: 'secondary', icon: 'question-circle', text: status };
        
        return `
            <span class="badge bg-${config.class}">
                <i class="bi bi-${config.icon}"></i>
                ${config.text}
            </span>
        `;
    }

    getActionButtons(plugin) {
        const buttons = [];

        // Info button
        buttons.push(`
            <button class="btn btn-outline-info btn-sm plugin-info-btn me-2" data-plugin-id="${plugin.id}">
                <i class="bi bi-info-circle"></i> Info
            </button>
        `);

        // Status-specific buttons
        switch (plugin.status) {
            case 'not_loaded':
                buttons.push(`
                    <button class="btn btn-primary btn-sm plugin-load-btn me-2" data-plugin-id="${plugin.id}">
                        <i class="bi bi-download"></i> Load
                    </button>
                `);
                break;

            case 'loaded':
                buttons.push(`
                    <button class="btn btn-success btn-sm plugin-activate-btn me-2" data-plugin-id="${plugin.id}">
                        <i class="bi bi-play-circle"></i> Activate
                    </button>
                    <button class="btn btn-warning btn-sm plugin-unload-btn me-2" data-plugin-id="${plugin.id}">
                        <i class="bi bi-x-circle"></i> Unload
                    </button>
                `);
                break;

            case 'active':
                buttons.push(`
                    <button class="btn btn-warning btn-sm plugin-deactivate-btn me-2" data-plugin-id="${plugin.id}">
                        <i class="bi bi-pause-circle"></i> Deactivate
                    </button>
                `);
                break;

            case 'disabled':
                buttons.push(`
                    <button class="btn btn-success btn-sm plugin-enable-btn me-2" data-plugin-id="${plugin.id}">
                        <i class="bi bi-check-circle"></i> Enable
                    </button>
                `);
                break;

            case 'error':
                buttons.push(`
                    <button class="btn btn-primary btn-sm plugin-load-btn me-2" data-plugin-id="${plugin.id}">
                        <i class="bi bi-arrow-clockwise"></i> Retry
                    </button>
                `);
                break;
        }

        // Disable/Uninstall buttons
        if (plugin.status !== 'disabled') {
            buttons.push(`
                <button class="btn btn-secondary btn-sm plugin-disable-btn me-2" data-plugin-id="${plugin.id}">
                    <i class="bi bi-pause-circle"></i> Disable
                </button>
            `);
        }

        buttons.push(`
            <button class="btn btn-danger btn-sm plugin-uninstall-btn" data-plugin-id="${plugin.id}">
                <i class="bi bi-trash"></i> Uninstall
            </button>
        `);

        return buttons.join('');
    }

    renderMarketplace() {
        const container = document.getElementById('marketplaceContainer');
        if (!container) return;

        container.innerHTML = '';

        if (this.marketplacePlugins.length === 0) {
            container.innerHTML = `
                <div class="alert alert-info">
                    <i class="bi bi-info-circle"></i>
                    No plugins available in marketplace.
                </div>
            `;
            return;
        }

        this.marketplacePlugins.forEach(plugin => {
            const card = this.createMarketplaceCard(plugin);
            container.appendChild(card);
        });
    }

    createMarketplaceCard(plugin) {
        const card = document.createElement('div');
        card.className = 'marketplace-plugin-card mb-3';

        card.innerHTML = `
            <div class="card">
                <div class="card-body">
                    <div class="d-flex justify-content-between align-items-start mb-3">
                        <div>
                            <h6 class="card-title mb-1">${plugin.name}</h6>
                            <p class="card-text text-muted mb-2">${plugin.description}</p>
                        </div>
                        <div class="text-end">
                            <div class="rating mb-1">
                                ${this.generateStars(plugin.rating)}
                                <small class="text-muted">(${plugin.rating})</small>
                            </div>
                            <small class="text-muted">${plugin.downloads} downloads</small>
                        </div>
                    </div>

                    <div class="row mb-3">
                        <div class="col-md-6">
                            <small class="text-muted">
                                <strong>Author:</strong> ${plugin.author}<br>
                                <strong>Version:</strong> ${plugin.version}<br>
                                <strong>Type:</strong> ${plugin.type}
                            </small>
                        </div>
                        <div class="col-md-6">
                            <div class="plugin-tags">
                                ${plugin.tags.map(tag => 
                                    `<span class="badge bg-secondary me-1">${tag}</span>`
                                ).join('')}
                            </div>
                        </div>
                    </div>

                    <div class="d-flex justify-content-between align-items-center">
                        <button class="btn btn-primary btn-sm install-from-marketplace-btn" data-plugin-id="${plugin.id}">
                            <i class="bi bi-download"></i> Install
                        </button>
                        <small class="text-muted">Plugin ID: ${plugin.id}</small>
                    </div>
                </div>
            </div>
        `;

        return card;
    }

    generateStars(rating) {
        const fullStars = Math.floor(rating);
        const hasHalfStar = rating % 1 >= 0.5;
        const emptyStars = 5 - fullStars - (hasHalfStar ? 1 : 0);

        let stars = '';
        for (let i = 0; i < fullStars; i++) {
            stars += '<i class="bi bi-star-fill text-warning"></i>';
        }
        if (hasHalfStar) {
            stars += '<i class="bi bi-star-half text-warning"></i>';
        }
        for (let i = 0; i < emptyStars; i++) {
            stars += '<i class="bi bi-star text-muted"></i>';
        }

        return stars;
    }

    async loadPlugin(pluginId) {
        const button = document.querySelector(`.plugin-load-btn[data-plugin-id="${pluginId}"]`);
        const originalText = button?.innerHTML;
        
        try {
            // Show loading state
            if (button) {
                button.disabled = true;
                button.innerHTML = '<i class="bi bi-hourglass-split"></i> Loading...';
            }

            const response = await fetch(`/api/plugins/${pluginId}/load`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();

            if (data.success) {
                window.notificationManager?.success('Plugin loaded successfully');
                await this.loadPlugins(); // Refresh the plugin list
            } else {
                throw new Error(data.error || 'Failed to load plugin');
            }
        } catch (error) {
            console.error('Error loading plugin:', error);
            window.notificationManager?.error('Failed to load plugin: ' + error.message);
        } finally {
            // Restore button state
            if (button && originalText) {
                button.disabled = false;
                button.innerHTML = originalText;
            }
        }
    }

    async activatePlugin(pluginId) {
        const button = document.querySelector(`.plugin-activate-btn[data-plugin-id="${pluginId}"]`);
        const originalText = button?.innerHTML;
        
        try {
            // Show loading state
            if (button) {
                button.disabled = true;
                button.innerHTML = '<i class="bi bi-hourglass-split"></i> Activating...';
            }

            const response = await fetch(`/api/plugins/${pluginId}/activate`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();

            if (data.success) {
                window.notificationManager?.success('Plugin activated successfully');
                await this.loadPlugins(); // Refresh the plugin list
            } else {
                throw new Error(data.error || 'Failed to activate plugin');
            }
        } catch (error) {
            console.error('Error activating plugin:', error);
            window.notificationManager?.error('Failed to activate plugin: ' + error.message);
        } finally {
            // Restore button state
            if (button && originalText) {
                button.disabled = false;
                button.innerHTML = originalText;
            }
        }
    }

    async deactivatePlugin(pluginId) {
        const button = document.querySelector(`.plugin-deactivate-btn[data-plugin-id="${pluginId}"]`);
        const originalText = button?.innerHTML;
        
        try {
            // Show loading state
            if (button) {
                button.disabled = true;
                button.innerHTML = '<i class="bi bi-hourglass-split"></i> Deactivating...';
            }

            const response = await fetch(`/api/plugins/${pluginId}/deactivate`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();

            if (data.success) {
                window.notificationManager?.success('Plugin deactivated successfully');
                await this.loadPlugins(); // Refresh the plugin list
            } else {
                throw new Error(data.error || 'Failed to deactivate plugin');
            }
        } catch (error) {
            console.error('Error deactivating plugin:', error);
            window.notificationManager?.error('Failed to deactivate plugin: ' + error.message);
        } finally {
            // Restore button state
            if (button && originalText) {
                button.disabled = false;
                button.innerHTML = originalText;
            }
        }
    }

    async enablePlugin(pluginId) {
        const button = document.querySelector(`.plugin-enable-btn[data-plugin-id="${pluginId}"]`);
        const originalText = button?.innerHTML;
        
        try {
            // Show loading state
            if (button) {
                button.disabled = true;
                button.innerHTML = '<i class="bi bi-hourglass-split"></i> Enabling...';
            }

            const response = await fetch(`/api/plugins/${pluginId}/enable`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();

            if (data.success) {
                window.notificationManager?.success('Plugin enabled successfully');
                await this.loadPlugins(); // Refresh the plugin list
            } else {
                throw new Error(data.error || 'Failed to enable plugin');
            }
        } catch (error) {
            console.error('Error enabling plugin:', error);
            window.notificationManager?.error('Failed to enable plugin: ' + error.message);
        } finally {
            // Restore button state
            if (button && originalText) {
                button.disabled = false;
                button.innerHTML = originalText;
            }
        }
    }

    async disablePlugin(pluginId) {
        if (!confirm('Are you sure you want to disable this plugin?')) {
            return;
        }

        const button = document.querySelector(`.plugin-disable-btn[data-plugin-id="${pluginId}"]`);
        const originalText = button?.innerHTML;
        
        try {
            // Show loading state
            if (button) {
                button.disabled = true;
                button.innerHTML = '<i class="bi bi-hourglass-split"></i> Disabling...';
            }

            const response = await fetch(`/api/plugins/${pluginId}/disable`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();

            if (data.success) {
                window.notificationManager?.success('Plugin disabled successfully');
                await this.loadPlugins(); // Refresh the plugin list
            } else {
                throw new Error(data.error || 'Failed to disable plugin');
            }
        } catch (error) {
            console.error('Error disabling plugin:', error);
            window.notificationManager?.error('Failed to disable plugin: ' + error.message);
        } finally {
            // Restore button state
            if (button && originalText) {
                button.disabled = false;
                button.innerHTML = originalText;
            }
        }
    }

    async unloadPlugin(pluginId) {
        if (!confirm('Are you sure you want to unload this plugin?')) {
            return;
        }

        const button = document.querySelector(`.plugin-unload-btn[data-plugin-id="${pluginId}"]`);
        const originalText = button?.innerHTML;
        
        try {
            // Show loading state
            if (button) {
                button.disabled = true;
                button.innerHTML = '<i class="bi bi-hourglass-split"></i> Unloading...';
            }

            const response = await fetch(`/api/plugins/${pluginId}/unload`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();

            if (data.success) {
                window.notificationManager?.success('Plugin unloaded successfully');
                await this.loadPlugins(); // Refresh the plugin list
            } else {
                throw new Error(data.error || 'Failed to unload plugin');
            }
        } catch (error) {
            console.error('Error unloading plugin:', error);
            window.notificationManager?.error('Failed to unload plugin: ' + error.message);
        } finally {
            // Restore button state
            if (button && originalText) {
                button.disabled = false;
                button.innerHTML = originalText;
            }
        }
    }

    async uninstallPlugin(pluginId) {
        if (!confirm('Are you sure you want to uninstall this plugin? This action cannot be undone.')) {
            return;
        }

        const button = document.querySelector(`.plugin-uninstall-btn[data-plugin-id="${pluginId}"]`);
        const originalText = button?.innerHTML;
        
        try {
            // Show loading state
            if (button) {
                button.disabled = true;
                button.innerHTML = '<i class="bi bi-hourglass-split"></i> Uninstalling...';
            }

            const response = await fetch(`/api/plugins/${pluginId}/uninstall`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();

            if (data.success) {
                window.notificationManager?.success('Plugin uninstalled successfully');
                await this.loadPlugins(); // Refresh the plugin list
            } else {
                throw new Error(data.error || 'Failed to uninstall plugin');
            }
        } catch (error) {
            console.error('Error uninstalling plugin:', error);
            window.notificationManager?.error('Failed to uninstall plugin: ' + error.message);
        } finally {
            // Restore button state
            if (button && originalText) {
                button.disabled = false;
                button.innerHTML = originalText;
            }
        }
    }

    async discoverPlugins() {
        const button = document.querySelector('.discover-plugins-btn');
        const originalText = button?.innerHTML;
        
        try {
            // Show loading state
            if (button) {
                button.disabled = true;
                button.innerHTML = '<i class="bi bi-hourglass-split"></i> Discovering...';
            }

            const response = await fetch('/api/plugins/discover', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();

            if (data.success) {
                window.notificationManager?.success(data.message || 'Plugin discovery completed');
                await this.loadPlugins(); // Refresh the plugin list
            } else {
                throw new Error(data.error || 'Failed to discover plugins');
            }
        } catch (error) {
            console.error('Error discovering plugins:', error);
            window.notificationManager?.error('Failed to discover plugins: ' + error.message);
        } finally {
            // Restore button state
            if (button && originalText) {
                button.disabled = false;
                button.innerHTML = originalText;
            }
        }
    }

    async installFromMarketplace(pluginId) {
        const button = document.querySelector(`.install-from-marketplace-btn[data-plugin-id="${pluginId}"]`);
        const originalText = button?.innerHTML;
        
        try {
            const plugin = this.marketplacePlugins.find(p => p.id === pluginId);
            if (!plugin) {
                window.notificationManager?.error('Plugin not found in marketplace');
                return;
            }

            // Show loading state
            if (button) {
                button.disabled = true;
                button.innerHTML = '<i class="bi bi-hourglass-split"></i> Installing...';
            }

            // Send request to backend API to install from marketplace
            const response = await fetch('/api/plugins/install', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    plugin_id: pluginId,
                    source: 'marketplace'
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();

            if (data.success) {
                window.notificationManager?.success(`Successfully installed ${plugin.name} from marketplace`);
                await this.loadPlugins();
                await this.loadMarketplace();
            } else {
                throw new Error(data.error || 'Failed to install from marketplace');
            }
        } catch (error) {
            console.error('Error installing from marketplace:', error);
            window.notificationManager?.error('Failed to install from marketplace: ' + error.message);
        } finally {
            // Restore button state
            if (button && originalText) {
                button.disabled = false;
                button.innerHTML = originalText;
            }
        }
    }

    handleFileUpload(file) {
        console.log('PluginManager: Handling file upload');
        
        if (!file) {
            console.warn('PluginManager: No file provided');
            window.notificationManager?.warning('No file selected');
            return;
        }

        console.log(`PluginManager: Processing file: ${file.name}, Size: ${file.size} bytes, Type: ${file.type}`);

        // Validate file type
        if (!file.name.endsWith('.zip')) {
            console.error('PluginManager: Invalid file type');
            window.notificationManager?.error('Please select a ZIP file');
            return;
        }

        // Validate file size (max 50MB)
        const maxSize = 50 * 1024 * 1024; // 50MB
        if (file.size > maxSize) {
            console.error('PluginManager: File too large');
            window.notificationManager?.error('File is too large (max 50MB)');
            return;
        }

        // Validate file name
        if (!/^[a-zA-Z0-9_\-.]+$/.test(file.name)) {
            console.error('PluginManager: Invalid file name');
            window.notificationManager?.error('Invalid file name. Only letters, numbers, hyphens, underscores, and dots are allowed.');
            return;
        }

        console.log('PluginManager: File validation passed');
        window.notificationManager?.success('File validated successfully');

        // Show upload progress
        this.showUploadProgress();

        // Store file for later upload
        this.selectedFile = file;

        // Enable install button if it exists
        const installBtn = document.querySelector('#installPluginForm button[type="submit"]');
        if (installBtn) {
            installBtn.disabled = false;
            installBtn.textContent = `Install ${file.name}`;
        }

        // Update file info display
        this.updateFileInfo(file);
    }

    updateFileInfo(file) {
        console.log('PluginManager: Updating file info display');
        
        const fileInfoContainer = document.getElementById('fileInfo');
        if (fileInfoContainer) {
            fileInfoContainer.innerHTML = `
                <div class="alert alert-info">
                    <h6><i class="bi bi-file-zip"></i> Selected File</h6>
                    <p class="mb-1"><strong>Name:</strong> ${file.name}</p>
                    <p class="mb-1"><strong>Size:</strong> ${this.formatFileSize(file.size)}</p>
                    <p class="mb-0"><strong>Type:</strong> ${file.type || 'application/zip'}</p>
                </div>
            `;
        }

        window.notificationManager?.info(`File info updated: ${file.name}`);
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    async installPlugin() {
        const fileInput = document.getElementById('pluginFileInput');
        const submitButton = document.querySelector('#installPluginForm button[type="submit"]');
        const originalButtonText = submitButton?.innerHTML;
        
        if (!fileInput?.files[0]) {
            window.notificationManager?.error('Please select a plugin file');
            return;
        }

        const formData = new FormData();
        formData.append('plugin_file', fileInput.files[0]);

        try {
            // Show loading state
            if (submitButton) {
                submitButton.disabled = true;
                submitButton.innerHTML = '<i class="bi bi-hourglass-split"></i> Installing...';
            }

            const response = await fetch('/api/plugins/install', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();

            if (data.success) {
                window.notificationManager?.success('Plugin installed successfully');
                fileInput.value = '';
                
                // Clear file info display
                const fileInfoContainer = document.getElementById('fileInfo');
                if (fileInfoContainer) {
                    fileInfoContainer.innerHTML = '';
                }
                
                await this.loadPlugins(); // Refresh plugin list
                this.closeModals();
            } else {
                throw new Error(data.error || 'Failed to install plugin');
            }
        } catch (error) {
            console.error('Error installing plugin:', error);
            window.notificationManager?.error('Failed to install plugin: ' + error.message);
        } finally {
            // Restore button state
            if (submitButton && originalButtonText) {
                submitButton.disabled = false;
                submitButton.innerHTML = originalButtonText;
            }
        }
    }

    async showPluginInfo(pluginId) {
        const button = document.querySelector(`.plugin-info-btn[data-plugin-id="${pluginId}"]`);
        const originalText = button?.innerHTML;
        
        try {
            // Show loading state
            if (button) {
                button.disabled = true;
                button.innerHTML = '<i class="bi bi-hourglass-split"></i> Loading...';
            }

            const response = await fetch(`/api/plugins/${pluginId}/info`);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();

            if (data.success) {
                this.showPluginInfoModal(data.plugin);
            } else {
                throw new Error(data.error || 'Failed to get plugin info');
            }
        } catch (error) {
            console.error('Error getting plugin info:', error);
            window.notificationManager?.error('Failed to get plugin info: ' + error.message);
        } finally {
            // Restore button state
            if (button && originalText) {
                button.disabled = false;
                button.innerHTML = originalText;
            }
        }
    }

    showPluginInfoModal(plugin) {
        const modal = document.createElement('div');
        modal.className = 'modal fade';
        modal.id = 'pluginInfoModal';

        modal.innerHTML = `
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">Plugin Information: ${plugin.metadata.name}</h5>
                        <button type="button" class="btn-close modal-close"></button>
                    </div>
                    <div class="modal-body">
                        <div class="row">
                            <div class="col-md-6">
                                <h6>Basic Information</h6>
                                <p><strong>ID:</strong> ${plugin.id}</p>
                                <p><strong>Name:</strong> ${plugin.metadata.name}</p>
                                <p><strong>Version:</strong> ${plugin.metadata.version}</p>
                                <p><strong>Author:</strong> ${plugin.metadata.author}</p>
                                <p><strong>Type:</strong> ${plugin.metadata.plugin_type}</p>
                                <p><strong>Description:</strong> ${plugin.metadata.description}</p>
                            </div>
                            <div class="col-md-6">
                                <h6>Status Information</h6>
                                <p><strong>Status:</strong> ${plugin.status}</p>
                                ${plugin.load_time ? `<p><strong>Load Time:</strong> ${new Date(plugin.load_time).toLocaleString()}</p>` : ''}
                                ${plugin.last_used ? `<p><strong>Last Used:</strong> ${new Date(plugin.last_used).toLocaleString()}</p>` : ''}
                                <p><strong>Usage Count:</strong> ${plugin.usage_count || 0}</p>
                                ${plugin.error_message ? `<p><strong>Error:</strong> ${plugin.error_message}</p>` : ''}
                            </div>
                        </div>

                        <div class="row mt-3">
                            <div class="col-12">
                                <h6>Dependencies</h6>
                                <p><strong>Dependencies:</strong> ${plugin.metadata.dependencies.join(', ') || 'None'}</p>
                                <p><strong>Requirements:</strong> ${plugin.metadata.requirements.join(', ') || 'None'}</p>
                                <p><strong>Permissions:</strong> ${plugin.metadata.permissions.join(', ') || 'None'}</p>
                            </div>
                        </div>

                        <div class="row mt-3">
                            <div class="col-12">
                                <h6>Tags</h6>
                                <div class="plugin-tags">
                                    ${plugin.metadata.tags.map(tag => 
                                        `<span class="badge bg-secondary me-1">${tag}</span>`
                                    ).join('')}
                                </div>
                            </div>
                        </div>

                        ${plugin.metadata.website ? `
                            <div class="row mt-3">
                                <div class="col-12">
                                    <h6>Links</h6>
                                    <p><strong>Website:</strong> <a href="${plugin.metadata.website}" target="_blank">${plugin.metadata.website}</a></p>
                                </div>
                            </div>
                        ` : ''}
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

    showUploadProgress() {
        console.log('PluginManager: Showing upload progress');
        
        // Create or update progress modal
        let progressModal = document.getElementById('uploadProgressModal');
        if (!progressModal) {
            progressModal = document.createElement('div');
            progressModal.className = 'modal fade';
            progressModal.id = 'uploadProgressModal';
            progressModal.innerHTML = `
                <div class="modal-dialog modal-dialog-centered">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">Uploading Plugin</h5>
                        </div>
                        <div class="modal-body text-center">
                            <div class="mb-3">
                                <i class="bi bi-cloud-upload" style="font-size: 2rem; color: #0d6efd;"></i>
                            </div>
                            <div class="progress mb-3" style="height: 20px;">
                                <div class="progress-bar progress-bar-striped progress-bar-animated" 
                                     id="uploadProgressBar" role="progressbar" 
                                     style="width: 0%" aria-valuenow="0" aria-valuemin="0" aria-valuemax="100">
                                    0%
                                </div>
                            </div>
                            <p id="uploadProgressText">Preparing upload...</p>
                        </div>
                    </div>
                </div>
            `;
            document.body.appendChild(progressModal);
        }

        // Show the modal
        const bootstrapModal = new window.bootstrap.Modal(progressModal);
        bootstrapModal.show();

        // Simulate upload progress
        this.simulateUploadProgress();

        window.notificationManager?.info('Upload started');
    }

    simulateUploadProgress() {
        console.log('PluginManager: Simulating upload progress');
        const progressBar = document.getElementById('uploadProgressBar');
        const progressText = document.getElementById('uploadProgressText');
        
        if (!progressBar || !progressText) return;

        let progress = 0;
        const interval = setInterval(() => {
            progress += Math.random() * 15 + 5; // Random increment between 5-20%
            
            if (progress >= 100) {
                progress = 100;
                clearInterval(interval);
                
                // Update UI to show completion
                progressBar.style.width = '100%';
                progressBar.textContent = '100%';
                progressBar.classList.remove('progress-bar-animated');
                progressBar.classList.add('bg-success');
                progressText.textContent = 'Upload complete!';
                
                // Close modal after a delay
                setTimeout(() => {
                    const modal = document.getElementById('uploadProgressModal');
                    if (modal) {
                        const bootstrapModal = window.bootstrap.Modal.getInstance(modal);
                        if (bootstrapModal) {
                            bootstrapModal.hide();
                        }
                    }
                    window.notificationManager?.success('Plugin upload completed');
                    console.log('PluginManager: Upload simulation completed');
                }, 1500);
                
                return;
            }
            
            // Update progress display
            progressBar.style.width = `${progress}%`;
            progressBar.textContent = `${Math.round(progress)}%`;
            progressBar.setAttribute('aria-valuenow', progress);
            
            // Update status text based on progress
            if (progress < 30) {
                progressText.textContent = 'Validating plugin file...';
            } else if (progress < 60) {
                progressText.textContent = 'Extracting plugin contents...';
            } else if (progress < 90) {
                progressText.textContent = 'Installing dependencies...';
            } else {
                progressText.textContent = 'Finalizing installation...';
            }
            
            console.log(`PluginManager: Upload progress: ${Math.round(progress)}%`);
        }, 200);
    }

    async showPluginSettings() {
        const button = document.querySelector('.plugin-settings-btn');
        const originalText = button?.innerHTML;
        
        try {
            // Show loading state
            if (button) {
                button.disabled = true;
                button.innerHTML = '<i class="bi bi-hourglass-split"></i> Loading...';
            }

            const response = await fetch('/api/plugins/settings');
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();

            if (data.success) {
                this.showPluginSettingsModal(data.settings);
            } else {
                throw new Error(data.error || 'Failed to get plugin settings');
            }
        } catch (error) {
            console.error('Error getting plugin settings:', error);
            window.notificationManager?.error('Failed to get plugin settings: ' + error.message);
        } finally {
            // Restore button state
            if (button && originalText) {
                button.disabled = false;
                button.innerHTML = originalText;
            }
        }
    }

    showPluginSettingsModal(settings) {
        const modal = document.createElement('div');
        modal.className = 'modal fade';
        modal.id = 'pluginSettingsModal';

        modal.innerHTML = `
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">Plugin System Settings</h5>
                        <button type="button" class="btn-close modal-close"></button>
                    </div>
                    <div class="modal-body">
                        <form id="pluginSettingsForm">
                            <div class="row">
                                <div class="col-md-6">
                                    <div class="mb-3">
                                        <label for="pluginsDirectory" class="form-label">Plugins Directory</label>
                                        <input type="text" class="form-control" id="pluginsDirectory" 
                                               value="${settings.plugins_directory}" readonly>
                                    </div>

                                    <div class="form-check mb-3">
                                        <input class="form-check-input" type="checkbox" id="autoDiscovery" 
                                               ${settings.auto_discovery ? 'checked' : ''}>
                                        <label class="form-check-label" for="autoDiscovery">
                                            Auto-discovery of plugins
                                        </label>
                                    </div>

                                    <div class="form-check mb-3">
                                        <input class="form-check-input" type="checkbox" id="autoLoadEnabled" 
                                               ${settings.auto_load_enabled ? 'checked' : ''}>
                                        <label class="form-check-label" for="autoLoadEnabled">
                                            Auto-load enabled plugins
                                        </label>
                                    </div>
                                </div>

                                <div class="col-md-6">
                                    <div class="form-check mb-3">
                                        <input class="form-check-input" type="checkbox" id="pluginValidation" 
                                               ${settings.plugin_validation ? 'checked' : ''}>
                                        <label class="form-check-label" for="pluginValidation">
                                            Plugin validation
                                        </label>
                                    </div>

                                    <div class="form-check mb-3">
                                        <input class="form-check-input" type="checkbox" id="sandboxMode" 
                                               ${settings.sandbox_mode ? 'checked' : ''}>
                                        <label class="form-check-label" for="sandboxMode">
                                            Sandbox mode
                                        </label>
                                    </div>

                                    <div class="mb-3">
                                        <label for="maxPlugins" class="form-label">Maximum Plugins</label>
                                        <input type="number" class="form-control" id="maxPlugins" 
                                               value="${settings.max_plugins}" min="1" max="1000">
                                    </div>
                                </div>
                            </div>

                            <div class="row mt-3">
                                <div class="col-12">
                                    <h6>Plugin Permissions</h6>
                                    <div class="form-check">
                                        <input class="form-check-input" type="checkbox" id="fileAccess" 
                                               ${settings.plugin_permissions.file_access ? 'checked' : ''}>
                                        <label class="form-check-label" for="fileAccess">
                                            File access
                                        </label>
                                    </div>
                                    <div class="form-check">
                                        <input class="form-check-input" type="checkbox" id="networkAccess" 
                                               ${settings.plugin_permissions.network_access ? 'checked' : ''}>
                                        <label class="form-check-label" for="networkAccess">
                                            Network access
                                        </label>
                                    </div>
                                    <div class="form-check">
                                        <input class="form-check-input" type="checkbox" id="systemAccess" 
                                               ${settings.plugin_permissions.system_access ? 'checked' : ''}>
                                        <label class="form-check-label" for="systemAccess">
                                            System access
                                        </label>
                                    </div>
                                </div>
                            </div>
                        </form>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary modal-close">Cancel</button>
                        <button type="submit" form="pluginSettingsForm" class="btn btn-primary">Save Settings</button>
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

    async updatePluginSettings() {
        const submitButton = document.querySelector('#pluginSettingsForm button[type="submit"]');
        const originalText = submitButton?.innerHTML;
        
        try {
            // Show loading state
            if (submitButton) {
                submitButton.disabled = true;
                submitButton.innerHTML = '<i class="bi bi-hourglass-split"></i> Updating...';
            }

            const formData = {
                auto_discovery: document.getElementById('autoDiscovery').checked,
                auto_load_enabled: document.getElementById('autoLoadEnabled').checked,
                plugin_validation: document.getElementById('pluginValidation').checked,
                sandbox_mode: document.getElementById('sandboxMode').checked,
                max_plugins: parseInt(document.getElementById('maxPlugins').value),
                plugin_permissions: {
                    file_access: document.getElementById('fileAccess').checked,
                    network_access: document.getElementById('networkAccess').checked,
                    system_access: document.getElementById('systemAccess').checked
                }
            };

            const response = await fetch('/api/plugins/settings', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(formData)
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();

            if (data.success) {
                window.notificationManager?.success('Plugin settings updated successfully');
                this.closeModals();
            } else {
                throw new Error(data.error || 'Failed to update plugin settings');
            }
        } catch (error) {
            console.error('Error updating plugin settings:', error);
            window.notificationManager?.error('Failed to update plugin settings: ' + error.message);
        } finally {
            // Restore button state
            if (submitButton && originalText) {
                submitButton.disabled = false;
                submitButton.innerHTML = originalText;
            }
        }
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

    // Utility method to get plugin by ID
    getPluginById(pluginId) {
        console.log(`PluginManager: Looking for plugin with ID: ${pluginId}`);
        const plugin = this.plugins.find(p => p.id === pluginId);
        if (plugin) {
            console.log(`PluginManager: Found plugin: ${plugin.metadata.name}`);
        } else {
            console.warn(`PluginManager: Plugin not found: ${pluginId}`);
        }
        return plugin;
    }

    // Utility method to get plugin statistics
    getPluginStats() {
        const stats = {
            total: this.plugins.length,
            active: this.plugins.filter(p => p.status === 'active').length,
            loaded: this.plugins.filter(p => p.status === 'loaded').length,
            disabled: this.plugins.filter(p => p.status === 'disabled').length,
            error: this.plugins.filter(p => p.status === 'error').length,
            not_loaded: this.plugins.filter(p => p.status === 'not_loaded').length
        };
        
        console.log('PluginManager: Plugin statistics:', stats);
        return stats;
    }

    // Utility method to refresh all data
    async refresh() {
        console.log('PluginManager: Refreshing all data');
        window.notificationManager?.info('Refreshing plugin data...');
        
        try {
            await this.loadPlugins();
            await this.loadMarketplace();
            window.notificationManager?.success('Plugin data refreshed');
        } catch (error) {
            console.error('PluginManager: Error refreshing data:', error);
            window.notificationManager?.error('Failed to refresh plugin data');
        }
    }

    showNotification(message, type = 'info') {
        // Use global NotificationManager for consistent notifications
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
            const notification = document.createElement('div');
            notification.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show position-fixed`;
            notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';

            notification.innerHTML = `
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            `;

            document.body.appendChild(notification);

            // Auto-remove after 5 seconds
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 5000);
        }
    }
}

// Notification system handled by global NotificationManager

// Bootstrap safety check
if (typeof window.bootstrap === 'undefined') {
    console.warn('PluginManager: Bootstrap not available, some UI features may not work properly');
    window.bootstrap = {
        Modal: function() {
            console.warn('Bootstrap Modal not available');
            return {
                show: () => console.log('Modal show (Bootstrap fallback)'),
                hide: () => console.log('Modal hide (Bootstrap fallback)')
            };
        }
    };
}

// Initialize when DOM is loaded
window.eventManager.add(document, 'DOMContentLoaded', () => {
    if (document.getElementById('plugin-manager-container')) {
        window.pluginManager = new PluginManager();
    }
});
