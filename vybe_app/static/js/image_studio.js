/**
 * Image Studio Manager
 * A modern JavaScript class to handle Stable Diffusion image generation interface
 * Version: 2.0
 */

// Placeholder for bootstrap if not defined globally
if (typeof window.bootstrap === 'undefined') {
    window.bootstrap = {
        Modal: class {
            constructor(element) { 
                this.element = element; 
            }
            show() { 
                console.log('Showing modal for:', this.element); 
                if (this.element) {
                    this.element.style.display = 'block';
                }
            }
            hide() { 
                console.log('Hiding modal for:', this.element); 
                if (this.element) {
                    this.element.style.display = 'none';
                }
            }
        }
    };
}

class ImageStudioManager {
    constructor() {
        console.log('[ImageStudio] Initializing Image Studio Manager...');
        
        // Enhanced state management with error tracking
        this.state = {
            isServiceRunning: false,
            isGenerating: false,
            currentImage: null,
            galleryImages: [],
            isServiceInstalled: false,
            lastError: null,
            errorCount: 0,
            retryCount: 0,
            maxRetries: 3
        };

        // Enhanced cleanup functions for event listeners
        this.cleanupFunctions = [];

        // API endpoints with fallback handling
        this.endpoints = {
            status: '/api/images/status',
            start: '/api/images/start',
            stop: '/api/images/stop',
            generate: '/api/images/generate',
            gallery: '/api/images/gallery',
            models: '/api/images/models'
        };

        // Initialize with comprehensive error handling
        this.initialize().catch(error => {
            console.error('[ImageStudio] Critical initialization error:', error);
            this.showError('Failed to initialize Image Studio. Please refresh the page.');
        });
        
        console.log('[ImageStudio] Constructor completed');
    }
    
    // Enhanced destroy method with comprehensive cleanup
    destroy() {
        console.log('[ImageStudio] Destroying Image Studio Manager...');
        
        try {
            // Remove all event listeners
            this.cleanupFunctions.forEach((cleanup, index) => {
                try {
                    cleanup();
                    console.log(`[ImageStudio] Cleanup function ${index} executed`);
                } catch (error) {
                    console.error(`[ImageStudio] Error during cleanup ${index}:`, error);
                }
            });
            this.cleanupFunctions = [];
            
            // Clear any intervals
            if (this.statusCheckInterval) {
                clearInterval(this.statusCheckInterval);
                this.statusCheckInterval = null;
            }
            
            // Reset state
            this.state = null;
            this.elements = null;
            
            console.log('[ImageStudio] Destroy completed successfully');
            
        } catch (error) {
            console.error('[ImageStudio] Error during destroy:', error);
        }
    }

    // Enhanced initialization with comprehensive error handling and user feedback
    async initialize() {
        console.log('[ImageStudio] Starting initialization...');
        
        try {
            // Step 1: Cache DOM elements
            console.log('[ImageStudio] Caching DOM elements...');
            this.cacheElements();
            
            // Step 2: Attach event listeners
            console.log('[ImageStudio] Attaching event listeners...');
            this.attachEventListeners();
            
            // Step 3: Initialize range inputs
            console.log('[ImageStudio] Initializing range inputs...');
            this.initializeRangeInputs();
            
            // Step 4: Check service status
            console.log('[ImageStudio] Checking service status...');
            await this.checkServiceStatus();
            
            // Step 5: Load gallery
            console.log('[ImageStudio] Loading gallery...');
            await this.loadGallery();
            
            // Step 6: Load models
            console.log('[ImageStudio] Loading models...');
            await this.loadModels();
            
            // Step 7: Start status monitoring
            console.log('[ImageStudio] Starting status monitoring...');
            this.startStatusMonitoring();
            
            console.log('[ImageStudio] Initialization completed successfully');
            this.showSuccess('Image Studio ready');
            
        } catch (error) {
            console.error('[ImageStudio] Initialization failed:', error);
            this.state.lastError = error;
            this.state.errorCount++;
            
            this.showError(`Failed to initialize Image Studio: ${error.message}`);
            
            // Attempt retry if under limit
            if (this.state.retryCount < this.state.maxRetries) {
                this.state.retryCount++;
                console.log(`[ImageStudio] Retrying initialization (${this.state.retryCount}/${this.state.maxRetries})...`);
                
                setTimeout(() => {
                    this.initialize().catch(retryError => {
                        console.error('[ImageStudio] Retry failed:', retryError);
                        this.showError('Image Studio initialization failed after retries. Please refresh the page.');
                    });
                }, 2000 * this.state.retryCount); // Progressive delay
            }
            
            throw error;
        }
    }

