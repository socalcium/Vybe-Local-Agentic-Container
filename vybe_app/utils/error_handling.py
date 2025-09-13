#!/usr/bin/env python3
"""
Comprehensive Error Handling Utilities for Vybe AI Desktop Application
Provides centralized error handling, logging, and recovery mechanisms
"""

import logging
import traceback
import sys
import json
import time
from datetime import datetime
from typing import Dict, Any, List, Optional, Union, Callable, Type
from functools import wraps
from flask import jsonify, request, current_app
from werkzeug.exceptions import HTTPException
import threading
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)


class ErrorCode:
    """Standardized error codes for the application"""
    
    # General errors (1000-1999)
    UNKNOWN_ERROR = 1000
    INVALID_REQUEST = 1001
    AUTHENTICATION_FAILED = 1002
    AUTHORIZATION_FAILED = 1003
    RATE_LIMIT_EXCEEDED = 1004
    MAINTENANCE_MODE = 1005
    
    # Validation errors (2000-2999)
    VALIDATION_ERROR = 2000
    MISSING_FIELD = 2001
    INVALID_FORMAT = 2002
    OUT_OF_RANGE = 2003
    SECURITY_VIOLATION = 2004
    FILE_TOO_LARGE = 2005
    UNSUPPORTED_FILE_TYPE = 2006
    
    # Database errors (3000-3999)
    DATABASE_ERROR = 3000
    CONNECTION_ERROR = 3001
    QUERY_ERROR = 3002
    CONSTRAINT_VIOLATION = 3003
    DATA_NOT_FOUND = 3004
    DUPLICATE_ENTRY = 3005
    
    # AI/Model errors (4000-4999)
    MODEL_ERROR = 4000
    MODEL_NOT_FOUND = 4001
    MODEL_LOADING_ERROR = 4002
    INFERENCE_ERROR = 4003
    CONTEXT_TOO_LONG = 4004
    INVALID_PROMPT = 4005
    
    # File system errors (5000-5999)
    FILE_ERROR = 5000
    FILE_NOT_FOUND = 5001
    PERMISSION_DENIED = 5002
    DISK_FULL = 5003
    PATH_TRAVERSAL = 5004
    
    # Network errors (6000-6999)
    NETWORK_ERROR = 6000
    CONNECTION_TIMEOUT = 6001
    DNS_ERROR = 6002
    PROXY_ERROR = 6003
    SSL_ERROR = 6004
    
    # Configuration errors (7000-7999)
    CONFIG_ERROR = 7000
    MISSING_CONFIG = 7001
    INVALID_CONFIG = 7002
    CONFIG_PARSE_ERROR = 7003


