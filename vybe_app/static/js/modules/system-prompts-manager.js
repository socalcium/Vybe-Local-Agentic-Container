/**
 * System Prompts Manager Module
 * Handles CRUD operations for system prompts and prompt selection
 */

import { ApiUtils } from '../utils/api-utils.js';

export class SystemPromptsManager {
    constructor() {
        this.currentSystemPrompts = [];
        this.currentPromptId = null;
        
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

    /**
     * Show toast notification
     */
    showToast(message, type = 'info') {
        console.log(`System Prompts Manager Toast (${type}): ${message}`);
        
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
        toast.className = `system-prompts-toast toast-${type}`;
        toast.style.cssText = `
            position: fixed;
            top: 140px;
            right: 20px;
            background: ${type === 'error' ? '#dc3545' : type === 'success' ? '#28a745' : type === 'warning' ? '#ffc107' : '#007bff'};
            color: ${type === 'warning' ? '#000' : '#fff'};
            padding: 12px 16px;
            border-radius: 6px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            z-index: 10004;
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
        
        // Auto remove after 3 seconds
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(100%)';
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
            }, 300);
        }, 3000);
    }


    init() {
        console.log('Initializing System Prompts Manager...');
        this.loadSystemPrompts();
        this.setupEventListeners();
        this.showToast('System Prompts Manager initialized', 'success');
        console.log('System Prompts Manager initialization completed');
    }

    setupEventListeners() {
        // System prompt selector
        const promptSelector = document.getElementById('current-system-prompt');
        if (promptSelector) {
            const selectorHandler = (e) => {
                if (e.target.value) {
                    this.selectSystemPrompt(e.target.value);
                }
            };
            window.eventManager.add(promptSelector, 'change', selectorHandler);
            this.cleanupFunctions.push(() => {
                window.eventManager.remove(promptSelector, 'change', selectorHandler);
            });
        }

        // Toggle prompt editor button
        const toggleEditorBtn = document.getElementById('toggle-prompt-editor');
        if (toggleEditorBtn) {
            const toggleHandler = () => {
                const editor = document.getElementById('system-prompt-editor');
                const container = editor?.parentElement;
                if (container) {
                    const isVisible = container.style.display !== 'none';
                    container.style.display = isVisible ? 'none' : 'block';
                    toggleEditorBtn.textContent = isVisible ? 'Edit System Prompt' : 'Hide Editor';
                }
            };
            window.eventManager.add(toggleEditorBtn, 'click', toggleHandler);
            this.cleanupFunctions.push(() => {
                window.eventManager.remove(toggleEditorBtn, 'click', toggleHandler);
            });
        }

        // Manage prompts button
        const managePromptsBtn = document.getElementById('manage-system-prompts');
        if (managePromptsBtn) {
            const manageHandler = () => {
                console.log('Opening system prompts management modal');
                this.showSystemPromptsModal();
            };
            window.eventManager.add(managePromptsBtn, 'click', manageHandler);
            this.cleanupFunctions.push(() => {
                window.eventManager.remove(managePromptsBtn, 'click', manageHandler);
            });
        }

        // Create new prompt button
        const createPromptBtn = document.getElementById('create-new-prompt');
        if (createPromptBtn) {
            const createHandler = () => {
                console.log('Opening new prompt editor');
                this.showPromptEditor();
            };
            window.eventManager.add(createPromptBtn, 'click', createHandler);
            this.cleanupFunctions.push(() => {
                window.eventManager.remove(createPromptBtn, 'click', createHandler);
            });
        }

        // Prompt editor form
        const promptForm = document.getElementById('prompt-editor-form');
        if (promptForm) {
            const formHandler = (e) => {
                e.preventDefault();
                this.saveSystemPrompt();
            };
            window.eventManager.add(promptForm, 'submit', formHandler);
            this.cleanupFunctions.push(() => {
                window.eventManager.remove(promptForm, 'submit', formHandler);
            });
        }

        // Cancel edit button
        const cancelBtn = document.getElementById('cancel-prompt-edit');
        if (cancelBtn) {
            const cancelHandler = () => {
                console.log('Cancelling prompt edit');
                document.getElementById('prompt-editor-modal').style.display = 'none';
                this.showToast('Prompt edit cancelled', 'info');
            };
            window.eventManager.add(cancelBtn, 'click', cancelHandler);
            this.cleanupFunctions.push(() => {
                window.eventManager.remove(cancelBtn, 'click', cancelHandler);
            });
        }

        // Delete prompt button
        const deleteBtn = document.getElementById('delete-prompt');
        if (deleteBtn) {
            const deleteHandler = () => {
                if (this.currentPromptId && confirm('Are you sure you want to delete this prompt?')) {
                    this.deleteSystemPrompt(this.currentPromptId);
                }
            };
            window.eventManager.add(deleteBtn, 'click', deleteHandler);
            this.cleanupFunctions.push(() => {
                window.eventManager.remove(deleteBtn, 'click', deleteHandler);
            });
        }
    }

    async loadSystemPrompts() {
        console.log('Loading system prompts...');
        try {
            const data = await ApiUtils.safeFetch('/api/system_prompts');
            if (data) {
                this.currentSystemPrompts = data;
                this.updatePromptSelector();
                console.log(`Loaded ${this.currentSystemPrompts.length} system prompts`);
                this.showToast('System prompts loaded successfully', 'success');
            }
        } catch (error) {
            console.error('Error loading system prompts:', error);
            ApiUtils.showGlobalStatus('Failed to load system prompts', 'error');
            this.showToast('Failed to load system prompts', 'error');
        }
    }

    updatePromptSelector() {
        console.log('Updating prompt selector with', this.currentSystemPrompts.length, 'prompts');
        const selector = document.getElementById('current-system-prompt');
        if (selector) {
            selector.innerHTML = '<option value="">Select a prompt...</option>';
            this.currentSystemPrompts.forEach(prompt => {
                const option = document.createElement('option');
                option.value = prompt.id;
                option.textContent = prompt.name;
                selector.appendChild(option);
            });
            console.log('Prompt selector updated successfully');
        } else {
            console.warn('Prompt selector element not found');
        }
    }

    async selectSystemPrompt(promptId) {
        console.log('Selecting system prompt:', promptId);
        this.showToast('Selecting system prompt...', 'info');
        
        try {
            const data = await ApiUtils.safeFetch(`/api/system_prompts/${promptId}/use`, {
                method: 'POST'
            });
            
            if (data && data.success) {
                console.log('System prompt selected successfully:', promptId);
                ApiUtils.showGlobalStatus('System prompt selected successfully', 'success');
                this.showToast('System prompt selected successfully', 'success');
                localStorage.setItem('selectedSystemPromptId', promptId);
                this.currentPromptId = promptId;
            } else {
                console.error('Failed to select system prompt:', data);
                ApiUtils.showGlobalStatus('Failed to select system prompt', 'error');
                this.showToast('Failed to select system prompt', 'error');
            }
        } catch (error) {
            console.error('Error selecting system prompt:', error);
            ApiUtils.showGlobalStatus('Error selecting system prompt', 'error');
            this.showToast('Error selecting system prompt', 'error');
        }
    }

    showSystemPromptsModal() {
        console.log('Opening system prompts management modal');
        const modal = document.getElementById('system-prompts-modal');
        if (modal) {
            modal.style.display = 'block';
            this.renderSystemPromptsList();
            this.showToast('System prompts manager opened', 'info');
        } else {
            console.error('System prompts modal not found');
            this.showToast('Could not open prompts manager', 'error');
        }
    }

    renderSystemPromptsList() {
        console.log('Rendering system prompts list with', this.currentSystemPrompts.length, 'prompts');
        const container = document.getElementById('system-prompts-list');
        if (!container) {
            console.error('System prompts list container not found');
            return;
        }

        if (this.currentSystemPrompts.length === 0) {
            container.innerHTML = '<p>No system prompts found. Create your first prompt to get started.</p>';
            console.log('No system prompts to display');
            return;
        }

        container.innerHTML = this.currentSystemPrompts.map(prompt => `
            <div class="prompt-item" data-id="${prompt.id}">
                <div class="prompt-header">
                    <h4>${prompt.name}</h4>
                    <div class="prompt-actions">
                        <button class="settings-button small edit-prompt" data-id="${prompt.id}">Edit</button>
                        <button class="settings-button small use-prompt" data-id="${prompt.id}">Use</button>
                    </div>
                </div>
                <p class="prompt-description">${prompt.description || 'No description'}</p>
                <div class="prompt-meta">
                    <span>Category: ${prompt.category || 'General'}</span>
                    ${prompt.created_at ? `<span>Created: ${new Date(prompt.created_at).toLocaleDateString()}</span>` : ''}
                </div>
            </div>
        `).join('');

        // Add event listeners to action buttons
        container.querySelectorAll('.edit-prompt').forEach(btn => {
            const editHandler = (e) => {
                const promptId = e.target.dataset.id;
                const prompt = this.currentSystemPrompts.find(p => p.id == promptId);
                if (prompt) {
                    console.log('Editing prompt:', prompt.name);
                    this.showPromptEditor(prompt);
                }
            };
            window.eventManager.add(btn, 'click', editHandler);
        });

        container.querySelectorAll('.use-prompt').forEach(btn => {
            const useHandler = (e) => {
                const promptId = e.target.dataset.id;
                const prompt = this.currentSystemPrompts.find(p => p.id == promptId);
                console.log('Using prompt:', prompt?.name || promptId);
                this.selectSystemPrompt(promptId);
                document.getElementById('system-prompts-modal').style.display = 'none';
            };
            window.eventManager.add(btn, 'click', useHandler);
        });
        
        console.log('System prompts list rendered successfully');
    }

    showPromptEditor(prompt = null) {
        console.log('Opening prompt editor for:', prompt ? `editing "${prompt.name}"` : 'new prompt');
        
        const modal = document.getElementById('prompt-editor-modal');
        const title = document.getElementById('prompt-editor-title');
        const deleteBtn = document.getElementById('delete-prompt');
        
        if (!modal) {
            console.error('Prompt editor modal not found');
            this.showToast('Could not open prompt editor', 'error');
            return;
        }
        
        if (prompt) {
            // Edit existing prompt
            title.textContent = 'Edit System Prompt';
            document.getElementById('prompt-id').value = prompt.id;
            document.getElementById('prompt-name').value = prompt.name;
            document.getElementById('prompt-description').value = prompt.description || '';
            document.getElementById('prompt-content').value = prompt.content;
            deleteBtn.style.display = 'inline-block';
            this.currentPromptId = prompt.id;
            this.showToast(`Editing prompt: ${prompt.name}`, 'info');
        } else {
            // Create new prompt
            title.textContent = 'Create System Prompt';
            document.getElementById('prompt-id').value = '';
            document.getElementById('prompt-name').value = '';
            document.getElementById('prompt-description').value = '';
            document.getElementById('prompt-content').value = '';
            deleteBtn.style.display = 'none';
            this.currentPromptId = null;
            this.showToast('Creating new prompt', 'info');
        }
        
        modal.style.display = 'block';
        
        // Focus on the name field
        const nameField = document.getElementById('prompt-name');
        if (nameField) {
            setTimeout(() => nameField.focus(), 100);
        }
    }

    async saveSystemPrompt() {
        console.log('Saving system prompt...');
        this.showToast('Saving prompt...', 'info');
        
        const promptId = document.getElementById('prompt-id').value;
        const name = document.getElementById('prompt-name').value.trim();
        const description = document.getElementById('prompt-description').value.trim();
        const content = document.getElementById('prompt-content').value.trim();

        if (!name || !content) {
            console.warn('Validation failed: name and content are required');
            ApiUtils.showGlobalStatus('Name and content are required', 'error');
            this.showToast('Name and content are required', 'error');
            return;
        }

        const data = { name, description, content };
        const isEdit = promptId !== '';
        const url = isEdit ? `/api/system_prompts/${promptId}` : '/api/system_prompts';
        const method = isEdit ? 'PUT' : 'POST';

        console.log(`${isEdit ? 'Updating' : 'Creating'} prompt:`, { name, description: description || 'No description' });

        try {
            const result = await ApiUtils.safeFetch(url, {
                method: method,
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data)
            });

            if (result) {
                const message = isEdit ? 'System prompt updated successfully' : 'System prompt created successfully';
                console.log('Prompt saved successfully:', result);
                ApiUtils.showGlobalStatus(message, 'success');
                this.showToast(message, 'success');
                
                document.getElementById('prompt-editor-modal').style.display = 'none';
                await this.loadSystemPrompts();
                this.renderSystemPromptsList();
            }
        } catch (error) {
            console.error('Error saving system prompt:', error);
            ApiUtils.showGlobalStatus('Failed to save system prompt', 'error');
            this.showToast('Failed to save system prompt', 'error');
        }
    }

    async deleteSystemPrompt(promptId) {
        console.log('Deleting system prompt:', promptId);
        this.showToast('Deleting prompt...', 'warning');
        
        try {
            const result = await ApiUtils.safeFetch(`/api/system_prompts/${promptId}`, {
                method: 'DELETE'
            });

            if (result && result.success) {
                console.log('System prompt deleted successfully:', promptId);
                ApiUtils.showGlobalStatus('System prompt deleted successfully', 'success');
                this.showToast('System prompt deleted successfully', 'success');
                
                document.getElementById('prompt-editor-modal').style.display = 'none';
                await this.loadSystemPrompts();
                this.renderSystemPromptsList();
                
                // Clear current selection if this was the selected prompt
                if (this.currentPromptId === promptId) {
                    this.currentPromptId = null;
                    localStorage.removeItem('selectedSystemPromptId');
                }
            }
        } catch (error) {
            console.error('Error deleting system prompt:', error);
            ApiUtils.showGlobalStatus('Failed to delete system prompt', 'error');
            this.showToast('Failed to delete system prompt', 'error');
        }
    }

    getCurrentPrompts() {
        console.log('Getting current prompts, count:', this.currentSystemPrompts.length);
        return this.currentSystemPrompts;
    }

    /**
     * Get the currently selected prompt ID
     */
    getCurrentPromptId() {
        return this.currentPromptId || localStorage.getItem('selectedSystemPromptId');
    }

    /**
     * Get the currently selected prompt object
     */
    getCurrentPrompt() {
        const currentId = this.getCurrentPromptId();
        if (currentId) {
            return this.currentSystemPrompts.find(p => p.id == currentId);
        }
        return null;
    }

    /**
     * Initialize the manager on page load
     */
    static initialize() {
        if (window.systemPromptsManager) {
            console.log('System Prompts Manager already initialized');
            return window.systemPromptsManager;
        }
        
        console.log('Initializing System Prompts Manager...');
        window.systemPromptsManager = new SystemPromptsManager();
        return window.systemPromptsManager;
    }
}

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        SystemPromptsManager.initialize();
    });
} else {
    SystemPromptsManager.initialize();
}

// Export for external access
export { SystemPromptsManager };