    // Enhanced element caching with validation
    cacheElements() {
        console.log('[ImageStudio] Caching DOM elements...');
        
        this.elements = {
            statusIndicator: document.getElementById('statusIndicator'),
            statusDot: document.getElementById('statusDot'),
            statusText: document.getElementById('statusText'),
            statusDetails: document.getElementById('statusDetails'),
            installStatus: document.getElementById('installStatus'),
            serviceStatus: document.getElementById('serviceStatus'),
            modelsCount: document.getElementById('modelsCount'),
            refreshStatusBtn: document.getElementById('refreshStatus'),
            startServiceBtn: document.getElementById('startService'),
            stopServiceBtn: document.getElementById('stopService'),
            generationForm: document.getElementById('generationForm'),
            promptInput: document.getElementById('prompt'),
            negativePromptInput: document.getElementById('negativePrompt'),
            modelSelect: document.getElementById('modelSelect'),
            samplerSelect: document.getElementById('samplerSelect'),
            widthSelect: document.getElementById('width'),
            heightSelect: document.getElementById('height'),
            stepsInput: document.getElementById('steps'),
            cfgScaleInput: document.getElementById('cfgScale'),
            seedInput: document.getElementById('seed'),
            stepsValue: document.getElementById('stepsValue'),
            cfgValue: document.getElementById('cfgValue'),
            generateBtn: document.getElementById('generateBtn'),
            generationProgress: document.getElementById('generationProgress'),
            progressText: document.getElementById('progressText'),
            generationResult: document.getElementById('generationResult'),
            resultImage: document.getElementById('resultImage'),
            generateAnotherBtn: document.getElementById('generateAnother'),
            downloadImage: document.getElementById('downloadImage'),
            addToGallery: document.getElementById('addToGallery'),
            refreshGalleryBtn: document.getElementById('refreshGallery'),
            galleryContent: document.getElementById('galleryContent'),
            imageModal: document.getElementById('imageModal'),
            modalOverlay: document.getElementById('modalOverlay'),
            modalClose: document.getElementById('modalClose'),
            modalImage: document.getElementById('modalImage'),
            modalMetadata: document.getElementById('modalMetadata'),
            modalReuseSettings: document.getElementById('modalReuseSettings'),
            downloadElement: document.getElementById('modalDownload'),
            modalDelete: document.getElementById('modalDelete')
        };
        
        // Validate critical elements
        const criticalElements = ['generateBtn', 'galleryContent'];
        const missingElements = criticalElements.filter(key => !this.elements[key]);
        
        if (missingElements.length > 0) {
            console.warn(`[ImageStudio] Missing critical elements: ${missingElements.join(', ')}`);
        }
        
        console.log(`[ImageStudio] Cached ${Object.keys(this.elements).length} DOM elements`);
    }

