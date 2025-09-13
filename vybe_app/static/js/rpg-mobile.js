/**
 * RPG Mobile Interface Controller
 * Handles tab switching and mobile-specific RPG functionality
 */

class RPGMobileController {
    constructor() {
        this.currentTab = 'adventure';
        this.isDesktop = window.innerWidth >= 768;
        this.syncData = new Map();
        this.rpgManager = null; // Reference to main RPG manager
        
        // Cleanup functions for event listeners
        this.cleanupFunctions = [];
        
        console.log('[RPGMobileController] Initializing mobile controller');
        this.init();
    }
    
    // Destroy method to prevent memory leaks
    destroy() {
        console.log('[RPGMobileController] Cleaning up mobile controller');
        
        // Remove all event listeners
        this.cleanupFunctions.forEach(cleanup => {
            try {
                cleanup();
            } catch (error) {
                console.error('[RPGMobileController] Error during cleanup:', error);
            }
        });
        this.cleanupFunctions = [];
    }

    // Helper method to add event listeners with cleanup tracking
    addEventListener(element, event, handler) {
        if (element && typeof element.addEventListener === 'function') {
            element.addEventListener(event, handler);
            this.cleanupFunctions.push(() => {
                element.removeEventListener(event, handler);
            });
        }
    }

    // Debounce utility method
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    // Toast notification method - Updated to use global notification manager
    showToast(message, type = 'info') {
        console.log(`[RPGMobileController] Toast: ${message} (${type})`);
        
        // Use the global notification manager first
        if (window.notificationManager) {
            switch (type) {
                case 'success':
                    window.notificationManager.showSuccess(message);
                    break;
                case 'error':
                    window.notificationManager.showError(message);
                    break;
                case 'warning':
                    window.notificationManager.showWarning(message);
                    break;
                case 'info':
                default:
                    window.notificationManager.showInfo(message);
                    break;
            }
            return;
        }
        
        // Try to use the main RPG manager's toast method as fallback
        if (this.rpgManager && typeof this.rpgManager.showToast === 'function') {
            this.rpgManager.showToast(message, type);
            return;
        }

        // Final fallback toast implementation
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.textContent = message;
        toast.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 12px 20px;
            border-radius: 6px;
            color: white;
            font-weight: 500;
            z-index: 10000;
            max-width: 300px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            transform: translateX(100%);
            transition: transform 0.3s ease;
        `;

        // Set background color based on type
        const colors = {
            success: '#10b981',
            error: '#ef4444', 
            warning: '#f59e0b',
            info: '#3b82f6'
        };
        toast.style.backgroundColor = colors[type] || colors.info;

        document.body.appendChild(toast);

        // Animate in
        setTimeout(() => {
            toast.style.transform = 'translateX(0)';
        }, 10);

        // Auto remove
        setTimeout(() => {
            toast.style.transform = 'translateX(100%)';
            setTimeout(() => {
                if (toast.parentNode) {
                    document.body.removeChild(toast);
                }
            }, 300);
        }, 3000);
    }


    init() {
        console.log('[RPGMobileController] Setting up mobile interface');
        
        // Try to connect to main RPG manager
        this.connectToRPGManager();
        
        this.setupEventListeners();
        this.setupDataSync();
        this.handleResize();
        
        // Initialize with adventure tab active
        this.switchTab('adventure');
        
        // Set up mobile-specific optimizations
        this.setupMobileOptimizations();
        
        this.showToast('Mobile interface ready', 'success');
    }

    connectToRPGManager() {
        // Try to get reference to the main RPG manager
        if (window.rpgManager) {
            this.rpgManager = window.rpgManager;
            console.log('[RPGMobileController] Connected to main RPG manager');
        } else {
            console.warn('[RPGMobileController] Main RPG manager not found');
            // Try again after a short delay
            setTimeout(() => {
                if (window.rpgManager) {
                    this.rpgManager = window.rpgManager;
                    console.log('[RPGMobileController] Connected to main RPG manager (delayed)');
                }
            }, 1000);
        }
    }

    setupMobileOptimizations() {
        console.log('[RPGMobileController] Setting up mobile optimizations');
        
        // Prevent zoom on input focus for iOS
        const inputs = document.querySelectorAll('input[type="text"], textarea, select');
        inputs.forEach(input => {
            this.addEventListener(input, 'focus', () => {
                if (window.navigator.userAgent.includes('iPhone')) {
                    document.querySelector('meta[name=viewport]')?.setAttribute(
                        'content', 
                        'width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no'
                    );
                }
            });
            
            this.addEventListener(input, 'blur', () => {
                if (window.navigator.userAgent.includes('iPhone')) {
                    document.querySelector('meta[name=viewport]')?.setAttribute(
                        'content', 
                        'width=device-width, initial-scale=1, user-scalable=yes'
                    );
                }
            });
        });

        // Add touch-friendly classes
        document.body.classList.add('mobile-optimized');
        
        // Improve button tap targets
        const buttons = document.querySelectorAll('button, .btn');
        buttons.forEach(btn => {
            if (btn.offsetHeight < 44) {
                btn.style.minHeight = '44px';
                btn.style.display = 'flex';
                btn.style.alignItems = 'center';
                btn.style.justifyContent = 'center';
            }
        });
    }

    setupEventListeners() {
        // Tab switching
        document.querySelectorAll('.mobile-tab-btn').forEach(btn => {
            this.addEventListener(btn, 'click', (e) => {
                const tab = e.currentTarget.dataset.tab;
                this.switchTab(tab);
                
                // Haptic feedback if available
                if (navigator.vibrate) {
                    navigator.vibrate(10);
                }
            });
        });

        // Window resize handler
        this.addEventListener(window, 'resize', this.debounce(() => {
            this.handleResize();
        }, 100));

        // Swipe gesture support for tabs
        this.setupSwipeGestures();
        
        // Sync button clicks between mobile and desktop
        this.setupButtonSync();
    }

    setupSwipeGestures() {
        let startX = 0;
        let startY = 0;
        const threshold = 50;
        
        const tabContent = document.querySelector('.rpg-container');
        if (!tabContent) return;

        this.addEventListener(tabContent, 'touchstart', (e) => {
            startX = e.touches[0].clientX;
            startY = e.touches[0].clientY;
        });

        this.addEventListener(tabContent, 'touchend', (e) => {
            if (!e.changedTouches) return;
            
            const endX = e.changedTouches[0].clientX;
            const endY = e.changedTouches[0].clientY;
            const deltaX = endX - startX;
            const deltaY = endY - startY;
            
            // Only swipe if horizontal movement is greater than vertical
            if (Math.abs(deltaX) > Math.abs(deltaY) && Math.abs(deltaX) > threshold) {
                const tabs = ['adventure', 'party', 'inventory', 'quests'];
                const currentIndex = tabs.indexOf(this.currentTab);
                
                if (deltaX > 0 && currentIndex > 0) {
                    // Swipe right - previous tab
                    this.switchTab(tabs[currentIndex - 1]);
                } else if (deltaX < 0 && currentIndex < tabs.length - 1) {
                    // Swipe left - next tab
                    this.switchTab(tabs[currentIndex + 1]);
                }
                
                if (navigator.vibrate) {
                    navigator.vibrate(15);
                }
            }
        }, { passive: true });
    }

    setupDataSync() {
        // Elements that need to stay in sync between mobile and desktop views
        const syncMappings = [
            { mobile: '#campaignName', desktop: '#campaignName-desktop' },
            { mobile: '#campaignDescription', desktop: '#campaignDescription-desktop' },
            { mobile: '#currentScene', desktop: '#currentScene-desktop' },
            { mobile: '#chatMessages', desktop: '#chatMessages-desktop' },
            { mobile: '#turnCount', desktop: '#turnCount-desktop' },
            { mobile: '#partySize', desktop: '.party-size' },
            { mobile: '#partyLevel', desktop: '.party-level' },
            { mobile: '#partyHealth', desktop: '.party-health' },
            { mobile: '#charactersList', desktop: '.characters-list-desktop' },
            { mobile: '#npcsList', desktop: '.npcs-list-desktop' },
            { mobile: '#inventoryList', desktop: '.inventory-list-desktop' },
            { mobile: '#questLog', desktop: '.quest-log-desktop' },
            { mobile: '#eventLog', desktop: '.event-log-desktop' }
        ];

        // Set up observers for content sync
        syncMappings.forEach(({ mobile, desktop }) => {
            const mobileEl = document.querySelector(mobile);
            const desktopEl = document.querySelector(desktop);
            
            if (mobileEl && desktopEl) {
                const observer = new MutationObserver(() => {
                    if (mobileEl.innerHTML !== desktopEl.innerHTML) {
                        desktopEl.innerHTML = mobileEl.innerHTML;
                    }
                });
                
                observer.observe(mobileEl, {
                    childList: true,
                    subtree: true,
                    characterData: true
                });
                
                // Sync desktop changes to mobile too
                const desktopObserver = new MutationObserver(() => {
                    if (desktopEl.innerHTML !== mobileEl.innerHTML) {
                        mobileEl.innerHTML = desktopEl.innerHTML;
                    }
                });
                
                desktopObserver.observe(desktopEl, {
                    childList: true,
                    subtree: true,
                    characterData: true
                });
            }
        });
    }

    setupButtonSync() {
        // Sync button clicks between mobile and desktop versions
        const buttonMappings = [
            { mobile: '#newCampaignBtn', desktop: '.new-campaign-btn' },
            { mobile: '#loadCampaignBtn', desktop: '.load-campaign-btn' },
            { mobile: '#saveCampaignBtn', desktop: '.save-campaign-btn' },
            { mobile: '#rollDiceBtn', desktop: '.roll-dice-btn' },
            { mobile: '#sendActionBtn', desktop: '.send-action-btn' },
            { mobile: '#addCharacterBtn', desktop: '.add-character-btn' },
            { mobile: '#addItemBtn', desktop: '.add-item-btn' },
            { mobile: '#addQuestBtn', desktop: '.add-quest-btn' }
        ];

        buttonMappings.forEach(({ mobile, desktop }) => {
            const mobileBtn = document.querySelector(mobile);
            const desktopBtn = document.querySelector(desktop);
            
            if (mobileBtn && desktopBtn) {
                this.addEventListener(mobileBtn, 'click', () => {
                    // Trigger desktop button click
                    desktopBtn.click();
                });
                
                this.addEventListener(desktopBtn, 'click', () => {
                    // Update mobile button state if needed
                    if (mobileBtn.disabled !== desktopBtn.disabled) {
                        mobileBtn.disabled = desktopBtn.disabled;
                    }
                });
            }
        });

        // Sync form inputs
        const inputMappings = [
            { mobile: '#actionInput', desktop: '.action-input' }
        ];

        inputMappings.forEach(({ mobile, desktop }) => {
            const mobileInput = document.querySelector(mobile);
            const desktopInput = document.querySelector(desktop);
            
            if (mobileInput && desktopInput) {
                this.addEventListener(mobileInput, 'input', this.debounce(() => {
                    desktopInput.value = mobileInput.value;
                }, 100));
                
                this.addEventListener(desktopInput, 'input', this.debounce(() => {
                    mobileInput.value = desktopInput.value;
                }, 100));
            }
        });

        // Sync form submissions
        const chatForm = document.querySelector('#chatForm');
        const desktopForm = document.querySelector('.chat-form');
        
        if (chatForm && desktopForm) {
            this.addEventListener(chatForm, 'submit', () => {
                const event = new Event('submit', { bubbles: true, cancelable: true });
                desktopForm.dispatchEvent(event);
            });
        }
    }

    switchTab(tabName) {
        if (this.isDesktop) return; // Don't switch tabs on desktop
        
        // Update button states
        document.querySelectorAll('.mobile-tab-btn').forEach(btn => {
            btn.classList.remove('active');
            if (btn.dataset.tab === tabName) {
                btn.classList.add('active');
            }
        });

        // Update tab content
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });
        
        const activeTab = document.querySelector(`#${tabName}-tab`);
        if (activeTab) {
            activeTab.classList.add('active');
        }

        this.currentTab = tabName;

        // Announce tab change for screen readers
        this.announceTabChange(tabName);
    }

