/**
 * Model Manager Module
 * Handles model selection, temperature settings, and RAG toggle
 */

import { ApiUtils } from '../utils/api-utils.js';

export class ModelManager {
    constructor() {
        this.ui = {
            modelSelect: document.getElementById('model-select'),
            modelContextInfo: document.getElementById('model-context-info'),
            threadsInput: document.getElementById('llm-threads-input'),
            threadsValueSpan: document.getElementById('llm-threads-value'),
            ctxInput: document.getElementById('llm-ctx-input'),
            ctxValueSpan: document.getElementById('llm-ctx-value'),
            saveBtn: document.getElementById('llm-config-save'),
            whyTip: document.getElementById('llm-why-tip'),
            temperatureInput: document.getElementById('temperature-input'),
            temperatureValueSpan: document.getElementById('temperature-value'),
            ragToggle: document.getElementById('rag-toggle')
        };

        // Cleanup functions for event listeners
        this.cleanupFunctions = [];
        
        this.modelsData = [];
        this.currentModel = null;
        this.currentTemperature = 0.7;
        this.ragEnabled = false;

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
        this.loadModels();
        this.loadLlmConfig();
        this.setupEventListeners();
        this.loadSettings();
    }

    setupEventListeners() {
        // Model selection change
        if (this.ui.modelSelect) {
            window.eventManager.add(this.ui.modelSelect, 'change', () => {
                this.onModelChange();
            });
        }

        // Temperature slider change
        if (this.ui.temperatureInput) {
            window.eventManager.add(this.ui.temperatureInput, 'input', window.eventManager.debounce((e) => {
                this.updateTemperature(parseFloat(e.target.value));
            }, 100));
        }

        // RAG toggle change
        if (this.ui.ragToggle) {
            window.eventManager.add(this.ui.ragToggle, 'change', () => {
                this.onRagToggle();
            });
        }

        // LLM threads/context inputs
        if (this.ui.threadsInput) {
            window.eventManager.add(this.ui.threadsInput, 'input', window.eventManager.debounce((e) => {
                const v = parseInt(e.target.value);
                this.ui.threadsValueSpan.textContent = String(v);
            }, 100));
        }
        if (this.ui.ctxInput) {
            window.eventManager.add(this.ui.ctxInput, 'input', window.eventManager.debounce((e) => {
                const v = parseInt(e.target.value);
                this.ui.ctxValueSpan.textContent = String(v);
            }, 100));
        }
        if (this.ui.saveBtn) {
            window.eventManager.add(this.ui.saveBtn, 'click', () => this.saveLlmConfig());
        }
    }

    onModelChange() {
        console.log('Model selection changed');
        const selectedModel = this.ui.modelSelect.value;
        if (selectedModel) {
            this.selectModel(selectedModel);
            if (window.showNotification) {
                window.showNotification(`Model changed to: ${selectedModel}`, 'success');
            }
        }
    }

    onRagToggle() {
        console.log('RAG toggle changed');
        const ragEnabled = this.ui.ragToggle.checked;
        this.setRagEnabled(ragEnabled);
        if (window.showNotification) {
            window.showNotification(`RAG ${ragEnabled ? 'enabled' : 'disabled'}`, 'info');
        }
    }

    updateTemperature(temperature) {
        console.log('Temperature updated:', temperature);
        this.setTemperature(temperature);
        if (window.showNotification) {
            window.showNotification(`Temperature set to: ${temperature.toFixed(1)}`, 'info');
        }
    }

    async loadModels() {
        try {
            const data = await ApiUtils.safeFetch('/api/models');
            if (data && data.models) {
                this.modelsData = data.models;
                this.updateModelSelect();
                this.updateModelContextInfo();
            } else {
                console.warn('No models data received from API');
                this.modelsData = [];
                this.updateModelSelect();
            }
        } catch (error) {
            console.error('Error loading models:', error);
            this.modelsData = [];
            if (this.ui.modelSelect) {
                this.ui.modelSelect.innerHTML = '<option>Error loading models</option>';
            }
        }
    }

    async loadLlmConfig() {
        try {
            const res = await fetch('/api/llm/config');
            const data = await res.json();
            if (data && data.success) {
                const cfg = data.config || {};
                const rec = data.recommendations || {};
                if (this.ui.threadsInput && typeof cfg.n_threads === 'number') {
                    this.ui.threadsInput.value = cfg.n_threads;
                    if (this.ui.threadsValueSpan) this.ui.threadsValueSpan.textContent = String(cfg.n_threads);
                }
                if (this.ui.ctxInput && typeof cfg.n_ctx === 'number') {
                    this.ui.ctxInput.value = cfg.n_ctx;
                    if (this.ui.ctxValueSpan) this.ui.ctxValueSpan.textContent = String(cfg.n_ctx);
                }
                if (this.ui.whyTip && rec.why) {
                    this.ui.whyTip.textContent = rec.why;
                }
                // Load backend status tile if present
                try {
                    const bsRes = await fetch('/api/models/backend_status');
                    const bs = await bsRes.json();
                    const el = document.getElementById('backend-status');
                    if (el && bs && bs.success) {
                        const running = bs.running;
                        const loaded = bs.model_loaded;
                        el.textContent = `Running: ${running ? 'Yes' : 'No'} | Model loaded: ${loaded ? 'Yes' : 'No'} | URL: ${bs.server_url || 'N/A'}`;
                    } else if (el) {
                        el.textContent = 'Backend status unavailable';
                    }
                } catch (backendStatusError) {
                    console.warn('Backend status error:', backendStatusError);
                    const el = document.getElementById('backend-status');
                    if (el) el.textContent = 'Backend status unavailable';
                }
            }
        } catch (e) {
            console.warn('Failed to load LLM config', e);
        }
    }

