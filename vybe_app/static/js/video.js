/* global bootstrap */
// Import the centralized notification manager (attaches to window.notificationManager)
import './services/NotificationManager.js';

// Safety check for Bootstrap
if (typeof bootstrap === 'undefined') {
    console.warn('Bootstrap is not defined. Using placeholder for modals.');
    window.bootstrap = {
        Modal: class {
            constructor(element) { this.element = element; console.log('Placeholder Modal created for:', this.element); }
            show() { console.log('Placeholder Modal show().'); }
            hide() { console.log('Placeholder Modal hide().'); }
        }
    };
}

// Video Portal JavaScript

class VideoPortal {
    constructor() {
        // Cleanup functions for event listeners
        this.cleanupFunctions = [];
        
        this.init();
        this.checkServiceStatus();
        this.setupEventListeners();
        this.loadVideoGallery();
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
        this.serviceRunning = false;
        this.serviceInstalled = false;
        this.generationInProgress = false;
        this._pollDelay = 2000;
        this._pollInterval = null;
        this._installationPollInterval = null;
        
        // Toast instance - using global bootstrap
        this.toast = new bootstrap.Toast(document.getElementById('generation-toast'));
        
        // Cleanup on page unload
        const cleanupHandler = () => {
            this.cleanup();
        };
        window.addEventListener('beforeunload', cleanupHandler);
        this.cleanupFunctions.push(() => window.removeEventListener('beforeunload', cleanupHandler));
    }
    
    cleanup() {
        if (this._pollInterval) {
            clearInterval(this._pollInterval);
            this._pollInterval = null;
        }
        if (this._installationPollInterval) {
            clearInterval(this._installationPollInterval);
            this._installationPollInterval = null;
        }
    }

    setupEventListeners() {
        // Service control buttons
        document.getElementById('video-service-toggle').addEventListener('click', () => {
            this.toggleVideoService();
        });

        document.getElementById('install-service').addEventListener('click', () => {
            this.installVideoService();
        });

        // Video generation form
        document.getElementById('video-generation-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.generateVideo();
        });

        // Example prompts
        document.getElementById('example-prompts-btn').addEventListener('click', () => {
            this.toggleExamplePrompts();
        });

        document.querySelectorAll('.example-prompt').forEach(btn => {
            const clickHandler = () => {
                this.useExamplePrompt(btn.textContent);
            };
            btn.addEventListener('click', clickHandler);
            this.cleanupFunctions.push(() => btn.removeEventListener('click', clickHandler));
        });

        // Gallery refresh
        document.getElementById('refresh-gallery').addEventListener('click', () => {
            this.loadVideoGallery();
        });

        // Batch generation controls
        const addBatchPromptBtn = document.getElementById('add-batch-prompt');
        if (addBatchPromptBtn) {
            addBatchPromptBtn.addEventListener('click', () => {
                this.addBatchPrompt();
            });
        }

        const batchGenerateBtn = document.getElementById('batch-generate');
        if (batchGenerateBtn) {
            batchGenerateBtn.addEventListener('click', () => {
                this.startBatchGeneration();
            });
        }

