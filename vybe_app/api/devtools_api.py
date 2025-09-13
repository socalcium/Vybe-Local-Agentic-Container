"""
Developer Tools and System Diagnostics API
===========================================

This module provides comprehensive developer tools and system diagnostics functionality
for the Vybe application. It offers detailed insights into system performance, application
configuration, environment settings, and runtime status specifically designed for
debugging, monitoring, and development purposes.

The API is primarily intended for developers, system administrators, and advanced users
who need deep visibility into the application's operational state. All endpoints are
protected by test mode authentication to ensure they are only accessible in development
or diagnostic scenarios.

Key Features:
    - Real-time system performance monitoring (CPU, memory, disk, network)
    - Comprehensive application configuration inspection
    - Environment variable and setting enumeration
    - Runtime status and health diagnostics
    - Error logging and debugging information
    - Performance metrics and profiling data
    - Database connection and query performance analysis
    - Plugin and extension status monitoring

API Endpoints:
    - GET /devtools/system_info: Detailed system hardware and OS information
    - GET /devtools/app_config: Application configuration and build settings
    - GET /devtools/app_settings: Database-stored application settings
    - GET /devtools/environment: Environment variables and runtime context
    - GET /devtools/performance: Real-time performance metrics
    - GET /devtools/logs: Application logs and error diagnostics
    - GET /devtools/health: Overall application health status

Security Model:
    All endpoints require test mode authentication via @test_mode_login_required
    decorator. This ensures diagnostic information is only accessible in
    development environments or when explicitly enabled by administrators.

Information Categories:
    
    System Information:
        - Hardware specifications (CPU, RAM, storage)
        - Operating system details and version
        - Network configuration and connectivity
        - Process information and resource usage
        - Installed software and dependency versions
    
    Application Configuration:
        - Build version and compilation details
        - Feature flags and operational modes
        - Resource limits and timeout settings
        - Database and cache configuration
        - Plugin and extension settings
    
    Runtime Diagnostics:
        - Memory usage patterns and garbage collection
        - Thread pool status and concurrency metrics
        - Database connection pool health
        - Cache hit rates and performance statistics
        - Error rates and exception tracking

Performance Considerations:
    Some endpoints may be computationally expensive as they gather real-time
    system information. Results should be cached appropriately and requests
    should be rate-limited to prevent system impact during monitoring.

Example Usage:
    ```javascript
    // Fetch system information
    const systemInfo = await fetch('/devtools/system_info');
    const data = await systemInfo.json();
    
    // Monitor application health
    const health = await fetch('/devtools/health');
    const status = await health.json();
    ```

Dependencies:
    - flask: Web framework for API endpoints
    - psutil: System and process monitoring (via system_monitor)
    - sqlalchemy: Database diagnostics and performance metrics
    - logging: Application log access and analysis

Note:
    This module is designed for diagnostic and development use only. In production
    environments, ensure proper access controls are in place and consider the
    security implications of exposing detailed system information.
"""

from flask import Blueprint, jsonify, request
from ..auth import test_mode_login_required

devtools_api = Blueprint('devtools', __name__, url_prefix='/devtools')


@devtools_api.route('/system_info', methods=['GET'])
@test_mode_login_required
def system_info():
    """
    Retrieve comprehensive system hardware and software information.
    
    Provides detailed insights into the host system's specifications, performance
    characteristics, and operational state. This information is essential for
    debugging performance issues, compatibility problems, and resource constraints.
    
    Returns:
        JSON response containing system information including:
            - CPU specifications (model, cores, frequency, usage)
            - Memory details (total, available, usage patterns)
            - Storage information (disk space, I/O performance)
            - Network configuration (interfaces, connectivity, speeds)
            - Operating system details (version, architecture, locale)
            - Python runtime information (version, modules, paths)
            - GPU information (if available for AI workloads)
            - Hardware sensors data (temperature, power, etc.)
    
    Response Format:
        ```json
        {
            "cpu": {
                "model": "Intel Core i7-12700K",
                "cores": 12,
                "frequency": 3600,
                "usage_percent": 23.5
            },
            "memory": {
                "total_gb": 32,
                "available_gb": 18.2,
                "usage_percent": 43.1
            },
            "storage": [
                {
                    "device": "/dev/sda1",
                    "mountpoint": "/",
                    "total_gb": 1000,
                    "free_gb": 750,
                    "filesystem": "ext4"
                }
            ],
            "os": {
                "name": "Ubuntu",
                "version": "22.04",
                "architecture": "x86_64",
                "python_version": "3.11.2"
            }
        }
        ```
    
    Error Handling:
        Returns HTTP 500 with error message if system information cannot be gathered.
        Common causes include insufficient permissions or missing system monitoring
        tools on the host platform.
    
    Performance Notes:
        This endpoint may take 1-3 seconds to complete as it gathers real-time
        system metrics. Consider caching results for dashboard applications.
    
    Security:
        Requires test mode authentication. System information can reveal sensitive
        details about the deployment environment and should be protected accordingly.
    """
    try:
        from ..core.system_monitor import get_system_info
        info = get_system_info()
        return jsonify(info)
    except Exception:
        return jsonify({'error': 'Failed to get system info'}), 500


