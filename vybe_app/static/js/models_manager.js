document.addEventListener('DOMContentLoaded', function() {
    // Collapsible section functionality
    const modelSections = document.querySelectorAll('.model-section');
    
    // Initialize collapsible sections
    modelSections.forEach(section => {
        // Note: section header is available but not currently used
        
        // Add event listener for section toggle
        // DISABLED: Preventing JS from overwriting hardcoded template content
        /*
        section.addEventListener('toggle', () => {
            const sectionId = section.id;
            
            // Load data when section is opened
            if (section.open) {
                if (sectionId === 'llm-models') {
                    // Ensure LLM models and recommended models are loaded
                    if (!installedModelsData.length) {
                        loadModels();
                    }
                    if (!recommendedModelsData.length) {
                        loadRecommendedModels();
                    }
                } else if (sectionId === 'image-models') {
                    // Ensure image models and SD status are loaded - DISABLED FOR TESTING
                    // if (!imageModelsData.length) {
                    //     loadImageModels();
                    // }
                    // Load available models for download - DISABLED FOR TESTING
                    // loadAvailableImageModels();
                    // checkSDStatus(); // DISABLED FOR TESTING
                } else if (sectionId === 'audio-models') {
                    // Load audio models immediately when section is opened
                    loadAudioModels();
                }
            }
        });
        */
        
        // Check if section is open by default and initialize
        if (section.open) {
            const sectionId = section.id;
            if (sectionId === 'llm-models') {
                // Initialize all models using parallel loading for better performance
                setTimeout(() => {
                    loadAllModelsInParallel();
                }, 100); // Small delay to ensure DOM is ready
            }
        }
    });

    // Only load models when section is open (handled by section toggle)

    // LLM Models elements
    const modelsList = document.getElementById('models-list');
    const dl32kBtn = document.getElementById('download-recommended-model-llm');
    const pullBtn = document.getElementById('pull-model-btn');
    const modelInput = document.getElementById('model-name-input');
    const pullStatus = document.getElementById('pull-status-output');
    const recommendedModelsList = document.getElementById('recommended-models-list');
    const searchInput = document.getElementById('search-recommended');
    const categoryFilter = document.getElementById('category-filter');
    const loadFilter = document.getElementById('load-filter');
    const sortNameBtn = document.getElementById('sort-name-btn');
    const sortLoadBtn = document.getElementById('sort-load-btn');
    
    // Comparison controls
    const compareSelectedBtn = document.getElementById('compare-selected-btn');
    const clearSelectionBtn = document.getElementById('clear-selection-btn');

    // Image models elements
    const sdStatus = document.getElementById('sd-status');
    const sdDetails = document.getElementById('sd-details');
    const sdInstallStatus = document.getElementById('sd-install-status');
    const sdServiceStatus = document.getElementById('sd-service-status');
    const sdModelsCount = document.getElementById('sd-models-count');
    const refreshSdStatusBtn = document.getElementById('refresh-sd-status');
    const imageModelsList = document.getElementById('image-models-list');
    const refreshImageModelsBtn = document.getElementById('refresh-image-models');
    const manageSdModelsBtn = document.getElementById('manage-sd-models');
    const openSdFolderBtn = document.getElementById('open-sd-folder');
    const openSdWebBtn = document.getElementById('open-sd-web');

    // Modal elements
    const optimizationModal = document.getElementById('optimization-modal');
    const modelDetailsModal = document.getElementById('model-details-modal');
    const modelCompareModal = document.getElementById('model-compare-modal');
    const baseModelNameSpan = document.getElementById('base-model-name');
    const newModelNamePreview = document.getElementById('new-model-name-preview');
    const gpuLayersInput = document.getElementById('gpu-layers-input');
    const gpuLayersValue = document.getElementById('gpu-layers-value');
    const cpuThreadsInput = document.getElementById('cpu-threads-input');
    const cpuThreadsValue = document.getElementById('cpu-threads-value');
    const createOptimizedBtn = document.getElementById('create-optimized-btn');
    const cancelOptimizationBtn = document.getElementById('cancel-optimization-btn');
    const optimizationStatus = document.getElementById('optimization-status');

    let recommendedModelsData = [];
    let installedModelsData = [];
    let imageModelsData = [];
    let currentBaseModel = '';
    let selectedModelsForComparison = new Set();

    // Utility functions to safely update DOM content
    function createElementSafely(tagName, className = '', textContent = '') {
        const element = document.createElement(tagName);
        if (className) element.className = className;
        if (textContent) element.textContent = textContent;
        return element;
    }

    function createLoadingState(message = 'Loading...') {
        const fragment = document.createDocumentFragment();
        const container = createElementSafely('div', 'loading-state');
        const spinner = createElementSafely('div', 'spinner');
        const text = createElementSafely('p', '', message);
        
        container.appendChild(spinner);
        container.appendChild(text);
        fragment.appendChild(container);
        return fragment;
    }

    function createStatusMessage(message, isError = false, additionalContent = null) {
        const fragment = document.createDocumentFragment();
        const container = createElementSafely('div', isError ? 'status-message error' : 'status-message');
        const text = createElementSafely('p', '', message);
        
        container.appendChild(text);
        if (additionalContent) {
            container.appendChild(additionalContent);
        }
        fragment.appendChild(container);
        return fragment;
    }

    function replaceContent(element, newContent) {
        while (element.firstChild) {
            element.removeChild(element.firstChild);
        }
        element.appendChild(newContent);
    }

    function renderAudioModelsList(container, models) {
        const fragment = document.createDocumentFragment();
        
        models.forEach(model => {
            const modelItem = createElementSafely('div', 'model-item');
            
            const modelInfo = createElementSafely('div', 'model-info');
            const title = createElementSafely('h4', 'model-title');
            title.textContent = model.name;
            const description = createElementSafely('p', 'model-description');
            description.textContent = model.description;
            modelInfo.appendChild(title);
            modelInfo.appendChild(description);
            
            if (model.size) {
                const size = createElementSafely('span', 'model-size');
                size.textContent = model.size;
                modelInfo.appendChild(size);
            }
            
            const modelActions = createElementSafely('div', 'model-actions');
            const statusBadge = createElementSafely('span', `status-badge ${model.status}`);
            statusBadge.textContent = model.status.replace('_', ' ');
            modelActions.appendChild(statusBadge);
            
            modelItem.appendChild(modelInfo);
            modelItem.appendChild(modelActions);
            fragment.appendChild(modelItem);
        });
        
        replaceContent(container, fragment);
    }

    function renderAudioModelsFromAPI(container, models, defaultDescription) {
        const fragment = document.createDocumentFragment();
        
        models.forEach(model => {
            const modelItem = createElementSafely('div', 'model-item');
            
            const modelInfo = createElementSafely('div', 'model-info');
            const title = createElementSafely('h4', 'model-title');
            title.textContent = model.name || model.full_name || 'Unknown Model';
            const description = createElementSafely('p', 'model-description');
            description.textContent = model.description || model.service || defaultDescription;
            modelInfo.appendChild(title);
            modelInfo.appendChild(description);
            
            const size = createElementSafely('span', 'model-size');
            size.textContent = model.language || model.size || 'Available';
            modelInfo.appendChild(size);
            
            const modelActions = createElementSafely('div', 'model-actions');
            const statusBadge = createElementSafely('span', `status-badge ${model.status || 'available'}`);
            statusBadge.textContent = model.status || 'Available';
            modelActions.appendChild(statusBadge);
            
            modelItem.appendChild(modelInfo);
            modelItem.appendChild(modelActions);
            fragment.appendChild(modelItem);
        });
        
        replaceContent(container, fragment);
    }

    // Function to update section counts
    function updateSectionCounts() {
        const llmCount = document.getElementById('llm-count');
        const imageCount = document.getElementById('image-count');
        const audioCount = document.getElementById('audio-count');
        
        if (llmCount) {
            if (installedModelsData.length > 0) {
                llmCount.textContent = `(${installedModelsData.length})`;
                llmCount.style.display = 'inline';
            } else {
                llmCount.style.display = 'none';
            }
        }
        
        if (imageCount) {
            if (imageModelsData.length > 0) {
                imageCount.textContent = `(${imageModelsData.length})`;
                imageCount.style.display = 'inline';
            } else {
                imageCount.style.display = 'none';
            }
        }

        if (audioCount) {
            // Audio count will be updated when audio models are loaded
            audioCount.style.display = 'none';
        }
    }

    // Initialize the page
    updateSectionCounts(); // Only update tab counts on load

    // Wire 1-click 32k download
    if (dl32kBtn) {
        const dlBar = document.getElementById('dl32k-progress-bar');
        const dlWrap = document.getElementById('dl32k-progress');
        const dlTxt = document.getElementById('dl32k-progress-text');
        let pollTimer = null;
        const poll = async () => {
            try {
                // Direct model download without splash progress
                const r = await fetch('/api/models/download_progress', { cache: 'no-store' });
                const j = await r.json();
                if (j && j.success) {
                    const pct = Math.max(0, Math.min(100, Math.round(j.percentage || 0)));
                    dlBar.style.width = pct + '%';
                    dlBar.setAttribute('aria-valuenow', String(pct));
                    dlTxt.textContent = j.last_message || dlTxt.textContent;
                    if (!j.in_progress && pct >= 100 && pollTimer) { clearInterval(pollTimer); pollTimer = null; }
                }
            } catch {
                // Silently handle polling errors
            }
        };

        dl32kBtn.addEventListener('click', async () => {
            try {
                dl32kBtn.disabled = true; dl32kBtn.textContent = 'Starting download…';
                dlWrap.style.display = 'block';
                dlBar.style.width = '0%'; dlBar.setAttribute('aria-valuenow','0');
                dlTxt.textContent = '';

                const res = await fetch('/api/models/download_default', { method: 'POST' });
                if (res.ok) {
                    const data = await res.json().catch(() => ({ success: true, updates: [] }));
                    // If backend returned progress updates, show last one
                    if (data && Array.isArray(data.updates) && data.updates.length) {
                        const last = data.updates[data.updates.length - 1];
                        const pct = Math.max(0, Math.min(100, Math.round(last.percentage || 0)));
                        dlBar.style.width = pct + '%';
                        dlBar.setAttribute('aria-valuenow', String(pct));
                        dlTxt.textContent = last.message || '';
                    }
                    // Start polling progress while backend finalizes
                    if (!pollTimer) { pollTimer = setInterval(poll, 1500); }
                    dlTxt.textContent = 'Downloading…';
                    setTimeout(() => { 
                        loadModels(); 
                        // Clear polling timer after completion
                        if (pollTimer) {
                            clearInterval(pollTimer);
                            pollTimer = null;
                        }
                    }, 4000);
                } else {
                    dl32kBtn.textContent = 'Retry Download'; dl32kBtn.disabled = false;
                    dlTxt.textContent = 'Server rejected download request';
                }
            } catch (e) {
                console.error('Download failed', e);
                window.notificationManager.showError('Download failed. Please check your connection and try again.');
                dl32kBtn.textContent = 'Retry Download'; dl32kBtn.disabled = false;
                dlTxt.textContent = 'Network error';
            }
        });
    }

    // Event listeners for image models with cleanup tracking
    const eventListeners = [];
    
    if (refreshSdStatusBtn) {
        refreshSdStatusBtn.addEventListener('click', checkSDStatus);
        eventListeners.push({ element: refreshSdStatusBtn, event: 'click', handler: checkSDStatus });
    }
    if (refreshImageModelsBtn) {
        refreshImageModelsBtn.addEventListener('click', loadImageModels);
        eventListeners.push({ element: refreshImageModelsBtn, event: 'click', handler: loadImageModels });
    }
    const refreshAvailableBtn = document.getElementById('refresh-available-models');
    if (refreshAvailableBtn) {
        refreshAvailableBtn.addEventListener('click', loadAvailableImageModels);
        eventListeners.push({ element: refreshAvailableBtn, event: 'click', handler: loadAvailableImageModels });
    }
    if (manageSdModelsBtn) {
        const manageHandler = () => { window.location.href = '/image_studio'; };
        manageSdModelsBtn.addEventListener('click', manageHandler);
        eventListeners.push({ element: manageSdModelsBtn, event: 'click', handler: manageHandler });
    }
    if (openSdFolderBtn) {
        openSdFolderBtn.addEventListener('click', openModelsFolder);
        eventListeners.push({ element: openSdFolderBtn, event: 'click', handler: openModelsFolder });
    }
    if (openSdWebBtn) {
        const webHandler = () => { window.open('http://localhost:7860', '_blank'); };
        openSdWebBtn.addEventListener('click', webHandler);
        eventListeners.push({ element: openSdWebBtn, event: 'click', handler: webHandler });
    }
    
    // Store event listeners for potential cleanup
    window.modelsPageEventListeners = eventListeners;
    
    // Cleanup function for event listeners
    window.cleanupModelsPageEventListeners = function() {
        if (window.modelsPageEventListeners) {
            window.modelsPageEventListeners.forEach(listener => {
                if (listener.element && listener.handler) {
                    listener.element.removeEventListener(listener.event, listener.handler);
                }
            });
            window.modelsPageEventListeners = [];
        }
    };
    
    // Cleanup on page unload
    window.addEventListener('beforeunload', window.cleanupModelsPageEventListeners);

    // Function to check Stable Diffusion status
    async function checkSDStatus() {
        try {
            sdStatus.textContent = 'Checking Stable Diffusion status...';
            sdDetails.style.display = 'none';
            
            const response = await fetch('/api/images/status');
            const data = await response.json();
            
            if (data.success) {
                const status = data.status;
                
                if (status.running) {
                    sdStatus.textContent = 'Stable Diffusion WebUI is running';
                    sdStatus.style.color = 'var(--color-success)';
                    openSdWebBtn.style.display = 'inline-flex';
                } else {
                    sdStatus.textContent = 'Stable Diffusion WebUI is not running';
                    sdStatus.style.color = 'var(--color-warning)';
                    openSdWebBtn.style.display = 'none';
                }
                
                // Update details
                sdInstallStatus.textContent = status.installed ? 'Installed' : 'Not Installed';
                sdServiceStatus.textContent = status.running ? 'Running' : 'Stopped';
                sdModelsCount.textContent = status.models_available ? status.models_available.length : '0';
                
                sdDetails.style.display = 'block';
                
            } else {
                sdStatus.textContent = 'Error checking Stable Diffusion status';
                sdStatus.style.color = 'var(--color-error)';
            }
        } catch (_error) {
            console.error('Error checking SD status:', _error);
            window.notificationManager.showError('Failed to check Stable Diffusion status. Please try again.');
            sdStatus.textContent = 'Error checking Stable Diffusion status';
            sdStatus.style.color = 'var(--color-error)';
        }
    }

    // Function to load image models
    async function loadImageModels() {
        try {
            replaceContent(imageModelsList, createLoadingState('Loading image models...'));
            
            const response = await fetch('/api/images/models');
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            if (data.success && data.models && data.models.length > 0) {
                imageModelsData = data.models;
                renderImageModels(data.models);
                updateSectionCounts();
            } else if (data.success && data.models && data.models.length === 0) {
                const fragment = document.createDocumentFragment();
                const container = createElementSafely('div', 'status-message');
                
                container.appendChild(createElementSafely('p', '', 'No Stable Diffusion models found.'));
                container.appendChild(createElementSafely('p', '', 'Place .safetensors or .ckpt files in your models directory.'));
                
                const dirText = createElementSafely('p', '');
                const strongText = createElementSafely('strong', '', 'Models directory: ');
                dirText.appendChild(strongText);
                dirText.appendChild(document.createTextNode(data.models_dir || 'Not available'));
                container.appendChild(dirText);
                
                fragment.appendChild(container);
                replaceContent(imageModelsList, fragment);
                imageModelsData = []; 
                updateSectionCounts(); 
            } else {
                const fragment = document.createDocumentFragment();
                const container = createElementSafely('div', 'status-message error');
                
                const strongEl = createElementSafely('strong', '', 'Could not load image models.');
                const p1 = createElementSafely('p', '');
                p1.appendChild(strongEl);
                container.appendChild(p1);
                
                container.appendChild(createElementSafely('p', '', 'Please ensure the Stable Diffusion service is running from the Image Studio and try again.'));
                
                const errorText = createElementSafely('p', '');
                const emText = createElementSafely('em', '', 'Error: ');
                errorText.appendChild(emText);
                errorText.appendChild(document.createTextNode(data.error || 'Unknown error'));
                container.appendChild(errorText);
                
                fragment.appendChild(container);
                replaceContent(imageModelsList, fragment);
                imageModelsData = []; 
                updateSectionCounts(); 
            }
        } catch (_error) {
            console.error('Error loading image models:', _error);
            window.notificationManager.showError('Failed to load image models. Please check the Stable Diffusion service and try again.');
            
            const fragment = document.createDocumentFragment();
            const container = createElementSafely('div', 'status-message error');
            
            const strongEl = createElementSafely('strong', '', 'Could not load image models.');
            const p1 = createElementSafely('p', '');
            p1.appendChild(strongEl);
            container.appendChild(p1);
            
            container.appendChild(createElementSafely('p', '', 'Please ensure the Stable Diffusion service is running from the Image Studio and try again.'));
            
            const errorText = createElementSafely('p', '');
            const emText = createElementSafely('em', '', 'Error: ');
            errorText.appendChild(emText);
            errorText.appendChild(document.createTextNode(_error.message));
            container.appendChild(errorText);
            
            const retryBtn = createElementSafely('button', 'btn btn-secondary');
            retryBtn.style.marginTop = '10px';
            retryBtn.addEventListener('click', () => window.loadImageModels());
            
            const btnIcon = createElementSafely('span', 'btn-icon', '🔄');
            retryBtn.appendChild(btnIcon);
            retryBtn.appendChild(document.createTextNode(' Retry'));
            container.appendChild(retryBtn);
            
            fragment.appendChild(container);
            replaceContent(imageModelsList, fragment);
            imageModelsData = []; 
            updateSectionCounts(); 
        }
    }

    // Make loadImageModels available globally for retry button
    window.loadImageModels = loadImageModels;

    // Function to load available image models for download
    async function loadAvailableImageModels() {
        const availableGrid = document.getElementById('available-models-grid');
        
        try {
            replaceContent(availableGrid, createLoadingState('Loading available models...'));
            
            const response = await fetch('/api/images/models/available');
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            if (data.success && data.models) {
                renderAvailableImageModels(data.models);
            } else {
                const fragment = document.createDocumentFragment();
                const container = createElementSafely('div', 'status-message error');
                
                const strongEl = createElementSafely('strong', '', 'Could not load available models.');
                const p1 = createElementSafely('p', '');
                p1.appendChild(strongEl);
                container.appendChild(p1);
                
                const errorText = createElementSafely('p', '');
                const emText = createElementSafely('em', '', 'Error: ');
                errorText.appendChild(emText);
                errorText.appendChild(document.createTextNode(data.error || 'Unknown error'));
                container.appendChild(errorText);
                
                fragment.appendChild(container);
                replaceContent(availableGrid, fragment);
            }
        } catch (_error) {
            console.error('Error loading available image models:', _error);
            window.notificationManager.showError('Failed to load available models. Please check your connection and try again.');
            
            const fragment = document.createDocumentFragment();
            const container = createElementSafely('div', 'status-message error');
            
            const strongEl = createElementSafely('strong', '', 'Could not load available models.');
            const p1 = createElementSafely('p', '');
            p1.appendChild(strongEl);
            container.appendChild(p1);
            
            const errorText = createElementSafely('p', '');
            const emText = createElementSafely('em', '', 'Error: ');
            errorText.appendChild(emText);
            errorText.appendChild(document.createTextNode(_error.message));
            container.appendChild(errorText);
            
            const retryBtn = createElementSafely('button', 'btn btn-secondary');
            retryBtn.style.marginTop = '10px';
            retryBtn.addEventListener('click', loadAvailableImageModels);
            
            const btnIcon = createElementSafely('span', 'btn-icon', '🔄');
            retryBtn.appendChild(btnIcon);
            retryBtn.appendChild(document.createTextNode(' Retry'));
            container.appendChild(retryBtn);
            
            fragment.appendChild(container);
            replaceContent(availableGrid, fragment);
        }
    }

    // Function to render available image models with samples
    function renderAvailableImageModels(models) {
        const availableGrid = document.getElementById('available-models-grid');
        
        if (!models || models.length === 0) {
            replaceContent(availableGrid, createStatusMessage('No available models found.'));
            return;
        }

        const fragment = document.createDocumentFragment();
        const gridContainer = createElementSafely('div', 'available-models-grid');

        models.forEach(model => {
            const modelCard = createElementSafely('div', 'available-model-card');
            
            // Model header
            const header = createElementSafely('div', 'model-header');
            const modelName = createElementSafely('h4', 'model-name');
            modelName.textContent = model.name;
            const modelType = createElementSafely('span', 'model-type');
            modelType.textContent = model.type;
            header.appendChild(modelName);
            header.appendChild(modelType);
            modelCard.appendChild(header);
            
            // Model samples
            const samplesDiv = createElementSafely('div', 'model-samples');
            if (model.sample_images && model.sample_images.length > 0) {
                model.sample_images.slice(0, 2).forEach((img, index) => {
                    const imageContainer = createElementSafely('div', 'image-container');
                    imageContainer.style.position = 'relative';
                    
                    const imgEl = document.createElement('img');
                    imgEl.src = img;
                    imgEl.alt = `${model.name} sample ${index + 1}`;
                    imgEl.className = 'model-sample-image';
                    imgEl.loading = 'lazy';
                    imgEl.style.cssText = 'width: 100%; height: 150px; object-fit: cover; border-radius: 8px;';
                    
                    const placeholder = createElementSafely('div', 'image-placeholder');
                    placeholder.style.cssText = 'display: flex; align-items: center; justify-content: center; background: #2a2a2a; color: #999; height: 150px; border-radius: 8px; position: absolute; top: 0; left: 0; right: 0; bottom: 0;';
                    const placeholderText = createElementSafely('span', '', '🖼️ Loading...');
                    placeholder.appendChild(placeholderText);
                    
                    imgEl.onerror = () => {
                        imgEl.style.display = 'none';
                        placeholder.style.display = 'flex';
                    };
                    imgEl.onload = () => {
                        placeholder.style.display = 'none';
                    };
                    
                    imageContainer.appendChild(imgEl);
                    imageContainer.appendChild(placeholder);
                    samplesDiv.appendChild(imageContainer);
                });
            } else {
                const placeholder = createElementSafely('div', 'image-placeholder');
                placeholder.style.cssText = 'display: flex; align-items: center; justify-content: center; background: #2a2a2a; color: #999; height: 150px; border-radius: 8px;';
                const placeholderText = createElementSafely('span', '', '🖼️ No Preview Available');
                placeholder.appendChild(placeholderText);
                samplesDiv.appendChild(placeholder);
            }
            modelCard.appendChild(samplesDiv);
            
            // Model info
            const infoDiv = createElementSafely('div', 'model-info');
            const description = createElementSafely('p', 'model-description');
            description.textContent = model.description;
            infoDiv.appendChild(description);
            
            const statsDiv = createElementSafely('div', 'model-stats');
            const sizeSpan = createElementSafely('span', 'model-size');
            sizeSpan.textContent = `📁 ${model.size}`;
            const licenseSpan = createElementSafely('span', 'model-license');
            licenseSpan.textContent = `📜 ${model.license}`;
            statsDiv.appendChild(sizeSpan);
            statsDiv.appendChild(licenseSpan);
            infoDiv.appendChild(statsDiv);
            modelCard.appendChild(infoDiv);
            
            // Model tags
            const tagsDiv = createElementSafely('div', 'model-tags');
            if (model.tags) {
                model.tags.forEach(tag => {
                    const tagSpan = createElementSafely('span', 'model-tag');
                    tagSpan.textContent = tag;
                    tagsDiv.appendChild(tagSpan);
                });
            }
            modelCard.appendChild(tagsDiv);
            
            // Model actions
            const actionsDiv = createElementSafely('div', 'model-actions');
            
            const downloadBtn = createElementSafely('button', 'btn btn-primary download-model-btn');
            downloadBtn.setAttribute('data-download-url', model.download_url);
            downloadBtn.setAttribute('data-filename', model.filename);
            downloadBtn.setAttribute('data-model-name', model.name);
            const downloadIcon = createElementSafely('span', 'btn-icon', '⬇️');
            downloadBtn.appendChild(downloadIcon);
            downloadBtn.appendChild(document.createTextNode(' Download'));
            
            const detailsBtn = createElementSafely('button', 'btn btn-secondary view-details-btn');
            detailsBtn.setAttribute('data-url', model.huggingface_url);
            const detailsIcon = createElementSafely('span', 'btn-icon', '🔗');
            detailsBtn.appendChild(detailsIcon);
            detailsBtn.appendChild(document.createTextNode(' View Details'));
            
            actionsDiv.appendChild(downloadBtn);
            actionsDiv.appendChild(detailsBtn);
            modelCard.appendChild(actionsDiv);
            
            gridContainer.appendChild(modelCard);
        });

        fragment.appendChild(gridContainer);
        replaceContent(availableGrid, fragment);
    }

    // Function to download an image model
    async function downloadImageModel(downloadUrl, filename, modelName, event) {
        console.log('downloadImageModel called with:', { downloadUrl, filename, modelName });
        
        const button = event.target.closest('.download-model-btn');
        if (!button) {
            console.error('Could not find download button');
            window.notificationManager.showError('Download button not found. Please refresh the page and try again.');
            return;
        }
        
        const originalContent = Array.from(button.childNodes).map(node => node.cloneNode(true));
        console.log('Original button content stored');
        
        try {
            while (button.firstChild) {
                button.removeChild(button.firstChild);
            }
            const icon = createElementSafely('span', 'btn-icon', '⏳');
            button.appendChild(icon);
            button.appendChild(document.createTextNode(' Downloading...'));
            button.disabled = true;
            
            console.log('Opening download URL:', downloadUrl);
            // For now, open the download URL in a new tab
            // In a real implementation, you'd want to handle the download server-side
            window.open(downloadUrl, '_blank');
            
            // Show success message
            while (button.firstChild) {
                button.removeChild(button.firstChild);
            }
            const successIcon = createElementSafely('span', 'btn-icon', '✅');
            button.appendChild(successIcon);
            button.appendChild(document.createTextNode(' Download Started'));
            console.log('Download started successfully');
            
            setTimeout(() => {
                while (button.firstChild) {
                    button.removeChild(button.firstChild);
                }
                originalContent.forEach(node => button.appendChild(node.cloneNode(true)));
                button.disabled = false;
                console.log('Button reset to original state');
            }, 3000);
            
        } catch (_error) {
            console.error('Error downloading model:', _error);
            window.notificationManager.showError('Failed to download model. Please check your connection and try again.');
            
            while (button.firstChild) {
                button.removeChild(button.firstChild);
            }
            const errorIcon = createElementSafely('span', 'btn-icon', '❌');
            button.appendChild(errorIcon);
            button.appendChild(document.createTextNode(' Error'));
            
            setTimeout(() => {
                while (button.firstChild) {
                    button.removeChild(button.firstChild);
                }
                originalContent.forEach(node => button.appendChild(node.cloneNode(true)));
                button.disabled = false;
            }, 3000);
        }
    }

    // Audio models loading with live API
    async function loadAudioModels() {
        const whisperModelsList = document.getElementById('whisper-models-list');
        const ttsModelsList = document.getElementById('tts-models-list');
        const audioCount = document.getElementById('audio-count');
        
        console.log('loadAudioModels called, elements found:', {
            whisperList: !!whisperModelsList,
            ttsList: !!ttsModelsList,
            audioCount: !!audioCount
        });

        // Immediately populate with fallback data to avoid loading states
        const fallbackWhisperModels = [
            { name: 'whisper-tiny', description: 'Fastest Whisper model (39MB)', size: '39 MB', status: 'available' },
            { name: 'whisper-base', description: 'Balanced speed and accuracy (74MB)', size: '74 MB', status: 'available' },
            { name: 'whisper-small', description: 'Better accuracy (244MB)', size: '244 MB', status: 'available' },
            { name: 'whisper-medium', description: 'High accuracy (769MB)', size: '769 MB', status: 'available' },
            { name: 'whisper-large', description: 'Best accuracy (1.55GB)', size: '1.55 GB', status: 'available' }
        ];
        
        const fallbackTtsModels = [
            { name: 'System TTS', description: 'Built-in system text-to-speech', status: 'available' },
            { name: 'Edge TTS', description: 'Microsoft Edge text-to-speech (online)', status: 'requires_internet' },
            { name: 'XTTS-v2', description: 'Advanced voice cloning model', status: 'downloadable' }
        ];
        
        // Render immediately using safe DOM methods
        if (whisperModelsList) {
            renderAudioModelsList(whisperModelsList, fallbackWhisperModels);
        }
        
        if (ttsModelsList) {
            renderAudioModelsList(ttsModelsList, fallbackTtsModels);
        }
        
        if (audioCount) {
            audioCount.textContent = `(${fallbackWhisperModels.length + fallbackTtsModels.length})`;
            audioCount.style.display = 'inline';
        }
        
        // Show loading notifications
        if (window.notificationManager) {
            window.notificationManager.info('Loading audio models...');
        }

        // Now try to get real data from the backend
        try {
            const response = await fetch('/api/models/audio');
            
            if (!response.ok) {
                console.log('Audio API failed, using fallback data');
                if (window.notificationManager) {
                    window.notificationManager.warning('Using cached audio models data - API unavailable');
                }
                return; // Keep fallback data
            }
            
            const data = await response.json();
            console.log('Audio models API response:', data);

            if (data.success && Array.isArray(data.models)) {
                // Notify success
                if (window.notificationManager) {
                    window.notificationManager.success('Audio models loaded successfully');
                }
                // Filter models by type
                const whisperModels = data.models.filter(model => 
                    model.type?.toLowerCase().includes('whisper') ||
                    model.name?.toLowerCase().includes('whisper') ||
                    model.service?.toLowerCase().includes('transcription')
                );

                const ttsModels = data.models.filter(model => 
                    model.type?.toLowerCase().includes('tts') ||
                    model.service?.toLowerCase().includes('tts') ||
                    model.service?.toLowerCase().includes('edge')
                );

                // Render Whisper models
                if (whisperModelsList) {
                    if (whisperModels.length > 0) {
                        renderAudioModelsFromAPI(whisperModelsList, whisperModels, 'Audio transcription model');
                    } else {
                        replaceContent(whisperModelsList, createStatusMessage('No Whisper models available'));
                    }
                }

                // Render TTS models
                if (ttsModelsList) {
                    if (ttsModels.length > 0) {
                        renderAudioModelsFromAPI(ttsModelsList, ttsModels, 'Text-to-speech model');
                    } else {
                        replaceContent(ttsModelsList, createStatusMessage('No TTS models available'));
                    }
                }

                // Update audio count
                if (audioCount) {
                    const totalModels = whisperModels.length + ttsModels.length;
                    audioCount.textContent = totalModels > 0 ? `(${totalModels})` : '';
                    audioCount.style.display = totalModels > 0 ? 'inline' : 'none';
                }

            } else {
                // Handle API error or no models
                if (window.notificationManager) {
                    window.notificationManager.error('Failed to load audio models from API');
                }
                
                if (whisperModelsList) {
                    const fragment = document.createDocumentFragment();
                    const container = createElementSafely('div', 'status-message error');
                    
                    const errorText = createElementSafely('p', '');
                    const strongText = createElementSafely('strong', '', 'Error loading Whisper models');
                    errorText.appendChild(strongText);
                    container.appendChild(errorText);
                    
                    const retryBtn = createElementSafely('button', 'btn btn-secondary retry-btn');
                    retryBtn.setAttribute('data-action', 'loadAudioModels');
                    retryBtn.style.marginTop = '10px';
                    retryBtn.addEventListener('click', loadAudioModels);
                    
                    const btnIcon = createElementSafely('span', 'btn-icon', '🔄');
                    retryBtn.appendChild(btnIcon);
                    retryBtn.appendChild(document.createTextNode(' Retry'));
                    container.appendChild(retryBtn);
                    
                    fragment.appendChild(container);
                    replaceContent(whisperModelsList, fragment);
                }
                if (ttsModelsList) {
                    const fragment = document.createDocumentFragment();
                    const container = createElementSafely('div', 'status-message error');
                    
                    const errorText = createElementSafely('p', '');
                    const strongText = createElementSafely('strong', '', 'Error loading TTS models');
                    errorText.appendChild(strongText);
                    container.appendChild(errorText);
                    
                    const retryBtn = createElementSafely('button', 'btn btn-secondary retry-btn');
                    retryBtn.setAttribute('data-action', 'loadAudioModels');
                    retryBtn.style.marginTop = '10px';
                    retryBtn.addEventListener('click', loadAudioModels);
                    
                    const btnIcon = createElementSafely('span', 'btn-icon', '🔄');
                    retryBtn.appendChild(btnIcon);
                    retryBtn.appendChild(document.createTextNode(' Retry'));
                    container.appendChild(retryBtn);
                    
                    fragment.appendChild(container);
                    replaceContent(ttsModelsList, fragment);
                }
                if (audioCount) {
                    audioCount.style.display = 'none';
                }
            }

        } catch (error) {
            console.error('Error loading audio models:', error);
            
            // Notify user of the error
            if (window.notificationManager) {
                window.notificationManager.warning('Using cached audio models - connection error');
            }
            
            // Show fallback data instead of error
            const fallbackWhisperModels = [
                { name: 'whisper-tiny', description: 'Fastest Whisper model (39MB)', size: '39 MB', status: 'available' },
                { name: 'whisper-base', description: 'Balanced speed and accuracy (74MB)', size: '74 MB', status: 'available' },
                { name: 'whisper-small', description: 'Better accuracy (244MB)', size: '244 MB', status: 'available' },
                { name: 'whisper-medium', description: 'High accuracy (769MB)', size: '769 MB', status: 'available' },
                { name: 'whisper-large', description: 'Best accuracy (1.55GB)', size: '1.55 GB', status: 'available' }
            ];
            
            const fallbackTtsModels = [
                { name: 'System TTS', description: 'Built-in system text-to-speech', status: 'available' },
                { name: 'Edge TTS', description: 'Microsoft Edge text-to-speech (online)', status: 'requires_internet' }
            ];
            
            if (whisperModelsList) {
                renderAudioModelsList(whisperModelsList, fallbackWhisperModels);
            }
            
            if (ttsModelsList) {
                renderAudioModelsList(ttsModelsList, fallbackTtsModels);
            }
            
            if (audioCount) {
                audioCount.textContent = `(${fallbackWhisperModels.length + fallbackTtsModels.length})`;
                audioCount.style.display = 'inline';
            }
        }
    }

    // Make functions available globally
    window.loadAvailableImageModels = loadAvailableImageModels;
    window.downloadImageModel = downloadImageModel;
    window.loadModels = loadModels;
    window.loadRecommendedModels = loadRecommendedModels;
    window.loadFallbackModels = loadFallbackModels;
    window.loadAudioModels = loadAudioModels;
    window.loadBackendModels = loadBackendModels;
    window.applyBackendModel = applyBackendModel;
    window.loadCurrentBackendModel = loadCurrentBackendModel;
    window.updateBackendModelSelection = updateBackendModelSelection;
    window.updateBackendStatusDisplay = updateBackendStatusDisplay;

    // Comprehensive event delegation for all dynamically created buttons
    document.addEventListener('click', function(e) {
        console.log('Click event detected on:', e.target, 'Classes:', e.target.className);
        
        // Download buttons (both image models and other download buttons)
        if (e.target.classList.contains('download-model-btn') || e.target.closest('.download-model-btn')) {
            console.log('Download button clicked');
            const button = e.target.closest('.download-model-btn');
            const downloadUrl = button.dataset.downloadUrl;
            const filename = button.dataset.filename;
            const modelName = button.dataset.modelName;
            
            console.log('Download data:', { downloadUrl, filename, modelName });
            
            if (downloadUrl && filename && modelName) {
                downloadImageModel(downloadUrl, filename, modelName, e);
            } else {
                console.error('Missing download data:', { downloadUrl, filename, modelName });
                window.notificationManager.showError('Missing download information. Please refresh the page and try again.');
            }
        }
        
        // Pull recommended model buttons
        if (e.target.classList.contains('pull-recommended-btn') || e.target.closest('.pull-recommended-btn')) {
            console.log('Pull recommended button clicked');
            const button = e.target.closest('.pull-recommended-btn');
            const modelName = button.dataset.modelName;
            if (modelName) {
                handlePullRecommendedModel(button, modelName);
            } else {
                console.error('Missing model name for pull button');
                window.notificationManager.showError('Missing model information. Please refresh the page and try again.');
            }
        }
        
        // Delete model buttons
        if (e.target.classList.contains('delete-model-button') || e.target.closest('.delete-model-button')) {
            console.log('Delete button clicked');
            const button = e.target.closest('.delete-model-button');
            const modelName = button.dataset.modelName;
            if (modelName) {
                handleDeleteModel(button, modelName);
            } else {
                window.notificationManager.showError('Missing model information. Please refresh the page and try again.');
            }
        }
        
        // Optimize model buttons
        if (e.target.classList.contains('optimize-model-button') || e.target.closest('.optimize-model-button')) {
            console.log('Optimize button clicked');
            const button = e.target.closest('.optimize-model-button');
            const modelName = button.dataset.modelName;
            if (modelName) {
                openOptimizationModal(modelName);
            } else {
                window.notificationManager.showError('Missing model information. Please refresh the page and try again.');
            }
        }
        
        // Details buttons
        if (e.target.classList.contains('details-btn') || e.target.closest('.details-btn')) {
            console.log('Details button clicked');
            const button = e.target.closest('.details-btn');
            const modelName = button.dataset.modelName;
            const modelType = button.dataset.modelType;
            if (modelName && modelType) {
                showModelDetails(modelName, modelType);
            } else {
                window.notificationManager.showError('Missing model details. Please refresh the page and try again.');
            }
        }
        
        // View details buttons
        if (e.target.classList.contains('view-details-btn') || e.target.closest('.view-details-btn')) {
            console.log('View details button clicked');
            const button = e.target.closest('.view-details-btn');
            const url = button.dataset.url;
            if (url) {
                window.open(url, '_blank');
            } else {
                window.notificationManager.showError('Missing URL for view details. Please refresh the page and try again.');
            }
        }
        
        // Retry buttons
        if (e.target.classList.contains('retry-btn') || e.target.closest('.retry-btn')) {
            console.log('Retry button clicked');
            const button = e.target.closest('.retry-btn');
            const action = button.dataset.action;
            console.log('Retry action:', action);
            if (action === 'loadModels') {
                loadModels();
            } else if (action === 'loadRecommendedModels') {
                loadRecommendedModels();
            } else if (action === 'loadAudioModels') {
                loadAudioModels();
            } else {
                window.notificationManager.showError('Unknown retry action. Please refresh the page and try again.');
            }
        }
        
        // Fallback buttons
        if (e.target.classList.contains('fallback-btn') || e.target.closest('.fallback-btn')) {
            console.log('Fallback button clicked');
            loadFallbackModels();
        }
    });

    // Checkbox event listeners for model comparison
    document.addEventListener('change', function(e) {
        if (e.target.classList.contains('model-compare-checkbox')) {
            const modelName = e.target.dataset.modelName;
            const modelType = e.target.dataset.modelType;
            if (e.target.checked) {
                selectedModelsForComparison.add(`${modelType}:${modelName}`);
            } else {
                selectedModelsForComparison.delete(`${modelType}:${modelName}`);
            }
            updateComparisonControls();
        }
    });

    // Handle pull recommended model
    async function handlePullRecommendedModel(button, modelName) {
        if (!modelName) return;

        button.disabled = true;
        button.textContent = 'Pulling...';

        try {
            const response = await fetch('/api/pull_model', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ model_name: modelName })
            });

            if (!response.ok) {
                throw new Error(`Server error: ${response.status} ${response.statusText}`);
            }

            button.textContent = 'Pulled!';
            setTimeout(() => {
                loadRecommendedModels();
                loadModels();
            }, 2000);

        } catch (err) {
            button.textContent = 'Error';
            button.disabled = false;
            
            // Show error notification
            window.notificationManager.showError(`Failed to pull model: ${err.message}`);
        }
    }

    // Handle delete model
    async function handleDeleteModel(button, modelName) {
        if (!modelName) return;
        if (!confirm(`Are you sure you want to delete model '${modelName}'?`)) return;
        
        const deleteStatus = document.getElementById('delete-status-output');
        if (deleteStatus) {
            deleteStatus.textContent = `Deleting '${modelName}'...`;
        }
        
        try {
            const response = await fetch('/api/delete_model', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ model_name: modelName })
            });
            
            if (!response.ok) {
                const errData = await response.json().catch(() => ({}));
                throw new Error(errData.error || 'Delete failed.');
            }
            
            if (response.headers.get('Content-Type') === 'text/plain') {
                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                if (deleteStatus) {
                    deleteStatus.textContent = '';
                }
                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;
                    if (deleteStatus) {
                        deleteStatus.textContent += decoder.decode(value, { stream: true });
                        deleteStatus.scrollTop = deleteStatus.scrollHeight;
                    }
                }
            } else {
                const data = await response.json();
                if (data.status === 'success') {
                    if (deleteStatus) {
                        deleteStatus.textContent = data.message || 'Model deleted.';
                    }
                    window.notificationManager.showSuccess(`Model '${modelName}' deleted successfully`);
                } else {
                    if (deleteStatus) {
                        deleteStatus.textContent = data.error || 'Delete failed.';
                    }
                    throw new Error(data.error || 'Delete failed.');
                }
            }
        } catch (err) {
            console.error('Delete failed:', err);
            if (deleteStatus) {
                deleteStatus.textContent = `Error: ${err.message}`;
            }
            window.notificationManager.showError(`Failed to delete model: ${err.message}`);
        } finally {
            loadModels();
            loadRecommendedModels();
        }
    }

    // Function to render image models
    function renderImageModels(models) {
        if (!models || models.length === 0) {
            imageModelsList.innerHTML = `
                <div class="status-message">
                    <p>No Stable Diffusion models found.</p>
                    <p>Place .safetensors or .ckpt files in your models directory.</p>
                </div>
            `;
            return;
        }

        const modelsGrid = document.createElement('div');
        modelsGrid.className = 'image-models-grid';

        models.forEach(model => {
            const modelCard = document.createElement('div');
            modelCard.className = 'image-model-card';
            
            // Handle different model data structures and ensure we have valid values
            const modelName = model.name || model.title || model.model_name || model.filename || 'Unknown Model';
            const modelPath = model.path || model.filename || 'Unknown Path';
            const sizeFormatted = model.size ? formatFileSize(model.size) : 'Unknown size';
            
            modelCard.innerHTML = `
                <div class="image-model-name">${modelName}</div>
                <div class="image-model-details">
                    <div class="image-model-size">Size: ${sizeFormatted}</div>
                    <div class="image-model-path" title="${modelPath}">${modelPath}</div>
                </div>
            `;
            
            modelsGrid.appendChild(modelCard);
        });

        imageModelsList.innerHTML = '';
        imageModelsList.appendChild(modelsGrid);
        updateSectionCounts(); // Update tab counts after rendering image models
    }

    // Function to format file size
    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    // Function to open models folder
    async function openModelsFolder() {
        try {
            const response = await fetch('/api/images/open_models_folder', { method: 'POST' });
            const data = await response.json();
            
            if (!data.success) {
                console.error('Error opening models folder:', data.error);
            }
        } catch (error) {
            console.error('Error opening models folder:', error);
        }
    }

    // Function to fetch and display the list of locally available models with detailed metadata
    // Model loading cache with TTL
    const modelCache = new Map();
    const CACHE_TTL = 5 * 60 * 1000; // 5 minutes TTL
    const MAX_CACHE_SIZE = 10;

    // Cache management utilities
    function getCachedData(key) {
        const cached = modelCache.get(key);
        if (cached && Date.now() - cached.timestamp < CACHE_TTL) {
            return cached.data;
        }
        modelCache.delete(key);
        return null;
    }

    function setCachedData(key, data) {
        // Implement simple LRU eviction
        if (modelCache.size >= MAX_CACHE_SIZE) {
            const firstKey = modelCache.keys().next().value;
            modelCache.delete(firstKey);
        }
        modelCache.set(key, {
            data: data,
            timestamp: Date.now()
        });
    }

    // Optimized parallel model loading function
    async function loadAllModelsInParallel() {
        const loadingStartTime = Date.now();
        
        try {
            // Show loading states for all sections
            if (modelsList) {
                modelsList.innerHTML = `
                    <div class="loading-state">
                        <div class="spinner"></div>
                        <p>Loading installed models...</p>
                    </div>
                `;
            }
            
            if (recommendedModelsList) {
                recommendedModelsList.innerHTML = `
                    <div class="loading-state">
                        <div class="loading-spinner"></div>
                        <p>Discovering models from model registry...</p>
                        <small>Loading in parallel for faster performance...</small>
                    </div>
                `;
            }

            // Check cache first
            const cachedInstalled = getCachedData('installed_models');
            const cachedRecommended = getCachedData('recommended_models');
            const cachedAudio = getCachedData('audio_models');

            // Prepare promises array for parallel execution
            const promises = [];
            
            // Only fetch if not cached
            if (!cachedInstalled) {
                promises.push(
                    fetch('/api/models/detailed')
                        .then(res => res.ok ? res.json() : Promise.reject(new Error(`HTTP ${res.status}: ${res.statusText}`)))
                        .then(data => ({ type: 'installed', data: data || [] }))
                        .catch(err => ({ type: 'installed', error: err.message }))
                );
            }

            if (!cachedRecommended) {
                const controller = new AbortController();
                setTimeout(() => controller.abort(), 30000); // 30s timeout
                
                promises.push(
                    fetch('/api/models/recommended', { 
                        signal: controller.signal,
                        headers: { 'Content-Type': 'application/json' }
                    })
                        .then(res => res.ok ? res.json() : Promise.reject(new Error(`HTTP ${res.status}: ${res.statusText}`)))
                        .then(data => ({ type: 'recommended', data: Array.isArray(data) ? data : (data.models || []) }))
                        .catch(err => ({ type: 'recommended', error: err.message }))
                );
            }

            if (!cachedAudio) {
                promises.push(
                    fetch('/api/models/audio')
                        .then(res => res.ok ? res.json() : Promise.reject(new Error(`HTTP ${res.status}: ${res.statusText}`)))
                        .then(data => ({ type: 'audio', data: data.success && data.models ? data.models : [] }))
                        .catch(err => ({ type: 'audio', error: err.message }))
                );
            }

            // Execute all requests in parallel
            const results = await Promise.allSettled(promises);
            
            // Process results and update cache
            let installedModels = cachedInstalled || [];
            let recommendedModels = cachedRecommended || [];
            let audioModels = cachedAudio || [];

            results.forEach(result => {
                if (result.status === 'fulfilled' && result.value) {
                    const { type, data, error } = result.value;
                    
                    if (!error && data) {
                        switch (type) {
                            case 'installed':
                                installedModels = data;
                                setCachedData('installed_models', data);
                                break;
                            case 'recommended':
                                recommendedModels = data;
                                setCachedData('recommended_models', data);
                                break;
                            case 'audio':
                                audioModels = data;
                                setCachedData('audio_models', data);
                                break;
                        }
                    }
                }
            });

            // Render all model types
            processInstalledModels(installedModels);
            processRecommendedModels(recommendedModels);
            processAudioModels(audioModels);
            
            // Update counts
            updateSectionCounts();
            
            const loadTime = ((Date.now() - loadingStartTime) / 1000).toFixed(1);
            console.log(`✅ All models loaded in parallel in ${loadTime}s`);
            
            // Show success notification
            if (window.notificationManager) {
                const totalModels = installedModels.length + recommendedModels.length + audioModels.length;
                window.notificationManager.success(`Loaded ${totalModels} models in ${loadTime}s`);
            }

        } catch (error) {
            console.error('Error in parallel model loading:', error);
            if (window.notificationManager) {
                window.notificationManager.error('Failed to load models. Please try again.');
            }
        }
    }

    // Processing functions for different model types
    function processInstalledModels(models) {
        if (!modelsList) return;
        
        const installedModelsData = models || [];
        if (models && models.length > 0) {
            modelsList.innerHTML = '';
            models.forEach(model => {
                const li = document.createElement('li');
                const modelName = model.name;
                const contextSize = model.context_size || model.n_ctx || 'Unknown';
                const quantLevel = model.quantization_level || 'GGUF';
                const modelType = model.type || 'GGUF';
                const status = model.status || 'available';
                const description = model.description || 'Local GGUF model';
                const modelSize = model.size ? (model.size / (1024 * 1024 * 1024)).toFixed(2) + ' GB' : 'Unknown';
                
                const statusClass = status.toLowerCase();
                
                li.innerHTML = `
                    <div class="model-item">
                        <div class="model-header">
                            <input type="checkbox" class="model-compare-checkbox" data-model-name="${modelName}" data-model-type="installed">
                            <span class="model-name">${modelName}</span>
                            <span class="scraped-badge ${statusClass}" title="Model Status">${status}</span>
                        </div>
                        <p class="model-description">${description}</p>
                        <div class="model-metadata">
                            <div class="model-badges">
                                <span class="badge-label">Type:</span>
                                <span class="badge model-type">${modelType}</span>
                                <span class="badge-label">Quant:</span>
                                <span class="badge quantization">${quantLevel}</span>
                            </div>
                            <div class="model-info">
                                <span class="model-context">Context: ${contextSize} tokens</span>
                                <span class="model-size">Size: ${modelSize}</span>
                            </div>
                        </div>
                        <div class="model-actions">
                            <button class="details-btn" data-model-name="${modelName}" data-model-type="installed">Details</button>
                            <button class="optimize-model-button" data-model-name="${modelName}">Optimize</button>
                            <button class="delete-model-button" data-model-name="${modelName}">Delete</button>
                        </div>
                    </div>
                `;
                modelsList.appendChild(li);
            });
        } else {
            modelsList.innerHTML = `
                <div class="status-message">
                    <p>No local models found. Pull a new one below.</p>
                </div>
            `;
        }
        window.installedModelsData = installedModelsData;
    }

    function processRecommendedModels(models) {
        if (!recommendedModelsList) return;
        
        const recommendedModelsData = models || [];
        if (models && models.length > 0) {
            window.recommendedModelsData = recommendedModelsData;
            displayRecommendedModels(models);
            
            // Show success feedback briefly
            const successMsg = document.createElement('div');
            successMsg.className = 'discovery-success';
            successMsg.innerHTML = `✅ Discovered ${models.length} models from model registry`;
            recommendedModelsList.insertBefore(successMsg, recommendedModelsList.firstChild);
            
            setTimeout(() => {
                if (successMsg.parentNode) {
                    successMsg.remove();
                }
            }, 3000);
        } else {
            recommendedModelsList.innerHTML = `
                <div class="status-message">
                    <p>No recommended models found.</p>
                </div>
            `;
        }
    }

    function processAudioModels(models) {
        const whisperModelsList = document.getElementById('whisper-models-list');
        const ttsModelsList = document.getElementById('tts-models-list');
        const audioCount = document.getElementById('audio-count');
        
        if (models && models.length > 0) {
            // Filter models by type
            const whisperModels = models.filter(model => 
                model.type?.toLowerCase().includes('whisper') ||
                model.name?.toLowerCase().includes('whisper') ||
                model.service?.toLowerCase().includes('transcription')
            );

            const ttsModels = models.filter(model => 
                model.type?.toLowerCase().includes('tts') ||
                model.service?.toLowerCase().includes('tts') ||
                model.service?.toLowerCase().includes('edge')
            );

            // Render models
            if (whisperModelsList) {
                if (whisperModels.length > 0) {
                    renderAudioModelsFromAPI(whisperModelsList, whisperModels, 'Audio transcription model');
                } else {
                    replaceContent(whisperModelsList, createStatusMessage('No Whisper models available'));
                }
            }

            if (ttsModelsList) {
                if (ttsModels.length > 0) {
                    renderAudioModelsFromAPI(ttsModelsList, ttsModels, 'Text-to-speech model');
                } else {
                    replaceContent(ttsModelsList, createStatusMessage('No TTS models available'));
                }
            }

            if (audioCount) {
                const totalModels = whisperModels.length + ttsModels.length;
                audioCount.textContent = totalModels > 0 ? `(${totalModels})` : '';
                audioCount.style.display = totalModels > 0 ? 'inline' : 'none';
            }
        } else {
            // Use fallback data
            const fallbackWhisperModels = [
                { name: 'whisper-tiny', description: 'Fastest Whisper model (39MB)', size: '39 MB', status: 'available' },
                { name: 'whisper-base', description: 'Balanced speed and accuracy (74MB)', size: '74 MB', status: 'available' },
                { name: 'whisper-small', description: 'Better accuracy (244MB)', size: '244 MB', status: 'available' },
                { name: 'whisper-medium', description: 'High accuracy (769MB)', size: '769 MB', status: 'available' },
                { name: 'whisper-large', description: 'Best accuracy (1.55GB)', size: '1.55 GB', status: 'available' }
            ];
            
            const fallbackTtsModels = [
                { name: 'System TTS', description: 'Built-in system text-to-speech', status: 'available' },
                { name: 'Edge TTS', description: 'Microsoft Edge text-to-speech (online)', status: 'requires_internet' }
            ];
            
            if (whisperModelsList) {
                renderAudioModelsList(whisperModelsList, fallbackWhisperModels);
            }
            
            if (ttsModelsList) {
                renderAudioModelsList(ttsModelsList, fallbackTtsModels);
            }
            
            if (audioCount) {
                audioCount.textContent = `(${fallbackWhisperModels.length + fallbackTtsModels.length})`;
                audioCount.style.display = 'inline';
            }
        }
    }

    // Refactored individual loading functions for backward compatibility
    function loadModels() {
        modelsList.innerHTML = `
            <div class="loading-state">
                <div class="spinner"></div>
                <p>Loading installed models...</p>
            </div>
        `;
        fetch('/api/models/detailed')
            .then(res => {
                if (!res.ok) {
                    throw new Error(`Network response was not ok: ${res.statusText}`);
                }
                return res.json();
            })
            .then(models => {
                // Handle case where API returns error object
                if (models && models.error) {
                    throw new Error(models.error);
                }
                
                installedModelsData = models || [];
                modelsList.innerHTML = '';
                if (models && models.length > 0) {
                    models.forEach(model => {
                        const li = document.createElement('li');
                        const modelName = model.name;
                        const contextSize = model.context_size || model.n_ctx || 'Unknown';
                        const quantLevel = model.quantization_level || 'GGUF';
                        const modelType = model.type || 'GGUF';
                        const status = model.status || 'available';
                        const description = model.description || 'Local GGUF model';
                        const modelSize = model.size ? (model.size / (1024 * 1024 * 1024)).toFixed(2) + ' GB' : 'Unknown';
                        
                        const statusClass = status.toLowerCase();
                        
                        li.innerHTML = `
                            <div class="model-item">
                                <div class="model-header">
                                    <input type="checkbox" class="model-compare-checkbox" data-model-name="${modelName}" data-model-type="installed">
                                    <span class="model-name">${modelName}</span>
                                    <span class="scraped-badge ${statusClass}" title="Model Status">${status}</span>
                                </div>
                                <p class="model-description">${description}</p>
                                <div class="model-metadata">
                                    <div class="model-badges">
                                        <span class="badge-label">Type:</span>
                                        <span class="badge model-type">${modelType}</span>
                                        <span class="badge-label">Quant:</span>
                                        <span class="badge quantization">${quantLevel}</span>
                                    </div>
                                    <div class="model-info">
                                        <span class="model-context">Context: ${contextSize} tokens</span>
                                        <span class="model-size">Size: ${modelSize}</span>
                                    </div>
                                </div>
                                <div class="model-actions">
                                    <button class="details-btn" data-model-name="${modelName}" data-model-type="installed">Details</button>
                                    <button class="optimize-model-button" data-model-name="${modelName}">Optimize</button>
                                    <button class="delete-model-button" data-model-name="${modelName}">Delete</button>
                                </div>
                            </div>
                        `;
                        modelsList.appendChild(li);
                    });
                } else {
                    modelsList.innerHTML = `
                        <div class="status-message">
                            <p>No local models found. Pull a new one below.</p>
                        </div>
                    `;
                }
                updateSectionCounts(); // Update tab counts after loading models
            })
            .catch(err => {
                console.error('Error loading models:', err);
                modelsList.innerHTML = `
                    <div class="status-message error">
                        <p><strong>Error loading models.</strong></p>
                        <p>Is the LLM backend running?</p>
                        <p><em>Error:</em> ${err.message}</p>
                        <button class="btn btn-secondary retry-btn" data-action="loadModels" style="margin-top: 10px;">
                            <span class="btn-icon">🔄</span>
                            Retry
                        </button>
                    </div>
                `;
                updateSectionCounts(); // Update tab counts even on error
            });
    }

    // Function to load recommended models with timeout handling
    function loadRecommendedModels() {
        // Show loading state with progress indication
        recommendedModelsList.innerHTML = `
            <div class="loading-state">
                <div class="loading-spinner"></div>
                <p>Discovering models from model registry...</p>
                <small>This may take a few moments while we fetch the latest models</small>
            </div>
        `;
        
        const startTime = Date.now();
        const timeoutDuration = 30000; // 30 seconds timeout
        
        // Create AbortController for timeout
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), timeoutDuration);
        
        fetch('/api/models/recommended', { 
            signal: controller.signal,
            headers: {
                'Content-Type': 'application/json'
            }
        })
            .then(res => {
                clearTimeout(timeoutId);
                if (!res.ok) {
                    throw new Error(`Network response was not ok: ${res.status} ${res.statusText}`);
                }
                return res.json();
            })
            .then(data => {
                // Handle case where API returns error object
                if (data && data.error) {
                    throw new Error(data.error);
                }
                
                const loadTime = ((Date.now() - startTime) / 1000).toFixed(1);
                const models = Array.isArray(data) ? data : (data.models || []);
                console.log(`Loaded ${models.length} models in ${loadTime}s`);
                
                recommendedModelsData = models;
                displayRecommendedModels(models);
                
                // Show success feedback briefly
                const successMsg = document.createElement('div');
                successMsg.className = 'discovery-success';
                successMsg.innerHTML = `✅ Discovered ${models.length} models from model registry`;
                recommendedModelsList.insertBefore(successMsg, recommendedModelsList.firstChild);
                
                setTimeout(() => {
                    if (successMsg.parentNode) {
                        successMsg.remove();
                    }
                }, 3000);
            })
            .catch(err => {
                clearTimeout(timeoutId);
                console.error('Error loading recommended models:', err);
                
                const isTimeout = err.name === 'AbortError';
                const errorMessage = isTimeout ? 'Request timed out after 30 seconds' : err.message;
                
                recommendedModelsList.innerHTML = `
                    <div class="error-state">
                        <h3>⚠️ Discovery Error</h3>
                        <p>Failed to fetch models from registry.</p>
                        <p><strong>Error:</strong> ${errorMessage}</p>
                        <div class="error-actions">
                            <button class="retry-btn" data-action="loadRecommendedModels">🔄 Retry Discovery</button>
                            <button class="fallback-btn">📦 Load Local Curated Models</button>
                        </div>
                        <details>
                            <summary>Troubleshooting</summary>
                            <ul>
                                <li>Check your internet connection</li>
                                <li>Verify model registry is accessible</li>
                                <li>Try refreshing the page</li>
                                <li>Local curated models are available as fallback</li>
                                ${isTimeout ? '<li>Server may be experiencing high load - try again later</li>' : ''}
                            </ul>
                        </details>
                    </div>
                `;
            });
    }

    // Function to display recommended models with virtualization for performance
    function displayRecommendedModels(models) {
        if (!models || models.length === 0) {
            recommendedModelsList.innerHTML = `
                <div class="status-message">
                    <p>No recommended models found.</p>
                </div>
            `;
            return;
        }

        // Store models globally for pagination
        window.allRecommendedModels = models;
        window.currentPage = 0;
        window.modelsPerPage = 20; // Show 20 models at a time
        
        // Clear container and add pagination controls
        recommendedModelsList.innerHTML = `
            <div class="models-pagination-controls">
                <div class="pagination-info">
                    Showing <span id="models-range">1-${Math.min(window.modelsPerPage, models.length)}</span> of ${models.length} models
                </div>
                <div class="pagination-buttons">
                    <button id="prev-page-btn" class="btn btn-secondary btn-sm" disabled>
                        <span class="btn-icon">←</span> Previous
                    </button>
                    <button id="next-page-btn" class="btn btn-secondary btn-sm" ${models.length <= window.modelsPerPage ? 'disabled' : ''}>
                        Next <span class="btn-icon">→</span>
                    </button>
                </div>
            </div>
            <div id="models-container"></div>
        `;
        
        // Render first page
        renderModelsPage(0);
        
        // Add pagination event listeners
        const prevBtn = document.getElementById('prev-page-btn');
        const nextBtn = document.getElementById('next-page-btn');
        
        if (prevBtn) {
            prevBtn.addEventListener('click', () => {
                if (window.currentPage > 0) {
                    window.currentPage--;
                    renderModelsPage(window.currentPage);
                }
            });
        }
        
        if (nextBtn) {
            nextBtn.addEventListener('click', () => {
                const maxPage = Math.ceil(models.length / window.modelsPerPage) - 1;
                if (window.currentPage < maxPage) {
                    window.currentPage++;
                    renderModelsPage(window.currentPage);
                }
            });
        }
    }
    
    // Function to render a specific page of models
    function renderModelsPage(page) {
        const modelsContainer = document.getElementById('models-container');
        const startIndex = page * window.modelsPerPage;
        const endIndex = Math.min(startIndex + window.modelsPerPage, window.allRecommendedModels.length);
        const pageModels = window.allRecommendedModels.slice(startIndex, endIndex);
        
        // Clear container
        modelsContainer.innerHTML = '';
        
        // Render models with performance optimization
        const fragment = document.createDocumentFragment();
        
        pageModels.forEach(model => {
            // Validate model data structure
            if (!model || typeof model !== 'object') {
                console.warn('Invalid model data:', model);
                return;
            }
            
            const modelCard = document.createElement('div');
            modelCard.className = 'recommended-model-card';
            
            // Add defensive check for categories array
            const categoriesList = (model.categories && Array.isArray(model.categories)) 
                ? model.categories.join(', ') 
                : 'General';
            const loadClass = (model.pc_load || 'Medium').toLowerCase().replace(/\s+/g, '-');
            const fidelityClass = (model.fidelity || 'Standard').toLowerCase().replace(/\s+/g, '-');
            
            // Determine data source and create appropriate badge
            let sourceBadge = '';
            if (model.scraped === true && model.source === 'huggingface') {
                sourceBadge = '<span class="model-source-badge hf-scraped">🤗 HuggingFace</span>';
            } else if (model.scraped === false && model.source === 'parsed') {
                sourceBadge = '<span class="model-source-badge parsed-data">🧠 Smart Parsed</span>';
            } else if (model.source === 'fallback') {
                sourceBadge = '<span class="model-source-badge fallback-data">⚠️ Limited Info</span>';
            } else {
                // Legacy fallback for older data format
                const isCurated = model.description !== 'No detailed description available.';
                sourceBadge = isCurated ? 
                    '<span class="model-source-badge curated">📚 Curated</span>' : 
                    '<span class="model-source-badge live">🌐 Live</span>';
            }
            
            // Format live metadata if available
            let liveMetadata = '';
            if (model.digest || model.modified_at) {
                liveMetadata = `
                    <div class="model-live-metadata">
                        ${model.digest ? `<div><strong>Digest:</strong> <span class="digest">${model.digest.substring(0, 12)}...</span></div>` : ''}
                        ${model.modified_at ? `<div><strong>Last Updated:</strong> ${new Date(model.modified_at).toLocaleDateString()}</div>` : ''}
                    </div>
                `;
            }
            
            // Validate required fields with fallbacks
            const modelName = model.full_name || model.name || 'Unknown Model';
            const modelDescription = model.description || 'No description available';
            const modelFidelity = model.fidelity || 'Standard';
            const modelLoad = model.pc_load || 'Medium';
            const modelSize = model.size || '';
            const isUncensored = Boolean(model.uncensored);
            
            modelCard.innerHTML = `
                ${sourceBadge}
                <div class="model-card-header">
                    <div class="model-title-row">
                        <input type="checkbox" class="model-compare-checkbox" data-model-name="${modelName}" data-model-type="recommended">
                        <h4 class="model-title">${modelName}</h4>
                        ${isUncensored ? '<span class="uncensored-badge">🔓 Uncensored</span>' : ''}
                    </div>
                    <div class="model-badges">
                        <span class="badge-label">Fidelity:</span>
                        <span class="badge fidelity-${fidelityClass}">${modelFidelity}</span>
                        <span class="badge-label">Load:</span>
                        <span class="badge load-${loadClass}">${modelLoad}</span>
                        ${modelSize ? `<span class="badge-label">Size:</span><span class="badge size">${modelSize}</span>` : ''}
                    </div>
                </div>
                <p class="model-description">${modelDescription}</p>
                <div class="model-metadata">
                    <div class="model-categories">
                        <strong>Categories:</strong> ${categoriesList || 'General'}
                    </div>
                    <div class="model-context">
                        <strong>Context:</strong> ${model.context_display || (model.n_ctx ? (typeof model.n_ctx === 'number' ? model.n_ctx.toLocaleString() + ' tokens' : model.n_ctx + ' tokens') : 'Unknown')}
                        ${model.usage_count ? `<span class="usage-info">• Used ${model.usage_count} times</span>` : ''}
                    </div>
                    ${(model.languages && Array.isArray(model.languages) && model.languages.length > 0) ? `
                    <div class="model-languages">
                        <strong>Languages:</strong> ${model.languages.slice(0, 4).join(', ')}${model.languages.length > 4 ? ` +${model.languages.length - 4} more` : ''}
                    </div>` : ''}
                    ${(model.strengths && Array.isArray(model.strengths) && model.strengths.length > 0) ? `
                    <div class="model-strengths">
                        <strong>Strengths:</strong> ${model.strengths.slice(0, 3).join(', ')}${model.strengths.length > 3 ? '...' : ''}
                    </div>` : ''}
                </div>
                ${liveMetadata}
                <div class="model-actions">
                    <button class="details-btn" data-model-name="${modelName}" data-model-type="recommended">Details</button>
                    ${model.is_installed ? 
                        '<span class="installed-badge">✓ Installed</span>' : 
                        `<button class="pull-recommended-btn" data-model-name="${modelName}">Pull Model</button>`
                    }
                </div>
            `;
            
            fragment.appendChild(modelCard);
        });
        
        // Append all models at once for better performance
        modelsContainer.appendChild(fragment);
        
        // Update pagination controls
        updatePaginationControls();
    }
    
    // Function to update pagination controls
    function updatePaginationControls() {
        const rangeSpan = document.getElementById('models-range');
        const prevBtn = document.getElementById('prev-page-btn');
        const nextBtn = document.getElementById('next-page-btn');
        
        if (rangeSpan) {
            const startIndex = window.currentPage * window.modelsPerPage + 1;
            const endIndex = Math.min((window.currentPage + 1) * window.modelsPerPage, window.allRecommendedModels.length);
            rangeSpan.textContent = `${startIndex}-${endIndex}`;
        }
        
        if (prevBtn) {
            prevBtn.disabled = window.currentPage === 0;
        }
        
        if (nextBtn) {
            const maxPage = Math.ceil(window.allRecommendedModels.length / window.modelsPerPage) - 1;
            nextBtn.disabled = window.currentPage >= maxPage;
        }
    }

    // Model details view functions
    function showModelDetails(modelName, modelType) {
        let modelData = null;
        
        if (modelType === 'installed') {
            modelData = installedModelsData.find(m => m.name === modelName);
        } else {
            modelData = recommendedModelsData.find(m => m.full_name === modelName);
        }
        
        if (!modelData) {
            console.error('Model data not found:', modelName);
            return;
        }
        
        const detailsContent = document.getElementById('model-details-content');
        const displayName = modelType === 'recommended' ? modelData.full_name : modelData.name;
        
        detailsContent.innerHTML = `
            <div class="model-details-view">
                <h4>${displayName}</h4>
                ${modelData.uncensored ? '<span class="uncensored-badge">🔓 Uncensored</span>' : ''}
                
                <div class="detail-section">
                    <h5>Description</h5>
                    <p>${modelData.description || 'No description available'}</p>
                </div>
                
                <div class="detail-section">
                    <h5>Technical Specifications</h5>
                    <div class="detail-grid">
                        <div class="detail-item">
                            <span class="detail-label">Fidelity:</span>
                            <span class="badge fidelity-${(modelData.fidelity || '').toLowerCase().replace(/\s+/g, '-')}">${modelData.fidelity || 'Unknown'}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">PC Load:</span>
                            <span class="badge load-${(modelData.pc_load || '').toLowerCase().replace(/\s+/g, '-')}">${modelData.pc_load || 'Unknown'}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Context Window:</span>
                            <span>${modelData.context_display || (modelData.n_ctx ? (typeof modelData.n_ctx === 'number' ? modelData.n_ctx.toLocaleString() + ' tokens' : modelData.n_ctx + ' tokens') : 'Unknown')}</span>
                        </div>
                        ${(modelType === 'installed' && modelData.size) ? `
                        <div class="detail-item">
                            <span class="detail-label">File Size:</span>
                            <span>${formatFileSize(modelData.size)}</span>
                        </div>` : (modelData.size_gb ? `
                        <div class="detail-item">
                            <span class="detail-label">Download Size:</span>
                            <span>${modelData.size_gb} GB</span>
                        </div>` : '')}
                    </div>
                </div>
                
                <div class="detail-section">
                    <h5>Categories</h5>
                    <div class="categories-list">
                        ${(modelData.categories || []).map(cat => `<span class="category-tag">${cat}</span>`).join('')}
                    </div>
                </div>
                
                ${modelData.languages && modelData.languages.length > 0 ? `
                <div class="detail-section">
                    <h5>Supported Languages</h5>
                    <div class="languages-list">
                        ${modelData.languages.map(lang => `<span class="language-tag">${lang}</span>`).join('')}
                    </div>
                </div>` : ''}
                
                ${modelData.strengths && modelData.strengths.length > 0 ? `
                <div class="detail-section">
                    <h5>Key Strengths</h5>
                    <ul class="strengths-list">
                        ${modelData.strengths.map(strength => `<li>${strength}</li>`).join('')}
                    </ul>
                </div>` : ''}
                
                ${modelData.use_cases && modelData.use_cases.length > 0 ? `
                <div class="detail-section">
                    <h5>Use Cases</h5>
                    <ul class="use-cases-list">
                        ${modelData.use_cases.map(useCase => `<li>${useCase}</li>`).join('')}
                    </ul>
                </div>` : ''}
                
                ${modelType === 'installed' && modelData.download_timestamp ? `
                <div class="detail-section">
                    <h5>Download Information</h5>
                    <p>Downloaded: ${new Date(modelData.download_timestamp).toLocaleString()}</p>
                </div>` : ''}
            </div>
        `;
        
        modelDetailsModal.style.display = 'block';
    }

    // Model comparison functions
    function updateComparisonControls() {
        const count = selectedModelsForComparison.size;
        compareSelectedBtn.textContent = `Compare Selected Models (${count})`;
        compareSelectedBtn.disabled = count < 2;
    }

    // toggleModelSelection function removed as it was unused

    function showModelComparison() {
        if (selectedModelsForComparison.size < 2) return;
        
        const compareContent = document.getElementById('model-compare-content');
        const modelsToCompare = [];
        
        // Gather data for selected models
        selectedModelsForComparison.forEach(key => {
            const [type, name] = key.split(':');
            let modelData;
            
            if (type === 'installed') {
                modelData = installedModelsData.find(m => m.name === name);
            } else {
                modelData = recommendedModelsData.find(m => m.full_name === name);
            }
            
            if (modelData) {
                modelsToCompare.push({
                    ...modelData,
                    displayName: type === 'recommended' ? modelData.full_name : modelData.name,
                    type: type
                });
            }
        });
        
        // Create comparison table
        let comparisonHTML = `
            <div class="comparison-grid">
                <div class="comparison-row comparison-header">
                    <div class="comparison-label">Model</div>
                    ${modelsToCompare.map(model => `<div class="comparison-value"><strong>${model.displayName}</strong></div>`).join('')}
                </div>
                
                <div class="comparison-row">
                    <div class="comparison-label">Description</div>
                    ${modelsToCompare.map(model => `<div class="comparison-value">${model.description || 'N/A'}</div>`).join('')}
                </div>
                
                <div class="comparison-row">
                    <div class="comparison-label">Fidelity</div>
                    ${modelsToCompare.map(model => `
                        <div class="comparison-value">
                            <span class="badge fidelity-${(model.fidelity || '').toLowerCase().replace(/\s+/g, '-')}">${model.fidelity || 'Unknown'}</span>
                        </div>
                    `).join('')}
                </div>
                
                <div class="comparison-row">
                    <div class="comparison-label">PC Load</div>
                    ${modelsToCompare.map(model => `
                        <div class="comparison-value">
                            <span class="badge load-${(model.pc_load || '').toLowerCase().replace(/\s+/g, '-')}">${model.pc_load || 'Unknown'}</span>
                        </div>
                    `).join('')}
                </div>
                
                <div class="comparison-row">
                    <div class="comparison-label">Context Window</div>
                    ${modelsToCompare.map(model => `<div class="comparison-value">${model.n_ctx || 0} tokens</div>`).join('')}
                </div>
                
                <div class="comparison-row">
                    <div class="comparison-label">Categories</div>
                    ${modelsToCompare.map(model => `<div class="comparison-value">${(model.categories || []).join(', ') || 'N/A'}</div>`).join('')}
                </div>
                
                <div class="comparison-row">
                    <div class="comparison-label">Uncensored</div>
                    ${modelsToCompare.map(model => `<div class="comparison-value">${model.uncensored ? '🔓 Yes' : '❌ No'}</div>`).join('')}
                </div>
                
                <div class="comparison-row">
                    <div class="comparison-label">Status</div>
                    ${modelsToCompare.map(model => `
                        <div class="comparison-value">
                            ${model.type === 'installed' ? 
                                '<span class="installed-badge">✓ Installed</span>' : 
                                (model.is_installed ? '<span class="installed-badge">✓ Installed</span>' : '<span class="not-installed-badge">Not Installed</span>')
                            }
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
        
        compareContent.innerHTML = comparisonHTML;
        modelCompareModal.style.display = 'block';
    }

    // Filter and sort functions with performance optimizations
    let filterTimeout = null;
    let currentSortBy = null;
    let currentSortOrder = 'asc';
    
    function filterAndSortRecommendedModels() {
        // Clear existing timeout to debounce rapid input
        if (filterTimeout) {
            clearTimeout(filterTimeout);
        }
        
        // Debounce the filtering to avoid excessive re-renders
        filterTimeout = setTimeout(() => {
            performFilterAndSort();
        }, 300);
    }
    
    function performFilterAndSort() {
        if (!window.allRecommendedModels) {
            return; // No models loaded yet
        }
        
        // Get filter values once
        const searchTerm = searchInput.value.toLowerCase().trim();
        const selectedCategory = categoryFilter.value;
        const selectedLoad = loadFilter.value;
        
        // Apply filters efficiently
        let filteredModels = window.allRecommendedModels.filter(model => {
            // Search filter
            if (searchTerm) {
                const nameMatch = model.name && model.name.toLowerCase().includes(searchTerm);
                const descMatch = model.description && model.description.toLowerCase().includes(searchTerm);
                const catMatch = model.categories && Array.isArray(model.categories) && 
                    model.categories.some(cat => cat && cat.toLowerCase().includes(searchTerm));
                
                if (!nameMatch && !descMatch && !catMatch) {
                    return false;
                }
            }
            
            // Category filter
            if (selectedCategory && (!model.categories || !model.categories.includes(selectedCategory))) {
                return false;
            }
            
            // Load filter
            if (selectedLoad && model.pc_load !== selectedLoad) {
                return false;
            }
            
            return true;
        });
        
        // Apply current sort if any
        if (currentSortBy) {
            filteredModels = sortModels(filteredModels, currentSortBy, currentSortOrder);
        }
        
        // Update global models and re-render
        window.allRecommendedModels = filteredModels;
        window.currentPage = 0; // Reset to first page
        renderModelsPage(0);
    }
    
    function sortModels(models, sortBy, order = 'asc') {
        const sortedModels = [...models]; // Create copy to avoid mutating original
        
        const loadOrder = { 'Very Low': 1, 'Low': 2, 'Medium': 3, 'High': 4 };
        
        sortedModels.sort((a, b) => {
            let comparison = 0;
            
            if (sortBy === 'name') {
                const nameA = (a.name || '').toLowerCase();
                const nameB = (b.name || '').toLowerCase();
                comparison = nameA.localeCompare(nameB);
            } else if (sortBy === 'load') {
                const loadA = loadOrder[a.pc_load] || 0;
                const loadB = loadOrder[b.pc_load] || 0;
                comparison = loadA - loadB;
            }
            
            return order === 'desc' ? -comparison : comparison;
        });
        
        return sortedModels;
    }
    
    function sortRecommendedModels(sortBy) {
        // Toggle sort order if same sort is clicked
        if (currentSortBy === sortBy) {
            currentSortOrder = currentSortOrder === 'asc' ? 'desc' : 'asc';
        } else {
            currentSortBy = sortBy;
            currentSortOrder = 'asc';
        }
        
        // Update button states to show current sort
        updateSortButtonStates();
        
        // Re-apply filters and sort
        performFilterAndSort();
    }
    
    function updateSortButtonStates() {
        // Reset all sort buttons
        const sortButtons = document.querySelectorAll('[data-sort]');
        sortButtons.forEach(btn => {
            btn.classList.remove('active', 'asc', 'desc');
        });
        
        // Highlight current sort button
        if (currentSortBy) {
            const activeBtn = document.querySelector(`[data-sort="${currentSortBy}"]`);
            if (activeBtn) {
                activeBtn.classList.add('active', currentSortOrder);
            }
        }
    }

    // Modal functions
    function openOptimizationModal(modelName) {
        currentBaseModel = modelName;
        baseModelNameSpan.textContent = modelName;
        updateModelNamePreview();
        optimizationModal.style.display = 'block';
        optimizationStatus.textContent = '';
    }

    function closeOptimizationModal() {
        optimizationModal.style.display = 'none';
        currentBaseModel = '';
        gpuLayersInput.value = 0;
        cpuThreadsInput.value = 4;
        updateSliderValues();
    }

    function updateModelNamePreview() {
        const gpuLayers = parseInt(gpuLayersInput.value);
        const cpuThreads = parseInt(cpuThreadsInput.value);
        const gpuSuffix = gpuLayers > 0 ? `gpu${gpuLayers}` : 'cpu';
        const threadSuffix = `t${cpuThreads}`;
        const newName = `${currentBaseModel}-opt-${gpuSuffix}-${threadSuffix}`;
        newModelNamePreview.textContent = newName;
    }

    function updateSliderValues() {
        gpuLayersValue.textContent = gpuLayersInput.value;
        cpuThreadsValue.textContent = cpuThreadsInput.value;
        updateModelNamePreview();
    }

    // Event listeners
    searchInput.addEventListener('input', filterAndSortRecommendedModels);
    categoryFilter.addEventListener('change', filterAndSortRecommendedModels);
    loadFilter.addEventListener('change', filterAndSortRecommendedModels);
    sortNameBtn.addEventListener('click', () => sortRecommendedModels('name'));
    sortLoadBtn.addEventListener('click', () => sortRecommendedModels('load'));
    
    // Refresh discovery button
    const refreshDiscoveryBtn = document.getElementById('refresh-discovery-btn');
    if (refreshDiscoveryBtn) {
        refreshDiscoveryBtn.addEventListener('click', function() {
            console.log('Refreshing model discovery...');
            loadRecommendedModels();
        });
    }

    // Comparison event listeners
    compareSelectedBtn.addEventListener('click', showModelComparison);
    clearSelectionBtn.addEventListener('click', function() {
        selectedModelsForComparison.clear();
        document.querySelectorAll('.model-compare-checkbox').forEach(cb => cb.checked = false);
        updateComparisonControls();
    });

    // Modal event listeners
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('close-modal') || e.target.id === 'close-details-btn') {
            modelDetailsModal.style.display = 'none';
        }
        if (e.target.classList.contains('close-modal') || e.target.id === 'close-compare-btn') {
            modelCompareModal.style.display = 'none';
        }
        if (e.target === optimizationModal) {
            closeOptimizationModal();
        }
        if (e.target === modelDetailsModal) {
            modelDetailsModal.style.display = 'none';
        }
        if (e.target === modelCompareModal) {
            modelCompareModal.style.display = 'none';
        }
    });

    cancelOptimizationBtn.addEventListener('click', closeOptimizationModal);
    gpuLayersInput.addEventListener('input', updateSliderValues);
    cpuThreadsInput.addEventListener('input', updateSliderValues);





    // Event listener for optimization
    createOptimizedBtn.addEventListener('click', async function() {
        if (!currentBaseModel) return;

        const numGpuLayers = parseInt(gpuLayersInput.value);
        const numThreads = parseInt(cpuThreadsInput.value);

        createOptimizedBtn.disabled = true;
        createOptimizedBtn.textContent = 'Creating...';
        optimizationStatus.textContent = 'Creating optimized model...';

        try {
            const response = await fetch('/api/optimize_model', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    base_model_name: currentBaseModel,
                    num_gpu_layers: numGpuLayers,
                    num_threads: numThreads
                })
            });

            const result = await response.json();

            if (response.ok && result.status === 'success') {
                optimizationStatus.textContent = result.message;
                setTimeout(() => {
                    closeOptimizationModal();
                    loadModels();
                }, 2000);
            } else {
                optimizationStatus.textContent = `Error: ${result.error}`;
            }

        } catch (err) {
            console.error('Optimization failed:', err);
            optimizationStatus.textContent = `Error: ${err.message}`;
        } finally {
            createOptimizedBtn.disabled = false;
            createOptimizedBtn.textContent = 'Create Optimized Model';
        }
    });



    // Event listener for the "Pull Model" button
    pullBtn.addEventListener('click', async function() {
        const modelName = modelInput.value.trim();
        if (!modelName) {
            pullStatus.textContent = 'Please enter a model name.';
            return;
        }

        pullBtn.disabled = true;
        modelInput.disabled = true;
        pullStatus.textContent = `Attempting to pull '${modelName}'...`;

        try {
            const response = await fetch('/api/pull_model', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ model_name: modelName })
            });

            if (!response.ok) {
                throw new Error(`Server error: ${response.status} ${response.statusText}`);
            }
            if (!response.body) {
                throw new Error('Response body is missing.');
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            
            pullStatus.textContent = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) {
                    pullStatus.textContent += '\n\n--- Pull complete! ---';
                    break;
                }
                const chunk = decoder.decode(value, { stream: true });
                pullStatus.textContent += chunk;
                pullStatus.scrollTop = pullStatus.scrollHeight;
            }

        } catch (err) {
            console.error('Pull failed:', err);
            pullStatus.textContent = `Error: ${err.message}`;
        } finally {
            pullBtn.disabled = false;
            modelInput.disabled = false;
            modelInput.value = '';
            loadModels();
            loadRecommendedModels();
        }
    });



    // Function to load fallback models when main loading fails
    function loadFallbackModels() {
        console.log('Loading fallback models...');
        
        // Basic fallback models list
        const fallbackModels = [
            {
                name: 'llama3.2',
                tag: '3b',
                full_name: 'llama3.2:3b',
                description: 'Latest Meta Llama 3.2 model optimized for efficiency and performance',
                fidelity: 'High',
                pc_load: 'Low',
                categories: ['Chat', 'Reasoning', 'Creative'],
                n_ctx: 128000,
                context_display: '128,000 tokens',
                size: '2.0 GB',
                uncensored: false,
                languages: ['English', 'Spanish', 'French', 'German'],
                strengths: ['Conversational AI', 'Creative writing', 'Code assistance'],
                use_cases: ['General chat', 'Content creation', 'Q&A'],
                scraped: false,
                source: 'fallback'
            },
            {
                name: 'phi3',
                tag: 'mini',
                full_name: 'phi3:mini',
                description: 'Microsoft\'s compact yet powerful model with enterprise-grade safety',
                fidelity: 'High',
                pc_load: 'Very Low',
                categories: ['Chat', 'Business', 'Efficiency'],
                n_ctx: 128000,
                context_display: '128,000 tokens',
                size: '2.3 GB',
                uncensored: false,
                languages: ['English'],
                strengths: ['Efficiency', 'Enterprise safety', 'Business tasks'],
                use_cases: ['Business automation', 'Quick responses', 'Enterprise apps'],
                scraped: false,
                source: 'fallback'
            },
            {
                name: 'mistral',
                tag: '7b',
                full_name: 'mistral:7b',
                description: 'Mistral AI\'s flagship model with excellent instruction following',
                fidelity: 'High',
                pc_load: 'Medium',
                categories: ['Chat', 'Reasoning', 'Creative'],
                n_ctx: 32768,
                context_display: '32,768 tokens',
                size: '4.1 GB',
                uncensored: false,
                languages: ['English', 'French', 'German', 'Spanish'],
                strengths: ['Instruction following', 'Creative writing', 'Reasoning'],
                use_cases: ['General assistance', 'Creative projects', 'Professional writing'],
                scraped: false,
                source: 'fallback'
            }
        ];
        
        recommendedModelsData = fallbackModels;
        displayRecommendedModels(fallbackModels);
        
        // Show fallback notice
        const fallbackNotice = document.createElement('div');
        fallbackNotice.className = 'fallback-notice';
        fallbackNotice.innerHTML = `
            <div class="notice-content">
                <span class="notice-icon">📦</span>
                <span class="notice-text">Showing local curated models. <a href="#" onclick="loadRecommendedModels(); return false;">Try loading from registry again</a></span>
            </div>
        `;
        recommendedModelsList.insertBefore(fallbackNotice, recommendedModelsList.firstChild);
    }

    // Make loadFallbackModels available globally
    window.loadFallbackModels = loadFallbackModels;

    // Initial load - only update controls, let section toggles handle data loading
    updateComparisonControls();
    
    // Initialize backend models with proper sequencing
    Promise.resolve()
        .then(() => loadBackendModels())
        .catch(error => console.error('Error loading backend models:', error))
        .then(() => {
            // Image Models functionality
            initializeImageModels();
        })
        .catch(error => console.error('Error initializing image models:', error));
});

