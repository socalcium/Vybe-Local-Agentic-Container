/**
 * Smart Context-Aware Chat Suggestions
 * Provides intelligent conversation starters and follow-up suggestions
 */

class SmartSuggestions {
    constructor() {
        this.suggestions = [];
        this.userContext = this.loadUserContext();
        this.contextHistory = [];
        this.currentTopic = null;
        this.userPreferences = this.loadUserPreferences();
        
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
        this.createSuggestionsContainer();
        this.loadInitialSuggestions();
        this.setupEventListeners();
        console.log('Smart Suggestions initialized');
    }
    
    createSuggestionsContainer() {
        // Create suggestions container in chat interface
        const chatContainer = document.querySelector('.chat-container') || document.querySelector('#chat-main');
        if (!chatContainer) return;
        
        const suggestionsHTML = `
            <div id="smart-suggestions" class="smart-suggestions-container">
                <div class="suggestions-header">
                    <span class="suggestions-title">💡 Suggested for you</span>
                    <button class="suggestions-toggle" onclick="toggleSuggestions()">×</button>
                </div>
                <div class="suggestions-content" id="suggestions-content">
                    <!-- Suggestions will be populated here -->
                </div>
            </div>
        `;
        
        // Add CSS styles
        const styles = `
            <style>
            .smart-suggestions-container {
                background: var(--card-background);
                border-radius: 12px;
                margin: 15px 0;
                box-shadow: 0 4px 12px rgba(0,0,0,0.1);
                border: 1px solid var(--border-color);
                overflow: hidden;
                animation: slideIn 0.3s ease;
            }
            
            @keyframes slideIn {
                from { opacity: 0; transform: translateY(-10px); }
                to { opacity: 1; transform: translateY(0); }
            }
            
            .suggestions-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 12px 16px;
                background: linear-gradient(135deg, var(--accent-color-fade) 0%, var(--background-secondary) 100%);
                border-bottom: 1px solid var(--border-color);
            }
            
            .suggestions-title {
                font-weight: 600;
                color: var(--text-primary);
                font-size: 0.9em;
            }
            
            .suggestions-toggle {
                background: none;
                border: none;
                color: var(--text-secondary);
                cursor: pointer;
                font-size: 1.2em;
                padding: 0;
                width: 20px;
                height: 20px;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            
            .suggestions-content {
                padding: 12px;
                max-height: 300px;
                overflow-y: auto;
            }
            
            .suggestion-category {
                margin-bottom: 16px;
            }
            
            .suggestion-category:last-child {
                margin-bottom: 0;
            }
            
            .category-title {
                font-size: 0.8em;
                font-weight: 600;
                color: var(--text-secondary);
                margin-bottom: 8px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            
            .suggestions-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 8px;
            }
            
            .suggestion-item {
                background: var(--background-secondary);
                border: 1px solid var(--border-color);
                border-radius: 8px;
                padding: 10px 12px;
                cursor: pointer;
                transition: all 0.2s ease;
                font-size: 0.9em;
                line-height: 1.3;
            }
            
            .suggestion-item:hover {
                background: var(--accent-color-fade);
                border-color: var(--accent-color);
                transform: translateY(-1px);
            }
            
            .suggestion-text {
                color: var(--text-primary);
                margin-bottom: 4px;
            }
            
            .suggestion-context {
                color: var(--text-secondary);
                font-size: 0.7em;
            }
            
            .suggestion-icon {
                margin-right: 6px;
            }
            
            .suggestions-empty {
                text-align: center;
                color: var(--text-secondary);
                padding: 20px;
                font-style: italic;
            }
            
            @media (max-width: 768px) {
                .suggestions-grid {
                    grid-template-columns: 1fr;
                }
            }
            </style>
        `;
        
        // Add styles to head
        if (!document.querySelector('#smart-suggestions-styles')) {
            const styleSheet = document.createElement('style');
            styleSheet.id = 'smart-suggestions-styles';
            styleSheet.innerHTML = styles;
            document.head.appendChild(styleSheet);
        }
        
        // Insert suggestions container
        chatContainer.insertAdjacentHTML('afterbegin', suggestionsHTML);
    }
    
