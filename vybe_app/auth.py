from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, session, g
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime, timedelta
from functools import wraps
from typing import Optional, DefaultDict, Dict, List
import os
import secrets
import hashlib
import ipaddress
import time
import json
import qrcode
import base64
import pyotp
from io import BytesIO
from collections import defaultdict
from threading import Lock
import gc
from .models import db, User
from .logger import log_user_action
import logging

logger = logging.getLogger(__name__)

class AuthStateManager:
    """Centralized authentication state management to reduce global variable usage"""
    
    def __init__(self):
        # Rate limiting for authentication endpoints
        self.auth_attempts = defaultdict(list)
        self.auth_lock = Lock()
        
        # MFA and security tracking
        self.mfa_sessions = {}
        self.mfa_lock = Lock()
        self.security_events = defaultdict(list)
        self.security_lock = Lock()
        
        # Enhanced session management
        self.user_sessions = defaultdict(list)  # user_id -> list of session tokens
        self.session_tokens = {}  # session_token -> session_data
        self.session_lock = Lock()
        
        # Security configuration
        self.security_config = {
            'mfa_required': os.getenv('VYBE_MFA_REQUIRED', 'False').lower() == 'true',
            'session_timeout': int(os.getenv('VYBE_SESSION_TIMEOUT', '3600')),  # 1 hour
            'max_failed_attempts': int(os.getenv('VYBE_MAX_FAILED_ATTEMPTS', '5')),
            'lockout_duration': int(os.getenv('VYBE_LOCKOUT_DURATION', '900')),  # 15 minutes
            'password_min_length': int(os.getenv('VYBE_PASSWORD_MIN_LENGTH', '8')),
            'require_special_chars': os.getenv('VYBE_REQUIRE_SPECIAL_CHARS', 'True').lower() == 'true',
            'max_sessions_per_user': int(os.getenv('VYBE_MAX_SESSIONS_PER_USER', '3')),
            'token_rotation_interval': int(os.getenv('VYBE_TOKEN_ROTATION_INTERVAL', '1800')),  # 30 minutes
            'device_tracking_enabled': os.getenv('VYBE_DEVICE_TRACKING', 'True').lower() == 'true',
            'session_encryption_enabled': os.getenv('VYBE_SESSION_ENCRYPTION', 'True').lower() == 'true'
        }
    
    def cleanup(self):
        """Clean up authentication state with secure memory handling"""
        with self.auth_lock:
            # Clear auth attempts (these are lists of timestamps, no sensitive data)
            for key in list(self.auth_attempts.keys()):
                self.auth_attempts[key].clear()
                del self.auth_attempts[key]
            self.auth_attempts.clear()
            
        with self.mfa_lock:
            # Clear MFA sessions with secure overwrite
            for session_id in list(self.mfa_sessions.keys()):
                if isinstance(self.mfa_sessions[session_id], dict):
                    for field in ['code', 'secret', 'backup_codes']:
                        if field in self.mfa_sessions[session_id]:
                            self.mfa_sessions[session_id][field] = '\x00' * len(str(self.mfa_sessions[session_id][field]))
                del self.mfa_sessions[session_id]
            self.mfa_sessions.clear()
            
        with self.security_lock:
            self.security_events.clear()
            
        with self.session_lock:
            # Clear user sessions (these are lists of session tokens)
            for session_id in list(self.user_sessions.keys()):
                self.user_sessions[session_id].clear()
                del self.user_sessions[session_id]
            self.user_sessions.clear()
            
            # Clear session tokens with secure overwrite
            for token in list(self.session_tokens.keys()):
                if isinstance(self.session_tokens[token], dict):
                    for field in ['token', 'api_key', 'password_hash']:
                        if field in self.session_tokens[token]:
                            self.session_tokens[token][field] = '\x00' * len(str(self.session_tokens[token][field]))
                del self.session_tokens[token]
            self.session_tokens.clear()
            
        # Force garbage collection to clear references
        import gc
        gc.collect()


# Global auth state manager instance
auth_state_manager = AuthStateManager()

