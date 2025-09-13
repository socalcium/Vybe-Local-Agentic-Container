/**
 * Prompt Maker JavaScript
 * Handles the interactive wizard for creating system prompts
 */

// Notification manager is accessed globally through window.notificationManager

class PromptMaker {
    constructor() {
        this.currentStep = 1;
        this.maxSteps = 3;
        this.formData = {};
        
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
        console.log('PromptMaker: Starting initialization');
        if (window.notificationManager) {
            window.notificationManager.showInfo('Initializing Prompt Maker...');
        }
        
        try {
            console.log('PromptMaker: Binding events...');
            this.bindEvents();
            
            console.log('PromptMaker: Loading templates...');
            this.loadTemplates();
            
            console.log('PromptMaker: Updating initial preview...');
            this.updatePreview();
            
            console.log('PromptMaker: Initialization completed successfully');
            if (window.notificationManager) {
                window.notificationManager.showSuccess('Prompt Maker initialized successfully');
            }
        } catch (error) {
            console.error('PromptMaker: Failed to initialize:', error);
            if (window.notificationManager) {
                window.notificationManager.showError('Failed to initialize Prompt Maker');
            }
            this.showError('Failed to initialize Prompt Maker: ' + error.message);
        }
    }

    bindEvents() {
        console.log('PromptMaker: Binding events');
        
        // Navigation buttons with enhanced logging
        const nextBtn = document.getElementById('nextBtn');
        const prevBtn = document.getElementById('prevBtn');
        const saveBtn = document.getElementById('saveBtn');
        
        if (nextBtn) {
            nextBtn.addEventListener('click', () => {
                console.log('PromptMaker: Next button clicked');
                if (window.notificationManager) {
                    window.notificationManager.showInfo('Moving to next step');
                }
                this.nextStep();
            });
        }
        
        if (prevBtn) {
            prevBtn.addEventListener('click', () => {
                console.log('PromptMaker: Previous button clicked');
                if (window.notificationManager) {
                    window.notificationManager.showInfo('Moving to previous step');
                }
                this.prevStep();
            });
        }
        
        if (saveBtn) {
            saveBtn.addEventListener('click', (e) => {
                console.log('PromptMaker: Save button clicked');
                if (window.notificationManager) {
                    window.notificationManager.showInfo('Saving prompt...');
                }
                this.handleSave(e);
            });
        }

        // Preview buttons with enhanced feedback
        const copyBtn = document.getElementById('copyBtn');
        const useInChatBtn = document.getElementById('useInChatBtn');
        
        if (copyBtn) {
            copyBtn.addEventListener('click', () => {
                console.log('PromptMaker: Copy button clicked');
                if (window.notificationManager) {
                    window.notificationManager.showInfo('Copying prompt to clipboard...');
                }
                this.copyToClipboard();
            });
        }
        
        if (useInChatBtn) {
            useInChatBtn.addEventListener('click', () => {
                console.log('PromptMaker: Use in chat button clicked');
                if (window.notificationManager) {
                    window.notificationManager.showInfo('Activating prompt for chat...');
                }
                this.useInChat();
            });
        }

        // Form inputs - update preview on change with debouncing
        const inputs = document.querySelectorAll('#promptMakerForm input, #promptMakerForm textarea, #promptMakerForm select');
        console.log(`PromptMaker: Found ${inputs.length} form inputs to monitor`);
        
        inputs.forEach((input, index) => {
            // Log input binding
            console.log(`PromptMaker: Binding events to input ${index}: ${input.name || input.id}`);
            
            window.eventManager.add(input, 'input', window.eventManager.debounce(() => {
                console.log(`PromptMaker: Input changed: ${input.name || input.id}`);
                this.updatePreview();
            }, 100));
            
            window.eventManager.add(input, 'change', () => {
                console.log(`PromptMaker: Input value changed: ${input.name || input.id}`);
                this.updatePreview();
            });
        });

        // Modal close events with enhanced handling
        document.querySelectorAll('.close').forEach((closeBtn, index) => {
            console.log(`PromptMaker: Binding close button ${index}`);
            window.eventManager.add(closeBtn, 'click', (e) => {
                e.preventDefault();
                const modal = e.target.closest('.modal');
                if (modal) {
                    console.log(`PromptMaker: Closing modal: ${modal.id}`);
                    if (window.notificationManager) {
                        window.notificationManager.showInfo('Closing modal');
                    }
                    this.closeModal(modal.id);
                }
            });
        });

        // Close modal when clicking outside with enhanced handling
        window.eventManager.add(window, 'click', (e) => {
            if (e.target.classList.contains('modal')) {
                console.log(`PromptMaker: Modal backdrop clicked: ${e.target.id}`);
                if (window.notificationManager) {
                    window.notificationManager.showInfo('Modal closed');
                }
                this.closeModal(e.target.id);
            }
        });

        // Add keyboard shortcuts
        window.eventManager.add(document, 'keydown', (e) => {
            // Ctrl+S to save
            if (e.ctrlKey && e.key === 's') {
                e.preventDefault();
                console.log('PromptMaker: Ctrl+S keyboard shortcut triggered');
                if (window.notificationManager) {
                    window.notificationManager.showInfo('Quick save triggered');
                }
                if (this.currentStep === this.maxSteps) {
                    this.handleSave(e);
                } else {
                    if (window.notificationManager) {
                        window.notificationManager.showWarning('Complete all steps before saving');
                    }
                }
            }
            
            // Ctrl+Enter to advance step
            if (e.ctrlKey && e.key === 'Enter') {
                e.preventDefault();
                console.log('PromptMaker: Ctrl+Enter keyboard shortcut triggered');
                if (this.currentStep < this.maxSteps) {
                    this.nextStep();
                } else {
                    this.handleSave(e);
                }
            }
            
            // Escape to go back
            if (e.key === 'Escape' && this.currentStep > 1) {
                console.log('PromptMaker: Escape key pressed - going to previous step');
                if (window.notificationManager) {
                    window.notificationManager.showInfo('Going to previous step');
                }
                this.prevStep();
            }
        });

        console.log('PromptMaker: All events bound successfully');
    }

