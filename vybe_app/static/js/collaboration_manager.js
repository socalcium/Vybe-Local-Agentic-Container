/**
 * Collaboration Manager for Vybe
 * Handles multi-user collaboration and session management with WebSocket support
 */

// Import the centralized notification manager (attaches to window.notificationManager)
import './services/NotificationManager.js';

class CollaborationManager {
    constructor() {
        this.currentSession = null;
        this.sessions = [];
        this.messages = [];
        this.participants = [];
        this.isConnected = false;
        this.messagePollingInterval = null;
        this.statusUpdateInterval = null;
        
        // WebSocket support
        this.websocket = null;
        this.wsUrl = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectTimeout = null;
        
        // Cleanup functions for event listeners
        this.cleanupFunctions = [];
        
        console.log('[CollaborationManager] Initializing collaboration manager...');
        this.init();
    }
    
    // Destroy method to prevent memory leaks
    destroy() {
        console.log('[CollaborationManager] Destroying collaboration manager...');
        
        // Disconnect WebSocket
        this.disconnectWebSocket();
        
        // Clear intervals
        this.stopMessagePolling();
        if (this.statusUpdateInterval) {
            clearInterval(this.statusUpdateInterval);
            this.statusUpdateInterval = null;
        }
        
        // Remove all event listeners
        this.cleanupFunctions.forEach(cleanup => {
            try {
                cleanup();
            } catch (error) {
                console.error('Error during cleanup:', error);
            }
        });
        this.cleanupFunctions = [];
        
        console.log('[CollaborationManager] Destroyed successfully');
    }

    
    init() {
        console.log('[CollaborationManager] Initializing...');
        this.bindEvents();
        this.loadSessions();
        this.startStatusUpdates();
        this.setupWebSocket();
        console.log('[CollaborationManager] Initialization complete');
    }
    
    bindEvents() {
        console.log('[CollaborationManager] Binding events...');
        
        // Wait for DOM to be ready
        if (document.readyState === 'loading') {
            const domContentLoadedHandler = () => {
                this.setupEventListeners();
                document.removeEventListener('DOMContentLoaded', domContentLoadedHandler);
            };
            document.addEventListener('DOMContentLoaded', domContentLoadedHandler);
        } else {
            this.setupEventListeners();
        }
        
        console.log('[CollaborationManager] Event binding complete');
    }
    
    setupEventListeners() {
        console.log('[CollaborationManager] Setting up event listeners...');
        
        const createSessionBtn = document.getElementById('create-session-btn');
        const joinSessionBtn = document.getElementById('join-session-btn');
        const leaveSessionBtn = document.getElementById('leave-session-btn');
        const searchSessionsBtn = document.getElementById('search-sessions-btn');
        
        if (createSessionBtn) {
            const createHandler = () => {
                console.log('[CollaborationManager] Create session button clicked');
                this.showCreateSessionModal();
            };
            createSessionBtn.addEventListener('click', createHandler);
            this.cleanupFunctions.push(() => createSessionBtn.removeEventListener('click', createHandler));
            window.notificationManager?.showInfo('Create session button ready');
        } else {
            console.warn('[CollaborationManager] Create session button not found');
        }
        
        if (joinSessionBtn) {
            const joinHandler = () => {
                console.log('[CollaborationManager] Join session button clicked');
                this.showJoinSessionModal();
            };
            joinSessionBtn.addEventListener('click', joinHandler);
            this.cleanupFunctions.push(() => joinSessionBtn.removeEventListener('click', joinHandler));
            window.notificationManager?.showInfo('Join session button ready');
        } else {
            console.warn('[CollaborationManager] Join session button not found');
        }
        
        if (leaveSessionBtn) {
            const leaveHandler = () => {
                console.log('[CollaborationManager] Leave session button clicked');
                this.leaveCurrentSession();
            };
            leaveSessionBtn.addEventListener('click', leaveHandler);
            this.cleanupFunctions.push(() => leaveSessionBtn.removeEventListener('click', leaveHandler));
            window.notificationManager?.showInfo('Leave session button ready');
        } else {
            console.warn('[CollaborationManager] Leave session button not found');
        }
        
        if (searchSessionsBtn) {
            const searchHandler = () => {
                console.log('[CollaborationManager] Search sessions button clicked');
                this.searchSessions();
            };
            searchSessionsBtn.addEventListener('click', searchHandler);
            this.cleanupFunctions.push(() => searchSessionsBtn.removeEventListener('click', searchHandler));
            window.notificationManager.showInfo('Search sessions button ready');
        } else {
            console.warn('[CollaborationManager] Search sessions button not found');
        }
        
        // Message sending
        const messageForm = document.getElementById('message-form');
        if (messageForm) {
            const formHandler = (e) => {
                e.preventDefault();
                console.log('[CollaborationManager] Message form submitted');
                this.sendMessage();
            };
            messageForm.addEventListener('submit', formHandler);
            this.cleanupFunctions.push(() => messageForm.removeEventListener('submit', formHandler));
            window.notificationManager.showInfo('Message form ready');
        } else {
            console.warn('[CollaborationManager] Message form not found');
        }
        
        // Session search
        const searchInput = document.getElementById('session-search');
        if (searchInput) {
            const searchInputHandler = this.debounce(() => {
                console.log('[CollaborationManager] Search input changed');
                this.searchSessions();
            }, 300);
            searchInput.addEventListener('input', searchInputHandler);
            this.cleanupFunctions.push(() => searchInput.removeEventListener('input', searchInputHandler));
            window.notificationManager.showInfo('Session search ready');
        } else {
            console.warn('[CollaborationManager] Session search input not found');
        }
        
        console.log('[CollaborationManager] Event listeners setup complete');
    }
    