    announceTabChange(tabName) {
        const announcement = document.createElement('div');
        announcement.setAttribute('aria-live', 'polite');
        announcement.setAttribute('aria-atomic', 'true');
        announcement.style.position = 'absolute';
        announcement.style.left = '-10000px';
        announcement.style.width = '1px';
        announcement.style.height = '1px';
        announcement.style.overflow = 'hidden';
        
        const tabLabels = {
            adventure: 'Adventure tab selected',
            party: 'Party tab selected',
            inventory: 'Inventory tab selected',
            quests: 'Quests tab selected'
        };
        
        announcement.textContent = tabLabels[tabName] || `${tabName} tab selected`;
        document.body.appendChild(announcement);
        
        setTimeout(() => {
            document.body.removeChild(announcement);
        }, 1000);
    }

    handleResize() {
        const wasDesktop = this.isDesktop;
        this.isDesktop = window.innerWidth >= 768;
        
        if (wasDesktop !== this.isDesktop) {
            // Layout changed, ensure proper display
            if (this.isDesktop) {
                // Show desktop layout
                document.querySelectorAll('.tab-content').forEach(content => {
                    content.classList.remove('active');
                });
            } else {
                // Show mobile layout with current tab
                this.switchTab(this.currentTab);
            }
        }
    }

