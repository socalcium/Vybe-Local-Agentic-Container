"""
Enhanced Error Management System for Vybe
Provides comprehensive error logging, monitoring, and debugging capabilities
"""

import os
import sys
import json
import traceback
import datetime
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from flask import request, session, current_app
import inspect

from ..logger import logger


class ErrorManager:
    """Advanced error management and debugging system"""
    
    def __init__(self, log_dir: Optional[Path] = None):
        # Set up error log directory
        if os.name == 'nt':  # Windows
            self.base_dir = Path(os.path.expanduser("~")) / "AppData" / "Local" / "Vybe AI Assistant"
        else:  # Linux/Mac
            self.base_dir = Path(os.path.expanduser("~")) / ".local" / "share" / "vybe-ai-assistant"
            
        self.log_dir = log_dir or self.base_dir / "logs"
        self.error_log_dir = self.log_dir / "errors"
        self.debug_log_dir = self.log_dir / "debug"
        
        # Create directories
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.error_log_dir.mkdir(parents=True, exist_ok=True)
        self.debug_log_dir.mkdir(parents=True, exist_ok=True)
        
        # Error tracking
        self.error_count = 0
        self.error_history = []
        self.debug_mode = os.getenv('VYBE_DEBUG', 'false').lower() == 'true'
        
        # Set up detailed error logger
        self.setup_error_logger()
        
        # Define sensitive keys that should be sanitized
        self.sensitive_keys = [
            'PASSWORD', 'API_KEY', 'SECRET_KEY', 'SECRET', 'TOKEN', 'AUTH', 
            'PRIVATE_KEY', 'CERT', 'CERTIFICATE', 'CREDENTIALS', 'CREDENTIAL',
            'SESSION_KEY', 'CSRF_TOKEN', 'COOKIE', 'OAUTH', 'JWT', 'BEARER',
            'PASSPHRASE', 'HASH', 'SALT', 'MFA_SECRET', 'TOTP_SECRET'
        ]
    
    def sanitize_data(self, data: Dict[str, Any], sensitive_keys: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Sanitize dictionary data by replacing values of sensitive keys with redacted placeholders
        
        Args:
            data: Dictionary containing data to sanitize
            sensitive_keys: List of sensitive key names (case-insensitive), defaults to self.sensitive_keys
            
        Returns:
            Sanitized dictionary with sensitive values replaced
        """
        if not isinstance(data, dict):
            return data
        
        # Use provided keys or default sensitive keys
        keys_to_sanitize = sensitive_keys or self.sensitive_keys
        
        # Convert to uppercase for case-insensitive matching
        sensitive_keys_upper = [key.upper() for key in keys_to_sanitize]
        
        sanitized_data = {}
        
        for key, value in data.items():
            key_upper = str(key).upper()
            
            # Check if this key should be sanitized
            should_sanitize = any(sensitive_key in key_upper for sensitive_key in sensitive_keys_upper)
            
            if should_sanitize:
                sanitized_data[key] = '***REDACTED***'
            elif isinstance(value, dict):
                # Recursively sanitize nested dictionaries
                sanitized_data[key] = self.sanitize_data(value, sensitive_keys)
            elif isinstance(value, list):
                # Handle lists that might contain dictionaries
                sanitized_data[key] = [
                    self.sanitize_data(item, sensitive_keys) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                sanitized_data[key] = value
        
        return sanitized_data
    
    def setup_error_logger(self):
        """Set up detailed error logging"""
        self.error_logger = logging.getLogger('vybe_errors')
        self.error_logger.setLevel(logging.ERROR)
        
        # Create file handler for errors
        error_file = self.error_log_dir / f"errors_{datetime.datetime.now().strftime('%Y%m%d')}.log"
        error_handler = logging.FileHandler(error_file)
        error_handler.setLevel(logging.ERROR)
        
        # Create detailed formatter
        error_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s - %(message)s'
        )
        error_handler.setFormatter(error_formatter)
        
        self.error_logger.addHandler(error_handler)
        
        # Debug logger
        self.debug_logger = logging.getLogger('vybe_debug')
        self.debug_logger.setLevel(logging.DEBUG)
        
        debug_file = self.debug_log_dir / f"debug_{datetime.datetime.now().strftime('%Y%m%d')}.log"
        debug_handler = logging.FileHandler(debug_file)
        debug_handler.setLevel(logging.DEBUG)
        debug_handler.setFormatter(error_formatter)
        
        self.debug_logger.addHandler(debug_handler)
    
    def log_error(self, error: Exception, context: Optional[Dict[str, Any]] = None, category: str = "general"):
        """Log an error with full context and debugging information"""
        self.error_count += 1
        
        # Get stack trace
        tb_str = ''.join(traceback.format_exception(type(error), error, error.__traceback__))
        
        # Get caller information
        frame = inspect.currentframe()
        caller_info = {}
        if frame and frame.f_back:
            caller_frame = frame.f_back
            caller_info = {
                'file': caller_frame.f_code.co_filename,
                'function': caller_frame.f_code.co_name,
                'line': caller_frame.f_lineno
            }
        
        # Sanitize context data before logging
        sanitized_context = self.sanitize_data(context or {})
        
        # Get system and request info and sanitize them
        system_info = self.sanitize_data(self.get_system_info())
        request_info = None
        if self.has_request_context():
            raw_request_info = self.get_request_info()
            request_info = self.sanitize_data(raw_request_info) if raw_request_info else None
        
        # Build error record
        error_record = {
            'timestamp': datetime.datetime.now().isoformat(),
            'error_id': f"ERR_{self.error_count:06d}",
            'category': category,
            'error_type': type(error).__name__,
            'error_message': str(error),
            'traceback': tb_str,
            'caller_info': caller_info,
            'context': sanitized_context,
            'system_info': system_info,
            'request_info': request_info
        }
        
        # Log to file
        self.error_logger.error(json.dumps(error_record, indent=2))
        
        # Keep in memory (limited)
        self.error_history.append(error_record)
        if len(self.error_history) > 100:  # Keep only last 100 errors
            self.error_history.pop(0)
        
        # Also log to main logger
        logger.error(f"[{category}] {type(error).__name__}: {str(error)}")
        
        return error_record
    
    def log_debug(self, message: str, data: Optional[Dict[str, Any]] = None, level: str = "DEBUG"):
        """Log debug information"""
        if not self.debug_mode:
            return
            
        # Get caller information
        frame = inspect.currentframe()
        caller_info = {}
        if frame and frame.f_back:
            caller_frame = frame.f_back
            caller_info = {
                'file': os.path.basename(caller_frame.f_code.co_filename),
                'function': caller_frame.f_code.co_name,
                'line': caller_frame.f_lineno
            }
        
        # Sanitize debug data before logging
        sanitized_data = self.sanitize_data(data or {})
        
        # Get request info and sanitize it
        request_info = None
        if self.has_request_context():
            raw_request_info = self.get_request_info()
            request_info = self.sanitize_data(raw_request_info) if raw_request_info else None
        
        debug_record = {
            'timestamp': datetime.datetime.now().isoformat(),
            'level': level,
            'message': message,
            'data': sanitized_data,
            'caller_info': caller_info,
            'request_info': request_info
        }
        
        self.debug_logger.debug(json.dumps(debug_record, indent=2))
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get current system information"""
        return {
            'python_version': sys.version,
            'platform': sys.platform,
            'cwd': os.getcwd(),
            'pid': os.getpid(),
            'memory_usage': self.get_memory_usage(),
            'environment_vars': {
                key: value for key, value in os.environ.items() 
                if key.startswith('VYBE_') or key in ['PATH', 'PYTHON_PATH']
            }
        }
    
    def get_request_info(self) -> Optional[Dict[str, Any]]:
        """Get current Flask request information"""
        if not self.has_request_context():
            return None
            
        try:
            return {
                'method': request.method,
                'url': request.url,
                'path': request.path,
                'remote_addr': request.remote_addr,
                'user_agent': request.headers.get('User-Agent', ''),
                'referrer': request.headers.get('Referer', ''),
                'content_type': request.headers.get('Content-Type', ''),
                'args': dict(request.args),
                'form_keys': list(request.form.keys()) if request.form else [],
                'session_id': session.get('user_id', 'anonymous') if session else 'no_session'
            }
        except Exception as e:
            return {'error': f"Could not get request info: {str(e)}"}
    
    def has_request_context(self) -> bool:
        """Check if we're in a Flask request context"""
        try:
            # This will raise RuntimeError if not in request context
            request.method
            return True
        except RuntimeError:
            return False
    
    def get_memory_usage(self) -> Dict[str, Any]:
        """Get memory usage information"""
        try:
            import psutil
            process = psutil.Process()
            memory_info = process.memory_info()
            return {
                'rss': memory_info.rss,  # Resident Set Size
                'vms': memory_info.vms,  # Virtual Memory Size
                'percent': process.memory_percent(),
                'available': psutil.virtual_memory().available
            }
        except ImportError:
            return {'error': 'psutil not available'}
        except Exception as e:
            return {'error': str(e)}
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of recent errors"""
        return {
            'total_errors': self.error_count,
            'recent_errors': len(self.error_history),
            'error_categories': self.get_error_categories(),
            'last_error': self.error_history[-1] if self.error_history else None,
            'debug_mode': self.debug_mode
        }
    
    def get_error_categories(self) -> Dict[str, int]:
        """Get count of errors by category"""
        categories = {}
        for error in self.error_history:
            category = error.get('category', 'unknown')
            categories[category] = categories.get(category, 0) + 1
        return categories
    
    def get_recent_errors(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent errors for debugging"""
        return self.error_history[-limit:]
    
    def clear_error_history(self):
        """Clear error history (useful for testing)"""
        self.error_history.clear()
        self.error_count = 0


# Global error manager instance
error_manager = ErrorManager()


def log_error(error: Exception, context: Optional[Dict[str, Any]] = None, category: str = "general") -> Dict[str, Any]:
    """Convenience function for logging errors"""
    return error_manager.log_error(error, context, category)


def log_debug(message: str, data: Optional[Dict[str, Any]] = None, level: str = "DEBUG"):
    """Convenience function for logging debug info"""
    error_manager.log_debug(message, data, level)


def handle_api_error(func):
    """Decorator to handle API errors consistently"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            error_record = log_error(e, {
                'function': func.__name__,
                'args': str(args)[:200],  # Limit arg logging
                'kwargs': str(kwargs)[:200]
            }, category="api_error")
            
            # Return error response
            from flask import jsonify
            return jsonify({
                'error': str(e),
                'error_id': error_record['error_id'],
                'category': 'api_error'
            }), 500
    
    return wrapper
