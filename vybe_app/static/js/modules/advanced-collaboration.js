/**
 * Advanced Collaboration Tools
 * Real-time multi-user collaboration with document sharing and editing
 */

export class AdvancedCollaboration {
    constructor() {
        this.sessions = new Map();
        this.activeUsers = new Map();
        this.sharedDocuments = new Map();
        this.collaborationRooms = new Map();
        this.realTimeConnections = new Map();
        this.permissions = new Map();
        
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
        this.setupWebSocketConnections();
        this.setupEventListeners();
        this.initializeUI();
        this.loadCollaborationData();
    }

    setupWebSocketConnections() {
        // Initialize WebSocket for real-time collaboration
        this.websocket = new WebSocket(`ws://${window.location.host}/ws/collaboration`);
        
        this.websocket.onopen = () => {
            console.log('Collaboration WebSocket connected');
            this.sendMessage('join', { userId: this.getCurrentUserId() });
        };

        this.websocket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleWebSocketMessage(data);
        };

        this.websocket.onclose = () => {
            console.log('Collaboration WebSocket disconnected');
            setTimeout(() => this.setupWebSocketConnections(), 5000);
        };
    }

    setupEventListeners() {
        // Collaboration session management
        const createSessionBtn = document.getElementById('create-collaboration-session');
        if (createSessionBtn) {
            window.eventManager.add(createSessionBtn, 'click', () => this.createCollaborationSession());
        }

        // Document sharing
        const shareDocumentBtn = document.getElementById('share-document');
        if (shareDocumentBtn) {
            window.eventManager.add(shareDocumentBtn, 'click', () => this.showDocumentSharing());
        }

        // User management
        const inviteUserBtn = document.getElementById('invite-user');
        if (inviteUserBtn) {
            window.eventManager.add(inviteUserBtn, 'click', () => this.showUserInvitation());
        }

        // Refresh buttons
        const refreshSharedDocsBtn = document.getElementById('refresh-shared-docs');
        if (refreshSharedDocsBtn) {
            window.eventManager.add(refreshSharedDocsBtn, 'click', () => this.loadSharedDocuments());
        }

        const refreshUsersBtn = document.getElementById('refresh-users');
        if (refreshUsersBtn) {
            window.eventManager.add(refreshUsersBtn, 'click', () => this.loadUsers());
        }

        // Chat room creation
        const createChatRoomBtn = document.getElementById('create-chat-room');
        if (createChatRoomBtn) {
            window.eventManager.add(createChatRoomBtn, 'click', () => this.createChatRoom());
        }

        // File attachment and emoji picker
        const attachFileBtn = document.getElementById('attach-file');
        if (attachFileBtn) {
            window.eventManager.add(attachFileBtn, 'click', () => this.showFileAttachment());
        }

        const emojiPickerBtn = document.getElementById('emoji-picker');
        if (emojiPickerBtn) {
            window.eventManager.add(emojiPickerBtn, 'click', () => this.showEmojiPicker());
        }

        // Session and user filters
        const sessionFilter = document.getElementById('session-filter');
        if (sessionFilter) {
            window.eventManager.add(sessionFilter, 'change', () => this.filterSessions());
        }

        const userFilter = document.getElementById('user-filter');
        if (userFilter) {
            window.eventManager.add(userFilter, 'change', () => this.filterUsers());
        }

        // Search functionality
        const sessionSearch = document.getElementById('session-search');
        if (sessionSearch) {
            window.eventManager.add(sessionSearch, 'input', window.eventManager.debounce(() => this.searchSessions(), 300));
        }
    }

    initializeUI() {
        this.createCollaborationInterface();
        this.createSessionManager();
        this.createDocumentSharing();
        this.createUserManagement();
        this.createRealTimeChat();
    }

    createCollaborationInterface() {
        const container = document.getElementById('advanced-collaboration-interface');
        if (!container) return;

        container.innerHTML = `
            <div class="collaboration-header">
                <h3>Advanced Collaboration</h3>
                <div class="collaboration-controls">
                    <button id="create-collaboration-session" class="btn btn-primary">
                        <i class="fas fa-plus"></i> New Session
                    </button>
                    <button id="share-document" class="btn btn-info">
                        <i class="fas fa-share"></i> Share Document
                    </button>
                    <button id="invite-user" class="btn btn-success">
                        <i class="fas fa-user-plus"></i> Invite User
                    </button>
                </div>
            </div>
            <div class="collaboration-dashboard">
                <div class="dashboard-stats">
                    <div class="stat-card">
                        <h4>Active Sessions</h4>
                        <div class="stat-value" id="active-sessions">0</div>
                    </div>
                    <div class="stat-card">
                        <h4>Online Users</h4>
                        <div class="stat-value" id="online-users">0</div>
                    </div>
                    <div class="stat-card">
                        <h4>Shared Documents</h4>
                        <div class="stat-value" id="shared-documents">0</div>
                    </div>
                    <div class="stat-card">
                        <h4>Collaboration Rooms</h4>
                        <div class="stat-value" id="collaboration-rooms">0</div>
                    </div>
                </div>
            </div>
        `;
    }

    createSessionManager() {
        const container = document.getElementById('session-manager');
        if (!container) return;

        container.innerHTML = `
            <div class="session-header">
                <h4>Collaboration Sessions</h4>
                <div class="session-filters">
                    <select id="session-filter">
                        <option value="all">All Sessions</option>
                        <option value="active">Active</option>
                        <option value="archived">Archived</option>
                    </select>
                    <input type="text" id="session-search" placeholder="Search sessions...">
                </div>
            </div>
            <div class="sessions-grid" id="sessions-grid"></div>
        `;

        this.loadSessions();
    }

    createDocumentSharing() {
        const container = document.getElementById('document-sharing');
        if (!container) return;

        container.innerHTML = `
            <div class="sharing-header">
                <h4>Document Sharing</h4>
                <button id="refresh-shared-docs" class="btn btn-secondary">
                    <i class="fas fa-sync"></i> Refresh
                </button>
            </div>
            <div class="shared-documents-grid" id="shared-documents-grid"></div>
        `;

        this.loadSharedDocuments();
    }

    createUserManagement() {
        const container = document.getElementById('user-management');
        if (!container) return;

        container.innerHTML = `
            <div class="user-header">
                <h4>User Management</h4>
                <div class="user-controls">
                    <select id="user-filter">
                        <option value="all">All Users</option>
                        <option value="online">Online</option>
                        <option value="offline">Offline</option>
                    </select>
                    <button id="refresh-users" class="btn btn-secondary">
                        <i class="fas fa-sync"></i> Refresh
                    </button>
                </div>
            </div>
            <div class="users-grid" id="users-grid"></div>
        `;

        this.loadUsers();
    }

    createRealTimeChat() {
        const container = document.getElementById('real-time-chat');
        if (!container) return;

        container.innerHTML = `
            <div class="chat-header">
                <h4>Real-time Chat</h4>
                <div class="chat-controls">
                    <select id="chat-room-selector">
                        <option value="general">General</option>
                    </select>
                    <button id="create-chat-room" class="btn btn-sm btn-primary">
                        <i class="fas fa-plus"></i> New Room
                    </button>
                </div>
            </div>
            <div class="chat-container">
                <div class="chat-messages" id="chat-messages">
                    <div class="chat-placeholder">
                        <i class="fas fa-comments"></i>
                        <p>Start a conversation in the chat room</p>
                    </div>
                </div>
                <div class="chat-input-area">
                    <div class="chat-input-wrapper">
                        <input type="text" id="chat-input" placeholder="Type your message...">
                        <button id="send-message" class="btn btn-primary">
                            <i class="fas fa-paper-plane"></i>
                        </button>
                    </div>
                    <div class="chat-actions">
                        <button id="attach-file" class="btn btn-sm btn-secondary">
                            <i class="fas fa-paperclip"></i>
                        </button>
                        <button id="emoji-picker" class="btn btn-sm btn-secondary">
                            <i class="fas fa-smile"></i>
                        </button>
                    </div>
                </div>
            </div>
        `;

        this.setupChatHandlers();
    }

    setupChatHandlers() {
        const chatInput = document.getElementById('chat-input');
        const sendButton = document.getElementById('send-message');

        if (chatInput && sendButton) {
            window.eventManager.add(sendButton, 'click', () => this.sendChatMessage());
            
            window.eventManager.add(chatInput, 'keypress', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.sendChatMessage();
                }
            });
        }
    }

    async createCollaborationSession() {
        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h3>Create Collaboration Session</h3>
                    <button class="close-modal">&times;</button>
                </div>
                <div class="modal-body">
                    <form id="session-form">
                        <div class="form-group">
                            <label for="session-name">Session Name:</label>
                            <input type="text" id="session-name" required placeholder="Enter session name">
                        </div>
                        <div class="form-group">
                            <label for="session-description">Description:</label>
                            <textarea id="session-description" placeholder="Enter session description"></textarea>
                        </div>
                        <div class="form-group">
                            <label for="session-type">Session Type:</label>
                            <select id="session-type">
                                <option value="document-editing">Document Editing</option>
                                <option value="brainstorming">Brainstorming</option>
                                <option value="code-review">Code Review</option>
                                <option value="presentation">Presentation</option>
                                <option value="meeting">Meeting</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label for="session-privacy">Privacy:</label>
                            <select id="session-privacy">
                                <option value="public">Public</option>
                                <option value="private">Private</option>
                                <option value="invite-only">Invite Only</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label for="session-duration">Duration (hours):</label>
                            <input type="number" id="session-duration" min="1" max="24" value="2">
                        </div>
                    </form>
                </div>
                <div class="modal-footer">
                    <button id="create-session" class="btn btn-primary">Create Session</button>
                    <button class="btn btn-secondary close-modal">Cancel</button>
                </div>
            </div>
        `;

        document.body.appendChild(modal);
        this.setupSessionCreationHandlers(modal);
    }

    setupSessionCreationHandlers(modal) {
        const createBtn = modal.querySelector('#create-session');

        window.eventManager.add(createBtn, 'click', async () => {
            console.log('[AdvancedCollaboration] Creating collaboration session...');
            
            const sessionName = document.getElementById('session-name').value.trim();
            if (!sessionName) {
                window.notificationManager?.showError('Session name is required');
                return;
            }
            
            const sessionData = {
                name: sessionName,
                description: document.getElementById('session-description').value.trim(),
                type: document.getElementById('session-type').value,
                privacy: document.getElementById('session-privacy').value,
                duration: parseInt(document.getElementById('session-duration').value),
                max_participants: 50,
                is_public: document.getElementById('session-privacy').value === 'public'
            };

            // Show loading state
            createBtn.disabled = true;
            createBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Creating...';
            
            try {
                const response = await fetch('/api/collaboration/sessions', {
                    method: 'POST',
                    headers: { 
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(sessionData)
                });

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                
                const data = await response.json();
                
                if (data.success) {
                    console.log('[AdvancedCollaboration] Session created successfully:', data.session.id);
                    window.notificationManager?.showSuccess(`Session "${sessionName}" created successfully`);
                    this.loadSessions();
                    modal.remove();
                } else {
                    throw new Error(data.error || 'Failed to create session');
                }
            } catch (error) {
                console.error('Error creating session:', error);
                window.notificationManager?.showError(`Failed to create session: ${error.message}`);
            } finally {
                // Re-enable button
                createBtn.disabled = false;
                createBtn.innerHTML = 'Create Session';
            }
        });

        modal.querySelectorAll('.close-modal').forEach(btn => {
            window.eventManager.add(btn, 'click', () => modal.remove());
        });
    }

    async showDocumentSharing() {
        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h3>Share Document</h3>
                    <button class="close-modal">&times;</button>
                </div>
                <div class="modal-body">
                    <div class="document-selection">
                        <h4>Select Document to Share</h4>
                        <div class="document-list" id="document-list">
                            <div class="loading">Loading documents...</div>
                        </div>
                    </div>
                    <div class="sharing-options">
                        <h4>Sharing Options</h4>
                        <div class="option-group">
                            <label for="share-permissions">Permissions:</label>
                            <select id="share-permissions">
                                <option value="view">View Only</option>
                                <option value="comment">Comment</option>
                                <option value="edit">Edit</option>
                                <option value="admin">Admin</option>
                            </select>
                        </div>
                        <div class="option-group">
                            <label for="share-expiry">Expiry Date:</label>
                            <input type="datetime-local" id="share-expiry">
                        </div>
                        <div class="option-group">
                            <label for="share-password">Password Protection:</label>
                            <input type="password" id="share-password" placeholder="Optional password">
                        </div>
                    </div>
                    <div class="user-invitation">
                        <h4>Invite Users</h4>
                        <div class="user-search">
                            <input type="text" id="user-search" placeholder="Search users...">
                            <div class="user-results" id="user-results"></div>
                        </div>
                        <div class="invited-users" id="invited-users"></div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button id="share-document-btn" class="btn btn-primary">Share Document</button>
                    <button class="btn btn-secondary close-modal">Cancel</button>
                </div>
            </div>
        `;

        document.body.appendChild(modal);
        this.setupDocumentSharingHandlers(modal);
        this.loadAvailableDocuments(modal);
    }

    setupDocumentSharingHandlers(modal) {
        const shareBtn = modal.querySelector('#share-document-btn');
        const userSearch = modal.querySelector('#user-search');

        window.eventManager.add(shareBtn, 'click', async () => {
            const selectedDocument = modal.querySelector('.document-item.selected');
            if (!selectedDocument) {
                window.notificationManager?.showError('Please select a document to share');
                return;
            }

            const sharingData = {
                documentId: selectedDocument.dataset.id,
                permissions: document.getElementById('share-permissions').value,
                expiryDate: document.getElementById('share-expiry').value,
                password: document.getElementById('share-password').value,
                invitedUsers: this.getInvitedUsers(modal)
            };

            console.log('[AdvancedCollaboration] Sharing document:', sharingData.documentId);
            
            // Show loading state
            shareBtn.disabled = true;
            shareBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Sharing...';

            try {
                const response = await fetch('/api/documents/share', {
                    method: 'POST',
                    headers: { 
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(sharingData)
                });

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                
                const data = await response.json();
                
                if (data.success) {
                    console.log('[AdvancedCollaboration] Document shared successfully');
                    window.notificationManager?.showSuccess('Document shared successfully');
                    this.loadSharedDocuments();
                    modal.remove();
                } else {
                    throw new Error(data.error || 'Failed to share document');
                }
            } catch (error) {
                console.error('Error sharing document:', error);
                window.notificationManager?.showError(`Failed to share document: ${error.message}`);
            } finally {
                // Re-enable button
                shareBtn.disabled = false;
                shareBtn.innerHTML = 'Share Document';
            }
        });

        // User search functionality
        if (userSearch) {
            window.eventManager.add(userSearch, 'input', window.eventManager.debounce((e) => {
                this.searchUsers(e.target.value, modal);
            }, 100));
        }

        modal.querySelectorAll('.close-modal').forEach(btn => {
            window.eventManager.add(btn, 'click', () => modal.remove());
        });
    }

    async showUserInvitation() {
        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h3>Invite Users</h3>
                    <button class="close-modal">&times;</button>
                </div>
                <div class="modal-body">
                    <div class="invitation-methods">
                        <div class="method-tabs">
                            <button class="tab-btn active" data-tab="email">Email Invitation</button>
                            <button class="tab-btn" data-tab="link">Share Link</button>
                            <button class="tab-btn" data-tab="users">Existing Users</button>
                        </div>
                        
                        <div class="tab-content active" id="email-tab">
                            <div class="form-group">
                                <label for="invite-emails">Email Addresses:</label>
                                <textarea id="invite-emails" placeholder="Enter email addresses (one per line)"></textarea>
                            </div>
                            <div class="form-group">
                                <label for="invite-message">Personal Message:</label>
                                <textarea id="invite-message" placeholder="Optional personal message"></textarea>
                            </div>
                        </div>
                        
                        <div class="tab-content" id="link-tab">
                            <div class="form-group">
                                <label for="invite-link">Invitation Link:</label>
                                <div class="link-display">
                                    <input type="text" id="invite-link" readonly>
                                    <button id="copy-link" class="btn btn-secondary">Copy</button>
                                </div>
                            </div>
                            <div class="form-group">
                                <label for="link-expiry">Link Expiry:</label>
                                <select id="link-expiry">
                                    <option value="1">1 day</option>
                                    <option value="7">7 days</option>
                                    <option value="30">30 days</option>
                                    <option value="never">Never</option>
                                </select>
                            </div>
                        </div>
                        
                        <div class="tab-content" id="users-tab">
                            <div class="form-group">
                                <label for="user-search-invite">Search Users:</label>
                                <input type="text" id="user-search-invite" placeholder="Search by name or email">
                            </div>
                            <div class="user-list" id="user-list-invite"></div>
                        </div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button id="send-invitations" class="btn btn-primary">Send Invitations</button>
                    <button class="btn btn-secondary close-modal">Cancel</button>
                </div>
            </div>
        `;

        document.body.appendChild(modal);
        this.setupUserInvitationHandlers(modal);
    }

    setupUserInvitationHandlers(modal) {
        const tabBtns = modal.querySelectorAll('.tab-btn');
        const sendBtn = modal.querySelector('#send-invitations');
        const copyLinkBtn = modal.querySelector('#copy-link');

        // Tab switching
        tabBtns.forEach(btn => {
            window.eventManager.add(btn, 'click', () => {
                tabBtns.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                
                const tabContents = modal.querySelectorAll('.tab-content');
                tabContents.forEach(content => content.classList.remove('active'));
                
                const targetTab = modal.querySelector(`#${btn.dataset.tab}-tab`);
                if (targetTab) targetTab.classList.add('active');
            });
        });

        // Send invitations
        window.eventManager.add(sendBtn, 'click', async () => {
            const activeTab = modal.querySelector('.tab-btn.active').dataset.tab;
            let invitationData = {};

            switch (activeTab) {
                case 'email': {
                    const emails = document.getElementById('invite-emails').value.split('\n').filter(e => e.trim());
                    const message = document.getElementById('invite-message').value;
                    invitationData = { type: 'email', emails, message };
                    break;
                }
                case 'link': {
                    const link = document.getElementById('invite-link').value;
                    const expiry = document.getElementById('link-expiry').value;
                    invitationData = { type: 'link', link, expiry };
                    break;
                }
                case 'users': {
                    const selectedUsers = this.getSelectedUsers(modal);
                    invitationData = { type: 'users', users: selectedUsers };
                    break;
                }
            }

            try {
                const response = await fetch('/api/collaboration/invite_users', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(invitationData)
                });

                if (response.ok) {
                    this.showNotification('Invitations sent successfully', 'success');
                    modal.remove();
                } else {
                    throw new Error('Failed to send invitations');
                }
            } catch (error) {
                console.error('Error sending invitations:', error);
                this.showNotification('Failed to send invitations', 'error');
            }
        });

        // Copy link
        if (copyLinkBtn) {
            window.eventManager.add(copyLinkBtn, 'click', () => {
                const shareLink = modal.querySelector('#share-link').value;
                navigator.clipboard.writeText(shareLink);
                this.showNotification('Link copied to clipboard', 'success');
            });
        }

        modal.querySelectorAll('.close-modal').forEach(btn => {
            window.eventManager.add(btn, 'click', () => modal.remove());
        });
    }

    handleWebSocketMessage(data) {
        switch (data.type) {
            case 'user_joined':
                this.handleUserJoined(data);
                break;
            case 'user_left':
                this.handleUserLeft(data);
                break;
            case 'chat_message':
                this.handleChatMessage(data);
                break;
            case 'document_update':
                this.handleDocumentUpdate(data);
                break;
            case 'session_update':
                this.handleSessionUpdate(data);
                break;
            case 'permission_change':
                this.handlePermissionChange(data);
                break;
        }
    }

    handleUserJoined(data) {
        this.activeUsers.set(data.userId, data.user);
        this.updateOnlineUsersCount();
        this.addChatMessage('system', `${data.user.name} joined the session`);
    }

    handleUserLeft(data) {
        this.activeUsers.delete(data.userId);
        this.updateOnlineUsersCount();
        this.addChatMessage('system', `${data.user.name} left the session`);
    }

    handleChatMessage(data) {
        this.addChatMessage('user', data.message, data.user);
    }

    handleDocumentUpdate(data) {
        // Handle real-time document updates
        this.updateDocumentContent(data.documentId, data.changes);
    }

    handleSessionUpdate(data) {
        // Handle session updates
        this.updateSessionInfo(data.sessionId, data.updates);
    }

    handlePermissionChange(data) {
        // Handle permission changes
        this.updateUserPermissions(data.userId, data.permissions);
    }

    sendMessage(type, data) {
        if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
            this.websocket.send(JSON.stringify({ type, data }));
        }
    }

    sendChatMessage() {
        const input = document.getElementById('chat-input');
        const message = input.value.trim();
        
        if (message) {
            this.sendMessage('chat_message', { message });
            input.value = '';
        }
    }

    addChatMessage(type, message, user = null) {
        const chatMessages = document.getElementById('chat-messages');
        if (!chatMessages) return;

        const messageDiv = document.createElement('div');
        messageDiv.className = `chat-message chat-${type}`;
        
        const timestamp = new Date().toLocaleTimeString();
        
        if (type === 'system') {
            messageDiv.innerHTML = `
                <div class="message-content system">
                    <span class="message-text">${message}</span>
                    <span class="message-time">${timestamp}</span>
                </div>
            `;
        } else {
            messageDiv.innerHTML = `
                <div class="message-content">
                    <div class="message-header">
                        <span class="user-name">${user ? user.name : 'You'}</span>
                        <span class="message-time">${timestamp}</span>
                    </div>
                    <div class="message-text">${message}</div>
                </div>
            `;
        }

        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    async loadSessions() {
        console.log('[AdvancedCollaboration] Loading collaboration sessions...');
        
        // Show loading state
        const grid = document.getElementById('sessions-grid');
        if (grid) {
            grid.innerHTML = `
                <div class="loading-state">
                    <i class="fas fa-spinner fa-spin"></i>
                    <p>Loading collaboration sessions...</p>
                </div>
            `;
        }
        
        try {
            const response = await fetch('/api/collaboration/sessions', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            if (data.success) {
                this.sessions = new Map(Object.entries(data.sessions || {}));
                console.log(`[AdvancedCollaboration] Loaded ${this.sessions.size} sessions`);
                this.updateSessionsGrid();
                this.updateActiveSessionsCount();
                window.notificationManager?.showSuccess(`Loaded ${this.sessions.size} collaboration sessions`);
            } else {
                console.error('Failed to load sessions:', data.error);
                window.notificationManager?.showError(`Failed to load sessions: ${data.error}`);
                this.sessions = new Map();
                this.updateSessionsGrid();
            }
        } catch (error) {
            console.error('Error loading sessions:', error);
            window.notificationManager?.showError('Failed to load collaboration sessions. Please check your connection.');
            this.sessions = new Map();
            this.updateSessionsGrid();
        }
    }

    async loadSharedDocuments() {
        console.log('[AdvancedCollaboration] Loading shared documents...');
        
        // Show loading state
        const grid = document.getElementById('shared-documents-grid');
        if (grid) {
            grid.innerHTML = `
                <div class="loading-state">
                    <i class="fas fa-spinner fa-spin"></i>
                    <p>Loading shared documents...</p>
                </div>
            `;
        }
        
        try {
            const response = await fetch('/api/documents/shared', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            if (data.success) {
                this.sharedDocuments = new Map(Object.entries(data.documents || {}));
                console.log(`[AdvancedCollaboration] Loaded ${this.sharedDocuments.size} shared documents`);
                this.updateSharedDocumentsGrid();
                this.updateSharedDocumentsCount();
                window.notificationManager?.showSuccess(`Loaded ${this.sharedDocuments.size} shared documents`);
            } else {
                console.error('Failed to load shared documents:', data.error);
                window.notificationManager?.showError(`Failed to load shared documents: ${data.error}`);
                this.sharedDocuments = new Map();
                this.updateSharedDocumentsGrid();
            }
        } catch (error) {
            console.error('Error loading shared documents:', error);
            window.notificationManager?.showError('Failed to load shared documents. Please check your connection.');
            this.sharedDocuments = new Map();
            this.updateSharedDocumentsGrid();
        }
    }

    async loadUsers() {
        console.log('[AdvancedCollaboration] Loading users...');
        
        // Show loading state
        const grid = document.getElementById('users-grid');
        if (grid) {
            grid.innerHTML = `
                <div class="loading-state">
                    <i class="fas fa-spinner fa-spin"></i>
                    <p>Loading users...</p>
                </div>
            `;
        }
        
        try {
            const response = await fetch('/api/users/list', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            if (data.success) {
                const users = data.users || [];
                console.log(`[AdvancedCollaboration] Loaded ${users.length} users`);
                this.updateUsersGrid(users);
                this.updateOnlineUsersCount();
                window.notificationManager?.showSuccess(`Loaded ${users.length} users`);
            } else {
                console.error('Failed to load users:', data.error);
                window.notificationManager?.showError(`Failed to load users: ${data.error}`);
                this.updateUsersGrid([]);
            }
        } catch (error) {
            console.error('Error loading users:', error);
            window.notificationManager?.showError('Failed to load users. Please check your connection.');
            this.updateUsersGrid([]);
        }
    }

    updateSessionsGrid() {
        const grid = document.getElementById('sessions-grid');
        if (!grid) return;

        grid.innerHTML = Array.from(this.sessions.values()).map(session => `
            <div class="session-card" data-id="${session.id}">
                <div class="session-header">
                    <h5>${session.name}</h5>
                    <div class="session-status ${session.status}">${session.status}</div>
                </div>
                <div class="session-info">
                    <p>${session.description || 'No description'}</p>
                    <div class="session-meta">
                        <span>Type: ${session.type}</span>
                        <span>Privacy: ${session.privacy}</span>
                    </div>
                </div>
                <div class="session-participants">
                    <span>${session.participant_count || 0} participants</span>
                </div>
                <div class="session-actions">
                    <button class="btn btn-sm btn-primary" onclick="advancedCollaboration.joinSession('${session.id}')">
                        <i class="fas fa-sign-in-alt"></i> Join
                    </button>
                    <button class="btn btn-sm btn-info" onclick="advancedCollaboration.viewSession('${session.id}')">
                        <i class="fas fa-eye"></i> View
                    </button>
                </div>
            </div>
        `).join('');
    }

    updateSharedDocumentsGrid() {
        const grid = document.getElementById('shared-documents-grid');
        if (!grid) return;

        grid.innerHTML = Array.from(this.sharedDocuments.values()).map(doc => `
            <div class="document-card" data-id="${doc.id}">
                <div class="document-header">
                    <h5>${doc.name}</h5>
                    <div class="document-type">${doc.type}</div>
                </div>
                <div class="document-info">
                    <p>Shared by: ${doc.sharedBy}</p>
                    <div class="document-meta">
                        <span>Permissions: ${doc.permissions}</span>
                        <span>Expires: ${doc.expiryDate ? new Date(doc.expiryDate).toLocaleDateString() : 'Never'}</span>
                    </div>
                </div>
                <div class="document-actions">
                    <button class="btn btn-sm btn-primary" onclick="advancedCollaboration.openDocument('${doc.id}')">
                        <i class="fas fa-external-link-alt"></i> Open
                    </button>
                    <button class="btn btn-sm btn-secondary" onclick="advancedCollaboration.downloadDocument('${doc.id}')">
                        <i class="fas fa-download"></i> Download
                    </button>
                </div>
            </div>
        `).join('');
    }

    updateUsersGrid(users) {
        const grid = document.getElementById('users-grid');
        if (!grid) return;

        grid.innerHTML = users.map(user => `
            <div class="user-card" data-id="${user.id}">
                <div class="user-avatar">
                    <img src="${user.avatar || '/static/img/default-avatar.png'}" alt="${user.name}">
                    <div class="user-status ${user.status}"></div>
                </div>
                <div class="user-info">
                    <h5>${user.name}</h5>
                    <p>${user.email}</p>
                    <div class="user-meta">
                        <span>Role: ${user.role}</span>
                        <span>Last seen: ${user.lastSeen ? new Date(user.lastSeen).toLocaleString() : 'Never'}</span>
                    </div>
                </div>
                <div class="user-actions">
                    <button class="btn btn-sm btn-primary" onclick="advancedCollaboration.messageUser('${user.id}')">
                        <i class="fas fa-comment"></i> Message
                    </button>
                    <button class="btn btn-sm btn-info" onclick="advancedCollaboration.viewUserProfile('${user.id}')">
                        <i class="fas fa-user"></i> Profile
                    </button>
                </div>
            </div>
        `).join('');
    }

    updateActiveSessionsCount() {
        const countElement = document.getElementById('active-sessions');
        if (countElement) {
            const activeCount = Array.from(this.sessions.values()).filter(s => s.status === 'active').length;
            countElement.textContent = activeCount;
        }
    }

    updateOnlineUsersCount() {
        const countElement = document.getElementById('online-users');
        if (countElement) {
            countElement.textContent = this.activeUsers.size;
        }
    }

    updateSharedDocumentsCount() {
        const countElement = document.getElementById('shared-documents');
        if (countElement) {
            countElement.textContent = this.sharedDocuments.size;
        }
    }

    // Utility methods
    getCurrentUserId() {
        // Get current user ID from session or localStorage
        return localStorage.getItem('userId') || 'current_user';
    }

    getCurrentUserName() {
        // Get current user name from session or localStorage
        return localStorage.getItem('userName') || 'Current User';
    }

    showNotification(message, type = 'info') {
        console.log(`[AdvancedCollaboration] ${type.toUpperCase()}: ${message}`);
        
        // Use centralized notification manager if available
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
                default:
                    window.notificationManager.showInfo(message);
            }
        } else if (typeof window.showToast === 'function') {
            window.showToast(message, type);
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

    // Enhanced methods with backend integration
    async loadCollaborationData() {
        console.log('[AdvancedCollaboration] Loading collaboration data...');
        window.notificationManager?.showInfo('Loading collaboration data...');
        
        try {
            // Load initial collaboration data concurrently
            await Promise.all([
                this.loadSessions(),
                this.loadSharedDocuments(),
                this.loadUsers()
            ]);
            
            console.log('[AdvancedCollaboration] All collaboration data loaded successfully');
            window.notificationManager?.showSuccess('Collaboration data loaded successfully');
        } catch (error) {
            console.error('Error loading collaboration data:', error);
            window.notificationManager?.showError('Failed to load some collaboration data');
        }
    }

    async loadAvailableDocuments(modal) {
        console.log('[AdvancedCollaboration] Loading available documents for sharing...');
        
        // Show loading state in modal
        const documentList = modal.querySelector('#document-list');
        if (documentList) {
            documentList.innerHTML = `
                <div class="loading-state">
                    <i class="fas fa-spinner fa-spin"></i>
                    <p>Loading available documents...</p>
                </div>
            `;
        }
        
        try {
            const response = await fetch('/api/documents/available', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            if (data.success) {
                const documents = data.documents || [];
                console.log(`[AdvancedCollaboration] Loaded ${documents.length} available documents`);
                this.updateDocumentList(modal, documents);
                
                if (documents.length === 0) {
                    window.notificationManager?.showInfo('No documents available for sharing');
                }
            } else {
                console.error('Failed to load available documents:', data.error);
                window.notificationManager?.showError(`Failed to load documents: ${data.error}`);
                this.updateDocumentList(modal, []);
            }
        } catch (error) {
            console.error('Error loading available documents:', error);
            window.notificationManager?.showError('Failed to load available documents');
            this.updateDocumentList(modal, []);
        }
    }

    updateDocumentList(modal, documents) {
        const documentList = modal.querySelector('#document-list');
        if (!documentList) return;

        documentList.innerHTML = documents.map(doc => `
            <div class="document-item" data-id="${doc.id}">
                <i class="fas fa-file"></i>
                <div class="document-info">
                    <span class="document-name">${doc.name}</span>
                    <span class="document-type">${doc.type}</span>
                </div>
                <div class="document-meta">
                    <span>Modified: ${new Date(doc.modifiedAt).toLocaleDateString()}</span>
                </div>
            </div>
        `).join('');

        // Add click handlers
        documentList.querySelectorAll('.document-item').forEach(item => {
            window.eventManager.add(item, 'click', () => {
                // Remove previous selection
                documentList.querySelectorAll('.document-item').forEach(i => i.classList.remove('selected'));
                // Add selection to current item
                item.classList.add('selected');
            });
        });
    }

    getInvitedUsers(modal) {
        // Get list of invited users from modal
        const invitedUsers = modal.querySelectorAll('.invited-user');
        return Array.from(invitedUsers).map(user => ({
            id: user.dataset.id,
            name: user.dataset.name,
            email: user.dataset.email
        }));
    }

    getSelectedUsers(modal) {
        // Get list of selected users from modal
        const selectedUsers = modal.querySelectorAll('.user-item.selected');
        return Array.from(selectedUsers).map(user => ({
            id: user.dataset.id,
            name: user.dataset.name,
            email: user.dataset.email
        }));
    }

    async searchUsers(query, modal) {
        // Search users based on query
        try {
            const response = await fetch(`/api/users/search?q=${encodeURIComponent(query)}`);
            if (response.ok) {
                const data = await response.json();
                this.updateUserResults(modal, data.users || []);
            }
        } catch (error) {
            console.error('Error searching users:', error);
        }
    }

    updateUserResults(modal, users) {
        const userResults = modal.querySelector('#user-results');
        if (!userResults) return;

        userResults.innerHTML = users.map(user => `
            <div class="user-item" data-id="${user.id}" data-name="${user.name}" data-email="${user.email}">
                <div class="user-avatar">
                    <img src="${user.avatar || '/static/img/default-avatar.png'}" alt="${user.name}">
                </div>
                <div class="user-info">
                    <span class="user-name">${user.name}</span>
                    <span class="user-email">${user.email}</span>
                </div>
                <button class="btn btn-sm btn-primary add-user">Add</button>
            </div>
        `).join('');

        // Add click handlers
        userResults.querySelectorAll('.add-user').forEach(btn => {
            window.eventManager.add(btn, 'click', (e) => {
                const userItem = e.target.closest('.user-result');
                this.addInvitedUser(modal, userItem);
                userItem.remove();
            });
        });
    }

    addInvitedUser(modal, userItem) {
        const invitedUsers = modal.querySelector('#invited-users');
        const userId = userItem.dataset.id;
        const userName = userItem.dataset.name;
        const userEmail = userItem.dataset.email;

        // Check if user is already invited
        if (invitedUsers.querySelector(`[data-id="${userId}"]`)) {
            return;
        }

        const invitedUser = document.createElement('div');
        invitedUser.className = 'invited-user';
        invitedUser.dataset.id = userId;
        invitedUser.dataset.name = userName;
        invitedUser.dataset.email = userEmail;

        invitedUser.innerHTML = `
            <span class="user-name">${userName}</span>
            <span class="user-email">${userEmail}</span>
            <button class="btn btn-sm btn-danger remove-user">Remove</button>
        `;

        invitedUsers.appendChild(invitedUser);

        // Add remove handler
        invitedUser.querySelector('.remove-user').addEventListener('click', () => {
            invitedUser.remove();
        });
    }

    // Missing method implementations for collaboration functionality
    async joinSession(sessionId) {
        console.log('Joining session:', sessionId);
        this.showNotification(`Joining session: ${sessionId}`, 'info');
        
        try {
            const response = await fetch(`/api/collaboration/sessions/${sessionId}/join`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ userId: this.getCurrentUserId() })
            });
            
            if (response.ok) {
                this.showNotification('Successfully joined session', 'success');
                this.sendMessage('join_session', { sessionId, userId: this.getCurrentUserId() });
                this.loadSessions(); // Refresh sessions
            } else {
                throw new Error('Failed to join session');
            }
        } catch (error) {
            console.error('Error joining session:', error);
            this.showNotification('Failed to join session', 'error');
        }
    }

    async viewSession(sessionId) {
        console.log('Viewing session:', sessionId);
        const session = this.sessions.get(sessionId);
        if (!session) {
            this.showNotification('Session not found', 'error');
            return;
        }
        
        this.showNotification(`Viewing session: ${session.name}`, 'info');
        this.displaySessionDetails(session);
    }

    displaySessionDetails(session) {
        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h3>Session: ${session.name}</h3>
                    <button class="close-modal">&times;</button>
                </div>
                <div class="modal-body">
                    <div class="session-details">
                        <div class="detail-item">
                            <label>Description:</label>
                            <span>${session.description || 'No description'}</span>
                        </div>
                        <div class="detail-item">
                            <label>Type:</label>
                            <span>${session.type}</span>
                        </div>
                        <div class="detail-item">
                            <label>Privacy:</label>
                            <span>${session.privacy}</span>
                        </div>
                        <div class="detail-item">
                            <label>Status:</label>
                            <span class="status ${session.status}">${session.status}</span>
                        </div>
                        <div class="detail-item">
                            <label>Participants:</label>
                            <span>${session.participant_count || 0}</span>
                        </div>
                        <div class="detail-item">
                            <label>Created:</label>
                            <span>${new Date(session.createdAt).toLocaleString()}</span>
                        </div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button id="join-session-btn" class="btn btn-primary">Join Session</button>
                    <button class="btn btn-secondary close-modal">Close</button>
                </div>
            </div>
        `;

        document.body.appendChild(modal);
        
        // Add event handlers
        modal.querySelector('#join-session-btn').addEventListener('click', () => {
            this.joinSession(session.id);
            modal.remove();
        });
        
        modal.querySelectorAll('.close-modal').forEach(btn => {
            btn.addEventListener('click', () => modal.remove());
        });
    }

    async openDocument(documentId) {
        console.log('Opening document:', documentId);
        const document = this.sharedDocuments.get(documentId);
        if (!document) {
            this.showNotification('Document not found', 'error');
            return;
        }
        
        this.showNotification(`Opening document: ${document.name}`, 'info');
        
        try {
            // Simulate opening document in collaboration mode
            const response = await fetch(`/api/collaboration/documents/${documentId}/open`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ userId: this.getCurrentUserId() })
            });
            
            if (response.ok) {
                this.showNotification('Document opened successfully', 'success');
                // In a real implementation, this would open the document editor
                window.open(`/documents/${documentId}/edit`, '_blank');
            } else {
                throw new Error('Failed to open document');
            }
        } catch (error) {
            console.error('Error opening document:', error);
            this.showNotification('Failed to open document', 'error');
        }
    }

    async downloadDocument(documentId) {
        console.log('Downloading document:', documentId);
        const document = this.sharedDocuments.get(documentId);
        if (!document) {
            this.showNotification('Document not found', 'error');
            return;
        }
        
        this.showNotification(`Downloading: ${document.name}`, 'info');
        
        try {
            const response = await fetch(`/api/collaboration/documents/${documentId}/download`);
            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = document.name;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);
                this.showNotification('Download started', 'success');
            } else {
                throw new Error('Failed to download document');
            }
        } catch (error) {
            console.error('Error downloading document:', error);
            this.showNotification('Download failed', 'error');
        }
    }

    async messageUser(userId) {
        console.log('Messaging user:', userId);
        this.showNotification(`Opening chat with user: ${userId}`, 'info');
        
        // Create a direct message interface
        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h3>Direct Message</h3>
                    <button class="close-modal">&times;</button>
                </div>
                <div class="modal-body">
                    <div class="direct-chat">
                        <div class="chat-messages" id="direct-chat-messages">
                            <div class="chat-placeholder">
                                <i class="fas fa-comment"></i>
                                <p>Start a direct conversation</p>
                            </div>
                        </div>
                        <div class="chat-input-area">
                            <input type="text" id="direct-chat-input" placeholder="Type your message...">
                            <button id="send-direct-message" class="btn btn-primary">Send</button>
                        </div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-secondary close-modal">Close</button>
                </div>
            </div>
        `;

        document.body.appendChild(modal);
        
        // Add event handlers
        modal.querySelector('#send-direct-message').addEventListener('click', () => {
            const input = modal.querySelector('#direct-chat-input');
            const message = input.value.trim();
            if (message) {
                this.sendDirectMessage(userId, message);
                input.value = '';
            }
        });
        
        modal.querySelectorAll('.close-modal').forEach(btn => {
            btn.addEventListener('click', () => modal.remove());
        });
    }

    async sendDirectMessage(userId, message) {
        console.log('Sending direct message to:', userId, message);
        this.showNotification('Message sent', 'success');
        
        try {
            const response = await fetch('/api/collaboration/direct_message', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    recipientId: userId,
                    message: message,
                    senderId: this.getCurrentUserId()
                })
            });
            
            if (response.ok) {
                this.sendMessage('direct_message', { recipientId: userId, message });
            } else {
                throw new Error('Failed to send message');
            }
        } catch (error) {
            console.error('Error sending direct message:', error);
            this.showNotification('Failed to send message', 'error');
        }
    }

    async viewUserProfile(userId) {
        console.log('Viewing user profile:', userId);
        this.showNotification(`Loading profile for user: ${userId}`, 'info');
        
        try {
            const response = await fetch(`/api/users/${userId}/profile`);
            if (response.ok) {
                const userProfile = await response.json();
                this.displayUserProfile(userProfile);
            } else {
                throw new Error('Failed to load user profile');
            }
        } catch (error) {
            console.error('Error loading user profile:', error);
            this.showNotification('Failed to load user profile', 'error');
        }
    }

    displayUserProfile(userProfile) {
        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h3>User Profile</h3>
                    <button class="close-modal">&times;</button>
                </div>
                <div class="modal-body">
                    <div class="user-profile">
                        <div class="profile-avatar">
                            <img src="${userProfile.avatar || '/static/img/default-avatar.png'}" alt="${userProfile.name}">
                        </div>
                        <div class="profile-info">
                            <h4>${userProfile.name}</h4>
                            <p>${userProfile.email}</p>
                            <div class="profile-details">
                                <div class="detail-item">
                                    <label>Role:</label>
                                    <span>${userProfile.role}</span>
                                </div>
                                <div class="detail-item">
                                    <label>Department:</label>
                                    <span>${userProfile.department || 'Not specified'}</span>
                                </div>
                                <div class="detail-item">
                                    <label>Status:</label>
                                    <span class="status ${userProfile.status}">${userProfile.status}</span>
                                </div>
                                <div class="detail-item">
                                    <label>Last seen:</label>
                                    <span>${userProfile.lastSeen ? new Date(userProfile.lastSeen).toLocaleString() : 'Never'}</span>
                                </div>
                                <div class="detail-item">
                                    <label>Bio:</label>
                                    <span>${userProfile.bio || 'No bio available'}</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button id="message-user-btn" class="btn btn-primary">Send Message</button>
                    <button class="btn btn-secondary close-modal">Close</button>
                </div>
            </div>
        `;

        document.body.appendChild(modal);
        
        // Add event handlers
        modal.querySelector('#message-user-btn').addEventListener('click', () => {
            modal.remove();
            this.messageUser(userProfile.id);
        });
        
        modal.querySelectorAll('.close-modal').forEach(btn => {
            btn.addEventListener('click', () => modal.remove());
        });
    }

    updateDocumentContent(documentId, changes) {
        console.log('Updating document content:', documentId, changes);
        this.showNotification(`Document ${documentId} updated`, 'info');
        
        // In a real implementation, this would update the document editor
        // For now, just log the changes and notify users
        this.sendMessage('document_updated', { documentId, changes });
    }

    updateSessionInfo(sessionId, updates) {
        console.log('Updating session info:', sessionId, updates);
        const session = this.sessions.get(sessionId);
        if (session) {
            Object.assign(session, updates);
            this.sessions.set(sessionId, session);
            this.updateSessionsGrid();
            this.showNotification('Session updated', 'info');
        }
    }

    updateUserPermissions(userId, permissions) {
        console.log('Updating user permissions:', userId, permissions);
        this.permissions.set(userId, permissions);
        this.showNotification(`Permissions updated for user: ${userId}`, 'info');
        
        // Update UI to reflect permission changes
        this.loadUsers();
    }

    // Additional utility methods for enhanced functionality
    createChatRoom() {
        console.log('Creating new chat room');
        const roomName = prompt('Enter chat room name:');
        if (!roomName) return;
        
        this.showNotification(`Creating chat room: ${roomName}`, 'info');
        
        // Add room to selector
        const roomSelector = document.getElementById('chat-room-selector');
        if (roomSelector) {
            const option = document.createElement('option');
            option.value = roomName.toLowerCase().replace(/\s+/g, '-');
            option.textContent = roomName;
            roomSelector.appendChild(option);
            roomSelector.value = option.value;
        }
        
        this.showNotification('Chat room created successfully', 'success');
    }

    showFileAttachment() {
        console.log('Showing file attachment dialog');
        this.showNotification('File attachment feature activated', 'info');
        
        // Create file input
        const fileInput = document.createElement('input');
        fileInput.type = 'file';
        fileInput.multiple = true;
        fileInput.accept = '.pdf,.doc,.docx,.txt,.jpg,.png,.gif';
        
        fileInput.addEventListener('change', (e) => {
            const files = Array.from(e.target.files);
            files.forEach(file => {
                this.attachFileToChat(file);
            });
        });
        
        fileInput.click();
    }

    attachFileToChat(file) {
        console.log('Attaching file to chat:', file.name);
        this.showNotification(`Attached: ${file.name}`, 'success');
        
        // Add file attachment to chat
        const chatMessages = document.getElementById('chat-messages');
        if (chatMessages) {
            const attachment = document.createElement('div');
            attachment.className = 'chat-message chat-attachment';
            attachment.innerHTML = `
                <div class="message-content">
                    <div class="attachment-info">
                        <i class="fas fa-paperclip"></i>
                        <span class="file-name">${file.name}</span>
                        <span class="file-size">${this.formatFileSize(file.size)}</span>
                    </div>
                    <div class="attachment-actions">
                        <button class="btn btn-sm btn-secondary">Download</button>
                    </div>
                </div>
            `;
            chatMessages.appendChild(attachment);
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
    }

    showEmojiPicker() {
        console.log('Showing emoji picker');
        this.showNotification('Emoji picker activated', 'info');
        
        // Simple emoji picker implementation
        const emojis = ['😀', '😂', '😍', '🤔', '👍', '👎', '❤️', '🔥', '💯', '🎉'];
        const emojiContainer = document.createElement('div');
        emojiContainer.className = 'emoji-picker';
        emojiContainer.style.cssText = `
            position: absolute;
            background: white;
            border: 1px solid #ccc;
            border-radius: 4px;
            padding: 10px;
            display: grid;
            grid-template-columns: repeat(5, 1fr);
            gap: 5px;
            z-index: 1000;
        `;
        
        emojis.forEach(emoji => {
            const emojiBtn = document.createElement('button');
            emojiBtn.textContent = emoji;
            emojiBtn.style.cssText = 'border: none; background: none; font-size: 20px; cursor: pointer;';
            emojiBtn.addEventListener('click', () => {
                this.insertEmoji(emoji);
                emojiContainer.remove();
            });
            emojiContainer.appendChild(emojiBtn);
        });
        
        // Position near emoji button
        const emojiButton = document.getElementById('emoji-picker');
        if (emojiButton) {
            const rect = emojiButton.getBoundingClientRect();
            emojiContainer.style.top = `${rect.top - 60}px`;
            emojiContainer.style.left = `${rect.left}px`;
        }
        
        document.body.appendChild(emojiContainer);
        
        // Close when clicking outside
        setTimeout(() => {
            document.addEventListener('click', function closeEmojiPicker(e) {
                if (!emojiContainer.contains(e.target)) {
                    emojiContainer.remove();
                    document.removeEventListener('click', closeEmojiPicker);
                }
            });
        }, 100);
    }

    insertEmoji(emoji) {
        const chatInput = document.getElementById('chat-input');
        if (chatInput) {
            chatInput.value += emoji;
            chatInput.focus();
        }
    }

    filterSessions() {
        const filter = document.getElementById('session-filter').value;
        console.log('Filtering sessions by:', filter);
        this.showNotification(`Filtering sessions: ${filter}`, 'info');
        
        // Apply filter to session grid
        const sessionCards = document.querySelectorAll('.session-card');
        sessionCards.forEach(card => {
            const status = card.querySelector('.session-status').textContent.toLowerCase();
            const shouldShow = filter === 'all' || status === filter;
            card.style.display = shouldShow ? 'block' : 'none';
        });
    }

    filterUsers() {
        const filter = document.getElementById('user-filter').value;
        console.log('Filtering users by:', filter);
        this.showNotification(`Filtering users: ${filter}`, 'info');
        
        // Apply filter to user grid
        const userCards = document.querySelectorAll('.user-card');
        userCards.forEach(card => {
            const status = card.querySelector('.user-status').className.includes('online') ? 'online' : 'offline';
            const shouldShow = filter === 'all' || status === filter;
            card.style.display = shouldShow ? 'block' : 'none';
        });
    }

    searchSessions() {
        const searchTerm = document.getElementById('session-search').value.toLowerCase();
        console.log('Searching sessions for:', searchTerm);
        
        const sessionCards = document.querySelectorAll('.session-card');
        sessionCards.forEach(card => {
            const sessionName = card.querySelector('h5').textContent.toLowerCase();
            const sessionDescription = card.querySelector('p').textContent.toLowerCase();
            const matches = sessionName.includes(searchTerm) || sessionDescription.includes(searchTerm);
            card.style.display = matches ? 'block' : 'none';
        });
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
}

// Initialize the advanced collaboration system
window.advancedCollaboration = new AdvancedCollaboration();
