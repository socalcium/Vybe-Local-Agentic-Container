/**
 * Professional Onboarding Manager
 * Provides guided tours and first-time user experience
 */

export class OnboardingManager {
    constructor() {
        this.isFirstVisit = localStorage.getItem('vybe_first_visit') === null;
        this.currentStep = 0;
        this.tourSteps = [
            {
                target: '#chat-interface',
                title: 'Welcome to Vybe AI! 👋',
                content: 'Start conversations with powerful AI models. Ask questions, get help with tasks, or just chat!',
                position: 'bottom'
            },
            {
                target: '.nav-link[href*="rag"]',
                title: 'Knowledge Base 📚',
                content: 'Upload documents to create your personal knowledge base. Vybe will use this to answer questions about your files.',
                position: 'bottom'
            },
            {
                target: '.nav-link[href*="image"]',
                title: 'Image Studio 🎨',
                content: 'Generate stunning AI-powered images using Stable Diffusion. Just describe what you want to see!',
                position: 'bottom'
            },
            {
                target: '.nav-link[href*="settings"]',
                title: 'Settings ⚙️',
                content: 'Customize your experience, manage AI models, and configure advanced features.',
                position: 'bottom'
            },
            {
                target: '.user-menu',
                title: 'Profile & More 👤',
                content: 'Access your profile, view usage statistics, and explore additional tools and features.',
                position: 'left'
            }
        ];

        // Cleanup functions for event listeners
        this.cleanupFunctions = [];
        
        this.overlay = null;
        this.tooltip = null;
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
        if (this.isFirstVisit) {
            this.showWelcomeModal();
        }
        this.addHelpButton();
        this.setupEventListeners();
    }

    setupEventListeners() {
        // Setup global keyboard shortcuts
        const keydownHandler = (e) => {
            if (this.tooltip) {
                if (e.key === 'Escape') {
                    e.preventDefault();
                    this.completeTour();
                } else if (e.key === 'ArrowRight' && this.currentStep < this.tourSteps.length - 1) {
                    e.preventDefault();
                    this.nextStep();
                } else if (e.key === 'ArrowLeft' && this.currentStep > 0) {
                    e.preventDefault();
                    this.previousStep();
                }
            }
        };

        if (window.eventManager) {
            const cleanup = window.eventManager.add(document, 'keydown', keydownHandler);
            this.cleanupFunctions.push(cleanup);
        } else {
            document.addEventListener('keydown', keydownHandler);
            this.cleanupFunctions.push(() => {
                document.removeEventListener('keydown', keydownHandler);
            });
        }

        // Setup window resize handler for tooltip repositioning
        const resizeHandler = () => {
            if (this.tooltip && this.tourSteps[this.currentStep]) {
                const target = document.querySelector(this.tourSteps[this.currentStep].target);
                if (target) {
                    this.positionTooltip(this.tooltip, target, this.tourSteps[this.currentStep].position);
                }
            }
        };

        if (window.eventManager) {
            const cleanup = window.eventManager.add(window, 'resize', resizeHandler);
            this.cleanupFunctions.push(cleanup);
        } else {
            window.addEventListener('resize', resizeHandler);
            this.cleanupFunctions.push(() => {
                window.removeEventListener('resize', resizeHandler);
            });
        }
    }

    showWelcomeModal() {
        const modal = this.createWelcomeModal();
        document.body.appendChild(modal);
        modal.classList.add('show');
    }