    nextStep() {
        console.log(`PromptMaker: Attempting to move from step ${this.currentStep} to ${this.currentStep + 1}`);
        
        if (this.validateCurrentStep()) {
            if (this.currentStep < this.maxSteps) {
                this.currentStep++;
                console.log(`PromptMaker: Successfully moved to step ${this.currentStep}`);
                if (window.notificationManager) {
                    window.notificationManager.showSuccess(`Step ${this.currentStep} of ${this.maxSteps}`);
                }
                this.updateStepDisplay();
                
                if (this.currentStep === 3) {
                    console.log('PromptMaker: Reached final step - updating final prompt');
                    this.updateFinalPrompt();
                    if (window.notificationManager) {
                        window.notificationManager.showInfo('Review your prompt before saving');
                    }
                }
            } else {
                console.log('PromptMaker: Already at maximum step');
                if (window.notificationManager) {
                    window.notificationManager.showWarning('Already at the final step');
                }
            }
        } else {
            console.log('PromptMaker: Step validation failed');
            if (window.notificationManager) {
                window.notificationManager.showError('Please complete all required fields');
            }
        }
    }

    prevStep() {
        console.log(`PromptMaker: Moving from step ${this.currentStep} to ${this.currentStep - 1}`);
        
        if (this.currentStep > 1) {
            this.currentStep--;
            console.log(`PromptMaker: Successfully moved to step ${this.currentStep}`);
            if (window.notificationManager) {
                window.notificationManager.showInfo(`Step ${this.currentStep} of ${this.maxSteps}`);
            }
            this.updateStepDisplay();
        } else {
            console.log('PromptMaker: Already at first step');
            if (window.notificationManager) {
                window.notificationManager.showWarning('Already at the first step');
            }
        }
    }