    // Enhanced event listener attachment with comprehensive error handling
    attachEventListeners() {
        console.log('[ImageStudio] Attaching event listeners...');
        
        try {
            // Service control buttons with error handling
            if (this.elements.refreshStatusBtn) {
                const handleRefreshStatus = async () => {
                    try {
                        await this.checkServiceStatus();
                        this.showSuccess('Status refreshed');
                    } catch (error) {
                        console.error('[ImageStudio] Error refreshing status:', error);
                        this.showError('Failed to refresh status');
                    }
                };
                
                this.addEventListenerWithCleanup(this.elements.refreshStatusBtn, 'click', handleRefreshStatus);
                console.log('[ImageStudio] Refresh status button listener attached');
            }
            
            if (this.elements.startServiceBtn) {
                const handleStartService = async () => {
                    try {
                        await this.startService();
                    } catch (error) {
                        console.error('[ImageStudio] Error starting service:', error);
                        this.showError('Failed to start service');
                    }
                };
                
                this.addEventListenerWithCleanup(this.elements.startServiceBtn, 'click', handleStartService);
                console.log('[ImageStudio] Start service button listener attached');
            }
            
            if (this.elements.stopServiceBtn) {
                const handleStopService = async () => {
                    try {
                        await this.stopService();
                    } catch (error) {
                        console.error('[ImageStudio] Error stopping service:', error);
                        this.showError('Failed to stop service');
                    }
                };
                
                this.addEventListenerWithCleanup(this.elements.stopServiceBtn, 'click', handleStopService);
                console.log('[ImageStudio] Stop service button listener attached');
            }
            
            // Image generation button with enhanced error handling
            if (this.elements.generateBtn) {
                const handleGenerate = async () => {
                    try {
                        await this.generateImage();
                    } catch (error) {
                        console.error('[ImageStudio] Error generating image:', error);
                        this.showError('Image generation failed');
                    }
                };
                
                this.addEventListenerWithCleanup(this.elements.generateBtn, 'click', handleGenerate);
                console.log('[ImageStudio] Generate button listener attached');
            }
            
            // Generation result buttons
            if (this.elements.generateAnotherBtn) {
                const handleGenerateAnother = () => {
                    try {
                        this.resetToGenerationForm();
                        if (window.notificationManager) {
                            window.notificationManager.showInfo('Ready for new generation');
                        }
                    } catch (error) {
                        console.error('[ImageStudio] Error resetting form:', error);
                        this.showError('Failed to reset form');
                    }
                };
                
                this.addEventListenerWithCleanup(this.elements.generateAnotherBtn, 'click', handleGenerateAnother);
                console.log('[ImageStudio] Generate another button listener attached');
            }
            
            if (this.elements.downloadImage) {
                const handleDownload = async () => {
                    try {
                        await this.downloadCurrentImage();
                        this.showSuccess('Image download started');
                    } catch (error) {
                        console.error('[ImageStudio] Error downloading image:', error);
                        this.showError('Failed to download image');
                    }
                };
                
                this.addEventListenerWithCleanup(this.elements.downloadImage, 'click', handleDownload);
                console.log('[ImageStudio] Download image button listener attached');
            }
            
            if (this.elements.addToGallery) {
                const handleViewInGallery = async () => {
                    try {
                        await this.viewInGallery();
                        if (window.notificationManager) {
                            window.notificationManager.showInfo('Viewing in gallery');
                        }
                    } catch (error) {
                        console.error('[ImageStudio] Error viewing in gallery:', error);
                        this.showError('Failed to view in gallery');
                    }
                };
                
                this.addEventListenerWithCleanup(this.elements.addToGallery, 'click', handleViewInGallery);
                console.log('[ImageStudio] Add to gallery button listener attached');
            }
            
            // Gallery controls
            if (this.elements.refreshGalleryBtn) {
                const handleRefreshGallery = async () => {
                    try {
                        await this.loadGallery();
                        this.showSuccess('Gallery refreshed');
                    } catch (error) {
                        console.error('[ImageStudio] Error refreshing gallery:', error);
                        this.showError('Failed to refresh gallery');
                    }
                };
                
                this.addEventListenerWithCleanup(this.elements.refreshGalleryBtn, 'click', handleRefreshGallery);
                console.log('[ImageStudio] Refresh gallery button listener attached');
            }
            
            // Modal controls
            if (this.elements.modalClose) {
                const handleCloseModal = () => {
                    try {
                        this.closeModal();
                    } catch (error) {
                        console.error('[ImageStudio] Error closing modal:', error);
                        this.showError('Failed to close modal');
                    }
                };
                
                this.addEventListenerWithCleanup(this.elements.modalClose, 'click', handleCloseModal);
                console.log('[ImageStudio] Modal close button listener attached');
            }
            
            if (this.elements.modalOverlay) {
                const handleOverlayClick = (e) => {
                    try {
                        if (e.target === this.elements.modalOverlay) {
                            this.closeModal();
                        }
                    } catch (error) {
                        console.error('[ImageStudio] Error in overlay click:', error);
                        this.showError('Modal overlay error');
                    }
                };
                
                this.addEventListenerWithCleanup(this.elements.modalOverlay, 'click', handleOverlayClick);
                console.log('[ImageStudio] Modal overlay listener attached');
            }
            
            if (this.elements.downloadElement) {
                const handleModalDownload = async () => {
                    try {
                        await this.downloadModalImage();
                        this.showSuccess('Download started');
                    } catch (error) {
                        console.error('[ImageStudio] Error downloading modal image:', error);
                        this.showError('Failed to download image');
                    }
                };
                
                this.addEventListenerWithCleanup(this.elements.downloadElement, 'click', handleModalDownload);
                console.log('[ImageStudio] Modal download button listener attached');
            }
            
            // Enhanced keyboard shortcuts
            this.setupKeyboardShortcuts();
            
            console.log('[ImageStudio] All event listeners attached successfully');
            
        } catch (error) {
            console.error('[ImageStudio] Error attaching event listeners:', error);
            throw error;
        }
    }

    // Helper method to add event listeners with automatic cleanup
    addEventListenerWithCleanup(element, event, handler) {
        if (!element) {
            console.warn(`[ImageStudio] Cannot add ${event} listener to null element`);
            return;
        }
        
        // Use eventManager if available, otherwise fallback to direct listener
        if (window.eventManager && window.eventManager.add) {
            window.eventManager.add(element, event, handler);
            
            // Add cleanup function
            this.cleanupFunctions.push(() => {
                if (window.eventManager && window.eventManager.remove) {
                    window.eventManager.remove(element, event, handler);
                }
            });
        } else {
            element.addEventListener(event, handler);
            
            // Add cleanup function
            this.cleanupFunctions.push(() => {
                element.removeEventListener(event, handler);
            });
        }
    }