// Image Models functionality  
function initializeImageModels() {
    // Unused loadSDStatus function removed
    

    
    // Event listeners are already handled in the main event listener section above





    // Audio studio button handler
    const openAudioStudioBtn = document.getElementById('open-audio-studio');
    const testAudioModelsBtn = document.getElementById('test-audio-models');

    openAudioStudioBtn?.addEventListener('click', () => {
        window.location.href = '/audio_studio';
    });

    testAudioModelsBtn?.addEventListener('click', () => {
        alert('Audio model testing functionality will be implemented in a future update.');
    });
    
    // DISABLED: Initial load - preventing content overwrite
    // loadSDStatus();
}

// Backend Model Selection Functions
async function loadBackendModels() {
    try {
        const response = await fetch('/api/models/available');
        const data = await response.json();
        
        // API returns array directly, not wrapped in success object
        if (Array.isArray(data) && data.length > 0) {
            updateBackendModelSelection(data);
        } else {
            console.error('No backend models available:', data);
            updateBackendModelSelection([]);
        }
    } catch (error) {
        console.error('Error loading backend models:', error);
        updateBackendModelSelection([]);
    }
}

function updateBackendModelSelection(models) {
    const select = document.getElementById('backend-model-select');
    const applyButton = document.getElementById('apply-backend-model');
    
    if (!select) return;
    
    // Clear existing options
    select.innerHTML = '<option value="">Select a model...</option>';
    
    // Add model options
    models.forEach(model => {
        const option = document.createElement('option');
        option.value = model.name;
        
        // Format display text with available information
        let displayText = model.name;
        if (model.size) {
            const sizeInMB = Math.round(model.size / (1024 * 1024));
            displayText += ` (${sizeInMB}MB)`;
        }
        if (model.n_ctx) {
            displayText += ` - ${model.n_ctx} context`;
        }
        
        option.textContent = displayText;
        select.appendChild(option);
    });
    
    // Load current backend model
    loadCurrentBackendModel();
    
    // Set up event listeners
    select.addEventListener('change', function() {
        if (applyButton) applyButton.disabled = !this.value;
    });
    
    if (applyButton) {
        applyButton.addEventListener('click', applyBackendModel);
    }
}

