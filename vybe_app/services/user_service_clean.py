"""
User Management Service for Vybe AI Desktop Application
Simplified version that works with existing models and avoids SQLAlchemy type issues
"""

import hashlib
import secrets
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from flask import current_app, request
from werkzeug.security import generate_password_hash, check_password_hash
import logging

from ..models import User, UserActivity, UserSession, db
from ..utils.input_validation import AdvancedInputValidator, ValidationError
from ..utils.error_handling import ApplicationError, ErrorCode, handle_exceptions

logger = logging.getLogger(__name__)


class UserService:
    """Simplified user management service that works with existing models"""
    
    def __init__(self):
        self.validator = AdvancedInputValidator()
        self.MAX_LOGIN_ATTEMPTS = 5
        self.LOCKOUT_DURATION = timedelta(minutes=30)
        self.SESSION_DURATION = timedelta(hours=24)
        
    @handle_exceptions()
    def create_user(self, username: str, email: str, password: str, 
                   user_type: str = 'user', **kwargs) -> Dict[str, Any]:
        """Create a new user with comprehensive validation"""
        
        # Validate input data
        try:
            validated_username = self.validator.validate_field(
                username, 'username', 'username', required=True
            )
            validated_email = self.validator.validate_field(
                email, 'email', 'email', required=True
            )
            validated_password = self.validator.validate_field(
                password, 'strong_password', 'password', required=True
            )
            
        except ValidationError as e:
            raise ApplicationError(
                f"Validation failed: {str(e)}",
                ErrorCode.VALIDATION_ERROR
            )
        
        # Check if user already exists
        existing_user = User.query.filter(
            (User.username == validated_username) | (User.email == validated_email)
        ).first()
        
        if existing_user:
            if existing_user.username == validated_username:
                raise ApplicationError(
                    "Username already exists",
                    ErrorCode.DUPLICATE_ENTRY
                )
            else:
                raise ApplicationError(
                    "Email already registered", 
                    ErrorCode.DUPLICATE_ENTRY
                )
        
        # Create new user
        user = User()
        user.username = validated_username
        user.email = validated_email
        user.password_hash = generate_password_hash(validated_password)
        
        db.session.add(user)
        
        try:
            db.session.commit()
            
            # Log user creation
            self._log_user_activity(user.id, 'user_created', {
                'registration_method': 'standard',
                'user_type': user_type
            })
            
            return {
                'success': True,
                'user_id': user.id,
                'username': user.username,
                'message': 'User created successfully'
            }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Database error during user creation: {e}")
            raise ApplicationError(
                "Failed to create user due to database error",
                ErrorCode.DATABASE_ERROR
            )
    
    @handle_exceptions()
    def authenticate_user(self, username_or_email: str, password: str) -> Dict[str, Any]:
        """Authenticate user login"""
        
        if not username_or_email or not password:
            raise ApplicationError(
                "Username/email and password are required",
                ErrorCode.VALIDATION_ERROR
            )
        
        # Find user by username or email
        user = User.query.filter(
            (User.username == username_or_email) | (User.email == username_or_email)
        ).first()
        
        if not user:
            self._log_user_activity(None, 'login_failed', {
                'reason': 'user_not_found',
                'username_or_email': username_or_email
            })
            raise ApplicationError(
                "Invalid credentials",
                ErrorCode.AUTHENTICATION_FAILED
            )
        
        # Check if account is locked
        if user.account_locked_until and user.account_locked_until > datetime.utcnow():
            raise ApplicationError(
                "Account temporarily locked",
                ErrorCode.AUTHENTICATION_FAILED
            )
        
        # Verify password
        if not user.check_password(password):
            # Increment failed attempts
            user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
            if user.failed_login_attempts >= self.MAX_LOGIN_ATTEMPTS:
                user.account_locked_until = datetime.utcnow() + self.LOCKOUT_DURATION
            
            db.session.commit()
            
            self._log_user_activity(user.id, 'login_failed', {
                'reason': 'invalid_password',
                'failed_attempts': user.failed_login_attempts
            })
            
            raise ApplicationError(
                "Invalid credentials",
                ErrorCode.AUTHENTICATION_FAILED
            )
        
        # Check if user is active
        if not user.is_active:
            raise ApplicationError(
                "Account is deactivated",
                ErrorCode.AUTHENTICATION_FAILED
            )
        
        # Reset failed attempts and update last login
        user.failed_login_attempts = 0
        user.account_locked_until = None
        user.last_login = datetime.utcnow()
        
        # Create session token
        session_token = self.create_session(user.id)
        
        db.session.commit()
        
        # Log successful login
        self._log_user_activity(user.id, 'login_successful', {
            'session_token': session_token[:10] + '...'  # Log partial token for debugging
        })
        
        return {
            'success': True,
            'user_id': user.id,
            'username': user.username,
            'session_token': session_token,
            'message': 'Authentication successful'
        }
    
    def create_session(self, user_id: int, ip_address: Optional[str] = None,
                      user_agent: Optional[str] = None) -> str:
        """Create a new session token for user"""
        
        # Generate secure session token
        session_token = secrets.token_urlsafe(64)
        expires_at = datetime.utcnow() + self.SESSION_DURATION
        
        # Create session record
        session = UserSession()
        session.user_id = user_id
        session.session_token = session_token
        session.ip_address = ip_address or (request.remote_addr if request else None)
        session.user_agent = user_agent or (request.headers.get('User-Agent') if request else None)
        session.expires_at = expires_at
        
        db.session.add(session)
        
        try:
            db.session.commit()
            return session_token
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to create session: {e}")
            raise ApplicationError(
                "Failed to create session",
                ErrorCode.DATABASE_ERROR
            )
    
    def validate_session(self, session_token: str) -> Dict[str, Any]:
        """Validate and refresh session"""
        
        if not session_token:
            raise ApplicationError(
                "Session token is required",
                ErrorCode.AUTHENTICATION_FAILED
            )
        
        session = UserSession.query.filter(
            (UserSession.session_token == session_token) & 
            (UserSession.is_active == True) &
            (UserSession.expires_at > datetime.utcnow())
        ).first()
        
        if not session:
            raise ApplicationError(
                "Invalid or expired session",
                ErrorCode.AUTHENTICATION_FAILED
            )
        
        # Update last activity
        session.last_activity = datetime.utcnow()
        
        # Get user
        user = User.query.get(session.user_id)
        if not user or not user.is_active:
            session.is_active = False
            db.session.commit()
            raise ApplicationError(
                "User account not active",
                ErrorCode.AUTHENTICATION_FAILED
            )
        
        db.session.commit()
        
        return {
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email
            },
            'session': {
                'id': session.id,
                'expires_at': session.expires_at.isoformat(),
                'last_activity': session.last_activity.isoformat()
            }
        }
    
    def logout_user(self, session_token: str) -> Dict[str, Any]:
        """Logout user and invalidate session"""
        
        session = UserSession.query.filter(
            (UserSession.session_token == session_token) &
            (UserSession.is_active == True)
        ).first()
        
        if session:
            session.is_active = False
            session.logout_at = datetime.utcnow()
            
            # Log logout
            self._log_user_activity(session.user_id, 'user_logout', {
                'session_duration': str(datetime.utcnow() - session.created_at)
            })
            
            db.session.commit()
            
            return {
                'success': True,
                'message': 'Logout successful'
            }
        
        return {
            'success': False,
            'message': 'Session not found'
        }
    
    def change_password(self, user_id: int, current_password: str, 
                       new_password: str) -> Dict[str, Any]:
        """Change user password"""
        
        user = User.query.get(user_id)
        if not user:
            raise ApplicationError(
                "User not found",
                ErrorCode.DATA_NOT_FOUND
            )
        
        # Verify current password
        if not user.check_password(current_password):
            raise ApplicationError(
                "Current password is incorrect",
                ErrorCode.AUTHENTICATION_FAILED
            )
        
        # Validate new password
        try:
            self.validator.validate_field(
                new_password, 'strong_password', 'new_password', required=True
            )
        except ValidationError as e:
            raise ApplicationError(
                f"Password validation failed: {str(e)}",
                ErrorCode.VALIDATION_ERROR
            )
        
        # Set new password
        user.set_password(new_password)
        user.password_changed_at = datetime.utcnow()
        
        # Invalidate all existing sessions
        UserSession.query.filter(
            (UserSession.user_id == user_id) &
            (UserSession.is_active == True)
        ).update({'is_active': False, 'logout_at': datetime.utcnow()})
        
        db.session.commit()
        
        # Log password change
        self._log_user_activity(user_id, 'password_changed', {})
        
        return {
            'success': True,
            'message': 'Password changed successfully'
        }
    
    def get_user_activity(self, user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """Get user activity history"""
        
        activities = UserActivity.query.filter(
            UserActivity.user_id == user_id
        ).order_by(UserActivity.created_at.desc()).limit(limit).all()
        
        return [
            {
                'id': activity.id,
                'activity_type': activity.activity_type,
                'details': activity.get_details(),
                'created_at': activity.created_at.isoformat(),
                'ip_address': activity.ip_address
            }
            for activity in activities
        ]
    
    def _log_user_activity(self, user_id: Optional[int], action: str, 
                          details: Optional[Dict[str, Any]] = None):
        """Log user activity"""
        try:
            activity = UserActivity()
            activity.user_id = user_id
            activity.activity_type = action
            activity.set_details(details or {})
            activity.ip_address = request.remote_addr if request else None
            activity.user_agent = request.headers.get('User-Agent') if request else None
            
            db.session.add(activity)
            # Note: Commit handled by calling function
            
        except Exception as e:
            logger.error(f"Failed to log user activity: {e}")
    
    def _record_failed_login(self, username_or_email: str, ip_address: Optional[str] = None):
        """Record failed login attempt"""
        self._log_user_activity(None, 'failed_login', {
            'username_or_email': username_or_email,
            'ip_address': ip_address or (request.remote_addr if request else None)
        })


# Global service instance
user_service = UserService()