    createWelcomeModal() {
        const modal = document.createElement('div');
        modal.className = 'onboarding-modal';
        modal.innerHTML = `
            <div class="onboarding-modal-content">
                <div class="onboarding-modal-header">
                    <h2>🚀 Welcome to Vybe AI Assistant!</h2>
                    <p>Your all-in-one AI-powered productivity companion</p>
                </div>
                <div class="onboarding-modal-body">
                    <div class="feature-grid">
                        <div class="feature-card">
                            <div class="feature-icon">💬</div>
                            <h3>Smart Conversations</h3>
                            <p>Chat with advanced AI models like GPT, Claude, and local LLMs</p>
                        </div>
                        <div class="feature-card">
                            <div class="feature-icon">📚</div>
                            <h3>Knowledge Base</h3>
                            <p>Upload documents and let AI answer questions about your content</p>
                        </div>
                        <div class="feature-card">
                            <div class="feature-icon">🎨</div>
                            <h3>Image Generation</h3>
                            <p>Create stunning visuals with AI-powered image generation</p>
                        </div>
                        <div class="feature-card">
                            <div class="feature-icon">🔧</div>
                            <h3>Productivity Tools</h3>
                            <p>File management, web search, and automation features</p>
                        </div>
                    </div>
                </div>
                <div class="onboarding-modal-footer">
                    <button class="btn btn-secondary skip-tour-btn">Skip Tour</button>
                    <button class="btn btn-primary start-tour-btn">Take the Tour</button>
                </div>
            </div>
            <div class="onboarding-modal-backdrop"></div>
        `;

        // Bind event handlers properly
        const skipBtn = modal.querySelector('.skip-tour-btn');
        const startBtn = modal.querySelector('.start-tour-btn');
        const backdrop = modal.querySelector('.onboarding-modal-backdrop');

        const skipHandler = () => this.skipTour();
        const startHandler = () => this.startTour();

        if (window.eventManager) {
            const skipCleanup = window.eventManager.add(skipBtn, 'click', skipHandler);
            const startCleanup = window.eventManager.add(startBtn, 'click', startHandler);
            const backdropCleanup = window.eventManager.add(backdrop, 'click', skipHandler);
            
            // Store cleanup functions on the modal for later removal
            modal._cleanupFunctions = [skipCleanup, startCleanup, backdropCleanup];
        } else {
            skipBtn.addEventListener('click', skipHandler);
            startBtn.addEventListener('click', startHandler);
            backdrop.addEventListener('click', skipHandler);
            
            modal._cleanupFunctions = [
                () => skipBtn.removeEventListener('click', skipHandler),
                () => startBtn.removeEventListener('click', startHandler),
                () => backdrop.removeEventListener('click', skipHandler)
            ];
        }

        return modal;
    }

    startTour() {
        this.closeWelcomeModal();
        this.currentStep = 0;
        this.createOverlay();
        this.showStep(this.currentStep);
    }

    skipTour() {
        this.closeWelcomeModal();
        this.markAsVisited();
    }

    createOverlay() {
        this.overlay = document.createElement('div');
        this.overlay.className = 'onboarding-overlay';
        document.body.appendChild(this.overlay);
    }

    showStep(stepIndex) {
        if (stepIndex >= this.tourSteps.length) {
            this.completeTour();
            return;
        }

        const step = this.tourSteps[stepIndex];
        const target = document.querySelector(step.target);
        
        if (!target) {
            console.warn(`Onboarding target not found: ${step.target}`);
            // Try to wait a bit and retry, or skip to next step
            setTimeout(() => {
                const retryTarget = document.querySelector(step.target);
                if (retryTarget) {
                    this.highlightElement(retryTarget);
                    this.showTooltip(retryTarget, step);
                } else {
                    this.nextStep(); // Skip this step if target still not found
                }
            }, 500);
            return;
        }

        this.highlightElement(target);
        this.showTooltip(target, step);
        
        // Emit custom event for step change
        this.emitEvent('stepChanged', {
            stepIndex,
            step,
            target: step.target
        });
    }

    highlightElement(element) {
        // Remove previous highlights
        document.querySelectorAll('.onboarding-highlight').forEach(el => {
            el.classList.remove('onboarding-highlight');
        });

        // Add highlight to current element
        element.classList.add('onboarding-highlight');
        element.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }

    showTooltip(target, step) {
        // Remove existing tooltip
        if (this.tooltip) {
            // Clean up existing event listeners
            if (this.tooltip._cleanupFunctions) {
                this.tooltip._cleanupFunctions.forEach(cleanup => {
                    try {
                        cleanup();
                    } catch (error) {
                        console.error('Error cleaning up tooltip events:', error);
                    }
                });
            }
            this.tooltip.remove();
        }

        this.tooltip = document.createElement('div');
        this.tooltip.className = 'onboarding-tooltip';
        this.tooltip.innerHTML = `
            <div class="onboarding-tooltip-content">
                <h3>${step.title}</h3>
                <p>${step.content}</p>
                <div class="onboarding-tooltip-actions">
                    <span class="step-counter">${this.currentStep + 1} of ${this.tourSteps.length}</span>
                    <div class="action-buttons">
                        ${this.currentStep > 0 ? '<button class="btn btn-sm btn-secondary" data-action="previous">Previous</button>' : ''}
                        ${this.currentStep < this.tourSteps.length - 1 ? 
                            '<button class="btn btn-sm btn-primary" data-action="next">Next</button>' : 
                            '<button class="btn btn-sm btn-success" data-action="finish">Finish</button>'
                        }
                        <button class="btn btn-sm btn-outline-secondary" data-action="skip">Skip Tour</button>
                    </div>
                    <button class="tooltip-close" data-action="close" aria-label="Close tour">×</button>
                </div>
            </div>
        `;

        // Position tooltip
        this.positionTooltip(this.tooltip, target, step.position);
        document.body.appendChild(this.tooltip);

        // Bind events with proper cleanup tracking
        const eventHandlers = [
            { selector: '[data-action="previous"]', handler: () => this.previousStep() },
            { selector: '[data-action="next"]', handler: () => this.nextStep() },
            { selector: '[data-action="finish"]', handler: () => this.completeTour() },
            { selector: '[data-action="skip"]', handler: () => this.completeTour() },
            { selector: '[data-action="close"]', handler: () => this.completeTour() }
        ];

        const cleanupFunctions = [];

        eventHandlers.forEach(({ selector, handler }) => {
            const element = this.tooltip.querySelector(selector);
            if (element) {
                if (window.eventManager) {
                    const cleanup = window.eventManager.add(element, 'click', handler);
                    cleanupFunctions.push(cleanup);
                } else {
                    element.addEventListener('click', handler);
                    cleanupFunctions.push(() => element.removeEventListener('click', handler));
                }
            }
        });

        // Store cleanup functions on tooltip
        this.tooltip._cleanupFunctions = cleanupFunctions;

        // Add smooth appearance animation
        requestAnimationFrame(() => {
            this.tooltip.classList.add('show');
        });
    }