class ApplicationError(Exception):
    """Base application error with enhanced context"""
    
    def __init__(self, message: str, code: int = ErrorCode.UNKNOWN_ERROR,
                 details: Optional[Dict[str, Any]] = None, cause: Optional[Exception] = None,
                 user_message: Optional[str] = None, suggestions: Optional[List[str]] = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}
        self.cause = cause
        self.user_message = user_message or self._generate_user_message()
        self.suggestions = suggestions or []
        self.timestamp = datetime.utcnow()
        self.traceback = traceback.format_exc()
        
    def _generate_user_message(self) -> str:
        """Generate user-friendly message based on error code"""
        user_messages = {
            ErrorCode.VALIDATION_ERROR: "The provided data is invalid. Please check your input.",
            ErrorCode.AUTHENTICATION_FAILED: "Authentication failed. Please check your credentials.",
            ErrorCode.AUTHORIZATION_FAILED: "You don't have permission to perform this action.",
            ErrorCode.RATE_LIMIT_EXCEEDED: "Too many requests. Please wait before trying again.",
            ErrorCode.MODEL_NOT_FOUND: "The requested AI model was not found.",
            ErrorCode.FILE_NOT_FOUND: "The requested file was not found.",
            ErrorCode.DATABASE_ERROR: "A database error occurred. Please try again later.",
            ErrorCode.NETWORK_ERROR: "A network error occurred. Please check your connection.",
        }
        return user_messages.get(self.code, "An unexpected error occurred. Please try again.")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for API responses"""
        return {
            'error': True,
            'code': self.code,
            'message': self.message,
            'user_message': self.user_message,
            'details': self.details,
            'suggestions': self.suggestions,
            'timestamp': self.timestamp.isoformat()
        }


class ErrorLogger:
    """Enhanced error logging with persistence and analysis"""
    
    def __init__(self, log_file: Optional[str] = None, db_path: Optional[str] = None):
        self.log_file = log_file
        self.db_path = db_path or "instance/error_logs.db"
        self.setup_database()
        
        # Thread-safe error tracking
        self._error_counts = {}
        self._error_lock = threading.Lock()
        
    def setup_database(self):
        """Setup error logging database"""
        try:
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS error_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        error_code INTEGER,
                        message TEXT NOT NULL,
                        details TEXT,
                        traceback TEXT,
                        user_id TEXT,
                        endpoint TEXT,
                        user_agent TEXT,
                        ip_address TEXT,
                        resolved BOOLEAN DEFAULT FALSE,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_error_logs_timestamp 
                    ON error_logs(timestamp)
                """)
                
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_error_logs_code 
                    ON error_logs(error_code)
                """)
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to setup error logging database: {e}")
    
    def log_error(self, error: Union[ApplicationError, Exception], 
                  context: Optional[Dict[str, Any]] = None):
        """Log error with enhanced context"""
        
        # Extract error details
        if isinstance(error, ApplicationError):
            error_code = error.code
            message = error.message
            details = error.details
            error_traceback = error.traceback
        else:
            error_code = ErrorCode.UNKNOWN_ERROR
            message = str(error)
            details = {}
            error_traceback = traceback.format_exc()
        
        # Add request context if available
        request_context = {}
        try:
            if request:
                request_context = {
                    'endpoint': request.endpoint,
                    'method': request.method,
                    'url': request.url,
                    'user_agent': request.headers.get('User-Agent'),
                    'ip_address': request.remote_addr,
                    'content_type': request.headers.get('Content-Type')
                }
        except RuntimeError:
            # Outside request context
            pass
        
        # Combine context
        full_context = {**details, **(context or {}), **request_context}
        
        # Log to application logger
        logger.error(f"Error {error_code}: {message}", extra={
            'error_code': error_code,
            'details': full_context,
            'traceback': error_traceback
        })
        
        # Log to database
        self._log_to_database(error_code, message, full_context, error_traceback)
        
        # Update error counts
        self._update_error_counts(error_code)
    
    def _log_to_database(self, error_code: int, message: str, 
                        details: Dict[str, Any], error_traceback: str):
        """Log error to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO error_logs 
                    (timestamp, error_code, message, details, traceback, 
                     user_id, endpoint, user_agent, ip_address)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    datetime.utcnow().isoformat(),
                    error_code,
                    message,
                    json.dumps(details),
                    error_traceback,
                    details.get('user_id'),
                    details.get('endpoint'),
                    details.get('user_agent'),
                    details.get('ip_address')
                ))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to log error to database: {e}")
    
    def _update_error_counts(self, error_code: int):
        """Update error frequency tracking"""
        with self._error_lock:
            current_hour = datetime.utcnow().strftime('%Y-%m-%d-%H')
            key = f"{error_code}:{current_hour}"
            self._error_counts[key] = self._error_counts.get(key, 0) + 1
    
    def get_error_stats(self, hours: int = 24) -> Dict[str, Any]:
        """Get error statistics for the last N hours"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT error_code, COUNT(*) as count
                    FROM error_logs 
                    WHERE timestamp > datetime('now', '-{} hours')
                    GROUP BY error_code
                    ORDER BY count DESC
                """.format(hours))
                
                error_counts = dict(cursor.fetchall())
                
                cursor = conn.execute("""
                    SELECT COUNT(*) as total
                    FROM error_logs 
                    WHERE timestamp > datetime('now', '-{} hours')
                """.format(hours))
                
                total_errors = cursor.fetchone()[0]
                
                return {
                    'total_errors': total_errors,
                    'error_counts': error_counts,
                    'period_hours': hours
                }
                
        except Exception as e:
            logger.error(f"Failed to get error stats: {e}")
            return {'total_errors': 0, 'error_counts': {}, 'period_hours': hours}


