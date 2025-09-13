/**
 * Workspace Manager Module
 * Handles workspace path configuration and management
 */

import { ApiUtils } from '../utils/api-utils.js';

export class WorkspaceManager {
    constructor() {
        this.currentWorkspacePath = '';
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
        this.loadWorkspacePath();
        this.setupEventListeners();
    }

    setupEventListeners() {
        // Change workspace button
        const changeWorkspaceBtn = document.getElementById('change-workspace');
        if (changeWorkspaceBtn) {
            window.eventManager.add(changeWorkspaceBtn, 'click', () => this.showWorkspaceModal());
        }

        // Manage chat sessions button
        const manageChatBtn = document.getElementById('manage-chat-sessions');
        if (manageChatBtn) {
            window.eventManager.add(manageChatBtn, 'click', () => this.showChatSessionsModal());
        }

        // Save chat session button
        const saveChatBtn = document.getElementById('save-chat-session');
        if (saveChatBtn) {
            window.eventManager.add(saveChatBtn, 'click', () => this.saveChatSession());
        }

        // Save workspace button
        const saveWorkspaceBtn = document.getElementById('save-workspace');
        if (saveWorkspaceBtn) {
            window.eventManager.add(saveWorkspaceBtn, 'click', () => this.saveWorkspacePath());
        }

        // Cancel workspace button
        const cancelWorkspaceBtn = document.getElementById('cancel-workspace');
        if (cancelWorkspaceBtn) {
            window.eventManager.add(cancelWorkspaceBtn, 'click', () => this.hideWorkspaceModal());
        }
    }

    async loadWorkspacePath() {
        try {
            const data = await ApiUtils.safeFetch('/api/workspace');
            if (data && data.workspace_path) {
                this.currentWorkspacePath = data.workspace_path;
                const workspacePathElement = document.getElementById('workspace-path');
                if (workspacePathElement) {
                    workspacePathElement.value = data.workspace_path;
                }

                // Update workspace status
                this.updateWorkspaceStatus(data);
            }
        } catch (error) {
            console.error('Error loading workspace path:', error);
            ApiUtils.showGlobalStatus('Failed to load workspace configuration', 'error');
        }
    }

    updateWorkspaceStatus(workspaceData) {
        const statusElement = document.getElementById('workspace-status');
        if (statusElement) {
            let statusText = '';
            let statusClass = '';

            if (!workspaceData.exists) {
                statusText = 'Directory does not exist';
                statusClass = 'status-warning';
            } else if (!workspaceData.readable || !workspaceData.writable) {
                statusText = 'Directory has permission issues';
                statusClass = 'status-error';
            } else {
                statusText = 'Directory is accessible';
                statusClass = 'status-success';
            }

            statusElement.textContent = statusText;
            statusElement.className = `workspace-status ${statusClass}`;
        }
    }

    showWorkspaceModal() {
        const currentPath = document.getElementById('workspace-path').value;
        const newPathInput = document.getElementById('new-workspace-path');
        if (newPathInput) {
            newPathInput.value = currentPath;
        }
        
        const modal = document.getElementById('workspace-modal');
        if (modal) {
            modal.style.display = 'block';
        }
    }