    positionTooltip(tooltip, target, position = 'bottom') {
        const targetRect = target.getBoundingClientRect();
        const tooltipRect = tooltip.getBoundingClientRect();
        
        let top, left;
        
        switch (position) {
            case 'top':
                top = targetRect.top - tooltipRect.height - 10;
                left = targetRect.left + (targetRect.width - tooltipRect.width) / 2;
                break;
            case 'bottom':
                top = targetRect.bottom + 10;
                left = targetRect.left + (targetRect.width - tooltipRect.width) / 2;
                break;
            case 'left':
                top = targetRect.top + (targetRect.height - tooltipRect.height) / 2;
                left = targetRect.left - tooltipRect.width - 10;
                break;
            case 'right':
                top = targetRect.top + (targetRect.height - tooltipRect.height) / 2;
                left = targetRect.right + 10;
                break;
            default:
                top = targetRect.bottom + 10;
                left = targetRect.left + (targetRect.width - tooltipRect.width) / 2;
        }

        // Ensure tooltip stays within viewport
        const viewportWidth = window.innerWidth;
        const viewportHeight = window.innerHeight;
        
        if (left < 10) left = 10;
        if (left + tooltipRect.width > viewportWidth - 10) left = viewportWidth - tooltipRect.width - 10;
        if (top < 10) top = 10;
        if (top + tooltipRect.height > viewportHeight - 10) top = viewportHeight - tooltipRect.height - 10;

        tooltip.style.position = 'fixed';
        tooltip.style.top = `${top}px`;
        tooltip.style.left = `${left}px`;
        tooltip.style.zIndex = '9999';
    }

    nextStep() {
        this.currentStep++;
        this.showStep(this.currentStep);
    }

    previousStep() {
        this.currentStep--;
        this.showStep(this.currentStep);
    }

    completeTour() {
        this.cleanup();
        this.markAsVisited();
        this.showCompletionMessage();
        this.emitEvent('tourCompleted', {
            stepsCompleted: this.currentStep + 1,
            totalSteps: this.tourSteps.length,
            timestamp: Date.now()
        });
    }

    cleanup() {
        // Clean up overlay
        if (this.overlay) {
            this.overlay.remove();
            this.overlay = null;
        }
        
        // Clean up tooltip with event listeners
        if (this.tooltip) {
            if (this.tooltip._cleanupFunctions) {
                this.tooltip._cleanupFunctions.forEach(cleanup => {
                    try {
                        cleanup();
                    } catch (error) {
                        console.error('Error cleaning up tooltip events:', error);
                    }
                });
            }
            this.tooltip.remove();
            this.tooltip = null;
        }
        
        // Remove highlights
        document.querySelectorAll('.onboarding-highlight').forEach(el => {
            el.classList.remove('onboarding-highlight');
        });
    }

    closeWelcomeModal() {
        const modal = document.querySelector('.onboarding-modal');
        if (modal) {
            // Clean up modal event listeners
            if (modal._cleanupFunctions) {
                modal._cleanupFunctions.forEach(cleanup => {
                    try {
                        cleanup();
                    } catch (error) {
                        console.error('Error cleaning up modal events:', error);
                    }
                });
            }
            modal.remove();
        }
    }

    markAsVisited() {
        localStorage.setItem('vybe_first_visit', 'false');
        localStorage.setItem('vybe_tour_completed', 'true');
        localStorage.setItem('vybe_tour_completion_date', new Date().toISOString());
    }

    showCompletionMessage() {
        // Show a brief success message
        if (window.vybeNotification) {
            window.vybeNotification.success('🎉 Tour completed! You\'re ready to explore Vybe AI.', {
                duration: 4000,
                title: 'Welcome Complete'
            });
        } else if (window.showNotification) {
            window.showNotification('🎉 Tour completed! You\'re ready to explore Vybe AI.', 'success');
        } else {
            // Fallback to simple alert
            setTimeout(() => {
                alert('🎉 Tour completed! You\'re ready to explore Vybe AI.');
            }, 100);
        }
    }

