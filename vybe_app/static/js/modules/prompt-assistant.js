/**
 * Advanced Prompt Engineering Tools
 * Provides comprehensive prompt management, testing, and optimization capabilities
 */

export class PromptAssistant {
    constructor() {
        this.prompts = new Map();
        this.templates = new Map();
        this.testResults = new Map();
        this.currentPrompt = null;
        
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
        this.loadPromptLibrary();
        this.setupEventListeners();
        this.initializeUI();
    }

    setupEventListeners() {
        console.log('Setting up prompt assistant event listeners');
        
        // Prompt editor events
        const promptEditor = document.getElementById('prompt-editor');
        if (promptEditor) {
            if (window.eventManager && window.eventManager.add) {
                window.eventManager.add(promptEditor, 'input', 
                    window.eventManager.debounce ? 
                    window.eventManager.debounce(() => this.autoSave(), 100) : 
                    () => this.autoSave()
                );
                window.eventManager.add(promptEditor, 'keydown', (e) => this.handleKeyboardShortcuts(e));
            } else {
                // Fallback event handling
                promptEditor.addEventListener('input', () => this.autoSave());
                promptEditor.addEventListener('keydown', (e) => this.handleKeyboardShortcuts(e));
            }
            console.log('Prompt editor event listeners attached');
        }

        // Template selector
        const templateSelector = document.getElementById('template-selector');
        if (templateSelector) {
            if (window.eventManager && window.eventManager.add) {
                window.eventManager.add(templateSelector, 'change', (e) => this.loadTemplate(e.target.value));
            } else {
                templateSelector.addEventListener('change', (e) => this.loadTemplate(e.target.value));
            }
            console.log('Template selector event listener attached');
        }

        // Test button
        const testButton = document.getElementById('test-prompt');
        if (testButton) {
            if (window.eventManager && window.eventManager.add) {
                window.eventManager.add(testButton, 'click', () => this.testPrompt());
            } else {
                testButton.addEventListener('click', () => this.testPrompt());
            }
            console.log('Test button event listener attached');
        }

        // Optimize button
        const optimizeButton = document.getElementById('optimize-prompt');
        if (optimizeButton) {
            if (window.eventManager && window.eventManager.add) {
                window.eventManager.add(optimizeButton, 'click', () => this.optimizePrompt());
            } else {
                optimizeButton.addEventListener('click', () => this.optimizePrompt());
            }
            console.log('Optimize button event listener attached');
        }

        // New prompt button
        const newPromptButton = document.getElementById('new-prompt');
        if (newPromptButton) {
            if (window.eventManager && window.eventManager.add) {
                window.eventManager.add(newPromptButton, 'click', () => this.createNewPrompt());
            } else {
                newPromptButton.addEventListener('click', () => this.createNewPrompt());
            }
            console.log('New prompt button event listener attached');
        }

        // Keyboard shortcuts (global)
        if (window.eventManager && window.eventManager.add) {
            window.eventManager.add(document, 'keydown', (e) => this.handleGlobalKeyboardShortcuts(e));
        } else {
            document.addEventListener('keydown', (e) => this.handleGlobalKeyboardShortcuts(e));
        }
        
        this.showToast('Prompt assistant event handlers initialized', 'info');
    }

    initializeUI() {
        this.createPromptLibrary();
        this.createTemplateGallery();
        this.createTestingPanel();
        this.createOptimizationTools();
    }

    createPromptLibrary() {
        const libraryContainer = document.getElementById('prompt-library');
        if (!libraryContainer) return;

        libraryContainer.innerHTML = `
            <div class="prompt-library-header">
                <h3>Prompt Library</h3>
                <button id="new-prompt" class="btn btn-primary">New Prompt</button>
                    </div>
            <div class="prompt-categories">
                <div class="category" data-category="creative">Creative Writing</div>
                <div class="category" data-category="technical">Technical</div>
                <div class="category" data-category="business">Business</div>
                <div class="category" data-category="educational">Educational</div>
                        </div>
            <div class="prompt-list" id="prompt-list"></div>
        `;

        this.loadPromptCategories();
    }