# Register authentication cleanup with global cleanup system
try:
    from run import register_cleanup_function
    register_cleanup_function(auth_state_manager.cleanup, "Authentication state cleanup")
except ImportError:
    pass  # Fallback if run module not available

# Convenience accessors for backward compatibility
SECURITY_CONFIG = auth_state_manager.security_config
auth_attempts: DefaultDict = auth_state_manager.auth_attempts
auth_lock = auth_state_manager.auth_lock
mfa_sessions = auth_state_manager.mfa_sessions
mfa_lock = auth_state_manager.mfa_lock
security_events_data: DefaultDict = auth_state_manager.security_events
security_lock = auth_state_manager.security_lock
user_sessions: DefaultDict = auth_state_manager.user_sessions
session_tokens = auth_state_manager.session_tokens
session_lock = auth_state_manager.session_lock

class SessionManager:
    """Enhanced session management with token rotation and device tracking"""
    
    def __init__(self):
        self.cleanup_interval = 300  # 5 minutes
        self.last_cleanup = time.time()
    
    def create_session(self, user_id: int, device_info: Optional[dict] = None) -> str:
        """Create a new session with token rotation"""
        with session_lock:
            # Generate unique session token
            session_token = self._generate_session_token()
            
            # Create session data
            session_data = {
                'user_id': user_id,
                'created_at': time.time(),
                'last_activity': time.time(),
                'device_info': device_info or self._get_device_info(),
                'ip_address': self._get_client_ip(),
                'user_agent': request.headers.get('User-Agent', ''),
                'token_version': 1,
                'is_active': True
            }
            
            # Store session
            session_tokens[session_token] = session_data
            user_sessions[user_id].append(session_token)
            
            # Enforce maximum sessions per user
            self._enforce_session_limit(user_id)
            
            # Clean up old sessions periodically
            self._cleanup_old_sessions()
            
            return session_token
    
    def validate_session(self, session_token: str) -> bool:
        """Validate session token and update activity"""
        with session_lock:
            if session_token not in session_tokens:
                return False
            
            session_data = session_tokens[session_token]
            
            # Check if session is active
            if not session_data['is_active']:
                return False
            
            # Check session timeout
            if time.time() - session_data['last_activity'] > SECURITY_CONFIG['session_timeout']:
                self._invalidate_session(session_token)
                return False
            
            # Check token rotation
            if self._should_rotate_token(session_data):
                new_token = self._rotate_session_token(session_token)
                if new_token:
                    # Update session in Flask
                    session['session_token'] = new_token
                    return True
            
            # Update last activity
            session_data['last_activity'] = time.time()
            
            return True
    
    def invalidate_session(self, session_token: str):
        """Invalidate a specific session"""
        with session_lock:
            self._invalidate_session(session_token)
    
    def invalidate_user_sessions(self, user_id: int, exclude_token: Optional[str] = None):
        """Invalidate all sessions for a user except the specified one"""
        with session_lock:
            if user_id in user_sessions:
                for token in user_sessions[user_id][:]:  # Copy list to avoid modification during iteration
                    if token != exclude_token:
                        self._invalidate_session(token)
    
    def get_user_sessions(self, user_id: int) -> list:
        """Get all active sessions for a user"""
        with session_lock:
            sessions = []
            if user_id in user_sessions:
                for token in user_sessions[user_id]:
                    if token in session_tokens:
                        session_data = session_tokens[token].copy()
                        # Remove sensitive data
                        session_data.pop('user_id', None)
                        sessions.append(session_data)
            return sessions
    
    def _generate_session_token(self) -> str:
        """Generate a cryptographically secure session token"""
        return secrets.token_urlsafe(32)
    
    def _get_device_info(self) -> dict:
        """Extract device information from request"""
        if not SECURITY_CONFIG['device_tracking_enabled']:
            return {}
        
        user_agent = request.headers.get('User-Agent', '')
        
        # Basic device fingerprinting
        device_info = {
            'user_agent': user_agent,
            'ip_address': self._get_client_ip(),
            'accept_language': request.headers.get('Accept-Language', ''),
            'accept_encoding': request.headers.get('Accept-Encoding', ''),
            'fingerprint': self._generate_device_fingerprint()
        }
        
        return device_info
    
    def _generate_device_fingerprint(self) -> str:
        """Generate a device fingerprint for tracking"""
        fingerprint_data = [
            request.headers.get('User-Agent', ''),
            request.headers.get('Accept-Language', ''),
            request.headers.get('Accept-Encoding', ''),
            self._get_client_ip()
        ]
        
        fingerprint_string = '|'.join(filter(None, fingerprint_data))
        return hashlib.sha256(fingerprint_string.encode()).hexdigest()[:16]
    
    def _get_client_ip(self) -> str:
        """Get client IP address"""
        client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', '127.0.0.1'))
        if client_ip:
            return client_ip.split(',')[0].strip()
        return '127.0.0.1'
    
    def _enforce_session_limit(self, user_id: int):
        """Enforce maximum sessions per user"""
        max_sessions = SECURITY_CONFIG['max_sessions_per_user']
        
        if user_id in user_sessions and len(user_sessions[user_id]) > max_sessions:
            # Remove oldest sessions
            sessions_to_remove = user_sessions[user_id][:-max_sessions]
            for token in sessions_to_remove:
                self._invalidate_session(token)
    
    def _should_rotate_token(self, session_data: dict) -> bool:
        """Check if token should be rotated"""
        rotation_interval = SECURITY_CONFIG['token_rotation_interval']
        return time.time() - session_data['last_activity'] > rotation_interval
    
    def _rotate_session_token(self, old_token: str) -> Optional[str]:
        """Rotate session token for security"""
        if old_token not in session_tokens:
            return None
        
        session_data = session_tokens[old_token]
        new_token = self._generate_session_token()
        
        # Update session data
        session_data['token_version'] += 1
        session_data['last_activity'] = time.time()
        
        # Move session to new token
        session_tokens[new_token] = session_data
        del session_tokens[old_token]
        
        # Update active sessions list
        user_id = session_data['user_id']
        if user_id in user_sessions:
            try:
                index = user_sessions[user_id].index(old_token)
                user_sessions[user_id][index] = new_token
            except ValueError:
                pass
        
        return new_token
    
    def _invalidate_session(self, session_token: str):
        """Invalidate a session"""
        if session_token in session_tokens:
            session_data = session_tokens[session_token]
            user_id = session_data['user_id']
            
            # Remove from active sessions
            if user_id in user_sessions:
                try:
                    user_sessions[user_id].remove(session_token)
                except ValueError:
                    pass
            
            # Remove session data
            del session_tokens[session_token]
    
    def _cleanup_old_sessions(self):
        """Clean up expired sessions"""
        current_time = time.time()
        
        # Only cleanup every 5 minutes
        if current_time - self.last_cleanup < self.cleanup_interval:
            return
        
        self.last_cleanup = current_time
        
        with session_lock:
            expired_tokens = []
            
            for token, session_data in session_tokens.items():
                # Check session timeout
                if current_time - session_data['last_activity'] > SECURITY_CONFIG['session_timeout']:
                    expired_tokens.append(token)
            
            # Remove expired sessions
            for token in expired_tokens:
                self._invalidate_session(token)

