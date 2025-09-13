/**
 * Multi-modal AI Workflow Automation
 * Orchestrates complex tasks across different AI models and modalities
 */

export class WorkflowAutomation {
    constructor() {
        this.workflows = new Map();
        this.activeWorkflows = new Map();
        this.workflowTemplates = new Map();
        this.currentWorkflow = null;
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
        this.loadWorkflowTemplates();
        this.setupEventListeners();
        this.initializeUI();
    }

    setupEventListeners() {
        // Workflow creation
        const createWorkflowBtn = document.getElementById('create-workflow');
        if (createWorkflowBtn) {
            window.eventManager.add(createWorkflowBtn, 'click', () => this.createNewWorkflow());
        }

        // Workflow execution
        const executeWorkflowBtn = document.getElementById('execute-workflow');
        if (executeWorkflowBtn) {
            window.eventManager.add(executeWorkflowBtn, 'click', () => this.executeWorkflow());
        }

        // Template selection
        const templateSelector = document.getElementById('workflow-template-selector');
        if (templateSelector) {
            window.eventManager.add(templateSelector, 'change', (e) => this.loadTemplate(e.target.value));
        }
    }

    initializeUI() {
        this.createWorkflowBuilder();
        this.createWorkflowLibrary();
        this.createExecutionPanel();
        this.createMonitoringDashboard();
    }

    createWorkflowBuilder() {
        const builderContainer = document.getElementById('workflow-builder');
        if (!builderContainer) return;

        builderContainer.innerHTML = `
            <div class="workflow-builder-header">
                <h3>Workflow Builder</h3>
                <div class="builder-controls">
                    <button id="save-workflow" class="btn btn-primary">Save Workflow</button>
                    <button id="test-workflow" class="btn btn-info">Test Workflow</button>
                    <button id="export-workflow" class="btn btn-secondary">Export</button>
                </div>
            </div>
            <div class="workflow-canvas">
                <div class="canvas-toolbar">
                    <div class="tool-group">
                        <h4>AI Models</h4>
                        <div class="tool-item" data-type="llm" draggable="true">
                            <i class="fas fa-brain"></i>
                            <span>LLM Task</span>
                        </div>
                        <div class="tool-item" data-type="image" draggable="true">
                            <i class="fas fa-image"></i>
                            <span>Image Generation</span>
                        </div>
                        <div class="tool-item" data-type="audio" draggable="true">
                            <i class="fas fa-microphone"></i>
                            <span>Audio Processing</span>
                        </div>
                        <div class="tool-item" data-type="rag" draggable="true">
                            <i class="fas fa-search"></i>
                            <span>RAG Query</span>
                        </div>
                    </div>
                    <div class="tool-group">
                        <h4>Data Processing</h4>
                        <div class="tool-item" data-type="transform" draggable="true">
                            <i class="fas fa-cogs"></i>
                            <span>Data Transform</span>
                        </div>
                        <div class="tool-item" data-type="filter" draggable="true">
                            <i class="fas fa-filter"></i>
                            <span>Filter Data</span>
                        </div>
                        <div class="tool-item" data-type="merge" draggable="true">
                            <i class="fas fa-object-group"></i>
                            <span>Merge Results</span>
                        </div>
                    </div>
                    <div class="tool-group">
                        <h4>Control Flow</h4>
                        <div class="tool-item" data-type="condition" draggable="true">
                            <i class="fas fa-code-branch"></i>
                            <span>Condition</span>
                        </div>
                        <div class="tool-item" data-type="loop" draggable="true">
                            <i class="fas fa-redo"></i>
                            <span>Loop</span>
                        </div>
                        <div class="tool-item" data-type="delay" draggable="true">
                            <i class="fas fa-clock"></i>
                            <span>Delay</span>
                        </div>
                    </div>
                </div>
                <div class="canvas-area" id="workflow-canvas">
                    <div class="canvas-placeholder">
                        <i class="fas fa-plus-circle"></i>
                        <p>Drag and drop components to build your workflow</p>
                    </div>
                </div>
            </div>
            <div class="workflow-properties" id="workflow-properties">
                <h4>Properties</h4>
                <div class="properties-content">
                    <p>Select a component to configure its properties</p>
                </div>
            </div>
        `;

        this.setupCanvasDragAndDrop();
    }

