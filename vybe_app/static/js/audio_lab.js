/**
 * Audio Lab JavaScript - COMPLETE REWRITE
 * Handles TTS, transcription, and audio model management
 */

// Import the centralized notification manager (attaches to window.notificationManager)
import './services/NotificationManager.js';

// Import the enhanced EventManager
import './utils/EventManager.js';

class AudioLab {
    constructor() {
        this.currentTab = 'tts-panel';
        this.availableVoices = [];
        this.currentAudio = null;
        
        // Create dedicated event manager for this instance
        this.eventManager = new window.EventManager('AudioLab');
        
        this.init();
    }
    
    // Destroy method to prevent memory leaks
    destroy() {
        // Use enhanced event manager cleanup
        this.eventManager.destroy();
        
        // Stop any current audio
        if (this.currentAudio) {
            this.currentAudio.pause();
            this.currentAudio = null;
        }
    }
    
    // Clean up without destroying (for reinitialization)
    cleanup() {
        this.eventManager.cleanup();
        
        if (this.currentAudio) {
            this.currentAudio.pause();
            this.currentAudio = null;
        }
    }


    init() {
        console.log('Initializing Audio Lab...');
        
        this.initializeElements();
        this.setupEventListeners();
        this.loadInitialData();
        
        // Cleanup on page unload
        this.eventManager.add(window, 'beforeunload', () => {
            this.destroy();
        });
    }

    initializeElements() {
        // Tab elements
        this.tabButtons = document.querySelectorAll('.audio-tab-btn');
        this.tabPanels = document.querySelectorAll('.tab-panel');
        
        // TTS elements
        this.ttsText = document.getElementById('tts-text');
        this.voiceSelect = document.getElementById('voice-select');
        this.speedSlider = document.getElementById('speed-slider');
        this.speedValue = document.getElementById('speed-value');
        this.generateBtn = document.getElementById('generate-speech-btn');
        this.charCount = document.getElementById('char-count');
        
        // Audio preview elements
        this.audioPreview = document.getElementById('audio-preview');
        this.audioPlayer = document.getElementById('audio-player');
        this.usedVoice = document.getElementById('used-voice');
        this.audioLength = document.getElementById('audio-length');
        this.downloadAudio = document.getElementById('download-audio');
        
        // Transcription elements
        this.audioUploadArea = document.getElementById('audio-upload-area');
        this.audioFileInput = document.getElementById('audio-file-input');
        this.transcriptionOutput = document.getElementById('transcription-output');
        this.copyTranscription = document.getElementById('copy-transcription');
        this.downloadTranscription = document.getElementById('download-transcription');
        
        // Voice cloning elements
        this.voiceUploadArea = document.getElementById('voice-upload-area');
        this.voiceFileInput = document.getElementById('voice-file-input');
        this.voiceName = document.getElementById('voice-name');
        this.cloneVoiceBtn = document.getElementById('clone-voice-btn');
        this.clonedVoicesList = document.getElementById('cloned-voices-list');
        
        // Models elements
        this.whisperModels = document.getElementById('whisper-models');
        this.ttsModels = document.getElementById('tts-models');
        this.refreshModelsBtn = document.getElementById('refresh-models-btn');
        this.testModelsBtn = document.getElementById('test-models-btn');
        this.openStudioBtn = document.getElementById('open-audio-studio-btn');
    }

    setupEventListeners() {
        // Tab switching
        this.tabButtons.forEach(button => {
            this.eventManager.add(button, 'click', () => {
                this.switchTab(button.dataset.target);
            });
        });

        // TTS form
        if (this.ttsText) {
            this.eventManager.add(this.ttsText, 'input', this.eventManager.debounce(() => {
                this.updateCharCount();
            }, 100));
        }

        if (this.speedSlider) {
            this.eventManager.add(this.speedSlider, 'input', this.eventManager.debounce(() => {
                this.speedValue.textContent = this.speedSlider.value;
            }, 100));
        }

        if (this.generateBtn) {
            this.eventManager.add(this.generateBtn, 'click', () => {
                this.generateSpeech();
            });
        }

        // File upload areas
        this.setupFileUpload(this.audioUploadArea, this.audioFileInput, this.handleAudioUpload.bind(this));
        this.setupFileUpload(this.voiceUploadArea, this.voiceFileInput, this.handleVoiceUpload.bind(this));

        // Transcription actions
        if (this.copyTranscription) {
            this.eventManager.add(this.copyTranscription, 'click', () => {
                this.copyTranscriptionToClipboard();
            });
        }

        if (this.downloadTranscription) {
            this.eventManager.add(this.downloadTranscription, 'click', () => {
                this.downloadTranscriptionFile();
            });
        }

        // Voice cloning
        if (this.voiceName) {
            this.eventManager.add(this.voiceName, 'input', this.eventManager.debounce(() => {
                this.updateCloneButton();
            }, 100));
        }

        if (this.cloneVoiceBtn) {
            this.eventManager.add(this.cloneVoiceBtn, 'click', () => {
                this.cloneVoice();
            });
        }

        // Models
        if (this.refreshModelsBtn) {
            this.eventManager.add(this.refreshModelsBtn, 'click', () => {
                this.loadAudioModels();
            });
        }

        if (this.testModelsBtn) {
            this.eventManager.add(this.testModelsBtn, 'click', () => {
                this.testAudioModels();
            });
        }

        if (this.openStudioBtn) {
            this.eventManager.add(this.openStudioBtn, 'click', () => {
                this.openAudioStudio();
            });
        }

        // Audio download
        if (this.downloadAudio) {
            this.eventManager.add(this.downloadAudio, 'click', () => {
                this.downloadGeneratedAudio();
            });
        }
    }