# Global session manager instance
session_manager = SessionManager()

def check_auth_rate_limit(identifier: str, max_attempts: int = 5, window: int = 300) -> bool:
    """
    Check if authentication attempts are within rate limits
    
    Args:
        identifier: IP address or username
        max_attempts: Maximum attempts allowed in window
        window: Time window in seconds (5 minutes default)
        
    Returns:
        True if within limits, False if rate limited
    """
    current_time = time.time()
    
    with auth_lock:
        # Clean old attempts
        auth_attempts[identifier] = [
            attempt_time for attempt_time in auth_attempts[identifier]
            if current_time - attempt_time < window
        ]
        
        # Check if limit exceeded
        if len(auth_attempts[identifier]) >= max_attempts:
            return False
        
        # Record this attempt
        auth_attempts[identifier].append(current_time)
        return True

def get_client_identifier() -> str:
    """Get client identifier for rate limiting (IP address)"""
    client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', '127.0.0.1'))
    if client_ip:
        return client_ip.split(',')[0].strip()
    return '127.0.0.1'

def log_security_event(user_id: int, event_type: str, details: Optional[dict] = None):
    """Log security events for monitoring"""
    with security_lock:
        event = {
            'timestamp': datetime.utcnow().isoformat(),
            'user_id': user_id,
            'event_type': event_type,
            'ip_address': get_client_identifier(),
            'user_agent': request.headers.get('User-Agent', ''),
            'details': details or {}
        }
        security_events_data[user_id].append(event)
        
        # Keep only last 100 events per user
        if len(security_events_data[user_id]) > 100:
            security_events_data[user_id] = security_events_data[user_id][-100:]

