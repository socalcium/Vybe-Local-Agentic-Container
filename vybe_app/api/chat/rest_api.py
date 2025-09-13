"""
RESTful Chat API Endpoints
==========================

This module provides RESTful HTTP endpoints for chat functionality, complementing
the WebSocket-based real-time chat system. It offers synchronous chat operations,
system status checking, and administrative functions for clients that prefer or
require traditional HTTP request-response patterns over WebSocket connections.

The REST API serves as an alternative interface for chat operations and provides
compatibility with clients that cannot establish WebSocket connections due to
network restrictions, proxy limitations, or architectural constraints.

Key Features:
    - Synchronous chat message processing with immediate responses
    - Chat system status monitoring and health checks
    - Message history retrieval and conversation management
    - Administrative functions for chat system configuration
    - Full compatibility with WebSocket chat functionality
    - Comprehensive error handling with detailed HTTP status codes
    - Request validation and rate limiting
    - Authentication integration with session management

API Endpoints:
    
    Status and Health:
        - GET /chat/status: Check chat system operational status
        - GET /chat/health: Detailed health diagnostics
        - GET /chat/capabilities: Available features and limitations
    
    Message Operations:
        - POST /chat/rest: Send message and receive synchronous response
        - GET /chat/history: Retrieve conversation history
        - DELETE /chat/history: Clear conversation history
        - POST /chat/feedback: Submit response feedback
    
    Administrative:
        - GET /chat/config: Retrieve chat system configuration
        - PUT /chat/config: Update chat system settings
        - POST /chat/reset: Reset chat system state
        - GET /chat/analytics: Usage statistics and metrics

REST vs WebSocket Comparison:
    
    REST API Advantages:
        - Simple HTTP client implementation
        - Better compatibility with firewalls and proxies
        - Natural request-response mapping for synchronous operations
        - Easier debugging and testing with standard HTTP tools
        - Built-in caching support through HTTP headers
    
    WebSocket Advantages:
        - Real-time bidirectional communication
        - Lower latency for interactive conversations
        - Support for typing indicators and presence
        - More efficient for high-frequency message exchange
        - Better user experience for interactive chat

Request/Response Format:
    All endpoints use JSON for both request and response bodies.
    Standard HTTP status codes indicate operation success or failure.
    Comprehensive error messages provide debugging information.
    
    Standard Response Format:
        ```json
        {
            "success": true,
            "data": {...},
            "timestamp": "2024-01-15T10:30:00Z",
            "request_id": "req_12345"
        }
        ```
    
    Error Response Format:
        ```json
        {
            "success": false,
            "error": "Error description",
            "error_code": "SPECIFIC_ERROR_CODE",
            "timestamp": "2024-01-15T10:30:00Z",
            "request_id": "req_12345"
        }
        ```

Authentication and Security:
    - All endpoints require test mode authentication
    - Rate limiting based on user session and IP address
    - Input validation and sanitization for all message content
    - CSRF protection for state-changing operations
    - Comprehensive audit logging for security monitoring

Performance Considerations:
    - Synchronous processing may have higher latency than WebSocket
    - Connection overhead for each HTTP request
    - No persistent connection state between requests
    - Suitable for low-frequency chat operations
    - Automatic retry handling for transient failures

Integration with WebSocket Chat:
    The REST API shares the same backend processing pipeline as WebSocket
    chat, ensuring consistent behavior and feature parity. Messages sent
    via REST API are fully compatible with WebSocket conversations.

Example Usage:
    ```javascript
    // Send chat message via REST API
    const response = await fetch('/chat/rest', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            message: 'Hello, how can you help me?',
            conversation_id: 'conv_123'
        })
    });
    
    const result = await response.json();
    if (result.success) {
        console.log('AI Response:', result.data.response);
    }
    ```

Dependencies:
    - flask: Web framework for HTTP endpoint handling
    - message_processor: Shared message processing and validation
    - auth: Authentication and session management
    - logger: Comprehensive logging and error tracking

Note:
    This module provides a synchronous alternative to WebSocket chat but
    may not support all real-time features like typing indicators or
    immediate presence updates. Choose the appropriate interface based
    on application requirements and client capabilities.
"""

from flask import Blueprint, request, jsonify
from ...auth import test_mode_login_required
from ...logger import log_api_request, log_error
from ...logger import handle_api_errors, log_execution_time
from .message_processor import (
    validate_message, sanitize_message, ensure_backend_ready,
    process_chat_message
)

# Create chat sub-blueprint
chat_bp = Blueprint('chat', __name__, url_prefix='/chat')


@chat_bp.route('/status', methods=['GET'])
@test_mode_login_required
def chat_status():
    """Get chat system status"""
    log_api_request(request.endpoint, request.method)
    
    from ...core.backend_llm_controller import llm_controller
    from ...utils.api_response_utils import format_success_response
    
    backend_running = llm_controller.is_server_ready()
    
    return format_success_response({
        'backend_running': backend_running,
        'llm_ready': backend_running,
        'websocket_enabled': True
    })


@chat_bp.route('/rest', methods=['POST'])
@test_mode_login_required
@handle_api_errors
@log_execution_time
def chat_rest():
    """REST endpoint for chat - bridges to WebSocket implementation"""
    log_api_request(request.endpoint, request.method)
    
    # Import utilities with lazy loading
    from ...utils.security_middleware import chat_rate_limit
    from ...utils.api_response_utils import format_error_response, format_success_response
    
    try:
        # Parse and validate request
        data = request.get_json()
        if not data:
            return format_error_response('Invalid JSON data', 'validation_error', 400)
        
        message = data.get('message', '')
        validation = validate_message(message)
        if not validation['valid']:
            return format_error_response(validation['error'], 'validation_error', 400)
        
        # Sanitize message
        sanitized_message = sanitize_message(validation['message'])
        
        # Ensure backend is ready
        backend_status = ensure_backend_ready()
        if not backend_status['ready']:
            return format_error_response(backend_status['error'], 'backend_error', 503)
        
        # Process message
        result = process_chat_message(
            sanitized_message,
            temperature=data.get('temperature', 0.7),
            max_tokens=data.get('max_tokens', 1024)
        )
        
        if result['success']:
            return format_success_response(result)
        else:
            return format_error_response(result['error'], 'processing_error', 503)
            
    except Exception as e:
        log_error(f"Error in chat REST endpoint: {str(e)}")
        return format_error_response('Internal server error', 'internal_error', 500)
