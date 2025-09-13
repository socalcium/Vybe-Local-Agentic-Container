"""
Enhanced Security Middleware for Vybe Application
Handles security headers, HTTPS redirection, threat detection, and advanced security features
"""

from flask import request, redirect, url_for, g, jsonify, current_app
from functools import wraps
import re
import ipaddress
import unicodedata
from urllib.parse import urlparse
import time
import json
import logging
import collections
from collections import defaultdict, deque
from functools import wraps
from flask import request, jsonify, g
import threading
import hashlib
import mimetypes
import os
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime, timedelta

# Configure logging
logger = logging.getLogger(__name__)


class ThreatDetector:
    """Advanced threat detection system"""
    
    def __init__(self):
        self.suspicious_patterns = [
            # SQL Injection patterns
            r"(?i)(union\s+select|or\s+1\s*=\s*1|drop\s+table|insert\s+into|delete\s+from)",
            # XSS patterns
            r"(?i)(<script|javascript:|vbscript:|onload\s*=|onerror\s*=|onclick\s*=)",
            # Path traversal
            r"(\.\./|\.\.\backslash|%2e%2e%2f|%2e%2e%5c)",
            # Command injection
            r"(?i)(;|\||\$\(|`|<\(|>\(|\|\||&&)",
            # LDAP injection
            r"(\*|\)|\(|\|\||&)",
            # XXE patterns
            r"(?i)(<!entity|<!doctype.*\[|%\w+;)",
        ]
        
        self.compiled_patterns = [re.compile(pattern) for pattern in self.suspicious_patterns]
        
        # Threat scoring thresholds
        self.threat_thresholds = {
            'low': 1,
            'medium': 3,
            'high': 5,
            'critical': 8
        }
        
        # Track threat attempts by IP - use bounded deque to prevent memory leak
        self.threat_attempts = collections.deque(maxlen=1000)
        self.blocked_ips = set()
        self.lock = threading.Lock()
    
    def analyze_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze request for threats and return threat assessment"""
        threat_score = 0
        detected_threats = []
        
        # Analyze all request data
        all_data = []
        
        # Add URL and query parameters
        if request_data.get('url'):
            all_data.append(request_data['url'])
        if request_data.get('query_params'):
            all_data.extend([str(v) for v in request_data['query_params'].values()])
        
        # Add form data
        if request_data.get('form_data'):
            all_data.extend([str(v) for v in request_data['form_data'].values()])
        
        # Add headers (check for suspicious values)
        if request_data.get('headers'):
            all_data.extend([str(v) for v in request_data['headers'].values()])
        
        # Check each data point against threat patterns
        for data in all_data:
            if isinstance(data, (str, bytes)):
                data_str = str(data)
                
                # Normalize Unicode to prevent obfuscation attacks
                normalized_data = unicodedata.normalize('NFKC', data_str)
                
                # Check both original and normalized data
                for check_data in [data_str, normalized_data]:
                    for i, pattern in enumerate(self.compiled_patterns):
                        if pattern.search(check_data):
                            threat_type = self._get_threat_type(i)
                            threat_score += self._get_threat_score(threat_type)
                            detected_threats.append({
                                'type': threat_type,
                                'pattern_index': i,
                                'data_sample': check_data[:100],  # First 100 chars for analysis
                                'normalized': check_data != data_str  # Flag if normalization changed the data
                            })
        
        # Assess threat level
        threat_level = self._assess_threat_level(threat_score)
        
        return {
            'threat_score': threat_score,
            'threat_level': threat_level,
            'detected_threats': detected_threats,
            'should_block': threat_level in ['high', 'critical']
        }
    
    def _get_threat_type(self, pattern_index: int) -> str:
        """Get threat type based on pattern index"""
        threat_types = [
            'sql_injection',
            'xss',
            'path_traversal', 
            'command_injection',
            'ldap_injection',
            'xxe'
        ]
        return threat_types[pattern_index] if pattern_index < len(threat_types) else 'unknown'
    
    def _get_threat_score(self, threat_type: str) -> int:
        """Get threat score based on type"""
        scores = {
            'sql_injection': 3,
            'xss': 2,
            'path_traversal': 2,
            'command_injection': 4,
            'ldap_injection': 3,
            'xxe': 3,
            'unknown': 1
        }
        return scores.get(threat_type, 1)
    
    def _assess_threat_level(self, score: int) -> str:
        """Assess threat level based on score"""
        if score >= self.threat_thresholds['critical']:
            return 'critical'
        elif score >= self.threat_thresholds['high']:
            return 'high'
        elif score >= self.threat_thresholds['medium']:
            return 'medium'
        elif score >= self.threat_thresholds['low']:
            return 'low'
        else:
            return 'none'
    
    def record_threat_attempt(self, ip_address: str, threat_assessment: Dict[str, Any]):
        """Record a threat attempt for tracking using bounded deque"""
        with self.lock:
            # Add new attempt to the deque
            self.threat_attempts.append({
                'ip_address': ip_address,
                'timestamp': datetime.utcnow(),
                'assessment': threat_assessment
            })
            
            # Check if IP should be blocked
            if self._should_block_ip(ip_address):
                self.blocked_ips.add(ip_address)
                logger.warning(f"IP {ip_address} blocked due to repeated threat attempts")
    
    def _should_block_ip(self, ip_address: str) -> bool:
        """Determine if IP should be blocked based on threat history"""
        # Count attempts from this IP in the last hour
        cutoff = datetime.utcnow() - timedelta(hours=1)
        recent_attempts = [
            attempt for attempt in self.threat_attempts
            if (attempt['ip_address'] == ip_address and 
                attempt['timestamp'] > cutoff)
        ]
        
        # Block if more than 5 medium+ threats in last hour
        medium_plus_threats = sum(
            1 for attempt in recent_attempts
            if attempt['assessment']['threat_level'] in ['medium', 'high', 'critical']
        )
        
        return medium_plus_threats >= 5
    
    def is_ip_blocked(self, ip_address: str) -> bool:
        """Check if IP is currently blocked"""
        return ip_address in self.blocked_ips


class SecurityMiddleware:
    """Enhanced security middleware for Flask application"""
    
    def __init__(self, app=None):
        self.app = app
        self.threat_detector = ThreatDetector()
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize enhanced security middleware with Flask app"""
        from ..config import Config
        
        self.config = Config
        
        # Initialize global tracking variables
        global _rate_limit_storage, _rate_limit_lock, _user_behavior_tracking
        _rate_limit_storage = defaultdict(deque)
        _rate_limit_lock = threading.Lock()
        _user_behavior_tracking = defaultdict(lambda: {
            'first_seen': datetime.utcnow(),
            'last_seen': datetime.utcnow(),
            'request_count': 0,
            'failed_logins': 0,
            'suspicious_activity': 0,
            'last_request_time': time.time()
        })
        
        # Add security headers to all responses
        app.after_request(self.add_security_headers)
        
        # Add threat detection
        app.before_request(self.detect_threats)
        
        # Add HTTPS redirection if enabled
        if Config.FORCE_HTTPS:
            app.before_request(self.force_https)
        
        # Add HTTPS redirection if enabled
        if Config.FORCE_HTTPS:
            app.before_request(self.force_https)
        
        # Add rate limiting setup (if flask-limiter is available)
        try:
            from flask_limiter import Limiter
            from flask_limiter.util import get_remote_address
            
            self.limiter = Limiter(
                key_func=get_remote_address,
                app=app,
                default_limits=[Config.RATELIMIT_DEFAULT],
                storage_uri=Config.RATELIMIT_STORAGE_URL,
                headers_enabled=Config.RATELIMIT_HEADERS_ENABLED
            )
            app.limiter = self.limiter
            
        except ImportError:
            print("⚠️  flask-limiter not installed - rate limiting disabled")
            self.limiter = None
    
    def add_security_headers(self, response):
        """Add security headers to response"""
        
        # Add configured security headers
        for header, value in self.config.SECURITY_HEADERS.items():
            response.headers[header] = value
        
        # Enhanced Content Security Policy
        csp_policy = self._build_csp_policy()
        response.headers['Content-Security-Policy'] = csp_policy
        
        # Additional security headers
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        
        # Conditional headers based on HTTPS
        if request.is_secure or self.config.FORCE_HTTPS:
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
        
        # Add additional security headers
        response.headers['Server'] = 'Vybe AI Assistant'  # Hide server details
        
        # Prevent caching of sensitive endpoints
        if self._is_sensitive_endpoint(request.endpoint):
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
        
        return response
    
    def detect_threats(self):
        """Detect and analyze threats in incoming requests"""
        # Check if IP is already blocked
        client_ip = self._get_client_ip()
        if self.threat_detector.is_ip_blocked(client_ip):
            return jsonify({
                'error': 'Access denied',
                'message': 'Your IP address has been temporarily blocked due to suspicious activity'
            }), 403
        
        # Analyze current request for threats
        request_data = {
            'url': request.url,
            'method': request.method,
            'headers': dict(request.headers),
            'query_params': dict(request.args),
            'form_data': dict(request.form) if request.form else {}
        }
        
        threat_assessment = self.threat_detector.analyze_request(request_data)
        
        # If threats detected, log and potentially block
        if threat_assessment['threat_level'] != 'none':
            logger.warning(f"Threat detected from {client_ip}: {threat_assessment}")
            
            # Record the threat attempt
            self.threat_detector.record_threat_attempt(client_ip, threat_assessment)
            
            # Block critical/high threats immediately
            if threat_assessment['should_block']:
                return jsonify({
                    'error': 'Security violation detected',
                    'message': 'Request blocked due to security policy violation'
                }), 403
    
    def _get_client_ip(self) -> str:
        """Get the real client IP address"""
        # Check for forwarded headers (in case of proxy/load balancer)
        forwarded_ips = [
            request.headers.get('X-Forwarded-For'),
            request.headers.get('X-Real-IP'),
            request.headers.get('CF-Connecting-IP'),  # Cloudflare
            request.remote_addr
        ]
        
        for ip in forwarded_ips:
            if ip:
                # Handle comma-separated IPs (X-Forwarded-For)
                first_ip = ip.split(',')[0].strip()
                if self._is_valid_ip(first_ip):
                    return first_ip
        
        return request.remote_addr or 'unknown'
    
    def _is_valid_ip(self, ip: str) -> bool:
        """Validate IP address format"""
        try:
            ipaddress.ip_address(ip)
            return True
        except ValueError:
            return False
    
    def force_https(self):
        """Force HTTPS redirection if enabled"""
        if not request.is_secure and request.url.startswith('http://'):
            # Skip HTTPS redirection for localhost/development
            if self._is_localhost():
                return
            
            # Redirect to HTTPS
            url = request.url.replace('http://', 'https://', 1)
            return redirect(url, code=301)
    
    def _is_sensitive_endpoint(self, endpoint):
        """Check if endpoint contains sensitive data"""
        if not endpoint:
            return False
            
        sensitive_patterns = [
            r'.*login.*',
            r'.*password.*',
            r'.*auth.*',
            r'.*admin.*',
            r'.*config.*',
            r'.*settings.*',
            r'.*api.*'
        ]
        
        for pattern in sensitive_patterns:
            if re.match(pattern, endpoint, re.IGNORECASE):
                return True
        
        return False
    
    def _is_localhost(self):
        """Check if request is from localhost"""
        try:
            host = request.headers.get('Host', '').split(':')[0]
            if host in ['localhost', '127.0.0.1', '::1']:
                return True
            
            # Check if it's a private IP
            try:
                ip = ipaddress.ip_address(host)
                return ip.is_private or ip.is_loopback
            except ValueError:
                return False
                
        except Exception:
            return False

    def _build_csp_policy(self) -> str:
        """Build Content Security Policy for the application"""
        csp_directives = {
            'default-src': ["'self'"],
            'script-src': [
                "'self'",
                "'unsafe-inline'",  # Required for inline scripts in templates
                "'unsafe-eval'",    # Required for some JavaScript libraries
                "https://cdn.jsdelivr.net",  # For external libraries
                "https://unpkg.com"          # For external libraries
            ],
            'style-src': [
                "'self'",
                "'unsafe-inline'",  # Required for inline styles
                "https://fonts.googleapis.com",
                "https://cdn.jsdelivr.net"
            ],
            'font-src': [
                "'self'",
                "https://fonts.gstatic.com",
                "https://cdn.jsdelivr.net"
            ],
            'img-src': [
                "'self'",
                "data:",
                "blob:",
                "https:"
            ],
            'connect-src': [
                "'self'",
                "ws://localhost:*",  # WebSocket connections
                "wss://localhost:*",
                "http://localhost:*",
                "https://localhost:*"
            ],
            'media-src': [
                "'self'",
                "blob:",
                "data:"
            ],
            'object-src': ["'none'"],
            'base-uri': ["'self'"],
            'form-action': ["'self'"],
            'frame-ancestors': ["'none'"],
            'upgrade-insecure-requests': []
        }
        
        # Build CSP string
        csp_parts = []
        for directive, sources in csp_directives.items():
            if sources:
                csp_parts.append(f"{directive} {' '.join(sources)}")
            else:
                csp_parts.append(directive)
        
        return '; '.join(csp_parts)