    createTemplateGallery() {
        const templateContainer = document.getElementById('template-gallery');
        if (!templateContainer) return;

        templateContainer.innerHTML = `
            <div class="template-gallery-header">
                <h3>Prompt Templates</h3>
                <div class="template-filters">
                    <select id="template-category-filter">
                        <option value="">All Categories</option>
                        <option value="creative">Creative</option>
                        <option value="technical">Technical</option>
                        <option value="business">Business</option>
                        <option value="educational">Educational</option>
                    </select>
                        </div>
                    </div>
            <div class="template-grid" id="template-grid"></div>
        `;

        this.loadTemplates();
    }

    createTestingPanel() {
        const testingContainer = document.getElementById('testing-panel');
        if (!testingContainer) return;

        testingContainer.innerHTML = `
            <div class="testing-header">
                <h3>Prompt Testing</h3>
                <button id="run-test" class="btn btn-success">Run Test</button>
            </div>
            <div class="test-inputs">
                <div class="test-input-group">
                    <label>Test Input:</label>
                    <textarea id="test-input" placeholder="Enter test input..."></textarea>
                    </div>
                <div class="test-parameters">
                    <label>Temperature: <span id="temp-value">0.7</span></label>
                    <input type="range" id="temperature" min="0" max="2" step="0.1" value="0.7">
                    <label>Max Tokens: <span id="tokens-value">1000</span></label>
                    <input type="range" id="max-tokens" min="100" max="4000" step="100" value="1000">
                </div>
            </div>
            <div class="test-results" id="test-results"></div>
        `;

        this.setupTestControls();
    }

    createOptimizationTools() {
        const optimizationContainer = document.getElementById('optimization-tools');
        if (!optimizationContainer) return;

        optimizationContainer.innerHTML = `
            <div class="optimization-header">
                <h3>Prompt Optimization</h3>
                <button id="analyze-prompt" class="btn btn-info">Analyze</button>
            </div>
            <div class="optimization-metrics">
                <div class="metric">
                    <label>Clarity Score:</label>
                    <div class="score" id="clarity-score">-</div>
                </div>
                <div class="metric">
                    <label>Specificity Score:</label>
                    <div class="score" id="specificity-score">-</div>
                </div>
                <div class="metric">
                    <label>Token Efficiency:</label>
                    <div class="score" id="token-efficiency">-</div>
                </div>
            </div>
            <div class="optimization-suggestions" id="optimization-suggestions"></div>
        `;
    }

    async loadPromptLibrary() {
        try {
            const response = await fetch('/api/prompts/library');
            if (response.ok) {
                const data = await response.json();
                this.prompts = new Map(Object.entries(data.prompts || {}));
                this.templates = new Map(Object.entries(data.templates || {}));
            }
        } catch (error) {
            console.error('Failed to load prompt library:', error);
        }
    }