def validate_password_strength(password: str) -> tuple[bool, str]:
    """Validate password strength according to security policy"""
    if len(password) < SECURITY_CONFIG['password_min_length']:
        return False, f"Password must be at least {SECURITY_CONFIG['password_min_length']} characters long"
    
    if SECURITY_CONFIG['require_special_chars']:
        if not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in password):
            return False, "Password must contain at least one special character"
    
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"
    
    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"
    
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one number"
    
    return True, "Password meets strength requirements"

def generate_mfa_secret() -> str:
    """Generate a new MFA secret key"""
    return pyotp.random_base32()

def generate_mfa_qr_code(secret: str, username: str) -> str:
    """Generate QR code for MFA setup"""
    totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
        name=username,
        issuer_name="Vybe AI"
    )
    
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(totp_uri)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, 'PNG')
    buffer.seek(0)
    
    return base64.b64encode(buffer.getvalue()).decode()

def verify_mfa_code(secret: str, code: str) -> bool:
    """Verify MFA code"""
    totp = pyotp.TOTP(secret)
    return totp.verify(code, valid_window=1)  # Allow 30-second window

def create_mfa_session(user_id: int) -> str:
    """Create MFA verification session"""
    session_id = secrets.token_urlsafe(32)
    with mfa_lock:
        mfa_sessions[session_id] = {
            'user_id': user_id,
            'created_at': datetime.utcnow(),
            'verified': False
        }
    return session_id

def verify_mfa_session(session_id: str) -> bool:
    """Verify MFA session is valid and verified"""
    with mfa_lock:
        if session_id not in mfa_sessions:
            return False
        
        session_data = mfa_sessions[session_id]
        
        # Check if session is expired (5 minutes)
        if datetime.utcnow() - session_data['created_at'] > timedelta(minutes=5):
            del mfa_sessions[session_id]
            return False
        
        return session_data['verified']

def mark_mfa_session_verified(session_id: str):
    """Mark MFA session as verified"""
    with mfa_lock:
        if session_id in mfa_sessions:
            mfa_sessions[session_id]['verified'] = True

def cleanup_expired_sessions():
    """Clean up expired MFA sessions"""
    with mfa_lock:
        current_time = datetime.utcnow()
        expired_sessions = [
            session_id for session_id, session_data in mfa_sessions.items()
            if current_time - session_data['created_at'] > timedelta(minutes=5)
        ]
        for session_id in expired_sessions:
            del mfa_sessions[session_id]

def check_user_sessions(user_id: int) -> bool:
    """Check if user has too many active sessions"""
    # This would typically check against a database table
    # For now, we'll use a simple in-memory check
    active_sessions = 0
    with mfa_lock:
        for session_data in mfa_sessions.values():
            if session_data['user_id'] == user_id and session_data['verified']:
                active_sessions += 1
    
    return active_sessions < SECURITY_CONFIG['max_sessions_per_user']

