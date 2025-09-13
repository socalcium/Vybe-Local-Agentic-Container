/**
 * Orchestrator Manager - handles orchestrator model selection and configuration
 */

let currentOrchestratorData = {};
let selectedModelForModal = null;
let eventListeners = []; // Track event listeners for cleanup

/**
 * Initialize orchestrator settings page
 */
async function initializeOrchestratorSettings() {
    try {
        await Promise.all([
            loadOrchestratorStatus(),
            loadAvailableModels(),
            loadPersonalizedRecommendations(),
            loadConfiguration()
        ]);
        
        setupEventListeners();
        
        // Cleanup on page unload
        const cleanup = () => cleanupOrchestratorManager();
        if (window.eventManager) {
            window.eventManager.add(window, 'beforeunload', cleanup);
        } else {
            window.addEventListener('beforeunload', cleanup);
        }
        
    } catch (error) {
        console.error('Error initializing orchestrator settings:', error);
        showErrorMessage('Failed to load orchestrator settings');
    }
}

/**
 * Cleanup function to prevent memory leaks
 */
function cleanupOrchestratorManager() {
    // Remove all tracked event listeners
    eventListeners.forEach(({element, event, handler, cleanup}) => {
        if (cleanup && typeof cleanup === 'function') {
            // Use eventManager cleanup function
            cleanup();
        } else if (element && element.removeEventListener) {
            // Fallback to direct removal
            element.removeEventListener(event, handler);
        }
    });
    eventListeners = [];
}

/**
 * Add event listener with tracking
 */
function addEventListener(element, event, handler) {
    if (window.eventManager) {
        const cleanup = window.eventManager.add(element, event, handler);
        eventListeners.push({element, event, handler, cleanup});
    } else {
        element.addEventListener(event, handler);
        eventListeners.push({element, event, handler});
    }
}

/**
 * Load orchestrator status and system profile
 */
async function loadOrchestratorStatus() {
    try {
        const response = await fetch('/api/orchestrator/status', { cache: 'no-store' });
        const data = await response.json();
        
        if (data.success) {
            currentOrchestratorData = data;
            console.log('Orchestrator status loaded:', currentOrchestratorData);
            displaySystemProfile(data.pc_profile);
            displayCurrentStatus(data);
            showToast('System status loaded.', 'success');
        } else {
            throw new Error(data.error || 'Failed to load status');
        }
        
    } catch (error) {
        console.error('Error loading orchestrator status:', error);
        showErrorMessage('Failed to load orchestrator status');
    }
}

/**
 * Load available orchestrator models
 */
async function loadAvailableModels() {
    try {
        const response = await fetch('/api/orchestrator/models');
        const data = await response.json();
        
        if (data.success) {
            displayOrchestratorModels(data.models, data.current_selection, data.hardware_tier);
        } else {
            throw new Error(data.error || 'Failed to load models');
        }
        
    } catch (error) {
        console.error('Error loading orchestrator models:', error);
        showErrorMessage('Failed to load orchestrator models');
    }
}

/**
 * Load personalized recommendations
 */
async function loadPersonalizedRecommendations() {
    try {
        const response = await fetch('/api/orchestrator/recommendations');
        const data = await response.json();
        
        if (data.success) {
            displayPersonalizedRecommendations(data.recommendations, data.user_profile, data.hardware_profile);
        } else {
            console.warn('No recommendations available:', data.error);
        }
        
    } catch (error) {
        console.error('Error loading recommendations:', error);
    }
}

/**
 * Load configuration settings
 */
async function loadConfiguration() {
    try {
        console.log('Loading orchestrator configuration...');
        
        const response = await fetch('/api/orchestrator/config');
        const data = await response.json();
        
        if (data.success) {
            console.log('Configuration loaded successfully:', data.config);
            applyConfigurationToUI(data.config);
            showToast('Configuration loaded.', 'success');
        } else {
            console.warn('No configuration available:', data.error);
            showToast('Using default configuration.', 'info');
        }
        
    } catch (error) {
        console.error('Error loading configuration:', error);
        showToast('Failed to load configuration.', 'error');
    }
}

/**
 * Display system profile
 */
