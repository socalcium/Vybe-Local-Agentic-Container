"""
User API
RESTful API for user management and authentication
"""

from flask import Blueprint, request, jsonify, g
from ..auth import test_mode_login_required, current_user
from functools import wraps
import logging

from ..models import User, db

logger = logging.getLogger(__name__)

user_api = Blueprint('user_api', __name__, url_prefix='/user')

def api_key_required(f):
    """Decorator to require API key authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check for Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({
                'success': False,
                'error': 'Missing or invalid Authorization header. Expected: Bearer <API_KEY>'
            }), 401
        
        # Extract the API key
        try:
            api_key = auth_header.split(' ')[1]
        except IndexError:
            return jsonify({
                'success': False,
                'error': 'Invalid Authorization header format. Expected: Bearer <API_KEY>'
            }), 401
        
        # Find user by API key
        user = User.find_by_api_key(api_key)
        if not user or not user.is_active:
            return jsonify({
                'success': False,
                'error': 'Invalid or expired API key'
            }), 401
        
        # Set the user in request context via flask.g
        g.api_user = user
        return f(*args, **kwargs)
    
    return decorated_function

@user_api.route('/generate-api-key', methods=['POST'])
@test_mode_login_required
def generate_api_key():
    """Generate a new API key for the current user"""
    try:
        # Check if user already has an API key to prevent conflicts
        if current_user.api_key:
            # Revoke existing key first
            current_user.revoke_api_key()
            db.session.commit()
            logger.info(f"Revoked existing API key for user {current_user.username}")
        
        # Generate new API key
        plain_key = current_user.generate_api_key()
        
        # Save to database
        db.session.commit()
        
        logger.info(f"Generated new API key for user {current_user.username}")
        
        return jsonify({
            'success': True,
            'api_key': plain_key,
            'message': 'API key generated successfully. Store this key securely - it will not be shown again.',
            'warning': 'This key provides full access to your account. Keep it secure!'
        })
        
    except Exception as e:
        logger.error(f"Error generating API key for user {current_user.username}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to generate API key'
        }), 500

@user_api.route('/revoke_api_key', methods=['POST'])
@test_mode_login_required
def revoke_api_key():
    """Revoke the current user's API key"""
    try:
        current_user.revoke_api_key()
        
        logger.info(f"Revoked API key for user {current_user.username}")
        
        return jsonify({
            'success': True,
            'message': 'API key revoked successfully'
        })
        
    except Exception as e:
        logger.error(f"Error revoking API key for user {current_user.username}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to revoke API key'
        }), 500

@user_api.route('/api_key_status', methods=['GET'])
@test_mode_login_required
def api_key_status():
    """Check if the user has an active API key"""
    try:
        has_key = current_user.api_key is not None
        
        return jsonify({
            'success': True,
            'has_api_key': has_key,
            'username': current_user.username
        })
        
    except Exception as e:
        logger.error(f"Error checking API key status for user {current_user.username}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to check API key status'
        }), 500

@user_api.route('/profile', methods=['GET'])
@api_key_required
def get_profile():
    """Get user profile (API key protected endpoint for testing)"""
    try:
        user = getattr(g, 'api_user', None)
        if user is None:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 401
        
        return jsonify({
            'success': True,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'created_at': user.created_at.isoformat() if user.created_at else None,
                'last_login': user.last_login.isoformat() if user.last_login else None
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting user profile: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get user profile'
        }), 500