def test_mode_login_required(f):
    """
    Custom decorator that bypasses authentication when VYBE_TEST_MODE is True,
    otherwise behaves like @login_required
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if test mode is enabled
        if os.getenv('VYBE_TEST_MODE', 'False').lower() == 'true':
            # In test mode, bypass authentication and provide a mock user
            from flask import g
            from flask_login import AnonymousUserMixin, login_user
            
            # Create a mock authenticated user for templates
            class TestModeUser(AnonymousUserMixin):
                def __init__(self):
                    self.id = 1
                    self.username = "test_user"
                    self.email = "test@vybe.local"
                
                @property
                def is_active(self):
                    return True
                
                @property
                def is_authenticated(self):
                    return True
                
                @property
                def is_anonymous(self):
                    return False
                
                def get_id(self):
                    return str(self.id)
            
            # Try to get or create the test user and simulate login
            try:
                # Check if a test user exists in the database
                test_user = User.query.filter_by(username='test_user').first()
                if not test_user:
                    # Create test user if it doesn't exist
                    test_user = User()
                    test_user.username = 'test_user'
                    test_user.email = 'test@vybe.local'
                    test_user.set_password('test123')
                    db.session.add(test_user)
                    db.session.commit()
                
                # Login the test user for this request
                login_user(test_user, remember=False)
            except Exception:
                # If database operations fail, use mock user in g
                g._login_user = TestModeUser()
            
            return f(*args, **kwargs)
        else:
            # In normal mode, require login
            return login_required(f)(*args, **kwargs)
    return decorated_function

def is_local_request():
    """Check if the request is coming from localhost/local network"""
    try:
        client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', '127.0.0.1'))
        if client_ip:
            # Handle comma-separated IPs (proxies)
            client_ip = client_ip.split(',')[0].strip()
            
            # Check if IP is localhost or local network
            ip_obj = ipaddress.ip_address(client_ip)
            return (ip_obj.is_loopback or 
                   ip_obj.is_private or 
                   client_ip in ['127.0.0.1', '::1', 'localhost'])
        return True  # Default to allowing if we can't determine IP
    except Exception as e:
        logger.warning(f"Error checking local request: {e}")
        return True  # Default to allowing on error

def device_only_required(f):
    """Decorator to ensure function is only accessible from the local device"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_local_request():
            return jsonify({'error': 'Access denied: Local device access only'}), 403
        return f(*args, **kwargs)
    return decorated_function

