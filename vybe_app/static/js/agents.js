/**
 * Autonomous Agents Workspace JavaScript Module
 * Handles agent creation, management, and real-time monitoring
 */

// Safety check for Bootstrap
if (typeof window.bootstrap === 'undefined') {
    console.warn('Bootstrap is not defined. Using placeholder for modals.');
    window.bootstrap = {
        Modal: class {
            constructor(element) { this.element = element; console.log('Placeholder Modal created for:', this.element); }
            show() { console.log('Placeholder Modal show().'); }
            hide() { console.log('Placeholder Modal hide().'); }
        },
        Toast: class {
            constructor(element) { this.element = element; console.log('Placeholder Toast created for:', this.element); }
            show() { console.log('Placeholder Toast show().'); }
            hide() { console.log('Placeholder Toast hide().'); }
        }
    };
}

class AgentWorkspace {
    constructor() {
        this.currentAgentId = null;
        this.autoScroll = true;
        this.pollingInterval = null;
        this.logPollingInterval = null;
        this.availableTools = [];
        this.systemPrompts = [];
        this.eventListeners = []; // Track event listeners for cleanup
        
        // Cleanup functions for event listeners
        this.cleanupFunctions = [];
        
        this.init();
    }

    // Utility functions to safely update DOM content
    createElementSafely(tagName, className = '', textContent = '') {
        const element = document.createElement(tagName);
        if (className) element.className = className;
        if (textContent) element.textContent = textContent;
        return element;
    }

    createStatusMessage(message, isError = false) {
        const fragment = document.createDocumentFragment();
        const container = this.createElementSafely('p', isError ? 'text-danger' : 'text-muted', message);
        fragment.appendChild(container);
        return fragment;
    }

    replaceContent(element, newContent) {
        while (element.firstChild) {
            element.removeChild(element.firstChild);
        }
        element.appendChild(newContent);
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
        console.log('Initializing Agent Workspace...');
        
        // Initialize DOM elements
        this.initializeElements();
        
        // Set up event listeners
        this.setupEventListeners();
        
        // Load initial data
        this.loadAvailableTools();
        this.loadSystemPrompts();
        this.loadAgentsList();
        
        // Start periodic updates
        this.startPolling();
        
        // Cleanup on page unload
        window.eventManager.add(window, 'beforeunload', () => {
            this.cleanup();
        });
    }
    
