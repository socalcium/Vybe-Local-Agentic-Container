/**
 * User Profile Manager Module
 * Handles user profile display, editing, and password changes
 */

import { ApiUtils } from '../utils/api-utils.js';

export class UserProfileManager {
    constructor() {
        this.currentUserData = null;
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
        this.loadUserProfile();
        this.loadApiKeyStatus();
        this.setupEventListeners();
    }

    setupEventListeners() {
        // Edit profile button
        const editProfileBtn = document.getElementById('edit-profile-btn');
        if (editProfileBtn) {
            window.eventManager.add(editProfileBtn, 'click', () => {
                this.showEditProfileModal();
            });
        }

        // Save profile button
        const saveProfileBtn = document.getElementById('save-profile');
        if (saveProfileBtn) {
            window.eventManager.add(saveProfileBtn, 'click', () => {
                this.saveProfile();
            });
        }

        // Change password button
        const changePasswordBtn = document.getElementById('change-password-btn');
        if (changePasswordBtn) {
            window.eventManager.add(changePasswordBtn, 'click', () => {
                this.showChangePasswordModal();
            });
        }

        // Save password button
        const savePasswordBtn = document.getElementById('save-password');
        if (savePasswordBtn) {
            window.eventManager.add(savePasswordBtn, 'click', () => {
                this.changePassword();
            });
        }

        // API Key management buttons
        const generateApiKeyBtn = document.getElementById('generate-api-key-btn');
        if (generateApiKeyBtn) {
            window.eventManager.add(generateApiKeyBtn, 'click', () => {
                this.generateApiKey();
            });
        }

        const revokeApiKeyBtn = document.getElementById('revoke-api-key-btn');
        if (revokeApiKeyBtn) {
            window.eventManager.add(revokeApiKeyBtn, 'click', () => {
                this.revokeApiKey();
            });
        }

        const copyApiKeyBtn = document.getElementById('copy-api-key');
        if (copyApiKeyBtn) {
            window.eventManager.add(copyApiKeyBtn, 'click', () => {
                this.copyApiKey();
            });
        }

        // Cancel buttons
        document.querySelectorAll('.cancel-profile, .cancel-password').forEach(btn => {
            window.eventManager.add(btn, 'click', (e) => {
                const modal = e.target.closest('.modal');
                if (modal) {
                    modal.style.display = 'none';
                }
            });
        });
    }

    async loadUserProfile() {
        try {
            const data = await ApiUtils.safeFetch('/api/user/profile');
            if (data) {
                this.currentUserData = data;
                this.displayUserProfile(data);
            }
        } catch (error) {
            console.error('Error loading user profile:', error);
            ApiUtils.showGlobalStatus('Failed to load user profile', 'error');
        }
    }

    displayUserProfile(userData) {
        const elements = {
            'profile-username': userData.username || 'N/A',
            'profile-email': userData.email || 'Not set',
            'profile-created': userData.created_at ? 
                new Date(userData.created_at).toLocaleDateString() : 'N/A'
        };

        Object.entries(elements).forEach(([id, value]) => {
            const element = document.getElementById(id);
            if (element) {
                element.textContent = value;
            }
        });
    }

    showEditProfileModal() {
        if (!this.currentUserData) return;

        // Pre-fill form
        const usernameInput = document.getElementById('edit-username');
        const emailInput = document.getElementById('edit-email');
        
        if (usernameInput) usernameInput.value = this.currentUserData.username || '';
        if (emailInput) emailInput.value = this.currentUserData.email || '';

        const modal = document.getElementById('edit-profile-modal');
        if (modal) {
            modal.style.display = 'block';
        }
    }

