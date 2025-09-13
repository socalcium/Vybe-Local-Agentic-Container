/**
 * In-App Terminal Component for Vybe
 * Provides debugging terminal interface within the web application with enhanced consistency and accuracy
 */

class VybeTerminal {
    constructor() {
        this.isVisible = localStorage.getItem('vybeTerminalVisible') === 'true';
        this.logs = [];
        this.maxLogs = 500;
        this.terminal = null;
        this.input = null;
        this.output = null;
        this.commandHistory = [];
        this.historyIndex = -1;
        this.isProcessing = false;
        this.connectionStatus = 'disconnected';
        this.lastHeartbeat = null;
        
        this.setupTerminal();
        this.setupKeyboardShortcuts();
        this.startHeartbeat();
        
        // Connect to error manager if available
        if (window.vybeErrorManager) {
            this.connectToErrorManager();
        }
        
        // Cleanup functions for event listeners
        this.cleanupFunctions = [];
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
    
    setupTerminal() {
        // Create terminal HTML structure
        this.createTerminalHTML();
        
        // Show/hide based on saved preference
        if (this.isVisible) {
            this.show();
        }
        
        // Capture console logs
        this.interceptConsoleLogs();
        
        // Initialize connection status
        this.updateConnectionStatus();
    }
    
    createTerminalHTML() {
        const terminalHTML = `
            <div id="vybe-terminal" class="vybe-terminal ${this.isVisible ? 'visible' : 'hidden'}">
                <div class="terminal-header">
                    <span class="terminal-title">🖥️ Vybe Debug Terminal</span>
                    <div class="terminal-status">
                        <span id="terminal-connection-status" class="status-indicator disconnected">●</span>
                        <span id="terminal-status-text">Disconnected</span>
                    </div>
                    <div class="terminal-controls">
                        <button id="terminal-clear" class="terminal-btn" title="Clear Terminal">🗑️</button>
                        <button id="terminal-export" class="terminal-btn" title="Export Logs">📁</button>
                        <button id="terminal-refresh" class="terminal-btn" title="Refresh Status">🔄</button>
                        <button id="terminal-minimize" class="terminal-btn" title="Minimize">➖</button>
                        <button id="terminal-close" class="terminal-btn" title="Close">❌</button>
                    </div>
                </div>
                <div class="terminal-body">
                    <div id="terminal-output" class="terminal-output"></div>
                    <div class="terminal-input-line">
                        <span class="terminal-prompt">vybe></span>
                        <input id="terminal-input" class="terminal-input" type="text" placeholder="Enter command..." autocomplete="off">
                        <span id="terminal-processing" class="processing-indicator hidden">⏳</span>
                    </div>
                </div>
            </div>
        `;
        
        // Add CSS styles
        const styles = `
            <style>
                .vybe-terminal {
                    position: fixed;
                    bottom: 0;
                    right: 0;
                    width: 60%;
                    max-width: 800px;
                    min-width: 400px;
                    height: 400px;
                    background: #1a1a1a;
                    border: 1px solid #333;
                    border-radius: 8px 8px 0 0;
                    font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
                    font-size: 12px;
                    color: #00ff00;
                    z-index: 10000;
                    box-shadow: 0 -4px 20px rgba(0,0,0,0.5);
                    resize: both;
                    overflow: hidden;
                    transition: all 0.3s ease;
                }
                
                .vybe-terminal.hidden {
                    display: none;
                }
                
                .vybe-terminal.minimized {
                    height: 40px;
                }
                
                .vybe-terminal.minimized .terminal-body {
                    display: none;
                }
                
                .terminal-header {
                    background: #2d2d2d;
                    padding: 8px 12px;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    border-bottom: 1px solid #333;
                    cursor: move;
                }
                
                .terminal-title {
                    font-weight: bold;
                    color: #fff;
                }
                
                .terminal-status {
                    display: flex;
                    align-items: center;
                    gap: 5px;
                    font-size: 10px;
                }
                
                .status-indicator {
                    font-size: 12px;
                    font-weight: bold;
                }
                
                .status-indicator.connected {
                    color: #00ff00;
                }
                
                .status-indicator.disconnected {
                    color: #ff4444;
                }
                
                .status-indicator.connecting {
                    color: #ffaa44;
                    animation: pulse 1s infinite;
                }
                
                @keyframes pulse {
                    0%, 100% { opacity: 1; }
                    50% { opacity: 0.5; }
                }
                
                .terminal-controls {
                    display: flex;
                    gap: 5px;
                }
                
                .terminal-btn {
                    background: #333;
                    border: none;
                    color: #fff;
                    width: 24px;
                    height: 24px;
                    border-radius: 4px;
                    cursor: pointer;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }
                
                .terminal-btn:hover {
                    background: #444;
                }
                
                .terminal-body {
                    display: flex;
                    flex-direction: column;
                    height: calc(100% - 40px);
                }
                
                .terminal-output {
                    flex: 1;
                    padding: 10px;
                    overflow-y: auto;
                    background: #1a1a1a;
                    white-space: pre-wrap;
                    word-wrap: break-word;
                }
                
                .terminal-input-line {
                    display: flex;
                    align-items: center;
                    padding: 8px 10px;
                    background: #222;
                    border-top: 1px solid #333;
                }
                
                .terminal-prompt {
                    color: #00ff00;
                    margin-right: 8px;
                    font-weight: bold;
                }
                
                .terminal-input {
                    flex: 1;
                    background: transparent;
                    border: none;
                    color: #00ff00;
                    font-family: inherit;
                    font-size: inherit;
                    outline: none;
                }
                
                .processing-indicator {
                    margin-left: 8px;
                    color: #ffaa44;
                    animation: spin 1s linear infinite;
                }
                
                .processing-indicator.hidden {
                    display: none;
                }
                
                @keyframes spin {
                    0% { transform: rotate(0deg); }
                    100% { transform: rotate(360deg); }
                }
                
                .terminal-log {
                    margin: 2px 0;
                }
                
                .terminal-log.error {
                    color: #ff4444;
                }
                
                .terminal-log.warn {
                    color: #ffaa44;
                }
                
                .terminal-log.info {
                    color: #44aaff;
                }
                
                .terminal-log.debug {
                    color: #888;
                }
                
                .terminal-log.success {
                    color: #00ff00;
                }
                
                .terminal-timestamp {
                    color: #666;
                    font-size: 10px;
                }
                
                .terminal-command {
                    color: #ffff00;
                    font-weight: bold;
                }
                
                .terminal-response {
                    color: #00ffff;
                    margin-left: 10px;
                }
            </style>
        `;
        
        // Add to document
        if (!document.getElementById('vybe-terminal')) {
            document.head.insertAdjacentHTML('beforeend', styles);
            document.body.insertAdjacentHTML('beforeend', terminalHTML);
            
            // Get references
            this.terminal = document.getElementById('vybe-terminal');
            this.input = document.getElementById('terminal-input');
            this.output = document.getElementById('terminal-output');
            
            // Setup event listeners
            this.setupEventListeners();
        }
    }
    
    setupEventListeners() {
        // Terminal controls
        const clearBtn = document.getElementById('terminal-clear');
        const exportBtn = document.getElementById('terminal-export');
        const refreshBtn = document.getElementById('terminal-refresh');
        const minimizeBtn = document.getElementById('terminal-minimize');
        const closeBtn = document.getElementById('terminal-close');

        if (clearBtn) clearBtn.addEventListener('click', () => this.clearTerminal());
        if (exportBtn) exportBtn.addEventListener('click', () => this.exportLogs());
        if (refreshBtn) refreshBtn.addEventListener('click', () => this.refreshStatus());
        if (minimizeBtn) minimizeBtn.addEventListener('click', () => this.toggleMinimize());
        if (closeBtn) closeBtn.addEventListener('click', () => this.hide());
        
        // Input handling with enhanced event management
        if (this.input) {
            const handleKeydown = (e) => {
                if (e.key === 'Enter' && !this.isProcessing) {
                    this.processCommand(this.input.value);
                    this.input.value = '';
                    this.historyIndex = -1;
                } else if (e.key === 'ArrowUp') {
                    e.preventDefault();
                    this.navigateHistory('up');
                } else if (e.key === 'ArrowDown') {
                    e.preventDefault();
                    this.navigateHistory('down');
                } else if (e.key === 'Tab') {
                    e.preventDefault();
                    this.handleTabCompletion();
                }
            };

            // Use eventManager if available, otherwise fall back to direct listeners
            if (window.eventManager && window.eventManager.add) {
                window.eventManager.add(this.input, 'keydown', handleKeydown);
                this.cleanupFunctions.push(() => {
                    if (window.eventManager.remove) {
                        window.eventManager.remove(this.input, 'keydown', handleKeydown);
                    }
                });
            } else {
                this.input.addEventListener('keydown', handleKeydown);
                this.cleanupFunctions.push(() => {
                    this.input.removeEventListener('keydown', handleKeydown);
                });
            }
        }
        
        // Make terminal draggable
        this.makeDraggable();
        
        // Auto-focus input when terminal is clicked
        if (this.terminal) {
            const handleTerminalClick = () => {
                if (this.input && this.isVisible) {
                    this.input.focus();
                }
            };

            if (window.eventManager && window.eventManager.add) {
                window.eventManager.add(this.terminal, 'click', handleTerminalClick);
                this.cleanupFunctions.push(() => {
                    if (window.eventManager.remove) {
                        window.eventManager.remove(this.terminal, 'click', handleTerminalClick);
                    }
                });
            } else {
                this.terminal.addEventListener('click', handleTerminalClick);
                this.cleanupFunctions.push(() => {
                    this.terminal.removeEventListener('click', handleTerminalClick);
                });
            }
        }
    }
    
    navigateHistory(direction) {
        if (this.commandHistory.length === 0) return;
        
        if (direction === 'up') {
            if (this.historyIndex < this.commandHistory.length - 1) {
                this.historyIndex++;
            }
        } else if (direction === 'down') {
            if (this.historyIndex > 0) {
                this.historyIndex--;
            } else if (this.historyIndex === 0) {
                this.historyIndex = -1;
                this.input.value = '';
                return;
            }
        }
        
        if (this.historyIndex >= 0) {
            this.input.value = this.commandHistory[this.commandHistory.length - 1 - this.historyIndex];
        }
    }

    handleTabCompletion() {
        const currentInput = this.input.value;
        const commands = ['help', 'clear', 'errors', 'debug', 'status', 'export', 'api', 'health', 'update', 'system', 'refresh'];
        
        const matches = commands.filter(cmd => cmd.startsWith(currentInput.toLowerCase()));
        
        if (matches.length === 1) {
            this.input.value = matches[0];
            this.addLog('info', `Tab completed: ${matches[0]}`);
        } else if (matches.length > 1) {
            this.addLog('info', `Available completions: ${matches.join(', ')}`);
        } else {
            this.addLog('warn', 'No matching commands found');
        }
    }
    
    setupKeyboardShortcuts() {
        const handleKeydown = (e) => {
            try {
                // Ctrl+` to toggle terminal
                if (e.ctrlKey && e.key === '`') {
                    e.preventDefault();
                    this.toggle();
                    this.addLog('info', `Terminal ${this.isVisible ? 'opened' : 'closed'} via keyboard shortcut`);
                }
                
                // Ctrl+Shift+C to clear terminal when visible
                if (e.ctrlKey && e.shiftKey && e.key === 'C' && this.isVisible) {
                    e.preventDefault();
                    this.clearTerminal();
                    this.addLog('info', 'Terminal cleared via keyboard shortcut');
                }
                
                // Ctrl+Shift+R to refresh status when visible
                if (e.ctrlKey && e.shiftKey && e.key === 'R' && this.isVisible) {
                    e.preventDefault();
                    this.refreshStatus();
                }
                
                // Escape to hide terminal when visible
                if (e.key === 'Escape' && this.isVisible) {
                    e.preventDefault();
                    this.hide();
                    this.addLog('info', 'Terminal closed via Escape key');
                }
            } catch (error) {
                console.error('Error in terminal keyboard shortcut handler:', error);
                this.addLog('error', `Keyboard shortcut error: ${error.message}`);
            }
        };

        // Use eventManager if available, otherwise fall back to direct listeners
        if (window.eventManager && window.eventManager.add) {
            if (window.eventManager.debounce) {
                window.eventManager.add(document, 'keydown', window.eventManager.debounce(handleKeydown, 100));
            } else {
                window.eventManager.add(document, 'keydown', handleKeydown);
            }
            
            this.cleanupFunctions.push(() => {
                if (window.eventManager.remove) {
                    window.eventManager.remove(document, 'keydown', handleKeydown);
                }
            });
        } else {
            document.addEventListener('keydown', handleKeydown);
            this.cleanupFunctions.push(() => {
                document.removeEventListener('keydown', handleKeydown);
            });
        }
    }
    
    startHeartbeat() {
        // Check connection status every 30 seconds
        setInterval(() => {
            this.checkConnectionStatus();
        }, 30000);
        
        // Initial check
        this.checkConnectionStatus();
    }
    
    async checkConnectionStatus() {
        try {
            const response = await fetch('/api/health', { 
                method: 'GET',
                timeout: 5000 
            });
            
            if (response.ok) {
                this.connectionStatus = 'connected';
                this.lastHeartbeat = Date.now();
            } else {
                this.connectionStatus = 'disconnected';
            }
        } catch (error) {
            this.connectionStatus = 'disconnected';
            console.error('Connection check failed:', error);
        }
        
        this.updateConnectionStatus();
    }
    
    updateConnectionStatus() {
        const statusIndicator = document.getElementById('terminal-connection-status');
        const statusText = document.getElementById('terminal-status-text');
        
        if (statusIndicator && statusText) {
            statusIndicator.className = `status-indicator ${this.connectionStatus}`;
            
            switch (this.connectionStatus) {
                case 'connected':
                    statusText.textContent = 'Connected';
                    break;
                case 'disconnected':
                    statusText.textContent = 'Disconnected';
                    break;
                case 'connecting':
                    statusText.textContent = 'Connecting...';
                    break;
            }
        }
    }
    
    interceptConsoleLogs() {
        const originalLog = console.log;
        const originalError = console.error;
        const originalWarn = console.warn;
        const originalInfo = console.info;
        
        console.log = (...args) => {
            originalLog.apply(console, args);
            this.addLog('log', args.join(' '));
        };
        
        console.error = (...args) => {
            originalError.apply(console, args);
            this.addLog('error', args.join(' '));
            if (window.notificationManager) {
                window.notificationManager.showError('An error occurred. Check the terminal for details.');
            }
        };
        
        console.warn = (...args) => {
            originalWarn.apply(console, args);
            this.addLog('warn', args.join(' '));
        };
        
        console.info = (...args) => {
            originalInfo.apply(console, args);
            this.addLog('info', args.join(' '));
        };
    }
    
    connectToErrorManager() {
        // Listen for errors from error manager
        const originalLogError = window.vybeErrorManager.logError;
        window.vybeErrorManager.logError = function(errorData) {
            originalLogError.call(this, errorData);
            
            if (window.vybeTerminal) {
                window.vybeTerminal.addLog('error', `[${errorData.type}] ${errorData.message}`);
            }
        };
    }
    
    addLog(level, message) {
        const timestamp = new Date().toLocaleTimeString();
        const logEntry = {
            timestamp,
            level,
            message
        };
        
        this.logs.push(logEntry);
        
        // Limit log storage
        if (this.logs.length > this.maxLogs) {
            this.logs.shift();
        }
        
        // Display in terminal if visible
        if (this.output) {
            const logElement = document.createElement('div');
            logElement.className = `terminal-log ${level}`;
            logElement.innerHTML = `<span class="terminal-timestamp">[${timestamp}]</span> ${message}`;
            
            this.output.appendChild(logElement);
            
            // Auto-scroll to bottom
            this.output.scrollTop = this.output.scrollHeight;
        }
    }
    
    async processCommand(command) {
        if (!command.trim()) return;
        
        // Add to command history
        this.commandHistory.push(command);
        if (this.commandHistory.length > 50) {
            this.commandHistory.shift();
        }
        
        this.addLog('command', `> ${command}`);
        this.setProcessing(true);
        
        try {
            // Simple command processing
            const parts = command.trim().split(' ');
            const cmd = parts[0].toLowerCase();
            const args = parts.slice(1);
            
            switch (cmd) {
                case 'help':
                    this.showHelp();
                    break;
                    
                case 'clear':
                    this.clearTerminal();
                    break;
                    
                case 'errors':
                    await this.showErrors();
                    break;
                    
                case 'debug':
                    this.toggleDebugMode();
                    break;
                    
                case 'status':
                    await this.showStatus();
                    break;
                    
                case 'export':
                    this.exportLogs();
                    break;
                    
                case 'api':
                    await this.testApiEndpoint(args[0]);
                    break;
                    
                case 'health':
                    await this.checkHealth();
                    break;
                    
                case 'update':
                    await this.checkForUpdates();
                    break;
                    
                case 'system':
                    await this.showSystemInfo();
                    break;
                    
                case 'refresh':
                    await this.refreshStatus();
                    break;
                    
                default:
                    this.addLog('warn', `Unknown command: ${cmd}. Type 'help' for available commands.`);
            }
        } catch (error) {
            this.addLog('error', `Command execution failed: ${error.message}`);
        } finally {
            this.setProcessing(false);
        }
    }
    
    setProcessing(processing) {
        this.isProcessing = processing;
        const indicator = document.getElementById('terminal-processing');
        if (indicator) {
            indicator.classList.toggle('hidden', !processing);
        }
        if (this.input) {
            this.input.disabled = processing;
        }
    }
    
    showHelp() {
        const helpText = `
Available Commands:
  help     - Show this help message
  clear    - Clear terminal output
  errors   - Show recent errors
  debug    - Toggle debug mode
  status   - Show system status
  export   - Export logs to file
  api <endpoint> - Test API endpoint
  health   - Check system health
  update   - Check for updates
  system   - Show system information
  refresh  - Refresh all status information
        `;
        this.addLog('info', helpText);
    }
    
    async showErrors() {
        if (window.vybeErrorManager) {
            const summary = window.vybeErrorManager.getErrorSummary();
            this.addLog('info', `Total errors: ${summary.totalErrors}`);
            this.addLog('info', `Error types: ${JSON.stringify(summary.errorTypes, null, 2)}`);
            
            if (summary.recentErrors.length > 0) {
                this.addLog('info', 'Recent errors:');
                summary.recentErrors.forEach(error => {
                    this.addLog('error', `[${error.type}] ${error.message}`);
                });
            }
        } else {
            this.addLog('warn', 'Error manager not available');
        }
    }
    
    toggleDebugMode() {
        if (window.vybeDebug) {
            const debugMode = window.vybeDebug.toggleDebug();
            this.addLog('info', `Debug mode: ${debugMode ? 'ON' : 'OFF'}`);
        } else {
            this.addLog('warn', 'Debug tools not available');
        }
    }
    
    async showStatus() {
        try {
            const response = await fetch('/api/status');
            const data = await response.json();
            
            const status = {
                terminal: 'Active',
                connection: this.connectionStatus,
                api: data.status || 'Unknown',
                errorManager: window.vybeErrorManager ? 'Connected' : 'Unavailable',
                debugTools: window.vybeDebug ? 'Available' : 'Unavailable',
                logs: this.logs.length,
                visible: this.isVisible,
                lastHeartbeat: this.lastHeartbeat ? new Date(this.lastHeartbeat).toLocaleTimeString() : 'Never'
            };
            
            this.addLog('info', `System Status:\n${JSON.stringify(status, null, 2)}`);
        } catch (error) {
            this.addLog('error', `Failed to get system status: ${error.message}`);
        }
    }
    
    async testApiEndpoint(endpoint) {
        if (!endpoint) {
            this.addLog('warn', 'Usage: api <endpoint>');
            return;
        }
        
        try {
            this.addLog('info', `Testing API endpoint: ${endpoint}`);
            const response = await fetch(endpoint);
            const data = await response.json();
            
            this.addLog('success', `Response [${response.status}]: ${JSON.stringify(data, null, 2)}`);
        } catch (error) {
            this.addLog('error', `API test failed: ${error.message}`);
        }
    }
    
    async checkHealth() {
        try {
            this.addLog('info', 'Checking system health...');
            const response = await fetch('/api/health');
            const data = await response.json();
            
            this.addLog('success', `Health check: ${JSON.stringify(data, null, 2)}`);
        } catch (error) {
            this.addLog('error', `Health check failed: ${error.message}`);
        }
    }
    
    async checkForUpdates() {
        try {
            this.addLog('info', 'Checking for updates...');
            const response = await fetch('/api/check-updates');
            const data = await response.json();
            
            if (data.success) {
                if (data.update_available) {
                    this.addLog('success', `Update available: ${data.update_info.version}`);
                    this.addLog('info', `Current: ${data.update_info.current_version} → Latest: ${data.update_info.version}`);
                } else {
                    this.addLog('info', 'No updates available');
                }
            } else {
                this.addLog('error', `Update check failed: ${data.error}`);
            }
        } catch (error) {
            this.addLog('error', `Update check failed: ${error.message}`);
        }
    }
    
    async showSystemInfo() {
        try {
            const systemInfo = {
                userAgent: navigator.userAgent,
                platform: navigator.platform,
                language: navigator.language,
                cookieEnabled: navigator.cookieEnabled,
                onLine: navigator.onLine,
                url: window.location.href,
                timestamp: new Date().toISOString()
            };
            
            this.addLog('info', `System Information:\n${JSON.stringify(systemInfo, null, 2)}`);
        } catch (error) {
            this.addLog('error', `Failed to get system info: ${error.message}`);
        }
    }
    
    async refreshStatus() {
        this.addLog('info', 'Refreshing status...');
        await this.checkConnectionStatus();
        await this.showStatus();
        this.addLog('success', 'Status refresh completed');
    }
    
    clearTerminal() {
        if (this.output) {
            this.output.innerHTML = '';
        }
        this.addLog('info', 'Terminal cleared');
    }
    
    exportLogs() {
        const exportData = {
            timestamp: new Date().toISOString(),
            logs: this.logs,
            userAgent: navigator.userAgent,
            url: window.location.href,
            connectionStatus: this.connectionStatus,
            lastHeartbeat: this.lastHeartbeat
        };
        
        const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `vybe_terminal_logs_${Date.now()}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        
        this.addLog('success', 'Logs exported successfully');
    }
    
    makeDraggable() {
        const header = this.terminal.querySelector('.terminal-header');
        if (!header) {
            console.warn('Terminal header not found, cannot make draggable');
            return;
        }

        let isDragging = false;
        let currentX;
        let currentY;
        let initialX;
        let initialY;
        let xOffset = 0;
        let yOffset = 0;
        
        const handleMouseDown = (e) => {
            try {
                // Only start dragging if clicking on header or its children (not buttons)
                if (e.target.closest('.terminal-controls')) {
                    return; // Don't drag when clicking control buttons
                }

                initialX = e.clientX - xOffset;
                initialY = e.clientY - yOffset;
                
                if (e.target === header || header.contains(e.target)) {
                    isDragging = true;
                    this.addLog('debug', 'Started dragging terminal');
                }
            } catch (error) {
                console.error('Error in mousedown handler:', error);
            }
        };

        const handleMouseMove = (e) => {
            try {
                if (isDragging) {
                    e.preventDefault();
                    currentX = e.clientX - initialX;
                    currentY = e.clientY - initialY;
                    
                    xOffset = currentX;
                    yOffset = currentY;
                    
                    // Constrain to viewport
                    const maxX = window.innerWidth - this.terminal.offsetWidth;
                    const maxY = window.innerHeight - this.terminal.offsetHeight;
                    
                    currentX = Math.max(0, Math.min(currentX, maxX));
                    currentY = Math.max(0, Math.min(currentY, maxY));
                    
                    this.terminal.style.transform = `translate(${currentX}px, ${currentY}px)`;
                }
            } catch (error) {
                console.error('Error in mousemove handler:', error);
            }
        };

        const handleMouseUp = () => {
            try {
                if (isDragging) {
                    isDragging = false;
                    this.addLog('debug', 'Stopped dragging terminal');
                }
            } catch (error) {
                console.error('Error in mouseup handler:', error);
            }
        };

        // Use eventManager if available, otherwise fall back to direct listeners
        if (window.eventManager && window.eventManager.add) {
            window.eventManager.add(header, 'mousedown', handleMouseDown);
            
            if (window.eventManager.debounce) {
                window.eventManager.add(document, 'mousemove', window.eventManager.debounce(handleMouseMove, 16)); // ~60fps
            } else {
                window.eventManager.add(document, 'mousemove', handleMouseMove);
            }
            
            window.eventManager.add(document, 'mouseup', handleMouseUp);
            
            // Store cleanup functions
            this.cleanupFunctions.push(() => {
                if (window.eventManager.remove) {
                    window.eventManager.remove(header, 'mousedown', handleMouseDown);
                    window.eventManager.remove(document, 'mousemove', handleMouseMove);
                    window.eventManager.remove(document, 'mouseup', handleMouseUp);
                }
            });
        } else {
            header.addEventListener('mousedown', handleMouseDown);
            document.addEventListener('mousemove', handleMouseMove);
            document.addEventListener('mouseup', handleMouseUp);
            
            // Store cleanup functions
            this.cleanupFunctions.push(() => {
                header.removeEventListener('mousedown', handleMouseDown);
                document.removeEventListener('mousemove', handleMouseMove);
                document.removeEventListener('mouseup', handleMouseUp);
            });
        }
    }
    
    toggle() {
        if (this.isVisible) {
            this.hide();
        } else {
            this.show();
        }
    }
    
    show() {
        this.isVisible = true;
        this.terminal.classList.remove('hidden');
        this.terminal.classList.add('visible');
        localStorage.setItem('vybeTerminalVisible', 'true');
        this.addLog('info', 'Terminal opened');
        this.input.focus();
    }
    
    hide() {
        this.isVisible = false;
        this.terminal.classList.remove('visible');
        this.terminal.classList.add('hidden');
        localStorage.setItem('vybeTerminalVisible', 'false');
    }
    
    toggleMinimize() {
        this.terminal.classList.toggle('minimized');
    }
}

// Enhanced initialization with robust error handling
(function() {
    'use strict';
    


    // Initialize terminal when DOM is ready
    function initializeTerminal() {
        try {
            // Check if terminal is already initialized
            if (window.vybeTerminal) {
                console.log('[Terminal] Already initialized, skipping...');
                return;
            }

            // Check if we should initialize the terminal
            const shouldInit = document.querySelector('.vybe-terminal-trigger') || 
                             document.querySelector('[data-terminal="true"]') ||
                             localStorage.getItem('vybeTerminalAutoStart') === 'true' ||
                             true; // Always initialize for debugging purposes

            if (shouldInit) {
                console.log('[Terminal] Initializing Vybe Terminal...');
                window.vybeTerminal = new VybeTerminal();
                
                // Add global convenience methods
                window.openTerminal = () => window.vybeTerminal.show();
                window.closeTerminal = () => window.vybeTerminal.hide();
                window.toggleTerminal = () => window.vybeTerminal.toggle();
                window.clearTerminal = () => window.vybeTerminal.clearTerminal();
                
                console.log('[Terminal] Vybe Terminal initialized successfully');
                
                // Log initial welcome message
                if (window.vybeTerminal) {
                    setTimeout(() => {
                        window.vybeTerminal.addLog('info', 'Vybe Debug Terminal initialized. Type "help" for commands.');
                        window.vybeTerminal.addLog('info', 'Use Ctrl+` to toggle terminal visibility.');
                    }, 100);
                }
            } else {
                console.log('[Terminal] Terminal initialization skipped - no trigger found');
            }
        } catch (error) {
            console.error('[Terminal] Failed to initialize Vybe Terminal:', error);
            if (window.notificationManager) {
                window.notificationManager.showError('Failed to initialize debug terminal');
            }
        }
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        // Use eventManager if available, otherwise fall back to DOMContentLoaded
        if (window.eventManager && window.eventManager.add) {
            window.eventManager.add(document, 'DOMContentLoaded', initializeTerminal);
        } else {
            document.addEventListener('DOMContentLoaded', initializeTerminal);
        }
    } else {
        // DOM is already ready
        initializeTerminal();
    }

    // Also initialize on window load as a fallback
    if (window.eventManager && window.eventManager.add) {
        window.eventManager.add(window, 'load', () => {
            if (!window.vybeTerminal) {
                initializeTerminal();
            }
        });
    } else {
        window.addEventListener('load', () => {
            if (!window.vybeTerminal) {
                initializeTerminal();
            }
        });
    }
})();