    // Enhanced keyboard shortcuts setup
    setupKeyboardShortcuts() {
        console.log('[ImageStudio] Setting up keyboard shortcuts...');
        
        const handleKeydown = (e) => {
            try {
                // Ctrl/Cmd + Enter: Generate image
                if ((e.ctrlKey || e.metaKey) && e.key === 'Enter' && !this.state.isGenerating) {
                    e.preventDefault();
                    this.generateImage().catch(error => {
                        console.error('[ImageStudio] Keyboard generate error:', error);
                        this.showError('Keyboard shortcut failed');
                    });
                }
                
                // Escape: Close modal
                if (e.key === 'Escape') {
                    e.preventDefault();
                    this.closeModal();
                }
                
                // Ctrl/Cmd + S: Save current image
                if ((e.ctrlKey || e.metaKey) && e.key === 's' && this.state.currentImage) {
                    e.preventDefault();
                    this.downloadCurrentImage().catch(error => {
                        console.error('[ImageStudio] Keyboard save error:', error);
                        this.showError('Save shortcut failed');
                    });
                }
                
            } catch (error) {
                console.error('[ImageStudio] Keyboard shortcut error:', error);
                this.showError('Keyboard shortcut error');
            }
        };
        
        this.addEventListenerWithCleanup(document, 'keydown', handleKeydown);
        console.log('[ImageStudio] Keyboard shortcuts enabled');
    }

    initializeRangeInputs() {
        if (this.elements.stepsInput && this.elements.stepsValue) {
            window.eventManager.add(this.elements.stepsInput, 'input', window.eventManager.debounce((e) => {
                this.elements.stepsValue.textContent = e.target.value;
            }, 100));
        }
        
        if (this.elements.cfgScaleInput && this.elements.cfgValue) {
            window.eventManager.add(this.elements.cfgScaleInput, 'input', window.eventManager.debounce((e) => {
                this.elements.cfgValue.textContent = parseFloat(e.target.value).toFixed(1);
            }, 100));
        }
    }

    async checkServiceStatus() {
        try {
            this.updateStatusDisplay('loading', 'Checking service status...');
            
            const response = await fetch(this.endpoints.status);
            const data = await response.json();
            
            if (data.success) {
                const status = data.status;
                this.state.isServiceRunning = status.running;
                this.state.isServiceInstalled = status.installed;
                
                this.updateServiceStatus(status);
                this.updateServiceControls();
                this.updateGenerationFormState();
            } else {
                throw new Error(data.error || 'Failed to check service status');
            }
        } catch (error) {
            console.error('Error checking service status:', error);
            this.updateStatusDisplay('stopped', 'Error checking service status');
            this.showError('Failed to check service status. Please check your connection and try again.');
        }
    }

    updateServiceStatus(status) {
        if (status.running) {
            this.updateStatusDisplay('running', 'Service is running');
        } else if (status.installed) {
            this.updateStatusDisplay('stopped', 'Service is stopped');
        } else {
            this.updateStatusDisplay('stopped', 'Service not installed');
        }
        
        if (this.elements.statusDetails) {
            this.elements.statusDetails.style.display = 'block';
            
            if (this.elements.installStatus) {
                this.elements.installStatus.textContent = status.installed ? 'Installed' : 'Not Installed';
            }
            
            if (this.elements.serviceStatus) {
                this.elements.serviceStatus.textContent = status.running ? 'Running' : 'Stopped';
            }
            
            if (this.elements.modelsCount) {
                const count = status.models_available ? status.models_available.length : 0;
                this.elements.modelsCount.textContent = count.toString();
            }
        }
    }

    updateStatusDisplay(state, message) {
        if (!this.elements.statusDot || !this.elements.statusText) return;
        
        this.elements.statusDot.className = 'status-dot';
        this.elements.statusDot.classList.add(state);
        this.elements.statusText.textContent = message;
    }

    updateServiceControls() {
        if (this.elements.startServiceBtn) {
            this.elements.startServiceBtn.style.display = 
                (!this.state.isServiceRunning && this.state.isServiceInstalled) ? 'inline-flex' : 'none';
        }
        
        if (this.elements.stopServiceBtn) {
            this.elements.stopServiceBtn.style.display = 
                this.state.isServiceRunning ? 'inline-flex' : 'none';
        }
    }

    updateGenerationFormState() {
        const isEnabled = this.state.isServiceRunning && !this.state.isGenerating;
        
        if (this.elements.generateBtn) {
            this.elements.generateBtn.disabled = !isEnabled;
            
            if (!this.state.isServiceRunning) {
                this.elements.generateBtn.textContent = this.state.isServiceInstalled 
                    ? 'Start Service First' 
                    : 'Service Not Installed';
            } else if (this.state.isGenerating) {
                this.elements.generateBtn.textContent = 'Generating...';
            } else {
                this.elements.generateBtn.innerHTML = '<span class="btn-icon">✨</span> Generate Image';
            }
        }
        
        const formInputs = [
            this.elements.promptInput,
            this.elements.negativePromptInput,
            this.elements.modelSelect,
            this.elements.samplerSelect,
            this.elements.widthSelect,
            this.elements.heightSelect,
            this.elements.stepsInput,
            this.elements.cfgScaleInput,
            this.elements.seedInput
        ];
        
        formInputs.forEach(input => {
            if (input) {
                input.disabled = !isEnabled;
            }
        });
    }

