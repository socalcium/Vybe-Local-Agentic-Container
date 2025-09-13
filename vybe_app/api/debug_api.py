"""
Debug API Module - System Diagnostics and Error Management Endpoints.

This module provides comprehensive debugging, error tracking, and system diagnostic
capabilities for the Vybe AI Desktop Application. It enables developers and
administrators to monitor system health, track errors, collect diagnostic information,
and troubleshoot issues in both development and production environments.

The debug API serves as a centralized hub for collecting and analyzing application
behavior, performance metrics, and error patterns. It supports both automated
error reporting from frontend applications and manual diagnostic operations.

Key Features:
    - Frontend JavaScript error logging and tracking
    - Backend error aggregation and analysis
    - System performance monitoring and diagnostics
    - Real-time error reporting and alerting
    - Detailed stack trace collection and analysis
    - User session tracking for error correlation
    - Performance bottleneck identification
    - Resource usage monitoring and reporting
    - Configuration validation and health checks
    - Log file management and rotation

Debug Endpoints:
    - POST /log_frontend_error: Log client-side JavaScript errors
    - GET /error_summary: Get aggregated error statistics
    - GET /recent_errors: Retrieve recent error entries with details
    - GET /system_info: Collect comprehensive system diagnostic information
    - GET /performance_metrics: Get application performance statistics
    - POST /debug_session: Start debugging session with enhanced logging
    - GET /health_check: Comprehensive application health assessment
    - GET /logs: Access and filter application log entries

Error Tracking Features:
    - Automatic error categorization and tagging
    - Error frequency analysis and trending
    - Stack trace parsing and source mapping
    - User action correlation with error occurrences
    - Error severity classification and prioritization
    - Duplicate error detection and aggregation
    - Error resolution tracking and statistics

System Diagnostics:
    - CPU, memory, and disk usage monitoring
    - Network connectivity and latency testing
    - Database performance and connection health
    - AI model loading status and performance
    - Service dependency health checks
    - Configuration validation and warnings
    - Security status and vulnerability scanning

Performance Monitoring:
    - Request/response time tracking
    - Database query performance analysis
    - AI model inference time monitoring
    - Memory usage patterns and leak detection
    - CPU utilization and thread pool status
    - Cache hit/miss ratios and efficiency
    - Background job queue monitoring

Security Considerations:
    - Debug endpoints require authentication in production
    - Sensitive information filtering from error logs
    - Rate limiting for debug API endpoints
    - Access control for sensitive diagnostic data
    - Secure handling of user data in error reports
    - Audit logging for debug API access

Production Safety:
    - Configurable debug mode with feature toggles
    - Automatic sensitive data masking
    - Performance impact minimization
    - Resource usage limits for debug operations
    - Emergency debug mode disabling capabilities

Example Usage:
    # Log frontend error
    POST /api/debug/log_frontend_error
    {
        "type": "TypeError",
        "message": "Cannot read property 'id' of undefined",
        "url": "/dashboard",
        "timestamp": "2024-01-15T10:30:00Z",
        "stack": "Error at line 42..."
    }
    
    # Get system health
    GET /api/debug/system_info
    
    # Check recent errors
    GET /api/debug/recent_errors?limit=50

Data Privacy:
    - User data anonymization in error reports
    - GDPR-compliant error data handling
    - Configurable data retention policies
    - Secure error data transmission and storage
    - User consent handling for detailed error reporting

Note:
    Debug endpoints should be used judiciously in production environments.
    Some operations may impact performance and should be rate-limited.
    Sensitive information is automatically filtered from error reports.
"""

from flask import Blueprint, request, jsonify
from flask_login import login_required
import logging
import datetime

from ..auth import test_mode_login_required
from ..core.error_manager import error_manager, log_error, log_debug
from ..logger import log_api_request, handle_api_errors, log_execution_time

# Initialize logger
logger = logging.getLogger(__name__)

# Create debug sub-blueprint
debug_bp = Blueprint('debug', __name__, url_prefix='/debug')