function displaySystemProfile(pcProfile) {
    const profileContainer = document.getElementById('systemProfile');
    
    const profileHTML = `
        <div class="profile-item">
            <div class="profile-value">${pcProfile.hardware_tier || 'Unknown'}</div>
            <div class="profile-label">Hardware Tier</div>
        </div>
        <div class="profile-item">
            <div class="profile-value">${pcProfile.total_ram_gb || 0}GB</div>
            <div class="profile-label">Total RAM</div>
        </div>
        <div class="profile-item">
            <div class="profile-value">${pcProfile.cpu_cores || 0}</div>
            <div class="profile-label">CPU Cores</div>
        </div>
        <div class="profile-item">
            <div class="profile-value">${pcProfile.gpu_available || 'None'}</div>
            <div class="profile-label">GPU</div>
        </div>
        <div class="profile-item">
            <div class="profile-value">${pcProfile.max_concurrent_models || 1}</div>
            <div class="profile-label">Max Models</div>
        </div>
        <div class="profile-item">
            <div class="profile-value">${pcProfile.disk_free_gb || 0}GB</div>
            <div class="profile-label">Free Space</div>
        </div>
    `;
    
    profileContainer.innerHTML = profileHTML;
}

/**
 * Display current orchestrator status
 */
function displayCurrentStatus(statusData) {
    const statusContainer = document.getElementById('currentStatus');
    
    const selectedModel = statusData.selected_model;
    const userProfile = statusData.user_profile_summary;
    
    const statusHTML = `
        <div class="status-grid">
            <div class="status-item">
                <div class="status-header">
                    <span class="status-indicator ${statusData.status.is_ready ? 'status-online' : 'status-offline'}"></span>
                    <strong>Current Orchestrator</strong>
                </div>
                <div class="status-details">
                    <div class="model-name">${selectedModel.display_name}</div>
                    <div class="model-tier">${selectedModel.tier}</div>
                    <div class="model-ram">${selectedModel.ram_requirement}</div>
                </div>
            </div>
            
            <div class="status-item">
                <div class="status-header">
                    <span class="status-indicator status-online"></span>
                    <strong>User Profile</strong>
                </div>
                <div class="status-details">
                    <div>Interactions: ${userProfile.total_interactions}</div>
                    <div>Skill Level: ${userProfile.skill_level}</div>
                    <div>Hardware: ${userProfile.hardware_tier}</div>
                </div>
            </div>
        </div>
    `;
    
    statusContainer.innerHTML = statusHTML;
}

/**
 * Display orchestrator models
 */
function displayOrchestratorModels(models, currentSelection, hardwareTier) {
    const modelsContainer = document.getElementById('orchestratorModels');
    
    const modelsHTML = models.map(model => {
        const isSelected = model.name === currentSelection;
        const isRecommended = model.recommended_for.includes(hardwareTier);
        const isInstalled = model.installed;
        
        let cardClasses = ['orchestrator-model-card'];
        if (isSelected) cardClasses.push('selected');
        if (isRecommended && !isSelected) cardClasses.push('recommended');
        
        const badges = [];
        if (isSelected) badges.push('<span class="model-badge badge-selected">Current</span>');
        if (isRecommended) badges.push('<span class="model-badge badge-recommended">Recommended</span>');
        if (model.uncensored) badges.push('<span class="model-badge badge-uncensored">Uncensored</span>');
        if (isInstalled) {
            badges.push('<span class="model-badge badge-installed">Installed</span>');
        } else {
            badges.push('<span class="model-badge badge-not-installed">Not Installed</span>');
        }
        
        const capabilities = model.capabilities.map(cap => 
            `<span class="capability-tag">${cap.replace(/_/g, ' ')}</span>`
        ).join('');
        
        return `
            <div class="${cardClasses.join(' ')}" onclick="selectOrchestratorModel('${model.name}', ${isInstalled})" data-model="${model.name}">
                <div class="model-header">
                    <h3 class="model-title">${model.display_name}</h3>
                    <span class="model-tier">${model.tier}</span>
                </div>
                
                <div class="model-description">${model.description}</div>
                
                <div class="model-specs">
                    <div class="spec-item">
                        <span class="spec-label">RAM Required:</span>
                        <span class="spec-value">${model.ram_requirement}</span>
                    </div>
                    <div class="spec-item">
                        <span class="spec-label">Tier:</span>
                        <span class="spec-value">${model.tier}</span>
                    </div>
                </div>
                
                <div class="model-badges">
                    ${badges.join('')}
                </div>
                
                <div class="capabilities-list">
                    ${capabilities}
                </div>
                
                <button class="btn btn-sm btn-secondary model-details-btn" onclick="event.stopPropagation(); showModelDetails('${model.name}')">
                    View Details
                </button>
            </div>
        `;
    }).join('');
    
    modelsContainer.innerHTML = modelsHTML;
}

