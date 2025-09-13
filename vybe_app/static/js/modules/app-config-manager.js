/**
 * App Configuration Manager Module
 * Handles application configuration, version info, and system status
 */

import { ApiUtils } from '../utils/api-utils.js';

export class AppConfigManager {
    constructor() {
        this.configData = null;
        
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
        this.loadAppConfiguration();
        this.setupEventListeners();
    }

    setupEventListeners() {
        // View configuration button
        const viewConfigBtn = document.getElementById('view-config-btn');
        if (viewConfigBtn) {
            window.eventManager.add(viewConfigBtn, 'click', () => this.showConfigModal());
        }

        // Edit configuration button
        const editConfigBtn = document.getElementById('edit-config-btn');
        if (editConfigBtn) {
            window.eventManager.add(editConfigBtn, 'click', () => this.showEditConfigModal());
        }

        // Refresh config button
        const refreshConfigBtn = document.getElementById('refresh-config');
        if (refreshConfigBtn) {
            window.eventManager.add(refreshConfigBtn, 'click', () => this.loadAppConfiguration());
        }

        // Submit feedback button
        const submitFeedbackBtn = document.getElementById('submit-feedback');
        if (submitFeedbackBtn) {
            window.eventManager.add(submitFeedbackBtn, 'click', () => this.submitFeedback());
        }

        // View logs button
        const viewLogsBtn = document.getElementById('view-logs');
        if (viewLogsBtn) {
            window.eventManager.add(viewLogsBtn, 'click', () => this.showLogsModal());
        }

        // Load logs button
        const loadLogsBtn = document.getElementById('load-logs');
        if (loadLogsBtn) {
            window.eventManager.add(loadLogsBtn, 'click', () => this.loadLogs());
        }

        // Export configuration button
        const exportConfigBtn = document.getElementById('export-config');
        if (exportConfigBtn) {
            window.eventManager.add(exportConfigBtn, 'click', () => this.exportConfiguration());
        }

        // Import configuration button
        const importConfigBtn = document.getElementById('import-config');
        if (importConfigBtn) {
            window.eventManager.add(importConfigBtn, 'click', () => this.importConfiguration());
        }

        // Reset configuration button
        const resetConfigBtn = document.getElementById('reset-config');
        if (resetConfigBtn) {
            window.eventManager.add(resetConfigBtn, 'click', () => this.resetConfiguration());
        }

        // System diagnostics button
        const diagnosticsBtn = document.getElementById('run-diagnostics');
        if (diagnosticsBtn) {
            window.eventManager.add(diagnosticsBtn, 'click', () => this.runSystemDiagnostics());
        }

        // Clear logs button
        const clearLogsBtn = document.getElementById('clear-logs');
        if (clearLogsBtn) {
            window.eventManager.add(clearLogsBtn, 'click', () => this.clearLogs());
        }
    }

    async loadAppConfiguration() {
        try {
            const data = await ApiUtils.safeFetch('/api/configuration');
            if (data) {
                this.configData = data;
                this.displayConfiguration(data);
            }
        } catch (error) {
            console.error('Error loading app configuration:', error);
            ApiUtils.showGlobalStatus('Failed to load application configuration', 'error');
        }
    }

    displayConfiguration(config) {
        // Display app version
        const versionElement = document.getElementById('app-version');
        if (versionElement && config.version) {
            versionElement.textContent = config.version;
        }

        // Display LLM backend status
        const llmStatusElement = document.getElementById('llm-status');
        if (llmStatusElement && config.llm_backend_status) {
            llmStatusElement.textContent = config.llm_backend_status;
            llmStatusElement.className = `status-indicator ${config.llm_backend_status}`;
        }

        // Display features status
        if (config.features) {
            Object.entries(config.features).forEach(([feature, enabled]) => {
                const element = document.getElementById(`feature-${feature}`);
                if (element) {
                    element.textContent = enabled ? 'Enabled' : 'Disabled';
                    element.className = `feature-status ${enabled ? 'enabled' : 'disabled'}`;
                }
            });
        }

        // Display app name
        const appNameElement = document.getElementById('app-name');
        if (appNameElement && config.app_name) {
            appNameElement.textContent = config.app_name;
        }
    }