def require_https(f):
    """Decorator to require HTTPS for specific routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not request.is_secure and not _is_localhost_request():
            # Redirect to HTTPS version
            return redirect(request.url.replace('http://', 'https://', 1), code=301)
        return f(*args, **kwargs)
    return decorated_function


def require_secure_headers(f):
    """Decorator to add extra security headers to specific routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        response = f(*args, **kwargs)
        
        # Add extra security headers
        if hasattr(response, 'headers'):
            response.headers['X-Frame-Options'] = 'DENY'
            response.headers['X-Content-Type-Options'] = 'nosniff'
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        
        return response
    return decorated_function


def validate_origin(f):
    """Decorator to validate request origin for sensitive operations"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check Origin header for AJAX requests
        origin = request.headers.get('Origin')
        referer = request.headers.get('Referer')
        host = request.headers.get('Host')
        
        if origin:
            origin_host = urlparse(origin).netloc
            if origin_host != host:
                from flask import jsonify
                return jsonify({'error': 'Invalid origin'}), 403
        
        return f(*args, **kwargs)
    return decorated_function


def _is_localhost_request():
    """Helper to check if request is from localhost"""
    try:
        host = request.headers.get('Host', '').split(':')[0]
        return host in ['localhost', '127.0.0.1', '::1']
    except Exception:
        return False


def get_client_ip():
    """Get the real client IP address"""
    # Check for forwarded headers (common in reverse proxy setups)
    forwarded_for = request.headers.get('X-Forwarded-For')
    if forwarded_for:
        # Take the first IP in the chain
        return forwarded_for.split(',')[0].strip()
    
    real_ip = request.headers.get('X-Real-IP')
    if real_ip:
        return real_ip
    
    # Fallback to Flask's remote_addr
    return request.remote_addr


def is_safe_url(target):
    """Check if a URL is safe for redirects"""
    from urllib.parse import urlparse, urljoin
    from flask import request
    
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc


# Content Security Policy helpers
def generate_nonce():
    """Generate a random nonce for CSP"""
    import secrets
    import base64
    
    nonce_bytes = secrets.token_bytes(16)
    return base64.b64encode(nonce_bytes).decode('utf-8')


def csp_nonce():
    """Get or generate CSP nonce for current request"""
    if not hasattr(g, 'csp_nonce'):
        g.csp_nonce = generate_nonce()
    return g.csp_nonce


# Input validation and file upload security
class InputValidator:
    """Input validation utilities for security hardening"""
    
    # Allowed file extensions and their MIME types
    ALLOWED_EXTENSIONS = {
        'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'svg', 'doc', 'docx',
        'xls', 'xlsx', 'ppt', 'pptx', 'csv', 'json', 'xml', 'md', 'html',
        'css', 'js', 'py', 'java', 'cpp', 'c', 'h', 'sql', 'zip', 'rar',
        'mp3', 'mp4', 'avi', 'mov', 'wav', 'flac', 'ogg'
    }
    
    ALLOWED_MIME_TYPES = {
        'text/plain', 'text/html', 'text/css', 'text/javascript',
        'application/pdf', 'application/json', 'application/xml',
        'application/zip', 'application/x-zip-compressed',
        'image/png', 'image/jpeg', 'image/gif', 'image/svg+xml',
        'audio/mpeg', 'audio/wav', 'audio/flac', 'audio/ogg',
        'video/mp4', 'video/avi', 'video/quicktime',
        'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/vnd.ms-powerpoint', 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        'text/csv', 'text/markdown'
    }
    
    # Maximum file sizes (in bytes)
    MAX_FILE_SIZES = {
        'image': 10 * 1024 * 1024,  # 10MB for images
        'document': 50 * 1024 * 1024,  # 50MB for documents
        'audio': 100 * 1024 * 1024,  # 100MB for audio
        'video': 500 * 1024 * 1024,  # 500MB for video
        'default': 25 * 1024 * 1024  # 25MB default
    }
    
    # Dangerous file patterns
    DANGEROUS_PATTERNS = [
        r'\.(exe|bat|cmd|com|pif|scr|vbs|js|jar|msi|dll|sys|drv)$',
        r'\.(php|asp|aspx|jsp|cgi|pl|py|sh|bash)$',
        r'\.(lnk|url|reg|inf|ini|cfg|conf)$'
    ]
    
    @classmethod
    def validate_file_upload(cls, file, allowed_extensions=None, max_size=None):
        """Validate file upload for security"""
        if not file or not file.filename:
            return False, "No file provided"
        
        # Check file extension
        filename = file.filename.lower()
        extension = filename.rsplit('.', 1)[1] if '.' in filename else ''
        
        if allowed_extensions is None:
            allowed_extensions = cls.ALLOWED_EXTENSIONS
        
        if extension not in allowed_extensions:
            return False, f"File extension '{extension}' not allowed"
        
        # Check for dangerous patterns
        for pattern in cls.DANGEROUS_PATTERNS:
            if re.search(pattern, filename, re.IGNORECASE):
                return False, f"Dangerous file pattern detected: {filename}"
        
        # Check file size
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)  # Reset file pointer
        
        if max_size is None:
            # Determine max size based on file type
            if extension in {'png', 'jpg', 'jpeg', 'gif', 'svg'}:
                max_size = cls.MAX_FILE_SIZES['image']
            elif extension in {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx'}:
                max_size = cls.MAX_FILE_SIZES['document']
            elif extension in {'mp3', 'wav', 'flac', 'ogg'}:
                max_size = cls.MAX_FILE_SIZES['audio']
            elif extension in {'mp4', 'avi', 'mov'}:
                max_size = cls.MAX_FILE_SIZES['video']
            else:
                max_size = cls.MAX_FILE_SIZES['default']
        
        if file_size > max_size:
            return False, f"File size {file_size} exceeds maximum allowed size {max_size}"
        
        # Check MIME type
        mime_type, _ = mimetypes.guess_type(filename)
        if mime_type and mime_type not in cls.ALLOWED_MIME_TYPES:
            return False, f"MIME type '{mime_type}' not allowed"
        
        return True, "File validation passed"
    
    @classmethod
    def sanitize_filename(cls, filename):
        """Sanitize filename for safe storage"""
        if not filename:
            return None
        
        # Remove path traversal attempts
        filename = os.path.basename(filename)
        
        # Remove or replace dangerous characters
        dangerous_chars = ['<', '>', ':', '"', '|', '?', '*', '\\', '/']
        for char in dangerous_chars:
            filename = filename.replace(char, '_')
        
        # Limit length
        if len(filename) > 255:
            name, ext = os.path.splitext(filename)
            filename = name[:255-len(ext)] + ext
        
        return filename
    
    @classmethod
    def validate_api_input(cls, data, required_fields=None, optional_fields=None, field_types=None):
        """Validate API input data"""
        if not isinstance(data, dict):
            return False, "Input must be a JSON object"
        
        # Check required fields
        if required_fields:
            for field in required_fields:
                if field not in data:
                    return False, f"Required field '{field}' is missing"
        
        # Check field types
        if field_types:
            for field, expected_type in field_types.items():
                if field in data:
                    if not isinstance(data[field], expected_type):
                        return False, f"Field '{field}' must be of type {expected_type.__name__}"
        
        return True, "Input validation passed"
    
    @classmethod
    def sanitize_string(cls, text, max_length=1000):
        """Sanitize string input"""
        if not isinstance(text, str):
            return None
        
        # Remove null bytes and control characters
        text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\r\t')
        
        # Limit length
        if len(text) > max_length:
            text = text[:max_length]
        
        return text.strip()
    
    @classmethod
    def validate_url(cls, url):
        """Validate URL for security"""
        if not url:
            return False, "URL is required"
        
        try:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return False, "Invalid URL format"
            
            # Check for dangerous protocols
            if parsed.scheme not in ['http', 'https', 'ftp']:
                return False, f"Dangerous protocol: {parsed.scheme}"
            
            # Check for localhost/private IP access
            if parsed.netloc in ['localhost', '127.0.0.1', '::1']:
                return False, "Localhost access not allowed"
            
            return True, "URL validation passed"
            
        except Exception as e:
            return False, f"URL validation error: {str(e)}"


def validate_file_upload(f):
    """Decorator to validate file uploads"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'file' in request.files:
            file = request.files['file']
            is_valid, message = InputValidator.validate_file_upload(file)
            
            if not is_valid:
                from flask import jsonify
                return jsonify({'error': message}), 400
        
        return f(*args, **kwargs)
    return decorated_function