    cleanup() {
        // Clear all polling intervals
        if (this.pollingInterval) {
            clearInterval(this.pollingInterval);
            this.pollingInterval = null;
        }
        if (this.logPollingInterval) {
            clearInterval(this.logPollingInterval);
            this.logPollingInterval = null;
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
        // Form elements
        this.agentForm = document.getElementById('agent-creation-form');
        this.objectiveInput = document.getElementById('agent-objective');
        this.systemPromptSelect = document.getElementById('system-prompt-select');
        this.toolsChecklist = document.getElementById('tools-checklist');
        this.createBtn = document.getElementById('create-agent-btn');
        
        // Agent list elements
        this.agentsList = document.getElementById('agents-list');
        this.refreshAgentsBtn = document.getElementById('refresh-agents-btn');
        
        // Monitoring elements
        this.agentStatusSummary = document.getElementById('agent-status-summary');
        this.currentAgentName = document.getElementById('current-agent-name');
        this.currentAgentObjective = document.getElementById('current-agent-objective');
        this.agentStatusBadge = document.getElementById('agent-status-badge');
        this.agentProgress = document.getElementById('agent-progress');
        this.agentActionsCount = document.getElementById('agent-actions-count');
        
        // Control buttons
        this.startBtn = document.getElementById('start-agent-btn');
        this.pauseBtn = document.getElementById('pause-agent-btn');
        this.resumeBtn = document.getElementById('resume-agent-btn');
        this.stopBtn = document.getElementById('stop-agent-btn');
        
        // Log elements
        this.liveLogContainer = document.getElementById('live-log-container');
        this.clearLogsBtn = document.getElementById('clear-logs-btn');
        this.autoScrollToggle = document.getElementById('auto-scroll-toggle');
        
        // Toast
        this.toast = new window.bootstrap.Toast(document.getElementById('agents-toast'));
    }

    setupEventListeners() {
        // Agent creation form
        window.eventManager.add(this.agentForm, 'submit', (e) => {
            this.handleAgentCreation(e);
        });

        // Agent list refresh
        window.eventManager.add(this.refreshAgentsBtn, 'click', () => {
            this.loadAgentsList();
        });

        // Agent control buttons
        window.eventManager.add(this.startBtn, 'click', () => {
            this.startAgent();
        });
        
        window.eventManager.add(this.pauseBtn, 'click', () => {
            this.pauseAgent();
        });
        
        window.eventManager.add(this.resumeBtn, 'click', () => {
            this.resumeAgent();
        });
        
        window.eventManager.add(this.stopBtn, 'click', () => {
            this.stopAgent();
        });

        // Log controls
        window.eventManager.add(this.clearLogsBtn, 'click', () => {
            this.clearLogs();
        });

        window.eventManager.add(this.autoScrollToggle, 'click', () => {
            this.toggleAutoScroll();
        });
    }

    async handleAgentCreation(e) {
        e.preventDefault();
        await this.createAgent();
    }

    async loadAvailableTools() {
        try {
            const response = await fetch('/api/agents/available-tools');
            const data = await response.json();
            
            if (data.success) {
                this.availableTools = data.tools;
                this.renderToolsChecklist();
            } else {
                this.showToast('error', 'Failed to load available tools');
            }

        } catch (error) {
            console.error('Error loading tools:', error);
            this.showToast('error', 'Failed to load available tools. Please check your connection and try again.');
        }
    }

    renderToolsChecklist() {
        if (this.availableTools.length === 0) {
            this.replaceContent(this.toolsChecklist, this.createStatusMessage('No tools available'));
            return;
        }

        const fragment = document.createDocumentFragment();
        
        this.availableTools.forEach(tool => {
            const toolDiv = this.createElementSafely('div', 'tool-option');
            
            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.className = 'form-check-input tool-checkbox';
            checkbox.id = `tool-${tool.id}`;
            checkbox.value = tool.id;
            
            const toolInfo = this.createElementSafely('div', 'tool-info');
            const toolName = this.createElementSafely('div', 'tool-name', tool.name);
            const toolDescription = this.createElementSafely('p', 'tool-description', tool.description);
            
            toolInfo.appendChild(toolName);
            toolInfo.appendChild(toolDescription);
            
            toolDiv.appendChild(checkbox);
            toolDiv.appendChild(toolInfo);
            fragment.appendChild(toolDiv);
        });

        this.replaceContent(this.toolsChecklist, fragment);
    }

    async loadSystemPrompts() {
        try {
            const response = await fetch('/api/agents/system-prompts');
            const data = await response.json();
            
            if (data.success) {
                this.systemPrompts = data.prompts;
                this.renderSystemPromptSelect();
            } else {
                this.showToast('error', 'Failed to load system prompts');
            }

        } catch (error) {
            console.error('Error loading system prompts:', error);
            this.showToast('error', 'Failed to load system prompts. Please check your connection and try again.');
        }
    }

    renderSystemPromptSelect() {
        const fragment = document.createDocumentFragment();
        
        const defaultOption = document.createElement('option');
        defaultOption.value = '';
        defaultOption.textContent = 'Select a persona...';
        fragment.appendChild(defaultOption);
        
        this.systemPrompts.forEach(prompt => {
            const option = document.createElement('option');
            option.value = prompt.content;
            option.textContent = prompt.name;
            option.title = prompt.description;
            fragment.appendChild(option);
        });

        this.replaceContent(this.systemPromptSelect, fragment);
    }

    async createAgent() {
        const objective = this.objectiveInput.value.trim();
        const systemPrompt = this.systemPromptSelect.value;
        const authorizedTools = this.getSelectedTools();

        // Input validation
        if (!objective) {
            this.showError('Please enter an agent objective');
            return;
        }
        
        if (objective.length > 2000) {
            this.showError('Agent objective is too long. Please keep it under 2000 characters.');
            return;
        }
        
        if (!systemPrompt) {
            this.showError('Please select a system prompt');
            return;
        }
        
        if (!authorizedTools || authorizedTools.length === 0) {
            this.showError('Please select at least one authorized tool');
            return;
        }
        
        // Basic content filtering
        if (this.containsHarmfulContent(objective)) {
            this.showError('Agent objective contains potentially inappropriate content. Please revise.');
            return;
        }

        this.createBtn.disabled = true;
        while (this.createBtn.firstChild) {
            this.createBtn.removeChild(this.createBtn.firstChild);
        }
        const spinner = this.createElementSafely('span', 'spinner-border spinner-border-sm me-2');
        this.createBtn.appendChild(spinner);
        this.createBtn.appendChild(document.createTextNode('Creating...'));

        try {
            // Get CSRF token from form
            const csrfToken = document.querySelector('input[name="csrf_token"]')?.value;

            const response = await fetch('/api/agents/create', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({
                    objective: objective,
                    system_prompt: systemPrompt,
                    authorized_tools: authorizedTools
                })
            });

            const data = await response.json();

            if (data.success) {
                this.showSuccess('Agent created successfully!');
                this.objectiveInput.value = '';
                this.loadAgentsList();
            } else {
                this.showError(data.error || 'Failed to create agent');
            }
        } catch (error) {
            console.error('Error creating agent:', error);
            this.showError('Failed to create agent. Please check your connection and try again.');
        } finally {
            this.createBtn.disabled = false;
            while (this.createBtn.firstChild) {
                this.createBtn.removeChild(this.createBtn.firstChild);
            }
            const icon = this.createElementSafely('i', 'bi bi-robot');
            this.createBtn.appendChild(icon);
            this.createBtn.appendChild(document.createTextNode(' Create Agent'));
        }
    }
    
