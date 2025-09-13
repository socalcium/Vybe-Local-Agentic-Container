/**
 * Mobile Debug Utility
 * Helps debug mobile device issues by showing device info and viewport details
 */

class MobileDebugger {
    constructor() {
        this.isEnabled = localStorage.getItem('mobile-debug') === 'true';
        this.debugPanel = null;
        
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
        if (!this.isEnabled) return;
        
        this.createDebugPanel();
        this.setupEventListeners();
        this.updateInfo();
    }

    enable() {
        localStorage.setItem('mobile-debug', 'true');
        this.isEnabled = true;
        this.init();
    }

    disable() {
        localStorage.setItem('mobile-debug', 'false');
        this.isEnabled = false;
        if (this.debugPanel) {
            this.debugPanel.remove();
            this.debugPanel = null;
        }
    }

    createDebugPanel() {
        this.debugPanel = document.createElement('div');
        this.debugPanel.id = 'mobile-debug-panel';
        this.debugPanel.style.cssText = `
            position: fixed;
            top: 10px;
            left: 10px;
            background: rgba(0, 0, 0, 0.9);
            color: white;
            padding: 10px;
            border-radius: 8px;
            font-family: monospace;
            font-size: 12px;
            z-index: 9999;
            max-width: 300px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
            backdrop-filter: blur(10px);
        `;
        
        document.body.appendChild(this.debugPanel);
    }

    updateInfo() {
        if (!this.debugPanel || !window.DeviceInfo) return;

        const info = window.DeviceInfo.getInfo();
        const viewport = info.viewport;
        
        const html = `
            <div style="margin-bottom: 8px; font-weight: bold; color: #4f8cff;">📱 Device Debug</div>
            <div><strong>Device:</strong> ${info.device.type}</div>
            <div><strong>Browser:</strong> ${info.browser.name} ${info.browser.version}</div>
            <div><strong>OS:</strong> ${info.os.name} ${info.os.version}</div>
            <div><strong>Viewport:</strong> ${viewport.width}×${viewport.height}</div>
            <div><strong>DPR:</strong> ${viewport.devicePixelRatio}</div>
            <div><strong>Orientation:</strong> ${viewport.orientation}</div>
            <div><strong>--vh:</strong> ${document.documentElement.style.getPropertyValue('--vh')}</div>
            <div style="margin-top: 8px; font-size: 10px; opacity: 0.7;">
                ${info.isIOSSafari ? '🍎 iOS Safari' : ''}
                ${info.isIOSChrome ? '🍎 iOS Chrome' : ''}
                ${info.isAndroidChrome ? '🤖 Android Chrome' : ''}
            </div>
            <div style="margin-top: 8px; cursor: pointer; color: #ff6b6b;" onclick="window.MobileDebugger.disable()">
                ❌ Close Debug
            </div>
        `;
        
        this.debugPanel.innerHTML = html;
    }

    setupEventListeners() {
        const resizeHandler = window.eventManager.debounce(() => {
            this.updateInfo();
        }, 100);
        
        window.eventManager.add(window, 'resize', resizeHandler);
        
        const orientationHandler = () => {
            setTimeout(() => {
                this.updateInfo();
            }, 100);
        };
        
        window.eventManager.add(window, 'orientationchange', orientationHandler);
        
        if (window.DeviceInfo) {
            window.eventManager.add(window, 'viewportChange', () => {
                this.updateInfo();
            });
            
            window.eventManager.add(window, 'orientationChange', () => {
                this.updateInfo();
            });
        }
    }

    logViewportInfo() {
        if (!window.DeviceInfo) {
            console.log('DeviceInfo not available');
            return;
        }

        const info = window.DeviceInfo.getInfo();
        console.group('📱 Mobile Debug Info');
        console.log('Device Type:', info.device.type);
        console.log('Browser:', `${info.browser.name} ${info.browser.version}`);
        console.log('OS:', `${info.os.name} ${info.os.version}`);
        console.log('Viewport:', `${info.viewport.width}×${info.viewport.height}`);
        console.log('Device Pixel Ratio:', info.viewport.devicePixelRatio);
        console.log('Orientation:', info.viewport.orientation);
        console.log('CSS --vh:', document.documentElement.style.getPropertyValue('--vh'));
        console.log('Is Mobile:', info.isMobile);
        console.log('Is iOS Safari:', info.isIOSSafari);
        console.log('Is iOS Chrome:', info.isIOSChrome);
        console.log('Is Android Chrome:', info.isAndroidChrome);
        console.groupEnd();
    }
}

// Initialize and expose globally
const mobileDebugger = new MobileDebugger();
window.MobileDebugger = mobileDebugger;

// Console commands for easy debugging
window.enableMobileDebug = () => mobileDebugger.enable();
window.disableMobileDebug = () => mobileDebugger.disable();
window.logMobileInfo = () => mobileDebugger.logViewportInfo();

// Auto-enable on mobile devices in development
if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    if (window.DeviceInfo?.isMobile && !localStorage.getItem('mobile-debug')) {
        console.log('🔧 Mobile device detected in development. Enable debug with: enableMobileDebug()');
    }
}

export default mobileDebugger;