    async loadInitialSuggestions() {
        try {
            // Get user context and generate suggestions
            await this.updateUserContext();
            this.generateContextualSuggestions();
            this.displaySuggestions();
            
        } catch (error) {
            console.error('Error loading initial suggestions:', error);
            this.showFallbackSuggestions();
        }
    }
    
    async updateUserContext() {
        try {
            // Get current system status
            const systemResponse = await fetch('/api/orchestrator/status');
            if (systemResponse.ok) {
                const systemData = await systemResponse.json();
                this.userContext.system = systemData;
            }
            
            // Get user profile and recommendations
            const recResponse = await fetch('/api/orchestrator/recommendations');
            if (recResponse.ok) {
                const recData = await recResponse.json();
                this.userContext.recommendations = recData.recommendations;
                this.userContext.profile = recData.user_profile;
            }
            
            // Get available models for suggestions
            const modelsResponse = await fetch('/api/models/available');
            if (modelsResponse.ok) {
                const modelsData = await modelsResponse.json();
                this.userContext.models = modelsData.models || [];
            }
            
        } catch (error) {
            console.error('Error updating user context:', error);
        }
    }
    
    generateContextualSuggestions() {
        console.log('Generating contextual suggestions');
        
        this.suggestions = [];
        
        try {
            // Quick Start suggestions
            const quickStartSuggestions = this.generateQuickStartSuggestions();
            this.suggestions.push({
                category: '🚀 Quick Start',
                items: quickStartSuggestions
            });
            console.log(`Generated ${quickStartSuggestions.length} quick start suggestions`);
            
            // Personalized suggestions based on user profile
            if (this.userContext.profile) {
                const personalizedSuggestions = this.generatePersonalizedSuggestions();
                this.suggestions.push({
                    category: '👤 Personalized',
                    items: personalizedSuggestions
                });
                console.log(`Generated ${personalizedSuggestions.length} personalized suggestions`);
            }
            
            // Feature Discovery
            const featureSuggestions = this.generateFeatureDiscoverySuggestions();
            this.suggestions.push({
                category: '🔍 Discover Features',
                items: featureSuggestions
            });
            console.log(`Generated ${featureSuggestions.length} feature discovery suggestions`);
            
            // Context-aware follow-ups
            if (this.contextHistory.length > 0) {
                const followUpSuggestions = this.generateFollowUpSuggestions();
                this.suggestions.push({
                    category: '💬 Continue Conversation',
                    items: followUpSuggestions
                });
                console.log(`Generated ${followUpSuggestions.length} follow-up suggestions based on context`);
            }
            
            // Productive tasks
            const productiveSuggestions = this.generateProductiveSuggestions();
            this.suggestions.push({
                category: '⚡ Productive Tasks',
                items: productiveSuggestions
            });
            console.log(`Generated ${productiveSuggestions.length} productive task suggestions`);
            
            // Topic-specific suggestions if current topic is identified
            if (this.currentTopic && this.currentTopic !== 'general') {
                const topicSuggestions = this.generateTopicSpecificSuggestions(this.currentTopic);
                this.suggestions.push({
                    category: `🎯 ${this.currentTopic.charAt(0).toUpperCase() + this.currentTopic.slice(1)} Focus`,
                    items: topicSuggestions
                });
                console.log(`Generated ${topicSuggestions.length} topic-specific suggestions for: ${this.currentTopic}`);
            }
            
            console.log(`Total suggestions generated: ${this.suggestions.reduce((total, cat) => total + cat.items.length, 0)}`);
            this.showToast('New suggestions generated based on context', 'info');
            
        } catch (error) {
            console.error('Error generating contextual suggestions:', error);
            this.showToast('Error generating suggestions, using fallback', 'warning');
            this.showFallbackSuggestions();
        }
    }
    
    generateQuickStartSuggestions() {
        return [
            {
                text: "What can you help me with today?",
                context: "General capabilities overview",
                icon: "❓"
            },
            {
                text: "Show me my system status",
                context: "Check system health and performance",
                icon: "📊"
            },
            {
                text: "Help me organize my tasks",
                context: "Task management and productivity",
                icon: "✅"
            },
            {
                text: "Generate a creative image",
                context: "AI image generation with Stable Diffusion",
                icon: "🎨"
            }
        ];
    }
    