    loadInitialData() {
        // Load immediately - no delays
        this.loadVoices();
        this.loadAudioModels();
        this.loadClonedVoices();
    }

    switchTab(targetId) {
        // Remove active from all tabs
        this.tabButtons.forEach(btn => btn.classList.remove('active'));
        this.tabPanels.forEach(panel => panel.classList.remove('active'));

        // Add active to selected tab
        const targetButton = document.querySelector(`[data-target="${targetId}"]`);
        const targetPanel = document.getElementById(targetId);

        if (targetButton && targetPanel) {
            targetButton.classList.add('active');
            targetPanel.classList.add('active');
            this.currentTab = targetId;
        }
    }

    async loadVoices() {
        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 second timeout
            
            const response = await fetch('/api/audio/voices', {
                signal: controller.signal
            });
            clearTimeout(timeoutId);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            if (data.success && Array.isArray(data.voices)) {
                this.availableVoices = data.voices;
                this.updateVoiceSelect();
                console.log(`Loaded ${data.voices.length} voices successfully`);
            } else {
                console.warn('No voices available:', data);
                this.setVoiceSelectError('No voices available');
                window.notificationManager?.warning('No voices available from the server');
            }
        } catch (error) {
            if (error.name === 'AbortError') {
                this.setVoiceSelectError('Voice loading timed out');
                window.notificationManager?.error('Voice loading timed out. Please try again.');
            } else {
                console.error('Error loading voices:', error);
                this.setVoiceSelectError('Error loading voices: ' + error.message);
                window.notificationManager?.error('Failed to load voices: ' + error.message);
            }
        }
    }

    updateVoiceSelect() {
        if (!this.voiceSelect) return;

        this.voiceSelect.innerHTML = '<option value="">Select a voice...</option>';
        
        if (this.availableVoices && Array.isArray(this.availableVoices)) {
            this.availableVoices.forEach(voice => {
                if (voice) {
                    const option = document.createElement('option');
                    option.value = voice.id || voice.name || voice;
                    option.textContent = voice.name || voice.id || voice;
                    this.voiceSelect.appendChild(option);
                }
            });
        }
    }

    setVoiceSelectError(message) {
        if (!this.voiceSelect) return;
        this.voiceSelect.innerHTML = `<option value="">${message}</option>`;
    }

    updateCharCount() {
        if (!this.ttsText || !this.charCount) return;
        this.charCount.textContent = this.ttsText.value.length;
    }

    async generateSpeech() {
        console.log('Generating speech...');
        
        const text = this.ttsText?.value?.trim();
        const voice = this.voiceSelect?.value;
        const speed = parseFloat(this.speedSlider?.value || 1.0);

        // Input validation
        if (!text) {
            window.notificationManager?.error('Please enter text to convert to speech');
            return;
        }
        
        if (text.length > 5000) {
            window.notificationManager?.error('Text is too long. Please keep it under 5000 characters.');
            return;
        }
        
        if (!voice) {
            window.notificationManager?.error('Please select a voice');
            return;
        }
        
        if (speed < 0.5 || speed > 2.0) {
            window.notificationManager?.error('Speed must be between 0.5x and 2.0x');
            return;
        }
        
        // Basic content filtering
        if (this.containsHarmfulContent(text)) {
            window.notificationManager?.error('Text contains potentially inappropriate content. Please revise.');
            return;
        }

        const originalText = this.generateBtn.textContent;
        this.generateBtn.disabled = true;
        this.generateBtn.innerHTML = '<i class="bi bi-hourglass-split"></i> Generating...';
        window.notificationManager?.info('Generating speech...');

        try {
            const response = await fetch('/api/audio/tts', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    text: text,
                    voice: voice,
                    speed: speed
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            // Check if response is audio or JSON
            const contentType = response.headers.get('content-type');
            
            if (contentType && contentType.includes('audio/')) {
                // Handle audio blob response
                const audioBlob = await response.blob();
                const audioUrl = URL.createObjectURL(audioBlob);
                this.currentAudio = audioUrl;
                this.showAudioPreview(audioUrl, voice);
                window.notificationManager?.success('Speech generated successfully!');
                console.log('Speech generation completed:', { voice, textLength: text.length, speed });
            } else {
                // Handle JSON response
                const data = await response.json();
                
                if (data.success && data.audio_url) {
                    this.currentAudio = data.audio_url;
                    this.showAudioPreview(data.audio_url, voice);
                    window.notificationManager?.success('Speech generated successfully!');
                    console.log('Speech generation completed:', { voice, textLength: text.length, speed });
                } else {
                    throw new Error(data.error || 'Failed to generate speech');
                }
            }
        } catch (error) {
            console.error('Error generating speech:', error);
            window.notificationManager?.error('Failed to generate speech: ' + error.message);
        } finally {
            this.generateBtn.disabled = false;
            this.generateBtn.innerHTML = originalText;
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

    showAudioPreview(audioUrl, voice) {
        if (!this.audioPreview || !this.audioPlayer) return;

        this.audioPlayer.src = audioUrl;
        this.usedVoice.textContent = voice;
        this.audioPreview.style.display = 'block';

        // Update audio length when loaded
        window.eventManager.add(this.audioPlayer, 'loadedmetadata', () => {
            const duration = Math.round(this.audioPlayer.duration);
            this.audioLength.textContent = `${duration}s`;
        });
    }

    setupFileUpload(uploadArea, fileInput, handleFunction) {
        if (!uploadArea || !fileInput) return;

        // Click to browse
        window.eventManager.add(uploadArea, 'click', () => {
            fileInput.click();
        });

        // File input change
        window.eventManager.add(fileInput, 'change', (e) => {
            if (e.target.files.length > 0) {
                handleFunction(e.target.files[0]);
            }
        });

        // Drag and drop
        window.eventManager.add(uploadArea, 'dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });

        window.eventManager.add(uploadArea, 'dragleave', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
        });

        window.eventManager.add(uploadArea, 'drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            
            if (e.dataTransfer.files.length > 0) {
                handleFunction(e.dataTransfer.files[0]);
            }
        });
    }

    async handleAudioUpload(file) {
        if (!file.type.startsWith('audio/')) {
            window.notificationManager?.error('Please select an audio file');
            return;
        }

        // Validate file size (max 100MB)
        if (file.size > 100 * 1024 * 1024) {
            window.notificationManager?.error('Audio file is too large. Maximum size is 100MB.');
            return;
        }

        this.transcriptionOutput.textContent = 'Transcribing audio...';
        this.copyTranscription.disabled = true;
        this.downloadTranscription.disabled = true;
        window.notificationManager?.info('Starting transcription...');

        try {
            const formData = new FormData();
            formData.append('audio_file', file);

            const response = await fetch('/api/audio/transcribe', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            
            if (data.success && data.text) {
                this.transcriptionOutput.textContent = data.text;
                this.copyTranscription.disabled = false;
                this.downloadTranscription.disabled = false;
                window.notificationManager?.success('Audio transcribed successfully!');
                console.log('Transcription completed:', { fileName: file.name, textLength: data.text.length });
            } else {
                this.transcriptionOutput.textContent = 'Transcription failed';
                throw new Error(data.error || 'Failed to transcribe audio');
            }
        } catch (error) {
            console.error('Error transcribing audio:', error);
            this.transcriptionOutput.textContent = 'Error occurred during transcription';
            window.notificationManager?.error('Failed to transcribe audio: ' + error.message);
        }
    }

    async handleVoiceUpload(file) {
        if (!file.type.startsWith('audio/')) {
            window.notificationManager?.error('Please select an audio file');
            return;
        }

        // Validate file size (max 50MB for voice cloning)
        if (file.size > 50 * 1024 * 1024) {
            window.notificationManager?.error('Audio file is too large. Maximum size is 50MB for voice cloning.');
            return;
        }

        // Update UI to show file selected
        const uploadContent = this.voiceUploadArea.querySelector('.upload-content p');
        if (uploadContent) {
            uploadContent.textContent = `Selected: ${file.name}`;
        }

        window.notificationManager?.success(`File selected: ${file.name}`);
        this.updateCloneButton();
    }

    updateCloneButton() {
        if (!this.cloneVoiceBtn || !this.voiceName || !this.voiceFileInput) return;

        const hasName = this.voiceName.value.trim().length > 0;
        const hasFile = this.voiceFileInput.files.length > 0;

        this.cloneVoiceBtn.disabled = !hasName || !hasFile;
    }

    async cloneVoice() {
        console.log('Starting voice cloning process...');
        
        if (!this.voiceName || !this.voiceFileInput || !this.cloneVoiceBtn) {
            window.notificationManager?.error('Voice cloning interface not properly initialized');
            return;
        }

        const name = this.voiceName.value.trim();
        const file = this.voiceFileInput.files[0];

        if (!name || !file) {
            window.notificationManager?.error('Please provide both a name and an audio file for voice cloning');
            return;
        }

        // Validate file type and size
        if (!file.type.startsWith('audio/')) {
            window.notificationManager?.error('Please select a valid audio file');
            return;
        }

        if (file.size > 50 * 1024 * 1024) { // 50MB limit
            window.notificationManager?.error('Audio file is too large. Please use a file smaller than 50MB');
            return;
        }

        // Validate name
        if (name.length < 2 || name.length > 50) {
            window.notificationManager?.error('Voice name must be between 2 and 50 characters');
            return;
        }

        const originalText = this.cloneVoiceBtn.textContent;
        this.cloneVoiceBtn.disabled = true;
        this.cloneVoiceBtn.innerHTML = '<i class="bi bi-hourglass-split"></i> Cloning Voice...';
        window.notificationManager?.info('Starting voice cloning process...');

        try {
            const formData = new FormData();
            formData.append('voice_file', file);
            formData.append('voice_name', name);
            formData.append('description', `Cloned voice: ${name}`);

            const response = await fetch('/api/audio/voice_clone', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();

            if (data.success) {
                window.notificationManager?.success(`Voice "${name}" cloned successfully!`);
                console.log('Voice cloning completed:', { name, fileSize: file.size, fileName: file.name });
                
                // Reset form
                this.voiceName.value = '';
                this.voiceFileInput.value = '';
                
                // Update UI to show file cleared
                const uploadContent = this.voiceUploadArea?.querySelector('.upload-content p');
                if (uploadContent) {
                    uploadContent.textContent = 'Click or drag audio file here';
                }
                
                // Refresh voice lists
                await this.loadClonedVoices();
                await this.loadVoices(); // Refresh main voice list to include new cloned voice
            } else {
                throw new Error(data.error || 'Failed to clone voice');
            }
        } catch (error) {
            console.error('Error cloning voice:', error);
            window.notificationManager?.error('Voice cloning failed: ' + error.message);
        } finally {
            this.cloneVoiceBtn.disabled = false;
            this.cloneVoiceBtn.innerHTML = originalText;
            this.updateCloneButton();
        }
    }

    async loadClonedVoices() {
        try {
            const response = await fetch('/api/audio/cloned_voices');
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();

            if (data.success && Array.isArray(data.voices)) {
                this.updateClonedVoicesList(data.voices);
                console.log(`Loaded ${data.voices.length} cloned voices`);
            } else {
                this.updateClonedVoicesList([]);
            }
        } catch (error) {
            console.error('Error loading cloned voices:', error);
            this.updateClonedVoicesList([]);
            window.notificationManager?.warning('Failed to load cloned voices: ' + error.message);
        }
    }

    updateClonedVoicesList(voices) {
        if (!this.clonedVoicesList) return;

        if (voices.length === 0) {
            this.clonedVoicesList.innerHTML = '<p class="no-voices">No cloned voices yet</p>';
            return;
        }

        const voicesHtml = voices.map(voice => `
            <div class="voice-item">
                <div class="voice-info">
                    <h6>${voice.name}</h6>
                    <p class="voice-meta">Created: ${new Date(voice.created).toLocaleDateString()}</p>
                </div>
                <div class="voice-actions">
                    <button class="test-voice-btn" data-voice="${voice.id}">Test</button>
                    <button class="use-voice-btn" data-voice="${voice.id}">Use in TTS</button>
                </div>
                </div>
        `).join('');

        this.clonedVoicesList.innerHTML = voicesHtml;

        // Add event listeners for voice actions
        this.clonedVoicesList.querySelectorAll('.test-voice-btn').forEach(btn => {
            window.eventManager.add(btn, 'click', () => this.testClonedVoice(btn.dataset.voice));
        });

        this.clonedVoicesList.querySelectorAll('.use-voice-btn').forEach(btn => {
            window.eventManager.add(btn, 'click', () => this.useVoiceInTTS(btn.dataset.voice));
        });
    }

    async loadAudioModels() {
        // Load Whisper models
        this.loadWhisperModels();
        
        // Load TTS models
        this.loadTTSModels();
    }

    async loadWhisperModels() {
        if (!this.whisperModels) return;

        try {
            const response = await fetch('/api/audio/models/whisper');
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();

            if (data.success && Array.isArray(data.models)) {
                this.updateModelsList(this.whisperModels, data.models, 'whisper');
                console.log(`Loaded ${data.models.length} Whisper models`);
            } else {
                this.whisperModels.innerHTML = '<div class="loading-indicator">No Whisper models available</div>';
            }
        } catch (error) {
            console.error('Error loading Whisper models:', error);
            this.whisperModels.innerHTML = '<div class="loading-indicator">Error loading Whisper models</div>';
            window.notificationManager?.warning('Failed to load Whisper models: ' + error.message);
        }
    }

    async loadTTSModels() {
        if (!this.ttsModels) return;

        try {
            const response = await fetch('/api/audio/models/tts');
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();

            if (data.success && Array.isArray(data.models)) {
                this.updateModelsList(this.ttsModels, data.models, 'tts');
                console.log(`Loaded ${data.models.length} TTS models`);
            } else {
                this.ttsModels.innerHTML = '<div class="loading-indicator">No TTS models available</div>';
            }
        } catch (error) {
            console.error('Error loading TTS models:', error);
            this.ttsModels.innerHTML = '<div class="loading-indicator">Error loading TTS models</div>';
            window.notificationManager?.warning('Failed to load TTS models: ' + error.message);
        }
    }

    updateModelsList(container, models, type) {
        if (!container) return;

        if (models.length === 0) {
            container.innerHTML = `<div class="loading-indicator">No ${type.toUpperCase()} models found</div>`;
            return;
        }

        const modelsHtml = models.map(model => `
            <div class="model-item">
                <div class="model-info">
                    <h6>${model.name || model}</h6>
                    <p class="model-size">${model.size || 'Unknown size'}</p>
                        </div>
                <div class="model-status">
                    <span class="status-badge ${model.status || 'available'}">${model.status || 'Available'}</span>
                        </div>
                    </div>
        `).join('');

        container.innerHTML = modelsHtml;
    }

    testClonedVoice(voiceId) {
        // Switch to TTS tab and set the voice
        this.switchTab('tts-panel');
        
        // Set a test message
        if (this.ttsText) {
        this.ttsText.value = "Hello! This is a test of the cloned voice. How do I sound?";
            this.updateCharCount();
        }
        
        // Set the voice
        setTimeout(() => {
            if (this.voiceSelect) {
            this.voiceSelect.value = voiceId;
            }
            window.notificationManager?.success('Voice selected for testing. Click Generate Speech to hear it!');
        }, 100);
    }

    useVoiceInTTS(voiceId) {
        // Switch to TTS tab and set the voice
        this.switchTab('tts-panel');
        
        setTimeout(() => {
            if (this.voiceSelect) {
            this.voiceSelect.value = voiceId;
            }
            window.notificationManager?.success('Voice selected for Text-to-Speech');
        }, 100);
    }

    copyTranscriptionText() {
        if (!this.transcriptionOutput) return;

        const text = this.transcriptionOutput.textContent;
        
        if (navigator.clipboard) {
            navigator.clipboard.writeText(text).then(() => {
                window.notificationManager?.success('Transcription copied to clipboard');
            }).catch(err => {
                console.error('Failed to copy:', err);
                window.notificationManager?.warning('Failed to copy to clipboard. Trying fallback method...');
                this.fallbackCopy(text);
            });
        } else {
            this.fallbackCopy(text);
        }
    }

    fallbackCopy(text) {
        const textArea = document.createElement('textarea');
        textArea.value = text;
        document.body.appendChild(textArea);
        textArea.select();
        
        try {
            document.execCommand('copy');
            window.notificationManager?.success('Transcription copied to clipboard');
        } catch (err) {
            console.error('Fallback copy failed:', err);
            window.notificationManager?.error('Failed to copy text. Please try selecting and copying manually.');
        } finally {
            document.body.removeChild(textArea);
        }
    }

    downloadTranscriptionText() {
        if (!this.transcriptionOutput) return;

        const text = this.transcriptionOutput.textContent;
        const blob = new Blob([text], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.href = url;
        a.download = `transcription-${new Date().getTime()}.txt`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        
        window.notificationManager?.success('Transcription downloaded');
    }

    downloadGeneratedAudio() {
        if (!this.audioPlayer || !this.audioPlayer.src) return;

        const a = document.createElement('a');
        a.href = this.audioPlayer.src;
        a.download = `generated-speech-${new Date().getTime()}.wav`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        
        window.notificationManager?.success('Audio downloaded');
    }

    testModels() {
        window.notificationManager?.success('Model testing initiated - check console for results');
        console.log('Testing audio models...');
    }

    openAudioStudio() {
        console.log('[AudioLab] Opening Audio Studio...');
        this.createAudioStudioModal();
    }

    createAudioStudioModal() {
        // Remove existing modal if it exists
        const existingModal = document.getElementById('audio-studio-modal');
        if (existingModal) {
            existingModal.remove();
        }

        const modal = document.createElement('div');
        modal.id = 'audio-studio-modal';
        modal.className = 'modal audio-studio-modal';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h3><i class="bi bi-music-note-beamed"></i> Audio Studio</h3>
                    <button class="close-modal" type="button">&times;</button>
                </div>
                <div class="modal-body">
                    <div class="studio-interface">
                        <div class="studio-controls">
                            <div class="input-section">
                                <h4>Audio Input</h4>
                                <textarea id="studio-text" placeholder="Enter text for advanced audio processing..." rows="4" maxlength="5000"></textarea>
                                <div class="char-counter">
                                    <span id="studio-char-count">0</span>/5000 characters
                                </div>
                            </div>
                            
                            <div class="voice-settings">
                                <h4>Voice & Effects</h4>
                                <div class="settings-grid">
                                    <div class="setting-group">
                                        <label for="studio-voice">Voice:</label>
                                        <select id="studio-voice">
                                            <option value="">Loading voices...</option>
                                        </select>
                                    </div>
                                    <div class="setting-group">
                                        <label for="studio-speed">Speed:</label>
                                        <input type="range" id="studio-speed" min="0.5" max="2.0" step="0.1" value="1.0">
                                        <span id="studio-speed-value">1.0x</span>
                                    </div>
                                    <div class="setting-group">
                                        <label for="studio-pitch">Pitch:</label>
                                        <input type="range" id="studio-pitch" min="-12" max="12" step="1" value="0">
                                        <span id="studio-pitch-value">0</span>
                                    </div>
                                    <div class="setting-group">
                                        <label for="studio-emotion">Emotion:</label>
                                        <select id="studio-emotion">
                                            <option value="neutral">Neutral</option>
                                            <option value="happy">Happy</option>
                                            <option value="sad">Sad</option>
                                            <option value="excited">Excited</option>
                                            <option value="calm">Calm</option>
                                            <option value="angry">Angry</option>
                                        </select>
                                    </div>
                                </div>
                            </div>
                            
                            <div class="audio-effects">
                                <h4>Audio Effects</h4>
                                <div class="effects-grid">
                                    <div class="effect-group">
                                        <label>
                                            <input type="checkbox" id="effect-reverb"> Reverb
                                        </label>
                                        <input type="range" id="reverb-amount" min="0" max="100" value="20" disabled>
                                    </div>
                                    <div class="effect-group">
                                        <label>
                                            <input type="checkbox" id="effect-echo"> Echo
                                        </label>
                                        <input type="range" id="echo-amount" min="0" max="100" value="15" disabled>
                                    </div>
                                    <div class="effect-group">
                                        <label>
                                            <input type="checkbox" id="effect-chorus"> Chorus
                                        </label>
                                        <input type="range" id="chorus-amount" min="0" max="100" value="25" disabled>
                                    </div>
                                    <div class="effect-group">
                                        <label>
                                            <input type="checkbox" id="effect-normalize"> Normalize
                                        </label>
                                    </div>
                                </div>
                            </div>
                            
                            <div class="output-settings">
                                <h4>Output Settings</h4>
                                <div class="settings-grid">
                                    <div class="setting-group">
                                        <label for="studio-format">Format:</label>
                                        <select id="studio-format">
                                            <option value="mp3">MP3</option>
                                            <option value="wav">WAV</option>
                                            <option value="ogg">OGG</option>
                                            <option value="flac">FLAC</option>
                                        </select>
                                    </div>
                                    <div class="setting-group">
                                        <label for="studio-quality">Quality:</label>
                                        <select id="studio-quality">
                                            <option value="low">Low (64 kbps)</option>
                                            <option value="medium" selected>Medium (128 kbps)</option>
                                            <option value="high">High (256 kbps)</option>
                                            <option value="highest">Highest (320 kbps)</option>
                                        </select>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <div class="studio-output">
                            <div class="audio-preview">
                                <h4>Audio Preview</h4>
                                <div id="audio-waveform" class="waveform-container">
                                    <div class="waveform-placeholder">
                                        <i class="bi bi-soundwave"></i>
                                        <p>Audio waveform will appear here</p>
                                    </div>
                                </div>
                                <div class="audio-controls">
                                    <audio id="studio-audio" controls style="width: 100%; display: none;">
                                        Your browser does not support the audio element.
                                    </audio>
                                </div>
                            </div>
                            
                            <div class="processing-status" id="studio-status">
                                <div class="status-indicator">
                                    <i class="bi bi-check-circle text-success"></i>
                                    <span>Ready to process</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button id="process-audio-btn" class="btn btn-primary">
                        <i class="bi bi-play-circle"></i> Process Audio
                    </button>
                    <button id="download-studio-audio" class="btn btn-success" style="display: none;">
                        <i class="bi bi-download"></i> Download
                    </button>
                    <button class="btn btn-secondary close-modal">Close</button>
                </div>
            </div>
        `;

        document.body.appendChild(modal);
        this.setupAudioStudioHandlers(modal);
        this.loadVoicesForStudio();
        window.notificationManager?.success('Audio Studio opened');
    }

    setupAudioStudioHandlers(modal) {
        console.log('[AudioLab] Setting up Audio Studio handlers...');
        
        // Text input character counter
        const studioText = modal.querySelector('#studio-text');
        const charCount = modal.querySelector('#studio-char-count');
        if (studioText && charCount) {
            window.eventManager.add(studioText, 'input', () => {
                const count = studioText.value.length;
                charCount.textContent = count;
                charCount.style.color = count > 4500 ? '#dc3545' : count > 4000 ? '#ffc107' : '#28a745';
            });
        }

        // Speed slider handler
        const speedSlider = modal.querySelector('#studio-speed');
        const speedValue = modal.querySelector('#studio-speed-value');
        if (speedSlider && speedValue) {
            window.eventManager.add(speedSlider, 'input', () => {
                speedValue.textContent = `${speedSlider.value}x`;
            });
        }

        // Pitch slider handler
        const pitchSlider = modal.querySelector('#studio-pitch');
        const pitchValue = modal.querySelector('#studio-pitch-value');
        if (pitchSlider && pitchValue) {
            window.eventManager.add(pitchSlider, 'input', () => {
                const value = parseInt(pitchSlider.value);
                pitchValue.textContent = value > 0 ? `+${value}` : value.toString();
            });
        }

        // Effect checkbox handlers
        const effectCheckboxes = modal.querySelectorAll('[id^="effect-"]');
        effectCheckboxes.forEach(checkbox => {
            window.eventManager.add(checkbox, 'change', () => {
                const effectName = checkbox.id.replace('effect-', '');
                const slider = modal.querySelector(`#${effectName}-amount`);
                if (slider) {
                    slider.disabled = !checkbox.checked;
                }
            });
        });

        // Process audio button
        const processBtn = modal.querySelector('#process-audio-btn');
        if (processBtn) {
            window.eventManager.add(processBtn, 'click', () => {
                this.processAudioInStudio();
            });
        }

        // Download button
        const downloadBtn = modal.querySelector('#download-studio-audio');
        if (downloadBtn) {
            window.eventManager.add(downloadBtn, 'click', () => {
                this.downloadStudioAudio();
            });
        }

        // Close modal handlers
        modal.querySelectorAll('.close-modal').forEach(btn => {
            window.eventManager.add(btn, 'click', () => {
                modal.remove();
            });
        });

        // Close on backdrop click
        window.eventManager.add(modal, 'click', (e) => {
            if (e.target === modal) {
                modal.remove();
            }
        });
    }

    async loadVoicesForStudio() {
        console.log('[AudioLab] Loading voices for Audio Studio...');
        const voiceSelect = document.getElementById('studio-voice');
        if (!voiceSelect) return;

        try {
            const response = await fetch('/api/audio/voices');
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            const voices = data.voices || [];

            voiceSelect.innerHTML = voices.length > 0 
                ? voices.map(voice => `<option value="${voice.id}">${voice.name} (${voice.gender})</option>`).join('')
                : '<option value="">No voices available</option>';

        } catch (error) {
            console.error('Error loading voices for studio:', error);
            voiceSelect.innerHTML = '<option value="">Error loading voices</option>';
        }
    }

    async processAudioInStudio() {
        console.log('[AudioLab] Processing audio in studio...');
        
        const modal = document.getElementById('audio-studio-modal');
        const text = modal.querySelector('#studio-text')?.value?.trim();
        const voice = modal.querySelector('#studio-voice')?.value;
        const speed = parseFloat(modal.querySelector('#studio-speed')?.value || 1.0);
        const pitch = parseInt(modal.querySelector('#studio-pitch')?.value || 0);
        const emotion = modal.querySelector('#studio-emotion')?.value || 'neutral';
        const format = modal.querySelector('#studio-format')?.value || 'mp3';
        const quality = modal.querySelector('#studio-quality')?.value || 'medium';

        // Validation
        if (!text) {
            window.notificationManager?.error('Please enter text to process');
            return;
        }

        if (!voice) {
            window.notificationManager?.error('Please select a voice');
            return;
        }

        // Collect effects
        const effects = {};
        if (modal.querySelector('#effect-reverb')?.checked) {
            effects.reverb = parseInt(modal.querySelector('#reverb-amount')?.value || 20);
        }
        if (modal.querySelector('#effect-echo')?.checked) {
            effects.echo = parseInt(modal.querySelector('#echo-amount')?.value || 15);
        }
        if (modal.querySelector('#effect-chorus')?.checked) {
            effects.chorus = parseInt(modal.querySelector('#chorus-amount')?.value || 25);
        }
        if (modal.querySelector('#effect-normalize')?.checked) {
            effects.normalize = true;
        }

        const processBtn = modal.querySelector('#process-audio-btn');
        const statusIndicator = modal.querySelector('#studio-status');
        const downloadBtn = modal.querySelector('#download-studio-audio');
        
        // Show processing state
        processBtn.disabled = true;
        processBtn.innerHTML = '<i class="bi bi-hourglass-split"></i> Processing...';
        statusIndicator.innerHTML = `
            <div class="status-indicator">
                <i class="bi bi-hourglass-split text-warning"></i>
                <span>Processing audio...</span>
            </div>
        `;
        downloadBtn.style.display = 'none';

        try {
            const requestData = {
                text: text,
                voice: voice,
                speed: speed,
                pitch: pitch,
                emotion: emotion,
                effects: effects,
                output: {
                    format: format,
                    quality: quality
                }
            };

            const response = await fetch('/api/audio/studio/process', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestData)
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            
            if (data.success) {
                console.log('[AudioLab] Audio processing completed successfully');
                
                // Handle audio response
                if (data.audio_url) {
                    this.displayStudioAudio(data.audio_url, modal);
                } else if (data.audio_data) {
                    // Handle base64 audio data
                    const audioBlob = this.base64ToBlob(data.audio_data, `audio/${format}`);
                    const audioUrl = URL.createObjectURL(audioBlob);
                    this.displayStudioAudio(audioUrl, modal);
                    this.currentStudioAudioBlob = audioBlob;
                }
                
                statusIndicator.innerHTML = `
                    <div class="status-indicator">
                        <i class="bi bi-check-circle text-success"></i>
                        <span>Processing complete</span>
                    </div>
                `;
                downloadBtn.style.display = 'inline-block';
                window.notificationManager?.success('Audio processed successfully');
                
            } else {
                throw new Error(data.error || 'Audio processing failed');
            }

        } catch (error) {
            console.error('Error processing audio in studio:', error);
            window.notificationManager?.error(`Audio processing failed: ${error.message}`);
            statusIndicator.innerHTML = `
                <div class="status-indicator">
                    <i class="bi bi-exclamation-triangle text-danger"></i>
                    <span>Processing failed</span>
                </div>
            `;
        } finally {
            processBtn.disabled = false;
            processBtn.innerHTML = '<i class="bi bi-play-circle"></i> Process Audio';
        }
    }

    displayStudioAudio(audioUrl, modal) {
        const audioElement = modal.querySelector('#studio-audio');
        const waveformContainer = modal.querySelector('#audio-waveform');
        
        if (audioElement) {
            audioElement.src = audioUrl;
            audioElement.style.display = 'block';
            audioElement.load();
        }
        
        if (waveformContainer) {
            waveformContainer.innerHTML = `
                <div class="waveform-success">
                    <i class="bi bi-soundwave text-success"></i>
                    <p>Audio ready for playback</p>
                </div>
            `;
        }
    }

    downloadStudioAudio() {
        console.log('[AudioLab] Downloading studio audio...');
        
        if (this.currentStudioAudioBlob) {
            const url = URL.createObjectURL(this.currentStudioAudioBlob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `audio_studio_${Date.now()}.mp3`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            window.notificationManager?.success('Audio download started');
        } else {
            window.notificationManager?.error('No audio available for download');
        }
    }

    base64ToBlob(base64Data, contentType) {
        const byteCharacters = atob(base64Data);
        const byteNumbers = new Array(byteCharacters.length);
        for (let i = 0; i < byteCharacters.length; i++) {
            byteNumbers[i] = byteCharacters.charCodeAt(i);
        }
        const byteArray = new Uint8Array(byteNumbers);
        return new Blob([byteArray], { type: contentType });
    }

    copyTranscriptionToClipboard() {
        if (!this.transcriptionOutput || !this.transcriptionOutput.textContent.trim()) {
            window.notificationManager?.error('No transcription to copy');
            return;
        }

        navigator.clipboard.writeText(this.transcriptionOutput.textContent)
            .then(() => {
                window.notificationManager?.success('Transcription copied to clipboard');
            })
            .catch(() => {
                window.notificationManager?.error('Failed to copy transcription');
            });
    }

    downloadTranscriptionFile() {
        if (!this.transcriptionOutput || !this.transcriptionOutput.textContent.trim()) {
            window.notificationManager?.error('No transcription to download');
            return;
        }

        const text = this.transcriptionOutput.textContent;
        const blob = new Blob([text], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.href = url;
        a.download = `transcription_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.txt`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        
        window.notificationManager?.success('Transcription downloaded');
    }

    async testAudioModels() {
        console.log('Starting comprehensive audio model testing...');
        window.notificationManager?.info('Starting audio model testing...');
        
        const testResults = {
            whisper: { passed: 0, failed: 0, tests: [] },
            tts: { passed: 0, failed: 0, tests: [] },
            total: { passed: 0, failed: 0 }
        };

        try {
            // Test Whisper models
            await this.testWhisperModels(testResults.whisper);
            
            // Test TTS models
            await this.testTTSModels(testResults.tts);
            
            // Calculate totals
            testResults.total.passed = testResults.whisper.passed + testResults.tts.passed;
            testResults.total.failed = testResults.whisper.failed + testResults.tts.failed;
            
            // Show results
            const totalTests = testResults.total.passed + testResults.total.failed;
            const successRate = totalTests > 0 ? Math.round((testResults.total.passed / totalTests) * 100) : 0;
            
            console.log('Audio model testing completed:', testResults);
            
            if (successRate >= 80) {
                window.notificationManager?.success(`Model testing completed! Success rate: ${successRate}% (${testResults.total.passed}/${totalTests} tests passed)`);
            } else if (successRate >= 50) {
                window.notificationManager?.warning(`Model testing completed with warnings. Success rate: ${successRate}% (${testResults.total.passed}/${totalTests} tests passed)`);
            } else {
                window.notificationManager?.error(`Model testing completed with issues. Success rate: ${successRate}% (${testResults.total.passed}/${totalTests} tests passed)`);
            }
            
        } catch (error) {
            console.error('Error during model testing:', error);
            window.notificationManager?.error('Model testing failed. Please check the console for details.');
        }
    }

    async testWhisperModels(results) {
        console.log('Testing Whisper models...');
        
        try {
            const response = await fetch('/api/audio/models/whisper/test', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ test_type: 'basic' })
            });
            
            const data = await response.json();
            
            if (data.success) {
                results.passed++;
                results.tests.push({ name: 'Whisper Basic Test', status: 'passed', details: data.details });
                console.log('✓ Whisper models test passed');
            } else {
                results.failed++;
                results.tests.push({ name: 'Whisper Basic Test', status: 'failed', error: data.error });
                console.error('✗ Whisper models test failed:', data.error);
            }
        } catch (error) {
            results.failed++;
            results.tests.push({ name: 'Whisper Basic Test', status: 'failed', error: error.message });
            console.error('✗ Whisper models test error:', error.message);
        }
    }

    async testTTSModels(results) {
        console.log('Testing TTS models...');
        
        try {
            const response = await fetch('/api/audio/models/tts/test', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    test_type: 'basic',
                    text: 'This is a test of the text-to-speech system.'
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                results.passed++;
                results.tests.push({ name: 'TTS Basic Test', status: 'passed', details: data.details });
                console.log('✓ TTS models test passed');
            } else {
                results.failed++;
                results.tests.push({ name: 'TTS Basic Test', status: 'failed', error: data.error });
                console.error('✗ TTS models test failed:', data.error);
            }
        } catch (error) {
            results.failed++;
            results.tests.push({ name: 'TTS Basic Test', status: 'failed', error: error.message });
            console.error('✗ TTS models test error:', error.message);
        }
    }

    // Notification methods - using centralized NotificationManager
    showSuccess(message) {
        window.notificationManager?.success(message);
    }

    showError(message) {
        window.notificationManager?.error(message);
    }

    showInfo(message) {
        window.notificationManager?.info(message);
    }

    showNotification(message, type = 'info') {
        // Fallback notification system if NotificationManager is not available
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
            console.log(`[${type.toUpperCase()}] ${message}`);
            
            // Create simple fallback notification
            const notification = document.createElement('div');
            notification.className = `notification notification-${type}`;
            notification.textContent = message;
            notification.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                padding: 1rem 1.5rem;
                border-radius: 8px;
                color: white;
                font-weight: 500;
                z-index: 10000;
                animation: slideIn 0.3s ease;
            `;

            if (type === 'success') {
                notification.style.background = '#28a745';
            } else if (type === 'error') {
                notification.style.background = '#dc3545';
            } else if (type === 'warning') {
                notification.style.background = '#ffc107';
                notification.style.color = '#212529';
            } else {
                notification.style.background = '#17a2b8';
            }

            document.body.appendChild(notification);

            setTimeout(() => {
                notification.remove();
            }, 3000);
        }
    }
}

// Initialize when DOM is ready
window.eventManager.add(document, 'DOMContentLoaded', () => {
    window.audioLab = new AudioLab();
});