    async startService() {
        try {
            this.updateStatusDisplay('loading', 'Starting service...');

            // Guard against repeated clicks
            if (this.elements.startServiceBtn) {
                this.elements.startServiceBtn.disabled = true;
                this.elements.startServiceBtn.innerHTML = '<span class="spinner"></span> Starting...';
            }

            const response = await fetch(this.endpoints.start, { method: 'POST' });
            const data = await response.json();

            if (!data.success) {
                throw new Error(data.error || 'Failed to start service');
            }

            // Poll for readiness with backoff
            await this.waitForServiceReady();
            this.state.isServiceRunning = true;
            this.updateStatusDisplay('running', 'Service is running');
            this.updateServiceControls();
            this.updateGenerationFormState();
            await this.loadModels();
            this.showSuccess('Service started successfully');
        } catch (error) {
            console.error('Error starting service:', error);
            this.updateStatusDisplay('stopped', 'Failed to start service');
            const hint = error.message && error.message.includes('disabled') ? ' Enable auto-launch in Settings → Startup Preferences.' : '';
            this.showError('Failed to start service: ' + error.message + hint);
        }
        finally {
            if (this.elements.startServiceBtn) {
                this.elements.startServiceBtn.disabled = false;
                this.elements.startServiceBtn.innerHTML = '<span class="btn-icon">▶️</span> Start Service';
            }
        }
    }

    async waitForServiceReady() {
        const start = Date.now();
        let delay = 1500;
        const hardCapMs = 180000; // 3 minutes
        while (Date.now() - start < hardCapMs) {
            try {
                const res = await fetch(this.endpoints.status);
                const j = await res.json();
                if (j && j.success && j.status && j.status.running) return true;
            } catch {
                // Continue trying on network errors
            }
            const elapsedSec = Math.floor((Date.now() - start) / 1000);
            this.updateStatusDisplay('loading', `Starting service... (${elapsedSec}s)`);
            await new Promise(r => setTimeout(r, delay));
            delay = Math.min(5000, Math.floor(delay * 1.4));
        }
        throw new Error('Service did not become ready in time');
    }

    async stopService() {
        try {
            this.updateStatusDisplay('loading', 'Stopping service...');
            if (this.elements.stopServiceBtn) {
                this.elements.stopServiceBtn.disabled = true;
                this.elements.stopServiceBtn.innerHTML = '<span class="spinner"></span> Stopping...';
            }
            
            const response = await fetch(this.endpoints.stop, { method: 'POST' });
            const data = await response.json();
            
            if (data.success) {
                this.state.isServiceRunning = false;
                this.updateStatusDisplay('stopped', 'Service stopped');
                this.updateServiceControls();
                this.updateGenerationFormState();
                this.showSuccess('Service stopped successfully');
            } else {
                throw new Error(data.error || 'Failed to stop service');
            }
        } catch (error) {
            console.error('Error stopping service:', error);
            this.showError('Failed to stop service. Please check your connection and try again.');
        } finally {
            if (this.elements.stopServiceBtn) {
                this.elements.stopServiceBtn.disabled = false;
                this.elements.stopServiceBtn.innerHTML = '<span class="btn-icon">⏹️</span> Stop Service';
            }
        }
    }

    async loadModels() {
        if (!this.elements.modelSelect || !this.state.isServiceRunning) return;
        
        try {
            const response = await fetch(this.endpoints.models);
            const data = await response.json();
            
            if (data.success && data.models) {
                this.populateModelSelect(data.models);
            } else {
                this.elements.modelSelect.innerHTML = '<option value="">No models available</option>';
            }
        } catch (error) {
            console.error('Error loading models:', error);
            this.elements.modelSelect.innerHTML = '<option value="">Error loading models</option>';
            this.showError('Failed to load models. Please check your connection and try again.');
        }
    }

    populateModelSelect(models) {
        if (!this.elements.modelSelect) return;
        
        this.elements.modelSelect.innerHTML = '';
        
        if (models.length === 0) {
            this.elements.modelSelect.innerHTML = '<option value="">No models found</option>';
            return;
        }
        
        models.forEach(model => {
            const option = document.createElement('option');
            option.value = model.name || model.title || model;
            option.textContent = model.name || model.title || model;
            this.elements.modelSelect.appendChild(option);
        });
        
        this.elements.modelSelect.selectedIndex = 0;
    }