def validate_api_input(required_fields=None, optional_fields=None, field_types=None):
    """Decorator to validate API input"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if request.is_json:
                data = request.get_json()
                is_valid, message = InputValidator.validate_api_input(
                    data, required_fields, optional_fields, field_types
                )
                
                if not is_valid:
                    from flask import jsonify
                    return jsonify({'error': message}), 400
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def sanitize_input(f):
    """Decorator to sanitize input data"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Sanitize form data
        if request.form:
            for key, value in request.form.items():
                if isinstance(value, str):
                    request.form[key] = InputValidator.sanitize_string(value)
        
        # Sanitize JSON data
        if request.is_json:
            data = request.get_json()
            if isinstance(data, dict):
                for key, value in data.items():
                    if isinstance(value, str):
                        data[key] = InputValidator.sanitize_string(value)
        
        return f(*args, **kwargs)
    return decorated_function

"""
Security middleware for rate limiting and other security features.
"""
import time
from collections import defaultdict, deque
from functools import wraps
from flask import request, jsonify, g
import threading
import hashlib
from typing import Dict, Any, Optional, Tuple

# Global rate limiting storage with enhanced tracking
class RateLimitStorage:
    """Thread-safe rate limiting storage"""
    
    def __init__(self):
        self._storage = defaultdict(lambda: deque())
        self._user_behavior = defaultdict(lambda: {
            'request_count': 0,
            'last_request_time': 0,
            'suspicious_activity': 0,
            'blocked_until': 0,
            'trust_score': 100  # Start with high trust
        })
        self._lock = threading.Lock()
    
    def get_storage(self):
        return self._storage
    
    def get_user_behavior(self):
        return self._user_behavior
    
    def get_lock(self):
        return self._lock