    generatePersonalizedSuggestions() {
        const suggestions = [];
        const profile = this.userContext.profile;
        
        if (profile.skill_level === 'beginner') {
            suggestions.push({
                text: "Give me a beginner's guide to AI assistants",
                context: "Perfect for getting started",
                icon: "🎓"
            });
        } else if (profile.skill_level === 'expert') {
            suggestions.push({
                text: "Show me advanced AI model configurations",
                context: "Expert-level customization",
                icon: "⚙️"
            });
        }
        
        // Based on most used tasks
        if (profile.most_used_tasks && profile.most_used_tasks.includes('coding')) {
            suggestions.push({
                text: "Help me write and debug code",
                context: "Code assistance and debugging",
                icon: "💻"
            });
        }
        
        if (profile.total_interactions > 50) {
            suggestions.push({
                text: "What's new since my last session?",
                context: "Updates and improvements",
                icon: "🆕"
            });
        }
        
        return suggestions.length > 0 ? suggestions : this.generateFallbackPersonalized();
    }
    
    generateFallbackPersonalized() {
        return [
            {
                text: "Customize my AI experience",
                context: "Personalization settings",
                icon: "🎛️"
            },
            {
                text: "Learn about my usage patterns",
                context: "Analytics and insights",
                icon: "📈"
            }
        ];
    }
    
    generateFeatureDiscoverySuggestions() {
        const features = [
            {
                text: "Create a voice note",
                context: "Text-to-speech functionality",
                icon: "🎤"
            },
            {
                text: "Search my knowledge base",
                context: "RAG document search",
                icon: "📚"
            },
            {
                text: "Generate a video",
                context: "AI video creation",
                icon: "🎬"
            },
            {
                text: "Connect external data sources",
                context: "GitHub, Drive, Notion integration",
                icon: "🔗"
            },
            {
                text: "Run a system health check",
                context: "Performance monitoring",
                icon: "🏥"
            },
            {
                text: "Download new AI models",
                context: "Expand AI capabilities",
                icon: "📦"
            }
        ];
        
        // Return 3 random features
        return features.sort(() => 0.5 - Math.random()).slice(0, 3);
    }
    
    generateFollowUpSuggestions() {
        const lastContext = this.contextHistory[this.contextHistory.length - 1];
        
        if (lastContext?.includes('image')) {
            return [
                {
                    text: "Generate a similar image with different style",
                    context: "Style variations",
                    icon: "🎨"
                },
                {
                    text: "Explain the image generation process",
                    context: "Learn how it works",
                    icon: "🔍"
                }
            ];
        }
        
        if (lastContext?.includes('code')) {
            return [
                {
                    text: "Optimize this code for performance",
                    context: "Code optimization",
                    icon: "⚡"
                },
                {
                    text: "Add error handling to this code",
                    context: "Improve robustness",
                    icon: "🛡️"
                }
            ];
        }
        
        return [
            {
                text: "Elaborate on that topic",
                context: "More detailed explanation",
                icon: "📖"
            },
            {
                text: "Give me related examples",
                context: "Practical examples",
                icon: "💡"
            }
        ];
    }
    