    validateForm() {
        const prompt = this.elements.promptInput ? this.elements.promptInput.value.trim() : '';
        const isValid = prompt && prompt.length > 0 && this.state.isServiceRunning;
        
        if (this.elements.generateBtn) {
            this.elements.generateBtn.disabled = !isValid || this.state.isGenerating;
        }
        
        return isValid;
    }

    async generateImage() {
        if (!this.validateForm()) {
            this.showError('Please enter a prompt and ensure the service is running.');
            return;
        }
        
        try {
            this.state.isGenerating = true;
            this.showGenerationProgress();
            this.updateGenerationFormState();
            
            const params = this.getGenerationParameters();
            
            const response = await fetch(this.endpoints.generate, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(params)
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.handleGenerationSuccess(data);
            } else {
                throw new Error(data.error || 'Generation failed');
            }
        } catch (error) {
            console.error('Error generating image:', error);
            this.handleGenerationError('Failed to generate image. Please check your connection and try again.');
        } finally {
            this.state.isGenerating = false;
            this.updateGenerationFormState();
        }
    }

    getGenerationParameters() {
        return {
            prompt: this.elements.promptInput ? this.elements.promptInput.value.trim() : '',
            negative_prompt: this.elements.negativePromptInput ? this.elements.negativePromptInput.value.trim() : '',
            model: this.elements.modelSelect ? this.elements.modelSelect.value : '',
            sampler: this.elements.samplerSelect ? this.elements.samplerSelect.value : 'Euler a',
            width: this.elements.widthSelect ? parseInt(this.elements.widthSelect.value) : 512,
            height: this.elements.heightSelect ? parseInt(this.elements.heightSelect.value) : 512,
            steps: this.elements.stepsInput ? parseInt(this.elements.stepsInput.value) : 20,
            cfg_scale: this.elements.cfgScaleInput ? parseFloat(this.elements.cfgScaleInput.value) : 7.0,
            seed: this.elements.seedInput ? parseInt(this.elements.seedInput.value) : -1
        };
    }

    showGenerationProgress() {
        if (this.elements.generationForm) {
            this.elements.generationForm.style.display = 'none';
        }
        
        if (this.elements.generationResult) {
            this.elements.generationResult.style.display = 'none';
        }
        
        if (this.elements.generationProgress) {
            this.elements.generationProgress.style.display = 'block';
        }
        
        if (this.elements.progressText) {
            this.elements.progressText.textContent = 'Preparing generation...';
        }
    }

    handleGenerationSuccess(data) {
        this.state.currentImage = data;
        
        if (this.elements.generationProgress) {
            this.elements.generationProgress.style.display = 'none';
        }
        
        if (this.elements.generationResult) {
            this.elements.generationResult.style.display = 'block';
        }
        
        if (this.elements.resultImage && data.image_url) {
            this.elements.resultImage.src = data.image_url;
            this.elements.resultImage.alt = 'Generated image';
        }
        
        this.loadGallery();
        this.showSuccess('Image generated successfully!');
    }

    handleGenerationError(errorMessage) {
        if (this.elements.generationProgress) {
            this.elements.generationProgress.style.display = 'none';
        }
        
        if (this.elements.generationForm) {
            this.elements.generationForm.style.display = 'block';
        }
        
        this.showError('Failed to generate image: ' + errorMessage);
    }

    resetToGenerationForm() {
        if (this.elements.generationResult) {
            this.elements.generationResult.style.display = 'none';
        }
        
        if (this.elements.generationProgress) {
            this.elements.generationProgress.style.display = 'none';
        }
        
        if (this.elements.generationForm) {
            this.elements.generationForm.style.display = 'block';
        }
    }

    downloadCurrentImage() {
        if (!this.state.currentImage || !this.state.currentImage.image_url) {
            this.showError('No image to download');
            return;
        }
        
        this.downloadImage(this.state.currentImage.image_url, 'generated-image.png');
    }

    viewInGallery() {
        this.loadGallery();
        if (this.elements.galleryContent) {
            this.elements.galleryContent.scrollIntoView({ behavior: 'smooth' });
        }
    }

    async loadGallery() {
        if (!this.elements.galleryContent) return;
        
        try {
            this.elements.galleryContent.innerHTML = `
                <div class="gallery-loading">
                    <div class="spinner"></div>
                    <p>Loading gallery...</p>
                </div>
            `;
            
            const response = await fetch(this.endpoints.gallery);
            const data = await response.json();
            
            if (data.success) {
                this.state.galleryImages = data.images || [];
                this.renderGallery(this.state.galleryImages);
            } else {
                throw new Error(data.error || 'Failed to load gallery');
            }
        } catch (error) {
            console.error('Error loading gallery:', error);
            this.elements.galleryContent.innerHTML = `
                <div class="gallery-loading">
                    <p>Error loading gallery</p>
                    <button class="btn btn-secondary btn-sm" onclick="imageStudio.loadGallery()">
                        <span class="btn-icon">��</span>
                        Try Again
                    </button>
                </div>
            `;
            this.showError('Failed to load gallery. Please check your connection and try again.');
        }
    }