# Singleton instance
_rate_limit_storage_instance = None
_storage_lock = threading.Lock()

def get_rate_limit_storage():
    """Get thread-safe singleton rate limit storage"""
    global _rate_limit_storage_instance
    if _rate_limit_storage_instance is None:
        with _storage_lock:
            if _rate_limit_storage_instance is None:
                _rate_limit_storage_instance = RateLimitStorage()
    return _rate_limit_storage_instance

class AdaptiveRateLimiter:
    """Enhanced rate limiter with adaptive thresholds based on user behavior"""
    
    def __init__(self):
        self.base_limits = {
            'normal': {'requests': 100, 'window': 60},
            'chat': {'requests': 10, 'window': 60},
            'download': {'requests': 5, 'window': 300},
            'auth': {'requests': 5, 'window': 300},
            'admin': {'requests': 1000, 'window': 60}
        }
        
        self.trust_thresholds = {
            'high': 80,    # 80-100: High trust, normal limits
            'medium': 50,  # 50-79: Medium trust, reduced limits
            'low': 20,     # 20-49: Low trust, strict limits
            'blocked': 0   # 0-19: Blocked, minimal access
        }
    
    def get_user_key(self, request) -> str:
        """Generate a unique key for rate limiting based on user identity"""
        # Try to get user ID if authenticated
        user_id = getattr(request, 'user_id', None)
        if user_id:
            return f"user_{user_id}"
        
        # Fall back to IP address with additional fingerprinting
        ip = request.remote_addr or 'unknown'
        user_agent = request.headers.get('User-Agent', '')
        
        # Create a hash of IP + User-Agent for better identification
        fingerprint = hashlib.md5(f"{ip}:{user_agent}".encode()).hexdigest()
        return f"ip_{fingerprint}"
    
    def calculate_trust_score(self, user_key: str) -> int:
        """Calculate trust score based on user behavior"""
        behavior = _user_behavior_tracking[user_key]
        
        # Base score starts at 100
        score = 100
        
        # Reduce score for suspicious activity
        suspicious_count = behavior.get('suspicious_activity', 0)
        if isinstance(suspicious_count, (int, float)):
            score -= int(suspicious_count * 10)
        
        # Reduce score for high request frequency
        request_count = behavior.get('request_count', 0)
        if isinstance(request_count, (int, float)) and request_count > 1000:
            score -= 20
        
        # Increase score for good behavior over time
        last_request = behavior.get('last_request_time', time.time())
        if isinstance(last_request, (int, float)):
            time_since_last = time.time() - last_request
            if time_since_last > 3600:  # 1 hour of good behavior
                score = min(100, score + 5)
        
        return max(0, score)
    
    def get_adaptive_limits(self, user_key: str, endpoint_type: str = 'normal') -> Dict[str, int]:
        """Get adaptive rate limits based on user trust score"""
        trust_score = self.calculate_trust_score(user_key)
        base_limit = self.base_limits[endpoint_type].copy()
        
        # Adjust limits based on trust score
        if trust_score >= self.trust_thresholds['high']:
            # High trust: normal limits
            pass
        elif trust_score >= self.trust_thresholds['medium']:
            # Medium trust: reduce limits by 25%
            base_limit['requests'] = int(base_limit['requests'] * 0.75)
        elif trust_score >= self.trust_thresholds['low']:
            # Low trust: reduce limits by 50%
            base_limit['requests'] = int(base_limit['requests'] * 0.5)
        else:
            # Blocked: minimal access
            base_limit['requests'] = 1
            base_limit['window'] = 300  # 5 minutes
        
        return base_limit
    
    def track_user_behavior(self, user_key: str, request_data: Dict[str, Any]):
        """Track user behavior for adaptive rate limiting"""
        behavior = _user_behavior_tracking[user_key]
        current_time = time.time()
        
        # Update request count
        current_count = behavior.get('request_count', 0)
        if isinstance(current_count, (int, float)) and not isinstance(current_count, bool):
            behavior['request_count'] = int(current_count) + 1
        else:
            behavior['request_count'] = 1
            
        behavior['last_request_time'] = current_time
        
        # Detect suspicious patterns
        suspicious_patterns = self._detect_suspicious_patterns(request_data)
        if suspicious_patterns:
            current_suspicious = behavior.get('suspicious_activity', 0)
            if isinstance(current_suspicious, (int, float)) and not isinstance(current_suspicious, bool):
                behavior['suspicious_activity'] = int(current_suspicious) + len(suspicious_patterns)
            else:
                behavior['suspicious_activity'] = len(suspicious_patterns)
        
        # Update trust score
        behavior['trust_score'] = self.calculate_trust_score(user_key)
    
    def _detect_suspicious_patterns(self, request_data: Dict[str, Any]) -> list:
        """Detect suspicious request patterns"""
        patterns = []
        
        # Check for rapid successive requests
        headers = request_data.get('headers', {})
        if isinstance(headers, dict):
            user_agent = headers.get('User-Agent', '')
            if not user_agent or user_agent == 'python-requests':
                patterns.append('missing_user_agent')
        
        # Check for unusual request patterns
        method = request_data.get('method', 'GET')
        if isinstance(method, str) and method not in ['GET', 'POST', 'PUT', 'DELETE']:
            patterns.append('unusual_method')
        
        return patterns
    
    def is_blocked(self, user_key: str) -> bool:
        """Check if user is currently blocked"""
        storage = get_rate_limit_storage()
        behavior = storage.get_user_behavior()[user_key]
        return time.time() < behavior['blocked_until']