/**
 * Display personalized recommendations
 */
function displayPersonalizedRecommendations(recommendations, userProfile, hardwareProfile) {
    const recommendationsContainer = document.getElementById('personalizedRecommendations');
    
    if (!recommendations || Object.keys(recommendations).length === 0) {
        recommendationsContainer.innerHTML = '<p>No personalized recommendations available yet. Use Vybe more to get personalized suggestions!</p>';
        return;
    }
    
    let recommendationsHTML = `
        <div class="recommendations-grid">
            <div class="recommendation-section">
                <h4>📈 Your Usage Profile</h4>
                <div class="profile-summary">
                    <div>Skill Level: <strong>${userProfile.skill_level}</strong></div>
                    <div>Total Interactions: <strong>${userProfile.total_interactions}</strong></div>
                    <div>Hardware Tier: <strong>${hardwareProfile.tier}</strong></div>
                </div>
            </div>
    `;
    
    if (recommendations.suggested_models && recommendations.suggested_models.length > 0) {
        recommendationsHTML += `
            <div class="recommendation-section">
                <h4>🤖 Suggested Models for You</h4>
                ${recommendations.suggested_models.map(model => 
                    `<div class="recommendation-item">
                        <span class="recommendation-icon">🎯</span>
                        <span>${model}</span>
                    </div>`
                ).join('')}
            </div>
        `;
    }
    
    if (recommendations.workflow_optimizations && recommendations.workflow_optimizations.length > 0) {
        recommendationsHTML += `
            <div class="recommendation-section">
                <h4>⚡ Workflow Optimizations</h4>
                ${recommendations.workflow_optimizations.map(opt => 
                    `<div class="recommendation-item">
                        <span class="recommendation-icon">💡</span>
                        <span>${opt}</span>
                    </div>`
                ).join('')}
            </div>
        `;
    }
    
    if (recommendations.hardware_optimizations && recommendations.hardware_optimizations.length > 0) {
        recommendationsHTML += `
            <div class="recommendation-section">
                <h4>🔧 Hardware Recommendations</h4>
                ${recommendations.hardware_optimizations.map(opt => 
                    `<div class="recommendation-item">
                        <span class="recommendation-icon">⚙️</span>
                        <span>${opt}</span>
                    </div>`
                ).join('')}
            </div>
        `;
    }
    
    if (recommendations.most_used_tasks && recommendations.most_used_tasks.length > 0) {
        recommendationsHTML += `
            <div class="recommendation-section">
                <h4>📊 Your Most Used Tasks</h4>
                ${recommendations.most_used_tasks.map(([task, count]) => 
                    `<div class="recommendation-item">
                        <span class="recommendation-icon">📈</span>
                        <span>${task}: ${count} times</span>
                    </div>`
                ).join('')}
            </div>
        `;
    }
    
    recommendationsHTML += '</div>';
    recommendationsContainer.innerHTML = recommendationsHTML;
}

/**
 * Apply configuration to UI
 */
function applyConfigurationToUI(config) {
    console.log('Applying configuration to UI:', config);
    
    // Set toggle switches
    if (config.personalization_enabled !== undefined) {
        const element = document.getElementById('personalizationEnabled');
        if (element) {
            element.checked = config.personalization_enabled;
            console.log('Set personalization enabled:', config.personalization_enabled);
        }
    }
    if (config.user_rag_enabled !== undefined) {
        const element = document.getElementById('userRagEnabled');
        if (element) {
            element.checked = config.user_rag_enabled;
            console.log('Set user RAG enabled:', config.user_rag_enabled);
        }
    }
    if (config.auto_install_requirements !== undefined) {
        const element = document.getElementById('autoInstallRequirements');
        if (element) {
            element.checked = config.auto_install_requirements;
            console.log('Set auto install requirements:', config.auto_install_requirements);
        }
    }
    if (config.hardware_optimization !== undefined) {
        const element = document.getElementById('hardwareOptimization');
        if (element) {
            element.checked = config.hardware_optimization;
            console.log('Set hardware optimization:', config.hardware_optimization);
        }
    }
    
    // Set sliders
    if (config.orchestrator_temperature !== undefined) {
        const tempSlider = document.getElementById('orchestratorTemperature');
        if (tempSlider) {
            tempSlider.value = config.orchestrator_temperature;
            updateRangeValue(tempSlider);
            console.log('Set orchestrator temperature:', config.orchestrator_temperature);
        }
    }
    if (config.delegation_threshold !== undefined) {
        const thresholdSlider = document.getElementById('delegationThreshold');
        if (thresholdSlider) {
            thresholdSlider.value = config.delegation_threshold;
            updateRangeValue(thresholdSlider);
            console.log('Set delegation threshold:', config.delegation_threshold);
        }
    }
    
    console.log('Configuration applied to UI successfully');
}