    // Public API methods
    getCurrentTab() {
        return this.currentTab;
    }

    setActiveTab(tabName) {
        this.switchTab(tabName);
    }

    isInMobileMode() {
        return !this.isDesktop;
    }

    // Campaign Management Methods for Mobile
    createNewCampaign(campaignData) {
        console.log('[RPGMobileController] Creating new campaign from mobile');
        
        if (this.rpgManager && typeof this.rpgManager.createNewCampaign === 'function') {
            return this.rpgManager.createNewCampaign(campaignData);
        } else {
            this.showToast('RPG Manager not available', 'error');
            return Promise.reject('RPG Manager not available');
        }
    }

    loadExistingCampaign(campaignId) {
        console.log(`[RPGMobileController] Loading campaign from mobile: ${campaignId}`);
        
        if (this.rpgManager && typeof this.rpgManager.loadCampaign === 'function') {
            return this.rpgManager.loadCampaign(campaignId);
        } else {
            this.showToast('RPG Manager not available', 'error');
            return Promise.reject('RPG Manager not available');
        }
    }

    handlePlayerAction(action) {
        console.log(`[RPGMobileController] Handling player action from mobile: ${action}`);
        
        if (!action || !action.trim()) {
            this.showToast('Please enter an action', 'warning');
            return;
        }

        if (this.rpgManager && typeof this.rpgManager.handlePlayerAction === 'function') {
            // Create a mock event object for compatibility
            const mockEvent = {
                preventDefault: () => {},
                target: {
                    value: action
                }
            };
            
            return this.rpgManager.handlePlayerAction(mockEvent);
        } else {
            this.showToast('RPG Manager not available', 'error');
        }
    }