    async savePrompt(promptData) {
        console.log('Saving prompt:', promptData);
        
        try {
            // Enhanced prompt data validation
            if (!promptData || !promptData.content) {
                throw new Error('Invalid prompt data - content is required');
            }
            
            const response = await fetch('/api/prompts/save', {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content || ''
                },
                body: JSON.stringify(promptData)
            });
            
            if (response.ok) {
                const result = await response.json();
                this.prompts.set(result.id, promptData);
                this.updatePromptList();
                this.showToast('Prompt saved successfully', 'success');
                console.log('Prompt saved successfully:', result);
                return result;
            } else {
                throw new Error(`Save failed with status: ${response.status}`);
            }
        } catch (error) {
            console.error('Failed to save prompt:', error);
            this.showToast('Failed to save prompt: ' + error.message, 'error');
            throw error;
        }
    }

    async testPrompt() {
        console.log('Starting prompt test');
        
        const promptText = document.getElementById('prompt-editor')?.value;
        const testInput = document.getElementById('test-input')?.value;
        const temperature = document.getElementById('temperature')?.value || 0.7;
        const maxTokens = document.getElementById('max-tokens')?.value || 1000;

        if (!promptText || promptText.trim() === '') {
            this.showToast('Please enter a prompt to test', 'warning');
            console.warn('Cannot test empty prompt');
            return;
        }

        const testResults = document.getElementById('test-results');
        if (testResults) {
            testResults.innerHTML = '<div class="loading">🔄 Testing prompt...</div>';
        }
        
        this.showToast('Testing prompt...', 'info');

        try {
            const response = await fetch('/api/prompts/test', {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content || ''
                },
                body: JSON.stringify({
                    prompt: promptText,
                    test_input: testInput || '',
                    temperature: parseFloat(temperature),
                    max_tokens: parseInt(maxTokens)
                })
            });

            if (response.ok) {
                const result = await response.json();
                this.displayTestResults(result);
                this.showToast('Prompt test completed successfully', 'success');
                console.log('Prompt test completed:', result);
            } else {
                throw new Error(`Test failed with status: ${response.status}`);
            }
        } catch (error) {
            console.error('Prompt test failed:', error);
            const errorMessage = 'Test failed: ' + error.message;
            this.showToast(errorMessage, 'error');
            
            if (testResults) {
                testResults.innerHTML = `<div class="error">❌ ${errorMessage}</div>`;
            }
        }
    }

    async optimizePrompt() {
        console.log('Starting prompt optimization');
        
        const promptText = document.getElementById('prompt-editor')?.value;
        
        if (!promptText || promptText.trim() === '') {
            this.showToast('Please enter a prompt to optimize', 'warning');
            console.warn('Cannot optimize empty prompt');
            return;
        }

        // Show optimization progress
        const optimizeBtn = document.getElementById('optimize-prompt');
        let originalText = '';
        if (optimizeBtn) {
            originalText = optimizeBtn.textContent;
            optimizeBtn.textContent = '🔄 Optimizing...';
            optimizeBtn.disabled = true;
        }
        
        this.showToast('Optimizing prompt...', 'info');

        try {
            const response = await fetch('/api/prompts/optimize', {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content || ''
                },
                body: JSON.stringify({ prompt: promptText })
            });

            if (response.ok) {
                const result = await response.json();
                this.displayOptimizationResults(result);
                this.showToast('Prompt optimization completed', 'success');
                console.log('Prompt optimization completed:', result);
            } else {
                throw new Error(`Optimization failed with status: ${response.status}`);
            }
        } catch (error) {
            console.error('Prompt optimization failed:', error);
            this.showToast('Optimization failed: ' + error.message, 'error');
            
            // Fallback to local analysis if API fails
            console.log('Falling back to local optimization analysis');
            this.analyzePrompt();
            this.showToast('Using local analysis instead', 'info');
        } finally {
            // Reset button state
            if (optimizeBtn) {
                optimizeBtn.textContent = originalText || '⚡ Optimize';
                optimizeBtn.disabled = false;
            }
        }
    }

    displayTestResults(results) {
        const testResults = document.getElementById('test-results');
        testResults.innerHTML = `
            <div class="test-result">
                <h4>Test Results</h4>
                <div class="result-metrics">
                    <div class="metric">
                        <label>Response Time:</label>
                        <span>${results.response_time}ms</span>
                    </div>
                    <div class="metric">
                        <label>Token Usage:</label>
                        <span>${results.tokens_used}</span>
                    </div>
                    <div class="metric">
                        <label>Quality Score:</label>
                        <span>${results.quality_score}/10</span>
                    </div>
                </div>
                <div class="response-preview">
                    <h5>Response Preview:</h5>
                    <div class="preview-text">${results.response.substring(0, 200)}...</div>
                </div>
            </div>
        `;
    }

    displayOptimizationResults(results) {
        // Update metrics
        document.getElementById('clarity-score').textContent = results.clarity_score + '/10';
        document.getElementById('specificity-score').textContent = results.specificity_score + '/10';
        document.getElementById('token-efficiency').textContent = results.token_efficiency + '%';

        // Display suggestions
        const suggestionsContainer = document.getElementById('optimization-suggestions');
        suggestionsContainer.innerHTML = `
            <h4>Optimization Suggestions</h4>
            <div class="suggestions-list">
                ${results.suggestions.map(suggestion => `
                    <div class="suggestion">
                        <div class="suggestion-type">${suggestion.type}</div>
                        <div class="suggestion-text">${suggestion.text}</div>
                        <button class="btn btn-sm btn-primary" onclick="promptAssistant.applySuggestion('${suggestion.id}')">
                            Apply
                        </button>
                    </div>
                `).join('')}
            </div>
            ${results.optimized_prompt ? `
                <div class="optimized-prompt">
                    <h5>Optimized Prompt:</h5>
                    <textarea readonly>${results.optimized_prompt}</textarea>
                    <button class="btn btn-success" onclick="promptAssistant.useOptimizedPrompt()">
                        Use Optimized Version
                    </button>
                </div>
            ` : ''}
        `;
    }

    applySuggestion(suggestionId) {
        console.log('Applying suggestion:', suggestionId);
        
        // Implementation for applying specific suggestions
        const promptEditor = document.getElementById('prompt-editor');
        if (!promptEditor) {
            this.showToast('Prompt editor not found', 'error');
            return;
        }
        
        // Mock suggestion application logic
        const suggestions = {
            'clarity': 'Be more specific about what you want the AI to do.',
            'specificity': 'Add more specific examples or context.',
            'structure': 'Organize your prompt with clear sections.',
            'tone': 'Specify the desired tone or style.',
            'format': 'Define the expected output format.'
        };
        
        const currentText = promptEditor.value;
        const suggestion = suggestions[suggestionId] || 'Generic improvement applied.';
        
        // Apply suggestion as a comment at the end
        const updatedText = currentText + `\n\n<!-- Suggestion applied: ${suggestion} -->`;
        promptEditor.value = updatedText;
        
        this.showToast(`Suggestion "${suggestionId}" applied`, 'success');
        console.log(`Applied suggestion: ${suggestionId}`);
        
        // Trigger auto-save
        this.autoSave();
    }

    useOptimizedPrompt() {
        console.log('Using optimized prompt');
        
        const optimizedText = document.querySelector('.optimized-prompt textarea')?.value;
        if (!optimizedText) {
            this.showToast('No optimized prompt available', 'warning');
            console.warn('No optimized prompt found');
            return;
        }
        
        const promptEditor = document.getElementById('prompt-editor');
        if (promptEditor) {
            // Store original for potential undo
            this.previousPrompt = promptEditor.value;
            
            promptEditor.value = optimizedText;
            this.showToast('Optimized prompt applied', 'success');
            console.log('Optimized prompt applied successfully');
            
            // Update current prompt data
            if (this.currentPrompt) {
                this.currentPrompt.content = optimizedText;
                this.currentPrompt.updated_at = new Date().toISOString();
            }
            
            // Trigger auto-save
            this.autoSave();
            
            // Focus the editor
            promptEditor.focus();
        } else {
            this.showToast('Prompt editor not found', 'error');
            console.error('Prompt editor not found');
        }
    }

    createNewPrompt() {
        console.log('Creating new prompt');
        
        const promptEditor = document.getElementById('prompt-editor');
        if (promptEditor) {
            promptEditor.value = '';
            promptEditor.focus();
        }
        
        this.currentPrompt = {
            id: 'new-' + Date.now(),
            title: 'Untitled Prompt',
            content: '',
            category: 'custom',
            created_at: new Date().toISOString()
        };
        
        this.showToast('New prompt created', 'success');
    }

    handleGlobalKeyboardShortcuts(event) {
        if (event.ctrlKey || event.metaKey) {
            switch (event.key) {
                case 'n':
                    if (event.shiftKey) {
                        event.preventDefault();
                        this.createNewPrompt();
                        console.log('New prompt created via keyboard shortcut');
                    }
                    break;
                case 't':
                    if (event.shiftKey) {
                        event.preventDefault();
                        this.testPrompt();
                        console.log('Prompt test triggered via keyboard shortcut');
                    }
                    break;
            }
        }
    }

    handleKeyboardShortcuts(event) {
        console.log('Handling keyboard shortcuts in prompt editor');
        
        if (event.ctrlKey || event.metaKey) {
            switch (event.key) {
                case 's':
                    event.preventDefault();
                    this.autoSave();
                    this.showToast('Prompt saved', 'success');
                    console.log('Manual save triggered');
                    break;
                case 'Enter':
                    event.preventDefault();
                    this.testPrompt();
                    console.log('Quick test triggered');
                    break;
            }
        }
    }

    autoSave() {
        console.log('Auto-save triggered');
        
        // Debounced auto-save
        clearTimeout(this.saveTimeout);
        this.saveTimeout = setTimeout(() => {
            this.saveCurrentPrompt();
        }, 1000);
        
        // Show visual feedback for auto-save
        const promptEditor = document.getElementById('prompt-editor');
        if (promptEditor) {
            promptEditor.style.borderColor = '#28a745';
            setTimeout(() => {
                promptEditor.style.borderColor = '';
            }, 500);
        }
    }

    async saveCurrentPrompt() {
        console.log('Saving current prompt');
        
        const promptText = document.getElementById('prompt-editor')?.value;
        if (!promptText || promptText.trim() === '') {
            console.log('Skipping save of empty prompt');
            return;
        }
        
        if (!this.currentPrompt) {
            // Create new prompt if none exists
            this.currentPrompt = {
                id: 'auto-' + Date.now(),
                title: 'Auto-saved Prompt',
                category: 'auto-save',
                created_at: new Date().toISOString()
            };
        }
        
        try {
            await this.savePrompt({
                id: this.currentPrompt.id,
                title: this.currentPrompt.title,
                content: promptText,
                category: this.currentPrompt.category,
                updated_at: new Date().toISOString()
            });
            console.log('Auto-save completed successfully');
        } catch (error) {
            console.error('Auto-save failed:', error);
            // Don't show toast for auto-save failures to avoid spam
        }
    }

    loadPromptCategories() {
        console.log('Loading prompt categories');
        
        // Load and display prompt categories
        const categoryContainer = document.querySelector('.prompt-categories');
        if (categoryContainer) {
            const categories = categoryContainer.querySelectorAll('.category');
            categories.forEach(category => {
                const handleCategoryClick = (e) => {
                    // Remove active class from all categories
                    categories.forEach(cat => cat.classList.remove('active'));
                    // Add active class to clicked category
                    e.target.classList.add('active');
                    
                    const categoryType = e.target.getAttribute('data-category');
                    console.log('Category selected:', categoryType);
                    this.filterPromptsByCategory(categoryType);
                    this.showToast(`Showing ${categoryType} prompts`, 'info');
                };
                
                if (window.eventManager && window.eventManager.add) {
                    window.eventManager.add(category, 'click', handleCategoryClick);
                } else {
                    category.addEventListener('click', handleCategoryClick);
                }
            });
            
            console.log(`Attached click handlers to ${categories.length} categories`);
        } else {
            console.warn('Category container not found');
        }
    }

    loadTemplates() {
        console.log('Loading prompt templates');
        
        // Load available prompt templates
        const templateGrid = document.getElementById('template-grid');
        if (templateGrid) {
            // Default templates
            const defaultTemplates = [
                { id: 'creative-story', name: 'Creative Story', category: 'creative' },
                { id: 'code-review', name: 'Code Review', category: 'technical' },
                { id: 'business-plan', name: 'Business Plan', category: 'business' },
                { id: 'lesson-plan', name: 'Lesson Plan', category: 'educational' },
                { id: 'email-template', name: 'Email Template', category: 'business' },
                { id: 'blog-post', name: 'Blog Post', category: 'creative' }
            ];

            templateGrid.innerHTML = defaultTemplates.map(template => `
                <div class="template-card" data-template-id="${template.id}">
                    <h4>${template.name}</h4>
                    <span class="template-category">${template.category}</span>
                    <button class="btn btn-sm btn-primary template-load-btn">Load Template</button>
                </div>
            `).join('');

            // Add click handlers
            templateGrid.querySelectorAll('.template-card').forEach(card => {
                const handleTemplateClick = (e) => {
                    const templateId = e.target.closest('.template-card').getAttribute('data-template-id');
                    console.log('Template selected:', templateId);
                    this.loadTemplate(templateId);
                };
                
                if (window.eventManager && window.eventManager.add) {
                    window.eventManager.add(card, 'click', handleTemplateClick);
                } else {
                    card.addEventListener('click', handleTemplateClick);
                }
            });
            
            console.log(`Loaded ${defaultTemplates.length} templates with event handlers`);
        } else {
            console.warn('Template grid container not found');
        }
    }

    setupTestControls() {
        console.log('Setting up test controls');
        
        // Setup temperature and token controls
        const temperatureSlider = document.getElementById('temperature');
        const tempValue = document.getElementById('temp-value');
        if (temperatureSlider && tempValue) {
            const updateTempValue = (e) => {
                tempValue.textContent = e.target.value;
                console.log('Temperature updated to:', e.target.value);
            };
            
            if (window.eventManager && window.eventManager.add) {
                window.eventManager.add(temperatureSlider, 'input', updateTempValue);
            } else {
                temperatureSlider.addEventListener('input', updateTempValue);
            }
        }

        const tokensSlider = document.getElementById('max-tokens');
        const tokensValue = document.getElementById('tokens-value');
        if (tokensSlider && tokensValue) {
            const updateTokensValue = (e) => {
                tokensValue.textContent = e.target.value;
                console.log('Max tokens updated to:', e.target.value);
            };
            
            if (window.eventManager && window.eventManager.add) {
                window.eventManager.add(tokensSlider, 'input', updateTokensValue);
            } else {
                tokensSlider.addEventListener('input', updateTokensValue);
            }
        }

        // Test run button
        const runTestBtn = document.getElementById('run-test');
        if (runTestBtn) {
            const handleTestRun = () => {
                console.log('Test run button clicked');
                this.testPrompt();
            };
            
            if (window.eventManager && window.eventManager.add) {
                window.eventManager.add(runTestBtn, 'click', handleTestRun);
            } else {
                runTestBtn.addEventListener('click', handleTestRun);
            }
        }

        // Analyze button
        const analyzeBtn = document.getElementById('analyze-prompt');
        if (analyzeBtn) {
            const handleAnalyze = () => {
                console.log('Analyze button clicked');
                this.analyzePrompt();
            };
            
            if (window.eventManager && window.eventManager.add) {
                window.eventManager.add(analyzeBtn, 'click', handleAnalyze);
            } else {
                analyzeBtn.addEventListener('click', handleAnalyze);
            }
        }
        
        console.log('Test controls setup completed');
    }

    loadTemplate(templateId) {
        console.log('Loading template:', templateId);
        
        // Load specific template content
        const templates = {
            'creative-story': 'Write a creative story about [TOPIC]. Include vivid descriptions, engaging characters, and a compelling plot. Make sure to:\n- Set the scene with rich sensory details\n- Develop interesting characters with clear motivations\n- Include dialogue that advances the story\n- Create a satisfying conclusion',
            'code-review': 'Review the following [LANGUAGE] code for best practices, bugs, and performance issues:\n\n```[LANGUAGE]\n[CODE]\n```\n\nPlease analyze:\n1. Code quality and structure\n2. Potential bugs or security issues\n3. Performance optimizations\n4. Best practices adherence\n5. Suggestions for improvement',
            'business-plan': 'Create a comprehensive business plan for a [BUSINESS_TYPE] targeting [TARGET_MARKET]. Include:\n\n1. Executive Summary\n2. Market Analysis\n3. Business Model\n4. Marketing Strategy\n5. Financial Projections\n6. Risk Assessment\n7. Implementation Timeline',
            'lesson-plan': 'Create a detailed lesson plan for teaching [SUBJECT] to [GRADE_LEVEL] students. Duration: [DURATION]\n\nInclude:\n- Learning objectives\n- Materials needed\n- Step-by-step activities\n- Assessment methods\n- Homework assignments\n- Differentiation strategies',
            'email-template': 'Write a professional email for [PURPOSE]. Tone: [FORMAL/CASUAL]\n\nRecipient: [RECIPIENT]\nSubject: [SUBJECT]\n\nInclude:\n- Appropriate greeting\n- Clear purpose statement\n- Supporting details\n- Call to action\n- Professional closing',
            'blog-post': 'Write an engaging blog post about [TOPIC] for [TARGET_AUDIENCE]. Length: [WORD_COUNT] words\n\nStructure:\n1. Attention-grabbing headline\n2. Compelling introduction\n3. Main content with subheadings\n4. Practical examples or tips\n5. Strong conclusion with call-to-action'
        };

        const promptEditor = document.getElementById('prompt-editor');
        if (promptEditor && templates[templateId]) {
            promptEditor.value = templates[templateId];
            
            // Update current prompt
            this.currentPrompt = {
                id: `template-${templateId}-${Date.now()}`,
                title: `Template: ${templateId.replace('-', ' ')}`,
                content: templates[templateId],
                category: 'template',
                created_at: new Date().toISOString()
            };
            
            this.showToast(`Template "${templateId.replace('-', ' ')}" loaded`, 'success');
            console.log(`Template "${templateId}" loaded successfully`);
            
            // Focus the editor for immediate editing
            promptEditor.focus();
        } else {
            this.showToast(`Template "${templateId}" not found`, 'error');
            console.error(`Template "${templateId}" not found`);
        }
    }

    filterPromptsByCategory(category) {
        console.log('Filtering prompts by category:', category);
        
        // Filter prompts by category
        const promptList = document.getElementById('prompt-list');
        if (!promptList) {
            console.warn('Prompt list container not found');
            return;
        }
        
        // Filter prompts based on category
        const filteredPrompts = Array.from(this.prompts.entries()).filter(([, prompt]) => {
            return !category || prompt.category === category;
        });
        
        if (filteredPrompts.length === 0) {
            promptList.innerHTML = `
                <div class="prompt-category-title">Category: ${category || 'All'}</div>
                <div class="no-prompts">No prompts found in this category.</div>
            `;
        } else {
            promptList.innerHTML = `
                <div class="prompt-category-title">Category: ${category || 'All'} (${filteredPrompts.length} prompts)</div>
                ${filteredPrompts.map(([id, prompt]) => `
                    <div class="prompt-item" data-prompt-id="${id}">
                        <div class="prompt-title">${prompt.title || 'Untitled'}</div>
                        <div class="prompt-preview">${(prompt.content || '').substring(0, 100)}...</div>
                        <div class="prompt-actions">
                            <button class="btn btn-sm btn-primary" onclick="promptAssistant.loadPromptById('${id}')">Load</button>
                            <button class="btn btn-sm btn-danger" onclick="promptAssistant.deletePrompt('${id}')">Delete</button>
                        </div>
                    </div>
                `).join('')}
            `;
        }
        
        console.log(`Filtered to ${filteredPrompts.length} prompts in category: ${category || 'All'}`);
    }

    async analyzePrompt() {
        const promptText = document.getElementById('prompt-editor')?.value;
        if (!promptText) {
            this.showNotification('Please enter a prompt to analyze', 'warning');
            return;
        }

        // Simple analysis
        const wordCount = promptText.split(' ').length;
        const clarity = this.calculateClarityScore(promptText);
        const specificity = this.calculateSpecificityScore(promptText);
        const efficiency = Math.round((100 - Math.min(wordCount / 10, 100)));

        document.getElementById('clarity-score').textContent = clarity + '/10';
        document.getElementById('specificity-score').textContent = specificity + '/10';
        document.getElementById('token-efficiency').textContent = efficiency + '%';
    }

    calculateClarityScore(text) {
        // Simple clarity scoring based on sentence structure
        const sentences = text.split('.').filter(s => s.trim().length > 0);
        const avgLength = sentences.reduce((sum, s) => sum + s.length, 0) / sentences.length;
        return Math.round(Math.max(1, Math.min(10, 15 - avgLength / 20)));
    }

    calculateSpecificityScore(text) {
        // Simple specificity scoring based on keywords
        const specificWords = ['specific', 'exactly', 'precisely', 'detailed', 'particular'];
        const hasSpecificWords = specificWords.some(word => text.toLowerCase().includes(word));
        const hasPlaceholders = text.includes('[') && text.includes(']');
        return hasSpecificWords ? 8 : (hasPlaceholders ? 6 : 4);
    }

    updatePromptList() {
        console.log('Updating prompt list');
        
        const promptList = document.getElementById('prompt-list');
        if (!promptList) {
            console.warn('Prompt list container not found');
            return;
        }
        
        if (this.prompts.size === 0) {
            promptList.innerHTML = '<div class="no-prompts">No prompts available. Create your first prompt!</div>';
            return;
        }
        
        promptList.innerHTML = Array.from(this.prompts.entries()).map(([id, prompt]) => `
            <div class="prompt-item" data-prompt-id="${id}">
                <div class="prompt-title">${prompt.title || 'Untitled'}</div>
                <div class="prompt-category">${prompt.category || 'uncategorized'}</div>
                <div class="prompt-actions">
                    <button class="btn btn-sm btn-primary" onclick="promptAssistant.loadPromptById('${id}')">Load</button>
                    <button class="btn btn-sm btn-danger" onclick="promptAssistant.deletePrompt('${id}')">Delete</button>
                </div>
            </div>
        `).join('');
        
        console.log(`Updated prompt list with ${this.prompts.size} prompts`);
    }

    loadPromptById(promptId) {
        console.log('Loading prompt by ID:', promptId);
        
        const prompt = this.prompts.get(promptId);
        if (!prompt) {
            this.showToast('Prompt not found', 'error');
            return;
        }
        
        const promptEditor = document.getElementById('prompt-editor');
        if (promptEditor) {
            promptEditor.value = prompt.content || '';
            this.currentPrompt = prompt;
            this.showToast(`Loaded prompt: ${prompt.title || 'Untitled'}`, 'success');
            console.log('Prompt loaded successfully');
        }
    }

    async deletePrompt(promptId) {
        console.log('Deleting prompt:', promptId);
        
        if (!confirm('Are you sure you want to delete this prompt?')) {
            return;
        }
        
        try {
            const response = await fetch(`/api/prompts/${promptId}`, {
                method: 'DELETE',
                headers: {
                    'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content || ''
                }
            });
            
            if (response.ok) {
                this.prompts.delete(promptId);
                this.updatePromptList();
                this.showToast('Prompt deleted successfully', 'success');
                console.log('Prompt deleted successfully');
            } else {
                throw new Error(`Delete failed with status: ${response.status}`);
            }
        } catch (error) {
            console.error('Failed to delete prompt:', error);
            this.showToast('Failed to delete prompt: ' + error.message, 'error');
        }
    }

    showToast(message, type = 'info') {
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
        toast.className = `prompt-toast toast-${type}`;
        toast.style.cssText = `
            position: fixed;
            top: 100px;
            right: 20px;
            background: ${type === 'error' ? '#dc3545' : type === 'success' ? '#28a745' : type === 'warning' ? '#ffc107' : '#007bff'};
            color: ${type === 'warning' ? '#000' : '#fff'};
            padding: 12px 16px;
            border-radius: 6px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            z-index: 10000;
            max-width: 300px;
            font-size: 0.9rem;
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
        
        // Auto remove after 4 seconds
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(100%)';
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
            }, 300);
        }, 4000);
    }

    showNotification(message, type = 'info') {
        console.log(`Notification (${type}): ${message}`);
        this.showToast(message, type);
    }
}

// Initialize the prompt assistant and make it globally available
const promptAssistant = new PromptAssistant();
window.promptAssistant = promptAssistant;

// Auto-initialize when DOM is ready
if (window.eventManager && window.eventManager.add) {
    window.eventManager.add(document, 'DOMContentLoaded', () => {
        console.log('Prompt Assistant initialized and ready');
    });
} else {
    document.addEventListener('DOMContentLoaded', () => {
        console.log('Prompt Assistant initialized and ready');
    });
}