    createWorkflowLibrary() {
        const libraryContainer = document.getElementById('workflow-library');
        if (!libraryContainer) return;

        libraryContainer.innerHTML = `
            <div class="workflow-library-header">
                <h3>Workflow Library</h3>
                <div class="library-filters">
                    <select id="workflow-category-filter">
                        <option value="">All Categories</option>
                        <option value="content-creation">Content Creation</option>
                        <option value="data-analysis">Data Analysis</option>
                        <option value="automation">Automation</option>
                        <option value="research">Research</option>
                    </select>
                    <input type="text" id="workflow-search" placeholder="Search workflows...">
                </div>
            </div>
            <div class="workflow-grid" id="workflow-grid"></div>
        `;

        this.loadWorkflows();
    }

    createExecutionPanel() {
        const executionContainer = document.getElementById('execution-panel');
        if (!executionContainer) return;

        executionContainer.innerHTML = `
            <div class="execution-header">
                <h3>Workflow Execution</h3>
                <div class="execution-controls">
                    <button id="start-execution" class="btn btn-success">Start</button>
                    <button id="pause-execution" class="btn btn-warning" disabled>Pause</button>
                    <button id="stop-execution" class="btn btn-danger" disabled>Stop</button>
                </div>
            </div>
            <div class="execution-status">
                <div class="status-indicator">
                    <span class="status-label">Status:</span>
                    <span class="status-value" id="execution-status">Ready</span>
                </div>
                <div class="progress-container">
                    <div class="progress-bar">
                        <div class="progress-fill" id="execution-progress"></div>
                    </div>
                    <span class="progress-text" id="progress-text">0%</span>
                </div>
            </div>
            <div class="execution-log" id="execution-log">
                <div class="log-header">
                    <h4>Execution Log</h4>
                    <button id="clear-log" class="btn btn-sm btn-secondary">Clear</button>
                </div>
                <div class="log-content" id="log-content"></div>
            </div>
        `;

        this.setupExecutionControls();
    }

    createMonitoringDashboard() {
        const monitoringContainer = document.getElementById('monitoring-dashboard');
        if (!monitoringContainer) return;

        monitoringContainer.innerHTML = `
            <div class="monitoring-header">
                <h3>Workflow Monitoring</h3>
                <div class="monitoring-controls">
                    <button id="refresh-metrics" class="btn btn-info">Refresh</button>
                    <button id="export-metrics" class="btn btn-secondary">Export</button>
                </div>
            </div>
            <div class="metrics-grid">
                <div class="metric-card">
                    <h4>Active Workflows</h4>
                    <div class="metric-value" id="active-workflows-count">0</div>
                </div>
                <div class="metric-card">
                    <h4>Completed Today</h4>
                    <div class="metric-value" id="completed-today">0</div>
                </div>
                <div class="metric-card">
                    <h4>Success Rate</h4>
                    <div class="metric-value" id="success-rate">0%</div>
                </div>
                <div class="metric-card">
                    <h4>Avg Execution Time</h4>
                    <div class="metric-value" id="avg-execution-time">0s</div>
                </div>
            </div>
            <div class="workflow-history">
                <h4>Recent Executions</h4>
                <div class="history-list" id="workflow-history"></div>
            </div>
        `;

        this.loadMonitoringData();
    }

    setupCanvasDragAndDrop() {
        const canvas = document.getElementById('workflow-canvas');
        const toolItems = document.querySelectorAll('.tool-item');

        toolItems.forEach(item => {
            window.eventManager.add(item, 'dragstart', (e) => {
                e.dataTransfer.setData('text/plain', item.dataset.type);
                e.dataTransfer.effectAllowed = 'copy';
            });
        });

        window.eventManager.add(canvas, 'dragover', (e) => {
            e.preventDefault();
            e.dataTransfer.dropEffect = 'copy';
            canvas.classList.add('drag-over');
        });

        window.eventManager.add(canvas, 'dragleave', (e) => {
            if (!canvas.contains(e.relatedTarget)) {
                canvas.classList.remove('drag-over');
            }
        });

        window.eventManager.add(canvas, 'drop', (e) => {
            e.preventDefault();
            canvas.classList.remove('drag-over');
            const type = e.dataTransfer.getData('text/plain');
            const rect = canvas.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            this.addComponentToCanvas(type, x, y);
        });
    }

    addComponentToCanvas(type, x, y) {
        const canvas = document.getElementById('workflow-canvas');
        const component = this.createComponent(type, x, y);
        
        canvas.appendChild(component);
        this.connectComponents();
    }