# Global adaptive rate limiter instance
adaptive_limiter = AdaptiveRateLimiter()

def adaptive_rate_limit(endpoint_type: str = 'normal'):
    """
    Enhanced rate limiting decorator with adaptive thresholds.
    
    Args:
        endpoint_type: Type of endpoint ('normal', 'chat', 'download', 'auth', 'admin')
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_key = adaptive_limiter.get_user_key(request)
            
            # Check if user is blocked
            if adaptive_limiter.is_blocked(user_key):
                return jsonify({
                    'success': False,
                    'error': 'Access temporarily blocked due to suspicious activity',
                    'error_type': 'access_blocked'
                }), 403
            
            # Get adaptive limits for this user
            limits = adaptive_limiter.get_adaptive_limits(user_key, endpoint_type)
            
            current_time = time.time()
            storage = get_rate_limit_storage()
            
            with storage.get_lock():
                # Clean old entries
                while (storage.get_storage()[user_key] and 
                       storage.get_storage()[user_key][0] < current_time - limits['window']):
                    storage.get_storage()[user_key].popleft()
                
                # Check if limit exceeded
                if len(storage.get_storage()[user_key]) >= limits['requests']:
                    # Track this as suspicious behavior
                    request_dict = {
                        'method': request.method,
                        'headers': dict(request.headers),
                        'url': request.url
                    }
                    adaptive_limiter.track_user_behavior(user_key, request_dict)
                    
                    return jsonify({
                        'success': False,
                        'error': f'Rate limit exceeded. Maximum {limits["requests"]} requests per {limits["window"]} seconds.',
                        'error_type': 'rate_limit_exceeded',
                        'retry_after': limits['window']
                    }), 429
                
                # Add current request
                storage.get_storage()[user_key].append(current_time)
                
                # Track user behavior
                request_dict = {
                    'method': request.method,
                    'headers': dict(request.headers),
                    'url': request.url
                }
                adaptive_limiter.track_user_behavior(user_key, request_dict)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def rate_limit(max_requests=60, window_seconds=60, key_func=None):
    """
    Legacy rate limiting decorator for backward compatibility.
    
    Args:
        max_requests: Maximum number of requests allowed in the time window
        window_seconds: Time window in seconds
        key_func: Function to generate rate limit key (defaults to IP address)
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Generate rate limit key
            if key_func:
                key = key_func()
            else:
                key = request.remote_addr or 'unknown'
            
            current_time = time.time()
            
            with _rate_limit_lock:
                # Clean old entries
                while _rate_limit_storage[key] and _rate_limit_storage[key][0] < current_time - window_seconds:
                    _rate_limit_storage[key].popleft()
                
                # Check if limit exceeded
                if len(_rate_limit_storage[key]) >= max_requests:
                    return jsonify({
                        'success': False,
                        'error': f'Rate limit exceeded. Maximum {max_requests} requests per {window_seconds} seconds.',
                        'error_type': 'rate_limit_exceeded'
                    }), 429
                
                # Add current request
                _rate_limit_storage[key].append(current_time)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def chat_rate_limit():
    """Specific rate limiting for chat endpoints (more restrictive)"""
    return adaptive_rate_limit(endpoint_type='chat')