    updateStepDisplay() {
        // Update step indicators
        document.querySelectorAll('.step').forEach((step, index) => {
            const stepNum = index + 1;
            step.classList.remove('active', 'completed');
            
            if (stepNum === this.currentStep) {
                step.classList.add('active');
            } else if (stepNum < this.currentStep) {
                step.classList.add('completed');
            }
        });

        // Update form steps
        document.querySelectorAll('.form-step').forEach((step, index) => {
            const stepNum = index + 1;
            step.classList.toggle('active', stepNum === this.currentStep);
        });

        // Update navigation buttons
        const prevBtn = document.getElementById('prevBtn');
        const nextBtn = document.getElementById('nextBtn');
        const saveBtn = document.getElementById('saveBtn');

        prevBtn.style.display = this.currentStep === 1 ? 'none' : 'inline-flex';
        nextBtn.style.display = this.currentStep === this.maxSteps ? 'none' : 'inline-flex';
        saveBtn.style.display = this.currentStep === this.maxSteps ? 'inline-flex' : 'none';
    }

    validateCurrentStep() {
        const currentStepElement = document.querySelector(`.form-step[data-step="${this.currentStep}"]`);
        const requiredFields = currentStepElement.querySelectorAll('[required]');
        
        for (let field of requiredFields) {
            if (!field.value.trim()) {
                field.focus();
                this.showError(`Please fill in the required field: ${field.previousElementSibling.textContent}`);
                return false;
            }
        }
        return true;
    }

    collectFormData() {
        const formElements = document.querySelectorAll('#promptMakerForm input, #promptMakerForm textarea, #promptMakerForm select');
        const data = {};
        
        formElements.forEach(element => {
            data[element.name] = element.value;
        });
        
        return data;
    }

    generatePrompt() {
        const data = this.collectFormData();
        let prompt = '';

        // Add persona if provided
        if (data.persona && data.persona.trim()) {
            prompt += `${data.persona.trim()}\n\n`;
        }

        // Add task (required)
        if (data.task && data.task.trim()) {
            prompt += `${data.task.trim()}\n\n`;
        }

        // Add context if provided
        if (data.context && data.context.trim()) {
            prompt += `${data.context.trim()}\n\n`;
        }

        // Add tone if selected
        if (data.tone && data.tone.trim()) {
            const toneText = this.getToneText(data.tone);
            if (toneText) {
                prompt += `${toneText}\n\n`;
            }
        }

        // Add format if provided
        if (data.format && data.format.trim()) {
            prompt += `${data.format.trim()}\n\n`;
        }

        // Add constraints if provided
        if (data.constraints && data.constraints.trim()) {
            prompt += `${data.constraints.trim()}\n\n`;
        }

        return prompt.trim();
    }

    getToneText(tone) {
        const toneMap = {
            'professional': 'Maintain a professional and respectful tone throughout your responses.',
            'friendly': 'Be friendly and approachable in your communication style.',
            'casual': 'Use a casual and conversational tone.',
            'formal': 'Use formal language and maintain professional decorum.',
            'concise': 'Be concise and to the point in your responses.',
            'detailed': 'Provide detailed and comprehensive explanations.',
            'encouraging': 'Be encouraging and supportive in your responses.',
            'direct': 'Be direct and straightforward in your communication.'
        };
        return toneMap[tone] || '';
    }

    updatePreview() {
        console.log('PromptMaker: Updating preview');
        const prompt = this.generatePrompt();
        const previewElement = document.getElementById('promptPreview');
        
        if (!previewElement) {
            console.warn('PromptMaker: Preview element not found');
            return;
        }
        
        if (prompt.trim()) {
            previewElement.textContent = prompt;
            previewElement.style.fontStyle = 'normal';
            console.log(`PromptMaker: Preview updated with ${prompt.length} characters`);
        } else {
            previewElement.innerHTML = '<em>Your prompt will appear here as you fill out the form...</em>';
            console.log('PromptMaker: Preview cleared - no content');
        }

        this.updateStats(prompt);
        
        // Show preview update notification (but only occasionally to avoid spam)
        if (!this.lastPreviewUpdate || Date.now() - this.lastPreviewUpdate > 2000) {
            if (window.notificationManager) {
                window.notificationManager.showInfo('Preview updated');
            }
            this.lastPreviewUpdate = Date.now();
        }
    }