    createComponent(type, x, y) {
        const component = document.createElement('div');
        component.className = 'workflow-component';
        component.dataset.type = type;
        component.style.left = x + 'px';
        component.style.top = y + 'px';
        
        const iconMap = {
            'llm': 'fas fa-brain',
            'image': 'fas fa-image',
            'audio': 'fas fa-microphone',
            'rag': 'fas fa-search',
            'transform': 'fas fa-cogs',
            'filter': 'fas fa-filter',
            'merge': 'fas fa-object-group',
            'condition': 'fas fa-code-branch',
            'loop': 'fas fa-redo',
            'delay': 'fas fa-clock'
        };

        component.innerHTML = `
            <div class="component-header">
                <i class="${iconMap[type] || 'fas fa-cube'}"></i>
                <span class="component-title">${this.getComponentTitle(type)}</span>
                <button class="component-remove" onclick="this.parentElement.parentElement.remove()">
                    <i class="fas fa-times"></i>
                </button>
            </div>
            <div class="component-body">
                <div class="component-inputs">
                    <div class="input-port" data-port="input"></div>
                </div>
                <div class="component-outputs">
                    <div class="output-port" data-port="output"></div>
                </div>
            </div>
        `;

        window.eventManager.add(component, 'click', () => this.selectComponent(component));
        return component;
    }

    getComponentTitle(type) {
        const titles = {
            'llm': 'LLM Task',
            'image': 'Image Generation',
            'audio': 'Audio Processing',
            'rag': 'RAG Query',
            'transform': 'Data Transform',
            'filter': 'Filter Data',
            'merge': 'Merge Results',
            'condition': 'Condition',
            'loop': 'Loop',
            'delay': 'Delay'
        };
        return titles[type] || 'Component';
    }

    selectComponent(component) {
        // Remove previous selection
        document.querySelectorAll('.workflow-component').forEach(c => c.classList.remove('selected'));
        component.classList.add('selected');
        
        // Show properties panel
        this.showComponentProperties(component);
    }

    showComponentProperties(component) {
        const propertiesPanel = document.getElementById('workflow-properties');
        const type = component.dataset.type;
        
        propertiesPanel.innerHTML = `
            <h4>${this.getComponentTitle(type)} Properties</h4>
            <div class="properties-content">
                ${this.getComponentPropertiesHTML(type)}
            </div>
        `;
    }

    getComponentPropertiesHTML(type) {
        const properties = {
            'llm': `
                <div class="property-group">
                    <label>Model:</label>
                    <select id="llm-model">
                        <option value="llama2">Llama 2</option>
                        <option value="gpt4">GPT-4</option>
                        <option value="claude">Claude</option>
                    </select>
                </div>
                <div class="property-group">
                    <label>Temperature:</label>
                    <input type="range" id="llm-temperature" min="0" max="2" step="0.1" value="0.7">
                    <span id="temp-display">0.7</span>
                </div>
                <div class="property-group">
                    <label>Max Tokens:</label>
                    <input type="number" id="llm-max-tokens" min="100" max="4000" value="1000">
                </div>
            `,
            'image': `
                <div class="property-group">
                    <label>Model:</label>
                    <select id="image-model">
                        <option value="stable-diffusion">Stable Diffusion</option>
                        <option value="dall-e">DALL-E</option>
                    </select>
                </div>
                <div class="property-group">
                    <label>Size:</label>
                    <select id="image-size">
                        <option value="512x512">512x512</option>
                        <option value="1024x1024">1024x1024</option>
                    </select>
                </div>
            `,
            'condition': `
                <div class="property-group">
                    <label>Condition Type:</label>
                    <select id="condition-type">
                        <option value="equals">Equals</option>
                        <option value="contains">Contains</option>
                        <option value="greater-than">Greater Than</option>
                        <option value="less-than">Less Than</option>
                    </select>
                </div>
                <div class="property-group">
                    <label>Value:</label>
                    <input type="text" id="condition-value" placeholder="Enter condition value">
                </div>
            `
        };
        
        return properties[type] || '<p>No configurable properties for this component.</p>';
    }

