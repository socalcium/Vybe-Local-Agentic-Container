/**
 * COMPLETELY REWRITTEN MAIN.JS - NO SPLASH SCREEN
 * Direct redirect to Flask backend without any splash logic
 */

let checkAttempts = 0;
const MAX_ATTEMPTS = 30; // 30 seconds timeout

async function checkFlaskStatus() {
    try {
        // Try multiple endpoints in order of preference  
        const endpoints = [
            'http://localhost:8000/health',     // Fastest health check
            'http://localhost:8000/api/health', // API health check
            'http://localhost:8000/'            // Main page
        ];
        
        for (const endpoint of endpoints) {
            try {
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), 2000); // 2 second timeout
                
                const response = await fetch(endpoint, { 
                    method: 'GET',
                    signal: controller.signal,
                    cache: 'no-store'
                });
                
                clearTimeout(timeoutId);
                
                if (response.ok) {
                    console.log(`Backend ready at ${endpoint}!`);
                    // IMMEDIATE redirect - no splash, no delay
                    window.location.href = 'http://localhost:8000';
                    return true;
                }
            } catch (endpointError) {
                if (endpointError.name === 'AbortError') {
                    console.log(`${endpoint} timeout`);
                } else {
                    console.log(`${endpoint} not ready:`, endpointError.message);
                }
            }
        }
    } catch {
        console.log('Backend not ready, attempt:', checkAttempts + 1);
    }
    return false;
}

function updateStatus(message) {
    const statusElement = document.getElementById('status-message');
    if (statusElement) {
        statusElement.textContent = message;
    }
    console.log('Status:', message);
}

function showBackendError() {
    const statusElement = document.getElementById('status-message');
    if (statusElement) {
        statusElement.innerHTML = `
            <div style="text-align: left; margin-top: 10px;">
                <strong>⚠️ Backend Startup Failed</strong><br>
                <small style="color: #888;">
                To start manually:<br>
                1. Open terminal in Vybe directory<br>
                2. Run: <code>python run.py</code><br>
                3. Or double-click: <code>launch_vybe.bat</code><br><br>
                <button onclick="window.location.reload()">Retry</button>
                </small>
            </div>
        `;
    }
}

function startHealthCheck() {
    console.log('Starting immediate health check - no splash delay');
    
    const interval = setInterval(async () => {
        checkAttempts++;
        updateStatus(`Connecting to AI backend... (${checkAttempts}/${MAX_ATTEMPTS})`);
        
        if (await checkFlaskStatus()) {
            clearInterval(interval);
        } else if (checkAttempts >= MAX_ATTEMPTS) {
            clearInterval(interval);
            updateStatus('Backend startup timeout');
            showBackendError();
        }
    }, 1000);
    
    console.log('Health check started - waiting for Flask backend...');
}

// Start health check when DOM is ready
window.addEventListener('DOMContentLoaded', async () => {
    console.log('DOM loaded, starting immediate backend check...');
    
    updateStatus('Connecting to AI backend...');
    
    // Try immediate connection first
    if (!(await checkFlaskStatus())) {
        // If not ready, start polling
        startHealthCheck();
    }
});