    updateFinalPrompt() {
        console.log('PromptMaker: Updating final prompt');
        const prompt = this.generatePrompt();
        const finalPromptElement = document.getElementById('finalPrompt');
        
        if (finalPromptElement) {
            finalPromptElement.value = prompt;
            console.log(`PromptMaker: Final prompt updated with ${prompt.length} characters`);
            if (window.notificationManager) {
                window.notificationManager.showSuccess('Final prompt ready for review');
            }
        } else {
            console.warn('PromptMaker: Final prompt element not found');
        }
    }

    updateStats(prompt) {
        const charCount = prompt.length;
        const wordCount = prompt.trim() ? prompt.trim().split(/\s+/).length : 0;
        const tokenCount = Math.ceil(charCount / 4); // Rough estimate

        const charElement = document.getElementById('charCount');
        const wordElement = document.getElementById('wordCount');
        const tokenElement = document.getElementById('tokenCount');

        if (charElement) charElement.textContent = charCount.toLocaleString();
        if (wordElement) wordElement.textContent = wordCount.toLocaleString();
        if (tokenElement) tokenElement.textContent = tokenCount.toLocaleString();

        console.log(`PromptMaker: Stats updated - Characters: ${charCount}, Words: ${wordCount}, Tokens: ${tokenCount}`);
    }