def api_rate_limit():
    """General API rate limiting with adaptive thresholds"""
    return adaptive_rate_limit(endpoint_type='normal')

def download_rate_limit():
    """Rate limiting for download endpoints"""
    return adaptive_rate_limit(endpoint_type='download')

def auth_rate_limit():
    """Rate limiting for authentication endpoints"""
    return adaptive_rate_limit(endpoint_type='auth')

def admin_rate_limit():
    """Rate limiting for admin endpoints"""
    return adaptive_rate_limit(endpoint_type='admin')

def cleanup_rate_limits():
    """Clean up old rate limit entries and user behavior data (call periodically)"""
    current_time = time.time()
    with _rate_limit_lock:
        # Clean rate limit storage
        for key in list(_rate_limit_storage.keys()):
            # Remove entries older than 1 hour
            while _rate_limit_storage[key] and _rate_limit_storage[key][0] < current_time - 3600:
                _rate_limit_storage[key].popleft()
            # Remove empty keys
            if not _rate_limit_storage[key]:
                del _rate_limit_storage[key]
        
        # Clean user behavior tracking (keep for 24 hours)
        for key in list(_user_behavior_tracking.keys()):
            behavior = _user_behavior_tracking[key]
            last_request = behavior.get('last_request_time', current_time)
            if isinstance(last_request, (int, float)) and current_time - last_request > 86400:  # 24 hours
                del _user_behavior_tracking[key]