    generateTopicSpecificSuggestions(topic) {
        console.log('Generating topic-specific suggestions for:', topic);
        
        const topicSuggestions = {
            'image': [
                {
                    text: "Generate an image with different art style",
                    context: "Explore various artistic styles",
                    icon: "🎨"
                },
                {
                    text: "Create variations of the same subject",
                    context: "Multiple interpretations",
                    icon: "🔄"
                },
                {
                    text: "Improve image quality and resolution",
                    context: "Enhance and upscale",
                    icon: "✨"
                }
            ],
            'code': [
                {
                    text: "Review this code for bugs and improvements",
                    context: "Code quality analysis",
                    icon: "🔍"
                },
                {
                    text: "Add documentation and comments",
                    context: "Improve code readability",
                    icon: "📝"
                },
                {
                    text: "Optimize for performance and efficiency",
                    context: "Performance tuning",
                    icon: "⚡"
                }
            ],
            'writing': [
                {
                    text: "Expand this content with more details",
                    context: "Content development",
                    icon: "📈"
                },
                {
                    text: "Rewrite in a different tone or style",
                    context: "Style adaptation",
                    icon: "🎭"
                },
                {
                    text: "Check grammar and improve clarity",
                    context: "Editorial review",
                    icon: "✏️"
                }
            ],
            'analysis': [
                {
                    text: "Provide deeper insights on this data",
                    context: "Advanced analysis",
                    icon: "🔬"
                },
                {
                    text: "Compare with industry benchmarks",
                    context: "Comparative analysis",
                    icon: "📊"
                },
                {
                    text: "Suggest actionable recommendations",
                    context: "Strategic insights",
                    icon: "💡"
                }
            ],
            'creative': [
                {
                    text: "Brainstorm alternative creative approaches",
                    context: "Creative exploration",
                    icon: "💭"
                },
                {
                    text: "Develop this idea into a full concept",
                    context: "Concept development",
                    icon: "🌱"
                },
                {
                    text: "Create a step-by-step implementation plan",
                    context: "Execution strategy",
                    icon: "📋"
                }
            ]
        };
        
        return topicSuggestions[topic] || [
            {
                text: `Tell me more about ${topic}`,
                context: "Learn more about this topic",
                icon: "❓"
            }
        ];
    }

    generateProductiveSuggestions() {
        console.log('Generating productive task suggestions');
        
        const currentHour = new Date().getHours();
        const timeBasedSuggestions = [];
        
        if (currentHour >= 9 && currentHour <= 17) {
            // Work hours
            timeBasedSuggestions.push({
                text: "Help me plan my workday efficiently",
                context: "Productivity planning for work hours",
                icon: "📅"
            });
            timeBasedSuggestions.push({
                text: "Draft a professional email or document",
                context: "Business communication",
                icon: "✉️"
            });
        } else if (currentHour >= 18 && currentHour <= 22) {
            // Evening
            timeBasedSuggestions.push({
                text: "Help me plan tomorrow's priorities",
                context: "Evening planning session",
                icon: "🌅"
            });
            timeBasedSuggestions.push({
                text: "Suggest creative evening projects",
                context: "Creative and personal time",
                icon: "🎭"
            });
        } else {
            // Morning or late night
            timeBasedSuggestions.push({
                text: "What should I learn or explore today?",
                context: "Learning and growth opportunities",
                icon: "🎓"
            });
        }
        
        return [
            ...timeBasedSuggestions,
            {
                text: "Summarize and analyze recent documents",
                context: "Document analysis and insights",
                icon: "📄"
            },
            {
                text: "Create a presentation or report outline",
                context: "Content structure and organization",
                icon: "📊"
            },
            {
                text: "Research a topic with comprehensive analysis",
                context: "In-depth research and investigation",
                icon: "🔬"
            },
            {
                text: "Help me solve a complex problem",
                context: "Problem-solving assistance",
                icon: "🧩"
            }
        ];
    }
    