    async saveProfile() {
        const usernameInput = document.getElementById('edit-username');
        const emailInput = document.getElementById('edit-email');

        if (!usernameInput || !emailInput) return;

        const username = usernameInput.value.trim();
        const email = emailInput.value.trim();

        if (!username) {
            ApiUtils.showGlobalStatus('Username is required', 'error');
            return;
        }

        try {
            const data = await ApiUtils.safeFetch('/api/user/profile', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ username, email })
            });

            if (data && data.success) {
                ApiUtils.showGlobalStatus('Profile updated successfully', 'success');
                document.getElementById('edit-profile-modal').style.display = 'none';
                await this.loadUserProfile(); // Refresh profile data
            } else {
                const errorMsg = data?.error || 'Failed to update profile';
                ApiUtils.showGlobalStatus(errorMsg, 'error');
            }
        } catch (error) {
            console.error('Error saving profile:', error);
            ApiUtils.showGlobalStatus('Error updating profile', 'error');
        }
    }

    showChangePasswordModal() {
        // Clear form
        const form = document.getElementById('change-password-form');
        if (form) {
            form.reset();
        }

        const modal = document.getElementById('change-password-modal');
        if (modal) {
            modal.style.display = 'block';
        }
    }

    async changePassword() {
        const currentPasswordInput = document.getElementById('current-password');
        const newPasswordInput = document.getElementById('new-password');
        const confirmPasswordInput = document.getElementById('confirm-password');

        if (!currentPasswordInput || !newPasswordInput || !confirmPasswordInput) return;

        const currentPassword = currentPasswordInput.value;
        const newPassword = newPasswordInput.value;
        const confirmPassword = confirmPasswordInput.value;

        // Validation
        if (!currentPassword || !newPassword || !confirmPassword) {
            ApiUtils.showGlobalStatus('All password fields are required', 'error');
            return;
        }

        if (newPassword !== confirmPassword) {
            ApiUtils.showGlobalStatus('New passwords do not match', 'error');
            return;
        }

        if (newPassword.length < 6) {
            ApiUtils.showGlobalStatus('New password must be at least 6 characters', 'error');
            return;
        }

        try {
            const data = await ApiUtils.safeFetch('/api/user/change_password', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ 
                    current_password: currentPassword, 
                    new_password: newPassword 
                })
            });

            if (data && data.success) {
                ApiUtils.showGlobalStatus('Password changed successfully', 'success');
                document.getElementById('change-password-modal').style.display = 'none';
                document.getElementById('change-password-form').reset();
            } else {
                const errorMsg = data?.error || 'Failed to change password';
                ApiUtils.showGlobalStatus(errorMsg, 'error');
            }
        } catch (error) {
            console.error('Error changing password:', error);
            ApiUtils.showGlobalStatus('Error changing password', 'error');
        }
    }

    getCurrentUserData() {
        return this.currentUserData;
    }

    async loadApiKeyStatus() {
        try {
            const data = await ApiUtils.safeFetch('/api/user/api_key_status');
            if (data) {
                this.displayApiKeyStatus(data);
            }
        } catch (error) {
            console.error('Error loading API key status:', error);
            const statusElement = document.getElementById('api-key-status');
            if (statusElement) {
                statusElement.textContent = 'Error loading status';
            }
        }
    }

    displayApiKeyStatus(statusData) {
        const statusElement = document.getElementById('api-key-status');
        const generateBtn = document.getElementById('generate-api-key-btn');
        const revokeBtn = document.getElementById('revoke-api-key-btn');
        const displayDiv = document.getElementById('api-key-display');

        if (!statusElement) return;

        if (statusData.has_api_key) {
            statusElement.textContent = '✅ Active';
            statusElement.style.color = '#28a745';
            if (generateBtn) generateBtn.textContent = 'Regenerate API Key';
            if (revokeBtn) revokeBtn.style.display = 'inline-block';
        } else {
            statusElement.textContent = '❌ Not configured';
            statusElement.style.color = '#dc3545';
            if (generateBtn) generateBtn.textContent = 'Generate API Key';
            if (revokeBtn) revokeBtn.style.display = 'none';
            if (displayDiv) displayDiv.style.display = 'none';
        }
    }

    async generateApiKey() {
        const isRegenerate = document.getElementById('generate-api-key-btn').textContent.includes('Regenerate');
        
        if (isRegenerate) {
            const confirmed = confirm('This will invalidate your current API key. Any mobile apps using it will need to be reconfigured. Continue?');
            if (!confirmed) return;
        }

        try {
            const response = await fetch('/api/user/generate-api-key', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });

            if (response.ok) {
                const data = await response.json();
                if (data.success && data.api_key) {
                    this.displayNewApiKey(data.api_key);
                    await this.loadApiKeyStatus(); // Refresh status
                    ApiUtils.showGlobalStatus('API key generated successfully', 'success');
                } else {
                    throw new Error(data.error || 'Failed to generate API key');
                }
            } else {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Failed to generate API key');
            }
        } catch (error) {
            console.error('Error generating API key:', error);
            ApiUtils.showGlobalStatus(error.message || 'Failed to generate API key', 'error');
        }
    }

    displayNewApiKey(apiKey) {
        const displayDiv = document.getElementById('api-key-display');
        const valueInput = document.getElementById('api-key-value');

        if (displayDiv && valueInput) {
            valueInput.value = apiKey;
            displayDiv.style.display = 'block';
            
            // Auto-select the key for easy copying
            valueInput.select();
            valueInput.focus();
        }
    }

    async copyApiKey() {
        const valueInput = document.getElementById('api-key-value');
        if (!valueInput || !valueInput.value) return;

        try {
            await navigator.clipboard.writeText(valueInput.value);
            ApiUtils.showGlobalStatus('API key copied to clipboard', 'success');
            
            // Temporarily change button text
            const copyBtn = document.getElementById('copy-api-key');
            if (copyBtn) {
                const originalText = copyBtn.textContent;
                copyBtn.textContent = 'Copied!';
                setTimeout(() => {
                    copyBtn.textContent = originalText;
                }, 2000);
            }
        } catch (error) {
            console.error('Error copying to clipboard:', error);
            // Fallback for older browsers
            valueInput.select();
            document.execCommand('copy');
            ApiUtils.showGlobalStatus('API key selected for copying', 'info');
        }
    }

    async revokeApiKey() {
        const confirmed = confirm('This will permanently disable your API key. Any mobile apps using it will stop working. Continue?');
        if (!confirmed) return;

        try {
            const data = await ApiUtils.safeFetch('/api/user/revoke_api_key', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });

            if (data && data.success) {
                ApiUtils.showGlobalStatus('API key revoked successfully', 'success');
                await this.loadApiKeyStatus(); // Refresh status
                
                // Hide the key display
                const displayDiv = document.getElementById('api-key-display');
                if (displayDiv) {
                    displayDiv.style.display = 'none';
                }
            } else {
                const errorMsg = data?.error || 'Failed to revoke API key';
                ApiUtils.showGlobalStatus(errorMsg, 'error');
            }
        } catch (error) {
            console.error('Error revoking API key:', error);
            ApiUtils.showGlobalStatus('Error revoking API key', 'error');
        }
    }
}