    containsHarmfulContent(text) {
        // Basic content filtering - this could be enhanced with more sophisticated checks
        const harmfulPatterns = [
            /\b(kill|murder|suicide|torture|abuse)\b/i,
            /\b(nazi|hitler|racist|hate)\b/i,
            /\b(sex|porn|nude|explicit)\b/i
        ];
        
        return harmfulPatterns.some(pattern => pattern.test(text));
    }

    clearForm() {
        this.objectiveInput.value = '';
        this.systemPromptSelect.value = '';
        document.querySelectorAll('.tool-checkbox').forEach(cb => cb.checked = false);
    }

    async loadAgentsList() {
        try {
            const response = await fetch('/api/agents/list');
            const data = await response.json();
            
            if (data.success) {
                this.renderAgentsList(data.agents);
            } else {
                this.replaceContent(this.agentsList, this.createStatusMessage('Failed to load agents'));
            }

        } catch (error) {
            console.error('Error loading agents:', error);
            this.replaceContent(this.agentsList, this.createStatusMessage('Error loading agents'));
            this.showToast('error', 'Failed to load agents. Please check your connection and try again.');
        }
    }

    renderAgentsList(agents) {
        if (agents.length === 0) {
            this.replaceContent(this.agentsList, this.createStatusMessage('No agents created yet'));
            return;
        }

        const fragment = document.createDocumentFragment();
        
        agents.forEach(agent => {
            const agentDiv = this.createElementSafely('div', 'agent-item');
            if (agent.id === this.currentAgentId) {
                agentDiv.classList.add('selected');
            }
            
            const createdDate = new Date(agent.created_at).toLocaleString();
            
            const agentName = this.createElementSafely('div', 'agent-name', agent.id);
            const agentObjective = this.createElementSafely('div', 'agent-objective', agent.objective);
            
            const agentMeta = this.createElementSafely('div', 'agent-meta');
            const agentStatus = this.createElementSafely('span', `agent-status ${agent.status}`, agent.status);
            const agentTimestamp = this.createElementSafely('span', 'agent-timestamp', createdDate);
            agentMeta.appendChild(agentStatus);
            agentMeta.appendChild(agentTimestamp);
            
            agentDiv.appendChild(agentName);
            agentDiv.appendChild(agentObjective);
            agentDiv.appendChild(agentMeta);
            
            window.eventManager.add(agentDiv, 'click', () => {
                this.selectAgent(agent.id);
            });
            
            fragment.appendChild(agentDiv);
        });

        this.replaceContent(this.agentsList, fragment);
    }

