#!/usr/bin/env python3
"""
Comprehensive Error Handling Utilities for Vybe AI Desktop Application
Replaces broad exception handling with specific error types and proper recovery
"""

import logging
import traceback
import sys
from typing import Dict, Any, Optional, Callable, Type, Union
from functools import wraps
from contextlib import contextmanager
import os
import json
from datetime import datetime

logger = logging.getLogger(__name__)


class VybeError(Exception):
    """Base exception class for Vybe application errors"""
    
    def __init__(self, message: str, error_code: Optional[str] = None, context: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.error_code = error_code or "VYBE_ERROR"
        self.context = context or {}
        self.timestamp = datetime.now().isoformat()


class DatabaseError(VybeError):
    """Database-related errors"""
    pass


class ValidationError(VybeError):
    """Data validation errors"""
    pass


class AuthenticationError(VybeError):
    """Authentication and authorization errors"""
    pass


class FileSystemError(VybeError):
    """File system operation errors"""
    pass


class NetworkError(VybeError):
    """Network and connectivity errors"""
    pass


class ConfigurationError(VybeError):
    """Configuration and setup errors"""
    pass


class ResourceError(VybeError):
    """Resource exhaustion and management errors"""
    pass


class SecurityError(VybeError):
    """Security-related errors"""
    pass


class ErrorHandler:
    """Comprehensive error handling and recovery system"""
    
    # Error type mappings
    ERROR_MAPPINGS = {
        'FileNotFoundError': FileSystemError,
        'PermissionError': FileSystemError,
        'OSError': FileSystemError,
        'IOError': FileSystemError,
        'ConnectionError': NetworkError,
        'TimeoutError': NetworkError,
        'requests.exceptions.RequestException': NetworkError,
        'sqlite3.Error': DatabaseError,
        'sqlalchemy.exc.SQLAlchemyError': DatabaseError,
        'ValueError': ValidationError,
        'TypeError': ValidationError,
        'KeyError': ValidationError,
        'IndexError': ValidationError,
        'AttributeError': ValidationError,
        'ImportError': ConfigurationError,
        'ModuleNotFoundError': ConfigurationError,
        'MemoryError': ResourceError,
        'RecursionError': ResourceError,
        'KeyboardInterrupt': VybeError,
        'SystemExit': VybeError
    }
    
    # Recovery strategies
    RECOVERY_STRATEGIES = {
        FileSystemError: [
            "Check file permissions and ownership",
            "Verify disk space availability",
            "Ensure file paths are correct",
            "Try running with elevated privileges if needed"
        ],
        NetworkError: [
            "Check network connectivity",
            "Verify service endpoints and ports",
            "Check firewall and proxy settings",
            "Retry operation with exponential backoff"
        ],
        DatabaseError: [
            "Check database connection",
            "Verify database schema",
            "Check for database locks",
            "Consider database maintenance"
        ],
        ValidationError: [
            "Verify input data format",
            "Check required fields",
            "Validate data types",
            "Review business logic constraints"
        ],
        ResourceError: [
            "Check system resources (memory, CPU)",
            "Reduce concurrent operations",
            "Optimize resource usage",
            "Consider system upgrades"
        ],
        ConfigurationError: [
            "Verify configuration files",
            "Check environment variables",
            "Validate dependencies",
            "Review application settings"
        ]
    }
    
    @classmethod
    def classify_error(cls, error: Exception) -> Type[VybeError]:
        """Classify an exception into a specific Vybe error type"""
        error_type = type(error).__name__
        
        # Check direct mappings
        if error_type in cls.ERROR_MAPPINGS:
            return cls.ERROR_MAPPINGS[error_type]
        
        # Check module-based mappings
        error_module = getattr(error, '__module__', '')
        for pattern, vybe_error_type in cls.ERROR_MAPPINGS.items():
            if '.' in pattern and pattern in f"{error_module}.{error_type}":
                return vybe_error_type
        
        # Default to base VybeError
        return VybeError
    
    @classmethod
    def get_recovery_suggestions(cls, error: Exception) -> list:
        """Get recovery suggestions for a specific error"""
        vybe_error_type = cls.classify_error(error)
        return cls.RECOVERY_STRATEGIES.get(vybe_error_type, [
            "Review error logs for details",
            "Check system status",
            "Contact support if issue persists"
        ])
    
    @classmethod
    def handle_error(cls, error: Exception, context: Optional[Dict[str, Any]] = None, 
                    reraise: bool = True, log_level: str = "ERROR") -> VybeError:
        """
        Handle an exception with proper classification and logging
        
        Args:
            error: The exception to handle
            context: Additional context information
            reraise: Whether to reraise as VybeError
            log_level: Logging level for the error
            
        Returns:
            Classified VybeError instance
        """
        # Classify the error
        vybe_error_type = cls.classify_error(error)
        
        # Create context
        error_context = {
            'original_error_type': type(error).__name__,
            'original_error_message': str(error),
            'traceback': traceback.format_exc(),
            'recovery_suggestions': cls.get_recovery_suggestions(error),
            **(context or {})
        }
        
        # Create VybeError instance
        vybe_error = vybe_error_type(
            message=str(error),
            error_code=f"{vybe_error_type.__name__.upper()}",
            context=error_context
        )
        
        # Log the error
        log_message = f"[{vybe_error.error_code}] {vybe_error.args[0]}"
        if log_level.upper() == "ERROR":
            logger.error(log_message, extra={'error_context': error_context})
        elif log_level.upper() == "WARNING":
            logger.warning(log_message, extra={'error_context': error_context})
        else:
            logger.info(log_message, extra={'error_context': error_context})
        
        # Reraise if requested
        if reraise:
            raise vybe_error
        
        return vybe_error
    
    @classmethod
    def safe_execute(cls, func: Callable, *args, 
                    error_context: Optional[Dict[str, Any]] = None,
                    default_return: Any = None,
                    **kwargs) -> Any:
        """
        Safely execute a function with proper error handling
        
        Args:
            func: Function to execute
            *args: Function arguments
            error_context: Additional context for error handling
            default_return: Value to return on error
            **kwargs: Function keyword arguments
            
        Returns:
            Function result or default_return on error
        """
        try:
            return func(*args, **kwargs)
        except Exception as e:
            cls.handle_error(e, error_context, reraise=False)
            return default_return
    
    @classmethod
    @contextmanager
    def error_context(cls, operation: str, context: Optional[Dict[str, Any]] = None):
        """
        Context manager for error handling with operation context
        
        Args:
            operation: Description of the operation being performed
            context: Additional context information
        """
        operation_context = {
            'operation': operation,
            'timestamp': datetime.now().isoformat(),
            **(context or {})
        }
        
        try:
            yield operation_context
        except Exception as e:
            cls.handle_error(e, operation_context)
            raise


def handle_specific_errors(*error_types: Type[Exception], 
                          default_handler: Optional[Callable] = None,
                          reraise: bool = True):
    """
    Decorator to handle specific error types with custom handlers
    
    Args:
        *error_types: Specific exception types to handle
        default_handler: Default error handler function
        reraise: Whether to reraise the error after handling
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except tuple(error_types) as e:
                if default_handler:
                    default_handler(e)
                else:
                    ErrorHandler.handle_error(e, {
                        'function': func.__name__,
                        'args': str(args)[:200],
                        'kwargs': str(kwargs)[:200]
                    }, reraise=reraise)
                return None
        return wrapper
    return decorator


def handle_file_operations(func: Callable) -> Callable:
    """Decorator specifically for file operation error handling"""
    return handle_specific_errors(
        FileNotFoundError, PermissionError, OSError, IOError,
        default_handler=lambda e: logger.error(f"File operation failed: {e}")
    )(func)


def handle_database_operations(func: Callable) -> Callable:
    """Decorator specifically for database operation error handling"""
    return handle_specific_errors(
        DatabaseError, Exception,
        default_handler=lambda e: logger.error(f"Database operation failed: {e}")
    )(func)


def handle_network_operations(func: Callable) -> Callable:
    """Decorator specifically for network operation error handling"""
    return handle_specific_errors(
        NetworkError, ConnectionError, TimeoutError,
        default_handler=lambda e: logger.error(f"Network operation failed: {e}")
    )(func)


def handle_validation_errors(func: Callable) -> Callable:
    """Decorator specifically for validation error handling"""
    return handle_specific_errors(
        ValidationError, ValueError, TypeError, KeyError, IndexError,
        default_handler=lambda e: logger.error(f"Validation failed: {e}")
    )(func)


# Convenience functions for common error handling patterns
def safe_file_operation(operation: str, file_path: str, func: Callable, *args, **kwargs):
    """Safely perform file operations with proper error handling"""
    with ErrorHandler.error_context(f"File operation: {operation}", {'file_path': file_path}):
        return func(*args, **kwargs)


def safe_database_operation(operation: str, func: Callable, *args, **kwargs):
    """Safely perform database operations with proper error handling"""
    with ErrorHandler.error_context(f"Database operation: {operation}"):
        return func(*args, **kwargs)


def safe_network_operation(operation: str, endpoint: str, func: Callable, *args, **kwargs):
    """Safely perform network operations with proper error handling"""
    with ErrorHandler.error_context(f"Network operation: {operation}", {'endpoint': endpoint}):
        return func(*args, **kwargs)


def safe_validation(operation: str, data: Any, func: Callable, *args, **kwargs):
    """Safely perform validation operations with proper error handling"""
    with ErrorHandler.error_context(f"Validation: {operation}", {'data_type': type(data).__name__}):
        return func(*args, **kwargs)


# Global error handler instance
error_handler = ErrorHandler()


# Export commonly used functions
__all__ = [
    'VybeError', 'DatabaseError', 'ValidationError', 'AuthenticationError',
    'FileSystemError', 'NetworkError', 'ConfigurationError', 'ResourceError',
    'SecurityError', 'ErrorHandler', 'handle_specific_errors', 'handle_file_operations',
    'handle_database_operations', 'handle_network_operations', 'handle_validation_errors',
    'safe_file_operation', 'safe_database_operation', 'safe_network_operation',
    'safe_validation', 'error_handler'
]