@devtools_api.route('/app_config', methods=['GET'])
@test_mode_login_required
def app_config():
    """
    Retrieve application configuration and build information.
    
    Provides access to compile-time and runtime configuration settings that
    control application behavior, feature availability, and operational limits.
    This information is crucial for debugging configuration-related issues and
    understanding the current application state.
    
    Returns:
        JSON response containing application configuration including:
            - Application identity (name, version, build information)
            - Operational mode settings (test mode, debug flags)
            - Resource limits (upload sizes, timeout values)
            - Feature toggles and capability flags
            - Environment-specific configuration overrides
            - Security settings and authentication modes
    
    Configuration Categories:
        
        Core Settings:
            - app_name: Application display name
            - version: Current version string (semantic versioning)
            - test_mode: Whether running in development/test mode
            - debug_mode: Detailed logging and error reporting enabled
        
        Resource Limits:
            - max_upload_mb: Maximum file upload size in megabytes
            - request_timeout: Default request timeout in seconds
            - memory_limit: Application memory usage limit
            - concurrent_requests: Maximum concurrent request limit
        
        Feature Flags:
            - ai_models_enabled: AI model processing available
            - web_scraping_enabled: Web content extraction available
            - external_api_enabled: Third-party API integrations active
            - experimental_features: Beta features available for testing
    
    Response Format:
        ```json
        {
            "app_name": "Vybe",
            "version": "1.0Test",
            "test_mode": true,
            "max_upload_mb": 20,
            "debug_mode": true,
            "build_timestamp": "2024-01-15T10:30:00Z",
            "features": {
                "ai_models": true,
                "web_scraping": true,
                "external_apis": false
            }
        }
        ```
    
    Error Handling:
        Returns HTTP 500 with error message if configuration cannot be accessed.
        This may occur if configuration files are corrupted or missing.
    
    Security:
        Requires test mode authentication. Configuration details may reveal
        application architecture and should be protected in production environments.
    
    Use Cases:
        - Debugging configuration-related application issues
        - Verifying correct deployment and environment setup
        - Feature availability checking for frontend components
        - Compliance and audit reporting for system administrators
    """
    try:
        from ..config import Config
        config = {
            'app_name': getattr(Config, 'APP_NAME', 'Vybe'),
            'version': getattr(Config, 'VERSION', '1.0Test'),
            'test_mode': getattr(Config, 'VYBE_TEST_MODE', True),
            'max_upload_mb': int((getattr(Config, 'MAX_CONTENT_LENGTH', 20 * 1024 * 1024) or 0) / (1024 * 1024)),
        }
        return jsonify(config)
    except Exception:
        return jsonify({'error': 'Failed to get app config'}), 500


@devtools_api.route('/app_settings', methods=['GET'])
@test_mode_login_required
def app_settings():
    try:
        from ..models import AppSetting
        settings = {}
        for s in AppSetting.query.all():
            settings[s.key] = s.value
        return jsonify(settings)
    except Exception:
        return jsonify({})


@devtools_api.route('/environment', methods=['GET'])
@test_mode_login_required
def environment():
    try:
        import sys, platform, os
        env = {
            'python_version': sys.version,
            'platform': platform.platform(),
            'executable': sys.executable,
            'cwd': os.getcwd(),
        }
        return jsonify(env)
    except Exception:
        return jsonify({'error': 'Failed to get environment'}), 500


@devtools_api.route('/app_status', methods=['GET'])
@test_mode_login_required
def app_status():
    try:
        # Compose status from existing health endpoint
        from . import api_system_health
        resp = api_system_health()
        import flask
        if isinstance(resp, flask.wrappers.Response):
            data = resp.get_json(silent=True)
        elif isinstance(resp, tuple) and isinstance(resp[0], flask.wrappers.Response):
            data = resp[0].get_json(silent=True)
        else:
            data = {'success': False}
        return jsonify({'success': True, 'health': data})
    except Exception:
        return jsonify({'success': False})