def enhanced_login_required(f):
    """Enhanced login required decorator with session validation"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if test mode is enabled
        if os.getenv('VYBE_TEST_MODE', 'False').lower() == 'true':
            return test_mode_login_required(f)(*args, **kwargs)
        
        # Validate session token
        session_token = session.get('session_token')
        if not session_token or not session_manager.validate_session(session_token):
            # Session invalid, redirect to login
            return redirect(url_for('auth.login'))
        
        return f(*args, **kwargs)
    return decorated_function

def device_tracking_required(f):
    """Decorator to require device tracking for sensitive operations"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not SECURITY_CONFIG['device_tracking_enabled']:
            return f(*args, **kwargs)
        
        # Check if device fingerprint matches
        session_token = session.get('session_token')
        if session_token and session_token in session_tokens:
            session_data = session_tokens[session_token]
            current_fingerprint = session_manager._generate_device_fingerprint()
            
            if session_data['device_info'].get('fingerprint') != current_fingerprint:
                # Device fingerprint changed, require re-authentication
                session_manager.invalidate_session(session_token)
                return redirect(url_for('auth.login'))
        
        return f(*args, **kwargs)
    return decorated_function

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Rate limiting check
        client_id = get_client_identifier()
        if not check_auth_rate_limit(client_id, max_attempts=SECURITY_CONFIG['max_failed_attempts'], window=300):
            flash('Too many login attempts. Please wait 5 minutes before trying again.', 'error')
            log_user_action('login_rate_limited', {'ip': client_id})
            return render_template('login.html', show_create=is_local_request())
        
        # CSRF protection
        if not request.form.get('csrf_token'):
            flash('Security token missing. Please refresh the page and try again.', 'error')
            return render_template('login.html', show_create=is_local_request())
        
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember', False))
        
        # Input validation
        if not username or not password:
            flash('Username and password are required.', 'error')
            return render_template('login.html', show_create=is_local_request())
        
        # Username validation
        if len(username) < 3 or len(username) > 64:
            flash('Username must be between 3 and 64 characters.', 'error')
            return render_template('login.html', show_create=is_local_request())
        
        # Check username format
        import re
        if not re.match(r'^[a-zA-Z0-9._-]+$', username):
            flash('Username can only contain letters, numbers, dots, hyphens, and underscores.', 'error')
            return render_template('login.html', show_create=is_local_request())
        
        # Enhanced password validation
        is_valid, error_msg = validate_password_strength(password)
        if not is_valid:
            flash(f'Password validation failed: {error_msg}', 'error')
            return render_template('login.html', show_create=is_local_request())
        
        user = User.query.filter(User.username.ilike(username)).first()
        
        if user and user.check_password(password):
            # Check if user has too many active sessions
            if not check_user_sessions(user.id):
                flash('Too many active sessions. Please log out from other devices.', 'error')
                log_security_event(user.id, 'too_many_sessions')
                return render_template('login.html', show_create=is_local_request())
            
            # Check if MFA is required
            if SECURITY_CONFIG['mfa_required'] and user.mfa_enabled:
                # Create MFA session and redirect to MFA verification
                mfa_session_id = create_mfa_session(user.id)
                session['mfa_session_id'] = mfa_session_id
                session['pending_user_id'] = user.id
                session['remember_me'] = remember
                session['next_page'] = request.args.get('next')
                
                log_security_event(user.id, 'mfa_required')
                return redirect(url_for('auth.mfa_verify'))
            
            # Update last login time
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            login_user(user, remember=remember)
            log_user_action(user.id, f"User {username} logged in")
            log_security_event(user.id, 'login_successful')
            
            # Redirect to next page or home
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('views.index'))
        else:
            flash('Invalid username or password.', 'error')
            if user:
                log_security_event(user.id, 'login_failed', {'reason': 'invalid_password'})
            log_user_action(None, f"Failed login attempt for username: {username}")
    
    # Show create account button only for local requests
    return render_template('login.html', show_create=is_local_request())

@auth_bp.route('/mfa/verify', methods=['GET', 'POST'])
def mfa_verify():
    """MFA verification page"""
    mfa_session_id = session.get('mfa_session_id')
    pending_user_id = session.get('pending_user_id')
    
    if not mfa_session_id or not pending_user_id:
        flash('Invalid MFA session. Please log in again.', 'error')
        return redirect(url_for('auth.login'))
    
    if not verify_mfa_session(mfa_session_id):
        flash('MFA session expired. Please log in again.', 'error')
        return redirect(url_for('auth.login'))
    
    user = User.query.get(pending_user_id)
    if not user:
        flash('User not found. Please log in again.', 'error')
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        mfa_code = request.form.get('mfa_code', '').strip()
        
        if not mfa_code:
            flash('MFA code is required.', 'error')
            return render_template('mfa_verify.html', user=user)
        
        if verify_mfa_code(user.mfa_secret, mfa_code):
            # Mark MFA session as verified
            mark_mfa_session_verified(mfa_session_id)
            
            # Update last login time
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            # Log in the user
            remember = session.get('remember_me', False)
            login_user(user, remember=remember)
            
            log_user_action(user.id, f"User {user.username} completed MFA verification")
            log_security_event(user.id, 'mfa_verification_successful')
            
            # Clean up session
            session.pop('mfa_session_id', None)
            session.pop('pending_user_id', None)
            session.pop('remember_me', None)
            
            # Redirect to next page or home
            next_page = session.pop('next_page', None)
            if next_page:
                return redirect(next_page)
            return redirect(url_for('views.index'))
        else:
            flash('Invalid MFA code. Please try again.', 'error')
            log_security_event(user.id, 'mfa_verification_failed')
    
    return render_template('mfa_verify.html', user=user)