    // Mobile-specific UI updates
    updateMobileUI(gameState) {
        console.log('[RPGMobileController] Updating mobile UI');
        
        try {
            // Update campaign info
            if (gameState?.campaign_name) {
                const campaignNameEl = document.getElementById('campaignName');
                if (campaignNameEl) {
                    campaignNameEl.textContent = gameState.campaign_name;
                }
            }

            // Update character info
            if (gameState?.character_name) {
                const characterNameEl = document.getElementById('characterName');
                if (characterNameEl) {
                    characterNameEl.textContent = gameState.character_name;
                }
            }

            // Update health display
            if (gameState?.character_health !== undefined) {
                this.updateHealthDisplay(gameState.character_health, gameState.character_max_health);
            }

            // Update inventory count
            if (gameState?.inventory) {
                this.updateInventoryCount(gameState.inventory.length);
            }

            // Update quest count
            if (gameState?.active_quests) {
                this.updateQuestCount(gameState.active_quests.length);
            }

            // Show appropriate tab content based on game state
            if (gameState?.is_active) {
                this.enableGameControls();
            } else {
                this.disableGameControls();
            }

        } catch (error) {
            console.error('[RPGMobileController] Error updating mobile UI:', error);
            this.showToast('Error updating mobile interface', 'error');
        }
    }