    async selectAgent(agentId) {
        // Update visual selection
        document.querySelectorAll('.agent-item').forEach(item => {
            item.classList.remove('selected');
        });
        
        const selectedItem = [...document.querySelectorAll('.agent-item')]
            .find(item => item.querySelector('.agent-name').textContent === agentId);
        if (selectedItem) {
            selectedItem.classList.add('selected');
        }

        this.currentAgentId = agentId;
        
        // Load agent details
        await this.loadAgentStatus(agentId);
        await this.loadAgentLogs(agentId);
        
        // Show status summary
        this.agentStatusSummary.style.display = 'block';
        
        // Start log polling for this agent
        this.startLogPolling();
    }

    async loadAgentStatus(agentId) {
        try {
            const response = await fetch(`/api/agents/status/${agentId}`);
            const data = await response.json();
            
            if (data.success) {
                this.updateAgentStatusDisplay(data.agent);
            }

        } catch (error) {
            console.error('Error loading agent status:', error);
            this.showToast('error', 'Failed to load agent status. Please try again.');
        }
    }

    updateAgentStatusDisplay(agent) {
        this.currentAgentName.textContent = agent.id;
        this.currentAgentObjective.textContent = agent.objective;
        
        // Update status badge
        this.agentStatusBadge.className = `badge bg-${this.getStatusColor(agent.status)}`;
        this.agentStatusBadge.textContent = agent.status;
        
        // Update progress
        this.agentProgress.textContent = `${agent.completed_steps}/${agent.total_steps} steps`;
        this.agentActionsCount.textContent = agent.actions_count;
        
        // Update control buttons
        this.updateControlButtons(agent.status);
    }

    getStatusColor(status) {
        const colors = {
            'idle': 'secondary',
            'planning': 'info',
            'executing': 'warning',
            'completed': 'success',
            'failed': 'danger',
            'paused': 'warning'
        };
        return colors[status] || 'secondary';
    }

    updateControlButtons(status) {
        // Reset all buttons
        this.startBtn.disabled = true;
        this.pauseBtn.disabled = true;
        this.resumeBtn.disabled = true;
        this.stopBtn.disabled = true;
        
        switch (status) {
            case 'idle':
                this.startBtn.disabled = false;
                break;
            case 'planning':
            case 'executing':
                this.pauseBtn.disabled = false;
                this.stopBtn.disabled = false;
                break;
            case 'paused':
                this.resumeBtn.disabled = false;
                this.stopBtn.disabled = false;
                break;
        }
    }

    async loadAgentLogs(agentId) {
        try {
            const response = await fetch(`/api/agents/logs/${agentId}?limit=20`);
            const data = await response.json();
            
            if (data.success) {
                this.renderLogs(data.logs);
            }

        } catch (error) {
            console.error('Error loading agent logs:', error);
            this.showToast('error', 'Failed to load agent logs. Please try again.');
        }
    }

    renderLogs(logs) {
        // Clear existing logs except system message
        const systemMessage = this.liveLogContainer.querySelector('.system-message');
        while (this.liveLogContainer.firstChild) {
            this.liveLogContainer.removeChild(this.liveLogContainer.firstChild);
        }
        if (systemMessage) {
            this.liveLogContainer.appendChild(systemMessage);
        }
        
        logs.forEach(log => {
            this.addLogEntryFromData(log);
        });
        
        if (this.autoScroll) {
            this.scrollToBottom();
        }
    }