def get_rate_limit_info(key=None):
    """Get current rate limit information for debugging"""
    if key is None:
        key = adaptive_limiter.get_user_key(request)
    
    with _rate_limit_lock:
        current_time = time.time()
        
        # Get rate limit info
        while _rate_limit_storage[key] and _rate_limit_storage[key][0] < current_time - 60:
            _rate_limit_storage[key].popleft()
        
        # Get user behavior info
        behavior = _user_behavior_tracking[key]
        trust_score = adaptive_limiter.calculate_trust_score(key)
        
        return {
            'current_requests': len(_rate_limit_storage[key]),
            'window_start': current_time - 60,
            'key': key,
            'trust_score': trust_score,
            'suspicious_activity': behavior['suspicious_activity'],
            'request_count': behavior['request_count'],
            'is_blocked': adaptive_limiter.is_blocked(key)
        }

def reset_user_trust(user_key: str):
    """Reset user trust score (admin function)"""
    with _rate_limit_lock:
        if user_key in _user_behavior_tracking:
            _user_behavior_tracking[user_key] = {
                'request_count': 0,
                'last_request_time': time.time(),
                'suspicious_activity': 0,
                'blocked_until': 0,
                'trust_score': 100
            }
        if user_key in _rate_limit_storage:
            _rate_limit_storage[user_key].clear()