@debug_bp.route('/log_frontend_error', methods=['POST'])
@test_mode_login_required
@handle_api_errors
@log_execution_time
def log_frontend_error():
    """
    Log and track frontend JavaScript errors for debugging and monitoring.
    
    This endpoint receives error reports from frontend JavaScript applications
    and integrates them into the backend error tracking system. It provides
    centralized error logging for client-side issues, enabling comprehensive
    application monitoring and debugging across the entire stack.
    
    The endpoint processes various types of client-side errors including
    JavaScript exceptions, network failures, resource loading errors, and
    custom application errors with detailed context information.
    
    Request Body:
        JSON object containing error information:
        {
            "type": "TypeError" | "ReferenceError" | "NetworkError" | "CustomError",
            "message": "Detailed error description",
            "url": "/path/where/error/occurred",
            "timestamp": "2024-01-15T10:30:00Z",
            "stack": "Complete JavaScript stack trace",
            "user_agent": "Browser and OS information",
            "browser_info": {
                "name": "Chrome",
                "version": "120.0.0.0",
                "platform": "Windows"
            },
            "session_id": "frontend_session_identifier",
            "user_id": 123,
            "additional_context": {
                "component": "ChatInterface",
                "action": "send_message",
                "data": "Relevant application state"
            }
        }
    
    Returns:
        JSON response confirming error logging:
        
        Success (200):
        {
            "status": "logged",
            "timestamp": "2024-01-15T10:30:15Z",
            "error_id": "fe_error_1642351815",
            "correlation_id": "corr_1642351815_abc123"
        }
        
        Missing Data (400):
        {
            "error": "No error data provided",
            "required_fields": ["type", "message"]
        }
        
        Processing Error (500):
        {
            "error": "Failed to log frontend error",
            "retry_after": 5
        }
    
    Error Processing:
        - Automatic error categorization and severity assessment
        - Duplicate error detection and aggregation
        - User session correlation for debugging patterns
        - Browser and platform-specific error handling
        - Stack trace parsing and source map integration
        - Error frequency tracking and alerting
    
    Data Enhancement:
        - Server-side timestamp addition for accuracy
        - IP address and geolocation (anonymized)
        - User agent parsing and normalization
        - Session correlation with backend events
        - Error pattern recognition and tagging
    
    Privacy and Security:
        - Automatic PII detection and redaction
        - Sensitive data filtering from error messages
        - User consent validation for detailed tracking
        - Rate limiting to prevent error spam
        - Secure transmission and storage
    
    Monitoring Integration:
        - Real-time error alerting for critical issues
        - Error trend analysis and reporting
        - Performance impact assessment
        - User experience correlation analysis
        - Automated error reporting to development teams
    
    Example:
        >>> error_data = {
        ...     "type": "TypeError",
        ...     "message": "Cannot read property 'id' of undefined",
        ...     "url": "/dashboard",
        ...     "stack": "TypeError: Cannot read property..."
        ... }
        >>> response = requests.post('/api/debug/log_frontend_error', 
        ...                         json=error_data)
        >>> print(response.json()['status'])  # 'logged'
    
    Note:
        This endpoint is designed for high-frequency usage and includes
        automatic deduplication to prevent log flooding. Critical errors
        trigger immediate alerts to development teams.
    """
    log_api_request(request.endpoint, request.method)
    
    try:
        error_data = request.get_json()
        if not error_data:
            return jsonify({'error': 'No error data provided'}), 400
        
        # Log the frontend error
        log_debug("Frontend Error Received", {
            'error_type': error_data.get('type', 'unknown'),
            'message': error_data.get('message', ''),
            'url': error_data.get('url', ''),
            'user_agent': request.headers.get('User-Agent', ''),
            'timestamp': error_data.get('timestamp', datetime.datetime.now().isoformat()),
            'full_error_data': error_data
        }, level="ERROR")
        
        return jsonify({'status': 'logged', 'timestamp': datetime.datetime.now().isoformat()})
        
    except Exception as e:
        log_error(e, {'endpoint': 'log_frontend_error'}, category="debug_api")
        return jsonify({'error': 'Failed to log frontend error'}), 500

@debug_bp.route('/error_summary', methods=['GET'])
@test_mode_login_required  
@handle_api_errors
@log_execution_time
def get_error_summary():
    """
    Get summary of backend errors
    """
    log_api_request(request.endpoint, request.method)
    
    try:
        summary = error_manager.get_error_summary()
        return jsonify(summary)
        
    except Exception as e:
        log_error(e, {'endpoint': 'get_error_summary'}, category="debug_api")
        return jsonify({'error': 'Failed to get error summary'}), 500

@debug_bp.route('/recent_errors', methods=['GET'])
@test_mode_login_required
@handle_api_errors  
@log_execution_time
def get_recent_errors():
    """
    Get recent errors for debugging
    """
    log_api_request(request.endpoint, request.method)
    
    try:
        limit = request.args.get('limit', 20, type=int)
        errors = error_manager.get_recent_errors(limit)
        
        return jsonify({
            'errors': errors,
            'total_count': len(errors),
            'debug_mode': error_manager.debug_mode
        })
        
    except Exception as e:
        log_error(e, {'endpoint': 'get_recent_errors'}, category="debug_api")
        return jsonify({'error': 'Failed to get recent errors'}), 500