    addLogEntry(type, action, message) {
        const timestamp = new Date().toLocaleTimeString();
        
        const logDiv = this.createElementSafely('div', `log-entry ${type}`);
        
        const timestampDiv = this.createElementSafely('div', 'log-timestamp', timestamp);
        const contentDiv = this.createElementSafely('div', 'log-content');
        
        const strongText = this.createElementSafely('strong', '', action + ': ');
        contentDiv.appendChild(strongText);
        contentDiv.appendChild(document.createTextNode(message));
        
        logDiv.appendChild(timestampDiv);
        logDiv.appendChild(contentDiv);
        
        this.liveLogContainer.appendChild(logDiv);
        
        if (this.autoScroll) {
            this.scrollToBottom();
        }
    }

    addLogEntryFromData(logData) {
        const timestamp = new Date(logData.timestamp).toLocaleTimeString();
        
        const logDiv = this.createElementSafely('div', `log-entry ${logData.action_type}`);
        
        const icon = logData.success ? '✓' : '✗';
        const statusClass = logData.success ? 'success' : 'error';
        
        const timestampDiv = this.createElementSafely('div', 'log-timestamp', timestamp);
        const contentDiv = this.createElementSafely('div', `log-content ${statusClass}`);
        
        const iconSpan = this.createElementSafely('span', 'log-icon', icon);
        const strongText = this.createElementSafely('strong', '', logData.tool_name + ': ');
        contentDiv.appendChild(iconSpan);
        contentDiv.appendChild(strongText);
        contentDiv.appendChild(document.createTextNode(logData.result));
        
        if (logData.execution_time > 0) {
            const timeText = this.createElementSafely('small', '', ` (${logData.execution_time.toFixed(2)}s)`);
            contentDiv.appendChild(timeText);
        }
        
        logDiv.appendChild(timestampDiv);
        logDiv.appendChild(contentDiv);
        
        this.liveLogContainer.appendChild(logDiv);
    }

    clearLogs() {
        const fragment = document.createDocumentFragment();
        const logEntry = this.createElementSafely('div', 'log-entry system-message');
        
        const timestamp = this.createElementSafely('div', 'log-timestamp', 'Ready');
        const content = this.createElementSafely('div', 'log-content');
        
        const icon = this.createElementSafely('i', 'bi bi-info-circle');
        content.appendChild(icon);
        content.appendChild(document.createTextNode(' Logs cleared. Select an agent to monitor its activity.'));
        
        logEntry.appendChild(timestamp);
        logEntry.appendChild(content);
        fragment.appendChild(logEntry);
        
        this.replaceContent(this.liveLogContainer, fragment);
    }

    toggleAutoScroll() {
        this.autoScroll = !this.autoScroll;
        
        while (this.autoScrollToggle.firstChild) {
            this.autoScrollToggle.removeChild(this.autoScrollToggle.firstChild);
        }
        
        if (this.autoScroll) {
            const icon = this.createElementSafely('i', 'bi bi-arrow-down');
            this.autoScrollToggle.appendChild(icon);
            this.autoScrollToggle.appendChild(document.createTextNode(' Auto-scroll'));
        } else {
            const icon = this.createElementSafely('i', 'bi bi-pause');
            this.autoScrollToggle.appendChild(icon);
            this.autoScrollToggle.appendChild(document.createTextNode(' Manual'));
        }
            
        if (this.autoScroll) {
            this.scrollToBottom();
        }
    }

    scrollToBottom() {
        this.liveLogContainer.scrollTop = this.liveLogContainer.scrollHeight;
    }

    async startAgent(agentId) {
        try {
            const response = await fetch(`/api/agents/start/${agentId}`, {
                method: 'POST'
            });
            const data = await response.json();
            
            if (data.success) {
                this.showToast('success', data.message);
                this.addLogEntry('system', 'Agent Started', `Agent ${agentId} has been dispatched`);
                await this.loadAgentStatus(agentId);
            } else {
                this.showToast('error', data.error);
            }

        } catch (error) {
            console.error('Error starting agent:', error);
            this.showToast('error', 'Failed to start agent. Please check your connection and try again.');
        }
    }

