/**
 * RPG Manager JavaScript
 * Handles the RPG interface, game state, and DM interactions
 * Enhanced with comprehensive error handling, logging, and full functionality
 * 
 * Features:
 * - Campaign management (create, load, save)
 * - Real-time chat and player actions
 * - Dice rolling system with quick dice
 * - Character and NPC management
 * - Inventory and quest tracking
 * - Multiplayer support with WebSocket
 * - Mobile/desktop synchronization
 * - Memory leak prevention
 */

class RPGManager {
    constructor() {
        console.log('[RPGManager] Initializing RPG Manager...');
        
        this.gameState = null;
        this.isGameActive = false;
        this.currentQuickInputType = null;
        this.eventListeners = []; // Track event listeners for cleanup
        
        // Multiplayer support
        this.isMultiplayer = false;
        this.sessionId = null;
        this.playerId = null;
        this.players = [];
        this.websocket = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        
        // Cleanup functions for event listeners
        this.cleanupFunctions = [];
        
        // UI state tracking
        this.isInitialized = false;
        this.currentModal = null;
        
        this.init();
    }
    
    // Destroy method to prevent memory leaks
    destroy() {
        console.log('[RPGManager] Cleaning up event listeners...');
        
        // Remove all event listeners
        this.cleanupFunctions.forEach(cleanup => {
            try {
                cleanup();
            } catch (error) {
                console.error('[RPGManager] Error during cleanup:', error);
            }
        });
        this.cleanupFunctions = [];
        
        // Close any open modals
        if (this.currentModal) {
            this.closeModal(this.currentModal);
        }
        
        // Reset state
        this.isInitialized = false;
        console.log('[RPGManager] Cleanup completed');
    }

    init() {
        try {
            console.log('[RPGManager] Starting initialization...');
            
            this.bindEvents();
            this.loadExistingCampaign();
            this.initMultiplayerSupport();
            
            // Cleanup on page unload
            this.addEventListener(window, 'beforeunload', () => {
                this.cleanup();
            });
            
            this.isInitialized = true;
            console.log('[RPGManager] Initialization completed successfully');
            this.showToast('RPG Manager initialized successfully', 'success');
            
        } catch (error) {
            console.error('[RPGManager] Initialization failed:', error);
            this.showToast('RPG Manager initialization failed: ' + error.message, 'error');
        }
    }
    
    cleanup() {
        // Remove all tracked event listeners
        this.eventListeners.forEach(({element, event, handler}) => {
            if (element && element.removeEventListener) {
                element.removeEventListener(event, handler);
            }
        });
        this.eventListeners = [];
        
        // Cleanup functions for event listeners
        this.cleanupFunctions.forEach(cleanup => {
            try {
                cleanup();
            } catch (error) {
                console.error('Error during cleanup:', error);
            }
        });
        this.cleanupFunctions = [];
        
        // Multiplayer cleanup
        this.disconnectWebSocket();
        if (this.isMultiplayer) {
            this.leaveMultiplayerSession();
        }
    }
    
    addEventListener(element, event, handler) {
        if (element && typeof element.addEventListener === 'function') {
            element.addEventListener(event, handler);
            this.eventListeners.push({element, event, handler});
            this.cleanupFunctions.push(() => {
                element.removeEventListener(event, handler);
            });
        }
    }
    