@auth_bp.route('/mfa/setup', methods=['GET', 'POST'])
@login_required
def mfa_setup():
    """MFA setup page"""
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'enable':
            # Generate new MFA secret
            secret = generate_mfa_secret()
            current_user.mfa_secret = secret
            current_user.mfa_enabled = True
            db.session.commit()
            
            log_security_event(current_user.id, 'mfa_enabled')
            flash('MFA has been enabled. Please scan the QR code with your authenticator app.', 'success')
            
        elif action == 'disable':
            current_user.mfa_secret = None
            current_user.mfa_enabled = False
            db.session.commit()
            
            log_security_event(current_user.id, 'mfa_disabled')
            flash('MFA has been disabled.', 'success')
    
    # Generate QR code if MFA is enabled
    qr_code = None
    if current_user.mfa_enabled and current_user.mfa_secret:
        qr_code = generate_mfa_qr_code(current_user.mfa_secret, current_user.username)
    
    return render_template('mfa_setup.html', user=current_user, qr_code=qr_code)

@auth_bp.route('/security/events')
@login_required
def security_events():
    """View security events for the current user"""
    user_events = security_events.get(current_user.id, [])
    return render_template('security_events.html', events=user_events)

@auth_bp.route('/security/sessions')
@login_required
def active_sessions():
    """View and manage active sessions"""
    # This would typically query a database table
    # For now, we'll show a simplified view
    return render_template('active_sessions.html', user=current_user)

@auth_bp.route('/register', methods=['GET', 'POST'])
@device_only_required
def register():
    """Account creation - LOCAL DEVICE ONLY for security"""
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email', '').strip()
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Validation
        errors = []
        
        if not username or len(username) < 3:
            errors.append('Username must be at least 3 characters long.')
        
        if not password or len(password) < 8:
            errors.append('Password must be at least 8 characters long.')
            
        # Enhanced password requirements
        if password:
            if not any(c.isupper() for c in password):
                errors.append('Password must contain at least one uppercase letter.')
            if not any(c.islower() for c in password):
                errors.append('Password must contain at least one lowercase letter.')
            if not any(c.isdigit() for c in password):
                errors.append('Password must contain at least one number.')
        
        if password != confirm_password:
            errors.append('Passwords do not match.')
        
        # Check if username already exists
        if User.query.filter(User.username.ilike(username)).first():
            errors.append('Username already exists.')
        
        # Check if email already exists (if provided)
        if email and User.query.filter(User.email.ilike(email)).first():
            errors.append('Email already registered.')
        
        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('login.html', show_register=True)
        
        # Create new user with enhanced security
        try:
            new_user = User()
            new_user.username = username
            new_user.email = email if email else None
            new_user.set_password(password)
            new_user.device_id = generate_device_id()  # Tie to specific device
            
            db.session.add(new_user)
            db.session.commit()
            
            flash('Account created successfully! Please log in.', 'success')
            log_user_action(new_user.id, f"New user registered: {username} (LOCAL DEVICE)")
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            db.session.rollback()
            flash('Account creation failed. Please try again.', 'error')
            log_user_action(None, f"Registration failed for {username}: {str(e)}")
    
    return render_template('login.html', show_register=True)

def generate_device_id():
    """Generate a unique device identifier"""
    import platform
    import uuid
    
    # Create device fingerprint from system info
    system_info = f"{platform.node()}-{platform.system()}-{platform.processor()}"
    mac_address = hex(uuid.getnode())
    
    # Hash the combined info for privacy
    device_string = f"{system_info}-{mac_address}"
    device_hash = hashlib.sha256(device_string.encode()).hexdigest()[:32]
    
    return device_hash

@auth_bp.route('/logout')
@login_required
def logout():
    user_id = current_user.id
    username = current_user.username
    
    # Invalidate current session token
    session_token = session.get('session_token')
    if session_token:
        session_manager.invalidate_session(session_token)
    
    # Clear Flask session
    session.clear()
    logout_user()
    
    log_user_action(user_id, f"User {username} logged out")
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))