    async saveWorkspacePath() {
        const newPathInput = document.getElementById('new-workspace-path');
        if (!newPathInput) return;

        const newPath = newPathInput.value.trim();
        if (!newPath) {
            ApiUtils.showGlobalStatus('Workspace path cannot be empty', 'error');
            return;
        }

        try {
            const data = await ApiUtils.safeFetch('/api/workspace', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ workspace_path: newPath })
            });

            if (data && data.success) {
                this.currentWorkspacePath = newPath;
                document.getElementById('workspace-path').value = newPath;
                document.getElementById('workspace-modal').style.display = 'none';
                ApiUtils.showGlobalStatus('Workspace path updated successfully', 'success');
                
                // Reload workspace status
                await this.loadWorkspacePath();
            } else {
                ApiUtils.showGlobalStatus('Failed to update workspace path', 'error');
            }
        } catch (error) {
            console.error('Error saving workspace path:', error);
            ApiUtils.showGlobalStatus('Error updating workspace path', 'error');
        }
    }

    getCurrentWorkspacePath() {
        return this.currentWorkspacePath;
    }

    showChatSessionsModal() {
        this.loadSavedSessions();
        const modal = this.createSessionsModal();
        document.body.appendChild(modal);
        modal.style.display = 'flex';
    }

    async saveChatSession() {
        const title = prompt('Enter a title for this chat session:');
        if (!title) return;

        try {
            // Get current chat history from the chat interface
            const chatMessages = this.getCurrentChatHistory();
            
            if (chatMessages.length === 0) {
                ApiUtils.showGlobalStatus('No chat messages to save', 'warning');
                return;
            }

            const sessionData = {
                title: title,
                messages: chatMessages,
                timestamp: new Date().toISOString(),
                message_count: chatMessages.length
            };

            const response = await fetch('/api/chat/save_session', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(sessionData)
            });

            if (response.ok) {
                await response.json();
                ApiUtils.showGlobalStatus(`Chat session "${title}" saved successfully!`, 'success');
            } else {
                throw new Error('Failed to save chat session');
            }
        } catch (error) {
            console.error('Error saving chat session:', error);
            ApiUtils.showGlobalStatus('Failed to save chat session', 'error');
        }
    }

    getCurrentChatHistory() {
        // Try to get chat messages from the chat interface
        const chatContainer = document.querySelector('#chat-messages, .chat-messages, .messages-container');
        const messages = [];
        
        if (chatContainer) {
            const messageElements = chatContainer.querySelectorAll('.message, .chat-message');
            messageElements.forEach(element => {
                const isUser = element.classList.contains('user') || element.classList.contains('user-message');
                const content = element.querySelector('.message-content, .content')?.textContent || element.textContent;
                
                if (content && content.trim()) {
                    messages.push({
                        role: isUser ? 'user' : 'assistant',
                        content: content.trim(),
                        timestamp: new Date().toISOString()
                    });
                }
            });
        }
        
        return messages;
    }

    async loadSavedSessions() {
        try {
            const response = await fetch('/api/chat/sessions');
            if (response.ok) {
                this.savedSessions = await response.json();
            } else {
                this.savedSessions = [];
            }
        } catch (error) {
            console.error('Error loading saved sessions:', error);
            this.savedSessions = [];
        }
    }

    createSessionsModal() {
        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.innerHTML = `
            <div class="modal-content" style="max-width: 800px; max-height: 600px;">
                <div class="modal-header">
                    <h3>💬 Saved Chat Sessions</h3>
                    <button class="modal-close">&times;</button>
                </div>
                <div class="modal-body">
                    <div id="sessions-list" style="max-height: 400px; overflow-y: auto;">
                        ${this.renderSessionsList()}
                    </div>
                </div>
                <div class="modal-footer">
                    <button class="settings-button secondary modal-close">Close</button>
                    <button id="refresh-sessions" class="settings-button primary">Refresh</button>
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

        const refreshBtn = modal.querySelector('#refresh-sessions');
        window.eventManager.add(refreshBtn, 'click', async () => {
            await this.loadSavedSessions();
            modal.querySelector('#sessions-list').innerHTML = this.renderSessionsList();
        });

        return modal;
    }

    renderSessionsList() {
        if (!this.savedSessions || this.savedSessions.length === 0) {
            return '<p style="text-align: center; color: var(--text-muted); padding: 2rem;">No saved chat sessions found.</p>';
        }

        return this.savedSessions.map(session => `
            <div class="session-item" style="border: 1px solid var(--border-color); border-radius: 8px; padding: 1rem; margin-bottom: 1rem; background: var(--surface-color);">
                <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.5rem;">
                    <h4 style="margin: 0; color: var(--text-color);">${session.title}</h4>
                    <div class="session-actions">
                        <button class="settings-button small" onclick="workspaceManager.loadChatSession('${session.id}')">Load</button>
                        <button class="settings-button small danger" onclick="workspaceManager.deleteChatSession('${session.id}')">Delete</button>
                    </div>
                </div>
                <div style="font-size: 0.9rem; color: var(--text-muted);">
                    <span>📅 ${new Date(session.created_at).toLocaleDateString()}</span>
                    <span style="margin-left: 1rem;">💬 ${session.message_count} messages</span>
                </div>
            </div>
        `).join('');
    }

    async loadChatSession(sessionId) {
        try {
            const response = await fetch(`/api/chat/sessions/${sessionId}`);
            if (response.ok) {
                const session = await response.json();
                // Dispatch event to chat interface to load the session
                window.dispatchEvent(new CustomEvent('loadChatSession', { detail: session }));
                ApiUtils.showGlobalStatus(`Loaded chat session: ${session.title}`, 'success');
            }
        } catch (error) {
            console.error('Error loading chat session:', error);
            ApiUtils.showGlobalStatus('Failed to load chat session', 'error');
        }
    }

    async deleteChatSession(sessionId) {
        if (!confirm('Are you sure you want to delete this chat session?')) return;

        try {
            const response = await fetch(`/api/chat/sessions/${sessionId}`, {
                method: 'DELETE'
            });

            if (response.ok) {
                await this.loadSavedSessions();
                const modal = document.querySelector('.modal:last-child');
                if (modal) {
                    modal.querySelector('#sessions-list').innerHTML = this.renderSessionsList();
                }
                ApiUtils.showGlobalStatus('Chat session deleted', 'success');
            }
        } catch (error) {
            console.error('Error deleting chat session:', error);
            ApiUtils.showGlobalStatus('Failed to delete chat session', 'error');
        }
    }

    async validateWorkspacePath(path) {
        try {
            const data = await ApiUtils.safeFetch('/api/workspace/validate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ workspace_path: path })
            });
            return data;
        } catch (error) {
            console.error('Error validating workspace path:', error);
            return { valid: false, error: 'Validation failed' };
        }
    }

    hideWorkspaceModal() {
        const modal = document.getElementById('workspace-modal');
        if (modal) {
            modal.style.display = 'none';
        }
    }
}
