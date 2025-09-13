// Settings page functionality
class SettingsManager {
    constructor() {
        // System Prompt Management
        this.currentSystemPrompts = [];
        this.currentPromptId = null;
        this.cleanupFunctions = [];
        this.availableTools = [];
        this.workspacePath = '';
        
        console.log('[SettingsManager] Initializing settings manager');
        
        // Initialize when DOM is ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.init());
        } else {
            this.init();
        }
    }

    // Initialize page
    init() {
        console.log('[SettingsManager] Setting up settings page');
        
        try {
            this.loadSystemPrompts();
            this.loadAvailableTools();
            this.loadWorkspacePath();
            this.loadStartupPreferences();
            this.loadAudioPreferences();
            this.loadApiProviders();
            this.setupEventListeners();
            this.initBackendMinContextPanel();
            
            this.showToast('Settings manager initialized successfully', 'success');
            
        } catch (error) {
            console.error('[SettingsManager] Error during initialization:', error);
            this.showToast('Settings manager initialization failed', 'error');
        }
    }

    // Toast notification method - Updated to use global notification manager
    showToast(message, type = 'info') {
        console.log(`[SettingsManager] Toast: ${message} (${type})`);
        
        // Use the global notification manager first
        if (window.notificationManager) {
            switch (type) {
                case 'success':
                    window.notificationManager.showSuccess(message);
                    break;
                case 'error':
                    window.notificationManager.showError(message);
                    break;
                case 'warning':
                    window.notificationManager.showWarning(message);
                    break;
                case 'info':
                default:
                    window.notificationManager.showInfo(message);
                    break;
            }
            return;
        }
        
        // Try to use existing notification system as fallback
        if (typeof this.showNotification === 'function') {
            this.showNotification(message, type);
            return;
        }

        // Final fallback toast implementation
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.textContent = message;
        toast.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 12px 20px;
            border-radius: 6px;
            color: white;
            font-weight: 500;
            z-index: 10000;
            max-width: 300px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            transform: translateX(100%);
            transition: transform 0.3s ease;
        `;

        // Set background color based on type
        const colors = {
            success: '#10b981',
            error: '#ef4444', 
            warning: '#f59e0b',
            info: '#3b82f6'
        };
        toast.style.backgroundColor = colors[type] || colors.info;

        document.body.appendChild(toast);

        // Animate in
        setTimeout(() => {
            toast.style.transform = 'translateX(0)';
        }, 10);

        // Auto remove
        setTimeout(() => {
            toast.style.transform = 'translateX(100%)';
            setTimeout(() => {
                if (toast.parentNode) {
                    document.body.removeChild(toast);
                }
            }, 300);
        }, 3000);
    }

    // Utility function to handle API responses properly
    async handleApiResponse(response) {
        // Check if response is ok
        if (!response.ok) {
            // Check if we're being redirected to login (common auth failure)
            if (response.status === 401 || response.url.includes('/login')) {
                window.location.href = '/login';
                return null;
            }
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        // Check if response is JSON
        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
            try {
                return await response.json();
            } catch (parseError) {
                console.error('Failed to parse JSON response:', parseError);
                throw new Error('Invalid JSON response from server');
            }
        } else {
            // If it's not JSON, it might be an authentication redirect
            const text = await response.text();
            if (text.includes('<!doctype') || text.includes('<html')) {
                window.location.href = '/login';
                return null;
            }
            throw new Error('Expected JSON response but received: ' + text.substring(0, 100));
        }
    }

    // Safe fetch wrapper
    async safeFetch(url, options = {}) {
        try {
            const response = await fetch(url, {
                credentials: 'same-origin', // Include cookies for authentication
                ...options
            });
            return await this.handleApiResponse(response);
        } catch (error) {
            console.error(`API call failed for ${url}:`, error);
            throw error;
        }
    }

    setupEventListeners() {
        // Legacy prompt editor toggle
        const togglePromptEditor = document.getElementById('toggle-prompt-editor');
        if (togglePromptEditor) {
            togglePromptEditor.addEventListener('click', () => {
                const section = document.getElementById('prompt-editor-section');
                if (section.style.display === 'none') {
                    section.style.display = 'block';
                    this.loadLegacySystemPrompt();
                } else {
                    section.style.display = 'none';
                }
            });
            this.cleanupFunctions.push(() => togglePromptEditor.removeEventListener('click', this.boundTogglePromptEditor));
        }

        // New System Prompt Manager
        const managePromptsBtn = document.getElementById('manage-system-prompts');
        if (managePromptsBtn) {
            managePromptsBtn.addEventListener('click', () => {
                document.getElementById('prompt-manager-modal').style.display = 'block';
            });
        }

        // System prompt selector
        const promptSelector = document.getElementById('current-system-prompt');
        if (promptSelector) {
            promptSelector.addEventListener('change', (e) => {
                if (e.target.value) {
                    this.selectSystemPrompt(e.target.value);
                }
            });
        }

        // Workspace management
        const changeWorkspaceBtn = document.getElementById('change-workspace');
        if (changeWorkspaceBtn) {
            changeWorkspaceBtn.addEventListener('click', () => {
                document.getElementById('workspace-modal').style.display = 'block';
            });
        }

        const saveWorkspaceBtn = document.getElementById('save-workspace');
        if (saveWorkspaceBtn) {
            saveWorkspaceBtn.addEventListener('click', () => {
                this.saveWorkspacePath();
            });
        }

        // Modal close buttons
        document.querySelectorAll('.close-modal').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.target.closest('.modal').style.display = 'none';
            });
        });

        // Create new prompt button
        const createPromptBtn = document.getElementById('create-new-prompt');
        if (createPromptBtn) {
            createPromptBtn.addEventListener('click', () => {
                this.currentPromptId = null;
                document.getElementById('prompt-editor-modal').style.display = 'block';
                document.getElementById('prompt-name').value = '';
                document.getElementById('prompt-content').value = '';
                document.getElementById('delete-prompt').style.display = 'none';
            });
        }

        // Prompt editor form
        const promptForm = document.getElementById('prompt-editor-form');
        if (promptForm) {
            promptForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.saveSystemPrompt();
            });
        }

        // Cancel edit button
        const cancelBtn = document.getElementById('cancel-prompt-edit');
        if (cancelBtn) {
            cancelBtn.addEventListener('click', () => {
                document.getElementById('prompt-editor-modal').style.display = 'none';
            });
        }

        // Delete prompt button
        const deleteBtn = document.getElementById('delete-prompt');
        if (deleteBtn) {
            deleteBtn.addEventListener('click', () => {
                if (this.currentPromptId && confirm('Are you sure you want to delete this prompt?')) {
                    this.deleteSystemPrompt(this.currentPromptId);
                }
            });
        }

        // Legacy save/reset buttons
        const savePromptBtn = document.getElementById('save-prompt');
        if (savePromptBtn) {
            savePromptBtn.addEventListener('click', () => this.saveLegacySystemPrompt());
        }

        const resetPromptBtn = document.getElementById('reset-prompt');
        if (resetPromptBtn) {
            resetPromptBtn.addEventListener('click', () => this.resetLegacySystemPrompt());
        }

        // Startup preferences toggles
        const prefAutoLlm = document.getElementById('pref-auto-llm');
        const prefAutoSd = document.getElementById('pref-auto-sd');
        const prefAutoComfy = document.getElementById('pref-auto-comfy');
        const savePrefs = this.debounce(() => this.saveStartupPreferences(), 250);
        if (prefAutoLlm) prefAutoLlm.addEventListener('change', savePrefs);
        if (prefAutoSd) prefAutoSd.addEventListener('change', savePrefs);
        if (prefAutoComfy) prefAutoComfy.addEventListener('change', savePrefs);

        // Audio prefs
        const prefEnableEdge = document.getElementById('pref-enable-edge-tts');
        if (prefEnableEdge) {
            prefEnableEdge.addEventListener('change', this.debounce(() => this.saveAudioPreferences(), 250));
        }

        // Provider settings
        const saveOpenAiBtn = document.getElementById('save-openai-key');
        if (saveOpenAiBtn) {
            saveOpenAiBtn.addEventListener('click', () => this.saveApiKey('openai'));
        }
        
        const saveAnthropicBtn = document.getElementById('save-anthropic-key');
        if (saveAnthropicBtn) {
            saveAnthropicBtn.addEventListener('click', () => this.saveApiKey('anthropic'));
        }
        
        const saveRoutingBtn = document.getElementById('save-routing');
        if (saveRoutingBtn) {
            saveRoutingBtn.addEventListener('click', () => this.saveRoutingPolicy());
        }

        // Click outside modal to close
        window.addEventListener('click', (e) => {
            if (e.target.classList.contains('modal')) {
                e.target.style.display = 'none';
            }
        });
    }

    async initBackendMinContextPanel() {
        // Populate min context display and wire download button
        try {
            const cfg = await this.safeFetch('/api/configuration');
            const minCtxEl = document.getElementById('min-context-display');
            if (cfg && cfg.static_config && minCtxEl) {
                const minCtx = cfg.static_config.required_min_context_tokens || 32768;
                minCtxEl.textContent = `${Number(minCtx).toLocaleString()} tokens`;
            }
        } catch {
            // ignore
        }
        const dlBtn = document.getElementById('download-recommended-model');
        if (dlBtn) {
            dlBtn.addEventListener('click', async () => {
                dlBtn.disabled = true;
                dlBtn.textContent = 'Downloading…';
                try {
                    const resp = await this.safeFetch('/api/models/download_default', { method: 'POST' });
                    if (resp && resp.success) {
                        dlBtn.textContent = 'Downloaded. Initializing…';
                        setTimeout(() => {
                            dlBtn.disabled = false;
                            dlBtn.textContent = 'Download Recommended 32k Model';
                        }, 3000);
                    } else {
                        dlBtn.textContent = 'Retry Download';
                        dlBtn.disabled = false;
                    }
                } catch {
                    dlBtn.textContent = 'Retry Download';
                    dlBtn.disabled = false;
                }
            });
        }
    }

    // Utility functions
    debounce(fn, wait) {
        let t;
        return (...args) => {
            clearTimeout(t);
            t = setTimeout(() => fn.apply(this, args), wait);
        };
    }

    showNotification(message, type = 'info') {
        // Use the global notification manager first
        if (window.notificationManager) {
            switch (type) {
                case 'success':
                    window.notificationManager.showSuccess(message);
                    break;
                case 'error':
                    window.notificationManager.showError(message);
                    break;
                case 'warning':
                    window.notificationManager.showWarning(message);
                    break;
                case 'info':
                default:
                    window.notificationManager.showInfo(message);
                    break;
            }
            return;
        }
        
        // Fallback to toast if notification manager not available
        this.showToast(message, type);
    }

    // Cleanup method for event listeners
    destroy() {
        this.cleanupFunctions.forEach(cleanup => cleanup());
        this.cleanupFunctions = [];
    }

    // Load methods - these will be stubbed since we don't have the full original implementation
    async loadSystemPrompts() {
        try {
            const data = await this.safeFetch('/api/system_prompts');
            if (data) {
                this.currentSystemPrompts = data;
                this.updatePromptSelector();
            }
        } catch (error) {
            console.error('Error loading system prompts:', error);
            this.showNotification('Failed to load system prompts', 'error');
        }
    }

    updatePromptSelector() {
        console.log('[SettingsManager] Updating prompt selector');
        
        const selector = document.getElementById('current-system-prompt');
        if (selector) {
            selector.innerHTML = '<option value="">Select a prompt...</option>';
            this.currentSystemPrompts.forEach(prompt => {
                const option = document.createElement('option');
                option.value = prompt.id;
                option.textContent = prompt.name;
                selector.appendChild(option);
            });
            
            // Restore previously selected prompt
            const savedPromptId = localStorage.getItem('selectedSystemPromptId');
            if (savedPromptId) {
                selector.value = savedPromptId;
            }
            
            this.showToast(`Loaded ${this.currentSystemPrompts.length} system prompts`, 'success');
        }
    }

    async selectSystemPrompt(promptId) {
        console.log(`[SettingsManager] Selecting system prompt: ${promptId}`);
        
        try {
            const response = await fetch(`/api/system_prompts/${promptId}/use`, {
                method: 'POST'
            });
            if (response.ok) {
                this.showToast('System prompt selected successfully', 'success');
                localStorage.setItem('selectedSystemPromptId', promptId);
                
                // Update UI to show selected prompt
                this.updateSelectedPromptDisplay(promptId);
            } else {
                this.showToast('Failed to select system prompt', 'error');
            }
        } catch (error) {
            console.error('[SettingsManager] Error selecting system prompt:', error);
            this.showToast('Error selecting system prompt', 'error');
        }
    }

    updateSelectedPromptDisplay(promptId) {
        const prompt = this.currentSystemPrompts.find(p => p.id === promptId);
        if (prompt) {
            const displayEl = document.getElementById('selected-prompt-display');
            if (displayEl) {
                displayEl.textContent = `Current: ${prompt.name}`;
                displayEl.classList.add('active');
            }
        }
    }

    async loadAvailableTools() {
        console.log('[SettingsManager] Loading available tools');
        
        try {
            // Simulate API call or load from static data
            this.availableTools = [
                { id: 'calculator', name: 'Calculator', enabled: true, description: 'Basic mathematical calculations' },
                { id: 'web-search', name: 'Web Search', enabled: false, description: 'Search the internet for information' },
                { id: 'file-manager', name: 'File Manager', enabled: true, description: 'Manage files and directories' },
                { id: 'image-generator', name: 'Image Generator', enabled: false, description: 'Generate images using AI' },
                { id: 'code-executor', name: 'Code Executor', enabled: true, description: 'Execute code snippets safely' },
                { id: 'translator', name: 'Translator', enabled: false, description: 'Translate text between languages' }
            ];
            
            // Load saved tool states
            const savedToolStates = JSON.parse(localStorage.getItem('toolStates') || '{}');
            this.availableTools.forEach(tool => {
                if (Object.prototype.hasOwnProperty.call(savedToolStates, tool.id)) {
                    tool.enabled = savedToolStates[tool.id];
                }
            });
            
            this.displayTools();
            this.showToast(`Loaded ${this.availableTools.length} available tools`, 'success');
            
        } catch (error) {
            console.error('[SettingsManager] Error loading available tools:', error);
            this.showToast('Error loading available tools', 'error');
        }
    }

    displayTools() {
        console.log('[SettingsManager] Displaying tools in UI');
        
        const toolsContainer = document.getElementById('tools-list');
        if (!toolsContainer) {
            console.warn('[SettingsManager] Tools container not found');
            return;
        }
        
        toolsContainer.innerHTML = '';
        
        this.availableTools.forEach(tool => {
            const toolElement = document.createElement('div');
            toolElement.className = 'tool-item';
            toolElement.innerHTML = `
                <div class="tool-info">
                    <h4>${tool.name}</h4>
                    <p>${tool.description}</p>
                </div>
                <div class="tool-controls">
                    <label class="toggle-switch">
                        <input type="checkbox" ${tool.enabled ? 'checked' : ''} 
                               onchange="settingsManager.toggleTool('${tool.id}', this.checked)">
                        <span class="toggle-slider"></span>
                    </label>
                </div>
            `;
            toolsContainer.appendChild(toolElement);
        });
    }

    toggleTool(toolId, enabled) {
        console.log(`[SettingsManager] Toggling tool: ${toolId} = ${enabled}`);
        
        try {
            // Update tool state
            const tool = this.availableTools.find(t => t.id === toolId);
            if (tool) {
                tool.enabled = enabled;
                
                // Save to localStorage
                const toolStates = JSON.parse(localStorage.getItem('toolStates') || '{}');
                toolStates[toolId] = enabled;
                localStorage.setItem('toolStates', JSON.stringify(toolStates));
                
                // Apply tool changes
                this.applyToolChanges(toolId, enabled);
                
                const action = enabled ? 'enabled' : 'disabled';
                this.showToast(`${tool.name} ${action}`, 'success');
            }
        } catch (error) {
            console.error('[SettingsManager] Error toggling tool:', error);
            this.showToast('Error updating tool', 'error');
        }
    }

    applyToolChanges(toolId, enabled) {
        console.log(`[SettingsManager] Applying changes for tool: ${toolId} = ${enabled}`);
        
        // Apply tool-specific logic
        switch (toolId) {
            case 'calculator':
                this.toggleCalculatorFeature(enabled);
                break;
            case 'web-search':
                this.toggleWebSearchFeature(enabled);
                break;
            case 'file-manager':
                this.toggleFileManagerFeature(enabled);
                break;
            case 'image-generator':
                this.toggleImageGeneratorFeature(enabled);
                break;
            case 'code-executor':
                this.toggleCodeExecutorFeature(enabled);
                break;
            case 'translator':
                this.toggleTranslatorFeature(enabled);
                break;
            default:
                console.log(`[SettingsManager] Unknown tool: ${toolId}`);
        }
    }

    toggleCalculatorFeature(enabled) {
        const calculatorElements = document.querySelectorAll('.calculator-feature');
        calculatorElements.forEach(el => {
            el.style.display = enabled ? 'block' : 'none';
        });
    }

    toggleWebSearchFeature(enabled) {
        const searchElements = document.querySelectorAll('.web-search-feature');
        searchElements.forEach(el => {
            el.style.display = enabled ? 'block' : 'none';
        });
    }

    toggleFileManagerFeature(enabled) {
        const fileElements = document.querySelectorAll('.file-manager-feature');
        fileElements.forEach(el => {
            el.style.display = enabled ? 'block' : 'none';
        });
    }

    toggleImageGeneratorFeature(enabled) {
        const imageElements = document.querySelectorAll('.image-generator-feature');
        imageElements.forEach(el => {
            el.style.display = enabled ? 'block' : 'none';
        });
    }

    toggleCodeExecutorFeature(enabled) {
        const codeElements = document.querySelectorAll('.code-executor-feature');
        codeElements.forEach(el => {
            el.style.display = enabled ? 'block' : 'none';
        });
    }

    toggleTranslatorFeature(enabled) {
        const translatorElements = document.querySelectorAll('.translator-feature');
        translatorElements.forEach(el => {
            el.style.display = enabled ? 'block' : 'none';
        });
    }

    async loadWorkspacePath() {
        console.log('[SettingsManager] Loading workspace path');
        
        try {
            // Try to load from API or localStorage
            const savedPath = localStorage.getItem('workspacePath') || '/default/workspace';
            this.workspacePath = savedPath;
            
            // Update UI
            const pathDisplay = document.getElementById('current-workspace-path');
            if (pathDisplay) {
                pathDisplay.textContent = this.workspacePath;
            }
            
            const pathInput = document.getElementById('workspace-path');
            if (pathInput) {
                pathInput.value = this.workspacePath;
            }
            
            this.showToast('Workspace path loaded', 'success');
            
        } catch (error) {
            console.error('[SettingsManager] Error loading workspace path:', error);
            this.showToast('Error loading workspace path', 'error');
        }
    }

    async saveWorkspacePath() {
        console.log('[SettingsManager] Saving workspace path');
        
        try {
            const pathInput = document.getElementById('workspace-path');
            if (!pathInput) {
                throw new Error('Workspace path input not found');
            }
            
            const newPath = pathInput.value.trim();
            if (!newPath) {
                this.showToast('Please enter a valid workspace path', 'warning');
                return;
            }
            
            // Validate path format
            if (!this.isValidPath(newPath)) {
                this.showToast('Please enter a valid file system path', 'warning');
                return;
            }
            
            // Save to localStorage
            localStorage.setItem('workspacePath', newPath);
            this.workspacePath = newPath;
            
            // Update display
            const pathDisplay = document.getElementById('current-workspace-path');
            if (pathDisplay) {
                pathDisplay.textContent = newPath;
            }
            
            // Close modal
            const modal = document.getElementById('workspace-modal');
            if (modal) {
                modal.style.display = 'none';
            }
            
            this.showToast('Workspace path saved successfully', 'success');
            
        } catch (error) {
            console.error('[SettingsManager] Error saving workspace path:', error);
            this.showToast('Error saving workspace path', 'error');
        }
    }

    isValidPath(path) {
        // Basic path validation
        if (!path || typeof path !== 'string') return false;
        
        // Check for common path patterns
        const pathPatterns = [
            /^[a-zA-Z]:\\/,  // Windows absolute path
            /^\/\w*/,        // Unix/Linux absolute path
            /^\.\/\w*/,      // Relative path starting with ./
            /^\w+/           // Simple relative path
        ];
        
        return pathPatterns.some(pattern => pattern.test(path));
    }

    async loadStartupPreferences() {
        try {
            const data = await this.safeFetch('/api/settings/startup_prefs');
            const prefs = data && data.prefs ? data.prefs : {};
            const prefAutoLlm = document.getElementById('pref-auto-llm');
            const prefAutoSd = document.getElementById('pref-auto-sd');
            const prefAutoComfy = document.getElementById('pref-auto-comfy');
            if (prefAutoLlm && typeof prefs.auto_launch_llm_on_start === 'boolean') prefAutoLlm.checked = prefs.auto_launch_llm_on_start;
            if (prefAutoSd && typeof prefs.auto_launch_sd_on_start === 'boolean') prefAutoSd.checked = prefs.auto_launch_sd_on_start;
            if (prefAutoComfy && typeof prefs.auto_launch_comfy_on_start === 'boolean') prefAutoComfy.checked = prefs.auto_launch_comfy_on_start;
        } catch (e) {
            console.warn('Failed to load startup preferences', e);
        }
    }

    async saveStartupPreferences() {
        try {
            const prefAutoLlm = document.getElementById('pref-auto-llm');
            const prefAutoSd = document.getElementById('pref-auto-sd');
            const prefAutoComfy = document.getElementById('pref-auto-comfy');
            const payload = {
                auto_launch_llm_on_start: !!(prefAutoLlm && prefAutoLlm.checked),
                auto_launch_sd_on_start: !!(prefAutoSd && prefAutoSd.checked),
                auto_launch_comfy_on_start: !!(prefAutoComfy && prefAutoComfy.checked)
            };
            const res = await this.safeFetch('/api/settings/startup_prefs', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            if (res && res.success) {
                this.showNotification('Startup preferences saved. These apply on next launch.', 'success');
            }
        } catch (e) {
            console.error('Failed to save startup preferences', e);
            this.showNotification('Failed to save startup preferences', 'error');
        }
    }

    async loadAudioPreferences() {
        try {
            const data = await this.safeFetch('/api/settings/audio_prefs');
            const pref = data && data.prefs ? data.prefs.enable_edge_tts : false;
            const toggle = document.getElementById('pref-enable-edge-tts');
            if (toggle) toggle.checked = !!pref;
        } catch (e) {
            console.warn('Failed to load audio prefs', e);
        }
    }

    async saveAudioPreferences() {
        try {
            const toggle = document.getElementById('pref-enable-edge-tts');
            const payload = { enable_edge_tts: !!(toggle && toggle.checked) };
            const res = await this.safeFetch('/api/settings/audio_prefs', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            if (res && res.success) {
                this.showNotification('Audio preference saved. Edge TTS is ' + (payload.enable_edge_tts ? 'enabled' : 'disabled'), 'success');
            }
        } catch (e) {
            console.error('Failed to save audio prefs', e);
            this.showNotification('Failed to save audio preferences', 'error');
        }
    }

    async loadApiProviders() {
        try {
            const data = await this.safeFetch('/api/settings/api_providers');
            if (!data) return;
            const openaiStatus = document.getElementById('openai-status');
            const anthropicStatus = document.getElementById('anthropic-status');
            const routingMode = document.getElementById('routing-mode');
            const defaultProvider = document.getElementById('default-provider');
            if (openaiStatus) openaiStatus.textContent = data.providers?.openai?.configured ? 'Configured' : 'Not configured';
            if (anthropicStatus) anthropicStatus.textContent = data.providers?.anthropic?.configured ? 'Configured' : 'Not configured';
            if (routingMode && data.routing_mode) routingMode.value = data.routing_mode;
            if (defaultProvider && data.default_provider) defaultProvider.value = data.default_provider;
        } catch (e) {
            console.warn('Failed to load API providers', e);
        }
    }

    async saveApiKey(provider) {
        try {
            const keyMap = {
                openai: document.getElementById('openai-api-key')?.value || '',
                anthropic: document.getElementById('anthropic-api-key')?.value || ''
            };
            const payload = {};
            if (provider === 'openai') payload.openai_api_key = keyMap.openai;
            if (provider === 'anthropic') payload.anthropic_api_key = keyMap.anthropic;
            const res = await this.safeFetch('/api/settings/api_providers', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            if (res && res.success) {
                this.showNotification(`${provider} key saved`, 'success');
                this.loadApiProviders();
            }
        } catch (e) {
            console.error('Failed to save API key', e);
            this.showNotification('Failed to save API key', 'error');
        }
    }

    async saveRoutingPolicy() {
        try {
            const routingMode = document.getElementById('routing-mode')?.value || 'prefer_local';
            const defaultProvider = document.getElementById('default-provider')?.value || 'local';
            const res = await this.safeFetch('/api/settings/api_providers', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ routing_mode: routingMode, default_provider: defaultProvider })
            });
            if (res && res.success) {
                this.showNotification('Routing policy saved', 'success');
                this.loadApiProviders();
            }
        } catch (e) {
            console.error('Failed to save routing policy', e);
            this.showNotification('Failed to save routing policy', 'error');
        }
    }

    // Stub methods for compatibility
    async loadLegacySystemPrompt() {
        console.log('[SettingsManager] Loading legacy system prompt');
        
        try {
            // Load from localStorage or API
            const legacyPrompt = localStorage.getItem('legacySystemPrompt') || 'You are a helpful AI assistant.';
            
            const promptTextarea = document.getElementById('legacy-system-prompt');
            if (promptTextarea) {
                promptTextarea.value = legacyPrompt;
            }
            
            this.showToast('Legacy system prompt loaded', 'success');
            
        } catch (error) {
            console.error('[SettingsManager] Error loading legacy system prompt:', error);
            this.showToast('Error loading legacy system prompt', 'error');
        }
    }

    async saveLegacySystemPrompt() {
        console.log('[SettingsManager] Saving legacy system prompt');
        
        try {
            const promptTextarea = document.getElementById('legacy-system-prompt');
            if (!promptTextarea) {
                throw new Error('Legacy system prompt textarea not found');
            }
            
            const promptText = promptTextarea.value.trim();
            if (!promptText) {
                this.showToast('Please enter a system prompt', 'warning');
                return;
            }
            
            // Save to localStorage
            localStorage.setItem('legacySystemPrompt', promptText);
            
            // Show success message
            this.showToast('Legacy system prompt saved', 'success');
            
        } catch (error) {
            console.error('[SettingsManager] Error saving legacy system prompt:', error);
            this.showToast('Error saving legacy system prompt', 'error');
        }
    }

    async resetLegacySystemPrompt() {
        console.log('[SettingsManager] Resetting legacy system prompt');
        
        try {
            const defaultPrompt = 'You are a helpful AI assistant.';
            
            const promptTextarea = document.getElementById('legacy-system-prompt');
            if (promptTextarea) {
                promptTextarea.value = defaultPrompt;
            }
            
            // Save default to localStorage
            localStorage.setItem('legacySystemPrompt', defaultPrompt);
            
            this.showToast('Legacy system prompt reset', 'success');
            
        } catch (error) {
            console.error('[SettingsManager] Error resetting legacy system prompt:', error);
            this.showToast('Error resetting legacy system prompt', 'error');
        }
    }

    async saveSystemPrompt() {
        console.log('[SettingsManager] Saving system prompt');
        
        try {
            const nameInput = document.getElementById('prompt-name');
            const contentTextarea = document.getElementById('prompt-content');
            
            if (!nameInput || !contentTextarea) {
                throw new Error('Prompt form elements not found');
            }
            
            const name = nameInput.value.trim();
            const content = contentTextarea.value.trim();
            
            if (!name) {
                this.showToast('Please enter a prompt name', 'warning');
                nameInput.focus();
                return;
            }
            
            if (!content) {
                this.showToast('Please enter prompt content', 'warning');
                contentTextarea.focus();
                return;
            }
            
            // Create or update prompt
            const promptData = {
                id: this.currentPromptId || 'prompt_' + Date.now(),
                name: name,
                content: content,
                created: this.currentPromptId ? undefined : new Date().toISOString(),
                modified: new Date().toISOString()
            };
            
            if (this.currentPromptId) {
                // Update existing prompt
                const promptIndex = this.currentSystemPrompts.findIndex(p => p.id === this.currentPromptId);
                if (promptIndex !== -1) {
                    this.currentSystemPrompts[promptIndex] = { ...this.currentSystemPrompts[promptIndex], ...promptData };
                }
            } else {
                // Add new prompt
                this.currentSystemPrompts.push(promptData);
            }
            
            // Save to localStorage
            localStorage.setItem('systemPrompts', JSON.stringify(this.currentSystemPrompts));
            
            // Update UI
            this.updatePromptSelector();
            
            // Close modal
            const modal = document.getElementById('prompt-editor-modal');
            if (modal) {
                modal.style.display = 'none';
            }
            
            const action = this.currentPromptId ? 'updated' : 'created';
            this.showToast(`System prompt ${action} successfully`, 'success');
            
        } catch (error) {
            console.error('[SettingsManager] Error saving system prompt:', error);
            this.showToast('Error saving system prompt', 'error');
        }
    }

    async deleteSystemPrompt(promptId) {
        console.log(`[SettingsManager] Deleting system prompt: ${promptId}`);
        
        try {
            if (!promptId) {
                throw new Error('No prompt ID provided');
            }
            
            // Find and remove prompt
            const promptIndex = this.currentSystemPrompts.findIndex(p => p.id === promptId);
            if (promptIndex === -1) {
                throw new Error('Prompt not found');
            }
            
            const promptName = this.currentSystemPrompts[promptIndex].name;
            this.currentSystemPrompts.splice(promptIndex, 1);
            
            // Save to localStorage
            localStorage.setItem('systemPrompts', JSON.stringify(this.currentSystemPrompts));
            
            // Update UI
            this.updatePromptSelector();
            
            // Close modal
            const modal = document.getElementById('prompt-editor-modal');
            if (modal) {
                modal.style.display = 'none';
            }
            
            // Clear current prompt ID
            this.currentPromptId = null;
            
            this.showToast(`System prompt "${promptName}" deleted`, 'success');
            
        } catch (error) {
            console.error('[SettingsManager] Error deleting system prompt:', error);
            this.showToast('Error deleting system prompt', 'error');
        }
    }

    editSystemPrompt(promptId) {
        console.log(`[SettingsManager] Editing system prompt: ${promptId}`);
        
        try {
            const prompt = this.currentSystemPrompts.find(p => p.id === promptId);
            if (!prompt) {
                throw new Error('Prompt not found');
            }
            
            // Set current prompt ID
            this.currentPromptId = promptId;
            
            // Populate form
            const nameInput = document.getElementById('prompt-name');
            const contentTextarea = document.getElementById('prompt-content');
            const deleteBtn = document.getElementById('delete-prompt');
            
            if (nameInput) nameInput.value = prompt.name;
            if (contentTextarea) contentTextarea.value = prompt.content;
            if (deleteBtn) deleteBtn.style.display = 'block';
            
            // Show modal
            const modal = document.getElementById('prompt-editor-modal');
            if (modal) {
                modal.style.display = 'block';
            }
            
        } catch (error) {
            console.error('[SettingsManager] Error editing system prompt:', error);
            this.showToast('Error editing system prompt', 'error');
        }
    }

    refreshAllData() {
        console.log('[SettingsManager] Refreshing all settings data');
        
        try {
            // Reload all data
            this.loadSystemPrompts();
            this.loadAvailableTools();
            this.loadWorkspacePath();
            this.loadStartupPreferences();
            this.loadAudioPreferences();
            this.loadApiProviders();
            
            this.showToast('All settings data refreshed', 'success');
            
        } catch (error) {
            console.error('[SettingsManager] Error refreshing all data:', error);
            this.showToast('Error refreshing settings data', 'error');
        }
    }
}

// Initialize the settings manager
window.settingsManager = new SettingsManager();