    displaySuggestions() {
        console.log('Displaying suggestions');
        
        const container = document.getElementById('suggestions-content');
        if (!container) {
            console.warn('Suggestions container not found');
            return;
        }
        
        try {
            if (this.suggestions.length === 0) {
                container.innerHTML = '<div class="suggestions-empty">No suggestions available at the moment. Try interacting with the chat to get contextual suggestions!</div>';
                console.log('No suggestions to display, showing empty state');
                return;
            }
            
            let html = '';
            let totalItems = 0;
            
            this.suggestions.forEach(category => {
                if (category.items.length === 0) return;
                
                html += `
                    <div class="suggestion-category">
                        <div class="category-title">${category.category}</div>
                        <div class="suggestions-grid">
                            ${category.items.map(item => `
                                <div class="suggestion-item" data-suggestion-text="${this.escapeHtml(item.text)}" data-category="${category.category}">
                                    <div class="suggestion-text">
                                        <span class="suggestion-icon">${item.icon}</span>
                                        ${item.text}
                                    </div>
                                    <div class="suggestion-context">${item.context}</div>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                `;
                totalItems += category.items.length;
            });
            
            container.innerHTML = html;
            console.log(`Successfully displayed ${totalItems} suggestions across ${this.suggestions.length} categories`);
            
            // Add enhanced click handlers after rendering
            setTimeout(() => {
                this.attachSuggestionClickHandlers();
            }, 100);
            
        } catch (error) {
            console.error('Error displaying suggestions:', error);
            container.innerHTML = '<div class="suggestions-empty">Error loading suggestions. Please try refreshing.</div>';
            this.showToast('Error displaying suggestions', 'error');
        }
    }

    attachSuggestionClickHandlers() {
        console.log('Attaching enhanced suggestion click handlers');
        
        const suggestionItems = document.querySelectorAll('.suggestion-item');
        suggestionItems.forEach(item => {
            const suggestionText = item.getAttribute('data-suggestion-text');
            const category = item.getAttribute('data-category');
            
            const clickHandler = (e) => {
                e.preventDefault();
                console.log(`Suggestion clicked: "${suggestionText}" from category: ${category}`);
                
                // Add visual feedback
                item.style.transform = 'scale(0.95)';
                item.style.opacity = '0.7';
                
                setTimeout(() => {
                    item.style.transform = '';
                    item.style.opacity = '';
                }, 150);
                
                // Apply the suggestion
                this.applySuggestionEnhanced(suggestionText);
                
                // Track usage for future personalization
                this.trackSuggestionUsage(suggestionText, category);
            };
            
            if (window.eventManager && window.eventManager.add) {
                window.eventManager.add(item, 'click', clickHandler);
            } else {
                item.addEventListener('click', clickHandler);
            }
        });
        
        console.log(`Attached click handlers to ${suggestionItems.length} suggestion items`);
    }

    trackSuggestionUsage(suggestionText, category) {
        console.log('Tracking suggestion usage:', { text: suggestionText, category });
        
        try {
            // Store usage data for personalization
            const usageData = JSON.parse(localStorage.getItem('smartSuggestionsUsage') || '[]');
            usageData.push({
                text: suggestionText,
                category,
                timestamp: new Date().toISOString(),
                context: this.currentTopic
            });
            
            // Keep only last 100 usage records
            if (usageData.length > 100) {
                usageData.splice(0, usageData.length - 100);
            }
            
            localStorage.setItem('smartSuggestionsUsage', JSON.stringify(usageData));
            console.log('Suggestion usage tracked and stored');
            
        } catch (error) {
            console.error('Error tracking suggestion usage:', error);
        }
    }
    
    showFallbackSuggestions() {
        const fallbackSuggestions = [
            {
                category: '💡 Getting Started',
                items: [
                    {
                        text: "What are your capabilities?",
                        context: "Learn about AI features",
                        icon: "❓"
                    },
                    {
                        text: "Help me with a task",
                        context: "General assistance",
                        icon: "🎯"
                    },
                    {
                        text: "Show me the settings",
                        context: "Configuration options",
                        icon: "⚙️"
                    }
                ]
            }
        ];
        
        this.suggestions = fallbackSuggestions;
        this.displaySuggestions();
    }
    
    setupEventListeners() {
        console.log('Setting up smart suggestions event listeners');
        
        // Listen for chat messages to update context
        const chatMessageHandler = (e) => {
            try {
                if (e.detail && e.detail.message) {
                    console.log('Chat message detected:', e.detail.message);
                    this.updateContextHistory(e.detail.message);
                    this.showToast('Context updated with new message', 'info');
                }
            } catch (error) {
                console.error('Error handling chat message:', error);
            }
        };
        
        if (window.eventManager && window.eventManager.add) {
            window.eventManager.add(document, 'chatMessage', chatMessageHandler);
            this.cleanupFunctions.push(() => {
                window.eventManager.remove(document, 'chatMessage', chatMessageHandler);
            });
        } else {
            // Fallback event handling
            document.addEventListener('chatMessage', chatMessageHandler);
            this.cleanupFunctions.push(() => {
                document.removeEventListener('chatMessage', chatMessageHandler);
            });
        }
        
        // Listen for suggestion clicks with enhanced handling
        const suggestionClickHandler = (e) => {
            const suggestionItem = e.target.closest('.suggestion-item');
            if (suggestionItem) {
                const suggestionText = suggestionItem.querySelector('.suggestion-text');
                if (suggestionText) {
                    const text = suggestionText.textContent.replace(/^[^\w]*/, '').trim(); // Remove icon
                    console.log('Suggestion clicked:', text);
                    this.applySuggestionEnhanced(text);
                    e.preventDefault();
                }
            }
        };
        
        // Add click handler to suggestions container
        const suggestionsContainer = document.getElementById('suggestions-content');
        if (suggestionsContainer) {
            if (window.eventManager && window.eventManager.add) {
                window.eventManager.add(suggestionsContainer, 'click', suggestionClickHandler);
                this.cleanupFunctions.push(() => {
                    window.eventManager.remove(suggestionsContainer, 'click', suggestionClickHandler);
                });
            } else {
                suggestionsContainer.addEventListener('click', suggestionClickHandler);
                this.cleanupFunctions.push(() => {
                    suggestionsContainer.removeEventListener('click', suggestionClickHandler);
                });
            }
        }
        
        // Enhanced refresh button functionality
        const refreshHandler = () => {
            console.log('Refreshing suggestions manually');
            this.refreshSuggestions();
        };
        
        // Add refresh functionality to suggestions header
        setTimeout(() => {
            const suggestionsHeader = document.querySelector('.suggestions-header');
            if (suggestionsHeader && !suggestionsHeader.querySelector('.refresh-btn')) {
                const refreshBtn = document.createElement('button');
                refreshBtn.className = 'refresh-btn';
                refreshBtn.innerHTML = '🔄';
                refreshBtn.title = 'Refresh suggestions';
                refreshBtn.style.cssText = `
                    background: none;
                    border: none;
                    color: var(--text-secondary);
                    cursor: pointer;
                    font-size: 1em;
                    padding: 4px;
                    margin-left: 8px;
                    border-radius: 4px;
                    transition: all 0.2s ease;
                `;
                refreshBtn.addEventListener('mouseover', () => {
                    refreshBtn.style.background = 'var(--accent-color-fade)';
                });
                refreshBtn.addEventListener('mouseout', () => {
                    refreshBtn.style.background = 'none';
                });
                
                if (window.eventManager && window.eventManager.add) {
                    window.eventManager.add(refreshBtn, 'click', refreshHandler);
                    this.cleanupFunctions.push(() => {
                        window.eventManager.remove(refreshBtn, 'click', refreshHandler);
                    });
                } else {
                    refreshBtn.addEventListener('click', refreshHandler);
                    this.cleanupFunctions.push(() => {
                        refreshBtn.removeEventListener('click', refreshHandler);
                    });
                }
                
                const titleElement = suggestionsHeader.querySelector('.suggestions-title');
                if (titleElement) {
                    titleElement.appendChild(refreshBtn);
                }
            }
        }, 100);
        
        // Adaptive polling based on user activity
        this.setupAdaptivePolling();
        
        console.log('Smart suggestions event listeners setup completed');
        this.showToast('Smart suggestions initialized', 'success');
    }
    
    applySuggestionEnhanced(text) {
        console.log('Applying enhanced suggestion:', text);
        
        try {
            // Find chat input and apply suggestion
            const chatInput = document.querySelector('#user-input') || 
                             document.querySelector('.chat-input') || 
                             document.querySelector('input[type="text"]') ||
                             document.querySelector('textarea');
            
            if (chatInput) {
                chatInput.value = text;
                chatInput.focus();
                
                // Trigger input event to update any watchers
                chatInput.dispatchEvent(new Event('input', { bubbles: true }));
                
                // Update context history with applied suggestion
                this.updateContextHistory(text);
                
                this.showToast('Suggestion applied successfully', 'success');
                console.log('Suggestion applied to chat input');
                
                // Auto-submit if there's a submit button nearby
                const submitBtn = chatInput.parentElement?.querySelector('button') ||
                                 document.querySelector('.send-button') ||
                                 document.querySelector('#send-button') ||
                                 document.querySelector('[type="submit"]');
                
                if (submitBtn) {
                    // Add a small delay to let user see the suggestion was applied
                    setTimeout(() => {
                        this.showToast('Press Enter or click Send to submit', 'info');
                    }, 1000);
                }
            } else {
                this.showToast('Chat input not found', 'warning');
                console.warn('Chat input element not found');
            }
        } catch (error) {
            console.error('Error applying suggestion:', error);
            this.showToast('Error applying suggestion', 'error');
        }
    }

    async refreshSuggestions() {
        console.log('Refreshing suggestions');
        
        try {
            this.showToast('Refreshing suggestions...', 'info');
            
            // Update user context
            await this.updateUserContext();
            
            // Regenerate suggestions
            this.generateContextualSuggestions();
            
            // Display updated suggestions
            this.displaySuggestions();
            
            this.showToast('Suggestions refreshed successfully', 'success');
            console.log('Suggestions refreshed successfully');
            
        } catch (error) {
            console.error('Error refreshing suggestions:', error);
            this.showToast('Error refreshing suggestions', 'error');
            
            // Fallback to showing default suggestions
            this.showFallbackSuggestions();
        }
    }

    showToast(message, type = 'info') {
        console.log(`Smart Suggestions Toast (${type}): ${message}`);
        
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
        toast.className = `smart-suggestions-toast toast-${type}`;
        toast.style.cssText = `
            position: fixed;
            top: 140px;
            right: 20px;
            background: ${type === 'error' ? '#dc3545' : type === 'success' ? '#28a745' : type === 'warning' ? '#ffc107' : '#007bff'};
            color: ${type === 'warning' ? '#000' : '#fff'};
            padding: 10px 14px;
            border-radius: 6px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            z-index: 10001;
            max-width: 280px;
            font-size: 0.85rem;
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
        
        // Auto remove after 3.5 seconds
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(100%)';
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
            }, 300);
        }, 3500);
    }

    updateContextHistory(message) {
        console.log('Updating context history with message:', message);
        
        this.contextHistory.push(message);
        
        // Keep only last 5 messages for context
        if (this.contextHistory.length > 5) {
            this.contextHistory.shift();
        }
        
        // Analyze current topic
        this.currentTopic = this.extractTopic(message);
        console.log('Current topic identified as:', this.currentTopic);
        
        // Save context for persistence
        this.saveUserContext();
        
        // Regenerate suggestions based on new context
        setTimeout(() => {
            this.generateContextualSuggestions();
            this.displaySuggestions();
        }, 1000);
    }
    
    setupAdaptivePolling() {
        console.log('Setting up adaptive polling for suggestions');
        
        let lastActivity = Date.now();
        let pollInterval = 600000; // Start with 10 minutes
        
        // Track user activity
        const activityEvents = ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart'];
        activityEvents.forEach(event => {
            const activityHandler = () => {
                lastActivity = Date.now();
                // Reduce polling interval when user is active
                pollInterval = Math.max(300000, pollInterval - 60000); // Min 5 minutes
                console.log(`User activity detected (${event}), poll interval: ${pollInterval / 1000}s`);
            };
            
            if (window.eventManager && window.eventManager.add) {
                window.eventManager.add(document, event, activityHandler, { passive: true });
                this.cleanupFunctions.push(() => {
                    window.eventManager.remove(document, event, activityHandler);
                });
            } else {
                // Fallback event handling
                document.addEventListener(event, activityHandler, { passive: true });
                this.cleanupFunctions.push(() => {
                    document.removeEventListener(event, activityHandler);
                });
            }
        });
        
        // Adaptive polling based on activity
        const adaptivePoll = async () => {
            try {
                const timeSinceActivity = Date.now() - lastActivity;
                
                // Increase interval if user is inactive
                if (timeSinceActivity > 300000) { // 5 minutes
                    pollInterval = Math.min(1800000, pollInterval + 300000); // Max 30 minutes
                }
                
                console.log(`Adaptive polling: ${pollInterval / 1000}s interval, last activity: ${timeSinceActivity / 1000}s ago`);
                
                // Only update if user has been somewhat active recently
                if (timeSinceActivity < 3600000) { // 1 hour
                    await this.updateUserContext();
                    this.generateContextualSuggestions();
                    this.displaySuggestions();
                    console.log('Suggestions updated via adaptive polling');
                }
                
                setTimeout(adaptivePoll, pollInterval);
            } catch (error) {
                console.error('Error in adaptive polling:', error);
                // Retry with longer interval on error
                setTimeout(adaptivePoll, pollInterval * 2);
            }
        };
        
        // Start polling after initial delay
        setTimeout(adaptivePoll, pollInterval);
        console.log('Adaptive polling started');
    }
    
    extractTopic(message) {
        const topics = {
            'image': ['image', 'picture', 'photo', 'visual', 'generate', 'create'],
            'code': ['code', 'programming', 'function', 'script', 'debug'],
            'writing': ['write', 'essay', 'document', 'text', 'content'],
            'analysis': ['analyze', 'data', 'research', 'study', 'examine'],
            'creative': ['creative', 'story', 'idea', 'brainstorm', 'design']
        };
        
        const lowerMessage = message.toLowerCase();
        
        for (const [topic, keywords] of Object.entries(topics)) {
            if (keywords.some(keyword => lowerMessage.includes(keyword))) {
                return topic;
            }
        }
        
        return 'general';
    }
    
    loadUserContext() {
        const stored = localStorage.getItem('smartSuggestionsContext');
        return stored ? JSON.parse(stored) : {};
    }
    
    saveUserContext() {
        localStorage.setItem('smartSuggestionsContext', JSON.stringify(this.userContext));
    }
    
    loadUserPreferences() {
        const stored = localStorage.getItem('smartSuggestionsPreferences');
        return stored ? JSON.parse(stored) : {
            categories: ['quick_start', 'personalized', 'features', 'productive'],
            maxSuggestions: 12,
            refreshInterval: 300000
        };
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Enhanced global functions
function applySuggestion(text) {
    console.log('Global applySuggestion called with:', text);
    
    if (window.smartSuggestions && window.smartSuggestions.applySuggestionEnhanced) {
        window.smartSuggestions.applySuggestionEnhanced(text);
    } else {
        // Fallback implementation
        const chatInput = document.querySelector('#user-input') || 
                         document.querySelector('.chat-input') || 
                         document.querySelector('input[type="text"]');
        
        if (chatInput) {
            chatInput.value = text;
            chatInput.focus();
            chatInput.dispatchEvent(new Event('input', { bubbles: true }));
            console.log('Fallback: Applied suggestion to chat input');
        } else {
            console.warn('Chat input not found for suggestion application');
        }
    }
}

function toggleSuggestions() {
    console.log('Toggling suggestions visibility');
    
    const container = document.getElementById('smart-suggestions');
    if (container) {
        const content = container.querySelector('.suggestions-content');
        const toggle = container.querySelector('.suggestions-toggle');
        
        if (content && toggle) {
            if (content.style.display === 'none') {
                content.style.display = 'block';
                toggle.textContent = '×';
                console.log('Suggestions shown');
            } else {
                content.style.display = 'none';
                toggle.textContent = '+';
                console.log('Suggestions hidden');
            }
        }
    } else {
        console.warn('Smart suggestions container not found');
    }
}

// Enhanced initialization
const initializeSmartSuggestions = () => {
    console.log('Initializing Smart Suggestions system');
    
    try {
        if (typeof window.eventManager !== 'undefined') {
            window.smartSuggestions = new SmartSuggestions();
            console.log('Smart Suggestions initialized successfully');
        } else {
            console.warn('Event manager not available, retrying in 1 second');
            setTimeout(initializeSmartSuggestions, 1000);
        }
    } catch (error) {
        console.error('Error initializing Smart Suggestions:', error);
        // Retry initialization after delay
        setTimeout(initializeSmartSuggestions, 2000);
    }
};

// Initialize when DOM is ready with enhanced error handling
if (window.eventManager && window.eventManager.add) {
    window.eventManager.add(document, 'DOMContentLoaded', initializeSmartSuggestions);
} else {
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeSmartSuggestions);
    } else {
        // DOM already loaded
        initializeSmartSuggestions();
    }
}

// Export for global access
window.applySuggestion = applySuggestion;
window.toggleSuggestions = toggleSuggestions;