// Cache for backend status to prevent redundant API calls
let backendStatusCache = null;
let backendStatusCacheTime = 0;
const BACKEND_STATUS_CACHE_DURATION = 5000; // 5 seconds cache
let backendStatusLoading = false;

async function loadCurrentBackendModel(forceRefresh = false) {
    // Prevent concurrent calls
    if (backendStatusLoading && !forceRefresh) {
        return;
    }
    
    // Check cache first
    const now = Date.now();
    if (!forceRefresh && backendStatusCache && (now - backendStatusCacheTime) < BACKEND_STATUS_CACHE_DURATION) {
        updateBackendStatusDisplay(backendStatusCache);
        return;
    }
    
    backendStatusLoading = true;
    
    try {
        const response = await fetch('/api/models/backend_status');
        const data = await response.json();
        
        console.log('Backend status response:', data); // Debug logging
        
        // Cache the successful response
        if (data.success) {
            backendStatusCache = data;
            backendStatusCacheTime = now;
        }
        
        updateBackendStatusDisplay(data);
        
    } catch (error) {
        console.error('Error loading current backend model:', error);
        const modelName = document.querySelector('#current-backend-model .model-name');
        const modelStatus = document.querySelector('#current-backend-model .model-status');
        if (modelName) modelName.textContent = 'Connection Error';
        if (modelStatus) modelStatus.textContent = 'Cannot connect to backend';
    } finally {
        backendStatusLoading = false;
    }
}