    updateHealthDisplay(current, max) {
        const healthBar = document.getElementById('healthBar');
        const healthText = document.getElementById('healthText');
        
        if (healthBar && healthText) {
            const percentage = max ? (current / max) * 100 : 0;
            healthBar.style.width = `${percentage}%`;
            healthText.textContent = `${current}/${max}`;
            
            // Update color based on health percentage
            if (percentage > 75) {
                healthBar.className = 'health-bar health-good';
            } else if (percentage > 25) {
                healthBar.className = 'health-bar health-warning';
            } else {
                healthBar.className = 'health-bar health-danger';
            }
        }
    }

    updateInventoryCount(count) {
        const inventoryCount = document.getElementById('inventoryCount');
        if (inventoryCount) {
            inventoryCount.textContent = count || 0;
        }
        
        // Update tab badge
        const inventoryTab = document.querySelector('[data-tab="inventory"]');
        if (inventoryTab) {
            let badge = inventoryTab.querySelector('.tab-badge');
            if (!badge) {
                badge = document.createElement('span');
                badge.className = 'tab-badge';
                inventoryTab.appendChild(badge);
            }
            badge.textContent = count || 0;
            badge.style.display = count > 0 ? 'inline' : 'none';
        }
    }

    updateQuestCount(count) {
        const questCount = document.getElementById('questCount');
        if (questCount) {
            questCount.textContent = count || 0;
        }
        
        // Update tab badge
        const questsTab = document.querySelector('[data-tab="quests"]');
        if (questsTab) {
            let badge = questsTab.querySelector('.tab-badge');
            if (!badge) {
                badge = document.createElement('span');
                badge.className = 'tab-badge';
                questsTab.appendChild(badge);
            }
            badge.textContent = count || 0;
            badge.style.display = count > 0 ? 'inline' : 'none';
        }
    }

    enableGameControls() {
        console.log('[RPGMobileController] Enabling game controls');
        
        const gameControls = document.querySelectorAll('.game-control');
        gameControls.forEach(control => {
            control.disabled = false;
            control.classList.remove('disabled');
        });
        
        // Show active game indicators
        const gameIndicators = document.querySelectorAll('.game-active-indicator');
        gameIndicators.forEach(indicator => {
            indicator.style.display = 'block';
        });
    }

    disableGameControls() {
        console.log('[RPGMobileController] Disabling game controls');
        
        const gameControls = document.querySelectorAll('.game-control');
        gameControls.forEach(control => {
            control.disabled = true;
            control.classList.add('disabled');
        });
        
        // Hide active game indicators
        const gameIndicators = document.querySelectorAll('.game-active-indicator');
        gameIndicators.forEach(indicator => {
            indicator.style.display = 'none';
        });
    }

    // Sync method to ensure mobile and desktop are in sync
    syncWithDesktop() {
        console.log('[RPGMobileController] Syncing mobile interface with desktop');
        
        if (this.rpgManager) {
            // Sync game state
            if (this.rpgManager.gameState) {
                this.updateMobileUI(this.rpgManager.gameState);
            }
            
            // Sync active state
            if (this.rpgManager.isGameActive) {
                this.enableGameControls();
            } else {
                this.disableGameControls();
            }
        }
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new RPGMobileController();
});
