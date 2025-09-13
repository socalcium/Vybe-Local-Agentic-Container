/**
 * Device Detection Utility
 * Detects browser type, device type, and viewport information
 */

class DeviceDetector {
    constructor() {
        this.userAgent = navigator.userAgent;
        this.platform = navigator.platform;
        this.vendor = navigator.vendor;
        
        // Cleanup functions for event listeners
        this.cleanupFunctions = [];
        
        this.detectAll();
        this.initViewportHandling();
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


    detectAll() {
        this.browser = this.detectBrowser();
        this.device = this.detectDevice();
        this.os = this.detectOS();
        this.isMobile = this.device.type === 'mobile' || this.device.type === 'tablet';
        this.isTablet = this.device.type === 'tablet';
        this.isDesktop = this.device.type === 'desktop';
        this.viewport = this.getViewportInfo();
    }

    detectBrowser() {
        const ua = this.userAgent;
        
        if (ua.includes('Firefox')) {
            return { name: 'Firefox', version: this.extractVersion('Firefox/') };
        }
        if (ua.includes('SamsungBrowser')) {
            return { name: 'Samsung Internet', version: this.extractVersion('SamsungBrowser/') };
        }
        if (ua.includes('Opera') || ua.includes('OPR')) {
            return { name: 'Opera', version: this.extractVersion('OPR/') || this.extractVersion('Opera/') };
        }
        if (ua.includes('Edge')) {
            return { name: 'Edge', version: this.extractVersion('Edge/') };
        }
        if (ua.includes('Chrome') && !ua.includes('Chromium')) {
            return { name: 'Chrome', version: this.extractVersion('Chrome/') };
        }
        if (ua.includes('Safari') && !ua.includes('Chrome') && !ua.includes('Chromium')) {
            return { name: 'Safari', version: this.extractVersion('Version/') };
        }
        if (ua.includes('Chromium')) {
            return { name: 'Chromium', version: this.extractVersion('Chromium/') };
        }
        
        return { name: 'Unknown', version: 'Unknown' };
    }

    detectDevice() {
        const ua = this.userAgent;
        const width = window.innerWidth;
        
        // Mobile detection
        if (/Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(ua)) {
            if (/iPad/i.test(ua) || (width >= 768 && /iPhone/i.test(ua))) {
                return { type: 'tablet', class: 'tablet' };
            }
            return { type: 'mobile', class: 'mobile' };
        }
        
        // Tablet detection by screen size
        if (width >= 768 && width <= 1024) {
            return { type: 'tablet', class: 'tablet' };
        }
        
        // Mobile by screen size
        if (width < 768) {
            return { type: 'mobile', class: 'mobile' };
        }
        
        return { type: 'desktop', class: 'desktop' };
    }

    detectOS() {
        const ua = this.userAgent;
        const platform = this.platform;
        
        if (/iPhone|iPad|iPod/i.test(ua)) {
            return { name: 'iOS', version: this.extractVersion('OS ') };
        }
        if (/Android/i.test(ua)) {
            return { name: 'Android', version: this.extractVersion('Android ') };
        }
        if (/Windows/i.test(ua)) {
            return { name: 'Windows', version: 'Unknown' };
        }
        if (/Mac/i.test(platform)) {
            return { name: 'macOS', version: 'Unknown' };
        }
        if (/Linux/i.test(platform)) {
            return { name: 'Linux', version: 'Unknown' };
        }
        
        return { name: 'Unknown', version: 'Unknown' };
    }

    extractVersion(pattern) {
        const match = this.userAgent.match(new RegExp(pattern + '([\\d\\.]+)'));
        return match ? match[1] : 'Unknown';
    }

    getViewportInfo() {
        return {
            width: window.innerWidth,
            height: window.innerHeight,
            devicePixelRatio: window.devicePixelRatio || 1,
            orientation: this.getOrientation()
        };
    }

    getOrientation() {
        if (screen.orientation) {
            return screen.orientation.angle === 0 || screen.orientation.angle === 180 ? 'portrait' : 'landscape';
        }
        return window.innerHeight > window.innerWidth ? 'portrait' : 'landscape';
    }

    initViewportHandling() {
        // Handle viewport changes
        const resizeHandler = window.eventManager.debounce(() => {
            this.viewport = this.getViewportInfo();
            this.handleViewportChange();
        }, 100);
        
        window.eventManager.add(window, 'resize', resizeHandler);

        // Handle orientation changes
        const orientationHandler = () => {
            setTimeout(() => {
                this.viewport = this.getViewportInfo();
                this.handleOrientationChange();
            }, 100);
        };
        
        window.eventManager.add(window, 'orientationchange', orientationHandler);

        // Handle iOS Safari specific issues
        if (this.isIOSSafari()) {
            this.handleIOSSafariViewport();
        }
    }

    isIOSSafari() {
        return this.os.name === 'iOS' && this.browser.name === 'Safari';
    }

    isIOSChrome() {
        return this.os.name === 'iOS' && this.browser.name === 'Chrome';
    }

    isAndroidChrome() {
        return this.os.name === 'Android' && this.browser.name === 'Chrome';
    }

    handleIOSSafariViewport() {
        // Handle iOS Safari bottom bar
        const updateViewportHeight = () => {
            const vh = window.innerHeight * 0.01;
            document.documentElement.style.setProperty('--vh', `${vh}px`);
            
            // Handle keyboard appearance on iOS
            const isKeyboardOpen = window.innerHeight < window.screen.height * 0.75;
            document.documentElement.classList.toggle('keyboard-open', isKeyboardOpen);
        };

        updateViewportHeight();
        
        const resizeHandler = window.eventManager.debounce(updateViewportHeight, 100);
        window.eventManager.add(window, 'resize', resizeHandler);
        
        const orientationHandler = () => {
            setTimeout(updateViewportHeight, 100);
        };
        window.eventManager.add(window, 'orientationchange', orientationHandler);
    }

    handleViewportChange() {
        // Update device type if viewport changed significantly
        const newDevice = this.detectDevice();
        if (newDevice.type !== this.device.type) {
            this.device = newDevice;
            this.updateBodyClasses();
        }
        
        // Dispatch custom event
        window.dispatchEvent(new CustomEvent('viewportChange', {
            detail: { viewport: this.viewport, device: this.device }
        }));
    }

    handleOrientationChange() {
        // Dispatch custom event
        window.dispatchEvent(new CustomEvent('orientationChange', {
            detail: { viewport: this.viewport, orientation: this.viewport.orientation }
        }));
    }

    updateBodyClasses() {
        const body = document.body;
        
        // Remove old classes
        body.classList.remove('device-mobile', 'device-tablet', 'device-desktop');
        body.classList.remove('browser-chrome', 'browser-safari', 'browser-firefox', 'browser-edge');
        body.classList.remove('os-ios', 'os-android', 'os-windows', 'os-macos', 'os-linux');
        
        // Add device class
        body.classList.add(`device-${this.device.type}`);
        
        // Add browser class
        body.classList.add(`browser-${this.browser.name.toLowerCase().replace(/\s+/g, '')}`);
        
        // Add OS class
        body.classList.add(`os-${this.os.name.toLowerCase()}`);
        
        // Add mobile/desktop convenience classes
        body.classList.toggle('is-mobile', this.isMobile);
        body.classList.toggle('is-tablet', this.isTablet);
        body.classList.toggle('is-desktop', this.isDesktop);
        
        // Add iOS Safari specific class
        body.classList.toggle('ios-safari', this.isIOSSafari());
        body.classList.toggle('ios-chrome', this.isIOSChrome());
        body.classList.toggle('android-chrome', this.isAndroidChrome());
    }

    getInfo() {
        return {
            browser: this.browser,
            device: this.device,
            os: this.os,
            viewport: this.viewport,
            isMobile: this.isMobile,
            isTablet: this.isTablet,
            isDesktop: this.isDesktop,
            isIOSSafari: this.isIOSSafari(),
            isIOSChrome: this.isIOSChrome(),
            isAndroidChrome: this.isAndroidChrome()
        };
    }
}

// Initialize device detector
const DeviceInfo = new DeviceDetector();

// Apply initial classes
DeviceInfo.updateBodyClasses();

// Log device info for debugging
console.log('📱 Device Detection:', DeviceInfo.getInfo());

// Export for use in other modules
window.DeviceInfo = DeviceInfo;

export default DeviceInfo;