class ErrorHandler:
    """Centralized error handling with recovery mechanisms"""
    
    def __init__(self):
        self.error_logger = ErrorLogger()
        self.recovery_strategies = {}
        self._register_default_strategies()
    
    def _register_default_strategies(self):
        """Register default error recovery strategies"""
        
        def retry_strategy(func: Callable, *args, **kwargs) -> Any:
            """Generic retry strategy"""
            max_retries = kwargs.pop('max_retries', 3)
            delay = kwargs.pop('retry_delay', 1.0)
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise e
                    time.sleep(delay * (2 ** attempt))  # Exponential backoff
        
        def fallback_strategy(func: Callable, fallback_func: Callable, 
                            *args, **kwargs) -> Any:
            """Fallback strategy"""
            try:
                return func(*args, **kwargs)
            except Exception:
                return fallback_func(*args, **kwargs)
        
        self.recovery_strategies['retry'] = retry_strategy
        self.recovery_strategies['fallback'] = fallback_strategy
    
    def register_strategy(self, name: str, strategy: Callable):
        """Register custom recovery strategy"""
        self.recovery_strategies[name] = strategy
    
    def handle_error(self, error: Exception, context: Optional[Dict[str, Any]] = None,
                    recovery_strategy: Optional[str] = None) -> Dict[str, Any]:
        """Handle error with logging and optional recovery"""
        
        # Convert to ApplicationError if needed
        if not isinstance(error, ApplicationError):
            app_error = ApplicationError(
                message=str(error),
                code=self._classify_error(error),
                cause=error,
                details=context or {}
            )
        else:
            app_error = error
        
        # Log the error
        self.error_logger.log_error(app_error, context)
        
        # Apply recovery strategy if specified
        if recovery_strategy and recovery_strategy in self.recovery_strategies:
            try:
                strategy = self.recovery_strategies[recovery_strategy]
                # Note: This is a simplified example - real implementation
                # would need more sophisticated strategy application
                logger.info(f"Applying recovery strategy: {recovery_strategy}")
            except Exception as recovery_error:
                logger.error(f"Recovery strategy failed: {recovery_error}")
        
        return app_error.to_dict()
    
    def _classify_error(self, error: Exception) -> int:
        """Classify generic exceptions into error codes"""
        error_type = type(error).__name__
        
        classification_map = {
            'ValueError': ErrorCode.VALIDATION_ERROR,
            'TypeError': ErrorCode.VALIDATION_ERROR,
            'KeyError': ErrorCode.MISSING_FIELD,
            'FileNotFoundError': ErrorCode.FILE_NOT_FOUND,
            'PermissionError': ErrorCode.PERMISSION_DENIED,
            'ConnectionError': ErrorCode.CONNECTION_ERROR,
            'TimeoutError': ErrorCode.CONNECTION_TIMEOUT,
            'sqlite3.Error': ErrorCode.DATABASE_ERROR,
            'json.JSONDecodeError': ErrorCode.INVALID_FORMAT,
        }
        
        return classification_map.get(error_type, ErrorCode.UNKNOWN_ERROR)


# Global error handler instance
error_handler = ErrorHandler()


def handle_exceptions(recovery_strategy: Optional[str] = None):
    """Decorator for automatic exception handling"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_response = error_handler.handle_error(
                    e, 
                    context={'function': func.__name__, 'args': str(args)[:200]},
                    recovery_strategy=recovery_strategy
                )
                
                # Return JSON response for API endpoints
                if hasattr(request, 'endpoint'):
                    return jsonify(error_response), 500
                else:
                    raise e
        
        return wrapper
    return decorator


def handle_api_error(error: Exception) -> tuple:
    """Handle API errors and return appropriate HTTP response"""
    
    if isinstance(error, HTTPException):
        return jsonify({
            'error': True,
            'code': error.code,
            'message': error.description,
            'user_message': error.description
        }), error.code
    
    error_response = error_handler.handle_error(error)
    
    # Map error codes to HTTP status codes
    status_code_map = {
        ErrorCode.VALIDATION_ERROR: 400,
        ErrorCode.MISSING_FIELD: 400,
        ErrorCode.INVALID_FORMAT: 400,
        ErrorCode.AUTHENTICATION_FAILED: 401,
        ErrorCode.AUTHORIZATION_FAILED: 403,
        ErrorCode.DATA_NOT_FOUND: 404,
        ErrorCode.FILE_NOT_FOUND: 404,
        ErrorCode.RATE_LIMIT_EXCEEDED: 429,
        ErrorCode.DATABASE_ERROR: 500,
        ErrorCode.MODEL_ERROR: 500,
        ErrorCode.NETWORK_ERROR: 503,
    }
    
    status_code = status_code_map.get(error_response['code'], 500)
    return jsonify(error_response), status_code


class CircuitBreaker:
    """Circuit breaker pattern implementation for error resilience"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
        self._lock = threading.Lock()
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection"""
        
        with self._lock:
            if self.state == 'OPEN':
                if (self.last_failure_time is not None and 
                    time.time() - self.last_failure_time > self.recovery_timeout):
                    self.state = 'HALF_OPEN'
                else:
                    raise ApplicationError(
                        "Service temporarily unavailable",
                        ErrorCode.MAINTENANCE_MODE
                    )
        
        try:
            result = func(*args, **kwargs)
            
            # Success - reset circuit breaker
            with self._lock:
                self.failure_count = 0
                self.state = 'CLOSED'
            
            return result
            
        except Exception as e:
            with self._lock:
                self.failure_count += 1
                self.last_failure_time = time.time()
                
                if self.failure_count >= self.failure_threshold:
                    self.state = 'OPEN'
            
            raise e


# Global circuit breakers for critical services
circuit_breakers = {
    'database': CircuitBreaker(failure_threshold=3, recovery_timeout=30),
    'ai_model': CircuitBreaker(failure_threshold=5, recovery_timeout=60),
    'file_system': CircuitBreaker(failure_threshold=3, recovery_timeout=15)
}


def with_circuit_breaker(service_name: str):
    """Decorator to apply circuit breaker protection"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            breaker = circuit_breakers.get(service_name)
            if breaker:
                return breaker.call(func, *args, **kwargs)
            else:
                return func(*args, **kwargs)
        return wrapper
    return decorator