/**
 * Setup event listeners
 */
function setupEventListeners() {
    // Configuration toggles
    const toggles = ['personalizationEnabled', 'userRagEnabled', 'autoInstallRequirements', 'hardwareOptimization'];
    toggles.forEach(id => {
        const element = document.getElementById(id);
        if (element) {
            addEventListener(element, 'change', () => {
                console.log(`Toggle ${id} changed to:`, element.checked);
                saveConfiguration();
            });
        }
    });
    
    // Range sliders
    const sliders = ['orchestratorTemperature', 'delegationThreshold'];
    sliders.forEach(id => {
        const element = document.getElementById(id);
        if (element) {
            // Debounce function fallback if eventManager not available
            const debounceHandler = window.eventManager && window.eventManager.debounce ? 
                window.eventManager.debounce(() => {
                    updateRangeValue(element);
                }, 100) : 
                (() => {
                    let timeout;
                    return () => {
                        clearTimeout(timeout);
                        timeout = setTimeout(() => updateRangeValue(element), 100);
                    };
                })();

            addEventListener(element, 'input', debounceHandler);
            addEventListener(element, 'change', () => {
                console.log(`Slider ${id} changed to:`, element.value);
                saveConfiguration();
            });
        }
    });
    
    // Modal close handlers
    const modal = document.getElementById('modelDetailsModal');
    if (modal) {
        const closeBtn = modal.querySelector('.close');
        if (closeBtn) {
            addEventListener(closeBtn, 'click', closeModal);
        }
        
        // Click outside modal to close
        addEventListener(window, 'click', function(event) {
            if (event.target === modal) {
                closeModal();
            }
        });
    }

    // Add button event listeners if they exist
    const checkRequirementsBtn = document.getElementById('checkRequirementsBtn');
    if (checkRequirementsBtn) {
        addEventListener(checkRequirementsBtn, 'click', () => {
            console.log('Check requirements button clicked');
            checkRequirements();
        });
    }

    const runTestsBtn = document.getElementById('runIntegrationTestsBtn');
    if (runTestsBtn) {
        addEventListener(runTestsBtn, 'click', () => {
            console.log('Run integration tests button clicked');
            runIntegrationTests();
        });
    }
}

/**
 * Select orchestrator model
 */
async function selectOrchestratorModel(modelName, isInstalled) {
    if (!isInstalled) {
        showErrorMessage('Model not installed. Please install it first from the Models Manager.');
        return;
    }
    
    try {
        showLoadingMessage('Switching orchestrator model...');
        
        const response = await fetch('/api/orchestrator/select', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                model_name: modelName
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showSuccessMessage(data.message);
            
            if (data.restart_recommended) {
                showInfoMessage('Restart recommended for optimal performance with the new orchestrator model.');
            }
            
            // Reload the page to show updated selection
            setTimeout(() => {
                window.location.reload();
            }, 2000);
            
        } else {
            if (data.requires_installation) {
                showErrorMessage(`${data.error}. Please install the model first.`);
            } else {
                throw new Error(data.error);
            }
        }
        
    } catch (error) {
        console.error('Error selecting orchestrator model:', error);
        showErrorMessage('Failed to select orchestrator model');
    }
}

/**
 * Check system requirements
 */
