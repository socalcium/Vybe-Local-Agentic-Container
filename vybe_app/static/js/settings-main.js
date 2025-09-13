/**
 * Settings Page Main Controller
 * Coordinates all settings page functionality using modular components
 */

import { ApiUtils } from './utils/api-utils.js';
import { ThemeManager } from './modules/theme-manager.js';
import { SystemPromptsManager } from './modules/system-prompts-manager.js';
import { ToolsManager } from './modules/tools-manager.js';
import { WorkspaceManager } from './modules/workspace-manager.js';
import { UserProfileManager } from './modules/user-profile-manager.js';
import { AppConfigManager } from './modules/app-config-manager.js';
import { ConnectorsManager } from './modules/connectors-manager.js';

class SettingsPageController {
    constructor() {
        this.managers = {};
        
        // Cleanup functions for event listeners
        this.cleanupFunctions = [];
        this.eventListeners = []; // Track event listeners for cleanup
        
        console.log('[SettingsPageController] Initializing settings page controller');
        this.init();
    }
    
    // Destroy method to prevent memory leaks
    destroy() {
        console.log('[SettingsPageController] Cleaning up settings page controller');
        
        // Remove all event listeners
        this.cleanupFunctions.forEach(cleanup => {
            try {
                cleanup();
            } catch (error) {
                console.error('[SettingsPageController] Error during cleanup:', error);
            }
        });
        this.cleanupFunctions = [];
        
        // Cleanup all managers
        Object.values(this.managers).forEach(manager => {
            if (manager && typeof manager.destroy === 'function') {
                manager.destroy();
            }
        });
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

    // Toast notification method - Updated to use global notification manager
    showToast(message, type = 'info') {
        console.log(`[SettingsPageController] Toast: ${message} (${type})`);
        
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
        
        // Fallback toast implementation
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
        console.log('[SettingsPageController] Setting up settings page');
        
        try {
            // Initialize all managers with fallback
            this.initializeManagers();

            // Setup global event listeners
            this.setupGlobalEventListeners();
            
            // Setup settings-specific event listeners
            this.setupSettingsEventListeners();
            
            // Load initial data
            this.loadInitialData();
            
            // Cleanup on page unload
            this.addEventListener(window, 'beforeunload', () => {
                this.destroy();
            });
            
            this.showToast('Settings page initialized successfully', 'success');
            console.log('[SettingsPageController] Settings page initialized with modular components');
            
        } catch (error) {
            console.error('[SettingsPageController] Error during initialization:', error);
            this.showToast('Settings page initialization failed', 'error');
        }
    }

    initializeManagers() {
        console.log('[SettingsPageController] Initializing managers');
        
        try {
            // Initialize managers with error handling
            const managerConfigs = [
                { name: 'theme', class: ThemeManager },
                { name: 'systemPrompts', class: SystemPromptsManager },
                { name: 'tools', class: ToolsManager },
                { name: 'workspace', class: WorkspaceManager },
                { name: 'userProfile', class: UserProfileManager },
                { name: 'appConfig', class: AppConfigManager },
                { name: 'connectors', class: ConnectorsManager }
            ];

            managerConfigs.forEach(config => {
                try {
                    if (config.class) {
                        this.managers[config.name] = new config.class();
                        console.log(`[SettingsPageController] ${config.name} manager initialized`);
                    } else {
                        console.error(`[SettingsPageController] ${config.name} manager class not available - manager will not be loaded`);
                    }
                } catch (error) {
                    console.error(`[SettingsPageController] Error initializing ${config.name} manager:`, error);
                    // Do not create mock manager - let it fail properly
                }
            });
            
        } catch (error) {
            console.error('[SettingsPageController] Error initializing managers:', error);
        }
    }



    setupSettingsEventListeners() {
        console.log('[SettingsPageController] Setting up settings-specific event listeners');
        
        // Settings navigation tabs
        const settingsTabs = document.querySelectorAll('.settings-tab');
        settingsTabs.forEach(tab => {
            this.addEventListener(tab, 'click', (e) => {
                e.preventDefault();
                const tabId = tab.dataset.tab;
                this.switchSettingsTab(tabId);
                this.showToast(`Switched to ${tabId} settings`, 'info');
            });
        });

        // Settings save buttons
        const saveButtons = document.querySelectorAll('.settings-save-btn');
        saveButtons.forEach(btn => {
            this.addEventListener(btn, 'click', (e) => {
                e.preventDefault();
                const settingsType = btn.dataset.settings || 'general';
                this.saveSettings(settingsType);
            });
        });

        // Settings reset buttons
        const resetButtons = document.querySelectorAll('.settings-reset-btn');
        resetButtons.forEach(btn => {
            this.addEventListener(btn, 'click', (e) => {
                e.preventDefault();
                const settingsType = btn.dataset.settings || 'general';
                if (confirm(`Reset ${settingsType} settings to defaults?`)) {
                    this.resetSettings(settingsType);
                }
            });
        });

        // Settings export/import
        const exportBtn = document.getElementById('export-settings');
        if (exportBtn) {
            this.addEventListener(exportBtn, 'click', () => this.exportSettings());
        }

        const importBtn = document.getElementById('import-settings');
        if (importBtn) {
            this.addEventListener(importBtn, 'click', () => this.importSettings());
        }
    }

    loadInitialData() {
        console.log('[SettingsPageController] Loading initial settings data');
        
        try {
            // Load settings from each manager
            Object.keys(this.managers).forEach(managerName => {
                const manager = this.managers[managerName];
                if (manager && typeof manager.refresh === 'function') {
                    manager.refresh();
                }
            });
            
            // Load application settings
            this.loadApplicationSettings();
            
            // Load user preferences
            this.loadUserPreferences();
            
        } catch (error) {
            console.error('[SettingsPageController] Error loading initial data:', error);
            this.showToast('Error loading settings data', 'error');
        }
    }

    loadApplicationSettings() {
        console.log('[SettingsPageController] Loading application settings');
        
        try {
            // Load from localStorage or API
            const savedSettings = localStorage.getItem('applicationSettings');
            if (savedSettings) {
                const settings = JSON.parse(savedSettings);
                this.applyApplicationSettings(settings);
                console.log('[SettingsPageController] Application settings loaded from localStorage');
            } else {
                // Load defaults
                this.applyApplicationSettings(this.getDefaultApplicationSettings());
                console.log('[SettingsPageController] Applied default application settings');
            }
        } catch (error) {
            console.error('[SettingsPageController] Error loading application settings:', error);
        }
    }

    loadUserPreferences() {
        console.log('[SettingsPageController] Loading user preferences');
        
        try {
            // Load from localStorage or API
            const savedPrefs = localStorage.getItem('userPreferences');
            if (savedPrefs) {
                const prefs = JSON.parse(savedPrefs);
                this.applyUserPreferences(prefs);
                console.log('[SettingsPageController] User preferences loaded from localStorage');
            } else {
                // Load defaults
                this.applyUserPreferences(this.getDefaultUserPreferences());
                console.log('[SettingsPageController] Applied default user preferences');
            }
        } catch (error) {
            console.error('[SettingsPageController] Error loading user preferences:', error);
        }
    }

    setupGlobalEventListeners() {
        console.log('[SettingsPageController] Setting up global event listeners');
        
        // Modal close functionality
        this.addEventListener(document, 'click', (e) => {
            // Close modal when clicking outside
            if (e.target.classList.contains('modal')) {
                e.target.style.display = 'none';
                console.log('[SettingsPageController] Modal closed by outside click');
            }

            // Close modal when clicking close button
            if (e.target.classList.contains('close-modal') || 
                e.target.classList.contains('modal-close')) {
                const modal = e.target.closest('.modal');
                if (modal) {
                    modal.style.display = 'none';
                    console.log('[SettingsPageController] Modal closed by close button');
                }
            }
        });

        // Escape key to close modals
        this.addEventListener(document, 'keydown', (e) => {
            if (e.key === 'Escape') {
                const modal = document.querySelector('.modal[style*="block"]');
                if (modal) {
                    modal.style.display = 'none';
                    console.log('[SettingsPageController] Modal closed by Escape key');
                }
            }
        });

        // Form submission prevention for settings forms
        this.addEventListener(document, 'submit', (e) => {
            if (e.target.classList.contains('settings-form')) {
                e.preventDefault();
                console.log('[SettingsPageController] Settings form submission prevented');
                this.handleFormSubmission(e.target);
            }
        });

        // Handle settings form inputs with auto-save
        this.addEventListener(document, 'input', (e) => {
            if (e.target.classList.contains('auto-save-setting')) {
                this.debounce(() => {
                    this.autoSaveSetting(e.target);
                }, 500)();
            }
        });

        // Handle settings toggles
        this.addEventListener(document, 'change', (e) => {
            if (e.target.classList.contains('settings-toggle')) {
                this.handleSettingsToggle(e.target);
            }
        });
    }

    handleFormSubmission(form) {
        console.log('[SettingsPageController] Handling form submission:', form.id);
        
        try {
            const formData = new FormData(form);
            const settingsData = Object.fromEntries(formData.entries());
            
            // Process the form based on its type
            const formType = form.dataset.settingsType || 'general';
            this.saveSettings(formType, settingsData);
            
        } catch (error) {
            console.error('[SettingsPageController] Error handling form submission:', error);
            this.showToast('Error saving settings', 'error');
        }
    }

    autoSaveSetting(input) {
        console.log(`[SettingsPageController] Auto-saving setting: ${input.name} = ${input.value}`);
        
        try {
            const settingKey = input.name;
            const settingValue = input.type === 'checkbox' ? input.checked : input.value;
            
            // Save to localStorage
            const currentSettings = JSON.parse(localStorage.getItem('autoSavedSettings') || '{}');
            currentSettings[settingKey] = settingValue;
            localStorage.setItem('autoSavedSettings', JSON.stringify(currentSettings));
            
            // Show feedback
            this.showToast(`${settingKey} saved`, 'success');
            
        } catch (error) {
            console.error('[SettingsPageController] Error auto-saving setting:', error);
            this.showToast('Error auto-saving setting', 'error');
        }
    }

    handleSettingsToggle(toggle) {
        console.log(`[SettingsPageController] Handling settings toggle: ${toggle.name} = ${toggle.checked}`);
        
        try {
            const settingName = toggle.name;
            const isEnabled = toggle.checked;
            
            // Apply the toggle immediately
            this.applySettingsToggle(settingName, isEnabled);
            
            // Save the setting
            this.autoSaveSetting(toggle);
            
            // Show appropriate feedback
            const action = isEnabled ? 'enabled' : 'disabled';
            this.showToast(`${settingName} ${action}`, 'success');
            
        } catch (error) {
            console.error('[SettingsPageController] Error handling settings toggle:', error);
            this.showToast('Error updating setting', 'error');
        }
    }

    applySettingsToggle(settingName, isEnabled) {
        console.log(`[SettingsPageController] Applying toggle: ${settingName} = ${isEnabled}`);
        
        // Apply setting-specific logic
        switch (settingName) {
            case 'darkMode':
                document.body.classList.toggle('dark-mode', isEnabled);
                break;
            case 'autoSave':
                this.autoSaveEnabled = isEnabled;
                break;
            case 'notifications':
                this.notificationsEnabled = isEnabled;
                break;
            case 'animations':
                document.body.classList.toggle('no-animations', !isEnabled);
                break;
            default:
                console.log(`[SettingsPageController] Unknown setting toggle: ${settingName}`);
        }
    }

    // Utility method for debouncing
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

    // Public API for accessing managers
    getManager(name) {
        const manager = this.managers[name];
        if (manager) {
            console.log(`[SettingsPageController] Accessing manager: ${name}`);
            return manager;
        } else {
            console.error(`[SettingsPageController] Manager not found: ${name}. This indicates a missing or failed manager initialization.`);
            return null;
        }
    }

    getAllManagers() {
        console.log('[SettingsPageController] Accessing all managers');
        return this.managers;
    }

    // Utility methods for cross-manager communication
    refreshAllData() {
        console.log('[SettingsPageController] Refreshing all manager data');
        
        try {
            Object.values(this.managers).forEach(manager => {
                if (typeof manager.refresh === 'function') {
                    manager.refresh();
                    console.log(`[SettingsPageController] Refreshed manager: ${manager.name || 'unknown'}`);
                }
            });
            
            this.showToast('All settings data refreshed', 'success');
            
        } catch (error) {
            console.error('[SettingsPageController] Error refreshing all data:', error);
            this.showToast('Error refreshing settings data', 'error');
        }
    }

    showGlobalStatus(message, type = 'info') {
        console.log(`[SettingsPageController] Global status: ${message} (${type})`);
        
        // Use ApiUtils if available, otherwise fallback to toast
        if (typeof ApiUtils !== 'undefined' && ApiUtils.showGlobalStatus) {
            ApiUtils.showGlobalStatus(message, type);
        } else {
            this.showToast(message, type);
        }
    }

    // Settings management methods
    switchSettingsTab(tabId) {
        console.log(`[SettingsPageController] Switching to settings tab: ${tabId}`);
        
        try {
            // Hide all tab content
            const tabContents = document.querySelectorAll('.settings-tab-content');
            tabContents.forEach(content => {
                content.classList.remove('active');
            });
            
            // Remove active class from all tabs
            const tabs = document.querySelectorAll('.settings-tab');
            tabs.forEach(tab => {
                tab.classList.remove('active');
            });
            
            // Show selected tab content
            const targetContent = document.getElementById(`${tabId}-content`);
            if (targetContent) {
                targetContent.classList.add('active');
            }
            
            // Activate selected tab
            const targetTab = document.querySelector(`[data-tab="${tabId}"]`);
            if (targetTab) {
                targetTab.classList.add('active');
            }
            
            // Load tab-specific data
            this.loadTabData(tabId);
            
        } catch (error) {
            console.error('[SettingsPageController] Error switching settings tab:', error);
            this.showToast('Error switching settings tab', 'error');
        }
    }

    loadTabData(tabId) {
        console.log(`[SettingsPageController] Loading data for tab: ${tabId}`);
        
        // Load data based on tab
        switch (tabId) {
            case 'general':
                this.loadGeneralSettings();
                break;
            case 'appearance':
                this.loadAppearanceSettings();
                break;
            case 'system':
                this.loadSystemSettings();
                break;
            case 'advanced':
                this.loadAdvancedSettings();
                break;
            default:
                console.log(`[SettingsPageController] Unknown tab: ${tabId}`);
        }
    }

    saveSettings(settingsType, data = null) {
        console.log(`[SettingsPageController] Saving ${settingsType} settings`);
        
        try {
            let settingsData = data;
            
            // If no data provided, collect from form
            if (!settingsData) {
                const form = document.querySelector(`[data-settings-type="${settingsType}"]`);
                if (form) {
                    const formData = new FormData(form);
                    settingsData = Object.fromEntries(formData.entries());
                } else {
                    settingsData = this.collectSettingsData(settingsType);
                }
            }
            
            // Save to localStorage
            const storageKey = `settings_${settingsType}`;
            localStorage.setItem(storageKey, JSON.stringify(settingsData));
            
            // Apply settings immediately
            this.applySettings(settingsType, settingsData);
            
            this.showToast(`${settingsType} settings saved`, 'success');
            
        } catch (error) {
            console.error(`[SettingsPageController] Error saving ${settingsType} settings:`, error);
            this.showToast(`Error saving ${settingsType} settings`, 'error');
        }
    }

    resetSettings(settingsType) {
        console.log(`[SettingsPageController] Resetting ${settingsType} settings`);
        
        try {
            // Get default settings
            const defaultSettings = this.getDefaultSettings(settingsType);
            
            // Apply default settings
            this.applySettings(settingsType, defaultSettings);
            
            // Save to storage
            const storageKey = `settings_${settingsType}`;
            localStorage.setItem(storageKey, JSON.stringify(defaultSettings));
            
            // Update UI
            this.updateSettingsUI(settingsType, defaultSettings);
            
            this.showToast(`${settingsType} settings reset to defaults`, 'success');
            
        } catch (error) {
            console.error(`[SettingsPageController] Error resetting ${settingsType} settings:`, error);
            this.showToast(`Error resetting ${settingsType} settings`, 'error');
        }
    }

    exportSettings() {
        console.log('[SettingsPageController] Exporting settings');
        
        try {
            // Collect all settings
            const allSettings = {
                general: JSON.parse(localStorage.getItem('settings_general') || '{}'),
                appearance: JSON.parse(localStorage.getItem('settings_appearance') || '{}'),
                system: JSON.parse(localStorage.getItem('settings_system') || '{}'),
                advanced: JSON.parse(localStorage.getItem('settings_advanced') || '{}'),
                autoSaved: JSON.parse(localStorage.getItem('autoSavedSettings') || '{}'),
                exportDate: new Date().toISOString()
            };
            
            // Create download link
            const dataStr = JSON.stringify(allSettings, null, 2);
            const dataBlob = new Blob([dataStr], { type: 'application/json' });
            const url = URL.createObjectURL(dataBlob);
            
            const link = document.createElement('a');
            link.href = url;
            link.download = `vybe-settings-${new Date().toISOString().split('T')[0]}.json`;
            link.click();
            
            URL.revokeObjectURL(url);
            
            this.showToast('Settings exported successfully', 'success');
            
        } catch (error) {
            console.error('[SettingsPageController] Error exporting settings:', error);
            this.showToast('Error exporting settings', 'error');
        }
    }

    importSettings() {
        console.log('[SettingsPageController] Importing settings');
        
        try {
            // Create file input
            const fileInput = document.createElement('input');
            fileInput.type = 'file';
            fileInput.accept = '.json';
            
            fileInput.onchange = (e) => {
                const file = e.target.files[0];
                if (file) {
                    const reader = new FileReader();
                    reader.onload = (e) => {
                        try {
                            const settings = JSON.parse(e.target.result);
                            this.processImportedSettings(settings);
                        } catch (error) {
                            console.error('[SettingsPageController] Error parsing imported settings:', error);
                            this.showToast('Error parsing settings file', 'error');
                        }
                    };
                    reader.readAsText(file);
                }
            };
            
            fileInput.click();
            
        } catch (error) {
            console.error('[SettingsPageController] Error importing settings:', error);
            this.showToast('Error importing settings', 'error');
        }
    }

    processImportedSettings(settings) {
        console.log('[SettingsPageController] Processing imported settings');
        
        try {
            // Validate settings structure
            if (!settings || typeof settings !== 'object') {
                throw new Error('Invalid settings format');
            }
            
            // Import each settings category
            const categories = ['general', 'appearance', 'system', 'advanced'];
            let importedCount = 0;
            
            categories.forEach(category => {
                if (settings[category]) {
                    localStorage.setItem(`settings_${category}`, JSON.stringify(settings[category]));
                    this.applySettings(category, settings[category]);
                    this.updateSettingsUI(category, settings[category]);
                    importedCount++;
                }
            });
            
            // Import auto-saved settings
            if (settings.autoSaved) {
                localStorage.setItem('autoSavedSettings', JSON.stringify(settings.autoSaved));
            }
            
            this.showToast(`Settings imported successfully (${importedCount} categories)`, 'success');
            
        } catch (error) {
            console.error('[SettingsPageController] Error processing imported settings:', error);
            this.showToast('Error processing imported settings', 'error');
        }
    }

    // Helper methods for settings management
    collectSettingsData(settingsType) {
        console.log(`[SettingsPageController] Collecting ${settingsType} settings data`);
        
        const data = {};
        const selector = `[data-setting-category="${settingsType}"]`;
        const settingElements = document.querySelectorAll(selector);
        
        settingElements.forEach(element => {
            const name = element.name || element.dataset.settingName;
            if (name) {
                if (element.type === 'checkbox') {
                    data[name] = element.checked;
                } else {
                    data[name] = element.value;
                }
            }
        });
        
        return data;
    }

    applySettings(settingsType, settings) {
        console.log(`[SettingsPageController] Applying ${settingsType} settings`);
        
        Object.entries(settings).forEach(([key, value]) => {
            this.applyIndividualSetting(settingsType, key, value);
        });
    }

    applyIndividualSetting(settingsType, key, value) {
        // Apply setting based on type and key
        switch (key) {
            case 'darkMode':
                document.body.classList.toggle('dark-mode', value);
                break;
            case 'fontSize':
                document.documentElement.style.setProperty('--base-font-size', `${value}px`);
                break;
            case 'animations':
                document.body.classList.toggle('no-animations', !value);
                break;
            default:
                console.log(`[SettingsPageController] Applied setting: ${key} = ${value}`);
        }
    }

    updateSettingsUI(settingsType, settings) {
        console.log(`[SettingsPageController] Updating UI for ${settingsType} settings`);
        
        Object.entries(settings).forEach(([key, value]) => {
            const element = document.querySelector(`[name="${key}"], [data-setting-name="${key}"]`);
            if (element) {
                if (element.type === 'checkbox') {
                    element.checked = value;
                } else {
                    element.value = value;
                }
            }
        });
    }

    getDefaultSettings(settingsType) {
        const defaults = {
            general: this.getDefaultGeneralSettings(),
            appearance: this.getDefaultAppearanceSettings(),
            system: this.getDefaultSystemSettings(),
            advanced: this.getDefaultAdvancedSettings()
        };
        
        return defaults[settingsType] || {};
    }

    getDefaultGeneralSettings() {
        return {
            autoSave: true,
            notifications: true,
            backupFrequency: 'daily'
        };
    }

    getDefaultAppearanceSettings() {
        return {
            darkMode: false,
            fontSize: 14,
            animations: true,
            compactMode: false
        };
    }

    getDefaultSystemSettings() {
        return {
            maxMemoryUsage: 1024,
            enableLogging: true,
            logLevel: 'info'
        };
    }

    getDefaultAdvancedSettings() {
        return {
            developerMode: false,
            debugMode: false,
            experimentalFeatures: false
        };
    }

    getDefaultApplicationSettings() {
        return {
            ...this.getDefaultGeneralSettings(),
            version: '1.0.0',
            initialized: true
        };
    }

    getDefaultUserPreferences() {
        return {
            ...this.getDefaultAppearanceSettings(),
            welcomeShown: false,
            tutorialCompleted: false
        };
    }

    applyApplicationSettings(settings) {
        console.log('[SettingsPageController] Applying application settings');
        this.applySettings('general', settings);
    }

    applyUserPreferences(prefs) {
        console.log('[SettingsPageController] Applying user preferences');
        this.applySettings('appearance', prefs);
    }

    loadGeneralSettings() {
        console.log('[SettingsPageController] Loading general settings');
        const settings = JSON.parse(localStorage.getItem('settings_general') || '{}');
        this.updateSettingsUI('general', settings);
    }

    loadAppearanceSettings() {
        console.log('[SettingsPageController] Loading appearance settings');
        const settings = JSON.parse(localStorage.getItem('settings_appearance') || '{}');
        this.updateSettingsUI('appearance', settings);
    }

    loadSystemSettings() {
        console.log('[SettingsPageController] Loading system settings');
        const settings = JSON.parse(localStorage.getItem('settings_system') || '{}');
        this.updateSettingsUI('system', settings);
    }

    loadAdvancedSettings() {
        console.log('[SettingsPageController] Loading advanced settings');
        const settings = JSON.parse(localStorage.getItem('settings_advanced') || '{}');
        this.updateSettingsUI('advanced', settings);
    }

    cleanup() {
        // Remove all tracked event listeners
        this.eventListeners.forEach(({element, event, handler}) => {
            if (element && element.removeEventListener) {
                element.removeEventListener(event, handler);
            }
        });
        this.eventListeners = [];
        
        // Cleanup managers
        Object.values(this.managers).forEach(manager => {
            if (typeof manager.cleanup === 'function') {
                manager.cleanup();
            }
        });
    }
    
    // Legacy addEventListener method for compatibility
    addEventListenerLegacy(element, event, handler) {
        if (element && typeof element.addEventListener === 'function') {
            element.addEventListener(event, handler);
            this.eventListeners.push({element, event, handler});
        }
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new SettingsPageController();
});

// Export for potential external use
export { SettingsPageController };