    async submitFeedback() {
        console.log('Submitting feedback...');
        const feedbackTextarea = document.getElementById('feedback-text');
        if (!feedbackTextarea) {
            this.showNotification('Feedback form not found', 'error');
            return;
        }

        const feedbackText = feedbackTextarea.value.trim();
        if (!feedbackText) {
            this.showNotification('Please enter your feedback', 'error');
            return;
        }

        try {
            this.showNotification('Submitting feedback...', 'info');
            const data = await ApiUtils.safeFetch('/api/feedback', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ feedback: feedbackText })
            });

            if (data && data.success) {
                this.showNotification('Thank you for your feedback!', 'success');
                feedbackTextarea.value = ''; // Clear the textarea
            } else {
                this.showNotification('Failed to submit feedback', 'error');
            }
        } catch (error) {
            console.error('Error submitting feedback:', error);
            this.showNotification('Error submitting feedback', 'error');
        }
    }

    showLogsModal() {
        console.log('Opening logs modal...');
        this.showNotification('Opening application logs', 'info');
        const modal = document.getElementById('logs-modal');
        if (modal) {
            modal.style.display = 'block';
            this.loadLogs(100); // Load recent logs by default
        } else {
            // Create logs modal if it doesn't exist
            this.createLogsModal();
        }
    }

    async loadLogs(lines = 100) {
        console.log('Loading application logs...');
        this.showNotification('Loading logs...', 'info');
        try {
            const data = await ApiUtils.safeFetch(`/api/logs?lines=${lines}`);
            const logsContainer = document.getElementById('logs-content');
            
            if (logsContainer) {
                if (data && data.logs) {
                    logsContainer.textContent = data.logs;
                    // Scroll to bottom
                    logsContainer.scrollTop = logsContainer.scrollHeight;
                    this.showNotification('Logs loaded successfully', 'success');
                } else {
                    logsContainer.textContent = 'No logs available';
                    this.showNotification('No logs found', 'warning');
                }
            }
        } catch (error) {
            console.error('Error loading logs:', error);
            const logsContainer = document.getElementById('logs-content');
            if (logsContainer) {
                logsContainer.textContent = 'Error loading logs: ' + error.message;
            }
            this.showNotification('Failed to load logs', 'error');
        }
    }

    getConfigurationData() {
        return this.configData;
    }

    showConfigurationModal() {
        // For now, show the configuration as JSON in an alert
        if (this.configData) {
            const configText = JSON.stringify(this.configData, null, 2);
            const modal = this.createConfigModal('View Configuration', configText, false);
            document.body.appendChild(modal);
            modal.style.display = 'flex';
        } else {
            alert('Configuration data not loaded yet. Please try again.');
        }
    }

    showEditConfigModal() {
        if (!this.configData) {
            alert('Configuration data not loaded yet. Please try again.');
            return;
        }

        const modal = this.createConfigEditModal();
        document.body.appendChild(modal);
        modal.style.display = 'flex';
    }

    createConfigEditModal() {
        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.innerHTML = `
            <div class="modal-content" style="max-width: 900px; max-height: 700px;">
                <div class="modal-header">
                    <h3>⚙️ Edit Configuration</h3>
                    <button class="modal-close">&times;</button>
                </div>
                <div class="modal-body">
                    <div class="config-editor">
                        <div class="config-warning" style="background: #fff3cd; border: 1px solid #ffeaa7; border-radius: 4px; padding: 1rem; margin-bottom: 1rem; color: #856404;">
                            ⚠️ <strong>Warning:</strong> Editing configuration requires careful attention. Invalid settings may cause application issues.
                        </div>
                        
                        <div class="config-sections">
                            ${this.renderConfigSections()}
                        </div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button class="settings-button secondary modal-close">Cancel</button>
                    <button id="save-config" class="settings-button primary">Save Configuration</button>
                </div>
            </div>
        `;

        // Add event listeners
        modal.querySelectorAll('.modal-close').forEach(btn => {
            window.eventManager.add(btn, 'click', () => modal.remove());
        });

        window.eventManager.add(modal, 'click', (e) => {
            if (e.target === modal) {
                modal.remove();
            }
        });

        const saveBtn = modal.querySelector('#save-config');
        if (saveBtn) {
            window.eventManager.add(saveBtn, 'click', () => this.saveConfiguration(modal));
        }

        return modal;
    }

    renderConfigSections() {
        const sections = [
            {
                title: 'Application Settings',
                fields: [
                    { key: 'app_name', label: 'Application Name', type: 'text', value: this.configData.app_name || 'Vybe' },
                    { key: 'version', label: 'Version', type: 'text', value: this.configData.version || '1.2.0', readonly: true },
                    { key: 'debug', label: 'Debug Mode', type: 'checkbox', value: this.configData.debug || false }
                ]
            },
            {
                title: 'AI Model Settings',
                fields: [
                    { key: 'default_model', label: 'Default LLM Model', type: 'text', value: this.configData.default_model || 'gemma2:2b' },
                    { key: 'max_tokens', label: 'Max Tokens', type: 'number', value: this.configData.max_tokens || 2048 },
                    { key: 'temperature', label: 'Temperature', type: 'number', value: this.configData.temperature || 0.7, step: 0.1, min: 0, max: 2 }
                ]
            },
            {
                title: 'Feature Toggles',
                fields: [
                    { key: 'enable_rag', label: 'Enable RAG', type: 'checkbox', value: this.configData.features?.rag || true },
                    { key: 'enable_web_search', label: 'Enable Web Search', type: 'checkbox', value: this.configData.features?.web_search || true },
                    { key: 'enable_file_management', label: 'Enable File Management', type: 'checkbox', value: this.configData.features?.file_management || true },
                    { key: 'enable_image_generation', label: 'Enable Image Generation', type: 'checkbox', value: this.configData.features?.image_generation || true }
                ]
            }
        ];

        return sections.map(section => `
            <div class="config-section" style="margin-bottom: 2rem;">
                <h4 style="margin-bottom: 1rem; color: var(--primary-color);">${section.title}</h4>
                <div class="config-fields">
                    ${section.fields.map(field => this.renderConfigField(field)).join('')}
                </div>
            </div>
        `).join('');
    }

    renderConfigField(field) {
        const fieldId = `config-${field.key}`;
        let inputHtml = '';

        switch (field.type) {
            case 'text':
                inputHtml = `<input type="text" id="${fieldId}" value="${field.value || ''}" ${field.readonly ? 'readonly' : ''} class="form-control">`;
                break;
            case 'number':
                inputHtml = `<input type="number" id="${fieldId}" value="${field.value || ''}" ${field.step ? `step="${field.step}"` : ''} ${field.min !== undefined ? `min="${field.min}"` : ''} ${field.max !== undefined ? `max="${field.max}"` : ''} class="form-control">`;
                break;
            case 'checkbox':
                inputHtml = `<input type="checkbox" id="${fieldId}" ${field.value ? 'checked' : ''} class="form-checkbox">`;
                break;
        }

        return `
            <div class="config-field" style="margin-bottom: 1rem;">
                <label for="${fieldId}" style="display: block; margin-bottom: 0.5rem; font-weight: 500;">${field.label}</label>
                ${inputHtml}
            </div>
        `;
    }

    async saveConfiguration(modal) {
        try {
            const updatedConfig = this.collectConfigValues(modal);
            
            const response = await fetch('/api/configuration', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(updatedConfig)
            });

            if (response.ok) {
                const result = await response.json();
                if (result.success) {
                    ApiUtils.showGlobalStatus('Configuration saved successfully!', 'success');
                    await this.loadAppConfiguration(); // Reload config
                    modal.remove();
                } else {
                    throw new Error(result.error || 'Failed to save configuration');
                }
            } else {
                throw new Error('Failed to save configuration');
            }
        } catch (error) {
            console.error('Error saving configuration:', error);
            ApiUtils.showGlobalStatus('Failed to save configuration: ' + error.message, 'error');
        }
    }

    collectConfigValues(modal) {
        const config = { ...this.configData };
        
        // Basic settings
        config.app_name = modal.querySelector('#config-app_name')?.value || config.app_name;
        config.default_model = modal.querySelector('#config-default_model')?.value || config.default_model;
        config.max_tokens = parseInt(modal.querySelector('#config-max_tokens')?.value) || config.max_tokens;
        config.temperature = parseFloat(modal.querySelector('#config-temperature')?.value) || config.temperature;
        config.debug = modal.querySelector('#config-debug')?.checked || false;

        // Features
        if (!config.features) config.features = {};
        config.features.rag = modal.querySelector('#config-enable_rag')?.checked || false;
        config.features.web_search = modal.querySelector('#config-enable_web_search')?.checked || false;
        config.features.file_management = modal.querySelector('#config-enable_file_management')?.checked || false;
        config.features.image_generation = modal.querySelector('#config-enable_image_generation')?.checked || false;

        return config;
    }

    createConfigModal(title, content) {
        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.innerHTML = `
            <div class="modal-content" style="max-width: 800px; max-height: 600px;">
                <div class="modal-header">
                    <h3>${title}</h3>
                    <button class="modal-close">&times;</button>
                </div>
                <div class="modal-body">
                    <pre style="background: var(--surface-color); padding: 1rem; border-radius: 4px; overflow: auto; max-height: 400px; white-space: pre-wrap;">${content}</pre>
                </div>
                <div class="modal-footer">
                    <button class="settings-button secondary modal-close">Close</button>
                </div>
            </div>
        `;

        // Add close event listeners
        modal.querySelectorAll('.modal-close').forEach(btn => {
            window.eventManager.add(btn, 'click', () => modal.remove());
        });

        window.eventManager.add(modal, 'click', (e) => {
            if (e.target === modal) {
                modal.remove();
            }
        });

        return modal;
    }

    getFeatureStatus(featureName) {
        return this.configData?.features?.[featureName] || false;
    }

    getLLMStatus() {
        return this.configData?.llm_backend_status || 'unknown';
    }

    getAppVersion() {
        return this.configData?.version || 'Unknown';
    }

    // Missing method implementations
    showConfigModal() {
        console.log('Showing configuration modal...');
        this.showNotification('Opening configuration view', 'info');
        this.showConfigurationModal();
    }

    createLogsModal() {
        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.id = 'logs-modal';
        modal.innerHTML = `
            <div class="modal-content" style="max-width: 900px; max-height: 700px;">
                <div class="modal-header">
                    <h3>📋 Application Logs</h3>
                    <button class="modal-close">&times;</button>
                </div>
                <div class="modal-body">
                    <div class="logs-controls" style="margin-bottom: 1rem;">
                        <button id="refresh-logs" class="settings-button secondary">Refresh Logs</button>
                        <select id="log-lines" style="margin-left: 10px;">
                            <option value="50">Last 50 lines</option>
                            <option value="100" selected>Last 100 lines</option>
                            <option value="500">Last 500 lines</option>
                            <option value="1000">Last 1000 lines</option>
                        </select>
                    </div>
                    <div id="logs-content" style="background: #1e1e1e; color: #fff; padding: 1rem; border-radius: 4px; height: 400px; overflow-y: auto; font-family: monospace; font-size: 12px; white-space: pre-wrap;">
                        Loading logs...
                    </div>
                </div>
                <div class="modal-footer">
                    <button class="settings-button secondary modal-close">Close</button>
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        // Add event listeners
        modal.querySelectorAll('.modal-close').forEach(btn => {
            window.eventManager.add(btn, 'click', () => {
                modal.style.display = 'none';
                modal.remove();
            });
        });

        const refreshBtn = modal.querySelector('#refresh-logs');
        if (refreshBtn) {
            window.eventManager.add(refreshBtn, 'click', () => {
                const lines = modal.querySelector('#log-lines').value;
                this.loadLogs(parseInt(lines));
            });
        }

        const logLinesSelect = modal.querySelector('#log-lines');
        if (logLinesSelect) {
            window.eventManager.add(logLinesSelect, 'change', (e) => {
                this.loadLogs(parseInt(e.target.value));
            });
        }

        modal.style.display = 'block';
        this.loadLogs(100);
    }

    showNotification(message, type = 'info') {
        console.log(`${type.toUpperCase()}: ${message}`);
        
        // Create toast notification if showToast function exists
        if (typeof window.showToast === 'function') {
            window.showToast(message, type);
        } else if (typeof ApiUtils !== 'undefined' && ApiUtils.showGlobalStatus) {
            ApiUtils.showGlobalStatus(message, type);
        } else {
            // Fallback: create simple notification element
            const notification = document.createElement('div');
            notification.className = `notification notification-${type}`;
            notification.textContent = message;
            notification.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                padding: 12px 20px;
                border-radius: 4px;
                color: white;
                z-index: 10000;
                max-width: 300px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                background: ${type === 'success' ? '#4CAF50' : type === 'error' ? '#f44336' : type === 'warning' ? '#FF9800' : '#2196F3'};
            `;
            
            document.body.appendChild(notification);
            
            // Remove after 3 seconds
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 3000);
        }
    }

    // Enhanced configuration management methods
    async exportConfiguration() {
        console.log('Exporting configuration...');
        this.showNotification('Exporting configuration...', 'info');
        
        if (!this.configData) {
            this.showNotification('No configuration data to export', 'error');
            return;
        }

        try {
            const configJson = JSON.stringify(this.configData, null, 2);
            const blob = new Blob([configJson], { type: 'application/json' });
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `vybe-config-${new Date().toISOString().split('T')[0]}.json`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            this.showNotification('Configuration exported successfully', 'success');
        } catch (error) {
            console.error('Error exporting configuration:', error);
            this.showNotification('Failed to export configuration', 'error');
        }
    }

    async importConfiguration() {
        console.log('Importing configuration...');
        this.showNotification('Select configuration file to import', 'info');
        
        const fileInput = document.createElement('input');
        fileInput.type = 'file';
        fileInput.accept = '.json';
        
        fileInput.addEventListener('change', async (e) => {
            const file = e.target.files[0];
            if (!file) return;
            
            try {
                const text = await file.text();
                const importedConfig = JSON.parse(text);
                
                // Validate imported configuration
                if (!this.validateConfiguration(importedConfig)) {
                    this.showNotification('Invalid configuration file', 'error');
                    return;
                }
                
                // Apply imported configuration
                this.configData = importedConfig;
                await this.saveConfiguration();
                this.displayConfiguration(importedConfig);
                this.showNotification('Configuration imported successfully', 'success');
                
            } catch (error) {
                console.error('Error importing configuration:', error);
                this.showNotification('Failed to import configuration', 'error');
            }
        });
        
        fileInput.click();
    }

    validateConfiguration(config) {
        // Basic validation for required fields
        const requiredFields = ['app_name', 'version'];
        return requiredFields.every(field => Object.prototype.hasOwnProperty.call(config, field));
    }

    async resetConfiguration() {
        console.log('Resetting configuration to defaults...');
        const confirmed = confirm('Are you sure you want to reset configuration to defaults? This action cannot be undone.');
        
        if (!confirmed) return;
        
        try {
            this.showNotification('Resetting configuration...', 'info');
            const response = await fetch('/api/configuration/reset', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            
            if (response.ok) {
                await this.loadAppConfiguration();
                this.showNotification('Configuration reset successfully', 'success');
            } else {
                throw new Error('Failed to reset configuration');
            }
        } catch (error) {
            console.error('Error resetting configuration:', error);
            this.showNotification('Failed to reset configuration', 'error');
        }
    }

    // System diagnostics methods
    async runSystemDiagnostics() {
        console.log('Running system diagnostics...');
        this.showNotification('Running system diagnostics...', 'info');
        
        try {
            const response = await fetch('/api/system/diagnostics');
            if (response.ok) {
                const diagnostics = await response.json();
                this.displayDiagnosticsModal(diagnostics);
                this.showNotification('System diagnostics completed', 'success');
            } else {
                throw new Error('Failed to run diagnostics');
            }
        } catch (error) {
            console.error('Error running diagnostics:', error);
            this.showNotification('Failed to run system diagnostics', 'error');
        }
    }

    displayDiagnosticsModal(diagnostics) {
        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.innerHTML = `
            <div class="modal-content" style="max-width: 800px;">
                <div class="modal-header">
                    <h3>🔧 System Diagnostics</h3>
                    <button class="modal-close">&times;</button>
                </div>
                <div class="modal-body">
                    <div class="diagnostics-results">
                        ${this.renderDiagnosticsResults(diagnostics)}
                    </div>
                </div>
                <div class="modal-footer">
                    <button class="settings-button secondary modal-close">Close</button>
                </div>
            </div>
        `;

        document.body.appendChild(modal);
        
        modal.querySelectorAll('.modal-close').forEach(btn => {
            window.eventManager.add(btn, 'click', () => modal.remove());
        });
        
        modal.style.display = 'flex';
    }

    renderDiagnosticsResults(diagnostics) {
        return Object.entries(diagnostics).map(([category, tests]) => `
            <div class="diagnostic-category" style="margin-bottom: 1.5rem;">
                <h4>${category.replace('_', ' ').toUpperCase()}</h4>
                ${Object.entries(tests).map(([test, result]) => `
                    <div class="diagnostic-item" style="display: flex; justify-content: space-between; padding: 0.5rem; border-left: 3px solid ${result.status === 'pass' ? '#4CAF50' : result.status === 'warning' ? '#FF9800' : '#f44336'}; margin-bottom: 0.5rem; background: var(--surface-color);">
                        <span>${test.replace('_', ' ')}</span>
                        <span class="status ${result.status}" style="font-weight: bold; color: ${result.status === 'pass' ? '#4CAF50' : result.status === 'warning' ? '#FF9800' : '#f44336'};">
                            ${result.status.toUpperCase()}
                        </span>
                    </div>
                `).join('')}
            </div>
        `).join('');
    }

    async clearLogs() {
        console.log('Clearing application logs...');
        const confirmed = confirm('Are you sure you want to clear all application logs? This action cannot be undone.');
        
        if (!confirmed) return;
        
        try {
            this.showNotification('Clearing logs...', 'info');
            const response = await fetch('/api/logs/clear', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            
            if (response.ok) {
                const logsContainer = document.getElementById('logs-content');
                if (logsContainer) {
                    logsContainer.textContent = 'Logs cleared successfully';
                }
                this.showNotification('Logs cleared successfully', 'success');
            } else {
                throw new Error('Failed to clear logs');
            }
        } catch (error) {
            console.error('Error clearing logs:', error);
            this.showNotification('Failed to clear logs', 'error');
        }
    }
}

// Initialize the app config manager
window.appConfigManager = new AppConfigManager();
