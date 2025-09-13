/**
 * Chat Application Main Controller
 * Coordinates all chat functionality using modular components
 */

// Import the centralized notification manager (attaches to window.notificationManager)
import './services/NotificationManager.js';
import DeviceDetector from './utils/device-detector.js';
import { ChatManager } from './modules/chat-manager.js';
import { ModelManager } from './modules/model-manager.js';
import { ChatSettingsPanelManager } from './modules/chat-settings-panel-manager.js';

class ChatController {
    constructor() {
        this.managers = {};
        this.deviceInfo = DeviceDetector;
        this.websocket = null;
        this.chatHistory = [];
        
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
        // Check if we're on the chat page
        const chatInput = document.getElementById('chat-input');
        if (!chatInput) {
            console.log('Not on chat page, skipping chat controller initialization');
            return;
        }

        // Setup device-specific optimizations
        this.setupDeviceOptimizations();

        // Initialize all managers
        this.managers.chat = new ChatManager();
        this.managers.model = new ModelManager();
        this.managers.settingsPanel = new ChatSettingsPanelManager();

        // Setup cross-manager communication
        this.setupManagerCommunication();
        
        // Setup WebSocket connection
        this.setupWebSocket();
        
        // Load chat history from backend
        this.loadChatHistory();
        
        // Setup voice I/O button handlers
        this.setupVoiceButtons();
        
        // Load sample prompts
        this.loadSamplePrompts();
        
        console.log('Chat application initialized with modular components');
        console.log('Device Info:', this.deviceInfo.getInfo());
    }

    setupVoiceButtons() {
        // Voice functionality is handled by voice.js
        // The VoiceManager will be available as window.voiceManager
        
        // We don't need to set up handlers here since voice.js handles them
        // But we can add integration with chat functionality
        
        // Set up integration with AI responses for voice output
        this.setupVoiceIntegration();
    }
    
    setupVoiceIntegration() {
        console.log('Setting up voice integration for chat...');
        
        // Wait for voice manager to be available with timeout
        let attempts = 0;
        const maxAttempts = 50; // 5 seconds max wait
        
        const checkVoiceManager = () => {
            attempts++;
            
            if (window.voiceManager) {
                console.log('✓ Voice manager available, setting up chat integration');
                
                // Prevent multiple setups
                if (window.voiceManager._chatIntegrationSetup) {
                    console.log('Voice integration already set up');
                    return;
                }
                window.voiceManager._chatIntegrationSetup = true;
                
                // Enhanced transcription integration
                this.setupTranscriptionIntegration();
                
                // Enhanced voice output integration
                this.setupVoiceOutputIntegration();
                
                // Setup voice commands
                this.setupVoiceCommands();
                
                this.showNotification('Voice integration enabled', 'success');
                
            } else if (attempts < maxAttempts) {
                // Try again in 100ms
                setTimeout(checkVoiceManager, 100);
            } else {
                console.warn('⚠️ Voice manager not available after 5 seconds, skipping voice integration');
                this.showNotification('Voice features unavailable', 'warning');
            }
        };
        
        checkVoiceManager();
    }
    
    setupWebSocket() {
        try {
            // Determine WebSocket URL
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const host = window.location.host;
            const wsUrl = `${protocol}//${host}/ws/chat`;
            
            console.log('Connecting to WebSocket:', wsUrl);
            this.websocket = new WebSocket(wsUrl);
            
            this.websocket.onopen = () => {
                console.log('WebSocket connected successfully');
                window.notificationManager?.success('Chat connected');
                this.updateConnectionStatus(true);
            };
            
            this.websocket.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.handleWebSocketMessage(data);
                } catch (error) {
                    console.error('Error parsing WebSocket message:', error);
                }
            };
            
            this.websocket.onclose = (event) => {
                console.log('WebSocket connection closed:', event.code, event.reason);
                this.updateConnectionStatus(false);
                
                if (event.code !== 1000) {
                    // Abnormal closure, attempt to reconnect
                    window.notificationManager?.warning('Connection lost. Attempting to reconnect...');
                    setTimeout(() => this.reconnectWebSocket(), 3000);
                }
            };
            
