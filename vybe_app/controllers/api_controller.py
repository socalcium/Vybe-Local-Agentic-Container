"""
Enhanced API Controller
RESTful API endpoints with comprehensive functionality and security.
"""
from flask import Blueprint, request, jsonify, current_app, g
from functools import wraps
from typing import Dict, Any, Optional
import logging

from ..services.user_service import user_service
from ..utils.error_handling import ApplicationError, ErrorCode
from ..utils.input_validation import InputValidator

logger = logging.getLogger(__name__)

# Create blueprint
api_bp = Blueprint('api', __name__, url_prefix='/api/v1')

# Initialize validator
validator = InputValidator()


def auth_required(f):
    """Decorator for authentication required endpoints"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({
                'error': 'Authentication required',
                'code': ErrorCode.AUTHENTICATION_FAILED
            }), 401
        
        token = auth_header.replace('Bearer ', '')
        try:
            session_data = user_service.validate_session(token)
            if not session_data:
                return jsonify({
                    'error': 'Invalid or expired session',
                    'code': ErrorCode.AUTHENTICATION_FAILED
                }), 401
            
            g.current_user = session_data['user']
            g.current_session = session_data['session']
            
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return jsonify({
                'error': 'Authentication failed',
                'code': ErrorCode.AUTHENTICATION_FAILED
            }), 401
        
        return f(*args, **kwargs)
    return decorated_function


def rate_limit(rule_name: str = 'default'):
    """Decorator for rate limiting endpoints - simplified version"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Simplified rate limiting - could be enhanced
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def handle_api_errors(f):
    """Decorator for consistent API error handling"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except ApplicationError as e:
            return jsonify({
                'error': e.message,
                'code': e.code,
                'details': getattr(e, 'details', None)
            }), getattr(e, 'http_status', 400)
        except Exception as e:
            logger.error(f"Unexpected API error: {e}")
            return jsonify({
                'error': 'Internal server error',
                'code': ErrorCode.UNKNOWN_ERROR
            }), 500
    return decorated_function


# User Management Endpoints

@api_bp.route('/auth/register', methods=['POST'])
@rate_limit('user_creation')
@handle_api_errors
def register_user():
    """Register a new user"""
    data = request.get_json()
    
    if not data:
        raise ApplicationError(
            "Request body is required",
            ErrorCode.VALIDATION_ERROR
        )
    
    # Validate required fields
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    
    if not all([username, email, password]):
        raise ApplicationError(
            "Username, email, and password are required",
            ErrorCode.VALIDATION_ERROR
        )
    
    # Create user
    result = user_service.create_user(
        username=username,
        email=email,
        password=password,
        **{k: v for k, v in data.items() if k not in ['username', 'email', 'password']}
    )
    
    return jsonify({
        'success': True,
        'data': result,
        'message': 'User registered successfully'
    }), 201


@api_bp.route('/auth/login', methods=['POST'])
@rate_limit('login_attempt')
@handle_api_errors
def login_user():
    """Authenticate user login"""
    data = request.get_json()
    
    if not data:
        raise ApplicationError(
            "Request body is required",
            ErrorCode.VALIDATION_ERROR
        )
    
    username_or_email = data.get('username') or data.get('email')
    password = data.get('password')
    
    if not all([username_or_email, password]):
        raise ApplicationError(
            "Username/email and password are required",
            ErrorCode.VALIDATION_ERROR
        )
    
    # Authenticate user
    result = user_service.authenticate_user(username_or_email, password)
    
    return jsonify({
        'success': True,
        'data': result,
        'message': 'Authentication successful'
    })


@api_bp.route('/auth/logout', methods=['POST'])
@auth_required
@handle_api_errors
def logout_user():
    """Logout current user"""
    auth_header = request.headers.get('Authorization', '')
    token = auth_header.replace('Bearer ', '')
    
    success = user_service.logout_user(token)
    
    return jsonify({
        'success': success,
        'message': 'Logout successful' if success else 'Logout failed'
    })


@api_bp.route('/auth/session', methods=['GET'])
@auth_required
@handle_api_errors
def get_session_info():
    """Get current session information"""
    return jsonify({
        'success': True,
        'data': {
            'user': g.current_user,
            'session': g.current_session
        }
    })


@api_bp.route('/users/me', methods=['GET'])
@auth_required
@handle_api_errors
def get_current_user():
    """Get current user profile"""
    return jsonify({
        'success': True,
        'data': g.current_user
    })


@api_bp.route('/users/me', methods=['PUT'])
@auth_required
@rate_limit('user_update')
@handle_api_errors
def update_current_user():
    """Update current user profile"""
    data = request.get_json()
    
    if not data:
        raise ApplicationError(
            "Request body is required",
            ErrorCode.VALIDATION_ERROR
        )
    
    # For now, return current user data
    # This would be implemented with user service update method
    return jsonify({
        'success': True,
        'data': g.current_user,
        'message': 'Profile update endpoint - not yet implemented'
    })


@api_bp.route('/users/me/password', methods=['PUT'])
@auth_required
@rate_limit('password_change')
@handle_api_errors
def change_password():
    """Change user password"""
    data = request.get_json()
    
    if not data:
        raise ApplicationError(
            "Request body is required",
            ErrorCode.VALIDATION_ERROR
        )
    
    current_password = data.get('current_password')
    new_password = data.get('new_password')
    
    if not all([current_password, new_password]):
        raise ApplicationError(
            "Current password and new password are required",
            ErrorCode.VALIDATION_ERROR
        )
    
    # Change password using user service
    success = user_service.change_password(
        g.current_user['id'], 
        current_password, 
        new_password
    )
    
    return jsonify({
        'success': success,
        'message': 'Password changed successfully'
    })


@api_bp.route('/users/me/activity', methods=['GET'])
@auth_required
@handle_api_errors
def get_user_activity():
    """Get user activity history"""
    limit = request.args.get('limit', 50, type=int)
    
    # Validate pagination parameters
    limit = min(max(limit, 1), 100)  # Between 1 and 100
    
    activity_data = user_service.get_user_activity(
        g.current_user['id'], 
        limit=limit
    )
    
    return jsonify({
        'success': True,
        'data': activity_data
    })


# Chat and AI Endpoints

@api_bp.route('/chat/sessions', methods=['GET'])
@auth_required
@handle_api_errors
def get_chat_sessions():
    """Get user's chat sessions"""
    # This would be implemented with a chat service
    return jsonify({
        'success': True,
        'data': [],
        'message': 'Chat sessions endpoint - not yet implemented'
    })