        // Custom tab switching
        this.setupCustomTabs();
    }
    
    setupCustomTabs() {
        // Handle custom tab switching
        const tabButtons = document.querySelectorAll('.custom-tab-btn');
        tabButtons.forEach(button => {
            const clickHandler = () => {
                this.switchTab(button);
            };
            button.addEventListener('click', clickHandler);
            this.cleanupFunctions.push(() => button.removeEventListener('click', clickHandler));
        });
    }
    
    switchTab(clickedButton) {
        // Remove active class from all tabs and panels
        document.querySelectorAll('.custom-tab-btn').forEach(tab => tab.classList.remove('active'));
        document.querySelectorAll('.tab-pane').forEach(panel => {
            panel.classList.remove('show', 'active');
        });
        
        // Add active class to clicked tab
        clickedButton.classList.add('active');
        
        // Show corresponding panel
        const targetPanel = document.querySelector(clickedButton.dataset.target);
        if (targetPanel) {
            targetPanel.classList.add('show', 'active');
            
            // Load content based on tab
            if (targetPanel.id === 'gallery-panel') {
                this.loadVideoGallery();
            } else if (targetPanel.id === 'queue-panel') {
                this.loadJobQueue();
            }
        }
    }

    async checkServiceStatus() {
        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 second timeout
            
            const response = await fetch('/api/video/status', {
                signal: controller.signal
            });
            clearTimeout(timeoutId);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            if (data.success) {
                this.updateServiceStatus(data.status);
                // Subtle guidance and backoff polling
                if (!data.status.installed) {
                    window.notificationManager?.showInfo('Video service not installed. Click Install to begin.');
                } else if (!data.status.running) {
                    // Exponential backoff up to 30s with inline hint
                    const hint = document.getElementById('setup-info');
                    if (hint) { hint.style.display = 'block'; }
                    
                    // Use setTimeout instead of recursive calls to prevent stack overflow
                    if (this._pollInterval) {
                        clearTimeout(this._pollInterval);
                    }
                    this._pollInterval = setTimeout(() => this.checkServiceStatus(), this._pollDelay);
                    this._pollDelay = Math.min(30000, Math.floor(this._pollDelay * 1.6));
                } else {
                    this._pollDelay = 2000;
                    if (this._pollInterval) {
                        clearTimeout(this._pollInterval);
                        this._pollInterval = null;
                    }
                }
            } else {
                window.notificationManager?.showError('Failed to check service status: ' + (data.error || 'Unknown error'));
            }
        } catch (error) {
            if (error.name === 'AbortError') {
                window.notificationManager?.showError('Service status check timed out');
            } else {
                console.error('Error checking service status:', error);
                window.notificationManager?.showError('Error checking service status: ' + error.message);
            }
        }
    }

    updateServiceStatus(status) {
        const statusBadge = document.getElementById('video-status');
        const modelsBadge = document.getElementById('models-status');
        const toggleBtn = document.getElementById('video-service-toggle');
        const installBtn = document.getElementById('install-service');
        const setupInfo = document.getElementById('setup-info');

        this.serviceRunning = status.running;
        this.serviceInstalled = status.installed;

        // Update status badge
        if (status.running) {
            statusBadge.className = 'badge bg-success';
            statusBadge.textContent = 'Running';
        } else if (status.installed) {
            statusBadge.className = 'badge bg-warning';
            statusBadge.textContent = 'Stopped';
        } else {
            statusBadge.className = 'badge bg-danger';
            statusBadge.textContent = 'Not Installed';
        }

        // Update models badge
        modelsBadge.textContent = `Models: ${status.models_available || 'Unknown'}`;

        // Update toggle button
        toggleBtn.disabled = false;
        toggleBtn.innerHTML = '';
        
        if (status.installed) {
            if (status.running) {
                toggleBtn.className = 'btn btn-outline-danger btn-sm';
                toggleBtn.innerHTML = '<i class="bi bi-stop-circle"></i> Stop Service';
            } else {
                toggleBtn.className = 'btn btn-outline-success btn-sm';
                toggleBtn.innerHTML = '<i class="bi bi-play-circle"></i> Start Service';
            }
            installBtn.style.display = 'none';
            setupInfo.style.display = 'none';
        } else {
            toggleBtn.style.display = 'none';
            installBtn.style.display = 'inline-block';
            setupInfo.style.display = 'block';
        }
    }

    async toggleVideoService() {
        const toggleBtn = document.getElementById('video-service-toggle');
        const originalContent = toggleBtn.innerHTML;
        
        try {
            toggleBtn.disabled = true;
            toggleBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>' + (this.serviceRunning ? 'Stopping...' : 'Starting...');

            const endpoint = this.serviceRunning ? '/api/video/stop' : '/api/video/start';
            const response = await fetch(endpoint, { method: 'POST' });
            const data = await response.json();

            if (data.success) {
                window.notificationManager?.showSuccess(data.message);
                // Poll more aggressively right after a toggle
                this._pollDelay = 1000;
                setTimeout(() => this.checkServiceStatus(), this._pollDelay);
            } else {
                window.notificationManager?.showError(data.error || 'Service operation failed');
                toggleBtn.innerHTML = originalContent;
                toggleBtn.disabled = false;
            }
        } catch (error) {
            console.error('Error toggling service:', error);
            window.notificationManager?.showError('Error communicating with service');
            toggleBtn.innerHTML = originalContent;
            toggleBtn.disabled = false;
        }
    }

    async installVideoService() {
        const installBtn = document.getElementById('install-service');
        const originalContent = installBtn.innerHTML;
        
        try {
            installBtn.disabled = true;
            installBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Installing...';

            const response = await fetch('/api/video/install', { method: 'POST' });
            const data = await response.json();

            if (data.success) {
                window.notificationManager?.showSuccess('Installation started in background. This may take 10-20 minutes.');
                // Poll for installation completion
                this.pollInstallationStatus();
            } else {
                window.notificationManager?.showError(data.error || 'Installation failed');
                installBtn.innerHTML = originalContent;
                installBtn.disabled = false;
            }
        } catch (error) {
            console.error('Error installing service:', error);
            window.notificationManager?.showError('Error starting installation');
            installBtn.innerHTML = originalContent;
            installBtn.disabled = false;
        }
    }

    pollInstallationStatus() {
        // Clear any existing polling
        if (this._installationPollInterval) {
            clearInterval(this._installationPollInterval);
        }
        
        this._installationPollInterval = setInterval(async () => {
            try {
                const response = await fetch('/api/video/status');
                const data = await response.json();
                
                if (data.success && data.status.installed) {
                    clearInterval(this._installationPollInterval);
                    this._installationPollInterval = null;
                    window.notificationManager?.showSuccess('Installation completed successfully!');
                    this.checkServiceStatus();
                }
            } catch (error) {
                console.error('Error polling installation status:', error);
            }
        }, 10000); // Poll every 10 seconds

        // Stop polling after 30 minutes
        setTimeout(() => {
            if (this._installationPollInterval) {
                clearInterval(this._installationPollInterval);
                this._installationPollInterval = null;
                window.notificationManager?.showWarning('Installation polling timed out. Please check manually.');
            }
        }, 30 * 60 * 1000);
    }

    async generateVideo() {
        if (this.generationInProgress) {
            window.notificationManager?.showWarning('Video generation already in progress');
            return;
        }

        const prompt = document.getElementById('video-prompt').value.trim();
        if (!prompt) {
            window.notificationManager?.showError('Please enter a video prompt');
            return;
        }
        
        // Validate prompt length
        if (prompt.length > 1000) {
            window.notificationManager?.showError('Video prompt is too long. Please keep it under 1000 characters.');
            return;
        }
        
        // Validate prompt content (basic check for potentially harmful content)
        if (this.containsHarmfulContent(prompt)) {
            window.notificationManager?.showError('Video prompt contains potentially inappropriate content. Please revise.');
            return;
        }

        if (!this.serviceRunning) {
            window.notificationManager?.showError('Video service is not running. Please start the service first.');
            return;
        }

        // Validate form inputs
        const width = parseInt(document.getElementById('video-width').value);
        const height = parseInt(document.getElementById('video-height').value);
        const frames = parseInt(document.getElementById('video-frames').value);
        const fps = parseInt(document.getElementById('video-fps').value);
        
        // Validate dimensions
        if (width < 256 || width > 2048 || height < 256 || height > 2048) {
            window.notificationManager?.showError('Video dimensions must be between 256 and 2048 pixels.');
            return;
        }
        
        // Validate frames
        if (frames < 1 || frames > 64) {
            window.notificationManager?.showError('Frame count must be between 1 and 64.');
            return;
        }
        
        // Validate FPS
        if (fps < 1 || fps > 30) {
            window.notificationManager?.showError('FPS must be between 1 and 30.');
            return;
        }

        // Get advanced settings
        const advancedSettings = this.getAdvancedSettings();
        
        // Validate advanced settings
        if (!this.validateAdvancedSettings(advancedSettings)) {
            return;
        }

        const generateBtn = document.getElementById('generate-btn');
        const originalContent = generateBtn.innerHTML;

        try {
            this.generationInProgress = true;
            generateBtn.disabled = true;
            generateBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Generating...';

            const requestData = {
                prompt: prompt,
                width: width,
                height: height,
                frames: frames,
                fps: fps,
                ...advancedSettings
            };

            // Get CSRF token from form
            const csrfToken = document.querySelector('input[name="csrf_token"]')?.value;

            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 second timeout for generation start

            const response = await fetch('/api/video/generate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify(requestData),
                signal: controller.signal
            });
            clearTimeout(timeoutId);

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();

            if (data.success) {
                window.notificationManager?.showSuccess(data.message);
                document.getElementById('video-prompt').value = '';
                
                // Switch to queue tab to show the job
                const queueTab = document.getElementById('queue-tab');
                this.switchTab(queueTab);
                
                this.loadJobQueue();
            } else {
                window.notificationManager?.showError(data.error || 'Video generation failed');
            }
        } catch (error) {
            if (error.name === 'AbortError') {
                window.notificationManager?.showError('Video generation request timed out. Please try again.');
            } else {
                console.error('Error generating video:', error);
                window.notificationManager?.showError('Error starting video generation: ' + error.message);
            }
        } finally {
            this.generationInProgress = false;
            generateBtn.disabled = false;
            generateBtn.innerHTML = originalContent;
        }
    }

    getAdvancedSettings() {
        const settings = {};
        
        // Get model selection
        const modelSelect = document.getElementById('video-model');
        if (modelSelect) {
            settings.model = modelSelect.value;
        }
        
        // Get seed value
        const seedInput = document.getElementById('video-seed');
        if (seedInput && seedInput.value) {
            settings.seed = parseInt(seedInput.value);
        }
        
        // Get guidance scale
        const guidanceInput = document.getElementById('video-guidance');
        if (guidanceInput && guidanceInput.value) {
            settings.guidance_scale = parseFloat(guidanceInput.value);
        }
        
        // Get motion bucket ID
        const motionInput = document.getElementById('video-motion');
        if (motionInput && motionInput.value) {
            settings.motion_bucket_id = parseInt(motionInput.value);
        }
        
        // Get negative prompt
        const negativePrompt = document.getElementById('video-negative-prompt');
        if (negativePrompt && negativePrompt.value.trim()) {
            settings.negative_prompt = negativePrompt.value.trim();
        }
        
        // Get batch settings
        const batchSize = document.getElementById('video-batch-size');
        if (batchSize && batchSize.value) {
            settings.batch_size = parseInt(batchSize.value);
        }
        
        // Get quality settings
        const qualitySelect = document.getElementById('video-quality');
        if (qualitySelect) {
            settings.quality = qualitySelect.value;
        }
        
        // Get style settings
        const styleSelect = document.getElementById('video-style');
        if (styleSelect) {
            settings.style = styleSelect.value;
        }
        
        return settings;
    }

    validateAdvancedSettings(settings) {
        // Validate seed
        if (settings.seed !== undefined && (settings.seed < 0 || settings.seed > 2147483647)) {
            window.notificationManager?.showError('Seed must be between 0 and 2147483647.');
            return false;
        }
        
        // Validate guidance scale
        if (settings.guidance_scale !== undefined && (settings.guidance_scale < 1.0 || settings.guidance_scale > 20.0)) {
            window.notificationManager?.showError('Guidance scale must be between 1.0 and 20.0.');
            return false;
        }
        
        // Validate motion bucket ID
        if (settings.motion_bucket_id !== undefined && (settings.motion_bucket_id < 1 || settings.motion_bucket_id > 255)) {
            window.notificationManager?.showError('Motion bucket ID must be between 1 and 255.');
            return false;
        }
        
        // Validate batch size
        if (settings.batch_size !== undefined && (settings.batch_size < 1 || settings.batch_size > 4)) {
            window.notificationManager?.showError('Batch size must be between 1 and 4.');
            return false;
        }
        
        // Validate negative prompt length
        if (settings.negative_prompt && settings.negative_prompt.length > 500) {
            window.notificationManager?.showError('Negative prompt is too long. Please keep it under 500 characters.');
            return false;
        }
        
        return true;
    }

    async generateBatchVideos() {
        const prompts = this.getBatchPrompts();
        
        if (prompts.length === 0) {
            window.notificationManager?.showError('Please add at least one prompt for batch generation.');
            return;
        }
        
        if (prompts.length > 10) {
            window.notificationManager?.showError('Batch generation is limited to 10 videos at a time.');
            return;
        }
        
        if (!this.serviceRunning) {
            window.notificationManager?.showError('Video service is not running. Please start the service first.');
            return;
        }
        
        // Validate all prompts
        for (let i = 0; i < prompts.length; i++) {
            const prompt = prompts[i];
            if (!prompt.trim()) {
                window.notificationManager?.showError(`Prompt ${i + 1} is empty. Please provide a valid prompt.`);
                return;
            }
            
            if (prompt.length > 1000) {
                window.notificationManager?.showError(`Prompt ${i + 1} is too long. Please keep it under 1000 characters.`);
                return;
            }
            
            if (this.containsHarmfulContent(prompt)) {
                window.notificationManager?.showError(`Prompt ${i + 1} contains potentially inappropriate content. Please revise.`);
                return;
            }
        }
        
        const batchBtn = document.getElementById('batch-generate-btn');
        const originalContent = batchBtn.innerHTML;
        
        try {
            batchBtn.disabled = true;
            batchBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Starting Batch...';
            
            const baseSettings = this.getAdvancedSettings();
            const batchData = {
                prompts: prompts,
                base_settings: baseSettings
            };
            
            // Get CSRF token
            const csrfToken = document.querySelector('input[name="csrf_token"]')?.value;
            
            const response = await fetch('/api/video/generate-batch', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify(batchData)
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            if (data.success) {
                window.notificationManager?.showSuccess(`Batch generation started: ${prompts.length} videos queued`);
                this.clearBatchPrompts();
                
                // Switch to queue tab
                const queueTab = document.getElementById('queue-tab');
                this.switchTab(queueTab);
                this.loadJobQueue();
            } else {
                window.notificationManager?.showError(data.error || 'Batch generation failed');
            }
        } catch (error) {
            console.error('Error starting batch generation:', error);
            window.notificationManager?.showError('Error starting batch generation: ' + error.message);
        } finally {
            batchBtn.disabled = false;
            batchBtn.innerHTML = originalContent;
        }
    }

    getBatchPrompts() {
        const prompts = [];
        const promptElements = document.querySelectorAll('.batch-prompt-input');
        
        for (const element of promptElements) {
            const prompt = element.value.trim();
            if (prompt) {
                prompts.push(prompt);
            }
        }
        
        return prompts;
    }

    clearBatchPrompts() {
        const promptElements = document.querySelectorAll('.batch-prompt-input');
        for (const element of promptElements) {
            element.value = '';
        }
    }

    addBatchPrompt() {
        const batchContainer = document.getElementById('batch-prompts-container');
        const promptCount = batchContainer.children.length;
        
        if (promptCount >= 10) {
            window.notificationManager?.showWarning('Maximum 10 prompts allowed for batch generation.');
            return;
        }
        
        const promptDiv = document.createElement('div');
        promptDiv.className = 'batch-prompt-item mb-3';
        promptDiv.innerHTML = `
            <div class="input-group">
                <span class="input-group-text">Prompt ${promptCount + 1}</span>
                <input type="text" class="form-control batch-prompt-input" 
                       placeholder="Enter video prompt..." maxlength="1000">
                <button class="btn btn-outline-danger" type="button" onclick="this.parentElement.parentElement.remove(); window.videoPortal?.updateBatchNumbers();">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        `;
        
        batchContainer.appendChild(promptDiv);
    }

    updateBatchNumbers() {
        const promptItems = document.querySelectorAll('.batch-prompt-item');
        promptItems.forEach((item, index) => {
            const label = item.querySelector('.input-group-text');
            label.textContent = `Prompt ${index + 1}`;
        });
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

    async loadVideoGallery() {
        const gallery = document.getElementById('video-gallery');
        
        try {
            // Show loading state
            gallery.innerHTML = `
                <div class="col-12 text-center py-4">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                    <p class="mt-2">Loading videos...</p>
                </div>
            `;

            const response = await fetch('/api/video/gallery');
            const data = await response.json();

            if (data.success) {
                this.renderVideoGallery(data.videos);
            } else {
                gallery.innerHTML = `
                    <div class="col-12 text-center py-4 text-muted">
                        <i class="bi bi-exclamation-triangle display-4"></i>
                        <p class="mt-2">Failed to load videos: ${data.error}</p>
                    </div>
                `;
            }
        } catch (error) {
            console.error('Error loading video gallery:', error);
            gallery.innerHTML = `
                <div class="col-12 text-center py-4 text-muted">
                    <i class="bi bi-wifi-off display-4"></i>
                    <p class="mt-2">Error loading videos</p>
                </div>
            `;
        }
    }

    renderVideoGallery(videos) {
        const gallery = document.getElementById('video-gallery');
        
        if (!videos || videos.length === 0) {
            gallery.innerHTML = `
                <div class="col-12 text-center py-4 text-muted">
                    <i class="bi bi-camera-video display-4"></i>
                    <p class="mt-2">No videos generated yet</p>
                    <p class="small">Create your first video using the generation panel!</p>
                </div>
            `;
            return;
        }

        const videoCards = videos.map(video => {
            const createdDate = new Date(video.created * 1000).toLocaleString();
            const fileSize = this.formatFileSize(video.size);
            
            // Escape HTML to prevent XSS
            const escapedFilename = this.escapeHtml(video.filename);
            
            return `
                <div class="col-md-4 col-lg-3">
                    <div class="video-card">
                        <div class="video-thumbnail" style="background-image: url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect width="100" height="100" fill="%23f0f0f0"/><circle cx="50" cy="50" r="20" fill="%23007bff"/><polygon points="45,40 45,60 65,50" fill="white"/></svg>')">
                        </div>
                        <div class="video-card-body">
                            <div class="video-title">${escapedFilename}</div>
                            <div class="video-meta">
                                <small class="text-muted">
                                    <i class="bi bi-calendar"></i> ${createdDate}<br>
                                    <i class="bi bi-file-earmark"></i> ${fileSize}
                                </small>
                            </div>
                            <div class="video-actions">
                                <button class="btn btn-sm btn-outline-primary" onclick="videoPortal.downloadVideo('${escapedFilename}')">
                                    <i class="bi bi-download"></i> Download
                                </button>
                                <button class="btn btn-sm btn-outline-secondary" onclick="videoPortal.previewVideo('${escapedFilename}')">
                                    <i class="bi bi-play"></i> Preview
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }).join('');

        gallery.innerHTML = videoCards;
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    async loadJobQueue() {
        const queue = document.getElementById('job-queue');
        
        try {
            // Show loading state
            queue.innerHTML = `
                <div class="text-center py-3">
                    <div class="spinner-border spinner-border-sm text-primary" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                    <p class="mt-2 mb-0">Loading job queue...</p>
                </div>
            `;

            // Try to fetch actual job queue data
            const response = await fetch('/api/video/queue');
            
            if (response.ok) {
                const data = await response.json();
                
                if (data.success && data.jobs && data.jobs.length > 0) {
                    this.renderJobQueue(data.jobs);
                } else {
                    // No active jobs
                    queue.innerHTML = `
                        <div class="text-center py-4 text-muted">
                            <i class="bi bi-check-circle display-4"></i>
                            <p class="mt-2">No active video generation jobs</p>
                            <p class="small">Start a new video generation to see jobs here</p>
                        </div>
                    `;
                }
            } else {
                throw new Error('Job queue API not available');
            }
        } catch (error) {
            // Fallback to placeholder when API is not available
            console.log('Job queue API not available, showing placeholder:', error.message);
            queue.innerHTML = `
                <div class="text-center py-4 text-muted">
                    <i class="bi bi-clock-history display-4"></i>
                    <p class="mt-2">Job queue monitoring coming soon</p>
                    <p class="small">Check the Video Gallery for completed videos</p>
                    <button class="btn btn-outline-primary btn-sm mt-2" onclick="videoPortal.loadVideoGallery(); videoPortal.switchTab(document.querySelector('[data-target=\\'#gallery-panel\\']'))">
                        <i class="bi bi-images"></i> View Gallery
                    </button>
                </div>
            `;
        }
    }

    renderJobQueue(jobs) {
        const queue = document.getElementById('job-queue');
        
        const jobCards = jobs.map(job => {
            const progress = job.progress || 0;
            const statusColor = this.getJobStatusColor(job.status);
            const createdDate = new Date(job.created * 1000).toLocaleString();
            
            return `
                <div class="job-card mb-3 p-3 border rounded">
                    <div class="d-flex justify-content-between align-items-start mb-2">
                        <h6 class="mb-1">${this.escapeHtml(job.prompt.substring(0, 50))}${job.prompt.length > 50 ? '...' : ''}</h6>
                        <span class="badge bg-${statusColor}">${job.status}</span>
                    </div>
                    <div class="progress mb-2" style="height: 6px;">
                        <div class="progress-bar bg-${statusColor}" style="width: ${progress}%"></div>
                    </div>
                    <div class="d-flex justify-content-between text-muted small">
                        <span>ID: ${job.id}</span>
                        <span>${createdDate}</span>
                    </div>
                    ${job.status === 'failed' && job.error ? `<div class="text-danger small mt-1">Error: ${this.escapeHtml(job.error)}</div>` : ''}
                </div>
            `;
        }).join('');
        
        queue.innerHTML = `
            <div class="d-flex justify-content-between align-items-center mb-3">
                <h5 class="mb-0">Active Jobs (${jobs.length})</h5>
                <button class="btn btn-outline-secondary btn-sm" onclick="videoPortal.loadJobQueue()">
                    <i class="bi bi-arrow-clockwise"></i> Refresh
                </button>
            </div>
            ${jobCards}
        `;
    }

    getJobStatusColor(status) {
        const colors = {
            'pending': 'secondary',
            'processing': 'primary',
            'completed': 'success',
            'failed': 'danger',
            'cancelled': 'warning'
        };
        return colors[status] || 'secondary';
    }

    toggleExamplePrompts() {
        const examples = document.getElementById('example-prompts');
        if (examples.style.display === 'none') {
            examples.style.display = 'block';
        } else {
            examples.style.display = 'none';
        }
    }

    hideExamplePrompts() {
        document.getElementById('example-prompts').style.display = 'none';
    }

    useExamplePrompt(promptText) {
        const promptInput = document.getElementById('video-prompt');
        if (promptInput) {
            promptInput.value = promptText.trim();
            this.hideExamplePrompts();
            
            // Show toast notification
            window.notificationManager?.showInfo(`Example prompt selected: "${promptText.substring(0, 50)}${promptText.length > 50 ? '...' : ''}"`);
            
            // Focus on the prompt input
            promptInput.focus();
            
            // Scroll to the generation form
            const form = document.getElementById('video-generation-form');
            if (form) {
                form.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        }
    }

    downloadVideo(filename) {
        window.open(`/api/video/serve/${filename}`, '_blank');
    }

    previewVideo(filename) {
        // For now, just download the video
        // In a full implementation, this would open a modal with video player
        this.downloadVideo(filename);
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }


}

// Initialize the video portal when the page loads
document.addEventListener('DOMContentLoaded', () => {
    window.videoPortal = new VideoPortal();
});