    async pauseAgent(agentId) {
        try {
            const response = await fetch(`/api/agents/pause/${agentId}`, {
                method: 'POST'
            });
            const data = await response.json();
            
            if (data.success) {
                this.showToast('success', data.message);
                this.addLogEntry('system', 'Agent Paused', `Agent ${agentId} has been paused`);
                await this.loadAgentStatus(agentId);
            } else {
                this.showToast('error', data.error);
            }

        } catch (error) {
            console.error('Error pausing agent:', error);
            this.showToast('error', 'Failed to pause agent. Please check your connection and try again.');
        }
    }

    async resumeAgent(agentId) {
        try {
            const response = await fetch(`/api/agents/resume/${agentId}`, {
                method: 'POST'
            });
            const data = await response.json();
            
            if (data.success) {
                this.showToast('success', data.message);
                this.addLogEntry('system', 'Agent Resumed', `Agent ${agentId} has been resumed`);
                await this.loadAgentStatus(agentId);
            } else {
                this.showToast('error', data.error);
            }

        } catch (error) {
            console.error('Error resuming agent:', error);
            this.showToast('error', 'Failed to resume agent. Please check your connection and try again.');
        }
    }

    async stopAgent(agentId) {
        try {
            const response = await fetch(`/api/agents/stop/${agentId}`, {
                method: 'POST'
            });
            const data = await response.json();
            
            if (data.success) {
                this.showToast('success', data.message);
                this.addLogEntry('system', 'Agent Stopped', `Agent ${agentId} has been stopped`);
                await this.loadAgentStatus(agentId);
            } else {
                this.showToast('error', data.error);
            }

        } catch (error) {
            console.error('Error stopping agent:', error);
            this.showToast('error', 'Failed to stop agent. Please check your connection and try again.');
        }
    }

    startPolling() {
        // Poll agents list every 10 seconds
        this.pollingInterval = setInterval(() => {
            this.loadAgentsList();
            if (this.currentAgentId) {
                this.loadAgentStatus(this.currentAgentId);
            }
        }, 10000);
    }

    startLogPolling() {
        // Clear existing log polling
        if (this.logPollingInterval) {
            clearInterval(this.logPollingInterval);
        }
        
        // Poll logs every 2 seconds for active agent
        this.logPollingInterval = setInterval(() => {
            if (this.currentAgentId) {
                this.loadAgentLogs(this.currentAgentId);
            }
        }, 2000);
    }

    showToast(type, message) {
        const toastBody = document.querySelector('#agents-toast .toast-body');
        const toastHeader = document.querySelector('#agents-toast .toast-header strong');
        
        toastBody.textContent = message;
        
        // Clear existing content
        while (toastHeader.firstChild) {
            toastHeader.removeChild(toastHeader.firstChild);
        }
        
        if (type === 'error') {
            const icon = this.createElementSafely('i', 'bi bi-exclamation-triangle me-2');
            toastHeader.appendChild(icon);
            toastHeader.appendChild(document.createTextNode('Error'));
            toastBody.className = 'toast-body text-danger';
        } else {
            const icon = this.createElementSafely('i', 'bi bi-check-circle me-2');
            toastHeader.appendChild(icon);
            toastHeader.appendChild(document.createTextNode('Success'));
            toastBody.className = 'toast-body text-success';
        }
        
        this.toast.show();
    }

    showError(message) {
        this.showToast('error', message);
    }

    showSuccess(message) {
        this.showToast('success', message);
    }

    getSelectedTools() {
        return Array.from(document.querySelectorAll('.tool-checkbox:checked'))
            .map(cb => cb.value);
    }
}

// Initialize Agent Workspace when DOM is loaded
window.eventManager.add(document, 'DOMContentLoaded', () => {
    window.agentWorkspace = new AgentWorkspace();
    
    // Cleanup on page unload
    window.eventManager.add(window, 'beforeunload', () => {
        if (window.agentWorkspace) {
            window.agentWorkspace.destroy();
        }
    });
});