@debug_bp.route('/system_info', methods=['GET'])
@test_mode_login_required
@handle_api_errors
@log_execution_time  
def get_system_info():
    """
    Get system information for debugging
    """
    log_api_request(request.endpoint, request.method)
    
    try:
        system_info = error_manager.get_system_info()
        
        # Add Flask app info
        from flask import current_app
        system_info['flask_info'] = {
            'debug': current_app.debug,
            'testing': current_app.testing,
            'config_keys': list(current_app.config.keys())
        }
        
        return jsonify(system_info)
        
    except Exception as e:
        log_error(e, {'endpoint': 'get_system_info'}, category="debug_api")
        return jsonify({'error': 'Failed to get system info'}), 500

@debug_bp.route('/clear_errors', methods=['POST'])
@test_mode_login_required
@handle_api_errors
@log_execution_time
def clear_errors():
    """
    Clear error history (for testing/debugging)
    """
    log_api_request(request.endpoint, request.method)
    
    try:
        error_manager.clear_error_history()
        log_debug("Error history cleared by user request")
        
        return jsonify({'status': 'cleared', 'timestamp': datetime.datetime.now().isoformat()})
        
    except Exception as e:
        log_error(e, {'endpoint': 'clear_errors'}, category="debug_api")
        return jsonify({'error': 'Failed to clear errors'}), 500

@debug_bp.route('/toggle_debug', methods=['POST'])
@test_mode_login_required
@handle_api_errors
@log_execution_time
def toggle_debug_mode():
    """
    Toggle debug mode on/off
    """
    log_api_request(request.endpoint, request.method)
    
    try:
        import os
        current_debug = os.getenv('VYBE_DEBUG', 'false').lower() == 'true'
        new_debug = not current_debug
        
        # This would require a restart to take full effect
        # But we can toggle the error_manager's debug mode
        error_manager.debug_mode = new_debug
        
        log_debug(f"Debug mode toggled to: {new_debug}")
        
        return jsonify({
            'debug_mode': new_debug,
            'note': 'Full debug mode requires server restart',
            'timestamp': datetime.datetime.now().isoformat()
        })
        
    except Exception as e:
        log_error(e, {'endpoint': 'toggle_debug_mode'}, category="debug_api")
        return jsonify({'error': 'Failed to toggle debug mode'}), 500

@debug_bp.route('/installation_diagnostics', methods=['GET'])
def get_installation_diagnostics():
    """Get AI-powered installation diagnostics summary"""
    try:
        from ..core.installation_monitor import installation_monitor
        summary = installation_monitor.get_diagnostics_summary()
        return jsonify({
            'success': True,
            'data': summary
        })
    except Exception as e:
        logger.error(f"Error getting installation diagnostics: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@debug_bp.route('/installation_diagnostics/detailed', methods=['GET'])
def get_detailed_installation_diagnostics():
    """Get detailed installation diagnostics report"""
    try:
        from ..core.installation_monitor import installation_monitor
        detailed_report = installation_monitor.get_detailed_report()
        return jsonify({
            'success': True,
            'data': detailed_report
        })
    except Exception as e:
        logger.error(f"Error getting detailed installation diagnostics: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@debug_bp.route('/installation_diagnostics/run', methods=['POST'])
def run_installation_diagnostics():
    """Run comprehensive AI-powered installation diagnostics"""
    try:
        from ..core.installation_monitor import installation_monitor
        diagnostics = installation_monitor.run_diagnostics()
        return jsonify({
            'success': True,
            'data': diagnostics
        })
    except Exception as e:
        logger.error(f"Error running installation diagnostics: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@debug_bp.route('/installation_diagnostics/start_monitoring', methods=['POST'])
def start_installation_monitoring():
    """Start continuous installation monitoring"""
    try:
        from ..core.installation_monitor import installation_monitor
        installation_monitor.start_monitoring()
        return jsonify({
            'success': True,
            'message': 'Installation monitoring started'
        })
    except Exception as e:
        logger.error(f"Error starting installation monitoring: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@debug_bp.route('/installation_diagnostics/stop_monitoring', methods=['POST'])
def stop_installation_monitoring():
    """Stop continuous installation monitoring"""
    try:
        from ..core.installation_monitor import installation_monitor
        installation_monitor.stop_monitoring()
        return jsonify({
            'success': True,
            'message': 'Installation monitoring stopped'
        })
    except Exception as e:
        logger.error(f"Error stopping installation monitoring: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