    renderGallery(images) {
        if (!this.elements.galleryContent) return;
        
        if (images.length === 0) {
            this.elements.galleryContent.innerHTML = `
                <div class="gallery-loading">
                    <p>No images in gallery yet</p>
                    <p>Generate your first image to get started!</p>
                </div>
            `;
            return;
        }
        
        const galleryGrid = document.createElement('div');
        galleryGrid.className = 'gallery-grid';
        
        images.forEach((image, index) => {
            const galleryItem = this.createGalleryItem(image, index);
            galleryGrid.appendChild(galleryItem);
        });
        
        this.elements.galleryContent.innerHTML = '';
        this.elements.galleryContent.appendChild(galleryGrid);
    }

    createGalleryItem(image, index) {
        const item = document.createElement('div');
        item.className = 'gallery-item';
        window.eventManager.add(item, 'click', () => this.openImageModal(image, index));
        
        // Store generation metadata as data attributes
        if (image.prompt) item.dataset.prompt = image.prompt;
        if (image.negative_prompt) item.dataset.negativePrompt = image.negative_prompt;
        if (image.model) item.dataset.model = image.model;
        if (image.sampler) item.dataset.sampler = image.sampler;
        if (image.width) item.dataset.width = image.width;
        if (image.height) item.dataset.height = image.height;
        if (image.steps) item.dataset.steps = image.steps;
        if (image.cfg_scale) item.dataset.cfgScale = image.cfg_scale;
        if (image.seed) item.dataset.seed = image.seed;
        
        const img = document.createElement('img');
        img.src = image.thumbnail_url || image.image_url || image.url;
        img.alt = `Gallery image ${index + 1}`;
        img.loading = 'lazy';
        
        const overlay = document.createElement('div');
        overlay.className = 'gallery-item-overlay';
        
        const info = document.createElement('div');
        info.className = 'gallery-item-info';
        info.textContent = image.filename || `Image ${index + 1}`;
        
        overlay.appendChild(info);
        item.appendChild(img);
        item.appendChild(overlay);
        
        return item;
    }

    openImageModal(image, index) {
        if (!this.elements.imageModal) return;
        
        this.state.currentModalImage = { ...image, index };
        
        if (this.elements.modalImage) {
            this.elements.modalImage.src = image.image_url || image.url;
            this.elements.modalImage.alt = image.filename || `Gallery image ${index + 1}`;
        }
        
        this.populateModalMetadata(image);
        this.elements.imageModal.style.display = 'flex';
    }

    populateModalMetadata(image) {
        if (!this.elements.modalMetadata) return;
        
        const metadata = [
            { label: 'Filename', value: image.filename || 'Unknown' },
            { label: 'Prompt', value: image.prompt || 'Not available' },
            { label: 'Negative Prompt', value: image.negative_prompt || 'None' },
            { label: 'Model', value: image.model || 'Unknown' },
            { label: 'Sampler', value: image.sampler || 'Unknown' },
            { label: 'Size', value: (image.width && image.height) ? `${image.width}×${image.height}` : 'Unknown' },
            { label: 'Steps', value: image.steps || 'Unknown' },
            { label: 'CFG Scale', value: image.cfg_scale || 'Unknown' },
            { label: 'Seed', value: image.seed || 'Unknown' }
        ];
        
        this.elements.modalMetadata.innerHTML = '';
        
        metadata.forEach(item => {
            const metadataItem = document.createElement('div');
            metadataItem.className = 'metadata-item';
            
            const label = document.createElement('div');
            label.className = 'metadata-label';
            label.textContent = item.label;
            
            const value = document.createElement('div');
            value.className = 'metadata-value';
            value.textContent = item.value;
            
            metadataItem.appendChild(label);
            metadataItem.appendChild(value);
            this.elements.modalMetadata.appendChild(metadataItem);
        });
    }

    closeModal() {
        if (this.elements.imageModal) {
            this.elements.imageModal.style.display = 'none';
        }
        this.state.currentModalImage = null;
    }

