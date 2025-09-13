/**
 * Module Health Check
 * Verifies all modules are loading correctly
 */

console.log('🔍 Starting Module Health Check...');

// Wait for modules to load
setTimeout(() => {
    console.log('\n📋 Module Loading Test:');
    
    const modules = [
        { name: 'ApiUtils', check: () => window.ApiUtils },
        { name: 'DeviceInfo', check: () => window.DeviceInfo },
        { name: 'ThemeManager', check: () => window.ThemeManager },
        { name: 'ChatController', check: () => window.chatController },
        { name: 'ModelManager', check: () => window.ModelManager },
        { name: 'ChatSettingsPanelManager', check: () => window.ChatSettingsPanelManager },
        { name: 'MobileDebugger', check: () => window.MobileDebugger },
        { name: 'ChatManager (via chatController)', check: () => window.chatController?.managers?.chat },
        { name: 'ModuleLoader', check: () => window.ModuleLoader }
    ];
    
    modules.forEach(module => {
        const exists = module.check();
        const status = exists ? '✅' : '❌';
        console.log(`${status} ${module.name} ${exists ? 'loaded' : 'not found'}`);
    });
    
    console.log('\n🔧 Import Test:');
    
    // Test ES6 module imports
    Promise.all([
        import('./utils/device-detector.js').then(() => '✅ DeviceDetector import').catch(() => '❌ DeviceDetector import failed'),
        import('./utils/mobile-debugger.js').then(() => '✅ MobileDebugger import').catch(() => '❌ MobileDebugger import failed'),
        import('./utils/api-utils.js').then(() => '✅ ApiUtils import').catch(() => '❌ ApiUtils import failed'),
        import('./modules/theme-manager.js').then(() => '✅ ThemeManager import').catch(() => '❌ ThemeManager import failed'),
        import('./modules/chat-manager.js').then(() => '✅ ChatManager import').catch(() => '❌ ChatManager import failed'),
        import('./modules/model-manager.js').then(() => '✅ ModelManager import').catch(() => '❌ ModelManager import failed'),
        import('./modules/chat-settings-panel-manager.js').then(() => '✅ ChatSettingsPanelManager import').catch(() => '❌ ChatSettingsPanelManager import failed')
    ]).then(results => {
        results.forEach(result => console.log(result));
        
        // Log device info if available
        if (window.DeviceInfo) {
            console.log('\n📱 Device Information:');
            const info = window.DeviceInfo.getInfo();
            console.log(`Device: ${info.device.type} (${info.viewport.width}×${info.viewport.height})`);
            console.log(`Browser: ${info.browser.name} ${info.browser.version}`);
            console.log(`OS: ${info.os.name}`);
            console.log(`Mobile optimizations: ${info.isMobile ? 'enabled' : 'disabled'}`);
            
            if (info.isMobile) {
                console.log('💡 Mobile debugging available: run enableMobileDebug() in console');
            }
        }
        
        console.log('\n✨ Module Health Check Complete!');
    });
    
}, 1000);
