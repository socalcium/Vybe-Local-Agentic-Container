/**
 * Voice functionality for Vybe chat interface
 * Handles speech recognition and text-to-speech using Web APIs
 */

class VoiceManager {
    constructor() {
        // Cleanup functions for event listeners
        this.cleanupFunctions = [];
        
        this.recognition = null;
        this.synthesis = window.speechSynthesis;
        this.isListening = false;
        this.isVoiceOutputEnabled = false;
        this.currentUtterance = null;
        
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
        // Initialize speech recognition if available
        if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            this.recognition = new SpeechRecognition();
            
            this.recognition.continuous = false;
            this.recognition.interimResults = true;
            this.recognition.lang = 'en-US';
            
            this.setupRecognitionHandlers();
        }
        
        // Initialize UI handlers
        this.setupUIHandlers();
        
        // Check capabilities
        this.checkCapabilities();
    }
    
    setupRecognitionHandlers() {
        if (!this.recognition) return;
        
        this.recognition.onstart = () => {
            console.log('Voice recognition started');
            this.updateVoiceInputButton(true);
        };
        
        this.recognition.onresult = (event) => {
            let finalTranscript = '';
            let interimTranscript = '';
            
            for (let i = event.resultIndex; i < event.results.length; i++) {
                const transcript = event.results[i][0].transcript;
                if (event.results[i].isFinal) {
                    finalTranscript += transcript;
                } else {
                    interimTranscript += transcript;
                }
            }
            
            // Update the message input with the transcript
            const messageInput = document.getElementById('message-input');
            if (messageInput) {
                if (finalTranscript) {
                    messageInput.value = finalTranscript;
                    // Optionally trigger send
                    this.onTranscriptionComplete(finalTranscript);
                } else if (interimTranscript) {
                    // Show interim results
                    messageInput.placeholder = `Listening: ${interimTranscript}`;
                }
            }
        };
        
        this.recognition.onerror = (event) => {
            console.error('Speech recognition error:', event.error);
            this.stopListening();
            this.showVoiceError(`Speech recognition error: ${event.error}`);
        };
        
        this.recognition.onend = () => {
            console.log('Voice recognition ended');
            this.stopListening();
        };
    }
    
    setupUIHandlers() {
        const voiceInputBtn = document.getElementById('voice-input-btn');
        const voiceOutputBtn = document.getElementById('voice-output-btn');
        const voiceSettingsBtn = document.getElementById('voice-settings-btn');
        
        if (voiceInputBtn) {
            const inputHandler = (e) => {
                // Check for long press to stop speaking
                if (e.type === 'mousedown' && this.synthesis.speaking) {
                    this.stopSpeaking();
                } else if (e.type === 'click') {
                    this.toggleVoiceInput();
                }
            };
            voiceInputBtn.addEventListener('click', inputHandler);
            voiceInputBtn.addEventListener('mousedown', inputHandler);
            this.cleanupFunctions.push(() => {
                voiceInputBtn.removeEventListener('click', inputHandler);
                voiceInputBtn.removeEventListener('mousedown', inputHandler);
            });
        }
        
        if (voiceOutputBtn) {
            const outputHandler = (e) => {
                if (e.type === 'mousedown' && this.synthesis.speaking) {
                    this.stopSpeaking();
                } else if (e.type === 'click') {
                    this.toggleVoiceOutput();
                }
            };
            voiceOutputBtn.addEventListener('click', outputHandler);
            voiceOutputBtn.addEventListener('mousedown', outputHandler);
            this.cleanupFunctions.push(() => {
                voiceOutputBtn.removeEventListener('click', outputHandler);
                voiceOutputBtn.removeEventListener('mousedown', outputHandler);
            });
        }

        if (voiceSettingsBtn) {
            const settingsHandler = () => this.showVoiceSettings();
            voiceSettingsBtn.addEventListener('click', settingsHandler);
            this.cleanupFunctions.push(() => voiceSettingsBtn.removeEventListener('click', settingsHandler));
        }

        // Add keyboard shortcuts
        const keyHandler = (e) => {
            if (e.ctrlKey || e.metaKey) {
                switch (e.key) {
                    case 'm':
                        if (e.shiftKey) {
                            e.preventDefault();
                            this.toggleVoiceInput();
                        }
                        break;
                    case 'l':
                        if (e.shiftKey) {
                            e.preventDefault();
                            this.toggleVoiceOutput();
                        }
                        break;
                    case 'Escape':
                        if (this.synthesis.speaking) {
                            e.preventDefault();
                            this.stopSpeaking();
                        }
                        break;
                }
            }
        };
        
        document.addEventListener('keydown', keyHandler);
        this.cleanupFunctions.push(() => document.removeEventListener('keydown', keyHandler));

        // Show keyboard shortcuts info on first load
        setTimeout(() => {
            this.showToast('Voice shortcuts: Ctrl+Shift+M (mic), Ctrl+Shift+L (speaker), Esc (stop)', 'info');
        }, 2000);
    }
    
    toggleVoiceInput() {
        if (!this.recognition) {
            this.showVoiceError('Speech recognition not supported in this browser');
            return;
        }
        
        if (this.isListening) {
            this.stopListening();
        } else {
            this.startListening();
        }
    }
    
    startListening() {
        if (!this.recognition || this.isListening) return;
        
        try {
            this.isListening = true;
            this.recognition.start();
            
            // Reset message input placeholder
            const messageInput = document.getElementById('message-input');
            if (messageInput) {
                messageInput.placeholder = 'Listening...';
            }
        } catch (error) {
            console.error('Error starting speech recognition:', error);
            this.isListening = false;
            this.showVoiceError('Failed to start voice recognition');
        }
    }
    
    stopListening() {
        if (!this.recognition || !this.isListening) return;
        
        this.isListening = false;
        this.recognition.stop();
        this.updateVoiceInputButton(false);
        
        // Reset message input placeholder
        const messageInput = document.getElementById('message-input');
        if (messageInput) {
            messageInput.placeholder = 'Type your message...';
        }
    }
    
    toggleVoiceOutput() {
        this.isVoiceOutputEnabled = !this.isVoiceOutputEnabled;
        this.updateVoiceOutputButton();
        
        // Stop any current speech
        if (!this.isVoiceOutputEnabled && this.synthesis.speaking) {
            this.synthesis.cancel();
        }
        
        this.showVoiceStatus(`Voice output ${this.isVoiceOutputEnabled ? 'enabled' : 'disabled'}`);
    }
    
    speakText(text) {
        if (!this.isVoiceOutputEnabled || !this.synthesis) {
            return;
        }
        
        // Cancel any ongoing speech
        this.synthesis.cancel();
        
        // Create new utterance
        this.currentUtterance = new SpeechSynthesisUtterance(text);
        this.currentUtterance.rate = 0.8;
        this.currentUtterance.pitch = 1;
        this.currentUtterance.volume = 0.8;
        
        // Set up event handlers
        this.currentUtterance.onstart = () => {
            console.log('Started speaking');
        };
        
        this.currentUtterance.onend = () => {
            console.log('Finished speaking');
            this.currentUtterance = null;
        };
        
        this.currentUtterance.onerror = (event) => {
            console.error('Speech synthesis error:', event.error);
            this.currentUtterance = null;
        };
        
        // Speak the text
        this.synthesis.speak(this.currentUtterance);
    }
    
    onTranscriptionComplete(transcript) {
        console.log('Transcription complete:', transcript);
        
        // Process voice commands first
        if (this.processVoiceCommand(transcript)) {
            return; // Command was processed, don't continue with regular input
        }
        
        // Check auto-send setting
        const autoSend = document.getElementById('auto-send')?.checked || false;
        
        if (autoSend) {
            // Small delay to let user see the transcript
            setTimeout(() => {
                const sendBtn = document.querySelector('.send-button') || document.getElementById('send-btn');
                if (sendBtn && !sendBtn.disabled) {
                    sendBtn.click();
                    this.showToast('Message sent automatically', 'success');
                }
            }, 1000);
        } else {
            this.showToast('Voice input complete. Click send or use voice command "send message"', 'info');
        }
    }
    
    updateVoiceInputButton(isListening = this.isListening) {
        const btn = document.getElementById('voice-input-btn');
        if (!btn) return;
        
        if (isListening) {
            btn.classList.add('listening');
            btn.title = 'Stop Voice Input';
            btn.style.backgroundColor = '#ff4757';
        } else {
            btn.classList.remove('listening');
            btn.title = 'Start Voice Input';
            btn.style.backgroundColor = '';
        }
    }
    
    updateVoiceOutputButton() {
        const btn = document.getElementById('voice-output-btn');
        if (!btn) return;
        
        if (this.isVoiceOutputEnabled) {
            btn.classList.add('enabled');
            btn.title = 'Disable Voice Output';
            btn.style.backgroundColor = '#2ed573';
        } else {
            btn.classList.remove('enabled');
            btn.title = 'Enable Voice Output';
            btn.style.backgroundColor = '';
        }
    }
    
    checkCapabilities() {
        const capabilities = {
            speechRecognition: !!this.recognition,
            speechSynthesis: !!this.synthesis && 'speak' in this.synthesis,
            microphone: navigator.mediaDevices && 'getUserMedia' in navigator.mediaDevices
        };
        
        console.log('Voice capabilities:', capabilities);
        
        // Update UI based on capabilities
        const voiceInputBtn = document.getElementById('voice-input-btn');
        const voiceOutputBtn = document.getElementById('voice-output-btn');
        
        if (voiceInputBtn && !capabilities.speechRecognition) {
            voiceInputBtn.disabled = true;
            voiceInputBtn.title = 'Speech recognition not supported';
        }
        
        if (voiceOutputBtn && !capabilities.speechSynthesis) {
            voiceOutputBtn.disabled = true;
            voiceOutputBtn.title = 'Speech synthesis not supported';
        }
        
        return capabilities;
    }
    
    showVoiceError(message) {
        console.error('Voice error:', message);
        this.showToast(message, 'error');
    }
    
    showVoiceStatus(message, type = 'info') {
        console.log(`Voice status (${type}):`, message);
        this.showToast(message, type);
    }

    showToast(message, type = 'info') {
        // Create toast element if it doesn't exist
        let toastContainer = document.getElementById('voice-toast-container');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.id = 'voice-toast-container';
            toastContainer.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 9999;
                max-width: 300px;
            `;
            document.body.appendChild(toastContainer);
        }

        const toast = document.createElement('div');
        const typeColors = {
            'success': '#28a745',
            'error': '#dc3545',
            'warning': '#ffc107',
            'info': '#17a2b8'
        };
        
        toast.style.cssText = `
            background: ${typeColors[type] || typeColors.info};
            color: white;
            padding: 12px 16px;
            border-radius: 4px;
            margin-bottom: 8px;
            font-size: 14px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.2);
            opacity: 0;
            transition: opacity 0.3s ease;
        `;
        toast.textContent = message;
        
        toastContainer.appendChild(toast);
        
        // Fade in
        setTimeout(() => toast.style.opacity = '1', 10);
        
        // Auto remove after 4 seconds
        setTimeout(() => {
            toast.style.opacity = '0';
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
            }, 300);
        }, 4000);
    }

    // Enhanced voice recognition with confidence scoring
    setupAdvancedRecognition() {
        if (!this.recognition) return;

        this.recognition.maxAlternatives = 3;
        this.recognition.continuous = true;
        this.recognition.interimResults = true;

        // Add language detection
        this.detectLanguage();
    }

    async detectLanguage() {
        try {
            const lang = navigator.language || navigator.userLanguage || 'en-US';
            if (this.recognition) {
                this.recognition.lang = lang;
                console.log('Voice recognition language set to:', lang);
            }
        } catch {
            console.warn('Could not detect language, using default en-US');
        }
    }

    // Voice commands processing
    processVoiceCommand(transcript) {
        const command = transcript.toLowerCase().trim();
        
        // Check for voice commands
        if (command.startsWith('search for ')) {
            const query = command.replace('search for ', '');
            this.executeSearchCommand(query);
            return true;
        } else if (command === 'clear message' || command === 'clear input') {
            this.clearMessageInput();
            return true;
        } else if (command === 'send message' || command === 'send') {
            this.sendCurrentMessage();
            return true;
        } else if (command === 'stop listening') {
            this.stopListening();
            return true;
        }
        
        return false;
    }

    executeSearchCommand(query) {
        // If on search page, fill search input
        const searchInput = document.getElementById('search-query') || document.getElementById('search-input');
        if (searchInput) {
            searchInput.value = query;
            this.showToast(`Search query set: "${query}"`, 'success');
            
            // Auto-trigger search if search button exists
            const searchBtn = document.getElementById('search-button') || document.getElementById('search-btn');
            if (searchBtn && !searchBtn.disabled) {
                setTimeout(() => searchBtn.click(), 500);
            }
        } else {
            this.showToast('Search not available on this page', 'warning');
        }
    }

    clearMessageInput() {
        const messageInput = document.getElementById('message-input');
        if (messageInput) {
            messageInput.value = '';
            this.showToast('Message input cleared', 'success');
        }
    }

    sendCurrentMessage() {
        const sendBtn = document.querySelector('.send-button') || document.getElementById('send-btn');
        if (sendBtn && !sendBtn.disabled) {
            sendBtn.click();
            this.showToast('Message sent via voice command', 'success');
        } else {
            this.showToast('No message to send or send button unavailable', 'warning');
        }
    }

    // Enhanced speech synthesis with better voice selection
    async selectBestVoice() {
        if (!this.synthesis) return null;

        return new Promise((resolve) => {
            const setVoice = () => {
                const voices = this.synthesis.getVoices();
                
                // Prefer local voices over remote ones
                let selectedVoice = voices.find(voice => 
                    voice.lang.startsWith(navigator.language.split('-')[0]) && voice.localService
                );
                
                // Fallback to any voice matching language
                if (!selectedVoice) {
                    selectedVoice = voices.find(voice => 
                        voice.lang.startsWith(navigator.language.split('-')[0])
                    );
                }
                
                // Final fallback to default English voice
                if (!selectedVoice) {
                    selectedVoice = voices.find(voice => voice.lang.startsWith('en'));
                }
                
                resolve(selectedVoice || voices[0]);
            };

            if (this.synthesis.getVoices().length > 0) {
                setVoice();
            } else {
                this.synthesis.onvoiceschanged = setVoice;
            }
        });
    }

    async enhancedSpeakText(text, options = {}) {
        if (!this.isVoiceOutputEnabled || !this.synthesis) {
            return;
        }

        // Cancel any ongoing speech
        this.synthesis.cancel();

        const voice = await this.selectBestVoice();
        
        // Create new utterance with enhanced options
        this.currentUtterance = new SpeechSynthesisUtterance(text);
        
        if (voice) {
            this.currentUtterance.voice = voice;
        }
        
        this.currentUtterance.rate = options.rate || 0.9;
        this.currentUtterance.pitch = options.pitch || 1;
        this.currentUtterance.volume = options.volume || 0.8;

        // Enhanced event handlers
        this.currentUtterance.onstart = () => {
            console.log('Started speaking:', text.substring(0, 50) + '...');
            this.updateSpeechStatus(true);
        };
        
        this.currentUtterance.onend = () => {
            console.log('Finished speaking');
            this.currentUtterance = null;
            this.updateSpeechStatus(false);
        };
        
        this.currentUtterance.onerror = (event) => {
            console.error('Speech synthesis error:', event.error);
            this.currentUtterance = null;
            this.updateSpeechStatus(false);
            this.showVoiceError(`Speech error: ${event.error}`);
        };

        // Speak the text
        this.synthesis.speak(this.currentUtterance);
    }

    updateSpeechStatus(isSpeaking) {
        const voiceOutputBtn = document.getElementById('voice-output-btn');
        if (voiceOutputBtn) {
            if (isSpeaking) {
                voiceOutputBtn.classList.add('speaking');
                voiceOutputBtn.title = 'Speaking... (Click to stop)';
            } else {
                voiceOutputBtn.classList.remove('speaking');
                voiceOutputBtn.title = this.isVoiceOutputEnabled ? 'Disable Voice Output' : 'Enable Voice Output';
            }
        }
    }

    // Stop current speech
    stopSpeaking() {
        if (this.synthesis && this.synthesis.speaking) {
            this.synthesis.cancel();
            this.updateSpeechStatus(false);
            this.showToast('Speech stopped', 'info');
        }
    }

    // Enhanced voice settings
    showVoiceSettings() {
        const settingsModal = this.createVoiceSettingsModal();
        document.body.appendChild(settingsModal);
    }

    createVoiceSettingsModal() {
        const modal = document.createElement('div');
        modal.className = 'voice-settings-modal';
        modal.innerHTML = `
            <div class="modal-overlay"></div>
            <div class="modal-content">
                <h3>Voice Settings</h3>
                <div class="settings-group">
                    <label for="voice-rate">Speech Rate:</label>
                    <input type="range" id="voice-rate" min="0.5" max="2" step="0.1" value="0.9">
                    <span id="rate-value">0.9</span>
                </div>
                <div class="settings-group">
                    <label for="voice-pitch">Speech Pitch:</label>
                    <input type="range" id="voice-pitch" min="0" max="2" step="0.1" value="1">
                    <span id="pitch-value">1</span>
                </div>
                <div class="settings-group">
                    <label for="voice-volume">Speech Volume:</label>
                    <input type="range" id="voice-volume" min="0" max="1" step="0.1" value="0.8">
                    <span id="volume-value">0.8</span>
                </div>
                <div class="settings-group">
                    <label for="auto-send">Auto-send after voice input:</label>
                    <input type="checkbox" id="auto-send">
                </div>
                <div class="modal-actions">
                    <button onclick="this.parentElement.parentElement.parentElement.remove()">Close</button>
                    <button onclick="window.voiceManager.testVoiceSettings()">Test Voice</button>
                </div>
            </div>
        `;

        // Style the modal
        modal.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            z-index: 10000;
            display: flex;
            align-items: center;
            justify-content: center;
        `;

        return modal;
    }

    testVoiceSettings() {
        const rate = document.getElementById('voice-rate')?.value || 0.9;
        const pitch = document.getElementById('voice-pitch')?.value || 1;
        const volume = document.getElementById('voice-volume')?.value || 0.8;
        
        this.enhancedSpeakText('This is a test of your voice settings.', {
            rate: parseFloat(rate),
            pitch: parseFloat(pitch),
            volume: parseFloat(volume)
        });
    }
}

// Initialize voice manager when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.voiceManager = new VoiceManager();
});

// Export for module use (if running in Node.js environment)
/* global module */
if (typeof window === 'undefined' && typeof module !== 'undefined' && module.exports) {
    module.exports = VoiceManager;
}