function updateBackendStatusDisplay(data) {
    const modelName = document.querySelector('#current-backend-model .model-name');
    const modelStatus = document.querySelector('#current-backend-model .model-status');
    const select = document.getElementById('backend-model-select');
    
    if (data.success) {
        const currentModel = data.current_model || 'No model loaded';
        const status = data.status || 'Ready';
        
        console.log('Setting current model:', currentModel, 'status:', status); // Debug
        
        if (modelName) modelName.textContent = currentModel;
        if (modelStatus) modelStatus.textContent = `Status: ${status}`;
        
        // Try to match model in dropdown
        if (select && currentModel !== 'No model loaded') {
            // Look for exact match or partial match
            const options = Array.from(select.options);
            const exactMatch = options.find(opt => opt.value === currentModel);
            const partialMatch = options.find(opt => opt.textContent.includes(currentModel) || currentModel.includes(opt.value));
            
            if (exactMatch) {
                select.value = exactMatch.value;
            } else if (partialMatch) {
                select.value = partialMatch.value;
            } else {
                console.log('No dropdown match found for:', currentModel, 'Available options:', options.map(o => o.value));
            }
        }
    } else {
        if (modelName) modelName.textContent = 'Error loading';
        if (modelStatus) modelStatus.textContent = data.error || 'Unknown error';
    }
}

async function applyBackendModel() {
    const select = document.getElementById('backend-model-select');
    const applyButton = document.getElementById('apply-backend-model');
    
    if (!select.value) return;
    
    applyButton.disabled = true;
    applyButton.textContent = 'Applying...';
    
    try {
        const response = await fetch('/api/models/set_backend_model', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                model_name: select.value
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Show success message
            window.notificationManager.showSuccess(`Backend model changed to ${select.value}`);
            // Reload current model display with force refresh
            setTimeout(() => loadCurrentBackendModel(true), 1000);
        } else {
            window.notificationManager.showError(data.error || 'Failed to change backend model');
        }
    } catch (error) {
        console.error('Error applying backend model:', error);
        window.notificationManager.showError('Failed to connect to backend');
    } finally {
        applyButton.disabled = false;
        applyButton.textContent = 'Apply Model';
    }
}