async function checkRequirements() {
    try {
        showLoadingMessage('Checking system requirements...');
        
        const response = await fetch('/api/orchestrator/requirements_check', {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (data.success) {
            displayRequirementsStatus(data.status);
            showSuccessMessage('Requirements check completed');
        } else {
            throw new Error(data.error);
        }
        
    } catch (error) {
        console.error('Error checking requirements:', error);
        showErrorMessage('Failed to check requirements');
    }
}

/**
 * Run comprehensive integration tests
 */
async function runIntegrationTests() {
    try {
        showLoadingMessage('Running comprehensive integration tests... This may take a few minutes.');
        
        const response = await fetch('/api/orchestrator/integration_test', {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (data.success !== undefined) {
            displayIntegrationTestResults(data);
            
            if (data.success) {
                showSuccessMessage('Integration tests completed successfully');
            } else {
                showErrorMessage('Integration tests completed with issues - see results below');
            }
        } else {
            throw new Error(data.error || 'Unknown error');
        }
        
    } catch (error) {
        console.error('Error running integration tests:', error);
        showErrorMessage('Failed to run integration tests');
    }
}

/**
 * Display requirements status
 */
function displayRequirementsStatus(status) {
    const statusContainer = document.getElementById('requirementsStatus');
    
    const statusHTML = `
        <div class="requirements-grid">
            ${Object.entries(status).map(([, requirement]) => `
                <div class="requirement-item">
                    <div class="requirement-header">
                        <span class="status-indicator ${requirement.installed ? 'status-online' : 'status-offline'}"></span>
                        <strong>${requirement.service}</strong>
                    </div>
                    <div class="requirement-status">
                        <div>Installed: ${requirement.installed ? '✅' : '❌'}</div>
                        <div>Running: ${requirement.running ? '✅' : '❌'}</div>
                        ${requirement.error ? `<div class="error-text">Error: ${requirement.error}</div>` : ''}
                        ${requirement.count ? `<div>Count: ${requirement.count}</div>` : ''}
                    </div>
                </div>
            `).join('')}
        </div>
        <button class="btn btn-primary" onclick="checkRequirements()">
            <i class="fas fa-sync-alt"></i> Refresh Status
        </button>
    `;
    
    statusContainer.innerHTML = statusHTML;
}

/**
 * Display integration test results
 */
function displayIntegrationTestResults(data) {
    const testSection = document.getElementById('integrationTestSection');
    const resultsContainer = document.getElementById('integrationTestResults');
    
    // Show the test section
    testSection.style.display = 'block';
    
    const summary = data.summary || {};
    const testResults = data.test_results || {};
    const errors = data.errors || [];
    const warnings = data.warnings || [];
    const recommendations = data.recommendations || [];
    
    let statusColor = 'success';
    if (summary.failed_tests > 0) statusColor = 'error';
    else if (summary.partial_tests > 0 || warnings.length > 0) statusColor = 'warning';
    
    let resultsHTML = `
        <div class="test-summary">
            <div class="summary-grid">
                <div class="summary-item status-${statusColor}">
                    <div class="summary-value">${summary.success_rate || 0}%</div>
                    <div class="summary-label">Success Rate</div>
                </div>
                <div class="summary-item">
                    <div class="summary-value">${summary.passed_tests || 0}</div>
                    <div class="summary-label">Passed</div>
                </div>
                <div class="summary-item">
                    <div class="summary-value">${summary.failed_tests || 0}</div>
                    <div class="summary-label">Failed</div>
                </div>
                <div class="summary-item">
                    <div class="summary-value">${summary.partial_tests || 0}</div>
                    <div class="summary-label">Partial</div>
                </div>
                <div class="summary-item">
                    <div class="summary-value">${summary.skipped_tests || 0}</div>
                    <div class="summary-label">Skipped</div>
                </div>
            </div>
        </div>
    `;
    
    // Add recommendations
    if (recommendations.length > 0) {
        resultsHTML += `
            <div class="test-recommendations">
                <h4>💡 Recommendations</h4>
                <div class="recommendations-list">
                    ${recommendations.map(rec => `<div class="recommendation-item">${rec}</div>`).join('')}
                </div>
            </div>
        `;
    }
    
    // Add detailed test results
    resultsHTML += '<div class="test-details"><h4>📋 Detailed Results</h4>';
    
    Object.entries(testResults).forEach(([testName, result]) => {
        const statusIcon = {
            'passed': '✅',
            'failed': '❌',
            'partial': '⚠️',
            'skipped': '⏭️'
        }[result.status] || '❓';
        
        resultsHTML += `
            <div class="test-result-item ${result.status}">
                <div class="test-header">
                    <span class="test-icon">${statusIcon}</span>
                    <span class="test-name">${testName.replace(/_/g, ' ')}</span>
                    <span class="test-status">${result.status}</span>
                </div>
        `;
        
        if (result.details) {
            resultsHTML += '<div class="test-details-content">';
            Object.entries(result.details).forEach(([key, value]) => {
                resultsHTML += `<div class="detail-row"><span class="detail-key">${key}:</span> <span class="detail-value">${value}</span></div>`;
            });
            resultsHTML += '</div>';
        }
        
        if (result.error) {
            resultsHTML += `<div class="test-error">Error: ${result.error}</div>`;
        }
        
        if (result.reason) {
            resultsHTML += `<div class="test-reason">Reason: ${result.reason}</div>`;
        }
        
        resultsHTML += '</div>';
    });
    
    resultsHTML += '</div>';
    
    // Add errors section
    if (errors.length > 0) {
        resultsHTML += `
            <div class="test-errors">
                <h4>❌ Errors</h4>
                <div class="errors-list">
                    ${errors.map(error => `<div class="error-item">${error}</div>`).join('')}
                </div>
            </div>
        `;
    }
    
    // Add warnings section
    if (warnings.length > 0) {
        resultsHTML += `
            <div class="test-warnings">
                <h4>⚠️ Warnings</h4>
                <div class="warnings-list">
                    ${warnings.map(warning => `<div class="warning-item">${warning}</div>`).join('')}
                </div>
            </div>
        `;
    }
    
    resultsContainer.innerHTML = resultsHTML;
    
    // Scroll to results
    testSection.scrollIntoView({ behavior: 'smooth' });
}

/**
 * Save configuration
 */
async function saveConfiguration() {
    try {
        console.log('Saving orchestrator configuration...');
        
        const config = {
            personalization_enabled: document.getElementById('personalizationEnabled')?.checked || false,
            user_rag_enabled: document.getElementById('userRagEnabled')?.checked || false,
            auto_install_requirements: document.getElementById('autoInstallRequirements')?.checked || false,
            hardware_optimization: document.getElementById('hardwareOptimization')?.checked || false,
            orchestrator_temperature: parseFloat(document.getElementById('orchestratorTemperature')?.value || 0.7),
            delegation_threshold: parseFloat(document.getElementById('delegationThreshold')?.value || 0.75)
        };
        
        console.log('Configuration data:', config);
        
        const response = await fetch('/api/orchestrator/config', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(config)
        });
        
        const data = await response.json();
        
        if (data.success) {
            console.log('Configuration saved successfully');
            showSuccessMessage('Configuration saved successfully');
            showToast('Configuration saved.', 'success');
        } else {
            throw new Error(data.error);
        }
        
    } catch (error) {
        console.error('Error saving configuration:', error);
        showErrorMessage('Failed to save configuration');
        showToast('Failed to save configuration.', 'error');
    }
}

/**
 * Update range value display
 */
function updateRangeValue(slider) {
    console.log(`Updating range value for ${slider.id}: ${slider.value}`);
    
    const valueDisplay = slider.parentElement.querySelector('.range-value');
    if (valueDisplay) {
        let displayValue = slider.value;
        let description = '';
        
        if (slider.id === 'orchestratorTemperature') {
            if (slider.value < 0.3) description = ' (Conservative)';
            else if (slider.value > 0.7) description = ' (Creative)';
            else description = ' (Balanced)';
            displayValue += description;
        } else if (slider.id === 'delegationThreshold') {
            if (slider.value < 0.7) description = ' (Quick Delegation)';
            else if (slider.value > 0.8) description = ' (Careful Delegation)';
            else description = ' (Balanced)';
            displayValue += description;
        }
        
        valueDisplay.textContent = displayValue;
        console.log(`Range display updated: ${displayValue}`);
        showToast(`${slider.id} updated to ${slider.value}${description}`, 'info');
    } else {
        console.warn(`Value display element not found for slider: ${slider.id}`);
    }
}

/**
 * Get current selected model for modal
 */
function getSelectedModelForModal() {
    return selectedModelForModal;
}

/**
 * Show model details in modal
 */
function showModelDetails(modelName) {
    console.log('Showing details for model:', modelName);
    selectedModelForModal = modelName;
    
    const modal = document.getElementById('modelDetailsModal');
    if (modal) {
        // Find the model data
        const modelData = currentOrchestratorData?.models?.find(m => m.name === modelName);
        if (modelData) {
            // Populate modal with model details
            const modalContent = modal.querySelector('.modal-content');
            if (modalContent) {
                modalContent.innerHTML = `
                    <div class="modal-header">
                        <h2>${modelData.display_name}</h2>
                        <button class="close" onclick="closeModal()">&times;</button>
                    </div>
                    <div class="modal-body">
                        <p><strong>Description:</strong> ${modelData.description}</p>
                        <p><strong>Tier:</strong> ${modelData.tier}</p>
                        <p><strong>RAM Required:</strong> ${modelData.ram_requirement}</p>
                        <p><strong>Capabilities:</strong> ${modelData.capabilities?.join(', ') || 'N/A'}</p>
                        <p><strong>Installed:</strong> ${modelData.installed ? 'Yes' : 'No'}</p>
                    </div>
                `;
            }
        }
        modal.style.display = 'block';
        showToast(`Viewing details for ${modelName}.`, 'info');
        console.log('Selected model for modal:', getSelectedModelForModal());
    } else {
        console.warn('Model details modal not found');
        showToast('Model details not available.', 'warning');
    }
}

/**
 * Close modal
 */
function closeModal() {
    console.log('Closing model details modal');
    const modal = document.getElementById('modelDetailsModal');
    if (modal) {
        modal.style.display = 'none';
        console.log('Modal closed');
        showToast('Modal closed.', 'info');
    }
    selectedModelForModal = null;
    console.log('Selected model for modal cleared:', getSelectedModelForModal());
}

/**
 * Show loading message
 */
function showLoadingMessage(message) {
    // Create or update a loading indicator
    let indicator = document.getElementById('loadingIndicator');
    if (!indicator) {
        indicator = document.createElement('div');
        indicator.id = 'loadingIndicator';
        indicator.className = 'loading-message';
        document.body.appendChild(indicator);
    }
    indicator.innerHTML = `
        <div class="loading-content">
            <div class="loading-spinner"></div>
            <span>${message}</span>
        </div>
    `;
    indicator.style.display = 'block';
}

/**
 * Hide loading message
 */
function hideLoadingMessage() {
    const indicator = document.getElementById('loadingIndicator');
    if (indicator) {
        indicator.style.display = 'none';
    }
}

/**
 * Show success message
 */
function showSuccessMessage(message) {
    hideLoadingMessage();
    showNotification(message, 'success');
}

/**
 * Show error message
 */
function showErrorMessage(message) {
    hideLoadingMessage();
    showNotification(message, 'error');
}

/**
 * Show info message
 */
function showInfoMessage(message) {
    showNotification(message, 'info');
}

/**
 * Show notification
 */
function showNotification(message, type = 'info') {
    console.log(`Notification (${type}): ${message}`);
    
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
    
    // Fallback notification
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        left: 50%;
        transform: translateX(-50%);
        background: ${type === 'error' ? '#dc3545' : type === 'success' ? '#28a745' : '#007bff'};
        color: white;
        padding: 12px 20px;
        border-radius: 4px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.2);
        z-index: 10000;
        max-width: 400px;
        text-align: center;
    `;
    notification.textContent = message;
    document.body.appendChild(notification);
    
    setTimeout(() => {
        if (notification.parentNode) {
            notification.parentNode.removeChild(notification);
        }
    }, 5000);
}

/**
 * Show toast notification (placeholder implementation)
 */
function showToast(message, type = 'info') {
    console.log(`Toast (${type}): ${message}`);
    
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
    toast.className = `toast toast-${type}`;
    toast.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: ${type === 'error' ? '#dc3545' : type === 'success' ? '#28a745' : '#007bff'};
        color: white;
        padding: 12px 20px;
        border-radius: 4px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.2);
        z-index: 10000;
        max-width: 300px;
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

// Export functions for global access
window.initializeOrchestratorSettings = initializeOrchestratorSettings;
window.selectOrchestratorModel = selectOrchestratorModel;
window.checkRequirements = checkRequirements;
window.runIntegrationTests = runIntegrationTests;
window.showModelDetails = showModelDetails;
window.closeModal = closeModal;
window.updateRangeValue = updateRangeValue;