    async executeWorkflow() {
        const workflow = this.buildWorkflowFromCanvas();
        if (!workflow || workflow.components.length === 0) {
            this.showNotification('No workflow to execute', 'warning');
            return;
        }

        this.updateExecutionStatus('Starting...');
        this.enableExecutionControls(false, true, true);

        try {
            const response = await fetch('/api/workflows/execute', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(workflow)
            });

            if (response.ok) {
                const result = await response.json();
                this.startExecutionMonitoring(result.execution_id);
            } else {
                throw new Error('Failed to start workflow execution');
            }
        } catch (error) {
            console.error('Workflow execution failed:', error);
            this.updateExecutionStatus('Failed');
            this.enableExecutionControls(true, false, false);
            this.addLogEntry('error', 'Workflow execution failed: ' + error.message);
        }
    }

    buildWorkflowFromCanvas() {
        const components = Array.from(document.querySelectorAll('.workflow-component')).map(component => {
            return {
                id: component.id || this.generateId(),
                type: component.dataset.type,
                position: {
                    x: parseInt(component.style.left),
                    y: parseInt(component.style.top)
                },
                properties: this.getComponentProperties(component)
            };
        });

        return {
            name: 'Generated Workflow',
            components: components,
            connections: this.getComponentConnections()
        };
    }

    getComponentProperties(component) {
        const type = component.dataset.type;
        const properties = {};

        switch (type) {
            case 'llm':
                properties.model = document.getElementById('llm-model')?.value || 'llama2';
                properties.temperature = parseFloat(document.getElementById('llm-temperature')?.value || 0.7);
                properties.maxTokens = parseInt(document.getElementById('llm-max-tokens')?.value || 1000);
                break;
            case 'image':
                properties.model = document.getElementById('image-model')?.value || 'stable-diffusion';
                properties.size = document.getElementById('image-size')?.value || '512x512';
                break;
            case 'condition':
                properties.type = document.getElementById('condition-type')?.value || 'equals';
                properties.value = document.getElementById('condition-value')?.value || '';
                break;
        }

        return properties;
    }

    getComponentConnections() {
        // Implementation for getting connections between components
        return [];
    }

    generateId() {
        return 'comp_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }

    updateExecutionStatus(status) {
        const statusElement = document.getElementById('execution-status');
        if (statusElement) {
            statusElement.textContent = status;
        }
    }

    enableExecutionControls(start, pause, stop) {
        const startBtn = document.getElementById('start-execution');
        const pauseBtn = document.getElementById('pause-execution');
        const stopBtn = document.getElementById('stop-execution');

        if (startBtn) startBtn.disabled = !start;
        if (pauseBtn) pauseBtn.disabled = !pause;
        if (stopBtn) stopBtn.disabled = !stop;
    }

    addLogEntry(level, message) {
        const logContent = document.getElementById('log-content');
        if (!logContent) return;

        const timestamp = new Date().toLocaleTimeString();
        const logEntry = document.createElement('div');
        logEntry.className = `log-entry log-${level}`;
        logEntry.innerHTML = `
            <span class="log-timestamp">[${timestamp}]</span>
            <span class="log-message">${message}</span>
        `;

        logContent.appendChild(logEntry);
        logContent.scrollTop = logContent.scrollHeight;
    }

    async loadWorkflowTemplates() {
        try {
            const response = await fetch('/api/workflows/templates');
            if (response.ok) {
                const data = await response.json();
                this.workflowTemplates = new Map(Object.entries(data.templates || {}));
            }
        } catch (error) {
            console.error('Failed to load workflow templates:', error);
        }
    }

    async loadWorkflows() {
        try {
            const response = await fetch('/api/workflows/list');
            if (response.ok) {
                const data = await response.json();
                this.workflows = new Map(Object.entries(data.workflows || {}));
                this.updateWorkflowGrid();
            }
        } catch (error) {
            console.error('Failed to load workflows:', error);
        }
    }

    updateWorkflowGrid() {
        const grid = document.getElementById('workflow-grid');
        if (!grid) return;

        grid.innerHTML = Array.from(this.workflows.values()).map(workflow => `
            <div class="workflow-card" data-id="${workflow.id}">
                <div class="workflow-header">
                    <h4>${workflow.name}</h4>
                    <div class="workflow-actions">
                        <button class="btn btn-sm btn-primary" onclick="workflowAutomation.loadWorkflow('${workflow.id}')">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button class="btn btn-sm btn-success" onclick="workflowAutomation.executeWorkflow('${workflow.id}')">
                            <i class="fas fa-play"></i>
                        </button>
                    </div>
                </div>
                <div class="workflow-info">
                    <span class="workflow-category">${workflow.category || 'General'}</span>
                    <span class="workflow-components">${workflow.components?.length || 0} components</span>
                </div>
            </div>
        `).join('');
    }

    showNotification(message, type = 'info') {
        console.log(`${type.toUpperCase()}: ${message}`);
    }
}

// Initialize the workflow automation
window.workflowAutomation = new WorkflowAutomation();