    addHelpButton() {
        // Check if help button already exists
        if (document.querySelector('.help-tour-btn')) {
            return;
        }

        // Add a help button to restart the tour
        const helpButton = document.createElement('button');
        helpButton.className = 'help-tour-btn';
        helpButton.innerHTML = '?';
        helpButton.title = 'Take the tour again';
        helpButton.setAttribute('aria-label', 'Start onboarding tour');
        
        // Position in bottom right corner
        helpButton.style.cssText = `
            position: fixed;
            bottom: 20px;
            right: 20px;
            width: 40px;
            height: 40px;
            border-radius: 50%;
            background: var(--primary-color, #007bff);
            color: white;
            border: none;
            font-size: 18px;
            font-weight: bold;
            cursor: pointer;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
            z-index: 1000;
            transition: all 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: center;
        `;
        
        // Event handlers with proper cleanup
        const clickHandler = () => this.restartTour();
        const mouseenterHandler = () => {
            helpButton.style.transform = 'scale(1.1)';
            helpButton.style.boxShadow = '0 4px 15px rgba(0,0,0,0.3)';
        };
        const mouseleaveHandler = () => {
            helpButton.style.transform = 'scale(1)';
            helpButton.style.boxShadow = '0 2px 10px rgba(0,0,0,0.2)';
        };

        if (window.eventManager) {
            const clickCleanup = window.eventManager.add(helpButton, 'click', clickHandler);
            const enterCleanup = window.eventManager.add(helpButton, 'mouseenter', mouseenterHandler);
            const leaveCleanup = window.eventManager.add(helpButton, 'mouseleave', mouseleaveHandler);
            
            this.cleanupFunctions.push(clickCleanup, enterCleanup, leaveCleanup);
        } else {
            helpButton.addEventListener('click', clickHandler);
            helpButton.addEventListener('mouseenter', mouseenterHandler);
            helpButton.addEventListener('mouseleave', mouseleaveHandler);
            
            this.cleanupFunctions.push(
                () => helpButton.removeEventListener('click', clickHandler),
                () => helpButton.removeEventListener('mouseenter', mouseenterHandler),
                () => helpButton.removeEventListener('mouseleave', mouseleaveHandler)
            );
        }
        
        document.body.appendChild(helpButton);
    }

    restartTour() {
        this.currentStep = 0;
        this.createOverlay();
        this.showStep(this.currentStep);
        this.emitEvent('tourRestarted', { timestamp: Date.now() });
    }

    // Custom event emission
    emitEvent(eventName, data) {
        try {
            const event = new CustomEvent(`vybeOnboarding:${eventName}`, {
                detail: data,
                bubbles: true,
                cancelable: true
            });
            document.dispatchEvent(event);
        } catch (error) {
            console.error('Error emitting onboarding event:', error);
        }
    }

    // Public API methods
    isFirstTime() {
        return this.isFirstVisit;
    }

    hasCompletedTour() {
        return localStorage.getItem('vybe_tour_completed') === 'true';
    }

    resetTourStatus() {
        localStorage.removeItem('vybe_first_visit');
        localStorage.removeItem('vybe_tour_completed');
        localStorage.removeItem('vybe_tour_completion_date');
        this.isFirstVisit = true;
    }

    addCustomStep(step) {
        if (step && step.target && step.title && step.content) {
            this.tourSteps.push({
                position: 'bottom',
                ...step
            });
        }
    }

    removeStep(index) {
        if (index >= 0 && index < this.tourSteps.length) {
            this.tourSteps.splice(index, 1);
        }
    }

    // Static getInstance method
    static getInstance() {
        if (!window._onboardingManager) {
            window._onboardingManager = new OnboardingManager();
        }
        return window._onboardingManager;
    }
}

// Auto-initialize and make globally available
const initializeOnboardingManager = () => {
    try {
        if (!window.vybeOnboarding) {
            window.vybeOnboarding = new OnboardingManager();
            window.vybeOnboarding.init();
            console.log('Onboarding Manager initialized successfully');
        }
    } catch (error) {
        console.error('Failed to initialize Onboarding Manager:', error);
        // Fallback: create a minimal onboarding system
        window.vybeOnboarding = {
            init: () => console.log('Onboarding fallback initialized'),
            startTour: () => console.log('Tour feature not available'),
            restartTour: () => console.log('Tour feature not available'),
            isFirstTime: () => false,
            hasCompletedTour: () => true
        };
    }
};

// Initialize when DOM is ready or immediately if already ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeOnboardingManager);
} else {
    initializeOnboardingManager();
}

// Export for module use
export default OnboardingManager;
