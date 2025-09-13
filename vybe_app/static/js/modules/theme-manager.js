/**
 * Theme Manager Module
 * Handles theme switching, persistence, and system preference detection
 */

import { ApiUtils } from '../utils/api-utils.js';

export class ThemeManager {
    constructor() {
        this.currentTheme = 'system';
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
        this.loadTheme();
        this.setupEventListeners();
        this.setupSystemPreferenceListener();
    }

    setupEventListeners() {
        const themeSelector = document.getElementById('theme-selector');
        if (themeSelector) {
            window.eventManager.add(themeSelector, 'change', (e) => {
                this.setTheme(e.target.value);
            });
        }
    }

    setupSystemPreferenceListener() {
        // Listen for system theme changes
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
            if (this.currentTheme === 'system') {
                this.applyTheme('system');
            }
        });
    }

    async loadTheme() {
        try {
            const data = await ApiUtils.safeFetch('/api/settings/theme_mode');
            if (data && data.theme_mode) {
                this.currentTheme = data.theme_mode;
                this.applyTheme(this.currentTheme);
                this.updateSelector();
            }
        } catch (error) {
            console.warn('Failed to load theme preference:', error);
            this.applyTheme('system');
        }
    }

    async setTheme(theme) {
        try {
            const data = await ApiUtils.safeFetch('/api/settings/theme_mode', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ theme_mode: theme })
            });

            if (data && data.success) {
                this.currentTheme = theme;
                this.applyTheme(theme);
                ApiUtils.showGlobalStatus(`Theme changed to ${theme} mode`, 'success');
            } else {
                ApiUtils.showGlobalStatus('Failed to save theme preference', 'error');
            }
        } catch (error) {
            console.error('Error saving theme:', error);
            ApiUtils.showGlobalStatus('Failed to save theme preference', 'error');
        }
    }

    applyTheme(theme) {
        const html = document.documentElement;
        const body = document.body;
        
        // Store theme preference for early detection
        try {
            localStorage.setItem('vybe_theme_mode', theme);
        } catch {
            // localStorage not available
        }
        
        // Remove existing theme classes from both html and body
        html.classList.remove('theme-light', 'theme-dark', 'theme-system');
        body.classList.remove('theme-light', 'theme-dark', 'theme-system');
        
        // Apply new theme
        if (theme === 'system') {
            // Use system preference
            const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
            const actualTheme = prefersDark ? 'dark' : 'light';
            
            html.classList.add('theme-system');
            html.setAttribute('data-theme', actualTheme);
            body.classList.add('theme-system');
            body.setAttribute('data-theme', actualTheme);
            
            // Store actual applied theme
            try {
                localStorage.setItem('vybe_current_theme', actualTheme);
            } catch {
                /* localStorage error is not critical */
            }
        } else {
            html.classList.add(`theme-${theme}`);
            html.setAttribute('data-theme', theme);
            body.classList.add(`theme-${theme}`);
            body.setAttribute('data-theme', theme);
            
            // Store actual applied theme
            try {
                localStorage.setItem('vybe_current_theme', theme);
            } catch {
                /* localStorage error is not critical */
            }
        }
        
        // Use early theme detection function if available
        if (window.vybeApplyTheme) {
            window.vybeApplyTheme();
        }
    }

    updateSelector() {
        const themeSelector = document.getElementById('theme-selector');
        if (themeSelector) {
            themeSelector.value = this.currentTheme;
        }
    }

    getCurrentTheme() {
        return this.currentTheme;
    }
}