    // Notification system - Updated to use global notification manager
    showToast(message, type = 'info') {
        console.log(`[RPGManager] ${type.toUpperCase()}: ${message}`);
        
        // Use the global notification manager
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
        } else {
            // Fallback to console and alert for critical errors
            if (type === 'error') {
                alert(`RPG Manager Error: ${message}`);
            } else if (type === 'success') {
                console.info(`RPG Manager Success: ${message}`);
            } else {
                console.info(`RPG Manager Info: ${message}`);
            }
        }
    }

    /**
     * Helper method to bind events to multiple element selectors
     */
    bindToAllElements(selectors, callback, eventType = 'click') {
        selectors.forEach(selector => {
            const elements = selector.startsWith('#') 
                ? [document.getElementById(selector.slice(1))]
                : document.querySelectorAll(selector);
            
            if (elements[0]) {
                elements.forEach(element => {
                    if (element) {
                        this.addEventListener(element, eventType, callback);
                    }
                });
            }
        });
    }

    bindEvents() {
        console.log('[RPGManager] Binding events...');
        
        try {
            // Campaign controls - bind to both mobile and desktop elements
            this.bindToAllElements(['#newCampaignBtn', '.new-campaign-btn'], () => {
                console.log('[RPGManager] New campaign button clicked');
                this.showNewCampaignModal();
            });
            this.bindToAllElements(['#loadCampaignBtn', '.load-campaign-btn'], () => {
                console.log('[RPGManager] Load campaign button clicked');
                this.loadCampaign();
            });
            this.bindToAllElements(['#saveCampaignBtn', '.save-campaign-btn'], () => {
                console.log('[RPGManager] Save campaign button clicked');
                this.saveCampaign();
            });

            // Chat form - handle both mobile and desktop
            this.bindToAllElements(['#chatForm', '.chat-form'], (e) => {
                console.log('[RPGManager] Chat form submitted');
                this.handlePlayerAction(e);
            }, 'submit');

            // Quick actions
            document.querySelectorAll('.quick-action-btn').forEach(btn => {
                this.addEventListener(btn, 'click', (e) => {
                    console.log('[RPGManager] Quick action clicked:', btn.textContent?.trim());
                    this.handleQuickAction(e);
                });
            });

            // Dice rolling
            this.bindToAllElements(['#rollDiceBtn', '.roll-dice-btn'], () => {
                console.log('[RPGManager] Roll dice button clicked');
                this.showDiceRollModal();
            });
            
            // Character and item management
            this.bindToAllElements(['#addCharacterBtn', '.add-character-btn'], () => {
                console.log('[RPGManager] Add character button clicked');
                this.showAddCharacterModal();
            });
            this.bindToAllElements(['#addItemBtn', '.add-item-btn'], () => {
                console.log('[RPGManager] Add item button clicked');
                this.showQuickInputModal('item');
            });
            this.bindToAllElements(['#addQuestBtn', '.add-quest-btn'], () => {
                console.log('[RPGManager] Add quest button clicked');
                this.showQuickInputModal('quest');
            });

            // Form submissions (these are unique)
            const diceForm = document.getElementById('diceRollForm');
            if (diceForm) this.addEventListener(diceForm, 'submit', (e) => this.rollDice(e));
            
            // Quick dice buttons
            document.querySelectorAll('.dice-btn').forEach(btn => {
                this.addEventListener(btn, 'click', (e) => this.selectQuickDice(e));
            });

            const newCampaignForm = document.getElementById('newCampaignForm');
            if (newCampaignForm) this.addEventListener(newCampaignForm, 'submit', (e) => this.createNewCampaign(e));
            
            const addCharacterForm = document.getElementById('addCharacterForm');
            if (addCharacterForm) this.addEventListener(addCharacterForm, 'submit', (e) => this.addCharacter(e));
            
            const quickInputForm = document.getElementById('quickInputForm');
            if (quickInputForm) this.addEventListener(quickInputForm, 'submit', (e) => this.handleQuickInput(e));

            // Modal close events
            document.querySelectorAll('.close').forEach(closeBtn => {
                this.addEventListener(closeBtn, 'click', (e) => {
                    const modal = e.target.closest('.modal');
                    if (modal) {
                        console.log('[RPGManager] Closing modal:', modal.id);
                        this.closeModal(modal.id);
                    }
                });
            });

            // Close modal when clicking outside
            this.addEventListener(window, 'click', (e) => {
                if (e.target.classList.contains('modal')) {
                    console.log('[RPGManager] Clicked outside modal, closing:', e.target.id);
                    this.closeModal(e.target.id);
                }
            });
            
            console.log('[RPGManager] Events bound successfully');
            
        } catch (error) {
            console.error('[RPGManager] Error binding events:', error);
        }
    }

    async loadExistingCampaign() {
        console.log('[RPGManager] Loading existing campaign...');
        
        try {
            const response = await fetch('/api/rpg/campaign/current');
            if (response.ok) {
                const data = await response.json();
                if (data.campaign) {
                    this.gameState = data.campaign;
                    this.isGameActive = true;
                    this.updateUI();
                    this.enableGameControls();
                    
                    console.log('[RPGManager] Existing campaign loaded:', data.campaign.name);
                    this.showToast(`Campaign "${data.campaign.name}" loaded successfully`, 'success');
                } else {
                    console.log('[RPGManager] No existing campaign found');
                    this.showToast('No existing campaign found. Create a new campaign to get started!', 'info');
                }
            } else {
                console.log('[RPGManager] No campaign response or error:', response.status);
            }
        } catch (error) {
            console.log('[RPGManager] No existing campaign found or error loading:', error);
            // Don't show error toast for this as it's normal to not have a campaign
        }
    }

    showNewCampaignModal() {
        this.showModal('newCampaignModal');
    }

    async createNewCampaign(e) {
        e.preventDefault();
        
        const formData = new FormData(e.target);
        const campaignData = {
            name: formData.get('newCampaignName') || document.getElementById('newCampaignName').value,
            world_description: formData.get('newWorldDescription') || document.getElementById('newWorldDescription').value,
            character_name: formData.get('newCharacterName') || document.getElementById('newCharacterName').value,
            character_backstory: formData.get('newCharacterBackstory') || document.getElementById('newCharacterBackstory').value || 'A brave adventurer.'
        };

        try {
            const response = await fetch('/api/rpg/campaign/new', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(campaignData)
            });

            if (response.ok) {
                const result = await response.json();
                this.gameState = result.campaign;
                this.isGameActive = true;
                this.closeModal('newCampaignModal');
                this.updateUI();
                this.enableGameControls();
                this.addChatMessage('system', `Campaign "${campaignData.name}" created! The adventure begins...`);
                
                // Generate initial scene
                this.sendActionToDM("The adventure begins. Set the scene and introduce the world.");
            } else {
                const error = await response.json();
                this.showMessage('Error', error.error || 'Failed to create campaign');
            }
        } catch (error) {
            console.error('Error creating campaign:', error);
            this.showMessage('Error', 'Network error. Please try again.');
        }
    }

    async loadCampaign() {
        try {
            const response = await fetch('/api/rpg/campaign/current');
            if (response.ok) {
                const data = await response.json();
                if (data.campaign) {
                    this.gameState = data.campaign;
                    this.isGameActive = true;
                    this.updateUI();
                    this.enableGameControls();
                    this.addChatMessage('system', `Campaign "${this.gameState.campaign_name}" loaded successfully!`);
                } else {
                    this.showMessage('Info', 'No saved campaign found. Create a new campaign to begin.');
                }
            } else {
                this.showMessage('Error', 'Failed to load campaign');
            }
        } catch (error) {
            console.error('Error loading campaign:', error);
            this.showMessage('Error', 'Network error. Please try again.');
        }
    }

    async saveCampaign() {
        if (!this.isGameActive) {
            this.showMessage('Info', 'No active campaign to save');
            return;
        }

        try {
            const response = await fetch('/api/rpg/campaign/save', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });

            if (response.ok) {
                this.showMessage('Success', 'Campaign saved successfully!');
            } else {
                this.showMessage('Error', 'Failed to save campaign');
            }
        } catch (error) {
            console.error('Error saving campaign:', error);
            this.showMessage('Error', 'Network error. Please try again.');
        }
    }

    enableGameControls() {
        document.getElementById('actionInput').disabled = false;
        document.getElementById('sendActionBtn').disabled = false;
        document.getElementById('saveCampaignBtn').style.display = 'inline-flex';
        
        document.querySelectorAll('.quick-action-btn').forEach(btn => {
            btn.disabled = false;
        });
    }

    handlePlayerAction(e) {
        e.preventDefault();
        
        const actionInput = document.getElementById('actionInput');
        const action = actionInput.value.trim();
        
        // Input validation
        if (!action) {
            this.showNotification('Please enter an action', 'warning');
            return;
        }
        
        if (action.length > 500) {
            this.showNotification('Action is too long. Please keep it under 500 characters.', 'warning');
            return;
        }
        
        // Basic content filtering
        if (this.containsHarmfulContent(action)) {
            this.showNotification('Action contains potentially inappropriate content. Please revise.', 'warning');
            return;
        }
        
        if (!this.isGameActive) {
            this.showNotification('No active campaign. Please start or load a campaign first.', 'warning');
            return;
        }

        // Disable input during processing
        actionInput.disabled = true;
        const sendBtn = document.getElementById('sendActionBtn');
        sendBtn.disabled = true;
        sendBtn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Acting...';

        this.sendPlayerAction(action)
            .then(() => {
                actionInput.value = '';
            })
            .catch(error => {
                console.error('Error sending action:', error);
                this.showNotification('Failed to send action. Please try again.', 'error');
            })
            .finally(() => {
                actionInput.disabled = false;
                sendBtn.disabled = false;
                sendBtn.innerHTML = '⚔️ Act';
                actionInput.focus();
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

    handleQuickAction(e) {
        const action = e.target.dataset.action;
        if (!action || !this.isGameActive) return;
        
        document.getElementById('actionInput').value = action;
        document.getElementById('chatForm').dispatchEvent(new Event('submit'));
    }

    async sendActionToDM(action) {
        if (!this.isGameActive) return;

        try {
            const response = await fetch('/api/rpg/action', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ action: action })
            });

            if (response.ok) {
                const result = await response.json();
                this.addChatMessage('dm', result.response);
                
                // Update game state if provided
                if (result.gameState) {
                    this.gameState = result.gameState;
                    this.updateUI();
                }
            } else {
                this.addChatMessage('system', '❌ Error: Could not process action');
            }
        } catch (error) {
            console.error('Error sending action:', error);
            this.addChatMessage('system', '❌ Network error. Please try again.');
        }
    }

    addChatMessage(type, message) {
        const chatContainers = ['#chatMessages', '#chatMessages-desktop'];
        
        chatContainers.forEach(selector => {
            const chatMessages = document.getElementById(selector.slice(1));
            if (!chatMessages) return;
            
            const messageDiv = document.createElement('div');
            messageDiv.className = `chat-message ${type}`;
            messageDiv.textContent = message;
            
            chatMessages.appendChild(messageDiv);
            chatMessages.scrollTop = chatMessages.scrollHeight;
        });
    }

    updateUI() {
        if (!this.gameState) return;

        // Update campaign header - both mobile and desktop
        this.updateElement('#campaignName', this.gameState.campaign_name);
        this.updateElement('#campaignName-desktop', this.gameState.campaign_name);
        this.updateElement('#campaignDescription', this.gameState.world_description);
        this.updateElement('#campaignDescription-desktop', this.gameState.world_description);
        
        // Update current scene
        this.updateElement('#currentScene', this.gameState.current_scene);
        this.updateElement('#currentScene-desktop', this.gameState.current_scene);
        
        // Update turn counter
        this.updateElement('#turnCount', this.gameState.turn_count);
        this.updateElement('#turnCount-desktop', this.gameState.turn_count);
        
        // Update party stats
        if (this.gameState.party_stats) {
            this.updateElement('#partySize', this.gameState.party_stats.size);
            this.updateElement('.party-size', this.gameState.party_stats.size);
            this.updateElement('#partyLevel', this.gameState.party_stats.average_level);
            this.updateElement('.party-level', this.gameState.party_stats.average_level);
            const healthText = `${this.gameState.party_stats.health}/${this.gameState.party_stats.max_health}`;
            this.updateElement('#partyHealth', healthText);
            this.updateElement('.party-health', healthText);
        }
        
        // Update characters list
        this.updateCharactersList();
        
        // Update NPCs list
        this.updateNPCsList();
        
        // Update inventory
        this.updateInventory();
        
        // Update quest log
        this.updateQuestLog();
        
        // Update event log
        this.updateEventLog();
    }

    /**
     * Helper method to update elements by selector
     */
    updateElement(selector, value) {
        const elements = selector.startsWith('#') 
            ? [document.getElementById(selector.slice(1))]
            : document.querySelectorAll(selector);
        
        elements.forEach(element => {
            if (element) {
                element.textContent = value;
            }
        });
    }

    updateCharactersList() {
        const containers = ['#charactersList', '.characters-list-desktop'];
        
        containers.forEach(selector => {
            const container = selector.startsWith('#') 
                ? document.getElementById(selector.slice(1))
                : document.querySelector(selector);
            
            if (!container) return;
            
            container.innerHTML = '';
            
            if (!this.gameState.characters || this.gameState.characters.length === 0) {
                container.innerHTML = '<em>No characters in party</em>';
                return;
            }
            
            this.gameState.characters.forEach(character => {
                const characterCard = document.createElement('div');
                characterCard.className = 'character-card';
                
                const healthPercent = (character.health / character.max_health) * 100;
                let healthClass = '';
                if (healthPercent <= 25) healthClass = 'critical';
                else if (healthPercent <= 50) healthClass = 'low';
                
                characterCard.innerHTML = `
                    <div class="character-header">
                        <span class="character-name">${character.name}</span>
                        <span class="character-level">Lvl ${character.level}</span>
                    </div>
                    <div class="health-bar">
                        <div class="health-fill ${healthClass}" style="width: ${healthPercent}%"></div>
                    </div>
                    <div class="health-text">${character.health}/${character.max_health} HP</div>
                `;
                
                container.appendChild(characterCard);
            });
        });
    }

    updateNPCsList() {
        const containers = ['#npcsList', '.npcs-list-desktop'];
        
        containers.forEach(selector => {
            const container = selector.startsWith('#') 
                ? document.getElementById(selector.slice(1))
                : document.querySelector(selector);
            
            if (!container) return;
            
            container.innerHTML = '';
            
            if (!this.gameState.npcs || this.gameState.npcs.length === 0) {
                container.innerHTML = '<em>No NPCs in the current scene</em>';
                return;
            }
            
            this.gameState.npcs.forEach(npc => {
                const npcDiv = document.createElement('div');
                npcDiv.className = 'npc-item';
                npcDiv.textContent = `${npc.name} (Level ${npc.level})`;
                container.appendChild(npcDiv);
            });
        });
    }

    updateInventory() {
        const containers = ['#inventoryList', '.inventory-list-desktop'];
        
        containers.forEach(selector => {
            const container = selector.startsWith('#') 
                ? document.getElementById(selector.slice(1))
                : document.querySelector(selector);
            
            if (!container) return;
            
            container.innerHTML = '';
            
            if (!this.gameState.inventory || this.gameState.inventory.length === 0) {
                container.innerHTML = '<em>No items in inventory</em>';
                return;
            }
            
            this.gameState.inventory.forEach(item => {
                const itemDiv = document.createElement('div');
                itemDiv.className = 'inventory-item';
                itemDiv.textContent = item;
                container.appendChild(itemDiv);
            });
        });
    }

    updateQuestLog() {
        const containers = ['#questLog', '.quest-log-desktop'];
        
        containers.forEach(selector => {
            const container = selector.startsWith('#') 
                ? document.getElementById(selector.slice(1))
                : document.querySelector(selector);
            
            if (!container) return;
            
            container.innerHTML = '';
            
            if (!this.gameState.quest_log || this.gameState.quest_log.length === 0) {
                container.innerHTML = '<em>No active quests</em>';
                return;
            }
            
            this.gameState.quest_log.forEach(quest => {
                const questDiv = document.createElement('div');
                questDiv.className = 'quest-item';
                questDiv.textContent = quest;
                container.appendChild(questDiv);
            });
        });
    }

    updateEventLog() {
        const containers = ['#eventLog', '.event-log-desktop'];
        
        containers.forEach(selector => {
            const container = selector.startsWith('#') 
                ? document.getElementById(selector.slice(1))
                : document.querySelector(selector);
            
            if (!container) return;
            
            container.innerHTML = '';
            
            if (!this.gameState.event_log || this.gameState.event_log.length === 0) {
                container.innerHTML = '<em>No events yet</em>';
                return;
            }
            
            // Show last 5 events
            const recentEvents = this.gameState.event_log.slice(-5);
            recentEvents.forEach(event => {
                const eventDiv = document.createElement('div');
                eventDiv.className = 'event-item';
                eventDiv.textContent = event;
                container.appendChild(eventDiv);
            });
        });
    }

    // Dice Rolling
    showDiceRollModal() {
        document.getElementById('diceResult').style.display = 'none';
        document.getElementById('diceNotation').value = '';
        this.showModal('diceRollModal');
    }

    selectQuickDice(e) {
        const diceNotation = e.target.dataset.dice;
        document.getElementById('diceNotation').value = diceNotation;
    }

    async rollDice(e) {
        e.preventDefault();
        
        const notation = document.getElementById('diceNotation').value.trim();
        if (!notation) return;
        
        try {
            const response = await fetch('/api/rpg/dice/roll', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ notation: notation })
            });

            if (response.ok) {
                const result = await response.json();
                this.displayDiceResult(result);
            } else {
                this.showMessage('Error', 'Invalid dice notation');
            }
        } catch (error) {
            console.error('Error rolling dice:', error);
            this.showMessage('Error', 'Failed to roll dice');
        }
    }

    displayDiceResult(result) {
        const resultDiv = document.getElementById('diceResult');
        
        if (result.error) {
            resultDiv.innerHTML = `<div style="color: var(--error-color);">Error: ${result.error}</div>`;
        } else {
            const rollsText = result.rolls.length > 0 ? `[${result.rolls.join(', ')}]` : '';
            const modifierText = result.modifier !== 0 ? ` ${result.modifier >= 0 ? '+' : ''}${result.modifier}` : '';
            
            resultDiv.innerHTML = `
                <div class="result-total">${result.total}</div>
                <div class="result-details">
                    ${result.notation}: ${rollsText}${modifierText}
                </div>
            `;
        }
        
        resultDiv.style.display = 'block';
        
        // Add to chat if game is active
        if (this.isGameActive) {
            this.addChatMessage('system', `🎲 Rolled ${result.notation}: ${result.total}`);
        }
    }

    // Character Management
    showAddCharacterModal() {
        document.getElementById('addCharacterForm').reset();
        this.showModal('addCharacterModal');
    }

    async addCharacter(e) {
        e.preventDefault();
        
        const formData = new FormData(e.target);
        const characterData = {
            name: formData.get('characterName') || document.getElementById('characterName').value,
            level: parseInt(formData.get('characterLevel') || document.getElementById('characterLevel').value),
            health: parseInt(formData.get('characterHealth') || document.getElementById('characterHealth').value),
            backstory: formData.get('characterBackstory') || document.getElementById('characterBackstory').value || ''
        };
        
        characterData.max_health = characterData.health; // Set max health to current health

        try {
            const response = await fetch('/api/rpg/character/add', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(characterData)
            });

            if (response.ok) {
                const result = await response.json();
                this.gameState = result.gameState;
                this.updateUI();
                this.closeModal('addCharacterModal');
                this.addChatMessage('system', `${characterData.name} joined the party!`);
            } else {
                this.showMessage('Error', 'Failed to add character');
            }
        } catch (error) {
            console.error('Error adding character:', error);
            this.showMessage('Error', 'Failed to add character');
        }
    }

    // Quick Input Modal (for items, quests, etc.)
    showQuickInputModal(type) {
        console.log(`[RPGManager] Showing quick input modal for: ${type}`);
        
        this.currentQuickInputType = type;
        const modal = document.getElementById('quickInputModal');
        const title = document.getElementById('quickInputTitle');
        const label = document.getElementById('quickInputLabel');
        const input = document.getElementById('quickInputText');
        
        if (!modal || !title || !label || !input) {
            console.warn('[RPGManager] Quick input modal elements not found');
            this.showToast('Quick input modal not available', 'warning');
            return;
        }
        
        switch (type) {
            case 'item':
                title.textContent = 'Add Item';
                label.textContent = 'Item Name';
                input.placeholder = 'Magic sword, healing potion, etc.';
                break;
            case 'quest':
                title.textContent = 'Add Quest';
                label.textContent = 'Quest Description';
                input.placeholder = 'Find the lost treasure, rescue the princess, etc.';
                break;
            default:
                title.textContent = `Add ${type}`;
                label.textContent = `${type} Description`;
                input.placeholder = `Enter ${type} details...`;
        }
        
        input.value = '';
        this.showModal('quickInputModal');
    }

    async handleQuickInput(e) {
        e.preventDefault();
        
        const text = document.getElementById('quickInputText').value.trim();
        if (!text || !this.currentQuickInputType) return;
        
        let endpoint = '';
        switch (this.currentQuickInputType) {
            case 'item':
                endpoint = '/api/rpg/inventory/add';
                break;
            case 'quest':
                endpoint = '/api/rpg/quest/add';
                break;
            default:
                return;
        }

        try {
            const response = await fetch(endpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ [this.currentQuickInputType]: text })
            });

            if (response.ok) {
                const result = await response.json();
                this.gameState = result.gameState;
                this.updateUI();
                this.closeModal('quickInputModal');
                
                const actionText = this.currentQuickInputType === 'item' ? 'added to inventory' : 'added to quest log';
                this.addChatMessage('system', `${text} ${actionText}`);
            } else {
                this.showMessage('Error', `Failed to add ${this.currentQuickInputType}`);
            }
        } catch (error) {
            console.error('Error adding item:', error);
            this.showMessage('Error', `Failed to add ${this.currentQuickInputType}`);
        }
    }

    // Modal Management
    showModal(modalId) {
        console.log(`[RPGManager] Showing modal: ${modalId}`);
        
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.style.display = 'block';
            this.currentModal = modalId;
        } else {
            console.warn(`[RPGManager] Modal not found: ${modalId}`);
            this.showToast(`Modal "${modalId}" not found`, 'warning');
        }
    }

    closeModal(modalId) {
        console.log(`[RPGManager] Closing modal: ${modalId}`);
        
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.style.display = 'none';
            if (this.currentModal === modalId) {
                this.currentModal = null;
            }
        } else {
            console.warn(`[RPGManager] Modal not found: ${modalId}`);
        }
    }

    showMessage(title, message) {
        console.log(`[RPGManager] Showing message: ${title} - ${message}`);
        
        const titleEl = document.getElementById('messageTitle');
        const textEl = document.getElementById('messageText');
        
        if (titleEl && textEl) {
            titleEl.textContent = title;
            textEl.textContent = message;
            this.showModal('messageModal');
        } else {
            console.warn('[RPGManager] Message modal elements not found');
            this.showToast(`${title}: ${message}`, 'info');
        }
    }

    // ====================
    // MULTIPLAYER METHODS
    // ====================

    initMultiplayerSupport() {
        // Add multiplayer UI elements
        this.addMultiplayerUI();
        
        // Check for existing multiplayer session
        this.checkForMultiplayerSession();
    }

    addMultiplayerUI() {
        // Add multiplayer controls to the UI
        const controlsContainer = document.querySelector('.rpg-controls') || document.querySelector('.campaign-controls');
        if (controlsContainer) {
            const multiplayerControls = document.createElement('div');
            multiplayerControls.className = 'multiplayer-controls';
            multiplayerControls.innerHTML = `
                <button id="createMultiplayerSession" class="btn btn-primary">Create Multiplayer Session</button>
                <button id="joinMultiplayerSession" class="btn btn-secondary">Join Session</button>
                <button id="leaveMultiplayerSession" class="btn btn-danger" style="display: none;">Leave Session</button>
                <div id="playerList" class="player-list" style="display: none;">
                    <h4>Players Online</h4>
                    <ul id="playersList"></ul>
                </div>
            `;
            controlsContainer.appendChild(multiplayerControls);
            
            // Bind multiplayer events
            this.bindMultiplayerEvents();
        }
    }

    bindMultiplayerEvents() {
        const createBtn = document.getElementById('createMultiplayerSession');
        const joinBtn = document.getElementById('joinMultiplayerSession');
        const leaveBtn = document.getElementById('leaveMultiplayerSession');
        
        if (createBtn) {
            this.addEventListener(createBtn, 'click', () => this.createMultiplayerSession());
        }
        if (joinBtn) {
            this.addEventListener(joinBtn, 'click', () => this.showJoinSessionModal());
        }
        if (leaveBtn) {
            this.addEventListener(leaveBtn, 'click', () => this.leaveMultiplayerSession());
        }
    }

    async createMultiplayerSession() {
        if (!this.gameState) {
            this.showMessage('Error', 'Please create or load a campaign first');
            return;
        }

        try {
            const response = await fetch('/api/rpg/multiplayer/create', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    campaign_id: this.gameState.id,
                    player_name: this.gameState.character_name || 'Player'
                })
            });

            if (response.ok) {
                const data = await response.json();
                this.sessionId = data.session_id;
                this.playerId = data.player_id;
                this.isMultiplayer = true;
                
                this.connectWebSocket();
                this.updateMultiplayerUI();
                this.addChatMessage('system', 'Multiplayer session created! Other players can join using the session code.');
            } else {
                const error = await response.json();
                this.showMessage('Error', error.error || 'Failed to create multiplayer session');
            }
        } catch (error) {
            console.error('Error creating multiplayer session:', error);
            this.showMessage('Error', 'Failed to create multiplayer session');
        }
    }

    showJoinSessionModal() {
        // Create modal for joining session
        const modal = document.createElement('div');
        modal.id = 'joinSessionModal';
        modal.className = 'modal';
        modal.innerHTML = `
            <div class="modal-content">
                <span class="close">&times;</span>
                <h2>Join Multiplayer Session</h2>
                <form id="joinSessionForm">
                    <div class="form-group">
                        <label for="sessionCode">Session Code:</label>
                        <input type="text" id="sessionCode" name="sessionCode" required>
                    </div>
                    <div class="form-group">
                        <label for="playerName">Your Name:</label>
                        <input type="text" id="playerName" name="playerName" required>
                    </div>
                    <button type="submit" class="btn btn-primary">Join Session</button>
                </form>
            </div>
        `;
        
        document.body.appendChild(modal);
        this.showModal('joinSessionModal');
        
        // Bind form submission
        document.getElementById('joinSessionForm').addEventListener('submit', (e) => this.joinMultiplayerSession(e));
    }

    async joinMultiplayerSession(e) {
        e.preventDefault();
        
        const formData = new FormData(e.target);
        const sessionCode = formData.get('sessionCode');
        const playerName = formData.get('playerName');

        try {
            const response = await fetch('/api/rpg/multiplayer/join', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    session_code: sessionCode,
                    player_name: playerName
                })
            });

            if (response.ok) {
                const data = await response.json();
                this.sessionId = data.session_id;
                this.playerId = data.player_id;
                this.gameState = data.campaign;
                this.isMultiplayer = true;
                this.isGameActive = true;
                
                this.connectWebSocket();
                this.updateMultiplayerUI();
                this.updateUI();
                this.enableGameControls();
                this.closeModal('joinSessionModal');
                this.addChatMessage('system', `Joined multiplayer session as ${playerName}!`);
            } else {
                const error = await response.json();
                this.showMessage('Error', error.error || 'Failed to join session');
            }
        } catch (error) {
            console.error('Error joining multiplayer session:', error);
            this.showMessage('Error', 'Failed to join session');
        }
    }

    async leaveMultiplayerSession() {
        if (!this.isMultiplayer) return;

        try {
            await fetch('/api/rpg/multiplayer/leave', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    session_id: this.sessionId,
                    player_id: this.playerId
                })
            });

            this.disconnectWebSocket();
            this.isMultiplayer = false;
            this.sessionId = null;
            this.playerId = null;
            this.players = [];
            
            this.updateMultiplayerUI();
            this.addChatMessage('system', 'Left multiplayer session');
        } catch (error) {
            console.error('Error leaving multiplayer session:', error);
        }
    }

    connectWebSocket() {
        if (!this.sessionId) return;

        const wsUrl = `ws://${window.location.host}/ws/rpg/multiplayer/${this.sessionId}`;
        this.websocket = new WebSocket(wsUrl);

        this.websocket.onopen = () => {
            console.log('WebSocket connected for multiplayer');
            this.reconnectAttempts = 0;
            
            // Send player info
            this.websocket.send(JSON.stringify({
                type: 'player_join',
                player_id: this.playerId,
                player_name: this.gameState.character_name || 'Player'
            }));
        };

        this.websocket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleWebSocketMessage(data);
        };

        this.websocket.onclose = () => {
            console.log('WebSocket disconnected');
            if (this.isMultiplayer && this.reconnectAttempts < this.maxReconnectAttempts) {
                this.reconnectAttempts++;
                setTimeout(() => this.connectWebSocket(), 2000 * this.reconnectAttempts);
            }
        };

        this.websocket.onerror = (error) => {
            console.error('WebSocket error:', error);
        };
    }

    disconnectWebSocket() {
        if (this.websocket) {
            this.websocket.close();
            this.websocket = null;
        }
    }

    handleWebSocketMessage(data) {
        switch (data.type) {
            case 'player_joined':
                this.players = data.players;
                this.updatePlayerList();
                this.addChatMessage('system', `${data.player_name} joined the session`);
                break;
                
            case 'player_left':
                this.players = data.players;
                this.updatePlayerList();
                this.addChatMessage('system', `${data.player_name} left the session`);
                break;
                
            case 'player_action':
                this.addChatMessage('player', `${data.player_name}: ${data.action}`);
                break;
                
            case 'dm_response':
                this.addChatMessage('dm', data.response);
                this.updateGameState(data.game_state);
                break;
                
            case 'game_state_update':
                this.updateGameState(data.game_state);
                break;
                
            case 'dice_roll':
                this.addChatMessage('system', `${data.player_name} rolled ${data.result} (${data.dice})`);
                break;
        }
    }

    updatePlayerList() {
        const playersList = document.getElementById('playersList');
        if (playersList) {
            playersList.innerHTML = '';
            this.players.forEach(player => {
                const li = document.createElement('li');
                li.textContent = player.name;
                if (player.is_dm) li.textContent += ' (DM)';
                playersList.appendChild(li);
            });
        }
    }

    // Player Management Methods
    addPlayer(playerData) {
        console.log('[RPGManager] Adding player:', playerData);
        
        if (!this.currentCampaign) {
            this.showToast('No active campaign', 'warning');
            return;
        }

        if (!this.currentCampaign.players) {
            this.currentCampaign.players = [];
        }

        const playerId = 'player_' + Date.now();
        const newPlayer = {
            id: playerId,
            name: playerData.name || 'Unnamed Player',
            class: playerData.class || 'Adventurer',
            level: playerData.level || 1,
            health: playerData.health || 100,
            maxHealth: playerData.maxHealth || 100,
            ...playerData
        };

        this.currentCampaign.players.push(newPlayer);
        this.updatePlayersView();
        this.showToast(`Player "${newPlayer.name}" added`, 'success');
    }

    editPlayer(playerId) {
        console.log(`[RPGManager] Editing player: ${playerId}`);
        
        if (!this.currentCampaign?.players) {
            this.showToast('No players available', 'warning');
            return;
        }

        const player = this.currentCampaign.players.find(p => p.id === playerId);
        if (!player) {
            this.showToast('Player not found', 'error');
            return;
        }

        // Pre-fill edit form
        const nameInput = document.getElementById('editPlayerName');
        const classInput = document.getElementById('editPlayerClass');
        const levelInput = document.getElementById('editPlayerLevel');
        
        if (nameInput) nameInput.value = player.name;
        if (classInput) classInput.value = player.class || '';
        if (levelInput) levelInput.value = player.level || 1;

        // Store player ID for editing
        this.editingPlayerId = playerId;
        this.showModal('editPlayerModal');
    }

    updatePlayer(updatedData) {
        console.log('[RPGManager] Updating player:', this.editingPlayerId, updatedData);
        
        if (!this.editingPlayerId || !this.currentCampaign?.players) {
            this.showToast('No player selected for editing', 'warning');
            return;
        }

        const playerIndex = this.currentCampaign.players.findIndex(p => p.id === this.editingPlayerId);
        if (playerIndex === -1) {
            this.showToast('Player not found', 'error');
            return;
        }

        // Update player data
        this.currentCampaign.players[playerIndex] = {
            ...this.currentCampaign.players[playerIndex],
            ...updatedData
        };

        this.updatePlayersView();
        this.closeModal('editPlayerModal');
        this.editingPlayerId = null;
        this.showToast(`Player "${updatedData.name}" updated`, 'success');
    }

    removePlayer(playerId) {
        console.log(`[RPGManager] Removing player: ${playerId}`);
        
        if (!this.currentCampaign?.players) {
            this.showToast('No players available', 'warning');
            return;
        }

        const player = this.currentCampaign.players.find(p => p.id === playerId);
        if (!player) {
            this.showToast('Player not found', 'error');
            return;
        }

        if (confirm(`Are you sure you want to remove "${player.name}" from the campaign?`)) {
            this.currentCampaign.players = this.currentCampaign.players.filter(p => p.id !== playerId);
            this.updatePlayersView();
            this.showToast(`Player "${player.name}" removed`, 'success');
        }
    }

    updateMultiplayerUI() {
        const createBtn = document.getElementById('createMultiplayerSession');
        const joinBtn = document.getElementById('joinMultiplayerSession');
        const leaveBtn = document.getElementById('leaveMultiplayerSession');
        const playerList = document.getElementById('playerList');

        if (this.isMultiplayer) {
            if (createBtn) createBtn.style.display = 'none';
            if (joinBtn) joinBtn.style.display = 'none';
            if (leaveBtn) leaveBtn.style.display = 'inline-block';
            if (playerList) playerList.style.display = 'block';
        } else {
            if (createBtn) createBtn.style.display = 'inline-block';
            if (joinBtn) joinBtn.style.display = 'inline-block';
            if (leaveBtn) leaveBtn.style.display = 'none';
            if (playerList) playerList.style.display = 'none';
        }
    }

    checkForMultiplayerSession() {
        // Check if there's an active multiplayer session in localStorage
        const sessionData = localStorage.getItem('rpg_multiplayer_session');
        if (sessionData) {
            try {
                const data = JSON.parse(sessionData);
                this.sessionId = data.session_id;
                this.playerId = data.player_id;
                this.isMultiplayer = true;
                
                // Attempt to reconnect
                this.connectWebSocket();
                this.updateMultiplayerUI();
            } catch (error) {
                console.error('Error parsing stored session data:', error);
                localStorage.removeItem('rpg_multiplayer_session');
            }
        }
    }

    // Override existing methods for multiplayer support
    async sendPlayerAction(action) {
        if (this.isMultiplayer && this.websocket) {
            // Send action through WebSocket for multiplayer
            this.websocket.send(JSON.stringify({
                type: 'player_action',
                player_id: this.playerId,
                action: action
            }));
            this.addChatMessage('user', action);
        } else {
            // Use existing single-player logic
            try {
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), 30000);
                
                const response = await fetch('/api/rpg/action', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        action: action,
                        campaign_id: this.gameState?.id
                    }),
                    signal: controller.signal
                });
                clearTimeout(timeoutId);
                
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                
                const data = await response.json();
                
                if (data.success) {
                    this.addChatMessage('user', action);
                    this.addChatMessage('dm', data.response);
                    this.updateGameState(data.game_state);
                } else {
                    throw new Error(data.error || 'Failed to process action');
                }
            } catch (error) {
                if (error.name === 'AbortError') {
                    throw new Error('Action request timed out. Please try again.');
                } else {
                    throw error;
                }
            }
        }
    }
}

// Initialize the RPG Manager when the page loads
let rpgManager;
document.addEventListener('DOMContentLoaded', () => {
    rpgManager = new RPGManager();
});

// Global function for modal closing (called from HTML)
window.closeModal = function closeModal(modalId) {
    if (rpgManager) {
        rpgManager.closeModal(modalId);
    }
};
