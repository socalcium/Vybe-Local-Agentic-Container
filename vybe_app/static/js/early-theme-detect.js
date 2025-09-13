/**
 * EARLY THEME DETECTION - Runs immediately to prevent flashbang
 * This script must load synchronously in <head> before any content renders
 */

(function() {
    'use strict';
    
    // Immediate theme application to prevent flashbang
    function applyThemeImmediately() {
        const html = document.documentElement;
        const body = document.body;
        
        // Default to dark theme to prevent white flashbang
        let theme = 'dark';
        
        try {
            // Try to get saved theme preference
            const savedTheme = localStorage.getItem('vybe_theme_mode');
            if (savedTheme && ['light', 'dark', 'system'].includes(savedTheme)) {
                theme = savedTheme;
            }
        } catch {
            // localStorage not available, use dark default
        }
        
        // Handle system theme
        if (theme === 'system') {
            const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
            theme = prefersDark ? 'dark' : 'light';
        }
        
        // Apply theme immediately
        html.classList.remove('theme-light', 'theme-dark', 'theme-system');
        html.setAttribute('data-theme', theme);
        html.classList.add(`theme-${theme}`);
        
        if (body) {
            body.classList.remove('theme-light', 'theme-dark', 'theme-system');
            body.classList.add(`theme-${theme}`);
            body.setAttribute('data-theme', theme);
        }
        
        // Store the applied theme
        try {
            localStorage.setItem('vybe_current_theme', theme);
        } catch {
            // localStorage not available, continue
        }
    }
    
    // Apply theme immediately if DOM is ready, or wait for it
    if (document.documentElement) {
        applyThemeImmediately();
    } else {
        document.addEventListener('DOMContentLoaded', applyThemeImmediately);
    }
    
    // Listen for system theme changes
    if (window.matchMedia) {
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function() {
            try {
                const currentTheme = localStorage.getItem('vybe_theme_mode');
                if (currentTheme === 'system') {
                    applyThemeImmediately();
                }
            } catch {
                // Continue without localStorage
            }
        });
    }
    
    // Expose theme application function globally for other scripts
    window.vybeApplyTheme = applyThemeImmediately;
})();
