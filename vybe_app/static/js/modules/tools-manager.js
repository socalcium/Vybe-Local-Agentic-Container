/**
 * Tools Manager Module
 * Handles tool configuration and toggling
 */

import { ApiUtils } from '../utils/api-utils.js';

export class ToolsManager {
    constructor() {
        this.availableTools = [];
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
        this.loadAvailableTools();
        this.setupEventListeners();
    }

    setupEventListeners() {
        // Tools will be dynamically added, so we'll use event delegation
        window.eventManager.add(document, 'click', (e) => {
            if (e.target.classList.contains('tool-toggle')) {
                const toolName = e.target.dataset.tool;
                const enabled = e.target.checked;
                this.toggleTool(toolName, enabled);
            }
        });
    }

    async loadAvailableTools() {
        try {
            const data = await ApiUtils.safeFetch('/api/tools');
            if (data) {
                this.availableTools = data;
                this.displayTools();
            }
        } catch (error) {
            console.error('Error loading tools:', error);
            const toolsList = document.getElementById('tools-list');
            if (toolsList) {
                toolsList.innerHTML = '<p class="error">Error loading tools.</p>';
            }
        }
    }

    displayTools() {
        const container = document.getElementById('tools-list');
        if (!container) return;

        if (this.availableTools.length === 0) {
            container.innerHTML = '<p>No tools available.</p>';
            return;
        }

        container.innerHTML = this.availableTools.map(tool => `
            <div class="tool-item">
                <div class="tool-header">
                    <h4>${tool.display_name}</h4>
                    <label class="toggle-switch">
                        <input type="checkbox" class="tool-toggle" 
                               data-tool="${tool.name}" 
                               ${tool.enabled ? 'checked' : ''}>
                        <span class="toggle-slider"></span>
                    </label>
                </div>
                <p class="tool-description">${tool.description}</p>
                <div class="tool-status">
                    <span class="status-indicator ${tool.enabled ? 'enabled' : 'disabled'}">
                        ${tool.enabled ? 'Enabled' : 'Disabled'}
                    </span>
                </div>
            </div>
        `).join('');
    }

    async toggleTool(toolName, enabled) {
        try {
            const data = await ApiUtils.safeFetch('/api/tools/toggle', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ 
                    tool_name: toolName, 
                    enabled: enabled 
                })
            });

            if (data && data.success) {
                ApiUtils.showGlobalStatus(
                    `Tool ${toolName} ${enabled ? 'enabled' : 'disabled'} successfully`,
                    'success'
                );
                // Update local state
                const tool = this.availableTools.find(t => t.name === toolName);
                if (tool) {
                    tool.enabled = enabled;
                }
                this.displayTools();
            } else {
                ApiUtils.showGlobalStatus('Failed to update tool status', 'error');
                // Revert the toggle
                const toggle = document.querySelector(`[data-tool="${toolName}"]`);
                if (toggle) {
                    toggle.checked = !enabled;
                }
            }
        } catch (error) {
            console.error('Error toggling tool:', error);
            ApiUtils.showGlobalStatus('Error updating tool status', 'error');
            // Revert the toggle
            const toggle = document.querySelector(`[data-tool="${toolName}"]`);
            if (toggle) {
                toggle.checked = !enabled;
            }
        }
    }

    getToolStatus(toolName) {
        const tool = this.availableTools.find(t => t.name === toolName);
        return tool ? tool.enabled : false;
    }

    getAllTools() {
        return this.availableTools;
    }
}
