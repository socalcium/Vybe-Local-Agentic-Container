// Setup page functionality
class SetupManager {
    constructor() {
        this.cleanupFunctions = [];
        
        // Initialize when DOM is ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.init());
        } else {
            this.init();
        }
    }

    init() {
        this.initializeCopyButtons();
        this.setupEventListeners();
        this.checkAllStatus();
    }

    setupEventListeners() {
        // Add help button listener if it exists
        const helpBtn = document.getElementById('help-btn');
        if (helpBtn) {
            helpBtn.addEventListener('click', () => this.showHelp());
        }

        // Add refresh button listener
        const refreshBtn = document.getElementById('refresh-checks');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.runAllChecks());
        }

        // Add export results button listener
        const exportBtn = document.getElementById('export-results');
        if (exportBtn) {
            exportBtn.addEventListener('click', () => this.exportCheckResults());
        }

        // Add keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey || e.metaKey) {
                switch (e.key) {
                    case 'r':
                        if (e.shiftKey) {
                            e.preventDefault();
                            this.runAllChecks();
                        }
                        break;
                    case 'h':
                        if (e.shiftKey) {
                            e.preventDefault();
                            this.showHelp();
                        }
                        break;
                    case 'e':
                        if (e.shiftKey) {
                            e.preventDefault();
                            this.exportCheckResults();
                        }
                        break;
                }
            }
        });

        // Show initial help tip
        setTimeout(() => {
            this.showInfo('Setup system initialized. Use Ctrl+Shift+R to refresh checks, Ctrl+Shift+H for help.');
        }, 1000);
    }

    initializeCopyButtons() {
        const copyButtons = document.querySelectorAll('.copy-btn');
        copyButtons.forEach(button => {
            button.addEventListener('click', async (e) => {
                const textToCopy = e.target.getAttribute('data-copy');
                const originalText = e.target.textContent;
                
                try {
                    // Try modern clipboard API first
                    await navigator.clipboard.writeText(textToCopy);
                    e.target.textContent = '✅ Copied!';
                    e.target.style.background = 'var(--success-color)';
                    this.showSuccess(`Copied: ${textToCopy.substring(0, 30)}${textToCopy.length > 30 ? '...' : ''}`);
                    
                    setTimeout(() => {
                        e.target.textContent = originalText;
                        e.target.style.background = 'var(--primary-color)';
                    }, 2000);
                } catch (err) {
                    console.error('Failed to copy text: ', err);
                    
                    // Fallback: create temporary textarea
                    try {
                        const textarea = document.createElement('textarea');
                        textarea.value = textToCopy;
                        textarea.style.position = 'fixed';
                        textarea.style.opacity = '0';
                        document.body.appendChild(textarea);
                        textarea.select();
                        document.execCommand('copy');
                        document.body.removeChild(textarea);
                        
                        e.target.textContent = '✅ Copied!';
                        e.target.style.background = 'var(--success-color)';
                        this.showSuccess(`Copied via fallback: ${textToCopy.substring(0, 30)}${textToCopy.length > 30 ? '...' : ''}`);
                        
                        setTimeout(() => {
                            e.target.textContent = originalText;
                            e.target.style.background = 'var(--primary-color)';
                        }, 2000);
                    } catch (fallbackErr) {
                        console.error('Fallback copy failed:', fallbackErr);
                        e.target.textContent = '❌ Failed';
                        e.target.style.background = 'var(--error-color)';
                        this.showError('Copy failed! Please copy manually.');
                        
                        // Show manual copy instructions
                        alert(`Failed to copy automatically. Please copy manually:\n\n${textToCopy}`);
                        
                        setTimeout(() => {
                            e.target.textContent = originalText;
                            e.target.style.background = 'var(--primary-color)';
                        }, 3000);
                    }
                }
            });
        });
    }

    async checkAllStatus() {
        const checks = [
            { id: 'python-check', checker: this.checkPython.bind(this), name: 'Python' },
            { id: 'git-check', checker: this.checkGit.bind(this), name: 'Git' },
            { id: 'venv-check', checker: this.checkVirtualEnv.bind(this), name: 'Virtual Environment' },
            { id: 'llm-backend-check', checker: this.checkLLMBackend.bind(this), name: 'LLM Backend' },
            { id: 'sd-check', checker: this.checkStableDiffusion.bind(this), name: 'Stable Diffusion' },
            { id: 'tts-check', checker: this.checkTTS.bind(this), name: 'Text-to-Speech' },
            { id: 'whisper-check', checker: this.checkWhisper.bind(this), name: 'Whisper' },
            { id: 'models-check', checker: this.checkModels.bind(this), name: 'Models' }
        ];
        
        // Reset all items to checking state
        checks.forEach(check => {
            this.setCheckStatus(check.id, 'checking', '⏳', 'Checking...');
        });
        
        let successCount = 0;
        let warningCount = 0;
        let errorCount = 0;
        
        // Run all checks with timeout
        for (const check of checks) {
            try {
                await Promise.race([
                    check.checker(check.id),
                    new Promise((_, reject) => 
                        setTimeout(() => reject(new Error('Check timeout')), 10000)
                    )
                ]);
                
                // Count status results
                const item = document.getElementById(check.id);
                if (item) {
                    if (item.classList.contains('success')) successCount++;
                    else if (item.classList.contains('warning')) warningCount++;
                    else if (item.classList.contains('error')) errorCount++;
                }
            } catch (error) {
                console.error(`Error checking ${check.id}:`, error);
                this.setCheckStatus(check.id, 'error', '❌', `Check failed: ${error.message}`);
                errorCount++;
            }
        }
        
        // Show summary
        const total = checks.length;
        let summaryMessage = `Checks completed: ${successCount}/${total} successful`;
        if (warningCount > 0) summaryMessage += `, ${warningCount} warnings`;
        if (errorCount > 0) summaryMessage += `, ${errorCount} errors`;
        
        if (errorCount === 0 && warningCount === 0) {
            this.showSuccess(summaryMessage + ' - System ready!');
        } else if (errorCount === 0) {
            this.showWarning(summaryMessage + ' - Minor issues detected');
        } else {
            this.showError(summaryMessage + ' - Action required');
        }
    }

    setCheckStatus(itemId, status, icon, text) {
        const item = document.getElementById(itemId);
        if (!item) return;
        
        const statusIcon = item.querySelector('.status-icon');
        const statusText = item.querySelector('.status-text');
        const commands = item.querySelector('.commands');
        
        // Remove previous status classes
        item.classList.remove('success', 'warning', 'error', 'checking');
        
        // Add new status class
        if (status !== 'checking') {
            item.classList.add(status);
        } else {
            item.classList.add('checking');
        }
        
        // Update icon and text
        if (statusIcon) statusIcon.textContent = icon;
        if (statusText) statusText.textContent = text;
        
        // Show/hide commands
        if (commands) {
            if (status === 'error' || status === 'warning') {
                commands.classList.remove('hidden');
            } else {
                commands.classList.add('hidden');
            }
        }
    }

    async checkPython(itemId) {
        try {
            const response = await fetch('/api/setup/check-python');
            const data = await response.json();
            
            if (data.installed && data.version_ok) {
                this.setCheckStatus(itemId, 'success', '✅', `Python ${data.version}`);
            } else if (data.installed) {
                this.setCheckStatus(itemId, 'warning', '⚠️', `Python ${data.version} (upgrade recommended)`);
            } else {
                this.setCheckStatus(itemId, 'error', '❌', 'Not installed');
            }
        } catch {
            this.setCheckStatus(itemId, 'error', '❌', 'Check failed');
        }
    }

    async checkGit(itemId) {
        try {
            const response = await fetch('/api/setup/check-git');
            const data = await response.json();
            
            if (data.installed) {
                this.setCheckStatus(itemId, 'success', '✅', `Git ${data.version}`);
            } else {
                this.setCheckStatus(itemId, 'error', '❌', 'Not installed');
            }
        } catch {
            this.setCheckStatus(itemId, 'error', '❌', 'Check failed');
        }
    }

    async checkVirtualEnv(itemId) {
        try {
            const response = await fetch('/api/setup/check-venv');
            const data = await response.json();
            
            if (data.exists && data.active) {
                this.setCheckStatus(itemId, 'success', '✅', 'Active');
            } else if (data.exists) {
                this.setCheckStatus(itemId, 'warning', '⚠️', 'Not activated');
            } else {
                this.setCheckStatus(itemId, 'error', '❌', 'Not created');
            }
        } catch {
            this.setCheckStatus(itemId, 'error', '❌', 'Check failed');
        }
    }

    async checkLLMBackend(itemId) {
        try {
            const response = await fetch('/api/setup/check-llm-backend');
            const data = await response.json();
            
            if (data.running && data.models_available) {
                this.setCheckStatus(itemId, 'success', '✅', 'Ready');
            } else if (data.running) {
                this.setCheckStatus(itemId, 'warning', '⚠️', 'No models');
            } else {
                this.setCheckStatus(itemId, 'error', '❌', 'Not running');
            }
        } catch {
            this.setCheckStatus(itemId, 'error', '❌', 'Check failed');
        }
    }

    async checkStableDiffusion(itemId) {
        try {
            const response = await fetch('/api/setup/check-sd');
            const data = await response.json();
            
            if (data.repo_exists && data.dependencies_installed) {
                this.setCheckStatus(itemId, 'success', '✅', 'Ready');
            } else if (data.repo_exists) {
                this.setCheckStatus(itemId, 'warning', '⚠️', 'Missing deps');
            } else {
                this.setCheckStatus(itemId, 'error', '❌', 'Not cloned');
            }
        } catch {
            this.setCheckStatus(itemId, 'error', '❌', 'Check failed');
        }
    }

    async checkTTS(itemId) {
        try {
            const response = await fetch('/api/setup/check-tts');
            const data = await response.json();
            
            if (data.available) {
                this.setCheckStatus(itemId, 'success', '✅', 'Ready');
            } else {
                this.setCheckStatus(itemId, 'warning', '⚠️', 'Not available');
            }
        } catch {
            this.setCheckStatus(itemId, 'error', '❌', 'Check failed');
        }
    }

    async checkWhisper(itemId) {
        try {
            const response = await fetch('/api/setup/check-whisper');
            const data = await response.json();
            
            if (data.installed) {
                this.setCheckStatus(itemId, 'success', '✅', 'Ready');
            } else {
                this.setCheckStatus(itemId, 'error', '❌', 'Not installed');
            }
        } catch {
            this.setCheckStatus(itemId, 'error', '❌', 'Check failed');
        }
    }

    async checkModels(itemId) {
        try {
            const response = await fetch('/api/setup/check-models');
            const data = await response.json();
            
            if (data.models_available && data.models_count > 0) {
                this.setCheckStatus(itemId, 'success', '✅', `${data.models_count} models available`);
            } else {
                this.setCheckStatus(itemId, 'warning', '⚠️', 'No models found');
            }
        } catch {
            this.setCheckStatus(itemId, 'error', '❌', 'Check failed');
        }
    }

    showHelp() {
        const helpContent = `
            <div style="max-width: 600px; margin: 0 auto; padding: 2rem; background: var(--card-background); border-radius: var(--border-radius);">
                <h2>🆘 Setup Help</h2>
                <h3>Common Issues:</h3>
                <ul>
                    <li><strong>Commands not found:</strong> Make sure to activate the virtual environment first</li>
                    <li><strong>Permission errors:</strong> Run terminal as administrator on Windows</li>
                    <li><strong>Network issues:</strong> Check your internet connection for downloads</li>
                    <li><strong>Disk space:</strong> Ensure you have at least 10GB free space</li>
                </ul>
                <h3>Getting Help:</h3>
                <ul>
                    <li>Check the console for detailed error messages</li>
                    <li>Visit the Vybe documentation</li>
                    <li>Join our community Discord</li>
                    <li>Create an issue on GitHub</li>
                </ul>
                <button onclick="this.parentElement.parentElement.remove()" style="margin-top: 1rem; padding: 0.5rem 1rem; background: var(--primary-color); color: white; border: none; border-radius: 4px; cursor: pointer;">Close</button>
            </div>
        `;
        
        const overlay = document.createElement('div');
        overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.7);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 1000;
        `;
        overlay.innerHTML = helpContent;
        
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) {
                overlay.remove();
            }
        });
        
        document.body.appendChild(overlay);
    }

    showToast(message, type = 'info') {
        // Create toast element if it doesn't exist
        let toastContainer = document.getElementById('setup-toast-container');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.id = 'setup-toast-container';
            toastContainer.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 9999;
                max-width: 300px;
            `;
            document.body.appendChild(toastContainer);
        }

        const toast = document.createElement('div');
        const typeColors = {
            'success': '#28a745',
            'error': '#dc3545',
            'warning': '#ffc107',
            'info': '#17a2b8'
        };
        
        toast.style.cssText = `
            background: ${typeColors[type] || typeColors.info};
            color: white;
            padding: 12px 16px;
            border-radius: 4px;
            margin-bottom: 8px;
            font-size: 14px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.2);
            opacity: 0;
            transition: opacity 0.3s ease;
        `;
        toast.textContent = message;
        
        toastContainer.appendChild(toast);
        
        // Fade in
        setTimeout(() => toast.style.opacity = '1', 10);
        
        // Auto remove after 4 seconds
        setTimeout(() => {
            toast.style.opacity = '0';
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
            }, 300);
        }, 4000);
    }

    showSuccess(message) {
        this.showToast(message, 'success');
    }

    showError(message) {
        this.showToast(message, 'error');
    }

    showWarning(message) {
        this.showToast(message, 'warning');
    }

    showInfo(message) {
        this.showToast(message, 'info');
    }

    async runAllChecks() {
        this.showInfo('Starting comprehensive system checks...');
        await this.checkAllStatus();
        this.showSuccess('System checks completed!');
    }

    // Export check results for debugging
    exportCheckResults() {
        const results = {};
        const checkItems = [
            'python-check', 'git-check', 'venv-check', 'llm-backend-check',
            'sd-check', 'tts-check', 'whisper-check', 'models-check'
        ];
        
        checkItems.forEach(itemId => {
            const item = document.getElementById(itemId);
            if (item) {
                const statusText = item.querySelector('.status-text')?.textContent || 'Unknown';
                const statusClass = item.classList.contains('success') ? 'success' :
                                  item.classList.contains('warning') ? 'warning' :
                                  item.classList.contains('error') ? 'error' : 'unknown';
                results[itemId] = { status: statusClass, text: statusText };
            }
        });
        
        const dataStr = JSON.stringify(results, null, 2);
        const blob = new Blob([dataStr], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.href = url;
        a.download = `vybe-setup-results-${new Date().toISOString().split('T')[0]}.json`;
        a.click();
        
        URL.revokeObjectURL(url);
        this.showSuccess('Check results exported successfully!');
    }

    // Cleanup method for event listeners
    destroy() {
        this.cleanupFunctions.forEach(cleanup => cleanup());
        this.cleanupFunctions = [];
    }
}

// Initialize the setup manager
window.setupManager = new SetupManager();