            this.websocket.onerror = (error) => {
                console.error('WebSocket error:', error);
                window.notificationManager?.error('Connection error. Please refresh the page if issues persist.');
            };
            
        } catch (error) {
            console.error('Failed to setup WebSocket:', error);
            window.notificationManager?.error('Failed to establish chat connection');
        }
    }
    
    reconnectWebSocket() {
        if (!this.websocket || this.websocket.readyState === WebSocket.CLOSED) {
            console.log('Attempting to reconnect WebSocket...');
            this.setupWebSocket();
        }
    }
    
    updateConnectionStatus(isConnected) {
        const statusIndicator = document.getElementById('connection-status');
        if (statusIndicator) {
            statusIndicator.className = isConnected ? 'connected' : 'disconnected';
            statusIndicator.title = isConnected ? 'Connected' : 'Disconnected';
        }
        
        // Update send button state
        if (this.managers.chat && this.managers.chat.ui.sendButton) {
            this.managers.chat.ui.sendButton.disabled = !isConnected;
        }
    }
    
    handleWebSocketMessage(data) {
        switch (data.type) {
            case 'message_chunk':
                this.handleStreamingChunk(data);
                break;
            case 'message_complete':
                this.handleMessageComplete(data);
                break;
            case 'error':
                this.handleError(data);
                break;
            case 'typing_indicator':
                this.handleTypingIndicator(data);
                break;
            default:
                console.log('Unknown WebSocket message type:', data.type);
        }
    }
    
    handleStreamingChunk(data) {
        if (this.managers.chat) {
            // Find or create the streaming message element
            let streamingMessage = document.getElementById(`streaming-message-${data.message_id}`);
            
            if (!streamingMessage) {
                // Create new streaming message
                streamingMessage = this.managers.chat.createMessage({
                    id: data.message_id,
                    type: 'assistant',
                    content: '',
                    streaming: true
                });
            }
            
            // Append the chunk to existing content
            const contentElement = streamingMessage.querySelector('.message-content');
            if (contentElement) {
                contentElement.textContent += data.content;
                
                // Auto-scroll to bottom if user is near bottom
                this.autoScrollIfNeeded();
            }
        }
    }
    
    handleMessageComplete(data) {
        if (this.managers.chat) {
            const streamingMessage = document.getElementById(`streaming-message-${data.message_id}`);
            
            if (streamingMessage) {
                // Mark as complete and render final content
                streamingMessage.classList.remove('streaming');
                streamingMessage.classList.add('complete');
                
                const contentElement = streamingMessage.querySelector('.message-content');
                if (contentElement && data.final_content) {
                    // Replace with final formatted content
                    contentElement.innerHTML = this.formatMessageContent(data.final_content);
                }
                
                // Add to chat history
                this.chatHistory.push({
                    id: data.message_id,
                    type: 'assistant',
                    content: data.final_content,
                    timestamp: new Date().toISOString()
                });
                
                // Trigger voice output if enabled
                if (window.voiceManager && window.voiceManager.isVoiceOutputEnabled) {
                    const textToSpeak = this.extractTextForSpeech(data.final_content);
                    if (textToSpeak) {
                        window.voiceManager.speakText(textToSpeak);
                    }
                }
            }
        }
    }
    
    handleError(data) {
        window.notificationManager?.error(data.message || 'An error occurred while processing your message');
        
        // Re-enable send button
        if (this.managers.chat && this.managers.chat.ui.sendButton) {
            this.managers.chat.ui.sendButton.disabled = false;
        }
    }
    
    handleTypingIndicator(data) {
        if (this.managers.chat) {
            if (data.typing) {
                this.managers.chat.showTypingIndicator();
            } else {
                this.managers.chat.hideTypingIndicator();
            }
        }
    }
    
    autoScrollIfNeeded() {
        const chatMessages = document.querySelector('.chat-messages');
        if (chatMessages) {
            const isNearBottom = chatMessages.scrollTop + chatMessages.clientHeight >= chatMessages.scrollHeight - 100;
            if (isNearBottom) {
                chatMessages.scrollTop = chatMessages.scrollHeight;
            }
        }
    }
    
    formatMessageContent(content) {
        // Basic markdown formatting for display
        // This could be enhanced with a proper markdown parser
        return content
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/`(.*?)`/g, '<code>$1</code>')
            .replace(/\n/g, '<br>');
    }
    
    async loadChatHistory() {
        try {
            const response = await fetch('/api/chat/history');
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.success && Array.isArray(data.messages)) {
                this.chatHistory = data.messages;
                
                if (this.managers.chat) {
                    // Clear existing messages
                    this.managers.chat.clearChat();
                    
                    // Render chat history
                    data.messages.forEach(message => {
                        this.managers.chat.displayMessage(message);
                    });
                    
                    // Scroll to bottom
                    this.autoScrollIfNeeded();
                }
                
                console.log(`Loaded ${data.messages.length} messages from chat history`);
            } else {
                console.log('No chat history found or empty history');
            }
        } catch (error) {
            console.error('Error loading chat history:', error);
            window.notificationManager?.warning('Could not load chat history: ' + error.message);
        }
    }
    
    sendMessage(messageContent) {
        if (!this.websocket || this.websocket.readyState !== WebSocket.OPEN) {
            window.notificationManager?.error('Not connected to chat server');
            return;
        }
        
        const chatInput = document.getElementById('chat-input');
        const message = messageContent || (chatInput ? chatInput.value.trim() : '');
        
        if (!message) {
            window.notificationManager?.warning('Please enter a message');
            return;
        }
        
        try {
            // Add user message to UI immediately
            const userMessage = {
                id: `user-${Date.now()}`,
                type: 'user',
                content: message,
                timestamp: new Date().toISOString()
            };
            
            if (this.managers.chat) {
                this.managers.chat.displayMessage(userMessage);
            }
            
            // Add to history
            this.chatHistory.push(userMessage);
            
            // Send via WebSocket
            this.websocket.send(JSON.stringify({
                type: 'user_message',
                content: message,
                timestamp: userMessage.timestamp
            }));
            
            // Clear input
            if (chatInput) {
                chatInput.value = '';
            }
            
            // Disable send button temporarily
            if (this.managers.chat && this.managers.chat.ui.sendButton) {
                this.managers.chat.ui.sendButton.disabled = true;
            }
            
            console.log('Message sent:', message);
            
        } catch (error) {
            console.error('Error sending message:', error);
            window.notificationManager?.error('Failed to send message');
        }
    }
    
    setupTranscriptionIntegration() {
        console.log('Setting up transcription integration...');
        
        // Enhanced transcription completion handler
        const originalOnTranscriptionComplete = window.voiceManager.onTranscriptionComplete;
        window.voiceManager.onTranscriptionComplete = (transcript) => {
            console.log('Voice transcription completed:', transcript);
            
            // Call original handler if it exists
            if (originalOnTranscriptionComplete) {
                originalOnTranscriptionComplete.call(window.voiceManager, transcript);
            }
            
            // Auto-fill chat input
            const chatInput = document.getElementById('chat-input') || document.getElementById('message-input');
            if (chatInput && transcript) {
                chatInput.value = transcript;
                chatInput.focus();
                
                // Update character count if available
                const charCount = document.getElementById('char-count');
                if (charCount) {
                    charCount.textContent = transcript.length;
                }
                
                // Auto-send if enabled in settings
                const autoSendVoice = localStorage.getItem('autoSendVoice') === 'true';
                if (autoSendVoice && transcript.trim().length > 0) {
                    setTimeout(() => {
                        if (chatInput.value.trim() === transcript.trim()) {
                            this.managers.chat?.sendMessage?.();
                        }
                    }, 1500); // 1.5 second delay for user to review
                }
            }
        };
        
        // Enhanced transcription error handler
        const originalOnTranscriptionError = window.voiceManager.onTranscriptionError;
        window.voiceManager.onTranscriptionError = (error) => {
            console.error('Voice transcription error:', error);
            
            if (originalOnTranscriptionError) {
                originalOnTranscriptionError.call(window.voiceManager, error);
            }
            
            this.showNotification('Voice transcription failed. Please try again.', 'error');
        };
    }
    
    setupVoiceOutputIntegration() {
        console.log('Setting up voice output integration...');
        
        // Hook into chat manager for AI response playback
        if (this.managers.chat) {
            const originalHandleResponse = this.managers.chat.handleResponse || 
                                         this.managers.chat.handleStreamResponse || 
                                         this.managers.chat.displayMessage;
            
            if (originalHandleResponse) {
                // Create enhanced response handler
                const enhancedResponseHandler = (response, options = {}) => {
                    // Call original handler first
                    let result;
                    try {
                        result = originalHandleResponse.call(this.managers.chat, response, options);
                    } catch (error) {
                        console.error('Error in original response handler:', error);
                    }
                    
                    // Handle voice output for AI responses
                    if (window.voiceManager && 
                        window.voiceManager.isVoiceOutputEnabled && 
                        response && 
                        !options.skipVoice) {
                        
                        const textToSpeak = this.extractTextForSpeech(response);
                        if (textToSpeak && textToSpeak.length > 0) {
                            console.log('Speaking AI response:', textToSpeak.substring(0, 50) + '...');
                            
                            // Add slight delay to ensure UI is updated
                            setTimeout(() => {
                                window.voiceManager.speakText(textToSpeak);
                            }, 300);
                        }
                    }
                    
                    return result;
                };
                
                // Replace the handler
                this.managers.chat.handleResponse = enhancedResponseHandler;
                if (this.managers.chat.handleStreamResponse) {
                    this.managers.chat.handleStreamResponse = enhancedResponseHandler;
                }
            }
        }
        
        // Setup voice output toggle
        this.setupVoiceOutputToggle();
    }
    
    setupVoiceOutputToggle() {
        const voiceToggle = document.getElementById('voice-output-toggle');
        if (voiceToggle && window.voiceManager) {
            // Set initial state
            voiceToggle.checked = window.voiceManager.isVoiceOutputEnabled || false;
            
            // Handle toggle changes
            window.eventManager.add(voiceToggle, 'change', (e) => {
                window.voiceManager.isVoiceOutputEnabled = e.target.checked;
                localStorage.setItem('voiceOutputEnabled', e.target.checked);
                
                const message = e.target.checked ? 
                    'Voice output enabled' : 
                    'Voice output disabled';
                this.showNotification(message, 'info');
                
                console.log('Voice output toggled:', e.target.checked);
            });
        }
    }
    
    setupVoiceCommands() {
        console.log('Setting up voice commands...');
        
        // Define voice commands
        const voiceCommands = {
            'clear chat': () => {
                this.managers.chat?.clearChat?.();
                this.showNotification('Chat cleared', 'info');
            },
            'send message': () => {
                this.managers.chat?.sendMessage?.();
            },
            'refresh models': () => {
                this.managers.model?.refreshModels?.();
                this.showNotification('Refreshing models...', 'info');
            },
            'open settings': () => {
                this.managers.settingsPanel?.togglePanel?.();
            },
            'export chat': () => {
                this.exportChatHistory();
                this.showNotification('Exporting chat history...', 'info');
            }
        };
        
        // Enhanced command recognition
        if (window.voiceManager && window.voiceManager.onTranscriptionComplete) {
            const originalHandler = window.voiceManager.onTranscriptionComplete;
            
            window.voiceManager.onTranscriptionComplete = (transcript) => {
                const lowerTranscript = transcript.toLowerCase().trim();
                
                // Check for voice commands
                for (const [command, action] of Object.entries(voiceCommands)) {
                    if (lowerTranscript.includes(command)) {
                        console.log('Executing voice command:', command);
                        action();
                        return; // Don't process as regular text
                    }
                }
                
                // If no command matched, process as regular transcription
                originalHandler(transcript);
            };
        }
    }
    
    setupVoiceOutputForResponses() {
        // Hook into the chat manager to speak AI responses
        if (this.managers.chat) {
            const originalHandleResponse = this.managers.chat.handleStreamResponse || this.managers.chat.handleResponse;
            if (originalHandleResponse) {
                this.managers.chat.handleResponse = (response) => {
                    // Call original handler
                    const result = originalHandleResponse.call(this.managers.chat, response);
                    
                    // Speak the response if voice output is enabled
                    if (window.voiceManager && window.voiceManager.isVoiceOutputEnabled && response) {
                        // Extract text from response (might be markdown)
                        const textToSpeak = this.extractTextForSpeech(response);
                        if (textToSpeak) {
                            window.voiceManager.speakText(textToSpeak);
                        }
                    }
                    
                    return result;
                };
            }
        }
    }
    
    extractTextForSpeech(text) {
        // Remove markdown and HTML for cleaner speech
        if (!text) return '';
        
        // Basic markdown removal
        let cleanText = text
            .replace(/\*\*(.*?)\*\*/g, '$1')  // Bold
            .replace(/\*(.*?)\*/g, '$1')      // Italic
            .replace(/`(.*?)`/g, '$1')        // Inline code
            .replace(/```[\s\S]*?```/g, '[code block]')  // Code blocks
            .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')    // Links
            .replace(/^#+\s+/gm, '')          // Headers
            .replace(/^\s*[-*+]\s+/gm, '')    // Lists
            .replace(/\n{2,}/g, '\n')         // Multiple newlines
            .trim();
        
        // Limit length for speech
        if (cleanText.length > 500) {
            cleanText = cleanText.substring(0, 500) + '...';
        }
        
        return cleanText;
    }

    showNotification(message, type = 'info') {
        // Use centralized notification manager
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
            notification.className = `notification notification-${type}`;
            notification.textContent = message;
            
            notification.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                background: var(--accent-color);
                color: white;
                padding: 12px 20px;
                border-radius: 6px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.3);
                z-index: 10000;
                transition: all 0.3s ease;
                max-width: 300px;
                word-wrap: break-word;
            `;
            
            document.body.appendChild(notification);
            
            setTimeout(() => {
                notification.style.opacity = '0';
                notification.style.transform = 'translateX(100%)';
                setTimeout(() => {
                    if (notification.parentNode) {
                        notification.parentNode.removeChild(notification);
                    }
                }, 300);
            }, 3000);
        }
    }

    setupDeviceOptimizations() {
        // Setup mobile-specific handlers
        if (this.deviceInfo.isMobile) {
            this.setupMobileOptimizations();
        }

        // Setup iOS Safari specific fixes
        if (this.deviceInfo.isIOSSafari()) {
            this.setupIOSSafariOptimizations();
        }

        // Listen for device changes
        window.eventManager.add(window, 'viewportChange', (e) => {
            this.handleViewportChange(e.detail);
        });

        window.eventManager.add(window, 'orientationChange', (e) => {
            this.handleOrientationChange(e.detail);
        });
    }

    setupMobileOptimizations() {
        const chatInput = document.getElementById('chat-input');
        const chatInputContainer = document.querySelector('.chat-input-container');
        if (!chatInput || !chatInputContainer) return;

        // Force input container visibility
        const ensureInputContainerVisible = () => {
            chatInputContainer.style.position = 'sticky';
            chatInputContainer.style.bottom = '0';
            chatInputContainer.style.zIndex = '1000';
            chatInputContainer.style.background = 'var(--surface-color)';
            chatInputContainer.style.borderTop = '2px solid var(--border-color)';
        };

        // Apply immediately
        ensureInputContainerVisible();

        // Handle virtual keyboard on mobile
        window.eventManager.add(chatInput, 'focus', () => {
            setTimeout(() => {
                ensureInputContainerVisible();
            }, 100);
        });

        window.eventManager.add(chatInput, 'blur', () => {
            ensureInputContainerVisible();
        });

        // Prevent zoom on double-tap for mobile
        let lastTouchEnd = 0;
        window.eventManager.add(document, 'touchend', (event) => {
            const now = (new Date()).getTime();
            if (now - lastTouchEnd <= 300) {
                event.preventDefault();
            }
            lastTouchEnd = now;
        }, false);

        // Handle touch events on input to ensure visibility
        window.eventManager.add(chatInput, 'touchstart', () => {
            ensureInputContainerVisible();
            
            // Force repaint
            chatInputContainer.style.transform = 'translateZ(0)';
            setTimeout(() => {
                chatInputContainer.style.transform = 'none';
            }, 10);
        });

        // Monitor scroll to keep input visible
        const chatMessages = document.querySelector('.chat-messages');
        if (chatMessages) {
            window.eventManager.add(chatMessages, 'scroll', window.eventManager.debounce(ensureInputContainerVisible, 100));
        }

        // Intersection Observer to monitor input visibility
        if ('IntersectionObserver' in window) {
            const inputObserver = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.target === chatInputContainer) {
                        if (!entry.isIntersecting) {
                            console.log('🚨 Chat input not visible, forcing visibility');
                            ensureInputContainerVisible();
                            
                            // Scroll to make it visible
                            chatInputContainer.scrollIntoView({ 
                                behavior: 'smooth', 
                                block: 'end' 
                            });
                        }
                    }
                });
            }, {
                threshold: 0.1,
                rootMargin: '0px'
            });

            inputObserver.observe(chatInputContainer);
        }
    }

    setupIOSSafariOptimizations() {
        // Handle iOS Safari address bar changes and viewport height
        const chatContainer = document.querySelector('.chat-container');
        const chatPageContainer = document.querySelector('.chat-page-container');
        if (!chatContainer || !chatPageContainer) return;

        // Set CSS custom properties for viewport height
        const setViewportHeight = () => {
            const vh = window.innerHeight * 0.01;
            document.documentElement.style.setProperty('--vh', `${vh}px`);
        };

        // Initial setup
        setViewportHeight();

        // Handle keyboard detection and viewport changes
        let initialViewportHeight = window.innerHeight;
        let isKeyboardOpen = false;

        const handleViewportResize = () => {
            const currentHeight = window.innerHeight;
            const heightDifference = initialViewportHeight - currentHeight;
            
            // Detect keyboard (if viewport height reduced by more than 150px)
            const newKeyboardState = heightDifference > 150;
            
            if (newKeyboardState !== isKeyboardOpen) {
                isKeyboardOpen = newKeyboardState;
                
                if (isKeyboardOpen) {
                    document.body.classList.add('keyboard-open');
                    // Ensure input is visible when keyboard opens
                    const chatInput = document.getElementById('chat-input');
                    if (chatInput) {
                        setTimeout(() => {
                            chatInput.scrollIntoView({ 
                                behavior: 'smooth', 
                                block: 'end' 
                            });
                        }, 100);
                    }
                } else {
                    document.body.classList.remove('keyboard-open');
                }
            }
            
            // Update viewport height
            setViewportHeight();
            
            // Apply device-specific classes
            if (this.deviceInfo.isIOSSafari()) {
                document.body.classList.add('ios-safari');
            }
            if (this.deviceInfo.isMobile) {
                document.body.classList.add('device-mobile');
            }
        };

        // Listen for resize events
        window.eventManager.add(window, 'resize', window.eventManager.debounce(handleViewportResize, 100));
        
        // Handle orientation changes with delay
        window.eventManager.add(window, 'orientationchange', () => {
            setTimeout(() => {
                initialViewportHeight = window.innerHeight;
                handleViewportResize();
            }, 500);
        });

        // Initial application of classes
        handleViewportResize();

        // Force input visibility on scroll
        const chatInput = document.getElementById('chat-input');
        if (chatInput) {
            // Ensure input container is always visible
            const ensureInputVisible = () => {
                const inputContainer = document.querySelector('.chat-input-container');
                if (inputContainer) {
                    inputContainer.style.transform = 'translateZ(0)'; // Force hardware acceleration
                    inputContainer.style.willChange = 'transform'; // Optimize for changes
                }
            };

            // Apply on focus and touch
            window.eventManager.add(chatInput, 'focus', ensureInputVisible);
            window.eventManager.add(chatInput, 'touchstart', ensureInputVisible);
            
            // Apply initially
            ensureInputVisible();
        }
    }

    handleViewportChange(detail) {
        console.log('📱 Viewport changed:', detail);
        
        // Adjust UI based on new viewport
        if (detail.device.type === 'mobile' && !this.deviceInfo.isMobile) {
            // Switched to mobile view
            this.setupMobileOptimizations();
        }
    }

    handleOrientationChange(detail) {
        console.log('🔄 Orientation changed:', detail.orientation);
        
        // Adjust chat container for orientation
        const chatMessages = document.querySelector('.chat-messages');
        if (chatMessages && this.deviceInfo.isMobile) {
            // Give time for orientation change to complete
            setTimeout(() => {
                chatMessages.scrollTop = chatMessages.scrollHeight;
            }, 500);
        }
    }

    setupManagerCommunication() {
        // Listen for custom events between managers
        window.eventManager.add(document, 'chatSettingsPanelOpened', () => {
            // Handle settings panel opening
            console.log('Settings panel opened');
        });

        // Setup keyboard shortcuts
        this.setupKeyboardShortcuts();
    }

    setupKeyboardShortcuts() {
        window.eventManager.add(document, 'keydown', (e) => {
            // Ctrl/Cmd + K to focus chat input
            if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                e.preventDefault();
                const chatInput = document.getElementById('chat-input');
                if (chatInput) {
                    chatInput.focus();
                }
            }

            // Ctrl/Cmd + L to clear chat
            if ((e.ctrlKey || e.metaKey) && e.key === 'l') {
                e.preventDefault();
                this.managers.chat?.clearChat?.();
            }

            // Ctrl/Cmd + , to open settings
            if ((e.ctrlKey || e.metaKey) && e.key === ',') {
                e.preventDefault();
                this.managers.settingsPanel?.togglePanel?.();
            }
        });
    }

    // Public API methods
    getChatManager() {
        return this.managers.chat;
    }

    getModelManager() {
        return this.managers.model;
    }

    getSettingsPanelManager() {
        return this.managers.settingsPanel;
    }

    getAllManagers() {
        return this.managers;
    }

    async loadSamplePrompts() {
        try {
            const samplePromptsContainer = document.getElementById('sample-prompts-list');
            const toggleButton = document.getElementById('toggle-sample-prompts');
            const samplePromptsSection = document.getElementById('sample-prompts');
            
            if (!samplePromptsContainer) return;

            // Fetch sample prompts from API
            const response = await fetch('/api/sample_prompts');
            const data = await response.json();

            if (data.success && data.prompts) {
                // Clear loading message
                samplePromptsContainer.innerHTML = '';

                // Create prompt items
                data.prompts.forEach(prompt => {
                    const promptItem = document.createElement('div');
                    promptItem.className = 'sample-prompt-item';
                    promptItem.textContent = prompt;
                    
                    // Add click handler to use prompt
                    window.eventManager.add(promptItem, 'click', () => {
                        const chatInput = document.getElementById('chat-input');
                        if (chatInput) {
                            chatInput.value = prompt;
                            chatInput.focus();
                            
                            // Auto-send if chat manager is available
                            if (this.managers.chat && this.managers.chat.sendMessage) {
                                // Small delay to allow UI to update
                                setTimeout(() => {
                                    this.managers.chat.sendMessage();
                                }, 100);
                            }
                        }
                    });

                    samplePromptsContainer.appendChild(promptItem);
                });

                // Setup toggle functionality
                if (toggleButton && samplePromptsSection) {
                    let isHidden = false;
                    
                    window.eventManager.add(toggleButton, 'click', () => {
                        isHidden = !isHidden;
                        samplePromptsContainer.style.display = isHidden ? 'none' : 'block';
                        toggleButton.innerHTML = isHidden ? 
                            '<i class="bi bi-chevron-down"></i> Show Sample Prompts' : 
                            '<i class="bi bi-chevron-up"></i> Hide Sample Prompts';
                    });
                }
            } else {
                samplePromptsContainer.innerHTML = '<div class="loading-prompts">No sample prompts available</div>';
            }

        } catch (error) {
            console.warn('Could not load sample prompts:', error);
            const samplePromptsContainer = document.getElementById('sample-prompts-list');
            if (samplePromptsContainer) {
                samplePromptsContainer.innerHTML = '<div class="loading-prompts">Sample prompts unavailable</div>';
            }
        }
    }

    // Utility methods
    async sendMessageProgrammatically(message) {
        // Send a message programmatically (from external calls)
        this.sendMessage(message);
    }

    clearChat() {
        this.managers.chat?.clearChat?.();
    }

    refreshModels() {
        return this.managers.model?.refreshModels?.();
    }

    exportChatHistory() {
        const history = this.managers.chat?.getChatHistory?.();
        if (history) {
            const blob = new Blob([JSON.stringify(history, null, 2)], { 
                type: 'application/json' 
            });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `chat-history-${new Date().toISOString().split('T')[0]}.json`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }
    }

    importChatHistory(file) {
        const reader = new FileReader();
        reader.onload = (e) => {
            try {
                const history = JSON.parse(e.target.result);
                this.managers.chat?.loadChatHistory?.(history);
            } catch (error) {
                console.error('Error importing chat history:', error);
                this.showNotification('error', 'Failed to import chat history. Please check the file format and try again.');
            }
        };
        reader.readAsText(file);
    }
}

// Initialize when DOM is ready
window.eventManager.add(document, 'DOMContentLoaded', () => {
    window.chatController = new ChatController();
});

// Export for potential external use
export { ChatController };