    async saveLlmConfig() {
        try {
            const n_threads = this.ui.threadsInput ? parseInt(this.ui.threadsInput.value || '0', 10) : undefined;
            const n_ctx = this.ui.ctxInput ? parseInt(this.ui.ctxInput.value || '0', 10) : undefined;
            const res = await fetch('/api/llm/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ n_threads, n_ctx })
            });
            const data = await res.json();
            if (data && data.success) {
                // reflect any clamped values
                const cfg = data.config || {};
                if (this.ui.threadsInput && typeof cfg.n_threads === 'number') {
                    this.ui.threadsInput.value = cfg.n_threads;
                    if (this.ui.threadsValueSpan) this.ui.threadsValueSpan.textContent = String(cfg.n_threads);
                }
                if (this.ui.ctxInput && typeof cfg.n_ctx === 'number') {
                    this.ui.ctxInput.value = cfg.n_ctx;
                    if (this.ui.ctxValueSpan) this.ui.ctxValueSpan.textContent = String(cfg.n_ctx);
                }
            }
        } catch (e) {
            console.warn('Failed to save LLM config', e);
        }
    }

    updateModelSelect() {
        if (!this.ui.modelSelect) return;

        if (this.modelsData.length === 0) {
            this.ui.modelSelect.innerHTML = '<option>No models found</option>';
            return;
        }

        this.ui.modelSelect.innerHTML = '';
        this.modelsData.forEach(model => {
            const option = document.createElement('option');
            option.value = model.name;
            option.textContent = model.name;
            this.ui.modelSelect.appendChild(option);
        });

        // Select first model by default if none selected
        if (!this.currentModel && this.modelsData.length > 0) {
            this.selectModel(this.modelsData[0].name);
        }
    }

    selectModel(modelName) {
        this.currentModel = modelName;
        if (this.ui.modelSelect) {
            this.ui.modelSelect.value = modelName;
        }
        this.updateModelContextInfo();
        this.saveSettings();
    }

    updateModelContextInfo() {
        if (!this.ui.modelContextInfo) return;

        if (this.currentModel) {
            const selectedModel = this.modelsData.find(m => m.name === this.currentModel);
            const contextSize = selectedModel ? selectedModel.n_ctx : '-';
            this.ui.modelContextInfo.textContent = `Max Context: ${contextSize}`;
        } else {
            this.ui.modelContextInfo.textContent = 'Max Context: -';
        }
    }

    setTemperature(temperature) {
        this.currentTemperature = Math.max(0, Math.min(2, temperature));
        
        if (this.ui.temperatureInput) {
            this.ui.temperatureInput.value = this.currentTemperature;
        }
        
        if (this.ui.temperatureValueSpan) {
            this.ui.temperatureValueSpan.textContent = this.currentTemperature.toFixed(1);
        }
        
        this.saveSettings();
    }

    setRagEnabled(enabled) {
        this.ragEnabled = enabled;
        if (this.ui.ragToggle) {
            this.ui.ragToggle.checked = enabled;
        }
        this.saveSettings();
    }

    saveSettings() {
        const settings = {
            model: this.currentModel,
            temperature: this.currentTemperature,
            ragEnabled: this.ragEnabled
        };
        localStorage.setItem('chatSettings', JSON.stringify(settings));
    }

    loadSettings() {
        try {
            const savedSettings = localStorage.getItem('chatSettings');
            if (savedSettings) {
                const settings = JSON.parse(savedSettings);
                
                if (settings.model) {
                    this.currentModel = settings.model;
                }
                
                if (typeof settings.temperature === 'number') {
                    this.setTemperature(settings.temperature);
                }
                
                if (typeof settings.ragEnabled === 'boolean') {
                    this.setRagEnabled(settings.ragEnabled);
                }
            }
        } catch (error) {
            console.error('Error loading chat settings:', error);
        }
    }

    // Getter methods
    getSelectedModel() {
        return this.currentModel;
    }

    getTemperature() {
        return this.currentTemperature;
    }

    getRagEnabled() {
        return this.ragEnabled;
    }

    getModelsData() {
        return this.modelsData;
    }

    getModelInfo(modelName) {
        return this.modelsData.find(m => m.name === modelName);
    }

    // Refresh models data
    async refreshModels() {
        await this.loadModels();
    }
}