    // WebSocket Management
    setupWebSocket() {
        console.log('[CollaborationManager] Setting up WebSocket connection...');
        
        // Determine WebSocket URL
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.host;
        this.wsUrl = `${protocol}//${host}/ws/collaboration`;
        
        console.log(`[CollaborationManager] WebSocket URL: ${this.wsUrl}`);
        window.notificationManager.showInfo('WebSocket configuration ready');
    }
    
    connectWebSocket() {
        if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
            console.log('[CollaborationManager] WebSocket already connected');
            return;
        }
        
        console.log('[CollaborationManager] Connecting to WebSocket...');
        window.notificationManager.showInfo('Connecting to real-time collaboration...');
        
        try {
            this.websocket = new WebSocket(this.wsUrl);
            
            this.websocket.onopen = () => {
                console.log('[CollaborationManager] WebSocket connected successfully');
                this.isConnected = true;
                this.reconnectAttempts = 0;
                window.notificationManager?.showSuccess('Real-time collaboration connected');
                
                // Join current session if exists
                if (this.currentSession) {
                    setTimeout(() => {
                        this.sendWebSocketMessage({
                            type: 'join_session',
                            session_id: this.currentSession,
                            username: this.getCurrentUsername()
                        });
                    }, 100); // Small delay to ensure connection is fully established
                }
            };
            
            this.websocket.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    console.log('[CollaborationManager] WebSocket message received:', data);
                    this.handleWebSocketMessage(data);
                } catch (error) {
                    console.error('[CollaborationManager] Error parsing WebSocket message:', error);
                }
            };
            
            this.websocket.onclose = (event) => {
                console.log('[CollaborationManager] WebSocket connection closed:', event.code, event.reason);
                this.isConnected = false;
                this.websocket = null;
                
                if (event.code !== 1000) { // Not a normal closure
                    window.notificationManager?.showWarning('Real-time collaboration disconnected');
                    this.scheduleReconnect();
                }
            };
            
            this.websocket.onerror = (error) => {
                console.error('[CollaborationManager] WebSocket error:', error);
                window.notificationManager?.showError('Real-time collaboration error');
            };
            
        } catch (error) {
            console.error('[CollaborationManager] Error creating WebSocket:', error);
            window.notificationManager?.showError('Failed to connect to real-time collaboration');
        }
    }
    
    disconnectWebSocket() {
        if (this.websocket) {
            console.log('[CollaborationManager] Disconnecting WebSocket...');
            this.websocket.close(1000, 'Client disconnect');
            this.websocket = null;
            this.isConnected = false;
        }
        
        if (this.reconnectTimeout) {
            clearTimeout(this.reconnectTimeout);
            this.reconnectTimeout = null;
        }
    }
    
    scheduleReconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.log('[CollaborationManager] Max reconnection attempts reached');
            window.notificationManager.showError('Unable to reconnect to real-time collaboration');
            return;
        }
        
        const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000); // Exponential backoff, max 30s
        this.reconnectAttempts++;
        
        console.log(`[CollaborationManager] Scheduling reconnect attempt ${this.reconnectAttempts} in ${delay}ms`);
        
        this.reconnectTimeout = setTimeout(() => {
            console.log('[CollaborationManager] Attempting to reconnect...');
            this.connectWebSocket();
        }, delay);
    }
    
    sendWebSocketMessage(message) {
        if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
            console.log('[CollaborationManager] Sending WebSocket message:', message);
            this.websocket.send(JSON.stringify(message));
            return true;
        } else {
            console.warn('[CollaborationManager] WebSocket not connected, cannot send message');
            return false;
        }
    }
    
    handleWebSocketMessage(data) {
        console.log('[CollaborationManager] Processing WebSocket message:', data.type);
        
        switch (data.type) {
            case 'new_message':
                this.handleNewMessage(data.message);
                break;
            case 'message_sent':
                this.handleMessageSent(data.message);
                break;
            case 'message_updated':
                this.handleMessageUpdated(data.message);
                break;
            case 'message_deleted':
                this.handleMessageDeleted(data.message_id);
                break;
            case 'user_joined':
                this.handleUserJoined(data.user);
                break;
            case 'user_left':
                this.handleUserLeft(data.user);
                break;
            case 'session_updated':
                this.handleSessionUpdated(data.session);
                break;
            case 'participants_updated':
                this.handleParticipantsUpdated(data.participants);
                break;
            case 'error':
                this.handleWebSocketError(data.error);
                break;
            default:
                console.log('[CollaborationManager] Unknown WebSocket message type:', data.type);
        }
    }
    
    handleNewMessage(message) {
        console.log('[CollaborationManager] New message received via WebSocket:', message);
        
        // Check if message already exists to prevent duplicates
        const existingMessage = this.messages.find(m => m.id === message.id);
        if (!existingMessage) {
            this.messages.push(message);
            this.renderMessages();
            
            // Show notification only if not from current user
            if (message.username !== this.getCurrentUsername()) {
                window.notificationManager?.showInfo(`New message from ${message.username}`);
            }
        }
    }
    
    handleUserJoined(user) {
        console.log('[CollaborationManager] User joined:', user);
        if (!this.participants.find(p => p.id === user.id)) {
            this.participants.push(user);
            this.renderParticipants();
        }
        window.notificationManager?.showSuccess(`${user.username} joined the session`);
    }
    
    handleUserLeft(user) {
        console.log('[CollaborationManager] User left:', user);
        this.participants = this.participants.filter(p => p.id !== user.id);
        this.renderParticipants();
        window.notificationManager.showInfo(`${user.username} left the session`);
    }
    
    handleSessionUpdated(session) {
        console.log('[CollaborationManager] Session updated:', session);
        const sessionIndex = this.sessions.findIndex(s => s.id === session.id);
        if (sessionIndex !== -1) {
            this.sessions[sessionIndex] = session;
            this.renderSessions();
        }
        window.notificationManager.showInfo('Session updated');
    }
    
    handleParticipantsUpdated(participants) {
        console.log('[CollaborationManager] Participants updated:', participants);
        this.participants = participants;
        this.renderParticipants();
    }
    
    handleMessageSent(message) {
        console.log('[CollaborationManager] Message sent confirmation received:', message);
        window.notificationManager?.showSuccess('Message sent');
    }
    
    handleMessageUpdated(message) {
        console.log('[CollaborationManager] Message updated via WebSocket:', message);
        const messageIndex = this.messages.findIndex(m => m.id === message.id);
        if (messageIndex !== -1) {
            this.messages[messageIndex] = message;
            this.renderMessages();
        }
    }
    
    handleMessageDeleted(messageId) {
        console.log('[CollaborationManager] Message deleted via WebSocket:', messageId);
        this.messages = this.messages.filter(m => m.id !== messageId);
        this.renderMessages();
    }
    
    handleWebSocketError(error) {
        console.error('[CollaborationManager] WebSocket error received:', error);
        window.notificationManager?.showError(`Real-time error: ${error}`);
    }
    
    async loadSessions() {
        console.log('[CollaborationManager] Loading sessions...');
        
        // Show loading state
        const sessionsContainer = document.getElementById('sessions-list');
        if (sessionsContainer) {
            sessionsContainer.innerHTML = `
                <div class="loading-state">
                    <i class="fas fa-spinner fa-spin"></i>
                    <p>Loading collaboration sessions...</p>
                </div>
            `;
        }
        
        window.notificationManager?.showInfo('Loading collaboration sessions...');
        
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
                this.sessions = data.sessions || [];
                console.log(`[CollaborationManager] Loaded ${this.sessions.length} sessions`);
                this.renderSessions();
                window.notificationManager?.showSuccess(`Loaded ${this.sessions.length} sessions`);
            } else {
                console.error('Failed to load sessions:', data.error);
                window.notificationManager?.showError(`Failed to load sessions: ${data.error || 'Unknown error'}`);
                this.sessions = [];
                this.renderSessions();
            }
        } catch (error) {
            console.error('Error loading sessions:', error);
            window.notificationManager?.showError('Failed to load sessions. Please check your connection and try again.');
            // Initialize empty sessions array on error
            this.sessions = [];
            this.renderSessions();
        }
    }
    
    renderSessions() {
        console.log('[CollaborationManager] Rendering sessions list...');
        const sessionsContainer = document.getElementById('sessions-list');
        if (!sessionsContainer) {
            console.warn('[CollaborationManager] Sessions container not found');
            return;
        }
        
        sessionsContainer.innerHTML = '';
        
        if (this.sessions.length === 0) {
            sessionsContainer.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-users"></i>
                    <h3>No collaboration sessions</h3>
                    <p>Create a new session to start collaborating with others</p>
                    <button class="btn btn-primary" onclick="collaborationManager.showCreateSessionModal()">
                        Create Session
                    </button>
                </div>
            `;
            return;
        }
        
        this.sessions.forEach(session => {
            const sessionElement = this.createSessionElement(session);
            sessionsContainer.appendChild(sessionElement);
        });
    }
    
    createSessionElement(session) {
        const div = document.createElement('div');
        div.className = 'session-card';
        div.innerHTML = `
            <div class="session-header">
                <h4>${session.name}</h4>
                <span class="session-type ${session.type}">${session.type}</span>
            </div>
            <p class="session-description">${session.description || 'No description'}</p>
            <div class="session-meta">
                <span class="participants">
                    <i class="fas fa-users"></i>
                    ${session.participants.length}/${session.max_participants}
                </span>
                <span class="status ${session.status}">${session.status}</span>
                <span class="created">
                    <i class="fas fa-calendar"></i>
                    ${new Date(session.created_at).toLocaleDateString()}
                </span>
            </div>
            <div class="session-actions">
                <button class="btn btn-sm btn-primary" onclick="collaborationManager.joinSession('${session.id}')">
                    Join
                </button>
                <button class="btn btn-sm btn-secondary" onclick="collaborationManager.viewSession('${session.id}')">
                    View
                </button>
            </div>
        `;
        return div;
    }
    
    async createSession(sessionData) {
        console.log('[CollaborationManager] Creating new session...');
        window.notificationManager?.showInfo('Creating collaboration session...');
        
        // Find the create button in the modal
        const createBtn = document.querySelector('.modal .btn-primary:last-child') || document.getElementById('create-session-submit');
        if (createBtn) {
            createBtn.disabled = true;
            createBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Creating...';
        }
        
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
                this.sessions.unshift(data.session); // Add to beginning for better UX
                this.renderSessions();
                this.hideCreateSessionModal();
                window.notificationManager?.showSuccess(`Session "${data.session.name}" created successfully`);
                
                // Optionally auto-join the created session
                if (confirm('Session created successfully! Would you like to join it now?')) {
                    this.joinSession(data.session.id);
                }
                
                return data.session;
            } else {
                console.error('Failed to create session:', data.error);
                window.notificationManager?.showError(`Failed to create session: ${data.error || 'Unknown error'}`);
                return null;
            }
        } catch (error) {
            console.error('Error creating session:', error);
            window.notificationManager?.showError('Failed to create session. Please check your connection and try again.');
            return null;
        } finally {
            // Re-enable create button
            if (createBtn) {
                createBtn.disabled = false;
                createBtn.innerHTML = 'Create Session';
            }
        }
    }
    
    async joinSession(sessionId) {
        console.log(`[CollaborationManager] Joining session: ${sessionId}`);
        window.notificationManager?.showInfo('Joining collaboration session...');
        
        // Disable join buttons to prevent multiple requests
        const joinButtons = document.querySelectorAll(`[onclick*="joinSession('${sessionId}')"]`);
        joinButtons.forEach(btn => {
            btn.disabled = true;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Joining...';
        });
        
        try {
            const response = await fetch(`/api/collaboration/sessions/${sessionId}/join`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    role: 'participant'
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            if (data.success) {
                this.currentSession = sessionId;
                console.log(`[CollaborationManager] Successfully joined session: ${sessionId}`);
                
                // Connect WebSocket for real-time updates
                this.connectWebSocket();
                
                // Load session details and start polling
                await this.loadSessionDetails(sessionId);
                this.startMessagePolling();
                
                // Update UI to show session view
                const sessionsList = document.getElementById('sessions-list');
                const sessionView = document.getElementById('session-view');
                if (sessionsList) sessionsList.style.display = 'none';
                if (sessionView) sessionView.style.display = 'block';
                
                window.notificationManager?.showSuccess(`Successfully joined session`);
                return true;
            } else {
                console.error('Failed to join session:', data.error);
                window.notificationManager?.showError(`Failed to join session: ${data.error || 'Unknown error'}`);
                return false;
            }
        } catch (error) {
            console.error('Error joining session:', error);
            window.notificationManager?.showError('Failed to join session. Please check your connection and try again.');
            return false;
        } finally {
            // Re-enable join buttons
            joinButtons.forEach(btn => {
                btn.disabled = false;
                btn.innerHTML = 'Join';
            });
        }
    }
    
    async leaveCurrentSession() {
        if (!this.currentSession) {
            console.log('[CollaborationManager] No current session to leave');
            window.notificationManager?.showWarning('No active session to leave');
            return;
        }
        
        console.log(`[CollaborationManager] Leaving session: ${this.currentSession}`);
        window.notificationManager?.showInfo('Leaving collaboration session...');
        
        // Disable leave button to prevent multiple requests
        const leaveBtn = document.querySelector('[onclick*="leaveCurrentSession"]');
        if (leaveBtn) {
            leaveBtn.disabled = true;
            leaveBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Leaving...';
        }
        
        try {
            const response = await fetch(`/api/collaboration/sessions/${this.currentSession}/leave`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            if (data.success) {
                console.log('[CollaborationManager] Successfully left session');
                this.handleSessionExit();
                window.notificationManager?.showSuccess('Successfully left session');
            } else {
                console.error('Failed to leave session:', data.error);
                window.notificationManager?.showError(`Failed to leave session: ${data.error || 'Unknown error'}`);
                // Still handle session exit locally to clean up state
                this.handleSessionExit();
            }
        } catch (error) {
            console.error('Error leaving session:', error);
            window.notificationManager?.showError('Failed to leave session. Please check your connection and try again.');
            // Still handle session exit locally to clean up state
            this.handleSessionExit();
        } finally {
            // Re-enable leave button (if it still exists)
            if (leaveBtn && leaveBtn.parentNode) {
                leaveBtn.disabled = false;
                leaveBtn.innerHTML = 'Leave Session';
            }
        }
    }
    
    handleSessionExit() {
        console.log('[CollaborationManager] Handling session exit...');
        
        // Send WebSocket leave message
        if (this.currentSession) {
            this.sendWebSocketMessage({
                type: 'leave_session',
                session_id: this.currentSession
            });
        }
        
        // Clear session state
        const sessionId = this.currentSession;
        this.currentSession = null;
        this.messages = [];
        this.participants = [];
        
        // Stop polling and disconnect WebSocket
        this.stopMessagePolling();
        this.disconnectWebSocket();
        this.clearSessionView();
        
        // Show sessions list again
        const sessionsList = document.getElementById('sessions-list');
        if (sessionsList) {
            sessionsList.style.display = 'block';
        }
        
        // Refresh sessions list to get updated participant counts
        this.loadSessions();
        
        console.log(`[CollaborationManager] Session exit complete for session: ${sessionId}`);
    }
    
    async loadSessionDetails(sessionId) {
        console.log(`[CollaborationManager] Loading session details for: ${sessionId}`);
        
        try {
            const response = await fetch(`/api/collaboration/sessions/${sessionId}`, {
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
                console.log('[CollaborationManager] Session details loaded successfully');
                this.renderSessionView(data.session);
                
                // Load messages and participants concurrently
                await Promise.all([
                    this.loadMessages(sessionId),
                    this.loadParticipants(sessionId)
                ]);
            } else {
                console.error('Failed to load session details:', data.error);
                window.notificationManager?.showError(`Failed to load session details: ${data.error || 'Unknown error'}`);
            }
        } catch (error) {
            console.error('Error loading session details:', error);
            window.notificationManager?.showError('Failed to load session details. Please check your connection and try again.');
        }
    }
    
    renderSessionView(session) {
        const sessionView = document.getElementById('session-view');
        if (!sessionView) return;
        
        sessionView.innerHTML = `
            <div class="session-header">
                <h2>${session.name}</h2>
                <div class="session-controls">
                    <button class="btn btn-sm btn-secondary" onclick="collaborationManager.leaveCurrentSession()">
                        Leave Session
                    </button>
                </div>
            </div>
            <div class="session-info">
                <p>${session.description || 'No description'}</p>
                <div class="session-meta">
                    <span class="type">${session.type}</span>
                    <span class="status ${session.status}">${session.status}</span>
                    <span class="participants">${session.participants.length} participants</span>
                </div>
            </div>
            <div class="session-content">
                <div class="messages-container">
                    <div id="messages-list" class="messages-list"></div>
                    <form id="message-form" class="message-form">
                        <input type="text" id="message-input" placeholder="Type your message..." required>
                        <button type="submit" class="btn btn-primary">Send</button>
                    </form>
                </div>
                <div class="participants-sidebar">
                    <h4>Participants</h4>
                    <div id="participants-list"></div>
                </div>
            </div>
        `;
        
        sessionView.style.display = 'block';
    }
    
    async loadMessages(sessionId) {
        console.log(`[CollaborationManager] Loading messages for session: ${sessionId}`);
        
        try {
            const response = await fetch(`/api/collaboration/sessions/${sessionId}/messages`, {
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
                this.messages = data.messages || [];
                console.log(`[CollaborationManager] Loaded ${this.messages.length} messages`);
                this.renderMessages();
            } else {
                console.error('Failed to load messages:', data.error);
                window.notificationManager?.showWarning(`Failed to load messages: ${data.error || 'Unknown error'}`);
                this.messages = [];
                this.renderMessages();
            }
        } catch (error) {
            console.error('Error loading messages:', error);
            window.notificationManager?.showWarning('Failed to load chat history. New messages will still appear.');
            this.messages = [];
            this.renderMessages();
        }
    }
    
    renderMessages() {
        const messagesList = document.getElementById('messages-list');
        if (!messagesList) return;
        
        messagesList.innerHTML = '';
        
        this.messages.forEach(message => {
            const messageElement = this.createMessageElement(message);
            messagesList.appendChild(messageElement);
        });
        
        // Scroll to bottom
        messagesList.scrollTop = messagesList.scrollHeight;
    }
    
    createMessageElement(message) {
        const div = document.createElement('div');
        div.className = 'message';
        const isCurrentUser = message.username === this.getCurrentUsername();
        const editedText = message.edited ? ' <small class="text-muted">(edited)</small>' : '';
        
        div.innerHTML = `
            <div class="message-header">
                <span class="username ${isCurrentUser ? 'current-user' : ''}">${message.username}</span>
                <span class="timestamp">${new Date(message.timestamp).toLocaleTimeString()}</span>
                ${editedText}
            </div>
            <div class="message-content">${this.escapeHtml(message.content)}</div>
            ${isCurrentUser ? `
                <div class="message-actions">
                    <button class="btn btn-sm btn-link" onclick="collaborationManager.editMessage('${message.id}')">
                        <i class="fas fa-edit"></i> Edit
                    </button>
                    <button class="btn btn-sm btn-link text-danger" onclick="collaborationManager.deleteMessage('${message.id}')">
                        <i class="fas fa-trash"></i> Delete
                    </button>
                </div>
            ` : ''}
        `;
        return div;
    }
    
    async sendMessage() {
        if (!this.currentSession) {
            console.warn('[CollaborationManager] No current session for sending message');
            window.notificationManager?.showWarning('Please join a session first');
            return;
        }
        
        const messageInput = document.getElementById('message-input');
        const sendButton = document.querySelector('#message-form button[type="submit"]');
        const content = messageInput ? messageInput.value.trim() : '';
        
        if (!content) {
            console.warn('[CollaborationManager] Cannot send empty message');
            window.notificationManager?.showWarning('Please enter a message');
            return;
        }
        
        console.log('[CollaborationManager] Sending message:', content);
        
        // Disable send button and input to prevent duplicate sends
        if (sendButton) {
            sendButton.disabled = true;
            sendButton.textContent = 'Sending...';
        }
        if (messageInput) {
            messageInput.disabled = true;
        }
        
        const messageData = {
            content: content,
            type: 'text',
            timestamp: new Date().toISOString()
        };
        
        try {
            // Try WebSocket first for real-time delivery
            if (this.isConnected && this.websocket.readyState === WebSocket.OPEN) {
                const wsMessage = {
                    type: 'send_message',
                    session_id: this.currentSession,
                    message: {
                        ...messageData,
                        username: this.getCurrentUsername()
                    }
                };
                
                if (this.sendWebSocketMessage(wsMessage)) {
                    if (messageInput) messageInput.value = '';
                    console.log('[CollaborationManager] Message sent via WebSocket');
                    return; // Don't show success notification yet, wait for WebSocket confirmation
                }
            }
            
            // Fallback to HTTP API
            const response = await fetch(`/api/collaboration/sessions/${this.currentSession}/messages`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(messageData)
            });
            
            const data = await response.json();
            
            if (data.success) {
                if (messageInput) messageInput.value = '';
                this.messages.push(data.message);
                this.renderMessages();
                window.notificationManager?.showSuccess('Message sent');
            } else {
                console.error('Failed to send message:', data.error);
                window.notificationManager?.showError(`Failed to send message: ${data.error || 'Unknown error'}`);
            }
        } catch (error) {
            console.error('Error sending message:', error);
            window.notificationManager?.showError('Failed to send message. Please check your connection and try again.');
        } finally {
            // Re-enable send button and input
            if (sendButton) {
                sendButton.disabled = false;
                sendButton.textContent = 'Send';
            }
            if (messageInput) {
                messageInput.disabled = false;
                messageInput.focus();
            }
        }
    }
    
    async editMessage(messageId) {
        const message = this.messages.find(m => m.id === messageId);
        if (!message) {
            window.notificationManager?.showError('Message not found');
            return;
        }
        
        const newContent = prompt('Edit message:', message.content);
        if (!newContent || newContent.trim() === message.content) return;
        
        console.log(`[CollaborationManager] Editing message: ${messageId}`);
        
        try {
            const response = await fetch(`/api/collaboration/sessions/${this.currentSession}/messages/${messageId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    content: newContent.trim()
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            if (data.success) {
                const messageIndex = this.messages.findIndex(m => m.id === messageId);
                if (messageIndex !== -1) {
                    this.messages[messageIndex].content = newContent.trim();
                    this.messages[messageIndex].edited = true;
                    this.messages[messageIndex].edited_at = new Date().toISOString();
                    this.renderMessages();
                }
                window.notificationManager?.showSuccess('Message updated successfully');
            } else {
                console.error('Failed to edit message:', data.error);
                window.notificationManager?.showError(`Failed to edit message: ${data.error || 'Unknown error'}`);
            }
        } catch (error) {
            console.error('Error editing message:', error);
            window.notificationManager?.showError('Failed to edit message. Please check your connection and try again.');
        }
    }
    
    async deleteMessage(messageId) {
        const message = this.messages.find(m => m.id === messageId);
        if (!message) {
            window.notificationManager?.showError('Message not found');
            return;
        }
        
        if (!confirm('Are you sure you want to delete this message? This action cannot be undone.')) return;
        
        console.log(`[CollaborationManager] Deleting message: ${messageId}`);
        
        try {
            const response = await fetch(`/api/collaboration/sessions/${this.currentSession}/messages/${messageId}`, {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            if (data.success) {
                this.messages = this.messages.filter(m => m.id !== messageId);
                this.renderMessages();
                window.notificationManager?.showSuccess('Message deleted successfully');
            } else {
                console.error('Failed to delete message:', data.error);
                window.notificationManager?.showError(`Failed to delete message: ${data.error || 'Unknown error'}`);
            }
        } catch (error) {
            console.error('Error deleting message:', error);
            window.notificationManager?.showError('Failed to delete message. Please check your connection and try again.');
        }
    }
    
    async loadParticipants(sessionId) {
        console.log(`[CollaborationManager] Loading participants for session: ${sessionId}`);
        
        try {
            const response = await fetch(`/api/collaboration/sessions/${sessionId}`, {
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
                this.participants = data.session.participants || [];
                console.log(`[CollaborationManager] Loaded ${this.participants.length} participants`);
                this.renderParticipants();
            } else {
                console.error('Failed to load participants:', data.error);
                window.notificationManager?.showWarning(`Failed to load participants: ${data.error || 'Unknown error'}`);
                this.participants = [];
                this.renderParticipants();
            }
        } catch (error) {
            console.error('Error loading participants:', error);
            window.notificationManager?.showWarning('Failed to load participants list.');
            this.participants = [];
            this.renderParticipants();
        }
    }
    
    renderParticipants() {
        const participantsList = document.getElementById('participants-list');
        if (!participantsList) return;
        
        participantsList.innerHTML = '';
        
        this.participants.forEach(participant => {
            const div = document.createElement('div');
            div.className = 'participant';
            div.innerHTML = `
                <div class="participant-info">
                    <span class="username">${participant.username}</span>
                    <span class="role ${participant.role}">${participant.role}</span>
                </div>
                <div class="participant-status">
                    <span class="status ${participant.status}">${participant.status}</span>
                </div>
            `;
            participantsList.appendChild(div);
        });
    }
    
    async searchSessions() {
        const searchInput = document.getElementById('session-search');
        const query = searchInput ? searchInput.value.trim() : '';
        
        console.log(`[CollaborationManager] Searching sessions with query: "${query}"`);
        
        // Show loading state
        const sessionsContainer = document.getElementById('sessions-list');
        if (sessionsContainer) {
            sessionsContainer.innerHTML = `
                <div class="loading-state">
                    <i class="fas fa-spinner fa-spin"></i>
                    <p>Searching sessions...</p>
                </div>
            `;
        }
        
        try {
            const url = query 
                ? `/api/collaboration/search?q=${encodeURIComponent(query)}`
                : '/api/collaboration/sessions'; // If no query, load all sessions
            
            const response = await fetch(url, {
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
                this.sessions = data.sessions || [];
                console.log(`[CollaborationManager] Found ${this.sessions.length} sessions`);
                this.renderSessions();
                
                if (query && this.sessions.length === 0) {
                    window.notificationManager?.showInfo('No sessions found matching your search');
                }
            } else {
                console.error('Failed to search sessions:', data.error);
                window.notificationManager?.showError(`Search failed: ${data.error || 'Unknown error'}`);
                this.sessions = [];
                this.renderSessions();
            }
        } catch (error) {
            console.error('Error searching sessions:', error);
            window.notificationManager?.showError('Failed to search sessions. Please check your connection and try again.');
            this.sessions = [];
            this.renderSessions();
        }
    }
    
    startMessagePolling() {
        if (this.messagePollingInterval) {
            clearInterval(this.messagePollingInterval);
        }
        
        this.messagePollingInterval = setInterval(() => {
            if (this.currentSession) {
                this.loadMessages(this.currentSession);
                this.loadParticipants(this.currentSession);
            }
        }, 5000); // Poll every 5 seconds
    }
    
    stopMessagePolling() {
        if (this.messagePollingInterval) {
            clearInterval(this.messagePollingInterval);
            this.messagePollingInterval = null;
        }
    }
    
    startStatusUpdates() {
        this.statusUpdateInterval = setInterval(() => {
            this.loadSessions();
        }, 30000); // Update every 30 seconds
    }
    
    clearSessionView() {
        const sessionView = document.getElementById('session-view');
        if (sessionView) {
            sessionView.style.display = 'none';
            sessionView.innerHTML = '';
        }
    }
    
    showCreateSessionModal() {
        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h3>Create Collaboration Session</h3>
                    <button class="close-btn" onclick="this.closest('.modal').remove()">&times;</button>
                </div>
                <div class="modal-body">
                    <form id="create-session-form">
                        <div class="form-group">
                            <label for="session-name">Session Name</label>
                            <input type="text" id="session-name" required>
                        </div>
                        <div class="form-group">
                            <label for="session-description">Description</label>
                            <textarea id="session-description"></textarea>
                        </div>
                        <div class="form-group">
                            <label for="session-type">Type</label>
                            <select id="session-type">
                                <option value="general">General</option>
                                <option value="project">Project</option>
                                <option value="meeting">Meeting</option>
                                <option value="brainstorming">Brainstorming</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label for="max-participants">Max Participants</label>
                            <input type="number" id="max-participants" min="2" max="50" value="10">
                        </div>
                        <div class="form-group">
                            <label>
                                <input type="checkbox" id="is-public">
                                Public Session
                            </label>
                        </div>
                    </form>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-secondary" onclick="this.closest('.modal').remove()">Cancel</button>
                    <button class="btn btn-primary" onclick="collaborationManager.submitCreateSession()">Create</button>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
    }
    
    hideCreateSessionModal() {
        const modal = document.querySelector('.modal');
        if (modal) {
            modal.remove();
        }
    }
    
    async submitCreateSession() {
        const sessionData = {
            name: document.getElementById('session-name').value,
            description: document.getElementById('session-description').value,
            type: document.getElementById('session-type').value,
            max_participants: parseInt(document.getElementById('max-participants').value),
            is_public: document.getElementById('is-public').checked
        };
        
        await this.createSession(sessionData);
    }
    
    showJoinSessionModal() {
        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h3>Join Session</h3>
                    <button class="close-btn" onclick="this.closest('.modal').remove()">&times;</button>
                </div>
                <div class="modal-body">
                    <div class="form-group">
                        <label for="session-id">Session ID</label>
                        <input type="text" id="session-id" placeholder="Enter session ID">
                    </div>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-secondary" onclick="this.closest('.modal').remove()">Cancel</button>
                    <button class="btn btn-primary" onclick="collaborationManager.submitJoinSession()">Join</button>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
    }
    
    async submitJoinSession() {
        const sessionId = document.getElementById('session-id').value.trim();
        if (!sessionId) {
            window.notificationManager.showError('Please enter a session ID');
            return;
        }
        
        const modal = document.querySelector('.modal');
        if (modal) {
            modal.remove();
        }
        
        await this.joinSession(sessionId);
    }
    
    async viewSession(sessionId) {
        console.log(`[CollaborationManager] Viewing session: ${sessionId}`);
        window.notificationManager.showInfo('Loading session details...');
        
        try {
            const response = await fetch(`/api/collaboration/sessions/${sessionId}`);
            const data = await response.json();
            
            if (data.success) {
                this.showSessionDetailsModal(data.session);
                window.notificationManager?.showSuccess('Session details loaded');
            } else {
                console.error('Failed to load session details:', data.error);
                window.notificationManager.showError(data.error);
            }
        } catch (error) {
            console.error('Error viewing session:', error);
            window.notificationManager?.showError('Failed to load session details. Please check your connection and try again.');
        }
    }
    
    showSessionDetailsModal(session) {
        console.log('[CollaborationManager] Showing session details modal for:', session.name);
        
        const modal = document.createElement('div');
        modal.className = 'modal session-details-modal';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h3>Session Details: ${session.name}</h3>
                    <button class="close-btn" onclick="this.closest('.modal').remove()">&times;</button>
                </div>
                <div class="modal-body">
                    <div class="session-info">
                        <div class="info-item">
                            <label>Name:</label>
                            <span>${session.name}</span>
                        </div>
                        <div class="info-item">
                            <label>Description:</label>
                            <span>${session.description || 'No description'}</span>
                        </div>
                        <div class="info-item">
                            <label>Type:</label>
                            <span class="session-type ${session.type}">${session.type}</span>
                        </div>
                        <div class="info-item">
                            <label>Status:</label>
                            <span class="session-status ${session.status}">${session.status}</span>
                        </div>
                        <div class="info-item">
                            <label>Participants:</label>
                            <span>${session.participants.length}/${session.max_participants}</span>
                        </div>
                        <div class="info-item">
                            <label>Created:</label>
                            <span>${new Date(session.created_at).toLocaleString()}</span>
                        </div>
                    </div>
                    <div class="participants-preview">
                        <h4>Participants:</h4>
                        <div class="participants-list">
                            ${session.participants.map(p => `
                                <div class="participant-item">
                                    <span class="username">${p.username}</span>
                                    <span class="role ${p.role}">${p.role}</span>
                                    <span class="status ${p.status}">${p.status}</span>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-secondary" onclick="this.closest('.modal').remove()">Close</button>
                    <button class="btn btn-primary" onclick="collaborationManager.joinSession('${session.id}'); this.closest('.modal').remove();">
                        Join Session
                    </button>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        window.notificationManager.showInfo('Session details displayed');
    }

    // Helper method to get current username
    getCurrentUsername() {
        // Try to get from global user context or localStorage
        return window.currentUser?.username || 
               localStorage.getItem('username') || 
               sessionStorage.getItem('username') || 
               'Anonymous';
    }
    
    // Helper method to escape HTML content
    escapeHtml(unsafe) {
        const div = document.createElement('div');
        div.textContent = unsafe;
        return div.innerHTML;
    }
    
    // Utility method for debouncing
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
    
    // Static initialization method
    static initialize() {
        console.log('[CollaborationManager] Static initialization called');
        if (!window.collaborationManager) {
            window.collaborationManager = new CollaborationManager();
            console.log('[CollaborationManager] Global instance created');
        }
        return window.collaborationManager;
    }
}

// Enhanced initialization with multiple fallbacks
(() => {
    console.log('[CollaborationManager] Module loaded, setting up initialization...');
    
    const initializeManager = () => {
        try {
            if (!window.collaborationManager) {
                window.collaborationManager = new CollaborationManager();
                console.log('[CollaborationManager] Successfully initialized global instance');
                window.notificationManager?.showSuccess('Collaboration Manager ready');
            }
        } catch (error) {
            console.error('[CollaborationManager] Initialization error:', error);
            window.notificationManager.showError('Collaboration Manager initialization failed');
        }
    };
    
    // Initialize immediately if DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeManager);
    } else {
        initializeManager();
    }
    
    // Also try with window load as fallback
    if (document.readyState !== 'complete') {
        window.addEventListener('load', () => {
            if (!window.collaborationManager) {
                console.log('[CollaborationManager] Fallback initialization on window load');
                initializeManager();
            }
        });
    }
})();