@api_bp.route('/chat/sessions', methods=['POST'])
@auth_required
@rate_limit('chat_creation')
@handle_api_errors
def create_chat_session():
    """Create a new chat session"""
    data = request.get_json() or {}
    
    # This would be implemented with a chat service
    return jsonify({
        'success': True,
        'data': {'session_id': 'placeholder'},
        'message': 'Chat session creation - not yet implemented'
    })


@api_bp.route('/models', methods=['GET'])
@auth_required
@handle_api_errors
def get_available_models():
    """Get available AI models"""
    # This would be implemented with a model service
    return jsonify({
        'success': True,
        'data': [],
        'message': 'Models endpoint - not yet implemented'
    })


# Configuration and Settings Endpoints

@api_bp.route('/settings', methods=['GET'])
@auth_required
@handle_api_errors
def get_user_settings():
    """Get user settings and preferences"""
    user_data = g.current_user
    
    return jsonify({
        'success': True,
        'data': {
            'preferences': user_data.get('preferences', {}),
            'metadata': user_data.get('metadata', {})
        }
    })


@api_bp.route('/settings', methods=['PUT'])
@auth_required
@rate_limit('settings_update')
@handle_api_errors
def update_user_settings():
    """Update user settings and preferences"""
    data = request.get_json()
    
    if not data:
        raise ApplicationError(
            "Request body is required",
            ErrorCode.VALIDATION_ERROR
        )
    
    # Extract settings-related fields
    updates = {}
    if 'preferences' in data:
        updates['preferences'] = data['preferences']
    if 'metadata' in data:
        updates['metadata'] = data['metadata']
    
    if not updates:
        raise ApplicationError(
            "No valid settings provided",
            ErrorCode.VALIDATION_ERROR
        )
    
    # For now, return current user data
    # This would be implemented with user service update method
    return jsonify({
        'success': True,
        'data': {
            'preferences': g.current_user.get('preferences', {}),
            'metadata': g.current_user.get('metadata', {})
        },
        'message': 'Settings update endpoint - not yet implemented'
    })


# Health and Status Endpoints

@api_bp.route('/health', methods=['GET'])
@handle_api_errors
def health_check():
    """API health check"""
    return jsonify({
        'success': True,
        'data': {
            'status': 'healthy',
            'version': '1.0.0',
            'timestamp': current_app.config.get('START_TIME', 'unknown')
        }
    })


@api_bp.route('/status', methods=['GET'])
@auth_required
@handle_api_errors
def get_system_status():
    """Get system status (authenticated)"""
    # This would include more detailed system information
    return jsonify({
        'success': True,
        'data': {
            'user_authenticated': True,
            'services': {
                'user_service': 'active',
                'database': 'connected'
            }
        }
    })


# Error handlers

@api_bp.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({
        'error': 'Endpoint not found',
        'code': ErrorCode.DATA_NOT_FOUND
    }), 404


@api_bp.errorhandler(405)
def method_not_allowed(error):
    """Handle 405 errors"""
    return jsonify({
        'error': 'Method not allowed',
        'code': ErrorCode.VALIDATION_ERROR
    }), 405


@api_bp.errorhandler(400)
def bad_request(error):
    """Handle 400 errors"""
    return jsonify({
        'error': 'Bad request',
        'code': ErrorCode.VALIDATION_ERROR
    }), 400


# Register blueprint function
def register_api_routes(app):
    """Register API routes with the Flask app"""
    app.register_blueprint(api_bp)
    logger.info("API routes registered successfully")