    reuseImageSettings() {
        if (!this.state.currentModalImage) {
            this.showError('No image settings to reuse');
            return;
        }

        const image = this.state.currentModalImage;
        
        try {
            // Populate form fields with image settings
            if (image.prompt && this.elements.promptInput) {
                this.elements.promptInput.value = image.prompt;
            }
            
            if (image.negative_prompt && this.elements.negativePromptInput) {
                this.elements.negativePromptInput.value = image.negative_prompt;
            }
            
            if (image.model && this.elements.modelSelect) {
                // Check if the model option exists in the select
                const modelOption = Array.from(this.elements.modelSelect.options).find(option => option.value === image.model);
                if (modelOption) {
                    this.elements.modelSelect.value = image.model;
                }
            }
            
            if (image.sampler && this.elements.samplerSelect) {
                // Check if the sampler option exists in the select
                const samplerOption = Array.from(this.elements.samplerSelect.options).find(option => option.value === image.sampler);
                if (samplerOption) {
                    this.elements.samplerSelect.value = image.sampler;
                }
            }
            
            if (image.width && this.elements.widthSelect) {
                this.elements.widthSelect.value = image.width.toString();
            }
            
            if (image.height && this.elements.heightSelect) {
                this.elements.heightSelect.value = image.height.toString();
            }
            
            if (image.steps && this.elements.stepsInput) {
                this.elements.stepsInput.value = image.steps.toString();
                if (this.elements.stepsValue) {
                    this.elements.stepsValue.textContent = image.steps;
                }
            }
            
            if (image.cfg_scale && this.elements.cfgScaleInput) {
                this.elements.cfgScaleInput.value = image.cfg_scale.toString();
                if (this.elements.cfgValue) {
                    this.elements.cfgValue.textContent = image.cfg_scale;
                }
            }
            
            if (image.seed && this.elements.seedInput) {
                this.elements.seedInput.value = image.seed.toString();
            }
            
            // Close the modal and scroll to generation form
            this.closeModal();
            
            // Scroll to the generation form for better UX
            if (this.elements.generationForm) {
                this.elements.generationForm.scrollIntoView({ 
                    behavior: 'smooth', 
                    block: 'start' 
                });
            }
            
            // Show success message
            this.showSuccess('Settings applied! You can now modify and generate a new image.');
            
        } catch (error) {
            console.error('Error reusing image settings:', error);
            this.showError('Failed to apply image settings. Please check your connection and try again.');
        }
    }

    downloadModalImage() {
        if (!this.state.currentModalImage) {
            this.showError('No image to download');
            return;
        }
        
        const image = this.state.currentModalImage;
        const filename = image.filename || `image-${Date.now()}.png`;
        this.downloadImage(image.image_url || image.url, filename);
    }

    async deleteModalImage() {
        if (!this.state.currentModalImage) {
            this.showError('No image to delete');
            return;
        }
        
        if (!confirm('Are you sure you want to delete this image?')) {
            return;
        }
        
        try {
            const image = this.state.currentModalImage;
            const response = await fetch(`/api/images/delete/${image.id || image.filename}`, {
                method: 'DELETE'
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showSuccess('Image deleted successfully');
                this.closeModal();
                this.loadGallery();
            } else {
                throw new Error(data.error || 'Failed to delete image');
            }
        } catch (error) {
            console.error('Error deleting image:', error);
            this.showError('Failed to delete image. Please check your connection and try again.');
        }
    }

    downloadImage(url, filename) {
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }



    showSuccess(message) {
        console.log('[ImageStudio Success]:', message);
        if (window.notificationManager) {
            window.notificationManager.showSuccess(message);
        } else {
            console.log('[ImageStudio] NotificationManager not available, using fallback');
        }
    }

    showError(message) {
        console.error('[ImageStudio Error]:', message);
        this.state.lastError = message;
        this.state.errorCount++;
        
        // Show error notification
        if (window.notificationManager) {
            window.notificationManager.showError(message);
        } else {
            console.error('[ImageStudio] NotificationManager not available, using fallback');
        }
        
        // For critical errors, also use alert as fallback
        if (this.state.errorCount > 3) {
            setTimeout(() => {
                if (confirm(`Multiple errors detected in Image Studio. Would you like to refresh the page?\n\nLatest error: ${message}`)) {
                    window.location.reload();
                }
            }, 1000);
        }
    }



    // Enhanced status monitoring
    startStatusMonitoring() {
        console.log('[ImageStudio] Starting status monitoring...');
        
        if (this.statusCheckInterval) {
            clearInterval(this.statusCheckInterval);
        }
        
        // Check status every 30 seconds
        this.statusCheckInterval = setInterval(async () => {
            try {
                await this.checkServiceStatus();
            } catch (error) {
                console.warn('[ImageStudio] Status check failed:', error);
                // Don't show error notifications for automatic status checks
                // to avoid spamming the user
            }
        }, 30000);
        
        console.log('[ImageStudio] Status monitoring started');
    }
}

window.eventManager.add(document, 'DOMContentLoaded', () => {
    try {
        window.imageStudio = new ImageStudioManager();
    } catch (error) {
        console.error('Failed to initialize Image Studio:', error);
        alert('Failed to initialize Image Studio. Please refresh the page and try again.');
    }
});