    async handleSave(e) {
        e.preventDefault();
        
        if (!this.validateCurrentStep()) {
            return;
        }

        const data = this.collectFormData();
        const prompt = this.generatePrompt();

        if (!prompt.trim()) {
            this.showError('Cannot save an empty prompt.');
            return;
        }

        const promptData = {
            name: data.promptName,
            description: data.promptDescription || '',
            category: data.promptCategory || 'General',
            content: prompt
        };

        try {
            const response = await fetch('/api/settings/system_prompts', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(promptData)
            });

            if (response.ok) {
                const result = await response.json();
                console.log('Save result:', result);
                this.showSuccess(`Prompt "${data.promptName}" saved successfully!`);
                this.clearForm();
                this.loadTemplates(); // Refresh templates list
            } else {
                const error = await response.json();
                this.showError(error.error || 'Failed to save prompt');
            }
        } catch (error) {
            console.error('Error saving prompt:', error);
            this.showError('Network error. Please try again.');
        }
    }

    async copyToClipboard() {
        const prompt = this.generatePrompt();
        
        if (!prompt.trim()) {
            this.showError('No prompt to copy');
            return;
        }

        try {
            await navigator.clipboard.writeText(prompt);
            this.showSuccess('Prompt copied to clipboard!');
        } catch (error) {
            console.error('Error copying to clipboard:', error);
            // Fallback method
            const textArea = document.createElement('textarea');
            textArea.value = prompt;
            document.body.appendChild(textArea);
            textArea.select();
            try {
                document.execCommand('copy');
                this.showSuccess('Prompt copied to clipboard!');
            } catch (fallbackError) {
                console.error('Fallback error:', fallbackError);
                this.showError('Failed to copy to clipboard');
            }
            document.body.removeChild(textArea);
        }
    }

    async useInChat() {
        const data = this.collectFormData();
        const prompt = this.generatePrompt();

        if (!prompt.trim()) {
            this.showError('No prompt to use');
            return;
        }

        // If prompt is not saved, save it first
        if (!data.promptName) {
            this.showError('Please save the prompt first before using it in chat');
            return;
        }

        try {
            // First, find the saved prompt by name or save it
            const promptsResponse = await fetch('/api/settings/system_prompts');
            const prompts = await promptsResponse.json();
            
            let savedPrompt = prompts.find(p => p.name === data.promptName);
            
            if (!savedPrompt) {
                // Save the prompt first
                const saveResponse = await fetch('/api/settings/system_prompts', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        name: data.promptName,
                        description: data.promptDescription || '',
                        category: data.promptCategory || 'General',
                        content: prompt
                    })
                });
                
                if (saveResponse.ok) {
                    savedPrompt = await saveResponse.json();
                } else {
                    throw new Error('Failed to save prompt');
                }
            }

            // Set as active prompt
            const useResponse = await fetch(`/api/settings/system_prompts/${savedPrompt.id}/use`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });

            if (useResponse.ok) {
                this.showSuccess('Prompt activated! You can now use it in chat.');
                // Optionally redirect to chat
                setTimeout(() => {
                    window.location.href = '/';
                }, 2000);
            } else {
                const error = await useResponse.json();
                this.showError(error.error || 'Failed to activate prompt');
            }
        } catch (error) {
            console.error('Error using prompt in chat:', error);
            this.showError('Failed to use prompt in chat');
        }
    }

    async loadTemplates() {
        console.log('PromptMaker: Loading templates');
        if (window.notificationManager) {
            window.notificationManager.showInfo('Loading templates...');
        }
        
        try {
            const response = await fetch('/api/settings/system_prompts');
            if (response.ok) {
                const templates = await response.json();
                console.log(`PromptMaker: Loaded ${templates.length} templates`);
                this.renderTemplates(templates);
                if (window.notificationManager) {
                    window.notificationManager.showSuccess(`Loaded ${templates.length} templates`);
                }
            } else {
                console.error('PromptMaker: Failed to load templates - HTTP error');
                if (window.notificationManager) {
                    window.notificationManager.showError('Failed to load templates');
                }
            }
        } catch (error) {
            console.error('PromptMaker: Error loading templates:', error);
            if (window.notificationManager) {
                window.notificationManager.showError('Error loading templates');
            }
        }
    }

    renderTemplates(templates) {
        console.log(`PromptMaker: Rendering ${templates.length} templates`);
        const grid = document.getElementById('templatesGrid');
        
        if (!grid) {
            console.warn('PromptMaker: Templates grid element not found');
            return;
        }
        
        if (templates.length === 0) {
            grid.innerHTML = '<p class="text-secondary">No saved templates yet. Create your first prompt above!</p>';
            console.log('PromptMaker: No templates to display');
            return;
        }

        grid.innerHTML = templates.map((template, index) => {
            console.log(`PromptMaker: Rendering template ${index}: ${template.name}`);
            return `
                <div class="template-card" data-id="${template.id}">
                    <h4>${this.escapeHtml(template.name)}</h4>
                    <span class="category">${this.escapeHtml(template.category)}</span>
                    <p class="description">${this.escapeHtml(template.description || 'No description')}</p>
                    <div class="actions">
                        <button class="btn btn-outline-primary btn-sm" onclick="promptMaker.loadTemplate(${template.id})">
                            📝 Edit
                        </button>
                        <button class="btn btn-outline-success btn-sm" onclick="promptMaker.useTemplate(${template.id})">
                            💬 Use
                        </button>
                        <button class="btn btn-outline-primary btn-sm" onclick="promptMaker.copyTemplate(${template.id})">
                            📋 Copy
                        </button>
                        <button class="btn btn-outline-danger btn-sm" onclick="promptMaker.deleteTemplate(${template.id})">
                            🗑️ Delete
                        </button>
                    </div>
                </div>
            `;
        }).join('');

        console.log('PromptMaker: Templates rendered successfully');
        if (window.notificationManager) {
            window.notificationManager.showSuccess('Templates displayed');
        }
    }

    async loadTemplate(templateId) {
        console.log(`PromptMaker: Loading template ${templateId}`);
        if (window.notificationManager) {
            window.notificationManager.showInfo('Loading template...');
        }
        
        try {
            const response = await fetch(`/api/settings/system_prompts/${templateId}`);
            if (response.ok) {
                const template = await response.json();
                console.log(`PromptMaker: Template loaded: ${template.name}`);
                this.populateFormWithTemplate(template);
                this.currentStep = 1;
                this.updateStepDisplay();
                if (window.notificationManager) {
                    window.notificationManager.showSuccess(`Template "${template.name}" loaded`);
                }
            } else {
                console.error('PromptMaker: Failed to load template - HTTP error');
                if (window.notificationManager) {
                    window.notificationManager.showError('Failed to load template');
                }
            }
        } catch (error) {
            console.error('PromptMaker: Error loading template:', error);
            if (window.notificationManager) {
                window.notificationManager.showError('Error loading template');
            }
        }
    }

    populateFormWithTemplate(template) {
        console.log(`PromptMaker: Populating form with template: ${template.name}`);
        
        // Parse the content to extract components (this is a basic implementation)
        const nameField = document.getElementById('promptName');
        const descriptionField = document.getElementById('promptDescription');
        const categoryField = document.getElementById('promptCategory');
        const taskField = document.getElementById('task');
        
        if (nameField) nameField.value = template.name + ' (Copy)';
        if (descriptionField) descriptionField.value = template.description;
        if (categoryField) categoryField.value = template.category;
        
        // For now, put the entire content in the task field
        // In a more sophisticated implementation, you could try to parse the content
        if (taskField) taskField.value = template.content;
        
        this.updatePreview();
        console.log('PromptMaker: Form populated with template data');
        if (window.notificationManager) {
            window.notificationManager.showInfo('Form updated with template data');
        }
    }

    async useTemplate(templateId) {
        console.log(`PromptMaker: Using template ${templateId}`);
        if (window.notificationManager) {
            window.notificationManager.showInfo('Activating template...');
        }
        
        try {
            const response = await fetch(`/api/settings/system_prompts/${templateId}/use`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });

            if (response.ok) {
                console.log(`PromptMaker: Template ${templateId} activated successfully`);
                if (window.notificationManager) {
                    window.notificationManager.showSuccess('Template activated for chat!');
                }
                this.showSuccess('Template activated for chat!');
            } else {
                const error = await response.json();
                console.error('PromptMaker: Failed to activate template:', error);
                if (window.notificationManager) {
                    window.notificationManager.showError('Failed to activate template');
                }
                this.showError(error.error || 'Failed to activate template');
            }
        } catch (error) {
            console.error('PromptMaker: Error using template:', error);
            if (window.notificationManager) {
                window.notificationManager.showError('Error activating template');
            }
            this.showError('Failed to use template');
        }
    }

    async copyTemplate(templateId) {
        console.log(`PromptMaker: Copying template ${templateId}`);
        if (window.notificationManager) {
            window.notificationManager.showInfo('Copying template...');
        }
        
        try {
            const response = await fetch(`/api/settings/system_prompts/${templateId}`);
            if (response.ok) {
                const template = await response.json();
                await navigator.clipboard.writeText(template.content);
                console.log(`PromptMaker: Template ${templateId} copied to clipboard`);
                if (window.notificationManager) {
                    window.notificationManager.showSuccess(`Template "${template.name}" copied to clipboard!`);
                }
                this.showSuccess('Template copied to clipboard!');
            } else {
                console.error('PromptMaker: Failed to fetch template for copying');
                if (window.notificationManager) {
                    window.notificationManager.showError('Failed to copy template');
                }
                this.showError('Failed to copy template');
            }
        } catch (error) {
            console.error('PromptMaker: Error copying template:', error);
            if (window.notificationManager) {
                window.notificationManager.showError('Error copying template');
            }
            this.showError('Failed to copy template');
        }
    }

    async deleteTemplate(templateId) {
        console.log(`PromptMaker: Delete requested for template ${templateId}`);
        
        if (!confirm('Are you sure you want to delete this template? This action cannot be undone.')) {
            console.log('PromptMaker: Template deletion cancelled by user');
            if (window.notificationManager) {
                window.notificationManager.showInfo('Template deletion cancelled');
            }
            return;
        }

        console.log(`PromptMaker: Deleting template ${templateId}`);
        if (window.notificationManager) {
            window.notificationManager.showWarning('Deleting template...');
        }

        try {
            const response = await fetch(`/api/settings/system_prompts/${templateId}`, {
                method: 'DELETE'
            });

            if (response.ok) {
                console.log(`PromptMaker: Template ${templateId} deleted successfully`);
                if (window.notificationManager) {
                    window.notificationManager.showSuccess('Template deleted successfully');
                }
                this.showSuccess('Template deleted successfully');
                this.loadTemplates(); // Refresh the list
            } else {
                const error = await response.json();
                console.error('PromptMaker: Failed to delete template:', error);
                if (window.notificationManager) {
                    window.notificationManager.showError('Failed to delete template');
                }
                this.showError(error.error || 'Failed to delete template');
            }
        } catch (error) {
            console.error('PromptMaker: Error deleting template:', error);
            if (window.notificationManager) {
                window.notificationManager.showError('Error deleting template');
            }
            this.showError('Failed to delete template');
        }
    }

    // Utility method to validate form data
    validateFormData(data) {
        console.log('PromptMaker: Validating form data');
        const errors = [];

        if (!data.promptName || !data.promptName.trim()) {
            errors.push('Prompt name is required');
        }

        if (!data.task || !data.task.trim()) {
            errors.push('Task description is required');
        }

        if (data.promptName && data.promptName.length > 100) {
            errors.push('Prompt name must be 100 characters or less');
        }

        if (errors.length > 0) {
            console.warn('PromptMaker: Form validation failed:', errors);
            return { valid: false, errors };
        }

        console.log('PromptMaker: Form validation passed');
        return { valid: true, errors: [] };
    }

    // Utility method to get prompt statistics
    getPromptStats() {
        const prompt = this.generatePrompt();
        const stats = {
            characters: prompt.length,
            words: prompt.trim() ? prompt.trim().split(/\s+/).length : 0,
            lines: prompt.split('\n').length,
            paragraphs: prompt.split('\n\n').filter(p => p.trim()).length,
            estimatedTokens: Math.ceil(prompt.length / 4)
        };
        
        console.log('PromptMaker: Prompt statistics:', stats);
        return stats;
    }

    // Utility method to export prompt data
    exportPromptData() {
        console.log('PromptMaker: Exporting prompt data');
        const data = this.collectFormData();
        const prompt = this.generatePrompt();
        
        const exportData = {
            metadata: {
                name: data.promptName,
                description: data.promptDescription,
                category: data.promptCategory,
                created: new Date().toISOString()
            },
            components: {
                persona: data.persona,
                task: data.task,
                context: data.context,
                tone: data.tone,
                format: data.format,
                constraints: data.constraints
            },
            generated_prompt: prompt,
            statistics: this.getPromptStats()
        };
        
        console.log('PromptMaker: Export data prepared');
        if (window.notificationManager) {
            window.notificationManager.showSuccess('Prompt data exported');
        }
        return exportData;
    }

    clearForm() {
        console.log('PromptMaker: Clearing form');
        
        const form = document.getElementById('promptMakerForm');
        if (form) {
            form.reset();
            console.log('PromptMaker: Form reset completed');
        }
        
        this.currentStep = 1;
        this.updateStepDisplay();
        this.updatePreview();
        
        // Clear any stored data
        this.formData = {};
        this.lastPreviewUpdate = null;
        
        console.log('PromptMaker: Form cleared and reset to step 1');
        if (window.notificationManager) {
            window.notificationManager.showInfo('Form cleared');
        }
    }

    showSuccess(message) {
        document.getElementById('successMessage').textContent = message;
        this.showModal('successModal');
    }

    showError(message) {
        document.getElementById('errorMessage').textContent = message;
        this.showModal('errorModal');
    }

    showModal(modalId) {
        document.getElementById(modalId).style.display = 'block';
    }

    closeModal(modalId) {
        document.getElementById(modalId).style.display = 'none';
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// All notifications now use the global window.notificationManager

// Initialize the Prompt Maker when the page loads
let promptMaker;
window.eventManager.add(document, 'DOMContentLoaded', () => {
    if (document.getElementById('promptMakerForm')) {
        promptMaker = new PromptMaker();
    }
});

// Global function for modal closing (called from HTML)
window.closeModal = function closeModal(modalId) {
    if (promptMaker) {
        promptMaker.closeModal(modalId);
    }
};
